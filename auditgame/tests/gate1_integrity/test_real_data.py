"""
GATE 1 -- real SWE-bench data.  Spec: docs/thesis/pipelines/SPEC-P1a-Harness.md Part 2.

These tests NEVER touch the network: they use one embedded sample row.
"""
from __future__ import annotations
import json, pathlib, tempfile, unittest

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
        self.assertEqual((d["n"], d["median"], d["hist"]), (2, 3.0, {3: 2}))
        # The gate reads "median > 3"; int() truncation would turn a true 3.5
        # into a "3" and trip a STOP the data never called for.
        self.assertIsInstance(d["median"], float)
        odd = topics.distribution([SAMPLE_ROW, TWO_FILE_ROW])
        self.assertEqual(odd["median"], 3.5,
                         "a median between two middle values must not be truncated")


class DownloadIsAllOrNothing(unittest.TestCase):
    """swebench_fetch writes the file every pinned number is measured from, and a
    TRUNCATED JSONL still parses -- so a half-download is indistinguishable
    downstream from a smaller dataset.  Driven entirely by a local stub: no test
    in this suite may touch the network.
    """

    def _stub(self, pages):
        """pages: list of payloads to answer successive _get calls with."""
        calls = iter(pages)

        def _get(url, tries=4):
            try:
                payload = next(calls)
            except StopIteration:
                raise AssertionError("fetch asked for more pages than the stub has")
            if isinstance(payload, Exception):
                raise payload
            return payload
        return _get

    @staticmethod
    def _page(ids):
        return {"rows": [{"row": {"instance_id": i}} for i in ids]}

    def test_a_download_that_fails_midway_leaves_the_previous_file_untouched(self):
        """Opening the output with "w" before the first page truncates the GOOD
        file at the moment the download starts, so a failure at page 3 of 50
        replaces a complete corpus with a valid-looking short one -- and nothing
        downstream can tell the difference.

        Thesis claim (vi): "so lieu do tren corpus DAY DU, khong phai mot phan".
        """
        import swebench_fetch
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "swebench_stub.jsonl"
            out.write_text("PREVIOUS COMPLETE FILE\n", encoding="utf-8")
            real_get = swebench_fetch._get
            swebench_fetch._get = self._stub(
                [self._page(["a", "b"]), RuntimeError("network died at page 2")])
            try:
                with self.assertRaises(RuntimeError):
                    swebench_fetch.fetch("stub/ds", "test", out)
            finally:
                swebench_fetch._get = real_get
            self.assertEqual(out.read_text(encoding="utf-8"),
                             "PREVIOUS COMPLETE FILE\n",
                             "a failed download overwrote the previous file")
            self.assertFalse(list(pathlib.Path(d).glob("*.part")),
                             "the partial file was left behind")

    def test_an_error_payload_is_raised_not_read_as_the_end_of_the_split(self):
        """datasets-server answers a rate-limited request with a JSON body that has
        an "error" key and no "rows".  `.get("rows", [])` read that as "the split
        ended here" and returned a SHORT count as though it were the whole
        dataset.  An empty "rows" list is the real terminator; a missing one is a
        failure.

        Thesis claim (vi): "loi mang phai bao loi, khong duoc thanh het du lieu".
        """
        import swebench_fetch
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "swebench_stub.jsonl"
            real_get = swebench_fetch._get
            swebench_fetch._get = self._stub(
                [self._page(["a", "b"]),
                 {"error": "rate limited, please retry"}])
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    swebench_fetch.fetch("stub/ds", "test", out)
            finally:
                swebench_fetch._get = real_get
            self.assertIn("rows", str(ctx.exception))
            self.assertFalse(out.exists(),
                             "an error payload still produced an output file")

    def test_an_empty_rows_page_ends_the_split_and_the_file_is_moved_into_place(self):
        """The success path of the two tests above: an empty "rows" list IS the
        end of the split, and only then does the .part file become the real one.

        Thesis claim (vi): "tai xong moi thay the file cu".
        """
        import swebench_fetch
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "swebench_stub.jsonl"
            out.write_text("PREVIOUS COMPLETE FILE\n", encoding="utf-8")
            real_get = swebench_fetch._get
            swebench_fetch._get = self._stub(
                [self._page(["a", "b"]), self._page(["c"]), {"rows": []}])
            try:
                n = swebench_fetch.fetch("stub/ds", "test", out)
            finally:
                swebench_fetch._get = real_get
            self.assertEqual(n, 3)
            self.assertEqual(
                [json.loads(l)["instance_id"]
                 for l in out.read_text(encoding="utf-8").splitlines()],
                ["a", "b", "c"])
            self.assertFalse(list(pathlib.Path(d).glob("*.part")))


class WorkflowGrouping(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        f = pathlib.Path(__file__).resolve().parents[2] / "data" / "swebench_verified.jsonl"
        if not f.exists():
            raise unittest.SkipTest("no data/ yet -- run swebench_fetch.py")

    @staticmethod
    def _shape_only():
        """A dataset with step 4 DISABLED.

        The tests that use it ask about the SHAPE of a workflow -- which repo its
        tasks come from, how its topic stringifies -- and those hold for every
        grouped workflow, feasible or not. Step 4 is about whether an ATTACK can
        be built on one, a different question, pinned by
        test_step4_drops_every_workflow_on_the_verified_pool below. Running these
        through the filtered corpus would make them skip (it is empty), and a skip
        is a claim with no evidence.
        """
        import swebench_dataset
        return swebench_dataset.SWEBenchDataset(sweep_deltas=())

    def test_a_workflow_only_groups_instances_from_ONE_repo(self):
        """Chaining instances across repos makes the workflow's "history" fake, and
        a shared topic is then a coincidence rather than a causal link.

        Thesis claim (vi): "carrier tich luy chi co nghia khi cung codebase".
        """
        for wf in self._shape_only().workflows(5, 8, seed=1):
            repos = {t.repo for t in wf.tasks}
            self.assertEqual(len(repos), 1, f"{wf.wf_id} mixes repos: {repos}")

    def test_statistics_answer_question_4(self):
        """SPEC-P1a Part 0 argues from the division 500 < 800.  The REAL constraint
        is that each repo must hold >= H instances.  This test pins the EXACT
        measured numbers, not just their types: on SWE-bench Verified at H=8 the
        grouping must yield 500 instances across 12 repos, of which 10 hold >= 8
        instances, giving 58 non-reused workflows and therefore a minimum reuse of
        42% (computed the same way the Buoc 3.6 command computes it) to reach
        N=100.  A mismatch here means the dataset changed underneath us, or
        tokenization drifted away from retrieval.topic_of -- STOP and find the
        cause. Do NOT edit the expected numbers below to make this test pass;
        that would defeat the reason this test exists.

        Thesis claim (vi): "cau 4 tra loi bang SO, khong bang phan doan".
        """
        import swebench_dataset
        st = swebench_dataset.SWEBenchDataset().stats(H=8)
        # `non_reused_workflows` counts the STEP-3 grouping, before step 4.
        # Question 4 asks how much instance REUSE is needed to reach N=100, which
        # is a property of the grouping; how many of those can host the sweep is a
        # different number, pinned separately below.

        self.assertEqual(
            st["instances"], 500,
            "instances != 500: the SWE-bench Verified data on disk changed. "
            "Stop and find out why before touching this expected number.")
        self.assertEqual(
            st["repos"], 12,
            "repos != 12: the set of repos in the Verified pool changed. "
            "Stop and find out why before touching this expected number.")
        self.assertEqual(
            st["repos_with_H"], 10,
            "repos_with_H != 10 at H=8: either the data changed, or "
            "tokenization drifted away from retrieval.topic_of and is "
            "grouping instances differently. Stop and find the cause -- do "
            "not update this expected number to match a new run.")
        self.assertEqual(
            st["non_reused_workflows"], 58,
            "non_reused_workflows != 58 at H=8: this is the exact number "
            "question 4 exists to answer. Either the dataset changed or "
            "tokenization drifted away from retrieval.topic_of. Stop and "
            "find the cause -- do not update this expected number.")

        # Same derivation as the Buoc 3.6 command, so the two cannot drift apart.
        needed = 100
        shortfall = max(0, needed - st["non_reused_workflows"])
        min_reuse_pct = 100 * shortfall / needed
        self.assertEqual(
            min_reuse_pct, 42,
            "minimum reuse to reach N=100 != 42%: this follows directly "
            "from non_reused_workflows via max(0, 100 - non_reused)/100, "
            "the same formula the Buoc 3.6 command uses. If this drifted "
            "while non_reused_workflows == 58, the formula itself changed "
            "-- stop and find the cause, do not update this number.")

    def test_step4_keeps_14_of_58_workflows_on_the_verified_pool(self):
        """SPEC-P1a Part 4 step 4 -- "LOAI workflow khong co cap (i, i+Delta)
        cung topic vuot theta cho Delta can quet", which the spec itself calls
        "N3 o muc dataset".

        This test used to pin feasible == 0: under `==` retrieval only 29 of the
        1624 intra-workflow task pairs (1.79%) shared a topic, so ALL 58 grouped
        workflows were dropped and the real corpus was empty. Two things changed,
        and NEITHER of them is theta being weakened to rescue the count:

          * core.CarrierStore.retrieve now goes through retrieval.retrieved(),
            so "related" is sim >= theta rather than set equality;
          * theta is retrieval.THETA = 0.5, derived from the measured |topic|
            distribution in docs/reports/chot_theta.md and COMMITTED BEFORE these
            counts were looked at. The old note here said "theta moves when
            retrieval moves"; retrieval moved.

        The numbers below are a RESULT. At theta=0.5, 281/1624 = 17.30% of
        intra-workflow pairs clear theta -- for scale the synthetic mock sits at
        282/1624 = 17.36%, so the real corpus's relatedness now measures like the
        mock's rather than an order of magnitude below it -- and 14 of the 58
        workflows survive. If this test moves, the corpus, the tokenization, or
        theta changed: STOP and find out which. Do NOT edit these numbers to make
        it pass, and in particular do not move theta to restore one -- theta is
        fixed from data, and the count is its consequence, never its reason.

        Thesis claim (vi): "workflow khong dung duoc attack phai RA KHOI mau so".
        """
        import retrieval, swebench_dataset
        self.assertEqual(
            swebench_dataset.THETA, retrieval.THETA,
            "step 4 and the runner's retrieval are using DIFFERENT thetas, so "
            "the filter no longer describes the retrieval it filters for")
        self.assertEqual(retrieval.THETA, 0.5,
                         "theta moved away from the value derived in "
                         "docs/reports/chot_theta.md -- re-derive it from the |topic| "
                         "distribution before touching this test")
        rep = swebench_dataset.SWEBenchDataset().grouping_report(H=8)
        self.assertEqual(rep["grouped"], 58)
        self.assertEqual(
            rep["feasible"], 14,
            "the number of workflows surviving step 4 on the Verified pool "
            "moved. Either the data changed, tokenization drifted, or theta "
            "changed. Find out which before reporting any swebench number.")
        self.assertEqual(rep["dropped"], 44)
        self.assertEqual(rep["per_delta"], {0: 58, 1: 37, 2: 28, 4: 28},
                         "the per-Delta hosting counts moved")

    def test_step4_still_empties_the_corpus_under_exact_retrieval(self):
        """The 14 above must be attributable to GRADED RETRIEVAL and to nothing
        else. Same data, same tokenization, same code path, theta back at 1.0 --
        which for equal token sets IS the `==` the store used to do -- and the
        count has to fall back to the 0 / {0:58, 1:8, 2:6, 4:2} this file pinned
        before. If it does not, something other than theta moved between the two
        readings and the gain cannot be credited to retrieval.

        Thesis claim (vi): "khop chinh xac la CA RIENG theta=1, khong bi thay the".
        """
        import swebench_dataset
        rep = swebench_dataset.SWEBenchDataset(theta=1.0).grouping_report(H=8)
        self.assertEqual(rep["grouped"], 58)
        self.assertEqual(rep["feasible"], 0,
                         "theta=1.0 no longer reproduces the exact-matching "
                         "corpus, so graded retrieval is NOT a generalisation "
                         "of it and the old table cannot be recovered")
        self.assertEqual(rep["per_delta"], {0: 58, 1: 8, 2: 6, 4: 2})

    def test_a_corpus_that_cannot_host_the_sweep_is_refused_with_a_reason(self):
        """N3 at dataset level: "could not be built" must never arrive as harm 0.

        The Verified pool at H=8 now survives step 4, so the refusal has to be
        driven by a corpus that genuinely cannot host the sweep rather than by
        the one that happens to be broken this week -- otherwise the refusal
        machinery goes untested the moment the data improves. H=4 is such a
        corpus for a structural reason, not a statistical one: the sweep reaches
        Delta=4 and a 4-task workflow has no pair (i, i+4) at all, so NO amount
        of relatedness can host it.

        `workflows()` must raise and NAME THE NUMBERS, so a reader is told what
        was dropped and why instead of receiving a grid of zeros.

        Thesis claim (vi): "o ngoai pham vi thi ghi LY DO, khong ghi harm=0".
        """
        import swebench_dataset
        ds = swebench_dataset.SWEBenchDataset()
        self.assertEqual(ds.grouping_report(H=4)["feasible"], 0,
                         "fixture drifted: H=4 can now host Delta=4, which is "
                         "structurally impossible -- check sweep_deltas")
        with self.assertRaises(ValueError) as ctx:
            list(ds.workflows(1, 4, seed=1))
        msg = str(ctx.exception)
        self.assertIn("step 4", msg)
        self.assertIn("120", msg, "the refusal must name how many were dropped")
        self.assertIn("harm 0", msg,
                      "the refusal must say what it is refusing to print")

    def test_a_usable_corpus_is_registered_rather_than_left_pending(self):
        """The mirror of the refusal, and the reason it has to be tested: a
        dataset that CAN host the sweep must reach datasets.REGISTRY, or
        experiment.py prints a stale refusal for a corpus that works. swebench
        sat in PENDING for exactly as long as step 4 emptied it; it is registered
        now because 14 workflows survive, and the PENDING entry must be gone
        rather than kept as a contradictory second opinion.

        Thesis claim (vi): "tu choi phai co ly do, va ly do phai het han duoc".
        """
        import datasets
        self.assertIn("swebench", datasets.REGISTRY,
                      "a corpus that survives step 4 is still refused")
        self.assertNotIn("swebench", datasets.PENDING,
                         "swebench is registered AND pending -- two answers to "
                         "one question, and experiment.py reads the wrong one")
        self.assertEqual(datasets.REGISTRY["swebench"].scope().topic_kind, "graded")

    def test_workflows_refuses_to_reuse_an_instance_beyond_the_cap(self):
        """bootstrap_paired resamples BY WORKFLOW and assumes independence across
        resamples. Two workflows that share an instance have CORRELATED clean-run
        results, so reusing an instance beyond swebench_dataset.MAX_INSTANCE_REUSE
        produces a falsely narrow confidence interval -- silently, if `workflows()`
        just wraps around with `%`. This test uses a tiny in-memory stand-in
        dataset (2 repos, independent of the gitignored data/ files) but drives it
        through the REAL SWEBenchDataset.workflows() code path, not a
        reimplementation of it: a request exactly at the cap must still succeed,
        and a request one workflow past it must raise, naming the numbers.

        Thesis claim (vi): "moi instance duoc dung lai toi da 2 lan, khong hon".
        """
        import swebench_dataset

        def row(repo: str, idx: int) -> dict:
            return {
                "instance_id": f"{repo}-{idx}",
                "repo": repo,
                "created_at": f"2022-01-{idx:02d}T00:00:00Z",
                "base_commit": "deadbeef",
                "patch": f"diff --git a/pkg/mod{idx}.py b/pkg/mod{idx}.py\n",
                "problem_statement": "",
            }

        rows = [row("org/one", i) for i in range(1, 3)] + \
               [row("org/two", i) for i in range(1, 3)]
        ds = swebench_dataset.SWEBenchDataset.__new__(swebench_dataset.SWEBenchDataset)
        ds.pool = "in-memory-stub"
        ds._rows = rows
        ds._topic_cache = {}
        # step 4 off: this test is about the REUSE CAP, and a fixture built to
        # exercise the cap would otherwise be emptied by the filter first.
        ds.sweep_deltas = ()
        ds.theta = swebench_dataset.THETA

        # H=1 -> each row is its own non-overlapping segment: 2 segments per
        # repo, 4 segments total. cap = MAX_INSTANCE_REUSE * 4 = 8.
        n_segments = len(ds._segments(H=1))
        self.assertEqual(n_segments, 4, "stand-in fixture no longer yields 4 segments")
        cap = swebench_dataset.MAX_INSTANCE_REUSE * n_segments

        at_cap = list(ds.workflows(cap, 1, seed=7))
        self.assertEqual(len(at_cap), cap,
                          f"a request exactly at the cap ({cap}) must succeed")

        with self.assertRaises(ValueError) as ctx:
            list(ds.workflows(cap + 1, 1, seed=7))
        msg = str(ctx.exception)
        self.assertIn(str(cap + 1), msg, "error must name the requested n")
        self.assertIn(str(n_segments), msg, "error must name the available segments")
        self.assertIn(str(swebench_dataset.MAX_INSTANCE_REUSE), msg,
                       "error must name the cap")

    def test_topic_never_stringifies_in_frozenset_hash_order(self):
        """A SWE-bench topic is a frozenset, and frozenset's own str()/repr() walks
        its internal hash table in an order that depends on Python's per-process
        string-hash randomisation (PYTHONHASHSEED).  Every place a topic reaches
        core.seed_of or an f-string content template (agent.py's memory/skill/
        branch/queue notes, build.py's payload content) goes through str(topic) --
        so if that ever fell back to frozenset's own order-dependent form, the SAME
        command would print a DIFFERENT number on two separate runs, exactly the
        failure class the project's hash() ban exists to prevent.

        Thesis claim (vi): "topic frozenset khong duoc roi thang vao chuoi hay seed".
        """
        wf = next(iter(self._shape_only().workflows(1, 8, seed=1)))
        topic = wf.tasks[0].topic
        self.assertIsInstance(topic, frozenset)
        self.assertEqual(str(topic), "|".join(sorted(topic)))


if __name__ == "__main__":
    unittest.main()
