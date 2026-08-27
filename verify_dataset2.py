# -*- coding: utf-8 -*-
"""Follow-up verification: 30%-set anomaly, RC rounding rule, 20%-vs-0% derivation."""
import os, re, sys, glob, collections, math
sys.stdout.reconfigure(encoding="utf-8")

ROOTS = {
    "20": r"data_raw/ex195/每组前五个（195个）",
    "0":  r"data_raw/exrc/不同比例RC数据集/0%RC数据集",
    "10": r"data_raw/exrc/不同比例RC数据集/10%RC数据集",
    "30": r"data_raw/exrc/不同比例RC数据集/30%RC数据集",
}
FNAME = re.compile(r"Bay-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)\.pro$")


def meta(path):
    S, T, G, C, OC, RC, idx = map(int, FNAME.search(os.path.basename(path)).groups())
    return dict(S=S, T=T, G=G, C=C, OC=OC, RC=RC, id=idx)


def parse(path):
    lines = [l.rstrip() for l in open(path, encoding="utf-8", errors="replace")]
    stacks, i = [], 0
    while i < len(lines):
        if lines[i].strip().startswith("Stack "):
            i += 1
            stacks.append(lines[i].split() if i < len(lines) else [])
        i += 1
    return stacks


print("=" * 72)
print("D. The 30% set: why 48 'subsets'?")
by_geom = collections.defaultdict(collections.Counter)
for f in sorted(glob.glob(os.path.join(ROOTS["30"], "*.pro"))):
    m = meta(f)
    by_geom[(m["C"], m["S"], m["T"], m["G"])][(m["OC"], m["RC"])] += 1
for geom, cnt in sorted(by_geom.items()):
    if len(cnt) > 1:
        c = geom[0]
        print(f"  C={geom[0]} S={geom[1]} T={geom[2]} G={geom[3]}  -> OC/RC variants {dict(cnt)}"
              f"   0.3*C={0.3*c:.1f} floor={math.floor(0.3*c)} ceil={math.ceil(0.3*c)}")
print(f"  distinct geometries = {len(by_geom)} (expected 39)")

print("\n" + "=" * 72)
print("E. RC-count rule per proportion (round vs ceil vs floor)")
for p in ["10", "20", "30"]:
    rows = {}
    for f in glob.glob(os.path.join(ROOTS[p], "*.pro")):
        m = meta(f)
        rows.setdefault(m["C"], set()).add(m["RC"])
    frac = int(p) / 100
    ok_round = ok_ceil = ok_floor = True
    for c, rcs in rows.items():
        for rc in rcs:
            ok_round &= (rc == round(frac * c))
            ok_ceil &= (rc == math.ceil(frac * c))
            ok_floor &= (rc == math.floor(frac * c))
    print(f"  {p}%: distinct C={len(rows)}  all==round:{ok_round}  all==ceil:{ok_ceil}  all==floor:{ok_floor}")
    bad = {c: sorted(r) for c, r in sorted(rows.items()) if any(x != math.ceil(frac*c) for x in r)}
    if bad:
        print("     C with RC != ceil(frac*C):", bad)

print("\n" + "=" * 72)
print("F. Table 5 grid vs dataset grid, per C (S,T) pairs")
TABLE5_ST = collections.defaultdict(set)
for c, oc, rc, s, t, g in [(10,8,2,3,6,3),(16,12,4,3,8,3),(16,12,4,4,6,3),(19,15,4,4,8,5),
    (19,15,4,5,6,5),(29,23,6,6,8,5),(29,23,6,8,6,5),(31,24,7,6,8,3),(31,24,7,8,6,3),
    (46,36,10,9,6,3),(46,36,10,12,8,3),(50,40,10,10,8,10),(50,40,10,13,6,10)]:
    TABLE5_ST[c].add((s, t))
ds_ST = collections.defaultdict(set)
for f in glob.glob(os.path.join(ROOTS["20"], "*.pro")):
    m = meta(f)
    if m["C"] <= 50:
        ds_ST[m["C"]].add((m["S"], m["T"]))
for c in sorted(TABLE5_ST):
    same = TABLE5_ST[c] == ds_ST[c]
    print(f"  C={c:3d}  paper={sorted(TABLE5_ST[c])}  dataset={sorted(ds_ST[c])}  match={same}"
          f"   fill(paper)={[round(c/(s*t),3) for s,t in sorted(TABLE5_ST[c])]}"
          f"  fill(data)={[round(c/(s*t),3) for s,t in sorted(ds_ST[c])]}")

print("\n" + "=" * 72)
print("G. Can each 20% instance be derived from SOME 0% instance of the same subset?")


def derive(stacks0, zpos):
    kept = [[c for j, c in enumerate(st) if (i, j) not in zpos] for i, st in enumerate(stacks0)]
    grp = collections.defaultdict(set)
    for st in kept:
        for c in st:
            g, p = c.split("_")
            grp[g].add(int(p))
    remap = {}
    for g, ps in grp.items():
        for new, old in enumerate(sorted(ps)):
            remap[(g, old)] = new
    return [[f"{c.split('_')[0]}_{remap[(c.split('_')[0], int(c.split('_')[1]))]}" for c in st]
            for st in kept]


zero_by_subset = collections.defaultdict(list)
for f in glob.glob(os.path.join(ROOTS["0"], "*.pro")):
    m = meta(f)
    zero_by_subset[(m["C"], m["S"], m["T"], m["G"])].append(f)

found = notfound = 0
detail = collections.Counter()
for f in sorted(glob.glob(os.path.join(ROOTS["20"], "*.pro"))):
    m = meta(f)
    s20 = parse(f)
    zpos = {(i, j) for i, st in enumerate(s20) for j, c in enumerate(st) if c.startswith("Z_")}
    target = [[c for c in st if not c.startswith("Z_")] for st in s20]
    shape = [len(st) for st in s20]
    hit = None
    for zf in zero_by_subset[(m["C"], m["S"], m["T"], m["G"])]:
        s0 = parse(zf)
        if [len(st) for st in s0] != shape:
            continue
        if derive(s0, zpos) == target:
            hit = zf
            break
    if hit:
        found += 1
        detail[m["C"]] += 1
    else:
        notfound += 1
print(f"  derivable = {found}/195 ; not derivable = {notfound}")
print(f"  derivable per C: {dict(sorted(detail.items()))}")
