"""Reproduce the AL/RL model comparisons from Tables 4 and 10.

The paper uses a 3,600 s time limit per instance.  This runner defaults to RL
only because the optimized AL formulation is intentionally enormous and the
paper reports that it solves no benchmark instance within the limit.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from pocrp_rc.core.validator import validate                 # noqa: E402
from pocrp_rc.data.loader import load_instance, parse_filename # noqa: E402
from pocrp_rc.heuristics.grasp import GraspConfig, grasp      # noqa: E402
from pocrp_rc.heuristics.greedy import GreedyConfig, construct # noqa: E402
from pocrp_rc.models import al_model, rl_model                # noqa: E402


TABLE4_RL_SOLVED = {
    (10, 3): 40, (16, 3): 9, (16, 4): 11,
}


def _files(root: str) -> list[str]:
    return sorted(glob.glob(os.path.join(root, "**", "*.pro"), recursive=True))


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join("data_raw", "ex195"))
    ap.add_argument("--models", default="rl",
                    help="comma-separated: al,rl")
    ap.add_argument("--include-heuristics", action="store_true",
                    help="also compute Greedy and GRASP for Table 10 style rows")
    ap.add_argument("--time-limit", type=float, default=3600.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-c", type=int, default=10 ** 9)
    ap.add_argument("--limit-per-subset", type=int, default=10 ** 9)
    ap.add_argument("--al-max-constraints", type=int, default=2_000_000)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    models = [x.strip().lower() for x in args.models.split(",") if x.strip()]
    invalid = set(models) - {"al", "rl"}
    if invalid:
        raise SystemExit(f"unknown model(s): {sorted(invalid)}")

    rows = []
    grouped: dict[tuple[int, int], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list))
    solved: dict[tuple[int, int], dict[str, int]] = defaultdict(
        lambda: defaultdict(int))
    seen: dict[tuple[int, int], int] = defaultdict(int)

    for path in _files(args.root):
        ins = load_instance(path)
        if ins.C > args.max_c:
            continue
        key = (ins.C, ins.S)
        if seen[key] >= args.limit_per_subset:
            continue
        seen[key] += 1
        meta = parse_filename(path) or {}
        row: dict[str, object] = {
            "instance": ins.name,
            "id": meta.get("id"),
            "C": ins.C,
            "OC": ins.O,
            "RC": ins.n_rc,
            "S": ins.S,
            "T": ins.T,
            "G": ins.G,
        }

        for model_name in models:
            if model_name == "al":
                res = al_model.build_and_solve(
                    ins, time_limit=args.time_limit, workers=args.workers,
                    max_constraints=args.al_max_constraints)
            else:
                res = rl_model.build_and_solve(
                    ins, time_limit=args.time_limit, workers=args.workers)
            row[f"{model_name}_status"] = res.status
            row[f"{model_name}_seconds"] = res.seconds
            if res.objective is not None:
                row[f"{model_name}_relos"] = res.objective
                grouped[key][f"{model_name}_relos"].append(float(res.objective))
                grouped[key][f"{model_name}_seconds"].append(res.seconds)
                solved[key][model_name] += 1
                if res.moves is not None:
                    validate(ins, res.moves)

        if args.include_heuristics:
            t0 = time.perf_counter()
            gm = construct(ins, GreedyConfig.paper())
            row["greedy_relos"] = validate(ins, gm)
            row["greedy_seconds"] = time.perf_counter() - t0
            grouped[key]["greedy_relos"].append(float(row["greedy_relos"]))
            grouped[key]["greedy_seconds"].append(float(row["greedy_seconds"]))
            t0 = time.perf_counter()
            sm = grasp(ins, GraspConfig(), seed=1000 + int(meta.get("id", 0)))
            row["grasp_relos"] = validate(ins, sm)
            row["grasp_seconds"] = time.perf_counter() - t0
            grouped[key]["grasp_relos"].append(float(row["grasp_relos"]))
            grouped[key]["grasp_seconds"].append(float(row["grasp_seconds"]))

        rows.append(row)

    header = f"{'C':>4} {'OC':>4} {'RC':>4} {'S':>3} {'T':>3} {'G':>3} {'n':>3}"
    for model_name in models:
        header += f" | {model_name.upper():>2} num {'relos':>7} {'time(s)':>9}"
    if args.include_heuristics:
        header += f" | {'Greedy':>7} {'time(s)':>9} | {'GRASP':>7} {'time(s)':>9}"
    print(header)
    by_key = defaultdict(list)
    for row in rows:
        by_key[(row["C"], row["S"], row["T"], row["G"])].append(row)
    for key in sorted(by_key):
        subset_rows = by_key[key]
        sample = subset_rows[0]
        line = (f"{sample['C']:>4} {sample['OC']:>4} {sample['RC']:>4} "
                f"{sample['S']:>3} {sample['T']:>3} {sample['G']:>3} "
                f"{len(subset_rows):>3}")
        subset_key = (int(sample["C"]), int(sample["S"]))
        for model_name in models:
            nsol = solved[subset_key][model_name]
            relos = _mean(grouped[subset_key][f"{model_name}_relos"])
            secs = _mean(grouped[subset_key][f"{model_name}_seconds"])
            relos_txt = "-" if relos is None else f"{relos:.2f}"
            secs_txt = "-" if secs is None else f"{secs:.2f}"
            line += f" | {nsol:>6} {relos_txt:>7} {secs_txt:>9}"
        if args.include_heuristics:
            greedy = _mean(grouped[subset_key]["greedy_relos"])
            greedy_s = _mean(grouped[subset_key]["greedy_seconds"])
            grasp_v = _mean(grouped[subset_key]["grasp_relos"])
            grasp_s = _mean(grouped[subset_key]["grasp_seconds"])
            line += (f" | {greedy:>7.2f} {greedy_s:>9.2f}"
                     f" | {grasp_v:>7.2f} {grasp_s:>9.2f}")
        print(line)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
