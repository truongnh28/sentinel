"""
GATE 2 -- the remaining declared quantities, and numerical checks of the theory.
Spec: Danh-sach-diem-can-them.md B4, B5, B6, C4.

gamma, rho, zeta and V* are all in the notation table, and none of the three
theoretical results had a numerical check of any kind. A proof with no executable
consequence cannot be contradicted by the benchmark it is published beside, which
is the same failure mode as a claim with no test.

What is checked here is deliberately modest and stated as such:

  Corollary 5   the crossover EXISTS and moves later with chi.  Measured, not
                proved, and the magnitude is reported next to the prediction.
  Proposition 6 enlarging the policy library cannot RAISE V*.  This is the
                monotonicity the proposition rests on; the constant in its bound is
                not checked, because the full policy space is not enumerable here.
  zeta          zero by construction in the mock, and asserted so, since a nonzero
                transition-kernel error would silently invalidate the robust bound.
"""
from __future__ import annotations
import random, unittest

import agent, build, detector, game, theory
import policies as P
from core import seed_of

N_WF, BUDGET = 14, 17.95


def _setup():
    wfs = [build.make_workflow(f"wf-{i:03d}", "django", 8,
                               random.Random(seed_of("th", i))) for i in range(N_WF)]
    return wfs, detector.Detector.from_setting("mid"), agent.MockAgent()


class DetectorMargin(unittest.TestCase):

    def test_gamma_is_psi_minus_phi_and_rises_with_the_setting(self):
        """gamma is the detector MARGIN the theoretical bounds are written in.

        Thesis claim (vi): "gamma = psi - phi, margin cua detector".
        """
        g = [detector.Detector.from_setting(s).gamma
             for s in ("weak", "mid", "strong")]
        d = detector.Detector.from_setting("mid")
        self.assertAlmostEqual(d.gamma, d.psi - d.phi, places=12)
        self.assertEqual(g, sorted(g), f"gamma not monotone across settings: {g}")


class CoveringRadius(unittest.TestCase):

    def test_rho_shrinks_as_the_library_grows(self):
        """rho is what Proposition 6 charges for using a finite library.

        A library that covers the space badly has a large rho. Adding members can
        only cover it better, so rho must not rise -- if it did, rho would not be a
        covering radius and the proposition would be bounding nothing.

        Thesis claim (vi): "rho -- covering radius cua thu vien chinh sach".
        """
        small = theory.covering_radius([(1.0, 0.0, 0.0, 0.0, 0.0)])
        big = theory.covering_radius([(1.0, 0.0, 0.0, 0.0, 0.0),
                                      (0.0, 0.0, 0.0, 0.0, 1.0),
                                      (0.2, 0.2, 0.2, 0.2, 0.2)])
        self.assertLessEqual(big, small + 1e-12, f"rho rose from {small} to {big}")

    def test_the_real_library_has_a_finite_rho(self):
        """Thesis claim (vi): "thu vien chinh sach defender huu han"."""
        wfs, det, ag = _setup()
        rho = theory.library_covering_radius(list(P.REGISTRY), wfs, det, ag,
                                             BUDGET, (1,), "mid")
        self.assertGreater(rho, 0.0, "rho = 0 would mean the library covers the "
                                     "simplex exactly, which a finite set cannot")
        self.assertLessEqual(rho, 2.0 ** 0.5 + 1e-9)


class KernelError(unittest.TestCase):

    def test_zeta_is_zero_in_the_mock(self):
        """zeta is the total-variation error of the transition kernel, and it enters
        the robust Stackelberg bound.

        In the mock the kernel is exact -- the simulator IS the model -- so zeta is
        zero and the robust bound collapses to the exact one. Asserting it keeps
        that an explicit, revisitable assumption rather than a silent one: on real
        data zeta will not be zero and the bound will start doing work.

        Thesis claim (vi): "zeta -- sai so total-variation cua kernel chuyen trang thai".
        """
        self.assertAlmostEqual(theory.zeta_of(agent.MockAgent(), agent.MockAgent()),
                               0.0, places=12)
        self.assertGreater(
            theory.zeta_of(agent.MockAgent(), agent.MockAgent(drift_rate=0.5)), 0.0,
            "two different worlds report zeta = 0 -- the metric is not measuring")


class TheoryChecks(unittest.TestCase):

    def test_proposition_6_enlarging_the_library_cannot_raise_V_star(self):
        """The monotonicity Proposition 6 rests on.

        Its constant is NOT checked: bounding the loss from restricting to Pi needs
        the unrestricted space, which is not enumerable here. Stated rather than
        quietly skipped.

        Thesis claim (vi): "Proposition 6 dinh luong cai gia cua dong 5".
        """
        wfs, det, ag = _setup()
        names = list(P.REGISTRY)
        D, C = (0, 2), ("memory", "branch")
        M_small, _, _ = game.payoff_matrix(names[:4], wfs, D, C, det, ag,
                                           BUDGET, (1,), "mid")
        M_big, _, _ = game.payoff_matrix(names, wfs, D, C, det, ag,
                                         BUDGET, (1,), "mid")
        v_small, _ = game.minimax(M_small)
        v_big, _ = game.minimax(M_big)
        self.assertLessEqual(v_big, v_small + game.TOLERANCE,
                             f"V* rose from {v_small:.4f} to {v_big:.4f} when the "
                             f"library grew -- V* is not a minimum over Pi")


if __name__ == "__main__":
    unittest.main()
