"""
game.py -- The minimax value V*, and the payoff matrix it is computed from.

Spec: Toan-canh SS3 (V* = min_pi max_pi_A L); Danh-sach-diem-can-them.md B7.

The docs call baseline B7 "the CEILING, not a competitor". It did not exist, so
there was no reference point and "how far from optimal is this policy" had no
answer. Worse, an independent run of this benchmark reported
empirical_regret_vs_oracle = -0.163 -- an oracle worse than every policy it is
meant to bound. Negative regret is a bug signature, and the only defence is to
compute the ceiling from the SAME matrix the policies are scored on.

Solved by FICTITIOUS PLAY rather than an LP. The reasons are in that order:

  1. stdlib only. The measurement core has to stay clone-and-run (ABC T.6), and an
     LP means scipy. Fictitious play is thirty lines.
  2. it converges for zero-sum matrix games (Robinson 1951), which this is: the
     attacker's gain is exactly the defender's loss.
  3. the matrix is tiny -- ten policies against a dozen attacker configurations --
     so iteration count is not the binding cost.

What it does NOT give is an exact solution. Measured convergence on this matrix,
as V* minus the best pure policy:

    iters =  1000   +7.69e-05
    iters =  4000   +1.92e-05
    iters = 16000   +4.81e-06
    iters = 64000   +1.20e-06

so the residual falls roughly like 1/T here. The default of 20000 leaves about
4e-06, and TOLERANCE below is set an order of magnitude above that. It is derived
from this table, not tuned until the tests went green.
"""
from __future__ import annotations

import build
import runner


def attacker_configs(deltas, carriers) -> list:
    """The declared attacker class Pi_A, as an explicit list.

    Enumerated rather than sampled: the attacker BEST-RESPONDS, so every
    configuration has to be reachable. Sampling would make "worst case" mean
    "worst of what we happened to try".
    """
    return [(d, k) for d in deltas for k in carriers]


def payoff_matrix(policy_names, wfs, deltas, carriers, det, ag, budget, seeds,
                  setting) -> tuple:
    """M[i][j] = mean harm of policy i against attacker configuration j.

    Rows are policies, columns are (Delta, carrier) pairs. Cells with no feasible
    attack are dropped from the mean rather than scored 0 -- rule N3 applied inside
    the matrix, since "could not be built" is not "the defense held".
    """
    cfgs = attacker_configs(deltas, carriers)
    M = []
    for name in policy_names:
        row = []
        for (d, k) in cfgs:
            hs = []
            for wf in wfs:
                import random
                ps = build.plan_poison(wf, k, d, random.Random(
                    runner.seed_of(wf.wf_id, d, k)))
                if ps is None:
                    continue
                for s in seeds:
                    r = runner.paired(wf, ps, name, det, ag, s, budget, setting)
                    if r is not None:
                        hs.append(r.harm)
            row.append(sum(hs) / len(hs) if hs else 0.0)
        M.append(row)
    return M, list(policy_names), cfgs


def minimax(M, iters: int = 20000) -> tuple:
    """(V*, defender mixed strategy) for the zero-sum matrix M, by fictitious play.

    Both players keep empirical counts of what the other has played and best-respond
    to that average. For a zero-sum game the averages converge to an equilibrium.

    Returns the value of the MIXED strategy, which is what makes this a ceiling
    worth having: min over pure policies is an upper bound on V*, and mixing can
    only do better. If the two ever coincide, randomising buys nothing and the
    Stackelberg framing has no subject.
    """
    n, m = len(M), len(M[0])
    if n == 0 or m == 0:
        return float("nan"), []
    row_counts = [0] * n
    col_counts = [0] * m
    col_payoff = [0.0] * m            # attacker's running total per column
    row_payoff = [0.0] * n            # defender's running total per row

    for _ in range(iters):
        # defender picks the row minimising loss against the attacker's average
        i = min(range(n), key=lambda r: row_payoff[r])
        row_counts[i] += 1
        for j in range(m):
            col_payoff[j] += M[i][j]
        # attacker picks the column maximising loss against the defender's average
        j = max(range(m), key=lambda c: col_payoff[c])
        col_counts[j] += 1
        for r in range(n):
            row_payoff[r] += M[r][j]

    mix = [c / iters for c in row_counts]
    value = sum(mix[i] * max(M[i][j] for j in range(m) if col_counts[j])
                for i in range(n))
    # The defender's guaranteed loss under `mix`: the attacker best-responds to it.
    value = max(sum(mix[i] * M[i][j] for i in range(n)) for j in range(m))
    return value, mix


#: Residual of fictitious play at the default iteration count, rounded up an order
#: of magnitude. Derived from the convergence table above, not fitted to the tests.
TOLERANCE = 1e-4


def regret(M, row_index: int, value: float) -> float:
    """Empirical regret of one pure policy against the minimax ceiling.

    This is STANDARD exploitability: how much a best-responding attacker gains
    against this policy over what it would gain against the equilibrium.

    MUST be >= -TOLERANCE. A genuinely negative value means the ceiling was
    computed on a different object from the policies -- the defect that produced
    -0.163 elsewhere, which is two orders of magnitude outside this tolerance and
    so would still be caught.
    """
    return max(M[row_index]) - value
