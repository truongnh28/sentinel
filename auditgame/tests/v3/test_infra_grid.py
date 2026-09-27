"""The run grid, the best-response trims of plan S8 (Q14) and the episode counts (T22).
Infrastructure; the rows that protect a draft sentence are in v3/dcm/T22.csv.  Run from
auditgame/.  Nothing here runs an episode or reads an eval workflow: the counts read the
pinned SHAPE of the eval splits (corpus.EVAL_SUMMARY_PINNED)."""
import unittest
from collections import Counter

from v3 import attackers as A
from v3 import budget as BU
from v3 import config as C
from v3 import grid as G


def _by_block(units):
    out = {}
    for u in units:
        out.setdefault(u.block, []).append(u)
    return out


class TestInfraGrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.units = G.units()
        cls.blocks = _by_block(cls.units)

    def test_br_trims_match_declared_plan(self):
        """D7.br (Q14): "the attacker's best response within ΠA is computed by enumeration
        over (k, ι, σ), and the defender picks the minimax policy."

        The best-response blocks kept are plan S8's, read from T7's br_systems (imported,
        not copied): main -- every system, headline detector, every (rho, chi, Delta);
        attacker column -- the Sentinel class; sensitivity and K_d -- B1 and Sentinel at
        Delta in {4, 8}; H18 -- chi 1.33 and {b1, 2 x B_min}; seed-2 pairs off in the core;
        plus the declared exception: the reversible world's attacker column untrimmed."""
        self.assertIs(G.A.br_systems, A.br_systems)
        self.assertEqual(G.definition()["br_trims"], A.BR_TRIMS)
        br = self.blocks["br"]
        self.assertEqual({u.cell.dprime for u in br}, {C.HEADLINE_DPRIME})
        self.assertEqual({u.system for u in br}, set(G.SYSTEMS))
        self.assertEqual(len(br), len(G.SYSTEMS) * 4 * 3 * len(C.DELTAS))
        att = self.blocks["attacker-delta"]
        self.assertEqual({u.system for u in att}, set(G.SENTINEL_CLASS))
        self.assertEqual({u.cell.delta for u in att}, {C.DELTA_ATTACKER})
        for name in G.CORE_SENSITIVITIES:
            sb = self.blocks.get(f"sens-br:{name}", [])
            if name == "seed-2":
                self.assertEqual(sb, [], "the pair block 4* is off in the core")
                continue
            self.assertEqual({u.system for u in sb}, set(G.PAIR))
            self.assertEqual({u.cell.delta for u in sb}, set(C.HEADLINE_DELTAS))
        kb = self.blocks["kd-br"]
        self.assertEqual(({u.system for u in kb}, {u.cell.delta for u in kb}),
                         (set(G.PAIR), set(C.HEADLINE_DELTAS)))
        hb = self.blocks["h18-br"]
        self.assertEqual({u.cell.chi for u in hb}, {C.HEADLINE_CHI})
        self.assertFalse(any(u.cell.price_only for u in hb))
        self.assertEqual({u.cell.budget for u in hb}, {"b1", "2xBmin"})
        at_b1 = {u.system for u in hb if u.cell.budget == "b1"}
        self.assertEqual(at_b1, {G.BLOCK_SCHEDULE}, "the rest of b1 is the main br block")
        rev = self.blocks["sens-attacker-delta:reversible"]
        self.assertEqual({u.system for u in rev}, {G.SENTINEL})
        self.assertEqual(len(rev), len(C.RHO_GRID))
        self.assertEqual(A.br_systems(rev[0].cell, rev[0].world), "none",
                         "br_systems trims it; the grid's exception is what keeps it")
        self.assertFalse(any(u.core for u in self.blocks["seed2-pairs"]))

    def test_main_grid_is_the_product_of_every_axis(self):
        """D8.delta: "Trigger delay Δ ∈ {0, 1, 2, 4, 8} tasks" -- and D8.chi: every rho x chi
        x detector x Delta cell holds every system against every held-out attacker."""
        main = self.blocks["main"]
        cells = {u.cell for u in main}
        self.assertEqual(len(cells), 4 * 3 * 3 * 5)
        self.assertEqual({c.delta for c in cells}, set(C.DELTAS))
        self.assertEqual({c.chi for c in cells}, set(C.CHI_LEVELS))
        self.assertEqual({c.rho for c in cells}, set(C.RHO_GRID))
        self.assertEqual({c.dprime for c in cells}, set(C.DPRIME_LEVELS))
        per = Counter(u.cell for u in main)
        self.assertEqual(set(per.values()), {len(G.SYSTEMS) * len(G.HELD_OUT)})
        self.assertEqual(set(G.HELD_OUT), set(A.held_out()))
        self.assertTrue(all(u.world == C.PRIMARY for u in main))

    def test_sensitivity_blocks_flip_exactly_one_switch(self):
        """Q2: every sens block runs in a world that is PRIMARY with one switch flipped, at
        chi 1.33 and the mid detector; A7 and stage are outside the core (C1, C2)."""
        sens = dict(C.sensitivities())
        for u in self.units:
            if not u.block.startswith("sens"):
                continue
            self.assertEqual(u.world, sens[u.world_name])
            diff = [f for f in C.world_fields()
                    if getattr(u.world, f) != getattr(C.PRIMARY, f)]
            self.assertEqual(len(diff), 1, u.block)
            self.assertEqual((u.cell.chi, u.cell.dprime), (C.CHI_PRIMARY, C.DPRIME_PRIMARY))
            self.assertEqual(u.core, u.world_name in G.CORE_SENSITIVITIES)

    def test_h18_drops_are_budget_holes_with_reasons(self):
        """N3 / R9: Delta = 0 and the attacker column leave H18 with budget's
        BudgetUndefined message; the B_min levels leave every commit-suffices cell (rho = 1
        at the mid detector); b1 at rho = 1 stays; WINDOW cells stay flagged."""
        drops = G.dropped()
        undefined = [d for d in drops if d.cell.delta in (0, C.DELTA_ATTACKER)]
        self.assertTrue(undefined)
        for d in undefined:
            with self.assertRaises(BU.BudgetUndefined) as cm:
                BU.bmin(d.cell, C.TABLE_H_MAX)
            self.assertEqual(d.reason, str(cm.exception))
        cs = [d for d in drops if d.cell.delta not in (0, C.DELTA_ATTACKER)]
        self.assertTrue(cs)
        for d in cs:
            self.assertEqual(d.reason, BU.FLAG_COMMIT_SUFFICES)
            self.assertEqual(d.cell.rho, 1.0)
            self.assertNotEqual(d.cell.budget, "b1")
        h18 = self.blocks["h18"]
        self.assertTrue(any(u.cell.rho == 1.0 and u.cell.budget == "b1" for u in h18))
        self.assertFalse(any(u.cell.rho == 1.0 and u.cell.budget != "b1" for u in h18))
        self.assertEqual({u.cell.delta for u in h18}, set(G.H18_DELTAS))
        for u in h18:
            self.assertEqual(bool(u.flags), BU.FLAG_WINDOW in BU.bmin(u.cell, 14).flags
                             and u.cell.budget != "b1")
        combos = {(u.system, u.cell.chi, u.cell.price_only, u.cell.budget) for u in h18}
        self.assertEqual(len(combos), 4 * 5 * 4 - 9, "P0 GD 11: 80 combinations, 9 in main")

    def test_p0_model_reproduces_the_p0_cost_table(self):
        """D9.scale: "4,500 instances × 8 systems × 3 seeds." -- v3's scale is counted, not
        asserted: with P0's own design (no trims, no drops) on P0's workflow unit (the
        secondary split, 26 workflows), every block equals docs/reports/v3-p0-chi-phi.md
        S3, and the headline rollout equals S6.2 (7,638 + 18,650 episodes, 47 / 129
        CPU-hours at R = 16)."""
        p0 = G.by_p0_block("secondary", p0_model=True)
        for b in G.P0_BLOCKS:
            self.assertAlmostEqual(p0[b], G.P0_EPISODES[b], delta=1.0, msg=b)
        self.assertAlmostEqual(p0["total"], G.P0_TOTAL, delta=1.0)
        head = {"held-out": 0.0, "br": 0.0}
        hist = G.histogram("secondary")
        for u in self.units:
            if u.block.startswith("headline-rollout"):
                head["br" if u.is_br else "held-out"] += G.episodes(u, hist)
        for k, v in G.P0_HEADLINE.items():
            self.assertAlmostEqual(head[k], v, delta=1.0)
        hr = G.headline_rollout_hours("secondary", 16)
        self.assertAlmostEqual(hr["held-out"], 47, delta=1.0)
        self.assertAlmostEqual(hr["br"], 129, delta=1.0)

    def test_trimmed_core_is_within_p0_on_its_unit(self):
        """Plan T22 acceptance: after the trims the core total is <= P0's on P0's unit.  The
        blocks the trims touch shrink, the others stay equal; H18 shrinks by >= 70%."""
        p0 = G.by_p0_block("secondary", p0_model=True)
        tr = G.by_p0_block("secondary")
        self.assertLessEqual(tr["total"], G.P0_TOTAL)
        for b in ("main", "br", "attacker-delta"):
            self.assertAlmostEqual(tr[b], p0[b], delta=1.0)
        for b in ("sensitivity", "kd", "h18"):
            self.assertLess(tr[b], p0[b])
        self.assertLessEqual(tr["h18"], 0.3 * p0["h18"])

    def test_counts_on_the_primary_split_read_shape_only(self):
        """The primary eval split is 96 workflows (D-v3-1); its count reads the pinned H
        histogram, and a held-out unit at Delta = 8 counts the 56 workflows with H >= 9."""
        hist = G.histogram("primary")
        self.assertEqual(sum(hist.values()), 96)
        u = next(u for u in self.blocks["main"] if u.cell.delta == 8)
        self.assertAlmostEqual(G.episodes(u, hist, seeds=1, survival=1.0), 56)
        self.assertGreater(G.by_p0_block("primary")["total"],
                           G.by_p0_block("secondary")["total"])

    def test_definition_digest_is_stable_and_every_chain_is_a_unit_seed(self):
        self.assertEqual(G.definition_digest(), G.definition_digest())
        ch = G.chains(["kd"], seeds=C.SEEDS[:2])
        self.assertEqual(len(ch), 2 * len(self.blocks["kd"]))
        self.assertEqual({c.seed for c in ch}, set(C.SEEDS[:2]))
        self.assertTrue(all(u.core for u in {c.unit for c in G.chains(core_only=True,
                                                                        seeds=(0,))}))


if __name__ == "__main__":
    unittest.main()
