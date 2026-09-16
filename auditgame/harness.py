"""
harness.py -- what the agent can see, and what it must not.

The single place that knows which host paths are mounted into the container.  It
lives beside the carrier store on purpose: the store decides what sits OUTSIDE the
repo, mounts decide what the agent can REACH, and if those two facts live in
different modules they drift apart quietly.

HIDDEN_ROOT is a SIBLING of the workspace, never a descendant.  A descendant would
be one careless mounts() entry away from being visible, and the hidden tests ARE
the harm measurement -- a leak does not make the number optimistic, it makes it
meaningless (the SWE-Lancer failure).

The image is the AGENT's environment, not the measurement's.  This module is part
of the measurement, so it shells out to `docker` with subprocess rather than
importing a Docker SDK: the measurement core has to import on a bare stdlib
interpreter (tests/gate1_integrity/test_environment.py), and "reproduce our
numbers" must not start with "first install a Docker client library".

The two facts worth knowing about `docker_argv`:

  * it exists so the argv can be ASSERTED ON.  A test that reads the source of
    run_in_container finds `--network=none` in a comment as happily as in the
    argument list, which is the narrower-than-the-claim defect this project has
    produced six times.
  * it is the ONLY place a `-v` is allowed to be built.  A mount appended
    somewhere else would be invisible to every check that walks mounts().
"""
from __future__ import annotations
import pathlib
import subprocess
from typing import Optional

import carrier_store_fs
import core

HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE / "workspace"          # repo clones, mounted rw
CARRIER_ROOT = HERE / "carriers"        # the four carriers, OUTSIDE every repo
HIDDEN_ROOT = HERE / "hidden_suites"    # mounted NOWHERE, run after the horizon

#: The image built from ../Dockerfile.  A single name, because two names is how a
#: run and its reproduction end up in different environments.
IMAGE = "auditgame:latest"

#: Where every mount lands inside the container.  Fixed here rather than spelled
#: out at each call site: the agent's view of its own filesystem is part of the
#: task definition, so it may not vary between two runs of the same benchmark.
CONTAINER_ROOT = "/workspace"


def ensure_dirs() -> None:
    """Create the three roots if they are missing.

    HIDDEN_ROOT is created too, and that is deliberate: `mounts()` must be shown
    to leave out a directory that EXISTS.  Leaving it absent would let the
    isolation tests pass against a path that simply is not there yet, and the
    claim would quietly become "we have not generated the hidden suites" instead
    of "the agent cannot reach them".
    """
    for d in (WORKSPACE, CARRIER_ROOT, HIDDEN_ROOT):
        d.mkdir(parents=True, exist_ok=True)


def mounts(task=None) -> list:
    """(host path, mode) pairs handed to the container.  HIDDEN_ROOT is never here."""
    if task is None:
        return [(WORKSPACE, "rw"), (CARRIER_ROOT, "rw")]
    return [(WORKSPACE / task.repo, "rw"), (CARRIER_ROOT, "rw")]


def docker_argv(task, cmd: list) -> list:
    """The exact command line `run_in_container` will execute.

    Separated from the run so a test can read it.  `--network=none` and the `-v`
    list are the two things this benchmark's validity rests on, and both are
    claims about the ARGV -- not about the source text that produces it.
    """
    args = ["docker", "run", "--rm", "--network=none"]
    for host, mode in mounts(task):
        args += ["-v", f"{host}:{CONTAINER_ROOT}/{host.name}:{mode}"]
    return args + [IMAGE] + list(cmd)


def run_in_container(task, cmd: list):
    """Run one command with exactly the mounts above, and no network.

    --network=none is not a hardening detail: an agent that can reach the internet
    can fetch the upstream fix, and `solved` would then measure retrieval instead
    of repair.
    """
    return subprocess.run(docker_argv(task, cmd), capture_output=True, text=True)


def last_run_store() -> Optional[core.CarrierStore]:
    """The carriers a completed run left behind, or None if there is no such run.

    None rather than an empty store, on purpose.  Task 19's tier-2 check scans
    this for a hidden-test path carried from one task to the next; an empty store
    handed back would be scanned, found clean, and reported as evidence -- a
    clean bill of health issued over a run that never happened.

    It takes no repo argument, which is why the carrier root records the repo
    holding its `branch` carrier (carrier_store_fs.REPO_POINTER).  Without that,
    this would return three carriers out of four and the scan would never look at
    the fourth.
    """
    if not CARRIER_ROOT.is_dir():
        return None
    store = carrier_store_fs.FSCarrierStore(CARRIER_ROOT)
    return store if any(store.items[c] for c in core.CARRIERS) else None
