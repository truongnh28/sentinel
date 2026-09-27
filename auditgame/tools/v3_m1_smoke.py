#!/usr/bin/env python3
"""tools/v3_m1_smoke.py -- milestone M1 of v3 P2: the v3 world with the baselines, end to end
on DEV (plan S7, S10 "M1").  DEV ONLY: the seal refuses every other split before any work.

THE SLICE (plan S7 "Lat chay").  Primary world; every rho in {0, 0.25, 0.5, 1}; chi = 1.33;
the mid detector (d' = 2.21); K_d = 2; budget b1; Delta in {0, 1, 4}; 2 seeds; the 100 dev
workflows; the 18 scripted attacker columns and the cross-fitted best response (D27).
Systems: every baseline of v3/baselines.BASELINES (B1-B6, cost-greedy, SW randomised,
B1-prov) and the Oracle (+) control.  B5 and SW randomised run at their declared
pre-tuning values (tau5 = 0.3, "commit3"): T18 has not tuned them.  A no-defence reference
("none (reference)", api.PolicyBase: never audits, never quarantines) runs the scripted
columns only; it is a diagnostic for gate 3, not a system.

N4 as v2 (tools/run_draft_eval.py): an (attack, workflow, seed) whose task sigma is not
solved in the clean run is skipped (carrier_runner.survives); a scripted rule with no
feasible placement leaves the denominator (N3).  Both are counted and printed.

V = max over the attacker columns of the workflow-weighted column mean harm (v3/metrics.py
table().value).  Here the columns are the 18 scripted rules (the M1 slice); the held-out-7
V is printed beside it.  V_BR is metrics.v_best_response (cross-fitted, D27).

ACCEPTANCE (plan S7), each marked pass / fail.  The tolerances below are DECLARED HERE,
before the run, and are not moved after it:
  1. the nine named tests green (tests/v3, run separately; the report quotes the run);
  2. D28 controls (metrics.Readout.controls, per rho):
       (+) V(Oracle) <= 0.05 at Delta = 4, at every rho;
       (-) at Delta = 0 no sweep-only baseline (B3, B4, B6) has V below V(B1), at every rho;
  3. direction of B1 (no number is checked):
       a. V(B1) does not increase with rho: at every Delta, each step up in rho raises V(B1)
          by at most TOL_RHO = 0.02 (seed / column noise);
       b. at rho = 0, B1 misses every harm that goes only through the delegated route: the
          share of MARKED delegated sigma-patches its commit review blocks is not above the
          share of CLEAN patches it blocks (the false-alarm rate) by more than 2 binomial SE
          -- the review carries no information on a delegated patch;
       c. V(B1) is near flat in Delta: at every rho, max - min over Delta <= TOL_FLAT = 0.05;
  4. one B1 episode <= 1.1 ms (single process, measured apart from the grid);
  5. test_v3_leaves_v2_freeze_clean green (run separately).

OUTPUT.  A summary JSON (--out, default spikes/v3-m1/m1-summary.json) that
docs/reports/v3-p2-m1.md is written from.  The per-episode rows stay in memory.

    cd auditgame
    ../.venv/bin/python tools/v3_m1_smoke.py --jobs 8
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import platform
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent.parent            # auditgame/
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import carrier_runner                                               # noqa: E402
from v3 import api as A                                             # noqa: E402
from v3 import attackers as AT                                      # noqa: E402
from v3 import baselines as BL                                      # noqa: E402
from v3 import config as C                                          # noqa: E402
from v3 import corpus as K                                          # noqa: E402
from v3 import metrics as M                                         # noqa: E402
from v3 import oracle as OR                                         # noqa: E402
from v3 import runner as R                                          # noqa: E402
from v3 import seal                                                 # noqa: E402

SPLIT = R.DEV
RHOS = tuple(C.RHO_GRID)
DELTAS = (0, 1, 4)
SEEDS = (0, 1)
CHI = "1.33"
DPRIME = 2.21
K_D = 2
ORACLE = BL.OracleControl.name
B1 = BL.B1AuditAtCommit.name
SYSTEMS = tuple(BL.BASELINES) + (ORACLE,)
NONE = "none (reference)"
TOL_RHO = 0.02
TOL_FLAT = 0.05
CONTROL_MAX = M.CONTROL_MAX_HARM
TIMING_BUDGET_MS = 1.1
OUT = HERE / "spikes" / "v3-m1" / "m1-summary.json"

_DEV: list | None = None


class NoDefence(A.PolicyBase):
    name = NONE


def dev() -> list:
    global _DEV
    if _DEV is None:
        _DEV = K.dev_workflows()
    return _DEV


def refuse_unless_dev(split: str) -> None:
    """The seal: this smoke runs on dev only.  Anything else is refused before any work,
    and the runner's own check (runner.check_split) refuses it again without a token."""
    if split != SPLIT:
        raise seal.SealedSplit(f"tools/v3_m1_smoke.py is a dev smoke: split {split!r} is "
                               f"refused (plan S6; eval is P5, run by the user)")
    R.check_split(split)


def cell_of(rho, delta) -> C.Cell:
    return C.Cell(rho=rho, delta=delta, k_delegated=K_D, chi=CHI, dprime=DPRIME)


def factory(system, pl):
    if system == NONE:
        return NoDefence
    if system == ORACLE:
        return BL.factory(ORACLE, attacked=pl.k)
    return BL.factory(system)


def sigma_patch(ep, pl, delegated) -> dict | None:
    """Evaluator-side trace of the patch written at sigma: marked?  route?  blocked?"""
    items = {it.item_id: it for k in ep.store.items for it in ep.store.items[k]}
    for it in ep.store.items[OR.BRANCH]:
        if it.provenance == OR.PATCH_PROVENANCE and it.created_at == pl.sigma:
            via = ""
            if it.poisoned:
                src = [items[i].carrier for i in it.derived_from if i in items]
                via = "delegated" if any(k in delegated for k in src) else "direct"
            return {"marked": bool(it.poisoned), "via": via,
                    "removed": it.item_id in ep.store.quarantined}
    return None


def slim(rec: A.EpisodeRecord, counters: dict) -> dict:
    return {"split": rec.split, "policy": rec.policy, "attack": rec.attack,
            "delta": rec.delta, "wf": rec.wf, "repo": rec.repo, "seed": rec.seed,
            "placement": rec.placement, "iota": rec.iota, "harm": rec.harm,
            "fq": rec.fq, "true_q": rec.true_q, "false_removed": rec.false_removed,
            "benign_inspected": rec.benign_inspected, "t_lost": rec.t_lost,
            "clean_lost_branch": rec.clean_lost_branch, "n_solved": rec.n_solved,
            "spent": rec.spent, "budget": rec.budget,
            "audits": {k: len(v) for k, v in rec.audits.items()},
            "quarantines": [list(q) for q in rec.quarantines],
            "detected_at": rec.detected_at,
            "patch_blocks": counters["patch_blocks"], "clean_blocked": counters["clean_blocked"]}


def work(job) -> dict:
    """One (rho, Delta, workflow): scripted columns for every system + the reference, and
    the best-response menu for every system."""
    rho, delta, wi, seeds = job
    wf = dev()[wi]
    cell = cell_of(rho, delta)
    delegated = set(cell.delegated())
    out = {"rows": [], "br": [], "b1_trace": [], "n_infeasible": 0, "n_nonsurv": 0,
           "n_br_nonsurv": 0, "sec": {}}

    def run(system, pl, seed, attack, br):
        t0 = time.perf_counter()
        ep = R.Episode(wf, pl, factory(system, pl), C.PRIMARY, cell, seed, split=SPLIT,
                       attack=attack, best_response=br)
        rec = ep.run().record
        out["sec"][system] = out["sec"].get(system, 0.0) + time.perf_counter() - t0
        return ep, rec

    for name in sorted(AT.SCRIPTED):
        pl = AT.SCRIPTED[name].plan(wf, delta)
        if pl is None:
            out["n_infeasible"] += 1
            continue
        for s in seeds:
            if not carrier_runner.survives(wf, pl.payloads[0], s):
                out["n_nonsurv"] += 1
                continue
            for system in SYSTEMS + (NONE,):
                ep, rec = run(system, pl, s, name, False)
                out["rows"].append(slim(rec, ep.counters()))
                if system == B1:
                    tr = sigma_patch(ep, pl, delegated)
                    clean = [it for it in ep.store.items[OR.BRANCH]
                             if it.provenance == OR.PATCH_PROVENANCE and not it.poisoned]
                    out["b1_trace"].append({
                        "attack": name, "wf": wf.wf_id, "seed": s, "harm": rec.harm,
                        "sigma": tr, "clean_patches": len(clean),
                        "clean_blocked": sum(it.item_id in ep.store.quarantined for it in clean)})
    for pl in AT.br_menu(wf, delta):
        for s in seeds:
            if not carrier_runner.survives(wf, pl.payloads[0], s):
                out["n_br_nonsurv"] += 1
                continue
            for system in SYSTEMS:
                _, rec = run(system, pl, s, "BR", True)
                out["br"].append({"split": rec.split, "policy": system, "placement": rec.placement,
                                  "delta": delta, "wf": wf.wf_id, "seed": s, "harm": rec.harm})
    out.update(rho=rho, delta=delta, wi=wi)
    return out


def time_b1(n_wf: int) -> dict:
    """Gate 4: B1 episodes, single process, rho = 0, Delta = 4, the scripted columns.
    Per-episode wall time of Episode(...).run() (placement planned outside)."""
    cell = cell_of(0.0, 4)
    eps = []
    for wf in dev()[:n_wf]:
        for name in sorted(AT.SCRIPTED):
            pl = AT.SCRIPTED[name].plan(wf, 4)
            if pl is None:
                continue
            for s in SEEDS:
                eps.append((wf, pl, s))
    fac = BL.factory(B1)
    for wf, pl, s in eps[:50]:                                     # warm-up
        R.Episode(wf, pl, fac, C.PRIMARY, cell, s).run()
    ts = []
    for wf, pl, s in eps:
        t0 = time.perf_counter()
        R.Episode(wf, pl, fac, C.PRIMARY, cell, s).run()
        ts.append(time.perf_counter() - t0)
    ms = [1000 * t for t in ts]
    return {"n": len(ms), "mean_ms": statistics.fmean(ms), "median_ms": statistics.median(ms),
            "p90_ms": sorted(ms)[int(0.9 * len(ms))], "budget_ms": TIMING_BUDGET_MS,
            "pass": statistics.fmean(ms) <= TIMING_BUDGET_MS}


def _f(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else x


def summarise(parts, n_wf) -> dict:
    scripted = sorted(AT.SCRIPTED)
    held = AT.held_out()
    rows = {rho: [] for rho in RHOS}
    br = {rho: [] for rho in RHOS}
    trace = []
    counts = {"infeasible_rule_wf_delta": 0, "nonsurviving_scripted": 0,
              "nonsurviving_br": 0}
    sec = {}
    for p in parts:
        rows[p["rho"]] += p["rows"]
        br[p["rho"]] += p["br"]
        if p["rho"] == 0.0:
            trace += [dict(t, delta=p["delta"]) for t in p["b1_trace"]]
        counts["infeasible_rule_wf_delta"] += p["n_infeasible"]
        counts["nonsurviving_scripted"] += p["n_nonsurv"]
        counts["nonsurviving_br"] += p["n_br_nonsurv"]
        for k, v in p["sec"].items():
            sec[k] = sec.get(k, 0.0) + v
    V, Vh, VBR, side, n_ep = {}, {}, {}, {}, {}
    for rho in RHOS:
        rs = rows[rho]
        for system in SYSTEMS + (NONE,):
            for d in DELTAS:
                key = f"{system}|{rho}|{d}"
                V[key] = _f(M.table(rs, system, scripted, (d,)).value)
                Vh[key] = _f(M.table(rs, system, held, (d,)).value)
                if system != NONE:
                    VBR[key] = _f(M.v_best_response(br[rho], system, (d,))["v_br"])
            sd = M.side(rs, system, scripted, DELTAS)
            blocks = [r for r in rs if r["policy"] == system]
            side[f"{system}|{rho}"] = {
                "clean_completion": _f(sd["clean_completion"]),
                "fq_per_ep": _f(sd["fq_per_ep"]),
                "false_quarantine_pct": _f(sd["false_quarantine_pct"]),
                "false_removed_per_ep": _f(sd["false_removed_per_ep"]),
                "audit_cost_share_pct": _f(sd["audit_cost_share_pct"]),
                "detection_rate_pct": _f(sd["detection_rate_pct"]),
                "clean_blocked_per_ep": sum(r["clean_blocked"] for r in blocks) / max(1, len(blocks)),
                "clean_lost_branch_per_ep": sum(r["clean_lost_branch"] for r in blocks) / max(1, len(blocks)),
                "patch_blocks_per_ep": sum(r["patch_blocks"] for r in blocks) / max(1, len(blocks)),
                "n_episodes": sd["n_episodes"]}
            n_ep[f"{system}|{rho}"] = len(blocks)
    # ---- gates -------------------------------------------------------------------------
    gates = {}
    ctrl = {}
    for rho in RHOS:
        ro = M.Readout(rows[rho])
        c = ro.controls(ORACLE, B1, BL.SWEEP_ONLY, scripted, headline_deltas=(4,), zero_delta=0)
        ctrl[str(rho)] = {k: (_f(v) if not isinstance(v, dict) else {a: _f(b) for a, b in v.items()})
                          for k, v in c.items()}
    gates["2+ oracle V <= 0.05 at Delta = 4"] = {
        "pass": all(ctrl[str(r)]["positive_ok"] for r in RHOS),
        "values": {str(r): ctrl[str(r)]["v_oracle_headline"] for r in RHOS}}
    gates["2- no sweep-only baseline beats B1 at Delta = 0"] = {
        "pass": all(ctrl[str(r)]["negative_ok"] for r in RHOS),
        "values": {str(r): {"B1": ctrl[str(r)]["v_b1_delta0"], **ctrl[str(r)]["v_sweepers_delta0"]}
                   for r in RHOS}}
    steps = {}
    ok_a = True
    for d in DELTAS:
        vs = [V[f"{B1}|{r}|{d}"] for r in RHOS]
        ups = [vs[i + 1] - vs[i] for i in range(len(vs) - 1)]
        steps[str(d)] = {"V": vs, "steps": ups}
        ok_a &= all(u <= TOL_RHO for u in ups)
    gates["3a V(B1) does not increase with rho"] = {"pass": ok_a, "tol": TOL_RHO, "values": steps}
    dm = [t for t in trace if t["sigma"] and t["sigma"]["marked"] and t["sigma"]["via"] == "delegated"]
    di = [t for t in trace if t["sigma"] and t["sigma"]["marked"] and t["sigma"]["via"] == "direct"]
    n_clean = sum(t["clean_patches"] for t in trace)
    p_clean = sum(t["clean_blocked"] for t in trace) / n_clean if n_clean else float("nan")
    p_del = sum(t["sigma"]["removed"] for t in dm) / len(dm) if dm else float("nan")
    p_dir = sum(t["sigma"]["removed"] for t in di) / len(di) if di else float("nan")
    se = math.sqrt(p_clean * (1 - p_clean) / len(dm) + p_clean * (1 - p_clean) / n_clean) \
        if dm and n_clean else float("nan")
    harm_del = sum(t["harm"] for t in dm) / len(dm) if dm else float("nan")
    gates["3b rho = 0: B1 misses harm through the delegated route"] = {
        "pass": bool(dm) and p_del <= p_clean + 2 * se,
        "n_delegated_marked": len(dm), "blocked_share_delegated": _f(p_del),
        "n_direct_marked": len(di), "blocked_share_direct": _f(p_dir),
        "n_clean_patches": n_clean, "blocked_share_clean": _f(p_clean), "se": _f(se),
        "harm_rate_delegated_marked": _f(harm_del)}
    flat = {}
    ok_c = True
    for r in RHOS:
        vs = [V[f"{B1}|{r}|{d}"] for d in DELTAS]
        flat[str(r)] = {"V": vs, "range": max(vs) - min(vs)}
        ok_c &= max(vs) - min(vs) <= TOL_FLAT
    gates["3c V(B1) near flat in Delta"] = {"pass": ok_c, "tol": TOL_FLAT, "values": flat}
    return {"V": V, "V_heldout": Vh, "V_BR": VBR, "side": side, "n_episodes": n_ep,
            "controls": ctrl, "gates": gates, "counts": counts,
            "cpu_sec_by_system": sec,
            "n_records": sum(len(v) for v in rows.values()),
            "n_br_records": sum(len(v) for v in br.values()), "n_workflows": n_wf}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", default=SPLIT, help="dev only; anything else is refused")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--workflows", type=int, default=C.DEV_N_WORKFLOWS)
    ap.add_argument("--timing-workflows", type=int, default=50)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    refuse_unless_dev(a.split)
    n_wf = min(a.workflows, len(dev()))
    t_start = time.time()
    timing = time_b1(min(a.timing_workflows, n_wf))
    print(f"B1 timing: {timing['mean_ms']:.3f} ms mean over {timing['n']} episodes")
    jobs = [(rho, d, wi, SEEDS) for rho in RHOS for d in DELTAS for wi in range(n_wf)]
    parts = []
    t0 = time.time()
    with ProcessPoolExecutor(a.jobs) as ex:
        for i, p in enumerate(ex.map(work, jobs, chunksize=4)):
            parts.append(p)
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(jobs)} jobs, {time.time() - t0:.0f} s", flush=True)
    grid_sec = time.time() - t0
    summ = summarise(parts, n_wf)
    summ["timing_b1"] = timing
    summ["wall_sec_grid"] = grid_sec
    summ["wall_sec_total"] = time.time() - t_start
    summ["config"] = {"split": SPLIT, "world": C.world_name(C.PRIMARY), "rhos": list(RHOS),
                      "deltas": list(DELTAS), "seeds": list(SEEDS), "chi": CHI,
                      "dprime": DPRIME, "k_delegated": K_D, "budget": C.BUDGET_PRIMARY,
                      "n_workflows": n_wf, "systems": list(SYSTEMS), "reference": NONE,
                      "scripted": sorted(AT.SCRIPTED), "held_out": AT.held_out(),
                      "br_eps": list(AT.BR_EPS), "jobs": a.jobs,
                      "machine": f"{platform.machine()} {platform.system()} "
                                 f"{os.cpu_count()} cpu, python {platform.python_version()}",
                      "tuned": {"tau5": BL.TAU5_DEFAULT, "sw_weights": BL.SW_DEFAULT}}
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summ, indent=1, sort_keys=True, default=str) + "\n")
    print(f"grid: {summ['n_records']} scripted + {summ['n_br_records']} BR episodes in "
          f"{grid_sec:.0f} s with {a.jobs} jobs -> {out}")
    for g, v in summ["gates"].items():
        print(f"  {'PASS' if v['pass'] else 'FAIL'}  {g}")
    print(f"  {'PASS' if timing['pass'] else 'FAIL'}  4 B1 episode <= {TIMING_BUDGET_MS} ms "
          f"({timing['mean_ms']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
