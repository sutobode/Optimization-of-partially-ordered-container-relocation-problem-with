"""Tests for the paired procedure reported in Sections 6.2 and 6.5."""
import pytest

from pocrp_rc.evaluation.statistics import paired_significance


def test_paired_significance_rejects_unpaired_samples():
    with pytest.raises(ValueError):
        paired_significance([1, 2, 3], [1, 2])


def test_paired_significance_handles_identical_samples():
    result = paired_significance([1, 2, 3, 4], [1, 2, 3, 4])
    assert result.p_value == 1.0
    assert result.marker == ""


def test_paired_significance_finds_a_clear_difference():
    result = paired_significance(
        [20, 21, 22, 23, 24, 25, 26, 27],
        [1, 2, 3, 4, 5, 6, 7, 8])
    assert result.mean_difference == 19.0
    assert result.p_value < 0.01
    assert result.marker == "**"
