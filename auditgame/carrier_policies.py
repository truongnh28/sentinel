"""carrier_policies.py -- policies of the carrier world: baselines B1..B6 (SS9.2), the
positive control, and the 28-policy library of SS5.2 (8 SW + 12 BT + 8 RO).

Contract with carrier_runner.run_carrier:
  act(t) -> (target, depth) | None        ONE action per task (SS4)
  affordable(t, cost), charge(cost), spent  pacing spent <= B*(t+1)/H for every policy (D4)
  observe(t, obs)                          obs: carrier_runner.Observation | None
  remove(t, k, firing, deep, live) -> items to quarantine among the FIRING items of carrier k
Baselines "quarantine on any anomaly" (SS4: drift is what makes that rule non-optimal).
Library members carry the drift belief and remove by Algorithm 1 line 8 (D11), because
they run inside Sentinel.
"""
from __future__ import annotations

import random

import belief_v2
import draft_setup as D
from core import CARRIERS, seed_of


class CarrierPolicy:
    def __init__(self, budget, kappa, H, rng_seed=0, setting="mid", cfg=None):
        self.budget, self.kappa, self.H = budget, kappa, H
        self.rng_seed, self.setting = rng_seed, setting
        self.cfg = cfg or {}
        self.spent = 0.0
        self.last = None                 # the last Observation, None if nothing was bought

    def affordable(self, t, cost) -> bool:
        return self.spent + cost <= self.budget * (t + 1) / self.H * (1 + 1e-9)

    def charge(self, cost) -> None:
        self.spent += cost

    def rng(self, *tag) -> random.Random:
        return random.Random(seed_of(self.rng_seed, *tag))

    def act(self, t):
        return None

    def observe(self, t, obs) -> None:
        self.last = obs

    def remove(self, t, k, firing, deep, live) -> list:
        return [it for it, _ in firing]                  # quarantine on any anomaly


# ------------------------------------------------------------------ baselines (SS9.2)
class B1AuditAtCommit(CarrierPolicy):
    """SS5.2: the whole budget on the final commit of each task, at maximum depth."""
    def act(self, t):
        return (D.COMMIT, D.MAX_DEPTH)


class B2UniformRandom(CarrierPolicy):
    """SS5.6: spread uniformly over every audit kind and task (randomized)."""
    def act(self, t):
        return (self.rng(t, "b2").choice(D.TARGETS), D.MAX_DEPTH)


class B3AuditOnInsertion(CarrierPolicy):
    """The insertion audit is the memory carrier's audit (D2)."""
    def act(self, t):
        return ("memory", D.MAX_DEPTH)


class B4AuditOnRetrieval(CarrierPolicy):
    """The retrieval audit is the queue carrier's audit (D2)."""
    def act(self, t):
        return ("queue", D.MAX_DEPTH)


class B5RiskScore(CarrierPolicy):
    """Cheap depth-1 sweeps in a fixed rotation; a deep commit audit on the task after a
    carrier signal passes tau5 (D12)."""
    def act(self, t):
        if self.last is not None and self.last.posterior is not None \
                and self.last.posterior > self.cfg.get("tau5", 0.3):
            return (D.COMMIT, D.MAX_DEPTH)
        return (D.SWEEP_CARRIERS[t % len(D.SWEEP_CARRIERS)], 1)


class B6TwoStage(CarrierPolicy):
    """Adaptive-contracts style [1]: a cheap random screen, a deep confirmation of the same
    carrier on the task after it fires."""
    def act(self, t):
        if self.last is not None and self.last.fired and self.last.target in D.SWEEP_CARRIERS:
            return (self.last.target, D.MAX_DEPTH)
        return (self.rng(t, "b6").choice(D.SWEEP_CARRIERS), 1)


BASELINES = {
    "B1 audit-at-commit": B1AuditAtCommit,
    "B2 uniform random": B2UniformRandom,
    "B3 audit-on-insertion": B3AuditOnInsertion,
    "B4 audit-on-retrieval": B4AuditOnRetrieval,
    "B5 risk-score": B5RiskScore,
    "B6 two-stage": B6TwoStage,
}


class OracleControl(CarrierPolicy):
    """POSITIVE CONTROL (D28), not a competitor: it is told the attacked carrier."""
    def __init__(self, *a, attacked=None, **kw):
        super().__init__(*a, **kw)
        self.attacked = attacked

    def act(self, t):
        if self.attacked in D.SWEEP_CARRIERS:
            return (self.attacked, D.MAX_DEPTH)
        return (D.COMMIT, D.MAX_DEPTH)


# ------------------------------------------------------------------ the library (SS5.2)
class _Believer(CarrierPolicy):
    """Line 7 (drift-aware window belief) and line 8 (item-level quarantine: a firing item
    goes iff P(payload | score) > eta_Q -- v1's precedent, runner.py line-8 block)."""
    def __init__(self, *a, betas=None, eta_q=D.ETA_Q_BAYES, drift_match=D.DRIFT_MATCH,
                 stateless=False, **kw):
        super().__init__(*a, **kw)
        self.betas = dict(betas or {})
        self.eta_q = eta_q
        self.drift_match = drift_match
        self.stateless = stateless
        self.belief = belief_v2.DriftBelief(CARRIERS, self.H, D.DELTAS, self.betas)

    def observe(self, t, obs):
        super().observe(t, obs)
        if self.stateless:
            self.belief = belief_v2.DriftBelief(CARRIERS, self.H, D.DELTAS, self.betas)
        sig = {obs.target: obs.posterior} if obs is not None and obs.posterior is not None else {}
        self.belief.update(t, sig)

    def remove(self, t, k, firing, deep, live):
        if not firing:
            return []
        p_k = self.belief.carrier_mass(t).get(k, 0.0)
        n = max(1, len(live))
        n_fresh = max(1, sum(1 for it in live if it.created_at == t))
        out = []
        for it, s in firing:
            p_drift = self.betas.get(k, 0.0) / n_fresh if it.created_at == t else 0.0
            p = belief_v2.item_posterior(s, deep.d_prime, p_k / n, p_drift, self.drift_match)
            if p > self.eta_q:
                out.append(it)
        return out


class CarrierWeighted(_Believer):
    """SW family: each task, draw the target with probability proportional to its weight."""
    def __init__(self, *a, weights=(1, 1, 1, 1), **kw):
        super().__init__(*a, **kw)
        self.w = dict(zip(D.TARGETS, weights))

    def act(self, t):
        r = self.rng(t, "sw").random() * sum(self.w.values())
        acc = 0.0
        for k in D.TARGETS:
            acc += self.w[k]
            if r < acc:
                return (k, D.MAX_DEPTH)
        return (D.TARGETS[-1], D.MAX_DEPTH)


class BeliefThreshold(_Believer):
    """BT family: commit while p_attack <= tau; above it, SAMPLE a carrier from
    floor*uniform + (1-floor)*posterior carrier mass (randomized, SS5.3; the floor keeps
    every carrier covered against a Stackelberg attacker)."""
    def __init__(self, *a, tau=0.5, floor=0.0, **kw):
        super().__init__(*a, **kw)
        self.tau, self.floor = tau, floor

    def act(self, t):
        if self.belief.p_attack() <= self.tau:
            return (D.COMMIT, D.MAX_DEPTH)
        mass = self.belief.carrier_mass(t)
        tot = sum(mass[k] for k in D.SWEEP_CARRIERS)
        u = 1.0 / len(D.SWEEP_CARRIERS)
        w = {k: self.floor * u + (1 - self.floor) * (mass[k] / tot if tot > 0 else u)
             for k in D.SWEEP_CARRIERS}
        r, acc = self.rng(t, "bt").random(), 0.0
        for k in D.SWEEP_CARRIERS:
            acc += w[k]
            if r < acc:
                return (k, D.MAX_DEPTH)
        return (D.SWEEP_CARRIERS[-1], D.MAX_DEPTH)


class CarrierRotation(_Believer):
    """RO family: cycle through `order`, each target held `period` tasks, at `depth`, from a
    RANDOM PHASE drawn per workflow (pilot 2b: a phased rotation keeps the rotation's
    coverage guarantee at Delta >= len(order) and removes its exploitability below it)."""
    def __init__(self, *a, order="c3", period=1, depth=3, **kw):
        super().__init__(*a, **kw)
        self.order = D.SWEEP_CARRIERS if order == "c3" else D.TARGETS
        self.period, self.depth = period, depth
        self.phase = self.rng("ro-phase").randrange(len(self.order) * period)

    def act(self, t):
        return (self.order[((t + self.phase) // self.period) % len(self.order)], self.depth)


_SW = {"commit": (0, 0, 0, 1), "uniform": (1, 1, 1, 1), "sweeps": (1, 1, 1, 0),
       "memory": (3, 1, 1, 1), "queue": (1, 3, 1, 1), "skill": (1, 1, 3, 1),
       "commit3": (1, 1, 1, 3), "nomemory": (0, 1, 1, 1)}     # weights over D.TARGETS
_TAUS = (0.3, 0.5, 0.7, 0.9)
_FLOORS = (0.0, 1 / 3, 2 / 3)

LIBRARY = {}
for _n, _w in _SW.items():
    LIBRARY[f"L-SW-{_n}"] = (CarrierWeighted, {"weights": _w})
for _tau in _TAUS:
    for _i, _f in enumerate(_FLOORS):
        LIBRARY[f"L-BT-{_tau}-f{_i}"] = (BeliefThreshold, {"tau": _tau, "floor": _f})
for _o in ("c3", "c4"):
    for _p in (1, 2):
        for _d in (2, 3):
            LIBRARY[f"L-RO-{_o}-p{_p}-d{_d}"] = (CarrierRotation, {"order": _o, "period": _p, "depth": _d})


def make_member(name, budget, kappa, H, rng_seed, setting, cfg, betas, eta_q,
                drift_match=D.DRIFT_MATCH, stateless=False):
    cls, kw = LIBRARY[name]
    return cls(budget, kappa, H, rng_seed, setting, cfg, betas=betas, eta_q=eta_q,
               drift_match=drift_match, stateless=stateless, **kw)
