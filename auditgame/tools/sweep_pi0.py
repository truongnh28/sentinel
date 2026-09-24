#!/usr/bin/env python3
"""sweep_pi0.py -- does the policy ranking survive a different pi0?

Spec: docs/preregistration/TIEN-DANG-KY-quet-pi0.md (issue #18).

pi0 = 1/E[n_total] = 0.0799 is DERIVED (costs.PI0_WORLD), but from 20
instrumented episodes.  This asks whether any conclusion rests on that number.

THREE PATHS CARRY pi0, and a sweep that moves only one of them measures a model
nobody runs:
  1. scoring.posterior / carrier_score -- the posterior a policy reads.  Their
     `pi0=PI0` default was bound at import, so rebinding scoring.PI0 alone
     changes nothing; the defaults are rebound too.
  2. scoring.tau_sel -- the threshold table GENERATED from pi0.
  3. p / scoring.PI0 in belief.py and policies.py -- read at call time.

THE TABLE IS CONVERTED, NOT REGENERATED.  tau_sel is an ORDER STATISTIC of p on
a clean carrier (gen_score_table.measure: ps[int((1-alpha_c) M)], no
interpolation), and p = pi0 L / (pi0 L + 1 - pi0) is strictly increasing in L.
So the order statistic at pi0' is exactly the image of the one at pi0 under
p -> L -> p'.  That saves 23 minutes per grid point and, more to the point,
keeps the SAME Monte Carlo draws behind every column -- a regenerated table
would add sampling noise that the sweep would then report as a pi0 effect.
`mean_p` is NOT an order statistic and is not converted; nothing on the run
path reads it (scoring.expected_clean_score is a diagnostic).

The frozen file is never written.  The freeze header reads DRIFTED while a
non-default pi0 is installed, which is correct: this is a sensitivity check.

    python3 tools/sweep_pi0.py > spikes/frozen/pi0-sweep.json
"""
from __future__ import annotations
import argparse, contextlib, copy, datetime, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent, costs, detector, experiment, policies as P, runner, scoring
from core import CARRIERS

#: DECLARED in the pre-registration.  0.04 is PI0_MODEL (pi_attack * pi0), the
#: one lower value with a reason behind it; 0.20 is 2.5x the derived value.
GRID = (0.04, costs.PI0_WORLD, 0.10, 0.20)
SHARES = (0.3205, 0.75)
POLICIES = ["B1 audit-at-commit", "B2 uniform random", "B5 risk-score",
            "SSG-full receding", "SSG-up receding", "SSG-G guarded",
            "SentinelW window-belief", "Sentinel"]
#: Pre-registration pi1: none of these reads `.p`, so each must be identical to
#: the last digit at every pi0.  A difference is a leak, not a result.
SIGNAL_BLIND = ("B1 audit-at-commit", "B2 uniform random",
                "SSG-full receding", "SSG-up receding")
GATE_PCT = 15.0


def convert(p: float, pi_from: float, pi_to: float) -> float:
    """Map a posterior computed at prior pi_from to the same evidence at pi_to."""
    if p <= 0.0 or p >= 1.0:
        return p
    lam = p * (1.0 - pi_from) / (pi_from * (1.0 - p))
    return pi_to * lam / (pi_to * lam + 1.0 - pi_to)


def converted_table(table: dict, pi_from: float, pi_to: float) -> dict:
    """The score table with every tau_sel moved to pi_to; everything else kept."""
    out = copy.deepcopy(table)
    for t in out["tables"].values():
        for row in t["rows"]:
            row["tau_sel"] = {k: convert(v, pi_from, pi_to)
                              for k, v in row["tau_sel"].items()}
    out["provenance"]["pi0"] = pi_to
    out["provenance"]["converted_from_pi0"] = pi_from
    return out


@contextlib.contextmanager
def installed_pi0(pi0: float):
    """Install pi0 on all three paths; restore every one of them on exit."""
    frozen = scoring.load_table()
    pi_from = frozen["provenance"]["pi0"]
    table = converted_table(frozen, pi_from, pi0)
    saved = (scoring.PI0, costs.PI0_WORLD, scoring.load_table,
             scoring.posterior.__defaults__, scoring.carrier_score.__defaults__)
    try:
        scoring.PI0 = costs.PI0_WORLD = pi0
        scoring.posterior.__defaults__ = (pi0,)
        scoring.carrier_score.__defaults__ = (pi0,)
        scoring.load_table = lambda: table
        yield
    finally:
        (scoring.PI0, costs.PI0_WORLD, scoring.load_table,
         scoring.posterior.__defaults__, scoring.carrier_score.__defaults__) = saved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--deltas", type=int, nargs="+", default=[2, 4])
    ap.add_argument("--detector", default="mid")
    a = ap.parse_args()

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    det, ag = detector.Detector.from_setting(a.detector), agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))
    old = costs.install(P)
    total = sum(P.KAPPA.values())
    rows = []
    try:
        for pi0 in GRID:
            with installed_pi0(pi0):
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
                        rows.append({"pi0": round(pi0, 4), "share": share, "delta": d,
                                     "harm": harm, "gain_vs_b1": gains,
                                     "best_policy": best, "best_gain": gains[best],
                                     "clears_15": gains[best] >= GATE_PCT})
                        print(f"pi0={pi0:.4f} share={share:<6} D={d}  best={best:24} "
                              f"{gains[best]:+6.1f}%", file=sys.stderr, flush=True)
    finally:
        costs.restore(P, old)

    # pi1: the signal-blind policies must not move at all.
    leaks = []
    for share in SHARES:
        for d in a.deltas:
            cell = [r for r in rows if r["share"] == share and r["delta"] == d]
            for nm in SIGNAL_BLIND:
                vals = {r["harm"][nm] for r in cell}
                if len(vals) > 1:
                    leaks.append({"share": share, "delta": d, "policy": nm,
                                  "harms": sorted(vals)})
    # pi3: is the best policy of each (share, delta) cell the same at every pi0?
    stable = {}
    for share in SHARES:
        for d in a.deltas:
            bests = [r["best_policy"] for r in rows
                     if r["share"] == share and r["delta"] == d]
            stable[f"share={share} delta={d}"] = {"best_by_pi0": bests,
                                                  "stable": len(set(bests)) == 1}
    out = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
           "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                    capture_output=True, text=True).stdout.strip(),
           "setup": {"n": a.n, "H": a.H, "seeds": a.seeds, "detector": a.detector,
                     "scale": "usd", "grid": [round(x, 4) for x in GRID],
                     "derived_pi0": round(costs.PI0_WORLD, 4),
                     "shares": list(SHARES), "policies": POLICIES,
                     "tau_sel": "converted from the frozen table (order statistics)"},
           "rows": rows,
           "pi1_signal_blind_leaks": leaks,
           "pi3_best_policy_by_cell": stable,
           "pi3_cells_stable": sum(v["stable"] for v in stable.values()),
           "pi4_cells_clearing_15_at_published_share": [
               {"pi0": r["pi0"], "delta": r["delta"], "best": r["best_policy"],
                "gain": r["best_gain"]}
               for r in rows if r["share"] == 0.3205 and r["clears_15"]]}
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
