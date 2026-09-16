"""
GATE 1 -- hidden tests stay out of the agent's reach.  TIER 1: the direct path.
Spec: eval/PLAN.md Task 13; ../pipelines/SPEC-P1a-Harness.md Part 3.

The SWE-Lancer failure mode: the agent reads the grading tests and writes code
that satisfies them.  Here it is worse than a leaderboard artifact -- the hidden
test IS the harm measurement, so a leak does not make the number optimistic, it
makes it meaningless.

Tier 2, which scans the carriers for a path written into memory at one task and
used at the next, needs a completed run to scan and lives in Task 19.

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
import pathlib, shutil, subprocess, unittest

import harness
from core import Task


#: Every path the agent must never reach.  `hidden_suites` is the generated
#: per-instance suites; `hidden_tests` is the hand-written oracle templates they
#: come from -- leaking either one hands over the answer key.
def forbidden_roots() -> list:
    return [harness.HIDDEN_ROOT, harness.HERE / "hidden_tests"]


#: Task shapes the mount code actually meets: a mock repo name, and a SWE-bench
#: `owner/name` one.  A single shape would leave `mounts()` half-covered.
TASKS = [
    None,
    Task(task_id="t-000", repo="django", base_commit="0" * 40,
         topic="orm", problem="fix it"),
    Task(task_id="astropy__astropy-12907", repo="astropy/astropy",
         base_commit="1" * 40, topic="modeling", problem="fix it"),
]


def container_ready() -> str:
    """Empty string when a real container run is possible, else the reason not."""
    if shutil.which("docker") is None:
        return "no docker executable on PATH"
    ping = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                          capture_output=True, text=True)
    if ping.returncode != 0:
        return "docker daemon not reachable"
    img = subprocess.run(["docker", "image", "inspect", harness.IMAGE],
                         capture_output=True, text=True)
    if img.returncode != 0:
        return f"image {harness.IMAGE} not built (docker build -t {harness.IMAGE} ..)"
    return ""


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
