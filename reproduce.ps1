param(
    [ValidateSet('test', 'table4', 'table5', 'table10', 'table11', 'table12')]
    [string]$Target = 'test'
)

$ErrorActionPreference = 'Stop'
if ($Target -eq 'test') {
    python -m pytest -q
} elseif ($Target -eq 'table4') {
    python -m pocrp_rc.experiments.run_ip_models --root data_raw/ex195 --models rl --max-c 10 --time-limit 60
} elseif ($Target -eq 'table5') {
    python -m pocrp_rc.experiments.run_heuristics --root data_gen/20pct --algos random,greedy,grasp --setting paper
} elseif ($Target -eq 'table10') {
    python -m pocrp_rc.experiments.run_ip_models --root data_raw/ex195 --models rl --include-heuristics --max-c 10 --time-limit 60
} elseif ($Target -eq 'table11') {
    python -m pocrp_rc.experiments.run_table11 --max-c 10 --time-limit 60
} else {
    python -m pocrp_rc.experiments.run_rc_proportions --dataset-mode published --limit-per-subset 40
}
