# Verification and Reproduction Guide

This document is the operational guide for checking the POCRP-RC
implementation. It distinguishes released paper data, reconstructed data, and
tests that check implementation correctness rather than exact author-runtime
reproduction.

## 1. Dataset Status

The paper states that the benchmark has 39 parameter subsets and 40 instances
per subset, for 1,560 instances in total. The source dataset is attributed to
Jovanovic et al. (2019). The original instances contain ordinary containers;
the paper creates rolled-container variants by selecting a proportion of
containers as RCs.

| Dataset | Location | Files | Status |
|---|---|---:|---|
| 0% RC | `data_raw/exrc/.../0%RC...` | 1,560 | released/raw |
| 10% RC | `data_raw/exrc/.../10%RC...` | 1,560 | released/raw |
| 20% RC | `data_raw/ex195/...` | 195 | released subset: first 5 per subset |
| 30% RC | `data_raw/exrc/.../30%RC...` | 1,560 | released/raw |
| 20% RC | `data_gen/20pct` | 1,560 | reconstructed/generated |

The generated 20% set is useful for a full-size run, but it must not be
reported as the authors' original 20% files. The repository currently has
enough data to run every experiment driver, while the publicly released 20%
set is only a five-instance-per-subset subset.

## 2. Recommended Order

Run the fast smoke test first:

```powershell
.\verify.ps1 -Smoke
```

This checks dataset counts and runs the CLI on the smallest published case
(`C=10`). It exercises Random, Greedy, GRASP, exact search, B&B, and RL. The
AL CLI is intentionally excluded because it constructs the benchmark-sized
absolute-location model; AL correctness is checked on tiny cases in the model
profile. The equivalent cross-platform command is `python verify.py --smoke`.

Run the deterministic verification gate:

```powershell
python verify.py
```

This runs:

1. The complete pytest suite.
2. Dataset RC-count and reconstruction checks.
3. Exact-solver checks against the five released Table 10 instances.
4. Random/Greedy solution validity and lower-bound checks.

Run the additional model checks:

```powershell
python verify.py --models
```

This repeats the deterministic gate and adds RL checks on the five Table 10
instances plus AL/RL checks on six tiny cases. The PowerShell equivalents are
`./verify.ps1` and `./verify.ps1 -Models`.

All commands return exit code 0 only when every selected check passes.

## 3. Expected Evidence

A healthy smoke run ends with `Smoke test: PASS`. A healthy full run ends with
`All selected verification checks passed.` Typical confirmed checkpoints are:

- pytest: 174 passed;
- generated 20% data: 1,560 files;
- published 20% data: 195 files;
- generator reconstruction: 195/195;
- exact Table 10 checkpoint: 5/5;
- RL Table 10 checkpoint: 5/5;
- AL/RL tiny cases: 6/6.

Small timing differences and heuristic objective differences are expected
across machines. The validity and optimum checks are the pass/fail criteria;
the paper's Java runtime and exact heuristic random stream are not reproduced.

## 4. Paper-to-Code Coverage

The implementation covers the following paper components:

- Section 3: POCRP-RC semantics, bay state, validator, and restricted retrieval.
- Sections 4.2-4.3: absolute-location IP model.
- Section 4.4: relative-location IP model.
- Section 5.1: bad containers, deadlocks, and lower bounds.
- Section 5.2: Greedy Algorithm 1.
- Section 5.3: GRASP Algorithms 2-4.
- Section 6.2: Random benchmark.
- Section 6.3: GRASP parameter studies.
- Section 6.4: RL versus heuristic comparison.
- Section 6.5: iterative B&B framework.
- Section 6.6: RC-proportion study.

The machine-readable map is in
`pocrp_rc/experiments/paper_coverage.py`. The corresponding implementation
and test files are listed in that map and in `tests/`.

## 5. Reproduction Boundaries

The following points are intentionally explicit:

- Several GRASP parameters are named but not numerically published. Their
  compatibility values are in `config.yaml` under `grasp.assumptions` and are
  not claimed to be author settings.
- `--strict-paper` refuses to run GRASP until those unpublished values are
  supplied explicitly.
- The paper's B&B description does not specify enough node-ordering and
  implementation detail to reproduce the authors' Java runtime exactly.
- The released 20% data does not contain all 40 instances per subset; generated
  replacements are labelled and kept separate.
- The benchmark in Sections 6.1-6.6 compares AL, RL, Random, Greedy, GRASP,
  and B&B. Surveyed methods without POCRP-RC benchmark inputs are not silently
  treated as baselines.

For the full list of ambiguities and reconstructed interpretations, see
`docs/ERRATA.md`.

## 6. Full Experiment Drivers

After smoke and verification pass, use bounded experiment commands first:

```powershell
.\reproduce.ps1 table4
.\reproduce.ps1 table5
.\reproduce.ps1 table10
.\reproduce.ps1 table11
.\reproduce.ps1 table12
```

The defaults are deliberately bounded. The paper used a 3,600-second
per-instance model limit, so a full benchmark run can be long and should be
started only after the smoke and verification gates pass.
