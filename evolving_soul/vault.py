"""
Két sắt dữ liệu V3 (Vault).

Bố cục thư mục `vault/`:
  keys.json       — khóa chủ đã bọc bằng passphrase của Chủ nhân (và bằng mật ước gia đình nếu đã niêm phong di sản).
                    Không chứa bí mật dạng rõ; chỉ có salt + khóa đã bọc.
  soul_v3.enc     — hồ sơ Chủ nhân đã mã hóa Fernet (khóa con HKDF từ khóa chủ).
  soul_v3.enc.bak — bản sao lần ghi trước, dùng khi file chính hỏng.

Mọi thao tác ghi đều nguyên tử (ghi file tạm rồi os.replace).

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from evolving_soul import crypto
from evolving_soul.errors import VaultCorruptError, VaultLockedError, VaultNotFoundError
from evolving_soul.logging_setup import kv

logger = logging.getLogger("evolving_soul.vault")

SCHEMA_VERSION = 3
KEYS_FILE = "keys.json"
PROFILE_FILE = "soul_v3.enc"


def atomic_write_bytes(path: Path, data: bytes, keep_backup: bool = False) -> None:
    """Ghi file nguyên tử: ghi vào file tạm cùng thư mục rồi thay thế."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if keep_backup and path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


@dataclass
class VaultSession:
    """Phiên két sắt đã mở khóa: giữ khóa chủ trong bộ nhớ, không bao giờ ghi ra đĩa dạng rõ."""

    master_key: bytes
    cipher: crypto.SoulCipher
    unlocked_by: str  # "owner" | "legacy"

    def __repr__(self) -> str:  # tránh lộ khóa khi log / debug
        return f"VaultSession(unlocked_by={self.unlocked_by!r})"


class Vault:
    """Quản lý khóa và hồ sơ đã mã hóa trong một thư mục két sắt."""

    def __init__(self, vault_dir: Path | str, kdf_n: int = 2 ** 15):
        self.dir = Path(vault_dir)
        self.kdf_n = kdf_n
        self.keys_path = self.dir / KEYS_FILE
        self.profile_path = self.dir / PROFILE_FILE
        self.backup_path = self.dir / (PROFILE_FILE + ".bak")

    # ------------------------------------------------------------------
    # Trạng thái
    # ------------------------------------------------------------------

    def is_initialized(self) -> bool:
        return self.keys_path.exists()

    def has_profile(self) -> bool:
        return self.profile_path.exists()

    def has_legacy_wrap(self) -> bool:
        return self.is_initialized() and self._read_keys().get("legacy") is not None

    # ------------------------------------------------------------------
    # Khóa
    # ------------------------------------------------------------------

    def _read_keys(self) -> dict:
        if not self.keys_path.exists():
            raise VaultNotFoundError(f"Chưa khởi tạo két sắt tại {self.dir}")
        try:
            keys = json.loads(self.keys_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise VaultCorruptError("keys.json hỏng hoặc không đọc được.") from exc
        if keys.get("schema_version") != SCHEMA_VERSION or "owner" not in keys:
            raise VaultCorruptError("keys.json sai định dạng V3.")
        return keys

    def _write_keys(self, keys: dict) -> None:
        atomic_write_bytes(self.keys_path, json.dumps(keys, indent=2).encode("utf-8"))

    def _make_wrap(self, master_key: bytes, secret: str, loose: bool) -> dict:
        salt = crypto.new_salt()
        wrapping_key = crypto.derive_key(secret, salt, self.kdf_n, loose=loose)
        return {"salt": _b64e(salt), "n": self.kdf_n, "wrapped": crypto.wrap_key(master_key, wrapping_key)}

    @staticmethod
    def _open_wrap(entry: dict, secret: str, loose: bool) -> bytes:
        wrapping_key = crypto.derive_key(secret, _b64d(entry["salt"]), int(entry["n"]), loose=loose)
        return crypto.unwrap_key(entry["wrapped"], wrapping_key)

    def initialize(self, passphrase: str) -> VaultSession:
        """Tạo két sắt mới với khóa chủ ngẫu nhiên, bọc bằng passphrase của Chủ nhân."""
        if self.is_initialized():
            raise VaultCorruptError("Két sắt đã tồn tại — không khởi tạo lại.")
        if len(passphrase or "") < 8:
            raise VaultLockedError("Passphrase phải dài tối thiểu 8 ký tự.")
        self.dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.dir, 0o700)
        except OSError:
            pass
        master_key = crypto.new_master_key()
        keys = {
            "schema_version": SCHEMA_VERSION,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "owner": self._make_wrap(master_key, passphrase, loose=False),
            "legacy": None,
        }
        self._write_keys(keys)
        logger.info("vault_initialized %s", kv(dir=self.dir))
        return VaultSession(master_key, crypto.SoulCipher(master_key), "owner")

    def unlock(self, passphrase: str) -> VaultSession:
        """Mở khóa bằng passphrase của Chủ nhân."""
        keys = self._read_keys()
        master_key = self._open_wrap(keys["owner"], passphrase, loose=False)
        logger.info("vault_unlocked %s", kv(by="owner"))
        return VaultSession(master_key, crypto.SoulCipher(master_key), "owner")

    def unlock_with_legacy_secret(self, family_secret: str) -> VaultSession:
        """Mở khóa bằng mật ước gia đình (chỉ dùng cho cổng tiếp quản di sản)."""
        keys = self._read_keys()
        if not keys.get("legacy"):
            raise VaultLockedError("Chủ nhân chưa niêm phong Di sản Số.")
        master_key = self._open_wrap(keys["legacy"], family_secret, loose=True)
        logger.info("vault_unlocked %s", kv(by="legacy"))
        return VaultSession(master_key, crypto.SoulCipher(master_key), "legacy")

    def set_legacy_secret(self, session: VaultSession, family_secret: str) -> None:
        """Bọc thêm khóa chủ bằng mật ước gia đình (ghi đè lần niêm phong trước)."""
        self._require_owner(session)
        keys = self._read_keys()
        keys["legacy"] = self._make_wrap(session.master_key, family_secret, loose=True)
        self._write_keys(keys)
        logger.info("legacy_wrap_set")

    def clear_legacy_secret(self, session: VaultSession) -> None:
        self._require_owner(session)
        keys = self._read_keys()
        keys["legacy"] = None
        self._write_keys(keys)
        logger.info("legacy_wrap_cleared")

    def change_passphrase(self, session: VaultSession, new_passphrase: str) -> None:
        self._require_owner(session)
        if len(new_passphrase or "") < 8:
            raise VaultLockedError("Passphrase phải dài tối thiểu 8 ký tự.")
        keys = self._read_keys()
        keys["owner"] = self._make_wrap(session.master_key, new_passphrase, loose=False)
        self._write_keys(keys)
        logger.info("passphrase_changed")

    @staticmethod
    def _require_owner(session: VaultSession) -> None:
        if session.unlocked_by != "owner":
            raise VaultLockedError("Thao tác này chỉ dành cho Chủ nhân.")

    # ------------------------------------------------------------------
    # Hồ sơ
    # ------------------------------------------------------------------

    def save_profile(self, session: VaultSession, profile: dict) -> None:
        profile = dict(profile)
        profile["schema_version"] = SCHEMA_VERSION
        profile["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        token = session.cipher.encrypt(json.dumps(profile, ensure_ascii=False).encode("utf-8"))
        atomic_write_bytes(self.profile_path, token, keep_backup=True)
        logger.info("profile_saved %s", kv(generation=profile.get("generation"), by=session.unlocked_by))

    def load_profile(self, session: VaultSession) -> dict | None:
        """Đọc hồ sơ; nếu file chính hỏng thì thử bản .bak."""
        if not self.profile_path.exists():
            return None
        try:
            return self._decode(session, self.profile_path)
        except VaultCorruptError:
            if not self.backup_path.exists():
                raise
            logger.warning("profile_corrupt_using_backup %s", kv(path=self.profile_path.name))
            return self._decode(session, self.backup_path)

    @staticmethod
    def _decode(session: VaultSession, path: Path) -> dict:
        try:
            raw = session.cipher.decrypt(path.read_bytes())
            profile = json.loads(raw.decode("utf-8"))
        except (VaultLockedError, ValueError, OSError) as exc:
            # Khóa đã được kiểm chứng khi mở bọc -> giải mã thất bại nghĩa là dữ liệu hỏng
            raise VaultCorruptError(f"Không đọc được {path.name}.") from exc
        if profile.get("schema_version") != SCHEMA_VERSION:
            raise VaultCorruptError(f"{path.name} không phải hồ sơ V3.")
        return profile

    def delete_profile(self, session: VaultSession) -> None:
        self._require_owner(session)
        for path in (self.profile_path, self.backup_path):
            if path.exists():
                path.unlink()
        logger.info("profile_deleted")
