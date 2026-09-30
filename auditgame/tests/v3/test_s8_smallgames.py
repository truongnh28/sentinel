"""The 240 small games of H7 (T21, v3/smallgame_v3.py): B7 = the exact minimax, the 28
library members ported, regret against B7 and the covering radius against pi*.  Each test
protects the DCM rows of v3/dcm/T21.csv that name it; its docstring carries the id(s) and
the verbatim draft sentence.

The belief the ported BT / RO-posterior members read is the small game's exact posterior
(smallgame_v3.SmallBelief), a stub: T9's particle filter is not imported.  To check the
port against v3/library.py it is wrapped in `GameBelief`, an api.BeliefAPI."""
import unittest

import numpy as np

import smallgame as SG
from v3 import api as A
from v3 import config as C
from v3 import library as L
from v3 import smallgame_v3 as S

#: A few games of every shape the tests run the expensive checks on.
SAMPLE = (S.Game(3, 2, 1, 1), S.Game(4, 4, 3, 4), S.Game(5, 3, 2, 2), S.Game(6, 4, 2, 2),
          S.Game(6, 4, 5, 4), S.Game(4, 3, 0, 4))


class GameBelief:
    """api.BeliefAPI over a SmallBelief at task t (K = 4: the game's carriers are all four)."""

    def __init__(self, b: S.SmallBelief, t: int):
        self.b, self.t = b, t
        tg = S.GAME_TARGETS[b.g.K]
        mass = b.carrier_mass(t)
        self._mass = {k: 0.0 for k in C.CARRIERS}
        for j, x in enumerate(tg):
            self._mass[C.CARRIER_OF_TARGET[x]] = mass[j]

    def update(self, t, obs):
        raise AssertionError("a member never updates the shared belief")

    def condition_on_quarantine(self, t, carrier):
        raise AssertionError("a member never quarantines")

    def p_poisoned(self):
        return self.b.p_attack()

    def carrier_mass(self):
        return dict(self._mass)

    def expected_harm(self):
        return self.b.p_attack()

    def bin_features(self):
        m = self._mass
        return A.BinFeatures(p_attack=self.b.p_attack(), top_carrier=max(m, key=m.get),
                             delegated_mass=m["skill"] + m["queue"])

    def sample(self, n, seed):
        return []


def ctx_for(H):
    cell = C.Cell(rho=0.0, delta=4)
    kappa = cell.kappa()
    return A.EpisodeContext(world=C.PRIMARY, cell=cell, wf_id="wf-small", seed=1, H=H,
                            budget=H * kappa["commit"], depths=cell.depths(), kappa=kappa,
                            delegated=cell.delegated(), rng_seed=3)


def histories(g, P):
    """Every decision history of the schedule distribution P, with its belief."""
    out = []
    for h in S.decision_histories(g, S.prefix_probs(P)):
        b = S.SmallBelief(g)
        for t, a in enumerate(h):
            b = b.after(t, a)
        out.append((h, b))
    return out


class TestS8Smallgames(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.games = S.games()
        cls.exact = {g: S.solve_exact(g) for g in cls.games}
        cls.members = {g: {n: S.leaves(p) for n, p in S.ported_library(g).items()}
                       for g in cls.games}
        cls.values = {g: S.library_values(cls.members[g], g) for g in cls.games}

    def test_240_small_games_solved_exactly(self):
        """D8.small (H7): "On the 240 exactly-solvable small games".

        The 240 cells are v2's smallgame.games() (H 2..6 x K 2..4 x m 1..4 x every
        feasible Delta), K H <= 40.  Each is solved over EVERY policy: an LP over all
        schedules (on the path where L is open every audit was quiet, so a policy is a
        distribution over schedules).  Exactness is certified by the dual: the attacker's
        mix y* holds every schedule to >= V*, and pi* holds every configuration to <= V*."""
        self.assertEqual(len(self.games), 240)
        self.assertEqual(len(set(self.games)), 240)
        self.assertTrue(all(g.K * g.H <= 40 for g in self.games))
        for g in self.games:
            ex = self.exact[g]
            self.assertTrue(S.feasible(ex.P, g), g)
            self.assertAlmostEqual(S.value_of(ex.P, g), ex.value, places=9, msg=g)
            self.assertAlmostEqual(sum(ex.y.values()), 1.0, places=9)
            self.assertAlmostEqual(ex.certificate, ex.value, places=7, msg=f"{g} not certified")
            self.assertTrue(0.0 <= ex.value <= 1.0)
            # v2's coverage-marginal LP is a relaxation: never above the exact value
            self.assertLessEqual(SG.solve(g.H, g.K, g.delta, g.m)["value"], ex.value + 1e-9)
        # brute force on the smallest games: no pure schedule beats y*, none catches all
        for g in self.games[:12]:
            ex = self.exact[g]
            for s in S.schedules(g.H, g.K, g.m):
                self.assertGreaterEqual(
                    sum(w for c, w in ex.y.items() if S.misses(s, c, g)), ex.value - 1e-9)

    def test_b7_is_the_exact_minimax_ceiling(self):
        """D9.B7 (H7): "(B7) Exhaustive small… game oracle — the minimax solution, computable
        only on the 240 small games; a ceiling, not a competitor."

        B7 is pi*, the exact LP solution; its value V* is a floor for every policy, so no
        mixture of the 28 ported members concedes less on any of the 240 games."""
        for g in self.games:
            v = self.values[g]
            self.assertGreaterEqual(v["V_mixture"], self.exact[g].value - 1e-9, g)
            self.assertGreaterEqual(v["V_single"], v["V_mixture"] - 1e-9, g)
            for n, P in self.members[g].items():
                self.assertGreaterEqual(S.value_of(P, g), self.exact[g].value - 1e-9, (g, n))

    def test_regret_against_b7_on_small_games(self):
        """D9.3.regret (H7): "Empirical regret against B7 on small games."

        regret = V(conv Pi) - V*: the library's minimax over mixtures of the 28 members
        (what line 5 computes) minus B7's value; >= 0, and it is the value of the mixture
        the LP returns (re-measured by the attacker's best response)."""
        for g in self.games:
            row = self.values[g]
            reg = row["V_mixture"] - self.exact[g].value
            self.assertGreaterEqual(reg, -1e-9)
            names = list(self.members[g])
            mix = S.mixture([self.members[g][n] for n in names],
                            [row["x_mixture"][n] for n in names])
            self.assertAlmostEqual(S.value_of(mix, g), row["V_mixture"], places=7, msg=g)
        # a game where the budget never binds: the library reaches B7
        g = S.Game(4, 4, 3, 4)
        self.assertAlmostEqual(self.values[g]["V_mixture"], self.exact[g].value, places=9)
        # and one where it binds: members spend m audits at once (O14), B7 waits
        g = S.Game(3, 2, 1, 1)
        self.assertAlmostEqual(self.exact[g].value, 0.5, places=9)
        self.assertAlmostEqual(self.values[g]["V_mixture"], 1.0, places=9)

    def test_ported_members_are_feasible(self):
        """D5.2.lib (H7): "a restricted policy library (28 parameterised policies spanning
        stage-weighted, belief-threshold and carrier-rotation families)".

        The 28 members, same names and families, run on every one of the 240 games; each is
        a probability distribution over schedules with one action per task and at most m
        audits (its marginals pass v2's smallgame.feasible)."""
        for g in self.games:
            lib = S.ported_library(g)
            self.assertEqual(tuple(lib), L.MEMBERS)
            fams = {}
            for n, p in lib.items():
                fams[p.family] = fams.get(p.family, 0) + 1
                self.assertEqual(p.family, L.family_of(n))
                P = self.members[g][n]
                self.assertTrue(S.feasible(P, g), (g, n))
                self.assertAlmostEqual(sum(P.values()), 1.0, places=12)
            self.assertEqual(fams, C.LIBRARY_FAMILIES)

    def test_ported_members_follow_the_library_rules(self):
        """D5.2.lib (H7): "a restricted policy library (28 parameterised policies spanning
        stage-weighted, belief-threshold and carrier-rotation families)".

        With K = 4 the game has all four targets, and on every history a ported member
        reaches its decision is the one v3/library.py's member takes from the same belief
        (SW weights, BT's tau in the Prop. 6.1 band and its posterior sweep draw, RO's
        order / period / phase; RO's random phase and tie draws enumerated)."""
        for g in (S.Game(6, 4, 2, 4), S.Game(5, 4, 1, 3), S.Game(4, 4, 0, 2)):
            self.assertEqual(S.GAME_TARGETS[g.K], C.TARGETS)
            band = L.band_prop61(S.SMALL_P0, S.SMALL_F)
            ctx = ctx_for(g.H)
            for n, p in S.ported_library(g).items():
                for h, b in histories(g, S.leaves(p)):
                    t = len(h)
                    gb = GameBelief(b, t)
                    self.assertIsInstance(gb, A.BeliefAPI)
                    for q, st in p.initial():
                        port = {}
                        for w, a, _ in p.decide(t, b, st):
                            port[C.TARGETS[a]] = port.get(C.TARGETS[a], 0.0) + w
                        m = L.make_member(n, ctx, belief=gb, band=band)
                        if isinstance(p, S.PortedRO) and p.phase == "random":
                            m._offset = st
                        lib = m.distribution(t)
                        lib = {k: v for k, v in lib.items() if v > 0}
                        # (a fresh RO-posterior member and the port's empty state both
                        # anchor the current cycle at this call, from this belief)
                        if isinstance(p, S.PortedRO) and p.phase == "posterior" and len(port) > 1:
                            # a tie: the library draws one of the tied starts
                            self.assertEqual(len(lib), 1)
                            self.assertIn(next(iter(lib)), port, (g, n, h))
                            continue
                        self.assertEqual(set(lib), set(port), (g, n, h))
                        for k in lib:
                            self.assertAlmostEqual(lib[k], port[k], places=12, msg=(g, n, h))

    def test_covering_radius_is_measured_against_pi_star(self):
        """D6.3.radius (H7, Prop. 6 as corrected): "We measure 𝜌 for our 28-policy library
        against exact solutions on the small games".

        The radius is Def. 4.1 with P_ref = {pi*}: the UNIFORM TV over histories (a max, not
        v2's mean over tasks), measured against a minimax pi* of the game, over mixtures of
        the 28 ported members.  A library holding pi* has radius 0; a mixture is never
        farther than the nearest single member; refining pi* inside the minimax set keeps
        it minimax and never increases the radius."""
        g = S.Game(3, 2, 1, 2)
        # uniform, not mean: two policies equal at the root, disjoint after one history
        P1 = {(0, 0, 2): 0.5, (1, 1, 2): 0.5}
        P2 = {(0, 1, 2): 0.5, (1, 1, 2): 0.5}
        d, h = S.uniform_tv(P1, P2, g)
        self.assertAlmostEqual(d, 1.0)
        self.assertEqual(h, (0,))
        mean_v2 = SG.tv(SG.per_task(S.coverage(P1, g), g.H, g.K),
                        SG.per_task(S.coverage(P2, g), g.H, g.K))
        self.assertLess(mean_v2, d)
        for g in SAMPLE:
            ex = self.exact[g]
            Ps = list(self.members[g].values())
            r, x = S.radius_mixture(Ps + [ex.P], ex.P, g)
            self.assertAlmostEqual(r, 0.0, places=6, msg=f"{g}: pi* in the library")
            rad = S.radius(g, ex, self.members[g])
            self.assertLessEqual(rad["radius_mixture"], rad["radius_single"] + 1e-9)
            names = list(self.members[g])
            mix = S.mixture(Ps, [rad["x_radius"].get(n, 0.0) for n in names])
            self.assertAlmostEqual(S.uniform_tv(mix, ex.P, g)[0], rad["radius_mixture"],
                                   places=9, msg="the reported radius is measured")
        for g in (S.Game(4, 4, 3, 4), S.Game(6, 4, 2, 2)):
            ex = self.exact[g]
            rad = S.radius(g, ex, self.members[g], refine=True)
            self.assertLessEqual(rad["radius_refined"], rad["radius_mixture"] + 1e-9)
            r_star, star, v = S.closest_minimax(g, ex, self.members[g][rad["nearest_single"]])
            self.assertLessEqual(v, ex.value + 1e-6, "a refined pi* stays minimax")
        # a member that is itself minimax: radius 0 against the pi* nearest it
        g = S.Game(4, 4, 3, 4)
        rad = S.radius(g, self.exact[g], self.members[g], refine=True)
        self.assertAlmostEqual(rad["radius"], 0.0, places=6)
        self.assertLess(rad["radius"], S.literal_radius_floor(g))

    def test_prop6_bound_holds_with_radius_against_pi_star(self):
        """D6.3.prop6 (H7, Prop. 4.2 of the theory note): "Let Π be a finite policy library
        with covering radius 𝜌 in total-variation over audit-action distributions relative
        to the unrestricted policy space".

        Measured against pi* (the reading under which Prop. 6 is proved; relative to the
        unrestricted space the radius is >= 1 - 1/(K+1), Remark 4.3), the bound
        V(conv Pi) - V* <= H rho range(L) holds on all 240 games, range(L) = 1."""
        for g in self.games:
            ex = self.exact[g]
            rad = S.radius(g, ex, self.members[g])
            reg = self.values[g]["V_mixture"] - ex.value
            self.assertLessEqual(reg, g.H * rad["radius"] + 1e-6, g)
            self.assertAlmostEqual(S.literal_radius_floor(g), 1 - 1 / (g.K + 1))


if __name__ == "__main__":
    unittest.main()
