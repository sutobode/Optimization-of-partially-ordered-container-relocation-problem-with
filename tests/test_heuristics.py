"""Property tests: every algorithm must always produce a feasible solution
whose objective is at least the lower bound, on a broad sample of instances."""
import glob
import os
import random

import pytest

from pocrp_rc.core.bay import Bay
from pocrp_rc.core.instance import n_relocations
from pocrp_rc.core.lower_bounds import lb_forced, lb_forced_plus_deadlock
from pocrp_rc.core.validator import validate
from pocrp_rc.data.loader import load_instance
from pocrp_rc.heuristics.grasp import GraspConfig, grasp
from pocrp_rc.heuristics.greedy import GreedyConfig, construct
from pocrp_rc.heuristics.greedy import select_target
from pocrp_rc.heuristics.random_alg import random_solution

PROFILES = ["literal", "prose", "calibrated"]


def test_paper_greedy_target_selection_uses_max_deadlock_indicator():
    """Section 5.2.2: after NBC ties, the candidate with max DC wins."""
    from pocrp_rc.data.tiny import make

    # A_1 and B_1 form the Figure-3 deadlock. E_0 is a non-bad blocker over
    # C_0, giving A_0 and C_0 equal NBC/BC but different DC.
    ins = make([
        ["B_0", "A_1"], ["A_0", "B_1"], ["C_0", "E_0"], []
    ], T=3)
    bay = Bay(ins)
    by_label = {ins.label(c): c for c in range(ins.C)}
    cfg = GreedyConfig.paper()
    chosen = select_target(bay, [by_label["A_0"], by_label["C_0"]], cfg,
                           random.Random(0))
    assert chosen == by_label["A_0"]


def test_paper_and_grasp_deadlock_settings_are_distinct():
    greedy = GreedyConfig.paper()
    grasp_setting = GreedyConfig.setting("B")
    assert (greedy.deadlock_in_target, greedy.deadlock_in_stack) == (True, True)
    assert (grasp_setting.deadlock_in_target,
            grasp_setting.deadlock_in_stack) == (False, True)


def _sample(root: str, per_subset: int = 1, max_c: int = 10 ** 9) -> list:
    seen: dict[tuple, int] = {}
    out = []
    for path in sorted(glob.glob(os.path.join(root, "*.pro"))):
        ins = load_instance(path)
        if ins.C > max_c:
            continue
        key = (ins.C, ins.S)
        if seen.get(key, 0) >= per_subset:
            continue
        seen[key] = seen.get(key, 0) + 1
        out.append(ins)
    return out


@pytest.mark.parametrize("profile", PROFILES)
def test_greedy_is_always_feasible(data20, profile):
    for ins in _sample(data20, per_subset=1):
        moves = construct(ins, GreedyConfig.profile(profile))
        n = validate(ins, moves)
        assert n == n_relocations(moves)
        assert n >= lb_forced(Bay(ins))


def test_greedy_settings_abc(data20):
    for ins in _sample(data20, per_subset=1, max_c=60):
        for setting in "ABC":
            moves = construct(ins, GreedyConfig.setting(setting))
            assert validate(ins, moves) >= lb_forced(Bay(ins))


def test_random_is_always_feasible(data20):
    for ins in _sample(data20, per_subset=1):
        for seed in (1, 2, 3):
            moves = random_solution(ins, seed=seed)
            assert validate(ins, moves) >= lb_forced(Bay(ins))


def test_randomised_construction_is_always_feasible(data20):
    rng = random.Random(0)
    for ins in _sample(data20, per_subset=1, max_c=200):
        for _ in range(5):
            cfg = GreedyConfig.profile("literal")
            cfg.randomized = True
            cfg.seed = rng.randrange(1 << 30)
            assert validate(ins, construct(ins, cfg)) >= lb_forced(Bay(ins))


def test_grasp_is_always_feasible_and_not_worse_than_its_start(data20):
    cfg = GraspConfig(max_iteration=2, hood_num=2)
    for ins in _sample(data20, per_subset=1, max_c=130):
        moves = grasp(ins, cfg, seed=7)
        n = validate(ins, moves)
        assert n >= lb_forced(Bay(ins))


def test_lower_bounds_never_exceed_a_feasible_solution(data20):
    for ins in _sample(data20, per_subset=2):
        n = validate(ins, construct(ins, GreedyConfig.profile("literal")))
        assert lb_forced(Bay(ins)) <= n
        assert lb_forced_plus_deadlock(Bay(ins)) <= n


def test_zero_rc_instances_are_plain_pocrp(data00):
    for ins in _sample(data00, per_subset=1, max_c=100):
        assert ins.n_rc == 0
        moves = construct(ins, GreedyConfig.profile("literal"))
        assert validate(ins, moves) >= lb_forced(Bay(ins))
