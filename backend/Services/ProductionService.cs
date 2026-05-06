using Microsoft.EntityFrameworkCore;
using backend.Data;
using backend.DTOs;
using backend.Models;

namespace backend.Services;

public class ProductionService
{
    private readonly AppDbContext _db;

    public ProductionService(AppDbContext db)
    {
        _db = db;
    }

    // ── Permission map (same as Python) ──
    private static readonly Dictionary<string, string[]> UserLinePermissions = new()
    {
        ["mixer"] = new[] { "MIXER" },
        ["pellet feedmill"] = new[] { "PL1", "PL2", "PL3", "PL4", "PL5" },
        ["pellet mini"] = new[] { "PL6", "PL7" },
        ["admin"] = new[] { "MIXER", "PL1", "PL2", "PL3", "PL4", "PL5", "PL6", "PL7" },
    };

    public async Task<DataResponse> GetAllDataAsync(string? monthKey)
    {
        var rows = await _db.Productions
            .OrderBy(p => p.Year).ThenBy(p => p.Month)
            .ThenBy(p => p.LineName).ThenBy(p => p.Day)
            .ToListAsync();

        var dataByMonth = new Dictionary<string, Dictionary<string, LineInfo>>();

        foreach (var row in rows)
        {
            var mk = $"{row.Year}-{row.Month:D2}";

            if (!dataByMonth.ContainsKey(mk))
                dataByMonth[mk] = new Dictionary<string, LineInfo>();

            if (!dataByMonth[mk].ContainsKey(row.LineName))
            {
                dataByMonth[mk][row.LineName] = new LineInfo
                {
                    Name = row.LineName,
                    Month = row.Month,
                    Year = row.Year,
                    MonthKey = mk,
                    Category = row.Category,
                    Days = new List<DayData>(),
                    Summary = new SummaryData()
                };
            }

            var dayData = new DayData
            {
                Day = row.Day,
                Ca1 = Math.Round(row.Ca1, 2),
                Ca2 = Math.Round(row.Ca2, 2),
                Ca3 = Math.Round(row.Ca3, 2),
                Total = Math.Round(row.Total, 2),
                CamBot = row.CamBot != 0 ? Math.Round(row.CamBot, 2) : null
            };

            dataByMonth[mk][row.LineName].Days.Add(dayData);
        }

        // Calculate summaries
        foreach (var (mk, lines) in dataByMonth)
        {
            foreach (var (_, info) in lines)
            {
                info.Summary = new SummaryData
                {
                    Ca1 = Math.Round(info.Days.Sum(d => d.Ca1), 2),
                    Ca2 = Math.Round(info.Days.Sum(d => d.Ca2), 2),
                    Ca3 = Math.Round(info.Days.Sum(d => d.Ca3), 2),
                    Total = Math.Round(info.Days.Sum(d => d.Total), 2),
                };
            }
        }

        var sortedMonths = dataByMonth.Keys.OrderByDescending(m => m).ToList();
        var fallback = DateTime.Now.ToString("yyyy-MM");
        var selected = monthKey ?? (sortedMonths.Count > 0 ? sortedMonths[0] : fallback);

        var monthData = dataByMonth.GetValueOrDefault(selected, new Dictionary<string, LineInfo>());

        // Monthly sale total
        double saleTotal = 0;
        if (selected.Contains('-'))
        {
            var parts = selected.Split('-');
            var year = int.Parse(parts[0]);
            var month = int.Parse(parts[1]);
            saleTotal = await GetMonthlySaleTotal(year, month);
        }

        return new DataResponse
        {
            Months = sortedMonths.Select(mk =>
            {
                var parts = mk.Split('-');
                return new MonthOption
                {
                    Key = mk,
                    Label = $"Tháng {int.Parse(parts[1])}/{parts[0]}"
                };
            }).ToList(),
            SelectedMonth = selected,
            Lines = monthData,
            MonthlySaleTotal = saleTotal,
        };
    }

    public async Task<ReportResponse> GetDayReportAsync(int day, string monthKey)
    {
        var parts = monthKey.Split('-');
        var year = int.Parse(parts[0]);
        var month = int.Parse(parts[1]);

        var dayRows = await _db.Productions
            .Where(p => p.Year == year && p.Month == month && p.Day == day)
            .ToListAsync();

        var mixer = dayRows.FirstOrDefault(r => r.LineName == "MIXER");
        var pellets = new List<PelletData>();
        double tpCa1 = 0, tpCa2 = 0, tpCa3 = 0, tpTotal = 0;

        for (int i = 1; i <= 7; i++)
        {
            var plName = $"PL{i}";
            var pl = dayRows.FirstOrDefault(r => r.LineName == plName);
            var pellet = new PelletData
            {
                Name = plName,
                Ca1 = pl?.Ca1 ?? 0,
                Ca2 = pl?.Ca2 ?? 0,
                Ca3 = pl?.Ca3 ?? 0,
                Total = pl?.Total ?? 0,
            };
            pellets.Add(pellet);
            tpCa1 += pellet.Ca1;
            tpCa2 += pellet.Ca2;
            tpCa3 += pellet.Ca3;
            tpTotal += pellet.Total;
        }

        // Manual inputs
        var manualInputs = await _db.ManualInputs
            .Where(m => m.Year == year && m.Month == month && m.Day == day)
            .ToListAsync();

        var saleInput = manualInputs.FirstOrDefault(m => m.Field == "sale");
        var stockInput = manualInputs.FirstOrDefault(m => m.Field == "stock");

        return new ReportResponse
        {
            Day = day,
            Month = monthKey,
            Mixer = new ShiftData
            {
                Ca1 = mixer?.Ca1 ?? 0,
                Ca2 = mixer?.Ca2 ?? 0,
                Ca3 = mixer?.Ca3 ?? 0,
                Total = mixer?.Total ?? 0,
                CamBot = mixer?.CamBot ?? 0,
            },
            Pellets = pellets,
            TotalPellet = new ShiftData
            {
                Ca1 = Math.Round(tpCa1, 2),
                Ca2 = Math.Round(tpCa2, 2),
                Ca3 = Math.Round(tpCa3, 2),
                Total = Math.Round(tpTotal, 2),
            },
            Sale = saleInput?.Value,
            Stock = stockInput?.Value,
        };
    }

    public async Task<object> SaveUploadedDataAsync(string username, List<UploadEntry> entries)
    {
        var allowedLines = UserLinePermissions.GetValueOrDefault(username, Array.Empty<string>());
        if (allowedLines.Length == 0)
            return new { status = "error", message = $"User '{username}' không có quyền upload" };

        int inserted = 0, skipped = 0;
        var errors = new List<string>();

        foreach (var entry in entries)
        {
            var lineName = entry.LineName.ToUpper();
            if (!allowedLines.Contains(lineName))
            {
                skipped++;
                errors.Add($"{lineName}: không có quyền");
                continue;
            }

            try
            {
                var existing = await _db.Productions
                    .FirstOrDefaultAsync(p => p.LineName == lineName
                        && p.Year == entry.Year && p.Month == entry.Month && p.Day == entry.Day);

                if (existing != null)
                {
                    existing.Category = entry.Category;
                    existing.Ca1 = entry.Ca1;
                    existing.Ca2 = entry.Ca2;
                    existing.Ca3 = entry.Ca3;
                    existing.Total = entry.Total;
                    existing.CamBot = entry.CamBot;
                }
                else
                {
                    _db.Productions.Add(new Production
                    {
                        LineName = lineName,
                        Category = entry.Category,
                        Year = entry.Year,
                        Month = entry.Month,
                        Day = entry.Day,
                        Ca1 = entry.Ca1,
                        Ca2 = entry.Ca2,
                        Ca3 = entry.Ca3,
                        Total = entry.Total,
                        CamBot = entry.CamBot,
                    });
                }
                inserted++;
            }
            catch (Exception e)
            {
                errors.Add($"{lineName} day {entry.Day}: {e.Message}");
            }
        }

        await _db.SaveChangesAsync();

        return new
        {
            status = "ok",
            inserted,
            skipped,
            errors = errors.Take(10).ToList(),
        };
    }

    public async Task SaveManualInputAsync(int year, int month, int day, string field, double value)
    {
        var existing = await _db.ManualInputs
            .FirstOrDefaultAsync(m => m.Year == year && m.Month == month && m.Day == day && m.Field == field);

        if (existing != null)
        {
            existing.Value = value;
        }
        else
        {
            _db.ManualInputs.Add(new ManualInput
            {
                Year = year,
                Month = month,
                Day = day,
                Field = field,
                Value = value,
            });
        }

        await _db.SaveChangesAsync();
    }

    public async Task<double> GetMonthlySaleTotal(int year, int month)
    {
        var total = await _db.ManualInputs
            .Where(m => m.Year == year && m.Month == month && m.Field == "sale")
            .SumAsync(m => (double?)m.Value) ?? 0;
        return Math.Round(total, 1);
    }

    public async Task<DbStatsResponse?> GetDbStatsAsync()
    {
        try
        {
            var totalRecords = await _db.Productions.CountAsync();
            var totalLines = await _db.Productions.Select(p => p.LineName).Distinct().CountAsync();
            var months = await _db.Productions
                .Select(p => new { p.Year, p.Month })
                .Distinct()
                .OrderByDescending(p => p.Year).ThenByDescending(p => p.Month)
                .Select(p => $"{p.Year}-{p.Month:D2}")
                .ToListAsync();
            var totalProduction = await _db.Productions.SumAsync(p => (double?)p.Total) ?? 0;

            return new DbStatsResponse
            {
                Records = totalRecords,
                Lines = totalLines,
                Months = months,
                TotalProduction = Math.Round(totalProduction, 2),
                DbType = "PostgreSQL",
            };
        }
        catch
        {
            return null;
        }
    }
}
