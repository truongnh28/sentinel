"""
GATE 1 -- M3: one workflow, eight tasks, end to end.
Spec: eval/PLAN.md Task 17; ../pipelines/SPEC-P1b-Trace.md Part 1.

M3 is the first time four separately-built things run together: the real
dataset, the filesystem carrier store, a real repo reset between tasks, and the
runner's trace.  Nothing here is a new measurement mechanism -- every number
still comes from `runner.run_once` -- so what these tests defend is the WIRING,
and the three ways wiring of this shape fails quietly:

  * the reset does not really happen, so "the carriers survive it" is a claim
    with no experiment behind it (the control file is the other half);
  * swapping the in-RAM store for the filesystem one MOVES A NUMBER, which would
    make every recorded figure in this build the figure of a different world;
  * a field group of SPEC-P1b Part 1 is missing from the trace and nobody
    notices until the LLM has to be re-run to get it back.

The eight-task run here is over the FIXTURE repo, not over a cloned SWE-bench
repository: what makes the reset real is that it is `git clean -xfd` plus `git
checkout --force` against a real `.git`, and a one-commit fixture supplies that
for the price of a temp directory.  The real-corpus run is `m3.py`'s own
`main()`, whose artefacts are `results/M3-trace.json` and `spikes/M3.md`.
"""
from __future__ import annotations
import json
import pathlib
import shutil
import tempfile
import unittest

import agent as agent_mod
import build
import carrier_store_fs
import core
import detector
import harness
import m3
import policies as P
import runner
from core import CARRIERS

from tests.fixtures import make_repo


H = 8
SEED = 4242


def a_workflow(wf_id: str = "m3-fixture", repo: str = "tinyrepo"):
    """An H-task workflow whose tasks can host a delta-2 injection."""
    import random
    return build.make_workflow(wf_id, repo, H=H, rng=random.Random(11), need_delta=2)


def a_plan(wf):
    import random
    ps = build.plan_poison(wf, "memory", 2, random.Random(11))
    assert ps is not None, "the fixture could not plan an injection"
    return ps


def a_detector():
    return detector.Detector.from_setting("mid")


def a_policy():
    return P.make_policy("B3 audit-on-insertion", budget=17.95,
                         rng_seed=core.seed_of("m3", SEED), setting="mid")


def measured_part(traces) -> str:
    """The trace with `audit_seconds` dropped, as a comparable string.

    A WALL-CLOCK READING IS NOT A MEASURED QUANTITY OF THE EXPERIMENT.  It is the
    one field in a TaskTrace that legitimately differs between two runs of the
    same seed -- that is what makes it a cost measurement -- so a test asking
    "did this change any number" has to compare everything else.  Dropping it is
    also the assertion that it is the ONLY such field: anything else that started
    reading the clock would show up here as a diff.
    """
    return core.dumps([{k: v for k, v in vars(tr).items() if k != "audit_seconds"}
                       for tr in traces])


class TheEightRepoResets(unittest.TestCase):
    """The reset is run for real, against a real `.git`."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="auditgame-m3-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "workspace" / "tinyrepo"
        self.base = make_repo(self.repo)
        self.root = self.tmp / "carriers"
        self.assertFalse(self.root.resolve().is_relative_to(self.repo.resolve()),
                         "the fixture put the carrier root INSIDE the repo -- this "
                         "test cannot tell persistence from luck")

    def a_run(self, **kw):
        wf = a_workflow()
        ps = a_plan(wf)
        return m3.run_workflow(wf, ps, repo_path=self.repo, root=self.root,
                               base_commit=self.base, det=a_detector(),
                               pol=a_policy(), ag=agent_mod.MockAgent(),
                               seed=SEED, **kw)

    def test_the_carriers_survive_every_one_of_the_eight_repo_resets(self):
        """The whole trick of the thesis, run eight times in a row rather than once.

        The CONTROL is the other half: each task drops a scratch file into the
        worktree and edits a tracked one, and both must be gone after the next
        task's reset.  Without it this passes against a reset that never happened
        -- and would keep passing if the carriers moved back inside the repo.

        Thesis claim (vi): "carrier song sot qua ca tam lan reset repo".
        """
        run = self.a_run()
        self.assertEqual(len(run.resets), H,
                         f"the run did not reset the repo once per task: {run.resets}")
        for r in run.resets:
            self.assertTrue(r["worktree_was_cleaned"],
                            f"task {r['t']}: the reset left the scratch file behind, "
                            f"so this run proves nothing about survival")
            self.assertTrue(r["tracked_file_was_restored"],
                            f"task {r['t']}: the reset did not restore the tracked "
                            f"file to base_commit")
        # The store is REOPENED from disk after every reset, so the counts below
        # are what a fresh process would read back, not what was held in RAM.
        counts = [r["live_after_reopen"] for r in run.resets]
        self.assertEqual(counts, sorted(counts),
                         f"a reset destroyed carrier items: {counts}")
        self.assertGreater(counts[-1], counts[0],
                           "nothing accumulated across the eight tasks: the run "
                           "cannot show that state outlived the reset")
        for c in ("memory", "branch"):
            self.assertTrue(run.final_store.items[c],
                            f"carrier {c!r} is empty after the whole run")

    def test_the_branch_carrier_is_the_one_the_reset_could_have_reached_and_did_not(self):
        """`branch` lives INSIDE the repo (in `.git/`, decision B-1: keep `.git`,
        only `checkout`).  A test that watches memory/skill/queue survive is green
        BY LUCK on the one carrier a reset could plausibly destroy.

        Thesis claim (vi): "carrier branch nam trong .git nen no la phep thu that".
        """
        run = self.a_run()
        reopened = carrier_store_fs.FSCarrierStore(self.root, repo=self.repo)
        self.assertEqual([i.item_id for i in reopened.items["branch"]],
                         [i.item_id for i in run.final_store.items["branch"]],
                         "the branch carrier read back from the repo differs from "
                         "the one the run ended with")
        self.assertEqual(len(reopened.items["branch"]), H,
                         "the mock agent commits once per task, so eight resets "
                         "must leave eight branch items")

    def test_the_payload_label_never_lands_in_the_directory_the_container_can_read(self):
        """M3 is the first production call site of `build.inject_sealed`.  The
        payload goes into a carrier the container reads; its `poisoned` label and
        the sealed manifest go into the sibling area that is mounted nowhere.

        Thesis claim (vi): "nhan ground truth khong bao gio nam trong mount".
        """
        run = self.a_run()
        blob = "\n".join(p.read_text(encoding="utf-8")
                         for p in sorted(self.root.rglob("*")) if p.is_file())
        self.assertNotIn("poisoned", blob,
                         "a `poisoned` label is inside the carrier root, which is "
                         "the directory the agent is handed")
        self.assertIsNotNone(run.manifest, "M3 planted a payload and sealed no "
                                           "manifest: nobody can identify it afterwards")
        sealed = carrier_store_fs.sealed_root_for(self.root)
        self.assertTrue((sealed / carrier_store_fs.LABELS).exists(),
                        "no sealed labels were written at all")
        self.assertEqual([m["injected_item"] for m in
                          carrier_store_fs.FSCarrierStore(self.root, repo=self.repo).read_manifests()],
                         [run.manifest["injected_item"]])


class SwappingTheStoreMovesNoNumber(unittest.TestCase):
    """The invariant that lets M3 exist at all."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="auditgame-m3-inv-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_a_run_over_a_supplied_store_measures_what_the_default_run_measures(self):
        """`runner.run_once` grew three optional arguments so M3 could hand it a
        filesystem store, a per-task hook and a sealing plan.  Defaults unchanged
        means every recorded number in this build still stands; a run over a
        SUPPLIED in-RAM store must therefore agree field by field with the default.

        Thesis claim (vi): "them tham so cho M3 khong duoc lam xe dich so nao".
        """
        wf, det, ag = a_workflow(), a_detector(), agent_mod.MockAgent()
        ps = a_plan(wf)
        base = runner.run_once(wf, ps, a_policy(), det, ag, SEED)
        mine = core.CarrierStore()
        given = runner.run_once(wf, ps, a_policy(), det, ag, SEED, store=mine)
        # THAT THE SUPPLIED STORE WAS THE ONE USED, before comparing anything.
        # A run_once that ignored the argument and made its own fresh in-RAM store
        # would agree with the default on every field below -- both are empty
        # `CarrierStore()`s -- so the comparison alone is a test that cannot fail
        # for the reason its name gives.  Measured: it did not (perturbation P23).
        self.assertTrue(any(mine.items[c] for c in CARRIERS),
                        "run_once did not write into the store it was handed")
        for f in ("harm", "solved", "marker", "spent", "detected_at",
                  "quarantined", "fired_at", "true_quarantine",
                  "false_quarantine", "t_lost"):
            self.assertEqual(getattr(base, f), getattr(given, f),
                             f"supplying a store moved {f}")
        self.assertEqual(measured_part(base.traces), measured_part(given.traces),
                         "supplying a store changed the trace")

    def test_reopening_the_store_between_tasks_measures_what_one_open_store_measures(self):
        """The reset hook reopens the filesystem store from disk on every task,
        which is what makes "it survived" a reading rather than an assertion.  A
        reopen that lost -- or gained -- an item would change what can be
        retrieved, and retrieval is the one causal channel in this experiment.

        Thesis claim (vi): "mo lai store moi task khong duoc doi ket qua do".
        """
        wf, ps = a_workflow(), None
        ps = a_plan(wf)
        repo_a, repo_b = self.tmp / "ws" / "a", self.tmp / "ws" / "b"
        base_a, base_b = make_repo(repo_a), make_repo(repo_b)
        kept = m3.run_workflow(wf, ps, repo_path=repo_a, root=self.tmp / "ca",
                               base_commit=base_a, det=a_detector(), pol=a_policy(),
                               ag=agent_mod.MockAgent(), seed=SEED, reopen=False)
        fresh = m3.run_workflow(wf, ps, repo_path=repo_b, root=self.tmp / "cb",
                                base_commit=base_b, det=a_detector(), pol=a_policy(),
                                ag=agent_mod.MockAgent(), seed=SEED, reopen=True)
        self.assertEqual(kept.result.harm, fresh.result.harm)
        self.assertEqual(measured_part(kept.result.traces),
                         measured_part(fresh.result.traces),
                         "reopening the store between tasks changed the trace")


class TheNineFieldGroups(unittest.TestCase):
    """SPEC-P1b-Trace.md Part 1's acceptance line: "trace co MOI truong Phan 1"."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="auditgame-m3-nine-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "ws" / "tinyrepo"
        self.base = make_repo(self.repo)
        wf = a_workflow()
        self.run = m3.run_workflow(wf, a_plan(wf), repo_path=self.repo,
                                   root=self.tmp / "carriers", base_commit=self.base,
                                   det=a_detector(), pol=a_policy(),
                                   ag=agent_mod.MockAgent(), seed=SEED)

    def test_the_nine_groups_are_named_after_the_spec_and_there_are_nine_of_them(self):
        """Nine rows in the spec's table, nine groups here.  A checker that knows
        about eight of them reports a complete trace while one row is missing.

        Thesis claim (vi): "chin nhom truong, dung chin, dung ten trong spec".
        """
        self.assertEqual(len(m3.FIELD_GROUPS), 9)
        self.assertEqual([g for g, _ in m3.FIELD_GROUPS],
                         ["state", "writes", "retrieval", "scores", "n_c",
                          "checkpoints", "quarantine", "result", "cost"])

    def test_an_eight_task_run_fills_every_one_of_the_nine_field_groups(self):
        """The acceptance criterion itself, checked rather than asserted.

        Thesis claim (vi): "mot lan chay tam task lap day ca chin nhom truong".
        """
        report = m3.field_groups(self.run.result.traces)
        missing = [g for g, v in report.items() if not v["present"]]
        self.assertEqual(missing, [], f"field groups not recorded: "
                                      f"{ {g: report[g] for g in missing} }")

    def test_a_group_no_task_recorded_is_reported_empty_rather_than_present(self):
        """The checker has to be able to say NO.  A reporter that always answers
        "present" is the exact shape of the defect this project has produced
        eleven times: a check narrower than the sentence it stands for.

        Thesis claim (vi): "nhom truong khong duoc ghi phai bao rong, khong bao du".
        """
        stripped = [core.TaskTrace(**dict(vars(tr), checkpoints={}, quarantines=[]))
                    for tr in self.run.result.traces]
        report = m3.field_groups(stripped)
        self.assertFalse(report["checkpoints"]["present"])
        self.assertFalse(report["quarantine"]["present"])
        self.assertTrue(report["state"]["present"],
                        "removing two groups must not take the others with them")

    def test_the_result_group_can_report_empty_too_and_not_only_the_container_ones(self):
        """The demonstration above only reaches CONTAINER-typed fields, and the two
        rules `_recorded` applies are different rules: an empty dict or list is an
        absence, while `False` is a VERDICT and counts.  Nothing exercised the
        second one -- and `result` is the group flagged with a warning in
        spikes/M3.md section 5, whose absence costs "harm cannot be scored".

        Why that matters here.  `core.TaskTrace` declares `patch_has_marker`,
        `public_ok` and `hidden_ok` as NON-DEFAULTED bools, so no ordinary run can
        produce a trace on which they are missing: `field_groups(...)["result"]`
        ["present"] was structurally True for any list of traces, and a checker
        that cannot answer NO about the group it is loudest about is not checking
        it.  The bool rule has to be shown to work, on the group that depends on it.

        Thesis claim (vi): "nhom `result` cung phai bao rong duoc, khong chi cac
        nhom kieu container".
        """
        # `None` is the only thing that can mean "nobody wrote this" for a bool:
        # False is a measurement. See m3._recorded.
        for absent in ("public_ok", "hidden_ok", "patch_has_marker", "agent_marker"):
            blanked = [core.TaskTrace(**dict(vars(tr), **{absent: None}))
                       for tr in self.run.result.traces]
            report = m3.field_groups(blanked)
            with self.subTest(field=absent):
                self.assertFalse(
                    report["result"]["present"],
                    f"every task's {absent} is None and the `result` group still "
                    f"reports present. Its cost_if_missing is "
                    f"{report['result']['cost_if_missing']!r}, so a false "
                    f"'present' here is a harm column certified by a checker that "
                    f"cannot see its own absence.")
                self.assertEqual(report["result"]["fields"][absent], 0)
                self.assertTrue(report["state"]["present"],
                                "blanking one result field took another group down")

        # and the other half of the rule: a recorded False is NOT an absence
        falsified = [core.TaskTrace(**dict(vars(tr), public_ok=False,
                                           hidden_ok=False, patch_has_marker=False,
                                           agent_marker=False))
                     for tr in self.run.result.traces]
        report = m3.field_groups(falsified)
        self.assertTrue(
            report["result"]["present"],
            "a run in which every verdict is False is a run that was MEASURED; "
            "reporting the group empty would make `_recorded` unable to tell a "
            "clean result from a missing one.")
        self.assertEqual(report["result"]["fields"]["public_ok"], len(falsified))

    def test_the_trace_written_to_disk_reads_back_with_the_same_nine_groups(self):
        """`results/M3-trace.json` is the artefact; a group that does not survive
        the round trip is a group the replay engine will never see.

        The PUBLIC half is what is read here, because the public half is what
        ships: the nine-field-group acceptance line has to hold on the file a
        reader actually gets, not on the one the evaluator keeps.

        Thesis claim (vi): "trace ghi ra dia doc lai van du chin nhom".
        """
        path = self.tmp / "M3-trace.json"
        core.dump_traces(path, self.run.result.traces)
        back = core.load_traces(path)
        self.assertEqual(m3.field_groups(back), m3.field_groups(self.run.result.traces))

    def test_writing_a_trace_puts_the_ground_truth_in_the_sealed_half_and_nowhere_else(self):
        """The seal line, applied to the artefact.  A trace carries the evaluator's
        answer key -- `poisoned` on every item record, the planted payload under
        `injected`, and `correct` beside every quarantine -- and `dump_traces` is
        the one door every writer goes through, so the split belongs there.

        Checked in BOTH directions: nothing survives in the public half, and
        nothing was lost, because a split that drops the labels is a split that
        makes the run unscorable.

        Thesis claim (vi): "nhan ground truth nam trong nua niem phong, khong nam
        trong file cong bo".
        """
        import sealed_trace
        path = self.tmp / "M3-trace.json"
        core.dump_traces(path, self.run.result.traces)
        sealed = sealed_trace.sealed_path(path)
        self.assertEqual(sealed.name, "M3-sealed.json")
        self.assertTrue(sealed.is_file(), f"{sealed} was not written")

        public = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            sealed_trace.ground_truth_fields_in(public), [],
            "the PUBLISHED half of the trace still carries evaluator fields")

        # and the run is still scorable from the two halves together
        merged = sealed_trace.load(path)
        self.assertEqual(len(merged), len(self.run.result.traces))
        planted = [tr for tr in merged if tr.injected]
        self.assertEqual(len(planted), 1, "the payload is not in the sealed half")
        self.assertTrue(planted[0].injected["poisoned"])
        self.assertTrue(
            all("poisoned" in w for tr in merged for w in tr.writes),
            "an item record came back from the two halves without its label")

    def test_a_public_trace_alone_refuses_to_be_scored_rather_than_scoring_clean(self):
        """N3 at the seal line, in its sharpest form.  With the labels stripped,
        `det.score` draws every item from the clean distribution, no quarantine is
        ever a true positive and the cell reports a run in which nothing was
        planted and the defence held -- a full, normal-looking grid of fake zeros.

        Both doors have to refuse: `sealed_trace.load` when the sealed file is not
        there, and `replay.rescore` when it is handed public traces anyway.

        Thesis claim (vi): "trace cong bo mot minh phai TU CHOI cham diem, khong
        duoc cham ra 0".
        """
        import replay, sealed_trace
        import policies as P
        path = self.tmp / "M3-trace.json"
        core.dump_traces(path, self.run.result.traces)
        sealed_trace.sealed_path(path).unlink()
        with self.assertRaises(sealed_trace.SealedLabelsMissing) as ctx:
            sealed_trace.load(path)
        self.assertIn("fake zero", str(ctx.exception))

        rr = replay.rescore(core.load_traces(path), a_detector(),
                            a_policy())
        self.assertFalse(rr.valid, "a stripped trace was scored instead of refused")
        self.assertIsNone(rr.harm, "a stripped trace produced a harm number")
        self.assertIn("poisoned", rr.reason)

    def test_the_seconds_in_the_cost_group_are_measured_and_not_a_row_of_zeros(self):
        """SPEC-P1b Part 1's "chi phi" row asks for REAL seconds per audit kind --
        it is the row that turns kappa from an assignment into a measurement.  A
        dict of 0.0 satisfies a presence check and measures nothing.

        Thesis claim (vi): "giay trong nhom chi phi la giay do that, khong phai 0.0".
        """
        secs = [v for tr in self.run.result.traces
                for v in tr.audit_seconds.values()]
        self.assertTrue(secs, "no audit was timed at all")
        self.assertTrue(all(s > 0.0 for s in secs),
                        f"an audit kind was recorded as costing 0.0 seconds: {secs}")


class TheM3ArtefactItself(unittest.TestCase):
    """`results/M3-trace.json` is what Task 17 PRODUCES, so it is checked like a
    result and not like a by-product.  A test that only exercises the code path is
    green on a build whose artefact was never written, or was written by an older
    version of it."""

    def setUp(self):
        self.path = m3.RESULTS / "M3-trace.json"

    def test_the_committed_m3_trace_carries_every_one_of_the_nine_field_groups(self):
        """SPEC-P1b Part 1's acceptance line for b1, read off the artefact: "trace
        co MOI truong Phan 1".  FAILS rather than skips when the file is absent --
        a skip here is the claim going dark on exactly the build that shipped no
        trace.

        Thesis claim (vi): "file trace da giao co du chin nhom truong".
        """
        self.assertTrue(self.path.exists(),
                        f"{self.path} does not exist. It is Task 17's artefact; "
                        f"regenerate it with `python3 m3.py`.")
        report = m3.field_groups(core.load_traces(self.path))
        missing = [g for g, v in report.items() if not v["present"]]
        self.assertEqual(missing, [],
                         f"the shipped M3 trace is missing field groups {missing}: "
                         f"{ {g: report[g] for g in missing} }")

    def test_the_committed_m3_trace_carries_no_ground_truth_field(self):
        """The sibling of the acceptance test above, and the one that stops this
        recurring at workflow 100.

        The committed trace used to carry `injected` with "poisoned": true, a
        `poisoned` label on all 24 item records, and `quarantines[0].correct` --
        the ground truth for every item plus whether each quarantine was right.
        That is precisely what .gitignore refuses to publish for
        `carriers-sealed/`, in its own words: "publishing it would hand over the
        labels the benchmark exists to infer". The justification for committing it
        cited the nine-field-group acceptance line, and that line needs the trace's
        SHAPE, not its labels -- the test above still passes on the stripped file.

        This is not an agent leak (results/ is outside every mount). It is worse in
        a different way: M3 sets the pattern for the full study, where this file
        becomes the complete evaluator ground truth published beside the benchmark.

        Thesis claim (vi): "trace da giao khong duoc mang mot truong ground truth nao".
        """
        import sealed_trace
        self.assertTrue(self.path.exists(), f"{self.path} does not exist")
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        leaked = sealed_trace.ground_truth_fields_in(doc)
        self.assertEqual(
            leaked, [],
            f"the COMMITTED M3 trace carries {len(leaked)} evaluator field(s): "
            f"{leaked[:8]}{' ...' if len(leaked) > 8 else ''}. These belong in "
            f"{sealed_trace.sealed_path(self.path).name}, which is gitignored "
            f"beside carriers-sealed/. Rewrite the artefact through "
            f"core.dump_traces, which splits it.")

    def test_the_shipped_m3_trace_is_a_whole_eight_task_workflow_with_its_sigma(self):
        """Nine groups on a one-task trace would still report complete.  M3 is the
        EIGHT-task milestone, and the payload has to have reached its sigma, or the
        checkpoints row is nine groups of nothing.

        WHAT THIS TEST NO LONGER READS.  It used to assert `injected["poisoned"]`
        off the committed file; that field is now in the sealed half, which is
        gitignored, so asserting it here would make the suite depend on an artefact
        a fresh clone does not have.  The same claim is made on FRESHLY GENERATED
        data by TheNineFieldGroups, which holds both halves -- so nothing was
        dropped, it moved to where both halves exist.

        Thesis claim (vi): "trace M3 la mot workflow tam task va co dung mot sigma".
        """
        self.assertTrue(self.path.exists(), f"{self.path} does not exist")
        traces = core.load_traces(self.path)
        self.assertEqual(len(traces), H, "M3 is an eight-task workflow")
        self.assertEqual([tr.t for tr in traces], list(range(H)),
                         "the tasks are not a contiguous 0..H-1 chain")
        sigma = [tr for tr in traces if tr.is_sigma]
        self.assertEqual(len(sigma), 1, "exactly one task is sigma")
        self.assertEqual(sorted(sigma[0].checkpoints), ["P1", "P2", "P3", "P4", "P5"],
                         "the sigma task does not carry the five checkpoints")
        self.assertTrue(sigma[0].writes, "the sigma task recorded no write")


class WhatM3RefusesToInvent(unittest.TestCase):
    """Rule N3 at the M3 boundary: no key, so no dollars -- and no zero either."""

    def test_the_dollar_cost_of_a_run_with_no_model_is_a_recorded_reason(self):
        """M3's cost line is the one place a plausible 0.00 would be indistinguishable
        from a measurement.  There is no API key in this environment, so no token
        was ever bought, and `0.00 USD` would read as "the run was free".

        Thesis claim (vi): "chi phi USD chua do duoc phai ghi LY DO, khong ghi 0".
        """
        cost = m3.usd_cost()
        self.assertIsNone(cost["usd"], "M3 produced a dollar figure with no API key")
        self.assertIn("reason", cost)
        self.assertTrue(cost["reason"].strip(), "the absence carries no reason")
        import llms
        self.assertEqual(cost["reason"], llms.pending_reason(cost["quantity"]),
                         "M3 started a second table of reasons instead of reusing "
                         "PENDING_MEASUREMENT")

    def test_the_sealed_manifest_records_a_reason_where_the_number_is_not_yet_measured(self):
        """`build.sealed_manifest` demands four evidence fields and M3 can supply
        one of them honestly.  The other three are recorded as reasons, because a
        sealed manifest is the evaluator's ground truth and a fabricated entry in
        it would be believed forever.

        Thesis claim (vi): "manifest niem phong ghi ly do, khong ghi so bia ra".
        """
        ev = m3.manifest_evidence(instance_source="verified")
        self.assertEqual(ev["instance_source"], "verified")
        for k in ("auc_match_ci", "n_c_at_sigma", "kappa_measured"):
            self.assertIn(m3.PENDING_KEY, ev[k],
                          f"{k} in the sealed manifest is not marked as unmeasured")
            self.assertTrue(str(ev[k][m3.PENDING_KEY]).strip(),
                            f"{k} is unmeasured and carries no reason")

    def test_the_run_report_says_which_half_of_m3_a_missing_key_left_unrun(self):
        """An honest partial M3 has to say WHICH half ran.  A report that lists the
        measured half alone reads as a complete M3 to anyone who did not run it.

        Thesis claim (vi): "bao cao phai noi ro nua nao cua M3 chua chay".
        """
        summary = m3.unmeasured()
        self.assertTrue(summary, "M3 claims nothing is unmeasured, with no API key")
        import llms
        for q in summary:
            self.assertEqual(summary[q], llms.pending_reason(q))
        for q in ("agent_patch", "cost_usd_per_task", "repository_test_command"):
            self.assertIn(q, summary)


class WhatTheContainerSeesOfEachTask(unittest.TestCase):
    """The agent's own view, read from inside the container, once per task."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="auditgame-m3-box-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _private_roots(self):
        """Point WORKSPACE, CARRIER_ROOT and HIDDEN_ROOT at roots of this test's own.

        The same move `test_hidden_test_isolation._private_roots` makes, and for
        the same two reasons.  UNDER THE PROJECT, not under the system temp dir:
        the mount has to be a path the Docker daemon may share, and the daemon may
        be a VM with its own file-sharing list.  And never the PROJECT's own roots:
        this run writes eight tasks' worth of carrier state, and a real run's
        carriers are not a test's to write into.

        The LAST SEGMENT is preserved, because the container path is
        `/workspace/<host dir name>` and the probe looks the carrier mount up by
        that name.
        """
        area = pathlib.Path(tempfile.mkdtemp(dir=harness.HERE, prefix="probe-"))
        self.addCleanup(shutil.rmtree, area, True)
        saved = (harness.WORKSPACE, harness.CARRIER_ROOT, harness.HIDDEN_ROOT)

        def restore() -> None:
            harness.WORKSPACE, harness.CARRIER_ROOT, harness.HIDDEN_ROOT = saved
        self.addCleanup(restore)
        harness.WORKSPACE = area / "workspace"
        harness.CARRIER_ROOT = area / "carriers"
        harness.HIDDEN_ROOT = area / "hidden_suites"
        harness.ensure_dirs()
        return area

    def _probe_run(self):
        why = harness.container_ready()
        if why:
            raise unittest.SkipTest(f"cannot run a container: {why}")
        self._private_roots()
        # An answer key that EXISTS, so "not reachable" is a statement about the
        # mounts rather than about an empty directory.
        (harness.HIDDEN_ROOT / "h_probe_suite.py").write_text(
            "assert False  # the answer key\n", encoding="utf-8")
        repo = harness.WORKSPACE / "m3probe"
        base = make_repo(repo)
        wf = a_workflow(repo="m3probe")
        return m3.run_workflow(wf, a_plan(wf), repo_path=repo,
                               root=harness.CARRIER_ROOT, base_commit=base,
                               det=a_detector(), pol=a_policy(),
                               ag=agent_mod.MockAgent(), seed=SEED,
                               probe=m3.container_probe)

    def test_the_repo_the_container_sees_is_back_at_this_tasks_base_commit(self):
        """The reset is a host action; what matters is the worktree the AGENT gets.
        Read from inside the container, once per task, so "the repo is reset" is a
        statement about the agent's filesystem rather than about the host's.

        Thesis claim (vi): "repo trong container dung o base_commit cua task do".
        """
        run = self._probe_run()
        self.assertEqual(len(run.probes), H, "the container was not asked once per task")
        for p in run.probes:
            self.assertEqual(p["head"], p["base_commit"],
                             f"task {p['t']}: the container sees HEAD={p['head']}, "
                             f"not base_commit={p['base_commit']}")
            # THIS task's scratch file, not the previous task's. TaskDriver
            # plants it and resets in the same call (see TaskDriver.__call__), so
            # what this observes is "the reset removed the file the driver planted
            # moments ago" -- which is the positive control that makes the reset
            # observable at all, MockAgent touching no file of its own. The
            # previous task's scratch file was already removed by the previous
            # task's reset, so it could never be here to find.
            self.assertTrue(p["scratch_absent"],
                            f"task {p['t']}: the scratch file this task's driver "
                            f"planted survived the reset and is still in the "
                            f"worktree the agent is handed")

    def test_no_answer_key_is_reachable_from_inside_any_of_the_eight_task_containers(self):
        """Task 19's rule, checked on the run that actually happened rather than on
        a hand-built argv.  The POSITIVE CONTROL is the carrier mount: a container
        whose mounts all silently failed would find no answer key either.

        Thesis claim (vi): "khong task nao trong tam task cham toi duoc dap an".
        """
        run = self._probe_run()
        for p in run.probes:
            self.assertTrue(p["carriers_visible"],
                            f"task {p['t']}: the carrier mount did not reach the "
                            f"container, so finding no answer key proves nothing")
            self.assertEqual(p["forbidden_seen"], [],
                             f"task {p['t']}: an answer key is reachable: "
                             f"{p['forbidden_seen']}")
            self.assertTrue(p["carrier_write_refused"],
                            f"task {p['t']}: the carrier mount is writable from "
                            f"inside the container")


if __name__ == "__main__":
    unittest.main()
