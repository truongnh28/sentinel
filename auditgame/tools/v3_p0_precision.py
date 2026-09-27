#!/usr/bin/env python3
"""v3_p0_precision.py -- how wide will Sentinel v3's headline-gain CI be on its fresh eval split?

A P0 planning check for Sentinel v3, not a run.  It is a plasmode simulation: v2's own
per-workflow harms (B1 audit-at-commit vs Sentinel-A1, 7 held-out attackers, Delta in {4, 8},
detector setting mid, every rho_patch) are re-dealt into v3's family structure, and the CI
v2's metrics_v2.gain_ci would report is recomputed on each re-deal.

1. Validation 1: metrics_v2.gain_ci on the v2 records reproduces eval-summary.json's
   curve_rho gain / lo / hi exactly (alpha = FAMILY_ALPHA / 4 = 0.0125, n_boot 10000, seed 2026).
2. Validation 2: gain_ci_np, a vectorised gain_ci, gives v2's point exactly and bounds within
   1 pp of gain_ci at alpha 0.05 (a different RNG, so only Monte-Carlo agreement is expected).
3. Plasmode, per rho (setting mid), R replicates of each scenario:
   (a) v2 actual, 10 seeds       -- the data are fixed; only the bootstrap draw varies
   (b) v2 actual structure, 3 random seeds per workflow
   (c) v3 two-pass split, 3 seeds (C14(a): 36 workflows / 18 families)
   (d) v3 one-pass split, 3 seeds (26 workflows / 18 families)
   (e) v3 two-pass split, 10 seeds
   (f) v3 one-pass split, 10 seeds
   (g) v3 primary split (SWE-rebench-V2, v3/corpus.py): 96 workflows / 20 families, 10 seeds
   (h) the same, 3 seeds
   (i) its Delta = 8-hosting subset (H >= 9): 56 workflows / 20 families, 10 seeds
   A v3 family slot of size n draws one of the 16 v2 eval families uniformly with replacement
   and takes n of its workflows (a random permutation, then with-replacement extras if n
   exceeds the family).  Each workflow keeps k seeds drawn without replacement from 1..10,
   shared by both policies; its harm in a column is the mean over those seeds' records.
   Every replicate is read by the pairs bootstrap (v2's gain_ci, the P0 baseline) and, on
   an independent draw, by v3/metrics.py's wild cluster bootstrap (Webb weights, T17).

Records: by default streamed from spikes/v2/eval-main.jsonl (4.5 GB, byte prefilter, then
the headline cell's filter); --extract PATH reads an already-filtered JSON list instead.
Writes spikes/v3-p0/precision.json.

    python3 tools/v3_p0_precision.py [--extract PATH] [--reps 1000] [--n-boot 2000]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import attackers_v2 as A
import draft_setup as D
import metrics_v2 as MV
from v3 import corpus as VC
from v3 import metrics as M3

MAIN = HERE / "spikes" / "v2" / "eval-main.jsonl"
SUMMARY = HERE / "spikes" / "v2" / "eval-summary.json"
CORPUS = HERE / "spikes" / "v3-p0" / "corpus.json"
OUT = HERE / "spikes" / "v3-p0" / "precision.json"

B1, SA = "B1 audit-at-commit", "Sentinel-A1"
POLICIES = (B1, SA)
SETTING = D.HEADLINE_DETECTOR                     # "mid"
DELTAS = tuple(D.HEADLINE_DELTAS)                 # (4, 8)
RHOS = tuple(D.RHO_PATCH_GRID)                    # (0.0, 0.25, 0.5, 1.0)
SEEDS = tuple(range(1, 11))
FAM_ALPHA = D.FAMILY_ALPHA / len(RHOS)            # 0.0125, D25
V2_BOOT, V2_SEED = 10000, 2026
KEEP = ("policy", "attack", "delta", "setting", "rho_patch", "wf", "repo", "seed", "harm")

#: sentinel-v3.md C14(a) split, if spikes/v3-p0/corpus.json is absent
TWO_PASS = [10, 9, 2, 1] + [1] * 14
ONE_PASS = [5, 5, 1, 1] + [1] * 14
#: v3 primary split (v3/corpus.py, SWE-rebench-V2): workflows per family, and per family among
#: the workflows with H >= 9 (the Delta = 8 cell).  Shape only; checked against
#: corpus.EVAL_SUMMARY_PINNED's totals and Kish below.
PRIMARY = [5] * 16 + [4] * 4
PRIMARY_D8 = [4] * 8 + [3] * 3 + [2] * 6 + [1] * 3

#: v2 curve_rho at alpha 0.0125 (eval-summary.json), asserted against the file AND recomputed
V2_KNOWN = {"0": (49.2, 40.8046, 54.9194), "0.25": (49.15, 36.8892, 54.133),
            "0.5": (43.03, 23.8159, 47.1006), "1": (8.79, -27.3201, 18.8573)}

REL_CUTS, ABS_CUTS, GATE = (10, 15, 20), (0.06, 0.10), 15.0


# --- records --------------------------------------------------------------------------------
def stream_main(path=MAIN) -> list:
    """The headline cell of eval-main.jsonl, in file order (so every mean sums as v2's did)."""
    held = set(A.held_out())
    pol = [f'"policy": "{p}"'.encode() for p in POLICIES]
    out = []
    with open(path, "rb") as fh:
        for line in fh:
            if b'"budget": "b1"' not in line or b'"eta_q": null' not in line:
                continue
            if not any(p in line for p in pol):
                continue
            r = json.loads(line)
            if (r["delta"] in DELTAS and r["chi"] == 1.34 and r["match"] == 1.0
                    and r["drift_visible"] == 1 and r["attack"] in held
                    and r["policy"] in POLICIES):
                out.append({k: r[k] for k in KEEP})
    return out


def load(extract) -> list:
    if extract:
        return json.loads(pathlib.Path(extract).read_text())
    t = time.time()
    recs = stream_main()
    print(f"streamed {MAIN.relative_to(HERE)}: {len(recs)} records in {time.time() - t:.0f}s")
    return recs


# --- the numpy gain_ci -------------------------------------------------------------------------
def _q(xs, a):
    """metrics_v2._q without the rounding: xs sorted."""
    return float(xs[min(len(xs) - 1, int(a * len(xs)))]) if len(xs) else float("nan")


def point_value(W) -> float:
    """metrics_v2.value: max over columns of the mean over the workflows present."""
    m = ~np.isnan(W)
    den = m.sum(0)
    col = np.where(den > 0, np.nan_to_num(W).sum(0) / np.maximum(den, 1), -np.inf)
    return float(col.max())


def counts(fam_of_wf, n_fam, n_boot, rng) -> np.ndarray:
    """K[b, w]: how often workflow w's family was drawn in resample b (families with replacement)."""
    draw = rng.integers(n_fam, size=(n_boot, n_fam))
    per_fam = np.zeros((n_boot, n_fam))
    np.add.at(per_fam, (np.arange(n_boot)[:, None], draw), 1.0)
    return per_fam[:, fam_of_wf]


def _boot_value(K, W) -> np.ndarray:
    """metrics_v2._value_multi for every resample: max(0, max over columns of the pooled mean)."""
    m = ~np.isnan(W)
    num, den = K @ np.nan_to_num(W), K @ m.astype(float)
    col = np.where(den > 0, num / np.where(den > 0, den, 1.0), -np.inf)
    return np.maximum(0.0, col.max(1))


def gain_ci_np(Wb, Wc, K, alpha) -> dict:
    """metrics_v2.gain_ci on W matrices (n_wf x n_col, NaN = missing) and a count matrix K."""
    vb, vc = point_value(Wb), point_value(Wc)
    b, c = _boot_value(K, Wb), _boot_value(K, Wc)
    dif = np.sort(b - c)
    pos = b > 0
    rel = np.sort(100.0 * (b[pos] - c[pos]) / b[pos])
    return {"gain": 100.0 * (vb - vc) / vb if vb else float("nan"),
            "lo": _q(rel, alpha / 2), "hi": _q(rel, 1 - alpha / 2),
            "abs_diff": vb - vc, "abs_lo": _q(dif, alpha / 2), "abs_hi": _q(dif, 1 - alpha / 2),
            "v_base": vb, "v_cand": vc, "n_zero_base": int((~pos).sum())}


# --- the harm cube -----------------------------------------------------------------------------
def cube(recs):
    """H[policy, rho, wf, column, seed] (NaN = no record), the workflows, their families, the columns."""
    mid = [r for r in recs if r["setting"] == SETTING]
    wfs = sorted({r["wf"] for r in mid})
    repo_of = {r["wf"]: r["repo"] for r in mid}
    fams = sorted(set(repo_of.values()))
    cols = sorted({f"{r['attack']}@{r['delta']}" for r in mid})
    iw, ic = {w: i for i, w in enumerate(wfs)}, {c: i for i, c in enumerate(cols)}
    ip, ir, isd = {p: i for i, p in enumerate(POLICIES)}, {r: i for i, r in enumerate(RHOS)}, \
        {s: i for i, s in enumerate(SEEDS)}
    H = np.full((len(POLICIES), len(RHOS), len(wfs), len(cols), len(SEEDS)), np.nan)
    for r in mid:
        k = (ip[r["policy"]], ir[r["rho_patch"]], iw[r["wf"]], ic[f"{r['attack']}@{r['delta']}"],
             isd[r["seed"]])
        assert np.isnan(H[k]), f"two records for one episode: {r}"
        H[k] = r["harm"]
    fam_of_wf = np.array([fams.index(repo_of[w]) for w in wfs])
    return H, wfs, fams, fam_of_wf, cols


def reduce_seeds(Hpr, src, S) -> np.ndarray:
    """W[w, c] = mean over the seeds S[w] (bool, n_wf x 10) of the records of workflow src[w]."""
    h = Hpr[src]                                    # n_wf x n_col x 10
    ok = ~np.isnan(h) & S[:, None, :]
    den = ok.sum(2)
    return np.where(den > 0, np.where(ok, h, 0.0).sum(2) / np.maximum(den, 1), np.nan)


# --- plasmode ------------------------------------------------------------------------------
def v3_sizes():
    if CORPUS.exists():
        s = json.loads(CORPUS.read_text()).get("summary", {})
        if "two_pass" in s and "one_pass" in s:
            return (sorted(s["two_pass"]["by_family"].values(), reverse=True),
                    sorted(s["one_pass"]["by_family"].values(), reverse=True), "corpus.json")
    return TWO_PASS, ONE_PASS, "constants"


def structure(kind, sizes, members, fam_of_wf, n_seeds, rng):
    """One replicate: (source v2 workflow per synthetic workflow, its cluster, its seed mask)."""
    if kind == "v2":
        src, clu = np.arange(len(fam_of_wf)), fam_of_wf.copy()
        n_clu = int(fam_of_wf.max()) + 1
    else:
        src, clu = [], []
        for j, n in enumerate(sizes):
            m = members[rng.integers(len(members))]
            take = list(rng.permutation(m)[:n])
            if n > len(m):
                take += list(rng.choice(m, n - len(m), replace=True))
            src += take
            clu += [j] * n
        src, clu, n_clu = np.array(src), np.array(clu), len(sizes)
    S = np.zeros((len(src), len(SEEDS)), bool)
    if n_seeds == len(SEEDS):
        S[:] = True
    else:
        pick = np.argsort(rng.random((len(src), len(SEEDS))), axis=1)[:, :n_seeds]
        S[np.arange(len(src))[:, None], pick] = True
    return src, clu, n_clu, S


def gain_ci_wild(Wb, Wc, clu, F, alpha) -> dict:
    """gain_ci_np with v3/metrics.py's wild cluster bootstrap: F = Webb weights (n_boot x n_clu)."""
    vb, vc = point_value(Wb), point_value(Wc)
    b, c = M3.boot_value(Wb, clu, F, "wild"), M3.boot_value(Wc, clu, F, "wild")
    dif = np.sort(b - c)
    pos = b > 0
    rel = np.sort(100.0 * (b[pos] - c[pos]) / b[pos])
    return {"gain": 100.0 * (vb - vc) / vb if vb else float("nan"),
            "lo": _q(rel, alpha / 2), "hi": _q(rel, 1 - alpha / 2),
            "abs_diff": vb - vc, "abs_lo": _q(dif, alpha / 2), "abs_hi": _q(dif, 1 - alpha / 2),
            "v_base": vb, "v_cand": vc, "n_zero_base": int((~pos).sum())}


def stats(rows) -> dict:
    rel_w = np.array([r["hi"] - r["lo"] for r in rows])
    abs_w = np.array([r["abs_hi"] - r["abs_lo"] for r in rows])
    lo = np.array([r["lo"] for r in rows])
    gain = np.array([r["gain"] for r in rows])
    q = lambda x: {"median": round(float(np.median(x)), 4), "p10": round(float(np.quantile(x, .1)), 4),
                   "p90": round(float(np.quantile(x, .9)), 4)}
    return {"rel_width": q(rel_w), "abs_width": q(abs_w),
            **{f"P_rel_width_le_{c}": round(float(np.mean(rel_w <= c)), 4) for c in REL_CUTS},
            **{f"P_abs_width_le_{c:g}": round(float(np.mean(abs_w <= c)), 4) for c in ABS_CUTS},
            f"P_lo_ge_{GATE:g}": round(float(np.mean(lo >= GATE)), 4),
            "median_gain": round(float(np.median(gain)), 4),
            "n_zero_base_max": int(max(r["n_zero_base"] for r in rows))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--extract", help="an already-filtered JSON list of the headline records")
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--n-boot", type=int, default=2000)
    args = ap.parse_args()
    t0 = time.time()

    recs = load(args.extract)
    assert len(recs) == 91896, f"{len(recs)} headline records, expected 91896"
    held = sorted(A.held_out())
    assert sorted({r["attack"] for r in recs}) == held and len(held) == 7, "held-out attackers changed"
    assert {r["delta"] for r in recs} == set(DELTAS)
    assert {r["rho_patch"] for r in recs} == set(RHOS)
    assert {r["seed"] for r in recs} == set(SEEDS)

    # --- validation 1: v2's own gain_ci reproduces eval-summary.json ---------------------
    summ = json.loads(SUMMARY.read_text())["curve_rho"]
    mid = {rho: [r for r in recs if r["setting"] == SETTING and r["rho_patch"] == rho] for rho in RHOS}
    v1, v2ref = {}, {}
    for rho in RHOS:
        key = f"{rho:g}"
        assert (summ[key]["gain"], summ[key]["lo"], summ[key]["hi"]) == V2_KNOWN[key], key
        assert summ[key]["alpha"] == FAM_ALPHA and summ[key]["n_boot"] == V2_BOOT, key
        g = MV.gain_ci(mid[rho], B1, SA, held, DELTAS, n_boot=V2_BOOT, seed=V2_SEED, alpha=FAM_ALPHA)
        for f in ("gain", "lo", "hi", "abs_diff", "abs_lo", "abs_hi", "v_base", "v_cand",
                  "n_repos", "n_workflows"):
            assert g[f] == summ[key][f], f"validation 1, rho {key}, {f}: {g[f]} != {summ[key][f]}"
        v1[key] = {f: g[f] for f in ("gain", "lo", "hi", "abs_diff", "abs_lo", "abs_hi")}
        v2ref[key] = MV.gain_ci(mid[rho], B1, SA, held, DELTAS, n_boot=V2_BOOT, seed=V2_SEED, alpha=0.05)
    print(f"validation 1 ok: metrics_v2.gain_ci reproduces curve_rho at alpha {FAM_ALPHA} "
          f"({time.time() - t0:.0f}s)")

    # --- validation 2: gain_ci_np vs gain_ci on the real data ------------------------------
    H, wfs, fams, fam_of_wf, cols = cube(recs)
    assert (len(wfs), len(fams), len(cols)) == (57, 16, 14), (len(wfs), len(fams), len(cols))
    all_seeds = np.ones((len(wfs), len(SEEDS)), bool)
    ident = np.arange(len(wfs))
    v2chk = {}
    for i, rho in enumerate(RHOS):
        key = f"{rho:g}"
        Wb, Wc = (reduce_seeds(H[p, i], ident, all_seeds) for p in range(2))
        tb = MV.harm_table(mid[rho], B1, held, DELTAS)
        tc = MV.harm_table(mid[rho], SA, held, DELTAS)
        assert abs(point_value(Wb) - MV.value(tb)) < 1e-12 and abs(point_value(Wc) - MV.value(tc)) < 1e-12
        K = counts(fam_of_wf, len(fams), V2_BOOT, np.random.default_rng(V2_SEED))
        g = gain_ci_np(Wb, Wc, K, 0.05)
        ref = v2ref[key]
        assert round(g["gain"], 2) == ref["gain"], f"validation 2 point, rho {key}: {g['gain']} vs {ref['gain']}"
        for f in ("lo", "hi"):
            assert abs(g[f] - ref[f]) <= 1.0, f"validation 2, rho {key}, {f}: {g[f]:.4f} vs {ref[f]}"
        for f in ("abs_lo", "abs_hi"):
            assert abs(g[f] - ref[f]) <= 0.01, f"validation 2, rho {key}, {f}: {g[f]:.4f} vs {ref[f]}"
        v2chk[key] = {"np": {f: round(g[f], 4) for f in ("gain", "lo", "hi", "abs_lo", "abs_hi")},
                      "metrics_v2": {f: ref[f] for f in ("gain", "lo", "hi", "abs_lo", "abs_hi")}}
    print(f"validation 2 ok: gain_ci_np point exact, bounds within 1 pp of gain_ci at alpha 0.05 "
          f"({time.time() - t0:.0f}s)")

    # --- plasmode ------------------------------------------------------------------------------
    two, one, src_sizes = v3_sizes()
    assert (sum(two), len(two), sum(one), len(one)) == (36, 18, 26, 18), (two, one)
    pin = VC.EVAL_SUMMARY_PINNED["primary"]
    assert (sum(PRIMARY), len(PRIMARY), round(VC.kish(PRIMARY), 2)) == \
        (pin["workflows"], pin["families"], pin["kish"]), PRIMARY
    assert (sum(PRIMARY_D8), len(PRIMARY_D8), round(VC.kish(PRIMARY_D8), 2)) == \
        (pin["delta8"]["workflows"], pin["delta8"]["families"], pin["delta8"]["kish"]), PRIMARY_D8
    members = [np.flatnonzero(fam_of_wf == f) for f in range(len(fams))]
    scen = {"a": ("v2 actual, 10 seeds", "v2", None, 10),
            "b": ("v2 actual, 3 seeds", "v2", None, 3),
            "c": ("v3 two-pass, 3 seeds", "v3", two, 3),
            "d": ("v3 one-pass, 3 seeds", "v3", one, 3),
            "e": ("v3 two-pass, 10 seeds", "v3", two, 10),
            "f": ("v3 one-pass, 10 seeds", "v3", one, 10),
            "g": ("v3 primary (SWE-rebench-V2), 10 seeds", "v3", PRIMARY, 10),
            "h": ("v3 primary (SWE-rebench-V2), 3 seeds", "v3", PRIMARY, 3),
            "i": ("v3 primary, Delta = 8 subset (H >= 9), 10 seeds", "v3", PRIMARY_D8, 10)}
    res = {}
    for si, (name, (label, kind, sizes, k)) in enumerate(scen.items()):
        rows = {f"{rho:g}": [] for rho in RHOS}
        wild = {f"{rho:g}": [] for rho in RHOS}
        for rep in range(args.reps):
            rng = np.random.default_rng([2027, si, rep])
            src, clu, n_clu, S = structure(kind, sizes, members, fam_of_wf, k, rng)
            K = counts(clu, n_clu, args.n_boot, rng)       # one draw, shared by the four rhos
            # the wild draw has its own stream, so the pairs numbers of (a)-(f) are unchanged
            F = M3.family_draws(n_clu, args.n_boot, np.random.default_rng([2027, si, rep, 1]),
                                "wild")
            for i, rho in enumerate(RHOS):
                Wb, Wc = (reduce_seeds(H[p, i], src, S) for p in range(2))
                rows[f"{rho:g}"].append(gain_ci_np(Wb, Wc, K, 0.05))
                wild[f"{rho:g}"].append(gain_ci_wild(Wb, Wc, clu, F, 0.05))
        res[name] = {"label": label, "workflows": int(len(src)), "families": int(n_clu),
                     "seeds": k, "by_rho": {r: stats(v) for r, v in rows.items()},
                     "wild_by_rho": {r: stats(v) for r, v in wild.items()}}
        print(f"scenario {name} ({label}) done ({time.time() - t0:.0f}s)")

    doc = {"what": "sentinel-v3 P0: plasmode precision of the headline gain CI "
                   "(v2 per-workflow harms re-dealt into v3's family structure)",
           "cell": {"setting": SETTING, "deltas": list(DELTAS), "attackers": held, "rhos": list(RHOS),
                    "base": B1, "cand": SA},
           "params": {"reps": args.reps, "n_boot": args.n_boot, "alpha": 0.05, "gate_pct": GATE,
                      "v3_sizes_from": src_sizes, "two_pass": two, "one_pass": one,
                      "primary": PRIMARY, "primary_delta8": PRIMARY_D8,
                      "bootstraps": {"by_rho": "pairs (v2 gain_ci, the P0 baseline)",
                                     "wild_by_rho": "v3/metrics.py wild, Webb weights, "
                                                    "default_rng([2027, scenario, rep, 1])"},
                      "rng": "numpy default_rng([2027, scenario, rep])"},
           "validation1_alpha_0.0125": v1, "validation2_alpha_0.05": v2chk,
           "scenarios": res}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")

    # --- report ------------------------------------------------------------------------------
    print(f"\nalpha 0.05, {args.reps} reps x {args.n_boot} resamples; widths in pp (rel) / harm (abs); "
          f"cells: median [p10, p90]")
    hdr = (f"{'rho':>4} {'sc':2} {'wf/fam':>6} {'k':>2} {'rel width':>20} {'abs width':>21} "
           f"{'<=10':>5} {'<=15':>5} {'<=20':>5} {'a<=.06':>6} {'a<=.10':>6} {'lo>=15':>6} {'gain':>6}")
    print(hdr)
    for rho in RHOS:
        key = f"{rho:g}"
        for bs, name in [(bs, n) for bs in ("by_rho", "wild_by_rho") for n in res]:
            s = res[name]
            b = s[bs][key]
            rw, aw = b["rel_width"], b["abs_width"]
            tag = name + ("w" if bs == "wild_by_rho" else "")
            print(f"{key:>4} {tag:2} {s['workflows']:>3}/{s['families']:<2} {s['seeds']:>2} "
                  f"{rw['median']:6.1f} [{rw['p10']:5.1f},{rw['p90']:5.1f}] "
                  f"{aw['median']:6.3f} [{aw['p10']:5.3f},{aw['p90']:5.3f}] "
                  f"{b['P_rel_width_le_10']:5.2f} {b['P_rel_width_le_15']:5.2f} "
                  f"{b['P_rel_width_le_20']:5.2f} {b['P_abs_width_le_0.06']:6.2f} "
                  f"{b['P_abs_width_le_0.1']:6.2f} {b['P_lo_ge_15']:6.2f} {b['median_gain']:6.1f}")
    print("tag Xw = scenario X's replicates read by the wild bootstrap")
    print("scenarios: " + "; ".join(f"{n} = {s['label']}" for n, s in res.items()))
    print(f"wrote {OUT.relative_to(HERE)} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
