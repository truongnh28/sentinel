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
         0 <= u, v, m <= 1
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
