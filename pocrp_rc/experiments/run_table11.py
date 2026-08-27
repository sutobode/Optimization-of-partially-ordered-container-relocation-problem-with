"""Run the Section 6.5 B&B/Greedy/GRASP comparison."""
from __future__ import annotations

import argparse
import glob
import os
import sys
from collections import defaultdict

from pocrp_rc.config import grasp_config_with_assumptions, load_config
from pocrp_rc.core.validator import validate
from pocrp_rc.data.loader import load_instance, parse_filename
from pocrp_rc.exact.branch_and_bound import solve_branch_and_bound
from pocrp_rc.heuristics.grasp import grasp
from pocrp_rc.heuristics.greedy import GreedyConfig, construct

sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.path.join("data_gen", "20pct"))
    parser.add_argument("--limit-per-subset", type=int, default=40)
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--max-c", type=int, default=10**9)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    grouped: dict[tuple[int, int], list[str]] = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(args.root, "*.pro"))):
        ins = load_instance(path)
        if ins.C <= args.max_c and len(grouped[(ins.C, ins.S)]) < args.limit_per_subset:
            grouped[(ins.C, ins.S)].append(path)

    print("dataset=" + args.root)
    print(f"{'C':>4} {'S':>3} {'n':>3} | {'B&B solved':>10} {'B&B relo':>9} "
          f"| {'Greedy':>8} {'GRASP':>8} {'gap':>8}")
    for key in sorted(grouped):
        bnb_values: list[int] = []
        greedy_values: list[int] = []
        grasp_values: list[int] = []
        for path in grouped[key]:
            ins = load_instance(path)
            meta = parse_filename(path) or {}
            bnb = solve_branch_and_bound(ins, time_limit=args.time_limit)
            if bnb.status == "OPTIMAL":
                bnb_values.append(bnb.objective)
            greedy_values.append(validate(ins, construct(ins, GreedyConfig.paper())))
            cfg = grasp_config_with_assumptions(load_config())
            grasp_values.append(validate(
                ins, grasp(ins, cfg, seed=args.seed + int(meta.get("id", 0)))))
        n = len(grouped[key])
        bavg = sum(bnb_values) / len(bnb_values) if bnb_values else float("nan")
        gavg = sum(greedy_values) / n
        gsavg = sum(grasp_values) / n
        gap = (gsavg - gavg) / gavg * 100 if gavg else 0.0
        print(f"{key[0]:>4} {key[1]:>3} {n:>3} | {len(bnb_values):>10} "
              f"{bavg:>9.2f} | {gavg:>8.2f} {gsavg:>8.2f} {gap:>+7.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
