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

OPEN QUESTION, TO SETTLE BEFORE THE FIRST REAL-AGENT RUN (Task 16/17).
`core.item_record` includes `poisoned`, the GROUND TRUTH flag whose own docstring
says audit policies must not read it -- and `harness.mounts()` hands this whole
root to the container rw.  Nothing reads it there today (the mock agent does not,
and the policies run in the measurement process, not the container), so no number
in this build is affected.  But once a real agent reads the carriers from inside
the container, a flag saying "this item is the payload" is the same leak shape as
the hidden tests: harm would then measure whether the agent can read a label
rather than whether the attack works.  The fix is a decision about WHERE ground
truth lives, not a detail of this file, so it is written down rather than guessed
at here.
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
        self.root.mkdir(parents=True, exist_ok=True)
        self.repo = self._attach(repo)
        self.items = {c: [] for c in CARRIERS}
        self.quarantined = set()
        self._load()

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

    def _load_flat(self, carrier: str) -> None:
        path = self.root / f"{carrier}.jsonl"
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                self.items[carrier].append(core.item_from_record(json.loads(line)))

    def _load_branch(self) -> None:
        out = self._git("for-each-ref", "--format=%(refname:short)",
                        f"refs/heads/{BRANCH_NS}")
        # Sorted by the zero-padded sequence number baked into the ref name, so
        # write order is recovered exactly.  Ref listing order is git's business;
        # `live()` order is ours, and the traces depend on it.
        for ref in sorted(out.split()):
            rec = json.loads(self._git("cat-file", "-p", f"{ref}:item.json"))
            self.items[BRANCH].append(core.item_from_record(rec))

    # ----------------------------------------------------------------- write

    def write(self, it: Item) -> Item:
        if it.carrier == BRANCH and not self.attached:
            raise AssertionError(
                "the `branch` carrier lives in the repo's .git (decision B-1) and "
                "this store has no repo attached. Writing it to a JSONL file "
                "instead would produce a branch carrier that outlives a repo "
                "reset for a reason that has nothing to do with git.")
        super().write(it)                      # collision guard, then append
        if it.carrier == BRANCH:
            self._write_branch(it, seq=len(self.items[BRANCH]) - 1)
        else:
            with (self.root / f"{it.carrier}.jsonl").open("a", encoding="utf-8") as f:
                f.write(_line(core.item_record(it)) + "\n")
        return it

    def _write_branch(self, it: Item, seq: int) -> None:
        """One item -> one git branch, via plumbing.

        blob -> tree -> root commit -> `git branch auditgame/<seq>-<item_id>`.
        A real branch rather than a file in `.git/`: `git clean -xfd` cannot see
        it and `git checkout` does not touch it, which is the B-1 property stated
        in the one way a reader can check by running git themselves.
        """
        payload = _line(core.item_record(it)) + "\n"
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
                "".join(_line(core.item_record(it)) + "\n" for it in self.items[BRANCH]),
                encoding="utf-8")
        # No REPO_POINTER in the copy: that is what makes it detached.
        return FSCarrierStore(dest)

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
