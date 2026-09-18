"""
test_p2_arms.py -- Gate 1 tests for P2 three-arm coordination and readout logic.
"""
import pathlib
import tempfile
import unittest

from spikes import p2_arms


class TestP2Arms(unittest.TestCase):
    def test_empty_store_has_no_items(self):
        store = p2_arms.empty_store()
        self.assertEqual(len(store.live()), 0)

    def test_summarize_arm_rows(self):
        rows = [
            {"mode": "A", "instance_id": "i1", "tokens_in": 100, "tokens_out": 20},
            {"mode": "A", "instance_id": "i2", "tokens_in": 200, "tokens_out": 30},
            {"mode": "REFUSED", "instance_id": "i3", "tokens_in": 50, "tokens_out": 10},
            {"mode": "VACUOUS_ANCHOR", "instance_id": "i4", "tokens_in": 150, "tokens_out": 25},
            {"type": "summary", "model": "test"},
        ]
        s = p2_arms.summarize_arm_rows(rows, arm_name="test_arm", model_name="test_model")
        self.assertEqual(s.instances, 4)
        self.assertEqual(s.classified, 2)
        self.assertEqual(s.refused, 1)
        self.assertEqual(s.vacuous_anchor, 1)
        self.assertEqual(s.patch_produced, 3)
        self.assertAlmostEqual(s.patch_rate, 0.75)
        self.assertEqual(s.adopted, 0)
        self.assertAlmostEqual(s.adoption_rate, 0.0)
        self.assertEqual(s.tokens_in, 500)
        self.assertEqual(s.tokens_out, 85)

    def test_compare_arms_delta(self):
        main_rows = [
            {"mode": "A", "instance_id": "i1"},
            {"mode": "REFUSED", "instance_id": "i2"},
        ]  # patch_rate = 1/2 = 0.5
        ctrl_rows = [
            {"mode": "A", "instance_id": "i1"},
            {"mode": "A", "instance_id": "i2"},
        ]  # patch_rate = 2/2 = 1.0
        cmp_res = p2_arms.compare_arms(main_rows, control_rows=ctrl_rows)
        self.assertIsNotNone(cmp_res["delta_patch_rate"])
        self.assertAlmostEqual(cmp_res["delta_patch_rate"], 0.5)

    def test_hypothesis_i_length_bottleneck(self):
        main_rows = [{"mode": "A", "instance_id": "i1"}]  # adopted = 0
        ceil_rows = [{"mode": "B", "instance_id": "i1"}]  # adopted = 1
        cmp_res = p2_arms.compare_arms(main_rows, ceiling_rows=ceil_rows)
        readout = cmp_res["readout"]
        self.assertEqual(readout["hypothesis"], p2_arms.HYPOTHESIS_LENGTH_BOTTLENECK)
        self.assertEqual(readout["code"], "(i)")
        self.assertEqual(readout["section"], "Model section")

    def test_hypothesis_ii_memory_ignored(self):
        # High patch rate (e.g. 50%), but 0 adoptions
        main_rows = [
            {"mode": "A", "instance_id": f"i{k}"} for k in range(5)
        ] + [
            {"mode": "REFUSED", "instance_id": f"r{k}"} for k in range(5)
        ]
        ceil_rows = [
            {"mode": "A", "instance_id": f"c{k}"} for k in range(3)
        ]
        cmp_res = p2_arms.compare_arms(main_rows, ceiling_rows=ceil_rows)
        readout = cmp_res["readout"]
        self.assertEqual(readout["hypothesis"], p2_arms.HYPOTHESIS_MEMORY_IGNORED)
        self.assertEqual(readout["code"], "(ii)")
        self.assertIn("Threats", readout["section"])

    def test_hypothesis_iii_task_unsolved(self):
        # Low patch rate (< 20%)
        main_rows = [
            {"mode": "REFUSED", "instance_id": f"r{k}"} for k in range(10)
        ] + [
            {"mode": "A", "instance_id": "i1"}
        ]  # 1/11 = 9.1%
        ctrl_rows = [
            {"mode": "REFUSED", "instance_id": f"r{k}"} for k in range(10)
        ]
        cmp_res = p2_arms.compare_arms(main_rows, control_rows=ctrl_rows)
        readout = cmp_res["readout"]
        self.assertEqual(readout["hypothesis"], p2_arms.HYPOTHESIS_TASK_UNSOLVED)
        self.assertEqual(readout["code"], "(iii)")
        self.assertEqual(readout["section"], "Limitations")

    def test_render_markdown_report_contains_table_and_readout(self):
        main_rows = [
            {"mode": "A", "instance_id": "i1", "tokens_in": 100, "tokens_out": 20, "proxy": True, "hidden": True, "patch": "diff", "tier": "high"},
            {"mode": "REFUSED", "instance_id": "i2", "tokens_in": 50, "tokens_out": 10, "proxy": None, "hidden": None, "patch": "", "tier": "low", "reason": "empty"},
        ]
        cmp_res = p2_arms.compare_arms(main_rows)
        cmp_res["main_rows"] = main_rows
        md = p2_arms.render_markdown_report(cmp_res)
        self.assertIn("# P2 — Báo Cáo Ba Arm", md)
        self.assertIn("| Arm | Model | Mục đích |", md)
        self.assertIn("### Phán quyết:", md)


if __name__ == "__main__":
    unittest.main()
