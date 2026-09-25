"""GATE 1 -- v2: the draft's setup constants and derived quantities (carrier world)."""
import unittest

import draft_setup as D


class TestDraftSetup(unittest.TestCase):
    def test_draft_table_gives_134_under_2mad_and_2114_under_range(self):
        self.assertAlmostEqual(D.chi_reported(D.TARGET_KAPPA_DRAFT), 1.342857, places=5)
        self.assertAlmostEqual(D.chi_range(D.TARGET_KAPPA_DRAFT), 2.114286, places=5)

    def test_headline_cell_is_the_draft_table_verbatim(self):
        self.assertEqual(D.target_kappa_for_chi(1.34), D.TARGET_KAPPA_DRAFT)

    def test_grid_labels_and_proportional_measures(self):
        for chi in D.CHIS:
            k = D.target_kappa_for_chi(chi)
            self.assertLess(abs(D.chi_reported(k) - chi), 0.005)
            if chi:
                self.assertAlmostEqual(D.chi_range(k) / D.chi_reported(k),
                                       2.114286 / 1.342857, places=6)

    def test_targets_are_the_four_carrier_audits(self):
        """D2: SS4's actions are per carrier; SS8's four kinds map one-to-one onto them."""
        self.assertEqual(D.TARGETS, D.SWEEP_CARRIERS + (D.COMMIT,))
        self.assertEqual(set(D.TARGET_KAPPA_DRAFT), set(D.TARGETS))
        self.assertEqual(sorted(D.STAGE_OF_TARGET.values()),
                         ["commit", "delegation", "insertion", "retrieval"])

    def test_budget_spec(self):
        self.assertAlmostEqual(D.BudgetSpec().budget(10), 10 * D.MAX_DEPTH * 4.1)
        self.assertAlmostEqual(D.BudgetSpec("share", 0.5).budget(10), 5 * D.MAX_DEPTH * 4.1)
        self.assertAlmostEqual(D.BudgetSpec("absolute", 3.0).budget(10), 30.0)
        with self.assertRaises(ValueError):
            D.BudgetSpec("bogus", 1).budget(10)

    def test_b1_budget_is_anchored_and_never_binds_one_action(self):
        """D4b: B does not move with chi; one action per task never exceeds B/H at b1."""
        for chi in D.CHIS:
            k = D.target_kappa_for_chi(chi)
            self.assertAlmostEqual(D.budget_b1(10) / 10, D.MAX_DEPTH * 4.1)
            self.assertLessEqual(D.MAX_DEPTH * max(k.values()), D.budget_b1(10) / 10 + 1e-9)

    def test_eta_q_grid_holds_the_bayes_value(self):
        lq = D.LAMBDA_Q
        self.assertAlmostEqual(D.ETA_Q_BAYES, lq / (1 + lq), places=4)
        self.assertIn(D.ETA_Q_BAYES, D.ETA_Q_GRID)
        self.assertEqual(list(D.ETA_Q_GRID), sorted(D.ETA_Q_GRID))

    def test_seeds(self):
        self.assertEqual(len(D.SEEDS), 10)
        self.assertTrue(set(D.TUNE_SEEDS) <= set(D.SEEDS))


if __name__ == "__main__":
    unittest.main()
