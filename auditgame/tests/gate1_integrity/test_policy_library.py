"""The 28-policy class: it has to be a CLASS, not a bag of knob settings.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 6B, 6D.

A covering argument -- "no policy in the class does better" -- says nothing
unless the class spans reasonable defenders and contains the baselines it is
compared against. These tests pin the properties that claim rests on.
"""
import random
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import agent
import build
import detector
import experiment
import policies as P
import policies_library as L
import runner


class TheClassIsDeclaredNotDrawn(unittest.TestCase):

    def test_three_families_and_their_sizes(self):
        self.assertEqual(len(L.LIBRARY), 28)
        self.assertEqual({k: len(v) for k, v in L.FAMILIES.items()},
                         {"stage-weighted": 8, "belief-threshold": 12,
                          "carrier-rotation": 8})
        covered = set().union(*(set(v) for v in L.FAMILIES.values()))
        self.assertEqual(covered, set(L.LIBRARY))

    def test_the_baseline_is_inside_the_class(self):
        """B1 audits only at commit. If that corner is outside the class, then
        'no policy in the class beats B1' is trivially unfalsifiable."""
        self.assertEqual(L.STAGE_WEIGHTS["SW-commit"], (0, 0, 0, 0, 1))

    def test_the_library_is_not_merged_into_the_main_registry(self):
        """experiment.main() iterates policies.REGISTRY and every entry costs a
        full attacker-class maximisation per cell. Folding 28 in would triple
        the main grid and bury B1..B7."""
        self.assertFalse(set(L.LIBRARY) & set(P.REGISTRY))


class EveryMemberActuallyRuns(unittest.TestCase):

    def setUp(self):
        self.wfs = experiment.make_corpus(3, 8, seed=2026)
        self.det = detector.Detector.from_setting("mid")
        self.ag = agent.MockAgent()

    def _run(self, name):
        acts, harms = [], []
        for wf in self.wfs:
            ps = build.plan_poison(wf, "memory", 2, random.Random(1))
            if ps is None:
                continue
            pol = L.make(name, 17.95, rng_seed=1)
            r = runner.run_once(wf, ps, pol, self.det, self.ag, seed=1,
                                record_traces=True)
            harms.append(r.harm)
            acts += [getattr(t, "action", None) for t in (r.traces or [])]
        return [a for a in acts if a], harms

    def test_no_member_crashes_and_none_is_silently_inert(self):
        """A policy that never acts is not a member of the class, it is a hole
        in it -- and it would drag rho down for free."""
        inert = []
        for name in L.LIBRARY:
            acts, harms = self._run(name)
            self.assertTrue(harms, f"{name}: produced no runs")
            if not acts:
                inert.append(name)
        self.assertEqual(inert, [], f"policies that never acted: {inert}")

    def test_the_depth_corollary_has_an_experimental_branch(self):
        """Theorem 4's corollary about audit depth has nothing to test against
        unless some policy actually spends kappa(k) * depth."""
        deep = []
        for name in L.FAMILIES["belief-threshold"]:
            acts, _ = self._run(name)
            deep += [a for a in acts if P.DEPTH_SEP in a]
        self.assertTrue(deep, "no policy ever audited deeper than 1")
        self.assertTrue(any(a.startswith("memory" + P.DEPTH_SEP) for a in deep),
                        f"depth actions seen but none on memory: {set(deep)}")

    def test_members_do_not_all_behave_alike(self):
        """28 names for one behaviour would make the covering radius a fiction."""
        sigs = set()
        for name in L.LIBRARY:
            acts, _ = self._run(name)
            sigs.add(tuple(acts))
        self.assertGreater(len(sigs), 10,
                           f"only {len(sigs)} distinct action sequences over 28 policies")


if __name__ == "__main__":
    unittest.main()
