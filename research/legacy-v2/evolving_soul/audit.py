"""
Nhật ký kiểm toán chuỗi băm (hash-chained audit log).

Mỗi dòng của `vault/audit.jsonl`:
  {"ts": ..., "event": "...", "result": "...", ...ngữ cảnh không nhạy cảm..., "prev": <hash dòng trước>, "hash": <sha256>}
Sửa / xóa một dòng ở giữa làm đứt chuỗi. Hồ sơ đã mã hóa còn lưu "neo" (hash mới nhất lúc ghi hồ sơ)
để phát hiện việc viết lại toàn bộ file. KHÔNG bao giờ ghi tên, email, ngày sinh, mật ước vào nhật ký.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger("evolving_soul.audit")

AUDIT_FILE = "audit.jsonl"
GENESIS = "0" * 64


def _entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, vault_dir: Path | str, clock: Callable[[], float] = time.time):
        self.path = Path(vault_dir) / AUDIT_FILE
        self.clock = clock

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        entries = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    entries.append({"corrupt": line[:80]})
        return entries

    @property
    def last_hash(self) -> str:
        entries = self._read()
        return entries[-1].get("hash", GENESIS) if entries else GENESIS

    def append(self, event: str, result: str, **fields) -> dict:
        entry = {"ts": round(self.clock(), 3), "event": event, "result": result, **fields, "prev": self.last_hash}
        entry["hash"] = _entry_hash(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def tail(self, n: int = 20) -> list[dict]:
        return self._read()[-n:]

    def verify(self, anchor: str | None = None) -> dict:
        """Kiểm tra chuỗi băm; nếu có neo từ hồ sơ thì neo phải xuất hiện trong chuỗi."""
        prev = GENESIS
        hashes = set()
        for index, entry in enumerate(self._read()):
            if entry.get("prev") != prev or entry.get("hash") != _entry_hash(entry):
                logger.warning("audit_chain_broken index=%d", index)
                return {"ok": False, "broken_at": index, "entries": index}
            prev = entry["hash"]
            hashes.add(prev)
        if anchor and anchor != GENESIS and anchor not in hashes:
            logger.warning("audit_anchor_missing")
            return {"ok": False, "broken_at": None, "entries": len(hashes), "reason": "anchor_missing"}
        return {"ok": True, "broken_at": None, "entries": len(hashes)}
