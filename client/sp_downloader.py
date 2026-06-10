"""
SharePoint Downloader — Tải file Excel sản lượng từ SharePoint.
Sử dụng Playwright browser automation để xác thực và tải file
qua SharePoint REST API.

Hỗ trợ:
    - MIXER: file dạng "MIXER T6.2026.xlsx", "MIXER T06.2026.xlsm"
    - Pellet: file dạng "PL1 6.2026.xlsx", "PL1 06.2026.xlsx"

Sử dụng:
    from sp_downloader import SPDownloader
    dl = SPDownloader()
    dl.login_sharepoint(sp_url)
    result = dl.download_all_production(sp_mixer_url, sp_pellet_url, 6, 2026)
"""

import os
import sys
import re
import base64
import time
from urllib.parse import urlparse, unquote

# ─── Playwright import (graceful fallback) ─────────────────
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# ─── App directory (hỗ trợ PyInstaller frozen EXE) ────────
if getattr(sys, 'frozen', False):
    _app_dir = os.path.dirname(sys.executable)
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))

# ─── Đường dẫn mặc định ───────────────────────────────────
SP_BROWSER_DATA = os.path.join(_app_dir, '.sp_browser_data')
SP_DOWNLOAD_DIR = os.path.join(_app_dir, 'sp_downloads')

# ─── Danh sách máy sản lượng ──────────────────────────────
MIXER_MACHINES = ["MIXER"]
PELLET_MACHINES = [f"PL{i}" for i in range(1, 8)]  # PL1..PL7


class SPDownloader:
    """Tải file Excel sản lượng từ SharePoint qua REST API (browser session)."""

    def __init__(self, log_fn=None, stop_check=None):
        """
        Khởi tạo SPDownloader.

        Args:
            log_fn:     Hàm log (mặc định: print).
            stop_check: Hàm kiểm tra dừng, trả True để hủy (mặc định: luôn False).
        """
        self.log = log_fn or print
        self.stop_check = stop_check or (lambda: False)
        self.user_data_dir = SP_BROWSER_DATA
        self.download_dir = SP_DOWNLOAD_DIR
        self.logged_in = False

    # ─── Kiểm tra playwright ──────────────────────────────
    def _check_playwright(self):
        """Kiểm tra playwright đã cài đặt chưa. Trả True nếu OK."""
        if not HAS_PLAYWRIGHT:
            self.log("❌ Chưa cài Playwright!")
            self.log("   Chạy lệnh sau để cài đặt:")
            self.log("     pip install playwright")
            self.log("     playwright install chromium")
            return False
        return True

    # ─── Kiểm tra phiên đăng nhập ────────────────────────
    def check_login(self):
        """
        Kiểm tra phiên đăng nhập SharePoint còn hiệu lực.

        Returns:
            True nếu thư mục browser data tồn tại và có cookie/session.
        """
        if not os.path.isdir(self.user_data_dir):
            return False
        # Kiểm tra có file session thực sự (Cookies, Local State, v.v.)
        session_markers = ['Default', 'Local State', 'Cookies']
        for marker in session_markers:
            if os.path.exists(os.path.join(self.user_data_dir, marker)):
                return True
        return False

    # ─── Đăng nhập SharePoint ─────────────────────────────
    def login_sharepoint(self, sp_url):
        """
        Mở trình duyệt để người dùng đăng nhập SharePoint.
        Phiên đăng nhập sẽ được lưu lại cho các lần tải sau.

        Args:
            sp_url: URL trang SharePoint cần đăng nhập.

        Returns:
            True nếu đăng nhập thành công.
        """
        if not self._check_playwright():
            return False

        self.log("🔑 Mở trình duyệt để đăng nhập SharePoint...")
        self.log("   → Đăng nhập bằng tài khoản công ty")
        self.log("   → Đăng nhập xong → ĐÓNG trình duyệt để tiếp tục")

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                self.user_data_dir, headless=False,
                accept_downloads=True, slow_mo=500
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(sp_url, timeout=60000)
            try:
                # Chờ người dùng đóng trình duyệt (tối đa 5 phút)
                page.wait_for_event('close', timeout=300000)
            except Exception:
                pass
            self.logged_in = True
            self.log("   ✅ Đã lưu phiên đăng nhập SharePoint")
            try:
                ctx.close()
            except Exception:
                pass
        return True

    # ─── Parse URL SharePoint ─────────────────────────────
    def _parse_sp_url(self, sp_url):
        """
        Phân tích URL SharePoint → (site_host, api_base, folder_path).

        Args:
            sp_url: URL thư mục SharePoint.

        Returns:
            Tuple (site_host, api_base, folder_path).
        """
        parsed = urlparse(sp_url)
        site_host = f"{parsed.scheme}://{parsed.hostname}"
        folder_path = ''

        # Thử lấy folder path từ tham số id=
        id_match = re.search(r'[?&]id=([^&]+)', sp_url)
        if id_match:
            folder_path = unquote(id_match.group(1))
        else:
            # Thử lấy từ dạng :f:/r/sites/...
            r_match = re.search(r':f:/r(/sites/[^?]+)', sp_url)
            if r_match:
                folder_path = unquote(r_match.group(1))

        # Trích xuất site path (VD: /sites/TenSite)
        site_match = re.match(r'(/sites/[^/]+)', folder_path)
        site_path = site_match.group(1) if site_match else ''
        api_base = f"{site_host}{site_path}"

        return site_host, api_base, folder_path

    # ─── Dọn lock file browser ────────────────────────────
    def _clean_browser_locks(self):
        """Xóa lock file trình duyệt để tránh lỗi khi mở lại."""
        for lock_file in ['SingletonLock', 'SingletonCookie', 'SingletonSocket']:
            lock_path = os.path.join(self.user_data_dir, lock_file)
            try:
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass

    # ─── Tạo patterns khớp tên file ──────────────────────
    def _build_file_patterns(self, machine, month, year):
        """
        Tạo danh sách pattern để khớp tên file Excel trên SharePoint.

        MIXER dùng tiền tố "T": MIXER T6.2026.xlsx, MIXER T06.2026.xlsm
        Pellet dùng khoảng trắng:  PL1 6.2026.xlsx,  PL1 06.2026.xlsx

        Args:
            machine: Tên máy (MIXER, PL1, PL2, ...).
            month:   Tháng (int).
            year:    Năm (int).

        Returns:
            Danh sách pattern (string) để so khớp đầu tên file.
        """
        if machine.upper() == "MIXER":
            # MIXER luôn có tiền tố "T" trước tháng
            return [
                f"MIXER T{month}.{year}",
                f"MIXER T{month:02d}.{year}",
            ]
        else:
            # Pellet: PL1 6.2026, PL1 06.2026, v.v.
            return [
                f"{machine} {month}.{year}",
                f"{machine} {month:02d}.{year}",
                f"{machine} T{month}.{year}",
                f"{machine} T{month:02d}.{year}",
            ]

    # ─── Tải file từ SharePoint ───────────────────────────
    def download_files(self, sp_url, machines, month, year, download_dir=None):
        """
        Tải file Excel từ SharePoint qua REST API.

        Duyệt danh sách file trong thư mục SharePoint, khớp tên file
        theo machine + tháng/năm, tải về dạng base64 rồi ghi ra file.

        Args:
            sp_url:       URL thư mục SharePoint chứa file.
            machines:     Danh sách tên máy cần tải (VD: ["MIXER"], ["PL1","PL2",...]).
            month:        Tháng (int).
            year:         Năm (int).
            download_dir: Thư mục lưu file (mặc định: sp_downloads/).

        Returns:
            Dict {machine_name: filepath} cho các file đã tải thành công.
        """
        if not self._check_playwright():
            return {}

        download_dir = download_dir or self.download_dir
        os.makedirs(download_dir, exist_ok=True)

        if not machines:
            return {}

        self.log(f"\n🚀 Tải {len(machines)} file từ SharePoint...")

        _, api_base, folder_path = self._parse_sp_url(sp_url)
        if not folder_path:
            self.log("  ❌ Không parse được folder path từ URL SharePoint")
            return {}

        self._clean_browser_locks()

        downloaded = {}
        with sync_playwright() as p:
            # Mở browser headless với session đã lưu
            ctx = None
            for attempt in range(3):
                try:
                    ctx = p.chromium.launch_persistent_context(
                        self.user_data_dir, headless=True,
                        accept_downloads=True
                    )
                    break
                except Exception as e:
                    if attempt < 2:
                        self.log(f"  ⚠️ Browser lần {attempt + 1} lỗi, thử lại...")
                        time.sleep(2)
                    else:
                        self.log(f"  ❌ Không mở được browser: {str(e)[:100]}")
                        raise e

            if not ctx:
                return downloaded

            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            try:
                # Truy cập API endpoint để kích hoạt session
                page.goto(f"{api_base}/_api/web", timeout=60000)
                page.wait_for_load_state('domcontentloaded', timeout=30000)

                # Lấy danh sách file trong folder
                list_url = (
                    f"{api_base}/_api/web/GetFolderByServerRelativeUrl"
                    f"('{folder_path}')/Files"
                    f"?$select=Name,ServerRelativeUrl&$top=500"
                )

                files_result = page.evaluate("""
                    async (url) => {
                        try {
                            const resp = await fetch(url, {
                                headers: { 'Accept': 'application/json;odata=verbose' }
                            });
                            const data = await resp.json();
                            const files = data.d?.results || [];
                            return files.map(f => ({ name: f.Name, url: f.ServerRelativeUrl }));
                        } catch(e) {
                            return { error: e.message };
                        }
                    }
                """, list_url)

                if isinstance(files_result, dict) and 'error' in files_result:
                    self.log(f"  ❌ Lỗi lấy danh sách file: {files_result['error']}")
                    ctx.close()
                    return downloaded

                self.log(f"  📁 Tìm thấy {len(files_result)} file trong thư mục")

                # Tải từng file theo machine name
                for machine in machines:
                    if self.stop_check():
                        self.log("  ⏹️ Đã dừng theo yêu cầu")
                        break

                    patterns = self._build_file_patterns(machine, month, year)

                    # Tìm file khớp pattern
                    matched = None
                    for f in files_result:
                        for pat in patterns:
                            if (f['name'].upper().startswith(pat.upper()) and
                                    (f['name'].endswith('.xlsx') or
                                     f['name'].endswith('.xlsm') or
                                     f['name'].endswith('.xlsb'))):
                                matched = f
                                break
                        if matched:
                            break

                    if not matched:
                        self.log(f"  ⚠️ {machine}: không tìm thấy file")
                        continue

                    # Tải file qua REST API (base64)
                    try:
                        dl_url = (
                            f"{api_base}/_api/web/GetFileByServerRelativeUrl"
                            f"('{matched['url']}')/$value"
                        )

                        # Giữ nguyên tên file gốc để parser có thể khớp
                        fpath = os.path.join(download_dir, matched['name'])

                        b64_data = page.evaluate("""
                            async (url) => {
                                const resp = await fetch(url);
                                if (!resp.ok) return { error: resp.status };
                                const buf = await resp.arrayBuffer();
                                const bytes = new Uint8Array(buf);
                                let binary = '';
                                for (let i = 0; i < bytes.length; i++) {
                                    binary += String.fromCharCode(bytes[i]);
                                }
                                return { data: btoa(binary), size: bytes.length };
                            }
                        """, dl_url)

                        if isinstance(b64_data, dict) and 'error' in b64_data:
                            self.log(f"  ❌ {machine}: lỗi HTTP {b64_data['error']}")
                            continue

                        # Ghi file ra ổ đĩa
                        file_bytes = base64.b64decode(b64_data['data'])
                        with open(fpath, 'wb') as f:
                            f.write(file_bytes)

                        size_kb = b64_data['size'] // 1024
                        self.log(f"  ✅ {machine} → {size_kb}KB ({matched['name']})")
                        downloaded[machine] = fpath

                    except Exception as e:
                        self.log(f"  ❌ {machine}: {str(e)[:80]}")

            except Exception as e:
                self.log(f"  ❌ Lỗi khi tải file: {str(e)[:100]}")
            finally:
                try:
                    ctx.close()
                except Exception:
                    pass

        return downloaded

    # ─── Tải tất cả file sản lượng ────────────────────────
    def download_all_production(self, sp_mixer_url, sp_pellet_url, month, year):
        """
        Tải tất cả file sản lượng: MIXER + PL1-PL7.

        MIXER tải từ sp_mixer_url, PL1-PL7 tải từ sp_pellet_url.
        File được lưu vào thư mục sp_downloads/ với tên gốc từ SharePoint.

        Args:
            sp_mixer_url:  URL thư mục SharePoint chứa file MIXER.
            sp_pellet_url: URL thư mục SharePoint chứa file PL1-PL7.
            month:         Tháng (int).
            year:          Năm (int).

        Returns:
            Đường dẫn thư mục chứa file đã tải (str), hoặc None nếu lỗi.
        """
        if not self._check_playwright():
            return None

        download_dir = os.path.join(self.download_dir, f"T{month}_{year}")
        os.makedirs(download_dir, exist_ok=True)

        self.log(f"📦 Tải file sản lượng tháng {month}/{year}")
        self.log(f"   📂 Lưu vào: {download_dir}")

        all_downloaded = {}

        # 1. Tải MIXER
        if sp_mixer_url:
            self.log(f"\n── MIXER ──────────────────────────")
            mixer_files = self.download_files(
                sp_mixer_url, MIXER_MACHINES, month, year, download_dir
            )
            all_downloaded.update(mixer_files)

        # 2. Tải PL1-PL7
        if sp_pellet_url:
            self.log(f"\n── PELLET (PL1-PL7) ──────────────")
            pellet_files = self.download_files(
                sp_pellet_url, PELLET_MACHINES, month, year, download_dir
            )
            all_downloaded.update(pellet_files)

        # Tổng kết
        total = len(all_downloaded)
        expected = len(MIXER_MACHINES) + len(PELLET_MACHINES)
        self.log(f"\n{'─' * 40}")
        self.log(f"📊 Kết quả: {total}/{expected} file đã tải")

        if total > 0:
            self.log(f"   Đã tải: {', '.join(sorted(all_downloaded.keys()))}")
        missing = set(MIXER_MACHINES + PELLET_MACHINES) - set(all_downloaded.keys())
        if missing:
            self.log(f"   Thiếu:  {', '.join(sorted(missing))}")

        return download_dir if total > 0 else None


# ─── CLI test ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  SharePoint Downloader - Test")
    print("=" * 50)

    dl = SPDownloader()

    if dl.check_login():
        print("✅ Đã có phiên đăng nhập SharePoint")
    else:
        print("⚠️ Chưa đăng nhập SharePoint")
        print("   Chạy dl.login_sharepoint(url) để đăng nhập")
