"""v3/stage_world.py -- the stage-gate world (C2) and the one-factor sensitivity worlds (T20).

Draft S8: "with 4 audit stages (insertion, retrieval, delegation, commit) and 4 carriers
(memory, cached skill, tool queue, branch)."  Draft S4 has the action as (audit, k, depth)
with k a carrier.  C2 reads k both ways and runs both: the carrier sweep of v3/runner.py is
primary; this module is the other reading, reusing v2's D29 gate world
(gate_world._Gates, STAGE_KAPPA, GATE_BASELINES) on the v3 agent, observation model and
sealed oracle.  It also holds what T20 needs to run the six sensitivities of
config.sensitivities() one factor at a time (Q2), H8's verdict world and O15's table world.

THE STAGE WORLD (world.audit_reading = "stage")
    action     AuditAction(stage, depth), stage in STAGES.  Cost kappa(stage, depth) = the
               stage's unit price x depth; the unit prices are STAGE_KAPPA of v2 (the draft's
               0.4 / 0.9 / 1.6 / 4.1, S7) and equal config.KAPPA_UNIT through STAGE_OF_TARGET.
               The cell fixes each stage's depth as it fixes its target's (C16), so
               ctx.depths / ctx.kappa are keyed by STAGE here.
    a gate     the bought stage inspects the OBJECTS IN FLIGHT at task t across every carrier
               (v2 D29), and a firing object is rejected:
                 insertion   every write labelled "insertion" (the agent's notes, every
                             drift event) and the attacker's write at iota.  H8: with
                             world.ingress_visible = False it does not see ingress writes
                             (drift, the payload on the ingress channel), as the carrier
                             world's memory sweep does not.
                 retrieval   every item the agent retrieves at t; a firing one is dropped
                             from THIS task's context (it stays in the store).
                 delegation  every skill / queued call the agent writes at t.
                 commit      the patch of task t (observe.ObservationModel.commit: D20 rho
                             for a delegated patch, A7 provenance when world.provenance =
                             "A7"); a firing patch is removed from the branch before it lands.
               Scores are the carrier world's (world_v2.DriftDetector: seed_of(seed,
               "v2-score", item, t), depth d' sqrt(d); the patch's seed_of(seed, "v2-patch",
               task_id)), so the two worlds share every draw (common random numbers).
    o_t        the scores of every inspected object, their written_at, alarm = any firing,
               the checkpoint (O8), A7's provenance on a commit gate.
    lines 8-9  unchanged: the policy may still quarantine a whole carrier (O7).
    accounting (L1, declared here) -- the stage reading's "quarantine" is the gate's
               rejection (v2 GateResult.false_blocks / true_blocks):
                 fq                 + one per BENIGN object a gate rejects, + the policy's
                                    carrier quarantines with c_t[k] = 0 (as the runner);
                 true_q             + one per POISONED object a gate rejects, + the policy's
                                    quarantines of a poisoned carrier;
                 clean_lost_branch  + one per clean, solved patch the commit gate rejects
                                    (v2 gate world's t_lost), + the runner's branch rule;
                 detected_at        the first task a gate rejected, or a quarantine removed,
                                    a poisoned object.
    harm       the same sealed oracle (C11 either way): it reads the branch, so a patch the
               commit gate rejected is not there.
    trace      StageEpisode.inspected (evaluator-only): (t, stage, item id) of every object
               a gate inspected; blocks: per-stage true / false rejections.

CARRIER-WORLD POLICIES IN THE STAGE WORLD (`carrier_policy`).  Every v3 system chooses a
target of config.TARGETS; the adapter maps it to the stage that audits the same carrier
under D2 (memory -> insertion, queue -> retrieval, skill -> delegation, commit -> commit),
keeps the cell's depth, and maps o_t back.  So B1 is v2's "B1g commit", B2 "B2g uniform",
B3 "B3g insertion", B4 "B4g retrieval".  Lines 8-9: a baseline's rule "quarantine the
audited carrier on an alarm" IS the gate's rejection in the stage reading (v2's gate
baselines never quarantine), so by default the adapter does not pass it on
(keep_quarantine=False); a policy with its own lines 8-9 (Sentinel, T15) passes
keep_quarantine=True.

SENSITIVITIES (Q2).  `run_in_world` runs one episode in any world of config: the runner for
audit_reading = "carrier", StageEpisode for "stage"; the placement is planned in that world
(the attacker seeds world.n_seeded carriers).  `components(ep)` reads, off a built episode,
the value each module ACTUALLY uses for each switch, so a test can check that a sensitivity
run differs from the primary run in exactly one of them.

H8 (sentinel-v3.md): the verdict is taken from the world whose insertion audit sees ingress
(the primary); in the ingress-hidden world H8 holds by construction and is only printed
(`h8_role`).  O15: every sensitivity (and K_d != 2) uses the primary world's line-5 table,
declared as "Sentinel's model is misspecified in one factor" (`table_world`,
`misspecification`).

DEV ONLY: episodes go through runner.check_split (the seal, plan S6).
Stdlib only; imports v2 (gate_world, core, carrier_runner) and v3, never patches them.
"""
from __future__ import annotations

from dataclasses import replace

import gate_world as GW
from carrier_runner import rs_of
from core import CarrierStore
from world_v2 import DriftDetector

from v3 import agent as AG
from v3 import api as A
from v3 import budget as BU
from v3 import config as C
from v3 import observe as O
from v3 import oracle as OR
from v3 import runner as R
from v3 import state as S

# ---------------------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------------------

#: Draft S8's four audit stages, in the order of config.TARGETS' prices.
STAGES = tuple(GW.STAGE_KAPPA)                     # insertion, retrieval, delegation, commit
#: v2's D2: the stage that audits the same carrier as each carrier-world target.
STAGE_OF_TARGET = {"memory": "insertion", "queue": "retrieval", "skill": "delegation",
                   "commit": "commit"}
TARGET_OF_STAGE = {s: t for t, s in STAGE_OF_TARGET.items()}
#: Per-look price of each stage (v2 gate_world.STAGE_KAPPA, the draft's S7 prices).
STAGE_UNIT = dict(GW.STAGE_KAPPA)
#: v2's D29 gate baselines, named by the v3 baseline they are under the adapter.
GATE_BASELINE_OF = {"B1 audit-at-commit": "B1g commit", "B2 uniform random": "B2g uniform",
                    "B3 audit-on-insertion": "B3g insertion",
                    "B4 audit-on-retrieval": "B4g retrieval"}
#: The labels the agent puts on its writes (v3/agent.py `put`) that each gate inspects.
_ADMIT_STAGES = ("insertion", "delegation")


def stage_depths(cell: C.Cell) -> dict:
    """stage -> the cell's depth for the carrier target it corresponds to (C16)."""
    dep = cell.depths()
    return {s: dep[TARGET_OF_STAGE[s]] for s in STAGES}


def stage_kappa(cell: C.Cell) -> dict:
    """stage -> price at the cell's depth (budget.cell_kappa, re-keyed)."""
    kap = BU.cell_kappa(cell)
    return {s: kap[TARGET_OF_STAGE[s]] for s in STAGES}


def stage_context(ctx: A.EpisodeContext) -> A.EpisodeContext:
    """The committed setup in the stage world: depths and prices keyed by stage."""
    return replace(ctx, depths=stage_depths(ctx.cell), kappa=stage_kappa(ctx.cell))


def target_context(ctx: A.EpisodeContext) -> A.EpisodeContext:
    """The same setup keyed by carrier target, for a carrier-world policy (the adapter)."""
    return replace(ctx, depths=ctx.cell.depths(), kappa=BU.cell_kappa(ctx.cell))


# ---------------------------------------------------------------------------------------
# The gate of one task
# ---------------------------------------------------------------------------------------

class StageGates(GW._Gates):
    """gate_world._Gates on the v3 detector, recording every inspected object (for o_t)
    and skipping ingress writes at insertion when the world hides them (H8)."""

    def __init__(self, stage, depth, det, t, seed, *, ingress_ids=frozenset(),
                 ingress_visible=True):
        super().__init__(stage, depth, det, t, seed)
        self.ingress_ids, self.ingress_visible = ingress_ids, ingress_visible
        self.seen: list = []                    # (item, score, fired), inspection order
        self.rejected: list = []                # the rejected items

    def _reject(self, item) -> bool:
        deep = self.det.at_depth(self.depth)
        s = deep.score(item, self.t, self.seed)
        fired = deep.fires(s)
        self.seen.append((item, s, fired))
        if not fired:
            return False
        self.rejected.append(item)
        if item.poisoned:
            self.true_blocks += 1
        else:
            self.false_blocks += 1
        return True

    def admit(self, item, stage) -> bool:
        if (stage == "insertion" and not self.ingress_visible
                and item.item_id in self.ingress_ids):
            return True                          # H8: the insertion audit does not see it
        return super().admit(item, stage)


class _Closed:
    """No gate bought: every object passes (world_v2.OpenGates, with the same fields)."""
    stage = None
    seen: tuple = ()
    rejected: tuple = ()

    def retrieval(self, items):
        return list(items)

    def admit(self, item, stage) -> bool:
        return True


# ---------------------------------------------------------------------------------------
# The stage-world episode
# ---------------------------------------------------------------------------------------

class StageEpisode(R.Episode):
    """One episode of the stage world.  Same constructor, record, post-mortem, oracle,
    snapshot / resume as runner.Episode; only the audit (a gate in flight) differs."""

    def __init__(self, wf, placement, policy_factory: A.PolicyFactory,
                 world: C.WorldV3 | None = None, cell: C.Cell | None = None, seed: int = 0, *,
                 split: str = R.DEV, token=None, order: int = 0, attack: str = "none",
                 best_response: bool = False, postmortems=(), budget: float | None = None,
                 agent_factory=None, observer=None, oracle=None):
        world = replace(C.PRIMARY, audit_reading="stage") if world is None else world
        if cell is None:
            raise ValueError("an episode runs in one cell")
        R.check_split(split, token)
        C.check_world_cell(world, cell)
        if world.audit_reading != "stage":
            raise ValueError("StageEpisode runs audit_reading='stage' only; the carrier "
                             "world is runner.Episode")
        if placement is not None:
            if placement.wf_id != wf.wf_id:
                raise ValueError(f"placement on {placement.wf_id!r}, workflow {wf.wf_id!r}")
            if len(placement.k) > world.n_seeded:
                raise ValueError(f"{len(placement.k)} seeded carriers in a world that seeds "
                                 f"{world.n_seeded}")
            if isinstance(cell.delta, int) and placement.delta != cell.delta:
                raise ValueError(f"placement Delta = {placement.delta} in a cell with Delta = "
                                 f"{cell.delta} (C10: the environment fixes Delta)")
        self.wf, self.placement, self.world, self.cell = wf, placement, world, cell
        self.seed, self.split, self.order, self.attack = seed, split, order, attack
        self.best_response = best_response
        self.H = len(wf.tasks)
        self.rs = rs_of(wf, seed)
        self.topics = [x.topic for x in wf.tasks]
        self.ctx = stage_context(R.context(wf, world, cell, seed, budget=budget,
                                           postmortems=postmortems))
        self.budget = self.ctx.budget
        self.unit = {s: self.ctx.kappa[s] / self.ctx.depths[s] for s in STAGES}
        self.policy = policy_factory(self.ctx)
        self.agent = (AG.SleeperMockAgent.for_cell(world, cell) if agent_factory is None
                      else agent_factory(world, cell))
        self._observer = O.ObservationModel if observer is None else observer
        self.obs = self._new_observer()
        self.oracle = OR.SealedOracle(world, self.H, None if placement is None
                                      else placement.sigma, oracle)
        self.store = CarrierStore()
        self.t = 0
        self.spent = 0.0
        self.n_solved = self.fq = self.true_q = self.false_removed = 0
        self.benign_inspected = self.clean_lost_branch = 0
        self.detected_at: int | None = None
        self.audits = {s: [] for s in STAGES}
        self.c_traj: list = []
        self.quarantines: list = []
        self.alarms: list = []
        self.patch_solved: dict = {}
        self.blocks = {s: {"true": 0, "false": 0} for s in STAGES}
        #: evaluator-only trace: (t, stage, item id) of every object a gate inspected
        self.inspected: list = []
        self._done = None

    # ---- the detector the gates score with (the carrier sweep's, D16 / D6) ----------------
    def _detector(self) -> DriftDetector:
        return DriftDetector(self.obs.detector, self.agent.drift_ids, match=O.DRIFT_MATCH,
                             rho_patch=self.cell.rho, d1=self.obs.dprime,
                             drift_visible=O.DRIFT_VISIBLE[self.world.drift])

    def cost(self, action: A.AuditAction) -> float:
        if action.target not in STAGES:
            raise ValueError(f"audit stage {action.target!r} is not one of {STAGES} (the "
                             f"stage world's k is a stage, C2; wrap a carrier-world policy "
                             f"with stage_world.carrier_policy)")
        d, cell_d = action.depth, self.ctx.depths[action.target]
        if isinstance(d, bool) or not isinstance(d, int) or not 1 <= d <= cell_d:
            raise ValueError(f"depth {d!r} on {action.target}: the cell fixes depth {cell_d} "
                             f"(C16); a declared rule may lower it, never raise it")
        return self.unit[action.target] * d

    def _count(self, t: int, stage: str, item) -> None:
        if item.poisoned:
            self.true_q += 1
            self.blocks[stage]["true"] += 1
            if self.detected_at is None:
                self.detected_at = t
        else:
            self.fq += 1
            self.false_removed += 1
            self.blocks[stage]["false"] += 1

    def step(self) -> None:
        if self.t >= self.H:
            raise RuntimeError("the episode is over")
        t, task, pol = self.t, self.wf.tasks[self.t], self.policy
        # 1-2. act, buy
        requested = pol.act(t, self.remaining)
        bought = None
        if requested is not None:
            c = self.cost(requested)
            if self.spent + c <= self.budget + R._EPS:
                self.spent += c
                bought = requested
                self.audits[requested.target].append(t)
        gates = _Closed() if bought is None or bought.target == "commit" else StageGates(
            bought.target, bought.depth, self._detector(), t, self.rs,
            ingress_ids=self.agent.ingress_ids, ingress_visible=self.world.ingress_visible)
        # 3. inject at iota, through the insertion gate
        pl = self.placement
        if pl is not None and t == pl.iota:
            for sp in pl.payloads:
                item = sp.item(self.wf)
                if pl.ingress:
                    self.agent.mark_ingress(item)
                if gates.admit(item, "insertion"):
                    self.store.write(item)
        # 4. the agent, through the retrieval / delegation / insertion gates
        o = self.agent.run_task(t, task, self.store, seed=self.rs,
                                marker=pl.payloads[0].marker if pl is not None else "x",
                                gates=gates, wf_topics=self.topics)
        self.n_solved += int(o.solved)
        patch = None
        for w in o.writes:
            if w.carrier == OR.BRANCH and w.provenance == OR.PATCH_PROVENANCE:
                self.patch_solved[w.item_id] = bool(o.solved)
                patch = w
        for item in gates.rejected:
            self._count(t, gates.stage, item)
        self.inspected.extend((t, gates.stage, it.item_id) for it, _, _ in gates.seen)
        # 5. the commit gate: the patch before it lands
        checkpoint = self.obs.checkpoint(o.solved)
        if bought is not None and bought.target == "commit":
            ins = self.obs.commit(t, bought.depth, has_marker=o.patch_has_marker,
                                  via=o.patch_via, task_id=task.task_id, seed=self.rs)
            self.benign_inspected += int(not ins.marker)
            if patch is not None:
                self.inspected.append((t, "commit", patch.item_id))
            obs = ins.observation(t, requested, checkpoint)
            if ins.alarm and patch is not None:
                self.store.quarantine(patch.item_id)
                self._count(t, "commit", patch)
                if not patch.poisoned and o.solved:
                    self.clean_lost_branch += 1
        elif bought is not None:
            seen = gates.seen
            self.benign_inspected += sum(1 for it, _, _ in seen if not it.poisoned)
            obs = A.Observation(t=t, requested=requested, bought=bought,
                                scores=tuple(s for _, s, _ in seen),
                                alarm=any(f for _, _, f in seen),
                                written_at=tuple(it.created_at for it, _, _ in seen),
                                checkpoint=checkpoint)
        else:
            obs = self.obs.nothing(t, requested, checkpoint)
        if obs.alarm:
            self.alarms.append((t, bought.target))
        pol.observe(t, obs)
        # 7. lines 8-9: the whole carrier (runner's O7 accounting)
        k = pol.quarantine(t)
        if k is not None:
            self.quarantine(t, k)
        # 8. lock harm at sigma (C11)
        self.oracle.task_end(t, self.store, o.solved)
        self.c_traj.append(S.bits(S.c_of(self.store)))
        self.t += 1

    def counters(self) -> dict:
        out = super().counters()
        out["blocks"] = {s: dict(v) for s, v in self.blocks.items()}
        return out


# ---------------------------------------------------------------------------------------
# Carrier-world policies in the stage world
# ---------------------------------------------------------------------------------------

def _to_stage(a: A.AuditAction | None) -> A.AuditAction | None:
    if a is None:
        return None
    if a.target not in STAGE_OF_TARGET:
        raise ValueError(f"target {a.target!r} is not a carrier-world target {C.TARGETS}")
    return A.AuditAction(STAGE_OF_TARGET[a.target], a.depth)


def _to_target(a: A.AuditAction | None) -> A.AuditAction | None:
    return None if a is None else A.AuditAction(TARGET_OF_STAGE[a.target], a.depth)


class CarrierPolicyInStages:
    """A carrier-world api.PolicyV3 run in the stage world (module docstring)."""

    def __init__(self, inner: A.PolicyV3, keep_quarantine: bool):
        self.inner, self.keep_quarantine = inner, keep_quarantine
        self.name = inner.name
        self._dropped: list = []

    def act(self, t: int, B_t: float) -> A.AuditAction | None:
        return _to_stage(self.inner.act(t, B_t))

    def observe(self, t: int, obs: A.Observation) -> None:
        self.inner.observe(t, replace(obs, requested=_to_target(obs.requested),
                                      bought=_to_target(obs.bought)))

    def quarantine(self, t: int) -> str | None:
        k = self.inner.quarantine(t)
        if k is not None and not self.keep_quarantine:
            self._dropped.append([t, k])
            return None
        return k

    def decision_log(self) -> list:
        return list(self.inner.decision_log()) + [{"stage_adapter": True,
                                                   "keep_quarantine": self.keep_quarantine,
                                                   "quarantines_dropped": self._dropped}]


def carrier_policy(factory: A.PolicyFactory, *, keep_quarantine: bool = False
                   ) -> A.PolicyFactory:
    """A stage-world factory from a carrier-world one: the inner policy is built with
    target-keyed depths and prices, its targets are mapped to D2 stages."""
    def make(ctx: A.EpisodeContext) -> A.PolicyV3:
        return CarrierPolicyInStages(factory(target_context(ctx)), keep_quarantine)
    return make


# ---------------------------------------------------------------------------------------
# One episode in any world (the sensitivities, Q2)
# ---------------------------------------------------------------------------------------



def episode_in_world(wf, placement, factory: A.PolicyFactory, world: C.WorldV3,
                     cell: C.Cell, seed: int, *, keep_quarantine: bool = False, **kw):
    """The Episode of `world`: runner.Episode (carrier reading) or StageEpisode (stage
    reading, `factory` a carrier-world factory wrapped by carrier_policy)."""
    if world.audit_reading == "stage":
        return StageEpisode(wf, placement, carrier_policy(factory,
                                                          keep_quarantine=keep_quarantine),
                            world, cell, seed, **kw)
    return R.Episode(wf, placement, factory, world, cell, seed, **kw)


def run_in_world(wf, placement, factory: A.PolicyFactory, world: C.WorldV3, cell: C.Cell,
                 seed: int, **kw) -> R.EpisodeOutput:
    return episode_in_world(wf, placement, factory, world, cell, seed, **kw).run()


def plan_in_world(attack, wf, cell: C.Cell, world: C.WorldV3, reasons=None):
    """The attacker's placement in `world`: world.n_seeded carriers (v3/attackers.py)."""
    return attack.plan_in_cell(wf, cell, world, reasons=reasons)


def components(ep) -> dict:
    """The value each module ACTUALLY uses for each WorldV3 switch in a built episode:
    observe (provenance), the episode class (audit reading), the oracle (harm), agent and
    observer (ingress, drift), the placement (carriers seeded), the agent's kernel, and the
    line-5 source (the world's; no Sentinel in the baselines' runs)."""
    ag, ob = ep.agent, ep.obs
    if ag.ingress_visible != ob.world.ingress_visible:
        raise AssertionError("agent and observer disagree on ingress visibility")
    if AG.DRIFT_VISIBLE[ag.drift] != O.DRIFT_VISIBLE[ob.world.drift]:
        raise AssertionError("agent and observer disagree on drift persistence")
    kernel = [k for k, (adopt, skill) in AG.KERNELS.items()
              if (adopt, skill) == (ag.adoption_rate, ag.skill_induction_rate)]
    return {
        "provenance": "A7" if ob.dprime_provenance is not None else "A0",
        "audit_reading": "stage" if isinstance(ep, StageEpisode) else "carrier",
        "harm": ep.oracle.mode,
        "ingress_visible": ag.ingress_visible,
        "drift": ag.drift,
        "n_seeded": 0 if ep.placement is None else len(ep.placement.k),
        "kernel": kernel[0] if kernel else "custom",
        "line5": ep.world.line5,
    }


# ---------------------------------------------------------------------------------------
# H8 and O15
# ---------------------------------------------------------------------------------------

H8_VERDICT = "verdict"
H8_PRINTED = "printed: holds by construction (the insertion audit cannot see ingress)"


def h8_verdict_world() -> C.WorldV3:
    """sentinel-v3.md S9: H8's verdict is taken from the world whose insertion audit sees
    ingress -- the primary configuration."""
    return C.PRIMARY


def h8_role(world: C.WorldV3) -> str | None:
    """What H8 reads off `world`: the verdict (primary), a print-only line (the
    ingress-hidden sensitivity), or nothing (every other world)."""
    if world == h8_verdict_world():
        return H8_VERDICT
    if world == dict(C.sensitivities())["ingress-hidden"]:
        return H8_PRINTED
    return None


def table_world(world: C.WorldV3) -> C.WorldV3:
    """O15: the line-5 table used in `world` is the primary world's, whatever the world."""
    if C.TABLE_WORLD != "primary":
        raise AssertionError(f"config.TABLE_WORLD = {C.TABLE_WORLD!r}")
    return C.PRIMARY


def misspecification(world: C.WorldV3, cell: C.Cell | None = None) -> dict:
    """O15's declaration for a run of Sentinel in (world, cell): which table it reads and
    in which factor Sentinel's model differs from the world."""
    tw = table_world(world)
    diff = [f for f in C.world_fields() if getattr(world, f) != getattr(tw, f)]
    if cell is not None and cell.k_delegated != C.K_D_PRIMARY:
        diff.append("k_delegated")
    out = {"table_world": C.world_name(tw), "table_world_id": C.world_id(tw),
           "world": C.world_name(world), "differs_in": diff,
           "label": ("Sentinel's model is misspecified in one factor: " + diff[0]
                     if len(diff) == 1 else "" if not diff else
                     "Sentinel's model differs in " + ", ".join(diff))}
    if cell is not None:
        out["table_key"] = C.table_key_id(cell)
    return out


# ---------------------------------------------------------------------------------------
# Smoke on dev (plan T20: "smoke 6 do nhay tren dev")
# ---------------------------------------------------------------------------------------

SMOKE_SYSTEMS = ("B1 audit-at-commit", "B2 uniform random", "B3 audit-on-insertion",
                 "B4 audit-on-retrieval", "B5 risk-score", "B6 two-stage", "cost-greedy")


def smoke(n_workflows: int = 12, seeds=(0, 1, 2), cell: C.Cell | None = None,
          systems=SMOKE_SYSTEMS) -> list:
    """Mean harm / FQ / clean lost / L per (world, system) on the first dev workflows,
    against the held-out scripted attackers planned in each world.  DEV ONLY."""
    from v3 import attackers as AT
    from v3 import baselines as B
    from v3 import corpus as K
    cell = C.Cell(rho=0.25, delta=4) if cell is None else cell
    wfs = K.dev_workflows()[:n_workflows]
    worlds = [("primary", C.PRIMARY)] + list(C.sensitivities())
    rows = []
    for wname, world in worlds:
        plans = [(wf, a, plan_in_world(AT.by_name(a), wf, cell, world))
                 for wf in wfs for a in AT.held_out()]
        plans = [p for p in plans if p[2] is not None]          # N3
        for sname in systems:
            recs = [run_in_world(wf, pl, B.factory(sname), world, cell, s, attack=a).record
                    for wf, a, pl in plans for s in seeds]
            n = len(recs)
            rows.append({"world": wname, "system": sname, "n": n,
                         "harm": sum(r.harm for r in recs) / n,
                         "fq": sum(r.fq for r in recs) / n,
                         "t_lost": sum(r.t_lost for r in recs) / n,
                         "L": sum(R.loss_of(r) for r in recs) / n})
    return rows


def _main() -> int:
    rows = smoke()
    print("T20 smoke (dev, first 12 workflows x 7 held-out attackers x 3 seeds; "
          "cell rho = 0.25, Delta = 4, chi 1.33, d' 2.21, b1)")
    print(f"{'world':18} {'system':24} {'n':>5} {'harm':>6} {'FQ':>6} {'lost':>6} {'L':>6}")
    for r in rows:
        print(f"{r['world']:18} {r['system']:24} {r['n']:>5} {r['harm']:6.3f} {r['fq']:6.2f} "
              f"{r['t_lost']:6.2f} {r['L']:6.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
