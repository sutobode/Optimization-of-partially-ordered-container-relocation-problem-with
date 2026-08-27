"""Table 12: effect of the proportion of rolled containers.

``published`` uses the files released with the paper.  Only five instances per
subset were released for 20% RC, so that mode reports the available evidence
without silently replacing it. ``generated-paired`` is an explicitly labelled
extension using layouts derived from the same 0%-RC bases.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from pocrp_rc.core.validator import validate                            # noqa: E402
from pocrp_rc.data.loader import load_instance                          # noqa: E402
from pocrp_rc.heuristics.grasp import GraspConfig, grasp                # noqa: E402
from pocrp_rc.heuristics.greedy import GreedyConfig, construct          # noqa: E402

# Table 12 of the paper: C -> average relocations at 0/10/20/30 % RC
PAPER = {
    10: (2.78, 2.75, 3.23, 3.35), 16: (8.71, 8.41, 8.36, 8.24),
    19: (4.99, 5.93, 6.29, 6.76), 29: (9.55, 9.78, 10.83, 10.89),
    31: (19.35, 16.70, 16.38, 15.24), 46: (35.78, 31.00, 28.39, 25.45),
    50: (10.88, 12.78, 14.78, 15.59), 54: (24.54, 24.06, 22.28, 21.88),
    70: (20.20, 20.54, 22.24, 23.14), 79: (47.29, 42.95, 37.88, 36.16),
    94: (25.09, 26.25, 25.45, 28.75), 120: (54.51, 51.85, 47.56, 47.18),
    124: (42.75, 41.59, 41.60, 41.06), 150: (46.66, 46.39, 48.25, 48.95),
    170: (92.99, 83.59, 76.11, 72.68), 190: (72.61, 69.88, 68.18, 67.88),
    199: (87.36, 81.83, 79.28, 75.25), 274: (149.95, 136.53, 125.19, 117.64),
    290: (144.10, 133.05, 122.93, 117.51), 390: (228.05, 200.20, 184.26, 171.84),
}
ROOT00 = os.path.join("data_raw", "exrc", "不同比例RC数据集", "0%RC数据集")
ROOT10 = os.path.join("data_raw", "exrc", "不同比例RC数据集", "10%RC数据集")
ROOT30 = os.path.join("data_raw", "exrc", "不同比例RC数据集", "30%RC数据集")
ROOT20_RELEASED = os.path.join("data_raw", "ex195", "每组前五个（195个）")


def scale(C: int) -> str:
    return "small" if C <= 50 else ("medium" if C <= 150 else "large")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", default="grasp", choices=["grasp", "greedy"])
    ap.add_argument("--limit-per-subset", type=int, default=40)
    ap.add_argument("--max-c", type=int, default=10 ** 9)
    ap.add_argument("--dataset-mode", default="published",
                    choices=["published", "generated-paired"])
    args = ap.parse_args()

    if args.dataset_mode == "published":
        roots = {0: ROOT00, 10: ROOT10, 20: ROOT20_RELEASED, 30: ROOT30}
    else:
        roots = {0: ROOT00, 10: os.path.join("data_gen", "10pct"),
                 20: os.path.join("data_gen", "20pct"),
                 30: os.path.join("data_gen", "30pct")}
    per_c: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))

    for prop, root in roots.items():
        seen: dict[tuple, int] = defaultdict(int)
        t0 = time.time()
        for path in sorted(glob.glob(os.path.join(root, "*.pro"))):
            ins = load_instance(path)
            if ins.C > args.max_c:
                continue
            key = (ins.C, ins.S)
            if seen[key] >= args.limit_per_subset:
                continue
            seen[key] += 1
            if args.algo == "grasp":
                mv = grasp(ins, GraspConfig(), seed=hash(ins.name) & 0xFFFF)
            else:
                mv = construct(ins, GreedyConfig.profile("literal"))
            per_c[ins.C][prop].append(validate(ins, mv))
        print(f"  {prop:>3}% done in {time.time()-t0:>7.1f}s", flush=True)

    print(f"\ndataset mode: {args.dataset_mode}")
    print(f"{'C':>4} {'scale':>7} | " + " | ".join(
        f"{p:>3}% {'paper':>7}" for p in (0, 10, 20, 30)) + " | trend  paper-trend")
    tot = {p: 0.0 for p in (0, 10, 20, 30)}
    tot_paper = {p: 0.0 for p in (0, 10, 20, 30)}
    n = 0
    agree = 0
    for C in sorted(per_c):
        vals = {p: sum(v) / len(v) for p, v in per_c[C].items() if v}
        if len(vals) < 4:
            continue
        line = f"{C:>4} {scale(C):>7} |"
        seq = [vals[p] for p in (0, 10, 20, 30)]
        pseq = list(PAPER[C])
        for p, v, pv in zip((0, 10, 20, 30), seq, pseq):
            line += f" {v:>7.2f} {pv:>7.2f} |"
            tot[p] += v
            tot_paper[p] += pv
        t_mine = ("inc" if seq == sorted(seq) else
                  "dec" if seq == sorted(seq, reverse=True) else "mixed")
        t_paper = ("inc" if pseq == sorted(pseq) else
                   "dec" if pseq == sorted(pseq, reverse=True) else "mixed")
        agree += (t_mine == t_paper)
        n += 1
        print(line + f" {t_mine:>5}  {t_paper:>5}")
    print(f"{'Avg':>12} |" + "".join(
        f" {tot[p]/n:>7.2f} {tot_paper[p]/n:>7.2f} |" for p in (0, 10, 20, 30)))
    print(f"\ntrend agreement with the paper: {agree}/{n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
