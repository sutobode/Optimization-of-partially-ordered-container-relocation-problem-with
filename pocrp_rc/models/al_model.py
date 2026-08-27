"""Absolute-Location (AL) integer programme of Sections 4.2 / 4.3, on CP-SAT.

Variables

    x[s][t][c][n] = 1  iff container c occupies slot (s, t) before the n-th
                       retrieval,  n = 1..N+1
    r[n][s]            number of relocations in stack s during period n

The optimised formulation of Section 4.3 is used: constraints (13)+(14) are
merged into (20) and (16)-(18) are replaced by (21)-(22).

Constraint (15) is printed with an unbound index ``m`` (``sum_{z=m+1}``
appears inside ``sum_{m=t+1}``); it is reconstructed with explicit tiers
``t < td < te`` which is the only reading matching its stated LIFO purpose.

The model is included for completeness -- as the paper reports, it does not
solve any instance of the benchmark.  ``estimate_size`` lets callers refuse to
build it when the constraint count explodes.
"""
from __future__ import annotations

import time
from typing import Optional

from ortools.sat.python import cp_model

from ..core.bay import Bay
from ..core.instance import Instance, Move, RELOCATE, RETRIEVE
from ..core.validator import validate
from .rl_model import IPResult


def estimate_size(ins: Instance) -> dict[str, int]:
    C, S, T, N = ins.C, ins.S, ins.T, ins.O
    n_var = S * T * C * (N + 1)
    trip = max(0, T * (T - 1) * (T - 2) // 6)          # t < td < te
    pair = T * (T - 1) // 2                            # v < w
    c15 = S * trip * max(S - 1, 0) * pair * C * max(C - 1, 0) * max(C - 2, 0)
    c20 = C * max(C - 1, 0) * S * T * N * S * T
    return {"variables": n_var, "constraints_15": c15, "constraints_20": c20,
            "total_estimate": c15 + c20}


def _decode_moves(ins: Instance, solver: cp_model.CpSolver, x: dict) -> list[Move]:
    """Decode absolute period layouts into a validated move sequence."""
    bay = Bay(ins)
    moves: list[Move] = []

    def location(n: int, c: int) -> tuple[int, int] | None:
        hits = [(s, t) for s in range(ins.S) for t in range(ins.T)
                if solver.Value(x[(s, t, c, n)])]
        if len(hits) > 1:
            raise ValueError(f"period {n}: duplicate location for container {c}")
        return hits[0] if hits else None

    for n in range(1, ins.O + 1):
        targets = [c for c in range(ins.O)
                   if location(n, c) is not None and location(n + 1, c) is None]
        if len(targets) != 1:
            raise ValueError(f"period {n}: expected one target, found {targets}")
        target = targets[0]
        src = bay.where(target)
        for blocker in reversed(bay.blockers_above(target)):
            loc = location(n + 1, blocker)
            if loc is None:
                raise ValueError(f"period {n}: blocker {blocker} disappeared")
            dst = loc[0]
            moves.append(Move(RELOCATE, blocker, src, dst, target))
            bay.relocate(blocker, dst)
        moves.append(Move(RETRIEVE, target, src, None, target))
        bay.retrieve(target)
    validate(ins, moves)
    return moves


def build_and_solve(ins: Instance, time_limit: float = 3600.0,
                    workers: int = 8, max_constraints: int = 2_000_000,
                    log: bool = False) -> IPResult:
    C, S, T, O = ins.C, ins.S, ins.T, ins.O
    N = O
    size = estimate_size(ins)
    if size["total_estimate"] > max_constraints:
        return IPResult(f"SKIPPED_TOO_LARGE({size['total_estimate']:,})",
                        None, None, 0.0)

    m = cp_model.CpModel()
    x = {(s, t, c, n): m.NewBoolVar(f"x_{s}_{t}_{c}_{n}")
         for s in range(S) for t in range(T) for c in range(C)
         for n in range(1, N + 2)}
    r = {(n, s): m.NewIntVar(0, T, f"r_{n}_{s}")
         for n in range(1, N + 1) for s in range(S)}
    M = T + 1

    def inbay(c, n):
        return sum(x[(s, t, c, n)] for s in range(S) for t in range(T))

    # ---- (1) objective ------------------------------------------------------
    m.Minimize(sum(r.values()))

    # ---- (2) initial layout -------------------------------------------------
    init = {(s, t): c for s, st in enumerate(ins.layout) for t, c in enumerate(st)}
    for s in range(S):
        for t in range(T):
            for c in range(C):
                m.Add(x[(s, t, c, 1)] == (1 if init.get((s, t)) == c else 0))

    # ---- (3)/(4) final layout ----------------------------------------------
    for c in range(C):
        m.Add(inbay(c, N + 1) == (0 if c < O else 1))

    # ---- (5)-(8) feasible layouts ------------------------------------------
    for n in range(1, N + 2):
        for c in range(C):
            m.Add(inbay(c, n) <= 1)
        for s in range(S):
            for t in range(T):
                m.Add(sum(x[(s, t, c, n)] for c in range(C)) <= 1)
            for t in range(T - 1):
                m.Add(sum(x[(s, t, c, n)] for c in range(C))
                      >= sum(x[(s, t + 1, c, n)] for c in range(C)))

    # ---- (9) partial order --------------------------------------------------
    for c in range(O):
        for d in range(O):
            if c == d or ins.group[c] != ins.group[d] or ins.prio[c] <= ins.prio[d]:
                continue
            for n in range(1, N + 2):
                m.Add(inbay(c, n) >= inbay(d, n))

    # ---- (10)/(11) transitions ---------------------------------------------
    for n in range(1, N + 1):
        m.Add(sum(inbay(c, n) for c in range(C))
              - sum(inbay(c, n + 1) for c in range(C)) == 1)
        for c in range(C):
            m.Add(inbay(c, n) >= inbay(c, n + 1))

    # ---- (12) blockers leave the stack -------------------------------------
    for n in range(1, N + 1):
        for s in range(S):
            for t in range(T):
                for c in range(C):
                    tgt = x[(s, t, c, n)] - inbay(c, n + 1)
                    for d in range(C):
                        if d == c:
                            continue
                        above = sum(x[(s, v, d, n)] for v in range(t + 1, T))
                        m.Add(sum(x[(s, u, d, n + 1)] for u in range(T))
                              <= 2 - above - tgt)

    # ---- (20) everything else keeps its slot -------------------------------
    for n in range(1, N + 1):
        for s in range(S):
            for t in range(T):
                for c in range(C):
                    tgt = x[(s, t, c, n)] - inbay(c, n + 1)
                    for d in range(C):
                        if d == c:
                            continue
                        elsewhere = sum(x[(u, tt, d, n)] for u in range(S)
                                        if u != s for tt in range(T))
                        below = sum(x[(s, v, d, n)] for v in range(t))
                        rhs = 2 - tgt - elsewhere - below
                        for sp in range(S):
                            for tp in range(T):
                                m.Add(x[(sp, tp, d, n)] - x[(sp, tp, d, n + 1)] <= rhs)
                                m.Add(x[(sp, tp, d, n + 1)] - x[(sp, tp, d, n)] <= rhs)

    # ---- (15) LIFO ----------------------------------------------------------
    for n in range(1, N + 1):
        for s in range(S):
            for t in range(T):
                for c in range(C):
                    tgt = x[(s, t, c, n)] - inbay(c, n + 1)
                    for td in range(t + 1, T):
                        for te in range(td + 1, T):
                            for d in range(C):
                                if d == c:
                                    continue
                                for e in range(C):
                                    if e in (c, d):
                                        continue
                                    lhs_pre = (x[(s, td, d, n)] + x[(s, te, e, n)] + tgt)
                                    for u in range(S):
                                        if u == s:
                                            continue
                                        for v in range(T):
                                            for w in range(v + 1, T):
                                                m.Add(x[(u, v, d, n + 1)]
                                                      + x[(u, w, e, n + 1)]
                                                      <= 4 - lhs_pre)

    # ---- (21)/(22) relocation counting -------------------------------------
    for n in range(1, N + 1):
        for s in range(S):
            for t in range(T):
                for c in range(C):
                    tgt = x[(s, t, c, n)] - inbay(c, n + 1)
                    above = sum(x[(s, v, cc, n)] for v in range(t + 1, T)
                                for cc in range(C))
                    m.Add((tgt - 1) * M + above <= r[(n, s)])

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    solver.parameters.log_search_progress = log
    t0 = time.perf_counter()
    status = solver.Solve(m)
    dt = time.perf_counter() - t0
    name = solver.StatusName(status)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        moves = _decode_moves(ins, solver, x)
        return IPResult(name, int(solver.ObjectiveValue()),
                        int(solver.BestObjectiveBound()), dt, moves)
    return IPResult(name, None, None, dt)
