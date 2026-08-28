# Paper ambiguities and implementation assumptions

This file separates statements reproduced from the paper from choices needed
to make the implementation executable.

## Greedy stack set

Section 5.2.3 describes `S_RC` both as stacks containing an RC and as non-empty,
non-rolled stacks. These descriptions are contradictory. The implementation
keeps both readings as profiles. The `paper` profile uses the literal
"contains at least one RC" reading.

## Undefined ABC term

Rule R1 refers to an `ABC`, which is not defined in the paper. The
implementation interprets it as a bad container because the accompanying prose
says R1 avoids bad containers and deadlocks.

## GRASP values absent from the paper

The paper does not publish numerical values for `INITFIT`, `INITIALTEMP`,
`FINALTEMP`, alpha, beta, or Boltzmann constant `k`. Values for `Ma`, `Mb`, and
`Mc` occur only in the Figure 4 illustration. `config.yaml` records these as
unpublished and separately lists compatibility assumptions. Results depending
on those assumptions are not claimed to be exact author-code reproduction.

The official dataset URL printed in the paper was checked. It provides the
released `.rar` data archives but no author implementation or supplemental
GRASP parameter file. For this reason `grasp_config_from_paper()` refuses to
build a strict GRASP configuration unless those values are explicitly supplied.

## Printed formulation issues

RL constraint (10) uses `c+r` where its semantics require artificial container
`C+r`. RL constraint (20) is duplicated/truncated in the typeset paper. AL
constraint (15) contains an unbound tier index. The model module docstrings
record the reconstructions used here.

## Dataset availability

The released 20%-RC data contains the first five instances of each of 39
subsets, not all 40 used in Sections 6.1--6.5. Generated replacements are
labelled generated data and are not treated as the authors' original instances.

## Branch-and-bound runtime

Section 6.5 says the B&B framework is similar to Tanaka and Voss (2019), but it
does not publish complete node ordering, dominance, or implementation details.
The Python B&B reproduces exactness, time limits, bounds and incumbent behavior;
its runtime is not claimed to match the authors' Java implementation.

## SOTA benchmark scope

Section 2 surveys earlier CRP/POCRP literature, but the computational benchmark
in Sections 6.1--6.6 compares only AL, RL, Random, Greedy, GRASP, and a B&B
framework similar to Tanaka and Voss (2019). The other cited methods are not
given POCRP-RC experimental inputs or results in this paper, so they are not
implemented as benchmark baselines in this reproduction.
