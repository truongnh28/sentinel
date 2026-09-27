"""Algorithm 1 lines 2-3: the exact minimax solve when KH <= 40 (plan T13).

Each test protects the DCM rows of v3/dcm/T13.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  Run from auditgame/.
"""
import logging
import unittest

import numpy as np

import smallgame
from v3 import api as A
from v3 import config as C
from v3 import exact as E


def _ctx(H, cell=None, world=C.PRIMARY, seed=7):
    cell = cell or C.Cell(rho=0.5, delta=4)
    kappa = cell.kappa()
    return A.EpisodeContext(world=world, cell=cell, wf_id="t13", seed=seed, H=H,
                            budget=max(kappa.values()) * H, depths=cell.depths(),
                            kappa=kappa, delegated=cell.delegated(), rng_seed=seed)


class TestAlg1Line23(unittest.TestCase):

    def test_line2_exact_when_KH_le_40_or_logs_infeasibility(self):
        """DA1.l2: "Small games (KH ≤ 40 belief-state discretisation) are solved exactly by
        backward induction over a discretised belief simplex."

        Line 2 reads KH <= 40 with K = 4 carriers.  Small and within the declared limits
        (10^6 sequences, 60 s) -> line 3 solves exactly and the plan is a valid sequence
        form that the policy walks; small but beyond the limits -> an infeasibility record
        (states, runtime, memory) and the log line `line23: infeasible, states=...,
        runtime=...`, and line 5 runs; KH > 40 -> line 5 without a solve attempt."""
        self.assertEqual(E.THRESHOLD_KH, 40)
        self.assertEqual(E.K_CARRIERS, 4)
        self.assertEqual((E.MAX_SEQUENCES, E.MAX_SECONDS), (10 ** 6, 60.0))
        self.assertTrue(E.is_small(10) and not E.is_small(11))

        # small and feasible: exact
        ctx = _ctx(3)
        res = E.line23(ctx, 1)
        self.assertEqual(res.kind, "exact")
        tree, sol = res.tree, res.solution
        self.assertEqual(tree.n_sequences, E.count_tree(tree.game)["sequences"])
        A_eq, b_eq = E._flow_matrix(tree)
        r = np.append(np.clip(sol.r, 0, None), sol.value)
        self.assertLess(np.abs(A_eq @ r - b_eq).max(), 1e-7)       # sequence form holds
        self.assertLessEqual(sol.per_strategy.max(), sol.value + 1e-7)
        for d in range(tree.n_nodes):                               # hard budget on every path
            self.assertTrue(set(tree.node_labels[d]) <= {E.NONE, E.QUARANTINE, E.CONTINUE,
                                                          *C.TARGETS})
        # the policy walks the plan and publishes distributions, never the draw
        pol = E.ExactLine3Policy(ctx, res)
        B = ctx.budget
        for t in range(ctx.H):
            a = pol.act(t, B)
            if a is not None:
                self.assertEqual(a.depth, ctx.depths[a.target])
                B -= ctx.kappa[a.target]
            self.assertGreaterEqual(B, -1e-9)
            pol.observe(t, A.Observation(t=t, requested=a, bought=a, alarm=False,
                                         scores=(0.0,) if a else ()))
            self.assertIsNone(pol.quarantine(t))
        self.assertFalse(pol.off_tree)
        logged = [e for e in pol.decision_log() if "x_t" in e]
        self.assertEqual(len(logged), ctx.H)
        for e in logged:
            self.assertAlmostEqual(sum(e["x_t"].values()), 1.0, places=9)
        # every alarm path too: the response node is played, the walk stays on the tree
        for seed in range(12):
            pol = E.ExactLine3Policy(_ctx(3, seed=seed), res)
            for t in range(ctx.H):
                a = pol.act(t, ctx.budget)
                pol.observe(t, A.Observation(t=t, requested=a, bought=a, alarm=a is not None))
                q = pol.quarantine(t)
                if q is not None:
                    self.assertEqual(q, C.CARRIER_OF_TARGET[a.target])
            self.assertFalse(pol.off_tree, pol.decision_log())

        # small but beyond the declared limits: evidence, a log line, line 5
        with self.assertLogs("v3.line23", level=logging.WARNING) as cm:
            res8 = E.line23(_ctx(8), 1)
        self.assertEqual(res8.kind, "infeasible")
        rec = res8.record
        self.assertEqual((rec.reason, rec.H, rec.KH), ("sequences", 8, 32))
        self.assertGreater(rec.states, E.MAX_SEQUENCES)
        self.assertGreater(rec.memory_bytes, 0)
        self.assertGreaterEqual(rec.runtime_s, 0.0)
        self.assertTrue(any(m.split(":", 2)[2].strip().startswith(
            "line23: infeasible, states=") for m in cm.output), cm.output)
        self.assertIn("runtime=", cm.output[0])
        # the runtime limit is enforced too
        with self.assertLogs("v3.line23", level=logging.WARNING):
            slow = E.solve_game(E.v3_game(_ctx(4), 1), max_seconds=1e-6)
        self.assertEqual((slow.kind, slow.record.reason), ("infeasible", "runtime"))
        # a world the exact game does not model: recorded, line 5
        with self.assertLogs("v3.line23", level=logging.WARNING):
            w = E.line23(_ctx(3, world=C.WorldV3(harm="reversible")), 1)
        self.assertEqual((w.kind, w.record.reason), ("infeasible", "world"))

        # KH > 40: the draft's else-branch, nothing built
        big = E.line23(_ctx(11), 1)
        self.assertEqual((big.kind, big.record.reason, big.record.KH), ("line5", "not-small", 44))
        self.assertIsNone(big.tree)

    def test_exact_matches_smallgame_on_coverage_reduction(self):
        """D1.small: "Small games are solved exactly; larger ones use a restricted policy
        library with robust optimisation."

        With perfect detection, no propagation, unit prices and the window {iota ..
        iota + Delta}, the history-tree solve is smallgame.py's covering game; its exact
        value must equal smallgame.solve's LP value on every game checked (all 240-grid
        games with H <= 5, and H = 6 with K = 2)."""
        n = 0
        for g in smallgame.games():
            if g["H"] > 6 or (g["H"] == 6 and g["K"] != 2):
                continue
            ref = smallgame.solve(g["H"], g["K"], g["delta"], g["m"])["value"]
            tree = E.build_tree(E.coverage_game(g["H"], g["K"], g["delta"], g["m"]))
            self.assertAlmostEqual(E.solve_tree(tree).value, ref, places=6, msg=str(g))
            n += 1
        self.assertGreaterEqual(n, 192)

    def test_library_never_beats_exact_value(self):
        """D5.2.l3: "Line 3 gives exact solutions on the small games where they are
        computable, which are our validation oracle."

        No library policy evaluated exactly in the same game does better than the exact
        minimax value, and the exact plan re-evaluated by the same evaluator gives the LP
        value back.  The 28 members are T11's; the declared stand-ins (B1, uniform,
        insertion, rotation, stationary mixes, recheck, idle; with and without quarantine
        on alarm) take their place until the library lands."""
        members = [E.stand_in(nm) for nm in E.STAND_INS]
        members += [E.stand_in(nm, quarantine_on_alarm=False) for nm in E.STAND_INS]
        members += [E.stand_in("mix", mix=x) for x in (0.0, 0.25, 0.75, 1.0)]
        checked = 0
        for rho in C.RHO_GRID:
            for H, dhat in ((3, 0), (3, 1), (4, 2)):
                res = E.line23(_ctx(H, C.Cell(rho=rho, delta=4)), dhat)
                self.assertTrue(res.exact)
                v = res.solution.value
                again = E.evaluate(res.tree, lambda tr, d: res.solution.behaviour(tr, d))
                self.assertAlmostEqual(again["value"], v, places=6)
                for pol in members:
                    got = E.evaluate(res.tree, pol)["value"]
                    self.assertGreaterEqual(got, v - 1e-7, (rho, H, dhat, pol.__name__))
                    checked += 1
        for g in ({"H": 4, "K": 3, "delta": 1, "m": 2}, {"H": 5, "K": 2, "delta": 2, "m": 1}):
            tree = E.build_tree(E.coverage_game(**g))
            v = E.solve_tree(tree).value
            for pol in members:
                self.assertGreaterEqual(E.evaluate(tree, pol)["value"], v - 1e-7)
                checked += 1
        self.assertGreater(checked, 200)


if __name__ == "__main__":
    unittest.main()
