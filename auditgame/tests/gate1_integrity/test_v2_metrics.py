"""GATE 1 -- v2 metrics: V re-maxes per resample; family alpha; cross-fitted best response."""
import random
import unittest

import metrics_v2 as M


def rec(policy, attack, wf, repo, harm):
    return dict(policy=policy, attack=attack, delta=4, wf=wf, repo=repo, seed=1, harm=harm,
                detected_at=None, iota=1, n_solved=6, t_lost=0, false_removed=1,
                benign_inspected=20)


class TestMetricsV2(unittest.TestCase):
    def setUp(self):
        self.recs = []
        for i in range(20):
            r = f"r{i % 5}"
            self.recs += [rec("B1", "a", f"w{i}", r, 1.0), rec("B1", "b", f"w{i}", r, 0.0),
                          rec("S", "a", f"w{i}", r, 0.5), rec("S", "b", f"w{i}", r, 0.5)]

    def test_value(self):
        self.assertEqual(M.value(M.harm_table(self.recs, "B1", ["a", "b"], [4])), 1.0)
        self.assertEqual(M.value(M.harm_table(self.recs, "S", ["a", "b"], [4])), 0.5)

    def test_gain(self):
        g = M.gain_ci(self.recs, "B1", "S", ["a", "b"], [4], n_boot=200)
        self.assertAlmostEqual(g["gain"], 50.0)
        self.assertAlmostEqual(g["abs_diff"], 0.5)
        self.assertEqual((g["n_repos"], g["n_workflows"], g["n_zero_base"]), (5, 20, 0))
        self.assertEqual(g["base_events"], 20)
        self.assertTrue(g["rel_reliable"])

    def test_family_alpha_widens_the_interval(self):
        noisy = [dict(r, harm=random.Random(i).random()) for i, r in enumerate(self.recs)]
        wide = M.gain_ci(noisy, "B1", "S", ["a", "b"], [4], n_boot=2000, alpha=0.05 / 4)
        narrow = M.gain_ci(noisy, "B1", "S", ["a", "b"], [4], n_boot=2000, alpha=0.05)
        self.assertLessEqual(wide["abs_lo"], narrow["abs_lo"])
        self.assertGreaterEqual(wide["abs_hi"], narrow["abs_hi"])

    def test_vs_best_baseline_picks_the_strongest(self):
        """D22."""
        recs = self.recs + [dict(r, policy="B4", harm=0.2) for r in self.recs if r["policy"] == "B1"]
        g = M.gain_vs_best(recs, ["B1", "B4"], "S", ["a", "b"], [4], n_boot=200)
        self.assertEqual(g["best_baseline"], "B4")
        self.assertAlmostEqual(g["abs_diff"], -0.3)
        self.assertLess(g["abs_hi"], 0)

    def test_too_few_base_events_is_unreadable(self):
        recs = [r for r in self.recs if r["wf"] in {f"w{i}" for i in range(5)}]
        g = M.gain_ci(recs, "B1", "S", ["a", "b"], [4], n_boot=200)
        self.assertEqual(g["base_events"], 5)
        self.assertFalse(g["rel_reliable"])

    def test_floor_is_counted_not_dropped(self):
        recs = [dict(r, harm=0.0) if r["policy"] == "B1" else r for r in self.recs]
        g = M.gain_ci(recs, "B1", "S", ["a", "b"], [4], n_boot=200)
        self.assertEqual(g["n_zero_base"], 200)
        self.assertFalse(g["rel_reliable"])
        self.assertAlmostEqual(g["abs_diff"], -0.5)

    def test_side(self):
        s = M.side(self.recs, "S", ["a", "b"], [4])
        self.assertAlmostEqual(s["false_quarantine_pct"], 5.0)
        self.assertAlmostEqual(s["clean_completion"], 100.0)

    def test_crossfit_removes_the_max_of_noisy_means_bias(self):
        """D27: 30 placements with the SAME true harm 0.2; the naive max over their noisy
        means overshoots, the cross-fitted value does not."""
        rng = random.Random(7)
        rows = [{"wf": f"w{w}", "placement": p, "seed": s, "harm": float(rng.random() < 0.2)}
                for w in range(40) for p in range(30) for s in range(1, 11)]
        v = M.crossfit_value(rows)
        self.assertGreater(v["v_br_naive"], 0.4)
        self.assertAlmostEqual(v["v_br"], 0.2, delta=0.05)

    def test_crossfit_finds_a_real_weak_spot(self):
        rows = [{"wf": "w0", "placement": p, "seed": s, "harm": float(p == 3)}
                for p in range(6) for s in range(1, 11)]
        self.assertAlmostEqual(M.crossfit_value(rows)["v_br"], 1.0)

    def test_controls(self):
        self.assertTrue(M.controls(0.01, 0.6, {"B3": 0.8, "B4": 0.7})["ok"])
        self.assertFalse(M.controls(0.2, 0.6, {"B3": 0.8})["positive_ok"])
        self.assertFalse(M.controls(0.01, 0.6, {"B3": 0.5})["negative_ok"])

    def test_a_policy_without_records_gives_nan_not_a_fake_interval(self):
        g = M.gain_ci(self.recs, "B1", "NOPE", ["a", "b"], [4], n_boot=50)
        for k in ("gain", "lo", "hi", "abs_diff", "abs_lo", "abs_hi"):
            self.assertNotEqual(g[k], g[k], k)                  # NaN
        self.assertFalse(g["rel_reliable"])
        v = M.gain_vs_best(self.recs, ["B1", "NOPE"], "S", ["a", "b"], [4], n_boot=50)
        self.assertEqual(v["best_baseline"], "B1")               # an empty baseline cannot win
        # ... not even inside a resample: before the fix NOPE's 0.0 won every draw (-0.5 here)
        self.assertAlmostEqual(v["abs_lo"], 0.5)
        self.assertAlmostEqual(v["abs_hi"], 0.5)
        none = M.gain_vs_best(self.recs, ["NOPE"], "S", ["a", "b"], [4], n_boot=50)
        self.assertIsNone(none["best_baseline"])
        self.assertNotEqual(none["abs_diff"], none["abs_diff"])  # NaN


if __name__ == "__main__":
    unittest.main()
