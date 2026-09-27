"""v3 leaves v2 alone (plan S2, R13).  Infrastructure: no DCM row.

v3 imports the v2 modules and never patches them.  The claim is checked the way a v2 run
checks it: through `costs.install(policies)` first, exactly as every v2 run does, then the
v2 freeze line and the D35 addendum's line.  Run from auditgame/.
"""
import pathlib
import unittest

import costs
import freeze
import freeze_d35
import policies as P

V2_FREEZE = "freeze: clean sha256:c789fa7362e0"


class TestInfraV2Intact(unittest.TestCase):
    def test_v3_leaves_v2_freeze_clean(self):
        """freeze.header_line() after costs.install(P) reads 'freeze: clean
        sha256:c789fa7362e0' with no PIN CONFLICT, freeze_d35.clean(...) holds, and no v3
        file is in the v2 freeze's cell (freeze.SOURCE, freeze.TABLES, freeze_d35.FILES)."""
        old = costs.install(P)
        try:
            base = freeze.header_line()
            d35 = freeze_d35.header_line()
        finally:
            costs.restore(P, old)
        self.assertEqual(base, V2_FREEZE, f"the v2 freeze moved: {base}")
        self.assertNotIn("PIN CONFLICT", base)
        self.assertTrue(freeze_d35.clean(d35), f"the D35 freeze moved: {d35}")

        cell = tuple(freeze.SOURCE) + tuple(freeze.TABLES) + tuple(freeze_d35.FILES)
        v3_in_cell = [f for f in cell if f.startswith("v3/") or "/v3" in f
                      or pathlib.PurePosixPath(f).name.startswith("v3_")]
        self.assertEqual(v3_in_cell, [], "a v3 file entered the v2 freeze's cell")


if __name__ == "__main__":
    unittest.main()
