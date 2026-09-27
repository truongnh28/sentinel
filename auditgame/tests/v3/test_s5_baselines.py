"""The v3 baselines and controls (T8, v3/baselines.py).  Each test protects the DCM rows of
v3/dcm/T08.csv that name it; its docstring carries the id(s) and the verbatim draft
sentence.  The runner (T6) is not used: `drive` below plays its budget rule (buy iff
sum kappa + kappa(a_t) <= B, plan T6) and hands the policy a synthetic o_t."""
import inspect
import math
import unittest
from collections import Counter

import carrier_policies as CP
from v3 import api as A
from v3 import baselines as BL
from v3 import config as C

HS = range(6, 15)                                       # draft S8: H ~ U{6..14}


def ctx_for(cell=None, *, H=10, budget=None, world=C.PRIMARY, rng_seed=7, depths=None,
            kappa=None, postmortems=()):
    """The EpisodeContext the runner builds for one episode.  Budget b1 = H x the cell's
    commit price (4.1 H in every chi cell, plan S1)."""
    cell = cell or C.Cell(rho=0.0, delta=4)
    depths = dict(depths or cell.depths())
    kappa = dict(kappa or cell.kappa())
    if budget is None:
        budget = H * kappa["commit"]
    return A.EpisodeContext(world=world, cell=cell, wf_id="wf-test", seed=1, H=H,
                            budget=budget, depths=depths, kappa=kappa,
                            delegated=cell.delegated(), postmortems=tuple(postmortems),
                            rng_seed=rng_seed)


def obs(t, bought, *, alarm=False, scores=None, provenance=None):
    scores = (1.0,) if scores is None and bought is not None else (scores or ())
    return A.Observation(t=t, requested=bought, bought=bought, scores=tuple(scores),
                         alarm=alarm, written_at=tuple(range(len(scores))), checkpoint=True,
                         provenance=provenance)


def drive(pol, ctx, alarm_at=lambda t, a: False, provenance_at=lambda t: None):
    """Play one episode's defender loop.  Returns [(t, requested, bought, quarantined)]."""
    spent, out = 0.0, []
    for t in range(ctx.H):
        a = pol.act(t, ctx.budget - spent)
        bought = None
        if a is not None:
            price = ctx.kappa[a.target] / ctx.depths[a.target] * a.depth   # linear in depth
            if spent + price <= ctx.budget * (1 + 1e-9):
                spent += price
                bought = a
        alarm = bought is not None and alarm_at(t, bought)
        pol.observe(t, obs(t, bought, alarm=alarm, scores=(4.0,) if alarm else (0.0,),
                           provenance=provenance_at(t) if bought is not None else None))
        out.append((t, a, bought, pol.quarantine(t)))
    return out, spent


def every_cell():
    for chi in C.CHI_LEVELS:
        for rho in C.RHO_GRID:
            yield C.Cell(rho=rho, delta=4, chi=chi)


class TestS5Baselines(unittest.TestCase):

    # ---- B1 ----------------------------------------------------------------------------

    def test_b1_audits_the_commit_of_every_task(self):
        """D5.2.b1 (C4, C16, O6): "Audit-at-Commit spends the entire budget inspecting the
        final commit of each task at maximum depth."

        At b1 every task's commit is bought at the cell's commit depth (1 in every chi
        cell, R7), and the whole budget is spent."""
        for cell in every_cell():
            for H in HS:
                ctx = ctx_for(cell, H=H)
                pol = BL.make_baseline("B1 audit-at-commit", ctx)
                steps, spent = drive(pol, ctx)
                self.assertEqual([s[1] for s in steps], [A.AuditAction("commit", 1)] * H)
                self.assertEqual([s[2] for s in steps], [s[1] for s in steps], "all bought")
                self.assertAlmostEqual(spent, ctx.budget, places=9)
                self.assertAlmostEqual(spent, 4.1 * H, places=9)

    def test_b1_lowers_commit_depth_evenly_when_budget_binds(self):
        """D5.2.b1 (Q8, O6, H18): "Audit-at-Commit spends the entire budget inspecting the
        final commit of each task at maximum depth."

        When B binds, B1 lowers its commit depth evenly while it is above 1, then drops
        commits at evenly spaced tasks; it never asks for what B cannot buy.  "Spend until
        exhausted, then stop" is the declared sensitivity."""
        # (a) a commit deeper than 1 (no chi cell has one, R7): depths even, differing by <= 1
        deep = {"memory": 1, "queue": 1, "skill": 1, "commit": 3}
        kap = {"memory": 0.4, "queue": 0.9, "skill": 1.6, "commit": 3 * 4.1}
        for H in HS:
            for units in range(H, 3 * H + 1):
                ctx = ctx_for(H=H, depths=deep, kappa=kap, budget=units * 4.1)
                pol = BL.make_baseline("B1 audit-at-commit", ctx)
                steps, spent = drive(pol, ctx)
                d = [s[2].depth for s in steps]
                self.assertEqual([s[1] for s in steps], [s[2] for s in steps], "never refused")
                self.assertEqual(sum(d), units, (H, units))
                self.assertLessEqual(max(d) - min(d), 1, (H, units, d))
                self.assertLessEqual(spent, ctx.budget * (1 + 1e-9))
        self.assertEqual(BL.b1_plan(10, 25 * 4.1, 3, 4.1), [2, 3] * 5)
        # (b) depth 1 already: drop the commit at evenly spaced tasks
        for cell in every_cell():
            for H in HS:
                for kept in range(0, H + 1):
                    ctx = ctx_for(cell, H=H, budget=kept * 4.1)
                    steps, spent = drive(BL.make_baseline("B1 audit-at-commit", ctx), ctx)
                    got = [s[1] for s in steps]
                    self.assertEqual([s[2] for s in steps], got, "never refused")
                    self.assertEqual(sum(a is not None for a in got), kept)
                    self.assertTrue(all(a is None or a == A.AuditAction("commit", 1) for a in got))
                    dropped = [t for t, a in enumerate(got) if a is None]
                    self.assertEqual(dropped, BL.evenly_spaced(H, H - kept))
                    gaps = [b - a for a, b in zip(dropped, dropped[1:])]
                    if gaps:
                        self.assertLessEqual(max(gaps) - min(gaps), 1, (H, kept, dropped))
        self.assertEqual(BL.b1_plan(10, 5 * 4.1, 1, 4.1), [1, 0] * 5)
        self.assertEqual(BL.b1_plan(10, 0.0, 1, 4.1), [0] * 10)
        # (c) the sensitivity: the cell's depth while affordable, then nothing
        ctx = ctx_for(H=10, budget=6 * 4.1)
        steps, _ = drive(BL.make_baseline("B1 audit-at-commit (exhaust)", ctx), ctx)
        self.assertEqual([s[2] is not None for s in steps], [True] * 6 + [False] * 4)
        self.assertEqual(C.B1_BINDING_RULE, ("lower-depth-evenly-while-above-1",
                                             "drop-commit-at-evenly-spaced-tasks"))

    # ---- lines 8-9 for baselines ---------------------------------------------------------

    def test_baselines_quarantine_whole_carrier_on_alarm(self):
        """D4.quarantine (O7): "may additionally quarantine (cost ηQ , removes a carrier)
        or continue."  D4.drift: "This is what makes the belief update non-trivial and what
        prevents “quarantine on any anomaly” from being optimal."

        A baseline quarantines on any anomaly: the whole audited carrier -- the branch for
        a commit alarm.  No alarm, nothing bought, or a stale o_t: no quarantine.  B6
        quarantines on its confirmation only."""
        ctx = ctx_for(H=12)
        for name in BL.BASELINES:
            if name == "B6 two-stage":
                continue
            steps, _ = drive(BL.make_baseline(name, ctx), ctx, alarm_at=lambda t, a: t % 2 == 0)
            for t, _req, bought, q in steps:
                want = C.CARRIER_OF_TARGET[bought.target] if t % 2 == 0 else None
                self.assertEqual(q, want, (name, t, bought))
            pol = BL.make_baseline(name, ctx)
            a = pol.act(0, ctx.budget)
            pol.observe(0, obs(0, None))
            self.assertIsNone(pol.quarantine(0), f"{name}: nothing bought")
            pol.observe(0, obs(0, a, alarm=True))
            self.assertIsNone(pol.quarantine(1), f"{name}: o_t is from another task")
            self.assertEqual(pol.quarantine(0), C.CARRIER_OF_TARGET[a.target])
        # B6: the screen alarm asks for a confirmation of the same carrier; its alarm quarantines
        pol = BL.make_baseline("B6 two-stage", ctx)
        a0 = pol.act(0, ctx.budget)
        pol.observe(0, obs(0, a0, alarm=True))
        self.assertIsNone(pol.quarantine(0))
        a1 = pol.act(1, ctx.budget)
        self.assertEqual(a1, a0)
        pol.observe(1, obs(1, a1, alarm=True))
        self.assertEqual(pol.quarantine(1), C.CARRIER_OF_TARGET[a0.target])
        self.assertEqual(C.CARRIER_OF_TARGET["commit"], "branch")

    # ---- cost-greedy, randomised stage-weighted -----------------------------------------

    def test_cost_greedy_audits_cheap_carriers_more(self):
        """D10.1.greedy (H6): "a cost-greedy allocator that audits cheap carriers more is
        beaten by an attacker who inserts into the expensive one"

        Each task a target with probability proportional to 1/kappa at the cell's depth:
        the cheaper the audit, the more often it runs; the commit, dearest in every cell,
        least."""
        for cell in every_cell():
            ctx = ctx_for(cell, H=14)
            dist = BL.make_baseline("cost-greedy", ctx).distribution()
            kap = cell.kappa()
            inv = {k: 1 / kap[k] for k in C.TARGETS}
            for k in C.TARGETS:
                self.assertAlmostEqual(dist[k], inv[k] / sum(inv.values()), places=12)
            by_price = sorted(C.TARGETS, key=lambda k: kap[k])
            self.assertEqual(sorted(C.TARGETS, key=lambda k: -dist[k]), by_price)
            self.assertEqual(min(dist, key=dist.get), "commit")
        # realised draws follow the distribution (chi = 2.11: memory 0.4 ... commit 4.1)
        cell = C.Cell(rho=0.0, delta=4, chi="2.11")
        n, freq = 0, Counter()
        for seed in range(300):
            ctx = ctx_for(cell, H=14, rng_seed=seed)
            steps, _ = drive(BL.make_baseline("cost-greedy", ctx), ctx)
            freq.update(s[1].target for s in steps)
            n += len(steps)
        dist = BL.make_baseline("cost-greedy", ctx_for(cell)).distribution()
        for k in C.TARGETS:
            se = math.sqrt(dist[k] * (1 - dist[k]) / n)
            self.assertLess(abs(freq[k] / n - dist[k]), 4 * se, k)
        self.assertEqual([k for k, _ in freq.most_common()], ["memory", "queue", "skill", "commit"])

    def test_randomised_stage_weighted_draws_by_declared_weights(self):
        """D11.sw (H17): "randomizing a simple stage-weighted policy captures more than half
        of Sentinel’s benefit at a fraction of the engineering cost."

        The weights are v2's stage-weighted vectors (carrier_policies._SW); the choice is
        T18's, on dev, with a declared placeholder until then.  No belief; the draw depends
        on the policy's own seed only."""
        self.assertEqual(BL.SW_WEIGHTS, CP._SW)
        self.assertIn(BL.SW_DEFAULT, CP._SW)
        ctx = ctx_for(H=14)
        for key, w in CP._SW.items():
            pol = BL.make_baseline("SW randomised", ctx, tuned={"sw_weights": key})
            dist = pol.distribution()
            for k, wk in zip(C.TARGETS, w):
                self.assertAlmostEqual(dist[k], wk / sum(w), places=12)
            steps, _ = drive(pol, ctx)
            self.assertTrue(all(dist[s[1].target] > 0 for s in steps), key)
        with self.assertRaises(ValueError):
            BL.make_baseline("SW randomised", ctx, tuned={"sw_weights": "nope"})
        a = [s[1] for s in drive(BL.make_baseline("SW randomised", ctx_for(H=14, rng_seed=3)),
                                 ctx_for(H=14, rng_seed=3))[0]]
        b = [s[1] for s in drive(BL.make_baseline("SW randomised", ctx_for(H=14, rng_seed=3)),
                                 ctx_for(H=14, rng_seed=3))[0]]
        self.assertEqual(a, b, "same seed, same draws")
        log = BL.make_baseline("SW randomised", ctx)
        log.act(0, ctx.budget)
        entry = log.decision_log()[-1]
        self.assertEqual(set(entry), {"t", "dist", "target"}, "distribution and draw, no seed")

    # ---- B2-B6 ---------------------------------------------------------------------------

    def test_b2_spreads_uniformly_over_every_stage_and_task(self):
        """D5.6.b2: "Spreading the budget uniformly over every stage and task avoids the
        belief machinery entirely."

        Equal coverage, not equal spending: each task one of the four targets with
        probability 1/4, whatever the prices."""
        for cell in every_cell():
            dist = BL.make_baseline("B2 uniform random", ctx_for(cell)).distribution()
            self.assertEqual(dist, {k: 0.25 for k in C.TARGETS})
        n, freq = 0, Counter()
        for seed in range(250):
            ctx = ctx_for(H=12, rng_seed=seed)
            steps, _ = drive(BL.make_baseline("B2 uniform random", ctx), ctx)
            freq.update(s[1].target for s in steps)
            n += len(steps)
        se = math.sqrt(0.25 * 0.75 / n)
        for k in C.TARGETS:
            self.assertLess(abs(freq[k] / n - 0.25), 4 * se, k)

    def test_b3_b4_audit_one_fixed_carrier(self):
        """D9.2.b3: "(B3) Audit-on-insertion."  D9.2.b4: "(B4) Audit-on-retrieval."

        The insertion audit is the memory carrier's, the retrieval audit the queue
        carrier's (D2 of v2), every task."""
        for cell in every_cell():
            ctx = ctx_for(cell, H=9)
            for name, target in (("B3 audit-on-insertion", "memory"),
                                 ("B4 audit-on-retrieval", "queue")):
                steps, _ = drive(BL.make_baseline(name, ctx), ctx, alarm_at=lambda t, a: t == 3)
                self.assertEqual({s[1].target for s in steps}, {target}, name)

    def test_b5_escalates_to_commit_after_score_exceeds_tuned_threshold(self):
        """D9.2.b5 (D12): "(B5) Risk-score thresholding: audit…when the detector’s score
        exceeds a tuned threshold."

        Sweeps memory, queue, skill in turn; on the task after a sweep whose carrier score
        (the v2 carrier posterior at the cell's depth) passes tau5, the commit.  tau5 is
        tuned on dev (T18); 0.3 until then."""
        self.assertEqual(BL.TAU5_DEFAULT, 0.3)
        ctx = ctx_for(H=10)
        pol = BL.make_baseline("B5 risk-score", ctx)
        self.assertEqual(pol.tau5, 0.3)
        seen = []
        for t in range(6):
            a = pol.act(t, ctx.budget)
            seen.append(a.target)
            hot = (4.0,) if t == 1 else (-1.0, 0.0)
            pol.observe(t, obs(t, a, scores=hot if a.target != "commit" else (0.0,)))
        self.assertEqual(seen, ["memory", "queue", "commit", "memory", "queue", "skill"])
        # the threshold is a parameter: at tau5 = 1 nothing escalates
        pol = BL.make_baseline("B5 risk-score", ctx, tuned={"tau5": 1.0})
        for t in range(6):
            a = pol.act(t, ctx.budget)
            self.assertNotEqual(a.target, "commit")
            pol.observe(t, obs(t, a, scores=(4.0,)))
        # an empty carrier is no evidence: no escalation
        pol = BL.make_baseline("B5 risk-score", ctx, tuned={"tau5": 0.0})
        a = pol.act(0, ctx.budget)
        pol.observe(0, obs(0, a, scores=()))
        self.assertEqual(pol.act(1, ctx.budget).target, "queue")

    def test_b6_confirms_the_screened_carrier_before_quarantine(self):
        """D9.2.b6: "contracts-inspired two-stage check [1]."

        A screen of a sweep carrier drawn uniformly; its alarm is confirmed on the same
        carrier the next task, and only a confirmed alarm quarantines."""
        for seed in range(40):
            c = ctx_for(H=14, rng_seed=seed)
            steps, _ = drive(BL.make_baseline("B6 two-stage", c), c,
                             alarm_at=lambda t, a: t in (2, 3, 7))
            by_t = {s[0]: s for s in steps}
            self.assertEqual(by_t[3][1], by_t[2][1], "t=3 confirms the carrier screened at t=2")
            self.assertIsNone(by_t[2][3])
            self.assertEqual(by_t[3][3], C.CARRIER_OF_TARGET[by_t[2][1].target])
            self.assertIsNone(by_t[7][3], "a screen alarm alone does not quarantine")
            self.assertEqual(by_t[8][1], by_t[7][1])
            self.assertTrue(all(s[1].target in BL.SWEEP_TARGETS for s in steps))
        self.assertEqual(BL.SWEEP_TARGETS, ("memory", "queue", "skill"))

    # ---- B1-prov (C1) --------------------------------------------------------------------

    def test_b1_prov_reads_provenance_only_in_a7(self):
        """D1.attribution (C1, O9): "An audit that observes only the artifact cannot distinguish
        “this patch is the product of a poisoned skill” from “this patch is ordinary”,
        because the distinguishing evidence is the skill’s provenance."

        B1-prov is B1 whose commit alarm also reads the provenance score of the
        contributing skills (A7) against the cell detector's threshold (O9).  In A0 there
        is no provenance and B1-prov behaves as B1."""
        a7 = C.sensitivities()[0][1]
        self.assertEqual(a7.provenance, "A7")
        for cell in every_cell():
            tau = cell.detector().tau_det
            for world, prov in ((a7, tau + 0.5), (C.PRIMARY, None)):
                ctx = ctx_for(cell, H=8, world=world)
                p_steps, _ = drive(BL.make_baseline("B1-prov", ctx), ctx,
                                   provenance_at=lambda t: prov if t == 4 else None)
                b_steps, _ = drive(BL.make_baseline("B1 audit-at-commit", ctx), ctx,
                                   provenance_at=lambda t: prov if t == 4 else None)
                self.assertEqual([s[1] for s in p_steps], [s[1] for s in b_steps])
                self.assertTrue(all(s[3] is None for s in b_steps), "B1 ignores provenance")
                want = "branch" if prov is not None else None
                self.assertEqual(p_steps[4][3], want, world.provenance)
                self.assertTrue(all(s[3] is None for s in p_steps if s[0] != 4))
            # below the threshold, no provenance alarm
            ctx = ctx_for(cell, H=8, world=a7)
            steps, _ = drive(BL.make_baseline("B1-prov", ctx), ctx,
                             provenance_at=lambda t: tau - 0.5)
            self.assertTrue(all(s[3] is None for s in steps))

    # ---- controls (D28) ------------------------------------------------------------------

    def test_oracle_control_is_told_the_attacked_carrier_only(self):
        """D1.oracle (D28): "evaluator-known carrier/trigger state"

        The positive control is given the seeded carrier(s) and nothing else of the
        evaluator's state (no iota, sigma, payload), audits it every task, and is a
        control, not a competitor."""
        params = list(inspect.signature(BL.OracleControl.__init__).parameters)
        self.assertEqual(params, ["self", "ctx", "attacked"])
        self.assertNotIn("Oracle (+)", BL.BASELINES)
        self.assertIn("Oracle (+)", BL.CONTROLS)
        ctx = ctx_for(H=10)
        for k in C.CARRIERS:
            steps, _ = drive(BL.make_baseline("Oracle (+)", ctx, attacked=(k,)), ctx)
            want = "commit" if k == "branch" else k
            self.assertEqual({s[1].target for s in steps}, {want}, k)
            self.assertEqual(BL.make_baseline("Oracle (+)", ctx, attacked=k).act(0, 1e9).target,
                             want)
        steps, _ = drive(BL.make_baseline("Oracle (+)", ctx, attacked=("memory", "skill")), ctx)
        self.assertEqual([s[1].target for s in steps], ["memory", "skill"] * 5)
        steps, _ = drive(BL.make_baseline("Oracle (+)", ctx), ctx)
        self.assertEqual({s[1].target for s in steps}, {"commit"}, "no attack: the commit")
        with self.assertRaises(ValueError):
            BL.make_baseline("Oracle (+)", ctx, attacked=("payload",))
        for name in BL.BASELINES:
            with self.assertRaises(ValueError, msg=name):
                BL.make_baseline(name, ctx, attacked=("memory",))
        # its actions do not move with anything but the carrier: post-mortems, seeds, alarms
        pm = A.PostMortem(cell_id="x", wf_id="w0", order=0, seed=1, k=("skill",), iota=2,
                          sigma=6, harm=1.0, H=10)
        ref = [s[1] for s in drive(BL.make_baseline("Oracle (+)", ctx, attacked="queue"), ctx)[0]]
        for c in (ctx_for(H=10, postmortems=(pm,)), ctx_for(H=10, rng_seed=99)):
            got = [s[1] for s in drive(BL.make_baseline("Oracle (+)", c, attacked="queue"), c,
                                       alarm_at=lambda t, a: True)[0]]
            self.assertEqual(got, ref)

    def test_delta_zero_control_sweep_only_baselines_never_audit_commit(self):
        """D10.1.delta0 (D28, plan S7): "At Δ = 0—the trigger fires in the same task as
        insertion—adaptive allocation is worse than commit-time audit by 1.2%, because it
        spends budget upstream where there is nothing yet to find."

        The negative control is the Delta = 0 cell with B1 as the reference; SWEEP_ONLY
        names the baselines that never audit the commit, whatever they observe."""
        self.assertEqual(BL.DELTA0_CONTROL, {"delta": 0, "reference": "B1 audit-at-commit"})
        for name in BL.BASELINES:
            targets = set()
            for seed in range(30):
                cell = C.Cell(rho=0.0, delta=0, chi=C.CHI_LEVELS[seed % 3])
                ctx = ctx_for(cell, H=14, rng_seed=seed)
                steps, _ = drive(BL.make_baseline(name, ctx), ctx,
                                 alarm_at=lambda t, a, s=seed: (t + s) % 3 == 0)
                targets |= {s[1].target for s in steps if s[1] is not None}
            self.assertEqual("commit" not in targets, name in BL.SWEEP_ONLY, (name, targets))

    # ---- C16 -----------------------------------------------------------------------------

    def test_depth_is_fixed_by_cell_for_every_policy(self):
        """D8.chi (C16): "carrier heterogeneity χ ∈ {0, 0.5, 1.34} (achieved by equalising
        or differentiating audit depths)"

        A policy chooses the target; the depth is the cell's, for every system and every
        chi cell at b1 (B1's O6 rule acts only when the budget binds).  The price-only arm
        keeps the primary depths."""
        names = list(BL.ALL)
        for cell in every_cell():
            for name in names:
                for seed in range(8):
                    ctx = ctx_for(cell, H=14, rng_seed=seed)
                    kw = {"attacked": ("skill",)} if name == "Oracle (+)" else {}
                    steps, _ = drive(BL.make_baseline(name, ctx, **kw), ctx,
                                     alarm_at=lambda t, a, s=seed: (t * 7 + s) % 4 == 0)
                    for t, a, _b, _q in steps:
                        self.assertIsNotNone(a, (name, t))
                        self.assertEqual(a.depth, cell.depths()[a.target], (name, cell.chi, t))
        po = C.Cell(rho=0.25, delta=4, chi="2.11", price_only=True)
        self.assertEqual(po.depths(), C.Cell(rho=0.25, delta=4).depths())
        kap = {"memory": 1.0, "queue": 2.0, "skill": 3.0, "commit": 4.1}   # any price-only prices
        ctx = ctx_for(po, H=10, kappa=kap)
        for name in names:
            kw = {"attacked": ("queue",)} if name == "Oracle (+)" else {}
            steps, _ = drive(BL.make_baseline(name, ctx, **kw), ctx)
            self.assertTrue(all(a.depth == po.depths()[a.target] for _t, a, _b, _q in steps), name)


if __name__ == "__main__":
    unittest.main()
