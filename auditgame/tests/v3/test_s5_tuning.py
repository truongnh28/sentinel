"""The v3 tuning tool (T18, tools/v3_tune.py).  Each test protects the DCM rows of
v3/dcm/T18.csv that name it; its docstring carries the id and the verbatim draft sentence.

The end-to-end runs here are tiny (1 dev workflow, 1 seed, reduced grids): they check the
plumbing and the objective, not a tuned value.  The smoke of plan T18 is the CLI's
--smoke (1 seed, 5 dev workflows)."""
import copy
import inspect
import json
import pathlib
import tempfile
import unittest

import draft_setup as D
from tools import v3_tune as T
from v3 import agent as AG
from v3 import baselines as BL
from v3 import config as C
from v3 import runner as R
from v3 import seal

TOOL_SRC = pathlib.Path(T.__file__).read_text()


def tiny(**kw):
    """One dev workflow, one seed, one rho, one attacker, reduced grids."""
    args = dict(workflows=T.dev_workflows(1), seeds=(1,), rhos=(0.0,),
                attacks=("memory-first-write-e0.6",), tau5_grid=(0.0, 0.3),
                sw_grid=("commit3",), progress=lambda *_: None)
    args.update(kw)
    return T.tune(**args)


def _sw_members():
    return {n: v for n, v in T.default_members().items() if n.startswith("L-SW-")}


class TestS5Tuning(unittest.TestCase):

    def test_tuning_objective_is_worst_case_L_over_three_kernels(self):
        """D5.robust -- "transition kernels are known up to a total-variation uncertainty ζ"
        (S6.1 p.4 Assumption 2).  C6: tau, eta_Q and tau5 are tuned on dev by the worst-case
        L of Definition 1, max over three kernels zeta = 0.10 apart."""
        # three kernels, the world differing in the kernel only, zeta apart
        self.assertEqual(T.KERNELS, ("nominal", "low", "high"))
        ws = T.worlds()
        self.assertEqual(set(ws), set(T.KERNELS))
        for k, w in ws.items():
            self.assertEqual(w, C.PRIMARY.__class__(**{**C.PRIMARY.as_dict(), "kernel": k}))
        nom, low, high = (AG.KERNELS[k] for k in T.KERNELS)
        self.assertAlmostEqual(nom[0] - low[0], C.ZETA)
        self.assertAlmostEqual(high[1] - nom[1], C.ZETA)
        self.assertEqual(C.ZETA, 0.10)

        # worst_case = max over kernels AND columns; every kernel is required
        L = {"nominal": {"a@4": 0.2, "b@4": 0.1}, "low": {"a@4": 0.5, "b@4": 0.3},
             "high": {"a@4": 0.1, "b@4": 0.4}}
        self.assertEqual(T.worst_case(L), 0.5)
        with self.assertRaises(ValueError):
            T.worst_case({"nominal": L["nominal"], "low": L["low"]})
        self.assertEqual(T.robust_matrix(L), {"a@4": 0.5, "b@4": 0.4})

        # a candidate best under the nominal kernel but worst under 'low' loses
        cands = [{"param": "nominal-best", "value": T.worst_case(
                    {"nominal": {"c": 0.0}, "low": {"c": 0.9}, "high": {"c": 0.1}}), "fq": 0},
                 {"param": "robust", "value": T.worst_case(
                    {"nominal": {"c": 0.3}, "low": {"c": 0.3}, "high": {"c": 0.3}}), "fq": 0}]
        self.assertEqual(T.choose(cands)["param"], "robust")

        # the measured value is Definition 1's L, per kernel, from the runner's records
        wf = T.dev_workflows(1)[0]
        an = "memory-first-write-e0.6"
        fac = BL.factory(BL.B1AuditAtCommit.name)
        m = T.measure(fac, 0.0, [wf], (1,), attacks=(an,), deltas=(4,))
        self.assertEqual(set(m["L"]), set(T.KERNELS))
        for k, w in T.worlds().items():
            pl = T.Plans().get(an, wf, 4, w)
            rec = R.run_episode(wf, pl, fac, w, C.Cell(rho=0.0, delta=4), 1).record
            self.assertAlmostEqual(m["L"][k][f"{an}@4"], R.loss_of(rec))
            self.assertAlmostEqual(R.loss_of(rec), R.loss(rec.harm, rec.fq, rec.t_lost))

        # the minimax LP (line-8 step): matching pennies has value 1/2
        mm = T.minimax({"p": {"x": 1.0, "y": 0.0}, "q": {"x": 0.0, "y": 1.0}},
                       {"p": 0.0, "q": 0.0})
        self.assertAlmostEqual(mm["value"], 0.5, places=6)
        self.assertAlmostEqual(mm["mixture"]["p"], 0.5, places=5)

        # end to end: each tau5 candidate's logged value is the worst case over kernels
        res = tiny()
        for e in (e for e in res["log"] if e["step"] == "tau5" and "candidate" in e):
            self.assertEqual(set(e["by_kernel"]), set(T.KERNELS))
            self.assertAlmostEqual(e["worst_L"], max(e["by_kernel"].values()))
        vals = {e["candidate"]["tau5"]: e["worst_L"] for e in res["log"]
                if e["step"] == "tau5" and "candidate" in e}
        best = min(vals.values())
        self.assertEqual(res["tuned"]["rho"]["0"]["tau5"],
                         min(v for v in vals if round(vals[v], 4) == round(best, 4)))
        self.assertIn("worst-case L", res["tuned"]["objective"])

    def test_tuning_reads_dev_only(self):
        """D5.5.dev-split -- "Adaptive attack development is performed on a development
        split" (S5.5 p.4).  Plan S6: tools/v3_tune.py has no road to eval; it refuses any
        other split and reads workflows only through v3.corpus.dev_workflows()."""
        T.require_dev("dev")
        for split in ("eval", "primary", "secondary", "test"):
            with self.assertRaises(seal.SealedSplit):
                T.require_dev(split)
            with self.assertRaises(seal.SealedSplit):
                T.tune(split=split, progress=lambda *_: None)
            with self.assertRaises(seal.SealedSplit):
                T.measure(BL.factory(BL.B1AuditAtCommit.name), 0.0, [], (1,), attacks=(),
                          split=split)
            with self.assertRaises(seal.SealedSplit):
                T.main(["--split", split, "--smoke"])
        # a workflow that is not dev is refused
        wf = T.dev_workflows(1)[0]
        fake = copy.copy(wf)
        object.__setattr__(fake, "wf_id", "not-a-dev-workflow")
        with self.assertRaises(seal.SealedSplit):
            tiny(workflows=[fake])
        # the dev workflows are corpus.dev_workflows()
        from v3 import corpus
        self.assertEqual([w.wf_id for w in T.dev_workflows()],
                         [w.wf_id for w in corpus.dev_workflows()])
        # no road to eval in the source: no token, no accessor, no builder
        for bad in ("eval_workflows", "unseal", "Unsealed", "_build_primary",
                    "_build_secondary", "_materialise", "_specs", "corpus.json"):
            self.assertNotIn(bad, TOOL_SRC, bad)
        self.assertIn("split=DEV", inspect.getsource(T.measure))
        # every record a tuning run makes is a dev record
        res = tiny()
        self.assertEqual(res["tuned"]["split"], "dev")
        self.assertTrue(set(res["tuned"]["setup"]["workflows"])
                        <= {w.wf_id for w in corpus.dev_workflows()})

    def test_eta_q_not_on_grid_edge_or_declared(self):
        """DA1.l8 -- "if Pr[poisoned | bt +1 ] > τ and expected harm > ηQ then" (Alg. 1
        line 8 p.3).  sentinel-v3.md: the chosen eta_Q is not on the grid edge, or the edge
        is declared; check_tuned refuses an undeclared edge."""
        g = T.ETA_Q_GRID
        self.assertEqual(g, tuple(D.ETA_Q_GRID))
        self.assertIsNotNone(T.edge_declaration(min(g), g))
        self.assertIsNotNone(T.edge_declaration(max(g), g))
        for e in sorted(g)[1:-1]:
            self.assertIsNone(T.edge_declaration(e, g))
        with self.assertRaises(ValueError):
            T.edge_declaration(0.123, g)
        good = {"grids": {"eta_q": list(g)}, "rho": {"0": {"eta_q": 0.1, "eta_q_edge": None}}}
        T.check_tuned(good)
        bad = {"grids": {"eta_q": list(g)}, "rho": {"0": {"eta_q": 0.0, "eta_q_edge": None}}}
        with self.assertRaises(ValueError):
            T.check_tuned(bad)
        bad["rho"]["0"]["eta_q_edge"] = T.edge_declaration(0.0, g)
        T.check_tuned(bad)
        with self.assertRaises(ValueError):
            T.check_tuned({"rho": {"0": {"eta_q": None}}})     # untuned needs a reason
        # end to end with the smoke's stub belief: the chosen eta_Q carries its declaration
        # exactly when it is on the edge
        res = tiny(belief_factory=T.stub_belief_factory, members=_sw_members(),
                   tau_grid=(0.5,), eta_grid=(0.0, 0.1, 0.5))
        blk = res["tuned"]["rho"]["0"]
        self.assertIn(blk["eta_q"], (0.0, 0.1, 0.5))
        self.assertEqual(blk["eta_q_edge"], T.edge_declaration(blk["eta_q"], (0.0, 0.1, 0.5)))
        # line 8 is the draft's rule: both thresholds must be exceeded
        b = T.StubAlarmBelief(R.context(T.dev_workflows(1)[0], C.PRIMARY,
                                        C.Cell(rho=0.0, delta=4), 1))
        b.m = {k: 0.0 for k in C.CARRIERS}
        b.m["skill"] = 0.8
        self.assertEqual(T.line8_rule(b, 0.5, 0.0), "skill")
        self.assertIsNone(T.line8_rule(b, 0.9, 0.0))
        self.assertIsNone(T.line8_rule(b, 0.5, 0.99))
        # without a belief, line 8 cannot run: not tuned, with the reason
        res = tiny()
        blk = res["tuned"]["rho"]["0"]
        self.assertIsNone(blk["eta_q"])
        self.assertIn("belief", blk["line8_reason"])

    def test_selection_log_is_hashed(self):
        """D9.frozen -- "Defender policies and attacker libraries are frozen by hash before
        evaluation." (S9.4 p.6).  sentinel-v3.md: the tuning's selection log is hashed; the
        output pins the log's sha256 and the written log reproduces it."""
        res = tiny()
        tuned, log = res["tuned"], res["log"]
        self.assertEqual(tuned["log_sha256"], T.log_sha256(log))
        self.assertEqual(len(tuned["log_sha256"]), 64)
        # every candidate and every choice is logged
        steps = [(e["step"], "choice" in e) for e in log]
        self.assertIn(("tau5", True), steps)
        self.assertIn(("sw_weights", True), steps)
        self.assertEqual(sum(1 for e in log if e["step"] == "tau5" and "candidate" in e), 2)
        # the log changes -> the hash changes
        other = json.loads(json.dumps(log))
        other[0]["worst_L"] += 1e-6
        self.assertNotEqual(T.log_sha256(other), tuned["log_sha256"])
        # the written log reproduces the pin; a smoke may not overwrite reference/
        with tempfile.TemporaryDirectory() as d:
            out, lp = T.write(res, pathlib.Path(d) / "tuned.json")
            back = [json.loads(x) for x in lp.read_text().splitlines()]
            self.assertEqual(T.log_sha256(back), json.loads(out.read_text())["log_sha256"])
        res["tuned"]["smoke"] = True
        with self.assertRaises(ValueError):
            T.write(res, T.TUNED_PATH)
        res["log"] = other
        with self.assertRaises(AssertionError), tempfile.TemporaryDirectory() as d:
            res["tuned"]["smoke"] = False
            T.write(res, pathlib.Path(d) / "tuned.json")

        # the hashed log is reproducible regardless of --jobs N: the per-candidate
        # measurements run in N worker processes (tools/v3_build_table.py's deterministic
        # ProcessPoolExecutor pattern -- the result does not depend on N), while the log and
        # every choice are assembled by the same single-process control flow.  So the tuned
        # JSON and its log_sha256 are byte-identical at --jobs 1 and --jobs N; only the
        # wall-clock `timing` block, which is not part of log_sha256, differs.
        kw = dict(rhos=(0.0, 0.25), belief_factory=T.stub_belief_factory,
                  members=_sw_members(), tau_grid=(0.3, 0.5), eta_grid=(0.0, 0.1))
        r1, r2 = tiny(jobs=1, **kw), tiny(jobs=4, **kw)
        self.assertEqual(r1["log"], r2["log"])
        self.assertEqual(r1["tuned"]["log_sha256"], r2["tuned"]["log_sha256"])
        strip = lambda t: {k: v for k, v in t.items() if k != "timing"}   # noqa: E731
        self.assertEqual(strip(r1["tuned"]), strip(r2["tuned"]))
        # the parallel run actually distributed line-8 work (>1 (tau, eta, member) candidate)
        self.assertGreater(sum(1 for e in r1["log"]
                               if e["step"] == "line8" and "candidate" in e), 1)
        T.check_tuned(r1["tuned"])
        T.check_tuned(r2["tuned"])
        # --jobs 1 is the default and leaves the single-process path untouched (no cache)
        self.assertEqual(inspect.signature(T.tune).parameters["jobs"].default, 1)
        self.assertIsNone(inspect.signature(T.tune_rho).parameters["cache"].default)

        # CHECKPOINT / RESUME (v3-tune-resume, 28/09/2026).  The hash is over the SELECTION
        # LOG, so a run finished from a checkpoint must reproduce the same evidence: every
        # per-candidate measurement is appended by its content key as it completes, --resume
        # loads the completed ones and computes only the rest, and the control flow that
        # assembles the log is unchanged.  So the tuned JSON and log_sha256 come out
        # byte-identical to a single-shot run (only the wall-clock `timing` differs).
        self.assertFalse(inspect.signature(T.tune).parameters["resume"].default)
        # the checkpoint is a run artefact: never beside the tracked reference/ output
        self.assertEqual(T.checkpoint_path(T.TUNED_NOMINAL_PATH).name,
                         "v3_tuned_nominal.ckpt.jsonl")
        self.assertEqual(T.checkpoint_path(T.TUNED_NOMINAL_PATH).parent, T.CKPT_DIR)
        self.assertNotIn("reference", T.CKPT_DIR.parts)
        with tempfile.TemporaryDirectory() as d:
            ck = pathlib.Path(d) / "tiny.ckpt.jsonl"
            single = tiny(checkpoint=ck, **kw)                   # a fresh run checkpoints
            lines = ck.read_text().splitlines()
            head = json.loads(lines[0])["header"]
            self.assertIn("config_digest", head)
            # the digest covers what would change a measurement
            self.assertLessEqual(
                {"code_version", "schema", "belief", "line8", "kernels", "rhos", "deltas",
                 "seeds", "grids", "n_workflows", "fq_cap", "members", "band", "world",
                 "lambda_Q", "lambda_T"}, set(head["config"]))
            keys = [T.measure_key_of_id(json.loads(x)["job_id"]) for x in lines[1:]]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertEqual(set(keys), {j[0] for j in T._enumerate_jobs(
                kw["rhos"], (0.0, 0.3), ("commit3",), kw["tau_grid"], kw["eta_grid"],
                kw["members"], kw["belief_factory"])})
            # a checkpoint holding only SOME measurements (a kill mid-run)
            keep = 1 + len(keys) // 2
            ck.write_text("\n".join(lines[:keep]) + "\n")
            calls, orig = [], T.measure

            def spy(*a, **k):                        # noqa: ANN002
                calls.append(1)
                return orig(*a, **k)
            T.measure = spy
            try:
                back = tiny(checkpoint=ck, resume=True, **kw)
            finally:
                T.measure = orig
            # ONLY the missing measurements were recomputed
            self.assertEqual(len(calls), len(keys) - (keep - 1))
            self.assertGreater(keep - 1, 0)
            # ... and the finished run is byte-identical (log, its hash, the tuned JSON)
            self.assertEqual(single["log"], back["log"])
            self.assertEqual(single["tuned"]["log_sha256"], back["tuned"]["log_sha256"])
            self.assertEqual(strip(single["tuned"]), strip(back["tuned"]))
            self.assertEqual(json.dumps(strip(single["tuned"]), indent=2, sort_keys=True),
                             json.dumps(strip(back["tuned"]), indent=2, sort_keys=True))
            # the resumed run appended the recomputed ones: the checkpoint is whole again
            self.assertEqual(len(ck.read_text().splitlines()) - 1, len(keys))
            # a header from a DIFFERENT config is REFUSED, never silently mixed
            with self.assertRaises(ValueError):
                T.load_checkpoint(ck, "sha256:not-this-run")
            bad = ck.read_text().splitlines()
            bad[0] = json.dumps({"header": {"config_digest": "sha256:stale",
                                            "config": head["config"]}})
            ck.write_text("\n".join(bad) + "\n")
            with self.assertRaisesRegex(ValueError, "without --resume"):
                tiny(checkpoint=ck, resume=True, **kw)
            # the fingerprint really moves with the config (here: the eta_Q grid)
            fp = dict(rhos=(0.0,), seeds=(1,), workflows=T.dev_workflows(1), attacks=("a",),
                      deltas=(4,), kernels=T.KERNELS, members={"m": None},
                      belief_label=None, line8=T.line8_rule, band=None, tau5_grid=(0.0,),
                      sw_grid=("commit3",), tau_grid=(0.3,), eta_grid=(0.0,),
                      world=C.PRIMARY, fq_cap=None, delta_hat="cell")
            self.assertNotEqual(T.config_digest(T.config_fingerprint(**fp)),
                                T.config_digest(T.config_fingerprint(
                                    **{**fp, "eta_grid": (0.0, 0.1)})))
            # the same under --jobs N (the path the real run uses): the pool is handed ONLY
            # the missing jobs, the loaded ones fill the same content-keyed cache
            ck2 = pathlib.Path(d) / "tiny-jobs.ckpt.jsonl"
            tiny(jobs=4, checkpoint=ck2, **kw)
            ln2 = ck2.read_text().splitlines()
            self.assertEqual(len(ln2) - 1, len(keys))
            ck2.write_text("\n".join(ln2[:keep]) + "\n")
            sent, orig_pool = [], T._run_measure_pool

            def spy_pool(jobs_list, *a, **k):         # noqa: ANN002
                sent.append(len(jobs_list))
                return orig_pool(jobs_list, *a, **k)
            T._run_measure_pool = spy_pool
            try:
                back4 = tiny(jobs=4, checkpoint=ck2, resume=True, **kw)
            finally:
                T._run_measure_pool = orig_pool
            self.assertEqual(sent, [len(keys) - (keep - 1)])
            self.assertEqual(single["log"], back4["log"])
            self.assertEqual(strip(single["tuned"]), strip(back4["tuned"]))
            # without --resume a run truncates and rewrites the header, so it stays recoverable
            tiny(checkpoint=ck, **kw)
            self.assertEqual(json.loads(ck.read_text().splitlines()[0])["header"][
                "config_digest"], head["config_digest"])
            self.assertEqual(len(ck.read_text().splitlines()) - 1, len(keys))


if __name__ == "__main__":
    unittest.main()
