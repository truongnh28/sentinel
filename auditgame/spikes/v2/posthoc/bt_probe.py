"""Review probe (read-only, synthetic workflows only; no dev/eval record is touched).

1. Does a BeliefThreshold member ever switch between commit and sweep on a natural trajectory?
2. What is the floor of p_attack that the never-informative windows (Delta = 0, branch) impose?
3. Are BT tau >= 0.5 members episode-for-episode identical to L-SW-commit / B1?
"""
import collections
import random
import pathlib
import sys

AUDITGAME = pathlib.Path(__file__).resolve().parents[3]     # auditgame/
sys.path.insert(0, str(AUDITGAME))

import belief_v2 as BV
import build
import carrier_policies as CP
import carrier_runner as R
import detector
import draft_setup as D
from core import CARRIERS, seed_of
import world_v2 as W

K = D.TARGET_KAPPA_DRAFT
BETAS = {"memory": 0.3058, "skill": 0.0654, "queue": 0.0326, "branch": 0.0141}


def world(rs):
    ag = W.StagedMockAgent(drift_rates=D.BETA_WORLD)
    return ag, W.DriftDetector(detector.Detector.from_setting("mid"), ag.drift_ids, 1.0, 0.25)


def floor_of(H):
    b = BV.DriftBelief(CARRIERS, H, D.DELTAS, BETAS)
    never = sum(v for w, v in b.b.items() if w != b.NULL and (w[0] == "branch" or w[1] == w[2]))
    return never / (never + b.b[b.NULL])


print("p_attack floor from never-informative windows, by H:",
      {H: round(floor_of(H), 4) for H in range(6, 15)})


class Tracking:
    """Wrap a member; record every action it asks for and its p_attack before acting."""
    def __init__(self, m):
        self.m, self.acts, self.p = m, [], []

    def __getattr__(self, k):
        return getattr(self.m, k)

    def act(self, t):
        self.p.append(self.m.belief.p_attack())
        a = self.m.act(t)
        self.acts.append(a[0] if a else None)
        return a


wfs = [build.make_workflow(f"probe-{i}", "repo-00", 6 + i % 9, random.Random(seed_of("probe", i)))
       for i in range(60)]
switch = collections.Counter()
minp = {}
for name in sorted(n for n in CP.LIBRARY if "-BT-" in n):
    for wf in wfs:
        cands = build.plan_poison_all(wf, "memory", 2)
        att = (cands[0], "write") if cands else None
        for s in (1, 2, 3):
            pol = Tracking(CP.make_member(name, D.budget_b1(wf.H), K, wf.H, R.rs_of(wf, s), "mid",
                                          {}, BETAS, 0.0))
            R.run_carrier(wf, att, pol, world, s, K)
            kinds = {"commit" if a == D.COMMIT else "sweep" for a in pol.acts}
            switch[(name, tuple(sorted(kinds)))] += 1
            minp[name] = min(minp.get(name, 1.0), min(pol.p))
for (name, kinds), n in sorted(switch.items()):
    print(f"{name:14s} action kinds seen {kinds}: {n} episodes; min p_attack {minp[name]:.4f}")

# 3. identical episodes: BT tau>=0.5 vs L-SW-commit vs B1
diff = collections.Counter()
for wf in wfs:
    cands = build.plan_poison_all(wf, "skill", 2)
    if not cands:
        continue
    for s in (1, 2, 3):
        if not R.survives(wf, cands[0], s):
            continue
        ref = R.run_carrier(wf, (cands[0], "write"), CP.B1AuditAtCommit(D.budget_b1(wf.H), K, wf.H),
                            world, s, K)
        for name in ["L-SW-commit"] + [n for n in CP.LIBRARY if "-BT-0.3" not in n and "-BT-" in n]:
            r = R.run_carrier(wf, (cands[0], "write"),
                              CP.make_member(name, D.budget_b1(wf.H), K, wf.H, R.rs_of(wf, s), "mid",
                                             {}, BETAS, 0.0), world, s, K)
            diff[name] += int(r != ref)
print("episodes differing from B1 (EpisodeResult !=):", dict(diff))
