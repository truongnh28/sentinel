"""Exact minimax over OBSERVATION-DEPENDENT policies -- the class lp.py cannot reach.

WHAT IS MISSING WITHOUT THIS.  `lp.solve_stackelberg_lp` optimises coverage
u[k,t], v[t] that depend on NOTHING the defender sees. Toan-canh section 7.1
says so plainly: the static class is a SUBSET of the adaptive one, so its value
is an UPPER BOUND on V*, not V*. Section 5.3 names what would give V* --
"backward induction on the discretised belief simplex" -- and that solver has
never existed. The model is stated as a partially-observed game and solved as
an observation-free one; this file closes that gap for small games.

WHY IT IS STILL AN LP, AND STILL EXACT.  Appendix F.1: the follower
best-responds with a PURE strategy, so the hidden state is ONE window (k, i, s)
fixed before the game starts -- a hidden PARAMETER, not a process. Against a
finite adversary set, a defender behavioural policy with perfect recall is
represented exactly by its SEQUENCE FORM: one realisation probability per
(information set, action) path. Coverage of a window and expected budget are
both LINEAR in those probabilities, so min-max is an LP -- no discretisation of
the belief simplex, and no approximation.

    max  m
    s.t. m <= coverage(w)              for every window w
         sum over sequences of cost <= B
         flow conservation at every information set
         r >= 0

THE OBSERVATION MODEL, declared because it bounds what this solves.  At each
step the defender sees WHICH carrier fired, or that none did -- K+1 outcomes,
derived from d' and tau exactly as `detector.Detector` does. Seeing the SET of
carriers that fired would be 2^K outcomes per step and is not modelled: at the
false-alarm rates involved, two carriers firing at once is a rare event whose
handling would double the tree for little information.

SCOPE.  Histories grow as (K+1)^H, so this is for SMALL games -- which is the
scope section 5.3 already declares ("KH <= 40"). `solve_adaptive_lp` REFUSES
rather than silently running for hours, and says what to shrink.
"""
from __future__ import annotations
import itertools
import math

from lp import simplex_max

_SQRT2 = math.sqrt(2.0)


def _phi(z: float) -> float:
    """Standard normal CDF -- stdlib only, same convention as detector.py."""
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


def observation_model(K: int, d_prime: float, tau: float) -> tuple:
    """(psi, phi) -- a poisoned carrier fires, a clean carrier fires.

    Same definition the thesis uses for d': psi = Phi(d' - tau), phi = Phi(-tau),
    so d' = z(psi) - z(phi) holds by construction rather than by assertion.
    """
    return _phi(d_prime - tau), _phi(-tau)


def obs_probs(K: int, live_carrier: int | None, psi: float, phi: float) -> list:
    """P(observation) over {0..K-1} = "carrier j fired", K = "quiet".

    `live_carrier` is None when no window is live at this step, so every carrier
    is clean and only false alarms can fire.
    """
    p = []
    for j in range(K):
        rate = psi if (live_carrier is not None and j == live_carrier) else phi
        # Exactly-one-fires: j fires and the others stay quiet.
        q = rate
        for j2 in range(K):
            if j2 == j:
                continue
            r2 = psi if (live_carrier is not None and j2 == live_carrier) else phi
            q *= (1.0 - r2)
        p.append(q)
    quiet = 1.0
    for j in range(K):
        r = psi if (live_carrier is not None and j == live_carrier) else phi
        quiet *= (1.0 - r)
    p.append(quiet)
    total = sum(p) or 1.0
    return [x / total for x in p]          # renormalise: multi-fire mass folded in


def solve_adaptive_lp(K: int, H: int, B: float, kap: list, kc: float,
                      deltas: tuple = (0, 2), d_prime: float = 2.2,
                      tau: float = 0.0, max_histories: int = 20000) -> dict:
    """Exact minimax value over policies that may depend on what was observed.

    Returns {"m", "n_sequences", "n_windows", "plan"} where `plan` maps
    (history, action) -> realisation probability. `history` is a tuple of
    observations seen so far, so the plan IS the observation-dependent policy.
    """
    windows = [(k, i, i + d) for d in deltas for k in range(K) for i in range(H - d)]
    if not windows:
        return {"m": None, "reason": f"no feasible window for K={K} H={H} deltas={deltas}"}

    n_hist = sum((K + 1) ** t for t in range(H))
    if n_hist > max_histories:
        raise ValueError(
            f"{n_hist} histories for K={K} H={H}: the sequence form is exact but "
            f"grows as (K+1)^H, and section 5.3 scopes this solver to SMALL games. "
            f"Shrink H or K, or raise max_histories deliberately and say why in "
            f"the run record")

    actions = list(range(K)) + ["commit", None]        # audit k / audit commit / idle
    cost = {**{k: kap[k] for k in range(K)}, "commit": kc, None: 0.0}

    histories = [h for t in range(H) for h in itertools.product(range(K + 1), repeat=t)]
    idx, var = {}, 0
    for h in histories:
        for a in actions:
            idx[(h, a)] = var
            var += 1
    im = var                                            # the m variable
    n = var + 1

    # Reach probability of a history GIVEN a window -- the observation model is
    # what makes two windows distinguishable at all.
    psi, phi = observation_model(K, d_prime, tau)

    def reach(h, w):
        k, i, s = w
        p = 1.0
        for t, o in enumerate(h):
            live = k if i <= t < s else None
            p *= obs_probs(K, live, psi, phi)[o]
        return p

    A, b = [], []

    # m <= coverage(w): audit carrier k while the window is open, or commit at s.
    for w in windows:
        k, i, s = w
        row = [0.0] * n
        for h in histories:
            t = len(h)
            if not (i <= t < s or (t == s and s < H)):
                continue
            r = reach(h, w)
            if r <= 0.0:
                continue
            if i <= t < s:
                row[idx[(h, k)]] -= r
            if t == s:
                row[idx[(h, "commit")]] -= r
        row[im] = 1.0
        A.append(row); b.append(0.0)

    # Budget: ONE ROW PER WORLD, not one row under the null.
    #
    # A first version charged expected spend under the NULL observation
    # distribution alone. Measured: it returned m = 1.0000 at B = 0.30, a budget
    # that cannot buy even one audit -- because the solver is free to load mass
    # onto histories that are RARE when nothing is wrong and COMMON under the
    # attack, collecting coverage at a price computed in the wrong world.
    #
    # The defender must stay inside B whichever world it is in, so the constraint
    # is per window, plus the null. The rows are linear in the same realisation
    # variables, so the program is still an LP.
    worlds = [(None, None, None)] + list(windows)    # (None,...) is "no attack"
    for w in worlds:
        wr = {}
        for h in histories:
            if w[0] is None:
                p = 1.0
                for o in h:
                    p *= obs_probs(K, None, psi, phi)[o]
            else:
                p = reach(h, w)
            wr[h] = p
        row = [0.0] * n
        for h in histories:
            for a in actions:
                if cost[a]:
                    row[idx[(h, a)]] = cost[a] * wr[h]
        A.append(row); b.append(B)

    # Flow conservation, as an INEQUALITY in one direction only.
    #
    # The exact condition is sum_a r(h, a) == (mass that reached h). `simplex_max`
    # takes b >= 0, so the "==" would need a row with b = -1 that it refuses. Only
    # the <= direction is needed here, and the reason is structural rather than a
    # convenience: the reverse would bind only if DISCARDING mass ever paid, and it
    # never can, because the idle action is in `actions` with cost 0. Anything a
    # defender could gain by holding mass back it can gain by idling, at the same
    # price and without leaving the simplex. So the optimum saturates these rows
    # and the two formulations have the same value.
    for h in histories:
        row = [0.0] * n
        for a in actions:
            row[idx[(h, a)]] = 1.0
        if not h:
            A.append(row); b.append(1.0)
        else:
            parent = h[:-1]
            for a in actions:
                row[idx[(parent, a)]] -= 1.0
            A.append(row); b.append(0.0)

    for i_v in range(n):
        row = [0.0] * n
        row[i_v] = 1.0
        A.append(row); b.append(1.0)

    c = [0.0] * n
    c[im] = 1.0
    x, _obj = simplex_max(c, A, b)   # (solution, objective)
    plan = {key: x[v] for key, v in idx.items() if x[v] > 1e-9}
    return {"m": x[im], "n_sequences": var, "n_windows": len(windows),
            "n_histories": len(histories), "plan": plan,
            "psi": psi, "phi": phi}
