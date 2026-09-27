"""Draft S4 "Defender ... observes o_t" and S8 "Detector": the v3 observation model (T5).

Each test protects the DCM rows of v3/dcm/T05.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  Run from auditgame/.
"""
import dataclasses
import inspect
import math
import unittest
from statistics import NormalDist

from core import CarrierStore, Item
from v3 import api as A
from v3 import config as C
from v3 import observe as O

_N = NormalDist()
SEED = 20260927


def _item(carrier, t, *, poisoned=False, tag="x", topic="auth"):
    return Item(carrier=carrier, topic=topic, content=f"[{topic}] {carrier} {tag} {t}",
                created_at=t, provenance="agent/notes", poisoned=poisoned)


def _miss_rate(model, *, has_marker, via, depth, n, seed=SEED):
    missed = 0
    for i in range(n):
        ins = model.commit(t=3, depth=depth, has_marker=has_marker, via=via,
                           task_id=f"task-{i}", seed=seed)
        missed += not ins.alarm
    return missed / n


def _mc_tol(p, n, k=4.0):
    return k * math.sqrt(max(p * (1 - p), 1e-4) / n) + 1e-9


class TestS4Observe(unittest.TestCase):

    # ---- D4.obs (O8): the checkpoint channel -------------------------------------------

    def test_checkpoint_channel_declared(self):
        """D4.obs (O8): "It observes ot : alarm scores from an imperfect detector with
        true-positive rate ψ and false-positive rate φ, plus executable checkpoint outcomes."

        The checkpoint is a declared channel (psi_c, phi_c) with psi_c = phi_c: it passes
        iff the task's patch passes its tests (solved), a draw no poison label enters (N4),
        so a marked patch passes exactly as often as a clean one (Fig. 1 t6 "passes
        tests") and its likelihood ratio is 1 under every hypothesis."""
        self.assertTrue(C.CHECKPOINT_PSI_EQUALS_PHI)
        ch = O.CHECKPOINT
        for rate in (0.62, 0.55, 0.7):
            psi_c, phi_c = ch.rates(rate)
            self.assertEqual(psi_c, phi_c)
            self.assertAlmostEqual(phi_c, 1 - rate, places=12)
        self.assertEqual(ch.source, "solved")
        for world in (C.PRIMARY, dataclasses.replace(C.PRIMARY, provenance="A7")):
            m = O.ObservationModel(world, C.Cell(rho=0.5, delta=4))
            for solved in (True, False):
                self.assertIs(m.checkpoint(solved=solved), solved)
            # the outcome has no parameter through which a poison label could enter
            self.assertEqual(list(inspect.signature(m.checkpoint).parameters), ["solved"])
        for passed in (True, False):
            for poisoned in (True, False):
                self.assertEqual(O.checkpoint_lr(passed, poisoned), 1.0)
                self.assertEqual(O.checkpoint_loglik(passed, poisoned, 0.62),
                                 O.checkpoint_loglik(passed, not poisoned, 0.62))
        # Fig. 1 t6: the marked patch "passes tests", and the observation carries it
        m = O.ObservationModel(C.PRIMARY, C.Cell(rho=0.0, delta=4))
        ins = m.commit(t=5, depth=1, has_marker=True, via="delegated", task_id="t6", seed=SEED)
        obs = ins.observation(t=5, requested=A.AuditAction("commit", 1),
                              checkpoint=m.checkpoint(solved=True))
        self.assertIsInstance(obs, A.Observation)
        self.assertIs(obs.checkpoint, True)
        none = m.nothing(t=5, requested=None, checkpoint=m.checkpoint(solved=True))
        self.assertIsNone(none.bought)
        self.assertEqual(none.scores, ())
        self.assertIs(none.checkpoint, True)

    # ---- D4.obs (D20, C1): commit review of a delegated patch --------------------------

    def test_commit_sees_delegated_patch_with_rho_dprime_at_every_depth(self):
        """D4.obs (D20, C1): "It observes ot : alarm scores from an imperfect detector with
        true-positive rate ψ and false-positive rate φ, plus executable checkpoint outcomes."

        Commit review sees a delegated patch with separation rho*d' at every depth (no
        sqrt(depth): depth does not show the commit the provenance), a direct patch with
        d'*sqrt(depth), and a sweep audit d'*sqrt(depth).  The simulated miss rate of a
        delegated patch matches P_miss = Phi(z_{1-phi} - rho d') within Monte Carlo error."""
        n = 3000
        for dp in C.DPRIME_LEVELS:
            for rho in C.RHO_GRID:
                cell = C.Cell(rho=rho, delta=4, dprime=dp)
                m = O.ObservationModel(C.PRIMARY, cell)
                d_exact = cell.detector().d_prime
                self.assertAlmostEqual(m.dprime, d_exact, places=12)
                self.assertEqual(round(d_exact, 2), dp)
                for depth in (1, 2, 3):
                    self.assertAlmostEqual(O.patch_mean(True, "delegated", rho, d_exact, depth),
                                           rho * d_exact, places=12)
                    self.assertAlmostEqual(O.patch_mean(True, "direct", rho, d_exact, depth),
                                           d_exact * math.sqrt(depth), places=12)
                    self.assertEqual(O.patch_mean(False, "", rho, d_exact, depth), 0.0)
                    self.assertAlmostEqual(O.sweep_dprime(d_exact, depth),
                                           d_exact * math.sqrt(depth), places=12)
                    # the same draw at every depth: depth changes nothing for a delegated patch
                    s1 = m.commit(t=2, depth=1, has_marker=True, via="delegated",
                                  task_id="tk", seed=SEED).scores
                    sd = m.commit(t=2, depth=depth, has_marker=True, via="delegated",
                                  task_id="tk", seed=SEED).scores
                    self.assertEqual(s1, sd)
                # the formula, against the simulation
                phi = cell.detector().phi
                want = _N.cdf(_N.inv_cdf(1 - phi) - rho * d_exact)
                self.assertAlmostEqual(O.p_miss_commit(rho, d_exact, phi), want, places=12)
                for depth in (1, 3):
                    got = _miss_rate(m, has_marker=True, via="delegated", depth=depth, n=n)
                    self.assertLess(abs(got - want), _mc_tol(want, n),
                                    f"d'={dp} rho={rho} depth={depth}: {got:.4f} vs {want:.4f}")
            # a direct patch at depth 2 is seen with d' sqrt(2), whatever rho is
            cell = C.Cell(rho=0.0, delta=4, dprime=dp)
            m = O.ObservationModel(C.PRIMARY, cell)
            det = cell.detector()
            want = _N.cdf(det.tau_det - det.d_prime * math.sqrt(2))
            got = _miss_rate(m, has_marker=True, via="direct", depth=2, n=n)
            self.assertLess(abs(got - want), _mc_tol(want, n), f"direct d'={dp}")
            # a clean patch alarms at phi
            fa = 1 - _miss_rate(m, has_marker=False, via="", depth=1, n=n)
            self.assertLess(abs(fa - det.phi), _mc_tol(det.phi, n), f"clean d'={dp}")
        with self.assertRaises(ValueError):
            O.patch_mean(True, "", 0.5, 2.0, 1)          # a marked patch needs a route
        with self.assertRaises(ValueError):
            O.patch_mean(False, "delegated", 0.5, 2.0, 1)

    # ---- C1 / O9: A7 adds provenance --------------------------------------------------

    def test_a7_adds_provenance_signal_only_in_a7(self):
        """D2.artifact (C1): "An audit that observes only the artifact cannot distinguish
        “this patch is the product of a poisoned skill” from “this patch is ordinary”,
        because the distinguishing evidence is the skill’s provenance."
        D7.commit-prov (C1, O9): "Audit actions. Insertion audit (content and provenance
        check on new memory records), … commit audit (patch review, differential testing,
        provenance of contributing skills)."

        A0 (primary) reads the patch only: no provenance field.  A7 reads the same patch
        score AND a provenance score of the contributing delegated carriers, mean d'_prov
        when a poisoned delegated carrier produced the marked patch, 0 otherwise; d'_prov
        is a placeholder equal to the cell's detector d' (O9), with no sqrt(depth).  The
        A7 alarm is 'either score over tau_det'.  Sweeps carry no provenance in either."""
        self.assertEqual(C.A7_PROVENANCE_DPRIME, "cell-detector-dprime")
        a7 = dataclasses.replace(C.PRIMARY, provenance="A7")
        n = 3000
        for rho in (0.0, 0.5):
            cell = C.Cell(rho=rho, delta=4)
            m0, m7 = O.ObservationModel(C.PRIMARY, cell), O.ObservationModel(a7, cell)
            self.assertIsNone(m0.dprime_provenance)
            self.assertAlmostEqual(m7.dprime_provenance, cell.detector().d_prime, places=12)
            for depth in (1, 3):
                for marker, via in ((True, "delegated"), (True, "direct"), (False, "")):
                    i0 = m0.commit(t=4, depth=depth, has_marker=marker, via=via,
                                   task_id="tk", seed=SEED)
                    i7 = m7.commit(t=4, depth=depth, has_marker=marker, via=via,
                                   task_id="tk", seed=SEED)
                    self.assertIsNone(i0.provenance)
                    self.assertIsInstance(i7.provenance, float)
                    self.assertEqual(i0.scores, i7.scores, "A7 adds, it does not replace")
                    tainted = marker and via == "delegated"
                    self.assertEqual(O.provenance_mean(tainted, m7.dprime_provenance),
                                     m7.dprime_provenance if tainted else 0.0)
                    self.assertEqual(i7.alarm, i7.alarm_patch or m7.detector.fires(i7.provenance))
                    self.assertEqual(i0.alarm, i0.alarm_patch)
                    o0 = i0.observation(t=4, requested=None, checkpoint=None)
                    o7 = i7.observation(t=4, requested=None, checkpoint=None)
                    self.assertIsNone(o0.provenance)
                    self.assertEqual(o7.provenance, i7.provenance)
            # provenance is one lookup: the same draw at every depth
            p1 = m7.commit(t=4, depth=1, has_marker=True, via="delegated", task_id="tk", seed=SEED)
            p3 = m7.commit(t=4, depth=3, has_marker=True, via="delegated", task_id="tk", seed=SEED)
            self.assertEqual(p1.provenance, p3.provenance)
            # sweeps: no provenance in either world
            st = CarrierStore()
            st.write(_item("skill", 1, poisoned=True))
            for m in (m0, m7):
                self.assertIsNone(m.sweep(t=2, target="skill", depth=1, store=st, seed=SEED).provenance)
            # A7 miss of a delegated patch: both scores under tau
            det = cell.detector()
            want = O.p_miss_commit(rho, det.d_prime, det.phi, dprime_provenance=det.d_prime)
            self.assertAlmostEqual(want, _N.cdf(det.tau_det - rho * det.d_prime)
                                   * _N.cdf(det.tau_det - det.d_prime), places=12)
            got = _miss_rate(m7, has_marker=True, via="delegated", depth=1, n=n)
            self.assertLess(abs(got - want), _mc_tol(want, n), f"A7 rho={rho}")
            self.assertLess(want, O.p_miss_commit(rho, det.d_prime, det.phi))
            # A7's false-alarm cost: either of two clean scores over tau
            fa = 1 - _miss_rate(m7, has_marker=False, via="", depth=1, n=n)
            want_fa = 1 - (1 - det.phi) ** 2
            self.assertLess(abs(fa - want_fa), _mc_tol(want_fa, n))

    # ---- H8: the insertion audit and the ingress channel ------------------------------

    def test_insertion_audit_blind_to_ingress_when_switch_off(self):
        """D10.6.ingress (H8): "Against audit-on-insertion, every best response inserts
        through repository ingress rather than direct write—the unaudited channel— which
        is why it is the worst policy."

        In the carrier world the insertion audit is the memory audit.  With
        ingress_visible=True (primary) it scores every live memory item; with False it
        does not see the items that entered through repository ingress (a world-side id
        set, like drift ids).  Only the insertion (memory) audit is blinded."""
        ingress = set()
        st = CarrierStore()
        note = st.write(_item("memory", 0, tag="note"))
        payload = st.write(_item("memory", 1, poisoned=True, tag="payload"))
        ingress.add(payload.item_id)
        via_ingress_skill = st.write(_item("skill", 2, poisoned=True, tag="skill"))
        ingress.add(via_ingress_skill.item_id)
        cell = C.Cell(rho=0.5, delta=4)
        hidden = dataclasses.replace(C.PRIMARY, ingress_visible=False)
        seen = O.ObservationModel(C.PRIMARY, cell, ingress_ids=ingress)
        blind = O.ObservationModel(hidden, cell, ingress_ids=ingress)

        a = seen.sweep(t=3, target="memory", depth=2, store=st, seed=SEED)
        b = blind.sweep(t=3, target="memory", depth=2, store=st, seed=SEED)
        self.assertEqual([it.item_id for it in a.items], [note.item_id, payload.item_id])
        self.assertEqual([it.item_id for it in b.items], [note.item_id])
        self.assertEqual(a.written_at, (0, 1))
        self.assertEqual(b.written_at, (0,))
        self.assertEqual(b.scores, a.scores[:1], "the visible item keeps its own draw")
        self.assertEqual(b.observation(t=3, requested=None, checkpoint=None).n_items, 1)
        # the other carriers are not the insertion audit: ingress stays visible there
        for m in (seen, blind):
            s = m.sweep(t=3, target="skill", depth=1, store=st, seed=SEED)
            self.assertEqual([it.item_id for it in s.items], [via_ingress_skill.item_id])
        # without a declared ingress set nothing is hidden
        self.assertEqual(len(O.ObservationModel(hidden, cell).sweep(
            t=3, target="memory", depth=1, store=st, seed=SEED).items), 2)

    # ---- D4.obs (D16): independent draws ----------------------------------------------

    def test_every_inspection_draws_an_independent_score(self):
        """D4.obs (D16): "It observes ot : alarm scores from an imperfect detector with
        true-positive rate ψ and false-positive rate φ, plus executable checkpoint outcomes."

        Every inspection draws a fresh score: the same item audited at two tasks gets two
        independent draws (the seed carries the task), while the same inspection replayed
        (same workflow seed, task, item) is reproducible."""
        cell = C.Cell(rho=0.5, delta=4)
        m = O.ObservationModel(C.PRIMARY, cell)
        st = CarrierStore()
        for i in range(400):
            st.write(_item("memory", 0, tag=f"n{i}"))
        a = m.sweep(t=5, target="memory", depth=1, store=st, seed=SEED)
        again = m.sweep(t=5, target="memory", depth=1, store=st, seed=SEED)
        b = m.sweep(t=6, target="memory", depth=1, store=st, seed=SEED)
        self.assertEqual(a.scores, again.scores)
        self.assertEqual(len(set(a.scores) & set(b.scores)), 0)
        xs, ys = a.scores, b.scores
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
        vx = sum((x - mx) ** 2 for x in xs) / len(xs)
        vy = sum((y - my) ** 2 for y in ys) / len(ys)
        corr = cov / math.sqrt(vx * vy)
        self.assertLess(abs(corr), 4 / math.sqrt(len(xs)), f"corr={corr:.3f}")
        for v in (vx, vy):
            self.assertLess(abs(v - 1.0), 0.3)
        # a different workflow seed is a different draw too
        c = m.sweep(t=5, target="memory", depth=1, store=st, seed=SEED + 1)
        self.assertNotEqual(a.scores, c.scores)
        # commit: one patch per task, each its own draw
        p = [m.commit(t=t, depth=1, has_marker=False, via="", task_id=f"task-{t}",
                      seed=SEED).scores[0] for t in range(50)]
        self.assertEqual(len(set(p)), 50)

    # ---- D8.detector (C15): no ground truth -------------------------------------------

    def test_detector_reads_no_ground_truth(self):
        """D8.detector (C15): "A shared learned anomaly detector across all systems, so
        that allocation—not detection quality—is the variable under study."

        One declared detector per cell, shared by every system (the model is built from
        the world and the cell only).  The alarm is a pure threshold on the observed
        scores; the defender's Observation names no item and no poison label; the
        realised (psi, phi) of a depth-1 sweep are the cell's declared operating point;
        and the pure mean functions the belief (T9) and rollout (T12) use are the ones the
        world draws from."""
        params = list(inspect.signature(O.ObservationModel).parameters)
        self.assertEqual(params[:2], ["world", "cell"])
        self.assertNotIn("policy", params)
        self.assertEqual(list(inspect.signature(O.ObservationModel.fires).parameters), ["self", "score"])
        banned = {"poisoned", "item_id", "items", "marker", "has_marker", "via", "k", "iota", "sigma"}
        self.assertFalse(banned & {f.name for f in dataclasses.fields(A.Observation)})
        n = 4000
        for dp in C.DPRIME_LEVELS:
            cell = C.Cell(rho=0.25, delta=4, dprime=dp)
            m = O.ObservationModel(C.PRIMARY, cell)
            psi, phi = cell.detector().psi, cell.detector().phi
            self.assertAlmostEqual(m.tau, _N.inv_cdf(1 - phi), places=12)
            st = CarrierStore()
            for i in range(n):
                st.write(_item("memory", 0, poisoned=(i % 2 == 0), tag=f"i{i}"))
            ins = m.sweep(t=1, target="memory", depth=1, store=st, seed=SEED)
            # the alarm is recomputed from the observed scores alone
            self.assertEqual(ins.firing, tuple(s > m.tau for s in ins.scores))
            self.assertEqual(ins.alarm, any(s > m.tau for s in ins.scores))
            obs = ins.observation(t=1, requested=A.AuditAction("memory", 1), checkpoint=None)
            self.assertEqual(obs.scores, ins.scores)
            self.assertEqual(obs.alarm, ins.alarm)
            tp = sum(f for f, it in zip(ins.firing, ins.items) if it.poisoned) / (n / 2)
            fp = sum(f for f, it in zip(ins.firing, ins.items) if not it.poisoned) / (n / 2)
            self.assertLess(abs(tp - psi), _mc_tol(psi, n // 2), f"psi d'={dp}")
            self.assertLess(abs(fp - phi), _mc_tol(phi, n // 2), f"phi d'={dp}")
        # the belief's pure means are the world's: depth 4 vs depth 1 on the same draw
        # moves each score by exactly item_mean(d' * 2) - item_mean(d')
        for drift in ("transient", "persistent"):
            cell = C.Cell(rho=0.25, delta=4)
            drift_ids = set()
            m = O.ObservationModel(dataclasses.replace(C.PRIMARY, drift=drift), cell,
                                   drift_ids=drift_ids)
            st = CarrierStore()
            pois = st.write(_item("memory", 2, poisoned=True, tag="p"))
            clean = st.write(_item("memory", 2, tag="c"))
            dr = st.write(_item("memory", 2, tag="d"))
            drift_ids.add(dr.item_id)
            for now in (2, 3):
                s1 = m.sweep(t=now, target="memory", depth=1, store=st, seed=SEED)
                s4 = m.sweep(t=now, target="memory", depth=4, store=st, seed=SEED)
                for it, a, b in zip(s1.items, s1.scores, s4.scores):
                    seen = it.item_id in drift_ids and O.drift_visible(it.created_at, now, drift)
                    want = (O.item_mean(it.poisoned, seen, O.sweep_dprime(m.dprime, 4))
                            - O.item_mean(it.poisoned, seen, O.sweep_dprime(m.dprime, 1)))
                    self.assertAlmostEqual(b - a, want, places=9, msg=f"{drift} t={now} {it.item_id}")
            self.assertEqual(O.drift_visible(2, 3, drift), drift == "persistent")
