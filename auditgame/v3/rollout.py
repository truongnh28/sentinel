"""v3/rollout.py -- the rollout engine of line 5 (T12; Q13, O12, O13).

Algorithm 1 line 5 needs L(pi, pi_A | b_t, B_t): the loss of following library member pi
from task t on, against attacker class pi_A, when the hidden state is distributed as b_t.
The engine estimates it by Monte Carlo: R draws per (member, class), 28 x 6 x R rollouts
per task.  RolloutSource (v3/line5.py) uses it in the headline cells (Q13); the line-5
table (T14) is built with it on dev.

ONE ROLLOUT = (member pi, class pi_A, draw r) FROM THE EPISODE STATE AT THE START OF TASK t
    1. OBSERVED STORE.  runner.resume(state) gives a copy of the episode; every item's
       `poisoned` label is set to False, the true placement and the sealed oracle are
       dropped.  Nothing evaluator-only survives (tested: an attacked snapshot and the same
       snapshot with its truth erased give the same L-hat).  Kept, and declared (L1): the
       agent's drift / ingress id sets of past tasks (world side, benign); under the
       primary transient drift a past drift item no longer changes any score.
    2. PARTICLE.  Draw r is the r-th of belief.sample(R, seed) (api.Hypothesis: attacked,
       c, iota, sigma), one sample per task, SHARED by every (member, class): common random
       numbers.
    3. PLANT (`plant`), past from the particle, future from the class:
         not attacked, or iota / sigma outside the horizon   no poison, no attack.
         iota >= t (not yet written)   the class plays the rest: its carrier(s), channel and
                 eps, and its iota rule (first / mid / last) over the feasible sleeper
                 placements at Delta = sigma - iota with iota' >= t (payload.
                 plan_sleeper_all).  None feasible: the particle's own (iota, sigma) with
                 the class's carrier, channel and eps.  The runner injects it at iota'.
         iota < t (already written)    poison per c: the root payload (the class's carrier
                 if c says it is poisoned, else the first poisoned carrier in CARRIERS
                 order) at (iota, sigma) with the class's eps and channel; every other
                 carrier with c[k] = 1 gets its poison on its latest live item written at
                 or after iota (the branch: the patch of sigma when sigma < t), relabelled
                 poisoned and derived from the root -- or, if it has none, a planted item.
                 A root carrier with c = 0 under poisoned copies is written and removed
                 (the trail survives, the note does not).  Every choice reads observable
                 store metadata (carrier, created_at, provenance), never a label.
       The oracle is rebuilt at the particle's sigma and replayed through tasks < t.
    4. CONTINUE.  The member acts; line 7 updates a COPY of b_t (the member's own view);
       lines 8-9 (v3/line8.py, the tuned tau and eta_Q) quarantine on that copy; the runner
       plays the world under the nominal kernel.  Every world draw is re-keyed on
       core.seed_of("v3-rollout", wf, seed, t, r), so a rollout never replays the real
       episode's future draws, and every (member, class) of draw r sees the same world.
    5. LOSS TO GO.  Definition 1 from t on: harm + lambda_Q (FQ - FQ_t) + lambda_T (clean
       lost - clean lost_t), v2's lambdas (runner.LAMBDA_Q, LAMBDA_T).

O13: N_A = 1 (one rollout per particle shared by all classes) is NOT used: each class has
its own rollouts, so "max over pi_A" keeps its meaning (config.N_A_SHARED_ROLLOUT).

O12: L-hat carries its Monte Carlo SE (sample sd / sqrt(R)) and n = R; the headline
rollout prints SE and does not gate on it (config.ROLLOUT_SE_IS_GATE = False).

`drive(episode, source)` steps an episode and binds the state at the start of every task
to a RolloutSource: the runner is not changed.

Stdlib only (the particle filter's numpy stays inside the belief).
"""
from __future__ import annotations

import copy
import math
import random
import time
from dataclasses import dataclass, replace

from core import CARRIERS, Item, seed_of

import build
import retrieval
from v3 import api as A
from v3 import attackers as AT
from v3 import config as C
from v3 import library as L
from v3 import oracle as OR
from v3 import payload as P
from v3 import runner as RU

#: core.seed_of tags (declared once).
WORLD_TAG = "v3-rollout"                  # the world's draws of rollout r at task t
SAMPLE_TAG = "v3-rollout-sample"          # the particle sample at task t
MEMBER_TAG = "v3-rollout-member"          # the member's own randomisation in rollout r
#: Provenance of a planted copy written when the carrier has no live item to carry it.
PLANT_PROVENANCE = {"memory": "agent/notes", "skill": "agent/skills", "queue": "agent/queue",
                    "branch": OR.PATCH_PROVENANCE}

if C.N_A_SHARED_ROLLOUT:                   # O13: declared off; turning it on is a decision
    raise AssertionError("O13: N_A = 1 is not enabled in v3")


# ---------------------------------------------------------------------------------------
# 1. the observed store
# ---------------------------------------------------------------------------------------


def observed(state: A.EpisodeState) -> RU.Episode:
    """The episode at the start of task state.t with every evaluator-only fact removed:
    labels cleared, no placement, a fresh oracle without sigma, no policy."""
    ep = RU.resume(state)
    for k in CARRIERS:
        for it in ep.store.items[k]:
            it.poisoned = False
            it.derived_from = ()
    ep.placement = None
    ep.policy = None
    ep.oracle = _oracle(ep, None)
    return ep


def _oracle(ep: RU.Episode, sigma, solved_sigma: bool = False) -> OR.SealedOracle:
    """A fresh sealed oracle at `sigma`, replayed through the tasks before ep.t."""
    orc = OR.SealedOracle(ep.world, ep.H, sigma, getattr(ep.oracle, "_orc", None))
    for tau in range(ep.t):
        orc.task_end(tau, ep.store, solved_sigma if tau == sigma else False)
    return orc


# ---------------------------------------------------------------------------------------
# 3. plant a particle and a class
# ---------------------------------------------------------------------------------------


def sleeper(wf, k: str, iota: int, sigma: int, eps: float) -> P.SleeperPayload:
    """The sleeper payload at (k, iota, sigma, eps), built as payload.plan_sleeper_all
    builds it but without its feasibility filter (a particle names (iota, sigma) itself)."""
    repo = getattr(wf, "repo", "?")
    target = wf.tasks[sigma].topic
    pay = retrieval.payload_topic_like(target, eps)
    return P.SleeperPayload(wf_id=wf.wf_id, repo=repo, carrier=k, iota=iota, sigma=sigma,
                            epsilon=eps, marker=build.marker_for(repo, wf.wf_id, k, iota,
                                                                 sigma, sigma - iota),
                            topic=pay, target_topic=target,
                            length_reason=build.payload_length_reason(pay))


def _future_placement(wf, world, attack: AT.AttackV3, hyp: A.Hypothesis, t: int):
    ks = attack.carriers(wf, world)
    delta = hyp.sigma - hyp.iota
    cands = [p for p in P.plan_sleeper_all(wf, ks[0], delta, attack.epsilon) if p.iota >= t]
    if cands:
        first = cands[{"first": 0, "mid": len(cands) // 2,
                       "last": len(cands) - 1}[attack.iota_rule]]
        how = f"class rule {attack.iota_rule} over {len(cands)} feasible iota >= {t}"
    else:
        first = sleeper(wf, ks[0], hyp.iota, hyp.sigma, attack.epsilon)
        how = "no feasible placement with iota >= t: the particle's (iota, sigma)"
    pays = [first] + [sleeper(wf, k, first.iota, first.sigma, attack.epsilon) for k in ks[1:]]
    return AT.Placement(tuple(pays), attack.channel), how


def _latest_live(store, k: str, since: int, exclude=(), at: int | None = None):
    live = [it for it in store.live(k) if it.item_id not in exclude
            and (it.created_at == at if at is not None else it.created_at >= since)]
    if k == "branch":
        patches = [it for it in live if it.provenance == OR.PATCH_PROVENANCE]
        live = patches or live
    return max(live, key=lambda it: it.created_at) if live else None


def plant(ep: RU.Episode, hyp: A.Hypothesis, attack: AT.AttackV3) -> dict:
    """Set the hidden state of `ep` (an `observed` copy at task ep.t) from particle `hyp`
    and attacker class `attack` (module docstring, step 3).  Returns what was done."""
    t, wf, world, store = ep.t, ep.wf, ep.world, ep.store
    if (not hyp.attacked or hyp.iota is None or hyp.sigma is None
            or not 0 <= hyp.iota <= hyp.sigma < ep.H):
        ep.placement, ep.oracle = None, _oracle(ep, None)
        return {"kind": "clean"}
    if hyp.iota >= t:
        pl, how = _future_placement(wf, world, attack, hyp, t)
        ep.placement, ep.oracle = pl, _oracle(ep, pl.sigma)
        return {"kind": "future", "placement": pl.id, "how": how}
    # the poison is already in: plant c
    c = dict(zip(CARRIERS, hyp.c))
    k0 = attack.carriers(wf, world)[0]
    root_k = k0 if c.get(k0) else next((k for k in CARRIERS if c.get(k)), k0)
    pay = sleeper(wf, root_k, hyp.iota, hyp.sigma, attack.epsilon)
    ep.placement = AT.Placement((pay,), attack.channel)
    if not any(c.values()):
        ep.oracle = _oracle(ep, hyp.sigma)
        return {"kind": "past", "placement": ep.placement.id, "planted": ()}
    root = pay.item(wf)
    same = next((it for it in store.items[root_k] if it.item_id == root.item_id), None)
    if c[root_k] and same is not None and same.item_id not in store.quarantined:
        root = same                        # the payload is an item the defender can see
        root.poisoned, root.derived_from = True, ()
    else:
        if same is not None:               # removed by the defender, or c says it is gone:
            root = replace(root, content=f"[rollout plant root] {pay.marker}", item_id="")
        store.write(root)
        if attack.channel == "ingress":
            ep.agent.mark_ingress(root)
        if not c[root_k]:
            store.quarantine(root.item_id)
    planted = [(root_k, root.item_id)]
    sigma_patch = None
    for k in CARRIERS:
        if k == root_k or not c[k]:
            continue
        at = hyp.sigma if (k == "branch" and hyp.sigma < t) else None
        it = _latest_live(store, k, hyp.iota, exclude=(root.item_id,), at=at)
        if it is None:
            ct = at if at is not None else t - 1
            it = store.write(Item(carrier=k, topic=wf.tasks[ct].topic,
                                  content=f"[rollout plant] {k} {pay.marker} {ct}",
                                  created_at=ct, provenance=PLANT_PROVENANCE[k],
                                  poisoned=True, derived_from=(root.item_id,)))
        else:
            it.poisoned, it.derived_from = True, (root.item_id,)
        planted.append((k, it.item_id))
        if k == "branch" and at is not None:
            sigma_patch = it
    solved = bool(sigma_patch is not None and ep.patch_solved.get(sigma_patch.item_id, True))
    ep.oracle = _oracle(ep, hyp.sigma, solved)
    return {"kind": "past", "placement": ep.placement.id, "planted": tuple(planted)}


# ---------------------------------------------------------------------------------------
# 4. the continuation policy: member + line 7 on a copy of b_t + lines 8-9
# ---------------------------------------------------------------------------------------


class RolloutPolicy(A.PolicyBase):
    """A library member as the defender of a rollout.  The member chooses a_t; line 7
    updates its own copy of b_t; lines 8-9 run on that copy (None = no quarantine)."""

    def __init__(self, ctx: A.EpisodeContext, member, belief: A.BeliefAPI, line8=None):
        super().__init__(ctx)
        self.member, self.belief, self.line8 = member, belief, line8
        self.name = f"rollout:{member.name}"

    def act(self, t, B_t):
        return self.member.act(t, B_t)

    def observe(self, t, obs):
        self.belief.update(t, obs)
        self.member.observe(t, obs)

    def quarantine(self, t):
        return None if self.line8 is None else self.line8.quarantine(t, self.belief, self._log)


# ---------------------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RolloutResult:
    loss: float
    harm: float
    fq: int
    clean_lost: int
    plant: dict


class RolloutEngine:
    """L-hat [member x attacker class] by R rollouts per pair from the state at task t.

    band    the Prop. 6.1 band the BT members are built with (library.Band).
    line8   the tuned v3.line8.Line8 of the cell's rho, or None (no quarantine: tests only).
    """

    def __init__(self, band: L.Band, line8=None, *, members=None, classes=None,
                 lambda_Q: float = RU.LAMBDA_Q, lambda_T: float = RU.LAMBDA_T):
        self.band, self.line8 = band, line8
        self.members = tuple(L.MEMBERS if members is None else members)
        self.classes = tuple(AT.attacker_classes() if classes is None else classes)
        unknown = [m for m in self.members if m not in L.LIBRARY]
        if unknown:
            raise ValueError(f"unknown library members {unknown}")
        self.attacks = {c: AT.by_name(c) for c in self.classes}
        self.lambda_Q, self.lambda_T = lambda_Q, lambda_T
        self.n_rollouts = 0
        self.last_timing: dict = {}

    def __deepcopy__(self, memo):
        return self

    def sample(self, state: A.EpisodeState, belief: A.BeliefAPI, R: int) -> list:
        hs = list(belief.sample(R, seed_of(SAMPLE_TAG, state.wf_id, state.seed, state.t)))
        if len(hs) != R:
            raise ValueError(f"belief.sample({R}) returned {len(hs)} hypotheses")
        return hs

    def planted(self, base: RU.Episode, hyp: A.Hypothesis, cls: str) -> tuple:
        ep = copy.deepcopy(base)
        info = plant(ep, hyp, self.attacks[cls])
        return ep, info

    def run(self, planted: RU.Episode, info: dict, member: str, belief: A.BeliefAPI,
            r: int) -> RolloutResult:
        """One rollout from a planted episode (copied here, so it can be reused)."""
        ep = copy.deepcopy(planted)
        t = ep.t
        rctx = replace(ep.ctx, rng_seed=seed_of(MEMBER_TAG, ep.wf.wf_id, ep.seed, t, r))
        b = copy.deepcopy(belief)
        m = L.make_member(member, rctx, belief=b, band=self.band)
        ep.policy = RolloutPolicy(rctx, m, b, self.line8)
        ep.rs = seed_of(WORLD_TAG, ep.wf.wf_id, ep.seed, t, r)
        fq0, lost0 = ep.fq, ep.clean_lost_branch
        while ep.t < ep.H:
            ep.step()
        rec = ep.finish().record
        fq, lost = rec.fq - fq0, rec.t_lost - lost0
        self.n_rollouts += 1
        return RolloutResult(RU.loss(rec.harm, fq, lost, self.lambda_Q, self.lambda_T),
                             rec.harm, fq, lost, info)

    def losses(self, state: A.EpisodeState, belief: A.BeliefAPI, R: int) -> dict:
        """(member, class) -> [loss of draw r for r in 0..R-1]."""
        base = observed(state)
        hyps = self.sample(state, belief, R)
        out = {(m, c): [] for m in self.members for c in self.classes}
        for r, h in enumerate(hyps):
            for c in self.classes:
                pep, info = self.planted(base, h, c)
                for m in self.members:
                    out[(m, c)].append(self.run(pep, info, m, belief, r).loss)
        return out

    def matrix(self, state: A.EpisodeState, belief: A.BeliefAPI, R: int) -> A.LossMatrix:
        t0, n0 = time.perf_counter(), self.n_rollouts
        ls = self.losses(state, belief, R)
        n = self.n_rollouts - n0
        dt = time.perf_counter() - t0
        self.last_timing = {"t": state.t, "H": state.private["episode"].H, "rollouts": n,
                            "seconds": dt, "ms_per_draw": 1000.0 * dt / max(n, 1)}
        Lm, se, nn = [], [], []
        for m in self.members:
            row, srow, nrow = [], [], []
            for c in self.classes:
                v = ls[(m, c)]
                mu = sum(v) / len(v)
                sd = math.sqrt(sum((x - mu) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
                row.append(mu)
                srow.append(sd / math.sqrt(len(v)))
                nrow.append(len(v))
            Lm.append(tuple(row))
            se.append(tuple(srow))
            nn.append(tuple(nrow))
        return A.LossMatrix(self.members, self.classes, tuple(Lm), tuple(se), tuple(nn),
                            "rollout", f"R={R}, t={state.t}")


def drive(ep: RU.Episode, source) -> RU.EpisodeOutput:
    """Run `ep` to the end, binding the state at the start of every task to `source`
    (a line5.RolloutSource) before the policy acts."""
    while ep.t < ep.H:
        source.bind(ep.snapshot())
        ep.step()
    return ep.finish()


# ---------------------------------------------------------------------------------------
# Timing (plan T12 acceptance: time per (member, class, draw), vs P0's 7.4 ms per episode)
# ---------------------------------------------------------------------------------------


class PriorBelief:
    """A FIXED prior over (attacked, iota, sigma = iota + delta) with c = the class-free
    memory bit after iota.  For timing and smoke runs only -- never Sentinel's belief (T9's
    particle filter is); it does not update."""

    def __init__(self, H: int, delta: int, p0: float = 0.5, t: int = 0):
        self.H, self.delta, self.p0 = H, delta, p0
        self.t = t

    def update(self, t, obs):
        self.t = t + 1

    def condition_on_quarantine(self, t, carrier):
        return None

    def p_poisoned(self):
        return self.p0

    def carrier_mass(self):
        return {k: self.p0 / len(CARRIERS) for k in CARRIERS}

    def expected_harm(self):
        return 0.5 * self.p0

    def bin_features(self):
        return A.BinFeatures(self.p0, CARRIERS[0], 0.5 * self.p0)

    def sample(self, n, seed):
        rng, out = random.Random(seed), []
        for _ in range(n):
            if rng.random() >= self.p0 or self.H <= self.delta:
                out.append(A.Hypothesis(False, (0, 0, 0, 0), None, None))
                continue
            iota = rng.randrange(self.H - self.delta)
            c = (1, 0, 0, 0) if iota < self.t else (0, 0, 0, 0)
            out.append(A.Hypothesis(True, c, iota, iota + self.delta))
        return out


def time_draws(n_wf: int = 6, R: int = 2, seed: int = 0) -> dict:
    """ms per (member, class, draw) from mid-episode states of dev workflows in the headline
    cell (rho = 0, Delta = 4), and the P0-comparable figure: rollouts at EVERY task of an
    episode, per (member, class, draw) summed over t."""
    from v3 import baselines as BL
    from v3 import corpus as K
    cell = C.Cell(rho=0.0, delta=4)
    wfs = [w for w in K.dev_workflows() if w.H > cell.delta][:n_wf]
    eng = RolloutEngine(L.band_prop61(0.5, 0.2))
    att = AT.by_name(AT.attacker_classes()[0])
    per_draw, per_episode, Hs = [], [], []
    for wf in wfs:
        pl = att.plan(wf, cell.delta)
        ep = RU.Episode(wf, pl, BL.factory(BL.B1AuditAtCommit.name), C.PRIMARY, cell, seed)
        tot = 0.0
        while ep.t < ep.H:
            st = ep.snapshot()
            eng.matrix(st, PriorBelief(ep.H, cell.delta, t=ep.t), R)
            tot += eng.last_timing["ms_per_draw"]
            if ep.t == ep.H // 2:
                per_draw.append(eng.last_timing["ms_per_draw"])
            ep.step()
        per_episode.append(tot)
        Hs.append(ep.H)
    return {"workflows": len(wfs), "R": R, "mean_H": sum(Hs) / len(Hs),
            "ms_per_draw_mid_episode": sum(per_draw) / len(per_draw),
            "ms_per_tuple_all_tasks": sum(per_episode) / len(per_episode),
            "p0_ms_per_tuple_all_tasks": 7.4}


def _main() -> int:
    r = time_draws()
    print("T12 rollout timing (headline cell rho = 0, Delta = 4, dev, fixed-prior belief):")
    for k, v in r.items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
