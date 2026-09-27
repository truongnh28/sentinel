"""v3/sentinel.py -- Sentinel v3 as Algorithm 1, its Table 3 ablations, V3_REGISTRY (plan T15).

Draft Algorithm 1 (every line is one module; this file only wires them):

    1: Delta-hat, chi-hat <- estimate delay and heterogeneity from history   v3/delta_hat.py
    2: if game is small (KH <= threshold) then                              v3/exact.py
    3:     a_t <- exact minimax solution by backward induction ...          v3/exact.py
    5: else a_t <- argmin_pi max_piA L-hat(pi, pi_A | b_t, B_t)              v3/line5.py
    7: execute a_t; observe o_t; b_{t+1} <- Update(b_t, a_t, o_t, beta)      v3/belief_pf.py
    8: if Pr[poisoned | b_{t+1}] > tau and expected harm > eta_Q then        v3/line8.py
    9:     quarantine the highest-posterior carrier

HOW THE LINES ARE CALLED (one Sentinel per episode, api.PolicyV3; the runner's order
act -> buy -> ... -> observe -> quarantine, v3/runner.py)
  __init__     line 1 once: delta_hat.line1 on ctx.postmortems (the post-mortems of the
               EARLIER workflows of the same cell and seed, C12; the runner / sequence pass
               them).  The arm (post-mortem / oracle / prior) is carried in the system
               name (delta_hat.system_name), so record.policy is the arm-tagged name and
               delta_hat.require_headline keeps the oracle arm out of headline sets.
               `self.delta_hat` is what the runner writes into EpisodeRecord.delta_hat.
               Line 7's b_0 (belief_pf.make_belief at Delta-hat), the Prop. 6.1 band from
               that belief (library.band_prop61(prior_p_attack(), uninformable_share())),
               the 28 members sharing b_t (library.make_library), line 5's source, and
               lines 2-3 once: exact.line23(ctx, Delta-hat).
  act(t)       line 3 while its plan is followed (ExactLine3Policy walks the tree); else
               line 5 (Line5.decide: the published x_t / q_t, the draw is the runner's).
  observe(t)   line 7 exactly once per task, in order (belief.update), after line 3's
               tree walk has taken o_t.
  quarantine   lines 8-9 on b_{t+1} (Line8.quarantine: conditions the belief with
               condition_on_quarantine when it fires).

LINES 2-3 WITH LINES 8-9 (the combination; declared).  In the draft lines 8-9 sit OUTSIDE
the if/else of lines 2-5, so they run after every task whichever line chose a_t.  Line 3's
plan has its own quarantine/continue response after an alarm; Sentinel does not play it:
line 8 decides, and the plan's walk FOLLOWS line 8's choice (`FollowingLine3.
follow_quarantine`): quarantining the alarmed carrier = the plan's "quarantine" branch,
no quarantine = "continue".  Line 8 naming another carrier, quarantining where the plan
has no response node, or choosing a branch the plan gives probability 0 takes the
history off the plan: the walk logs it and line 5 decides every later task.  At H >= 6
(K = 4) line 23 logs its infeasibility record and line 5 runs from t = 0 (T13's measured
frontier: H <= 5); every dev workflow has H >= 6.

SENTINEL'S MODEL WORLD (declared, L1).  Line 7 and line 3 model the carrier world
(audit_reading = "carrier": the stage world runs Sentinel through stage_world's adapter,
C2) under the NOMINAL kernel (the robustness to zeta is the tuning's, C6: tau and eta_Q
are chosen by worst-case L over the three kernels).  Every other WorldV3 switch is the
world's own.  In a perturbed-kernel world (tuning, the -transition arm's evaluation) the
belief therefore keeps the nominal kernel -- the world it cannot know.

LINE 5'S SOURCE (Q13).  world.line5 is the switch: "table" (primary, every cell) builds a
line5.TableSource over T14's table; "rollout" builds a line5.RolloutSource over a
rollout.RolloutEngine (Sentinel's band and line 8), and is refused outside the Table 2
headline cells (config.check_world_cell).  A rollout episode must be driven by
rollout.drive(ep, ep.policy.source), which binds the state before every task.
`self.line5_source` (read by the runner into EpisodeRecord.line5_source) is "exact" when
line 3 chose every action of the episode, else the source's name.

TUNED VALUES.  tau and eta_Q per rho come from T18's tuned output (tools/v3_tune.py:
tuned_for(tuned, rho)["tau"], ["eta_q"]); the -transition arm reads a nominal-kernel-only
tuning (`Parts.tuned_nominal`).  The line-5 table is T14's.  V3_REGISTRY resolves both
lazily at the first episode (`default_parts`), so importing this module never needs them;
tests and the dev smoke pass `Parts` explicitly (a StubTable and placeholder values).

TABLE 3 ABLATIONS (sentinel-v3.md "Sentinel theo Algorithm 1 va S7", by their names)
  -randomization          the best DETERMINISTIC policy against the best response (S5.3),
                          not a frozen member as in v2: line 5 is restricted to the members
                          whose decision is a point mass (L-SW-commit and the four
                          highest-posterior-phase rotations, their posterior ties broken by
                          CARRIERS order instead of a seeded draw) and picks, every task,
                          argmin over those members of max over the attacker classes of
                          L-hat -- a pure minimax, no mixture, no draw.
  -alarm memory           stateless: b_t forgets every observation but o_t (the belief is
                          rebuilt from b_0 each task and takes o_t alone; the carriers it
                          quarantined stay removed -- those are facts about the store, not
                          alarms).
  -transition uncertainty tau and eta_Q tuned on the nominal kernel only; evaluated in the
                          perturbed-kernel worlds (the grid's job, T22).
  -benign-drift           drift removed from the belief: betas = {} (belief_pf.make_belief).
  Lines 2-3 are not run in -randomization (the exact plan is a mixture) nor in -alarm
  memory (walking the history tree IS memory); moot wherever H >= 6.
  Reference arms (never headline): oracle-Delta and -regime estimate (line-1 arms "oracle"
  and "prior", tagged names), and Sentinel-rollout (the rollout world, headline cells).

THE GATE (sentinel-v3.md): every arm must change at least one decision of Sentinel's in the
headline cell, else it is printed "NOT EXERCISED", never as a zero effect.
`ablation_gate` runs Sentinel and the arm on the same episodes and compares their decision
traces (per task: the line that decided, the published action distribution, the
quarantine).

Randomness only from core.seed_of via ctx.rng_seed (line 5's draw, line 3's draw, the
members) and the belief's own seeded generator.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
import time
from dataclasses import dataclass, field, replace

from core import seed_of

from v3 import api as A
from v3 import attackers as AT
from v3 import belief_pf as PF
from v3 import config as C
from v3 import delta_hat as DH
from v3 import exact as E
from v3 import library as LIB
from v3 import line5 as L5
from v3 import line8 as L8

ROOT = pathlib.Path(__file__).resolve().parents[1]                   # auditgame/
#: T18's tuned output (tools/v3_tune.TUNED_PATH) and the nominal-kernel-only tuning of
#: the -transition arm (T18 writes it with the kernels restricted to "nominal").
TUNED_PATH = ROOT / "reference" / "v3_tuned.json"
TUNED_NOMINAL_PATH = ROOT / "reference" / "v3_tuned_nominal.json"

# ---------------------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------------------

SENTINEL = "Sentinel"
#: variants (what an arm changes relative to Sentinel)
FULL, NO_RANDOM, STATELESS, NOMINAL, NO_DRIFT = (
    "full", "no-random", "stateless", "nominal-kernel", "no-drift")
VARIANTS = (FULL, NO_RANDOM, STATELESS, NOMINAL, NO_DRIFT)
#: Table 3's four ablations, with the names v3/grid.py gives them.
ABLATIONS = {"Sentinel -randomization": NO_RANDOM,
             "Sentinel -alarm memory": STATELESS,
             "Sentinel -transition uncertainty": NOMINAL,
             "Sentinel -benign-drift": NO_DRIFT}
ORACLE_DELTA = DH.system_name(SENTINEL, DH.ARM_ORACLE)     # "Sentinel [dhat=oracle]"
REGIME_PRIOR = DH.system_name(SENTINEL, DH.ARM_PRIOR)      # "Sentinel [dhat=prior]"
SENTINEL_ROLLOUT = "Sentinel-rollout"
#: Table 3 row label of the draft per ablation (printing only).
TABLE3_LABEL = {"Sentinel -randomization": "- randomization (deterministic)",
                "Sentinel -alarm memory": "- alarm memory (stateless)",
                "Sentinel -transition uncertainty": "- transition uncertainty (nominal kernel)",
                "Sentinel -benign-drift": "- benign-drift modelling"}
#: -transition is evaluated in the perturbed-kernel worlds (the gate compares it there).
PERTURBED_KERNELS = tuple(k for k in C.KERNEL if k != "nominal")

#: -randomization: the members whose decision is a point mass at every task.
DETERMINISTIC_MEMBERS = ("L-SW-commit",) + tuple(
    n for n in LIB.MEMBERS if n.startswith("L-RO-") and n.endswith("-posterior"))

NOT_EXERCISED = "NOT EXERCISED"


class PartMissing(RuntimeError):
    """A part Sentinel needs (T14's table, T18's tuned tau / eta_Q) is not available."""


# ---------------------------------------------------------------------------------------
# Line 1
# ---------------------------------------------------------------------------------------

def line1_for(ctx: A.EpisodeContext, arm: str, true_delta=None) -> DH.Line1:
    """Line 1 from the post-mortems the episode was given (ctx.postmortems: the earlier
    workflows of this cell and seed, in pinned order).  The episode's own position is after
    every post-mortem it holds; delta_hat.line1 refuses anything of this workflow, another
    cell or another seed."""
    pms = tuple(ctx.postmortems)
    order = 1 + max((p.order for p in pms), default=-1)
    td = None
    if arm == DH.ARM_ORACLE:
        td = true_delta if true_delta is not None else ctx.cell.delta
        if not isinstance(td, int) or isinstance(td, bool):
            raise ValueError(f"the oracle-Delta arm needs the workflow's true Delta; cell "
                             f"Delta is {ctx.cell.delta!r} (use the factory's for_placement)")
    return DH.line1(arm, pms, wf_id=ctx.wf_id, order=order, cell_id=C.cell_id(ctx.cell),
                    seed=ctx.seed, true_delta=td, kappa=ctx.kappa)


# ---------------------------------------------------------------------------------------
# Line 7 (and the model world)
# ---------------------------------------------------------------------------------------

def model_context(ctx: A.EpisodeContext) -> A.EpisodeContext:
    """Sentinel's model: the carrier reading under the nominal kernel (module docstring)."""
    return replace(ctx, world=replace(ctx.world, audit_reading="carrier", kernel="nominal"))


class StatelessBelief:
    """-alarm memory: b_t is b_0 moved to t with o_t as its ONLY observation.  Every task
    rebuilds the particle filter from b_0 (same seed), steps it with no observation through
    t - 1 (re-applying the carriers quarantined so far at their tasks) and updates it with
    o_t.  Implements api.BeliefAPI and the Prop. 6.1 read-outs by delegation."""

    def __init__(self, make):
        self._make = make
        self._b = make()
        self._quarantined: dict = {}
        self.t_last = -1

    def update(self, t: int, obs) -> None:
        if t <= self.t_last:
            raise ValueError(f"update(t={t}) after t={self.t_last}")
        b = self._make()
        for tau in range(t):
            b.update(tau, None)
            for k in self._quarantined.get(tau, ()):
                b.condition_on_quarantine(tau, k)
        b.update(t, obs)
        self._b, self.t_last = b, t

    def condition_on_quarantine(self, t: int, carrier: str) -> None:
        self._quarantined.setdefault(t, []).append(carrier)
        self._b.condition_on_quarantine(t, carrier)

    def p_poisoned(self) -> float:
        return self._b.p_poisoned()

    def carrier_mass(self) -> dict:
        return self._b.carrier_mass()

    def expected_harm(self) -> float:
        return self._b.expected_harm()

    def bin_features(self) -> A.BinFeatures:
        return self._b.bin_features()

    def sample(self, n: int, seed: int) -> list:
        return self._b.sample(n, seed)

    def prior_p_attack(self) -> float:
        return self._b.prior_p_attack()

    def uninformable_share(self, targets=None) -> float:
        return self._b.uninformable_share(targets)


class CachedBelief:
    """b_t with its read-outs computed once per belief state: line 5 reads carrier_mass /
    bin_features through every belief-threshold member and the table key, line 8 reads
    p_poisoned / expected_harm.  update and condition_on_quarantine clear the cache; every
    other call is passed through.  Values are the wrapped belief's, unchanged."""

    _READ = ("p_poisoned", "carrier_mass", "expected_harm", "bin_features")

    def __init__(self, inner):
        self.inner = inner
        self._c: dict = {}

    def update(self, t: int, obs) -> None:
        self._c.clear()
        self.inner.update(t, obs)

    def condition_on_quarantine(self, t: int, carrier: str) -> None:
        self._c.clear()
        self.inner.condition_on_quarantine(t, carrier)

    def _get(self, name):
        if name not in self._c:
            self._c[name] = getattr(self.inner, name)()
        v = self._c[name]
        return dict(v) if isinstance(v, dict) else v

    def p_poisoned(self) -> float:
        return self._get("p_poisoned")

    def carrier_mass(self) -> dict:
        return self._get("carrier_mass")

    def expected_harm(self) -> float:
        return self._get("expected_harm")

    def bin_features(self) -> A.BinFeatures:
        return self._get("bin_features")

    def sample(self, n: int, seed: int) -> list:
        return self.inner.sample(n, seed)

    def prior_p_attack(self) -> float:
        return self.inner.prior_p_attack()

    def uninformable_share(self, targets=None) -> float:
        return self.inner.uninformable_share(targets)


def make_belief(ctx: A.EpisodeContext, delta_hat, variant: str = FULL,
                n: int = C.PF_PARTICLES):
    """Line 7's b_0 for one episode in Sentinel's model world; the variant's belief."""
    mctx = model_context(ctx)
    betas = {} if variant == NO_DRIFT else None          # -benign-drift: no drift in b_t
    make = lambda: PF.make_belief(mctx, delta_hat, betas=betas, n=n)   # noqa: E731
    return CachedBelief(StatelessBelief(make) if variant == STATELESS else make())


def band_of(belief) -> LIB.Band:
    """Prop. 6.1's band (p_floor, p0) from the belief's own prior (T11 contract)."""
    return LIB.band_prop61(belief.prior_p_attack(), belief.uninformable_share())


# ---------------------------------------------------------------------------------------
# Lines 2-3, following line 8
# ---------------------------------------------------------------------------------------

class FollowingLine3(E.ExactLine3Policy):
    """Line 3's plan walked along the realised history, with the response after an alarm
    taken from line 8 (module docstring) instead of drawn from the plan."""

    def quarantine(self, t: int):                        # the plan's own response: unused
        raise RuntimeError("Sentinel's quarantine is line 8's; use follow_quarantine")

    def follow_quarantine(self, t: int, carrier: str | None) -> None:
        if self.off_tree:
            return
        if self.node < 0 or self.tree.node_kind[self.node] != "response":
            if carrier is not None:
                self._leave(t, f"line 8 quarantined {carrier} where the plan has no response")
            return
        target = self._alarmed_target()
        if carrier is None:
            lab = E.CONTINUE
        elif carrier == C.CARRIER_OF_TARGET[target]:
            lab = E.QUARANTINE
        else:
            self._leave(t, f"line 8 quarantined {carrier}, the alarm was on {target}")
            return
        dist = self.sol.behaviour(self.tree, self.node)
        if dist.get(lab, 0.0) <= 1e-12:
            self._leave(t, f"line 8 chose {lab!r}, which the plan plays with probability 0")
            return
        self._log.append({"t": t, "line": 3, "response_followed": lab, "plan": dist})
        self.node = self.tree.child.get((self.node, lab, "-"), -1)


_LINE23: dict = {}
#: Bound on the lines 2-3 cache (games are keyed by everything that builds them).
LINE23_CACHE_MAX = 4096


def line23_cached(mctx: A.EpisodeContext, delta_hat) -> E.Line23:
    """exact.line23 once per game: the game is built from (H, Delta-hat, world, cell,
    budget, depths, prices) only (exact.v3_game), so the result -- the exact plan, or the
    infeasibility record and its log line -- is the same for every episode sharing them.
    The first call logs; later calls reuse (the record's runtime is the first call's)."""
    key = (mctx.H, delta_hat, mctx.world, mctx.cell, round(float(mctx.budget), 9),
           tuple(sorted(mctx.depths.items())), tuple(sorted(mctx.kappa.items())),
           tuple(mctx.delegated))
    if key not in _LINE23:
        if len(_LINE23) >= LINE23_CACHE_MAX:
            _LINE23.clear()
        _LINE23[key] = E.line23(mctx, delta_hat)
    return _LINE23[key]


# ---------------------------------------------------------------------------------------
# Line 5 for -randomization: the best deterministic policy against the best response
# ---------------------------------------------------------------------------------------

class DeterministicRotation(LIB.CarrierRotation):
    """A highest-posterior-phase rotation whose tie at a cycle's start goes to the first
    tied target in its order (no seeded draw): a point mass at every task."""

    def _start(self, t: int) -> int:
        c = t // self.cycle
        if c not in self._anchor:
            mass = self.belief.carrier_mass()
            m = [float(mass.get(C.CARRIER_OF_TARGET[k], 0.0)) for k in self.order]
            top = max(m)
            self._anchor[c] = next(j for j, v in enumerate(m)
                                   if math.isclose(v, top, rel_tol=1e-12, abs_tol=1e-15))
            self._log.append({"t": t, "member": self.name, "ro_cycle": c,
                              "ro_start": self._anchor[c]})
        return self._anchor[c]


def deterministic_members(ctx: A.EpisodeContext, belief, band: LIB.Band) -> dict:
    out = {}
    for n in DETERMINISTIC_MEMBERS:
        cls, kw = LIB.LIBRARY[n]
        if cls is LIB.CarrierRotation:
            out[n] = DeterministicRotation(ctx, name=n, belief=belief, **kw)
        else:
            out[n] = LIB.make_member(n, ctx, belief=belief, band=band)
    return out


def point_target(dist: dict) -> str:
    pos = [k for k, p in dist.items() if p > 0.0]
    if len(pos) != 1 or not math.isclose(dist[pos[0]], 1.0, abs_tol=1e-12):
        raise ValueError(f"a deterministic member put mass on {pos}: {dist}")
    return pos[0]


class PureLine5(L5.Line5):
    """Line 5 restricted to pure strategies: argmin over the deterministic members of the
    worst attacker class's L-hat (ties: DETERMINISTIC_MEMBERS order); no mixture, no draw."""

    def decide(self, t, belief, B_t, delta_hat) -> L5.Line5Decision:
        M = self.source.matrix(t, belief, B_t, delta_hat, self.ctx)
        L5.check_classes(M.classes)
        rows = {n: M.L[i] for i, n in enumerate(M.members) if n in self.members}
        if not rows:
            raise ValueError("the loss matrix names none of the deterministic members")
        order = [n for n in DETERMINISTIC_MEMBERS if n in rows]
        dists = {n: self.members[n].distribution(t) for n in order}
        ok = [n for n in order if L5.affordable(dists[n], self.ctx.kappa, B_t)]
        skipped = tuple(n for n in order if n not in ok)
        if not ok:
            d = L5.Line5Decision(t, None, {}, {}, None, M.source, (), skipped,
                                 f"no deterministic member affordable at B_t = {B_t:.6g}")
            self.log.append(d.published())
            return d
        worst = {n: max(float(v) for v in rows[n]) for n in ok}
        pick = min(ok, key=lambda n: (worst[n], ok.index(n)))
        target = point_target(dists[pick])
        d = L5.Line5Decision(t, A.AuditAction(target, self.ctx.depths[target]), {pick: 1.0},
                             {target: 1.0}, worst[pick], M.source, tuple(ok), skipped,
                             M.note)
        self.log.append(d.published())
        return d


# ---------------------------------------------------------------------------------------
# The parts Sentinel is assembled from
# ---------------------------------------------------------------------------------------

def tuned_block(tuned: dict, rho: float) -> dict:
    """tools/v3_tune.tuned_for, restated (a v3 module does not import tools/)."""
    return dict(tuned["rho"][f"{float(rho):g}"])


@dataclass
class Parts:
    """table          T14's line-5 table: lookup(line5.TableKey) -> api.LossMatrix.
    tuned          T18's tuned output (the "tuned" dict): rho -> {"tau", "eta_q", ...}.
    tuned_nominal  the same tuned on the nominal kernel only (-transition).
    R              draws per (member, class) of the rollout source (config.ROLLOUT_R_GRID).
    rollout_members  the members the rollout engine rolls (None = all 28; tests only).
    n_particles    line 7's particles (config.PF_PARTICLES; lower only in tests)."""
    table: object = None
    tuned: dict | None = None
    tuned_nominal: dict | None = None
    R: int = C.ROLLOUT_R_GRID[0]
    rollout_members: tuple | None = None
    n_particles: int = C.PF_PARTICLES
    label: str = ""

    def line8(self, rho: float, nominal: bool = False) -> L8.Line8:
        src, what = ((self.tuned_nominal, "tuned_nominal") if nominal
                     else (self.tuned, "tuned"))
        if src is None:
            raise PartMissing(f"no {what} (T18's tools/v3_tune.py output) for line 8")
        blk = tuned_block(src, rho)
        if blk.get("tau") is None or blk.get("eta_q") is None:
            raise PartMissing(f"rho {rho:g}: tau / eta_Q not tuned in {what} "
                              f"({blk.get('line8_reason', 'no reason given')})")
        return L8.Line8(float(blk["tau"]), float(blk["eta_q"]))

    def source(self, ctx: A.EpisodeContext, band: LIB.Band, line8: L8.Line8):
        if ctx.world.line5 == "rollout":
            if not ctx.cell.is_headline():
                raise ValueError("line5='rollout' runs only in the Table 2 headline cells (Q13)")
            from v3 import rollout as RO
            return L5.RolloutSource(RO.RolloutEngine(band, line8, members=self.rollout_members),
                                    self.R)
        if self.table is None:
            raise PartMissing("no line-5 table (T14's v3/line5_table.py)")
        return L5.TableSource(self.table)


_DEFAULT: dict = {}


def _load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def default_parts() -> Parts:
    """The frozen parts: T18's tuned files and T14's table (resolved once, lazily)."""
    if "parts" not in _DEFAULT:
        table = None
        try:
            from v3 import line5_table as LT                          # T14
            table = LT.load_table()
        except (ImportError, AttributeError, FileNotFoundError):
            table = None
        _DEFAULT["parts"] = Parts(table=table, tuned=_load_json(TUNED_PATH),
                                  tuned_nominal=_load_json(TUNED_NOMINAL_PATH), label="frozen")
    return _DEFAULT["parts"]


# ---------------------------------------------------------------------------------------
# Sentinel
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ArmSpec:
    name: str
    variant: str = FULL
    arm: str = DH.ARM_POSTMORTEM              # line 1's arm
    needs_rollout: bool = False               # Sentinel-rollout: the rollout world only

    def __post_init__(self):
        if self.variant not in VARIANTS:
            raise ValueError(f"variant {self.variant!r} is not one of {VARIANTS}")
        if self.arm not in DH.ARMS:
            raise ValueError(f"line-1 arm {self.arm!r} is not one of {DH.ARMS}")


class Sentinel(A.PolicyBase):
    """Algorithm 1 for one episode (module docstring).

    reads_provenance (fix-a7, decided 27/09): in A7 Sentinel's commit review blocks the
    patch on the provenance channel too (observe.reads_provenance / Inspection.
    commit_alarm), the same commit information as B1-prov; line 7 also reads provenance
    through the belief (belief_pf, O9).  Inert in A0 and on a base without fix-a7."""
    reads_provenance = True

    def __init__(self, ctx: A.EpisodeContext, spec: ArmSpec, parts: Parts,
                 true_delta=None):
        super().__init__(ctx)
        self.name, self.spec = spec.name, spec
        if spec.needs_rollout and ctx.world.line5 != "rollout":
            raise ValueError(f"{spec.name} runs in the rollout world (line5='rollout') only")
        self.trace: list = []                   # (t, line) in execution order
        self._decisions: list = []
        # line 1
        self.l1 = line1_for(ctx, spec.arm, true_delta)
        self.delta_hat = self.l1.delta_hat
        self.trace.append((None, "1"))
        self._log.append({"line": 1, "arm": self.l1.arm, "source": self.l1.source,
                          "delta_hat": self.l1.delta_hat, "chi_hat": self.l1.chi_hat,
                          "n_incidents_seen": self.l1.n_incidents_seen,
                          "n_delays": self.l1.n_delays})
        # line 7's b_0, the band, lines 8-9
        self.belief = make_belief(ctx, self.delta_hat, spec.variant, parts.n_particles)
        self.band = band_of(self.belief)
        self.line8 = parts.line8(ctx.cell.rho, nominal=spec.variant == NOMINAL)
        self._log.append({"line": 7, "variant": spec.variant,
                          "band": [self.band.p_floor, self.band.p0],
                          "tau": self.line8.tau, "eta_q": self.line8.eta_q})
        # line 5
        self.source = parts.source(ctx, self.band, self.line8)
        if spec.variant == NO_RANDOM:
            self.line5 = PureLine5(ctx, self.source,
                                   deterministic_members(ctx, self.belief, self.band))
        else:
            self.line5 = L5.Line5(ctx, self.source,
                                  LIB.make_library(ctx, belief=self.belief, band=self.band))
        # lines 2-3
        self.line3: FollowingLine3 | None = None
        self.line23_diagnostics: dict | None = None   # non-pinned (D33): wall time, RSS
        self.trace.append((None, "2"))
        if spec.variant in (NO_RANDOM, STATELESS):
            self._log.append({"line": 2, "kind": "skipped",
                              "why": f"{spec.variant}: the exact plan is a mixture over the "
                                     f"history tree"})
        else:
            res = line23_cached(model_context(ctx), self.delta_hat)
            entry = {"line": 2, "kind": res.kind}
            if res.record is not None:
                # D33: only the reproducible decision content is pinned; the per-run
                # measurements (wall time, RSS) go to a non-pinned diagnostic channel so
                # the same inputs give the same decision_log_sha256 across runs.
                entry["record"] = res.record.decision_line()
                self.line23_diagnostics = res.record.diagnostics()
            self._log.append(entry)
            if res.exact:
                self.line3 = FollowingLine3(ctx, res)
        self._used_line5 = False
        self._line3_used = False

    # ---- the record's trace fields ----------------------------------------------------
    @property
    def line5_source(self) -> str:
        return "exact" if (self._line3_used and not self._used_line5) else self.source.name

    def on_plan(self) -> bool:
        return self.line3 is not None and not self.line3.off_tree

    # ---- lines 3 / 5 --------------------------------------------------------------------
    def act(self, t: int, B_t: float):
        if self.on_plan():
            a = self.line3.act(t, B_t)
            if not self.line3.off_tree:
                self._line3_used = True
                dist = next((e["x_t"] for e in reversed(self.line3._log)
                             if e.get("t") == t and "x_t" in e), {})
                self.trace.append((t, "3"))
                self._decisions.append({"t": t, "line": 3,
                                        "dist": {k: round(v, 9) for k, v in dist.items()},
                                        "quarantine": None})
                return a
        d = self.line5.decide(t, self.belief, B_t, self.delta_hat)
        self._used_line5 = True
        self.trace.append((t, "5"))
        self._log.append(d.published())
        self._decisions.append({"t": t, "line": 5,
                                "dist": {k: round(v, 9) for k, v in d.dist.items()},
                                "quarantine": None})
        return d.action

    # ---- line 7 -------------------------------------------------------------------------
    def observe(self, t: int, obs: A.Observation) -> None:
        if self.on_plan():
            self.line3.observe(t, obs)
        self.belief.update(t, obs)
        self.trace.append((t, "7"))

    # ---- lines 8-9 ----------------------------------------------------------------------
    def quarantine(self, t: int) -> str | None:
        k = self.line8.quarantine(t, self.belief, self._log)
        if self.on_plan():
            self.line3.follow_quarantine(t, k)
        self.trace.append((t, "8"))
        if self._decisions and self._decisions[-1]["t"] == t:
            self._decisions[-1]["quarantine"] = k
        return k

    def decision_log(self) -> list:
        return list(self._log) + ([] if self.line3 is None else self.line3.decision_log())

    def decisions(self) -> list:
        """Per task: the line that decided, the published action distribution, the
        quarantine (the gate compares these, `ablation_gate`)."""
        return [dict(d) for d in self._decisions]


class SentinelFactory:
    """api.PolicyFactory of one registry name.  parts=None resolves `default_parts()` at
    the first episode.  `for_placement(pl)` gives the oracle-Delta arm the placement's true
    Delta (the attacker-chooses-Delta column); every other arm ignores it."""

    def __init__(self, spec: ArmSpec, parts: Parts | None = None, true_delta=None):
        self.spec, self.parts, self.true_delta = spec, parts, true_delta

    @property
    def name(self) -> str:
        return self.spec.name

    def __call__(self, ctx: A.EpisodeContext) -> Sentinel:
        return Sentinel(ctx, self.spec, self.parts or default_parts(), self.true_delta)

    def with_parts(self, parts: Parts) -> "SentinelFactory":
        return SentinelFactory(self.spec, parts, self.true_delta)

    def for_placement(self, pl) -> "SentinelFactory":
        if self.spec.arm != DH.ARM_ORACLE or pl is None:
            return self
        return SentinelFactory(self.spec, self.parts, int(pl.delta))

    def __repr__(self) -> str:
        return f"SentinelFactory({self.spec.name!r})"


def _specs() -> dict:
    specs = [ArmSpec(SENTINEL)]
    specs += [ArmSpec(n, v) for n, v in ABLATIONS.items()]
    specs += [ArmSpec(ORACLE_DELTA, arm=DH.ARM_ORACLE),
              ArmSpec(REGIME_PRIOR, arm=DH.ARM_PRIOR),
              ArmSpec(SENTINEL_ROLLOUT, needs_rollout=True)]
    out = {}
    for s in specs:
        if s.name in out:
            raise AssertionError(f"duplicate registry name {s.name!r}")
        out[s.name] = s
    return out


SPECS = _specs()
#: name -> api.PolicyFactory (ctx -> Sentinel), as tools/v3_run.policy_factory reads it.
V3_REGISTRY = {n: SentinelFactory(s) for n, s in SPECS.items()}
#: Arms whose numbers may enter a headline row (C12: no oracle / prior-only line 1).
HEADLINE_SYSTEMS = tuple(n for n in V3_REGISTRY if DH.arm_of(n) is None
                         and n != SENTINEL_ROLLOUT)


def registry(parts: Parts) -> dict:
    """V3_REGISTRY bound to explicit parts (tests, the dev smoke)."""
    return {n: f.with_parts(parts) for n, f in V3_REGISTRY.items()}


def check_ready(names=None, parts: Parts | None = None) -> list:
    """What is missing before `names` can run (empty = ready)."""
    p = parts or default_parts()
    names = list(V3_REGISTRY) if names is None else list(names)
    out = []
    if p.table is None and any(n != SENTINEL_ROLLOUT for n in names):
        out.append("line-5 table (T14)")
    if p.tuned is None:
        out.append(f"tuned tau / eta_Q ({TUNED_PATH.name}, T18)")
    if "Sentinel -transition uncertainty" in names and p.tuned_nominal is None:
        out.append(f"nominal-kernel tuning ({TUNED_NOMINAL_PATH.name}, T18)")
    return out


# ---------------------------------------------------------------------------------------
# The gate: every arm must change at least one decision in the headline cell
# ---------------------------------------------------------------------------------------

def _same_decision(a: dict, b: dict) -> bool:
    if a["t"] != b["t"] or a["line"] != b["line"] or a["quarantine"] != b["quarantine"]:
        return False
    keys = set(a["dist"]) | set(b["dist"])
    return all(math.isclose(a["dist"].get(k, 0.0), b["dist"].get(k, 0.0), abs_tol=1e-9)
               for k in keys)


def first_change(ref: list, arm: list):
    """The first task at which two decision traces differ, or None."""
    for x, y in zip(ref, arm):
        if not _same_decision(x, y):
            return x["t"]
    if len(ref) != len(arm):
        return min(len(ref), len(arm))
    return None


def decision_trace(factory, wf, placement, world: C.WorldV3, cell: C.Cell, seed: int,
                   attack: str = "gate") -> list:
    """Run one dev episode and return the policy's decision trace."""
    from v3 import runner as RU
    ep = RU.Episode(wf, placement, factory, world, cell, seed, attack=attack)
    ep.run()
    return ep.policy.decisions()


@dataclass
class GateResult:
    name: str
    exercised: bool
    n_episodes: int
    worlds: tuple
    first: tuple | None = None               # (wf, seed, world kernel, t) of the first change

    def line(self) -> str:
        if self.exercised:
            wf, seed, kern, t = self.first
            return (f"{self.name}: exercised -- first decision change at wf {wf}, seed "
                    f"{seed}, kernel {kern}, task {t} ({self.n_episodes} episodes)")
        return (f"{self.name}: {NOT_EXERCISED} -- no decision differs from Sentinel's in "
                f"{self.n_episodes} episodes of the headline cell (not a zero effect)")


def ablation_gate(factories: dict, episodes: list, cell: C.Cell, *,
                  reference: str = SENTINEL, world: C.WorldV3 = C.PRIMARY) -> dict:
    """factories: name -> factory, `reference` among them.  episodes: [(wf, placement,
    seed)].  Every other arm is run on the same episodes as the reference and their
    decision traces compared; -transition is compared in the perturbed-kernel worlds (where
    it is evaluated).  Returns name -> GateResult."""
    if not cell.is_headline():
        raise ValueError("the gate is read in the Table 2 headline cell")
    ref_f = factories[reference]
    cache: dict = {}

    def ref_trace(w, i, wf, pl, seed):
        key = (w.kernel, i)
        if key not in cache:
            cache[key] = decision_trace(ref_f, wf, pl, w, cell, seed)
        return cache[key]

    out = {}
    for name, f in factories.items():
        if name == reference:
            continue
        spec = getattr(f, "spec", None)
        kernels = (PERTURBED_KERNELS if spec is not None and spec.variant == NOMINAL
                   else (world.kernel,))
        worlds = tuple(replace(world, kernel=k) for k in kernels)
        res = GateResult(name, False, 0, tuple(kernels))
        for w in worlds:
            for i, (wf, pl, seed) in enumerate(episodes):
                res.n_episodes += 1
                t = first_change(ref_trace(w, i, wf, pl, seed),
                                 decision_trace(f, wf, pl, w, cell, seed))
                if t is not None and not res.exercised:
                    res.exercised, res.first = True, (wf.wf_id, seed, w.kernel, t)
        out[name] = res
    return out


def gate_lines(results: dict) -> list:
    return [r.line() for r in results.values()]


# ---------------------------------------------------------------------------------------
# Smoke only: a stub line-5 table and placeholder tuned values (never frozen, never run
# outside tests and `python -m v3.sentinel --smoke`)
# ---------------------------------------------------------------------------------------

class StubTable:
    """SMOKE / TEST ONLY.  lookup(TableKey) -> LossMatrix [28 members x 6 D18 classes]:
    a fixed pseudo-random loss in [0, 1) per (member, class) that moves with the key's h,
    Delta-hat, top carrier and p_attack (rounded to 0.05), so decisions read the belief.
    It is not T14's table and no number from it is a result."""

    def __init__(self, seed: int = 0, members=None, classes=None):
        self.seed = seed
        self.members = tuple(LIB.MEMBERS if members is None else members)
        self.classes = tuple(AT.attacker_classes() if classes is None else classes)
        self.n_lookups = 0
        self._cache: dict = {}

    def lookup(self, key: L5.TableKey) -> A.LossMatrix:
        self.n_lookups += 1
        f = key.features
        pb = round(round(f.p_attack / 0.05) * 0.05, 2)
        k = (key.table_cell, key.h, key.delta_hat, f.top_carrier, pb)
        if k not in self._cache:
            rng = random.Random(seed_of("t15-stub", self.seed, *k))
            L = tuple(tuple(round(rng.random(), 6) for _ in self.classes)
                      for _ in self.members)
            z = tuple(tuple(0.0 for _ in self.classes) for _ in self.members)
            n = tuple(tuple(1 for _ in self.classes) for _ in self.members)
            self._cache[k] = A.LossMatrix(self.members, self.classes, L, z, n, "table",
                                          "t15 stub table (smoke / tests only)")
        return self._cache[k]


def placeholder_tuned(tau: float, eta_q: float, rhos=C.RHO_GRID) -> dict:
    """SMOKE / TEST ONLY: a tuned dict in T18's shape with one (tau, eta_Q) for every rho."""
    return {"smoke": True, "rho": {f"{float(r):g}": {"tau": tau, "eta_q": eta_q}
                                   for r in rhos}}


def stub_parts(**kw) -> Parts:
    """SMOKE / TEST ONLY: the stub table and placeholder (tau, eta_Q) -- robust (0.5,
    0.05) and nominal-kernel (0.7, 0.2), different on purpose so -transition can change a
    decision."""
    base = dict(table=StubTable(), tuned=placeholder_tuned(0.5, 0.05),
                tuned_nominal=placeholder_tuned(0.7, 0.2), label="stub")
    base.update(kw)
    return Parts(**base)


def _smoke(n_workflows: int, rhos, delta: int, seed: int, out=print) -> dict:
    """Dev smoke: the headline cell, Sentinel + the four ablations + the line-1 reference
    arms, every held-out attacker column, workflows in the pinned order through
    v3/sequence.run_sequence (post-mortems carried, C12)."""
    import carrier_runner as CR
    from v3 import corpus as K
    from v3 import runner as RU
    from v3 import sequence as SQ
    parts = stub_parts()
    reg = registry(parts)
    names = [SENTINEL, *ABLATIONS, ORACLE_DELTA, REGIME_PRIOR]
    wfs = [w for w in K.dev_workflows() if w.H >= delta + 1][:n_workflows]
    by_id = {w.wf_id: w for w in wfs}
    man = SQ.order_manifest([w.wf_id for w in wfs])
    summary = {}
    for rho in rhos:
        cell = C.Cell(rho=rho, delta=delta)
        cid = C.cell_id(cell)
        for name in names:
            spec = SPECS[name]
            worlds = ([replace(C.PRIMARY, kernel=k) for k in PERTURBED_KERNELS]
                      if spec.variant == NOMINAL else [C.PRIMARY])
            recs, secs = [], 0.0
            for world in worlds:
                for col in AT.held_out():
                    base = DH.HistoryKey(cid, name if spec.arm == DH.ARM_POSTMORTEM
                                         else SENTINEL, col, seed)

                    def run_one(step, world=world, col=col):
                        nonlocal secs
                        wf = by_id[step.wf_id]
                        pl = AT.by_name(col).plan(wf, delta, world)    # None: clean (N3)
                        fac = reg[name].for_placement(pl)
                        t0 = time.perf_counter()
                        eo = RU.run_episode(wf, pl, fac, world, cell, seed, order=step.order,
                                            attack=col, postmortems=step.postmortems)
                        secs += time.perf_counter() - t0
                        return eo.record, eo.postmortem

                    res = SQ.run_sequence(base, man, run_one, arm=spec.arm,
                                          true_delta=((lambda wf_id: delta)
                                                      if spec.arm == DH.ARM_ORACLE else None),
                                          kappa=None)
                    recs += res.records
            n = len(recs)
            summary[(rho, name)] = {
                "episodes": n, "ms_per_episode": 1000.0 * secs / max(n, 1),
                "harm": sum(r.harm for r in recs) / n,
                "L": sum(RU.loss_of(r) for r in recs) / n,
                "fq": sum(r.fq for r in recs) / n,
                "spent": sum(r.spent for r in recs) / n,
                "sources": sorted({r.line5_source for r in recs}),
                "delta_hat": sorted({r.delta_hat for r in recs}),
                "worlds": [w.kernel for w in worlds]}
            s = summary[(rho, name)]
            out(f"rho {rho:g}  {name:34} n {n:4}  {s['ms_per_episode']:7.1f} ms/ep  "
                f"harm {s['harm']:.3f}  L {s['L']:.3f}  FQ {s['fq']:.3f}  "
                f"dhat {s['delta_hat']}  src {s['sources']}  kernels {s['worlds']}")
        # the gate, on the first workflows x held-out columns
        eps = []
        for w in wfs:
            for col in AT.held_out()[:3]:
                pl = AT.by_name(col).plan(w, delta, C.PRIMARY)
                if pl is not None and CR.survives(w, pl, seed):
                    eps.append((w, pl, seed))
        gate = ablation_gate({n: reg[n] for n in [SENTINEL, *ABLATIONS]}, eps, cell)
        for ln in gate_lines(gate):
            out(f"rho {rho:g}  gate  {ln}")
        summary[(rho, "gate")] = {n: r.exercised for n, r in gate.items()}
    return summary


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="T15 dev smoke (stub table, placeholders)")
    ap.add_argument("--smoke", action="store_true", required=True)
    ap.add_argument("--workflows", type=int, default=4)
    ap.add_argument("--rho", type=float, nargs="+", default=[0.0, 0.5])
    ap.add_argument("--delta", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    import logging
    logging.getLogger("v3.line23").setLevel(logging.ERROR)
    print("DEV SMOKE ONLY: stub line-5 table and placeholder tau / eta_Q -- no number here "
          "is a result", flush=True)
    _smoke(a.workflows, a.rho, a.delta, a.seed, out=lambda s: print(s, flush=True))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(_main())
