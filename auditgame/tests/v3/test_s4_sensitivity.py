"""The stage-gate world (C2) and the one-factor sensitivity worlds (Q2) of v3 (T20:
v3/stage_world.py).

Each test protects the DCM rows of v3/dcm/T20.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  DEV ONLY: every episode runs on the v2 corpus
(v3/corpus.dev_workflows).  Run from auditgame/.
"""
import unittest
from dataclasses import replace

from core import Task, Workflow
from v3 import api as A
from v3 import attackers as AT
from v3 import baselines as B
from v3 import config as C
from v3 import corpus as K
from v3 import library as L
from v3 import observe as O
from v3 import payload as P
from v3 import runner as R
from v3 import stage_world as SW

CELL = C.Cell(rho=0.25, delta=4)
SENS = dict(C.sensitivities())
STAGE = SENS["stage"]
TOPICS = ["auth", "cache", "routing", "serializer", "orm", "migration", "views", "admin"]


def _wf(topics=TOPICS, wf_id="wf-t20"):
    return Workflow(wf_id, "repo/t20", [Task(f"{wf_id}-t{t + 1}", "repo/t20", f"{t:07x}", tp,
                                             f"fix {tp}") for t, tp in enumerate(topics)])


def _dev_plans(n_wf=4, world=C.PRIMARY, cell=CELL, attacks=None):
    """(wf, attack name, placement) on the first dev workflows, planned in `world` (N3:
    infeasible placements are left out)."""
    out = []
    for wf in K.dev_workflows()[:n_wf]:
        for a in (attacks or AT.held_out()):
            pl = SW.plan_in_world(AT.by_name(a), wf, cell, world)
            if pl is not None:
                out.append((wf, a, pl))
    return out


def _recording(log):
    """An observe.ObservationModel that logs (t, item id) of every item a sweep scores."""
    class Recording(O.ObservationModel):
        def sweep(self, t, target, depth, store, seed):
            ins = super().sweep(t, target, depth, store, seed)
            log.extend((t, it.item_id) for it in ins.items)
            return ins
    return Recording


class Script(A.PolicyBase):
    """A stage-native scripted defender: acts[t] is an AuditAction (or a stage name)."""
    name = "script"

    def __init__(self, ctx, acts=None, quarantines=None):
        super().__init__(ctx)
        self.acts, self.quars = dict(acts or {}), dict(quarantines or {})
        self.obs = {}

    def act(self, t, B_t):
        a = self.acts.get(t)
        return self.action(a) if isinstance(a, str) else a

    def observe(self, t, obs):
        self.obs[t] = obs

    def quarantine(self, t):
        return self.quars.get(t)


class SentinelShape(A.PolicyBase):
    """Algorithm 1's shape on the frozen api, for a world test until T15's Sentinel is on
    this branch: line 5 = a library member's distribution (L-SW-commit3), line 7 = the
    observation, lines 8-9 = quarantine the carrier of the alarmed target."""
    name = "sentinel-shape"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.member = L.make_member("L-SW-commit3", ctx)
        self._alarm = None

    def act(self, t, B_t):
        return self.member.act(t, B_t)

    def observe(self, t, obs):
        self._alarm = obs.bought.target if obs.alarm and obs.bought is not None else None

    def quarantine(self, t):
        return None if self._alarm is None else C.CARRIER_OF_TARGET[self._alarm]

    def decision_log(self):
        return self.member.decision_log()


class TestS4Sensitivity(unittest.TestCase):

    # ---------------------------------------------------------------------------------
    def test_stage_world_action_is_stage_and_depth(self):
        """D8.stages C2 -- "with 4 audit stages (insertion, retrieval, delegation, commit) and
        4 carriers (memory, cached skill, tool queue, branch).": in the stage world the
        action is (stage, depth) at kappa(stage, depth) = unit price x depth, the cell fixing
        the depth; the bought stage inspects the objects in flight at t across every
        carrier and rejects a firing one."""
        self.assertEqual(SW.STAGES, ("insertion", "retrieval", "delegation", "commit"))
        self.assertEqual(STAGE, replace(C.PRIMARY, audit_reading="stage"))
        for t, s in SW.STAGE_OF_TARGET.items():
            self.assertEqual(SW.STAGE_UNIT[s], C.KAPPA_UNIT[t], "the draft's S7 prices")
        self.assertEqual(SW.stage_depths(CELL),
                         {"insertion": 3, "retrieval": 2, "delegation": 1, "commit": 1})
        wf = _wf()
        # cost linear in depth, below the cell's depth; audits keyed by stage
        acts = {0: A.AuditAction("insertion", 2), 1: A.AuditAction("retrieval", 2),
                2: A.AuditAction("delegation", 1), 3: A.AuditAction("commit", 1)}
        rec = SW.StageEpisode(wf, None, lambda ctx: Script(ctx, acts), STAGE, CELL, 0).run().record
        self.assertAlmostEqual(rec.spent, 2 * 0.4 + 2 * 0.9 + 1.6 + 4.1)
        self.assertEqual(rec.audits, {"insertion": [0], "retrieval": [1], "delegation": [2],
                                      "commit": [3]})
        self.assertEqual(rec.world["audit_reading"], "stage")
        for bad in (A.AuditAction("memory", 1), A.AuditAction("commit", 2),
                    A.AuditAction("delegation", 2)):
            with self.assertRaises(ValueError):
                SW.StageEpisode(wf, None, lambda ctx, b=bad: Script(ctx, {0: b}), STAGE,
                                CELL, 0).run()
        with self.assertRaises(ValueError):
            SW.StageEpisode(wf, None, lambda ctx: Script(ctx), C.PRIMARY, CELL, 0)
        with self.assertRaises(ValueError):
            R.Episode(wf, None, lambda ctx: Script(ctx), STAGE, CELL, 0)
        # what each gate inspects, on dev
        span = in_flight = 0
        for wf, _, pl in _dev_plans(6):
            H = wf.H
            for stage in SW.STAGES:
                for seed in (0, 1):
                    ep = SW.StageEpisode(wf, pl, lambda ctx, s=stage: Script(
                        ctx, {t: s for t in range(H)}), STAGE, CELL, seed)
                    pol = ep.policy
                    while ep.t < H:
                        t = ep.t
                        before = ep.agent.retrieve(ep.store, wf.tasks[t].topic)
                        ep.step()
                        o = pol.obs[t]
                        self.assertEqual(o.bought, A.AuditAction(stage, ep.ctx.depths[stage]))
                        if stage == "retrieval":
                            # after injection at iota the payload is in flight too
                            if t != pl.iota:
                                self.assertEqual(o.n_items, len(before))
                            span += len({it.carrier for it in before}) >= 2
                        elif stage == "commit":
                            self.assertEqual(o.written_at, (t,))
                        else:
                            self.assertTrue(all(w == t for w in o.written_at),
                                                "a gate sees objects written at t")
                            in_flight += o.n_items
                    rec = ep.finish().record
                    blocks = ep.counters()["blocks"]
                    self.assertEqual(rec.fq + rec.true_q,
                                     sum(v["true"] + v["false"] for v in blocks.values()))
                    for s in SW.STAGES:
                        if s != stage:
                            self.assertEqual(blocks[s], {"true": 0, "false": 0})
                    # a rejected patch never lands: harm needs a marked patch in the branch
                    if rec.harm:
                        self.assertTrue(any(it.poisoned for it in ep.store.live("branch")))
        self.assertGreater(span, 0, "the retrieval gate sees more than one carrier")
        self.assertGreater(in_flight, 0)
        # the insertion gate inspects the attacker's write at iota (write channel)
        wf = _wf()
        pl = AT.Placement((next(p for p in P.plan_sleeper_all(wf, "memory", 4) if p.iota == 0),),
                          "write")
        hits = 0
        for seed in range(20):
            ep = SW.StageEpisode(wf, pl, lambda ctx: Script(ctx, {0: "insertion"}), STAGE,
                                 C.Cell(rho=0.0, delta=4), seed)
            ep.step()
            root = pl.payloads[0].item(wf).item_id
            if root not in {it.item_id for it in ep.store.live("memory")}:
                hits += 1
                self.assertEqual(ep.detected_at, 0)
                self.assertEqual(ep.blocks["insertion"]["true"], 1)
        self.assertGreater(hits, 10, "d' sqrt(3) at depth 3 rejects the payload most times")

    # ---------------------------------------------------------------------------------
    def test_sentinel_runs_in_both_worlds(self):
        """C2 D4.defender -- "At each task the defender chooses an audit action at ∈ A =
        {none} ∪ {(audit, k, depth)} with cost κ (k, depth)": the same policy objects run in
        the carrier world and in the stage world (k a carrier / a stage), end to end on dev,
        with the same agent draws; a policy with its own lines 8-9 keeps them in the stage
        world, and a stage episode resumes from a snapshot (the rollouts of line 5)."""
        systems = {n: B.factory(n) for n in B.BASELINES}
        systems["sentinel-shape"] = SentinelShape
        plans = _dev_plans(3)
        self.assertGreater(len(plans), 5)
        for name, fac in systems.items():
            keep = name == "sentinel-shape"
            for wf, a, pl in plans[:6]:
                for seed in (0, 1):
                    out = {}
                    for world in (C.PRIMARY, STAGE):
                        r = SW.run_in_world(wf, pl, fac, world, CELL, seed, attack=a,
                                            keep_quarantine=keep).record
                        self.assertEqual(r.world["audit_reading"], world.audit_reading)
                        self.assertEqual(r.policy, name)
                        self.assertLessEqual(r.spent, r.budget + 1e-9)
                        self.assertEqual(A.EpisodeRecord.from_dict(r.to_dict()), r)
                        keys = set(r.audits)
                        self.assertEqual(keys, set(SW.STAGES if world == STAGE else C.TARGETS))
                        out[world.audit_reading] = r
                    self.assertEqual(out["carrier"].cell_id, out["stage"].cell_id)
                    self.assertEqual(out["carrier"].n_solved, out["stage"].n_solved,
                                     "the solve draw is the world's own (N4): same in both")
                    if name == "B1 audit-at-commit":
                        self.assertEqual(out["stage"].audits["commit"],
                                         out["carrier"].audits["commit"])
        # lines 8-9 pass through for Sentinel, not for a baseline's alarm rule
        seen_q = {True: 0, False: 0}
        for wf, a, pl in plans:
            for seed in range(3):
                for keep in (True, False):
                    r = SW.run_in_world(wf, pl, SentinelShape, STAGE, CELL, seed,
                                        keep_quarantine=keep).record
                    seen_q[keep] += len(r.quarantines)
        self.assertGreater(seen_q[True], 0)
        self.assertEqual(seen_q[False], 0)
        # snapshot / resume in the stage world
        wf, a, pl = plans[1]
        full = SW.run_in_world(wf, pl, B.factory("B2 uniform random"), STAGE, CELL, 7).record
        for t in (0, 2, wf.H):
            ep = SW.episode_in_world(wf, pl, B.factory("B2 uniform random"), STAGE, CELL, 7)
            for _ in range(t):
                ep.step()
            got = R.resume(ep.snapshot(), t).run().record
            self.assertEqual(got.to_json(), full.to_json(), f"resumed at {t}")

    # ---------------------------------------------------------------------------------
    def test_each_sensitivity_run_flips_exactly_one_factor(self):
        """Q2 D10.rq4 -- "RQ4 Attribution and sensitivity.": each sensitivity world differs
        from the primary configuration in exactly one switch -- in the record AND in what
        the modules actually use (observe, episode class, oracle, agent, attacker) -- and
        runs end to end on dev with the baselines; the flip is visible in the outcomes.
        One world per switch:
          A7                D7.commit-prov  "Audit actions. Insertion audit (content and
                            provenance check on new memory records), … commit audit (patch
                            review, differential testing, provenance of contributing skills)."
          stage             D8.stages       "with 4 audit stages (insertion, retrieval,
                            delegation, commit) and 4 carriers (memory, cached skill, tool
                            queue, branch)."
          reversible        D4.payoff       "with verified harm measured by a sealed oracle
                            at the end of the horizon"
          ingress-hidden    D10.6.ingress   "Against audit-on-insertion, every best response
                            inserts through repository ingress rather than direct write—the
                            unaudited channel— which is why it is the worst policy."
          drift-persistent  D4.drift        "A latent process independently modifies
                            carriers benignly at rate β, with observation statistics matched
                            to poisoning events."
          seed-2            D4.attacker     "Its budget constrains the number of carriers
                            it may seed and the magnitude of each." """
        self.assertEqual(sorted(SENS), sorted(["A7", "stage", "reversible", "ingress-hidden",
                                               "drift-persistent", "seed-2"]))
        systems = ("B1 audit-at-commit", "B2 uniform random", "B3 audit-on-insertion",
                   "B4 audit-on-retrieval", "B5 risk-score", "B6 two-stage")
        base_plans = {(wf.wf_id, a): pl for wf, a, pl in _dev_plans(4)}
        for sname, world in C.sensitivities():
            field = [f for f in C.world_fields()
                     if getattr(world, f) != getattr(C.PRIMARY, f)]
            self.assertEqual(len(field), 1, sname)
            field = field[0]
            plans = _dev_plans(4, world)
            self.assertGreater(len(plans), 5, sname)
            differs = False
            for wf, a, pl in plans:
                p0 = base_plans.get((wf.wf_id, a))
                if p0 is None:
                    continue
                if field != "n_seeded":
                    self.assertEqual(pl, p0, "the attacker's placement is the primary's")
                for name in systems:
                    for seed in (0, 1):
                        e0 = SW.episode_in_world(wf, p0, B.factory(name), C.PRIMARY, CELL, seed)
                        e1 = SW.episode_in_world(wf, pl, B.factory(name), world, CELL, seed)
                        c0, c1 = SW.components(e0), SW.components(e1)
                        self.assertEqual(c0, {f: getattr(C.PRIMARY, f)
                                              for f in C.world_fields()})
                        diff = sorted(k for k in c0 if c0[k] != c1[k])
                        self.assertEqual(diff, [field], f"{sname} / {name}")
                        self.assertEqual(c1[field], getattr(world, field))
                        r0, r1 = e0.run().record, e1.run().record
                        wdiff = [f for f in C.world_fields() if r0.world[f] != r1.world[f]]
                        self.assertEqual(wdiff, [field])
                        self.assertEqual((r0.cell_id, r0.n_solved), (r1.cell_id, r1.n_solved))
                        self.assertEqual(r1.world_id, C.world_id(world))
                        differs |= ((r0.harm, r0.fq, r0.t_lost, r0.c_traj, r0.quarantines)
                                    != (r1.harm, r1.fq, r1.t_lost, r1.c_traj, r1.quarantines))
            self.assertTrue(differs, f"{sname}: the flipped factor changes some outcome")

    # ---------------------------------------------------------------------------------
    def test_h8_verdict_is_taken_from_ingress_visible_world(self):
        """H8 D10.6.ingress -- "Against audit-on-insertion, every best response inserts
        through repository ingress rather than direct write—the unaudited channel— which is
        why it is the worst policy.": H8's verdict is read in the primary world, whose
        insertion audit sees ingress; in the ingress-hidden world B3 cannot see an ingress
        payload by construction, so there it is only printed."""
        self.assertEqual(SW.h8_verdict_world(), C.PRIMARY)
        self.assertTrue(SW.h8_verdict_world().ingress_visible)
        self.assertEqual(SW.h8_role(C.PRIMARY), SW.H8_VERDICT)
        self.assertEqual(SW.h8_role(SENS["ingress-hidden"]), SW.H8_PRINTED)
        for n, w in C.sensitivities():
            if n != "ingress-hidden":
                self.assertIsNone(SW.h8_role(w), n)
        # by construction: B3's audit never inspects an ingress payload written into memory
        # when ingress is hidden, in the carrier and in the stage world; when ingress is
        # visible it inspects it at iota, every time.  (A whole-memory quarantine on a
        # false alarm can still remove it: that is luck, not sight.)
        memory_ingress = [a.name for a in AT.br_attacks()
                          if a.carrier_rule == "memory" and a.channel == "ingress"]
        seen = {}
        for world in (C.PRIMARY, SENS["ingress-hidden"], STAGE,
                      replace(STAGE, ingress_visible=False)):
            n = runs = 0
            for wf, a, pl in _dev_plans(8, world, attacks=memory_ingress):
                self.assertTrue(pl.ingress)
                root = pl.payloads[0].item(wf).item_id
                for seed in range(3):
                    swept = []
                    ep = SW.episode_in_world(wf, pl, B.factory("B3 audit-on-insertion"), world,
                                             CELL, seed, observer=_recording(swept))
                    ep.run()
                    if world.audit_reading == "stage":
                        swept = [(t, i) for t, _, i in ep.inspected]
                    hit = [t for t, i in swept if i == root]
                    runs += 1
                    n += bool(hit) and min(hit) == pl.iota
                    if not world.ingress_visible:
                        self.assertEqual(hit, [], "B3 never inspects the ingress payload")
            seen[(world.audit_reading, world.ingress_visible)] = (n, runs)
        self.assertGreater(seen[("carrier", True)][1], 5)
        for key, (n, runs) in seen.items():
            self.assertEqual(n, runs if key[1] else 0, key)

    # ---------------------------------------------------------------------------------
    def test_sensitivity_uses_primary_table_as_declared(self):
        """O15 DA1.l5 -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust over a
        restricted library": in every sensitivity world (and at K_d != 2) line 5 reads the
        primary world's table, declared as Sentinel's model misspecified in the one flipped
        factor; the table key does not depend on the world."""
        self.assertEqual(C.TABLE_WORLD, "primary")
        self.assertEqual(C.DECIDED_O["O15"], {"table_world": "primary"})
        m = SW.misspecification(C.PRIMARY, CELL)
        self.assertEqual((m["differs_in"], m["label"]), ([], ""))
        for name, w in C.sensitivities():
            self.assertEqual(SW.table_world(w), C.PRIMARY)
            m = SW.misspecification(w, CELL)
            field = [f for f in C.world_fields() if getattr(w, f) != getattr(C.PRIMARY, f)]
            self.assertEqual(m["differs_in"], field, name)
            self.assertEqual(m["table_world"], "primary")
            self.assertEqual(m["table_world_id"], C.world_id(C.PRIMARY))
            self.assertEqual(m["world"], name)
            self.assertIn("misspecified in one factor: " + field[0], m["label"])
            self.assertEqual(m["table_key"], C.table_key_id(CELL))
        kd = C.Cell(rho=0.25, delta=4, k_delegated=3)
        m = SW.misspecification(C.PRIMARY, kd)
        self.assertEqual(m["differs_in"], ["k_delegated"])
        self.assertEqual(m["table_key"], C.table_key_id(CELL), "K_d is not a table key")
        self.assertEqual(SW.misspecification(STAGE, kd)["differs_in"],
                         ["audit_reading", "k_delegated"])


if __name__ == "__main__":
    unittest.main()
