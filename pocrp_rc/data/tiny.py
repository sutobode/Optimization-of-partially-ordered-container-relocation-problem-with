"""Helpers to build small instances directly from a layout specification."""
from __future__ import annotations

from ..core.instance import Instance


def make(layout: list[list[str]], T: int, name: str = "tiny") -> Instance:
    """Build an instance from labels such as ``[["A_1", "B_0"], ["Z", "A_0"]]``.

    Labels ``Z``/``Z_*``/``RC*`` denote rolled containers, everything else is
    ``<group>_<priority>`` with priority 0 = retrieved first.  Priorities inside
    a group must be contiguous, exactly as in the published dataset.
    """
    flat = [lab for st in layout for lab in st]
    is_rc = [lab.upper().startswith(("Z", "RC")) for lab in flat]
    oc_labels = sorted({lab for lab, rc in zip(flat, is_rc) if not rc},
                       key=lambda l: (l.split("_")[0], int(l.split("_")[1])))
    group_names = sorted({l.split("_")[0] for l in oc_labels})
    gidx = {g: i for i, g in enumerate(group_names)}
    O = len(oc_labels)
    C = len(flat)

    ids: dict[str, int] = {}
    group = [-1] * C
    prio = [-1] * C
    labels = [""] * C
    for i, lab in enumerate(oc_labels):
        g, p = lab.split("_")
        ids[lab] = i
        group[i] = gidx[g]
        prio[i] = int(p)
        labels[i] = lab
    nxt = O
    seq: list[int] = []
    for lab, rc in zip(flat, is_rc):
        if rc:
            ids_key = f"{lab}#{nxt}"
            ids[ids_key] = nxt
            labels[nxt] = f"Z_{100 + nxt - O}"
            seq.append(nxt)
            nxt += 1
        else:
            seq.append(ids[lab])

    out: list[tuple[int, ...]] = []
    k = 0
    for st in layout:
        out.append(tuple(seq[k:k + len(st)]))
        k += len(st)
    return Instance(name=name, S=len(layout), T=T, G=len(group_names), C=C, O=O,
                    group=group, prio=prio, layout=tuple(out), labels=labels)
