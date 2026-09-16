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
from dataclasses import dataclass, field
from core import Item, CarrierStore, Task, seed_of

@dataclass
class Outcome:
    retrieved: list
    writes: list
    patch_has_marker: bool
    solved: bool              # did the agent solve the task (independent of the payload)
    #: Every STATE QUERY the agent put to the store, in order, with what came
    #: back: {kind, arg, after_writes, returned}.  SPEC-P1b Part 1 asks the
    #: retrieval row for "truy van gi . tra ve gi" -- WHAT WAS ASKED as well as
    #: what came back -- and the query is the half that makes offline replay
    #: CHECKABLE: replay re-executes each query against its own reconstructed
    #: store and compares.  If every answer matches, the recorded outcome is the
    #: outcome this agent would have produced, because the store is the only
    #: state-dependent input it has (see the determinism note above).  If one
    #: differs, a quarantine has changed what could be retrieved, and replay must
    #: DECLARE that instead of scoring on.
    #: `after_writes` is how many of `writes` were already in the store when the
    #: query ran, so replay can interleave the writes and the queries in order.
    queries: list = field(default_factory=list)


def _query(kind: str, arg, writes_so_far: list, returned: list) -> dict:
    """One recorded state query.  See Outcome.queries."""
    return dict(kind=kind, arg=arg, after_writes=len(writes_so_far),
                returned=[it.item_id for it in returned])


class Agent:
    def run_task(self, t: int, task: Task, store: CarrierStore,
                 seed: int, marker: str) -> Outcome: ...

@dataclass
class MockAgent(Agent):
    solve_rate: float = 0.62       # clean solve rate (a good SWE-bench agent is ~0.4-0.6)
    adoption_rate: float = 0.85    # probability of adopting a retrieved note
    skill_induction_rate: float = 0.55  # probability of inducing a skill from the trajectory
    queue_rate: float = 0.35       # probability of leaving a tool call pending
    drift_rate: float = 0.0        # beta -- BENIGN churn, see run_task step (6)

    def run_task(self, t, task, store, seed, marker):
        r = random.Random(seed_of(seed, t))          # deterministic in (seed, t)
        writes = []
        queries = []
        retrieved = store.retrieve(task.topic)
        queries.append(_query("retrieve", task.topic, writes, retrieved))
        poisoned_seen = [it for it in retrieved if it.poisoned]

        # (2) adopt the payload -> the patch carries the signature
        adopt = r.random()
        patch_has_marker = bool(poisoned_seen) and adopt < self.adoption_rate

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

        # (6) BENIGN DRIFT (beta).  An ordinary revision of an earlier note: the
        # agent refines something it wrote before.  This is the COMPETING LATENT
        # CAUSE -- without it, the only thing that ever changes a carrier is the
        # attacker, so "was this change benign?" is not a question the world can
        # pose and lambda_Q prices a risk that does not exist.
        #
        # Seeded on (seed, t, "drift") rather than reusing `r`, so turning drift on
        # does not consume draws from the stream that decides adoption or skill
        # induction.  Otherwise beta=0 and beta>0 would differ in every outcome and
        # nothing could be attributed to drift itself.
        rd = random.Random(seed_of(seed, t, "drift"))
        if self.drift_rate and rd.random() < self.drift_rate:
            # store.live("memory") is a SECOND state-dependent channel, so it is
            # logged like the retrieval.  It is read inside the branch, and the
            # branch is decided by `rd` alone -- state cannot move it -- so the
            # log is complete: a replay that reproduces every recorded answer
            # reproduces every state read this agent performed.
            live_memory = store.live("memory")
            queries.append(_query("live", "memory", writes, live_memory))
            prior = [x for x in live_memory if not x.poisoned]
            if prior:
                old = prior[rd.randrange(len(prior))]
                writes.append(store.write(Item(
                    carrier="memory", topic=old.topic,
                    content=f"{old.content} (rev {t})",
                    created_at=t, provenance="agent/notes/drift", poisoned=False)))

        solved = random.Random(seed_of(seed, t, "solve")).random() < self.solve_rate
        return Outcome(retrieved=retrieved, writes=writes,
                       patch_has_marker=patch_has_marker, solved=solved,
                       queries=queries)
