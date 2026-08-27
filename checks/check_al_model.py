"""Check 5: AL model vs RL model vs exact solver on tiny instances.

The AL formulation has ``S^2*T^3*C^3*N`` constraints in the worst case, so it is
only tractable on instances far below the benchmark size -- which is exactly
what the paper observes (Table 4: the AL model solves none of the 1560
instances).  Here it is verified for *correctness* on tiny instances and its
size is reported for the smallest benchmark subset.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.setrecursionlimit(100000)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocrp_rc.data.tiny import make                                     # noqa: E402
from pocrp_rc.data.loader import load_instance                          # noqa: E402
from pocrp_rc.exact.brute_force import optimum                         # noqa: E402
from pocrp_rc.models import al_model, rl_model                          # noqa: E402

CASES = [
    ("no relocation needed", [["A_1", "A_0"], ["B_0"], []], 3),
    ("one bad container", [["A_0", "A_1"], ["B_0"], []], 3),
    ("rc on top of an oc", [["A_0", "Z"], ["B_0"], []], 3),
    ("two groups, no relocation", [["A_0"], ["B_0"], ["A_1"]], 3),
    ("deadlock (Fig. 3)", [["B_0", "A_1"], ["A_0", "B_1"], []], 3),
    ("stacked rcs", [["A_1", "Z", "A_0"], ["B_0"], ["Z"]], 3),
]


def main() -> int:
    print(f"{'case':28s} {'exact':>6} {'RL':>4} {'AL':>4} {'AL status':>22} {'sec':>6}  st")
    ok = 0
    for name, layout, T in CASES:
        ins = make(layout, T, name.replace(" ", "_"))
        ex = optimum(ins)
        rl = rl_model.build_and_solve(ins, time_limit=120)
        al = al_model.build_and_solve(ins, time_limit=120, max_constraints=3_000_000)
        good = (rl.objective == ex) and (al.objective == ex)
        ok += good
        print(f"{name:28s} {ex:>6} {str(rl.objective):>4} {str(al.objective):>4} "
              f"{al.status:>22} {al.seconds:>6.1f}  {'OK' if good else 'FAIL'}")

    print("\nmodel size on the smallest benchmark subset (C=10, S=3, T=6, N=8):")
    ins = load_instance(os.path.join("data_raw", "ex195", "每组前五个（195个）",
                                     "Bay-3-6-3-10-8-2-0.pro"))
    size = al_model.estimate_size(ins)
    for k, v in size.items():
        print(f"   AL {k:20s} {v:>15,}")
    N = ins.O
    print(f"   RL variables         {(N+1)*(ins.C+ins.S)*ins.C + N*ins.C:>15,}")
    print(f"   RL constraints (~N*S*C^2) {N*ins.S*ins.C**2:>10,}")
    print(f"\nmatched {ok}/{len(CASES)}")
    return 0 if ok == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
