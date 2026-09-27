"""P3 kappa measurement (v3/audit_checks.py, tools/v3_measure_kappa.py).  Infrastructure:
no DCM row (D7.kappa's own test stays test_s8_config).  Static: needs no repo clone, no
venv and no run, so it never skips.  Run from auditgame/."""
import json
import pathlib
import sys
import unittest

import draft_setup as D
from v3 import audit_checks as A
from v3 import config as C

ROOT = pathlib.Path(__file__).resolve().parents[2]            # auditgame/
sys.path.insert(0, str(ROOT / "tools"))
import v3_measure_kappa as M                                  # noqa: E402

DIFF = """diff --git a/pkg/mod.py b/pkg/mod.py
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -10,3 +10,3 @@ def target(x):
     a = 1
-    return x
+    return x + a
diff --git a/tests/test_mod.py b/tests/test_mod.py
"""


class TestInfraP3Kappa(unittest.TestCase):
    def test_checks_never_read_a_label(self):
        for f in (ROOT / "v3" / "audit_checks.py", ROOT / "tools" / "v3_measure_kappa.py"):
            self.assertNotIn("poisoned", f.read_text(encoding="utf-8"), f.name)

    def test_tool_refuses_a_non_dev_workflow(self):
        class W:
            wf_id = "v3e-001"
        with self.assertRaises(RuntimeError):
            M._dev_only([W()])

    def test_targets_map_to_the_draft_stages(self):
        self.assertEqual(A.STAGE_OF_TARGET, D.STAGE_OF_TARGET)
        self.assertEqual(M.TARGETS, tuple(C.TARGETS))
        self.assertEqual(M.CHI_CONFIGS, {k: tuple(v) for k, v in C.CHI_DEPTHS.items()})

    def test_diff_helpers(self):
        self.assertEqual(A.diff_files(DIFF), ["pkg/mod.py", "tests/test_mod.py"])
        (path, start, pre, ctx), = A.hunks(DIFF)
        self.assertEqual((path, start, pre), ("pkg/mod.py", 10, ["    a = 1", "    return x"]))
        self.assertIn("target", ctx)
        self.assertTrue(A.is_test_path("tests/test_mod.py"))
        self.assertFalse(A.is_test_path("pkg/mod.py"))
        # git's blob id of "hello\n"
        self.assertEqual(A.blob_id(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_chi_of_the_draft_table(self):
        chi = M.chi_of(dict(D.TARGET_KAPPA_DRAFT))
        self.assertAlmostEqual(chi["chi_range"], 2.114, places=3)
        self.assertAlmostEqual(chi["chi_2mad"], 1.343, places=3)

    def test_measured_values_are_not_wired_into_config(self):
        self.assertEqual(C.KAPPA_UNIT, D.TARGET_KAPPA_DRAFT)
        out = ROOT / "reference" / "v3_kappa_measured.json"
        if out.exists():
            self.assertFalse(json.loads(out.read_text())["wired_into_config"])


if __name__ == "__main__":
    unittest.main()
