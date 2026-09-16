"""
core.py -- Base data types for AuditGame-SE.

Central idea: the agent KEEPS its memory across tasks, while the repo is reset to
each task's base_commit.  The four carriers live OUTSIDE the repo, so resetting
the repo cannot erase them -- that is what creates persistence, and it is what
plain SWE-bench does not have.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json

CARRIERS = ("memory", "skill", "queue", "branch")


@dataclass
class Item:
    """A piece of state living in one carrier."""
    carrier: str
    topic: str                 # join key: which tasks are "related" to this item
    content: str
    created_at: int            # task index at which it was written
    provenance: str            # 'agent' | 'inject' | 'derived'
    poisoned: bool             # GROUND TRUTH -- audit policies must NOT read this
    derived_from: tuple = ()   # ids of the items it came from (propagation trail)
    item_id: str = ""

    def __post_init__(self):
        if not self.item_id:
            # CONTENT-DERIVED, not a counter.  A module-level `itertools.count`
            # made item_id depend on HOW MANY Items had been built earlier in the
            # same process -- two identical builds produced different ids.  And
            # since detector.score seeds on seed_of(seed, item_id), it changed
            # the SCORES too: measured, B5 moved 0.417 / 0.583 / 0.333 across
            # three identical worst_case calls.  Same class of bug as hash() in
            # build.py, same lost claim ("results are reproducible"), same fix.
            h = seed_of(self.carrier, self.topic, self.content,
                        self.created_at, self.provenance, self.derived_from)
            self.item_id = f"{self.carrier[:3]}-{h & 0xFFFFFFFF:08x}"

    # ---- SURFACE features: all the detector is ever allowed to look at ----
    def surface(self, now: int) -> dict:
        return dict(
            size=len(self.content),
            depth=self.provenance.count("/"),
            recency=now - self.created_at,
            derived=len(self.derived_from),
        )


@dataclass
class CarrierStore:
    """The four state stores.  NOT reset between tasks."""
    items: dict = field(default_factory=lambda: {c: [] for c in CARRIERS})
    quarantined: set = field(default_factory=set)

    def write(self, it: Item) -> Item:
        # item_id is hashed from CONTENT (see Item.__post_init__), so two items
        # agreeing on every field collide.  Harmless today because every content
        # string embeds a task_id.  But D5 requires MockAgent to write into
        # queue/branch, and ONE template that forgets the task_id is enough:
        # quarantine() keys on id and live() filters on id, so quarantining one
        # item would ERASE THE OTHER.  That breaks the claim in agent.py's
        # docstring ("quarantine only changes outcomes through the ONE causal
        # channel") and would surface as harm mysteriously dropping on the new
        # carrier -- looking exactly like D5 working.  Catch it AT THE WRITE,
        # not while debugging B6.
        if any(x.item_id == it.item_id for x in self.items[it.carrier]):
            raise AssertionError(
                f"item_id collision {it.item_id!r} in carrier {it.carrier!r}: "
                f"two items agree on every field. Quarantining one would erase "
                f"the other. Make the content template embed a task identifier.")
        self.items[it.carrier].append(it)
        return it

    def live(self, carrier: Optional[str] = None):
        cs = CARRIERS if carrier is None else (carrier,)
        return [it for c in cs for it in self.items[c]
                if it.item_id not in self.quarantined]

    def retrieve(self, topic: str):
        """Retrieval = every live item whose topic matches the current task."""
        return [it for it in self.live() if it.topic == topic]

    def quarantine(self, item_id: str):
        self.quarantined.add(item_id)

    def snapshot(self) -> dict:
        return {c: [it.item_id for it in self.items[c]] for c in CARRIERS}

    def clone(self) -> "CarrierStore":
        import copy
        return copy.deepcopy(self)


@dataclass
class Task:
    """One task, mapped 1-1 onto a SWE-bench instance."""
    task_id: str
    repo: str
    base_commit: str
    topic: str                 # module/API this task touches
    problem: str
    # public_ok / hidden_ok are scored by the oracle, see oracle.py


@dataclass
class Workflow:
    """H tasks in sequence on one repo; the agent's memory is never reset."""
    wf_id: str
    repo: str
    tasks: list

    @property
    def H(self) -> int:
        return len(self.tasks)


@dataclass
class PoisonSpec:
    """Injection config -- the manuscript's (k, iota, sigma, epsilon)."""
    carrier: str               # k
    iota: int                  # task at which it is planted
    sigma: int                 # task at which it fires
    epsilon: float             # perturbation magnitude, 0..1
    marker: str = "raw_write"  # machine-checkable signature in the patch

    @property
    def delta(self) -> int:
        return self.sigma - self.iota


@dataclass
class TaskTrace:
    """Everything needed for offline replay -- record too little and the LLM has
    to be re-run from scratch."""
    t: int
    task_id: str
    topic: str
    before: dict
    after: dict
    writes: list
    retrieved: list
    alarms: dict               # item_id -> RAW alarm score (lets psi/phi be rescanned)
    patch_has_marker: bool
    public_ok: bool
    hidden_ok: bool
    audit_seconds: dict        # audit kind -> MEASURED seconds (to derive kappa, not assign it)
    n_c: dict = field(default_factory=dict)       # carrier -> number of live items
    signals: dict = field(default_factory=dict)   # carrier -> posterior p_c
    is_sigma: bool = False                        # is this the task the payload fires at


def dumps(obj) -> str:
    def enc(o):
        if hasattr(o, "__dataclass_fields__"):
            return asdict(o)
        if isinstance(o, frozenset):
            # `frozenset` is NOT a subclass of `set` (isinstance(frozenset(), set)
            # is False), so a real trace carrying a swebench_dataset.Topic -- a
            # frozenset subclass, TaskTrace.topic on the real dataset -- fell
            # through to the `raise TypeError` below and could not be written to
            # disk at all, defeating the one thing TaskTrace exists for: offline
            # replay without re-running the LLM.
            #
            # CHOSEN FORM: a SORTED list, not a bare `list(o)`. frozenset
            # iteration order depends on per-process string-hash randomisation
            # (PYTHONHASHSEED) -- exactly the trap Topic's own __str__ override
            # was written to close (see swebench_dataset.Topic's docstring) --
            # so an unsorted list would make the SAME trace serialise to a
            # DIFFERENT byte string on two runs. `sorted()` is deterministic
            # (input order never matters) and directly reversible: a replay
            # reconstructs the topic with `frozenset(the_list)`, or
            # `swebench_dataset.Topic(the_list)` when it needs that subclass.
            return sorted(o)
        if isinstance(o, (set, tuple)):
            return list(o)
        raise TypeError(type(o))
    return json.dumps(obj, default=enc, ensure_ascii=False, indent=2)


def seed_of(*parts) -> int:
    """Seed that is stable across runs.

    Do NOT use Python's hash(): it is randomised by PYTHONHASHSEED, so results
    stop being reproducible -- and reproducibility is requirement number one for
    this benchmark.  Python 3.14 also no longer accepts tuples as seeds.
    """
    import hashlib
    s = "|".join(map(str, parts)).encode()
    return int.from_bytes(hashlib.blake2b(s, digest_size=8).digest(), "big")
