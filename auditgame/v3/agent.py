"""v3/agent.py -- the mock agent of v3: SleeperMockAgent (plan T4; C8, Q3, O1, O2, H8, H19).

WHAT THE AGENT DOES AT TASK t (one call of run_task, after the runner's injection at iota)

    1. RETRIEVE.  v2's topic join at THETA (core.CarrierStore.retrieve), plus every live
       POISONED item: the attacker's own write is a shared note every task from iota on
       reads (O2, payload.retrieve), and an item the agent DERIVED from poison inherits
       that scope -- the skill of Fig. 1 t2 is induced at an "auth" task and runs at
       the "orm" task t5, which v2's topic join would never connect.  Benign items keep
       v2's topic join (`retrieve`).
    2. ACTIVATE.  A retrieved poisoned item ACTIVATES at t iff the task meets the target
       predicate of the payload it came from: v2's THETA rule of the ROOT payload's
       topic on the task's topic (payload.SleeperPayload.predicate; the root is found
       through the derived_from trail, so a skill carries its note's predicate and keeps
       it after the note is quarantined).  Retrieval alone never activates (C8).
    3. ADOPT.  The patch carries the marker iff some source activates and the adoption
       draw succeeds (adoption_rate): "patch mang marker chi khi vi tu thoa va adoption
       thanh cong".  The marked patch goes into the branch as a derived item.
    4. PROPAGATE.  note -> skill: a skill induced from a trajectory that retrieved
       poison inherits it (v2's rule, Fig. 1 t2).  note -> queue: a queued tool call
       left by such a trajectory inherits it too (Q3; v2 never did this), and it runs
       at a LATER task -- it is written after this task's retrieval, so the first task
       that can read it is t + 1, where it activates like any poisoned source.
       patch -> branch: step 3.  So c_t goes (1,0,0,0) -> (1,1,0,0) -> ... -> (1,1,0,1).
    5. ROUTE (patch_via, O1 / H19).  A marked patch is "delegated" iff one of the
       activating sources lives in a carrier the cell delegates (config.DELEGATED_BY_KD
       [K_d]: {skill}, {skill, queue}, {skill, queue, memory}); it is then the product of
       that skill / queued call and derives from those sources only (Fig. 1 t5: "The
       skill runs on a target where its poisoned step matters. A patch is produced."),
       even while the note it came from is still live and retrieved.  Otherwise the
       patch is "direct".  v2's rule was "delegated iff EVERY source is delegated"; the
       two agree whenever one source activates, which is all v2 ever had at sigma.
    6. DRIFT.  v2's StagedMockAgent drift, unchanged: carrier c draws
       seed_of(seed, t, "drift-v2", c) against draft_setup.BETA_WORLD[c] and writes a
       benign revision (world_v2.drift_content) on a future task's topic.  Drift items
       enter from the repository ("repo/docs/conventions.md", the payload's own
       provenance), so they are INGRESS writes (`ingress_ids`).  Whether a drift event
       stays anomalous for one task or forever is world.drift (`drift_anomalous`).
    7. SOLVE.  seed_of(seed, t, "solve") < solve_rate and nothing else (N4): no world
       switch, no kernel, no carrier state moves it (carrier_runner.survives).

DRAWS.  Seeds and draw order are StagedMockAgent's: r = Random(seed_of(seed, t)) gives
adoption, skill induction and the queue draw in that order.  v2 drew the skill uniform
only when something was retrieved, so a quarantine that emptied the retrieval shifted
the queue draw; v3 draws all three every task (`AgentMode.state_free_draws`), so every
draw is a function of (seed, t) alone -- what agent.MockAgent's docstring promised --
and two policies see the same agent on the same seed (common random numbers).

v2 COMPATIBILITY (plan T4 acceptance).  AgentMode(sleeper=False, queue_propagation=False,
state_free_draws=False, via_rule="all-delegated") -- V2_COMPAT -- is v2: retrieval is
the topic join and activation IS retrieval (v2's dormancy rule: the payload's topic
join at sigma is the trigger), no poison enters the queue, v2's draw order and route
rule.  tests/v3/test_infra_v2_compat.py checks it reproduces world_v2.StagedMockAgent
draw for draw on 20 dev workflows, so every later difference comes from the C points.

INGRESS (S10.3, H8).  `ingress_ids` holds the items that entered through repository
ingress rather than a direct write: every drift item, and the payload when the attacker
uses the ingress channel (the runner writes it with `ingress_write`).  The agent's own
writes (notes, skills, patches, queued calls) are never ingress.  world.ingress_visible
changes nothing the agent does; it only decides what the insertion (memory) audit sees
(`insertion_view`; v3/observe.py applies the same rule over the same id set).

GROUND TRUTH.  `drift_ids`, `ingress_ids`, the Outcome's `activated` / `patch_sources`
and every `poisoned` label are world-side: the runner reads them, a policy never does.

Stdlib only; imports v2, never patches it.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import draft_setup as D
import prose_world as _PW
import retrieval
from agent import MockAgent, _query
from core import CARRIERS, Item, seed_of
from world_v2 import OpenGates, StagedMockAgent, StagedOutcome, drift_content

from v3 import config as C
from v3 import payload as P

# ---------------------------------------------------------------------------------------
# The declared kernel (L1)
# ---------------------------------------------------------------------------------------

_NOMINAL = MockAgent()
#: (adoption, skill induction) per world.kernel: v2's tools/select_mixture.KERNELS, built
#: the same way (zeta = draft_setup.ZETA) and tested equal to it, not imported from a tool.
KERNELS = {"nominal": (0.85, 0.55),
           "low": (0.85 - D.ZETA, 0.55 - D.ZETA),
           "high": (min(1.0, 0.85 + D.ZETA), 0.55 + D.ZETA)}
#: Rates no kernel moves: v2's MockAgent defaults.
SOLVE_RATE = _NOMINAL.solve_rate            # 0.62 (N4: the solve draw is the world's own)
QUEUE_RATE = _NOMINAL.queue_rate            # 0.35
#: A skill / queued call left by a trajectory that retrieved poison carries it with
#: probability 1 (v2's skill rule, extended to the queue by Q3).
INHERIT_PROB = 1.0
#: Benign drift rate per carrier (D6 of v2).
DRIFT_RATES = dict(D.BETA_WORLD)
#: How long a drift event looks anomalous (D6 of v2, Prop. 5.11 of the theory note):
#: transient = the task it happens in (draft_setup.DRIFT_VISIBLE_TASKS), persistent = forever.
DRIFT_VISIBLE = {"transient": D.DRIFT_VISIBLE_TASKS, "persistent": None}
#: Patch routes (world_v2.StagedOutcome.patch_via): "" = the patch carries no marker.
VIAS = ("", "direct", "delegated")
VIA_RULES = ("any-delegated", "all-delegated")
#: The provenance of what enters through repository ingress (build.inject's payload and
#: StagedMockAgent's drift use the same string).
INGRESS_PROVENANCE = "repo/docs/conventions.md"


def kernel_of(world: C.WorldV3) -> dict:
    """The declared propagation kernel of a world (L1): every probability the agent uses."""
    adopt, skill = KERNELS[world.kernel]
    return {"adoption": adopt, "skill_induction": skill, "queue": QUEUE_RATE,
            "skill_inherits": INHERIT_PROB, "queue_inherits": INHERIT_PROB,
            "solve": SOLVE_RATE, "drift": dict(DRIFT_RATES),
            "drift_visible_tasks": DRIFT_VISIBLE[world.drift]}


@dataclass(frozen=True)
class AgentMode:
    """Which of v3's departures from v2 are on.  V3_MODE is the v3 world; V2_COMPAT
    reproduces world_v2.StagedMockAgent draw for draw (module docstring)."""
    sleeper: bool = True               # O2 retrieval of poison + predicate gating (C8)
    queue_propagation: bool = True     # a queued call inherits poison (Q3)
    state_free_draws: bool = True      # the three uniforms are drawn every task
    via_rule: str = "any-delegated"    # Fig. 1 t5; v2: "all-delegated"

    def __post_init__(self):
        if self.via_rule not in VIA_RULES:
            raise ValueError(f"via_rule={self.via_rule!r} is not one of {VIA_RULES}")


V3_MODE = AgentMode()
V2_COMPAT = AgentMode(sleeper=False, queue_propagation=False, state_free_draws=False,
                      via_rule="all-delegated")


@dataclass
class SleeperOutcome(StagedOutcome):
    """StagedOutcome plus the world-side facts of the v3 mechanics.

    activated      ids of the retrieved poisoned items that met their predicate at t
    patch_sources  carriers of the items the marked patch was produced from ("" if clean)
    ingress        ids of the items written through ingress during this task
    drift          ids of the drift items written during this task
    """
    activated: tuple = ()
    patch_sources: tuple = ()
    ingress: tuple = ()
    drift: tuple = ()


# ---------------------------------------------------------------------------------------
# Pure rules (shared with observe / belief so they cannot drift apart)
# ---------------------------------------------------------------------------------------

def drift_anomalous(created_at: int, now: int, drift: str) -> bool:
    """A drift event written at `created_at` still looks like poison at `now`."""
    window = DRIFT_VISIBLE[drift]
    return now >= created_at and (window is None or now - created_at < window)


def insertion_view(items, ingress_ids, ingress_visible: bool) -> list:
    """What the insertion (memory) audit sees of `items`: everything when the world's
    insertion audit sees ingress (primary, H8), else everything but ingress writes."""
    if ingress_visible:
        return list(items)
    return [it for it in items if it.item_id not in ingress_ids]


def route(sources, delegated, via_rule: str = "any-delegated") -> tuple:
    """(patch_via, the sources the patch is produced from) for a marked patch whose
    activating sources are `sources` (module docstring, step 5)."""
    if not sources:
        return "", ()
    dele = [it for it in sources if it.carrier in delegated]
    if via_rule == "all-delegated":
        return ("delegated" if len(dele) == len(sources) else "direct"), tuple(sources)
    if via_rule != "any-delegated":
        raise ValueError(f"via_rule={via_rule!r} is not one of {VIA_RULES}")
    return ("delegated", tuple(dele)) if dele else ("direct", tuple(sources))


def _all_items(store) -> dict:
    """item_id -> Item over every item ever written (quarantined ones too: a copy's
    trail runs through its removed source)."""
    return {it.item_id: it for k in CARRIERS for it in store.items[k]}


def roots_of(store, item: Item, index: dict | None = None) -> tuple:
    """The attacker writes the poison in `item` came from: poisoned items with no
    derived_from, reached through the poisoned parents of the trail.  Store order."""
    if not item.poisoned:
        return ()
    if not item.derived_from:
        return (item,)
    idx = _all_items(store) if index is None else index
    out, seen, todo = {}, set(), [item]
    while todo:
        cur = todo.pop()
        if cur.item_id in seen:
            continue
        seen.add(cur.item_id)
        if not cur.derived_from:
            out[cur.item_id] = cur
            continue
        todo.extend(idx[p] for p in cur.derived_from if p in idx and idx[p].poisoned)
    return tuple(out[i] for i in idx if i in out)


def meets_predicate(store, item: Item, task_topic, index: dict | None = None) -> bool:
    """The target predicate of the poison in `item` holds on the task: v2's THETA rule of
    a root payload's topic on the task's topic (payload.SleeperPayload.predicate)."""
    want = retrieval.as_topic(task_topic)
    return any(retrieval.retrieved(retrieval.as_topic(r.topic), want, retrieval.THETA)
               for r in roots_of(store, item, index))


def retrieve(store, task_topic) -> list:
    """Step 1: payload.retrieve (v2's topic join plus the attacker's live writes) plus
    every live item derived from poison.  Store order, no duplicates."""
    shared = {it.item_id for it in P.retrieve(store, task_topic)}
    return [it for it in store.live()
            if it.item_id in shared or (it.poisoned and it.derived_from)]


# ---------------------------------------------------------------------------------------
# The agent
# ---------------------------------------------------------------------------------------

@dataclass
class SleeperMockAgent(StagedMockAgent):
    """world_v2.StagedMockAgent with the v3 mechanics (module docstring).

    Inherited fields: solve_rate, adoption_rate, skill_induction_rate, queue_rate,
    drift_rates (per carrier), drift_ids.  New: the cell's delegated carriers, the
    mode, the world's drift and ingress switches, and ingress_ids.  One agent per
    episode, like v2: the runner builds it (for_cell) and deep-copies it with the
    episode state for snapshot/resume -- its only state is the two id sets."""
    delegated: tuple = C.DELEGATED_BY_KD[C.K_D_PRIMARY]
    mode: AgentMode = V3_MODE
    drift: str = "transient"
    ingress_visible: bool = True
    ingress_ids: set = field(default_factory=set)       # GROUND TRUTH, world side only

    @classmethod
    def for_cell(cls, world: C.WorldV3, cell: C.Cell, *, mode: AgentMode = V3_MODE,
                 adoption_rate: float | None = None) -> "SleeperMockAgent":
        """The agent of one (world, cell).  `adoption_rate` is the P3 calibration knob
        (p = P(marked patch | payload retrieved)); None = the world's kernel."""
        adopt, skill = KERNELS[world.kernel]
        return cls(solve_rate=SOLVE_RATE,
                   adoption_rate=adopt if adoption_rate is None else adoption_rate,
                   skill_induction_rate=skill, queue_rate=QUEUE_RATE,
                   drift_rates=dict(DRIFT_RATES), delegated=cell.delegated(), mode=mode,
                   drift=world.drift, ingress_visible=world.ingress_visible)

    # ---- declared views ------------------------------------------------------------
    def kernel(self) -> dict:
        return {"adoption": self.adoption_rate, "skill_induction": self.skill_induction_rate,
                "queue": self.queue_rate, "skill_inherits": INHERIT_PROB,
                "queue_inherits": INHERIT_PROB if self.mode.queue_propagation else 0.0,
                "solve": self.solve_rate, "drift": dict(self.drift_rates),
                "drift_visible_tasks": DRIFT_VISIBLE[self.drift]}

    def drift_anomalous(self, item: Item, now: int) -> bool:
        """Is `item` a drift event that still looks like poison at `now` (world.drift)?"""
        return item.item_id in self.drift_ids and drift_anomalous(item.created_at, now,
                                                                  self.drift)

    def insertion_view(self, items) -> list:
        return insertion_view(items, self.ingress_ids, self.ingress_visible)

    def is_ingress(self, item: Item) -> bool:
        return item.item_id in self.ingress_ids

    # ---- ingress ---------------------------------------------------------------------
    def mark_ingress(self, item: Item) -> Item:
        self.ingress_ids.add(item.item_id)
        return item

    def ingress_write(self, store, item: Item) -> Item:
        """Write `item` through repository ingress (the attacker's ingress channel)."""
        return self.mark_ingress(store.write(item))

    # ---- one task --------------------------------------------------------------------
    def retrieve(self, store, task_topic) -> list:
        return retrieve(store, task_topic) if self.mode.sleeper else store.retrieve(task_topic)

    def run_task(self, t, task, store, seed, marker="x", gates=None, wf_topics=()):
        mode = self.mode
        gates = gates or OpenGates()
        # The same function of `seed` as StagedMockAgent: the runner passes the
        # per-workflow seed (carrier_runner.rs_of, D19).
        r = random.Random(seed_of(seed, t))
        writes, queries = [], []
        retrieved_all = self.retrieve(store, task.topic)
        queries.append(_query("retrieve", task.topic, writes, retrieved_all))
        retrieved = gates.retrieval(retrieved_all)
        poisoned_seen = [it for it in retrieved if it.poisoned]
        if mode.sleeper and poisoned_seen:
            idx = _all_items(store)
            active = [it for it in poisoned_seen if meets_predicate(store, it, task.topic, idx)]
        else:
            active = list(poisoned_seen)              # v2: retrieval is activation
        adopt = r.random()
        if mode.state_free_draws:
            u_skill, u_queue = r.random(), r.random()
        patch_has_marker = bool(active) and adopt < self.adoption_rate
        via, sources = route(active, self.delegated, mode.via_rule) if patch_has_marker \
            else ("", ())

        def put(item, stage):
            if gates.admit(item, stage):
                writes.append(store.write(item))
                return True
            return False

        put(Item(carrier="memory", topic=task.topic,
                 content=_PW.benign(task.topic, task.task_id, "memory",
                                    f"[{task.topic}] ghi chú từ {task.task_id}"),
                 created_at=t, provenance="agent/notes", poisoned=False), "insertion")
        if retrieved and (u_skill if mode.state_free_draws else r.random()) \
                < self.skill_induction_rate:
            inherits = bool(poisoned_seen)
            put(Item(carrier="skill", topic=task.topic,
                     content=_PW.benign(task.topic, task.task_id, "skill",
                                        f"[{task.topic}] quy trình rút từ {task.task_id}"),
                     created_at=t, provenance="agent/skills", poisoned=inherits,
                     derived_from=tuple(it.item_id for it in poisoned_seen) if inherits else ()),
                "delegation")
        put(Item(carrier="branch", topic=task.topic,
                 content=_PW.benign(task.topic, task.task_id, "branch",
                                    f"[{task.topic}] commit {task.task_id}"),
                 created_at=t, provenance="agent/branch", poisoned=patch_has_marker,
                 derived_from=tuple(it.item_id for it in sources) if patch_has_marker else ()),
            "commit-lineage")
        if (u_queue if mode.state_free_draws else r.random()) < self.queue_rate:
            inherits = mode.queue_propagation and bool(poisoned_seen)
            put(Item(carrier="queue", topic=task.topic,
                     content=_PW.benign(task.topic, task.task_id, "queue",
                                        f"[{task.topic}] lời gọi treo {task.task_id}"),
                     created_at=t, provenance="agent/queue", poisoned=inherits,
                     derived_from=tuple(it.item_id for it in poisoned_seen) if inherits else ()),
                "delegation")

        drifted = []
        future = list(wf_topics[t + 1:]) or [task.topic]
        for c in CARRIERS:
            b = self.drift_rates.get(c, 0.0)
            rd = random.Random(seed_of(seed, t, "drift-v2", c))
            if b and rd.random() < b:
                topic = future[rd.randrange(len(future))]
                it = Item(carrier=c, topic=topic, content=drift_content(topic, task.task_id, c),
                          created_at=t, provenance=INGRESS_PROVENANCE, poisoned=False)
                # ground truth before any gate sees it (as StagedMockAgent)
                self.drift_ids.add(it.item_id)
                self.ingress_ids.add(it.item_id)
                drifted.append(it.item_id)
                put(it, "insertion")

        solved = random.Random(seed_of(seed, t, "solve")).random() < self.solve_rate
        return SleeperOutcome(retrieved=retrieved, writes=writes,
                              patch_has_marker=patch_has_marker, solved=solved,
                              queries=queries, patch_via=via,
                              activated=tuple(it.item_id for it in active),
                              patch_sources=tuple(it.carrier for it in sources),
                              ingress=tuple(drifted), drift=tuple(drifted))
