using Microsoft.EntityFrameworkCore;
using backend.Models;

namespace backend.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<Production> Productions { get; set; } = null!;
    public DbSet<ManualInput> ManualInputs { get; set; } = null!;
    public DbSet<User> Users { get; set; } = null!;
    public DbSet<UploadLog> UploadLogs { get; set; } = null!;

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Production: unique constraint (line_name, year, month, day)
        modelBuilder.Entity<Production>()
            .HasIndex(p => new { p.LineName, p.Year, p.Month, p.Day })
            .IsUnique();

        modelBuilder.Entity<Production>()
            .HasIndex(p => new { p.Year, p.Month })
            .HasDatabaseName("idx_production_month");

        modelBuilder.Entity<Production>()
            .HasIndex(p => new { p.LineName, p.Year, p.Month })
            .HasDatabaseName("idx_production_line_month");

        // ManualInput: unique constraint (year, month, day, field)
        modelBuilder.Entity<ManualInput>()
            .HasIndex(m => new { m.Year, m.Month, m.Day, m.Field })
            .IsUnique();

        // User: unique constraint (username)
        modelBuilder.Entity<User>()
            .HasIndex(u => u.Username)
            .IsUnique();

        // UploadLog: index on uploaded_at for fast queries
        modelBuilder.Entity<UploadLog>()
            .HasIndex(l => l.UploadedAt)
            .HasDatabaseName("idx_upload_logs_uploaded_at");

        // Seed default users
        modelBuilder.Entity<User>().HasData(
            new User { Id = 1, Username = "mixer", Password = "123", Role = "user", DisplayName = "Mixer" },
            new User { Id = 2, Username = "pellet feedmill", Password = "111", Role = "user", DisplayName = "Pellet Feedmill" },
            new User { Id = 3, Username = "pellet mini", Password = "222", Role = "user", DisplayName = "Pellet Mini" },
            new User { Id = 4, Username = "admin", Password = "2810", Role = "admin", DisplayName = "Admin" }
        );
    }
}
