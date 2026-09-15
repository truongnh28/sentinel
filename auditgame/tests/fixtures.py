"""
fixtures.py -- A DETERMINISTIC tiny world for the test suite.

Why it exists (SPEC-Tang-Do-va-Test.md SS7.1): a test over 40 random workflows at
B=17.95 CANNOT be checked by hand.  It goes "green" without convincing anyone,
including ourselves.  A test that copies the previous run's output is a test that
LOCKS IN THE BUG, not one that defends a claim.

The detector and the agent are both random, so nothing can be worked out on paper
=> REPLACE RANDOMNESS WITH A SCRIPT.  The random components are tested separately,
by fixed-seed statistical tests (I7).
"""
from __future__ import annotations
import contextlib
from dataclasses import dataclass, field

from core import Item, CarrierStore, Task, Workflow, PoisonSpec
from agent import Outcome
import policies as P

# ---------------------------------------------------------------- detector ----

_LEGACY = object()

@dataclass
class ScriptedDetector:
    """A deterministic detector.  The score is a FUNCTION of the item, not a draw.

    Keyed by that function and NOT by `item_id`: `item_id` used to come from a
    process-global counter (`itertools.count`), so it depended on how many Items
    had been created earlier in the same process and was unstable between tests.
    That was also a threat to I1, since traces are hashed by item_id.  Item now
    hashes item_id from its content, but keying on the function here stays correct
    either way.

    The TARGET interface is N1 (SS2.2): `score(item, now, seed)` + `fires(score)`.
    `raw_score` and the second parameter of `fires` are temporary SHIMS so this
    still runs against the current `runner.py` -- and `legacy_calls` COUNTS how
    many times the runner still passes ground truth in.  The I2 test watches that
    counter: it is RED now and GREEN after B1, with no edit to the test.
    """
    poisoned_score: float = 2.0
    clean_score: float = 0.0
    tau: float = 1.0
    overrides: dict = field(default_factory=dict)   # topic -> score, to steer edge cases
    legacy_calls: int = 0
    # After B1 the runner calls scoring.carrier_score(raw, det.d_prime).  Script
    # that too: the scores are already deterministic, so d_prime only affects the
    # rollup, and we take the `weak` setting's d' exactly so the constants in the
    # tests line up with the reference table.
    d_prime: float = 1.5161

    # ---- the TARGET interface (N1) ----
    def score(self, item, now: int = 0, seed: int = 0) -> float:
        if item.topic in self.overrides:
            return self.overrides[item.topic]
        return self.poisoned_score if item.poisoned else self.clean_score

    def fires(self, score: float, _legacy=_LEGACY) -> bool:
        if _legacy is not _LEGACY:
            self.legacy_calls += 1      # WARNING: ground truth is still being passed in
        return score > self.tau

    def score_patch(self, has_marker: bool, task_id: str = "", seed: int = 0) -> float:
        """D2: score the PATCH, not writes[0].  Deterministic in has_marker."""
        return self.poisoned_score if has_marker else self.clean_score

    # ---- SHIM: raw_score disappeared from the real Detector at B1.  Kept here so
    # that any test still calling it breaks VISIBLY instead of silently using the
    # wrong thing. ----
    def raw_score(self, item, now: int = 0, seed: int = 0) -> float:
        raise AttributeError(
            "raw_score was removed at B1 (N1). Use score(item, now, seed).")

    @property
    def psi(self) -> float:
        return 1.0 if self.poisoned_score > self.tau else 0.0

    @property
    def phi(self) -> float:
        return 1.0 if self.clean_score > self.tau else 0.0


class BlindDetector(ScriptedDetector):
    """Never fires.  Used to isolate the budget mechanism from the detection mechanism."""
    def __init__(self):
        super().__init__(poisoned_score=-9.0, clean_score=-9.0, tau=1.0)


# ------------------------------------------------------------------- agent ----

@dataclass
class ScriptedAgent:
    """A deterministic agent.

    Retrieval is REAL (`store.retrieve`) -- mandatory, because if retrieval were
    scripted too, the causal channel `quarantine -> cannot be retrieved -> no
    marker` would be cut, and every gate-2 control would become meaningless.

    Only three things are scripted: whether the task is solved, whether a note is
    written, whether a skill is induced.
    """
    solved_at: tuple = (True, True, True, True, True, True, True, True)
    writes_note: bool = True
    induces_skill: bool = False
    adopts: bool = True

    def run_task(self, t: int, task: Task, store: CarrierStore,
                 seed: int, marker: str) -> Outcome:
        retrieved = store.retrieve(task.topic)
        poisoned_seen = [it for it in retrieved if it.poisoned]
        patch_has_marker = bool(poisoned_seen) and self.adopts

        writes = []
        if self.writes_note:
            writes.append(store.write(Item(
                carrier="memory", topic=task.topic,
                content=f"note {task.task_id}", created_at=t,
                provenance="agent/notes", poisoned=False)))
        if self.induces_skill and retrieved:
            writes.append(store.write(Item(
                carrier="skill", topic=task.topic,
                content=f"skill {task.task_id}", created_at=t,
                provenance="agent/skills", poisoned=bool(poisoned_seen),
                derived_from=tuple(i.item_id for i in poisoned_seen))))

        solved = self.solved_at[t] if t < len(self.solved_at) else True
        return Outcome(retrieved=retrieved, writes=writes,
                       patch_has_marker=patch_has_marker, solved=solved)


# ----------------------------------------------------------------- profile ----

def _wf(wf_id: str, topics: list, repo: str = "tiny") -> Workflow:
    """A deterministic workflow.  Does NOT use `build.make_workflow` -- that used
    `hash()` for `base_commit`, and `hash()` is randomised by PYTHONHASHSEED (bug I1)."""
    return Workflow(wf_id=wf_id, repo=repo, tasks=[
        Task(task_id=f"{wf_id}-t{t}", repo=repo,
             base_commit=f"{t:07d}", topic=tp, problem=f"fix {tp} #{t}")
        for t, tp in enumerate(topics)])


@dataclass
class Profile:
    name: str
    workflows: list
    specs: list                 # PoisonSpec, parallel to workflows
    budget: float
    kappa: dict
    kappa_commit: float
    note: str = ""

    @contextlib.contextmanager
    def kappa_applied(self):
        """Apply the profile's cost table, restore it afterwards.  `policies.KAPPA`
        is a module-level dict, so it has to be patched -- it cannot be passed in."""
        old_k, old_c = dict(P.KAPPA), P.KAPPA_COMMIT
        P.KAPPA.clear(); P.KAPPA.update(self.kappa)
        P.KAPPA_COMMIT = self.kappa_commit
        try:
            yield self
        finally:
            P.KAPPA.clear(); P.KAPPA.update(old_k)
            P.KAPPA_COMMIT = old_c


def profile_A() -> Profile:
    """PROFILE A -- budget and determinism (gate 1).  SS7.2

    2 workflows - H=4 - 1 carrier (memory) - Delta=1
    kappa_memory = 0.4 - kappa_commit = 4.1 - B = 1.0

      => exactly 2 memory audits  (2 x 0.4 = 0.8 <= 1.0; a third would overrun)
      => 0 commit audits          (4.1 > 1.0)

    Consequences you can verify IN YOUR HEAD:
      . B1 audit-at-commit cannot afford a single audit => harm(B1) == harm(no
        defense), i.e. B1 BECOMES NC2 in this profile.
      . With 1 carrier, Sentinel's choice set has one element => Sentinel, B3 and
        B4 COINCIDE.

    So profile A isolates the budget/detector mechanism from the allocation
    mechanism -- exactly what gate 1 needs.
    """
    topics = ["a", "b", "c", "d"]          # pairwise distinct => Delta=1 is always constructible
    wfs = [_wf("A0", topics), _wf("A1", topics)]
    # sigma = 2, iota = 1: topic(t1)="b" != topic(t2)="c" => no early firing
    specs = [PoisonSpec(carrier="memory", iota=1, sigma=2, epsilon=0.6) for _ in wfs]
    return Profile("A", wfs, specs, budget=1.0,
                   kappa={"memory": 0.4, "skill": 0.9, "queue": 1.6, "branch": 4.1},
                   kappa_commit=4.1,
                   note="2 memory audits, 0 commit audits; B1==NC2; Sentinel==B3==B4")


def profile_B() -> Profile:
    """PROFILE B -- allocation (gate 2, for C4/C5).  SS7.2

    2 workflows - H=4 - 2 carriers (memory k=0.4 - branch k=4.1) - Delta=1 - B=4.5

      => either 11 memory audits  (11 x 0.4 = 4.4)
      => or 1 branch + 1 memory   (4.1 + 0.4 = 4.5)

    Those two branches are the ENTIRE decision tree, and it fits on one page.
    C5 (flat kappa, c = 0.4) turns it into any 11 audits => the price differential
    disappears and what is left is pure information.
    """
    topics = ["a", "b", "c", "d"]
    wfs = [_wf("B0", topics), _wf("B1", topics)]
    specs = [PoisonSpec(carrier="memory", iota=1, sigma=2, epsilon=0.6),
             PoisonSpec(carrier="branch", iota=1, sigma=2, epsilon=0.6)]
    return Profile("B", wfs, specs, budget=4.5,
                   kappa={"memory": 0.4, "skill": 0.9, "queue": 1.6, "branch": 4.1},
                   kappa_commit=4.1,
                   note="11 memory OR 1 branch + 1 memory")


PROFILES = {"A": profile_A, "B": profile_B}
