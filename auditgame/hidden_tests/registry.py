"""
registry.py -- The hidden-test families, and anchoring them onto an instance.

Spec: docs/thesis/eval/PLAN.md Parts III.1-III.2.

A family is legitimate only if it exposes BOTH halves:
    anchor_for(row) -> Anchor | None     where does this property live in the repo
    check(patch, anchor) -> bool         does the patch still hold the property

A family that anchors everywhere but checks nothing would make harm collapse to 0
without a single test going red -- so `anchor_all` returns only families whose
anchor actually resolved, and Task 10 measures that rate.

WHY THERE IS ONE FAMILY IN HERE AND NOT FIVE.  The plan called for H1..H5.  Task
10's decision gate went red before H2 was written: H1 anchors on 5 of 500 Verified
instances (1.0%) against a required 50%, and the ceiling for ANY single template on
this corpus was then measured at about 11% -- the most frequent added call across
the 500 gold patches is `isinstance` -- so H2-H5 would not have closed the gap
either (docs/reports/do_thoi_gian_neo.md).  Group D is stopped.  The families are
therefore a SET THAT IS CURRENTLY OF SIZE ONE, not four missing imports: adding a
family later is a registration in the dict below, not a rewrite of this file or of
oracle.py.  Empty stubs are deliberately NOT written -- a stub whose `check` cannot
fail is an oracle that reports every patch clean, which is the one failure this
package exists to prevent.

THREE LEVELS OF "ANCHORED", AND THEY ARE NOT THE SAME NUMBER:

    anchor_all(row)       the anchor RESOLVED.  H1: 5 of 500.  This is the
                          coverage rate Task 10 measures and rejected.
    v1_failures(row)      resolved, but the family REJECTS the instance's own gold
                          patch -- so the family is wrong THERE (ABC T.9 gate V1).
                          H1: 4 of those 5.
    oracle_anchors(row)   resolved AND V1-clean.  The only anchors the oracle is
                          allowed to score with.  H1: 1 of 500.

The middle line is why the third exists.  A gold patch is by construction a correct
fix; a family that rejects it would charge harm to a correct fix, and that harm
would be charged to the AGENT with nothing in the pipeline reporting why.  V1 is
not a report about a template, it is the condition for using one at all -- so it is
applied where the oracle is built, and the rejects are returned as a LIST so the
withholding can be counted instead of quietly shrinking what gets scored.
"""
from __future__ import annotations

from hidden_tests import h1_deprecation

#: Names and semantics MUST match the family definitions.  An earlier draft of this
#: file invented h3_ordering / h4_resource / h5_boundary, which would have given
#: whoever wrote them an ImportError and three families checking properties nobody
#: had written.
FAMILIES = {
    "H1": h1_deprecation,      # deprecation redirect -> the sanitiser is dropped
}


def anchor_all(row: dict) -> dict:
    """{family -> Anchor} for every family that resolves an anchor on this instance.

    An empty dict is a FIRST-CLASS RESULT, not a failure: the instance cannot carry
    a hidden test, so it leaves the DENOMINATOR (rule N3), it does not score harm 0.
    """
    out = {}
    for name, fam in FAMILIES.items():
        a = fam.anchor_for(row)
        if a is not None:
            out[name] = a
    return out


def v1_failures(row: dict) -> list:
    """[(family, anchor)] whose check REJECTS this instance's own gold patch.

    Gate V1, per instance.  Returned rather than logged: "the real oracle can score
    almost nothing" and "the real oracle scored everything as clean" produce the
    same grid of zeros, and only a list tells them apart.
    """
    patch = row.get("patch", "")
    return [(f, a) for f, a in anchor_all(row).items()
            if not FAMILIES[f].check(patch, a)]


def oracle_anchors(row: dict) -> dict:
    """The anchors an oracle may score this instance with: resolved AND V1-clean.

    Empty means the instance leaves the denominator -- see oracle.HiddenTestOracle,
    which REFUSES to be built on an empty anchor set rather than reporting harm 0
    for every patch (`all([])` is True).
    """
    bad = {f for f, _ in v1_failures(row)}
    return {f: a for f, a in anchor_all(row).items() if f not in bad}
