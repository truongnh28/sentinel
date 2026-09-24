"""
r1_tier.py -- THE FIFTEEN PER-INSTANCE HIDDEN TESTS, AS ONE REGISTRY FAMILY.

`per_instance.TESTS` has been V1/V2/V3-green on REAL gold patch text since Task
10b (tests/gate1_integrity/test_r1_agreement.EveryR1TestClearsTheThreeGates), and
until this module existed the oracle could not reach a single one of them:
`registry.FAMILIES` held only H1, so `oracle.HiddenTestOracle` scored exactly ONE
instance in 500 while fifteen verified properties sat one import away.  That gap
was not a measurement about the corpus, it was missing wiring, and it is the whole
content of this file.

WHY A MODULE AND NOT A DICT ENTRY POINTING AT `per_instance`.  A registry family
is a pair, `anchor_for(row)` and `check(patch, anchor)` (registry.py's opening
line).  `per_instance` exposes neither: its `R1Test.check` takes a patch alone,
because each test already knows its own file.  Adapting it HERE rather than
widening `R1Test` keeps the fifteen properties readable as fifteen properties --
and keeps `per_instance.py` a file whose entire content is checks, which is what
lets the marker grep below mean something.

WHY R1 IS ONE FAMILY AND NOT FIFTEEN.  A family names a PROPERTY SHAPE, and the
name travels into `oracle.OracleScope.families` and from there into the results
header.  Fifteen family names would put an instance id in a header line that is
supposed to say what KIND of test scored the column; the instance is already
identified by the anchor, which is the R1Test itself -- `anchor.prop` is the
property in one English sentence.  So the header says `families=H1,R1` and the
sealed trace says which instance.

THIS MODULE MAY NEVER SPELL THE MARKER, for the same reason `per_instance.py` may
not: a checker that can name the injector's signature can key on it, and gate V3
exists to reject exactly that.  `test_r1_agreement` greps both files' source.
"""
from __future__ import annotations

from hidden_tests.per_instance import TESTS

#: instance_id -> R1Test.  Built from TESTS rather than restated, so a test added
#: there is reachable by the oracle without a second edit -- the one-copy rule
#: that `freeze.constants()` follows for the constants.
BY_INSTANCE = {t.instance_id: t for t in TESTS}

assert len(BY_INSTANCE) == len(TESTS), (
    "two R1 tests claim the same instance_id: one of them would be unreachable "
    "from the oracle while still counting in the agreement rate")


def anchor_for(row: dict):
    """The R1Test written for THIS instance, or None.

    Keyed on `instance_id` alone.  A family that anchored by repo or by touched
    file would attach one instance's property to another instance's patch, and the
    resulting harm would be charged to an agent that never violated anything.
    """
    return BY_INSTANCE.get(row.get("instance_id"))


def check(patch: str, anchor) -> bool:
    """True = the property still holds (the hidden test passes)."""
    return anchor.check(patch)
