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
                            has_hidden_tests=True, is_mock=True)

    def workflows(self, n: int, H: int, seed: int) -> Iterator[Workflow]:
        for i in range(n):
            yield build.make_workflow(f"wf-{i:03d}", "django", H,
                                      random.Random(seed_of(seed, i)))


REGISTRY: dict = {d.name: d for d in (MockDataset(),)}

#: Datasets not yet built, each WITH ITS REASON -- never dropped silently
#: (rule N3 lifted to the pipeline level).
PENDING: dict = {}


def _register_swebench() -> None:
    """Register only once the data is downloaded; otherwise PENDING WITH A REASON."""
    import pathlib
    if (pathlib.Path(__file__).resolve().parent / "data" / "swebench_verified.jsonl").exists():
        import swebench_dataset
        REGISTRY["swebench"] = swebench_dataset.SWEBenchDataset()
    else:
        PENDING["swebench"] = (
            None, "data/swebench_verified.jsonl not downloaded -- run swebench_fetch.py")


_register_swebench()
