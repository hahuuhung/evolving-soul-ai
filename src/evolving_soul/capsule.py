"""Read and write the portable `.soul` Capsule Format 1.0."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
import zipfile
from collections.abc import Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .crypto import (
    b64,
    canonical_json,
    decrypt,
    derive_key,
    encrypt,
    passphrase_unwrap,
    passphrase_wrap,
    public_key_bytes,
    random_key,
    unb64,
    verify,
)
from .errors import CapsuleIntegrityError, UnsupportedLegacyFormat
from .types import CapsuleHeader, CapsuleManifest, Compartment

MAGIC = "EVOLVING-SOUL-CAPSULE"
FORMAT_VERSION = "1.0"
HEADER_ENTRY = "header.json"
MANIFEST_ENTRY = "manifest.enc"
MAX_ENTRIES = 1_024
MAX_ENTRY_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _signature_payload(header: dict[str, Any]) -> bytes:
    unsigned = dict(header)
    unsigned["signature"] = ""
    return canonical_json(unsigned)


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and "\\" not in name
        and not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _validate_archive(archive: zipfile.ZipFile) -> None:
    infos = archive.infolist()
    if len(infos) > MAX_ENTRIES:
        raise CapsuleIntegrityError("Capsule contains too many entries")
    total = 0
    seen: set[str] = set()
    for info in infos:
        if not _safe_name(info.filename) or info.filename in seen or info.is_dir():
            raise CapsuleIntegrityError(f"Unsafe or duplicate capsule entry: {info.filename!r}")
        seen.add(info.filename)
        if info.file_size > MAX_ENTRY_BYTES:
            raise CapsuleIntegrityError("Capsule entry exceeds the size limit")
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise CapsuleIntegrityError("Capsule exceeds the total size limit")
        if info.compress_size and info.file_size / info.compress_size > 100:
            raise CapsuleIntegrityError("Suspicious capsule compression ratio")


def _header_from_dict(value: dict[str, Any]) -> CapsuleHeader:
    try:
        header = CapsuleHeader(**value)
    except (TypeError, KeyError) as exc:
        raise CapsuleIntegrityError("Invalid capsule header schema") from exc
    if header.magic != MAGIC:
        raise CapsuleIntegrityError("Invalid capsule magic")
    if header.format_version != FORMAT_VERSION:
        raise CapsuleIntegrityError(f"Unsupported capsule format {header.format_version!r}")
    return header


class SoulCapsule:
    """Stateless capsule serializer used by :class:`SoulVault`."""

    @staticmethod
    def export(
        destination: str | Path,
        *,
        capsule_id: str,
        root_key: bytes,
        signing_key: Ed25519PrivateKey,
        compartments: Iterable[Compartment],
        passphrase: str,
        sequence: int = 1,
        recovery_destination: str | Path | None = None,
        recovery_compartment_ids: set[str] | None = None,
        recovery_key: bytes | None = None,
        policy_hash: str | None = None,
    ) -> Path:
        destination = Path(destination)
        if destination.suffix != ".soul":
            destination = destination.with_suffix(".soul")
        capsule_aad = f"{MAGIC}:{capsule_id}:{FORMAT_VERSION}".encode()
        entry_blobs: dict[str, bytes] = {}
        descriptors: list[dict[str, Any]] = []
        recovery_descriptors: list[dict[str, Any]] = []
        wrap_key = derive_key(root_key, b"soul-capsule/compartment-wrap/v1")

        for compartment in compartments:
            cid = str(uuid.UUID(compartment.compartment_id))
            entry = f"compartments/{cid}.enc"
            cek = random_key()
            data_nonce, ciphertext = encrypt(
                cek,
                canonical_json(asdict(compartment)),
                f"{capsule_id}:{entry}".encode(),
            )
            cek_nonce, wrapped_cek = encrypt(wrap_key, cek, f"{capsule_id}:{cid}:cek".encode())
            blob = data_nonce + ciphertext
            entry_blobs[entry] = blob
            descriptors.append(
                {
                    "compartment_id": cid,
                    "kind": compartment.kind,
                    "entry": entry,
                    "sha256": _sha256(blob),
                    "wrapped_cek_nonce": b64(cek_nonce),
                    "wrapped_cek": b64(wrapped_cek),
                }
            )
            if recovery_compartment_ids and cid in recovery_compartment_ids:
                recovery_descriptors.append(
                    {
                        "compartment_id": cid,
                        "entry": entry,
                        "sha256": _sha256(blob),
                        "cek": b64(cek),
                    }
                )

        created_at = datetime.now(UTC).isoformat()
        manifest = CapsuleManifest(
            capsule_id=capsule_id,
            format_version=FORMAT_VERSION,
            created_at=created_at,
            compartments=descriptors,
            sequence=sequence,
        )
        manifest_key = derive_key(root_key, b"soul-capsule/manifest/v1")
        manifest_nonce, manifest_ciphertext = encrypt(
            manifest_key, canonical_json(asdict(manifest)), capsule_aad
        )
        root_wrap = passphrase_wrap(root_key, passphrase, capsule_aad)
        header = CapsuleHeader(
            magic=MAGIC,
            format_version=FORMAT_VERSION,
            capsule_id=capsule_id,
            created_at=created_at,
            crypto_suite="AES-256-GCM+HKDF-SHA256+Ed25519",
            signing_public_key=b64(public_key_bytes(signing_key)),
            manifest_entry=MANIFEST_ENTRY,
            manifest_nonce=b64(manifest_nonce),
            manifest_sha256=_sha256(manifest_ciphertext),
            signature="",
            key_wrap=root_wrap,
        )
        header_dict = asdict(header)
        header_dict["signature"] = b64(signing_key.sign(_signature_payload(header_dict)))

        if recovery_destination is not None and (
            not recovery_key or not policy_hash or not recovery_descriptors
        ):
            raise ValueError(
                "Selective recovery requires a key, policy hash, and selected compartment"
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        os.close(handle)
        try:
            with zipfile.ZipFile(
                temporary_name, "w", compression=zipfile.ZIP_STORED, allowZip64=True
            ) as archive:
                archive.writestr(HEADER_ENTRY, canonical_json(header_dict))
                archive.writestr(MANIFEST_ENTRY, manifest_ciphertext)
                for entry, blob in sorted(entry_blobs.items()):
                    archive.writestr(entry, blob)
            os.replace(temporary_name, destination)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
        if recovery_destination is not None:
            if recovery_key is None or policy_hash is None:
                raise ValueError("Recovery configuration became incomplete")
            from .recovery import write_recovery_bundle

            write_recovery_bundle(
                recovery_destination,
                capsule_id=capsule_id,
                policy_hash=policy_hash,
                release_key=recovery_key,
                signing_key=signing_key,
                selected=recovery_descriptors,
            )
        return destination

    @staticmethod
    def verify(source: str | Path, passphrase: str | None = None) -> CapsuleHeader:
        header, _manifest, _compartments, _root = SoulCapsule._read(source, passphrase, False)
        return header

    @staticmethod
    def open(
        source: str | Path, passphrase: str, *, minimum_sequence: int | None = None
    ) -> tuple[CapsuleHeader, CapsuleManifest, list[Compartment], bytes]:
        header, manifest, compartments, root_key = SoulCapsule._read(source, passphrase, True)
        if manifest is None or root_key is None:
            raise CapsuleIntegrityError("Capsule payload was not decrypted")
        if minimum_sequence is not None and manifest.sequence < minimum_sequence:
            raise CapsuleIntegrityError("Capsule export sequence is older than the trusted state")
        return header, manifest, compartments, root_key

    @staticmethod
    def _read(
        source: str | Path, passphrase: str | None, decrypt_payloads: bool
    ) -> tuple[CapsuleHeader, CapsuleManifest | None, list[Compartment], bytes | None]:
        source = Path(source)
        if not zipfile.is_zipfile(source):
            try:
                prefix = source.read_bytes()[:4096].lower()
            except OSError as exc:
                raise CapsuleIntegrityError("Capsule cannot be read") from exc
            if (
                b"owner_profile" in prefix
                or b"evolvingownerai_v2" in prefix
                or source.suffix == ".enc"
            ):
                raise UnsupportedLegacyFormat()
            raise CapsuleIntegrityError("Not a valid Soul Capsule archive")
        try:
            with zipfile.ZipFile(source, "r") as archive:
                _validate_archive(archive)
                names = set(archive.namelist())
                if HEADER_ENTRY not in names or MANIFEST_ENTRY not in names:
                    raise CapsuleIntegrityError("Required capsule entries are missing")
                raw_header = archive.read(HEADER_ENTRY)
                if len(raw_header) > 64 * 1024:
                    raise CapsuleIntegrityError("Capsule header is too large")
                try:
                    header_dict = json.loads(raw_header)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise CapsuleIntegrityError("Capsule header is not valid JSON") from exc
                header = _header_from_dict(header_dict)
                try:
                    verify(
                        unb64(header.signing_public_key),
                        unb64(header.signature),
                        _signature_payload(header_dict),
                    )
                except (InvalidSignature, ValueError) as exc:
                    raise CapsuleIntegrityError("Capsule header signature is invalid") from exc
                manifest_blob = archive.read(header.manifest_entry)
                if _sha256(manifest_blob) != header.manifest_sha256:
                    raise CapsuleIntegrityError("Encrypted manifest hash mismatch")
                if not decrypt_payloads:
                    return header, None, [], None
                if passphrase is None:
                    raise CapsuleIntegrityError("A passphrase is required to open this capsule")
                capsule_aad = f"{MAGIC}:{header.capsule_id}:{FORMAT_VERSION}".encode()
                root_key = passphrase_unwrap(header.key_wrap, passphrase, capsule_aad)
                plaintext = decrypt(
                    derive_key(root_key, b"soul-capsule/manifest/v1"),
                    unb64(header.manifest_nonce),
                    manifest_blob,
                    capsule_aad,
                )
                manifest_value = json.loads(plaintext)
                manifest = CapsuleManifest(**manifest_value)
                if manifest.capsule_id != header.capsule_id:
                    raise CapsuleIntegrityError("Manifest belongs to a different capsule")
                expected = {HEADER_ENTRY, MANIFEST_ENTRY}
                compartments: list[Compartment] = []
                wrap_key = derive_key(root_key, b"soul-capsule/compartment-wrap/v1")
                for descriptor in manifest.compartments:
                    entry = descriptor["entry"]
                    if not _safe_name(entry) or not entry.startswith("compartments/"):
                        raise CapsuleIntegrityError("Unsafe compartment entry")
                    expected.add(entry)
                    blob = archive.read(entry)
                    if _sha256(blob) != descriptor["sha256"]:
                        raise CapsuleIntegrityError("Compartment hash mismatch")
                    cid = descriptor["compartment_id"]
                    cek = decrypt(
                        wrap_key,
                        unb64(descriptor["wrapped_cek_nonce"]),
                        unb64(descriptor["wrapped_cek"]),
                        f"{header.capsule_id}:{cid}:cek".encode(),
                    )
                    value = json.loads(
                        decrypt(cek, blob[:12], blob[12:], f"{header.capsule_id}:{entry}".encode())
                    )
                    compartments.append(Compartment(**value))
                if names != expected:
                    raise CapsuleIntegrityError("Capsule contains undeclared entries")
                return header, manifest, compartments, root_key
        except UnsupportedLegacyFormat:
            raise
        except CapsuleIntegrityError:
            raise
        except (InvalidTag, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise CapsuleIntegrityError(
                "Capsule authentication or schema validation failed"
            ) from exc
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise CapsuleIntegrityError("Capsule archive is invalid") from exc
