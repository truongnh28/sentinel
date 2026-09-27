"""Draft S8/S9 grid values that v3/config.py fixes (T1).  Each test protects one DCM row
of v3/dcm/T01.csv; its docstring carries the id and the verbatim draft sentence."""
import unittest

import detector
import draft_setup as D
from v3 import config as C


class TestS8Config(unittest.TestCase):
    def test_chi_levels_realised_by_depth_configs(self):
        """D8.chi (C3, C16, Q6): "carrier heterogeneity χ ∈ {0, 0.5, 1.34} (achieved by
        equalising or differentiating audit depths)".  D7.kappa (C3): "Costs are measured,
        not assigned: 0.4, 0.9, 1.6 and 4.1 CPU-minutes respectively, giving χ = 1.34."

        The levels are the ones depth CAN reach (C16(a)): each label is the S4 chi_range
        of the per-look prices times the cell's fixed depths, rounded to 2 decimals; the
        commit is at depth 1 in every cell (R7).  The draft's own prices give 2.114 under
        its own S4 formula, not 1.34 (erratum C3)."""
        self.assertEqual(C.KAPPA_UNIT, {"memory": 0.4, "queue": 0.9, "skill": 1.6, "commit": 4.1})
        self.assertAlmostEqual(D.chi_range(C.KAPPA_UNIT), 2.114, places=3)
        self.assertEqual(C.CHI_LEVELS, ("1.04", "1.33", "2.11"))
        self.assertEqual(C.CHI_DEPTHS, {"1.04": (3, 3, 2, 1), "1.33": (3, 2, 1, 1),
                                        "2.11": (1, 1, 1, 1)})
        self.assertEqual(C.TARGETS, ("memory", "queue", "skill", "commit"))
        expected_kappa = {"1.04": (1.2, 2.7, 3.2, 4.1), "1.33": (1.2, 1.8, 1.6, 4.1),
                          "2.11": (0.4, 0.9, 1.6, 4.1)}          # plan S1 "Kiem so chi"
        for label in C.CHI_LEVELS:
            cell = C.Cell(rho=0.0, delta=4, chi=label)
            kappa = cell.kappa()
            for t, want in zip(C.TARGETS, expected_kappa[label]):
                self.assertAlmostEqual(kappa[t], want, places=9, msg=f"{label} {t}")
            self.assertEqual(f"{D.chi_range(kappa):.2f}", label)
            self.assertEqual(cell.depths()["commit"], 1, "commit is at depth 1 in every chi cell")
        self.assertEqual(C.CHI_PRIMARY, "1.33")

    def test_detector_levels_are_three_dprimes(self):
        """D8.detector (C15, Q11): "(ψ, φ) are swept over 3 settings (0.75/0.20,
        0.85/0.12, 0.92/0.06) so that results are not an artifact of one detector."

        psi rises while phi falls, so the three settings are three detectors of different
        quality, not three thresholds on one ROC: the grid is labelled by d'."""
        self.assertEqual(C.DPRIME_LEVELS, (1.52, 2.21, 2.96))
        self.assertEqual(C.DPRIME_PRIMARY, 2.21)
        dps = []
        for level, name in C.DETECTOR_OF_DPRIME.items():
            psi, phi = detector.SETTINGS[name]
            dp, _tau = detector.operating_point(psi, phi)
            self.assertEqual(round(dp, 2), level, name)
            det = C.Cell(rho=0.25, delta=4, dprime=level).detector()
            self.assertAlmostEqual(det.psi, psi, places=9)
            self.assertAlmostEqual(det.phi, phi, places=9)
            dps.append(dp)
        self.assertEqual(dps, sorted(dps))
        psis = [detector.SETTINGS[n][0] for n in C.DETECTOR_OF_DPRIME.values()]
        phis = [detector.SETTINGS[n][1] for n in C.DETECTOR_OF_DPRIME.values()]
        self.assertEqual(psis, sorted(psis))
        self.assertEqual(phis, sorted(phis, reverse=True))

    def test_delta_grid_is_draft_grid_plus_attacker_column(self):
        """D8.delta (C10, O5): "Trigger delay Δ ∈ {0, 1, 2, 4, 8} tasks".

        The environment fixes Delta per cell on the draft's grid (primary); one extra
        column lets the attacker choose Delta, with the O5 classes declared."""
        self.assertEqual(C.DELTAS, (0, 1, 2, 4, 8))
        self.assertEqual(C.DELTA_AXIS, (0, 1, 2, 4, 8, "attacker"))
        for d in C.DELTA_AXIS:
            self.assertEqual(C.Cell(rho=0.5, delta=d).delta, d)
        for bad in (3, -1, 16, "4", True, None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                C.Cell(rho=0.5, delta=bad)
        self.assertEqual(C.ATTACKER_DELTA_CLASSES,
                         ("fixed-delta-per-sequence", "uniform-delta-mix-per-workflow"))
        self.assertEqual(C.HEADLINE_DELTAS, (4, 8))

    def test_ten_seeds(self):
        """D9.seeds (Q9, D24): "4,500 instances × 8 systems × 3 seeds."

        v3 runs 10 seeds, a declared L2 deviation (docs/reports/v3-p0.md S2)."""
        self.assertEqual(C.SEEDS, tuple(range(1, 11)))
        self.assertEqual(len(set(C.SEEDS)), 10)


if __name__ == "__main__":
    unittest.main()
