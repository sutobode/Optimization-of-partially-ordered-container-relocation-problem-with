"""Command-line entry point for solving and validating POCRP-RC instances."""
from __future__ import annotations

import argparse
import json
import sys

from pocrp_rc.config import (grasp_config_from_paper,
                             grasp_config_with_assumptions, load_config,
                             paper_greedy_config)
from pocrp_rc.core.instance import n_relocations
from pocrp_rc.core.validator import validate
from pocrp_rc.data.loader import load_instance
from pocrp_rc.exact.brute_force import solve_exact
from pocrp_rc.exact.branch_and_bound import solve_branch_and_bound
from pocrp_rc.heuristics.grasp import grasp
from pocrp_rc.heuristics.greedy import construct
from pocrp_rc.heuristics.random_alg import random_solution
from pocrp_rc.models.al_model import build_and_solve as solve_al
from pocrp_rc.models.rl_model import build_and_solve as solve_rl


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve one POCRP-RC instance")
    parser.add_argument("instance")
    parser.add_argument(
        "--algorithm", default="greedy",
        choices=["random", "greedy", "grasp", "exact", "bnb", "al", "rl"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--max-nodes", type=int, default=4_000_000)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict-paper", action="store_true",
        help="for GRASP, refuse unpublished parameter assumptions")
    args = parser.parse_args()
    ins = load_instance(args.instance)
    config = load_config(args.config)

    if args.algorithm == "random":
        moves = random_solution(ins, seed=args.seed)
        payload = {"algorithm": "random", "objective": validate(ins, moves)}
    elif args.algorithm == "greedy":
        moves = construct(ins, paper_greedy_config(config))
        payload = {"algorithm": "greedy", "objective": validate(ins, moves)}
    elif args.algorithm == "grasp":
        try:
            cfg = (grasp_config_from_paper(config) if args.strict_paper
                   else grasp_config_with_assumptions(config))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        moves = grasp(ins, cfg, seed=args.seed)
        payload = {"algorithm": "grasp", "objective": validate(ins, moves)}
    elif args.algorithm == "exact":
        objective, moves = solve_exact(ins, max_nodes=args.max_nodes)
        validate(ins, moves)
        payload = {"algorithm": "exact", "objective": objective}
    elif args.algorithm == "bnb":
        result = solve_branch_and_bound(
            ins, time_limit=args.time_limit, max_nodes=args.max_nodes)
        moves = result.moves
        validate(ins, moves)
        payload = {
            "algorithm": "bnb", "status": result.status,
            "objective": result.objective, "bound": result.bound,
            "gap": result.gap, "seconds": result.seconds,
            "nodes": result.nodes,
        }
    else:
        result = (solve_al if args.algorithm == "al" else solve_rl)(
            ins, time_limit=args.time_limit)
        payload = {
            "algorithm": args.algorithm, "status": result.status,
            "objective": result.objective, "bound": result.bound,
            "seconds": result.seconds,
        }
        if result.moves is not None:
            validate(ins, result.moves)
            payload["relocations"] = n_relocations(result.moves)
            payload["move_count"] = len(result.moves)
    payload["instance"] = ins.name
    if "moves" in locals():
        payload["relocations"] = n_relocations(moves)
        payload["move_count"] = len(moves)
    print(json.dumps(payload, indent=2) if args.json else " ".join(
        f"{key}={value}" for key, value in payload.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
