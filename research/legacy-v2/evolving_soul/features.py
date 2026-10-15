"""
Trích xuất đặc trưng 5 trụ cột (V3).

Khác với V2 (mọi đặc trưng là giá trị băm rời rạc), V3 tách:
  * Bí mật so khớp chính xác  -> HMAC-SHA256 (ngày sinh, tên người thân, OAuth, thói quen mật khẩu, thiết bị).
  * Đặc trưng hành vi liên tục -> số thực [0, 1] (văn phong, độ dài & độ đa dạng mật khẩu),
    nhờ đó công thức tiến hóa EMA có ý nghĩa thật.

Vector 14 chiều (theo CLAUDE.md §4):
  0-3   OAuth Trust     : khớp Google, khớp Apple, khớp Facebook, tỷ lệ liên kết khớp
  4-5   Family Lore     : khớp ngày sinh, độ phủ tên người thân
  6-8   Stylometry      : độ dài từ TB, độ dài câu TB, mật độ dấu câu
  9-11  Password habit  : độ dài, độ đa dạng lớp ký tự, khớp thói quen (tiền tố + cấu trúc)
  12-13 Device          : khớp thiết bị tin cậy, khớp hệ điều hành

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import platform
import re
from collections import Counter
from dataclasses import dataclass, field

from evolving_soul.crypto import SoulCipher, normalize_text, strip_diacritics

VECTOR_DIM = 14
OAUTH_PROVIDERS = ("google", "apple", "facebook")
IDX_OAUTH = slice(0, 4)
IDX_DOB, IDX_FAMILY = 4, 5
IDX_STYLE = slice(6, 9)
IDX_PW_LEN, IDX_PW_DIV, IDX_PW_HABIT = 9, 10, 11
IDX_DEVICE, IDX_OS = 12, 13
# Các chiều hành vi liên tục được tiến hóa bằng EMA
EVOLVING_DIMS = (6, 7, 8, IDX_PW_LEN, IDX_PW_DIV)

# Từ chỉ quan hệ gia đình (đã bỏ dấu) — bị loại khỏi tên để so khớp đúng người, không khớp "Bố", "Mẹ"...
RELATION_WORDS = {
    "bo", "ba", "me", "ma", "vo", "chong", "con", "trai", "gai", "dau", "re", "anh", "chi", "em",
    "ong", "noi", "ngoai", "co", "chu", "bac", "di", "cau", "mo", "thim", "chau", "ut", "ca",
    "ruot", "nuoi",
    "father", "mother", "dad", "mom", "wife", "husband", "son", "daughter", "brother", "sister",
    "grandpa", "grandma", "grandfather", "grandmother", "uncle", "aunt", "cousin",
}

# Hư từ tiếng Việt / Anh phổ biến — không dùng làm từ khóa văn phong
STOPWORDS = {
    "tôi", "toi", "mình", "minh", "và", "va", "là", "la", "của", "cua", "có", "co", "khi", "thì", "thi",
    "với", "voi", "cho", "các", "cac", "những", "nhung", "một", "mot", "được", "duoc", "này", "nay",
    "đó", "do", "để", "de", "trong", "vào", "vao", "ra", "lại", "lai", "rất", "rat", "cũng", "cung",
    "nhất", "nhat", "sự", "su", "đã", "da", "sẽ", "se", "đang", "dang", "thấy", "thay", "luôn", "luon",
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "i", "my", "me", "it", "at", "on", "with",
}

_LIST_SEPARATORS = re.compile(r"[,;\n/|]+")
_WORD = re.compile(r"\w+", re.UNICODE)
_SENTENCE_END = re.compile(r"[.!?…]+")


# =========================================================================
# CÁC HÀM ĐẶC TRƯNG THUẦN
# =========================================================================

def parse_family_names(text: str | None) -> list[str]:
    """
    Tách danh sách người thân thành tên đầy đủ đã chuẩn hóa (bỏ dấu, bỏ từ quan hệ ở đầu).
    "Bố Hà Văn A, Con trai Hà Minh Khôi" -> ["ha van a", "ha minh khoi"]
    """
    names: list[str] = []
    for chunk in _LIST_SEPARATORS.split(text or ""):
        tokens = strip_diacritics(chunk).replace(".", " ").split()
        while len(tokens) > 1 and tokens[0] in RELATION_WORDS:
            tokens.pop(0)
        if tokens and not (len(tokens) == 1 and tokens[0] in RELATION_WORDS):
            name = " ".join(tokens)
            if name not in names:
                names.append(name)
    return names


def style_features(answer: str | None) -> list[float]:
    """Stylometry: [độ dài từ TB / 10, số từ mỗi câu / 30, mật độ dấu câu * 10] — tất cả kẹp về [0, 1]."""
    text = normalize_text(answer)
    words = _WORD.findall(text)
    if not words:
        return [0.0, 0.0, 0.0]
    avg_word = sum(len(w) for w in words) / len(words)
    sentences = [s for s in _SENTENCE_END.split(text) if _WORD.search(s)] or [text]
    words_per_sentence = len(words) / len(sentences)
    punct = sum(1 for c in text if not c.isalnum() and not c.isspace())
    punct_rate = punct / max(len(text), 1)
    return [min(avg_word / 10.0, 1.0), min(words_per_sentence / 30.0, 1.0), min(punct_rate * 10.0, 1.0)]


def answer_keywords(answer: str | None) -> list[str]:
    """Từ có nghĩa trong câu trả lời mở (bỏ hư từ, bỏ từ 1 ký tự)."""
    return [w for w in _WORD.findall(normalize_text(answer)) if len(w) > 1 and w not in STOPWORDS]


def _char_class(c: str) -> str:
    if c.isupper():
        return "U"
    if c.islower():
        return "L"
    if c.isdigit():
        return "D"
    return "S"


def password_pattern(password: str | None) -> str:
    """Chuỗi lớp ký tự đã nén: "HungAI@1985#Secret" -> "ULUSDSUL" (không chứa ký tự gốc)."""
    pattern = ""
    for c in password or "":
        cls = _char_class(c)
        if not pattern or pattern[-1] != cls:
            pattern += cls
    return pattern


def password_features(password: str | None) -> tuple[float, float]:
    """[độ dài / 20, số lớp ký tự / 4] — không bao giờ lưu mật khẩu gốc."""
    pw = password or ""
    classes = {_char_class(c) for c in pw}
    return min(len(pw) / 20.0, 1.0), len(classes) / 4.0


def probe_device() -> tuple[str, str]:
    """Dấu vết thiết bị: (tên máy + HĐH + kiến trúc, họ HĐH). Ổn định hơn uuid.getnode() ở V2."""
    return f"{platform.node()}|{platform.system()}|{platform.machine()}", platform.system()


# =========================================================================
# QUAN SÁT MỘT PHIÊN
# =========================================================================

@dataclass
class Observation:
    """Toàn bộ đặc trưng của một phiên nhập liệu — chỉ chứa digest và số thực, không có văn bản gốc."""

    oauth: dict[str, str | None]
    dob: str | None
    family: set[str]
    traits: set[str]
    keywords: Counter
    style: list[float]
    pw_len: float
    pw_diversity: float
    pw_prefix: str | None
    pw_pattern: str | None
    device: str | None
    os_family: str | None
    extras: dict = field(default_factory=dict)


def observe(data: dict, cipher: SoulCipher, device: tuple[str, str] | None = None) -> Observation:
    """Chuyển dữ liệu nhập (dict giống V2) thành Observation đã băm HMAC."""
    password = str(data.get("password") or "")
    device_id, os_family = device if device is not None else probe_device()
    pw_len, pw_div = password_features(password)
    return Observation(
        oauth={p: cipher.digest(data.get(p), f"oauth:{p}") for p in OAUTH_PROVIDERS},
        dob=cipher.digest(data.get("dob"), "dob"),
        family={cipher.digest(n, "family") for n in parse_family_names(data.get("family"))},
        traits={normalize_text(t) for t in (data.get("traits") or []) if normalize_text(t)},
        keywords=Counter(cipher.digest(w, "keyword") for w in answer_keywords(data.get("answer"))),
        style=style_features(data.get("answer")),
        pw_len=pw_len,
        pw_diversity=pw_div,
        pw_prefix=cipher.digest(password[:3], "pw:prefix") if len(password) >= 3 else None,
        pw_pattern=cipher.digest(password_pattern(password), "pw:pattern") if password else None,
        device=cipher.digest(device_id, "device"),
        os_family=cipher.digest(os_family, "os"),
    )
