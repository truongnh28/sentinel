"""
GATE 1 -- the TWO-CONDITION quarantine rule.
Spec: docs/thesis/math-foundation.md SS8.2 (Algorithm 1, line 8); docs/thesis/Danh-sach-diem-can-them.md A2.

The manuscript quarantines only when BOTH hold:

    Pr[poisoned | b_{t+1}] > tau      AND      E[harm] > eta_Q

and math-foundation SS8.2 says in as many words that the second condition is what
prevents "quarantine everything".  runner.py quarantined UNCONDITIONALLY on any
detector firing, so the very mechanism that rules out the degenerate policy was
absent -- and measured, Sentinel's E[Q_false] was 1.700 per workflow against B5's
0.272.  Penalising that through lambda_Q without restoring the rule would charge
policies for a defect we introduced.

E[harm] is not observable, so it is ESTIMATED, and the estimator is part of the
frozen config rather than a hidden constant:

    E[harm] ~= p_item * retrieval_rate(topic) * tasks_remaining

Every factor is computable by the defender from the PAST: the item posterior, how
often that topic has actually been retrieved so far, and how much horizon is left.
Nothing reads ground truth, nothing reads the future.
"""
from __future__ import annotations
import random, unittest

import build, agent, detector, runner
import policies as P
from core import seed_of
from tests.fixtures import identifiers


def _run(pol_name, tau_q, eta_q, delta=2, n=25):
    wfs = [build.make_workflow(f"wf-{i:03d}", "django", 8,
                               random.Random(seed_of("qr", i))) for i in range(n)]
    det, ag = detector.Detector.from_setting("mid"), agent.MockAgent()
    fq = tq = 0
    for i, wf in enumerate(wfs):
        ps = build.plan_poison(wf, "memory", delta, random.Random(seed_of("qrp", i)))
        if ps is None:
            continue
        pol = P.make_policy(pol_name, 17.95, seed_of(wf.wf_id, 1, pol_name), "mid")
        pol.tau_quarantine, pol.eta_Q = tau_q, eta_q
        r = runner.run_once(wf, ps, pol, det, ag, seed=1)
        fq += r.false_quarantine
        tq += r.true_quarantine
    return fq, tq


class TwoConditionQuarantine(unittest.TestCase):

    def test_raising_eta_Q_reduces_false_quarantine(self):
        """eta_Q is the magnitude gate.  Raise it and items that are suspicious but
        cannot do much damage stop being quarantined.

        If eta_Q changes nothing, the second condition is decorative and
        "quarantine everything" is still reachable -- the ABC O.g.3 / R.13 hole.

        Thesis claim (vi): "dieu kien thu hai la thu ngan 'quarantine moi thu'".
        """
        low, _ = _run("Sentinel", tau_q=0.0, eta_q=0.0)
        high, _ = _run("Sentinel", tau_q=0.0, eta_q=0.5)
        self.assertLess(high, low,
                        f"eta_Q=0.5 gives Q_false={high}, eta_Q=0.0 gives {low}: "
                        f"the magnitude gate does nothing.")

    def test_raising_tau_reduces_false_quarantine(self):
        """tau is the confidence gate, and it must bite independently of eta_Q.

        Thesis claim (vi): "quy tac quarantine HAI dieu kien".
        """
        low, _ = _run("Sentinel", tau_q=0.0, eta_q=0.0)
        high, _ = _run("Sentinel", tau_q=0.9, eta_q=0.0)
        self.assertLess(high, low,
                        f"tau=0.9 gives Q_false={high}, tau=0.0 gives {low}: "
                        f"the confidence gate does nothing.")

    def test_a_dormant_item_is_not_estimated_harmless(self):
        """The estimator must never assign ZERO expected harm to a dormant item.

        This is the trap the whole thesis is about.  A payload lies dormant by
        construction -- plan_poison guarantees no task in [iota, sigma) carries its
        topic -- so an unsmoothed frequency estimate gives it rate 0, therefore
        E[harm] = 0, therefore it is never quarantined.  The estimator would be
        blind to exactly the threat it exists to price.

        Measured with the unsmoothed version: Q_false halved (1.433 -> 0.775) but
        harm rose 0.450 -> 0.750, because the dormant payload became unquarantinable.

        Thesis claim (vi): "nam im dung Delta task" la co che tan cong trung tam.
        """
        # a topic never seen before: count 0, but it must not price to zero
        e = runner.expected_harm(p_item=0.9, topic="never-seen",
                                 topic_counts={"other": 5}, tasks_seen=5,
                                 tasks_remaining=3)
        self.assertGreater(e, 0.0,
                           "a dormant item prices to zero expected harm -- the "
                           "estimator is blind to dormancy, which is the attack")

    def test_the_rule_reads_no_ground_truth(self):
        """Structural: the estimator must not touch Item.poisoned.

        Thesis claim (vi): "chinh sach khong biet dau la mam doc".
        """
        self.assertNotIn("poisoned", identifiers(runner.expected_harm),
                         "expected_harm() reads ground truth -- I2 broken")


if __name__ == "__main__":
    unittest.main()
