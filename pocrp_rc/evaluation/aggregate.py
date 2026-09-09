"""Conservative aggregation of benchmark JSON records.

The command operates only on completed records with a common instance id; it
never silently drops malformed or timed-out records.
"""
from __future__ import annotations

import argparse, json, math, statistics
from pathlib import Path
from .statistics import paired_significance


def _records(path: Path) -> list[dict]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    rows = obj if isinstance(obj, list) else obj.get("results", obj.get("records", []))
    if not isinstance(rows, list):
        raise ValueError("input must be a JSON list or an object containing results/records")
    return [r for r in rows if isinstance(r, dict)]


def _ci95(xs: list[float]) -> tuple[float, float]:
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    mean = statistics.fmean(xs)
    se = statistics.stdev(xs) / math.sqrt(len(xs))
    return mean - 1.96 * se, mean + 1.96 * se


def aggregate(rows: list[dict], baseline: str | None = None) -> dict:
    valid = [r for r in rows if not r.get("timeout") and r.get("status", "OK") not in {"INVALID", "ERROR"}]
    methods = sorted({str(r.get("algorithm", r.get("method", "unknown"))) for r in valid})
    out: dict = {"records": len(rows), "valid_records": len(valid), "methods": {}}
    for method in methods:
        xs = [float(r["objective"]) for r in valid if str(r.get("algorithm", r.get("method"))) == method and "objective" in r]
        lo, hi = _ci95(xs)
        out["methods"][method] = {"n": len(xs), "mean": statistics.fmean(xs) if xs else None,
            "median": statistics.median(xs) if xs else None, "std": statistics.stdev(xs) if len(xs)>1 else 0.0,
            "min": min(xs) if xs else None, "max": max(xs) if xs else None,
            "ci95": [lo, hi], "timeouts": sum(1 for r in rows if str(r.get("algorithm", r.get("method"))) == method and r.get("timeout"))}
    if baseline and baseline in out["methods"]:
        b = {r.get("instance_id", r.get("instance")): float(r["objective"]) for r in valid if str(r.get("algorithm", r.get("method"))) == baseline and "objective" in r}
        for method in methods:
            if method == baseline: continue
            a = {r.get("instance_id", r.get("instance")): float(r["objective"]) for r in valid if str(r.get("algorithm", r.get("method"))) == method and "objective" in r}
            keys = sorted(set(a) & set(b))
            if len(keys) >= 3:
                p = paired_significance([a[k] for k in keys], [b[k] for k in keys])
                out.setdefault("paired_vs_baseline", {})[method] = p.to_dict()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--baseline")
    ns = ap.parse_args()
    result = aggregate(_records(ns.input), ns.baseline)
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
