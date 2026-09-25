"""D35 freeze and run tool (freeze_d35.py, tools/run_d35.py); no eval data is read.
Run from auditgame/: ../.venv/bin/python -m unittest tests.tools.test_d35_run -v"""
import json
import pathlib
import tempfile
import unittest

import addendum_d35 as X
import attackers_v2 as A
import draft_setup as D
import freeze_d35 as F
import sentinel as S
from tools import run_d35 as RD
from tools import run_draft_eval


class TestFreezeD35(unittest.TestCase):
    def test_manifest_pins_the_base_the_files_and_the_names(self):
        man = F.manifest()
        self.assertEqual(man["base_digest"][:12], "c789fa7362e0")
        self.assertEqual(set(man["files"]),
                         {"addendum_d35.py", "reference/d35_tuned.json", "tools/run_d35.py"})
        self.assertEqual(man["arms"], sorted(X.ARMS))
        self.assertEqual(len(man["fixed_library"]), 11)
        self.assertEqual(man["dhat"]["A1 dhat-swap"], {"4": 8, "8": 4})
        self.assertEqual(man["p_grid"], list(X.P_GRID))

    def test_write_then_no_drift_then_tamper_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "MANIFEST-D35.json"
            dig = F.write(path)
            self.assertEqual(len(dig), 64)
            self.assertEqual(F.drift(path), [])
            man = json.loads(path.read_text())
            man["files"]["addendum_d35.py"] = "0" * 64
            man["p_grid"] = [0.5]
            path.write_text(json.dumps(man))
            got = F.drift(path)
            self.assertIn("files/addendum_d35.py: changed", got)
            self.assertIn("p_grid: changed", got)

    def test_missing_manifest(self):
        self.assertEqual(F.drift(pathlib.Path("/nonexistent/M.json")),
                         ["no D35 manifest: nothing has been frozen"])

    def test_clean_needs_both_freezes_clean(self):
        ok = "freeze-d35: clean sha256:abc  |  base freeze: clean sha256:c789fa7362e0"
        self.assertTrue(F.clean(ok))
        self.assertFalse(F.clean("freeze-d35: NONE  |  base freeze: clean sha256:c789fa7362e0"))
        self.assertFalse(F.clean("freeze-d35: clean sha256:abc  |  base freeze: DRIFTED from x"))
        self.assertFalse(F.clean(ok + "  |  PIN CONFLICT: x"))


def _complete_main_summary() -> dict:
    """A fake spikes/v2/eval-summary.json shape, complete enough for RD.refusal's F4 pre-flight
    check and RD.reproduces: every rho of the grid, both B1 and Sentinel-A1."""
    return {"by_rho": {f"{rho:g}": {"table2": {
                RD.B1: {"worst_case_harm": 0.9}, RD.SA1: {"worst_case_harm": 0.1}}}
            for rho in D.RHO_PATCH_GRID}}


class TestRefusal(unittest.TestCase):
    def _patch_main_summary(self, path):
        old = RD.MAIN_SUMMARY
        RD.MAIN_SUMMARY = path
        self.addCleanup(lambda: setattr(RD, "MAIN_SUMMARY", old))

    def test_eval_needs_a_clean_d35_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            fake = pathlib.Path(d) / "main-summary.json"
            fake.write_text(json.dumps(_complete_main_summary()))
            self._patch_main_summary(fake)
            self.assertIsNotNone(RD.refusal("eval", "freeze-d35: NONE  |  base freeze: clean",
                                            pathlib.Path(d), False))
            self.assertIsNone(RD.refusal(
                "eval", "freeze-d35: clean sha256:a  |  base freeze: clean sha256:c", pathlib.Path(d), False))

    def test_dev_runs_before_the_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(RD.refusal("dev", "freeze-d35: NONE  |  base freeze: clean",
                                         pathlib.Path(d), False))

    def test_the_addendum_runs_once(self):
        with tempfile.TemporaryDirectory() as d:
            fake = pathlib.Path(d) / "main-summary.json"
            fake.write_text(json.dumps(_complete_main_summary()))
            self._patch_main_summary(fake)
            (pathlib.Path(d) / RD.MAIN).write_text("{}\n")
            clean = "freeze-d35: clean sha256:a  |  base freeze: clean sha256:c"
            self.assertIn("runs once", RD.refusal("eval", clean, pathlib.Path(d), False))
            self.assertIsNone(RD.refusal("eval", clean, pathlib.Path(d), True))

    def test_eval_preflight_needs_a_complete_main_summary(self):
        clean = "freeze-d35: clean sha256:a  |  base freeze: clean sha256:c"
        with tempfile.TemporaryDirectory() as d:
            missing = pathlib.Path(d) / "no-such-main-summary.json"
            self._patch_main_summary(missing)
            why = RD.refusal("eval", clean, pathlib.Path(d), False)
            self.assertIsNotNone(why)
            self.assertIn("main summary", why)

    def test_eval_preflight_passes_a_complete_main_summary(self):
        clean = "freeze-d35: clean sha256:a  |  base freeze: clean sha256:c"
        with tempfile.TemporaryDirectory() as d:
            fake = pathlib.Path(d) / "main-summary.json"
            fake.write_text(json.dumps(_complete_main_summary()))
            self._patch_main_summary(fake)
            self.assertIsNone(RD.refusal("eval", clean, pathlib.Path(d), False))


class TestReproduction(unittest.TestCase):
    MAIN = {"table2": {"B1 audit-at-commit": {"worst_case_harm": 0.79813797},
                       "Sentinel-A1": {"worst_case_harm": 0.40543650}}}

    def test_equal_to_four_decimals_passes(self):
        self.assertEqual(RD.reproduces(0.79814, 0.405436, self.MAIN), [])

    def test_a_difference_is_named(self):
        got = RD.reproduces(0.79814, 0.4061, self.MAIN)
        self.assertEqual(len(got), 1)
        self.assertIn("Sentinel-A1", got[0])


def _ci(lo):
    return {"abs_lo": lo, "abs_hi": lo + 0.1, "abs_diff": lo + 0.05}


def _rows(swap_lo=0.1, down1_lo=0.1, b2_lo=0.1, fixed_lo=0.1, vbr_fixed=0.5, vbr_sa1=0.4):
    out = {}
    for rk in ("0", "0.25", "0.5", "1"):
        out[rk] = {"Sentinel-A1": {"v_br": vbr_sa1},
                   "A1 dhat-swap": {"vs_b1": _ci(swap_lo if rk != "1" else -0.1)},
                   "A1 dhat-down1": {"vs_b1": _ci(down1_lo if rk != "1" else -0.1)},
                   "A1 dhat-down2": {"vs_b1": _ci(-0.2)},
                   X.B2_FQ: {"vs_sentinel": _ci(b2_lo)},
                   X.FIXED: {"vs_sentinel": _ci(fixed_lo), "v_br": vbr_fixed}}
    return out


class TestReadings(unittest.TestCase):
    def test_a_uses_rho_up_to_half_and_both_one_step_arms(self):
        self.assertTrue(RD.readings(_rows())["A_oracle_survives_one_step"])
        self.assertFalse(RD.readings(_rows(down1_lo=-0.01))["A_oracle_survives_one_step"])

    def test_b_and_c_per_rho(self):
        r = RD.readings(_rows(b2_lo=-0.01, fixed_lo=0.02, vbr_fixed=0.3))
        self.assertEqual(r["B_beats_fq_matched_mix"], {"0": False, "0.25": False, "0.5": False, "1": False})
        self.assertTrue(all(r["C_fixed_worse_than_sentinel"].values()))
        self.assertFalse(any(r["C_br_fixed_above_sentinel"].values()))


class TestReadingsMissingEvidence(unittest.TestCase):
    """F2: a NaN or missing input to a reading comparison must yield None, never False."""

    def test_nan_abs_lo_gives_none_for_a(self):
        r = RD.readings(_rows(swap_lo=float("nan")))
        self.assertIsNone(r["A_by_arm"]["A1 dhat-swap"])
        self.assertIsNone(r["A_oracle_survives_one_step"])
        self.assertIsNotNone(r["A_by_arm"]["A1 dhat-down1"])

    def test_nan_abs_lo_gives_none_for_b_and_c(self):
        r = RD.readings(_rows(b2_lo=float("nan"), fixed_lo=float("nan")))
        self.assertTrue(all(v is None for v in r["B_beats_fq_matched_mix"].values()))
        self.assertTrue(all(v is None for v in r["C_fixed_worse_than_sentinel"].values()))

    def test_nan_v_br_gives_none_in_c_br_fixed_above_sentinel(self):
        r = RD.readings(_rows(vbr_fixed=float("nan")))
        self.assertTrue(all(v is None for v in r["C_br_fixed_above_sentinel"].values()))
        r2 = RD.readings(_rows(vbr_sa1=float("nan")))
        self.assertTrue(all(v is None for v in r2["C_br_fixed_above_sentinel"].values()))


# ---------------------------------------------------------------- synthetic summarise() runs

WFS = (("wf1", "repo1"), ("wf2", "repo2"))
#: B1 worst (0.9), the five arms in between-but-worse-than-B1 (0.95), Sentinel-A1 best (0.1):
#: vs_b1 = V(B1) - V(arm) is negative, vs_sentinel = V(arm) - V(Sentinel-A1) is positive, so
#: the two really differ in sign and the argument order (F6) is really tested.
HARM = {RD.B1: 0.9, RD.SA1: 0.1, "A1 dhat-swap": 0.95, "A1 dhat-down1": 0.95,
        "A1 dhat-down2": 0.95, X.B2_FQ: 0.95, X.FIXED: 0.95}
VBR = {RD.B1: 0.9, RD.SA1: 0.3, "A1 dhat-swap": 0.95, "A1 dhat-down1": 0.95,
       "A1 dhat-down2": 0.95, X.B2_FQ: 0.95, X.FIXED: 0.5}


def _main_rows(harm_of, attack, deltas=D.HEADLINE_DELTAS, rhos=D.RHO_PATCH_GRID, seeds=(1, 2),
              wfs=WFS, systems=RD.SYSTEMS):
    rows = []
    for p in systems:
        for d in deltas:
            for rho in rhos:
                for wf, repo in wfs:
                    for s in seeds:
                        rows.append({"policy": p, "attack": attack, "delta": d, "rho_patch": rho,
                                     "wf": wf, "repo": repo, "seed": s, "harm": harm_of[p],
                                     "detected_at": None, "iota": None, "n_solved": 1,
                                     "t_lost": 0, "false_removed": 0, "benign_inspected": 1})
    return rows


def _br_rows(vbr_of, deltas=D.HEADLINE_DELTAS, rhos=D.RHO_PATCH_GRID, systems=RD.SYSTEMS):
    return [{"policy": p, "delta": d, "rho_patch": rho, "v_br": vbr_of[p],
             "v_br_naive": vbr_of[p], "n_workflows": len(WFS)}
            for p in systems for d in deltas for rho in rhos]


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


class TestSummariseDevComplete(unittest.TestCase):
    """F8(a)-(c): synthetic dev records, no eval data touched."""

    def _out_dir(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return pathlib.Path(d.name)

    def test_a_complete_run_produces_rows(self):
        out_dir = self._out_dir()
        attack = A.held_out()[0]
        _write_jsonl(out_dir / RD.MAIN, _main_rows(HARM, attack))
        _write_jsonl(out_dir / RD.BR, _br_rows(VBR))
        out = RD.summarise("dev", out_dir, {"split": "dev"})
        self.assertNotIn("withheld", out)
        self.assertEqual(set(out["rows"]), {f"{r:g}" for r in D.RHO_PATCH_GRID})

        row = out["rows"]["0"]["A1 dhat-swap"]
        vb, va, vs = HARM[RD.B1], HARM["A1 dhat-swap"], HARM[RD.SA1]
        self.assertEqual(row["vs_b1"]["abs_diff"], round(vb - va, 4))
        self.assertEqual(row["vs_sentinel"]["abs_diff"], round(va - vs, 4))
        self.assertLess(row["vs_b1"]["abs_diff"] * row["vs_sentinel"]["abs_diff"], 0)  # F6: opposite signs
        for key in ("gain", "lo", "hi", "rel_reliable", "v_base", "v_cand", "n_zero_base", "base_events"):
            self.assertNotIn(key, row["vs_sentinel"])
        self.assertIn("gain", row["vs_b1"])
        self.assertEqual(set(row["v_br_by_delta"]), {"4", "8"})
        self.assertEqual(row["v_br_nan_deltas"], [])

    def test_b_missing_system_at_one_rho_is_withheld(self):
        out_dir = self._out_dir()
        attack = A.held_out()[0]
        rows = [r for r in _main_rows(HARM, attack)
                if not (r["policy"] == "A1 dhat-swap" and r["rho_patch"] == 0.0)]
        _write_jsonl(out_dir / RD.MAIN, rows)
        _write_jsonl(out_dir / RD.BR, _br_rows(VBR))
        out = RD.summarise("dev", out_dir, {"split": "dev"})
        self.assertIn("withheld", out)
        self.assertIn("incomplete", out["withheld"])

    def test_c_missing_br_row_is_withheld(self):
        out_dir = self._out_dir()
        attack = A.held_out()[0]
        _write_jsonl(out_dir / RD.MAIN, _main_rows(HARM, attack))
        br = _br_rows(VBR)
        del br[0]
        _write_jsonl(out_dir / RD.BR, br)
        out = RD.summarise("dev", out_dir, {"split": "dev"})
        self.assertIn("withheld", out)
        self.assertIn("incomplete", out["withheld"])


class TestSummariseEvalReproduction(unittest.TestCase):
    """F8(d): summarise("eval", ...) with RD.MAIN_SUMMARY patched to a temp file; no real eval
    data is ever read."""

    def _patch_main_summary(self, path):
        old = RD.MAIN_SUMMARY
        RD.MAIN_SUMMARY = path
        self.addCleanup(lambda: setattr(RD, "MAIN_SUMMARY", old))

    def _prepare(self, out_dir):
        attack = A.held_out()[0]
        _write_jsonl(out_dir / RD.MAIN, _main_rows(HARM, attack))
        _write_jsonl(out_dir / RD.BR, _br_rows(VBR))
        RD.pin(out_dir, [RD.MAIN, RD.BR])

    def test_a_mismatch_in_the_4th_decimal_is_withheld_as_does_not_reproduce(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = pathlib.Path(d)
            self._prepare(out_dir)
            fake = {"by_rho": {f"{rho:g}": {"table2": {
                        RD.B1: {"worst_case_harm": HARM[RD.B1] + (0.0005 if rho == 0.0 else 0.0)},
                        RD.SA1: {"worst_case_harm": HARM[RD.SA1]}}}
                    for rho in D.RHO_PATCH_GRID}}
            fake_path = out_dir / "fake-main-summary.json"
            fake_path.write_text(json.dumps(fake))
            self._patch_main_summary(fake_path)
            out = RD.summarise("eval", out_dir, {"split": "eval"})
            self.assertIn("withheld", out)
            self.assertIn("does not reproduce", out["withheld"])

    def test_b_a_matching_main_summary_and_pin_is_not_withheld(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = pathlib.Path(d)
            self._prepare(out_dir)
            fake = {"by_rho": {f"{rho:g}": {"table2": {
                        RD.B1: {"worst_case_harm": HARM[RD.B1]},
                        RD.SA1: {"worst_case_harm": HARM[RD.SA1]}}}
                    for rho in D.RHO_PATCH_GRID}}
            fake_path = out_dir / "fake-main-summary.json"
            fake_path.write_text(json.dumps(fake))
            self._patch_main_summary(fake_path)
            out = RD.summarise("eval", out_dir, {"split": "eval"})
            self.assertNotIn("withheld", out)
            self.assertEqual(set(out["rows"]), {f"{r:g}" for r in D.RHO_PATCH_GRID})


class TestDevFidelity(unittest.TestCase):
    """F8(g): RD.work must still reproduce tools.run_draft_eval.work bit for bit on the shared
    fields, for a plain (non-addendum) system, on the dev split, one small job."""
    SHARED = ("harm", "false_removed", "benign_inspected", "t_lost", "wf", "seed")

    def _compare(self, policy):
        attack = A.held_out()[0]
        tuned = S.load_tuned()
        got_d35 = RD.work(((policy, attack, 8, 0.25), tuned, {}, (1,), "dev"))
        got_main = run_draft_eval.work((run_draft_eval.Job(policy, attack, 8, "mid", 0.25),
                                        tuned, (1,), "dev"))
        self.assertTrue(got_d35)
        self.assertEqual(len(got_d35), len(got_main))
        for a, b in zip(got_d35, got_main):
            for f in self.SHARED:
                self.assertEqual(a[f], b[f], f"{policy}/{f}: {a[f]!r} != {b[f]!r}")

    def test_b1_matches_run_draft_eval(self):
        self._compare("B1 audit-at-commit")

    def test_sentinel_a1_matches_run_draft_eval(self):
        self._compare("Sentinel-A1")


if __name__ == "__main__":
    unittest.main()
