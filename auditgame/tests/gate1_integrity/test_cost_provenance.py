"""GATE 1 -- every cost constant carries its provenance, and the clock counts WORK.

Three groups, three different questions:

  W4  kappa is measured in CPU-time, not wall-clock.  Wall-clock also counts the
      stretches where the process was set aside, so a busy machine inflates
      kappa without any extra work being done, and the cost table stops being
      reproducible between two runs.
  W1  pi0 is a CONSEQUENCE of how an episode is built, not a hand-picked
      constant; and it has exactly ONE source, because the tau_sel table is
      generated FROM it.
  W2  eta_Q exceeds kappa on every carrier, and is larger on the carrier whose
      quarantine has more live items to rebuild.

Spec: docs/design/plans/2026-09-22-W1-W10-tham-so.md (W1, W2, W4);
docs/AuditGame-SE_Parameter_Estimation_Report.md sections 5.2, 5.3, 5.6.
"""
from __future__ import annotations
import json
import pathlib
import time
import unittest

import costs
import runner
import scoring


class _SleepingDetector:
    """score() sleeps 50ms per item: costs wall-clock, costs almost no CPU."""
    d_prime = 1.0

    def score(self, item, t, seed):
        time.sleep(0.05)
        return 0.0


class TheAuditClockCountsWorkNotWaiting(unittest.TestCase):

    def test_sleeping_does_not_show_up_as_audit_cost(self):
        """Four items sleeping 50ms is 0.2s of wall-clock; CPU-time must be ~0.

        This is why kappa is timed with process_time: an audit's cost is the
        WORK it has to do, not the time that passed while it waited.
        """
        items = [object() for _ in range(4)]
        secs = runner._probe_seconds(_SleepingDetector(), items, t=0, seed=1)
        self.assertLess(secs, 0.05,
                        "four items sleeping 50ms is 0.2s wall-clock; "
                        "CPU-time must be near zero")

    def test_the_clock_still_counts_real_work(self):
        """The control for the test above: a detector doing real work must show.

        Without this one, `return 0.0` would also make the previous test pass.
        """
        class _BusyDetector:
            d_prime = 1.0

            def score(self, item, t, seed):
                s = 0.0
                for i in range(200_000):
                    s += i * 0.5
                return s

        secs = runner._probe_seconds(_BusyDetector(), [object()], t=0, seed=1)
        self.assertGreater(secs, 0.0, "the clock does not count real work either")


class Pi0IsDerivedNotAssigned(unittest.TestCase):

    def test_pi0_world_is_one_payload_over_the_live_items(self):
        self.assertAlmostEqual(costs.EXPECTED_ITEMS_TOTAL, 12.51, places=2)
        self.assertAlmostEqual(costs.PI0_WORLD, 1.0 / 12.51, places=4)

    def test_scoring_reads_pi0_from_costs_instead_of_keeping_its_own(self):
        self.assertIs(scoring.PI0, costs.PI0_WORLD)

    def test_the_model_prior_carries_the_attack_prior_of_the_belief(self):
        """Two roles, two numbers (rule R2 of the parameter estimation report).

        The WORLD's pi0 is the share of live items that were seeded in the
        injected arm; the pi0 the DEFENDER works with must also be multiplied by
        the probability that this episode is under attack at all.  Using one
        number for both silently tells the defender an attack is certain.
        """
        self.assertAlmostEqual(costs.PI0_MODEL,
                               costs.PI_ATTACK * costs.PI0_WORLD, places=9)
        self.assertLess(costs.PI0_MODEL, costs.PI0_WORLD)

    def test_the_frozen_table_was_generated_at_the_pi0_in_force(self):
        """The tau_sel table is a function of pi0.  If the two disagree, every
        carrier-selection threshold is being read off a table generated at a
        different prior."""
        path = pathlib.Path(scoring.__file__).parent / "reference" / "score_table.json"
        table = json.loads(path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(table["provenance"]["pi0"], scoring.PI0, places=6)


class QuarantineCostsMoreThanLooking(unittest.TestCase):

    def test_eta_q_exceeds_kappa_on_every_carrier(self):
        """Quarantine detaches the carrier from the loop AND rebuilds the clean
        part of it, so it cannot be cheaper than merely looking at that carrier.
        If it were, the optimal policy would quarantine instead of auditing and
        the benchmark would stop measuring allocation."""
        for c in costs.KAPPA_USD:
            self.assertGreater(costs.eta_q(c), costs.KAPPA_USD[c], c)

    def test_eta_q_is_higher_where_more_live_items_must_be_rebuilt(self):
        self.assertGreater(costs.eta_q("memory"), costs.eta_q("skill"))

    def test_eta_q_names_its_two_parts(self):
        """eta_Q = detach + restore.  The restore half is derived from n_live and
        the detach half is measured; a scalar eta_Q for all four carriers is a
        rounding that has to be declared, not a fact."""
        parts = costs.eta_q_parts("memory")
        self.assertEqual(set(parts), {"detach", "restore"})
        self.assertAlmostEqual(sum(parts.values()), costs.eta_q("memory"), places=12)


if __name__ == "__main__":
    unittest.main()
