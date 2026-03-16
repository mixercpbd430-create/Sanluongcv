"""
Data loader module - Reads production data from Excel files.
Supports two file types:
  1. PL files (PL1-PL7): sheet "SAN LUONG (2)", cols A:E, rows 9-39
  2. MIXER files: sheet "SAN LUONG", cols B:F, rows 8-38

Returns data grouped by month/year for filtering.
"""

import os
import re
import glob
import pandas as pd


# File type configurations
FILE_CONFIGS = {
    "PL": {
        "pattern": "PL*.xlsx",
        "regex": r"(PL\d+)\s+(\d+)\.(\d+)\.xlsx",
        "sheet_name": "SAN LUONG (2)",
        "usecols": "A:E",
        "skiprows": 8,
        "category": "Pellet Mill",
    },
    "MIXER": {
        "pattern": "MIXER*.xls*",
        "regex": r"(MIXER)\s+T(\d+)\.(\d+)\.(xlsx|xlsm)",
        "sheet_name": "SAN LUONG",
        "usecols": "B:F",
        "skiprows": 7,
        "category": "Mixer",
        "extra_col": "AL",  # Column AL = Sản lượng cám bột
    },
}


def _parse_file(filepath, config):
    """Parse a single Excel file based on its config."""
    filename = os.path.basename(filepath)
    match = re.match(config["regex"], filename, re.IGNORECASE)
    if not match:
        return None

    line_name = match.group(1).upper()
    month = int(match.group(2))
    year = int(match.group(3))

    try:
        df = pd.read_excel(
            filepath,
            sheet_name=config["sheet_name"],
            header=None,
            usecols=config["usecols"],
            skiprows=config["skiprows"],
            nrows=31,
        )
        df.columns = ["day", "ca1", "ca2", "ca3", "total"]
        df = df.fillna(0)

        days = []
        for _, row in df.iterrows():
            day_num = int(row["day"]) if row["day"] else 0
            if day_num < 1 or day_num > 31:
                continue
            days.append({
                "day": day_num,
                "ca1": round(float(row["ca1"]), 2),
                "ca2": round(float(row["ca2"]), 2),
                "ca3": round(float(row["ca3"]), 2),
                "total": round(float(row["total"]), 2),
            })

        summary = {
            "ca1": round(sum(d["ca1"] for d in days), 2),
            "ca2": round(sum(d["ca2"] for d in days), 2),
            "ca3": round(sum(d["ca3"] for d in days), 2),
            "total": round(sum(d["total"] for d in days), 2),
        }

        result = {
            "name": line_name,
            "month": month,
            "year": year,
            "month_key": f"{year}-{month:02d}",
            "category": config["category"],
            "days": days,
            "summary": summary,
        }

        # Read extra column if configured (e.g., MIXER column AL = cám bột)
        extra_col = config.get("extra_col")
        if extra_col:
            try:
                df_extra = pd.read_excel(
                    filepath,
                    sheet_name=config["sheet_name"],
                    header=None,
                    usecols=extra_col,
                    skiprows=config["skiprows"],
                    nrows=31,
                )
                for idx, row in df_extra.iterrows():
                    day_idx = idx  # 0-based
                    if day_idx < len(days):
                        val = row.iloc[0]
                        days[day_idx]["cam_bot"] = round(float(val) if val else 0, 2)
            except Exception:
                pass

        return result

    except Exception as e:
        print(f"Warning: Could not read {filename}: {e}")
        return None


def load_all_data(data_dir):
    """
    Load ALL production Excel files from data_dir.
    Returns:
    {
        "months": ["2026-01", "2026-02"],   # sorted list of available months
        "data": {
            "2026-01": {
                "PL1": {...}, "PL2": {...}, ...
            },
            "2026-02": {
                "MIXER": {...}, ...
            }
        }
    }
    """
    all_entries = []

    for config_key, config in FILE_CONFIGS.items():
        pattern = os.path.join(data_dir, config["pattern"])
        files = sorted(glob.glob(pattern))

        for filepath in files:
            entry = _parse_file(filepath, config)
            if entry:
                all_entries.append(entry)

    # Group by month_key
    data_by_month = {}
    for entry in all_entries:
        mk = entry["month_key"]
        if mk not in data_by_month:
            data_by_month[mk] = {}
        data_by_month[mk][entry["name"]] = entry

    # Sort months descending (newest first)
    sorted_months = sorted(data_by_month.keys(), reverse=True)

    return {
        "months": sorted_months,
        "data": data_by_month,
    }


def get_latest_month_data(data_dir):
    """Load data and return only the latest month."""
    result = load_all_data(data_dir)
    if result["months"]:
        latest = result["months"][0]
        return result["data"][latest], latest
    return {}, None


if __name__ == "__main__":
    result = load_all_data(os.path.dirname(os.path.abspath(__file__)))
    print(f"Available months: {result['months']}")
    for mk in result["months"]:
        lines = result["data"][mk]
        total = sum(info["summary"]["total"] for info in lines.values())
        m, y = mk.split("-")
        print(f"\nTháng {int(m)}/{y} — {len(lines)} dây chuyền — Tổng: {total:,.1f} tấn")
        for ln, info in lines.items():
            print(f"  {ln}: {info['summary']['total']:,.1f} tấn ({sum(1 for d in info['days'] if d['total'] > 0)} ngày)")
