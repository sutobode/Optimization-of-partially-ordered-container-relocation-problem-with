"""The checked-in config must preserve paper values and explicit unknowns."""
import pytest

from pocrp_rc.config import (grasp_config_from_paper,
                             grasp_config_with_assumptions, load_config,
                             paper_greedy_config)


def test_checked_in_config_is_loadable():
    config = load_config()
    greedy = paper_greedy_config(config)
    grasp = grasp_config_with_assumptions(config)
    assert greedy.deadlock_in_target and greedy.deadlock_in_stack
    assert (grasp.max_iteration, grasp.hood_num, grasp.noimpr_limit) == (10, 10, 3)
    assert all(value is None for value in config["grasp"]["unpublished"].values())


def test_strict_paper_grasp_refuses_unpublished_values():
    config = load_config()
    with pytest.raises(ValueError, match="does not publish"):
        grasp_config_from_paper(config)
