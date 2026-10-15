# SDK API reference

Stable alpha surface:

- `SoulVault.create(path)` / `SoulVault.open(path)` / `lock()`
- `export(destination, passphrase=...)` / `SoulVault.verify(source)`
- `propose_memory(...)` / `list_proposals()` / `approve_memory(...)` / `reject_memory(...)`
- `search_context(query, compartment_ids=..., token_budget=...)`
- `configure_succession(...)` / `revoke_succession(...)` / `check_in(...)`

Public protocol types are `CapsuleHeader`, `CapsuleManifest`, `Compartment`, `MemoryProposal`,
`MemoryRecord`, `ConsentReceipt`, `Provenance`, `SuccessionPolicy`, and `AuditEvent`.

`owner_asserted=True` is an SDK trust-boundary acknowledgement, not authentication by itself. Only
set it after a verified passkey ceremony. The bundled sidecar does this after `py_webauthn`
validation and a single-use five-minute step-up session.

