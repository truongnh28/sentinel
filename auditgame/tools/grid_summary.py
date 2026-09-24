#!/usr/bin/env python3
"""grid_summary.py -- read an experiment.py grid file back as numbers.

The grid files are the published artefact, so the comparisons README makes
between them (M0 vs MA, H = 8 vs H = 12, corpus split of #15) are computed from
the files rather than transcribed by hand.  Prints JSON: harm per
(detector, policy, Delta), gain vs B1 per cell, and the cells >= 15%.

    python3 tools/grid_summary.py spikes/frozen/grid-usd-H8.txt [other.txt ...]
"""
from __future__ import annotations
import json, re, sys

GATE_PCT = 15.0
_DET = re.compile(r"^\[detector = (\w+)\]")
_HEAD = re.compile(r"^\s+policy\s+((?:D=\d+\s*)+)$")
_ROW = re.compile(r"^\s{2}(\S.*?\S)\s{2,}((?:[01]\.\d{3}\s*)+)$")


def parse(path: str) -> dict:
    out, det, deltas = {}, None, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = _DET.match(line)
        if m:
            det, deltas = m.group(1), None
            continue
        m = _HEAD.match(line)
        if m and det:
            deltas = [int(x[2:]) for x in m.group(1).split()]
            continue
        if det and deltas:
            m = _ROW.match(line)
            if m:
                vals = [float(x) for x in m.group(2).split()]
                if len(vals) == len(deltas):
                    out.setdefault(det, {})[m.group(1)] = dict(zip(deltas, vals))
            elif not line.strip():
                deltas = None
    return out


def summarise(path: str) -> dict:
    g = parse(path)
    gains, clears = {}, []
    for det, rows in g.items():
        b1 = rows.get("B1 audit-at-commit")
        if not b1:
            continue
        for pol, cells in rows.items():
            if pol == "B1 audit-at-commit":
                continue
            for d, h in cells.items():
                if b1[d]:
                    gv = round(100.0 * (b1[d] - h) / b1[d], 1)
                    gains.setdefault(det, {}).setdefault(pol, {})[d] = gv
                    if gv >= GATE_PCT:
                        clears.append({"detector": det, "policy": pol, "delta": d, "gain": gv})
    return {"file": path, "harm": g, "gain_vs_b1": gains, "cells_ge_15": clears}


if __name__ == "__main__":
    json.dump([summarise(p) for p in sys.argv[1:]], sys.stdout, indent=1)
    print()
