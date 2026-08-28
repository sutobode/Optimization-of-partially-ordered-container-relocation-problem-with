"""Machine-readable coverage map for the implemented paper components."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperComponent:
    section: str
    name: str
    implementation: str
    verification: str
    status: str = "implemented"


PAPER_COVERAGE: tuple[PaperComponent, ...] = (
    PaperComponent(
        "3",
        "POCRP-RC instance semantics and restricted retrieval rule",
        "pocrp_rc.core.instance, pocrp_rc.core.bay, pocrp_rc.core.validator",
        "tests/test_core.py, tests/test_validator.py",
    ),
    PaperComponent(
        "4.2-4.3",
        "Absolute-location IP model and optimized constraints",
        "pocrp_rc.models.al_model",
        "tests/test_models.py",
    ),
    PaperComponent(
        "4.4",
        "Relative-location IP model",
        "pocrp_rc.models.rl_model",
        "tests/test_models.py, tests/test_golden_paper.py",
    ),
    PaperComponent(
        "5.1",
        "Bad containers, deadlocks, and lower bounds",
        "pocrp_rc.core.concepts, pocrp_rc.core.lower_bounds",
        "tests/test_core.py, tests/test_exact_crosscheck.py",
    ),
    PaperComponent(
        "5.2",
        "Greedy Algorithm 1",
        "pocrp_rc.heuristics.greedy",
        "tests/test_heuristics.py, tests/test_golden_paper.py",
    ),
    PaperComponent(
        "6.2",
        "Random benchmark",
        "pocrp_rc.heuristics.random_alg",
        "tests/test_heuristics.py",
    ),
    PaperComponent(
        "5.3",
        "GRASP Algorithms 2-4",
        "pocrp_rc.heuristics.grasp",
        "tests/test_grasp.py",
    ),
    PaperComponent(
        "6.3",
        "GRASP parameter studies",
        "pocrp_rc.experiments.run_grasp_tuning",
        "tests/test_config.py",
    ),
    PaperComponent(
        "6.4",
        "RL versus Greedy/GRASP Table 10 comparison",
        "pocrp_rc.experiments.run_ip_models, pocrp_rc.experiments.run_heuristics",
        "tests/test_models.py, tests/test_golden_paper.py",
    ),
    PaperComponent(
        "6.5",
        "Iterative branch-and-bound benchmark",
        "pocrp_rc.exact.branch_and_bound, pocrp_rc.experiments.run_table11",
        "tests/test_branch_and_bound.py, tests/test_exact_crosscheck.py",
    ),
    PaperComponent(
        "6.6",
        "Rolled-container proportion study Table 12",
        "pocrp_rc.experiments.run_rc_proportions",
        "tests/test_golden_paper.py",
    ),
)


REQUIRED_BENCHMARK_METHODS = frozenset({
    "random",
    "greedy",
    "grasp",
    "al",
    "rl",
    "bnb",
})

