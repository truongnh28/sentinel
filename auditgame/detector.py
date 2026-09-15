"""
detector.py -- ONE detector shared by EVERY system.

This is a methodological constraint, not an implementation detail: if each system
had its own detector we would be measuring DETECTION QUALITY, while the variable
under study is ALLOCATION.

N1 (spec: eval/SPEC-Tang-Do-va-Test.md SS2.1-2.2) -- the old version had two
fatal defects:

    fires(score, item_is_poisoned)  ->  score > 1 - (psi if poisoned else phi)

  1. it READ GROUND TRUTH, so I2 held only by code-review discipline;
  2. two different thresholds keyed on the true label mean the operating point
     is NOT on the ROC curve of raw_score.  Measured: declared (0.75, 0.20) but
     realised (0.985, 0.0068), d' = 4.63 instead of 1.52 -- off by ~22x, and all
     three settings collapsed into near-perfect detectors 1.4 percentage points
     of TPR apart.

New version: ONE distribution, ONE threshold, operating point DERIVED rather than
declared separately.

    s(x) ~ N(d' * 1[x poisoned], 1)      fires(s) <=> s > tau_det
    psi = Phi(d' - tau_det)              phi = Phi(-tau_det)

Inverting for the manuscript's three SS8 settings:

    d' = z(psi) - z(phi)                 tau_det = z(1 - phi)

I7 now holds BY CONSTRUCTION, and fires() has no parameter through which ground
truth could be passed.

NOTE: tau_det is an ITEM-level threshold on the RAW score.  It is a DIFFERENT
object from tau_sel (carrier-level, on the posterior in [0,1], read from a frozen
table) in scoring.py.
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from statistics import NormalDist

from core import seed_of

_N = NormalDist()

# The manuscript's three (psi, phi) settings, SS8.
SETTINGS = {"weak": (0.75, 0.20), "mid": (0.85, 0.12), "strong": (0.92, 0.06)}


def operating_point(psi: float, phi: float) -> tuple[float, float]:
    """(psi, phi) -> (d', tau_det).  d' = z(psi) - z(phi), tau_det = z(1-phi)."""
    return _N.inv_cdf(psi) - _N.inv_cdf(phi), _N.inv_cdf(1.0 - phi)


@dataclass
class Detector:
    """Detector parameterised by SEPARABILITY and THRESHOLD, not by a loose
    (psi, phi) pair."""
    d_prime: float
    tau_det: float

    @classmethod
    def from_operating_point(cls, psi: float, phi: float) -> "Detector":
        return cls(*operating_point(psi, phi))

    @classmethod
    def from_setting(cls, name: str) -> "Detector":
        return cls.from_operating_point(*SETTINGS[name])

    # ---- operating point is DERIVED, never declared => I7 holds structurally --
    @property
    def psi(self) -> float:
        return _N.cdf(self.d_prime - self.tau_det)

    @property
    def phi(self) -> float:
        return _N.cdf(-self.tau_det)

    def score(self, item, now: int, seed: int) -> float:
        """Raw score ~ N(d' if poisoned else 0, sd 1).

        Seeded by (seed, item_id), and item_id is CONTENT-DERIVED (core.Item), so
        the same logical item always scores the same -- including across the
        clean and injected arms of the paired design.  With the old global
        counter, 0 of 9 clean notes kept their score.
        """
        r = random.Random(seed_of(seed, item.item_id))
        return r.gauss(self.d_prime if item.poisoned else 0.0, 1.0)

    def score_patch(self, has_marker: bool, task_id: str, seed: int) -> float:
        """Score of the PATCH, for audit-at-commit (D2).

        The old code scored `o.writes[0]` -- always the CLEAN note the agent had
        just written -- and hard-coded item_is_poisoned=True.  That made B1
        audit-at-commit, the BASELINE OF THE 15% GATE, fire with the probability
        of an unrelated object.  Here we score the thing actually being audited.
        """
        r = random.Random(seed_of(seed, "patch", task_id))
        return r.gauss(self.d_prime if has_marker else 0.0, 1.0)

    def fires(self, score: float) -> bool:
        """PURE threshold.  No parameter through which ground truth can enter."""
        return score > self.tau_det
