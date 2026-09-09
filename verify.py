"""Run the reproducibility verification suite from one stable entry point.

The default profile is deterministic and covers the unit/integration tests,
dataset reconstruction, exact Table 10 optima, and heuristic validity. Model
solver checks are opt-in because their runtime depends on the local OR-Tools
installation and available CPU time.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_step(label: str, command: list[str], env: dict[str, str]) -> bool:
    """Run one verification step and preserve its output and exit status."""
    print(f"\n{'=' * 72}\n{label}\n$ {' '.join(command)}\n{'=' * 72}", flush=True)
    started = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    elapsed = time.perf_counter() - started
    status = "PASS" if result.returncode == 0 else f"FAIL (exit {result.returncode})"
    print(f"[{status}] {label} ({elapsed:.1f}s)", flush=True)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the POCRP-RC implementation and paper checkpoints."
    )
    parser.add_argument(
        "--models",
        action="store_true",
        help="also run RL and AL model checks (can be substantially slower)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run only the fast dataset and CLI end-to-end smoke test",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help="extra arguments passed to pytest, after '--pytest-args'",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    if args.smoke:
        passed = run_step(
            "Smoke test on the smallest published instance",
            [sys.executable, "checks/smoke_test.py"],
            env,
        )
        return 0 if passed else 1

    steps: list[tuple[str, list[str]]] = [
        (
            "1. Python test suite",
            [sys.executable, "-m", "pytest", "-q", *(args.pytest_args or [])],
        ),
        ("2. Dataset structure and RC-count rules", [sys.executable, "checks/check_generator.py"]),
        ("3. Exact solver against Table 10", [sys.executable, "checks/check_exact.py"]),
        ("4. Random/Greedy validity and lower bounds", [sys.executable, "checks/check_greedy_random.py"]),
    ]
    if args.models:
        steps.extend(
            [
                ("5. RL model checkpoint", [sys.executable, "checks/check_rl_model.py"]),
                ("6. AL/RL model checkpoint", [sys.executable, "checks/check_al_model.py"]),
            ]
        )

    results = [run_step(label, command, env) for label, command in steps]
    passed = sum(results)
    print(f"\nVerification summary: {passed}/{len(results)} steps passed.")
    if not all(results):
        print("One or more checks failed. Review the section immediately above the summary.")
        return 1
    print("All selected verification checks passed.")
    if not args.models:
        print("Model checks were not run; use: python verify.py --models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
