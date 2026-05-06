using Microsoft.AspNetCore.Mvc;

namespace backend.Controllers;

[ApiController]
public class HealthController : ControllerBase
{
    [HttpGet("healthz")]
    public IActionResult Health() => Ok("ok");
}
