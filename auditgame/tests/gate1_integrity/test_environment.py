"""
GATE 1 -- the environment.  Spec: eval/PLAN.md, Part II "Ranh gioi phu thuoc".

Loosening dependencies for the ANALYSIS tier is a win.  But if that leak reaches
the MEASUREMENT CORE, the benchmark stops being clone-and-run -- the property
Thiet-ke-Framework-Test.md SS4 gives up a lot to keep.
"""
from __future__ import annotations
import pathlib, subprocess, sys, unittest

#: Modules that must import with site-packages stripped.  `replay` is NOT here:
#: it is created in Task 5, and listing it now makes Step 0.5 fail with
#: ModuleNotFoundError -- red for the wrong reason, which the TDD cycle treats as
#: "fix the error and re-run", not as a passing gate.  Step 5.5 adds it.
CORE_MODULES = ("core", "detector", "scoring", "policies", "runner", "oracle",
                "metrics", "retrieval", "attacks", "datasets", "agents")


class Environment(unittest.TestCase):

    def test_core_modules_import_without_site_packages(self):
        """Import every core module with site-packages stripped from sys.path.

        Thesis claim (vi): ABC T.6 -- "nguoi khac git clone roi chay duoc ngay".
        """
        root = pathlib.Path(__file__).resolve().parents[2]
        code = ("import sys\n"
                "sys.path = [p for p in sys.path if 'site-packages' not in p]\n"
                f"sys.path.insert(0, {str(root)!r})\n"
                f"import {', '.join(CORE_MODULES)}\n")
        r = subprocess.run([sys.executable, "-S", "-c", code],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         f"the measurement core leaked a non-stdlib dependency:\n{r.stderr[-600:]}")

    def test_lock_file_pins_exact_versions(self):
        """An unpinned lock makes the environment hash meaningless.

        Thesis claim (vi): "moi truong la MOT PHAN CUA KET QUA".
        """
        lock = pathlib.Path(__file__).resolve().parents[3] / "requirements.lock"
        self.assertTrue(lock.exists(), "requirements.lock is missing")
        lines = [l for l in lock.read_text().splitlines() if l.strip()]
        self.assertTrue(lines, "lock file is empty")
        for l in lines:
            self.assertIn("==", l, f"line is not pinned exactly: {l!r}")
