"""
GATE 2 -- VALIDITY for the break-even d'*: "what is that number about?"

Red here means the sweep's numbers are REAL but d'* is about something other than
what the thesis says it is -- a noise crossing, a pooled average, a cell where no
attack existed, or a curve whose false-alarm rate moved underneath it.
"""
from __future__ import annotations
import math
import unittest

import agent
import dprime_sweep as S
import detector
import runner
import scoring


def cell(d_prime, delta, ci_lo, ci_hi=None, dharm=None, reason=None):
    """A SYNTHETIC cell -- the break-even rule is a rule about a list of bounds and
    is tested as one, so a rule defect cannot hide behind a 40-workflow run."""
    ci_hi = ci_lo + 0.5 if ci_hi is None else ci_hi
    dharm = (ci_lo + ci_hi) / 2 if dharm is None else dharm
    return S.SweepCell(d_prime=d_prime, delta=delta, harm_b1=1.0,
                       harm_sentinel=1.0 - dharm, dharm=dharm,
                       ci_lo=ci_lo, ci_hi=ci_hi, n_feasible=40, n_total=40,
                       reason=reason)


class BreakEvenRule(unittest.TestCase):

    def test_break_even_rejects_a_lone_positive_point_below_a_later_negative_one(self):
        """A crossing that does not HOLD is not a threshold.

        Thesis claim (vi): "d'* la d' NHO NHAT ma tu do tro len can duoi CI95 > 0
        VA GIU DUOC nhu vay o moi d' lon hon trong luoi".

        The "and stays" clause exists to stop a noise crossing being reported as
        the threshold.  Here the bound is positive at 0.6, negative again at 1.0,
        and positive from 1.4 up: a first-crossing rule answers 0.6, and 0.6 is a
        dice roll.  The answer is 1.4.
        """
        rows = [cell(0.2, 1, -0.10), cell(0.6, 1, +0.03), cell(1.0, 1, -0.02),
                cell(1.4, 1, +0.05), cell(1.8, 1, +0.09), cell(2.2, 1, +0.14)]
        self.assertEqual(S.break_even(rows), 1.4,
                         "break_even reported the first crossing instead of the "
                         "smallest d' from which the bound STAYS above zero")

    def test_break_even_is_the_smallest_d_prime_of_the_holding_run_not_the_largest(self):
        """The threshold is where the advantage STARTS, not where it is safest.

        Thesis claim (vi): "Sentinel giam hai KHI VA CHI KHI audit dat d' > d'*".

        A rule that returned the top of the run would be trivially "correct" on
        every monotone curve and would say nothing; this pins the direction.
        """
        rows = [cell(0.4, 2, -0.01), cell(0.8, 2, +0.02),
                cell(1.2, 2, +0.06), cell(1.6, 2, +0.11)]
        self.assertEqual(S.break_even(rows), 0.8)

    def test_a_cell_where_no_attack_could_be_built_carries_a_reason_and_no_harm_zero(self):
        """N3: an absent measurement is not "the defense held".

        Thesis claim (vi): "o khong dung duoc attack thi ghi LY DO, khong ghi
        harm = 0, va LOAI KHOI trung binh".

        Delta = 99 on H = 4 tasks: plan_poison has no sigma to pick, so no workflow
        yields an attack at all.  harm = 0.0 there would read as a perfect defense
        and would drag every average toward it.
        """
        wfs = S.make_corpus(4, 4, seed=2026)
        c = S.measure_cell(wfs, 2.0, 99, 17.95, (1,))
        self.assertIsNotNone(c.reason, "an infeasible cell reported a number")
        self.assertIn("no attack", c.reason)
        self.assertEqual(c.n_feasible, 0)
        self.assertTrue(math.isnan(c.dharm),
                        f"infeasible cell reported d-harm {c.dharm} instead of NaN "
                        "-- 0.0 here would read as 'the defense held'")
        self.assertFalse(c.usable, "an infeasible cell must be excluded, not averaged")

    def test_an_infeasible_cell_breaks_the_break_even_run_instead_of_being_skipped(self):
        """A gap in the grid cannot support "and stays above zero".

        Thesis claim (vi): "o khong dung duoc attack ... LOAI KHOI trung binh" --
        and therefore out of the evidence for the threshold too.

        Silently skipping the hole would let a run of positive bounds reach ACROSS
        a d' at which nothing was measured, and d'* would claim evidence that does
        not exist.
        """
        rows = [cell(1.0, 1, +0.05), cell(1.4, 1, 0.0, reason="nothing to attack"),
                cell(1.8, 1, +0.09), cell(2.2, 1, +0.12)]
        self.assertEqual(S.break_even(rows), 1.8,
                         "break_even jumped over a cell with no measurement in it")


class OneDimensionalParameterisation(unittest.TestCase):

    def test_the_sweep_holds_the_false_alarm_rate_fixed_at_every_point_of_the_grid(self):
        """Only psi moves along the curve; phi does not.

        Thesis claim (vi): "quet mot chieu dung nghia -- ti le bao dong gia
        phi = Phi(-tau_det) khong doi, chi ti le phat hien psi = Phi(d'-tau_det) chay".

        The three declared settings move psi AND phi together, so a difference
        between two of them cannot be attributed to either.  If phi drifted along
        this sweep, d'* would be a threshold on two quantities at once and the
        restated claim would be false as written.
        """
        phis = {round(S.make_detector(d).phi, 12) for d in S.GRID}
        self.assertEqual(len(phis), 1,
                         f"phi moved along the sweep: {sorted(phis)}")
        self.assertAlmostEqual(phis.pop(), detector.SETTINGS["mid"][1], places=9,
                               msg="the sweep's fixed phi is not mid's phi = 0.12")
        psis = [S.make_detector(d).psi for d in S.GRID]
        self.assertEqual(len(set(psis)), len(S.GRID),
                         "psi did not move -- nothing is being swept")
        self.assertTrue(all(a < b for a, b in zip(psis, psis[1:])),
                        "psi is not increasing in d'")

    def test_the_grid_is_declared_as_sixteen_points_from_zero_to_three_step_two_tenths(self):
        """The grid is a FIXED declaration, not something chosen after seeing a curve.

        Thesis claim (vi): "Luoi quet: d' in {0,0 . 0,2 . ... . 3,0} (buoc 0,2,
        16 diem)" -- chot truoc, dung chon sau khi thay so.
        """
        self.assertEqual(len(S.GRID), 16)
        self.assertEqual(S.GRID[0], 0.0)
        self.assertEqual(S.GRID[-1], 3.0)
        self.assertTrue(all(abs((b - a) - 0.2) < 1e-9
                            for a, b in zip(S.GRID, S.GRID[1:])))


class TauSelFollowsTheSweptDPrime(unittest.TestCase):
    """The declared confound of the sweep, and the switch that removes it.

    `setting` is the key into the FROZEN tau_sel table.  Pinning it to "mid" at
    every swept d' leaves the carrier-selection threshold calibrated at d' = 2.211
    while the detector runs somewhere else entirely -- a real confound at the two
    ends of the grid.  With d'-keyed rows in the table there is a second mode in
    which the threshold follows the sweep."""

    def test_the_default_mode_still_reads_the_frozen_mid_row_at_every_grid_point(self):
        """Default behaviour is UNCHANGED, so the published curve reproduces.

        Thesis claim (vi): "quet nay giu setting='mid' o moi d'" -- so cu phai tai
        lap duoc DUNG NHU DA IN; che do moi la mot phep do THEM, khong phai mot
        phep do thay the.
        """
        for dp in S.GRID:
            with self.subTest(d_prime=dp):
                self.assertEqual(S.setting_for(dp), S.SETTING)
        self.assertEqual(S.SETTING, "mid")

    def test_the_following_mode_reads_the_tau_sel_row_calibrated_at_the_swept_d_prime(self):
        """One name per grid point, and the name resolves to a real table row.

        Thesis claim (vi): "go confound bang cach tra tau_sel o DUNG d' dang
        quet, khong phai o d' cua mid".

        scoring.tau_sel is a plain dict lookup by setting NAME, so a format drift
        between the generator's names and the sweep's names is a KeyError in the
        middle of a 20-minute run.  Both ends are pinned here.
        """
        for dp in S.GRID:
            name = S.setting_for(dp, tau_follows_dprime=True)
            with self.subTest(d_prime=dp):
                self.assertEqual(name, f"d{dp:.1f}")
                self.assertIsInstance(scoring.tau_sel(9, name, 1), float)

    def test_following_the_sweep_actually_moves_the_threshold_away_from_mid(self):
        """The switch has to CHANGE something, or it removes no confound.

        Thesis claim (vi): "bang tau_sel duoc hieu chinh THEO d'" -- neu nguong o
        d' = 0.4 bang nguong o d' = 2.211 thi khong co confound nao de go, va ca
        phep do nay vo nghia.
        """
        far = 0.4
        follows = scoring.tau_sel(9, S.setting_for(far, tau_follows_dprime=True), 1)
        pinned = scoring.tau_sel(9, S.setting_for(far), 1)
        self.assertNotAlmostEqual(
            follows, pinned, places=3,
            msg=f"tau_sel at d'={far} is the same whether or not it follows the "
                f"sweep ({follows}) -- the confound this mode removes does not exist")


class TheDeclaredConfoundIsInertForThisDeltaHarmPair(unittest.TestCase):
    """The measured answer to "how much did the pinned tau_sel cost us".

    Policy.tau -- the ONLY caller of scoring.tau_sel -- is consulted by B5
    risk-score and B6 two-stage and by nobody else.  Neither policy of the pair
    Delta-harm is defined through (B1 audit-at-commit, Sentinel) ever reads it, so
    the confound the module docstring declares cannot move the number the module
    reports.  That is a structural fact and it is pinned here, because it is the
    reason --tau-follows-dprime reproduces the default curve exactly.
    """

    #: d' = 1.0 at Delta = 4 on 10 workflows -- a cell where B5 DOES move, so the
    #: probe is known to be sensitive before it is used to claim insensitivity.
    N, H, D_PRIME, DELTA, SEEDS, BUDGET = 10, 8, 1.0, 4, (1, 2, 3), 17.95

    def _harm(self, policy: str, setting: str) -> float:
        wfs = S.make_corpus(self.N, self.H, seed=2026)
        runner.reset_survivor_cache()
        return runner.worst_case(policy, wfs, (self.DELTA,), S.CARRIERS,
                                 S.make_detector(self.D_PRIME), agent.MockAgent(),
                                 self.BUDGET, self.SEEDS, setting).harm

    def test_a_policy_that_reads_tau_sel_does_move_when_the_row_changes(self):
        """The control.  Without it the next test proves nothing.

        Thesis claim (vi): "bang tau_sel duoc hieu chinh theo d'" -- neu doi hang
        tau_sel ma KHONG policy nao nhuc nhich thi phep so sanh hai che do la mot
        phep do chet, chu khong phai mot ket luan.
        """
        pinned = self._harm("B5 risk-score", "mid")
        following = self._harm("B5 risk-score", "d0.0")
        self.assertNotEqual(pinned, following,
                            "B5 risk-score reads tau_sel through Policy.tau and "
                            "must respond to a different row; this probe cell is "
                            "no longer sensitive and the next test is vacuous")

    def test_neither_policy_of_the_delta_harm_pair_reads_the_tau_sel_row(self):
        """B1 and Sentinel are INSENSITIVE to the tau_sel row, so Delta-harm is.

        Thesis claim (vi): "confound tau_sel dong bang o mid ... CO THE gop phan
        vao chieu di xuong o Delta=0" -- do la mot GIA THUYET, va o day no bi bac
        bang cau truc: Policy.tau chi duoc B5/B6 goi.

        If this ever goes red, the sweep's declared confound has become LIVE for
        the pair it reports, and every --tau-follows-dprime number has to be
        re-read as a different measurement rather than a reproduction.
        """
        for policy in (S.B1, S.SENTINEL):
            with self.subTest(policy=policy):
                self.assertEqual(self._harm(policy, "mid"),
                                 self._harm(policy, "d0.0"),
                                 f"{policy} moved when only the tau_sel row "
                                 f"changed -- it now reads the frozen table")


class ReportOnTheGridDoNotPool(unittest.TestCase):

    def test_break_even_is_computed_per_delta_cell_and_never_over_the_pooled_grid(self):
        """One d'* per Delta, because the cells disagree.

        Thesis claim (vi): "bao cao TREN LUOI, khong gop" -- mot con so gop se
        trung binh vung phuong phap CO loi voi vung KHONG.

        Delta=0 never separates from zero here and Delta=4 separates from 0.4.
        Pooling the two lists into one call hides both facts behind a single
        number; the sweep must answer per cell.
        """
        d0 = [cell(0.4, 0, -0.06), cell(1.2, 0, -0.04), cell(2.0, 0, -0.01)]
        d4 = [cell(0.4, 4, +0.05), cell(1.2, 4, +0.12), cell(2.0, 4, +0.20)]
        self.assertIsNone(S.break_even(d0),
                          "Delta=0 has no break-even and must not be given one")
        self.assertEqual(S.break_even(d4), 0.4)
        self.assertNotEqual(S.break_even(d0), S.break_even(d4),
                            "the two Delta cells were collapsed into one answer")

    def test_a_non_monotone_curve_is_reported_as_non_monotone_and_not_smoothed(self):
        """Non-monotone in d' is a RESULT, not a defect to smooth away.

        Thesis claim (vi): "Neu Delta-harm KHONG don dieu theo d' thi BAO DUNG NHU
        VAY -- do la mot ket qua, khong phai loi can lam muot".
        """
        rising = [cell(0.4, 1, 0.0, dharm=0.01), cell(0.8, 1, 0.0, dharm=0.05),
                  cell(1.2, 1, 0.0, dharm=0.09)]
        dipping = [cell(0.4, 1, 0.0, dharm=0.01), cell(0.8, 1, 0.0, dharm=0.09),
                   cell(1.2, 1, 0.0, dharm=0.05)]
        self.assertTrue(S.is_monotone(rising))
        self.assertFalse(S.is_monotone(dipping),
                         "a curve that falls back was reported as monotone")


class RefinementIsDeclaredNotInterpolated(unittest.TestCase):

    def test_refinement_re_measures_inside_the_bracket_instead_of_interpolating(self):
        """A finer d'* comes from MEASURING the bracket, never from a straight line.

        Thesis claim (vi): "Neu vung cat 0 nam giua hai diem thi MIN HOA CUC BO
        quanh do (buoc 0,05), dung noi suy tuyen tinh roi bao mot con so gia do
        chinh xac".

        d'* = 1.4 means the crossing lies in (1.2, 1.4]; the points to add are
        exactly 1.25, 1.30, 1.35 -- the open interval, at step 0.05.
        """
        self.assertEqual(S.refinement_points(1.4), (1.25, 1.30, 1.35))

    def test_there_is_nothing_to_refine_when_the_grid_has_no_break_even(self):
        """No crossing, no bracket, no invented precision.

        Thesis claim (vi): "dung noi suy tuyen tinh roi bao mot con so gia do
        chinh xac".
        """
        self.assertEqual(S.refinement_points(None), ())
        self.assertEqual(S.refinement_points(0.0), (),
                         "d'* at the bottom of the grid has nothing measured below "
                         "it, so there is no bracket to refine")


if __name__ == "__main__":
    unittest.main()
