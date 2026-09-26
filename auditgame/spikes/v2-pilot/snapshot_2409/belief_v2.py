"""belief_v2.py -- draft SS5.4: benign drift as a per-carrier competing cause.

A carrier that is NOT poisoned still produces evidence ev with probability beta_k
(drift matched to poisoning, D6), so its likelihood is (1 - beta_k) + beta_k*ev.
betas = {} collapses that to 1: every alarm is evidence of poisoning only -- the
"- benign-drift modelling" ablation.
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
