"""Dedicated unit tests for the stage-gate world (C2, T20: v3/stage_world.py).

test_s4_sensitivity.py runs the stage world as one of the six one-factor sensitivities
(the RQ4 story: every switch flips exactly one factor).  This module protects the stage
world's OWN declared behaviour in isolation, at unit granularity and deterministically (no
Monte-Carlo sweep): the four stages and their prices, the D2 target<->stage round-trip, the
gate reading objects in flight and its true/false rejection accounting, the C16 stage-depth
fixing, and a carrier-world policy mapped onto stages through the adapter.

Each test protects the DCM rows of v3/dcm/T20.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  DEV ONLY: episodes run on the v2 dev corpus
(v3/corpus.dev_workflows).  Run from auditgame/.
"""
import unittest
from dataclasses import replace

from core import Task, Workflow
from v3 import api as A
from v3 import attackers as AT
from v3 import config as C
from v3 import corpus as K
from v3 import runner as R
from v3 import stage_world as SW

CELL = C.Cell(rho=0.25, delta=4)
STAGE = replace(C.PRIMARY, audit_reading="stage")
TOPICS = ["auth", "cache", "routing", "serializer", "orm", "migration", "views", "admin"]


def _wf(topics=TOPICS, wf_id="wf-sw"):
    return Workflow(wf_id, "repo/sw", [Task(f"{wf_id}-t{t + 1}", "repo/sw", f"{t:07x}", tp,
                                            f"fix {tp}") for t, tp in enumerate(topics)])


def _dev_plans(n_wf=3, world=STAGE, cell=CELL):
    """(wf, attack name, placement) on the first dev workflows, planned in `world`; N3:
    infeasible placements are left out."""
    out = []
    for wf in K.dev_workflows()[:n_wf]:
        for a in AT.held_out():
            pl = SW.plan_in_world(AT.by_name(a), wf, cell, world)
            if pl is not None:
                out.append((wf, a, pl))
    return out


class Script(A.PolicyBase):
    """A stage-native scripted defender: acts[t] is an AuditAction (or a stage name)."""
    name = "script"

    def __init__(self, ctx, acts=None):
        super().__init__(ctx)
        self.acts = dict(acts or {})
        self.obs = {}

    def act(self, t, B_t):
        a = self.acts.get(t)
        return self.action(a) if isinstance(a, str) else a

    def observe(self, t, obs):
        self.obs[t] = obs


class CarrierScript(A.PolicyBase):
    """A carrier-world scripted defender (targets in config.TARGETS): it audits one carrier
    target per task and quarantines a carrier once.  Run in the stage world it goes through
    stage_world.carrier_policy; a bare instance is the adapter's inner policy."""
    name = "carrier-script"

    def __init__(self, ctx, acts=None, quar=None):
        super().__init__(ctx)
        self.acts, self.quar = dict(acts or {}), dict(quar or {})
        self.obs = {}

    def act(self, t, B_t):
        a = self.acts.get(t)
        return self.action(a) if isinstance(a, str) else a

    def observe(self, t, obs):
        self.obs[t] = obs

    def quarantine(self, t):
        return self.quar.get(t)


# ---------------------------------------------------------------------------------------
# Deterministic fakes for the gate (no detector Monte-Carlo)
# ---------------------------------------------------------------------------------------

class _FakeItem:
    def __init__(self, item_id, poisoned, created_at):
        self.item_id, self.poisoned, self.created_at = item_id, poisoned, created_at


class _FakeDeep:
    """A detector at a fixed depth: fires for exactly the item ids in `fire_ids`."""
    def __init__(self, fire_ids):
        self.fire_ids = set(fire_ids)

    def score(self, item, t, seed):
        return 1.0 if item.item_id in self.fire_ids else 0.0

    def fires(self, s):
        return s > 0.5


class _FakeDet:
    def __init__(self, fire_ids):
        self._deep = _FakeDeep(fire_ids)

    def at_depth(self, depth):
        return self._deep


class TestStageWorld(unittest.TestCase):

    # ---------------------------------------------------------------------------------
    def test_stages_are_the_four_named_and_priced(self):
        """D8.stages -- "with 4 audit stages (insertion, retrieval, delegation, commit) and 4
        carriers (memory, cached skill, tool queue, branch).": the stage world names exactly
        the four stages in the draft's order, each priced at the draft's S7 unit price
        (0.4 / 0.9 / 1.6 / 4.1), and equal to the carrier-world unit price of the carrier it
        audits under D2 (config.KAPPA_UNIT through STAGE_OF_TARGET)."""
        self.assertEqual(SW.STAGES, ("insertion", "retrieval", "delegation", "commit"))
        self.assertEqual(SW.STAGE_UNIT,
                         {"insertion": 0.4, "retrieval": 0.9, "delegation": 1.6, "commit": 4.1})
        self.assertEqual(tuple(SW.STAGE_UNIT), SW.STAGES, "the S7 price order")
        for target, stage in SW.STAGE_OF_TARGET.items():
            self.assertEqual(SW.STAGE_UNIT[stage], C.KAPPA_UNIT[target],
                             "a stage costs its carrier's draft unit price")

    # ---------------------------------------------------------------------------------
    def test_stage_target_roundtrip_is_the_d2_mapping(self):
        """D4.defender -- "At each task the defender chooses an audit action at ∈ A =
        {none} ∪ {(audit, k, depth)} with cost κ (k, depth)": k is read both as a carrier and
        as a stage; STAGE_OF_TARGET / TARGET_OF_STAGE are the D2 bijection between them
        (memory<->insertion, queue<->retrieval, skill<->delegation, commit<->commit) and
        round-trip in both directions, so an action's k maps there and back unchanged."""
        self.assertEqual(SW.STAGE_OF_TARGET,
                         {"memory": "insertion", "queue": "retrieval", "skill": "delegation",
                          "commit": "commit"})
        self.assertEqual(set(SW.STAGE_OF_TARGET), set(C.TARGETS))
        self.assertEqual(set(SW.TARGET_OF_STAGE), set(SW.STAGES))
        for target in C.TARGETS:                                   # carrier -> stage -> carrier
            self.assertEqual(SW.TARGET_OF_STAGE[SW.STAGE_OF_TARGET[target]], target)
        for stage in SW.STAGES:                                    # stage -> carrier -> stage
            self.assertEqual(SW.STAGE_OF_TARGET[SW.TARGET_OF_STAGE[stage]], stage)
        # the adapter's private mappers round-trip a whole AuditAction
        for target in C.TARGETS:
            a = A.AuditAction(target, 2)
            self.assertEqual(SW._to_stage(a), A.AuditAction(SW.STAGE_OF_TARGET[target], 2))
            self.assertEqual(SW._to_target(SW._to_stage(a)), a)
        self.assertIsNone(SW._to_stage(None))
        self.assertIsNone(SW._to_target(None))

    # ---------------------------------------------------------------------------------
    def test_c16_fixes_stage_depth(self):
        """D8.stages -- "with 4 audit stages (insertion, retrieval, delegation, commit) and 4
        carriers (memory, cached skill, tool queue, branch).": the cell fixes each stage's
        depth as it fixes its carrier's (C16), so stage_depths / stage_kappa are the cell's
        carrier values re-keyed by stage; cost is unit price x depth, and StageEpisode.cost
        rejects a non-stage k, a depth above the cell's, and a non-positive depth (a declared
        rule may lower the depth, never raise it)."""
        self.assertEqual(SW.stage_depths(CELL),
                         {"insertion": 3, "retrieval": 2, "delegation": 1, "commit": 1})
        dep = CELL.depths()
        self.assertEqual(SW.stage_depths(CELL),
                         {s: dep[SW.TARGET_OF_STAGE[s]] for s in SW.STAGES})
        self.assertEqual(SW.stage_kappa(CELL),
                         {s: SW.STAGE_UNIT[s] * SW.stage_depths(CELL)[s] for s in SW.STAGES})
        ep = SW.StageEpisode(_wf(), None, lambda ctx: Script(ctx), STAGE, CELL, 0)
        # cost is unit price x depth, linear below the cell's fixed depth
        self.assertAlmostEqual(ep.cost(A.AuditAction("insertion", 3)), 0.4 * 3)
        self.assertAlmostEqual(ep.cost(A.AuditAction("insertion", 1)), 0.4 * 1)
        self.assertAlmostEqual(ep.cost(A.AuditAction("commit", 1)), 4.1)
        for bad in (A.AuditAction("memory", 1),           # a carrier, not a stage
                    A.AuditAction("insertion", 4),        # above the cell's depth 3
                    A.AuditAction("commit", 2),           # above the cell's depth 1
                    A.AuditAction("insertion", 0),        # non-positive
                    A.AuditAction("insertion", True)):    # bool is not a depth
            with self.assertRaises(ValueError):
                ep.cost(bad)

    # ---------------------------------------------------------------------------------
    def test_gate_reading_inspects_objects_in_flight(self):
        """D8.stages -- "with 4 audit stages (insertion, retrieval, delegation, commit) and 4
        carriers (memory, cached skill, tool queue, branch).": the bought stage inspects the
        objects IN FLIGHT at task t across every carrier; the insertion / delegation gates
        see only objects written at t, the commit gate sees the task's single patch, and every
        inspected object is recorded in the evaluator-only trace (StageEpisode.inspected)."""
        for stage in SW.STAGES:
            saw_any = False
            for wf, _a, pl in _dev_plans(3):
                H = wf.H
                ep = SW.StageEpisode(wf, pl, lambda ctx, s=stage: Script(
                    ctx, {t: s for t in range(H)}), STAGE, CELL, 0)
                pol = ep.policy
                while ep.t < H:
                    t = ep.t
                    ep.step()
                    obs = pol.obs[t]
                    self.assertEqual(obs.bought, A.AuditAction(stage, ep.ctx.depths[stage]))
                    if stage == "commit":
                        self.assertIn(obs.written_at, ((), (t,)))   # only this task's patch
                    elif stage in ("insertion", "delegation"):
                        # a write gate sees only objects written at t (in flight now)
                        if obs.written_at:
                            saw_any = True
                        self.assertTrue(all(w == t for w in obs.written_at),
                                        "a write gate sees only objects written at t")
                    else:                                           # retrieval: items pulled at t
                        # the payloads were written earlier, so written_at may precede t
                        if obs.written_at:
                            saw_any = True
                        self.assertTrue(all(w <= t for w in obs.written_at),
                                        "a retrieval gate cannot see a future write")
                # every inspected object is on the trace, tagged with the bought stage
                stages_on_trace = {s for _t, s, _i in ep.inspected}
                self.assertTrue(stages_on_trace <= {stage},
                                "only the bought stage inspects anything")
            if stage in ("insertion", "retrieval", "delegation"):
                self.assertTrue(saw_any, f"{stage}: some object was in flight")

    # ---------------------------------------------------------------------------------
    def test_gate_accounting_true_false_rejections(self):
        """D8.stages -- "with 4 audit stages (insertion, retrieval, delegation, commit) and 4
        carriers (memory, cached skill, tool queue, branch).": a firing object is rejected; a
        benign rejection counts as a false quarantine (fq / false_removed), a poisoned one as
        a true quarantine (true_q) and sets detected_at, a clean solved patch the commit gate
        rejects as a clean task lost (L1).  StageGates records what it inspected and rejected;
        the per-stage blocks reconcile with fq + true_q."""
        # (a) the gate's own accounting, deterministic (a stub detector)
        poison = _FakeItem("p", poisoned=True, created_at=2)
        benign = _FakeItem("b", poisoned=False, created_at=2)
        clean = _FakeItem("c", poisoned=False, created_at=2)      # never fires
        g = SW.StageGates("insertion", 3, _FakeDet({"p", "b"}), t=2, seed=0)
        self.assertFalse(g.admit(poison, "insertion"))            # fires -> rejected
        self.assertFalse(g.admit(benign, "insertion"))            # fires -> rejected
        self.assertTrue(g.admit(clean, "insertion"))              # passes
        self.assertEqual((g.true_blocks, g.false_blocks), (1, 1))
        self.assertEqual([it.item_id for it in g.rejected], ["p", "b"])
        self.assertEqual([(it.item_id, fired) for it, _s, fired in g.seen],
                         [("p", True), ("b", True), ("c", False)])
        # H8: with ingress hidden the insertion gate does not even look at an ingress item
        gh = SW.StageGates("insertion", 3, _FakeDet({"p"}), t=2, seed=0,
                           ingress_ids=frozenset({"p"}), ingress_visible=False)
        self.assertTrue(gh.admit(poison, "insertion"))
        self.assertEqual((gh.true_blocks, gh.seen), (0, []))
        # a gate for a different stage passes an object it is not watching
        self.assertTrue(SW.StageGates("delegation", 1, _FakeDet({"p"}), 2, 0)
                        .admit(poison, "insertion"))
        # (b) the episode's counters reconcile with the per-stage blocks, on dev
        for wf, _a, pl in _dev_plans(3):
            H = wf.H
            for stage in SW.STAGES:
                ep = SW.StageEpisode(wf, pl, lambda ctx, s=stage: Script(
                    ctx, {t: s for t in range(H)}), STAGE, CELL, 1)
                rec = ep.run().record
                blocks = ep.counters()["blocks"]
                self.assertEqual(rec.fq + rec.true_q,
                                 sum(v["true"] + v["false"] for v in blocks.values()))
                for s in SW.STAGES:                    # only the bought stage rejects anything
                    if s != stage:
                        self.assertEqual(blocks[s], {"true": 0, "false": 0})
                self.assertEqual(ep.false_removed, rec.fq)
                if rec.true_q:
                    self.assertIsNotNone(ep.detected_at)
                else:
                    self.assertIsNone(ep.detected_at)
                self.assertLessEqual(ep.clean_lost_branch, rec.true_q + rec.fq + rec.t_lost)

    # ---------------------------------------------------------------------------------
    def test_carrier_policy_maps_onto_stages(self):
        """D4.defender -- "At each task the defender chooses an audit action at ∈ A =
        {none} ∪ {(audit, k, depth)} with cost κ (k, depth)": a carrier-world policy runs in
        the stage world through stage_world.carrier_policy -- its carrier target maps to the
        D2 stage, its observation maps back to a carrier target, and its lines 8-9 are dropped
        by default (the gate's rejection already is the quarantine) but kept with
        keep_quarantine=True; the adapter forwards delta_hat / line5_source (None here)."""
        wf, _a, pl = _dev_plans(1)[0]
        acts = {0: "memory", 1: "queue", 2: "skill", 3: "commit"}   # carrier targets

        def inner(ctx):
            return CarrierScript(ctx, acts=acts, quar={2: "memory"})

        # keep_quarantine defaults to False: the baseline's alarm-rule quarantine is dropped
        ep = SW.episode_in_world(wf, pl, inner, STAGE, CELL, 0)     # wraps with carrier_policy
        self.assertIsInstance(ep, SW.StageEpisode)
        rec = ep.run().record
        self.assertEqual(set(rec.audits), set(SW.STAGES))
        self.assertEqual(rec.audits["insertion"], [0], "memory target -> insertion stage")
        self.assertEqual(rec.audits["retrieval"], [1], "queue -> retrieval")
        self.assertEqual(rec.audits["delegation"], [2], "skill -> delegation")
        self.assertEqual(rec.audits["commit"], [3], "commit -> commit")
        self.assertEqual(rec.quarantines, (), "keep_quarantine=False drops lines 8-9")
        # the inner policy sees its observation keyed back to a carrier target
        adapter = ep.policy
        self.assertIsInstance(adapter, SW.CarrierPolicyInStages)
        for t, target in ((0, "memory"), (3, "commit")):
            obs = adapter.inner.obs[t]
            if obs.bought is not None:
                self.assertEqual(obs.bought.target, target)
        self.assertIsNone(adapter.delta_hat)                        # a baseline has neither
        self.assertIsNone(adapter.line5_source)
        # keep_quarantine=True lets the inner policy's own lines 8-9 through
        ep2 = SW.StageEpisode(wf, pl, SW.carrier_policy(inner, keep_quarantine=True),
                              STAGE, CELL, 0)
        rec2 = ep2.run().record
        self.assertEqual(rec2.quarantines, ((2, "memory"),), "keep_quarantine=True keeps them")
        # runner.Episode refuses the stage world, StageEpisode refuses the carrier world
        with self.assertRaises(ValueError):
            R.Episode(wf, pl, inner, STAGE, CELL, 0)
        with self.assertRaises(ValueError):
            SW.StageEpisode(wf, pl, SW.carrier_policy(inner), C.PRIMARY, CELL, 0)


if __name__ == "__main__":
    unittest.main()
