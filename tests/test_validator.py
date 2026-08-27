"""The validator must reject every kind of infeasible solution."""
import pytest

from pocrp_rc.core.bay import Bay
from pocrp_rc.core.instance import Move, RELOCATE, RETRIEVE
from pocrp_rc.core.validator import InfeasibleSolution, validate
from pocrp_rc.data.tiny import make
from pocrp_rc.heuristics.greedy import GreedyConfig, construct


@pytest.fixture
def ins():
    return make([["A_0", "A_1"], ["B_0", "Z"], []], T=3)


def test_accepts_a_greedy_solution(ins):
    moves = construct(ins, GreedyConfig.profile("literal"))
    n = validate(ins, moves)
    assert n == sum(1 for m in moves if m.kind == RELOCATE)


def test_rejects_retrieving_a_rolled_container(ins):
    rc = ins.O
    with pytest.raises(InfeasibleSolution, match="RC"):
        validate(ins, [Move(RETRIEVE, rc, 1, None, rc)])


def test_rejects_violating_the_partial_order(ins):
    lab = {ins.label(c): c for c in range(ins.C)}
    a1 = lab["A_1"]
    # A_1 is on top but A_0 (higher priority, same group) is still in the bay
    with pytest.raises(InfeasibleSolution, match="partial order"):
        validate(ins, [Move(RETRIEVE, a1, 0, None, a1)])


def test_rejects_relocation_inside_the_same_stack(ins):
    lab = {ins.label(c): c for c in range(ins.C)}
    a1 = lab["A_1"]
    with pytest.raises(InfeasibleSolution, match="leave its stack"):
        validate(ins, [Move(RELOCATE, a1, 0, 0, lab["A_0"])])


def test_rejects_moving_a_buried_container(ins):
    lab = {ins.label(c): c for c in range(ins.C)}
    with pytest.raises(InfeasibleSolution, match="not on top"):
        validate(ins, [Move(RELOCATE, lab["A_0"], 0, 2, lab["A_0"])])


def test_rejects_unrestricted_relocation():
    """Relocating from a stack other than the target's is the unrestricted version."""
    ins = make([["A_0", "A_1"], ["B_0", "B_1"], []], T=3)
    lab = {ins.label(c): c for c in range(ins.C)}
    moves = [
        Move(RELOCATE, lab["B_1"], 1, 2, lab["A_0"]),   # not above the target
        Move(RELOCATE, lab["A_1"], 0, 2, lab["A_0"]),
        Move(RETRIEVE, lab["A_0"], 0, None, lab["A_0"]),
    ]
    with pytest.raises(InfeasibleSolution, match="restricted version"):
        validate(ins, moves)


def test_rejects_exceeding_the_height_limit():
    ins = make([["A_0", "A_1"], ["B_0", "B_1"], []], T=2)
    lab = {ins.label(c): c for c in range(ins.C)}
    with pytest.raises(InfeasibleSolution, match="full"):
        validate(ins, [Move(RELOCATE, lab["A_1"], 0, 1, lab["A_0"])])


def test_rejects_incomplete_solutions(ins):
    lab = {ins.label(c): c for c in range(ins.C)}
    moves = [Move(RELOCATE, lab["A_1"], 0, 2, lab["A_0"]),
             Move(RETRIEVE, lab["A_0"], 0, None, lab["A_0"])]
    with pytest.raises(InfeasibleSolution, match="never retrieved"):
        validate(ins, moves)


def test_rejects_dangling_relocations(ins):
    lab = {ins.label(c): c for c in range(ins.C)}
    with pytest.raises(InfeasibleSolution, match="no retrieval"):
        validate(ins, [Move(RELOCATE, lab["A_1"], 0, 2, lab["A_0"])])


def test_bay_rejects_illegal_transitions(ins):
    bay = Bay(ins)
    lab = {ins.label(c): c for c in range(ins.C)}
    with pytest.raises(ValueError):
        bay.retrieve(ins.O)                       # a rolled container
    with pytest.raises(ValueError):
        bay.relocate(lab["A_0"], 2)               # buried
    with pytest.raises(ValueError):
        bay.retrieve(lab["A_1"])                  # not a candidate
