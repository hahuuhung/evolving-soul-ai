"""
Các ngoại lệ có kiểu của Evolving Soul AI — thay cho việc trả về None im lặng ở V2.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations


class EvolvingSoulError(Exception):
    """Lớp gốc cho mọi lỗi của Evolving Soul AI."""


class VaultNotFoundError(EvolvingSoulError):
    """Két sắt chưa được khởi tạo."""


class VaultLockedError(EvolvingSoulError):
    """Sai passphrase / mật ước, hoặc két sắt chưa được mở khóa."""


class VaultCorruptError(EvolvingSoulError):
    """Dữ liệu két sắt hỏng hoặc sai định dạng."""


class ProfileExistsError(EvolvingSoulError, PermissionError):
    """Đã có hồ sơ Chủ nhân — không được ghi đè khi chưa xác minh."""


class OwnerNotVerifiedError(EvolvingSoulError, PermissionError):
    """Thao tác nhạy cảm yêu cầu Chủ nhân đã xác minh trong phiên."""


class LockedOutError(EvolvingSoulError, PermissionError):
    """Quá nhiều lần thử thất bại — tạm khóa."""

    def __init__(self, message: str, retry_after_seconds: float):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
