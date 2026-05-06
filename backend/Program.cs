using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using backend.Data;
using backend.Services;

// ── Load .env file if present ──
var envFile = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".env");
if (!File.Exists(envFile)) envFile = Path.Combine(Directory.GetCurrentDirectory(), ".env");
if (File.Exists(envFile))
{
    foreach (var line in File.ReadAllLines(envFile))
    {
        var trimmed = line.Trim();
        if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith('#')) continue;
        var idx = trimmed.IndexOf('=');
        if (idx <= 0) continue;
        var key = trimmed[..idx].Trim();
        var val = trimmed[(idx + 1)..].Trim().Trim('"');
        Environment.SetEnvironmentVariable(key, val);
    }
    Console.WriteLine($"[ENV] Loaded .env from {envFile}");
}

var builder = WebApplication.CreateBuilder(args);

// ── JSON serialization: snake_case ──
builder.Services.AddControllers()
    .AddJsonOptions(o =>
    {
        o.JsonSerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
        o.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
    });

// ── Swagger (dev only) ──
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// ── PostgreSQL via EF Core ──
var dbUrl = Environment.GetEnvironmentVariable("DATABASE_URL") ?? "";
string connectionString;

if (!string.IsNullOrEmpty(dbUrl))
{
    // Parse DATABASE_URL format: postgres://user:pass@host:port/dbname
    connectionString = ConvertDatabaseUrl(dbUrl);
    Console.WriteLine($"[DB] Using DATABASE_URL → {new Uri(dbUrl).Host}");
}
else
{
    connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
        ?? "Host=localhost;Database=sanluong;Username=postgres;Password=postgres";
    Console.WriteLine("[DB] Using default connection string (localhost)");
}

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connectionString));

// ── Services ──
builder.Services.AddScoped<ProductionService>();

// ── JWT Authentication ──
var jwtKey = builder.Configuration["Jwt:Key"] ?? "cpvn-sanluong-2026-secret-key-min-32-chars!";
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"] ?? "SanLuongApp",
            ValidAudience = builder.Configuration["Jwt:Audience"] ?? "SanLuongApp",
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey)),
        };
    });

// ── CORS ──
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.WithOrigins(
                "http://localhost:5173",    // Vite dev
                "http://localhost:3000",     // alt
                "https://sanluongcv.onrender.com"
            )
            .AllowAnyHeader()
            .AllowAnyMethod()
            .AllowCredentials();
    });
});

var app = builder.Build();

// ── Auto-migrate on startup (gracefully) ──
try
{
    using var scope = app.Services.CreateScope();
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.Migrate();
    Console.WriteLine("[DB] Migration applied successfully");
}
catch (Exception ex)
{
    Console.WriteLine($"[DB] Migration warning: {ex.Message}");
    // Try EnsureCreated as fallback
    try
    {
        using var scope = app.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        db.Database.EnsureCreated();
        Console.WriteLine("[DB] EnsureCreated completed");
    }
    catch (Exception ex2)
    {
        Console.WriteLine($"[DB] Database setup failed: {ex2.Message}");
        Console.WriteLine("[DB] App will start but database operations will fail");
    }
}

// ── Middleware ──
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors("AllowFrontend");
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();

var port = Environment.GetEnvironmentVariable("PORT") ?? "5000";
app.Run($"http://0.0.0.0:{port}");


// ── Helper: convert DATABASE_URL to Npgsql connection string ──
static string ConvertDatabaseUrl(string url)
{
    // postgres://user:pass@host:port/dbname?sslmode=require
    var uri = new Uri(url);
    var userInfo = uri.UserInfo.Split(':');
    var host = uri.Host;
    var port = uri.Port > 0 ? uri.Port : 5432;
    var database = uri.AbsolutePath.TrimStart('/');
    var username = userInfo[0];
    var password = userInfo.Length > 1 ? userInfo[1] : "";

    var sslMode = "Require";
    if (uri.Query.Contains("sslmode=disable", StringComparison.OrdinalIgnoreCase))
        sslMode = "Disable";

    return $"Host={host};Port={port};Database={database};Username={username};Password={password};SSL Mode={sslMode};Trust Server Certificate=true";
}
