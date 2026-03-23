using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using backend.Data;
using backend.DTOs;
using backend.Models;
using backend.Services;

namespace backend.Controllers;

[ApiController]
[Route("api")]
public class UploadController : ControllerBase
{
    private readonly ProductionService _service;
    private readonly AppDbContext _db;

    public UploadController(ProductionService service, AppDbContext db)
    {
        _service = service;
        _db = db;
    }

    [HttpPost("upload-data")]
    public async Task<IActionResult> UploadData([FromBody] UploadRequest req)
    {
        if (req == null)
            return BadRequest(new { status = "error", message = "No JSON data" });

        var username = req.Username.Trim().ToLower();
        var password = req.Password.Trim();

        // Authenticate
        var user = await _db.Users
            .FirstOrDefaultAsync(u => u.Username == username && u.Password == password);
        if (user == null)
            return Unauthorized(new { status = "error", message = "Sai tài khoản hoặc mật khẩu" });

        if (req.Entries.Count == 0)
            return BadRequest(new { status = "error", message = "Không có dữ liệu" });

        var result = await _service.SaveUploadedDataAsync(username, req.Entries);

        // Log the upload timestamp
        _db.UploadLogs.Add(new UploadLog
        {
            Username = username,
            DisplayName = user.DisplayName,
            RecordsCount = req.Entries.Count,
            UploadedAt = DateTime.UtcNow,
        });
        await _db.SaveChangesAsync();

        return Ok(result);
    }

    /// <summary>
    /// Admin-only: get latest upload logs for each source.
    /// </summary>
    [Authorize]
    [HttpGet("upload-logs")]
    public async Task<IActionResult> GetUploadLogs()
    {
        var role = User.FindFirst(ClaimTypes.Role)?.Value;
        if (role != "admin")
            return StatusCode(403, new { error = "Không có quyền" });

        // Get the latest upload for each username
        var latestLogs = await _db.UploadLogs
            .GroupBy(l => l.Username)
            .Select(g => g.OrderByDescending(l => l.UploadedAt).First())
            .ToListAsync();

        // Also get last 20 upload records for history view
        var recentLogs = await _db.UploadLogs
            .OrderByDescending(l => l.UploadedAt)
            .Take(20)
            .Select(l => new UploadLogDto
            {
                Username = l.Username,
                DisplayName = l.DisplayName,
                RecordsCount = l.RecordsCount,
                UploadedAt = l.UploadedAt,
            })
            .ToListAsync();

        var latestDtos = latestLogs.Select(l => new UploadLogDto
        {
            Username = l.Username,
            DisplayName = l.DisplayName,
            RecordsCount = l.RecordsCount,
            UploadedAt = l.UploadedAt,
        }).ToList();

        return Ok(new { latest = latestDtos, recent = recentLogs });
    }
}
