"""Instance definition and moves for POCRP-RC (Section 3 of the paper)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

# Move kinds
RELOCATE = "R"
RETRIEVE = "T"


@dataclass(frozen=True)
class Move:
    """A single crane operation.

    kind      : RELOCATE or RETRIEVE
    container : container id
    src       : source stack index
    dst       : destination stack index (None for RETRIEVE)
    target    : the target container of the period this move belongs to.
                For a RETRIEVE move this equals ``container``.
    """

    kind: str
    container: int
    src: int
    dst: Optional[int]
    target: int

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        if self.kind == RETRIEVE:
            return f"T(c{self.container}@s{self.src})"
        return f"R(c{self.container}: s{self.src}->s{self.dst} | tgt c{self.target})"


@dataclass
class Instance:
    """A POCRP-RC instance.

    Container ids are 0..C-1 with ordinary containers (OC) first:
      * ``0 .. O-1``  : ordinary containers, ``group``/``prio`` are valid
      * ``O .. C-1``  : rolled containers (RC), ``group = prio = -1``

    Within a group, priorities are ``0, 1, ..., group_size-1`` and a *lower*
    number means *higher* priority (must be retrieved earlier).  The published
    dataset satisfies this contiguity property (verified for all 4875 files).
    """

    name: str
    S: int                      # number of stacks
    T: int                      # height limit
    G: int                      # number of groups (as recorded by the generator)
    C: int                      # number of containers
    O: int                      # number of ordinary containers
    group: list[int]            # group of each container (-1 for RC)
    prio: list[int]             # priority inside the group (-1 for RC)
    layout: tuple[tuple[int, ...], ...]   # bottom -> top per stack
    labels: list[str] = field(default_factory=list)   # original file labels

    # derived
    group_size: list[int] = field(default_factory=list, repr=False)
    container_by_gp: dict[tuple[int, int], int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        n_groups = (max(self.group) + 1) if self.O else 0
        self.group_size = [0] * n_groups
        self.container_by_gp = {}
        for c in range(self.O):
            g, p = self.group[c], self.prio[c]
            self.group_size[g] += 1
            self.container_by_gp[(g, p)] = c
        for g, size in enumerate(self.group_size):
            missing = [p for p in range(size) if (g, p) not in self.container_by_gp]
            if missing:
                raise ValueError(
                    f"{self.name}: priorities of group {g} are not contiguous, "
                    f"missing {missing}"
                )
        if len(self.layout) != self.S:
            raise ValueError(f"{self.name}: {len(self.layout)} stacks != S={self.S}")
        flat = [c for st in self.layout for c in st]
        if sorted(flat) != list(range(self.C)):
            raise ValueError(f"{self.name}: layout is not a permutation of 0..C-1")
        if any(len(st) > self.T for st in self.layout):
            raise ValueError(f"{self.name}: a stack exceeds the height limit T={self.T}")

    # ------------------------------------------------------------------ #
    @property
    def n_rc(self) -> int:
        return self.C - self.O

    @property
    def n_groups(self) -> int:
        return len(self.group_size)

    def is_rc(self, c: int) -> bool:
        return c >= self.O

    def label(self, c: int) -> str:
        if self.labels:
            return self.labels[c]
        return f"Z_{c}" if self.is_rc(c) else f"{self.group[c]}_{self.prio[c]}"

    def describe(self) -> str:
        rows = [f"{self.name}: C={self.C} O={self.O} RC={self.n_rc} "
                f"S={self.S} T={self.T} G={self.G}"]
        for i, st in enumerate(self.layout):
            rows.append(f"  s{i}: " + " ".join(self.label(c) for c in st))
        return "\n".join(rows)


def n_relocations(moves: Sequence[Move]) -> int:
    """Objective value of a solution: the number of relocations."""
    return sum(1 for m in moves if m.kind == RELOCATE)
