"""world_v2.py -- an agent the defender can GATE (D3), and benign drift (D6).

With open gates and no drift StagedMockAgent reproduces MockAgent draw for draw.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import build
import prose_world as _PW
from agent import MockAgent, Outcome, _query

#: Carriers whose influence reaches the patch through DELEGATED provenance (D20):
#: an induced skill or a queued tool call.  Draft lines 275-279: an artifact-only audit
#: "cannot distinguish 'this patch is the product of a poisoned skill' from 'this patch
#: is ordinary', because the distinguishing evidence is the skill's provenance".
DELEGATED = frozenset({"skill", "queue"})


@dataclass
class StagedOutcome(Outcome):
    """Outcome plus HOW the poison reached the patch: "" (clean), "direct", "delegated"."""
    patch_via: str = ""
from core import CARRIERS, Item, seed_of
from detector import Detector


class OpenGates:
    def retrieval(self, items):
        return list(items)

    def admit(self, item, stage: str) -> bool:
        return True


def drift_content(topic, task_id: str, carrier: str) -> str:
    """A benign revision padded to the payload's length (`size` is a scored feature)."""
    s = _PW.benign(topic, task_id, carrier, f"[{topic}] cập nhật quy ước {task_id}/{carrier}")
    return s if len(s) >= build.PAYLOAD_LENGTH else s.ljust(build.PAYLOAD_LENGTH, ".")


@dataclass
class StagedMockAgent(MockAgent):
    drift_rates: dict = field(default_factory=dict)
    drift_ids: set = field(default_factory=set)       # GROUND TRUTH, world side only

    def run_task(self, t, task, store, seed, marker, gates=None, wf_topics=()):
        gates = gates or OpenGates()
        # The same function of `seed` as MockAgent (tested draw for draw).  The RUNNER
        # passes a per-workflow seed (staged.py, D19) -- this class must not be called
        # with a bare experiment seed, or task t repeats across workflows.
        r = random.Random(seed_of(seed, t))
        writes, queries = [], []
        retrieved_all = store.retrieve(task.topic)
        queries.append(_query("retrieve", task.topic, writes, retrieved_all))
        retrieved = gates.retrieval(retrieved_all)
        poisoned_seen = [it for it in retrieved if it.poisoned]
        adopt = r.random()
        patch_has_marker = bool(poisoned_seen) and adopt < self.adoption_rate

        def put(item, stage):
            if gates.admit(item, stage):
                writes.append(store.write(item))
                return True
            return False

        put(Item(carrier="memory", topic=task.topic,
                 content=_PW.benign(task.topic, task.task_id, "memory",
                                    f"[{task.topic}] ghi chú từ {task.task_id}"),
                 created_at=t, provenance="agent/notes", poisoned=False), "insertion")
        if retrieved and r.random() < self.skill_induction_rate:
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
                 derived_from=tuple(it.item_id for it in poisoned_seen) if patch_has_marker else ()),
            "commit-lineage")
        if r.random() < self.queue_rate:
            put(Item(carrier="queue", topic=task.topic,
                     content=_PW.benign(task.topic, task.task_id, "queue",
                                        f"[{task.topic}] lời gọi treo {task.task_id}"),
                     created_at=t, provenance="agent/queue", poisoned=False), "delegation")

        future = list(wf_topics[t + 1:]) or [task.topic]
        for c in CARRIERS:
            b = self.drift_rates.get(c, 0.0)
            rd = random.Random(seed_of(seed, t, "drift-v2", c))
            if b and rd.random() < b:
                topic = future[rd.randrange(len(future))]
                it = Item(carrier=c, topic=topic, content=drift_content(topic, task.task_id, c),
                          created_at=t, provenance="repo/docs/conventions.md", poisoned=False)
                # GROUND TRUTH before any gate sees it: the insertion audit must score
                # drift as drift (match * d'), not as a clean item.  Kept even if rejected.
                self.drift_ids.add(it.item_id)
                put(it, "insertion")

        solved = random.Random(seed_of(seed, t, "solve")).random() < self.solve_rate
        via = ""
        if patch_has_marker:
            via = ("delegated" if all(it.carrier in DELEGATED for it in poisoned_seen)
                   else "direct")
        return StagedOutcome(retrieved=retrieved, writes=writes,
                             patch_has_marker=patch_has_marker, solved=solved,
                             queries=queries, patch_via=via)


@dataclass
class DriftDetector:
    """The shared detector, drift scored like poison (D6; `match` swept).

    D16: every inspection draws an INDEPENDENT score (the seed includes `now`), unlike
    v1's detector.score, which gives one item one score for life.  Theorem 4 counts
    informative samples; if a repeated audit returned the same number it would carry
    no information and the theorem could not be tested.
    """
    base: Detector
    drift_ids: set
    match: float = 1.0
    rho_patch: float = 1.0        # D20: exposure of a DELEGATED patch, as a fraction of d'
    d1: float | None = None       # depth-1 d'; depth does not help a delegated patch

    @property
    def d_prime(self) -> float:
        return self.base.d_prime

    def _mean(self, item) -> float:
        if item.poisoned:
            return self.base.d_prime
        if item.item_id in self.drift_ids:
            return self.match * self.base.d_prime
        return 0.0

    def score(self, item, now: int, seed: int) -> float:
        return random.Random(seed_of(seed, "v2-score", item.item_id, now)).gauss(self._mean(item), 1.0)

    def score_patch(self, has_marker: bool, task_id: str, seed: int, via: str = "direct") -> float:
        """D20.  A patch that carries the marker through DIRECT retrieval is seen with the
        (depth-scaled) d'.  One that got it through a skill or a queued call is seen with
        rho_patch * d'(depth 1): the evidence is in the provenance, which the commit audit
        does not read, so no depth recovers it (draft Theorem 4, "no amount of depth
        increases the number of informative samples")."""
        if not has_marker:
            mean = 0.0
        elif via == "delegated":
            mean = self.rho_patch * (self.d1 if self.d1 is not None else self.base.d_prime)
        else:
            mean = self.base.d_prime
        return random.Random(seed_of(seed, "v2-patch", task_id)).gauss(mean, 1.0)

    def fires(self, s: float) -> bool:
        return self.base.fires(s)

    def at_depth(self, depth: int) -> "DriftDetector":
        d1 = self.d1 if self.d1 is not None else self.base.d_prime
        return DriftDetector(self.base.at_depth(depth), self.drift_ids, self.match,
                             self.rho_patch, d1)
