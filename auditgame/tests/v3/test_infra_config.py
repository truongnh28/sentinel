"""v3/config.py and v3/api.py hold the contract W1-W9 code against (T1).  Infrastructure:
no DCM row.  Run from auditgame/."""
import ast
import dataclasses
import json
import os
import pathlib
import subprocess
import sys
import unittest

import metrics
from v3 import api as A
from v3 import config as C

ROOT = pathlib.Path(__file__).resolve().parents[2]            # auditgame/

#: Pinned so that a change to the canonical serialisation (or to a field) is noticed:
#: cell_id keys the Delta-hat history and the line-5 table, so it must not move silently.
GOLDEN_CELL_ID = ("rho=0.25,delta=4 (primary axes)", "854ed6337459")


class TestInfraConfig(unittest.TestCase):
    # ---- the three tests the plan lists for T1 ---------------------------------------------

    def test_sensitivities_differ_from_primary_in_one_factor(self):
        names, worlds = zip(*C.sensitivities())
        self.assertEqual(len(set(names)), len(names))
        flipped = []
        for name, w in C.sensitivities():
            diff = [f for f in C.world_fields() if getattr(w, f) != getattr(C.PRIMARY, f)]
            self.assertEqual(len(diff), 1, f"{name} differs in {diff}")
            flipped.append(diff[0])
            self.assertEqual(C.world_name(w), name)
        # every model switch has its one-factor world, except the two the plan keeps out
        self.assertEqual(sorted(flipped),
                         sorted(set(C.world_fields()) - {"kernel", "line5"}))
        self.assertEqual(len(set(map(C.world_id, worlds)) | {C.world_id(C.PRIMARY)}),
                         len(worlds) + 1)

    def test_cell_id_is_stable_across_processes(self):
        cells = [C.Cell(rho=r, delta=d, chi=x, dprime=p)
                 for r in C.RHO_GRID for d in C.DELTA_AXIS
                 for x in C.CHI_LEVELS for p in C.DPRIME_LEVELS]
        here = [C.cell_id(c) for c in cells]
        self.assertEqual(len(set(here)), len(cells), "two cells share an id")
        code = ("import json, sys; from v3 import config as C; "
                "cells=[C.Cell(rho=r, delta=d, chi=x, dprime=p) for r in C.RHO_GRID "
                "for d in C.DELTA_AXIS for x in C.CHI_LEVELS for p in C.DPRIME_LEVELS]; "
                "print(json.dumps([C.cell_id(c) for c in cells]))")
        for hashseed in ("0", "12345"):
            env = dict(os.environ, PYTHONHASHSEED=hashseed)
            out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                                 capture_output=True, text=True, check=True).stdout
            self.assertEqual(json.loads(out), here, f"PYTHONHASHSEED={hashseed}")
        self.assertEqual(C.cell_id(C.Cell(rho=0.25, delta=4)), GOLDEN_CELL_ID[1],
                         "the canonical cell id moved: every Delta-hat history and table key moves with it")
        # numbers are normalised: an int rho / float delta is the same cell
        self.assertEqual(C.cell_id(C.Cell(rho=0, delta=4.0)), C.cell_id(C.Cell(rho=0.0, delta=4)))

    def test_api_record_has_every_field_metrics_read(self):
        have = set(A.record_fields())
        # every field the S9.3 metrics (and learning curve, controls, fidelity row) read
        declared = {f for fs in A.METRIC_FIELDS.values() for f in fs}
        self.assertEqual(sorted(declared - have), [])
        # every key v2's metrics_v2 reads off a record, so its readers apply unchanged
        tree = ast.parse((ROOT / "metrics_v2.py").read_text(encoding="utf-8"))
        v2_keys = {n.slice.value for n in ast.walk(tree)
                   if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                   and isinstance(n.slice.value, str) and isinstance(n.value, ast.Name)
                   and n.value.id in ("r", "rec", "row")}
        self.assertTrue(v2_keys, "metrics_v2 no longer reads records as r[...]: update this test")
        self.assertEqual(sorted(v2_keys - have), [])
        # Definition 1 is computable from a record with v2's declared lambdas
        rec = _record()
        self.assertAlmostEqual(metrics.loss(rec.harm, rec.fq, rec.t_lost),
                               1.0 + metrics.LAMBDA_Q * 1 + metrics.LAMBDA_T * 2)
        # identity: every field of both objects travels with the record
        self.assertEqual(set(rec.world), set(C.world_fields()))
        self.assertEqual(set(rec.cell), set(C.cell_fields()))

    # ---- the rest of the contract ---------------------------------------------------------

    def test_primary_matches_q1(self):
        """Q1: A0 x carrier sweep x every rho x harm locked at sigma x insertion audit sees
        ingress x transient drift x 1 seeded carrier; K_d = 2 (O1), chi 1.33, mid, b1."""
        self.assertEqual(C.PRIMARY.as_dict(), {
            "provenance": "A0", "audit_reading": "carrier", "harm": "locked",
            "ingress_visible": True, "drift": "transient", "n_seeded": 1,
            "kernel": "nominal", "line5": "table"})
        self.assertEqual(C.RHO_GRID, (0.0, 0.25, 0.5, 1.0))
        cell = C.Cell(rho=0.0, delta=4)
        self.assertEqual((cell.k_delegated, cell.chi, cell.dprime, cell.budget, cell.price_only),
                         (2, "1.33", 2.21, "b1", False))
        self.assertEqual(cell.delegated(), ("skill", "queue"))
        self.assertEqual(C.DELEGATED_BY_KD, {1: ("skill",), 2: ("skill", "queue"),
                                             3: ("skill", "queue", "memory")})
        for bad in ({"provenance": "A1"}, {"harm": "gone"}, {"n_seeded": 3},
                    {"ingress_visible": 1}, {"line5": "exact"}):
            with self.assertRaises(ValueError, msg=bad):
                C.WorldV3(**bad)

    def test_every_decided_o_value_is_declared(self):
        self.assertEqual(set(C.DECIDED_O), {f"O{i}" for i in range(1, 17)})
        self.assertEqual(C.DECIDED_O["O3"]["q"], 0.1)                  # 27/09: q = 0.1 (C12)
        self.assertEqual((C.DHAT_MIN_POSTMORTEMS, C.DHAT_PRIOR), (1, 1))
        self.assertFalse(C.N_A_SHARED_ROLLOUT)                          # O13: not used
        self.assertEqual((C.TABLE_R, C.TABLE_SE_MAX), (32, 0.09))       # O12
        self.assertEqual(C.N_BELIEF_BINS, 40)                           # O16
        json.dumps(C.DECIDED_O)                                         # hashable into a manifest

    def test_eval_sources_are_declared_rules_not_counts(self):
        """D-v3-1: SWE-rebench-V2 from 01/2024, 20 untouched families, cap 5, one pass,
        H ~ U{6..14}, no reuse; the SWE-bench one-pass split is secondary."""
        p, s = C.EVAL_SOURCE_PRIMARY, C.EVAL_SOURCE_SECONDARY
        self.assertEqual((p.dataset, p.created_from, p.n_families, p.cap_per_family),
                         ("nebius/SWE-rebench-V2", "2024-01", 20, 5))
        self.assertEqual((p.h_range, p.one_pass, p.reuse_instances), ((6, 14), True, False))
        self.assertEqual(s.builder_seed, 2027)
        self.assertEqual(C.EVAL_SOURCES, (p, s))
        self.assertFalse(any("workflow" in f.name for f in dataclasses.fields(C.EvalSource)),
                         "the number of eval workflows is T2's measurement, not a constant")

    def test_cell_rejects_values_off_the_grid(self):
        ok = dict(rho=0.5, delta=2)
        for bad in ({"rho": 0.3}, {"rho": True}, {"k_delegated": 4}, {"chi": "1.34"},
                    {"chi": 1.33}, {"dprime": 2.2}, {"budget": "3xBmin"},
                    {"price_only": True}):                               # price-only at 1.33
            with self.assertRaises(ValueError, msg=bad):
                C.Cell(**{**ok, **bad})
        po = C.Cell(rho=0.5, delta=2, chi="2.11", price_only=True)
        self.assertEqual(po.depths(), C.Cell(rho=0.5, delta=2).depths())  # keeps depth
        with self.assertRaises(ValueError):
            po.kappa()                                                  # budget.py's (T16)

    def test_headline_cells_and_the_rollout_source(self):
        heads = [C.Cell(rho=r, delta=d) for r in C.RHO_GRID for d in C.HEADLINE_DELTAS]
        self.assertTrue(all(c.is_headline() for c in heads))
        self.assertEqual(len(heads), 8)
        self.assertFalse(C.Cell(rho=0.0, delta=2).is_headline())
        self.assertFalse(C.Cell(rho=0.0, delta=4, dprime=1.52).is_headline())
        roll = dataclasses.replace(C.PRIMARY, line5="rollout")
        C.check_world_cell(roll, heads[0])
        with self.assertRaises(ValueError):
            C.check_world_cell(roll, C.Cell(rho=0.0, delta=1))
        # the table key ignores Delta and the non-table axes (O14, O15)
        self.assertEqual(C.table_key_id(C.Cell(rho=0.5, delta=4)),
                         C.table_key_id(C.Cell(rho=0.5, delta=8, k_delegated=3, budget="2xBmin")))
        self.assertNotEqual(C.table_key_id(C.Cell(rho=0.5, delta=4)),
                            C.table_key_id(C.Cell(rho=0.25, delta=4)))

    def test_record_round_trips_through_json(self):
        rec = _record()
        back = A.EpisodeRecord.from_dict(json.loads(rec.to_json()))
        self.assertEqual(back, rec)
        with self.assertRaises(ValueError):
            A.EpisodeRecord.from_dict({**rec.to_dict(), "surprise": 1})

    def test_policy_base_satisfies_the_policy_protocol(self):
        ctx = _ctx()
        pol = A.PolicyBase(ctx)
        self.assertIsInstance(pol, A.PolicyV3)
        self.assertEqual(pol.action("commit"), A.AuditAction("commit", 1))
        self.assertEqual(pol.action("memory"), A.AuditAction("memory", 3))
        self.assertIsNone(pol.act(0, ctx.budget))
        self.assertIsNone(pol.quarantine(0))
        self.assertEqual(pol.decision_log(), [])

    def test_observation_and_loss_matrix_shapes(self):
        obs = A.Observation(t=2, requested=A.AuditAction("memory", 3),
                            bought=A.AuditAction("memory", 3), scores=(0.1, 2.5),
                            alarm=True, written_at=(0, 1))
        self.assertEqual(obs.n_items, 2)
        self.assertNotIn("poisoned", {f.name for f in dataclasses.fields(A.Observation)})
        m = A.LossMatrix(members=("a", "b"), classes=("x",), L=((0.1,), (0.2,)),
                         se=((0.01,), (0.02,)), n=((32,), (32,)), source="table")
        self.assertEqual(len(m.L), 2)
        with self.assertRaises(ValueError):
            A.LossMatrix(members=("a",), classes=("x", "y"), L=((0.1,),), se=((0.0,),),
                         n=((1,),), source="table")
        pm = A.PostMortem(cell_id="c", wf_id="w", order=0, seed=1, k=("memory",), iota=2,
                          sigma=6, harm=1.0, H=9)
        self.assertEqual(pm.delay, 4)

    def test_episode_state_clone_is_deep(self):
        st = A.EpisodeState(wf_id="w", seed=1, t=3, remaining=10.0, store={"memory": [1]},
                            hidden=A.HiddenState(attacked=True, c=(1, 0, 0, 0)))
        cl = st.clone()
        cl.store["memory"].append(2)
        self.assertEqual(st.store, {"memory": [1]})

    def test_config_and_api_do_not_import_numpy(self):
        """Plan S2: numpy only in PF, rollout and table; the world core stays stdlib."""
        code = "import sys; from v3 import config, api; print('numpy' in sys.modules)"
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        self.assertEqual(out, "False")


def _ctx() -> A.EpisodeContext:
    cell = C.Cell(rho=0.25, delta=4)
    return A.EpisodeContext(world=C.PRIMARY, cell=cell, wf_id="wf-1", seed=1, H=9,
                            budget=9 * 4.1, depths=cell.depths(), kappa=cell.kappa(),
                            delegated=cell.delegated())


def _record() -> A.EpisodeRecord:
    ident = C.identity(C.PRIMARY, C.Cell(rho=0.25, delta=4))
    return A.EpisodeRecord(
        split="dev", **ident, delta=4, wf="wf-1", repo="django", H=9, order=0, seed=1,
        policy="B1", attack="R01", placement=None, k=("memory",), iota=1, sigma=5, eps=0.5,
        harm=1.0, solved_sigma=True, harm_locked_at=5, detected_at=None,
        missed_before_sigma=True, fq=1, true_q=0, false_removed=3, benign_inspected=7,
        clean_lost_branch=1, t_lost=2, n_solved=8, spent=36.9, budget=36.9,
        audits={"commit": 9}, c_traj=("0000", "1000", "1100"), quarantines=((3, "branch"),),
        delta_hat=None, n_incidents_seen=0, line5_source=None, decision_log_sha256="")


if __name__ == "__main__":
    unittest.main()
