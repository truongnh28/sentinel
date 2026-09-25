"""D35 freeze and run tool (freeze_d35.py, tools/run_d35.py); no eval data is read.
Run from auditgame/: ../.venv/bin/python -m unittest tests.tools.test_d35_run -v"""
import json
import pathlib
import tempfile
import unittest

import addendum_d35 as X
import freeze_d35 as F
from tools import run_d35 as RD


class TestFreezeD35(unittest.TestCase):
    def test_manifest_pins_the_base_the_files_and_the_names(self):
        man = F.manifest()
        self.assertEqual(man["base_digest"][:12], "c789fa7362e0")
        self.assertEqual(set(man["files"]), {"addendum_d35.py", "reference/d35_tuned.json"})
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


class TestRefusal(unittest.TestCase):
    def test_eval_needs_a_clean_d35_freeze(self):
        with tempfile.TemporaryDirectory() as d:
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
            (pathlib.Path(d) / RD.MAIN).write_text("{}\n")
            clean = "freeze-d35: clean sha256:a  |  base freeze: clean sha256:c"
            self.assertIn("runs once", RD.refusal("eval", clean, pathlib.Path(d), False))
            self.assertIsNone(RD.refusal("eval", clean, pathlib.Path(d), True))


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


class TestReadings(unittest.TestCase):
    def rows(self, swap_lo=0.1, down1_lo=0.1, b2_lo=0.1, fixed_lo=0.1, vbr_fixed=0.5):
        out = {}
        for rk in ("0", "0.25", "0.5", "1"):
            out[rk] = {"Sentinel-A1": {"v_br": 0.4},
                       "A1 dhat-swap": {"vs_b1": _ci(swap_lo if rk != "1" else -0.1)},
                       "A1 dhat-down1": {"vs_b1": _ci(down1_lo if rk != "1" else -0.1)},
                       "A1 dhat-down2": {"vs_b1": _ci(-0.2)},
                       X.B2_FQ: {"vs_sentinel": _ci(b2_lo)},
                       X.FIXED: {"vs_sentinel": _ci(fixed_lo), "v_br": vbr_fixed}}
        return out

    def test_a_uses_rho_up_to_half_and_both_one_step_arms(self):
        self.assertTrue(RD.readings(self.rows())["A_oracle_survives_one_step"])
        self.assertFalse(RD.readings(self.rows(down1_lo=-0.01))["A_oracle_survives_one_step"])

    def test_b_and_c_per_rho(self):
        r = RD.readings(self.rows(b2_lo=-0.01, fixed_lo=0.02, vbr_fixed=0.3))
        self.assertEqual(r["B_beats_fq_matched_mix"], {"0": False, "0.25": False, "0.5": False, "1": False})
        self.assertTrue(all(r["C_scripted_gain_attributable_to_randomisation"].values()))
        self.assertFalse(any(r["C_br_fixed_above_sentinel"].values()))


if __name__ == "__main__":
    unittest.main()
