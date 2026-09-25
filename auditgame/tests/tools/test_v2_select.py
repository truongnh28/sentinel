"""GATE 1 -- v2 tuning: the constrained minimax of SS4's objective (D9, D26).  Needs scipy:
run with ../.venv/bin/python."""
import unittest

from tools.select_mixture import constrained_minimax, reduce_kernels

NAMES = ["a", "b", "c"]
#       column:  x     y
M = {"a": {"x": 1.0, "y": 0.0},
     "b": {"x": 0.0, "y": 1.0},
     "c": {"x": 0.6, "y": 0.6}}


class TestConstrainedMinimax(unittest.TestCase):
    def test_unconstrained_mix_beats_every_pure_policy(self):
        cell = constrained_minimax(M, {n: 0.0 for n in NAMES}, NAMES, ["x", "y"], cap=10.0)
        self.assertAlmostEqual(cell["value"], 0.5, places=6)
        self.assertAlmostEqual(cell["robust"]["a"], 0.5, places=4)
        self.assertAlmostEqual(cell["robust"]["b"], 0.5, places=4)
        self.assertTrue(cell["cap_ok"])
        self.assertEqual(cell["pure"], "c")

    def test_fq_cap_binds(self):
        F = {"a": 20.0, "b": 20.0, "c": 0.0}          # the good mix quarantines too much
        cell = constrained_minimax(M, F, NAMES, ["x", "y"], cap=10.0)
        self.assertTrue(cell["cap_ok"])
        self.assertLessEqual(cell["fq_pct"], 10.0 + 1e-6)
        self.assertGreater(cell["value"], 0.5)
        self.assertEqual(cell["pure"], "c")

    def test_infeasible_cap_is_flagged_not_hidden(self):
        F = {n: 50.0 for n in NAMES}
        cell = constrained_minimax(M, F, NAMES, ["x", "y"], cap=10.0)
        self.assertFalse(cell["cap_ok"])
        self.assertAlmostEqual(cell["value"], 0.5, places=6)

    def test_reduce_kernels_takes_the_worst_kernel(self):
        rows = [("a", "mid", "nominal", 0.25, 0.1, {"x": 0.2}, 1.0),
                ("a", "mid", "high", 0.25, 0.1, {"x": 0.5}, 3.0),
                ("a", "mid", "low", 0.25, 0.1, {"x": 0.1}, 2.0)]
        Mk, F, cols = reduce_kernels(rows, ["nominal", "high", "low"])
        self.assertEqual(Mk["a"]["x"], 0.5)
        self.assertEqual(F["a"], 3.0)
        self.assertEqual(cols, ["x"])


if __name__ == "__main__":
    unittest.main()
