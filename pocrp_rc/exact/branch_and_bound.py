"""Time-limited exact branch-and-bound for the restricted POCRP-RC.

This implements the iterative B&B *framework* described in Section 6.5.  The
paper says its implementation is similar to Tanaka and Voss (2019), but does
not publish node ordering or complete implementation details.  Consequently,
this module provides an auditable exact benchmark without claiming identical
runtime behavior to the authors' Java code.
"""
from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass

from ..core.bay import Bay
from ..core.instance import Instance, Move, n_relocations
from ..core.lower_bounds import lb_forced_plus_deadlock
from ..core.validator import validate
from ..heuristics.greedy import GreedyConfig, construct
from .brute_force import ExactSolver


@dataclass(frozen=True)
class BnBResult:
    status: str
    objective: int
    bound: int
    seconds: float
    nodes: int
    moves: list[Move]

    @property
    def gap(self) -> float:
        if self.objective == 0:
            return 0.0
        return max(0.0, (self.objective - self.bound) / self.objective)


def solve_branch_and_bound(
    ins: Instance,
    *,
    time_limit: float = 3600.0,
    max_nodes: int | None = None,
) -> BnBResult:
    """Solve using best-bound search with symmetry and dominance pruning."""
    if time_limit <= 0:
        raise ValueError("time_limit must be positive")
    start = time.perf_counter()
    root = Bay(ins)

    incumbent_moves = construct(ins, GreedyConfig.paper())
    incumbent = validate(ins, incumbent_moves)
    if root.done():
        return BnBResult("OPTIMAL", 0, 0, time.perf_counter() - start, 0, [])

    generator = ExactSolver(ins, max_nodes=2**63 - 1)
    serial = itertools.count()
    root_lb = lb_forced_plus_deadlock(root)
    # Entries: total lower bound, relocations so far, serial, bay, move prefix.
    queue: list[tuple[int, int, int, Bay, list[Move]]] = [
        (root_lb, 0, next(serial), root, [])
    ]
    best_g: dict[tuple, int] = {root.key(): 0}
    nodes = 0
    timed_out = False

    while queue:
        if time.perf_counter() - start >= time_limit:
            timed_out = True
            break
        lower, cost_so_far, _, bay, prefix = heapq.heappop(queue)
        if lower >= incumbent:
            continue
        if cost_so_far != best_g.get(bay.key()):
            continue
        nodes += 1
        if max_nodes is not None and nodes > max_nodes:
            timed_out = True
            break

        for period_cost, child, period_moves in generator._children(bay):
            child_cost = cost_so_far + period_cost
            if child_cost >= incumbent:
                continue
            child_prefix = prefix + period_moves
            if child.done():
                incumbent = child_cost
                incumbent_moves = child_prefix
                continue
            key = child.key()
            if child_cost >= best_g.get(key, 2**63 - 1):
                continue
            child_lb = child_cost + lb_forced_plus_deadlock(child)
            if child_lb >= incumbent:
                continue
            best_g[key] = child_cost
            heapq.heappush(queue, (
                child_lb, child_cost, next(serial), child, child_prefix))

    seconds = time.perf_counter() - start
    validate(ins, incumbent_moves)
    if not timed_out:
        return BnBResult(
            "OPTIMAL", incumbent, incumbent, seconds, nodes, incumbent_moves)

    active_bounds = [entry[0] for entry in queue
                     if entry[1] == best_g.get(entry[3].key())]
    bound = min([incumbent, *active_bounds]) if active_bounds else incumbent
    return BnBResult(
        "TIME_LIMIT", incumbent, bound, seconds, nodes, incumbent_moves)
