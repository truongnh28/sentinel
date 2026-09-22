#!/usr/bin/env python3
"""
measure_band_vs_n.py -- Measure the noise band width vs n curve across salts.
Generates data for docs/reports/dai-theo-n.md.
"""
import json
import time
from analysis import band_vs_n, gate2_v2

def main():
    salts = list(gate2_v2.SALT_FAMILY)[:8]  # >= 8 salts as required
    n_grid = [100, 200, 400, 900, 1800]
    results = []

    print(f"Measuring band curve over {len(salts)} salts across n in {n_grid}...")
    t0 = time.time()
    for n in n_grid:
        tn0 = time.time()
        b = band_vs_n.band_width(n, salts, delta=0)
        dt = time.time() - tn0
        print(f"  n = {n:4d} ({dt:.1f}s): lo = {b['lo']:.4f}, hi = {b['hi']:.4f}, "
              f"width = {b['width']:.4f}, median = {b['median']:.4f}")
        results.append(b)

    # Check resolving_n
    try:
        rn = band_vs_n.resolving_n(n_grid, salts, ceiling=0.56, delta=0)
        print(f"\nresolving_n(ceiling=0.56) = {rn}")
    except band_vs_n.Unresolved as e:
        print(f"\nresolving_n(ceiling=0.56) raised Unresolved: {e}")
        rn = None

    data = {
        "date": "2026-09-19",
        "salts": salts,
        "n_grid": n_grid,
        "delta": 0,
        "ceiling": 0.56,
        "resolving_n": rn,
        "curve": results,
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    with open("spikes/band_curve.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Wrote spikes/band_curve.json successfully!")

if __name__ == "__main__":
    main()
