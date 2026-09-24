#!/usr/bin/env python3
"""measure_budget_gap.py -- the LP budgets in EXPECTATION, the runtime per EPISODE.

Spec: docs/AuditGame-SE_Parameter_Estimation_Notes.md 4.4 ("gap ky vong vs rang
buoc cung"); README 3.2, row "Chenh lech rang buoc".

`lp.solve_stackelberg_lp` constrains spend in expectation:
    sum_k kappa_k sum_t u[k,t] + kappa_c sum_t v[t] <= B
while every executed episode obeys spent + cost(a) <= B at each draw.  The two
are not the same constraint, and the difference is a number: coverage the LP
promises that no single episode can buy, because the draws that exceed the
remaining budget are dropped.

That number was measured once (-13.29% coverage, legacy scale) and its result
file was never committed, so it could not be reproduced.  This tool is the
reproduction, and it runs on BOTH scales so the legacy figure is re-derived by
the same code that produces the operating one.

    python3 tools/measure_budget_gap.py > spikes/budget-gap.json
"""
from __future__ import annotations
import argparse, datetime, json, pathlib, random, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import costs
import lp
from core import CARRIERS, seed_of


def tables(scale: str):
    if scale == "usd":
        kap = [costs.KAPPA_USD[c] for c in CARRIERS]
        return kap, costs.KAPPA_COMMIT_USD
    return [costs.KAPPA_PLACEHOLDER[c] for c in CARRIERS], 4.1


def measure(scale: str, H: int, reps: int, deltas):
    kap, kc = tables(scale)
    B = costs.BUDGET_SHARE * H * sum(kap)
    u, v, m = lp.solve_stackelberg_lp(len(kap), H, B, kap, kc, deltas=tuple(deltas))
    K = len(kap)
    lp_cov = sum(sum(r) for r in u) / (K * H)
    lp_spend = sum(kap[k] * sum(u[k]) for k in range(K)) + kc * sum(v)

    windows = [(k, i, i + d) for d in deltas for k in range(K) for i in range(H - d)]
    caught = {w: 0 for w in windows}
    rng = random.Random(seed_of("budget-gap", scale, H))
    total_sum = spend_sum = dropped = 0.0
    for _ in range(reps):
        spent, did = 0.0, []                  # executed actions: ("k", k, t) / ("c", None, t)
        for t in range(H):
            r, acc, pick = rng.random(), 0.0, None
            for k in range(K):
                acc += u[k][t]
                if r < acc:
                    pick = ("k", k); break
            else:
                acc += v[t]
                if r < acc:
                    pick = ("c", None)
            if pick is None:
                continue
            cost = kap[pick[1]] if pick[0] == "k" else kc
            if spent + cost > B * (1 + 1e-9):
                dropped += 1                   # the hard constraint bites here
                continue
            spent += cost
            did.append((pick[0], pick[1], t))
        total_sum += len(did) / H
        spend_sum += spent
        for (k, i, s_) in windows:
            if any((a == "k" and kk == k and i <= t < s_) or (a == "c" and t == s_)
                   for a, kk, t in did):
                caught[(k, i, s_)] += 1
    ex_value = min(c / reps for c in caught.values())
    lp_total = (sum(sum(r) for r in u) + sum(v)) / H
    return {
        "scale": scale, "H": H, "reps": reps, "deltas": list(deltas),
        "budget": B,
        "value_lp": round(m, 4), "value_executed": round(ex_value, 4),
        "value_gap_pct": round(100 * (ex_value - m) / m, 2) if m else None,
        "actions_per_task_lp": round(lp_total, 4),
        "actions_per_task_executed": round(total_sum / reps, 4),
        "carrier_coverage_lp": round(lp_cov, 4),
        "spend_lp_share": round(lp_spend / B, 4),
        "spend_executed_share": round(spend_sum / reps / B, 4),
        "dropped_draws_per_episode": round(dropped / reps, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--deltas", type=int, nargs="+", default=[0, 2, 4])
    a = ap.parse_args()
    rows = [measure(s, a.H, a.reps, a.deltas) for s in ("legacy", "usd")]
    print(json.dumps({
        "rows": rows,
        "reading": ("value_gap_pct: the LP promises catch probability value_lp on "
                    "the attacker's best window, budgeting in EXPECTATION; an "
                    "episode that obeys the budget draw by draw catches the worst "
                    "window with probability value_executed. Any figure read off "
                    "the LP value is optimistic by about this much."),
        "provenance": {"date": datetime.date.today().isoformat(),
                       "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                                capture_output=True, text=True).stdout.strip()},
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
