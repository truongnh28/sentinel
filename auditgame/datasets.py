"""
datasets.py -- The DatasetPipeline PORT.
Spec: pipelines/SPEC-Framework-Benchmark.md Part 2.3.

Swap this port to answer: *do the results depend on the repo or the language?*

The scope's most important field is `topic_kind`:

    exact   topic is a STRING, retrieval matches exactly   -> sim in {0,1}
    graded  topic is a TOKEN SET, Jaccard retrieval        -> sim continuous

It decides which AttackPipeline may be used.  An attack declaring
`requires_graded_retrieval=True` running on an `exact` dataset is a MEANINGLESS
combination -- epsilon has no surface to act on -- so the framework must REFUSE it
with a reason rather than print a number.
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Iterator, Protocol

import build
from core import Workflow, seed_of


@dataclass(frozen=True)
class DatasetScope:
    repos: frozenset
    topic_kind: str            # "exact" | "graded"
    has_hidden_tests: bool
    is_mock: bool
    #: WHICH instance pool the workflows were cut from -- SPEC-P1a-Harness.md
    #: Part 5 marks this "MOI, bat buoc" and requires it in the results header.
    #: Without it a swebench result cannot be attributed to the Verified pool or
    #: the full one, and the two differ by 4.6x in instances and by a factor of
    #: five in how many workflows survive grouping -- so "swebench" alone does
    #: not identify what was measured.
    instance_pool: str = "n/a"


class DatasetPipeline(Protocol):
    name: str
    def scope(self) -> DatasetScope: ...
    def workflows(self, n: int, H: int, seed: int) -> Iterator[Workflow]: ...


class MockDataset:
    """Synthetically generated workflows -- used to test the measurement layer
    without spending LLM tokens.

    `is_mock=True` is not a decorative label: the results table MUST print it, or
    the reader cannot tell numbers measured on real data from numbers measured on
    the mock.
    """
    name = "mock"

    def scope(self) -> DatasetScope:
        return DatasetScope(repos=frozenset({"django"}), topic_kind="exact",
                            has_hidden_tests=True, is_mock=True,
                            instance_pool="synthetic")

    def workflows(self, n: int, H: int, seed: int) -> Iterator[Workflow]:
        for i in range(n):
            yield build.make_workflow(f"wf-{i:03d}", "django", H,
                                      random.Random(seed_of(seed, i)))


REGISTRY: dict = {d.name: d for d in (MockDataset(),)}

#: Datasets not yet built, each WITH ITS REASON -- never dropped silently
#: (rule N3 lifted to the pipeline level).
PENDING: dict = {}


#: H at which swebench's feasibility is probed on import.  It is experiment.py's
#: default; `workflows()` re-checks at whatever H it is actually asked for, so a
#: dataset registered here can still refuse a particular request.
_PROBE_H = 8


def _register_swebench() -> None:
    """Register only once the data is downloaded AND the corpus can host the
    sweep; otherwise PENDING WITH A REASON.

    The second condition is SPEC-P1a Part 4 step 4 -- "N3 o muc dataset".  A
    corpus that cannot host an attack at the deltas being swept does not produce
    a harm of 0; it produces NO NUMBER, and the reason is recorded here rather
    than discovered as a surprise in the middle of a table.
    """
    import pathlib
    if not (pathlib.Path(__file__).resolve().parent / "data"
            / "swebench_verified.jsonl").exists():
        PENDING["swebench"] = (
            None, "data/swebench_verified.jsonl not downloaded -- run swebench_fetch.py")
        return
    import swebench_dataset
    ds = swebench_dataset.SWEBenchDataset()
    rep = ds.grouping_report(H=_PROBE_H)
    if rep["feasible"] == 0:
        PENDING["swebench"] = (ds, (
            f"no workflow survives SPEC-P1a Part 4 step 4. At H={rep['H']} on "
            f"pool {rep['pool']!r} the corpus groups into {rep['grouped']} "
            f"workflows and ALL {rep['dropped']} of them are dropped: none holds "
            f"a pair of tasks (i, i+Delta) whose topics match at theta="
            f"{rep['theta']} for every Delta in {rep['sweep_deltas']}. Workflows "
            f"that can host each Delta on its own: {rep['per_delta']}. The "
            f"payload was reaching sigma only because build.inject stamps it with "
            f"sigma's own topic, so the harm column was measuring the injection, "
            f"not the repo's history. theta is 1.0 because "
            f"core.CarrierStore.retrieve compares topics with `==` -- this "
            f"unblocks when retrieval becomes graded (retrieval.py, advisor "
            f"question 3), not by weakening theta."))
    else:
        REGISTRY["swebench"] = ds


_register_swebench()
