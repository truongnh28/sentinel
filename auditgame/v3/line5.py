"""v3/line5.py -- Algorithm 1 line 5: the minimax LP over the restricted library (T12).

Draft Algorithm 1:
    5: a_t <- arg min_{pi in Pi} max_{pi_A in Pi_A-hat} L(pi, pi_A | b_t, B_t)
       |> robust over a restricted library
and S5.3: "Sentinel commits to a distribution over audit actions and reveals only the
distribution."

ONE LP, TWO SOURCES OF L-hat (Q13).  Every task, line 5 asks a source for the loss matrix
L-hat [28 members x 6 attacker classes] (api.LossMatrix) and solves ONE LP over it
(`minimax`):
    min_x max_a sum_pi x_pi L-hat[pi, a]   s.t.  x in the simplex over the affordable members
    TableSource    (primary, every cell)  looks L-hat up in the precomputed line-5 table
                   (T14's v3/line5_table.py) under the key (table cell, Delta-hat, h = tasks
                   left, O16 belief-bin features).
    RolloutSource  (headline cells only)  estimates L-hat by R real rollouts per (member,
                   attacker class) from b_t (v3/rollout.py).
Line5 never looks at which source it holds except to record it (EpisodeRecord.line5_source).

THE LP (lp.simplex_max, stdlib).  With c = max L-hat + 1 and M = c - L-hat > 0,
    max v  s.t.  v - sum_pi x_pi M[pi, a] <= 0 (every a),  sum_pi x_pi <= 1,  x, v >= 0
has sum x = 1 at the optimum (M > 0), and the minimax loss is c - v.  The value reported is
re-read from x (max_a x.L-hat), never from the tableau.

x_t IS PUBLISHED, THE DRAW IS NOT (S5.3, D4.attacker).  The induced action distribution is
q_t(target) = sum_pi x_pi Pr_pi[target at t]; a_t is drawn from q_t with
core.seed_of(ctx.rng_seed, "v3-line5", t).  The decision log (PolicyV3.decision_log) holds
x_t and q_t, the value, the source and the skipped members -- never the drawn member, the
drawn target or the draw's seed.

ATTACKER CLASSES (S5.5, D18).  The columns must be tuning columns (attackers.
attacker_classes(): the six D18 behaviour classes of the primary world), and no column may
share a behaviour key with a held-out attacker; a matrix that breaks this is refused.

O14: AFFORDABILITY.  The table has no budget key (config.TABLE_HAS_BUDGET_KEY = False).
Line 5 drops every member whose decision at t puts positive probability on an action whose
price exceeds the remaining budget B_t (config.LINE5_SKIP_UNAFFORDABLE); the LP runs over
the rest.  If no member is left, a_t = none (config.LINE5_ACTION_WHEN_NONE_AFFORDABLE).

Stdlib only (the LP is lp.simplex_max).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import lp as LP
from core import seed_of

from v3 import api as A
from v3 import attackers as AT
from v3 import config as C

#: core.seed_of tag of line 5's own draw from q_t.
DRAW_TAG = "v3-line5"
_EPS = 1e-9


# ---------------------------------------------------------------------------------------
# The LP
# ---------------------------------------------------------------------------------------


#: minimax results by their exact input (the float rows): the LP is a deterministic
#: function of L, and the line-5 table hands out the same L-hat for every episode that
#: reaches the same key, so a repeated matrix is solved once.  Bounded; cleared when full.
_MINIMAX: dict = {}
MINIMAX_CACHE_MAX = 65536


def minimax(L) -> tuple:
    """(x, value): x minimises max_a sum_i x_i L[i][a] over the simplex; value is that
    worst case, re-read from x.  L is a non-empty list of equal-length non-empty rows.
    Memoised on the exact float rows (`_MINIMAX`): same input, same (x, value)."""
    key = tuple(tuple(float(v) for v in r) for r in L)
    hit = _MINIMAX.get(key)
    if hit is None:
        hit = _minimax(key)
        if len(_MINIMAX) >= MINIMAX_CACHE_MAX:
            _MINIMAX.clear()
        _MINIMAX[key] = hit
    x, value = hit
    return list(x), value


def _minimax(L) -> tuple:
    rows = [[float(v) for v in r] for r in L]
    if not rows or not rows[0] or any(len(r) != len(rows[0]) for r in rows):
        raise ValueError("minimax needs a non-empty rectangular matrix")
    P, K = len(rows), len(rows[0])
    c = max(max(r) for r in rows) + 1.0
    n = P + 1                                                  # x_0..x_{P-1}, v
    A_ub, b = [], []
    for a in range(K):
        A_ub.append([-(c - rows[i][a]) for i in range(P)] + [1.0])
        b.append(0.0)
    A_ub.append([1.0] * P + [0.0])
    b.append(1.0)
    obj = [0.0] * P + [1.0]
    sol, _ = LP.simplex_max(obj, A_ub, b)
    x = [max(0.0, v) for v in sol[:P]]
    s = sum(x)
    if s <= _EPS:
        raise RuntimeError("minimax LP returned an empty mixture")
    x = [v / s for v in x]
    value = max(sum(x[i] * rows[i][a] for i in range(P)) for a in range(K))
    return tuple(x), value


def mixture_value(x, L) -> float:
    """max_a sum_i x_i L[i][a]: what the attacker's best class gets against x."""
    return max(sum(xi * r[a] for xi, r in zip(x, L)) for a in range(len(L[0])))


# ---------------------------------------------------------------------------------------
# Attacker classes (S5.5, D18)
# ---------------------------------------------------------------------------------------


#: The column sets check_classes has passed (the check reads only the fixed D18 tuning
#: classes and the fixed held-out split, so a set that passed once passes always).
_CLASSES_OK: set = set()


def check_classes(classes) -> None:
    """Refuse a column that is not a tuning column or can realise held-out behaviour.
    A column set that passed is remembered (`_CLASSES_OK`); a refusal is never cached."""
    key = tuple(classes)
    if key in _CLASSES_OK:
        return
    _check_classes(key)
    _CLASSES_OK.add(key)


def _check_classes(classes) -> None:
    tuning = set(AT.attacker_classes())
    bad = [c for c in classes if c not in tuning]
    if bad:
        raise ValueError(f"line 5 columns {bad} are not the D18 tuning classes "
                         f"(attackers.attacker_classes()): a held-out or unknown attacker "
                         f"must never enter the defender's optimisation (S5.5)")
    held = set().union(*(AT.behavior_keys(AT.SCRIPTED[n], C.PRIMARY) for n in AT.held_out()))
    for c in classes:
        if AT.behavior_keys(AT.by_name(c), C.PRIMARY) & held:
            raise ValueError(f"line 5 column {c!r} shares behaviour with a held-out attacker")


# ---------------------------------------------------------------------------------------
# O14: which members can pay for their decision at t
# ---------------------------------------------------------------------------------------


def affordable(dist: dict, kappa: dict, B_t: float) -> bool:
    """Every action the member may take at t (positive probability) costs <= B_t."""
    return all(kappa[k] <= B_t + _EPS for k, p in dist.items() if p > 0.0)


# ---------------------------------------------------------------------------------------
# The two sources (Q13)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TableKey:
    """The line-5 table's key (T14, O16): the table cell (config.table_key_id: rho, chi,
    detector of the primary world at K_d = 2 and b1), Delta-hat, h = tasks left including
    t, and the raw O16 bin features (T14 bins p_attack into dev quantiles)."""
    table_cell: str
    delta_hat: object
    h: int
    features: A.BinFeatures


class TableSource:
    """Primary source (Q13): L-hat from the precomputed table.  `table` is T14's object
    with lookup(TableKey) -> api.LossMatrix (source "table"; its `note` carries the O16
    empty-bin fallback reason)."""
    name = "table"

    def __init__(self, table):
        self.table = table

    def key(self, t: int, belief: A.BeliefAPI, delta_hat, ctx: A.EpisodeContext) -> TableKey:
        return TableKey(C.table_key_id(ctx.cell), delta_hat, ctx.H - t, belief.bin_features())

    def matrix(self, t, belief, B_t, delta_hat, ctx) -> A.LossMatrix:
        m = self.table.lookup(self.key(t, belief, delta_hat, ctx))
        if not isinstance(m, A.LossMatrix) or m.source != "table":
            raise ValueError("the line-5 table must return an api.LossMatrix with source 'table'")
        return m


class RolloutSource:
    """Headline-cell source (Q13): L-hat from R real rollouts per (member, attacker class)
    from b_t (v3/rollout.py).  The episode's state at the start of task t is handed in with
    `bind` (rollout.drive does it before every step); the source is shared, never copied,
    when the runner snapshots the episode."""
    name = "rollout"

    def __init__(self, engine, R: int):
        if R not in C.ROLLOUT_R_GRID:
            raise ValueError(f"R={R} is not one of the declared {C.ROLLOUT_R_GRID} (Q13, T19)")
        self.engine, self.R = engine, R
        self._state: A.EpisodeState | None = None

    def bind(self, state: A.EpisodeState) -> None:
        self._state = state

    def __deepcopy__(self, memo):
        return self

    def matrix(self, t, belief, B_t, delta_hat, ctx) -> A.LossMatrix:
        if not ctx.cell.is_headline():
            raise ValueError("RolloutSource runs only in the Table 2 headline cells (Q13)")
        st = self._state
        if st is None or st.t != t:
            raise RuntimeError(f"no episode state bound for task {t} (rollout.drive binds it)")
        return self.engine.matrix(st, belief, R=self.R)


# ---------------------------------------------------------------------------------------
# Line 5
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Line5Decision:
    """One task's line-5 decision.  `action` is the draw (the runner's); everything else is
    what is published."""
    t: int
    action: A.AuditAction | None
    x: dict                                 # member -> weight (x_t), affordable members only
    dist: dict                              # target -> q_t(target)
    value: float | None                     # max_a x_t . L-hat
    source: str
    members: tuple                          # the affordable members the LP ran over
    skipped: tuple                          # O14: members dropped at B_t
    note: str = ""

    def published(self) -> dict:
        """The decision-log entry: x_t and q_t, never the draw (S5.3)."""
        return {"t": self.t, "line": 5, "source": self.source,
                "x": {n: round(w, 12) for n, w in self.x.items()},
                "dist": {k: round(p, 12) for k, p in self.dist.items()},
                "value": None if self.value is None else round(self.value, 12),
                "skipped": list(self.skipped), "note": self.note}


class Line5:
    """Line 5 for one episode: the library members (sharing Sentinel's b_t, library.
    make_library), a source of L-hat, and one LP per task."""

    def __init__(self, ctx: A.EpisodeContext, source, members: dict):
        if getattr(source, "name", None) not in C.LINE5:
            raise ValueError(f"line-5 source {getattr(source, 'name', None)!r} is not one of "
                             f"{C.LINE5}")
        self.ctx, self.source, self.members = ctx, source, dict(members)
        self.log: list = []

    @property
    def source_name(self) -> str:
        return self.source.name

    def decide(self, t: int, belief: A.BeliefAPI, B_t: float, delta_hat) -> Line5Decision:
        M = self.source.matrix(t, belief, B_t, delta_hat, self.ctx)
        check_classes(M.classes)
        rows = {n: M.L[i] for i, n in enumerate(M.members) if n in self.members}
        if not rows:
            raise ValueError("the loss matrix names none of this episode's library members")
        dists = {n: self.members[n].distribution(t) for n in rows}
        ok = [n for n in rows if affordable(dists[n], self.ctx.kappa, B_t)]
        skipped = tuple(n for n in rows if n not in ok)
        if not ok:
            d = Line5Decision(t, None, {}, {}, None, M.source, (), skipped,
                              f"no member affordable at B_t = {B_t:.6g}: a_t = "
                              f"{C.LINE5_ACTION_WHEN_NONE_AFFORDABLE} (O14)")
            self.log.append(d.published())
            return d
        x, value = minimax([rows[n] for n in ok])
        xs = {n: w for n, w in zip(ok, x) if w > _EPS}
        z = sum(xs.values())
        xs = {n: w / z for n, w in xs.items()}
        q = {k: sum(w * dists[n].get(k, 0.0) for n, w in xs.items()) for k in C.TARGETS}
        q = {k: p for k, p in q.items() if p > 0.0}
        action = self._draw(t, q)
        d = Line5Decision(t, action, xs, q, value, M.source, tuple(ok), skipped, M.note)
        self.log.append(d.published())
        return d

    def _draw(self, t: int, q: dict) -> A.AuditAction:
        r, acc, pick = random.Random(seed_of(self.ctx.rng_seed, DRAW_TAG, t)).random(), 0.0, None
        for k in C.TARGETS:
            p = q.get(k, 0.0)
            if p <= 0.0:
                continue
            acc += p
            pick = k
            if r < acc:
                break
        return A.AuditAction(pick, self.ctx.depths[pick])
