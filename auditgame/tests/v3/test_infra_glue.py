"""The P2 integration glue after T15 (Sentinel): grid names, tools/v3_run.py's seams, the
nominal-kernel tuning, and the speedups that must not move a decision.  Infrastructure;
the draft sentences are protected by the DCM-row tests these modules already have.  DEV
ONLY (Sentinel runs on sentinel.stub_parts(): no number here is a result).  Run from
auditgame/."""
import logging
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from unittest import mock

from tools import v3_tune as TU
from v3 import attackers as AT
from v3 import baselines as BL
from v3 import config as C
from v3 import corpus as K
from v3 import delta_hat as DH
from v3 import grid as G
from v3 import line5 as L5
from v3 import rollout as RO
from v3 import runner as RN
from v3 import sentinel as S
from v3 import sequence as SQ

sys.path.insert(0, str(pathlib.Path("tools").resolve()))
import v3_run as R  # noqa: E402

HEADLINE = C.Cell(rho=0.5, delta=4)


def _dev(n, min_H=6):
    return [w for w in K.dev_workflows() if w.H >= min_H][:n]


class TestInfraGlue(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logging.getLogger("v3.line23").setLevel(logging.ERROR)
        cls.parts = S.stub_parts()

    # ---- v3/grid.py ------------------------------------------------------------------
    def test_grid_names_are_the_registry_names(self):
        """The Sentinel class of the grid is T15's registry, the oracle arm under its
        tagged name (no alias: the C12 guard still catches it), and the -regime-estimate
        arm is an ablation row outside the headline and outside the core."""
        self.assertEqual(G.ORACLE_DELTA, S.ORACLE_DELTA)
        self.assertEqual(G.REGIME_PRIOR, S.REGIME_PRIOR)
        self.assertLessEqual(set(G.SENTINEL_CLASS) | set(G.ABLATION_ROWS), set(S.V3_REGISTRY))
        self.assertNotIn("Sentinel oracle-Delta", G.all_systems())
        self.assertIn(S.ORACLE_DELTA, G.SENTINEL_CLASS)
        with self.assertRaises(DH.OracleInHeadline):
            DH.require_headline([{"policy": G.ORACLE_DELTA}])
        with self.assertRaises(DH.OracleInHeadline):
            DH.require_headline([{"policy": G.REGIME_PRIOR}])
        ab = [u for u in G.units() if u.block == "ablation-prior"]
        self.assertTrue(ab)
        self.assertEqual({u.system for u in ab}, {S.REGIME_PRIOR})
        self.assertFalse(any(u.core for u in ab))
        self.assertTrue(all(u.cell.is_headline() and u.world == C.PRIMARY for u in ab))
        self.assertEqual({u.column for u in ab}, set(G.HELD_OUT))
        self.assertNotIn(S.REGIME_PRIOR, G.SYSTEMS)
        self.assertNotIn(S.REGIME_PRIOR, S.HEADLINE_SYSTEMS)
        self.assertFalse(any(ch.unit.system == S.REGIME_PRIOR
                             for ch in G.chains(core_only=True, seeds=(1,))))

    # ---- tools/v3_run.py: factories and parts ------------------------------------------
    def test_policy_factory_binds_the_placement(self):
        """policy_factory -> reg[name].for_placement(pl): the oracle arm is told the
        placement's true Delta, also where the cell's Delta is the attacker's choice."""
        wf = _dev(1, min_H=9)[0]
        att = C.Cell(rho=0.5, delta=C.DELTA_ATTACKER)
        for d in (2, 8):
            pl = AT.by_name(AT.held_out()[0]).plan(wf, d)
            if pl is None:
                continue
            ctx = RN.context(wf, C.PRIMARY, att, 1)
            pol = R.policy_factory(S.ORACLE_DELTA, self.parts)(pl)(ctx)
            self.assertEqual(pol.delta_hat, d)
            self.assertEqual(pol.name, S.ORACLE_DELTA)
        with self.assertRaises(ValueError):             # unbound: no true Delta to give
            S.registry(self.parts)[S.ORACLE_DELTA](RN.context(wf, C.PRIMARY, att, 1))
        f = R.policy_factory(S.SENTINEL, self.parts)
        self.assertIs(f(None).parts, self.parts)
        b1 = R.policy_factory(BL.B1AuditAtCommit.name)
        self.assertIs(b1(None), b1(object()))

    def test_run_checks_sentinel_parts_before_simulating(self):
        """sentinel.check_ready runs before any chain: without T14 / T18 parts a run naming
        the Sentinel class exits 3 and says what is missing; --stub-parts (dev only) passes
        the check; eval refuses --stub-parts."""
        with tempfile.TemporaryDirectory() as d:
            calls = []

            def stub(chain, workflows, factory_of, split, token=None):
                calls.append(chain)
                return []
            args = ["--split", "dev", "--blocks", "main", "--systems", S.SENTINEL,
                    "--seeds", "1", "--workflows", "1", "--jobs", "1", "--out", d]
            with mock.patch.object(S, "default_parts", lambda: S.Parts()):
                buf = StringIO()
                with redirect_stdout(buf):
                    rc = R.main(args, run_chain=stub)
                self.assertEqual(rc, R.EXIT_NO_RUNNER)
                self.assertIn("line-5 table", buf.getvalue())
                self.assertEqual(calls, [])
                with redirect_stdout(StringIO()):
                    rc = R.main(args + ["--stub-parts"], run_chain=stub)
                self.assertNotEqual(rc, R.EXIT_NO_RUNNER)
                self.assertTrue(calls)
            self.assertEqual(R.missing_parts([BL.B1AuditAtCommit.name]), [])
            self.assertEqual(R.missing_parts([S.SENTINEL], self.parts), [])
            with self.assertRaises(SystemExit), redirect_stdout(StringIO()), \
                    mock.patch("sys.stderr", StringIO()):
                R.main(["--split", "eval", "--stub-parts"])
            with self.assertRaises(R.Refused):
                R.simulate([], [], "eval", pathlib.Path(d), stub=True)

    # ---- tools/v3_run.py: the chain ---------------------------------------------------
    def test_sentinel_chain_runs_through_run_sequence(self):
        """A held-out Sentinel chain: T10's run_sequence, the pinned order, post-mortems
        carried (n_incidents_seen counts them), the oracle arm told the true Delta; a
        baseline chain runs the same order directly.  Every record validates."""
        wfs = _dev(4)
        for system, arm in ((S.SENTINEL, DH.ARM_POSTMORTEM), (S.ORACLE_DELTA, DH.ARM_ORACLE),
                            (BL.B1AuditAtCommit.name, None)):
            u = G.Unit("main", "main", "primary", C.PRIMARY, HEADLINE, system, G.HELD_OUT[0])
            ch = G.Chain(u, 1)
            seen = []
            real = SQ.run_sequence

            def spy(*a, **k):
                seen.append(k.get("arm"))
                return real(*a, **k)
            with mock.patch.object(SQ, "run_sequence", spy):
                recs = R.episode_runner()(ch, wfs, R.policy_factory(system, self.parts), "dev")
            self.assertEqual(seen, [] if arm is None else [arm])
            sched = R.schedule(ch, wfs)
            self.assertEqual([r.wf for r in recs], [wf.wf_id for wf, _ in sched])
            self.assertEqual([r.wf for r in recs],
                             [w for w in SQ.workflow_order([r.wf for r in recs])])
            self.assertEqual([r.order for r in recs], list(range(len(recs))))
            for r in recs:
                R.validate_record(r, ch, "dev")
            if arm is None:
                self.assertTrue(all(r.delta_hat is None for r in recs))
                continue
            self.assertEqual([r.n_incidents_seen for r in recs], list(range(len(recs))))
            if arm == DH.ARM_ORACLE:
                self.assertTrue(all(r.delta_hat == HEADLINE.delta for r in recs))
            else:
                self.assertEqual(recs[0].delta_hat, C.DHAT_PRIOR)

    def test_rollout_and_stage_worlds_use_their_drivers(self):
        """Sentinel-rollout is driven by rollout.drive(ep, ep.policy.source); in the stage
        world the Sentinel class keeps its own lines 8-9 (keep_quarantine=True)."""
        wf = _dev(1)[0]
        pl = AT.by_name(AT.held_out()[1]).plan(wf, HEADLINE.delta)
        parts = S.stub_parts(rollout_members=("L-SW-commit",), n_particles=64)
        u = G.Unit("headline-rollout", None, "headline-rollout", G.HEADLINE_WORLD, HEADLINE,
                   S.SENTINEL_ROLLOUT, G.HELD_OUT[1], core=False)
        got = {}

        def fake_drive(ep, source):
            got["ep"], got["source"] = ep, source
            return "driven"
        with mock.patch.object(RO, "drive", fake_drive):
            out = R.episode(G.Chain(u, 1), wf, pl,
                            R.policy_factory(S.SENTINEL_ROLLOUT, parts)(pl), "dev")
        self.assertEqual(out, "driven")
        self.assertIs(got["source"], got["ep"].policy.source)
        self.assertIsInstance(got["source"], L5.RolloutSource)
        stage = dict(C.sensitivities())["stage"]
        seen = []
        import v3.stage_world as SW
        real = SW.episode_in_world

        def spy(*a, **k):
            seen.append(k.get("keep_quarantine"))
            return real(*a, **k)
        with mock.patch.object(SW, "episode_in_world", spy):
            for system in (S.SENTINEL, BL.B1AuditAtCommit.name):
                us = G.Unit("sens:stage", None, "stage", stage, C.Cell(rho=0.25, delta=4),
                            system, G.HELD_OUT[1], core=False)
                spl = SW.plan_in_world(AT.by_name(G.HELD_OUT[1]), wf, us.cell, stage)
                rec = R.episode(G.Chain(us, 1), wf, spl,
                                R.policy_factory(system, self.parts)(spl), "dev").record
                self.assertEqual(rec.world["audit_reading"], "stage")
        self.assertEqual(seen, [True, False])

    # ---- speed: nothing may move a decision --------------------------------------------
    #: sha256 of (record minus decision_log_sha256, decisions(), decision log minus the
    #: line-2 entry) over the episodes of `_decision_digest`, computed on int-p2 5aafaa2
    #: BEFORE the speedups (check_classes and minimax memoised) and unchanged after.  The
    #: two left-out fields carry the line-2 infeasibility record's wall time and RSS, so
    #: they are not reproducible run to run.
    #: Re-pinned 27/09 (branch fix-drift) for ONE declared change: v3's drift text is
    #: sized to the payload (v3.drift, AgentMode.drift_size = "payload").  With the drift
    #: text swapped back to world_v2.drift_content the digest is still the old
    #: f9177fdd04d0ff57f282622c4e34c7a920fdf779efa81eaea62f8742b83fbd17 (checked).
    PINNED_DECISIONS = "2670cc56bd118744beb73e1efff6a54e4174f92fbe9b18b311321af447d19284"

    @staticmethod
    def _decision_digest(reg) -> str:
        import hashlib
        import json
        h = hashlib.sha256()
        for name in (S.SENTINEL, "Sentinel -randomization", "Sentinel -alarm memory"):
            for cell in (HEADLINE, C.Cell(rho=0.0, delta=2)):
                for wf in _dev(3):
                    pl = AT.by_name(AT.held_out()[0]).plan(wf, cell.delta)
                    for seed in (1, 2):
                        ep = RN.Episode(wf, pl, reg[name], C.PRIMARY, cell, seed)
                        d = ep.run().record.to_dict()
                        d.pop("decision_log_sha256")
                        log = [e for e in ep.policy.decision_log() if e.get("line") != 2]
                        h.update(json.dumps([d, ep.policy.decisions(), log], sort_keys=True,
                                            default=str).encode())
        return h.hexdigest()

    def test_speedups_keep_every_decision(self):
        """The memoised line-5 pieces return what the uncached ones return, a refused
        column set is refused every time, and Sentinel's decisions on fixed seeds are the
        ones pinned before the speedups (twice: cold and warm caches)."""
        import random
        rng = random.Random(7)
        L = [[round(rng.random(), 6) for _ in range(6)] for _ in range(28)]
        L5._MINIMAX.clear()
        x0, v0 = L5._minimax(L)
        for _ in range(2):
            x, v = L5.minimax(L)
            self.assertEqual((tuple(x), v), (tuple(x0), v0))
            self.assertIsInstance(x, list)
        x[0] = -1.0                                     # the caller's list is its own
        self.assertEqual(L5.minimax(L)[0][0], x0[0])
        with self.assertRaises(ValueError):
            L5.minimax([])
        classes = tuple(AT.attacker_classes())
        L5.check_classes(classes)
        self.assertIn(classes, L5._CLASSES_OK)
        for _ in range(2):
            with self.assertRaises(ValueError):
                L5.check_classes(classes + (AT.held_out()[0],))
        L5._MINIMAX.clear()
        L5._CLASSES_OK.clear()
        reg = S.registry(S.stub_parts())
        self.assertEqual(self._decision_digest(reg), self.PINNED_DECISIONS)
        self.assertEqual(self._decision_digest(S.registry(S.stub_parts())),
                         self.PINNED_DECISIONS)

    # ---- tools/v3_tune.py --------------------------------------------------------------
    def test_nominal_only_tuning_for_minus_transition(self):
        """Table 3's '- transition uncertainty' arm reads tau and eta_Q tuned on the
        nominal kernel only (sentinel.Parts.tuned_nominal): --nominal-only restricts the
        worst case to that kernel, records it, and is the only tuning written to
        reference/v3_tuned_nominal.json (and never to v3_tuned.json)."""
        self.assertEqual(TU.TUNED_NOMINAL_PATH, S.TUNED_NOMINAL_PATH)
        self.assertEqual(TU.TUNED_PATH, S.TUNED_PATH)

        def tiny(**kw):
            args = dict(workflows=TU.dev_workflows(1), seeds=(1,), rhos=(0.0,),
                        attacks=("memory-first-write-e0.6",), tau5_grid=(0.0,),
                        sw_grid=("commit3",), progress=lambda *_: None)
            args.update(kw)
            return TU.tune(**args)
        res = tiny(kernels=TU.NOMINAL_ONLY)
        self.assertEqual(res["tuned"]["kernels"], ["nominal"])
        self.assertEqual(tiny()["tuned"]["kernels"], list(TU.KERNELS))
        for e in (e for e in res["log"] if e["step"] == "tau5" and "candidate" in e):
            self.assertEqual(set(e["by_kernel"]), {"nominal"})
            self.assertEqual(e["worst_L"], e["by_kernel"]["nominal"])
        with self.assertRaises(ValueError):
            TU.tune(kernels=("nominal", "sideways"), progress=lambda *_: None)
        with self.assertRaises(ValueError):             # the wrong file for each tuning
            TU.write(res, TU.TUNED_PATH)
        with self.assertRaises(ValueError):
            TU.write(tiny(), TU.TUNED_NOMINAL_PATH)
        self.assertIn("--nominal-only", pathlib.Path(TU.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
