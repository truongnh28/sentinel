"""
GATE 1 -- the carriers live OUTSIDE the repo, on a real filesystem.
Spec: eval/PLAN.md Task 13; ../pipelines/SPEC-P1a-Harness.md Part 3.

The whole trick of the thesis is one sentence: the repo is reset to every task's
`base_commit`, and the agent's state is NOT.  `core.CarrierStore` cannot show
that -- it is a dict in RAM, so nothing is ever actually reset and "survives the
reset" is a claim with no experiment behind it.  These tests run the reset for
real (`git clean -xfd` + `git checkout <base_commit>`) against a store on disk.

Two things make the reset test able to fail, rather than merely able to pass:

  * a CONTROL inside the repo.  A scratch file in the worktree and an edit to a
    tracked file must both be GONE afterwards.  Without it the test would go
    green against a reset that did nothing at all -- and then it would keep going
    green if the carriers moved back inside the repo.
  * ALL FOUR carriers.  `branch` is the only one that lives INSIDE the repo
    (in `.git/`, decision B-1: keep `.git`, only `checkout`), so a test that
    checks `memory`/`skill`/`queue` and stops is green BY LUCK on the one carrier
    the reset could plausibly reach.
"""
from __future__ import annotations
import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest

import core
import retrieval
from core import CARRIERS, Item

from carrier_store_fs import FSCarrierStore


#: Fixed identity and fixed dates: a commit's sha is then a pure function of its
#: content, so the branch carrier holds no wall-clock reading.  Same reason
#: core.seed_of exists -- nothing that is hashed may vary between two runs of the
#: same command.
GIT_ENV = {
    "GIT_AUTHOR_NAME": "auditgame", "GIT_AUTHOR_EMAIL": "auditgame@invalid",
    "GIT_COMMITTER_NAME": "auditgame", "GIT_COMMITTER_EMAIL": "auditgame@invalid",
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}

BASE_SRC = "def f():\n    return 1\n"


def git(repo: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                       text=True, env={**os.environ, **GIT_ENV})
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def make_repo(path: pathlib.Path) -> str:
    """A one-commit repo standing in for a SWE-bench instance.  Returns base_commit."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True,
                   env={**os.environ, **GIT_ENV})
    (path / "src.py").write_text(BASE_SRC, encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "base")
    return git(path, "rev-parse", "HEAD").strip()


def reset_repo(repo: pathlib.Path, base_commit: str) -> None:
    """The reset that happens between two tasks.  Decision B-1: `.git` is KEPT,
    only the worktree is put back -- which is exactly why a carrier stored as a
    git ref survives and one stored as a worktree file does not."""
    git(repo, "clean", "-xfd", "-q")
    git(repo, "checkout", "-q", "--force", base_commit)


def an_item(carrier: str, t: int = 0, topic="orm", extra: str = "") -> Item:
    return Item(carrier=carrier, topic=topic,
                content=f"note written into {carrier} at task {t}{extra}",
                created_at=t, provenance="agent", poisoned=False)


class CarriersOutsideTheRepo(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="auditgame-fs-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = self.tmp / "workspace" / "django"
        self.base = make_repo(self.repo)
        # SIBLING of the repo, never a descendant.  Asserted, not assumed: a
        # fixture that put the carriers under the repo would make every test in
        # this class vacuous while still printing OK.
        self.root = self.tmp / "carriers"
        self.assertFalse(self.root.resolve().is_relative_to(self.repo.resolve()),
                         "the fixture put the carrier root INSIDE the repo -- "
                         "this test cannot tell persistence from luck")

    # ---------------------------------------------------------------- the claim

    def test_carriers_survive_a_repo_reset(self):
        """All FOUR must be checked.  `branch` is the only one living INSIDE the
        repo (.git/), so checking only the other three can go green BY LUCK.

        The control is the other half: a scratch file and a mutated tracked file
        inside the worktree must be GONE, otherwise this passes against a reset
        that never happened.

        Thesis claim (vi): "reset repo KHONG reset agent" -- the whole trick of
        the thesis.
        """
        store = FSCarrierStore(self.root, repo=self.repo)
        written = {c: store.write(an_item(c, t=3)) for c in CARRIERS}

        # CONTROL: state the reset is supposed to destroy.
        scratch = self.repo / "agent_scratch.txt"
        scratch.write_text("the agent's working notes", encoding="utf-8")
        (self.repo / "src.py").write_text("def f():\n    return 999\n", encoding="utf-8")

        reset_repo(self.repo, self.base)

        self.assertFalse(scratch.exists(),
                         "the reset did not remove an untracked worktree file: "
                         "this fixture cannot demonstrate anything about survival")
        self.assertEqual((self.repo / "src.py").read_text(encoding="utf-8"), BASE_SRC,
                         "the reset did not restore the tracked file to base_commit")

        # Re-opened from scratch, the way the next task would open it.
        after = FSCarrierStore(self.root, repo=self.repo)
        for c in CARRIERS:
            live = after.live(c)
            self.assertEqual([it.item_id for it in live], [written[c].item_id],
                             f"carrier {c!r} did not survive the repo reset")
            self.assertEqual(live[0].content, written[c].content,
                             f"carrier {c!r} survived as an id but lost its content")

    def test_a_quarantine_decision_survives_a_repo_reset(self):
        """Quarantine is the defender's only causal channel.  If it does not
        persist, an item quarantined at task t is live again at task t+1 and every
        harm number is measured against a defence that silently undid itself.

        Thesis claim (vi): "quyet dinh cach ly cung phai song qua reset".
        """
        store = FSCarrierStore(self.root, repo=self.repo)
        kept = store.write(an_item("memory", t=1, extra=" kept"))
        killed = store.write(an_item("memory", t=1, extra=" killed"))
        store.quarantine(killed.item_id)

        reset_repo(self.repo, self.base)

        after = FSCarrierStore(self.root, repo=self.repo)
        self.assertIn(killed.item_id, after.quarantined)
        self.assertEqual([it.item_id for it in after.live("memory")], [kept.item_id])

    def test_the_branch_carrier_is_stored_inside_the_repos_git_directory(self):
        """Decision B-1 spelled out.  `branch` is the carrier whose whole point is
        that it rides in `.git`, so a version that quietly wrote it to a JSONL file
        beside the other three would pass `survive_a_repo_reset` for the WRONG
        reason -- it would survive because it was never in the repo, not because
        `.git` is kept.

        Thesis claim (vi): "carrier branch nam trong .git, reset chi dung toi
        worktree".
        """
        store = FSCarrierStore(self.root, repo=self.repo)
        it = store.write(an_item("branch", t=2))

        refs = git(self.repo, "for-each-ref", "--format=%(refname)", "refs/heads").split()
        self.assertTrue(any(it.item_id in r for r in refs),
                        f"no git ref carries the branch item {it.item_id!r}: {refs}")
        self.assertFalse((self.root / "branch.jsonl").exists(),
                         "the branch carrier was written outside the repo -- it "
                         "would survive a reset without .git having anything to do "
                         "with it")

    # -------------------------------------------------- it is really on disk

    def test_another_process_reading_the_same_root_sees_every_write(self):
        """In-process survival proves nothing: a dict survives a reset too, because
        a reset never touched it.  A SECOND PROCESS is the only witness that the
        state reached the filesystem, and it is also what the benchmark actually
        does -- the agent runs in a container, the measurement does not.

        Thesis claim (vi): "trang thai nam tren dia, khong phai trong RAM".
        """
        store = FSCarrierStore(self.root, repo=self.repo)
        ids = {c: store.write(an_item(c, t=5)).item_id for c in CARRIERS}

        code = (
            "import json, pathlib, sys\n"
            f"sys.path.insert(0, {str(pathlib.Path.cwd())!r})\n"
            "from carrier_store_fs import FSCarrierStore\n"
            "from core import CARRIERS\n"
            f"s = FSCarrierStore(pathlib.Path({str(self.root)!r}), "
            f"repo=pathlib.Path({str(self.repo)!r}))\n"
            "print(json.dumps({c: [i.item_id for i in s.live(c)] for c in CARRIERS}))\n"
        )
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout)
        self.assertEqual(got, {c: [ids[c]] for c in CARRIERS})

    def test_reopening_a_carrier_root_finds_the_repo_again_by_itself(self):
        """`harness.last_run_store()` takes no repo argument, so the root has to
        remember which repo holds its `branch` carrier.  If it does not, the store
        comes back with THREE carriers and no error, and the Task 19 scan that
        looks for a leaked hidden-test path would simply never look at `branch`.

        Thesis claim (vi): "mo lai carrier root phai thay du BON carrier".
        """
        store = FSCarrierStore(self.root, repo=self.repo)
        it = store.write(an_item("branch", t=0))
        reopened = FSCarrierStore(self.root)            # no repo= handed in
        self.assertEqual([i.item_id for i in reopened.live("branch")], [it.item_id])

    # ------------------------------------- it behaves like core.CarrierStore

    def test_it_answers_every_query_the_same_way_the_in_memory_store_does(self):
        """The FS store is a swap-in for `core.CarrierStore`, so a run that uses it
        must produce the same retrieval, the same live set and the same snapshot.
        Anything else moves a measured number by changing the plumbing.

        Thesis claim (vi): "doi cho luu tru KHONG duoc doi so do duoc".
        """
        mem, fs = core.CarrierStore(), FSCarrierStore(self.root, repo=self.repo)
        items = [an_item(c, t=t, topic=tp)
                 for t, (c, tp) in enumerate(
                     [("memory", "orm"), ("skill", "orm"), ("queue", "http"),
                      ("branch", "orm"), ("memory", "http")])]
        for it in items:
            mem.write(it)
            fs.write(it)
        fs.quarantine(items[1].item_id)
        mem.quarantine(items[1].item_id)

        self.assertEqual(fs.snapshot(), mem.snapshot())
        self.assertEqual([i.item_id for i in fs.live()], [i.item_id for i in mem.live()])
        for topic in ("orm", "http", "nothing"):
            self.assertEqual([i.item_id for i in fs.retrieve(topic)],
                             [i.item_id for i in mem.retrieve(topic)],
                             f"retrieval disagreed on topic {topic!r}")

    def test_retrieval_off_the_disk_is_still_graded_not_exact(self):
        """Retrieval became GRADED (Jaccard at retrieval.THETA); an FS store that
        re-implemented `retrieve` as a string `==` would pass every test above --
        all their topics are single tokens, where Jaccard takes only {0, 1} -- and
        silently put epsilon back to having no surface.

        Thesis claim (vi): "truy xuat co cap do, khong phai bang nhau tuyet doi".
        """
        fs = FSCarrierStore(self.root, repo=self.repo)
        task_topic = retrieval.Topic({"django", "db", "models", "query"})
        partial = retrieval.Topic({"django", "db", "models"})     # sim = 0.75 >= 0.50
        far = retrieval.Topic({"django"})                          # sim = 0.25 <  0.50
        near_it = fs.write(Item(carrier="memory", topic=partial, content="near",
                                created_at=0, provenance="agent", poisoned=False))
        far_it = fs.write(Item(carrier="memory", topic=far, content="far",
                               created_at=0, provenance="agent", poisoned=False))

        reopened = FSCarrierStore(self.root, repo=self.repo)
        got = [i.item_id for i in reopened.retrieve(task_topic)]
        self.assertIn(near_it.item_id, got,
                      "a strict SUBSET topic was not retrieved: retrieval went back "
                      "to exact matching, and epsilon lost its surface again")
        self.assertNotIn(far_it.item_id, got, "theta stopped excluding anything")

    def test_a_token_set_topic_round_trips_the_way_core_dumps_writes_it(self):
        """`frozenset` iteration order is per-process, so a JSONL line that wrote
        the raw set would serialise the SAME carrier to a DIFFERENT byte string on
        two runs -- the trap core.dumps closes with `sorted()`.  The FS store must
        close it the same way, or the two on-disk formats disagree.

        Thesis claim (vi): "cung mot trang thai phai ra cung mot chuoi byte".
        """
        topic = retrieval.Topic({"django", "db", "models"})
        it = Item(carrier="queue", topic=topic, content="set topic",
                  created_at=0, provenance="agent", poisoned=False)
        FSCarrierStore(self.root, repo=self.repo).write(it)

        line = (self.root / "queue.jsonl").read_text(encoding="utf-8").strip()
        self.assertEqual(json.loads(line)["topic"], sorted(topic),
                         "the topic was not written as a SORTED list")
        self.assertEqual(json.loads(line)["topic"],
                         json.loads(core.dumps(core.item_record(it)))["topic"],
                         "the JSONL encoder and core.dumps disagree on a token set")

    def test_two_items_agreeing_on_every_field_are_refused_at_the_write(self):
        """core.CarrierStore.write raises on an item_id collision, because
        quarantining one of two colliding items would ERASE THE OTHER.  Persisting
        to disk must not lose that guard -- on disk the second write would also
        leave a duplicate line that reloads as two items.

        Thesis claim (vi): "hai item trung id phai bi chan NGAY LUC GHI".
        """
        fs = FSCarrierStore(self.root, repo=self.repo)
        fs.write(an_item("memory", t=7))
        with self.assertRaises(AssertionError):
            fs.write(an_item("memory", t=7))
        self.assertEqual(len(FSCarrierStore(self.root, repo=self.repo).live("memory")), 1,
                         "the refused write still reached the file")

    def test_a_detached_copy_refuses_to_invent_a_branch_carrier(self):
        """`clone()` is a DETACHED copy: it has no repo, so by B-1 it has nowhere
        legitimate to put a `branch` item.  Writing one to a JSONL file instead
        would create a branch carrier that outlives a reset for a reason that has
        nothing to do with `.git` -- the exact confusion
        test_the_branch_carrier_is_stored_inside... exists to prevent.

        Thesis claim (vi): "ban sao tach roi KHONG duoc tu che carrier branch".
        """
        fs = FSCarrierStore(self.root, repo=self.repo)
        for c in CARRIERS:
            fs.write(an_item(c, t=4))
        cp = fs.clone()
        self.addCleanup(shutil.rmtree, cp.root, True)

        self.assertEqual(cp.snapshot(), fs.snapshot(), "the copy lost state")
        cp.write(an_item("memory", t=9))                      # allowed
        self.assertEqual(len(fs.live("memory")), 1, "the copy wrote through to the original")
        with self.assertRaises(AssertionError):
            cp.write(an_item("branch", t=9))


if __name__ == "__main__":
    unittest.main()
