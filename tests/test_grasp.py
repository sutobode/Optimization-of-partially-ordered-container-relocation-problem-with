"""Tests for the GRASP components of Section 5.3."""
import pytest

from pocrp_rc.core.instance import Move, RELOCATE, RETRIEVE, n_relocations
from pocrp_rc.core.validator import validate
from pocrp_rc.data.tiny import make
from pocrp_rc.heuristics.grasp import (GraspConfig, POOR_RELOC_EXPENSIVE,
                                       POOR_RELOC_REPEATED,
                                       POOR_TARGET_EXPENSIVE,
                                       POOR_TARGET_INDUCED, find_poor_moves,
                                       grasp, lns, neigh_gene)
from pocrp_rc.heuristics.greedy import GreedyConfig, construct


def test_criterion_1_1_blames_the_first_relocation():
    """A container relocated more than Ma times: its first relocation is poor."""
    moves = [
        Move(RELOCATE, 5, 0, 1, 9),      # 0 : first relocation of 5
        Move(RETRIEVE, 9, 0, None, 9),   # 1
        Move(RELOCATE, 5, 1, 2, 8),      # 2
        Move(RETRIEVE, 8, 1, None, 8),   # 3
        Move(RELOCATE, 5, 2, 0, 7),      # 4 : third relocation of 5
        Move(RETRIEVE, 7, 2, None, 7),   # 5
    ]
    poor = dict(find_poor_moves(moves, GraspConfig(ma=2, mb=99, mc=99)))
    assert poor.get(0) == POOR_RELOC_REPEATED
    assert 2 not in poor and 4 not in poor


def test_criterion_2_2_blames_an_expensive_target():
    moves = [Move(RELOCATE, c, 0, 1, 9) for c in (1, 2, 3, 4)]
    moves.append(Move(RETRIEVE, 9, 0, None, 9))
    poor = dict(find_poor_moves(moves, GraspConfig(ma=99, mb=99, mc=3)))
    assert poor.get(4) == POOR_TARGET_EXPENSIVE


def test_criterion_2_1_propagates_to_the_inducing_target():
    moves = [
        Move(RELOCATE, 5, 0, 1, 9),
        Move(RETRIEVE, 9, 0, None, 9),
        Move(RELOCATE, 5, 1, 2, 8),
        Move(RETRIEVE, 8, 1, None, 8),
        Move(RELOCATE, 5, 2, 0, 7),
        Move(RETRIEVE, 7, 2, None, 7),
    ]
    poor = dict(find_poor_moves(moves, GraspConfig(ma=2, mb=99, mc=99)))
    # move 0 is a poor relocation induced by the retrieval of container 9
    assert poor.get(0) == POOR_RELOC_REPEATED
    assert poor.get(1) == POOR_TARGET_INDUCED


def test_criterion_1_2_blames_the_last_relocation_of_the_target():
    moves = [
        Move(RELOCATE, 9, 0, 1, 4),          # 0 : the future target 9 is moved
        Move(RETRIEVE, 4, 0, None, 4),       # 1
        Move(RELOCATE, 1, 1, 2, 9),          # 2 : retrieving 9 now costs 4
        Move(RELOCATE, 2, 1, 2, 9),          # 3
        Move(RELOCATE, 3, 1, 0, 9),          # 4
        Move(RELOCATE, 5, 1, 0, 9),          # 5
        Move(RETRIEVE, 9, 1, None, 9),       # 6
    ]
    poor = dict(find_poor_moves(moves, GraspConfig(ma=99, mb=3, mc=99)))
    assert poor.get(0) == POOR_RELOC_EXPENSIVE


def test_no_poor_move_in_a_relocation_free_solution():
    ins = make([["A_1", "A_0"], ["B_0"], []], T=3)
    moves = construct(ins, GreedyConfig.profile("literal"))
    assert n_relocations(moves) == 0
    assert find_poor_moves(moves, GraspConfig()) == []


@pytest.fixture
def hard_instance():
    return make([["A_0", "B_1", "A_2"], ["B_0", "A_1", "Z"], ["C_0", "Z", "B_2"],
                 []], T=4)


def test_neighbour_generation_returns_feasible_solutions(hard_instance):
    ins = hard_instance
    import random
    rng = random.Random(3)
    # aggressive thresholds so that poor moves certainly exist
    cfg = GraspConfig(ma=0, mb=0, mc=0)
    sol = construct(ins, GreedyConfig.profile("literal"))
    validate(ins, sol)
    assert find_poor_moves(sol, cfg), "expected poor moves with Ma=Mb=Mc=0"
    fitness = [1.0] * 4
    seen = 0
    for _ in range(30):
        neigh, ptype = neigh_gene(ins, sol, cfg, fitness, rng)
        if neigh is None:
            break
        validate(ins, neigh)                       # must stay feasible
        assert 0 <= ptype < 4
        seen += 1
    assert seen > 0


def test_lns_never_worsens_the_returned_solution(hard_instance):
    import random
    ins = hard_instance
    sol = construct(ins, GreedyConfig.profile("literal"))
    out = lns(ins, sol, GraspConfig(), random.Random(11))
    assert validate(ins, out) <= validate(ins, sol)


def test_grasp_is_deterministic_for_a_fixed_seed(hard_instance):
    a = grasp(hard_instance, GraspConfig(max_iteration=3, hood_num=3), seed=42)
    b = grasp(hard_instance, GraspConfig(max_iteration=3, hood_num=3), seed=42)
    assert n_relocations(a) == n_relocations(b)
    assert [str(m) for m in a] == [str(m) for m in b]


def test_grasp_reaches_the_optimum_on_a_tiny_instance(hard_instance):
    from pocrp_rc.exact.brute_force import optimum
    best = grasp(hard_instance, GraspConfig(max_iteration=10, hood_num=5), seed=5)
    assert validate(hard_instance, best) == optimum(hard_instance)
