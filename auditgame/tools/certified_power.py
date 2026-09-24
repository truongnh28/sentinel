#!/usr/bin/env python3
"""certified_power.py -- is the certified region BELOW the 15% gate, or just quiet?

Spec: docs/preregistration/cong-v2-chot.md; docs/thesis/eval/SPEC-AuditGame-SE.md SS15.

THE QUESTION THIS ANSWERS.  Gate v2 certifies Delta in {0, 2} and refuses
Delta = 4 (AUC 0.587, 1/20 splits; the permutation test agrees the cell is
genuinely separable, p = 0.010).  The only two grid cells that clear this
project's 15% gate sit at Delta = 4.  Inside the certified region the best gain
anywhere is +10.7%.

+10.7% against a 15% bar is not a verdict until it carries an interval.  At
N = 40 the interval may well straddle 15, in which case the honest statement is
"underpowered", not "fails".  This script settles which.

THE STATISTIC IS THE RELATIVE GAIN, not Delta-harm.  runner.bootstrap_paired
gives a CI on the absolute difference, and the gate is stated as a percentage of
B1, so the resample has to carry the ratio through: for each bootstrap draw of
workflows, recompute mean(B1) and mean(policy) on THAT draw and take the gain of
the two means.  Taking a CI on the numerator and dividing by a fixed denominator
understates the spread.

RESAMPLED BY WORKFLOW, never by case -- cases inside a workflow share a task
chain and a clean-run outcome, so by-case resampling invents precision.

    python3 tools/certified_power.py --n 100 --seeds 3 > spikes/certified-power.json
"""
from __future__ import annotations
import argparse
import datetime
import json
import pathlib
import random
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent
import costs
import detector
import experiment
import policies as P
import runner
from core import CARRIERS

#: Gate v2's verdict per Delta, from docs/preregistration/cong-v2-chot.md.
#: Delta = 1 was never put through the gate, so it is neither certified nor
#: refused -- and saying "untested" is not the same as saying "red".
GATE = {0: "certified", 1: "untested", 2: "certified", 4: "refused"}

BASELINE = "B1 audit-at-commit"
CANDIDATES = ["SSG-full receding", "SSG-G guarded", "SSG-GU guarded upstream",
              "B7U minimax-lp upstream", "SentinelW window-belief", "Sentinel"]

#: The project's own bar, from the proposal: a 15% reduction in worst-case harm.
GATE_PCT = 15.0


def gain_ci(b1_per_wf, pol_per_wf, n_boot=10000, seed=2026):
    """Point estimate and CI95 of the RELATIVE gain, resampled by workflow."""
    n = len(b1_per_wf)
    if n == 0 or len(pol_per_wf) != n:
        return None
    mb = sum(b1_per_wf) / n
    point = 100.0 * (mb - sum(pol_per_wf) / n) / mb if mb else float("nan")
    rng = random.Random(seed)
    draws = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        a = sum(b1_per_wf[i] for i in idx) / n
        b = sum(pol_per_wf[i] for i in idx) / n
        if a > 0:
            draws.append(100.0 * (a - b) / a)
    draws.sort()
    if not draws:
        return None
    return {"gain": round(point, 2),
            "lo": round(draws[int(0.025 * len(draws))], 2),
            "hi": round(draws[int(0.975 * len(draws))], 2),
            "n_workflows": n}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--deltas", type=int, nargs="+", default=[0, 2, 4])
    ap.add_argument("--budget-share", type=float, default=None,
                    help="B/(H*sum kappa). Default: the published 0.3205 via "
                         "costs.budget_for_table. Any other value is computed "
                         "exactly as tools/sweep_budget.py does (share*H*sum kappa), "
                         "so the two tools report the same cell (README issue #17).")
    ap.add_argument("--candidates", nargs="+", default=CANDIDATES,
                    help="policies compared against B1. Default: the published set.")
    a = ap.parse_args()

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    ag = agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))
    old = costs.install(P)                       # the declared operating scale
    budget = (costs.budget_for_table(P.KAPPA, a.H) if a.budget_share is None
              else a.budget_share * a.H * sum(P.KAPPA.values()))
    try:
        cells = []
        for det_name in ("weak", "mid", "strong"):
            det = detector.Detector.from_setting(det_name)
            for d in a.deltas:
                runner.reset_survivor_cache()
                base = runner.worst_case(BASELINE, wfs, (d,), CARRIERS, det, ag,
                                         budget, seeds, det_name)
                for nm in a.candidates:
                    runner.reset_survivor_cache()
                    c = runner.worst_case(nm, wfs, (d,), CARRIERS, det, ag,
                                          budget, seeds, det_name)
                    ci = gain_ci(base.per_wf, c.per_wf)
                    if ci is None:
                        continue
                    row = {"detector": det_name, "delta": d,
                           "gate": GATE.get(d, "untested"), "policy": nm,
                           "b1_harm": round(base.harm, 4),
                           "harm": round(c.harm, 4), **ci}
                    # The three verdicts a CI can give against a fixed bar, kept
                    # apart on purpose: "below" is a result, "straddles" is a
                    # sample-size statement, and conflating them is how an
                    # underpowered grid gets reported as a negative finding.
                    row["vs_gate"] = ("clears" if ci["lo"] >= GATE_PCT else
                                      "below" if ci["hi"] < GATE_PCT else
                                      "straddles")
                    cells.append(row)
                    print(f"{det_name:7} D={d} {nm:26} "
                          f"{ci['gain']:+6.1f}%  CI[{ci['lo']:+6.1f};{ci['hi']:+6.1f}]"
                          f"  {GATE.get(d,'untested'):9} {row['vs_gate']}",
                          file=sys.stderr)
    finally:
        costs.restore(P, old)

    cert = [c for c in cells if c["gate"] == "certified"]
    best_cert = max(cert, key=lambda c: c["gain"]) if cert else None
    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "setup": {"n": a.n, "H": a.H, "seeds": a.seeds, "scale": "usd",
                  "budget": budget, "budget_share": a.budget_share or costs.BUDGET_SHARE,
                  "candidates": list(a.candidates), "gate_pct": GATE_PCT,
                  "resample_unit": "workflow", "n_boot": 10000},
        "gate_verdict_per_delta": GATE,
        "cells": cells,
        "best_certified_cell": best_cert,
        "certified_cells_clearing_the_gate":
            [c for c in cert if c["vs_gate"] == "clears"],
        "certified_cells_straddling":
            [c for c in cert if c["vs_gate"] == "straddles"],
    }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
