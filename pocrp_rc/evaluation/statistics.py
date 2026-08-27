"""Paired significance procedure used in Sections 6.2 and 6.5."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from scipy import stats


@dataclass(frozen=True)
class PairedTestResult:
    """Result of the paper's normality-then-paired-test procedure."""

    n: int
    mean_left: float
    mean_right: float
    mean_difference: float
    normality_p: float
    test: str
    statistic: float
    p_value: float
    marker: str

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


def paired_significance(
    left: Sequence[float],
    right: Sequence[float],
    *,
    alpha: float = 0.05,
    strong_alpha: float = 0.01,
) -> PairedTestResult:
    """Apply Shapiro then paired t-test or Wilcoxon, as in the paper.

    ``left`` and ``right`` must contain per-instance results in identical
    order. A positive mean difference means ``left`` uses more relocations.
    """
    if len(left) != len(right):
        raise ValueError("paired samples must have equal lengths")
    if len(left) < 3:
        raise ValueError("at least three paired observations are required")
    a = [float(x) for x in left]
    b = [float(x) for x in right]
    diff = [x - y for x, y in zip(a, b)]
    constant_difference = all(x == diff[0] for x in diff)
    if constant_difference:
        normality_p = 1.0
        p_value = 1.0 if diff[0] == 0.0 else 0.0
        statistic = 0.0 if diff[0] == 0.0 else float("inf")
        marker = "" if p_value == 1.0 else "**"
        return PairedTestResult(
            n=len(a), mean_left=sum(a) / len(a), mean_right=sum(b) / len(b),
            mean_difference=sum(diff) / len(diff), normality_p=normality_p,
            test="paired_t", statistic=statistic, p_value=p_value,
            marker=marker)
    normality_p = float(stats.shapiro(diff).pvalue)
    if normality_p >= alpha:
        test = "paired_t"
        result = stats.ttest_rel(a, b)
    else:
        test = "wilcoxon_signed_rank"
        if all(x == 0.0 for x in diff):
            statistic, p_value = 0.0, 1.0
            marker = ""
            return PairedTestResult(
                len(a), sum(a) / len(a), sum(b) / len(b), 0.0,
                normality_p, test, statistic, p_value, marker)
        result = stats.wilcoxon(a, b)
    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    marker = "**" if p_value < strong_alpha else ("*" if p_value < alpha else "")
    return PairedTestResult(
        n=len(a), mean_left=sum(a) / len(a), mean_right=sum(b) / len(b),
        mean_difference=sum(diff) / len(diff), normality_p=normality_p,
        test=test, statistic=statistic, p_value=p_value, marker=marker)
