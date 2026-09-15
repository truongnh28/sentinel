"""
GATE 1 -- real SWE-bench data.  Spec: ../pipelines/SPEC-P1a-Harness.md Part 2.

These tests NEVER touch the network: they use one embedded sample row.
"""
from __future__ import annotations
import unittest

import topics

SAMPLE_ROW = {
    "instance_id": "astropy__astropy-12907",
    "repo": "astropy/astropy",
    "created_at": "2022-02-16T09:17:22Z",
    "patch": (
        "diff --git a/astropy/modeling/separable.py b/astropy/modeling/separable.py\n"
        "--- a/astropy/modeling/separable.py\n"
        "+++ b/astropy/modeling/separable.py\n"
        "@@ -242,7 +242,7 @@ def _cstack(left, right):\n"
        "-        cright[-right.shape[0]:, -right.shape[1]:] = 1\n"
        "+        cright[-right.shape[0]:, -right.shape[1]:] = right\n"
    ),
}

# Two-file patch: distinct path tokens on each file, so a hunk reversed at the
# diff level would produce a DIFFERENT list from files_of_patch() if topic
# extraction were order-dependent.  This is the fixture that can actually
# catch a regression that test_topic_extracts_the_right_files_from_the_gold_patch
# and the single-file SAMPLE_ROW cannot.
TWO_FILE_ROW = {
    "instance_id": "astropy__astropy-99999",
    "repo": "astropy/astropy",
    "created_at": "2022-02-16T09:17:22Z",
    "patch": (
        "diff --git a/astropy/modeling/separable.py b/astropy/modeling/separable.py\n"
        "--- a/astropy/modeling/separable.py\n"
        "+++ b/astropy/modeling/separable.py\n"
        "@@ -242,7 +242,7 @@ def _cstack(left, right):\n"
        "-        cright[-right.shape[0]:, -right.shape[1]:] = 1\n"
        "+        cright[-right.shape[0]:, -right.shape[1]:] = right\n"
        "diff --git a/astropy/modeling/core.py b/astropy/modeling/core.py\n"
        "--- a/astropy/modeling/core.py\n"
        "+++ b/astropy/modeling/core.py\n"
        "@@ -10,3 +10,3 @@ def _validate(self):\n"
        "-    return True\n"
        "+    return self._valid\n"
    ),
}

# Same two hunks as TWO_FILE_ROW, with the file order reversed at the diff
# level (core.py first, separable.py second).
TWO_FILE_ROW_REVERSED = {
    "instance_id": "astropy__astropy-99999",
    "repo": "astropy/astropy",
    "created_at": "2022-02-16T09:17:22Z",
    "patch": (
        "diff --git a/astropy/modeling/core.py b/astropy/modeling/core.py\n"
        "--- a/astropy/modeling/core.py\n"
        "+++ b/astropy/modeling/core.py\n"
        "@@ -10,3 +10,3 @@ def _validate(self):\n"
        "-    return True\n"
        "+    return self._valid\n"
        "diff --git a/astropy/modeling/separable.py b/astropy/modeling/separable.py\n"
        "--- a/astropy/modeling/separable.py\n"
        "+++ b/astropy/modeling/separable.py\n"
        "@@ -242,7 +242,7 @@ def _cstack(left, right):\n"
        "-        cright[-right.shape[0]:, -right.shape[1]:] = 1\n"
        "+        cright[-right.shape[0]:, -right.shape[1]:] = right\n"
    ),
}


class RealData(unittest.TestCase):

    def test_topic_extracts_the_right_files_from_the_gold_patch(self):
        """topic is the JOIN KEY -- "two related tasks" is defined through it.
        Extract the wrong files and every injection configuration is wrong too.

        Thesis claim (vi): "topic = danh sach file ma gold patch sua".
        """
        self.assertEqual(topics.files_of_patch(SAMPLE_ROW["patch"]),
                         ["astropy/modeling/separable.py"])

    def test_topic_is_a_token_set_independent_of_file_order(self):
        """Thesis claim (vi): "ket qua tai lap duoc"."""
        self.assertEqual(topics.topic_of_instance(SAMPLE_ROW),
                         frozenset({"astropy", "modeling", "separable"}))

    def test_topic_of_two_file_patch_is_unchanged_by_hunk_order(self):
        """SAMPLE_ROW touches exactly ONE file, so the assertion above passes
        no matter whether topic_of_instance is order-dependent -- a one-file
        patch has no order to depend on.  This test uses a patch that touches
        TWO files with different path tokens, so reversing the hunks would
        change a list-ordered result but must NOT change the token SET.

        Thesis claim (vi): "ket qua tai lap duoc" (kiem tra that voi >= 2 file).
        """
        expected = frozenset({"astropy", "modeling", "separable", "core"})
        forward = topics.topic_of_instance(TWO_FILE_ROW)
        reversed_ = topics.topic_of_instance(TWO_FILE_ROW_REVERSED)
        self.assertEqual(forward, expected)
        self.assertEqual(reversed_, expected)

    def test_distribution_reports_median_and_histogram(self):
        """The sample instance edits EXACTLY ONE file => a 3-token topic => Jaccard
        takes only a few discrete values.  Without the distribution, fixing theta is
        guesswork.

        Thesis claim (vi): "theta chot duoc BANG DU LIEU".
        """
        d = topics.distribution([SAMPLE_ROW, SAMPLE_ROW])
        self.assertEqual((d["n"], d["median"], d["hist"]), (2, 3, {3: 2}))


if __name__ == "__main__":
    unittest.main()
