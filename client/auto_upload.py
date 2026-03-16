"""
Auto Upload - Tự động gửi dữ liệu sản lượng lên server.
Chạy không cần GUI, dùng cho Windows Task Scheduler.

Sử dụng:
    python auto_upload.py
    
Cấu hình trong config.json (cùng thư mục).
"""

import os
import sys
import json
import logging
from datetime import datetime

# Setup logging
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("auto_upload")

# Import from uploader module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uploader import load_config, read_all_files, upload_data


def main():
    log.info("=" * 50)
    log.info("🚀 Bắt đầu tự động gửi dữ liệu")

    # Load config
    config = load_config()
    server = config.get("server_url", "").strip()
    username = config.get("username", "").strip().lower()
    password = config.get("password", "").strip()
    folder = config.get("folder", "").strip()

    if not all([server, username, password, folder]):
        log.error("❌ Config thiếu thông tin! Kiểm tra config.json")
        log.error(f"   server={server}, user={username}, folder={folder}")
        sys.exit(1)

    if not os.path.isdir(folder):
        log.error(f"❌ Folder không tồn tại: {folder}")
        sys.exit(1)

    # Read Excel files
    log.info(f"📂 Đọc file từ: {folder}")
    log.info(f"👤 User: {username}")

    entries, file_results = read_all_files(folder, username)

    for msg in file_results:
        log.info(msg)

    if not entries:
        log.warning("⚠️ Không tìm thấy dữ liệu phù hợp")
        sys.exit(0)

    log.info(f"📊 Tổng: {len(entries)} bản ghi")

    # Upload
    log.info(f"🚀 Đang gửi lên {server}...")

    try:
        result = upload_data(server, username, password, entries)

        if result.get("status") == "ok":
            log.info(f"✅ Gửi thành công!")
            log.info(f"   Đã lưu: {result.get('inserted', 0)} bản ghi")
            if result.get("skipped", 0) > 0:
                log.info(f"   Bỏ qua: {result['skipped']}")
        else:
            log.error(f"❌ Lỗi: {result.get('message', 'Unknown')}")

        if result.get("errors"):
            for err in result["errors"]:
                log.warning(f"   ⚠️ {err}")

    except Exception as e:
        log.error(f"❌ Lỗi kết nối: {str(e)}")
        sys.exit(1)

    log.info("Hoàn tất!")


if __name__ == "__main__":
    main()
