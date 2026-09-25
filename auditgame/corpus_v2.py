"""corpus_v2.py -- the draft's workload from SWE-bench Verified + Multilingual (D8).

Per repo (never mixing repos), instances sorted by created_at, cut into
consecutive windows of H ~ U{6..14}.  Two passes (offsets 0 and 3) put every
instance in at most two workflows -- exactly swebench_dataset.MAX_INSTANCE_REUSE,
which is not raised.  Step 4 of SPEC-P1a (a same-topic pair) is NOT applied:
the draft does not ask for it, and plan_poison_all already enforces dormancy;
infeasible cells leave the denominator (N3).  Topics are path tokens, so
non-Python patches work unchanged.
"""
from __future__ import annotations

import random

import draft_setup as D
from core import Task, Workflow, seed_of
from swebench_dataset import MAX_INSTANCE_REUSE, SWEBenchDataset

PASS_OFFSETS = (0, 3)
_CACHE: dict = {}
_POOL_OF: dict = {}              # repo -> pool it came from


def pool_of(wf) -> str:
    return _POOL_OF[wf.repo]


def make_corpus_v2(n: int = D.N_WORKFLOWS, seed: int = 2027, pools=D.POOLS) -> list:
    key = (n, seed, tuple(pools))
    if key in _CACHE:
        return _CACHE[key]
    assert len(PASS_OFFSETS) <= MAX_INSTANCE_REUSE
    by_repo, topic_of = {}, {}
    for pool in pools:
        ds = SWEBenchDataset(pool, sweep_deltas=())
        for repo, rows in ds._by_repo().items():
            if repo in by_repo:
                raise ValueError(f"repo {repo!r} appears in two pools")
            by_repo[repo], _POOL_OF[repo] = rows, pool
            for r in rows:
                topic_of[r["instance_id"]] = ds._topic(r)
    wfs = []
    for off in PASS_OFFSETS:
        for repo, rows in sorted(by_repo.items()):
            rng = random.Random(seed_of(seed, repo, off))     # per repo: pools do not interact
            i = off
            while True:
                H = rng.randint(*D.H_RANGE)
                if i + H > len(rows):
                    break
                seg, i = rows[i:i + H], i + H
                wfs.append(Workflow(
                    wf_id=f"v2-{len(wfs):03d}", repo=repo,
                    tasks=[Task(task_id=r["instance_id"], repo=repo,
                                base_commit=r["base_commit"], topic=topic_of[r["instance_id"]],
                                problem=r.get("problem_statement", "")) for r in seg]))
    if len(wfs) > n:
        keep = {w.wf_id for w in sorted(wfs, key=lambda w: seed_of("keep", w.wf_id))[:n]}
        wfs = [w for w in wfs if w.wf_id in keep]
    _CACHE[key] = wfs
    return wfs


def dev_repos(wfs: list) -> set:
    """D8: the LARGEST families (by workflow count, ties by name) until dev holds
    >= DEV_SHARE.  Decided from counts only: django holds 43% of workflows, and left
    in eval it would make the cluster bootstrap a one-repo interval (Kish ~2.5)."""
    size = {}
    for w in wfs:
        size[w.repo] = size.get(w.repo, 0) + 1
    fams = sorted(size, key=lambda r: (-size[r], r))
    dev, count = set(), 0
    for r in fams:
        if count >= D.DEV_SHARE * len(wfs):
            break
        dev.add(r)
        count += sum(1 for w in wfs if w.repo == r)
    return dev


def split(wfs: list) -> tuple:
    dev = dev_repos(wfs)
    return [w for w in wfs if w.repo in dev], [w for w in wfs if w.repo not in dev]


def kish(wfs: list) -> float:
    """Effective number of repo clusters, (sum n)^2 / sum n^2."""
    size = {}
    for w in wfs:
        size[w.repo] = size.get(w.repo, 0) + 1
    n = list(size.values())
    return sum(n) ** 2 / sum(x * x for x in n) if n else 0.0
