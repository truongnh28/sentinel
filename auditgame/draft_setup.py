"""draft_setup.py -- the FSE-2027-15 draft's setup in ONE place (model v2, carrier world).

Each constant is copied from the draft (section cited) or is a decision in
docs/preregistration/TIEN-DANG-KY-v2-thiet-lap-draft.md (D cited).  Nothing here is tuned.
"""
from __future__ import annotations

from dataclasses import dataclass

import costs
import metrics

# SS4: A = {none} U {(audit, k, depth)}, cost kappa(k, depth); chi is taken over CARRIERS.
# SS8 prices four audit kinds 0.4/0.9/1.6/4.1 "giving chi = 1.34", so the four kinds ARE the
# four carriers' audits.  D2 fixes the bijection from SS8's own descriptions.
SWEEP_CARRIERS = ("memory", "queue", "skill")    # audited by reading their LIVE state (Thm 4)
COMMIT = "commit"                                # the branch carrier's audit: the patch at t
TARGETS = SWEEP_CARRIERS + (COMMIT,)
TARGET_KAPPA_DRAFT = {"memory": 0.4, "queue": 0.9, "skill": 1.6, "commit": 4.1}   # SS8
STAGE_OF_TARGET = {"memory": "insertion", "queue": "retrieval",                  # D2
                   "skill": "delegation", "commit": "commit"}
DEPTHS = (1, 2, 3)
MAX_DEPTH = max(DEPTHS)

H_RANGE = (6, 14)                  # SS8
N_WORKFLOWS = 100                  # SS8
POOLS = ("verified", "multilingual")   # D8
DEV_SHARE = 0.25                   # D8
DELTAS = (0, 1, 2, 4, 8)           # SS8
CHIS = (0.0, 0.5, 1.34)            # SS8, on the 2*MAD/kbar scale (D2); read where B binds (D4b)
DETECTORS = ("weak", "mid", "strong")
SEEDS = tuple(range(1, 11))        # D24: 10 eval seeds
TUNE_SEEDS = (1, 2)                # D24: dev tuning seeds
N_HELD_OUT = 7                     # SS8
MARGIN_PCT = 15.0                  # SS9.4
HEADLINE_DELTAS = (4, 8)           # "Delta > 2"
HEADLINE_CHI = 1.34
HEADLINE_DETECTOR = "mid"
ZETA = 0.10                        # D9
RHO_PATCH_GRID = (0.0, 0.25, 0.5, 1.0)   # D20
#: D20: chosen by the advisor WITHOUT seeing any v2 number, before Task 10.  None = the
#: primary result is the curve over RHO_PATCH_GRID.
HEADLINE_RHO = None
REF_RHO_FALLBACK = 0.25            # D23
FAMILY_ALPHA = 0.05                # D25: Bonferroni over RHO_PATCH_GRID for the 15% statement
DRIFT_VISIBLE_TASKS = 1            # D6: a drift event is anomalous only in the task it happens
DRIFT_MATCH = 1.0                  # D6: headline match; swept {0, 0.5, 1}

BETA_WORLD = {"memory": costs.BETA_RULE_A["memory"], "skill": costs.BETA_RULE_A["skill"],
              "queue": costs.BETA_RULE_A["queue"], "branch": 0.0}          # D6
LAMBDA_Q = metrics.LAMBDA_Q                                              # prereg lambda
ETA_Q_BAYES = round(LAMBDA_Q / (1.0 + LAMBDA_Q), 4)                      # D11: 0.3543
#: D11: from the naive rule (0: quarantine any firing item) to above the Bayes value, so the
#: FQ cap -- the draft's stated constraint -- and not the grid's edge bounds line 8.
ETA_Q_GRID = (0.0, 0.01, 0.02, 0.05, 0.1, 0.2, ETA_Q_BAYES, 0.5)
FQ_CAP_PCT = 10.0                  # D26: "false quarantine acceptable" (SS4 Objectives)
TAU5_GRID = (0.0, 0.1, 0.2, 0.3, 0.5, 0.7)   # D12: 0 = escalate after every sweep


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


def target_kappa_for_chi(chi: float, base: dict = TARGET_KAPPA_DRAFT) -> dict:
    """lambda = chi / 1.34, so chi = 1.34 IS the draft table (D2)."""
    lam = chi / HEADLINE_CHI
    if lam == 1.0:
        return dict(base)
    kb = kappa_bar(base)
    out = {s: kb + lam * (v - kb) for s, v in base.items()}
    if any(v <= 0 for v in out.values()):
        raise ValueError(f"chi={chi} gives a non-positive cost: {out}")
    return out


def budget_b1(H: int) -> float:
    """D4: B1's bill for every commit at MAX_DEPTH, anchored on the draft table (not on chi)."""
    return H * MAX_DEPTH * TARGET_KAPPA_DRAFT[COMMIT]


@dataclass(frozen=True)
class BudgetSpec:
    """D4.  b1: the anchored B1 bill (headline).  share: value x b1 (EXPLORATORY below 1).
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
