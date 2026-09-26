"""D35 tuning rules (tools/tune_d35.py).
Run from auditgame/: ../.venv/bin/python -m unittest tests.tools.test_d35_tune -v"""
import unittest

import sentinel as S
from tools.tune_d35 import cell_d35, choose_fixed, choose_p


def cols(v4, v8):
    return {"a@4": v4, "b@4": v4 / 2, "a@8": v8, "b@8": v8 / 2, "a@0": 0.99}


class TestChooseP(unittest.TestCase):
    def test_lowest_worst_case_within_the_fq_target(self):
        cands = {0.25: (cols(0.30, 0.2), 14.0), 0.5: (cols(0.40, 0.2), 7.0),
                 0.75: (cols(0.60, 0.2), 3.0), 1.0: (cols(0.90, 0.9), 0.0)}
        got = choose_p(cands, 4, target_fq=8.0)
        self.assertEqual(got["p"], 0.5)
        self.assertAlmostEqual(got["dev_worst"], 0.40)
        self.assertEqual(got["target_fq"], 8.0)

    def test_reads_only_the_columns_of_its_delta(self):
        cands = {0.5: (cols(0.40, 0.10), 7.0), 0.75: (cols(0.35, 0.50), 3.0)}
        self.assertEqual(choose_p(cands, 4, 8.0)["p"], 0.75)
        self.assertEqual(choose_p(cands, 8, 8.0)["p"], 0.5)

    def test_ties_at_four_decimals_go_to_lower_fq_then_smaller_p(self):
        cands = {0.5: (cols(0.40001, 0.2), 7.0), 0.6: (cols(0.40002, 0.2), 5.0),
                 0.7: (cols(0.40, 0.2), 5.0)}
        self.assertEqual(choose_p(cands, 4, 8.0)["p"], 0.6)

    def test_p_one_is_always_feasible(self):
        cands = {0.5: (cols(0.1, 0.1), 9.0), 1.0: (cols(0.9, 0.9), 0.0)}
        self.assertEqual(choose_p(cands, 4, target_fq=2.0)["p"], 1.0)


class TestChooseFixed(unittest.TestCase):
    def test_lowest_worst_case_within_the_cap(self):
        cands = {"FI-a": (cols(0.2, 0.2), 12.0), "FI-b": (cols(0.3, 0.3), 6.0),
                 "FI-c": (cols(0.5, 0.1), 2.0)}
        got = choose_fixed(cands, 4, cap=10.0)
        self.assertEqual(got["member"], "FI-b")
        self.assertTrue(got["cap_ok"])

    def test_ties_go_to_lower_fq_then_name(self):
        cands = {"FI-b": (cols(0.3, 0.3), 6.0), "FI-a": (cols(0.3, 0.3), 6.0),
                 "FI-c": (cols(0.3, 0.3), 4.0)}
        self.assertEqual(choose_fixed(cands, 4, 10.0)["member"], "FI-c")
        del cands["FI-c"]
        self.assertEqual(choose_fixed(cands, 4, 10.0)["member"], "FI-a")

    def test_no_member_within_the_cap_is_flagged(self):
        cands = {"FI-a": (cols(0.2, 0.2), 12.0), "FI-b": (cols(0.3, 0.3), 11.0)}
        got = choose_fixed(cands, 4, 10.0)
        self.assertEqual(got["member"], "FI-a")
        self.assertFalse(got["cap_ok"])


class TestCellOnDev(unittest.TestCase):
    """One small dev job per kind: it runs, is shaped like select_mixture.member_cell."""
    def test_b2p_one_quarantines_nothing(self):
        name, _s, _k, rho, eq, c, fq = cell_d35(("B2p:1", "mid", "nominal", 0.0, (4,), (1,),
                                                 S.load_tuned()))
        self.assertEqual((name, rho, eq), ("B2p:1", 0.0, None))
        self.assertEqual(fq, 0.0)
        self.assertTrue(c and all(k.endswith("@4") for k in c))

    def test_fixed_member_runs(self):
        _n, _s, _k, _r, _e, c, fq = cell_d35(("FI-alt-m2", "mid", "nominal", 0.0, (4,), (1,),
                                              S.load_tuned()))
        self.assertTrue(c)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in c.values()))
        self.assertGreater(fq, 0.0)


if __name__ == "__main__":
    unittest.main()
