using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using backend.Data;
using backend.DTOs;

namespace backend.Controllers;

[ApiController]
[Route("api/auth")]
public class AuthController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly IConfiguration _config;

    public AuthController(AppDbContext db, IConfiguration config)
    {
        _db = db;
        _config = config;
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest req)
    {
        var username = req.Username.Trim().ToLower();
        var user = await _db.Users
            .FirstOrDefaultAsync(u => u.Username == username && u.Password == req.Password.Trim());

        if (user == null)
            return Unauthorized(new { error = "Sai tài khoản hoặc mật khẩu!" });

        var token = GenerateJwtToken(user);

        return Ok(new LoginResponse
        {
            Token = token,
            User = new UserInfo
            {
                Id = user.Id,
                Username = user.Username,
                Role = user.Role,
                DisplayName = user.DisplayName,
            }
        });
    }

    [Authorize]
    [HttpPost("change-password")]
    public async Task<IActionResult> ChangePassword([FromBody] ChangePasswordRequest req)
    {
        var newPass = req.NewPassword.Trim();
        if (string.IsNullOrEmpty(newPass))
            return BadRequest(new { error = "Mật khẩu không được để trống" });

        var username = User.FindFirst(ClaimTypes.Name)?.Value;
        if (username == null)
            return Unauthorized();

        var user = await _db.Users.FirstOrDefaultAsync(u => u.Username == username);
        if (user == null)
            return NotFound(new { error = "User not found" });

        user.Password = newPass;
        await _db.SaveChangesAsync();

        return Ok(new { status = "ok", message = "Đổi mật khẩu thành công!" });
    }

    [Authorize]
    [HttpGet("users")]
    public async Task<IActionResult> GetUsers()
    {
        var role = User.FindFirst(ClaimTypes.Role)?.Value;
        if (role != "admin")
            return StatusCode(403, new { error = "Không có quyền" });

        var users = await _db.Users
            .OrderByDescending(u => u.Role).ThenBy(u => u.Username)
            .Select(u => new UserListItem
            {
                Username = u.Username,
                Password = u.Password,
                Role = u.Role,
                DisplayName = u.DisplayName,
            })
            .ToListAsync();

        return Ok(users);
    }

    private string GenerateJwtToken(Models.User user)
    {
        var key = new SymmetricSecurityKey(
            Encoding.UTF8.GetBytes(_config["Jwt:Key"] ?? "cpvn-sanluong-2026-secret-key-min-32-chars!"));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new Claim(ClaimTypes.Name, user.Username),
            new Claim(ClaimTypes.Role, user.Role),
            new Claim("display_name", user.DisplayName),
        };

        var token = new JwtSecurityToken(
            issuer: _config["Jwt:Issuer"] ?? "SanLuongApp",
            audience: _config["Jwt:Audience"] ?? "SanLuongApp",
            claims: claims,
            expires: DateTime.UtcNow.AddDays(30),
            signingCredentials: creds
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
