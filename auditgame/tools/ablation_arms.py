#!/usr/bin/env python3
"""ablation_arms.py -- the two ablation rows the grid never had.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 9 (ablation);
draft section 9, "bo randomisation / bo belief / bo rotation / bo benign-drift".

WHAT WAS MISSING.  The registry carries C4 (belief removed) and C8
(randomisation removed), so two of the draft's four ablation rows existed.  The
other two did not, for different reasons:

  ROTATION.  It simply had no arm.  `Sentinel.ROTATION_PERIOD = 0` disables the
  mechanism and the class documents that it reproduces the two-mechanism
  version, so the arm is a value, not a new policy -- which is why it is set
  here rather than added to REGISTRY, where it would need a freeze entry and a
  registry test for something that is not a different policy.

  BENIGN DRIFT.  It could not be removed because IT WAS NEVER THERE.  Nothing
  in build.py, core.py or runner.py generates benign churn; grepping for drift
  finds only belief.py, where beta is the NULL hypothesis's prior mass.  So the
  world has no drift and the belief reasons about a competing cause that does
  not exist in the data it is fed -- which is also why beta is inert
  (tools/sweep_beta.py, tests/gate1_integrity/test_beta_invariance.py).

  What DOES act like benign drift here is the detector's false alarms: a clean
  item draws N(0, 1) and fires whenever it clears tau_det, so the defence spends
  budget on innocent items at rate phi.  Removing benign drift therefore means
  removing false alarms, and that is the arm below.

THE DRIFT-FREE ARM READS GROUND TRUTH, DELIBERATELY.  `_NoFalseAlarms.score`
returns -inf for clean items, which the real detector may never do -- gate 1
enforces exactly that.  It is legal here for the same reason an oracle upper
bound is legal: it is a COUNTERFACTUAL WORLD used to price a mechanism, it is
defined in this tool rather than in detector.py so the shipped detector cannot
acquire it, and its number may never be quoted as a policy result.

    python3 tools/ablation_arms.py --n 40 --seeds 3 > spikes/ablation.json
"""
from __future__ import annotations
import argparse
import datetime
import json
import math
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


class _NoFalseAlarms(detector.Detector):
    """A world with no benign drift: clean items never fire.

    NOT A DETECTOR ANYONE COULD BUILD -- it reads `item.poisoned`.  See the
    module docstring for why that is allowed in this file and nowhere else.
    """

    def score(self, item, now: int, seed: int) -> float:
        if not item.poisoned:
            return -math.inf
        return super().score(item, now, seed)

    def at_depth(self, depth: int) -> "detector.Detector":
        return _NoFalseAlarms(self.d_prime * (depth ** 0.5), self.tau_det)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--deltas", type=int, nargs="+", default=[0, 2, 4])
    ap.add_argument("--detector", default="mid")
    a = ap.parse_args()

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    ag = agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))
    base_det = detector.Detector.from_setting(a.detector)
    drift_free = _NoFalseAlarms(base_det.d_prime, base_det.tau_det)

    old_cost = costs.install(P)
    budget = costs.budget_for_table(P.KAPPA, a.H)
    saved_rot = P.Sentinel.ROTATION_PERIOD
    try:
        rows = []
        for d in a.deltas:
            cell = {"delta": d, "arms": {}}

            def run(label, name, det, note):
                runner.reset_survivor_cache()
                c = runner.worst_case(name, wfs, (d,), CARRIERS, det, ag,
                                      budget, seeds, a.detector)
                cell["arms"][label] = {
                    "policy": name, "harm": round(c.harm, 4),
                    "L": round(metrics.loss(c.harm, c.q_false, c.t_lost), 4),
                    "q_false": round(c.q_false, 3),
                    "n_feasible": c.n_feasible, "note": note}

            run("full", "Sentinel", base_det,
                "all three mechanisms, the control every row is read against")
            run("minus_belief", "C4 blind sentinel", base_det,
                "registry arm: belief removed")
            run("minus_randomisation", "C8 deterministic sentinel", base_det,
                "registry arm: randomisation removed")

            P.Sentinel.ROTATION_PERIOD = 0
            try:
                run("minus_rotation", "Sentinel", base_det,
                    "ROTATION_PERIOD=0 -- the class says this reproduces the "
                    "two-mechanism version")
            finally:
                P.Sentinel.ROTATION_PERIOD = saved_rot

            run("minus_benign_drift", "Sentinel", drift_free,
                "COUNTERFACTUAL WORLD: clean items never fire, so no budget is "
                "spent on false alarms. Reads ground truth; never a policy result")

            full = cell["arms"]["full"]["harm"]
            cell["cost_of_removing"] = {
                k: round(v["harm"] - full, 4)
                for k, v in cell["arms"].items() if k != "full"}
            rows.append(cell)
            print(f"D={d}  " + "  ".join(
                f"{k}:{v['harm']:.3f}" for k, v in cell["arms"].items()),
                file=sys.stderr)
    finally:
        P.Sentinel.ROTATION_PERIOD = saved_rot
        costs.restore(P, old_cost)

    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "setup": {"n": a.n, "H": a.H, "seeds": a.seeds, "scale": "usd",
                  "detector": a.detector, "budget": budget,
                  "rotation_period": saved_rot,
                  "rotation_gain": P.Sentinel.ROTATION_GAIN},
        "draft_reference": {
            "removing randomisation costs": 0.184,
            "removing belief costs": 0.099,
            "removing benign-drift": 0.264,
            "sentinel_full": 0.272,
            "note": "the draft's benign-drift row is LOWER than full Sentinel, "
                    "which README SS3.4 issue 10 already flags as a question "
                    "for the advisor rather than a number to reproduce"},
        "cells": rows,
    }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
