# Soul Capsule Format 1.0

Status: experimental with package `3.0.0a1`. The format version is independent of package SemVer.

## Container

A capsule is a ZIP64 archive with stored (uncompressed) entries. Readers MUST reject absolute
paths, `.`/`..`, backslashes, duplicate names, directories, undeclared entries, excessive entry
counts/sizes, and suspicious compression ratios. Current defensive limits are 1,024 entries,
64 MiB per entry, and 512 MiB total plaintext archive size.

Required entries:

```text
header.json
manifest.enc
compartments/<uuid>.enc  (zero or more)
```

## Header

`header.json` is canonical UTF-8 JSON. It contains no owner name, email, memory label, guardian
identity, or other intended PII. Fields are:

- magic `EVOLVING-SOUL-CAPSULE`
- format version `1.0`, random capsule UUID, creation UTC
- suite identifier and Ed25519 public key
- encrypted-manifest entry, 96-bit nonce, and SHA-256 hash
- Argon2id/AES-GCM portable root-key wrap
- Ed25519 signature

The signature input is the canonical complete header with `signature` replaced by an empty string.
The signed manifest hash transitively authenticates the compartment hashes and CEK wraps.

## Key hierarchy

- The root key is 256 random bits.
- HKDF-SHA256 derives domain-separated manifest and compartment-wrap keys.
- Every compartment gets an independent random 256-bit CEK.
- Every AES-256-GCM operation gets a random 96-bit nonce.
- Export passphrases derive a 256-bit wrap key with Argon2id, minimum 64 MiB, 3 iterations, 1 lane,
  and a random 128-bit salt.

Associated data binds ciphertext to capsule ID, format, entry name, and purpose.

## Encrypted manifest

The manifest contains capsule ID, format version, monotonically increasing export sequence,
creation UTC, and descriptors for each compartment: UUID, semantic kind, safe entry name,
ciphertext hash, and authenticated CEK wrap. Labels and records exist only inside the compartment
ciphertext.

## Verification order

Readers validate archive structure and limits, parse the bounded header, verify its Ed25519
signature, verify the encrypted manifest hash, unwrap the root key, authenticate/decrypt the
manifest, check capsule identity and every declared entry, then unwrap/decrypt compartments.
Failure is closed and reported as a typed integrity error.

V3 readers MUST NOT decrypt, migrate, rewrite, or delete a detected V2 object. They return
`UnsupportedLegacyFormat` with a link to `v2.0.0`.

