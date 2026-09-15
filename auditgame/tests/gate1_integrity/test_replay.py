"""
GATE 1 -- trace and replay (I9).  Spec: ../pipelines/SPEC-P1b-Trace.md Part 1.

Right now this is a PROMISE WITH NOTHING HOLDING IT UP: `TaskTrace` is declared in
core.py but NOTHING writes to it, and `runner` returns no traces.
"""
from __future__ import annotations
import random, unittest

import agent, build, detector, runner
import policies as P
from core import seed_of


def _wf():
    return build.make_workflow("wf-000", "django", 6, random.Random(seed_of("rp", 0)))


def _run(carrier="memory"):
    wf = _wf()
    ps = build.plan_poison(wf, carrier, 2, random.Random(1))
    return wf, runner.run_once(
        wf, ps, P.make_policy("Sentinel", 17.95, 1, "mid"),
        detector.Detector.from_setting("mid"), agent.MockAgent(), seed=1)


class TraceRecording(unittest.TestCase):

    def test_run_once_returns_one_trace_per_task(self):
        """With no trace there is no replay, and the cost lever is an empty promise.

        Thesis claim (vi): "chi phi giam hai bac nho replay".
        """
        wf, r = _run()
        self.assertEqual(len(r.traces), len(wf.tasks))

    def test_trace_records_RAW_scores_so_rescanning_psi_phi_is_free(self):
        """SPEC-P1b Part 1: record the RAW score, BEFORE thresholding.  Record it
        after the threshold and rescanning (psi, phi) means RE-RUNNING THE LLM.

        Thesis claim (vi): "chi phi giam hai bac nho replay".
        """
        _, r = _run()
        with_alarms = [t for t in r.traces if t.alarms]
        self.assertTrue(with_alarms, "no trace recorded a raw alarm score")
        for v in with_alarms[0].alarms.values():
            self.assertIsInstance(v, float)

    def test_trace_records_n_c_to_separate_chi_from_item_density(self):
        """chi (the COST spread) and n_c (item DENSITY) are TWO different evasion
        axes.  Without n_c on the trace, "hiding in the crowd" stays a post-hoc
        story instead of a measured variable.

        Thesis claim (vi): "nap trong dam dong" (RQ2).
        """
        _, r = _run("branch")
        last = r.traces[-1]
        self.assertEqual(set(last.n_c), {"memory", "skill", "queue", "branch"})
        self.assertGreater(sum(last.n_c.values()), 0)


if __name__ == "__main__":
    unittest.main()
