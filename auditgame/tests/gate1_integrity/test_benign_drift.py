"""
GATE 1 -- benign drift, the competing latent cause.
Spec: Toan-canh SS3 (beta); docs/thesis/Danh-sach-diem-can-them.md B3.

beta is in the notation table and was nowhere in the code. It is the rate at which
carriers change for ORDINARY reasons -- a note rewritten, a skill refined -- and it
is what makes false quarantine possible at all. Without it the only thing that ever
changes a carrier is the attacker, so "was this change benign?" is not a question
the world can pose, and lambda_Q prices a risk that does not exist.

It also underwrites the success criterion "benign-drift modelling is a USABILITY
mechanism: removing it multiplies false quarantine". That claim needs a world in
which drift happens.

Default beta = 0.0 reproduces every number recorded before this existed.
"""
from __future__ import annotations
import random, unittest

import agent, build, detector, runner
import policies as P
from core import CarrierStore, seed_of


def _churn_and_fq(beta: float, n=20):
    wfs = [build.make_workflow(f"wf-{i:03d}", "django", 8,
                               random.Random(seed_of("bd", i))) for i in range(n)]
    det = detector.Detector.from_setting("mid")
    ag = agent.MockAgent(drift_rate=beta)
    items = fq = runs = 0
    for i, wf in enumerate(wfs):
        ps = build.plan_poison(wf, "memory", 2, random.Random(seed_of("bdp", i)))
        if ps is None:
            continue
        pol = P.make_policy("Sentinel", 17.95, seed_of(wf.wf_id, 1, "S"), "mid")
        r = runner.run_once(wf, ps, pol, det, ag, seed=1)
        fq += r.false_quarantine
        runs += 1
        st = CarrierStore()
        a2 = agent.MockAgent(drift_rate=beta)
        for t, task in enumerate(wf.tasks):
            a2.run_task(t, task, st, seed=1, marker="raw_write")
        items += len(st.items["memory"])
    return items / runs, fq / runs


class BenignDrift(unittest.TestCase):

    def test_beta_zero_writes_no_extra_items(self):
        """The default must reproduce the old world exactly, or every recorded
        number silently becomes a number about a different world.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        items, _ = _churn_and_fq(0.0)
        self.assertAlmostEqual(items, 8.0, places=9,
                               msg=f"beta=0 writes {items} memory items per workflow, "
                                   f"expected one per task")

    def test_drift_creates_benign_churn(self):
        """beta > 0 must actually change the world.

        Thesis claim (vi): "benign drift la nguyen nhan tiem an canh tranh".
        """
        lo, _ = _churn_and_fq(0.0)
        hi, _ = _churn_and_fq(0.8)
        self.assertGreater(hi, lo, f"beta=0.8 gives {hi} items, beta=0 gives {lo}")

    def test_drift_raises_false_quarantine(self):
        """This is the mechanism lambda_Q prices.

        With no drift, every non-payload item is the agent's own fresh note and a
        false quarantine costs only that note. Under drift the store fills with
        benign revisions, so sweeping a carrier destroys more of them. If beta did
        not move Q_false, benign drift would be scenery.

        Thesis claim (vi): "cach ly nham phai co gia" (lambda_Q).
        """
        _, lo = _churn_and_fq(0.0)
        _, hi = _churn_and_fq(0.8)
        self.assertGreater(hi, lo, f"Q_false {hi} at beta=0.8 against {lo} at beta=0")

    def test_drifted_items_are_not_poisoned(self):
        """Drift is BENIGN by definition. If a drifted item carried the poison flag,
        beta would be an attack channel and the ground truth would be wrong.

        Thesis claim (vi): "benign drift la LANH TINH".
        """
        st = CarrierStore()
        ag = agent.MockAgent(drift_rate=1.0)
        wf = build.make_workflow("w", "django", 8, random.Random(seed_of("bd", 0)))
        for t, task in enumerate(wf.tasks):
            ag.run_task(t, task, st, seed=1, marker="raw_write")
        drifted = [i for i in st.live() if i.provenance.endswith("/drift")]
        self.assertTrue(drifted, "no drifted items produced at beta=1.0")
        self.assertFalse([i for i in drifted if i.poisoned],
                         "a drifted item is flagged poisoned -- drift is not benign")


if __name__ == "__main__":
    unittest.main()
