"""GATE 1 -- the secondary gate world (D29): stage gates across all carriers."""
import random
import unittest

import build
import carrier_runner as R
import detector
import draft_setup as D
import gate_world as G
import world_v2 as W
from core import seed_of


def _perfect(rs):
    ag = W.StagedMockAgent(adoption_rate=1.0)
    return ag, W.DriftDetector(detector.Detector(12.0, 6.0), ag.drift_ids)


def _run(name, carrier="skill", channel="write"):
    for i in range(300):
        wf = build.make_workflow(f"wfg-{i}", "repo-00", 10, random.Random(seed_of("g", i)))
        c = build.plan_poison_all(wf, carrier, 2)
        if c:
            for seed in range(1, 80):
                if R.survives(wf, c[0], seed):
                    return G.run_gate(wf, (c[0], channel), name, _perfect, seed, D.budget_b1(wf.H))
    raise AssertionError("no case")


class TestGateWorld(unittest.TestCase):
    def test_retrieval_gate_stops_any_carrier(self):
        """The gate world's defining property: one retrieval gate sees every carrier at sigma."""
        for carrier in ("memory", "skill", "queue", "branch"):
            self.assertEqual(_run("B4g retrieval", carrier).harm, 0.0, carrier)

    def test_insertion_gate_is_bypassed_by_ingress(self):
        self.assertEqual(_run("B3g insertion", "memory", "write").harm, 0.0)
        self.assertEqual(_run("B3g insertion", "memory", "ingress").harm, 1.0)

    def test_commit_gate_blocks_a_direct_patch(self):
        self.assertEqual(_run("B1g commit", "memory").harm, 0.0)


if __name__ == "__main__":
    unittest.main()
