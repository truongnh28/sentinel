#!/usr/bin/env python3
"""compare_horizon_corpus.py -- issue #15, computed from the grid files.

Spec: docs/preregistration/TIEN-DANG-KY-tach-chan-troi-khoi-corpus.md.  Same
H = 8, two corpora (generated at H = 8, and generated at H = 12 then truncated):
if the decisive cell moves between them, the H = 8 / H = 12 gap was the corpus,
not the horizon (H2).  Replaces the hand-built JSON of 24/09 (README #20).

    python3 tools/compare_horizon_corpus.py spikes/frozen/grid-usd-H8.txt \
        spikes/grid-usd-H8-from-H12-corpus.txt spikes/grid-usd-H12-delta8.txt \
        > spikes/horizon-vs-corpus.json
"""
from __future__ import annotations
import datetime, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from grid_summary import summarise  # noqa: E402

DECISIVE = ("mid", 4, "SSG-full receding")
TRACKED = ("SSG-full receding", "SSG-G guarded", "Sentinel")
#: The pre-registration's thresholds on g = the decisive cell on the truncated
#: corpus, declared before the run and ABSOLUTE: H1 if g >= 12, H2 if g <= 8,
#: H3 ("cannot be decided at N = 40") in between.


def verdict(g: float) -> str:
    return "H1" if g >= 12.0 else "H2" if g <= 8.0 else "H3"


def main(h8: str, h8_from_h12: str, h12: str) -> int:
    a, b = summarise(h8)["gain_vs_b1"], summarise(h8_from_h12)["gain_vs_b1"]
    c = summarise(h12)["gain_vs_b1"]
    det, d, pol = DECISIVE
    out = {"prereg": "docs/preregistration/TIEN-DANG-KY-tach-chan-troi-khoi-corpus.md",
           "decisive_cell": {"detector": det, "delta": d, "policy": pol,
                             "corpus_H8": a[det][pol][d], "corpus_H12_truncated": b[det][pol][d]},
           "published_H12_value": c[det][pol].get(d),
           "verdict": verdict(b[det][pol][d]),
           "gains_pct": {dt: {p: {f"D{x}": {"corpus_H8": a[dt][p][x],
                                            "corpus_H12_truncated": b[dt][p][x]}
                                  for x in a[dt][p]} for p in TRACKED} for dt in a},
           "provenance": {"date": datetime.date.today().isoformat(),
                          "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                                   text=True).stdout.strip(),
                          "runs": [h8, h8_from_h12, h12]}}
    json.dump(out, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:4]))
