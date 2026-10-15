"""Synthetic, ephemeral demos. Never use this module with real data."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from .coordinator import (
    CoordinatorService,
    InMemoryCoordinatorRepository,
    PyWebAuthnAssertionVerifier,
    create_coordinator_app,
)
from .keyring_store import MemoryKeyStore
from .service import create_app
from .types import Provenance
from .vault import SoulVault


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic Evolving Soul demo")
    parser.add_argument("component", choices=["sidecar", "coordinator"])
    args = parser.parse_args(argv)
    import uvicorn

    if args.component == "sidecar":
        path = Path(tempfile.mkdtemp(prefix="soul-synthetic-demo-"))
        vault = SoulVault.create(path, key_store=MemoryKeyStore())
        vault.propose_memory(
            "Synthetic owner prefers short release notes.",
            provenance=Provenance(source="synthetic-demo"),
        )
        app = create_app(vault, rp_id="localhost", origin="http://localhost:8765")
        issued = app.state.bootstrap_code
        print(f"SYNTHETIC DEMO bootstrap code: {issued.code}")
        uvicorn.run(app, host="0.0.0.0", port=8765)  # noqa: S104  # nosec B104
    else:
        service = CoordinatorService(
            InMemoryCoordinatorRepository(),
            deployment_key=b"synthetic-demo-deployment-key-32b",
            verifier=PyWebAuthnAssertionVerifier(rp_id="localhost", origin="http://localhost:8770"),
        )
        app = create_coordinator_app(
            service,
            provisioning_token="synthetic-demo-only",  # noqa: S106  # nosec B106
        )
        uvicorn.run(app, host="0.0.0.0", port=8770)  # noqa: S104  # nosec B104
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
