"""
Cổng Giao Tiếp REST API Gateway (FastAPI) — Evolving Soul AI V3
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)

Swagger UI (/docs), ReDoc (/redoc). Cấu hình qua biến môi trường:
  EVOLVING_SOUL_PASSPHRASE  passphrase mở két (bắt buộc cho các endpoint của Chủ nhân)
  SOUL_API_KEY              khóa cho header X-API-Key (bắt buộc; không có giá trị mặc định)
  SOUL_API_CORS_ORIGINS     danh sách origin được phép, phân tách bởi dấu phẩy (mặc định: không cho phép)
Endpoint công khai: /api/v1/health và /api/v1/legacy/claim (bảo vệ bởi mật ước + khóa tạm chống dò).
"""

from __future__ import annotations

import hmac
import logging
import os
import time
from typing import Any, Callable, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

from evolving_soul import (
    EvolvingSoulEngine,
    EvolvingSoulError,
    LockedOutError,
    OwnerNotVerifiedError,
    ProfileExistsError,
    VaultLockedError,
    VaultNotFoundError,
    __version__,
    service,
)
from evolving_soul.config import AUTHOR_ATTRIBUTION
from evolving_soul.logging_setup import configure_logging

configure_logging()
logger = logging.getLogger("evolving_soul.api")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Xác thực header X-API-Key (so sánh thời gian hằng định)."""
    expected = os.environ.get("SOUL_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Máy chủ chưa cấu hình SOUL_API_KEY — endpoint của Chủ nhân bị vô hiệu hóa.")
    if not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="API Key không hợp lệ hoặc bị thiếu trong header 'X-API-Key'.")
    return api_key


# Ánh xạ lỗi nghiệp vụ -> mã HTTP (thứ tự: lớp cụ thể trước)
ERROR_STATUS = [
    (LockedOutError, status.HTTP_429_TOO_MANY_REQUESTS),
    (VaultNotFoundError, status.HTTP_404_NOT_FOUND),
    (VaultLockedError, status.HTTP_423_LOCKED),
    (OwnerNotVerifiedError, status.HTTP_403_FORBIDDEN),
    (ProfileExistsError, status.HTTP_409_CONFLICT),
    (PermissionError, status.HTTP_403_FORBIDDEN),
    (EvolvingSoulError, status.HTTP_400_BAD_REQUEST),
    (ValueError, status.HTTP_400_BAD_REQUEST),
]


def call(action: Callable[[], Any]) -> Any:
    try:
        return action()
    except tuple(kind for kind, _ in ERROR_STATUS) as exc:
        code = next(code for kind, code in ERROR_STATUS if isinstance(exc, kind))
        logger.warning("api_error type=%s status=%d", type(exc).__name__, code)
        headers = {"Retry-After": str(int(exc.retry_after_seconds) + 1)} if isinstance(exc, LockedOutError) else None
        raise HTTPException(status_code=code, detail=str(exc), headers=headers) from exc


# =========================================================================
# KHỞI TẠO FASTAPI APP
# =========================================================================

app = FastAPI(
    title="Evolving Soul AI — REST API Gateway",
    description=f"""
API Gateway kết nối hệ thống ngoài và AI Agents với **Evolving Soul AI V3**.
- **{AUTHOR_ATTRIBUTION}**
- **Bảo mật**: két sắt Fernet, khóa chủ bọc bằng Scrypt; bí mật băm HMAC-SHA256; chống dò bằng khóa tạm tăng dần.
- **Tiến hóa**: EMA $S_t = 0.85 \\cdot S_{{t-1}} + 0.15 \\cdot X_t$ trên các đặc trưng hành vi.
- **Di sản số**: Dead Man's Switch (mặc định 730 ngày), xác thực kép tri thức + sinh trắc.
    """,
    version=__version__,
    contact={"name": "HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X"},
)

_origins = [o.strip() for o in os.environ.get("SOUL_API_CORS_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_credentials=False,
                       allow_methods=["GET", "POST"], allow_headers=[API_KEY_NAME, "Content-Type"])


# =========================================================================
# PYDANTIC SCHEMAS
# =========================================================================

class IdentityPayload(BaseModel):
    google_id: str = Field(default="", description="Google OAuth ID hoặc email")
    apple_id: str = Field(default="", description="Apple Sign-in ID")
    facebook_id: str = Field(default="", description="Facebook ID")
    dob: str = Field(default="", description="Ngày sinh YYYY-MM-DD")
    family: str = Field(default="", description="Tên các thành viên gia đình, phân tách bởi dấu phẩy")
    traits: List[str] = Field(default_factory=list, description="Các nét cá tính cốt lõi")
    password_sample: str = Field(default="", description="Mẫu mật khẩu (chỉ học cấu trúc, không lưu)")
    security_answer: str = Field(default="", description="Câu trả lời mở để phân tích văn phong")

    def to_identity(self, owner_name: Optional[str] = None) -> dict:
        return service.identity(google=self.google_id, apple=self.apple_id, facebook=self.facebook_id, dob=self.dob,
                                family=self.family, traits=self.traits, password=self.password_sample,
                                answer=self.security_answer, owner_name=owner_name)


class RegisterPayload(IdentityPayload):
    owner_name: str = Field(default="HÀ HỮU HƯNG (1985)", description="Họ tên Chủ nhân")
    force_override: bool = Field(default=False, description="Ghi đè hồ sơ đã có (cần current_identity)")
    current_identity: Optional[IdentityPayload] = Field(default=None, description="Định danh hiện tại để xác minh khi ghi đè")


class LegacySetupPayload(BaseModel):
    owner_identity: IdentityPayload = Field(description="Định danh Chủ nhân — được xác minh ngay trong yêu cầu này")
    heir_name: str = Field(description="Họ tên người thừa kế")
    heir_email: str = Field(description="Email người thừa kế")
    family_secret: str = Field(description="Mật ước gia đình (≥ 10 ký tự)")
    assets_list: List[str] = Field(default_factory=list, description="Danh mục tài sản số")
    legacy_message: str = Field(default="", description="Lời nhắn cho người thừa kế")
    inactivity_days: int = Field(default=730, description="Ngưỡng vắng mặt (ngày)")


class LegacyClaimPayload(BaseModel):
    kin_name: str = Field(description="Họ tên người thừa kế")
    kin_email: str = Field(description="Email người thừa kế")
    owner_dob: str = Field(description="Ngày sinh của Chủ nhân")
    other_family_members: str = Field(description="Các thành viên khác trong gia đình")
    family_secret: str = Field(description="Mật ước gia đình")
    simulated_days_offline: float = Field(default=0.0, description="Số ngày mô phỏng offline (chỉ chế độ demo)")


# =========================================================================
# ENDPOINTS
# =========================================================================

@app.get("/api/v1/health", tags=["Hệ Thống"], summary="Trạng thái máy chủ & két sắt")
def get_health() -> dict[str, Any]:
    engine = EvolvingSoulEngine()
    return {
        "status": "HEALTHY",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "vault_initialized": engine.is_initialized,
        "profile_present": engine.has_profile,
        "legacy_sealed": engine.legacy_sealed,
        "author": "HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X",
        "version": __version__,
    }


@app.get("/api/v1/soul/status", tags=["Linh Hồn Số"], summary="Hồ sơ và 5 trụ cột radar")
def get_soul_status(_: str = Depends(verify_api_key)) -> dict[str, Any]:
    summary = call(lambda: service.profile_summary(service.open_engine()))
    if not summary["is_initialized"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Két sắt chưa có hồ sơ Chủ nhân.")
    return summary


@app.post("/api/v1/soul/verify", tags=["Bảo Mật & Xác Thực"], summary="Xác minh Chủ nhân (tiến hóa nếu đạt)")
def verify_identity(payload: IdentityPayload, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Xác minh 5 trụ cột. Nếu đạt, hồ sơ tiến hóa lên Gen #N+1. Sai 5 lần liên tiếp → 429."""
    return call(lambda: service.verify_summary(service.open_engine().verify_owner(payload.to_identity())))


@app.post("/api/v1/soul/evolve", tags=["Linh Hồn Số"], summary="Chu kỳ học liên tục EMA")
def evolve_soul(payload: IdentityPayload, api_key: str = Depends(verify_api_key)) -> dict[str, Any]:
    result = verify_identity(payload, api_key)
    if result["is_owner"]:
        return {"status": "EVOLVED", "new_generation": result["current_generation"], "trust_score": result["trust_score"],
                "updated_radar": result["updated_radar"],
                "message": f"Chủ nhân {result['owner_name']} đã tiến hóa lên Gen #{result['current_generation']}."}
    return {"status": "REJECTED", "is_owner": False, "trust_score": result["trust_score"],
            "message": f"Điểm tin cậy chưa đạt ngưỡng {result['threshold']:.0%}. Hồ sơ được giữ nguyên."}


@app.post("/api/v1/soul/register", tags=["Linh Hồn Số"], summary="Khởi tạo Hạt giống Số (Gen #1)")
def register_soul(payload: RegisterPayload, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    current = payload.current_identity.to_identity() if payload.current_identity else None
    profile = call(lambda: service.register(service.open_or_create_engine(), payload.to_identity(payload.owner_name),
                                            force=payload.force_override, current_identity=current))
    return {"status": "REGISTERED", "generation": 1, "created_at": profile["created_at"],
            "radar_baseline": profile["radar_baseline"], "message": f"Khởi tạo thành công cho {profile['owner_name']} (Gen #1)"}


@app.get("/api/v1/soul/persona", tags=["Linh Hồn Số"], summary="Persona Prompt cho AI Agent")
def get_persona_prompt(_: str = Depends(verify_api_key)) -> dict[str, str]:
    return {"persona_prompt": call(lambda: service.persona_prompt(service.open_engine()))}


@app.get("/api/v1/legacy/status", tags=["Di Sản Số"], summary="Đồng hồ Dead Man's Switch")
def get_legacy_status(simulated_days_offline: float = 0.0, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    def run():
        engine = service.open_engine()
        service.apply_demo_days(engine, simulated_days_offline)
        return engine.legacy_status()

    legacy_status = call(run)
    if not legacy_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chưa niêm phong Di sản Số.")
    return legacy_status


@app.post("/api/v1/legacy/setup", tags=["Di Sản Số"], summary="Niêm phong di sản (xác minh Chủ nhân trong cùng yêu cầu)")
def setup_legacy(payload: LegacySetupPayload, _: str = Depends(verify_api_key)) -> dict[str, Any]:
    legacy_status = call(lambda: service.seal_legacy(
        service.open_engine(), payload.owner_identity.to_identity(),
        heir_name=payload.heir_name, heir_email=payload.heir_email, family_secret=payload.family_secret,
        assets=payload.assets_list, message=payload.legacy_message, inactivity_days=payload.inactivity_days,
    ))
    return {"status": "CONFIGURED", **legacy_status}


@app.post("/api/v1/legacy/claim", tags=["Di Sản Số"], summary="Người thừa kế mở khóa di sản số")
def claim_legacy(payload: LegacyClaimPayload) -> dict[str, Any]:
    """
    Công khai cho người thừa kế (không cần API Key / passphrase): bảo vệ bởi mật ước gia đình,
    xác thực tri thức và khóa tạm sau 5 lần sai. Di sản có khóa sinh trắc phải tiếp quản qua giao diện Streamlit.
    """
    def run():
        engine = service.open_engine(unlock=False)
        service.apply_demo_days(engine, payload.simulated_days_offline)
        return service.claim_summary(engine.claim_legacy(
            kin_name=payload.kin_name, kin_email=payload.kin_email, owner_dob=payload.owner_dob,
            family_members=payload.other_family_members, family_secret=payload.family_secret,
        ))

    return call(run)
