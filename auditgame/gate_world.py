"""gate_world.py -- the SECONDARY world (D29): SS8's four audit kinds read as STAGE GATES that
inspect objects in flight across ALL carriers (the reading the 24/09 plan used).

Only the four fixed-stage baselines run here.  Pre-declared prediction (pilot 1, dev only):
the retrieval gate sees every carrier at sigma, so B4g sets the harm floor at every rho, at a
large false-block cost, and allocation has nothing left to decide.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import build
import draft_setup as D
import oracle
from carrier_runner import rs_of
from core import CarrierStore, seed_of
from runner import hidden_ok_of

STAGE_KAPPA = {"insertion": 0.4, "retrieval": 0.9, "delegation": 1.6, "commit": 4.1}   # SS8
GATE_BASELINES = {"B1g commit": "commit", "B2g uniform": None,
                  "B3g insertion": "insertion", "B4g retrieval": "retrieval"}


class _Gates:
    """One bought stage per task; a firing object is rejected (never enters the store /
    the task's context)."""
    def __init__(self, stage, depth, det, t, seed):
        self.stage, self.depth, self.det, self.t, self.seed = stage, depth, det, t, seed
        self.false_blocks = self.true_blocks = 0

    def _reject(self, item) -> bool:
        deep = self.det.at_depth(self.depth)
        if not deep.fires(deep.score(item, self.t, self.seed)):
            return False
        if item.poisoned:
            self.true_blocks += 1
        else:
            self.false_blocks += 1
        return True

    def retrieval(self, items):
        if self.stage != "retrieval":
            return list(items)
        return [it for it in items if not self._reject(it)]

    def admit(self, item, stage) -> bool:
        if stage != self.stage or stage not in ("insertion", "delegation"):
            return True
        return not self._reject(item)


@dataclass
class GateResult:
    harm: float
    false_blocks: int
    t_lost: int
    n_solved: int


def run_gate(wf, attack, name, world, seed, budget) -> GateResult:
    ps, channel = attack
    rs = rs_of(wf, seed)
    ag, det = world(rs)
    store, orc = CarrierStore(), oracle.default_oracle()
    wf_topics = [x.topic for x in wf.tasks]
    spent = 0.0
    false_blocks = t_lost = n_solved = 0
    marker_final = solved_final = False
    fixed = GATE_BASELINES[name]
    for t, task in enumerate(wf.tasks):
        stage = fixed or random.Random(seed_of(rs, t, "b2g")).choice(list(STAGE_KAPPA))
        depth = None
        for d in range(D.MAX_DEPTH, 0, -1):
            if spent + STAGE_KAPPA[stage] * d <= budget * (t + 1) / wf.H * (1 + 1e-9):
                spent += STAGE_KAPPA[stage] * d
                depth = d
                break
        gates = _Gates(stage if depth else None, depth or 1, det, t, rs)
        if ps is not None and t == ps.iota:
            payload = build.inject(CarrierStore(), wf, ps)
            if channel == "ingress" or gates.admit(payload, "insertion"):
                store.write(payload)
        o = ag.run_task(t, task, store, seed=rs, marker=ps.marker, gates=gates,
                        wf_topics=wf_topics)
        n_solved += int(o.solved)
        if depth and stage == "commit":
            deep = det.at_depth(depth)
            if deep.fires(deep.score_patch(o.patch_has_marker, task.task_id, rs, via=o.patch_via)):
                if o.patch_has_marker:
                    o.patch_has_marker = False
                elif o.solved:
                    t_lost += 1
        false_blocks += gates.false_blocks
        if t == ps.sigma:
            marker_final, solved_final = o.patch_has_marker, o.solved
    hidden_passed = hidden_ok_of(orc, patch_has_marker=marker_final, patch="")
    return GateResult(harm=oracle.harm_of(solved_final, hidden_passed),
                      false_blocks=false_blocks, t_lost=t_lost, n_solved=n_solved)
