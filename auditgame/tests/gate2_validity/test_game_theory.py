"""
GATE 2 -- the game-theoretic quantities the model is built on.
Spec: docs/thesis/Danh-sach-diem-can-them.md B7, C1, C3.

Three claims rest on these and none of them had a measurement:

  C1  exploitability -- "commit to a DISTRIBUTION, reveal only the distribution,
      never the draw". If randomising does not lower the best-response gain, the
      central mechanism of Sentinel is doing nothing a deterministic schedule
      could not do.
  B7  V* = min_pi max_a L -- the docs call B7 "the CEILING". Without it there is
      no reference point at all, and "how far from optimal" is unanswerable.
  C3  the best-responding attacker. runner.worst_case already maximises over the
      declared class per policy, which IS a best response -- it was simply never
      named as one, so the Stackelberg premise was neither stated nor checked.

The regret test below is the one that matters most. An independent run of this
same benchmark reported empirical_regret_vs_oracle = -0.163: a minimax oracle
worse than every policy. Negative regret is a BUG SIGNATURE, not a virtue, and
this asserts the sign that rules it out.
"""
from __future__ import annotations
import random, unittest

import agent, build, detector, game, runner
import policies as P
from core import seed_of

N_WF, BUDGET = 16, 17.95
DELTAS = (0, 2, 4)
CARRIERS = ("memory", "skill", "queue", "branch")


def _setup():
    wfs = [build.make_workflow(f"wf-{i:03d}", "django", 8,
                               random.Random(seed_of("gt", i))) for i in range(N_WF)]
    return wfs, detector.Detector.from_setting("mid"), agent.MockAgent()


class BestResponseGap(unittest.TestCase):

    def test_the_gap_is_never_negative(self):
        """A max over a set cannot fall below the mean over that same set.

        Negative means the best response and the average were computed over
        DIFFERENT sets -- exactly how an oracle ends up worse than the policies it
        bounds.

        Thesis claim (vi): "worst-case la MAX tren lop attacker".
        """
        wfs, det, ag = _setup()
        for name in ("B1 audit-at-commit", "B5 risk-score", "Sentinel"):
            runner.reset_survivor_cache()
            g = runner.best_response_gap(name, wfs, DELTAS, CARRIERS, det, ag,
                                         BUDGET, (1, 2), "mid")
            with self.subTest(policy=name):
                self.assertGreaterEqual(g, -1e-9, f"[{name}] gap {g}")

    def test_randomisation_does_not_lower_the_best_response_gap(self):
        """A NEGATIVE result, asserted so it cannot quietly go away.

        Sentinel against C8 -- the same policy with randomisation removed, matched
        on every other mechanism. Measured on 16 workflows x 2 seeds:

            Sentinel (randomised)          gap 0.4905
            C8 (deterministic)             gap 0.4515
            mean over randomised policies  0.4384
            mean over deterministic ones   0.3862

        Randomising makes the policy MORE exploitable here, not less. That runs
        against "commit to a distribution, reveal only the distribution, never the
        draw", which is the mechanism Sentinel is built on, and it is the second
        independent piece of evidence against RQ3 after the ablation turned out to
        be unstable across implementations.

        This test asserts the finding rather than the claim. If a later change
        makes randomisation protective, this goes RED -- which is the point: the
        result has to be revisited deliberately, not drift back.

        Thesis claim (vi): PHAN CHUNG cua "cam ket mot PHAN BO" -- chua co bang
        chung nao do trong benchmark nay.
        """
        wfs, det, ag = _setup()
        gaps = {}
        for name in ("Sentinel", "C8 deterministic sentinel"):
            runner.reset_survivor_cache()
            gaps[name] = runner.best_response_gap(name, wfs, DELTAS, CARRIERS, det,
                                                  ag, BUDGET, (1, 2), "mid")
        self.assertGreater(
            gaps["Sentinel"], gaps["C8 deterministic sentinel"],
            f"randomisation now LOWERS the best-response gap "
            f"({gaps['Sentinel']:.4f} vs {gaps['C8 deterministic sentinel']:.4f}). "
            f"That would support RQ3 -- re-measure and rewrite this test and the "
            f"finding in docs/thesis/Danh-sach-diem-can-them.md C5.")


class MinimaxCeiling(unittest.TestCase):

    def test_no_pure_policy_beats_the_minimax_value(self):
        """V* is a CEILING: empirical regret must be >= 0 for every pure policy.

        An independent run of this benchmark reported regret = -0.163, an oracle
        worse than everything it bounds. That is a bug signature, and this is the
        assertion that would have caught it.

        Thesis claim (vi): "B7 la TRAN TREN, khong phai doi thu canh tranh".
        """
        wfs, det, ag = _setup()
        M, rows, cols = game.payoff_matrix(list(P.REGISTRY), wfs, DELTAS, CARRIERS,
                                           det, ag, BUDGET, (1, 2), "mid")
        v, mix = game.minimax(M)
        for i, name in enumerate(rows):
            with self.subTest(policy=name):
                self.assertGreaterEqual(
                    max(M[i]) - v, -game.TOLERANCE,
                    f"[{name}] regret {max(M[i]) - v:.4f} < 0 -- V* is not a ceiling")

    def test_the_mixed_strategy_is_a_distribution(self):
        """Thesis claim (vi): "V* = min_pi max_a L"."""
        wfs, det, ag = _setup()
        M, rows, _ = game.payoff_matrix(list(P.REGISTRY), wfs, DELTAS, CARRIERS,
                                        det, ag, BUDGET, (1, 2), "mid")
        _, mix = game.minimax(M)
        self.assertEqual(len(mix), len(rows))
        self.assertAlmostEqual(sum(mix), 1.0, places=6)
        self.assertTrue(all(p >= -1e-12 for p in mix), f"negative weight: {mix}")

    def test_mixing_is_at_least_as_good_as_the_best_pure_policy(self):
        """The point of a mixed strategy: V* <= min over pure policies.

        If mixing never helps, the Stackelberg framing buys nothing over picking
        one policy, and Proposition 6's restricted-library story has no subject.

        Thesis claim (vi): "ngau nhien hoa la don bay".
        """
        wfs, det, ag = _setup()
        M, _, _ = game.payoff_matrix(list(P.REGISTRY), wfs, DELTAS, CARRIERS,
                                     det, ag, BUDGET, (1, 2), "mid")
        v, _ = game.minimax(M)
        self.assertLessEqual(v, min(max(r) for r in M) + game.TOLERANCE)


if __name__ == "__main__":
    unittest.main()
