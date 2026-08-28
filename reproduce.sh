#!/usr/bin/env sh
set -eu
target="${1:-test}"
case "$target" in
  test) python -m pytest -q ;;
  table4) python -m pocrp_rc.experiments.run_ip_models --root data_raw/ex195 --models rl --max-c 10 --time-limit 60 ;;
  table5) python -m pocrp_rc.experiments.run_heuristics --root data_gen/20pct --algos random,greedy,grasp --setting paper ;;
  table10) python -m pocrp_rc.experiments.run_ip_models --root data_raw/ex195 --models rl --include-heuristics --max-c 10 --time-limit 60 ;;
  table11) python -m pocrp_rc.experiments.run_table11 --max-c 10 --time-limit 60 ;;
  table12) python -m pocrp_rc.experiments.run_rc_proportions --dataset-mode published --limit-per-subset 40 ;;
  *) echo "usage: $0 [test|table4|table5|table10|table11|table12]" >&2; exit 2 ;;
esac
