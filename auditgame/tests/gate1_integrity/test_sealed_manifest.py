"""
GATE 1 -- the sealed manifest.  Spec: docs/thesis/eval/SPEC-AuditGame-SE.md.

The manifest is what the EVALUATOR knows and the SYSTEM does not.  A missing field
is not cosmetic: each one closes a specific "how do we know that" question, and
without it the answer reverts to "trust us".
"""
from __future__ import annotations
import inspect, unittest

import build


class SealedManifest(unittest.TestCase):

    REQUIRED = ("auc_match_ci", "n_c_at_sigma", "kappa_measured", "instance_source")

    def test_manifest_carries_all_four_evidence_fields(self):
        """Thesis claim (vi): "manifest niem phong du truong"."""
        sig = inspect.signature(build.sealed_manifest).parameters
        for f in self.REQUIRED:
            self.assertIn(f, sig, f"sealed_manifest is missing: {f}")
            self.assertIs(sig[f].default, inspect.Parameter.empty,
                          f"{f} has a default -- it would be silently omitted")

    def test_no_defense_can_reach_the_manifest(self):
        """Structural, not disciplinary: grep every policy's source for the symbol.

        The manifest holds `carrier`, `iota` and `sigma` -- reading it once gives a
        policy perfect knowledge and every allocation number becomes meaningless.

        Thesis claim (vi): "chinh sach khong biet dau la mam doc".
        """
        import policies as P
        for name, cls in P.REGISTRY.items():
            src = inspect.getsource(cls)
            for forbidden in ("sealed_manifest", "manifest", "PoisonSpec"):
                self.assertNotIn(forbidden, src, f"[{name}] reaches for {forbidden!r}")


if __name__ == "__main__":
    unittest.main()
