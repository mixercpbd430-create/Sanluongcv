"""
Flask Web App - Sản Lượng Hàng Ngày
Displays daily production output from SQLite database.
Data imported from Excel files (PL1-PL7, MIXER) into production.db.
Accessible via LAN (company WiFi) and Internet.
"""

import os
import time
from functools import wraps
from flask import (Flask, render_template, jsonify, request,
                   session, redirect, url_for)
from database import (init_db, import_from_excel, import_month_from_excel,
                      load_all_from_db, get_db_stats,
                      save_manual_input, get_manual_inputs,
                      get_monthly_sale_total, save_uploaded_data,
                      authenticate, change_password, get_all_users)

app = Flask(__name__)
app.secret_key = "cpvn-sanluong-2026-secret"

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize database on startup
init_db(DATA_DIR)


@app.route("/healthz")
def healthz():
    """Health check endpoint for cloud platforms (Render, etc.)."""
    return "ok", 200

# ── In-memory cache (reads from SQLite, not Excel) ───────────
CACHE_TTL = 300  # 5 minutes
_cache = {"data": None, "timestamp": 0}


def get_all_data():
    """Return cached data, refreshing from SQLite only when stale."""
    now = time.time()
    if _cache["data"] is None or (now - _cache["timestamp"]) > CACHE_TTL:
        _cache["data"] = load_all_from_db(DATA_DIR)
        _cache["timestamp"] = now
    return _cache["data"]


def invalidate_cache():
    """Force reload on next request."""
    _cache["data"] = None
    _cache["timestamp"] = 0


# ── Authentication ───────────────────────────────────────────

def login_required(f):
    """Decorator: redirect to /login if not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        user = authenticate(DATA_DIR, username, password)
        if user:
            session["user"] = user
            return redirect(url_for("index"))
        return render_template("login.html", error="Sai tài khoản hoặc mật khẩu!")
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    """Logout and redirect to login page."""
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/api/lib/h2c")
def serve_h2c():
    """Serve html2canvas library dynamically to bypass antivirus blocking."""
    h2c_path = os.path.join(DATA_DIR, "node_modules", "html2canvas", "dist", "html2canvas.min.js")
    if not os.path.exists(h2c_path):
        h2c_path = os.path.join(DATA_DIR, "static", "h2c_lib.js")
    try:
        with open(h2c_path, "r", encoding="utf-8") as f:
            content = f.read()
        return app.response_class(content, mimetype="application/javascript")
    except Exception:
        return "// html2canvas not found", 404


@app.route("/api/upload-data", methods=["POST"])
def api_upload_data():
    """Receive production data from client PCs.
    JSON body: {username, password, entries: [{line_name, category, year, month, day, ca1, ca2, ca3, total, cam_bot?}, ...]}
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400

    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()
    entries = data.get("entries", [])

    # Authenticate
    user = authenticate(DATA_DIR, username, password)
    if not user:
        return jsonify({"status": "error", "message": "Sai tài khoản hoặc mật khẩu"}), 401

    if not entries:
        return jsonify({"status": "error", "message": "Không có dữ liệu"}), 400

    # Save data
    result = save_uploaded_data(DATA_DIR, username, entries)

    # Invalidate cache so dashboard shows new data
    invalidate_cache()

    return jsonify(result)


@app.route("/api/change-password", methods=["POST"])
@login_required
def api_change_password():
    """Change password for the current user."""
    data = request.get_json()
    new_pass = data.get("new_password", "").strip()
    if not new_pass or len(new_pass) < 1:
        return jsonify({"error": "Mật khẩu không được để trống"}), 400

    username = session["user"]["username"]
    if change_password(DATA_DIR, username, new_pass):
        return jsonify({"status": "ok", "message": "Đổi mật khẩu thành công!"})
    return jsonify({"error": "Lỗi đổi mật khẩu"}), 500


@app.route("/api/users")
@login_required
def api_users():
    """Admin only: get all users with passwords."""
    if session["user"]["role"] != "admin":
        return jsonify({"error": "Không có quyền"}), 403
    users = get_all_users(DATA_DIR)
    return jsonify(users)


@app.context_processor
def inject_user():
    """Make current_user available in all templates."""
    return {"current_user": session.get("user", None)}


@app.route("/")
@login_required
def index():
    result = get_all_data()
    months = result["months"]  # sorted descending (newest first)
    all_data = result["data"]

    # Default to latest month, or use query param, or current month
    from datetime import datetime as _dt
    fallback = _dt.now().strftime("%Y-%m")
    selected_month = request.args.get("month", months[0] if months else fallback)

    # Get data for selected month
    month_data = all_data.get(selected_month, {})

    # Build month labels for dropdown (e.g., "Tháng 1/2026")
    month_labels = []
    for mk in months:
        parts = mk.split("-")
        label = f"Tháng {int(parts[1])}/{parts[0]}"
        month_labels.append({"key": mk, "label": label})

    # Monthly sale total for dashboard
    sale_total = 0
    if selected_month and "-" in selected_month:
        parts = selected_month.split("-")
        sale_total = get_monthly_sale_total(DATA_DIR, int(parts[0]), int(parts[1]))

    return render_template(
        "index.html",
        data=month_data,
        months=month_labels,
        selected_month=selected_month,
        monthly_sale_total=sale_total,
    )


@app.route("/api/data")
@login_required
def api_all_data():
    """JSON API: data for a specific month (or latest)."""
    result = get_all_data()
    months = result["months"]
    from datetime import datetime as _dt
    fallback = _dt.now().strftime("%Y-%m")
    selected = request.args.get("month", months[0] if months else fallback)
    month_data = result["data"].get(selected, {})

    # Monthly sale total
    sale_total = 0
    if selected and "-" in selected:
        parts = selected.split("-")
        sale_total = get_monthly_sale_total(DATA_DIR, int(parts[0]), int(parts[1]))

    return jsonify({
        "months": [
            {"key": mk, "label": f"Tháng {int(mk.split('-')[1])}/{mk.split('-')[0]}"}
            for mk in months
        ],
        "selected_month": selected,
        "lines": month_data,
        "monthly_sale_total": sale_total,
    })


@app.route("/api/data/<line>")
@login_required
def api_line_data(line):
    """JSON API: data for a specific production line in the selected month."""
    result = get_all_data()
    months = result["months"]
    selected = request.args.get("month", months[0] if months else "")
    month_data = result["data"].get(selected, {})

    line_upper = line.upper()
    if line_upper in month_data:
        return jsonify(month_data[line_upper])
    return jsonify({"error": f"Line {line} not found in {selected}"}), 404


@app.route("/api/refresh", methods=["POST"])
@login_required
def api_refresh():
    """Re-import Excel → SQLite for the selected month (or all)."""
    month = request.args.get("month", "")
    if month:
        # Only re-import the selected month (fast)
        count = import_month_from_excel(DATA_DIR, month)
    else:
        # Full re-import (all months)
        count = import_from_excel(DATA_DIR)
    invalidate_cache()
    return jsonify({"status": "ok", "records": count, "month": month})


@app.route("/api/db-stats")
def api_db_stats():
    """Database statistics."""
    stats = get_db_stats(DATA_DIR)
    return jsonify(stats or {"error": "No database found"})


@app.route("/api/manual-input", methods=["POST"])
@login_required
def api_save_manual_input():
    """Save SALE or STOCK value for a specific day."""
    data = request.get_json()
    month_key = data.get("month", "")
    day = data.get("day", 0)
    field = data.get("field", "")  # 'sale' or 'stock'
    value = data.get("value", 0)

    if not month_key or not day or field not in ("sale", "stock"):
        return jsonify({"error": "Invalid input"}), 400

    parts = month_key.split("-")
    year = int(parts[0])
    month = int(parts[1])

    save_manual_input(DATA_DIR, year, month, day, field, float(value))
    return jsonify({"status": "ok", "field": field, "day": day, "value": value})


@app.route("/report")
@login_required
def report_page():
    """Daily report page with 31 day buttons."""
    result = get_all_data()
    months = result["months"]
    from datetime import datetime as _dt
    fallback = _dt.now().strftime("%Y-%m")
    selected_month = request.args.get("month", months[0] if months else fallback)
    month_data = result["data"].get(selected_month, {})

    # Build month labels
    month_labels = []
    for mk in months:
        parts = mk.split("-")
        label = f"Tháng {int(parts[1])}/{parts[0]}"
        month_labels.append({"key": mk, "label": label})

    # Find days that have data (any line with total > 0)
    days_with_data = set()
    for line_info in month_data.values():
        for d in line_info.get("days", []):
            if d["total"] > 0:
                days_with_data.add(d["day"])
    days_with_data = sorted(days_with_data)

    # Read html2canvas for inline embedding (avoids antivirus blocking)
    h2c_path = os.path.join(DATA_DIR, "static", "html2canvas.min.js")
    html2canvas_js = ""
    if os.path.exists(h2c_path):
        with open(h2c_path, "r", encoding="utf-8") as f:
            html2canvas_js = f.read()

    return render_template(
        "report.html",
        data=month_data,
        months=month_labels,
        selected_month=selected_month,
        days_with_data=days_with_data,
        html2canvas_js=html2canvas_js,
    )


@app.route("/api/report/<int:day>")
@login_required
def api_report_day(day):
    """JSON API: daily report for a specific day."""
    result = get_all_data()
    months = result["months"]
    selected = request.args.get("month", months[0] if months else "")
    month_data = result["data"].get(selected, {})

    # Build report
    report = {"day": day, "month": selected}

    # MIXER data
    mixer = month_data.get("MIXER", {})
    mixer_day = next((d for d in mixer.get("days", []) if d["day"] == day), None)
    report["mixer"] = {
        "ca1": mixer_day["ca1"] if mixer_day else 0,
        "ca2": mixer_day["ca2"] if mixer_day else 0,
        "ca3": mixer_day["ca3"] if mixer_day else 0,
        "total": mixer_day["total"] if mixer_day else 0,
        "cam_bot": mixer_day.get("cam_bot", 0) if mixer_day else 0,
    }

    # PL1-PL7 data
    pellets = []
    for i in range(1, 8):
        pl_name = f"PL{i}"
        pl = month_data.get(pl_name, {})
        pl_day = next((d for d in pl.get("days", []) if d["day"] == day), None)
        pellets.append({
            "name": pl_name,
            "ca1": pl_day["ca1"] if pl_day else 0,
            "ca2": pl_day["ca2"] if pl_day else 0,
            "ca3": pl_day["ca3"] if pl_day else 0,
            "total": pl_day["total"] if pl_day else 0,
        })
    report["pellets"] = pellets

    # Total pellet
    report["total_pellet"] = {
        "ca1": round(sum(p["ca1"] for p in pellets), 2),
        "ca2": round(sum(p["ca2"] for p in pellets), 2),
        "ca3": round(sum(p["ca3"] for p in pellets), 2),
        "total": round(sum(p["total"] for p in pellets), 2),
    }

    # Manual inputs (sale/stock)
    parts = selected.split("-")
    manual = get_manual_inputs(DATA_DIR, int(parts[0]), int(parts[1]), day)
    report["sale"] = manual.get("sale", None)
    report["stock"] = manual.get("stock", None)

    return jsonify(report)


if __name__ == "__main__":
    print("=" * 60)
    print("  SẢN LƯỢNG HÀNG NGÀY - Flask Web App")
    print("  Truy cập: http://localhost:5000")
    print("  Hoặc từ thiết bị khác: http://<IP máy>:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
