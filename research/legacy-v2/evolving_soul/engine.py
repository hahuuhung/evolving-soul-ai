"""
EvolvingSoulEngine — façade điều phối két sắt, nhận diện Chủ nhân, tiến hóa và Di sản Số (V3).

Luồng Chủ nhân:
  create_vault(passphrase) / unlock(passphrase)  ->  register_owner(data)  ->  verify_owner(data)
Xác minh hành vi là lớp thứ hai SAU passphrase: hồ sơ chỉ đọc được khi két sắt đã mở khóa.
Thao tác nhạy cảm (khởi tạo lại, niêm phong di sản) yêu cầu Chủ nhân đã xác minh trong
`Settings.owner_session_ttl_seconds` gần nhất — trạng thái này do engine giữ, không phải tham số do bên gọi truyền vào.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import copy
import functools
import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Callable

from filelock import FileLock

from evolving_soul import legacy, legacy_v2, scoring
from evolving_soul.audit import AuditLog
from evolving_soul.biometrics import BiometricError, FaceBiometrics
from evolving_soul.config import AUTHOR_ATTRIBUTION, Settings
from evolving_soul.errors import OwnerNotVerifiedError, ProfileExistsError, VaultLockedError
from evolving_soul.features import observe, probe_device
from evolving_soul.guard import AttemptGuard
from evolving_soul.logging_setup import kv
from evolving_soul.vault import Vault, VaultSession

logger = logging.getLogger("evolving_soul.engine")

SECONDS_PER_DAY = 86400.0
TRUST_HISTORY_LIMIT = 50
LOCK_FILE = "vault.lock"
LOCK_TIMEOUT_SECONDS = 30.0


def _exclusive(method):
    """
    Khóa liên tiến trình (FileLock) quanh mọi thao tác đọc-sửa-ghi két sắt, để UI, CLI, MCP và REST API
    chạy đồng thời không ghi đè lẫn nhau. FileLock cho phép gọi lồng nhau trong cùng luồng.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        Path(self.settings.vault_dir).mkdir(parents=True, exist_ok=True)
        with self._file_lock:
            return method(self, *args, **kwargs)

    return wrapper


class EvolvingSoulEngine:
    """Lõi AI V3. Mỗi phiên người dùng (ví dụ một phiên Streamlit) nên giữ một instance riêng."""

    def __init__(
        self,
        settings: Settings | None = None,
        clock: Callable[[], float] = time.time,
        device_probe: Callable[[], tuple[str, str]] = probe_device,
        biometrics: FaceBiometrics | None = None,
    ):
        self.settings = settings or Settings.from_env()
        self.vault = Vault(self.settings.vault_dir, kdf_n=self.settings.kdf_n)
        self.audit = AuditLog(self.settings.vault_dir, clock=clock)
        self.biometrics = biometrics or FaceBiometrics(self.settings.model_dir)
        self.guard = AttemptGuard(
            self.settings.vault_dir,
            max_failures=self.settings.max_failed_attempts,
            base_seconds=self.settings.lockout_base_seconds,
            clock=clock,
        )
        self._file_lock = FileLock(str(Path(self.settings.vault_dir) / LOCK_FILE), timeout=LOCK_TIMEOUT_SECONDS)
        self._clock = clock
        self._device_probe = device_probe
        self._session: VaultSession | None = None
        self._profile: dict | None = None
        self._owner_verified_at: float | None = None
        self._demo_offset_days = 0.0

    # =====================================================================
    # THỜI GIAN & CHẾ ĐỘ DEMO
    # =====================================================================

    def now(self) -> float:
        """Đồng hồ hệ thống; chỉ ở chế độ demo mới được dịch thời gian để mô phỏng số ngày offline."""
        return self._clock() + self._demo_offset_days * SECONDS_PER_DAY

    @property
    def demo_mode(self) -> bool:
        return self.settings.demo_mode

    def set_demo_offset_days(self, days: float) -> None:
        if not self.settings.demo_mode:
            raise PermissionError("Chỉ được mô phỏng thời gian ở chế độ demo (EVOLVING_SOUL_DEMO=1).")
        self._demo_offset_days = float(days)

    # =====================================================================
    # VÒNG ĐỜI KÉT SẮT
    # =====================================================================

    @property
    def is_initialized(self) -> bool:
        return self.vault.is_initialized()

    @property
    def is_unlocked(self) -> bool:
        return self._session is not None and self._session.unlocked_by == "owner"

    @property
    def has_profile(self) -> bool:
        return self.vault.has_profile()

    @property
    def profile(self) -> dict | None:
        """Bản sao hồ sơ đã giải mã (chỉ khi két sắt đang mở khóa)."""
        return copy.deepcopy(self._profile) if self._profile is not None else None

    @_exclusive
    def create_vault(self, passphrase: str) -> None:
        self._session = self.vault.initialize(passphrase)
        self._profile = None
        self._owner_verified_at = None
        self.audit.append("vault_created", "ok")

    @_exclusive
    def unlock(self, passphrase: str) -> None:
        self.guard.check("unlock")
        try:
            session = self.vault.unlock(passphrase)
        except VaultLockedError:
            self.guard.record_failure("unlock")
            self.audit.append("vault_unlock", "denied")
            raise
        self.guard.record_success("unlock")
        self.audit.append("vault_unlock", "ok")
        self._session = session
        self._profile = self.vault.load_profile(session)
        self._owner_verified_at = None

    def lock(self) -> None:
        self._session = None
        self._profile = None
        self._owner_verified_at = None
        logger.info("vault_locked")

    @_exclusive
    def change_passphrase(self, new_passphrase: str) -> None:
        """Đổi passphrase (chỉ bọc lại khóa chủ). Yêu cầu Chủ nhân đã xác minh trong phiên."""
        session = self._require_unlocked()
        self.require_owner_verified()
        self.vault.change_passphrase(session, new_passphrase)
        self.audit.append("passphrase_changed", "ok")

    @property
    def soul_id(self) -> str | None:
        """Mã định danh công khai ổn định, dẫn xuất một chiều từ hồ sơ đã băm (không lộ dữ liệu gốc)."""
        if not self._profile or "model" not in self._profile:
            return None
        material = f"{self._profile['model'].get('dob')}|{self._profile.get('created_at')}"
        return "SOUL-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()

    def _require_unlocked(self) -> VaultSession:
        if not self.is_unlocked:
            raise VaultLockedError("Két sắt đang khóa — cần passphrase của Chủ nhân.")
        return self._session

    def _refresh(self) -> None:
        """Đọc lại hồ sơ từ đĩa (tránh ghi đè thay đổi do phiên khác, ví dụ người thừa kế vừa tiếp quản)."""
        if self.is_unlocked:
            self._profile = self.vault.load_profile(self._session)

    def _save(self, session: VaultSession | None = None) -> None:
        """Ghi hồ sơ, kèm neo nhật ký kiểm toán để phát hiện việc viết lại toàn bộ nhật ký."""
        self._profile["audit_anchor"] = self.audit.last_hash
        self.vault.save_profile(session or self._require_unlocked(), self._profile)

    # =====================================================================
    # PHIÊN CHỦ NHÂN ĐÃ XÁC MINH
    # =====================================================================

    @property
    def owner_verified(self) -> bool:
        if self._owner_verified_at is None or not self.is_unlocked:
            return False
        return (self._clock() - self._owner_verified_at) <= self.settings.owner_session_ttl_seconds

    @property
    def owner_session_remaining_seconds(self) -> float:
        if not self.owner_verified:
            return 0.0
        return max(0.0, self.settings.owner_session_ttl_seconds - (self._clock() - self._owner_verified_at))

    @property
    def legacy_sealed(self) -> bool:
        """Đã có lớp bọc khóa bằng mật ước (cổng người thừa kế dùng được) — không cần mở két."""
        return self.vault.has_legacy_wrap()

    def require_owner_verified(self) -> None:
        if not self.owner_verified:
            raise OwnerNotVerifiedError("Cần xác minh Chủ nhân (Tab Xác minh) trước khi thực hiện thao tác này.")

    # =====================================================================
    # ĐĂNG KÝ CHỦ NHÂN (GEN #1)
    # =====================================================================

    @_exclusive
    def register_owner(self, data: dict, force: bool = False) -> dict:
        """
        Khởi tạo 'Hạt giống Số' của Chủ nhân.
        Nếu đã có hồ sơ: chỉ ghi đè khi force=True VÀ Chủ nhân đã xác minh trong phiên;
        khởi tạo lại sẽ xóa Di sản Số đã niêm phong.
        """
        session = self._require_unlocked()
        if self.has_profile:
            if not force:
                raise ProfileExistsError("Hồ sơ Chủ nhân đã tồn tại.")
            self.require_owner_verified()
            self.vault.clear_legacy_secret(session)
            self.audit.append("owner_reinitialized", "ok")
            logger.warning("owner_reinitialized")

        obs = observe(data, session.cipher, self._device_probe())
        model = scoring.build_model(obs)
        self._profile = {
            "owner_name": str(data.get("owner_name") or "Chủ nhân"),
            "generation": 1,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "traits_saved": list(data.get("traits") or []),
            "model": model,
            "radar_baseline": scoring.baseline_radar(model),
            "trust_history": [],
            "author_attribution": AUTHOR_ATTRIBUTION,
        }
        self.audit.append("owner_registered", "ok", generation=1)
        self._save()
        self._owner_verified_at = None
        logger.info("owner_registered %s", kv(generation=1, family_members=len(model["family"])))
        return self.profile

    # =====================================================================
    # XÁC MINH & TIẾN HÓA
    # =====================================================================

    @_exclusive
    def verify_owner(self, data: dict) -> dict:
        """
        Xác minh Chủ nhân; nếu đạt thì tiến hóa lên Gen #N+1 theo S_t = (1-α)·S_{t-1} + α·X_t.
        Sai liên tiếp `max_failed_attempts` lần -> LockedOutError.
        """
        session = self._require_unlocked()
        self._refresh()
        if self._profile is None:
            raise ProfileExistsError("Chưa có hồ sơ Chủ nhân để xác minh.")
        self.guard.check("owner")
        if self._profile.get("migration_pending"):
            return self._complete_migration(data, session)

        obs = observe(data, session.cipher, self._device_probe())
        result = scoring.compare(obs, self._profile["model"], self.settings)
        curr_radar = scoring.radar_from_pillars(result["pillars"])
        saved_radar = dict(self._profile["radar_baseline"])
        is_owner = bool(result["is_owner"])

        history = self._profile.setdefault("trust_history", [])
        history.append({"ts": round(self.now()), "trust": round(result["trust_score"], 4), "is_owner": is_owner})
        del history[:-TRUST_HISTORY_LIMIT]

        if is_owner:
            self._profile["model"] = scoring.evolve(self._profile["model"], obs, result["vector"], self.settings)
            self._profile["radar_baseline"] = scoring.evolve_radar(saved_radar, curr_radar, self.settings.alpha)
            self._profile["generation"] += 1
            if data.get("traits"):
                self._profile["traits_saved"] = list(data["traits"])
            self._on_owner_verified()
            self.guard.record_success("owner")
            self._owner_verified_at = self._clock()
        else:
            self.guard.record_failure("owner")
        self.audit.append("owner_verification", "ok" if is_owner else "denied",
                          trust=round(result["trust_score"], 3), generation=self._profile["generation"])
        self._save()

        logger.info(
            "owner_verification %s",
            kv(is_owner=is_owner, trust=f"{result['trust_score']:.3f}", gate=result["gate_passed"],
               generation=self._profile["generation"]),
        )
        return {
            "is_owner": is_owner,
            "trust_score": result["trust_score"],
            "threshold": self.settings.owner_threshold,
            "gate_passed": result["gate_passed"],
            "pillars": result["pillars"],
            "details": result["details"],
            "generation": self._profile["generation"],
            "saved_radar": saved_radar,
            "curr_radar": curr_radar,
            "owner_name": self._profile["owner_name"],
            "migrated": False,
        }

    # =====================================================================
    # MIGRATION V2 -> V3
    # =====================================================================

    @property
    def v2_vault_path(self) -> Path:
        return Path(self.settings.vault_dir) / legacy_v2.V2_FILE

    @property
    def v2_backup_path(self) -> Path:
        return Path(self.settings.vault_dir) / "owner_soul_v2.v2.bak"

    @property
    def needs_migration(self) -> bool:
        """Có két sắt V2 nhưng chưa có két V3."""
        return self.v2_vault_path.exists() and not self.is_initialized

    @property
    def migration_pending(self) -> bool:
        """Đã chuyển dữ liệu V2 vào két V3, chờ Chủ nhân xác minh lần đầu để dựng mô hình V3."""
        return bool((self._profile or {}).get("migration_pending"))

    @_exclusive
    def migrate_from_v2(self, new_passphrase: str, v2_phrase: str = legacy_v2.V2_DEFAULT_PHRASE) -> dict:
        """
        Bước 1: giải mã két V2, tạo két V3 với passphrase mới, giữ dữ liệu V2 bên trong (đã mã hóa V3)
        và đổi tên file V2. Bước 2 diễn ra ở lần verify_owner() đầu tiên.
        """
        if self.is_initialized:
            raise ProfileExistsError("Đã có két sắt V3 — không migrate lại.")
        v2 = legacy_v2.read_v2_profile(self.v2_vault_path, v2_phrase)
        self.create_vault(new_passphrase)
        self._profile = {
            "owner_name": v2.get("owner_name", "Chủ nhân"),
            "generation": int(v2.get("generation", 1)),
            "created_at": v2.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S")),
            "traits_saved": list(v2.get("traits_saved", [])),
            "radar_baseline": {label: 1.0 for label in scoring.PILLAR_LABELS.values()},
            "trust_history": [],
            "author_attribution": AUTHOR_ATTRIBUTION,
            "migration_pending": True,
            "v2_profile": v2,
        }
        self.audit.append("migration_started", "ok", generation=self._profile["generation"])
        self._save()
        os.replace(self.v2_vault_path, self.v2_backup_path)
        logger.info("migration_started %s", kv(generation=self._profile["generation"]))
        return self.profile

    def _complete_migration(self, data: dict, session: VaultSession) -> dict:
        """Chấm điểm bằng thuật toán V2 trên dữ liệu cũ; nếu đạt thì dựng mô hình V3 từ chính phiên này."""
        trust = legacy_v2.v2_trust_score(self._profile["v2_profile"], data)
        is_owner = trust >= legacy_v2.V2_THRESHOLD
        saved_radar = dict(self._profile["radar_baseline"])
        history = self._profile.setdefault("trust_history", [])
        history.append({"ts": round(self.now()), "trust": round(trust, 4), "is_owner": is_owner})

        pillars: dict = {p: None for p in scoring.PILLARS}
        if is_owner:
            v2 = self._profile.pop("v2_profile")
            model = scoring.build_model(observe(data, session.cipher, self._device_probe()))
            self._profile.update({
                "model": model,
                "radar_baseline": scoring.baseline_radar(model),
                "generation": self._profile["generation"] + 1,
                "migration_pending": False,
                "legacy_v2_pending": legacy_v2.pending_legacy_summary(v2),
            })
            if data.get("traits"):
                self._profile["traits_saved"] = list(data["traits"])
            pillars = {p: (1.0 if s is not None else None) for p, s in scoring.compare(
                observe(data, session.cipher, self._device_probe()), model, self.settings)["pillars"].items()}
            self.guard.record_success("owner")
            self._owner_verified_at = self._clock()
            self.audit.append("migration_completed", "ok", trust_v2=round(trust, 3), generation=self._profile["generation"])
        else:
            self.guard.record_failure("owner")
            self.audit.append("owner_verification", "denied", trust_v2=round(trust, 3), migration=True)
        self._save()
        if is_owner and self.v2_backup_path.exists():
            self.v2_backup_path.unlink()  # file V2 dùng khóa công khai trong mã nguồn -> xóa sau khi đã dựng xong V3
        logger.info("migration_verification %s", kv(is_owner=is_owner, trust_v2=f"{trust:.3f}"))
        return {
            "is_owner": is_owner,
            "trust_score": trust,
            "threshold": legacy_v2.V2_THRESHOLD,
            "gate_passed": is_owner,
            "pillars": pillars,
            "details": {},
            "generation": self._profile["generation"],
            "saved_radar": saved_radar,
            "curr_radar": self._profile["radar_baseline"] if is_owner else {k: 0.0 for k in saved_radar},
            "owner_name": self._profile["owner_name"],
            "migrated": is_owner,
        }

    def _on_owner_verified(self) -> None:
        """Heartbeat Di sản Số: Chủ nhân còn hoạt động -> đặt lại đồng hồ 730 ngày, thu hồi nếu đã bị tiếp quản."""
        config = self._profile.get("legacy")
        if config and legacy.heartbeat(config, self.now()):
            self.audit.append("legacy_claim_revoked", "ok")
            logger.warning("legacy_claim_revoked_owner_returned")

    # =====================================================================
    # DI SẢN SỐ — PHÍA CHỦ NHÂN
    # =====================================================================

    @_exclusive
    def seal_legacy(
        self,
        *,
        heir_name: str,
        heir_email: str,
        family_secret: str,
        assets: list[str],
        message: str,
        heir_images: list[bytes] | None = None,
        inactivity_days: int | None = None,
    ) -> dict:
        """Niêm phong Di sản Số (ghi đè lần niêm phong trước). Yêu cầu Chủ nhân đã xác minh trong phiên."""
        session = self._require_unlocked()
        self.require_owner_verified()
        if not heir_name.strip() or not heir_email.strip() or not assets:
            raise ValueError("Cần đủ họ tên, email người thừa kế và ít nhất một tài sản số.")
        if len(family_secret.strip()) < legacy.MIN_FAMILY_SECRET_LENGTH:
            raise ValueError(f"Mật ước gia đình phải dài tối thiểu {legacy.MIN_FAMILY_SECRET_LENGTH} ký tự.")
        days = int(inactivity_days or self.settings.inactivity_days)
        if days < 30 and not self.settings.demo_mode:
            raise ValueError("Ngưỡng vắng mặt tối thiểu 30 ngày.")

        template = self.biometrics.enroll(heir_images) if heir_images else None
        self._refresh()
        self._profile["legacy"] = legacy.seal(
            session.cipher, self.settings,
            heir_name=heir_name, heir_email=heir_email, family_secret=family_secret,
            assets=assets, message=message, biometric=template, inactivity_days=days, now=self.now(),
        )
        self.vault.set_legacy_secret(session, family_secret)
        self.audit.append("legacy_sealed", "ok", threshold_days=days, biometric=template["method"] if template else "none",
                          assets=len(assets))
        self._save()
        return self.legacy_status()

    @_exclusive
    def legacy_status(self) -> dict | None:
        """Trạng thái Dead Man's Switch cho Chủ nhân (két sắt đang mở khóa)."""
        self._require_unlocked()
        self._refresh()
        config = (self._profile or {}).get("legacy")
        return legacy.status(config, self.now(), self.settings) if config else None

    @_exclusive
    def revoke_legacy(self) -> None:
        session = self._require_unlocked()
        self.require_owner_verified()
        self._refresh()
        self._profile.pop("legacy", None)
        self.vault.clear_legacy_secret(session)
        self.audit.append("legacy_revoked", "ok")
        self._save()

    # =====================================================================
    # DI SẢN SỐ — CỔNG TIẾP QUẢN CỦA NGƯỜI THỪA KẾ
    # =====================================================================

    @_exclusive
    def claim_legacy(
        self,
        *,
        kin_name: str,
        kin_email: str,
        owner_dob: str,
        family_members: str,
        family_secret: str,
        live_image: bytes | None = None,
    ) -> dict:
        """
        Xác thực kép người thừa kế (không cần passphrase của Chủ nhân).
        Chỉ bàn giao tài sản khi: xác thực đạt VÀ Chủ nhân vắng mặt ≥ ngưỡng (mặc định 730 ngày).
        """
        self.guard.check("kin")
        result = {
            "is_verified": False, "is_unlockable": False, "is_unlocked": False,
            "knowledge_score": 0.0, "knowledge_parts": {}, "bio": None,
            "assets": [], "message": "", "owner_name": None, "reason": "",
            "elapsed_days": None, "threshold_days": None,
        }
        try:
            session = self.vault.unlock_with_legacy_secret(family_secret)
        except VaultLockedError as exc:
            self.guard.record_failure("kin")
            self.audit.append("legacy_claim", "denied", reason="secret")
            result["reason"] = str(exc)
            return result

        profile = self.vault.load_profile(session)
        config = (profile or {}).get("legacy")
        if not config:
            result["reason"] = "Chủ nhân chưa niêm phong Di sản Số."
            return result

        state = legacy.status(config, self.now(), self.settings)
        knowledge, parts = legacy.knowledge_score(
            config, profile["model"], session.cipher,
            kin_name=kin_name, kin_email=kin_email, owner_dob=owner_dob, family_members=family_members,
        )
        bio = None
        if config.get("biometric") and live_image:
            try:
                bio = self.biometrics.match(config["biometric"], live_image)
            except BiometricError as exc:
                result["reason"] = str(exc)
        verified, reason = legacy.decide(knowledge, bio, config.get("biometric") is not None, self.settings)
        unlocked = verified and state["is_unlockable"]

        result.update({
            "is_verified": verified, "is_unlockable": state["is_unlockable"], "is_unlocked": unlocked,
            "knowledge_score": knowledge, "knowledge_parts": parts, "bio": bio,
            "owner_name": profile["owner_name"], "reason": result["reason"] or reason,
            "elapsed_days": state["elapsed_days"], "threshold_days": state["threshold_days"],
        })
        if not verified:
            self.guard.record_failure("kin")
        else:
            self.guard.record_success("kin")
        if unlocked:
            payload = legacy.open_payload(config, family_secret)
            result["assets"], result["message"] = payload["assets"], payload["message"]
            config.update({"claimed": True, "custodian_display": kin_name, "claimed_at": self.now()})
            self.audit.append("legacy_claim", "unlocked", knowledge=round(knowledge, 3),
                              bio=round(bio["cosine"], 3) if bio else None)
            profile["audit_anchor"] = self.audit.last_hash
            self.vault.save_profile(session, profile)
            self._refresh()
            logger.warning("legacy_transferred %s", kv(elapsed_days=state["elapsed_days"]))
        else:
            outcome = "verified_locked" if verified else "denied"
            self.audit.append("legacy_claim", outcome, knowledge=round(knowledge, 3),
                              bio=round(bio["cosine"], 3) if bio else None)
        return result

    # =====================================================================
    # NHẬT KÝ KIỂM TOÁN
    # =====================================================================

    def audit_events(self, n: int = 20) -> list[dict]:
        return self.audit.tail(n)

    def audit_integrity(self) -> dict:
        anchor = (self._profile or {}).get("audit_anchor")
        return self.audit.verify(anchor)
