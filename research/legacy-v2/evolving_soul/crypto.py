"""
Lớp mật mã của Evolving Soul AI V3.

- Suy khóa từ passphrase / mật ước bằng Scrypt (có salt, chống dò offline).
- Khóa chủ (master key) 32 byte ngẫu nhiên; từ đó tách khóa con bằng HKDF:
  * khóa Fernet để mã hóa hồ sơ,
  * khóa HMAC-SHA256 để băm một chiều các bí mật (ngày sinh, tên người thân, mật ước...).
- Chuẩn hóa văn bản Unicode trước khi băm để so khớp ổn định.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import unicodedata

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from evolving_soul.errors import VaultLockedError

SALT_BYTES = 16
MASTER_KEY_BYTES = 32
_WHITESPACE = re.compile(r"\s+")


# =========================================================================
# CHUẨN HÓA VĂN BẢN
# =========================================================================

def normalize_text(text: str | None) -> str:
    """NFC + chữ thường + gộp khoảng trắng. Giữ nguyên dấu tiếng Việt."""
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFC", str(text)).casefold()
    return _WHITESPACE.sub(" ", cleaned).strip()


def strip_diacritics(text: str | None) -> str:
    """Bỏ dấu tiếng Việt (kể cả đ/Đ) để so khớp tên không phụ thuộc cách gõ."""
    base = normalize_text(text).replace("đ", "d")
    decomposed = unicodedata.normalize("NFKD", base)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


# =========================================================================
# SUY KHÓA & BỌC KHÓA
# =========================================================================

def new_salt() -> bytes:
    return os.urandom(SALT_BYTES)


def new_master_key() -> bytes:
    return os.urandom(MASTER_KEY_BYTES)


def derive_key(secret: str, salt: bytes, n: int = 2 ** 15, loose: bool = False) -> bytes:
    """
    Suy khóa 32 byte bằng Scrypt (r=8, p=1).
    loose=False (passphrase): chỉ chuẩn hóa NFC + bỏ khoảng trắng hai đầu, phân biệt hoa/thường.
    loose=True (mật ước gia đình): chuẩn hóa đầy đủ để người thân gõ khác hoa/thường vẫn khớp.
    """
    material = normalize_text(secret) if loose else unicodedata.normalize("NFC", str(secret or "")).strip()
    if not material:
        raise VaultLockedError("Passphrase / mật ước không được để trống.")
    kdf = Scrypt(salt=salt, length=32, n=n, r=8, p=1)
    return kdf.derive(material.encode("utf-8"))


def _fernet(key32: bytes) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(key32))


def wrap_key(master_key: bytes, wrapping_key: bytes) -> str:
    """Bọc khóa chủ bằng khóa suy từ passphrase / mật ước."""
    return _fernet(wrapping_key).encrypt(master_key).decode("ascii")


def unwrap_key(wrapped: str, wrapping_key: bytes) -> bytes:
    """Mở bọc khóa chủ; sai khóa -> VaultLockedError."""
    try:
        return _fernet(wrapping_key).decrypt(wrapped.encode("ascii"))
    except InvalidToken as exc:
        raise VaultLockedError("Sai passphrase hoặc mật ước.") from exc


def _hkdf(master_key: bytes, info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(master_key)


# =========================================================================
# BỘ MÃ HÓA HỒ SƠ
# =========================================================================

class SoulCipher:
    """Mã hóa hồ sơ (Fernet) và băm bí mật (HMAC-SHA256) từ cùng một khóa chủ."""

    def __init__(self, master_key: bytes):
        if len(master_key) != MASTER_KEY_BYTES:
            raise ValueError("Khóa chủ phải dài 32 byte.")
        self._fernet = _fernet(_hkdf(master_key, b"evolving-soul/v3/fernet"))
        self._hmac_key = _hkdf(master_key, b"evolving-soul/v3/hmac")

    def encrypt(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        try:
            return self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise VaultLockedError("Không giải mã được hồ sơ bằng khóa hiện tại.") from exc

    def digest(self, text: str | None, domain: str) -> str | None:
        """HMAC-SHA256 một chiều theo miền (domain) — None nếu văn bản rỗng."""
        normalized = normalize_text(text)
        if not normalized:
            return None
        msg = f"{domain}\x00{normalized}".encode("utf-8")
        return hmac.new(self._hmac_key, msg, hashlib.sha256).hexdigest()


def digests_equal(a: str | None, b: str | None) -> bool:
    """So sánh digest thời gian hằng định; None không bao giờ khớp."""
    if not a or not b:
        return False
    return hmac.compare_digest(a, b)


def encrypt_with_secret(data: bytes, secret: str, salt: bytes, n: int = 2 ** 15) -> str:
    """Mã hóa một gói dữ liệu bằng khóa suy trực tiếp từ bí mật (dùng cho tài sản di sản)."""
    return _fernet(derive_key(secret, salt, n, loose=True)).encrypt(data).decode("ascii")


def decrypt_with_secret(token: str, secret: str, salt: bytes, n: int = 2 ** 15) -> bytes:
    try:
        return _fernet(derive_key(secret, salt, n, loose=True)).decrypt(token.encode("ascii"))
    except InvalidToken as exc:
        raise VaultLockedError("Sai mật ước gia đình.") from exc
