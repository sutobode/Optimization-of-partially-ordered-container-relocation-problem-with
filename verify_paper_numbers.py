# -*- coding: utf-8 -*-
"""Verify the numeric claims I made about Tables 5, 10, 11, 12 and the typos."""
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
t = open("paper_text.txt", encoding="utf-8").read()
flat = re.sub(r"\s+", " ", t)


def has(s):
    return re.sub(r"\s+", " ", s) in flat


print("=" * 72)
print("H. Numbers I quoted from the paper")
checks = {
    "Table5 avg row (149.89 / 57.46 / 54.22 / 2,938.01 / 63.8%)":
        "Avg. 149.89 57.46 54.22 2,938.01   63.8%",
    "Table5 C=390 S=74 Greedy time 34,081.70":
        "561.60 479.30 223.08 34,081.70",
    "Table11 avg row (54.22 / 339.46 / 50.66 / 20,441.75 / 6.0%)":
        "40 54.22 339.46 50.66 20,441.75   6.0%",
    "Table11 C=390 S=74 Greedy time 2,593.43":
        "223.08 2,593.43 210.63 388,684.20",
    "Table10 avg row (3.05 / 2,689 / 3.25 / 9.6 / 3.23 / 25.78)":
        "Avg. 3.05 2,689 3.25 9.6 3.23 25.78 6.6% 5.7%",
    "Greedy optimal 80% (32 out of 40)": "80% of all instances (32 out of 40)",
    "GRASP optimal 82.5% (33 out of 40)": "82.5% of all instances (33 out of 40)",
    "Table12 avg row (57.78 / 53.57 / 50.66 / 48.91)": "Avg. 57.78 53.57 50.66 48.91",
    "Tuned max-iteration = 10": "we set max-iteration = 10",
    "Tuned hood-num = 10": "we set hood-num = 10 in subsequent experiments",
    "Tuned NOIMPRMENT = 3": "we set NOIMPRMENT = 3 in subsequent experiments",
    "1560 instances / 39 subsets / 40 each": "consists of 1560 instances, which are divided into 39 sub",
    "small 10-50, medium 54-150, large 170-390": "10 – 50 containers as small",
    "RL model solves 40/40 on 10x8x2x3x6x3 in 5.74s": "10 8 2 3 6 3 0 > 3,600 40 5.74",
    "AL model solves nothing": "the AL model fails to produce results for any",
}
for k, v in checks.items():
    print(f"  [{'OK ' if has(v) else 'FAIL'}] {k}")

print("\n" + "=" * 72)
print("I. Claimed typos / omissions")
typos = {
    "RL constraint (10) writes a_{n,c+r,d} instead of a_{n,C+r,d}": "a n , c + r , d",
    "Alg.3 line 8 compares with sol (prose says currSol)": "8 if neighSol < sol then",
    "finalTemperature assigned but never used in Alg.3 body":
        None,   # handled below
    "'ABC' used in rule R1 without definition": "is neither an ABC nor",
    "Table 3 lists INITFIT with no numeric value": "INITFIT Initial fitness value assigned to each type",
}
for k, v in typos.items():
    if v is None:
        body = flat[flat.find("Algorithm 3. Pseudocode for LNS"):]
        body = body[:body.find("19 return currSol")]
        n = body.count("finalTemperature")
        print(f"  [{'OK ' if n == 1 else 'FAIL'}] {k}  (occurrences in Alg.3 = {n}, only the init line)")
    else:
        print(f"  [{'OK ' if has(v) else 'FAIL'}] {k}")

# numeric values that Table 3 declares but never quantifies
print("\n  Parameters declared in Table 3 and whether a value appears anywhere:")
for p in ["max -iteration", "hood-num", "NOIMPRLIMIT", "INITFIT", "INITIALTEMP",
          "FINALTEMP", "M", "k"]:
    pass
for name, pat in [("INITFIT", r"INITFIT\s*=\s*[\d.]+"), ("INITIALTEMP", r"INITIALTEMP\s*=\s*[\d.]+"),
                  ("FINALTEMP", r"FINALTEMP\s*=\s*[\d.]+"), ("alpha", r"α\s*=\s*[\d.]+"),
                  ("beta", r"β\s*=\s*[\d.]+"), ("Boltzmann k", r"k\s*=\s*[\d.]+"),
                  ("Ma", r"M\s*a\s*=\s*[\d.]+"), ("Mb", r"M\s*b\s*=\s*[\d.]+"),
                  ("Mc", r"M\s*c\s*=\s*[\d.]+")]:
    m = re.findall(pat, flat)
    print(f"    {name:12s} value assignment found: {m if m else 'NONE'}")

print("\n" + "=" * 72)
print("J. Table 12 trend per C (0% / 10% / 20% / 30%)")
seg = t[t.find("Table 12"):t.find("From Table 12")]
rows = re.findall(r"^(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", seg, re.M)
print(f"  parsed {len(rows)} rows")
small = [10, 16, 19, 29, 31, 46, 50]
inc = dec = mixed = 0
for r in rows:
    c = int(r[0]); v = [float(x) for x in r[1:]]
    trend = "increasing" if v == sorted(v) else ("decreasing" if v == sorted(v, reverse=True) else "mixed")
    scale = "small" if c <= 50 else ("medium" if c <= 150 else "large")
    print(f"    C={c:3d} {scale:6s} {v}  -> {trend}")
