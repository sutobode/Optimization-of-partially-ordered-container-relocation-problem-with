from pocrp_rc.experiments.paper_coverage import (
    NOT_EXPERIMENTAL_BENCHMARKS,
    PAPER_COVERAGE,
    REQUIRED_BENCHMARK_METHODS,
)


def test_all_paper_benchmark_methods_are_declared():
    assert REQUIRED_BENCHMARK_METHODS == {
        "random",
        "greedy",
        "grasp",
        "al",
        "rl",
        "bnb",
    }


def test_core_paper_sections_have_implementation_and_verification_entries():
    sections = {component.section for component in PAPER_COVERAGE}
    assert {"3", "4.2-4.3", "4.4", "5.1", "5.2", "5.3", "6.2",
            "6.3", "6.4", "6.5", "6.6"} <= sections
    for component in PAPER_COVERAGE:
        assert component.implementation
        assert component.verification
        assert component.status == "implemented"


def test_non_benchmark_scope_is_explicit():
    assert "Sections 6.1-6.6 benchmark" in NOT_EXPERIMENTAL_BENCHMARKS
    assert "Tanaka" in NOT_EXPERIMENTAL_BENCHMARKS
