"""
GATE 1 -- Stage 7: the two worked examples, computed by hand in the methodology
and recomputed here by the code the pipeline actually runs.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 7 ("Minimax 4x4 ->
deterministic 1.0, mixed 0.5.  Bayes 0.10 -> 0.44 -> 0.85.  If the hand matches
the code on the same small game, the pipeline is right and may be scaled"),
section 16 and Stage 5.

The point of a hand example is that it is checked by something OTHER than the
hand.  Until this file existed both were numbers in a document: the 4x4 matrix
was matched once by spikes/trace_one_episode.py and never pinned, and the Bayes
chain had no code path under it at all.  Both are now asked of the production
functions -- `game.minimax` and `scoring.posterior` -- not of a re-implementation
written for the test, which would only prove the test agrees with itself.
"""
from __future__ import annotations
import itertools
import unittest

import game
import scoring


# ---------------------------------------------------------------------------
# Section 16: K = 2, H = 4, Delta = 2, perfect detector, budget 2 audits.
# ---------------------------------------------------------------------------

#: Attacker pure strategies (carrier, iota, sigma), exactly as the document lists.
ATTACKS = {"a1": ("mem", 1, 3), "a2": ("mem", 2, 4),
           "a3": ("skill", 1, 3), "a4": ("skill", 2, 4)}
#: Defender schedules: which carrier is audited at task 2 and at task 3.
SCHEDULES = {"A": (("mem", 2), ("mem", 3)), "B": (("skill", 2), ("skill", 3)),
             "C": (("mem", 2), ("skill", 3)), "D": (("skill", 2), ("mem", 3))}
#: The harm matrix as the DOCUMENT prints it -- rows A..D, columns a1..a4.
DOCUMENT_MATRIX = [[0, 0, 1, 1],
                   [1, 1, 0, 0],
                   [0, 0, 1, 0],
                   [1, 0, 0, 0]]


def _harm(schedule, attack) -> int:
    """1 if the payload detonates uncaught.  Caught iff an audit hits the poisoned
    carrier at some t in the half-open window [iota, sigma) -- the document's rule,
    and the same half-open convention belief.WindowBelief.active uses."""
    k, iota, sigma = attack
    return 0 if any(c == k and iota <= t < sigma for c, t in schedule) else 1


def _derived_matrix():
    return [[_harm(SCHEDULES[r], ATTACKS[a]) for a in sorted(ATTACKS)]
            for r in sorted(SCHEDULES)]


class TheFourByFourMinimaxExample(unittest.TestCase):

    def test_the_printed_matrix_is_the_one_the_catch_rule_produces(self):
        """The document's worked example is only evidence if its table follows
        from its rule.  DERIVED here from the attack windows and schedules, not
        transcribed and then trusted.

        Measured: all 16 cells agree.  The ones that decide the example are
        C x a3 = 1 and D x a1 = 1 -- an audit at task 3 does NOT catch a payload
        live on [1, 3), because the window is half-open -- and a table built
        with a closed window would have printed 0 there and a value below 0.5.
        Compared cell by cell so a future edit to either side is named, not
        silently preferred.
        """
        derived = _derived_matrix()
        diff = [(r, a, DOCUMENT_MATRIX[i][j], derived[i][j])
                for i, r in enumerate(sorted(SCHEDULES))
                for j, a in enumerate(sorted(ATTACKS))
                if DOCUMENT_MATRIX[i][j] != derived[i][j]]
        self.assertEqual(diff, [], f"printed vs derived cells differ: {diff}")

    def test_every_deterministic_schedule_has_worst_case_one(self):
        worst = [max(row) for row in DOCUMENT_MATRIX]
        self.assertEqual(worst, [1, 1, 1, 1])

    def test_the_production_minimax_finds_value_one_half(self):
        v, mix = game.minimax(DOCUMENT_MATRIX, iters=20000)
        self.assertAlmostEqual(v, 0.5, places=2)
        # The document's certificate: rows B and D cover a1, rows A and C cover
        # a3, so max >= 0.5 for every mix -- no mix can beat 0.5.
        for w in itertools.product([i / 10 for i in range(11)], repeat=3):
            if sum(w) > 1:
                continue
            p = list(w) + [1 - sum(w)]
            cols = [sum(p[r] * DOCUMENT_MATRIX[r][c] for r in range(4))
                    for c in range(4)]
            self.assertGreaterEqual(max(cols) + 1e-9, 0.5, p)

    def test_mixing_c_and_d_half_and_half_reaches_the_value(self):
        p = [0, 0, 0.5, 0.5]
        cols = [sum(p[r] * DOCUMENT_MATRIX[r][c] for r in range(4)) for c in range(4)]
        self.assertEqual(cols, [0.5, 0, 0.5, 0])


# ---------------------------------------------------------------------------
# Stage 5: Bernoulli alarms, (psi, phi) = (0.85, 0.12), p0 = 0.10.
# ---------------------------------------------------------------------------

PSI, PHI, P0 = 0.85, 0.12, 0.10


def _step(p: float, alarm: int) -> float:
    """One alarm through the PRODUCTION posterior.  A Bernoulli alarm's likelihood
    ratio is psi/phi when it fires and (1-psi)/(1-phi) when it does not; the Bayes
    step itself is scoring.posterior, the function every carrier score goes
    through -- so this checks the pipeline's arithmetic, not a copy of it."""
    lam = PSI / PHI if alarm else (1 - PSI) / (1 - PHI)
    return scoring.posterior(lam, pi0=p)


class TheBayesChainExample(unittest.TestCase):

    def test_one_alarm_takes_the_prior_from_0_10_to_0_44(self):
        self.assertAlmostEqual(_step(P0, 1), 0.085 / 0.193, places=6)
        self.assertEqual(round(_step(P0, 1), 2), 0.44)

    def test_a_second_alarm_takes_it_to_0_85(self):
        self.assertEqual(round(_step(_step(P0, 1), 1), 2), 0.85)

    def test_silence_takes_it_down_to_0_019(self):
        self.assertAlmostEqual(_step(P0, 0), 0.019, places=3)

    def test_with_tau_0_8_quarantine_needs_two_alarms(self):
        """The document's operational reading, and the one worth pinning: one
        alarm is never enough at tau = 0.8, two always are."""
        self.assertLess(_step(P0, 1), 0.8)
        self.assertGreater(_step(_step(P0, 1), 1), 0.8)


if __name__ == "__main__":
    unittest.main()
