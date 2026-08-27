"""Check 4: the RL model reproduces the optima of Table 10 / the exact solver."""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.setrecursionlimit(100000)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocrp_rc.data.loader import load_instance                          # noqa: E402
from pocrp_rc.exact.brute_force import optimum                          # noqa: E402
from pocrp_rc.models.rl_model import build_and_solve                    # noqa: E402

TABLE10 = [1, 3, 5, 2, 6]
ROOT = os.path.join("data_raw", "ex195", "每组前五个（195个）")


def main() -> int:
    limit = float(os.environ.get("IP_TIME_LIMIT", "600"))
    files = sorted(glob.glob(os.path.join(ROOT, "Bay-3-6-3-10-8-2-*.pro")),
                   key=lambda p: int(re.search(r"-(\d+)\.pro", p).group(1)))
    print(f"{'instance':26s} {'RL':>4} {'exact':>6} {'paper':>6} {'status':>10} {'sec':>7}  st")
    ok = 0
    for path in files:
        idx = int(re.search(r"-(\d+)\.pro", path).group(1))
        ins = load_instance(path)
        exact = optimum(ins)
        res = build_and_solve(ins, time_limit=limit)
        ref = TABLE10[idx]
        good = res.objective == exact == ref
        ok += good
        print(f"{os.path.basename(path):26s} {str(res.objective):>4} {exact:>6} {ref:>6} "
              f"{res.status:>10} {res.seconds:>7.1f}  {'OK' if good else 'FAIL'}")
    print(f"\nmatched {ok}/{len(files)}")
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
