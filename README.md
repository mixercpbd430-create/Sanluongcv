# 🏭 Sản Lượng Sản Xuất — Nhà Máy Bình Dương

> Hệ thống theo dõi và báo cáo sản lượng sản xuất hàng ngày  
> **CÔNG TY CỔ PHẦN CHĂN NUÔI C.P VIỆT NAM — Chi Nhánh Tại Bình Dương — Phòng Sản Xuất**

---

## 📌 Mục Đích

| # | Mục đích | Mô tả |
|---|----------|-------|
| 1 | **Theo dõi sản lượng** | Thu thập dữ liệu sản lượng từ các dây chuyền MIXER và PELLET (PL1–PL7) theo từng ca (CA1, CA2, CA3) mỗi ngày |
| 2 | **Báo cáo tự động** | Tạo bảng báo cáo sản lượng hàng ngày, chụp ảnh gửi qua Zalo/Email nhanh chóng |
| 3 | **Quản lý tập trung** | Dữ liệu từ nhiều máy tính nhà máy được tổng hợp về 1 hệ thống duy nhất |
| 4 | **Truy cập mọi nơi** | Xem sản lượng từ bất kỳ thiết bị nào có trình duyệt (PC, điện thoại, tablet) |

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Client Uploader │────▶│  .NET Web API    │────▶│  PostgreSQL  │
│  (Python/Tkinter)│     │  (Backend:5000)  │     │  (Neon.tech) │
└─────────────────┘     └──────────────────┘     └──────────────┘
                               ▲
                               │
                        ┌──────┴──────┐
                        │  React App   │
                        │ (Frontend:   │
                        │  5173)       │
                        └─────────────┘
```

| Thành phần | Công nghệ | Vai trò |
|------------|-----------|---------|
| **Frontend** | React 19 + TypeScript + Vite | Giao diện web (Dashboard, Report) |
| **Backend** | .NET 8 Web API (C#) | API server, xác thực JWT, xử lý nghiệp vụ |
| **Database** | PostgreSQL (Neon.tech) | Lưu trữ dữ liệu sản lượng, user |
| **Client Uploader** | Python + Tkinter | Đọc Excel sản lượng → upload lên server |

---

## 🖥️ Các Trang Chính

### 1. Trang Đăng Nhập (`/login`)
- Nhập tài khoản và mật khẩu
- Xác thực qua JWT token

### 2. Trang Dashboard (`/`)
| Tính năng | Mô tả |
|-----------|-------|
| **Summary Cards** | Tổng sản lượng MIXER, PL1–PL7, SALE |
| **Biểu đồ** | Chart.js cột xếp chồng theo ngày, phân biệt màu theo line |
| **Bảng dữ liệu** | Chi tiết từng ngày: CA1, CA2, CA3, Tổng |
| **Chọn tháng** | Dropdown chuyển tháng xem dữ liệu |
| **Chọn line** | Tab: ALL / MIXER / PL1–PL7 |
| **User menu** | Đổi mật khẩu, quản lý user (admin) |

### 3. Trang Báo Cáo Ngày (`/report`)
| Tính năng | Mô tả |
|-----------|-------|
| **Chọn ngày** | Grid 1–31, ngày có data tô xanh |
| **Bảng báo cáo** | MIXER, Cám bột, TOTAL PELLET, PL1–PL7 |
| **Nhập SALE/STOCK** | Gõ trực tiếp, tự động lưu sau 0.5 giây |
| **Capture báo cáo** | Chụp bảng thành ảnh PNG → Copy clipboard → Dán Zalo/Email |

### 4. Client Uploader (Desktop App)
| Trường | Cách dùng |
|--------|-----------|
| **Server URL** | URL backend (VD: `https://sanluongcv.onrender.com`) |
| **Username** | Tài khoản upload (`mixer`, `pellet feedmill`, `pellet mini`) |
| **Password** | Mật khẩu tài khoản |
| **Folder Excel** | Thư mục chứa file Excel sản lượng |
| **Nút "Gửi"** | Đọc file Excel → Parse data → Upload lên server |

---

## 🔄 Quy Trình Sử Dụng Hàng Ngày

```
Bước 1  →  Máy nhà máy chạy Client Uploader → gửi data Excel lên server
Bước 2  →  Mở trình duyệt → vào Dashboard → xem tổng quan sản lượng
Bước 3  →  Nhấn "Báo cáo ngày" → chọn ngày → nhập SALE/STOCK
Bước 4  →  Nhấn "Capture báo cáo" → dán ảnh vào Zalo/Email gửi ban lãnh đạo
```

---

## 👤 Tài Khoản Mặc Định

| Username | Mật khẩu | Quyền upload | Ghi chú |
|----------|----------|-------------|---------|
| `mixer` | `2810` | Chỉ data MIXER | Máy tính khu vực Mixer |
| `pellet feedmill` | `2810` | Chỉ data PELLET | Máy tính khu vực Pellet chính |
| `pellet mini` | `2810` | Chỉ data PELLET | Máy tính khu vực Pellet mini |
| `admin` | `2810` | Tất cả + quản lý user | Quản trị viên |

> ⚠️ **Lưu ý**: Nên đổi mật khẩu mặc định sau khi cài đặt lần đầu.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy

### Yêu cầu
- **Node.js** >= 18
- **.NET 8 SDK**
- **PostgreSQL** (hoặc dùng Neon.tech miễn phí)

### 1. Backend (.NET Web API)

```powershell
cd backend

# Tạo file .env với connection string PostgreSQL
echo "DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require" > .env

# Chạy server
dotnet run
# → http://localhost:5000
```

### 2. Frontend (React + Vite)

```powershell
cd frontend
npm install
npm run dev -- --host
# → http://localhost:5173 (local)
# → http://<IP-máy>:5173 (LAN)
```

### 3. Client Uploader

```powershell
cd client
python uploader.py
# Hoặc chạy file .bat đã tạo sẵn
```

---

## 📁 Cấu Trúc Dự Án

```
Sanluongcv/
├── backend/                    # .NET 8 Web API
│   ├── Controllers/            # API endpoints
│   ├── Models/                 # Entity models (Production, User, ManualInput)
│   ├── Services/               # Business logic
│   ├── Data/                   # EF Core DbContext
│   ├── DTOs/                   # Request/Response types
│   ├── Program.cs              # App configuration
│   └── .env                    # DATABASE_URL (không push lên Git)
│
├── frontend/                   # React + TypeScript (Vite)
│   └── src/
│       ├── pages/              # LoginPage, DashboardPage, ReportPage
│       ├── api/                # Axios client + JWT interceptor
│       ├── contexts/           # AuthContext
│       └── components/         # ProtectedRoute
│
├── client/                     # Python uploader (Desktop)
│   └── uploader.py
│
├── app.py                      # Flask app (phiên bản cũ)
├── database.py                 # Database module (phiên bản cũ)
└── README.md                   # File này
```

---

## 📊 Ý Nghĩa Dữ Liệu

| Thuật ngữ | Ý nghĩa |
|-----------|---------|
| **MIXER** | Dây chuyền trộn thức ăn (Mixer Feedmill) |
| **PELLET (PL1–PL7)** | 7 dây chuyền ép viên thức ăn chăn nuôi |
| **CA 1 / CA 2 / CA 3** | Ca sản xuất: Sáng / Chiều / Đêm |
| **Target** | Mục tiêu sản lượng (MIXER: 2200 tấn, PELLET: 2150 tấn) |
| **SALE** | Sản lượng bán ra trong ngày (tấn) |
| **STOCK** | Tồn kho cuối ngày (tấn) |
| **Cám bột** | Sản lượng cám bột từ dây chuyền Mixer |

---

## 🌐 Deploy lên Render.com

1. Push code lên GitHub
2. Tạo **Web Service** trên [Render.com](https://render.com)
3. Thêm Environment Variable: `DATABASE_URL` = connection string Neon.tech
4. Deploy tự động từ GitHub

---

<p align="center">
  <b>Phòng Sản Xuất — Nhà Máy Bình Dương</b><br>
  <i>Công Ty Cổ Phần Chăn Nuôi C.P Việt Nam</i>
</p>
