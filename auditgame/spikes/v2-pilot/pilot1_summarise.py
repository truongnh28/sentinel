"""Reduce pilot1.json (raw per-run tuples, ~15 MB) to pilot1-summary.json: per (rho, policy,
column) the mean harm, false blocks, lost tasks and L, and n.  Only the summary is kept."""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
raw = json.loads((HERE / "pilot1.json").read_text())
out = {}
for rho, pols in raw.items():
    for pol, cols in pols.items():
        for col, runs in cols.items():
            n = len(runs)
            out.setdefault(rho, {}).setdefault(pol, {})[col] = {
                "n": n, "harm": sum(r[0] for r in runs) / n, "q_false": sum(r[1] for r in runs) / n,
                "t_lost": sum(r[2] for r in runs) / n, "L": sum(r[3] for r in runs) / n}
(HERE / "pilot1-summary.json").write_text(json.dumps(out, sort_keys=True, separators=(",", ":")))
print("wrote pilot1-summary.json")
