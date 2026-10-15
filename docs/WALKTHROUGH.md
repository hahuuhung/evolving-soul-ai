# Walkthrough nâng cấp Evolving Soul AI V3

Tác giả sáng lập: **HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X**

Tài liệu này ghi lại từng giai đoạn nâng cấp từ V2 lên V3. Mỗi giai đoạn là một commit riêng.

---

## Giai đoạn 0 — Vá bảo mật khẩn cấp & tương thích Python 3.9

**Vấn đề đã sửa**

| # | Lỗ hổng V2 | Cách sửa |
|---|---|---|
| 1 | Ai cũng ghi đè được hồ sơ Chủ nhân ở Tab 1 | `register_owner()` ném `PermissionError` nếu két sắt đã có hồ sơ, trừ khi `force=True` **và** `owner_verified=True`. UI khóa nút đăng ký, chỉ mở khi Chủ nhân đã xác minh ở Tab 2 và tick xác nhận. |
| 2 | Ai cũng tự đặt mình làm người thừa kế | `setup_digital_legacy()` yêu cầu `owner_session_verified=True`. UI chỉ bật nút niêm phong sau khi xác minh Chủ nhân trong phiên (`st.session_state["owner_verified"]`). |
| 3 | Kéo thanh trượt tới 1000 ngày để mở di sản | `simulated_days_offline` chỉ có hiệu lực khi `demo_mode=True` (hoặc biến môi trường `EVOLVING_SOUL_DEMO=1`). Ngoài demo bị bỏ qua và ghi log cảnh báo; thanh trượt chỉ hiện trong chế độ demo. |
| 4 | Tab 3 in toàn bộ hồ sơ đã giải mã (kể cả tài sản số) | Thay `st.json(profile)` bằng `mask_profile()` — chỉ lộ tên trường, độ dài và 8 ký tự đầu SHA-256. |
| 5 | Chèn HTML qua tên chủ nhân / người thừa kế / tài sản | `esc()` (`html.escape`) mọi giá trị người dùng trước khi đưa vào `unsafe_allow_html`. |
| 6 | Cú pháp `dict \| None` làm vỡ Python 3.9 | Thêm `from __future__ import annotations`. |
| 7 | `str(None)` → `"None"` khi chưa chọn ngày sinh; ngưỡng 730 viết cứng ở UI | Kiểm tra rỗng; đọc `threshold_days` từ trạng thái. |

**Chạy chế độ demo**

```bash
# Linux / macOS
EVOLVING_SOUL_DEMO=1 streamlit run app_ui.py
# Windows PowerShell
$env:EVOLVING_SOUL_DEMO="1"; streamlit run app_ui.py
```

**Kiểm thử**: `test_security_regressions.py` — 5 test hồi quy (ghi đè hồ sơ, niêm phong khi chưa xác minh, giả lập ngày ngoài demo, giả lập ngày trong demo, đọc biến môi trường). Tổng: 11/11 pass.

**Còn tồn tại (xử lý ở các giai đoạn sau)**: khóa vault mặc định viết cứng, băm 4 chữ số, sinh trắc học histogram.

---

## Giai đoạn 1 — Package `evolving_soul/` & két sắt an toàn

**Mô-đun mới**

| Mô-đun | Vai trò |
|---|---|
| `config.py` | `Settings` tập trung: alpha=0.15, ngưỡng 0.72, 730 ngày, trọng số 5 trụ cột, giới hạn chống dò, `kdf_n`. `Settings.from_env()` đọc `EVOLVING_SOUL_DEMO`, `EVOLVING_SOUL_VAULT_DIR`, `EVOLVING_SOUL_MODEL_DIR`. |
| `errors.py` | Ngoại lệ có kiểu: `VaultLockedError`, `VaultCorruptError`, `VaultNotFoundError`, `ProfileExistsError`, `OwnerNotVerifiedError`, `LockedOutError`. |
| `crypto.py` | Scrypt (salt 16 byte), HKDF tách khóa con Fernet / HMAC, `SoulCipher.digest()` = HMAC-SHA256 64 hex theo miền, chuẩn hóa NFC + bỏ dấu cho tên. |
| `vault.py` | Khóa chủ ngẫu nhiên 32 byte được **bọc** bằng passphrase Chủ nhân (`keys.json`), và sau này bằng mật ước gia đình. Ghi nguyên tử + `.bak`. |
| `guard.py` | Sai 5 lần liên tiếp → khóa 15 phút, mỗi lần khóa tiếp theo nhân đôi; tách theo kênh (`owner`, `kin`). |
| `logging_setup.py` | `configure_logging()` chỉ gọi từ ứng dụng; logger theo module `evolving_soul.*`, ngữ cảnh dạng `key=value`. |

**Vì sao bọc khóa chủ (key wrapping)?**
- Không còn khóa mặc định viết cứng trong mã nguồn.
- Người thừa kế mở két bằng mật ước gia đình mà **không cần** biết passphrase của Chủ nhân.
- Đổi passphrase chỉ cần bọc lại khóa, không phải mã hóa lại toàn bộ hồ sơ.

**Mô hình đe dọa (giới hạn đã biết)**: ứng dụng chạy cục bộ, không có máy chủ tin cậy, nên mốc 730 ngày được thực thi bằng logic ứng dụng chứ không phải bằng mật mã. Người có cả file két sắt lẫn mật ước gia đình về lý thuyết có thể giải mã offline. Scrypt khiến việc dò mật ước tốn kém.

**Kiểm thử**: `tests/test_crypto.py`, `tests/test_vault.py` — 16 test (passphrase sai, khôi phục từ `.bak`, không có plaintext trên đĩa, bọc khóa di sản, khóa tăng dần).

---

## Giai đoạn 2 — Thuật toán nhận diện Chủ nhân V3

**Vấn đề của V2**: mọi đặc trưng là giá trị băm 4 chữ số → EMA trung bình hai giá trị băm ngẫu nhiên là vô nghĩa; cosine giữa các vector dương luôn cao; tách tên người thân theo từ đơn khiến "Bố", "Mẹ", "Thị", "Văn" cũng được tính là khớp.

**Thiết kế V3** (`features.py`, `scoring.py`, `engine.py`)
- **Bí mật so khớp chính xác** → HMAC-SHA256: ngày sinh, tên đầy đủ người thân (bỏ dấu + bỏ từ quan hệ ở đầu), OAuth, tiền tố 3 ký tự & cấu trúc lớp ký tự của mật khẩu (`HungAI@1985#Secret` → `ULUSDSUL`), thiết bị.
- **Đặc trưng hành vi liên tục** ∈ [0,1]: độ dài từ, độ dài câu, mật độ dấu câu, độ dài & độ đa dạng mật khẩu → EMA $S_t = 0.85·S_{t-1} + 0.15·X_t$ chỉ áp lên các chiều này.
- Vector vẫn **14 chiều / 5 trụ cột** đúng CLAUDE.md §4.
- **Cổng cứng**: phải khớp ngày sinh hoặc ≥ 50% người thân.
- Tiến hóa còn ghi nhớ thiết bị mới (≤5), thói quen mật khẩu mới (≤5), người thân mới (≤30), 60 từ khóa dùng nhiều nhất (thay cho cắt `set` ngẫu nhiên).
- **Phiên Chủ nhân** do engine giữ (hết hạn sau 15 phút), không còn là cờ do bên gọi truyền vào.
- Sai 5 lần liên tiếp → khóa tạm (cả xác minh lẫn mở két).

**Hiệu chỉnh** (`tools/calibrate_weights.py`, `tests/synthetic.py`): 300 Chủ nhân giả lập × (3 phiên Chủ nhân già đi, 3 người lạ, 2 người nhà biết ngày sinh + tên người thân + dùng chung máy). Chọn trọng số trên tập train, đo trên tập test độc lập:

| Trọng số | OAuth 0.15 · Gia đình 0.25 · Văn phong 0.35 · Mật khẩu 0.20 · Thiết bị 0.05 |
|---|---|
| Ngưỡng | **0.62** (V2: 0.72 trên thang cosine — thang điểm V3 khác nên hiệu chỉnh lại) |
| FRR | ≈ 4.7% |
| FAR người lạ | 0% |
| FAR người nhà | ≈ 3.8% |

Người nhà là đối thủ mạnh nhất; vì vậy ở V3 xác minh hành vi là **lớp thứ hai sau passphrase**: không mở được két thì không có gì để xác minh. Không nên đặt `EVOLVING_SOUL_PASSPHRASE` trên máy dùng chung.

**Kiểm thử**: `tests/test_features.py` (12, gồm test hiệu chỉnh FAR/FRR với seed riêng), `tests/test_engine_owner.py` (9). Tổng 37 test V3.

---

## Giai đoạn 3 — Sinh trắc học YuNet + SFace

**Vấn đề của V2**: "sinh trắc học" chỉ là histogram xám 64 bin — mọi ảnh có độ sáng tương tự đều khớp; khi chưa đăng ký ảnh thì `bio_score = knowledge_score`.

**V3** (`evolving_soul/biometrics.py`)
- `cv2.FaceDetectorYN` (YuNet, 232 KB) phát hiện & căn chỉnh khuôn mặt; `cv2.FaceRecognizerSF` (SFace, 38.7 MB) sinh embedding 128 chiều. Có sẵn trong `opencv-python` ≥ 4.8 — không cần thêm thư viện.
- Model tải từ opencv_zoo vào `models/` (đã gitignore) ở lần dùng đầu; **SHA-256 được ghim cố định** trong mã, file sai checksum bị từ chối. Môi trường offline: chép 2 file `.onnx` vào một thư mục và đặt `EVOLVING_SOUL_MODEL_DIR`.
- Đăng ký: 1–3 ảnh, mỗi ảnh phải có **đúng một** khuôn mặt; lưu trung bình embedding đã chuẩn hóa — không lưu ảnh.
- So khớp: cosine SFace, ngưỡng 0.363 (khuyến nghị của OpenCV). Thử nghiệm: cùng người (lật + đổi sáng) ≈ 0.90, khác người ≈ 0.13.
- Fallback histogram (khi không có model) được gắn `assurance="low"`; Giai đoạn 4 sẽ bắt buộc điểm tri thức cao hơn cho mức này.

**Ghi chú ghim checksum**: SHA-256 được lấy từ bản tải opencv_zoo ngày 2026-10-15 (trust-on-first-use). Nếu opencv_zoo cập nhật file, cần cập nhật hằng số `DETECTOR` / `RECOGNIZER`.

**Kiểm thử**: `tests/test_biometrics.py` — 4 test luôn chạy (checksum, fallback, ảnh hỏng, mẫu SFace khi thiếu model) + 3 test `@pytest.mark.models` dùng ảnh mẫu `lena.jpg` / `messi5.jpg` của OpenCV (tải về cache, ghim SHA-256, tự bỏ qua khi offline).

---

## Giai đoạn 4 — Dead Man's Switch & nhật ký kiểm toán

**Niêm phong (Chủ nhân, `engine.seal_legacy`)** — yêu cầu Chủ nhân đã xác minh trong 15 phút gần nhất.
- Mật ước gia đình tối thiểu 10 ký tự; khóa chủ của két được bọc thêm bằng khóa Scrypt suy từ mật ước → người thừa kế mở két **không cần** passphrase của Chủ nhân.
- Tên / email người thừa kế lưu dạng HMAC; danh mục tài sản + lời nhắn được mã hóa thêm một lớp bằng khóa suy từ mật ước, nên người chỉ có passphrase của Chủ nhân cũng không đọc được.
- Sinh trắc: 1–3 ảnh người thừa kế → mẫu SFace (hoặc histogram nếu không có model).
- Khởi tạo lại hồ sơ Chủ nhân sẽ hủy lớp bọc mật ước (di sản cũ không còn mở được).

**Đồng hồ 730 ngày (`legacy.status`)**
- Mốc tính từ lần cuối Chủ nhân **xác minh hành vi thành công** (heartbeat).
- ≥ 90% ngưỡng (≈ 657 ngày): trạng thái `warning` để nhắc Chủ nhân.
- Chủ nhân quay lại và xác minh thành công → đặt lại đồng hồ, **thu hồi** di sản nếu đã bị tiếp quản.
- *Khác với kế hoạch*: mở két bằng passphrase **không** được tính là heartbeat — nếu passphrase đặt trong biến môi trường, mỗi lần khởi động ứng dụng sẽ tự đặt lại đồng hồ và Dead Man's Switch không bao giờ kích hoạt.

**Cổng tiếp quản (`engine.claim_legacy`)** — quy tắc xác thực kép:

| Lớp sinh trắc đã niêm phong | Điều kiện |
|---|---|
| SFace (bảo đảm cao) | tri thức ≥ 70% **và** cosine ≥ 0.363 |
| Histogram (bảo đảm thấp) | tri thức ≥ 85% **và** histogram khớp |
| Không có | tri thức ≥ 85% |

Điểm tri thức = 0.20 tên + 0.20 email + 0.15 ngày sinh Chủ nhân + 0.20 người thân + 0.25 mật ước. Chỉ bàn giao tài sản khi xác thực đạt **và** đã qua ngưỡng vắng mặt. Sai 5 lần → khóa tạm kênh `kin`.

**Nhật ký kiểm toán (`audit.py`)** — `vault/audit.jsonl`, mỗi dòng chứa hash của dòng trước (chuỗi băm). Hồ sơ đã mã hóa lưu "neo" là hash mới nhất, nên sửa một dòng hay xóa cả file đều bị phát hiện (`engine.audit_integrity()`). Nhật ký không chứa tên, email, ngày sinh hay mật ước.

**Kiểm thử**: `tests/test_legacy.py` — 22 test (niêm phong, trước/sau 730 ngày, thu hồi khi Chủ nhân quay lại, cảnh báo 90%, khóa tạm, bảng quy tắc xác thực kép, SFace người thật vs người khác, sửa/xóa nhật ký). Tổng 66 test V3.
