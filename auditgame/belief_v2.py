"""belief_v2.py -- draft SS5.1/SS5.4: the window belief with benign drift as a competing
cause (line 7), and the item posterior line 8 acts on.

DriftBelief: a carrier that is NOT poisoned still shows evidence ev in a task with
probability beta_k (a drift EVENT, D6), so its likelihood is (1 - beta_k) + beta_k*ev.
betas = {} collapses that to 1 -- the "- benign-drift modelling" ablation.

item_posterior: P(item is the payload | its score) against two competitors, a fresh drift
event (mean match*d') and a clean item (mean 0), all with unit variance (the detector's
model, Assumption 2).
"""
from __future__ import annotations

import math

import scoring
from belief import WindowBelief


class DriftBelief(WindowBelief):
    def __init__(self, carriers, H, deltas, betas: dict, pi_attack: float = 0.5):
        super().__init__(carriers, H, [d for d in deltas if d < H] or [0], beta=0.0,
                         pi_attack=pi_attack)
        self.betas = dict(betas)

    def update(self, t: int, signals: dict) -> None:
        ev = {}
        for c in self.carriers:
            p = signals.get(c)
            p = getattr(p, "p", p)
            ev[c] = 1.0 if p is None else max(float(p), 1e-12) / scoring.PI0
        clean = {c: (1 - self.betas.get(c, 0.0)) + self.betas.get(c, 0.0) * ev[c]
                 for c in self.carriers}
        all_clean = math.prod(clean.values())
        post = {}
        for win in self.windows:
            k = win[0]
            like = ev[k] * all_clean / clean[k] if self.active(win, t) else all_clean
            post[win] = self.b[win] * like
        post[self.NULL] = self.b[self.NULL] * all_clean
        z = sum(post.values())
        if z > 0:
            self.b = {h: v / z for h, v in post.items()}


def item_posterior(s: float, d_prime: float, prior_poison: float, prior_drift: float,
                   match: float = 1.0) -> float:
    """P(payload | score s) with Gaussian likelihood ratios against N(0, 1)."""
    lp = prior_poison * math.exp(min(700.0, d_prime * s - d_prime * d_prime / 2))
    md = match * d_prime
    ld = prior_drift * math.exp(min(700.0, md * s - md * md / 2))
    lc = max(0.0, 1.0 - prior_poison - prior_drift)
    z = lp + ld + lc
    return lp / z if z > 0 else 0.0
