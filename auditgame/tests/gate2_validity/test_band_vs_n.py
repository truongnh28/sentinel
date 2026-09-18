"""
test_band_vs_n.py -- Tests for the noise band vs n curve (Task A3).

Verifies that:
1. band_width refuses families smaller than MIN_SALTS (3).
2. The band width narrows as n grows.
3. resolving_n raises Unresolved when no tested n resolves the ceiling.
"""
from __future__ import annotations
import unittest

from analysis import band_vs_n, gate2_v2

SALTS = list(gate2_v2.SALT_FAMILY)


class TestBandVsN(unittest.TestCase):
    def test_a_single_salt_is_refused(self):
        """A band is a spread over the salt family. One salt has no spread, and a
        zero-width 'band' read as a resolution claim is the defect this exists to expose."""
        with self.assertRaises(ValueError):
            band_vs_n.band_width(400, SALTS[:1])

    def test_two_salts_are_refused(self):
        """MIN_SALTS is 3: two salts cannot establish a robust spread."""
        with self.assertRaises(ValueError):
            band_vs_n.band_width(400, SALTS[:2])

    def test_the_band_narrows_as_n_grows(self):
        """The whole claim rests on this being monotone in the large: if the band does
        not narrow with n, the curve says nothing about how much corpus a gate needs."""
        curve = band_vs_n.band_curve((100, 400, 900), SALTS[:5])
        widths = [w for _, w in curve]
        self.assertLess(widths[-1], widths[0])

    def test_unresolved_exception_carries_context(self):
        """When resolving_n fails to resolve, Unresolved carries the largest n tried."""
        with self.assertRaises(band_vs_n.Unresolved) as ctx:
            band_vs_n.resolving_n((200,), SALTS[:3], ceiling=0.557)
        self.assertIn("no n up to 200", str(ctx.exception))
