"""One-factor sensitivity analysis for unpublished GRASP parameters."""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

from pocrp_rc.config import grasp_config_with_assumptions, load_config
from pocrp_rc.core.validator import validate
from pocrp_rc.data.loader import load_instance, parse_filename
from pocrp_rc.heuristics.grasp import grasp

sys.stdout.reconfigure(encoding="utf-8")


PARAMETERS = {
    "ma": int, "mb": int, "mc": int, "initfit": float, "alpha": float,
    "initial_temp": float, "final_temp": float, "beta": float, "k": float,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.path.join(
        "data_raw", "ex195", "每组前五个（195个）"))
    parser.add_argument("--parameter", required=True, choices=sorted(PARAMETERS))
    parser.add_argument("--values", required=True,
                        help="comma-separated values, e.g. 1.2,1.5,2.0")
    parser.add_argument("--limit", type=int, default=195)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    cast = PARAMETERS[args.parameter]
    values = [cast(value.strip()) for value in args.values.split(",")]
    files = sorted(glob.glob(os.path.join(args.root, "*.pro")))[:args.limit]
    if not files:
        raise SystemExit(f"no .pro instances under {args.root}")

    print(f"parameter={args.parameter} dataset={args.root} n={len(files)}")
    print(f"{'value':>12} {'relos':>10} {'time_ms':>12}")
    for value in values:
        cfg = grasp_config_with_assumptions(load_config())
        setattr(cfg, args.parameter, value)
        relos: list[int] = []
        elapsed: list[float] = []
        for path in files:
            ins = load_instance(path)
            meta = parse_filename(path) or {}
            start = time.perf_counter()
            moves = grasp(ins, cfg, seed=args.seed + int(meta.get("id", 0)))
            elapsed.append((time.perf_counter() - start) * 1000.0)
            relos.append(validate(ins, moves))
        print(f"{str(value):>12} {sum(relos)/len(relos):>10.2f} "
              f"{sum(elapsed)/len(elapsed):>12.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
