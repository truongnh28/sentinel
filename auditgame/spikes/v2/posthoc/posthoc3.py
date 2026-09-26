#!/usr/bin/env python3
"""POST HOC readout #3 (26/09, answering a third critique round). No simulation.

Sentinel-A1 at every eta_Q of the line-8 sweep (main run, sweep-eta.jsonl, mixtures fixed) against
the D35 arm "B2 FQ-matched" (d35-main.jsonl): worst-case harm V and FQ% of both, and the paired
98.75% interval of V(B2 FQ-matched) - V(Sentinel-A1 at eta_Q).  Both files hold the same episodes
(headline cell: mid, Delta in {4, 8}, 7 held-out attackers, 57 eval workflows, seeds 1-10); the
script checks that, and both files' sha256 against their pins.  Every number here is POST HOC:
eta_Q other than the tuned value was never the configuration Sentinel-A1 committed to.

Writes posthoc3.json next to this script.  From auditgame/: python3 spikes/v2/posthoc/posthoc3.py
"""
import hashlib
import json
import pathlib
import sys

V2 = pathlib.Path(__file__).resolve().parent.parent            # auditgame/spikes/v2
ADD = V2.parent / "v2-addendum"                                # auditgame/spikes/v2-addendum
sys.path.insert(0, str(V2.parent.parent))                      # auditgame/
import metrics_v2 as MV                                        # noqa: E402

OUT = pathlib.Path(__file__).parent / "posthoc3.json"
HELD_OUT = ["branch-first-write-e0.6", "memory-last-ingress-e0.3", "memory-last-write-e0.6",
            "memory-mid-write-e0.3", "queue-last-ingress-e0.6", "queue-mid-write-e0.6", "skill-last-write-e1.0"]
HD = [4, 8]
B2F = "B2 FQ-matched"
ALPHA = 0.05 / 4                                               # 98.75%, as the D35 arms


def pinned(path, pin_file):
    pins = {l.split()[1]: l.split()[0] for l in pin_file.read_text().splitlines()
            if l and not l.startswith("#")}
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == pins[path.name], f"{path.name} differs from its pin"
    return pins[path.name], data


sha_eta, eta_bytes = pinned(V2 / "sweep-eta.jsonl", V2 / "eval-records.sha256")
sha_add, add_bytes = pinned(ADD / "d35-main.jsonl", ADD / "d35-records.sha256")

recs = {}                                                      # rho -> [records]
for ln in eta_bytes.decode().splitlines():
    r = json.loads(ln)
    if r["policy"] == "Sentinel-A1" and r["delta"] in HD and r["attack"] in HELD_OUT:
        recs.setdefault(f"{r['rho_patch']:g}", []).append({**r, "policy": f"S@{r['eta_q']:g}"})
for ln in add_bytes.decode().splitlines():
    r = json.loads(ln)
    if r["policy"] == B2F:
        recs.setdefault(f"{r['rho_patch']:g}", []).append(r)

out = {"post_hoc": True, "sha256_sweep_eta": sha_eta, "sha256_d35_main": sha_add, "alpha": ALPHA,
       "by_rho": {}}
for rho, rs in sorted(recs.items()):
    eps = {}
    for r in rs:
        eps.setdefault(r["policy"], set()).add((r["wf"], r["attack"], r["delta"], r["seed"]))
    names = sorted(p for p in eps if p.startswith("S@"))
    assert all(eps[p] == eps[B2F] for p in names), f"rho {rho}: episode sets differ"
    b2 = {"V": MV.value(MV.harm_table(rs, B2F, HELD_OUT, HD)),
          "FQ": MV.side(rs, B2F, HELD_OUT, HD)["false_quarantine_pct"]}
    rows = {}
    for p in names:
        v = MV.value(MV.harm_table(rs, p, HELD_OUT, HD))
        fq = MV.side(rs, p, HELD_OUT, HD)["false_quarantine_pct"]
        ci = MV.gain_ci(rs, B2F, p, HELD_OUT, HD, alpha=ALPHA)
        rows[p[2:]] = {"V": v, "FQ": fq,
                       "b2_minus_s": {k: ci[k] for k in ("abs_diff", "abs_lo", "abs_hi")},
                       "dominates": v < b2["V"] and fq < b2["FQ"]}
    out["by_rho"][rho] = {"B2 FQ-matched": b2, "sentinel_by_eta": rows,
                          "n_episodes": len(eps[B2F])}

OUT.write_text(json.dumps(out, indent=1, sort_keys=True))
print("wrote", OUT)
