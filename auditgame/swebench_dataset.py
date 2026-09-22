"""
swebench_dataset.py -- A DatasetPipeline over REAL SWE-bench metadata.

Spec: docs/thesis/pipelines/SPEC-P1a-Harness.md Part 4.  Sits ALONGSIDE MockDataset, does not replace it
-- the mock is still needed so measurement-layer tests stay fast and file-free.

Sorting by `created_at` is the most important step here: it makes a workflow follow
the repo's REAL DEVELOPMENT HISTORY, so "two related tasks" carries causal meaning.
Shuffle instead and a shared topic is pure coincidence.
"""
from __future__ import annotations
import json, pathlib, random
from typing import Iterator

import retrieval
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

# Question 4's signed-off answer ("42% minimum reuse to reach N=100") is
# conditional on each instance appearing in at most this many workflows.
# Two workflows that share an instance have CORRELATED clean-run results,
# while `bootstrap_paired` resamples BY WORKFLOW and assumes independence
# across resamples.  Reuse beyond this cap therefore produces a falsely
# NARROW confidence interval -- the very error `bootstrap_paired` was
# introduced to fix, arriving one layer earlier, at corpus construction
# instead of at the statistics.  Do not raise this value to make a larger N
# fit; the fix for a larger N is a larger pool (more repos / more history),
# not a larger cap.
MAX_INSTANCE_REUSE = 2

#: The Delta grid experiment.py sweeps.  SPEC-P1a Part 4 step 4 drops a workflow
#: that cannot host an attack at "Delta can quet" -- the deltas that are going to
#: be swept -- so the filter needs to know them, and they are not a free
#: parameter: change them here only when experiment.py's `deltas` changes.
SWEEP_DELTAS = (0, 1, 2, 4)

#: Retrieval threshold used by step 4.  It is not a number of its own: it is
#: `retrieval.THETA`, the SAME threshold core.CarrierStore.retrieve applies, so
#: step 4 cannot admit a workflow the runner's retrieval would then refuse to act
#: on (or refuse one it would).  Binding the two together is the point -- two
#: independent copies of theta is how a filter and a measurement quietly stop
#: describing the same world.
#:
#: It reads 0.5 rather than 1.0 because RETRIEVAL MOVED, which is the only reason
#: the previous note here allowed: "theta moves when retrieval moves."
#: core.CarrierStore.retrieve now goes through retrieval.retrieved() instead of
#: `==`, and theta was fixed from the measured |topic| distribution
#: (docs/reports/chot_theta.md), written down and committed BEFORE the surviving
#: workflow count was looked at.
#:
#: DO NOT MOVE THIS TO KEEP THE WORKFLOW COUNT UP.  The count is a consequence of
#: theta; theta is not a consequence of the count.  If it ever needs to change,
#: the derivation in docs/reports/chot_theta.md is what changes first, from data.
THETA = retrieval.THETA


class Topic(retrieval.Topic):
    """`topics.topic_of_instance` returns a token set of path tokens, and
    Task.topic here MUST stay a real frozenset, not a string: it is what
    retrieval.sim / retrieval.payload_topic are written against, and it is the
    form the graded retrieval in core.CarrierStore.retrieve is built on.  A
    token-set TYPE was never graded RETRIEVAL on its own, which is why scope()
    declared "exact" until the wiring landed; it declares "graded" now because
    the retrieval behind it changed, not because the type did.

    The canonical "|".join(sorted(...)) stringification that makes this safe --
    against a bare frozenset's PYTHONHASHSEED-dependent str(), which would give
    the same run a different item_id and therefore a different detector score --
    now lives on retrieval.Topic, and this class inherits it.  It moved there
    because retrieval CONSTRUCTS topics too: build.inject stamps the payload with
    retrieval.payload_topic_like(sigma_topic, eps), a subset no dataset ever
    handed out, so a canonical form defined only here would not have covered it.

    The distinct subclass is kept rather than aliased away so that the DATASET's
    topics stay identifiable as such at a glance in a traceback, and so
    retrieval.payload_topic_like's `type(target)(...)` hands back a topic of this
    same type instead of silently widening it.
    """


class SWEBenchDataset:
    name = "swebench"

    def __init__(self, pool: str = "verified", sweep_deltas=SWEEP_DELTAS,
                 theta: float = THETA):
        self.pool = pool
        #: Deltas step 4 requires the workflow to be able to host.  `()` disables
        #: step 4 -- only for tests that are about the SHAPE of a workflow (which
        #: repo its tasks come from, how its topic stringifies) rather than about
        #: whether an attack can be built on it.
        self.sweep_deltas = tuple(sweep_deltas)
        self.theta = theta
        self._rows = [json.loads(l) for l in
                      (DATA / f"swebench_{pool}.jsonl").open(encoding="utf-8")]
        self._topic_cache: dict = {}

    def _by_repo(self) -> dict:
        g: dict = {}
        for r in self._rows:
            g.setdefault(r["repo"], []).append(r)
        for v in g.values():
            v.sort(key=lambda r: (r.get("created_at", ""), r["instance_id"]))
        return g

    def _topic(self, row: dict):
        key = row["instance_id"]
        if key not in self._topic_cache:
            self._topic_cache[key] = Topic(topics.topic_of_instance(row))
        return self._topic_cache[key]

    def _raw_segments(self, H: int) -> list:
        """Steps 1-3 of SPEC-P1a Part 4: group by repo, sort by created_at, cut
        into runs of H consecutive instances, NON-OVERLAPPING."""
        out = []
        for repo, rows in sorted(self._by_repo().items()):
            for i in range(0, len(rows) - H + 1, H):
                out.append((repo, rows[i:i + H]))
        return out

    def hosts_delta(self, rows, delta: int) -> bool:
        """Can an attack at this Delta be built on these H tasks WITHOUT relying
        on the injection to manufacture the relation?

        True iff some pair (i, i+delta) has sim(topic_i, topic_{i+delta}) >= theta.
        Delta = 0 is plant-and-fire on the SAME task, so it needs no pair and is
        always hostable.
        """
        if delta <= 0:
            return True
        tp = [self._topic(r) for r in rows]
        return any(retrieval.sim(tp[i], tp[i + delta]) >= self.theta
                   for i in range(len(tp) - delta))

    def _segments(self, H: int) -> list:
        """SPEC-P1a Part 4, ALL FOUR steps.

        Step 4 -- "LOAI workflow khong co cap (i, i+Delta) cung topic vuot theta
        cho Delta can quet" -- was missing, and the spec calls it "N3 o muc
        dataset": a workflow on which the attack cannot be built must leave the
        DENOMINATOR, not enter it and contribute a harm of 0.

        It is not a formality on this corpus. build.plan_poison only requires that
        no task in [iota, sigma) carries sigma's topic; it never requires iota and
        sigma to be RELATED, and build.inject then stamps the payload with sigma's
        own topic. So the payload is retrieved at sigma whether or not any two
        real tasks in the workflow have anything to do with each other -- "two
        related tasks" becomes an artifact of the injection rather than a property
        of the repo's history, which is precisely the causal reading the
        created_at sort was introduced to earn.

        Both halves of that have now moved, and step 4 stayed. build.inject
        narrows the payload to payload_topic_like(sigma_topic, eps), so it is no
        longer stamped with sigma's whole topic; and retrieval is graded, so
        "related" is sim >= theta rather than set equality. Measured on the 58
        grouped workflows of SWE-bench Verified at H=8 (1624 intra-workflow task
        pairs): 281 of them clear theta=0.5, i.e. 17.30%, against 29 (1.79%)
        under `==`. For scale, the synthetic mock sits at 282/1624 = 17.36% --
        the real corpus's relatedness now measures like the mock's instead of an
        order of magnitude below it. 14 of the 58 workflows survive this filter,
        against 0 before. Step 4 is what keeps the other 44 out of the
        DENOMINATOR.
        """
        segs = self._raw_segments(H)
        if not self.sweep_deltas:
            return segs
        return [(repo, rows) for repo, rows in segs
                if all(self.hosts_delta(rows, d) for d in self.sweep_deltas)]

    def grouping_report(self, H: int = 8) -> dict:
        """What step 4 cost, in workflows -- the number the run header must carry.

        `per_delta` is the diagnostic: it says WHICH Delta the corpus cannot host,
        which is the difference between "the pool is too small" and "the sweep
        asks for a relation this corpus does not contain".
        """
        raw = self._raw_segments(H)
        return {
            "pool": self.pool, "H": H, "theta": self.theta,
            "sweep_deltas": self.sweep_deltas,
            "grouped": len(raw),
            "feasible": len(self._segments(H)),
            "dropped": len(raw) - len(self._segments(H)),
            "per_delta": {d: sum(1 for _r, rows in raw if self.hosts_delta(rows, d))
                          for d in self.sweep_deltas},
        }

    def stats(self, H: int = 8) -> dict:
        """`non_reused_workflows` deliberately counts the STEP-3 segments, before
        step 4: question 4 asks how much INSTANCE REUSE is needed to reach N=100,
        which is a property of the grouping, not of attack feasibility. The step-4
        cost is reported separately by grouping_report() so the two cannot be
        confused for one another -- and so that a reader of the question-4 number
        is told, in the same object, how many of those workflows can actually host
        the sweep.
        """
        g = self._by_repo()
        rep = self.grouping_report(H)
        return {"instances": len(self._rows),
                "repos": len(g),
                "repos_with_H": sum(1 for v in g.values() if len(v) >= H),
                "non_reused_workflows": len(self._raw_segments(H)),
                "feasible_workflows": rep["feasible"],
                "dropped_by_step4": rep["dropped"]}

    def scope(self) -> "DatasetScope":
        # topic_kind="graded".  This was downgraded to "exact" while the
        # declaration was false, and the note left here listed the two conditions
        # under which it could go back up. BOTH now hold, which is why it does:
        #
        #   1. core.CarrierStore.retrieve goes through
        #      retrieval.retrieved(item.topic, task.topic, theta) instead of `==`;
        #   2. theta was FIXED FROM THE MEASURED |topic| distribution
        #      (docs/reports/chot_theta.md, derived and committed before the surviving
        #      workflow count was looked at), not guessed.
        #
        # Neither of those is asserted here, and the declaration is not what makes
        # it true. test_D2_topic_kind_is_declared_truthfully plants items whose
        # similarity to the query is strictly between 0 and 1 and checks that the
        # retrieval the RUNNER uses returns the closer one and not the farther
        # one. That test is the thing standing behind this string; if the wiring
        # is ever reverted it goes red here rather than letting the old fake zero
        # back in (GradedAttack's payload is a strict SUBSET of sigma's topic, so
        # under `==` every epsilon < 1 reports harm == 0).
        from datasets import DatasetScope
        return DatasetScope(repos=frozenset(self._by_repo()),
                            topic_kind="graded", has_hidden_tests=False,
                            is_mock=False, instance_pool=self.pool)

    def workflows(self, n: int, H: int, seed: int) -> Iterator[Workflow]:
        segments = self._segments(H)
        if not segments and self.sweep_deltas:
            rep = self.grouping_report(H)
            raise ValueError(
                f"no workflow survives SPEC-P1a Part 4 step 4 on pool "
                f"{self.pool!r} at H={H}: all {rep['grouped']} grouped workflows "
                f"were dropped because none hosts a same-topic pair (i, i+Delta) "
                f"at theta={self.theta} for every Delta in {self.sweep_deltas}. "
                f"Per Delta, the workflows that CAN host it: {rep['per_delta']}. "
                f"This is N3 at dataset level: a workflow on which the attack "
                f"cannot be built leaves the denominator, it does not enter it "
                f"with harm 0. Do NOT lower theta to make this pass: theta is "
                f"retrieval.THETA, derived from the measured |topic| "
                f"distribution in docs/reports/chot_theta.md and shared with the "
                f"retrieval the runner performs, so lowering it here would "
                f"admit workflows that retrieval then cannot act on. The fix "
                f"for an empty corpus is a pool whose workflows contain "
                f"genuinely related tasks.")
        cap = MAX_INSTANCE_REUSE * len(segments)
        if n > cap:
            reuse_factor = n / len(segments) if segments else float("inf")
            raise ValueError(
                f"workflows(n={n}) would reuse each of the {len(segments)} "
                f"available segments {reuse_factor:.1f}x, above the cap of "
                f"{MAX_INSTANCE_REUSE}x (max n at this cap is {cap}). "
                "bootstrap_paired resamples by workflow and assumes "
                "independence across resamples; reusing an instance beyond "
                "the cap correlates their clean-run results and understates "
                "the confidence interval. Fix: use a larger pool or a "
                "smaller n -- do not raise MAX_INSTANCE_REUSE.")
        rng = random.Random(seed_of(seed, "wf", self.pool))
        rng.shuffle(segments)
        for i in range(n):
            repo, rows = segments[i % len(segments)]   # `%` = reuse, bounded by the cap above
            yield Workflow(
                wf_id=f"swe-{i:03d}", repo=repo,
                tasks=[Task(task_id=r["instance_id"], repo=r["repo"],
                            base_commit=r["base_commit"],
                            topic=self._topic(r),
                            problem=r.get("problem_statement", ""))
                       for r in rows])
