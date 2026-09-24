#!/usr/bin/env python3
"""sweep_budget.py -- is the null result a property of the game, or of one budget?

Spec: docs/preregistration/TIEN-DANG-KY-thang-van-hanh-USD.md section 3.

THE HOLE THIS CLOSES.  Every negative number measured so far -- no policy clears
the 15% gate, Sentinel ties B1, all three of its mechanisms contribute nothing --
was measured at ONE budget: B/(H*sum kappa) = 0.3205, inherited from the legacy
17.95 at H = 8.  A reviewer's first question is whether the defence simply could
not afford to play, and the harm levels invite it: 0.88..0.98 at Delta = 2 means
the attacker nearly always wins.

So the budget share is swept.  Two outcomes and both are publishable:
  - gains stay flat  -> the null result is a property of the GAME, and saying so
                        across a 6x range is far stronger than saying it once;
  - gains cross 15%  -> the claim survives WITH A SCOPE, "audit allocation pays
                        off above budget share X", which is a result the draft
                        does not have.

WHAT IS HELD FIXED.  The cost table, kappa_commit/kbar, eta_Q/kbar and H all
stay put; only B moves.  So this is the fourth dimensionless ratio alone -- the
one axis of the four that had never been swept.

    python3 tools/sweep_budget.py --n 40 --seeds 3 > spikes/budget-sweep.json
"""
from __future__ import annotations
import argparse, datetime, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent, costs, detector, experiment, policies as P, runner
from core import CARRIERS

POLICIES = ["B1 audit-at-commit", "SSG-full receding", "SSG-G guarded",
            "SentinelW window-belief", "Sentinel", "B2 uniform random"]

#: Share of one task's full four-carrier audit bill, per task.  DECLARED BEFORE
#: THE RUN.  0.3205 is where every published number sits; 1.0 buys a full sweep
#: of all four carriers every task, which is the ceiling worth testing -- above
#: it the defender audits everything and the allocation question disappears.
SHARES = (0.16, 0.3205, 0.5, 0.75, 1.0, 1.5, 2.0)
GATE_PCT = 15.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--deltas", type=int, nargs="+", default=[2, 4])
    ap.add_argument("--detector", default="mid")
    ap.add_argument("--policies", nargs="+", default=POLICIES,
                    help="policies to sweep; B1 must be among them, since every "
                         "gain is measured against it. Default: the published set.")
    a = ap.parse_args()
    if "B1 audit-at-commit" not in a.policies:
        ap.error("--policies must include 'B1 audit-at-commit': every gain is vs B1")
    POLICIES[:] = a.policies

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    det, ag = detector.Detector.from_setting(a.detector), agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))
    old = costs.install(P)
    total = sum(P.KAPPA.values())
    try:
        rows = []
        for share in SHARES:
            budget = share * a.H * total
            for d in a.deltas:
                harm = {}
                for nm in POLICIES:
                    runner.reset_survivor_cache()
                    c = runner.worst_case(nm, wfs, (d,), CARRIERS, det, ag,
                                          budget, seeds, a.detector)
                    harm[nm] = round(c.harm, 4)
                b1 = harm["B1 audit-at-commit"]
                gains = {nm: (round(100.0 * (b1 - harm[nm]) / b1, 2)
                              if b1 else None)
                         for nm in POLICIES if nm != "B1 audit-at-commit"}
                best = max(gains, key=lambda k: gains[k])
                rows.append({"share": share, "delta": d, "budget": budget,
                             "harm": harm, "gain_vs_b1": gains,
                             "best_policy": best, "best_gain": gains[best],
                             "clears_15": gains[best] >= GATE_PCT})
                print(f"share={share:<7} D={d}  best={best:22} "
                      f"{gains[best]:+6.1f}%  {'CLEARS' if gains[best] >= GATE_PCT else ''}"
                      f"   B1 harm {b1:.3f}", file=sys.stderr)
    finally:
        costs.restore(P, old)

    clearing = [r for r in rows if r["clears_15"]]
    out = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
           "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                    capture_output=True, text=True).stdout.strip(),
           "setup": {"n": a.n, "H": a.H, "seeds": a.seeds,
                     "detector": a.detector, "scale": "usd",
                     "published_share": 0.3205, "gate_pct": GATE_PCT},
           "rows": rows,
           "shares_where_some_policy_clears_15": sorted(
               {r["share"] for r in clearing}),
           "verdict": ("the null result is budget-specific"
                       if clearing else
                       "no budget in the swept range lets any policy clear 15%")}
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
