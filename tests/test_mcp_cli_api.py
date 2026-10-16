"""
Bộ kiểm thử cổng giao tiếp V3: MCP Server, Rich CLI & REST API Gateway, cùng khóa liên tiến trình.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from evolving_soul import EvolvingSoulEngine, Settings, service

ROOT = Path(__file__).resolve().parent.parent
PASSPHRASE = "test_secret_passphrase_1985"
API_KEY = "test_api_key_123"
SECRET = "Kỷ niệm ngôi nhà phố cổ Hà Nội 1985"
OWNER = {
    "owner_name": "HÀ HỮU HƯNG (1985)",
    "google": "hahuuhung1985@gmail.com",
    "apple": "hung8x@icloud.com",
    "facebook": "fb.com/hahuuhung85",
    "dob": "1985-05-15",
    "family": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi",
    "traits": ["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
    "password": "HungAI@1985#Secret",
    "answer": "Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng.",
}
IDENTITY_API = {
    "google_id": OWNER["google"], "apple_id": OWNER["apple"], "facebook_id": OWNER["facebook"], "dob": OWNER["dob"],
    "family": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C", "traits": OWNER["traits"],
    "password_sample": OWNER["password"], "security_answer": OWNER["answer"],
}
STRANGER_API = {"dob": "1995-01-01", "family": "Không rõ", "password_sample": "123456", "security_answer": "du lịch biển"}
CLAIM = {
    "kin_name": "Hà Minh Khôi", "kin_email": "khoi.ha@gmail.com", "owner_dob": "1985-05-15",
    "other_family_members": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C", "family_secret": SECRET,
}


@pytest.fixture
def vault_env(monkeypatch, tmp_path) -> Path:
    """Két sắt V3 tạm có hồ sơ Chủ nhân và di sản đã niêm phong; biến môi trường trỏ tới két này."""
    vault_dir = tmp_path / "vault"
    monkeypatch.setenv("EVOLVING_SOUL_VAULT_DIR", str(vault_dir))
    monkeypatch.setenv("EVOLVING_SOUL_PASSPHRASE", PASSPHRASE)
    monkeypatch.setenv("EVOLVING_SOUL_DEMO", "1")
    monkeypatch.setenv("EVOLVING_SOUL_MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("SOUL_API_KEY", API_KEY)

    engine = EvolvingSoulEngine(Settings.from_env())
    engine.create_vault(PASSPHRASE)
    engine.register_owner(OWNER)
    engine.verify_owner(OWNER)
    engine.seal_legacy(heir_name="Hà Minh Khôi", heir_email="khoi.ha@gmail.com", family_secret=SECRET,
                       assets=["Bản quyền Evolving Soul AI"], message="Thông điệp trao gửi con trai.")
    return vault_dir


def generation() -> int:
    return service.open_engine().profile["generation"]


# =========================================================================
# 1. KHÓA LIÊN TIẾN TRÌNH: KHÔNG MẤT CẬP NHẬT KHI GHI ĐỒNG THỜI
# =========================================================================

def test_concurrent_verifications_do_not_lose_updates(vault_env):
    start = generation()
    errors: list[Exception] = []

    def owner_session():
        try:
            for _ in range(3):
                assert service.open_engine().verify_owner(OWNER)["is_owner"]
        except Exception as exc:  # noqa: BLE001 — gom lỗi từ luồng để assert ở luồng chính
            errors.append(exc)

    def reader():
        try:
            for _ in range(5):
                assert service.profile_summary(service.open_engine())["is_initialized"]
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=owner_session) for _ in range(4)] + [threading.Thread(target=reader) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert generation() == start + 12  # 4 phiên x 3 lần, không lần nào bị ghi đè
    assert service.open_engine().audit_integrity()["ok"]


# =========================================================================
# 2. MCP SERVER (Python ≥ 3.10)
# =========================================================================

def test_mcp_tools_and_resources(vault_env):
    soul_mcp = pytest.importorskip("soul_mcp", reason="MCP SDK 2.x cần Python ≥ 3.10")

    status = soul_mcp.soul_get_status()
    assert status["is_initialized"] and status["owner_name"] == "HÀ HỮU HƯNG (1985)"
    assert status["soul_id"].startswith("SOUL-")
    assert "Định danh OAuth (SSO)" in status["radar_metrics"]

    owner_args = dict(google_id=OWNER["google"], apple_id=OWNER["apple"], facebook_id=OWNER["facebook"],
                      dob=OWNER["dob"], family=OWNER["family"], traits=OWNER["traits"],
                      password_sample=OWNER["password"], security_answer=OWNER["answer"])
    verified = soul_mcp.soul_verify_identity(**owner_args)
    assert verified["is_owner"] and verified["trust_score"] >= verified["threshold"]
    evolved = soul_mcp.soul_evolve(**owner_args)
    assert evolved["status"] == "EVOLVED" and evolved["new_generation"] == verified["current_generation"] + 1
    assert soul_mcp.soul_evolve(dob="1995-01-01", family="Không rõ")["status"] == "REJECTED"

    # Ghi đè hồ sơ không kèm định danh hiện tại -> bị từ chối
    hijack = soul_mcp.soul_register(owner_name="HACKER", dob="2000-01-01", family="X", force_override=True)
    assert hijack["status"] == "ERROR" and hijack["error_type"] == "OwnerNotVerifiedError"

    persona = soul_mcp.soul_get_persona_prompt()
    assert "HÀ HỮU HƯNG (1985)" in persona and "EVOLVING SOUL PERSONA" in persona
    for secret in ["1985-05-15", "Khôi", "HungAI", "bình yên"]:
        assert secret not in persona

    assert soul_mcp.soul_legacy_status()["is_unlockable"] is False
    claim = soul_mcp.soul_claim_legacy(**CLAIM, simulated_days_offline=735.0)
    assert claim["is_unlocked"] and claim["assets_unlocked"] == ["Bản quyền Evolving Soul AI"]

    assert json.loads(soul_mcp.resource_profile())["owner_name"] == "HÀ HỮU HƯNG (1985)"
    assert "Định danh OAuth (SSO)" in json.loads(soul_mcp.resource_radar())
    assert json.loads(soul_mcp.resource_legacy())["claimed"] is True


def test_mcp_without_passphrase_reports_locked(vault_env, monkeypatch):
    soul_mcp = pytest.importorskip("soul_mcp", reason="MCP SDK 2.x cần Python ≥ 3.10")
    monkeypatch.delenv("EVOLVING_SOUL_PASSPHRASE")
    result = soul_mcp.soul_get_status()
    assert result["status"] == "ERROR" and result["error_type"] == "VaultLockedError"


# =========================================================================
# 3. CLI (RICH & --json)
# =========================================================================

def _cli(*args: str, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env_overrides or {})}
    return subprocess.run([sys.executable, str(ROOT / "soul_cli.py"), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, cwd=ROOT, stdin=subprocess.DEVNULL)


def test_cli_subcommands(vault_env):
    proc = _cli("--json", "status")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["status"] == "ACTIVE" and data["owner_name"] == "HÀ HỮU HƯNG (1985)"

    proc = _cli("--json", "persona")
    assert proc.returncode == 0 and "persona_prompt" in json.loads(proc.stdout)

    proc = _cli("--json", "verify", "--google", OWNER["google"], "--apple", OWNER["apple"], "--facebook", OWNER["facebook"],
                "--dob", OWNER["dob"], "--family", "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C",
                "--traits", ",".join(OWNER["traits"]), "--password", OWNER["password"], "--answer", OWNER["answer"])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["is_owner"] is True

    proc = _cli("--json", "legacy", "status", "--simulate-days", "10")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["elapsed_days"] == pytest.approx(10.0, abs=0.2)

    proc = _cli("--json", "legacy", "claim", "--kin-name", CLAIM["kin_name"], "--kin-email", CLAIM["kin_email"],
                "--owner-dob", CLAIM["owner_dob"], "--family", CLAIM["other_family_members"], "--secret", SECRET,
                "--simulate-days", "800")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["is_unlocked"] is True


def test_cli_without_passphrase_fails_cleanly(vault_env):
    proc = _cli("--json", "status", env_overrides={"EVOLVING_SOUL_PASSPHRASE": ""})
    assert proc.returncode == 1
    assert "EVOLVING_SOUL_PASSPHRASE" in proc.stderr and "Traceback" not in proc.stderr


def test_cli_simulation_rejected_outside_demo(vault_env):
    proc = _cli("--json", "legacy", "status", "--simulate-days", "800", env_overrides={"EVOLVING_SOUL_DEMO": "0"})
    assert proc.returncode == 1 and "demo" in proc.stderr


# =========================================================================
# 4. REST API GATEWAY
# =========================================================================

@pytest.fixture
def client(vault_env):
    from fastapi.testclient import TestClient

    from soul_api import app
    return TestClient(app)


AUTH = {"X-API-Key": API_KEY}


def test_api_authentication(client, monkeypatch):
    health = client.get("/api/v1/health").json()
    assert health["status"] == "HEALTHY" and health["vault_initialized"] and health["legacy_sealed"]

    for method, path in [("get", "/api/v1/soul/status"), ("get", "/api/v1/soul/persona"), ("get", "/api/v1/legacy/status")]:
        assert getattr(client, method)(path).status_code == 401
        assert getattr(client, method)(path, headers={"X-API-Key": "sai"}).status_code == 401
    assert client.post("/api/v1/soul/verify", json=IDENTITY_API).status_code == 401  # V2 để trống, nay bắt buộc khóa

    monkeypatch.delenv("SOUL_API_KEY")
    assert client.get("/api/v1/soul/status", headers=AUTH).status_code == 503  # không có khóa mặc định


def test_api_owner_endpoints(client):
    status = client.get("/api/v1/soul/status", headers=AUTH)
    assert status.status_code == 200 and status.json()["owner_name"] == "HÀ HỮU HƯNG (1985)"

    verified = client.post("/api/v1/soul/verify", json=IDENTITY_API, headers=AUTH).json()
    assert verified["is_owner"] is True
    assert client.post("/api/v1/soul/evolve", json=IDENTITY_API, headers=AUTH).json()["status"] == "EVOLVED"
    assert client.post("/api/v1/soul/evolve", json=STRANGER_API, headers=AUTH).json()["status"] == "REJECTED"

    persona = client.get("/api/v1/soul/persona", headers=AUTH).json()["persona_prompt"]
    assert "HÀ HỮU HƯNG (1985)" in persona

    conflict = client.post("/api/v1/soul/register", json={**STRANGER_API, "owner_name": "HACKER"}, headers=AUTH)
    assert conflict.status_code == 409


def test_api_legacy_setup_requires_owner_identity(client):
    seal = {"heir_name": "Kẻ gian", "heir_email": "gian@example.com", "family_secret": "mat uoc moi cua ke gian",
            "assets_list": ["Chiếm đoạt"], "inactivity_days": 30}
    denied = client.post("/api/v1/legacy/setup", json={**seal, "owner_identity": STRANGER_API}, headers=AUTH)
    assert denied.status_code == 403
    assert client.get("/api/v1/legacy/status", headers=AUTH).json()["heir_name_display"] == "Hà Minh Khôi"

    ok = client.post("/api/v1/legacy/setup", json={**seal, "heir_name": "Hà Minh Khôi",
                                                    "owner_identity": IDENTITY_API}, headers=AUTH)
    assert ok.status_code == 200 and ok.json()["threshold_days"] == 30


def test_api_claim_and_lockout(client):
    early = client.post("/api/v1/legacy/claim", json=CLAIM).json()
    assert early["is_verified"] and not early["is_unlocked"] and early["assets_unlocked"] == []

    unlocked = client.post("/api/v1/legacy/claim", json={**CLAIM, "simulated_days_offline": 735.0}).json()
    assert unlocked["is_unlocked"] and len(unlocked["assets_unlocked"]) == 1

    wrong = {**CLAIM, "family_secret": "sai mat uoc roi"}
    for _ in range(5):
        assert client.post("/api/v1/legacy/claim", json=wrong).json()["is_verified"] is False
    locked = client.post("/api/v1/legacy/claim", json=CLAIM)
    assert locked.status_code == 429 and "Retry-After" in locked.headers
