using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace backend.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "manual_inputs",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    year = table.Column<int>(type: "integer", nullable: false),
                    month = table.Column<int>(type: "integer", nullable: false),
                    day = table.Column<int>(type: "integer", nullable: false),
                    field = table.Column<string>(type: "text", nullable: false),
                    value = table.Column<double>(type: "double precision", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_manual_inputs", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "production",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    line_name = table.Column<string>(type: "text", nullable: false),
                    category = table.Column<string>(type: "text", nullable: false),
                    year = table.Column<int>(type: "integer", nullable: false),
                    month = table.Column<int>(type: "integer", nullable: false),
                    day = table.Column<int>(type: "integer", nullable: false),
                    ca1 = table.Column<double>(type: "double precision", nullable: false),
                    ca2 = table.Column<double>(type: "double precision", nullable: false),
                    ca3 = table.Column<double>(type: "double precision", nullable: false),
                    total = table.Column<double>(type: "double precision", nullable: false),
                    cam_bot = table.Column<double>(type: "double precision", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_production", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "users",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    username = table.Column<string>(type: "text", nullable: false),
                    password = table.Column<string>(type: "text", nullable: false),
                    role = table.Column<string>(type: "text", nullable: false),
                    display_name = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_users", x => x.id);
                });

            migrationBuilder.InsertData(
                table: "users",
                columns: new[] { "id", "display_name", "password", "role", "username" },
                values: new object[,]
                {
                    { 1, "Mixer", "123", "user", "mixer" },
                    { 2, "Pellet Feedmill", "111", "user", "pellet feedmill" },
                    { 3, "Pellet Mini", "222", "user", "pellet mini" },
                    { 4, "Admin", "2810", "admin", "admin" }
                });

            migrationBuilder.CreateIndex(
                name: "IX_manual_inputs_year_month_day_field",
                table: "manual_inputs",
                columns: new[] { "year", "month", "day", "field" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_production_line_month",
                table: "production",
                columns: new[] { "line_name", "year", "month" });

            migrationBuilder.CreateIndex(
                name: "idx_production_month",
                table: "production",
                columns: new[] { "year", "month" });

            migrationBuilder.CreateIndex(
                name: "IX_production_line_name_year_month_day",
                table: "production",
                columns: new[] { "line_name", "year", "month", "day" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_users_username",
                table: "users",
                column: "username",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "manual_inputs");

            migrationBuilder.DropTable(
                name: "production");

            migrationBuilder.DropTable(
                name: "users");
        }
    }
}
