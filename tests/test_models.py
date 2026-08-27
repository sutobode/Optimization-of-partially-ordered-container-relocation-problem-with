"""The two IP models must agree with the exact solver on tiny instances."""
import pytest

from pocrp_rc.data.tiny import make
from pocrp_rc.exact.brute_force import optimum
from pocrp_rc.core.validator import validate

cp_model = pytest.importorskip("ortools.sat.python.cp_model")
from pocrp_rc.models import al_model, rl_model            # noqa: E402

CASES = [
    ("no_relocation", [["A_1", "A_0"], ["B_0"], []], 3),
    ("one_bad_container", [["A_0", "A_1"], ["B_0"], []], 3),
    ("rc_above_oc", [["A_0", "Z"], ["B_0"], []], 3),
    ("independent_groups", [["A_0"], ["B_0"], ["A_1"]], 3),
    ("deadlock_fig3", [["B_0", "A_1"], ["A_0", "B_1"], []], 3),
    ("stacked_rcs", [["A_1", "Z", "A_0"], ["B_0"], ["Z"]], 3),
]


@pytest.mark.parametrize("name,layout,T", CASES)
def test_rl_model_matches_exact(name, layout, T):
    ins = make(layout, T, name)
    res = rl_model.build_and_solve(ins, time_limit=120)
    assert res.status == "OPTIMAL", res.status
    assert res.objective == optimum(ins)
    assert res.moves is not None
    assert validate(ins, res.moves) == res.objective


@pytest.mark.parametrize("name,layout,T", CASES)
def test_al_model_matches_exact(name, layout, T):
    ins = make(layout, T, name)
    res = al_model.build_and_solve(ins, time_limit=180, max_constraints=3_000_000)
    assert res.status == "OPTIMAL", res.status
    assert res.objective == optimum(ins)
    assert res.moves is not None
    assert validate(ins, res.moves) == res.objective


def test_al_model_is_much_larger_than_rl_model():
    """Section 4.5: the AL formulation is S^2*T^3*C^3*N against N*S*C^2."""
    ins = make([["A_0", "A_1", "Z"], ["B_0", "B_1"], ["C_0"]], T=4)
    size = al_model.estimate_size(ins)
    N, C, S = ins.O, ins.C, ins.S
    rl_constraints = N * S * C * C
    assert size["total_estimate"] > 20 * rl_constraints


@pytest.mark.parametrize("layout", [
    [["A_0", "B_1"], ["B_0", "A_1"], ["Z"]],
    [["A_1", "Z"], ["B_0", "A_0"], ["B_1"]],
    [["A_0", "Z"], ["A_1", "B_1"], ["B_0"]],
])
def test_both_models_decode_to_exact_valid_solutions_on_additional_layouts(layout):
    ins = make(layout, T=3)
    expected = optimum(ins)
    for module in (rl_model, al_model):
        result = module.build_and_solve(
            ins, time_limit=120,
            **({"max_constraints": 3_000_000} if module is al_model else {}))
        assert result.status == "OPTIMAL"
        assert result.objective == expected
        assert result.moves is not None
        assert validate(ins, result.moves) == expected
