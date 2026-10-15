# CLAUDE.md — Quy Chuẩn & Hướng Dẫn Phát Triển Dự Án Evolving Soul AI

## 1. Thông Tin Bản Quyền & Tác Giả
- **Dự án**: Evolving Soul AI — Mô hình AI Nhỏ Gọn Ghi Nhớ & Nhận Diện Chủ Nhân Phi Sinh Trắc Học & Thừa Kế Di Sản Số.
- **Tác giả sáng lập**: **HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X**.
- **Bản quyền**: Giấy phép Mã nguồn mở ghi nhận nguồn gốc bắt buộc (Mandatory Attribution).

---

## 2. Tiêu Chuẩn Kỹ Thuật & Đa Nền Tảng (Cross-Platform Standards)
- **Đường dẫn**: Tuyệt đối **KHÔNG** dùng đường dẫn tuyệt đối dạng `C:\...`. Bắt buộc sử dụng `os.path.join(...)` hoặc thư viện `pathlib.Path`.
- **Ngôn ngữ & Môi trường**: Python 3.9+, hỗ trợ Windows, Linux, macOS.
- **Bảo mật Zero-Knowledge**: Không lưu mật khẩu thô hoặc tên người thân dạng plaintext; bắt buộc băm SHA-256 một chiều và mã hóa đối xứng Fernet trong thư mục `vault/`.
- **Thư mục bảo mật**: `vault/` và các file `*.enc` luôn nằm trong `.gitignore`.

---

## 3. Tiêu Chuẩn Giao Diện (UI/UX Standards)
- **White Theme chủ đạo**: Giao diện sáng, hiện đại, chuyên nghiệp, tối giản và thanh lịch:
  - Màu nền: `#FFFFFF`, `#F8FAFC`.
  - Màu viền & phân cách: `#E2E8F0`, `#CBD5E1`.
  - Màu thương hiệu chính: Xanh công nghệ `#2563EB`, Xanh tin cậy `#059669`.
  - Màu cảnh báo / Di sản: Vàng kim hổ phách `#D97706`.
  - Chữ / Typography: `#0F172A` (tiêu đề), `#334155` (nội dung), `#64748B` (chú thích).
- **Trực quan hóa**: Sử dụng Radar Chart (Plotly) hiển thị 5 trụ cột đặc trưng theo thời gian thực.
- **Tạo Mockup**: Bắt buộc phác thảo trực quan trước khi hiện thực hóa màn hình mới.

---

## 4. Kiến Trúc Lõi & Dữ Liệu
- **Vector đặc trưng**: 14 chiều tổng hợp từ 5 trụ cột:
  1. Liên kết OAuth Trust (Google, Apple, Facebook).
  2. Đồ thị Tri thức Gia đình (Family Lore & Ngày sinh).
  3. Cá tính & Phong cách ngôn ngữ (Stylometry).
  4. Thói quen cấu trúc mật khẩu (Behavioral Biometrics).
  5. Dấu vết thiết bị (Device Footprint).
- **Công thức Tiến hóa**: $S_t = (1-\alpha) \cdot S_{t-1} + \alpha \cdot X_t$ với $\alpha = 0.15$.
- **Cơ chế Thừa kế Di sản Số (Dead Man's Switch)**:
  - $< 730$ ngày: Chủ nhân online, bảo vệ độc quyền; người thân ở chế độ bạn đồng hành.
  - $\ge 730$ ngày (2 năm không online): Kích hoạt lớp xác thực sinh trắc học khẩn cấp (Delayed Biometric Fallback) kết hợp Mật ước gia đình để mở khóa bản quyền, tác phẩm và tài sản số.

---

## 5. Quy Trình Kiểm Thử & Quản Lý Mã Nguồn
- **Logging**: Logging có cấu trúc, rõ ràng, chi tiết ngữ cảnh.
- **Unit & E2E Testing**: Tối thiểu 6 kịch bản kiểm thử toàn trình (với `pytest`).
- **Git Commit**: Commit sau mỗi task hoàn thành, cập nhật walkthrough rõ ràng, review 2 lần trước khi bàn giao.
