"""
Core AI Engine — Evolving Soul AI (Phiên bản V2)
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)
"""

import os
import json
import time
import hashlib
import platform
import uuid
import base64
import logging
import numpy as np
from cryptography.fernet import Fernet
from sklearn.metrics.pairwise import cosine_similarity

# Cấu hình Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("EvolvingSoulAI")


class EvolvingOwnerAI_V2:
    """
    Hệ thống nhận diện Chủ nhân phi sinh trắc học và Tự tiến hóa (Evolving Soul AI).
    Tích hợp bảo mật đa tầng, đồ thị gia đình, mã hóa thời gian và cơ chế thừa kế di sản số 2 năm.
    """

    def __init__(self, secret_key_phrase: str = "chu_nhan_bi_mat_v2_2026", vault_dir: str = "vault"):
        self.vault_dir = vault_dir
        self.vault_path = os.path.join(self.vault_dir, "owner_soul_v2.enc")

        if not os.path.exists(self.vault_dir):
            os.makedirs(self.vault_dir, exist_ok=True)
            logger.info("Đã tạo thư mục két sắt bảo mật: %s", self.vault_dir)

        # Khóa mã hóa đối xứng Fernet sinh từ SHA-256 của cụm từ bí mật
        key_hash = hashlib.sha256(secret_key_phrase.encode("utf-8")).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_hash))

        # Tốc độ tiến hóa thời gian (alpha = 0.15: giữ 85% bản sắc cũ, hấp thụ 15% thay đổi mới)
        self.alpha = 0.15
        logger.info("Khởi tạo EvolvingOwnerAI_V2 thành công với alpha=%.2f", self.alpha)

    # =========================================================================
    # CÁC HÀM XỬ LÝ ĐẶC TRƯNG & BĂM MỘT CHIỀU (ZERO-KNOWLEDGE)
    # =========================================================================

    def _hash_norm(self, text: str) -> float:
        """
        Băm chuỗi văn bản bằng SHA-256 và chuẩn hóa về miền số thực [0.0, 1.0].
        Đảm bảo tính bảo mật Zero-Knowledge: không thể giải mã ngược lại dữ liệu gốc.
        """
        if not text:
            return 0.0
        clean_text = str(text).strip().lower()
        h = int(hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:8], 16)
        return float((h % 10000) / 10000.0)

    def _extract_oauth_trust(self, google_id: str, apple_id: str, facebook_id: str) -> list[float]:
        """
        Lớp 1: Xác thực độ tin cậy từ các liên kết SSO / OAuth lớn.
        Đo độ phủ và chữ ký số định danh.
        """
        g_feat = self._hash_norm(google_id)
        a_feat = self._hash_norm(apple_id)
        f_feat = self._hash_norm(facebook_id)

        # Tỷ lệ liên kết: Càng nhiều tài khoản chính chủ càng tăng độ tin cậy nền tảng
        linked_accounts = [x for x in [google_id, apple_id, facebook_id] if x and str(x).strip()]
        linked_ratio = float(len(linked_accounts) / 3.0)

        return [g_feat, a_feat, f_feat, linked_ratio]

    def _extract_personal_lore(self, dob: str, family_members_str: str, personality_traits: list[str]) -> tuple[list[float], set[str]]:
        """
        Lớp 2: Ký ức gốc & Cá tính Chủ nhân (Ngày sinh, Thành viên gia đình, Nét cá tính).
        """
        dob_feat = self._hash_norm(dob)

        # Chuẩn hóa danh sách người thân (tách từ khóa và sắp xếp để độc lập thứ tự nhập)
        raw_tokens = family_members_str.replace(",", " ").replace(";", " ").split()
        family_tokens = sorted([w.strip().lower() for w in raw_tokens if w.strip()])
        family_feat = self._hash_norm("".join(family_tokens))

        # Chuẩn hóa nét cá tính
        traits_sorted = "".join(sorted([t.strip().lower() for t in personality_traits if t.strip()]))
        trait_feat = self._hash_norm(traits_sorted)

        return [dob_feat, family_feat, trait_feat], set(family_tokens)

    def _extract_behavior_and_device(self, password_sample: str, security_answer: str) -> tuple[list[float], set[str]]:
        """
        Lớp 3 & 4: Sinh trắc học hành vi (Thói quen cấu trúc mật khẩu, Stylometry & Thiết bị).
        Tuyệt đối không lưu mật khẩu gốc.
        """
        # Thói quen cấu trúc mật khẩu
        pw_str = str(password_sample) if password_sample else ""
        pw_len = float(min(len(pw_str) / 20.0, 1.0))

        has_upper = 1.0 if any(c.isupper() for c in pw_str) else 0.0
        has_digit = 1.0 if any(c.isdigit() for c in pw_str) else 0.0
        has_special = 1.0 if any(not c.isalnum() for c in pw_str) else 0.0
        pw_struct = float(has_upper * 0.3 + has_digit * 0.3 + has_special * 0.4)

        pw_prefix = self._hash_norm(pw_str[:3]) if len(pw_str) >= 3 else 0.0

        # Dấu vân tay thiết bị hiện tại
        mac_feat = self._hash_norm(str(uuid.getnode()))
        os_info = f"{platform.system()}_{platform.release()}"
        os_feat = self._hash_norm(os_info)

        # Phân tích văn phong câu trả lời mở (Stylometry)
        words = str(security_answer).strip().lower().split()
        avg_w_len = float(min(np.mean([len(w) for w in words]) / 10.0, 1.0)) if words else 0.0
        vocab_feat = self._hash_norm("".join(sorted(set(words))))

        features = [pw_len, pw_struct, pw_prefix, mac_feat, os_feat, avg_w_len, vocab_feat]
        return features, set(words)

    def build_soul_package(self, data_dict: dict) -> tuple[np.ndarray, set[str], set[str], dict[str, float]]:
        """
        Tổng hợp tất cả dữ liệu thành Vector đặc trưng 14 chiều và các metrics cho Radar Chart.
        """
        oauth_vec = self._extract_oauth_trust(
            data_dict.get("google", ""),
            data_dict.get("apple", ""),
            data_dict.get("facebook", "")
        )

        lore_vec, family_set = self._extract_personal_lore(
            data_dict.get("dob", ""),
            data_dict.get("family", ""),
            data_dict.get("traits", [])
        )

        behav_vec, word_set = self._extract_behavior_and_device(
            data_dict.get("password", ""),
            data_dict.get("answer", "")
        )

        full_vector = np.array(oauth_vec + lore_vec + behav_vec, dtype=np.float32)

        # 5 trụ cột trực quan hóa Radar Chart
        radar_metrics = {
            "Định danh OAuth (SSO)": float(np.mean(oauth_vec)),
            "Ký ức Gia đình & Ngày sinh": float(np.mean(lore_vec[:2])),
            "Cá tính & Văn phong Ngôn ngữ": float(np.mean([lore_vec[2], behav_vec[5], behav_vec[6]])),
            "Thói quen Cấu trúc Mật khẩu": float(np.mean(behav_vec[:3])),
            "Dấu vân tay Thiết bị": float(np.mean(behav_vec[3:5]))
        }

        return full_vector, family_set, word_set, radar_metrics

    # =========================================================================
    # LƯU TRỮ VÀ GIẢI MÃ KÉT SẮT (VAULT ENCRYPTION)
    # =========================================================================

    def save_profile(self, profile_data: dict) -> None:
        """Mã hóa toàn bộ hồ sơ bằng Fernet và ghi an toàn vào két sắt."""
        profile_data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        raw_bytes = json.dumps(profile_data).encode("utf-8")
        encrypted = self.cipher.encrypt(raw_bytes)
        with open(self.vault_path, "wb") as f:
            f.write(encrypted)
        logger.info("Đã mã hóa và lưu trữ thành công hồ sơ vào: %s", self.vault_path)

    def load_profile(self) -> dict | None:
        """Đọc và giải mã hồ sơ chủ nhân từ két sắt."""
        if not os.path.exists(self.vault_path):
            return None
        try:
            with open(self.vault_path, "rb") as f:
                encrypted_bytes = f.read()
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            logger.error("Lỗi khi giải mã hồ sơ két sắt: %s", e)
            return None

    # =========================================================================
    # ĐĂNG KÝ HỒ SƠ CHỦ NHÂN GỐC (ONBOARDING)
    # =========================================================================

    def register_owner(self, data_dict: dict) -> dict:
        """
        Khởi tạo 'Hạt giống Số' (Generation #1) của Chủ nhân.
        """
        vec, family_set, word_set, radar = self.build_soul_package(data_dict)

        profile = {
            "owner_name": data_dict.get("owner_name", "HÀ HỮU HƯNG (1985)"),
            "evolving_vector": vec.tolist(),
            "family_hashes": [self._hash_norm(w) for w in family_set],
            "cognitive_keywords": list(word_set),
            "traits_saved": data_dict.get("traits", []),
            "radar_baseline": radar,
            "generation": 1,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "author_attribution": "Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X"
        }

        self.save_profile(profile)
        logger.info("Chủ nhân '%s' đã được khởi tạo thành công (Gen #1)!", profile["owner_name"])
        return profile

    # =========================================================================
    # XÁC MINH CHỦ NHÂN & TIẾN HÓA TRƯỢT THỜI GIAN (EMA CONTINUAL LEARNING)
    # =========================================================================

    def verify_and_evolve(self, data_dict: dict) -> dict | None:
        """
        Xác minh danh tính Chủ nhân và tự động thích nghi (Tiến hóa lên Gen #N+1).
        Áp dụng công thức: S_t = (1 - alpha) * S_{t-1} + alpha * X_t
        """
        profile = self.load_profile()
        if not profile:
            logger.warning("Chưa có hồ sơ chủ nhân trong két sắt.")
            return None

        curr_vec, curr_family, curr_words, curr_radar = self.build_soul_package(data_dict)
        saved_vec = np.array(profile["evolving_vector"], dtype=np.float32)

        # 1. Đo độ khớp Vector tổng thể (Cosine Similarity)
        vec_sim = float(cosine_similarity([saved_vec], [curr_vec])[0][0])

        # 2. Đo độ khớp Trí nhớ Gia đình
        curr_fam_hashes = set([self._hash_norm(w) for w in curr_family])
        saved_fam_hashes = set(profile.get("family_hashes", []))
        fam_sim = float(len(curr_fam_hashes.intersection(saved_fam_hashes)) / max(len(saved_fam_hashes), 1))

        # 3. Đo độ khớp Ngữ nghĩa & Văn phong câu trả lời
        saved_words = set(profile.get("cognitive_keywords", []))
        word_sim = float(len(curr_words.intersection(saved_words)) / max(len(saved_words), 1))

        # Điểm Tin Cậy Tổng Hợp (Trust Score)
        trust_score = float((vec_sim * 0.55) + (fam_sim * 0.30) + (word_sim * 0.15))
        is_owner = trust_score >= 0.72

        logger.info(
            "Kết quả xác minh: vec_sim=%.3f, fam_sim=%.3f, word_sim=%.3f -> TrustScore=%.3f (IsOwner=%s)",
            vec_sim, fam_sim, word_sim, trust_score, is_owner
        )

        # CƠ CHẾ TIẾN HÓA TRƯỢT THỜI GIAN (EMA)
        if is_owner:
            new_vec = (1.0 - self.alpha) * saved_vec + (self.alpha * curr_vec)
            profile["evolving_vector"] = new_vec.tolist()
            profile["cognitive_keywords"] = list(saved_words.union(curr_words))[-60:]
            profile["generation"] += 1
            profile["radar_baseline"] = curr_radar

            # Cập nhật ping trực tuyến của chủ nhân cho giao thức di sản số
            if "legacy_config" in profile:
                profile["legacy_config"]["last_owner_ping"] = time.time()

            self.save_profile(profile)
            logger.info("Hồ sơ Chủ nhân đã tự động tiến hóa lên Thế hệ: Gen #%d", profile["generation"])

        return {
            "is_owner": is_owner,
            "trust_score": trust_score,
            "vec_sim": vec_sim,
            "fam_sim": fam_sim,
            "word_sim": word_sim,
            "generation": profile["generation"],
            "saved_radar": profile["radar_baseline"],
            "curr_radar": curr_radar,
            "owner_name": profile["owner_name"]
        }

    # =========================================================================
    # MODULE THỪA KẾ DI SẢN SỐ & SINH TRẮC HỌC KHẨN CẤP (DEAD MAN'S SWITCH 2 NĂM)
    # =========================================================================

    def _extract_biometric_vector(self, image_bytes: bytes | None) -> list[float] | None:
        """
        Trích xuất Vector đặc trưng sinh trắc học 64 chiều từ ảnh khuôn mặt/vân tay người thừa kế.
        Tuyệt đối không lưu ảnh gốc, chỉ lưu vector đã chuẩn hóa vào két sắt.
        """
        if not image_bytes:
            return None
        try:
            import cv2
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return None

            # Tự động cắt vùng khuôn mặt nếu có
            cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            if os.path.exists(cascade_path):
                face_cascade = cv2.CascadeClassifier(cascade_path)
                faces = face_cascade.detectMultiScale(img, 1.2, 5)
                for (x, y, w, h) in faces:
                    img = img[y:y + h, x:x + w]
                    break

            # Chuẩn hóa kích thước 64x64 và tính Histogram đặc trưng không gian
            img_resized = cv2.resize(img, (64, 64))
            hist = cv2.calcHist([img_resized], [0], None, [64], [0, 256])
            cv2.normalize(hist, hist)
            return hist.flatten().tolist()
        except Exception as e:
            logger.warning("Không thể xử lý sinh trắc học ảnh: %s", e)
            return None

    def setup_digital_legacy(
        self,
        heir_name: str,
        heir_email: str,
        family_secret: str,
        assets_list: list[str],
        message_to_kin: str,
        heir_bio_bytes: bytes | None = None,
        inactivity_days: int = 730
    ) -> dict:
        """
        Thiết lập giao thức Di sản Số với ngưỡng mặc định 2 năm (730 ngày) và khóa Sinh trắc học.
        """
        profile = self.load_profile()
        if not profile:
            raise ValueError("Cần khởi tạo hồ sơ Chủ nhân trước khi lập Di sản Số!")

        bio_vector = self._extract_biometric_vector(heir_bio_bytes)

        profile["legacy_config"] = {
            "heir_name_display": heir_name,
            "heir_name_hash": self._hash_norm(heir_name),
            "heir_email_hash": self._hash_norm(heir_email),
            "family_secret_hash": self._hash_norm(family_secret),
            "inactivity_threshold_days": int(inactivity_days),
            "last_owner_ping": time.time(),
            "heir_biometric_vector": bio_vector,
            "digital_assets": assets_list,
            "legacy_message": message_to_kin,
            "inheritance_claimed": False,
            "current_custodian": None
        }

        self.save_profile(profile)
        logger.info("Đã niêm phong Di sản Số cho người thừa kế '%s' (Ngưỡng: %d ngày)", heir_name, inactivity_days)
        return profile["legacy_config"]

    def check_inactivity_status(self, simulated_days_offline: float = 0.0) -> dict | None:
        """
        Kiểm tra trạng thái hoạt động của Chủ nhân đối chiếu với ngưỡng 2 năm (730 ngày).
        """
        profile = self.load_profile()
        if not profile or "legacy_config" not in profile:
            return None

        leg = profile["legacy_config"]
        elapsed_days = ((time.time() - leg.get("last_owner_ping", time.time())) / 86400.0) + simulated_days_offline
        threshold = leg.get("inactivity_threshold_days", 730)

        return {
            "elapsed_days": round(elapsed_days, 1),
            "threshold_days": threshold,
            "is_unlockable": elapsed_days >= threshold,
            "has_biometric_lock": leg.get("heir_biometric_vector") is not None,
            "heir_name_display": leg.get("heir_name_display", "Người thừa kế"),
            "inheritance_claimed": leg.get("inheritance_claimed", False)
        }

    def verify_kin_with_biometrics(
        self,
        kin_name: str,
        kin_email: str,
        owner_dob: str,
        other_family_members: str,
        family_secret_input: str,
        live_bio_bytes: bytes | None = None,
        simulated_days_offline: float = 0.0
    ) -> dict:
        """
        Xác thực Kép (Tri thức Gia đình + Sinh trắc học Người thừa kế sau 2 năm).
        """
        profile = self.load_profile()
        if not profile or "legacy_config" not in profile:
            return {"status": "ERROR", "msg": "Chủ nhân chưa thiết lập Di sản Số."}

        status = self.check_inactivity_status(simulated_days_offline)
        leg = profile["legacy_config"]

        # 1. Điểm Tri thức Gia đình & Định danh người thân
        name_match = 1.0 if self._hash_norm(kin_name) == leg["heir_name_hash"] else 0.0
        email_match = 1.0 if self._hash_norm(kin_email) == leg["heir_email_hash"] else 0.0

        # Kiểm tra ngày sinh gốc của chủ nhân
        owner_dob_hash = profile["evolving_vector"][4]
        dob_match = 1.0 if abs(self._hash_norm(owner_dob) - owner_dob_hash) < 0.001 else 0.0

        # Mạng lưới người thân trong gia đình
        raw_tokens = other_family_members.replace(",", " ").replace(";", " ").split()
        fam_tokens = [self._hash_norm(w) for w in raw_tokens if w.strip()]
        saved_fam = set(profile.get("family_hashes", []))
        fam_overlap = float(len(set(fam_tokens).intersection(saved_fam)) / max(len(saved_fam), 1))

        # Tín vật / Mật ước gia đình
        secret_match = 1.0 if self._hash_norm(family_secret_input) == leg["family_secret_hash"] else 0.0

        knowledge_score = float(
            (name_match * 0.20) + (email_match * 0.20) + (dob_match * 0.15) + (fam_overlap * 0.20) + (secret_match * 0.25)
        )

        # 2. Điểm Khớp Sinh Trắc Học Người Thừa Kế
        bio_score = 0.0
        saved_bio_vec = leg.get("heir_biometric_vector")

        if saved_bio_vec and live_bio_bytes:
            live_bio_vec = self._extract_biometric_vector(live_bio_bytes)
            if live_bio_vec:
                bio_score = float(cosine_similarity([saved_bio_vec], [live_bio_vec])[0][0])
        elif not saved_bio_vec:
            # Nếu chủ nhân không niêm phong mẫu sinh trắc học trước, dùng điểm tri thức
            bio_score = knowledge_score

        # Điều kiện: Khớp tri thức (>= 70%) VÀ Sinh trắc học (>= 75%)
        is_verified = (knowledge_score >= 0.70) and (bio_score >= 0.75)

        # Chỉ mở khóa tài sản khi thỏa mãn cả hai: Được xác thực VÀ Chủ nhân đã vắng mặt >= 730 ngày
        is_unlocked = is_verified and status["is_unlockable"]

        if is_unlocked:
            profile["legacy_config"]["inheritance_claimed"] = True
            profile["legacy_config"]["current_custodian"] = kin_name
            self.save_profile(profile)
            logger.info("Di sản số đã chính thức được chuyển giao cho: %s", kin_name)

        return {
            "is_verified": is_verified,
            "knowledge_score": knowledge_score,
            "bio_score": bio_score,
            "is_unlockable": status["is_unlockable"],
            "is_unlocked": is_unlocked,
            "elapsed_days": status["elapsed_days"],
            "threshold_days": status["threshold_days"],
            "assets": leg["digital_assets"] if is_unlocked else [],
            "message": leg["legacy_message"] if is_unlocked else "",
            "owner_name": profile["owner_name"]
        }
