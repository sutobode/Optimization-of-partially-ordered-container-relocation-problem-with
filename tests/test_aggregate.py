import json
from pocrp_rc.evaluation.aggregate import aggregate


def test_aggregate_and_paired_comparison():
    rows = []
    for i in range(5):
        rows += [{"instance_id": str(i), "algorithm": "greedy", "objective": 5+i},
                 {"instance_id": str(i), "algorithm": "grasp", "objective": 4+i}]
    out = aggregate(rows, "greedy")
    assert out["methods"]["grasp"]["mean"] < out["methods"]["greedy"]["mean"]
    assert out["paired_vs_baseline"]["grasp"]["n"] == 5


def test_aggregate_retains_timeout_count():
    out = aggregate([{"algorithm": "x", "objective": 1}, {"algorithm": "x", "timeout": True}], None)
    assert out["records"] == 2
    assert out["methods"]["x"]["timeouts"] == 1
