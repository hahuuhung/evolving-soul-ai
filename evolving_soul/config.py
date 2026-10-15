"""
Cấu hình tập trung của Evolving Soul AI V3.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

ENV_DEMO = "EVOLVING_SOUL_DEMO"
ENV_PASSPHRASE = "EVOLVING_SOUL_PASSPHRASE"
ENV_VAULT_DIR = "EVOLVING_SOUL_VAULT_DIR"
ENV_MODEL_DIR = "EVOLVING_SOUL_MODEL_DIR"

# Trọng số 5 trụ cột khi tính Điểm Tin Cậy (Trust Score); trụ cột vắng mặt được loại và chuẩn hóa lại
DEFAULT_PILLAR_WEIGHTS = {
    "oauth": 0.10,
    "family": 0.30,
    "style": 0.25,
    "password": 0.25,
    "device": 0.10,
}


@dataclass(frozen=True)
class Settings:
    """Tham số vận hành. Dùng `Settings.from_env()` để đọc biến môi trường."""

    vault_dir: Path = Path("vault")
    model_dir: Path = Path("models")

    # Tiến hóa thời gian: S_t = (1 - alpha) * S_{t-1} + alpha * X_t
    alpha: float = 0.15
    owner_threshold: float = 0.72
    pillar_weights: dict = field(default_factory=lambda: dict(DEFAULT_PILLAR_WEIGHTS))

    # Dead Man's Switch
    inactivity_days: int = 730
    warning_ratio: float = 0.90
    kin_knowledge_threshold: float = 0.70
    kin_knowledge_threshold_no_bio: float = 0.85
    owner_session_ttl_seconds: int = 15 * 60

    # Chống dò (brute-force)
    max_failed_attempts: int = 5
    lockout_base_seconds: int = 15 * 60

    # Giới hạn bộ nhớ tiến hóa
    max_keywords: int = 60
    max_trusted_devices: int = 5
    max_password_habits: int = 5
    max_family_members: int = 30

    # Suy khóa Scrypt (n = 2^15 cho môi trường thật; test có thể hạ xuống để chạy nhanh)
    kdf_n: int = 2 ** 15

    demo_mode: bool = False

    @classmethod
    def from_env(cls, **overrides) -> Settings:
        """Tạo Settings từ biến môi trường, cho phép ghi đè bằng tham số."""
        values = {
            "demo_mode": os.environ.get(ENV_DEMO, "") == "1",
        }
        if os.environ.get(ENV_VAULT_DIR):
            values["vault_dir"] = Path(os.environ[ENV_VAULT_DIR])
        if os.environ.get(ENV_MODEL_DIR):
            values["model_dir"] = Path(os.environ[ENV_MODEL_DIR])
        values.update(overrides)
        return cls(**values)

    def with_overrides(self, **overrides) -> Settings:
        return replace(self, **overrides)
