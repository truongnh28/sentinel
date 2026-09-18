"""
test_fdetect_g4.py -- Gate 2 validity tests for G4 judge-human agreement evaluation.
Spec: 261-Master-Proposal-Analysis/TIEN-DANG-KY-m-x-va-F-detect-v2.md Section 6.
"""
import inspect
import unittest

import fdetect_g4


class TestFdetectG4(unittest.TestCase):
    def test_n_g4_and_theta_constants(self):
        self.assertEqual(fdetect_g4.N_G4, 38)
        self.assertEqual(fdetect_g4.THETA_G4, 0.75)
        self.assertEqual(fdetect_g4.EXPECTED_AGREEMENT, 0.90)

    def test_clopper_pearson_known_pre_registered_points(self):
        # n = 15, 15/15 => CI95 lower bound is ~0.7820
        lo15, hi15 = fdetect_g4.clopper_pearson(15, 15)
        self.assertAlmostEqual(lo15, 0.7820, places=3)
        self.assertEqual(hi15, 1.0)

        # n = 36, k = 32 (round(0.9 * 36) = 32, real rate 0.889) => lo ~ 0.7394 < 0.75
        lo36, _ = fdetect_g4.clopper_pearson(32, 36)
        self.assertAlmostEqual(lo36, 0.7394, places=3)
        self.assertLess(lo36, 0.75)

        # n = 37, k = 33 => lo ~ 0.7458 < 0.75
        lo37, _ = fdetect_g4.clopper_pearson(33, 37)
        self.assertAlmostEqual(lo37, 0.7458, places=3)
        self.assertLess(lo37, 0.75)

        # n = 38, k = 35 (round(0.9 * 38) = 34 or 35)
        lo38_35, _ = fdetect_g4.clopper_pearson(35, 38)
        self.assertGreaterEqual(lo38_35, 0.75)

    def test_evaluate_g4_passes_at_or_above_n38_with_high_agreement(self):
        # 38 instances, 36 agreements
        h = [1] * 38
        j = [1] * 36 + [0] * 2
        res = fdetect_g4.evaluate_g4(h, j)
        self.assertTrue(res["passes"])
        self.assertEqual(res["status"], "PASS")
        self.assertNotIn("limitation", res)

    def test_evaluate_g4_discloses_limitation_when_n_below_38(self):
        # 15 instances, 15 agreements
        h = [1] * 15
        j = [1] * 15
        res = fdetect_g4.evaluate_g4(h, j)
        self.assertFalse(res["passes"])
        self.assertEqual(res["status"], "FAIL")
        self.assertIn("limitation", res)
        self.assertIn("pre-registered floor", res["limitation"])

    def test_no_auc_bridge_in_g4(self):
        src = inspect.getsource(fdetect_g4)
        body = "\n".join(l for l in src.splitlines()
                         if "REJECT" not in l and "never" not in l.lower())
        self.assertNotIn("2 ** 0.5", body)
        self.assertNotIn("sqrt(2)", body)
        self.assertNotIn("auc", body.lower().replace("because", ""))


if __name__ == "__main__":
    unittest.main()
