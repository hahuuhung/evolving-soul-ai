import argparse
import getpass
import json
import os
import platform
import sys
from pathlib import Path

from .capsule import SoulCapsule
from .keyring_store import PlatformKeyring
from .service import create_app
from .vault import SoulVault

# Ensure Windows terminal handles UTF-8 safely without charmap crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _run_doctor(vault_path: Path, as_json: bool = False) -> int:
    py_ver = platform.python_version_tuple()
    py_ok = (int(py_ver[0]), int(py_ver[1])) >= (3, 11)
    
    # Check keyring backend
    keyring_name = "unknown"
    keyring_ok = False
    try:
        import keyring
        kr = keyring.get_keyring()
        keyring_name = type(kr).__name__
        # Supported native keyrings or fallback
        keyring_ok = "fail" not in keyring_name.lower()
    except Exception as exc:
        keyring_name = f"error: {exc}"

    # Check terminal encoding
    stdout_enc = getattr(sys.stdout, "encoding", "unknown") or "unknown"
    enc_ok = "utf" in stdout_enc.lower()

    # Check server dependencies
    has_server = False
    try:
        import uvicorn
        import fastapi
        has_server = True
    except ImportError:
        pass

    # Check vault existence and readability
    vault_status = "missing"
    capsule_id = None
    if (vault_path / "vault.json").exists():
        try:
            v = SoulVault.open(vault_path)
            vault_status = "unlocked"
            capsule_id = v.capsule_id
            v.lock()
        except Exception as exc:
            vault_status = f"locked/error ({exc})"

    report = {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "python": {
            "version": platform.python_version(),
            "compatible": py_ok,
        },
        "terminal": {
            "encoding": stdout_enc,
            "utf8_ready": enc_ok,
        },
        "keyring": {
            "backend": keyring_name,
            "ready": keyring_ok,
        },
        "server_dependencies": {
            "installed": has_server,
        },
        "vault": {
            "path": str(vault_path.resolve()),
            "status": vault_status,
            "capsule_id": capsule_id,
        },
    }

    if as_json:
        print(json.dumps(report, indent=2))
        return 0

    print("=================================================================")
    print("        EVOLVING SOUL AI — CROSS-PLATFORM SYSTEM DOCTOR          ")
    print("        Author: Ha Huu Hung (1985) — 8X Generation AI Engineer   ")
    print("=================================================================")
    print(f"OS Platform     : {report['os']['system']} {report['os']['release']} ({report['os']['machine']})")
    print(f"Python Version  : {report['python']['version']} -> [{'OK' if py_ok else 'WARN: >=3.11 recommended'}]")
    print(f"Terminal Output : {stdout_enc} -> [{'OK' if enc_ok else 'WARN: Set PYTHONIOENCODING=utf-8'}]")
    print(f"Keyring Backend : {keyring_name} -> [{'OK' if keyring_ok else 'WARN: keyring backend needs configuration'}]")
    print(f"Local Server    : FastAPI/Uvicorn -> [{'OK' if has_server else 'INFO: install evolving-soul-ai[server]'}]")
    print(f"Vault Directory : {vault_path}")
    print(f"Vault Status    : {vault_status} (capsule: {capsule_id or 'none'})")
    print("=================================================================")
    if py_ok and keyring_ok:
        print("System is fully ready for Evolving Soul AI operations.")
    else:
        print("Notice: some components have warnings. Review the flags above.")
    print("=================================================================")
    return 0


def _run_status(vault_path: Path, as_json: bool = False) -> int:
    state_file = vault_path / "vault.json"
    if not state_file.exists():
        msg = {"error": f"No vault found at {vault_path}. Run 'soul init' first."}
        if as_json:
            print(json.dumps(msg, indent=2))
        else:
            print(f"Error: No vault found at {vault_path.resolve()}.")
            print("Run 'soul init' to create a new local vault.")
        return 1

    try:
        vault = SoulVault.open(vault_path)
    except Exception as exc:
        msg = {"error": f"Failed to unlock vault: {exc}"}
        if as_json:
            print(json.dumps(msg, indent=2))
        else:
            print(f"Error: Unable to unlock vault at {vault_path}: {exc}")
        return 1

    try:
        memories = vault._require_memory().records()
        proposals = vault.list_proposals()
        store = vault._store
        passkeys = list(store.iter_objects("passkey")) if store else []
        succession = list(store.iter_objects("succession-policy")) if store else []
        pairing = list(store.iter_objects("pairing-state")) if store else []

        data = {
            "capsule_id": vault.capsule_id,
            "vault_path": str(vault_path.resolve()),
            "format": vault.metadata.get("format", "unknown"),
            "version": vault.metadata.get("version", 1),
            "export_sequence": vault.metadata.get("export_sequence", 0),
            "stats": {
                "memories_count": len(memories),
                "proposals_count": len(proposals),
                "passkeys_count": len(passkeys),
                "succession_configured": len(succession) > 0,
                "paired_integrations_count": len(pairing),
            },
        }

        if as_json:
            print(json.dumps(data, indent=2))
            return 0

        print("=================================================================")
        print("               EVOLVING SOUL AI — VAULT STATUS                   ")
        print("=================================================================")
        print(f"Capsule ID      : {data['capsule_id']}")
        print(f"Vault Location  : {data['vault_path']}")
        print(f"Format Version  : {data['format']} (v{data['version']})")
        print(f"Export Sequence : #{data['export_sequence']}")
        print("-----------------------------------------------------------------")
        print(f"Approved Memory : {data['stats']['memories_count']} records")
        print(f"Pending Reviews : {data['stats']['proposals_count']} proposals")
        print(f"Passkeys Bound  : {data['stats']['passkeys_count']} credentials")
        print(f"Succession Plan : {'Active' if data['stats']['succession_configured'] else 'Not configured'}")
        print(f"Integrations    : {data['stats']['paired_integrations_count']} paired")
        print("=================================================================")
        return 0
    finally:
        vault.lock()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="soul", description="Local-first AI continuity SDK")
    root.add_argument("--vault", default=".soul-vault", help="Local vault directory")
    commands = root.add_subparsers(dest="command", required=True)
    
    # doctor
    doctor_cmd = commands.add_parser("doctor", help="Cross-platform environment diagnostics (OS, Python, Keyring, Terminal)")
    doctor_cmd.add_argument("--json", action="store_true", help="Output diagnostic report in JSON format")

    # status
    status_cmd = commands.add_parser("status", help="Inspect local vault statistics and health")
    status_cmd.add_argument("--json", action="store_true", help="Output vault status in JSON format")

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

    if args.command == "doctor":
        return _run_doctor(vault_path, as_json=bool(getattr(args, "json", False)))

    if args.command == "status":
        return _run_status(vault_path, as_json=bool(getattr(args, "json", False)))

    if args.command == "init":
        vault = SoulVault.create(vault_path)
        print(f"Created local vault {vault.capsule_id} at {vault_path.resolve()}")
        vault.lock()
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
