# Evolving Soul AI

**Owner-bound, local-first continuity for personal AI memory.**

[![CI](https://github.com/evolving-soul-ai/evolving-soul-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/evolving-soul-ai/evolving-soul-ai/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> **Developer preview (`3.0.0a1`). Do not use it for important data.** The protocol and
> implementation have not completed an external security audit.

Evolving Soul AI is a protocol and Python SDK for protecting, moving, and selectively
inheriting approved personal-AI memory. It is not a chatbot, identity classifier, legal asset
transfer service, or password-behaviour profiler.

## Why it is different

- **Soul Capsule:** a model-independent `.soul` archive with independently encrypted
  compartments.
- **Proof of Continuity:** owner and guardian passkeys plus coordinator-authoritative signed
  heartbeats.
- **Selective Succession:** a recovery bundle can unlock only owner-selected compartments and
  requires the coordinator group plus two of three guardian shares.

Memory always follows `candidate → encrypted pending queue → owner edit/approve/reject →
approved compartment`. Model output never approves itself.

## Five-minute developer preview

Requirements: Python 3.11–3.13 and an OS keyring supported by the `keyring` package.

```bash
python -m pip install -e ".[server,dev]"

# Cross-platform environment diagnostic
soul doctor

# Initialize & inspect vault
soul --vault .soul-vault init
soul --vault .soul-vault status

# Run local control plane (White Theme UI with Passkey & WebAuthn)
soul --vault .soul-vault serve
```

### 1-Click Launchers (Windows, Linux, macOS)
- **Linux & macOS**: `./soul.sh doctor` or 1-click UI demo: `./run_demo.sh`
- **Windows**: `soul.bat doctor` or 1-click UI demo: `run_demo.bat`
- See the complete [Cross-Platform Guide](docs/CROSS_PLATFORM.md) for OS keyring details, Passkey setup, and headless environments.

The server prints a one-time bootstrap code that expires after ten minutes. Open
`http://localhost:8765`, register a passkey, and use the local queue to review proposals.

Export and publicly verify a capsule:

```bash
soul --vault .soul-vault capsule export backup.soul
soul capsule verify backup.soul
```

The export passphrase wraps the capsule key with Argon2id (64 MiB, 3 iterations, 1 lane). The
local master key remains in the OS keyring.

## SDK

```python
from evolving_soul import Provenance, SoulVault

vault = SoulVault.open(".soul-vault")
proposal = vault.propose_memory(
    "The owner prefers concise release notes.",
    provenance=Provenance(source="my-local-agent"),
)

# A real application sets owner_asserted only after a verified passkey ceremony.
record = vault.approve_memory(
    proposal.proposal_id,
    actor_credential_id="verified-passkey-id",
    owner_asserted=True,
)
context = vault.search_context("release notes", token_budget=512)
```

Approved context is returned as untrusted data. Integrations must never interpret memory as a
tool instruction or policy override.

## Architecture

```text
Open WebUI Function ── scoped token ──> local sidecar ──> local encrypted vault
                                             │
                                  heartbeat / claim only
                                             │
                                      coordinator
                         (no memory, capsule, asset, or CEK)
```

The capsule works with the coordinator offline. Only heartbeat and succession become
unavailable. The official alpha supports one owner/capsule per sidecar.

Read the [threat model](docs/THREAT_MODEL.md), [Capsule Format 1.0](docs/spec/soul-capsule-1.0.md),
[architecture decisions](docs/adr/0001-v3-trust-reset.md), and
[comparison with adjacent projects](docs/WHY_NOT.md).

## V2 boundary

V3 does not migrate, decrypt, convert, or delete V2 data. A V3 reader only reports
`UnsupportedLegacyFormat` and points to the isolated [`v2.0.0`](../../releases/tag/v2.0.0)
tag. Behaviour scoring, password-habit learning, family lore, face models, and local-clock
succession remain historical research and are excluded from the V3 wheel.

Historical snapshots:

- `v2.0.0` → commit `062f338`
- `prototype-v3-behavioral` → commit `7de8174`

## Security status

This alpha makes no claim of “zero knowledge,” “absolute privacy,” biometric owner recognition,
or legal ownership transfer. See [SECURITY.md](SECURITY.md) to report a vulnerability. Stable
`3.0.0` is blocked on an external audit and zero open Critical/High findings.

## Community

English documentation is canonical. Translations live in `docs/i18n/`. Contributions use DCO
sign-off and the [Contributor Covenant](CODE_OF_CONDUCT.md). Start with issues labelled
`good first issue` or read [CONTRIBUTING.md](CONTRIBUTING.md).

Apache-2.0 — see [LICENSE](LICENSE), [NOTICE](NOTICE), and [AUTHORS](AUTHORS).
