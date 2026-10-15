"""Selective recovery bundles containing keys, never memory content."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .crypto import b64, canonical_json, decrypt, derive_key, encrypt, unb64, verify
from .errors import CapsuleIntegrityError
from .types import Compartment

RECOVERY_MAGIC = "EVOLVING-SOUL-RECOVERY"


def write_recovery_bundle(
    destination: str | Path,
    *,
    capsule_id: str,
    policy_hash: str,
    release_key: bytes,
    signing_key: Ed25519PrivateKey,
    selected: list[dict[str, Any]],
) -> Path:
    """Write descriptors and CEKs encrypted under the SLIP-39 release secret."""
    destination = Path(destination)
    payload = canonical_json({"selected_compartments": selected})
    nonce, ciphertext = encrypt(
        derive_key(release_key, b"soul-recovery/bundle/v1"),
        payload,
        f"{capsule_id}:{policy_hash}".encode(),
    )
    envelope = {
        "magic": RECOVERY_MAGIC,
        "version": "1.0",
        "capsule_id": capsule_id,
        "policy_hash": policy_hash,
        "nonce": b64(nonce),
        "ciphertext": b64(ciphertext),
        "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
        "signature": "",
    }
    envelope["signature"] = b64(signing_key.sign(canonical_json(envelope)))
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(canonical_json(envelope))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return destination


def recover_compartments(
    capsule_path: str | Path,
    recovery_path: str | Path,
    release_key: bytes,
) -> list[Compartment]:
    from .capsule import SoulCapsule, _safe_name, _sha256

    header = SoulCapsule.verify(capsule_path)
    try:
        envelope = json.loads(Path(recovery_path).read_bytes())
        if envelope["magic"] != RECOVERY_MAGIC or envelope["capsule_id"] != header.capsule_id:
            raise CapsuleIntegrityError("Recovery bundle does not match this capsule")
        signature = unb64(envelope["signature"])
        unsigned = dict(envelope)
        unsigned["signature"] = ""
        verify(unb64(header.signing_public_key), signature, canonical_json(unsigned))
        ciphertext = unb64(envelope["ciphertext"])
        if hashlib.sha256(ciphertext).hexdigest() != envelope["ciphertext_sha256"]:
            raise CapsuleIntegrityError("Recovery bundle hash mismatch")
        plaintext = decrypt(
            derive_key(release_key, b"soul-recovery/bundle/v1"),
            unb64(envelope["nonce"]),
            ciphertext,
            f"{header.capsule_id}:{envelope['policy_hash']}".encode(),
        )
        selected = json.loads(plaintext)["selected_compartments"]
        results: list[Compartment] = []
        with zipfile.ZipFile(capsule_path) as archive:
            for item in selected:
                entry = item["entry"]
                if not _safe_name(entry) or not entry.startswith("compartments/"):
                    raise CapsuleIntegrityError("Unsafe recovery compartment entry")
                blob = archive.read(entry)
                if _sha256(blob) != item["sha256"]:
                    raise CapsuleIntegrityError("Recovery compartment hash mismatch")
                raw = decrypt(
                    unb64(item["cek"]),
                    blob[:12],
                    blob[12:],
                    f"{header.capsule_id}:{entry}".encode(),
                )
                results.append(Compartment(**json.loads(raw)))
        return results
    except CapsuleIntegrityError:
        raise
    except (
        OSError,
        KeyError,
        ValueError,
        InvalidSignature,
        InvalidTag,
        json.JSONDecodeError,
    ) as exc:
        raise CapsuleIntegrityError("Recovery bundle authentication failed") from exc
