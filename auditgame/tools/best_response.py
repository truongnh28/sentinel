#!/usr/bin/env python3
"""best_response.py -- the attacker that CHOOSES sigma, not the one that draws it.

Spec: docs/preregistration/TIEN-DANG-KY-attacker-best-response.md.

WHAT IS BEING FIXED.  The model states a best-responding attacker: it sees the
committed policy and plays the configuration worst for it.  build.plan_poison
ends in rng.choice over the feasible sigma set, and runner.worst_case maxes over
(Delta, k) with that ONE sigma per cell -- so the published quantity is
max_k E_sigma, not max_{k,sigma}.  Measured here: at H = 8 the attacker was
using 1 placement out of 8 at Delta=0, 1 of 5 at Delta=2, 1 of 3 at Delta=4.

So every worst-case number so far is OPTIMISTIC, and this measures by how much.

THE COMPARISON IS PAIRED BY WORKFLOW.  Both arms run the same workflows, the
same seeds, the same budget and the same cost scale; the only difference is
whether sigma is drawn or maximised over.  `sampled` reproduces
runner.worst_case exactly -- same rng seeding -- so the two columns differ in
one thing only.

    python3 tools/best_response.py --n 40 --seeds 3 > spikes/best-response.json
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
import build
import costs
import detector
import experiment
import policies as P
import runner
from core import CARRIERS, seed_of

POLICIES = ["B1 audit-at-commit", "SSG-full receding", "SSG-G guarded",
            "SentinelW window-belief", "Sentinel",
            "C8 deterministic sentinel", "B2 uniform random"]


def _cell(policy, wfs, d, det, ag, budget, seeds, setting, free: bool):
    """Worst-case harm over the attacker class, per workflow.

    free=False reproduces runner.worst_case: one sigma drawn per (wf, k).
    free=True maximises over every feasible sigma as well as over k.
    """
    per_wf = []
    for wf in wfs:
        best = None
        for k in CARRIERS:
            if free:
                specs = build.plan_poison_all(wf, k, d)
            else:
                one = build.plan_poison(wf, k, d,
                                        random.Random(seed_of(wf.wf_id, d, k)))
                specs = [one] if one is not None else []
            for ps in specs:
                hs = []
                for s in seeds:
                    r = runner.paired(wf, ps, policy, det, ag, s, budget,
                                      setting, "ratio")
                    if r is not None:
                        hs.append(r.harm)
                if hs:
                    m = sum(hs) / len(hs)
                    if best is None or m > best:
                        best = m
        if best is not None:
            per_wf.append(best)
    n = len(per_wf)
    return (sum(per_wf) / n if n else float("nan")), per_wf


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--deltas", type=int, nargs="+", default=[0, 2, 4])
    ap.add_argument("--detector", default="mid")
    a = ap.parse_args()

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    det, ag = detector.Detector.from_setting(a.detector), agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))
    old = costs.install(P)
    budget = costs.budget_for_table(P.KAPPA, a.H)
    try:
        # How much of the attacker's action space was being ignored.
        space = {}
        for d in a.deltas:
            counts = [len(build.plan_poison_all(wf, k, d))
                      for wf in wfs for k in CARRIERS]
            counts = [c for c in counts if c]
            space[d] = {"mean_placements_per_cell": round(
                sum(counts) / len(counts), 3) if counts else 0,
                "min": min(counts) if counts else 0,
                "max": max(counts) if counts else 0}

        cells = []
        for d in a.deltas:
            harm = {}
            for nm in POLICIES:
                runner.reset_survivor_cache()
                h_s, _ = _cell(nm, wfs, d, det, ag, budget, seeds, a.detector, False)
                runner.reset_survivor_cache()
                h_f, _ = _cell(nm, wfs, d, det, ag, budget, seeds, a.detector, True)
                harm[nm] = {"sampled": round(h_s, 4), "free": round(h_f, 4),
                            "rise": round(h_f - h_s, 4)}
                print(f"D={d} {nm:26} sampled {h_s:.4f} -> free {h_f:.4f} "
                      f"({h_f - h_s:+.4f})", file=sys.stderr)
            b1 = harm["B1 audit-at-commit"]
            row = {"delta": d, "harm": harm, "gain_vs_b1": {}}
            for nm in POLICIES:
                if nm == "B1 audit-at-commit":
                    continue
                row["gain_vs_b1"][nm] = {
                    "sampled": round(100.0 * (b1["sampled"] - harm[nm]["sampled"])
                                     / b1["sampled"], 2) if b1["sampled"] else None,
                    "free": round(100.0 * (b1["free"] - harm[nm]["free"])
                                  / b1["free"], 2) if b1["free"] else None}
                g = row["gain_vs_b1"][nm]
                if g["sampled"] is not None and g["free"] is not None:
                    g["narrowed_by"] = round(g["sampled"] - g["free"], 2)
            cells.append(row)

        # BR4: randomisation is supposed to reduce exactly this gain.
        br4 = []
        for c in cells:
            s = c["harm"].get("Sentinel", {}).get("rise")
            d8 = c["harm"].get("C8 deterministic sentinel", {}).get("rise")
            if s is not None and d8 is not None:
                br4.append({"delta": c["delta"], "sentinel_rise": s,
                            "c8_rise": d8, "randomisation_helps": s < d8})
    finally:
        costs.restore(P, old)

    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "setup": {"n": a.n, "H": a.H, "seeds": a.seeds, "detector": a.detector,
                  "scale": "usd", "budget": budget},
        "attacker_action_space_per_cell": space,
        "cells": cells,
        "BR4_randomisation_vs_deterministic": br4,
    }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
