"""select_mixture.py -- all v2 tuning, on DEV only (the django family), before the v2 freeze.

  1. betas: method of moments on OBSERVED alarms of dev clean runs (D6) -- never drift labels
  2. per rho in the grid (the defender knows rho, Assumption 2):
     a. tau5 (B5): argmin worst-case dev harm at the headline cell (D12)
     b. eta_Q (line 8): for each grid value, the constrained minimax over the 28 members at
        the headline cell (mid, Delta in {4, 8}, 3 kernels); keep the value with the lowest
        worst-case harm, ties (4 decimals) to the lower FQ% (D11)
     c. at that eta_Q, per (detector, regime), regime in DELTAS + ["all"] (line 1, D9b):
        M[pi, col] = max over 3 kernels of dev harm, F_pi = FQ% (max over kernels);
        LP  min z  s.t.  sum_pi x_pi M[pi,col] <= z (every col),  sum_pi x_pi F_pi <= cap,
        sum x = 1, x >= 0   (SS4 objective, D26); the nominal-kernel LP; the pure argmin
Columns are attackers.tuning_attack_names() (D18): no behaviour a held-out attacker can show.
Other ties go to the smaller parameter.

    ../.venv/bin/python tools/select_mixture.py --jobs 10
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor
from statistics import NormalDist

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import attackers_v2 as A
import carrier_policies as CP
import carrier_runner as R
import corpus_v2 as C
import detector
import draft_setup as D
import sentinel as S
import world_v2 as W
from core import CARRIERS, CarrierStore

KERNELS = {"nominal": (0.85, 0.55), "low": (0.85 - D.ZETA, 0.55 - D.ZETA),
           "high": (min(1.0, 0.85 + D.ZETA), 0.55 + D.ZETA)}


def make_world(setting, kernel="nominal", rho=1.0, match=D.DRIFT_MATCH,
               drift_visible=D.DRIFT_VISIBLE_TASKS, betas=None):
    adopt, skill = KERNELS[kernel]

    def world(rs):
        ag = W.StagedMockAgent(adoption_rate=adopt, skill_induction_rate=skill,
                               drift_rates=D.BETA_WORLD if betas is None else betas)
        return ag, W.DriftDetector(detector.Detector.from_setting(setting), ag.drift_ids,
                                   match, rho, None, drift_visible)
    return world


def dev_workflows():
    return C.split(C.make_corpus_v2())[0]


def member_cell(job):
    """One policy under one (setting, kernel, rho, eta_q) on dev: per column harm mean,
    plus the false-removal and inspection totals that make its FQ%."""
    name, setting, kernel, rho, eta_q, deltas, seeds, tuned = job
    K = D.TARGET_KAPPA_DRAFT
    world = make_world(setting, kernel, rho)
    cols, fr, bi = {}, 0, 0
    for an in A.tuning_attack_names():
        for d in deltas:
            for wf in dev_workflows():
                got = A.by_name(an).plan(wf, d)
                if got is None:
                    continue
                for s in seeds:
                    if not R.survives(wf, got[0], s):
                        continue
                    pol = S.make_policy(name, budget=D.budget_b1(wf.H), kappa=K, H=wf.H,
                                        rng_seed=R.rs_of(wf, s), setting=setting, tuned=tuned,
                                        rho_patch=rho, delta=d, eta_q=eta_q)
                    r = R.run_carrier(wf, got, pol, world, s, K)
                    cols.setdefault(f"{an}@{d}", []).append(r.harm)
                    fr += r.false_removed
                    bi += r.benign_inspected
    return (name, setting, kernel, rho, eta_q,
            {c: sum(v) / len(v) for c, v in cols.items()}, 100.0 * fr / bi if bi else 0.0)


def run_jobs(jobs, n):
    with ProcessPoolExecutor(n) as ex:
        return list(ex.map(member_cell, jobs, chunksize=1))


def constrained_minimax(M, F, names, cols, cap):
    """min_x max_col x.M[:, col]  s.t.  x.F <= cap (D26).  Falls back to the unconstrained
    LP, flagged, if no mixture meets the cap."""
    from scipy.optimize import linprog
    cols = [c for c in cols if all(c in M[n] for n in names)]
    P = len(names)
    A_ub = [[M[n][c] for n in names] + [-1.0] for c in cols]
    b_ub = [0.0] * len(cols)
    res = linprog(c=[0.0] * P + [1.0], A_ub=A_ub + [[F[n] for n in names] + [0.0]],
                  b_ub=b_ub + [cap], A_eq=[[1.0] * P + [0.0]], b_eq=[1.0],
                  bounds=[(0, None)] * P + [(None, None)], method="highs")
    cap_ok = res.status == 0
    if not cap_ok:
        res = linprog(c=[0.0] * P + [1.0], A_ub=A_ub, b_ub=b_ub, A_eq=[[1.0] * P + [0.0]],
                      b_eq=[1.0], bounds=[(0, None)] * P + [(None, None)], method="highs")
    x = {n: round(float(v), 6) for n, v in zip(names, res.x[:P]) if v > 1e-6}
    ok = [n for n in names if F[n] <= cap] or list(names)
    pure = min(ok, key=lambda n: (max(M[n][c] for c in cols), n))
    fq = sum(w * F[n] for n, w in x.items())
    return {"robust": x, "pure": pure, "value": round(float(res.x[-1]), 6),
            "fq_pct": round(fq, 3), "cap_ok": cap_ok}


def reduce_kernels(rows, kernels):
    """rows: member_cell outputs for one (setting, rho, eta_q) -> M (max over kernels), F."""
    M, F = {}, {}
    for name, _s, kern, _r, _e, cols, fq in rows:
        if kern not in kernels:
            continue
        for c, v in cols.items():
            M.setdefault(name, {}).setdefault(c, {})[kern] = v
        F[name] = max(F.get(name, 0.0), fq)
    M = {n: {c: max(v.values()) for c, v in row.items() if len(v) == len(kernels)}
         for n, row in M.items()}
    cols = sorted({c for row in M.values() for c in row})
    return M, F, cols


class _Probe(W.OpenGates):
    """Observe-only insertion probe for the beta estimator: counts every new item and its
    depth-1 alarm, blocks nothing."""
    def __init__(self, det, t, seed, F, N):
        self.det, self.t, self.seed, self.F, self.N = det, t, seed, F, N

    def admit(self, item, stage):
        self.N[item.carrier] += 1
        self.F[item.carrier] += int(self.det.fires(self.det.score(item, self.t, self.seed)))
        return True


def estimate_betas(seeds=D.TUNE_SEEDS, setting=D.HEADLINE_DETECTOR, match=D.DRIFT_MATCH):
    """D6: method of moments from OBSERVABLES on dev clean runs -- never from drift labels.
    A drift event is new when it is created, so an insertion probe sees it while it is still
    anomalous: E[F_k] = beta_k*T*psi_m + (N_k - beta_k*T)*phi, psi_m = P(fire | match*d')."""
    base = detector.Detector.from_setting(setting)
    psi_m = NormalDist().cdf(match * base.d_prime - base.tau_det)
    phi = base.phi
    F, N, T = {c: 0 for c in CARRIERS}, {c: 0 for c in CARRIERS}, 0
    for wf in dev_workflows():
        topics = [x.topic for x in wf.tasks]
        for s in seeds:
            rs = R.rs_of(wf, s)
            ag = W.StagedMockAgent(drift_rates=D.BETA_WORLD)
            det, st = W.DriftDetector(base, ag.drift_ids, match), CarrierStore()
            for t, task in enumerate(wf.tasks):
                ag.run_task(t, task, st, seed=rs, marker="x", gates=_Probe(det, t, rs, F, N),
                            wf_topics=topics)
                T += 1
    return {c: max(0.0, (F[c] - N[c] * phi) / (T * (psi_m - phi))) if psi_m > phi else 0.0
            for c in CARRIERS}


def tune_rho(rho, tuned, seeds, jobs, settings):
    names = sorted(CP.LIBRARY)
    kernels = list(KERNELS)
    blk = tuned["rho"].setdefault(f"{rho:g}", {"mix": {}})
    # a. tau5 for B5
    best = None
    for tau5 in D.TAU5_GRID:
        blk["tau5"] = tau5
        (_, _, _, _, _, cols, _), = run_jobs([("B5 risk-score", D.HEADLINE_DETECTOR, "nominal",
                                               rho, None, D.HEADLINE_DELTAS, seeds, tuned)], 1)
        v = max(cols.values())
        best = min(best or (v, tau5), (v, tau5))
    blk["tau5"] = best[1]
    print(rho, "tau5", best, flush=True)
    # b. eta_Q at the headline cell
    rows = run_jobs([(n, D.HEADLINE_DETECTOR, k, rho, e, D.HEADLINE_DELTAS, seeds, tuned)
                     for n in names for k in kernels for e in D.ETA_Q_GRID], jobs)
    best = None
    for e in D.ETA_Q_GRID:
        M, F, cols = reduce_kernels([r for r in rows if r[4] == e], kernels)
        cell = constrained_minimax(M, F, names, cols, D.FQ_CAP_PCT)
        print(rho, "eta_q", e, cell["value"], cell["fq_pct"], flush=True)
        # lexicographic (SS4 objective): worst-case harm first, then false quarantine
        key = (round(cell["value"], 4), cell["fq_pct"], e)
        best = min(best or key, key)
    blk["eta_q"] = best[2]
    # c. the mixtures, per (detector, regime), at that eta_Q
    rows = run_jobs([(n, st, k, rho, blk["eta_q"], D.DELTAS, seeds, tuned)
                     for n in names for st in settings for k in kernels], jobs)
    for st in settings:
        sub = [r for r in rows if r[1] == st]
        for regime in list(D.DELTAS) + ["all"]:
            keep = (lambda c: True) if regime == "all" else (lambda c, d=regime: c.endswith(f"@{d}"))
            pick = [(n, s_, k, r_, e, {c: v for c, v in cols.items() if keep(c)}, fq)
                    for n, s_, k, r_, e, cols, fq in sub]
            M, F, cols = reduce_kernels(pick, kernels)
            Mn, Fn, _ = reduce_kernels(pick, ["nominal"])
            cell = constrained_minimax(M, F, names, cols, D.FQ_CAP_PCT)
            cell["nominal"] = constrained_minimax(Mn, Fn, names, cols, D.FQ_CAP_PCT)["robust"]
            blk["mix"][S.mix_key(st, regime)] = cell
            print(rho, st, regime, cell["robust"], cell["value"], cell["fq_pct"], flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(D.TUNE_SEEDS))    # cut (T1): 1
    ap.add_argument("--pool-detectors", action="store_true")                      # cut (T2)
    ap.add_argument("--rhos", type=float, nargs="+", default=list(D.RHO_PATCH_GRID))  # cut (T3)
    ap.add_argument("--out", default=str(S.TUNED_PATH))
    a = ap.parse_args()
    seeds = tuple(a.seeds)
    tuned = {"betas": estimate_betas(seeds), "rho": {}}
    print("betas (estimated)", tuned["betas"], "world", D.BETA_WORLD, flush=True)
    settings = [D.HEADLINE_DETECTOR] if a.pool_detectors else list(D.DETECTORS)
    for rho in a.rhos:
        tune_rho(rho, tuned, seeds, a.jobs, settings)
        if a.pool_detectors:
            blk = tuned["rho"][f"{rho:g}"]["mix"]
            for regime in list(D.DELTAS) + ["all"]:
                for st in D.DETECTORS:
                    blk[S.mix_key(st, regime)] = blk[S.mix_key(D.HEADLINE_DETECTOR, regime)]
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(tuned, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
