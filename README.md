# security-app — Ubuntu 24.04 LTS Security Checking Toolkit

[🇻🇳 Tiếng Việt](#-ti%E1%BA%BFng-vi%E1%BB%87t) · [🇬🇧 English](#-english)

---

## 🔎 Summary

`security-app` is a CLI + API + Dashboard toolkit to **validate and observe system hardening** on Ubuntu 24.04 LTS. It ingests **JSON/CSV/XML** checklists, extracts and executes **safe-guarded commands** (deny‑list, timeout, retry), **masks secrets** in logs, and exports **JSON/CSV/Excel/PDF** reports.

- Safe by design: deny‑list, risk scoring, environment sanitization, secret masking
- Smart execution: pre‑run estimation, pilot sampling, auto‑tuned parallel workers
- Observability: per‑rule logs, run rotation, rich stats, drill‑down dashboard

> Works standalone via CLI or with the Dashboard (FastAPI backend + Vite/React frontend).

---

## 📁 Repository Structure (high-level)

```
APP/
 ├─ security_app/
 │   ├─ core/            # runners, command exec, estimator, tuner
 │   ├─ policy/          # safety (deny-list), risk scoring, secret masking
 │   ├─ parsers/         # input adapters: JSON/CSV/XML → Rule schema
 │   ├─ reporting/       # stats, terminal report, JSON/CSV exporters
 │   ├─ runtime/         # sudo handling, environment, paths
 │   ├─ utils/           # normalization, text helpers (_safe_name, ...)
 │   └─ app/             # run orchestration (run_once), CLI handlers
 └─ apps/dashboard/
     ├─ backend/         # FastAPI (summary, rules, export excel/pdf)
     └─ frontend/        # Vite/React UI (Top failing, drill-down, export)
```

---

## ⚙️ Requirements

- **Python ≥ 3.10**
- (Dashboard) **Node.js ≥ 18** + npm/pnpm/yarn

---

## 🚀 Quick Start

### Install CLI

```bash
# recommended virtualenv
python -m venv .venv && source .venv/bin/activate

# from repo root
pip install -e .

# verify
security-app --help
```

### Run a checklist (CLI)

```bash
security-app data/canonical_ubuntu_24.04_lts.json
```

This will: parse → (silently) estimate workers → execute with safety guards → write **per‑rule logs** under `logs/<YYYY-MM-DD_HH-MM-SS>/` → print a terminal report.

### Useful CLI switches

```bash
# Show PRE-RUN estimate table (and still execute)
security-app --estimate data/list.json

# Only plan (do not execute)
security-app --plan-only data/list.json

# Control parallelism & execution model
security-app --workers 8 --proc data/list.json   # --proc → processes (else threads)

# Timeouts & retries
security-app --timeout 20 --retries 2 data/list.json

# Logs & top failing limit
security-app --logs-dir mylogs --top 15 data/list.json

# Export stats to JSON & CSV bundle
security-app --json-out out/report.json --csv-out-dir out/csv data/list.json
```

> Without `--estimate/--plan-only`, the **estimator still runs** to suggest workers, but it **does not print** the table.

---

## 🧩 Input Checklist Format

Accepts **JSON / CSV / XML**, normalized to a common schema with at least: `id`, `title`, `severity`, `description`, `check`, `fix`.

**JSON example**

```json
[
  {
    "id": "UBTU-SSH-0001",
    "title": "Disable root SSH login",
    "severity": "high",
    "description": "Root login via SSH should be disabled.",
    "check": "$ grep -i '^PermitRootLogin' /etc/ssh/sshd_config\n$ systemctl status ssh",
    "fix": "$ sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config\n$ systemctl restart ssh"
  }
]
```

**CSV suggestion**

```
id,title,severity,description,check,fix
UBTU-SSH-0001,Disable root SSH login,high,Root login via SSH should be disabled.,"$ grep -i '^PermitRootLogin' /etc/ssh/sshd_config
$ systemctl status ssh","$ sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
$ systemctl restart ssh"
```

> In `check`, start shell lines with `` marker for precise extraction.

---

## 🛡️ Safety & Defaults

- **Sudo**: required by default; set `SECURITY_APP_REQUIRE_SUDO=0|false|no|off` to disable auto `sudo` re-exec.
- **Deny‑list**: blocks dangerous patterns (e.g., `rm -rf /`, fork‑bomb, `mkfs.*`, `curl|sh`, `wget|sh`, …).
- **Secret masking**: masks passwords/tokens/bearers/`sshpass -p`/`--password` from commands and logs.
- **Risk scoring**: flags risky writes/paths (e.g., `/etc`, `/var/log`, `sed -i`, `sysctl -w`, `systemctl ...`).
- **Timeout/Retry**: default **10s** timeout, **1** retry with **0.5s** delay; retry on timeout enabled.
- **Logs**: default `logs/`, per‑run folder by timestamp; keep last **50** runs (rotation).

Environment variables:

- `SECURITY_APP_REQUIRE_SUDO` — require root (default **on**)
- `SECAPP_REPORT_DIR` — mirror exported Excel/PDF to a persistent folder
- (Dashboard BE) `ALLOWED_ORIGINS` — CORS whitelist (comma‑separated)

---

## 📊 Logs & Reports

**Per‑rule logs** in `logs/<run_id>/rule-XXX_<safe_title>.log` contain:

- Rule metadata (id, title, severity)
- **Check** section (masked)
- **Command Results**: each `$ ...` with `rc`, `ok/fail`, `duration`, `stdout/stderr`

**Exports**

```bash
# JSON summary
security-app --json-out out/report.json data/list.json

# CSV bundle (multiple tables)
security-app --csv-out-dir out/csv data/list.json
```

---

## 🖥️ Dashboard (API + UI)

### Backend (FastAPI)

```bash
# from APP/apps/dashboard/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Key endpoints**

- `GET /api/runs` – list runs
- `GET /api/runs/{run_id}/summary`
- `GET /api/runs/{run_id}/rules`
- `GET /api/runs/{run_id}/rule/{index}`
- `GET /api/runs/{run_id}/export/{excel|pdf}`
- `GET /api/runs/timeseries`

### Frontend (Vite/React)

```bash
# from APP/apps/dashboard/frontend
npm install
npm run dev   # http://localhost:5173
```

**UI features**: run list, trends, **Top failing rules**, **Denied by policy**, **rule drill‑down**, **Export Excel/PDF**.

> Tip: set `SECAPP_REPORT_DIR` so backend keeps a copy of exported files under `<SECAPP_REPORT_DIR>/<run_id>/`.

---

## 🧹 Cleanup

Dry‑run prints a plan and does not delete anything.

```bash
# plan
security-app --cleanup --logs-dir logs --report-dir "$SECAPP_REPORT_DIR"

# execute
security-app --cleanup --no-dry-run --logs-dir logs --report-dir "$SECAPP_REPORT_DIR"
```

Options: `--keep-runs N` (default 50), `--runs-older-than-days D`, `--compress-runs-older-than-days D`, `--keep-reports-days D`, `--tmp-older-than-hours H`.

---

## 🤝 Contributing

- Use clear commit messages and small PRs.
- Keep modules cohesive (`parsers/`, `core/`, `policy/`, `reporting/`, `runtime/`, `utils/`).
- Add or update examples in `data/` for new rule types.
- Ensure commands extracted from `check` remain safe and idempotent.

---

## 📄 License

TBD (e.g., MIT). Update this section to match your actual license.

---

## 📬 Contact

Maintainer: Nông Ngọc Sơn · (update contact info)

---

# 🇻🇳 Tiếng Việt

## 🔎 Tóm tắt

`security-app` là bộ công cụ **kiểm định & quan sát hardening** cho Ubuntu 24.04 LTS. Ứng dụng nhận **JSON/CSV/XML** checklist, trích & thực thi lệnh **có kiểm soát** (deny‑list, timeout, retry), **che bí mật** trong log và **xuất báo cáo** định dạng **JSON/CSV/Excel/PDF**.

- An toàn: deny‑list, chấm điểm rủi ro, làm sạch môi trường, che bí mật
- Thông minh: ước lượng trước, pilot sampling, tự gợi ý số worker tối ưu
- Quan sát: log theo từng rule, xoay vòng run, thống kê phong phú, dashboard drill‑down

---

## 📁 Cấu trúc thư mục (tổng quan)

```
APP/
 ├─ security_app/
 │   ├─ core/            # thực thi, estimator, tuner
 │   ├─ policy/          # deny-list, risk, mask bí mật
 │   ├─ parsers/         # chuyển đổi JSON/CSV/XML → Rule
 │   ├─ reporting/       # thống kê, in terminal, xuất JSON/CSV
 │   ├─ runtime/         # sudo, môi trường, đường dẫn
 │   ├─ utils/           # chuẩn hoá, text (_safe_name, ...)
 │   └─ app/             # điều phối run (run_once), handler CLI
 └─ apps/dashboard/
     ├─ backend/         # FastAPI (summary, rules, export excel/pdf)
     └─ frontend/        # Vite/React UI (Top failing, drill-down, export)
```

---

## ⚙️ Yêu cầu

- **Python ≥ 3.10**
- (Dashboard) **Node.js ≥ 18** + npm/pnpm/yarn

---

## 🚀 Bắt đầu nhanh

### Cài CLI

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
security-app --help
```

### Chạy checklist

```bash
security-app data/canonical_ubuntu_24.04_lts.json
```

Luồng: parse → (ước lượng ngầm để chọn workers) → thực thi an toàn → ghi **log theo rule** trong `logs/<YYYY-MM-DD_HH-MM-SS>/` → in báo cáo terminal.

### Tuỳ chọn hay dùng

```bash
# Hiển thị bảng ước lượng rồi vẫn chạy
security-app --estimate data/list.json

# Chỉ lập kế hoạch (không chạy lệnh)
security-app --plan-only data/list.json

# Điều khiển song song & mô hình thực thi
security-app --workers 8 --proc data/list.json

# Timeout & retry
security-app --timeout 20 --retries 2 data/list.json

# Logs & giới hạn top failing
security-app --logs-dir mylogs --top 15 data/list.json

# Xuất thống kê JSON & CSV bundle
security-app --json-out out/report.json --csv-out-dir out/csv data/list.json
```

> Không bật `--estimate/--plan-only` thì **vẫn ước lượng** để gợi ý `workers`, chỉ là **không in bảng**.

---

## 🧩 Định dạng checklist

Chấp nhận **JSON / CSV / XML**; schema tối thiểu: `id`, `title`, `severity`, `description`, `check`, `fix`.

**Ví dụ JSON**

```json
[
  {
    "id": "UBTU-SSH-0001",
    "title": "Disable root SSH login",
    "severity": "high",
    "description": "Root login via SSH should be disabled.",
    "check": "$ grep -i '^PermitRootLogin' /etc/ssh/sshd_config\n$ systemctl status ssh",
    "fix": "$ sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config\n$ systemctl restart ssh"
  }
]
```

**Gợi ý CSV**

```
id,title,severity,description,check,fix
UBTU-SSH-0001,Disable root SSH login,high,Root login via SSH should be disabled.,"$ grep -i '^PermitRootLogin' /etc/ssh/sshd_config
$ systemctl status ssh","$ sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
$ systemctl restart ssh"
```

> Trong `check`, nên bắt đầu dòng lệnh bằng `` để extractor nhận diện chính xác.

---

## 🛡️ An toàn & Mặc định

- **Sudo**: bật mặc định; đặt `SECURITY_APP_REQUIRE_SUDO=0|false|no|off` để tắt tự `sudo`.
- **Deny‑list**: chặn mẫu lệnh nguy hiểm (`rm -rf /`, fork‑bomb, `mkfs.*`, `curl|sh`, `wget|sh`, …).
- **Che bí mật**: ẩn password/token/bearer/`sshpass -p`/`--password` trong lệnh & log.
- **Chấm điểm rủi ro**: phát hiện ghi/chạm đường dẫn nhạy cảm (`/etc`, `/var/log`, `sed -i`, `sysctl -w`, `systemctl ...`).
- **Timeout/Retry**: mặc định **10s**, **retry 1 lần**, delay **0.5s**, retry khi timeout.
- **Logs**: mặc định `logs/`, thư mục theo timestamp; giữ **50** run gần nhất.

Biến môi trường:

- `SECURITY_APP_REQUIRE_SUDO` — yêu cầu root (mặc định bật)
- `SECAPP_REPORT_DIR` — nơi lưu bản sao file Excel/PDF export
- (Dashboard BE) `ALLOWED_ORIGINS` — danh sách CORS cho frontend

---

## 📊 Logs & Báo cáo

**Per‑rule logs**: `logs/<run_id>/rule-XXX_<safe_title>.log` gồm metadata, **Check** (đã che), và **Command Results** (mỗi `$ ...` có `rc`, `ok/fail`, `duration`, `stdout/stderr`).

**Xuất báo cáo**

```bash
security-app --json-out out/report.json data/list.json
security-app --csv-out-dir out/csv data/list.json
```

---

## 🖥️ Dashboard (API + UI)

### Backend (FastAPI)

```bash
cd APP/apps/dashboard/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Endpoints**

- `GET /api/runs` – danh sách run
- `GET /api/runs/{run_id}/summary`
- `GET /api/runs/{run_id}/rules`
- `GET /api/runs/{run_id}/rule/{index}`
- `GET /api/runs/{run_id}/export/{excel|pdf}`
- `GET /api/runs/timeseries`

### Frontend (Vite/React)

```bash
cd APP/apps/dashboard/frontend
npm install
npm run dev   # http://localhost:5173
```

**Tính năng**: danh sách run, xu hướng, **Top failing**, **Denied by policy**, **drill‑down rule**, **Export Excel/PDF**.

> Mẹo: đặt `SECAPP_REPORT_DIR` để backend tự lưu bản sao file export theo `<SECAPP_REPORT_DIR>/<run_id>/`.

---

## 🧹 Dọn dẹp

```bash
# Xem kế hoạch (không xoá)
security-app --cleanup --logs-dir logs --report-dir "$SECAPP_REPORT_DIR"

# Thực thi xoá/nén
security-app --cleanup --no-dry-run --logs-dir logs --report-dir "$SECAPP_REPORT_DIR"
```

Tuỳ chọn: `--keep-runs N` (mặc định 50), `--runs-older-than-days D`, `--compress-runs-older-than-days D`, `--keep-reports-days D`, `--tmp-older-than-hours H`.

---

## 🤝 Đóng góp

- Commit rõ ràng, PR nhỏ gọn.
- Giữ module mạch lạc (`parsers/`, `core/`, `policy/`, `reporting/`, `runtime/`, `utils/`).
- Bổ sung ví dụ trong `data/` khi có rule type mới.
- Đảm bảo lệnh trong `check` an toàn, idempotent.

---

## 📄 Giấy phép

TBD (ví dụ MIT). Cập nhật phần này theo giấy phép thực tế.

---

## 📬 Liên hệ

Maintainer: Nông Ngọc Sơn · (cập nhật email/số liên hệ)

