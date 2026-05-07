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
        c.execute("""
            CREATE TABLE IF NOT EXISTS nvvh (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                ca TEXT NOT NULL,
                pl_group TEXT NOT NULL,
                names TEXT NOT NULL DEFAULT '',
                UNIQUE(year, month, day, ca, pl_group)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS loss_notes (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                pl_num INTEGER NOT NULL,
                code TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                ca1_count INTEGER DEFAULT 0,
                ca1_time INTEGER DEFAULT 0,
                ca2_count INTEGER DEFAULT 0,
                ca2_time INTEGER DEFAULT 0,
                ca3_count INTEGER DEFAULT 0,
                ca3_time INTEGER DEFAULT 0,
                UNIQUE(year, month, day, pl_num, code)
            )
        """)
        # Create indexes (IF NOT EXISTS for PG)
        c.execute("CREATE INDEX IF NOT EXISTS idx_production_month ON production(year, month)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_production_line_month ON production(line_name, year, month)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_nvvh_day ON nvvh(year, month, day)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_loss_day ON loss_notes(year, month, day)")
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
        c.execute("""
            CREATE TABLE IF NOT EXISTS nvvh (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                ca TEXT NOT NULL,
                pl_group TEXT NOT NULL,
                names TEXT NOT NULL DEFAULT '',
                UNIQUE(year, month, day, ca, pl_group)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS loss_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                pl_num INTEGER NOT NULL,
                code TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                ca1_count INTEGER DEFAULT 0,
                ca1_time INTEGER DEFAULT 0,
                ca2_count INTEGER DEFAULT 0,
                ca2_time INTEGER DEFAULT 0,
                ca3_count INTEGER DEFAULT 0,
                ca3_time INTEGER DEFAULT 0,
                UNIQUE(year, month, day, pl_num, code)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_production_month ON production(year, month)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_production_line_month ON production(line_name, year, month)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_nvvh_day ON nvvh(year, month, day)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_loss_day ON loss_notes(year, month, day)")

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


def save_uploaded_data(data_dir, username, entries, nvvh_entries=None, loss_entries=None):
    """Save production, NVVH, and LOSS data uploaded from a client PC."""
    conn = _get_conn()
    inserted = 0
    skipped = 0
    errors = []

    # Production data
    for entry in entries:
        line_name = entry.get("line_name", "").upper()

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

    # NVVH data
    nvvh_count = 0
    for nv in (nvvh_entries or []):
        try:
            params = (int(nv["year"]), int(nv["month"]), int(nv["day"]),
                      nv["ca"], nv["pl_group"], nv["names"])
            if _use_postgres():
                c = conn.cursor()
                c.execute("""
                    INSERT INTO nvvh (year, month, day, ca, pl_group, names)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (year, month, day, ca, pl_group)
                    DO UPDATE SET names=EXCLUDED.names
                """, params)
            else:
                _execute(conn, """
                    INSERT OR REPLACE INTO nvvh (year, month, day, ca, pl_group, names)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, params)
            nvvh_count += 1
        except Exception as e:
            errors.append(f"NVVH day {nv.get('day')}: {str(e)}")

    # LOSS data
    loss_count = 0
    for lo in (loss_entries or []):
        try:
            params = (int(lo["year"]), int(lo["month"]), int(lo["day"]),
                      int(lo["pl_num"]), lo["code"], lo.get("description", ""),
                      int(lo.get("ca1_count", 0)), int(lo.get("ca1_time", 0)),
                      int(lo.get("ca2_count", 0)), int(lo.get("ca2_time", 0)),
                      int(lo.get("ca3_count", 0)), int(lo.get("ca3_time", 0)))
            if _use_postgres():
                c = conn.cursor()
                c.execute("""
                    INSERT INTO loss_notes
                    (year, month, day, pl_num, code, description,
                     ca1_count, ca1_time, ca2_count, ca2_time, ca3_count, ca3_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (year, month, day, pl_num, code)
                    DO UPDATE SET description=EXCLUDED.description,
                        ca1_count=EXCLUDED.ca1_count, ca1_time=EXCLUDED.ca1_time,
                        ca2_count=EXCLUDED.ca2_count, ca2_time=EXCLUDED.ca2_time,
                        ca3_count=EXCLUDED.ca3_count, ca3_time=EXCLUDED.ca3_time
                """, params)
            else:
                _execute(conn, """
                    INSERT OR REPLACE INTO loss_notes
                    (year, month, day, pl_num, code, description,
                     ca1_count, ca1_time, ca2_count, ca2_time, ca3_count, ca3_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, params)
            loss_count += 1
        except Exception as e:
            errors.append(f"LOSS PL{lo.get('pl_num')} day {lo.get('day')}: {str(e)}")

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "inserted": inserted,
        "nvvh_count": nvvh_count,
        "loss_count": loss_count,
        "skipped": skipped,
        "errors": errors[:10],
    }


# ─── Excel Import (local only) ────────────────────────────

def import_from_excel(data_dir, source_dir=None):
    """Read all Excel files and import into database.
    source_dir: folder containing Excel files (defaults to data_dir).
    """
    from data_loader import load_all_data
    excel_dir = source_dir or data_dir
    print(f"📂 Importing data from: {excel_dir}")

    result = load_all_data(excel_dir)
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
    print(f"✅ Imported {count} production records")

    # Also import NVVH + LOSS
    import_nvvh_loss_from_excel(excel_dir)

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
        # Search in data_dir and data_dir/Update
        all_files = []
        for search_dir in [data_dir, os.path.join(data_dir, "Update")]:
            pattern = os.path.join(search_dir, config["pattern"])
            all_files.extend(glob.glob(pattern))
        files = sorted(set(all_files))

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


# ─── NVVH + LOSS DB functions ──────────────────────────────

def import_nvvh_loss_from_excel(source_dir):
    """Import NVVH and LOSS data from PL and MIXER Excel files into database."""
    from data_loader import load_nvvh_for_day, load_loss_for_day, _find_pl_file
    import glob
    import re as regex

    # Detect which months are available from PL and MIXER files (recursive)
    months_found = set()
    for pattern in ["PL* *.xls*", "MIXER*.xls*"]:
        for f in glob.glob(os.path.join(source_dir, "**", pattern), recursive=True):
            basename = os.path.basename(f)
            if basename.startswith('~$'):
                continue
            match = regex.search(r'(\d+)\.(\d{4})', basename)
            if match:
                months_found.add((int(match.group(1)), int(match.group(2))))
    # Also check flat directory
    for pattern in ["PL* *.xls*", "MIXER*.xls*"]:
        for f in glob.glob(os.path.join(source_dir, pattern)):
            basename = os.path.basename(f)
            if basename.startswith('~$'):
                continue
            match = regex.search(r'(\d+)\.(\d{4})', basename)
            if match:
                months_found.add((int(match.group(1)), int(match.group(2))))

    conn = _get_conn()
    nvvh_count = 0
    loss_count = 0

    for month, year in months_found:
        print(f"📋 Importing NVVH/LOSS for {month}/{year}...")

        for day in range(1, 32):
            # NVVH
            try:
                nvvh = load_nvvh_for_day(source_dir, month, year, day)
                if nvvh:
                    for ca in ['ca1', 'ca2', 'ca3']:
                        # PL1-5 names
                        names15 = nvvh.get('pl1_5', {}).get(ca, [])
                        if names15:
                            _execute(conn, """
                                INSERT OR REPLACE INTO nvvh (year, month, day, ca, pl_group, names)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (year, month, day, ca, 'pl1_5', ','.join(names15)))
                            nvvh_count += 1
                        # PL6-7 name
                        name67 = nvvh.get('pl6_7', {}).get(ca, '')
                        if name67:
                            _execute(conn, """
                                INSERT OR REPLACE INTO nvvh (year, month, day, ca, pl_group, names)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (year, month, day, ca, 'pl6_7', name67))
                            nvvh_count += 1
            except Exception as e:
                pass  # Skip days that don't exist in Excel

            # LOSS
            try:
                loss = load_loss_for_day(source_dir, month, year, day)
                if loss:
                    for pl_str, entries in loss.items():
                        pl_num = int(pl_str)
                        for entry in entries:
                            _execute(conn, """
                                INSERT OR REPLACE INTO loss_notes
                                (year, month, day, pl_num, code, description,
                                 ca1_count, ca1_time, ca2_count, ca2_time, ca3_count, ca3_time)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (year, month, day, pl_num, entry['code'], entry['desc'],
                                  entry['ca1_count'], entry['ca1_time'],
                                  entry['ca2_count'], entry['ca2_time'],
                                  entry['ca3_count'], entry['ca3_time']))
                            loss_count += 1
            except Exception as e:
                pass

        conn.commit()

    conn.close()
    print(f"✅ Imported {nvvh_count} NVVH + {loss_count} LOSS records")


def get_nvvh_for_day(year, month, day):
    """Read NVVH from database for a specific day."""
    conn = _get_conn()
    cursor = _execute(conn, """
        SELECT ca, pl_group, names FROM nvvh
        WHERE year=? AND month=? AND day=?
    """, (year, month, day))
    rows = _fetchall(cursor)
    conn.close()

    result = {
        "pl1_5": {"ca1": [], "ca2": [], "ca3": []},
        "pl6_7": {"ca1": "", "ca2": "", "ca3": ""},
        "mixer": {"ca1": "", "ca2": "", "ca3": ""},
    }
    for row in rows:
        ca = row['ca']
        group = row['pl_group']
        names = row['names']
        if group == 'pl1_5':
            result['pl1_5'][ca] = [n.strip() for n in names.split(',') if n.strip()]
        elif group == 'pl6_7':
            result['pl6_7'][ca] = names
        elif group == 'mixer':
            result['mixer'][ca] = names

    return result


def get_loss_for_day(year, month, day):
    """Read LOSS from database for a specific day."""
    conn = _get_conn()
    cursor = _execute(conn, """
        SELECT pl_num, code, description, ca1_count, ca1_time,
               ca2_count, ca2_time, ca3_count, ca3_time
        FROM loss_notes
        WHERE year=? AND month=? AND day=?
        ORDER BY pl_num, code
    """, (year, month, day))
    rows = _fetchall(cursor)
    conn.close()

    result = {str(i): [] for i in range(0, 8)}  # 0=Mixer, 1-7=PL
    for row in rows:
        pl_key = str(row['pl_num'])
        if pl_key in result:
            result[pl_key].append({
                'code': row['code'],
                'desc': row['description'],
                'ca1_count': row['ca1_count'],
                'ca1_time': row['ca1_time'],
                'ca2_count': row['ca2_count'],
                'ca2_time': row['ca2_time'],
                'ca3_count': row['ca3_count'],
                'ca3_time': row['ca3_time'],
            })

    return result


if __name__ == "__main__":
    import sys
    data_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = sys.argv[1] if len(sys.argv) > 1 else data_dir

    print("=" * 50)
    print("  Database Setup")
    print(f"  Source: {source_dir}")
    print("=" * 50)

    init_db(data_dir)
    count = import_from_excel(data_dir, source_dir)

    stats = get_db_stats(data_dir)
    if stats:
        print(f"\n📊 Database Stats ({stats['db_type']}):")
        print(f"   Records: {stats['records']}")
        print(f"   Lines: {stats['lines']}")
        print(f"   Months: {', '.join(stats['months'])}")
        print(f"   Total Production: {stats['total_production']:,.1f} tấn")
