"""stage_policies.py -- v2 policies over ranked (stage, depth) plans.

Part 1: base class and the draft's baselines B1..B6 (SS9.2).  Every policy
spends on the same pacing rule spent <= B*(t+1)/H (D4).  Plans are RANKED: the
runner buys the first n_slots affordable ones (D1).
"""
from __future__ import annotations

import random

import draft_setup as D
import scoring
from core import seed_of


def cfg_for(tuned: dict, mode: str, rho: float) -> dict:
    """Tuned block for (mode, rho): tuned["modes"][mode]["<rho:g>"].

    Cut (T3): a mode without its own block reads "single".  Cut (T4): a rho that was
    not tuned reads the NEAREST tuned rho (ties to the smaller).  Both are declared.
    """
    modes = tuned.get("modes", {})
    by_rho = modes.get(mode) or modes.get("single") or {}
    if not by_rho:
        return {}
    key = f"{rho:g}"
    if key in by_rho:
        return by_rho[key]
    return by_rho[min(by_rho, key=lambda k: (abs(float(k) - rho), float(k)))]


class StagePolicy:
    def __init__(self, budget, kappa, H, rng_seed=0, setting="mid", tuned=None,
                 action_mode="single", rho_patch=1.0):
        self.budget, self.kappa, self.H = budget, kappa, H
        self.rng_seed, self.setting, self.action_mode = rng_seed, setting, action_mode
        self.tuned = tuned or {}
        self.rho_patch = rho_patch
        self.cfg = cfg_for(self.tuned, action_mode, rho_patch)
        self.spent = 0.0
        self.last_alarm = 0.0            # max carrier posterior seen at the previous task

    def can(self, cost):
        return self.spent + cost <= self.budget * (1 + 1e-9)

    def affordable(self, t, cost):
        return self.spent + cost <= self.budget * (t + 1) / self.H * (1 + 1e-9)

    def charge(self, cost):
        self.spent += cost

    def per_task(self):
        return self.budget / self.H

    def rng(self, *tag):
        return random.Random(seed_of(self.rng_seed, *tag))

    def plan(self, t):
        return []

    def escalate(self, t, log):
        return None

    def observe(self, t, signals):
        post = [p for p in signals.values() if p is not None]
        self.last_alarm = max(post) if post else 0.0

    def quarantine(self, t):
        return None


class B1AuditAtCommit(StagePolicy):
    """Draft SS4: the whole budget on the final commit of each task, max depth."""
    def plan(self, t):
        return [("commit", D.MAX_DEPTH)]


class B2UniformRandom(StagePolicy):
    """Each stage at depth 1 with p = (B/H)/sum(kappa), in a random order."""
    def plan(self, t):
        p = min(1.0, self.per_task() / sum(self.kappa.values()))
        chosen = [s for s in D.STAGES if self.rng(t, "b2", s).random() < p]
        self.rng(t, "b2-order").shuffle(chosen)
        return [(s, 1) for s in chosen]


class B3AuditOnInsertion(StagePolicy):
    def plan(self, t):
        return [("insertion", D.MAX_DEPTH)]


class B4AuditOnRetrieval(StagePolicy):
    def plan(self, t):
        return [("retrieval", D.MAX_DEPTH)]


class B5RiskScore(StagePolicy):
    """Score retrievals; a deep commit audit when the score passes tau5 (D12) --
    in the same task if a slot is left, else at the next task."""
    def _tau(self):
        return self.cfg.get("tau5", 0.3)

    def plan(self, t):
        if self.last_alarm > self._tau():
            return [("commit", D.MAX_DEPTH), ("retrieval", 1)]
        return [("retrieval", 1)]

    def escalate(self, t, log):
        post = [p for p in log.posterior().values() if p is not None]
        return D.MAX_DEPTH if post and max(post) > self._tau() else None


class B6TwoStage(StagePolicy):
    """Adaptive-contracts-style [1]: cheap upstream checks, the expensive one on an alarm."""
    def plan(self, t):
        if self.last_alarm > scoring.PI0:
            return [("commit", D.MAX_DEPTH), ("insertion", 1), ("retrieval", 1)]
        return [("insertion", 1), ("retrieval", 1)]

    def escalate(self, t, log):
        return D.MAX_DEPTH if log.fired else None


BASELINES = {
    "B1 audit-at-commit": B1AuditAtCommit,
    "B2 uniform random": B2UniformRandom,
    "B3 audit-on-insertion": B3AuditOnInsertion,
    "B4 audit-on-retrieval": B4AuditOnRetrieval,
    "B5 risk-score": B5RiskScore,
    "B6 two-stage": B6TwoStage,
}


# ============================================================ Part 2: the library (SS5.2: 8 + 12 + 8)
import belief_v2
from core import CARRIERS

_SW = {  # weights over (insertion, retrieval, delegation, commit)
    "commit": (0, 0, 0, 1), "uniform": (1, 1, 1, 1), "upstream": (1, 1, 1, 0),
    "ingress": (2, 1, 0, 0), "egress": (0, 0, 1, 2), "retrieval": (0, 3, 1, 1),
    "delegation": (0, 1, 3, 1), "half-commit": (1, 1, 1, 4),
}
_TAUS = (0.3, 0.5, 0.7, 0.9)
_UP = ("insertion", "retrieval", "delegation")
#: The two DISTINCT cyclic orders of three stages.  Not derived from kappa: on the
#: draft table kappa's order equals the declared order, so "cheap-first"/"dear-first"
#: were copies of "declared"/"reverse" (and at chi = 0 all four collapsed) -- review 25/09 #9.
_ORDERS = {"abc": _UP, "acb": ("insertion", "delegation", "retrieval")}


class _Believer(StagePolicy):
    def __init__(self, budget, kappa, H, rng_seed=0, setting="mid", tuned=None,
                 action_mode="single", rho_patch=1.0, betas=None):
        super().__init__(budget, kappa, H, rng_seed, setting, tuned, action_mode, rho_patch)
        self.betas = dict(betas or {})
        self.belief = belief_v2.DriftBelief(CARRIERS, H, D.DELTAS, self.betas)

    def observe(self, t, signals):
        super().observe(t, signals)
        self.belief.update(t, signals)


class StageWeighted(_Believer):
    """Spend share w_s of the per-task budget on stage s; ranked by weight."""
    def __init__(self, *a, weights=(1, 1, 1, 1), **kw):
        super().__init__(*a, **kw)
        self.w = dict(zip(D.STAGES, weights))

    def plan(self, t):
        tot = sum(self.w.values())
        out = []
        for s in sorted(D.STAGES, key=lambda s: -self.w[s]):
            share = self.w[s] / tot * self.per_task()
            if share <= 0:
                continue
            depth = min(D.MAX_DEPTH, int(share // self.kappa[s]))
            if depth >= 1:
                out.append((s, depth))
            elif self.rng(t, "sw", s).random() < share / self.kappa[s]:
                out.append((s, 1))
        return out


class BeliefThreshold(_Believer):
    """Above tau, audit the stage covering the most suspect live carrier at depth d; commit@1 after."""
    def __init__(self, *a, tau=0.5, depth=1, **kw):
        super().__init__(*a, **kw)
        self.tau, self.depth = tau, depth

    def plan(self, t):
        if self.belief.p_attack() <= self.tau:
            return [("commit", 1)]
        mass = self.belief.carrier_mass(t)
        stage = D.CARRIER_STAGE[max(mass, key=mass.get)]
        return [("commit", self.depth)] if stage == "commit" else [(stage, self.depth), ("commit", 1)]


class StageRotation(_Believer):
    """One upstream stage at `depth`, rotated every `period` tasks; commit@1 after.
    2 orders x 2 periods x 2 depths = 8 distinct schedules."""
    def __init__(self, *a, order="abc", period=1, depth=1, **kw):
        super().__init__(*a, **kw)
        self.order, self.period, self.depth = _ORDERS[order], period, depth

    def plan(self, t):
        return [(self.order[(t // self.period) % len(self.order)], self.depth), ("commit", 1)]


LIBRARY = {}
for _n, _w in _SW.items():
    LIBRARY[f"L-SW-{_n}"] = (StageWeighted, {"weights": _w})
for _tau in _TAUS:
    for _d in D.DEPTHS:
        LIBRARY[f"L-BT-{_tau}-d{_d}"] = (BeliefThreshold, {"tau": _tau, "depth": _d})
for _o in _ORDERS:
    for _p in (1, 2):
        for _d in (1, 2):
            LIBRARY[f"L-RO-{_o}-p{_p}-d{_d}"] = (StageRotation, {"order": _o, "period": _p, "depth": _d})


def make_library_policy(name, budget, kappa, H, rng_seed, setting, tuned, betas,
                        action_mode="single", rho_patch=1.0):
    cls, kw = LIBRARY[name]
    return cls(budget, kappa, H, rng_seed, setting, tuned, action_mode, rho_patch,
               betas=betas, **kw)


# ============================================================ Part 3: Sentinel (Algorithm 1)
import json
import pathlib

TUNED_PATH = pathlib.Path(__file__).resolve().parent / "reference" / "v2_tuned.json"


def load_tuned(path=TUNED_PATH) -> dict:
    p = pathlib.Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


class SentinelA1(StagePolicy):
    """Algorithm 1 at scale (D9, D10, D11).

    line 5: commit to the robust minimax MIXTURE over the 28-policy library (solved on
            dev); reveal only the mixture; draw one member per workflow.
    line 7: the member's DriftBelief.
    line 8: quarantine the live carrier with the largest window mass p_k when
            p_attack > tau_Q (a gate, tuned on dev) and p_k > eta_Q = m * lambda_Q/(1+lambda_Q),
            the Bayes threshold for binary harm (p_k * 1 > lambda_Q * (1 - p_k)).
    """
    def __init__(self, budget, kappa, H, rng_seed=0, setting="mid", tuned=None,
                 action_mode="single", rho_patch=1.0, *, variant="full", eta_mult=1.0):
        super().__init__(budget, kappa, H, rng_seed, setting, tuned, action_mode, rho_patch)
        mixes = self.cfg["mix"]            # (mode, rho) block; cuts T3/T4 handled by cfg_for
        cell = mixes[f"{setting}|{round(D.chi_reported(kappa), 2)}"]
        self.variant = variant
        if variant == "no-random":
            self.member_name, member_seed = cell["pure"], 0     # same schedule everywhere
        else:
            mix = cell["nominal" if variant == "nominal" else "robust"]
            names = sorted(mix)
            r = self.rng("a1-pick").random() * sum(mix.values())
            acc, self.member_name = 0.0, names[-1]
            for n in names:
                acc += mix[n]
                if r <= acc:
                    self.member_name = n
                    break
            member_seed = rng_seed
        self._betas = {} if variant == "no-drift" else self.tuned.get("betas", D.BETA_WORLD)
        self.member = make_library_policy(self.member_name, budget, kappa, H, member_seed,
                                          setting, self.tuned, self._betas, action_mode,
                                          rho_patch)
        self.tau_q = self.cfg.get("tau_q", 1.0)
        self.eta_q = D.eta_q_threshold(eta_mult)          # Bayes threshold on p_k (D11)

    def plan(self, t):
        return self.member.plan(t)

    def escalate(self, t, log):
        return self.member.escalate(t, log)

    def observe(self, t, signals):
        if self.variant == "stateless":
            self.member.belief = belief_v2.DriftBelief(CARRIERS, self.H, D.DELTAS, self._betas)
        self.member.observe(t, signals)

    def quarantine(self, t):
        b = self.member.belief
        if b.p_attack() <= self.tau_q:
            return None
        mass = b.carrier_mass(t)
        c = max(mass, key=mass.get)
        return c if mass[c] > self.eta_q else None


def _base(cls):
    return lambda budget, kappa, H, rng_seed, setting, tuned, action_mode, rho_patch, eta_mult: cls(
        budget, kappa, H, rng_seed, setting, tuned, action_mode, rho_patch)


def _a1(variant):
    return lambda budget, kappa, H, rng_seed, setting, tuned, action_mode, rho_patch, eta_mult: SentinelA1(
        budget, kappa, H, rng_seed, setting, tuned, action_mode, rho_patch,
        variant=variant, eta_mult=eta_mult)


REGISTRY_V2 = {n: _base(c) for n, c in BASELINES.items()}
REGISTRY_V2.update({
    "Sentinel-A1": _a1("full"),
    "A1 -randomization": _a1("no-random"),
    "A1 -alarm memory": _a1("stateless"),
    "A1 -transition uncertainty": _a1("nominal"),
    "A1 -benign-drift": _a1("no-drift"),
})


def make_v2(name, *, budget, kappa, H, rng_seed, setting, tuned, action_mode="single",
            rho_patch=1.0, eta_mult=1.0):
    """rho_patch is the WORLD's delegated-patch exposure; the defender knows it
    (Assumption 2: the detector is known) and reads the matching tuned block."""
    if name in REGISTRY_V2:
        return REGISTRY_V2[name](budget, kappa, H, rng_seed, setting, tuned, action_mode,
                                 rho_patch, eta_mult)
    return make_library_policy(name, budget, kappa, H, rng_seed, setting, tuned,
                               tuned.get("betas", D.BETA_WORLD), action_mode, rho_patch)
