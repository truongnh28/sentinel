"""
GATE 1 -- graded retrieval (R).
Spec: pipelines/SPEC-R-Truy-xuat.md

A test's NAME states the claim it defends; the Vietnamese wording of that claim
lives in the docstring under `Thesis claim (vi):`.
"""
from __future__ import annotations
import unittest

import retrieval


class GradedRetrieval(unittest.TestCase):

    def test_exact_match_is_the_special_case_theta_equals_one(self):
        """If R cannot reproduce the old table, we cannot tell "R changed the
        conclusion" from "R has a bug".  A design constraint, not a convenience.

        Thesis claim (vi): "R khong thay the hanh vi cu, no tong quat hoa".
        """
        a = retrieval.topic_of(["django/db/models/query.py"])
        b = retrieval.topic_of(["django/db/models/query.py"])
        c = retrieval.topic_of(["django/db/models/sql/compiler.py"])
        self.assertTrue(retrieval.retrieved(a, b, theta=1.0),
                        "EQUAL token sets must be retrieved at theta=1")
        self.assertFalse(retrieval.retrieved(a, c, theta=1.0),
                         "DIFFERENT token sets must not be retrieved at theta=1")

    def test_sim_is_deterministic_across_calls(self):
        """The function does not learn and does not sample.

        Thesis claim (vi): "replay khop bit".
        """
        a = retrieval.topic_of(["a/b/c.py", "a/d.py"])
        b = retrieval.topic_of(["a/b/e.py"])
        vals = {retrieval.sim(a, b) for _ in range(50)}
        self.assertEqual(len(vals), 1, f"sim is not deterministic: {vals}")

    def test_epsilon_controls_retrievability(self):
        """Measured on the current version: the payload at eps=0.05 and eps=0.95 is
        byte-for-byte IDENTICAL, same item_id.  A quarter of the attack space is a
        no-op.

        Thesis claim (vi): "epsilon la ngan sach phan biet", not a decorative parameter.
        """
        target = retrieval.topic_of(["django/db/models/query.py",
                                     "django/db/models/sql/compiler.py"])
        sims = [retrieval.sim(retrieval.payload_topic(target, eps), target)
                for eps in (0.2, 0.5, 0.8, 1.0)]
        self.assertEqual(sims, sorted(sims),
                         f"sim must be NON-DECREASING in epsilon, measured {sims}")
        self.assertLess(sims[0], sims[-1],
                        f"epsilon cannot change sim: {sims} -- still a no-op")
        self.assertAlmostEqual(sims[-1], 1.0, places=9,
                               msg="eps=1 must coincide exactly with task sigma's topic")

    def test_larger_epsilon_makes_a_larger_payload(self):
        """Without this second dimension, epsilon is just a free "make it stronger"
        knob and the distinguishability budget does not exist.  `size` is an
        F_match feature.

        Thesis claim (vi): "epsilon danh doi truy xuat LAY do kho phat hien".
        """
        target = retrieval.topic_of([f"pkg/mod{i}/file{i}.py" for i in range(5)])
        sizes = [len(retrieval.payload_topic(target, eps))
                 for eps in (0.2, 0.5, 0.8, 1.0)]
        self.assertEqual(sizes, sorted(sizes), f"|A| must be non-decreasing: {sizes}")
        self.assertLess(sizes[0], sizes[-1],
                        f"epsilon cannot change the payload size: {sizes}")

    def test_payload_is_a_subset_of_the_target_topic(self):
        """If the payload added tokens OUTSIDE the target, the Jaccard denominator
        would inflate and sim would DROP -- a larger epsilon would weaken the
        attack, exactly backwards from the intended semantics.

        Thesis claim (vi): "sim(A,B) = eps" -- a simple relation, checkable by hand.
        """
        target = retrieval.topic_of(["a/b.py", "c/d.py", "e/f.py"])
        for eps in (0.1, 0.4, 0.7, 1.0):
            with self.subTest(eps=eps):
                self.assertTrue(
                    retrieval.payload_topic(target, eps) <= target,
                    "the payload must be a SUBSET of the target topic")

    def test_topic_does_not_depend_on_file_order(self):
        """Whatever order the gold patch lists files in, the topic must come out
        the same.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        x = retrieval.topic_of(["a/b.py", "c/d.py"])
        y = retrieval.topic_of(["c/d.py", "a/b.py"])
        self.assertEqual(x, y, "topic depends on file order => traces do not replay")


if __name__ == "__main__":
    unittest.main()
