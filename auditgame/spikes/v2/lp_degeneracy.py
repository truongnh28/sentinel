"""DEV-only diagnostic behind D32: is the per-cell minimax LP degenerate (many optimal mixtures)?

Run at 4c02883, before D32, against that commit's reference/v2_tuned.json; its output is
lp-degeneracy-pre-D32.txt.  From auditgame/:  ../.venv/bin/python spikes/v2/lp_degeneracy.py

For each rho (at its tuned eta_Q) and each (detector, regime) cell, recompute M, F exactly as
tools/select_mixture.tune_rho step c does, then report:
  v*        the LP optimum (should equal the committed value)
  n_pure    how many pure members already reach v* (ties -> the LP vertex is arbitrary)
  fq_lp     FQ% of the committed LP mixture
  fq_min    the lowest FQ% among mixtures with worst case <= v* (second-stage LP)
  mean_lp / mean_min   mean harm over the cell's columns for the two mixtures
Nothing is written into the repo.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import carrier_policies as CP  # noqa: E402
import draft_setup as D  # noqa: E402
import select_mixture as SM  # noqa: E402
from scipy.optimize import linprog  # noqa: E402


def second_stage(M, F, names, cols, v, obj):
    """min obj.x  s.t.  worst case <= v, FQ <= cap, simplex."""
    P = len(names)
    A_ub = [[M[n][c] for n in names] for c in cols] + [[F[n] for n in names]]
    b_ub = [v + 2e-6] * len(cols) + [D.FQ_CAP_PCT]   # v is rounded to 6 d.p.
    res = linprog(c=obj, A_ub=A_ub, b_ub=b_ub, A_eq=[[1.0] * P], b_eq=[1.0],
                  bounds=[(0, None)] * P, method="highs")
    return {n: float(w) for n, w in zip(names, res.x) if w > 1e-6} if res.status == 0 else None


def main():
    tuned = json.loads((ROOT / "reference/v2_tuned.json").read_text())
    names = sorted(CP.LIBRARY)
    kernels = list(SM.KERNELS)
    seeds = tuple(D.TUNE_SEEDS)
    for rho in D.RHO_PATCH_GRID:
        blk = tuned["rho"][f"{rho:g}"]
        rows = SM.run_jobs([(n, st, k, rho, blk["eta_q"], D.DELTAS, seeds, tuned)
                            for n in names for st in D.DETECTORS for k in kernels], 10)
        for st in D.DETECTORS:
            sub = [r for r in rows if r[1] == st]
            for regime in list(D.DELTAS) + ["all"]:
                keep = (lambda c: True) if regime == "all" else (lambda c, d=regime: c.endswith(f"@{d}"))
                pick = [(n, s_, k, r_, e, {c: v for c, v in cols.items() if keep(c)}, fq)
                        for n, s_, k, r_, e, cols, fq in sub]
                M, F, cols = SM.reduce_kernels(pick, kernels)
                cell = SM.constrained_minimax(M, F, names, cols, D.FQ_CAP_PCT)
                v = cell["value"]
                committed = blk["mix"][f"{st}|{regime}"]
                same = cell["robust"] == committed["robust"]
                worst = {n: max(M[n][c] for c in cols) for n in names}
                n_pure = sum(1 for n in names if worst[n] <= v + 2e-6 and F[n] <= D.FQ_CAP_PCT)
                xf = second_stage(M, F, names, cols, v, [F[n] for n in names])
                xm = second_stage(M, F, names, cols, v, [sum(M[n][c] for c in cols) / len(cols) for n in names])

                def fq(x):
                    return sum(w * F[n] for n, w in x.items())

                def mean(x):
                    return sum(w * sum(M[n][c] for c in cols) / len(cols) for n, w in x.items())
                x0 = cell["robust"]
                print(f"rho={rho:g} {st:6s} {str(regime):3s} v*={v:.4f} same_as_committed={same} "
                      f"n_pure_at_v*={n_pure:2d} | LP: fq={fq(x0):.2f} mean={mean(x0):.4f} "
                      f"| minFQ: fq={fq(xf):.2f} mean={mean(xf):.4f} "
                      f"| minMean: fq={fq(xm):.2f} mean={mean(xm):.4f} top={max(xm, key=xm.get)}",
                      flush=True)


if __name__ == "__main__":
    main()
