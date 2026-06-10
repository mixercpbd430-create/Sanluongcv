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

from uploader import load_config, read_all_files, upload_data, upload_khuon


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
    base_folder = config.get("base_folder", "").strip()
    folder = config.get("folder", "").strip()

    # ── Tự động tìm folder theo tháng hiện tại ───────────
    today = datetime.now()
    cur_year = today.year
    cur_month = today.month

    if base_folder:
        # base_folder VD: "D:/bao cao cam vien/OEE"
        # Tự xây: "{base_folder} {year}/THANG {month}"
        year_folder = os.path.join(f"{base_folder} {cur_year}")
        if not os.path.isdir(year_folder):
            # Thử thêm pattern khác: "OEE2026", "OEE 2026"
            alt = f"{base_folder}{cur_year}"
            if os.path.isdir(alt):
                year_folder = alt
            else:
                log.error(f"❌ Không tìm thấy folder năm: {year_folder}")
                add_history_entry("error", username, errors=[f"Folder năm không tồn tại: {year_folder}"])
                sys.exit(1)

        # Thử các pattern tên folder tháng phổ biến
        month_patterns = [
            f"THANG {cur_month}",                         # THANG 6
            f"THANG {cur_month}/THANG {cur_month}",       # THANG 6/THANG 6
            f"Thang {cur_month}",                         # Thang 6
            f"T{cur_month}",                              # T6
            f"THANG {cur_month:02d}",                     # THANG 06
            f"thang {cur_month}",                         # thang 6
        ]

        folder = ""
        for pattern in month_patterns:
            candidate = os.path.join(year_folder, pattern)
            if os.path.isdir(candidate):
                folder = candidate
                break

        if not folder:
            log.error(f"❌ Không tìm thấy folder tháng {cur_month} trong: {year_folder}")
            log.error(f"   Đã thử: {', '.join(month_patterns)}")
            add_history_entry("error", username,
                              errors=[f"Folder tháng {cur_month} không tồn tại trong {year_folder}"])
            sys.exit(1)

        log.info(f"📁 Auto-detect folder: {folder}")

    elif folder:
        # Backward compatible: dùng folder cố định từ config
        log.info(f"📁 Dùng folder từ config: {folder}")
    else:
        log.error("❌ Config thiếu 'base_folder' hoặc 'folder'!")
        add_history_entry("error", username, errors=["Config thiếu folder"])
        sys.exit(1)

    if not all([server, username, password]):
        log.error("❌ Config thiếu thông tin! Kiểm tra config.json")
        log.error(f"   server={server}, user={username}")
        add_history_entry("error", username, errors=["Config thiếu thông tin"])
        sys.exit(1)

    if not os.path.isdir(folder):
        log.error(f"❌ Folder không tồn tại: {folder}")
        add_history_entry("error", username, errors=[f"Folder không tồn tại: {folder}"])
        sys.exit(1)

    # Read Excel files
    log.info(f"📂 Đọc file từ: {folder}")
    log.info(f"👤 User: {username}")

    entries, nvvh_entries, loss_entries, khuon_entries, file_results = read_all_files(folder, username)

    for msg in file_results:
        log.info(msg)

    # ── Lọc chỉ giữ 3 ngày gần nhất ──────────────────────
    today = datetime.now()
    recent_days = set()
    for delta in range(3):
        d = today - __import__('datetime').timedelta(days=delta)
        recent_days.add((d.year, d.month, d.day))

    def is_recent(entry):
        return (entry.get("year"), entry.get("month"), entry.get("day")) in recent_days

    orig_counts = (len(entries), len(nvvh_entries), len(loss_entries))
    entries = [e for e in entries if is_recent(e)]
    nvvh_entries = [e for e in nvvh_entries if is_recent(e)]
    loss_entries = [e for e in loss_entries if is_recent(e)]
    # Khuôn gửi nguyên (dữ liệu theo tháng, không lọc theo ngày)

    log.info(f"📅 Lọc 3 ngày gần nhất: {sorted(recent_days)}")
    log.info(f"   Sản lượng: {orig_counts[0]} → {len(entries)}")
    log.info(f"   NVVH: {orig_counts[1]} → {len(nvvh_entries)}")
    log.info(f"   LOSS: {orig_counts[2]} → {len(loss_entries)}")

    log.info(f"📊 Tổng: {len(entries)} sản lượng, {len(nvvh_entries)} NVVH, {len(loss_entries)} LOSS, {len(khuon_entries)} KHUÔN")

    if not entries and not nvvh_entries and not loss_entries and not khuon_entries:
        log.warning("⚠️ Không tìm thấy dữ liệu phù hợp trong 3 ngày gần nhất")
        add_history_entry("no-data", username)
        sys.exit(0)

    # Dry-run mode: stop here
    if _dry_run:
        log.info("🧪 [DRY-RUN] Chỉ kiểm tra đọc file. Không gửi lên server.")
        log.info(f"🧪 [DRY-RUN] Sẽ gửi {len(entries)} sản lượng, {len(nvvh_entries)} NVVH, {len(loss_entries)} LOSS, {len(khuon_entries)} KHUÔN nếu chạy thật.")
        add_history_entry("dry-run", username, records_sent=len(entries), dry_run=True)
        log.info("Hoàn tất (dry-run)!")
        return

    # Upload
    log.info(f"🚀 Đang gửi lên {server}...")

    try:
        result = upload_data(server, username, password, entries, nvvh_entries, loss_entries)

        if result.get("status") == "ok":
            saved = result.get("inserted", 0)
            nvvh_saved = result.get("nvvh_count", 0)
            loss_saved = result.get("loss_count", 0)
            skipped = result.get("skipped", 0)
            log.info(f"✅ Gửi thành công!")
            log.info(f"   Sản lượng: {saved} bản ghi")
            if nvvh_saved > 0:
                log.info(f"   NVVH: {nvvh_saved} bản ghi")
            if loss_saved > 0:
                log.info(f"   LOSS: {loss_saved} bản ghi")
            if skipped > 0:
                log.info(f"   Bỏ qua: {skipped}")

            error_msgs = result.get("errors", [])
            if error_msgs:
                for err in error_msgs:
                    log.warning(f"   ⚠️ {err}")

            # Upload khuon data
            khuon_saved = 0
            if khuon_entries:
                log.info(f"🔩 Đang gửi {len(khuon_entries)} khuôn...")
                khuon_result = upload_khuon(server, username, password, khuon_entries)
                if khuon_result.get("status") == "ok":
                    khuon_saved = khuon_result.get("khuon_count", 0)
                    log.info(f"   ✅ Gửi khuôn thành công! {khuon_saved} bản ghi")
                else:
                    log.error(f"   ❌ Lỗi khuôn: {khuon_result.get('message', 'Unknown')}")
                khuon_errors = khuon_result.get("errors", [])
                if khuon_errors:
                    for err in khuon_errors:
                        log.warning(f"   ⚠️ {err}")
                    error_msgs.extend(khuon_errors)

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
