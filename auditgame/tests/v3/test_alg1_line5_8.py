"""Algorithm 1 line 5 (the minimax LP over the restricted library, with its two sources of
L-hat and the rollout engine) and lines 8-9 (quarantine) -- T12: v3/line5.py,
v3/rollout.py, v3/line8.py.

Each test protects the DCM rows of v3/dcm/T12.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  T9's particle filter is written in parallel, so
the belief here is `StubBelief`, a BeliefAPI whose numbers are set by the test and whose
`sample` draws from a fixed list of hypotheses.  Tasks are 0-based.  Run from auditgame/.
"""
import copy
import itertools
import json
import random
import unittest
from unittest import mock

import smallgame
from core import CARRIERS, Task, Workflow
from v3 import api as A
from v3 import attackers as AT
from v3 import baselines as BL
from v3 import config as C
from v3 import library as L
from v3 import line5 as L5
from v3 import line8 as L8
from v3 import oracle as OR
from v3 import payload as P
from v3 import rollout as RO
from v3 import runner as R
from v3 import state as S

TOPICS = ["auth", "cache", "routing", "serializer", "orm", "migration", "views", "admin"]
CELL = C.Cell(rho=0.0, delta=4)                       # a Table 2 headline cell
BAND = L.band_prop61(0.5, 0.2)
CLASSES = AT.attacker_classes()


def _wf(topics=TOPICS, wf_id="wf-t12"):
    return Workflow(wf_id, "repo/t12", [Task(f"{wf_id}-t{t + 1}", "repo/t12", f"{t:07x}", tp,
                                             f"fix {tp}") for t, tp in enumerate(topics)])


def _placement(wf, k="memory", delta=4, iota=0, channel="write"):
    return AT.Placement((next(p for p in P.plan_sleeper_all(wf, k, delta) if p.iota == iota),),
                        channel)


CLEAN = A.Hypothesis(False, (0, 0, 0, 0), None, None)


class StubBelief:
    """A BeliefAPI stand-in: p_poisoned (or a per-task schedule), expected harm and the
    carrier masses are set by the test; `sample` draws uniformly from `hyps`."""

    def __init__(self, p=0.3, harm=0.2, masses=None, hyps=(CLEAN,), schedule=None):
        self.p, self.harm, self.schedule, self.hyps = p, harm, schedule, tuple(hyps)
        self.masses = dict(masses or {"memory": 0.4, "skill": 0.3, "queue": 0.2, "branch": 0.1})
        self.t, self.updates, self.conditioned = 0, [], []

    def update(self, t, obs):
        self.updates.append(t)
        self.t = t + 1

    def condition_on_quarantine(self, t, carrier):
        self.conditioned.append((t, carrier))
        self.masses[carrier] = 0.0

    def p_poisoned(self):
        return self.schedule[min(self.t, len(self.schedule) - 1)] if self.schedule else self.p

    def carrier_mass(self):
        return dict(self.masses)

    def expected_harm(self):
        return self.harm

    def bin_features(self):
        m = self.masses
        return A.BinFeatures(self.p_poisoned(), max(CARRIERS, key=lambda k: m[k]),
                             m["skill"] + m["queue"])

    def sample(self, n, seed):
        rng = random.Random(seed)
        return [self.hyps[rng.randrange(len(self.hyps))] for _ in range(n)]


class AlarmBelief(StubBelief):
    """A StubBelief that reacts: an alarm on a bought audit puts all mass on its carrier
    (p = 1); a quarantine clears it (p = 0).  Enough for line 8 to act inside rollouts."""

    def update(self, t, obs):
        super().update(t, obs)
        if obs.alarm and obs.bought is not None:
            k = C.CARRIER_OF_TARGET[obs.bought.target]
            self.p, self.masses = 1.0, {c: float(c == k) for c in CARRIERS}

    def condition_on_quarantine(self, t, carrier):
        super().condition_on_quarantine(t, carrier)
        self.p = 0.0


class FakeTable:
    """T14's table stand-in: a seeded random L-hat [28 x 6] per key; remembers the keys."""

    def __init__(self, members=L.MEMBERS, classes=CLASSES, fixed=None):
        self.members, self.classes, self.fixed, self.keys = members, classes, fixed, []

    def lookup(self, key):
        self.keys.append(key)
        if self.fixed is not None:
            Lm = self.fixed
        else:
            rng = random.Random(f"t12-table-{key.h}")
            Lm = tuple(tuple(rng.random() for _ in self.classes) for _ in self.members)
        z = tuple(tuple(0.0 for _ in self.classes) for _ in self.members)
        n = tuple(tuple(32 for _ in self.classes) for _ in self.members)
        return A.LossMatrix(tuple(self.members), tuple(self.classes), Lm, z, n, "table")


class FixedMember:
    """A member whose decision is a fixed distribution (for the LP-only tests)."""

    def __init__(self, name, dist):
        self.name, self.dist = name, dict(dist)

    def distribution(self, t):
        return dict(self.dist)


class Line5Policy(A.PolicyBase):
    """The smallest defender that runs line 5 each task (T15 assembles the real one)."""
    name = "line5-test"

    def __init__(self, ctx, source, belief, members):
        super().__init__(ctx)
        self.belief = belief
        lib = L.make_library(ctx, belief=belief, band=BAND)
        self.line5 = L5.Line5(ctx, source, {n: lib[n] for n in members})

    def act(self, t, B_t):
        return self.line5.decide(t, self.belief, B_t, self.ctx.cell.delta).action

    def observe(self, t, obs):
        self.belief.update(t, obs)

    def decision_log(self):
        return list(self.line5.log)


def scipy_value(Lm):
    from scipy.optimize import linprog
    P_, K = len(Lm), len(Lm[0])
    res = linprog(c=[0.0] * P_ + [1.0],
                  A_ub=[[Lm[i][a] for i in range(P_)] + [-1.0] for a in range(K)],
                  b_ub=[0.0] * K, A_eq=[[1.0] * P_ + [0.0]], b_eq=[1.0],
                  bounds=[(0, None)] * P_ + [(None, None)], method="highs")
    return float(res.x[-1])


def coverage_reduction(H, K, delta, m):
    """Smallgame's covering game as a line-5 matrix: members = every pure schedule (one
    carrier or none per task, <= m audits), classes = every (k, iota); loss 1 iff the
    schedule never audits k inside [iota, iota + delta]."""
    pures = [s for s in itertools.product(range(K + 1), repeat=H)
             if sum(1 for a in s if a < K) <= m]
    cfg = smallgame.configs(H, K, delta)
    return [[0.0 if any(s[t] == k for t in range(i, min(i + delta + 1, H))) else 1.0
             for (k, i) in cfg] for s in pures]


def snapshot_at(wf, pl, t, cell=CELL, seed=0):
    ep = R.Episode(wf, pl, BL.factory(BL.B1AuditAtCommit.name), C.PRIMARY, cell, seed)
    while ep.t < t:
        ep.step()
    return ep.snapshot()


class TestAlg1Line58(unittest.TestCase):

    # ---------------------------------------------------------------------------------
    def test_line5_is_argmin_max_over_library_each_task(self):
        """DA1.l5 -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust over a
        restricted library".  D7.br -- "the attacker’s best response within ΠA is computed
        by enumeration over (k, ι, σ), and the defender picks the minimax policy."

        At EVERY task line 5 asks its source for L-hat [28 x 6] once and solves one LP:
        x_t minimises the worst attacker class over the simplex of library members (checked
        against scipy's HiGHS), and is never worse than the best pure member."""
        wf = _wf()
        ctx = R.context(wf, C.PRIMARY, CELL, 3)
        belief = StubBelief()
        table = FakeTable()
        line5 = L5.Line5(ctx, L5.TableSource(table),
                         L.make_library(ctx, belief=belief, band=BAND))
        for t in range(ctx.H):
            d = line5.decide(t, belief, ctx.budget, 4)
            Lm = [list(r) for r in table.lookup(table.keys[-1]).L]
            table.keys.pop()
            self.assertEqual(table.keys[-1].h, ctx.H - t)
            self.assertAlmostEqual(sum(d.x.values()), 1.0, places=9)
            self.assertTrue(all(w >= 0.0 for w in d.x.values()))
            x = [d.x.get(n, 0.0) for n in L.MEMBERS]
            self.assertAlmostEqual(d.value, L5.mixture_value(x, Lm), places=9)
            self.assertAlmostEqual(d.value, scipy_value(Lm), places=7)
            self.assertLessEqual(d.value, min(max(r) for r in Lm) + 1e-12)
            self.assertIn(d.action.target, d.dist)
            self.assertEqual(d.action.depth, ctx.depths[d.action.target])
        self.assertEqual([k.h for k in table.keys], [ctx.H - t for t in range(ctx.H)])
        self.assertEqual(len(line5.log), ctx.H)
        self.assertEqual([e["t"] for e in line5.log], list(range(ctx.H)))

    # ---------------------------------------------------------------------------------
    def test_line5_table_and_rollout_sources_share_one_lp(self):
        """DA1.l5 (Q13) -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust over
        a restricted library".

        The precomputed table (primary, every cell) and real rollouts (headline cells only)
        are two sources of the same L-hat; both go through the one LP (line5.minimax), so
        equal L-hat gives the equal x_t.  The rollout source refuses a non-headline cell."""
        wf = _wf()
        ctx = R.context(wf, C.PRIMARY, CELL, 5)
        rng = random.Random("t12-share")
        Lm = tuple(tuple(rng.random() for _ in CLASSES) for _ in L.MEMBERS)

        class FakeEngine:
            def matrix(self, state, belief, R):
                z = tuple(tuple(0.0 for _ in CLASSES) for _ in L.MEMBERS)
                return A.LossMatrix(L.MEMBERS, CLASSES, Lm, z, z, "rollout")

        st = snapshot_at(wf, _placement(wf), 2)
        rsrc = L5.RolloutSource(FakeEngine(), 16)
        rsrc.bind(st)
        tsrc = L5.TableSource(FakeTable(fixed=Lm))
        out = {}
        with mock.patch.object(L5, "minimax", wraps=L5.minimax) as spy:
            for src in (tsrc, rsrc):
                belief = StubBelief()
                lib = L.make_library(ctx, belief=belief, band=BAND)
                out[src.name] = L5.Line5(ctx, src, lib).decide(2, belief, ctx.budget, 4)
            self.assertEqual(spy.call_count, 2)
        self.assertEqual(out["table"].x, out["rollout"].x)
        self.assertEqual(out["table"].dist, out["rollout"].dist)
        self.assertEqual(out["table"].value, out["rollout"].value)
        self.assertEqual((out["table"].source, out["rollout"].source), ("table", "rollout"))
        # rollouts only in the Table 2 headline cells
        off = C.Cell(rho=0.0, delta=1)
        self.assertFalse(off.is_headline())
        with self.assertRaises(ValueError):
            rsrc.matrix(2, StubBelief(), ctx.budget, 1, R.context(wf, C.PRIMARY, off, 5))
        with self.assertRaises(ValueError):
            L5.RolloutSource(FakeEngine(), 8)                  # R outside the declared grid

    # ---------------------------------------------------------------------------------
    def test_line5_attacker_class_excludes_held_out_behaviour(self):
        """D5.5.freeze -- "Adaptive attack development is performed on a development split,
        and both the defender policy and the attacker library are frozen before final
        evaluation on held-out repositories and held-out attacker policies."

        Line 5's columns are the six D18 tuning classes; the rollout engine uses exactly
        them, none of them can realise a held-out behaviour, and a loss matrix with a
        held-out (or non-tuning) column is refused."""
        eng = RO.RolloutEngine(BAND)
        self.assertEqual(eng.classes, CLASSES)
        self.assertEqual(len(CLASSES), C.N_ATTACKER_CLASSES)
        held = AT.held_out()
        self.assertFalse(set(CLASSES) & set(held))
        held_keys = set().union(*(AT.behavior_keys(AT.SCRIPTED[n]) for n in held))
        for c in CLASSES:
            self.assertFalse(AT.behavior_keys(AT.by_name(c)) & held_keys, c)
        L5.check_classes(CLASSES)
        wf = _wf()
        ctx = R.context(wf, C.PRIMARY, CELL, 5)
        dev_not_tuning = next(n for n in AT.development() if n not in CLASSES)
        for bad in (held[0], dev_not_tuning):
            cols = CLASSES[:-1] + (bad,)
            belief = StubBelief()
            line5 = L5.Line5(ctx, L5.TableSource(FakeTable(classes=cols)),
                             L.make_library(ctx, belief=belief, band=BAND))
            with self.assertRaises(ValueError):
                line5.decide(0, belief, ctx.budget, 4)

    # ---------------------------------------------------------------------------------
    def test_line5_reveals_distribution_not_draw(self):
        """D5.3.rand -- "Sentinel commits to a distribution over audit actions and reveals
        only the distribution."

        The decision log holds x_t and q_t (the action distribution); the draw is keyed on
        the policy's own seed and never logged.  Two members that each cover one class give
        x_t = (1/2, 1/2); the realised audits over 400 policy seeds follow q_t."""
        wf = _wf()
        members = {"L-SW-a": FixedMember("L-SW-a", {"memory": 1.0}),
                   "L-SW-b": FixedMember("L-SW-b", {"commit": 1.0})}
        Lm = ((1.0, 0.0, 1.0, 0.0, 1.0, 0.0), (0.0, 1.0, 0.0, 1.0, 0.0, 1.0))
        table = FakeTable(members=tuple(members), fixed=Lm)
        logs, draws = set(), []
        for s in range(400):
            ctx = R.context(wf, C.PRIMARY, CELL, s)
            line5 = L5.Line5(ctx, L5.TableSource(table), members)
            d = line5.decide(0, StubBelief(), ctx.budget, 4)
            draws.append(d.action.target)
            entry = line5.log[-1]
            self.assertEqual(entry, d.published())
            self.assertEqual(set(entry), {"t", "line", "source", "x", "dist", "value",
                                          "skipped", "note"})
            logs.add(json.dumps(entry, sort_keys=True))
        self.assertEqual(len(logs), 1)                  # the same published x_t every seed
        (entry,) = [json.loads(s) for s in logs]
        self.assertAlmostEqual(entry["x"]["L-SW-a"], 0.5, places=9)
        self.assertAlmostEqual(entry["dist"]["memory"], 0.5, places=9)
        self.assertAlmostEqual(entry["dist"]["commit"], 0.5, places=9)
        share = draws.count("memory") / len(draws)
        self.assertLess(abs(share - 0.5), 0.08)
        self.assertEqual(set(draws), {"memory", "commit"})

    # ---------------------------------------------------------------------------------
    def test_line5_skips_unaffordable_members(self):
        """DA1.req (O14) -- "Require: belief bt , remaining budget Bt , policy library Π".

        The table has no budget key; line 5 drops every member whose decision at t may buy
        an action dearer than B_t and runs the LP over the rest.  With no member left,
        a_t = none."""
        wf = _wf()
        ctx = R.context(wf, C.PRIMARY, CELL, 9)
        kappa = ctx.kappa                              # chi 1.33: 1.2 / 1.8 / 1.6 / 4.1
        belief = StubBelief(p=0.3)
        lib = L.make_library(ctx, belief=belief, band=BAND)
        line5 = L5.Line5(ctx, L5.TableSource(FakeTable()), lib)
        B_t = 2.0
        d = line5.decide(0, belief, B_t, 4)
        dists = {n: m.distribution(0) for n, m in lib.items()}
        dear = {n for n, q in dists.items() if any(p > 0 and kappa[k] > B_t for k, p in q.items())}
        self.assertTrue(dear and dear != set(lib))
        self.assertIn("L-SW-commit", dear)
        self.assertEqual(set(d.skipped), dear)
        self.assertEqual(set(d.members), set(lib) - dear)
        self.assertTrue(set(d.x) <= set(d.members))
        self.assertLessEqual(kappa[d.action.target], B_t)
        self.assertTrue(all(kappa[k] <= B_t for k in d.dist))
        # nothing affordable: none
        d0 = line5.decide(1, belief, min(kappa.values()) - 0.01, 4)
        self.assertIsNone(d0.action)
        self.assertEqual((d0.x, d0.dist, d0.value), ({}, {}, None))
        self.assertEqual(set(d0.skipped), set(lib))
        self.assertIn("O14", d0.note)
        self.assertEqual(C.LINE5_ACTION_WHEN_NONE_AFFORDABLE, "none")
        self.assertFalse(C.TABLE_HAS_BUDGET_KEY)

    # ---------------------------------------------------------------------------------
    def test_line5_matches_exact_minimax_on_coverage_reduction(self):
        """D5.2.oracle -- "Line 3 gives exact solutions on the small games where they are
        computable, which are our validation oracle."  D7.br -- "the attacker’s best
        response within ΠA is computed by enumeration over (k, ι, σ), and the defender picks
        the minimax policy."

        smallgame's covering game written as a line-5 matrix (members = every pure audit
        schedule within the budget, columns = every (k, iota)): line 5's LP gives the exact
        minimax value smallgame.solve computes on the coverage marginals."""
        games = [g for g in smallgame.games()
                 if (g["K"] + 1) ** g["H"] <= 800]
        self.assertGreaterEqual(len(games), 40)
        for g in games:
            Lm = coverage_reduction(g["H"], g["K"], g["delta"], g["m"])
            x, v = L5.minimax(Lm)
            exact = smallgame.solve(g["H"], g["K"], g["delta"], g["m"])["value"]
            self.assertAlmostEqual(v, exact, places=7, msg=str(g))

    # ---------------------------------------------------------------------------------
    def test_line8_quarantines_highest_posterior_carrier_when_tau_and_eta_q_exceeded(self):
        """DA1.l8 -- "if Pr[poisoned | bt +1 ] > τ and expected harm > ηQ then 9: quarantine
        the highest-posterior carrier".

        Above both thresholds line 9 names argmax_k Pr[c[k] = 1 | b] (ties: CARRIERS order),
        conditions the belief on the removal, and the runner removes EVERY live item of it
        (O7)."""
        line8 = L8.Line8(tau=0.5, eta_q=0.1)
        b = StubBelief(p=0.8, harm=0.4, masses={"memory": 0.1, "skill": 0.6, "queue": 0.2,
                                                 "branch": 0.1})
        log = []
        self.assertEqual(line8.quarantine(3, b, log), "skill")
        self.assertEqual(b.conditioned, [(3, "skill")])
        self.assertEqual(log[-1]["quarantine"], "skill")
        tie = StubBelief(p=0.8, harm=0.4, masses={k: 0.25 for k in CARRIERS})
        self.assertEqual(line8.decide(tie), CARRIERS[0])
        # in the runner: the belief crosses tau after task 1; memory holds the payload
        wf = _wf()
        pl = _placement(wf, "memory", 4, 0)
        sched = StubBelief(p=0.0, harm=0.4, masses={"memory": 0.7, "skill": 0.1,
                                                    "queue": 0.1, "branch": 0.1},
                           schedule=[0.1, 0.2, 0.9])

        def factory(ctx):
            m = L.make_member("L-SW-commit", ctx, belief=sched, band=BAND)
            return RO.RolloutPolicy(ctx, m, sched, line8)

        rec = R.Episode(wf, pl, factory, C.PRIMARY, CELL, 0).run().record
        self.assertEqual(rec.quarantines[0], (1, "memory"))
        self.assertGreaterEqual(rec.true_q, 1)
        self.assertEqual(rec.detected_at, 1)
        self.assertEqual(rec.c_traj[1][0], "0")         # memory bit cleared at task 1

    # ---------------------------------------------------------------------------------
    def test_line8_does_nothing_below_tau(self):
        """DA1.l8 -- "if Pr[poisoned | bt +1 ] > τ and expected harm > ηQ then 9: quarantine
        the highest-posterior carrier".

        Both comparisons are strict: at or below tau, or at or below eta_Q, nothing is
        quarantined and the belief is left as it is."""
        line8 = L8.Line8(tau=0.5, eta_q=0.1)
        for p, h in ((0.5, 0.9), (0.2, 0.9), (0.0, 1.0), (0.9, 0.1), (0.9, 0.0)):
            b = StubBelief(p=p, harm=h)
            self.assertIsNone(line8.quarantine(0, b), (p, h))
            self.assertEqual(b.conditioned, [])
        wf = _wf()
        low = StubBelief(p=0.0, harm=0.9, schedule=[0.1, 0.3, 0.5, 0.49])

        def factory(ctx):
            return RO.RolloutPolicy(ctx, L.make_member("L-SW-commit", ctx, band=BAND),
                                    low, line8)

        rec = R.Episode(wf, _placement(wf), factory, C.PRIMARY, CELL, 0).run().record
        self.assertEqual(rec.quarantines, ())

    # ---------------------------------------------------------------------------------
    def test_line5_rollouts_plant_the_particle_not_the_true_poison(self):
        """DA1.l5 (Q13) -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust over
        a restricted library".

        L(pi, pi_A | b_t, B_t) conditions on b_t, not on the truth: a rollout starts from
        the observed store, plants the particle's (c, iota, sigma) (the past) and the
        class's attack (the future).  An attacked snapshot and the same snapshot with every
        evaluator-only fact erased give the same L-hat; the particle moves it."""
        wf = _wf()
        pl = _placement(wf, "memory", 4, 0)
        st = snapshot_at(wf, pl, 2)
        self.assertEqual(st.hidden.c[0], 1)                       # the truth: memory poisoned
        erased = st.clone()
        ep2 = erased.private["episode"]
        for k in CARRIERS:
            for it in ep2.store.items[k]:
                it.poisoned, it.derived_from = False, ()
        ep2.placement = None
        ep2.oracle = OR.SealedOracle(C.PRIMARY, ep2.H, None)
        for tau in range(ep2.t):
            ep2.oracle.task_end(tau, ep2.store, False)
        hyps = (A.Hypothesis(True, (1, 1, 0, 0), 0, 4), A.Hypothesis(True, (0, 0, 0, 0), 5, 7),
                CLEAN)
        members = ("L-SW-commit", "L-SW-uniform", "L-RO-c4-p1-random")
        eng = RO.RolloutEngine(BAND, L8.Line8(0.5, 0.05), members=members)
        b = AlarmBelief(p=0.3, harm=0.2, hyps=hyps)
        m_true = eng.matrix(st, b, 4)
        m_erased = eng.matrix(erased, b, 4)
        self.assertEqual(m_true.L, m_erased.L)
        m_clean = eng.matrix(st, AlarmBelief(p=0.3, harm=0.2, hyps=(CLEAN,)), 4)
        self.assertNotEqual(m_true.L, m_clean.L)
        # what is planted: the past from the particle, the future from the class
        base = RO.observed(st)
        self.assertEqual(S.c_of(base.store), (0, 0, 0, 0))
        ep = copy.deepcopy(base)
        info = RO.plant(ep, hyps[0], AT.by_name("memory-first-write-e0.6"))
        self.assertEqual(info["kind"], "past")
        self.assertEqual(S.c_of(ep.store), (1, 1, 0, 0))
        self.assertEqual((ep.placement.iota, ep.placement.sigma), (0, 4))
        ep = copy.deepcopy(base)
        info = RO.plant(ep, hyps[1], AT.by_name("skill-last-ingress-e0.6"))
        self.assertEqual(info["kind"], "future")
        self.assertEqual(S.c_of(ep.store), (0, 0, 0, 0))
        self.assertEqual((ep.placement.k, ep.placement.channel), (("skill",), "ingress"))
        self.assertGreaterEqual(ep.placement.iota, ep.t)
        self.assertEqual(ep.placement.delta, 2)

    # ---------------------------------------------------------------------------------
    def test_line5_rollouts_run_every_member_against_every_attacker_class(self):
        """DA1.l5 (O13, O12) -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust
        over a restricted library".

        R draws for EVERY (member, attacker class) pair: 28 x 6 x R rollouts, no rollout
        shared across classes (O13: N_A = 1 is not used); the draws are common random
        numbers, so with no attack every class sees the same world.  L-hat carries its SE
        and n = R.  Driven through a whole episode, line 5 takes the rollout source's
        matrix at every task."""
        self.assertFalse(C.N_A_SHARED_ROLLOUT)
        wf = _wf()
        st = snapshot_at(wf, _placement(wf), 3)
        eng = RO.RolloutEngine(BAND, L8.Line8(0.5, 0.05))
        m = eng.matrix(st, StubBelief(hyps=(CLEAN,)), 1)
        self.assertEqual(eng.n_rollouts, len(L.MEMBERS) * len(CLASSES))
        self.assertEqual((m.members, m.classes, m.source), (L.MEMBERS, CLASSES, "rollout"))
        self.assertTrue(all(n == 1 for row in m.n for n in row))
        for row in m.L:                                   # no attack: the class is inert
            self.assertEqual(len(set(row)), 1)
        m2 = RO.RolloutEngine(BAND, members=("L-SW-uniform",)).matrix(
            st, StubBelief(hyps=(A.Hypothesis(True, (1, 0, 0, 0), 0, 4), CLEAN)), 16)
        self.assertTrue(all(n == 16 for n in m2.n[0]))
        self.assertTrue(all(s >= 0.0 for s in m2.se[0]))
        # when b_t reacts to alarms (line 8 can act), members differ
        m3 = RO.RolloutEngine(BAND, L8.Line8(0.5, 0.05),
                              members=("L-SW-commit", "L-SW-skill")).matrix(
            st, AlarmBelief(hyps=(A.Hypothesis(True, (1, 1, 0, 0), 0, 4), CLEAN)), 16)
        self.assertNotEqual(m3.L[0], m3.L[1])
        # a whole episode with line 5 on the rollout source (R = 16, two members)
        wf6 = _wf(TOPICS[:6], "wf-t12-6")
        members = ("L-SW-commit", "L-SW-uniform")
        src = L5.RolloutSource(RO.RolloutEngine(BAND, L8.Line8(0.5, 0.05), members=members), 16)
        belief = StubBelief(hyps=(A.Hypothesis(True, (1, 0, 0, 0), 0, 4), CLEAN))
        ep = R.Episode(wf6, _placement(wf6), lambda ctx: Line5Policy(ctx, src, belief, members),
                       C.PRIMARY, CELL, 0)
        out = RO.drive(ep, src)
        log = ep.policy.decision_log()
        self.assertEqual([e["t"] for e in log], list(range(6)))
        self.assertTrue(all(e["source"] == "rollout" for e in log))
        self.assertEqual(out.record.H, 6)


if __name__ == "__main__":
    unittest.main()
