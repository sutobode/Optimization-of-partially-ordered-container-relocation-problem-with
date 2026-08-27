"""Reproduce the controlled GRASP studies of Tables 6--9."""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from collections import defaultdict

from pocrp_rc.config import grasp_config_with_assumptions, load_config
from pocrp_rc.core.validator import validate
from pocrp_rc.data.loader import load_instance, parse_filename
from pocrp_rc.heuristics.grasp import grasp
from pocrp_rc.heuristics.greedy import GreedyConfig

sys.stdout.reconfigure(encoding="utf-8")


ROOT195 = os.path.join("data_raw", "ex195", "每组前五个（195个）")


def _instances(root: str, max_per_subset: int):
    seen: dict[tuple[int, int], int] = defaultdict(int)
    for path in sorted(glob.glob(os.path.join(root, "*.pro"))):
        ins = load_instance(path)
        key = (ins.C, ins.S)
        if seen[key] >= max_per_subset:
            continue
        seen[key] += 1
        yield path, ins


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT195)
    parser.add_argument("--study", required=True,
                        choices=["settings", "max_iteration", "hood_num", "noimpr"])
    parser.add_argument("--limit-per-subset", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    if args.study == "settings":
        variants = [(name, name) for name in "ABC"]
    elif args.study == "max_iteration":
        variants = [(str(v), v) for v in (1, 10, 50, 100, 200)]
    elif args.study == "hood_num":
        variants = [(str(v), v) for v in (1, 5, 10, 20, 30)]
    else:
        variants = [(str(v), v) for v in (1, 3, 5)]

    print(f"study={args.study} instances-per-subset={args.limit_per_subset}")
    print(f"{'value':>8} {'instances':>9} {'relos':>10} {'time_ms':>12}")
    for label, value in variants:
        cfg = grasp_config_with_assumptions(load_config())
        if args.study == "settings":
            cfg.greedy = GreedyConfig.setting(value, oc_pool="has_rc")
        elif args.study == "max_iteration":
            cfg.max_iteration, cfg.hood_num, cfg.noimpr_limit = value, 1, 3
        elif args.study == "hood_num":
            cfg.max_iteration, cfg.hood_num, cfg.noimpr_limit = 10, value, 3
        else:
            cfg.max_iteration, cfg.hood_num, cfg.noimpr_limit = 10, 10, value
        relos: list[int] = []
        elapsed: list[float] = []
        for path, ins in _instances(args.root, args.limit_per_subset):
            meta = parse_filename(path) or {}
            start = time.perf_counter()
            moves = grasp(ins, cfg, seed=args.seed + int(meta.get("id", 0)))
            elapsed.append((time.perf_counter() - start) * 1000.0)
            relos.append(validate(ins, moves))
        print(f"{label:>8} {len(relos):>9} {sum(relos)/len(relos):>10.2f} "
              f"{sum(elapsed)/len(elapsed):>12.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
