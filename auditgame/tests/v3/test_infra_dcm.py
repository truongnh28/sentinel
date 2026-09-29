"""The draft compliance matrix holds together (plan S5).  Infrastructure: no DCM row.

These are checks 1-6 of `tools/v3_dcm.py --check`, run on every `tests/run_v3.py`, with one
difference the tool's docstring explains: here a P2 row may be PENDING (its task has not
written the test file yet); `--check` is strict and fails on pending rows.  The tail of the
file tests the checker itself, on rows made up for the purpose.
"""
import pathlib
import tempfile
import unittest

from tools import v3_dcm as V


class TestInfraDcm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.load_problems = V.load()
        cls.tests = V.collect_tests()

    def test_dcm_rows_are_well_formed(self):
        """Every shard starts with the PDF pin and the ten columns; every row is well formed."""
        self.assertTrue(V.shard_paths(), "no DCM shard found in v3/dcm/")
        problems = self.load_problems + V.check_format(self.rows)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_dcm_id_test_pairs_are_unique(self):
        """Check 1: (id, test) is unique across every shard."""
        problems = V.check_unique(self.rows)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_every_p2_dcm_row_names_an_existing_test(self):
        """Check 2 (existence): a P2 row names a test that exists, or -- while its task has
        not run -- a test in a file that is not written yet AND belongs to the shard's task."""
        problems, _pending = V.check_p2_tests_exist(self.rows, self.tests)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_every_v3_test_is_a_dcm_row_or_infra(self):
        """Check 3: every test in tests/v3/ is named by a DCM row or lives in test_infra_*.py."""
        problems = V.check_every_test_covered(self.rows, self.tests)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_dcm_quotes_are_verbatim_in_pinned_draft(self):
        """Check 4: every quote occurs in docs/v3/draft-2026-09-07.txt (NFKC, whitespace
        collapsed; the ellipsis character elides)."""
        problems = V.check_quotes(self.rows, V.draft_text())
        self.assertEqual(problems, [], "\n".join(problems))

    def test_draft_pdf_sha256_is_pinned(self):
        """Check 5: the draft PDF (repo copy, and the vault copy when present), the pinned
        text and every shard header carry the pinned digests."""
        self.assertEqual(V.DRAFT_PDF_SHA256,
                         "c37643f0971c3457c176c39607e1be6782007c85988c053e4b5ab0aa8be7263a",
                         "the pin itself moved: sentinel-v3.md 'Tai lieu goc' names this digest")
        problems = V.check_pins()
        self.assertEqual(problems, [], "\n".join(problems))

    def test_pinned_draft_text_is_pdftotext_of_pinned_pdf(self):
        """The committed text is what pdftotext makes of the pinned PDF, so a quote check
        against it is a check against the draft."""
        sha = V.regenerate_text_sha()
        if sha is None:
            self.skipTest("pdftotext is not installed: the pinned text cannot be regenerated "
                          "here (its sha256 is still checked by test_draft_pdf_sha256_is_pinned)")
        self.assertEqual(sha, V.DRAFT_TXT_SHA256,
                         "this pdftotext gives a different text; if poppler changed, re-pin "
                         "deliberately and re-verify every quote")

    def test_every_dcm_test_docstring_names_its_id(self):
        """Check 6: the docstring of each named, existing test contains the row's id."""
        problems = V.check_docstrings(self.rows, self.tests)
        self.assertEqual(problems, [], "\n".join(problems))

    # ---- the checker itself --------------------------------------------------------------

    @staticmethod
    def _row(**kw):
        base = dict(id="D4.state", where="§4", quote="State at task t", level="L0", c_ref="",
                    decision="d", module="v3/state.py",
                    test="tests/v3/test_s4_state_payload.py::TestS4StatePayload::test_x",
                    phase="P2", result_ref="", shard="T03", line=3)
        base.update(kw)
        return V.Row(**base)

    def test_checker_catches_a_duplicate_pair(self):
        rows = [self._row(line=3), self._row(line=4)]
        self.assertEqual(len(V.check_unique(rows)), 1)
        self.assertEqual(V.check_unique([self._row(), self._row(id="D4.sigma")]), [])

    def test_checker_rejects_a_paraphrased_quote_and_accepts_an_elided_one(self):
        text = V.draft_text()
        self.assertTrue(V.quote_in("Defender loss is L = E[verified harm]…with verified "
                                   "harm measured by a sealed oracle", text))
        self.assertFalse(V.quote_in("Defender loss is L = E[harm]", text))
        self.assertFalse(V.quote_in("with verified harm measured…Defender loss is", text),
                         "fragments must appear in order")
        self.assertFalse(V.quote_in("…", text))

    def test_checker_flags_a_missing_test_in_a_written_file(self):
        with tempfile.TemporaryDirectory() as d:
            tdir = pathlib.Path(d)
            (tdir / "test_s4_state_payload.py").write_text("")
            problems, pending = V.check_p2_tests_exist([self._row()], {}, tests_dir=tdir)
            self.assertEqual(len(problems), 1)
            self.assertEqual(pending, [])

    def test_checker_keeps_an_unwritten_file_pending_and_strict_mode_fails_it(self):
        with tempfile.TemporaryDirectory() as d:
            tdir = pathlib.Path(d)
            problems, pending = V.check_p2_tests_exist([self._row()], {}, tests_dir=tdir)
            self.assertEqual((problems, len(pending)), ([], 1))
            problems, _ = V.check_p2_tests_exist([self._row()], {}, tests_dir=tdir, strict=True)
            self.assertEqual(len(problems), 1)

    def test_checker_rejects_a_row_outside_its_tasks_files(self):
        row = self._row(shard="T05")
        problems, pending = V.check_p2_tests_exist([row], {})
        self.assertEqual(len(problems), 1)
        self.assertIn("not a test file of T05", problems[0])

    def test_checker_requires_a_row_for_every_non_infra_test(self):
        tests = {"tests/v3/test_s4_agent.py::TestS4Agent::test_y": "",
                 "tests/v3/test_infra_seal.py::TestInfraSeal::test_z": ""}
        self.assertEqual(len(V.check_every_test_covered([], tests)), 1)


if __name__ == "__main__":
    unittest.main()
