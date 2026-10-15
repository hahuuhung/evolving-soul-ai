# Threat model — alpha

## Assets and goals

The protected assets are approved memory content, compartment keys, the local master key, signing
keys, owner consent records, and recovery material. The primary goals are confidentiality and
integrity of a capsule at rest, explicit owner control over memory admission, and prevention of a
coordinator-only or guardian-only succession release.

## Trust boundaries

1. The owner device and OS keyring hold the local master key.
2. The local sidecar decrypts approved memory only while unlocked.
3. Open WebUI runs third-party Python and receives only scoped context/proposal access.
4. The optional coordinator is online and authoritative for UTC time, but content-blind.
5. Guardians hold their SLIP-39 shares and passkeys outside the coordinator.

## Adversaries considered

- A stolen `.soul` file or local SQLite database
- A malicious model output or prompt injection stored as memory
- A compromised Open WebUI Function or stolen pairing token
- A malicious guardian, fewer than two guardians, or a compromised coordinator
- Archive parser abuse, entry tampering, rollback, replayed challenges, and brute-force attempts
- A curious coordinator database operator

## Controls

- Per-blob random AES-256-GCM nonces; per-purpose HKDF-SHA256 keys; independent compartment CEKs
- Ed25519-signed header and authenticated encrypted manifest containing every entry hash
- Argon2id export wrapping at no less than 64 MiB, three iterations, one lane
- ZIP entry count/size/ratio limits, exact declared-entry matching, and traversal rejection
- Encrypted opaque SQLite objects and an in-memory-only search index
- One-time, expiring WebAuthn challenges with RP ID, origin, user-verification, and counter checks
- Explicit proposal approval; rejected and expired proposal content is deleted
- Context is marked untrusted and never exposed as a model-callable write tool
- Top-level SLIP-39 2-of-2 groups: guardians 2-of-3 plus coordinator 1-of-1
- Coordinator time, fresh assertions, grace period, policy rotation, and signed receipts

## Out of scope or residual risk

- An attacker controlling the unlocked owner OS can read process memory or approve on the owner's
  behalf after compromising the browser/session.
- Metadata such as capsule archive size, export time, and compartment count is observable.
- Python and third-party cryptographic libraries are part of the trusted computing base.
- Alpha has not completed independent review, fuzzing coverage, cross-platform recovery drills, or
  side-channel analysis.
- Succession releases encrypted data; legal ownership and probate effects are outside this project.
- Availability is not guaranteed if owner and guardian devices or shares are lost.

## Non-goals

No biometric owner recognition, behavior-based authentication, password-style learning, covert
telemetry, legal asset transfer, “absolute privacy,” or “zero knowledge” claim is made.

