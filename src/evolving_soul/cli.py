"""`soul` command line interface."""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path

from .capsule import SoulCapsule
from .service import create_app
from .vault import SoulVault


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="soul", description="Local-first AI continuity SDK")
    root.add_argument("--vault", default=".soul-vault", help="Local vault directory")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create a local vault and master key in the OS keyring")
    serve = commands.add_parser("serve", help="Run the local review and plugin sidecar")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    pair = commands.add_parser("pair", help="Pair an integration")
    pair.add_argument("integration", choices=["open-webui"])
    pair.add_argument("--user-id", required=True)
    capsule = commands.add_parser("capsule", help="Export or verify a capsule")
    capsule_sub = capsule.add_subparsers(dest="capsule_command", required=True)
    export = capsule_sub.add_parser("export")
    export.add_argument("destination")
    verify = capsule_sub.add_parser("verify")
    verify.add_argument("source")
    commands.add_parser("check-in", help="Create an owner heartbeat after passkey step-up")
    guardian = commands.add_parser("guardian", help="Guardian operations")
    guardian_sub = guardian.add_subparsers(dest="guardian_command", required=True)
    claim = guardian_sub.add_parser("claim")
    claim.add_argument("--coordinator", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    vault_path = Path(args.vault)
    if args.command == "init":
        vault = SoulVault.create(vault_path)
        print(f"Created local vault {vault.capsule_id} at {vault_path.resolve()}")
        return 0
    if args.command == "capsule" and args.capsule_command == "verify":
        header = SoulCapsule.verify(args.source)
        print(
            json.dumps(
                {"valid": True, "capsule_id": header.capsule_id, "format": header.format_version}
            )
        )
        return 0
    vault = SoulVault.open(vault_path)
    if args.command == "capsule" and args.capsule_command == "export":
        first = getpass.getpass("Export passphrase: ")
        second = getpass.getpass("Repeat passphrase: ")
        if first != second or not first:
            raise SystemExit("Passphrases do not match or are empty")
        print(vault.export(args.destination, passphrase=first))
        return 0
    if args.command == "serve":
        try:
            import uvicorn
        except ImportError as exc:
            raise SystemExit("Install evolving-soul-ai[server]") from exc
        app = create_app(vault, origin=f"http://{args.host}:{args.port}")
        issued = app.state.bootstrap_code
        print(f"One-time bootstrap code (expires {issued.expires_at.isoformat()}): {issued.code}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0
    if args.command in {"pair", "check-in"}:
        raise SystemExit("This command requires the local sidecar and a browser passkey step-up")
    if args.command == "guardian":
        raise SystemExit("Guardian claim must be completed against the configured coordinator")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
