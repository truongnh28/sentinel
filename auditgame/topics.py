"""
topics.py -- gold patch -> module token set.  Spec: docs/thesis/pipelines/SPEC-P1a-Harness.md Part 2.

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
    # The median is returned as a FLOAT, not int()-truncated. The decision gate
    # in PLAN.md is "median > 3 => proceed, median <= 3 => STOP and tokenize
    # finer", and statistics.median averages the two middle values on an even n,
    # so a true 3.5 is a PROCEED that int() would report as "3" -- a STOP the
    # data never called for. Both pools measure 4.0 today, so nothing already
    # published moves; the truncation is removed because the gate reads this
    # number, not because the number is currently wrong. Formatting is the
    # caller's business.
    return {"n": len(sizes),
            "median": float(statistics.median(sizes)) if sizes else 0.0,
            "hist": dict(sorted(hist.items()))}
