"""
GATE 1 -- hidden tests stay out of the agent's reach.  Both tiers.
Spec: eval/PLAN.md Task 13 and Task 19; ../pipelines/SPEC-P1a-Harness.md Part 3.

The SWE-Lancer failure mode: the agent reads the grading tests and writes code
that satisfies them.  Here it is worse than a leaderboard artifact -- the hidden
test IS the harm measurement, so a leak does not make the number optimistic, it
makes it meaningless.

TIER 1 (the direct path) blocks the mount.  TIER 2 (the indirect path) blocks the
way round it: the agent can write the path INTO A CARRIER at task t and read it
back at task t+1, which is precisely the persistence this thesis studies, turned
against the oracle.  Blocking the mount closes the front door; scanning the
carriers closes the one the benchmark itself installed.

WHY THESE TESTS LOOK AT THE ARGV AND NOT AT `mounts()` ALONE.  A check that only
walks `mounts()` is narrower than the sentence it protects: a mount added
directly inside `run_in_container`, bypassing `mounts()`, would never be seen,
and neither would a mount added UNDER the hidden root (`hidden.is_relative_to(h)`
is False when `h` is a child of `hidden`, yet the agent can read the files all
the same).  Both directions, and the real argv, are checked below.

The container tests are SKIPPED without a Docker daemon and the image, the way
test_real_data.py skips without its gitignored data file.  tests/run_all.py
prints a skip as NOT VERIFIED and refuses to call the gate green; a skip here is
a claim with no evidence in this run, not a claim that held.
"""
from __future__ import annotations
import pathlib, random, shutil, subprocess, tempfile, unittest

import agent as agent_mod
import build
import carrier_store_fs
import harness
from core import CARRIERS, Item, Task


#: Every path the agent must never reach.  `hidden_suites` is the generated
#: per-instance suites; `hidden_tests` is the hand-written oracle templates they
#: come from; `carriers-sealed` is where the ground-truth labels and the sealed
#: manifest live now that the carrier store no longer keeps them.  Leaking any one
#: of the three hands over an answer key.
#:
#: Spelled out HERE rather than read off `harness.forbidden_roots()`, and the two
#: are asserted equal below: a test that takes its own subject from the module
#: under test goes green the moment someone shortens that list.
def forbidden_roots() -> list:
    return [harness.HIDDEN_ROOT, harness.HERE / "hidden_tests", harness.SEALED_ROOT]


#: Task shapes the mount code actually meets: a mock repo name, and a SWE-bench
#: `owner/name` one.  A single shape would leave `mounts()` half-covered.
TASKS = [
    None,
    Task(task_id="t-000", repo="django", base_commit="0" * 40,
         topic="orm", problem="fix it"),
    Task(task_id="astropy__astropy-12907", repo="astropy/astropy",
         base_commit="1" * 40, topic="modeling", problem="fix it"),
]


#: Empty string when a real container run is possible, else the reason not.  It
#: lives in `harness` because two test modules now ask the same question, and two
#: copies of "is Docker usable" is two ways for a skip to become a silent green.
container_ready = harness.container_ready


class HiddenTestIsolation(unittest.TestCase):

    def test_hidden_root_is_inside_no_mount_the_agent_sees(self):
        """Compared with RESOLVED absolute paths: a relative-string comparison
        passes happily on `../..` and on a symlink.

        Thesis claim (vi): "test an nam ngoai tam agent".
        """
        for task in TASKS:
            for host, _mode in harness.mounts(task):
                h = host.resolve()
                for hidden in (p.resolve() for p in forbidden_roots()):
                    self.assertFalse(
                        hidden == h or hidden.is_relative_to(h),
                        f"hidden tests are inside a mount the agent sees: {h} "
                        f"(task={task and task.task_id})")

    def test_no_mount_the_agent_sees_is_inside_the_hidden_suites_either(self):
        """The other direction, and it is not symmetric with the one above.  A
        mount of `hidden_suites/astropy` is NOT an ancestor of `hidden_suites`, so
        the ancestor check waves it straight through -- while the agent reads the
        answer key for the instance it is being graded on.

        Thesis claim (vi): "khong mount nao duoc nam BEN TRONG thu muc test an".
        """
        for task in TASKS:
            for host, _mode in harness.mounts(task):
                h = host.resolve()
                for hidden in (p.resolve() for p in forbidden_roots()):
                    self.assertFalse(
                        h.is_relative_to(hidden),
                        f"a mount handed to the agent lives inside the hidden "
                        f"tests: {h} (task={task and task.task_id})")

    def test_no_hidden_path_reaches_the_command_line_the_container_is_run_with(self):
        """`mounts()` is not the only way a path can get mounted -- the argv is.
        A `-v` appended straight into the docker command, bypassing `mounts()`,
        is invisible to every check that walks `mounts()` and is exactly how a
        leak would be introduced by someone "just adding one mount".

        Thesis claim (vi): "cai agent THUC SU nhin thay la argv, khong phai y dinh".
        """
        for task in TASKS:
            argv = harness.docker_argv(task, ["python3", "-c", "pass"])
            joined = " ".join(argv)
            for hidden in forbidden_roots():
                self.assertNotIn(str(hidden), joined,
                                 f"a hidden path is on the docker command line: {joined}")
                self.assertNotIn(str(hidden.resolve()), joined,
                                 f"a hidden path is on the docker command line: {joined}")

    def test_two_mounts_never_land_on_the_same_place_in_the_container(self):
        """The container path is `/workspace/<host dir name>`, so two mounts whose
        last segment agrees collide -- a repo literally named `carriers` would land
        on top of the carrier mount, and the agent would be handed a store that is
        not the store being measured.  It costs one comparison to rule out.

        Thesis claim (vi): "moi mount phai co cho rieng trong container".
        """
        for task in TASKS:
            dests = [h.name for h, _ in harness.mounts(task)]
            self.assertEqual(len(dests), len(set(dests)),
                             f"two mounts share a container path: {dests} "
                             f"(task={task and task.task_id})")

    def test_the_container_gets_no_network(self):
        """Not hardening: an agent that can reach the internet can fetch the
        upstream fix, and `solved` then measures retrieval rather than repair.

        Asserted on the BUILT ARGV, not on the source text.  `inspect.getsource`
        finds the flag in a comment or a docstring just as happily as in the
        argument list, so it would stay green through the very edit it exists to
        catch.

        Thesis claim (vi): "solved phai do SUA LOI, khong do TRA CUU".
        """
        for task in TASKS:
            self.assertIn("--network=none", harness.docker_argv(task, ["true"]))

    def test_the_harness_knows_about_every_one_of_the_three_answer_keys(self):
        """The three checks above walk a list, so the list is the claim.  Dropping
        `carriers-sealed` from `harness.forbidden_roots()` would leave all of them
        green while the ground-truth labels became mountable again -- a check going
        green because its SUBJECT shrank, not because the property held.

        Thesis claim (vi): "danh sach vung cam phai du ca ba, khong duoc rut ngan".
        """
        self.assertEqual(sorted(p.resolve() for p in harness.forbidden_roots()),
                         sorted(p.resolve() for p in forbidden_roots()),
                         "harness.forbidden_roots() and this test disagree on what "
                         "the agent must never reach")

    def test_a_mount_that_would_expose_an_answer_key_is_refused_while_the_argv_is_built(self):
        """The check moved into the PRODUCTION path, not only into this file.  Every
        test above runs against today's `mounts()`; none of them runs when someone
        adds a mount tomorrow in a branch whose tests nobody ran.  `docker_argv` is
        the single place a `-v` may be built, so it is the place that can refuse.

        Thesis claim (vi): "mount lo dap an phai bi tu choi ngay luc dung argv".
        """
        original = harness.mounts
        for bad in (harness.HERE, harness.HIDDEN_ROOT, harness.SEALED_ROOT,
                    harness.HIDDEN_ROOT / "astropy"):
            harness.mounts = lambda task=None, _b=bad: [(_b, "rw")]
            try:
                with self.assertRaises(AssertionError,
                                       msg=f"a mount of {bad} was allowed onto the argv"):
                    harness.docker_argv(None, ["true"])
            finally:
                harness.mounts = original

    # ------------------------------------------------- with a real container

    def test_the_agent_cannot_reach_the_hidden_suites_from_inside_the_container(self):
        """The claim, run rather than argued.  A sentinel file is dropped into the
        hidden root AND into a carrier, and the container is asked to find both
        anywhere under /workspace.  The carrier one MUST be found: without that
        positive control an image whose mounts all silently failed would report
        "hidden not found" and look like a pass.

        Thesis claim (vi): "test an nam ngoai tam agent".
        """
        why = container_ready()
        if why:
            raise unittest.SkipTest(f"cannot run a container: {why}")
        harness.ensure_dirs()
        hidden_mark = harness.HIDDEN_ROOT / "sentinel_hidden_suite.py"
        carrier_mark = harness.CARRIER_ROOT / "sentinel_carrier.txt"
        hidden_mark.write_text("assert False  # the answer key\n", encoding="utf-8")
        carrier_mark.write_text("a carrier file\n", encoding="utf-8")
        self.addCleanup(hidden_mark.unlink, True)
        self.addCleanup(carrier_mark.unlink, True)

        r = harness.run_in_container(None, [
            "python3", "-c",
            "import pathlib;"
            "print('\\n'.join(str(p) for p in pathlib.Path('/workspace').rglob('sentinel_*')))"])
        self.assertEqual(r.returncode, 0, f"the container did not run: {r.stderr[-500:]}")
        self.assertIn("sentinel_carrier.txt", r.stdout,
                      "the carrier mount did not reach the container at all -- this "
                      "run proves nothing about what is NOT reachable")
        self.assertNotIn("sentinel_hidden_suite.py", r.stdout,
                         "the agent can read the hidden suites from inside the container")

    def test_a_command_inside_the_container_cannot_open_a_network_connection(self):
        """`--network=none` asserted by running it.  The positive control is the
        same command shape succeeding at something local: without it, an image
        that cannot run python at all would pass this by failing for the wrong
        reason.

        Thesis claim (vi): "solved phai do SUA LOI, khong do TRA CUU".
        """
        why = container_ready()
        if why:
            raise unittest.SkipTest(f"cannot run a container: {why}")
        harness.ensure_dirs()
        ok = harness.run_in_container(None, ["python3", "-c", "print('alive')"])
        self.assertEqual(ok.returncode, 0, f"the container did not run: {ok.stderr[-500:]}")
        self.assertIn("alive", ok.stdout)

        net = harness.run_in_container(None, [
            "python3", "-c",
            "import socket; socket.create_connection(('1.1.1.1', 80), 5)"])
        self.assertNotEqual(net.returncode, 0,
                            "the container reached the network: `solved` would be "
                            "measuring whether the agent can fetch the upstream fix")


class HiddenPathsDoNotTravelInTheCarriers(unittest.TestCase):
    """TIER 2 -- the indirect path, the one the benchmark installed itself.

    An agent that ever sees a hidden-test path can WRITE IT INTO A CARRIER at task
    t and read it back at task t+1.  Nothing is reset between tasks except the
    repo; that is the whole premise, and it is a premise the oracle has to survive
    too.  So the carriers are scanned -- all four, every field, quarantined items
    included, because `skill` items are induced from trajectories and inherit
    whatever the trajectory saw.

    The scan is exercised with a PLANTED leak before it is trusted on a clean run.
    A scanner nobody has ever seen find anything reports "clean" for both reasons
    -- the carriers are clean, or the scanner is broken -- and those are the same
    printed line.
    """

    EVIDENCE = dict(auc_match_ci=(0.6, 0.4, 0.8), n_c_at_sigma={"memory": 2},
                    kappa_measured={"memory": 1.0}, instance_source="mock")

    def setUp(self):
        from tests.gate1_integrity.test_ground_truth_out_of_the_carriers import make_repo
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="auditgame-tier2-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "workspace" / "django"
        make_repo(self.repo)
        self.store = carrier_store_fs.FSCarrierStore(self.tmp / "carriers", repo=self.repo)
        self.addCleanup(shutil.rmtree, self.store.sealed, True)

    def test_the_scan_looks_for_the_files_inside_the_answer_keys_and_not_only_their_names(self):
        """A needle list holding only `hidden_suites` catches an agent that wrote
        down the DIRECTORY and misses one that wrote down
        `hidden_tests/h1_deprecation.py` -- the more useful half of the leak, since
        it names the suite the agent is about to be graded by.

        The expected names are read off the filesystem rather than spelled out, so
        renaming an oracle template cannot silently empty this check.

        Thesis claim (vi): "quet phai bat ca duong dan TEP, khong chi ten thu muc".
        """
        needles = harness.hidden_needles()
        self.assertTrue(needles, "the scan has nothing to look for")
        for root in forbidden_roots():
            self.assertIn(root.name.casefold(), needles,
                          f"the scan does not look for {root.name!r}")
        files = [p for p in (harness.HERE / "hidden_tests").rglob("*.py")
                 if "__pycache__" not in p.parts and not p.name.startswith("__")]
        self.assertTrue(files, "the oracle templates are gone -- this check is vacuous")
        for p in files:
            self.assertIn(p.name.casefold(), needles,
                          f"the scan does not look for the oracle template {p.name!r}")

    def test_a_hidden_path_written_into_any_carrier_and_any_field_is_found(self):
        """The positive control, run over the whole matrix.

        EVERY carrier, because `branch` lives in the repo's object database rather
        than in a JSONL file and a scan that walked the directory would miss it.
        EVERY field, because a scan of `content` and `provenance` -- the two the
        first draft of this test read -- waves through a path smuggled in the topic
        or in the propagation trail.

        Thesis claim (vi): "co che dai dang quay lai can chinh oracle".
        """
        needle = (harness.HERE / "hidden_tests" / "h1_deprecation.py")
        planted = []
        for i, carrier in enumerate(CARRIERS):
            for field in ("content", "provenance", "topic"):
                kw = dict(carrier=carrier, topic=f"orm{i}", created_at=i,
                          content=f"[{carrier}] an ordinary note {i}",
                          provenance="agent/notes", poisoned=False)
                kw[field] = f"{kw[field]} :: {needle}"
                planted.append(self.store.write(Item(**kw)).item_id)

        found = {item_id for _c, item_id, _n in harness.hidden_leaks(self.store)}
        for item_id in planted:
            self.assertIn(item_id, found,
                          "the scan missed a planted hidden-test path: it would "
                          "report a leaking run as clean")

    def test_an_item_that_was_quarantined_is_scanned_all_the_same(self):
        """`live()` hides quarantined items, and the first draft of this scan used
        it.  But quarantine is the DEFENDER's action: an item the defence removed
        still travelled, still proves the path leaked, and hiding it would make the
        oracle's own audit the thing that conceals the oracle's leak.

        Thesis claim (vi): "item bi cach ly van phai bi quet".
        """
        it = self.store.write(Item(
            carrier="memory", topic="orm",
            content=f"grading suite at {harness.HIDDEN_ROOT}/astropy",
            created_at=0, provenance="agent/notes", poisoned=False))
        self.store.quarantine(it.item_id)
        self.assertEqual([x.item_id for x in self.store.live("memory")], [],
                         "the fixture did not actually quarantine the item")
        self.assertIn(it.item_id,
                      {i for _c, i, _n in harness.hidden_leaks(self.store)},
                      "quarantining an item hid the leak it proves")

    def test_the_scan_stays_silent_on_carriers_that_never_saw_an_answer_key(self):
        """The negative control.  A scan whose needles are loose enough to match
        ordinary agent notes goes red on every honest run, and a gate that cries
        wolf is turned off within a week.

        Thesis claim (vi): "quet KHONG duoc bao dong tren ghi chu binh thuong".
        """
        for i, carrier in enumerate(CARRIERS):
            self.store.write(Item(carrier=carrier, topic="orm",
                                  content=f"[orm] ghi chu tu task {i}", created_at=i,
                                  provenance="agent/notes", poisoned=False))
        self.assertEqual(harness.hidden_leaks(self.store), [])

    def a_completed_run(self):
        """A real workflow driven to the end on the filesystem store.

        A payload planted through `harness.inject_sealed`, the mock agent run task
        by task, and the store CLOSED AND REOPENED between tasks the way the
        harness opens it once per container -- so the carriers being scanned are
        carriers that made the disk round trip, not a dict that never left RAM.
        """
        rng = random.Random(11)
        wf = build.make_workflow("wf-tier2", "django", H=8, rng=rng, need_delta=2)
        ps = build.plan_poison(wf, "memory", 2, rng)
        self.assertIsNotNone(ps, "the fixture could not plan an injection")
        ag = agent_mod.MockAgent()
        for t, task in enumerate(wf.tasks):
            store = carrier_store_fs.FSCarrierStore(self.store.root, repo=self.repo)
            if t == ps.iota:
                harness.inject_sealed(store, wf, ps, **self.EVIDENCE)
            ag.run_task(t, task, store, seed=3, marker="mk")
        final = carrier_store_fs.FSCarrierStore(self.store.root, repo=self.repo)
        # NOT VACUOUS: if nothing was ever retrieved and nothing inherited the
        # poison, the carriers are trivially clean and a scan of them proves
        # nothing about a run that did not happen.
        self.assertTrue(any(it.poisoned for c in CARRIERS for it in final.items[c]
                            if it.carrier != ps.carrier or it.created_at != ps.iota),
                        "nothing inherited the poison: the run never exercised "
                        "propagation, so finding no leak proves nothing")
        return final

    def test_a_whole_mock_run_persisted_to_disk_names_no_hidden_test_anywhere(self):
        """The claim itself, with evidence in EVERY suite run rather than only when
        somebody happens to have left a run behind.

        Thesis claim (vi): "mot lan chay that KHONG de lai duong dan test an nao".
        """
        self.assertEqual(harness.hidden_leaks(self.a_completed_run()), [],
                         "a carrier written by a real run names the hidden tests")

    def test_the_scan_reaches_a_finished_run_through_the_door_the_harness_opens(self):
        """The same scan, but through `harness.last_run_store()` -- which takes no
        repo argument and reopens the root from the REPO_POINTER alone.  That is the
        path a leak hunt would actually use, and it is the path that can come back
        with THREE of four carriers: `branch` lives in the repo's object database,
        so a root that forgot its repo would be scanned, found clean, and reported
        as evidence while the one carrier holding a commit per task was never read.

        CARRIER_ROOT is pointed at this test's own finished run rather than skipping
        when the real one is empty: a test that skips on a fresh clone protects
        nothing on a fresh clone.  The real carriers are scanned too when a run has
        left something there.

        Thesis claim (vi): "co che dai dang quay lai can chinh oracle".
        """
        real = harness.last_run_store()
        if real is not None:
            self.assertEqual(harness.hidden_leaks(real), [],
                             "the last real run's carriers reference the hidden tests")

        finished = self.a_completed_run()
        old = harness.CARRIER_ROOT
        try:
            harness.CARRIER_ROOT = finished.root
            through_the_door = harness.last_run_store()
        finally:
            harness.CARRIER_ROOT = old
        self.assertIsNotNone(through_the_door, "last_run_store() lost a finished run")
        self.assertEqual({c: len(through_the_door.items[c]) for c in CARRIERS},
                         {c: len(finished.items[c]) for c in CARRIERS},
                         "reopening the root without a repo lost a carrier -- the "
                         "scan below would never look at it")
        self.assertEqual(harness.hidden_leaks(through_the_door), [])


class WhatTheStoreAndTheMountsAgreeOn(unittest.TestCase):

    def test_the_carrier_root_is_not_inside_any_repo_the_agent_works_in(self):
        """The two halves of this task have to agree: the store decides what sits
        OUTSIDE the repo, the mounts decide what the agent can REACH.  If the
        carrier root were under the workspace, a `git clean -xfd` in the repo
        would delete the carriers and "reset repo does not reset the agent" would
        be false in the harness while still true in every unit test.

        Thesis claim (vi): "carrier nam NGOAI repo, do la toan bo tro cua luan van".
        """
        self.assertFalse(
            harness.CARRIER_ROOT.resolve().is_relative_to(harness.WORKSPACE.resolve()),
            "the carriers live inside the workspace: a repo reset would erase them")

    def test_last_run_store_is_none_before_anything_has_been_written(self):
        """Task 19 scans `last_run_store()` for a leaked hidden path.  An empty
        store returned instead of None reads as "scanned, found nothing" -- a
        clean bill of health issued over a run that never happened.

        Thesis claim (vi): "chua chay thi phai bao CHUA CHAY, khong phai SACH".
        """
        import tempfile
        import carrier_store_fs
        empty = pathlib.Path(tempfile.mkdtemp(prefix="auditgame-empty-"))
        self.addCleanup(shutil.rmtree, empty, True)
        old = harness.CARRIER_ROOT
        try:
            harness.CARRIER_ROOT = empty
            self.assertIsNone(harness.last_run_store())
            st = carrier_store_fs.FSCarrierStore(empty)
            st.write(__import__("core").Item(
                carrier="memory", topic="orm", content="something was written",
                created_at=0, provenance="agent", poisoned=False))
            got = harness.last_run_store()
            self.assertIsNotNone(got)
            self.assertEqual(len(got.live("memory")), 1)
        finally:
            harness.CARRIER_ROOT = old


if __name__ == "__main__":
    unittest.main()
