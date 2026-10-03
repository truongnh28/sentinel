#!/usr/bin/env python3
"""tools/quick_summary.py -- a short table from one tools/v3_run.py output directory.

    cd auditgame
    ../.venv/bin/python tools/quick_summary.py spikes/v3-run/quick-<time>

For each rho of the headline cell (chi = 1.33, d' = 2.21, K_d = 2, budget b1), the 7 held-out
attackers and Delta in {4, 8}: worst-case loss L (Definition 1) and worst-case harm V of every
system, and the gain of Sentinel over B1 with the family-cluster bootstrap of v3/metrics.py.
Nothing is reimplemented: the table is metrics.table / metrics.gain_ci, and L is relabelled
into the scored field as tools/v3_p5_h18_heldout.as_metric does.

On a quick dev run (few workflows, one seed) the numbers only check that the pipeline runs end to
end.  On spikes/v3-run/eval-pass1 with --n-boot 10000 it reproduces the held-out main table.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent           # auditgame/
sys.path.insert(0, str(HERE))

from v3 import attackers as A                                     # noqa: E402
from v3 import config as C                                        # noqa: E402
from v3 import metrics as M                                       # noqa: E402
from v3 import runner as R                                        # noqa: E402

B1 = "B1 audit-at-commit"
SENTINEL = "Sentinel"
HELD_OUT = tuple(A.held_out())
DELTAS = tuple(C.HEADLINE_DELTAS)                                 # (4, 8)
HEADLINE = {"chi": C.CHI_PRIMARY, "dprime": C.DPRIME_PRIMARY, "k_delegated": 2,
            "budget": "b1", "price_only": False}


def load(run_dir: pathlib.Path) -> list:
    rows = []
    for f in sorted(run_dir.glob("main*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if any(r["cell"].get(k) != v for k, v in HEADLINE.items()):
                    continue
                rows.append({k: r[k] for k in ("policy", "attack", "delta", "wf", "seed",
                                               "repo", "split", "harm", "fq", "t_lost")}
                            | {"rho": r["cell"]["rho"], "loss": R.loss_of(r)})
    return rows


def fmt(x, n=3) -> str:
    return "  n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir", type=pathlib.Path)
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args(argv)
    rows = load(a.run_dir)
    if not rows:
        print(f"no headline records in {a.run_dir}")
        return 1
    systems = sorted({r["policy"] for r in rows}, key=lambda p: (p != B1, p != SENTINEL, p))
    n_wf = len({r["wf"] for r in rows})
    n_seed = len({r["seed"] for r in rows})
    print(f"{a.run_dir}: {len(rows):,} headline records, {n_wf} workflows, {n_seed} seed(s), "
          f"split {rows[0]['split']}")
    if rows[0]["split"] == "dev":
        print("Dev run: checks the pipeline, not a result.")
    print()
    for rho in sorted({r["rho"] for r in rows}):
        rs = [r for r in rows if r["rho"] == rho]
        as_l = [{**r, "harm": r["loss"]} for r in rs]
        print(f"rho = {rho}")
        print(f"  {'system':36s} {'V(L)':>7s} {'V(harm)':>8s}")
        for p in systems:
            vl = M.table(as_l, p, HELD_OUT, DELTAS).value
            vh = M.table(rs, p, HELD_OUT, DELTAS).value
            print(f"  {p:36s} {fmt(vl):>7s} {fmt(vh):>8s}")
        if {B1, SENTINEL} <= set(systems):
            for name, recs in (("L", as_l), ("harm", rs)):
                g = M.gain_ci(recs, B1, SENTINEL, HELD_OUT, DELTAS, n_boot=a.n_boot)
                print(f"  Sentinel vs B1, gain on {name:4s}: {fmt(g['gain'], 1)}% "
                      f"[{fmt(g['lo'], 1)}; {fmt(g['hi'], 1)}]")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
