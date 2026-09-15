"""
policies.py -- Baselines B1..B6 + Sentinel.

Every policy answers ONE question per task:
    WHICH CARRIER do I audit (or the commit, or nothing) -- within the budget left?

Methodological constraint: EVERY policy runs on the SAME budget B and the SAME
detector.  Otherwise the comparison means nothing.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from core import CARRIERS, seed_of
import scoring

# Audit costs.  This is the placeholder awaiting the lab's per-carrier cost table;
# for now taken from the per-STAGE costs in manuscript SS7.
KAPPA = {"memory": 0.4, "skill": 0.9, "queue": 1.6, "branch": 4.1}
KAPPA_COMMIT = 4.1

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
        for c in CARRIERS:
            sig = signals.get(c)
            evidence = (sig.p / scoring.PI0) if sig is not None else 1.0
            self.belief[c] = (1 - self.BETA) * self.belief[c] + self.BETA * evidence

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

REGISTRY = {
    "B1 audit-at-commit": AuditAtCommit,
    "B2 uniform random":  UniformRandom,
    "B3 audit-on-insertion": AuditOnInsertion,
    "B4 audit-on-retrieval": AuditOnRetrieval,
    "B5 risk-score":      RiskScore,
    "B6 two-stage":       TwoStage,
    "Sentinel":           Sentinel,
}

def make_policy(name: str, budget: float, rng_seed: int = 0,
                setting: str = "mid") -> Policy:
    """Factory -- N2.  The old runner used `lambda n, b: cls(n, b)`, so rng_seed
    fell back to 0 for EVERY workflow: we were measuring ONE dice roll repeated 40
    times, not 40 samples.  For a thesis whose central claim is "randomisation is
    the strongest lever", that has to be fixed before stating any confidence
    interval at all.
    """
    return REGISTRY[name](name=name, budget=budget, rng_seed=rng_seed, setting=setting)


def cost_of(action: str | None) -> float:
    if action is None: return 0.0
    return KAPPA_COMMIT if action == "commit" else KAPPA[action]
