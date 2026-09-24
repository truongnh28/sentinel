"""GATE 1 -- a game run gives each workflow its OWN agent stream (README #20).

Spec: docs/preregistration/TIEN-DANG-KY-sua-seed-agent.md.

MockAgent draws from seed_of(seed, t).  The runner used to hand it the raw run
seed, so task t of every workflow in the corpus received the same draw and a
seed was one dice roll shared by all of them.  Pinned here at the call site,
where the bug was, and on the outcome it produced.
"""
from __future__ import annotations
import random
import unittest

import agent, build, detector, experiment, runner
import policies as P
from core import agent_seed


class _Recording(agent.MockAgent):
    def __init__(self):
        super().__init__()
        self.seen = []

    def run_task(self, t, task, store, seed, marker):
        self.seen.append((task.task_id.rsplit("-t", 1)[0], t, seed))
        return super().run_task(t, task, store, seed, marker)


class EachWorkflowGetsItsOwnStream(unittest.TestCase):

    def test_two_workflows_under_one_seed_hand_the_agent_different_seeds(self):
        wfs = experiment.make_corpus(2, 4, seed=2026)
        ag, det = _Recording(), detector.Detector.from_setting("mid")
        for wf in wfs:
            pol = P.make_policy("B1 audit-at-commit", 1.0, 0, "mid")
            runner.run_once(wf, None, pol, det, ag, 1, do_inject=False,
                            record_traces=False)
        by_wf = {}
        for wf_id, t, s in ag.seen:
            by_wf.setdefault(wf_id, set()).add(s)
        self.assertEqual(len(by_wf), 2)
        a, b = by_wf.values()
        self.assertFalse(a & b, "two workflows shared an agent seed: README #20")

    def test_the_stream_is_stable_and_still_varies_with_the_seed(self):
        self.assertEqual(agent_seed("wf-000", 1), agent_seed("wf-000", 1))
        self.assertNotEqual(agent_seed("wf-000", 1), agent_seed("wf-000", 2))
        self.assertNotEqual(agent_seed("wf-000", 1), agent_seed("wf-001", 1))

    def test_solve_outcomes_are_no_longer_identical_across_the_corpus(self):
        """The symptom, not the mechanism: under the old seeding every workflow's
        task-t `solved` coin was the same coin."""
        wfs = experiment.make_corpus(30, 8, seed=2026)
        ag = agent.MockAgent()
        from core import CarrierStore
        cols = []
        for wf in wfs:
            st = CarrierStore()
            cols.append(tuple(ag.run_task(t, task, st, seed=agent_seed(wf.wf_id, 1),
                                          marker="x").solved
                              for t, task in enumerate(wf.tasks)))
        self.assertGreater(len(set(cols)), 1)


if __name__ == "__main__":
    unittest.main()
