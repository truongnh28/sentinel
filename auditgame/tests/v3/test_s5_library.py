"""The restricted policy library of Algorithm 1 line 5 (T11, v3/library.py).  Each test
protects the DCM rows of v3/dcm/T11.csv that name it; its docstring carries the id(s) and
the verbatim draft sentence.

The belief-reading members read b_t only through the frozen api.BeliefAPI.  T9's particle
filter is written in parallel, so these tests use `StubBelief`, a small BeliefAPI whose
attack mass splits into a part no observation informs (share f, Prop. 6.1 of paper v2) and
a per-carrier part that a quiet audit of the carrier shrinks and an alarm grows."""
import unittest

import carrier_policies as CP
from v3 import api as A
from v3 import config as C
from v3 import library as L

HS = (6, 10, 14)                                        # draft S8: H ~ U{6..14}
PRIOR = {"memory": 0.4, "skill": 0.3, "queue": 0.2, "branch": 0.1}


class StubBelief:
    """A BeliefAPI stand-in.  Unnormalised masses: null 1 - p0, uninformable p0 f, and
    p0 (1 - f) PRIOR[k] on each carrier k.  An audit of target k multiplies carrier k's
    mass by lr_quiet (no alarm) or lr_alarm; with commit_informs=False a commit review
    informs nothing (v2's D17 premise of Prop. 6.1)."""

    def __init__(self, p0=0.5, f=0.2, *, lr_quiet=0.5, lr_alarm=6.0, commit_informs=True,
                 prior=PRIOR):
        self.null, self.unin = 1.0 - p0, p0 * f
        self.inf = {k: p0 * (1.0 - f) * prior[k] for k in C.CARRIERS}
        self.lr_quiet, self.lr_alarm, self.commit_informs = lr_quiet, lr_alarm, commit_informs
        self.updates = 0
        self.history = [self.p_poisoned()]

    def set_state(self, p, masses):
        """Probe: p_attack = p, the attack mass spread over carriers by `masses`."""
        s = sum(masses.values())
        self.null, self.unin = 1.0 - p, 0.0
        self.inf = {k: p * masses[k] / s for k in C.CARRIERS}
        return self

    def update(self, t, obs):
        self.updates += 1
        if obs.bought is not None and (obs.bought.target != "commit" or self.commit_informs):
            k = C.CARRIER_OF_TARGET[obs.bought.target]
            self.inf[k] *= self.lr_alarm if obs.alarm else self.lr_quiet
        self.history.append(self.p_poisoned())

    def condition_on_quarantine(self, t, carrier):
        self.inf[carrier] = 0.0

    def _z(self):
        return self.null + self.unin + sum(self.inf.values())

    def p_poisoned(self):
        return (self.unin + sum(self.inf.values())) / self._z()

    def carrier_mass(self):
        z = self._z()
        return {k: (self.inf[k] + self.unin / len(C.CARRIERS)) / z for k in C.CARRIERS}

    def expected_harm(self):
        return 0.5 * self.p_poisoned()

    def bin_features(self):
        m = self.carrier_mass()
        return A.BinFeatures(p_attack=self.p_poisoned(), top_carrier=max(m, key=m.get),
                             delegated_mass=sum(m[k] for k in ("skill", "queue")))

    def sample(self, n, seed):
        return []


def ctx_for(cell=None, *, H=10, rng_seed=7):
    cell = cell or C.Cell(rho=0.0, delta=4)
    kappa = cell.kappa()
    return A.EpisodeContext(world=C.PRIMARY, cell=cell, wf_id="wf-test", seed=1, H=H,
                            budget=H * kappa["commit"], depths=cell.depths(), kappa=kappa,
                            delegated=cell.delegated(), rng_seed=rng_seed)


def every_cell():
    for chi in C.CHI_LEVELS:
        for rho in C.RHO_GRID:
            yield C.Cell(rho=rho, delta=4, chi=chi)


STUB_BAND = L.band_prop61(0.5, 0.2)


class TestS5Library(unittest.TestCase):

    def test_library_has_28_members_in_three_families(self):
        """D5.2.lib (O10): "a restricted policy library (28 parameterised policies spanning
        stage-weighted, belief-threshold and carrier-rotation families)".
        DA1.l8: "quarantine the highest-posterior carrier" is Sentinel's line 9, not a
        member's: members only choose the action, and only READ the shared b_t.

        8 SW (v2's _SW) + 12 BT (4 band positions x v2's 3 floors) + 8 RO (2 orders x 2
        periods x O10's 2 phases); every member is an api.PolicyV3."""
        self.assertEqual(len(L.LIBRARY), 28)
        fam = L.by_family()
        self.assertEqual({f: len(v) for f, v in fam.items()}, C.LIBRARY_FAMILIES)
        self.assertEqual(tuple(fam), ("SW", "BT", "RO"))
        # the declared grids (L1): v2's grids reused, O10's phase axis for RO
        self.assertEqual(L.SW_WEIGHTS, CP._SW)
        self.assertEqual({L.LIBRARY[n][1]["weights"] for n in fam["SW"]}, set(CP._SW))
        self.assertEqual({(L.LIBRARY[n][1]["u"], L.LIBRARY[n][1]["floor"]) for n in fam["BT"]},
                         {(u, fl) for u in CP._TAUS for fl in CP._FLOORS})
        self.assertEqual({(k["order"], k["period"], L.RO_PHASES[k["phase"]])
                          for k in (L.LIBRARY[n][1] for n in fam["RO"])},
                         {(o, p, ph) for o in ("c3", "c4") for p in (1, 2) for ph in C.RO_AXIS})
        for H in HS:
            ctx = ctx_for(H=H)
            belief = StubBelief()
            lib = L.make_library(ctx, belief=belief, band=STUB_BAND)
            self.assertEqual(tuple(lib), L.MEMBERS)
            for name, m in lib.items():
                self.assertIsInstance(m, A.PolicyV3, name)
                self.assertEqual(m.family, L.family_of(name))
                for t in range(H):
                    d = m.distribution(t)
                    self.assertAlmostEqual(sum(d.values()), 1.0, places=12, msg=name)
                    a = m.act(t, ctx.budget)
                    self.assertIn(a.target, C.TARGETS)
                    self.assertGreater(d[a.target], 0.0, f"{name} drew off its support")
                    o = L.scripted_observation(ctx, t, a, alarm=(t == 2))
                    m.observe(t, o)
                    self.assertIsNone(m.quarantine(t), f"{name}: lines 8-9 are Sentinel's")
                log = m.decision_log()
                self.assertTrue(all("seed" not in e for e in log), "the log never names a seed")
            self.assertEqual(belief.updates, 0, "a member in Sentinel never updates b_t")
        # standalone (owns_belief) a member runs line 7 itself, once per task
        own = StubBelief()
        m = L.make_member("L-BT-u0.9-f0", ctx_for(H=6), belief=own, band=STUB_BAND,
                          owns_belief=True)
        for t in range(6):
            m.observe(t, L.scripted_observation(m.ctx, t, m.act(t, 1e9), False))
        self.assertEqual(own.updates, 6)
        # the belief-reading members refuse to run without a BeliefAPI
        for name in L.MEMBERS:
            cls = L.LIBRARY[name][0]
            if cls is L.BeliefThreshold or L.LIBRARY[name][1].get("phase") == "posterior":
                with self.assertRaises(ValueError):
                    L.make_member(name, ctx_for(), band=STUB_BAND)
            else:
                L.make_member(name, ctx_for())
        with self.assertRaises(TypeError):
            L.make_member("L-RO-c3-p1-posterior", ctx_for(), belief=object())

    def test_library_members_are_distinct_under_fixed_depth(self):
        """D8.chi (C16, O10, R7): "carrier heterogeneity χ ∈ {0, 0.5, 1.34} (achieved by
        equalising or differentiating audit depths)".

        The cell fixes the depth, so no member carries a depth: every action is at the
        cell's depth for its target in every chi cell.  v2's RO depth axis {2, 3} would
        collapse 8 members to 4; O10's phase axis keeps 28 pairwise distinct policies,
        compared as functions of (b_t, t) on probe beliefs and rng seeds."""
        for n, (cls, kw) in L.LIBRARY.items():
            self.assertNotIn("depth", kw, n)
        v2_ro = {tuple(sorted((k, v) for k, v in kw.items() if k != "depth"))
                 for n, (cls, kw) in CP.LIBRARY.items() if cls is CP.CarrierRotation}
        self.assertEqual(len(v2_ro), 4, "v2's RO-d2 and RO-d3 coincide at a fixed depth")
        for cell in every_cell():
            ctx = ctx_for(cell, H=14)
            lib = L.make_library(ctx, belief=StubBelief(), band=STUB_BAND)
            for name, m in lib.items():
                for t in range(ctx.H):
                    a = m.act(t, ctx.budget)
                    self.assertEqual(a.depth, cell.depths()[a.target], (name, cell.chi))
        # probes: p_attack across the stub band's four tau, two carrier-mass profiles
        profiles = [(p, masses) for p in (0.1, 0.3, 0.36, 0.43, 0.48, 0.7)
                    for masses in (PRIOR, {"memory": 0.1, "skill": 0.2, "queue": 0.6,
                                           "branch": 0.1})]
        sig = {}
        for name in L.MEMBERS:
            rows = []
            for seed in range(4):
                for p, masses in profiles:
                    ctx = ctx_for(H=14, rng_seed=seed)
                    m = L.make_member(name, ctx, belief=StubBelief().set_state(p, masses),
                                      band=STUB_BAND)
                    rows.append(tuple(tuple(round(m.distribution(t).get(k, 0.0), 9)
                                            for k in C.TARGETS) for t in range(ctx.H)))
            sig[name] = tuple(rows)
        by_sig = {}
        for name, s in sig.items():
            by_sig.setdefault(s, []).append(name)
        self.assertEqual([v for v in by_sig.values() if len(v) > 1], [],
                         "members that play identically")

    def test_prop61_each_family_has_a_member_that_changes_a_decision(self):
        """D5.2.lib (sentinel-v3.md "Thư viện" gate, paper v2 Prop. 6.1): "a restricted
        policy library (28 parameterised policies spanning stage-weighted, belief-threshold
        and carrier-rotation families)".

        The gate before tuning: on reachable histories (all quiet; one alarm at task j),
        each family has a member whose decision differs from B1's; in BT and RO some
        member's decision reads the history; in BT some member both commits and sweeps
        (Prop. 6.1's lock broken).  Control: v2's absolute tau {0.3, 0.5, 0.7, 0.9} in a
        world whose commit review informs nothing (f = 0.5147, H = 6) is locked, and the
        gate says so; a commit-only SW family fails too."""
        for cell in (C.Cell(rho=r, delta=4) for r in C.RHO_GRID):
            for H in HS:
                ctx = ctx_for(cell, H=H)
                for commit_informs in (True, False):
                    rep = L.decision_gate(
                        ctx, lambda: StubBelief(commit_informs=commit_informs), STUB_BAND)
                    self.assertEqual(rep.failures(), [], (cell.rho, H, commit_informs))
                    self.assertTrue(rep.passed)
                    for fam in L.FAMILIES:
                        self.assertTrue(rep.changing(fam), fam)
                    self.assertTrue(rep.reading("BT") and rep.reading("RO"))
                    self.assertTrue(rep.unlocked_bt())
                    self.assertFalse(rep.members["L-SW-commit"]["differs_from_b1"])
                    self.assertEqual(rep.reading("SW"), [], "SW reads no belief")
        # control: v2's library tau in v2's premise is locked
        ctx = ctx_for(H=6)
        v2_bt = {f"v2-BT-{tau}-f{i}": ("BT", (lambda tt, ff: lambda c, b: L.BeliefThreshold(
                     c, name=f"v2-{tt}", belief=b, tau=tt, floor=ff))(tau, fl))
                 for tau in CP._TAUS for i, fl in enumerate(CP._FLOORS)}
        rep = L.decision_gate(ctx, lambda: StubBelief(f=0.5147, commit_informs=False),
                              builders=v2_bt)
        self.assertEqual(rep.unlocked_bt(), [])
        self.assertIn("BT: every member's commit rule is constant (Prop. 6.1 lock)",
                      rep.failures())
        self.assertEqual({n for n in v2_bt if not rep.members[n]["differs_from_b1"]},
                         {n for n in v2_bt if not n.startswith("v2-BT-0.3-")},
                         "tau >= p0 plays exactly as B1")
        sw_only = {"L-SW-commit": ("SW", lambda c, b: L.make_member("L-SW-commit", c))}
        self.assertFalse(L.decision_gate(ctx, StubBelief, builders=sw_only).passed)

    def test_tau_inside_p_floor_p0_band(self):
        """D5.2.lib (paper v2 Prop. 6.1, prop:res-lock): "a restricted policy library (28
        parameterised policies spanning stage-weighted, belief-threshold and
        carrier-rotation families)".

        p_floor = p0 f / (p0 f + 1 - p0) reproduces paper v2's numbers (p0 = 0.5,
        f = 0.5147 / 0.4409 -> 0.3398 / 0.3060), which v2's absolute tau grid misses;
        every BT member's tau is strictly inside (p_floor, p0) for any band; the stub
        belief never falls below p_floor on a reachable history, so the reachable band
        lies inside the proposition's."""
        self.assertAlmostEqual(L.prop61_floor(0.5, 0.5147), 0.3398, places=4)
        self.assertAlmostEqual(L.prop61_floor(0.5, 0.4409), 0.3060, places=4)
        paper = L.Band(0.3398, 0.5, "paper v2")
        self.assertEqual([t for t in CP._TAUS if paper.contains(t)], [],
                         "v2's tau grid misses the band common to every H")
        bands = [paper, L.band_prop61(0.5, 0.4409), L.band_prop61(0.5, 0.0),
                 L.band_prop61(0.2, 0.3), STUB_BAND]
        for band in bands:
            ctx = ctx_for()
            for name in L.by_family()["BT"]:
                m = L.make_member(name, ctx, belief=StubBelief(), band=band)
                self.assertTrue(band.contains(m.tau), (name, band, m.tau))
                self.assertTrue(band.p_floor < m.tau < band.p0)
                self.assertAlmostEqual(m.tau, band.tau(m.u), places=15)
        for bad in ((0.5, 0.5), (0.6, 0.5), (0.1, 1.0)):
            with self.assertRaises(ValueError):
                L.Band(bad[0], bad[1], "bad")
        with self.assertRaises(ValueError):
            L.make_member("L-BT-u0.5-f0", ctx_for(), belief=StubBelief())      # no band
        # Prop. 6.1 on the stub: p_attack never falls below the floor on any history
        f, p0 = 0.2, 0.5
        floor = L.prop61_floor(p0, f)
        seen = []
        for H in HS:
            ctx = ctx_for(H=H)
            for respond in L.gate_scripts(H).values():
                for name in L.MEMBERS:
                    b = StubBelief(p0, f)
                    L.decision_trace(lambda c, bb: L.make_member(name, c, belief=bb,
                                                                 band=STUB_BAND),
                                     ctx, lambda: b, respond)
                    seen.extend(b.history)
        self.assertGreaterEqual(min(seen), floor - 1e-12)
        reach = L.band_reachable(p0, seen)
        self.assertGreaterEqual(reach.p_floor, STUB_BAND.p_floor)
        self.assertEqual(reach.p0, STUB_BAND.p0)


if __name__ == "__main__":
    unittest.main()
