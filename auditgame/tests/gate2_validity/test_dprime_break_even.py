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
import metrics
import runner
import scoring


def cell(d_prime, delta, ci_lo, ci_hi=None, dharm=None, reason=None, curves=None):
    """A SYNTHETIC cell -- the break-even rule is a rule about a list of bounds and
    is tested as one, so a rule defect cannot hide behind a 40-workflow run."""
    ci_hi = ci_lo + 0.5 if ci_hi is None else ci_hi
    dharm = (ci_lo + ci_hi) / 2 if dharm is None else dharm
    return S.SweepCell(d_prime=d_prime, delta=delta, harm_b1=1.0,
                       harm_sentinel=1.0 - dharm, dharm=dharm,
                       ci_lo=ci_lo, ci_hi=ci_hi, n_feasible=40, n_total=40,
                       reason=reason, curves=curves or {})


def curve(harm, q_false, t_lost, spent, per_wf_harm=None, n_total=40):
    """A SYNTHETIC per-policy curve.  The per-workflow vectors are CONSTANT unless
    given, so the bootstrap over them is a point and the L arithmetic under test is
    not hidden behind resampling noise."""
    per_wf_harm = [harm] * n_total if per_wf_harm is None else list(per_wf_harm)
    k = len(per_wf_harm)
    return S.PolicyCurve(harm=sum(per_wf_harm) / k, q_false=q_false, t_lost=t_lost,
                         spent=spent, n_feasible=k, n_total=n_total,
                         per_wf_harm=per_wf_harm,
                         per_wf_q_false=[q_false] * k,
                         per_wf_t_lost=[t_lost] * k,
                         per_wf_spent=[spent] * k)


def four(b1, sentinel, b5, b6):
    """{policy -> PolicyCurve} over EXACTLY the four policies the frame decision
    is taken over, spelled with the REGISTRY keys."""
    return {S.B1: b1, S.SENTINEL: sentinel, S.B5: b5, S.B6: b6}


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

    def test_a_refined_cell_reads_the_same_tau_sel_row_as_the_coarse_pass(self):
        """A refinement point must not fall back to `mid` while the grid follows d'.

        Thesis claim (vi): "go confound bang cach tra tau_sel o DUNG d' dang
        quet, khong phai o d' cua mid".

        The two-phase run is not reachable from today's CLI (--tau-follows-dprime
        forces refinement off), so no published number is affected.  It is pinned
        anyway because the failure mode is SILENT: an unthreaded refinement pass
        appends d'-row cells measured at the `mid` row into the same table as the
        coarse pass, and nothing anywhere would say so.  Threaded, the refinement
        point 1.30 asks for a row the table does not have and the run dies with a
        KeyError -- which is the correct outcome, not a defect.
        """
        recorded = []

        def spy(wfs, d_prime, delta, budget, seeds, carriers=S.CARRIERS, ag=None,
                setting=S.SETTING):
            recorded.append((d_prime, setting))
            return cell(d_prime, delta, +0.1)

        rows = {2: [cell(1.2, 2, -0.1), cell(1.4, 2, +0.1)]}
        original = S.measure_cell
        S.measure_cell = spy
        try:
            S.refine_brackets(rows, [], 17.95, (1,), tau_follows_dprime=True)
            following = list(recorded)
            recorded.clear()
            rows = {2: [cell(1.2, 2, -0.1), cell(1.4, 2, +0.1)]}
            S.refine_brackets(rows, [], 17.95, (1,), tau_follows_dprime=False)
            pinned = list(recorded)
        finally:
            S.measure_cell = original

        self.assertEqual([dp for dp, _ in following], [1.25, 1.30, 1.35],
                         "refinement no longer measures the open bracket")
        for dp, setting in following:
            self.assertEqual(setting, S.setting_for(dp, tau_follows_dprime=True),
                             f"the refined cell at d'={dp} was measured at row "
                             f"{setting!r}: the refinement pass mixes coarse rows "
                             f"with mid-row cells in ONE table, silently")
        self.assertNotIn("d1.3", scoring.load_table()["tables"],
                         "the table gained a row at an odd tenth, so a refined "
                         "run no longer fails loudly on a missing row")
        self.assertEqual([setting for _, setting in pinned], [S.SETTING] * 3,
                         "the default mode stopped reading the frozen `mid` row")


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


class TheSweepIsScoredWithTheDeclaredLossNotHarmAlone(unittest.TestCase):
    """The sweep reported d-harm and called it the defender's advantage.  The
    DECLARED objective (De-cuong II.7.3, metrics.loss) is

        L = E[harm] + lambda_Q E[Q_false] + lambda_T E[T_lost]

    and Sentinel buys its harm advantage by quarantining more.  A d'* read off
    harm alone is a threshold on ONE TERM of a three-term objective, and the
    ranking it reports can reverse inside the plausible range of lambda_Q.  These
    tests are about WHAT THE NUMBER IS ABOUT, which is why they live in gate 2."""

    def test_the_sweep_measures_all_four_policies_the_frame_decision_is_taken_over(self):
        """B5 and B6 are in the cell, not only the pair d-harm is defined through.

        Thesis claim (vi): "so sanh phai chay tren CUNG mot ngan sach va CUNG mot
        detector cho MOI policy" -- mot bang chi co B1 va Sentinel khong tra loi
        duoc "Sentinel co hon B5/B6 khong", va hai cai dat doc lap deu bao B6 hon
        Sentinel duoi L.

        The keys are the REGISTRY keys verbatim; a renamed policy is a KeyError at
        measurement time rather than a silently missing column.
        """
        self.assertEqual(tuple(S.POLICIES), (S.B1, S.SENTINEL, S.B5, S.B6))
        import policies as P
        for name in S.POLICIES:
            with self.subTest(policy=name):
                self.assertIn(name, P.REGISTRY,
                              f"{name!r} is not a REGISTRY key -- the sweep would "
                              f"measure a policy that does not exist")

        wfs = S.make_corpus(4, 4, seed=2026)
        c = S.measure_cell(wfs, 2.0, 1, 17.95, (1,))
        self.assertEqual(sorted(c.curves), sorted(S.POLICIES),
                         "the measured cell does not carry all four policies")

    def test_delta_loss_is_the_three_term_loss_differenced_over_the_reported_pair(self):
        """Delta-L is L(B1) - L(Sentinel), with metrics.loss doing the arithmetic.

        Thesis claim (vi): "ham mat mat khai bao la L = harm + lambda_Q Q_false +
        lambda_T T_lost" -- neu phep quet cham diem bang harm thi no dang tra loi
        mot cau hoi KHAC voi cau hoi luan van dat ra.

        Hand-built so the direction cannot silently flip: Sentinel is better on
        harm (0.30 against 0.80) and worse on Q_false (1.70 against 0.00), which is
        exactly the trade the loss exists to price.
        """
        c = cell(2.0, 2, +0.10, curves=four(
            b1=curve(0.80, 0.00, 0.45, 16.40),
            sentinel=curve(0.30, 1.70, 0.00, 6.47),
            b5=curve(0.78, 0.27, 0.00, 0.40),
            b6=curve(0.72, 0.30, 0.00, 5.00)))

        for lq in (0.0, 0.05, metrics.LAMBDA_Q):
            with self.subTest(lambda_Q=lq):
                want = (metrics.loss(0.80, 0.00, 0.45, lq, metrics.LAMBDA_T)
                        - metrics.loss(0.30, 1.70, 0.00, lq, metrics.LAMBDA_T))
                self.assertAlmostEqual(S.dloss(c, lq), want, places=12)

        self.assertGreater(S.dloss(c, 0.0), 0.0,
                           "at lambda_Q = 0 Sentinel must still be ahead -- this "
                           "fixture no longer exhibits the trade under test")
        self.assertLess(S.dloss(c, 0.40), S.dloss(c, 0.0),
                        "Delta-L does not fall as the false-quarantine weight "
                        "rises: the Q_false term is not reaching the number")

    def test_the_break_even_rule_applied_to_loss_is_the_SAME_frozen_rule(self):
        """d'* under L is break_even() on L-cells, not a second rule.

        Thesis claim (vi): "d'* = d' NHO NHAT ma tu do tro len can duoi CI95 > 0 VA
        GIU DUOC" -- dinh nghia nay da CHOT; cham diem bang L khong duoc phep keo
        theo mot luat tom tat moi, vi du an da mot lan bi bong vi chon luat sau khi
        nhin so lieu (finding P7).

        Same shape as the harm test above it: a lone positive bound at 0.6 must not
        be reported when the bound goes negative again at 1.0.
        """
        def c_at(dp, sen_harm):
            return cell(dp, 2, -9.0, curves=four(
                b1=curve(0.80, 0.00, 0.00, 16.40),
                sentinel=curve(sen_harm, 0.00, 0.00, 6.47),
                b5=curve(0.78, 0.27, 0.00, 0.40),
                b6=curve(0.72, 0.30, 0.00, 5.00)))

        rows = [c_at(0.2, 0.90), c_at(0.6, 0.77), c_at(1.0, 0.85),
                c_at(1.4, 0.75), c_at(1.8, 0.71), c_at(2.2, 0.66)]
        self.assertEqual(S.break_even_loss(rows, 0.0), 1.4,
                         "d'* under L reported the first crossing instead of the "
                         "smallest d' from which the bound STAYS above zero")
        self.assertEqual(S.break_even_loss(rows, 0.0),
                         S.break_even(S.as_loss_cells(rows, 0.0)),
                         "break_even_loss is not the frozen break_even rule "
                         "applied to the L-differenced cells")

    def test_a_cell_that_carries_a_reason_still_carries_it_under_the_loss_scoring(self):
        """N3 survives the change of score.

        Thesis claim (vi): "o khong dung duoc attack thi ghi LY DO, khong ghi
        harm = 0, va LOAI KHOI trung binh" -- doi truc cham diem tu harm sang L
        khong duoc bien mot o TRONG thanh mot o co so.
        """
        rows = [cell(1.0, 1, +0.05, curves=four(
                    curve(0.8, 0, 0, 16.4), curve(0.3, 1.7, 0, 6.5),
                    curve(0.8, 0.3, 0, 0.4), curve(0.7, 0.3, 0, 5.0))),
                cell(1.4, 1, 0.0, reason="nothing to attack")]
        shadow = S.as_loss_cells(rows, 0.0)
        self.assertEqual([c.reason for c in shadow][1], "nothing to attack")
        self.assertFalse(shadow[1].usable,
                         "an infeasible cell became usable once scored with L")
        self.assertEqual(S.break_even_loss(rows, 0.0), None,
                         "the L scan jumped over a cell with no measurement in it")

    def test_lambda_bar_is_computed_from_the_four_policy_cell_and_never_assumed(self):
        """lambda-bar is metrics.lambda_q_star over the cell's own four policies.

        Thesis claim (vi): "lambda_Q KHONG duoc chon -- no duoc BAO CAO:
        lambda_q_star la trong so ma thu hang doi chu" -- mot con so gan cung o day
        bien ket qua thanh mot phat bieu ve chinh con so do.

        Pinned against metrics.lambda_q_star directly, so the sweep cannot grow its
        own copy of the crossing solver.
        """
        cur = four(b1=curve(0.80, 0.00, 0.45, 16.40),
                   sentinel=curve(0.30, 1.70, 0.00, 6.47),
                   b5=curve(0.78, 0.27, 0.00, 0.40),
                   b6=curve(0.72, 0.30, 0.00, 5.00))
        c = cell(2.0, 2, +0.10, curves=cur)
        want = metrics.lambda_q_star({k: (v.harm, v.q_false, v.t_lost)
                                      for k, v in cur.items()},
                                     lambda_T=metrics.LAMBDA_T)
        self.assertIsNotNone(want, "this fixture has no ranking flip, so it cannot "
                                   "test that lambda-bar is reported")
        self.assertAlmostEqual(S.lambda_bar(c), want, places=12)
        self.assertEqual(S.l_winners(c, 0.0), [S.SENTINEL],
                         "at lambda_Q = 0 the fixture's SOLE winner is not "
                         "Sentinel, so the flip this measures is about some other "
                         "pair")
        self.assertNotIn(S.SENTINEL, S.l_winners(c, want + 1e-6),
                         "the winner did not change at lambda-bar")

    def test_a_cell_with_no_lambda_bar_says_so_instead_of_being_given_a_number(self):
        """metrics.lambda_q_star returning None is an ANSWER, not a missing value.

        Thesis claim (vi): "lambda_q_star tra ve None neu khong trong so nao doi
        thu hang" -- thay None bang 0, bang 0.10, hay bang trung binh cua cac o
        khac la bia mot trong so va bao cao no nhu mot ket qua do duoc.

        Here Sentinel dominates on every term, so no weight can unseat it and the
        own-lambda-bar column has no weight to score this cell at.  N3 applies: the
        cell records WHY it is absent from that column, it is not skipped.
        """
        dominant = four(b1=curve(0.80, 0.90, 0.45, 16.40),
                        sentinel=curve(0.30, 0.10, 0.00, 6.47),
                        b5=curve(0.78, 0.50, 0.20, 0.40),
                        b6=curve(0.72, 0.60, 0.30, 5.00))
        c = cell(2.0, 2, +0.10, curves=dominant)
        self.assertIsNone(S.lambda_bar(c),
                          "this fixture does have a ranking flip, so it cannot "
                          "test the None path")

        shadow = S.as_loss_cells_at_own_lambda_bar([c])[0]
        self.assertIsNotNone(shadow.reason,
                             "a cell with no lambda-bar was scored anyway -- at "
                             "which weight?")
        self.assertIn("lambda", shadow.reason.lower())
        self.assertFalse(shadow.usable)
        self.assertIsNone(S.break_even_loss_at_own_lambda_bar([c]),
                          "a d'* was reported from a grid whose weight does not "
                          "exist")

    def test_the_three_declared_lambda_q_columns_are_zero_lambda_bar_and_the_default(self):
        """Three columns, declared: 0, the cell's own lambda-bar, metrics.LAMBDA_Q.

        Thesis claim (vi): "bao cao o BA muc lambda_Q: 0, lambda_q_star, 0.10;
        lambda_Q = 0 va 0.10 la MINH HOA, khong bao gio la dong tit" -- mot bang
        chi co mot cot lambda_Q lai tro thanh mot phat bieu ve dung trong so do.

        0.10 is read off metrics.LAMBDA_Q rather than pasted, so the column cannot
        drift away from the weight metrics.py declares.
        """
        rows = [cell(dp, 2, -9.0, curves=four(
                    b1=curve(0.80, 0.00, 0.00, 16.40),
                    sentinel=curve(0.80 - 0.05 * i, 1.70, 0.00, 6.47),
                    b5=curve(0.78, 0.27, 0.00, 0.40),
                    b6=curve(0.72, 0.30, 0.00, 5.00)))
                for i, dp in enumerate(S.GRID)]
        cols = S.loss_break_evens(rows)
        self.assertEqual(list(cols), [S.LQ_ZERO, S.LQ_BAR, S.LQ_DEFAULT],
                         "the three declared lambda_Q columns are not the ones "
                         "reported, or they are not in the declared order")
        self.assertIn("0.1", S.LQ_DEFAULT)
        self.assertEqual(cols[S.LQ_ZERO], S.break_even_loss(rows, 0.0))
        self.assertEqual(cols[S.LQ_DEFAULT],
                         S.break_even_loss(rows, metrics.LAMBDA_Q))
        self.assertEqual(cols[S.LQ_BAR], S.break_even_loss_at_own_lambda_bar(rows))
        self.assertNotEqual(cols[S.LQ_ZERO], cols[S.LQ_DEFAULT],
                            "the two illustration columns agree on this fixture, "
                            "so it cannot show that the weight matters")

    def test_scoring_with_the_loss_does_not_move_the_harm_break_even(self):
        """The harm curve is ADDED TO, never replaced.

        Thesis claim (vi): "phep do nay la CONG THEM -- khong lam xe dich bat ky
        con so da dong bang nao": duong cong harm da cong bo (d'* = none / none /
        2.55 / 0.60) phai tai lap nguyen ven sau khi bang duoc cham diem bang L.
        """
        rows = [cell(0.2, 1, -0.10), cell(0.6, 1, +0.03), cell(1.0, 1, -0.02),
                cell(1.4, 1, +0.05), cell(1.8, 1, +0.09), cell(2.2, 1, +0.14)]
        before = [(c.dharm, c.ci_lo, c.ci_hi) for c in rows]
        S.as_loss_cells(rows, metrics.LAMBDA_Q)
        S.break_even_loss(rows, metrics.LAMBDA_Q)
        self.assertEqual([(c.dharm, c.ci_lo, c.ci_hi) for c in rows], before,
                         "the L scoring mutated the harm cells it was handed")
        self.assertEqual(S.break_even(rows), 1.4,
                         "the harm break-even moved once L scoring existed")


class ATieForTheBestLossIsReportedAsATieAndNotAsAWin(unittest.TestCase):
    """Found in self-review, not by a red test, so it is written down here.

    `min(cells, key=L)` breaks a tie by INSERTION ORDER, and the cells are inserted
    in POLICIES order with Sentinel second.  On this corpus at lambda_Q = 0 a
    quarter of the grid has an exact tie -- at Delta = 0 every score-reading policy
    sits at harm 0.992 and T_lost 0.000, so their L(0) are equal to the last digit
    -- and a bare min() hands every one of those to Sentinel.  Counting those as
    Sentinel wins overstates the headline by nearly a factor of two."""

    def _tied(self):
        return cell(2.0, 0, +0.10, curves=four(
            b1=curve(1.20, 0.00, 0.40, 16.40),
            sentinel=curve(0.99, 1.12, 0.00, 7.13),
            b5=curve(0.99, 0.00, 0.00, 0.00),
            b6=curve(0.99, 1.03, 0.00, 3.20)))

    def test_every_policy_holding_the_minimum_loss_is_returned_not_just_the_first(self):
        """Three policies at the same L must come back as three.

        Thesis claim (vi): "thu hang duoi L phai doc duoc" -- mot o HOA khong phai
        mot o THANG, va thu tu chen dict khong duoc phep quyet dinh ai thang.
        """
        c = self._tied()
        self.assertEqual(sorted(S.l_winners(c, 0.0)),
                         sorted([S.SENTINEL, S.B5, S.B6]),
                         "a three-way tie for the smallest L was reported as one "
                         "winner")
        self.assertEqual(S.l_winners(c, metrics.LAMBDA_Q), [S.B5],
                         "the tie does not break at lambda_Q = 0.10, so this "
                         "fixture cannot show a tie being broken by the weight")

    def test_the_printed_table_shows_the_tie_rather_than_naming_one_policy(self):
        """A reader of the table must see the tie.

        Thesis claim (vi): "mot bang ket qua phai TU MANG bang chung cua no" --
        in ra mot ten policy o mot o hoa la mot phat bieu khong co trong so lieu.
        """
        out = S.policy_table([self._tied()])
        self.assertIn("=", out.split("argmin")[1],
                      "the printed argmin column names a single policy at a cell "
                      "where three policies hold the same L")
        for name in (S.SENTINEL, S.B5, S.B6):
            self.assertIn(name.split()[0], out)

    def test_a_tie_at_zero_is_a_place_lambda_q_star_cannot_see_the_flip(self):
        """lambda-bar is an UPPER reading wherever L(0) ties.

        Thesis claim (vi): "lambda_q_star la trong so NHO NHAT > 0 lam doi thu
        hang" -- no bo qua diem cat tai DUNG 0, nen o mot o hoa tai 0, thu hang da
        doi ngay tren 0 ma lambda_q_star van bao mot so lon hon.  Dieu do phai duoc
        GHI, khong duoc de nguoi doc tu doan.

        Here Sentinel ties B5 at lambda_Q = 0 and B5 has strictly less Q_false, so
        B5 is ahead at EVERY positive weight -- yet lambda-bar comes back well above
        zero, read off the Sentinel-B1 crossing instead.
        """
        c = self._tied()
        lb = S.lambda_bar(c)
        self.assertIsNotNone(lb)
        self.assertGreater(lb, 0.05,
                           "this fixture no longer shows lambda-bar overshooting a "
                           "tie-at-zero flip")
        self.assertNotIn(S.SENTINEL, S.l_winners(c, 1e-9),
                         "Sentinel is still a winner just above zero, so there is "
                         "no overshoot to report here")


if __name__ == "__main__":
    unittest.main()
