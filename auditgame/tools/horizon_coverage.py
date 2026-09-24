#!/usr/bin/env python3
"""horizon_coverage.py -- which horizon H do the MEASURED delays call for?

Spec: docs/preregistration/TIEN-DANG-KY-W10-bien-ho-tham-so.md section 3.

An attack with trigger delay Delta fits a workflow of H tasks only if
Delta <= H - 1: the insertion task and the trigger task both have to be inside
it.  So H is justified by the share of REAL delays it can hold, read per
repository from spikes/delta-swebench.json (SZZ-style, in task units).  Pooling
is refused for the same reason that file refuses it: django is 231/500 of
SWE-bench Verified, so a pooled share is django's share.

Declared criterion: H covers >= 90% of the measured Delta in EVERY repository
with n >= 10.  No prediction -- this describes data already measured.

    python3 tools/horizon_coverage.py > spikes/frozen/horizon-coverage.json
"""
from __future__ import annotations
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCE = HERE / "spikes" / "delta-swebench.json"
GRID = (4, 6, 8, 10, 12, 13, 16)
TARGET = 0.90
MIN_N = 10


def coverage(dist, H):
    return sum(d <= H - 1 for d in dist) / len(dist)


def main() -> int:
    src = json.loads(SOURCE.read_text(encoding="utf-8"))["per_repo"]
    repos = {r: v["distribution"] for r, v in src.items() if v["n"] >= MIN_N}
    table = {r: {str(H): round(coverage(dist, H), 3) for H in GRID}
             for r, dist in repos.items()}
    worst = {str(H): min(table[r][str(H)] for r in repos) for H in GRID}
    meets = [H for H in GRID if worst[str(H)] >= TARGET]
    need = {r: next((H for H in range(1, 64) if coverage(d, H) >= TARGET), None)
            for r, d in repos.items()}
    out = {"source": str(SOURCE.relative_to(HERE)), "criterion":
           f"Delta <= H-1 for >= {TARGET:.0%} of instances in every repo with n >= {MIN_N}",
           "coverage_by_repo": table, "worst_repo_coverage": worst,
           "smallest_H_per_repo": need,
           "smallest_H_meeting_criterion": min(meets) if meets else None,
           "H8_meets_criterion": worst["8"] >= TARGET,
           "repos_H8_fails": sorted(r for r in repos if table[r]["8"] < TARGET)}
    json.dump(out, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
