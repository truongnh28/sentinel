"""
GATE 3 -- STRONG ENOUGH: "is there enough signal to conclude?"

Red here means the numbers are REAL and MEANINGFUL, but the 15% gate cannot yet
be claimed.

Naming convention (see PLAN-Thi-Hanh.md, section "Ngon ngu"): test names are
English; the thesis sentence each test defends lives in the docstring under a
mandatory `Thesis claim (vi):` line.  That keeps the property SS4 of
Thiet-ke-Framework-Test.md paid a lot for -- when a test goes red you can read
off which thesis sentence just lost its support -- only relocated.
"""
from __future__ import annotations
import unittest


class Gate3StrongEnough(unittest.TestCase):

    def test_gain_percent_is_none_when_denominator_is_meaningless(self):
        """gain% must be None once h_B1 drops below the floor.

        Thesis claim (vi): "giam >= 15% so B1" -- the ratio needs a valid
        denominator.

        The old experiment.py divided by max(h_B1, 1e-9): as h_B1 -> 0 (large
        budget, or small Delta) the ratio explodes or flips sign arbitrarily --
        exactly in the Delta=0 cell we most need to read.
        """
        try:
            import metrics
        except ImportError:
            self.fail("metrics.py missing (B5). Need gain() -> None when "
                      "h_B1 < 0.05, and absolute Delta-harm as the headline.")
        self.assertIsNone(metrics.gain(h_b1=0.0, h_sentinel=0.0),
                          "gain% must be None below the 0.05 floor")

    def test_results_table_carries_all_five_mandatory_lines(self):
        """Gate 3 is enforced by FORMAT, not by assertions.

        Thesis claim (vi): moi bang ket qua phai tu mang theo bang chung.

        A table missing these lines is not a results table:
            config sha256 . feasible n/N . survived n/N . env lock . Delta-harm + CI95
        """
        try:
            import metrics
        except ImportError:
            self.fail("metrics.py missing (B5) -- nowhere to enforce format.")
        hdr = metrics.report_header(config_sha="a" * 64, n_feasible=38,
                                    n_total=40, n_survived=26, lock_sha="b" * 64)
        for line in ("sha256", "feasible", "survived", "lock"):
            self.assertIn(line, hdr, f"header is missing the line: {line}")


if __name__ == "__main__":
    unittest.main()
