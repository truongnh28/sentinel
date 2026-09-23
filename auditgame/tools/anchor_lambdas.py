#!/usr/bin/env python3
"""anchor_lambdas.py -- two hand-set weights become one measured ratio.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Part VI class C;
docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md P3.

THE PROBLEM.  L = harm + lambda_Q E[Q_false] + lambda_T E[T_lost] carries two
weights that were assigned, not derived: 0.10 and 0.50.  The main claim of the
paper depends on them -- Sentinel beats B1 in 64/64 cells at lambda_T = 0.5 and
in 22/64 at lambda_T = 0 -- so two numbers nobody measured decide the result.

WHAT CAN BE MEASURED AND WHAT CANNOT.  A false quarantine and a lost task are
both PRICEABLE in this project's own USD scale:

    lambda_Q  one carrier wrongly quarantined = eta_Q(k), measured
    lambda_T  one clean task lost             = the cost of re-running it,
                                                measured on the P2 arm

so their RATIO is a measurement.  What is NOT measurable here is what one harm
event is worth in the same currency -- that is the cost of a poisoned patch
reaching a repository, which this benchmark has no way to price and which
differs by orders of magnitude between projects.

SO THE REDUCTION IS: two free parameters -> one measured ratio plus one
declared scalar.  The scalar is lambda_T, "how many harm events is one lost
clean task worth", and the paper has to declare it rather than measure it.
This script reports the ranking as a function of that one number, so the
declaration can be made against the whole curve instead of at a point.

CONSISTENCY, ENFORCED RATHER THAN ASSUMED.  lambda_Q and eta_Q price THE SAME
EVENT in two places -- the loss function and the budget constraint.  If they
disagree, a policy is charged one price to act and a different one to be judged.
The check is in tests/gate1_integrity/test_cost_provenance.py.

    python3 tools/anchor_lambdas.py --n 20 --seeds 2 > spikes/lambda-anchors.json
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
            "B7 minimax-lp"]

#: The one declared scalar, swept. 0 means "a lost clean task costs nothing",
#: which is the degenerate model A.4 rules out; 2.0 means one lost task hurts
#: twice as much as one poisoned patch landing, which is hard to argue for.
LAMBDA_T_GRID = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


def measured_ratio() -> dict:
    """lambda_Q / lambda_T, from this project's own USD measurements."""
    task = json.loads((pathlib.Path(__file__).resolve().parent.parent
                       / "spikes" / "eta-q.json").read_text())["usd_per_task_p2"]["median"]
    per = {c: costs.eta_q(c) / task for c in CARRIERS}
    return {"usd_per_task": task,
            "per_carrier": {c: round(v, 4) for c, v in per.items()},
            "mean": round(sum(per.values()) / len(per), 4),
            "min": round(min(per.values()), 4),
            "max": round(max(per.values()), 4)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--delta", type=int, default=2)
    ap.add_argument("--detector", default="mid")
    a = ap.parse_args()

    ratio = measured_ratio()
    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    det, ag = detector.Detector.from_setting(a.detector), agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))

    old = {"KAPPA": dict(P.KAPPA), "KAPPA_COMMIT": P.KAPPA_COMMIT,
           "ETA_Q_COST": P.ETA_Q_COST}
    P.KAPPA = dict(costs.KAPPA_USD)
    P.KAPPA_COMMIT = costs.KAPPA_COMMIT_USD
    P.ETA_Q_COST = sum(costs.eta_q(c) for c in CARRIERS) / len(CARRIERS)
    budget = costs.budget_for_table(costs.KAPPA_USD, a.H)
    try:
        cells = {}
        for nm in POLICIES:
            runner.reset_survivor_cache()
            c = runner.worst_case(nm, wfs, (a.delta,), CARRIERS, det, ag,
                                  budget, seeds, a.detector)
            cells[nm] = (c.harm, c.q_false, c.t_lost)
            print(f"{nm:26} harm {c.harm:.3f}  q_false {c.q_false:.2f}  "
                  f"t_lost {c.t_lost:.2f}", file=sys.stderr)
    finally:
        for k, v in old.items():
            setattr(P, k, v)

    # The sweep: one free parameter, with lambda_Q pinned to it by the MEASURED
    # ratio instead of assigned independently.
    curve = []
    for lt in LAMBDA_T_GRID:
        row = {"lambda_T": lt, "lambda_Q": round(ratio["mean"] * lt, 4)}
        L = {nm: metrics.loss(*cells[nm], lambda_Q=ratio["mean"] * lt,
                              lambda_T=lt) for nm in POLICIES}
        row["L"] = {nm: round(v, 4) for nm, v in L.items()}
        row["ranking"] = sorted(POLICIES, key=lambda n: L[n])
        row["winner"] = row["ranking"][0]
        curve.append(row)

    winners = [r["winner"] for r in curve]
    flips = [(curve[i]["lambda_T"], winners[i - 1], winners[i])
             for i in range(1, len(winners)) if winners[i] != winners[i - 1]]

    # The number that was in the code, for contrast: lambda_Q/lambda_T = 0.2,
    # against a measured 0.39..1.87.
    hand = metrics.LAMBDA_Q / metrics.LAMBDA_T

    print(json.dumps({
        "measured_ratio_lambda_Q_over_lambda_T": ratio,
        "hand_set_ratio": hand,
        "hand_set_understates_by": round(ratio["mean"] / hand, 2),
        "cells": {nm: {"harm": round(v[0], 4), "q_false": round(v[1], 4),
                       "t_lost": round(v[2], 4)} for nm, v in cells.items()},
        "sweep": curve,
        "winner_changes_at": flips,
        "reading": ("lambda_Q is NOT swept independently: it is pinned to "
                    "lambda_T by the measured ratio, because both price events "
                    "this project can cost in USD. What stays declared is "
                    "lambda_T -- how many harm events one lost clean task is "
                    "worth -- which no measurement here can supply."),
        "provenance": {
            "scale": "USD, with the MEASURED eta_Q",
            "grid": f"{a.n} workflows, H={a.H}, Delta={a.delta}, "
                    f"detector {a.detector}, seeds {seeds}, B={budget:.6g}",
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
