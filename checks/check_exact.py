"""Check 1: the exact solver reproduces the proven optima of Table 10."""
import glob
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.setrecursionlimit(100000)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocrp_rc.core.lower_bounds import lower_bound, lb_forced          # noqa: E402
from pocrp_rc.core.bay import Bay                                      # noqa: E402
from pocrp_rc.core.validator import validate                           # noqa: E402
from pocrp_rc.data.loader import load_instance                         # noqa: E402
from pocrp_rc.exact.brute_force import solve_exact                     # noqa: E402

# Table 10, instances ID 1..40 of subset 10x8x2x3x6x3 (RL model = proven optimum)
TABLE10 = [1, 3, 5, 2, 6, 3, 4, 5, 3, 5, 3, 3, 2, 4, 3, 5, 0, 3, 3, 3,
           5, 4, 2, 1, 1, 1, 2, 2, 4, 4, 2, 6, 1, 3, 2, 2, 2, 6, 4, 2]

ROOT = os.path.join("data_raw", "ex195", "每组前五个（195个）")


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, "Bay-3-6-3-10-8-2-*.pro")),
                   key=lambda p: int(re.search(r"-(\d+)\.pro", p).group(1)))
    print(f"{'instance':26s} {'opt':>4} {'paper':>6} {'valid':>6} {'LB1':>4} {'LB2':>4} "
          f"{'sec':>6}  status")
    ok = 0
    for path in files:
        idx = int(re.search(r"-(\d+)\.pro", path).group(1))
        ins = load_instance(path)
        t0 = time.time()
        val, moves = solve_exact(ins)
        dt = time.time() - t0
        nrel = validate(ins, moves)
        lb1 = lb_forced(Bay(ins))
        lb2 = lower_bound(ins)
        ref = TABLE10[idx]
        good = (val == ref) and (nrel == val) and (lb1 <= val) and (lb2 <= val)
        ok += good
        print(f"{os.path.basename(path):26s} {val:>4} {ref:>6} {nrel:>6} {lb1:>4} {lb2:>4} "
              f"{dt:>6.2f}  {'OK' if good else 'FAIL'}")
    print(f"\nmatched {ok}/{len(files)}")
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
