"""Check 2: Greedy and Random on the 195 published 20 %-RC instances.

Compares against the per-subset averages of Table 5 (which were computed on 40
instances per subset, we only have the first 5 -- so a per-subset deviation is
expected; the aggregate gap is the meaningful figure).
"""
import glob
import os
import re
import sys
import time
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocrp_rc.core.bay import Bay                                      # noqa: E402
from pocrp_rc.core.instance import n_relocations                       # noqa: E402
from pocrp_rc.core.lower_bounds import lb_forced                       # noqa: E402
from pocrp_rc.core.validator import validate                           # noqa: E402
from pocrp_rc.data.loader import load_instance, parse_filename         # noqa: E402
from pocrp_rc.heuristics.greedy import GreedyConfig, construct         # noqa: E402
from pocrp_rc.heuristics.random_alg import random_solution             # noqa: E402

ROOT = os.path.join("data_raw", "ex195", "每组前五个（195个）")

# Table 5: (C, S) -> (Random relos, Greedy relos)
TABLE5 = {
    (10, 3): (7.53, 3.25), (16, 3): (22.65, 9.58), (16, 4): (15.05, 7.35),
    (19, 4): (22.95, 7.65), (19, 5): (17.18, 5.43), (29, 6): (37.55, 13.70),
    (29, 8): (26.65, 8.83), (31, 6): (45.05, 20.68), (31, 8): (30.10, 13.90),
    (46, 9): (66.20, 36.30), (46, 12): (45.90, 24.13), (50, 10): (68.45, 18.43),
    (50, 13): (50.10, 13.80), (54, 11): (72.08, 25.80), (54, 14): (53.98, 21.48),
    (70, 14): (96.98, 27.08), (70, 18): (70.20, 20.50), (79, 15): (112.58, 47.98),
    (79, 20): (78.88, 32.85), (94, 18): (128.80, 31.90), (94, 24): (93.13, 23.10),
    (120, 23): (168.70, 60.48), (120, 30): (123.33, 42.93),
    (124, 24): (176.58, 51.33), (124, 31): (126.50, 39.03),
    (150, 29): (206.13, 59.58), (150, 38): (151.38, 44.88),
    (170, 32): (245.03, 97.20), (170, 43): (172.23, 66.20),
    (190, 36): (275.05, 82.80), (190, 48): (196.35, 63.23),
    (199, 38): (286.55, 96.70), (199, 50): (203.60, 73.10),
    (274, 52): (392.53, 156.05), (274, 69): (278.55, 115.25),
    (290, 55): (417.28, 152.38), (290, 73): (299.60, 111.68),
    (390, 74): (561.60, 223.08), (390, 98): (402.88, 164.90),
}


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, "*.pro")))
    per_subset = defaultdict(lambda: {"rnd": [], "grd": [], "lb": [], "tg": [], "tr": []})
    infeasible = lb_violation = 0

    for path in files:
        ins = load_instance(path)
        meta = parse_filename(path)
        key = (ins.C, ins.S)

        t0 = time.perf_counter()
        rnd = random_solution(ins, seed=1000 + meta["id"])
        t_rnd = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        grd = construct(ins, GreedyConfig.setting("B"))
        t_grd = (time.perf_counter() - t0) * 1000

        try:
            nr = validate(ins, rnd)
            ng = validate(ins, grd)
        except Exception as exc:                       # pragma: no cover
            infeasible += 1
            print(f"INFEASIBLE {ins.name}: {exc}")
            continue
        assert nr == n_relocations(rnd) and ng == n_relocations(grd)
        lb = lb_forced(Bay(ins))
        if lb > ng or lb > nr:
            lb_violation += 1
            print(f"LB VIOLATION {ins.name}: lb={lb} greedy={ng} random={nr}")

        d = per_subset[key]
        d["rnd"].append(nr)
        d["grd"].append(ng)
        d["lb"].append(lb)
        d["tr"].append(t_rnd)
        d["tg"].append(t_grd)

    print(f"{'C':>4} {'S':>3} | {'Rnd':>7} {'paper':>7} | {'Grd':>7} {'paper':>7} "
          f"| {'LB':>6} | {'gap':>7} {'paper':>7} | {'ms':>8}")
    tot_r = tot_g = tot_lb = 0.0
    n_sub = 0
    for key in sorted(per_subset, key=lambda k: (k[0], k[1])):
        d = per_subset[key]
        r = sum(d["rnd"]) / len(d["rnd"])
        g = sum(d["grd"]) / len(d["grd"])
        lb = sum(d["lb"]) / len(d["lb"])
        gap = (g - r) / r * 100 if r else 0.0
        pr, pg = TABLE5[key]
        pgap = (pg - pr) / pr * 100
        tot_r += r
        tot_g += g
        tot_lb += lb
        n_sub += 1
        print(f"{key[0]:>4} {key[1]:>3} | {r:>7.2f} {pr:>7.2f} | {g:>7.2f} {pg:>7.2f} "
              f"| {lb:>6.2f} | {gap:>6.1f}% {pgap:>6.1f}% | {sum(d['tg'])/len(d['tg']):>8.1f}")
    print(f"{'Avg':>8} | {tot_r/n_sub:>7.2f} {149.89:>7.2f} | {tot_g/n_sub:>7.2f} "
          f"{54.22:>7.2f} | {tot_lb/n_sub:>6.2f} | "
          f"{(tot_g-tot_r)/tot_r*100:>6.1f}% {-63.8:>6.1f}% |")
    print(f"\ninfeasible solutions : {infeasible}")
    print(f"lower-bound violations: {lb_violation}")
    return 0 if (infeasible == 0 and lb_violation == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
