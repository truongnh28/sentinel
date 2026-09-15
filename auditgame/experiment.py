#!/usr/bin/env python3
"""
experiment.py -- The AuditGame-SE experiment driver.

Sweeps the grid (Delta x chi x detector) and prints the table the way the
manuscript requires: REPORT ON THE GRID, DO NOT POOL.  A single pooled number
averages the regime where the method helps together with the regime where it does
not.

    python3 experiment.py                  # defaults
    python3 experiment.py --n 60 --json r.json
"""
from __future__ import annotations
import argparse, json, random, sys
import build, agent, datasets, detector, metrics, runner
import policies as P

def gain(row):
    """Percent reduction in worst-case harm, Sentinel vs B1 audit-at-commit."""
    b1 = row["B1 audit-at-commit"].harm
    return 100.0 * (b1 - row["Sentinel"].harm) / max(b1, 1e-9)

def make_corpus(n, H, seed):
    rng = random.Random(seed)
    return [build.make_workflow(f"wf-{i:03d}", "django", H, rng) for i in range(n)]

def sweep_delta(wfs, deltas, det_name, budget, seeds, carriers, chi=None):
    """One (policy x Delta) grid at one detector setting and one chi.

    `chi` patches policies.KAPPA for the duration.  It is a module-level dict, so
    there is no way to pass a cost table in -- the same reason fixtures.Profile
    patches it rather than parameterising.
    """
    det, ag = detector.Detector.from_setting(det_name), agent.MockAgent()
    old = dict(P.KAPPA)
    if chi is not None:
        P.KAPPA.clear(); P.KAPPA.update(P.kappa_for_chi(chi, old))
    try:
        out = {}
        for d in deltas:
            row = {}
            for name in P.REGISTRY:
                runner.reset_survivor_cache()
                row[name] = runner.worst_case(name, wfs, (d,), carriers, det, ag,
                                              budget, seeds, det_name)
            out[d] = row
        return out
    finally:
        P.KAPPA.clear(); P.KAPPA.update(old)


def sweep_chi(wfs, deltas, det_name, budget, seeds, carriers, chis):
    """RQ2's axis, swept for the first time.

    experiment.py's docstring claimed a (Delta x chi x detector) grid while the code
    looped over deltas and detector settings only -- chi was a property of one fixed
    KAPPA table, so RQ2 had never been tested even though tables kept printing.
    """
    return {c: sweep_delta(wfs, deltas, det_name, budget, seeds, carriers, chi=c)
            for c in chis}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="number of workflows")
    ap.add_argument("--H", type=int, default=8, help="tasks per workflow")
    ap.add_argument("--budget", type=float, default=17.95)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--dataset", choices=("mock", "swebench"), default="mock",
                    help="mock: synthetic workflows, numbers unchanged from "
                         "before. swebench: real SWE-bench metadata via "
                         "datasets.REGISTRY -- the agent is still MockAgent; "
                         "a real agent plugs in at this same spot via "
                         "agents.REGISTRY (Task 16), no separate code path.")
    ap.add_argument("--json", metavar="FILE")
    a = ap.parse_args()

    # `--dataset mock` (the default) MUST keep calling make_corpus, not
    # datasets.REGISTRY["mock"].workflows(): MockDataset.workflows() seeds each
    # workflow independently via seed_of(seed, i), while make_corpus shares ONE
    # rng across the whole corpus -- routing the default path through the
    # registry would move every existing number in the mock table.
    if a.dataset == "mock":
        wfs = make_corpus(a.n, a.H, seed=2026)
        scope = datasets.REGISTRY["mock"].scope()
    else:
        if a.dataset not in datasets.REGISTRY:
            _, reason = datasets.PENDING.get(a.dataset, (None, "not registered"))
            print(f"dataset {a.dataset!r} is not available: {reason}")
            return 1
        ds = datasets.REGISTRY[a.dataset]
        wfs = list(ds.workflows(a.n, a.H, seed=2026))
        scope = ds.scope()

    seeds = tuple(range(1, a.seeds + 1))
    deltas = (0, 1, 2, 4)
    # D5 -- the attacker class must cover ALL FOUR carriers.  Sweeping only
    # {memory, skill} takes the two CHEAPEST carriers (0.4 and 0.9), so chi -- the
    # cost spread BETWEEN carriers -- is nearly fixed, and RQ2 was never actually
    # tested even though the table kept printing numbers.
    carriers = ("memory", "skill", "queue", "branch")

    print("=" * 78)
    print("AuditGame-SE -- grid sweep (mock agent, no LLM spend)")
    # Real and mock numbers must NEVER share one unlabeled table (a3 Bước 3.6b).
    print(f"dataset={a.dataset} is_mock={scope.is_mock}")
    print(f"{a.n} workflows - H={a.H} - B={a.budget} - {a.seeds} seeds - "
          f"injection carriers: {', '.join(carriers)}")
    print("=" * 78)

    results = {}
    for det_name in ("weak", "mid", "strong"):
        psi, phi = detector.SETTINGS[det_name]
        print(f"\n[detector = {det_name}]  psi={psi} phi={phi}")
        grid = sweep_delta(wfs, deltas, det_name, a.budget, seeds, carriers)
        results[det_name] = grid
        names = list(P.REGISTRY)
        print(f"  {'policy':24s}" + "".join(f"{'D='+str(d):>9s}" for d in deltas))
        print("  " + "-" * (24 + 9 * len(deltas)))
        for nm in names:
            print(f"  {nm:24s}" + "".join(f"{grid[d][nm].harm:9.3f}" for d in deltas))
        print(f"  {'-> Sentinel vs B1':24s}"
              + "".join(f"{gain(grid[d]):+8.1f}%" for d in deltas))

        # N3 -- harm never travels alone; and CI95 is resampled BY WORKFLOW
        c0 = grid[deltas[0]]["Sentinel"]
        print(f"  {'feasible':24s}" + "".join(
            f"{grid[d]['Sentinel'].n_feasible:>4d}/{grid[d]['Sentinel'].n_total:<4d}" for d in deltas))
        print(f"  {'Q_false / wf (lambda_Q)':24s}"
              + "".join(f"{grid[d]['Sentinel'].q_false:9.2f}" for d in deltas))
        print(f"  {'T_lost / wf  B1 (lam_T)':24s}"
              + "".join(f"{grid[d]['B1 audit-at-commit'].t_lost:9.2f}" for d in deltas))
        # A4 -- what each policy actually SPENT, not just its cap.  "Equal budget"
        # is true of the cap and false of the spend: measured, B5 reaches B1's harm
        # on 2% of the budget.  A harm table without this reads policies as
        # comparable when one of them declined to play.
        print()
        print(metrics.spend_table(
            {nm: grid[deltas[0]][nm].spent_mean for nm in names
             if grid[deltas[0]][nm].spent_mean == grid[deltas[0]][nm].spent_mean},
            a.budget))

        # A1 -- the composite loss, and the weight at which the ranking flips.
        cells = {nm: (grid[deltas[0]][nm].harm, grid[deltas[0]][nm].q_false,
                      grid[deltas[0]][nm].t_lost) for nm in names}
        star = metrics.lambda_q_star(cells)
        print(f"\n  lambda_Q* = {star:.4f}" if star is not None else
              "\n  lambda_Q* = none (one policy dominates on every term)")
        print(f"  {'policy':<28}{'L(0)':>9}{'L(lQ*)':>10}")
        for nm in sorted(names, key=lambda k: metrics.loss(*cells[k])):
            l0 = metrics.loss(*cells[nm], lambda_Q=0.0)
            ls = metrics.loss(*cells[nm], lambda_Q=(star or 0.0) + 1e-6)
            print(f"  {nm:<28}{l0:>9.3f}{ls:>10.3f}")

        for d in deltas:
            lo, hi = runner.bootstrap_paired(grid[d]["B1 audit-at-commit"].per_wf,
                                             grid[d]["Sentinel"].per_wf)
            b1, sn = grid[d]["B1 audit-at-commit"], grid[d]["Sentinel"]
            print(f"     D={d}  d-harm = {b1.harm - sn.harm:+.3f}"
                  f"  CI95 [{lo:+.3f} ; {hi:+.3f}]"
                  f"   {'excludes 0' if lo > 0 else 'CI COVERS 0'}")

    print("\n" + "=" * 78)
    print("READING THE TABLE")
    print("=" * 78)
    g = results["mid"]
    gains = [gain(g[d]) for d in deltas]
    print(f"  Gain by Delta (detector mid): "
          + " - ".join(f"D={d}:{gv:+.0f}%" for d, gv in zip(deltas, gains)))
    print(f"  Monotone increasing in Delta: {'YES' if all(gains[i] <= gains[i+1]+1e-9 for i in range(len(gains)-1)) else 'NO'}"
          "   <- this is RQ1 / Corollary 5")
    w = [gain(results[s][d]) for s in ("weak", "strong") for d in (4,)]
    print(f"  Gain at Delta=4:  WEAK detector {w[0]:+.0f}%  -  STRONG detector {w[1]:+.0f}%")
    print(f"  Largest advantage when the detector is weakest: {'YES' if w[0] >= w[1] else 'NO'}"
          "   <- RQ4, allocation COMPENSATES for detection quality")

    if a.json:
        from dataclasses import asdict
        dump = {s: {str(d): {nm: asdict(c) for nm, c in row.items()}
                    for d, row in grid.items()} for s, grid in results.items()}
        json.dump(dump, open(a.json, "w"), indent=2, ensure_ascii=False)
        print(f"\n  wrote {a.json}")

if __name__ == "__main__":
    sys.exit(main())
