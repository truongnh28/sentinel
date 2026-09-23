"""policies_library.py -- the 28-policy class the manuscript compares against.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 6B, 6D;
docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md P4.

WHAT 28 IS AND IS NOT.  The manuscript says "28 policies, three families" and
gives no list, so the number has to be EARNED rather than reproduced: Stage 6D
asks for it to be justified by rho SATURATING -- adding policies stops lowering
the covering radius -- not by matching a figure in a table.  The grid below is
therefore declared as a grid (its axes, and why each axis exists), and the count
falls out of it: 8 + 12 + 8.  If saturation says 20 is enough, the honest report
is 20 with the measurement beside it.

A SEPARATE REGISTRY, ON PURPOSE.  These do not go into `policies.REGISTRY`.
That dict is what `experiment.main()` iterates, and every entry costs a full
attacker-class maximisation per cell; folding 28 more in would multiply the main
grid's cost by three and bury B1..B7 in a table nobody reads.  The library is
for rho and for the covering argument, and tools opt into it by name.

WHAT EACH FAMILY IS A HYPOTHESIS ABOUT.  A policy class that is just "28 knob
settings" cannot support a covering argument -- the point is to span the space
of REASONABLE defenders, so that "no policy in the class does better" means
something.  The three families are three different answers to "where should the
budget go":

    stage-weighted    by CHANNEL, fixed in advance and ignoring evidence.
                      B1 = all mass on commit is the corner of this family, so
                      the baseline the paper must beat is IN the class rather
                      than outside it.
    belief-threshold  by EVIDENCE: audit where the posterior is high enough,
                      and at a chosen DEPTH.  This is the only family that
                      exercises kappa(k, depth), which Theorem 4's corollary
                      about depth has no experimental branch without.
    carrier-rotation  by COVERAGE: never leave a carrier unwatched for long,
                      which is the one thing a belief policy can fail at.
"""
from __future__ import annotations

import random

from core import CARRIERS, seed_of
import policies as P

#: Audit depths the belief family reaches.  Depth is not free -- policies.cost_of
#: charges kappa(k) * depth -- so a deep policy audits fewer places.  That
#: trade-off is the experimental branch of the depth corollary.
DEPTHS = (1, 2, 3)

#: Posterior thresholds.  Four, spanning "audit on a whisper" to "audit only on
#: strong evidence"; the endpoints matter more than the spacing.
TAUS = (0.3, 0.5, 0.7, 0.9)

#: Fixed weight vectors over the five action channels, in the order
#: (memory, skill, queue, branch, commit).  Declared, not sampled: a family whose
#: members are drawn at random cannot be reported as a class.
STAGE_WEIGHTS = {
    "SW-commit":      (0, 0, 0, 0, 1),      # B1's corner, inside the class
    "SW-uniform":     (1, 1, 1, 1, 1),
    "SW-carriers":    (1, 1, 1, 1, 0),
    "SW-ingress":     (2, 1, 1, 0, 0),      # where items ENTER
    "SW-egress":      (0, 0, 1, 2, 2),      # where they LEAVE
    "SW-memory":      (3, 1, 1, 1, 1),
    "SW-branch":      (1, 1, 1, 3, 1),
    "SW-half-commit": (1, 1, 1, 1, 4),
}

#: Rotation orders, each a rule for ranking carriers without looking at evidence.
ROTATIONS = {
    "declared":    lambda kap: list(CARRIERS),
    "cheap-first": lambda kap: sorted(CARRIERS, key=lambda c: kap[c]),
    "dear-first":  lambda kap: sorted(CARRIERS, key=lambda c: -kap[c]),
    "alternating": lambda kap: [c for pair in zip(
        sorted(CARRIERS, key=lambda c: kap[c]),
        sorted(CARRIERS, key=lambda c: -kap[c])) for c in pair][:len(CARRIERS)],
}

#: How many tasks a rotation stays on one carrier before moving on.
PERIODS = (1, 2)

CHANNELS = tuple(CARRIERS) + ("commit",)


class _StageWeighted(P.Policy):
    """Sample a channel from a FIXED distribution, ignoring every signal.

    Randomised but not adaptive: this family is the control for "does the gain
    come from randomisation or from reacting to evidence", which the C4/C8
    ablation answers only for Sentinel's particular mix.
    """
    WEIGHTS: tuple = (1, 1, 1, 1, 1)
    READS_SCORES = False
    RANDOMIZED = True

    def choose(self, t, retrieved_carriers, signals):
        opts, w = [], []
        for ch, wt in zip(CHANNELS, self.WEIGHTS):
            if wt <= 0:
                continue
            if self.can(P.cost_of(ch)):
                opts.append(ch)
                w.append(float(wt))
        if not opts:
            return None
        r = random.Random(seed_of(self.rng_seed, t, self.name)).random() * sum(w)
        acc = 0.0
        for ch, wi in zip(opts, w):
            acc += wi
            if r <= acc:
                return ch
        return opts[-1]


class _BeliefThreshold(P.Policy):
    """Audit the most suspicious carrier IF it clears tau -- at a fixed depth.

    The belief is the same exponential update Sentinel uses (UPDATE_RULES), so
    this family differs from Sentinel in the DECISION RULE, not in what it knows.
    Deterministic on purpose: it is the family a best-responding attacker should
    find easiest to route around, which is what makes it useful in a covering
    argument.
    """
    TAU: float = 0.5
    DEPTH: int = 1
    READS_SCORES = True
    RANDOMIZED = False

    def choose(self, t, retrieved_carriers, signals):
        # Lazily, NOT in __post_init__: Policy is a dataclass and these classes
        # are built with type(), so they are not themselves @dataclass -- the
        # generated __init__ belongs to the base and never calls a hook defined
        # only here.  A subclass that looks initialised and is not is worse than
        # one that initialises on first use.
        if not hasattr(self, "_b"):
            self._b = {c: 1.0 for c in CARRIERS}
        rule = P.UPDATE_RULES[self.update_rule]
        for c in CARRIERS:
            sig = signals.get(c)
            ev = rule(sig.p) if sig is not None else 1.0
            self._b[c] = 0.75 * self._b[c] + 0.25 * max(ev, 0.0)
        # The threshold is on the EVIDENCE RATIO, which is 1.0 under no evidence
        # and grows with it; tau is expressed on the same scale by shifting, so
        # tau = 0.5 means "half again as much evidence as silence".
        hot = [c for c in CARRIERS if self._b[c] >= 1.0 + self.TAU]
        if not hot:
            return None
        c = max(hot, key=lambda k: self._b[k])
        for d in range(self.DEPTH, 0, -1):
            act = c if d == 1 else f"{c}{P.DEPTH_SEP}{d}"
            if self.can(P.cost_of(act)):
                return act
        return None


class _CarrierRotation(P.Policy):
    """Walk a fixed order, holding each carrier for PERIOD tasks.

    No evidence, no randomisation: pure coverage.  It is the family that bounds
    how long any carrier can go unwatched, which is exactly the failure mode a
    belief policy has when the detector is weak.
    """
    ORDER: str = "declared"
    PERIOD: int = 1
    READS_SCORES = False
    RANDOMIZED = False

    def choose(self, t, retrieved_carriers, signals):
        order = ROTATIONS[self.ORDER](P.KAPPA)
        start = (t // max(self.PERIOD, 1)) % len(order)
        for i in range(len(order)):
            c = order[(start + i) % len(order)]
            if self.can(P.cost_of(c)):
                return c
        return None


def _build() -> dict:
    out: dict = {}
    for nm, w in STAGE_WEIGHTS.items():
        out[nm] = type(nm, (_StageWeighted,), {"WEIGHTS": w})
    for tau in TAUS:
        for d in DEPTHS:
            nm = f"BT-tau{tau}-d{d}"
            out[nm] = type(nm.replace(".", "_").replace("-", "_"),
                           (_BeliefThreshold,), {"TAU": tau, "DEPTH": d})
    for order in ROTATIONS:
        for per in PERIODS:
            nm = f"ROT-{order}-p{per}"
            out[nm] = type(nm.replace("-", "_"), (_CarrierRotation,),
                           {"ORDER": order, "PERIOD": per})
    return out


#: The class itself.  Deliberately NOT merged into policies.REGISTRY.
LIBRARY = _build()

FAMILIES = {
    "stage-weighted": tuple(STAGE_WEIGHTS),
    "belief-threshold": tuple(n for n in LIBRARY if n.startswith("BT-")),
    "carrier-rotation": tuple(n for n in LIBRARY if n.startswith("ROT-")),
}


def make(name: str, budget: float, rng_seed: int = 0, setting: str = "mid",
         update_rule: str = "ratio") -> P.Policy:
    """Same factory shape as policies.make_policy, so callers stay uniform."""
    return LIBRARY[name](name=name, budget=budget, rng_seed=rng_seed,
                         setting=setting, update_rule=update_rule)
