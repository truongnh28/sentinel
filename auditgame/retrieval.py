"""
retrieval.py -- GRADED RETRIEVAL (R).  Spec: pipelines/SPEC-R-Truy-xuat.md

Problem: `CarrierStore.retrieve` matches topic strings EXACTLY, so the retrieval
function takes only two values {0, 1}.  AgentPoison attacks by optimising a
trigger in embedding space -- against a two-valued function there is NOTHING TO
OPTIMISE.  And `epsilon`, one of the four attacker knobs (k, iota, sigma,
epsilon), has no surface to act on: measured, the payload at eps=0.05 and
eps=0.95 is byte-for-byte IDENTICAL.

Fix: Jaccard similarity over MODULE TOKEN SETS.  Deterministic (no learning, no
sampling), no third-party dependency, and exact matching is the SPECIAL CASE
theta=1.

The trade-off the older docs conflated: exact matching buys bit-exact REPLAY, it
does NOT buy oracle determinism -- the oracle scores patches with pytest plus an
AST diff and never touches retrieval.  Determinism does not require discreteness,
so we get both.

NOTE: not yet wired into core.CarrierStore.  Blocked on advisor question 3.
"""
from __future__ import annotations
import math

Topic = frozenset


def topic_of(files) -> Topic:
    """Files touched by a gold patch -> set of module tokens.

        django/db/models/query.py  ->  {django, db, models, query}

    No model, no embedding -- just string splitting.  Being a SET, it does not
    depend on file order, which is what lets traces replay.
    """
    tokens = set()
    for path in files:
        for part in str(path).split("/"):
            part = part.rsplit(".", 1)[0] if "." in part else part
            if part:
                tokens.add(part)
    return frozenset(tokens)


def sim(a: Topic, b: Topic) -> float:
    """Jaccard.  |A & B| / |A | B|.  Two empty sets are 0 by convention."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def retrieved(item_topic: Topic, task_topic: Topic, theta: float) -> bool:
    """theta=1 with equal token sets <=> exact match (today's behaviour)."""
    return sim(item_topic, task_topic) >= theta


def payload_topic(target: Topic, eps: float) -> Topic:
    """Token set the attacker picks for the payload -- a SUBSET of task sigma's.

    |A| = ceil(eps * |B|), taken in SORTED order: deterministic, no sampling.

    It must be a subset.  Adding tokens OUTSIDE the target inflates the Jaccard
    denominator and DROPS sim, so a larger eps would weaken the attack -- exactly
    backwards from "distinguishability budget".  Since A is a subset of B,
    sim(A, B) = |A| / |B| ~= eps.

    Two opposing directions, and that is what makes it a budget:
        small eps -> few tokens -> low sim, may NOT clear theta -> attack fails
        large eps -> surely retrieved, but a larger `size` feature, so EASIER to
                     spot on F_match
    """
    if not target:
        return frozenset()
    k = max(1, math.ceil(eps * len(target)))
    return frozenset(sorted(target)[:k])
