from pocrp_rc.experiments.paper_coverage import (
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
