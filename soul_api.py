"""
Cổng Giao Tiếp REST API Gateway (FastAPI) — Evolving Soul AI
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)

Cung cấp các API RESTful bảo mật Zero-Knowledge, hỗ trợ Swagger UI (/docs) và ReDoc (/redoc)
để các hệ thống web bên thứ ba, ứng dụng di động, microservices và webhook tích hợp dễ dàng.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, List, Optional

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from fastapi import Depends, FastAPI, Header, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

from core_engine import EvolvingOwnerAI_V2

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SoulAPI] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("soul_api")

# Cấu hình API Key
API_KEY_NAME = "X-API-Key"
DEFAULT_API_KEY = os.environ.get("SOUL_API_KEY", "soul_secret_api_key_2026")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Xác thực Header X-API-Key."""
    expected_key = os.environ.get("SOUL_API_KEY", DEFAULT_API_KEY)
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key không hợp lệ hoặc bị thiếu trong Header 'X-API-Key'."
        )
    return api_key


def get_engine() -> EvolvingOwnerAI_V2:
    """Khởi tạo engine dựa trên biến môi trường."""
    vault_dir = os.environ.get("EVOLVING_SOUL_VAULT_DIR", "vault")
    secret_key = os.environ.get("EVOLVING_SOUL_PASSPHRASE", "chu_nhan_bi_mat_v2_2026")
    demo_mode = os.environ.get("EVOLVING_SOUL_DEMO", "") == "1"
    return EvolvingOwnerAI_V2(secret_key_phrase=secret_key, vault_dir=vault_dir, demo_mode=demo_mode)


# =========================================================================
# KHỞI TẠO FASTAPI APP VỚI METADATA ĐẦY ĐỦ
# =========================================================================

app = FastAPI(
    title="Evolving Soul AI — REST API Gateway",
    description="""
API Gateway chuẩn quốc tế phục vụ kết nối các hệ thống ngoài và AI Agents với **Evolving Soul AI**.
- **Tác giả sáng lập**: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
- **Bảo mật**: Zero-Knowledge SHA-256 một chiều, mã hóa két sắt Fernet AES-128-CBC.
- **Tiến hóa thời gian**: Thuật toán EMA tự thích nghi liên tục $S_t = 0.85 \\cdot S_{t-1} + 0.15 \\cdot X_t$.
- **Di sản số**: Giao thức Dead Man's Switch 2 năm (730 ngày) chuyển giao an toàn cho người thừa kế.
    """,
    version="2.0.0",
    contact={
        "name": "HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X",
        "url": "https://github.com/hahuuhung/evolving-soul-ai"
    }
)

# CORS Middleware cho phép mọi client (web, mobile, bot) kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# PYDANTIC SCHEMAS (DATA CONTRACTS)
# =========================================================================

class IdentityPayload(BaseModel):
    google_id: str = Field(default="", description="Google OAuth ID hoặc email")
    apple_id: str = Field(default="", description="Apple Sign-in ID")
    facebook_id: str = Field(default="", description="Facebook ID")
    dob: str = Field(default="", description="Ngày sinh định dạng YYYY-MM-DD")
    family: str = Field(default="", description="Tên các thành viên gia đình (Family Lore)")
    traits: List[str] = Field(default_factory=list, description="Danh sách các nét cá tính cốt lõi")
    password_sample: str = Field(default="", description="Mẫu mật khẩu (chỉ trích xuất thói quen cấu trúc, không lưu trữ)")
    security_answer: str = Field(default="", description="Câu trả lời mở để phân tích văn phong Stylometry")


class RegisterPayload(IdentityPayload):
    owner_name: str = Field(default="HÀ HỮU HƯNG (1985)", description="Họ tên đầy đủ của Chủ nhân")
    force_override: bool = Field(default=False, description="Ghi đè nếu hồ sơ đã tồn tại")


class LegacySetupPayload(BaseModel):
    heir_name: str = Field(description="Họ tên người thừa kế")
    heir_email: str = Field(description="Email người thừa kế")
    family_secret: str = Field(description="Mật ước / Tín vật gia đình")
    assets_list: List[str] = Field(default_factory=list, description="Danh mục tài sản số thừa kế")
    legacy_message: str = Field(default="", description="Thông điệp gửi gắm cho thế hệ sau")
    inactivity_days: int = Field(default=730, description="Ngưỡng vắng mặt (mặc định: 730 ngày / 2 năm)")


class LegacyClaimPayload(BaseModel):
    kin_name: str = Field(description="Họ tên người thừa kế yêu cầu nhận di sản")
    kin_email: str = Field(description="Email người thừa kế")
    owner_dob: str = Field(description="Ngày sinh gốc của chủ nhân để đối chiếu")
    other_family_members: str = Field(description="Mạng lưới người thân trong gia đình")
    family_secret: str = Field(description="Mật ước bí mật gia đình")
    simulated_days_offline: float = Field(default=0.0, description="Số ngày mô phỏng offline (Demo mode)")


# =========================================================================
# CÁC ENDPOINT RESTFUL
# =========================================================================

@app.get("/api/v1/health", tags=["Hệ Thống"], summary="Kiểm tra trạng thái máy chủ & két sắt")
def get_health() -> dict[str, Any]:
    """Kiểm tra máy chủ đang hoạt động và tính toàn vẹn của két sắt."""
    engine = get_engine()
    profile = engine.load_profile()
    return {
        "status": "HEALTHY",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "vault_initialized": profile is not None,
        "author": "HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X",
        "version": "2.0.0"
    }


@app.get("/api/v1/soul/status", tags=["Linh Hồn Số"], summary="Xem hồ sơ và 5 trụ cột radar")
def get_soul_status(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Lấy dữ liệu định danh số, thế hệ hiện tại và 5 trụ cột radar của Chủ nhân."""
    engine = get_engine()
    profile = engine.load_profile()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Két sắt chưa có hồ sơ chủ nhân. Hãy khởi tạo trước."
        )

    legacy_status = engine.check_inactivity_status()
    return {
        "owner_name": profile.get("owner_name"),
        "generation": profile.get("generation"),
        "created_at": profile.get("created_at"),
        "last_updated": profile.get("last_updated"),
        "radar_metrics": profile.get("radar_baseline", {}),
        "traits": profile.get("traits_saved", []),
        "legacy_status": legacy_status,
        "attribution": profile.get("author_attribution")
    }


@app.post("/api/v1/soul/verify", tags=["Bảo Mật & Xác Thực"], summary="Xác thực danh tính chủ nhân phi sinh trắc học")
def verify_identity(payload: IdentityPayload) -> dict[str, Any]:
    """
    Xác minh danh tính theo chuẩn Zero-Knowledge:
    Kiểm tra 5 trụ cột đặc trưng, trả về Trust Score và kết luận is_owner.
    """
    engine = get_engine()
    data = {
        "google": payload.google_id,
        "apple": payload.apple_id,
        "facebook": payload.facebook_id,
        "dob": payload.dob,
        "family": payload.family,
        "traits": payload.traits,
        "password": payload.password_sample,
        "answer": payload.security_answer
    }
    result = engine.verify_and_evolve(data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Két sắt chưa được khởi tạo để xác minh."
        )

    return {
        "is_owner": result["is_owner"],
        "trust_score": round(result["trust_score"], 4),
        "vec_similarity": round(result["vec_sim"], 4),
        "family_match": round(result["fam_sim"], 4),
        "stylometry_match": round(result["word_sim"], 4),
        "current_generation": result["generation"],
        "owner_name": result["owner_name"]
    }


@app.post("/api/v1/soul/evolve", tags=["Linh Hồn Số"], summary="Kích hoạt chu kỳ học liên tục EMA")
def evolve_soul(payload: IdentityPayload, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    """
    Kích hoạt chu kỳ tiến hóa tự thích nghi.
    Nếu danh tính được xác minh hợp lệ, hồ sơ sẽ chuyển dịch vector và tăng lên Gen #N+1.
    """
    engine = get_engine()
    data = {
        "google": payload.google_id,
        "apple": payload.apple_id,
        "facebook": payload.facebook_id,
        "dob": payload.dob,
        "family": payload.family,
        "traits": payload.traits,
        "password": payload.password_sample,
        "answer": payload.security_answer
    }
    result = engine.verify_and_evolve(data)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Két sắt chưa được khởi tạo.")

    if result["is_owner"]:
        return {
            "status": "EVOLVED",
            "message": f"Chủ nhân {result['owner_name']} đã tiến hóa lên Thế hệ Gen #{result['generation']}!",
            "new_generation": result["generation"],
            "trust_score": round(result["trust_score"], 4),
            "updated_radar": result["curr_radar"]
        }
    else:
        return {
            "status": "REJECTED",
            "message": "Điểm tin cậy chưa đạt ngưỡng 72%. Hồ sơ được giữ nguyên.",
            "is_owner": False,
            "trust_score": round(result["trust_score"], 4)
        }


@app.post("/api/v1/soul/register", tags=["Linh Hồn Số"], summary="Khởi tạo Hạt giống Số (Gen #1)")
def register_soul(payload: RegisterPayload, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Khởi tạo hồ sơ Chủ nhân thế hệ đầu tiên vào két sắt."""
    engine = get_engine()
    data = {
        "owner_name": payload.owner_name,
        "google": payload.google_id,
        "apple": payload.apple_id,
        "facebook": payload.facebook_id,
        "dob": payload.dob,
        "family": payload.family,
        "traits": payload.traits,
        "password": payload.password_sample,
        "answer": payload.security_answer
    }
    try:
        profile = engine.register_owner(data, force=payload.force_override)
        return {
            "status": "REGISTERED",
            "message": f"Khởi tạo thành công cho {profile['owner_name']} (Gen #1)",
            "generation": 1,
            "created_at": profile["created_at"],
            "radar_baseline": profile["radar_baseline"]
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/soul/persona", tags=["Linh Hồn Số"], summary="Lấy Persona Prompt đồng hành")
def get_persona_prompt() -> dict[str, str]:
    """Sinh ra System Prompt mô tả chân dung, bản sắc và văn phong của chủ nhân cho AI Agents."""
    engine = get_engine()
    prompt = engine.generate_persona_prompt()
    return {"persona_prompt": prompt}


@app.get("/api/v1/legacy/status", tags=["Di Sản Số"], summary="Kiểm tra đồng hồ Dead Man's Switch (730 ngày)")
def get_legacy_status(simulated_days_offline: float = 0.0) -> dict[str, Any]:
    """Xem tiến độ đếm ngược thời gian vắng mặt của chủ nhân đối chiếu với ngưỡng 2 năm."""
    engine = get_engine()
    status = engine.check_inactivity_status(simulated_days_offline=simulated_days_offline)
    if not status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chưa cấu hình Di sản Số.")
    return status


@app.post("/api/v1/legacy/setup", tags=["Di Sản Số"], summary="Thiết lập di sản số và người thừa kế")
def setup_legacy(payload: LegacySetupPayload, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Thiết lập thông tin người thừa kế, tài sản số và thông điệp trao truyền."""
    engine = get_engine()
    try:
        cfg = engine.setup_digital_legacy(
            heir_name=payload.heir_name,
            heir_email=payload.heir_email,
            family_secret=payload.family_secret,
            assets_list=payload.assets_list,
            message_to_kin=payload.legacy_message,
            heir_bio_bytes=None,
            inactivity_days=payload.inactivity_days,
            owner_session_verified=True
        )
        return {"status": "CONFIGURED", "heir_name": cfg["heir_name_display"], "threshold_days": cfg["inactivity_threshold_days"]}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/v1/legacy/claim", tags=["Di Sản Số"], summary="Người thừa kế mở khóa di sản số")
def claim_legacy(payload: LegacyClaimPayload) -> dict[str, Any]:
    """
    Xác thực khẩn cấp Người thừa kế (Tri thức Gia đình + Mật ước).
    Chỉ mở khóa tài sản khi thỏa mãn cả 2 điều kiện: Chủ nhân offline >= 730 ngày VÀ Xác thực người thừa kế đạt chuẩn.
    """
    engine = get_engine()
    res = engine.verify_kin_with_biometrics(
        kin_name=payload.kin_name,
        kin_email=payload.kin_email,
        owner_dob=payload.owner_dob,
        other_family_members=payload.other_family_members,
        family_secret_input=payload.family_secret,
        live_bio_bytes=None,
        simulated_days_offline=payload.simulated_days_offline
    )
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("msg", "Lỗi xác thực"))

    return {
        "is_verified": res["is_verified"],
        "is_unlocked": res["is_unlocked"],
        "knowledge_score": round(res["knowledge_score"], 4),
        "elapsed_days": res["elapsed_days"],
        "threshold_days": res["threshold_days"],
        "assets_unlocked": res.get("assets", []) if res["is_unlocked"] else [],
        "legacy_message": res.get("message", "") if res["is_unlocked"] else "Di sản số đang được bảo vệ an toàn."
    }
