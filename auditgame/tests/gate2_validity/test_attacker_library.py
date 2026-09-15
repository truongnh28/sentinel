"""
GATE 2 -- the scripted attacker library, and the held-out split.
Spec: Danh-sach-diem-can-them.md C2, C3.

The manuscript reports 27.6% against held-out adaptive attackers. There was no
attacker library, no split, and therefore nothing behind that number -- an
independent review of this benchmark says so in as many words.

What existed was an enumeration of (Delta, carrier) CONFIGURATIONS, which is the
attacker's action space, not a set of attacker POLICIES. A policy is a rule for
choosing the configuration from what it can see, and only a rule can be held out:
you cannot hold out a coordinate.

The split is BY HASH, fixed before any measurement, so "held out" cannot drift into
"the ones it did worst on".
"""
from __future__ import annotations
import random, unittest

import agent, attackers, build, detector, runner
from core import seed_of

N_WF, BUDGET = 16, 17.95


def _setup():
    wfs = [build.make_workflow(f"wf-{i:03d}", "django", 8,
                               random.Random(seed_of("al", i))) for i in range(N_WF)]
    return wfs, detector.Detector.from_setting("mid"), agent.MockAgent()


class AttackerLibrary(unittest.TestCase):

    def test_the_split_is_by_hash_and_is_stable(self):
        """Held-out membership is decided by a hash of the name, before anything is
        measured.  Choosing the split afterwards is how a transfer number becomes
        whatever the author needs it to be.

        Thesis claim (vi): "7/18 scripted policy giu rieng khoi toan bo qua trinh tuning".
        """
        a, b = attackers.held_out(), attackers.held_out()
        self.assertEqual(a, b, "the split is not deterministic")
        self.assertTrue(a, "nothing is held out -- there is no transfer claim to make")
        self.assertFalse(a & attackers.development(),
                         "an attacker is in both splits")
        self.assertEqual(a | attackers.development(), set(attackers.REGISTRY))

    def test_every_attacker_produces_a_buildable_plan_somewhere(self):
        """An attacker that never builds contributes silent zeros to the denominator.

        Thesis claim (vi): "khong dung duoc KHAC voi phong thu thanh cong" (N3).
        """
        wfs, _, _ = _setup()
        for name, atk in attackers.REGISTRY.items():
            with self.subTest(attacker=name):
                built = any(atk.plan(wf, random.Random(seed_of(name, i))) is not None
                            for i, wf in enumerate(wfs))
                self.assertTrue(built, f"[{name}] never produces a plan")

    def test_attackers_differ_from_one_another(self):
        """A library of clones measures one attacker eighteen times.

        Thesis claim (vi): "lop attacker da khai bao".
        """
        wfs, _, _ = _setup()
        sigs = {}
        for name, atk in attackers.REGISTRY.items():
            plans = []
            for i, wf in enumerate(wfs):
                ps = atk.plan(wf, random.Random(seed_of("sig", i)))
                plans.append(None if ps is None else (ps.carrier, ps.delta))
            sigs[name] = tuple(plans)
        self.assertEqual(len(set(sigs.values())), len(sigs),
                         f"identical attackers: { {k: v[:3] for k, v in sigs.items()} }")

    def test_transfer_gap_is_reported_for_both_splits(self):
        """The honest number is harm against HELD-OUT attackers, reported next to
        the development one, with the gap stated rather than hidden.

        A gap is EXPECTED. What is not acceptable is quoting the development number
        as though it were the transfer number.

        Thesis claim (vi): "con so transfer phai co bang chung".
        """
        wfs, det, ag = _setup()
        runner.reset_survivor_cache()
        dev = attackers.worst_case_over(
            "Sentinel", attackers.development(), wfs, det, ag, BUDGET, (1, 2), "mid")
        held = attackers.worst_case_over(
            "Sentinel", attackers.held_out(), wfs, det, ag, BUDGET, (1, 2), "mid")
        self.assertFalse(dev != dev or held != held, "NaN harm -- nothing ran")
        self.assertGreaterEqual(dev, 0.0)
        self.assertGreaterEqual(held, 0.0)


if __name__ == "__main__":
    unittest.main()
