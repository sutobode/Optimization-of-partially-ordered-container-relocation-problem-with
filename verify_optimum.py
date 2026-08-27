# -*- coding: utf-8 -*-
"""
Exact solver (memoised DFS) for restricted POCRP-RC on tiny instances.
Purpose: validate my reading of the problem semantics against Table 10 of
Wang et al. (2026), which reports proven optima (RL model) for subset
10x8x2x3x6x3, instances ID 1..40  ->  1, 3, 5, 2, 6, ...
"""
import os, re, sys, glob, functools
sys.stdout.reconfigure(encoding="utf-8")
sys.setrecursionlimit(100000)

RC = "Z"          # all rolled containers are interchangeable


def load(path):
    lines = [l.rstrip() for l in open(path, encoding="utf-8", errors="replace")]
    hdr, stacks, i = {}, [], 0
    while i < len(lines):
        l = lines[i].strip()
        if l.startswith("Stack "):
            i += 1
            stacks.append(tuple(lines[i].split()) if i < len(lines) else ())
        elif l and not l[0].isdigit() and l != "Yard Bay":
            if i + 1 < len(lines) and lines[i + 1].strip().isdigit():
                hdr[l] = int(lines[i + 1].strip())
                i += 1
        i += 1
    T = hdr["MaxTier of Yard Stacks"]
    lay = tuple(tuple(RC if c.startswith("Z_") else c for c in st) for st in stacks)
    return lay, T


def canon(layout):
    return tuple(sorted(layout))


def candidates(layout):
    """OCs whose echelon is 1: minimal remaining priority inside their group."""
    best = {}
    for st in layout:
        for c in st:
            if c == RC:
                continue
            g, p = c.split("_")
            p = int(p)
            if g not in best or p < best[g]:
                best[g] = p
    return {f"{g}_{p}" for g, p in best.items()}


def solve(layout, T):
    memo = {}

    def rec(lay, ub):
        """min relocations to retrieve every OC; ub = remaining budget (prune)."""
        cand = candidates(lay)
        if not cand:
            return 0
        key = canon(lay)
        hit = memo.get(key)
        if hit is not None and hit[1] >= ub:
            return hit[0]
        best = ub + 1
        for si, st in enumerate(lay):
            for ti, c in enumerate(st):
                if c not in cand:
                    continue
                k = len(st) - ti - 1                     # blocking containers
                if k >= best:
                    continue
                # enumerate all ways to move the k blockers (top-first) elsewhere
                results = []

                def place(cur, idx, moved):
                    if idx == 0:
                        # target now on top of stack si -> retrieve it
                        new = list(cur)
                        new[si] = new[si][:-1]
                        results.append(tuple(new))
                        return
                    top = cur[si][-1]
                    for dj in range(len(cur)):
                        if dj == si or len(cur[dj]) >= T:
                            continue
                        nxt = list(cur)
                        nxt[si] = nxt[si][:-1]
                        nxt[dj] = nxt[dj] + (top,)
                        place(tuple(nxt), idx - 1, moved + 1)

                place(lay, k, 0)
                seen = set()
                for nl in results:
                    ck = canon(nl)
                    if ck in seen:
                        continue
                    seen.add(ck)
                    sub = rec(nl, best - k - 1)
                    if k + sub < best:
                        best = k + sub
        memo[key] = (best, ub)
        return best

    # iterative deepening on the upper bound
    for ub in range(0, 40):
        v = rec(layout, ub)
        memo.clear()
        if v <= ub:
            return v
    return None


PAPER_TABLE10 = [1, 3, 5, 2, 6, 3, 4, 5, 3, 5]   # IDs 1..10
root = r"data_raw/ex195/每组前五个（195个）"
files = sorted(glob.glob(os.path.join(root, "Bay-3-6-3-10-8-2-*.pro")),
               key=lambda p: int(re.search(r"-(\d+)\.pro$", p).group(1)))
print(f"instances found: {len(files)}")
print("file                          my_optimum  Table10(ID=idx+1)  match")
ok = 0
for f in files:
    idx = int(re.search(r"-(\d+)\.pro$", f).group(1))
    lay, T = load(f)
    opt = solve(lay, T)
    ref = PAPER_TABLE10[idx] if idx < len(PAPER_TABLE10) else None
    m = (opt == ref)
    ok += m
    print(f"  {os.path.basename(f):28s}  {opt:>3}         {ref:>3}             {'OK' if m else 'MISMATCH'}")
print(f"\nmatched {ok}/{len(files)}")
