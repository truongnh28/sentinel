"""Pilot 1 -- the v2 world AS THE PLAN WRITES IT, on DEV only (django), tuning columns only (D18).

Question: before any tuning, what do B1..B6 and the 28 library members score on harm and on L,
and what would a minimax mixture on L (the plan's line 5) pick?  No held-out attacker, no eval repo.
"""
import json, sys, time
from concurrent.futures import ProcessPoolExecutor

import attackers_v2 as A
import corpus_v2 as C
import draft_setup as D
import metrics
import stage_policies as SP
import staged as S
from core import seed_of
from tools.select_mixture import make_world

DELTAS = (0, 2, 4, 8)
SEEDS = (1, 2)
RHOS = (0.0, 0.25, 0.5, 1.0)
POLICIES = list(SP.BASELINES) + sorted(SP.LIBRARY)


def dev():
    w = C.make_corpus_v2(pools=("verified",))
    return [x for x in w if x.repo == "django/django"]


def job(args):
    pol_name, rho = args
    K = D.STAGE_KAPPA_DRAFT
    world = make_world("mid", "nominal", rho_patch=rho)
    out = {}
    for an in A.tuning_attack_names():
        for d in DELTAS:
            for wf in dev():
                got = A.by_name(an).plan(wf, d)
                if got is None:
                    continue
                for s in SEEDS:
                    if not S.survives_staged(wf, got[0], world, s, K):
                        continue
                    pol = SP.make_v2(pol_name, budget=D.BudgetSpec().budget(wf.H), kappa=K, H=wf.H,
                                     rng_seed=seed_of(wf.wf_id, s), setting="mid", tuned={},
                                     action_mode="single", rho_patch=rho)
                    r = S.run_staged(wf, got, pol, world, s, K, action_mode="single")
                    out.setdefault(f"{an}@{d}", []).append(
                        (r.harm, r.q_false, r.t_lost, metrics.loss(r.harm, r.q_false, r.t_lost)))
    return pol_name, rho, out


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(p, r) for p in POLICIES for r in RHOS]
    res = {}
    with ProcessPoolExecutor(10) as ex:
        for p, r, out in ex.map(job, jobs):
            res.setdefault(str(r), {})[p] = out
    json.dump(res, open("pilot1.json", "w"))
    print(f"done {len(jobs)} jobs in {time.time()-t0:.0f}s")
