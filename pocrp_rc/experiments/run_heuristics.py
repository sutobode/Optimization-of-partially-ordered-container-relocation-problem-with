"""Compare Random / Greedy / GRASP against the paper's tables.

Usage::

    python -m pocrp_rc.experiments.run_heuristics --root data_gen/20pct
    python -m pocrp_rc.experiments.run_heuristics --root data_raw/... --algos random,greedy
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from pocrp_rc.core.bay import Bay                                       # noqa: E402
from pocrp_rc.core.lower_bounds import lb_forced                        # noqa: E402
from pocrp_rc.core.validator import validate                            # noqa: E402
from pocrp_rc.data.loader import load_instance, parse_filename          # noqa: E402
from pocrp_rc.evaluation.statistics import paired_significance          # noqa: E402
from pocrp_rc.heuristics.greedy import GreedyConfig, construct          # noqa: E402
from pocrp_rc.heuristics.random_alg import random_solution              # noqa: E402

# Table 5 / Table 11: (C, S) -> (Random, Greedy, GRASP)
PAPER = {
    (10, 3): (7.53, 3.25, 3.23), (16, 3): (22.65, 9.58, 9.48),
    (16, 4): (15.05, 7.35, 7.25), (19, 4): (22.95, 7.65, 7.30),
    (19, 5): (17.18, 5.43, 5.28), (29, 6): (37.55, 13.70, 13.05),
    (29, 8): (26.65, 8.83, 8.60), (31, 6): (45.05, 20.68, 19.40),
    (31, 8): (30.10, 13.90, 13.35), (46, 9): (66.20, 36.30, 34.10),
    (46, 12): (45.90, 24.13, 22.68), (50, 10): (68.45, 18.43, 16.68),
    (50, 13): (50.10, 13.80, 12.88), (54, 11): (72.08, 25.80, 24.10),
    (54, 14): (53.98, 21.48, 20.45), (70, 14): (96.98, 27.08, 25.15),
    (70, 18): (70.20, 20.50, 19.33), (79, 15): (112.58, 47.98, 44.68),
    (79, 20): (78.88, 32.85, 31.08), (94, 18): (128.80, 31.90, 29.38),
    (94, 24): (93.13, 23.10, 21.53), (120, 23): (168.70, 60.48, 55.03),
    (120, 30): (123.33, 42.93, 40.10), (124, 24): (176.58, 51.33, 46.78),
    (124, 31): (126.50, 39.03, 36.43), (150, 29): (206.13, 59.58, 54.73),
    (150, 38): (151.38, 44.88, 41.78), (170, 32): (245.03, 97.20, 89.75),
    (170, 43): (172.23, 66.20, 62.48), (190, 36): (275.05, 82.80, 78.08),
    (190, 48): (196.35, 63.23, 58.28), (199, 38): (286.55, 96.70, 90.80),
    (199, 50): (203.60, 73.10, 67.75), (274, 52): (392.53, 156.05, 143.78),
    (274, 69): (278.55, 115.25, 106.60), (290, 55): (417.28, 152.38, 140.10),
    (290, 73): (299.60, 111.68, 105.75), (390, 74): (561.60, 223.08, 210.63),
    (390, 98): (402.88, 164.90, 157.90),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join("data_gen", "20pct"))
    ap.add_argument("--algos", default="random,greedy")
    ap.add_argument("--max-c", type=int, default=10 ** 9)
    ap.add_argument("--limit-per-subset", type=int, default=10 ** 9)
    ap.add_argument("--setting", default="paper",
                    choices=["paper", "A", "B", "C"],
                    help="Greedy configuration; 'paper' follows Algorithm 1")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--grasp-iterations", type=int, default=10)
    ap.add_argument("--grasp-hood", type=int, default=10)
    args = ap.parse_args()
    algos = [a.strip() for a in args.algos.split(",") if a.strip()]

    grasp_fn = None
    if "grasp" in algos:
        from pocrp_rc.heuristics.grasp import GraspConfig, grasp        # noqa: E402
        gcfg = GraspConfig(max_iteration=args.grasp_iterations,
                           hood_num=args.grasp_hood)
        grasp_fn = (grasp, gcfg)

    files = sorted(glob.glob(os.path.join(args.root, "*.pro")))
    per_subset: dict[tuple[int, int], dict[str, list]] = defaultdict(
        lambda: defaultdict(list))
    seen = defaultdict(int)
    problems = 0

    for path in files:
        meta = parse_filename(path) or {}
        ins = load_instance(path)
        if ins.C > args.max_c:
            continue
        key = (ins.C, ins.S)
        if seen[key] >= args.limit_per_subset:
            continue
        seen[key] += 1
        d = per_subset[key]
        d["lb"].append(lb_forced(Bay(ins)))

        for algo in algos:
            t0 = time.perf_counter()
            if algo == "random":
                mv = random_solution(ins, seed=1000 + meta.get("id", 0))
            elif algo == "greedy":
                cfg = (GreedyConfig.paper() if args.setting == "paper"
                       else GreedyConfig.setting(args.setting))
                mv = construct(ins, cfg)
            elif algo == "grasp":
                fn, cfg = grasp_fn
                mv = fn(ins, cfg, seed=1000 + meta.get("id", 0))
            else:
                raise SystemExit(f"unknown algorithm {algo}")
            dt = (time.perf_counter() - t0) * 1000
            try:
                n = validate(ins, mv)
            except Exception as exc:
                problems += 1
                print(f"INFEASIBLE {algo} {ins.name}: {exc}")
                continue
            d[algo].append(n)
            d[algo + "_ms"].append(dt)

    # ------------------------------------------------------------------ #
    head = f"{'C':>4} {'S':>3} {'n':>3} {'LB':>6}"
    for a in algos:
        head += f" | {a[:6]:>7} {'paper':>7} {'dev':>7} {'ms':>8}"
    print(head)
    col = {"random": 0, "greedy": 1, "grasp": 2}
    totals = {a: 0.0 for a in algos}
    totals_paper = {a: 0.0 for a in algos}
    tot_lb = 0.0
    n_sub = 0
    rows = []
    for key in sorted(per_subset, key=lambda k: (k[0], k[1])):
        d = per_subset[key]
        line = (f"{key[0]:>4} {key[1]:>3} {len(d['lb']):>3} "
                f"{sum(d['lb'])/len(d['lb']):>6.2f}")
        row = {"C": key[0], "S": key[1], "n": len(d["lb"]),
               "lb": sum(d["lb"]) / len(d["lb"])}
        for a in algos:
            if not d[a]:
                line += f" | {'-':>7} {'-':>7} {'-':>7} {'-':>8}"
                continue
            v = sum(d[a]) / len(d[a])
            p = PAPER[key][col[a]]
            ms = sum(d[a + "_ms"]) / len(d[a + "_ms"])
            totals[a] += v
            totals_paper[a] += p
            line += f" | {v:>7.2f} {p:>7.2f} {(v-p)/p*100:>+6.1f}% {ms:>8.1f}"
            row[a] = v
            row[a + "_paper"] = p
            row[a + "_ms"] = ms
        tot_lb += row["lb"]
        n_sub += 1
        rows.append(row)
        print(line)

    line = f"{'Avg':>8} {n_sub:>3} {tot_lb/n_sub:>6.2f}"
    for a in algos:
        v = totals[a] / n_sub
        p = totals_paper[a] / n_sub
        line += f" | {v:>7.2f} {p:>7.2f} {(v-p)/p*100:>+6.1f}% {'':>8}"
    print(line)

    if "random" in algos and "greedy" in algos:
        gr = totals["greedy"] / n_sub
        rn = totals["random"] / n_sub
        print(f"\nGreedy vs Random gap: {(gr-rn)/rn*100:+.1f}%   (paper -63.8%)")
    if "greedy" in algos and "grasp" in algos:
        gr = totals["greedy"] / n_sub
        gs = totals["grasp"] / n_sub
        print(f"GRASP vs Greedy gap : {(gs-gr)/gr*100:+.1f}%   (paper  -6.0%)")
    pairs = (("random", "greedy"), ("greedy", "grasp"))
    for left, right in pairs:
        if left not in algos or right not in algos:
            continue
        print(f"\nPaired significance: {left} vs {right}")
        for key in sorted(per_subset, key=lambda k: (k[0], k[1])):
            d = per_subset[key]
            if len(d[left]) != len(d[right]) or len(d[left]) < 3:
                print(f"  C={key[0]:>3} S={key[1]:>3}: insufficient paired data")
                continue
            result = paired_significance(d[left], d[right])
            print(f"  C={key[0]:>3} S={key[1]:>3}: {result.test:<21} "
                  f"p={result.p_value:.4g}{result.marker}")
    print(f"infeasible solutions: {problems}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)
        print(f"wrote {args.json_out}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
