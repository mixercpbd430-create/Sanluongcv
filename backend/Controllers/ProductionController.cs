using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using backend.DTOs;
using backend.Services;

namespace backend.Controllers;

[ApiController]
[Route("api")]
public class ProductionController : ControllerBase
{
    private readonly ProductionService _service;

    public ProductionController(ProductionService service)
    {
        _service = service;
    }

    [Authorize]
    [HttpGet("data")]
    public async Task<IActionResult> GetData([FromQuery] string? month)
    {
        var data = await _service.GetAllDataAsync(month);
        return Ok(data);
    }

    [Authorize]
    [HttpGet("report/{day:int}")]
    public async Task<IActionResult> GetReport(int day, [FromQuery] string? month)
    {
        if (string.IsNullOrEmpty(month))
            return BadRequest(new { error = "Month parameter required" });

        var report = await _service.GetDayReportAsync(day, month);
        return Ok(report);
    }

    [Authorize]
    [HttpGet("db-stats")]
    public async Task<IActionResult> GetDbStats()
    {
        var stats = await _service.GetDbStatsAsync();
        return Ok(stats ?? (object)new { error = "No database found" });
    }
}
