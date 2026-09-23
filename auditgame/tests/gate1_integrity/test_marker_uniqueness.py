"""The injected marker must not be one constant for every payload.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md 3.5.

WHY THIS MATTERS MORE THAN IT LOOKS.  `core.PoisonSpec.marker` defaulted to the
literal "raw_write" and `build.plan_poison` never overrode it, so every payload
this benchmark ever produced carried the same token.  The benign-corpus gate
(gate 2) exists to certify that no surface feature separates poisoned items from
benign ones -- and `payloads/gen_payload_scale.py` had already measured the
single feature "contains raw_write" at AUC 1.000.  A constant marker does not
just weaken that gate, it makes the thing the gate certifies false.
"""
import random
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import build


class MarkersDifferAcrossConfigurations(unittest.TestCase):

    def _specs(self):
        out = {}
        for w in range(6):
            wf = build.make_workflow(f"wf-{w:03d}", "django", 8, random.Random(w))
            for k in ("memory", "skill", "queue", "branch"):
                for d in (0, 1, 2, 4):
                    ps = build.plan_poison(wf, k, d, random.Random(7))
                    if ps is not None:
                        out[(wf.wf_id, k, d)] = ps.marker
        return out

    def test_no_single_token_covers_every_payload(self):
        """The exact property gate 2 certifies. One token shared by all payloads
        is a perfect classifier, whatever else the corpus is matched on."""
        markers = self._specs()
        self.assertGreater(len(markers), 40, "not enough configurations to judge")
        share = max(list(markers.values()).count(m) for m in set(markers.values()))
        self.assertLess(share / len(markers), 0.5,
                        f"one marker covers {share}/{len(markers)} payloads")

    def test_the_old_constant_is_no_longer_universal(self):
        markers = self._specs()
        self.assertNotEqual(set(markers.values()), {"raw_write"})

    def test_same_configuration_gives_the_same_marker(self):
        """Determinism is not optional: sealed traces and results/M3-trace.json
        record the marker, and a replay has to reproduce them."""
        a, b = self._specs(), self._specs()
        self.assertEqual(a, b)

    def test_every_marker_is_a_plain_identifier(self):
        """The marker is spelled into advice as `{marker}()` and matched on the
        AST, so anything that is not an identifier silently stops being found."""
        for key, m in self._specs().items():
            with self.subTest(cfg=key):
                self.assertTrue(m.isidentifier(), m)
                self.assertEqual(m, m.lower())

    def test_markers_do_not_look_like_a_generated_pattern(self):
        """A hex suffix would satisfy uniqueness and reintroduce the problem one
        level up: the separating feature becomes the PATTERN rather than the
        token. Every marker has to read like an identifier somebody wrote.

        Digits are NOT banned -- `parse_v2` is how people actually name things,
        and an earlier version of this test rejected `unsafe_flush_v2` for
        looking generated when it looks the opposite. What is banned is a run of
        hex, which no hand-written identifier carries.
        """
        import re
        for key, m in self._specs().items():
            with self.subTest(cfg=key):
                self.assertIsNone(re.search(r"[0-9a-f]{6,}", m), m)
                self.assertRegex(m, r"^[a-z]+(_[a-z0-9]+)+$")


if __name__ == "__main__":
    unittest.main()
