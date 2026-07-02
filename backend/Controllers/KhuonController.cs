using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Text;
using backend.Services;

namespace backend.Controllers;

[ApiController]
[Route("api/khuon")]
public class KhuonController : ControllerBase
{
    private readonly KhuonService _service;

    public KhuonController(KhuonService service)
    {
        _service = service;
    }

    /// <summary>GET /api/khuon?month=2026-05 — daily khuon data</summary>
    [Authorize]
    [HttpGet]
    public async Task<IActionResult> GetKhuonData([FromQuery] string? month)
    {
        if (string.IsNullOrEmpty(month)) month = DateTime.Now.ToString("yyyy-MM");
        var parts = month.Split('-');
        if (parts.Length < 2) return BadRequest(new { error = "Invalid month format" });

        int year = int.Parse(parts[0]);
        int mon = int.Parse(parts[1]);

        var data = await _service.GetKhuonDataAsync(year, mon);
        return Ok(data);
    }

    /// <summary>GET /api/khuon/yearly?year=2026 — monthly summary</summary>
    [Authorize]
    [HttpGet("yearly")]
    public async Task<IActionResult> GetKhuonYearly([FromQuery] int? year)
    {
        int y = year ?? DateTime.Now.Year;
        var data = await _service.GetKhuonYearlyAsync(y);
        return Ok(data);
    }

    /// <summary>GET /api/khuon/export?month=2026-07&view=monthly — export CSV</summary>
    [Authorize]
    [HttpGet("export")]
    public async Task<IActionResult> ExportKhuon([FromQuery] string? month, [FromQuery] string? view)
    {
        if (string.IsNullOrEmpty(month)) month = DateTime.Now.ToString("yyyy-MM");
        var parts = month.Split('-');
        if (parts.Length < 2) return BadRequest(new { error = "Invalid month format" });

        int year = int.Parse(parts[0]);
        int mon = int.Parse(parts[1]);
        view = view ?? "monthly";

        var sb = new StringBuilder();
        // BOM for Excel to recognize UTF-8
        sb.Append('\uFEFF');

        if (view == "daily")
        {
            // Daily view — columns: STT, Seri, Khuôn, PL, Day1..Day31, Tổng Tháng, Tồn Trước, Tổng
            var data = await _service.GetKhuonDataAsync(year, mon);

            sb.Append("STT,Seri Khuôn,Khuôn,PL");
            for (int d = 1; d <= 31; d++) sb.Append($",{d}");
            sb.AppendLine(",Tổng Tháng,Tồn Trước,Tổng");

            int stt = 1;
            for (int i = 1; i <= 7; i++)
            {
                var plKey = $"PL{i}";
                var molds = data.Data.GetValueOrDefault(plKey, new List<DTOs.KhuonMoldDto>());
                foreach (var m in molds)
                {
                    sb.Append($"{stt},\"{EscapeCsv(m.Seri)}\",\"{EscapeCsv(m.ThongSo)}\",{plKey}");
                    for (int d = 1; d <= 31; d++)
                    {
                        var val = m.Days.GetValueOrDefault(d, 0);
                        sb.Append($",{val}");
                    }
                    sb.AppendLine($",{m.TongThang},{m.TonTruoc},{m.Tong}");
                    stt++;
                }
            }

            var bytes = Encoding.UTF8.GetBytes(sb.ToString());
            return File(bytes, "text/csv; charset=utf-8", $"Khuon_T{mon}_{year}.csv");
        }
        else
        {
            // Monthly/Yearly view — columns: STT, Seri, Khuôn, PL, T1..T12, Tổng Năm
            var data = await _service.GetKhuonYearlyAsync(year);

            sb.Append("STT,Seri Khuôn,Khuôn,PL");
            for (int m = 1; m <= 12; m++) sb.Append($",T{m}");
            sb.AppendLine(",Tổng Năm");

            int stt = 1;
            for (int i = 1; i <= 7; i++)
            {
                var plKey = $"PL{i}";
                var molds = data.Data.GetValueOrDefault(plKey, new List<DTOs.KhuonYearlyMoldDto>());
                foreach (var m in molds)
                {
                    sb.Append($"{stt},\"{EscapeCsv(m.Seri)}\",\"{EscapeCsv(m.ThongSo)}\",{plKey}");
                    for (int mo = 1; mo <= 12; mo++)
                    {
                        var val = m.Months.GetValueOrDefault(mo, 0);
                        sb.Append($",{val}");
                    }
                    sb.AppendLine($",{m.YearTotal}");
                    stt++;
                }
            }

            var bytes = Encoding.UTF8.GetBytes(sb.ToString());
            return File(bytes, "text/csv; charset=utf-8", $"Khuon_Nam_{year}.csv");
        }
    }

    private static string EscapeCsv(string? val)
    {
        if (val == null) return "";
        return val.Replace("\"", "\"\"");
    }
}
