"""Golden tests against the numbers published in the paper."""
import glob
import os
import re

import pytest

from pocrp_rc.core.validator import validate
from pocrp_rc.data.generator import derives_from, n_rolled
from pocrp_rc.data.loader import load_instance, write_instance
from pocrp_rc.exact.brute_force import optimum, solve_exact
from pocrp_rc.heuristics.greedy import GreedyConfig, construct

# Table 10 of the paper: proven optima of subset 10x8x2x3x6x3, IDs 1..5
TABLE10_FIRST5 = [1, 3, 5, 2, 6]


def _subset(root: str, pattern: str):
    files = sorted(glob.glob(os.path.join(root, pattern)),
                   key=lambda p: int(re.search(r"-(\d+)\.pro", p).group(1)))
    return [load_instance(p) for p in files]


def test_exact_solver_matches_table10(data20):
    inss = _subset(data20, "Bay-3-6-3-10-8-2-*.pro")
    assert len(inss) == 5
    got = []
    for ins in inss:
        value, moves = solve_exact(ins)
        assert validate(ins, moves) == value
        got.append(value)
    assert got == TABLE10_FIRST5


def test_greedy_is_optimal_on_the_smallest_subset(data20):
    """The paper's Greedy is 6.6 % above the optimum here (3.25 vs 3.05)."""
    inss = _subset(data20, "Bay-3-6-3-10-8-2-*.pro")
    for ins, opt in zip(inss, TABLE10_FIRST5):
        got = validate(ins, construct(ins, GreedyConfig.profile("literal")))
        assert got == opt


def test_dataset_headers_are_consistent(data20):
    for path in sorted(glob.glob(os.path.join(data20, "*.pro"))):
        ins = load_instance(path)                 # __post_init__ does the checks
        m = re.search(r"Bay-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-", os.path.basename(path))
        S, T, G, C, O, RC = map(int, m.groups())
        assert (ins.S, ins.T, ins.G, ins.C, ins.O, ins.n_rc) == (S, T, G, C, O, RC)
        assert ins.n_rc == n_rolled(ins.C, 0.2)


def test_rc_count_rule_is_ceil():
    assert n_rolled(16, 0.2) == 4        # round() would give 3
    assert n_rolled(31, 0.2) == 7        # round() would give 6
    assert n_rolled(46, 0.2) == 10       # round() would give 9
    assert n_rolled(10, 0.2) == 2


def test_generator_reproduces_published_instances(data20, data00):
    """Every published 20 %-RC instance is derivable from a 0 %-RC instance."""
    zero = {}
    for path in sorted(glob.glob(os.path.join(data00, "Bay-3-6-3-10-*.pro"))):
        ins = load_instance(path)
        zero.setdefault((ins.C, ins.S, ins.T), []).append(ins)
    targets = _subset(data20, "Bay-3-6-3-10-8-2-*.pro")
    assert targets
    for target in targets:
        pool = zero[(target.C, target.S, target.T)]
        assert any(derives_from(target, base) for base in pool), target.name


def test_write_then_read_roundtrip(data20, tmp_path):
    ins = _subset(data20, "Bay-3-6-3-10-8-2-0.pro")[0]
    path = os.path.join(str(tmp_path), ins.name + ".pro")
    write_instance(ins, path)
    back = load_instance(path)
    assert (back.C, back.O, back.S, back.T, back.G) == (ins.C, ins.O, ins.S, ins.T, ins.G)
    assert [[back.label(c) for c in st] for st in back.layout] == \
           [[ins.label(c) for c in st] for st in ins.layout]
    assert optimum(back) == optimum(ins)
