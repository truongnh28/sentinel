#!/usr/bin/env python3
"""power_n_seeds.py -- how many workflows, and how many seeds, does a claim need?

Spec: docs/preregistration/TIEN-DANG-KY-W10-bien-ho-tham-so.md section 4.

N.  The workflow is the unit of resampling (certified_power.gain_ci), so the CI
half-width shrinks as sqrt(100/N) from its measured value at N = 100.  The N a
cell NEEDS is the smallest N at which its point gain, if true, still puts the
lower bound above the 15% gate.  Read straight from the frozen N = 100 files;
nothing is re-run for this half.

SEEDS.  Seeds average INSIDE a workflow before it is resampled, so extra seeds
only help if seed noise is a visible share of the between-workflow spread.
Measured directly: the headline cell's CI on the SAME 100 workflows with 1, 3
and 5 seeds.

    python3 tools/power_n_seeds.py > spikes/frozen/power-n-seeds.json
"""
from __future__ import annotations
import datetime, json, math, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import agent, costs, detector, experiment, policies as P, runner
from core import CARRIERS
from certified_power import gain_ci

GATE_PCT = 15.0
SOURCES = ("certified-power-share-0.5.json", "certified-power-share-0.75.json",
           "certified-power.json")
HEADLINE = {"share": 0.75, "delta": 2, "detector": "mid", "policy": "SSG-up receding"}
#: Nested sets answer "does the CI narrow"; the single seeds 2..5 answer the
#: question the nested sets raised on the first run -- the point gain FELL as
#: seeds were added (44.3 -> 35.7 -> 32.5), which is either a few unlucky seeds
#: or a systematic effect of averaging seeds inside a per-workflow max.
SEED_SETS = ((1,), (1, 2, 3), (1, 2, 3, 4, 5), tuple(range(1, 11)),
             (2,), (3,), (4,), (5,))


def n_needed(cell: dict, n_ref: int) -> int | None:
    hw = (cell["hi"] - cell["lo"]) / 2.0
    margin = cell["gain"] - GATE_PCT
    if margin <= 0 or hw <= 0:
        return None
    return math.ceil(n_ref * (hw / margin) ** 2)


def main() -> int:
    power = []
    for name in SOURCES:
        f = HERE / "spikes" / "frozen" / name
        if not f.exists():
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        share = doc["setup"].get("budget_share", 0.3205)
        for c in doc["cells"]:
            if c.get("gate") != "certified":
                continue
            power.append({"source": name, "share": share, "detector": c["detector"],
                          "delta": c["delta"], "policy": c["policy"], "gain": c["gain"],
                          "ci": [c["lo"], c["hi"]], "n_ref": c["n_workflows"],
                          "n_needed": n_needed(c, c["n_workflows"])})

    h = HEADLINE
    wfs = experiment.make_corpus(100, 8, seed=2026)
    det, ag = detector.Detector.from_setting(h["detector"]), agent.MockAgent()
    old = costs.install(P)
    budget = h["share"] * 8 * sum(P.KAPPA.values())
    seeds_rows = []
    try:
        for s in SEED_SETS:
            runner.reset_survivor_cache()
            b = runner.worst_case("B1 audit-at-commit", wfs, (h["delta"],), CARRIERS,
                                  det, ag, budget, s, h["detector"])
            runner.reset_survivor_cache()
            c = runner.worst_case(h["policy"], wfs, (h["delta"],), CARRIERS,
                                  det, ag, budget, s, h["detector"])
            ci = gain_ci(b.per_wf, c.per_wf)
            seeds_rows.append({"seeds": len(s), "seed_ids": list(s), **ci,
                               "half_width": round((ci["hi"] - ci["lo"]) / 2, 2)})
            print(f"seeds={len(s)} {ci}", file=sys.stderr, flush=True)
    finally:
        costs.restore(P, old)

    hw = {r["seeds"]: r["half_width"] for r in seeds_rows if r["seed_ids"][0] == 1}
    head = next((p for p in power if p["share"] == h["share"] and p["delta"] == h["delta"]
                 and p["detector"] == h["detector"] and p["policy"] == h["policy"]), None)
    out = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
           "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                    capture_output=True, text=True).stdout.strip(),
           "gate_pct": GATE_PCT, "n_needed_by_cell": power, "headline": h,
           "seeds": seeds_rows,
           "S1_half_width_change_3_to_5_pct": (
               round(100 * abs(hw[5] - hw[3]) / hw[3], 1) if hw.get(3) else None),
           "S2_headline_n_needed": head["n_needed"] if head else None}
    json.dump(out, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
