using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace backend.Models;

[Table("manual_inputs")]
public class ManualInput
{
    [Key]
    [Column("id")]
    public int Id { get; set; }

    [Column("year")]
    public int Year { get; set; }

    [Column("month")]
    public int Month { get; set; }

    [Column("day")]
    public int Day { get; set; }

    [Required]
    [Column("field")]
    public string Field { get; set; } = string.Empty;

    [Column("value")]
    public double Value { get; set; }
}
