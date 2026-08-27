"""Regenerate the 20 %-RC dataset that the paper used but did not publish.

The repository of Wang et al. (2026) contains the full 1560-instance sets for
0 %, 10 % and 30 % RC but only the first five instances of each subset for
20 % RC -- which is precisely the proportion used in Sections 6.1-6.5.  This
script rebuilds a statistically equivalent full set from the 0 % instances with
the procedure validated by ``checks/check_generator.py``.
"""
import argparse
import glob
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from pocrp_rc.data.generator import mark_rolled                        # noqa: E402
from pocrp_rc.data.loader import load_instance, write_instance         # noqa: E402

ROOT00 = os.path.join("data_raw", "exrc", "不同比例RC数据集", "0%RC数据集")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proportion", type=float, default=0.2)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=20260827)
    args = ap.parse_args()
    out = args.out or os.path.join("data_gen", f"{int(args.proportion*100)}pct")

    files = sorted(glob.glob(os.path.join(ROOT00, "*.pro")))
    if not files:
        print(f"no source instances in {ROOT00}")
        return 1
    n = 0
    for path in files:
        base = load_instance(path)
        rng = random.Random(f"{args.seed}:{base.name}")
        ins = mark_rolled(base, args.proportion, rng)
        write_instance(ins, os.path.join(out, ins.name + ".pro"))
        n += 1
    print(f"wrote {n} instances with {int(args.proportion*100)}% RC to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
