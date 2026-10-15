"""Small, auditable cryptographic building blocks for the capsule format."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

ARGON2_MEMORY_KIB = 64 * 1024
ARGON2_ITERATIONS = 3
ARGON2_LANES = 1


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def random_key() -> bytes:
    return os.urandom(32)


def derive_key(root_key: bytes, domain: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=domain).derive(root_key)


def encrypt(key: bytes, plaintext: bytes, aad: bytes) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    return nonce, AESGCM(key).encrypt(nonce, plaintext, aad)


def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    return AESGCM(key).decrypt(nonce, ciphertext, aad)


def passphrase_wrap(secret: bytes, passphrase: str, aad: bytes) -> dict[str, Any]:
    if not passphrase:
        raise ValueError("A non-empty export passphrase is required")
    salt = os.urandom(16)
    key = Argon2id(
        salt=salt,
        length=32,
        iterations=ARGON2_ITERATIONS,
        lanes=ARGON2_LANES,
        memory_cost=ARGON2_MEMORY_KIB,
    ).derive(passphrase.encode())
    nonce, ciphertext = encrypt(key, secret, aad)
    return {
        "algorithm": "argon2id-aes-256-gcm",
        "salt": b64(salt),
        "memory_kib": ARGON2_MEMORY_KIB,
        "iterations": ARGON2_ITERATIONS,
        "lanes": ARGON2_LANES,
        "nonce": b64(nonce),
        "ciphertext": b64(ciphertext),
    }


def passphrase_unwrap(wrap: dict[str, Any], passphrase: str, aad: bytes) -> bytes:
    if wrap.get("algorithm") != "argon2id-aes-256-gcm":
        raise ValueError("Unsupported key wrapping algorithm")
    # Never accept parameters weaker than the protocol floor.
    memory = int(wrap["memory_kib"])
    iterations = int(wrap["iterations"])
    lanes = int(wrap["lanes"])
    if memory < ARGON2_MEMORY_KIB or iterations < ARGON2_ITERATIONS or lanes < ARGON2_LANES:
        raise ValueError("Capsule KDF parameters are below the protocol minimum")
    key = Argon2id(
        salt=unb64(wrap["salt"]),
        length=32,
        iterations=iterations,
        lanes=lanes,
        memory_cost=memory,
    ).derive(passphrase.encode())
    return decrypt(key, unb64(wrap["nonce"]), unb64(wrap["ciphertext"]), aad)


def new_signing_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def private_key_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )


def public_key_bytes(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def load_private_key(raw: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(raw)


def verify(public_key: bytes, signature: bytes, message: bytes) -> None:
    Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
