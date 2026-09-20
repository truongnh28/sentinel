"""GATE 1 -- prose_pool co dung tinh chat da tuyen bo khong.

Spec: TIEN-DANG-KY-Detector-Noi-Dung.md §3, §3.1.
Claim: corpus nay la VAN XUOI, cung the loai voi payload, khong mang khuon cu.
"""
from __future__ import annotations
import json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POOL = os.path.join(ROOT, "payloads", "prose_pool.jsonl")
OLD_TEMPLATE = re.compile(r"^\[[^\]]*\] (commit|ghi chú từ|lời gọi treo) \S+$")


def _load() -> list:
    with open(POOL, encoding="utf-8") as fh:
        return [json.loads(line)["content"] for line in fh if line.strip()]


class TestProsePool(unittest.TestCase):

    def test_exactly_2294_records(self):
        self.assertEqual(len(_load()), 2294)

    def test_no_record_carries_the_old_template(self):
        """Neu prompt ro khuon corpus vao van xuoi thi detector se doc khuon
        thay vi doc y do -- dung con confound ma corpus nay sinh ra de bit."""
        bad = [c for c in _load() if OLD_TEMPLATE.match(c)]
        self.assertEqual(bad, [], f"{len(bad)} ban ghi mang khuon cu")

    def test_no_exact_duplicates(self):
        rows = _load()
        self.assertEqual(len(set(rows)), len(rows))

    def test_file_order_is_deterministic(self):
        """offline-then-frozen: file phai tai lap duoc bat ke thu tu thread."""
        rows = _load()
        self.assertEqual(rows, sorted(rows))

    def test_provenance_pins_model_and_temperature(self):
        with open(os.path.join(ROOT, "payloads",
                               "prose-pool-provenance.json"), encoding="utf-8") as fh:
            prov = json.load(fh)
        for key in ("model", "model_version", "temperature",
                    "prompt_sha256", "n", "prose_pool_sha256"):
            self.assertIn(key, prov)
        self.assertEqual(prov["n"], 2294)
