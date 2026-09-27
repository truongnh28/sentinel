"""Infrastructure (T4 acceptance): v3's agent in V2_COMPAT mode IS v2's agent.

With the target predicate equal to v2's dormancy rule (retrieval by the topic join is the
trigger), no poison entering the queue, v2's draw order and v2's route rule,
v3.agent.SleeperMockAgent reproduces world_v2.StagedMockAgent draw for draw on 20 dev
workflows: the same retrieved items, the same writes (every field, so the same item_id
and therefore the same detector seed), the same marker, route and solve draw, the same
state queries and the same drift ground truth.  That is the evidence that every later
difference between v2 and v3 comes from the C points (C8, Q3), not from a rewrite."""
import unittest
from dataclasses import asdict

import build
import carrier_runner
import draft_setup as D
from core import CARRIERS, CarrierStore
from world_v2 import DELEGATED, StagedMockAgent
from v3 import agent as AG
from v3 import config as C
from v3 import corpus as CO

_N_WF = 20
_SEEDS = (1, 2)
_DELTAS = (0, 1, 4)


def _attacks(wf):
    """v2 placements (build.plan_poison_all, dormancy included) on every carrier and a
    few Deltas, earliest and latest, plus the clean run."""
    out = [None]
    for i, k in enumerate(CARRIERS):
        d = _DELTAS[i % len(_DELTAS)]
        cands = build.plan_poison_all(wf, k, d, 0.6)
        if cands:
            out += [cands[0], cands[-1]] if len(cands) > 1 else [cands[0]]
    return out


def _run(ag, wf, ps, seed, quarantine_after):
    """The runner's inject / agent part (carrier_runner.run_carrier), with an optional
    whole-memory quarantine after one task so a defender's interference is covered."""
    rs = carrier_runner.rs_of(wf, seed)
    store = CarrierStore()
    topics = [x.topic for x in wf.tasks]
    outs = []
    for t, task in enumerate(wf.tasks):
        if ps is not None and t == ps.iota:
            store.write(build.inject(CarrierStore(), wf, ps))
        outs.append(ag.run_task(t, task, store, seed=rs, marker=ps.marker if ps else "x",
                                wf_topics=topics))
        if t == quarantine_after:
            for it in store.live("memory"):
                store.quarantine(it.item_id)
    return outs, store


def _items(items):
    return [asdict(it) for it in items]


class TestInfraV2Compat(unittest.TestCase):

    def test_v2_compat_mode_reproduces_staged_mock_agent(self):
        """Infra (T4): V2_COMPAT reproduces world_v2.StagedMockAgent draw for draw on 20
        dev workflows, with v2's drift (BETA_WORLD) on, at K_d = 2 (v2's DELEGATED)."""
        self.assertEqual(set(C.DELEGATED_BY_KD[2]), set(DELEGATED))
        cell = C.Cell(rho=0.0, delta=4)
        n_eps = n_marked = n_via = 0
        for wf in CO.dev_workflows()[:_N_WF]:
            for ps in _attacks(wf):
                for seed in _SEEDS:
                    for q in (None, (ps.iota if ps else 0) + 1):
                        v2 = StagedMockAgent(drift_rates=D.BETA_WORLD)
                        v3 = AG.SleeperMockAgent.for_cell(C.PRIMARY, cell, mode=AG.V2_COMPAT)
                        o2, s2 = _run(v2, wf, ps, seed, q)
                        o3, s3 = _run(v3, wf, ps, seed, q)
                        where = (wf.wf_id, ps, seed, q)
                        self.assertEqual(len(o2), len(o3))
                        for t, (a, b) in enumerate(zip(o2, o3)):
                            self.assertEqual(_items(a.retrieved), _items(b.retrieved), (where, t))
                            self.assertEqual(_items(a.writes), _items(b.writes), (where, t))
                            self.assertEqual(
                                (a.patch_has_marker, a.solved, a.patch_via, a.queries),
                                (b.patch_has_marker, b.solved, b.patch_via, b.queries),
                                (where, t))
                            n_marked += a.patch_has_marker
                            n_via += a.patch_via == "delegated"
                        self.assertEqual(v2.drift_ids, v3.drift_ids, where)
                        self.assertEqual(s2.snapshot(), s3.snapshot(), where)
                        self.assertEqual(s2.quarantined, s3.quarantined, where)
                        n_eps += 1
        # the comparison exercised the paths it claims to cover
        self.assertGreater(n_eps, 4 * _N_WF)
        self.assertGreater(n_marked, 0)
        self.assertGreater(n_via, 0)

    def test_each_mode_switch_is_an_observable_departure_from_v2(self):
        """Infra (T4): each AgentMode switch is a real departure: flipping any single
        switch of V2_COMPAT to its v3 value, or all of them (V3_MODE), changes some write,
        marker or route on these dev episodes -- so the compatibility above is not
        vacuous for any of them.  (27/09: drift_size, the drift text sized to the
        payload, is the fifth switch.)"""
        cell = C.Cell(rho=0.0, delta=4)
        modes = {"v3": AG.V3_MODE,
                 "sleeper": AG.AgentMode(True, False, False, "all-delegated", "pad"),
                 "queue": AG.AgentMode(False, True, False, "all-delegated", "pad"),
                 "draws": AG.AgentMode(False, False, True, "all-delegated", "pad"),
                 "via": AG.AgentMode(False, False, False, "any-delegated", "pad"),
                 "drift": AG.AgentMode(False, False, False, "all-delegated", "payload")}
        key = lambda outs: [(_items(o.writes), o.patch_has_marker, o.patch_via) for o in outs]
        differs = {name: False for name in modes}
        for wf in CO.dev_workflows()[:_N_WF]:
            for ps in _attacks(wf):
                for seed in _SEEDS:
                    for q in (None, (ps.iota if ps else 0) + 1):
                        ref = key(_run(StagedMockAgent(drift_rates=D.BETA_WORLD), wf, ps,
                                       seed, q)[0])
                        for name, mode in modes.items():
                            if not differs[name]:
                                ag = AG.SleeperMockAgent.for_cell(C.PRIMARY, cell, mode=mode)
                                differs[name] = key(_run(ag, wf, ps, seed, q)[0]) != ref
        self.assertEqual(differs, {name: True for name in modes})


if __name__ == "__main__":
    unittest.main()
