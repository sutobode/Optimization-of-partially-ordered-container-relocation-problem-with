"""Mutable bay state with the echelon machinery of Section 5.1."""
from __future__ import annotations

from typing import Iterable, Optional

from .instance import Instance

EMPTY_STACK_ECHELON_OFFSET = 1   # se(s) = C + 1 for empty / rolled stacks


class Bay:
    """The layout during retrieval, plus incremental echelon bookkeeping.

    Definition 4 (container echelon): ``ce(c)`` is the rank of ``c``'s priority
    among the containers of its group that are still in the layout.  Because
    priorities inside a group are contiguous and are always retrieved in
    increasing order, ``ce(c) = prio[c] - next_prio[group[c]] + 1``.

    Definition 5 (stack echelon): ``se(s) = C + 1`` if ``s`` is empty or a
    rolled stack, otherwise ``min ce(c)`` over the ordinary containers in ``s``.
    """

    __slots__ = ("ins", "stacks", "next_prio", "n_oc_left", "_where")

    def __init__(self, ins: Instance):
        self.ins = ins
        self.stacks: list[list[int]] = [list(st) for st in ins.layout]
        self.next_prio: list[int] = [0] * ins.n_groups
        self.n_oc_left: int = ins.O
        self._where: list[int] = [-1] * ins.C     # container -> stack index
        for si, st in enumerate(self.stacks):
            for c in st:
                self._where[c] = si

    # ------------------------------------------------------------------ #
    # basic queries
    # ------------------------------------------------------------------ #
    def copy(self) -> "Bay":
        new = Bay.__new__(Bay)
        new.ins = self.ins
        new.stacks = [list(st) for st in self.stacks]
        new.next_prio = list(self.next_prio)
        new.n_oc_left = self.n_oc_left
        new._where = list(self._where)
        return new

    def height(self, s: int) -> int:
        return len(self.stacks[s])

    def is_full(self, s: int) -> bool:
        return len(self.stacks[s]) >= self.ins.T

    def is_empty(self, s: int) -> bool:
        return not self.stacks[s]

    def top(self, s: int) -> Optional[int]:
        st = self.stacks[s]
        return st[-1] if st else None

    def where(self, c: int) -> int:
        return self._where[c]

    def is_rc(self, c: int) -> bool:
        return c >= self.ins.O

    def is_rolled_stack(self, s: int) -> bool:
        """Definition 1: a non-empty stack that contains only RCs."""
        st = self.stacks[s]
        return bool(st) and all(c >= self.ins.O for c in st)

    def has_oc(self, s: int) -> bool:
        return any(c < self.ins.O for c in self.stacks[s])

    def done(self) -> bool:
        return self.n_oc_left == 0

    # ------------------------------------------------------------------ #
    # echelons
    # ------------------------------------------------------------------ #
    def ce(self, c: int) -> int:
        """Container echelon; ``C + 1`` for rolled containers (lowest priority)."""
        ins = self.ins
        if c >= ins.O:
            return ins.C + EMPTY_STACK_ECHELON_OFFSET
        return ins.prio[c] - self.next_prio[ins.group[c]] + 1

    def is_candidate(self, c: int) -> bool:
        ins = self.ins
        return c < ins.O and ins.prio[c] == self.next_prio[ins.group[c]]

    def candidates(self) -> list[int]:
        """Containers with ``ce == 1``: the only legal targets (Definition 4)."""
        ins = self.ins
        out = []
        for g, size in enumerate(ins.group_size):
            p = self.next_prio[g]
            if p < size:
                out.append(ins.container_by_gp[(g, p)])
        return out

    def se(self, s: int) -> int:
        """Stack echelon (Definition 5)."""
        ins = self.ins
        st = self.stacks[s]
        if not st or all(c >= ins.O for c in st):
            return ins.C + EMPTY_STACK_ECHELON_OFFSET
        best = ins.C + EMPTY_STACK_ECHELON_OFFSET
        for c in st:
            if c < ins.O:
                v = ins.prio[c] - self.next_prio[ins.group[c]] + 1
                if v < best:
                    best = v
        return best

    def se_group(self, s: int, g: int) -> int:
        """``se_c(s)`` of rule R3: min echelon among containers of group ``g``."""
        ins = self.ins
        best = ins.C + EMPTY_STACK_ECHELON_OFFSET
        for c in self.stacks[s]:
            if c < ins.O and ins.group[c] == g:
                v = ins.prio[c] - self.next_prio[g] + 1
                if v < best:
                    best = v
        return best

    # ------------------------------------------------------------------ #
    # transitions
    # ------------------------------------------------------------------ #
    def relocate(self, c: int, dst: int) -> None:
        src = self._where[c]
        if self.stacks[src][-1] != c:
            raise ValueError(f"container {c} is not on top of stack {src}")
        if src == dst:
            raise ValueError("a blocking container may not stay in its own stack")
        if self.is_full(dst):
            raise ValueError(f"stack {dst} is full")
        self.stacks[src].pop()
        self.stacks[dst].append(c)
        self._where[c] = dst

    def retrieve(self, c: int) -> None:
        ins = self.ins
        if c >= ins.O:
            raise ValueError("rolled containers are never retrieved")
        src = self._where[c]
        if self.stacks[src][-1] != c:
            raise ValueError(f"container {c} is not on top of stack {src}")
        if ins.prio[c] != self.next_prio[ins.group[c]]:
            raise ValueError(f"container {c} is not a candidate (ce={self.ce(c)})")
        self.stacks[src].pop()
        self._where[c] = -1
        self.next_prio[ins.group[c]] += 1
        self.n_oc_left -= 1

    def blockers_above(self, c: int) -> list[int]:
        """Containers stacked above ``c`` (bottom-most blocker first)."""
        s = self._where[c]
        st = self.stacks[s]
        return st[st.index(c) + 1:]

    def n_above(self, c: int) -> int:
        s = self._where[c]
        st = self.stacks[s]
        return len(st) - st.index(c) - 1

    # ------------------------------------------------------------------ #
    def key(self) -> tuple:
        """Canonical hashable state, exploiting two symmetries.

        * stacks are interchangeable (all have the same height limit T),
        * rolled containers are pairwise interchangeable.
        """
        ins = self.ins
        rc = ins.O
        return tuple(sorted(
            tuple(rc if c >= rc else c for c in st) for st in self.stacks
        ))

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return "\n".join(
            f"  s{i}: " + " ".join(self.ins.label(c) for c in st)
            for i, st in enumerate(self.stacks)
        )
