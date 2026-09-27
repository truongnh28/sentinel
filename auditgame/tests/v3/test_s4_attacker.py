"""Draft S4 attacker (T7): v3/attackers.py.

Each test protects the DCM rows of v3/dcm/T07.csv whose `test` column names it; its
docstring carries the ids and the verbatim draft sentences.  The attacker is evaluated by
the runner (T6) and the grid (T22); here the attacker's side is checked on its own: what
it may choose in a cell, which rules exist and which are held out, what it is allowed to
know, what its budget allows, and the "attacker chooses Delta" column (C10, O5)."""
import inspect
import unittest
from collections import Counter
from dataclasses import replace
from itertools import combinations

import attackers_v2 as A2
import corpus_v2
import metrics_v2 as MV
from core import CARRIERS, seed_of
from v3 import attackers as A
from v3 import config as C
from v3 import payload as P

#: A slice of dev (the v2 corpus, Q10) for the per-placement checks; the per-rule checks
#: run on all of dev, which is cheap.
_N_SAMPLE = 20

_HIDDEN = dict(C.sensitivities())["ingress-hidden"]
_SEED2 = dict(C.sensitivities())["seed-2"]


def _dev():
    return corpus_v2.make_corpus_v2()


def _cell(delta, **kw):
    return C.Cell(rho=0.5, delta=delta, **kw)


class TestS4Attacker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dev = _dev()
        cls.sample = cls.dev[:_N_SAMPLE]

    # ------------------------------------------------------- D4.attacker, C10: the menu

    def test_attacker_menu_matches_cell(self):
        """D4.attacker (C10): "The attacker chooses (k, ι, σ, ε): a permitted carrier,
        insertion time, trigger schedule, and a bounded modification of magnitude ≤ ε."
        D7.br: "the attacker’s best response within ΠA is computed by enumeration over
        (k, ι, σ), and the defender picks the minimax policy."
        D10.6.ingress (H8): "Against audit-on-insertion, every best response inserts
        through repository ingress rather than direct write—the unaudited channel—"

        In a fixed-Delta cell the attacker chooses (k, iota, eps) and sigma = iota + Delta:
        the best-response menu is EVERY feasible sleeper placement of T3's planner over
        the four carriers and the declared eps grid, nothing else.  The channel is a
        choice only where it changes what an audit sees (ingress hidden, S10.6); where the
        insertion audit sees ingress it is inert (D7) and the menu has one channel.  The
        "attacker" column has no menu until a Delta class resolves Delta (O5).  Which
        cells get a best-response block at all is the plan's S8 trim (Q14)."""
        self.assertEqual(A.BR_EPS, tuple(sorted({r[3] for r in A.SCRIPTED_RULES})))
        self.assertTrue(all(0 < e <= A.EPS_MAX for e in A.BR_EPS))
        n_pl = 0
        for wf in self.sample:
            for d in C.DELTAS:
                cell = _cell(d)
                menu = A.cell_menu(wf, cell)
                self.assertEqual(menu, A.br_menu(wf, d))
                want = {(k, p.iota, p.sigma, e) for e in A.BR_EPS for k in CARRIERS
                        for p in P.plan_sleeper_all(wf, k, d, e)}
                got = [(pl.k[0], pl.iota, pl.sigma, pl.epsilon) for pl in menu]
                self.assertEqual(len(got), len(set(got)), "no placement twice")
                self.assertEqual(set(got), want, (wf.wf_id, d))
                for pl in menu:
                    n_pl += 1
                    self.assertEqual(pl.sigma - pl.iota, d)
                    self.assertEqual(pl.delta, d)
                    self.assertEqual(pl.channel, "write")
                    self.assertEqual(len(pl.k), 1)
                    self.assertTrue(pl.within_budget(C.PRIMARY))
                self.assertEqual(len({pl.id for pl in menu}), len(menu), "ids are unique")
                # ingress hidden: the channel becomes a choice, one copy per channel
                hid = A.cell_menu(wf, cell, _HIDDEN)
                self.assertEqual(len(hid), 2 * len(menu))
                self.assertEqual(Counter(pl.channel for pl in hid),
                                 Counter({"write": len(menu), "ingress": len(menu)}) if menu
                                 else Counter())
                self.assertEqual({(pl.k, pl.iota, pl.epsilon) for pl in hid},
                                 {(pl.k, pl.iota, pl.epsilon) for pl in menu})
                # every scripted rule's realisation is in the best responder's class
                ids = {pl.id for pl in hid}
                for name, att in A.SCRIPTED.items():
                    pl = att.plan(wf, d, _HIDDEN)
                    if pl is not None:
                        self.assertIn(pl.id, ids, (name, wf.wf_id, d))
        self.assertGreater(n_pl, 1000)

        # the "attacker" column: no menu until a Delta class is given (O5)
        wf = self.sample[0]
        with self.assertRaises(ValueError):
            A.cell_menu(wf, _cell(C.DELTA_ATTACKER))
        fixed4 = next(dc for dc in A.attacker_delta_menu() if dc.delta == 4)
        self.assertEqual(A.cell_menu(wf, _cell(C.DELTA_ATTACKER), delta_class=fixed4),
                         A.br_menu(wf, 4))
        with self.assertRaises(ValueError):          # a fixed cell takes no Delta class
            A.cell_menu(wf, _cell(4), delta_class=fixed4)

        # S8 trims (Q14): which systems get a best-response block in which cell
        W = dict(C.sensitivities())
        cases = [
            (C.PRIMARY, _cell(0), "all"),                                  # main grid
            (C.PRIMARY, _cell(8, chi="2.11"), "all"),
            (C.PRIMARY, _cell(4, dprime=1.52), "none"),                    # non-headline detector
            (C.PRIMARY, _cell(C.DELTA_ATTACKER), "sentinel"),              # attacker-chooses-Delta
            (C.PRIMARY, _cell(C.DELTA_ATTACKER, dprime=2.96), "none"),
            (W["ingress-hidden"], _cell(4), "b1+sentinel"),                # sensitivities
            (W["drift-persistent"], _cell(8), "b1+sentinel"),
            (W["reversible"], _cell(2), "none"),
            (W["reversible"], _cell(C.DELTA_ATTACKER), "none"),
            (C.PRIMARY, _cell(4, k_delegated=3), "b1+sentinel"),           # K_d axis
            (C.PRIMARY, _cell(1, k_delegated=1), "none"),
            (C.PRIMARY, _cell(4, budget="2xBmin"), "all"),                 # H18
            (C.PRIMARY, _cell(4, budget="1xBmin"), "none"),
            (C.PRIMARY, _cell(4, budget="2xBmin", chi="2.11"), "none"),
            (C.PRIMARY, _cell(4, chi="2.11", price_only=True), "none"),
            (W["seed-2"], _cell(4), "none"),                               # block 4* off
        ]
        for world, cell, want in cases:
            self.assertEqual(A.br_systems(cell, world), want, (C.world_name(world), cell))
        self.assertEqual(A.br_systems(_cell(4), W["seed-2"], core=False), "b1+sentinel")
        self.assertFalse(A.N_A_SHARED)

    # ------------------------------------------------------------- D8.attackers, D18

    def test_eighteen_scripted_seven_held_out(self):
        """D8.attackers (D18): "18 scripted attacker policies, of which 7 are held out from
        all defender development."

        The 18 rules are v2's (_RULES: carrier or per-workflow uniform carrier, iota rule
        first / mid / last, channel, eps), same names; each is built on T3's sleeper
        planner: the rule picks the first / middle / last feasible placement at Delta."""
        self.assertEqual(len(A.SCRIPTED), C.N_SCRIPTED)
        self.assertEqual(len(A.SCRIPTED_RULES), C.N_SCRIPTED)
        self.assertEqual(list(A.SCRIPTED), list(A2.SCRIPTED))
        self.assertEqual(len(A.held_out()), C.N_HELD_OUT)
        self.assertTrue(set(A.held_out()) <= set(A.SCRIPTED))
        self.assertEqual(len(A.development()), C.N_SCRIPTED - C.N_HELD_OUT)
        self.assertEqual(set(A.held_out()) | set(A.development()), set(A.SCRIPTED))
        self.assertFalse(set(A.held_out()) & set(A.development()))
        for name, att in A.SCRIPTED.items():
            v2 = A2.SCRIPTED[name]
            self.assertEqual((att.iota_rule, att.channel, att.epsilon),
                             (v2.iota_rule, v2.channel, v2.epsilon))
            self.assertEqual(att.carrier_rule,
                             "uniform" if callable(v2.carrier_rule) else v2.carrier_rule)
            self.assertIs(A.by_name(name), att)
        n_plans = 0
        for wf in self.dev:
            for d in C.DELTAS:
                for name, att in A.SCRIPTED.items():
                    pl = att.plan(wf, d)
                    k = att.carriers(wf, C.PRIMARY)[0]
                    cands = P.plan_sleeper_all(wf, k, d, att.epsilon)
                    if not cands:
                        self.assertIsNone(pl)
                        continue
                    i = {"first": 0, "mid": len(cands) // 2, "last": len(cands) - 1}[att.iota_rule]
                    self.assertEqual(pl.payloads, (cands[i],), (name, wf.wf_id, d))
                    self.assertEqual(pl.channel, att.channel)
                    n_plans += 1
        self.assertGreater(n_plans, 5000)
        # the per-workflow uniform carrier is v2's draw
        uni = A.SCRIPTED["uniform-mid-write-e0.6"]
        for wf in self.sample:
            self.assertEqual(uni.carriers(wf, C.PRIMARY), (A2._uniform_carrier(wf),))

    def test_held_out_names_equal_v2_split(self):
        """D8.attackers (D18): "18 scripted attacker policies, of which 7 are held out from
        all defender development."

        The held-out split is v2's, name for name and by the same hash
        (core.seed_of("heldout-v2", name)); so are the development split and, in the
        primary world, the six D18 tuning columns line 5 uses as attacker classes."""
        self.assertEqual(A.held_out(), A2.held_out())
        self.assertEqual(A.held_out(),
                         sorted(sorted(A.SCRIPTED, key=lambda n: seed_of("heldout-v2", n))
                                [:C.N_HELD_OUT]))
        self.assertEqual(A.development(), A2.development())
        self.assertEqual(A.tuning_attack_names(), A2.tuning_attack_names())
        self.assertEqual([a.name for a in A.br_attacks()], [a.name for a in A2.br_attacks()])
        self.assertEqual(A.attacker_classes(), tuple(A2.tuning_attack_names()))
        self.assertEqual(len(A.attacker_classes()), C.N_ATTACKER_CLASSES)

    # ------------------------------------------------------------ S5.5, D18: tuning

    def test_tuning_columns_never_realise_held_out_behaviour(self):
        """D5.5.freeze (D18): "Adaptive attack development is performed on a development
        split, and both the defender policy and the attacker library are frozen before
        final evaluation on held-out repositories and held-out attacker policies."

        A tuning column is a development or rule-BR column whose behaviour keys (carriers,
        iota rule, eps) can never coincide with a held-out attacker's.  The channel joins
        the key where it changes what an audit sees (ingress hidden); with two seeded
        carriers the key holds the realisable carrier pair.  Checked on the keys and on
        every realisation over dev.

        With two seeded carriers no rule is behaviour-disjoint from the held-out set: the
        second carrier is uniform over the other three, so e.g. memory-first-write-e0.6
        realises {memory, branch} first at eps 0.6, as held-out branch-first-write-e0.6
        does.  That world has no tuning column; line 5 uses the primary world's (O15)."""
        held = set(A.held_out())
        self.assertEqual(A.tuning_attack_names(_SEED2), [])
        for world in (C.PRIMARY, _HIDDEN, _SEED2):
            tune = A.tuning_attack_names(world)
            if world is not _SEED2:
                self.assertTrue(tune, C.world_name(world))
            self.assertFalse(set(tune) & held)
            hk = set().union(*(A.behavior_keys(A.SCRIPTED[n], world) for n in held))
            seen = set()
            for n in tune:
                keys = A.behavior_keys(A.by_name(n), world)
                self.assertFalse(keys & hk, (C.world_name(world), n))
                self.assertNotIn(keys, seen, "one name per distinct behaviour set")
                seen.add(keys)
            for wf in self.dev:
                for d in C.DELTAS:
                    for n in tune:
                        pl = A.by_name(n).plan(wf, d, world)
                        if pl is not None:
                            key = A.realised_key(A.by_name(n), pl, world)
                            self.assertIn(key, A.behavior_keys(A.by_name(n), world))
                            self.assertNotIn(key, hk, (C.world_name(world), n, wf.wf_id, d))
        # the channel is in the key only when ingress is hidden
        att = A.SCRIPTED["memory-last-ingress-e0.6"]
        self.assertEqual(A.behavior_keys(att, C.PRIMARY), {(("memory",), "last", 0.6)})
        self.assertEqual(A.behavior_keys(att, _HIDDEN), {(("memory",), "last", 0.6, "ingress")})
        # line 5's classes are the primary world's tuning columns (O15)
        self.assertEqual(A.attacker_classes(), tuple(A.tuning_attack_names(C.PRIMARY)))
        self.assertFalse(set(A.attacker_classes()) & held)

    # ---------------------------------------------- D4.attacker, D5.3.rand: information

    def test_attacker_sees_policy_not_its_draw(self):
        """D4.attacker (C10): "It observes the defender’s policy (Stackelberg) but not its
        realised randomization."  D5.3.rand (C10): "Sentinel commits to a distribution
        over audit actions and reveals only the distribution."

        (1) No attacker entry point takes an episode seed, a policy, or a draw: a
        placement is a function of (workflow, Delta, world) alone, fixed before the
        episode.  (2) The best response is cross-fitted (D27): the placement is chosen on
        one half of the seeds -- the policy's distribution, sampled -- and scored on the
        other, so the draws it is scored against never enter the choice."""
        banned = {"seed", "seeds", "rng", "rng_seed", "ctx", "policy", "draw", "obs"}
        for fn in (A.AttackV3.plan, A.AttackV3.carriers, A.br_menu, A.cell_menu,
                   A.resolve_delta, A.DeltaClass.delta_for):
            params = set(inspect.signature(fn).parameters)
            self.assertFalse(params & banned, (fn.__qualname__, params & banned))
        for wf in self.sample[:5]:
            for world in (C.PRIMARY, _SEED2):
                for name, att in A.SCRIPTED.items():
                    self.assertEqual(att.plan(wf, 2, world), att.plan(wf, 2, world))

        # A published mixture: audit placement "a" w.p. 0.7, "b" w.p. 0.3 (harm 0 when
        # the audited placement is the attacked one).  Realised draws come from seeds.
        seeds = range(1, 41)

        def harm(pl, s):
            audited = "a" if seed_of("mix", s) % 10 < 7 else "b"
            return 0.0 if audited == pl else 1.0

        rows = [{"wf": "w", "placement": pl, "seed": s, "harm": harm(pl, s)}
                for pl in ("a", "b") for s in seeds]
        for fold in (0, 1):
            self.assertEqual(A.choose(rows, fold), {"w": "b"})
        # the choice on fold 1 is blind to the realised draws of fold 0 (and vice versa)
        for fold in (0, 1):
            flipped = [dict(r, harm=1.0 - r["harm"]) if r["seed"] % 2 != fold else r
                       for r in rows]
            self.assertEqual(A.choose(flipped, fold), A.choose(rows, fold))
            self.assertNotEqual(A.crossfit(flipped)["v_br"], A.crossfit(rows)["v_br"])
        got = A.crossfit(rows)
        self.assertEqual({k: got[k] for k in ("v_br", "v_br_naive", "n_workflows")},
                         MV.crossfit_value(rows))
        self.assertEqual(got["choices"], {"w": {0: "b", 1: "b"}})

        # br_rows runs the menu against a policy through a caller's episode function
        wf = self.sample[0]
        menu = A.br_menu(wf, 1)
        rr = A.br_rows(wf, menu, lambda pl, s: None if s == 3 else float(pl.iota % 2), (1, 2, 3))
        self.assertEqual(len(rr), 2 * len(menu))
        self.assertEqual({r["placement"] for r in rr}, {pl.id for pl in menu})

    # ------------------------------------------------------ D4.attacker: attacker budget

    def test_two_carrier_seeding_respects_attacker_budget(self):
        """D4.attacker (C10): "Its budget constrains the number of carriers it may seed
        and the magnitude of each."

        The attacker's budget is world.n_seeded carriers (1 primary, 2 sensitivity) and
        eps <= EPS_MAX for each.  With two, a scripted rule seeds its own carrier and a
        second one drawn uniformly among the other three per workflow, at the same
        (iota, sigma, eps); the pair best response enumerates carrier pairs."""
        for wf in self.sample:
            for d in (1, 4):
                for name, att in A.SCRIPTED.items():
                    one = att.plan(wf, d)
                    two = att.plan(wf, d, _SEED2)
                    self.assertEqual(one is None, two is None)
                    if one is None:
                        continue
                    self.assertEqual(len(one.k), 1)
                    self.assertTrue(one.within_budget(C.PRIMARY))
                    self.assertEqual(len(two.k), 2)
                    self.assertEqual(len(set(two.k)), 2)
                    self.assertEqual(two.k[0], one.k[0])
                    self.assertEqual(two.payloads[0], one.payloads[0])
                    self.assertEqual({(p.iota, p.sigma, p.epsilon) for p in two.payloads},
                                     {(one.iota, one.sigma, one.epsilon)})
                    self.assertTrue(two.within_budget(_SEED2))
                    self.assertFalse(two.within_budget(C.PRIMARY))
                    self.assertLessEqual(two.epsilon, A.EPS_MAX)
                    self.assertNotEqual(two.payloads[0].item(wf).item_id,
                                        two.payloads[1].item(wf).item_id)
                    # the second payload is itself a feasible T3 placement
                    self.assertIn(two.payloads[1],
                                  P.plan_sleeper_all(wf, two.k[1], d, att.epsilon))
                menu2 = A.br_menu(wf, d, _SEED2)
                menu1 = A.br_menu(wf, d)
                self.assertTrue(all(len(pl.k) == 2 and pl.within_budget(_SEED2) for pl in menu2))
                per = Counter((pl.iota, pl.epsilon) for pl in menu1)
                self.assertEqual(len(menu2), sum(len(list(combinations(range(c), 2)))
                                                 for c in per.values()))
        # the second carrier is uniform over the other three
        att = A.SCRIPTED["memory-first-write-e0.6"]
        second = Counter(att.carriers(wf, _SEED2)[1] for wf in self.dev)
        self.assertEqual(set(second), {"skill", "queue", "branch"})
        # over budget is refused, not clipped
        wf = self.sample[0]
        ps = [p for k in CARRIERS for p in P.plan_sleeper_all(wf, k, 0, 0.6) if p.iota == 0]
        with self.assertRaises(ValueError):
            A.Placement(tuple(ps[:3]), "write")
        with self.assertRaises(ValueError):
            A.Placement((ps[0], ps[0]), "write")
        big = replace(ps[0], epsilon=1.5)
        with self.assertRaises(ValueError):
            A.Placement((big,), "write")
        with self.assertRaises(ValueError):
            A.br_menu(wf, 0, eps_grid=(0.6, 1.5))

    # ---------------------------------------------------------- C10, O5: Delta column

    def test_attacker_chooses_delta_menu_is_declared(self):
        """D8.delta (C10, O5): "Trigger delay Δ ∈ {0, 1, 2, 4, 8} tasks".
        D4.attacker (C10, O5): "The attacker chooses (k, ι, σ, ε): a permitted carrier,
        insertion time, trigger schedule, and a bounded modification of magnitude ≤ ε."

        In the "attacker" column the attacker chooses Delta too.  O5 declares its
        classes before any number: one class per Delta of the grid, used for the whole
        sequence, plus one declared mix that draws Delta uniformly on the grid per
        workflow.  The column's value is the max over the classes.  The planner itself
        always receives a concrete Delta."""
        menu = A.attacker_delta_menu()
        self.assertEqual(tuple(dict.fromkeys(dc.kind for dc in menu)), C.ATTACKER_DELTA_CLASSES)
        fixed = [dc for dc in menu if dc.kind == C.ATTACKER_DELTA_CLASSES[0]]
        mix = [dc for dc in menu if dc.kind == C.ATTACKER_DELTA_CLASSES[1]]
        self.assertEqual(tuple(dc.delta for dc in fixed), C.DELTAS)
        self.assertEqual(len(mix), 1)
        self.assertIsNone(mix[0].delta)
        self.assertEqual(len({dc.name for dc in menu}), len(menu))
        self.assertIs(A.delta_class(mix[0].name), mix[0])
        for dc in fixed:
            self.assertTrue(all(dc.delta_for(wf) == dc.delta for wf in self.sample))
        # the mix: deterministic per workflow, on the grid, close to uniform on dev
        draws = [mix[0].delta_for(wf) for wf in self.dev]
        self.assertEqual(draws, [mix[0].delta_for(wf) for wf in self.dev])
        self.assertEqual(draws, [C.DELTAS[seed_of(A.DELTA_MIX_KEY, wf.wf_id) % len(C.DELTAS)]
                                 for wf in self.dev])
        cnt = Counter(draws)
        self.assertEqual(set(cnt), set(C.DELTAS))
        exp = len(self.dev) / len(C.DELTAS)
        chi2 = sum((cnt[d] - exp) ** 2 / exp for d in C.DELTAS)
        self.assertLess(chi2, 13.28, cnt)            # chi-square(4) at 0.01

        # resolution: a fixed cell needs no class; the attacker column needs one
        wf = self.sample[0]
        self.assertEqual(A.resolve_delta(_cell(4), wf), 4)
        with self.assertRaises(ValueError):
            A.resolve_delta(_cell(C.DELTA_ATTACKER), wf)
        for dc in menu:
            self.assertEqual(A.resolve_delta(_cell(C.DELTA_ATTACKER), wf, dc), dc.delta_for(wf))
        # the planner never receives the column label
        with self.assertRaises(ValueError):
            A.SCRIPTED["memory-first-write-e0.6"].plan(wf, C.DELTA_ATTACKER)
        with self.assertRaises(ValueError):
            A.br_menu(wf, C.DELTA_ATTACKER)
        # in the attacker column a scripted rule plans at the class's Delta
        att = A.SCRIPTED["skill-first-write-e0.6"]
        for dc in menu:
            got = att.plan_in_cell(wf, _cell(C.DELTA_ATTACKER), delta_class=dc)
            self.assertEqual(got, att.plan(wf, dc.delta_for(wf)))
        # the column's value: the attacker takes the worst class for the defender
        vals = {dc.name: 0.1 * i for i, dc in enumerate(menu)}
        self.assertEqual(A.attacker_delta_value(vals), (vals[menu[-1].name], menu[-1].name))
        tie = {dc.name: 0.5 for dc in menu}
        self.assertEqual(A.attacker_delta_value(tie)[1], menu[0].name)
        with self.assertRaises(ValueError):
            A.attacker_delta_value({menu[0].name: 0.1})


if __name__ == "__main__":
    unittest.main()
