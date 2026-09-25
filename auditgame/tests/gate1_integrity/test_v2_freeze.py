"""GATE 1 -- the v2 freeze covers v2's code, tuned table, systems and splits."""
import pathlib
import tempfile
import unittest

import freeze

V2_SOURCE = ("draft_setup.py", "corpus_v2.py", "world_v2.py", "carrier_runner.py",
             "gate_world.py", "attackers_v2.py", "belief_v2.py", "carrier_policies.py",
             "sentinel.py", "metrics_v2.py")


class TestFreezeV2(unittest.TestCase):
    def test_manifest_lists_v2(self):
        m = freeze.manifest()
        for f in V2_SOURCE:
            self.assertIn(f, m["source"])
        self.assertIn("reference/v2_tuned.json", m["tables"])
        self.assertIn("Sentinel-A1", m["policies_v2"])
        self.assertEqual(len(m["policy_library_v2"]), 28)
        self.assertEqual(len(m["held_out_attackers_v2"]), 7)
        self.assertTrue(m["tuning_attackers_v2"])
        self.assertEqual(m["dev_repos_v2"], ["django/django"])

    def test_require_frozen_knows_the_v2_systems(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "MANIFEST.json"
            freeze.write(path)
            freeze.require_frozen("Sentinel-A1", path)
            freeze.require_frozen("L-RO-c3-p1-d3", path)
            with self.assertRaises(freeze.NotFrozen):
                freeze.require_frozen("Sentinel-A2", path)


if __name__ == "__main__":
    unittest.main()
