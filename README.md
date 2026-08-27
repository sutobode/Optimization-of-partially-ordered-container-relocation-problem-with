# POCRP-RC paper reproduction

Python implementation of the AL and RL formulations, Random, Greedy and GRASP
algorithms from *Optimization of partially ordered container relocation problem
with rolled containers* (Wang et al., 2026).

## Install and test

```powershell
python -m pip install -r requirements.txt
.\reproduce.ps1 test
```

Solve one instance with the paper-faithful standalone Greedy configuration:

```powershell
python main.py "data_raw/ex195/每组前五个（195个）/Bay-3-6-3-10-8-2-0.pro" --algorithm greedy --json
```

Run the Table 5/11 heuristic comparison:

```powershell
.\reproduce.ps1 table5
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
