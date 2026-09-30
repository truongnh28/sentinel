"""Sentinel v3 assembled as Algorithm 1, its Table 3 ablations and V3_REGISTRY (plan T15).

Each test protects the DCM rows of v3/dcm/T15.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  T14's table is built in parallel, so line 5 reads
sentinel.StubTable (a fixed pseudo-random L-hat keyed like T14's table) and T18's tuned
(tau, eta_Q) are placeholders (sentinel.stub_parts).  Tasks are 0-based.  Run from
auditgame/.
"""
import logging
import unittest
from dataclasses import replace

from core import Task, Workflow
from tools import v3_tune as TU
from v3 import api as A
from v3 import attackers as AT
from v3 import baselines as BL
from v3 import config as C
from v3 import corpus as K
from v3 import delta_hat as DH
from v3 import grid as G
from v3 import library as LIB
from v3 import line5 as L5
from v3 import rollout as RO
from v3 import runner as R
from v3 import sentinel as S
from v3 import sequence as SQ

HEADLINE = C.Cell(rho=0.5, delta=4)                   # a Table 2 headline cell
TOPICS = ["auth", "cache", "routing", "serializer"]


def _short_wf(H=4, wf_id="wf-t15"):
    return Workflow(wf_id, "repo/t15", [Task(f"{wf_id}-t{t + 1}", "repo/t15", f"{t:07x}", tp,
                                             f"fix {tp}") for t, tp in enumerate(TOPICS[:H])])


def _dev(n, min_H=5):
    return [w for w in K.dev_workflows() if w.H >= min_H][:n]


def _quiet_line23():
    logging.getLogger("v3.line23").setLevel(logging.ERROR)


def _lines_by_task(trace):
    out = {}
    for t, line in trace:
        if t is not None:
            out.setdefault(t, []).append(line)
    return out


class TestAlg1Sentinel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _quiet_line23()
        cls.parts = S.stub_parts()
        cls.reg = S.registry(cls.parts)

    # ---------------------------------------------------------------------------------
    def test_sentinel_runs_algorithm1_lines_in_order(self):
        """DA1.l1 DA1.l2 DA1.l7 DA1.l8 -- Algorithm 1: "1: b Δ, 𝜒b ← estimate delay and
        heterogeneity from history 2: if game is small (𝐾𝐻 ≤ threshold) then 3: 𝑎𝑡 ← exact
        minimax solution … 7: execute 𝑎𝑡 ; observe 𝑜 𝑡 ; 𝑏𝑡 +1 ← Update(𝑏𝑡 , 𝑎𝑡 , 𝑜 𝑡 , 𝛽)
        8: if Pr[poisoned | 𝑏𝑡 +1 ] > 𝜏 and expected harm > 𝜂𝑄 then 9: quarantine the
        highest-posterior carrier".

        Line 1 once, line 2 once, then per task exactly one of line 3 / line 5, then line 7
        once, then lines 8-9 -- on a small workflow (H = 4, KH = 16: line 3's exact plan)
        and on dev workflows (H >= 6: line 2 logs infeasibility, line 5 decides).  Line 1
        runs through sequence.run_sequence: Delta-hat is the prior before any post-mortem
        and the post-mortems' low quantile after; the record carries the arm-tagged name,
        the policy's delta_hat and its line-5 source."""
        # (a) the small game: lines 2-3
        wf = _short_wf(4)
        cell = C.Cell(rho=0.5, delta=1)
        pl = AT.by_name(AT.held_out()[0]).plan(wf, 1)
        ep = R.Episode(wf, pl, self.reg[S.SENTINEL], C.PRIMARY, cell, 3)
        out = ep.run()
        pol = ep.policy
        self.assertEqual(pol.trace[:2], [(None, "1"), (None, "2")])
        self.assertIsNotNone(pol.line3, "H = 4, K = 4: KH = 16 <= 40 and within the limits")
        by_t = _lines_by_task(pol.trace)
        self.assertEqual(sorted(by_t), list(range(len(wf.tasks))))
        for t, lines in by_t.items():
            self.assertIn(lines, (["3", "7", "8"], ["5", "7", "8"]), (t, lines))
        self.assertEqual(by_t[0][0], "3", "line 3 decides task 0 of a small game")
        self.assertEqual(pol.belief.inner.t_last, 3, "line 7 once per task, in order")
        self.assertEqual(out.record.line5_source, pol.line5_source)
        self.assertIn(out.record.line5_source, ("exact", "table"))
        # line 3 follows line 8: a quarantine it cannot follow takes the history off the plan
        f = S.FollowingLine3(ep.ctx, S.line23_cached(S.model_context(ep.ctx), 1))
        a = f.act(0, ep.ctx.budget)
        f.observe(0, A.Observation(t=0, requested=a, bought=a, alarm=False,
                                   scores=(0.0,) if a else ()))
        f.follow_quarantine(0, "memory")
        self.assertTrue(f.off_tree, "line 8 quarantined where the plan has no response node")

        # (b) dev workflows: line 2 infeasible -> line 5 every task
        for wf in _dev(3, min_H=6):
            pl = AT.by_name(AT.held_out()[1]).plan(wf, HEADLINE.delta)
            ep = R.Episode(wf, pl, self.reg[S.SENTINEL], C.PRIMARY, HEADLINE, 1)
            rec = ep.run().record
            pol = ep.policy
            self.assertIsNone(pol.line3)
            l2 = [e for e in pol.decision_log() if e.get("line") == 2]
            self.assertEqual(len(l2), 1)
            self.assertIn(l2[0]["kind"], ("infeasible", "line5"))
            self.assertIn("line23: infeasible", l2[0].get("record", "line23: infeasible"))
            by_t = _lines_by_task(pol.trace)
            self.assertEqual(by_t, {t: ["5", "7", "8"] for t in range(wf.H)})
            self.assertEqual(pol.belief.inner.t_last, wf.H - 1)
            self.assertEqual((rec.policy, rec.delta_hat, rec.line5_source),
                             (S.SENTINEL, pol.delta_hat, "table"))
            self.assertEqual(sum(1 for e in pol.decision_log() if e.get("line") == 5), wf.H)

        # (c) line 1 through the pinned sequence (C12): prior first, post-mortems after
        wfs = [w for w in _dev(8, min_H=6)][:4]
        by_id = {w.wf_id: w for w in wfs}
        man = SQ.order_manifest([w.wf_id for w in wfs])
        col = AT.held_out()[1]
        for name, arm in ((S.SENTINEL, DH.ARM_POSTMORTEM), (S.ORACLE_DELTA, DH.ARM_ORACLE)):
            key = DH.HistoryKey(C.cell_id(HEADLINE), S.SENTINEL, col, 1)

            def run_one(step, name=name):
                wf = by_id[step.wf_id]
                p = AT.by_name(col).plan(wf, HEADLINE.delta)
                eo = R.run_episode(wf, p, self.reg[name].for_placement(p), C.PRIMARY,
                                   HEADLINE, 1, order=step.order, attack=col,
                                   postmortems=step.postmortems)
                return eo.record, eo.postmortem

            res = SQ.run_sequence(key, man, run_one, arm=arm,
                                  true_delta=(lambda _w: HEADLINE.delta)
                                  if arm == DH.ARM_ORACLE else None)
            self.assertEqual({r.policy for r in res.records}, {name})
            dh = [r.delta_hat for r in res.records]
            if arm == DH.ARM_ORACLE:
                self.assertEqual(set(dh), {HEADLINE.delta})
            else:
                self.assertEqual(dh[0], DH.PRIOR, "no post-mortem yet: the prior (O3)")
                attacked_before = [any(r.iota is not None for r in res.records[:i])
                                   for i in range(len(dh))]
                for i, d in enumerate(dh):
                    self.assertEqual(d, HEADLINE.delta if attacked_before[i] else DH.PRIOR)

    # ---------------------------------------------------------------------------------
    def test_minus_randomization_is_best_deterministic_policy(self):
        """D5.3.rand H12 -- §5.3: "a deterministic allocation is trivially defeated: the
        attacker seeds the carrier the defender is not currently inspecting."

        The -randomization arm is the best DETERMINISTIC policy against the best response,
        not a frozen member: every task, line 5 picks argmin over the point-mass members of
        max over the attacker classes of L-hat, and plays that member's single target -- no
        mixture, no draw, the same action whatever the policy's own seed.  Its worst case
        is never below the minimax mixture's over the same matrix."""
        self.assertIn("L-SW-commit", S.DETERMINISTIC_MEMBERS)
        self.assertEqual(len(S.DETERMINISTIC_MEMBERS), 5)
        wf = _dev(1, min_H=8)[0]
        pl = AT.by_name(AT.held_out()[2]).plan(wf, HEADLINE.delta)
        name = "Sentinel -randomization"
        traces = []
        for rng in (11, 12, 13):
            ctx = replace(R.context(wf, C.PRIMARY, HEADLINE, 1), rng_seed=rng)
            pure, full = self.reg[name](ctx), self.reg[S.SENTINEL](ctx)
            self.assertIsInstance(pure.line5, S.PureLine5)
            self.assertEqual(set(pure.line5.members), set(S.DETERMINISTIC_MEMBERS))
            B = ctx.budget
            acts = []
            for t in range(ctx.H):
                M = pure.source.matrix(t, pure.belief, B, pure.delta_hat, ctx)
                rows = {n: M.L[i] for i, n in enumerate(M.members)}
                a = pure.act(t, B)
                d = pure.line5.log[-1]
                (pick, w), = d["x"].items()
                self.assertEqual(w, 1.0)
                best = min(S.DETERMINISTIC_MEMBERS, key=lambda n: (max(rows[n]),
                                                                    S.DETERMINISTIC_MEMBERS.index(n)))
                self.assertEqual(pick, best, f"t={t}: argmin_pi max_class L-hat over "
                                             f"deterministic members")
                self.assertEqual(list(d["dist"].values()), [1.0])
                self.assertEqual(a.target, next(iter(d["dist"])))
                # the minimax mixture over the full library is never worse
                x, v = L5.minimax([rows[n] for n in M.members])
                self.assertLessEqual(v, max(rows[best]) + 1e-9)
                fa = full.act(t, B)
                pure.observe(t, LIB.scripted_observation(ctx, t, a, alarm=(t == 2)))
                pure.quarantine(t)
                full.observe(t, LIB.scripted_observation(ctx, t, fa, alarm=(t == 2)))
                full.quarantine(t)
                acts.append(a.target)
            traces.append(acts)
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2], "no draw: the action does not read the seed")
        # through the runner: every decision is a point mass
        ep = R.Episode(wf, pl, self.reg[name], C.PRIMARY, HEADLINE, 1)
        ep.run()
        for d in ep.policy.decisions():
            self.assertEqual(list(d["dist"].values()), [1.0])
        # the full Sentinel mixes somewhere on the same episode
        ep2 = R.Episode(wf, pl, self.reg[S.SENTINEL], C.PRIMARY, HEADLINE, 1)
        ep2.run()
        self.assertTrue(any(len(d["dist"]) > 1 for d in ep2.policy.decisions()))

    # ---------------------------------------------------------------------------------
    def test_ablation_changes_at_least_one_decision_in_headline_cell(self):
        """DT3.rand DT3.mem DT3.trans DT3.drift DRQ4.abl -- Table 3 (RQ4) "Full Sentinel − randomization (deterministic) − alarm
        memory (stateless) − transition uncertainty (nominal kernel) − benign-drift
        modelling".

        The shared gate: every arm is run on the same episodes of the headline cell as
        Sentinel and must change at least one decision (the line, the published action
        distribution, or the quarantine) -- -transition in the perturbed-kernel worlds it
        is evaluated in.  An arm that changes none prints NOT EXERCISED, not a zero effect;
        an exact copy of Sentinel is the negative check.  The gate refuses a
        non-headline cell."""
        eps = []
        for wf in _dev(2, min_H=8):
            for col in AT.held_out()[:2]:
                pl = AT.by_name(col).plan(wf, HEADLINE.delta)
                if pl is not None:
                    eps.append((wf, pl, 1))
        self.assertGreaterEqual(len(eps), 3)
        facs = {n: self.reg[n] for n in [S.SENTINEL, *S.ABLATIONS]}
        facs["Sentinel copy"] = S.SentinelFactory(replace(S.SPECS[S.SENTINEL],
                                                          name="Sentinel copy"), self.parts)
        res = S.ablation_gate(facs, eps, HEADLINE)
        lines = S.gate_lines(res)
        self.assertEqual(set(res), set(S.ABLATIONS) | {"Sentinel copy"})
        for n in S.ABLATIONS:
            self.assertTrue(res[n].exercised, res[n].line())
            self.assertNotIn(S.NOT_EXERCISED, res[n].line())
        self.assertEqual(res["Sentinel -transition uncertainty"].worlds, S.PERTURBED_KERNELS)
        self.assertFalse(res["Sentinel copy"].exercised)
        self.assertIn(S.NOT_EXERCISED, res["Sentinel copy"].line())
        self.assertEqual(sum(S.NOT_EXERCISED in ln for ln in lines), 1)
        with self.assertRaises(ValueError):
            S.ablation_gate(facs, eps[:1], C.Cell(rho=0.5, delta=1))

    # ---------------------------------------------------------------------------------
    def test_sentinel_line5_source_is_table_outside_headline(self):
        """Q13 DA1.l5 -- Algorithm 1 line 5: "𝑎𝑡 ← arg min𝜋 ∈Π max𝜋𝐴 ∈Π𝐴 b 𝐿(𝜋, 𝜋𝐴 | 𝑏𝑡 ,
        𝐵𝑡 ) ⊲ robust over a restricted library".

        Q13: the precomputed table is line 5's source in every cell of the primary world,
        headline or not; the rollout source only in the rollout world and only in the
        Table 2 headline cells; Sentinel-rollout refuses the table world.  The record's
        line5_source is the source's name."""
        wf = _dev(1, min_H=6)[0]
        for cell in (C.Cell(rho=0.5, delta=1), C.Cell(rho=0.0, delta=4, chi="2.11"),
                     C.Cell(rho=1.0, delta=8, dprime=1.52), HEADLINE):
            if wf.H < cell.delta + 1:
                continue
            pl = AT.by_name(AT.held_out()[1]).plan(wf, cell.delta)
            ep = R.Episode(wf, pl, self.reg[S.SENTINEL], C.PRIMARY, cell, 1)
            self.assertIsInstance(ep.policy.source, L5.TableSource)
            rec = ep.run().record
            self.assertEqual(rec.line5_source, "table", cell)
        rollout_world = replace(C.PRIMARY, line5="rollout")
        off = C.Cell(rho=0.5, delta=1)
        ctx_off = R.context(wf, rollout_world, off, 1)
        with self.assertRaises(ValueError):
            self.reg[S.SENTINEL](ctx_off)
        with self.assertRaises(ValueError):
            self.reg[S.SENTINEL_ROLLOUT](R.context(wf, C.PRIMARY, HEADLINE, 1))
        # the headline cell in the rollout world: one real line-5 step on rollouts
        parts = S.stub_parts(rollout_members=("L-SW-commit", "L-RO-c4-p1-posterior"),
                             n_particles=256)
        fac = S.registry(parts)[S.SENTINEL_ROLLOUT]
        pl = AT.by_name(AT.held_out()[1]).plan(wf, HEADLINE.delta)
        ep = R.Episode(wf, pl, fac, rollout_world, HEADLINE, 1)
        self.assertIsInstance(ep.policy.source, L5.RolloutSource)
        ep.policy.source.bind(ep.snapshot())
        ep.step()
        self.assertEqual(ep.policy.line5_source, "rollout")
        l5 = [e for e in ep.policy.decision_log() if e.get("line") == 5]
        self.assertEqual(l5[0]["source"], "rollout")
        self.assertLessEqual(set(l5[0]["x"]), {"L-SW-commit", "L-RO-c4-p1-posterior"})

    # ---------------------------------------------------------------------------------
    def test_registry_names_are_unique(self):
        """D7.freeze D7.commit-prov -- §7: "the evaluation harness refuses to run a policy
        whose hash is not in the frozen manifest."  Plan T15: V3_REGISTRY's names are unique, each builds a policy
        of that very name (record.policy = the arm-tagged name), the line-1 arms carry
        their tag (so no oracle number reaches a headline row), the ablations carry the
        grid's names, no name collides with a baseline or a library member, and line 8
        reads T18's tuned block as tools/v3_tune.tuned_for does."""
        names = list(S.V3_REGISTRY)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), 8)
        self.assertFalse(set(names) & set(BL.ALL))
        self.assertFalse(set(names) & set(LIB.MEMBERS))
        for n in S.ABLATIONS:
            self.assertIn(n, G.SENTINEL_CLASS)
        self.assertIn(S.SENTINEL, G.SENTINEL_CLASS)
        self.assertEqual(S.SENTINEL_ROLLOUT, G.SENTINEL_ROLLOUT)
        self.assertEqual(DH.arm_of(S.ORACLE_DELTA), DH.ARM_ORACLE)
        self.assertEqual(DH.arm_of(S.REGIME_PRIOR), DH.ARM_PRIOR)
        self.assertNotIn(S.ORACLE_DELTA, S.HEADLINE_SYSTEMS)
        self.assertNotIn(S.REGIME_PRIOR, S.HEADLINE_SYSTEMS)
        wf = _dev(1, min_H=6)[0]
        ctx = R.context(wf, C.PRIMARY, HEADLINE, 1)
        for n, f in S.registry(self.parts).items():
            self.assertEqual(f.name, n)
            if n == S.SENTINEL_ROLLOUT:
                continue
            p = f(ctx)
            self.assertEqual(p.name, n)
            self.assertIsInstance(p, A.PolicyV3)
            self.assertTrue(hasattr(p, "delta_hat") and hasattr(p, "line5_source"))
            self.assertIs(p.reads_provenance, True, "fix-a7: Sentinel's commit review reads "
                          "provenance in A7, as B1-prov's does")
        tuned = S.placeholder_tuned(0.3, 0.1)
        for rho in C.RHO_GRID:
            self.assertEqual(S.tuned_block(tuned, rho), TU.tuned_for(tuned, rho))
        with self.assertRaises(S.PartMissing):
            S.Parts(table=S.StubTable()).line8(0.5)


if __name__ == "__main__":
    unittest.main()
