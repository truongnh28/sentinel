"""v3/observe.py -- the observation model: what an audit shows the defender (plan T5).

Draft S4 "Defender": "It observes o_t : alarm scores from an imperfect detector with
true-positive rate psi and false-positive rate phi, plus executable checkpoint outcomes."
Draft S8 "Detector": one shared detector for every system (C15: a declared model with
three d', 1.52 / 2.21 / 2.96, from the draft's three (psi, phi)).

WHAT EACH AUDIT SEES (cell = the grid point, world = the model switches)
    sweep of memory / queue / skill at depth d
        every live item of the carrier, one INDEPENDENT score each (D16):
        s ~ N(mu, 1), mu = d' sqrt(d) for a poisoned item, match * d' sqrt(d) for a benign
        drift item while it is visible (D6), 0 otherwise.  Drift is visible for 1 task
        (world.drift = "transient") or forever ("persistent").
        H8: memory is the insertion audit; with world.ingress_visible = False it does not
        see the items that entered through repository ingress (a world-side id set).
    commit at depth d (the patch written at this task, D2 / D20)
        direct patch     mu = d' sqrt(d)
        delegated patch  mu = rho * d'      at EVERY depth: the evidence is the delegating
                                            carrier's provenance, which a deeper patch
                                            review does not read (draft S2, proof of Thm 4)
        clean patch      mu = 0
        A7 only (C1): plus a provenance score of the contributing delegated carriers,
        mu = d'_prov if a poisoned delegated carrier produced the marked patch, else 0.
        d'_prov is a placeholder equal to the cell's detector d' (O9, measured in P3), and
        is one lookup (no sqrt(depth)).
        A7 READING (L2, fix-a7 27/09): provenance is an EXTRA observation channel, not part
        of the alarm.  `alarm` is the patch score over tau_det in every world, so a plain
        policy (B1, ...) behaves identically in A0 and A7.  Only a system that reads the
        channel uses it: B1-prov (`reads_provenance = True`, baselines.B1Provenance),
        whose commit alarm is "either score over tau_det" and whose patch is blocked on
        it (runner step 5, `commit_alarm`), and Sentinel's belief, through its likelihood
        (belief_pf reads Observation.provenance directly).
    checkpoint (every task)
        O8: psi_c = phi_c.  The checkpoint passes iff the task's patch passes its tests,
        i.e. `solved`, which is drawn from seed_of(rs, t, "solve") alone (N4) -- no poison
        label enters it, so it carries no information about poison (Fig. 1 t6 "passes
        tests").  Its likelihood ratio is 1 under every hypothesis.

So B1's miss probability on a delegated patch is P_miss = Phi(z_{1-phi} - rho d') at every
rho and every depth, in A0 and A7 alike (sentinel-v3.md, formula section); B1-prov's in A7
is that times Phi(z_{1-phi} - d'_prov), and its false-alarm rate 1 - (1 - phi)^2.

The world-side scoring is v2's world_v2.DriftDetector, composed (never patched): its seeds
(`v2-score` keyed on (seed, item, task), `v2-patch` keyed on (seed, task_id)), its drift
visibility rule and its D20 patch rule.  v3 adds the provenance score, the checkpoint and
the ingress filter.

WHO USES WHAT
    ObservationModel     runner (T6): world side; it reads the evaluator-only labels
                         through DriftDetector's means, never hands them to a policy.
    Inspection           runner (T6): evaluator record of one audit (items, marker) plus
                         the defender view, `observation(...)` -> api.Observation.
    the pure functions   PF (T9) and rollout (T12): the same means and densities as the
                         world, as functions of a HYPOTHESIS, so belief and world cannot
                         drift apart.  Stdlib floats; T9 vectorises them.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist

from core import seed_of
from world_v2 import DriftDetector

from v3 import api as A
from v3 import config as C

_N = NormalDist()
_LOG_SQRT_2PI = 0.5 * math.log(2.0 * math.pi)

#: D6 of v2: a drift item looks like poison for this many tasks after it is written
#: (transient, primary), or forever (persistent, Prop. 5.11 sensitivity).
DRIFT_VISIBLE = {"transient": 1, "persistent": None}
#: D6 of v2: a visible drift item's mean is match * d' (matched surface statistics).
DRIFT_MATCH = 1.0
#: The patch routes (world_v2.StagedOutcome.patch_via); "" = the patch carries no marker.
VIAS = ("", "direct", "delegated")
#: The sweep targets: the audit targets other than the commit (config.TARGETS).
SWEEP_TARGETS = tuple(t for t in C.TARGETS if t != "commit")


@dataclass(frozen=True)
class CheckpointChannel:
    """O8: the executable checkpoint as a declared channel (psi_c, phi_c).

    psi_c = Pr[checkpoint FAILS | poisoned patch], phi_c = Pr[FAILS | clean patch].  The
    outcome is the task's `solved` draw, which no poison label enters (N4), so both are
    1 - (solve rate): declared equal, not measured (the real-run set measures them, C9)."""
    source: str = "solved"

    def rates(self, solve_rate: float) -> tuple:
        """(psi_c, phi_c) at the agent kernel's solve rate."""
        fail = 1.0 - solve_rate
        return (fail, fail) if C.CHECKPOINT_PSI_EQUALS_PHI else (None, fail)


CHECKPOINT = CheckpointChannel()


# ---------------------------------------------------------------------------------------
# Pure functions: means, densities, miss probabilities (world and belief share them)
# ---------------------------------------------------------------------------------------

def tau_of(phi: float) -> float:
    """tau_det = z_{1-phi}: the one threshold of the shared detector (detector.py)."""
    return _N.inv_cdf(1.0 - phi)


def sweep_dprime(dprime: float, depth: int) -> float:
    """A sweep at depth d: d independent looks, separation d' sqrt(d) (detector.at_depth)."""
    _check_depth(depth)
    return dprime * math.sqrt(depth)


def drift_visible(created_at: int, now: int, drift: str) -> bool:
    """D6: a drift item written at `created_at` still looks anomalous at `now`."""
    window = DRIFT_VISIBLE[drift]
    return window is None or now - created_at < window


def item_mean(poisoned: bool, drift_seen: bool, dprime_eff: float,
              match: float = DRIFT_MATCH) -> float:
    """Mean score of one inspected item (DriftDetector._mean, as a function of the
    hypothesis): d'_eff if poisoned, match*d'_eff if a visible drift item, else 0."""
    if poisoned:
        return dprime_eff
    return match * dprime_eff if drift_seen else 0.0


def patch_mean(has_marker: bool, via: str, rho: float, dprime: float, depth: int) -> float:
    """D20: the commit review's mean score of this task's patch.  `dprime` is the cell's
    depth-1 d'; a delegated patch gets rho*d' whatever the depth."""
    _check_depth(depth)
    _check_via(has_marker, via)
    if not has_marker:
        return 0.0
    if via == "delegated":
        return rho * dprime
    return dprime * math.sqrt(depth)


def provenance_mean(tainted: bool, dprime_provenance: float) -> float:
    """A7 (C1, O9): the provenance score's mean; `tainted` = a poisoned delegated carrier
    produced the marked patch (has_marker and via == 'delegated')."""
    return dprime_provenance if tainted else 0.0


def loglik(s: float, mean: float) -> float:
    """log N(s; mean, 1): the detector's score model (Assumption 2)."""
    return -0.5 * (s - mean) ** 2 - _LOG_SQRT_2PI


def log_lr(s: float, mean: float) -> float:
    """log [N(s; mean, 1) / N(s; 0, 1)] = mean*s - mean^2/2."""
    return mean * s - 0.5 * mean * mean


def lr(s: float, mean: float) -> float:
    return math.exp(min(700.0, log_lr(s, mean)))


def one_of_lr(scores, mean: float, weights=None) -> float:
    """LR of 'exactly one of these items has `mean`, the rest 0' against 'all 0', with
    `weights` the prior over which one (uniform if None): sum_i w_i LR_i."""
    if not scores:
        return 1.0
    if weights is None:
        weights = [1.0 / len(scores)] * len(scores)
    if len(weights) != len(scores):
        raise ValueError("one weight per score")
    return sum(w * lr(s, mean) for s, w in zip(scores, weights))


def p_alarm(mean: float, tau: float) -> float:
    """Pr[s > tau], s ~ N(mean, 1)."""
    return 1.0 - _N.cdf(tau - mean)


def p_miss(mean: float, tau: float) -> float:
    return _N.cdf(tau - mean)


def alarm_loglik(alarm: bool, mean: float, tau: float) -> float:
    """log Pr[alarm | mean]: for a filter that reads the binary alarm only."""
    p = p_alarm(mean, tau)
    p = p if alarm else 1.0 - p
    return math.log(max(p, 1e-300))


def p_miss_commit(rho: float, dprime: float, phi: float, *, via: str = "delegated",
                  depth: int = 1, dprime_provenance: float | None = None) -> float:
    """Pr[a marked patch passes the commit review].  Delegated, patch score only (every
    plain policy, A0 and A7): Phi(z_{1-phi} - rho d') at every depth.  A reader of the A7
    provenance channel (dprime_provenance given, B1-prov): times Phi(z_{1-phi} - d'_prov)
    for a delegated patch (a direct one has clean provenance)."""
    tau = tau_of(phi)
    p = p_miss(patch_mean(True, via, rho, dprime, depth), tau)
    if dprime_provenance is not None:
        p *= p_miss(provenance_mean(via == "delegated", dprime_provenance), tau)
    return p


def checkpoint_lr(passed: bool, poisoned: bool) -> float:
    """O8: psi_c = phi_c, so the checkpoint's likelihood ratio is 1 under every hypothesis."""
    return 1.0


def checkpoint_loglik(passed: bool, poisoned: bool, solve_rate: float) -> float:
    """log Pr[checkpoint outcome | hypothesis]: depends on the solve rate only (O8)."""
    return math.log(solve_rate if passed else 1.0 - solve_rate)


def _check_depth(depth) -> None:
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
        raise ValueError(f"depth={depth!r} is not a positive integer")


def _check_via(has_marker: bool, via: str) -> None:
    if via not in VIAS:
        raise ValueError(f"via={via!r} is not one of {VIAS}")
    if bool(has_marker) != bool(via):
        raise ValueError(f"has_marker={has_marker!r} with via={via!r}: a marked patch has a "
                         "route ('direct' / 'delegated'), a clean one has none ('')")


# ---------------------------------------------------------------------------------------
# One audit's result
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Inspection:
    """One bought audit.  `items` and `marker` are EVALUATOR-ONLY (the runner's accounting:
    benign_inspected, quarantine outcomes); `observation()` is what the defender gets."""
    target: str
    depth: int
    scores: tuple
    written_at: tuple
    firing: tuple                          # per score: s > tau_det
    alarm_patch: bool                      # any score over tau_det (the patch / items)
    provenance: float | None = None        # A7 commit only
    alarm: bool = False                    # = alarm_patch: what every policy sees
    provenance_fired: bool = False         # A7 commit: provenance over tau_det (readers only)
    items: tuple = ()                      # evaluator-only: the inspected core.Items
    marker: bool | None = None             # evaluator-only: commit, the patch's marker

    @property
    def action(self) -> A.AuditAction:
        return A.AuditAction(self.target, self.depth)

    def observation(self, t: int, requested: A.AuditAction | None,
                    checkpoint: bool | None) -> A.Observation:
        """o_t for the policy: scores, alarm, written_at, checkpoint, provenance -- no
        item, no label."""
        return A.Observation(t=t, requested=requested, bought=self.action,
                             scores=self.scores, alarm=self.alarm,
                             written_at=self.written_at, checkpoint=checkpoint,
                             provenance=self.provenance)

    def commit_alarm(self, reads_provenance: bool) -> bool:
        """The alarm a system acts on (runner step 5 blocks the patch on it): the patch
        score's alarm, or -- for a system that reads the A7 provenance channel -- either
        score over tau_det."""
        return self.alarm or (bool(reads_provenance) and self.provenance_fired)


def reads_provenance(policy) -> bool:
    """Does `policy` read the A7 provenance channel in its alarm rule (B1-prov)?  Declared
    as a class attribute, like library.Member.reads_belief; absent = False."""
    return bool(getattr(policy, "reads_provenance", False))


# ---------------------------------------------------------------------------------------
# The world-side model
# ---------------------------------------------------------------------------------------

class ObservationModel:
    """The shared detector of one (world, cell): every system in the cell sees through
    this one object (C15).  Stateless apart from two world-side id sets the runner shares
    with the agent (build a new model after a resume, over the resumed sets):

        drift_ids    benign drift items (the agent's ground truth, D6)
        ingress_ids  items that entered through repository ingress (H8)
    """

    def __init__(self, world: C.WorldV3, cell: C.Cell, *, drift_ids: set | None = None,
                 ingress_ids: set | None = None):
        C.check_world_cell(world, cell)
        self.world, self.cell = world, cell
        self.detector = cell.detector()                    # exact (psi, phi) of SETTINGS
        self.dprime = self.detector.d_prime
        self.tau = self.detector.tau_det
        self.drift_ids = drift_ids if drift_ids is not None else set()
        self.ingress_ids = ingress_ids if ingress_ids is not None else set()
        #: O9: A7's provenance d' is the cell's detector d' (placeholder, measured in P3).
        self.dprime_provenance = self.dprime if world.provenance == "A7" else None
        self._det = DriftDetector(self.detector, self.drift_ids, match=DRIFT_MATCH,
                                  rho_patch=cell.rho, d1=self.dprime,
                                  drift_visible=DRIFT_VISIBLE[world.drift])

    # ---- the one threshold ---------------------------------------------------------
    def fires(self, score):
        """PURE threshold on a score: no parameter through which ground truth can enter."""
        return self.detector.fires(score)

    # ---- what a sweep can see --------------------------------------------------------
    def visible(self, target: str, store) -> list:
        """The live items the audit of `target` inspects.  H8: with ingress hidden, the
        insertion (memory) audit does not see ingress items."""
        if target not in SWEEP_TARGETS:
            raise ValueError(f"target={target!r} is not a sweep target {SWEEP_TARGETS}")
        live = store.live(C.CARRIER_OF_TARGET[target])
        if target == "memory" and not self.world.ingress_visible:
            live = [it for it in live if it.item_id not in self.ingress_ids]
        return live

    def sweep(self, t: int, target: str, depth: int, store, seed: int) -> Inspection:
        """Score every visible live item of the carrier at depth d (D16: one fresh draw per
        item per task, seeded on (seed, item, t))."""
        _check_depth(depth)
        items = tuple(self.visible(target, store))
        deep = self._det.at_depth(depth)
        scores = tuple(deep.score(it, t, seed) for it in items)
        firing = tuple(self.fires(s) for s in scores)
        return Inspection(target=target, depth=depth, scores=scores,
                          written_at=tuple(it.created_at for it in items), firing=firing,
                          alarm_patch=any(firing), alarm=any(firing), items=items)

    def commit(self, t: int, depth: int, *, has_marker: bool, via: str, task_id: str,
               seed: int) -> Inspection:
        """Review this task's patch (D20), plus (A7) the provenance of the contributing
        delegated carriers.  `alarm` is the patch score's only; the provenance score and
        its firing are returned beside it for the systems that read them."""
        _check_depth(depth)
        _check_via(has_marker, via)
        deep = self._det.at_depth(depth)
        s = deep.score_patch(bool(has_marker), task_id, seed, via=via or "direct")
        fired = self.fires(s)
        prov, prov_fired = None, False
        if self.dprime_provenance is not None:
            mu = provenance_mean(bool(has_marker) and via == "delegated", self.dprime_provenance)
            prov = random.Random(seed_of(seed, "v3-provenance", task_id)).gauss(mu, 1.0)
            prov_fired = bool(self.fires(prov))
        return Inspection(target="commit", depth=depth, scores=(s,), written_at=(t,),
                          firing=(fired,), alarm_patch=fired, provenance=prov, alarm=fired,
                          provenance_fired=prov_fired, marker=bool(has_marker))

    def audit(self, t: int, action: A.AuditAction, store, seed: int, *, has_marker: bool,
              via: str, task_id: str) -> Inspection:
        """Dispatch a bought action: the commit reads the patch, the others sweep."""
        if action.target == "commit":
            return self.commit(t, action.depth, has_marker=has_marker, via=via,
                               task_id=task_id, seed=seed)
        return self.sweep(t, action.target, action.depth, store, seed)

    # ---- the checkpoint and the empty observation ----------------------------------------
    def checkpoint(self, solved):
        """O8: the executable checkpoint passes iff the patch passes its tests."""
        return bool(solved)

    def nothing(self, t: int, requested: A.AuditAction | None,
                checkpoint: bool | None) -> A.Observation:
        """o_t when nothing was bought: the checkpoint only."""
        return A.Observation(t=t, requested=requested, bought=None, checkpoint=checkpoint)
