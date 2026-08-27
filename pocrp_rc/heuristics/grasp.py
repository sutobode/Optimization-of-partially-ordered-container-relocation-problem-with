"""GRASP of Section 5.3 (Algorithms 2, 3 and 4).

Structure

* ``grasp``          -- Algorithm 2: multi-start over randomised constructions
* ``lns``            -- Algorithm 3: neighbourhood search with a Metropolis
                        acceptance criterion and an adaptive fitness per poor
                        move type
* ``neigh_gene``     -- Algorithm 4: locate the poor moves, pick one by roulette
                        wheel, truncate the solution and complete it with
                        ``Greedy_Randomized_noRRDL``

Poor move criteria (Section 5.3.3)

* (1.1) a container relocated more than ``Ma`` times   -> its *first* relocation
* (1.2) a retrieval that needed more than ``Mb``       -> the *last* relocation
        relocations                                       of the retrieved
                                                          container itself
* (2.1) the target that induced a poor relocation      -> poor target
* (2.2) a target that needed more than ``Mc``          -> poor target
        relocations

Only ``Ma = 2``, ``Mb = 3``, ``Mc = 3`` appear in the paper, and only as
"suppose" values of the Fig. 4 illustration; ``INITFIT``, ``INITIALTEMP``,
``FINALTEMP``, ``alpha``, ``beta`` and the Boltzmann constant ``k`` are never
given a value anywhere in the paper.  The defaults below were chosen here; see
docs/ERRATA.md.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from ..core.bay import Bay
from ..core.instance import Instance, Move, RELOCATE, RETRIEVE, n_relocations
from .greedy import GreedyConfig, construct

# poor move types, used as indices into the fitness array
POOR_RELOC_REPEATED = 0     # criterion 1.1
POOR_RELOC_EXPENSIVE = 1    # criterion 1.2
POOR_TARGET_INDUCED = 2     # criterion 2.1
POOR_TARGET_EXPENSIVE = 3   # criterion 2.2
N_POOR_TYPES = 4


@dataclass
class GraspConfig:
    # Section 6.3: the only parameters the paper reports tuned values for
    max_iteration: int = 10
    hood_num: int = 10
    noimpr_limit: int = 3
    # Fig. 4 "suppose" values
    ma: int = 2
    mb: int = 3
    mc: int = 3
    # never quantified in the paper
    initfit: float = 1.0
    alpha: float = 1.5
    initial_temp: float = 2.0
    final_temp: float = 0.01
    beta: float = 0.9
    k: float = 1.0
    greedy: GreedyConfig | None = None

    def base(self) -> GreedyConfig:
        """Tuned setting (B) selected in Section 6.3.1 for GRASP."""
        return self.greedy or GreedyConfig.profile("literal")


# --------------------------------------------------------------------------- #
# poor move detection
# --------------------------------------------------------------------------- #
def find_poor_moves(moves: list[Move], cfg: GraspConfig) -> list[tuple[int, int]]:
    """Return ``[(index, poor_move_type)]`` for the current solution."""
    n_reloc_of: dict[int, int] = {}
    first_reloc_of: dict[int, int] = {}
    last_reloc_of: dict[int, int] = {}
    reloc_for_target: dict[int, list[int]] = {}
    retrieval_index: dict[int, int] = {}

    for i, m in enumerate(moves):
        if m.kind == RELOCATE:
            n_reloc_of[m.container] = n_reloc_of.get(m.container, 0) + 1
            first_reloc_of.setdefault(m.container, i)
            last_reloc_of[m.container] = i
            reloc_for_target.setdefault(m.target, []).append(i)
        else:
            retrieval_index[m.container] = i

    poor: dict[int, int] = {}

    # (1.1) a container that is relocated too often -- blame its first relocation
    for c, n in n_reloc_of.items():
        if n > cfg.ma:
            poor.setdefault(first_reloc_of[c], POOR_RELOC_REPEATED)

    # (1.2) an expensive retrieval -- blame the last relocation of the target
    #       itself (it was dropped in a bad place earlier)
    for target, idxs in reloc_for_target.items():
        if len(idxs) > cfg.mb and target in last_reloc_of:
            j = last_reloc_of[target]
            if j < retrieval_index.get(target, len(moves)):
                poor.setdefault(j, POOR_RELOC_EXPENSIVE)

    # (2.1) the target that induced a poor relocation is a poor target
    for idx, kind in list(poor.items()):
        if moves[idx].kind == RELOCATE:
            t = moves[idx].target
            ti = retrieval_index.get(t)
            if ti is not None:
                poor.setdefault(ti, POOR_TARGET_INDUCED)

    # (2.2) a target that needed too many relocations
    for target, idxs in reloc_for_target.items():
        if len(idxs) > cfg.mc:
            ti = retrieval_index.get(target)
            if ti is not None:
                poor.setdefault(ti, POOR_TARGET_EXPENSIVE)

    return sorted(poor.items())


# --------------------------------------------------------------------------- #
def _replay(ins: Instance, moves: list[Move]) -> Bay:
    bay = Bay(ins)
    for m in moves:
        if m.kind == RELOCATE:
            bay.relocate(m.container, m.dst)
        else:
            bay.retrieve(m.container)
    return bay


def _roulette(items: list[tuple[int, int]], fitness: list[float],
              rng: random.Random) -> tuple[int, int]:
    weights = [max(fitness[t], 1e-9) for _, t in items]
    total = sum(weights)
    r = rng.random() * total
    acc = 0.0
    for (idx, t), w in zip(items, weights):
        acc += w
        if r <= acc:
            return idx, t
    return items[-1]


def neigh_gene(ins: Instance, sol: list[Move], cfg: GraspConfig,
               fitness: list[float], rng: random.Random
               ) -> tuple[Optional[list[Move]], int]:
    """Algorithm 4."""
    poor = find_poor_moves(sol, cfg)
    if not poor:
        return None, -1
    idx, ptype = _roulette(poor, fitness, rng)

    rcfg = GreedyConfig(randomized=True, deadlock_in_target=cfg.base().deadlock_in_target,
                        deadlock_in_stack=False,          # noRRDL
                        rc_mode=cfg.base().rc_mode, rc_prefer=cfg.base().rc_prefer,
                        tie=cfg.base().tie, oc_rule=cfg.base().oc_rule,
                        tr_rule=cfg.base().tr_rule, oc_pool=cfg.base().oc_pool,
                        seed=rng.randrange(1 << 30))

    if sol[idx].kind == RELOCATE:
        prefix = sol[:idx]                       # keep the first idx-1 moves
        bay = _replay(ins, prefix)
        if prefix and prefix[-1].kind == RELOCATE:
            # the interrupted retrieval has to be finished first (Algorithm 4,
            # lines 9-12): relocate the remaining blockers with the randomised
            # RR that skips the deadlock computation, then retrieve the target
            target = prefix[-1].target
            prefix = list(prefix)
            _finish_retrieval(ins, bay, prefix, target, rcfg, rng)
    else:
        # poor target: rewind to just after the previous retrieval
        prev = idx - 1
        while prev >= 0 and sol[prev].kind != RETRIEVE:
            prev -= 1
        prefix = sol[:prev + 1]
        bay = _replay(ins, prefix)

    moves = list(prefix)
    construct(ins, rcfg, bay=bay, moves=moves)
    return moves, ptype


def _finish_retrieval(ins: Instance, bay: Bay, moves: list[Move], target: int,
                      rcfg: GreedyConfig, rng: random.Random) -> None:
    from .greedy import select_stack_oc, select_stack_rc
    if bay.where(target) < 0:
        return
    src = bay.where(target)
    cand = set(bay.candidates()) - {target}
    g = ins.group[target]
    nxt = ins.container_by_gp.get((g, ins.prio[target] + 1))
    forbidden = cand | ({nxt} if nxt is not None else set())
    for blocker in reversed(bay.blockers_above(target)):
        if blocker >= ins.O:
            dst = select_stack_rc(bay, blocker, src, forbidden, rcfg, rng)
        else:
            dst = select_stack_oc(bay, blocker, src, rcfg, rng)
        moves.append(Move(RELOCATE, blocker, src, dst, target))
        bay.relocate(blocker, dst)
    moves.append(Move(RETRIEVE, target, src, None, target))
    bay.retrieve(target)


# --------------------------------------------------------------------------- #
def lns(ins: Instance, sol: list[Move], cfg: GraspConfig,
        rng: random.Random) -> list[Move]:
    """Algorithm 3.

    The pseudocode compares ``neighSol`` with ``sol`` on line 8 while the
    surrounding text says ``currSol``; we follow the text.
    """
    cur = sol
    cur_val = n_relocations(cur)
    noimpr = 0
    fitness = [cfg.initfit] * N_POOR_TYPES
    temperature = cfg.initial_temp

    while noimpr < cfg.noimpr_limit:
        neigh, ptype = neigh_gene(ins, cur, cfg, fitness, rng)
        if neigh is None:
            break
        val = n_relocations(neigh)
        if val < cur_val:
            cur, cur_val = neigh, val
            fitness[ptype] *= cfg.alpha
            noimpr = 0
        else:
            if temperature > cfg.final_temp:
                p = math.exp(-(val - cur_val) / (cfg.k * temperature))
                if rng.random() < p:
                    cur, cur_val = neigh, val
            noimpr += 1
            temperature *= cfg.beta
    return cur


def grasp(ins: Instance, cfg: GraspConfig | None = None,
          seed: Optional[int] = None) -> list[Move]:
    """Algorithm 2."""
    cfg = cfg or GraspConfig()
    rng = random.Random(seed)
    best: Optional[list[Move]] = None
    best_val = 1 << 30

    rand_cfg_base = cfg.base()
    for _ in range(cfg.max_iteration):
        rcfg = GreedyConfig(randomized=True,
                            deadlock_in_target=rand_cfg_base.deadlock_in_target,
                            deadlock_in_stack=rand_cfg_base.deadlock_in_stack,
                            rc_mode=rand_cfg_base.rc_mode,
                            rc_prefer=rand_cfg_base.rc_prefer,
                            tie=rand_cfg_base.tie, oc_rule=rand_cfg_base.oc_rule,
                            tr_rule=rand_cfg_base.tr_rule,
                            oc_pool=rand_cfg_base.oc_pool,
                            seed=rng.randrange(1 << 30))
        sol = construct(ins, rcfg)
        val = n_relocations(sol)
        for _ in range(cfg.hood_num):
            new = lns(ins, sol, cfg, rng)
            nv = n_relocations(new)
            if nv < val:
                sol, val = new, nv
        if val < best_val:
            best, best_val = sol, val
    assert best is not None
    return best
