"""scratch-only driver: a reduced eval on the smoke-tuned table, bypassing freeze."""
import json, pathlib, sys, time
sys.argv = ["x"]
import tools.run_draft_eval as E, sentinel as S, attackers_v2 as A, draft_setup as D, gate_world as G
SP = pathlib.Path(__file__).resolve().parent
def main():
    E.OUT = SP / "v2new" / "spikes" / "v2-smoke"
    tuned = json.loads((SP / "v2new/reference/v2_tuned_smoke.json").read_text())
    seeds = (1, 2, 3)
    ho = A.held_out()
    t0 = time.time()
    grid = [E.Job(p, c, d, "mid", rho) for rho in (0.25, 1.0) for p in S.REGISTRY for c in ho for d in (0, 4, 8)]
    print("main", E.run(E.work, [(j, tuned, seeds) for j in grid], 10, E.OUT / "eval-main.jsonl"), f"{time.time()-t0:.0f}s", flush=True)
    br = [((p, d, "mid", rho), tuned, seeds) for p in ("B1 audit-at-commit", "Sentinel-A1", "A1 -randomization", "B2 uniform random") for d in (4,) for rho in (0.25, 1.0)]
    print("br", E.run(E.br_work, br, 10, E.OUT / "eval-br.jsonl"), f"{time.time()-t0:.0f}s", flush=True)
    gate = [((n, c, d, rho), seeds) for n in G.GATE_BASELINES for c in ho for d in (4, 8) for rho in (0.25, 1.0)]
    print("gate", E.run(E.gate_work, gate, 10, E.OUT / "eval-gate-world.jsonl"), f"{time.time()-t0:.0f}s", flush=True)
    E.freeze.header_line = lambda *a, **k: "freeze: SCRATCH (not frozen)"
    s = E.summarise()
    for rho, g in s["curve_rho"].items():
        vb = s["curve_rho_vs_best"][rho]
        print(rho, "vs B1:", {k: g[k] for k in ("v_base", "v_cand", "gain", "lo", "abs_diff", "rel_reliable", "meets_margin")},
              "| vs best:", {k: vb[k] for k in ("best_baseline", "v_best", "v_cand", "abs_diff", "abs_lo", "abs_hi")})
        t2 = s["by_rho"][rho]["table2"]
        for p in S.REGISTRY:
            x = t2[p]; print(f"   {p:28s} V={x['worst_case_harm']:.3f} V_BR={x['v_br_crossfit']:.3f} FQ%={x['false_quarantine_pct']:.2f} CC={x['clean_completion']:.1f}")
        print("   fig3", {d: (v['v_base'], v['v_cand']) for d, v in s["by_rho"][rho]["figure3_gain_by_delta"].items()})
    print("gate", json.dumps(s["gate_world"], indent=None)[:600])


if __name__ == '__main__':
    main()
