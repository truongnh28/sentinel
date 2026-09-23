"""checkpoints.py -- the four audit stages, doing the work they are named for.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 2;
docs/design/plans/2026-09-23-tham-so-dot-2.md T8.

WHY THIS MODULE EXISTS.  kappa is supposed to be the cost of AUDITING a carrier,
and Stage 2 names four checkpoints that each do a different job.  What the runner
timed before this module was `detector.score` -- one Gaussian draw per item.  That
made every carrier cost the same (measured: chi = 0.16), so the cost table
described the SIMULATOR rather than the audit, and the chi axis of the regime
boundary rested on a number about random sampling.

Each function below inspects real fields of real objects and returns findings.
Cost therefore scales with what the stage actually has to look at: how many items,
how long their content is, how deep their lineage runs.

TWO INVARIANTS, BOTH LOAD-BEARING.

  NO GROUND TRUTH.  Nothing here reads `Item.poisoned` or anything derived from
  it.  These are the defender's own checks; if they could see the label, every
  policy would audit perfectly and the benchmark would stop measuring allocation.
  `tests/gate1_integrity/test_audit_stages.py` enforces this for the probe path.

  NO SIDE EFFECTS.  A checkpoint reads the store and returns findings.  It never
  quarantines, never writes, never draws from a shared rng.  The runner times it
  and stores a DURATION; the findings are not fed back into any decision, so
  calling a checkpoint an extra time changes nothing but the clock.

WHAT IS MISSING, AND IT IS THE EXPENSIVE HALF.  Stage 2 defines the commit
checkpoint as "patch review + DIFFERENTIAL TESTING + provenance of the skill".
Differential testing means running the repository's test suite, which needs the
Docker image per instance.  `commit()` below does the review and the provenance
walk and does NOT run tests, so kappa_commit measured through it is a LOWER
BOUND.  Any table quoting it has to say so.
"""
from __future__ import annotations

import re

from core import Item, seed_of

#: Provenance strings the benchmark itself writes.  A value outside this set is
#: not "suspicious" -- it is unparseable, which is a different finding.
KNOWN_PROVENANCE = ("agent", "inject", "derived")

_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def _tokens(text: str) -> set:
    return set(_WORD.findall(text or ""))


def _recompute_id(it: Item) -> str:
    """Rebuild item_id from the fields it is hashed over.

    This is the integrity half of an insertion audit: an item whose id does not
    match its own content was rewritten under a kept id.  It is real work, and
    its cost scales with the content length, which is what makes a carrier of
    long items more expensive to audit than a carrier of short ones.
    """
    h = seed_of(it.carrier, it.topic, it.content, it.created_at,
                it.provenance, it.derived_from)
    return f"{it.carrier[:3]}-{h & 0xFFFFFFFF:08x}"


def insertion(items, store=None, task=None) -> dict:
    """Content + provenance check on freshly written records.

    Three questions, none of which needs the label:
      1. does the record hash to its own id (was it rewritten in place)?
      2. is its provenance one this benchmark writes?
      3. do the topic tokens it claims actually occur in its content?
    """
    findings = {"checked": 0, "id_mismatch": 0, "unknown_provenance": 0,
                "topic_not_in_content": 0}
    for it in items:
        findings["checked"] += 1
        if _recompute_id(it) != it.item_id:
            findings["id_mismatch"] += 1
        if it.provenance.split("/")[0] not in KNOWN_PROVENANCE:
            findings["unknown_provenance"] += 1
        body = _tokens(it.content)
        claimed = _tokens(str(it.topic))
        if claimed and not (claimed & body):
            findings["topic_not_in_content"] += 1
    return findings


def retrieval(items, store=None, task=None) -> dict:
    """Consistency between a retrieved record and the request that pulled it.

    The record came back because its topic matched the task's.  This recomputes
    that match from the record's own content rather than trusting the stored
    topic field, which is the check the stage is named for.
    """
    want = _tokens(str(getattr(task, "topic", "")))
    findings = {"checked": 0, "weak_match": 0, "topic_drift": 0}
    for it in items:
        findings["checked"] += 1
        body = _tokens(it.content)
        stored = _tokens(str(it.topic))
        overlap = (want & body)
        if want and not overlap:
            findings["weak_match"] += 1
        if stored and body and not (stored & body):
            findings["topic_drift"] += 1
    return findings


def delegation(items, store=None, task=None) -> dict:
    """Contract + evidence: does a derived record's lineage hold up.

    A skill is supposed to be distilled from records that still exist and still
    hash to themselves.  Walking that chain is the work; a carrier whose items
    carry deep lineage costs more to audit than one whose items stand alone.
    """
    findings = {"checked": 0, "missing_ancestor": 0, "ancestor_id_mismatch": 0,
                "no_shared_tokens": 0, "lineage_steps": 0}
    by_id = {}
    if store is not None:
        by_id = {x.item_id: x for x in store.live()}
    for it in items:
        findings["checked"] += 1
        body = _tokens(it.content)
        for anc_id in it.derived_from:
            findings["lineage_steps"] += 1
            anc = by_id.get(anc_id)
            if anc is None:
                findings["missing_ancestor"] += 1
                continue
            if _recompute_id(anc) != anc.item_id:
                findings["ancestor_id_mismatch"] += 1
            if body and not (body & _tokens(anc.content)):
                findings["no_shared_tokens"] += 1
    return findings


def commit(items, store=None, task=None) -> dict:
    """Patch review + provenance of every skill that contributed.

    The mock agent does not emit patch text; what it emits is the branch record
    the commit carries, so the review walks THAT: its full transitive lineage
    across carriers, re-hashing each ancestor and comparing token sets.  This is
    the deepest of the four stages by construction, which is the ordering the
    manuscript's cost table claims and this one can now be checked against.

    DIFFERENTIAL TESTING IS NOT DONE HERE -- see the module docstring.  The cost
    this returns is a lower bound on a real commit audit.
    """
    findings = {"checked": 0, "lineage_steps": 0, "missing_ancestor": 0,
                "ancestor_id_mismatch": 0, "carriers_touched": 0,
                "added_identifiers": 0}
    by_id = {}
    if store is not None:
        by_id = {x.item_id: x for x in store.live()}
    for it in items:
        findings["checked"] += 1
        findings["added_identifiers"] += len(_tokens(it.content))
        seen, frontier, carriers = set(), list(it.derived_from), set()
        while frontier:
            anc_id = frontier.pop()
            if anc_id in seen:
                continue
            seen.add(anc_id)
            findings["lineage_steps"] += 1
            anc = by_id.get(anc_id)
            if anc is None:
                findings["missing_ancestor"] += 1
                continue
            carriers.add(anc.carrier)
            if _recompute_id(anc) != anc.item_id:
                findings["ancestor_id_mismatch"] += 1
            frontier.extend(anc.derived_from)
        findings["carriers_touched"] += len(carriers)
    return findings


#: The runner looks the stage up by name; a stage with no entry is a stage
#: nobody implemented, and KeyError says so instead of silently timing nothing.
STAGES = {"insertion": insertion, "retrieval": retrieval,
          "delegation": delegation, "commit": commit}
