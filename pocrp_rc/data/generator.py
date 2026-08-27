"""Instance generator: turn a 0 %-RC instance into a p %-RC instance.

The procedure was reverse-engineered from the published data and verified: all
195 published 20 %-RC instances are reproduced exactly (up to the random draw)
by

    1. pick ``ceil(p * C)`` container positions uniformly at random,
    2. turn those containers into rolled containers,
    3. renumber the priorities inside every group so that they are contiguous
       ``0..k-1`` again (groups that lose all their members disappear, which is
       why ``G`` in the file name of the 30 %-set can be smaller than nominal).
"""
from __future__ import annotations

import math
import random

from ..core.instance import Instance


def n_rolled(C: int, proportion: float) -> int:
    """``ceil(p * C)`` -- verified against the 10 %, 20 % and 30 % published sets."""
    return math.ceil(proportion * C)


def mark_rolled(base: Instance, proportion: float,
                rng: random.Random | None = None,
                name: str | None = None) -> Instance:
    """Return a copy of ``base`` with ``ceil(p*C)`` containers turned into RCs."""
    if base.n_rc:
        raise ValueError("mark_rolled expects an instance without rolled containers")
    rng = rng or random.Random()
    k = n_rolled(base.C, proportion)
    if k > base.C:
        raise ValueError("proportion too large")
    rolled = set(rng.sample(range(base.C), k))
    return _rebuild(base, rolled, name or _derive_name(base, k))


def _derive_name(base: Instance, k: int) -> str:
    parts = base.name.split("-")
    if len(parts) == 8 and parts[0] == "Bay":
        return "-".join(["Bay", parts[1], parts[2], parts[3], parts[4],
                         str(base.C - k), str(k), parts[7]])
    return f"{base.name}-rc{k}"


def _rebuild(base: Instance, rolled: set[int], name: str) -> Instance:
    """Rebuild an instance where ``rolled`` becomes the RC set."""
    # surviving OCs per old group, ordered by old priority
    per_group: dict[int, list[int]] = {}
    for c in range(base.C):
        if c in rolled or base.group[c] < 0:
            continue
        per_group.setdefault(base.group[c], []).append(c)
    surviving = sorted(g for g, cs in per_group.items() if cs)
    new_gidx = {g: i for i, g in enumerate(surviving)}

    new_id: dict[int, int] = {}
    group: list[int] = []
    prio: list[int] = []
    nxt = 0
    for g in surviving:
        for new_p, c in enumerate(sorted(per_group[g], key=lambda x: base.prio[x])):
            new_id[c] = nxt
            group.append(new_gidx[g])
            prio.append(new_p)
            nxt += 1
    O = nxt
    for c in sorted(rolled):
        new_id[c] = nxt
        group.append(-1)
        prio.append(-1)
        nxt += 1

    layout = tuple(tuple(new_id[c] for c in st) for st in base.layout)
    letters = [chr(ord("A") + i) for i in range(len(surviving))]
    labels = [""] * base.C
    for c in range(base.C):
        nc = new_id[c]
        labels[nc] = (f"Z_{100 + nc - O}" if nc >= O
                      else f"{letters[group[nc]]}_{prio[nc]}")
    return Instance(name=name, S=base.S, T=base.T, G=len(surviving), C=base.C, O=O,
                    group=group, prio=prio, layout=layout, labels=labels)


# --------------------------------------------------------------------------- #
def derives_from(target: Instance, base: Instance) -> bool:
    """Is ``target`` obtainable from ``base`` by RC marking + renumbering?

    Used to validate the generator against the published 20 %-RC instances.
    """
    if (target.C, target.S, target.T) != (base.C, base.S, base.T):
        return False
    if [len(st) for st in target.layout] != [len(st) for st in base.layout]:
        return False
    rolled = {base.layout[i][j]
              for i, st in enumerate(target.layout)
              for j, c in enumerate(st) if c >= target.O}
    if len(rolled) != target.n_rc:
        return False
    rebuilt = _rebuild(base, rolled, target.name)
    return _signature(rebuilt) == _signature(target)


def _signature(ins: Instance) -> tuple:
    """Layout written with (group, priority) pairs; RCs collapse to a wildcard."""
    return tuple(
        tuple(("RC",) if c >= ins.O else (ins.group[c], ins.prio[c]) for c in st)
        for st in ins.layout
    )
