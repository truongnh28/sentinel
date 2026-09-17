"""
GATE 1 -- the frozen, offline-generated payload bank (Task 26).
Spec: task-llmpayload-brief.md; SPEC-AuditGame-SE Part 0.

This suite protects four claims about `payloads.FrozenPayloadAttack` and the
committed corpus it plays:

  1. the bank makes F_match MULTI-DIMENSIONAL, where MatchedAttack leaves it
     one-dimensional (the premise of the whole task, kept as a live test);
  2. a committed payload is a FROZEN STRING -- the file self-seals and the reader
     refuses a tampered byte;
  3. K2/K3 hold for the new pipeline (it reads no ground truth, no budget, no
     policy) and its output is deterministic across processes (K1/K1b);
  4. the held-out split is by hash of the payload name, identical across processes.

STDLIB ONLY, like the rest of the measurement core.  The infra generator
(payloads/generate.py) is NEVER imported here -- it is exercised, if at all, as a
subprocess, exactly as swebench_fetch.py is.
"""
from __future__ import annotations
import inspect
import json
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest

import build
import payloads
from core import seed_of


def _wf(i: int, H: int = 8):
    return build.make_workflow(f"wf-{i:03d}", "django", H,
                               random.Random(seed_of("frozen-test", i)))


def _payload_axes(pipe, n: int = 30, delta: int = 2):
    """Distinct `depth`, `derived` and `provenance` over a SET of payloads the
    pipeline generates for different events.  This is F_match as the attacker
    actually produces it, read straight off Item.surface()."""
    depths, deriveds, provs = set(), set(), set()
    for i in range(n):
        wf = _wf(i)
        ps = pipe.plan(wf, "memory", delta, random.Random(seed_of("plan", i)))
        if ps is None:
            continue
        it = pipe.payload(wf, ps)
        s = it.surface(now=ps.sigma)
        depths.add(s["depth"])
        deriveds.add(s["derived"])
        provs.add(it.provenance)
    return depths, deriveds, provs


class FMatchIsMultiDimensional(unittest.TestCase):
    """The task's premise, and the thing it fixes, both kept as live tests."""

    def test_matched_attack_leaves_derived_constant_the_axis_this_bank_opens(self):
        """MatchedAttack produces the SAME `derived` for every event: a payload has
        no parents, so `derived` is 0 always.  Measured in the task brief as
        derived in [0,0] -- one of the three constant features that make the
        distinguishability classifier effectively one-variable.  This is the RED the
        diversified bank turns green; if MatchedAttack ever varied `derived` on its
        own the premise would be wrong and this test says so.

        Thesis claim (vi): "cong mot khuon giu derived hang so, bo phan biet con mot bien".
        """
        import attacks
        _d, deriveds, _p = _payload_axes(attacks.MatchedAttack())
        self.assertEqual(
            len(deriveds), 1,
            f"MatchedAttack varies `derived` across events ({sorted(deriveds)}); the "
            f"task premise (derived in [0,0]) no longer holds -- STOP and re-check.")

    def test_the_frozen_bank_varies_depth_derived_and_provenance(self):
        """The fix: the bank's payloads take MORE THAN ONE value on each of `depth`,
        `derived` and `provenance`, so the F_match measurement exercises more than
        `size` alone.  Asserted per axis so a bank that collapses any one of them
        fails for the axis it collapsed.

        Thesis claim (vi): "ngan hang payload lam F_match da chieu, khong con mot bien".
        """
        depths, deriveds, provs = _payload_axes(payloads.FrozenPayloadAttack())
        self.assertGreater(len(depths), 1,
                           f"the bank's payloads all have depth {depths} -- provenance "
                           f"depth does not vary")
        self.assertGreater(len(deriveds), 1,
                           f"the bank's payloads all have derived {deriveds} -- no "
                           f"record carries derived_from")
        self.assertGreater(len(provs), 1,
                           f"the bank's payloads all have provenance {provs} -- the "
                           f"provenance string does not vary")


class TheCorpusIsFrozen(unittest.TestCase):
    """A committed payload obeys the no-edit rule of a `content=` literal."""

    def test_the_committed_corpus_matches_its_own_self_seal(self):
        """Loading the real committed file verifies payloads_sha256 against the hash
        of the records it seals; if they disagree, load_frozen raises.  Green here
        means the committed corpus has not been hand-edited since it was generated.

        Thesis claim (vi): "corpus dong bang khop dau niem cua chinh no".
        """
        bank = payloads.load_frozen()          # raises FrozenPayloadTampered on mismatch
        self.assertGreaterEqual(len(bank), 12,
                                "the bank must hold >=12 records (task brief)")

    def test_editing_one_byte_of_a_frozen_payload_makes_the_reader_refuse(self):
        """Change a single character of a committed payload and the seal no longer
        matches, so the reader raises rather than measuring with an item_id that
        describes an item nobody committed.

        Thesis claim (vi): "sua mot byte trong corpus dong bang thi reader tu choi".
        """
        doc = json.loads(pathlib.Path(payloads.DEFAULT_PATH).read_text(encoding="utf-8"))
        doc["payloads"][0]["content"] += "x"    # one byte, seal left untouched
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False)
            tampered = fh.name
        try:
            with self.assertRaises(payloads.FrozenPayloadTampered):
                payloads.load_frozen(tampered)
        finally:
            pathlib.Path(tampered).unlink()

    def test_a_seal_that_matches_still_loads(self):
        """The refusal above must be caused by the MISMATCH, not by any copy through
        a temp file: the same document, re-sealed over its edited records, loads.
        Without this, the tamper test could pass for the wrong reason (e.g. the
        reader rejecting every temp path).

        Thesis claim (vi): "niem khop thi van doc duoc; do choi la do lech, khong do sao chep".
        """
        doc = json.loads(pathlib.Path(payloads.DEFAULT_PATH).read_text(encoding="utf-8"))
        doc["payloads"][0]["content"] += "x"
        doc["payloads_sha256"] = payloads._records_sha256(doc["payloads"])  # re-seal
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False)
            resealed = fh.name
        try:
            bank = payloads.load_frozen(resealed)
            self.assertTrue(any(p.content.endswith("x") for p in bank))
        finally:
            pathlib.Path(resealed).unlink()


class FrozenPayloadConformance(unittest.TestCase):
    """K1-K3 for the new pipeline.  It is registered in attacks.PENDING (it fails
    the gate-2 AUC bar, by design and by measurement), so the REGISTRY conformance
    suite does not reach it; the contract is enforced here instead."""

    def test_K2_the_pipeline_cannot_read_ground_truth(self):
        """No method takes a `store`: an attack that received a CarrierStore could
        read other items' `.poisoned`.  Checked by SIGNATURE, a structural bar.

        Thesis claim (vi): "cong khong nhan store, khong doc duoc nhan that".
        """
        pipe = payloads.FrozenPayloadAttack()
        for meth in ("plan", "payload"):
            params = inspect.signature(getattr(pipe, meth)).parameters
            bad = [p for p in params if "store" in p.lower()]
            self.assertFalse(bad, f"{meth} takes {bad} -- can read ground truth")

    def test_K3_the_pipeline_does_not_touch_the_budget(self):
        """Only the defender spends budget.  Walk the class AST: no name may be
        `charge`, `budget` or `spent`.

        Thesis claim (vi): "cong khong dung ngan sach; moi chinh sach chay tren cung B".
        """
        from tests.fixtures import identifiers
        used = identifiers(payloads.FrozenPayloadAttack)
        for forbidden in ("charge", "budget", "spent"):
            self.assertNotIn(forbidden, used, f"pipeline touches the budget: {forbidden!r}")

    def test_K1_same_seed_yields_the_same_payload(self):
        """Same event => byte-identical payload and item_id, within one process.

        Thesis claim (vi): "cung seed cho cung payload; ket qua tai lap duoc".
        """
        pipe = payloads.FrozenPayloadAttack()
        wf = _wf(0)
        ids = set()
        for _ in range(3):
            ps = pipe.plan(wf, "memory", 2, random.Random(7))
            ids.add(pipe.payload(wf, ps).item_id)
        self.assertEqual(len(ids), 1, f"non-deterministic item_id within a process: {ids}")

    def test_K1b_payload_is_identical_across_PYTHONHASHSEED(self):
        """The template pick is seeded through core.seed_of, not hash(), so it does
        not move with PYTHONHASHSEED.  Run in fresh processes to prove it.

        Thesis claim (vi): "payload khong doi theo PYTHONHASHSEED; khong dung hash()".
        """
        code = (
            "import random, build, payloads\n"
            "from core import seed_of\n"
            "wf = build.make_workflow('wf-000','django',8,random.Random(seed_of('frozen-test',0)))\n"
            "pipe = payloads.FrozenPayloadAttack()\n"
            "ps = pipe.plan(wf,'memory',2,random.Random(7))\n"
            "print(pipe.payload(wf, ps).item_id)\n")
        outs = set()
        for h in ("0", "1", "424242"):
            r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                               text=True, cwd=".",
                               env={"PYTHONHASHSEED": h, "PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 0, f"run failed at HASHSEED={h}: {r.stderr[-400:]}")
            outs.add(r.stdout)
        self.assertEqual(len(outs), 1,
                         f"payload item_id changes with PYTHONHASHSEED:\n{sorted(outs)}")


class TheHeldOutSplit(unittest.TestCase):
    """Split by hash of the payload NAME, fixed before any measurement."""

    def test_the_split_is_deterministic_across_two_processes(self):
        """The same names land on the same side of the split in a fresh process:
        the split is a property of the name through core.seed_of, not of a run.

        Thesis claim (vi): "chia held-out theo hash ten, tat dinh qua hai tien trinh".
        """
        here = {n: payloads.held_out(n) for n in (p.name for p in payloads.load_frozen())}
        code = (
            "import payloads\n"
            "print({n: payloads.held_out(n) for n in "
            "(p.name for p in payloads.load_frozen())})\n")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, cwd=".",
                           env={"PYTHONHASHSEED": "99", "PATH": "/usr/bin:/bin"})
        self.assertEqual(r.returncode, 0, f"subprocess failed: {r.stderr[-400:]}")
        there = eval(r.stdout)
        self.assertEqual(here, there,
                         "the held-out split differs across processes -- it is not "
                         "fixed by the name")

    def test_held_out_and_development_partition_the_bank(self):
        """Every name is on exactly one side, and both sides come from the same bank.

        Thesis claim (vi): "held-out va development chia doi ngan hang, khong chong lan".
        """
        held, dev = payloads.held_out_names(), payloads.development_names()
        allnames = {p.name for p in payloads.load_frozen()}
        self.assertEqual(held | dev, allnames)
        self.assertEqual(held & dev, set())


if __name__ == "__main__":
    unittest.main()
