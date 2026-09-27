"""H18 budget grid (T16a): B_min(Delta) of the theory note's Theorem 5.6, the budget levels
of Q8, the price-only chi arm (C16) and the block schedule of Proposition 5.7.  Each test
protects one DCM row of v3/dcm/T16.csv; its docstring carries the id and the draft quote.

Reference numbers are the theory note's (Table tab:lp, S5) and the output of
theory/checks/thm4_budget.py (parts C and D, scipy quad), pinned here as literals: the
checks script is ported, never imported (plan T16).

T16b adds, with the runner (T6) and the grid (T22): test_missed_before_sigma_is_logged
[H18] and test_kd_grid_runs_at_primary_for_every_rho [H19]."""
import json
import math
import unittest

import draft_setup as D
from v3 import api
from v3 import budget as B
from v3 import config as C

#: theory/checks/thm4_budget.py kl_mix(beta, d' sqrt(depth)) with scipy quad (27/09).
DS_REF = {("mid", "memory", 3): 4.476974, ("mid", "queue", 2): 4.625228,
          ("mid", "skill", 1): 2.197007, ("mid", "skill", 3): 6.718424,
          ("mid", "queue", 3): 6.969802, ("weak", "memory", 1): 0.590644,
          ("strong", "queue", 3): 12.566833}
DPRIME = {"weak": 1.516110983768996, "mid": 2.2114201815598795, "strong": 2.9598451549064855}


def all_cells(delta):
    for rho in C.RHO_GRID:
        for chi in C.CHI_LEVELS:
            for dp in C.DPRIME_LEVELS:
                for po in (False, True):
                    if po and chi == C.CHI_PRIMARY:
                        continue
                    yield C.Cell(rho=rho, delta=delta, chi=chi, dprime=dp, price_only=po)


def context(cell, H, budget):
    return api.EpisodeContext(world=C.PRIMARY, cell=cell, wf_id="wf-test", seed=1, H=H,
                              budget=budget, depths=cell.depths(), kappa=B.cell_kappa(cell),
                              delegated=cell.delegated())


class TestS9Budget(unittest.TestCase):
    def test_bmin_matches_theory_note_theorem_5_6(self):
        """D6.thm4 (C13, H18): "To distinguish a poisoned state from a benign one with error
        ≤ α at the moment of decision, the required audit budget satisfies".

        B_min(Delta) = K kbar n_alpha floor((H-1)/Delta), n_alpha = (l_alpha - eps_c)^+/D_s,
        l_alpha = log(1/(4 alpha)) (theory note Theorem 5.6(ii)); window Delta >= K n_alpha
        (5.6(i)); eps_c >= l_alpha gives B_min = 0 (5.6(iii)).  Checked on Table tab:lp,
        on the Gaussian D_s of check part D, and on one cell computed by hand."""
        self.assertAlmostEqual(B.ell_alpha(0.05), math.log(5.0), places=12)
        # Table tab:lp: H = 30, K = 4, kappa = (0.4, 0.9, 1.6, 2.5), D_s = 0.8, eps_c = 0.
        n = B.n_alpha(B.ell_alpha(0.05), 0.0, 0.8)
        self.assertAlmostEqual(n, 2.01, places=2)
        self.assertAlmostEqual(4 * n, 8.05, places=2)
        kbar = (0.4 + 0.9 + 1.6 + 2.5) / 4
        for delta, want in ((12, 21.727), (16, 10.864), (20, 10.864), (29, 10.864)):
            self.assertAlmostEqual(B.bmin_formula(30, delta, 4, kbar, n), want, places=3)
        n4 = {k: n for k in range(4)}
        for delta in range(1, 30):
            self.assertEqual(B.window_ok(delta, n4), delta >= 9, f"Delta={delta}")  # "<= 8 vo nghiem"
            self.assertAlmostEqual(
                B.bmin_carriers(30, delta, dict(zip(range(4), (0.4, 0.9, 1.6, 2.5))), n4),
                B.bmin_formula(30, delta, 4, kbar, n), places=9,
                msg="the per-carrier form IS the theorem when D_s is common")
        # Hand-computed: Delta = 5, H = 12, K = 3, kbar = 2, l = log 5, eps_c = 0.6, D_s = 0.5.
        self.assertAlmostEqual(B.bmin_formula(12, 5, 3, 2.0, B.n_alpha(math.log(5), 0.6, 0.5)),
                               3 * 2.0 * (math.log(5) - 0.6) / 0.5 * 2, places=12)
        self.assertEqual(B.n_alpha(math.log(5), 2.0, 0.5), 0.0)            # (l - eps_c)^+
        # Gaussian D_s (Lemma 5.5(b), check part D): no drift is mu^2/2 exactly.
        mu3 = 2.2114 * math.sqrt(3)
        self.assertAlmostEqual(B.kl_drift_gauss(0.0, mu3), 7.335, places=3)
        for (det, t, depth), want in DS_REF.items():
            got = B.kl_drift_gauss(B.BETA[t], DPRIME[det] * math.sqrt(depth))
            self.assertAlmostEqual(got, want, places=5, msg=f"{det} {t} depth {depth}")
        self.assertEqual(B.SWEEP_TARGETS, ("memory", "queue", "skill"))
        self.assertEqual(B.BETA, {"memory": 0.314, "queue": 0.033, "skill": 0.058})
        # One cell by hand: rho = 0.5, Delta = 4, chi = 1.33 (depths 3,2,1 on memory, queue,
        # skill; prices 1.2, 1.8, 1.6), mid detector, H = 10 -> floor(9/4) = 2.
        cell = C.Cell(rho=0.5, delta=4, chi="1.33", dprime=2.21)
        r = B.bmin(cell, 10)
        eps_c = 0.25 * DPRIME["mid"] ** 2 / 2
        gap = math.log(5) - eps_c
        want = 2 * (1.2 * gap / 4.476974 + 1.8 * gap / 4.625228 + 1.6 * gap / 2.197007)
        self.assertAlmostEqual(r.eps_c, eps_c, places=12)
        self.assertAlmostEqual(r.value, want, places=5)
        self.assertAlmostEqual(r.value, 2.765796, places=5)
        self.assertEqual(r.flags, ())
        # Theorem 5.6(iii): at rho = 1 the mid detector's commit already carries l_alpha.
        r1 = B.bmin(C.Cell(rho=1.0, delta=4, dprime=2.21), 10)
        self.assertEqual(r1.value, 0.0)
        self.assertIn(B.FLAG_COMMIT_SUFFICES, r1.flags)
        # Theorem 5.6(i): the window flag is exactly sum_k n_k > Delta, never interpolated.
        n_flagged = 0
        for delta in (1, 2, 4, 8):
            for cell in all_cells(delta):
                r = B.bmin(cell, 14)
                self.assertEqual(B.FLAG_WINDOW in r.flags, sum(r.n.values()) > delta)
                n_flagged += B.FLAG_WINDOW in r.flags
        self.assertGreater(n_flagged, 0, "the weak detector at Delta = 1 violates the window")
        self.assertIn(B.FLAG_WINDOW, B.bmin(C.Cell(rho=0.0, delta=1, dprime=1.52), 10).flags)

    def test_bmin_is_non_increasing_in_delta(self):
        """D6.thm4 (C13, H18): "Theorem 4 makes this precise: the budget required to
        distinguish harmful persistence from benign state change grows with trigger delay
        and with carrier heterogeneity".

        The theory note corrects the direction: the lower bound falls with Delta
        (Proposition 5.9(b) for the LP relaxation; floor((H-1)/Delta) here).  H18 keeps
        both directions in the scorecard (C13); this test fixes what v3 computes."""
        for H in range(6, 15):
            for cell1 in all_cells(1):
                prev = math.inf
                for delta in range(1, H):
                    if delta in C.DELTAS:
                        v = B.bmin(C.Cell(**{**cell1.as_dict(), "delta": delta}), H).value
                    else:                       # off-grid Delta: the formula on the same inputs
                        r = B.bmin(cell1, H)
                        v = B.bmin_carriers(H, delta, r.kappa, r.n)
                    self.assertLessEqual(v, prev + 1e-12, f"{cell1} H={H} Delta={delta}")
                    prev = v
                lo = B.bmin(C.Cell(**{**cell1.as_dict(), "delta": 8}), 14).value
                hi = B.bmin(cell1, 14).value
                if hi > 0:
                    self.assertLess(lo, hi)
        lp_bound = [B.bmin_formula(30, d, 4, 1.35, math.log(5) / 0.8) for d in (12, 16, 20, 29)]
        self.assertEqual(lp_bound, sorted(lp_bound, reverse=True))

    def test_budget_levels_are_b1_and_multiples_of_bmin(self):
        """D5.2.b1 (C4, Q8, H18): "Audit-at-Commit spends the entire budget inspecting the
        final commit of each task at maximum depth."

        b1 = H x max kappa is loose (C4): the dearest audit, the commit at depth 1 (4.1), at
        every task.  The binding levels are {2, 1, 0.5} x B_min(Delta) per cell.  Delta = 0
        and the attacker column have no B_min and are dropped (R9); b1 stays defined."""
        self.assertEqual(C.BUDGET_LEVELS, ("b1",) + tuple(B.MULTIPLE))
        self.assertEqual(B.MULTIPLE, {"2xBmin": 2.0, "1xBmin": 1.0, "0.5xBmin": 0.5})
        for H in (6, 10, 14):
            for delta in (1, 2, 4, 8):
                if delta > H - 1:
                    continue
                for cell in all_cells(delta):
                    kap = B.cell_kappa(cell)
                    base = C.Cell(**{**cell.as_dict(), "budget": "b1"})
                    self.assertAlmostEqual(B.budget_of(base, H), H * max(kap.values()), places=9)
                    if not cell.price_only:
                        self.assertAlmostEqual(B.budget_of(base, H), 4.1 * H, places=9)
                    bm = B.bmin(cell, H).value
                    for level, mult in B.MULTIPLE.items():
                        c = C.Cell(**{**cell.as_dict(), "budget": level})
                        self.assertAlmostEqual(B.budget_of(c, H), mult * bm, places=12)
                        self.assertEqual(B.bmin(c, H).value, bm, "B_min does not read the level")
        for delta in (0, C.DELTA_ATTACKER):
            for level in B.MULTIPLE:
                with self.assertRaises(B.BudgetUndefined):
                    B.budget_of(C.Cell(rho=0.0, delta=delta, budget=level), 10)
            self.assertAlmostEqual(B.budget_of(C.Cell(rho=0.0, delta=delta), 10), 41.0)
        with self.assertRaises(B.BudgetUndefined):
            B.bmin(C.Cell(rho=0.0, delta=8), 8)                          # Delta > H - 1

    def test_price_only_arm_keeps_depth_and_kbar(self):
        """D8.chi (C16, Q6): "carrier heterogeneity χ ∈ {0, 0.5, 1.34} (achieved by
        equalising or differentiating audit depths)".

        The price-only arm holds the primary depths (3, 2, 1, 1) and kbar = 2.175 and moves
        the prices affinely about kbar (order kept) until chi_range equals the chi of the
        named depth cell: chi then changes the price, not the information per look."""
        primary = C.Cell(rho=0.0, delta=4)
        base = primary.kappa()
        self.assertAlmostEqual(D.kappa_bar(base), 2.175, places=12)
        for chi in C.CHI_LEVELS:
            if chi == C.CHI_PRIMARY:
                with self.assertRaises(ValueError):
                    B.price_only_kappa(chi)
                continue
            cell = C.Cell(rho=0.0, delta=4, chi=chi, price_only=True)
            depth_cell = C.Cell(rho=0.0, delta=4, chi=chi)
            kap = B.cell_kappa(cell)
            self.assertEqual(cell.depths(), primary.depths(), "depths are held")
            self.assertAlmostEqual(D.kappa_bar(kap), D.kappa_bar(base), places=12)
            self.assertAlmostEqual(D.chi_range(kap), D.chi_range(depth_cell.kappa()), places=12)
            self.assertEqual(f"{D.chi_range(kap):.2f}", chi)
            self.assertEqual(sorted(kap, key=kap.get), sorted(base, key=base.get))
            self.assertTrue(all(v > 0 for v in kap.values()))
            self.assertEqual(B.cell_kappa(depth_cell), depth_cell.kappa())
        want = {"1.04": (1.417634, 1.883705, 1.728348, 3.670312),
                "2.11": (0.628929, 1.580357, 1.263214, 5.2275)}
        for chi, vals in want.items():
            kap = B.price_only_kappa(chi)
            for t, v in zip(C.TARGETS, vals):
                self.assertAlmostEqual(kap[t], v, places=5, msg=f"{chi} {t}")

    def test_block_schedule_matches_proposition_5_7(self):
        """D6.thm4 (H18): "To distinguish a poisoned state from a benign one with error ≤ α at
        the moment of decision, the required audit budget satisfies".

        The achievability side (theory note Proposition 5.7), ported from check part C:
        n = ceil(2 log(1/alpha)/((1-beta)^2 gamma^2)); b = floor(Delta/(n+1)); every window
        of length Delta holds >= n sweeps of each carrier; both errors of the counting test
        <= alpha (exact binomial tails); spend up to t <= (K kbar / b) t; B = K kbar H / b."""
        psi, phi, beta, alpha = 0.85, 0.12, 0.05, 0.05
        gamma = psi - phi
        phib = beta * psi + (1 - beta) * phi
        n = B.counting_n(alpha, beta, gamma)
        self.assertEqual(n, 13)
        err0, err1 = B.binom_tails(n, psi, phib)
        hoeff = math.exp(-n * (1 - beta) ** 2 * gamma ** 2 / 2)
        self.assertAlmostEqual(err0, 0.0016, places=4)
        self.assertAlmostEqual(err1, 0.0013, places=4)
        self.assertLessEqual(max(err0, err1), hoeff)
        self.assertLessEqual(hoeff, alpha)
        kappa = [0.4, 0.9, 1.6, 2.5]
        K, kbar = len(kappa), sum(kappa) / len(kappa)
        table = {(200, 56): (4, 270.0), (200, 112): (8, 135.0), (400, 56): (4, 540.0),
                 (400, 112): (8, 270.0), (400, 224): (16, 135.0), (800, 56): (4, 1080.0),
                 (800, 112): (8, 540.0), (800, 224): (16, 270.0)}
        seen = set()
        for H in (200, 400, 800):
            for delta in (K * (n + 1), 2 * K * (n + 1), 4 * K * (n + 1)):
                if delta > H - 1:
                    continue
                sched, b = B.block_schedule(H, K, delta, n, kappa)
                Bud = K * kbar * H / b
                self.assertEqual((b, round(Bud, 2)), table[(H, delta)])
                seen.add((H, delta))
                for iota in range(1, H - delta + 1):                         # (a)
                    win = sched[iota: iota + delta]
                    for k in range(K):
                        self.assertGreaterEqual(sum(1 for x in win if x == k), n)
                spent = 0.0
                for t in range(1, H + 1):                                    # (c)
                    if sched[t] is not None:
                        spent += kappa[sched[t]]
                    self.assertLessEqual(spent, Bud * t / H + 1e-9)
                block = [x for x in sched[1: b + 1] if x is not None]
                self.assertEqual(block, sorted(range(K), key=lambda k: kappa[k]), "cheapest first")
        self.assertEqual(seen, set(table))
        with self.assertRaises(ValueError):                                  # K(n+1) > Delta
            B.block_schedule(100, K, K * (n + 1) - 1, n, kappa)

    def test_block_schedule_policy_follows_the_schedule(self):
        """D6.thm4 (H18): "To distinguish a poisoned state from a benign one with error ≤ α at
        the moment of decision, the required audit budget satisfies".

        The block schedule as a PolicyV3 on a v3 cell.  With the draft's detectors n >= 8,
        so Prop. 5.7's K(n+1) <= Delta never holds at Delta <= 8: the policy logs
        precondition_met = False and uses the densest block (b = K).  Under a binding
        budget it lengthens the block so that spend stays within B t / H (5.7(c)).  The
        counting test rejects a carrier and the policy quarantines it."""
        cell = C.Cell(rho=0.0, delta=8)
        ctx = context(cell, 14, B.budget_of(cell, 14))
        pol = B.BlockSchedule(ctx)
        self.assertIsInstance(pol, api.PolicyV3)
        self.assertGreaterEqual(pol.n, 8)
        self.assertFalse(pol.precondition_met)
        self.assertFalse(pol.budget_paced)
        self.assertEqual(pol.b, 3)
        self.assertEqual(pol.order, ["memory", "skill", "queue"])            # 1.2 < 1.6 < 1.8
        acts = [pol.act(t, 1e9) for t in range(14)]
        want = ["memory", "skill", "queue"] * 4 + [None, None]
        self.assertEqual([a.target if a else None for a in acts], want)
        for a in acts:
            if a is not None:
                self.assertEqual(a.depth, cell.depths()[a.target], "the cell's depth (C16)")
        # A binding budget: 1 x B_min at H = 14.
        tight = C.Cell(rho=0.0, delta=4, budget="1xBmin")
        Bud = B.budget_of(tight, 14)
        pol = B.BlockSchedule(context(tight, 14, Bud))
        self.assertTrue(pol.budget_paced)
        kap = B.cell_kappa(tight)
        spent, n_bought = 0.0, 0
        for t in range(14):
            a = pol.act(t, Bud - spent)
            if a is not None:
                spent += kap[a.target]
                n_bought += 1
            self.assertLessEqual(spent, Bud * (t + 1) / 14 + 1e-9)
        self.assertGreater(n_bought, 0)
        # The counting test: an alarm on the one sweep of memory in the window rejects it.
        pol = B.BlockSchedule(ctx)
        a0 = pol.act(0, 1e9)
        pol.observe(0, api.Observation(t=0, requested=a0, bought=a0, scores=(3.0,), alarm=True))
        self.assertEqual(pol.quarantine(0), "memory")
        self.assertIsNone(pol.quarantine(1))
        a1 = pol.act(1, 1e9)
        pol.observe(1, api.Observation(t=1, requested=a1, bought=a1, scores=(0.0,), alarm=False))
        self.assertIsNone(pol.quarantine(1))
        a2 = pol.act(2, 1e9)
        pol.observe(2, api.Observation(t=2, requested=a2, bought=None))     # not bought
        self.assertIsNone(pol.quarantine(2))
        json.dumps(pol.decision_log())
        self.assertEqual(pol.decision_log()[0]["precondition_met"], False)
        with self.assertRaises(B.BudgetUndefined):
            B.BlockSchedule(context(C.Cell(rho=0.0, delta=0), 10, 41.0))


if __name__ == "__main__":
    unittest.main()
