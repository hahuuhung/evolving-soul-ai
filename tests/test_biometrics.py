"""
Kiểm thử sinh trắc học người thừa kế (YuNet + SFace, fallback histogram).
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import pytest

from evolving_soul import biometrics
from evolving_soul.biometrics import BiometricError, FaceBiometrics, ModelSpec, fetch_verified

ROOT = Path(__file__).resolve().parent.parent
MODEL_CACHE = Path(os.environ.get("EVOLVING_SOUL_MODEL_DIR", ROOT / "models"))
SAMPLES = {
    "lena.jpg": ModelSpec("lena.jpg", "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/lena.jpg",
                          "7de7ed51a1594fff247f4cae2301eceacf5313d6011e37b4a4c8733f7bb72c07"),
    "messi5.jpg": ModelSpec("messi5.jpg", "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/messi5.jpg",
                            "1d570e49654e84c7a943918537bd9e5e1ef82920152e147c834006e235be97c9"),
}


def synthetic_face_bytes(seed_val: int = 42) -> bytes:
    """Ảnh khuôn mặt giả lập (giống bộ test V2) — đủ cho fallback histogram."""
    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.circle(img, (100, 100), 70, int(150 + (seed_val % 80)), -1)
    cv2.circle(img, (75, 80), 12, 30, -1)
    cv2.circle(img, (125, 80), 12, 30, -1)
    cv2.ellipse(img, (100, 130), (30, 15), 0, 0, 180, 40, 4)
    return cv2.imencode(".jpg", img)[1].tobytes()


def encode(img: np.ndarray) -> bytes:
    return cv2.imencode(".jpg", img)[1].tobytes()


# =========================================================================
# KHÔNG CẦN MODEL
# =========================================================================

def test_checksum_mismatch_is_rejected(tmp_path):
    spec = ModelSpec("fake.onnx", "https://invalid.example/fake.onnx", "0" * 64)
    (tmp_path / "fake.onnx").write_bytes(b"model gia mao")
    assert fetch_verified(spec, tmp_path, allow_download=False) is None
    assert fetch_verified(ModelSpec("none.onnx", spec.url, spec.sha256), tmp_path, allow_download=False) is None


def test_fallback_histogram_is_low_assurance(tmp_path):
    bio = FaceBiometrics(tmp_path, allow_download=False)
    assert bio.method == "histogram"
    template = bio.enroll([synthetic_face_bytes(100)])
    result = bio.match(template, synthetic_face_bytes(100))
    assert result["assurance"] == "low"
    assert result["passed"] and result["cosine"] > 0.99
    assert template["samples"] == 1 and len(template["vector"]) == 64


def test_invalid_images_and_enrollment_counts(tmp_path):
    bio = FaceBiometrics(tmp_path, allow_download=False)
    with pytest.raises(BiometricError):
        bio.embed(None)
    with pytest.raises(BiometricError):
        bio.embed(b"khong phai anh")
    with pytest.raises(BiometricError):
        bio.enroll([])
    with pytest.raises(BiometricError):
        bio.enroll([synthetic_face_bytes()] * 4)


def test_sface_template_cannot_be_matched_without_models(tmp_path):
    bio = FaceBiometrics(tmp_path, allow_download=False)
    with pytest.raises(BiometricError):
        bio.match({"method": "sface", "vector": [0.1] * 128}, synthetic_face_bytes())


# =========================================================================
# CẦN MODEL YuNet + SFace (tự bỏ qua khi offline)
# =========================================================================

@pytest.fixture(scope="module")
def sface() -> FaceBiometrics:
    bio = FaceBiometrics(MODEL_CACHE, allow_download=True)
    if bio.method != "sface":
        pytest.skip("Không có model YuNet/SFace (offline?)")
    return bio


@pytest.fixture(scope="module")
def faces() -> dict[str, np.ndarray]:
    images = {}
    for name, spec in SAMPLES.items():
        path = fetch_verified(spec, MODEL_CACHE / "samples")
        if path is None:
            pytest.skip("Không tải được ảnh mẫu OpenCV (offline?)")
        images[name] = cv2.imread(str(path))
    return images


@pytest.mark.models
def test_sface_same_person_matches_different_person_rejected(sface, faces):
    lena, messi = faces["lena.jpg"], faces["messi5.jpg"]
    template = sface.enroll([encode(lena)])
    assert template["method"] == "sface" and len(template["vector"]) == 128

    same = sface.match(template, encode(cv2.convertScaleAbs(cv2.flip(lena, 1), alpha=0.8, beta=20)))
    assert same["passed"] and same["assurance"] == "high"
    assert same["cosine"] > 0.7

    other = sface.match(template, encode(messi))
    assert not other["passed"]
    assert other["cosine"] < biometrics.SFACE_COSINE_THRESHOLD


@pytest.mark.models
def test_sface_enrollment_requires_exactly_one_face(sface, faces):
    lena = cv2.resize(faces["lena.jpg"], (400, 400))
    messi = cv2.resize(faces["messi5.jpg"], (640, 400))
    with pytest.raises(BiometricError):
        sface.enroll([encode(np.hstack([lena, messi]))])
    with pytest.raises(BiometricError):
        sface.enroll([synthetic_face_bytes()])  # hình vẽ không phải khuôn mặt thật


@pytest.mark.models
def test_sface_multi_image_template_is_unit_norm(sface, faces):
    lena = faces["lena.jpg"]
    template = sface.enroll([encode(lena), encode(cv2.GaussianBlur(lena, (5, 5), 0))])
    assert template["samples"] == 2
    assert np.linalg.norm(template["vector"]) == pytest.approx(1.0, abs=1e-4)
