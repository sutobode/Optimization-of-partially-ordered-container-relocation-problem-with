"""Reader for the ``.pro`` instance files of Jovanovic et al. (2019) / Wang et al. (2026).

File format (verified on all 4875 published files)::

    Number Of Containers          -> C
    <int>
    Number Of Yard Stacks         -> S
    <int>
    MaxTier of Yard Stacks        -> T
    <int>
    Number of Vessel Stacks       -> G
    <int>
    Number Of Export Containers   -> O   (ordinary containers)
    <int>
    Number Of Shutout Containers  -> C-O (rolled containers)
    <int>
    Yard Bay
    Stack 0
    B_2 B_1 Z_100 A_0
    ...

Labels are ``<letter>_<priority>`` for ordinary containers (the letter is the
vessel stack = group, the number is the priority, 0 = retrieved first) and
``Z_<n>`` for rolled containers.  Containers are listed **bottom to top**.
The file name encodes ``Bay-S-T-G-C-O-RC-id.pro``; note that in the 30 %-RC set
``G`` is the number of groups *after* the RC marking, so it may be smaller than
the nominal grid value -- always trust the file content.
"""
from __future__ import annotations

import os
import re
from typing import Iterator

from ..core.instance import Instance

_HEADERS = {
    "Number Of Containers": "C",
    "Number Of Yard Stacks": "S",
    "MaxTier of Yard Stacks": "T",
    "Number of Vessel Stacks": "G",
    "Number Of Export Containers": "O",
    "Number Of Shutout Containers": "RC",
}

FNAME_RE = re.compile(r"Bay-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)\.pro$")


def parse_filename(path: str) -> dict[str, int] | None:
    m = FNAME_RE.search(os.path.basename(path))
    if not m:
        return None
    S, T, G, C, O, RC, idx = map(int, m.groups())
    return dict(S=S, T=T, G=G, C=C, O=O, RC=RC, id=idx)


def _read_raw(path: str) -> tuple[dict[str, int], list[list[str]]]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = [ln.rstrip("\n").rstrip("\r") for ln in fh]
    hdr: dict[str, int] = {}
    stacks: list[list[str]] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if line in _HEADERS:
            if i + 1 >= n or not lines[i + 1].strip().lstrip("-").isdigit():
                raise ValueError(f"{path}: header {line!r} without a value")
            hdr[_HEADERS[line]] = int(lines[i + 1].strip())
            i += 2
            continue
        if line.startswith("Stack "):
            nxt = lines[i + 1].strip() if i + 1 < n else ""
            if nxt.startswith("Stack ") or nxt in _HEADERS or nxt == "" or nxt == "Yard Bay":
                stacks.append([])            # empty stack
                i += 1
            else:
                stacks.append(nxt.split())
                i += 2
            continue
        i += 1
    missing = set(_HEADERS.values()) - set(hdr)
    if missing:
        raise ValueError(f"{path}: missing headers {sorted(missing)}")
    return hdr, stacks


def load_instance(path: str) -> Instance:
    """Read a ``.pro`` file into an :class:`Instance`."""
    hdr, raw = _read_raw(path)
    C, S, T, G, O, nrc = hdr["C"], hdr["S"], hdr["T"], hdr["G"], hdr["O"], hdr["RC"]
    if O + nrc != C:
        raise ValueError(f"{path}: O({O}) + RC({nrc}) != C({C})")
    if len(raw) != S:
        raise ValueError(f"{path}: {len(raw)} stacks but S={S}")

    labels_flat = [lab for st in raw for lab in st]
    if len(labels_flat) != C:
        raise ValueError(f"{path}: {len(labels_flat)} containers but C={C}")

    # ---- map labels to ids: OCs first, ordered by (group letter, priority) ----
    oc_labels = sorted({l for l in labels_flat if not l.startswith("Z_")},
                       key=lambda l: (l.split("_")[0], int(l.split("_")[1])))
    rc_labels = [l for l in labels_flat if l.startswith("Z_")]
    if len(oc_labels) != O or len(rc_labels) != nrc:
        raise ValueError(
            f"{path}: found {len(oc_labels)} OCs / {len(rc_labels)} RCs, "
            f"expected {O}/{nrc}")

    group_names = sorted({l.split("_")[0] for l in oc_labels})
    gidx = {g: i for i, g in enumerate(group_names)}

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
    for j, lab in enumerate(sorted(rc_labels, key=lambda l: int(l.split("_")[1]))):
        ids[lab] = O + j
        labels[O + j] = lab

    layout = tuple(tuple(ids[lab] for lab in st) for st in raw)
    name = os.path.splitext(os.path.basename(path))[0]
    return Instance(name=name, S=S, T=T, G=G, C=C, O=O, group=group, prio=prio,
                    layout=layout, labels=labels)


def iter_instances(root: str, pattern: str = "*.pro") -> Iterator[Instance]:
    import glob
    for p in sorted(glob.glob(os.path.join(root, pattern))):
        yield load_instance(p)


def write_instance(ins: Instance, path: str) -> None:
    """Write an instance back in the original ``.pro`` format."""
    letters = [chr(ord("A") + g) for g in range(ins.n_groups)]
    rc_no = 100
    lab: list[str] = [""] * ins.C
    for c in range(ins.O):
        lab[c] = f"{letters[ins.group[c]]}_{ins.prio[c]}"
    for c in range(ins.O, ins.C):
        lab[c] = f"Z_{rc_no}"
        rc_no += 1
    lines = [
        "Number Of Containers", str(ins.C),
        "Number Of Yard Stacks", str(ins.S),
        "MaxTier of Yard Stacks", str(ins.T),
        "Number of Vessel Stacks", str(ins.G),
        "Number Of Export Containers", str(ins.O),
        "Number Of Shutout Containers", str(ins.n_rc),
        "Yard Bay",
    ]
    for i, st in enumerate(ins.layout):
        lines.append(f"Stack {i}")
        lines.append(" ".join(lab[c] for c in st) + " ")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
