param(
    [ValidateSet('test', 'table5', 'table12')]
    [string]$Target = 'test'
)

$ErrorActionPreference = 'Stop'
if ($Target -eq 'test') {
    python -m pytest -q
} elseif ($Target -eq 'table5') {
    python -m pocrp_rc.experiments.run_heuristics --root data_gen/20pct --algos random,greedy,grasp --setting paper
} else {
    python -m pocrp_rc.experiments.run_rc_proportions --dataset-mode published --limit-per-subset 40
}
