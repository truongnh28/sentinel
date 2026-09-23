#!/usr/bin/env python3
"""measure_heldout_transfer.py -- worst case on attackers nobody tuned against.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 3.3, Stage 9;
docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md (group F).

THE CLAIM THIS EXISTS TO TEST.  The manuscript reports 27.6% against held-out
adaptive attackers.  `attackers.py` already carries the library, the hash-based
split and `worst_case_over` -- everything except a caller.  So the split existed
and nothing had ever been measured on it, which is the worst of both worlds: the
apparatus reads as evidence while producing none.

WHAT IS AND IS NOT COMPARABLE HERE.  An attacker in this file is a RULE that maps
a workflow to (carrier, Delta).  `runner.worst_case` maximises over raw
configurations instead, which cannot be held out -- you can withhold a rule, not
a coordinate.  So the numbers below are NOT the ones in the main grid and must
not be put in a table beside them.

THE STATISTIC SATURATES, AND IT HAS TO BE SAID BEFORE ANY NUMBER IS READ.
Worst case over EIGHTEEN rules compromises almost every workflow whatever the
policy does, so every harm lands in 0.88 .. 0.98 and the differences are
fractions of one workflow.  Measured: SSG-G's transfer gap is +0.050 at N=20,
-0.050 at N=40 and -0.025 at N=80 -- the SIGN follows the sample size.  Nothing
here supports a claim about transfer in either direction, including the earlier
reading that belief-carrying policies overfit; that was N=20 noise.

Fixing it needs a different statistic (mean over rules, or a per-rule
breakdown) or far more workflows -- not more seeds, which do not touch the
saturation.  Until then this tool reports a measurement that cannot yet decide.

THE HONEST DENOMINATOR.  Six of the twelve rules are held out, not seven of
eighteen: the library is 12 and the split is by hash of the name, fixed before
any measurement.  A transfer number on 6 rules is quoted as a transfer number on
6 rules.

    python3 tools/measure_heldout_transfer.py --n 40 --seeds 3 > spikes/heldout-transfer.json
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
import attackers
import detector
import experiment
import runner

POLICIES = ["B1 audit-at-commit", "B5 risk-score", "B6 two-stage",
            "Sentinel", "SentinelW window-belief", "SSG-G guarded",
            "SSG-B belief-weighted", "B7 minimax-lp"]


def gain_vs_b1(row: dict) -> float:
    b1 = row["B1 audit-at-commit"]
    return 100.0 * (b1 - row["Sentinel"]) / max(b1, 1e-9)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--budget", type=float, default=17.95)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--detector", default="mid")
    a = ap.parse_args()

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    det, ag = detector.Detector.from_setting(a.detector), agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))
    dev, held = attackers.development(), attackers.held_out()

    out = {"development": {}, "held_out": {}}
    raw = {"development": {}, "held_out": {}}
    for split, names in (("development", dev), ("held_out", held)):
        for nm in POLICIES:
            runner.reset_survivor_cache()
            table = attackers.per_rule_harm(nm, names, wfs, det, ag,
                                            a.budget, seeds, a.detector)
            summ = attackers.summarise_rules(table)
            raw[split][nm] = summ
            out[split][nm] = round(summ["worst_case"], 4)
            print(f"{split:12} {nm:26} worst {summ['worst_case']:.4f}  "
                  f"mean {summ['mean_over_rules']:.4f}  "
                  f"defeated {summ['rules_defeated']:.2f}/{summ['n_rules']}",
                  file=sys.stderr)

    # The transfer gap: how much worse a policy does on rules it was never tuned
    # against.  Positive means the held-out rules hurt more, which is the
    # direction a tuned defender is supposed to show.
    transfer = {nm: round(out["held_out"][nm] - out["development"][nm], 4)
                for nm in POLICIES}

    # CI95 on the transfer gap, RESAMPLED BY WORKFLOW -- the unit, because cases
    # from one workflow share a task chain. Without it this table repeats the
    # mistake it was written to correct: reading a direction off noise.
    gaps = {}
    for nm in POLICIES:
        d_, h_ = raw["development"][nm], raw["held_out"][nm]
        gaps[nm] = {}
        for stat in ("worst", "mean", "defeated"):
            a_, b_ = h_["per_workflow"][stat], d_["per_workflow"][stat]
            k = min(len(a_), len(b_))
            lo, hi = runner.bootstrap_paired(a_[:k], b_[:k])
            gaps[nm][stat] = {
                "held_minus_dev": round(sum(a_[:k]) / k - sum(b_[:k]) / k, 4),
                "ci95": [round(lo, 4), round(hi, 4)],
                "separates_from_zero": not (lo <= 0.0 <= hi),
            }

    print(json.dumps({
        "statistics": {
            split: {nm: {k: round(v, 4) for k, v in raw[split][nm].items()
                         if k != "per_workflow"} for nm in POLICIES}
            for split in raw},
        "transfer_gap_with_ci": gaps,
        "why_three_statistics": (
            "worst_case is the manuscript's quantity and it SATURATES at 18 "
            "rules -- almost every workflow is compromised by something, so "
            "every value lands in 0.88..0.98 and its sign followed the sample "
            "size (+0.050 at N=20, -0.050 at N=40, -0.025 at N=80). "
            "mean_over_rules and rules_defeated are reported beside it because "
            "they do not, not instead of it."),
        "harm": out,
        "transfer_gap_held_out_minus_development": transfer,
        "gain_vs_b1": {s: round(gain_vs_b1(out[s]), 2) for s in out},
        "split": {"library_size": len(attackers.REGISTRY),
                  "development": sorted(dev), "held_out": sorted(held),
                  "note": "6 of 12 rules held out by hash of the name, not 7 of "
                          "18 -- the library is not yet the manuscript's size, "
                          "and the transfer number is quoted on what exists"},
        "saturation_warning": (
            "worst case over 18 rules leaves every harm in 0.88..0.98; the "
            "transfer gap's SIGN follows N (+0.050 at 20, -0.050 at 40, -0.025 "
            "at 80 workflows). Do not read a direction off this."),
        "not_comparable_with": ("the main grid, which maximises over raw "
                                "(carrier, Delta) configurations rather than "
                                "over attacker rules"),
        "provenance": {
            "grid": f"{a.n} workflows, H={a.H}, B={a.budget}, "
                    f"detector {a.detector}, seeds {seeds}",
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
