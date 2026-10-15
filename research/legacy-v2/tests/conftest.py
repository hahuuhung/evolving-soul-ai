"""
Fixture dùng chung cho bộ kiểm thử V3 — mỗi test có két sắt riêng trong tmp_path.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import pytest

from evolving_soul.config import Settings

# Scrypt n thấp để test chạy nhanh; môi trường thật dùng 2^15
FAST_KDF_N = 2 ** 10
PASSPHRASE = "Chu-nhan-8X-passphrase"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(vault_dir=tmp_path / "vault", model_dir=tmp_path / "models", kdf_n=FAST_KDF_N)


@pytest.fixture
def demo_settings(settings) -> Settings:
    return settings.with_overrides(demo_mode=True)
