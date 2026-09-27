"""The v3 mock agent (T4, v3/agent.py): propagation, the declared kernel, K_d, ingress,
drift and the solve draw.  Each test protects the DCM rows of v3/dcm/T04.csv that name
it; its docstring carries the id(s) and the verbatim draft sentence.  The runner (T6) is
not used: `episode` below plays its order inside a task (inject at iota, then the agent)
and reads c_t with T3's v3/state.py.  The bitvector half of
test_state_is_carrier_bitvector_with_propagation is T3's (test_s4_state_payload.py)."""
import math
import random
import unittest
from dataclasses import replace

import build
import carrier_runner
from core import CARRIERS, CarrierStore, Item, PoisonSpec, Task, Workflow, seed_of
from tools import select_mixture
from v3 import agent as AG
from v3 import config as C
from v3 import corpus as CO
from v3 import payload as P
from v3 import state as S

#: Figure 1's shape (as T3's test): H = 7, the note is written at t1 and the target task is
#: t5 (Delta = 4); t2..t4 touch other modules, t6 touches the target module again.
_FIG1 = ["cache", "auth", "routing", "serializer", "migration", "orm", "orm"]
_CELL = C.Cell(rho=0.0, delta=4)


def _wf(topics, wf_id="wf-t4", repo="repo/t4"):
    return Workflow(wf_id=wf_id, repo=repo,
                    tasks=[Task(task_id=f"{wf_id}-t{t}", repo=repo, base_commit=f"{t:07x}",
                                topic=tp, problem=f"fix {tp} #{t}")
                           for t, tp in enumerate(topics)])


def _forced(adopt=1.0, skill=1.0, queue=0.0, kd=2, mode=AG.V3_MODE, drift=None):
    """An agent with forced rates, so a path is followed without hunting seeds."""
    return AG.SleeperMockAgent(adoption_rate=adopt, skill_induction_rate=skill,
                               queue_rate=queue, drift_rates=drift or {},
                               delegated=C.DELEGATED_BY_KD[kd], mode=mode)


def episode(ag, wf, sleeper=None, seed=1, channel="write", quarantine=None):
    """Play one episode's inject/agent part.  Returns (outcomes, c after the injection at
    each task, c after the agent at each task, store).  `quarantine(t, store)` runs after
    the agent, as the runner's lines 8-9 would."""
    store, outs, c_in, c_out = CarrierStore(), [], [], []
    topics = [x.topic for x in wf.tasks]
    for t, task in enumerate(wf.tasks):
        if sleeper is not None and t == sleeper.iota:
            if channel == "ingress":
                ag.ingress_write(store, sleeper.item(wf))
            else:
                P.inject(store, wf, sleeper)
        c_in.append(S.c_of(store))
        outs.append(ag.run_task(t, task, store, seed=seed, wf_topics=topics))
        if quarantine is not None:
            quarantine(t, store)
        c_out.append(S.c_of(store))
    return outs, c_in, c_out, store


def _fig1_sleeper(wf, k="memory"):
    return next(p for p in P.plan_sleeper_all(wf, k, 4) if p.iota == 1)


def _one_task(ag, root_carrier, target="orm", task_topic="orm", seed=1, extra=()):
    """One task reading one attacker write in `root_carrier` whose predicate is `target`."""
    wf = _wf(["x", task_topic], wf_id=f"wf-one-{root_carrier}")
    store = CarrierStore()
    root = store.write(Item(carrier=root_carrier, topic=target, content=f"payload {target}",
                            created_at=0, provenance=AG.INGRESS_PROVENANCE, poisoned=True))
    for it in extra:
        store.write(it)
    out = ag.run_task(1, wf.tasks[1], store, seed=seed, wf_topics=[x.topic for x in wf.tasks])
    return out, store, root


def _se(p, n):
    return math.sqrt(p * (1 - p) / n)


class TestS4Agent(unittest.TestCase):

    # ------------------------------------------------------------- propagation (D4.state)

    def test_state_is_carrier_bitvector_with_propagation(self):
        """D4.state (C8, Q3): "State at task t is st = (ct , ι, σ) where ct ∈ {0, 1}K
        records which of K carriers (memory records, cached skills, tool queue entries,
        branch derivations) are poisoned".
        DF1.t5: "The skill runs on a target where its poisoned step matters. A patch is
        produced."

        Propagation half: the agent carries the poison note -> skill -> patch -> branch,
        so c_t goes (1,0,0,0) -> (1,1,0,0) -> ... -> (1,1,0,1); a queued call carries it
        too, and runs at a later task; the patch carries the marker only on a task that
        meets the predicate and only when adoption succeeds."""
        wf = _wf(_FIG1)
        sl = _fig1_sleeper(wf)
        self.assertEqual((sl.iota, sl.sigma), (1, 5))

        # --- note -> skill -> patch -> branch (queue off, every rate forced to 1)
        outs, c_in, c_out, store = episode(_forced(), wf, sl)
        bits_in = [S.bits(c) for c in c_in]
        bits_out = [S.bits(c) for c in c_out]
        self.assertEqual(bits_in[1], "1000")                   # the note, before the agent
        self.assertEqual(bits_out, ["0000", "1100", "1100", "1100", "1100", "1101", "1101"])
        # retrieval before sigma never marks a patch (C8: retrieved, not activated)
        for t in (1, 2, 3, 4):
            self.assertTrue(any(it.poisoned for it in outs[t].retrieved), t)
            self.assertEqual(outs[t].activated, (), t)
            self.assertFalse(outs[t].patch_has_marker, t)
        # sigma: the skill runs and produces the patch -> delegated, derived from the skill
        o5 = outs[5]
        self.assertTrue(o5.patch_has_marker)
        self.assertEqual(o5.patch_via, "delegated")
        self.assertEqual(set(o5.patch_sources), {"skill"})
        patch = next(w for w in o5.writes if w.carrier == "branch")
        self.assertTrue(patch.poisoned)
        self.assertEqual(S.lineage(store, patch), ("memory", "skill", "branch"))
        self.assertEqual(S.trail_problems(store), [])
        # the hops the poison made; ("branch", "skill") appears once t6 reads the t5 patch
        self.assertTrue({("memory", "skill"), ("skill", "branch")}
                        <= set(S.CarrierState.of(store).edges))
        self.assertNotIn(("memory", "branch"), S.CarrierState.of(store).edges)
        # t6 meets the predicate again ("a later task meeting it activates too", T3)
        self.assertTrue(outs[6].patch_has_marker)

        # --- the skill outlives the note: quarantining memory after t2 leaves (0,1,0,*)
        def drop_memory(t, st):
            if t == 2:
                for it in st.live("memory"):
                    st.quarantine(it.item_id)
        outs, _, c_out, store = episode(_forced(), wf, sl, quarantine=drop_memory)
        self.assertEqual([S.bits(c) for c in c_out][2:], ["0100", "0100", "0100", "0101", "0101"])
        self.assertEqual(outs[5].patch_via, "delegated")       # the skill keeps the predicate

        # --- note -> queued call -> patch: the call written at t1 runs at a later task
        outs, _, c_out, store = episode(_forced(skill=0.0, queue=1.0), wf, sl)
        self.assertEqual([S.bits(c) for c in c_out],
                         ["0000", "1010", "1010", "1010", "1010", "1011", "1011"])
        q1 = next(w for w in outs[1].writes if w.carrier == "queue")
        self.assertTrue(q1.poisoned)
        self.assertNotIn(q1.item_id, [it.item_id for it in outs[1].retrieved])  # not at t1
        self.assertIn(q1.item_id, [it.item_id for it in outs[2].retrieved])     # from t2 on
        self.assertEqual(outs[5].patch_via, "delegated")       # queue is delegated at K_d = 2
        self.assertEqual(set(outs[5].patch_sources), {"queue"})
        patch = next(w for w in outs[5].writes if w.carrier == "branch")
        self.assertEqual(S.lineage(store, patch), ("memory", "queue", "branch"))

        # --- adoption fails: the predicate holds at sigma but no patch is marked
        outs, _, c_out, _ = episode(_forced(adopt=0.0), wf, sl)
        self.assertTrue(outs[5].activated)
        self.assertFalse(any(o.patch_has_marker for o in outs))
        self.assertEqual(S.bits(c_out[-1]), "1100")

        # --- no retrieval of poison, no propagation: a clean episode keeps c = 0
        outs, _, c_out, _ = episode(_forced(queue=1.0), wf, None)
        self.assertTrue(all(c == (0, 0, 0, 0) for c in c_out))

        # --- the nominal kernel reaches every stage on dev-like runs (not forced)
        ag = AG.SleeperMockAgent.for_cell(C.PRIMARY, _CELL)
        reached = set()
        for seed in range(1, 41):
            ag.drift_ids.clear(), ag.ingress_ids.clear()
            _, _, c_out, _ = episode(ag, wf, sl, seed=seed)
            reached.update(S.bits(c) for c in c_out)
        self.assertTrue({"1100", "1101"} <= reached, reached)
        self.assertTrue(any(b[2] == "1" for b in reached), reached)   # queue reached too

    # ---------------------------------------------------------- kernel (D5.robust, L1)

    def test_propagation_probabilities_are_the_declared_kernel(self):
        """D5.robust (L1): "transition kernels are known up to a total-variation
        uncertainty ζ".

        The agent's propagation probabilities are the declared kernel: v2's nominal rates
        (adoption 0.85, skill induction 0.55, queue 0.35, solve 0.62) and the ζ = 0.10
        low / high kernels of tools/select_mixture.KERNELS; a skill or queued call left by
        a trajectory that read poison inherits it with probability 1.  Measured frequencies
        match within 4 standard errors, and every draw is a function of (seed, t) alone."""
        self.assertEqual(AG.KERNELS, select_mixture.KERNELS)
        self.assertEqual((AG.SOLVE_RATE, AG.QUEUE_RATE), (0.62, 0.35))
        self.assertEqual(AG.KERNELS["nominal"], (0.85, 0.55))
        for kern in C.KERNEL:
            world = replace(C.PRIMARY, kernel=kern)
            ag = AG.SleeperMockAgent.for_cell(world, _CELL)
            self.assertEqual((ag.adoption_rate, ag.skill_induction_rate), AG.KERNELS[kern])
            self.assertEqual((ag.queue_rate, ag.solve_rate), (AG.QUEUE_RATE, AG.SOLVE_RATE))
            self.assertEqual(ag.drift_rates, AG.DRIFT_RATES)
            k = ag.kernel()
            self.assertEqual(k, AG.kernel_of(world))
            self.assertEqual((k["skill_inherits"], k["queue_inherits"]), (1.0, 1.0))
        self.assertEqual(AG.SleeperMockAgent.for_cell(C.PRIMARY, _CELL,
                                                      adoption_rate=0.2).adoption_rate, 0.2)

        n = 3000
        for kern in ("nominal", "low"):
            ag = AG.SleeperMockAgent.for_cell(replace(C.PRIMARY, kernel=kern), _CELL)
            ag.drift_rates = {}
            adopt, skill = AG.KERNELS[kern]
            marked = skills = queued = poisoned_derived = derived = 0
            for seed in range(n):
                out, _, _ = _one_task(ag, "memory", seed=seed)
                self.assertEqual(len(out.activated), 1)
                marked += out.patch_has_marker
                for w in out.writes:
                    if w.carrier in ("skill", "queue"):
                        derived += 1
                        poisoned_derived += w.poisoned
                        skills += w.carrier == "skill"
                        queued += w.carrier == "queue"
            for got, p in ((marked, adopt), (skills, skill), (queued, AG.QUEUE_RATE)):
                self.assertLess(abs(got / n - p), 4 * _se(p, n), (kern, got / n, p))
            self.assertEqual(poisoned_derived, derived)          # inheritance w.p. 1

        # the draws are (seed, t) alone: the same seeds decide skill and queue whether or
        # not anything is retrieved (v2 skipped the skill draw on an empty retrieval)
        ag = _forced(adopt=0.85, skill=0.55, queue=0.35)
        wf = _wf(["a", "b"])
        for seed in range(200):
            empty = ag.run_task(1, wf.tasks[1], CarrierStore(), seed=seed)
            full, _, _ = _one_task(ag, "memory", target="zzz", task_topic="b", seed=seed)
            self.assertEqual([w.carrier == "queue" for w in empty.writes].count(True),
                             [w.carrier == "queue" for w in full.writes].count(True), seed)

    # ------------------------------------------------------------ K_d (DF1.attrib, H19)

    def test_kd_axis_sets_delegated_carriers(self):
        """DF1.attrib (H19, O1): "An audit that observes only the artifact cannot
        distinguish “this patch is the product of a poisoned skill” from “this patch is
        ordinary”, because the distinguishing evidence is the skill’s provenance."

        K_d sets which carriers reach the patch through delegated provenance: K_d = 1 ->
        {skill}, 2 -> {skill, queue} (v2's DELEGATED, D20), 3 -> {skill, queue, memory}.
        A marked patch is 'delegated' iff an activating source is in a delegated carrier;
        the branch is never delegated."""
        self.assertEqual(C.DELEGATED_BY_KD[2], ("skill", "queue"))
        for kd in C.KD_LEVELS:
            cell = C.Cell(rho=0.0, delta=4, k_delegated=kd)
            ag = AG.SleeperMockAgent.for_cell(C.PRIMARY, cell)
            self.assertEqual(ag.delegated, C.DELEGATED_BY_KD[kd])
            ag.adoption_rate, ag.drift_rates = 1.0, {}
            for k in CARRIERS:
                out, _, _ = _one_task(ag, k)
                self.assertTrue(out.patch_has_marker, (kd, k))
                want = "delegated" if k in C.DELEGATED_BY_KD[kd] else "direct"
                self.assertEqual(out.patch_via, want, (kd, k))
                self.assertEqual(out.patch_sources, (k,))
            # a note and the skill it propagated into: the skill produced the patch
            # (Fig. 1 t5), whatever K_d, and the patch derives from the delegated
            # sources only (the skill; the note too once K_d = 3 delegates memory)
            store = CarrierStore()
            note = store.write(Item(carrier="memory", topic="orm", content="payload orm",
                                    created_at=0, provenance=AG.INGRESS_PROVENANCE,
                                    poisoned=True))
            skill = store.write(Item(carrier="skill", topic="auth", content="skill auth",
                                     created_at=1, provenance="agent/skills", poisoned=True,
                                     derived_from=(note.item_id,)))
            out = ag.run_task(2, _wf(["a", "b", "orm"]).tasks[2], store, seed=3)
            self.assertEqual(out.patch_via, "delegated", kd)
            patch = next(w for w in out.writes if w.carrier == "branch")
            self.assertEqual(patch.derived_from,
                             tuple(it.item_id for it in (note, skill)
                                   if it.carrier in C.DELEGATED_BY_KD[kd]))
            self.assertEqual(patch.derived_from[-1], skill.item_id)
            # a direct and a non-delegated source together stay direct
            if "queue" not in C.DELEGATED_BY_KD[kd]:
                self.assertEqual(AG.route([note, replace(note, carrier="queue")],
                                          ag.delegated)[0], "direct")
        # the v2 rule, kept for V2_COMPAT: delegated only if EVERY source is delegated
        self.assertEqual(AG.route([note, skill], ("skill", "queue"), "all-delegated"),
                         ("direct", (note, skill)))
        self.assertEqual(AG.route([note, skill], ("skill", "queue")),
                         ("delegated", (skill,)))
        self.assertEqual(AG.route([], ("skill",)), ("", ()))

    # ------------------------------------------------------------------ ingress (H8)

    def test_ingress_visibility_is_a_switch(self):
        """D10.3.ingress (H8, L1): "Against audit-on-insertion, every best response
        inserts through repository ingress rather than direct write—the unaudited
        channel— which is why it is the worst policy."

        Whether the insertion audit sees ingress is a WORLD SWITCH, not a result: the
        agent does exactly the same thing under ingress_visible = True / False (same
        writes, same draws, same ingress set); the switch only decides whether the
        insertion (memory) view drops ingress writes.  Ingress writes are the drift items
        and the payload on the ingress channel, never the agent's own writes."""
        hidden = replace(C.PRIMARY, ingress_visible=False)
        self.assertIn(("ingress-hidden", hidden), C.sensitivities())
        wfs = CO.dev_workflows()[:8]
        n_ingress = n_hidden = 0
        for wf in wfs:
            sls = P.plan_sleeper_all(wf, "memory", 1)
            if not sls:
                continue
            sl = sls[0]
            runs = {}
            for world in (C.PRIMARY, hidden):
                ag = AG.SleeperMockAgent.for_cell(world, _CELL)
                self.assertEqual(ag.ingress_visible, world.ingress_visible)
                outs, _, c_out, store = episode(ag, wf, sl, seed=seed_of(wf.wf_id, 1),
                                                channel="ingress")
                runs[world.ingress_visible] = (ag, outs, c_out, store)
            (a1, o1, c1, s1), (a0, o0, c0, s0) = runs[True], runs[False]
            self.assertEqual(c1, c0)
            self.assertEqual(a1.ingress_ids, a0.ingress_ids)
            self.assertEqual(a1.drift_ids, a0.drift_ids)
            for x, y in zip(o1, o0):
                self.assertEqual([w.item_id for w in x.writes], [w.item_id for w in y.writes])
                self.assertEqual((x.patch_has_marker, x.patch_via, x.solved, x.ingress),
                                 (y.patch_has_marker, y.patch_via, y.solved, y.ingress))
            payload = sl.item(wf).item_id
            self.assertIn(payload, a1.ingress_ids)
            # ingress = the payload + every drift item; the agent's own writes never
            self.assertEqual(a1.ingress_ids, a1.drift_ids | {payload})
            for o in o1:
                for w in o.writes:
                    self.assertEqual(a1.is_ingress(w), w.item_id in a1.drift_ids)
            mem = s1.live("memory")
            seen_on, seen_off = a1.insertion_view(mem), a0.insertion_view(mem)
            self.assertEqual(seen_on, mem)
            self.assertEqual(seen_off, [it for it in mem if not a0.is_ingress(it)])
            self.assertNotIn(payload, [it.item_id for it in seen_off])
            n_ingress += sum(a1.is_ingress(it) for it in mem)
            n_hidden += len(mem) - len(seen_off)
        self.assertGreater(n_ingress, 0)
        self.assertEqual(n_hidden, n_ingress)
        # the direct-write channel is not ingress
        wf = _wf(_FIG1)
        ag = _forced()
        episode(ag, wf, _fig1_sleeper(wf), channel="write")
        self.assertEqual(ag.ingress_ids, set())

    # -------------------------------------------------------------- drift (D4.drift)

    def test_drift_transient_or_persistent_is_a_switch(self):
        """D4.drift (Prop. 5.11): "A latent process independently modifies carriers
        benignly at rate β, with observation statistics matched to poisoning events."

        The drift process is v2's (per-carrier rate draft_setup.BETA_WORLD, benign items
        padded to the payload's length, the payload's provenance); how long a drift event
        looks like poison is world.drift: the task it happens in (transient, primary) or
        forever (persistent).  The events themselves are the same under both."""
        persistent = replace(C.PRIMARY, drift="persistent")
        self.assertIn(("drift-persistent", persistent), C.sensitivities())
        self.assertEqual(AG.DRIFT_VISIBLE, {"transient": 1, "persistent": None})
        wfs = CO.dev_workflows()[:20]
        counts = {k: 0 for k in CARRIERS}
        n_tasks = 0
        for wf in wfs:
            runs = {}
            for world in (C.PRIMARY, persistent):
                ag = AG.SleeperMockAgent.for_cell(world, _CELL)
                self.assertEqual(ag.drift, world.drift)
                outs, _, c_out, store = episode(ag, wf, None, seed=seed_of(wf.wf_id, 2))
                runs[world.drift] = (ag, outs, store)
            (at, ot, st), (ap, op, sp) = runs["transient"], runs["persistent"]
            self.assertEqual(at.drift_ids, ap.drift_ids)
            self.assertEqual([[w.item_id for w in o.writes] for o in ot],
                             [[w.item_id for w in o.writes] for o in op])
            n_tasks += wf.H
            for it in st.live():
                if it.item_id not in at.drift_ids:
                    self.assertFalse(at.drift_anomalous(it, it.created_at))
                    self.assertFalse(ap.drift_anomalous(it, wf.H))
                    continue
                counts[it.carrier] += 1
                self.assertFalse(it.poisoned)
                self.assertEqual(it.provenance, AG.INGRESS_PROVENANCE)
                self.assertGreaterEqual(len(it.content), build.PAYLOAD_LENGTH)
                for now in range(it.created_at, wf.H):
                    self.assertEqual(at.drift_anomalous(it, now), now == it.created_at)
                    self.assertTrue(ap.drift_anomalous(it, now))
        # rate beta per (task, carrier): memory is the only carrier with enough mass here
        b = AG.DRIFT_RATES["memory"]
        self.assertLess(abs(counts["memory"] / n_tasks - b), 4 * _se(b, n_tasks),
                        (counts, n_tasks))
        if AG.DRIFT_RATES["branch"] == 0:
            self.assertEqual(counts["branch"], 0)

    # ------------------------------------------------------------------ solve (N4)

    def test_solved_draw_independent_of_world_switches(self):
        """D4.def1 (N4): "Defender loss is L = E[verified harm]+λQ E[false
        quarantines]+…λT E[clean tasks lost]".

        Clean tasks lost count tasks the agent would have solved, so `solved` must be the
        world's own draw: seed_of(rs, t, "solve") < 0.62, the same under every world switch
        (the six sensitivities, the three kernels), every K_d, with or without an attack,
        and equal to carrier_runner.survives."""
        worlds = ([C.PRIMARY] + [w for _, w in C.sensitivities()]
                  + [replace(C.PRIMARY, kernel=k) for k in ("low", "high")])
        cells = [C.Cell(rho=0.0, delta=4, k_delegated=kd) for kd in C.KD_LEVELS]
        for wf in CO.dev_workflows()[:6]:
            sls = P.plan_sleeper_all(wf, "skill", 1)
            for seed in (1, 2):
                rs = carrier_runner.rs_of(wf, seed)
                ref = [random.Random(seed_of(rs, t, "solve")).random() < 0.62
                       for t in range(wf.H)]
                for t in range(wf.H):
                    ps = PoisonSpec(carrier="memory", iota=0, sigma=t, epsilon=0.6)
                    self.assertEqual(carrier_runner.survives(wf, ps, seed), ref[t])
                for world in worlds:
                    for cell in cells:
                        for sl in (None, sls[0] if sls else None):
                            ag = AG.SleeperMockAgent.for_cell(world, cell)
                            outs, _, _, _ = episode(ag, wf, sl, seed=rs)
                            self.assertEqual([o.solved for o in outs], ref,
                                             (wf.wf_id, world, cell.k_delegated))


if __name__ == "__main__":
    unittest.main()
