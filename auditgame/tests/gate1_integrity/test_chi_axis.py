"""The chi axis: three declared anchors, and the table must HAVE the chi asked for.

Spec: docs/preregistration/TIEN-DANG-KY-truc-chi.md;
docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md P7.

WHY THIS FILE EXISTS.  `experiment.sweep_chi` was written, documented as the RQ2
axis, and then never called from anywhere -- the grid printed tables at ONE chi
while the docstring claimed a (Delta x chi x detector) sweep.  Dead code that
describes a measurement is worse than absent code, because it reads as evidence.

The tests below pin the two things a reader has to be able to trust: the anchor
is a declared choice with a stated consequence, and the table handed to the
policies actually has the chi the row is labelled with.
"""
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import experiment
import policies as P


class ChiIsWhatTheLabelSays(unittest.TestCase):
    """A row labelled chi = x must be run on a table whose chi IS x."""

    BASE = {"memory": 0.4, "skill": 0.9, "queue": 1.6, "branch": 4.1}

    def test_every_anchor_hits_the_requested_chi(self):
        for anchor in P.CHI_ANCHORS:
            for chi in (0.0, 0.25, 0.5, 1.0, 1.349, 2.0, 2.114):
                with self.subTest(anchor=anchor, chi=chi):
                    t = P.kappa_for_chi(chi, self.BASE, anchor=anchor)
                    self.assertAlmostEqual(P.chi_of(t), chi, places=9)

    def test_the_anchored_statistic_is_the_one_held_fixed(self):
        """Each anchor's promise, stated as a test rather than as a comment."""
        for chi in (0.25, 0.5, 1.0, 2.0):
            mean = P.kappa_for_chi(chi, self.BASE, anchor="mean")
            self.assertAlmostEqual(sum(mean.values()) / len(mean),
                                   sum(self.BASE.values()) / len(self.BASE), places=9)
            lo = P.kappa_for_chi(chi, self.BASE, anchor="min")
            self.assertAlmostEqual(min(lo.values()), min(self.BASE.values()), places=9)
            hi = P.kappa_for_chi(chi, self.BASE, anchor="max")
            self.assertAlmostEqual(max(hi.values()), max(self.BASE.values()), places=9)

    def test_at_the_base_chi_all_three_anchors_agree(self):
        """Sanity: asking for the chi the base already has must return the base,
        whichever statistic is pinned.  If they disagree there, the anchors are
        not three views of one table."""
        chi0 = P.chi_of(self.BASE)
        for anchor in P.CHI_ANCHORS:
            t = P.kappa_for_chi(chi0, self.BASE, anchor=anchor)
            for k, v in self.BASE.items():
                self.assertAlmostEqual(t[k], v, places=6, msg=f"{anchor}/{k}")

    def test_a_chi_that_would_need_a_negative_cost_is_refused(self):
        """Refuse, do not clamp.  A clamped table no longer has the chi it was
        asked for, so the sweep would report a value it is not running."""
        with self.assertRaises(ValueError):
            P.kappa_for_chi(50.0, self.BASE, anchor="max")

    def test_an_undeclared_anchor_is_refused(self):
        with self.assertRaises(ValueError):
            P.kappa_for_chi(1.0, self.BASE, anchor="whatever")


class TheAxisIsReachableFromTheMainPath(unittest.TestCase):
    """The reason this file exists: sweep_chi used to be unreachable."""

    def test_sweep_chi_is_called_by_main(self):
        src = pathlib.Path(experiment.__file__).read_text(encoding="utf-8")
        body = src[src.index("def main("):]
        self.assertIn("sweep_chi(", body,
                      "experiment.main() does not call sweep_chi: the chi axis is "
                      "documented but not run, which is how RQ2 went untested.")

    def test_the_anchor_is_named_in_the_output(self):
        """A chi table that does not say which anchor produced it is unreadable:
        the same chi means three different things."""
        src = pathlib.Path(experiment.__file__).read_text(encoding="utf-8")
        self.assertIn("chi_anchor", src)


class TheAnchorQuestionDissolves(unittest.TestCase):
    """P7 asked which of three chi-sweep conventions to declare.  It has an
    answer rather than a preference: once the whole cost table moves together
    and the budget is a SHARE of the audit bill, the three coincide.
    """

    BASE = {"memory": 0.4, "skill": 0.9, "queue": 1.6, "branch": 4.1}

    def test_two_tables_with_the_same_chi_are_proportional(self):
        """Why the question dissolves, in one line of algebra made checkable.

        Fixing chi fixes spread/mean; fixing the shape fixes the relative
        deviations; so any two tables with the same chi over the same base are
        scalar multiples.  An anchor therefore only RESCALES -- it cannot change
        the shape of the cost vector, which is the thing chi is about.
        """
        for chi in (0.25, 0.5, 1.0, 1.349, 2.0):
            tm = P.kappa_for_chi(chi, self.BASE, anchor="mean")
            for other in ("min", "max"):
                t = P.kappa_for_chi(chi, self.BASE, anchor=other)
                ratios = [t[k] / tm[k] for k in self.BASE]
                self.assertAlmostEqual(max(ratios), min(ratios), places=9,
                                       msg=f"chi={chi} anchor={other}: not a rescaling")

    def test_the_commit_channel_moves_with_the_table(self):
        """The axis is only a chi axis if kappa_commit and eta_Q move too.

        Left at their absolute values they re-price the commit channel as chi
        moves, and kappa_commit / kappa_bar is the quantity that decides which
        policy wins -- so RQ2 would be measuring RQ1's confound.  Measured before
        this was fixed: the three anchors gave B7 harm 0.6053 / 0.7632 / 0.5.
        """
        src = pathlib.Path(experiment.__file__).read_text(encoding="utf-8")
        body = src[src.index("def sweep_delta("):src.index("def sweep_chi(")]
        self.assertIn("KAPPA_COMMIT", body)
        self.assertIn("ETA_Q_COST", body)
        self.assertIn("scale", body)

    def test_sweep_delta_restores_every_patched_global(self):
        """A sweep that leaks its cost table poisons every later table in the
        same process -- and the chi sweep runs after the detector loop."""
        before = (dict(P.KAPPA), P.KAPPA_COMMIT, P.ETA_Q_COST)
        try:
            experiment.sweep_delta([], (0,), "mid", 1.0, (1,), ("memory",),
                                   chi=0.5, chi_anchor="min")
        except Exception:
            pass                       # the restore is what is under test
        self.assertEqual(dict(P.KAPPA), before[0])
        self.assertEqual(P.KAPPA_COMMIT, before[1])
        self.assertEqual(P.ETA_Q_COST, before[2])


if __name__ == "__main__":
    unittest.main()
