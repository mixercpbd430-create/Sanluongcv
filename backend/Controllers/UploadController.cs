using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using backend.Data;
using backend.DTOs;
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
        return Ok(result);
    }
}
