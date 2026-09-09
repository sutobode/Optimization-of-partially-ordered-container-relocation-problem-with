# POCRP-RC paper reproduction

Python implementation of the AL and RL formulations, Random, Greedy and GRASP
algorithms from *Optimization of partially ordered container relocation problem
with rolled containers* (Wang et al., 2026).

## Install and test

```powershell
python -m pip install -r requirements.txt
.\reproduce.ps1 test
```

Run the complete deterministic verification gate (tests, dataset
reconstruction, Table 10 exact optima, and heuristic validity) with one
command:

```powershell
.\verify.ps1
```

Run the additional RL and AL model checks when a longer solver run is
acceptable:

```powershell
.\verify.ps1 -Models
```

The equivalent cross-platform command is `python verify.py`; both commands
return a non-zero exit code if any selected check fails.

Before a full run, use the fast end-to-end smoke test on the smallest instance:

```powershell
.\verify.ps1 -Smoke
```

The smoke test exercises the CLI algorithms on the smallest benchmark case;
the AL formulation is checked separately on tiny cases by `python verify.py
--models`.

For the complete dataset inventory, verification scope, expected evidence, and
paper-reproduction limits, read [docs/VERIFICATION.md](docs/VERIFICATION.md).

## Citation

If you use this reproduction code, cite the original paper listed in
`CITATION.cff`.

## Dataset status

The paper uses 39 subsets x 40 instances = 1,560 instances, based on the
Jovanovic et al. (2019) dataset. The repository contains 1,560 raw instances
for 0%, 10%, and 30% RC, the 195 released 20% RC instances (five per subset),
and a separate generated 20% RC set with 1,560 instances. The generated set is
kept separate and is not presented as the authors' original data.

Solve one instance with the paper-faithful standalone Greedy configuration:

```powershell
python main.py "data_raw/ex195/每组前五个（195个）/Bay-3-6-3-10-8-2-0.pro" --algorithm greedy --json
```

Run GRASP with an explicit distinction between runnable assumed parameters and
strict paper-published parameters:

```powershell
python main.py "data_raw/ex195/每组前五个（195个）/Bay-3-6-3-10-8-2-0.pro" --algorithm grasp --json
python main.py "data_raw/ex195/每组前五个（195个）/Bay-3-6-3-10-8-2-0.pro" --algorithm grasp --strict-paper
```

The second command intentionally fails unless the missing GRASP parameter
values are supplied in `config.yaml`, because the paper names those parameters
without publishing their numeric values.

Run the Table 5/11 heuristic comparison:

```powershell
.\reproduce.ps1 table5
```

Run bounded AL/RL model checks for Tables 4 and 10. These defaults use the
micro subset because the paper's full IP runs use a 3,600 s per-instance limit:

```powershell
.\reproduce.ps1 table4
.\reproduce.ps1 table10
```

Run the bounded B&B comparison from Table 11:

```powershell
.\reproduce.ps1 table11
```

Run Table 12 using only released data:

```powershell
.\reproduce.ps1 table12
```

Reproduce a GRASP parameter sweep from Tables 6--9, for example:

```powershell
python -m pocrp_rc.experiments.run_grasp_tuning --study noimpr
```

Run a bounded Table 11 reproduction or inspect an unpublished GRASP parameter:

```powershell
python -m pocrp_rc.experiments.run_table11 --max-c 10 --time-limit 60
python -m pocrp_rc.experiments.run_grasp_sensitivity --parameter alpha --values 1.2,1.5,2.0 --limit 10
```

The paper does not publish several GRASP parameters and releases only five of
the forty 20%-RC instances per subset. See [docs/ERRATA.md](docs/ERRATA.md) and
`config.yaml`; generated data and assumed parameters are never labelled as
exact author settings.

`pocrp_rc.exact.branch_and_bound` implements the time-limited iterative B&B
framework of Section 6.5. The paper does not publish enough implementation
detail to reproduce the authors' exact node ordering or Java runtime.

Implemented benchmark methods from the paper are Random, Greedy, GRASP, AL,
RL, and B&B. The coverage map in `pocrp_rc.experiments.paper_coverage` links
paper sections to implementation modules and verification tests.
