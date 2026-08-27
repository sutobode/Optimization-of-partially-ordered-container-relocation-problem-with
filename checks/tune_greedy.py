"""Calibrate the ambiguous parts of the Greedy description against Table 5.

Every switch below corresponds to a place where the published description of
TR / RR admits more than one reading (see docs/ERRATA.md).  The variant whose
average number of relocations is closest to the paper's 54.22 is adopted.
"""
import glob
import itertools
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocrp_rc.core.validator import validate                           # noqa: E402
from pocrp_rc.data.loader import load_instance                         # noqa: E402
from pocrp_rc.heuristics.greedy import GreedyConfig, construct         # noqa: E402

ROOT = os.path.join("data_raw", "ex195", "每组前五个（195个）")
PAPER_AVG = 54.22          # Table 5, average over the 39 subsets


def main() -> int:
    instances = [load_instance(p) for p in sorted(glob.glob(os.path.join(ROOT, "*.pro")))]
    by_subset: dict[tuple[int, int], list] = {}
    for ins in instances:
        by_subset.setdefault((ins.C, ins.S), []).append(ins)

    grid = list(itertools.product(
        ["bad"],                                            # rc_mode (best)
        ["rolled"],                                         # rc_prefer
        ["first", "max_height"],                            # tie
        ["B"],                                              # deadlock setting
        ["max_se", "best_fit", "min_se"],                   # oc_rule
        ["paper", "min_total", "max_bc"],                   # tr_rule
    ))
    print(f"{'rc_mode':>8} {'rc_pref':>8} {'tie':>11} {'set':>4} {'oc_rule':>9} "
          f"{'tr_rule':>10} | {'avg':>7} {'delta':>7} | {'sec':>5}")
    results = []
    for rc_mode, rc_prefer, tie, setting, oc_rule, tr_rule in grid:
        cfg = GreedyConfig.setting(setting, rc_mode=rc_mode, rc_prefer=rc_prefer,
                                   tie=tie, oc_rule=oc_rule, tr_rule=tr_rule)
        t0 = time.perf_counter()
        subset_avgs = []
        for key, group in by_subset.items():
            vals = []
            for ins in group:
                mv = construct(ins, cfg)
                vals.append(validate(ins, mv))
            subset_avgs.append(sum(vals) / len(vals))
        avg = sum(subset_avgs) / len(subset_avgs)
        dt = time.perf_counter() - t0
        results.append((abs(avg - PAPER_AVG), avg, rc_mode, rc_prefer, tie, setting,
                        oc_rule, tr_rule))
        print(f"{rc_mode:>8} {rc_prefer:>8} {tie:>11} {setting:>4} {oc_rule:>9} "
              f"{tr_rule:>10} | {avg:>7.2f} {avg - PAPER_AVG:>+7.2f} | {dt:>5.1f}")

    results.sort()
    print("\nbest five variants (closest to the paper's 54.22):")
    for d, avg, rc_mode, rc_prefer, tie, setting, oc_rule, tr_rule in results[:5]:
        print(f"  avg={avg:6.2f}  delta={avg - PAPER_AVG:+.2f}  rc_mode={rc_mode} "
              f"rc_prefer={rc_prefer} tie={tie} setting={setting} "
              f"oc_rule={oc_rule} tr_rule={tr_rule}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
