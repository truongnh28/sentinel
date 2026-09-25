"""GATE 1 -- v2 carrier world: an audit reads the LIVE state of ONE carrier (SS4, Theorem 4)."""
import random
import unittest

import build
import carrier_policies as CP
import carrier_runner as R
import detector
import draft_setup as D
import world_v2 as W
from core import seed_of

K = D.TARGET_KAPPA_DRAFT


class _Fixed(CP.CarrierPolicy):
    """One fixed action every task, unlimited budget, quarantine on any anomaly."""
    def __init__(self, action, budget=1e9, H=10):
        super().__init__(budget, K, H)
        self.action, self.seen = action, []

    def act(self, t):
        return self.action

    def observe(self, t, obs):
        super().observe(t, obs)
        self.seen.append(obs)


def _perfect(rs):
    ag = W.StagedMockAgent(adoption_rate=1.0)
    return ag, W.DriftDetector(detector.Detector(12.0, 6.0), ag.drift_ids)


def _case(carrier="memory", delta=2):
    for i in range(300):
        wf = build.make_workflow(f"wfc-{i}", "repo-00", 10, random.Random(seed_of("cr", i)))
        c = build.plan_poison_all(wf, carrier, delta)
        if c:
            return wf, c[0]
    raise AssertionError("no feasible case")


def _run(action, carrier="memory", delta=2, **kw):
    wf, ps = _case(carrier, delta)
    for seed in range(1, 80):
        if R.survives(wf, ps, seed):
            pol = _Fixed(action, H=wf.H)
            return R.run_carrier(wf, (ps, "write"), pol, _perfect, seed, K, **kw), pol
    raise AssertionError("no surviving seed")


class TestCarrierRunner(unittest.TestCase):
    def test_no_audit_harms(self):
        self.assertEqual(_run(None)[0].harm, 1.0)

    def test_sweeping_the_poisoned_carrier_in_the_window_removes_it(self):
        r, _ = _run(("memory", 1))
        self.assertEqual(r.harm, 0.0)
        self.assertGreaterEqual(r.true_removed, 1)
        self.assertIsNotNone(r.detected_at)

    def test_sweeping_another_carrier_does_not_help(self):
        self.assertEqual(_run(("skill", 3))[0].harm, 1.0)

    def test_at_delta_zero_a_sweep_is_too_late(self):
        """The sweep runs after the agent: with iota = sigma it cannot act before sigma."""
        self.assertEqual(_run(("memory", 3), delta=0)[0].harm, 1.0)

    def test_commit_blocks_a_direct_patch(self):
        r, _ = _run((D.COMMIT, 1))
        self.assertEqual(r.harm, 0.0)
        # >= 1: a commit audit stops the patch, not the payload, which stays in memory and
        # can mark later patches too
        self.assertGreaterEqual(r.patch_blocks, 1)

    def test_commit_alarm_is_not_carrier_evidence(self):
        """D17."""
        _, pol = _run((D.COMMIT, 1))
        self.assertTrue(pol.seen)
        self.assertTrue(all(o.posterior is None for o in pol.seen))

    def test_the_policy_sees_only_the_carrier_it_paid_for(self):
        """D5."""
        _, pol = _run(("memory", 2))
        self.assertTrue(all(o.target == "memory" and o.posterior is not None for o in pol.seen))

    def test_depth_ladder_buys_the_deepest_affordable(self):
        wf, ps = _case()
        seed = next(s for s in range(1, 80) if R.survives(wf, ps, s))
        pol = _Fixed(("skill", 3), budget=wf.H * 2 * K["skill"], H=wf.H)
        r = R.run_carrier(wf, (ps, "write"), pol, _perfect, seed, K)
        self.assertAlmostEqual(r.spent, wf.H * 2 * K["skill"])
        self.assertEqual(r.audits["skill"], wf.H)

    def test_workflows_do_not_share_draws(self):
        """D19 (v1 bug #20): same seed, different workflows -> different episodes."""
        wfs = [build.make_workflow(f"wfd-{i}", "repo-00", 10, random.Random(seed_of("d", i)))
               for i in range(20)]
        solved = {R.run_carrier(w, None, _Fixed(None, H=10), _perfect, 1, K).n_solved for w in wfs}
        self.assertGreater(len(solved), 1)

    def test_survives_matches_a_clean_run(self):
        """survives() reads the solve draw directly; it must equal a full clean episode in a
        DIFFERENT world, for many workflows sharing one seed."""
        def other(rs):
            ag = W.StagedMockAgent(adoption_rate=0.3, skill_induction_rate=0.9,
                                   drift_rates={"memory": 0.5})
            return ag, W.DriftDetector(detector.Detector.from_setting("weak"), ag.drift_ids)

        checked = 0
        for i in range(20):
            wf = build.make_workflow(f"wfs-{i}", "repo-00", 10, random.Random(seed_of("sv", i)))
            cands = build.plan_poison_all(wf, "memory", 2)
            if not cands:
                continue
            ps = cands[0]
            fresh = R.run_carrier(wf, (ps, "write"), _Fixed(None, H=wf.H), other, 1, K,
                                  do_inject=False).solved_sigma
            self.assertEqual(R.survives(wf, ps, 1), fresh, wf.wf_id)
            checked += 1
        self.assertGreater(checked, 5)


if __name__ == "__main__":
    unittest.main()
