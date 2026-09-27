"""Algorithm 1 line 1 (T10: v3/delta_hat.py, v3/sequence.py).  Each test protects the DCM
rows of v3/dcm/T10.csv that name it; its docstring carries the id(s) and the verbatim draft
sentence.

The runner (T6) and the particle filter (T9) are not used: `StubEpisode` below stands in
for one episode.  It returns an EpisodeRecord and the O4 post-mortem, so the sequence is
exercised through exactly the interface a runner adapter plugs into (sequence.EpisodeFn).
"""
import dataclasses
import json
import os
import tempfile
import unittest

import core
from v3 import api as A
from v3 import config as C
from v3 import delta_hat as DH
from v3 import metrics as M
from v3 import sequence as S

CELL = C.Cell(rho=0.0, delta=4)
CID = C.cell_id(CELL)
WFS = tuple(f"wf-{i:03d}" for i in range(12))


def pm(order, delay, *, wf=None, cell_id=CID, seed=1, H=12, iota=2, alarms=(), k=("memory",)):
    """A post-mortem of an attacked workflow (delay None = no attack)."""
    wf = wf or f"wf-pm-{order}"
    if delay is None:
        return A.PostMortem(cell_id=cell_id, wf_id=wf, order=order, seed=seed, k=(),
                            iota=None, sigma=None, harm=0.0, H=H, alarms=tuple(alarms))
    return A.PostMortem(cell_id=cell_id, wf_id=wf, order=order, seed=seed, k=tuple(k),
                        iota=iota, sigma=iota + delay, harm=1.0, H=H, alarms=tuple(alarms))


def record(step, *, harm, iota, sigma, cell=CELL, policy=None):
    """An EpisodeRecord carrying the line-1 trace the sequence handed to the episode."""
    ident = C.identity(C.PRIMARY, cell)
    return A.EpisodeRecord(
        split="dev", world=ident["world"], world_id=ident["world_id"], cell=ident["cell"],
        cell_id=ident["cell_id"], delta=cell.delta, wf=step.wf_id, repo="repo-" + step.wf_id,
        H=12, order=step.order, seed=step.key.seed,
        policy=policy or step.key.system, attack=step.key.attack,
        placement=None, k=("memory",) if iota is not None else (), iota=iota, sigma=sigma,
        eps=None, harm=harm, solved_sigma=True, harm_locked_at=None, detected_at=None,
        missed_before_sigma=False, fq=0, true_q=0, false_removed=0, benign_inspected=0,
        clean_lost_branch=0, t_lost=0, n_solved=12, spent=0.0, budget=49.2, audits={},
        c_traj=(), quarantines=(), delta_hat=step.line1.delta_hat,
        n_incidents_seen=step.line1.n_incidents_seen, line5_source="table",
        decision_log_sha256="0" * 64)


class StubEpisode:
    """One 'episode' per call: the attacker plays delay_of(wf) from iota = 2; harm is 1 iff
    the stub's Delta-hat was below the true delay (any deterministic rule would do)."""

    def __init__(self, delay_of, alarms_of=lambda wf: (), harm_of=None):
        self.delay_of, self.alarms_of, self.harm_of = delay_of, alarms_of, harm_of
        self.steps = []

    def __call__(self, step):
        self.steps.append(step)
        d = self.delay_of(step.wf_id)
        iota, sigma = (None, None) if d is None else (2, 2 + d)
        harm = (self.harm_of(step) if self.harm_of else
                float(d is not None and step.line1.delta_hat < d))
        rec = record(step, harm=harm, iota=iota, sigma=sigma)
        return rec, S.postmortem_from_record(rec, alarms=self.alarms_of(step.wf_id))


def key(cell=CELL, system="Sentinel", attack="br", seed=1):
    return DH.HistoryKey(cell_id=C.cell_id(cell), system=system, attack=attack, seed=seed)


class TestAlg1Line1(unittest.TestCase):

    # ---- the estimator ---------------------------------------------------------------

    def test_line1_delta_hat_is_low_quantile_of_same_cell_postmortems(self):
        """DA1.l1 -- Alg. 1 line 1: "Δ, χb ← estimate delay and heterogeneity from history".
        C12 / O3: Delta-hat is the q = 0.1 lower quantile of the delays sigma - iota seen in
        the same cell's earlier post-mortems, rounded DOWN to the nearest grid level
        (Cor. 6.6); chi-hat is chi_range of the cell's price table."""
        self.assertEqual((DH.Q, DH.PRIOR, DH.MIN_POSTMORTEMS),
                         (C.DHAT_QUANTILE, C.DHAT_PRIOR, C.DHAT_MIN_POSTMORTEMS))
        self.assertEqual((DH.Q, DH.PRIOR, DH.MIN_POSTMORTEMS), (0.1, 1, 1))
        self.assertEqual(DH.GRID, C.DELTAS)
        # lower empirical quantile: the ceil(q n)-th smallest delay
        self.assertEqual(DH.low_quantile([8] * 18 + [4] * 2, 0.1), 4)
        self.assertEqual(DH.low_quantile([8] * 19 + [4], 0.1), 8)
        self.assertEqual(DH.low_quantile([8, 4, 2], 0.1), 2)          # n <= 10: the minimum
        # rounded down to the grid, never up
        for x, g in ((0, 0), (1, 1), (3, 2), (5, 4), (7, 4), (8, 8), (13, 8)):
            self.assertEqual(DH.round_down_to_grid(x), g, x)
        pms = [pm(i, d) for i, d in enumerate([8] * 18 + [4] * 2)]
        self.assertEqual(DH.estimate(pms), 4)
        self.assertEqual(DH.estimate([pm(i, 3) for i in range(5)]), 2)
        self.assertEqual(DH.estimate([pm(i, 12) for i in range(5)]), 8)
        # workflows without an attack publish a post-mortem but carry no delay
        self.assertEqual(DH.estimate([pm(0, None), pm(1, 8), pm(2, None)]), 8)
        # line 1 as the sequence calls it: from the orders before the current one
        l1 = DH.line1(DH.ARM_POSTMORTEM, [pm(0, 8), pm(1, 4)], wf_id="wf-now", order=2,
                      cell_id=CID, seed=1, kappa=CELL.kappa())
        self.assertEqual((l1.delta_hat, l1.n_incidents_seen, l1.source), (4, 2, "postmortem"))
        import draft_setup
        self.assertAlmostEqual(l1.chi_hat, draft_setup.chi_range(CELL.kappa()))
        self.assertEqual(round(l1.chi_hat, 2), float(CELL.chi))
        # and inside a sequence, workflow n sees exactly workflows 0..n-1
        man = S.order_manifest(WFS)
        delays = {w: (8 if i % 3 else 4) for i, w in enumerate(man["order"])}
        ep = StubEpisode(delays.get)
        res = S.run_sequence(key(), man, ep, kappa=CELL.kappa())
        for n, step in enumerate(ep.steps):
            seen = [delays[w] for w in man["order"][:n]]
            want = DH.PRIOR if not seen else DH.round_down_to_grid(DH.low_quantile(seen, DH.Q))
            self.assertEqual(step.line1.delta_hat, want, n)
            self.assertEqual(res.records[n].delta_hat, want)

    def test_line1_uses_prior_before_first_postmortem(self):
        """DA1.l1 -- Alg. 1 line 1: "Δ, χb ← estimate delay and heterogeneity from history".
        O3: with fewer than 1 post-mortem carrying a delay, Delta-hat is the prior 1."""
        l1 = DH.line1(DH.ARM_POSTMORTEM, [], wf_id="wf-0", order=0, cell_id=CID, seed=1)
        self.assertEqual((l1.delta_hat, l1.n_incidents_seen, l1.source), (1, 0, "prior"))
        # post-mortems of clean workflows are published (O4) and counted, but carry no delay
        l1 = DH.line1(DH.ARM_POSTMORTEM, [pm(0, None), pm(1, None)], wf_id="wf-2", order=2,
                      cell_id=CID, seed=1)
        self.assertEqual((l1.delta_hat, l1.n_incidents_seen, l1.n_delays, l1.source),
                         (1, 2, 0, "prior"))
        self.assertIn(DH.PRIOR, DH.GRID)
        ep = StubEpisode(lambda w: 8)
        S.run_sequence(key(), S.order_manifest(WFS), ep)
        self.assertEqual(ep.steps[0].line1.delta_hat, 1)
        self.assertEqual(ep.steps[0].line1.n_incidents_seen, 0)
        self.assertEqual(ep.steps[1].line1.delta_hat, 8)
        # the prior-only arm (the '-regime estimate' ablation) stays at the prior throughout
        ep = StubEpisode(lambda w: 8)
        res = S.run_sequence(key(), S.order_manifest(WFS), ep, arm=DH.ARM_PRIOR)
        self.assertEqual({r.delta_hat for r in res.records}, {1})
        self.assertEqual([r.n_incidents_seen for r in res.records], list(range(len(WFS))))

    def test_line1_never_reads_current_workflow_sigma(self):
        """D5.1.delta-def -- §5.1: "Let Δ = σ − ι be the trigger delay".  C12: before sigma
        nothing depends on sigma, so line 1 reads earlier workflows' post-mortems only --
        never the current (or a later) workflow's (iota, sigma)."""
        with self.assertRaises(DH.LeakError):     # the current workflow's own post-mortem
            DH.line1(DH.ARM_POSTMORTEM, [pm(3, 8, wf="wf-now")], wf_id="wf-now", order=3,
                     cell_id=CID, seed=1)
        for late in (3, 4):                       # a post-mortem not strictly earlier
            with self.assertRaises(DH.LeakError):
                DH.line1(DH.ARM_POSTMORTEM, [pm(late, 8)], wf_id="wf-now", order=3,
                         cell_id=CID, seed=1)
        # changing workflow j's delay moves no Delta-hat at orders <= j
        man = S.order_manifest(WFS)
        j = 5
        base = {w: 4 for w in man["order"]}
        moved = dict(base, **{man["order"][j]: 0})
        e1, e2 = StubEpisode(base.get), StubEpisode(moved.get)
        S.run_sequence(key(), man, e1)
        S.run_sequence(key(), man, e2)
        for n in range(j + 1):
            self.assertEqual(e1.steps[n], e2.steps[n], n)
        self.assertNotEqual(e1.steps[j + 1].line1.delta_hat, e2.steps[j + 1].line1.delta_hat)
        # the step handed to the episode is frozen before the episode runs
        self.assertTrue(dataclasses.is_dataclass(e1.steps[0]))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            e1.steps[0].postmortems = ()
        # the oracle arm is the one arm told the current workflow's Delta, and says so
        l1 = DH.line1(DH.ARM_ORACLE, [], wf_id="wf-now", order=0, cell_id=CID, seed=1,
                      true_delta=8)
        self.assertEqual((l1.delta_hat, l1.source), (8, "oracle"))
        with self.assertRaises(ValueError):
            DH.line1(DH.ARM_POSTMORTEM, [], wf_id="wf-now", order=0, cell_id=CID, seed=1,
                     true_delta=8)

    # ---- the pinned order and the history's key --------------------------------------

    def test_workflow_order_is_pinned_in_manifest(self):
        """D9.4.freeze -- §9.4: "Defender policies and attacker libraries are frozen by hash
        before evaluation."  C12: the workflow order that decides which post-mortems line 1
        has seen is sorted by core.seed_of("v3-order", wf_id), written into the manifest with
        its sha256, and checked before a sequence runs."""
        order = S.workflow_order(WFS)
        self.assertEqual(order, S.workflow_order(tuple(reversed(WFS))))
        self.assertEqual(list(order), sorted(WFS, key=lambda w: (core.seed_of("v3-order", w), w)))
        self.assertNotEqual(list(order), sorted(WFS))            # not the id order
        with self.assertRaises(ValueError):
            S.workflow_order(WFS + WFS[:1])
        man = S.order_manifest(WFS, split="dev")
        self.assertEqual(man["order"], list(order))
        self.assertEqual(man["tag"], "v3-order")
        self.assertEqual(man["split"], "dev")
        self.assertEqual(man["sha256"], S.order_sha256(man["order"]))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "order.json")
            S.write_order_manifest(path, man)
            self.assertEqual(S.load_order_manifest(path), man)
            with open(path) as f:
                bad = json.load(f)
            bad["order"][0], bad["order"][1] = bad["order"][1], bad["order"][0]
            with open(path, "w") as f:
                json.dump(bad, f)
            with self.assertRaises(S.OrderMismatch):
                S.load_order_manifest(path)
        # a manifest whose order is not the rule's is refused, even with a matching sha
        forged = dict(man, order=list(reversed(man["order"])))
        forged["sha256"] = S.order_sha256(forged["order"])
        with self.assertRaises(S.OrderMismatch):
            S.run_sequence(key(), forged, StubEpisode(lambda w: 4))
        # the sequence runs in the manifest's order and stamps it on every record
        ep = StubEpisode(lambda w: 4)
        res = S.run_sequence(key(), man, ep)
        self.assertEqual([s.wf_id for s in ep.steps], man["order"])
        self.assertEqual([(r.wf, r.order) for r in res.records],
                         [(w, i) for i, w in enumerate(man["order"])])
        self.assertEqual(res.manifest_sha256, man["sha256"])

    def test_history_does_not_cross_cells_or_seeds(self):
        """D9.4.grid -- §9.4: "Results are reported on the (Δ, χ) grid rather than pooled".
        C12: the history is keyed by (cell_id, system, attacker column, seed); a post-mortem
        of another cell or seed never reaches line 1."""
        other = C.Cell(rho=0.0, delta=8)
        k1, k_cell, k_seed = key(), key(cell=other), key(seed=2)
        k_sys, k_att = key(system="Sentinel-lite"), key(attack="rule-3")
        self.assertEqual(len({k1, k_cell, k_seed, k_sys, k_att}), 5)
        ctx = A.EpisodeContext(world=C.PRIMARY, cell=CELL, wf_id="w", seed=1, H=12, budget=49.2,
                               depths=CELL.depths(), kappa=CELL.kappa(),
                               delegated=CELL.delegated())
        self.assertEqual(DH.HistoryKey.of(ctx, "Sentinel", "br"), k1)
        h = DH.DeltaHatHistory()
        h.add(k1, pm(0, 4))
        with self.assertRaises(DH.LeakError):
            h.add(k1, pm(1, 8, cell_id=C.cell_id(other)))
        with self.assertRaises(DH.LeakError):
            h.add(k1, pm(1, 8, seed=2))
        with self.assertRaises(DH.LeakError):
            h.add(k1, pm(0, 8, wf="wf-again"))                 # order must increase
        h.add(k_cell, pm(0, 8, cell_id=C.cell_id(other)))
        self.assertEqual([p.delay for p in h.before(k1, 5)], [4])
        self.assertEqual([p.delay for p in h.before(k_cell, 5)], [8])
        self.assertEqual(h.before(k_seed, 5), ())
        self.assertEqual(h.before(k_sys, 5), ())
        # line 1 refuses a mixed history outright
        with self.assertRaises(DH.LeakError):
            DH.line1(DH.ARM_POSTMORTEM, [pm(0, 4), pm(1, 8, seed=2)], wf_id="w", order=2,
                     cell_id=CID, seed=1)
        # a sequence refuses a history that already holds its key (a rerun would mix runs)
        man = S.order_manifest(WFS)
        with self.assertRaises(DH.LeakError):
            S.run_sequence(k1, man, StubEpisode(lambda w: 4), history=h)
        # two cells sharing one history object stay apart

        class Other(StubEpisode):
            def __call__(self, step):
                self.steps.append(step)
                rec = record(step, harm=0.0, iota=2, sigma=10, cell=other)
                return rec, S.postmortem_from_record(rec)
        shared = DH.DeltaHatHistory()
        e4, e8 = StubEpisode(lambda w: 4), Other(lambda w: 8)
        S.run_sequence(k1, man, e4, history=shared)
        S.run_sequence(k_cell, man, e8, history=shared)
        self.assertEqual({s.line1.delta_hat for s in e4.steps[1:]}, {4})
        self.assertEqual({s.line1.delta_hat for s in e8.steps[1:]}, {8})
        self.assertEqual(e8.steps[0].line1.delta_hat, DH.PRIOR)

    # ---- the learning curve and the channel ------------------------------------------

    def test_learning_curve_is_recorded(self):
        """DA1.l1 -- Alg. 1 line 1: "Δ, χb ← estimate delay and heterogeneity from history".
        C12: every record carries n_incidents_seen and delta_hat along the pinned order, so
        the learning curve (harm by number of incidents seen, metrics.learning_curve) is
        printed; workflow 0 is the prior-only point."""
        man = S.order_manifest(WFS)
        ep = StubEpisode(lambda w: 4)
        res = S.run_sequence(key(), man, ep)
        self.assertEqual([r.n_incidents_seen for r in res.records], list(range(len(WFS))))
        self.assertEqual([r.delta_hat for r in res.records], [1] + [4] * (len(WFS) - 1))
        self.assertEqual(res.curve(), [(n, r.delta_hat, r.harm)
                                       for n, r in enumerate(res.records)])
        rows = M.learning_curve(res.records, "Sentinel", ["br"], [4])
        self.assertEqual([r["n_incidents_seen"] for r in rows], list(range(len(WFS))))
        self.assertTrue(rows[0]["prior_only"])
        self.assertEqual(rows[0]["mean_harm"], 1.0)             # prior 1 < true 4
        self.assertTrue(all(r["mean_harm"] == 0.0 for r in rows[1:]))
        # a clean workflow publishes a post-mortem (counted, as the runner's
        # len(ctx.postmortems)) but carries no delay: Delta-hat stays at the prior
        ep = StubEpisode(lambda w: None if w == man["order"][0] else 4)
        res = S.run_sequence(key(), man, ep)
        self.assertEqual([r.n_incidents_seen for r in res.records][:3], [0, 1, 2])
        self.assertEqual([r.delta_hat for r in res.records][:3], [1, 1, 4])
        self.assertEqual(len(res.postmortems), len(WFS))

    def test_postmortem_is_the_only_cross_workflow_channel(self):
        """D6.online -- §6.1: "Learning the policy online against the observed attacker.
        Attractive, and outside our model: the Stackelberg formulation assumes the defender
        commits first, and an online learner does not commit."  C12 / O4: what crosses a
        workflow boundary is the published post-mortem (true k, iota, sigma after EVERY
        workflow) and nothing else; it feeds Delta-hat and beta, never the policy's library."""
        # the post-mortem carries the declared O4 fields only (no item or poison label)
        self.assertEqual({f.name for f in dataclasses.fields(A.PostMortem)},
                         {"cell_id", "wf_id", "order", "seed", "k", "iota", "sigma", "harm",
                          "H", "alarms"})
        self.assertEqual({f.name for f in dataclasses.fields(S.Step)},
                         {"key", "wf_id", "order", "arm", "postmortems", "line1"})
        # two sequences whose episodes differ in everything but the post-mortem hand
        # identical steps to every later workflow
        man = S.order_manifest(WFS)
        e1 = StubEpisode(lambda w: 4, harm_of=lambda s: 1.0)
        e2 = StubEpisode(lambda w: 4, harm_of=lambda s: 1.0)
        orig = e2.__call__

        def noisy(step):
            rec, p = orig(step)
            return dataclasses.replace(rec, spent=17.0, fq=3, audits={"memory": [1]}), p
        r1 = S.run_sequence(key(), man, e1)
        r2 = S.run_sequence(key(), man, noisy)
        self.assertEqual(e1.steps, e2.steps)
        self.assertEqual(r1.postmortems, r2.postmortems)
        # the episode's context is the template plus the step's post-mortems, nothing else
        tmpl = A.EpisodeContext(world=C.PRIMARY, cell=CELL, wf_id=man["order"][3], seed=1, H=12,
                                budget=49.2, depths=CELL.depths(), kappa=CELL.kappa(),
                                delegated=CELL.delegated(), rng_seed=9)
        ctx = e1.steps[3].context(tmpl)
        self.assertEqual(ctx.postmortems, e1.steps[3].postmortems)
        self.assertEqual(dataclasses.replace(ctx, postmortems=()), tmpl)
        with self.assertRaises(DH.LeakError):
            e1.steps[4].context(tmpl)                          # another workflow's template
        # O4: a post-mortem after EVERY workflow -- an episode that withholds one is refused
        with self.assertRaises(S.MissingPostMortem):
            S.run_sequence(key(), man, lambda s: (record(s, harm=0.0, iota=None, sigma=None),
                                                  None))
        # and a post-mortem that disagrees with the step is refused
        def wrong(step):
            rec = record(step, harm=0.0, iota=2, sigma=6)
            return rec, dataclasses.replace(S.postmortem_from_record(rec), order=step.order + 1)
        with self.assertRaises(DH.LeakError):
            S.run_sequence(key(), man, wrong)

    def test_beta_evidence_counts_alarms_outside_k_iota_sigma_as_drift(self):
        """D7.beta -- §7: "β is estimated online from clean workflows."  O11: the post-mortem
        also feeds beta; an alarm outside (k, [iota, sigma)) of the published attack counts
        as drift, every alarm of a clean workflow counts as drift."""
        pms = [pm(0, 4, iota=2, alarms=((1, "memory"), (3, "memory"), (3, "skill"),
                                        (6, "memory"))),     # sigma = 6: outside
               pm(1, None, alarms=((0, "commit"), (5, "queue"))),
               pm(2, 2, iota=1, k=("skill",), alarms=((2, "skill"),))]
        ev = DH.beta_evidence(pms)
        self.assertEqual(ev["n_alarms"], 7)
        self.assertEqual(ev["n_drift_alarms"], 5)            # t1, skill@3, t6, two clean
        self.assertEqual(ev["n_tasks"], 36)
        self.assertEqual(ev["n_workflows"], 3)
        self.assertEqual(ev["n_clean_workflows"], 1)
        self.assertEqual(DH.beta_evidence([]), {"n_alarms": 0, "n_drift_alarms": 0,
                                                "n_tasks": 0, "n_workflows": 0,
                                                "n_clean_workflows": 0})

    # ---- headline numbers -------------------------------------------------------------

    def test_no_headline_number_comes_from_the_oracle_arm(self):
        """D9.4.gate -- §9.4: "Worst-case harm against heldout attacker policies at equal
        budget is the preregistered primary endpoint against B1 with a 15% relative margin."
        C12: the oracle-Delta arm is an upper bound and the prior-only arm an ablation;
        headline numbers come from the post-mortem arm only."""
        self.assertEqual(DH.HEADLINE_ARMS, (DH.ARM_POSTMORTEM,))
        self.assertEqual(set(DH.ARMS), {DH.ARM_POSTMORTEM, DH.ARM_ORACLE, DH.ARM_PRIOR})
        self.assertEqual(DH.system_name("Sentinel", DH.ARM_POSTMORTEM), "Sentinel")
        for arm in (DH.ARM_ORACLE, DH.ARM_PRIOR):
            self.assertEqual(DH.arm_of(DH.system_name("Sentinel", arm)), arm)
        self.assertIsNone(DH.arm_of("Sentinel"))               # untagged = headline-eligible
        self.assertIsNone(DH.arm_of("B1 Audit-at-commit"))
        man = S.order_manifest(WFS)
        runs = {arm: S.run_sequence(key(), man, StubEpisode(lambda w: 8), arm=arm,
                                    true_delta=(lambda w: 8) if arm == DH.ARM_ORACLE else None)
                for arm in DH.ARMS}
        self.assertEqual({r.delta_hat for r in runs[DH.ARM_ORACLE].records}, {8})
        self.assertEqual({r.policy for r in runs[DH.ARM_ORACLE].records},
                         {DH.system_name("Sentinel", DH.ARM_ORACLE)})
        every = [r for res in runs.values() for r in res.records]
        head = DH.headline_records(every)
        self.assertEqual(len(head), len(WFS))
        self.assertEqual({r.policy for r in head}, {"Sentinel"})
        with self.assertRaises(DH.OracleInHeadline):
            DH.require_headline(every)
        DH.require_headline(head)
        DH.require_headline([r.to_dict() for r in head])
        # the oracle arm needs the true Delta; no other arm accepts it
        with self.assertRaises(ValueError):
            S.run_sequence(key(), man, StubEpisode(lambda w: 8), arm=DH.ARM_ORACLE)
        with self.assertRaises(ValueError):
            S.run_sequence(key(), man, StubEpisode(lambda w: 8), true_delta=lambda w: 8)


if __name__ == "__main__":
    unittest.main()
