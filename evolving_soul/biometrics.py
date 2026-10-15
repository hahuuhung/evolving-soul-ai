"""
Sinh trắc học khuôn mặt người thừa kế (V3): OpenCV YuNet (phát hiện) + SFace (embedding 128 chiều).

- Model ONNX tải từ opencv_zoo lần đầu vào `Settings.model_dir`, kiểm tra SHA-256 cố định trước khi dùng.
  Môi trường offline: đặt sẵn 2 file vào thư mục và trỏ EVOLVING_SOUL_MODEL_DIR tới đó.
- Không bao giờ lưu ảnh; chỉ lưu embedding đã chuẩn hóa (trong hồ sơ đã mã hóa).
- Khi không có model: dùng histogram xám kiểu V2, gắn assurance="low". Theo chính sách di sản,
  mức này KHÔNG đủ để mở khóa một mình (bắt buộc điểm tri thức cao hơn).

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from evolving_soul.logging_setup import kv

logger = logging.getLogger("evolving_soul.biometrics")

ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"


@dataclass(frozen=True)
class ModelSpec:
    filename: str
    url: str
    sha256: str


DETECTOR = ModelSpec(
    "face_detection_yunet_2023mar.onnx",
    f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
)
RECOGNIZER = ModelSpec(
    "face_recognition_sface_2021dec.onnx",
    f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
)

# Ngưỡng cosine khuyến nghị của OpenCV cho SFace (cùng người khi >= 0.363)
SFACE_COSINE_THRESHOLD = 0.363
# Histogram xám rất dễ khớp nhầm -> ngưỡng cao và chỉ là mức bảo đảm thấp
HISTOGRAM_THRESHOLD = 0.90
MAX_IMAGE_SIDE = 1280


class BiometricError(ValueError):
    """Ảnh không dùng được cho sinh trắc học (không có mặt, nhiều mặt, ảnh hỏng...)."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_verified(spec: ModelSpec, target_dir: Path, allow_download: bool = True, timeout: float = 120.0) -> Path | None:
    """Trả về đường dẫn model đã kiểm tra SHA-256; tải về nếu chưa có (và được phép)."""
    path = Path(target_dir) / spec.filename
    if path.exists():
        if sha256_file(path) == spec.sha256:
            return path
        logger.error("model_checksum_mismatch %s", kv(file=spec.filename))
        return None
    if not allow_download:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=spec.filename + ".", suffix=".part", dir=path.parent)
    try:
        logger.info("model_download_start %s", kv(file=spec.filename))
        with urllib.request.urlopen(spec.url, timeout=timeout) as response, os.fdopen(fd, "wb") as out:  # noqa: S310 (URL cố định)
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
        if sha256_file(Path(tmp_name)) != spec.sha256:
            logger.error("model_download_checksum_mismatch %s", kv(file=spec.filename))
            return None
        os.replace(tmp_name, path)
        logger.info("model_download_done %s", kv(file=spec.filename))
        return path
    except OSError as exc:
        logger.warning("model_download_failed %s", kv(file=spec.filename, error=type(exc).__name__))
        return None
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def decode_image(image_bytes: bytes | None) -> np.ndarray:
    if not image_bytes:
        raise BiometricError("Chưa có ảnh.")
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise BiometricError("Không đọc được ảnh (định dạng không hỗ trợ hoặc file hỏng).")
    scale = MAX_IMAGE_SIDE / max(img.shape[:2])
    if scale < 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


def _cosine(a: list[float], b: list[float]) -> float:
    return float(np.dot(_unit(np.asarray(a, dtype=float)), _unit(np.asarray(b, dtype=float))))


class FaceBiometrics:
    """Trích xuất & so khớp embedding khuôn mặt. Model được nạp lười (lazy) ở lần dùng đầu tiên."""

    def __init__(self, model_dir: Path | str, allow_download: bool = True):
        self.model_dir = Path(model_dir)
        self.allow_download = allow_download
        self._detector = None
        self._recognizer = None
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        det_path = fetch_verified(DETECTOR, self.model_dir, self.allow_download)
        rec_path = fetch_verified(RECOGNIZER, self.model_dir, self.allow_download)
        if not (det_path and rec_path):
            logger.warning("biometrics_fallback_histogram %s", kv(reason="models_unavailable"))
            return
        try:
            self._detector = cv2.FaceDetectorYN.create(str(det_path), "", (320, 320), 0.8, 0.3, 5000)
            self._recognizer = cv2.FaceRecognizerSF.create(str(rec_path), "")
        except (cv2.error, AttributeError) as exc:
            logger.warning("biometrics_model_load_failed %s", kv(error=type(exc).__name__))
            self._detector = self._recognizer = None

    @property
    def method(self) -> str:
        """Phương pháp sẽ dùng cho đăng ký mới: "sface" (bảo đảm cao) hoặc "histogram" (bảo đảm thấp)."""
        self._load()
        return "sface" if self._recognizer is not None else "histogram"

    # ------------------------------------------------------------------
    # Trích xuất
    # ------------------------------------------------------------------

    def _detect(self, img: np.ndarray) -> np.ndarray:
        self._detector.setInputSize((img.shape[1], img.shape[0]))
        _, faces = self._detector.detect(img)
        return faces if faces is not None else np.empty((0, 15), dtype=np.float32)

    def _sface_embedding(self, img: np.ndarray, require_single: bool) -> list[float]:
        faces = self._detect(img)
        if len(faces) == 0:
            raise BiometricError("Không tìm thấy khuôn mặt trong ảnh.")
        if require_single and len(faces) > 1:
            raise BiometricError("Ảnh đăng ký phải có đúng một khuôn mặt.")
        face = max(faces, key=lambda f: f[2] * f[3])  # khuôn mặt lớn nhất
        feature = self._recognizer.feature(self._recognizer.alignCrop(img, face))
        return _unit(feature.flatten().astype(float)).tolist()

    @staticmethod
    def _histogram_embedding(img: np.ndarray) -> list[float]:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if os.path.exists(cascade_path):
            faces = cv2.CascadeClassifier(cascade_path).detectMultiScale(gray, 1.2, 5)
            if len(faces):
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                gray = gray[y:y + h, x:x + w]
        hist = cv2.calcHist([cv2.resize(gray, (64, 64))], [0], None, [64], [0, 256])
        return _unit(hist.flatten().astype(float)).tolist()

    def embed(self, image_bytes: bytes | None, method: str | None = None, require_single: bool = False) -> list[float]:
        img = decode_image(image_bytes)
        method = method or self.method
        if method == "sface":
            self._load()
            if self._recognizer is None:
                raise BiometricError("Mẫu sinh trắc được đăng ký bằng SFace nhưng hiện không có model để so khớp.")
            return self._sface_embedding(img, require_single)
        return self._histogram_embedding(img)

    # ------------------------------------------------------------------
    # Đăng ký & so khớp
    # ------------------------------------------------------------------

    def enroll(self, images: list[bytes]) -> dict:
        """Đăng ký 1–3 ảnh; lưu trung bình các embedding đã chuẩn hóa."""
        images = [b for b in images if b]
        if not 1 <= len(images) <= 3:
            raise BiometricError("Cần từ 1 đến 3 ảnh để đăng ký sinh trắc học.")
        method = self.method
        vectors = [self.embed(b, method, require_single=True) for b in images]
        template = _unit(np.mean(np.asarray(vectors, dtype=float), axis=0))
        logger.info("biometric_enrolled %s", kv(method=method, images=len(images)))
        return {"method": method, "vector": template.round(6).tolist(), "samples": len(images)}

    def match(self, template: dict, image_bytes: bytes | None) -> dict:
        """So khớp ảnh trực tiếp với mẫu đã niêm phong."""
        method = template["method"]
        threshold = SFACE_COSINE_THRESHOLD if method == "sface" else HISTOGRAM_THRESHOLD
        cosine = _cosine(template["vector"], self.embed(image_bytes, method))
        return {
            "method": method,
            "assurance": "high" if method == "sface" else "low",
            "cosine": cosine,
            "threshold": threshold,
            "score": max(0.0, min(1.0, cosine)),
            "passed": cosine >= threshold,
        }
