"""
GATE 1 -- the observation model (T1 / P2): does the budget buy information?

Spec: docs/preregistration/TIEN-DANG-KY-mo-hinh-quan-sat-MA.md.

Under M0 the runner hands every policy the posterior of all four carriers at
every task, so the budget buys actions and never information -- the reason
tools/measure_c.py found the posterior flat from B = 2 to 200.  MA makes sight a
thing the budget pays for.  These tests pin the three properties that make MA
mean what it says, plus prediction MA2 of the pre-registration, which is a
correctness check rather than a finding.
"""
from __future__ import annotations
import random
import unittest

import agent, build, detector, runner, scoring
import policies as P
from core import CARRIERS, Task, Workflow


def _signals(p_by_carrier):
    return {c: P.CarrierSignal(p=p_by_carrier.get(c, 0.5), n=3) for c in CARRIERS}


class VisibleSignals(unittest.TestCase):

    def test_M0_is_the_identity(self):
        sig = _signals({"memory": 0.9})
        self.assertIs(runner.visible_signals(sig, {}, "M0"), sig)

    def test_an_unaudited_carrier_does_not_move_the_belief(self):
        """The step-2 test of the plan.  Two worlds that differ ONLY in an
        unaudited carrier's posterior must look identical to the policy."""
        a = runner.visible_signals(_signals({"memory": 0.01}), {}, "MA")
        b = runner.visible_signals(_signals({"memory": 0.99}), {}, "MA")
        self.assertEqual(a, b)
        self.assertEqual(a["memory"].p, scoring.PI0,
                         "an unseen carrier must read as NO evidence (pi0), "
                         "not as clean and not as a missing key")

    def test_the_item_count_is_still_visible(self):
        """n is metadata, not a detector reading; hiding it would make MA blind
        to whether a carrier is even populated, which no real harness is."""
        v = runner.visible_signals({c: P.CarrierSignal(p=0.5, n=i) for i, c in
                                    enumerate(CARRIERS)}, {}, "MA")
        self.assertEqual([v[c].n for c in CARRIERS], list(range(len(CARRIERS))))

    def test_what_was_bought_is_what_is_seen(self):
        sig = _signals({"skill": 0.77})
        seen = runner.bought_sight("skill", sig)
        v = runner.visible_signals(_signals({"skill": 0.11}), seen, "MA")
        self.assertEqual(v["skill"].p, 0.77,
                         "MA shows the reading the audit TOOK, not the current one")

    def test_commit_and_quarantine_reveal_no_carrier(self):
        sig = _signals({})
        self.assertEqual(runner.bought_sight("commit", sig), {})
        self.assertEqual(runner.bought_sight(None, sig), {})
        self.assertEqual(runner.bought_sight(P.QUARANTINE_PREFIX + "memory", sig), {})

    def test_an_undeclared_model_is_refused(self):
        with self.assertRaises(ValueError):
            runner.visible_signals(_signals({}), {}, "MX")


def _run(policy, model):
    old = runner.OBSERVATION
    runner.OBSERVATION = model
    try:
        wf = build.make_workflow("wf-obs", "django", 8, random.Random(7))
        ps = build.plan_poison(wf, "memory", 2, random.Random(3))
        return runner.run_once(wf, ps, P.make_policy(policy, 17.95, 1, "mid"),
                               detector.Detector.from_setting("mid"),
                               agent.MockAgent(), seed=1)
    finally:
        runner.OBSERVATION = old


class TheModelOnlyReachesPoliciesThatReadSignals(unittest.TestCase):

    def test_MA2_B1_is_identical_under_both_models(self):
        """Pre-registered MA2.  B1 audits at commit and reads no carrier signal,
        so the observation model must not move it by one digit.  If it does, the
        model has leaked into a path that does not observe -- a bug."""
        a, b = _run("B1 audit-at-commit", "M0"), _run("B1 audit-at-commit", "MA")
        self.assertEqual((a.harm, a.spent), (b.harm, b.spent))

    def test_a_replay_under_MA_re_derives_the_run(self):
        """I9 under MA: replay applies the same model through the same two
        functions, so a run made under MA replays to the same spend."""
        import replay
        old = runner.OBSERVATION
        runner.OBSERVATION = "MA"
        try:
            r = _run("Sentinel", "MA")
            rr = replay.rescore(r.traces, detector.Detector.from_setting("mid"),
                                P.make_policy("Sentinel", 17.95, 1, "mid"))
        finally:
            runner.OBSERVATION = old
        if not rr.valid:
            self.skipTest(f"replay declared this case invalid: {rr.reason}")
        self.assertAlmostEqual(rr.spent, r.spent, places=9)


if __name__ == "__main__":
    unittest.main()
