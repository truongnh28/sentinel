"""DEV-only record of D32's effect on the committed tuned table.

For every (rho, detector, regime) cell, at the rho's committed eta_Q, recompute M, F on dev as
tools/select_mixture.tune_rho step c does, then solve the cell twice:
  before  constrained_minimax exactly as committed at 4c02883 (read from git): the first LP's
          vertex, and `pure` by (worst case, name)
  after   today's constrained_minimax (D32): the second LP, and `pure` by (worst case, FQ%, name)
and compare both with reference/v2_tuned.json.  Its output is d32-effect.txt.

    ../.venv/bin/python spikes/v2/d32_effect.py        (from auditgame/)
"""
import json
import pathlib
import subprocess
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import carrier_policies as CP  # noqa: E402
import draft_setup as D  # noqa: E402
import select_mixture as SM  # noqa: E402

BEFORE = "4c02883"


def module_at(commit):
    src = subprocess.run(["git", "show", f"{commit}:auditgame/tools/select_mixture.py"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    mod = types.ModuleType(f"select_mixture_{commit}")
    mod.__file__ = str(ROOT / "tools" / "select_mixture.py")
    exec(compile(src, f"select_mixture@{commit}", "exec"), mod.__dict__)
    return mod


def moved(a, b, tol=1e-5):
    return any(abs(a.get(n, 0.0) - b.get(n, 0.0)) > tol for n in set(a) | set(b))


def main():
    old = module_at(BEFORE)
    tuned = json.loads((ROOT / "reference/v2_tuned.json").read_text())
    names, kernels = sorted(CP.LIBRARY), list(SM.KERNELS)
    n = n_repro = n_robust = n_pure = 0
    for rho in D.RHO_PATCH_GRID:
        blk = tuned["rho"][f"{rho:g}"]
        rows = SM.run_jobs([(p, st, k, rho, blk["eta_q"], D.DELTAS, D.TUNE_SEEDS, tuned)
                            for p in names for st in D.DETECTORS for k in kernels], 10)
        for st in D.DETECTORS:
            sub = [r for r in rows if r[1] == st]
            for regime in list(D.DELTAS) + ["all"]:
                keep = (lambda c: True) if regime == "all" else (lambda c, d=regime: c.endswith(f"@{d}"))
                pick = [(p, s_, k, r_, e, {c: v for c, v in cols.items() if keep(c)}, fq)
                        for p, s_, k, r_, e, cols, fq in sub]
                M, F, cols = SM.reduce_kernels(pick, kernels)
                before = old.constrained_minimax(M, F, names, cols, D.FQ_CAP_PCT)
                after = SM.constrained_minimax(M, F, names, cols, D.FQ_CAP_PCT)
                table = blk["mix"][f"{st}|{regime}"]
                n += 1
                n_repro += (after["robust"] == table["robust"] and after["pure"] == table["pure"])
                worst = {p: max(M[p][c] for c in cols) for p in names}
                tied = [p for p in names if worst[p] == worst[after["pure"]] and F[p] <= D.FQ_CAP_PCT]
                r_moved = moved(before["robust"], after["robust"])
                p_moved = before["pure"] != after["pure"]
                n_robust += r_moved
                n_pure += p_moved
                if r_moved or p_moved or len(tied) > 1:
                    print(f"rho={rho:g} {st:6s} {regime!s:3s} "
                          f"robust {'MOVED' if r_moved else 'same '} fq {before['fq_pct']:.3f} -> {after['fq_pct']:.3f} | "
                          f"pure {before['pure']} -> {after['pure']} "
                          f"(tied at worst {worst[after['pure']]:.4f}: {len(tied)}, "
                          f"FQ% of the tied: min {min(F[p] for p in tied):.2f}, max {max(F[p] for p in tied):.2f})",
                          flush=True)
    print(f"cells {n}; committed table reproduced (robust and pure) in {n_repro}; "
          f"robust moved (> 1e-5) in {n_robust}; pure changed in {n_pure}")


if __name__ == "__main__":
    main()
