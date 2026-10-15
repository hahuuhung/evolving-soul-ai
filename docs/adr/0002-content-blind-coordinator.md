# ADR 0002: Content-blind optional coordinator

- Status: accepted
- Date: 2026-10-15

The coordinator supplies authoritative UTC, heartbeat state, fresh guardian assertion checks, and
one SLIP-39 group share. It stores only a keyed capsule pseudonym, public credential material,
policy hash and timing state, encrypted notification destination, and its encrypted share. It does
not receive capsule files, memory, assets, CEKs, or guardian shares.

Top-level recovery is 2-of-2 groups: a 2-of-3 guardian group and a 1-of-1 coordinator group. This
prevents three guardians from bypassing grace/coordinator policy and prevents the coordinator from
recovering alone. The local vault remains usable when the service is offline.

