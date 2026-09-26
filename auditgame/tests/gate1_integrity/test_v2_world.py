"""GATE 1 -- v2 world: the agent reproduces MockAgent; drift is a matched, TRANSIENT event."""
import random
import statistics
import unittest

import build
import detector
import world_v2 as W
from agent import MockAgent
from analysis.discriminator import auc_with_ci
from core import CarrierStore, Item, seed_of


def _wfs(n=20):
    return [build.make_workflow(f"wfw-{i:02d}", "repo-00", 10,
                                random.Random(seed_of("w2", i))) for i in range(n)]


def _drift_item(created_at=0):
    return Item(carrier="memory", topic="auth", content="x", created_at=created_at,
                provenance="repo/docs/conventions.md", poisoned=False)


class TestWorldV2(unittest.TestCase):
    def test_no_gates_no_drift_reproduce_mock_agent(self):
        for wf in _wfs():
            a, b = MockAgent(), W.StagedMockAgent()
            sa, sb = CarrierStore(), CarrierStore()
            for t, task in enumerate(wf.tasks):
                oa = a.run_task(t, task, sa, seed=1, marker="m")
                ob = b.run_task(t, task, sb, seed=1, marker="m")
                self.assertEqual([w.item_id for w in oa.writes], [w.item_id for w in ob.writes])
                self.assertEqual((oa.patch_has_marker, oa.solved), (ob.patch_has_marker, ob.solved))

    def test_drift_rate(self):
        ag = W.StagedMockAgent(drift_rates={"memory": 0.5})
        n = 0
        for wf in _wfs():
            st = CarrierStore()
            for t, task in enumerate(wf.tasks):
                ag.run_task(t, task, st, seed=1, marker="m", wf_topics=[x.topic for x in wf.tasks])
            n += len(wf.tasks)
        self.assertGreater(len(ag.drift_ids), 0.35 * n)
        self.assertLess(len(ag.drift_ids), 0.65 * n)

    def test_drift_is_matched_while_fresh_then_clean(self):
        """D6: a drift event scores like poison in the task it happens, like a clean item after."""
        base = detector.Detector.from_setting("mid")
        item = _drift_item(created_at=0)
        det = W.DriftDetector(base, {item.item_id}, match=1.0)
        fresh = statistics.mean(det.score(item, 0, s) for s in range(2000))
        later = statistics.mean(det.score(item, 3, s) for s in range(2000))
        self.assertAlmostEqual(fresh, base.d_prime, delta=0.1)
        self.assertAlmostEqual(later, 0.0, delta=0.1)
        persistent = W.DriftDetector(base, {item.item_id}, match=1.0, drift_visible=None)
        self.assertAlmostEqual(statistics.mean(persistent.score(item, 3, s) for s in range(2000)),
                               base.d_prime, delta=0.1)
        unmatched = W.DriftDetector(base, {item.item_id}, match=0.0)
        self.assertAlmostEqual(statistics.mean(unmatched.score(item, 0, s) for s in range(2000)),
                               0.0, delta=0.1)

    def test_payload_stays_visible(self):
        base = detector.Detector.from_setting("mid")
        it = Item(carrier="memory", topic="auth", content="p", created_at=0,
                  provenance="repo/docs/conventions.md", poisoned=True)
        det = W.DriftDetector(base, set())
        self.assertAlmostEqual(statistics.mean(det.score(it, 7, s) for s in range(2000)),
                               base.d_prime, delta=0.1)

    def test_every_inspection_is_an_independent_draw(self):
        """D16: re-inspecting the same item gives a new score."""
        det = W.DriftDetector(detector.Detector.from_setting("mid"), set())
        it = _drift_item()
        self.assertGreater(len({round(det.score(it, t, 1), 9) for t in range(20)}), 15)

    def test_insertion_probe_sees_fresh_drift_as_matched(self):
        base = detector.Detector.from_setting("mid")
        ag = W.StagedMockAgent(drift_rates={"memory": 1.0})
        det = W.DriftDetector(base, ag.drift_ids, match=1.0)
        fired = []

        class Probe(W.OpenGates):
            def __init__(self, t, s):
                self.t, self.s = t, s

            def admit(self, item, stage):
                if item.provenance == "repo/docs/conventions.md":
                    fired.append(det.fires(det.score(item, self.t, self.s)))
                return True

        for i, wf in enumerate(_wfs(30)):
            st, topics = CarrierStore(), [x.topic for x in wf.tasks]
            for t, task in enumerate(wf.tasks):
                ag.run_task(t, task, st, seed=i, marker="m", gates=Probe(t, i), wf_topics=topics)
        self.assertAlmostEqual(sum(fired) / len(fired), base.psi, delta=0.05)

    def test_patch_exposure_follows_provenance(self):
        """D20: delegated patch seen at rho * d'(depth 1), direct at d'(depth)."""
        base = detector.Detector.from_setting("mid")
        det = W.DriftDetector(base, set(), rho_patch=0.25)

        def mean(d, via):
            return statistics.mean(d.score_patch(True, f"t{i}", s, via)
                                   for i in range(40) for s in range(40))

        self.assertAlmostEqual(mean(det, "direct"), base.d_prime, delta=0.1)
        self.assertAlmostEqual(mean(det, "delegated"), 0.25 * base.d_prime, delta=0.1)
        deep = det.at_depth(3)
        self.assertAlmostEqual(mean(deep, "direct"), base.d_prime * 3 ** 0.5, delta=0.1)
        self.assertAlmostEqual(mean(deep, "delegated"), 0.25 * base.d_prime, delta=0.1)

    def test_agent_labels_the_path(self):
        wf = build.make_workflow("wfp", "repo-00", 10, random.Random(seed_of("p", 1)))
        for carrier, want in (("memory", "direct"), ("skill", "delegated")):
            ps = build.plan_poison_all(wf, carrier, 2)[0]
            st = CarrierStore()
            ag = W.StagedMockAgent(adoption_rate=1.0)
            got = set()
            for t, task in enumerate(wf.tasks):
                if t == ps.iota:
                    st.write(build.inject(CarrierStore(), wf, ps))
                o = ag.run_task(t, task, st, seed=1, marker=ps.marker)
                if o.patch_has_marker:
                    got.add(o.patch_via)
            self.assertIn(want, got)

    def test_drift_surface_is_matched_to_payload(self):
        """Draft SS8: a surface discriminator reaches AUC <= 0.56.  Both sides are read at
        the SAME recency (Delta = 2): `recency` is a scored feature, and reading drift at
        min(t + 2, H - 1) -- as the 24/09 version did -- truncates it near the end of a
        workflow and measures the truncation (0.570), not the drift."""
        pois, ben = [], []
        ag = W.StagedMockAgent(drift_rates={"memory": 1.0})
        for i, wf in enumerate(_wfs(60)):
            cands = build.plan_poison_all(wf, "memory", 2)
            if cands:
                it = build.inject(CarrierStore(), wf, cands[0])
                pois.append(it.surface(cands[0].sigma))
            st = CarrierStore()
            topics = [x.topic for x in wf.tasks]
            for t, task in enumerate(wf.tasks):
                o = ag.run_task(t, task, st, seed=i, marker="m", wf_topics=topics)
                if t + 2 <= wf.H - 1:
                    ben += [w.surface(t + 2) for w in o.writes if w.item_id in ag.drift_ids]
        aucs = [auc_with_ci(pois, ben[:len(pois) * 3], seed=s)[0] for s in range(5)]
        self.assertLessEqual(statistics.median(aucs), 0.56)


if __name__ == "__main__":
    unittest.main()
