# -*- coding: utf-8 -*-
"""Verify claims about the POCRP-RC dataset published by Wang et al. (2026)."""
import os, re, sys, glob, collections
sys.stdout.reconfigure(encoding="utf-8")

ROOTS = {
    "20": r"data_raw/ex195/每组前五个（195个）",
    "0":  r"data_raw/exrc/不同比例RC数据集/0%RC数据集",
    "10": r"data_raw/exrc/不同比例RC数据集/10%RC数据集",
    "30": r"data_raw/exrc/不同比例RC数据集/30%RC数据集",
}

FNAME = re.compile(r"Bay-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)\.pro$")


def parse(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    lines = [l.rstrip() for l in txt.splitlines()]
    hdr = {}
    stacks = []
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        if l.startswith("Stack "):
            i += 1
            toks = lines[i].split() if i < len(lines) else []
            stacks.append(toks)          # bottom -> top as written
        elif l and not l[0].isdigit() and l != "Yard Bay":
            key = l
            if i + 1 < len(lines) and lines[i + 1].strip().isdigit():
                hdr[key] = int(lines[i + 1].strip())
                i += 1
        i += 1
    return hdr, stacks


def meta(path):
    m = FNAME.search(os.path.basename(path))
    S, T, G, C, OC, RC, idx = map(int, m.groups())
    return dict(S=S, T=T, G=G, C=C, OC=OC, RC=RC, id=idx)


def check_set(name, root):
    files = sorted(glob.glob(os.path.join(root, "*.pro")))
    subsets = collections.Counter()
    problems = []
    for f in files:
        mm = meta(f)
        hdr, stacks = parse(f)
        subsets[(mm["C"], mm["OC"], mm["RC"], mm["S"], mm["T"], mm["G"])] += 1
        flat = [c for s in stacks for c in s]
        # header consistency
        if hdr.get("Number Of Containers") != mm["C"]:
            problems.append((f, "C mismatch header"))
        if hdr.get("Number Of Yard Stacks") != mm["S"]:
            problems.append((f, "S mismatch header"))
        if hdr.get("MaxTier of Yard Stacks") != mm["T"]:
            problems.append((f, "T mismatch header"))
        if hdr.get("Number of Vessel Stacks") != mm["G"]:
            problems.append((f, "G mismatch header"))
        if hdr.get("Number Of Export Containers") != mm["OC"]:
            problems.append((f, "OC mismatch header"))
        if hdr.get("Number Of Shutout Containers") != mm["RC"]:
            problems.append((f, "RC mismatch header"))
        # layout consistency
        if len(flat) != mm["C"]:
            problems.append((f, f"container count {len(flat)} != {mm['C']}"))
        if len(stacks) != mm["S"]:
            problems.append((f, f"stack count {len(stacks)} != {mm['S']}"))
        if any(len(s) > mm["T"] for s in stacks):
            problems.append((f, "stack exceeds T"))
        if len(set(flat)) != len(flat):
            problems.append((f, "duplicate container id"))
        rc = [c for c in flat if c.startswith("Z_")]
        oc = [c for c in flat if not c.startswith("Z_")]
        if len(rc) != mm["RC"] or len(oc) != mm["OC"]:
            problems.append((f, f"OC/RC split {len(oc)}/{len(rc)}"))
        # groups contiguous 0..k-1
        grp = collections.defaultdict(list)
        for c in oc:
            g, p = c.split("_")
            grp[g].append(int(p))
        for g, ps in grp.items():
            if sorted(ps) != list(range(len(ps))):
                problems.append((f, f"group {g} priorities not contiguous: {sorted(ps)}"))
        if len(grp) > mm["G"]:
            problems.append((f, f"#groups {len(grp)} > G {mm['G']}"))
    return files, subsets, problems


print("=" * 70)
print("A. Structural check of every published instance")
summary = {}
for name, root in ROOTS.items():
    files, subsets, problems = check_set(name, root)
    summary[name] = (files, subsets, problems)
    fill = 0.0
    print(f"\n[{name}% RC]  files={len(files)}  distinct subsets={len(subsets)}  "
          f"instances/subset={sorted(set(subsets.values()))}  problems={len(problems)}")
    for p in problems[:5]:
        print("   PROBLEM", p)

print("\n" + "=" * 70)
print("B. Subset parameter grid vs Table 5 of the paper")
TABLE5 = [(10,8,2,3,6,3),(16,12,4,3,8,3),(16,12,4,4,6,3),(19,15,4,4,8,5),(19,15,4,5,6,5),
          (29,23,6,6,8,5),(29,23,6,8,6,5),(31,24,7,6,8,3),(31,24,7,8,6,3),(46,36,10,9,6,3),
          (46,36,10,12,8,3),(50,40,10,10,8,10),(50,40,10,13,6,10),(54,43,11,11,8,5),
          (54,43,11,14,6,5),(70,56,14,14,8,10),(70,56,14,18,6,10),(79,63,16,15,8,5),
          (79,63,16,20,6,5),(94,75,19,18,8,15),(94,75,19,24,6,15),(120,96,24,23,8,10),
          (120,96,24,30,6,10),(124,99,25,24,8,15),(124,99,25,31,6,15),(150,120,30,29,8,20),
          (150,120,30,38,6,20),(170,136,34,32,8,10),(170,136,34,43,6,10),(190,152,38,36,8,20),
          (190,152,38,48,6,20),(199,159,40,38,8,15),(199,159,40,50,6,15),(274,219,55,52,8,15),
          (274,219,55,69,6,15),(290,232,58,55,8,20),(290,232,58,73,6,20),(390,312,78,74,8,20),
          (390,312,78,98,6,20)]
got20 = set(summary["20"][1].keys())
exp = set(TABLE5)
print(f"Table 5 subsets = {len(exp)} ; 20%-set subsets = {len(got20)}")
print("missing from dataset:", sorted(exp - got20))
print("extra in dataset  :", sorted(got20 - exp))
print("\nRC counts: RC == round(0.2*C) for every Table-5 row? ",
      all(rc == round(0.2 * c) for c, oc, rc, s, t, g in TABLE5))
print("fill rate C/(S*T): min=%.3f max=%.3f mean=%.3f" % (
    min(c/(s*t) for c,oc,rc,s,t,g in TABLE5),
    max(c/(s*t) for c,oc,rc,s,t,g in TABLE5),
    sum(c/(s*t) for c,oc,rc,s,t,g in TABLE5)/len(TABLE5)))

print("\n" + "=" * 70)
print("C. Is the 20% set derivable from the 0% set? (RC-marking + renumbering)")


def key_of(path):
    m = meta(path)
    return (m["S"], m["T"], m["G"], m["C"], m["id"])


zero_by_key = {}
for f in summary["0"][0]:
    m = meta(f)
    zero_by_key[(m["S"], m["T"], m["G"], m["C"], m["id"])] = f

matched = mismatched = nofile = 0
examples = []
for f in summary["20"][0]:
    m = meta(f)
    k = (m["S"], m["T"], m["G"], m["C"], m["id"])
    zf = zero_by_key.get(k)
    if zf is None:
        nofile += 1
        continue
    _, s20 = parse(f)
    _, s0 = parse(zf)
    # same shape?
    shape_ok = [len(x) for x in s20] == [len(x) for x in s0]
    # positions of RCs in the 20% layout
    zpos = {(i, j) for i, st in enumerate(s20) for j, c in enumerate(st) if c.startswith("Z_")}
    # remove those positions from the 0% layout, then renumber per group
    if shape_ok:
        kept = [[c for j, c in enumerate(st) if (i, j) not in zpos] for i, st in enumerate(s0)]
        grp = collections.defaultdict(list)
        for st in kept:
            for c in st:
                g, p = c.split("_")
                grp[g].append(int(p))
        remap = {}
        for g, ps in grp.items():
            for new, old in enumerate(sorted(set(ps))):
                remap[(g, old)] = new
        rebuilt = [[f"{c.split('_')[0]}_{remap[(c.split('_')[0], int(c.split('_')[1]))]}"
                    for c in st] for st in kept]
        target = [[c for c in st if not c.startswith("Z_")] for st in s20]
        if rebuilt == target:
            matched += 1
        else:
            mismatched += 1
            if len(examples) < 3:
                examples.append((os.path.basename(f), os.path.basename(zf), s0, s20, rebuilt, target))
    else:
        mismatched += 1
        if len(examples) < 3:
            examples.append((os.path.basename(f), os.path.basename(zf), s0, s20, "shape", "mismatch"))

print(f"20% instances checked against 0% counterpart: matched={matched} "
      f"mismatched={mismatched} no-counterpart={nofile}")
for e in examples:
    print("  EXAMPLE MISMATCH:", e[0], "vs", e[1])
    print("    0% :", e[2])
    print("    20%:", e[3])
    print("    rebuilt:", e[4])
    print("    target :", e[5])
