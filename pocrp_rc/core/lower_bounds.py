"""Lower bounds on the number of relocations."""
from __future__ import annotations

from .bay import Bay
from .concepts import deadlock_pairs, must_relocate
from .instance import Instance


def lb_forced(bay: Bay) -> int:
    """Property 1 extended to rolled containers.

    Every bad OC needs at least one relocation, and so does every RC that sits
    above an OC.  These sets are disjoint, hence their sizes add up.
    """
    return sum(1 for st in bay.stacks for c in st if must_relocate(bay, c))


def lb_forced_plus_deadlock(bay: Bay) -> int:
    """``lb_forced`` plus a maximal set of vertex-disjoint deadlocks.

    Deadlock containers are non-bad by definition, so they are never counted by
    ``lb_forced``; picking pairwise disjoint deadlocks keeps the bound valid
    (Property 2).
    """
    base = lb_forced(bay)
    used: set[int] = set()
    extra = 0
    for a, b in deadlock_pairs(bay):
        if a in used or b in used:
            continue
        used.add(a)
        used.add(b)
        extra += 1
    return base + extra


def lower_bound(ins: Instance, *, with_deadlock: bool = True) -> int:
    bay = Bay(ins)
    return lb_forced_plus_deadlock(bay) if with_deadlock else lb_forced(bay)
