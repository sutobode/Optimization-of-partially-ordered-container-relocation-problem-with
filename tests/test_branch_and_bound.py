"""Cross-check the iterative B&B against the independent DFS oracle."""
import random

import pytest

from pocrp_rc.core.validator import validate
from pocrp_rc.exact.branch_and_bound import solve_branch_and_bound
from pocrp_rc.exact.brute_force import optimum
from tests.test_exact_crosscheck import random_instance


@pytest.mark.parametrize("seed", range(20))
def test_branch_and_bound_matches_exact_on_random_small_instances(seed):
    ins = random_instance(random.Random(9000 + seed))
    expected = optimum(ins, max_nodes=500_000)
    result = solve_branch_and_bound(ins, time_limit=30)
    assert result.status == "OPTIMAL"
    assert result.bound == result.objective == expected
    assert result.gap == 0.0
    assert validate(ins, result.moves) == expected


def test_branch_and_bound_rejects_nonpositive_time_limit():
    ins = random_instance(random.Random(1))
    with pytest.raises(ValueError):
        solve_branch_and_bound(ins, time_limit=0)
