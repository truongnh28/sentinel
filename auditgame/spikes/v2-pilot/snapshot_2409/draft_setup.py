"""draft_setup.py -- the FSE-2027-15 draft's setup in ONE place (model v2).

Each constant is copied from the draft (section cited) or is a decision in
docs/preregistration/TIEN-DANG-KY-v2-thiet-lap-draft.md (D cited).  Nothing here is tuned.
"""
from __future__ import annotations

from dataclasses import dataclass

import costs
import metrics
from core import seed_of

STAGES = ("insertion", "retrieval", "delegation", "commit")        # SS8
STAGE_KAPPA_DRAFT = {"insertion": 0.4, "retrieval": 0.9,          # Table 1, SS7
                     "delegation": 1.6, "commit": 4.1}
DEPTHS = (1, 2, 3)
MAX_DEPTH = max(DEPTHS)

H_RANGE = (6, 14)                  # SS8
N_WORKFLOWS = 100                  # SS8; Verified + Multilingual give 107 under reuse <= 2 (D8)
POOLS = ("verified", "multilingual")   # D8
DEV_SHARE = 0.25                   # D8
DELTAS = (0, 1, 2, 4, 8)           # SS8
CHIS = (0.0, 0.5, 1.34)            # SS8, on the 2*MAD/kbar scale (D2)
DETECTORS = ("weak", "mid", "strong")
SEEDS = (1, 2, 3)                  # SS9.4
N_HELD_OUT = 7                     # SS8
MARGIN_PCT = 15.0                  # SS9.4
HEADLINE_DELTAS = (4, 8)           # "Delta > 2"
HEADLINE_CHI = 1.34
HEADLINE_DETECTOR = "mid"
ACTION_MODES = ("single", "multi")  # D1
RHO_PATCH_GRID = (0.0, 0.25, 0.5, 1.0)   # D20: exposure of a DELEGATED patch; 1.0 = v1 / D4c
#: D20: the headline rho_patch, chosen by the advisor WITHOUT seeing any v2 number and
#: written into the prereg before Task 10.  None = no headline cell; the primary result
#: is the gain-vs-rho curve and the 15% statement is made per rho.
HEADLINE_RHO = None
#: D23: used only when HEADLINE_RHO is None, and only to decide which rho keeps all three
#: detectors under cut (e).  Chosen from STRUCTURE, before any number: rho = 0 makes a
#: delegated patch invisible and rho = 1 is the D4c floor, both degenerate by construction;
#: of the two interior points, 0.25 is the closer reading of the draft's "cannot distinguish".
REF_RHO_FALLBACK = 0.25
N_SLOTS_MAX = len(STAGES)
ZETA = 0.10                        # D9

BETA_WORLD = {"memory": costs.BETA_RULE_A["memory"], "skill": costs.BETA_RULE_A["skill"],
              "queue": costs.BETA_RULE_A["queue"], "branch": 0.0}          # D6
LAMBDA_Q = metrics.LAMBDA_Q                                              # prereg lambda
ETA_Q_PRICE_OVER_KBAR = costs.ETA_Q_OVER_KAPPA   # 61.5 -- sensitivity row only (D11)

CARRIER_STAGE = {"memory": "retrieval", "skill": "delegation",
                 "queue": "delegation", "branch": "commit"}


def kappa_bar(kappa: dict) -> float:
    return sum(kappa.values()) / len(kappa)


def chi_reported(kappa: dict) -> float:
    """D2: 2 * mean absolute deviation / kbar -- the measure that gives the draft's 1.34."""
    kb = kappa_bar(kappa)
    return 2 * sum(abs(v - kb) for v in kappa.values()) / len(kappa) / kb


def chi_range(kappa: dict) -> float:
    """Draft SS4's printed formula, max |k - k'| / kbar -- Theorem 4's chi."""
    v = list(kappa.values())
    return (max(v) - min(v)) / kappa_bar(kappa)


def stage_kappa_for_chi(chi: float, base: dict = STAGE_KAPPA_DRAFT) -> dict:
    """lambda = chi / 1.34, so the headline cell IS the draft table (D2)."""
    lam = chi / HEADLINE_CHI
    if lam == 1.0:
        return dict(base)
    kb = kappa_bar(base)
    out = {s: kb + lam * (v - kb) for s, v in base.items()}
    if any(v <= 0 for v in out.values()):
        raise ValueError(f"chi={chi} gives a non-positive stage cost: {out}")
    return out


def budget_b1(H: int) -> float:
    """D4: B1's bill for every commit at MAX_DEPTH, ANCHORED on the draft table.

    Held fixed across chi cells: the chi interpolation keeps kbar fixed, so a fixed B
    keeps B/(H*sum kappa) fixed and chi moves only relative prices.  Letting B follow
    each cell's kappa_commit would confound chi with the budget level (D4b).
    """
    return H * MAX_DEPTH * STAGE_KAPPA_DRAFT["commit"]


@dataclass(frozen=True)
class BudgetSpec:
    """D4.  b1: anchored B1 bill (headline).  share: value x b1 (EXPLORATORY below 1).
    absolute: value per task, x H."""
    mode: str = "b1"
    value: float = 1.0

    def budget(self, H: int) -> float:
        if self.mode == "b1":
            return budget_b1(H)
        if self.mode == "share":
            return self.value * budget_b1(H)
        if self.mode == "absolute":
            return self.value * H
        raise ValueError(f"unknown budget mode {self.mode!r}")

    def label(self) -> str:
        return "b1" if self.mode == "b1" else f"{self.mode}-{self.value:g}"


def eta_q_threshold(mult: float = 1.0) -> float:
    """D11: Algorithm 1 line 8's "expected harm > eta_Q", with expected harm = p_k * h
    and h = 1 (binary oracle).  Quarantining carrier k is Bayes-worth-it iff
    p_k > lambda_Q * (1 - p_k), i.e. p_k > lambda_Q / (1 + lambda_Q).  `mult` is the
    SS11 sweep (< 1: more aggressive than Bayes, > 1: more cautious).

    The tau_Q condition on p_attack is a separate gate and plays no part here:
    p_k <= p_attack, so a bound on p_attack says nothing about p_k.
    """
    return mult * LAMBDA_Q / (1.0 + LAMBDA_Q)


def n_slots(mode: str, wf_id: str, t: int, seed: int) -> int:
    """D1: audit slots at task t -- an ENVIRONMENT draw, identical for every policy."""
    if mode == "single":
        return 1
    if mode == "multi":
        return 1 + seed_of(wf_id, t, seed, "slots") % N_SLOTS_MAX
    if mode == "all":                        # diagnostic only (tests)
        return N_SLOTS_MAX
    raise ValueError(f"unknown action mode {mode!r}")
