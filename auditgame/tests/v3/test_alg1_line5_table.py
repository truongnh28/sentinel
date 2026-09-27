"""Algorithm 1 line 5 from the precomputed table (T14): v3/line5_table.py (bins, schema,
lookup, digest) and tools/v3_build_table.py (the dev build).

Each test protects the DCM rows of v3/dcm/T14.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  The builds here are tiny (2 dev workflows, 3
members, 2 attacker classes, R = 2): they check the plumbing, not a table value.  Run from
auditgame/.
"""
import inspect
import pathlib
import random
import tempfile
import unittest

import numpy as np

from core import CARRIERS, seed_of
from tools import v3_build_table as B
from v3 import api as A
from v3 import attackers as AT
from v3 import config as C
from v3 import library as LIB
from v3 import line5 as L5
from v3 import line5_table as T
from v3 import seal

CLASSES = AT.attacker_classes()
TINY_MEMBERS = LIB.MEMBERS[:2] + ("L-BT-u0.5-f0",)
TINY_CLASSES = CLASSES[:2]


def tiny_settings(**kw):
    args = dict(rhos=[0.25], pilot=True, members=TINY_MEMBERS, classes=TINY_CLASSES, r=2,
                r_max=2)
    args.update(kw)
    return B.settings_of(**args)


def tiny_build(jobs=1, **kw):
    return B.build(tcs=[B.table_cell(0.25)], deltas=[4], workflows=B.dev_workflows()[:2],
                   settings=tiny_settings(**kw), jobs=jobs, progress=None)


def synthetic_table(rho=0.25, built=(4,), fill=None, edges=(0.2, 0.4, 0.6, 0.8)):
    """A one-cell table whose L-hat entry at (d, h, b) is d*1e4 + h*100 + b everywhere.
    `fill`: bool [5, 14, 40] of filled keys (default: every key of the built Delta-hats)."""
    tc = B.table_cell(rho)
    cid = B.tc_id(tc)
    arr = T.empty_cell(len(LIB.MEMBERS), len(CLASSES))
    d, h, b = np.meshgrid(np.arange(len(T.DELTA_KEYS)), np.arange(1, T.H_MAX + 1),
                          np.arange(T.N_BINS), indexing="ij")
    code = (d * 10000 + h * 100 + b).astype(np.float32)
    arr["L"][:] = code[..., None, None]
    arr["se"][:] = 0.01
    arr["n"][:] = T.R
    arr["states"][:] = 1
    if fill is None:
        fill = np.zeros(arr["reason"].shape, bool)
        for dh in built:
            fill[T.delta_pos(dh)] = True
    arr["src"], arr["reason"] = T.resolve_fallbacks(fill, built)
    meta = {"members": list(LIB.MEMBERS), "classes": list(CLASSES),
            "cells": {cid: {**tc, "edges": list(edges), "built_deltas": list(built)}}}
    return T.Line5Table(meta, {cid: arr}), cid


def feats(p=0.5, top="memory", dmass=0.0):
    return A.BinFeatures(p_attack=p, top_carrier=top, delegated_mass=dmass)


class FixedBelief:
    def __init__(self, f):
        self.f = f

    def bin_features(self):
        return self.f


def _loss_low(snap, hyp, m, c, r):
    return 0.5 + 0.1 * (random.Random(seed_of("t14-low", m, c, r)).random() - 0.5)


def _loss_high(snap, hyp, m, c, r):
    return 5.0 * random.Random(seed_of("t14-high", m, c, r)).random()


class TestAlg1Line5Table(unittest.TestCase):

    def test_line5_table_is_built_on_dev_only(self):
        """D5.5.freeze -- "Adaptive attack development is performed on a development split,
        and both the defender policy and the attacker library are frozen before final
        evaluation on held-out repositories and held-out attacker policies." (S5.5 p.4)
        The table is built from dev workflows only; any other split, and any workflow that
        is not dev, is refused with seal.SealedSplit; the tool has no road to eval."""
        B.require_dev(B.DEV)
        other = "ev" + "al"
        for split in (other, "secondary", "primary", ""):
            with self.assertRaises(seal.SealedSplit):
                B.require_dev(split)
            with self.assertRaises(seal.SealedSplit):
                B.build(tcs=[B.table_cell(0.0)], deltas=[4], settings=tiny_settings(),
                        split=split, progress=None)
        from core import Task, Workflow
        fake = Workflow("not-dev", "repo/x", [Task(f"x-{i}", "repo/x", f"{i:07x}", "auth", "fix")
                                               for i in range(8)])
        with self.assertRaises(seal.SealedSplit):
            B.build(tcs=[B.table_cell(0.0)], deltas=[4], workflows=[fake],
                    settings=tiny_settings(), progress=None)
        # the workflows are corpus.dev_workflows(), and the source never touches the seal
        from v3 import corpus
        self.assertEqual([w.wf_id for w in B.dev_workflows()],
                         [w.wf_id for w in corpus.dev_workflows()])
        for mod in (B, T):
            src = inspect.getsource(mod)
            self.assertNotIn("eval_workflows(", src)
            self.assertNotIn("unseal(", src)
            self.assertNotIn("corpus.json", src)
        self.assertNotIn("import corpus", inspect.getsource(T))       # the table reads no split
        # the build's meta says dev, and names only dev workflows
        tab, _ = tiny_build()
        self.assertEqual(tab.meta["split"], B.DEV)
        dev_ids = {w.wf_id for w in corpus.dev_workflows()}
        self.assertTrue(set(tab.meta["workflows"]) <= dev_ids)

    def test_table_key_is_cell_deltahat_remaining_bin(self):
        """DA1.l5 -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust over a
        restricted library" (Alg. 1 line 5 p.3).  Q13, O16: the table's key is (table
        cell = rho, chi, detector of the primary world; Delta-hat; h = tasks left; belief
        bin = 5 p_attack levels x top carrier x delegated flag = 40)."""
        tab, cid = synthetic_table(built=(4, 8))
        # the table cell: rho, chi, detector -- not the cell's Delta, K_d or budget (O14, O15)
        base = C.Cell(rho=0.25, delta=4)
        for other in (C.Cell(rho=0.25, delta=8), C.Cell(rho=0.25, delta=0, k_delegated=3),
                      C.Cell(rho=0.25, delta=4, budget=C.BUDGET_LEVELS[-1])):
            self.assertEqual(C.table_key_id(other), C.table_key_id(base))
        self.assertEqual(C.table_key_id(base), cid)
        for other in (C.Cell(rho=0.5, delta=4), C.Cell(rho=0.25, delta=4, chi="2.11"),
                      C.Cell(rho=0.25, delta=4, dprime=C.DPRIME_LEVELS[0])):
            self.assertNotEqual(C.table_key_id(other), cid)
        # 40 bins, each (level, carrier, flag) exactly once
        self.assertEqual(T.N_BINS, 40)
        seen = {T.bin_of(l, c, f) for l in range(5) for c in range(4) for f in range(2)}
        self.assertEqual(seen, set(range(40)))
        for b in range(40):
            self.assertEqual(T.bin_of(*T.bin_coords(b)), b)
        # p_attack levels at the stored dev-quantile edges; the other two exact
        edges = tab.meta["cells"][cid]["edges"]
        self.assertEqual([T.p_level(p, edges) for p in (0.0, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0)],
                         [0, 1, 1, 2, 3, 4, 4])
        self.assertEqual(T.edges_of(np.linspace(0, 1, 101)), (0.2, 0.4, 0.6, 0.8))
        # lookup reads exactly (Delta-hat, h, bin) of the cell
        for dh, h, f in ((4, 1, feats(0.1, "memory", 0.0)), (8, 14, feats(0.95, "branch", 0.9)),
                         (4, 7, feats(0.5, "queue", 0.6)), (8, 3, feats(0.3, "skill", 0.2))):
            b = T.bin_key(f, edges)
            m = tab.lookup(L5.TableKey(cid, dh, h, f))
            self.assertIsInstance(m, A.LossMatrix)
            self.assertEqual(m.source, "table")
            self.assertEqual((m.members, m.classes), (LIB.MEMBERS, CLASSES))
            self.assertEqual(m.L[0][0], T.DELTA_KEYS.index(dh) * 10000 + h * 100 + b)
        # off-grid keys are refused, never approximated
        for bad in ((3, 5), (4, 0), (4, 15), (None, 5)):
            with self.assertRaises(KeyError):
                tab.lookup(L5.TableKey(cid, bad[0], bad[1], feats()))
        with self.assertRaises(KeyError):
            tab.lookup(L5.TableKey(C.table_key_id(C.Cell(rho=1.0, delta=4)), 4, 5, feats()))
        # TableSource builds the key from the episode: table cell, Delta-hat, H - t, b_t
        ctx = A.EpisodeContext(world=C.PRIMARY, cell=C.Cell(rho=0.25, delta=8), wf_id="w",
                               seed=1, H=10, budget=100.0, depths=base.depths(),
                               kappa=base.kappa(), delegated=base.delegated())
        src = L5.TableSource(tab)
        f = feats(0.7, "skill", 0.8)
        k = src.key(3, FixedBelief(f), 4, ctx)
        self.assertEqual((k.table_cell, k.delta_hat, k.h, k.features), (cid, 4, 7, f))
        m = src.matrix(3, FixedBelief(f), 100.0, 4, ctx)
        self.assertEqual(m.L[0][0], T.DELTA_KEYS.index(4) * 10000 + 7 * 100
                         + T.bin_key(f, edges))

    def test_table_build_is_deterministic(self):
        """DA1.l5, D7.freeze -- "Defender policies and the attacker library are serialised
        and hashed before final evaluation" (S7 p.5 Freezing).  The build is a function of
        dev and the declared settings: the same table content (digest) at 1 and 2 jobs,
        and the digest survives save / load (it pins content, not zip time stamps)."""
        t1, rep1 = tiny_build(jobs=1)
        t2, rep2 = tiny_build(jobs=2)
        self.assertGreater(len(rep1["values"]), 0)
        self.assertEqual(t1.digest(), t2.digest())
        # the declared source design travels in the table (plan T14 "Trang thai nguon")
        m = t1.meta
        self.assertEqual((m["s_max"], m["source_seeds"]), (32, [1, 2]))
        self.assertTrue(m["behaviour"].startswith("uniform mixture of the members, per task"))
        self.assertEqual((m["move_on_alarm_sources"], m["rollout_move_on_alarm"]), (True, False))
        self.assertIn("PILOT placeholder", m["line8_source"])
        self.assertTrue(all(v["states"] <= 32 for v in rep1["values"]))
        with self.assertRaises(ValueError):                    # only a pilot may skip tuning
            B.settings_of(rhos=[0.25], pilot=False)
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "t.npz"
            dg = t1.save(p)
            self.assertEqual(dg, t1.digest())
            self.assertEqual(T.table_digest(p), dg)
            self.assertEqual(T.Line5Table.load(p).digest(), dg)
            self.assertEqual(T.load_table(p).digest(), dg)             # T15's entry point
            self.assertTrue(callable(T.load_table(p).lookup))
            self.assertIsNone(T.table_digest(pathlib.Path(d) / "absent.npz"))
        # the seal and the v3 manifest read table_digest() with no argument
        self.assertEqual(inspect.signature(T.table_digest).parameters["path"].default, None)
        self.assertTrue(str(T.TABLE_PATH).endswith("v3_line5_table.npz"))

    def test_empty_bins_fall_back_with_a_reason(self):
        """DA1.l5 -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust over a
        restricted library" (Alg. 1 line 5 p.3).  O16, N3: an empty bin takes the nearest
        filled bin with the same h and says so; a row with no filled bin takes the nearest
        h; a Delta-hat the build did not cover is refused."""
        d4 = T.delta_pos(4)
        fill = np.zeros((len(T.DELTA_KEYS), T.H_MAX, T.N_BINS), bool)
        b_full = T.bin_of(2, CARRIERS.index("skill"), 1)
        fill[d4, 4, b_full] = True                        # h = 5: one bin
        fill[d4, 4, T.bin_of(0, 0, 0)] = True
        fill[d4, 9, T.bin_of(4, 3, 0)] = True             # h = 10
        tab, cid = synthetic_table(built=(4,), fill=fill)
        edges = tab.meta["cells"][cid]["edges"]
        # filled: its own values, no fallback note
        f = feats(0.5, "skill", 0.9)
        self.assertEqual(T.bin_key(f, edges), b_full)
        m = tab.lookup(L5.TableKey(cid, 4, 5, f))
        self.assertEqual(m.L[0][0], d4 * 10000 + 500 + b_full)
        self.assertNotIn("nearest", m.note)
        # empty bin, same h: the nearest filled bin (level 3, skill, flag 1 -> level 2 ...)
        f = feats(0.7, "skill", 0.9)
        b = T.bin_key(f, edges)
        self.assertNotEqual(b, b_full)
        self.assertEqual(T.nearest_bin(b, [b_full, T.bin_of(0, 0, 0)]), b_full)
        m = tab.lookup(L5.TableKey(cid, 4, 5, f))
        self.assertEqual(m.L[0][0], d4 * 10000 + 500 + b_full)
        self.assertIn(T.REASONS[T.REASON_NEAREST_BIN], m.note)
        self.assertIn(f"bin {b_full}", m.note)
        # ties go to the lower bin index; the distance is level + carrier + flag
        self.assertEqual(T.bin_distance(T.bin_of(0, 0, 0), T.bin_of(2, 1, 1)), 4)
        self.assertEqual(T.nearest_bin(T.bin_of(1, 0, 0), [T.bin_of(0, 0, 0), T.bin_of(2, 0, 0)]),
                         T.bin_of(0, 0, 0))
        # a row with no filled bin: nearest h (h = 8 -> h = 10 is 2 away, h = 5 is 3 away)
        m = tab.lookup(L5.TableKey(cid, 4, 8, feats(0.9, "branch", 0.0)))
        self.assertEqual(m.L[0][0], d4 * 10000 + 1000 + T.bin_of(4, 3, 0))
        self.assertIn(T.REASONS[T.REASON_NEAREST_H], m.note)
        # every key of a built Delta-hat answers, with a reason code
        rs = tab.cells[cid]["reason"][d4]
        self.assertTrue(set(np.unique(rs)) <= {T.REASON_FILLED, T.REASON_NEAREST_BIN,
                                                T.REASON_NEAREST_H})
        # a Delta-hat not built (a pilot) is refused, with the reason
        with self.assertRaisesRegex(KeyError, "not built"):
            tab.lookup(L5.TableKey(cid, 8, 5, feats()))
        # a built Delta-hat with no state at all is refused too
        src, reason = T.resolve_fallbacks(np.zeros_like(fill), (4,))
        self.assertTrue((reason[d4] == T.REASON_EMPTY).all())
        self.assertTrue((src[d4] == -1).all())

    def test_table_cell_se_below_declared_threshold(self):
        """DA1.l5 -- "at ← arg minπ ∈Π maxπA ∈ΠA b L(π, πA | bt , Bt ) ⊲ robust over a
        restricted library" (Alg. 1 line 5 p.3).  O12: every table cell has R = 32 rollouts
        per (member, class) and SE = sd / sqrt(n) <= 0.09; a cell over it is topped up once to
        R = 64, and one still over it is flagged, and its lookup note says so."""
        self.assertEqual((T.R, T.SE_MAX, T.R_MAX), (C.TABLE_R, C.TABLE_SE_MAX, 2 * C.TABLE_R))
        self.assertEqual((C.TABLE_R, C.TABLE_SE_MAX), (32, 0.09))
        st = B.settings_of(rhos=[0.25], pilot=True)
        self.assertEqual((st["r"], st["r_max"], st["se_max"]), (32, 64, 0.09))
        tc = B.table_cell(0.25)
        wf = B.dev_workflows()[0]
        state = (wf.wf_id, len(TINY_CLASSES), B.SOURCE_SEEDS[0], 2)  # unattacked, t = 2
        results = {}
        for name, fn in (("low", _loss_low), ("high", _loss_high)):
            s = B.settings_of(rhos=[0.25], pilot=True, members=TINY_MEMBERS,
                              classes=TINY_CLASSES, rollout_fn=fn)
            B._init_worker(s)
            results[name] = B.value_job((tc, 4, wf.H - 2, 0, [state]))
        low, high = results["low"], results["high"]
        # low variance: R = 32 is enough, SE = sd / sqrt(32), under 0.09, not flagged
        self.assertEqual(low["n"], 32)
        self.assertLessEqual(float(low["se"].max()), 0.09)
        self.assertFalse(low["se_flag"])
        v = [_loss_low(None, None, TINY_MEMBERS[0], TINY_CLASSES[0], r) for r in range(32)]
        self.assertAlmostEqual(float(low["se"][0, 0]), float(np.std(v, ddof=1) / np.sqrt(32)),
                               places=12)
        self.assertAlmostEqual(float(low["L"][0, 0]), float(np.mean(v)), places=12)
        # high variance: topped up to 64, still over, flagged
        self.assertEqual(high["n"], 64)
        self.assertGreater(float(high["se"].max()), 0.09)
        self.assertTrue(high["se_flag"])
        # a flagged cell's lookup says so
        tab, cid = synthetic_table()
        d4 = T.delta_pos(4)
        tab.cells[cid]["se_flag"][d4, 4, :] = True
        tab.cells[cid]["se"][d4, 4, :] = 0.2
        tab.cells[cid]["n"][d4, 4, :] = 64
        m = tab.lookup(L5.TableKey(cid, 4, 5, feats()))
        self.assertIn("> 0.09 after R = 64 (O12)", m.note)
        self.assertEqual(m.n[0][0], 64)
        m = tab.lookup(L5.TableKey(cid, 4, 6, feats()))
        self.assertNotIn("O12", m.note)
        self.assertEqual(m.n[0][0], 32)


if __name__ == "__main__":
    unittest.main()
