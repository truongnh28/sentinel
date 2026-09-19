"""
tools/evaluate_chi_variants.py -- Compare three formulations of the carrier heterogeneity axis chi.

Variant A: Mean-anchored (sum_k kappa_k is constant across chi).
Variant B: Min-anchored (kappa_lo is fixed, sum_k kappa_k increases with chi).
Variant C: Carrier-dependent commit audit v(k, t) where commit checks inspect specific carriers.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add Sentinel root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import smoke_repro as S


def run_variant_a(chis, deltas, cfg):
    K, H, psi, kc = cfg["K"], cfg["H"], cfg["psi"], cfg["kappa_commit"]
    B = S.budget(cfg)
    res = {}
    for chi in chis:
        kap = S.carrier_costs(chi, K, {"het_model": "mean", "kappa_bar": cfg["kappa_bar"]})
        res[chi] = {}
        for d in deltas:
            u, v = S.p_minimax(K, H, B, kap, kc, delta=d, psi=psi)
            h_mm = S.worst_case(u, v, K, H, d, psi)
            u_c, v_c = S.p_commit(K, H, B, kap, kc)
            h_c = S.worst_case(u_c, v_c, K, H, d, psi)
            gain = (h_c - h_mm) / h_c * 100.0 if h_c > 0 else 0.0
            res[chi][d] = {"harm_mm": h_mm, "harm_commit": h_c, "gain_pct": gain, "sum_kappa": sum(kap)}
    return res


def run_variant_b(chis, deltas, cfg):
    K, H, psi, kc = cfg["K"], cfg["H"], cfg["psi"], cfg["kappa_commit"]
    B = S.budget(cfg)
    res = {}
    for chi in chis:
        kap = S.carrier_costs(chi, K, {"het_model": "min", "kappa_bar": cfg["kappa_bar"]})
        res[chi] = {}
        for d in deltas:
            u, v = S.p_minimax(K, H, B, kap, kc, delta=d, psi=psi)
            h_mm = S.worst_case(u, v, K, H, d, psi)
            u_c, v_c = S.p_commit(K, H, B, kap, kc)
            h_c = S.worst_case(u_c, v_c, K, H, d, psi)
            gain = (h_c - h_mm) / h_c * 100.0 if h_c > 0 else 0.0
            res[chi][d] = {"harm_mm": h_mm, "harm_commit": h_c, "gain_pct": gain, "sum_kappa": sum(kap)}
    return res


def run_variant_c(chis, deltas, cfg):
    K, H, psi, kc = cfg["K"], cfg["H"], cfg["psi"], cfg["kappa_commit"]
    B = S.budget(cfg)

    def p_minimax_c(kap, delta):
        nU, nV = K * H, K * H
        n = nU + nV + 1
        im = n - 1
        c = [0.0] * n
        c[im] = 1.0
        A, b = [], []
        for (k, i, s) in S.attacker_actions(K, H, delta):
            row = [0.0] * n
            for t in range(i, s):
                row[k * H + t] = -1.0
            row[nU + k * H + s] += -1.0
            row[im] = 1.0
            A.append(row)
            b.append(0.0)
        row = [0.0] * n
        for k in range(K):
            for t in range(H):
                row[k * H + t] = kap[k]
                row[nU + k * H + t] = kc
        A.append(row)
        b.append(B)
        for j in range(n):
            row = [0.0] * n
            row[j] = 1.0
            A.append(row)
            b.append(1.0)
        x, _ = S.simplex_max(c, A, b)
        m = x[im]
        return 1.0 - psi * min(1.0, m)

    def p_commit_c():
        c = min(1.0, B / (kc * H * K))
        return 1.0 - psi * c

    h_c = p_commit_c()
    res = {}
    for chi in chis:
        kap = S.carrier_costs(chi, K, {"het_model": "mean", "kappa_bar": cfg["kappa_bar"]})
        res[chi] = {}
        for d in deltas:
            h_mm = p_minimax_c(kap, d)
            gain = (h_c - h_mm) / h_c * 100.0 if h_c > 0 else 0.0
            res[chi][d] = {"harm_mm": h_mm, "harm_commit": h_c, "gain_pct": gain, "sum_kappa": sum(kap)}
    return res


def main():
    parser = argparse.ArgumentParser(description="Evaluate Chi Formulations")
    parser.add_argument("--json", type=str, help="Output JSON path")
    args = parser.parse_args()

    chis = (0.00, 0.50, 1.00, 1.34)
    deltas = (0, 1, 2, 4)
    cfg = S.CFG

    out = {
        "variant_a_mean": run_variant_a(chis, deltas, cfg),
        "variant_b_min": run_variant_b(chis, deltas, cfg),
        "variant_c_carrier_commit": run_variant_c(chis, deltas, cfg),
    }

    if args.json:
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2)
        print(f"Wrote results to {args.json}")


if __name__ == "__main__":
    main()
