"""The pi0 sweep converts the tau_sel table instead of regenerating it.

Spec: docs/preregistration/TIEN-DANG-KY-quet-pi0.md.

That shortcut is only honest if an order statistic of p at pi0' really is the
converted order statistic at pi0.  Pinned here on synthetic draws, plus the
property that makes the sweep safe to run inside a test process: every path it
touches is restored.
"""
import math
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))

import costs
import scoring
import sweep_pi0


def _post(lam, pi0):
    return pi0 * lam / (pi0 * lam + 1.0 - pi0)


class TheConversionIsExact(unittest.TestCase):

    def test_order_statistic_commutes_with_the_prior(self):
        rng = random.Random(7)
        d = 1.5
        lams = [sum(math.exp(d * rng.gauss(0, 1) - d * d / 2) for _ in range(5)) / 5
                for _ in range(20_000)]
        for q in (0.95, 0.975, 0.983, 0.987):
            i = int(q * len(lams))
            at_old = sorted(_post(x, 0.0799) for x in lams)[i]
            at_new = sorted(_post(x, 0.20) for x in lams)[i]
            self.assertAlmostEqual(sweep_pi0.convert(at_old, 0.0799, 0.20), at_new,
                                   places=12)

    def test_converting_to_the_same_prior_is_the_identity(self):
        for p in (0.0799, 0.2, 0.5, 0.93):
            self.assertAlmostEqual(sweep_pi0.convert(p, 0.0799, 0.0799), p, places=14)

    def test_the_empty_carrier_row_lands_on_the_new_prior(self):
        """n = 0 stores tau_sel = pi0 (no evidence); converted, it must read pi0'."""
        self.assertAlmostEqual(sweep_pi0.convert(0.0799, 0.0799, 0.04), 0.04, places=14)


class TheSweepLeavesNothingBehind(unittest.TestCase):

    def test_all_three_paths_move_inside_and_are_restored_after(self):
        before = (scoring.PI0, costs.PI0_WORLD, scoring.tau_sel(5, "mid", 2),
                  scoring.carrier_score([], 1.0))
        with sweep_pi0.installed_pi0(0.20):
            self.assertEqual(scoring.PI0, 0.20)
            self.assertEqual(scoring.carrier_score([], 1.0), 0.20)
            self.assertEqual(scoring.posterior(1.0), 0.20)
            self.assertGreater(scoring.tau_sel(5, "mid", 2), before[2])
        after = (scoring.PI0, costs.PI0_WORLD, scoring.tau_sel(5, "mid", 2),
                 scoring.carrier_score([], 1.0))
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
