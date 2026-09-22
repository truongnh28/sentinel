"""
GATE 2 -- the composite loss L, and the degeneracy test it exists to pass.
Spec: Toan-canh SSA.4; docs/thesis/Danh-sach-diem-can-them.md A1.

    L = E[harm] + lambda_Q * E[Q_false] + lambda_T * E[T_lost]

Toan-canh SSA.4 argues the point directly: with lambda_Q = lambda_T = 0, the policy
"quarantine all K carriers at t=1" reaches harm 0 and is therefore OPTIMAL, while
shutting the system down completely. It calls the one-term model "trivially
solvable and useless".

Every number measured before this file existed scored exactly that one-term model,
because metrics.py had gain() and report_header() and nothing else.

lambda_Q is NOT chosen here. It is REPORTED: lambda_q_star is the weight at which
the ranking changes, so a reader decides whether a false quarantine really costs
less than that fraction of a slipped payload in their setting. Same move as eps*.
"""
from __future__ import annotations
import random, unittest

import build, agent, detector, metrics, runner
import policies as P
from core import seed_of

N_WF, BUDGET, DELTA = 25, 17.95, 2

#: SSA.4's argument is about the SHAPE of the loss, not about affordability: it
#: assumes the degenerate policy can be run.  Testing it at a budget where NC1
#: cannot afford to sweep every carrier every task tests nothing at all, so the
#: degeneracy test gets its own budget.
DEGENERACY_BUDGET = 200.0


def _cells(budget=BUDGET):
    """{policy -> (harm, q_false, t_lost)} on one frozen corpus."""
    wfs = [build.make_workflow(f"wf-{i:03d}", "django", 8,
                               random.Random(seed_of("cl", i))) for i in range(N_WF)]
    det, ag = detector.Detector.from_setting("mid"), agent.MockAgent()
    out = {}
    for name in P.REGISTRY:
        runner.reset_survivor_cache()
        c = runner.worst_case(name, wfs, (DELTA,), list(P.KAPPA), det, ag,
                              budget, (1, 2, 3), "mid")
        out[name] = (c.harm, c.q_false, c.t_lost)
    return out


class CompositeLoss(unittest.TestCase):

    def test_quarantine_everything_loses_once_lambda_Q_is_positive(self):
        """The degeneracy test from Toan-canh SSA.4, made executable.

        NC1 quarantines the store clean, so on harm alone it is unbeatable. If it
        does not lose under L, the loss function still has a way to win by
        cheating, and the whole allocation question is vacuous.

        Thesis claim (vi): "ham mat mat KHONG co duong thang bang gian lan".
        """
        cells = _cells(DEGENERACY_BUDGET)
        self.assertIn("NC1 quarantine-everything", cells,
                      "the degeneracy control is not registered -- nothing tests SSA.4")
        nc1 = cells["NC1 quarantine-everything"]
        others = {k: v for k, v in cells.items() if k != "NC1 quarantine-everything"}

        self.assertLessEqual(
            nc1[0], min(v[0] for v in others.values()) + 1e-9,
            "NC1 does not even win on harm alone -- the fixture is not exercising "
            "the degenerate behaviour, so this test proves nothing")

        L_nc1 = metrics.loss(*nc1, lambda_Q=metrics.LAMBDA_Q, lambda_T=metrics.LAMBDA_T)
        beaten = [k for k, v in others.items()
                  if metrics.loss(*v, lambda_Q=metrics.LAMBDA_Q,
                                  lambda_T=metrics.LAMBDA_T) < L_nc1]
        self.assertTrue(
            beaten,
            f"NC1 wins under L too (L={L_nc1:.3f}) at lambda_Q={metrics.LAMBDA_Q}: "
            f"the loss function still rewards shutting the system down.")

    def test_lambda_q_star_is_reported_not_assumed(self):
        """The weight at which the ranking flips is a RESULT, not a parameter.

        A headline that holds only below lambda_q_star is a statement about
        lambda_Q, not about the policy. Measured: the flip sits near 0.05, far too
        close to zero to pick a value by intuition.

        Thesis claim (vi): "bao cao lambda_Q*, dung chon lambda_Q".
        """
        cells = _cells()
        star = metrics.lambda_q_star(cells, lambda_T=metrics.LAMBDA_T)
        self.assertIsNotNone(
            star, "no lambda_Q changes the ranking -- either one policy dominates "
                  "on every term, or Q_false is not being measured at all")
        self.assertGreater(star, 0.0)
        below = min(cells, key=lambda k: metrics.loss(
            *cells[k], lambda_Q=0.0, lambda_T=metrics.LAMBDA_T))
        above = min(cells, key=lambda k: metrics.loss(
            *cells[k], lambda_Q=star + 1e-6, lambda_T=metrics.LAMBDA_T))
        self.assertNotEqual(below, above,
                            f"ranking unchanged across lambda_q_star={star}: "
                            f"{below} wins on both sides")


if __name__ == "__main__":
    unittest.main()
