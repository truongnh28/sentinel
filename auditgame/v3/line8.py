"""v3/line8.py -- Algorithm 1 lines 8-9: quarantine the highest-posterior carrier (T12).

Draft Algorithm 1:
    8: if Pr[poisoned | b_{t+1}] > tau and expected harm > eta_Q then
    9:     quarantine the highest-posterior carrier

WHAT IS READ.  Only the belief, through the frozen api.BeliefAPI, AFTER line 7 has taken
o_t in (b_{t+1}):
    Pr[poisoned | b_{t+1}]   belief.p_poisoned()
    expected harm            belief.expected_harm()  (Pr[the poison reaches harm by the
                             horizon | b_{t+1}], api.BeliefAPI)
    highest-posterior        argmax_k belief.carrier_mass()[k]; ties go to the first carrier
                             in config.CARRIERS order (declared, deterministic).
Both comparisons are STRICT, as the draft writes them: at p = tau or harm = eta_Q nothing
is quarantined.

WHAT IS DONE.  `quarantine(t, belief)` returns the carrier and conditions the belief on its
removal (api.BeliefAPI.condition_on_quarantine: c[k] = 0); the runner removes EVERY live
item of memory / skill / queue, and only the poisoned lineage of the branch (O7, author
decision 27/09; v3/runner.py Episode.removed_by_quarantine).  tau and eta_Q are tuned per rho
on dev (T18, C6); nothing here has a default for them.

Stdlib only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from v3 import api as A
from v3 import config as C


def highest_posterior_carrier(belief: A.BeliefAPI) -> str:
    """argmax_k Pr[c[k] = 1 | b]; ties go to the first carrier in config.CARRIERS order."""
    mass = belief.carrier_mass()
    missing = [k for k in C.CARRIERS if k not in mass]
    if missing:
        raise ValueError(f"carrier_mass() lacks {missing}: api.BeliefAPI returns every carrier")
    return max(C.CARRIERS, key=lambda k: (float(mass[k]), -C.CARRIERS.index(k)))


@dataclass(frozen=True)
class Line8:
    """Lines 8-9 with the tuned (tau, eta_Q) of one rho (T18)."""
    tau: float
    eta_q: float

    def __post_init__(self):
        for name in ("tau", "eta_q"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(v):
                raise ValueError(f"{name}={v!r} is not a number")
        if not 0.0 <= self.tau <= 1.0:
            raise ValueError(f"tau={self.tau} is not a probability")

    def fires(self, belief: A.BeliefAPI) -> bool:
        """Line 8: Pr[poisoned | b_{t+1}] > tau and expected harm > eta_Q (strict)."""
        return (float(belief.p_poisoned()) > self.tau
                and float(belief.expected_harm()) > self.eta_q)

    def decide(self, belief: A.BeliefAPI) -> str | None:
        """The carrier line 9 quarantines, or None.  Reads only; see `quarantine`."""
        return highest_posterior_carrier(belief) if self.fires(belief) else None

    def quarantine(self, t: int, belief: A.BeliefAPI, log: list | None = None) -> str | None:
        """Lines 8-9 at task t: the carrier to remove (None = continue).  When it fires the
        belief is conditioned on the removal, so b_{t+1} already has c[k] = 0."""
        p, h = float(belief.p_poisoned()), float(belief.expected_harm())
        k = self.decide(belief)
        if k is not None:
            belief.condition_on_quarantine(t, k)
        if log is not None:
            log.append({"t": t, "line": 8, "p_poisoned": round(p, 12),
                        "expected_harm": round(h, 12), "tau": self.tau, "eta_q": self.eta_q,
                        "quarantine": k})
        return k
