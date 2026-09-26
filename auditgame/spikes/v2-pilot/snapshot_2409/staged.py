"""staged.py -- v2 runner: the draft's four audit stages (D1, D3, D5, D11, D15).

Inside task t:
  1. the policy's ranked plan; the first n_slots(mode) affordable actions are bought
  2. injection at iota: "write" passes the INSERTION gate, "ingress" does not
  3. the agent runs through RETRIEVAL, INSERTION, DELEGATION gates
  4. escalation hook (if a slot is left), then the COMMIT gate on the patch
  5. the defender sees only what it paid for, updates, may quarantine (line 8) --
     quarantine is priced in L (lambda_Q), not in the audit budget, unless q_price > 0
"""
from __future__ import annotations

from dataclasses import dataclass

import build
import draft_setup as D
import oracle
import scoring
from core import CARRIERS, CarrierStore, seed_of
from runner import hidden_ok_of

UPSTREAM = ("insertion", "retrieval", "delegation")


class AuditLog:
    def __init__(self):
        self.scores = {c: [] for c in CARRIERS}
        self.true_blocks = self.false_up = self.false_commit = 0
        self.first_detect = None
        self.fired = False
        self.patch_scores = []          # commit alarms: detection + escalation only (D17)
        self.false_objects = 0          # benign objects rejected or removed (FQ% numerator)
        self.benign_touched = 0         # benign objects the defender inspected or removed

    def record(self, carrier, s, d_prime):
        self.scores[carrier].append((s, d_prime))

    def posterior(self) -> dict:
        return {c: (scoring.carrier_score([s for s, _ in v], v[-1][1]) if v else None)
                for c, v in self.scores.items()}


class Gates:
    def __init__(self, stages, det, t, seed, log, gate_mode):
        self.stages, self.det, self.t, self.seed, self.log = stages, det, t, seed, log
        self.gate_mode = gate_mode

    def _inspect(self, item, stage) -> bool:
        """Score one object at `stage`; return True iff it is REJECTED."""
        deep = self.det.at_depth(self.stages[stage])
        s = deep.score(item, self.t, self.seed)
        self.log.record(item.carrier, s, deep.d_prime)
        if not item.poisoned:
            self.log.benign_touched += 1
        if not deep.fires(s):
            return False
        self.log.fired = True
        if item.poisoned and self.log.first_detect is None:
            self.log.first_detect = self.t
        if self.gate_mode == "observe-upstream":
            return False                                  # alarm only
        if item.poisoned:
            self.log.true_blocks += 1
        else:
            self.log.false_up += 1
            self.log.false_objects += 1
        return True

    def retrieval(self, items):
        if "retrieval" not in self.stages:
            return list(items)
        return [it for it in items if not self._inspect(it, "retrieval")]

    def admit(self, item, stage) -> bool:
        if stage not in ("insertion", "delegation") or stage not in self.stages:
            return True
        return not self._inspect(item, stage)


@dataclass
class StagedResult:
    harm: float
    solved_sigma: bool
    detected_at: int | None
    iota: int | None
    H: int
    spent: float
    n_solved: int
    t_lost: int
    q_false: int                 # D15: false upstream rejections + clean-carrier quarantines
    true_blocks: int
    true_quarantine: int
    false_quarantine: int
    false_objects: int
    benign_touched: int


class NoAudit:
    def __init__(self, budget: float = 0.0):
        self.budget, self.spent = budget, 0.0

    def plan(self, t):
        return []

    def can(self, cost):
        return self.spent + cost <= self.budget * (1 + 1e-9)

    def affordable(self, t, cost):
        return self.can(cost)

    def charge(self, cost):
        self.spent += cost

    def escalate(self, t, log):
        return None

    def observe(self, t, signals):
        pass

    def quarantine(self, t):
        return None


def run_staged(wf, attack, pol, world, seed, kappa, *, action_mode="single",
               gate_mode="block", q_price=0.0, do_inject=True) -> StagedResult:
    ps, channel = attack if attack is not None else (None, None)
    # D19: every draw inside the episode is keyed on (workflow, seed).  The agent seeds
    # on (seed, t) only, so passing the bare seed would give task t of EVERY workflow the
    # same adopt / skill / solve outcome -- the v1 bug (#20) that moved gain from -56% to
    # +44% across seeds, invisibly to a cluster bootstrap.  Still paired across policies:
    # every policy on (wf, seed) sees the same rs.
    rs = seed_of(wf.wf_id, seed)
    ag, det = world(rs)
    store = CarrierStore()
    orc = oracle.default_oracle()
    detected_at = None
    marker_final = solved_final = False
    t_lost = n_solved = tb = q_false = tq = fq = false_obj = touched = 0
    wf_topics = [x.topic for x in wf.tasks]

    for t, task in enumerate(wf.tasks):
        slots = D.n_slots(action_mode, wf.wf_id, t, seed)
        stages: dict = {}
        for stage, depth in pol.plan(t):
            if len(stages) >= slots:
                break
            cost = kappa[stage] * depth
            if stage not in stages and pol.affordable(t, cost):
                pol.charge(cost)
                stages[stage] = depth
        log = AuditLog()
        gates = Gates(stages, det, t, rs, log, gate_mode)

        if do_inject and ps is not None and t == ps.iota:
            payload = build.inject(CarrierStore(), wf, ps)
            if channel == "ingress" or gates.admit(payload, "insertion"):
                store.write(payload)

        o = ag.run_task(t, task, store, seed=rs, marker=ps.marker if ps else "x",
                        gates=gates, wf_topics=wf_topics)
        n_solved += int(o.solved)

        if "commit" not in stages and len(stages) < slots:
            d = pol.escalate(t, log)
            if d and pol.affordable(t, kappa["commit"] * d):
                pol.charge(kappa["commit"] * d)
                stages["commit"] = d
        if "commit" in stages:
            deep = det.at_depth(stages["commit"])
            s = deep.score_patch(o.patch_has_marker, task.task_id, rs, via=o.patch_via)
            log.patch_scores.append(s)       # D17: NOT carrier evidence -- a marked patch does
                                             # not say which carrier fired
            if not o.patch_has_marker:
                log.benign_touched += 1
            if deep.fires(s):
                log.fired = True
                if o.patch_has_marker:
                    log.true_blocks += 1
                    if log.first_detect is None:
                        log.first_detect = t
                    o.patch_has_marker = False
                    for w in o.writes:
                        if w.carrier == "branch":
                            store.quarantine(w.item_id)       # never merged
                elif o.solved:
                    t_lost += 1
                    log.false_commit += 1
                    log.false_objects += 1

        if detected_at is None and log.first_detect is not None:
            detected_at = log.first_detect
        pol.observe(t, log.posterior())

        qc = pol.quarantine(t)
        if qc is not None and (q_price <= 0 or pol.can(q_price)):
            if q_price > 0:
                pol.charge(q_price)
            live = store.live(qc)
            if any(it.poisoned for it in live):
                tq += 1
                detected_at = t if detected_at is None else detected_at
            else:
                fq += 1
            n_benign = sum(1 for it in live if not it.poisoned)
            log.false_objects += n_benign
            log.benign_touched += n_benign
            for it in live:
                store.quarantine(it.item_id)

        tb += log.true_blocks
        q_false += log.false_up
        false_obj += log.false_objects
        touched += log.benign_touched
        if ps is not None and t == ps.sigma:
            marker_final, solved_final = o.patch_has_marker, o.solved

    q_false += fq
    hidden_passed = hidden_ok_of(orc, patch_has_marker=marker_final, patch="")
    return StagedResult(harm=oracle.harm_of(solved_final, hidden_passed),
                        solved_sigma=solved_final, detected_at=detected_at,
                        iota=ps.iota if ps else None, H=len(wf.tasks), spent=pol.spent,
                        n_solved=n_solved, t_lost=t_lost, q_false=q_false, true_blocks=tb,
                        true_quarantine=tq, false_quarantine=fq, false_objects=false_obj,
                        benign_touched=touched)


_SURV: dict = {}


def survives_staged(wf, ps, world, seed, kappa) -> bool:
    """N4 in v2: clean run, no audit, no injection -- shared by every policy.

    The key leaves out the world on purpose: `solved` at sigma is drawn from
    seed_of(rs, t, "solve") with rs = seed_of(wf_id, seed) alone, so no kernel, detector
    or drift setting can move it.
    If that ever changes, the world's parameters must join the key.
    """
    key = (wf.wf_id, ps.carrier, ps.iota, ps.sigma, seed)
    if key not in _SURV:
        r = run_staged(wf, (ps, "write"), NoAudit(), world, seed, kappa, do_inject=False)
        _SURV[key] = r.solved_sigma
    return _SURV[key]
