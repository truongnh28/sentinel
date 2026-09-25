"""The v2 eval tool's summaries and run safety (D14, D15, D27, D28, D33), on small synthetic record
files in a temporary OUT.  Nothing is simulated and no eval record is read: every test that asks
for --split eval also replaces the stages with stubs that fail if called.

    ../.venv/bin/python -m unittest tests.tools.test_v2_eval_summary -v
"""
import contextlib
import dataclasses
import io
import json
import math
import pathlib
import tempfile
import unittest
from unittest import mock

import attackers_v2 as A
import carrier_runner as R
import draft_setup as D
import metrics
import metrics_v2 as MV
import sentinel as S
import tools.run_draft_eval as rde

B1, SEN, ORACLE, RHO = "B1 audit-at-commit", "Sentinel-A1", S.CONTROL, 0.25
WFS = (("w1", "r1"), ("w2", "r1"), ("w3", "r2"), ("w4", "r2"))
SEEDS, DELTAS, SETTINGS = (1, 2), (0, 4, 8), ("mid", "weak")
HO = A.held_out()
COLS = list(A.SCRIPTED) + [A.br_attacks()[0].name]        # 18 scripted + one BR column
ARGV = ["--summarise-only", "--split", "dev", "--seeds", "1", "2", "--deltas", "0", "4", "8",
        "--rhos", "0.25"]
NAN = float("nan")


def harm(p, a, d, wf, seed, oracle_harm):
    if d == 0:
        return 1.0                     # every system harmed at Delta = 0: the (-) control holds
    if p == ORACLE:
        return oracle_harm
    return float((len(p) + len(a) + d + int(wf[1:]) + seed) % 3 == 0)


def main_rec(p, a, d, st, wf, repo, seed, h, **job):
    """A record exactly as run_draft_eval.work writes one."""
    j = rde.Job(p, a, d, st, RHO, **job)
    r = R.EpisodeResult(harm=h, solved_sigma=True, detected_at=None if h else 2, iota=1,
                        sigma=1 + d, H=12, spent=10.0, n_solved=8, t_lost=(seed + d) % 2,
                        true_removed=0, false_removed=(seed + int(wf[1:])) % 3,
                        benign_inspected=10, patch_blocks=0, audits={k: 0 for k in D.TARGETS})
    rec = {k: v for k, v in dataclasses.asdict(r).items() if k != "audits"}
    rec.update({k: v for k, v in dataclasses.asdict(j).items() if k != "budget"})
    rec.update(budget=j.budget.label(), wf=wf, repo=repo, seed=seed, audits=r.audits)
    return rec


def br_v(p, d):
    return NAN if (p == B1 and d == 4) else {0: 0.9, 4: 0.3, 8: 0.6}[d]


def write_records(out: pathlib.Path, oracle_harm=0.0, sweeps=True):
    """Every file of a run, in run()'s format.  Returns the main-grid records."""
    out.mkdir(parents=True, exist_ok=True)

    def dump(name, recs):
        with open(out / name, "w") as fh:
            for r in recs:
                fh.write(json.dumps(r, default=str) + "\n")

    def cells(policies, attacks, deltas, **job):
        return [main_rec(p, a, d, "mid", w, rp, s, harm(p, a, d, w, s, oracle_harm), **job)
                for p in policies for a in attacks for d in deltas for w, rp in WFS for s in SEEDS]

    main = [main_rec(p, a, d, st, w, rp, s, harm(p, a, d, w, s, oracle_harm))
            for st in SETTINGS for p in S.REGISTRY for a in COLS for d in DELTAS
            for w, rp in WFS for s in SEEDS]
    dump("eval-main.jsonl", main)
    dump("eval-br.jsonl", [{"policy": p, "delta": d, "setting": "mid", "rho_patch": RHO,
                            "v_br": br_v(p, d), "v_br_naive": br_v(p, d), "n_workflows": len(WFS),
                            "per_wf": {w: br_v(p, d) for w, _ in WFS}, "repo_of": dict(WFS)}
                           for p in S.REGISTRY for d in DELTAS])
    if sweeps:
        dump("sweep-eta.jsonl", [r for e in (0.0, D.ETA_Q_BAYES)
                                 for r in cells([SEN], HO, D.HEADLINE_DELTAS, eta_q=e)])
        dump("sweep-match.jsonl", [r for m in (0.0, 0.5, 1.0)
                                   for r in cells([B1, SEN], HO, D.HEADLINE_DELTAS, match=m)])
        dump("sweep-persistent-drift.jsonl", cells([B1, SEN], HO, D.HEADLINE_DELTAS, drift_visible=None))
        dump("sweep-budget-EXPLORATORY.jsonl",
             [r for chi in (0.5, D.HEADLINE_CHI) for sh in (0.5, 1.0)
              for r in cells([B1, SEN], HO, rde.BUDGET_DELTAS, chi=chi, budget=D.BudgetSpec("share", sh))])
        dump("eval-gate-world.jsonl",
             [{"policy": p, "attack": a, "delta": d, "rho_patch": RHO, "wf": w, "repo": rp, "seed": s,
               "harm": harm(p, a, d, w, s, 0.0), "false_blocks": s + int(w[1:]), "t_lost": 0, "n_solved": 8}
              for p in rde.G.GATE_BASELINES for a in HO for d in D.HEADLINE_DELTAS for w, rp in WFS
              for s in SEEDS])
    return main


def ci_entries(x, path=""):
    """Every (path, dict) of a summary that holds a confidence interval."""
    if isinstance(x, dict):
        if "lo" in x or "abs_lo" in x:
            yield path, x
        for k, v in x.items():
            yield from ci_entries(v, f"{path}/{k}")


def strict(text):
    def refuse(c):
        raise ValueError(f"non-JSON constant {c}")
    return json.loads(text, parse_constant=refuse)


class _Tmp(unittest.TestCase):
    """A temporary OUT for every test; main() --split dev moves it to <tmp>/v2-smoke-dev."""
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.out_before = rde.OUT
        rde.OUT = self.root / "v2"
        self.dev = self.root / "v2-smoke-dev"

    def tearDown(self):
        rde.OUT = self.out_before
        self._tmp.cleanup()

    def main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = rde.main(argv)
        return code, buf.getvalue()


class TestWithholding(_Tmp):
    def test_a_failing_control_withholds_every_sentinel_number(self):
        write_records(self.dev, oracle_harm=1.0)          # (+) fails: the oracle is harmed
        (self.dev / "eval-sweeps-summary.json").write_text("{}")      # a stale one must go
        code, stdout = self.main(ARGV)
        self.assertNotEqual(code, 0)
        summary = strict((self.dev / "eval-summary.json").read_text())
        self.assertEqual(set(summary), {"run", "controls", "withheld"})
        self.assertFalse(summary["controls"]["ok"])
        self.assertEqual(summary["withheld"], rde.WITHHELD)
        self.assertIn("controls FAILED (D28): Sentinel numbers withheld", stdout)
        self.assertNotIn("curve_rho", stdout)
        self.assertFalse((self.dev / "eval-sweeps-summary.json").exists())


class TestSummaries(unittest.TestCase):
    """One passing summary of the synthetic run, read by every test below."""
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls._tmp.name)
        cls.out_before, rde.OUT = rde.OUT, root / "v2"
        cls.recs = write_records(root / "v2-smoke-dev")
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            cls.code = rde.main(ARGV)
        cls.stdout = buf.getvalue()
        cls.text = (root / "v2-smoke-dev" / "eval-summary.json").read_text()
        cls.sweeps_text = (root / "v2-smoke-dev" / "eval-sweeps-summary.json").read_text()
        cls.summary, cls.sweeps = strict(cls.text), strict(cls.sweeps_text)

    @classmethod
    def tearDownClass(cls):
        rde.OUT = cls.out_before
        cls._tmp.cleanup()

    def test_controls_pass_and_the_endpoint_is_printed_after_them(self):
        self.assertEqual(self.code, 0)
        self.assertTrue(self.summary["controls"]["ok"])
        self.assertLess(self.stdout.index("controls ok"), self.stdout.index("curve_rho"))

    def test_every_ci_resamples_ten_thousand_times(self):
        found = list(ci_entries(self.summary)) + list(ci_entries(self.sweeps))
        # curve, D22, 5 ablations, 3 Deltas, 2x2 transfer, Verified, 2 detectors; eta 2, match 3,
        # persistent 1, budget 2 chi x 2 shares x 3 Deltas
        self.assertEqual(len(found), 1 + 1 + 5 + 3 + 4 + 1 + 2 + 2 + 3 + 1 + 12)
        for path, entry in found:
            self.assertEqual(entry.get("n_boot"), 10000, path)
        self.assertEqual(rde.N_BOOT, 10000)
        self.assertEqual(rde.inspect.signature(MV.gain_vs_best).parameters["n_boot"].default, rde.N_BOOT)

    def test_worst_case_L_is_metrics_loss_on_the_columns_of_V(self):
        for p in (B1, SEN, "B2 uniform random"):
            cols = {}
            for r in self.recs:
                if (r["setting"] == "mid" and r["policy"] == p and r["attack"] in HO
                        and r["delta"] in D.HEADLINE_DELTAS):
                    cols.setdefault((r["attack"], r["delta"]), {}).setdefault(r["wf"], []).append(
                        metrics.loss(r["harm"], r["false_removed"], r["t_lost"]))
            hand = max(sum(sum(v) / len(v) for v in by_wf.values()) / len(by_wf) for by_wf in cols.values())
            row = self.summary["by_rho"]["0.25"]["table2"][p]
            self.assertAlmostEqual(row["worst_case_L"], hand, places=12)
            self.assertGreater(row["worst_case_L"], row["worst_case_harm"])

    def test_v_br_skips_a_nan_delta_and_names_it(self):
        row = self.summary["by_rho"]["0.25"]["table2"][B1]
        self.assertEqual(row["v_br_crossfit"], 0.6)          # the old max() read NaN at Delta 4 first
        self.assertEqual(row["v_br_nan_deltas"], [4])
        self.assertEqual(row["v_br_by_delta"], {"4": None, "8": 0.6})
        self.assertAlmostEqual(row["exploitability"], 0.6 - row["worst_case_harm"], places=12)

    def test_every_row_carries_its_n(self):
        s = self.summary
        rows = [s["controls"], s["curve_rho"]["0.25"], s["curve_rho_vs_best"]["0.25"],
                *s["by_rho"]["0.25"]["table2"].values(), *s["by_rho"]["0.25"]["table3_ablations"].values(),
                *s["by_rho"]["0.25"]["figure3_gain_by_delta"].values(),
                *s["by_rho"]["0.25"]["transfer_dev_vs_heldout"].values(),
                *s["by_rho"]["0.25"]["transfer_tuning_vs_heldout"].values(),
                s["by_rho"]["0.25"]["verified_only"], *s["by_rho"]["0.25"]["rq4_detectors"].values(),
                *s["gate_world"]["0.25"].values(), *[e for _, e in ci_entries(self.sweeps)],
                *self.sweeps["eta"]["0.25"].values()]
        for row in rows:
            for k in ("n_workflows", "n_repos", "n_episodes"):
                self.assertIn(k, row)
        # held-out x {4, 8} x 4 workflows x 2 seeds, every system playing the same episodes
        self.assertEqual(s["curve_rho"]["0.25"]["n_episodes"], len(HO) * 2 * len(WFS) * len(SEEDS))
        self.assertEqual(s["by_rho"]["0.25"]["table2"][B1]["n_episodes"], len(HO) * 2 * len(WFS) * len(SEEDS))
        self.assertEqual(s["by_rho"]["0.25"]["table2"][B1]["n_repos"], 2)

    def test_both_summaries_carry_the_run_block(self):
        for run in (self.summary["run"], self.sweeps["run"]):
            for k in ("split", "seeds", "deltas", "rhos", "rho_mid_only", "skip_br", "skip_sweeps",
                      "summarise_only", "ref_rho", "headline_rho", "family_alpha", "n_boot", "lambda_Q",
                      "lambda_T", "header_start", "header_summary", "git_head", "git_clean", "sha256",
                      "records_read", "present"):
                self.assertIn(k, run)
            self.assertEqual(run["split"], "dev")
            self.assertTrue(run["summarise_only"])
            self.assertEqual(run["records_read"]["eval-main.jsonl"], len(self.recs))
            self.assertEqual(run["present"]["eval-main.jsonl"]["seed"], [1, 2])
            self.assertEqual(run["present"]["eval-main.jsonl"]["setting"], ["mid", "weak"])
            self.assertEqual(set(run["sha256"]), {"tools/run_draft_eval.py", "tools/select_mixture.py"})

    def test_shape_of_the_new_rows(self):
        s, sw = self.summary, self.sweeps
        self.assertNotIn("NaN", self.text + self.sweeps_text)
        self.assertEqual(s["transfer_note"]["dev_attackers_with_heldout_keys"],
                         ["memory-last-ingress-e0.6", "uniform-last-ingress-e0.6", "uniform-mid-write-e0.6"])
        self.assertEqual(set(s["by_rho"]["0.25"]["transfer_tuning_vs_heldout"]),
                         {"tuning_attackers", "heldout_attackers"})
        self.assertEqual(list(sw["drift_visible"]["0.25"]), ["persistent"])
        self.assertEqual(list(sw["match"]["0.25"]), ["0.0", "0.5", "1.0"])
        self.assertEqual(sw["budget_EXPLORATORY"]["0.25"]["chi=1.34"]["share-1"]["4"]["chi_range"],
                         round(D.chi_range(D.TARGET_KAPPA_DRAFT), 4))
        g = sw["eta"]["0.25"]["0"]["gain_ci"]
        self.assertEqual((g["alpha"], g["deltas"]), (0.05, [4, 8]))
        self.assertEqual(s["denominators"]["reasons"]["infeasible"],
                         "attacker rule has no placement at this Δ and H")


class TestVBR(unittest.TestCase):
    def test_nan_delta_gives_the_same_answer_in_either_order(self):
        for by in ({4: NAN, 8: 0.3}, {8: 0.3, 4: NAN}):
            out = rde._v_br(by)
            self.assertEqual((out["v_br_crossfit"], out["v_br_nan_deltas"]), (0.3, [4]))
        for by in ({4: 0.3, 8: NAN}, {8: NAN, 4: 0.3}):
            self.assertEqual(rde._v_br(by)["v_br_crossfit"], 0.3)
        self.assertTrue(math.isnan(rde._v_br({4: NAN})["v_br_crossfit"]))
        self.assertEqual(rde._v_br({4: 0.2, 8: 0.5})["v_br_crossfit"], 0.5)


class TestStreaming(_Tmp):
    def test_the_loader_drops_br_columns_and_unused_fields(self):
        recs = write_records(rde.OUT, sweeps=False)
        with tempfile.TemporaryDirectory() as tmp:
            got = rde._load("eval-main.jsonl", pathlib.Path(tmp), ("rho_patch", "setting"), rde.MAIN_FIELDS,
                            attacks=set(rde._summarised()))
            self.assertEqual(got.read, len(recs))
            kept = [r for r in recs if not r["attack"].startswith("br:")]
            self.assertEqual(got.kept, len(kept))
            self.assertEqual(set(got.shards), {(RHO, st) for st in SETTINGS})
            cell = got.cell((RHO, "mid"))
            self.assertTrue(all(set(r) == set(rde.MAIN_FIELDS) for r in cell))
            self.assertFalse(any(r["attack"].startswith("br:") for r in cell))
            # file order kept: every mean sums as it did on the whole list
            self.assertEqual(cell, [{f: r[f] for f in rde.MAIN_FIELDS} for r in kept if r["setting"] == "mid"])
            self.assertIsNone(rde._load("eval-gate-world.jsonl", pathlib.Path(tmp), ("rho_patch",), ()))

    def test_a_missing_file_is_not_run_never_an_empty_list(self):
        write_records(self.dev, sweeps=False)
        code, _ = self.main(ARGV)
        self.assertEqual(code, 0)
        summary = strict((self.dev / "eval-summary.json").read_text())
        sweeps = strict((self.dev / "eval-sweeps-summary.json").read_text())
        self.assertEqual(summary["gate_world"], "not run")
        for k in ("eta", "match", "drift_visible", "budget_EXPLORATORY"):
            self.assertEqual(sweeps[k], "not run")
        self.assertEqual(summary["run"]["records_read"]["sweep-eta.jsonl"], "not run")


class TestRunSafety(_Tmp):
    def refused(self, argv, header):
        """main() on the eval split with every stage stubbed to fail: it must refuse first."""
        stub = mock.Mock(side_effect=AssertionError("simulated or summarised"))
        with mock.patch.object(rde.freeze, "header_line", return_value=header), \
                mock.patch.object(rde, "simulate", stub), mock.patch.object(rde, "run", stub), \
                mock.patch.object(rde, "summarise", stub):
            code, stdout = self.main(argv)
        self.assertNotEqual(code, 0)
        self.assertIn("refused (D33)", stdout)
        stub.assert_not_called()
        self.assertFalse(rde.OUT.exists())

    def test_eval_refuses_a_drifted_freeze(self):
        self.refused(["--split", "eval"], "freeze: DRIFTED from sha256:c789fa7362e0 in 1 place(s): "
                                          "source/sentinel.py: changed")

    def test_eval_refuses_a_pin_conflict(self):
        self.refused(["--split", "eval", "--summarise-only"],
                     "freeze: clean sha256:c789fa7362e0  |  PIN CONFLICT: pins/gate2_v2: live a != declared b")

    def test_eval_refuses_a_grid_without_the_reference_rho(self):
        self.refused(["--split", "eval", "--rhos", "0.5", "1"], "freeze: clean sha256:c789fa7362e0")

    def test_summarise_refuses_eval_on_a_freeze_that_drifted_mid_run(self):
        with mock.patch.object(rde.freeze, "header_line", return_value="freeze: DRIFTED from sha256:x"):
            with self.assertRaises(rde.Refused):
                rde.summarise({"split": "eval", "seeds": [1], "deltas": [0], "rhos": [RHO],
                               "skip_br": True, "skip_sweeps": True})
        self.assertFalse(rde.OUT.exists())

    def test_split_has_no_default(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            rde.main(["--jobs", "1"])
        self.assertEqual(cm.exception.code, 2)


class TestDenominators(unittest.TestCase):
    def test_every_pair_is_used_or_dropped_for_a_reason(self):
        den = rde.denominators({"split": "dev", "seeds": [1, 2], "deltas": [0, 8],
                                "skip_br": False, "skip_sweeps": True})
        n = den["workflows"] * 2
        for c in den["main"]["columns"].values():
            self.assertEqual(c["pairs"], n)
            self.assertEqual(c["infeasible"] + c["non_surviving"] + c["used"], n)
        self.assertGreater(den["main"]["columns"]["memory-first-write-e0.6@8"]["infeasible"], 0)
        self.assertEqual(den["main"]["columns"]["memory-first-write-e0.6@0"]["infeasible"], 0)
        self.assertEqual(den["sweeps"], "not run")
        for d in ("0", "8"):
            self.assertLessEqual(den["br"][d]["survived"], den["br"][d]["tried"])


if __name__ == "__main__":
    unittest.main()
