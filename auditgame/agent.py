"""
agent.py -- The Agent interface + an offline MockAgent.

MockAgent reproduces EXACTLY the three mechanisms the framework has to test:
  1. topic-based retrieval
  2. the payload is adopted -> the patch carries a measurable signature
  3. AUTOMATIC PROPAGATION: the skill-induction step bakes the poison into a
     second carrier (memory -> skill), exactly like t1 -> t2 in manuscript Fig. 1

Determinism: every draw is seeded from (seed, t), NEVER from carrier state.  That
is what makes quarantine change outcomes through the ONE causal channel "what
could be retrieved", without perturbing the solve rate -- the condition for exact
replay.

FROZEN STRINGS.  The Vietnamese `content=` templates below are DATA, not prose,
and are deliberately left untranslated -- item_id is hashed from content and seeds
the detector.  See build.py's module docstring for the measured impact.
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from core import Item, CarrierStore, Task, seed_of

@dataclass
class Outcome:
    retrieved: list
    writes: list
    patch_has_marker: bool
    solved: bool              # did the agent solve the task (independent of the payload)

class Agent:
    def run_task(self, t: int, task: Task, store: CarrierStore,
                 seed: int, marker: str) -> Outcome: ...

@dataclass
class MockAgent(Agent):
    solve_rate: float = 0.62       # clean solve rate (a good SWE-bench agent is ~0.4-0.6)
    adoption_rate: float = 0.85    # probability of adopting a retrieved note
    skill_induction_rate: float = 0.55  # probability of inducing a skill from the trajectory
    queue_rate: float = 0.35       # probability of leaving a tool call pending

    def run_task(self, t, task, store, seed, marker):
        r = random.Random(seed_of(seed, t))          # deterministic in (seed, t)
        retrieved = store.retrieve(task.topic)
        poisoned_seen = [it for it in retrieved if it.poisoned]

        # (2) adopt the payload -> the patch carries the signature
        adopt = r.random()
        patch_has_marker = bool(poisoned_seen) and adopt < self.adoption_rate

        writes = []
        # the agent always records a note about the task it just did
        writes.append(store.write(Item(
            carrier="memory", topic=task.topic,
            content=f"[{task.topic}] ghi chú từ {task.task_id}",
            created_at=t, provenance="agent/notes", poisoned=False)))

        # (3) PROPAGATION: a skill induced from the trajectory inherits the poison
        if retrieved and r.random() < self.skill_induction_rate:
            inherits = bool(poisoned_seen)
            writes.append(store.write(Item(
                carrier="skill", topic=task.topic,
                content=f"[{task.topic}] quy trình rút từ {task.task_id}",
                created_at=t, provenance="agent/skills", poisoned=inherits,
                derived_from=tuple(it.item_id for it in poisoned_seen) if inherits else ())))

        # (4) D5 -- BRANCH: the long-lived branch, ACCUMULATING a commit per task.
        # This is the most expensive carrier (kappa=4.1) and also the most crowded,
        # so it is the clearest "hide in the crowd" spot: hard to CHOOSE to audit,
        # but easy to CLEAN once chosen (the runner sweeps every item, catching each
        # poisoned one with probability psi).
        # A commit carries the poison iff the patch carries the signature -- REAL
        # propagation, not staged.
        writes.append(store.write(Item(
            carrier="branch", topic=task.topic,
            content=f"[{task.topic}] commit {task.task_id}",
            created_at=t, provenance="agent/branch",
            poisoned=patch_has_marker,
            derived_from=tuple(it.item_id for it in poisoned_seen) if patch_has_marker else ())))

        # (5) D5 -- QUEUE: pending tool calls.  Sparser than branch, so it supplies
        # the LOW end of the n_c axis, against branch at the high end.
        if r.random() < self.queue_rate:
            writes.append(store.write(Item(
                carrier="queue", topic=task.topic,
                content=f"[{task.topic}] lời gọi treo {task.task_id}",
                created_at=t, provenance="agent/queue", poisoned=False)))

        solved = random.Random(seed_of(seed, t, "solve")).random() < self.solve_rate
        return Outcome(retrieved=retrieved, writes=writes,
                       patch_has_marker=patch_has_marker, solved=solved)
