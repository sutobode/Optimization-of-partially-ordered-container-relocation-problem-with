"""Structural concepts of Section 5.1: bad containers and deadlocks."""
from __future__ import annotations

from .bay import Bay

INF = 1 << 30


# --------------------------------------------------------------------------- #
# Definition 2 - bad containers
# --------------------------------------------------------------------------- #
def is_bad_oc(bay: Bay, c: int) -> bool:
    """Definition 2: an OC placed above a *higher priority* OC of its own group.

    Such a container is guaranteed to need at least one relocation (Property 1).
    """
    ins = bay.ins
    if c >= ins.O:
        return False
    s = bay.where(c)
    if s < 0:
        return False
    st = bay.stacks[s]
    g, p = ins.group[c], ins.prio[c]
    for d in st:
        if d == c:
            break
        if d < ins.O and ins.group[d] == g and ins.prio[d] < p:
            return True
    return False


def rc_blocks_oc(bay: Bay, c: int) -> bool:
    """An RC that sits above at least one OC.

    The paper's Property 1 only speaks about bad OCs, but such an RC must also
    be relocated at least once because the OC below it has to be retrieved.
    Used for the lower bound and (by default) for the TR indicators.
    """
    ins = bay.ins
    if c < ins.O:
        return False
    s = bay.where(c)
    if s < 0:
        return False
    st = bay.stacks[s]
    for d in st:
        if d == c:
            break
        if d < ins.O:
            return True
    return False


def must_relocate(bay: Bay, c: int) -> bool:
    """``c`` provably needs at least one relocation."""
    return is_bad_oc(bay, c) or rc_blocks_oc(bay, c)


def would_be_bad(bay: Bay, c: int, dst: int) -> bool:
    """Would relocating OC ``c`` onto stack ``dst`` make it a bad container?"""
    ins = bay.ins
    if c >= ins.O:
        return False
    g, p = ins.group[c], ins.prio[c]
    for d in bay.stacks[dst]:
        if d < ins.O and ins.group[d] == g and ins.prio[d] < p:
            return True
    return False


def count_bad_above(bay: Bay, c: int, rc_as_bad: bool = True) -> tuple[int, int]:
    """``(n_bad_above, n_non_bad_above)`` used by the TR indicators."""
    s = bay.where(c)
    st = bay.stacks[s]
    above = st[st.index(c) + 1:]
    bad = 0
    for d in above:
        if is_bad_oc(bay, d) or (rc_as_bad and rc_blocks_oc(bay, d)):
            bad += 1
    return bad, len(above) - bad


# --------------------------------------------------------------------------- #
# Definition 3 - deadlocks
# --------------------------------------------------------------------------- #
# Pattern (Fig. 3).  Two stacks s1 != s2 and two groups ga != gb with
#     s1:  ... b1 ... a2 ...      (a2 above b1)
#     s2:  ... a1 ... b2 ...      (b2 above a1)
# where prio(a1) < prio(a2) and prio(b1) < prio(b2) and all four are non-bad.
# Then a2 and b2 are deadlock containers: at least one of them must be
# relocated (Property 2).
# --------------------------------------------------------------------------- #
def _nonbad_ocs(bay: Bay, s: int) -> list[tuple[int, int, int]]:
    """``[(tier, group, prio)]`` of the non-bad OCs of stack ``s``."""
    ins = bay.ins
    out = []
    seen: dict[int, int] = {}          # group -> min prio seen so far below
    for t, c in enumerate(bay.stacks[s]):
        if c < ins.O:
            g, p = ins.group[c], ins.prio[c]
            if seen.get(g, INF) >= p:   # no higher-priority same-group container below
                out.append((t, g, p))
            if p < seen.get(g, INF):
                seen[g] = p
    return out


def deadlock_pairs(bay: Bay) -> list[tuple[int, int]]:
    """All deadlocked container pairs ``(a2, b2)`` of the layout (Definition 3).

    Complexity ``O(S^2 * T^2)``.
    """
    ins = bay.ins
    nb = [_nonbad_ocs(bay, s) for s in range(ins.S)]
    out: set[tuple[int, int]] = set()
    for s1 in range(ins.S):
        if len(nb[s1]) < 2:
            continue
        # iterate a2 upwards, keeping the minimum priority per group among the
        # non-bad OCs strictly below it (candidates for b1)
        below: dict[int, int] = {}
        for t2, ga2, pa2 in nb[s1]:
            a2 = bay.stacks[s1][t2]
            if below:
                for s2 in range(ins.S):
                    if s2 == s1 or len(nb[s2]) < 2:
                        continue
                    # lowest tier of a valid a1 in s2 (group ga2, priority < pa2)
                    ti = None
                    for t, g, p in nb[s2]:
                        if g == ga2 and p < pa2:
                            ti = t
                            break
                    if ti is None:
                        continue
                    for tj, gb2, pb2 in nb[s2]:               # b2 above a1
                        if tj <= ti or gb2 == ga2:
                            continue
                        if below.get(gb2, INF) < pb2:         # a matching b1 in s1
                            b2 = bay.stacks[s2][tj]
                            out.add((a2, b2) if a2 < b2 else (b2, a2))
            if pa2 < below.get(ga2, INF):
                below[ga2] = pa2
    return sorted(out)


def deadlock_containers(bay: Bay) -> set[int]:
    """All deadlock containers of the current layout (Definition 3)."""
    return {c for pair in deadlock_pairs(bay) for c in pair}


def count_deadlock_above(bay: Bay, c: int, dl: set[int] | None = None) -> int:
    """``DC(c)``: number of deadlock containers above ``c``."""
    if dl is None:
        dl = deadlock_containers(bay)
    if not dl:
        return 0
    s = bay.where(c)
    st = bay.stacks[s]
    return sum(1 for d in st[st.index(c) + 1:] if d in dl)


class DeadlockOracle:
    """Answers ``creates_deadlock(s)`` for one blocking container efficiently.

    Rebuilt once per relocation decision.  For container ``c`` to become a
    deadlock container after being dropped on stack ``s`` we need another stack
    ``s2 != s`` holding ``a1`` (same group as ``c``, higher priority) with some
    non-bad ``b2`` above it, while stack ``s`` must hold a non-bad ``b1`` of
    ``b2``'s group with a higher priority than ``b2``.

    Construction is ``O(S*T)`` and each query is ``O(T)``.
    """

    __slots__ = ("ok", "minprio", "top1", "top2")

    def __init__(self, bay: Bay, c: int):
        ins = bay.ins
        self.ok = c < ins.O
        if not self.ok:
            return
        gc, pc = ins.group[c], ins.prio[c]
        nb = [_nonbad_ocs(bay, s) for s in range(ins.S)]

        # min priority of a non-bad OC per (stack, group) -> candidates for b1
        self.minprio: list[dict[int, int]] = []
        for s in range(ins.S):
            d: dict[int, int] = {}
            for _, g, p in nb[s]:
                if p < d.get(g, INF):
                    d[g] = p
            self.minprio.append(d)

        # per group g: the two largest "b2 priority" values over all stacks
        self.top1: dict[int, tuple[int, int]] = {}      # g -> (prio, stack)
        self.top2: dict[int, int] = {}                  # g -> prio
        for s2 in range(ins.S):
            best: dict[int, int] = {}
            seen_a1 = False
            for _, g, p in nb[s2]:
                if seen_a1 and g != gc and p > best.get(g, -1):
                    best[g] = p
                if g == gc and p < pc:
                    seen_a1 = True
            for g, p in best.items():
                cur = self.top1.get(g)
                if cur is None or p > cur[0]:
                    if cur is not None:
                        self.top2[g] = max(self.top2.get(g, -1), cur[0])
                    self.top1[g] = (p, s2)
                elif p > self.top2.get(g, -1):
                    self.top2[g] = p

    def creates_deadlock(self, s: int) -> bool:
        if not self.ok:
            return False
        for g, pmin in self.minprio[s].items():
            hit = self.top1.get(g)
            if hit is None:
                continue
            pb2 = hit[0] if hit[1] != s else self.top2.get(g, -1)
            if pmin < pb2:
                return True
        return False
