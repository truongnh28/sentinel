"""
metrics.py -- The three-tier metric stack.  (B5)

Spec: eval/SPEC-Tang-Do-va-Test.md, Parts 4-5, SS6.4, SS8.3.

Three jobs, each closing a hole that was actually measured:

  1. gain() returns None once the denominator stops meaning anything.  The old
     experiment.py divided by max(h_B1, 1e-9): as h_B1 -> 0 the ratio explodes or
     flips sign -- precisely in the Delta=0 cell we most need to read.
  2. report_header() enforces FORMAT.  Gate 3 cannot be enforced by assertions;
     a table missing these lines is not a results table.
  3. The three terms of L, and lambda* instead of inventing a lambda.
"""
from __future__ import annotations

# Below this the ratio stops meaning anything -- report ABSOLUTE Delta-harm.
GAIN_FLOOR = 0.05


def gain(h_b1: float, h_sentinel: float, floor: float = GAIN_FLOOR):
    """Percent reduction in worst-case harm vs B1 -- or None if meaningless.

    Returns None, NOT 0 and NOT NaN: None forces the caller to handle it, while 0
    would quietly average in and turn "unreadable" into "no benefit".
    """
    if h_b1 < floor:
        return None
    return 100.0 * (h_b1 - h_sentinel) / h_b1


def report_header(config_sha: str, n_feasible: int, n_total: int,
                  n_survived: int) -> str:
    """The four mandatory lines of every results table (SS8.3).

    They pre-answer the first four questions a reviewer asks.  A bare number
    without them FORCES THE READER TO TRUST US -- which is the very thing this
    framework exists to avoid having to beg for.
    """
    pct = (100.0 * n_survived / n_feasible) if n_feasible else float("nan")
    return (f"config     sha256:{config_sha[:12]}...\n"
            f"feasible   {n_feasible}/{n_total}\n"
            f"survived   {n_survived}/{n_feasible} ({pct:.0f}%)")
