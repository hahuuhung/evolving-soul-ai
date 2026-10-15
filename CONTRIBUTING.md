# Contributing

Thank you for helping build a portable continuity protocol for personal AI memory.

1. Discuss protocol or trust-boundary changes in an issue first.
2. Create a focused branch and include tests for security-relevant behavior.
3. Run `python -m pytest`, `ruff check .`, `ruff format --check .`, and `mypy`.
4. Sign every commit with `git commit -s` to certify the Developer Certificate of Origin 1.1.
5. Never submit real conversations, capsules, passkeys, guardian shares, credentials, or PII.

Cryptographic format changes require an ADR, conformance fixture update, and compatibility review.
No contributor may weaken KDF parameters, bypass passkey step-up, or add network egress defaults
without an explicit threat-model change.

