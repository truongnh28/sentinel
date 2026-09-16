"""
carrier_store_fs.py -- the four carriers, on a real filesystem, OUTSIDE the repo.

`core.CarrierStore` is a dict in RAM.  That is enough to measure a policy, but it
cannot DEMONSTRATE the property the benchmark exists to study: the repo is reset
to each task's `base_commit` and the agent's state is not.  Nothing is ever reset
in RAM, so "survives the reset" is a claim with no experiment behind it.

This store puts the same four carriers where the reset can be run against them:

    memory / skill / queue    JSONL files under `root`, a SIBLING of the repo
    branch                    git refs inside the repo's OWN `.git`

`branch` is deliberately the odd one out -- decision B-1.  The reset is
`git clean -xfd` plus `git checkout <base_commit>`: it rebuilds the WORKTREE and
keeps `.git`.  So a carrier stored as a git ref survives BECAUSE `.git` is kept,
while a worktree file does not survive at all.  Storing `branch` beside the other
three would make it survive for a reason that has nothing to do with git, and the
one carrier that can actually exercise the B-1 decision would stop exercising it.

Everything read back comes from `core.item_record` / `core.item_from_record`, the
same round trip the traces use, so the two on-disk formats cannot drift apart.
`item_id` is passed back EXPLICITLY rather than rehashed -- see that function; a
token-set topic returns from JSON as a plain frozenset whose str() is not the
canonical form, and rehashing would move every id and therefore every score.

Reads are served from an in-memory mirror loaded at construction, so `live`,
`retrieve` and `snapshot` are literally `core.CarrierStore`'s own methods (this
class subclasses it) and cannot answer differently.  The consequence to know:
ONE writer per root.  Two live objects over the same root do not see each other's
writes; re-open the root to pick up another process's.

GROUND TRUTH IS NOT IN HERE -- the open question Task 13 left, settled in Task 19.
`core.item_record` includes `poisoned`, the flag whose own docstring says audit
policies must not read it, and `harness.mounts()` used to hand this whole root to
the container READ-WRITE.  Nothing read it there while the agent was a mock, so no
number in this build ever depended on it; but Tasks 14/16/17 put a real LLM agent
at exactly that mount, and a file saying "this item is the payload" is the same
leak shape as the hidden tests -- harm would measure whether the agent can read a
label rather than whether the attack works, and the agent could WRITE the label
too.

So what lands under `root` is `public_record`, which is `core.item_record` minus
SEALED_FIELDS, and the labels go to `sealed_root_for(root)`: a SIBLING, mounted
nowhere, alongside the sealed manifest (`build.sealed_manifest`, Task 21).  The
in-memory `Item.poisoned` is untouched -- the runner's Q_true/Q_false accounting,
`detector.score` and the manifest all still read it -- and it is recovered at load
from the sealed side.  A LOAD WITH NO LABEL IS AN ERROR, not a False: a missing
label read as "clean" turns every payload into an ordinary note, undercounts harm,
and says nothing while doing it.

MOVING THE LABEL OUT IS ONLY HALF OF IT.  A label bound to an `item_id` and to
nothing else is a label bound to a string a writer can retype:
rewrite `content` and keep the id, and the payload's ground truth attaches to what
the agent wrote; delete the line, and the payload leaves every count in silence.
So the sealed record carries `line_digest` of the exact public line as well as the
label, `_rejoin` refuses a record whose bytes moved, and
`_refuse_a_record_count_that_moved` refuses a store whose number of records is no
longer the number of labels.  Both raise `CarrierTampered`, a subclass of
`GroundTruthMissing`, because the consequence is the one that class already names.

A DIGEST BINDS A LINE TO A LABEL AND NOTHING ELSE, which leaves two moves that
never touch a byte.  COPY a sealed line -- into another carrier's file, or twice
into its own -- and every digest still matches while the poisoned-item count goes
1 -> 2: `Q_true`/`Q_false` double-count and the same `item_id` is live in two
carriers, the state `core.CarrierStore.write`'s collision guard exists to refuse
("quarantining one item would ERASE THE OTHER") and the one place that guard was
never run.  MOVE a sealed line from `memory.jsonl` into `queue.jsonl` and the
count does not move at all, while the payload is accounted to the wrong carrier
and per-carrier accounting (kappa, n_c) mis-attributes it.  So the load path
counts as a MULTISET and compares it for equality with the labels, and every line
must agree with the FILE it was read from about which carrier it is in.

A DIGEST, A COUNT AND A CARRIER LOOK EXHAUSTIVE, AND THEIR COMPLEMENT IS POSITION.
A line is bound to a label, the label set is bound to a count, and a line is bound
to the file it was found in -- and none of the three is bound to WHERE IN THE FILE
the line sits.  Reversing the three lines of `memory.jsonl` therefore reopened with
every check green and `live("memory")` reading back in the opposite order, which is
not cosmetic: retrieval order reaches `agent.py`'s `poisoned_seen`, which becomes
`derived_from`, which `core.Item.__post_init__` hashes into `item_id`, which
`detector.score` seeds on.  A reorder moved an item's score.  `_load_branch`'s own
docstring claimed the property ("write order is recovered exactly ... `live()`
order is ours, and the traces depend on it") and nothing defended it.  So each
sealed record carries a WRITE SEQUENCE NUMBER as well, and
`_refuse_an_order_that_moved` refuses a carrier whose lines no longer come back in
the order they were written.

`quarantined.jsonl` is sealed too, for the same reason and one more: quarantine
decisions come from a detector drawing N(d' * 1[poisoned], 1), so the list of
quarantined ids is a noisy copy of the label -- and while the mount was rw it was
also an un-quarantine switch.  What a real agent observes is absence from `live()`,
which is untouched.

WHY ALL OF THIS SURVIVES A READ-ONLY MOUNT.  `harness.mounts()` now hands the
carrier root over `ro` and the agent's only write path is a host-mediated tool call
(Task 14), so the agent has no route to any of the moves above.  The checks stay
regardless: they are the guard that does not depend on a mount flag being right,
and the mount flag is exactly the kind of one-character fact that gets changed in a
branch whose tests nobody ran.  They also catch what a mount flag never could -- a
half-written store left by a killed run, and a `.git` reordered through the
workspace mount, which IS still rw because repairing the repo is the task.
"""
from __future__ import annotations
import collections, hashlib, json, os, pathlib, shutil, subprocess, tempfile
from typing import Optional

import core
from core import CARRIERS, Item

#: Carriers kept as JSONL beside the repo.  `branch` is the complement, and the
#: complement is computed rather than written out twice, so adding a fifth
#: carrier to core.CARRIERS cannot leave this file silently half-updated.
#:
#: The OTHER half of that promise is `write`'s cross-carrier id guard.  Computing
#: the complement keeps the FILE LIST complete; it says nothing about ids, and
#: `item_id` is `carrier[:3]` plus a content hash while the sealed side
#: (`_seal_label`) is keyed on the id ALONE.  Two carriers sharing a three-character
#: prefix could therefore produce one id for two items, and `core.CarrierStore`'s
#: collision guard would not see it -- it looks inside ONE carrier.
BRANCH = "branch"
FLAT_CARRIERS = tuple(c for c in CARRIERS if c != BRANCH)

#: Namespace for the branch carrier's refs: `refs/heads/auditgame/<seq>-<id>`.
BRANCH_NS = "auditgame"

#: Name of the file recording which repo holds the branch carrier.  Without it,
#: re-opening a carrier root (harness.last_run_store() takes no repo argument)
#: would come back with three carriers and no error at all.
REPO_POINTER = "repo.path"

#: Fields of `core.item_record` that are GROUND TRUTH and may not reach the carrier
#: root.  A TUPLE rather than an inline `del`, so `public_record` and the sealing
#: side name the same thing and a second sealed field cannot be added to one half.
SEALED_FIELDS = ("poisoned",)

#: The sealed area: `<carrier root>-sealed`, a SIBLING of the carrier root.
#: DERIVED, never passed in.  A `sealed=` argument is a thing a call site can get
#: wrong once, in a branch whose tests nobody ran, and the consequence of getting
#: it wrong is silent: the labels land inside the mount and everything still works.
SEALED_SUFFIX = "-sealed"
LABELS = "ground_truth.jsonl"
MANIFEST_PREFIX = "manifest-"

#: The defender's own record of what it removed.  SEALED, not published -- see
#: `quarantine`.  It used to sit in the carrier root, where it was both a noisy
#: copy of the label (`detector.score` draws N(d' * 1[poisoned], 1), so at a usable
#: d' the quarantined id list approximates the poisoned set) and a writable
#: un-quarantine switch while that mount was still rw.
QUARANTINE = "quarantined.jsonl"

#: The field of a sealed record holding the digest of the PUBLIC line it belongs
#: to.  Without it a label is bound to an `item_id` and to nothing else, and
#: `item_id` is a string anyone holding the file can retype onto any line.
DIGEST_FIELD = "line_digest"

#: The field of a sealed record fixing WHERE the line sits among its carrier's
#: lines: a strictly increasing counter over every `write` this root has seen.
#: The digest binds a line to a label, the multiset binds the label set to a count
#: and `_rejoin` binds a line to a file -- the complement of those three is
#: position, and position is not cosmetic here: `live()` order reaches
#: `retrieve()`, then `derived_from`, then `item_id`, then the detector's seed.
#:
#: GLOBAL, not per carrier.  Per-carrier would need a second counter to survive a
#: line MOVED between files, and `_rejoin`'s carrier check already refuses that;
#: one counter over the whole root is the smaller thing to get right.  It is also
#: NOT the `seq` baked into a branch ref name (`_write_branch`), which is that
#: carrier's own index and exists to make `sorted()` recover write order -- see
#: `_load_branch`.
SEQ_FIELD = "write_seq"

#: Written into every sealed area at construction, and the thing the mount walk
#: actually looks for.  The walk used to ask "is a file NAMED like a sealed file
#: present", and `manifest-*.json` is an ordinary name in real repositories -- an
#: agent that writes `workspace/django/docs/manifest-frontend.json` made
#: `docker_argv` raise and every later container run in the benchmark die the same
#: way, i.e. it could halt the whole measurement with one `open()`.  The question
#: the mount turns on is "is a sealed AREA present", so this is a mark only the
#: sealing side produces, at a name no repository has a reason to carry.
SEALED_MARKER = ".auditgame-sealed-area"
SEALED_MARKER_TEXT = (
    "AuditGame-SE sealed area: per-item `poisoned` labels, the quarantine record\n"
    "and the sealed manifests. Mounted nowhere -- see carrier_store_fs.py.\n")

#: Directories the mount walk does not descend into.  The walk runs once per
#: `docker run` over `WORKSPACE`, which holds a full SWE-bench clone per instance,
#: and `.git` is most of the file count in each of them.  Nothing here can hold a
#: sealed area for ONE reason and not two: `sealed_root_for` only ever produces a
#: SIBLING of a carrier root, and nothing in this benchmark opens a store inside
#: any of these directories.  "It would not survive the reset" stood here too and
#: is FALSE for the first of them -- `git clean -xfd` KEEPS `.git`, which is the
#: whole of decision B-1 and the reason the `branch` carrier lives there, so a
#: store put in `.git` would survive better than one anywhere else.  A stated
#: reason wider than the check is the defect family this project keeps finding;
#: what actually holds is the narrow half.
WALK_SKIP = frozenset({".git", "__pycache__", ".hg", ".svn", ".tox", ".venv",
                       "node_modules"})


class GroundTruthMissing(RuntimeError):
    """A carrier item was read back with no sealed label.

    Its own class because the alternative is `poisoned=False`, and that is the one
    outcome this whole arrangement exists to prevent: every payload silently
    demoted to an ordinary note, harm undercounted, nothing printed.
    """


class CarrierTampered(GroundTruthMissing):
    """A public record no longer matches the line whose label was sealed.

    A SUBCLASS, because the consequence is the one GroundTruthMissing names: a
    record whose bytes changed has no label that belongs to it, and reading it
    under the label of the line it replaced is worse than reading it as clean --
    the payload's label would travel to content the agent wrote.  Every call site
    already written to refuse "no label" refuses this too, which is the point.
    """


class _GitFailed(RuntimeError):
    """`_git` ran a command and git answered with a non-zero status.

    Separate from the TIMEOUT that `_git` also raises, and that separation is the
    whole point: `_load_branch` turns a failed `cat-file` into `CarrierTampered`,
    and a wedged `.git/index.lock` must never be re-reported as tampering. A
    subclass of RuntimeError, so every caller that only ever wanted "git broke"
    keeps working unchanged.
    """


class GroundTruthExposed(RuntimeError):
    """A directory arrangement that would put ground truth where it can be read.

    Two sites raise it: `FSCarrierStore._refuse_nesting`, where a carrier root
    would seal its labels inside a mounted directory, and `harness.docker_argv`,
    where a mount would carry an answer key into the container.  Both were
    `AssertionError` -- the class `unittest` raises for every failed assertion, so
    a refusal that means THE ANSWER KEY IS ON THE ARGV read as a test defect, and
    it is the class most likely to be swallowed by a broad `except` in the Task 16
    run loop.  Swallowed, every task scores unsolved: a wrong number rather than a
    stopped run.  The store's tamper refusals have had a class of their own since
    Task 19; this is the other half of that.

    NOT a subclass of GroundTruthMissing.  That class names a label the evaluator
    cannot READ; this one names a label the AGENT can.  The consequences point in
    opposite directions and a handler written for one must not quietly catch the
    other.
    """


def sealed_root_for(root) -> pathlib.Path:
    """Where the ground truth for `root` lives.  Outside `root`, by construction."""
    root = pathlib.Path(root)
    return root.parent / (root.name + SEALED_SUFFIX)


#: The two sealed file names NO REPOSITORY CARRIES.  `ground_truth.jsonl` and
#: `quarantined.jsonl` are this project's own words; `manifest-*.json` is not, and
#: it was the whole of the false positive that made the walk refuse an ordinary
#: `docs/manifest-frontend.json`.  So the two halves are named apart: these two are
#: evidence on their own ONLY where the agent cannot write the directory being
#: asked about (`is_sealed_area(..., names_are_evidence=True)`, which only the
#: carrier-root mount passes -- it is `ro`), while the manifest glob is evidence
#: only inside a directory already named like a sealed area, for every caller.
SEALED_ONLY_NAMES = (LABELS, QUARANTINE)


#: Mode for a sealed area: OWNER ONLY.  `tempfile.mkdtemp` already gives `clone()`
#: its carrier root at 0700 while a plain `mkdir` left the sealed sibling at 0755 --
#: the public half private and the answer key world-readable, which is the wrong way
#: round.  Not reachable from the container either way (the sealed area is mounted
#: nowhere), so this is host hygiene on a shared machine, not part of the isolation
#: argument; it is here because 0755 on `ground_truth.jsonl`'s directory is the kind
#: of detail nobody looks at twice.
SEALED_MODE = 0o700


def mkdir_private(path) -> pathlib.Path:
    """`mkdir -p` at SEALED_MODE, and tighten one that is already there.

    BOTH halves are needed and each is useless alone: `mkdir(mode=...)` is masked
    by the process umask and does nothing at all when the directory already exists,
    which is every reopen of an existing store.
    """
    path = pathlib.Path(path)
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(SEALED_MODE)
    return path


# --------------------------------------------------------------------------
# NAMED SEAM -- `is_sealed_file`, `is_sealed_area`, `sealed_area_under`,
# SEALED_ONLY_NAMES and WALK_SKIP are a MOUNT PREDICATE.  They answer "may this
# host directory be handed to a container", which is `harness.docker_argv`'s
# question and nobody else's -- no method of `FSCarrierStore` calls any of them.
# They live here because the names they match (LABELS, QUARANTINE,
# MANIFEST_PREFIX, SEALED_SUFFIX) are this module's, and splitting them out would
# put a list of sealed file names in two modules, which is the drift the
# `is_sealed_file` docstring exists to prevent.
#
# The cost is that this file now carries five jobs -- persistence, sealing, tamper
# detection, a mount predicate and git plumbing -- in ~900 lines.  The clean split
# is `sealed_names.py` holding the NAMES, imported by both halves; it is not done
# in this pass because nothing in the round-3 or round-4 findings made it natural
# and a move with no behavioural reason is a diff a reviewer cannot check.  Do it
# the next time either half is opened for its own sake.
#
# STILL THE RIGHT SEAM after the round-4 fix.  `names_are_evidence` did not move
# the seam, it named which side of it a fact belongs to: the NAMES are this
# module's (they would travel to `sealed_names.py`), and "may a bare file name be
# taken as evidence here" is the CALLER's, because only the caller knows whether
# the directory it is asking about is one the agent can write.  That fact now
# travels as an argument instead of being assumed, which is what makes the split
# above still a pure move of names.
# --------------------------------------------------------------------------


def is_sealed_file(name: str) -> bool:
    """True for a file name that belongs in the sealed area and nowhere else.

    Named here rather than at the check site: a list of sealed file names kept in
    two modules is one rename away from a guard that watches for a file nobody
    writes any more.

    NOT a mount check on its own: `manifest-*.json` is an ordinary repository file
    name, so "a file named like this is present" is a question an agent can answer
    YES to at will.  `is_sealed_area` uses the two halves differently -- see
    SEALED_ONLY_NAMES.
    """
    return name in SEALED_ONLY_NAMES or (
        name.startswith(MANIFEST_PREFIX) and name.endswith(".json"))


def is_sealed_area(path, *, names_are_evidence: bool = False) -> bool:
    """True when `path` IS a sealed area, not when it merely holds a file named
    like one.

    Two ways in that hold for every caller, and both are shapes the SEALING side
    produces at a name no repository has a reason to carry:

      * it carries `SEALED_MARKER`, which `FSCarrierStore.__init__` writes into
        `self.sealed` -- the primary answer, and the only one for an area that is
        still empty (a store opened but not yet written to);
      * its NAME ends in SEALED_SUFFIX (which is how `sealed_root_for` names every
        one of them) AND it holds a sealed file -- which adds the manifest glob,
        for an area put there by hand without opening a store.

    `names_are_evidence` adds a THIRD: `ground_truth.jsonl` or `quarantined.jsonl`
    present at ANY directory name (SEALED_ONLY_NAMES).  OFF by default, because
    whether a bare file name is evidence depends on WHO CAN WRITE the directory
    being asked about, and that is the caller's fact, not this function's:

        those two names used to match for every caller, and `harness.docker_argv`
        walks the WORKSPACE mount, which is rw because repairing the repo is the
        task.  One `open("workspace/django/tests/ground_truth.jsonl", "w")`
        therefore made `docker_argv` raise for that task's mount AND for
        `mounts(None)`, so every later container run in the benchmark died the same
        way: the one-`open()` kill switch `manifest-*.json` had already handed over
        once, with a narrower trigger set and the same consequence.  No `-sealed`
        directory was needed for it.  And it is worse than a halt if a Task 16 run
        loop wraps its container runs in a broad `except`: every task then scores
        unsolved, which is a WRONG NUMBER rather than a stopped run.

    So the caller passes it True only for a directory the agent cannot write -- the
    carrier root, mounted `ro` since Task 14 -- and there it earns its keep: the
    labels copied into the carrier root by hand, under any directory name, are
    still refused, which is the Task 19 regression that match was restored for.

    THE RESIDUAL, as it actually stands.  An agent CAN still halt a run by building
    `x-sealed/ground_truth.jsonl` (or `x-sealed/manifest-anything.json`) under the
    WORKSPACE: the `-sealed` name is what makes it a sealed area to the second rule,
    and that rule has to keep firing, because an area really put under a mount is
    what the walk exists to catch.  That is a DoS reachable a dozen other ways and
    it costs a deliberate `-sealed` directory rather than one plausibly-named file.
    What is NOT true -- and was written here -- is that the carrier mount being `ro`
    closes it: the route is the WORKSPACE mount, which is rw by design.
    """
    p = pathlib.Path(path)
    if not p.is_dir():
        return False
    if (p / SEALED_MARKER).is_file():
        return True
    named_like_one = p.name.endswith(SEALED_SUFFIX)
    # Nothing left to look for in the common case, which is every ordinary
    # directory of every SWE-bench clone: the walk skips the iterdir entirely.
    if not (named_like_one or names_are_evidence):
        return False
    try:
        for e in p.iterdir():
            if not e.is_file():
                continue
            if names_are_evidence and e.name in SEALED_ONLY_NAMES:
                return True
            if named_like_one and is_sealed_file(e.name):
                return True
    except OSError:
        return False
    return False


def sealed_area_under(path, *, names_are_evidence: bool = False) -> Optional[pathlib.Path]:
    """The first sealed area at `path` or anywhere beneath it, or None.

    `names_are_evidence` is handed straight to `is_sealed_area` and means what it
    means there: the caller, not this walk, knows whether the tree being walked is
    one the agent can write into.  See that docstring for why the default is False.

    A WALK, at any depth -- not a check on where a particular store put its sealed
    area.  The sibling rule (`sealed_root_for`) is what keeps the labels out of a
    mount, and the one way left to defeat it is to open a store UNDER a directory
    that is already mounted: a per-workflow sub-root `<mounted root>/run1` seals to
    `<mounted root>/run1-sealed`, inside the mount, and
    `FSCarrierStore._refuse_nesting` accepts it because at construction time the
    ancestor holds nothing yet.  What the agent can see is decided when the mount
    is built, so that is where this is asked.

    DIRECTORIES, not file names.  The previous version asked every file name under
    the mount whether it looked sealed, which was both wider than the claim (an
    agent-written `docs/manifest-frontend.json` halted the benchmark) and dearer
    than it needs to be (every loose object of every SWE-bench clone, once per
    `docker run`).  Asking directories lets the walk prune -- see WALK_SKIP.
    """
    p = pathlib.Path(path)
    if not p.is_dir():
        return None
    # The mount ITSELF: os.walk reports a directory's children, never the top.
    if is_sealed_area(p, names_are_evidence=names_are_evidence):
        return p
    for dirpath, dirnames, _filenames in os.walk(p, followlinks=False):
        dirnames[:] = [d for d in sorted(dirnames) if d not in WALK_SKIP]
        for d in dirnames:
            cand = pathlib.Path(dirpath) / d
            if is_sealed_area(cand, names_are_evidence=names_are_evidence):
                return cand
    return None


def public_record(it: Item) -> dict:
    """`core.item_record` minus the ground truth -- the ONLY item shape written
    into the carrier root, JSONL and git blob alike.

    Subtractive rather than an allow-list: a new field of `core.item_record` is
    then carried to disk automatically (the round trip stays complete), while the
    one class of field that must not travel is named in SEALED_FIELDS.  `pop`
    without a default is deliberate -- if `poisoned` is ever renamed, this raises
    instead of quietly passing the renamed field straight through.
    """
    rec = core.item_record(it)
    for f in SEALED_FIELDS:
        rec.pop(f)
    return rec


#: Seconds any one git call may take.  A git command with no timeout does not
#: fail, it WAITS: a stale `.git/index.lock` -- which is what a killed container or
#: an interrupted run leaves behind -- makes every branch write block forever, and
#: gate 1 then produces neither a green line nor a red one.  The same failure mode
#: `harness.DOCKER_RUN_TIMEOUT` was added for, one subprocess down.
GIT_TIMEOUT = 120

#: Fixed identity, fixed dates, no user config.  A commit sha is then a pure
#: function of its content: the branch carrier contains no wall-clock reading,
#: for the same reason core.seed_of exists instead of hash().
GIT_ENV = {
    "GIT_AUTHOR_NAME": "auditgame", "GIT_AUTHOR_EMAIL": "auditgame@invalid",
    "GIT_COMMITTER_NAME": "auditgame", "GIT_COMMITTER_EMAIL": "auditgame@invalid",
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def _jsonable(o):
    """The encoder rule of `core.dumps`, for ONE LINE.

    core.dumps hardcodes indent=2, which JSONL cannot use, so the rule is
    restated rather than reused -- and `test_a_token_set_topic_round_trips_the_way
    _core_dumps_writes_it` pins the two to the same answer.  A set becomes a
    SORTED list: frozenset iteration order depends on PYTHONHASHSEED, so a raw
    one would serialise the same carrier to a different byte string per process.
    A tuple keeps its order, because `derived_from` is a propagation trail.
    """
    if isinstance(o, (frozenset, set)):
        return sorted(o)
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))


def _line(rec: dict) -> str:
    return json.dumps(rec, default=_jsonable, sort_keys=True, ensure_ascii=False)


def line_digest(line: str) -> str:
    """The digest sealed beside a label, over the EXACT public line.

    blake2b for the same reason `core` uses it: a fixed function of the bytes, no
    process state, no PYTHONHASHSEED.  Over the serialised line rather than over
    the parsed record, because the thing being bound is what is on the disk -- a
    re-serialisation would silently forgive a rewrite that JSON happens to
    normalise away.
    """
    return hashlib.blake2b(line.encode("utf-8"), digest_size=16).hexdigest()


def _parse_line(text: str, where) -> dict:
    """`json.loads`, with this module's OWN refusal class on bytes that do not parse.

    Every docstring here promises one family -- `GroundTruthMissing` and its
    subclass `CarrierTampered` -- and `json.loads` promised something else:
    `json.JSONDecodeError`, a `ValueError`, reaching a caller written against that
    family as an unrelated class with a message about a column number.  The case is
    not hypothetical and the module docstring already names it: a HALF-WRITTEN line
    left by a killed run, plus the hand-edited store the tamper checks exist for.

    CarrierTampered is the right member of the family rather than a third class.
    The digest is taken over the exact public line; bytes that no longer parse are
    not the bytes whose label was sealed, so there is no record here that may be
    read under that label -- which is what tampering MEANS in this module.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise CarrierTampered(
            f"a line in {where} is not JSON any more ({e}). A store half-written by "
            f"a killed run and one edited by hand are the same defect here: these "
            f"bytes are not the bytes whose label was sealed, so nothing in them "
            f"can be read back under it.") from e


class FSCarrierStore(core.CarrierStore):
    """`core.CarrierStore` with the same six methods, persisted.

    It SUBCLASSES the in-memory store on purpose: `live`, `retrieve` and
    `snapshot` are inherited unchanged, so swapping the store cannot change a
    measured number by re-implementing retrieval slightly differently.  Only the
    three methods that MUTATE state -- `write`, `quarantine`, `clone` -- are
    overridden, and `write` still calls `super().write` first so the item_id
    collision guard runs before anything touches the disk.
    """

    def __init__(self, root: pathlib.Path, repo: Optional[pathlib.Path] = None):
        self.root = pathlib.Path(root)
        self.sealed = sealed_root_for(self.root)
        self._refuse_nesting()
        self.root.mkdir(parents=True, exist_ok=True)
        mkdir_private(self.sealed)
        # The mark the mount walk looks for, written before anything is sealed:
        # an area with a store open on it but nothing written yet is still an area
        # the next `write` will put labels into, and the walk has to refuse the
        # mount NOW rather than after the first payload is planted.
        marker = self.sealed / SEALED_MARKER
        if not marker.exists():
            marker.write_text(SEALED_MARKER_TEXT, encoding="utf-8")
        self.repo = self._attach(repo)
        self.items = {c: [] for c in CARRIERS}
        self.quarantined = set()
        self.labels: dict = {}
        self.digests: dict = {}
        self.seqs: dict = {}
        # The next write's sequence number, recovered from the sealed side at the
        # end of `_load`.  An int rather than itertools.count: this module may hold
        # no process-local counter whose value a re-open cannot reproduce.
        self._next_seq = 0
        self._load()

    def _refuse_nesting(self) -> None:
        """Refuse a carrier root that sits inside another store's area.

        The sibling rule is derived, so the one way left to defeat it is nesting:
        a store at `<mounted carrier root>/inner` puts its labels at
        `<mounted carrier root>/inner-sealed`, INSIDE the mount, and the leak is
        back with one more directory in the path.  Walking the ancestors costs a
        handful of stat calls once per open, and the alternative is a paragraph in
        a docstring that the call site introducing the bug will not be reading.
        """
        here = self.root.resolve()
        for anc in here.parents:
            if (anc / LABELS).exists() or (anc / SEALED_MARKER).exists():
                raise GroundTruthExposed(
                    f"carrier root {here} is inside the SEALED area {anc}: its own "
                    f"labels would sit next to another store's ground truth.")
            if (anc / REPO_POINTER).exists() or any(
                    (anc / f"{c}.jsonl").exists() for c in FLAT_CARRIERS):
                raise GroundTruthExposed(
                    f"carrier root {here} is nested inside the carrier root {anc}: "
                    f"its sealed area {sealed_root_for(here)} would land inside a "
                    f"directory the container is mounted on.")

    # ------------------------------------------------------------- attachment

    @property
    def attached(self) -> bool:
        """True when a repo holds the branch carrier.  A DETACHED store (what
        `clone()` returns) can READ a materialised branch carrier but may not
        write one -- see `write`."""
        return self.repo is not None

    def _attach(self, repo) -> Optional[pathlib.Path]:
        ptr = self.root / REPO_POINTER
        if repo is not None:
            repo = pathlib.Path(repo).resolve()
            ptr.write_text(str(repo) + "\n", encoding="utf-8")
            return repo
        if ptr.exists():
            remembered = pathlib.Path(ptr.read_text(encoding="utf-8").strip())
            if not (remembered / ".git").exists():
                # LOUD, not silent.  Coming back with three of four carriers is
                # the "green by luck" failure this whole module is written
                # against: a scan for a leaked path would simply never look at
                # `branch` and would report nothing found.
                raise FileNotFoundError(
                    f"carrier root {self.root} records its branch carrier in "
                    f"{remembered}, which is not a git repo any more. Three of "
                    f"four carriers would load, silently.")
            return remembered
        return None

    # ------------------------------------------------------------------ read

    def _load(self) -> None:
        self._load_labels()
        for c in FLAT_CARRIERS:
            self._load_flat(c)
        if self.attached:
            self._load_branch()
        else:
            # A detached copy carries its branch carrier as JSONL like the rest;
            # it is a snapshot for analysis, not a second repo.
            self._load_flat(BRANCH)
        self._refuse_a_record_count_that_moved()
        # LAST of the four, and deliberately so.  It is the only one that needs
        # every other to have held: it reads `self.seqs` for items it has already
        # rejoined, in the order the files gave them back.  Running it here means a
        # deleted, duplicated, moved or rewritten record still raises with the
        # message about ITS defect rather than being re-described as an ordering
        # one -- the four compose instead of shadowing each other.
        self._refuse_an_order_that_moved()
        self._next_seq = max(self.seqs.values(), default=-1) + 1
        qpath = self.sealed / QUARANTINE
        if qpath.exists():
            for line in qpath.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.quarantined.add(_parse_line(line, qpath)["item_id"])

    def _load_labels(self) -> None:
        """The sealed side, read before any carrier is."""
        path = self.sealed / LABELS
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = _parse_line(line, path)
                for field in (DIGEST_FIELD, SEQ_FIELD):
                    if field not in rec:
                        # A label with no digest binds to an item_id and to nothing
                        # else, and a label with no sequence number binds to no
                        # POSITION -- each is the state its field exists to end.
                        # Refused rather than defaulted: a default would re-open
                        # exactly the hole for every store written before the
                        # field existed, which is the quietest way to keep a bug.
                        raise CarrierTampered(
                            f"a sealed label in {path} carries no {field!r}: it "
                            f"cannot be bound to the public record it belongs to.")
                self.labels[rec["item_id"]] = rec[SEALED_FIELDS[0]]
                self.digests[rec["item_id"]] = rec[DIGEST_FIELD]
                self.seqs[rec["item_id"]] = rec[SEQ_FIELD]

    def _refuse_a_record_count_that_moved(self) -> None:
        """One sealed label, one public record.  COUNTED, and compared for equality.

        The half of the tampering story `_rejoin` cannot see.  `_rejoin` is only
        ever called on lines that are THERE, and it is called once per line, so it
        sees neither of the two moves that leave every byte -- and therefore every
        digest -- intact:

          * a line DELETED (or `memory.jsonl` truncated to nothing) removes the
            payload from every count with no error at all, which is the quietest
            way to defeat the harm measurement from inside the mount;
          * a line COPIED -- a second time into its own file, or verbatim into
            another carrier's -- puts the SAME item_id into `live()` twice. Harm is
            built on these counts: `Q_true`/`Q_false` double-count the payload, and
            `core.CarrierStore.write` refuses exactly this state at the write
            ("quarantining one item would ERASE THE OTHER") while the load path,
            until now, did not.

        A SET could only ever see the first.  The multiset is what makes the two
        one check, and equality -- rather than a subset test in either direction --
        is what keeps it from going quiet when a new way of duplicating a record
        turns up.  Checked against the sealed side because that is the side the
        agent cannot reach.

        It also means a crash between `_seal_label` and the publish that follows it
        is now DETECTED rather than harmless.  That is the right way round: a store
        that refuses to open is a stopped run, while a store that opens one item
        short is a run whose harm figure is wrong and says nothing.
        """
        seen = collections.Counter(it.item_id for c in CARRIERS
                                   for it in self.items[c])
        sealed = collections.Counter(self.labels.keys())
        if seen == sealed:
            return
        lost = sorted((sealed - seen).elements())
        extra = sorted((seen - sealed).elements())
        first_lost = repr(lost[0]) if lost else "-"
        first_extra = repr(extra[0]) if extra else "-"
        raise CarrierTampered(
            f"the carrier root {self.root} holds {sum(seen.values())} record(s) "
            f"for {sum(sealed.values())} sealed label(s) in "
            f"{self.sealed / LABELS}: {len(lost)} label(s) with no record "
            f"(first: {first_lost}) and {len(extra)} record(s) "
            f"beyond their label (first: {first_extra}). A "
            f"deleted item disappears from Q_true/Q_false and from harm without "
            f"anything being printed; a copied one is counted twice, in two "
            f"carriers at once if it was copied across.")

    def _refuse_an_order_that_moved(self) -> None:
        """One carrier, one write order.  COMPARED, not assumed.

        The move none of the other three can see.  A digest binds a line to a
        label, the multiset binds the label set to a count, `_rejoin` binds a line
        to the file it came out of -- and the complement of all three is WHERE IN
        THE FILE the line sits.  Reversing the three lines of `memory.jsonl` changes
        no byte of any line, no id, no count and no carrier, so it reopened with
        every check green.

        Why that is not cosmetic.  `live()` hands its list to `retrieve()`
        (core.py), `agent.py` turns what it retrieved into `derived_from`, and
        `core.Item.__post_init__` hashes `derived_from` into `item_id` -- a TUPLE,
        because a propagation trail has an order, so the two orderings of one pair
        give two different ids.  That is asserted rather than asserted-about, in
        `test_a_carrier_file_whose_lines_were_reordered_is_refused_instead_of_
        reopening_clean`, which builds both and refuses to proceed if they agree.
        `detector.score` seeds on `item_id`, so a reorder moves an item's score,
        and `agent.py` indexes its retrieval list positionally besides.
        `_load_branch`'s docstring already claims this property -- "write order is
        recovered exactly ... `live()` order is ours, and the traces depend on it"
        -- and until now nothing defended it.

        STRICTLY increasing, per carrier, over the sealed counter.  Equal is
        impossible (one counter, one write) and would mean two labels claiming one
        position, so `<=` is the refusal rather than `<`.  Both the flat carriers
        and `branch` are checked: the branch order comes from ref NAMES, which live
        in the repo's `.git` under a mount that is rw because repairing the repo is
        the task -- it is the one carrier whose order a container can still reach.
        """
        for c in CARRIERS:
            items = self.items[c]
            for i in range(1, len(items)):
                prev, cur = items[i - 1], items[i]
                if self.seqs[cur.item_id] <= self.seqs[prev.item_id]:
                    raise CarrierTampered(
                        f"carrier {c!r} under {self.root} comes back in an order "
                        f"that is not the order it was written: position {i - 1} "
                        f"holds {prev.item_id!r} (written {self.seqs[prev.item_id]}) "
                        f"and position {i} holds {cur.item_id!r} (written "
                        f"{self.seqs[cur.item_id]}). Retrieval order reaches "
                        f"`derived_from`, which is hashed into `item_id`, which the "
                        f"detector seeds on -- so a reordered carrier moves scores "
                        f"while every digest, count and carrier check stays green.")

    def _rejoin(self, rec: dict, line: str, carrier: str) -> Item:
        """A public record from the carrier root + its sealed label -> the Item.

        The two halves are rejoined HERE and nowhere else, so there is one place
        that can answer "what happens when a label is missing" -- and it answers
        LOUDLY.  `poisoned=False` would be the silent answer, and the silent answer
        is the bug: a fabricated line read back as clean is a payload the scoring
        path will never count.  The container can no longer append to
        `memory.jsonl` (`harness.CARRIER_MODE` is `ro` -- Task 14), which removes
        the agent's route to it and not the requirement: a killed run, a clone and
        anything on the host can still hand this method a line with no label.

        `item_id` is trusted verbatim and has to be -- rehashing would move every
        id and every score (see the module docstring) -- so the id ALONE cannot be
        what binds a record to its label: a known id can be retyped onto a written
        line, or the content rewritten under an id that is kept, and in both
        cases the payload's label travels to content the attacker did not write.
        The sealed side therefore carries `line_digest` of the exact public line,
        and the LINE is what is checked.

        `carrier` is WHERE THE LINE WAS FOUND -- the file it came out of, or the
        `branch` ref namespace -- and the record has to agree with it.  The digest
        binds a line to a label and says nothing about which file the line is in,
        so moving a sealed line from `memory.jsonl` into `queue.jsonl` left every
        check green while the payload was accounted to a carrier it was never
        written to: `self.items` is keyed on the FILENAME, so per-carrier
        accounting (kappa, n_c at sigma) would charge the wrong carrier for it.
        """
        item_id = rec["item_id"]
        if rec.get("carrier") != carrier:
            raise CarrierTampered(
                f"a record in carrier {carrier!r} under {self.root} says it "
                f"belongs to carrier {rec.get('carrier')!r} (item "
                f"{item_id!r}). A line moved between carrier files keeps its "
                f"digest and its label, and lands in the per-carrier accounting "
                f"of a carrier it was never written to.")
        try:
            label = self.labels[item_id]
        except KeyError:
            raise GroundTruthMissing(
                f"item {item_id!r} is in {self.root} but has no sealed label in "
                f"{self.sealed / LABELS}. Reading it as clean would silently "
                f"demote a payload to an ordinary note.") from None
        want, got = self.digests[item_id], line_digest(line)
        if want != got:
            raise CarrierTampered(
                f"item {item_id!r} in {self.root} does not match the line whose "
                f"label was sealed ({got} != {want}). Loading it anyway would "
                f"attach the payload's ground truth to a record that is no longer "
                f"the payload.")
        return core.item_from_record({**rec, SEALED_FIELDS[0]: label})

    def _load_flat(self, carrier: str) -> None:
        path = self.root / f"{carrier}.jsonl"
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                self.items[carrier].append(
                    self._rejoin(_parse_line(line, path), line, carrier))

    def _load_branch(self) -> None:
        out = self._git("for-each-ref", "--format=%(refname:short)",
                        f"refs/heads/{BRANCH_NS}")
        # Sorted by the zero-padded sequence number baked into the ref name, so
        # write order is recovered exactly.  Ref listing order is git's business;
        # `live()` order is ours, and the traces depend on it.
        for ref in sorted(out.split()):
            # `_write_branch` stores `_line(...) + "\n"`, so the blob stripped of
            # that newline is the same string the digest was taken over.
            #
            # A ref in this namespace carrying no `item.json` is a ref THIS STORE
            # DID NOT WRITE: `git branch auditgame/999999-anything HEAD`, which is
            # inside the agent's reach because the branch carrier lives in the
            # repo's own `.git` (decision B-1) under a mount that is rw. That came
            # back as a bare RuntimeError naming a git command -- outside the family
            # every docstring here promises -- for the one carrier a container can
            # still perturb. It is tampering by this module's definition: a line in
            # the branch carrier that no sealed label can belong to. A git TIMEOUT
            # is deliberately NOT caught here (see `_GitFailed`): a wedged repo is a
            # red gate, not an attack.
            try:
                line = self._git("cat-file", "-p", f"{ref}:item.json").strip()
            except _GitFailed as e:
                raise CarrierTampered(
                    f"the ref {ref!r} in {self.repo} sits in the branch carrier's "
                    f"namespace refs/heads/{BRANCH_NS}/ but carries no `item.json`, "
                    f"so this store did not write it. A ref added there is counted "
                    f"as a carrier item by `live()` order and by nothing else -- "
                    f"there is no sealed label it could be read under.") from e
            self.items[BRANCH].append(
                self._rejoin(_parse_line(line, f"{self.repo} ref {ref}"),
                             line, BRANCH))

    # ----------------------------------------------------------------- write

    def write(self, it: Item) -> Item:
        if it.carrier == BRANCH and not self.attached:
            raise AssertionError(
                "the `branch` carrier lives in the repo's .git (decision B-1) and "
                "this store has no repo attached. Writing it to a JSONL file "
                "instead would produce a branch carrier that outlives a repo "
                "reset for a reason that has nothing to do with git.")
        # ACROSS carriers, which `super().write` cannot see: its guard looks inside
        # `self.items[it.carrier]`, while `_seal_label` writes into GLOBAL label,
        # digest and sequence dicts keyed on `item_id`. Two carriers cannot collide
        # TODAY only because `carrier[:3]` differs for all four of core.CARRIERS --
        # a coincidence of four spellings, not a guard. A fifth carrier sharing a
        # three-character prefix would silently overwrite the first item's label,
        # digest and write sequence, and the count check would then report the
        # SECOND item as the one with no label. Raised with the same class as the
        # per-carrier guard, because it is the same defect one carrier wider and a
        # caller should need one handler for it.
        #
        # The same-carrier case is deliberately left to `super().write`, whose
        # message names it exactly ("two items agree on every field").
        if it.item_id in self.labels and not any(
                x.item_id == it.item_id for x in self.items[it.carrier]):
            raise AssertionError(
                f"item_id {it.item_id!r} is already sealed under {self.root} by "
                f"another carrier, and the sealed side is keyed on the id alone: "
                f"this write would OVERWRITE the first item's label, digest and "
                f"write sequence. Ids carry `carrier[:3]`, so this can only happen "
                f"once a carrier sharing a three-character prefix is added to "
                f"core.CARRIERS -- which is exactly when it must not pass quietly.")
        super().write(it)                      # collision guard, then append
        # SEAL FIRST, publish second.  A crash between the two then leaves a label
        # with no item, which `_refuse_a_record_count_that_moved` reports at the
        # next open;
        # the other order leaves an item with no label, which is the
        # GroundTruthMissing case.  Both are refusals, and that is the point --
        # what may never happen is a half-written store that opens quietly.
        line = _line(public_record(it))
        self._seal_label(it, line)
        if it.carrier == BRANCH:
            self._write_branch(it, line, seq=len(self.items[BRANCH]) - 1)
        else:
            with (self.root / f"{it.carrier}.jsonl").open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        return it

    def _seal_label(self, it: Item, line: str) -> None:
        """The ground truth, to the sealed sibling and nowhere else.

        The label, a digest of the public line it belongs to, AND the position that
        line holds in the write order.  The digest is what makes the label the
        evaluator's record of a specific record rather than a note attached to a
        string anyone holding the file can retype; the sequence number is what
        makes it a record of a specific POSITION -- see
        `_refuse_an_order_that_moved` for why order is a measured quantity here.
        """
        self.labels[it.item_id] = getattr(it, SEALED_FIELDS[0])
        self.digests[it.item_id] = line_digest(line)
        self.seqs[it.item_id] = self._next_seq
        self._next_seq += 1
        with (self.sealed / LABELS).open("a", encoding="utf-8") as f:
            f.write(_line({"item_id": it.item_id,
                           SEALED_FIELDS[0]: self.labels[it.item_id],
                           DIGEST_FIELD: self.digests[it.item_id],
                           SEQ_FIELD: self.seqs[it.item_id]}) + "\n")

    def _write_branch(self, it: Item, line: str, seq: int) -> None:
        """One item -> one git branch, via plumbing.

        blob -> tree -> root commit -> `git branch auditgame/<seq>-<item_id>`.
        A real branch rather than a file in `.git/`: `git clean -xfd` cannot see
        it and `git checkout` does not touch it, which is the B-1 property stated
        in the one way a reader can check by running git themselves.
        """
        payload = line + "\n"
        blob = self._git("hash-object", "-w", "--stdin", stdin=payload).strip()
        tree = self._git("mktree", stdin=f"100644 blob {blob}\titem.json\n").strip()
        commit = self._git("commit-tree", tree, "-m",
                           f"auditgame {it.carrier} {it.item_id}").strip()
        self._git("branch", f"{BRANCH_NS}/{seq:06d}-{it.item_id}", commit)

    def quarantine(self, item_id: str) -> None:
        """Remove an item from `live()`, and record that in the SEALED area.

        Not in the carrier root, for two reasons that point the same way.  It is a
        LABEL PROXY: quarantine decisions come out of `detector.score`, which draws
        N(d' * 1[poisoned], 1), so at any d' worth running the list of quarantined
        ids approximates the poisoned set -- an explicit id list, in the mount,
        covering items the agent never retrieved.  And it is a SWITCH: the mount is
        rw, so emptying the file un-quarantines everything at the next reopen, and
        quarantine is the defender's only causal channel.

        What a real agent observes is unchanged, because what a real agent observes
        is that its note is not in `live()` any more -- absence, not an announcement.
        """
        if item_id in self.quarantined:
            return                             # `set.add` is idempotent; a file append is not
        super().quarantine(item_id)
        with (self.sealed / QUARANTINE).open("a", encoding="utf-8") as f:
            f.write(_line({"item_id": item_id}) + "\n")

    # ----------------------------------------------------------------- copy

    def clone(self, dest: Optional[pathlib.Path] = None) -> "FSCarrierStore":
        """An independent DETACHED copy of the state.

        `core.CarrierStore.clone` deep-copies a dict; the filesystem equivalent is
        a second directory.  The copy keeps no repo: the branch carrier is
        MATERIALISED into `branch.jsonl` so it can still be read, and a branch
        WRITE on the copy is refused (see `write`).  A clone is for scoring a
        counterfactual, not for running a second agent.
        """
        dest = pathlib.Path(dest) if dest is not None else pathlib.Path(
            tempfile.mkdtemp(prefix="auditgame-carriers-"))
        dest.mkdir(parents=True, exist_ok=True)
        for c in FLAT_CARRIERS:
            src = self.root / f"{c}.jsonl"
            if src.exists():
                shutil.copyfile(src, dest / f"{c}.jsonl")
        # The quarantine record is NOT copied here: it lives in the sealed area
        # now, and the sealed area travels below.  One copy site, so it cannot land
        # in the public half of the copy by accident.
        if self.items[BRANCH]:
            (dest / f"{BRANCH}.jsonl").write_text(
                "".join(_line(public_record(it)) + "\n" for it in self.items[BRANCH]),
                encoding="utf-8")
        # The SEALED side travels with the copy.  A clone is for scoring a
        # counterfactual and scoring reads `poisoned`, so a copy without the labels
        # would either score an all-clean world or -- since Task 19 -- refuse to
        # open at all.  It lands in the copy's OWN sealed sibling, still outside
        # the copy's carrier root.
        sealed_dest = mkdir_private(sealed_root_for(dest))
        for f in sorted(self.sealed.glob("*")):
            if f.is_file():
                shutil.copyfile(f, sealed_dest / f.name)
        # No REPO_POINTER in the copy: that is what makes it detached.
        return FSCarrierStore(dest)

    # ------------------------------------------------------------- manifest

    def seal_manifest(self, manifest: dict) -> pathlib.Path:
        """Write one `build.sealed_manifest` record into the sealed area.

        WRITE ONCE.  A manifest that can be overwritten after the run records what
        the evaluator concluded afterwards rather than what was planted, and every
        "the manifest says so" argument in the thesis rests on the opposite.
        """
        path = self.sealed / f"{MANIFEST_PREFIX}{manifest['wf_id']}.json"
        if path.exists():
            raise AssertionError(
                f"{path} is already sealed. A sealed manifest is written before the "
                f"run and never again -- rewriting it would make it a record of the "
                f"outcome rather than of the plan.")
        path.write_text(core.dumps(manifest), encoding="utf-8")
        return path

    def read_manifests(self) -> list:
        """The sealed manifests for this root, in workflow-id order.  The evaluator
        reads these; nothing inside the container can."""
        return [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(self.sealed.glob(f"{MANIFEST_PREFIX}*.json"))]

    # ------------------------------------------------------------------ git

    def _git(self, *args: str, stdin: Optional[str] = None) -> str:
        try:
            r = subprocess.run(["git", "-C", str(self.repo), *args], input=stdin,
                               capture_output=True, text=True,
                               timeout=GIT_TIMEOUT,
                               env={**os.environ, **GIT_ENV})
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"git {' '.join(args)} in {self.repo} did not finish within "
                f"{GIT_TIMEOUT}s and was killed. Treat this as a RED gate, not as "
                f"a slow machine: a stale .git/index.lock makes every branch write "
                f"wait forever, and a gate that hangs produces neither a green line "
                f"nor a red one.") from e
        if r.returncode != 0:
            raise _GitFailed(
                f"git {' '.join(args)} in {self.repo} failed ({r.returncode}): "
                f"{r.stderr.strip()[:400]}")
        return r.stdout
