# Security policy

## Supported versions

`3.0.0a1` is an experimental developer preview. It is not approved for important or irreplaceable
data. The historical V2 and behavioural prototype tags receive no security fixes.

## Reporting

Do not open a public issue for a suspected vulnerability. Use GitHub private vulnerability
reporting for this repository. Include affected version, impact, reproduction steps, and whether
any real personal data was involved. Do not include secrets, capsules, guardian mnemonics, or
personal memory in the report.

The project will acknowledge a report within three business days, provide a triage update within
seven business days, and coordinate disclosure after a fix is available. These are response
targets, not a warranty.

## Security boundaries

- The coordinator must never receive memory, capsule files, assets, compartment keys, or complete
  recovery material.
- OIDC links accounts only. It cannot unlock, export, change policy, revoke a claim, or approve
  memory.
- Open WebUI pairing tokens have only `context:read` and `proposal:create`.
- Adding/removing passkeys, export, policy changes, approvals, check-ins, and claim cancellation
  require a fresh passkey assertion.
- V3 does not process V2 secrets.

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for assumptions and residual risks.

