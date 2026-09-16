"""
GATE 1 -- audit stages as an OBSERVATION layer (Task 25a).
Spec: task-25-brief.md, step 25a.1.

The benchmark declares FOUR audit stages (insertion / retrieval / delegation /
commit), but before this file existed the runner only ever priced audits at ONE
structural point per task -- the same point regardless of which carrier a policy
targeted. That point is, honestly, "commit": it runs AFTER this task's writes,
retrieval and skill-induction have already happened, exactly where the b1
audit-at-commit check sits.

25a does not let any policy CHOOSE a stage yet (that is 25b, gated on Task 22).
It only makes the stage axis REAL in `audit_seconds`: the one decision a policy
still makes is labelled by the stage it actually runs at ("commit"), and three
runner-initiated PROBES -- real detector-score passes, timed, never budgeted,
never quarantining anything -- give insertion/retrieval/delegation their first
measured seconds, so Task 22 has a place to plug in real (stage, carrier) data
once M3 lands a real store.
"""
from __future__ import annotations
import random
import unittest
from unittest import mock

import agent, build, detector, runner
import policies as P
from core import seed_of


def _wf(h=6, seed=0):
    return build.make_workflow("wf-stages", "django", h, random.Random(seed_of("stg", seed)))


def _run(policy_name="B1 audit-at-commit", budget=50.0, carrier="memory", delta=2,
         h=6, seed=1):
    wf = _wf(h)
    ps = build.plan_poison(wf, carrier, delta, random.Random(1))
    r = runner.run_once(
        wf, ps, P.make_policy(policy_name, budget, 1, "mid"),
        detector.Detector.from_setting("mid"), agent.MockAgent(), seed=seed)
    return wf, ps, r


class StagesExist(unittest.TestCase):

    def test_stages_declares_the_four_lifecycle_points_in_order(self):
        """The stage axis has to EXIST as code, not only as a table in a doc, or
        Task 22 has nothing to import and no way to say which of four numbers a
        measured second belongs to.

        Thesis claim (vi): "bon giai doan audit ton tai trong runner".
        """
        self.assertEqual(runner.STAGES,
                         ("insertion", "retrieval", "delegation", "commit"))


class CommitStageLabel(unittest.TestCase):

    def test_the_policy_chosen_audit_is_labelled_by_its_stage_not_a_bare_action_name(self):
        """Every policy alive today (B1..B6, Sentinel, C4, C8, NC1) fires its ONE
        audit at the exact same structural point -- right after ag.run_task, before
        this task is finalised -- regardless of which carrier its ACTION names.
        Recording that under the bare action string (the pre-25a behaviour) hides
        that fact; recording it under "commit:<carrier>" states it.

        Thesis claim (vi): "audit cua chinh sach cu van chay o diem commit".
        """
        _, _, r = _run(policy_name="B1 audit-at-commit", budget=50.0)
        ran = [tr for tr in r.traces if tr.action is not None]
        self.assertTrue(ran, "bad fixture: B1 never got to audit")
        for tr in ran:
            self.assertIn("commit:commit", tr.audit_seconds,
                         f"task {tr.t}: action {tr.action!r} did not land under a "
                         f"commit:<carrier> key, got {sorted(tr.audit_seconds)}")
            self.assertGreater(tr.audit_seconds["commit:commit"], 0.0)

    def test_a_carrier_targeting_policy_still_labels_its_audit_commit_not_insertion(self):
        """B3 audit-on-insertion NAMES insertion, but 25a does not move WHEN its
        audit executes -- only 25b does, and only after Task 22. So even B3's
        audit -- which targets the "memory" carrier -- must still be labelled by
        where it REALLY runs today: the commit-structural point, not "insertion:
        memory".

        Thesis claim (vi): "ten chinh sach khong phai giai doan thuc thi".
        """
        _, _, r = _run(policy_name="B3 audit-on-insertion", budget=50.0)
        ran = [tr for tr in r.traces if tr.action is not None]
        self.assertTrue(ran, "bad fixture: B3 never got to audit")
        self.assertEqual({tr.action for tr in ran}, {"memory"},
                         "bad fixture: B3 is supposed to always target memory")
        for tr in ran:
            self.assertIn("commit:memory", tr.audit_seconds,
                         f"task {tr.t}: B3's audit was not labelled under the "
                         f"commit stage: {sorted(tr.audit_seconds)}")


class ProbesAtTheOtherThreeStages(unittest.TestCase):

    def test_insertion_gets_real_seconds_even_though_no_policy_ever_chooses_it(self):
        """Insertion never fires as a POLICY decision under 25a (no signature
        change to Policy.choose), yet Task 22 needs a real, non-fabricated number
        for it once a real store exists after M3. The runner must supply that
        itself, as a probe: real det.score work, really timed.

        Thesis claim (vi): "insertion co so do that, khong cho den 25b".
        """
        _, _, r = _run(policy_name="B1 audit-at-commit", budget=0.0, h=8)
        hits = [(tr.t, k, v) for tr in r.traces
               for k, v in tr.audit_seconds.items() if k.startswith("insertion:")]
        self.assertTrue(hits, "no insertion probe ever recorded a second")
        for t, k, v in hits:
            self.assertGreater(v, 0.0, f"task {t} {k} is not a measurement")

    def test_retrieval_gets_real_seconds_even_though_no_policy_ever_chooses_it(self):
        """Same claim as insertion, for the retrieval marker.

        Thesis claim (vi): "retrieval co so do that, khong cho den 25b".
        """
        _, _, r = _run(policy_name="B1 audit-at-commit", budget=0.0, h=8)
        hits = [(tr.t, k, v) for tr in r.traces
               for k, v in tr.audit_seconds.items() if k.startswith("retrieval:")]
        self.assertTrue(hits, "no retrieval probe ever recorded a second")
        for t, k, v in hits:
            self.assertGreater(v, 0.0, f"task {t} {k} is not a measurement")

    def test_delegation_gets_real_seconds_when_a_skill_is_induced(self):
        """delegation ("truoc khi skill duoc rut") maps onto MockAgent's skill-
        induction step, the only place a skill item is written -- the closest this
        black-box agent boundary lets the runner get to "before".

        Thesis claim (vi): "delegation gan voi buoc rut skill, khong phai commit".
        """
        found = False
        for seed in range(1, 8):
            _, _, r = _run(policy_name="B1 audit-at-commit", budget=0.0, h=8, seed=seed)
            hits = [(tr.t, v) for tr in r.traces
                   for k, v in tr.audit_seconds.items() if k == "delegation:skill"]
            if hits:
                found = True
                for t, v in hits:
                    self.assertGreater(v, 0.0, f"task {t} delegation:skill is not a measurement")
                break
        self.assertTrue(found, "no seed in range induced a skill item to probe")


class NoFabricatedZeros(unittest.TestCase):

    def test_a_budget_exhausted_task_records_no_commit_key_at_all(self):
        """N3, extended to the stage axis: once B1's budget is gone, no COMMIT
        audit ran, so no "commit:*" key may appear -- even though insertion and
        retrieval probes, which are not budget-gated, may still be present on the
        very same task.

        Thesis claim (vi): "khong gan tay 0 giay cho tang commit khi het ngan sach".
        """
        _, _, r = _run(policy_name="B1 audit-at-commit", budget=4.1, h=8)
        idle = [tr for tr in r.traces if tr.action is None]
        self.assertTrue(idle, "bad fixture: budget 4.1 should exhaust after one commit audit")
        for tr in idle:
            self.assertFalse(any(k.startswith("commit:") for k in tr.audit_seconds),
                             f"task {tr.t}: no policy audit ran (action=None) but "
                             f"audit_seconds carries a commit key: {tr.audit_seconds}")


class ObserverInvariant(unittest.TestCase):
    """25a is an OBSERVATION layer: adding it must not move a single measured
    number. These are the structural guards, independent of the experiment.py
    md5 comparison run separately."""

    def test_repeating_the_same_seed_gives_identical_harm_solved_and_spent(self):
        """If wall-clock noise from the new probes ever reached a decision, two
        runs of the SAME seed would disagree -- real time never repeats exactly.

        Thesis claim (vi): "tang quan sat khong lam doi so do".
        """
        results = []
        for _ in range(3):
            _, _, r = _run(policy_name="Sentinel", budget=17.95, h=8, seed=5)
            results.append((r.harm, r.solved, r.marker, r.spent, r.detected_at,
                            r.quarantined, r.true_quarantine, r.false_quarantine,
                            r.t_lost))
        self.assertEqual(len(set(results)), 1,
                         f"non-deterministic across identical-seed runs: {results}")

    def test_faking_the_clock_does_not_change_harm_or_any_recorded_item_id(self):
        """A stronger version of the same guard: force time.perf_counter() to
        return a weird, non-monotonic sequence and confirm nothing that decides
        harm, or any hashed item_id, is built from it.

        Thesis claim (vi): "gio dong ho khong duoc ro ri vao seed hay item_id".
        """
        wf = _wf(8)
        ps = build.plan_poison(wf, "memory", 2, random.Random(1))

        def make_run():
            return runner.run_once(
                wf, ps, P.make_policy("Sentinel", 17.95, 1, "mid"),
                detector.Detector.from_setting("mid"), agent.MockAgent(), seed=5)

        real = make_run()

        counter = iter(float(x) for x in range(10**6, 0, -1))  # decreasing, weird
        with mock.patch("runner.time.perf_counter", lambda: next(counter)):
            faked = make_run()

        self.assertEqual(real.harm, faked.harm)
        self.assertEqual(real.solved, faked.solved)
        self.assertEqual(real.spent, faked.spent)
        real_ids = [w["item_id"] for tr in real.traces for w in tr.writes]
        faked_ids = [w["item_id"] for tr in faked.traces for w in tr.writes]
        self.assertEqual(real_ids, faked_ids)


if __name__ == "__main__":
    unittest.main()
