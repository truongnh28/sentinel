#!/usr/bin/env python3
"""compare_cost_scales.py -- the same grid, priced three ways.

Spec: docs/design/plans/2026-09-23-tham-so-dot-2.md T3;
docs/AuditGame-SE_Parameter_Estimation_Report.md, method M1.

THE QUESTION THIS ANSWERS.  kappa(k) is the cost of auditing a carrier, and this
project now has THREE candidate tables for it, in three different units:

  draft  policies.KAPPA -- the manuscript's numbers.  They are the per-STAGE
         costs of section 7 used as a per-CARRIER table; kept here as evidence.
  usd    costs.KAPPA_USD -- items_scored(k) x USD per judgement.  What an audit
         costs to BUY from the model that does the judging.
  cpu    costs.KAPPA_CPU -- CPU seconds of checkpoints.py doing the four audit
         stages.  What an audit costs to RUN.

A scale is not a rescaling of the loss.  It changes which carrier is expensive,
hence which carrier the attacker prefers, hence the game -- and it changes which
ACTIONS a fixed budget can still afford.  So the two things to read off the table
below are the ORDERING of the policies and the `spent`/`q_false` columns, which
say whether every policy could still take its own action.

EQUAL SHARE, NOT EQUAL NUMBER.  Budget is set per scale by costs.budget_for_table:
each scale gets the same share of a full audit bill that the legacy 17.95 bought
(32.1% at H=8).  Copying one number across scales would compare a policy that can
audit everything against one that can audit nothing.

    python3 tools/compare_cost_scales.py --n 20 --seeds 2 > spikes/cost-scale-comparison.json
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

#: The policies the manuscript's main table carries, plus the two that span BOTH
#: channels.  Not the whole registry: each cell is a full attacker-class
#: maximisation, so the grid is quadratic in what goes here.
#:
#: WHY SentinelW AND SSG-G HAD TO BE ADDED.  `Sentinel` declares
#: `ACTIONS = frozenset(CARRIERS)` -- it can audit the four carriers and nothing
#: else, so no commit price can reach it (verified: 0 commit actions in 80
#: decisions, even priced below the cheapest carrier).  Comparing it against B1,
#: which audits ONLY at commit, therefore compares two disjoint channels, and
#: the cost scale decides the winner by deciding which channel is cheap.  The
#: two policies below carry both channels, so they are the ones whose answer to
#: "which unit" is about allocation rather than about reachability.
POLICIES = ["B1 audit-at-commit", "B5 risk-score", "B6 two-stage",
            "Sentinel", "SentinelW window-belief", "SSG-G guarded",
            "B7 minimax-lp", "NC1 quarantine-everything"]

CARRIERS = ("memory", "skill", "queue", "branch")


def scales(H: int) -> dict:
    """The cost tables, each with the budget that buys the same share of an audit bill."""
    return {
        "draft": {
            "kappa": dict(P.KAPPA), "kappa_commit": P.KAPPA_COMMIT,
            "eta_q": P.ETA_Q_COST, "budget": costs.LEGACY_BUDGET,
            "note": "per-STAGE costs of the manuscript, used as a per-carrier table",
        },
        # TWO USD COLUMNS, because costs.py holds two different prices for
        # quarantine and they disagree by 54x.  `ETA_Q_USD` scales the
        # PLACEHOLDER's ratio (2.0 / mean placeholder kappa = 1.14x) onto the USD
        # table; `eta_q(k)` is the MEASURED one (n_live(k) rebuild writes, 61.5x
        # an audit).  Which one is installed decides whether quarantine is an
        # affordable action at all, so both are run rather than one being chosen
        # silently.  `usd` is the all-measured column; `usd-legacy-etaQ` is the
        # column every USD table published before today was actually run on.
        "usd": {
            "kappa": dict(costs.KAPPA_USD), "kappa_commit": costs.KAPPA_COMMIT_USD,
            "eta_q": sum(costs.eta_q(c) for c in CARRIERS) / len(CARRIERS),
            "budget": costs.budget_for_table(costs.KAPPA_USD, H),
            "note": "items_scored(k) x USD per judgement, with the MEASURED "
                    "eta_Q (rebuild cost of the quarantined carrier)",
        },
        "usd-legacy-etaQ": {
            "kappa": dict(costs.KAPPA_USD), "kappa_commit": costs.KAPPA_COMMIT_USD,
            "eta_q": costs.ETA_Q_USD,
            "budget": costs.budget_for_table(costs.KAPPA_USD, H),
            "note": "same kappa, but quarantine priced by the placeholder's "
                    "ratio instead of the measurement -- kept as evidence, this "
                    "is what costs.install() still does",
        },
        "cpu": {
            "kappa": dict(costs.KAPPA_CPU), "kappa_commit": costs.KAPPA_COMMIT_CPU,
            "eta_q": costs.ETA_Q_OVER_KAPPA * (sum(costs.KAPPA_CPU.values())
                                               / len(costs.KAPPA_CPU)),
            "budget": costs.budget_for_table(costs.KAPPA_CPU, H),
            "note": "measured through checkpoints.py; commit EXCLUDES "
                    "differential testing, so it is a lower bound",
        },
    }


def run_scale(spec: dict, wfs, det_name: str, delta: int, seeds) -> dict:
    """One full policy sweep with policies patched to this scale, then restored."""
    old = {"KAPPA": dict(P.KAPPA), "KAPPA_COMMIT": P.KAPPA_COMMIT,
           "ETA_Q_COST": P.ETA_Q_COST}
    P.KAPPA = dict(spec["kappa"])
    P.KAPPA_COMMIT = spec["kappa_commit"]
    P.ETA_Q_COST = spec["eta_q"]
    det, ag = detector.Detector.from_setting(det_name), agent.MockAgent()
    try:
        out = {}
        for name in POLICIES:
            runner.reset_survivor_cache()
            cell = runner.worst_case(name, wfs, (delta,), CARRIERS, det, ag,
                                     spec["budget"], seeds, det_name)
            out[name] = {
                "harm": round(cell.harm, 4),
                "L": round(metrics.loss(cell.harm, cell.q_false, cell.t_lost), 4),
                "q_false": round(cell.q_false, 4),
                "t_lost": round(cell.t_lost, 4),
                # The share of its OWN budget the policy managed to spend.  A
                # policy sitting near 0 here is not frugal, it is priced out.
                "spent_pct": round(100.0 * cell.spent_mean / spec["budget"], 1),
                "n_feasible": cell.n_feasible,
            }
        return out
    finally:
        for k, v in old.items():
            setattr(P, k, v)


def affordability(spec: dict, H: int) -> dict:
    """Can a policy still take each action once, on this scale, in this budget?

    This is the check that turned up NC1 spending 0%: on the CPU scale a single
    quarantine costs 4.4x the whole budget, so the control never acts.  Reported
    per scale rather than discovered per table.
    """
    b = spec["budget"]
    return {
        "budget": b,
        "cheapest_audit": min(spec["kappa"].values()) / b,
        "dearest_audit": max(spec["kappa"].values()) / b,
        "commit_audit": spec["kappa_commit"] / b,
        "one_quarantine": spec["eta_q"] / b,
        "full_sweep_per_step": sum(spec["kappa"].values()) / b,
        "unit": "fraction of the episode budget",
    }


def sweep_commit_price(spec: dict, wfs, det_name, delta, seeds,
                       multipliers) -> dict:
    """The one-dimensional sensitivity the scale comparison reduces to.

    WHY THIS SWEEP AND NOT ANOTHER.  Across the three scales, Sentinel's own
    numbers barely move (L 0.970 / 0.970 / 0.973) while B1's swing from 1.000 to
    0.512.  B1 audits ONLY at commit, so what moved is one number: the price of
    a commit audit relative to the budget.  Every other difference between the
    scales is second order next to it.

    kappa_commit is also the number nobody has measured: the USD table DEFINES it
    as "score all four carriers" (4.0x the mean carrier audit) and the CPU table
    MEASURES it without differential testing (1.43x, a lower bound).  So the
    honest report is not a single table but the multiplier at which the answer
    changes sign -- which is what this returns.

    The carrier table and the budget are held fixed; only kappa_commit moves.
    """
    out = {}
    for m in multipliers:
        kbar = sum(spec["kappa"].values()) / len(spec["kappa"])
        variant = dict(spec, kappa_commit=m * kbar)
        r = run_scale(variant, wfs, det_name, delta, seeds)
        out[str(m)] = {
            "kappa_commit": variant["kappa_commit"],
            "commit_audits_per_episode": spec["budget"] / variant["kappa_commit"],
            "B1_L": r["B1 audit-at-commit"]["L"],
            "Sentinel_L": r["Sentinel"]["L"],
            "B1_harm": r["B1 audit-at-commit"]["harm"],
            "Sentinel_harm": r["Sentinel"]["harm"],
            "sentinel_wins_on_L": r["Sentinel"]["L"] < r["B1 audit-at-commit"]["L"],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=20, help="workflows")
    ap.add_argument("--H", type=int, default=8, help="tasks per workflow")
    ap.add_argument("--delta", type=int, default=2)
    ap.add_argument("--detector", default="mid")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--sweep-commit", action="store_true",
                    help="also sweep kappa_commit as a multiple of mean kappa")
    a = ap.parse_args()

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    seeds = tuple(range(1, a.seeds + 1))
    spec = scales(a.H)

    results = {name: run_scale(s, wfs, a.detector, a.delta, seeds)
               for name, s in spec.items()}

    comparison = {pol: {s: results[s][pol] for s in spec} for pol in POLICIES}
    ranking = {s: sorted(POLICIES, key=lambda p: results[s][p]["L"])
               for s in spec}

    commit_sweep = None
    if a.sweep_commit:
        mult = [1, 1.43, 2, 3, 4, 6, 8, 12, 16, 24]
        commit_sweep = {name: sweep_commit_price(spec[name], wfs, a.detector,
                                                 a.delta, seeds, mult)
                        for name in ("usd", "cpu")}

    print(json.dumps({
        "comparison": comparison,
        "commit_price_sweep": commit_sweep,
        "ranking_by_L": ranking,
        "ranking_identical": len({tuple(r) for r in ranking.values()}) == 1,
        "scales": spec,
        "chi": {s: round(P.chi_of(spec[s]["kappa"]), 3) for s in spec},
        "affordability": {s: affordability(spec[s], a.H) for s in spec},
        "provenance": {
            "grid": f"{a.n} workflows, H={a.H}, Delta={a.delta}, "
                    f"detector {a.detector}, seeds {seeds}",
            "budget_rule": "same share of the full audit bill as the legacy 17.95",
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
