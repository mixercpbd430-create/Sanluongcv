using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using backend.DTOs;
using backend.Services;

namespace backend.Controllers;

[ApiController]
[Route("api")]
public class ManualInputController : ControllerBase
{
    private readonly ProductionService _service;

    public ManualInputController(ProductionService service)
    {
        _service = service;
    }

    [Authorize]
    [HttpPost("manual-input")]
    public async Task<IActionResult> SaveManualInput([FromBody] ManualInputRequest req)
    {
        if (string.IsNullOrEmpty(req.Month) || req.Day == 0 ||
            (req.Field != "sale" && req.Field != "stock"))
        {
            return BadRequest(new { error = "Invalid input" });
        }

        var parts = req.Month.Split('-');
        var year = int.Parse(parts[0]);
        var month = int.Parse(parts[1]);

        await _service.SaveManualInputAsync(year, month, req.Day, req.Field, req.Value);

        return Ok(new { status = "ok", field = req.Field, day = req.Day, value = req.Value });
    }
}
