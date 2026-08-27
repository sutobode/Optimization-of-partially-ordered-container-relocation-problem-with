"""Benchmark Random algorithm of Section 6.2.

"The Random algorithm conducts random relocations by randomly selecting a
target container from the set of candidate containers and a feasible stack
(non-full and not containing the target container) as the drop-off stack."
"""
from __future__ import annotations

import random
from typing import Optional

from ..core.bay import Bay
from ..core.instance import Instance, Move, RELOCATE, RETRIEVE
from .greedy import NoFeasibleStack


def random_solution(ins: Instance, seed: Optional[int] = None) -> list[Move]:
    rng = random.Random(seed)
    bay = Bay(ins)
    moves: list[Move] = []
    while not bay.done():
        target = rng.choice(bay.candidates())
        src = bay.where(target)
        for blocker in reversed(bay.blockers_above(target)):
            options = [s for s in range(ins.S) if s != src and not bay.is_full(s)]
            if not options:
                raise NoFeasibleStack(f"no stack can host container {blocker}")
            dst = rng.choice(options)
            moves.append(Move(RELOCATE, blocker, src, dst, target))
            bay.relocate(blocker, dst)
        moves.append(Move(RETRIEVE, target, src, None, target))
        bay.retrieve(target)
    return moves
