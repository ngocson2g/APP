# security\_app — Ubuntu STIG/CIS checker & web dashboard

> Công cụ chạy checklist bảo mật (STIG/CIS) cho Ubuntu, ghi log theo từng rule, tổng hợp kết quả và hiển thị trên web dashboard (FastAPI + React).

---

## 1) Tính năng chính

* **CLI `security-app`** chạy checklist đầu vào (CSV/JSON/XML), trích lệnh từ phần *check* theo marker mặc định `"$ "`, thực thi an toàn (deny‑list), timeout + retry, và **ghi log theo từng rule**.
* **Log rotation** ở cấp thư mục run: tự động **chỉ giữ lại 20 bản chạy gần nhất**.
* **Không sinh summary JSON/CSV** – phù hợp yêu cầu hiện tại (chỉ log per‑rule); tổng hợp số liệu để in terminal và phục vụ dashboard.
* **Dashboard web** gồm backend FastAPI đọc thư mục logs → API `/api/runs`, `/api/runs/{id}/summary`, `/api/runs/{id}/rules`; frontend Vite + React hiển thị Overview, biểu đồ theo severity (Recharts) và bảng Top failing.
* **Yêu cầu sudo mặc định**: khi chạy CLI, chương trình sẽ tự re‑exec với `sudo` nếu cần. Có thể tắt bằng biến môi trường.

---

## 2) Kiến trúc & cấu trúc thư mục

```
APP
├─ data/                    # input mẫu (CSV / JSON / XCCDF XML)
├─ logs/                    # output per‑rule theo từng phiên chạy (được xoay vòng)
├─ security_app/            # package chính (CLI, core, parsers, policy, reporting, utils)
│  ├─ app/cli.py            # entry point: security-app
│  ├─ core/                 # thực thi, logger, runner (extract/plan/workers/merge/tuner)
│  ├─ parsers/              # CSV/JSON/XML → Rule
│  ├─ policy/               # denylist & secret masking
│  └─ reporting/            # compute_stats + in terminal
└─ apps/dashboard/          # web dashboard (backend FastAPI + frontend React)
```

---

## 3) Yêu cầu hệ thống

* Python 3.10+ (khuyến nghị 3.11+)
* Node.js 18+ và npm 9+ (cho frontend)
* Linux (đã thử trên Ubuntu/Kali)

---

## 4) Cài đặt nhanh

```bash
# 1) Tạo virtualenv & cài đặt Python package
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .

# 2) (Tuỳ chọn) cấu hình sudo mặc định
#   - Mặc định: BẬT yêu cầu sudo khi chạy CLI
#   - Tắt: export SECURITY_APP_REQUIRE_SUDO=false

# 3) Chạy thử với input mẫu
security-app data/canonical_ubuntu_24.04_lts.csv \
  --logs-dir logs \
  --workers 8 \
  --proc \
  --timeout 15 \
  --retries 1 \
  --top 10
```

Sau khi chạy, thư mục `logs/<yyyy-mm-dd_hh-mm-ss>/` sẽ có các file `rule-XXX_<safe_title>.log`.

---

## 5) Dashboard web

### Backend (FastAPI)

* Biến môi trường: `LOGS_DIR` trỏ tới thư mục gốc chứa các **run** (mỗi subfolder là một run).
* Chạy từ **root** dự án:

```bash
# (tuỳ chọn) tạo apps/dashboard/backend/.env
#   LOGS_DIR=../../../../logs
uvicorn apps.dashboard.backend.main:app --reload --host 0.0.0.0 --port 8000
```

* API:

  * `GET /api/runs` – danh sách các run (id, mtime, số file)
  * `GET /api/runs/{run_id}/summary` – tổng hợp (overview/by\_severity/top\_failing)
  * `GET /api/runs/{run_id}/rules` – danh sách rule đã parse từ log

### Frontend (Vite + React)

```bash
cd apps/dashboard/frontend
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev
```

* Truy cập: `http://localhost:5173/home`, `http://localhost:5173/reporting`.
* Trang Reporting: dropdown chọn run → thẻ Overview → biểu đồ By severity (Recharts) → bảng Top failing.

---

## 6) Sử dụng CLI chi tiết

**Tham số chính**

* `input` (*bắt buộc*): đường dẫn file checklist (`.csv` / `.json` / `.xml`).
* `--logs-dir`: thư mục gốc để ghi log (mặc định `logs`).
* `--workers`: số worker tối đa (mặc định **tự chọn** dựa trên pilot run & số CPU).
* `--proc`: dùng `ProcessPool` thay vì `ThreadPool`.
* `--timeout`: timeout mỗi lệnh (giây; `0`/`None` = không giới hạn).
* `--retries`: số lần thử lại (không tính lần đầu).
* `--top`: số item tối đa hiển thị ở "Top failing rules" khi in terminal.

**Cơ chế an toàn & riêng tư**

* **Deny‑list** chặn các lệnh nguy hiểm (`rm -rf /`, fork bomb, `shutdown`, `mkfs`, `dd of=/dev`, `curl|sh`, ...). Lệnh bị chặn vẫn được ghi vào log với lý do.
* **Mask bí mật**: tự động che `password=`, `token=`, `Bearer ...`, `sshpass -p`, `--password ...` trong log.

**Trích lệnh & thực thi**

* Lệnh được trích từ `check` bằng marker `"$ "` (hỗ trợ dòng tiếp ). Có thể chứa nhiều lệnh cho một rule.
* Mỗi rule ghi **1 file log**; trong file có ID, Title, Severity, phần Check (đã mask bí mật) và block kết quả từng lệnh: `RC=… | OK=… | duration…`, kèm stdout/stderr.

**Tự điều chỉnh số worker**

* Trong lần chạy, chương trình lấy mẫu thời gian vài task đầu (pilot) rồi ước lượng số worker phù hợp (khác nhau giữa thread/process). Bạn vẫn có thể chỉ định `--workers` để ghi đè.

---

## 7) Biến môi trường & cấu hình

* `SECURITY_APP_REQUIRE_SUDO`: `1/true/yes` (mặc định) để **bật** yêu cầu sudo tự động; `0/false/no/off` để **tắt**.
* `LOGS_DIR`: (Backend) đường dẫn thư mục chứa các run logs.
* Frontend `.env`: `VITE_API_BASE_URL=http://localhost:8000`.
* Các hằng số khác (có thể xem trong mã):

  * `CMD_MARKER="$ "` — marker trích lệnh
  * `LOG_ROTATE_KEEP=20` — số run gần nhất được giữ lại
  * `DEFAULT_SHELL_TIMEOUT=10` — timeout mặc định cho lệnh (giây)
  * `RETRY_ATTEMPTS=1`, `RETRY_DELAY_SEC=0.5`, `RETRY_ON_TIMEOUT=true`

---

## 8) Troubleshooting

* **`404 GET /api/runs`** khi mở frontend: hãy đảm bảo backend FastAPI đang chạy **và** `LOGS_DIR` trỏ đúng thư mục có các subfolder run.
* **Không thấy dữ liệu trong Reporting**: cần có ít nhất một lần chạy CLI để sinh log per‑rule.
* **CORS**: backend đang cho phép `allow_origins=["*"]` để dễ dev; khi deploy sản xuất, nên giới hạn theo domain.
* **Không muốn dùng sudo**: export `SECURITY_APP_REQUIRE_SUDO=false` trước khi chạy CLI.

---

## 9) Phát triển & đóng góp

* Style: Python với `dataclasses`, module hoá runner (extract/plan/workers/merge/tuner) để dễ test.
* Gợi ý viết test cho: parsers (CSV/JSON/XML), safety policy, command extractor, stats.
* PR/Issue: vui lòng mô tả rõ input mẫu, môi trường và log liên quan.

---

## 10) Giấy phép

Cập nhật sau.

---

## 11) Ghi chú triển khai/định hướng

* (Tuỳ chọn) thêm endpoint trả về bảng chi tiết đầy đủ để mở rộng UI.
* (Tuỳ chọn) bật/tắt log rotation qua cấu hình.
* (Tuỳ chọn) xuất báo cáo JSON cho CI/CD.
