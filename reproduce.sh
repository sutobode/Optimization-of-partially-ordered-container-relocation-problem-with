#!/usr/bin/env sh
set -eu
target="${1:-test}"
case "$target" in
  test) python -m pytest -q ;;
  table5) python -m pocrp_rc.experiments.run_heuristics --root data_gen/20pct --algos random,greedy,grasp --setting paper ;;
  table12) python -m pocrp_rc.experiments.run_rc_proportions --dataset-mode published --limit-per-subset 40 ;;
  *) echo "usage: $0 [test|table5|table12]" >&2; exit 2 ;;
esac
