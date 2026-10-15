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
import logging
import time
from typing import Callable

from evolving_soul import scoring
from evolving_soul.config import AUTHOR_ATTRIBUTION, Settings
from evolving_soul.errors import OwnerNotVerifiedError, ProfileExistsError, VaultLockedError
from evolving_soul.features import observe, probe_device
from evolving_soul.guard import AttemptGuard
from evolving_soul.logging_setup import kv
from evolving_soul.vault import Vault, VaultSession

logger = logging.getLogger("evolving_soul.engine")

SECONDS_PER_DAY = 86400.0
TRUST_HISTORY_LIMIT = 50


class EvolvingSoulEngine:
    """Lõi AI V3. Mỗi phiên người dùng (ví dụ một phiên Streamlit) nên giữ một instance riêng."""

    def __init__(
        self,
        settings: Settings | None = None,
        clock: Callable[[], float] = time.time,
        device_probe: Callable[[], tuple[str, str]] = probe_device,
    ):
        self.settings = settings or Settings.from_env()
        self.vault = Vault(self.settings.vault_dir, kdf_n=self.settings.kdf_n)
        self.guard = AttemptGuard(
            self.settings.vault_dir,
            max_failures=self.settings.max_failed_attempts,
            base_seconds=self.settings.lockout_base_seconds,
            clock=clock,
        )
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

    def create_vault(self, passphrase: str) -> None:
        self._session = self.vault.initialize(passphrase)
        self._profile = None
        self._owner_verified_at = None

    def unlock(self, passphrase: str) -> None:
        self.guard.check("unlock")
        try:
            session = self.vault.unlock(passphrase)
        except VaultLockedError:
            self.guard.record_failure("unlock")
            raise
        self.guard.record_success("unlock")
        self._session = session
        self._profile = self.vault.load_profile(session)
        self._owner_verified_at = None

    def lock(self) -> None:
        self._session = None
        self._profile = None
        self._owner_verified_at = None
        logger.info("vault_locked")

    def _require_unlocked(self) -> VaultSession:
        if not self.is_unlocked:
            raise VaultLockedError("Két sắt đang khóa — cần passphrase của Chủ nhân.")
        return self._session

    def _save(self) -> None:
        self.vault.save_profile(self._require_unlocked(), self._profile)

    # =====================================================================
    # PHIÊN CHỦ NHÂN ĐÃ XÁC MINH
    # =====================================================================

    @property
    def owner_verified(self) -> bool:
        if self._owner_verified_at is None or not self.is_unlocked:
            return False
        return (self._clock() - self._owner_verified_at) <= self.settings.owner_session_ttl_seconds

    def require_owner_verified(self) -> None:
        if not self.owner_verified:
            raise OwnerNotVerifiedError("Cần xác minh Chủ nhân (Tab Xác minh) trước khi thực hiện thao tác này.")

    # =====================================================================
    # ĐĂNG KÝ CHỦ NHÂN (GEN #1)
    # =====================================================================

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
        self._save()
        self._owner_verified_at = None
        logger.info("owner_registered %s", kv(generation=1, family_members=len(model["family"])))
        return self.profile

    # =====================================================================
    # XÁC MINH & TIẾN HÓA
    # =====================================================================

    def verify_owner(self, data: dict) -> dict:
        """
        Xác minh Chủ nhân; nếu đạt thì tiến hóa lên Gen #N+1 theo S_t = (1-α)·S_{t-1} + α·X_t.
        Sai liên tiếp `max_failed_attempts` lần -> LockedOutError.
        """
        session = self._require_unlocked()
        if self._profile is None:
            raise ProfileExistsError("Chưa có hồ sơ Chủ nhân để xác minh.")
        self.guard.check("owner")

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
        }

    def _on_owner_verified(self) -> None:
        """Điểm mở rộng: Di sản Số cập nhật heartbeat khi Chủ nhân xác minh thành công."""
