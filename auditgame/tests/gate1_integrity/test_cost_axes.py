"""
GATE 1 -- the two cost axes the model declares and the code did not have.
Spec: Danh-sach-diem-can-them.md A3, B1, B2.

    chi   = max_{k,k'} |kappa(k) - kappa(k')| / kappa_bar      carrier heterogeneity
    a_t   = {none} U {(audit, k, DEPTH)},  cost kappa(k, depth)

chi was never swept: experiment.py's docstring claimed a (Delta x chi x detector)
grid while the code looped over deltas and detector settings only, and chi is a
property of one fixed KAPPA table. RQ2 had therefore never been tested.

depth was missing entirely: the action was a bare carrier name and kappa was a
one-argument lookup, so "a deeper audit costs more and sees more" -- the central
trade-off of the audit action -- did not exist.
"""
from __future__ import annotations
import unittest

import detector
import policies as P


class ChiAxis(unittest.TestCase):

    def test_chi_of_matches_the_declared_formula(self):
        """chi is DERIVED from the cost table, never declared next to it.

        Declaring it separately is how the manuscript ended up with two values for
        one table: SS7 lists costs 0.4 / 0.9 / 1.6 / 4.1 and says "giving chi = 1.34",
        but the formula on those numbers gives 3.7 / 1.75 = 2.11.

        Thesis claim (vi): "chi la do khong dong nhat chi phi carrier".
        """
        self.assertAlmostEqual(P.chi_of({"a": 1.0, "b": 1.0}), 0.0, places=12)
        self.assertAlmostEqual(P.chi_of({"a": 0.0, "b": 2.0}), 2.0, places=12)

    def test_the_measured_table_gives_chi_2_11_not_1_34(self):
        """Reproduces the contradiction the docs flagged, as a measurement.

        Thesis claim (vi): "mau thuan 1,34 vs 2,11".
        """
        self.assertAlmostEqual(P.chi_of(P.KAPPA), 2.114, places=3)

    def test_kappa_for_chi_hits_the_target_and_preserves_the_mean(self):
        """Sweeping chi must not secretly sweep the budget too.

        kappa_bar is held fixed so that B means the same thing at every chi. If the
        mean moved, "equal budget across chi" would be false and the RQ2 axis would
        be confounded with the RQ1 budget.

        Thesis claim (vi): "chi day diem giao CHAM LAI", he so (1+chi).
        """
        base_mean = sum(P.KAPPA.values()) / len(P.KAPPA)
        for chi in (0.0, 0.5, 1.34, 2.114):
            t = P.kappa_for_chi(chi)
            with self.subTest(chi=chi):
                self.assertAlmostEqual(P.chi_of(t), chi, places=6)
                self.assertAlmostEqual(sum(t.values()) / len(t), base_mean, places=9)
                self.assertTrue(all(v > 0 for v in t.values()), f"negative cost: {t}")


class AuditDepth(unittest.TestCase):

    def test_a_deeper_audit_costs_more(self):
        """kappa(k, depth) is the two-argument function the model declares.

        Thesis claim (vi): "kappa(k, depth) -- audit sau hon thi dat hon".
        """
        self.assertGreater(P.cost_of("memory@2"), P.cost_of("memory@1"))
        self.assertAlmostEqual(P.cost_of("memory@1"), P.KAPPA["memory"], places=9)

    def test_a_deeper_audit_sees_more(self):
        """Depth has to buy something, or it is a pure tax nobody would ever pay.

        More depth = more independent evidence, so d' grows like sqrt(depth) and psi
        rises at a fixed tau_det. If psi did not move, depth would be decorative in
        exactly the way epsilon once was.

        Thesis claim (vi): "audit sau hon thi THAY nhieu hon".
        """
        det = detector.Detector.from_setting("mid")
        self.assertGreater(det.at_depth(2).psi, det.at_depth(1).psi)
        self.assertAlmostEqual(det.at_depth(1).psi, det.psi, places=12)

    def test_depth_does_not_change_the_false_positive_rate(self):
        """phi is fixed by tau_det, which depth must not touch.

        If depth moved phi as well, a deep audit would be a different DETECTOR, and
        the one-shared-detector constraint -- the reason allocation rather than
        detection is the studied variable -- would be broken.

        Thesis claim (vi): "MOT detector dung chung cho moi he thong".
        """
        det = detector.Detector.from_setting("mid")
        for d in (1, 2, 3):
            with self.subTest(depth=d):
                self.assertAlmostEqual(det.at_depth(d).phi, det.phi, places=12)


if __name__ == "__main__":
    unittest.main()
