"""The v3 freeze and the run tool (T22; D7.freeze, D33, plan S6).  Infrastructure; the rows
that protect a draft sentence are in v3/dcm/T22.csv.  Run from auditgame/.

Every manifest here is written to a temporary directory, and the unseal log and the Gate-4
file are redirected there too, so frozen/ is never written.  The dev smoke runs T6's runner
on a few dev workflows; no test reads an eval workflow."""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import costs
import freeze
import freeze_d35
import policies as P
from v3 import api
from v3 import attackers as A
from v3 import config as C
from v3 import corpus as K
from v3 import freeze_v3 as F
from v3 import grid as G
from v3 import seal

sys.path.insert(0, str(pathlib.Path("tools").resolve()))
import v3_run as R  # noqa: E402

V2_FREEZE = "freeze: clean sha256:c789fa7362e0"


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.man = self.dir / "MANIFEST-V3.json"
        self.patches = [mock.patch.object(seal, "LOG_PATH", self.dir / "v3-unseal-log.jsonl"),
                        mock.patch.object(seal, "GATE_PATH", self.dir / "V3-GATE4.json"),
                        mock.patch.object(F, "MANIFEST_PATH", self.man)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()


def _stub_run_chain(calls=None, drop_field=None):
    """A run_chain that fabricates one record per workflow from the chain's identity, for
    the tool-side checks (the real runner is exercised in the dev smoke test)."""
    def run(chain, workflows, factory_of, split, token=None):
        if calls is not None:
            calls.append(chain)
        u, out = chain.unit, []
        ident = C.identity(u.world, u.cell)
        if drop_field:
            ident["cell"] = {k: v for k, v in ident["cell"].items() if k != drop_field}
        for i, wf in enumerate(workflows):
            out.append(api.EpisodeRecord(
                split=split, world=ident["world"], world_id=ident["world_id"],
                cell=ident["cell"], cell_id=ident["cell_id"], delta=u.cell.delta,
                wf=wf.wf_id, repo=wf.repo, H=wf.H, order=i, seed=chain.seed,
                policy=u.system, attack=u.column, placement="p" if u.is_br else None,
                k=("memory",), iota=0, sigma=1, eps=0.6, harm=0.0, solved_sigma=True,
                harm_locked_at=None, detected_at=None, missed_before_sigma=True, fq=0,
                true_q=0, false_removed=0, benign_inspected=0, clean_lost_branch=0,
                t_lost=0, n_solved=wf.H, spent=0.0, budget=1.0, audits={}, c_traj=(),
                quarantines=(), delta_hat=None, n_incidents_seen=0, line5_source=None,
                decision_log_sha256="0" * 64))
        return out
    return run


class TestInfraFreeze(_Tmp):
    def test_harness_refuses_policy_not_in_v3_manifest(self):
        """D7.freeze: "Defender policies and the attacker library are serialised and hashed
        before final evaluation; the evaluation harness refuses to run a policy whose hash
        is not in the frozen manifest."  Also D12.freeze.

        Once a v3 manifest exists, require_frozen refuses a name it does not hold and
        passes every system the grid builds; v3_run checks every system of its chains
        before it simulates anything."""
        F.require_frozen("not-a-policy")          # no manifest: nothing is frozen yet
        F.write(self.man)
        with self.assertRaises(F.NotFrozen):
            F.require_frozen("not-a-policy")
        for name in G.all_systems():
            F.require_frozen(name)
        calls = []
        with mock.patch.object(G, "chains", lambda *a, **k: [
                G.Chain(G.Unit("main", "main", "primary", C.PRIMARY,
                               C.Cell(rho=0.0, delta=4), "rogue-policy", G.HELD_OUT[0]), 0)]):
            with self.assertRaises(F.NotFrozen):
                R.main(["--split", "dev", "--seeds", "1", "--workflows", "1", "--jobs", "1",
                        "--out", str(self.dir / "out")], run_chain=_stub_run_chain(calls))
        self.assertEqual(calls, [])

    def test_eval_refused_on_dirty_or_missing_freeze(self):
        """D5.5.freeze: "Adaptive attack development is performed on a development split,
        and both the defender policy and the attacker library are frozen before final
        evaluation on held-out repositories and held-out attacker policies."

        Missing v3 freeze: the header reads NONE, seal lists it, v3_run --split eval exits 2
        before any chain runs, and the attempt is logged.  A fresh manifest reads clean
        (seal no longer lists freeze_v3); a drifted one reads DRIFTED and is refused again,
        by seal and by the summary refusal."""
        h = F.header_line()
        self.assertTrue(h.startswith("freeze-v3: NONE"))
        self.assertFalse(seal._v3_clean(h))
        self.assertTrue(any("freeze_v3" in r for r in seal.reasons({"split": "eval"})))
        calls = []
        rc = R.main(["--split", "eval", "--jobs", "1", "--out", str(self.dir / "out")],
                    run_chain=_stub_run_chain(calls))
        self.assertEqual(rc, R.EXIT_REFUSED)
        self.assertEqual(calls, [])
        log = [json.loads(x) for x in seal.LOG_PATH.read_text().splitlines()]
        self.assertEqual(len(log), 1)
        self.assertFalse(log[0]["granted"])
        self.assertEqual(log[0]["run_meta"]["tool"], "tools/v3_run.py")
        self.assertIsNotNone(R.refusal("eval", h))
        self.assertIsNone(R.refusal("dev", h))

        F.write(self.man)
        h = F.header_line()
        self.assertTrue(h.startswith("freeze-v3: clean"), h)
        self.assertTrue(seal._v3_clean(h) and F.clean(h))
        self.assertFalse(any("freeze_v3" in r for r in seal.reasons({"split": "eval"})))

        doc = json.loads(self.man.read_text())
        doc["source"]["grid.py"] = "0" * 64
        self.man.write_text(json.dumps(doc))
        h = F.header_line()
        self.assertTrue(h.startswith("freeze-v3: DRIFTED"), h)
        self.assertIn("source/grid.py: changed", h)
        self.assertFalse(seal._v3_clean(h))
        self.assertTrue(any("freeze_v3 is not clean" in r
                            for r in seal.reasons({"split": "eval"})))
        self.assertIsNotNone(R.refusal("eval", h))
        with self.assertRaises(R.Refused):
            R.summarise(self.dir, "eval", h)

    def test_manifest_hashes_policies_and_attacker_library(self):
        """D9.freeze: "Defender policies and attacker libraries are frozen by hash before
        evaluation."

        The manifest holds every v3 source file and DCM shard by sha256, the policy
        registries, the scripted library with its held-out split and the BR menu, the
        split digests and the grid; moving any of them moves the digest."""
        man = F.manifest()
        self.assertEqual(set(man), set(F.SECTIONS))
        self.assertEqual(set(man["source"]),
                         {p.name for p in pathlib.Path("v3").glob("*.py")})
        self.assertIn("T22.csv", man["dcm"])
        self.assertEqual(man["source"]["grid.py"],
                         hashlib.sha256(pathlib.Path("v3/grid.py").read_bytes()).hexdigest())
        self.assertLessEqual({"B1 audit-at-commit", "Oracle (+)"},
                             set(man["registries"]["baselines"]))
        self.assertEqual(set(man["registries"]["grid_systems"]), set(G.all_systems()))
        self.assertEqual(man["attackers"]["held_out"], A.held_out())
        self.assertEqual(man["attackers"]["scripted"], sorted(A.SCRIPTED))
        self.assertEqual(man["attackers"]["br_eps"], list(A.BR_EPS))
        self.assertEqual(man["splits"]["eval_split_sha256"], K.EVAL_SPLIT_SHA256)
        self.assertEqual(len(man["splits"]["dev_order"]), C.DEV_N_WORKFLOWS)
        self.assertEqual(man["grid"], G.definition_digest())
        d = F.digest(man)
        self.assertEqual(d, F.digest())
        for sec, key in (("source", "grid.py"), ("attackers", "held_out"), ("dcm", "T22.csv")):
            moved = json.loads(json.dumps(man))
            moved[sec][key] = "moved"
            self.assertNotEqual(F.digest(moved), d, sec)
        F.write(self.man)
        self.assertEqual(F.digest(F.load()), F.load()["digest"])

    def test_base_v2_and_d35_freezes_stay_clean(self):
        """The v3 freeze sits on v2's: building and reading it leaves the v2 line
        'freeze: clean sha256:c789fa7362e0' and the D35 line clean, pins the v2 digest as
        its base, and restores the policies module it installs costs on."""
        kappa = dict(P.KAPPA)
        man = F.manifest()
        h = F.header_line()
        self.assertEqual(dict(P.KAPPA), kappa, "header_line left costs installed")
        self.assertIn("base " + V2_FREEZE, h)
        self.assertNotIn("PIN CONFLICT", h)
        self.assertTrue(man["base"]["v2"].startswith("c789fa7362e0"))
        self.assertEqual(man["base"]["v2"], freeze.load()["digest"])
        self.assertEqual(man["base"]["d35"], freeze_d35.load()["digest"])
        old = costs.install(P)
        try:
            self.assertEqual(freeze.header_line(), V2_FREEZE)
            self.assertTrue(freeze_d35.clean(freeze_d35.header_line()))
        finally:
            costs.restore(P, old)
        self.assertEqual(F.MANIFEST_PATH.parent.name, pathlib.Path(self.tmp.name).name)
        self.assertNotIn(F.MANIFEST_PATH.name, {freeze.MANIFEST_PATH.name,
                                                freeze_d35.PATH.name})

    def test_records_are_pinned_by_sha256(self):
        """D33: every record file of a run is pinned by sha256, lines and bytes."""
        out = self.dir / "run"
        out.mkdir()
        files = {"main.jsonl": b'{"a":1}\n{"a":2}\n', "br.jsonl": b'{"b":1}\n'}
        for n, b in files.items():
            (out / n).write_bytes(b)
        pin = R.pin_records(out, list(files))
        text = pin.read_text()
        for n, b in files.items():
            self.assertIn(f"{hashlib.sha256(b).hexdigest()}  {n}\n", text)
            lines = b.count(b"\n")
            self.assertIn(f"#   {lines}  {len(b)}  {n}\n", text)

    def test_dev_smoke_records_carry_every_switch(self):
        """D9.grid: "Results are reported on the (Δ, 𝜒) grid rather than pooled" -- so every
        record carries its whole cell and world.

        One chain of each core block that has a buildable system (baselines, the block
        schedule) runs on T6's runner on three dev workflows at one seed; every record
        carries every WorldV3 and Cell field of its chain, both ids and the split.  A
        record missing a switch is rejected by the tool."""
        wfs = K.dev_workflows()[:3]
        buildable = set(G.BASELINE_SYSTEMS) - {G.B7} | {G.BLOCK_SCHEDULE}
        picked, seen = [], set()
        for ch in G.chains(seeds=C.SEEDS[:1], core_only=True):
            u = ch.unit
            if u.block in seen or u.system not in buildable:
                continue
            if u.is_br and u.cell.delta not in (4, C.DELTA_ATTACKER):
                continue
            seen.add(u.block)
            picked.append(ch)
        self.assertGreaterEqual(len(picked), 8)
        out = self.dir / "smoke"
        written = R.simulate(picked, wfs, "dev", out, jobs=1)
        n = 0
        by_block = {ch.unit.block.replace(":", "_") + ".jsonl": ch for ch in picked}
        for name in written:
            ch = by_block[name]
            recs = R.load_records(out / name)
            for r in recs:
                n += 1
                self.assertEqual(r.world, ch.unit.world.as_dict())
                self.assertEqual(r.cell, ch.unit.cell.as_dict())
                self.assertEqual(set(r.world), set(C.world_fields()))
                self.assertEqual(set(r.cell), set(C.cell_fields()))
                self.assertEqual((r.world_id, r.cell_id),
                                 (C.world_id(ch.unit.world), C.cell_id(ch.unit.cell)))
                self.assertEqual(r.split, "dev")
        self.assertGreater(n, 0)
        bad = G.Chain(G.Unit("main", "main", "primary", C.PRIMARY,
                             C.Cell(rho=0.0, delta=4), "B1 audit-at-commit", G.HELD_OUT[0]), 0)
        rec = _stub_run_chain(drop_field="chi")(bad, wfs[:1], None, "dev")[0]
        with self.assertRaises(ValueError):
            R.validate_record(rec, bad, "dev")
        ok = _stub_run_chain()(bad, wfs[:1], None, "dev")[0]
        R.validate_record(ok, bad, "dev")
        with self.assertRaises(ValueError):
            R.validate_record(ok, bad, "eval")

    def test_run_stops_before_simulating_a_system_whose_task_has_not_landed(self):
        """B7 (T21) has no factory yet, and Sentinel's class (T15) has no frozen parts yet
        (T14's line-5 table, T18's tuned tau / eta_Q: sentinel.check_ready): a run naming
        them exits 3 and simulates nothing, after the freeze checks."""
        calls = []
        rc = R.main(["--split", "dev", "--blocks", "attacker-delta", "--seeds", "1",
                     "--workflows", "1", "--jobs", "1", "--out", str(self.dir / "o")],
                    run_chain=_stub_run_chain(calls))
        self.assertEqual(rc, R.EXIT_NO_RUNNER)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
