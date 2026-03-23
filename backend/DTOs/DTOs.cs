namespace backend.DTOs;

public class LoginRequest
{
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
}

public class LoginResponse
{
    public string Token { get; set; } = string.Empty;
    public UserInfo User { get; set; } = null!;
}

public class UserInfo
{
    public int Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
}

public class ChangePasswordRequest
{
    public string NewPassword { get; set; } = string.Empty;
}

public class UploadRequest
{
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public List<UploadEntry> Entries { get; set; } = new();
}

public class UploadEntry
{
    public string LineName { get; set; } = string.Empty;
    public string Category { get; set; } = "Pellet Mill";
    public int Year { get; set; }
    public int Month { get; set; }
    public int Day { get; set; }
    public double Ca1 { get; set; }
    public double Ca2 { get; set; }
    public double Ca3 { get; set; }
    public double Total { get; set; }
    public double CamBot { get; set; }
}

public class ManualInputRequest
{
    public string Month { get; set; } = string.Empty; // "2026-01"
    public int Day { get; set; }
    public string Field { get; set; } = string.Empty; // "sale" or "stock"
    public double Value { get; set; }
}

public class DayData
{
    public int Day { get; set; }
    public double Ca1 { get; set; }
    public double Ca2 { get; set; }
    public double Ca3 { get; set; }
    public double Total { get; set; }
    public double? CamBot { get; set; }
}

public class LineInfo
{
    public string Name { get; set; } = string.Empty;
    public int Month { get; set; }
    public int Year { get; set; }
    public string MonthKey { get; set; } = string.Empty;
    public string Category { get; set; } = string.Empty;
    public List<DayData> Days { get; set; } = new();
    public SummaryData Summary { get; set; } = new();
}

public class SummaryData
{
    public double Ca1 { get; set; }
    public double Ca2 { get; set; }
    public double Ca3 { get; set; }
    public double Total { get; set; }
}

public class MonthOption
{
    public string Key { get; set; } = string.Empty;
    public string Label { get; set; } = string.Empty;
}

public class DataResponse
{
    public List<MonthOption> Months { get; set; } = new();
    public string SelectedMonth { get; set; } = string.Empty;
    public Dictionary<string, LineInfo> Lines { get; set; } = new();
    public double MonthlySaleTotal { get; set; }
}

public class ReportResponse
{
    public int Day { get; set; }
    public string Month { get; set; } = string.Empty;
    public ShiftData Mixer { get; set; } = new();
    public List<PelletData> Pellets { get; set; } = new();
    public ShiftData TotalPellet { get; set; } = new();
    public double? Sale { get; set; }
    public double? Stock { get; set; }
}

public class ShiftData
{
    public double Ca1 { get; set; }
    public double Ca2 { get; set; }
    public double Ca3 { get; set; }
    public double Total { get; set; }
    public double CamBot { get; set; }
}

public class PelletData
{
    public string Name { get; set; } = string.Empty;
    public double Ca1 { get; set; }
    public double Ca2 { get; set; }
    public double Ca3 { get; set; }
    public double Total { get; set; }
}

public class DbStatsResponse
{
    public int Records { get; set; }
    public int Lines { get; set; }
    public List<string> Months { get; set; } = new();
    public double TotalProduction { get; set; }
    public string DbType { get; set; } = "PostgreSQL";
}

public class UserListItem
{
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
}

public class UploadLogDto
{
    public string Username { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public int RecordsCount { get; set; }
    public DateTime UploadedAt { get; set; }
}

