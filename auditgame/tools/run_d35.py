"""run_d35.py -- the D35 addendum (preregistration D35); on the eval split ONCE, after its freeze.

Headline cell only (mid, Delta in {4, 8}, the 7 held-out attackers, chi 1.34, b1, match 1), every
rho: B1 and Sentinel-A1 (re-simulated: the reproduction check) and the five addendum arms, plus
the cross-fitted best response of the same seven systems.  On eval, no addendum number is written
unless B1's and Sentinel-A1's V equal the main run's (spikes/v2/eval-summary.json) to 4 decimals
at every rho.

    ../.venv/bin/python tools/run_d35.py --split dev --jobs 10     # pilot -> spikes/v2-addendum-dev
    ../.venv/bin/python tools/run_d35.py --split eval --jobs 10    # once  -> spikes/v2-addendum
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import pathlib
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import addendum_d35 as X
import attackers_v2 as A
import carrier_runner as R
import costs
import draft_setup as D
import freeze_d35
import metrics as M
import metrics_v2 as MV
import policies as P
import sentinel as S
from tools.run_draft_eval import _write, workflows
from tools.select_mixture import make_world

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = {"eval": ROOT / "spikes" / "v2-addendum", "dev": ROOT / "spikes" / "v2-addendum-dev"}
MAIN_SUMMARY = ROOT / "spikes" / "v2" / "eval-summary.json"
B1, SA1 = "B1 audit-at-commit", "Sentinel-A1"
SYSTEMS = [B1, SA1] + X.ARMS
ALPHA = D.FAMILY_ALPHA / len(D.RHO_PATCH_GRID)           # 98.75%, per arm (D35)
MAIN, BR, PIN, SUMMARY = "d35-main.jsonl", "d35-br.jsonl", "d35-records.sha256", "d35-summary.json"
FIELDS = ("harm", "detected_at", "iota", "n_solved", "t_lost", "false_removed", "benign_inspected")


def work(args):
    """One (system, held-out attacker, Delta, rho) at the headline cell, as run_draft_eval.work."""
    (policy, attack, delta, rho), tuned, d35, seeds, split = args
    K = D.target_kappa_for_chi(D.HEADLINE_CHI)
    world = make_world(D.HEADLINE_DETECTOR, "nominal", rho, D.DRIFT_MATCH, D.DRIFT_VISIBLE_TASKS)
    out = []
    for wf in workflows(split):
        got = A.by_name(attack).plan(wf, delta)
        if got is None:
            continue
        for s in seeds:
            if not R.survives(wf, got[0], s):
                continue
            pol = X.make_policy_d35(policy, budget=D.BudgetSpec().budget(wf.H), kappa=K, H=wf.H,
                                    rng_seed=R.rs_of(wf, s), setting=D.HEADLINE_DETECTOR,
                                    tuned=tuned, d35=d35, rho_patch=rho, delta=delta,
                                    attacked=got[0].carrier)
            r = dataclasses.asdict(R.run_carrier(wf, got, pol, world, s, K))
            out.append({**{k: r[k] for k in FIELDS}, "policy": policy, "attack": attack,
                        "delta": delta, "rho_patch": rho, "wf": wf.wf_id, "repo": wf.repo,
                        "seed": s})
    return out


def br_work(args):
    """D27 for one system at one (Delta, rho), as run_draft_eval.br_work."""
    (policy, delta, rho), tuned, d35, seeds, split = args
    K = D.TARGET_KAPPA_DRAFT
    world = make_world(D.HEADLINE_DETECTOR, "nominal", rho)
    rows = []
    for wf in workflows(split):
        for ps in A.placements(wf, delta):
            for s in seeds:
                if not R.survives(wf, ps, s):
                    continue
                pol = X.make_policy_d35(policy, budget=D.budget_b1(wf.H), kappa=K, H=wf.H,
                                        rng_seed=R.rs_of(wf, s), setting=D.HEADLINE_DETECTOR,
                                        tuned=tuned, d35=d35, rho_patch=rho, delta=delta,
                                        attacked=ps.carrier)
                r = R.run_carrier(wf, (ps, "write"), pol, world, s, K)
                rows.append({"wf": wf.wf_id, "placement": (ps.carrier, ps.iota), "seed": s,
                             "harm": r.harm})
    return {"policy": policy, "delta": delta, "rho_patch": rho, **MV.crossfit_value(rows)}


def run(fn, items, jobs, path) -> int:
    n = 0
    with ProcessPoolExecutor(jobs) as ex, open(path, "x") as fh:     # "x": never overwrite (D35)
        for recs in ex.map(fn, items, chunksize=2):
            for r in (recs if isinstance(recs, list) else [recs]):
                fh.write(json.dumps(r, default=str) + "\n")
                n += 1
    return n


def pin(out_dir, names) -> pathlib.Path:
    rows = []
    for name in names:
        h, lines, size = hashlib.sha256(), 0, 0
        with open(out_dir / name, "rb") as fh:
            while chunk := fh.read(1 << 20):
                h.update(chunk)
                lines += chunk.count(b"\n")
                size += len(chunk)
        rows.append((h.hexdigest(), lines, size, name))
    path = out_dir / PIN
    path.write_text("# raw D35 records, not committed; lines  bytes  file:\n"
                    + "".join(f"#   {n}  {b}  {f}\n" for _, n, b, f in rows)
                    + "".join(f"{h}  {f}\n" for h, _, _, f in rows))
    return path


def refusal(split, header, out_dir, summarise_only) -> str | None:
    """D35: eval only on a clean D35 freeze over a clean base, and only once."""
    if split == "eval" and not freeze_d35.clean(header):
        return f"the D35 freeze is not clean: {header}"
    if not summarise_only and (pathlib.Path(out_dir) / MAIN).exists():
        return f"{pathlib.Path(out_dir) / MAIN} exists: the addendum runs once (D35)"
    return None


def reproduces(v_b1, v_s, main_rho) -> list:
    """D35: B1 and Sentinel-A1 must equal the main run to 4 decimals; the mismatches."""
    out = []
    for name, v in ((B1, v_b1), (SA1, v_s)):
        want = main_rho["table2"][name]["worst_case_harm"]
        if round(v, 4) != round(want, 4):
            out.append(f"{name}: {v:.4f} != main {want:.4f}")
    return out


def readings(rows) -> dict:
    """The declared readings (A), (B), (C) of D35, mechanically."""
    low = [rk for rk in rows if float(rk) <= 0.5]
    a = {arm: all(rows[rk][arm]["vs_b1"]["abs_lo"] > 0 for rk in low)
         for arm in ("A1 dhat-swap", "A1 dhat-down1")}
    return {"A_oracle_survives_one_step": all(a.values()), "A_by_arm": a,
            "B_beats_fq_matched_mix": {rk: rows[rk][X.B2_FQ]["vs_sentinel"]["abs_lo"] > 0
                                       for rk in rows},
            "C_scripted_gain_attributable_to_randomisation":
                {rk: rows[rk][X.FIXED]["vs_sentinel"]["abs_lo"] > 0 for rk in rows},
            "C_br_fixed_above_sentinel": {rk: rows[rk][X.FIXED]["v_br"] > rows[rk][SA1]["v_br"]
                                          for rk in rows}}


def _v(rs, p, loss=False):
    if loss:
        rs = [{**r, "harm": M.loss(r["harm"], r["false_removed"], r["t_lost"])} for r in rs]
    return MV.value(MV.harm_table(rs, p, A.held_out(), list(D.HEADLINE_DELTAS)))


def summarise(split, out_dir, meta) -> dict:
    ho, hd = A.held_out(), list(D.HEADLINE_DELTAS)
    recs = [json.loads(line) for line in open(out_dir / MAIN)]
    brs = [json.loads(line) for line in open(out_dir / BR)]
    d35 = X.load_d35()
    main = json.loads(MAIN_SUMMARY.read_text())["by_rho"] if split == "eval" else None
    out = {"run": meta, "alpha": ALPHA, "n_boot": 10000, "reproduction": {}, "rows": {}}
    by = {f"{rho:g}": [r for r in recs if r["rho_patch"] == rho] for rho in D.RHO_PATCH_GRID}
    for rk, rs in by.items():
        vb, vs = _v(rs, B1), _v(rs, SA1)
        out["reproduction"][rk] = {B1: vb, SA1: vs, "checked": main is not None,
                                   "mismatches": reproduces(vb, vs, main[rk]) if main else []}
    if any(v["mismatches"] for v in out["reproduction"].values()):
        out["withheld"] = "D35: B1 or Sentinel-A1 does not reproduce the main run; no addendum number"
        _write(out_dir / SUMMARY, out)
        return out
    for rk, rs in by.items():
        rho = float(rk)
        vb, vs = out["reproduction"][rk][B1], out["reproduction"][rk][SA1]
        rows = {}
        for p in SYSTEMS:
            prs = [r for r in rs if r["policy"] == p]
            vbr = [b["v_br"] for b in brs if b["policy"] == p and b["rho_patch"] == rho
                   and b["v_br"] is not None and math.isfinite(b["v_br"])]
            row = {"V": _v(prs, p), "worst_case_L": _v(prs, p, loss=True),
                   **MV.side(prs, p, ho, hd), "v_br": max(vbr) if vbr else float("nan"),
                   "n_workflows": len({r["wf"] for r in prs}),
                   "n_repos": len({r["repo"] for r in prs}), "n_episodes": len(prs)}
            if p in X.ARMS:
                row["vs_b1"] = MV.gain_ci(rs, B1, p, ho, hd, alpha=ALPHA)
                row["vs_sentinel"] = MV.gain_ci(rs, p, SA1, ho, hd, alpha=ALPHA)
            if p in X.DHAT:
                row["retained"] = (vb - row["V"]) / (vb - vs) if vb > vs else None
            if p == X.B2_FQ:
                row["tuned"] = d35["b2_fq"][rk]
            if p == X.FIXED:
                row["tuned"] = d35["fixed"][rk]
            rows[p] = row
        out["rows"][rk] = rows
    out["readings"] = readings(out["rows"])
    _write(out_dir / SUMMARY, out)
    return out


def provenance() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                                  check=True).stdout.rstrip("\n")
        except (OSError, subprocess.CalledProcessError):
            return None
    status = git("status", "--porcelain", "--", ".")
    return {"git_head": git("rev-parse", "--short", "HEAD"),
            "git_clean": None if status is None else status == "",
            "sha256": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
                       for n in ("tools/run_d35.py", "tools/tune_d35.py", "freeze_d35.py")}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("eval", "dev"), required=True)
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--summarise-only", action="store_true")
    a = ap.parse_args(argv)
    costs.install(P)
    header = freeze_d35.header_line()
    print(header, flush=True)
    out_dir = OUT[a.split]
    why = refusal(a.split, header, out_dir, a.summarise_only)
    if why:
        print(f"refused (D35): {why}", flush=True)
        return 2
    meta = {"split": a.split, "seeds": list(D.SEEDS), "rhos": list(D.RHO_PATCH_GRID),
            "deltas": list(D.HEADLINE_DELTAS), "systems": SYSTEMS, "header": header,
            **provenance()}
    if not a.summarise_only:
        out_dir.mkdir(parents=True, exist_ok=True)
        tuned, d35, seeds = S.load_tuned(), X.load_d35(), tuple(D.SEEDS)
        items = [((p, c, d, rho), tuned, d35, seeds, a.split) for p in SYSTEMS
                 for c in A.held_out() for d in D.HEADLINE_DELTAS for rho in D.RHO_PATCH_GRID]
        print("main", run(work, items, a.jobs, out_dir / MAIN), flush=True)
        brs = [((p, d, rho), tuned, d35, seeds, a.split) for p in SYSTEMS
               for d in D.HEADLINE_DELTAS for rho in D.RHO_PATCH_GRID]
        print("br", run(br_work, brs, a.jobs, out_dir / BR), flush=True)
        print("records", pin(out_dir, [MAIN, BR]), flush=True)
    s = summarise(a.split, out_dir, meta)
    return 1 if "withheld" in s else 0


if __name__ == "__main__":
    raise SystemExit(main())
