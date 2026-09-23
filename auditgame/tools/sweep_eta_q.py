#!/usr/bin/env python3
"""sweep_eta_q.py -- the price at which quarantine stops being an action.

Spec: docs/preregistration/TIEN-DANG-KY-thang-van-hanh-USD.md section 3;
docs/AuditGame-SE_Sentinel_Methodology_Full.md Part VI class B (M2).

WHY THIS IS A SWEEP AND NOT A NUMBER.  eta_Q IS measured: rebuilding a
quarantined carrier's live items is agent work at 61.5x the judge work of
auditing it (tools/measure_eta_q.py, spikes/eta-q.json).  The trouble is what
that measurement implies rather than how good it is.  The budget rule fixes

    B = budget_fraction(H) * H * 4 * kappa_bar = 10.257 * kappa_bar   (H = 8)

so at the measured r = eta_Q/kappa_bar = 61.5, ONE quarantine costs six times
the entire episode budget.  No policy can buy one.  `Sentinel`, `SentinelW` and
`NC1` are then not losing the argument -- they are being denied a move, and
costs.py's own comment says why that is not a comparison.

The honest form of the result is therefore not "eta_Q = X" but "quarantine is an
action below r = A, a rationed one between A and B, and not an action above B",
with the measured value placed on that axis.  Two of those thresholds are
derivable and unit-free -- see costs.eta_q_kills_action -- and this script
measures where the RANKING actually moves, which is not derivable.

WHAT IS HELD FIXED.  kappa, kappa_commit and the budget are the USD table at
every point; only r moves.  So this axis is eta_Q ALONE, unlike the chi axis,
which had to drag kappa_commit and eta_Q along to stay honest.

    python3 tools/sweep_eta_q.py --n 20 --seeds 2 > spikes/eta-q-sweep.json
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
import build
import costs
import detector
import experiment
import metrics
import policies as P
import runner
from core import CARRIERS, seed_of
import random

#: The policies that CAN quarantine, plus the comparators they have to beat.
#: B1 is here because it is the baseline the main claim is stated against, and
#: it never quarantines -- so it is the fixed point the others move around.
POLICIES = ["B1 audit-at-commit", "B5 risk-score", "B6 two-stage",
            "Sentinel", "SentinelW window-belief", "SSG-G guarded",
            "NC1 quarantine-everything"]

#: r = eta_Q / kappa_bar.  DECLARED BEFORE THE RUN.  The grid is not uniform on
#: purpose: it is dense where the two derived thresholds sit, because that is
#: where a flip is possible at all.
#:
#:   1.143   the legacy value every USD table before 2026-09-23 ran on
#:   1.282   one quarantine = one task's share of the budget, B/H
#:  10.257   one quarantine = the WHOLE episode budget
#:  61.519   the measured value
ETA_GRID = (1.143, 1.282, 2.0, 4.0, 6.0, 8.0, 10.257, 14.0, 20.0, 32.0, 61.519)


def count_quarantines(policy_name, wfs, det, ag, budget, seeds, setting,
                      delta: int) -> dict:
    """How many quarantines the policy actually BUYS, and how many it wanted.

    worst_case reports only FALSE quarantines, because lambda_Q prices those.
    P2 of the pre-registration is about whether the action happens at all, so
    the true ones have to be counted too.  One fixed (delta, carrier) sweep
    rather than the max over the attacker class: this counts actions, not harm.
    """
    tq = fq = eps = 0
    for wf in wfs:
        for k in CARRIERS:
            rng = random.Random(seed_of(wf.wf_id, delta, k))
            ps = build.plan_poison(wf, k, delta, rng)
            if ps is None:
                continue
            for s in seeds:
                r = runner.paired(wf, ps, policy_name, det, ag, s, budget,
                                  setting, "ratio")
                if r is None:
                    continue
                eps += 1
                tq += r.true_quarantine
                fq += r.false_quarantine
    return {"episodes": eps, "true": tq, "false": fq, "total": tq + fq,
            "per_episode": round((tq + fq) / eps, 4) if eps else None}


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
    budget = costs.budget_for_table(costs.KAPPA_USD, a.H)
    kbar = sum(costs.KAPPA_USD.values()) / len(costs.KAPPA_USD)

    curve = []
    for r in ETA_GRID:
        old = costs.install(P, eta_q_over_kappa_ratio=r)
        try:
            row = {"r": r,
                   "eta_q": P.ETA_Q_COST,
                   "quarantine_over_budget": round(P.ETA_Q_COST / budget, 4),
                   "L": {}, "harm": {}, "quarantines": {}}
            for nm in POLICIES:
                runner.reset_survivor_cache()
                c = runner.worst_case(nm, wfs, (a.delta,), CARRIERS, det, ag,
                                      budget, seeds, a.detector)
                row["L"][nm] = round(metrics.loss(c.harm, c.q_false, c.t_lost), 4)
                row["harm"][nm] = round(c.harm, 4)
                runner.reset_survivor_cache()
                row["quarantines"][nm] = count_quarantines(
                    nm, wfs, det, ag, budget, seeds, a.detector, a.delta)
            row["ranking"] = sorted(POLICIES, key=lambda n: row["L"][n])
            row["winner"] = row["ranking"][0]
            row["any_quarantine"] = sum(
                row["quarantines"][n]["total"] for n in POLICIES)
            curve.append(row)
            print(f"r={r:>7.3f}  winner={row['winner']:<26} "
                  f"quarantines={row['any_quarantine']:>5}  "
                  f"one_Q/B={row['quarantine_over_budget']:.3f}",
                  file=sys.stderr)
        finally:
            costs.restore(P, old)

    winners = [c["winner"] for c in curve]
    flips = [{"between_r": [curve[i - 1]["r"], curve[i]["r"]],
              "from": winners[i - 1], "to": winners[i]}
             for i in range(1, len(winners)) if winners[i] != winners[i - 1]]

    # Where the ACTION dies, measured rather than derived: the last r at which
    # any policy still buys a quarantine.
    alive = [c["r"] for c in curve if c["any_quarantine"] > 0]
    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "setup": {"n": a.n, "H": a.H, "seeds": a.seeds, "delta": a.delta,
                  "detector": a.detector, "budget": budget,
                  "kappa_bar": kbar, "scale": "usd",
                  "lambda_Q": metrics.LAMBDA_Q, "lambda_T": metrics.LAMBDA_T},
        "derived_thresholds": {
            "one_quarantine_is_one_task_share": round(
                costs.eta_q_kills_action(a.H) / a.H, 4),
            "one_quarantine_is_the_whole_budget": round(
                costs.eta_q_kills_action(a.H), 4)},
        "legacy_r": round(costs.ETA_Q_USD_LEGACY / kbar, 4),
        "measured_r": round(costs.ETA_Q_USD / kbar, 4),
        "curve": curve,
        "winner_flips": flips,
        "last_r_with_a_quarantine": max(alive) if alive else None,
    }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
