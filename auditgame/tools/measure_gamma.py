"""
tools/measure_gamma.py -- Measure empirical detector operating points (psi, phi, gamma, d')
and cross-reference against declared settings and theoretical break-even d'*.

Evaluates:
  1. Declared operating points: weak, mid, strong.
  2. Empirical operating points measured from the matched case-control corpus across
     Delta in {0, 2, 4} and epsilon in {0.0, 0.2, 0.4, 0.7, 1.0}.
  3. Comparison against empirical break-even d'* (from sweep-v2 / T1).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

# Add auditgame root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis import benign_corpus as B, discriminator as D
import attacks
import detector

_N = NormalDist()

DECLARED_SETTINGS = detector.SETTINGS
BREAK_EVEN_DPRIME = {
    0: {"pinned": None, "following": None},
    1: {"pinned": None, "following": None},
    2: {"pinned": 2.85, "following": 3.00},
    4: {"pinned": 0.95, "following": 1.00},
}


def evaluate_declared_settings() -> dict:
    res = {}
    for name, (psi, phi) in DECLARED_SETTINGS.items():
        det = detector.Detector.from_operating_point(psi, phi)
        # AUC on unit-variance Gaussian: AUC = Phi(d' / sqrt(2))
        auc = _N.cdf(det.d_prime / math.sqrt(2.0))
        res[name] = {
            "psi": round(psi, 4),
            "phi": round(phi, 4),
            "gamma": round(det.gamma, 4),
            "d_prime": round(det.d_prime, 4),
            "tau_det": round(det.tau_det, 4),
            "implied_auc": round(auc, 4),
        }
    return res


def evaluate_empirical_corpus(
    deltas=(0, 2, 4),
    epsilons=(0.0, 0.2, 0.4, 0.7, 1.0),
    n_events: int = 80,
    seeds=D.SPLIT_SEEDS[:10],
    ref_tau_det: float = 1.175,  # mid tau_det
) -> dict:
    pipe = attacks.REGISTRY["matched"]
    res = {}
    for d in deltas:
        res[str(d)] = {}
        for eps in epsilons:
            pos, neg = B.matched_corpus(pipe, d, eps, n_events)
            split_res = D.auc_over_splits(pos, neg, ceiling=0.56, seeds=seeds)
            auc = split_res["auc_mean"]
            auc_hi = split_res["hi_mean"]

            # Convert AUC to d': d' = sqrt(2) * z(AUC)
            bounded_auc = min(0.9999, max(0.5000, auc))
            z = _N.inv_cdf(bounded_auc)
            d_prime = math.sqrt(2.0) * z

            # Operating point at ref_tau_det
            psi = _N.cdf(d_prime - ref_tau_det)
            phi = _N.cdf(-ref_tau_det)
            gamma = psi - phi

            be = BREAK_EVEN_DPRIME.get(d, {})
            be_val = be.get("pinned")
            clears_breakeven = (d_prime >= be_val) if be_val is not None else False

            res[str(d)][str(eps)] = {
                "n_pos": len(pos),
                "n_neg": len(neg),
                "auc_mean": round(auc, 4),
                "auc_hi_mean": round(auc_hi, 4),
                "d_prime": round(d_prime, 4),
                "psi": round(psi, 4),
                "phi": round(phi, 4),
                "gamma": round(gamma, 4),
                "break_even_d_prime": be_val,
                "clears_breakeven": clears_breakeven,
            }
    return res


def main():
    parser = argparse.ArgumentParser(description="Measure Detector Operating Points and Margins")
    parser.add_argument("--n-events", type=int, default=80, help="Event cap for empirical matching")
    parser.add_argument("--json", type=str, help="Output JSON path")
    args = parser.parse_args()

    print("=========================================================================")
    print("1. DECLARED DETECTOR OPERATING POINTS (Manuscript SS8):")
    print(f"{'Setting':<10} | {'psi (TPR)':<10} | {'phi (FPR)':<10} | {'gamma (Margin)':<14} | {'d_prime':<8} | {'Implied AUC':<10}")
    print("-" * 73)
    decl = evaluate_declared_settings()
    for name, v in decl.items():
        print(f"{name:<10} | {v['psi']:<10.4f} | {v['phi']:<10.4f} | {v['gamma']:<14.4f} | {v['d_prime']:<8.4f} | {v['implied_auc']:<10.4f}")

    print("\n=========================================================================")
    print("2. EMPIRICAL DETECTOR OPERATING POINTS (Matched Benign Surface Corpus):")
    header_d = "d'* Break-even"
    print(f"{'Delta':<6} | {'Epsilon':<8} | {'AUC Mean':<9} | {'d_prime':<8} | {'psi':<6} | {'phi':<6} | {'gamma':<7} | {header_d:<15} | {'Clears?'}")
    print("-" * 88)
    emp = evaluate_empirical_corpus(n_events=args.n_events)
    for d, row in emp.items():
        for eps, v in row.items():
            be_str = f"{v['break_even_d_prime']:.2f}" if v['break_even_d_prime'] is not None else "None (null)"
            clr_str = "YES" if v["clears_breakeven"] else "NO"
            print(
                f"{d:<6} | {eps:<8} | {v['auc_mean']:<9.4f} | {v['d_prime']:<8.4f} | "
                f"{v['psi']:<6.3f} | {v['phi']:<6.3f} | {v['gamma']:<7.3f} | {be_str:<15} | {clr_str}"
            )

    full_report = {
        "declared_settings": decl,
        "empirical_corpus": emp,
        "break_even_table": BREAK_EVEN_DPRIME,
    }

    if args.json:
        with open(args.json, "w") as f:
            json.dump(full_report, f, indent=2)
        print(f"\nWrote full report to {args.json}")


if __name__ == "__main__":
    main()
