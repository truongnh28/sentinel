"""v3/drift.py -- the benign drift text of v3, matched to the payload on edit size (L0).

Draft S8, Table 1: benign changes are "matched on edit size" to the poisoning events.
v2's world_v2.drift_content (FROZEN, not touched) pads a drift revision up to
build.PAYLOAD_LENGTH but never shortens it; on SWE-bench topics 96% of drift items came
out longer than the payload (docs/reports/v3-p3-benign.md, 27/09), and edit size alone
separated drift from payload (AUC 0.970).

Decision of 27/09 (the author, before any rerun): v3's drift text has EXACTLY the length
of the payload the attacker would write on the same topic.

    target(topic) = len(build.payload_content(topic, .)) = PAYLOAD_LENGTH, or the tag
                    alone when the tag reaches L (build.payload_length_reason's case)
    text          = v2's drift text (the same template, prose_world.benign as v2 calls it)
    shorter       -> padded with "." as v2 does
    longer        -> cut on the last word boundary at or before target (trailing
                     whitespace dropped), then padded with "."; a hard cut at target only
                     when no boundary exists inside the budget.

Stdlib only; imports v2, never patches it.
"""
from __future__ import annotations

import build
import prose_world as _PW

PAD = "."


def target_length(topic) -> int:
    """The payload's length on `topic`: L, or the tag alone when the tag reaches L."""
    return max(build.PAYLOAD_LENGTH, len(build.payload_tag(topic)))


def fit_length(s: str, n: int) -> str:
    """`s` at exactly `n` characters: pad with PAD, or cut on a word boundary and pad."""
    if len(s) <= n:
        return s.ljust(n, PAD)
    if s[n].isspace():
        cut = n
    else:
        cut = max(s.rfind(" ", 0, n + 1), 0)
        if cut == 0:
            cut = n                                     # no boundary: hard cut
    return s[:cut].rstrip().ljust(n, PAD)


def drift_content(topic, task_id: str, carrier: str) -> str:
    """world_v2.drift_content's text at exactly the payload's length on `topic`."""
    s = _PW.benign(topic, task_id, carrier, f"[{topic}] cập nhật quy ước {task_id}/{carrier}")
    return fit_length(s, target_length(topic))
