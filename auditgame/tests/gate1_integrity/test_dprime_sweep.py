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

import dprime_sweep as S
import detector
import experiment
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
                   S.break_even, S.refinement_points):
            used = identifiers(fn)
            self.assertNotIn("hash", used,
                             f"{fn.__name__} calls hash() -- process-dependent")
            self.assertNotIn("count", used,
                             f"{fn.__name__} uses a counter -- order-dependent")


if __name__ == "__main__":
    unittest.main()
