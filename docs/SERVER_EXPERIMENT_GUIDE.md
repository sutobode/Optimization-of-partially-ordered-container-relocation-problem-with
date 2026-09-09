# Server experiment guide

Do not run the full benchmark on a development laptop. Copy the repository and
the legally distributable dataset to a server, install `requirements.txt`, and
record the commit hash and hardware.

## Preflight (safe)

```bash
python verify.py --smoke
python -m pytest -q
python -m pocrp_rc.experiments.run_heuristics --help
python -m pocrp_rc.experiments.run_ip_models --help
```

## Benchmark protocol

Use one manifest and the same instance list, seed list, and time limit for all
methods. For paper-style exact-model runs use 3600 seconds per instance.
Keep original released data and generated/reconstructed data in separate output
directories. Never overwrite an existing run.

Example server commands:

```bash
python -m pocrp_rc.experiments.run_heuristics --help
python -m pocrp_rc.experiments.run_ip_models --help
python -m pocrp_rc.experiments.run_table11 --help
python -m pocrp_rc.experiments.run_rc_proportions --help
```

Run each command's `--dry-run` first when available, then archive raw JSON/CSV,
logs, config snapshot, manifest and commit hash. Aggregate only after all jobs
finish; timeout and invalid-solution records must remain visible.

For a completed JSON record file, aggregate objective summaries and paired
comparisons without rerunning solvers:

```bash
python -m pocrp_rc.evaluation.aggregate results/raw.json \
  --baseline greedy --output results/summary.json
```

## Claim gate

Run the statistical aggregation and inspect `PUBLICATION_READINESS_REPORT.md`.
Do not claim an improvement over a baseline or SOTA until every method has the
same instance set/protocol and the report contains confidence intervals,
paired tests and effect sizes.
