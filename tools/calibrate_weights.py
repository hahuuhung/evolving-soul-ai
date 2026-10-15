"""
Công cụ hiệu chỉnh trọng số 5 trụ cột & ngưỡng nhận diện trên dữ liệu giả lập.

Chạy:  python tools/calibrate_weights.py [--owners 300]
Tìm tổ hợp trọng số có FRR thấp nhất với ràng buộc FAR người lạ ≤ 1% và FAR người nhà ≤ 3%
trên tập huấn luyện, rồi báo cáo trên tập kiểm tra độc lập (seed khác).

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import argparse
import itertools
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evolving_soul.config import Settings  # noqa: E402
from evolving_soul.crypto import SoulCipher, new_master_key  # noqa: E402
from evolving_soul.features import observe  # noqa: E402
from evolving_soul.scoring import PILLARS, build_model, compare  # noqa: E402
from tests import synthetic  # noqa: E402

GRID = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
KINDS = (("owner", synthetic.owner_session, 3), ("stranger", synthetic.stranger, 3), ("insider", synthetic.insider, 2))


def collect(seed: int, owners: int) -> dict:
    settings, cipher, rng = Settings(), SoulCipher(new_master_key()), random.Random(seed)
    out = {kind: [] for kind, _, _ in KINDS}
    for _ in range(owners):
        person = synthetic.owner_base(rng)
        model = build_model(observe(person["registration"], cipher, person["device"]))
        for kind, make, n in KINDS:
            for _ in range(n):
                data, device = make(person, rng)
                r = compare(observe(data, cipher, device), model, settings)
                out[kind].append(([r["pillars"][p] for p in PILLARS], r["gate_passed"]))
    return out


def rates(samples: dict, weights: tuple, threshold: float) -> tuple[float, float, float]:
    def accepted(pillars, gate):
        present = [(weights[i], v) for i, v in enumerate(pillars) if v is not None]
        trust = sum(w * v for w, v in present) / sum(w for w, _ in present)
        return gate and trust >= threshold

    return (
        float(np.mean([not accepted(*s) for s in samples["owner"]])),
        float(np.mean([accepted(*s) for s in samples["stranger"]])),
        float(np.mean([accepted(*s) for s in samples["insider"]])),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--owners", type=int, default=300)
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    train, test = collect(1, args.owners), collect(2, args.owners)
    candidates = []
    for weights in itertools.product(GRID, repeat=len(PILLARS)):
        if abs(sum(weights) - 1.0) > 1e-9:
            continue
        for threshold in np.arange(0.55, 0.80, 0.01):
            frr, far_s, far_i = rates(train, weights, threshold)
            if far_s <= 0.01 and far_i <= 0.03:
                candidates.append((frr, far_i, weights, round(float(threshold), 2)))
    candidates.sort()

    for frr, far_i, weights, threshold in candidates[: args.top]:
        t_frr, t_far_s, t_far_i = rates(test, weights, threshold)
        print(f"{dict(zip(PILLARS, weights))} ngưỡng={threshold} | train FRR={frr:.3f} FAR_nhà={far_i:.3f}"
              f" | test FRR={t_frr:.3f} FAR_lạ={t_far_s:.3f} FAR_nhà={t_far_i:.3f}")


if __name__ == "__main__":
    main()
