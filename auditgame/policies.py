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
    """A policy's SCOPE.  Spec: SPEC-Framework-Benchmark.md SS2.4.

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
        return self.spent + cost <= self.budget + 1e-9

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

    def __init__(self, name: str, budget: float, rng_seed: int = 0,
                 setting: str = "mid", update_rule: str = "ratio", h: int = 8):
        super().__init__(name=name, budget=budget, rng_seed=rng_seed,
                         setting=setting, update_rule=update_rule)
        import lp
        carriers_ordered = list(CARRIERS)
        kap = [KAPPA[c] for c in carriers_ordered]
        self._carriers = carriers_ordered
        self.u, self.v, self.m = lp.solve_stackelberg_lp(
            K=len(self._carriers), H=h, B=budget, kap=kap, kc=KAPPA_COMMIT, deltas=(0, 2, 4)
        )

    def choose(self, t: int, retrieved_carriers: list, signals: dict) -> str | None:
        if t >= len(self.v):
            return None
        rng = random.Random(seed_of(self.rng_seed, t, "minimax_lp"))
        if self.v[t] > 1e-6 and rng.random() < self.v[t] and self.can(KAPPA_COMMIT):
            return "commit"
        for i, c in enumerate(self._carriers):
            prob = self.u[i][t]
            if prob > 1e-6 and rng.random() < prob and self.can(KAPPA[c]):
                return c
        return None


REGISTRY = {
    "B1 audit-at-commit": AuditAtCommit,
    "B2 uniform random":  UniformRandom,
    "B3 audit-on-insertion": AuditOnInsertion,
    "B4 audit-on-retrieval": AuditOnRetrieval,
    "B5 risk-score":      RiskScore,
    "B6 two-stage":       TwoStage,
    "B7 minimax-lp":      MinimaxLP,
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
