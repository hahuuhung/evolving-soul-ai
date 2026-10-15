"""
Bộ Kiểm Thử Nâng Cấp MCP, CLI & REST API Gateway — Evolving Soul AI
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import pytest
from fastapi.testclient import TestClient

from core_engine import EvolvingOwnerAI_V2
import soul_mcp
from soul_api import app


@pytest.fixture
def clean_test_vault(monkeypatch, tmp_path):
    """Fixture tạo thư mục két sắt tạm biệt lập cho từng test case."""
    vault_dir = str(tmp_path / "test_vault")
    os.makedirs(vault_dir, exist_ok=True)
    passphrase = "test_secret_passphrase_1985"

    monkeypatch.setenv("EVOLVING_SOUL_VAULT_DIR", vault_dir)
    monkeypatch.setenv("EVOLVING_SOUL_PASSPHRASE", passphrase)
    monkeypatch.setenv("EVOLVING_SOUL_DEMO", "1")
    monkeypatch.setenv("SOUL_API_KEY", "test_api_key_123")

    ai = EvolvingOwnerAI_V2(secret_key_phrase=passphrase, vault_dir=vault_dir, demo_mode=True)
    # Khởi tạo hồ sơ mẫu
    sample_owner = {
        "owner_name": "HÀ HỮU HƯNG (1985)",
        "google": "hahuuhung1985@gmail.com",
        "apple": "hung8x@icloud.com",
        "facebook": "fb.com/hahuuhung85",
        "dob": "1985-05-15",
        "family": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi",
        "traits": ["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
        "password": "HungAI@1985#Secret",
        "answer": "Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng."
    }
    ai.register_owner(sample_owner)
    ai.setup_digital_legacy(
        heir_name="Hà Minh Khôi",
        heir_email="khoi.ha@gmail.com",
        family_secret="Kỷ niệm ngôi nhà phố cổ Hà Nội 1985",
        assets_list=["Bản quyền Evolving Soul AI"],
        message_to_kin="Thông điệp trao gửi con trai.",
        inactivity_days=730,
        owner_session_verified=True
    )

    yield ai, vault_dir


# =========================================================================
# 1. KIỂM THỬ ĐỒNG THỜI & FILELOCK TRÊN KÉT SẮT
# =========================================================================

def test_filelock_concurrency(clean_test_vault):
    """Kiểm tra đa luồng cùng đọc và ghi hồ sơ đồng thời không bị hỏng file mã hóa."""
    ai, _ = clean_test_vault
    errors = []

    def writer_task(idx: int):
        try:
            for _ in range(5):
                prof = ai.load_profile()
                if prof:
                    prof["generation"] += 1
                    ai.save_profile(prof)
        except Exception as e:
            errors.append(e)

    def reader_task():
        try:
            for _ in range(10):
                prof = ai.load_profile()
                assert prof is not None
                assert "owner_name" in prof
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(4):
        threads.append(threading.Thread(target=writer_task, args=(i,)))
        threads.append(threading.Thread(target=reader_task))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Xảy ra lỗi đồng thời khi dùng FileLock: {errors}"
    final_prof = ai.load_profile()
    assert final_prof is not None
    assert final_prof["generation"] > 1


# =========================================================================
# 2. KIỂM THỬ MCP SERVER TOOLS VÀ RESOURCES
# =========================================================================

def test_mcp_tools_and_resources(clean_test_vault):
    """Kiểm tra hoạt động của các MCP Tools và Resources."""
    ai, _ = clean_test_vault

    # Tool: soul_get_status
    status = soul_mcp.soul_get_status()
    assert status["is_initialized"] is True
    assert status["owner_name"] == "HÀ HỮU HƯNG (1985)"
    assert "Định danh OAuth (SSO)" in status["radar_metrics"]

    # Tool: soul_verify_identity (chính chủ)
    res_verify = soul_mcp.soul_verify_identity(
        google_id="hahuuhung1985@gmail.com",
        apple_id="hung8x@icloud.com",
        facebook_id="fb.com/hahuuhung85",
        dob="1985-05-15",
        family="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi",
        traits=["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
        password_sample="HungAI@1985#Secret",
        security_answer="Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng."
    )
    assert res_verify["is_owner"] is True
    assert res_verify["trust_score"] >= 0.72

    # Tool: soul_evolve
    res_evolve = soul_mcp.soul_evolve(
        google_id="hahuuhung1985@gmail.com",
        apple_id="hung8x@icloud.com",
        facebook_id="fb.com/hahuuhung85",
        dob="1985-05-15",
        family="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi",
        traits=["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
        password_sample="HungAI@1985#Secret",
        security_answer="Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng."
    )
    assert res_evolve["status"] == "EVOLVED"
    assert res_evolve["new_generation"] >= 2

    # Tool: soul_get_persona_prompt
    persona = soul_mcp.soul_get_persona_prompt()
    assert "HÀ HỮU HƯNG (1985)" in persona
    assert "EVOLVING SOUL PERSONA" in persona

    # Tool: soul_legacy_status & soul_claim_legacy
    leg_stat = soul_mcp.soul_legacy_status(simulated_days_offline=0.0)
    assert leg_stat["is_unlockable"] is False

    # Thử claim khi offline đủ 735 ngày
    claim_res = soul_mcp.soul_claim_legacy(
        kin_name="Hà Minh Khôi",
        kin_email="khoi.ha@gmail.com",
        owner_dob="1985-05-15",
        other_family_members="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C",
        family_secret="Kỷ niệm ngôi nhà phố cổ Hà Nội 1985",
        simulated_days_offline=735.0
    )
    assert claim_res["is_unlocked"] is True
    assert len(claim_res["assets_unlocked"]) > 0

    # Resources
    prof_json = json.loads(soul_mcp.resource_profile())
    assert prof_json["owner_name"] == "HÀ HỮU HƯNG (1985)"

    radar_json = json.loads(soul_mcp.resource_radar())
    assert "Định danh OAuth (SSO)" in radar_json

    persona_str = soul_mcp.resource_persona()
    assert "HÀ HỮU HƯNG (1985)" in persona_str


# =========================================================================
# 3. KIỂM THỬ GIAO DIỆN DÒNG LỆNH CLI (RICH & JSON MODE)
# =========================================================================

def test_cli_subcommands(clean_test_vault):
    """Kiểm tra thực thi các câu lệnh CLI qua subprocess với cờ --json."""
    _, vault_dir = clean_test_vault
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["EVOLVING_SOUL_VAULT_DIR"] = vault_dir
    env["EVOLVING_SOUL_PASSPHRASE"] = "test_secret_passphrase_1985"
    env["EVOLVING_SOUL_DEMO"] = "1"

    # Lệnh: status --json
    cmd_stat = [sys.executable, "soul_cli.py", "--json", "status"]
    proc = subprocess.run(cmd_stat, capture_output=True, text=True, encoding="utf-8", env=env)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "INITIALIZED"
    assert data["owner_name"] == "HÀ HỮU HƯNG (1985)"

    # Lệnh: persona --json
    cmd_persona = [sys.executable, "soul_cli.py", "--json", "persona"]
    proc_p = subprocess.run(cmd_persona, capture_output=True, text=True, encoding="utf-8", env=env)
    assert proc_p.returncode == 0
    p_data = json.loads(proc_p.stdout)
    assert "persona_prompt" in p_data

    # Lệnh: verify --json
    cmd_verify = [
        sys.executable, "soul_cli.py", "--json", "verify",
        "--google", "hahuuhung1985@gmail.com",
        "--apple", "hung8x@icloud.com",
        "--facebook", "fb.com/hahuuhung85",
        "--dob", "1985-05-15",
        "--family", "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C",
        "--traits", "Thích công nghệ,Logic & Lý trí,Hướng nội",
        "--password", "HungAI@1985#Secret",
        "--answer", "Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng."
    ]
    proc_v = subprocess.run(cmd_verify, capture_output=True, text=True, encoding="utf-8", env=env)
    assert proc_v.returncode == 0
    v_data = json.loads(proc_v.stdout)
    assert v_data["is_owner"] is True

    # Lệnh: legacy status --json
    cmd_leg = [sys.executable, "soul_cli.py", "--json", "legacy", "status", "--simulate-days", "10"]
    proc_l = subprocess.run(cmd_leg, capture_output=True, text=True, encoding="utf-8", env=env)
    assert proc_l.returncode == 0
    l_data = json.loads(proc_l.stdout)
    assert "is_unlockable" in l_data


# =========================================================================
# 4. KIỂM THỬ FASTAPI REST GATEWAY
# =========================================================================

def test_fastapi_rest_endpoints(clean_test_vault):
    """Kiểm thử tất cả các REST API endpoints và xác thực Header X-API-Key."""
    client = TestClient(app)

    # 1. Health check (không cần API Key)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "HEALTHY"
    assert resp.json()["vault_initialized"] is True

    # 2. Soul status không có API Key -> 401
    resp_unauth = client.get("/api/v1/soul/status")
    assert resp_unauth.status_code == 401

    # 3. Soul status có API Key hợp lệ -> 200
    resp_stat = client.get("/api/v1/soul/status", headers={"X-API-Key": "test_api_key_123"})
    assert resp_stat.status_code == 200
    data = resp_stat.json()
    assert data["owner_name"] == "HÀ HỮU HƯNG (1985)"
    assert "Định danh OAuth (SSO)" in data["radar_metrics"]

    # 4. Xác thực danh tính qua POST /api/v1/soul/verify
    verify_payload = {
        "google_id": "hahuuhung1985@gmail.com",
        "apple_id": "hung8x@icloud.com",
        "facebook_id": "fb.com/hahuuhung85",
        "dob": "1985-05-15",
        "family": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C",
        "traits": ["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
        "password_sample": "HungAI@1985#Secret",
        "security_answer": "Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng."
    }
    resp_ver = client.post("/api/v1/soul/verify", json=verify_payload)
    assert resp_ver.status_code == 200
    assert resp_ver.json()["is_owner"] is True
    assert resp_ver.json()["trust_score"] >= 0.72

    # 5. Evolve qua POST /api/v1/soul/evolve (yêu cầu API Key)
    resp_evo = client.post("/api/v1/soul/evolve", json=verify_payload, headers={"X-API-Key": "test_api_key_123"})
    assert resp_evo.status_code == 200
    assert resp_evo.json()["status"] == "EVOLVED"

    # 6. Persona prompt qua GET /api/v1/soul/persona
    resp_per = client.get("/api/v1/soul/persona")
    assert resp_per.status_code == 200
    assert "HÀ HỮU HƯNG (1985)" in resp_per.json()["persona_prompt"]

    # 7. Legacy claim qua POST /api/v1/legacy/claim sau 735 ngày offline
    claim_payload = {
        "kin_name": "Hà Minh Khôi",
        "kin_email": "khoi.ha@gmail.com",
        "owner_dob": "1985-05-15",
        "other_family_members": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C",
        "family_secret": "Kỷ niệm ngôi nhà phố cổ Hà Nội 1985",
        "simulated_days_offline": 735.0
    }
    resp_claim = client.post("/api/v1/legacy/claim", json=claim_payload)
    assert resp_claim.status_code == 200
    c_res = resp_claim.json()
    assert c_res["is_unlocked"] is True
    assert len(c_res["assets_unlocked"]) > 0
