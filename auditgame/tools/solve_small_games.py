#!/usr/bin/env python3
"""solve_small_games.py -- 240 small games solved exactly, and what rho really is.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 6.

WHAT WAS MISSING.  rho is defined as max_{pi*} min_{pi in Pi} TV(pi, pi*) -- how
far the optimum can get from the nearest member of the policy library.  The
number the project has been quoting, 0.5078, was measured on the library against
ITSELF, because on the full benchmark no pi* exists to measure against.  That
answers "how spread out is the library", which is a different question, and it
cannot support the claim rho is used for: that the library covers the optima.

This supplies the optima.  240 small games, each solved exactly in the coverage
marginal form (smallgame.solve), each giving a true pi*.

TWO NUMBERS COME OUT, AND THEY DISAGREE ON PURPOSE.

  rho        distance from the optimum to the nearest library member, in the
             same averaged-TV units the 0.5078 was measured in.
  regret     the attacker value the library actually concedes, minus V*.

A library can sit far from pi* in TV and lose almost nothing (many coverages are
near-optimal), or sit close and lose a lot.  Proposition 6 bounds loss by
H * rho * range(L), so reporting rho without the regret beside it is reporting
the bound's input and not its subject.

DOUBLE ORACLE.  The specification says: if rho is large, add the optimum that is
furthest from the library and repeat until the gap closes.  That is run here,
and the resulting curve is what decides whether 28 policies is a justified
number -- the manuscript declares 28 as an INPUT and nothing has tested it.

    python3 tools/solve_small_games.py > spikes/small-games.json
"""
from __future__ import annotations
import argparse, datetime, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import smallgame as S


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rho-target", type=float, default=0.10,
                    help="double oracle stops when rho falls below this")
    ap.add_argument("--max-added", type=int, default=40)
    a = ap.parse_args()

    gs = S.games()
    solved = []
    for g in gs:
        r = S.solve(**g)
        solved.append({**g, "value": round(r["value"], 6),
                       "guaranteed_coverage": round(r["guaranteed_coverage"], 6),
                       "_pi": S.per_task(r["coverage"], g["H"], g["K"]),
                       "_cov": r["coverage"]})
    print(f"solved {len(solved)} games exactly", file=sys.stderr)

    # ---- the declared library, evaluated on every game -------------------
    def assess(extra: dict) -> dict:
        """extra: {(H,K,m): [(pi rows, coverage dict)]} added by double oracle.

        KEYED BY BUDGET TOO, and that is not cosmetic.  Keyed by (H,K) alone, a
        pi* solved at m=4 was offered as a candidate in a game with m=1, where
        it spends budget the defender does not have -- so it "beat" V* and mean
        regret came out NEGATIVE, which is impossible against an exact minimax.
        A candidate is only admissible in a game whose budget it respects.

        The coverage dict travels with every candidate, added ones included.  An
        earlier version stored None for added policies and skipped them in the
        regret line, which made regret look immovable under double oracle -- an
        artefact of the bookkeeping, not a property of the game.
        """
        rows = []
        for s in solved:
            H, K, d, m = s["H"], s["K"], s["delta"], s["m"]
            lib = S.library(H, K, m)
            cands = [(nm, S.per_task(cov, H, K), cov)
                     for nm, cov in lib.items()]
            for j, (pi, cov) in enumerate(extra.get((H, K, m), [])):
                cands.append((f"added_{j}", pi, cov))
            best_nm, best_tv = None, float("inf")
            for nm, pi, _ in cands:
                t = S.tv(pi, s["_pi"])
                if t < best_tv:
                    best_nm, best_tv = nm, t
            # regret: the best value any library member actually achieves
            best_val = min(S.value_of(cov, H, K, d) for _, _, cov in cands)
            rows.append({"H": H, "K": K, "delta": d, "m": m,
                         "V_star": s["value"],
                         "nearest": best_nm, "tv": round(best_tv, 6),
                         "library_value": round(best_val, 6),
                         "regret": round(best_val - s["value"], 6)})
        rho = max(r["tv"] for r in rows)
        worst = max(rows, key=lambda r: r["tv"])
        return {"rows": rows, "rho": round(rho, 6),
                "worst_game": {k: worst[k] for k in ("H", "K", "delta", "m")},
                "max_regret": round(max(r["regret"] for r in rows), 6),
                "mean_regret": round(sum(r["regret"] for r in rows) / len(rows), 6)}

    base = assess({})
    print(f"rho(library) = {base['rho']:.4f}   max regret = {base['max_regret']:.4f}"
          f"   mean regret = {base['mean_regret']:.4f}", file=sys.stderr)

    # ---- double oracle ---------------------------------------------------
    extra: dict = {}
    curve = [{"added": 0, "rho": base["rho"], "max_regret": base["max_regret"],
              "mean_regret": base["mean_regret"]}]
    cur = base
    while cur["rho"] > a.rho_target and len(curve) - 1 < a.max_added:
        w = cur["worst_game"]
        s = next(x for x in solved
                 if all(x[k] == w[k] for k in ("H", "K", "delta", "m")))
        extra.setdefault((w["H"], w["K"], w["m"]), []).append((s["_pi"], s["_cov"]))
        cur = assess(extra)
        curve.append({"added": len(curve),
                      "rho": cur["rho"], "max_regret": cur["max_regret"],
                      "mean_regret": cur["mean_regret"],
                      "added_game": w})
        print(f"  +1 policy (from H={w['H']} K={w['K']} d={w['delta']} m={w['m']})"
              f" -> rho {cur['rho']:.4f}", file=sys.stderr)

    n_lib = len(S.library(6, 4, 2))
    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "setup": {"n_games": len(gs), "K_times_H_max": max(g["K"] * g["H"] for g in gs),
                  "ceiling": 40, "library_size": n_lib,
                  "rho_target": a.rho_target,
                  "tv": "averaged over tasks, same convention as tools/measure_rho.py"},
        "draft_reference": {"rho": 0.07, "proposition6_bound": 0.42,
                            "regret_measured": 0.09,
                            "library_size_declared": 28},
        "rho_library_vs_optima": base["rho"],
        "max_regret": base["max_regret"],
        "mean_regret": base["mean_regret"],
        "worst_covered_game": base["worst_game"],
        "double_oracle_curve": curve,
        "policies_needed_for_target": (curve[-1]["added"]
                                       if curve[-1]["rho"] <= a.rho_target
                                       else None),
        "games": [{k: v for k, v in s.items() if not k.startswith("_")}
                  for s in solved],
        "per_game": base["rows"],
    }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
