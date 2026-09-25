"""addendum_d35.py -- the systems of the D35 addendum (preregistration D35).

Not in freeze.SOURCE: the addendum has its own freeze (freeze_d35.py, frozen/MANIFEST-D35.json),
so the base freeze sha256:c789fa7362e0 stays clean.

Arm A  "A1 dhat-*": Sentinel-A1 told a WRONG Delta on the grid (a degraded line 1); it plays the
       frozen mixture of that Delta.  Defined at the headline Deltas only.
Arm B  "B2 FQ-matched": B2 with a commit probability p, tuned on dev per (rho, Delta) so that its
       FQ% does not exceed that of Sentinel's mixture (tools/tune_d35.py).
Arm C  "A1 fixed interleave": the best FIXED-PHASE schedule of an 11-member family on dev, per
       (rho, Delta), by the objective of `pure` (lowest worst-case harm with FQ% <= the cap).
"""
from __future__ import annotations

import json
import pathlib

import carrier_policies as CP
import draft_setup as D
import sentinel as S

D35_TUNED_PATH = pathlib.Path(__file__).resolve().parent / "reference" / "d35_tuned.json"

#: Arm A: the Delta line 1 is told, per true headline Delta (D35).
DHAT = {"A1 dhat-swap": {4: 8, 8: 4},
        "A1 dhat-down1": {4: 2, 8: 4},
        "A1 dhat-down2": {4: 1, 8: 2}}
B2_FQ = "B2 FQ-matched"
FIXED = "A1 fixed interleave"
ARMS = list(DHAT) + [B2_FQ, FIXED]
#: Arm B: commit probabilities from B2's own share (0.25) to B1 (1.0).
P_GRID = tuple(round(0.25 + 0.05 * i, 2) for i in range(16))
B2P_PREFIX = "B2p:"                          # tuning names, e.g. "B2p:0.6"


class B2CommitProb(CP.CarrierPolicy):
    """B2 with a commit probability: each task a depth-3 commit review with probability p,
    else a depth-3 sweep of a carrier drawn uniformly from D.SWEEP_CARRIERS.  Quarantines every
    firing item (the baseline rule)."""
    def __init__(self, *a, p=0.25, **kw):
        super().__init__(*a, **kw)
        self.p = p

    def act(self, t):
        g = self.rng(t, "b2p")
        if g.random() < self.p:
            return (D.COMMIT, D.MAX_DEPTH)
        return (g.choice(D.SWEEP_CARRIERS), D.MAX_DEPTH)


class FixedRotation(CP.CarrierRotation):
    """An RO schedule with its phase fixed at 0 for every workflow and seed."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.phase = 0


class FixedAlternation(CP._Believer):
    """A depth-3 commit review at every task t with t % m == m - 1; the other tasks sweep
    memory, queue, skill in turn, at depth 3.  Fixed phase."""
    def __init__(self, *a, m=2, **kw):
        super().__init__(*a, **kw)
        self.m = m

    def act(self, t):
        if t % self.m == self.m - 1:
            return (D.COMMIT, D.MAX_DEPTH)
        i = t - (t + 1) // self.m                   # index of t among the sweep tasks
        return (D.SWEEP_CARRIERS[i % len(D.SWEEP_CARRIERS)], D.MAX_DEPTH)


FIXED_LIBRARY = {}
for _o in ("c3", "c4"):
    for _p in (1, 2):
        for _d in (2, 3):
            FIXED_LIBRARY[f"FI-{_o}-p{_p}-d{_d}"] = (FixedRotation,
                                                     {"order": _o, "period": _p, "depth": _d})
for _m in (2, 3, 4):
    FIXED_LIBRARY[f"FI-alt-m{_m}"] = (FixedAlternation, {"m": _m})


def load_d35(path=D35_TUNED_PATH) -> dict:
    p = pathlib.Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def _cell(table: dict, rho: float, delta: int) -> dict:
    return table[f"{rho:g}"][str(delta)]


def make_policy_d35(name, *, budget, kappa, H, rng_seed, setting, tuned, d35, rho_patch, delta,
                    attacked=None, eta_q=None):
    """Every system of the addendum by name, and its tuning names (B2p:<p>, FI-*).  Any other
    name goes to sentinel.make_policy unchanged (B1, Sentinel-A1, ...)."""
    cfg = S.cfg_for(tuned, rho_patch)
    if name in DHAT:
        if delta not in DHAT[name]:
            raise ValueError(f"{name} is defined at Delta {sorted(DHAT[name])}, not {delta}")
        return S.make_policy("Sentinel-A1", budget=budget, kappa=kappa, H=H, rng_seed=rng_seed,
                             setting=setting, tuned=tuned, rho_patch=rho_patch,
                             delta=DHAT[name][delta], eta_q=eta_q)
    if name == B2_FQ or name.startswith(B2P_PREFIX):
        p = (_cell(d35["b2_fq"], rho_patch, delta)["p"] if name == B2_FQ
             else float(name[len(B2P_PREFIX):]))
        return B2CommitProb(budget, kappa, H, rng_seed, setting, cfg, p=p)
    if name == FIXED or name in FIXED_LIBRARY:
        member = _cell(d35["fixed"], rho_patch, delta)["member"] if name == FIXED else name
        cls, kw = FIXED_LIBRARY[member]
        eq = cfg.get("eta_q", D.ETA_Q_BAYES) if eta_q is None else eta_q
        return cls(budget, kappa, H, rng_seed, setting, cfg, betas=tuned.get("betas", {}),
                   eta_q=eq, **kw)
    return S.make_policy(name, budget=budget, kappa=kappa, H=H, rng_seed=rng_seed,
                         setting=setting, tuned=tuned, rho_patch=rho_patch, delta=delta,
                         attacked=attacked, eta_q=eta_q)
