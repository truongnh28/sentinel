"""v3/belief_pf.py -- Algorithm 1 line 7: the particle filter over (c, iota, sigma) (plan T9).

Draft S7 "Belief update": "A particle filter (2048 particles) over (c, ι, σ) with the
benign-drift process as a competing transition; β is estimated online from clean
workflows."  Draft S5.1: b_t is "updated from alarm observations and checkpoint outcomes
with the benign-drift process as a competing explanation", and "an alarm at task t
raises the posterior on insertions at t' < t with triggers at t'' > t".

THE HIDDEN STATE OF ONE PARTICLE (numpy arrays of length N = config.PF_PARTICLES = 2048)
    attacked   is there an attack in this episode at all
    kmask      the seeded carrier(s) as a bit mask (world.n_seeded bits, core.CARRIERS
               order: memory = 1, skill = 2, queue = 4, branch = 8)
    iota       the insertion task (H = "never": not attacked)
    sigma      the trigger task, iota + Delta (H = "never")
    c          c_t in {0,1}^4 as a bit mask, the draft's carrier state
    harmed     a marked patch entered the branch at sigma (C11: harm locked at sigma)
The draft's (c, iota, sigma) is (c, iota, sigma); `attacked`, `kmask` and `harmed` are the
bookkeeping a rollout needs (HiddenState.k, harm_locked).  `Particle` is api.Hypothesis
plus these two.

THE TRANSITION (the declared kernel of v3/agent.py, `kernel_of(world)`, per task t in the
runner's order: inject at iota -> agent -> audit -> observe)
    inject    t == iota: c |= kmask.
    agent     poison is live (c != 0) -> every task retrieves it (O2, agent step 1), so
              a skill induced now inherits it (skill_induction), a queued call left now
              inherits it (queue * queue_inherits), and at t == sigma the patch carries
              the marker with probability `adoption` (the payload activates at sigma
              only: no task in [iota, sigma) meets the predicate, O2; a re-activation
              after sigma is not modelled -- declared, L1).  The marked patch enters the
              branch (c |= branch, harmed).  Its route is "delegated" iff a carrier the
              cell delegates (K_d, O1) holds poison when the task retrieves (agent step 5).
    drift     BENIGN DRIFT IS THE COMPETING TRANSITION: carrier k gets a benign drift
              write with probability beta_k per task (agent step 6), with the payload's
              score statistics (observe.DRIFT_MATCH).  It never changes c, so it is not
              sampled: it is marginalised per inspected item in the likelihood
              (Rao-Blackwellised), which is exact under the item model below.

THE LIKELIHOOD (observe.py's pure functions: sweep_dprime, patch_mean, provenance_mean,
log_lr, drift_visible, checkpoint_lr -- nothing re-derived)
    checkpoint  O8: likelihood ratio 1 under every hypothesis (observe.checkpoint_lr).
    commit      this task's patch: log_lr(s, patch_mean(marked, route, rho, d', depth)),
                so a delegated marked patch moves the belief with strength rho*d' and not
                at all at rho = 0 in A0; A7 adds log_lr(provenance, d'_prov) (C1, O9).
    sweep of k  every inspected item i (score s_i, written_at w_i) is, a priori, one of
                    poison  (only under c[k] = 1, and only if w_i can hold it -- below)
                    drift   share q_k = beta_k / (r_k + beta_k), r_k the agent's own write
                            rate into k (memory 1, skill skill_induction, queue queue)
                    clean
                with mean d'_eff = d' sqrt(depth) (poison), DRIFT_MATCH * d'_eff (drift
                while observe.drift_visible), 0 otherwise.  Which items can hold poison:
                    memory (and any carrier the agent never writes poison into): one root,
                        written at iota, one of the items with w_i == iota;
                    skill, queue (the agent's copies): EVERY item written at w_i >= iota
                        while poison is live is a poisoned copy (agent steps 1, 4), so
                        under c[k] = 1 each such item is poison unless it is a drift write,
                        and under c[k] = 0 with poison live elsewhere each such item MUST
                        be a drift write.
                c[k] = 1 with no inspected item that could hold the poison has likelihood
                MISS_FLOOR (not 0: model error must not kill every particle).  H8: with
                ingress hidden, the insertion audit sees neither drift (ingress writes) nor
                a root the attacker wrote through ingress (INGRESS_ROOT_SHARE).
    The filter reads scores and written_at; it does not read item counts (declared).

RESAMPLING.  Systematic, when ESS < ESS_RESAMPLE_FRACTION * N, followed by a MOVE that is
an exact Gibbs step on the part of each particle no past observation depends on:
    (a) not yet injected (not attacked, or iota > t): every past likelihood is the c = 0
        one, so (attacked, kmask, iota, sigma) is redrawn from the prior restricted to
        this class;
    (b) injected, not yet triggered (iota <= t < sigma): nothing before sigma depends on
        sigma (C12), so Delta is redrawn from its prior given iota and sigma > t.
This rejuvenates exactly the coordinates line 5 and line 8 look ahead with (R11).  It is
followed by an INDEPENDENCE MOVE on whole paths: each particle's path is proposed afresh
from the prior and the kernel, replayed through the recorded observations (ObsRecord) and
quarantines, and accepted with probability min(1, L(new) / L(old)).  That move also runs
after every task whose audit raised an alarm (MOVE_ON_ALARM): an alarm can put the
posterior where an earlier resampling left no particle, and the ESS cannot see that.
Measured on the small cases: without it one case in ~500 steps had TV 0.6 to the exact
posterior; it costs ~4x per alarm task (python -m v3.belief_pf prints both timings).

PROP. 6.1 (T11).  `uninformable_share(targets)` is f, the prior share of attack hypotheses
no buyable observation of `targets` can tell from the null; `prior_p_attack()` is p0.

THE PRIOR (L1, declared).  Pr[attacked] = PRIOR_P_ATTACK; the seeded carrier set uniform
over the world.n_seeded-subsets of CARRIERS; Delta uniform over the grid values >= Delta-hat
that fit the workflow (Delta-hat is line 1's LOW quantile, C12 / O3, so it is read as a lower
bound; DELTA_PRIOR = "point" puts all the mass on Delta-hat), iota uniform on [0, H-1-Delta].

BETA ONLINE (O11).  beta starts from the dev clean runs (BETA_BASE_FILE: the method-of-
moments estimate of tools/select_mixture.estimate_betas on dev clean runs, the same drift
world as v3's agent) and is updated from the same-cell post-mortems in ctx.postmortems:
every audit OUTSIDE (k, [iota, sigma)) is a clean exposure and its alarm counts as drift
or a false positive (`estimate_beta`).  The audits themselves must travel in the
post-mortem (`pm.audits`); api.PostMortem has only `alarms` -- see `estimate_beta`.

Numpy only here (plan S2: numpy for the PF, rollout and table).  Seeds come from
core.seed_of; no module-level randomness.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np

from core import CARRIERS, seed_of

from v3 import api as A
from v3 import config as C
from v3 import observe as O
from v3.agent import kernel_of

# ---------------------------------------------------------------------------------------
# Declared values (L1)
# ---------------------------------------------------------------------------------------

N_PARTICLES = C.PF_PARTICLES               # S7: 2048
#: Resample when the effective sample size falls below this fraction of N.
ESS_RESAMPLE_FRACTION = 0.5
#: Also run the independence move after a task whose audit raised an alarm: an alarm is
#: the observation that can put mass where no particle is left, and the ESS cannot see it
#: (every surviving particle explains the alarm equally badly).
MOVE_ON_ALARM = True
#: Independence-move sweeps per move.
MOVE_STEPS = 1
#: b_0: probability that the episode is attacked at all (v2 belief.WindowBelief's 0.5).
PRIOR_P_ATTACK = 0.5
#: How line 1's Delta-hat becomes the prior on sigma - iota.
DELTA_PRIORS = ("at-least", "point")
DELTA_PRIOR = "at-least"
#: Likelihood of c[k] = 1 when no inspected item of k could hold the poison.
MISS_FLOOR = 1e-3
#: H8, ingress hidden: prior share of "the memory root came through ingress (invisible)".
INGRESS_ROOT_SHARE = 0.5
#: O11: weight of the dev base beta, in clean single-item depth-1 audits.
BETA_PRIOR_AUDITS = 20.0
#: O11: the dev clean-run beta (method of moments, D6 of v2; reference/v2_tuned.json).
BETA_BASE_FILE = Path(__file__).resolve().parents[1] / "reference" / "v2_tuned.json"
#: Declared BEFORE the comparison was run (plan T9): the particle filter's posterior over
#: (attacked, c, iota, sigma) is within this mean total-variation distance of the exact
#: enumerator (v3/belief_exact.py) on the small cases of tests/v3/test_alg1_line7.py, and
#: its read-outs (p_poisoned, p_attack, carrier_mass) within PF_EXACT_MARGINAL_MAX on average.
PF_EXACT_TV_MAX = 0.12
PF_EXACT_MARGINAL_MAX = 0.03

BIT = {k: 1 << j for j, k in enumerate(CARRIERS)}
MEMORY, SKILL, QUEUE, BRANCH = (BIT[k] for k in ("memory", "skill", "queue", "branch"))
_FLOOR = 1e-300


def _log(x):
    return np.log(np.maximum(x, _FLOOR))


def mask_of(carriers) -> int:
    m = 0
    for k in carriers:
        m |= BIT[k]
    return m


def carriers_of(mask: int) -> tuple:
    return tuple(k for k in CARRIERS if int(mask) & BIT[k])


def bits_of(mask: int) -> tuple:
    return tuple(int(bool(int(mask) & BIT[k])) for k in CARRIERS)


@dataclass(frozen=True)
class Particle(A.Hypothesis):
    """api.Hypothesis plus what a rollout needs to set HiddenState: the seeded carriers
    and whether the harm is already locked (C11)."""
    k: tuple = ()
    harmed: bool = False


# ---------------------------------------------------------------------------------------
# Beta: dev base, online update from same-cell post-mortems (O11)
# ---------------------------------------------------------------------------------------

def beta_base(path: Path = BETA_BASE_FILE) -> dict:
    """The dev clean-run beta per carrier (O11 'beta nen lay tu luot sach tren dev')."""
    with open(path, encoding="utf-8") as f:
        betas = json.load(f)["betas"]
    return {k: float(betas[k]) for k in CARRIERS}


@dataclass(frozen=True)
class BetaEstimate:
    betas: dict                            # carrier -> beta used by the belief
    base: dict
    audits: dict                           # carrier -> clean exposures used
    alarms: dict                           # carrier -> alarms among them
    notes: tuple = ()                      # N3: post-mortems skipped, and why


def estimate_beta(postmortems, cell: C.Cell, *, base: dict | None = None,
                  prior_audits: float = BETA_PRIOR_AUDITS) -> BetaEstimate:
    """O11: beta_k from the dev base plus the same-cell post-mortems.

    A clean exposure is an audit of a sweep target whose carrier is NOT in (k, [iota,
    sigma)) of that workflow ("bao dong nam ngoai (k, [iota, sigma)) tinh la drift").
    With n items inspected at depth d and a transient drift write among them with
    probability beta, Pr[alarm] = 1 - (1-phi)^n + beta (1-phi)^(n-1) (psi_m - phi),
    psi_m = Pr[fire | DRIFT_MATCH d' sqrt(d)]: linear in beta, so the moment estimate
    with `prior_audits` pseudo-audits at the base is
        beta_k = (n0 w1 beta_base + sum(alarm - e0)) / (n0 w1 + sum w),
    w = (1-phi)^(n-1) (psi_m - phi), e0 = 1 - (1-phi)^n, w1 = w at n = 1, d = 1.

    The audits come from `pm.audits`: ((t, target, depth, n_inspected), ...).
    api.PostMortem carries only `alarms`, so a post-mortem without `audits` is skipped
    with a note and beta stays at the base (interface need, reported with T9)."""
    base = beta_base() if base is None else dict(base)
    det = cell.detector()
    tau = det.tau_det
    phi = O.p_alarm(0.0, tau)
    cid = C.cell_id(cell)
    num = {k: 0.0 for k in CARRIERS}
    den = {k: 0.0 for k in CARRIERS}
    n_aud = {k: 0 for k in CARRIERS}
    n_al = {k: 0 for k in CARRIERS}
    notes = []
    for pm in postmortems:
        if getattr(pm, "cell_id", cid) != cid:
            notes.append(f"{pm.wf_id}: post-mortem of cell {pm.cell_id}, not {cid}")
            continue
        audits = getattr(pm, "audits", None)
        if audits is None:
            notes.append(f"{pm.wf_id}: post-mortem carries no audits (PostMortem.audits); "
                         "its alarms cannot be turned into a rate")
            continue
        alarms = {(int(t), str(g)) for t, g in pm.alarms}
        for t, target, depth, n in audits:
            if target not in O.SWEEP_TARGETS or n < 1:
                continue
            k = C.CARRIER_OF_TARGET[target]
            if (pm.iota is not None and k in tuple(pm.k)
                    and pm.iota <= t < (pm.sigma if pm.sigma is not None else pm.H)):
                continue                                  # inside (k, [iota, sigma))
            psi_m = O.p_alarm(O.DRIFT_MATCH * O.sweep_dprime(det.d_prime, int(depth)), tau)
            fired = (int(t), str(target)) in alarms
            num[k] += float(fired) - (1.0 - (1.0 - phi) ** n)
            den[k] += (1.0 - phi) ** (n - 1) * (psi_m - phi)
            n_aud[k] += 1
            n_al[k] += int(fired)
    psi_1 = O.p_alarm(O.DRIFT_MATCH * det.d_prime, tau)
    w1 = psi_1 - phi
    out = {}
    for k in CARRIERS:
        b0 = base.get(k, 0.0)
        d = prior_audits * w1 + den[k]
        out[k] = b0 if d <= 0 else min(1.0, max(0.0, (prior_audits * w1 * b0 + num[k]) / d))
    return BetaEstimate(betas=out, base=base, audits=n_aud, alarms=n_al, notes=tuple(notes))


# ---------------------------------------------------------------------------------------
# The model shared by the particle filter and the exact enumerator
# ---------------------------------------------------------------------------------------

def delta_support(H: int, delta_hat, rule: str = DELTA_PRIOR) -> tuple:
    """(support of sigma - iota, notes).  Delta-hat off the grid is rounded down (O3)."""
    if rule not in DELTA_PRIORS:
        raise ValueError(f"delta prior {rule!r} is not one of {DELTA_PRIORS}")
    notes = []
    dh = C.DHAT_PRIOR if delta_hat is None else delta_hat
    if dh not in C.DELTAS:
        below = [d for d in C.DELTAS if d <= dh]
        new = max(below) if below else min(C.DELTAS)
        notes.append(f"Delta-hat {dh} is off the grid: rounded down to {new} (O3)")
        dh = new
    fits = [d for d in C.DELTAS if d <= H - 1]
    if not fits:
        raise ValueError(f"H = {H}: no Delta on the grid {C.DELTAS} fits")
    sup = [d for d in fits if d >= dh] if rule == "at-least" else [d for d in fits if d == dh]
    if not sup:
        sup = [max(fits)]
        notes.append(f"Delta-hat {dh} does not fit H = {H}: prior on the largest grid "
                     f"Delta that fits, {sup[0]} (N3)")
    return tuple(sup), dh, tuple(notes)


@dataclass(frozen=True)
class ObsRecord:
    """o_t compiled by BeliefModel.record.  kind 'commit': a / b = the log likelihood
    ratio of a delegated / direct marked patch (A7 provenance folded into a); kind
    'sweep': a / b = the tables over iota of BeliefModel.sweep_tables, bit = the swept
    carrier; chk = the checkpoint's (poison live, clean) log likelihoods when they differ."""
    t: int
    kind: str                              # "none" | "commit" | "sweep"
    chk: tuple | None = None
    alarm: bool = False
    bit: int = 0
    a: object = None
    b: object = None


@dataclass
class BeliefModel:
    """Prior, transition and likelihood of line 7 for one episode (module docstring)."""
    H: int
    rho: float
    dprime: float                          # the cell's depth-1 d' (exact operating point)
    tau: float
    drift: str
    ingress_visible: bool
    dprime_provenance: float | None        # A7 only (O9)
    delegated_mask: int
    kernel: dict
    betas: dict
    deltas: tuple                          # support of sigma - iota
    delta_hat: int
    masks: tuple                           # seeded carrier sets as bit masks
    harm: str
    p_attack: float = PRIOR_P_ATTACK
    notes: tuple = ()

    @classmethod
    def for_context(cls, ctx: A.EpisodeContext, delta_hat=None, *, betas: dict | None = None,
                    delta_prior: str = DELTA_PRIOR, p_attack: float = PRIOR_P_ATTACK,
                    beta_estimate: BetaEstimate | None = None) -> "BeliefModel":
        world, cell = ctx.world, ctx.cell
        if world.audit_reading != "carrier":
            raise ValueError("belief_pf models the carrier world (C2 primary); the stage "
                             "world's targets are stages (T20)")
        det = cell.detector()
        kern = kernel_of(world)
        for key in ("skill_inherits", "queue_inherits"):
            if kern[key] not in (0.0, 1.0):
                raise ValueError(f"kernel {key} = {kern[key]}: the item model needs 0 or 1")
        sup, dh, notes = delta_support(ctx.H, delta_hat, delta_prior)
        if betas is None:
            est = beta_estimate or estimate_beta(ctx.postmortems, cell)
            betas, notes = est.betas, notes + est.notes
        return cls(H=int(ctx.H), rho=float(cell.rho), dprime=det.d_prime, tau=det.tau_det,
                   drift=world.drift, ingress_visible=world.ingress_visible,
                   dprime_provenance=det.d_prime if world.provenance == "A7" else None,
                   delegated_mask=mask_of(ctx.delegated), kernel=kern,
                   betas={k: float(betas.get(k, 0.0)) for k in CARRIERS}, deltas=sup,
                   delta_hat=dh,
                   masks=tuple(mask_of(ks) for ks in combinations(CARRIERS, world.n_seeded)),
                   harm=world.harm, p_attack=float(p_attack), notes=notes)

    # ---- rates -----------------------------------------------------------------------
    @property
    def p_skill(self) -> float:
        return self.kernel["skill_induction"] * self.kernel["skill_inherits"]

    @property
    def p_queue(self) -> float:
        return self.kernel["queue"] * self.kernel["queue_inherits"]

    @property
    def p_adopt(self) -> float:
        return self.kernel["adoption"]

    def write_rate(self, k: str) -> float:
        """r_k: the agent's own writes into k per task (a note, a skill, a queued call,
        a patch)."""
        return {"memory": 1.0, "skill": self.kernel["skill_induction"],
                "queue": self.kernel["queue"], "branch": 1.0}[k]

    def drift_share(self, k: str) -> float:
        """q_k: Pr[an item written into k is a drift write]."""
        if k == "memory" and not self.ingress_visible:
            return 0.0                     # drift enters through ingress (agent step 6)
        b = self.betas.get(k, 0.0)
        return b / (self.write_rate(k) + b) if b > 0 else 0.0

    def derived(self, k: str) -> bool:
        """Does the agent copy poison into k (every item written while poison is live)?"""
        return (k == "skill" and self.kernel["skill_inherits"] == 1.0) or \
               (k == "queue" and self.kernel["queue_inherits"] == 1.0)

    # ---- prior -----------------------------------------------------------------------
    def prior_table(self) -> tuple:
        """(arrays, p): every prior hypothesis once, with its probability.  Row 0 is
        'not attacked'."""
        H = self.H
        att, km, io, sg, p = [False], [0], [H], [H], [1.0 - self.p_attack]
        pd = 1.0 / len(self.deltas)
        pk = 1.0 / len(self.masks)
        for m in self.masks:
            for d in self.deltas:
                for i in range(H - d):
                    att.append(True); km.append(m); io.append(i); sg.append(i + d)
                    p.append(self.p_attack * pk * pd / (H - d))
        arrays = {"attacked": np.array(att, bool), "kmask": np.array(km, np.uint8),
                  "iota": np.array(io, np.int64), "sigma": np.array(sg, np.int64)}
        return arrays, np.array(p, float)

    def informable(self, targets=None) -> np.ndarray:
        """Per prior_table row: can SOME observation of `targets` (default config.TARGETS),
        at some task, have a likelihood different from the null's under this attack
        hypothesis?  Read off the model (no sampling):
            memory sweep  the root is visible iff memory is seeded (with ingress hidden
                          the root is still seen with share 1 - INGRESS_ROOT_SHARE);
            skill / queue a seeded root, or a copy the agent can write (p_skill / p_queue
                          > 0: poison is live from iota on, so a copy can appear);
            commit        the marked patch at sigma moves the likelihood iff its mean is
                          non-zero: a direct route is possible (no seeded carrier is
                          delegated -- the copies are, but they may not have happened), or
                          rho > 0, or A7's provenance channel.
        Row 0 ('not attacked') is False."""
        tg = C.TARGETS if targets is None else tuple(targets)
        for g in tg:
            if g not in C.TARGETS:
                raise ValueError(f"target {g!r} is not one of {C.TARGETS}")
        arr, _ = self._prior_cache()
        km = arr["kmask"].astype(np.int64)
        out = np.zeros(len(km), bool)
        if "memory" in tg:
            out |= (km & MEMORY) != 0
        if "skill" in tg:
            out |= ((km & SKILL) != 0) | (self.p_skill > 0)
        if "queue" in tg:
            out |= ((km & QUEUE) != 0) | (self.p_queue > 0)
        if "commit" in tg and self.p_adopt > 0:
            if self.rho > 0 or self.dprime_provenance is not None:
                out |= np.ones(len(km), bool)
            else:
                out |= (km & self.delegated_mask) == 0
        return out & arr["attacked"]

    def uninformable_share(self, targets=None) -> float:
        """f of Prop. 6.1 (library.band_prop61): the PRIOR share, within the attack mass,
        of the attack hypotheses whose likelihood equals the null's under every
        observation of `targets` the policy can buy (`informable`)."""
        arr, p = self._prior_cache()
        att = arr["attacked"]
        tot = p[att].sum()
        return float(p[att & ~self.informable(targets)].sum() / tot) if tot > 0 else 0.0

    # ---- transition --------------------------------------------------------------------
    def advance(self, t: int, st: dict, induce, enqueue, adopt) -> tuple:
        """Task t of the kernel, in place on `st`; `induce`, `enqueue`, `adopt` are the
        agent's three events (bool arrays).  Returns (marked, delegated) of this task's
        patch."""
        c = st["c"]
        c = np.where(st["iota"] == t, c | st["kmask"], c)
        live = c != 0
        deleg = (c & self.delegated_mask) != 0
        marked = live & (st["sigma"] == t) & adopt
        add = (np.where(live & induce, SKILL, 0) | np.where(live & enqueue, QUEUE, 0)
               | np.where(marked, BRANCH, 0))
        st["c"] = (c | add).astype(np.uint8)
        st["harmed"] = st["harmed"] | marked
        return marked, deleg

    # ---- likelihood --------------------------------------------------------------------
    def record(self, t: int, obs: A.Observation) -> "ObsRecord":
        """o_t compiled once into what the likelihood of ANY particle needs: two numbers
        (commit) or two tables over iota (sweep).  `apply` evaluates it on particles; the
        filter keeps the records, so replaying a history costs no per-item work."""
        chk = None
        if obs.checkpoint is not None:                       # O8: ratio 1
            lp = math.log(O.checkpoint_lr(obs.checkpoint, True))
            lc = math.log(O.checkpoint_lr(obs.checkpoint, False))
            if lp != lc:
                chk = (lp, lc)
        a = obs.bought
        if a is None:
            return ObsRecord(t, "none", chk)
        alarm = any(float(s) > self.tau for s in obs.scores)
        if a.target == "commit":
            if len(obs.scores) != 1:
                raise ValueError(f"a commit audit has one score, got {len(obs.scores)}")
            s = float(obs.scores[0])
            l_del = O.log_lr(s, O.patch_mean(True, "delegated", self.rho, self.dprime, a.depth))
            l_dir = O.log_lr(s, O.patch_mean(True, "direct", self.rho, self.dprime, a.depth))
            if obs.provenance is not None and self.dprime_provenance is not None:
                l_del += O.log_lr(float(obs.provenance),
                                  O.provenance_mean(True, self.dprime_provenance))
                alarm = alarm or float(obs.provenance) > self.tau
            return ObsRecord(t, "commit", chk, alarm=alarm, a=l_del, b=l_dir)
        if a.target not in O.SWEEP_TARGETS:
            raise ValueError(f"target {a.target!r} is not one of {C.TARGETS}")
        k = C.CARRIER_OF_TARGET[a.target]
        A_, B_ = self.sweep_tables(t, obs, k, a.depth)
        return ObsRecord(t, "sweep", chk, alarm=alarm, bit=BIT[k], a=A_, b=B_)

    def apply(self, rec: "ObsRecord", st: dict, marked, deleg) -> np.ndarray:
        """log Pr[o_t | particle], up to a constant shared by every particle."""
        c = st["c"]
        if rec.kind == "commit":
            ll = np.where(marked, np.where(deleg, rec.a, rec.b), 0.0)
        elif rec.kind == "sweep":
            io = np.minimum(st["iota"], self.H)
            ll = np.where((c & rec.bit) != 0, rec.a[io], np.where(c != 0, rec.b[io], 0.0))
        else:
            ll = np.zeros(len(c))
        if rec.chk is not None:
            ll = ll + np.where(c != 0, rec.chk[0], rec.chk[1])
        return ll

    def loglik(self, t: int, obs: A.Observation, st: dict, marked, deleg) -> np.ndarray:
        """log Pr[o_t | particle], up to a constant shared by every particle."""
        return self.apply(self.record(t, obs), st, marked, deleg)

    def sweep_tables(self, t: int, obs, k: str, depth: int) -> tuple:
        """(A, B) indexed by iota in [0, H]: the log likelihood ratio, against 'c = 0',
        of the sweep of carrier k under c[k] = 1 (A) and under c[k] = 0 with poison
        live elsewhere (B)."""
        H = self.H
        s = np.asarray(obs.scores, float)
        w = np.asarray(obs.written_at, np.int64)
        if len(s) != len(w):
            raise ValueError("one written_at per score")
        deff = O.sweep_dprime(self.dprime, depth)
        mdrift = O.DRIFT_MATCH * deff
        lp = np.array([O.log_lr(x, deff) for x in s])
        ld = np.array([O.log_lr(x, mdrift) if O.drift_visible(int(wi), t, self.drift) else 0.0
                       for x, wi in zip(s, w)])
        q = self.drift_share(k)
        lq = math.log(q) if q > 0 else math.log(_FLOOR)
        l1q = math.log1p(-q)
        l0 = np.logaddexp(l1q, lq + ld)                      # clean or drift
        iotas = np.arange(H + 1)
        if self.derived(k):
            E = w[None, :] >= iotas[:, None]
            l1 = np.logaddexp(l1q + lp, lq + ld)             # poison copy or drift
            A_ = np.where(E, l1 - l0, 0.0).sum(1) + np.where(E.any(1), 0.0, math.log(MISS_FLOOR))
            B_ = np.where(E, lq + ld - l0, 0.0).sum(1)       # every copy must be drift
        else:
            E = w[None, :] == iotas[:, None]
            cnt = E.sum(1)
            num = np.where(E, np.exp(np.minimum(lp - l0, 700.0)), 0.0).sum(1)
            one_of = np.where(cnt > 0, num / np.maximum(cnt, 1), MISS_FLOOR)
            if k == "memory" and not self.ingress_visible:
                one_of = INGRESS_ROOT_SHARE + (1.0 - INGRESS_ROOT_SHARE) * one_of
            A_ = _log(one_of)
            B_ = np.zeros(H + 1)
        return A_, B_

    # ---- the Gibbs move (resample-move) -------------------------------------------------
    def refresh(self, t: int, st: dict, rng: np.random.Generator) -> None:
        """Redraw, in place, what no observation up to t depends on (module docstring)."""
        H = self.H
        arr, p = self._prior_cache()
        # (a) not yet injected
        a = ~st["attacked"] | (st["iota"] > t)
        na = int(a.sum())
        if na:
            ok = ~arr["attacked"] | (arr["iota"] > t)
            pr = np.where(ok, p, 0.0)
            pr = pr / pr.sum()
            idx = rng.choice(len(pr), size=na, p=pr)
            for key in ("attacked", "kmask", "iota", "sigma"):
                st[key][a] = arr[key][idx]
            st["c"][a] = 0
            st["harmed"][a] = False
        # (b) injected, not yet triggered
        b = st["attacked"] & (st["iota"] <= t) & (st["sigma"] > t)
        nb = int(b.sum())
        if nb:
            d = np.asarray(self.deltas, np.int64)
            io = st["iota"][b][:, None]
            pw = np.where((io + d[None, :] > t) & (io + d[None, :] <= H - 1),
                          1.0 / (H - d[None, :]), 0.0)
            cum = np.cumsum(pw, 1)
            u = rng.random(nb) * cum[:, -1]
            j = (cum < u[:, None]).sum(1)
            st["sigma"][b] = st["iota"][b] + d[np.minimum(j, len(d) - 1)]

    def replay(self, t: int, history: list, quarantines: dict, rng: np.random.Generator,
               n: int) -> tuple:
        """n fresh paths drawn from the prior and the kernel through tasks 0..t, under the
        same observations (`history[tau]`, an ObsRecord or None) and the same quarantines
        (`quarantines[tau]`: carriers removed after task tau), with the log likelihood of
        each path: the proposal of the independence move (module docstring)."""
        arr, p = self._prior_cache()
        idx = rng.choice(len(p), size=n, p=p)
        st = {k: v[idx].copy() for k, v in arr.items()}
        st["c"] = np.zeros(n, np.uint8)
        st["harmed"] = np.zeros(n, bool)
        ll = np.zeros(n)
        ps, pq, pa = self.p_skill, self.p_queue, self.p_adopt
        for tau in range(t + 1):
            u = rng.random((3, n))
            marked, deleg = self.advance(tau, st, u[0] < ps, u[1] < pq, u[2] < pa)
            rec = history[tau]
            if rec is not None:
                ll += self.apply(rec, st, marked, deleg)
            for k in quarantines.get(tau, ()):
                st["c"] = (st["c"] & ~np.uint8(BIT[k])).astype(np.uint8)
        return st, ll

    def _prior_cache(self):
        if not hasattr(self, "_prior"):
            self._prior = self.prior_table()
        return self._prior


# ---------------------------------------------------------------------------------------
# Read-outs shared by the particle filter and the exact enumerator
# ---------------------------------------------------------------------------------------

class _WeightedBelief:
    """BeliefAPI read-outs over weighted hypotheses `self.st` / `self.weights()`."""
    model: BeliefModel
    st: dict
    t_last: int = -1

    def weights(self) -> np.ndarray:
        raise NotImplementedError

    # ---- BeliefAPI -----------------------------------------------------------------
    def p_poisoned(self) -> float:
        return float(self.weights()[self.st["c"] != 0].sum())

    def p_attack(self) -> float:
        return float(self.weights()[self.st["attacked"]].sum())

    def carrier_mass(self) -> dict:
        w, c = self.weights(), self.st["c"]
        return {k: float(w[(c & BIT[k]) != 0].sum()) for k in CARRIERS}

    def expected_harm(self) -> float:
        """Pr[the poison reaches harm by the horizon | b_t], with no further quarantine:
        harm already locked at sigma (C11 locked; c[branch] = 1 in the reversible world),
        or a trigger still ahead with poison live or not yet written, times adoption."""
        st, t = self.st, self.t_last
        if self.model.harm == "locked":
            done = st["harmed"]
        else:
            done = (st["c"] & BRANCH) != 0
        ahead = st["attacked"] & (st["sigma"] > t) & ((st["c"] != 0) | (st["iota"] > t))
        p = np.where(done, 1.0, np.where(ahead, self.model.p_adopt, 0.0))
        return float((self.weights() * p).sum())

    def bin_features(self) -> A.BinFeatures:
        """O16: Pr[attacked], the carrier with the highest Pr[c[k] = 1] (ties: CARRIERS
        order), and the mass on 'some delegated carrier holds poison'."""
        cm = self.carrier_mass()
        top = max(CARRIERS, key=lambda k: (cm[k], -CARRIERS.index(k)))
        w, c = self.weights(), self.st["c"]
        dm = float(w[(c & self.model.delegated_mask) != 0].sum())
        return A.BinFeatures(p_attack=self.p_attack(), top_carrier=top, delegated_mass=dm)

    def sample(self, n: int, seed: int) -> list:
        rng = np.random.default_rng(seed_of(seed, "v3-belief-sample"))
        w = self.weights()
        idx = rng.choice(len(w), size=n, p=w / w.sum())
        return [self.hypothesis(i) for i in idx]

    # ---- extra read-outs (tests, T11, T12, T14) --------------------------------------
    def prior_p_attack(self) -> float:
        """p0 of Prop. 6.1: Pr[attacked] under b_0."""
        return self.model.p_attack

    def uninformable_share(self, targets=None) -> float:
        """f of Prop. 6.1 for library.band_prop61(p0, f): read-only, from the model's
        prior (BeliefModel.uninformable_share); `targets` = the audit targets the policy
        can buy (default every config.TARGETS)."""
        return self.model.uninformable_share(targets)

    def hypothesis(self, i: int) -> Particle:
        st = self.st
        att = bool(st["attacked"][i])
        return Particle(attacked=att, c=bits_of(st["c"][i]),
                        iota=int(st["iota"][i]) if att else None,
                        sigma=int(st["sigma"][i]) if att else None,
                        k=carriers_of(st["kmask"][i]) if att else (),
                        harmed=bool(st["harmed"][i]))

    def mass(self, pred) -> float:
        """Posterior mass of pred(st) -> bool array over the hypotheses."""
        return float(self.weights()[np.asarray(pred(self.st), bool)].sum())

    def distribution(self) -> dict:
        """(attacked, c, iota, sigma) -> posterior probability (api.Hypothesis coordinates)."""
        st, w = self.st, self.weights()
        H = self.model.H
        key = ((st["attacked"].astype(np.int64) * 16 + st["c"]) * (H + 1)
               + st["iota"]) * (H + 1) + st["sigma"]
        u, inv = np.unique(key, return_inverse=True)
        tot = np.bincount(inv, weights=w)
        first = np.zeros(len(u), np.int64)
        first[inv[::-1]] = np.arange(len(inv))[::-1]
        out = {}
        for j, i in enumerate(first):
            att = bool(st["attacked"][i])
            out[(att, bits_of(st["c"][i]), int(st["iota"][i]) if att else None,
                 int(st["sigma"][i]) if att else None)] = float(tot[j])
        return out


def total_variation(p: dict, q: dict) -> float:
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in set(p) | set(q))


# ---------------------------------------------------------------------------------------
# The particle filter
# ---------------------------------------------------------------------------------------

class ParticleBelief(_WeightedBelief):
    """Line 7: b_{t+1} <- Update(b_t, a_t, o_t, beta), N particles (api.BeliefAPI)."""

    def __init__(self, model: BeliefModel, *, n: int = N_PARTICLES, seed: int = 0):
        self.model = model
        self.n = int(n)
        self.rng = np.random.default_rng(seed)
        arr, p = model.prior_table()
        idx = self.rng.choice(len(p), size=self.n, p=p)
        self.st = {k: v[idx].copy() for k, v in arr.items()}
        self.st["c"] = np.zeros(self.n, np.uint8)
        self.st["harmed"] = np.zeros(self.n, bool)
        self.logw = np.zeros(self.n)
        self.cumll = np.zeros(self.n)      # log likelihood of each particle's whole path
        self._w = None
        self.t_last = -1
        self.history = []                  # ObsRecord (or None) per task, for the move
        self.quarantines = {}              # task -> carriers removed after it
        self.n_resampled = 0
        self.n_moved = 0                   # replay moves run
        self.n_accepted = 0                # particles those moves replaced
        self.last = None                   # (st, marked, delegated, weights) of the last task

    # ---- weights -------------------------------------------------------------------
    def weights(self) -> np.ndarray:
        if self._w is None:
            lw = self.logw - self.logw.max()
            w = np.exp(lw)
            self._w = w / w.sum()
        return self._w

    def ess(self) -> float:
        w = self.weights()
        return float(1.0 / np.dot(w, w))

    # ---- line 7 --------------------------------------------------------------------
    def update(self, t: int, obs: A.Observation | None) -> None:
        if t <= self.t_last:
            raise ValueError(f"update(t={t}) after t={self.t_last}: line 7 runs once per task")
        while self.t_last < t - 1:                           # tasks with no observation
            self._step(self.t_last + 1, None)
        self._step(t, obs)

    def _step(self, t: int, obs) -> None:
        m, st = self.model, self.st
        u = self.rng.random((3, self.n))
        marked, deleg = m.advance(t, st, u[0] < m.p_skill, u[1] < m.p_queue, u[2] < m.p_adopt)
        rec = None if obs is None else m.record(t, obs)
        self.history.append(rec)
        if rec is not None and (rec.kind != "none" or rec.chk is not None):
            ll = m.apply(rec, st, marked, deleg)
            self.cumll += ll
            self.logw = self.logw + ll
            self.logw -= self.logw.max()
        self._w = None
        self.t_last = t
        self.last = (dict(st), marked, deleg, self.weights())
        if self.ess() < ESS_RESAMPLE_FRACTION * self.n:
            self._resample(t)
            self._move(t)
        elif rec is not None and rec.alarm and MOVE_ON_ALARM:
            self._move(t)

    def _resample(self, t: int) -> None:
        """Systematic resampling (plan T9)."""
        w = self.weights()
        pos = (self.rng.random() + np.arange(self.n)) / self.n
        idx = np.minimum(np.searchsorted(np.cumsum(w), pos), self.n - 1)
        self.st = {k: v[idx].copy() for k, v in self.st.items()}
        self.cumll = self.cumll[idx]
        self.logw = np.zeros(self.n)
        self._w = None
        self.model.refresh(t, self.st, self.rng)
        self.n_resampled += 1

    def _move(self, t: int) -> None:
        """The independence move: each particle's whole path is proposed afresh from the
        prior and the kernel (BeliefModel.replay) and accepted with probability
        min(1, L(new path) / L(old path)).  The kernel leaves the posterior over paths
        invariant, so it is valid on weighted particles too; it can re-seed a region an
        earlier resampling emptied (R11), which no local move of iota or sigma can."""
        for _ in range(MOVE_STEPS):
            new, ll = self.model.replay(t, self.history, self.quarantines, self.rng, self.n)
            acc = np.log(self.rng.random(self.n)) < ll - self.cumll
            if acc.any():
                self.st = {k: np.where(acc, new[k], v) for k, v in self.st.items()}
                self.cumll = np.where(acc, ll, self.cumll)
            self.n_moved += 1
            self.n_accepted += int(acc.sum())

    def condition_on_quarantine(self, t: int, carrier: str) -> None:
        """Lines 8-9 removed every live item of `carrier`: c[carrier] = 0 everywhere."""
        if carrier not in BIT:
            raise ValueError(f"carrier {carrier!r} is not one of {CARRIERS}")
        self.st["c"] = (self.st["c"] & ~np.uint8(BIT[carrier])).astype(np.uint8)
        self.quarantines.setdefault(t, []).append(carrier)

    def particles(self) -> dict:
        """The particle arrays (read-only view): attacked, kmask, iota, sigma, c, harmed."""
        return self.st


def make_belief(ctx: A.EpisodeContext, delta_hat=None, *, betas: dict | None = None,
                delta_prior: str = DELTA_PRIOR, n: int = N_PARTICLES,
                p_attack: float = PRIOR_P_ATTACK) -> ParticleBelief:
    """api.BeliefFactory: b_0 of one episode.  `delta_hat` None = the prior of O3;
    `betas` None = O11 (dev base + ctx.postmortems); betas = {} is the '- benign-drift
    modelling' ablation (T15)."""
    model = BeliefModel.for_context(ctx, delta_hat, betas=betas, delta_prior=delta_prior,
                                    p_attack=p_attack)
    return ParticleBelief(model, n=n,
                          seed=seed_of(ctx.rng_seed, ctx.wf_id, ctx.seed, "v3-belief-pf"))


# ---------------------------------------------------------------------------------------
# Timing (plan T9: 2048 particles per task must be cheap; P0 measured +10.1 us per task)
# ---------------------------------------------------------------------------------------

def _main() -> int:
    import time
    cell = C.Cell(rho=0.5, delta=4)
    H = 14
    ctx = A.EpisodeContext(world=C.PRIMARY, cell=cell, wf_id="timing", seed=1, H=H,
                           budget=1e9, depths=cell.depths(), kappa=cell.kappa(),
                           delegated=cell.delegated(), rng_seed=1)
    rng = np.random.default_rng(seed_of("v3-pf-timing"))
    targets = C.TARGETS + (None,)
    obs_seq = []
    for t in range(H):
        g = targets[t % len(targets)]
        if g is None:
            obs_seq.append(A.Observation(t=t, requested=None, bought=None, checkpoint=True))
        elif g == "commit":
            a = A.AuditAction(g, cell.depths()[g])
            obs_seq.append(A.Observation(t=t, requested=a, bought=a, scores=(float(rng.normal()),),
                                         written_at=(t,), checkpoint=True))
        else:
            a = A.AuditAction(g, cell.depths()[g])
            n = t + 1
            obs_seq.append(A.Observation(t=t, requested=a, bought=a,
                                         scores=tuple(float(x) for x in rng.normal(size=n)),
                                         written_at=tuple(range(n)), checkpoint=True))
    reps = 200
    b0 = make_belief(ctx, 4)
    t0 = time.perf_counter()
    for _ in range(reps):
        b = make_belief(ctx, 4)
    t_init = (time.perf_counter() - t0) / reps
    global MOVE_ON_ALARM
    keep = MOVE_ON_ALARM
    n_alarm = sum(1 for o in obs_seq if o.bought is not None
                  and any(s > b0.model.tau for s in o.scores))
    for on in (True, False):
        MOVE_ON_ALARM = on
        t0 = time.perf_counter()
        nres = nmov = 0
        for r in range(reps):
            b = make_belief(ctx, 4)
            for t, o in enumerate(obs_seq):
                b.update(t, o)
            nres += b.n_resampled
            nmov += b.n_moved
        t_ep = (time.perf_counter() - t0) / reps - t_init
        print(f"particle filter, N = {b0.n}, H = {H}, MOVE_ON_ALARM = {on}: init "
              f"{t_init * 1e6:.0f} us, update {t_ep / H * 1e6:.1f} us per task "
              f"({nres / reps:.1f} resamples, {nmov / reps:.1f} moves per episode; "
              f"{n_alarm} alarm tasks of {H})")
    MOVE_ON_ALARM = keep
    t0 = time.perf_counter()
    for _ in range(reps * 10):
        b.bin_features(); b.p_poisoned(); b.expected_harm()
    print(f"read-outs (bin_features + p_poisoned + expected_harm): "
          f"{(time.perf_counter() - t0) / (reps * 10) * 1e6:.1f} us")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
