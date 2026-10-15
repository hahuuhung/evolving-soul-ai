"""
Chống dò (brute-force guard): đếm số lần thất bại liên tiếp theo từng kênh và tạm khóa tăng dần.

Trạng thái lưu ở `vault/guard.json` (không chứa dữ liệu nhạy cảm) để vẫn hoạt động
khi két sắt chưa mở khóa (ví dụ cổng tiếp quản của người thân).

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Callable

from evolving_soul.errors import LockedOutError
from evolving_soul.logging_setup import kv
from evolving_soul.vault import atomic_write_bytes

logger = logging.getLogger("evolving_soul.guard")

GUARD_FILE = "guard.json"


class AttemptGuard:
    """Sau `max_failures` lần sai liên tiếp: khóa `base_seconds`, mỗi lần khóa tiếp theo nhân đôi."""

    def __init__(
        self,
        vault_dir: Path | str,
        max_failures: int = 5,
        base_seconds: int = 900,
        clock: Callable[[], float] = time.time,
    ):
        self.path = Path(vault_dir) / GUARD_FILE
        self.max_failures = max_failures
        self.base_seconds = base_seconds
        self.clock = clock

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save(self, state: dict) -> None:
        atomic_write_bytes(self.path, json.dumps(state, indent=2).encode("utf-8"))

    def check(self, channel: str) -> None:
        """Ném LockedOutError nếu kênh đang bị khóa."""
        entry = self._load().get(channel, {})
        remaining = float(entry.get("locked_until", 0)) - self.clock()
        if remaining > 0:
            raise LockedOutError(
                f"Quá nhiều lần thử sai. Vui lòng thử lại sau {int(remaining // 60) + 1} phút.",
                retry_after_seconds=remaining,
            )

    def record_failure(self, channel: str) -> None:
        state = self._load()
        entry = state.setdefault(channel, {"failures": 0, "lockouts": 0, "locked_until": 0})
        entry["failures"] += 1
        if entry["failures"] >= self.max_failures:
            duration = self.base_seconds * (2 ** entry["lockouts"])
            entry["locked_until"] = self.clock() + duration
            entry["lockouts"] += 1
            entry["failures"] = 0
            logger.warning("channel_locked %s", kv(channel=channel, seconds=duration, lockouts=entry["lockouts"]))
        self._save(state)

    def record_success(self, channel: str) -> None:
        state = self._load()
        if channel in state:
            state[channel] = {"failures": 0, "lockouts": 0, "locked_until": 0}
            self._save(state)

    def failures(self, channel: str) -> int:
        return int(self._load().get(channel, {}).get("failures", 0))
