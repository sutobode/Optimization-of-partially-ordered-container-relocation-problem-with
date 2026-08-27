"""Second calibration round: which stacks may host an OC blocking container."""
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
PAPER_AVG = 54.22


def main() -> int:
    instances = [load_instance(p) for p in sorted(glob.glob(os.path.join(ROOT, "*.pro")))]
    by_subset: dict[tuple[int, int], list] = {}
    for ins in instances:
        by_subset.setdefault((ins.C, ins.S), []).append(ins)

    grid = list(itertools.product(
        ["oc_only", "has_rc", "include_rolled", "include_all"],   # oc_pool
        ["max_se", "best_fit"],                         # oc_rule
        ["first", "max_height"],                        # tie
    ))
    print(f"{'oc_pool':>15} {'oc_rule':>9} {'tie':>11} | {'avg':>7} {'delta':>7} | {'sec':>5}")
    results = []
    for oc_pool, oc_rule, tie in grid:
        cfg = GreedyConfig.setting("B", oc_pool=oc_pool, oc_rule=oc_rule, tie=tie)
        t0 = time.perf_counter()
        subset_avgs = []
        for key, group in by_subset.items():
            vals = [validate(ins, construct(ins, cfg)) for ins in group]
            subset_avgs.append(sum(vals) / len(vals))
        avg = sum(subset_avgs) / len(subset_avgs)
        results.append((abs(avg - PAPER_AVG), avg, oc_pool, oc_rule, tie))
        print(f"{oc_pool:>15} {oc_rule:>9} {tie:>11} | {avg:>7.2f} "
              f"{avg - PAPER_AVG:>+7.2f} | {time.perf_counter()-t0:>5.1f}")

    results.sort()
    print("\nbest three:")
    for d, avg, oc_pool, oc_rule, tie in results[:3]:
        print(f"  avg={avg:6.2f} delta={avg-PAPER_AVG:+.2f}  oc_pool={oc_pool} "
              f"oc_rule={oc_rule} tie={tie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
