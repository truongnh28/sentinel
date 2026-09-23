"""
policies.py -- Baselines B1..B6 + Sentinel.

Every policy answers ONE question per task:
    WHICH CARRIER do I audit (or the commit, or nothing) -- within the budget left?

Methodological constraint: EVERY policy runs on the SAME budget B and the SAME
detector.  Otherwise the comparison means nothing.
"""
from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from core import CARRIERS, seed_of
import scoring

# Audit costs.  This is the placeholder awaiting the lab's per-carrier cost table;
# for now taken from the per-STAGE costs in manuscript SS7.
KAPPA = {"memory": 0.4, "skill": 0.9, "queue": 1.6, "branch": 4.1}
KAPPA_COMMIT = 4.1

#: Cost of a QUARANTINE action.  Toan-canh SS3: "besides auditing the defender has a
#: second tool -- quarantine, which removes a carrier from the loop entirely, at a
#: fixed cost eta_Q".  It is a SEPARATE ACTION, not only a threshold: modelling it
#: as a threshold alone makes the degenerate policy of SSA.4 inexpressible, so the
#: test that rules that policy out cannot be written.
#: Prefix used in the action space: "quarantine:<carrier>", or "quarantine:all"
#: for the wholesale sweep that Toan-canh SSA.4's degenerate policy performs.
ETA_Q_COST = 2.0
QUARANTINE_PREFIX = "quarantine:"
QUARANTINE_ALL = "quarantine:all"

#: Audit DEPTH.  The model's action is (audit, k, depth) and its cost is the
#: two-argument kappa(k, depth); the code had a bare carrier name and a
#: one-argument lookup, so "a deeper audit costs more and sees more" did not exist.
#: Action spelling: "memory@2".  A bare "memory" means depth 1.
DEPTHS = (1, 2)
DEPTH_SEP = "@"

#: Belief UPDATE RULES.  Each maps a carrier posterior p_c to an evidence weight.
#:
#: These exist because RQ3's answer turned out to depend on which one is used.
#: Three implementations of this benchmark reported randomisation +0.184 / belief
#: +0.099, randomisation +0.131 / belief -0.025, and randomisation +0.069 / belief
#: +0.161 -- not a disagreement about the world, a disagreement about calibration.
#: The old "1 + 2*p" was tuned for a [0,1] score centred at 0.38/0.62; on the
#: posterior scale it spans a belief range of 1.86 against a 1/kappa range of 10.2,
#: so cost dominates and the belief contributes exactly 0.0000.
#:
#: Sweeping them and reporting the RANGE is what makes RQ3 a statement one can
#: check.  Naming one and freezing it would also be honest; quoting a number
#: without saying which rule produced it is not.
UPDATE_RULES = {
    # posterior ratio -- 1.0 under no evidence, proportional to evidence strength,
    # so the range is ~[0, 5] and comparable with 1/kappa.
    "ratio":  lambda p: p / scoring.PI0,
    # the pre-N1 rule, kept so the historical number stays reproducible.
    "linear": lambda p: 1.0 + 2.0 * p,
    # compresses strong evidence: a carrier ten times more likely is not ten times
    # more worth auditing once the cheap ones are already covered.
    "log":    lambda p: 1.0 + math.log(max(p, 1e-12) / scoring.PI0),
    # flat -- identical to C4 by construction, and the control that proves the
    # sweep is wired to something.
    "flat":   lambda p: 1.0,
}


@dataclass(frozen=True)
class CarrierSignal:
    """The ONLY thing a policy ever sees about a carrier.

    `p` is the POSTERIOR (scoring.carrier_score), not a raw score -- see SPEC
    SS2.5.  `n` is the number of live items, needed to look up tau_sel: the
    threshold depends on n_c because the quantile of p_c on a clean carrier is a
    function of n (and REVERSES DIRECTION across detector settings: weak
    decreasing, strong increasing).

    No field leads to `poisoned`.  I2 holds structurally.
    """
    p: float
    n: int


@dataclass(frozen=True)
class DefenseScope:
    """A policy's SCOPE.  Spec: docs/thesis/pipelines/SPEC-Framework-Benchmark.md SS2.4.

    `reads_scores` and `randomized` are NOT decoration -- they are two
    declarations the F3/F4 contracts can enforce, and both were born from bugs
    that were actually measured:

      F3  Sentinel declared that it used its belief, yet the ablation gave
          EXACTLY 0.0000 at every Delta: C4 "blind Sentinel" was identical to
          Sentinel.  Declaring "reads scores" while the score cannot change
          behaviour is RED, not a result.
      F4  `rng_seed` used to be ALWAYS 0, making Sentinel a DETERMINISTIC
          schedule repeated across every workflow -- while randomisation is the
          central claim.
    """
    actions: frozenset
    reads_scores: bool
    randomized: bool


@dataclass
class Policy:
    name: str
    budget: float
    spent: float = 0.0
    rng_seed: int = 0
    setting: str = "mid"          # for the tau_sel lookup; NOT ground truth
    _rot: int = 0

    #: Algorithm 1 line 8 -- the TWO-CONDITION quarantine rule.
    #:     Pr[poisoned | b] > tau_quarantine   AND   E[harm] > eta_Q
    #: math-foundation SS8.2: the second condition is what prevents "quarantine
    #: everything".  Both default to 0.0, which reproduces the old unconditional
    #: behaviour EXACTLY, so every number recorded before this change still holds.
    #: They are SWEPT and reported, not assigned -- the same treatment as eps* and
    #: lambda_Q*.  Picking a value here would be inventing a constant the
    #: manuscript never published.
    tau_quarantine: float = 0.0
    eta_Q: float = 0.0

    #: Which UPDATE_RULES entry Sentinel's belief uses.  Declared per policy so a
    #: results table can say which rule produced it.
    update_rule: str = "ratio"

    def can(self, cost: float) -> bool:
        """Affordability, with slack RELATIVE to the budget.

        The slack used to be a flat 1e-9, which is a quantity in the same unit as
        kappa -- so it meant something different on every cost table.  The game
        is otherwise invariant under rescaling (kappa, kappa_commit, eta_Q, B) by
        a common factor: every use of a cost is either a ratio to another cost or
        a comparison against the budget.  A flat slack was the one thing that
        broke that invariance, and it broke it silently: rescaling the USD table
        by 1e-6 moved SentinelW's L from 0.855 to 0.8625, because 1e-9 had grown
        into 6% of the budget.  Relative slack makes the unit of kappa what it
        should be -- free.
        """
        return self.spent + cost <= self.budget * (1.0 + 1e-9)

    def charge(self, cost: float):
        self.spent += cost

    def tau(self, sig: "CarrierSignal", k: int) -> float:
        """CARRIER-SELECTION threshold, from the frozen table, keyed by (n_c, setting, K).

        Replaces the old `threshold = 0.55` -- that constant was calibrated for a
        [0,1] scale centred at 0.38/0.62.  On the posterior scale it gives a clean
        9-item carrier a 0.955 chance of exceeding it, and at `strong` it matches
        no n at all.
        """
        return scoring.tau_sel(sig.n, self.setting, k)

    #: Subclasses redeclare these three.  The default is the most conservative.
    ACTIONS = frozenset(CARRIERS) | {"commit"}
    READS_SCORES = False
    RANDOMIZED = False

    def scope(self) -> DefenseScope:
        return DefenseScope(actions=self.ACTIONS, reads_scores=self.READS_SCORES,
                            randomized=self.RANDOMIZED)

    def choose(self, t: int, retrieved_carriers: list, signals: dict) -> str | None:
        """signals: {carrier -> CarrierSignal}.  Returns 'memory'|...|'commit'|None."""
        raise NotImplementedError

class AuditAtCommit(Policy):          # B1 -- the headline comparator
    ACTIONS = frozenset({"commit"})
    def choose(self, t, retrieved_carriers, signals):
        return "commit" if self.can(KAPPA_COMMIT) else None

class UniformRandom(Policy):          # B2
    RANDOMIZED = True
    def choose(self, t, retrieved_carriers, signals):
        opts = [c for c in CARRIERS if self.can(KAPPA[c])]
        if self.can(KAPPA_COMMIT): opts.append("commit")
        if not opts: return None
        return random.Random(seed_of(self.rng_seed, t)).choice(opts)

class AuditOnInsertion(Policy):       # B3 -- the first instinct, and the worst policy
    ACTIONS = frozenset({"memory"})
    def choose(self, t, retrieved_carriers, signals):
        return "memory" if self.can(KAPPA["memory"]) else None

class AuditOnRetrieval(Policy):       # B4
    ACTIONS = frozenset(CARRIERS)
    def choose(self, t, retrieved_carriers, signals):
        for c in retrieved_carriers:
            if self.can(KAPPA[c]): return c
        return None

class RiskScore(Policy):              # B5 -- LED BY the attacker: shape the payload to sit just under the threshold
    ACTIONS = frozenset(CARRIERS)
    READS_SCORES = True
    def choose(self, t, retrieved_carriers, signals):
        k = max(1, sum(1 for s in signals.values() if s.n))     # K_t
        hot = [c for c in CARRIERS
               if c in signals and signals[c].p > self.tau(signals[c], k)
               and self.can(KAPPA[c])]
        if not hot: return None
        return max(hot, key=lambda c: signals[c].p)

class TwoStage(Policy):               # B6 -- cheap check first, expensive second
    ACTIONS = frozenset(CARRIERS)
    READS_SCORES = True
    def choose(self, t, retrieved_carriers, signals):
        k = max(1, sum(1 for s in signals.values() if s.n))
        cheap = sorted((c for c in CARRIERS if self.can(KAPPA[c])), key=KAPPA.get)
        if not cheap: return None
        pricey = cheap[-1]
        sig = signals.get(pricey)
        if sig is not None and sig.p > self.tau(sig, k) and self.can(KAPPA[pricey]):
            return pricey
        return cheap[0]

@dataclass
class Sentinel(Policy):
    """Three mechanisms, in the order of contribution the ablation reports:

      1. RANDOMISATION  (the strongest lever -- removing it costs 0.184)
         commit to a DISTRIBUTION, reveal only the distribution, never the draw.
      2. BELIEF STATE   (removing it costs only 0.099)
         an alarm raises the posterior for the carrier that fired.
      3. ROTATION       makes sure no carrier goes unwatched for long.
    """
    belief: dict = field(default_factory=lambda: {c: 1.0 for c in CARRIERS})

    ACTIONS = frozenset(CARRIERS)
    READS_SCORES = True
    RANDOMIZED = True

    BETA = 0.25          # update rate

    def observe(self, signals: dict):
        """belief <- (1-beta) belief + beta * (p_c / pi0).

        The old `1 + 2*score` was calibrated for a [0,1] scale centred at
        0.38/0.62.  On the posterior scale (concentrated near pi0=0.1, tail out to
        ~0.5) it spanned a belief range of 1.86 while the 1/kappa range is 10.2,
        so COST DOMINATED and the belief became useless.  Measured on the old
        version: Sentinel minus C4 (belief removed) was EXACTLY 0.0000 at every
        Delta -- the belief had never participated in a decision.

        p_c/pi0 equals 1.0 under no evidence and scales with evidence strength, so
        the range becomes ~[0, 5] -- comparable to the cost range.
        """
        rule = UPDATE_RULES[self.update_rule]
        for c in CARRIERS:
            sig = signals.get(c)
            evidence = rule(sig.p) if sig is not None else 1.0
            self.belief[c] = (1 - self.BETA) * self.belief[c] + self.BETA * max(evidence, 0.0)

    def choose(self, t, retrieved_carriers, signals):
        self.observe(signals)
        opts = [c for c in CARRIERS if self.can(KAPPA[c])]
        if not opts: return None
        # weight = belief / cost  -> prefer the suspicious places that are cheap
        w = [self.belief[c] / KAPPA[c] for c in opts]
        tot = sum(w)
        r = random.Random(seed_of(self.rng_seed, t, "sentinel")).random() * tot
        acc = 0.0
        for c, wi in zip(opts, w):
            acc += wi
            if r <= acc: return c
        return opts[-1]

# --------------------------------------------------------------------------
# Controls.  Not competitors -- instruments.
# --------------------------------------------------------------------------

class BlindSentinel(Sentinel):
    """C4 -- drop the belief, KEEP randomisation and the 1/kappa weighting.

    Whatever gain survives is PURE PRICE DIFFERENTIAL.
    """
    READS_SCORES = False
    def observe(self, signals):
        pass                                  # belief frozen at 1.0


class DeterministicSentinel(Sentinel):
    """C8 -- KEEP the belief, drop randomisation.  The complement of C4.

    Without C8 the ablation RQ3 rests on is absent from gate 2.  And RQ3 turns out
    to be unstable across implementations: three independent measurements give
    randomisation > belief, belief harmful, and belief > randomisation. The
    ablation measures the CALIBRATION of the update rule, not the value of state.
    """
    RANDOMIZED = False
    def choose(self, t, retrieved_carriers, signals):
        self.observe(signals)
        opts = [c for c in CARRIERS if self.can(KAPPA[c])]
        if not opts:
            return None
        return max(opts, key=lambda c: self.belief[c] / KAPPA[c])


class QuarantineEverything(Policy):
    """NC1 -- the null control from Toan-canh SSA.4: quarantine every carrier, at once.

    It uses the QUARANTINE action, not the audit action.  An earlier version audited
    the cheapest carrier each task, which is not the degenerate policy at all -- it
    is B3 under another name, and measured, it did not even win on harm (0.913
    against B1's 0.720) because the poison propagated to carriers it never touched.
    A control that fails to exhibit the behaviour it exists to rule out proves
    nothing.

    It MUST LOSE under L.  On harm alone it is unbeatable by construction -- an
    empty store carries no payload -- which is exactly why SSA.4 rejects the
    one-term model.
    """
    ACTIONS = frozenset({QUARANTINE_ALL})
    def choose(self, t, retrieved_carriers, signals):
        return QUARANTINE_ALL if self.can(cost_of(QUARANTINE_ALL)) else None


class MinimaxLP(Policy):
    """B7 -- exact Stackelberg Minimax LP policy (Conitzer & Sandholm 2006).

    Precomputes optimal marginal audit coverages u[k, t] and v[t] via simplex LP,
    then samples randomized audit actions within the remaining hard budget.
    """
    ACTIONS = frozenset(CARRIERS) | {"commit"}
    READS_SCORES = False
    RANDOMIZED = True

    #: The DECLARED attacker class Pi_A this policy commits against.  A MODELLING
    #: DECISION, not a tuning knob: the LP's answer is only as broad as the class
    #: it was solved on (Toan-canh SSA.5, "worst-case in WHICH set?").
    #:
    #: Keeping Delta=0 in the class is what makes commit-audit minimax-optimal:
    #: a Delta=0 window has an EMPTY upstream sum, so only v[t] can cover it, the
    #: min-over-windows objective is always bound by those windows, and upstream
    #: coverage buys nothing.  Measured: deltas=(0,2,4) puts sum(u)=0.00 and
    #: sum(v)=4.38; dropping Delta=0 gives sum(u)=10.26 and m rises 0.55 -> 0.85.
    #: That is Corollary 5 reproducing itself, not a bug.
    #:
    #: Exposed as a parameter so the upstream-only class can be MEASURED without
    #: editing this file.  Changing the default changes what B7 claims, so it
    #: belongs in a pre-registration, not in a patch.
    DELTAS: tuple = (0, 2, 4)

    def __init__(self, name: str, budget: float, rng_seed: int = 0,
                 setting: str = "mid", update_rule: str = "ratio", h: int = 8,
                 deltas: tuple | None = None):
        super().__init__(name=name, budget=budget, rng_seed=rng_seed,
                         setting=setting, update_rule=update_rule)
        import lp
        carriers_ordered = list(CARRIERS)
        kap = [KAPPA[c] for c in carriers_ordered]
        self._carriers = carriers_ordered
        self.deltas = tuple(self.DELTAS if deltas is None else deltas)
        self.u, self.v, self.m = lp.solve_stackelberg_lp(
            K=len(self._carriers), H=h, B=budget, kap=kap, kc=KAPPA_COMMIT,
            deltas=self.deltas
        )

    def choose(self, t: int, retrieved_carriers: list, signals: dict) -> str | None:
        """Draw ONE action from the LP marginals for task t.

        The earlier version walked the actions in order and returned on the first
        hit, drawing a FRESH uniform for each.  Two defects followed, and both were
        measured:

          * the walk returns at the first success, so only the first action of the
            schedule ever ran.  `self._carriers` is in fixed order and `memory` is
            cheapest, so realised spend pinned at 0.400 against a budget of 17.95 --
            2.2% -- and did not move when the budget was varied.
          * per-action draws do not sample the joint the LP prescribes; they give
            each action its own independent Bernoulli, which is a different policy.

        With the per-task row now in `lp.solve_stackelberg_lp` the mass on any t is
        at most 1.0, so a single uniform draw reproduces the LP marginals EXACTLY
        and the leftover probability is the LP's own "audit nothing at t".  No
        renormalisation: renormalising would silently inflate every marginal.
        """
        if t >= len(self.v):
            return None
        opts = []
        if self.v[t] > 1e-9 and self.can(KAPPA_COMMIT):
            opts.append(("commit", self.v[t]))
        for i, c in enumerate(self._carriers):
            if self.u[i][t] > 1e-9 and self.can(KAPPA[c]):
                opts.append((c, self.u[i][t]))
        if not opts:
            return None
        r = random.Random(seed_of(self.rng_seed, t, "minimax_lp")).random()
        acc = 0.0
        for c, w in opts:
            acc += w
            if r <= acc:
                return c
        return None



class MinimaxLPUpstream(MinimaxLP):
    """B7U -- B7 with the UPSTREAM attacker class declared instead of the default.

    Spec: docs/preregistration/TIEN-DANG-KY-Sentinel-SSG.md SS4 (two registered variants).

    NOT a tuning variant: the declared class Pi_A DECIDES the solution, and the two
    classes are two different problems.  Measured: (0,2,4) puts sum(u) = 0.00 and
    sum(v) = 4.38 -- commit-only, because a Delta=0 window has an EMPTY upstream sum
    so only v can cover it and the min-over-windows objective is always bound there.
    Dropping Delta=0 gives sum(u) = 10.26 and m rises 0.55 -> 0.85.

    Registered as its OWN policy rather than by editing MinimaxLP.DELTAS, so both
    classes are reported side by side.  Toan-canh SSA.5: the declared class is part
    of the claim, so reporting both IS the result.

    It exists to be the STATIC control for SSG-up: using B7 on (0,2,4) as that
    control would mix "what does the receding horizon buy" with "what does the
    class buy".
    """
    DELTAS = (2, 4)


class SSGReceding(MinimaxLP):
    """Re-solve the minimax coverage every task, over the windows STILL OPEN.

    Spec: docs/preregistration/TIEN-DANG-KY-Sentinel-SSG.md SS4, step 3.

    WHY.  The static LP is solved once at construction against the NOMINAL budget
    and never learns what it has spent, while `Policy.can` enforces the cap online.
    The solution saturates 100% of B in expectation, so the tail of the schedule is
    cut and realised coverage falls short of the marginals -- the knapsack gap of
    Toan-canh SSF.5.  Re-solving against the REMAINING budget recovers it.

    WHAT IT DOES NOT DO.  No belief restriction: that is step 6 of the
    pre-registration and needs a posterior over WINDOWS which does not exist yet.
    At the default class this policy is therefore "B1 with a re-solve", because
    (0,2,4) is commit-only; the upstream variant below is the one that tests the
    minimax claim.

    Its own seed label.  A sibling policy sharing `"minimax_lp"` would draw the same
    stream and the two would stop being independent samples; a mislabelled seed was
    measured to move harm by 0.13, larger than most effects under study.
    """
    SEED_TAG = "ssg_receding"

    def choose(self, t: int, retrieved_carriers: list, signals: dict) -> str | None:
        import lp
        kap = [KAPPA[c] for c in self._carriers]
        u, v, _m, n_win = lp.solve_remaining_lp(
            K=len(self._carriers), H=len(self.v) or 8, t=t,
            B_rem=max(self.budget - self.spent, 0.0), kap=kap,
            kc=KAPPA_COMMIT, deltas=self.deltas, done=getattr(self, "_done", None))
        # A zero-window solve returns m = 1.0 from the empty min.  Refusing here is
        # the difference between "nothing left to protect" and "perfect coverage".
        if n_win == 0 or not v:
            return None
        opts = []
        if v[0] > 1e-9 and self.can(KAPPA_COMMIT):
            opts.append(("commit", v[0]))
        for i, c in enumerate(self._carriers):
            if u[i][0] > 1e-9 and self.can(KAPPA[c]):
                opts.append((c, u[i][0]))
        if not opts:
            return None
        r = random.Random(seed_of(self.rng_seed, t, self.SEED_TAG)).random()
        acc = 0.0
        for c, w in opts:
            acc += w
            if r <= acc:
                self._log_audit(t, c)
                return c
        return None

    def _log_audit(self, t: int, carrier: str) -> None:
        """Record a PERFORMED audit so `done` counts actions, not intentions."""
        if not hasattr(self, "_hist"):
            self._hist = []
            self._done = {}
        self._hist.append((t, carrier))
        if carrier == "commit":
            return
        k = self._carriers.index(carrier)
        H = len(self.v) or 8
        for d in self.deltas:
            for i in range(H - d):
                s = i + d
                if i <= t < s:
                    self._done[(k, i, s)] = self._done.get((k, i, s), 0) + 1


class SSGRecedingUpstream(SSGReceding):
    """SSG-up -- the receding-horizon solve on the UPSTREAM class.

    This is the variant the pre-registration names for the MAIN verdict: on the
    default class the policy is commit-only, so "beats B1" would only measure the
    re-solve, not the minimax.
    """
    DELTAS = (2, 4)
    SEED_TAG = "ssg_receding_up"


class SentinelWindow(Policy):
    """Sentinel as Toan-canh section 5.1 and 5.4 describe it -- belief over WINDOWS.

    WHAT CHANGED FROM `Sentinel`.  That class keeps four floats, one per
    carrier, moved by an exponential average. It has no time axis, so it cannot
    express section 5.1's central claim: an alarm at task t raises the
    posterior on insertions at t' < t whose trigger is still at t'' > t. This
    one carries `belief.WindowBelief`, a posterior over (carrier, iota, sigma)
    plus a NULL hypothesis for benign drift, so the claim is representable and
    the drift rate beta competes for the same evidence (section 5.4) instead of
    being a separate knob.

    WHAT IT KEEPS.  The action weighting is still mass over cost -- audit where
    it is both suspicious and cheap -- and the draw is still randomised over a
    committed distribution (section 5.2). Only the source of "suspicious"
    moved, from a per-carrier average to the mass of windows LIVE AT t.

    WHY `commit` IS IN ACTIONS, unlike `Sentinel`.  Measured 2026-09-20: with
    `ACTIONS = frozenset(CARRIERS)` the policy has no move at all when
    Delta = 0, because insertion and detonation share a task and the commit
    gate is the only one left. A best-responding attacker then pins it there
    and every other mechanism it has never runs -- section 9.1.1. Leaving the
    hole in would measure the hole, not the belief.
    """

    belief_state: object = None

    ACTIONS = (frozenset(CARRIERS) | {"commit"}
               | {QUARANTINE_PREFIX + c for c in CARRIERS})
    READS_SCORES = True
    RANDOMIZED = True

    #: Attack windows the belief is defined over. The DECLARED attacker class,
    #: same role as MinimaxLP.DELTAS -- a belief over windows that cannot occur
    #: would spend its mass on impossibilities.
    DELTAS = (0, 2, 4)
    #: Benign drift rate of section 5.4, as the null's prior mass.
    BETA_DRIFT = 0.25
    SEED_TAG = "sentinel_window"

    def _belief(self, H: int):
        if self.belief_state is None:
            import belief
            self.belief_state = belief.WindowBelief(
                list(CARRIERS), H=H, deltas=self.DELTAS, beta=self.BETA_DRIFT)
        return self.belief_state

    def choose(self, t: int, retrieved_carriers: list, signals: dict) -> str | None:
        H = len(getattr(self, "v", []) or []) or 8
        b = self._belief(H)
        b.update(t, signals)
        mass = b.carrier_mass(t)

        opts, w = [], []
        for c in CARRIERS:
            if self.can(KAPPA[c]):
                opts.append(c)
                w.append(mass.get(c, 0.0) / KAPPA[c])
        # The commit gate is worth the total attack mass, not any one carrier's:
        # it is the last place a poisoned patch can be stopped whatever carrier
        # carried it. This is the Delta = 0 path section 9.1.1 measured.
        if self.can(KAPPA_COMMIT):
            opts.append("commit")
            w.append(b.p_attack() / KAPPA_COMMIT)

        # QUARANTINE AS AN ACTION, not as a threshold on an audit's finding.
        #
        # ETA_Q_COST's own comment says why it has to be here: "a SEPARATE
        # ACTION, not only a threshold -- modelling it as a threshold alone
        # makes the degenerate policy of section A.4 inexpressible, so the test
        # that rules that policy out cannot be written". Before this, only NC1
        # could choose it; every real policy quarantined solely as a CONSEQUENCE
        # of auditing, so eta_Q was never charged against the budget and
        # quarantine was effectively free -- penalised only through lambda_Q in
        # the loss, which is a preference, not a constraint.
        #
        # What makes the comparison meaningful is that the two now differ in
        # WHAT THEY BUY, at prices in the same units. An audit of carrier k buys
        # EVIDENCE: it may remove the payload, and it may find nothing.
        # Quarantining k removes every item it holds, guilty or not -- certain
        # removal, certain collateral. So the weight is the mass of live windows
        # on k (the same numerator as the audit) scaled by how much of the
        # horizon is still ahead for that harm to land in, over eta_Q. A window
        # whose remaining life is short is not worth the wholesale price.
        remaining = max(H - t - 1, 0)
        if remaining and self.can(ETA_Q_COST):
            for c in CARRIERS:
                opts.append(QUARANTINE_PREFIX + c)
                w.append(mass.get(c, 0.0) * (remaining / H) / ETA_Q_COST)

        tot = sum(w)
        if not opts or tot <= 0.0:
            return None
        r = random.Random(seed_of(self.rng_seed, t, self.SEED_TAG)).random() * tot
        acc = 0.0
        for c, wi in zip(opts, w):
            acc += wi
            if r <= acc:
                return c
        return opts[-1]


class SSGRecedingGuarded(MinimaxLP):
    """Giai lai CO SAN va CO CO -- ban thiet ke lai sau chan doan cong 4c.

    Spec: docs/preregistration/TIEN-DANG-KY-Sentinel-SSG.md SS10.

    CAI DA DO O 4b.  `SSGReceding` giai lai MOI buoc thoi gian va HOI QUY tren
    lop upstream: harm 0,5721 so voi 0,4505 cua control tinh B7U, lech +0,1216.
    Chan doan 4c tach duoc:

        0,121622 = 0,027027 (bo rang buoc C) + 0,094595 (BAN THAN viec giai lai)

    Bon phan nam do chinh viec giai lai.  Co che: khi giai lai o t=1, nghiem
    tro nen DOI XUNG qua carrier ([0,25]x4), trong khi nghiem tinh BAT DOI
    XUNG theo kappa -- vi tinh bat doi xung ay la thuoc tinh cua CA CHAN TROI,
    khong phai cua phan con lai.  Ket qua: do phu cuoi tap mong hon (0,267 so
    voi 0,332), deu hon (do lech chuan 0,110 so voi 0,129), nhung CUA SO TE
    NHAT TE HON (0,074 so voi 0,105).  Muc tieu minimax tra gia cho DO SAU o
    cho yeu nhat, khong tra gia cho su dong deu.

    Ten dung cua loi: BAT NHAT THOI GIAN tren mot ngan sach dung chung.

    HAI SUA DOI, moi cai nham dung mot nua chan doan.

    (a) SAN BAO DAM.  Mot lan giai lai chi duoc CAI THIEN, khong bao gio duoc
        ha, do phu bao dam o cua so te nhat.  `_m_open` tinh do phu toi thieu
        ma KE HOACH TINH con giao duoc tren cac cua so CON MO; nghiem giai lai
        chi duoc dung khi m cua no >= con so do.  Khong dat thi GIU NGUYEN ke
        hoach da cam ket.  Bien the nay vi the KHONG THE te hon tinh theo cau
        tao -- hoi quy 4b bi chan bang rang buoc, khong bang hy vong.

    (b) PHAI CO CO.  Ly do chinh dang duy nhat de giai lai la THONG TIN MOI.
        Giai lai vi thoi gian troi thi khong co tin gi -- va do dung la cai 4b
        do duoc: mat thuan 0,0946.  Nen chi giai lai khi co BAO DONG tu tang
        phat hien (`signals` vuot TAU).

    KHE A VAO DUNG VAI.  LLM khong doi phep toan phan bo; no cung cap SU KIEN
    cho phep tai toi uu.  Ranh gioi SS4.3 giu nguyen: gamma la DAU VAO, pi_D
    la cai duoc TOI UU.

    DU DOAN CHOT TRUOC (SS10.5): duoi tan cong NGAM, phep do noi dung 20/09
    cho AUC 0,518 => d' ~ 0,06 => khong co bao dong => khong giai lai =>
    SUY BIEN VE DUNG BANG TINH.  Mot du doan co the sai.
    """

    SEED_TAG = "ssg_guarded"
    #: Nguong bao dong.  Chot truoc, khong hieu chinh sau khi thay so.
    TAU = 0.6

    def _m_open(self, t: int) -> float:
        """Do phu toi thieu KE HOACH TINH con giao duoc tren cua so con mo.

        Chi dem cac buoc t' >= t: nhung buoc da qua khong con la loi hua nao
        nua.  Day la dai luong PHAI so sanh duoc voi m cua ban giai lai, nen
        hai ben cung mot mien thoi gian.
        """
        H = len(self.v) or 8
        worst = None
        for d in self.deltas:
            for i in range(H - d):
                s = i + d
                if s < t:                      # cua so da dong
                    continue
                cov = 0.0
                for tp in range(max(i, t), min(s, H)):
                    cov += self.v[tp]
                    for k in range(len(self._carriers)):
                        cov += self.u[k][tp]
                if worst is None or cov < worst:
                    worst = cov
        return 1.0 if worst is None else worst

    def choose(self, t: int, retrieved_carriers: list, signals: dict) -> str | None:
        if t >= len(self.v):
            return None
        # `signals` la {carrier: CarrierSignal} o duong run_once, nhung mot
        # so duong goi khac da rut san `.p` thanh float -- chap nhan ca hai.
        alarm = 0.0
        for sig in (signals or {}).values():
            v = getattr(sig, "p", sig)
            if v is not None and v > alarm:
                alarm = v
        u, v = self.u, self.v
        col = t                                 # chi so cot trong ke hoach tinh
        if alarm >= self.TAU:
            import lp
            kap = [KAPPA[c] for c in self._carriers]
            ru, rv, rm, n_win = lp.solve_remaining_lp(
                K=len(self._carriers), H=len(self.v) or 8, t=t,
                B_rem=max(self.budget - self.spent, 0.0), kap=kap,
                kc=KAPPA_COMMIT, deltas=self.deltas,
                done=getattr(self, "_done", None))
            # SAN: chi nhan nghiem moi khi no KHONG HA bao dam.  n_win == 0 la
            # "khong con gi de bao ve", khac han "phu hoan hao" -- tu choi.
            if n_win and rv and rm >= self._m_open(t) - 1e-12:
                u, v, col = ru, rv, 0
            self._n_resolve = getattr(self, "_n_resolve", 0) + 1
        opts = []
        if v[col] > 1e-9 and self.can(KAPPA_COMMIT):
            opts.append(("commit", v[col]))
        for i, c in enumerate(self._carriers):
            if u[i][col] > 1e-9 and self.can(KAPPA[c]):
                opts.append((c, u[i][col]))
        if not opts:
            return None
        r = random.Random(seed_of(self.rng_seed, t, self.SEED_TAG)).random()
        acc = 0.0
        for c, w in opts:
            acc += w
            if r <= acc:
                self._log_audit(t, c)
                return c
        return None

    _log_audit = SSGReceding._log_audit


class SSGGuardedUpstream(SSGRecedingGuarded):
    """Ban guarded tren lop UPSTREAM -- lop ma tien dang ky goi ten cho phan quyet."""
    DELTAS = (2, 4)
    SEED_TAG = "ssg_guarded_up"


REGISTRY = {
    "B1 audit-at-commit": AuditAtCommit,
    "B2 uniform random":  UniformRandom,
    "B3 audit-on-insertion": AuditOnInsertion,
    "B4 audit-on-retrieval": AuditOnRetrieval,
    "B5 risk-score":      RiskScore,
    "B6 two-stage":       TwoStage,
    "B7 minimax-lp":      MinimaxLP,
    "B7U minimax-lp upstream": MinimaxLPUpstream,
    "SSG-full receding":  SSGReceding,
    "SSG-up receding":    SSGRecedingUpstream,
    "SentinelW window-belief": SentinelWindow,
    "SSG-G guarded":      SSGRecedingGuarded,
    "SSG-GU guarded upstream": SSGGuardedUpstream,
    "Sentinel":           Sentinel,
    "C4 blind sentinel":         BlindSentinel,
    "C8 deterministic sentinel": DeterministicSentinel,
    "NC1 quarantine-everything": QuarantineEverything,
}

def make_policy(name: str, budget: float, rng_seed: int = 0,
                setting: str = "mid", update_rule: str = "ratio") -> Policy:
    """Factory -- N2.  The old runner used `lambda n, b: cls(n, b)`, so rng_seed
    fell back to 0 for EVERY workflow: we were measuring ONE dice roll repeated 40
    times, not 40 samples.  For a thesis whose central claim is "randomisation is
    the strongest lever", that has to be fixed before stating any confidence
    interval at all.
    """
    return REGISTRY[name](name=name, budget=budget, rng_seed=rng_seed,
                          setting=setting, update_rule=update_rule)


def chi_of(kappa: dict) -> float:
    """chi = max_{k,k'} |kappa(k) - kappa(k')| / kappa_bar.

    DERIVED from the table, never declared beside it.  Declaring it separately is
    how the manuscript came to carry two values for one table: SS7 lists costs
    0.4 / 0.9 / 1.6 / 4.1 and says "giving chi = 1.34", while the formula on those
    same numbers gives 3.7 / 1.75 = 2.11.
    """
    vals = list(kappa.values())
    mean = sum(vals) / len(vals)
    return (max(vals) - min(vals)) / mean if mean else 0.0


def kappa_for_chi(chi: float, base: dict | None = None) -> dict:
    """A cost table with the requested chi and the SAME mean as `base`.

        kappa_c(chi) = kappa_bar + s * (kappa_c - kappa_bar),   s = chi / chi(base)

    The mean is held fixed on purpose.  If it moved, sweeping chi would secretly
    sweep the effective budget as well, and the RQ2 axis would be confounded with
    the very quantity RQ1 holds constant -- the same class of error as per-carrier
    alpha drifting along Delta.
    """
    base = dict(KAPPA if base is None else base)
    vals = list(base.values())
    mean = sum(vals) / len(vals)
    chi0 = chi_of(base)
    s = 0.0 if chi0 == 0 else chi / chi0
    return {k: mean + s * (v - mean) for k, v in base.items()}


def split_action(action: str) -> tuple:
    """"memory@2" -> ("memory", 2).  A bare name means depth 1."""
    if DEPTH_SEP in action:
        k, d = action.rsplit(DEPTH_SEP, 1)
        return k, int(d)
    return action, 1


def cost_of(action: str | None) -> float:
    if action is None:
        return 0.0
    if action == QUARANTINE_ALL:
        return ETA_Q_COST * len(CARRIERS)      # one eta_Q per carrier swept
    if action.startswith(QUARANTINE_PREFIX):
        return ETA_Q_COST
    carrier, depth = split_action(action)
    base = KAPPA_COMMIT if carrier == "commit" else KAPPA[carrier]
    return base * depth                        # kappa(k, depth), linear in depth
