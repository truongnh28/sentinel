"""One sweep, four worlds -- replaces stackelberg_value / stackelberg_guarded /
llm_cost_game / ssg_llm_world, which were four copies of the same loop.

    python3 spikes/ssg_sweep.py legacy     placeholder kappa, synthetic detector
    python3 spikes/ssg_sweep.py usd        kappa in LLM dollars, synthetic detector
    python3 spikes/ssg_sweep.py prose      USD kappa, PROSE world, LLM judge

WHY THE OLD SPIKES WERE WRONG, recorded so the corrected numbers can be read
against the ones already circulated.  Each of them averaged harm FLAT over
episodes.  `paired` returns None whenever an instance does not survive the
clean phase, so workflows contribute UNEQUAL numbers of episodes -- 75 of an
expected 120 in one measured cell -- and a flat mean therefore weights each
workflow by how often it survived, which correlates with the outcome.
`GridCell` already names `per_wf` "the bootstrap UNIT (not the case)" and
`runner.worst_case` averages per workflow.  The spikes deviated from the
repo's own convention.

It changed the answer, not just the digits: at d'=1.42 the flat mean ranked
branch/Delta=2 (0.7701) above memory/Delta=0 (0.7600), while the per-workflow
mean ranks memory/Delta=0 (0.7875) above branch/Delta=2 (0.7792).  The
reported BEST RESPONSE was wrong, not only the value.

This file calls `runner.stackelberg_value` instead of carrying its own loop.
"""
from __future__ import annotations
import json, pathlib, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import agent, attacks, costs, metrics, policies as P, prose_world as PW, runner  # noqa: E402
import dprime_sweep as DS                                                        # noqa: E402

DELTAS = (0, 2, 4)
CARRIERS = tuple(sorted(attacks.CARRIERS_ALL))
SEEDS = (1, 2, 3, 4, 5)
N_WF, H, SETTING = 40, 8, "mid"

POLICIES = ("B1 audit-at-commit", "B5 risk-score", "Sentinel",
            "SentinelW window-belief", "B7 minimax-lp", "SSG-G guarded")

#: d' grid for the synthetic worlds. 0.06 and 1.42 are MEASURED from D_llm
#: (AUC 0.518 covert, 0.843 self-declaring); the rest bracket them.
D_PRIMES = (0.0, 0.06, 0.5, 1.42, 2.2)


def detector_for(world: str, dp: float):
    """The detector, and whether its d' was measured or set."""
    if world != "prose":
        return DS.make_detector(dp), {"d_prime": dp, "source": "swept parameter"}
    from detector_llm import LlmDetector
    pos, neg = PW.judgeable_texts()
    det = LlmDetector.from_cache(pos, neg)
    det.patch_detector = DS.make_detector(det.d_prime)
    return det, {"d_prime": det.d_prime, "source": "MEASURED from the judge cache",
                 "patch_channel_d_prime": det.d_prime,
                 "patch_channel_note": "DECLARED, not measured -- the judge reads "
                                       "notes, not diffs",
                 "hard_split": {"vs_ordinary_advice": 10.598,
                                "vs_minimal_pair_twin": -0.119}}


def main(world: str) -> int:
    budget = costs.budget_for(H) if world != "legacy" else costs.LEGACY_BUDGET
    if world != "legacy":
        costs.install(P)
    if world == "prose":
        PW.enable()
    wfs = DS.make_corpus(N_WF, H, seed=DS.CORPUS_SEED)
    ag = agent.MockAgent()
    grid = (None,) if world == "prose" else D_PRIMES
    out = {"meta": {"world": world, "budget": budget, "seeds": list(SEEDS),
                    "n_wf": N_WF, "deltas": list(DELTAS),
                    "kappa": dict(P.KAPPA), "kappa_commit": P.KAPPA_COMMIT,
                    "value": "runner.stackelberg_value -- max over configs of the "
                             "MEAN OVER WORKFLOWS (per-workflow is the unit)"},
           "cells": []}
    for dp in grid:
        det, dmeta = detector_for(world, dp)
        row = {}
        for pol in POLICIES:
            runner.reset_survivor_cache()
            t0 = time.time()
            v = runner.stackelberg_value(pol, wfs, DELTAS, CARRIERS, det, ag,
                                         budget, SEEDS, SETTING)
            if v.get("value") is not None:
                v["L10"] = metrics.loss(v["value"], v["q_false"], v["t_lost"],
                                        lambda_Q=0.10, lambda_T=0.0)
                print("  %-26s V=%.4f L10=%.4f BR=(%s,D=%d) n_wf=%d (%.0fs)"
                      % (pol, v["value"], v["L10"], v["carrier"], v["delta"],
                         v["n_wf"], time.time() - t0), flush=True)
            else:
                print("  %-26s %s" % (pol, v["reason"]), flush=True)
            row[pol] = v
        out["cells"].append({"detector": dmeta, "policies": row})
    path = HERE / f"ssg-sweep-{world}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    if world == "prose":
        PW.disable()
    print(f"-> {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "usd"))
