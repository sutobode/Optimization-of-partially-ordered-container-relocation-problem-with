# Baseline and SOTA scope

The paper's Section 6 experiments benchmark Random, Greedy, GRASP, AL, RL and
an iterative B&B framework. These are the directly supported comparison
methods in this repository.

Methods mentioned only in the literature review are not automatically SOTA
baselines: they must have a compatible POCRP-RC implementation, identical
instance set, objective, stopping rule and time budget. Until those conditions
are met they are reported as **not reproducible**, never assigned fabricated
numbers, and never included in a comparative claim.

The proposed method may be claimed superior only after the server run produces
raw results for the same instances and seeds, followed by the statistical
analysis described in `SERVER_EXPERIMENT_GUIDE.md`.
