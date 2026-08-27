"""Cross-validation of every solver against the exact optimum on random
small instances (fuzz test)."""
import random

import pytest

from pocrp_rc.core.bay import Bay
from pocrp_rc.core.instance import Instance
from pocrp_rc.core.lower_bounds import lb_forced, lb_forced_plus_deadlock
from pocrp_rc.core.validator import validate
from pocrp_rc.exact.brute_force import solve_exact
from pocrp_rc.heuristics.grasp import GraspConfig, grasp
from pocrp_rc.heuristics.greedy import GreedyConfig, construct
from pocrp_rc.heuristics.random_alg import random_solution


def random_instance(rng: random.Random) -> Instance:
    S = rng.randint(2, 4)
    T = rng.randint(3, 4)
    n_groups = rng.randint(1, 3)
    capacity = S * T
    C = rng.randint(2, max(2, int(capacity * 0.7)))
    n_rc = rng.randint(0, max(0, C // 3))
    O = C - n_rc
    # split the OCs into groups
    sizes = [0] * n_groups
    for _ in range(O):
        sizes[rng.randrange(n_groups)] += 1
    group, prio = [], []
    for g, size in enumerate(sizes):
        for p in range(size):
            group.append(g)
            prio.append(p)
    keep = [g for g, size in enumerate(sizes) if size]
    remap = {g: i for i, g in enumerate(keep)}
    group = [remap[g] for g in group]
    O = len(group)
    group += [-1] * n_rc
    prio += [-1] * n_rc
    C = O + n_rc

    order = list(range(C))
    rng.shuffle(order)
    stacks: list[list[int]] = [[] for _ in range(S)]
    for c in order:
        options = [s for s in range(S) if len(stacks[s]) < T]
        stacks[rng.choice(options)].append(c)
    return Instance(name="fuzz", S=S, T=T, G=len(keep), C=C, O=O, group=group,
                    prio=prio, layout=tuple(tuple(s) for s in stacks))


@pytest.mark.parametrize("seed", range(60))
def test_all_solvers_respect_the_optimum(seed):
    rng = random.Random(seed)
    ins = random_instance(rng)
    opt, moves = solve_exact(ins, max_nodes=400_000)
    assert validate(ins, moves) == opt

    bay = Bay(ins)
    assert lb_forced(bay) <= opt
    assert lb_forced_plus_deadlock(bay) <= opt

    for profile in ("literal", "prose", "calibrated"):
        got = validate(ins, construct(ins, GreedyConfig.profile(profile)))
        assert got >= opt, f"{profile} beat the optimum"

    assert validate(ins, random_solution(ins, seed=seed)) >= opt
    g = validate(ins, grasp(ins, GraspConfig(max_iteration=3, hood_num=3), seed=seed))
    assert g >= opt


@pytest.mark.parametrize("seed", range(20))
def test_grasp_without_lns_equals_its_single_construction(seed):
    rng = random.Random(1000 + seed)
    ins = random_instance(rng)
    opt, _ = solve_exact(ins, max_nodes=400_000)
    grasp_seed = seed
    construction_seed = random.Random(grasp_seed).randrange(1 << 30)
    expected_cfg = GreedyConfig.profile(
        "literal", randomized=True, seed=construction_seed)
    expected = validate(ins, construct(ins, expected_cfg))
    got = validate(
        ins, grasp(ins, GraspConfig(max_iteration=1, hood_num=0), seed=grasp_seed))
    assert opt <= got == expected
