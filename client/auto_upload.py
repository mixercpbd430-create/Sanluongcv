"""
Auto Upload - Tự động gửi dữ liệu sản lượng lên server.
Chạy không cần GUI, dùng cho Windows Task Scheduler.

Sử dụng:
    python auto_upload.py                    # Gửi bình thường
    python auto_upload.py --dry-run          # Test: chỉ đọc file, không gửi
    python auto_upload.py --profile mixer    # Dùng config_mixer.json

Cấu hình trong config.json (cùng thư mục).
Lịch sử upload lưu trong upload_history.json.
"""

import os
import sys
import json
import logging
from datetime import datetime

# ─── Directory & Profile ──────────────────────────────────
if getattr(sys, 'frozen', False):
    _app_dir = os.path.dirname(sys.executable)
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))

# Parse arguments
_profile = ""
_dry_run = "--dry-run" in sys.argv
for i, arg in enumerate(sys.argv):
    if arg == "--profile" and i + 1 < len(sys.argv):
        _profile = sys.argv[i + 1]

# ─── Logging ──────────────────────────────────────────────
LOG_FILE = os.path.join(_app_dir, "upload.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("auto_upload")

# ─── History ──────────────────────────────────────────────
HISTORY_FILE = os.path.join(_app_dir, "upload_history.json")
MAX_HISTORY = 100


def load_history():
    """Load upload history from JSON file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history):
    """Save upload history, keeping only the last MAX_HISTORY entries."""
    history = history[-MAX_HISTORY:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_history_entry(status, username="", records_sent=0, records_saved=0,
                      records_skipped=0, errors=None, dry_run=False):
    """Add a new entry to upload history."""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,  # "success", "error", "dry-run", "no-data"
        "username": username,
        "profile": _profile or "default",
        "windows_user": os.environ.get("USERNAME", "unknown"),
        "computer": os.environ.get("COMPUTERNAME", "unknown"),
        "records_sent": records_sent,
        "records_saved": records_saved,
        "records_skipped": records_skipped,
        "dry_run": dry_run,
    }
    if errors:
        entry["errors"] = errors

    history = load_history()
    history.append(entry)
    save_history(history)
    return entry


# ─── Import uploader module ──────────────────────────────
sys.path.insert(0, _app_dir)

# Set profile for uploader's config loading
if _profile:
    # Inject --profile into sys.argv so uploader picks it up
    if "--profile" not in sys.argv:
        sys.argv.extend(["--profile", _profile])

from uploader import load_config, read_all_files, upload_data


def main():
    mode_label = "[DRY-RUN] " if _dry_run else ""
    profile_label = f"[{_profile}] " if _profile else ""

    log.info("=" * 50)
    log.info(f"🚀 {mode_label}{profile_label}Bắt đầu tự động gửi dữ liệu")

    # Load config
    config = load_config()
    server = config.get("server_url", "").strip()
    username = config.get("username", "").strip().lower()
    password = config.get("password", "").strip()
    folder = config.get("folder", "").strip()

    if not all([server, username, password, folder]):
        log.error("❌ Config thiếu thông tin! Kiểm tra config.json")
        log.error(f"   server={server}, user={username}, folder={folder}")
        add_history_entry("error", username, errors=["Config thiếu thông tin"])
        sys.exit(1)

    if not os.path.isdir(folder):
        log.error(f"❌ Folder không tồn tại: {folder}")
        add_history_entry("error", username, errors=[f"Folder không tồn tại: {folder}"])
        sys.exit(1)

    # Read Excel files
    log.info(f"📂 Đọc file từ: {folder}")
    log.info(f"👤 User: {username}")

    entries, file_results = read_all_files(folder, username)

    for msg in file_results:
        log.info(msg)

    if not entries:
        log.warning("⚠️ Không tìm thấy dữ liệu phù hợp")
        add_history_entry("no-data", username)
        sys.exit(0)

    log.info(f"📊 Tổng: {len(entries)} bản ghi")

    # Dry-run mode: stop here
    if _dry_run:
        log.info("🧪 [DRY-RUN] Chỉ kiểm tra đọc file. Không gửi lên server.")
        log.info(f"🧪 [DRY-RUN] Sẽ gửi {len(entries)} bản ghi nếu chạy thật.")
        add_history_entry("dry-run", username, records_sent=len(entries), dry_run=True)
        log.info("Hoàn tất (dry-run)!")
        return

    # Upload
    log.info(f"🚀 Đang gửi lên {server}...")

    try:
        result = upload_data(server, username, password, entries)

        if result.get("status") == "ok":
            saved = result.get("inserted", 0)
            skipped = result.get("skipped", 0)
            log.info(f"✅ Gửi thành công!")
            log.info(f"   Đã lưu: {saved} bản ghi")
            if skipped > 0:
                log.info(f"   Bỏ qua: {skipped}")

            error_msgs = result.get("errors", [])
            if error_msgs:
                for err in error_msgs:
                    log.warning(f"   ⚠️ {err}")

            add_history_entry(
                "success", username,
                records_sent=len(entries),
                records_saved=saved,
                records_skipped=skipped,
                errors=error_msgs if error_msgs else None,
            )
        else:
            err_msg = result.get("message", "Unknown")
            log.error(f"❌ Lỗi: {err_msg}")
            add_history_entry("error", username, records_sent=len(entries),
                              errors=[err_msg])

    except Exception as e:
        log.error(f"❌ Lỗi kết nối: {str(e)}")
        add_history_entry("error", username, errors=[str(e)])
        sys.exit(1)

    log.info("Hoàn tất!")


if __name__ == "__main__":
    main()
