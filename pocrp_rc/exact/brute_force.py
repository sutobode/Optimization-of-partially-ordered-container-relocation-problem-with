"""Exact solver for small POCRP-RC instances.

Memoised depth-first search over layouts.  Two symmetries shrink the state
space: stacks are interchangeable and rolled containers are indistinguishable
(see :meth:`Bay.key`).  Used as the ground truth for every other component.
"""
from __future__ import annotations

from typing import Optional

from ..core.bay import Bay
from ..core.instance import Instance, Move, RELOCATE, RETRIEVE
from ..core.lower_bounds import lb_forced


class SearchLimit(RuntimeError):
    pass


class ExactSolver:
    def __init__(self, ins: Instance, max_nodes: int = 4_000_000):
        self.ins = ins
        self.max_nodes = max_nodes
        self.nodes = 0
        self.memo: dict[tuple, int] = {}

    # ------------------------------------------------------------------ #
    def _children(self, bay: Bay):
        """Yield ``(cost, child_bay, moves)`` for every legal period."""
        ins = self.ins
        seen: set[tuple] = set()
        for c in bay.candidates():
            s = bay.where(c)
            blockers = bay.blockers_above(c)          # bottom-most first
            k = len(blockers)
            order = list(reversed(blockers))          # must be moved top-first

            def place(b: Bay, idx: int, moves: list[Move]):
                if idx == k:
                    nb = b.copy()
                    nb.retrieve(c)
                    yield k, nb, moves + [Move(RETRIEVE, c, s, None, c)]
                    return
                cont = order[idx]
                for dst in range(ins.S):
                    if dst == s or b.is_full(dst):
                        continue
                    nb = b.copy()
                    nb.relocate(cont, dst)
                    yield from place(nb, idx + 1,
                                     moves + [Move(RELOCATE, cont, s, dst, c)])

            for cost, child, moves in place(bay, 0, []):
                key = child.key()
                if key in seen:
                    continue
                seen.add(key)
                yield cost, child, moves

    # ------------------------------------------------------------------ #
    def value(self, bay: Bay) -> int:
        if bay.done():
            return 0
        key = bay.key()
        hit = self.memo.get(key)
        if hit is not None:
            return hit
        self.nodes += 1
        if self.nodes > self.max_nodes:
            raise SearchLimit(f"node limit {self.max_nodes} exceeded")
        best = 1 << 30
        lb = lb_forced(bay)
        for cost, child, _ in self._children(bay):
            if cost >= best:
                continue
            v = cost + self.value(child)
            if v < best:
                best = v
                if best <= lb:                        # cannot do better
                    break
        self.memo[key] = best
        return best

    # ------------------------------------------------------------------ #
    def solution(self, bay: Optional[Bay] = None) -> tuple[int, list[Move]]:
        """Optimal value together with one optimal move sequence."""
        bay = bay or Bay(self.ins)
        total = self.value(bay)
        moves: list[Move] = []
        cur, remaining = bay, total
        while not cur.done():
            for cost, child, ms in self._children(cur):
                if cost + self.value(child) == remaining:
                    moves.extend(ms)
                    remaining -= cost
                    cur = child
                    break
            else:                                     # pragma: no cover
                raise RuntimeError("failed to reconstruct an optimal solution")
        return total, moves


def solve_exact(ins: Instance, max_nodes: int = 4_000_000) -> tuple[int, list[Move]]:
    return ExactSolver(ins, max_nodes).solution()


def optimum(ins: Instance, max_nodes: int = 4_000_000) -> int:
    solver = ExactSolver(ins, max_nodes)
    return solver.value(Bay(ins))
