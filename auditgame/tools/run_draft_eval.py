"""run_draft_eval.py -- draft SS9.4 on the frozen v2 configuration.

Main grid (carrier world): every system of sentinel.REGISTRY x 34 columns (18 scripted +
16 BR) x Delta x detector x rho; chi = 1.34, budget b1, 10 seeds.
Best response (D27): every system x Delta x rho at the headline detector, every feasible
placement, cross-fitted.
Sweeps (headline detector, every rho, held-out class, Delta in {4, 8}): line-8 threshold,
drift match, persistent drift; budget share x chi (EXPLORATORY, D4b) on Delta in {2, 4, 8}.
Secondary world (D29): the four gate baselines on the held-out class.

    python3 tools/run_draft_eval.py --jobs 10
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import attackers_v2 as A
import carrier_policies as CP
import carrier_runner as R
import corpus_v2 as C
import costs
import draft_setup as D
import freeze
import gate_world as G
import metrics_v2 as MV
import policies as P
import sentinel as S
from tools.select_mixture import make_world

OUT = pathlib.Path(__file__).resolve().parent.parent / "spikes" / "v2"
SWEEPERS = ("B3 audit-on-insertion", "B4 audit-on-retrieval")


@dataclasses.dataclass(frozen=True)
class Job:
    policy: str
    attack: str
    delta: int
    setting: str
    rho_patch: float
    chi: float = D.HEADLINE_CHI
    budget: D.BudgetSpec = D.BudgetSpec()
    eta_q: float | None = None           # None = the tuned line-8 threshold
    match: float = D.DRIFT_MATCH
    drift_visible: int | None = D.DRIFT_VISIBLE_TASKS


def workflows(split):
    """The eval split for the study; "dev" only for the pipeline smoke (Task 12 Step 2),
    which must never read an eval number before the freeze."""
    dev, ev = C.split(C.make_corpus_v2())
    return {"dev": dev, "eval": ev}[split]


def work(args):
    job, tuned, seeds, split = args
    K = D.target_kappa_for_chi(job.chi)
    world = make_world(job.setting, "nominal", job.rho_patch, job.match, job.drift_visible)
    out = []
    for wf in workflows(split):
        got = A.by_name(job.attack).plan(wf, job.delta)
        if got is None:
            continue
        for s in seeds:
            if not R.survives(wf, got[0], s):
                continue
            pol = S.make_policy(job.policy, budget=job.budget.budget(wf.H), kappa=K, H=wf.H,
                                rng_seed=R.rs_of(wf, s), setting=job.setting, tuned=tuned,
                                rho_patch=job.rho_patch, delta=job.delta,
                                eta_q=job.eta_q, drift_match=job.match,
                                attacked=got[0].carrier)
            r = R.run_carrier(wf, got, pol, world, s, K)
            rec = {k: v for k, v in dataclasses.asdict(r).items() if k != "audits"}
            rec.update({k: v for k, v in dataclasses.asdict(job).items() if k != "budget"})
            rec.update(budget=job.budget.label(), wf=wf.wf_id, repo=wf.repo, seed=s,
                       audits=r.audits)
            out.append(rec)
    return out


def br_work(args):
    """D27: every feasible placement at Delta, cross-fitted per workflow."""
    (policy, delta, setting, rho), tuned, seeds, split = args
    K = D.TARGET_KAPPA_DRAFT
    world = make_world(setting, "nominal", rho)
    rows, repo_of = [], {}
    for wf in workflows(split):
        repo_of[wf.wf_id] = wf.repo
        for ps in A.placements(wf, delta):
            for s in seeds:
                if not R.survives(wf, ps, s):
                    continue
                pol = S.make_policy(policy, budget=D.budget_b1(wf.H), kappa=K, H=wf.H,
                                    rng_seed=R.rs_of(wf, s), setting=setting, tuned=tuned,
                                    rho_patch=rho, delta=delta, attacked=ps.carrier)
                r = R.run_carrier(wf, (ps, "write"), pol, world, s, K)
                rows.append({"wf": wf.wf_id, "placement": (ps.carrier, ps.iota), "seed": s,
                             "harm": r.harm})
    per_wf = {}
    for w in {r["wf"] for r in rows}:
        per_wf[w] = MV.crossfit_value([r for r in rows if r["wf"] == w])["v_br"]
    return {"policy": policy, "delta": delta, "setting": setting, "rho_patch": rho,
            **MV.crossfit_value(rows), "per_wf": per_wf, "repo_of": repo_of}


def gate_work(args):
    (name, attack, delta, rho), seeds, split = args
    world = make_world(D.HEADLINE_DETECTOR, "nominal", rho)
    out = []
    for wf in workflows(split):
        got = A.by_name(attack).plan(wf, delta)
        if got is None:
            continue
        for s in seeds:
            if not R.survives(wf, got[0], s):
                continue
            g = G.run_gate(wf, got, name, world, s, D.budget_b1(wf.H))
            out.append({"policy": name, "attack": attack, "delta": delta, "rho_patch": rho,
                        "wf": wf.wf_id, "repo": wf.repo, "seed": s, "harm": g.harm,
                        "false_blocks": g.false_blocks, "t_lost": g.t_lost, "n_solved": g.n_solved})
    return out


def run(fn, items, jobs, path):
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    with ProcessPoolExecutor(jobs) as ex, open(path, "w") as fh:
        for recs in ex.map(fn, items, chunksize=2):
            for r in (recs if isinstance(recs, list) else [recs]):
                fh.write(json.dumps(r, default=str) + "\n")
                n += 1
    return n


def ref_rho() -> float:
    return D.HEADLINE_RHO if D.HEADLINE_RHO is not None else D.REF_RHO_FALLBACK


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(D.SEEDS))        # cut (c)
    ap.add_argument("--deltas", type=int, nargs="+", default=list(D.DELTAS))      # cut (b)
    ap.add_argument("--rhos", type=float, nargs="+", default=list(D.RHO_PATCH_GRID))
    ap.add_argument("--rho-mid-only", action="store_true")                        # cut (a)
    ap.add_argument("--skip-br", action="store_true")                             # smoke only
    ap.add_argument("--skip-sweeps", action="store_true")                         # smoke only
    ap.add_argument("--split", choices=("eval", "dev"), default="eval")           # smoke: dev
    a = ap.parse_args()
    if a.split == "dev":
        global OUT
        OUT = OUT.parent / "v2-smoke-dev"
    # The manifest is written through the operating installation (freeze.write_operating);
    # a reader compares against the same one, as every v1 tool does.  v2 never reads P.KAPPA.
    costs.install(P)
    print(freeze.header_line(), flush=True)
    for name in S.REGISTRY:
        freeze.require_frozen(name)
    tuned, seeds = S.load_tuned(), tuple(a.seeds)
    cols = list(A.SCRIPTED) + [x.name for x in A.br_attacks()]

    grid = [Job(p, c, d, st, rho) for rho in a.rhos
            for st in (D.DETECTORS if (rho == ref_rho() or not a.rho_mid_only) else [D.HEADLINE_DETECTOR])
            for p in S.REGISTRY for c in cols for d in a.deltas]
    print("main", run(work, [(j, tuned, seeds, a.split) for j in grid], a.jobs, OUT / "eval-main.jsonl"), flush=True)

    if not a.skip_br:
        br = [((p, d, D.HEADLINE_DETECTOR, rho), tuned, seeds, a.split)
              for p in S.REGISTRY for d in a.deltas for rho in a.rhos]
        print("br", run(br_work, br, a.jobs, OUT / "eval-br.jsonl"), flush=True)

    if not a.skip_sweeps:
        pair = ("B1 audit-at-commit", "Sentinel-A1")
        ho, hd = A.held_out(), list(D.HEADLINE_DELTAS)
        sweeps = {
            "sweep-eta": [Job("Sentinel-A1", c, d, D.HEADLINE_DETECTOR, rho, eta_q=e)
                          for c in ho for d in hd for rho in a.rhos for e in D.ETA_Q_GRID],
            "sweep-match": [Job(p, c, d, D.HEADLINE_DETECTOR, rho, match=m)
                            for p in pair for c in ho for d in hd for rho in a.rhos for m in (0.0, 0.5, 1.0)],
            "sweep-persistent-drift": [Job(p, c, d, D.HEADLINE_DETECTOR, rho, drift_visible=None)
                                       for p in pair for c in ho for d in hd for rho in a.rhos],
            "sweep-budget-EXPLORATORY": [Job(p, c, d, D.HEADLINE_DETECTOR, rho, chi=chi,
                                             budget=D.BudgetSpec("share", sh))
                                         for p in pair for c in ho for d in (2, 4, 8)
                                         for rho in a.rhos for chi in D.CHIS
                                         for sh in (0.25, 0.5, 0.75, 1.0)],
        }
        for name, g in sweeps.items():
            print(name, run(work, [(j, tuned, seeds, a.split) for j in g], a.jobs, OUT / f"{name}.jsonl"), flush=True)
        gate = [((n, c, d, rho), seeds, a.split) for n in G.GATE_BASELINES for c in ho for d in hd for rho in a.rhos]
        print("gate", run(gate_work, gate, a.jobs, OUT / "eval-gate-world.jsonl"), flush=True)

    summarise()
    summarise_sweeps()
    return 0


def _load(name):
    p = OUT / name
    return [json.loads(l) for l in open(p)] if p.exists() else []


def summarise():
    C.make_corpus_v2()                        # fills C._POOL_OF for the Verified-only row
    recs = _load("eval-main.jsonl")
    brs = _load("eval-br.jsonl")
    ho, dev = A.held_out(), A.development()
    hd = list(D.HEADLINE_DELTAS)
    b1, s = "B1 audit-at-commit", "Sentinel-A1"
    rhos = sorted({r["rho_patch"] for r in recs})
    fam_alpha = D.FAMILY_ALPHA / max(1, len(rhos))

    def cell(rho, st=D.HEADLINE_DETECTOR):
        return [r for r in recs if r["rho_patch"] == rho and r["setting"] == st]

    ref = ref_rho() if ref_rho() in rhos else rhos[0]
    hl_ref = cell(ref)
    ctrl = MV.controls(
        MV.value(MV.harm_table(hl_ref, S.CONTROL, ho, hd)),
        MV.value(MV.harm_table(hl_ref, b1, ho, [0])),
        {p: MV.value(MV.harm_table(hl_ref, p, ho, [0])) for p in SWEEPERS})
    summary = {"freeze": freeze.header_line(), "controls": ctrl, "family_alpha": fam_alpha,
               "curve_rho": {}, "curve_rho_vs_best": {}, "by_rho": {}}
    for rho in rhos:
        hl = cell(rho)
        g = MV.gain_ci(hl, b1, s, ho, hd, alpha=fam_alpha)
        g["meets_margin"] = bool(g["rel_reliable"] and g["lo"] >= D.MARGIN_PCT)
        summary["curve_rho"][f"{rho:g}"] = g
        summary["curve_rho_vs_best"][f"{rho:g}"] = MV.gain_vs_best(hl, list(CP.BASELINES), s, ho, hd, alpha=fam_alpha)
        br = {(x["policy"], x["delta"]): x for x in brs if x["rho_patch"] == rho}
        table2 = {}
        for p in S.REGISTRY:
            v = MV.value(MV.harm_table(hl, p, ho, hd))
            v_br = max((br[(p, d)]["v_br"] for d in hd if (p, d) in br), default=float("nan"))
            table2[p] = {"worst_case_harm": v, "v_br_crossfit": v_br,
                         "exploitability": (v_br - v) if v == v and v_br == v_br else float("nan"),
                         **MV.side(hl, p, ho, hd)}
        summary["by_rho"][f"{rho:g}"] = {
            "table2": table2,
            "table3_ablations": {p: MV.gain_ci(hl, p, s, ho, hd) for p in S.VARIANTS if p != s},
            "figure3_gain_by_delta": {str(d): MV.gain_ci(hl, b1, s, ho, [d], n_boot=2000)
                                      for d in sorted({r["delta"] for r in hl})},
            "transfer_dev_vs_heldout": {"dev_attackers": MV.gain_ci(hl, b1, s, dev, hd),
                                        "heldout_attackers": MV.gain_ci(hl, b1, s, ho, hd)},
            "verified_only": MV.gain_ci([r for r in hl if C._POOL_OF.get(r["repo"]) == "verified"],
                                        b1, s, ho, hd),
            "rq4_detectors": {st: MV.gain_ci(cell(rho, st), b1, s, ho, hd)
                              for st in sorted({r["setting"] for r in recs if r["rho_patch"] == rho})},
        }
    gate = _load("eval-gate-world.jsonl")
    summary["gate_world"] = {
        f"{rho:g}": {p: {"worst_case_harm": MV.value(MV.harm_table(
                         [r for r in gate if r["rho_patch"] == rho], p, ho, hd)),
                         "false_blocks_per_ep": (lambda rs: sum(r["false_blocks"] for r in rs) / len(rs) if rs else float("nan"))(
                             [r for r in gate if r["rho_patch"] == rho and r["policy"] == p])}
                     for p in G.GATE_BASELINES}
        for rho in sorted({r["rho_patch"] for r in gate})}
    (OUT / "eval-summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print("controls", json.dumps(ctrl), flush=True)
    print("curve_rho", json.dumps({k: {x: v[x] for x in ("gain", "lo", "abs_diff", "rel_reliable", "meets_margin")}
                                   for k, v in summary["curve_rho"].items()}), flush=True)
    return summary


def summarise_sweeps():
    """The sweeps, read on the held-out class at Delta in {4, 8} (budget: {2, 4, 8}), per rho.
    Line 8 is read on Sentinel alone (B1 has no line 8): its worst-case harm and FQ% at every
    eta_Q of the grid (SS11: "as quarantine becomes cheap").  Budget x chi is EXPLORATORY (D4b)."""
    ho, hd = A.held_out(), list(D.HEADLINE_DELTAS)
    b1, s = "B1 audit-at-commit", "Sentinel-A1"
    out = {}
    eta = _load("sweep-eta.jsonl")
    for rho in sorted({r["rho_patch"] for r in eta}):
        for e in sorted({r["eta_q"] for r in eta}):
            rs = [r for r in eta if r["rho_patch"] == rho and r["eta_q"] == e]
            out.setdefault("eta", {}).setdefault(f"{rho:g}", {})[f"{e:g}"] = {
                "worst_case_harm": MV.value(MV.harm_table(rs, s, ho, hd)), **MV.side(rs, s, ho, hd)}
    for name, key in (("sweep-match.jsonl", "match"), ("sweep-persistent-drift.jsonl", "drift_visible")):
        rs_all = _load(name)
        for rho in sorted({r["rho_patch"] for r in rs_all}):
            for v in sorted({str(r[key]) for r in rs_all}):
                rs = [r for r in rs_all if r["rho_patch"] == rho and str(r[key]) == v]
                out.setdefault(key, {}).setdefault(f"{rho:g}", {})[v] = MV.gain_ci(rs, b1, s, ho, hd, n_boot=2000)
    bud = _load("sweep-budget-EXPLORATORY.jsonl")
    for rho in sorted({r["rho_patch"] for r in bud}):
        for chi in sorted({r["chi"] for r in bud}):
            for sh in sorted({r["budget"] for r in bud}):
                for d in sorted({r["delta"] for r in bud}):
                    rs = [r for r in bud if r["rho_patch"] == rho and r["chi"] == chi
                          and r["budget"] == sh and r["delta"] == d]
                    out.setdefault("budget_EXPLORATORY", {}).setdefault(f"{rho:g}", {}).setdefault(
                        f"chi={chi:g}", {}).setdefault(sh, {})[str(d)] = MV.gain_ci(rs, b1, s, ho, [d], n_boot=2000)
    (OUT / "eval-sweeps-summary.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
