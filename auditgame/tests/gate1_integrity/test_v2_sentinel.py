"""GATE 1 -- Sentinel-A1: line 1 regime, line 5 mixture draw, ablations as declared."""
import unittest

import carrier_runner as R
import draft_setup as D
import sentinel as S

CELL4 = {"robust": {"L-RO-c3-p1-d3": 0.5, "L-BT-0.5-f1": 0.5}, "nominal": {"L-SW-uniform": 1.0},
         "pure": "L-RO-c3-p1-d3", "value": 0.0, "fq_pct": 0.0, "cap_ok": True}
CELL_ALL = {"robust": {"L-SW-commit": 1.0}, "nominal": {"L-SW-commit": 1.0},
            "pure": "L-SW-commit", "value": 0.0, "fq_pct": 0.0, "cap_ok": True}
TUNED = {"betas": dict(D.BETA_WORLD),
         "rho": {"0.25": {"tau5": 0.3, "eta_q": 0.1,
                          "mix": {"mid|4": CELL4, "mid|all": CELL_ALL}}}}


def mk(name, seed, **kw):
    return S.make_policy(name, budget=D.budget_b1(10), kappa=D.TARGET_KAPPA_DRAFT, H=10,
                         rng_seed=seed, setting="mid", tuned=TUNED, rho_patch=0.25, delta=4, **kw)


class TestSentinelA1(unittest.TestCase):
    def test_draws_both_members(self):
        self.assertEqual({mk("Sentinel-A1", s).member_name for s in range(40)},
                         {"L-RO-c3-p1-d3", "L-BT-0.5-f1"})

    def test_line1_uses_the_regime(self):
        self.assertEqual({mk("A1 -regime estimate", s).member_name for s in range(10)}, {"L-SW-commit"})

    def test_ablation_members(self):
        pure = [mk("A1 -randomization", s) for s in range(10)]
        self.assertEqual({p.member_name for p in pure}, {"L-RO-c3-p1-d3"})
        self.assertEqual({p.member.phase for p in pure}, {pure[0].member.phase})   # one schedule
        self.assertEqual(mk("A1 -transition uncertainty", 3).member_name, "L-SW-uniform")
        self.assertEqual(mk("A1 -benign-drift", 3).member.betas, {})
        self.assertTrue(mk("A1 -alarm memory", 3).member.stateless)

    def test_stateless_forgets(self):
        pol = mk("A1 -alarm memory", 3)
        pol.observe(0, R.Observation("memory", 3, True, 0.95, 4))
        p1 = pol.member.belief.p_attack()
        pol.observe(1, None)
        self.assertNotAlmostEqual(p1, pol.member.belief.p_attack())

    def test_line8_threshold_comes_from_the_tuned_block(self):
        self.assertAlmostEqual(mk("Sentinel-A1", 1).eta_q, 0.1)
        self.assertAlmostEqual(mk("Sentinel-A1", 1, eta_q=0.0).eta_q, 0.0)       # SS11 sweep
        self.assertAlmostEqual(mk("Sentinel-A1", 1).member.eta_q, 0.1)

    def test_budget_is_the_members(self):
        pol = mk("Sentinel-A1", 1)
        pol.charge(3.0)
        self.assertEqual(pol.spent, 3.0)
        self.assertEqual(pol.member.spent, 3.0)

    def test_registry(self):
        for n in ["B1 audit-at-commit", "Sentinel-A1", "A1 -regime estimate", S.CONTROL]:
            self.assertIn(n, S.REGISTRY)
        self.assertEqual(len(S.REGISTRY), 6 + 6 + 1)

    def test_cfg_for_nearest_rho(self):
        self.assertIs(S.cfg_for(TUNED, 1.0), TUNED["rho"]["0.25"])

    def test_library_names_take_an_eta_override(self):
        self.assertAlmostEqual(mk("L-SW-uniform", 1, eta_q=0.02).eta_q, 0.02)


if __name__ == "__main__":
    unittest.main()
