"""select_mixture.py -- all v2 tuning, on DEV only, before the v2 freeze.

Per action mode:
  1. betas (once): per-carrier drift rate estimated from OBSERVED alarms on dev clean runs
     (method of moments, D6; draft SS7 "estimated online") -- never from drift labels
  2. tau5: B5's threshold, argmin worst-case L on dev (D12)
  3. mixture per (detector, chi): M[pi,a] = max over 3 kernels of dev L on the D18 columns
     (dev scripted + BR columns that are not a held-out rule);
     x* = argmin_x max_a x.M[:,a] (scipy linprog); also nominal-kernel x and pure argmin (D9)
  4. tau_Q: Sentinel-A1's line-8 gate on p_attack, argmin worst-case L on dev
     (eta_Q is NOT tuned: it is the Bayes threshold lambda_Q/(1+lambda_Q), D11)
Ties go to the smaller parameter.

    ../.venv/bin/python tools/select_mixture.py --jobs 10
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import attackers_v2 as A
import corpus_v2 as C
import detector
import draft_setup as D
import metrics
import stage_policies as SP
import staged as S
import world_v2 as W
from core import CARRIERS, CarrierStore, seed_of

KERNELS = {"nominal": (0.85, 0.55), "low": (0.85 - D.ZETA, 0.55 - D.ZETA),
           "high": (min(1.0, 0.85 + D.ZETA), 0.55 + D.ZETA)}


def make_world(setting, kernel="nominal", betas=None, match=1.0, rho_patch=1.0):
    adopt, skill = KERNELS[kernel]

    def world(seed):
        ag = W.StagedMockAgent(adoption_rate=adopt, skill_induction_rate=skill,
                               drift_rates=D.BETA_WORLD if betas is None else betas)
        return ag, W.DriftDetector(detector.Detector.from_setting(setting), ag.drift_ids,
                                   match, rho_patch)
    return world


def dev_attack_names():
    return A.tuning_attack_names()                   # D18: held-out rules never enter tuning


def cell_loss(job):
    name, attack_name, delta, setting, chi, kernel, tuned, seeds, mode, rho = job
    K = D.stage_kappa_for_chi(chi)
    world = make_world(setting, kernel, rho_patch=rho)
    dev, _ = C.split(C.make_corpus_v2())
    vals = []
    for wf in dev:
        got = A.by_name(attack_name).plan(wf, delta)
        if got is None:
            continue
        for s in seeds:
            if not S.survives_staged(wf, got[0], world, s, K):
                continue
            pol = SP.make_v2(name, budget=D.BudgetSpec().budget(wf.H), kappa=K, H=wf.H,
                             rng_seed=seed_of(wf.wf_id, s), setting=setting, tuned=tuned,
                             action_mode=mode, rho_patch=rho)
            r = S.run_staged(wf, got, pol, world, s, K, action_mode=mode)
            vals.append(metrics.loss(r.harm, r.q_false, r.t_lost))
    return name, f"{attack_name}@{delta}", kernel, (sum(vals) / len(vals) if vals else None)


def matrix3(names, setting, chi, kernels, tuned, seeds, jobs, mode, rho):
    """{name: {column: {kernel: dev L}}} -- computed ONCE per cell; both reductions read it."""
    todo = [(n, a, d, setting, chi, k, tuned, seeds, mode, rho)
            for n in names for a in dev_attack_names() for d in D.DELTAS for k in kernels]
    M3: dict = {}
    with ProcessPoolExecutor(jobs) as ex:
        for n, col, k, v in ex.map(cell_loss, todo, chunksize=8):
            if v is not None:
                M3.setdefault(n, {}).setdefault(col, {})[k] = v
    return M3


def reduce(M3, names, kernels):
    """Max over `kernels`; a column enters only where every kernel was measured."""
    M = {n: {c: max(v[k] for k in kernels) for c, v in M3.get(n, {}).items()
             if all(k in v for k in kernels)} for n in names}
    cols = sorted({c for row in M.values() for c in row})
    return M, cols


def minimax(M, names, cols):
    from scipy.optimize import linprog
    cols = [c for c in cols if all(c in M[n] for n in names)]
    P = len(names)
    res = linprog(c=[0.0] * P + [1.0],
                  A_ub=[[M[n][c] for n in names] + [-1.0] for c in cols], b_ub=[0.0] * len(cols),
                  A_eq=[[1.0] * P + [0.0]], b_eq=[1.0],
                  bounds=[(0, None)] * P + [(None, None)], method="highs")
    x = {n: round(float(v), 6) for n, v in zip(names, res.x[:P]) if v > 1e-6}
    pure = min(names, key=lambda n: (max(M[n][c] for c in cols), n))
    return x, pure, float(res.x[-1])


def worst_L(name, tuned, seeds, jobs, mode, rho):
    M, _ = reduce(matrix3([name], D.HEADLINE_DETECTOR, D.HEADLINE_CHI, ["nominal"], tuned,
                          seeds, jobs, mode, rho), [name], ["nominal"])
    return max(M[name].values())


class _Probe(W.OpenGates):
    """Observe-only insertion probe: counts every new item and its alarm, blocks nothing."""
    def __init__(self, det, t, seed, F, N):
        self.det, self.t, self.seed, self.F, self.N = det, t, seed, F, N

    def admit(self, item, stage):
        self.N[item.carrier] += 1
        self.F[item.carrier] += int(self.det.fires(self.det.score(item, self.t, self.seed)))
        return True


def estimate_betas(seeds=(1, 2, 3), setting=D.HEADLINE_DETECTOR):
    """D6: method of moments from OBSERVABLES on dev clean runs -- never from drift labels.

    With every new item probed, carrier k over T tasks gives F_k alarms from N_k items.
    Drift fires at psi (matched), everything else at phi, so
        E[F_k] = beta_k*T*psi + (N_k - beta_k*T)*phi
        beta_k = (F_k - N_k*phi) / (T*(psi - phi)),   clipped at 0.
    psi and phi are the detector's known operating point (Assumption 2).
    """
    base = detector.Detector.from_setting(setting)
    psi, phi = base.psi, base.phi
    dev, _ = C.split(C.make_corpus_v2())
    F, N, T = {c: 0 for c in CARRIERS}, {c: 0 for c in CARRIERS}, 0
    for wf in dev:
        topics = [x.topic for x in wf.tasks]
        for s in seeds:
            ag = W.StagedMockAgent(drift_rates=D.BETA_WORLD)
            det, st = W.DriftDetector(base, ag.drift_ids), CarrierStore()
            for t, task in enumerate(wf.tasks):
                ag.run_task(t, task, st, seed=s, marker="x", gates=_Probe(det, t, s, F, N),
                            wf_topics=topics)
                T += 1
    return {c: max(0.0, (F[c] - N[c] * phi) / (T * (psi - phi))) for c in CARRIERS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2])       # cut (T1): --seeds 1
    ap.add_argument("--modes", nargs="+", default=list(D.ACTION_MODES))
    ap.add_argument("--pool-detectors", action="store_true")               # cut (T2)
    ap.add_argument("--reuse-single-mix", action="store_true")             # cut (T3)
    ap.add_argument("--rhos", type=float, nargs="+", default=list(D.RHO_PATCH_GRID))  # cut (T4): 0.25 1
    ap.add_argument("--out", default=str(SP.TUNED_PATH))
    a = ap.parse_args()
    seeds = tuple(a.seeds)
    tuned = {"betas": estimate_betas(), "modes": {}}
    print("betas (estimated)", tuned["betas"], "world", D.BETA_WORLD, flush=True)
    names = sorted(SP.LIBRARY)
    modes = ["single"] if a.reuse_single_mix else a.modes      # T3: cfg_for falls back to single
    for mode in modes:
        for rho in a.rhos:
            # D20: the defender knows the world's rho (Assumption 2) and is tuned for it
            cfg = tuned["modes"].setdefault(mode, {}).setdefault(f"{rho:g}", {"tau_q": 1.0, "mix": {}})
            best = None
            for tau5 in (0.2, 0.3, 0.5, 0.7):
                cfg["tau5"] = tau5
                v = worst_L("B5 risk-score", tuned, seeds, a.jobs, mode, rho)
                best = min(best or (v, tau5), (v, tau5))
            cfg["tau5"] = best[1]
            print(mode, rho, "tau5", best, flush=True)
            settings = [D.HEADLINE_DETECTOR] if a.pool_detectors else list(D.DETECTORS)
            for chi in D.CHIS:
                for setting in settings:
                    M3 = matrix3(names, setting, chi, list(KERNELS), tuned, seeds, a.jobs, mode, rho)
                    M, cols = reduce(M3, names, list(KERNELS))
                    Mn, _ = reduce(M3, names, ["nominal"])
                    x, pure, v = minimax(M, names, cols)
                    xn, _, _ = minimax(Mn, names, cols)
                    cell = {"robust": x, "nominal": xn, "pure": pure, "value": v}
                    for st in (D.DETECTORS if a.pool_detectors else [setting]):
                        cfg["mix"][f"{st}|{round(chi, 2)}"] = cell
                    print(mode, rho, setting, chi, x, pure, round(v, 4), flush=True)
            best = None
            for tq in (0.5, 0.7, 0.9, 0.99):
                cfg["tau_q"] = tq
                v = worst_L("Sentinel-A1", tuned, seeds, a.jobs, mode, rho)
                best = min(best or (v, tq), (v, tq))
            cfg["tau_q"] = best[1]
            print(mode, rho, "tau_q", best, flush=True)
    pathlib.Path(a.out).write_text(json.dumps(tuned, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
