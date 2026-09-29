"""The eval splits stay sealed until P5 (plan S6, T2).  Infrastructure.

Nothing here builds a workflow of an eval split, and nothing runs a policy: the tests check
that every road to eval refuses on a P2 tree, that each attempt is logged, that no v3
module or tool has a road around the seal, and that the reduced SWE-rebench-V2 copy
matches its sha256 manifest.  The unseal log and the Gate-4 file are redirected to a
temporary directory, so the real frozen/ is never written.  Run from auditgame/.
"""
import json
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from v3 import corpus as K
from v3 import seal as S

V3_DIR = pathlib.Path("v3")
TOOLS_DIR = pathlib.Path("tools")
#: The two P5 tools the plan lets reach eval (plan S6 layer 4).
P5_TOOLS = {"tools/v3_run.py", "tools/v3_headline_rollout.py"}
#: The P0 tools are v2-era files the plan freezes (S2); they write spikes/v3-p0/.
FROZEN_P0 = re.compile(r"^tools/v3_p0_\w+\.py$")
EVAL_LITERAL = re.compile(r"""split\s*={1,2}\s*["']eval["']""")
#: corpus.py internals and data that only corpus.py and seal.py may name.
PRIVATE = ("_build_primary", "_build_secondary", "_materialise", "_candidate_families",
           "_chosen_families", "_secondary_rows", "_index(", "_ISSUER", "_ISSUED",
           "swerebench_v2_eval_pool", "POOL_FILE", "INDEX_FILE", "swerebench_v2_index")


def scanned_files() -> list:
    files = sorted(V3_DIR.glob("*.py")) + sorted(TOOLS_DIR.glob("v3_*.py"))
    return [f for f in files if not FROZEN_P0.match(f.as_posix())]


class TestInfraSeal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self.tmp.name)
        self.log = tmp / "v3-unseal-log.jsonl"
        self.gate = tmp / "V3-GATE4.json"
        self.patches = [mock.patch.object(S, "LOG_PATH", self.log),
                        mock.patch.object(S, "GATE_PATH", self.gate)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_eval_split_refuses_without_unseal(self):
        """D5.5.freeze (D33): "Adaptive attack development is performed on a development
        split, and both the defender policy and the attacker library are frozen before
        final evaluation on held-out repositories and held-out attacker policies."

        eval_workflows takes only a token unseal() issued; on a P2 tree -- no Gate-4 file,
        no freeze_v3 -- unseal refuses, for split='eval' and for anything else."""
        self.assertEqual(S.GATE_PATH, self.gate)
        for fake in (None, "token", object(), {"split": "eval"}):
            with self.assertRaises(S.SealedSplit):
                S.eval_workflows(fake)
        with self.assertRaises(S.SealedSplit):
            S.Unsealed(object(), {"split": "eval"}, "now", {})
        forged = object.__new__(S.Unsealed)                 # skips __init__
        with self.assertRaises(S.SealedSplit):
            S.eval_workflows(forged, "secondary")

        for meta in ({"split": "eval"}, {"split": "dev"}, {}):
            with self.assertRaises(S.SealedSplit) as cm:
                S.unseal(meta)
            msg = str(cm.exception)
            self.assertIn("Gate-4", msg)
            self.assertIn("freeze_v3", msg)
        why = S.reasons({"split": "dev"})
        self.assertTrue(any("split='eval'" in w for w in why), why)

        # a Gate-4 file with the wrong split digests is refused, and naming them
        # correctly is not enough on its own either
        self.gate.write_text(json.dumps({f: "x" for f in S.GATE_FIELDS}))
        why = S.reasons({"split": "eval"})
        self.assertTrue(any("eval_split_sha256" in w for w in why), why)
        self.assertTrue(any("secondary_split_sha256" in w for w in why), why)
        gate = {f: "x" for f in S.GATE_FIELDS}
        gate.update(eval_split_sha256=K.EVAL_SPLIT_SHA256,
                    secondary_split_sha256=K.SECONDARY_SPLIT_SHA256)
        self.gate.write_text(json.dumps(gate))
        why = S.reasons({"split": "eval"})
        self.assertFalse(any("split_sha256" in w for w in why), why)
        self.assertTrue(why, "a gate with placeholder digests must not unseal")
        with self.assertRaises(S.SealedSplit):
            S.unseal({"split": "eval"})

    def test_granted_token_builds_the_committed_split(self):
        """The P5 road works end to end, checked on SHAPE only (no policy runs): with every
        condition forced true, unseal() grants and logs, and eval_workflows returns the
        workflows whose instance lists hash to the committed digests."""
        with mock.patch.object(S, "reasons", return_value=[]):
            token = S.unseal({"split": "eval", "run": "shape-check"})
        line = json.loads(self.log.read_text().splitlines()[-1])
        self.assertTrue(line["granted"])
        for split in K.SPLITS:
            wfs = S.eval_workflows(token, split)
            specs = K._specs(split)
            self.assertEqual([(w.wf_id, w.repo, [t.task_id for t in w.tasks]) for w in wfs],
                             [(s["wf_id"], s["family"], s["instances"]) for s in specs])
            self.assertTrue(all(t.base_commit and t.topic is not None
                                for w in wfs for t in w.tasks))
        with mock.patch.object(K, "EVAL_SPLIT_SHA256", "0" * 64):
            with self.assertRaises(S.SealedSplit):
                S.eval_workflows(token, "primary")

    def test_every_unseal_attempt_is_logged(self):
        """Plan S6 layer 3: every unseal() call appends one line to the unseal log, with
        what was asked, whether it was granted, why not, and the committed digests."""
        metas = [{"split": "eval", "run": "a"}, {"split": "dev"}, {"split": "eval", "run": "b"}]
        for m in metas:
            with self.assertRaises(S.SealedSplit):
                S.unseal(m)
        lines = [json.loads(l) for l in self.log.read_text().splitlines()]
        self.assertEqual(len(lines), len(metas))
        for line, m in zip(lines, metas):
            self.assertEqual(line["run_meta"], m)
            self.assertFalse(line["granted"])
            self.assertTrue(line["reasons"])
            self.assertEqual(line["eval_split_sha256"], K.EVAL_SPLIT_SHA256)
            self.assertEqual(line["secondary_split_sha256"], K.SECONDARY_SPLIT_SHA256)
            self.assertIn("at", line)
        self.assertEqual(S.LOG_PATH.name, "v3-unseal-log.jsonl")

    def test_no_v3_module_reads_eval_outside_seal(self):
        """Plan S6 layer 4: in v3/ and tools/v3_*.py, `eval_workflows(` and split='eval' only
        in seal.py and the two P5 tools; spikes/v3-p0/corpus.json nowhere; the corpus
        builders and the eval data only in corpus.py and seal.py."""
        files = scanned_files()
        self.assertIn(pathlib.Path("v3/corpus.py"), files)
        self.assertIn(pathlib.Path("v3/seal.py"), files)
        bad = []
        for f in files:
            name, text = f.as_posix(), f.read_text(encoding="utf-8")
            if name not in P5_TOOLS | {"v3/seal.py"}:
                if "eval_workflows(" in text:
                    bad.append(f"{name}: calls eval_workflows(")
                if EVAL_LITERAL.search(text):
                    bad.append(f"{name}: uses split='eval'")
            if "corpus.json" in text:
                bad.append(f"{name}: reads spikes/v3-p0/corpus.json")
            if name not in ("v3/corpus.py", "v3/seal.py"):
                bad += [f"{name}: names {p}" for p in PRIVATE if p in text]
        seal_text = pathlib.Path("v3/seal.py").read_text(encoding="utf-8")
        for p in PRIVATE:
            if p in seal_text and p not in ("_materialise", "_ISSUER", "_ISSUED"):
                bad.append(f"v3/seal.py: names {p}")
        self.assertEqual(bad, [])

    def test_corpus_exposes_digests_and_shape_only(self):
        """Plan S6 layer 1: corpus.py's public surface is a fixed list; the only public
        function returning workflows is dev_workflows (dev), and eval_digest /
        eval_summary return a digest and counts -- no instance of an eval split."""
        public = {n for n in dir(K) if not n.startswith("_") and callable(getattr(K, n))
                  and getattr(getattr(K, n), "__module__", None) == K.__name__}
        self.assertEqual(public, {"dev_workflows", "family_of", "is_exercise", "manifest",
                                  "verify_data", "v2_repos", "touched_families",
                                  "eval_digest", "kish", "eval_summary", "fetch"})
        for split in K.SPLITS:
            d = K.eval_digest(split)
            self.assertRegex(d, r"^[0-9a-f]{64}$")
            text = json.dumps(K.eval_summary(split))
            leaked = [i for s in K._specs(split) for i in s["instances"] if i in text]
            self.assertEqual(leaked, [], f"{split} summary names an instance")
        dev_inst = {t.task_id for w in K.dev_workflows() for t in w.tasks}
        eval_inst = {i for sp in K.SPLITS for s in K._specs(sp) for i in s["instances"]}
        self.assertEqual(dev_inst & eval_inst, set(), "a dev code path reaches an eval instance")

    def test_rebench_data_matches_its_sha256_manifest(self):
        """The reduced SWE-rebench-V2 copy is pinned: sha256 of each decompressed jsonl,
        row counts, revision; the pool holds every instance the primary split uses."""
        self.assertEqual(K.verify_data(), [])
        man = K.manifest()
        self.assertEqual((man["dataset"], man["revision"]),
                         (K.REBENCH_DATASET, K.REBENCH_REVISION))
        self.assertEqual(man["parquet_rows"], 32079)
        files = man["files"]
        self.assertEqual(set(files), {K.INDEX_FILE.name, K.POOL_FILE.name})
        self.assertEqual(files[K.INDEX_FILE.name]["rows"], 32079)
        self.assertEqual(tuple(files[K.POOL_FILE.name]["fields"]), K.POOL_FIELDS)
        for f in ("repo", "instance_id", "created_at", "base_commit", "patch", "test_patch",
                  "FAIL_TO_PASS", "image_name", "flags"):
            self.assertIn(f, K.POOL_FIELDS)
        _, pool = K._read_jsonl_gz(K.POOL_FILE)
        have = {r["instance_id"] for r in pool}
        need = {i for s in K._build_primary() for i in s["instances"]}
        self.assertLessEqual(need, have)


if __name__ == "__main__":
    unittest.main()
