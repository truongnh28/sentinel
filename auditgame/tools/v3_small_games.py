#!/usr/bin/env python3
"""v3_small_games.py -- H7 on the 240 small games: B7 (exact minimax), the 28 members
ported, regret against B7 and the covering radius against pi* (plan T21).

Draft S10.2: "On the 240 exactly-solvable small games, Sentinel's empirical regret against
the minimax value (B7) is 0.09 in normalised harm, against Proposition 6's worst-case bound
of 0.42 at the measured covering radius rho = 0.07".  sentinel-v3.md H7: measured only on
the small games, against pi*, the 28 members ported, the radius the uniform TV over every
history (theory note Def. 4.1 / Prop. 4.2 / Remark 4.3).  v2's spikes/v2/small-games.json
recorded a MEAN TV over tasks on an 8-policy library; this is the uniform one on the 28.

Per game (v3/smallgame_v3.assess):
    V_star                 B7's value (exact LP over every schedule; `certificate` is the
                           attacker's dual value, equal to V_star at optimum)
    V_v2_marginal          v2's coverage-marginal value, for comparison
    V_mixture, V_single    the library's minimax value over mixtures / single members
    regret_mixture         V_mixture - V_star   ("regret against B7")
    radius_single          min over members of d(member, pi*_LP)
    radius_mixture         min over mixtures of d(mix, pi*_LP)
    radius_refined         (--refine) the smallest d(mix, pi*) found over minimax pi*
    radius                 the smallest radius found against a genuine minimax pi*
    prop42_bound           H * radius * range(L), range(L) = 1

Summary (stderr, and "summary" in the JSON): the covering radius is a sup, so the headline
is its MAX over games; mean and median beside it; each split by budget regime (m >= H: the
budget never binds, like b1 in the v3 grid; m < H: it binds).  Prop. 4.2 is checked on
every game (regret <= H radius).

    cd auditgame
    ../.venv/bin/python tools/v3_small_games.py --refine --jobs 8 > /tmp/v3-small-games.json

Runs on the small games only; touches no dev or eval data.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import statistics as st
import subprocess
import sys
from multiprocessing import Pool

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from v3 import smallgame_v3 as S

KEYS_SUMMARY = ("regret_mixture", "regret_single", "radius_single", "radius_mixture",
                "radius", "prop42_bound")


def _assess(args):
    g, refine = args
    return S.assess(g, refine=refine)


def _stats(rows: list, key: str) -> dict | None:
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    if not vals:
        return None
    return {"n": len(vals), "max": round(max(vals), 6), "mean": round(st.mean(vals), 6),
            "median": round(st.median(vals), 6), "min": round(min(vals), 6)}


def summarise(rows: list) -> dict:
    regimes = {"all": rows,
               "budget_lax_m_ge_H": [r for r in rows if r["m"] >= r["H"]],
               "budget_binds_m_lt_H": [r for r in rows if r["m"] < r["H"]]}
    keys = KEYS_SUMMARY + (("radius_refined",) if any("radius_refined" in r for r in rows)
                           else ())
    out = {name: {k: _stats(rs, k) for k in keys} for name, rs in regimes.items()}
    out["exact"] = {
        "certified": sum(abs(r["certificate"] - r["V_star"]) <= 1e-7 for r in rows),
        "v2_marginal_below_exact": sum(r["V_v2_marginal"] < r["V_star"] - 1e-9 for r in rows),
        "library_below_exact": sum(r["V_mixture"] < r["V_star"] - 1e-9 for r in rows)}
    out["prop42_holds"] = sum(r["regret_mixture"] <= r["prop42_bound"] + 1e-6 for r in rows)
    out["radius_zero"] = sum(r["radius"] <= 1e-6 for r in rows)
    out["literal_radius_floor_min"] = round(min(r["literal_radius_floor"] for r in rows), 6)
    worst = max(rows, key=lambda r: r["radius"])
    out["worst_radius_game"] = {k: worst[k] for k in ("H", "K", "delta", "m", "radius")}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refine", action="store_true",
                    help="also search the minimax set for the pi* nearest the library")
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args()

    gs = S.games()
    work = [(g, a.refine) for g in gs]
    if a.jobs > 1:
        with Pool(a.jobs) as pool:
            rows = pool.map(_assess, work, chunksize=1)
    else:
        rows = [_assess(w) for w in work]
    summ = summarise(rows)

    def r6(v):
        return round(float(v), 6) if isinstance(v, float) or hasattr(v, "dtype") else v

    for name in ("all", "budget_lax_m_ge_H", "budget_binds_m_lt_H"):
        s = summ[name]
        print(f"[{name}] n={s['radius']['n']}", file=sys.stderr)
        for k in ("regret_mixture", "radius_mixture", "radius", "prop42_bound"):
            v = s[k]
            print(f"   {k:16s} max {v['max']:.4f}  mean {v['mean']:.4f}  median {v['median']:.4f}",
                  file=sys.stderr)
    print(f"exact: {summ['exact']}; Prop. 4.2 holds on {summ['prop42_holds']}/{len(rows)}; "
          f"radius 0 on {summ['radius_zero']}; worst {summ['worst_radius_game']}",
          file=sys.stderr)

    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "setup": {"n_games": len(gs), "library": "v3/library.py, 28 members ported",
                  "small_p0": S.SMALL_P0, "game_targets": {str(k): v for k, v in
                                                            S.GAME_TARGETS.items()},
                  "tv": "uniform over every history both policies reach (Def. 4.1)",
                  "refine": a.refine, "range_L": 1.0},
        "draft_reference": {"regret_vs_B7": 0.09, "radius": 0.07, "prop6_bound": 0.42},
        "summary": summ,
        "per_game": [{k: r6(v) for k, v in r.items()} for r in rows],
    }
    json.dump(out, sys.stdout, indent=2, default=float)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
