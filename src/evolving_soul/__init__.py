"""Evolving Soul AI V3 public SDK."""

from .errors import (
    AuthenticationRequired,
    CapsuleIntegrityError,
    SoulError,
    UnsupportedLegacyFormat,
    VaultLockedError,
)
from .types import (
    AuditEvent,
    CapsuleHeader,
    CapsuleManifest,
    Compartment,
    ConsentReceipt,
    MemoryProposal,
    MemoryRecord,
    Provenance,
    SuccessionPolicy,
)
from .vault import SoulVault

__all__ = [
    "AuditEvent",
    "AuthenticationRequired",
    "CapsuleHeader",
    "CapsuleIntegrityError",
    "CapsuleManifest",
    "Compartment",
    "ConsentReceipt",
    "MemoryProposal",
    "MemoryRecord",
    "Provenance",
    "SoulError",
    "SoulVault",
    "SuccessionPolicy",
    "UnsupportedLegacyFormat",
    "VaultLockedError",
]

__version__ = "3.0.0a1"
CAPSULE_FORMAT_VERSION = "1.0"

