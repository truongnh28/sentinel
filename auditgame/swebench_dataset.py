"""
swebench_dataset.py -- A DatasetPipeline over REAL SWE-bench metadata.

Spec: SPEC-P1a-Harness.md Part 4.  Sits ALONGSIDE MockDataset, does not replace it
-- the mock is still needed so measurement-layer tests stay fast and file-free.

Sorting by `created_at` is the most important step here: it makes a workflow follow
the repo's REAL DEVELOPMENT HISTORY, so "two related tasks" carries causal meaning.
Shuffle instead and a shared topic is pure coincidence.
"""
from __future__ import annotations
import json, pathlib, random
from typing import Iterator

import topics
from core import Task, Workflow, seed_of

# `DatasetScope` is only used as a return-type annotation below (deferred by
# `from __future__ import annotations`, so it is never evaluated at import
# time) and inside scope().  It is NOT imported at module level: datasets.py's
# _register_swebench() imports THIS module, so a top-level `from datasets
# import DatasetScope` here would race it -- whichever of the two modules
# starts importing first leaves the other only partially initialised when the
# cycle closes.  Concretely: `python3 -c "import swebench_dataset"` (Bước 3.6)
# begins executing this file, hits a hypothetical module-level `from datasets
# import ...`, which runs datasets.py to completion, which itself does
# `import swebench_dataset` -- Python hands back the SAME partial module
# object (already registered in sys.modules) instead of re-entering it, and
# at that point SWEBenchDataset is not yet defined.  Importing DatasetScope
# lazily, after both modules are fully loaded, avoids the cycle entirely.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from datasets import DatasetScope

DATA = pathlib.Path(__file__).resolve().parent / "data"


class Topic(frozenset):
    """`topics.topic_of_instance` returns a plain `frozenset` of path tokens, and
    tests/gate1_integrity/test_conformance_ports.py's D2 requires exactly that
    type once a dataset declares `topic_kind="graded"` -- so Task.topic here MUST
    stay a real frozenset, not a string.

    But frozenset's own str()/repr() walks its internal hash table, whose layout
    depends on Python's per-process string-hash randomisation (PYTHONHASHSEED).
    Every consumer downstream of Task.topic embeds it straight into an f-string
    (agent.py's memory/skill/branch/queue notes, build.py's payload content) or
    hands it to core.seed_of, which stringifies its arguments -- so a bare
    frozenset here would make the SAME command print a DIFFERENT number on two
    separate runs.  That is exactly the failure class the project's hash() ban
    exists to prevent (see core.seed_of's docstring), just arriving through
    frozenset ordering instead of hash() itself.

    Overriding __str__/__repr__ to the canonical "|".join(sorted(...)) form fixes
    every one of those call sites WITHOUT touching any of them: isinstance(topic,
    frozenset) is still True, and set equality / Jaccard similarity / use as a
    dict key (runner.py's topic_counts) are all unaffected, because none of them
    depend on iteration order -- only string conversion does.
    """
    def __str__(self) -> str:
        return "|".join(sorted(self))

    __repr__ = __str__


class SWEBenchDataset:
    name = "swebench"

    def __init__(self, pool: str = "verified"):
        self.pool = pool
        self._rows = [json.loads(l) for l in
                      (DATA / f"swebench_{pool}.jsonl").open(encoding="utf-8")]

    def _by_repo(self) -> dict:
        g: dict = {}
        for r in self._rows:
            g.setdefault(r["repo"], []).append(r)
        for v in g.values():
            v.sort(key=lambda r: (r.get("created_at", ""), r["instance_id"]))
        return g

    def _segments(self, H: int) -> list:
        """Every run of H consecutive instances, NON-OVERLAPPING, within each repo."""
        out = []
        for repo, rows in sorted(self._by_repo().items()):
            for i in range(0, len(rows) - H + 1, H):
                out.append((repo, rows[i:i + H]))
        return out

    def stats(self, H: int = 8) -> dict:
        g = self._by_repo()
        return {"instances": len(self._rows),
                "repos": len(g),
                "repos_with_H": sum(1 for v in g.values() if len(v) >= H),
                "non_reused_workflows": len(self._segments(H))}

    def scope(self) -> "DatasetScope":
        from datasets import DatasetScope
        return DatasetScope(repos=frozenset(self._by_repo()),
                            topic_kind="graded", has_hidden_tests=False,
                            is_mock=False)

    def workflows(self, n: int, H: int, seed: int) -> Iterator[Workflow]:
        segments = self._segments(H)
        rng = random.Random(seed_of(seed, "wf", self.pool))
        rng.shuffle(segments)
        for i in range(n):
            repo, rows = segments[i % len(segments)]   # `%` = reuse when segments run out
            yield Workflow(
                wf_id=f"swe-{i:03d}", repo=repo,
                tasks=[Task(task_id=r["instance_id"], repo=r["repo"],
                            base_commit=r["base_commit"],
                            topic=Topic(topics.topic_of_instance(r)),
                            problem=r.get("problem_statement", ""))
                       for r in rows])
