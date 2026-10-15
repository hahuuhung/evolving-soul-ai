"""
Bộ sinh dữ liệu giả lập để hiệu chỉnh ngưỡng nhận diện (FAR / FRR).

- owner_base     : hồ sơ gốc của một Chủ nhân ngẫu nhiên.
- owner_session  : Chủ nhân sau nhiều năm — nêu một phần người thân, đổi mật khẩu theo thói quen,
                   viết lại câu trả lời bằng văn phong cũ, đôi khi dùng thiết bị mới.
- stranger       : người lạ hoàn toàn (đôi khi dùng chung máy).
- insider        : người nhà biết ngày sinh + tên người thân, dùng chung máy, nhưng thói quen mật khẩu
                   và văn phong là của chính họ.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import random

SURNAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Hà"]
MIDDLES = ["Văn", "Thị", "Minh", "Hữu", "Đức", "Thanh", "Ngọc", "Quang", "Thu", "Hoài", "Gia", "Bảo"]
GIVENS = ["An", "Bình", "Châu", "Dũng", "Giang", "Hải", "Hùng", "Khôi", "Lan", "Linh", "Long", "Mai", "Nam", "Ngân",
          "Phúc", "Quân", "Sơn", "Tâm", "Thảo", "Trang", "Tuấn", "Vy", "Yến", "Hưng", "Hà", "Khoa"]
RELATIONS = ["Bố", "Mẹ", "Vợ", "Chồng", "Con trai", "Con gái", "Anh", "Chị", "Em", "Ông", "Bà"]
TRAITS = ["Hướng nội", "Hướng ngoại", "Logic & Lý trí", "Giàu cảm xúc", "Thích công nghệ", "Yêu nghệ thuật",
          "Cầu toàn", "Phóng khoáng", "Thức khuya", "Dậy sớm", "Thích sự yên tĩnh", "Ưa mạo hiểm"]
VOCAB = ["bình", "yên", "gia", "đình", "trà", "nóng", "code", "đêm", "sáng", "sớm", "đọc", "sách", "biển", "núi",
         "nhạc", "cà", "phê", "vườn", "hoa", "mưa", "chạy", "bộ", "con", "cháu", "quê", "nhà", "bếp", "nấu", "ăn",
         "thiền", "câu", "cá", "du", "lịch", "game", "phim", "bạn", "bè", "chó", "mèo", "xe", "đạp", "viết", "vẽ",
         "học", "dạy", "làm", "việc", "nghỉ", "ngơi", "hát", "karaoke", "bóng", "đá", "tập", "gym", "yoga", "chợ"]
WORDS_UPPER = ["Hung", "Lan", "Mai", "Son", "Nam", "Khoi", "Tam", "Bao", "Vy", "Linh", "Long", "Quan"]
WORDS_LOWER = ["secret", "pass", "home", "love", "sky", "moon", "code", "family", "happy", "sun", "tea", "rain"]
SPECIALS = "@#!$%&*"


def _name(rng: random.Random) -> str:
    return f"{rng.choice(SURNAMES)} {rng.choice(MIDDLES)} {rng.choice(GIVENS)}"


def _dob(rng: random.Random) -> str:
    return f"{rng.randint(1950, 2005)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def _password_habit(rng: random.Random) -> dict:
    """Thói quen tạo mật khẩu của một người: tiền tố cố định + khung cấu trúc."""
    return {
        "prefix": rng.choice(WORDS_UPPER) + rng.choice(["", "AI", "X", "Pro", "VN"]),
        "sep": rng.choice(SPECIALS),
        "tail_sep": rng.choice(SPECIALS + " "),
        "word": rng.choice(WORDS_LOWER).capitalize() if rng.random() < 0.6 else rng.choice(WORDS_LOWER),
    }


def _password(habit: dict, rng: random.Random) -> str:
    digits = str(rng.randint(1000, 2040)) if rng.random() < 0.7 else str(rng.randint(10, 99))
    tail = habit["tail_sep"].strip() + habit["word"] if habit["tail_sep"].strip() else ""
    return f"{habit['prefix']}{habit['sep']}{digits}{tail}"


def _style(rng: random.Random) -> dict:
    """Văn phong: tập từ yêu thích + độ dài câu + thói quen dấu câu."""
    return {
        "favorites": rng.sample(VOCAB, 10),
        "length": rng.randint(8, 22),
        "punct": rng.choice([".", "...", "!", ""]),
        "commas": rng.random() < 0.5,
    }


def _answer(style: dict, rng: random.Random, reuse: float) -> str:
    n = max(5, style["length"] + rng.randint(-3, 3))
    words = ["Tôi"]
    for _ in range(n):
        words.append(rng.choice(style["favorites"]) if rng.random() < reuse else rng.choice(VOCAB))
        if style["commas"] and rng.random() < 0.12:
            words[-1] += ","
    return " ".join(words) + style["punct"]


def _family_text(members: list[tuple[str, str]], rng: random.Random, k: int) -> str:
    chosen = rng.sample(members, k)
    parts = []
    for relation, name in chosen:
        if rng.random() < 0.3:  # gõ không dấu
            name = name.replace("ữ", "u").replace("ư", "u").replace("ơ", "o").replace("ô", "o").replace("ạ", "a")
        parts.append(f"{relation} {name}" if rng.random() < 0.7 else name)
    return ", ".join(parts)


def owner_base(rng: random.Random) -> dict:
    members = [(rng.choice(RELATIONS), _name(rng)) for _ in range(rng.randint(3, 6))]
    person = {
        "members": members,
        "dob": _dob(rng),
        "traits": rng.sample(TRAITS, 3),
        "habit": _password_habit(rng),
        "style": _style(rng),
        "device": (f"PC-{rng.randint(1000, 9999)}|Windows|AMD64", "Windows"),
        "google": f"user{rng.randint(1, 10**6)}@gmail.com" if rng.random() < 0.6 else "",
    }
    person["registration"] = {
        "owner_name": "Chủ nhân",
        "google": person["google"],
        "dob": person["dob"],
        "family": _family_text(members, rng, len(members)),
        "traits": person["traits"],
        "password": _password(person["habit"], rng),
        "answer": _answer(person["style"], rng, reuse=0.8),
    }
    return person


def owner_session(person: dict, rng: random.Random) -> tuple[dict, tuple[str, str]]:
    traits = list(person["traits"])
    if rng.random() < 0.4:
        traits[rng.randrange(len(traits))] = rng.choice(TRAITS)
    k = min(len(person["members"]), rng.randint(2, 4))
    data = {
        "google": person["google"] if rng.random() < 0.8 else "",
        "dob": person["dob"] if rng.random() < 0.97 else "",
        "family": _family_text(person["members"], rng, k),
        "traits": traits,
        # 15% số lần Chủ nhân phá thói quen, dùng một mật khẩu hoàn toàn khác
        "password": _password(person["habit"] if rng.random() < 0.85 else _password_habit(rng), rng),
        "answer": _answer(person["style"], rng, reuse=0.7),
    }
    device = person["device"] if rng.random() < 0.85 else (f"LAPTOP-{rng.randint(1, 999)}|Darwin|arm64", "Darwin")
    return data, device


def stranger(owner: dict, rng: random.Random) -> tuple[dict, tuple[str, str]]:
    other = owner_base(rng)
    data, _ = owner_session(other, rng)
    device = owner["device"] if rng.random() < 0.5 else other["device"]
    return data, device


def insider(owner: dict, rng: random.Random) -> tuple[dict, tuple[str, str]]:
    """Người nhà: biết ngày sinh + tên người thân, dùng chung máy, đoán cá tính."""
    other = owner_base(rng)
    k = min(len(owner["members"]), rng.randint(2, 4))
    data = {
        "google": "",
        "dob": owner["dob"],
        "family": _family_text(owner["members"], rng, k),
        "traits": rng.sample(TRAITS, 3),
        "password": _password(other["habit"], rng),
        "answer": _answer(other["style"], rng, reuse=0.7),
    }
    return data, owner["device"]
