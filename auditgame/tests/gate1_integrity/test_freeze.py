"""The freeze manifest must actually bite.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 8.

A manifest nobody checks is a promise with extra steps. These tests pin the two
properties that make it evidence: it MOVES when the configuration moves, and the
harness REFUSES a policy that appeared after the freeze.
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import freeze
import policies as P


class TheManifestReactsToWhatItCovers(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()) / "MANIFEST.json"

    def test_a_clean_tree_reports_no_drift(self):
        freeze.write(self.tmp)
        self.assertEqual(freeze.drift(self.tmp), [])

    def test_moving_a_constant_is_detected_and_named(self):
        """Not just 'it changed' -- the message has to say WHICH field, or a
        reader is sent to diff two JSON files by hand."""
        freeze.write(self.tmp)
        old = P.KAPPA_COMMIT
        try:
            P.KAPPA_COMMIT = old * 2
            d = freeze.drift(self.tmp)
        finally:
            P.KAPPA_COMMIT = old
        self.assertTrue(any("kappa_commit" in x for x in d), d)

    def test_adding_a_policy_is_detected(self):
        freeze.write(self.tmp)
        P.REGISTRY["ZZ test-only"] = P.Policy
        try:
            d = freeze.drift(self.tmp)
        finally:
            del P.REGISTRY["ZZ test-only"]
        self.assertTrue(any("ZZ test-only" in x for x in d), d)

    def test_docs_are_not_in_the_cell(self):
        """A manifest that invalidates results when a runbook is edited will be
        ignored within a week. The source list is the claim about what matters."""
        self.assertTrue(all(f.endswith(".py") for f in freeze.SOURCE))
        for f in freeze.SOURCE:
            self.assertFalse(f.startswith(("docs", "tools", "spikes")), f)

    def test_the_generated_table_is_its_own_entry(self):
        """score_table.json is built FROM pi0. Changing pi0 and forgetting to
        regenerate is precisely the drift this has to catch."""
        self.assertIn("reference/score_table.json", freeze.TABLES)


class TheHarnessRefuses(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()) / "MANIFEST.json"

    def test_a_policy_added_after_the_freeze_is_refused(self):
        freeze.write(self.tmp)
        man = json.loads(self.tmp.read_text())
        man["policies"] = [p for p in man["policies"] if p != "Sentinel"]
        self.tmp.write_text(json.dumps(man))
        with self.assertRaises(freeze.NotFrozen) as cm:
            freeze.require_frozen("Sentinel", self.tmp)
        self.assertIn("Sentinel", str(cm.exception))

    def test_a_frozen_policy_passes(self):
        freeze.write(self.tmp)
        freeze.require_frozen("Sentinel", self.tmp)
        freeze.require_frozen("SW-commit", self.tmp)

    def test_no_manifest_means_no_refusal(self):
        """Most of this project's life is before the freeze. A module that
        refuses without one would just get bypassed, and then it protects
        nothing when the freeze finally happens."""
        freeze.require_frozen("anything at all",
                              pathlib.Path("/nonexistent/MANIFEST.json"))

    def test_the_header_says_which_of_the_three_states_holds(self):
        self.assertIn("NONE", freeze.header_line(
            pathlib.Path("/nonexistent/MANIFEST.json")))
        freeze.write(self.tmp)
        self.assertIn("clean", freeze.header_line(self.tmp))
        man = json.loads(self.tmp.read_text())
        man["constants"]["theta"] = 0.123456
        self.tmp.write_text(json.dumps(man))
        self.assertIn("DRIFTED", freeze.header_line(self.tmp))


if __name__ == "__main__":
    unittest.main()
