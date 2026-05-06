using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace backend.Models;

[Table("production")]
public class Production
{
    [Key]
    [Column("id")]
    public int Id { get; set; }

    [Required]
    [Column("line_name")]
    public string LineName { get; set; } = string.Empty;

    [Required]
    [Column("category")]
    public string Category { get; set; } = string.Empty;

    [Column("year")]
    public int Year { get; set; }

    [Column("month")]
    public int Month { get; set; }

    [Column("day")]
    public int Day { get; set; }

    [Column("ca1")]
    public double Ca1 { get; set; }

    [Column("ca2")]
    public double Ca2 { get; set; }

    [Column("ca3")]
    public double Ca3 { get; set; }

    [Column("total")]
    public double Total { get; set; }

    [Column("cam_bot")]
    public double CamBot { get; set; }
}
