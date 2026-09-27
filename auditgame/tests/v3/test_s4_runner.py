"""Draft S4 "Defender" and "Payoffs" on the v3 runner and sealed oracle (T6: v3/runner.py,
v3/oracle.py).

Each test protects the DCM rows of v3/dcm/T06.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  Tasks are 0-based (task number = t + 1), as in
v2's carrier_runner.  Run from auditgame/.
"""
import unittest
from dataclasses import replace

import carrier_runner
import metrics as V2M
from core import Task, Workflow
from v3 import agent as AG
from v3 import api as A
from v3 import attackers as AT
from v3 import baselines as B
from v3 import config as C
from v3 import corpus as K
from v3 import oracle as OR
from v3 import payload as P
from v3 import runner as R
from v3 import seal

TOPICS = ["auth", "cache", "routing", "serializer", "orm", "migration", "views", "admin"]
CELL = C.Cell(rho=0.0, delta=4)


def _wf(topics=TOPICS, wf_id="wf-t6"):
    return Workflow(wf_id, "repo/t6", [Task(f"{wf_id}-t{t + 1}", "repo/t6", f"{t:07x}", tp,
                                            f"fix {tp}") for t, tp in enumerate(topics)])


def _placement(wf, k="memory", delta=4, iota=0, channel="write", second=None):
    pays = [next(p for p in P.plan_sleeper_all(wf, k, delta) if p.iota == iota)]
    if second is not None:
        pays.append(next(p for p in P.plan_sleeper_all(wf, second, delta) if p.iota == iota))
    return AT.Placement(tuple(pays), channel)


def _sure_agent(world, cell):
    """Adoption 1, no skill, no queue, no drift: a marked DIRECT patch at sigma whenever the
    note is live, so a harm path is followed without hunting draws."""
    return AG.SleeperMockAgent(adoption_rate=1.0, skill_induction_rate=0.0, queue_rate=0.0,
                               drift_rates={}, delegated=cell.delegated(),
                               drift=world.drift, ingress_visible=world.ingress_visible)


def _surviving_seed(wf, pl):
    """The first seed whose task sigma is solved (N4: harm needs a solved patch)."""
    return next(s for s in range(1000) if carrier_runner.survives(wf, pl.payloads[0], s))


class Script(A.PolicyBase):
    """A scripted defender: acts[t] (target or AuditAction), quarantines[t] (carrier).
    Remembers every act call and observation."""
    name = "script"

    def __init__(self, ctx, acts=None, quarantines=None):
        super().__init__(ctx)
        self.acts, self.quars = dict(acts or {}), dict(quarantines or {})
        self.calls, self.obs = [], {}

    def act(self, t, B_t):
        self.calls.append((t, B_t))
        a = self.acts.get(t)
        if isinstance(a, str):
            a = self.action(a)
        self._log.append({"t": t, "a": None if a is None else [a.target, a.depth]})
        return a

    def observe(self, t, obs):
        self.obs[t] = obs

    def quarantine(self, t):
        return self.quars.get(t)


def script(**kw):
    return lambda ctx: Script(ctx, **kw)


class TestS4Runner(unittest.TestCase):

    def run_ep(self, wf, pl, factory, world=C.PRIMARY, cell=CELL, seed=0, **kw):
        return R.Episode(wf, pl, factory, world, cell, seed, **kw).run()

    # ---------------------------------------------------------------------------------
    def test_one_action_per_task_within_budget(self):
        """D4.defender -- "At each task the defender chooses an audit action at ∈ A = {none}
        ∪ {(audit, k, depth)} with cost κ (k, depth)" subject to sum_t kappa(a_t) <= B:
        act is called once per task, t = 0..H-1 (task number = t + 1, v2's carrier_runner),
        with the remaining budget; an action is bought iff it fits, else nothing."""
        wf = _wf()
        H = len(wf.tasks)
        kappa = CELL.kappa()
        # a budget for exactly 3 commits
        budget = 3 * kappa["commit"] + 0.5 * kappa["commit"]
        eps = []

        def fac(ctx):
            p = Script(ctx, acts={t: "commit" for t in range(H)})
            eps.append(p)
            return p
        out = self.run_ep(wf, None, fac, budget=budget)
        pol = eps[0]
        self.assertEqual([t for t, _ in pol.calls], list(range(H)), "one act per task, 0-based")
        self.assertEqual(pol.calls[0][1], budget)
        for (t, b), (t2, b2) in zip(pol.calls, pol.calls[1:]):
            self.assertLessEqual(b2, b)
        self.assertEqual(out.record.audits["commit"], [0, 1, 2])
        self.assertLessEqual(out.record.spent, budget + 1e-9)
        self.assertAlmostEqual(out.record.spent, 3 * kappa["commit"])
        for t in range(H):
            o = pol.obs[t]
            self.assertEqual(o.t, t)
            self.assertEqual(o.requested, A.AuditAction("commit", 1))
            self.assertEqual(o.bought is not None, t < 3, "bought iff affordable, no fallback")
        # the whole budget of the cell: every task can buy its commit (C4, b1)
        out = self.run_ep(wf, None, script(acts={t: "commit" for t in range(H)}))
        self.assertEqual(out.record.audits["commit"], list(range(H)))
        self.assertAlmostEqual(out.record.spent, H * kappa["commit"])
        self.assertAlmostEqual(out.record.budget, H * kappa["commit"])
        # a cheaper audit costs unit price x depth (Q6); a deeper one than the cell's is refused
        out = self.run_ep(wf, None, script(acts={0: A.AuditAction("memory", 2)}))
        self.assertAlmostEqual(out.record.spent, 2 * C.KAPPA_UNIT["memory"])
        with self.assertRaises(ValueError):
            self.run_ep(wf, None, script(acts={0: A.AuditAction("commit", 2)}))
        with self.assertRaises(ValueError):
            self.run_ep(wf, None, script(acts={0: A.AuditAction("branch", 1)}))

    # ---------------------------------------------------------------------------------
    def test_quarantine_removes_whole_carrier(self):
        """D4.quarantine -- "may additionally quarantine (cost ηQ , removes a carrier) or
        continue.": lines 8-9 remove EVERY live item of the named carrier, poisoned or not,
        and c_t[k] drops to 0."""
        wf = _wf()
        pl = _placement(wf, "memory")
        ep = R.Episode(wf, pl, script(quarantines={2: "memory"}), C.PRIMARY, CELL, 3)
        for _ in range(2):
            ep.step()
        before = ep.store.live("memory")
        self.assertGreaterEqual(len(before), 2)
        self.assertTrue(any(it.poisoned for it in before))
        self.assertEqual(ep.c_traj[-1][0], "1")
        ep.step()                                       # t = 2: the agent writes, then lines 8-9
        self.assertEqual(ep.store.live("memory"), [])
        self.assertEqual(ep.c_traj[-1][0], "0")
        self.assertEqual(ep.quarantines, [(2, "memory")])
        n_removed = sum(1 for it in ep.store.items["memory"] if it.item_id in ep.store.quarantined)
        self.assertEqual(n_removed, len(ep.store.items["memory"]))
        out = ep.run()
        self.assertEqual(out.record.true_q, 1)
        self.assertEqual(out.record.fq, 0)
        self.assertEqual(out.record.detected_at, 2)
        self.assertEqual(out.record.false_removed, len(before))      # the benign notes too
        with self.assertRaises(ValueError):
            self.run_ep(wf, pl, script(quarantines={0: "commit"}))   # a target, not a carrier

    # ---------------------------------------------------------------------------------
    def test_harm_read_at_horizon_end(self):
        """D4.payoff -- "with verified harm measured by a sealed oracle at the end of the
        horizon": the oracle reveals nothing before the last task has ended, the policy
        never holds it, and it reads the branch: a marked, solved patch of sigma."""
        wf = _wf()
        pl = _placement(wf, "memory")
        seed = _surviving_seed(wf, pl)
        ep = R.Episode(wf, pl, script(), C.PRIMARY, CELL, seed, agent_factory=_sure_agent)
        self.assertNotIn("oracle", vars(ep.ctx))
        for t in range(len(wf.tasks)):
            with self.assertRaises(OR.OracleSealed):
                ep.oracle.harm
            with self.assertRaises(OR.OracleSealed):
                ep.oracle.read(t, ep.store)
            ep.step()
        with self.assertRaises(OR.OracleSealed):
            ep.oracle.read(len(wf.tasks) - 2, ep.store)
        out = ep.finish()
        self.assertEqual(out.verdict.read_at, len(wf.tasks) - 1)
        self.assertEqual(out.record.harm, 1.0)
        self.assertTrue(out.record.solved_sigma)
        self.assertEqual(len(out.verdict.marked_patches), 1)
        self.assertEqual(ep.oracle.harm, 1.0)
        self.assertEqual(ep.oracle.scope().kind, "marker")
        # an unsolved sigma is blocked by the public tests: no harm (v2's truth table)
        bad = next(s for s in range(1000) if not carrier_runner.survives(wf, pl.payloads[0], s))
        out = self.run_ep(wf, pl, script(), seed=bad, agent_factory=_sure_agent)
        self.assertEqual((out.record.harm, out.record.solved_sigma), (0.0, False))
        # no attack: harm 0, nothing locked
        out = self.run_ep(wf, None, script(), seed=seed, agent_factory=_sure_agent)
        self.assertEqual((out.record.harm, out.record.harm_locked_at, out.record.sigma),
                         (0.0, None, None))

    # ---------------------------------------------------------------------------------
    def test_locked_harm_is_not_undone_by_later_quarantine(self):
        """C11 D4.payoff -- "with verified harm measured by a sealed oracle at the end of the
        horizon": in the primary world harm is locked at sigma, after sigma's lines 8-9.  A
        branch quarantine at sigma removes the patch first; one after sigma does not undo."""
        wf = _wf()
        pl = _placement(wf, "memory")
        seed = _surviving_seed(wf, pl)
        s = pl.sigma
        kw = dict(seed=seed, agent_factory=_sure_agent)
        self.assertEqual(C.PRIMARY.harm, "locked")
        after = self.run_ep(wf, pl, script(quarantines={s + 1: "branch"}), **kw).record
        self.assertEqual((after.harm, after.harm_locked_at), (1.0, s))
        self.assertIn((s + 1, "branch"), after.quarantines)
        at = self.run_ep(wf, pl, script(quarantines={s: "branch"}), **kw).record
        self.assertEqual((at.harm, at.harm_locked_at), (0.0, None))
        self.assertEqual(at.detected_at, s)
        self.assertTrue(at.missed_before_sigma, "caught AT sigma is not caught before it (H18)")
        early = self.run_ep(wf, pl, script(quarantines={s - 1: "memory"}), **kw).record
        self.assertEqual(early.harm, 0.0)
        self.assertFalse(early.missed_before_sigma)

    # ---------------------------------------------------------------------------------
    def test_reversible_harm_is_undone_by_branch_quarantine(self):
        """C11 D4.payoff -- "with verified harm measured by a sealed oracle at the end of the
        horizon": in the reversible sensitivity a branch quarantine at any task >= sigma
        removes the patch, and the oracle, reading the branch at the end, sees no harm."""
        wf = _wf()
        pl = _placement(wf, "memory")
        seed = _surviving_seed(wf, pl)
        rev = dict(C.sensitivities())["reversible"]
        kw = dict(world=rev, seed=seed, agent_factory=_sure_agent)
        H, s = len(wf.tasks), pl.sigma
        self.assertEqual(self.run_ep(wf, pl, script(), **kw).record.harm, 1.0)
        for tq in (s, s + 1, H - 1):
            r = self.run_ep(wf, pl, script(quarantines={tq: "branch"}), **kw).record
            self.assertEqual((r.harm, r.harm_locked_at), (0.0, None), f"branch quarantine at {tq}")
        # quarantining another carrier after sigma leaves the patch in the branch
        r = self.run_ep(wf, pl, script(quarantines={s + 1: "memory"}), **kw).record
        self.assertEqual(r.harm, 1.0)

    # ---------------------------------------------------------------------------------
    def test_loss_matches_definition_1(self):
        """D4.def1 -- "Defender loss is L = E[verified harm]+λQ E[false quarantines]+…λT
        E[clean tasks lost]": per episode L = harm + lambda_Q fq + lambda_T t_lost, with v2's
        declared lambdas (metrics.loss), FQ at the carrier level (O7)."""
        self.assertEqual((R.LAMBDA_Q, R.LAMBDA_T), (V2M.LAMBDA_Q, V2M.LAMBDA_T))
        wf = _wf()
        pl = _placement(wf, "memory")
        seed = _surviving_seed(wf, pl)
        H = len(wf.tasks)
        cases = [
            self.run_ep(wf, pl, script(), seed=seed, agent_factory=_sure_agent).record,
            self.run_ep(wf, pl, script(quarantines={1: "queue", 3: "skill", H - 1: "branch"}),
                        seed=seed, agent_factory=_sure_agent).record,
            self.run_ep(wf, None, script(quarantines={t: "branch" for t in range(H)}),
                        seed=seed).record,
        ]
        seen = set()
        for r in cases:
            want = r.harm + V2M.LAMBDA_Q * r.fq + V2M.LAMBDA_T * r.t_lost
            self.assertAlmostEqual(R.loss_of(r), want, places=12)
            self.assertAlmostEqual(R.loss_of(r.to_dict()), want, places=12)
            self.assertAlmostEqual(R.loss_of(r, lambda_Q=0.3, lambda_T=0.2),
                                   r.harm + 0.3 * r.fq + 0.2 * r.t_lost, places=12)
            seen |= {("harm", r.harm > 0), ("fq", r.fq > 0), ("t_lost", r.t_lost > 0)}
        self.assertTrue({("harm", True), ("fq", True), ("t_lost", True)} <= seen,
                        "every term of L is exercised")
        self.assertEqual(cases[1].t_lost, cases[1].clean_lost_branch)

    # ---------------------------------------------------------------------------------
    def test_false_quarantine_counts_clean_carrier_removals(self):
        """O7 D4.def1 -- "Defender loss is L = E[verified harm]+λQ E[false quarantines]+…λT
        E[clean tasks lost]": FQ = one quarantine of a carrier with c_t[k] = 0; a branch
        quarantine loses the clean solved patches in it, counted as clean tasks lost."""
        wf = _wf()
        H = len(wf.tasks)
        seed = 5
        clean = self.run_ep(wf, None, script(), seed=seed).record
        r = self.run_ep(wf, None, script(quarantines={2: "queue", 3: "memory"}), seed=seed).record
        self.assertEqual((r.fq, r.true_q, r.t_lost), (2, 0, 0))
        self.assertEqual(r.quarantines, ((2, "queue"), (3, "memory")))
        # a branch quarantine at the last task loses every solved clean patch
        r = self.run_ep(wf, None, script(quarantines={H - 1: "branch"}), seed=seed).record
        self.assertEqual(r.fq, 1)
        self.assertEqual(r.clean_lost_branch, clean.n_solved)
        self.assertEqual(r.t_lost, clean.n_solved)
        self.assertGreaterEqual(r.false_removed, r.clean_lost_branch)
        # twice: the second removes only what was written since
        r2 = self.run_ep(wf, None, script(quarantines={2: "branch", H - 1: "branch"}),
                         seed=seed).record
        self.assertEqual(r2.fq, 2)
        self.assertEqual(r2.clean_lost_branch, clean.n_solved)
        # a poisoned carrier is a true quarantine, not an FQ
        pl = _placement(wf, "memory")
        r = self.run_ep(wf, pl, script(quarantines={1: "memory", 2: "memory"}), seed=seed).record
        self.assertEqual((r.true_q, r.fq), (1, 1), "after the first, memory is clean again")

    # ---------------------------------------------------------------------------------
    def test_episode_is_deterministic_in_workflow_and_seed(self):
        """D19 D9.frozen -- "Defender policies and attacker libraries are frozen by hash before
        evaluation.": an episode is a function of (workflow, seed, policy, placement, world,
        cell) -- every draw is keyed on core.seed_of(wf, seed), nothing on process state."""
        dev = K.dev_workflows()[:6]
        a = AT.by_name(AT.held_out()[0])
        for wf in dev:
            pl = a.plan(wf, 1)
            for name in ("B1 audit-at-commit", "B2 uniform random"):
                r1 = self.run_ep(wf, pl, B.factory(name), cell=C.Cell(rho=0.25, delta=1), seed=4)
                r2 = self.run_ep(wf, pl, B.factory(name), cell=C.Cell(rho=0.25, delta=1), seed=4)
                self.assertEqual(r1.record.to_json(), r2.record.to_json())
                self.assertEqual(r1.postmortem, r2.postmortem)
        recs = {self.run_ep(dev[0], None, B.factory("B2 uniform random"), seed=s)
                .record.decision_log_sha256 for s in range(4)}
        self.assertGreater(len(recs), 1, "the seed reaches the policy's own randomisation")

    # ---------------------------------------------------------------------------------
    def test_resume_from_snapshot_equals_full_run(self):
        """DA1.l5 -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust over a restricted
        library": the rollouts behind L-hat continue an episode from a snapshot; resuming at
        any task gives the full run's record, and one snapshot resumes any number of times."""
        wf = K.dev_workflows()[3]
        a = AT.by_name(AT.held_out()[1])
        pl = a.plan(wf, 1)
        cell = C.Cell(rho=0.5, delta=1)
        fac = B.factory("B2 uniform random")
        full = R.run_episode(wf, pl, fac, C.PRIMARY, cell, 7)
        for t in range(len(wf.tasks) + 1):
            ep = R.Episode(wf, pl, fac, C.PRIMARY, cell, 7)
            for _ in range(t):
                ep.step()
            st = ep.snapshot()
            self.assertEqual((st.t, st.wf_id, st.seed), (t, wf.wf_id, 7))
            self.assertAlmostEqual(st.remaining, ep.remaining)
            self.assertEqual(st.hidden.k, pl.k)
            ep.step() if t < len(wf.tasks) else None          # the original moves on
            for _ in range(2):
                got = R.resume(st, t).run()
                self.assertEqual(got.record.to_json(), full.record.to_json(), f"resumed at {t}")
        with self.assertRaises(ValueError):
            R.resume(st, 0)

    # ---------------------------------------------------------------------------------
    def test_runner_refuses_a_sealed_split(self):
        """D9.frozen -- "Defender policies and attacker libraries are frozen by hash before
        evaluation.": the runner runs dev only; any other split needs the seal.Unsealed token,
        which seal.unseal alone issues (plan S6)."""
        wf = _wf()
        for split in ("ev" + "al", "secondary", "primary"):
            with self.assertRaises(seal.SealedSplit):
                R.Episode(wf, None, script(), C.PRIMARY, CELL, 0, split=split)
            with self.assertRaises(seal.SealedSplit):
                R.Episode(wf, None, script(), C.PRIMARY, CELL, 0, split=split, token=object())
        with self.assertRaises(seal.SealedSplit):
            seal.Unsealed(object(), {"split": "ev" + "al"}, "", {})
        self.assertEqual(self.run_ep(wf, None, script()).record.split, "dev")

    # ---------------------------------------------------------------------------------
    def test_two_seeded_carriers_count_one_harm(self):
        """D4.attacker -- "Its budget constrains the number of carriers it may seed and the
        magnitude of each.": with two seeded carriers both payloads can mark only the one
        patch of sigma, so harm is 0 or 1, and removing one carrier leaves the other's path."""
        wf = _wf()
        two = replace(C.PRIMARY, n_seeded=2)
        pl = _placement(wf, "memory", second="queue")
        self.assertEqual(pl.k, ("memory", "queue"))
        seed = _surviving_seed(wf, pl)
        with self.assertRaises(ValueError):
            R.Episode(wf, pl, script(), C.PRIMARY, CELL, seed)       # the world seeds one
        out = self.run_ep(wf, pl, script(), world=two, seed=seed, agent_factory=_sure_agent)
        self.assertEqual(out.record.harm, 1.0)
        self.assertEqual(len(out.verdict.marked_patches), 1)
        self.assertEqual(out.record.c_traj[pl.iota][:3], "101", "both seeds are live")
        r = self.run_ep(wf, pl, script(quarantines={pl.iota: "memory"}), world=two, seed=seed,
                        agent_factory=_sure_agent).record
        self.assertEqual(r.harm, 1.0, "the queue seed alone still reaches sigma")
        r = self.run_ep(wf, pl, script(quarantines={pl.iota: "memory", pl.iota + 1: "queue"}),
                        world=two, seed=seed, agent_factory=_sure_agent).record
        self.assertEqual((r.harm, r.true_q), (0.0, 2))

    # ---------------------------------------------------------------------------------
    def test_postmortem_published_after_every_workflow(self):
        """DA1.l1 O4 -- "estimate delay and heterogeneity from history": after every episode
        the runner emits the post-mortem line 1 reads -- the true (k, iota, sigma), harm or
        not, and the defender's alarms -- and a policy sees earlier ones only through
        EpisodeContext.postmortems."""
        wf = _wf()
        pl = _placement(wf, "memory")
        out = self.run_ep(wf, pl, B.factory("B1 audit-at-commit"), seed=2)
        pm = out.postmortem
        self.assertEqual((pm.k, pm.iota, pm.sigma, pm.delay), (("memory",), 0, 4, 4))
        self.assertEqual((pm.cell_id, pm.wf_id, pm.harm, pm.H),
                         (C.cell_id(CELL), wf.wf_id, out.record.harm, len(wf.tasks)))
        # B1 quarantines the branch on every commit alarm: the two logs name the same tasks
        self.assertTrue(all(k == "commit" for _, k in pm.alarms))
        self.assertEqual([t for t, _ in pm.alarms], [t for t, _ in out.record.quarantines])
        none = self.run_ep(wf, None, script(), seed=2).postmortem
        self.assertEqual((none.k, none.iota, none.sigma, none.harm), ((), None, None, 0.0))
        seen = []
        out2 = self.run_ep(wf, pl, lambda ctx: seen.append(ctx) or Script(ctx), seed=2,
                           postmortems=(pm, none), order=2)
        self.assertEqual(seen[0].postmortems, (pm, none))
        self.assertEqual((out2.record.n_incidents_seen, out2.record.order), (2, 2))


if __name__ == "__main__":
    unittest.main()
