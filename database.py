"""
Database module - PostgreSQL (cloud) or SQLite (local) storage.
Uses DATABASE_URL env var for PostgreSQL, falls back to SQLite.
"""

import os
import sqlite3

# Try to import psycopg2 for PostgreSQL
try:
    import psycopg2
    import psycopg2.extras
    HAS_PG = True
except ImportError:
    HAS_PG = False

DB_NAME = "production.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "")


# ─── Connection helpers ────────────────────────────────────

def _use_postgres():
    """Check if we should use PostgreSQL."""
    return bool(DATABASE_URL) and HAS_PG


def _get_conn():
    """Get a database connection (PostgreSQL or SQLite)."""
    if _use_postgres():
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        data_dir = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(data_dir, DB_NAME)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn


def _execute(conn, sql, params=None):
    """Execute SQL with placeholder conversion for PG (%s) vs SQLite (?)."""
    if _use_postgres():
        sql = sql.replace("?", "%s")
        sql = sql.replace("INSERT OR REPLACE", "INSERT")
    c = conn.cursor()
    if params:
        c.execute(sql, params)
    else:
        c.execute(sql)
    return c


def _fetchone(cursor):
    """Fetch one row as dict."""
    row = cursor.fetchone()
    if row is None:
        return None
    if _use_postgres():
        cols = [desc[0] for desc in cursor.description]
        return dict(zip(cols, row))
    return dict(row)


def _fetchall(cursor):
    """Fetch all rows as list of dicts."""
    rows = cursor.fetchall()
    if _use_postgres():
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in rows]
    return [dict(row) for row in rows]


# ─── Upsert helper ────────────────────────────────────────

def _upsert_production(conn, line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot):
    """Insert or update production record."""
    if _use_postgres():
        c = conn.cursor()
        c.execute("""
            INSERT INTO production (line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (line_name, year, month, day)
            DO UPDATE SET category=EXCLUDED.category, ca1=EXCLUDED.ca1, ca2=EXCLUDED.ca2,
                          ca3=EXCLUDED.ca3, total=EXCLUDED.total, cam_bot=EXCLUDED.cam_bot
        """, (line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot))
    else:
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO production
            (line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot))
    return c


def _upsert_manual(conn, year, month, day, field, value):
    """Insert or update manual input."""
    if _use_postgres():
        c = conn.cursor()
        c.execute("""
            INSERT INTO manual_inputs (year, month, day, field, value)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (year, month, day, field)
            DO UPDATE SET value=EXCLUDED.value
        """, (year, month, day, field, value))
    else:
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO manual_inputs (year, month, day, field, value)
            VALUES (?, ?, ?, ?, ?)
        """, (year, month, day, field, value))
    return c


# ─── Init ──────────────────────────────────────────────────

def get_db_path(data_dir):
    """Return the full path to the SQLite database."""
    return os.path.join(data_dir, DB_NAME)


def init_db(data_dir=None):
    """Create tables if they don't exist."""
    conn = _get_conn()
    c = conn.cursor()

    if _use_postgres():
        # PostgreSQL syntax
        c.execute("""
            CREATE TABLE IF NOT EXISTS production (
                id SERIAL PRIMARY KEY,
                line_name TEXT NOT NULL,
                category TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                ca1 REAL DEFAULT 0,
                ca2 REAL DEFAULT 0,
                ca3 REAL DEFAULT 0,
                total REAL DEFAULT 0,
                cam_bot REAL DEFAULT 0,
                UNIQUE(line_name, year, month, day)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS manual_inputs (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                field TEXT NOT NULL,
                value REAL DEFAULT 0,
                UNIQUE(year, month, day, field)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                display_name TEXT NOT NULL
            )
        """)
        # Create indexes (IF NOT EXISTS for PG)
        c.execute("CREATE INDEX IF NOT EXISTS idx_production_month ON production(year, month)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_production_line_month ON production(line_name, year, month)")
    else:
        # SQLite syntax
        c.execute("""
            CREATE TABLE IF NOT EXISTS production (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_name TEXT NOT NULL,
                category TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                ca1 REAL DEFAULT 0,
                ca2 REAL DEFAULT 0,
                ca3 REAL DEFAULT 0,
                total REAL DEFAULT 0,
                cam_bot REAL DEFAULT 0,
                UNIQUE(line_name, year, month, day)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS manual_inputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                field TEXT NOT NULL,
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_production_month ON production(year, month)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_production_line_month ON production(line_name, year, month)")

    conn.commit()

    # Insert default users if table is empty
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0] if not _use_postgres() else c.fetchone()[0]
    if count == 0:
        default_users = [
            ("mixer", "123", "user", "Mixer"),
            ("pellet feedmill", "111", "user", "Pellet Feedmill"),
            ("pellet mini", "222", "user", "Pellet Mini"),
            ("admin", "2810", "admin", "Admin"),
        ]
        if _use_postgres():
            for u in default_users:
                c.execute("INSERT INTO users (username, password, role, display_name) VALUES (%s, %s, %s, %s)", u)
        else:
            c.executemany(
                "INSERT INTO users (username, password, role, display_name) VALUES (?, ?, ?, ?)",
                default_users,
            )
        conn.commit()
        print("✅ Default users created")

    conn.close()
    db_type = "PostgreSQL" if _use_postgres() else "SQLite"
    print(f"✅ Database initialized: {db_type}")


# ─── Auth ──────────────────────────────────────────────────

def authenticate(data_dir, username, password):
    """Check username/password. Returns user dict or None."""
    conn = _get_conn()
    c = _execute(conn,
        "SELECT id, username, role, display_name FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    row = _fetchone(c)
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"],
                "role": row["role"], "display_name": row["display_name"]}
    return None


def change_password(data_dir, username, new_password):
    """Change password for a user."""
    conn = _get_conn()
    c = _execute(conn, "UPDATE users SET password = ? WHERE username = ?", (new_password, username))
    conn.commit()
    changed = c.rowcount > 0
    conn.close()
    return changed


def get_all_users(data_dir):
    """Get all users (admin view)."""
    conn = _get_conn()
    c = _execute(conn, "SELECT username, password, role, display_name FROM users ORDER BY role DESC, username")
    users = _fetchall(c)
    conn.close()
    return users


# ─── Manual Inputs (Sale/Stock) ────────────────────────────

def save_manual_input(data_dir, year, month, day, field, value):
    """Save a manual input (sale/stock) for a specific day."""
    conn = _get_conn()
    _upsert_manual(conn, year, month, day, field, value)
    conn.commit()
    conn.close()


def get_manual_inputs(data_dir, year, month, day):
    """Get manual inputs (sale/stock) for a specific day."""
    conn = _get_conn()
    c = _execute(conn, """
        SELECT field, value FROM manual_inputs
        WHERE year = ? AND month = ? AND day = ?
    """, (year, month, day))
    rows = c.fetchall()
    if _use_postgres():
        result = {row[0]: row[1] for row in rows}
    else:
        result = {row[0]: row[1] for row in rows}
    conn.close()
    return result


def get_monthly_sale_total(data_dir, year, month):
    """Get total SALE for a month."""
    conn = _get_conn()
    c = _execute(conn, """
        SELECT COALESCE(SUM(value), 0) FROM manual_inputs
        WHERE year = ? AND month = ? AND field = 'sale'
    """, (year, month))
    total = c.fetchone()[0]
    conn.close()
    return round(total, 1)


# ─── Upload API ────────────────────────────────────────────

USER_LINE_PERMISSIONS = {
    "mixer": ["MIXER"],
    "pellet feedmill": ["PL1", "PL2", "PL3", "PL4", "PL5"],
    "pellet mini": ["PL6", "PL7"],
    "admin": ["MIXER", "PL1", "PL2", "PL3", "PL4", "PL5", "PL6", "PL7"],
}


def save_uploaded_data(data_dir, username, entries):
    """Save production data uploaded from a client PC."""
    allowed_lines = USER_LINE_PERMISSIONS.get(username, [])
    if not allowed_lines:
        return {"status": "error", "message": f"User '{username}' không có quyền upload"}

    conn = _get_conn()
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
            _upsert_production(
                conn, line_name,
                entry.get("category", "Pellet Mill"),
                int(entry["year"]), int(entry["month"]), int(entry["day"]),
                float(entry.get("ca1", 0)), float(entry.get("ca2", 0)),
                float(entry.get("ca3", 0)), float(entry.get("total", 0)),
                float(entry.get("cam_bot", 0)),
            )
            inserted += 1
        except Exception as e:
            errors.append(f"{line_name} day {entry.get('day')}: {str(e)}")

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors[:10],
    }


# ─── Excel Import (local only) ────────────────────────────

def import_from_excel(data_dir):
    """Read all Excel files and import into database."""
    from data_loader import load_all_data
    print("📂 Importing data from Excel files...")

    result = load_all_data(data_dir)
    conn = _get_conn()

    count = 0
    for month_key, lines in result["data"].items():
        for line_name, line_info in lines.items():
            year = line_info["year"]
            month = line_info["month"]
            category = line_info["category"]

            for day_data in line_info["days"]:
                _upsert_production(
                    conn, line_name, category, year, month,
                    day_data["day"], day_data["ca1"], day_data["ca2"],
                    day_data["ca3"], day_data["total"],
                    day_data.get("cam_bot", 0),
                )
                count += 1

    conn.commit()
    conn.close()
    print(f"✅ Imported {count} records")
    return count


def import_month_from_excel(data_dir, month_key):
    """Import only files for a specific month."""
    from data_loader import FILE_CONFIGS, _parse_file
    import glob

    parts = month_key.split("-")
    target_year = int(parts[0])
    target_month = int(parts[1])

    print(f"📂 Importing Excel data for month {target_month}/{target_year}...")

    conn = _get_conn()
    count = 0

    for config_key, config in FILE_CONFIGS.items():
        pattern = os.path.join(data_dir, config["pattern"])
        files = sorted(glob.glob(pattern))

        for filepath in files:
            entry = _parse_file(filepath, config)
            if entry and entry["year"] == target_year and entry["month"] == target_month:
                for day_data in entry["days"]:
                    _upsert_production(
                        conn, entry["name"], entry["category"],
                        target_year, target_month,
                        day_data["day"], day_data["ca1"], day_data["ca2"],
                        day_data["ca3"], day_data["total"],
                        day_data.get("cam_bot", 0),
                    )
                    count += 1

    conn.commit()
    conn.close()
    print(f"✅ Imported {count} records for {target_month}/{target_year}")
    return count


# ─── Load Data ─────────────────────────────────────────────

def load_all_from_db(data_dir):
    """Load all production data from database."""
    conn = _get_conn()
    c = _execute(conn, """
        SELECT line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot
        FROM production
        ORDER BY year, month, line_name, day
    """)
    rows = _fetchall(c)
    conn.close()

    # Group into structure
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
    """Get database statistics."""
    conn = _get_conn()
    c = conn.cursor()

    try:
        if _use_postgres():
            c.execute("SELECT COUNT(*) FROM production")
            total_records = c.fetchone()[0]
            c.execute("SELECT COUNT(DISTINCT line_name) FROM production")
            total_lines = c.fetchone()[0]
            c.execute("SELECT DISTINCT year, month FROM production ORDER BY year DESC, month DESC")
            months = [f"{r[0]}-{r[1]:02d}" for r in c.fetchall()]
            c.execute("SELECT COALESCE(SUM(total), 0) FROM production")
            total_production = c.fetchone()[0]
        else:
            c.execute("SELECT COUNT(*) FROM production")
            total_records = c.fetchone()[0]
            c.execute("SELECT COUNT(DISTINCT line_name) FROM production")
            total_lines = c.fetchone()[0]
            c.execute("SELECT DISTINCT year, month FROM production ORDER BY year DESC, month DESC")
            months = [f"{r[0]}-{r[1]:02d}" for r in c.fetchall()]
            c.execute("SELECT SUM(total) FROM production")
            total_production = c.fetchone()[0] or 0

        conn.close()
        return {
            "records": total_records,
            "lines": total_lines,
            "months": months,
            "total_production": round(total_production, 2),
            "db_type": "PostgreSQL" if _use_postgres() else "SQLite",
        }
    except Exception:
        conn.close()
        return None


if __name__ == "__main__":
    data_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 50)
    print("  Database Setup")
    print("=" * 50)

    init_db(data_dir)
    count = import_from_excel(data_dir)

    stats = get_db_stats(data_dir)
    if stats:
        print(f"\n📊 Database Stats ({stats['db_type']}):")
        print(f"   Records: {stats['records']}")
        print(f"   Lines: {stats['lines']}")
        print(f"   Months: {', '.join(stats['months'])}")
        print(f"   Total Production: {stats['total_production']:,.1f} tấn")
