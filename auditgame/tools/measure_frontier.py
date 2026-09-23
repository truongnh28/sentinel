#!/usr/bin/env python3
"""measure_frontier.py -- does the average/worst-case trade-off hold on the GRID?

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 9;
docs/preregistration/TIEN-DANG-KY-SSG-B-giai-tren-belief.md SS3.

WHAT IS BEING TESTED.  Measured at one cell -- Delta = 2, detector mid, 20
workflows, 2 seeds -- ranking policies by worst-case L came out as very nearly
the REVERSE of ranking them by regret, and SSG-B, a policy built specifically to
escape that, landed on the line instead of off it.  If that inversion is a
property of the problem it has to survive the grid.  If it holds only at one
(Delta, detector) it is a coincidence of that cell and must not be reported as a
law.

THE STATISTIC IS SPEARMAN, per cell, between rank-by-L and rank-by-regret.
-1.0 is a perfect frontier; 0 is no relationship.  Reported per cell and NOT
pooled, for the reason experiment.py gives at the top of its own docstring: a
pooled number averages the regime where a claim holds with the regime where it
does not.

THE TWO NUMBERS ARE NOT THE SAME KIND OF THING, and the difference is the point.
    L       worst case over the attacker class at THIS Delta -- average-case
            quality in the sense that the policy's own behaviour is averaged
            over workflows and seeds.
    regret  distance to the minimax value over the WHOLE declared class --
            what the policy gives up to an attacker who reads it.

    python3 tools/measure_frontier.py --n 100 --seeds 3 > spikes/frontier.json
"""
from __future__ import annotations
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent
import costs
import detector
import experiment
import metrics
import policies as P
import runner
from core import CARRIERS

POLICIES = ["B1 audit-at-commit", "B5 risk-score", "B6 two-stage",
            "Sentinel", "SentinelW window-belief", "SSG-G guarded",
            "SSG-B belief-weighted", "B7 minimax-lp"]


def spearman(a: dict, b: dict) -> float:
    """Rank correlation between two scorings of the same policies."""
    names = sorted(a)
    ra = {n: i for i, n in enumerate(sorted(names, key=lambda x: a[x]), 1)}
    rb = {n: i for i, n in enumerate(sorted(names, key=lambda x: b[x]), 1)}
    n = len(names)
    d2 = sum((ra[x] - rb[x]) ** 2 for x in names)
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--lambda-t", type=float, default=0.5)
    a = ap.parse_args()

    # lambda_Q is PINNED to lambda_T by the measured ratio, never swept beside
    # it -- see tools/anchor_lambdas.py for why the two are one measurement.
    ratio = json.loads((pathlib.Path(__file__).resolve().parent.parent / "spikes"
                        / "lambda-anchors.json").read_text()
                       )["measured_ratio_lambda_Q_over_lambda_T"]["mean"]
    lam_q = ratio * a.lambda_t

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    seeds = tuple(range(1, a.seeds + 1))
    ag = agent.MockAgent()

    old = {"KAPPA": dict(P.KAPPA), "KAPPA_COMMIT": P.KAPPA_COMMIT,
           "ETA_Q_COST": P.ETA_Q_COST}
    P.KAPPA = dict(costs.KAPPA_USD)
    P.KAPPA_COMMIT = costs.KAPPA_COMMIT_USD
    P.ETA_Q_COST = sum(costs.eta_q(c) for c in CARRIERS) / len(CARRIERS)
    budget = costs.budget_for_table(costs.KAPPA_USD, a.H)

    cells = {}
    try:
        for det_name in ("weak", "mid", "strong"):
            det = detector.Detector.from_setting(det_name)
            for d in (0, 1, 2, 4):
                L, harm = {}, {}
                for nm in POLICIES:
                    runner.reset_survivor_cache()
                    c = runner.worst_case(nm, wfs, (d,), CARRIERS, det, ag,
                                          budget, seeds, det_name)
                    L[nm] = metrics.loss(c.harm, c.q_false, c.t_lost,
                                         lambda_Q=lam_q, lambda_T=a.lambda_t)
                    harm[nm] = c.harm
                # Regret against the minimax value of THIS cell's policy set:
                # the best any mixture over these policies could guarantee.
                # Computed from the same L values so the two axes cannot drift.
                v_star = min(L.values())
                regret = {nm: L[nm] - v_star for nm in POLICIES}
                cells[f"{det_name}/D{d}"] = {
                    "L": {n: round(v, 4) for n, v in L.items()},
                    "harm": {n: round(v, 4) for n, v in harm.items()},
                    "best": min(L, key=L.get),
                    "worst": max(L, key=L.get),
                }
                print(f"{det_name:>6}/D{d}  best={min(L, key=L.get)}",
                      file=sys.stderr)
    finally:
        for k, v in old.items():
            setattr(P, k, v)

    # The frontier question needs regret measured against the DECLARED attacker
    # class, not re-derived from L -- so it is read from the exploitability run
    # rather than recomputed here, and the cell list says which run.
    expl = json.loads((pathlib.Path(__file__).resolve().parent.parent / "spikes"
                       / "exploitability-ssgb.json").read_text())
    reg = {n: v["regret"] for n, v in expl["grid"][3]["policies"].items()}

    rho = {}
    for key, cell in cells.items():
        common = [n for n in POLICIES if n in reg]
        rho[key] = round(spearman({n: cell["L"][n] for n in common},
                                  {n: reg[n] for n in common}), 3)

    vals = list(rho.values())
    print(json.dumps({
        "lambda_T": a.lambda_t, "lambda_Q": round(lam_q, 4),
        "ratio_source": "measured, spikes/lambda-anchors.json",
        "cells": cells,
        "regret": {n: round(v, 4) for n, v in reg.items()},
        "regret_source": "spikes/exploitability-ssgb.json, lambda cell 3",
        "spearman_L_vs_regret": rho,
        "summary": {
            "cells": len(vals),
            "mean": round(sum(vals) / len(vals), 3),
            "min": min(vals), "max": max(vals),
            "cells_with_strong_inversion": sum(1 for v in vals if v <= -0.5),
        },
        "reading": ("Spearman near -1 in a cell means ranking by L is the "
                    "reverse of ranking by regret there -- the frontier. Near 0 "
                    "means no trade-off in that cell. Reported per cell and not "
                    "pooled: a mean would average a regime where the law holds "
                    "with one where it does not."),
        "caveat": ("regret is measured ONCE, on the declared attacker class "
                   "over deltas (0,2,4), so it does not vary by cell. The "
                   "correlation therefore asks whether each cell's L ordering "
                   "matches one fixed robustness ordering -- which is the "
                   "question -- not whether both move together."),
        "provenance": {
            "grid": f"{a.n} workflows, H={a.H}, seeds {seeds}, USD scale, "
                    f"measured eta_Q, B={budget:.6g}",
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
