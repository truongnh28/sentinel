"""tune_d35.py -- the D35 addendum's tuning, on DEV only (preregistration D35).

  B2 FQ-matched, per (rho, Delta in {4, 8}): p* = argmin over P_GRID of the dev worst-case harm
     (max over the 3 kernels, over the tuning columns at that Delta), subject to dev FQ% (max over
     kernels, pooled over every Delta) <= fq_pct of Sentinel's mixture for mid|Delta; ties at 4
     decimals go to the lower FQ%, then the smaller p.  p = 1 (B1, FQ 0) is always feasible.
  A1 fixed interleave, per (rho, Delta in {4, 8}): the member of FIXED_LIBRARY with the lowest dev
     worst-case harm and FQ% <= D.FQ_CAP_PCT; ties: FQ%, then name (the rule of `pure`).
The dev measurement mirrors select_mixture.member_cell (seeds 1, 2; the 6 tuning columns; every
Delta), through the addendum's resolver.  Writes reference/d35_tuned.json, never v2_tuned.json.

    ../.venv/bin/python tools/tune_d35.py --jobs 10 | tee spikes/v2-addendum-dev/tune-log.txt
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import addendum_d35 as X
import attackers_v2 as A
import carrier_runner as R
import draft_setup as D
import sentinel as S
from tools.select_mixture import KERNELS, dev_workflows, make_world, reduce_kernels


def cell_d35(job):
    """select_mixture.member_cell through the addendum's resolver: one policy under one
    (setting, kernel, rho) on dev -- per-column harm means and the FQ%."""
    name, setting, kernel, rho, deltas, seeds, tuned = job
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
                    pol = X.make_policy_d35(name, budget=D.budget_b1(wf.H), kappa=K, H=wf.H,
                                            rng_seed=R.rs_of(wf, s), setting=setting,
                                            tuned=tuned, d35={}, rho_patch=rho, delta=d)
                    r = R.run_carrier(wf, got, pol, world, s, K)
                    cols.setdefault(f"{an}@{d}", []).append(r.harm)
                    fr += r.false_removed
                    bi += r.benign_inspected
    return (name, setting, kernel, rho, None,
            {c: sum(v) / len(v) for c, v in cols.items()}, 100.0 * fr / bi if bi else 0.0)


def _worst(M: dict, delta: int) -> float:
    return max(v for c, v in M.items() if c.endswith(f"@{delta}"))


def choose_p(cands, delta, target_fq) -> dict:
    """cands: {p: (M over columns, FQ%)}.  D35 arm B's rule."""
    ok = [(round(_worst(M, delta), 4), F, p, _worst(M, delta))
          for p, (M, F) in cands.items() if F <= target_fq + 1e-9]
    key, F, p, worst = min(ok)
    return {"p": p, "dev_worst": round(worst, 6), "dev_fq": round(F, 3), "target_fq": target_fq}


def choose_fixed(cands, delta, cap) -> dict:
    """cands: {member: (M over columns, FQ%)}.  D35 arm C's rule (that of `pure`)."""
    ok = [n for n, (_M, F) in cands.items() if F <= cap]
    pool = ok or list(cands)
    n = min(pool, key=lambda n: (_worst(cands[n][0], delta), cands[n][1], n))
    return {"member": n, "dev_worst": round(_worst(cands[n][0], delta), 6),
            "dev_fq": round(cands[n][1], 3), "cap_ok": bool(ok)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--out", default=str(X.D35_TUNED_PATH))
    a = ap.parse_args(argv)
    tuned, seeds, kernels = S.load_tuned(), tuple(D.TUNE_SEEDS), list(KERNELS)
    b2 = [f"{X.B2P_PREFIX}{p:g}" for p in X.P_GRID]
    names = b2 + sorted(X.FIXED_LIBRARY)
    jobs = [(n, D.HEADLINE_DETECTOR, k, rho, D.DELTAS, seeds, tuned)
            for rho in D.RHO_PATCH_GRID for n in names for k in kernels]
    with ProcessPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(cell_d35, jobs, chunksize=1))
    out = {"seeds": list(seeds), "p_grid": list(X.P_GRID), "fixed_library": sorted(X.FIXED_LIBRARY),
           "b2_fq": {}, "fixed": {}, "dev_rows": {}}
    for rho in D.RHO_PATCH_GRID:
        rk = f"{rho:g}"
        M, F, _cols = reduce_kernels([r for r in rows if r[3] == rho], kernels)
        mix = S.cfg_for(tuned, rho)["mix"]
        out["dev_rows"][rk] = {n: {"worst": {str(d): round(_worst(M[n], d), 6)
                                             for d in D.HEADLINE_DELTAS},
                                   "fq": round(F[n], 3)} for n in names}
        for d in D.HEADLINE_DELTAS:
            target = mix[S.mix_key(D.HEADLINE_DETECTOR, d)]["fq_pct"]
            out["b2_fq"].setdefault(rk, {})[str(d)] = choose_p(
                {float(n[len(X.B2P_PREFIX):]): (M[n], F[n]) for n in b2}, d, target)
            out["fixed"].setdefault(rk, {})[str(d)] = choose_fixed(
                {n: (M[n], F[n]) for n in X.FIXED_LIBRARY}, d, D.FQ_CAP_PCT)
            print(rk, d, "b2_fq", out["b2_fq"][rk][str(d)], "fixed", out["fixed"][rk][str(d)],
                  flush=True)
    path = pathlib.Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
