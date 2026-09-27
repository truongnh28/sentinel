"""v3/library.py -- the restricted policy library Pi of Algorithm 1 line 5 (plan T11).

Draft S5.2: "a restricted policy library (28 parameterised policies spanning stage-weighted,
belief-threshold and carrier-rotation families)".  v3 builds 8 + 12 + 8 members on the
frozen contract (v3/config.py, v3/api.py), reusing v2's grids (carrier_policies._SW,
_TAUS, _FLOORS) and the logic of v2's three families through a thin adapter.

WHAT A MEMBER DOES.  It chooses the audit TARGET of task t, nothing else:
  * depth is the cell's (C16, PolicyBase.action); no member has a depth parameter;
  * lines 8-9 (quarantine) are Sentinel's (T12 line8, T15): `quarantine` is always None;
  * line 7 is Sentinel's too: a member READS the shared b_t through api.BeliefAPI and never
    updates it, unless it is built with owns_belief=True to run standalone (then `observe`
    calls belief.update; whoever quarantines conditions the belief).
A member exposes its decision at t as a DISTRIBUTION over targets (`distribution`); `act`
draws from it with core.seed_of(ctx.rng_seed, ...), and the decision log records the
distribution and the realised target (S5.3: the attacker knows the policy, not the draw).

THE THREE FAMILIES.
    SW  stage-weighted (8)   the target drawn by fixed weights over (memory, queue, skill,
                             commit): v2's _SW, unchanged.  L-SW-commit is B1 at the cell's
                             depth, the corner of the family.  Reads no belief.
    BT  belief-threshold (12) review the commit while p_attack <= tau; above it, draw a
                             sweep carrier from floor * uniform + (1 - floor) * posterior
                             carrier mass (v2's rule).  tau in {4 band positions} x floor in
                             v2's _FLOORS.
    RO  carrier-rotation (8) cycle through `order`, each target held `period` tasks.
                             order in {c3 = the three sweeps, c4 = + the commit} x period
                             {1, 2} x PHASE {random, highest-posterior} (O10).

BT: TAU IN THE BAND OF PROP. 6.1 (paper v2, prop:res-lock).  In v2 every BT member was
locked: the rule "review the commit iff p_attack <= tau" is constant (always or never)
unless p_floor < tau < p0, where p0 is the prior attack probability and
p_floor = p0 f / (p0 f + 1 - p0), f the prior share of attack hypotheses whose likelihood
equals the null's under every observation the policy can buy.  v2's absolute
tau in {0.3, 0.5, 0.7, 0.9} missed the band (0.3398, 0.5) at every H.  v3 therefore
declares tau as a POSITION u in the band: tau = p_floor + u (p0 - p_floor), with
u in v2's _TAUS = {0.3, 0.5, 0.7, 0.9} reused as positions, so every BT tau lies strictly
inside the band by construction.  The band (`Band`) is computed from the belief's model
before tuning and passed to the members: `band_prop61(p0, f)` (the proposition's floor)
or `band_reachable(p0, p_values)` (the lowest p_attack seen on reachable histories, which
is >= the proposition's floor, so its band lies inside the proposition's).

RO: THE PHASE AXIS (O10).  Depth is fixed by the cell, so v2's RO-d2 and RO-d3 play
identically; the depth axis is replaced by the phase:
    random     v2's: one phase drawn per episode, uniform on the n * period offsets;
    posterior  each rotation cycle (n * period tasks) starts at the order's target whose
               carrier has the highest posterior mass at the cycle's first call (ties by a
               seeded draw), then visits every other target once.  Every cycle still
               covers every target, which keeps the rotation's coverage property; the
               belief chooses where each cycle begins.

THE GATE BEFORE TUNING (sentinel-v3.md, Algorithm 1 table, "Thu vien").  `decision_gate`
checks that each family has at least one member that CHANGES A DECISION on a reachable
history: its decision at some task differs from B1's (the commit, with probability 1).
For the families whose members read b_t (BT, RO) it also asks for a member whose decision
differs between two reachable histories (its action reads the evidence), and for BT a
member whose commit/sweep rule is not constant -- Prop. 6.1's lock broken.  A history is a
response script (t, action) -> Observation: all quiet, or one alarm at task j; both are
reachable because the detector misses and false-alarms with positive probability.  The
gate takes any BeliefAPI factory, so T15/T18 run it with the particle filter (T9); the
tests run it with a stub.

Randomness comes only from core.seed_of(ctx.rng_seed, ...).  Stdlib only.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import carrier_policies as CP
from core import seed_of
from v3 import api as A
from v3 import config as C

COMMIT = "commit"
#: The three sweep targets (memory, queue, skill), in config.TARGETS order.
SWEEP_TARGETS = tuple(t for t in C.TARGETS if t != COMMIT)
#: B1's decision at every task: the commit with probability 1 (S5.2, the baseline to beat).
B1_DECISION = {COMMIT: 1.0}

FAMILIES = ("SW", "BT", "RO")
#: SW: v2's eight weight vectors over config.TARGETS = (memory, queue, skill, commit).
SW_WEIGHTS = dict(CP._SW)
#: BT: v2's _TAUS reused as POSITIONS u in the Prop. 6.1 band (module docstring).
BT_TAU_POSITIONS = tuple(CP._TAUS)
#: BT: v2's uniform floors mixed into the posterior carrier draw.
BT_FLOORS = tuple(CP._FLOORS)
#: RO: v2's two orders.
RO_ORDERS = {"c3": SWEEP_TARGETS, "c4": tuple(C.TARGETS)}
RO_PERIODS = (1, 2)
#: RO: O10's phase axis, in config.RO_AXIS order, with short member-name labels.
RO_PHASES = dict(zip(("random", "posterior"), C.RO_AXIS))


# ---------------------------------------------------------------------------------------
# The band of Prop. 6.1 (paper v2)
# ---------------------------------------------------------------------------------------


def prop61_floor(p0: float, f: float) -> float:
    """Prop. 6.1 of paper v2: after any history p_attack >= p0 f / (p0 f + 1 - p0), where f
    is the prior share of attack hypotheses no buyable observation can inform."""
    if not 0.0 < p0 < 1.0:
        raise ValueError(f"p0={p0} is not a probability in (0, 1)")
    if not 0.0 <= f <= 1.0:
        raise ValueError(f"f={f} is not a share in [0, 1]")
    return p0 * f / (p0 * f + 1.0 - p0)


@dataclass(frozen=True)
class Band:
    """(p_floor, p0): the open interval a BT tau must lie in (Prop. 6.1 of paper v2)."""
    p_floor: float
    p0: float
    source: str                            # "prop6.1" | "reachable" | a caller's label

    def __post_init__(self):
        if not 0.0 < self.p0 < 1.0:
            raise ValueError(f"p0={self.p0} is not a probability in (0, 1)")
        if not 0.0 <= self.p_floor < self.p0:
            raise ValueError(f"empty band ({self.p_floor}, {self.p0}): every belief-"
                             f"threshold member would be locked (Prop. 6.1)")

    def contains(self, tau: float) -> bool:
        return self.p_floor < tau < self.p0

    def tau(self, u: float) -> float:
        """The tau at position u in (0, 1) of the band."""
        if not 0.0 < u < 1.0:
            raise ValueError(f"band position u={u} is not in (0, 1)")
        return self.p_floor + u * (self.p0 - self.p_floor)


def band_prop61(p0: float, f: float) -> Band:
    """The band of Prop. 6.1 from the belief's prior attack probability and f."""
    return Band(prop61_floor(p0, f), p0, "prop6.1")


def band_reachable(p0: float, p_values) -> Band:
    """The band whose floor is the lowest p_attack seen on reachable histories (e.g. dev
    episodes or `decision_gate` scripts).  Prop. 6.1 says that floor is >= the
    proposition's, so this band lies inside the proposition's band."""
    vals = [float(p) for p in p_values]
    if not vals:
        raise ValueError("band_reachable needs at least one p_attack value")
    return Band(min(vals), p0, "reachable")


def p_attack(belief: A.BeliefAPI) -> float:
    """Pr[attacked | b_t], the quantity of Prop. 6.1, read through the frozen BeliefAPI."""
    return float(belief.bin_features().p_attack)


# ---------------------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------------------


class Member(A.PolicyBase):
    """A library member: chooses the target of task t; the cell fixes the depth; lines 7-9
    are Sentinel's.  Subclasses implement `distribution(t)`."""
    name = "member"
    family = ""
    reads_belief = False

    def __init__(self, ctx: A.EpisodeContext, *, name: str | None = None,
                 belief: A.BeliefAPI | None = None, owns_belief: bool = False):
        super().__init__(ctx)
        if name is not None:
            self.name = name
        if self.reads_belief:
            if belief is None:
                raise ValueError(f"{self.name} reads b_t: pass the shared BeliefAPI")
            if not isinstance(belief, A.BeliefAPI):
                raise TypeError(f"{self.name}: belief does not implement api.BeliefAPI")
        self.belief = belief
        self.owns_belief = owns_belief and belief is not None

    # --- the decision ---------------------------------------------------------------
    def distribution(self, t: int) -> dict:
        """target -> probability at task t (sums to 1); idempotent within a task."""
        raise NotImplementedError

    def rng(self, *tag) -> random.Random:
        return random.Random(seed_of(self.ctx.rng_seed, "lib", self.name, *tag))

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        dist = self.distribution(t)
        r, acc, pick = self.rng(t, "draw").random(), 0.0, None
        for k in C.TARGETS:
            p = dist.get(k, 0.0)
            if p <= 0.0:
                continue
            acc += p
            pick = k
            if r < acc:
                break
        self._log.append({"t": t, "member": self.name,
                          "dist": {k: round(dist.get(k, 0.0), 12) for k in C.TARGETS},
                          "target": pick})
        return self.action(pick)

    # --- line 7 is Sentinel's; lines 8-9 are Sentinel's -------------------------------
    def observe(self, t: int, obs: A.Observation) -> None:
        if self.owns_belief:
            self.belief.update(t, obs)

    def quarantine(self, t: int) -> str | None:
        return None


class StageWeighted(Member):
    """SW: each task, the target drawn with probability proportional to fixed weights."""
    family = "SW"

    def __init__(self, ctx, *, weights: str, **kw):
        super().__init__(ctx, **kw)
        if weights not in SW_WEIGHTS:
            raise ValueError(f"weights={weights!r} is not one of {sorted(SW_WEIGHTS)}")
        w = dict(zip(C.TARGETS, SW_WEIGHTS[weights]))
        s = sum(w.values())
        self._dist = {k: v / s for k, v in w.items()}

    def distribution(self, t: int) -> dict:
        return dict(self._dist)


class BeliefThreshold(Member):
    """BT: the commit while p_attack <= tau; above it a sweep carrier drawn from
    floor * uniform + (1 - floor) * the posterior carrier mass over the sweeps.

    Built from a band position u (the library) or, for checks only, an absolute tau."""
    family = "BT"
    reads_belief = True

    def __init__(self, ctx, *, floor: float, u: float | None = None, band: Band | None = None,
                 tau: float | None = None, **kw):
        super().__init__(ctx, **kw)
        if not 0.0 <= floor <= 1.0:
            raise ValueError(f"floor={floor} is not in [0, 1]")
        if (u is None) == (tau is None):
            raise ValueError("give a band position u (with a band) or an absolute tau")
        if u is not None:
            if band is None:
                raise ValueError(f"{self.name}: tau is a position in the Prop. 6.1 band; "
                                 f"pass the band (band_prop61 / band_reachable)")
            tau = band.tau(u)
        self.u, self.band, self.tau, self.floor = u, band, float(tau), float(floor)
        self._log.append({"member": self.name, "tau": self.tau, "u": u,
                          "band": None if band is None else [band.p_floor, band.p0],
                          "band_source": None if band is None else band.source})

    def distribution(self, t: int) -> dict:
        if p_attack(self.belief) <= self.tau:
            return dict(B1_DECISION)
        mass = self.belief.carrier_mass()
        m = {k: max(0.0, float(mass.get(C.CARRIER_OF_TARGET[k], 0.0))) for k in SWEEP_TARGETS}
        tot, u = sum(m.values()), 1.0 / len(SWEEP_TARGETS)
        return {k: self.floor * u + (1.0 - self.floor) * (m[k] / tot if tot > 0 else u)
                for k in SWEEP_TARGETS}


class CarrierRotation(Member):
    """RO: cycle through `order`, each target held `period` tasks; the phase is random
    (v2) or set by the posterior at each cycle's start (O10)."""
    family = "RO"

    def __init__(self, ctx, *, order: str, period: int, phase: str, **kw):
        if order not in RO_ORDERS:
            raise ValueError(f"order={order!r} is not one of {sorted(RO_ORDERS)}")
        if period not in RO_PERIODS:
            raise ValueError(f"period={period!r} is not one of {RO_PERIODS}")
        if phase not in RO_PHASES:
            raise ValueError(f"phase={phase!r} is not one of {sorted(RO_PHASES)}")
        self.reads_belief = phase == "posterior"
        super().__init__(ctx, **kw)
        self.order, self.period, self.phase = RO_ORDERS[order], period, phase
        self.cycle = len(self.order) * period
        self._anchor: dict = {}                      # cycle index -> starting order index
        if phase == "random":
            self._offset = self.rng("ro-phase").randrange(self.cycle)
            self._log.append({"member": self.name, "ro_phase": self._offset})

    def _start(self, t: int) -> int:
        c = t // self.cycle
        if c not in self._anchor:
            mass = self.belief.carrier_mass()
            m = [float(mass.get(C.CARRIER_OF_TARGET[k], 0.0)) for k in self.order]
            top = max(m)
            tied = [j for j, v in enumerate(m) if math.isclose(v, top, rel_tol=1e-12,
                                                               abs_tol=1e-15)]
            j0 = tied[0] if len(tied) == 1 else self.rng(c, "ro-tie").choice(tied)
            self._anchor[c] = j0
            self._log.append({"t": t, "member": self.name, "ro_cycle": c, "ro_start": j0})
        return self._anchor[c]

    def target_at(self, t: int) -> str:
        n = len(self.order)
        if self.phase == "random":
            return self.order[((t + self._offset) // self.period) % n]
        return self.order[(self._start(t) + (t % self.cycle) // self.period) % n]

    def distribution(self, t: int) -> dict:
        return {self.target_at(t): 1.0}


# ---------------------------------------------------------------------------------------
# The registry: 8 SW + 12 BT + 8 RO
# ---------------------------------------------------------------------------------------


def _fmt(x: float) -> str:
    return f"{x:.4g}"


def _build_library() -> dict:
    lib = {}
    for w in SW_WEIGHTS:
        lib[f"L-SW-{w}"] = (StageWeighted, {"weights": w})
    for u in BT_TAU_POSITIONS:
        for i, fl in enumerate(BT_FLOORS):
            lib[f"L-BT-u{_fmt(u)}-f{i}"] = (BeliefThreshold, {"u": u, "floor": fl})
    for o in RO_ORDERS:
        for p in RO_PERIODS:
            for ph in RO_PHASES:
                lib[f"L-RO-{o}-p{p}-{ph}"] = (CarrierRotation,
                                              {"order": o, "period": p, "phase": ph})
    return lib


#: name -> (class, parameters).  Parameters are declared here, before tuning (L1).
LIBRARY = _build_library()
MEMBERS = tuple(LIBRARY)


def family_of(name: str) -> str:
    return LIBRARY[name][0].family


def by_family() -> dict:
    out = {f: [] for f in FAMILIES}
    for n in MEMBERS:
        out[family_of(n)].append(n)
    return out


def make_member(name: str, ctx: A.EpisodeContext, *, belief: A.BeliefAPI | None = None,
                band: Band | None = None, owns_belief: bool = False) -> Member:
    """One member for one episode.  BT and RO-posterior members need the shared belief;
    BT members need the Prop. 6.1 band too.  owns_belief=True only to run a member
    standalone (its observe() then updates the belief)."""
    if name not in LIBRARY:
        raise KeyError(f"unknown library member {name!r}")
    cls, kw = LIBRARY[name]
    extra = {"band": band} if cls is BeliefThreshold else {}
    return cls(ctx, name=name, belief=belief, owns_belief=owns_belief, **kw, **extra)


def make_library(ctx: A.EpisodeContext, *, belief: A.BeliefAPI, band: Band) -> dict:
    """All 28 members for one episode, sharing Sentinel's belief (which they only read)."""
    return {n: make_member(n, ctx, belief=belief, band=band) for n in MEMBERS}


def factory(name: str, *, belief_factory: A.BeliefFactory, band: Band,
            delta_hat: int | None = None) -> A.PolicyFactory:
    """api.PolicyFactory running `name` standalone (it owns a fresh belief per episode)."""
    if name not in LIBRARY:
        raise KeyError(f"unknown library member {name!r}")
    return lambda ctx: make_member(name, ctx, belief=belief_factory(ctx, delta_hat),
                                   band=band, owns_belief=True)


# ---------------------------------------------------------------------------------------
# The gate before tuning: each family has a member that changes a decision
# ---------------------------------------------------------------------------------------

#: A clean item's mean score (observe.item_mean), and the margin of a scripted alarm
#: over the detector threshold.
QUIET_SCORE = 0.0
ALARM_MARGIN = 1.0


def scripted_observation(ctx: A.EpisodeContext, t: int, action: A.AuditAction | None,
                         alarm: bool) -> A.Observation:
    """A reachable o_t for `action`: one object written at t, quiet or over threshold."""
    if action is None:
        return A.Observation(t=t, requested=None, bought=None, checkpoint=True)
    s = ctx.cell.detector().tau_det + ALARM_MARGIN if alarm else QUIET_SCORE
    return A.Observation(t=t, requested=action, bought=action, scores=(s,), alarm=alarm,
                         written_at=(t,), checkpoint=True)


def gate_scripts(H: int) -> dict:
    """The reachable histories of the gate: all quiet, and one alarm at task j for every
    j (on whatever the member bought there).  label -> respond(ctx, t, action)."""
    out = {"quiet": lambda ctx, t, a: scripted_observation(ctx, t, a, False)}
    for j in range(H):
        out[f"alarm@{j}"] = (lambda jj: lambda ctx, t, a:
                             scripted_observation(ctx, t, a, t == jj))(j)
    return out


def _same(d1: dict, d2: dict) -> bool:
    return all(math.isclose(d1.get(k, 0.0), d2.get(k, 0.0), abs_tol=1e-12)
               for k in C.TARGETS)


def decision_trace(build, ctx: A.EpisodeContext, make_belief, respond) -> list:
    """Play one reachable history with a fresh belief and member; the decision
    (distribution) at every task.  build(ctx, belief) -> Member.  Every action is bought
    (the gate asks what a member would decide, not what a budget allows: O14 is line 5's)."""
    belief = make_belief()
    m = build(ctx, belief)
    trace = []
    for t in range(ctx.H):
        trace.append(m.distribution(t))
        a = m.act(t, ctx.budget)
        o = respond(ctx, t, a)
        if not m.owns_belief:
            belief.update(t, o)                      # line 7, played here as Sentinel does
        m.observe(t, o)
    return trace


@dataclass
class GateReport:
    """Per member: differs_from_b1 (some decision is not B1's), reads_history (two
    histories give different decisions at one task), both_rules (BT: commits on some
    history and sweeps on another -- the Prop. 6.1 lock broken)."""
    members: dict = field(default_factory=dict)       # name -> dict of the three flags
    families: dict = field(default_factory=dict)      # name -> family

    def changing(self, family: str) -> list:
        return [n for n, f in self.families.items()
                if f == family and self.members[n]["differs_from_b1"]]

    def reading(self, family: str) -> list:
        return [n for n, f in self.families.items()
                if f == family and self.members[n]["reads_history"]]

    def unlocked_bt(self) -> list:
        return [n for n, f in self.families.items()
                if f == "BT" and self.members[n]["both_rules"]]

    def failures(self) -> list:
        out = []
        for fam in sorted(set(self.families.values())):
            if not self.changing(fam):
                out.append(f"{fam}: no member changes a decision from B1's")
            if fam in ("BT", "RO") and not self.reading(fam):
                out.append(f"{fam}: no member's decision reads the history")
        if "BT" in self.families.values() and not self.unlocked_bt():
            out.append("BT: every member's commit rule is constant (Prop. 6.1 lock)")
        return out

    @property
    def passed(self) -> bool:
        return not self.failures()


def decision_gate(ctx: A.EpisodeContext, make_belief, band: Band | None = None, *,
                  builders: dict | None = None, scripts: dict | None = None) -> GateReport:
    """Run every member on every reachable history (gate_scripts by default).
    make_belief() -> a fresh BeliefAPI at b_0 (the particle filter in T15/T18, a stub in
    the tests).  builders: name -> (family, build(ctx, belief)); default the 28 members."""
    if builders is None:
        builders = {n: (family_of(n),
                        (lambda nn: lambda c, b: make_member(nn, c, belief=b, band=band))(n))
                    for n in MEMBERS}
    scripts = scripts if scripts is not None else gate_scripts(ctx.H)
    rep = GateReport()
    for name, (fam, build) in builders.items():
        traces = [decision_trace(build, ctx, make_belief, r) for r in scripts.values()]
        decisions = [d for tr in traces for d in tr]
        differs = any(not _same(d, B1_DECISION) for d in decisions)
        reads = any(not _same(tr[t], traces[0][t]) for tr in traces[1:]
                    for t in range(ctx.H))
        commits = any(_same(d, B1_DECISION) for d in decisions)
        sweeps = any(d.get(COMMIT, 0.0) == 0.0 for d in decisions)
        rep.members[name] = {"differs_from_b1": differs, "reads_history": reads,
                             "both_rules": commits and sweeps}
        rep.families[name] = fam
    return rep
