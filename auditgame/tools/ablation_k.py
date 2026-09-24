#!/usr/bin/env python3
"""ablation_k.py -- does any conclusion depend on there being FOUR carriers?

Spec: docs/preregistration/TIEN-DANG-KY-W10-bien-ho-tham-so.md section 2.

A REMOVED CARRIER LEAVES THE GAME.  The attacker cannot seed it, and the
defender can neither see nor audit it.  Passing a subset to runner.worst_case is
NOT that: its `carriers` argument narrows only the ATTACKER, while every policy
still spreads over the four names it imported from core.  So the subset is
installed on the modules that read CARRIERS for decisions -- every loaded module
except the ones that STORE items (core, build, m3, carrier_store_fs), because
the workflow generator writes benign items into all four carriers and those
items simply go unread.

WHAT IS HELD FIXED.  kappa_commit = sum of the remaining kappas, the same
definition K = 4 uses (a commit audit scores every carrier that exists), and the
budget is the SAME SHARE of the remaining bill.  chi is NOT held: removing a
carrier changes the cost spread, and that is declared rather than hidden.

    python3 tools/ablation_k.py > spikes/frozen/ablation-k.json
"""
from __future__ import annotations
import argparse, contextlib, datetime, importlib, itertools, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent, core, costs, detector, experiment, policies as P, runner

SHARES = (0.3205, 0.75)
POLICIES = ["B1 audit-at-commit", "B2 uniform random", "SSG-full receding",
            "SSG-up receding", "SSG-G guarded", "SentinelW window-belief"]
SSG_FAMILY = {"SSG-full receding", "SSG-up receding", "SSG-G guarded"}
#: Modules that STORE items per carrier.  Shrinking their CARRIERS makes the
#: workflow generator raise on the benign items it writes to the removed ones.
STORAGE = {"core", "build", "m3", "carrier_store_fs"}
#: Imported up front so a lazily-imported module cannot keep the four-carrier
#: tuple it would otherwise bind on first use, mid-run.
DECIDERS = ("policies", "runner", "belief", "attackers", "lp", "theory",
            "policies_library", "attacks", "agents", "replay")
GATE_PCT = 15.0


@contextlib.contextmanager
def only_carriers(subset: tuple):
    """Install `subset` wherever CARRIERS drives a decision; restore on exit."""
    for name in DECIDERS:
        with contextlib.suppress(ImportError):
            importlib.import_module(name)
    full = core.CARRIERS
    touched = [m for m in list(sys.modules.values())
               if getattr(m, "CARRIERS", None) is full
               and m.__name__ not in STORAGE]
    old_commit = P.KAPPA_COMMIT
    try:
        for m in touched:
            m.CARRIERS = subset
        P.KAPPA_COMMIT = sum(P.KAPPA[c] for c in subset)
        yield [m.__name__ for m in touched]
    finally:
        for m in touched:
            m.CARRIERS = full
        P.KAPPA_COMMIT = old_commit


def subsets():
    full = core.CARRIERS
    yield full
    for k in (3, 2):
        yield from itertools.combinations(full, k)


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
    rows, patched = [], None
    try:
        for sub in subsets():
            with only_carriers(sub) as patched:
                bill = sum(P.KAPPA[c] for c in sub)
                for share in SHARES:
                    budget = share * a.H * bill
                    for d in a.deltas:
                        harm = {}
                        for nm in POLICIES:
                            runner.reset_survivor_cache()
                            c = runner.worst_case(nm, wfs, (d,), sub, det, ag,
                                                  budget, seeds, a.detector)
                            harm[nm] = round(c.harm, 4)
                        b1 = harm["B1 audit-at-commit"]
                        gains = {nm: (round(100.0 * (b1 - harm[nm]) / b1, 2)
                                      if b1 else None)
                                 for nm in POLICIES if nm != "B1 audit-at-commit"}
                        best = max((k for k in gains if gains[k] is not None),
                                   key=lambda k: gains[k], default=None)
                        rows.append({"K": len(sub), "carriers": list(sub),
                                     "share": share, "delta": d, "harm": harm,
                                     "gain_vs_b1": gains, "best_policy": best,
                                     "best_gain": gains.get(best)})
                        print(f"K={len(sub)} {'+'.join(sub):28} share={share:<6} "
                              f"D={d}  best={best} {gains.get(best)}",
                              file=sys.stderr, flush=True)
    finally:
        costs.restore(P, old)

    def pick(k, share, d):
        return [r for r in rows if r["K"] == k and r["share"] == share and r["delta"] == d]

    up = "SSG-up receding"
    k2 = {d: sum(r["gain_vs_b1"][up] is not None and r["gain_vs_b1"][up] >= GATE_PCT
                 for r in pick(3, 0.75, d)) for d in a.deltas}
    k3 = [r["carriers"] for r in rows
          if r["K"] == 3 and r["share"] == 0.75 and r["best_policy"] not in SSG_FAMILY]

    def spread(k):
        g = [r["gain_vs_b1"][up] for r in pick(k, 0.75, 4) if r["gain_vs_b1"][up] is not None]
        return round(max(g) - min(g), 2) if g else None

    out = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
           "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                    capture_output=True, text=True).stdout.strip(),
           "setup": {"n": a.n, "H": a.H, "seeds": a.seeds, "detector": a.detector,
                     "scale": "usd", "shares": list(SHARES), "policies": POLICIES,
                     "kappa_commit": "sum of the remaining carriers' kappa",
                     "budget": "share * H * sum of the remaining carriers' kappa",
                     "modules_patched": patched},
           "rows": rows,
           "K2_ssg_up_clears_15_at_0.75_of_4_triples": k2,
           "K3_triples_where_best_is_outside_ssg_family": k3,
           "K4_spread_ssg_up_0.75_delta4": {"K=3": spread(3), "K=2": spread(2)}}
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
