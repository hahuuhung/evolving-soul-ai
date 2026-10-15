import json
from pathlib import Path
from evolving_soul.cli import main
from evolving_soul.keyring_store import MemoryKeyStore
from evolving_soul.vault import SoulVault


def test_cli_doctor(capsys):
    ret = main(["doctor"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "EVOLVING SOUL AI" in captured
    assert "OS Platform" in captured


def test_cli_doctor_json(capsys):
    ret = main(["doctor", "--json"])
    assert ret == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "os" in data
    assert "python" in data
    assert "keyring" in data
    assert "vault" in data


def test_cli_status_missing(tmp_path, capsys):
    vault_dir = tmp_path / "nonexistent"
    ret = main(["--vault", str(vault_dir), "status"])
    assert ret == 1
    captured = capsys.readouterr().out
    assert "No vault found" in captured


def test_cli_status_json_missing(tmp_path, capsys):
    vault_dir = tmp_path / "nonexistent"
    ret = main(["--vault", str(vault_dir), "status", "--json"])
    assert ret == 1
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "error" in data


def test_cli_init_and_status(tmp_path, capsys):
    vault_dir = tmp_path / "cli_vault"
    # Init
    ret_init = main(["--vault", str(vault_dir), "init"])
    assert ret_init == 0
    captured_init = capsys.readouterr().out
    assert "Created local vault" in captured_init

    # Status text
    ret_status = main(["--vault", str(vault_dir), "status"])
    assert ret_status == 0
    captured_status = capsys.readouterr().out
    assert "EVOLVING SOUL AI — VAULT STATUS" in captured_status
    assert "Approved Memory" in captured_status

    # Status json
    ret_json = main(["--vault", str(vault_dir), "status", "--json"])
    assert ret_json == 0
    data = json.loads(capsys.readouterr().out)
    assert data["format"] == "evolving-soul-vault"
    assert data["stats"]["memories_count"] == 0
