"""Relative-Location (RL) integer programme of Section 4.4, on CP-SAT.

Variables (paper notation)

    a[n][c][d] = 1  iff container c is below container d before the n-th
                    retrieval;  c in 1..C+S, d in 1..C.  Containers C+1..C+S
                    are the "artificial containers" that stand for the stacks.
    x[n][c]    = 1  iff container c is relocated during period n.

Deviations from the printed model (see docs/ERRATA.md)

* constraint (10) is printed as ``a_{n,c+r,d}``; the semantics require
  ``a_{n,C+r,d}``;
* constraint (20) is printed with a duplicated, truncated second line; it is
  reconstructed from the accompanying prose on p. 8;
* the published constraint set does not by itself force a *single* target per
  period to be a candidate of the partial order in every case, so constraint
  (11) is applied for all ``n`` including ``N+1``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ortools.sat.python import cp_model

from ..core.bay import Bay
from ..core.instance import Instance, Move, RELOCATE, RETRIEVE
from ..core.validator import validate


@dataclass
class IPResult:
    status: str
    objective: Optional[int]
    bound: Optional[int]
    seconds: float
    moves: Optional[list[Move]] = None


def _initial_matrix(ins: Instance) -> dict[tuple[int, int], int]:
    """``A[c][d] = 1`` iff ``c`` is below ``d``; stacks are containers C..C+S-1."""
    A: dict[tuple[int, int], int] = {}
    for s, st in enumerate(ins.layout):
        art = ins.C + s
        for j, d in enumerate(st):
            A[(art, d)] = 1
            for c in st[:j]:
                A[(c, d)] = 1
    return A


def _decode_moves(ins: Instance, solver: cp_model.CpSolver, a: dict) -> list[Move]:
    """Decode period layouts into the restricted relocation sequence."""
    bay = Bay(ins)
    moves: list[Move] = []

    def present(n: int, c: int) -> bool:
        return any(solver.Value(a[(n, ins.C + s, c)]) for s in range(ins.S))

    for n in range(1, ins.O + 1):
        targets = [c for c in range(ins.O) if present(n, c) and not present(n + 1, c)]
        if len(targets) != 1:
            raise ValueError(f"period {n}: expected one target, found {targets}")
        target = targets[0]
        src = bay.where(target)
        for blocker in reversed(bay.blockers_above(target)):
            destinations = [s for s in range(ins.S)
                            if solver.Value(a[(n + 1, ins.C + s, blocker)])]
            if len(destinations) != 1:
                raise ValueError(
                    f"period {n}: container {blocker} has destinations {destinations}")
            dst = destinations[0]
            moves.append(Move(RELOCATE, blocker, src, dst, target))
            bay.relocate(blocker, dst)
        moves.append(Move(RETRIEVE, target, src, None, target))
        bay.retrieve(target)
    validate(ins, moves)
    return moves


def build_and_solve(ins: Instance, time_limit: float = 3600.0,
                    workers: int = 8, log: bool = False) -> IPResult:
    import time
    C, S, T, O = ins.C, ins.S, ins.T, ins.O
    N = O                                     # one retrieval per period
    CS = C + S
    A = _initial_matrix(ins)

    m = cp_model.CpModel()
    a = {(n, c, d): m.NewBoolVar(f"a_{n}_{c}_{d}")
         for n in range(1, N + 2) for c in range(CS) for d in range(C) if c != d}
    x = {(n, c): m.NewBoolVar(f"x_{n}_{c}")
         for n in range(1, N + 1) for c in range(C)}

    def av(n, c, d):
        return a[(n, c, d)] if c != d else 0

    def instack(n, d):                        # sum_s a[n][C+s][d]  (d is in the bay)
        return sum(a[(n, C + s, d)] for s in range(S))

    # ---- (1) objective ------------------------------------------------------
    m.Minimize(sum(x.values()))

    # ---- (2) initial layout -------------------------------------------------
    for c in range(CS):
        for d in range(C):
            if c == d:
                continue
            m.Add(a[(1, c, d)] == A.get((c, d), 0))

    # ---- (3)/(4) final layout ----------------------------------------------
    for d in range(C):
        m.Add(instack(N + 1, d) == (0 if d < O else 1))

    # ---- (5)/(6) one stack per container, height limit ----------------------
    for n in range(1, N + 2):
        for c in range(C):
            m.Add(instack(n, c) <= 1)
        for s in range(S):
            m.Add(sum(a[(n, C + s, c)] for c in range(C)) <= T)

    # ---- (7)/(8) irreflexivity and antisymmetry ----------------------------
    for n in range(1, N + 2):
        for c in range(C):
            for d in range(c + 1, C):
                m.Add(a[(n, c, d)] + a[(n, d, c)] <= 1)

    # ---- (9)/(10) same stack <=> stacking relation --------------------------
    for n in range(1, N + 2):
        for s in range(S):
            for c in range(C):
                for d in range(C):
                    if c == d:
                        continue
                    m.Add(a[(n, c, d)] + a[(n, d, c)]
                          >= a[(n, C + s, c)] + a[(n, C + s, d)] - 1)
                    other = sum(a[(n, C + r, d)] for r in range(S) if r != s)
                    m.Add(a[(n, c, d)] + a[(n, d, c)] <= 2 - a[(n, C + s, c)] - other)

    # ---- (11) partial order -------------------------------------------------
    for c in range(O):
        g, p = ins.group[c], ins.prio[c]
        for d in range(O):
            if d == c or ins.group[d] != g or ins.prio[d] >= p:
                continue
            # d has a higher priority than c: c may only leave after d
            for n in range(1, N + 2):
                m.Add(instack(n, c) >= instack(n, d))

    # ---- (12) exactly one retrieval per period ------------------------------
    for n in range(1, N + 2):
        m.Add(sum(instack(n, c) for c in range(C)) == C + 1 - n)

    # ---- (13) no container returns ------------------------------------------
    for n in range(1, N + 1):
        for c in range(C):
            m.Add(instack(n + 1, c) <= instack(n, c))

    # ---- (14)/(15) unmoved containers keep their relations ------------------
    for n in range(1, N + 1):
        for c in range(C):
            left = instack(n, c) - instack(n + 1, c)      # 1 iff c is the target
            for d in range(CS):
                if d == c:
                    continue
                m.Add(a[(n + 1, d, c)] <= a[(n, d, c)] + x[(n, c)] + left)
                m.Add(a[(n + 1, d, c)] >= a[(n, d, c)] - x[(n, c)] - left)

    # ---- (16)-(19) which containers are relocated ---------------------------
    for n in range(1, N + 1):
        for c in range(C):
            m.Add(x[(n, c)] <= instack(n + 1, c))
        for d in range(C):
            tgt = instack(n, d) - instack(n + 1, d)        # 1 iff d is the target
            for c in range(C):
                if c == d:
                    continue
                m.Add(x[(n, c)] >= a[(n, d, c)] + tgt - 1)
                m.Add(x[(n, c)] <= 2 - tgt - a[(n, c, d)])
                m.Add(x[(n, c)] <= 1 - tgt + a[(n, c, d)] + a[(n, d, c)])

    # ---- (20) nothing moves into the target's stack -------------------------
    for n in range(1, N + 1):
        for d in range(C):
            tgt = instack(n, d) - instack(n + 1, d)
            for s in range(S):
                for c in range(C):
                    if c == d:
                        continue
                    other = sum(a[(n, C + r, c)] for r in range(S) if r != s)
                    m.Add(a[(n + 1, C + s, c)] <= 3 - a[(n, C + s, d)] - tgt - other)

    # ---- (21) a relocated container leaves its stack ------------------------
    for n in range(1, N + 1):
        for c in range(C):
            for s in range(S):
                m.Add(a[(n + 1, C + s, c)] <= 2 - x[(n, c)] - a[(n, C + s, c)])

    # ---- (22) LIFO ----------------------------------------------------------
    for n in range(1, N + 1):
        for c in range(C):
            for d in range(C):
                if c == d:
                    continue
                m.Add(a[(n + 1, d, c)] <= 3 - a[(n, d, c)] - x[(n, c)] - x[(n, d)])

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    solver.parameters.log_search_progress = log
    t0 = time.perf_counter()
    status = solver.Solve(m)
    dt = time.perf_counter() - t0
    name = solver.StatusName(status)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        moves = _decode_moves(ins, solver, a)
        return IPResult(name, int(solver.ObjectiveValue()),
                        int(solver.BestObjectiveBound()), dt, moves)
    return IPResult(name, None, None, dt)
