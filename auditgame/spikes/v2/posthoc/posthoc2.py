#!/usr/bin/env python3
"""POST HOC readouts #2 (25/09, answering an external critique of the paper draft). No simulation.

Reads the pinned records of the single eval run and re-summarises them with the pinned metric
code (metrics_v2, metrics.loss).  Nothing is tuned; no policy is re-run.  Every number written
here is POST HOC and must be labelled so wherever it is used.

1. Loss L by eta_Q.  sweep-eta.jsonl (Sentinel-A1 at each eta_Q of the grid, mixtures fixed) and
   the main grid's B1 at the same cell: worst-case L of each, and the lambda_Q at which
   Sentinel's worst-case L equals B1's (lambda_T fixed at metrics.LAMBDA_T).
2. Leave-one-repo-out.  eval-main.jsonl, headline cell (mid, Delta in {4, 8}, held-out): the
   gain of Sentinel-A1 over B1 with each repository removed; with sympy removed, the 98.75%
   interval (alpha = 0.05 / 4, D25) of the pinned bootstrap.
3. V against FQ.  Every policy of the main grid at the headline cell, and Sentinel-A1 at every
   eta_Q: which points no other point beats on both V and FQ.
4. D30 sensitivity at 98.75%.  The eta_Q grid's lowest lower bound, at alpha = 0.05 / 4.

Writes posthoc2.json next to this script.  From auditgame/: python3 spikes/v2/posthoc/posthoc2.py
"""
import hashlib
import json
import pathlib
import sys

V2 = pathlib.Path(__file__).resolve().parent.parent            # auditgame/spikes/v2
sys.path.insert(0, str(V2.parent.parent))                      # auditgame/
import metrics as M                                            # noqa: E402
import metrics_v2 as MV                                        # noqa: E402

OUT = pathlib.Path(__file__).parent / "posthoc2.json"
HELD_OUT = ["branch-first-write-e0.6", "memory-last-ingress-e0.3", "memory-last-write-e0.6",
            "memory-mid-write-e0.3", "queue-last-ingress-e0.6", "queue-mid-write-e0.6", "skill-last-write-e1.0"]
HD = [4, 8]
B1, S = "B1 audit-at-commit", "Sentinel-A1"
FIELDS = ("policy", "attack", "delta", "wf", "repo", "seed", "harm", "detected_at", "iota",
          "n_solved", "t_lost", "false_removed", "benign_inspected", "rho_patch", "eta_q")
ALPHA_FAMILY = 0.05 / 4                                        # D25: four rho points


def cut(r):
    return {f: r.get(f) for f in FIELDS}


def worst_L(rs, pol, lq, lt=M.LAMBDA_T):
    loss = [{**r, "harm": M.loss(r["harm"], r["false_removed"], r["t_lost"], lq, lt)} for r in rs]
    return MV.value(MV.harm_table(loss, pol, HELD_OUT, HD))


def col_lines(rs, pol, lt=M.LAMBDA_T):
    """Each column's mean L as a line in lambda_Q, a + lambda_Q b: the column mean is a mean of
    per-workflow means, so it is linear in lambda_Q, and the worst case is the max of the lines."""
    a = MV.harm_table([{**r, "harm": M.loss(r["harm"], 0.0, r["t_lost"], 0.0, lt)} for r in rs], pol, HELD_OUT, HD)
    b = MV.harm_table([{**r, "harm": float(r["false_removed"])} for r in rs], pol, HELD_OUT, HD)
    return [(sum(a[c].values()) / len(a[c]), sum(b[c][w] for w in a[c]) / len(a[c])) for c in a]


def breakeven(s_rs, b_rs, lo=0.0, hi=5.0, step=0.0005):
    """Smallest lambda_Q on the grid at which Sentinel's worst-case L reaches B1's (None if never)."""
    ls, lb = col_lines(s_rs, S), col_lines(b_rs, B1)
    for i in range(int((hi - lo) / step) + 1):
        lq = lo + i * step
        if max(a + lq * b for a, b in ls) >= max(a + lq * b for a, b in lb):
            return round(lq, 4)
    return None


# ------------------------------------------------------------------ pinned records
pin = {l.split()[1]: l.split()[0] for l in (V2 / "eval-records.sha256").read_text().splitlines()
       if l and not l.startswith("#")}

main = {}                                                      # rho -> [records at the headline cell]
h = hashlib.sha256()
with open(V2 / "eval-main.jsonl", "rb") as fh:
    tail = b""
    while True:
        chunk = fh.read(1 << 26)
        if not chunk:
            break
        h.update(chunk)
        lines = (tail + chunk).split(b"\n")
        tail = lines.pop()
        for ln in lines:
            if b'"setting": "mid"' not in ln or not (b'"delta": 4,' in ln or b'"delta": 8,' in ln):
                continue
            r = json.loads(ln)
            if r["setting"] != "mid" or r["delta"] not in HD or r["attack"] not in HELD_OUT:
                continue
            main.setdefault(f"{r['rho_patch']:g}", []).append(cut(r))
assert tail == b""
assert h.hexdigest() == pin["eval-main.jsonl"], "eval-main.jsonl differs from its pin"

eta_bytes = (V2 / "sweep-eta.jsonl").read_bytes()
assert hashlib.sha256(eta_bytes).hexdigest() == pin["sweep-eta.jsonl"], "sweep-eta.jsonl differs from its pin"
eta = {}                                                       # rho -> eta_q -> [records]
for ln in eta_bytes.decode().splitlines():
    r = json.loads(ln)
    if r["delta"] in HD and r["attack"] in HELD_OUT and r["policy"] == S:
        eta.setdefault(f"{r['rho_patch']:g}", {}).setdefault(r["eta_q"], []).append(cut(r))

out = {"sha256_eval_main": pin["eval-main.jsonl"], "sha256_sweep_eta": pin["sweep-eta.jsonl"],
       "lambda_Q": M.LAMBDA_Q, "lambda_T": M.LAMBDA_T, "post_hoc": True}

# ------------------------------------------------------------------ 1. loss by eta_Q
out["loss_by_eta"] = {}
for rho, by_eta in sorted(eta.items()):
    b_rs = [r for r in main[rho] if r["policy"] == B1]
    row = {"B1": {"worst_case_L": worst_L(b_rs, B1, M.LAMBDA_Q),
                  "worst_case_harm": MV.value(MV.harm_table(b_rs, B1, HELD_OUT, HD))}}
    for e, s_rs in sorted(by_eta.items()):
        row[f"{e:g}"] = {"worst_case_harm": MV.value(MV.harm_table(s_rs, S, HELD_OUT, HD)),
                         "worst_case_L": worst_L(s_rs, S, M.LAMBDA_Q),
                         "fq_pct": MV.side(s_rs, S, HELD_OUT, HD)["false_quarantine_pct"],
                         "breakeven_lambda_Q": breakeven(s_rs, b_rs)}
    out["loss_by_eta"][rho] = row

# ------------------------------------------------------------------ 2. leave one repo out
out["loro"] = {}
for rho, rs in sorted(main.items()):
    pair = [r for r in rs if r["policy"] in (B1, S)]
    repos = sorted({r["repo"] for r in pair})
    per = {}
    for rp in repos:
        keep = [r for r in pair if r["repo"] != rp]
        vb = MV.value(MV.harm_table(keep, B1, HELD_OUT, HD))
        vc = MV.value(MV.harm_table(keep, S, HELD_OUT, HD))
        per[rp] = {"gain": round(100 * (vb - vc) / vb, 2) if vb else None,
                   "abs_diff": round(vb - vc, 4),
                   "n_workflows": len({r["wf"] for r in keep})}
    gains = [v["gain"] for v in per.values() if v["gain"] is not None]
    no_sympy = [r for r in pair if r["repo"] != "sympy/sympy"]
    out["loro"][rho] = {"min_gain": min(gains), "max_gain": max(gains), "per_repo": per,
                        "without_sympy_98.75": MV.gain_ci(no_sympy, B1, S, HELD_OUT, HD,
                                                          alpha=ALPHA_FAMILY)}

# ------------------------------------------------------------------ 3. V against FQ
out["v_fq"] = {}
for rho, rs in sorted(main.items()):
    pts = {}
    for p in sorted({r["policy"] for r in rs}):
        if p.startswith("Oracle"):
            continue                                           # the positive control sees ground truth
        prs = [r for r in rs if r["policy"] == p]
        pts[p] = (MV.value(MV.harm_table(prs, p, HELD_OUT, HD)),
                  MV.side(prs, p, HELD_OUT, HD)["false_quarantine_pct"])
    for e, s_rs in sorted(eta.get(rho, {}).items()):
        pts[f"Sentinel-A1 eta_Q={e:g}"] = (MV.value(MV.harm_table(s_rs, S, HELD_OUT, HD)),
                                          MV.side(s_rs, S, HELD_OUT, HD)["false_quarantine_pct"])
    front = [p for p, (v, q) in pts.items()
             if not any((v2 <= v and q2 <= q) and (v2 < v or q2 < q) for p2, (v2, q2) in pts.items() if p2 != p)]
    out["v_fq"][rho] = {"points": {p: {"V": v, "FQ": q} for p, (v, q) in pts.items()},
                        "undominated": sorted(front)}

# ------------------------------------------------------------------ 4. D30 sensitivity at 98.75%
out["d30_98.75"] = {}
for rho, by_eta in sorted(eta.items()):
    b_rs = [r for r in main[rho] if r["policy"] == B1]
    cis = {f"{e:g}": MV.gain_ci(b_rs + s_rs, B1, S, HELD_OUT, HD, alpha=ALPHA_FAMILY)
           for e, s_rs in sorted(by_eta.items())}
    lo = min(cis, key=lambda k: cis[k]["lo"])
    out["d30_98.75"][rho] = {"lowest_lo_at_eta": lo, "lo": cis[lo]["lo"], "abs_lo": cis[lo]["abs_lo"],
                             "by_eta": {k: {"lo": c["lo"], "abs_lo": c["abs_lo"]} for k, c in cis.items()}}

OUT.write_text(json.dumps(out, indent=1, sort_keys=True))
print("wrote", OUT)
