# 🛡️ Evolving Soul AI — AI Ghi Nhớ Chủ Nhân & Thừa Kế Di Sản Số

<p align="center">
  <b>Languages / Các ngôn ngữ:</b>
  <a href="#-english"><b>English</b></a> |
  <a href="#-tiếng-việt"><b>Tiếng Việt</b></a> |
  <a href="README_zh.md"><b>简体中文</b></a> |
  <a href="README_fr.md"><b>Français</b></a> |
  <a href="README_hi.md"><b>हिन्दी</b></a>
</p>

<p align="center">
  <a href="#-license--attribution"><img src="https://img.shields.io/badge/License-MIT%20(Attribution%20Required)-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/Version-v3.2.005-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.9%2B-green.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/UI-Streamlit%20White%20Theme-FF4B4B.svg" alt="Streamlit UI">
  <img src="https://img.shields.io/badge/Protocol-MCP%202.x-8A2BE2.svg" alt="Model Context Protocol">
  <img src="https://img.shields.io/badge/CLI-Rich%20Terminal-00B4D8.svg" alt="Rich CLI">
  <img src="https://img.shields.io/badge/API-FastAPI%20Gateway-009688.svg" alt="FastAPI Gateway">
  <a href="https://github.com/hahuuhung/evolving-soul-ai/actions/workflows/e2e_ci.yml"><img src="https://github.com/hahuuhung/evolving-soul-ai/actions/workflows/e2e_ci.yml/badge.svg" alt="CI"></a>
  <a href="#-license--attribution"><img src="https://img.shields.io/badge/Author-HÀ%20HỮU%20HƯNG%20(1985)-orange.svg" alt="Author"></a>
</p>

<p align="center">
  <img src="Future.png" alt="Evolving Soul AI Banner" width="100%" style="border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
</p>

---

<a name="-english"></a>
# 🇬🇧 English

## 🛡️ Evolving Soul AI — Lightweight Non-Biometric Owner Recognition & Digital Legacy Succession

> **"Faces may age, fingerprints may fade, devices may change — but the 'Digital Soul' and the bond between Owner and AI co-evolve over time."**

**Evolving Soul AI** is a lightweight, privacy-first open-source AI that runs on a standard CPU. It **recognizes, remembers and adapts to its owner** through a zero-knowledge, 5-pillar behavioral profile that evolves over decades — without daily face, iris or fingerprint scans. A **Dead Man's Switch** (default 730 days of owner inactivity) hands digital assets to a designated heir after dual authentication: family knowledge **and** a face match.

### 🔐 V3 security model

| Layer | How it works |
|---|---|
| Vault | A random 32-byte master key encrypts the profile (Fernet). The key is **wrapped** by the owner's passphrase (Scrypt) and, once a legacy is sealed, also by the family secret — so the heir never needs the owner's passphrase. No key is hard-coded. |
| Secrets | Birth date, family names, linked accounts, password habits and device are stored only as **HMAC-SHA256** digests (keyed by the vault). |
| Owner verification | Behavioral second factor *after* the passphrase. Sensitive actions (re-initialising the profile, sealing a legacy, changing the passphrase) require a successful verification in the last 15 minutes. |
| Brute force | 5 consecutive failures → temporary lockout (15 min, doubling each time), per channel (unlock, owner, heir). |
| Legacy assets | Encrypted a second time with a key derived from the family secret — unreadable even with the owner's passphrase alone. |
| Audit | Hash-chained `vault/audit.jsonl` anchored in the encrypted profile; any edit or deletion is detected. No personal data in the log. |
| Concurrency | An inter-process file lock lets the Web UI, CLI, MCP server and REST API share one vault safely. |

### 🧬 The 5 pillars (14-dimensional vector)

| Pillar | Dims | Signal |
|---|---|---|
| OAuth trust | 4 | Google / Apple / Facebook digest matches + linked ratio |
| Family lore | 2 | Birth-date match, coverage of **full** family names (diacritics- and relation-word-insensitive) |
| Stylometry | 3 | Average word length, sentence length, punctuation density (+ known-keyword overlap and traits) |
| Password habit | 3 | Length, character-class diversity, prefix & structure habit (`HungAI@1985#Secret` → `ULUSDSUL`) — never the password |
| Device | 2 | Trusted-device and OS-family matches |

Trust score = weighted mean (OAuth 0.15 · Family 0.25 · Style 0.35 · Password 0.20 · Device 0.05), owner if **≥ 0.62** *and* the knowledge gate passes (birth date or ≥ 50 % of family names). Calibrated on a synthetic population (`tools/calibrate_weights.py`): **FRR ≈ 4.7 %, stranger FAR 0 %, informed-family-member FAR ≈ 3.8 %**.

Continual learning on the behavioral dimensions:
$$S_t = (1 - \alpha) \cdot S_{t-1} + \alpha \cdot X_t, \quad \alpha = 0.15$$

### 🕊️ Dead Man's Switch

- Clock resets every time the owner **verifies successfully** (unlocking the vault alone does not count). Warning at 90 % of the threshold.
- Heir rule — SFace face embedding (OpenCV YuNet + SFace, cosine ≥ 0.363): knowledge ≥ 70 %. Low-assurance histogram fallback or no face lock: knowledge ≥ 85 %.
- If the owner comes back and verifies, a completed handover is revoked.

### 🚀 Quickstart

```bash
pip install -r requirements.txt          # Python 3.9+; the MCP server needs Python 3.10+
```

| Interface | Command |
|---|---|
| Web UI (Streamlit White Theme) | `streamlit run app_ui.py` → create a vault with your passphrase on first run |
| Rich CLI | `python soul_cli.py init …`, `status`, `verify`, `legacy status/seal/claim`, `persona` (add `--json` for scripts) |
| MCP server (Claude Desktop, Antigravity, Cursor) | `python soul_cli.py mcp` (stdio) or `--sse`; see `mcp_config.json` |
| REST API (FastAPI + Swagger) | `python soul_cli.py serve --port 8080` → `http://localhost:8080/docs` |

Environment variables:

| Variable | Purpose |
|---|---|
| `EVOLVING_SOUL_PASSPHRASE` | Vault passphrase for CLI / MCP / API (and optional auto-unlock of the Web UI). Use only on a personal machine. |
| `EVOLVING_SOUL_VAULT_DIR` | Vault directory (default `vault/`) |
| `EVOLVING_SOUL_MODEL_DIR` | Folder with the YuNet / SFace ONNX models (downloaded and SHA-256-checked on first use) |
| `EVOLVING_SOUL_DEMO=1` | Demo mode: enables the "days offline" simulation slider / `--simulate-days` |
| `SOUL_API_KEY` | **Required** `X-API-Key` for owner endpoints of the REST API (no default) |
| `SOUL_API_CORS_ORIGINS` | Comma-separated allowed origins (default: none) |

Upgrading from V2: start the Web UI — it detects `vault/owner_soul_v2.enc`, asks for a new passphrase and finishes the migration at your first successful verification.

### 🧪 Tests

```bash
pytest -v
```
~96 tests: crypto & vault, features & FAR/FRR calibration, biometrics (real YuNet/SFace on OpenCV sample faces), Dead Man's Switch, migration, Streamlit UI (AppTest), CLI / MCP / REST gateways, and `tests/test_e2e_suite.py` (12 end-to-end scenarios). CI runs on Ubuntu, Windows and macOS with Python 3.9 and 3.12.

Step-by-step upgrade notes: [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md).

### 📜 License & Attribution

Distributed under the **MIT License with Mandatory Author Attribution**.

Any reproduction, derivative work, or commercial integration **MUST PROMINENTLY DISPLAY THE ORIGINAL AUTHOR CREDIT**:

> * **Original Author:** **HÀ HỮU HƯNG (1985) — 8X GENERATION AI ENGINEER**
> * **Core Architecture:** Lightweight Non-Biometric Evolving Owner Recognition & 2-Year Digital Legacy Succession (Evolving Soul AI).

---

<br>
<hr>
<br>

<a name="-tiếng-việt"></a>
# 🇻🇳 Tiếng Việt

## 🛡️ Evolving Soul AI — Hệ Thống AI Nhỏ Gọn Ghi Nhớ & Nhận Diện Chủ Nhân Phi Sinh Trắc Học & Thừa Kế Di Sản Số

> **"Khuôn mặt có thể già đi, vân tay có thể mòn, thiết bị có thể thay đổi — nhưng 'Linh hồn số' và sự gắn kết giữa Chủ nhân với AI sẽ cùng nhau tiến hóa theo thời gian."**

**Evolving Soul AI** là mô hình AI mã nguồn mở siêu nhẹ chạy trên CPU thông thường, **nhận diện, ghi nhớ và thích nghi với Chủ nhân** qua hồ sơ hành vi 5 trụ cột được băm một chiều (Zero-Knowledge) và tiến hóa theo năm tháng — không cần quét khuôn mặt hay vân tay hằng ngày. **Dead Man's Switch** (mặc định 730 ngày Chủ nhân vắng mặt) chuyển giao tài sản số cho người thừa kế sau khi xác thực kép: tri thức gia đình **và** khớp khuôn mặt.

### 🔐 Mô hình bảo mật V3

| Lớp | Cách hoạt động |
|---|---|
| Két sắt | Khóa chủ ngẫu nhiên 32 byte mã hóa hồ sơ (Fernet). Khóa được **bọc** bởi passphrase của Chủ nhân (Scrypt) và, khi đã niêm phong di sản, bởi mật ước gia đình — người thừa kế không cần biết passphrase. Không còn khóa viết cứng trong mã. |
| Bí mật | Ngày sinh, tên người thân, tài khoản liên kết, thói quen mật khẩu, thiết bị chỉ lưu dạng **HMAC-SHA256**. |
| Xác minh Chủ nhân | Lớp thứ hai *sau* passphrase. Thao tác nhạy cảm (khởi tạo lại, niêm phong di sản, đổi passphrase) cần xác minh thành công trong 15 phút gần nhất. |
| Chống dò | Sai 5 lần liên tiếp → khóa tạm 15 phút, nhân đôi mỗi lần; tách theo kênh (mở két, Chủ nhân, người thừa kế). |
| Tài sản di sản | Mã hóa thêm một lớp bằng khóa suy từ mật ước — chỉ có passphrase của Chủ nhân cũng không đọc được. |
| Nhật ký | `vault/audit.jsonl` chuỗi băm, neo trong hồ sơ đã mã hóa; sửa hay xóa đều bị phát hiện. Không chứa dữ liệu cá nhân. |
| Đồng thời | Khóa file liên tiến trình cho phép Web UI, CLI, MCP và REST API dùng chung một két an toàn. |

### 🧬 5 trụ cột (vector 14 chiều)

| Trụ cột | Chiều | Tín hiệu |
|---|---|---|
| OAuth Trust | 4 | Khớp digest Google / Apple / Facebook + tỷ lệ liên kết |
| Ký ức gia đình | 2 | Khớp ngày sinh, độ phủ **tên đầy đủ** người thân (không phụ thuộc dấu và từ quan hệ) |
| Văn phong | 3 | Độ dài từ, độ dài câu, mật độ dấu câu (+ từ khóa quen thuộc và cá tính) |
| Thói quen mật khẩu | 3 | Độ dài, độ đa dạng lớp ký tự, tiền tố & cấu trúc (`HungAI@1985#Secret` → `ULUSDSUL`) — không bao giờ lưu mật khẩu |
| Thiết bị | 2 | Thiết bị tin cậy, họ hệ điều hành |

Điểm tin cậy = trung bình có trọng số (OAuth 0.15 · Gia đình 0.25 · Văn phong 0.35 · Mật khẩu 0.20 · Thiết bị 0.05); là Chủ nhân khi **≥ 0.62** *và* qua cổng tri thức (đúng ngày sinh hoặc ≥ 50% tên người thân). Hiệu chỉnh trên tập giả lập (`tools/calibrate_weights.py`): **FRR ≈ 4.7%, FAR người lạ 0%, FAR người nhà biết ngày sinh & tên người thân ≈ 3.8%**.

Học liên tục trên các chiều hành vi:
$$S_t = (1 - \alpha) \cdot S_{t-1} + \alpha \cdot X_t, \quad \alpha = 0.15$$

### 🕊️ Dead Man's Switch

- Đồng hồ đặt lại mỗi khi Chủ nhân **xác minh thành công** (chỉ mở két thì không tính). Cảnh báo ở 90% ngưỡng.
- Người thừa kế — có mẫu khuôn mặt SFace (OpenCV YuNet + SFace, cosine ≥ 0.363): tri thức ≥ 70%. Fallback histogram (bảo đảm thấp) hoặc không có khóa khuôn mặt: tri thức ≥ 85%.
- Chủ nhân quay lại và xác minh thành công → quyền tiếp quản tự động bị thu hồi.

### 🚀 Cài đặt & khởi chạy

```bash
pip install -r requirements.txt          # Python 3.9+; MCP Server cần Python 3.10+
```

| Cổng | Lệnh |
|---|---|
| Web UI (Streamlit White Theme) | `streamlit run app_ui.py` → lần đầu tạo két sắt bằng passphrase của bạn |
| Rich CLI | `python soul_cli.py init …`, `status`, `verify`, `legacy status/seal/claim`, `persona` (thêm `--json` cho script) |
| MCP Server (Claude Desktop, Antigravity, Cursor) | `python soul_cli.py mcp` (stdio) hoặc `--sse`; xem `mcp_config.json` |
| REST API (FastAPI + Swagger) | `python soul_cli.py serve --port 8080` → `http://localhost:8080/docs` |

Biến môi trường:

| Biến | Ý nghĩa |
|---|---|
| `EVOLVING_SOUL_PASSPHRASE` | Passphrase két sắt cho CLI / MCP / API (và tự mở két cho Web UI). Chỉ dùng trên máy cá nhân. |
| `EVOLVING_SOUL_VAULT_DIR` | Thư mục két sắt (mặc định `vault/`) |
| `EVOLVING_SOUL_MODEL_DIR` | Thư mục model ONNX YuNet / SFace (tự tải và kiểm tra SHA-256 lần đầu) |
| `EVOLVING_SOUL_DEMO=1` | Chế độ demo: bật thanh trượt / `--simulate-days` mô phỏng số ngày offline |
| `SOUL_API_KEY` | `X-API-Key` **bắt buộc** cho các endpoint của Chủ nhân (không có mặc định) |
| `SOUL_API_CORS_ORIGINS` | Danh sách origin được phép, phân tách bằng dấu phẩy (mặc định: không) |

Nâng cấp từ V2: mở Web UI — ứng dụng phát hiện `vault/owner_soul_v2.enc`, hỏi passphrase mới và hoàn tất migration ở lần xác minh thành công đầu tiên.

### 🧪 Kiểm thử

```bash
pytest -v
```
~96 test: mật mã & két sắt, đặc trưng & hiệu chỉnh FAR/FRR, sinh trắc (YuNet/SFace thật trên ảnh mẫu OpenCV), Dead Man's Switch, migration, giao diện Streamlit (AppTest), cổng CLI / MCP / REST, và `tests/test_e2e_suite.py` (12 kịch bản đầu-cuối). CI chạy trên Ubuntu, Windows, macOS với Python 3.9 và 3.12.

Ghi chép chi tiết từng giai đoạn nâng cấp: [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md).

### 📜 Giấy Phép & Bản Quyền Tác Giả

Dự án được phát hành dưới giấy phép **MIT License with Mandatory Author Attribution**.

Mọi bản sao, dẫn xuất, giao diện người dùng hoặc sản phẩm tích hợp mã nguồn này **BẮT BUỘC PHẢI GHI RÕ NGUỒN GỐC TÁC GIẢ**:

> * **Tác giả sáng lập (Original Author):** **HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X**
> * **Kiến trúc cốt lõi:** Mô hình AI Nhỏ Gọn Ghi Nhớ & Nhận Diện Chủ Nhân Phi Sinh Trắc Học & Thừa Kế Di Sản Số 2 Năm (Evolving Soul AI).

*Phát triển với tâm huyết vì một không gian AI cá nhân hóa an toàn, bảo mật và nhân văn — Hà Hữu Hưng (1985).*
