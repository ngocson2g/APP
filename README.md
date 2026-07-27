# 🛡️ Security App: Ubuntu 24.04 Compliance Checker

**`security-app`** là một công cụ kiểm tra tuân thủ bảo mật tự động chuyên sâu, được thiết kế tối ưu cho **Ubuntu 24.04 LTS**. Ứng dụng đọc các bộ quy tắc (CIS Benchmark, DISA STIG) và thực thi kiểm tra hệ thống với tốc độ cực cao nhờ thuật toán lập lịch **LPT (Longest Processing Time)** và điều chỉnh worker động **AIMD**.

---

## 🚀 Tính Năng Nổi Bật

- ⚡ **Siêu Tốc**: Kiểm tra ~250 rule của CIS/STIG chỉ trong **~12 giây** nhờ lập lịch đa luồng/đa tiến trình thông minh (Dual-pool).
- 🧠 **Adaptive Scheduling**: Tự động phân loại lệnh CPU-ish/IO-ish và tự động điều chỉnh timeout/worker (AIMD tuning) dựa trên độ trễ thực tế.
- 🛡️ **Safety-First**: Tích hợp nhiều lớp bảo vệ (Command Denylist, Risk Scoring, Secret Masking) để tránh thực thi nhầm các lệnh shell nguy hiểm (rm, mkfs, fork bomb, v.v.).
- 📊 **Báo Cáo Đa Kênh**: Cung cấp báo cáo qua Terminal (ASCII charts), JSON, bundle CSV, và giao diện **Web Dashboard**.
- 📈 **Chấm Điểm Tuân Thủ**: Tính điểm compliance score (0-100) có trọng số theo mức độ nghiêm trọng (critical, high, medium, low).

## 🏗️ Kiến Trúc

Ứng dụng chia thành 5 module chính:
1. **Parsers**: Đọc và chuẩn hoá rule từ nhiều định dạng `CSV`, `JSON`, `XML (XCCDF)`.
2. **Policy**: Lớp bảo vệ (Safety & Risk policy) chặn lệnh cấm và chấm điểm rủi ro.
3. **Core (Runner & Scheduler)**: Động cơ chính gom nhóm lệnh (LPT) và điều phối thực thi song song (ProcessPool & ThreadPool).
4. **Reporting**: Xuất báo cáo, tính compliance score.
5. **Dashboard**: Giao diện người dùng Web (FastAPI + Vite) để theo dõi kết quả.

## 📦 Cài Đặt

**Yêu cầu hệ thống:**
- OS: Ubuntu 24.04 LTS (được khuyến nghị)
- Python: 3.10 trở lên

**Cài đặt:**
```bash
# Clone repository
git clone https://github.com/ngocson2g/APP.git security-app
cd security-app

# Cài đặt ứng dụng (không cần cài dashboard nếu chỉ dùng CLI)
pip install -e .

# Cài đặt đầy đủ (kèm Dashboard API & Report generation)
pip install -e ".[dashboard]"

# Cài đặt môi trường dev (để test/lint)
pip install -e ".[dev]"
```

## 💻 Hướng Dẫn Sử Dụng

### 1. Chạy Kiểm Tra (CLI)

Chạy kiểm tra dựa trên file rule mẫu (yêu cầu `sudo` vì nhiều check cần quyền root):

```bash
sudo security-app data/canonical_ubuntu_24.04_lts.csv
```

**Các tuỳ chọn xuất báo cáo:**
```bash
# Xuất báo cáo dạng JSON
sudo security-app data/canonical_ubuntu_24.04_lts.csv --json-out result.json

# Xuất bộ báo cáo CSV (summary, rules, top_failing, by_severity)
sudo security-app data/canonical_ubuntu_24.04_lts.csv --csv-dir ./reports/
```

### 2. Truy Vấn Lịch Sử (Query)

```bash
# Xem các lần chạy gần đây
security-app query

# Lọc các rule 'failed' có mức độ 'critical' hoặc 'high'
security-app query --severity critical high --status fail

# Tìm kiếm theo keyword
security-app query -q "password" "ssh" --scope any
```

### 3. Web Dashboard

1. Khởi động Backend API (yêu cầu đã cài `.[dashboard]`):
   ```bash
   uvicorn apps.dashboard.backend.main:app --host 0.0.0.0 --port 8000
   ```
   *(Nếu đã bật tính năng xác thực, cần set biến môi trường `SECAPP_API_KEY`)*

2. Khởi động Frontend:
   ```bash
   cd apps/dashboard/frontend
   npm install
   npm run dev
   ```

## 🛠️ Hỗ Trợ Đóng Góp (Development)

Dự án sử dụng `ruff`, `black`, `isort` và `mypy` cho chất lượng code. CI pipeline đã được thiết lập qua GitHub Actions.

```bash
# Chạy Linter & Formatter
ruff check security_app/
black security_app/

# Chạy Test & Coverage
pytest --cov=security_app
```

## 📝 Giấy phép
Dự án được phân phối dưới giấy phép [MIT](LICENSE).
