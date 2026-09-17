"""
GATE 3 -- POWER for the d' sweep: "is there enough to conclude?"

Red here means the curve is real and about the right thing, but d'* cannot be
stated from it -- the interval behind it was computed on the wrong unit, or a
threshold was printed where the data never separated from zero.
"""
from __future__ import annotations
import math
import unittest

import agent
import dprime_sweep as S
import runner


class TheIntervalBehindTheThreshold(unittest.TestCase):

    N, H, SEEDS, BUDGET = 6, 4, (1, 2, 3), 17.95

    def test_the_break_even_ci_resamples_workflows_not_cases(self):
        """d'* rests on bootstrap_paired's WORKFLOW unit, untouched.

        Thesis claim (vi): "CI95 bang bootstrap_paired -- no lay lai mau THEO
        WORKFLOW; giu nguyen, dung doi don vi lay mau".

        Cases from one workflow share a task chain and the same clean-run outcome,
        so they are not independent.  Resampling by case gives a FALSELY NARROW
        interval, and a break-even read off a falsely narrow interval crosses zero
        earlier than the evidence allows -- the exact way a threshold gets
        overstated.
        """
        wfs = S.make_corpus(self.N, self.H, seed=2026)
        c = S.measure_cell(wfs, 2.0, 1, self.BUDGET, self.SEEDS)
        self.assertIsNone(c.reason, "the probe cell was not measurable")

        det, ag = S.make_detector(2.0), agent.MockAgent()
        cells = {}
        for name in (S.B1, S.SENTINEL):
            runner.reset_survivor_cache()
            cells[name] = runner.worst_case(name, wfs, (1,), S.CARRIERS, det, ag,
                                            self.BUDGET, self.SEEDS, S.SETTING)
        b1, sn = cells[S.B1], cells[S.SENTINEL]
        self.assertEqual(len(b1.per_wf), c.n_feasible,
                         "the CI was not computed over one entry per workflow")
        self.assertEqual((c.ci_lo, c.ci_hi),
                         runner.bootstrap_paired(b1.per_wf, sn.per_wf),
                         "the sweep's CI is not bootstrap_paired over the "
                         "per-workflow lists")

        # The unit is LOAD-BEARING: the same numbers resampled as if each workflow
        # were three independent cases give a strictly narrower interval.
        lo_case, hi_case = runner.bootstrap_paired(
            [x for x in b1.per_wf for _ in range(3)],
            [x for x in sn.per_wf for _ in range(3)])
        self.assertLess(hi_case - lo_case, c.ci_hi - c.ci_lo,
                        "resampling by case did not narrow the interval -- this "
                        "test can no longer tell the two units apart")

    def test_no_break_even_is_claimed_where_the_interval_never_leaves_zero(self):
        """An interval straddling zero everywhere supports NO threshold.

        Thesis claim (vi): "Sentinel giam hai khi va chi khi audit dat d' > d'*" --
        in a cell with no such d', the honest report is that there is none in this
        range, not the nearest number on the grid.
        """
        straddle = [S.SweepCell(d_prime=d, delta=0, harm_b1=1.0, harm_sentinel=0.95,
                                dharm=0.05, ci_lo=-0.04, ci_hi=+0.14,
                                n_feasible=40, n_total=40)
                    for d in S.GRID]
        self.assertIsNone(S.break_even(straddle),
                          "a threshold was reported from intervals that never "
                          "separated from zero")


class TheTableCarriesItsOwnEvidence(unittest.TestCase):
    """Gate 3 is enforced by FORMAT as well as by assertions: a curve printed
    without its denominators and its holes is not a results table."""

    def test_every_printed_harm_number_carries_its_feasible_denominator(self):
        """N3 at the level of the printed curve.

        Thesis claim (vi): "harm khong bao gio di mot minh" -- mot con so khong co
        mau so khong phai la ket qua bao cao duoc.
        """
        rows = [S.SweepCell(d_prime=1.0, delta=2, harm_b1=0.80, harm_sentinel=0.55,
                            dharm=0.25, ci_lo=0.10, ci_hi=0.40,
                            n_feasible=37, n_total=40)]
        out = S.table(rows)
        self.assertIn("0.250", out, "the d-harm number is missing")
        self.assertIn("37/40", out,
                      "a harm number was printed without its feasible denominator")

    def test_a_cell_with_no_measurement_prints_its_reason_instead_of_a_number(self):
        """A hole in the curve says WHY, in words, on the line where the number
        would have been.

        Thesis claim (vi): "o ngoai pham vi ghi LY DO, khong ghi harm = 0".

        Printing 0.000 there reads as "the defense held perfectly at this d'",
        which is the single most misleading thing this table could say.
        """
        rows = [S.SweepCell(d_prime=0.6, delta=4, harm_b1=float("nan"),
                            harm_sentinel=float("nan"), dharm=float("nan"),
                            ci_lo=float("nan"), ci_hi=float("nan"),
                            n_feasible=0, n_total=40,
                            reason="no attack could be built at Delta=4")]
        out = S.table(rows)
        self.assertIn("REASON:", out, "the hole was printed without its reason")
        self.assertIn("no attack could be built", out)
        self.assertNotIn("0.000", out,
                         "an unmeasured cell printed a harm number")
        self.assertNotIn("nan", out.lower(),
                         "an unmeasured cell leaked NaN into the table instead of "
                         "saying why it is empty")


if __name__ == "__main__":
    unittest.main()
