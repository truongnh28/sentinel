"""carrier_runner.py -- the PRIMARY world: the draft's SS4 action model (D1, D3, D5, D15-D17).

a_t in {none} U {(k, d): k in SWEEP_CARRIERS} U {("commit", d)}: ONE action per task (SS4).
Inside task t:
  1. the policy names a target and a depth; the runner buys the DEEPEST affordable depth
     <= the requested one on that target (one ladder for every policy), or nothing
  2. injection at iota (both channels land in the store an audit reads: SS4 / Theorem 4)
  3. the agent runs task t (retrieval, adoption, propagation, benign drift) -- no gates
  4. the bought action:
       commit  -- review THIS task's patch (D20 exposure).  A firing patch is blocked: a
                  marked patch loses its marker, a clean solved patch costs one T_lost.
                  The alarm is NOT carrier evidence (D17).
       k       -- score EVERY live item of carrier k at depth d (D16: independent draws);
                  the policy sees the carrier signal it paid for (D5), updates, then decides
                  which FIRING items to quarantine (D3; Algorithm 1 lines 7-8).
Harm is read at sigma (sealed oracle, marker gate).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import build
import draft_setup as D
import oracle
import scoring
from core import CarrierStore, seed_of
from runner import hidden_ok_of


@dataclass
class Observation:
    target: str
    depth: int
    fired: bool
    posterior: float | None      # carrier signal (scoring.carrier_score); None for commit (D17)
    n_items: int


@dataclass
class EpisodeResult:
    harm: float
    solved_sigma: bool
    detected_at: int | None
    iota: int | None
    sigma: int | None
    H: int
    spent: float
    n_solved: int
    t_lost: int
    true_removed: int
    false_removed: int            # D15: benign items quarantined
    benign_inspected: int         # D15: benign objects the defender looked at
    patch_blocks: int             # marked patches blocked at commit
    audits: dict                  # target -> number of tasks it was bought


def rs_of(wf, seed) -> int:
    """D19: every draw inside an episode is keyed on (workflow, seed)."""
    return seed_of(wf.wf_id, seed)


def survives(wf, ps, seed, solve_rate: float = 0.62) -> bool:
    """N4: the task at sigma is solved in the clean run.  `solved` is drawn from
    seed_of(rs, t, "solve") alone (world_v2.StagedMockAgent), so no world parameter can
    move it; tested against a full clean episode (test_survives_matches_a_clean_run)."""
    return random.Random(seed_of(rs_of(wf, seed), ps.sigma, "solve")).random() < solve_rate


def run_carrier(wf, attack, pol, world, seed, kappa, *, do_inject=True) -> EpisodeResult:
    ps, _channel = attack if attack is not None else (None, None)
    rs = rs_of(wf, seed)
    ag, det = world(rs)
    store = CarrierStore()
    orc = oracle.default_oracle()
    wf_topics = [x.topic for x in wf.tasks]
    detected_at = None
    marker_final = solved_final = False
    n_solved = t_lost = true_removed = false_removed = benign_inspected = patch_blocks = 0
    audits = {k: 0 for k in D.TARGETS}

    for t, task in enumerate(wf.tasks):
        bought = None
        want = pol.act(t)
        if want is not None:
            target, depth = want
            for d in range(min(depth, D.MAX_DEPTH), 0, -1):
                cost = kappa[target] * d
                if pol.affordable(t, cost):
                    pol.charge(cost)
                    bought = (target, d)
                    audits[target] += 1
                    break

        if do_inject and ps is not None and t == ps.iota:
            store.write(build.inject(CarrierStore(), wf, ps))

        o = ag.run_task(t, task, store, seed=rs, marker=ps.marker if ps else "x",
                        wf_topics=wf_topics)
        n_solved += int(o.solved)

        if bought is not None and bought[0] == D.COMMIT:
            deep = det.at_depth(bought[1])
            s = deep.score_patch(o.patch_has_marker, task.task_id, rs, via=o.patch_via)
            fired = deep.fires(s)
            if not o.patch_has_marker:
                benign_inspected += 1
            if fired and o.patch_has_marker:
                o.patch_has_marker = False
                patch_blocks += 1
                detected_at = t if detected_at is None else detected_at
                for w in o.writes:
                    if w.carrier == "branch":
                        store.quarantine(w.item_id)          # never merged
            elif fired and o.solved:
                t_lost += 1
            pol.observe(t, Observation(D.COMMIT, bought[1], fired, None, 1))
        elif bought is not None:
            k, d = bought
            deep = det.at_depth(d)
            live = store.live(k)
            scores = [deep.score(it, t, rs) for it in live]
            benign_inspected += sum(1 for it in live if not it.poisoned)
            firing = [(it, s) for it, s in zip(live, scores) if deep.fires(s)]
            post = scoring.carrier_score(scores, deep.d_prime) if scores else None
            pol.observe(t, Observation(k, d, bool(firing), post, len(live)))      # line 7
            for it in pol.remove(t, k, firing, deep, live):                         # line 8
                store.quarantine(it.item_id)
                if it.poisoned:
                    true_removed += 1
                    detected_at = t if detected_at is None else detected_at
                else:
                    false_removed += 1
        else:
            pol.observe(t, None)

        if ps is not None and t == ps.sigma:
            marker_final, solved_final = o.patch_has_marker, o.solved

    hidden_passed = hidden_ok_of(orc, patch_has_marker=marker_final, patch="")
    return EpisodeResult(harm=oracle.harm_of(solved_final, hidden_passed),
                         solved_sigma=solved_final, detected_at=detected_at,
                         iota=ps.iota if ps else None, sigma=ps.sigma if ps else None,
                         H=len(wf.tasks), spent=pol.spent, n_solved=n_solved, t_lost=t_lost,
                         true_removed=true_removed, false_removed=false_removed,
                         benign_inspected=benign_inspected, patch_blocks=patch_blocks,
                         audits=audits)
