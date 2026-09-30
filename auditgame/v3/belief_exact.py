"""v3/belief_exact.py -- the exact line-7 posterior by enumeration: the benchmark the
particle filter is tested against (plan T9; v2's belief.WindowBelief / belief_v2.DriftBelief
played this role in v2).

SAME MODEL, NO SAMPLING.  ExactBelief runs the prior, the transition and the likelihood of
belief_pf.BeliefModel -- the one object both use, so the two cannot drift apart -- as a
forward filter over EVERY hypothesis (attacked, kmask, iota, sigma, c, harmed):

    prior      belief_pf.BeliefModel.prior_table(), with its probabilities;
    transition each hypothesis branches on the agent's three events (skill induced,
               call queued, patch adopted), 8 branches with their kernel probabilities;
    likelihood BeliefModel.loglik on every branch;
    merge      branches that land on the same hypothesis are summed.

The support stays small -- at most 4 x H x |Delta| x 16 x 2 attacked hypotheses plus 'not
attacked', under 10^4 at H = 14 -- so the enumeration is exact for every H the corpus has,
not only the small cases the PF test uses.  It is deterministic: no seed.

`last` keeps the branches of the latest task BEFORE merging (with their posterior weights
and this task's marked / delegated flags), so a test can read the posterior of 'this
task's patch was marked through a delegated carrier' that the merge folds away.
"""
from __future__ import annotations

from itertools import product

import numpy as np

from v3 import api as A
from v3.belief_pf import (BIT, DELTA_PRIOR, PRIOR_P_ATTACK, BeliefModel, _WeightedBelief)

_KEYS = ("attacked", "kmask", "iota", "sigma", "c", "harmed")


class ExactBelief(_WeightedBelief):
    """api.BeliefAPI by exhaustive forward filtering (module docstring)."""

    def __init__(self, model: BeliefModel):
        self.model = model
        arr, p = model.prior_table()
        n = len(p)
        self.st = dict(arr)
        self.st["c"] = np.zeros(n, np.uint8)
        self.st["harmed"] = np.zeros(n, bool)
        self.logw = np.log(p)
        self._w = None
        self.t_last = -1
        self.last = None

    def weights(self) -> np.ndarray:
        if self._w is None:
            lw = self.logw - self.logw.max()
            w = np.exp(lw)
            self._w = w / w.sum()
        return self._w

    @property
    def n_states(self) -> int:
        return len(self.logw)

    def update(self, t: int, obs: A.Observation | None) -> None:
        if t <= self.t_last:
            raise ValueError(f"update(t={t}) after t={self.t_last}: line 7 runs once per task")
        while self.t_last < t - 1:
            self._step(self.t_last + 1, None)
        self._step(t, obs)

    def _step(self, t: int, obs) -> None:
        m = self.model
        n = len(self.logw)
        rates = (m.p_skill, m.p_queue, m.p_adopt)
        parts, lws, mk, dl = [], [], [], []
        for bits in product((True, False), repeat=3):
            lp = 0.0
            for b, r in zip(bits, rates):
                pr = r if b else 1.0 - r
                if pr <= 0.0:
                    lp = None
                    break
                lp += float(np.log(pr))
            if lp is None:
                continue
            st = {k: v.copy() for k, v in self.st.items()}
            ev = [np.full(n, b) for b in bits]
            marked, deleg = m.advance(t, st, *ev)
            lw = self.logw + lp
            if obs is not None:
                lw = lw + m.loglik(t, obs, st, marked, deleg)
            parts.append(st); lws.append(lw); mk.append(marked); dl.append(deleg)
        st = {k: np.concatenate([p[k] for p in parts]) for k in _KEYS}
        lw = np.concatenate(lws)
        lw -= lw.max()
        w = np.exp(lw)
        self.last = (st, np.concatenate(mk), np.concatenate(dl), w / w.sum())
        # merge identical hypotheses (sum of their weights)
        H1 = m.H + 1
        key = (((((st["attacked"].astype(np.int64) * 16 + st["kmask"]) * H1 + st["iota"]) * H1
                 + st["sigma"]) * 16 + st["c"]) * 2 + st["harmed"])
        u, first, inv = np.unique(key, return_index=True, return_inverse=True)
        tot = np.bincount(inv, weights=w)
        keep = tot > 0
        self.st = {k: st[k][first][keep] for k in _KEYS}
        self.logw = np.log(tot[keep])
        self._w = None
        self.t_last = t

    def condition_on_quarantine(self, t: int, carrier: str) -> None:
        self.st["c"] = (self.st["c"] & ~np.uint8(BIT[carrier])).astype(np.uint8)


def make_exact_belief(ctx: A.EpisodeContext, delta_hat=None, *, betas: dict | None = None,
                      delta_prior: str = DELTA_PRIOR,
                      p_attack: float = PRIOR_P_ATTACK) -> ExactBelief:
    """api.BeliefFactory for the exact enumerator (same arguments as belief_pf.make_belief)."""
    return ExactBelief(BeliefModel.for_context(ctx, delta_hat, betas=betas,
                                               delta_prior=delta_prior, p_attack=p_attack))
