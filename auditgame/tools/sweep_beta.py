#!/usr/bin/env python3
"""sweep_beta.py -- the drift rate that two mapping rules could not agree on.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Part VI class B (M2);
docs/design/plans/2026-09-23-tham-so-dot-2.md W3.

WHY A SWEEP.  tools/measure_beta.py counted benign churn on the real history of
ten SWE-bench repositories under two defensible mapping rules, and they disagree
by an order of magnitude on skill (0.058 vs 0.607) and by 2.5x on queue.  That
disagreement was the PRE-DECLARED trigger for moving beta from M1 (measure) to
M2 (sweep): a number two honest readings of the same history put 10x apart is
not a measurement, and quoting either one would be choosing.

costs.BETA_DEFAULT's own comment says the consequence out loud -- "It is a
DEFAULT, not a finding -- results that depend on it have to show the sweep" --
and until this script the sweep did not exist.

WHAT IT FOUND ON THE WAY.  The policies do not read the measured value at all.
`SentinelWindow.BETA_DRIFT` and `SSGBelief.BETA_DRIFT` are hardcoded 0.25, and
both call sites pass that to belief.WindowBelief, overriding the
costs.BETA_DEFAULT = 0.314 default it declares.  Same shape of defect as
experiment.py never calling costs.install(): the measured constant exists and
nothing consumes it.

THE CONTROL IS BUILT IN.  Only SentinelW and SSG-B carry a WindowBelief, so
every other policy's harm must be byte-identical at every beta.  If one moves,
the sweep is touching something it should not be.

    python3 tools/sweep_beta.py --n 20 --seeds 2 > spikes/beta-sweep.json
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

#: The two policies that carry a belief, and the comparators that do not.
BELIEF = ["SentinelW window-belief", "SSG-B belief-weighted"]
CONTROL = ["B1 audit-at-commit", "SSG-G guarded", "Sentinel"]

#: DECLARED BEFORE THE RUN.  Spans everything the two mapping rules produced,
#: plus the two values the code actually holds:
#:   0.013  queue under rule B, the smallest number either rule gives
#:   0.058  skill under rule A        0.607  skill under rule B -- the 10x split
#:   0.250  what the policies hardcode
#:   0.279  memory under rule B       0.314  memory under rule A (costs.BETA_DEFAULT)
#:   1.000  branch, by construction -- drift explains everything
BETA_GRID = (0.013, 0.033, 0.058, 0.15, 0.25, 0.279, 0.314, 0.45, 0.607, 0.8, 1.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--delta", type=int, default=2)
    ap.add_argument("--detector", default="mid")
    a = ap.parse_args()

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    det, ag = detector.Detector.from_setting(a.detector), agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))

    old_cost = costs.install(P)                      # the declared operating scale
    budget = costs.budget_for_table(P.KAPPA, a.H)
    names = BELIEF + CONTROL
    saved = {c.__name__: c.BETA_DRIFT
             for c in (P.SentinelWindow, P.SSGBelief)}
    try:
        curve = []
        for b in BETA_GRID:
            P.SentinelWindow.BETA_DRIFT = b
            P.SSGBelief.BETA_DRIFT = b
            row = {"beta": b, "harm": {}, "L": {}}
            for nm in names:
                runner.reset_survivor_cache()
                c = runner.worst_case(nm, wfs, (a.delta,), CARRIERS, det, ag,
                                      budget, seeds, a.detector)
                row["harm"][nm] = round(c.harm, 4)
                row["L"][nm] = round(metrics.loss(c.harm, c.q_false, c.t_lost), 4)
            row["ranking"] = sorted(names, key=lambda n: row["L"][n])
            row["winner"] = row["ranking"][0]
            curve.append(row)
            print(f"beta={b:<6} winner={row['winner']:<26} "
                  + "  ".join(f"{n.split()[0]}:{row['L'][n]:.3f}" for n in BELIEF),
                  file=sys.stderr)
    finally:
        P.SentinelWindow.BETA_DRIFT = saved["SentinelWindow"]
        P.SSGBelief.BETA_DRIFT = saved["SSGBelief"]
        costs.restore(P, old_cost)

    # THE CONTROL: policies with no belief must not move at all.
    drift = {nm: sorted({r["harm"][nm] for r in curve}) for nm in CONTROL}
    broken = {nm: v for nm, v in drift.items() if len(v) > 1}

    span = {nm: round(max(r["L"][nm] for r in curve)
                      - min(r["L"][nm] for r in curve), 4) for nm in BELIEF}
    winners = [r["winner"] for r in curve]
    flips = [{"between_beta": [curve[i-1]["beta"], curve[i]["beta"]],
              "from": winners[i-1], "to": winners[i]}
             for i in range(1, len(winners)) if winners[i] != winners[i-1]]

    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "setup": {"n": a.n, "H": a.H, "seeds": a.seeds, "delta": a.delta,
                  "detector": a.detector, "scale": "usd", "budget": budget},
        "beta_values_in_the_code": {
            "costs.BETA_DEFAULT": costs.BETA_DEFAULT,
            "policies.SentinelWindow.BETA_DRIFT": saved["SentinelWindow"],
            "policies.SSGBelief.BETA_DRIFT": saved["SSGBelief"],
            "note": "the policies hardcode their own value and never read the "
                    "measured one -- the sweep exists partly because of that",
        },
        "measured": {"rule_A": costs.BETA_RULE_A, "rule_B": costs.BETA_RULE_B},
        "curve": curve,
        "L_span_over_the_sweep": span,
        "winner_flips": flips,
        "control_policies_that_moved": broken,
    }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
