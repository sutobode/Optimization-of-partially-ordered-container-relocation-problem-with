"""Fast end-to-end smoke test on the smallest published instance."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RAW_20 = ROOT / "data_raw" / "ex195" / "每组前五个（195个）"
RAW_0 = ROOT / "data_raw" / "exrc" / "不同比例RC数据集" / "0%RC数据集"
RAW_10 = ROOT / "data_raw" / "exrc" / "不同比例RC数据集" / "10%RC数据集"
RAW_30 = ROOT / "data_raw" / "exrc" / "不同比例RC数据集" / "30%RC数据集"
GEN_20 = ROOT / "data_gen" / "20pct"


def count_instances(path: Path) -> int:
    return len(tuple(path.glob("*.pro"))) if path.is_dir() else 0


def main() -> int:
    expected = {
        "raw 0%": (RAW_0, 1560),
        "raw 10%": (RAW_10, 1560),
        "raw 20% released": (RAW_20, 195),
        "raw 30%": (RAW_30, 1560),
        "generated 20%": (GEN_20, 1560),
    }
    print("Dataset availability:")
    ok = True
    for label, (path, wanted) in expected.items():
        actual = count_instances(path)
        good = actual == wanted
        ok &= good
        print(f"  {'OK' if good else 'FAIL':4s} {label:18s} {actual}/{wanted} files")

    files = sorted(RAW_20.glob("*.pro"))
    if not files:
        print("FAIL no published 20% instance is available")
        return 1
    # Filename fields are S-T-G-C-OC-RC-ID; choose the smallest C subset.
    instance = min(
        files,
        key=lambda p: (
            int(p.stem.split("-")[4]),
            int(p.stem.split("-")[1]),
            int(p.stem.split("-")[-1]),
        ),
    )
    print(f"\nSmoke instance: {instance.relative_to(ROOT)}")

    # AL builds the benchmark-sized absolute-location model; it is covered by
    # the dedicated tiny-case model checker instead of this fast CLI smoke.
    algorithms = ["random", "greedy", "grasp", "exact", "bnb", "rl"]
    for algorithm in algorithms:
        command = [
            sys.executable,
            str(ROOT / "main.py"),
            str(instance),
            "--algorithm",
            algorithm,
            "--time-limit",
            "30",
            "--max-nodes",
            "100000",
            "--json",
        ]
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=90,
                encoding="utf-8",
            )
        except subprocess.TimeoutExpired:
            ok = False
            print(f"  FAIL {algorithm:6s} timed out after 90s")
            continue
        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout)
                detail = f"objective={payload.get('objective')}"
            except json.JSONDecodeError:
                good = False
                detail = "invalid JSON output"
            else:
                good = payload.get("instance") == instance.stem
                if not good:
                    detail = f"wrong instance={payload.get('instance')}"
            ok &= good
            print(f"  {'OK' if good else 'FAIL':4s} {algorithm:6s} {detail}")
        else:
            ok = False
            error = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "no stderr"
            print(f"  FAIL {algorithm:6s} exit={result.returncode}: {error}")

    print("\nSmoke test: PASS" if ok else "\nSmoke test: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
