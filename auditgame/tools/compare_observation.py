#!/usr/bin/env python3
"""compare_observation.py -- M0 vs MA, computed from the two grid files.

Spec: docs/preregistration/TIEN-DANG-KY-mo-hinh-quan-sat-MA.md, predictions MA1
and MA2.  Replaces the hand-built comparison of 24/09 so the JSON can be
regenerated whenever the grids are (README #20 moved both).

    python3 tools/compare_observation.py spikes/frozen/grid-usd-H8.txt \
        spikes/grid-usd-H8-observation-MA.txt > spikes/observation-M0-vs-MA.json
"""
from __future__ import annotations
import datetime, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from grid_summary import parse  # noqa: E402

TRACKED = ("SSG-full receding", "SSG-up receding", "SSG-G guarded", "Sentinel",
           "SentinelW window-belief", "SSG-B belief-weighted")


def main(m0_path: str, ma_path: str) -> int:
    m0, ma = parse(m0_path), parse(ma_path)
    up = down = same = 0
    moved, falls = set(), []
    for det in m0:
        for pol, cells in m0[det].items():
            for d, h0 in cells.items():
                h1 = ma[det][pol][d]
                if h1 != h0:
                    moved.add(pol)
                    if h1 > h0:
                        up += 1
                    else:
                        down += 1
                        falls.append({"detector": det, "policy": pol, "delta": d,
                                      "M0": h0, "MA": h1})
                elif pol not in ("B1 audit-at-commit",):
                    same += 1
    b1_same = all(m0[det]["B1 audit-at-commit"] == ma[det]["B1 audit-at-commit"]
                  for det in m0)

    def gain(g, det, pol, d):
        b = g[det]["B1 audit-at-commit"][d]
        return round(100.0 * (b - g[det][pol][d]) / b, 1) if b else None

    delta4 = {det: {pol: {"M0": gain(m0, det, pol, 4), "MA": gain(ma, det, pol, 4)}
                    for pol in TRACKED if pol in m0[det]} for det in m0}
    readers = sorted(moved)
    same_cells = sum(len(m0[det][pol]) for det in m0 for pol in readers) - up - down
    out = {"prereg": "docs/preregistration/TIEN-DANG-KY-mo-hinh-quan-sat-MA.md",
           "MA1_harm_never_falls": {"verdict": "REFUTED" if down else "HOLDS",
                                    "cells_up": up, "cells_down": down,
                                    "cells_same_among_moved_policies": same_cells,
                                    "largest_falls": sorted(falls, key=lambda x: x["MA"] - x["M0"])[:5]},
           "MA2_B1_identical": b1_same,
           "policies_moved_by_MA": readers,
           "policies_unchanged": sorted({p for det in m0 for p in m0[det]} - moved),
           "gain_vs_B1_delta4_pct": delta4,
           "caveat": "N = 40 workflows x 3 seeds, point estimates, no CI.",
           "provenance": {"date": datetime.date.today().isoformat(),
                          "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                                   text=True).stdout.strip(),
                          "runs": [m0_path + " (M0)", ma_path + " (MA)"]}}
    json.dump(out, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
