#!/usr/bin/env python3
"""gamma_grid.py -- the draft's three detector levels as their own grid, and a
test of the 1/gamma^2 claim its theory makes.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md sections 9.1-9.2.

TWO THINGS, AND THE SECOND IS THE POINT.

1. The three operating points are run as a grid indexed by gamma = psi - phi
   rather than by the names weak/mid/strong, with d' and tau_det derived and
   checked against the table the manuscript derives them in
   (weak d = 1.52, mid 2.21, strong 2.96).  Verified: our Detector reproduces
   all three to two decimals, so the levels in the code ARE the draft's levels.

2. The manuscript states a Chernoff-style bound: distinguishing an infected
   carrier from a clean one needs n >~ log(1/alpha)/gamma^2 observations, glossed
   as "a detector twice as good needs less than four times fewer observations",
   and used to argue that improving the detector beats improving allocation.

   That is a falsifiable prediction about THIS benchmark, and it had never been
   checked.  If it holds, the audit budget needed to reach a fixed harm level
   should scale as 1/gamma^2 across the three levels:

       gamma       0.55    0.73    0.86
       1/gamma^2   3.31    1.88    1.35
       ratio vs strong  2.45    1.39    1.00

   So reaching the same harm at `weak` should cost about 2.45x the budget it
   costs at `strong`.  We measure the budget share at which a policy first
   reaches a target harm, at each level, and report the ratios beside the
   predicted ones.

    python3 tools/gamma_grid.py --n 40 --seeds 3 > spikes/gamma-grid.json
"""
from __future__ import annotations
import argparse, datetime, json, math, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent, costs, detector, experiment, policies as P, runner
from core import CARRIERS

#: The manuscript's own derivation, section 9.1, to check the code against.
DRAFT_TABLE = {"weak": {"t": 0.84, "d": 1.52, "gamma": 0.55},
               "mid": {"t": 1.17, "d": 2.21, "gamma": 0.73},
               "strong": {"t": 1.55, "d": 2.96, "gamma": 0.86}}

#: Budget shares, dense enough to locate a crossing rather than bracket it.
SHARES = (0.16, 0.25, 0.3205, 0.40, 0.50, 0.60, 0.75, 0.90, 1.0)

POLICIES = ["SSG-full receding", "B1 audit-at-commit"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--delta", type=int, default=4)
    ap.add_argument("--target-harm", type=float, default=0.50)
    a = ap.parse_args()

    # ---- 1. the operating points, derived and checked -------------------
    levels = {}
    for name, (psi, phi) in detector.SETTINGS.items():
        det = detector.Detector.from_setting(name)
        d_ref = DRAFT_TABLE[name]
        levels[name] = {
            "psi": psi, "phi": phi,
            "gamma": round(psi - phi, 4),
            "d_prime": round(det.d_prime, 4),
            "tau_det": round(det.tau_det, 4),
            "draft_d": d_ref["d"], "draft_gamma": d_ref["gamma"],
            "matches_draft": (abs(det.d_prime - d_ref["d"]) < 0.02
                              and abs(det.tau_det - d_ref["t"]) < 0.02
                              and abs((psi - phi) - d_ref["gamma"]) < 0.005),
            "inv_gamma_sq": round(1.0 / (psi - phi) ** 2, 4),
        }

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    ag = agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))
    old = costs.install(P)
    total = sum(P.KAPPA.values())
    try:
        curves = {}
        for name in ("weak", "mid", "strong"):
            det = detector.Detector.from_setting(name)
            curves[name] = []
            for share in SHARES:
                budget = share * a.H * total
                row = {"share": share}
                for nm in POLICIES:
                    runner.reset_survivor_cache()
                    c = runner.worst_case(nm, wfs, (a.delta,), CARRIERS, det, ag,
                                          budget, seeds, name)
                    row[nm] = round(c.harm, 4)
                curves[name].append(row)
                print(f"{name:7} share={share:<7} "
                      + "  ".join(f"{nm.split()[0]}:{row[nm]:.3f}" for nm in POLICIES),
                      file=sys.stderr)
    finally:
        costs.restore(P, old)

    # ---- 2. budget to reach the target harm, by linear interpolation ----
    pol = POLICIES[0]

    def crossing(name):
        pts = [(r["share"], r[pol]) for r in curves[name]]
        for (s0, h0), (s1, h1) in zip(pts, pts[1:]):
            if h0 > a.target_harm >= h1:          # harm falls as budget rises
                if h0 == h1:
                    return s1
                return s0 + (h0 - a.target_harm) * (s1 - s0) / (h0 - h1)
        return None

    cross = {n: crossing(n) for n in ("weak", "mid", "strong")}
    ref = cross["strong"]
    check = {}
    if ref:
        for n in ("weak", "mid", "strong"):
            if cross[n] is None:
                check[n] = {"measured_ratio": None,
                            "note": "never reaches the target in the swept range"}
                continue
            pred = levels[n]["inv_gamma_sq"] / levels["strong"]["inv_gamma_sq"]
            check[n] = {"budget_share_to_target": round(cross[n], 4),
                        "measured_ratio_vs_strong": round(cross[n] / ref, 3),
                        "predicted_ratio_1_over_gamma_sq": round(pred, 3),
                        "measured_over_predicted": round((cross[n] / ref) / pred, 3)}

    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "setup": {"n": a.n, "H": a.H, "seeds": a.seeds, "delta": a.delta,
                  "scale": "usd", "target_harm": a.target_harm,
                  "policy": pol, "shares": list(SHARES)},
        "operating_points": levels,
        "code_matches_draft_derivation": all(v["matches_draft"]
                                             for v in levels.values()),
        "curves": curves,
        "budget_to_reach_target": cross,
        "one_over_gamma_squared_check": check,
    }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
