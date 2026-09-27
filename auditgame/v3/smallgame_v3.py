"""v3/smallgame_v3.py -- the 240 small games of H7: exact minimax (B7), the 28 members
ported, regret against B7 and the covering radius against pi* (plan T21).

Draft S8 / S10.2: "On the 240 exactly-solvable small games, Sentinel's empirical regret
against the minimax value (B7) is 0.09 ... at the measured covering radius rho = 0.07".
sentinel-v3.md H7: the radius is measured only on the 240 small games, where pi* exists;
the 28 members are ported to them; the radius is the UNIFORM TV over every history,
against pi* (theory note S4: Def. 4.1 with P_ref = {pi*}, Prop. 4.2, Remark 4.3).

THE GAME (v2's smallgame, same 240 cells: smallgame.games()).  K carriers, H tasks,
trigger delay Delta, audit budget m (audits).  At each task the defender audits one
carrier or nothing ("none", action index K); an audit costs 1 and at most m are bought.
The attacker picks (k, iota); the payload is live on carrier k over W = {iota..iota+Delta}
and is caught iff k is audited at some task of W (perfect detection, as in v2).  L = 1 if
it survives, 0 if caught; range(L) = 1.

EXACT MINIMAX OVER EVERY POLICY, NOT THE MARGINAL RELAXATION.  An audit of k at t either
catches (the game is over, L = 0) or is quiet.  So on every history on which L is still
open every observation was "quiet", and a history is just the defender's own past actions.
A pure (even adaptive) policy is therefore one SCHEDULE s in {0..K}^H with at most m
audits, and by Kuhn's theorem every behavioural policy is a distribution over schedules.
`solve_exact` solves   min_{P in Delta(S)} max_{(k,iota)} Pr_P[s misses W(k,iota)]   as an
LP over all schedules (<= 5^6), and returns the attacker's dual y* as a certificate:
min_s sum_c y*(c) miss(s, c) = V*.  v2's `smallgame.solve` optimises coverage MARGINALS
with Pr[caught] = sum_{t in W} c(t,k); that is exact only for singleton windows (Delta = 0)
and is a relaxation otherwise (Pr[caught] <= the sum), so its value is <= V* (the tool
prints where they differ).

B7 is pi*: "the minimax solution, computable only on the 240 small games; a ceiling, not
a competitor".  Its value V* is the floor every library value is compared with.

THE 28 MEMBERS, PORTED (`ported_library`).  Same names and parameters as v3/library.py
(SW 8, BT 12, RO 8), the same decision rules, run on the game's targets:
  * targets: the game's K carriers are GAME_TARGETS[K] = the first K - 1 sweep targets of
    config.TARGETS (memory, queue, skill) plus the commit; a member's rule runs over the
    targets the game has (SW weights restricted and renormalised; BT's sweep draw over the
    game's sweeps; RO's order restricted to the game's targets);
  * budget: a member chooses a target every task, as in v3; once m audits are spent its
    choice is unaffordable and it plays none (O14: line 5 drops unaffordable members);
  * belief (the T9 particle filter is not imported: stub, per the task): the exact
    posterior of the game over {null} + (k, iota) with prior Pr[attack] = SMALL_P0, uniform
    over the configurations; a quiet audit of k at t removes every (k, iota) whose window
    holds t.  c_t[k] = 1 iff the poison of k is live at t.  p_attack and carrier_mass are
    read from it exactly as library.BeliefThreshold / CarrierRotation read b_t;
  * BT band: Prop. 6.1's floor with f = 0 (every configuration is caught by some audit),
    so tau = u * SMALL_P0;
  * the members' own randomisation (RO's random phase, RO-posterior's tie draw, SW's and
    BT's draws) is part of the policy: a member is the distribution over schedules it
    induces (`leaves`).

REGRET AGAINST B7 (H7, draft S9.3 "Empirical regret against B7 on small games").
    V(Pi)      = min over single members of max_y L          (Prop. 4.2's V(Pi))
    V(conv Pi) = min over mixtures x in Delta(28) of max_y L (what line 5 computes: an LP)
    regret     = V(conv Pi) - V*   (and the single-member regret beside it).

COVERING RADIUS AGAINST pi* (Def. 4.1 with P_ref = {pi*}).  d(pi, pi') = max_{t, h} TV of
the audit distributions at history h, the UNIFORM TV, not v2's mean over tasks.  A
history off a policy's path carries none of its behaviour (Kuhn): its completion there is
free and changes no loss, so it is completed to match the other policy and the max runs
over histories both reach.  Over mixtures x of the 28 members (drawn once per episode),
the conditional at h is sum_i x_i P_i(h, a) / sum_i x_i P_i(h), and
    TV_h(x) <= r   <=>   sum_a |sum_i x_i (P_i(h,a) - pi*(a|h) P_i(h))| <= 2 r sum_i x_i P_i(h),
linear in x for a fixed r; `radius_mixture` bisects on r with one LP per step.
pi* is not unique and Prop. 4.2 holds for every minimax pi*, so the radius depends on the
pi* chosen.  `radius` reports it against the LP's pi* (the declared B7) and, with
refine=True, against the minimax pi* nearest the library that a local search finds:
starting from the LP-pi* mixture and from the REFINE_STARTS members nearest their own
closest minimax pi*, alternate "fix x, move pi* inside the minimax set" (`closest_minimax`)
and "fix pi*, re-optimise x".  The search is a heuristic (the joint problem is bilinear),
so the refined radius is an upper bound on min over minimax pi*.  LP noise on histories
of tiny reach is removed by `graft`; every radius reported is RE-MEASURED by `uniform_tv`
on the two policies it names, and every pi* kept has value <= V* + 1e-6, so Prop. 4.2's
bound H * rho * range(L) holds for each.

Remark 4.3: against the whole policy space the radius is >= 1 - 1/(K + 1) (K + 1 actions);
`literal_radius_floor` prints it next to the measured one.

numpy/scipy (scipy.optimize.linprog, HiGHS); randomness: none (every policy is an exact
distribution, no draws).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog

import smallgame as SG
from v3 import config as C
from v3 import library as L

#: The prior attack probability of the small-game belief (the stub of b_t).  L1, declared.
SMALL_P0 = 0.5
#: Prop. 6.1's f in the small game: no configuration is uninformable.
SMALL_F = 0.0
#: Game carrier j <-> target, per K: the first K - 1 sweeps of config.TARGETS + the commit.
GAME_TARGETS = {K: tuple(L.SWEEP_TARGETS[:K - 1]) + (L.COMMIT,) for K in SG.K_VALUES}
#: Bisection tolerance on the radius.
RADIUS_TOL = 1e-7
#: Slack on V* when pi* is moved inside the minimax set (refine).
VSTAR_TOL = 1e-9
#: Alternation rounds of refine.
REFINE_ROUNDS = 4
#: Single members used as extra starting points of refine (nearest first).
REFINE_STARTS = 3
#: Schedules below this probability are dropped from a refined pi* (LP noise).
PRUNE = 1e-7


@dataclass(frozen=True)
class Game:
    H: int
    K: int
    delta: int
    m: int

    @property
    def none(self) -> int:
        return self.K

    def configs(self) -> list:
        return SG.configs(self.H, self.K, self.delta)

    def window(self, c) -> range:
        k, i = c
        return range(i, i + self.delta + 1)


def games() -> list:
    """The 240 cells of v2's smallgame.games(), as Game."""
    return [Game(g["H"], g["K"], g["delta"], g["m"]) for g in SG.games()]


# ---------------------------------------------------------------------------------------
# Schedules and the exact minimax (B7)
# ---------------------------------------------------------------------------------------


@lru_cache(maxsize=None)
def schedules(H: int, K: int, m: int) -> tuple:
    """Every pure policy: an action per task (K = none), at most m audits."""
    return tuple(s for s in itertools.product(range(K + 1), repeat=H)
                 if sum(a != K for a in s) <= m)


def misses(s: tuple, c: tuple, g: Game) -> bool:
    k = c[0]
    return all(s[t] != k for t in g.window(c))


def miss_matrix(g: Game, S=None) -> np.ndarray:
    """M[c, s] = 1 iff schedule s misses configuration c's window."""
    S = schedules(g.H, g.K, g.m) if S is None else S
    cs = g.configs()
    return np.array([[1.0 if misses(s, c, g) else 0.0 for s in S] for c in cs])


def value_of(P: dict, g: Game) -> float:
    """The attacker's best-response value against a schedule distribution."""
    return max(sum(p for s, p in P.items() if misses(s, c, g)) for c in g.configs())


@dataclass
class Exact:
    game: Game
    value: float                 # V*
    P: dict                      # pi*: schedule -> probability (B7)
    y: dict                      # the attacker's minimax mix (dual certificate)
    certificate: float           # min_s sum_c y(c) miss(s, c): equals V* at optimum


def solve_exact(g: Game) -> Exact:
    """min_P max_c Pr_P[miss c] over every schedule distribution (LP, HiGHS)."""
    S = schedules(g.H, g.K, g.m)
    M = miss_matrix(g, S)
    nc, ns = M.shape
    # variables: P (ns), v
    cost = np.zeros(ns + 1); cost[-1] = 1.0
    A_ub = np.hstack([M, -np.ones((nc, 1))])
    A_eq = np.hstack([np.ones((1, ns)), np.zeros((1, 1))])
    res = linprog(cost, A_ub=A_ub, b_ub=np.zeros(nc), A_eq=A_eq, b_eq=[1.0],
                  bounds=[(0, None)] * ns + [(None, None)], method="highs")
    if res.status != 0:
        raise RuntimeError(f"exact LP failed at {g}: {res.message}")
    p = np.clip(res.x[:ns], 0.0, None)
    p /= p.sum()
    P = {S[j]: float(p[j]) for j in range(ns) if p[j] > 1e-12}
    y = np.clip(-res.ineqlin.marginals, 0.0, None)
    y = y / y.sum() if y.sum() > 0 else np.full(nc, 1.0 / nc)
    cert = float((y @ M).min())
    return Exact(g, float(res.fun), P, dict(zip(g.configs(), map(float, y))), cert)


# ---------------------------------------------------------------------------------------
# The belief stub: the exact posterior of the small game
# ---------------------------------------------------------------------------------------


class SmallBelief:
    """Posterior over {null} + (k, iota) after quiet audits; prior SMALL_P0 on attack,
    uniform over configurations.  Immutable: `after` returns the next belief."""

    def __init__(self, g: Game, alive: frozenset | None = None, p0: float = SMALL_P0):
        self.g, self.p0 = g, p0
        self.cs = g.configs()
        self.alive = frozenset(range(len(self.cs))) if alive is None else alive

    def after(self, t: int, a: int) -> "SmallBelief":
        if a == self.g.none:
            return self
        gone = {j for j in self.alive
                if self.cs[j][0] == a and t in self.g.window(self.cs[j])}
        return SmallBelief(self.g, self.alive - gone, self.p0)

    def _z(self) -> float:
        return (1.0 - self.p0) + self.p0 * len(self.alive) / len(self.cs)

    def p_attack(self) -> float:
        return self.p0 * len(self.alive) / len(self.cs) / self._z()

    def carrier_mass(self, t: int) -> list:
        """Pr[c_t[k] = 1 | h] for every game carrier k."""
        w = self.p0 / len(self.cs) / self._z()
        out = [0.0] * self.g.K
        for j in self.alive:
            k, i = self.cs[j]
            if t in self.g.window(self.cs[j]):
                out[k] += w
        return out


# ---------------------------------------------------------------------------------------
# The 28 members, ported
# ---------------------------------------------------------------------------------------


class Ported:
    """A library member on game g.  initial() -> [(p, state)] (its own per-episode draw);
    decide(t, belief, state) -> [(p, action, state')] before the budget is applied."""
    family = ""

    def __init__(self, name: str, g: Game):
        self.name, self.g = name, g
        self.targets = GAME_TARGETS[g.K]
        self.commit = self.targets.index(L.COMMIT)
        self.sweeps = [j for j, x in enumerate(self.targets) if x != L.COMMIT]

    def initial(self) -> list:
        return [(1.0, None)]

    def decide(self, t, belief, state) -> list:
        raise NotImplementedError


class PortedSW(Ported):
    family = "SW"

    def __init__(self, name, g, *, weights):
        super().__init__(name, g)
        full = dict(zip(C.TARGETS, L.SW_WEIGHTS[weights]))
        w = [float(full[x]) for x in self.targets]
        if sum(w) <= 0:
            raise ValueError(f"{name}: no weight on the game's targets {self.targets}")
        self.dist = [v / sum(w) for v in w]

    def decide(self, t, belief, state):
        return [(p, a, state) for a, p in enumerate(self.dist) if p > 0]


class PortedBT(Ported):
    family = "BT"

    def __init__(self, name, g, *, u, floor):
        super().__init__(name, g)
        self.band = L.band_prop61(SMALL_P0, SMALL_F)
        self.u, self.floor, self.tau = u, floor, self.band.tau(u)

    def decide(self, t, belief, state):
        if belief.p_attack() <= self.tau:
            return [(1.0, self.commit, state)]
        mass = belief.carrier_mass(t)
        m = [max(0.0, mass[j]) for j in self.sweeps]
        tot, n = sum(m), len(self.sweeps)
        out = []
        for j, mj in zip(self.sweeps, m):
            p = self.floor / n + (1.0 - self.floor) * (mj / tot if tot > 0 else 1.0 / n)
            if p > 0:
                out.append((p, j, state))
        return out


class PortedRO(Ported):
    family = "RO"

    def __init__(self, name, g, *, order, period, phase):
        super().__init__(name, g)
        self.order = [self.targets.index(x) for x in L.RO_ORDERS[order] if x in self.targets]
        self.period, self.phase = period, phase
        self.cycle = len(self.order) * period

    def initial(self):
        if self.phase == "random":
            return [(1.0 / self.cycle, off) for off in range(self.cycle)]
        return [(1.0, ())]                            # anchors of the cycles seen so far

    def decide(self, t, belief, state):
        n = len(self.order)
        if self.phase == "random":
            return [(1.0, self.order[((t + state) // self.period) % n], state)]
        c = t // self.cycle
        anchors = dict(state)
        if c in anchors:
            j0s = [(1.0, anchors[c], state)]
        else:
            mass = belief.carrier_mass(t)
            m = [mass[k] for k in self.order]
            top = max(m)
            tied = [j for j, v in enumerate(m) if abs(v - top) <= 1e-15 + 1e-12 * abs(top)]
            j0s = [(1.0 / len(tied), j, tuple(sorted({**anchors, c: j}.items())))
                   for j in tied]
        return [(p, self.order[(j0 + (t % self.cycle) // self.period) % n], st)
                for p, j0, st in j0s]


def port(name: str, g: Game) -> Ported:
    cls, kw = L.LIBRARY[name]
    if cls is L.StageWeighted:
        return PortedSW(name, g, **kw)
    if cls is L.BeliefThreshold:
        return PortedBT(name, g, **kw)
    if cls is L.CarrierRotation:
        return PortedRO(name, g, **kw)
    raise TypeError(f"no port for {cls.__name__}")


def ported_library(g: Game) -> dict:
    return {n: port(n, g) for n in L.MEMBERS}


def leaves(pol: Ported) -> dict:
    """The distribution over schedules the member induces (budget applied: once m audits
    are spent, none)."""
    g = pol.g
    out: dict = {}

    def rec(t, prefix, used, belief, state, p):
        if t == g.H:
            out[prefix] = out.get(prefix, 0.0) + p
            return
        for q, a, st in pol.decide(t, belief, state):
            if used >= g.m:
                a = g.none
            rec(t + 1, prefix + (a,), used + (a != g.none), belief.after(t, a), st, p * q)

    for q, st in pol.initial():
        rec(0, (), 0, SmallBelief(g), st, q)
    return out


def feasible(P: dict, g: Game, tol: float = 1e-9) -> bool:
    """A schedule distribution respects the game: one action per task, <= m audits, a
    probability distribution; its per-task marginals pass v2's smallgame.feasible."""
    if abs(sum(P.values()) - 1.0) > tol or any(p < -tol for p in P.values()):
        return False
    for s in P:
        if len(s) != g.H or any(not 0 <= a <= g.K for a in s) or sum(a != g.K for a in s) > g.m:
            return False
    return SG.feasible(coverage(P, g), g.H, g.K, g.m, tol)


def coverage(P: dict, g: Game) -> dict:
    cov = {(t, k): 0.0 for t in range(g.H) for k in range(g.K)}
    for s, p in P.items():
        for t, a in enumerate(s):
            if a != g.K:
                cov[(t, a)] += p
    return cov


# ---------------------------------------------------------------------------------------
# Histories, the uniform TV, the covering radius
# ---------------------------------------------------------------------------------------


def prefix_probs(P: dict) -> dict:
    """P(h) for every prefix h (lengths 0..H) of the schedules in P."""
    out: dict = {}
    for s, p in P.items():
        for t in range(len(s) + 1):
            out[s[:t]] = out.get(s[:t], 0.0) + p
    return out


def decision_histories(g: Game, pp: dict, eps: float = 1e-12) -> list:
    """The histories (decision points t = 0..H-1) a policy reaches."""
    return sorted((h for h, v in pp.items() if len(h) < g.H and v > eps),
                  key=lambda h: (len(h), h))


def uniform_tv(P1: dict, P2: dict, g: Game, eps: float = 1e-12) -> tuple:
    """d(pi1, pi2) = max over histories both reach of TV of the audit distribution at h,
    and the history attaining it."""
    a1, a2 = prefix_probs(P1), prefix_probs(P2)
    best, arg = 0.0, None
    for h in decision_histories(g, a1, eps):
        if a2.get(h, 0.0) <= eps:
            continue
        tv = 0.5 * sum(abs(a1.get(h + (a,), 0.0) / a1[h] - a2.get(h + (a,), 0.0) / a2[h])
                       for a in range(g.K + 1))
        if tv > best:
            best, arg = tv, h
    return best, arg


class Infeasible(RuntimeError):
    """An LP of the radius search failed even at r = 1 (numerical; refine skips that step)."""


def _bisect(feasible_at, hi: float, tol: float = RADIUS_TOL):
    """Smallest r in [0, hi] with feasible_at(r) not None (monotone); returns (r, sol)."""
    sol = feasible_at(hi)
    if sol is None and hi < 1.0:                   # a measured hi can sit on LP noise
        hi = 1.0
        sol = feasible_at(hi)
    if sol is None:
        raise Infeasible("the LP is infeasible at r = 1")
    s0 = feasible_at(0.0)
    if s0 is not None:
        return 0.0, s0
    lo = 0.0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        s = feasible_at(mid)
        if s is None:
            lo = mid
        else:
            hi, sol = mid, s
    return hi, sol


def _tv_lp(N, D, nz: int, K: int, hi: float, extra_ub=None, extra_b=None):
    """Bisect on r: find z in the simplex with, for every history h (row block of K + 1),
        sum_a |(N z)_{h,a}| <= 2 r (D z)_h     (plus extra_ub z <= extra_b).
    N is (nh (K+1)) x nz, D is nh x nz, both sparse.  Returns (r, z)."""
    na, nh = N.shape[0], D.shape[0]
    I = sp.identity(na, format="csr")
    agg = sp.kron(sp.identity(nh), np.ones((1, K + 1)), format="csr")
    A_eq = sp.hstack([np.ones((1, nz)), sp.csr_matrix((1, na))], format="csr")
    cost = np.concatenate([np.zeros(nz), np.full(na, 1e-6)])
    top = [sp.hstack([N, -I]), sp.hstack([-N, -I])]
    if extra_ub is not None:
        top.append(sp.hstack([extra_ub, sp.csr_matrix((extra_ub.shape[0], na))]))

    def at(r):
        A_ub = sp.vstack(top + [sp.hstack([-2.0 * r * D, agg])], format="csr")
        b_ub = np.zeros(A_ub.shape[0])
        if extra_ub is not None:
            b_ub[2 * na:2 * na + extra_ub.shape[0]] = extra_b
        res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1.0],
                      bounds=[(0, None)] * (nz + na), method="highs")
        return None if res.status != 0 else np.clip(res.x[:nz], 0.0, None)

    r, z = _bisect(at, hi)
    return r, z / z.sum()


def radius_mixture(members_P: list, star_P: dict, g: Game, hi: float = 1.0):
    """min over x in Delta(members) of the uniform TV between the mixture and pi*
    (bisection; the returned radius is MEASURED on the returned mixture).  Returns (r, x)."""
    spp = prefix_probs(star_P)
    hs = decision_histories(g, spp)
    row = {h: j for j, h in enumerate(hs)}
    n, K1 = len(members_P), g.K + 1
    N = np.zeros((len(hs) * K1, n))
    D = np.zeros((len(hs), n))
    for i, P in enumerate(members_P):
        pp = prefix_probs(P)
        for h, j in row.items():
            ph = pp.get(h, 0.0)
            D[j, i] = ph
            for a in range(K1):
                N[j * K1 + a, i] = pp.get(h + (a,), 0.0) - spp.get(h + (a,), 0.0) / spp[h] * ph
    _, x = _tv_lp(sp.csr_matrix(N), sp.csr_matrix(D), n, g.K, hi)
    return uniform_tv(mixture(members_P, x), star_P, g)[0], x


def mixture(members_P: list, x) -> dict:
    out: dict = {}
    for w, P in zip(x, members_P):
        if w <= 0:
            continue
        for s, p in P.items():
            out[s] = out.get(s, 0.0) + w * p
    return out


def closest_minimax(g: Game, ex: Exact, target_P: dict, hi: float = 1.0):
    """Move pi* inside the minimax set (value <= V* + VSTAR_TOL) to shrink the uniform TV to
    a fixed policy target_P.  Returns (measured radius, pi*, value of pi*); pi* is pruned
    at PRUNE and renormalised, and its value is re-measured."""
    S = schedules(g.H, g.K, g.m)
    ns, K1 = len(S), g.K + 1
    tpp = prefix_probs(target_P)
    hs = decision_histories(g, tpp)
    row = {h: j for j, h in enumerate(hs)}
    cond = {h: [tpp.get(h + (a,), 0.0) / tpp[h] for a in range(K1)] for h in hs}
    nr, nc, nv, dr, dc = [], [], [], [], []
    for j, s in enumerate(S):
        for t in range(g.H):
            h = s[:t]
            r = row.get(h)
            if r is None:
                continue
            dr.append(r); dc.append(j)
            for a in range(K1):
                v = (1.0 if s[t] == a else 0.0) - cond[h][a]
                if v != 0.0:
                    nr.append(r * K1 + a); nc.append(j); nv.append(v)
    N = sp.csr_matrix((nv, (nr, nc)), shape=(len(hs) * K1, ns))
    D = sp.csr_matrix((np.ones(len(dr)), (dr, dc)), shape=(len(hs), ns))
    M = sp.csr_matrix(miss_matrix(g, S))
    _, p = _tv_lp(N, D, ns, g.K, hi, extra_ub=M,
                  extra_b=np.full(M.shape[0], ex.value + VSTAR_TOL))
    star = graft({S[j]: float(p[j]) for j in range(ns) if p[j] > 0}, target_P, g)
    return uniform_tv(target_P, star, g)[0], star, value_of(star, g)


def graft(P: dict, target_P: dict, g: Game, eps: float = PRUNE) -> dict:
    """The policy that plays P's conditional at every history P reaches with probability
    >= eps, and target_P's conditional below that (where target_P reaches the history).
    LP solutions carry noise on histories of tiny reach, where the conditional -- and so
    the uniform TV -- is meaningless; grafting moves Pr <= H eps of play, and the caller
    re-measures the value."""
    pp, tp = prefix_probs(P), prefix_probs(target_P)
    out: dict = {}

    def rec(h, q):
        if len(h) == g.H:
            out[h] = out.get(h, 0.0) + q
            return
        src = pp if pp.get(h, 0.0) >= eps or tp.get(h, 0.0) <= 0.0 else tp
        for a in range(g.K + 1):
            w = src.get(h + (a,), 0.0) / src[h]
            if w > 0.0:
                rec(h + (a,), q * w)

    rec((), 1.0)
    return out


# ---------------------------------------------------------------------------------------
# One game: values, regret, radius
# ---------------------------------------------------------------------------------------


def library_values(members_P: dict, g: Game) -> dict:
    """V(Pi) over single members and V(conv Pi) over mixtures (LP)."""
    names = list(members_P)
    cs = g.configs()
    Lm = np.array([[sum(p for s, p in members_P[n].items() if misses(s, c, g)) for c in cs]
                   for n in names])                       # (members, configs)
    single = Lm.max(axis=1)
    j = int(single.argmin())
    nm = len(names)
    cost = np.zeros(nm + 1); cost[-1] = 1.0
    A_ub = np.hstack([Lm.T, -np.ones((len(cs), 1))])
    A_eq = np.hstack([np.ones((1, nm)), np.zeros((1, 1))])
    res = linprog(cost, A_ub=A_ub, b_ub=np.zeros(len(cs)), A_eq=A_eq, b_eq=[1.0],
                  bounds=[(0, None)] * nm + [(None, None)], method="highs")
    x = np.clip(res.x[:nm], 0.0, None)
    return {"V_single": float(single[j]), "best_single": names[j],
            "V_mixture": float(res.fun), "x_mixture": dict(zip(names, map(float, x / x.sum())))}


def literal_radius_floor(g: Game) -> float:
    """Remark 4.3: against the whole policy space the radius is >= 1 - 1/(#actions)."""
    return 1.0 - 1.0 / (g.K + 1)


def radius(g: Game, ex: Exact, members_P: dict, refine: bool = False) -> dict:
    """The covering radius of the ported library against pi* (uniform TV).

    radius_single      min over members of d(member, pi*_LP)   (Def. 4.1 on Pi itself)
    radius_mixture     min over mixtures x of d(mix_x, pi*_LP)
    radius_refined     with refine: the smallest d(mix_x, pi*) found by alternating x and
                       pi* inside the minimax set (every pi* kept has value <= V* + 1e-6).
    radius             the smallest of the above: the radius against a genuine minimax pi*.
    Every number is MEASURED by uniform_tv on the policies it names."""
    names = list(members_P)
    Ps = [members_P[n] for n in names]
    per = {n: uniform_tv(members_P[n], ex.P, g)[0] for n in names}
    nearest = min(per, key=per.get)
    r_mix, x = radius_mixture(Ps, ex.P, g, hi=per[nearest])
    if per[nearest] < r_mix:                        # a single member is a mixture too
        r_mix, x = per[nearest], np.array([1.0 if n == nearest else 0.0 for n in names])
    out = {"radius_single": per[nearest], "nearest_single": nearest,
           "radius_mixture": r_mix, "radius": r_mix, "rounds": 0,
           "x_radius": {n: float(w) for n, w in zip(names, x) if w > 1e-9}}
    if refine:
        ok = lambda v: v <= ex.value + 1e-6
        # one step per member: the minimax pi* closest to it (Def. 4.1 on Pi, best pi*)
        singles, failures = {}, 0
        for i, n in enumerate(names):
            try:
                r_i, _, v_i = closest_minimax(g, ex, Ps[i], hi=1.0)
            except Infeasible:
                failures += 1
                continue
            if ok(v_i):
                singles[n] = r_i
        order = sorted(singles, key=singles.get)
        starts = [(r_mix, x)] + [(singles[n], np.eye(len(names))[names.index(n)])
                                 for n in order[:REFINE_STARTS]]
        best, rounds = min(starts, key=lambda c: c[0]), 0
        for r, x in starts:
            for k in range(REFINE_ROUNDS):
                if r <= 1e-9:
                    break
                try:
                    r_star, star, v = closest_minimax(g, ex, mixture(Ps, x),
                                                      hi=min(1.0, r + 1e-6))
                    if not ok(v):
                        break
                    r_new, x_new = radius_mixture(Ps, star, g, hi=1.0)
                except Infeasible:
                    failures += 1
                    break
                cand = min((r_star, x), (r_new, x_new), key=lambda c: c[0])
                if cand[0] >= r - 1e-6:
                    break
                r, x = cand
                rounds = max(rounds, k + 1)
            if r < best[0]:
                best = (r, x)
        out.update({"radius_single_refined": singles[order[0]] if order else None,
                    "nearest_single_refined": order[0] if order else None,
                    "radius_refined": best[0], "radius": min(best[0], r_mix),
                    "rounds": rounds, "lp_failures": failures,
                    "x_radius": {n: float(w) for n, w in zip(names, best[1]) if w > 1e-9}})
    return out


def assess(g: Game, refine: bool = False) -> dict:
    """Everything H7 reports for one game."""
    ex = solve_exact(g)
    members_P = {n: leaves(p) for n, p in ported_library(g).items()}
    vals = library_values(members_P, g)
    rad = radius(g, ex, members_P, refine=refine)
    v2 = SG.solve(g.H, g.K, g.delta, g.m)["value"]
    return {"H": g.H, "K": g.K, "delta": g.delta, "m": g.m,
            "V_star": ex.value, "certificate": ex.certificate, "V_v2_marginal": v2,
            **{k: v for k, v in vals.items() if k != "x_mixture"},
            "regret_mixture": vals["V_mixture"] - ex.value,
            "regret_single": vals["V_single"] - ex.value,
            **rad,
            "prop42_bound": g.H * rad["radius"],       # H rho range(L), range(L) = 1
            "literal_radius_floor": literal_radius_floor(g)}
