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

TWO ANSWER KEYS, ONE RULE.  The hidden suites are the first; `Item.poisoned` is
the second, and it is the label the whole experiment exists to infer.  Task 13
persisted it into the carrier root, which is mounted rw, so the agent could have
read -- and rewritten -- the answer to the question being put to it.  Since Task
19 it lives in SEALED_ROOT with the sealed manifest (`inject_sealed` below), and
`forbidden_roots()` names all three places so that ONE list, checked in ONE place
(`docker_argv`), decides what may not be mounted.

Blocking the mount closes the front door.  `hidden_leaks` closes the other one:
an agent that ever sees a hidden path can WRITE IT INTO A CARRIER at task t and
read it back at t+1 -- the persistence this thesis studies, turned against the
oracle.

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
import shutil
import subprocess
from typing import Optional

import build
import carrier_store_fs
import core

HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE / "workspace"          # repo clones, mounted rw
CARRIER_ROOT = HERE / "carriers"        # the four carriers, OUTSIDE every repo
HIDDEN_ROOT = HERE / "hidden_suites"    # mounted NOWHERE, run after the horizon

#: Ground truth: the per-item `poisoned` labels and the sealed manifests.  Mounted
#: NOWHERE.  Derived from CARRIER_ROOT rather than spelled out, so the two cannot
#: be moved apart by editing one of them (carrier_store_fs.sealed_root_for).
SEALED_ROOT = carrier_store_fs.sealed_root_for(CARRIER_ROOT)

#: The image built from ../Dockerfile.  A single name, because two names is how a
#: run and its reproduction end up in different environments.
IMAGE = "auditgame:latest"

#: Where every mount lands inside the container.  Fixed here rather than spelled
#: out at each call site: the agent's view of its own filesystem is part of the
#: task definition, so it may not vary between two runs of the same benchmark.
CONTAINER_ROOT = "/workspace"


def forbidden_roots() -> list:
    """Every root the agent must never reach, in one place.

    `hidden_suites` is the generated per-instance suites, `hidden_tests` the
    hand-written oracle templates they come from, and the sealed area the
    ground-truth labels plus the sealed manifests.  Leaking any one of the three
    hands over an answer key, so they are checked by one rule rather than three.

    A FUNCTION, not a constant: the sealed area follows CARRIER_ROOT, which tests
    move.  A tuple frozen at import time would keep naming the old sealed area
    after the move, and `docker_argv` would guard a directory nobody is using.
    """
    return [HIDDEN_ROOT, HERE / "hidden_tests",
            carrier_store_fs.sealed_root_for(CARRIER_ROOT)]


def ensure_dirs() -> None:
    """Create the four roots if they are missing.

    HIDDEN_ROOT and the sealed area are created too, and that is deliberate:
    `mounts()` must be shown to leave out directories that EXIST.  Leaving them
    absent would let the isolation tests pass against paths that simply are not
    there yet, and the claim would quietly become "we have not generated the
    hidden suites" instead of "the agent cannot reach them".
    """
    for d in (WORKSPACE, CARRIER_ROOT, HIDDEN_ROOT, SEALED_ROOT):
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
        # The guard lives in the PRODUCTION path, not only in the gate-1 tests.
        # Every test in test_hidden_test_isolation.py runs against today's
        # `mounts()`; none of them runs when a mount is added tomorrow in a branch
        # whose tests nobody ran.  This is the single place a `-v` may be built,
        # so it is the place that can refuse -- in BOTH directions, because a
        # mount of `hidden_suites/astropy` is not an ancestor of `hidden_suites`
        # and the ancestor test alone waves it straight through while the agent
        # reads the answer key for the instance it is being graded on.
        h = host.resolve()
        for secret in forbidden_roots():
            s = secret.resolve()
            if s == h or s.is_relative_to(h) or h.is_relative_to(s):
                raise AssertionError(
                    f"refusing to mount {h}: it would put {s} inside the "
                    f"container. That directory is an answer key -- the hidden "
                    f"suites or the ground-truth labels -- and an agent that can "
                    f"read it makes `harm` unmeasurable rather than optimistic.")
        args += ["-v", f"{h}:{CONTAINER_ROOT}/{h.name}:{mode}"]
    return args + [IMAGE] + list(cmd)


def container_ready() -> str:
    """Empty string when a real container run is possible, else the reason not.

    Here rather than in a test file because two test modules ask it, and two
    copies of "is Docker usable" is two ways for a skip to drift into a silent
    green on one side and not the other.
    """
    if shutil.which("docker") is None:
        return "no docker executable on PATH"
    ping = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                          capture_output=True, text=True)
    if ping.returncode != 0:
        return "docker daemon not reachable"
    img = subprocess.run(["docker", "image", "inspect", IMAGE],
                         capture_output=True, text=True)
    if img.returncode != 0:
        return f"image {IMAGE} not built (docker build -t {IMAGE} ..)"
    return ""


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


# --------------------------------------------------------------------- tier 2

def hidden_needles() -> list:
    """Strings whose presence in a carrier means an answer key travelled.

    Three kinds, because a leak can be written down three ways: the directory
    NAME (`hidden_suites`), the absolute PATH, and the name of a FILE inside --
    `hidden_tests/h1_deprecation.py` is the more useful half of the leak, since it
    names the suite the agent is about to be graded by, and a needle list holding
    only directory names misses it entirely.

    File names keep their extension on purpose.  The bare stem would match an
    ordinary agent note ("agreement", "diffutil" are English words a SE agent
    writes), and a gate that cries wolf on honest runs is a gate somebody turns
    off.  `__init__.py` and dotfiles are dropped for the same reason, and so are
    needles under four characters.
    """
    needles = set()
    for root in forbidden_roots():
        needles.update({root.name, str(root), str(root.resolve())})
        if root.is_dir():
            for p in root.rglob("*"):
                if p.is_file() and "__pycache__" not in p.parts \
                        and not p.name.startswith(("__", ".")):
                    needles.add(p.name)
    return sorted(n.casefold() for n in needles if len(n) >= 4)


def hidden_leaks(store) -> list:
    """(carrier, item_id, needle) for every carrier item that names an answer key.

    Scans the FULL serialised record of every item, not `content` and `provenance`
    alone: a path smuggled in the topic or in the propagation trail is the same
    leak, and a field list is exactly the kind of check that goes green because
    its scope is narrower than the sentence it stands for.

    Scans `store.items`, not `store.live()`.  Quarantine is the DEFENDER's action;
    an item the defence removed still travelled and still proves the path leaked,
    so filtering it out would let the oracle's own audit conceal the oracle's own
    leak.  All four carriers, because `skill` items are induced from trajectories
    and inherit whatever the trajectory saw -- and because `branch` is the one
    carrier a directory walk would miss (it lives in the repo's object database).
    """
    needles = hidden_needles()
    leaks = []
    for c in core.CARRIERS:
        for it in store.items[c]:
            blob = core.dumps(core.item_record(it)).casefold()
            leaks += [(c, it.item_id, n) for n in needles if n in blob]
    return leaks


# ------------------------------------------------------------- ground truth

def inject_sealed(store, wf, ps, *, auc_match_ci, n_c_at_sigma, kappa_measured,
                  instance_source) -> tuple:
    """Plant the payload into a filesystem store AND seal the manifest beside it.

    ONE door for both, because they are one act.  `build.inject` writes the payload
    into a carrier the container can read, and the carrier no longer records which
    item that was -- so an injection whose manifest was not sealed is a run whose
    payload nobody can identify afterwards, and every harm figure from it is
    unscorable.  Two separate calls at the call site is one forgotten line away
    from exactly that.

    This is `build.sealed_manifest`'s call site.  It was written in Task 21 and
    left unwired, which is how the evaluator's record of the ground truth came to
    exist as a function that produced a dict nobody stored.  The four evidence
    fields stay keyword-only and mandatory all the way through: a default here
    would answer a reviewer's question silently.
    """
    injected = build.inject(store, wf, ps)
    manifest = build.sealed_manifest(wf, ps, injected, auc_match_ci=auc_match_ci,
                                     n_c_at_sigma=n_c_at_sigma,
                                     kappa_measured=kappa_measured,
                                     instance_source=instance_source)
    store.seal_manifest(manifest)
    return injected, manifest
