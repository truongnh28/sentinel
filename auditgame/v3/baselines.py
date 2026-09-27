"""v3/baselines.py -- the defender baselines and the controls of v3 (plan T8, sentinel-v3.md S9).

Every system here is an api.PolicyV3 built from one api.EpisodeContext.  They code against
the frozen contract only (v3/config.py, v3/api.py) plus the v2 modules the plan reuses
(core.seed_of, scoring.carrier_score, carrier_policies._SW); no other v3 module.

WHAT A BASELINE DECIDES.  Only the TARGET (C16): the depth of every action is the cell's
(ctx.depths), taken through PolicyBase.action().  The one declared exception is B1 when
the budget binds (Q8, O6), which lowers its commit depth evenly and then drops commits at
evenly spaced tasks.  In every chi cell the commit is already at depth 1 (R7), so only the
second step can happen in the grid; the first is kept for a cell with a deeper commit.

WHAT A BASELINE DOES ON AN ALARM.  "Quarantine on any anomaly" (draft S4, v2's baseline
rule), at the carrier level of v3: when a SWEEP bought at t raises an alarm, the whole
audited carrier is quarantined (lines 8-9, O7): memory / queue / skill.  A COMMIT alarm
quarantines nothing: the runner blocks that task's patch only, so it never enters the
branch (v3/runner.py step 5; v2's patch_blocks, the draft's "audit-at-commit"; M1 fix
27/09).  A whole-branch quarantine comes only from Algorithm 1 line 8 (Sentinel and the
library), never from a baseline.  B6 is the one declared exception on sweeps: a screen
alarm asks for a confirmation, and only the confirmation's alarm quarantines (it is a
two-stage CHECK).

THE SYSTEMS (names are the record's `policy` field).
    B1 audit-at-commit        S5.2 / S9.2: the commit of every task, the cell's commit depth.
    B2 uniform random         S9.2: each task a target drawn uniformly over the four.
    B3 audit-on-insertion     S9.2: the memory carrier's audit (D2), every task.
    B4 audit-on-retrieval     S9.2: the queue carrier's audit (D2), every task.
    B5 risk-score             S9.2: sweeps in a fixed rotation; the commit on the task after
                              a sweep's carrier score passes a tuned threshold tau5.
    B6 two-stage              S9.2: a random sweep screen; on an alarm, the same carrier is
                              confirmed on the next task.
    cost-greedy               S10.1: a target drawn with probability proportional to 1/kappa.
    SW randomised             S11: a target drawn by stage weights (v2 _SW), tuned by T18.
    B1-prov                   C1: B1 whose commit alarm also reads the provenance score (A7).
  controls (read before any Sentinel number, D28), not competitors:
    Oracle (+)                told the evaluator-known carrier state c_t at every task (the
                              runner hands it over, to this class only) and quarantines
                              every carrier whose bit is 1, without needing an audit; it
                              still audits the seeded carrier(s) every task (M1 fix 27/09).
    Delta = 0 (-)             a cell, not a policy: SWEEP_ONLY names the baselines that may
                              not beat B1 there (plan S7).
  sensitivity:
    B1 audit-at-commit (exhaust)   B1 that spends until the budget runs out, then stops
                                   (sentinel-v3.md "B1 khi ngan sach chan").

Randomness comes only from core.seed_of(ctx.rng_seed, ...), never from the module-level
`random` or hash().  The attacker knows the policy, not its draw (S5.3): the decision log
records each randomised policy's distribution, and the realised target, never a seed.
"""
from __future__ import annotations

import math
import random

import carrier_policies as CP
import scoring
from core import seed_of
from v3 import api as A
from v3 import config as C

COMMIT = "commit"
#: The three sweep targets, each reading the live state of its own carrier (D2 of v2).
SWEEP_TARGETS = tuple(t for t in C.TARGETS if t != COMMIT)
#: carrier -> the audit that reads it (inverse of config.CARRIER_OF_TARGET).
TARGET_OF_CARRIER = {k: t for t, k in C.CARRIER_OF_TARGET.items()}

#: B5's threshold on the sweep's carrier score before tuning (v2 carrier_policies.B5 default;
#: T18 tunes it on dev over draft_setup.TAU5_GRID and passes it as tuned["tau5"]).
TAU5_DEFAULT = 0.3
#: The SW randomised baseline's weight vector before tuning: a PLACEHOLDER declared here,
#: not chosen from results.  T18 picks one of carrier_policies._SW on dev and passes it as
#: tuned["sw_weights"] (a key of _SW).  "commit" (= B1) and "uniform" (= B2) would only
#: repeat another baseline.
SW_WEIGHTS = dict(CP._SW)
SW_DEFAULT = "commit3"

_EPS = 1e-9


def evenly_spaced(H: int, m: int) -> list:
    """m distinct task indices in range(H), evenly spaced and centred: floor((i + 1/2) H / m).

    Consecutive values differ by H/m >= 1, so they are distinct whenever m <= H."""
    if not 0 <= m <= H:
        raise ValueError(f"cannot space {m} tasks over H={H}")
    return [int((i + 0.5) * H / m) for i in range(m)]


class _Baseline(A.PolicyBase):
    """Common part: remembers o_t, quarantines the audited carrier on an alarm, logs."""
    name = "baseline"
    randomised = False

    def __init__(self, ctx: A.EpisodeContext):
        super().__init__(ctx)
        self._obs: A.Observation | None = None

    # --- randomisation (S5.3): only through core.seed_of --------------------------------
    def rng(self, *tag) -> random.Random:
        return random.Random(seed_of(self.ctx.rng_seed, *tag))

    def draw(self, t: int, dist: dict, tag: str) -> str:
        """One target from `dist` (target -> probability), logged as distribution + draw."""
        r, acc = self.rng(t, tag).random(), 0.0
        pick = None
        for k in C.TARGETS:
            p = dist.get(k, 0.0)
            if p <= 0:
                continue
            acc += p
            pick = k
            if r < acc:
                break
        self._log.append({"t": t, "dist": {k: round(dist.get(k, 0.0), 12) for k in C.TARGETS},
                          "target": pick})
        return pick

    def _act(self, t: int, target: str | None) -> A.AuditAction | None:
        a = None if target is None else self.action(target)
        if not self.randomised:
            self._log.append({"t": t, "a": None if a is None else [a.target, a.depth]})
        return a

    # --- line 7 and lines 8-9 -----------------------------------------------------------
    def observe(self, t: int, obs: A.Observation) -> None:
        self._obs = obs

    def alarmed_target(self, t: int) -> str | None:
        """The target bought at t if its audit raised an alarm, else None."""
        o = self._obs
        if o is None or o.t != t or o.bought is None or not o.alarm:
            return None
        return o.bought.target

    def quarantine(self, t: int) -> str | None:
        target = self.alarmed_target(t)
        if target == COMMIT:
            return None                  # the runner blocks this task's patch only (step 5)
        carrier = None if target is None else C.CARRIER_OF_TARGET.get(target)
        if carrier is not None:
            self._log.append({"t": t, "quarantine": carrier})
        return carrier


# ---------------------------------------------------------------------------------------
# B1 (S5.2 "The baseline to beat") and its binding-budget rule (Q8, O6)
# ---------------------------------------------------------------------------------------


def b1_plan(H: int, budget: float, depth: int, unit_price: float) -> list:
    """O6: B1's commit depth per task under budget B.

    Loose budget (B >= H x the price at the cell's depth): the cell's depth every task.
    Binding: the depth units B affords, floor(B / unit price), are spread evenly -- every
    task gets floor(U/H) or one more, the extra units at evenly spaced tasks.  When fewer
    than H units remain, the commit is at depth 1 on U tasks and DROPPED (depth 0) at
    H - U evenly spaced tasks."""
    if H <= 0 or depth < 1 or unit_price <= 0:
        raise ValueError(f"b1_plan(H={H}, depth={depth}, unit_price={unit_price})")
    units = math.floor(budget / unit_price + _EPS) if budget > 0 else 0
    if units >= H * depth:
        return [depth] * H
    if units >= H:
        base, extra = divmod(units, H)
        plan = [base] * H
        for i in evenly_spaced(H, extra):
            plan[i] += 1
        return plan
    plan = [1] * H
    for i in evenly_spaced(H, H - units):
        plan[i] = 0
    return plan


class B1AuditAtCommit(_Baseline):
    """S5.2: "Audit-at-Commit spends the entire budget inspecting the final commit of each
    task at maximum depth."  Maximum depth is the cell's commit depth (C16); it is 1 in
    every chi cell (R7).  When the budget binds, `binding` picks the rule:
        "even"     (primary, O6)  lower the depth evenly, then drop commits evenly;
        "exhaust"  (sensitivity)  the cell's depth while it is affordable, then stop."""
    name = "B1 audit-at-commit"
    BINDING = ("even", "exhaust")

    def __init__(self, ctx: A.EpisodeContext, binding: str = "even"):
        super().__init__(ctx)
        if binding not in self.BINDING:
            raise ValueError(f"binding={binding!r} is not one of {self.BINDING}")
        self.binding = binding
        self.depth = ctx.depths[COMMIT]
        self.unit = ctx.kappa[COMMIT] / self.depth           # cost is linear in depth (Q6)
        self.plan = (b1_plan(ctx.H, ctx.budget, self.depth, self.unit)
                     if binding == "even" else [self.depth] * ctx.H)
        self._log.append({"b1_binding": binding, "b1_plan": list(self.plan)})

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        d = self.plan[t] if 0 <= t < len(self.plan) else self.depth
        affordable = math.floor(B_t / self.unit + _EPS) if B_t > 0 else 0
        d = min(d, affordable)          # a guard: the plan never exceeds B_t when B_t is ctx's
        a = A.AuditAction(COMMIT, d) if d >= 1 else None
        self._log.append({"t": t, "a": None if a is None else [a.target, a.depth]})
        return a


class B1Exhaust(B1AuditAtCommit):
    name = "B1 audit-at-commit (exhaust)"

    def __init__(self, ctx: A.EpisodeContext):
        super().__init__(ctx, binding="exhaust")


class B1Provenance(B1AuditAtCommit):
    """C1: B1 in a world whose commit audit also returns the provenance score of the
    contributing skills (A7).  Its commit alarm is "patch score OR provenance score over the
    cell detector's threshold" (O9: the provenance d' is the detector's, so is its
    threshold); on it, the patch is blocked as B1's is.  The runner blocks on the
    observation's alarm, which in A7 already ORs the provenance score at the same threshold
    (v3/observe.py ObservationModel.commit).  In A0 the observation carries no provenance,
    and B1-prov is B1."""
    name = "B1-prov"

    def __init__(self, ctx: A.EpisodeContext):
        super().__init__(ctx)
        self.tau_prov = ctx.cell.detector().tau_det

    def provenance_alarm(self, t: int) -> bool:
        o = self._obs
        return (o is not None and o.t == t and o.bought is not None
                and o.bought.target == COMMIT and o.provenance is not None
                and o.provenance > self.tau_prov)

    def alarmed_target(self, t: int) -> str | None:
        target = super().alarmed_target(t)
        if target is None and self.provenance_alarm(t):
            target = COMMIT
        return target


# ---------------------------------------------------------------------------------------
# B2-B6 (S9.2)
# ---------------------------------------------------------------------------------------


class B2UniformRandom(_Baseline):
    """S6: "Spreading the budget uniformly over every stage and task": each task one target
    drawn uniformly over the four -- equal COVERAGE, not equal spending (a spend-equal split
    would be cost-greedy in disguise)."""
    name = "B2 uniform random"
    randomised = True

    def distribution(self) -> dict:
        return {k: 1.0 / len(C.TARGETS) for k in C.TARGETS}

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        return self.action(self.draw(t, self.distribution(), "b2"))


class B3AuditOnInsertion(_Baseline):
    """The insertion audit is the memory carrier's audit (D2), every task."""
    name = "B3 audit-on-insertion"

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        return self._act(t, "memory")


class B4AuditOnRetrieval(_Baseline):
    """The retrieval audit is the queue carrier's audit (D2), every task."""
    name = "B4 audit-on-retrieval"

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        return self._act(t, "queue")


class B5RiskScore(_Baseline):
    """S9.2 "Risk-score thresholding": sweeps memory, queue, skill in a fixed rotation (by
    t); on the task after a sweep whose carrier score (scoring.carrier_score, the v2 carrier
    posterior at the cell's depth) exceeds tau5, the commit.  tau5 is tuned on dev (T18)."""
    name = "B5 risk-score"

    def __init__(self, ctx: A.EpisodeContext, tau5: float = TAU5_DEFAULT):
        super().__init__(ctx)
        self.tau5 = tau5
        self.detector = ctx.cell.detector()
        self._escalate = False

    def carrier_score(self, obs: A.Observation) -> float | None:
        if obs.bought is None or obs.bought.target == COMMIT or not obs.scores:
            return None
        return scoring.carrier_score(list(obs.scores),
                                     self.detector.at_depth(obs.bought.depth).d_prime)

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        if self._escalate:
            return self._act(t, COMMIT)
        return self._act(t, SWEEP_TARGETS[t % len(SWEEP_TARGETS)])

    def observe(self, t: int, obs: A.Observation) -> None:
        super().observe(t, obs)
        post = self.carrier_score(obs)
        self._escalate = post is not None and post > self.tau5
        if post is not None:
            self._log.append({"t": t, "score": round(post, 12), "escalate": self._escalate})


class B6TwoStage(_Baseline):
    """S9.2 "Adaptive-contracts-inspired two-stage check" [1]: a screen of a sweep carrier
    drawn uniformly; if it raises an alarm, the same carrier is confirmed on the next task.
    Only the confirmation's alarm quarantines (the screen alone does not: emptying the
    carrier on the screen would leave nothing to confirm).  Both stages run at the cell's
    depth (C16), so the stages differ in timing, not in depth."""
    name = "B6 two-stage"
    randomised = True

    def __init__(self, ctx: A.EpisodeContext):
        super().__init__(ctx)
        self._confirm: str | None = None          # target to confirm at the next task
        self._stage: dict = {}                    # t -> "screen" | "confirm"

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        if self._confirm is not None:
            target, self._stage[t] = self._confirm, "confirm"
            self._confirm = None
            self._log.append({"t": t, "confirm": target})
            return self.action(target)
        self._stage[t] = "screen"
        dist = {k: 1.0 / len(SWEEP_TARGETS) for k in SWEEP_TARGETS}
        return self.action(self.draw(t, dist, "b6"))

    def observe(self, t: int, obs: A.Observation) -> None:
        super().observe(t, obs)
        if self._stage.get(t) == "screen" and obs.bought is not None and obs.alarm:
            self._confirm = obs.bought.target

    def quarantine(self, t: int) -> str | None:
        if self._stage.get(t) != "confirm":
            return None
        return super().quarantine(t)


# ---------------------------------------------------------------------------------------
# cost-greedy (S10.1) and randomised stage-weighted (S11)
# ---------------------------------------------------------------------------------------


class CostGreedy(_Baseline):
    """S10.1: "a cost-greedy allocator that audits cheap carriers more": each task a target
    drawn with probability proportional to 1 / kappa (the cell's price at its depth)."""
    name = "cost-greedy"
    randomised = True

    def distribution(self) -> dict:
        w = {k: 1.0 / self.ctx.kappa[k] for k in C.TARGETS}
        s = sum(w.values())
        return {k: v / s for k, v in w.items()}

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        return self.action(self.draw(t, self.distribution(), "greedy"))


class StageWeightedRandomised(_Baseline):
    """S11: "randomizing a simple stage-weighted policy": each task a target drawn by fixed
    weights over (memory, queue, skill, commit) -- no belief, the baseline alarm rule."""
    name = "SW randomised"
    randomised = True

    def __init__(self, ctx: A.EpisodeContext, weights: str = SW_DEFAULT):
        super().__init__(ctx)
        if weights not in SW_WEIGHTS:
            raise ValueError(f"weights={weights!r} is not one of {sorted(SW_WEIGHTS)}")
        self.weights = weights
        w = dict(zip(C.TARGETS, SW_WEIGHTS[weights]))
        s = sum(w.values())
        self._dist = {k: v / s for k, v in w.items()}
        self._log.append({"sw_weights": weights})

    def distribution(self) -> dict:
        return dict(self._dist)

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        return self.action(self.draw(t, self._dist, "sw"))


# ---------------------------------------------------------------------------------------
# Controls (D28)
# ---------------------------------------------------------------------------------------


class OracleControl(_Baseline):
    """POSITIVE CONTROL (D28), not a competitor.  The draft's "evaluator-known
    carrier/trigger state" (L2): after each task's audit the runner hands it c_t
    (`quarantine_state`) and it quarantines EVERY carrier whose bit is 1, without needing an
    audit -- v3 poison propagates (note -> skill, queue) inside the insertion task, so the
    seeded carrier alone is not enough (M1 smoke: V = 0.525 at rho = 0, Delta = 4).  It is
    never told iota, sigma or the payload.  It still audits the seeded carrier(s) every task
    (in turn when two are seeded); no attack (attacked empty): the commit, as B1.  Its own
    alarms quarantine nothing: c_t decides.  The runner hands c_t to this class only."""
    name = "Oracle (+)"

    def __init__(self, ctx: A.EpisodeContext, attacked=()):
        super().__init__(ctx)
        ks = (attacked,) if isinstance(attacked, str) else tuple(attacked or ())
        for k in ks:
            if k not in TARGET_OF_CARRIER:
                raise ValueError(f"attacked carrier {k!r} is not one of {C.CARRIERS}")
        self._targets = tuple(TARGET_OF_CARRIER[k] for k in ks) or (COMMIT,)

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        return self._act(t, self._targets[t % len(self._targets)])

    def quarantine(self, t: int) -> str | None:
        return None                      # the runner calls quarantine_state instead

    def quarantine_state(self, t: int, c: tuple) -> tuple:
        """Lines 8-9 of the control: every carrier (config.CARRIERS order) with c_t[k] = 1."""
        if len(c) != len(C.CARRIERS) or any(b not in (0, 1) for b in c):
            raise ValueError(f"c_t={c!r} is not a {len(C.CARRIERS)}-bit vector")
        ks = tuple(k for k, b in zip(C.CARRIERS, c) if b)
        if ks:
            self._log.append({"t": t, "quarantine": list(ks)})
        return ks


# ---------------------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------------------

#: The competitors (sentinel-v3.md S9: B1-B6, plus cost-greedy, SW randomised, B1-prov).
#: B7 is the small-game minimax (T21), not a per-episode policy.
BASELINES = {c.name: c for c in (B1AuditAtCommit, B2UniformRandom, B3AuditOnInsertion,
                                 B4AuditOnRetrieval, B5RiskScore, B6TwoStage, CostGreedy,
                                 StageWeightedRandomised, B1Provenance)}
#: Controls, read before any Sentinel number (D28).  The negative control is the Delta = 0
#: cell: there no baseline that only sweeps carriers may beat B1 (plan S7).
CONTROLS = {OracleControl.name: OracleControl}
DELTA0_CONTROL = {"delta": 0, "reference": B1AuditAtCommit.name}
#: The baselines that never audit the commit: the ones the Delta = 0 control compares to B1.
SWEEP_ONLY = (B3AuditOnInsertion.name, B4AuditOnRetrieval.name, B6TwoStage.name)
#: One-factor sensitivity of B1's binding rule.
SENSITIVITY = {B1Exhaust.name: B1Exhaust}
ALL = {**BASELINES, **CONTROLS, **SENSITIVITY}


def make_baseline(name: str, ctx: A.EpisodeContext, *, attacked=(), tuned=None) -> A.PolicyV3:
    """Every system of this module by name.  `attacked` is read by the Oracle control only
    (the evaluator passes the seeded carrier(s)); `tuned` carries T18's choices
    ("tau5" for B5, "sw_weights" for SW randomised)."""
    tuned = tuned or {}
    if name not in ALL:
        raise KeyError(f"unknown v3 baseline {name!r}; known: {sorted(ALL)}")
    if name == OracleControl.name:
        return OracleControl(ctx, attacked=attacked)
    if attacked:
        raise ValueError(f"{name} is not told the attacked carrier (only {OracleControl.name} is)")
    if name == B5RiskScore.name:
        return B5RiskScore(ctx, tau5=tuned.get("tau5", TAU5_DEFAULT))
    if name == StageWeightedRandomised.name:
        return StageWeightedRandomised(ctx, weights=tuned.get("sw_weights", SW_DEFAULT))
    return ALL[name](ctx)


def factory(name: str, **kw) -> A.PolicyFactory:
    """api.PolicyFactory for `name` (one fresh policy per episode)."""
    if name not in ALL:
        raise KeyError(f"unknown v3 baseline {name!r}")
    return lambda ctx: make_baseline(name, ctx, **kw)
