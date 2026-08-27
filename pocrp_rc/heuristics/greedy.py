"""Greedy algorithm of Section 5.2 (Algorithm 1) and its randomised variant.

Deviations from the published text, all recorded in docs/ERRATA.md:

* rule R1 of Task 2 mentions "an ABC" which the paper never defines; the only
  reading that keeps R1 strictly stronger than R2 is *a bad container*;
* ``S_RC`` is described as "the set of stacks that contain at least one RC,
  i.e., non-empty stacks and non-rolled stacks" -- the two halves contradict
  each other.  The surrounding prose ("R1 avoids empty and rolled stacks")
  makes the second half the intended one, so ``S_RC`` is implemented as the set
  of stacks holding at least one *ordinary* container.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional, Sequence

from ..core.bay import Bay
from ..core.concepts import (DeadlockOracle, count_deadlock_above,
                             deadlock_containers, is_bad_oc, would_be_bad)
from ..core.instance import Instance, Move, RELOCATE, RETRIEVE


class NoFeasibleStack(RuntimeError):
    pass


@dataclass
class GreedyConfig:
    """Setting (B) of Section 6.3.1 is the paper's tuned default.

    The options below the first block resolve genuine ambiguities of the
    published description; ``checks/tune_greedy.py`` selects them empirically
    against the averages of Table 5.
    """

    randomized: bool = False
    deadlock_in_target: bool = False      # DC(c) indicator inside TR
    deadlock_in_stack: bool = True        # deadlock avoidance inside RR (rule R1)
    seed: Optional[int] = None

    # --- ambiguity switches ------------------------------------------------
    rc_mode: str = "bad"                  # how RCs above a target count in NBC/BC:
    #                                       "bad" | "nonbad" | "ignore"
    rc_prefer: str = "rolled"             # rule R1 of Task 1 prefers "rolled" or
    #                                       "empty" stacks first
    tie: str = "first"                    # deterministic tie-breaking: first|last|
    #                                       min_height|max_height
    oc_rule: str = "max_se"               # rules R1/R2 of Task 2: "max_se" (the
    #                                       literal argmax of the paper),
    #                                       "best_fit" (smallest se still larger
    #                                       than ce(c)) or "min_se"
    tr_rule: str = "paper"                # "paper" = (min NBC, max DC, min BC),
    #                                       "min_total", "max_bc"
    oc_pool: str = "has_rc"               # which stacks Task 2 may use before R4:
    #                                       "has_rc"        - literal S_RC,
    #                                       "oc_only"       - the prose reading,
    #                                       "include_rolled", "include_all"

    @staticmethod
    def setting(name: str, **kw) -> "GreedyConfig":
        """Settings (A), (B), (C) of Section 6.3.1."""
        table = {"A": (True, True), "B": (False, True), "C": (False, False)}
        tgt, stk = table[name.upper()]
        return GreedyConfig(deadlock_in_target=tgt, deadlock_in_stack=stk, **kw)

    @staticmethod
    def paper(**kw) -> "GreedyConfig":
        """Algorithm 1 as written in Sections 5.2.2--5.2.3.

        Unlike GRASP setting (B), the standalone Greedy algorithm uses the
        deadlock indicator both in target selection (``max DC(c)``) and in
        drop-off stack rule R1.
        """
        opts = dict(deadlock_in_target=True, deadlock_in_stack=True,
                    rc_mode="bad", rc_prefer="rolled", tie="first",
                    oc_rule="max_se", tr_rule="paper", oc_pool="has_rc")
        opts.update(kw)
        return GreedyConfig(**opts)

    @staticmethod
    def profile(name: str, **kw) -> "GreedyConfig":
        """Named readings of the ambiguous parts (see ``checks/tune_greedy*.py``).

        ==============  ================================================  =======
        profile         reading                                           avg
        ==============  ================================================  =======
        ``literal``     ``S_RC`` = stacks holding at least one RC          51.11
        ``prose``       ``S_RC`` = stacks holding at least one OC          59.14
        ``calibrated``  strongest variant: any non-empty stack, max_se     50.09
        ==============  ================================================  =======

        Reference value of the paper (Table 5/11): ``54.22``.
        """
        profiles = {
            "literal": dict(oc_pool="has_rc", oc_rule="max_se", tie="first"),
            "prose": dict(oc_pool="oc_only", oc_rule="max_se", tie="first"),
            "calibrated": dict(oc_pool="include_rolled", oc_rule="max_se",
                               tie="max_height"),
        }
        opts = dict(profiles[name.lower()])
        opts.update(kw)
        return GreedyConfig.setting(opts.pop("setting", "B"), **opts)


# --------------------------------------------------------------------------- #
def _auto_retrieve(bay: Bay, moves: list[Move]) -> None:
    """Retrieve every top container whose echelon is 1 (Algorithm 1, lines 11-14)."""
    again = True
    while again:
        again = False
        for s in range(bay.ins.S):
            c = bay.top(s)
            if c is not None and bay.is_candidate(c):
                moves.append(Move(RETRIEVE, c, s, None, c))
                bay.retrieve(c)
                again = True


def _creates_free_stack(bay: Bay, c: int) -> bool:
    """Would retrieving ``c`` leave its stack empty or rolled?"""
    s = bay.where(c)
    st = bay.stacks[s]
    below = st[:st.index(c)]
    return (not below) or all(x >= bay.ins.O for x in below)


def _free_stack_exists(bay: Bay) -> bool:
    """Is there already an empty stack or a non-full rolled stack for the RCs?"""
    for s in range(bay.ins.S):
        if bay.is_empty(s) or (bay.is_rolled_stack(s) and not bay.is_full(s)):
            return True
    return False


# --------------------------------------------------------------------------- #
def _indicators(bay: Bay, c: int, cfg: GreedyConfig) -> tuple[int, int]:
    """``(BC(c), NBC(c))``: bad / non-bad containers above ``c``."""
    ins = bay.ins
    s = bay.where(c)
    st = bay.stacks[s]
    above = st[st.index(c) + 1:]
    bad = nonbad = 0
    for d in above:
        if d >= ins.O:                        # rolled container
            if cfg.rc_mode == "bad":
                bad += 1
            elif cfg.rc_mode == "nonbad":
                nonbad += 1
            continue
        if is_bad_oc(bay, d):
            bad += 1
        else:
            nonbad += 1
    return bad, nonbad


def select_target(bay: Bay, cand: Sequence[int], cfg: GreedyConfig,
                  rng: random.Random) -> int:
    """Function ``TR(bay, currCandi)`` of Section 5.2.2.

    Lexicographic order: ``min NBC(c)``, ``max DC(c)``, ``min BC(c)``; then the
    tie-breaking rule based on free stacks for the rolled containers.
    """
    if len(cand) == 1:
        return cand[0]
    dl = deadlock_containers(bay) if cfg.deadlock_in_target else set()
    scored = []
    for c in cand:
        bc, nbc = _indicators(bay, c, cfg)
        dc = count_deadlock_above(bay, c, dl) if cfg.deadlock_in_target else 0
        if cfg.tr_rule == "min_total":
            score = (nbc + bc, -dc, 0)
        elif cfg.tr_rule == "max_bc":
            score = (nbc, -dc, -bc)
        else:
            score = (nbc, -dc, bc)
        scored.append((score, c))
    best = min(s for s, _ in scored)
    tied = [c for s, c in scored if s == best]
    if len(tied) == 1:
        return tied[0]

    if not _free_stack_exists(bay):
        prefer = [c for c in tied if _creates_free_stack(bay, c)]
        if prefer:
            tied = prefer
    return _pick(tied, cfg, rng)


# --------------------------------------------------------------------------- #
def _pick(options: list[int], cfg: GreedyConfig, rng: random.Random,
          bay: Bay | None = None) -> int:
    if cfg.randomized:
        return rng.choice(options)
    if len(options) == 1 or bay is None:
        return options[-1] if cfg.tie == "last" else options[0]
    if cfg.tie == "min_height":
        return min(options, key=lambda s: (bay.height(s), s))
    if cfg.tie == "max_height":
        return max(options, key=lambda s: (bay.height(s), -s))
    return options[-1] if cfg.tie == "last" else options[0]


def _argmax(bay: Bay, options: list[int], score, cfg: GreedyConfig,
            rng: random.Random) -> int:
    best = max(score(s) for s in options)
    tied = [s for s in options if score(s) == best]
    return _pick(tied, cfg, rng, bay)


def select_stack_rc(bay: Bay, c: int, src: int, forbidden: set[int],
                    cfg: GreedyConfig, rng: random.Random) -> int:
    """Task 1 of ``RR(bay, i)``: the blocking container is a rolled container."""
    S = bay.ins.S
    open_stacks = [s for s in range(S) if s != src and not bay.is_full(s)]
    if not open_stacks:
        raise NoFeasibleStack(f"no stack can host container {c}")

    rolled = [s for s in open_stacks if bay.is_rolled_stack(s)]
    empty = [s for s in open_stacks if bay.is_empty(s)]
    if cfg.rc_prefer == "rolled":
        r1 = rolled or empty            # cluster the RCs first (Section 6.6)
    else:
        r1 = empty or rolled
    if r1:
        return _pick(r1, cfg, rng, bay)
    r2 = [s for s in open_stacks if not (forbidden & set(bay.stacks[s]))]
    if r2:
        return _pick(r2, cfg, rng, bay)
    return _pick(open_stacks, cfg, rng, bay)


def _choose_by_se(bay: Bay, options: list[int], c: int, cfg: GreedyConfig,
                  rng: random.Random) -> int:
    """Rules R1/R2 of Task 2: pick a drop-off stack from ``options`` via ``se``."""
    if cfg.oc_rule == "best_fit":
        ce = bay.ce(c)
        fits = [s for s in options if bay.se(s) > ce]
        if fits:
            return _argmin(bay, fits, bay.se, cfg, rng)
        return _argmax(bay, options, bay.se, cfg, rng)
    if cfg.oc_rule == "min_se":
        return _argmin(bay, options, bay.se, cfg, rng)
    return _argmax(bay, options, bay.se, cfg, rng)


def _argmin(bay: Bay, options: list[int], score, cfg: GreedyConfig,
            rng: random.Random) -> int:
    best = min(score(s) for s in options)
    tied = [s for s in options if score(s) == best]
    return _pick(tied, cfg, rng, bay)


def select_stack_oc(bay: Bay, c: int, src: int, cfg: GreedyConfig,
                    rng: random.Random) -> int:
    """Task 2 of ``RR(bay, i)``: the blocking container is an ordinary container."""
    S = bay.ins.S
    open_stacks = [s for s in range(S) if s != src and not bay.is_full(s)]
    if not open_stacks:
        raise NoFeasibleStack(f"no stack can host container {c}")
    # S_RC of the paper: the text says both "stacks that contain at least one RC"
    # and "non-empty stacks and non-rolled stacks" (= stacks with at least one
    # OC).  Both readings are implemented; see docs/ERRATA.md.
    if cfg.oc_pool == "include_all":
        s_oc = list(open_stacks)
    elif cfg.oc_pool == "include_rolled":
        s_oc = [s for s in open_stacks if not bay.is_empty(s)]
    elif cfg.oc_pool == "has_rc":
        s_oc = [s for s in open_stacks
                if any(c >= bay.ins.O for c in bay.stacks[s])]
    else:
        s_oc = [s for s in open_stacks if bay.has_oc(s)]

    if s_oc:
        not_bad = [s for s in s_oc if not would_be_bad(bay, c, s)]
        if not_bad and cfg.deadlock_in_stack:
            oracle = DeadlockOracle(bay, c)
            r1 = [s for s in not_bad if not oracle.creates_deadlock(s)]
            if r1:
                return _choose_by_se(bay, r1, c, cfg, rng)
        if not_bad:                                   # R2
            return _choose_by_se(bay, not_bad, c, cfg, rng)
        g = bay.ins.group[c]                          # R3
        return _argmax(bay, s_oc, lambda s: bay.se_group(s, g), cfg, rng)

    r4 = [s for s in open_stacks if bay.is_empty(s) or bay.is_rolled_stack(s)]
    return _pick(r4 or open_stacks, cfg, rng, bay)


# --------------------------------------------------------------------------- #
def construct(ins: Instance, cfg: GreedyConfig | None = None,
              bay: Bay | None = None, moves: list[Move] | None = None) -> list[Move]:
    """Algorithm 1 -- also serves as ``Greedy_Randomized_Construction`` and,
    with ``deadlock_in_stack=False``, as ``Greedy_Randomized_noRRDL``.

    ``bay``/``moves`` allow completing a partial solution (needed by the LNS).
    """
    cfg = cfg or GreedyConfig()
    rng = random.Random(cfg.seed)
    bay = bay if bay is not None else Bay(ins)
    moves = moves if moves is not None else []

    _auto_retrieve(bay, moves)
    while not bay.done():
        cand = bay.candidates()
        target = select_target(bay, cand, cfg, rng)
        src = bay.where(target)
        others = set(cand) - {target}
        # the container that becomes a candidate right after this retrieval
        g = ins.group[target]
        nxt = ins.container_by_gp.get((g, ins.prio[target] + 1))
        forbidden = others | ({nxt} if nxt is not None else set())

        for blocker in reversed(bay.blockers_above(target)):
            if blocker >= ins.O:
                dst = select_stack_rc(bay, blocker, src, forbidden, cfg, rng)
            else:
                dst = select_stack_oc(bay, blocker, src, cfg, rng)
            moves.append(Move(RELOCATE, blocker, src, dst, target))
            bay.relocate(blocker, dst)

        moves.append(Move(RETRIEVE, target, src, None, target))
        bay.retrieve(target)
        _auto_retrieve(bay, moves)
    return moves


def greedy(ins: Instance, **kw) -> list[Move]:
    return construct(ins, GreedyConfig.paper(**kw))
