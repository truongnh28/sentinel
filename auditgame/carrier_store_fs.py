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
policies must not read it, and `harness.mounts()` hands this whole root to the
container READ-WRITE.  Nothing read it there while the agent was a mock, so no
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
"""
from __future__ import annotations
import json, os, pathlib, shutil, subprocess, tempfile
from typing import Optional

import core
from core import CARRIERS, Item

#: Carriers kept as JSONL beside the repo.  `branch` is the complement, and the
#: complement is computed rather than written out twice, so adding a fifth
#: carrier to core.CARRIERS cannot leave this file silently half-updated.
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


class GroundTruthMissing(RuntimeError):
    """A carrier item was read back with no sealed label.

    Its own class because the alternative is `poisoned=False`, and that is the one
    outcome this whole arrangement exists to prevent: every payload silently
    demoted to an ordinary note, harm undercounted, nothing printed.
    """


def sealed_root_for(root) -> pathlib.Path:
    """Where the ground truth for `root` lives.  Outside `root`, by construction."""
    root = pathlib.Path(root)
    return root.parent / (root.name + SEALED_SUFFIX)


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
        self.sealed.mkdir(parents=True, exist_ok=True)
        self.repo = self._attach(repo)
        self.items = {c: [] for c in CARRIERS}
        self.quarantined = set()
        self.labels: dict = {}
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
            if (anc / LABELS).exists():
                raise AssertionError(
                    f"carrier root {here} is inside the SEALED area {anc}: its own "
                    f"labels would sit next to another store's ground truth.")
            if (anc / REPO_POINTER).exists() or any(
                    (anc / f"{c}.jsonl").exists() for c in FLAT_CARRIERS):
                raise AssertionError(
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
        qpath = self.root / "quarantined.jsonl"
        if qpath.exists():
            for line in qpath.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.quarantined.add(json.loads(line)["item_id"])

    def _load_labels(self) -> None:
        """The sealed side, read before any carrier is."""
        path = self.sealed / LABELS
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                self.labels[rec["item_id"]] = rec[SEALED_FIELDS[0]]

    def _rejoin(self, rec: dict) -> Item:
        """A public record from the carrier root + its sealed label -> the Item.

        The two halves are rejoined HERE and nowhere else, so there is one place
        that can answer "what happens when a label is missing" -- and it answers
        LOUDLY.  `poisoned=False` would be the silent answer, and the silent answer
        is the bug: an agent can append to `memory.jsonl` from inside the container
        (the mount is rw), and a fabricated line read back as clean is a payload
        the scoring path will never count.
        """
        item_id = rec["item_id"]
        try:
            label = self.labels[item_id]
        except KeyError:
            raise GroundTruthMissing(
                f"item {item_id!r} is in {self.root} but has no sealed label in "
                f"{self.sealed / LABELS}. Reading it as clean would silently "
                f"demote a payload to an ordinary note.") from None
        return core.item_from_record({**rec, SEALED_FIELDS[0]: label})

    def _load_flat(self, carrier: str) -> None:
        path = self.root / f"{carrier}.jsonl"
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                self.items[carrier].append(self._rejoin(json.loads(line)))

    def _load_branch(self) -> None:
        out = self._git("for-each-ref", "--format=%(refname:short)",
                        f"refs/heads/{BRANCH_NS}")
        # Sorted by the zero-padded sequence number baked into the ref name, so
        # write order is recovered exactly.  Ref listing order is git's business;
        # `live()` order is ours, and the traces depend on it.
        for ref in sorted(out.split()):
            rec = json.loads(self._git("cat-file", "-p", f"{ref}:item.json"))
            self.items[BRANCH].append(self._rejoin(rec))

    # ----------------------------------------------------------------- write

    def write(self, it: Item) -> Item:
        if it.carrier == BRANCH and not self.attached:
            raise AssertionError(
                "the `branch` carrier lives in the repo's .git (decision B-1) and "
                "this store has no repo attached. Writing it to a JSONL file "
                "instead would produce a branch carrier that outlives a repo "
                "reset for a reason that has nothing to do with git.")
        super().write(it)                      # collision guard, then append
        # SEAL FIRST, publish second.  A crash between the two then leaves a label
        # with no item, which is harmless; the other order leaves an item with no
        # label, which is the GroundTruthMissing case -- recoverable, but it stops
        # the next run dead.
        self._seal_label(it)
        if it.carrier == BRANCH:
            self._write_branch(it, seq=len(self.items[BRANCH]) - 1)
        else:
            with (self.root / f"{it.carrier}.jsonl").open("a", encoding="utf-8") as f:
                f.write(_line(public_record(it)) + "\n")
        return it

    def _seal_label(self, it: Item) -> None:
        """The ground truth, to the sealed sibling and nowhere else."""
        self.labels[it.item_id] = getattr(it, SEALED_FIELDS[0])
        with (self.sealed / LABELS).open("a", encoding="utf-8") as f:
            f.write(_line({"item_id": it.item_id,
                           SEALED_FIELDS[0]: self.labels[it.item_id]}) + "\n")

    def _write_branch(self, it: Item, seq: int) -> None:
        """One item -> one git branch, via plumbing.

        blob -> tree -> root commit -> `git branch auditgame/<seq>-<item_id>`.
        A real branch rather than a file in `.git/`: `git clean -xfd` cannot see
        it and `git checkout` does not touch it, which is the B-1 property stated
        in the one way a reader can check by running git themselves.
        """
        payload = _line(public_record(it)) + "\n"
        blob = self._git("hash-object", "-w", "--stdin", stdin=payload).strip()
        tree = self._git("mktree", stdin=f"100644 blob {blob}\titem.json\n").strip()
        commit = self._git("commit-tree", tree, "-m",
                           f"auditgame {it.carrier} {it.item_id}").strip()
        self._git("branch", f"{BRANCH_NS}/{seq:06d}-{it.item_id}", commit)

    def quarantine(self, item_id: str) -> None:
        if item_id in self.quarantined:
            return                             # `set.add` is idempotent; a file append is not
        super().quarantine(item_id)
        with (self.root / "quarantined.jsonl").open("a", encoding="utf-8") as f:
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
        q = self.root / "quarantined.jsonl"
        if q.exists():
            shutil.copyfile(q, dest / "quarantined.jsonl")
        if self.items[BRANCH]:
            (dest / f"{BRANCH}.jsonl").write_text(
                "".join(_line(public_record(it)) + "\n" for it in self.items[BRANCH]),
                encoding="utf-8")
        # The SEALED side travels with the copy.  A clone is for scoring a
        # counterfactual and scoring reads `poisoned`, so a copy without the labels
        # would either score an all-clean world or -- since Task 19 -- refuse to
        # open at all.  It lands in the copy's OWN sealed sibling, still outside
        # the copy's carrier root.
        sealed_dest = sealed_root_for(dest)
        sealed_dest.mkdir(parents=True, exist_ok=True)
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
        r = subprocess.run(["git", "-C", str(self.repo), *args], input=stdin,
                           capture_output=True, text=True,
                           env={**os.environ, **GIT_ENV})
        if r.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} in {self.repo} failed ({r.returncode}): "
                f"{r.stderr.strip()[:400]}")
        return r.stdout
