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

import retrieval

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

    def retrieve(self, topic, theta: Optional[float] = None):
        """Retrieval = every live item whose topic MATCHES the current task's,
        where "matches" is Jaccard over module tokens at the frozen
        `retrieval.THETA` (SPEC-R-Truy-xuat.md Part 2.2).

        This used to be `it.topic == topic`, i.e. theta = 1.0, and that single
        `==` was the bottleneck under advisor question 3:

          * `epsilon` had NO SURFACE.  The payload's topic is a subset of task
            sigma's, and a strict subset never equals it, so every epsilon < 1
            would have reported harm 0 -- one of the attacker's four knobs
            (k, iota, sigma, epsilon) reduced to decoration.
          * On real data the join key almost never fires: only 1.79% of
            intra-workflow task pairs shared a topic exactly, so SPEC-P1a Part 4
            step 4 dropped all 58 Verified workflows and the corpus was empty.

        Exact matching is NOT replaced, it is the special case theta = 1.0 with
        equal token sets -- and on the mock, whose topics are single tokens, it
        is the special case at EVERY theta in (0, 1]: Jaccard on one-token sets
        takes only {0, 1}.  So the mock table must not move by a single digit;
        see retrieval.as_topic.

        `theta` is exposed only so a test can perturb it and watch the claim go
        red.  The runner never passes it: a per-call threshold would be a free
        parameter sitting in the measurement path, and theta is frozen.
        """
        th = retrieval.THETA if theta is None else theta
        want = retrieval.as_topic(topic)
        return [it for it in self.live()
                if retrieval.retrieved(retrieval.as_topic(it.topic), want, th)]

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
    to be re-run from scratch.

    The nine rows of SPEC-P1b-Trace.md Part 1, and the field each one lands in:

        state        4 carriers before and after      before / after
        writes       content . provenance . timestamp writes (+ injected)
        retrieval    WHAT WAS ASKED . what came back  queries (+ retrieved)
        scores       RAW per-item score, pre-threshold alarms
        n_c          live items per carrier           n_c
        checkpoint   P1..P5                           checkpoints
        quarantine   WHICH item, right or wrong       quarantines
        result       the patch produced . public/hidden agent_marker / public_ok / hidden_ok
        cost         MEASURED seconds per audit kind  audit_seconds

    Two of those fields are easy to get subtly wrong:

      `writes` holds FULL ITEM RECORDS, not ids.  item_id is blake2b of the
      content, so it is a ONE-WAY function: a list of ids cannot rebuild the
      carrier, and the row exists precisely so the carrier can be rebuilt.

      `agent_marker` is the marker the AGENT produced.  `patch_has_marker` is
      what survived the commit audit -- runner.run_once sets it to False when the
      audit catches the patch.  Replay under a DIFFERENT policy needs the
      pre-audit value; scoring the post-audit one would bake configuration A's
      commit audit into every cell replayed out of that trace.
    """
    t: int
    task_id: str
    topic: str
    before: dict
    after: dict
    writes: list               # full item RECORDS (see item_record), in write order
    retrieved: list
    alarms: dict               # item_id -> RAW alarm score (lets psi/phi be rescanned)
    patch_has_marker: bool     # AFTER the commit audit may have stopped it
    public_ok: bool
    hidden_ok: bool
    audit_seconds: dict        # audit kind -> MEASURED seconds (to derive kappa, not assign it)
    n_c: dict = field(default_factory=dict)       # carrier -> number of live items
    signals: dict = field(default_factory=dict)   # carrier -> posterior p_c
    is_sigma: bool = False                        # is this the task the payload fires at
    #: The run seed.  detector.score seeds on (seed, item_id), so a trace without
    #: it cannot be re-scored under any detector at all.
    seed: Optional[int] = None
    #: Every STATE QUERY the agent made, in order: {kind, arg, after_writes,
    #: returned}.  This is the "truy van gi" half of the retrieval row, and it is
    #: also what makes the replay validity condition CHECKABLE -- see replay.py.
    queries: list = field(default_factory=list)
    #: The payload record, on the task where it was planted; None elsewhere.
    injected: Optional[dict] = None
    #: One entry per quarantined item, WITH the manifest verdict.  The only
    #: offline route to lambda_Q; a scalar count cannot supply it.
    quarantines: list = field(default_factory=list)
    #: P1..P5 on the SIGMA task.  Empty elsewhere, and empty when nothing was
    #: injected -- N3: an out-of-scope cell records nothing, not a row of False.
    checkpoints: dict = field(default_factory=dict)
    #: The marker on the patch the AGENT produced, before any commit audit.
    agent_marker: Optional[bool] = None
    #: The audit action actually taken (accounting; replay derives its own).
    action: Optional[str] = None


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
        if isinstance(o, set):
            # Same reason as the frozenset branch above, and it is NOT covered by
            # it: `frozenset` is not a subclass of `set`, so neither is a subclass
            # of the other and each needs its own case.  CarrierStore.quarantined
            # is a plain `set` of item_ids, so an unsorted list(o) here walks a
            # hash-backed collection and serialises the SAME run to a DIFFERENT
            # byte string across processes.
            return sorted(o)
        if isinstance(o, tuple):
            # A tuple's order is MEANINGFUL (derived_from is a propagation trail),
            # so it is preserved, never sorted.
            return list(o)
        raise TypeError(type(o))
    return json.dumps(obj, default=enc, ensure_ascii=False, indent=2)


#: Bumped whenever a field a replay DEPENDS ON changes shape.  load_traces
#: refuses an unknown format rather than silently reading a trace that is missing
#: the field it is about to score with.
TRACE_FORMAT = 1


def _thaw_topic(v):
    """JSON gives back a LIST where a Topic (frozenset subclass) went in.

    dumps() writes a frozenset as a SORTED list, so the reverse is frozenset(v).
    It must be a frozenset and not a list: replay uses the topic as a dict key
    (topic_counts) and CarrierStore.retrieve runs Jaccard set operations over it
    (`a & b`, `a | b`), neither of which a list supports.  The plain-string topics
    of the mock dataset pass through and are normalised at the comparison site by
    retrieval.as_topic.

    Note what is NOT recovered: a swebench_dataset.Topic comes back a plain
    frozenset, so its str() is the hash-order form rather than the canonical one.
    That is why item_from_record passes item_id EXPLICITLY instead of letting
    __post_init__ rehash it -- see that function.
    """
    return frozenset(v) if isinstance(v, list) else v


def item_record(it: Item) -> dict:
    """The FULL record of one write -- SPEC-P1b Part 1, the "thao tac" row
    ("noi dung . provenance . timestamp").

    Recording item_id ALONE is recording a one-way function of the write: the id
    is blake2b of the content (Item.__post_init__), so it cannot be inverted, and
    the thing that row exists for -- "dung lai duoc carrier", rebuild the carrier
    -- is false.  `created_at` is the timestamp the row asks for: the task index
    at which the write happened.
    """
    return dict(item_id=it.item_id, carrier=it.carrier, topic=it.topic,
                content=it.content, created_at=it.created_at,
                provenance=it.provenance, poisoned=it.poisoned,
                derived_from=list(it.derived_from))


def item_from_record(rec: dict) -> Item:
    """Rebuild the Item a trace recorded.

    item_id is passed EXPLICITLY instead of letting __post_init__ recompute it.
    Recomputing would rehash seed_of(carrier, topic, content, ...), and str(topic)
    does NOT survive the JSON round trip: a swebench_dataset.Topic comes back as a
    plain frozenset, whose str() is the hash-order form rather than Topic's
    canonical "|".join(sorted(...)).  Every id would move, and since
    detector.score seeds on (seed, item_id), so would every score -- a replay that
    silently scores a different world.
    """
    return Item(carrier=rec["carrier"], topic=_thaw_topic(rec["topic"]),
                content=rec["content"], created_at=rec["created_at"],
                provenance=rec["provenance"], poisoned=rec["poisoned"],
                derived_from=tuple(rec.get("derived_from", ())),
                item_id=rec["item_id"])


def dump_traces(path, traces) -> None:
    """Write a run's traces to disk, SPLIT ON THE SEAL LINE.

    Without this "offline replay" is a figure of speech: RunResult.traces was
    built and dropped at the end of every run_once, so re-scoring could only
    happen inside the very process that had just run the agent -- which saves
    nothing at all.  The saving is: pay for the agent ONCE, write the traces out,
    then score the whole grid from the file in processes that never load an agent.

    TWO FILES, NOT ONE, AND THE SPLIT IS HERE BECAUSE THIS IS THE ONE DOOR.  A
    TaskTrace carries the evaluator's answer key as well as the run's mechanics:
    `poisoned` on every item record (core.Item's own field comment calls it
    "GROUND TRUTH -- audit policies must NOT read this"), the planted payload's
    full record under `injected`, and a `correct` verdict beside every quarantine.
    `results/M3-trace.json` was committed with all three, which published for the
    benchmark's headline artefact exactly what .gitignore refuses to publish for
    `carriers-sealed/`.  The acceptance line the artefact has to meet -- "the
    trace carries all nine field groups of SPEC-P1b Part 1" -- is a claim about
    its SHAPE, and shape survives the split.

        path                   the PUBLIC trace.  Nine field groups, every write
                               record, every query, every score, every checkpoint.
                               Committed.
        sealed_trace.sealed_path(path)   the answer key.  gitignored.

    Splitting anywhere else would be a second door: every writer in this build
    goes through this function, so putting it here is what makes "the labels are
    not published" a property of the codebase rather than of one call site that
    remembered.  `sealed_trace.load` is the reader that puts the halves back
    together, and it REFUSES when the sealed half is absent instead of returning
    traces on which nothing is poisoned.
    """
    import sealed_trace
    doc = json.loads(dumps({"format": TRACE_FORMAT, "traces": list(traces)}))
    sealed_trace.write(path, doc, dumps)


def load_traces(path) -> list:
    """Read traces back.  Inverse of dump_traces, ACROSS PROCESSES."""
    import pathlib
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    got = doc.get("format")
    if got != TRACE_FORMAT:
        raise ValueError(f"trace format {got!r}, this build reads {TRACE_FORMAT!r}")
    return [_trace_from_dict(d) for d in doc["traces"]]


def _trace_from_dict(d: dict) -> TaskTrace:
    d = dict(d)
    d["topic"] = _thaw_topic(d["topic"])
    d["queries"] = [dict(q, arg=_thaw_topic(q["arg"])) for q in d.get("queries", [])]
    return TaskTrace(**d)


def seed_of(*parts) -> int:
    """Seed that is stable across runs.

    Do NOT use Python's hash(): it is randomised by PYTHONHASHSEED, so results
    stop being reproducible -- and reproducibility is requirement number one for
    this benchmark.  Python 3.14 also no longer accepts tuples as seeds.
    """
    import hashlib
    s = "|".join(map(str, parts)).encode()
    return int.from_bytes(hashlib.blake2b(s, digest_size=8).digest(), "big")
