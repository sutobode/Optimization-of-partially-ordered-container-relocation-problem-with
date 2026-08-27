"""Full feasibility check of a POCRP-RC solution (restricted version)."""
from __future__ import annotations

from .bay import Bay
from .instance import Instance, Move, RELOCATE, RETRIEVE


class InfeasibleSolution(ValueError):
    pass


def validate(ins: Instance, moves: list[Move], *, strict_target: bool = True) -> int:
    """Replay ``moves`` on a fresh bay and return the number of relocations.

    Checks, in order of the paper's constraint groups:

    * every relocation moves the top container of its stack to a different,
      non-full stack (constraints 12/21);
    * a period consists of relocations of the containers above the target,
      all taken from the target's stack, followed by the retrieval of the
      target -- this is the *restricted* version (constraints 13/14/18/19);
    * a retrieved container is an OC whose echelon is 1 (constraints 9/11);
    * exactly one container is retrieved per period (constraint 10/12);
    * at the end all OCs are gone and every RC is still in the bay
      (constraints 3/4).
    """
    bay = Bay(ins)
    n_reloc = 0
    pending: list[Move] = []

    for k, m in enumerate(moves):
        if m.kind == RELOCATE:
            if m.container >= ins.C or m.container < 0:
                raise InfeasibleSolution(f"move {k}: unknown container {m.container}")
            if bay.where(m.container) != m.src:
                raise InfeasibleSolution(
                    f"move {k}: container {m.container} is in stack "
                    f"{bay.where(m.container)}, not {m.src}")
            if bay.top(m.src) != m.container:
                raise InfeasibleSolution(
                    f"move {k}: container {m.container} is not on top of stack {m.src}")
            if m.dst is None or m.dst == m.src:
                raise InfeasibleSolution(
                    f"move {k}: a blocking container must leave its stack")
            if bay.is_full(m.dst):
                raise InfeasibleSolution(f"move {k}: destination stack {m.dst} is full")
            pending.append(m)
            bay.relocate(m.container, m.dst)
            n_reloc += 1

        elif m.kind == RETRIEVE:
            c = m.container
            if c >= ins.O:
                raise InfeasibleSolution(f"move {k}: RC {c} may not be retrieved")
            if bay.where(c) != m.src:
                raise InfeasibleSolution(
                    f"move {k}: target {c} is in stack {bay.where(c)}, not {m.src}")
            if bay.top(m.src) != c:
                raise InfeasibleSolution(f"move {k}: target {c} is not on top")
            if not bay.is_candidate(c):
                raise InfeasibleSolution(
                    f"move {k}: target {c} violates the partial order "
                    f"(ce={bay.ce(c)}, must be 1)")
            if strict_target:
                for p in pending:
                    if p.src != m.src:
                        raise InfeasibleSolution(
                            f"move {k}: restricted version violated -- container "
                            f"{p.container} was relocated from stack {p.src} while "
                            f"the target sits in stack {m.src}")
                    if p.target != c:
                        raise InfeasibleSolution(
                            f"move {k}: relocation of {p.container} is attributed to "
                            f"target {p.target} but the period retrieves {c}")
            bay.retrieve(c)
            pending = []
        else:
            raise InfeasibleSolution(f"move {k}: unknown move kind {m.kind!r}")

    if pending:
        raise InfeasibleSolution("solution ends with relocations but no retrieval")
    if bay.n_oc_left != 0:
        raise InfeasibleSolution(f"{bay.n_oc_left} ordinary containers were never retrieved")
    left = sum(len(st) for st in bay.stacks)
    if left != ins.n_rc:
        raise InfeasibleSolution(
            f"{left} containers remain in the bay but there are {ins.n_rc} RCs")
    for st in bay.stacks:
        for c in st:
            if c < ins.O:
                raise InfeasibleSolution(f"OC {c} is still in the bay")
        if len(st) > ins.T:
            raise InfeasibleSolution("a stack exceeds the height limit")
    return n_reloc
