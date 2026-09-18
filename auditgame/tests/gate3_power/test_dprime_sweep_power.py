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
import metrics
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


class TheIntervalBehindTheLossThreshold(unittest.TestCase):
    """d'* under L rests on the SAME resampling unit as d'* under harm.  If the
    Q_false and T_lost terms entered without their own sampling variability -- as
    they would if the L interval were the harm interval shifted by a constant --
    the interval would be narrower than the evidence and the threshold would be
    read too low."""

    N, H, SEEDS, BUDGET = 6, 4, (1, 2, 3), 17.95

    def test_the_loss_ci_resamples_workflows_not_cases(self):
        """The L interval is bootstrap_paired over PER-WORKFLOW L, unit unchanged.

        Thesis claim (vi): "CI95 bang bootstrap_paired -- no lay lai mau THEO
        WORKFLOW; giu nguyen, dung doi don vi lay mau".
        """
        wfs = S.make_corpus(self.N, self.H, seed=2026)
        c = S.measure_cell(wfs, 2.0, 1, self.BUDGET, self.SEEDS)
        self.assertIsNone(c.reason, "the probe cell was not measurable")

        b1, sn = c.curves[S.B1], c.curves[S.SENTINEL]
        lq = metrics.LAMBDA_Q
        want = runner.bootstrap_paired(b1.per_wf_loss(lq), sn.per_wf_loss(lq))
        self.assertEqual(S.loss_interval(c, lq), want,
                         "the L interval is not bootstrap_paired over the "
                         "per-workflow L lists")
        self.assertEqual(len(b1.per_wf_loss(lq)), c.n_feasible,
                         "the L interval was not computed over one entry per "
                         "workflow")

    def test_the_loss_interval_is_not_the_harm_interval_shifted_by_a_constant(self):
        """The Q_false and T_lost terms carry their OWN sampling variability.

        Thesis claim (vi): "CI95 hep hon bang chung se day d'* xuong thap hon muc
        du lieu cho phep" -- do dung la cach mot nguong bi bao qua tay.

        Shifting the harm interval by the mean penalty difference would keep the
        WIDTH of the harm interval exactly.  Measuring per-workflow L keeps the
        per-workflow spread of Q_false and T_lost in the resample, so the widths
        differ.
        """
        wfs = S.make_corpus(self.N, self.H, seed=2026)
        c = S.measure_cell(wfs, 2.0, 1, self.BUDGET, self.SEEDS)
        lq = metrics.LAMBDA_Q
        lo, hi = S.loss_interval(c, lq)
        self.assertNotAlmostEqual(
            hi - lo, c.ci_hi - c.ci_lo, places=6,
            msg="the L interval has exactly the harm interval's width, so the "
                "penalty terms entered as a constant offset and contribute no "
                "uncertainty of their own")

    def test_a_cell_with_no_lambda_bar_prints_none_rather_than_a_substituted_weight(self):
        """The reader sees "none", not a number that was never measured.

        Thesis claim (vi): "lambda_q_star tra ve None thi GHI RO, khong thay bang
        mot con so".
        """
        rows = [S.SweepCell(d_prime=1.0, delta=2, harm_b1=0.80,
                            harm_sentinel=0.55, dharm=0.25, ci_lo=0.10, ci_hi=0.40,
                            n_feasible=37, n_total=40)]
        out = S.policy_table(rows)
        self.assertIn("none", out.lower(),
                      "a cell with no lambda-bar printed something other than "
                      "'none' in the lambda-bar column")


class TheSpendingTableSitsBesideTheResults(unittest.TestCase):
    """"Every policy runs on the same budget B" is true of the CAP and false of the
    SPEND.  metrics.spend_table has existed since B5 and was never called from the
    sweep, so a reader of the d' curve could not see that one policy declines to
    play."""

    def test_every_reported_policy_row_prints_what_it_actually_spent(self):
        """The four-policy table carries `spent` beside every L number.

        Thesis claim (vi): "MOI policy chay tren CUNG mot ngan sach B" -- dung voi
        TRAN, sai voi SO DA TIEU; mot bang L khong co cot spent doc nhu bon policy
        ngang gia nhau trong khi mot trong so do tieu 1/40.
        """
        import dprime_sweep as _S
        cur = {_S.B1: _S.PolicyCurve(0.80, 0.00, 0.45, 16.40, 37, 40,
                                     [0.80] * 37, [0.0] * 37, [0.45] * 37,
                                     [16.40] * 37),
               _S.SENTINEL: _S.PolicyCurve(0.55, 1.70, 0.00, 6.47, 37, 40,
                                           [0.55] * 37, [1.70] * 37, [0.0] * 37,
                                           [6.47] * 37),
               _S.B5: _S.PolicyCurve(0.78, 0.27, 0.00, 0.40, 37, 40,
                                     [0.78] * 37, [0.27] * 37, [0.0] * 37,
                                     [0.40] * 37),
               _S.B6: _S.PolicyCurve(0.72, 0.30, 0.00, 5.00, 37, 40,
                                     [0.72] * 37, [0.30] * 37, [0.0] * 37,
                                     [5.00] * 37)}
        rows = [S.SweepCell(d_prime=1.0, delta=2, harm_b1=0.80, harm_sentinel=0.55,
                            dharm=0.25, ci_lo=0.10, ci_hi=0.40, n_feasible=37,
                            n_total=40, curves=cur)]
        out = S.policy_table(rows)
        for spent in ("16.40", "6.47", "0.40", "5.00"):
            self.assertIn(spent, out,
                          f"the four-policy table dropped the spend {spent}")
        self.assertIn("37/40", out,
                      "a harm number was printed without its feasible denominator")

    def test_the_sweep_prints_the_metrics_spend_table_beside_the_curve(self):
        """metrics.spend_table is CALLED, at a declared grid point.

        Thesis claim (vi): "B5 dat toi harm cua B1 tren 0.40 cua ngan sach 17.95
        trong khi B1 tieu 16.40 va Sentinel 6.47" -- con so nay chi den duoc nguoi
        doc neu bang chi tieu duoc IN ra canh bang ket qua.

        The reference grid point is DECLARED (the grid point nearest mid's
        d' = 2.211, the operating point every frozen number in the thesis uses),
        not picked after seeing which one flatters a policy.
        """
        self.assertIn(S.SPEND_REFERENCE_D_PRIME, S.GRID,
                      "the declared spend reference d' is not on the grid")
        import detector
        d_mid = detector.operating_point(*detector.SETTINGS["mid"])[0]
        self.assertLessEqual(abs(S.SPEND_REFERENCE_D_PRIME - d_mid), 0.1,
                             "the declared spend reference d' is not the grid point "
                             "nearest mid's d'")

        cur = {n: S.PolicyCurve(0.5, 0.1, 0.0, s, 40, 40, [0.5] * 40, [0.1] * 40,
                                [0.0] * 40, [s] * 40)
               for n, s in ((S.B1, 16.40), (S.SENTINEL, 6.47),
                            (S.B5, 0.40), (S.B6, 5.00))}
        rows = [S.SweepCell(d_prime=S.SPEND_REFERENCE_D_PRIME, delta=2,
                            harm_b1=0.8, harm_sentinel=0.5, dharm=0.3, ci_lo=0.1,
                            ci_hi=0.5, n_feasible=40, n_total=40, curves=cur)]

        out = S.spend_report(rows, 17.95)
        self.assertIn("cap", out, "this is not metrics.spend_table's output")
        self.assertIn("16.40", out)
        self.assertIn("91%", out, "the % of cap used is missing (16.40/17.95)")
        self.assertIn("2%", out, "B5's 0.40 of a 17.95 cap is not reported")

    def test_a_refused_cell_prints_its_reason_instead_of_a_spend_table(self):
        """N3 reaches the spend table too.

        Thesis claim (vi): "mot o bi tu choi ghi LY DO, khong bao gio mot gia tri
        im lang" -- mot o co curve nhung KHONG dung duoc (vi du: hai policy giu so
        workflow khac nhau nen khong ghep cap duoc) van co `spent` huu han, nen mot
        bang chi tieu van in ra duoc tu no -- va se doc nhu mot phep do hop le o mot
        o ma khong so nao trong o do duoc bao cao.
        """
        cur = {n: S.PolicyCurve(0.5, 0.1, 0.0, s_, 12, 40, [0.5] * 12, [0.1] * 12,
                                [0.0] * 12, [s_] * 12)
               for n, s_ in ((S.B1, 16.40), (S.SENTINEL, 6.47),
                             (S.B5, 0.40), (S.B6, 5.00))}
        rows = [S.SweepCell(d_prime=S.SPEND_REFERENCE_D_PRIME, delta=2,
                            harm_b1=0.8, harm_sentinel=0.5, dharm=float("nan"),
                            ci_lo=float("nan"), ci_hi=float("nan"), n_feasible=12,
                            n_total=40, curves=cur,
                            reason="B1 kept 12 workflows and Sentinel 9: the "
                                   "paired CI has no pairing")]
        out = S.spend_report(rows, 17.95)
        self.assertIn("REASON", out,
                      "an unusable cell printed a spend table with nothing to say "
                      "that the cell itself carries no reportable measurement")
        self.assertIn("no pairing", out, "the reason text was dropped")
        self.assertNotIn("16.40", out,
                         "the spend table was printed anyway for a refused cell")


if __name__ == "__main__":
    unittest.main()
