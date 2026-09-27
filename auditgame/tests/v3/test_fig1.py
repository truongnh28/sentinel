"""Figure 1 of the draft, replayed step by step on the v3 runner (T6, v3/runner.py).

The test protects the DF1.* rows of v3/dcm/T06.csv; its docstring carries the ids and the
verbatim sentences.  The world is the primary one with the DECLARED kernel (no forced
rate): the seed below is the first of a search for a draw sequence that follows the
figure (no skill at t1, a skill at t2, no poisoned queued call before t5, adoption and a
solved patch at t5).  Only the detector scores are forced (plan T6): the memory audits of
t3-t4 read the poisoned note, whose declared mean is d' sqrt(3), and the figure has them
find nothing.  Run from auditgame/.
"""
import dataclasses
import random
import unittest

from core import Task, Workflow, seed_of
from v3 import api as A
from v3 import attackers as AT
from v3 import config as C
from v3 import observe as O
from v3 import oracle as OR
from v3 import payload as P
from v3 import runner as R

#: H = 7 tasks; t1..t7 of the figure are t = 0..6 (0-based, task number = t + 1).
TOPICS = ["auth", "cache", "routing", "serializer", "orm", "migration", "views"]
SEED = 69
INSERTION_RATE = 0.3
FORCED_SCORE = 0.0                   # below every declared threshold (tau_det > 1)
CELL = C.Cell(rho=0.0, delta=4)      # A0 is the primary world's provenance


def fig1_workflow():
    return Workflow("wf-fig1", "repo/fig1",
                    [Task(f"wf-fig1-t{t + 1}", "repo/fig1", f"{t:07x}", tp, f"fix {tp}")
                     for t, tp in enumerate(TOPICS)])


class ForcedScores(O.ObservationModel):
    """The declared observation model with every detector score forced to FORCED_SCORE."""

    def _force(self, ins):
        scores = tuple(FORCED_SCORE for _ in ins.scores)
        firing = tuple(self.fires(s) for s in scores)
        return dataclasses.replace(ins, scores=scores, firing=firing,
                                   alarm_patch=any(firing), alarm=any(firing))

    def sweep(self, *a, **kw):
        return self._force(super().sweep(*a, **kw))

    def commit(self, *a, **kw):
        return self._force(super().commit(*a, **kw))


class Fig1Policy(A.PolicyBase):
    """The defender of Figure 1: an insertion audit at rate 0.3 at t1, retrieval audits of
    the memory store at t3-t4, the commit audit at t5/t6; quarantine on an alarm."""
    name = "fig1"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.obs = {}
        self.insertion_draw = random.Random(seed_of(ctx.rng_seed, 0, "fig1-insertion")).random()

    def act(self, t, B_t):
        if t == 0:
            return self.action("memory") if self.insertion_draw < INSERTION_RATE else None
        if t in (2, 3):
            return self.action("memory")
        if t == 4:
            return self.action("commit")
        return None

    def observe(self, t, obs):
        self.obs[t] = obs

    def quarantine(self, t):
        o = self.obs.get(t)
        if o is not None and o.alarm:
            return C.CARRIER_OF_TARGET[o.bought.target]
        return None


class TestFig1(unittest.TestCase):

    def test_figure1_replays_t1_to_t7(self):
        """DF1.t1 DF1.t2 DF1.t3-t4 DF1.t5 DF1.t6 DF1.t7 -- Figure 1, t1..t7 (t = 0..6):
        t1 "Attacker writes a poisoned note into shared memory. Insertion audit is running
        at rate 0.3; not sampled."  t2 "A skill is induced from a trajectory that used the
        note. The poison is now in two carriers."  t3-t4 "Two tasks complete normally.
        Retrieval audits sample the memory store and find nothing anomalous"  t5 "The skill
        runs on a target where its poisoned step matters. A patch is produced."  t6 "Commit
        audit inspects the patch. It is small, plausible, passes tests. Accepted."  t7
        "Harm manifests two tasks later, in a different module."  t5 and t6 are the same
        task sigma = 4 (L1)."""
        wf = fig1_workflow()
        pl_note = next(p for p in P.plan_sleeper_all(wf, "memory", 4) if p.iota == 0)
        pl = AT.Placement((pl_note,), "write")
        ep = R.Episode(wf, pl, Fig1Policy, C.PRIMARY, CELL, SEED, observer=ForcedScores)
        self.assertEqual((pl.iota, pl.sigma), (0, 4), "t1 = t 0 writes, t5 = t 4 activates")
        pol = ep.policy

        # t1 (t = 0): the note is written; the insertion audit is not drawn.
        ep.step()
        self.assertGreaterEqual(pol.insertion_draw, INSERTION_RATE)
        self.assertIsNone(pol.obs[0].requested)
        self.assertIsNone(pol.obs[0].bought)
        self.assertEqual(ep.c_traj, ["1000"])
        note = [it for it in ep.store.live("memory") if it.poisoned]
        self.assertEqual(len(note), 1)
        self.assertEqual((note[0].created_at, note[0].derived_from), (0, ()))

        # t2 (t = 1): a skill is induced from the trajectory that used the note.
        ep.step()
        self.assertEqual(ep.c_traj[-1], "1100", "poison in two carriers: memory and skill")
        skills = [it for it in ep.store.live("skill") if it.poisoned]
        self.assertEqual([(s.created_at, s.derived_from) for s in skills],
                         [(1, (note[0].item_id,))])

        # t3-t4 (t = 2, 3): memory audits run, find nothing; the tasks complete normally.
        ep.step()
        ep.step()
        for t in (2, 3):
            o = pol.obs[t]
            self.assertEqual(o.bought, A.AuditAction("memory", CELL.depths()["memory"]))
            self.assertGreater(o.n_items, 0)
            self.assertFalse(o.alarm)
            self.assertTrue(o.checkpoint, f"t{t + 1} completes normally")
        self.assertEqual(ep.quarantines, [])
        self.assertEqual(ep.c_traj[2:], ["1100", "1100"])

        # t5 / t6 (t = 4 = sigma): the skill runs on the target, a delegated patch is
        # produced; the commit audit in A0 at rho = 0 accepts it; it passes tests.
        ep.step()
        patch = [it for it in ep.store.live("branch") if it.created_at == 4]
        self.assertEqual(len(patch), 1)
        self.assertTrue(patch[0].poisoned)
        live_skills = {it.item_id: it for it in ep.store.live("skill") if it.poisoned}
        self.assertIn(skills[0].item_id, patch[0].derived_from)
        self.assertTrue(set(patch[0].derived_from) <= set(live_skills),
                        "the patch is the skill's product (delegated route), not the note's")
        self.assertIn("skill", CELL.delegated())
        o = pol.obs[4]
        self.assertEqual(C.PRIMARY.provenance, "A0")
        self.assertEqual(o.bought.target, "commit")
        self.assertIsNone(o.provenance)
        self.assertFalse(o.alarm, "accepted")
        self.assertTrue(o.checkpoint, "passes tests")
        self.assertEqual(ep.c_traj[-1], "1101")

        # t6 -> t7: nothing is visible yet; the oracle is sealed until the horizon's end.
        ep.step()
        with self.assertRaises(OR.OracleSealed):
            ep.oracle.harm
        with self.assertRaises(OR.OracleSealed):
            ep.oracle.read(5, ep.store)
        ep.step()
        out = ep.finish()
        self.assertEqual(out.verdict.read_at, 6, "read at t7, two tasks after sigma")
        self.assertEqual(out.record.harm, 1.0)
        self.assertEqual(out.record.harm_locked_at, 4)
        self.assertEqual(out.record.detected_at, None)
        self.assertTrue(out.record.missed_before_sigma)
        self.assertNotEqual(TOPICS[6], TOPICS[4], "a different module")
        self.assertEqual(out.postmortem.k, ("memory",))
        self.assertEqual((out.postmortem.iota, out.postmortem.sigma), (0, 4))


if __name__ == "__main__":
    unittest.main()
