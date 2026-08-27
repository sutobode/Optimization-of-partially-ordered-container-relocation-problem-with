"""Check 3: the generator reproduces the published 20 %-RC instances.

For every one of the 195 published 20 %-RC instances there must be a 0 %-RC
instance of the same subset from which it is obtained by the documented
procedure (mark ``ceil(0.2*C)`` positions as RC, renumber priorities).
"""
import glob
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocrp_rc.data.generator import derives_from, n_rolled              # noqa: E402
from pocrp_rc.data.loader import load_instance                          # noqa: E402

ROOT20 = os.path.join("data_raw", "ex195", "每组前五个（195个）")
ROOT00 = os.path.join("data_raw", "exrc", "不同比例RC数据集", "0%RC数据集")
ROOT10 = os.path.join("data_raw", "exrc", "不同比例RC数据集", "10%RC数据集")
ROOT30 = os.path.join("data_raw", "exrc", "不同比例RC数据集", "30%RC数据集")


def main() -> int:
    zero = defaultdict(list)
    for p in sorted(glob.glob(os.path.join(ROOT00, "*.pro"))):
        ins = load_instance(p)
        zero[(ins.C, ins.S, ins.T)].append(ins)

    print("A. ceil(p*C) rule")
    bad_rule = 0
    for prop, root in ((0.1, ROOT10), (0.2, ROOT20), (0.3, ROOT30)):
        seen = set()
        for p in glob.glob(os.path.join(root, "*.pro")):
            ins = load_instance(p)
            if ins.n_rc != n_rolled(ins.C, prop):
                bad_rule += 1
            seen.add(ins.C)
        print(f"   {int(prop*100):>3}% : {len(seen)} distinct C, violations={bad_rule}")

    print("\nB. derivability of the published 20 %-RC instances")
    total = ok = 0
    per_c = defaultdict(int)
    for p in sorted(glob.glob(os.path.join(ROOT20, "*.pro"))):
        target = load_instance(p)
        total += 1
        pool = zero[(target.C, target.S, target.T)]
        if any(derives_from(target, base) for base in pool):
            ok += 1
            per_c[target.C] += 1
    print(f"   derivable {ok}/{total}")
    if ok != total:
        print("   per C:", dict(sorted(per_c.items())))
    return 0 if (ok == total and bad_rule == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
