"""
r1_subset.py -- WHICH instances the hand-written hidden tests cover, and WHY those.

docs/thesis/eval/PLAN.md III.6 offers two retreats from the coverage gate Task 10 failed:
R1 (hand-write real hidden tests for a subset) and R2 (keep the marker proxy and
declare it a limitation).  This module is the R1 half of the hybrid: it fixes,
BY A SEEDED RULE RATHER THAN BY EYE, the list of instances a hand-written hidden
test is attempted for.

WHY THE RULE IS IN CODE AND NOT IN A COMMENT.  The one way to rig an agreement
rate is to choose the instances after seeing which of them give a nicer answer.
A rule that re-derives the same list from the corpus, from a seed, with no human
in the loop, removes that freedom -- and `test_r1_agreement.py` re-runs it
against the real pool and fails if the list moves.

THE CANDIDATE LIST IS FIXED A PRIORI AND THE SUBSET IS WHATEVER SURVIVES.  Every
candidate is attempted; the ones whose hidden test cannot be made to clear V1 or
V3 are DROPPED, recorded in DROPPED below with the reason, and stay in the
denominator of the story even though they leave the subset.  Taking candidates
"until enough survive" would reintroduce exactly the freedom the seed removes.
"""
from __future__ import annotations
import random

#: Instances H1 anchors on, measured over SWE-bench Verified in
#: docs/reports/do_thoi_gian_neo.md (5 of 500).  Sorted, so the seat order is not the
#: corpus's file order.  These are seeds, not passes: four of the five FAIL H1's
#: own V1 -- H1's generic property does not hold on their gold patches -- so they
#: need a per-instance test like every other candidate.
H1_ANCHORED = (
    "astropy__astropy-14182",
    "django__django-11119",
    "django__django-13809",
    "pytest-dev__pytest-7205",
    "sphinx-doc__sphinx-11510",
)

#: How many instances the seeded draw adds on top of H1_ANCHORED.
N_DRAWN = 10

#: Seed label.  Goes through core.seed_of -- never hash(), which is randomised
#: per process and would make the subset unreproducible.
SEED_LABEL = ("task-10b", "r1-subset")


def _seed() -> int:
    import core
    return core.seed_of(*SEED_LABEL)


def draw(rows, n: int = N_DRAWN, exclude=H1_ANCHORED) -> list[str]:
    """The seeded rule: ROUND-ROBIN ACROSS REPOS, shuffled within each repo.

    Round-robin rather than a uniform draw over the pool, because a uniform draw
    over SWE-bench Verified is a draw over django: django holds 231 of the 500
    instances, so 10 uniform draws would be ~5 django instances and would leave
    most repos unrepresented.  The dispatch's "prefer spreading across repos"
    is therefore implemented in the sampler, not applied afterwards by hand.

    Repos are visited in descending pool size with the repo name breaking ties,
    so the visiting order is a property of the corpus.  Within a repo the
    instances are sorted by id and then shuffled by ONE Random seeded from
    SEED_LABEL, so which member of a repo is taken is the seed's business and
    not the corpus's file order.
    """
    rng = random.Random(_seed())
    by_repo: dict = {}
    for r in rows:
        by_repo.setdefault(r["repo"], []).append(r["instance_id"])
    order = sorted(by_repo, key=lambda repo: (-len(by_repo[repo]), repo))
    queues = {}
    for repo in order:
        ids = sorted(by_repo[repo])
        rng.shuffle(ids)
        queues[repo] = [i for i in ids if i not in set(exclude)]

    picked: list[str] = []
    while len(picked) < n and any(queues[repo] for repo in order):
        for repo in order:
            if len(picked) == n:
                break
            if queues[repo]:
                picked.append(queues[repo].pop(0))
    return picked
