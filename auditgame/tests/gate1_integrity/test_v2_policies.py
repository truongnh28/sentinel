"""GATE 1 -- v2 policies: baselines B1..B6, the 28-policy library, the belief, line 8."""
import collections
import random
import unittest

import belief_v2 as BV
import build
import carrier_policies as CP
import carrier_runner as R
import detector
import draft_setup as D
import world_v2 as W
from core import CARRIERS, Item, seed_of

K = D.TARGET_KAPPA_DRAFT


def world(rs):
    ag = W.StagedMockAgent(drift_rates=D.BETA_WORLD)
    return ag, W.DriftDetector(detector.Detector.from_setting("mid"), ag.drift_ids)


def _member(name, seed=0, betas=None, eta_q=D.ETA_Q_BAYES, H=12):
    return CP.make_member(name, D.budget_b1(H), K, H, seed, "mid", {}, betas or {}, eta_q)


class TestBaselines(unittest.TestCase):
    def setUp(self):
        self.wf = build.make_workflow("wfb", "repo-00", 11, random.Random(seed_of("b", 3)))
        self.B = D.budget_b1(self.wf.H)

    def test_b1_audits_every_commit_at_max_depth(self):
        pol = CP.B1AuditAtCommit(self.B, K, self.wf.H)
        r = R.run_carrier(self.wf, None, pol, world, 1, K)
        self.assertAlmostEqual(pol.spent, self.B)
        self.assertEqual(r.audits[D.COMMIT], self.wf.H)

    def test_every_baseline_respects_budget(self):
        for share in (1.0, 0.25):
            for name, cls in CP.BASELINES.items():
                pol = cls(share * self.B, K, self.wf.H, rng_seed=7, cfg={"tau5": 0.3})
                R.run_carrier(self.wf, None, pol, world, 1, K)
                self.assertLessEqual(pol.spent, share * self.B * (1 + 1e-9), (share, name))

    def test_fixed_carrier_baselines_follow_d2(self):
        self.assertEqual(CP.B3AuditOnInsertion(self.B, K, 11).act(0), ("memory", D.MAX_DEPTH))
        self.assertEqual(CP.B4AuditOnRetrieval(self.B, K, 11).act(0), ("queue", D.MAX_DEPTH))

    def test_b5_escalates_to_commit_after_a_hot_signal(self):
        from carrier_runner import Observation
        pol = CP.B5RiskScore(self.B, K, 11, cfg={"tau5": 0.3})
        pol.observe(0, Observation("memory", 1, True, 0.9, 5))
        self.assertEqual(pol.act(1), (D.COMMIT, D.MAX_DEPTH))
        pol.observe(1, Observation(D.COMMIT, 3, False, None, 1))
        self.assertEqual(pol.act(2)[1], 1)

    def test_oracle_control_audits_the_attacked_carrier(self):
        self.assertEqual(CP.OracleControl(self.B, K, 11, attacked="skill").act(3), ("skill", D.MAX_DEPTH))
        self.assertEqual(CP.OracleControl(self.B, K, 11, attacked="branch").act(3), (D.COMMIT, D.MAX_DEPTH))


class TestLibrary(unittest.TestCase):
    def test_28_in_three_families(self):
        self.assertEqual(len(CP.LIBRARY), 28)
        fam = collections.Counter(n.split("-")[1] for n in CP.LIBRARY)
        self.assertEqual(fam, {"SW": 8, "BT": 12, "RO": 8})

    def test_sw_commit_is_b1(self):
        pol = _member("L-SW-commit")
        self.assertEqual({pol.act(t) for t in range(12)}, {(D.COMMIT, D.MAX_DEPTH)})

    def test_evidence_free_members_are_distinct(self):
        """SW and RO do not read evidence: their schedules over (seed, t) must all differ."""
        sched = {}
        for n in CP.LIBRARY:
            if "-BT-" in n:
                continue
            sched[n] = tuple(_member(n, seed=s).act(t) for s in range(8) for t in range(12))
        self.assertEqual(len(set(sched.values())), len(sched))

    def test_rotation_phase_is_random_and_covers(self):
        phases = {_member("L-RO-c3-p1-d3", seed=s).phase for s in range(40)}
        self.assertEqual(phases, {0, 1, 2})
        pol = _member("L-RO-c3-p1-d3", seed=5)
        for t0 in range(9):
            self.assertEqual({pol.act(t)[0] for t in range(t0, t0 + 3)}, set(D.SWEEP_CARRIERS))

    def test_belief_threshold_samples_with_a_floor(self):
        """SS5.3: randomized; the floor keeps every sweep carrier in play."""
        def picks(floor_idx):
            out = collections.Counter()
            for s in range(300):
                pol = _member(f"L-BT-0.3-f{floor_idx}", seed=s)
                b = pol.belief
                for w in b.windows:
                    b.b[w] = 0.0
                live = [w for w in b.windows if w[0] == "memory" and b.active(w, 2)]
                for w in live:
                    b.b[w] = 0.9 / len(live)
                b.b[b.NULL] = 0.1
                out[pol.act(2)[0]] += 1
            return out
        self.assertEqual(set(picks(0)), {"memory"})
        self.assertEqual(set(picks(2)), set(D.SWEEP_CARRIERS))


class TestBeliefAndLine8(unittest.TestCase):
    def test_drift_lowers_attack_posterior_for_the_same_alarm(self):
        a = BV.DriftBelief(CARRIERS, 10, (2,), betas={"memory": 0.5})
        b = BV.DriftBelief(CARRIERS, 10, (2,), betas={})
        a.update(3, {"memory": 0.6})
        b.update(3, {"memory": 0.6})
        self.assertLess(a.p_attack(), b.p_attack())

    def test_item_posterior(self):
        d = 3.8
        lo, hi = BV.item_posterior(1.5, d, 0.02, 0.0), BV.item_posterior(4.0, d, 0.02, 0.0)
        self.assertLess(lo, hi)
        self.assertGreater(hi, 0.9)
        self.assertLess(BV.item_posterior(4.0, d, 0.02, 0.3), 0.2)      # a matched fresh drift
        self.assertEqual(BV.item_posterior(4.0, d, 0.0, 0.0), 0.0)

    def _firing_fresh_item(self, carrier="memory"):
        it = Item(carrier=carrier, topic="auth", content="new", created_at=4,
                  provenance="repo/docs/conventions.md", poisoned=True)
        deep = W.DriftDetector(detector.Detector.from_setting("mid"), set()).at_depth(3)
        return it, deep, [(it, deep.d_prime)]

    def test_line8_waits_for_a_second_look_when_drift_is_likely(self):
        """A FRESH firing item in a drift-heavy carrier could be a drift event: with beta_hat
        the member keeps it; without drift modelling it removes it (the ablation's lever)."""
        it, deep, firing = self._firing_fresh_item()
        keep = _member("L-SW-uniform", betas={"memory": 0.31})
        drop = _member("L-SW-uniform", betas={})
        self.assertEqual(keep.remove(4, "memory", firing, deep, [it]), [])
        self.assertEqual(drop.remove(4, "memory", firing, deep, [it]), [it])

    def test_line8_removes_an_old_item_that_keeps_firing(self):
        it, deep, firing = self._firing_fresh_item()
        pol = _member("L-SW-uniform", betas={"memory": 0.31})
        self.assertEqual(pol.remove(6, "memory", firing, deep, [it]), [it])


if __name__ == "__main__":
    unittest.main()
