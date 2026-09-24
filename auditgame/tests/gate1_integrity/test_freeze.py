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


class TheHeldOutSplitIsFrozen(unittest.TestCase):

    def test_moving_the_held_out_share_is_detected(self):
        """The split is hash(name) < HELD_OUT_SHARE, so changing the share
        changes WHICH attackers are held out while every name stays the same.
        Only a manifest that records the split itself can see that."""
        import attackers
        tmp = pathlib.Path(tempfile.mkdtemp()) / "MANIFEST.json"
        freeze.write(tmp)
        old = attackers.HELD_OUT_SHARE
        try:
            attackers.HELD_OUT_SHARE = 0.9
            d = freeze.drift(tmp)
        finally:
            attackers.HELD_OUT_SHARE = old
        self.assertTrue(any("held_out_attackers" in x for x in d), d)


class TheScatteredDigestsAreInTheCell(unittest.TestCase):
    """Three configurations used to be pinned by three separate digests, and the
    run-level manifest covered none of them.

    Each private digest catches its own file being edited and is blind to the
    other two, so `freeze: clean` was printable on a run whose gate-2 criterion,
    payload bank or judge prompt had moved since the numbers were produced.
    These tests pin the two properties that make gathering them worth anything:
    the manifest MOVES when a pin moves, and a pin that disagrees with its own
    committed declaration is reported WITHOUT waiting for a freeze.
    """

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp()) / "MANIFEST.json"

    def test_every_pin_carries_a_live_digest_and_a_declared_slot(self):
        """A pin whose `live` is empty covers nothing while looking like coverage.

        `declared` is allowed to be None -- the judge prompt has no committed
        artefact to disagree with, which is precisely why it needed a cell -- but
        the key must be PRESENT, so that adding a declaration later is a change to
        a value rather than a change to the shape of the manifest.
        """
        p = freeze.pins()
        self.assertTrue(p, "the pins section is empty: it covers nothing")
        for name, v in p.items():
            with self.subTest(pin=name):
                self.assertIn("declared", v)
                self.assertTrue(v.get("live"), f"{name} has no live digest")

    def test_the_manifest_digest_moves_when_a_pin_moves(self):
        """THE CLAIM. Before this section existed, editing the judge prompt left
        `freeze.digest()` byte-identical, so a results header could go on saying
        `freeze: clean` with a different prompt behind the numbers."""
        import fdetect
        before = freeze.digest()
        old = fdetect.JUDGE_PROMPT
        try:
            fdetect.JUDGE_PROMPT = old + "\n(an edit nobody declared)"
            after = freeze.digest()
        finally:
            fdetect.JUDGE_PROMPT = old
        self.assertNotEqual(before, after)
        self.assertEqual(before, freeze.digest())

    def test_a_moved_pin_is_named_in_the_drift_report(self):
        """'The manifest does not match' sends a reader to diff two JSON files.
        The report has to say WHICH pin, the same way it does for a constant."""
        import fdetect
        freeze.write(self.tmp)
        self.assertEqual(freeze.drift(self.tmp), [])
        old = fdetect.JUDGE_PROMPT
        try:
            fdetect.JUDGE_PROMPT = old + "\n(an edit nobody declared)"
            d = freeze.drift(self.tmp)
        finally:
            fdetect.JUDGE_PROMPT = old
        self.assertTrue(any("pins/judge_prompt" in x for x in d), d)

    def test_a_pin_that_disagrees_with_its_own_declaration_is_reported(self):
        """The failure a copied digest INTRODUCES: the manifest records the live
        value, so an artefact that has drifted from the module generating it is
        recorded as though it were fine. `pin_conflicts` reads the second column."""
        from analysis import gate2_v2
        self.assertEqual(freeze.pin_conflicts(), [])
        old = gate2_v2.FROZEN_MD5
        try:
            gate2_v2.FROZEN_MD5 = "0" * 32
            c = freeze.pin_conflicts()
        finally:
            gate2_v2.FROZEN_MD5 = old
        self.assertTrue(any("pins/gate2_v2" in x for x in c), c)

    def test_a_pin_conflict_is_reported_before_any_freeze_exists(self):
        """Most of this project's life is before the freeze, and a gate-2
        definition that disagrees with its committed artefact is a fact about the
        tree the table was produced on -- true whether or not anyone has frozen
        anything. Holding it back until the freeze hides it for exactly the period
        in which it is still cheap to fix."""
        from analysis import gate2_v2
        old = gate2_v2.FROZEN_MD5
        try:
            gate2_v2.FROZEN_MD5 = "0" * 32
            line = freeze.header_line(pathlib.Path("/nonexistent/MANIFEST.json"))
        finally:
            gate2_v2.FROZEN_MD5 = old
        self.assertIn("NONE", line)
        self.assertIn("PIN CONFLICT", line)
        self.assertIn("gate2_v2", line)

    def test_a_manifest_written_before_pins_existed_still_reports(self):
        """A manifest on somebody's disk predates this section. Missing pins must
        read as one added section, not as a KeyError that makes the whole drift
        report unavailable."""
        freeze.write(self.tmp)
        man = json.loads(self.tmp.read_text())
        del man["pins"]
        self.tmp.write_text(json.dumps(man))
        d = freeze.drift(self.tmp)
        self.assertTrue(all("pins/" in x and "added" in x for x in d), d)


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
