"""
GATE 1 -- trace and replay (I9).  Spec: ../pipelines/SPEC-P1b-Trace.md Part 1.

Right now this is a PROMISE WITH NOTHING HOLDING IT UP: `TaskTrace` is declared in
core.py but NOTHING writes to it, and `runner` returns no traces.
"""
from __future__ import annotations
import random, subprocess, sys, unittest

import agent, build, core, detector, runner
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


class TraceSerialisation(unittest.TestCase):
    """On the real SWE-bench dataset, TaskTrace.topic is a swebench_dataset.Topic
    -- a frozenset subclass, not the plain string the mock dataset uses -- and
    core.dumps must be able to write that trace to disk, or the whole point of
    TaskTrace (replay without re-running the LLM) does not hold for real data.
    """

    def test_a_trace_carrying_a_real_frozenset_topic_serialises(self):
        """isinstance(frozenset(), set) is False, so the old encoder's `isinstance(o,
        (set, tuple))` branch never matched a Topic and core.dumps raised TypeError
        on every real-dataset trace.

        Thesis claim (vi): "chi phi giam hai bac nho replay".
        """
        from swebench_dataset import Topic
        tr = core.TaskTrace(
            t=0, task_id="frozen-topic-x", topic=Topic({"alpha", "beta", "gamma"}),
            before={}, after={}, writes=[], retrieved=[], alarms={},
            patch_has_marker=False, public_ok=True, hidden_ok=True, audit_seconds={})
        core.dumps(tr)   # must not raise TypeError

    def test_frozenset_topic_serialises_byte_identically_across_PYTHONHASHSEED(self):
        """A bare `list(frozenset)` would pass inside one process (hash
        randomisation is fixed per process) while still making the same trace
        serialise to a different byte string on the next run -- so this must be
        checked ACROSS processes, not by calling dumps twice in this one.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        code = (
            "import core\n"
            "from swebench_dataset import Topic\n"
            "topic = Topic({'astropy/modeling/separable.py',\n"
            "               'astropy/utils/introspection.py',\n"
            "               'astropy/wcs/wcs.py', 'beta', 'gamma', 'delta',\n"
            "               'epsilon', 'zeta'})\n"
            "tr = core.TaskTrace(t=0, task_id='frozen-topic-x', topic=topic,\n"
            "                    before={}, after={}, writes=[], retrieved=[],\n"
            "                    alarms={}, patch_has_marker=False, public_ok=True,\n"
            "                    hidden_ok=True, audit_seconds={})\n"
            "print(core.dumps(tr))\n")
        outs = set()
        for h in ("0", "1", "424242"):
            r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                               text=True, env={"PYTHONHASHSEED": h, "PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 0, f"run failed at HASHSEED={h}: {r.stderr[-400:]}")
            outs.add(r.stdout)
        self.assertEqual(len(outs), 1,
                         f"serialised trace changes with PYTHONHASHSEED:\n{chr(10).join(sorted(outs))}")


if __name__ == "__main__":
    unittest.main()
