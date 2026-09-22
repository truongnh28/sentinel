"""
lp.py -- Simplex solver and Minimax LP for AuditGame.

STDLIB ONLY, consistent with the rest of auditgame (ABC T.6).
Implements the Conitzer & Sandholm (EC 2006) Stackelberg equilibrium LP
for finite workflow games.
"""
from __future__ import annotations


def simplex_max(c: list[float], A: list[list[float]], b: list[float],
                tol: float = 1e-9, max_iter: int = 50000) -> tuple[list[float], float]:
    """max c^T x  s.t.  A x <= b,  x >= 0,  with b >= 0.

    Uses Dantzig pivot rule with Bland's rule fallback after 500 iterations
    to prevent cycling.
    """
    m, n = len(A), len(c)
    assert all(bi >= -tol for bi in b), "simplex_max requires b >= 0"
    T = [list(A[i]) + [1.0 if j == i else 0.0 for j in range(m)] + [b[i]] for i in range(m)]
    T.append([-ci for ci in c] + [0.0] * m + [0.0])
    basis = [n + i for i in range(m)]
    for it in range(max_iter):
        obj = T[m]
        cand = [j for j in range(n + m) if obj[j] < -tol]
        if not cand:
            break
        pc = min(cand, key=lambda j: obj[j]) if it < 500 else min(cand)
        pr, best = -1, None
        for i in range(m):
            if T[i][pc] > tol:
                r = T[i][-1] / T[i][pc]
                if best is None or r < best - 1e-12 or (abs(r - best) <= 1e-12 and basis[i] < basis[pr]):
                    best, pr = r, i
        if pr < 0:
            raise RuntimeError("LP unbounded")
        pv = T[pr][pc]
        T[pr] = [x / pv for x in T[pr]]
        for i in range(m + 1):
            if i != pr and abs(T[i][pc]) > tol:
                f = T[i][pc]
                T[i] = [a - f * bb for a, bb in zip(T[i], T[pr])]
        basis[pr] = pc
    else:
        raise RuntimeError("simplex did not converge")
    x = [0.0] * n
    for i in range(m):
        if basis[i] < n:
            x[basis[i]] = T[i][-1]
    return x, T[m][-1]


def solve_stackelberg_lp(K: int, H: int, B: float, kap: list[float], kc: float,
                         deltas: tuple[int, ...] = (0, 2, 4)) -> tuple[list[list[float]], list[float], float]:
    """Solve the defender's minimax audit coverage allocation u[k, t] and commit coverage v[t].

    max  m
    s.t. m <= coverage(k, i, s)    for all feasible attacker windows (k, i, s)
         sum_k kap_k sum_t u[k,t] + kc sum_t v[t] <= B
         sum_k u[k,t] + v[t] <= 1   for every t          <-- ONE ACTION PER TASK
         0 <= u, v, m <= 1

    THE PER-TASK ROW IS NOT OPTIONAL.  `Policy.choose` returns ONE action per task,
    so a solution spending more than 1.0 of coverage on a single t cannot be run by
    any sampling rule -- the marginals it prescribes are outside the action space,
    not merely hard to hit.  Without this row the solver returned 4.00 on one task
    for deltas=(4,) and 3.42 for deltas=(2,): the policy executed the first draw and
    dropped the rest, which is why measured spend collapsed to 0.400 (the cheapest
    carrier, first in iteration order) against a budget of 17.95.

    The defect HID at the default deltas=(0, 2, 4), whose solution happens to be
    feasible (max 0.55 per task), and appeared only on the upstream-only classes --
    that is, only when the solver was asked the question this thesis is about.

    Feasibility costs value, as it must: for deltas=(2,) the optimum falls from
    m = 0.855 to m = 0.768.  The larger number was never attainable.
    """
    nU, nV = K * H, H
    n = nU + nV + 1
    im = n - 1
    c = [0.0] * n
    c[im] = 1.0
    A, b = [], []

    # Attacker actions across all deltas
    for d in deltas:
        for k in range(K):
            for i in range(H - d):
                s = i + d
                row = [0.0] * n
                for t in range(i, s):
                    row[k * H + t] = -1.0
                row[nU + s] += -1.0
                row[im] = 1.0
                A.append(row)
                b.append(0.0)

    # Budget constraint
    row = [0.0] * n
    for k in range(K):
        for t in range(H):
            row[k * H + t] = kap[k]
    for t in range(H):
        row[nU + t] = kc
    A.append(row)
    b.append(B)

    # ONE ACTION PER TASK -- see the docstring.  `choose` picks a single action,
    # so the coverage mass on any one t may not exceed 1.0.
    for t in range(H):
        row = [0.0] * n
        for k in range(K):
            row[k * H + t] = 1.0
        row[nU + t] = 1.0
        A.append(row)
        b.append(1.0)

    # Upper bound of 1.0 on all decision variables
    for j in range(n):
        row = [0.0] * n
        row[j] = 1.0
        A.append(row)
        b.append(1.0)

    x, _ = simplex_max(c, A, b)
    u = [[x[k * H + t] for t in range(H)] for k in range(K)]
    v = [x[nU + t] for t in range(H)]
    m = x[im]
    return u, v, m


def solve_remaining_lp(K: int, H: int, t: int, B_rem: float, kap: list[float],
                       kc: float, deltas: tuple[int, ...],
                       done: dict | None = None):
    """Minimax coverage for the windows STILL OPEN at task t.

    Spec: docs/preregistration/TIEN-DANG-KY-Sentinel-SSG.md SS4 ("hieu ung duoi").

    WHY NOT JUST RE-SOLVE A FRESH GAME OF LENGTH H-t.  A fresh game only knows
    windows that both start and end inside [t, H).  Measured with deltas=(2,4):
    at H' = 2 the fresh game has ZERO feasible windows, so it returns sum_u =
    sum_v = 0 AND m = 1.0 -- a min over the empty set, which takes the variable's
    upper bound.  The policy stops auditing while the objective reports perfect
    coverage.  That is a SILENT failure of the same family as the missing
    per-task row: the number says best-possible while nothing is done.

    WHICH WINDOWS ARE OPEN.  Every (k, i, s) whose trigger has NOT fired: s >= t.
    There is NO condition on i.  The attacker fixes (k, i, s) BEFORE the episode
    (Toan-canh SS4.0, arrow 1), so a window with i >= t -- not yet inserted -- is
    just as live as one already placed.  `max(i, t)` in the lower limit is what
    handles that case; an extra `i < t` filter would silently drop future
    insertions.

    `done[(k, i, s)]` is the count of audits ALREADY PERFORMED on carrier k at
    some t' in [i, s).  It is a COUNT of realised actions, never a planned
    marginal: before t the draws have happened, so what exists is audits, not
    probabilities.  Mixing ex-ante mass with ex-post outcomes in one row is the
    same error shape as solving outside the action space.  Pass None to drop the
    term -- conservative, and then it must be DECLARED as dropped.

    Returns (u, v, m, n_windows) with u[k][j], v[j] indexed by j = t' - t.
    n_windows == 0 means there is nothing left to protect -- the caller must NOT
    audit and must NOT read m.  An exhausted budget is reported SEPARATELY: the
    marginals come back all-zero while n_windows still counts the open windows,
    because "nothing left to cover" and "no money left to cover it" are different
    facts and a caller reading n_windows as exposure would be misled by merging
    them.
    """
    Hr = H - t
    if Hr <= 0:
        return [[0.0] * 0 for _ in range(K)], [], 0.0, 0
    if B_rem <= 0:
        # Out of budget is NOT the same fact as out of windows, and a caller that
        # reads n_windows as "how much is still at risk" would be misled by
        # folding them together.  Report the windows that ARE open and let the
        # zero-budget solve return all-zero marginals.
        n_open = sum(1 for d in deltas for _k in range(K)
                     for i in range(H - d) if i + d >= t)
        return [[0.0] * Hr for _ in range(K)], [0.0] * Hr, 0.0, n_open
    done = done or {}
    nU, nV = K * Hr, Hr
    n = nU + nV + 1
    im = n - 1
    c = [0.0] * n
    c[im] = 1.0
    A, b = [], []
    n_win = 0

    for d in deltas:
        for k in range(K):
            for i in range(H - d):
                s = i + d
                if s < t:
                    continue                     # already fired: not open
                n_win += 1
                row = [0.0] * n
                for tp in range(max(i, t), s):   # NO `i < t` filter -- see docstring
                    row[k * Hr + (tp - t)] = -1.0
                row[nU + (s - t)] += -1.0
                row[im] = 1.0
                A.append(row)
                b.append(float(done.get((k, i, s), 0)))

    if n_win == 0:
        return [[0.0] * Hr for _ in range(K)], [0.0] * Hr, 0.0, 0

    row = [0.0] * n                              # remaining budget
    for k in range(K):
        for j in range(Hr):
            row[k * Hr + j] = kap[k]
    for j in range(Hr):
        row[nU + j] = kc
    A.append(row)
    b.append(B_rem)

    for j in range(Hr):                          # ONE ACTION PER TASK
        row = [0.0] * n
        for k in range(K):
            row[k * Hr + j] = 1.0
        row[nU + j] = 1.0
        A.append(row)
        b.append(1.0)

    for j in range(n):
        row = [0.0] * n
        row[j] = 1.0
        A.append(row)
        b.append(1.0)

    x, _ = simplex_max(c, A, b)
    u = [[x[k * Hr + j] for j in range(Hr)] for k in range(K)]
    v = [x[nU + j] for j in range(Hr)]
    return u, v, x[im], n_win
