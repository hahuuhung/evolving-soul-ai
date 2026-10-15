"""
Evolving Soul AI V3 — Mô hình AI Nhỏ Gọn Ghi Nhớ & Nhận Diện Chủ Nhân Phi Sinh Trắc Học & Thừa Kế Di Sản Số.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)
"""

from __future__ import annotations

from evolving_soul.config import Settings
from evolving_soul.errors import (
    EvolvingSoulError,
    LockedOutError,
    OwnerNotVerifiedError,
    ProfileExistsError,
    VaultCorruptError,
    VaultLockedError,
    VaultNotFoundError,
)

__version__ = "3.0.0"
AUTHOR_ATTRIBUTION = "Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X"

__all__ = [
    "AUTHOR_ATTRIBUTION",
    "EvolvingSoulError",
    "LockedOutError",
    "OwnerNotVerifiedError",
    "ProfileExistsError",
    "Settings",
    "VaultCorruptError",
    "VaultLockedError",
    "VaultNotFoundError",
    "__version__",
]
