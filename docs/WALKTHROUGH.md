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
