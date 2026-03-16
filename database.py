"""
Database module - SQLite storage for production data.
Reads Excel data once and stores in SQLite for fast queries.
Database file: production.db (in project root)
Can be viewed with DB Browser for SQLite.
"""

import os
import sqlite3
from data_loader import load_all_data, FILE_CONFIGS, _parse_file
import re
import glob


DB_NAME = "production.db"


def get_db_path(data_dir):
    """Return the full path to the SQLite database."""
    return os.path.join(data_dir, DB_NAME)


def init_db(data_dir):
    """Create tables if they don't exist."""
    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_name TEXT NOT NULL,       -- PL1, PL2, ..., MIXER
            category TEXT NOT NULL,        -- Pellet Mill, Mixer
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            ca1 REAL DEFAULT 0,
            ca2 REAL DEFAULT 0,
            ca3 REAL DEFAULT 0,
            total REAL DEFAULT 0,
            cam_bot REAL DEFAULT 0,        -- MIXER only: cám bột
            UNIQUE(line_name, year, month, day)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS manual_inputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            field TEXT NOT NULL,           -- 'sale' or 'stock'
            value REAL DEFAULT 0,
            UNIQUE(year, month, day, field)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            display_name TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_production_month
        ON production(year, month)
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_production_line_month
        ON production(line_name, year, month)
    """)

    conn.commit()

    # Insert default users if table is empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        default_users = [
            ("mixer", "123", "user", "Mixer"),
            ("pellet feedmill", "111", "user", "Pellet Feedmill"),
            ("pellet mini", "222", "user", "Pellet Mini"),
            ("admin", "2810", "admin", "Admin"),
        ]
        c.executemany(
            "INSERT INTO users (username, password, role, display_name) VALUES (?, ?, ?, ?)",
            default_users,
        )
        conn.commit()
        print("✅ Default users created")

    conn.close()
    print(f"✅ Database initialized: {db_path}")


def authenticate(data_dir, username, password):
    """Check username/password. Returns user dict or None."""
    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT id, username, role, display_name FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"],
                "role": row["role"], "display_name": row["display_name"]}
    return None


def change_password(data_dir, username, new_password):
    """Change password for a user."""
    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
    conn.commit()
    changed = c.rowcount > 0
    conn.close()
    return changed


def get_all_users(data_dir):
    """Get all users (admin view). Returns list of user dicts WITH passwords."""
    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT username, password, role, display_name FROM users ORDER BY role DESC, username")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return users


def save_manual_input(data_dir, year, month, day, field, value):
    """Save a manual input (sale/stock) for a specific day."""
    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO manual_inputs (year, month, day, field, value)
        VALUES (?, ?, ?, ?, ?)
    """, (year, month, day, field, value))
    conn.commit()
    conn.close()


def get_manual_inputs(data_dir, year, month, day):
    """Get manual inputs (sale/stock) for a specific day."""
    db_path = get_db_path(data_dir)
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT field, value FROM manual_inputs
        WHERE year = ? AND month = ? AND day = ?
    """, (year, month, day))
    result = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return result


def get_monthly_sale_total(data_dir, year, month):
    """Get total SALE for a month (sum of all daily sale inputs)."""
    db_path = get_db_path(data_dir)
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT COALESCE(SUM(value), 0) FROM manual_inputs
        WHERE year = ? AND month = ? AND field = 'sale'
    """, (year, month))
    total = c.fetchone()[0]
    conn.close()
    return round(total, 1)
# Permission mapping: which user can upload which lines
USER_LINE_PERMISSIONS = {
    "mixer": ["MIXER"],
    "pellet feedmill": ["PL1", "PL2", "PL3", "PL4", "PL5"],
    "pellet mini": ["PL6", "PL7"],
    "admin": ["MIXER", "PL1", "PL2", "PL3", "PL4", "PL5", "PL6", "PL7"],
}


def save_uploaded_data(data_dir, username, entries):
    """
    Save production data uploaded from a client PC.
    
    Args:
        data_dir: path to database directory
        username: authenticated user
        entries: list of dicts, each with:
            {line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot?}
    
    Returns:
        dict with status, inserted/updated count, and any errors
    """
    allowed_lines = USER_LINE_PERMISSIONS.get(username, [])
    if not allowed_lines:
        return {"status": "error", "message": f"User '{username}' không có quyền upload"}

    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    inserted = 0
    skipped = 0
    errors = []

    for entry in entries:
        line_name = entry.get("line_name", "").upper()
        if line_name not in allowed_lines:
            skipped += 1
            errors.append(f"{line_name}: không có quyền")
            continue

        try:
            c.execute("""
                INSERT OR REPLACE INTO production
                (line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                line_name,
                entry.get("category", "Pellet Mill"),
                int(entry["year"]),
                int(entry["month"]),
                int(entry["day"]),
                float(entry.get("ca1", 0)),
                float(entry.get("ca2", 0)),
                float(entry.get("ca3", 0)),
                float(entry.get("total", 0)),
                float(entry.get("cam_bot", 0)),
            ))
            inserted += 1
        except Exception as e:
            errors.append(f"{line_name} day {entry.get('day')}: {str(e)}")

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors[:10],  # limit error messages
    }


def import_from_excel(data_dir):
    """
    Read all Excel files and import/update data into SQLite.
    Uses INSERT OR REPLACE to update existing records.
    """
    print("📂 Importing data from Excel files into SQLite...")

    # Load data from Excel
    result = load_all_data(data_dir)

    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    count = 0
    for month_key, lines in result["data"].items():
        for line_name, line_info in lines.items():
            year = line_info["year"]
            month = line_info["month"]
            category = line_info["category"]

            for day_data in line_info["days"]:
                c.execute("""
                    INSERT OR REPLACE INTO production
                    (line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    line_name,
                    category,
                    year,
                    month,
                    day_data["day"],
                    day_data["ca1"],
                    day_data["ca2"],
                    day_data["ca3"],
                    day_data["total"],
                    day_data.get("cam_bot", 0),
                ))
                count += 1

    conn.commit()
    conn.close()
    print(f"✅ Imported {count} records into {db_path}")
    return count


def import_month_from_excel(data_dir, month_key):
    """
    Import only files for a specific month (e.g. '2026-03').
    Much faster than import_from_excel() which reads ALL files.
    """
    parts = month_key.split("-")
    target_year = int(parts[0])
    target_month = int(parts[1])

    print(f"📂 Importing Excel data for month {target_month}/{target_year}...")

    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    count = 0
    for config_key, config in FILE_CONFIGS.items():
        pattern = os.path.join(data_dir, config["pattern"])
        files = sorted(glob.glob(pattern))

        for filepath in files:
            entry = _parse_file(filepath, config)
            if entry and entry["year"] == target_year and entry["month"] == target_month:
                for day_data in entry["days"]:
                    c.execute("""
                        INSERT OR REPLACE INTO production
                        (line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry["name"],
                        entry["category"],
                        target_year,
                        target_month,
                        day_data["day"],
                        day_data["ca1"],
                        day_data["ca2"],
                        day_data["ca3"],
                        day_data["total"],
                        day_data.get("cam_bot", 0),
                    ))
                    count += 1

    conn.commit()
    conn.close()
    print(f"✅ Imported {count} records for {target_month}/{target_year}")
    return count


def load_all_from_db(data_dir):
    """
    Load all production data from SQLite.
    Returns the same structure as load_all_data() for compatibility.
    """
    db_path = get_db_path(data_dir)

    if not os.path.exists(db_path):
        return {"months": [], "data": {}}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get all records ordered by line, year, month, day
    c.execute("""
        SELECT line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot
        FROM production
        ORDER BY year, month, line_name, day
    """)

    rows = c.fetchall()
    conn.close()

    # Group into the same structure as Excel loader
    data_by_month = {}

    for row in rows:
        year = row["year"]
        month = row["month"]
        mk = f"{year}-{month:02d}"
        line_name = row["line_name"]

        if mk not in data_by_month:
            data_by_month[mk] = {}

        if line_name not in data_by_month[mk]:
            data_by_month[mk][line_name] = {
                "name": line_name,
                "month": month,
                "year": year,
                "month_key": mk,
                "category": row["category"],
                "days": [],
                "summary": {"ca1": 0, "ca2": 0, "ca3": 0, "total": 0},
            }

        entry = data_by_month[mk][line_name]
        day_data = {
            "day": row["day"],
            "ca1": round(row["ca1"], 2),
            "ca2": round(row["ca2"], 2),
            "ca3": round(row["ca3"], 2),
            "total": round(row["total"], 2),
        }

        # Add cam_bot for MIXER
        if row["cam_bot"] and row["cam_bot"] != 0:
            day_data["cam_bot"] = round(row["cam_bot"], 2)

        entry["days"].append(day_data)

    # Calculate summaries
    for mk, lines in data_by_month.items():
        for line_name, info in lines.items():
            info["summary"] = {
                "ca1": round(sum(d["ca1"] for d in info["days"]), 2),
                "ca2": round(sum(d["ca2"] for d in info["days"]), 2),
                "ca3": round(sum(d["ca3"] for d in info["days"]), 2),
                "total": round(sum(d["total"] for d in info["days"]), 2),
            }

    sorted_months = sorted(data_by_month.keys(), reverse=True)

    return {
        "months": sorted_months,
        "data": data_by_month,
    }


def get_db_stats(data_dir):
    """Get database statistics for display."""
    db_path = get_db_path(data_dir)

    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM production")
    total_records = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT line_name) FROM production")
    total_lines = c.fetchone()[0]

    c.execute("SELECT DISTINCT year, month FROM production ORDER BY year DESC, month DESC")
    months = [f"{r[0]}-{r[1]:02d}" for r in c.fetchall()]

    c.execute("SELECT SUM(total) FROM production")
    total_production = c.fetchone()[0] or 0

    # File size
    file_size = os.path.getsize(db_path)

    conn.close()

    return {
        "records": total_records,
        "lines": total_lines,
        "months": months,
        "total_production": round(total_production, 2),
        "file_size_kb": round(file_size / 1024, 1),
        "db_path": db_path,
    }


if __name__ == "__main__":
    data_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 50)
    print("  SQLite Database Setup")
    print("=" * 50)

    # 1. Initialize database
    init_db(data_dir)

    # 2. Import from Excel
    count = import_from_excel(data_dir)

    # 3. Show stats
    stats = get_db_stats(data_dir)
    if stats:
        print(f"\n📊 Database Stats:")
        print(f"   Records: {stats['records']}")
        print(f"   Lines: {stats['lines']}")
        print(f"   Months: {', '.join(stats['months'])}")
        print(f"   Total Production: {stats['total_production']:,.1f} tấn")
        print(f"   File Size: {stats['file_size_kb']} KB")
        print(f"   Path: {stats['db_path']}")

    # 4. Verification - load back from DB
    print("\n🔍 Verifying data from database...")
    result = load_all_from_db(data_dir)
    for mk in result["months"]:
        lines = result["data"][mk]
        total = sum(info["summary"]["total"] for info in lines.values())
        m, y = mk.split("-")
        print(f"  Tháng {int(m)}/{y}: {len(lines)} dây chuyền — {total:,.1f} tấn")
