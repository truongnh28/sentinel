"""
GATE 1 -- the operational form of F_match / F_detect separation.
Spec: QUYET-DINH.md, question 1.

The declared constraint used to be a set intersection,
    F_match n F_detect = {}
which is VACUOUS here: F_detect is not a feature list, it is an operating
characteristic (psi, phi) => (d', tau_det).  Comparing a real name list against an
aspirational one can never go red, so it was never a test.

The operational content splits in two:

    (a) epsilon MUST move AUC on F_match          -> the budget has teeth
    (b) epsilon MUST NOT move the distribution of s(x)  -> the detector is blind to F_match

This file holds (b).  (a) lives in gate 2, because it is a question about what the
numbers MEAN, not about whether they are real.
"""
from __future__ import annotations
import random, statistics, unittest

import attacks, build, detector
from core import seed_of

SEEDS = 400          # enough to separate a 0.1 shift in the mean at sd 1


def _payload_scores(pipe, eps: float, det, wf, n=SEEDS) -> list:
    """Raw detector scores for one pipeline's payload at one epsilon."""
    ps = pipe.plan(wf, "memory", 2, random.Random(7), epsilon=eps)
    item = pipe.payload(wf, ps)
    return [det.score(item, now=ps.sigma, seed=s) for s in range(n)]


class DetectorIsBlindToFMatch(unittest.TestCase):

    def setUp(self):
        self.det = detector.Detector.from_setting("mid")
        self.wf = build.make_workflow("wf-000", "django", 8,
                                      random.Random(seed_of("fsep", 0)))

    def test_epsilon_does_not_shift_the_detector_score_distribution(self):
        """Invariant (b).  epsilon is the attacker's budget on F_match; the detector
        runs on F_detect.  If moving epsilon moved the score distribution, the two
        would be reading the same signal and the benign-corpus argument would be
        circular: "indistinguishable on F_match" and "detectable on F_detect" would
        be claims about one number.

        Compares DISTRIBUTIONS, not realisations.  Individual scores must differ --
        item_id is content-derived, so a different payload draws a different sample.
        That is correct.  What must not differ is the mean.

        Thesis claim (vi): "F_match giao F_detect bang rong", dang van hanh.
        """
        for name, pipe in attacks.REGISTRY.items():
            means = {}
            for eps in (0.1, 0.4, 0.7, 1.0):
                sc = _payload_scores(pipe, eps, self.det, self.wf)
                means[eps] = statistics.fmean(sc)
            spread = max(means.values()) - min(means.values())
            # 4 sigma of the sampling error of a mean over SEEDS draws at sd 1
            tol = 4.0 / (SEEDS ** 0.5)
            with self.subTest(pipeline=name):
                self.assertLess(
                    spread, tol,
                    f"[{name}] epsilon shifts the mean detector score by {spread:.4f} "
                    f"(tolerance {tol:.4f}): {({k: round(v,3) for k,v in means.items()})}. "
                    f"The detector is reading an F_match feature.")

    def test_the_detector_never_reads_a_surface_feature(self):
        """Structural companion to the statistical test above.

        A statistical test can only fail once the leak is large enough to see.  This
        one fails the moment `surface` appears in the detector at all, which is
        cheaper and earlier.

        Thesis claim (vi): "F_detect giu nguyen dang truu tuong".
        """
        import inspect
        src = inspect.getsource(detector)
        for f in ("surface", "size", "recency", "derived_from"):
            self.assertNotIn(
                f, src,
                f"detector.py mentions the F_match feature {f!r} -- the detector must "
                f"stay parameterised by (d', tau_det), not compute features.")


if __name__ == "__main__":
    unittest.main()
