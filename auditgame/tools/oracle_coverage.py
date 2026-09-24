#!/usr/bin/env python3
"""oracle_coverage.py -- how much of the corpus the REAL oracle can score, and why.

Spec: docs/thesis/eval/PLAN.md Part III (Task 10, Task 18); delivery group A,
"Oracle test an".

THE NUMBER THIS TOOL EXISTS TO STOP PEOPLE MISREADING.  There are two of them and
they are not the same kind of number:

    H1's 5 of 500   a property of the CORPUS.  One generic template, asked of 500
                    real gold patches, resolves an anchor on five.  It extrapolates
                    -- that is why Task 10's decision gate could read it and stop.
    R1's 15 of 500  a property of the AUTHORS.  Fifteen hand-written properties
                    anchor on the fifteen instances they were hand-written for.  It
                    extrapolates to nothing: writing thirty would make it 30.

Quoting the union (15 of 500, 3.0%) as though it were a coverage rate would be
reporting the size of an afternoon's typing as a measurement about SWE-bench.  So
this tool reports the two separately, keeps `extrapolates` as a FIELD beside each,
and reports the one claim that actually moved:

    REACHABLE   of the instances a hidden test was WRITTEN for, how many can the
                oracle score.  It was 1 of 15 and is now 15 of 15.

That is a wiring number, not a measurement.  `registry.FAMILIES` held only H1, so
fourteen properties that had cleared V1/V2/V3 on real gold patch text in Task 10b
scored nothing; `hidden_tests/r1_tier.py` registers them.  Reporting the wiring
fix as a coverage gain is exactly the move this docstring forbids.

THE COUNTERFACTUAL IS COMPUTED, NOT REMEMBERED.  "1 of 15 before" is re-derived by
running the same three levels against H1 alone, so the before/after cannot drift
apart the way two numbers in a README do.

    python3 tools/oracle_coverage.py > spikes/oracle-coverage.json
"""
from __future__ import annotations
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from hidden_tests import per_instance, registry

DATA = (pathlib.Path(__file__).resolve().parent.parent
        / "data" / "swebench_verified.jsonl")

#: Which families extrapolate, as a declared field rather than a footnote.  A
#: family added here without an answer is a family whose rate has no reading.
EXTRAPOLATES = {
    "H1": "yes -- one template asked of every instance; the rate is about the corpus",
    "R1": "no -- one property per instance, hand-written; the rate is about the authors",
}


def levels(rows: list, families: dict) -> dict:
    """The three levels of 'anchored' (registry.py) under a given family set."""
    anchored, scorable, v1 = {}, {}, []
    saved = dict(registry.FAMILIES)
    registry.FAMILIES.clear()
    registry.FAMILIES.update(families)
    try:
        for r in rows:
            iid = r["instance_id"]
            a = registry.anchor_all(r)
            if a:
                anchored[iid] = sorted(a)
            v1 += [(iid, f) for f, _ in registry.v1_failures(r)]
            o = registry.oracle_anchors(r)
            if o:
                scorable[iid] = sorted(o)
    finally:
        registry.FAMILIES.clear()
        registry.FAMILIES.update(saved)
    return {"anchored": anchored, "scorable": scorable,
            "v1_failures": sorted(v1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(DATA))
    a = ap.parse_args()

    path = pathlib.Path(a.data)
    if not path.exists():
        print(json.dumps({"error": f"no corpus at {path} -- run swebench_fetch.py"}))
        return 1
    rows = [json.loads(l) for l in
            path.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = len(rows)

    per_family = {}
    for name, fam in sorted(registry.FAMILIES.items()):
        lv = levels(rows, {name: fam})
        per_family[name] = {
            "anchored": len(lv["anchored"]),
            "anchored_pct": round(100.0 * len(lv["anchored"]) / n, 2),
            "v1_failures": len(lv["v1_failures"]),
            "scorable": len(lv["scorable"]),
            "scorable_pct": round(100.0 * len(lv["scorable"]) / n, 2),
            "extrapolates": EXTRAPOLATES.get(name, "UNDECLARED -- give this family "
                                                   "a reading before quoting its rate"),
        }

    live = levels(rows, dict(registry.FAMILIES))
    written = {t.instance_id for t in per_instance.TESTS}
    reachable_now = written & set(live["scorable"])
    h1_only = levels(rows, {"H1": registry.FAMILIES["H1"]})
    reachable_before = written & set(h1_only["scorable"])

    print(json.dumps({
        "corpus": {"path": str(path), "instances": n},
        "per_family": per_family,
        "union": {
            "anchored": len(live["anchored"]),
            "scorable": len(live["scorable"]),
            "scorable_pct": round(100.0 * len(live["scorable"]) / n, 2),
            "scored_by_both_families": sorted(
                i for i, fs in live["scorable"].items() if len(fs) > 1),
            "v1_failures": [list(x) for x in live["v1_failures"]],
        },
        "reachable": {
            "hidden_tests_written_for": len(written),
            "oracle_can_score_now": len(reachable_now),
            "oracle_could_score_before_r1_was_registered": len(reachable_before),
            "still_unreachable": sorted(written - reachable_now),
        },
        "reading": (
            "The claim that moved is REACHABLE, "
            f"{len(reachable_before)}/{len(written)} -> "
            f"{len(reachable_now)}/{len(written)}: every instance a hidden test was "
            "written for can now be scored by the oracle. The corpus rate did NOT "
            "meaningfully move and must not be quoted as though it had: H1's "
            "5/500 is a measurement about SWE-bench, R1's 15/500 is a count of "
            "hand-written properties. The live grid is still MarkerOracle-scored "
            "(no patch text in the pipeline), which the results header states."),
        "provenance": {
            "families": sorted(registry.FAMILIES),
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
