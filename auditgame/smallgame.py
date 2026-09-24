"""smallgame.py -- small audit games solved EXACTLY, as the ground truth rho needs.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md section on Stage 6 --
"game nho (K*H <= 40 sau roi rac hoa belief), o do pi* tinh duoc ... 240 game
nho = 240 diem do", and rho = max_{pi*} min_{pi in Pi} TV(pi, pi*).

WHY A SEPARATE GAME AT ALL.  On the full benchmark the optimum is not
computable, so "is our policy library close to optimal?" cannot be asked
directly.  The escape is a family of games small enough to solve exactly, where
the same question has an answer.  rho measured on the library against ITSELF --
which is what spikes/rho.json reports as 0.5078 -- answers a different and
weaker question: how spread out the library is, not how far it sits from the
optimum.  This module supplies the optima.

THE GAME.  It is the canonical Stackelberg covering game, stripped to the
structure the benchmark shares with it:

  - K carriers, H tasks, trigger delay Delta, audit budget m (audits, not money).
  - The attacker picks a carrier k and an insertion task iota; the payload is
    live over the window W = {iota, ..., iota + Delta} and is caught iff the
    defender audits carrier k at some task in W.
  - Payoff to the attacker is 1 if it survives its window and 0 if caught; the
    defender minimises the maximum over configurations.

EXACT, AND WHY THE COMPACT FORM IS EXACT HERE.  A defender pure strategy is a
set of (task, carrier) audits, so enumerating them is exponential.  We solve the
COVERAGE MARGINAL form instead -- variables c(t,k), the probability that carrier
k is audited at task t.  For security games whose schedules are singletons (one
audit covers one (task, carrier) cell, at most one audit per task) the marginal
form is exact rather than a relaxation: any marginal vector satisfying the
per-task and budget constraints is implementable as a distribution over pure
strategies (Kiekintveld et al., AAMAS 2009; Korzhyk et al.).  That is the same
compact representation `lp.solve_stackelberg_lp` uses on the full game.

ONE AUDIT PER TASK is the constraint that makes c(t, .) a probability
distribution directly, which is what lets rho be a total variation distance
between per-task action distributions -- the same space the library's own rho
was measured in, so the two numbers are comparable.
"""
from __future__ import annotations

import itertools

import lp

#: The 240 games.  THE COUNT IS A CONSEQUENCE OF THE AXES, not a target: Delta
#: runs over every value the horizon admits (0 .. H-1, since Delta >= H leaves
#: no feasible insertion), which gives 2+3+4+5+6 = 20 (H, Delta) pairs, times 3
#: carrier counts times 4 budgets = 240.  Every cell satisfies the K*H <= 40
#: ceiling the specification sets; the largest here is 4 x 6 = 24.
#:
#: Stating it this way matters: had we capped Delta at some value the grid would
#: have produced 204 and the honest options would have been to report 204 or to
#: pick a cap that reached 240 after seeing the count.
H_VALUES = (2, 3, 4, 5, 6)
K_VALUES = (2, 3, 4)
BUDGET_VALUES = (1, 2, 3, 4)


def games() -> list:
    """Every (H, K, Delta, m) with Delta feasible for the horizon."""
    out = []
    for H, K, m in itertools.product(H_VALUES, K_VALUES, BUDGET_VALUES):
        for d in range(H):
            out.append({"H": H, "K": K, "delta": d, "m": m})
    return out


def configs(H: int, K: int, delta: int) -> list:
    """Attacker pure strategies: (carrier, iota), window {iota..iota+delta}."""
    return [(k, i) for k in range(K) for i in range(H - delta)]


def solve(H: int, K: int, delta: int, m: int) -> dict:
    """Exact minimax coverage and its value.

        maximise  u
        s.t.      u - sum_{t in W(k,i)} c(t,k) <= 0   for every config
                  sum_k c(t,k) <= 1                   for every task
                  sum_{t,k} c(t,k) <= m
                  0 <= c <= 1

    u is the worst-case coverage the defender can guarantee; the attacker's
    value is 1 - min(1, u).  Written as a maximisation with non-negative
    right-hand sides because `lp.simplex_max` requires b >= 0.
    """
    cells = [(t, k) for t in range(H) for k in range(K)]
    idx = {c: j for j, c in enumerate(cells)}
    n = len(cells) + 1                       # c(t,k) ... , u
    u_j = len(cells)

    A, b = [], []
    for (k, i) in configs(H, K, delta):
        row = [0.0] * n
        row[u_j] = 1.0
        for t in range(i, min(i + delta + 1, H)):
            row[idx[(t, k)]] = -1.0
        A.append(row); b.append(0.0)
    for t in range(H):                       # at most one audit per task
        row = [0.0] * n
        for k in range(K):
            row[idx[(t, k)]] = 1.0
        A.append(row); b.append(1.0)
    row = [0.0] * n                          # budget
    for c in cells:
        row[idx[c]] = 1.0
    A.append(row); b.append(float(m))
    for c in cells:                          # c <= 1
        row = [0.0] * n
        row[idx[c]] = 1.0
        A.append(row); b.append(1.0)

    obj = [0.0] * n
    obj[u_j] = 1.0
    x, u = lp.simplex_max(obj, A, b)
    cov = {c: max(0.0, min(1.0, x[idx[c]])) for c in cells}
    return {"coverage": cov, "guaranteed_coverage": u,
            "value": max(0.0, 1.0 - min(1.0, u))}


def per_task(cov: dict, H: int, K: int) -> list:
    """Coverage marginals as one action distribution per task.

    The K+1st entry is "audit nothing at this task", which is what the budget
    not spent buys.  Making it explicit is what keeps the rows probability
    distributions, so TV between two policies is well defined.
    """
    out = []
    for t in range(H):
        row = [cov.get((t, k), 0.0) for k in range(K)]
        out.append(row + [max(0.0, 1.0 - sum(row))])
    return out


def tv(p: list, q: list) -> float:
    """Total variation between two per-task policies, averaged over tasks.

    Averaged rather than maxed over H, matching how the library's own rho was
    measured (tools/measure_rho.py), so the two numbers sit on one scale.
    """
    return sum(0.5 * sum(abs(a - b) for a, b in zip(pt, qt))
               for pt, qt in zip(p, q)) / len(p)


def value_of(cov: dict, H: int, K: int, delta: int) -> float:
    """Attacker value against an ARBITRARY coverage -- its best response."""
    worst = 0.0
    for (k, i) in configs(H, K, delta):
        c = sum(cov.get((t, k), 0.0) for t in range(i, min(i + delta + 1, H)))
        worst = max(worst, 1.0 - min(1.0, c))
    return worst


# ---------------------------------------------------------------- the library
#
# The declared policy class, written directly as coverage marginals so it can be
# evaluated in the same game the optimum is computed in.  These are the
# small-game analogues of the benchmark's baselines, not new inventions:
#   commit_only   spends nothing upstream -- B1
#   uniform       spreads the budget over every cell -- B2
#   earliest      covers the earliest tasks first -- B3 audit-on-insertion
#   single        puts everything on one carrier -- the degenerate focus policy
#   spread_tasks  one carrier per task, cycling -- carrier rotation

def feasible(cov: dict, H: int, K: int, m: int, tol: float = 1e-9) -> bool:
    """Does this coverage respect both constraints the game imposes?

    Exists because a candidate that quietly breaks one of them scores BETTER
    than the exact minimax, and "our library beat the optimum" is a bug report,
    not a result.  `library` asserts it on every member it returns.
    """
    if any(v < -tol or v > 1.0 + tol for v in cov.values()):
        return False
    if sum(cov.values()) > m + tol:
        return False
    for t in range(H):
        if sum(cov.get((t, k), 0.0) for k in range(K)) > 1.0 + tol:
            return False
    return True


def library(H: int, K: int, m: int) -> dict:
    out = {}
    out["commit_only"] = {(t, k): 0.0 for t in range(H) for k in range(K)}

    # BOTH constraints, not just the budget.  `min(1, m/(H*K))` alone spends
    # m/H per task, which exceeds one audit per task whenever m > H -- and a
    # candidate that breaks feasibility beats V*, which is how 16 games came
    # back with NEGATIVE regret against an exact minimax.
    share = min(m / float(H * K), 1.0 / K)
    out["uniform"] = {(t, k): share for t in range(H) for k in range(K)}

    cov = {(t, k): 0.0 for t in range(H) for k in range(K)}
    left = float(m)
    for t in range(H):
        take = min(1.0, left)
        for k in range(K):
            cov[(t, k)] = take / K
        left -= take
        if left <= 0:
            break
    out["earliest"] = cov

    for k0 in range(K):
        cov = {(t, k): 0.0 for t in range(H) for k in range(K)}
        left = float(m)
        for t in range(H):
            take = min(1.0, left)
            cov[(t, k0)] = take
            left -= take
            if left <= 0:
                break
        out[f"single_c{k0}"] = cov

    cov = {(t, k): 0.0 for t in range(H) for k in range(K)}
    left = float(m)
    for t in range(H):
        take = min(1.0, left)
        cov[(t, t % K)] = take
        left -= take
        if left <= 0:
            break
    out["rotation"] = cov

    for nm, cov in out.items():
        assert feasible(cov, H, K, m), (
            f"library member {nm!r} is infeasible at H={H} K={K} m={m}: it "
            f"would beat the exact minimax by spending budget it does not have")
    return out
