"""D35 addendum systems (addendum_d35.py).
Run from auditgame/: ../.venv/bin/python -m unittest tests.tools.test_d35_policies -v"""
import unittest

import addendum_d35 as X
import carrier_policies as CP
import draft_setup as D
import sentinel as S

TUNED = S.load_tuned()
K = D.TARGET_KAPPA_DRAFT


def mk(name, *, seed=7, rho=0.0, delta=4, d35=None, H=14):
    return X.make_policy_d35(name, budget=D.budget_b1(H), kappa=K, H=H, rng_seed=seed,
                             setting="mid", tuned=TUNED, d35=d35 or {}, rho_patch=rho,
                             delta=delta)


class TestB2CommitProb(unittest.TestCase):
    def test_p1_always_commits_p0_never(self):
        one, zero = mk("B2p:1"), mk("B2p:0")
        for t in range(200):
            self.assertEqual(one.act(t), (D.COMMIT, D.MAX_DEPTH))
            k, d = zero.act(t)
            self.assertIn(k, D.SWEEP_CARRIERS)
            self.assertEqual(d, D.MAX_DEPTH)

    def test_commit_share_tracks_p(self):
        pol = mk("B2p:0.6")
        share = sum(pol.act(t)[0] == D.COMMIT for t in range(4000)) / 4000
        self.assertAlmostEqual(share, 0.6, delta=0.03)

    def test_sweeps_cover_all_three_carriers(self):
        pol = mk("B2p:0.25")
        seen = {pol.act(t)[0] for t in range(400)} - {D.COMMIT}
        self.assertEqual(seen, set(D.SWEEP_CARRIERS))

    def test_quarantines_every_firing_item(self):
        pol = mk("B2p:0.5")
        self.assertEqual(pol.remove(0, "memory", [("a", 1.0), ("b", 2.0)], None, []), ["a", "b"])

    def test_the_tuned_arm_reads_p_per_rho_and_delta(self):
        d35 = {"b2_fq": {"0.25": {"4": {"p": 0.7}, "8": {"p": 0.55}}}}
        self.assertEqual(mk(X.B2_FQ, rho=0.25, delta=4, d35=d35).p, 0.7)
        self.assertEqual(mk(X.B2_FQ, rho=0.25, delta=8, d35=d35).p, 0.55)

    def test_p_grid(self):
        self.assertEqual(len(X.P_GRID), 16)
        self.assertEqual(X.P_GRID[0], 0.25)
        self.assertEqual(X.P_GRID[-1], 1.0)
        self.assertIn(0.6, X.P_GRID)


class TestFixedSchedules(unittest.TestCase):
    def test_family_has_eleven_members(self):
        self.assertEqual(len(X.FIXED_LIBRARY), 11)
        self.assertIn("FI-c4-p1-d3", X.FIXED_LIBRARY)
        self.assertIn("FI-alt-m4", X.FIXED_LIBRARY)

    def test_rotation_phase_is_zero_for_every_seed(self):
        a, b = mk("FI-c4-p1-d3", seed=1), mk("FI-c4-p1-d3", seed=99)
        self.assertEqual([a.act(t) for t in range(12)], [b.act(t) for t in range(12)])
        self.assertEqual([a.act(t)[0] for t in range(4)], list(D.TARGETS))

    def test_alternation_m2(self):
        pol = mk("FI-alt-m2")
        self.assertEqual([pol.act(t)[0] for t in range(8)],
                         ["memory", "commit", "queue", "commit", "skill", "commit", "memory", "commit"])
        self.assertTrue(all(pol.act(t)[1] == D.MAX_DEPTH for t in range(8)))

    def test_alternation_m3(self):
        pol = mk("FI-alt-m3")
        self.assertEqual([pol.act(t)[0] for t in range(6)],
                         ["memory", "queue", "commit", "skill", "memory", "commit"])

    def test_fixed_members_use_the_rhos_line8_threshold(self):
        self.assertEqual(mk("FI-alt-m2", rho=1.0).eta_q, S.cfg_for(TUNED, 1.0)["eta_q"])
        self.assertEqual(mk("FI-c3-p2-d2", rho=0.0).eta_q, S.cfg_for(TUNED, 0.0)["eta_q"])

    def test_the_tuned_arm_reads_its_member(self):
        d35 = {"fixed": {"0": {"4": {"member": "FI-alt-m3"}, "8": {"member": "FI-c4-p2-d3"}}}}
        self.assertIsInstance(mk(X.FIXED, delta=4, d35=d35), X.FixedAlternation)
        self.assertIsInstance(mk(X.FIXED, delta=8, d35=d35), X.FixedRotation)


class TestWrongDelta(unittest.TestCase):
    def test_table(self):
        self.assertEqual(X.DHAT, {"A1 dhat-swap": {4: 8, 8: 4},
                                  "A1 dhat-down1": {4: 2, 8: 4},
                                  "A1 dhat-down2": {4: 1, 8: 2}})

    def test_plays_a_member_of_the_told_deltas_mixture(self):
        robust = S.cfg_for(TUNED, 0.0)["mix"]["mid|8"]["robust"]
        for seed in range(1, 30):
            self.assertIn(mk("A1 dhat-swap", seed=seed, delta=4).member_name, robust)

    def test_same_draw_as_sentinel_told_the_same_delta(self):
        for seed in range(1, 30):
            self.assertEqual(mk("A1 dhat-down1", seed=seed, delta=8).member_name,
                             mk("Sentinel-A1", seed=seed, delta=4).member_name)

    def test_undefined_off_the_headline(self):
        with self.assertRaises(ValueError):
            mk("A1 dhat-swap", delta=2)


class TestFallsThrough(unittest.TestCase):
    def test_study_systems_resolve_as_before(self):
        self.assertIsInstance(mk("B1 audit-at-commit"), CP.B1AuditAtCommit)
        self.assertIsInstance(mk("Sentinel-A1"), S.SentinelA1)

    def test_the_frozen_registries_are_untouched(self):
        self.assertEqual(len(S.REGISTRY), 13)
        self.assertEqual(len(CP.LIBRARY), 28)
        self.assertFalse(set(X.ARMS) & set(S.REGISTRY))
        self.assertEqual(X.ARMS, ["A1 dhat-swap", "A1 dhat-down1", "A1 dhat-down2",
                                  "B2 FQ-matched", "A1 fixed interleave"])


if __name__ == "__main__":
    unittest.main()
