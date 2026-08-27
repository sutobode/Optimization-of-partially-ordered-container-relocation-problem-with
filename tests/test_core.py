"""Unit tests for the bay state and the structural concepts of Section 5.1."""
import pytest

from pocrp_rc.core.bay import Bay
from pocrp_rc.core.concepts import (DeadlockOracle, deadlock_containers,
                                    deadlock_pairs, is_bad_oc, must_relocate,
                                    rc_blocks_oc, would_be_bad)
from pocrp_rc.core.lower_bounds import lb_forced, lb_forced_plus_deadlock
from pocrp_rc.data.tiny import make


def test_echelons_and_candidates():
    ins = make([["A_2", "A_0"], ["B_1", "A_1"], ["B_0"]], T=3)
    bay = Bay(ins)
    lab = {ins.label(c): c for c in range(ins.C)}
    assert sorted(ins.label(c) for c in bay.candidates()) == ["A_0", "B_0"]
    assert bay.ce(lab["A_0"]) == 1
    assert bay.ce(lab["A_1"]) == 2
    assert bay.ce(lab["A_2"]) == 3
    # retrieving A_0 shifts the whole group down by one echelon
    bay.retrieve(lab["A_0"])
    assert bay.ce(lab["A_1"]) == 1
    assert bay.ce(lab["A_2"]) == 2


def test_stack_echelon_and_rolled_stacks():
    ins = make([["A_1", "A_0"], ["Z", "Z"], []], T=3)
    bay = Bay(ins)
    assert bay.is_rolled_stack(1)
    assert not bay.is_rolled_stack(0)
    assert not bay.is_rolled_stack(2)          # empty is not "rolled"
    assert bay.se(0) == 1                      # holds candidate A_0
    assert bay.se(1) == ins.C + 1              # rolled
    assert bay.se(2) == ins.C + 1              # empty


def test_bad_container_definition():
    # A_1 sits above A_0 of the same group -> A_1 is bad (Definition 2)
    ins = make([["A_0", "A_1"], ["B_0"], []], T=3)
    bay = Bay(ins)
    lab = {ins.label(c): c for c in range(ins.C)}
    assert is_bad_oc(bay, lab["A_1"])
    assert not is_bad_oc(bay, lab["A_0"])
    # the reverse order is fine: A_0 above A_1 is not bad
    ins2 = make([["A_1", "A_0"], ["B_0"], []], T=3)
    bay2 = Bay(ins2)
    lab2 = {ins2.label(c): c for c in range(ins2.C)}
    assert not is_bad_oc(bay2, lab2["A_0"])
    assert not is_bad_oc(bay2, lab2["A_1"])
    # different groups are incomparable under the partial order
    ins3 = make([["A_0", "B_0"], [], []], T=3)
    bay3 = Bay(ins3)
    assert not any(is_bad_oc(bay3, c) for c in range(ins3.O))


def test_rc_above_oc_must_move():
    ins = make([["A_0", "Z"], ["Z"], []], T=3)
    bay = Bay(ins)
    rc_above, rc_alone = bay.stacks[0][1], bay.stacks[1][0]
    assert rc_blocks_oc(bay, rc_above)
    assert not rc_blocks_oc(bay, rc_alone)
    assert must_relocate(bay, rc_above)
    assert lb_forced(bay) == 1


def test_would_be_bad():
    ins = make([["A_0"], ["B_0", "A_1"], ["Z"]], T=3)
    bay = Bay(ins)
    lab = {ins.label(c): c for c in range(ins.C)}
    a1 = lab["A_1"]
    assert would_be_bad(bay, a1, 0)        # A_0 is there and has higher priority
    assert not would_be_bad(bay, a1, 2)    # only an RC there


def test_deadlock_fig3():
    """Fig. 3: A_0 below B_1 and B_0 below A_1, in two stacks."""
    ins = make([["B_0", "A_1"], ["A_0", "B_1"], []], T=3)
    bay = Bay(ins)
    lab = {ins.label(c): c for c in range(ins.C)}
    pairs = deadlock_pairs(bay)
    assert pairs, "the layout of Fig. 3 must be recognised as a deadlock"
    dl = deadlock_containers(bay)
    assert dl == {lab["A_1"], lab["B_1"]}
    assert all(not is_bad_oc(bay, c) for c in dl)
    assert lb_forced(bay) == 0
    assert lb_forced_plus_deadlock(bay) == 1


def test_no_false_deadlock():
    ins = make([["A_0", "A_1"], ["B_0", "B_1"], []], T=3)
    assert deadlock_pairs(Bay(ins)) == []


def test_deadlock_oracle_matches_definition():
    """The incremental oracle must agree with the full recomputation."""
    ins = make([["B_0", "A_1"], ["A_0"], ["B_1"], []], T=3)
    bay = Bay(ins)
    lab = {ins.label(c): c for c in range(ins.C)}
    c = lab["B_1"]
    src = bay.where(c)
    oracle = DeadlockOracle(bay, c)
    for dst in range(ins.S):
        if dst == src or bay.is_full(dst):
            continue
        probe = bay.copy()
        probe.relocate(c, dst)
        assert oracle.creates_deadlock(dst) == (c in deadlock_containers(probe)), dst


def test_deadlock_oracle_matches_full_recomputation_on_many_layouts():
    """Property-check the optimized RR oracle beyond the single Figure-3 case."""
    import random

    labels = ["A_0", "A_1", "B_0", "B_1", "C_0", "C_1"]
    for seed in range(40):
        rng = random.Random(seed)
        rng.shuffle(labels)
        stacks = [labels[i::4] for i in range(4)]
        ins = make(stacks, T=3)
        bay = Bay(ins)
        for src in range(ins.S):
            c = bay.top(src)
            if c is None or c >= ins.O:
                continue
            oracle = DeadlockOracle(bay, c)
            for dst in range(ins.S):
                if dst == src or bay.is_full(dst):
                    continue
                probe = bay.copy()
                probe.relocate(c, dst)
                after = c in deadlock_containers(probe)
                assert oracle.creates_deadlock(dst) == after


def test_bay_key_symmetries():
    a = make([["A_0"], ["B_0"], []], T=3)
    bay = Bay(a)
    # permuting stacks does not change the canonical key
    other = Bay(make([["B_0"], [], ["A_0"]], T=3))
    assert bay.key() == other.key()


def test_instance_rejects_broken_priorities():
    with pytest.raises(ValueError):
        make([["A_0", "A_2"], [], []], T=3)
