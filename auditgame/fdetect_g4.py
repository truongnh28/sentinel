"""
fdetect_g4.py -- Gate 4: Judge-human agreement verification under pre-registered protocol.
Spec: 261-Master-Proposal-Analysis/TIEN-DANG-KY-m-x-va-F-detect-v2.md Section 6.

G4 Protocol:
1. Minimum sample size: n_G4 = 38, derived from requirement that Clopper-Pearson 95%
   lower bound reaches theta_G4 = 0.75 at expected agreement rate 0.90.
2. Acceptance threshold: theta_G4 = 0.75 on the 95% Clopper-Pearson lower bound.
3. Blind human labels: annotators are blind to judge scores.
4. Pure standard library implementation (no third-party dependencies).
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

#: Pre-registered minimum sample size derived from theta_G4
N_G4: int = 38

#: Pre-registered acceptance threshold on 95% Clopper-Pearson lower bound
THETA_G4: float = 0.75

#: Pre-registered expected agreement rate
EXPECTED_AGREEMENT: float = 0.90


def _binomial_cdf(k: int, n: int, p: float) -> float:
    """Cumulative probability P(X <= k) for Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    total = 0.0
    for i in range(k + 1):
        coeff = math.comb(n, i)
        total += coeff * (p ** i) * ((1.0 - p) ** (n - i))
    return min(1.0, max(0.0, total))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Exact Clopper-Pearson two-sided confidence interval via bisection."""
    if n <= 0:
        raise ValueError("n must be positive")
    if not (0 <= k <= n):
        raise ValueError(f"k must satisfy 0 <= k <= n ({k}/{n})")

    # Lower bound
    if k == 0:
        lo = 0.0
    else:
        target = alpha / 2.0
        low_p, high_p = 0.0, 1.0
        for _ in range(60):
            mid_p = (low_p + high_p) / 2.0
            # P(X >= k | mid_p) = 1 - P(X <= k - 1 | mid_p)
            tail = 1.0 - _binomial_cdf(k - 1, n, mid_p)
            if tail < target:
                low_p = mid_p
            else:
                high_p = mid_p
        lo = (low_p + high_p) / 2.0

    # Upper bound
    if k == n:
        hi = 1.0
    else:
        target = alpha / 2.0
        low_p, high_p = 0.0, 1.0
        for _ in range(60):
            mid_p = (low_p + high_p) / 2.0
            tail = _binomial_cdf(k, n, mid_p)
            if tail < target:
                high_p = mid_p
            else:
                low_p = mid_p
        hi = (low_p + high_p) / 2.0

    return float(lo), float(hi)


def evaluate_g4(human_labels: Sequence[int], judge_labels: Sequence[int],
                threshold: float = THETA_G4, alpha: float = 0.05) -> Dict[str, object]:
    """Evaluate agreement between human labels and judge predictions under G4."""
    if len(human_labels) != len(judge_labels):
        raise ValueError("human_labels and judge_labels must have identical length")
    n = len(human_labels)
    if n == 0:
        raise ValueError("labels sequence cannot be empty")

    agreements = sum(1 for h, j in zip(human_labels, judge_labels) if h == j)
    agreement_rate = agreements / n
    ci_lo, ci_hi = clopper_pearson(agreements, n, alpha=alpha)

    passes = (ci_lo >= threshold) and (n >= N_G4)
    res: Dict[str, object] = {
        "n": n,
        "n_target": N_G4,
        "agreements": agreements,
        "agreement_rate": agreement_rate,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "threshold": threshold,
        "passes": passes,
        "status": "PASS" if passes else "FAIL",
    }
    if n < N_G4:
        res["limitation"] = (
            f"Sample size n={n} is below the pre-registered floor n_G4={N_G4}. "
            f"Report only the interval [{ci_lo:.4f}, {ci_hi:.4f}]; do not declare gate passed."
        )
    return res
