# Hướng Dẫn Hỗ Trợ Đa Nền Tảng (Cross-Platform Guide)
### Evolving Soul AI — Windows, macOS & Linux
**Tác giả:** Hà Hữu Hưng (1985) — Kỹ sư AI thế hệ 8X  
**Phiên bản:** v3.2.005

---

## 1. Tổng Quan Kiến Trúc Đa Nền Tảng

Evolving Soul AI được thiết kế theo triết lý **Local-First, Zero-Cloud Lock-in**, hoạt động hoàn toàn độc lập và đồng nhất trên cả 3 hệ điều hành máy trạm & máy chủ phổ biến:

| Thành Phần | Windows 10/11 | macOS (Intel / Apple Silicon) | Linux (Ubuntu, Debian, Fedora, Arch) |
| :--- | :--- | :--- | :--- |
| **OS Keyring** | Windows Credential Manager | macOS Keychain | SecretService / GNOME Keyring / KWallet |
| **Passkey / WebAuthn** | Windows Hello (PIN, Vân tay, Nhận diện khuôn mặt) | Touch ID / Apple Passkeys | FIDO2 Hardware Key, Chrome Passkeys |
| **Console Encoding** | Chế độ UTF-8 tự động (`chcp 65001`) | UTF-8 mặc định | UTF-8 mặc định |
| **Script Runner** | `soul.bat` & `run_demo.bat` | `soul.sh` & `run_demo.sh` | `soul.sh` & `run_demo.sh` |
| **Entry Point CLI** | `python -m evolving_soul.cli` | `python3 -m evolving_soul.cli` | `python3 -m evolving_soul.cli` |

---

## 2. Bộ Khởi Động Nhanh 1-Click (1-Click Launchers)

Dự án cung cấp sẵn các tập lệnh launcher không phụ thuộc vào đường dẫn tuyệt đối:

### Trên Linux & macOS:
```bash
# Cấp quyền thực thi nếu cần
chmod +x soul.sh run_demo.sh

# Chạy chẩn đoán môi trường
./soul.sh doctor

# Chạy giao diện Control Plane demo 1-click
./run_demo.sh
```

### Trên Windows (CMD hoặc PowerShell):
```cmd
:: Chạy chẩn đoán môi trường
soul.bat doctor

:: Chạy giao diện Control Plane demo 1-click
run_demo.bat
```

---

## 3. Lệnh Chẩn Đoán & Trạng Thái Mới (CLI Commands)

### 3.1. `soul doctor` — Chẩn đoán hệ thống
Kiểm tra khả năng tương thích toàn diện của hệ điều hành, Python runtime, Keyring backend và mã hóa console:

```bash
soul doctor
```
**Đầu ra JSON (dành cho automation / CI/CD / MCP):**
```bash
soul doctor --json
```

Ví dụ mẫu JSON output:
```json
{
  "os": {
    "system": "Windows",
    "release": "11",
    "machine": "AMD64",
    "platform": "Windows-11-10.0.22631-SP0"
  },
  "python": {
    "version": "3.13.2",
    "compatible": true
  },
  "terminal": {
    "encoding": "utf-8",
    "utf8_ready": true
  },
  "keyring": {
    "backend": "WinVaultKeyring",
    "ready": true
  },
  "server_dependencies": {
    "installed": true
  },
  "vault": {
    "path": "d:/AntiGravity/aiupboss/.soul-vault",
    "status": "unlocked",
    "capsule_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
}
```

### 3.2. `soul status` — Thống kê & Kiểm tra kho lưu trữ
Kiểm tra sức khỏe của `.soul-vault` cục bộ:

```bash
soul status
```
**Đầu ra JSON:**
```bash
soul status --json
```

Hiển thị:
- Capsule ID định danh linh hồn
- Số lượng ký ức đã phê duyệt (`Approved Memory`)
- Số lượng đề xuất đang chờ duyệt (`Pending Reviews`)
- Số lượng Passkey đã liên kết (`Passkeys Bound`)
- Trạng thái chính sách thừa kế (`Succession Plan`)
- Số lượng tích hợp AI đã ghép đôi (`Integrations Paired`)

---

## 4. Giao Diện Người Dùng White Theme & Nhận Diện OS

Control Plane Web UI (`http://127.0.0.1:8765`) đã được nâng cấp theo phong cách **White Theme** trang nhã, hiện đại:
- **Tự động nhận diện OS:** Phát hiện trình duyệt đang chạy trên Windows, macOS hay Linux và hiển thị huy hiệu nền tảng tương ứng.
- **Hỗ trợ Passkey WebAuthn trực quan:** Hướng dẫn sử dụng Windows Hello, Touch ID hoặc Khóa FIDO2 để đăng ký khóa chủ.
- **Duyệt đề xuất trực tiếp:** Cho phép chỉnh sửa nội dung ký ức inline trước khi phê duyệt.
- **Lệnh nhanh tương tác:** Cung cấp sẵn các mẫu câu lệnh CLI để sao chép nhanh.

---

## 5. Cấu Hình Môi Trường Headless (Linux Server / Docker / CI)

Khi chạy trên Linux Server không có màn hình hoặc D-Bus (ví dụ: container Docker hoặc SSH headless):
- Đặt biến môi trường `PYTHONIOENCODING=utf-8`.
- Nếu không có GNOME Keyring hoặc D-Bus, hệ thống tự động sử dụng fallback an toàn hoặc có thể dùng `keyrings.alt`.
- Để cài đặt đầy đủ các gói máy chủ:
  ```bash
  pip install -e ".[server]"
  ```

---

## 6. Cam Kết Chất Lượng & Bản Quyền

- **Tác giả:** Hà Hữu Hưng (1985) — Kỹ sư AI thế hệ 8X
- **Bản quyền:** Evolving Soul AI open-source project
- **Mã nguồn kiểm định:** 100% qua tất cả 29/29 tests của giao thức protocol (`pytest tests_protocol`).
