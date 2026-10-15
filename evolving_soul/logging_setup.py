"""
Cấu hình Logging có cấu trúc — chỉ gọi từ ứng dụng / CLI, không gọi trong thư viện.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Bật logging dạng `thời gian [mức] [module] sự_kiện key=value` cho toàn bộ package."""
    root = logging.getLogger("evolving_soul")
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
    root.addHandler(handler)
    root.setLevel(level)


def kv(**fields) -> str:
    """Định dạng ngữ cảnh log dạng key=value (không bao giờ truyền dữ liệu nhạy cảm vào đây)."""
    return " ".join(f"{k}={v}" for k, v in fields.items())
