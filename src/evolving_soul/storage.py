"""Encrypted local object store backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .crypto import canonical_json, decrypt, derive_key, encrypt
from .errors import CapsuleIntegrityError


class EncryptedStore:
    """SQLite exposes only random identifiers and authenticated ciphertext."""

    def __init__(self, path: Path, root_key: bytes) -> None:
        self._key = derive_key(root_key, b"soul-vault/sqlite-objects/v1")
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS objects "
            "(opaque_id BLOB PRIMARY KEY, ciphertext BLOB NOT NULL)"
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def put(self, opaque_id: bytes, kind: str, value: dict[str, Any]) -> None:
        aad = b"soul-object:" + opaque_id
        nonce, ciphertext = encrypt(self._key, canonical_json({"kind": kind, "value": value}), aad)
        with self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO objects(opaque_id, ciphertext) VALUES (?, ?)",
                (opaque_id, nonce + ciphertext),
            )

    def delete(self, opaque_id: bytes) -> None:
        with self._connection:
            self._connection.execute("DELETE FROM objects WHERE opaque_id = ?", (opaque_id,))

    def iter_objects(self, kind: str | None = None) -> Iterator[tuple[bytes, dict[str, Any]]]:
        rows = self._connection.execute("SELECT opaque_id, ciphertext FROM objects").fetchall()
        for opaque_id, blob in rows:
            try:
                raw = decrypt(
                    self._key,
                    blob[:12],
                    blob[12:],
                    b"soul-object:" + opaque_id,
                )
                envelope = json.loads(raw)
            except Exception as exc:
                raise CapsuleIntegrityError("Local encrypted object failed authentication") from exc
            if kind is None or envelope["kind"] == kind:
                yield opaque_id, envelope["value"]
