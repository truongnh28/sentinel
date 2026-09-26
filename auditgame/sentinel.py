"""sentinel.py -- Sentinel as Algorithm 1 in the carrier world, its ablations, the registry.

line 1: the regime (Delta, chi) of the cell is given to Sentinel -- a PERFECT line-1
        estimator, declared (D9b); "A1 -regime estimate" drops it and plays the mixture
        tuned over every Delta at once.
line 5: commit to the robust minimax MIXTURE over the 28-policy library, solved on dev for
        this regime under the SS4 objective (worst-case harm, FQ% <= cap, D26); reveal
        only the mixture; draw ONE member per workflow.
line 7: the member's drift-aware window belief.
line 8: the member quarantines a firing item iff P(payload | score) > eta_Q (tuned, D11).
Tuned table (reference/v2_tuned.json):
  {"betas": {carrier: beta_hat},
   "rho": {"<rho:g>": {"tau5": x, "eta_q": x,
                       "mix": {"<setting>|<regime>": {"robust": {name: w}, "nominal": {...},
                                                      "pure": name, "value": v, "fq_pct": f}}}}}
  regime = str(Delta) or "all".
"""
from __future__ import annotations

import json
import pathlib

import carrier_policies as CP
import draft_setup as D

TUNED_PATH = pathlib.Path(__file__).resolve().parent / "reference" / "v2_tuned.json"


def load_tuned(path=TUNED_PATH) -> dict:
    p = pathlib.Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def cfg_for(tuned: dict, rho: float) -> dict:
    """The tuned block for rho; cut (T3): an untuned rho reads the NEAREST tuned one
    (ties to the smaller).  Declared."""
    by = tuned.get("rho", {})
    if not by:
        return {}
    key = f"{rho:g}"
    if key in by:
        return by[key]
    return by[min(by, key=lambda k: (abs(float(k) - rho), float(k)))]


def mix_key(setting: str, regime) -> str:
    return f"{setting}|{regime}"


class SentinelA1(CP.CarrierPolicy):
    def __init__(self, budget, kappa, H, rng_seed=0, setting="mid", cfg=None, *,
                 variant="full", delta=None, betas=None, eta_q=None,
                 drift_match=D.DRIFT_MATCH):
        super().__init__(budget, kappa, H, rng_seed, setting, cfg)
        regime = "all" if (variant == "no-regime" or delta is None) else str(delta)
        cell = self.cfg["mix"][mix_key(setting, regime)]
        self.variant = variant
        if variant == "no-random":
            self.member_name, member_seed = cell["pure"], 0      # one schedule for everyone
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
        used_betas = {} if variant == "no-drift" else dict(betas or {})
        self.eta_q = self.cfg.get("eta_q", D.ETA_Q_BAYES) if eta_q is None else eta_q
        self.member = CP.make_member(self.member_name, budget, kappa, H, member_seed, setting,
                                     self.cfg, used_betas, self.eta_q, drift_match,
                                     stateless=(variant == "stateless"))

    # the member IS the executed policy; Sentinel is the draw (line 5)
    @property
    def spent(self):
        return self.member.spent

    @spent.setter
    def spent(self, v):
        pass                                          # base __init__ sets 0.0; member owns it

    def affordable(self, t, cost):
        return self.member.affordable(t, cost)

    def charge(self, cost):
        self.member.charge(cost)

    def act(self, t):
        return self.member.act(t)

    def observe(self, t, obs):
        self.member.observe(t, obs)

    def remove(self, t, k, firing, deep, live):
        return self.member.remove(t, k, firing, deep, live)


VARIANTS = {"Sentinel-A1": "full", "A1 -randomization": "no-random",
            "A1 -alarm memory": "stateless", "A1 -transition uncertainty": "nominal",
            "A1 -benign-drift": "no-drift", "A1 -regime estimate": "no-regime"}
CONTROL = "Oracle (control)"
REGISTRY = list(CP.BASELINES) + list(VARIANTS) + [CONTROL]


def make_policy(name, *, budget, kappa, H, rng_seed, setting, tuned, rho_patch, delta,
                drift_match=D.DRIFT_MATCH, attacked=None, eta_q=None):
    """Every system of the study by name.  Library members (L-...) are allowed for tuning.
    `eta_q` overrides the tuned line-8 threshold (tuning, and the SS11 sweep)."""
    cfg = cfg_for(tuned, rho_patch)
    betas = tuned.get("betas", {})
    if name in CP.BASELINES:
        return CP.BASELINES[name](budget, kappa, H, rng_seed, setting, cfg)
    if name in VARIANTS:
        return SentinelA1(budget, kappa, H, rng_seed, setting, cfg, variant=VARIANTS[name],
                          delta=delta, betas=betas, eta_q=eta_q, drift_match=drift_match)
    if name == CONTROL:
        return CP.OracleControl(budget, kappa, H, rng_seed, setting, cfg, attacked=attacked)
    return CP.make_member(name, budget, kappa, H, rng_seed, setting, cfg, betas,
                          cfg.get("eta_q", D.ETA_Q_BAYES) if eta_q is None else eta_q,
                          drift_match)
