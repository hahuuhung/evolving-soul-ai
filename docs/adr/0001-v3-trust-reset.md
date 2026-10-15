# ADR 0001: V3 trust reset

- Status: accepted
- Date: 2026-10-15

## Context

The prototype coupled personal memory with behavioral scoring, face models, family knowledge, a
locally measured inactivity timer, and direct family-secret wrapping. Those mechanisms were hard
to audit, produced misleading product claims, and did not create portable model-independent
memory.

## Decision

V3 is a local-first continuity protocol and SDK. Passkeys are the authentication root, OIDC is
account linking only, memory admission always requires owner consent, and the optional coordinator
stores no content. V3 uses a new `src/` package and Capsule Format 1.0. Historical modules remain
outside the wheel and are not imported by the V3 package.

V3 is intentionally incompatible with V2. There is no automatic migration.

## Consequences

The alpha has a smaller, auditable security boundary and supports selective recovery. Existing V2
users must keep the V2 release isolated. Stable release requires independent audit and recovery
drills.

