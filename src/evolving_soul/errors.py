"""Typed public errors; callers should not need to parse exception text."""


class SoulError(Exception):
    """Base class for SDK failures."""


class VaultLockedError(SoulError):
    """An operation requires an unlocked vault."""


class AuthenticationRequired(SoulError):
    """A fresh owner or guardian assertion is required."""


class CapsuleIntegrityError(SoulError):
    """A capsule is malformed, oversized, or fails authentication."""


class UnsupportedLegacyFormat(SoulError):
    """V2 data was detected but is intentionally not opened by V3."""

    documentation_url = "https://github.com/evolving-soul-ai/evolving-soul-ai/releases/tag/v2.0.0"

    def __init__(self) -> None:
        super().__init__(
            "Legacy V2 data is not supported by V3. Use the isolated v2.0.0 release; "
            "V3 will not migrate, decrypt, or delete it."
        )


class ProposalStateError(SoulError):
    """A proposal transition is invalid or no longer possible."""


class SuccessionError(SoulError):
    """A succession policy or claim is invalid."""
