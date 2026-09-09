# Final implementation gap analysis

This document records what is verified by the repository and what still
requires server-scale execution. It is intentionally conservative: passing
unit tests is not evidence of an empirical improvement claim.

## Verified in the repository

- POCRP-RC state semantics, restricted retrieval, validator and lower bounds:
  `pocrp_rc/core/` and `tests/`.
- Greedy, Random and GRASP implementations:
  `pocrp_rc/heuristics/`.
- AL and RL formulations and solution decoding:
  `pocrp_rc/models/`.
- Exact and time-limited B&B solvers:
  `pocrp_rc/exact/`.
- Five released Table 10 instances and tiny AL/RL cross-checks:
  `python verify.py --models`.

## Requires server execution

- Full 1,560-instance runs for every RC proportion and every method.
- Full 3,600-second-per-instance AL/RL/B&B comparison.
- Multiple-seed statistical analysis and paper tables/figures.
- Any empirical claim that the proposed method is better than a baseline.

## Reproduction limits

The released 20% dataset contains 195 instances, not the full 1,560. Several
GRASP parameters and implementation details are not numerically specified in
the paper. They must remain marked as assumed/reconstructed unless an official
supplement supplies them. See `ERRATA.md` and `BASELINE_SCOPE.md`.
