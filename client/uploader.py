"""
Client Uploader — Gửi dữ liệu sản lượng lên server.
Chạy trên mỗi PC (Mixer, Pellet Feedmill, Pellet Mini).
Đọc file Excel local → parse dữ liệu → POST lên server.

Sử dụng:
    python uploader.py
"""

import os
import sys
import re
import json
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import threading

# Try to import pandas and requests
try:
    import pandas as pd
except ImportError:
    print("Cần cài pandas: pip install pandas openpyxl")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Cần cài requests: pip install requests")
    sys.exit(1)


# ─── Config ────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_CONFIG = {
    "server_url": "http://localhost:5000",
    "username": "",
    "password": "",
    "folder": "",
}

# File type configurations (same as data_loader.py)
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
        "extra_col": "AL",
    },
}

# Permission: which user reads which files
USER_FILE_TYPES = {
    "mixer": ["MIXER"],
    "pellet feedmill": ["PL"],
    "pellet mini": ["PL"],
}

# Line name filter per user
USER_LINES = {
    "mixer": ["MIXER"],
    "pellet feedmill": ["PL1", "PL2", "PL3", "PL4", "PL5"],
    "pellet mini": ["PL6", "PL7"],
}


# ─── Config Load/Save ─────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Merge with defaults
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ─── Excel Parser ──────────────────────────────────────────
def parse_excel_file(filepath, config):
    """Parse a single Excel file. Returns list of day entries."""
    filename = os.path.basename(filepath)
    match = re.match(config["regex"], filename, re.IGNORECASE)
    if not match:
        return None, None

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

        entries = []
        for _, row in df.iterrows():
            day_num = int(row["day"]) if row["day"] else 0
            if day_num < 1 or day_num > 31:
                continue
            entry = {
                "line_name": line_name,
                "category": config["category"],
                "year": year,
                "month": month,
                "day": day_num,
                "ca1": round(float(row["ca1"]), 2),
                "ca2": round(float(row["ca2"]), 2),
                "ca3": round(float(row["ca3"]), 2),
                "total": round(float(row["total"]), 2),
                "cam_bot": 0,
            }
            entries.append(entry)

        # Read extra column (cam_bot) for MIXER
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
                    if idx < len(entries):
                        val = row.iloc[0]
                        entries[idx]["cam_bot"] = round(float(val) if val else 0, 2)
            except Exception:
                pass

        return f"{line_name} T{month}.{year}", entries

    except Exception as e:
        return filename, f"Lỗi: {e}"


def read_all_files(folder, username):
    """Read all Excel files the user is allowed to access."""
    allowed_types = USER_FILE_TYPES.get(username, [])
    allowed_lines = USER_LINES.get(username, [])
    all_entries = []
    file_results = []

    for type_key in allowed_types:
        config = FILE_CONFIGS[type_key]
        pattern = os.path.join(folder, config["pattern"])
        files = sorted(glob.glob(pattern))

        for filepath in files:
            label, result = parse_excel_file(filepath, config)
            if result is None:
                continue

            if isinstance(result, str):
                # Error
                file_results.append(f"❌ {label}: {result}")
                continue

            # Filter by allowed line names
            filtered = [e for e in result if e["line_name"] in allowed_lines]
            if filtered:
                all_entries.extend(filtered)
                total = sum(e["total"] for e in filtered)
                file_results.append(f"✅ {label}: {len(filtered)} ngày, {total:,.1f} tấn")

    return all_entries, file_results


def upload_data(server_url, username, password, entries):
    """Send data to server via API."""
    url = f"{server_url.rstrip('/')}/api/upload-data"
    payload = {
        "username": username,
        "password": password,
        "entries": entries,
    }
    resp = requests.post(url, json=payload, timeout=120)
    return resp.json()


# ─── GUI ───────────────────────────────────────────────────
class UploaderApp:
    def __init__(self):
        self.config = load_config()
        self.root = tk.Tk()
        self.root.title("📊 Cập Nhật Sản Lượng")
        self.root.geometry("520x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        self._build_ui()

    def _build_ui(self):
        bg = "#1a1a2e"
        fg = "#e2e8f0"
        accent = "#6366f1"
        entry_bg = "#16213e"

        # Title
        tk.Label(self.root, text="📊 Cập Nhật Sản Lượng",
                 font=("Segoe UI", 16, "bold"), bg=bg, fg=fg).pack(pady=(15, 5))
        tk.Label(self.root, text="Đọc Excel → Gửi lên Server",
                 font=("Segoe UI", 9), bg=bg, fg="#94a3b8").pack()

        # Form frame
        form = tk.Frame(self.root, bg=bg)
        form.pack(pady=15, padx=25, fill="x")

        # Server URL
        tk.Label(form, text="Server URL:", font=("Segoe UI", 10),
                 bg=bg, fg=fg).grid(row=0, column=0, sticky="w", pady=4)
        self.server_var = tk.StringVar(value=self.config["server_url"])
        tk.Entry(form, textvariable=self.server_var, font=("Segoe UI", 10),
                 bg=entry_bg, fg=fg, insertbackground=fg, relief="flat",
                 width=35).grid(row=0, column=1, columnspan=2, pady=4, sticky="ew")

        # Username
        tk.Label(form, text="Username:", font=("Segoe UI", 10),
                 bg=bg, fg=fg).grid(row=1, column=0, sticky="w", pady=4)
        self.user_var = tk.StringVar(value=self.config["username"])
        tk.Entry(form, textvariable=self.user_var, font=("Segoe UI", 10),
                 bg=entry_bg, fg=fg, insertbackground=fg, relief="flat",
                 width=35).grid(row=1, column=1, columnspan=2, pady=4, sticky="ew")

        # Password
        tk.Label(form, text="Password:", font=("Segoe UI", 10),
                 bg=bg, fg=fg).grid(row=2, column=0, sticky="w", pady=4)
        self.pass_var = tk.StringVar(value=self.config.get("password", ""))
        tk.Entry(form, textvariable=self.pass_var, font=("Segoe UI", 10),
                 show="•", bg=entry_bg, fg=fg, insertbackground=fg, relief="flat",
                 width=35).grid(row=2, column=1, columnspan=2, pady=4, sticky="ew")

        # Folder
        tk.Label(form, text="Folder Excel:", font=("Segoe UI", 10),
                 bg=bg, fg=fg).grid(row=3, column=0, sticky="w", pady=4)
        self.folder_var = tk.StringVar(value=self.config["folder"])
        tk.Entry(form, textvariable=self.folder_var, font=("Segoe UI", 10),
                 bg=entry_bg, fg=fg, insertbackground=fg, relief="flat",
                 width=28).grid(row=3, column=1, pady=4, sticky="ew")
        tk.Button(form, text="📁", font=("Segoe UI", 10),
                  bg=accent, fg="white", relief="flat", width=3,
                  command=self._browse_folder).grid(row=3, column=2, padx=(5, 0))

        form.columnconfigure(1, weight=1)

        # Upload button
        self.btn_upload = tk.Button(
            self.root, text="🚀  Gửi dữ liệu lên hệ thống",
            font=("Segoe UI", 12, "bold"), bg=accent, fg="white",
            activebackground="#4f46e5", relief="flat", height=2,
            command=self._start_upload)
        self.btn_upload.pack(pady=10, padx=25, fill="x")

        # Status text
        self.status_text = tk.Text(
            self.root, height=10, bg="#0f172a", fg="#94a3b8",
            font=("Consolas", 9), relief="flat", state="disabled",
            wrap="word")
        self.status_text.pack(padx=25, pady=(0, 15), fill="both", expand=True)

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Chọn folder chứa file Excel")
        if folder:
            self.folder_var.set(folder)

    def _log(self, msg):
        self.status_text.config(state="normal")
        self.status_text.insert("end", msg + "\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")

    def _clear_log(self):
        self.status_text.config(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.config(state="disabled")

    def _start_upload(self):
        """Start upload in background thread."""
        self.btn_upload.config(state="disabled", text="⏳ Đang xử lý...")
        self._clear_log()
        threading.Thread(target=self._do_upload, daemon=True).start()

    def _do_upload(self):
        try:
            server = self.server_var.get().strip()
            username = self.user_var.get().strip().lower()
            password = self.pass_var.get().strip()
            folder = self.folder_var.get().strip()

            if not all([server, username, password, folder]):
                self._log("❌ Vui lòng điền đầy đủ thông tin!")
                return

            if not os.path.isdir(folder):
                self._log(f"❌ Folder không tồn tại: {folder}")
                return

            # Save config (including password for auto mode)
            self.config["server_url"] = server
            self.config["username"] = username
            self.config["password"] = password
            self.config["folder"] = folder
            save_config(self.config)

            # Read Excel files
            self._log(f"📂 Đang đọc file Excel từ: {folder}")
            self._log(f"👤 User: {username}")
            self._log("")

            entries, file_results = read_all_files(folder, username)

            for msg in file_results:
                self._log(msg)

            if not entries:
                self._log("\n❌ Không tìm thấy dữ liệu phù hợp!")
                return

            self._log(f"\n📊 Tổng: {len(entries)} bản ghi")
            self._log(f"🚀 Đang gửi lên {server}...")

            # Upload
            result = upload_data(server, username, password, entries)

            if result.get("status") == "ok":
                now = datetime.now().strftime("%H:%M:%S")
                self._log(f"\n✅ Gửi thành công lúc {now}!")
                self._log(f"   Đã lưu: {result.get('inserted', 0)} bản ghi")
                if result.get("skipped", 0) > 0:
                    self._log(f"   Bỏ qua: {result['skipped']}")
            else:
                self._log(f"\n❌ Lỗi: {result.get('message', 'Unknown error')}")

            if result.get("errors"):
                for err in result["errors"]:
                    self._log(f"   ⚠️ {err}")

        except requests.exceptions.ConnectionError:
            self._log(f"\n❌ Không kết nối được đến server!")
            self._log(f"   Kiểm tra lại URL: {self.server_var.get()}")
        except Exception as e:
            self._log(f"\n❌ Lỗi: {str(e)}")
        finally:
            self.root.after(0, lambda: self.btn_upload.config(
                state="normal", text="🚀  Gửi dữ liệu lên hệ thống"))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = UploaderApp()
    app.run()
