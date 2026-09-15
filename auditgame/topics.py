"""
topics.py -- gold patch -> module token set.  Spec: SPEC-P1a-Harness.md Part 2.

No model, no embedding, just string splitting -- so it is deterministic and replays.
"""
from __future__ import annotations
import re, statistics

import retrieval

_DIFF = re.compile(r"^diff --git a/(\S+) b/\S+", re.M)


def files_of_patch(patch: str) -> list[str]:
    """Files the patch edits, in order of appearance."""
    return _DIFF.findall(patch or "")


def topic_of_instance(row: dict) -> frozenset:
    return retrieval.topic_of(files_of_patch(row.get("patch", "")))


def distribution(rows) -> dict:
    """Distribution of |topic|.  Used to fix theta FROM DATA, not by guessing."""
    sizes = [len(topic_of_instance(r)) for r in rows]
    hist: dict = {}
    for s in sizes:
        hist[s] = hist.get(s, 0) + 1
    return {"n": len(sizes),
            "median": int(statistics.median(sizes)) if sizes else 0,
            "hist": dict(sorted(hist.items()))}
