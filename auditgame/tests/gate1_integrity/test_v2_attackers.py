"""GATE 1 -- v2 attacker class: 18 rules, 7 held out, behaviour-level hygiene, full menu."""
import random
import unittest

import attackers_v2 as A
import build
from core import CARRIERS, seed_of


class TestAttackersV2(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(A.SCRIPTED), 18)
        self.assertEqual(len(A.held_out()), 7)
        self.assertEqual(set(A.held_out()) | set(A.development()), set(A.SCRIPTED))
        self.assertFalse(set(A.held_out()) & set(A.development()))
        self.assertEqual(len(A.br_attacks()), 16)

    def test_plan_respects_delta(self):
        wf = build.make_workflow("wfa", "repo-00", 14, random.Random(seed_of("a", 1)))
        for a in list(A.SCRIPTED.values()) + A.br_attacks():
            for d in (0, 2, 4, 8):
                got = a.plan(wf, d)
                if got is not None:
                    self.assertEqual(got[0].sigma - got[0].iota, d)
                    self.assertIn(got[1], ("write", "ingress"))

    def test_by_name(self):
        for n in list(A.SCRIPTED) + [a.name for a in A.br_attacks()]:
            self.assertEqual(A.by_name(n).name, n)

    def test_behaviour_keys_ignore_the_channel(self):
        """D7: in the carrier world write and ingress land in the same store."""
        a, b = A.SCRIPTED["memory-last-write-e0.6"], A.SCRIPTED["memory-last-ingress-e0.6"]
        self.assertEqual(A.behavior_keys(a), A.behavior_keys(b))
        self.assertEqual(len(A.behavior_keys(A.SCRIPTED["uniform-mid-write-e0.6"])), len(CARRIERS))

    def test_tuning_never_shows_a_held_out_behaviour(self):
        """D18: no tuning column can realise a held-out attacker's (k, iota rule, eps) on ANY
        workflow -- names are not enough once the channel is inert."""
        held = set().union(*(A.behavior_keys(A.SCRIPTED[n]) for n in A.held_out()))
        tune = A.tuning_attack_names()
        for n in tune:
            self.assertFalse(A.behavior_keys(A.by_name(n)) & held, n)
        self.assertFalse(set(A.held_out()) & set(tune))
        carriers = {k for n in tune for k, _, _ in A.behavior_keys(A.by_name(n))}
        self.assertEqual(carriers, set(CARRIERS))           # every carrier is still defended

    def test_placements_are_the_full_menu(self):
        wf = build.make_workflow("wfm", "repo-00", 12, random.Random(seed_of("m", 2)))
        for d in (0, 2, 4):
            menu = A.placements(wf, d)
            self.assertTrue(all(ps.sigma - ps.iota == d for ps in menu))
            for k in CARRIERS:
                self.assertEqual(sum(1 for ps in menu if ps.carrier == k),
                                 len(build.plan_poison_all(wf, k, d)))


if __name__ == "__main__":
    unittest.main()
