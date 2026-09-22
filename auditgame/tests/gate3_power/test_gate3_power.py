"""
GATE 3 -- STRONG ENOUGH: "is there enough signal to conclude?"

Red here means the numbers are REAL and MEANINGFUL, but the 15% gate cannot yet
be claimed.

Naming convention (see PLAN-Thi-Hanh.md, section "Ngon ngu"): test names are
English; the thesis sentence each test defends lives in the docstring under a
mandatory `Thesis claim (vi):` line.  That keeps the property SS4 of
docs/thesis/eval/Thiet-ke-Framework-Test.md paid a lot for -- when a test goes red you can read
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

    def test_printed_table_has_all_four_lines_AND_the_CI(self):
        """Those four lines pre-answer the first four questions a reviewer asks.  A
        bare number without them FORCES THE READER TO TRUST US.

        The expected substrings must match metrics.report_header, which emits the
        English words `config` / `feasible` / `survived`.

        Thesis claim (vi): "cong 3 cuong che bang DINH DANG, khong bang assertion".
        """
        import metrics
        table = metrics.results_table(
            {"B1 audit-at-commit": {"harm": 0.80, "per_wf": [1.0, 1.0, 0.0, 1.0]},
             "Sentinel":           {"harm": 0.50, "per_wf": [1.0, 0.0, 0.0, 1.0]}},
            config_sha="a" * 64, n_feasible=38, n_total=40, n_survived=26)
        for line in ("sha256", "feasible", "survived", "d-harm", "CI95"):
            self.assertIn(line, table, f"table is missing: {line}")


class ConfigHash(unittest.TestCase):

    def test_config_sha_moves_when_theta_moves(self):
        """The hash-cell requirement (Global Constraints, "Gia phai tra" #2)
        names theta by name.  Nothing enforced that theta actually reaches the
        digest -- this is that enforcement.

        Thesis claim (vi): "khoa vao cung o hash voi pi_0 / phep gop / tau_sel / theta / scope()".
        """
        import metrics
        a = metrics.config_sha(pi0=0.10, aggregation="mean_lambda",
                               tau_sel=1, theta=0.50, scope="graded")
        b = metrics.config_sha(pi0=0.10, aggregation="mean_lambda",
                               tau_sel=1, theta=0.75, scope="graded")
        self.assertNotEqual(a, b, "config_sha did not move when theta changed")

    def test_config_sha_is_stable_for_the_same_inputs(self):
        """A hash that is not REPRODUCIBLE is not a hash-freeze -- see the
        core.seed_of / hash() ban this project already carries.

        Thesis claim (vi): "hash cau hinh phai TAI TAO DUOC tu cung dau vao".
        """
        import metrics
        a = metrics.config_sha(pi0=0.10, aggregation="mean_lambda",
                               tau_sel=1, theta=0.50, scope="graded")
        b = metrics.config_sha(pi0=0.10, aggregation="mean_lambda",
                               tau_sel=1, theta=0.50, scope="graded")
        self.assertEqual(a, b, "config_sha is not deterministic for identical inputs")


if __name__ == "__main__":
    unittest.main()
