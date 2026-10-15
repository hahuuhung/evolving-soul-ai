"""
Kiểm thử lớp mật mã V3.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import pytest

from evolving_soul import crypto
from evolving_soul.errors import VaultLockedError

N = 2 ** 10


def test_normalize_and_strip_diacritics():
    assert crypto.normalize_text("  Hà   Minh\tKHÔI ") == "hà minh khôi"
    assert crypto.strip_diacritics("Đặng Thị Hà Minh Khôi") == "dang thi ha minh khoi"
    assert crypto.normalize_text(None) == ""


def test_derive_key_requires_salt_and_secret():
    salt = crypto.new_salt()
    assert crypto.derive_key("bi mat", salt, N) == crypto.derive_key("bi mat", salt, N)
    assert crypto.derive_key("bi mat", salt, N) != crypto.derive_key("bi mat", crypto.new_salt(), N)
    with pytest.raises(VaultLockedError):
        crypto.derive_key("   ", salt, N)


def test_passphrase_is_case_sensitive_but_family_secret_is_loose():
    salt = crypto.new_salt()
    assert crypto.derive_key("Secret Pass", salt, N) != crypto.derive_key("secret pass", salt, N)
    assert crypto.derive_key("Kỷ niệm  Hà Nội", salt, N, loose=True) == crypto.derive_key("kỷ niệm hà nội", salt, N, loose=True)


def test_wrap_and_unwrap_master_key():
    master = crypto.new_master_key()
    salt = crypto.new_salt()
    wrapped = crypto.wrap_key(master, crypto.derive_key("dung", salt, N))
    assert crypto.unwrap_key(wrapped, crypto.derive_key("dung", salt, N)) == master
    with pytest.raises(VaultLockedError):
        crypto.unwrap_key(wrapped, crypto.derive_key("sai", salt, N))


def test_hmac_digest_is_domain_separated_and_full_length():
    cipher = crypto.SoulCipher(crypto.new_master_key())
    a = cipher.digest("1985-05-15", "dob")
    assert len(a) == 64
    assert a == cipher.digest(" 1985-05-15 ", "dob")
    assert a != cipher.digest("1985-05-15", "family")
    assert cipher.digest("", "dob") is None
    other = crypto.SoulCipher(crypto.new_master_key())
    assert a != other.digest("1985-05-15", "dob")


def test_digests_equal_rejects_none():
    assert crypto.digests_equal("ab", "ab")
    assert not crypto.digests_equal(None, None)
    assert not crypto.digests_equal("ab", "ac")


def test_encrypt_with_secret_roundtrip():
    salt = crypto.new_salt()
    token = crypto.encrypt_with_secret(b"MASTER-KEY", "Mat uoc", salt, N)
    assert crypto.decrypt_with_secret(token, "  MAT   UOC ", salt, N) == b"MASTER-KEY"
    with pytest.raises(VaultLockedError):
        crypto.decrypt_with_secret(token, "sai", salt, N)
