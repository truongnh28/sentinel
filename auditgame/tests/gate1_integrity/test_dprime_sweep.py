"""
GATE 1 -- INTEGRITY for the d' sweep: "are these numbers real?"

Red here means the sweep's curve is not the same measurement the frozen tables
are, and every d'* read off it is worthless.

Naming convention: test names are English and each name is the SENTENCE the test
protects; the thesis sentence it defends lives in the mandatory
`Thesis claim (vi):` docstring line.
"""
from __future__ import annotations
import unittest

import agent
import dprime_sweep as S
import detector
import experiment
import runner
from tests.fixtures import identifiers


class SweepIsTheSameMeasurement(unittest.TestCase):
    """The sweep must be ADDITIVE: at the d' of an existing setting it has to give
    back that setting's numbers, or it is a second, incomparable experiment."""

    #: Small on purpose -- the claim is about AGREEMENT, not about corpus size, and
    #: experiment.sweep_delta runs all ten policies at every point.
    N, H, SEEDS, BUDGET = 4, 4, (1, 2, 3), 17.95

    def test_the_sweep_builds_the_same_corpus_experiment_py_builds(self):
        """Two corpora seeded the same way, or the curve is about other workflows.

        Thesis claim (vi): "phep do nay la CONG THEM -- khong lam xe dich bat ky
        con so da dong bang nao".

        make_corpus shares ONE rng across the whole corpus; seeding each workflow
        independently (which datasets.MockDataset does) moves every number.  This
        module keeps its own copy of that loop, so the copy has to be pinned to the
        original rather than trusted.
        """
        mine = S.make_corpus(self.N, self.H, seed=2026)
        theirs = experiment.make_corpus(self.N, self.H, seed=2026)
        self.assertEqual([w.wf_id for w in mine], [w.wf_id for w in theirs])
        self.assertEqual([[t.topic for t in w.tasks] for w in mine],
                         [[t.topic for t in w.tasks] for w in theirs],
                         "the sweep's corpus is not experiment.py's corpus, so the "
                         "curve is measured on different workflows")

    def test_the_sweep_at_mid_d_prime_reproduces_the_frozen_mid_detector_row(self):
        """At d' = d'(mid) the sweep must return experiment.py's `mid` harms EXACTLY.

        Thesis claim (vi): "d' la tham so QUET; ba diem weak/mid/strong la ba diem
        TREN chinh duong cong do, khong phai mot phep do khac".

        This is the join between the curve and every number already frozen.  If it
        does not hold, "weak/mid/strong land at X on the curve" is a comparison
        between two different experiments.
        """
        d_mid, tau_mid = detector.operating_point(*detector.SETTINGS["mid"])
        self.assertAlmostEqual(S.TAU_DET, tau_mid, places=12,
                               msg="the sweep's fixed tau_det is not mid's tau_det")

        wfs = S.make_corpus(self.N, self.H, seed=2026)
        deltas = (1,)
        grid = experiment.sweep_delta(wfs, deltas, "mid", self.BUDGET, self.SEEDS,
                                      S.CARRIERS)
        for d in deltas:
            cell = S.measure_cell(wfs, d_mid, d, self.BUDGET, self.SEEDS)
            self.assertEqual(cell.harm_b1, grid[d][S.B1].harm,
                             f"Delta={d}: sweep B1 harm {cell.harm_b1} != frozen "
                             f"{grid[d][S.B1].harm}")
            self.assertEqual(cell.harm_sentinel, grid[d][S.SENTINEL].harm,
                             f"Delta={d}: sweep Sentinel harm {cell.harm_sentinel} "
                             f"!= frozen {grid[d][S.SENTINEL].harm}")
            self.assertEqual(cell.n_feasible, grid[d][S.SENTINEL].n_feasible)

    def test_two_runs_of_the_same_sweep_cell_agree_to_the_last_digit(self):
        """Every draw goes through core.seed_of, so the cell is a pure function.

        Thesis claim (vi): "tat dinh -- cung mot lenh phai ra cung mot con so".

        A break-even that moves between two runs of the same command is not a
        threshold, it is a dice roll.

        SCOPE, stated so the name does not outrun it.  The comparison covers the
        harms AND the interval, but what it can actually DETECT is a lost seed in
        the HARM path: perturbing measure_cell's bootstrap call to
        `seed=random.randrange(10**6)` leaves this test green, because per-workflow
        harm is discrete and small-n, so the 2.5%/97.5% quantiles of 10000 resamples
        land on the same lattice value under any seed.  The claim "the CI is a
        seeded call on the per-workflow lists" is pinned by the gate-3 test
        test_the_break_even_ci_resamples_workflows_not_cases, which compares the
        sweep's interval against runner.bootstrap_paired directly.  The assertion
        on ci_lo < ci_hi below only keeps this cell from being a degenerate point.
        """
        wfs = S.make_corpus(6, 4, seed=2026)
        a = S.measure_cell(wfs, 2.0, 1, self.BUDGET, self.SEEDS)
        b = S.measure_cell(wfs, 2.0, 1, self.BUDGET, self.SEEDS)
        self.assertLess(a.ci_lo, a.ci_hi,
                        "the probe cell's CI is a single point, so this test cannot "
                        "see a bootstrap that lost its seed -- pick another cell")
        self.assertEqual((a.harm_b1, a.harm_sentinel, a.dharm, a.ci_lo, a.ci_hi),
                         (b.harm_b1, b.harm_sentinel, b.dharm, b.ci_lo, b.ci_hi),
                         "the same sweep cell measured twice gave two answers")

    def test_the_sweep_core_draws_nothing_through_hash_or_itertools_count(self):
        """No process-dependent source of numbers anywhere in the measurement core.

        Thesis claim (vi): "moi boc tham qua core.seed_of; hash() va
        itertools.count bi CAM".

        Checked on the AST, not on the source text: a docstring mentioning `hash`
        is prose, and a grep would read it as code -- that is the test failing, not
        the module.  PYTHONHASHSEED makes `hash()` on a str differ between two
        runs of the same command, which is exactly the property a frozen number
        must not have.
        """
        for fn in (S.measure_cell, S.sweep, S.make_corpus, S.make_detector,
                   S.break_even, S.refinement_points, S.refine_brackets):
            used = identifiers(fn)
            self.assertNotIn("hash", used,
                             f"{fn.__name__} calls hash() -- process-dependent")
            self.assertNotIn("count", used,
                             f"{fn.__name__} uses a counter -- order-dependent")


class TheSweepArtefactSaysWhichRunMadeIt(unittest.TestCase):
    """An archived --json file has to carry the identity of the run that made it."""

    def _cells(self):
        return {0: [S.SweepCell(d_prime=0.2, delta=0, harm_b1=1.0,
                                harm_sentinel=0.9, dharm=0.1, ci_lo=0.0, ci_hi=0.2,
                                n_feasible=40, n_total=40)]}

    def test_the_json_artefact_records_the_mode_and_the_run_that_produced_it(self):
        """Cells alone cannot say which tau_sel mode measured them.

        Thesis claim (vi): "moi con so deu co mot lenh tai lap di kem".

        The two modes of this sweep produce numbers of the SAME shape -- on the
        published corpus they are identical cell for cell -- so two archived files
        are indistinguishable unless the file says which mode, which grid, which
        seeds and which corpus size it came from.  Without that a sweep JSON is a
        number with no recipe behind it, which is precisely what gate 1 exists to
        refuse.
        """
        rows = self._cells()
        common = dict(n=40, H=8, budget=17.95, seeds=(1, 2, 3), deltas=(0,),
                      grid=S.GRID, refined=False)
        pinned = S.json_payload(rows, tau_follows_dprime=False, **common)
        following = S.json_payload(rows, tau_follows_dprime=True, **common)

        for name, doc in (("pinned", pinned), ("following", following)):
            with self.subTest(mode=name):
                run = doc["run"]
                self.assertEqual(run["n_workflows"], 40)
                self.assertEqual(run["budget"], 17.95)
                self.assertEqual(list(run["seeds"]), [1, 2, 3])
                self.assertEqual(list(run["grid"]), list(S.GRID))
                self.assertEqual(run["corpus_seed"], S.CORPUS_SEED)
                self.assertEqual(len(doc["cells"]["0"]), 1)
                self.assertEqual(doc["cells"]["0"][0]["d_prime"], 0.2)

        self.assertFalse(pinned["run"]["tau_follows_dprime"])
        self.assertTrue(following["run"]["tau_follows_dprime"])
        self.assertNotEqual(pinned["run"], following["run"],
                            "the two tau_sel modes write indistinguishable "
                            "artefacts, so an archived sweep cannot say which one "
                            "it is")
        self.assertEqual(pinned["cells"], following["cells"],
                         "the run block leaked into the cells")


class TheFourPolicyCellIsTheSameMeasurementRunnerAlreadyMakes(unittest.TestCase):
    """The cell now needs PER-WORKFLOW Q_false and T_lost, and runner.GridCell
    carries those two only as means (`per_wf` is the harm vector alone).  runner.py
    is frozen, so the sweep keeps its OWN copy of the worst-case loop -- the same
    move make_corpus already makes against experiment.make_corpus, and pinned the
    same way: the copy is asserted against the original rather than trusted.

    Without the per-workflow vectors the CI95 of Delta-L could only be the harm CI
    shifted by a constant, which would give the Q_false and T_lost terms NO
    sampling variability at all and so report an interval narrower than the
    evidence -- the exact way a threshold gets overstated."""

    N, H, SEEDS, BUDGET = 6, 4, (1, 2, 3), 17.95

    def test_the_per_workflow_vectors_reproduce_runner_worst_case_exactly(self):
        """Every scalar of the sweep's own loop equals runner.worst_case's.

        Thesis claim (vi): "phep do nay la CONG THEM -- khong lam xe dich bat ky
        con so da dong bang nao".

        Not "close to": EQUAL.  A copy of an attacker-max loop that drifts by one
        seed, one carrier or one tie-break is a second experiment wearing the
        first one's name.
        """
        wfs = S.make_corpus(self.N, self.H, seed=2026)
        det, ag = S.make_detector(2.0), agent.MockAgent()
        for name in S.POLICIES:
            with self.subTest(policy=name):
                runner.reset_survivor_cache()
                theirs = runner.worst_case(name, wfs, (1,), S.CARRIERS, det, ag,
                                           self.BUDGET, self.SEEDS, S.SETTING)
                runner.reset_survivor_cache()
                mine = S.policy_curve(name, wfs, (1,), S.CARRIERS, det, ag,
                                      self.BUDGET, self.SEEDS, S.SETTING)
                self.assertEqual(mine.per_wf_harm, theirs.per_wf,
                                 "the sweep's per-workflow harm vector is not "
                                 "runner.worst_case's")
                self.assertEqual((mine.harm, mine.q_false, mine.t_lost,
                                  mine.spent, mine.n_feasible, mine.n_total),
                                 (theirs.harm, theirs.q_false, theirs.t_lost,
                                  theirs.spent_mean, theirs.n_feasible,
                                  theirs.n_total),
                                 f"{name}: the sweep's copy of the worst-case loop "
                                 f"drifted from runner.worst_case")
                for vec in (mine.per_wf_q_false, mine.per_wf_t_lost,
                            mine.per_wf_spent):
                    self.assertEqual(len(vec), len(theirs.per_wf),
                                     "a per-workflow vector has a different length "
                                     "from the harm vector it must pair with")
                n = len(theirs.per_wf)
                self.assertAlmostEqual(sum(mine.per_wf_q_false) / n, theirs.q_false,
                                       places=12,
                                       msg="the per-workflow Q_false vector does "
                                           "not average to the reported mean")
                self.assertAlmostEqual(sum(mine.per_wf_t_lost) / n, theirs.t_lost,
                                       places=12)
                self.assertAlmostEqual(sum(mine.per_wf_spent) / n, theirs.spent_mean,
                                       places=12)

    def test_adding_b5_and_b6_does_not_move_the_b1_sentinel_pair(self):
        """The published d-harm cell is unchanged by the two policies added beside it.

        Thesis claim (vi): "duong cong harm da cong bo phai tai lap NGUYEN VEN" --
        neu them B5/B6 vao cung mot o lam xe dich harm cua B1 hay Sentinel thi co
        trang thai dung chung giua cac policy, va moi so da dong bang deu dang ngo.

        The survivor cache is keyed without the policy name (runner.survives), so
        two policies measured in one cell share the clean phase.  That is the
        state a shared-state defect would travel through, and this pins it.
        """
        wfs = S.make_corpus(self.N, self.H, seed=2026)
        pair = S.measure_cell(wfs, 2.0, 1, self.BUDGET, self.SEEDS,
                              policies=(S.B1, S.SENTINEL))
        four = S.measure_cell(wfs, 2.0, 1, self.BUDGET, self.SEEDS)
        self.assertEqual(sorted(four.curves), sorted(S.POLICIES))
        self.assertEqual((pair.harm_b1, pair.harm_sentinel, pair.dharm,
                          pair.ci_lo, pair.ci_hi, pair.n_feasible),
                         (four.harm_b1, four.harm_sentinel, four.dharm,
                          four.ci_lo, four.ci_hi, four.n_feasible),
                         "measuring B5 and B6 in the same cell moved B1/Sentinel")

    def test_the_sweeps_own_worst_case_loop_draws_nothing_process_dependent(self):
        """The copied loop obeys the same seeding rule as the rest of the core.

        Thesis claim (vi): "moi boc tham qua core.seed_of; hash() va
        itertools.count bi CAM".
        """
        used = identifiers(S.policy_curve)
        self.assertNotIn("hash", used,
                         "policy_curve calls hash() -- process-dependent")
        self.assertNotIn("count", used,
                         "policy_curve uses a counter -- order-dependent")


if __name__ == "__main__":
    unittest.main()
