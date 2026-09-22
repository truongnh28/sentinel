#!/usr/bin/env python3
"""
run_all.py -- Runs the suite GATE BY GATE, stopping at the first red gate.

Stopping is DELIBERATE.  Running gate 2 while gate 1 is red only produces a screen
full of failures none of which is worth reading: if a number cannot be reproduced,
asking "what does it mean" is a meaningless question.

A SKIPPED test is reported separately from a green one, and a gate holding one is
never called green.  A skip is a claim with no evidence in this run; folding it
into the pass count makes the suite loudest exactly where it knows least.

    cd auditgame
    python3 tests/run_all.py
    python3 tests/run_all.py --all      # run everything, do not stop (for the full picture)
"""
from __future__ import annotations
import argparse, io, os, sys, unittest

GATES = [
    ("GATE 1 - INTEGRITY", "tests/gate1_integrity",
     "are the numbers real -- if red, EVERY number below is worthless"),
    ("GATE 2 - VALIDITY",  "tests/gate2_validity",
     "what are the numbers about -- if red, they are real but about something else"),
    ("GATE 3 - POWER",     "tests/gate3_power",
     "is there enough to conclude -- if red, the 15% gate cannot be stated"),
]

W = 78

def run_gate(path: str) -> unittest.TestResult:
    suite = unittest.TestLoader().discover(start_dir=path, top_level_dir=".")
    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
    res._log = buf.getvalue()
    return res

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="run every gate, do not stop at the first red one")
    a = ap.parse_args()

    if not os.path.isdir("tests"):
        print("Must be run from the auditgame/ directory (cwd has to be on sys.path)")
        return 2
    sys.path.insert(0, os.getcwd())

    first_red, summary = None, []
    for title, path, gloss in GATES:
        print("=" * W); print(f"  {title}"); print(f"  {gloss}"); print("=" * W)
        res = run_gate(path)
        bad = len(res.failures) + len(res.errors)
        # `testsRun` COUNTS SKIPPED TESTS.  Subtracting only failures+errors from
        # it therefore prints a skip as a pass, and the suite's skips are not
        # decorative: tests/gate1_integrity/test_real_data.py skips the whole
        # WorkflowGrouping class when data/swebench_verified.jsonl is absent --
        # the NORMAL state of a fresh clone, because that file is gitignored on
        # purpose.  Those are the tests that pin the question-4 decision numbers
        # (500 / 12 / 10 / 58 / 42%), whose own assertion messages say a mismatch
        # means STOP AND INVESTIGATE.  Counted as green, a clone would print
        # "REPORTABLE" having verified none of them.  A skip is NOT a pass: it is
        # a claim that was never put to the test.
        skipped = len(res.skipped)
        summary.append((title, res.testsRun, bad, skipped))

        for case, tb in res.failures + res.errors:
            name = case.id().rsplit(".", 1)[-1].removeprefix("test_")
            # the last line of the traceback is the message -- the CLAIM that just lost its support
            msg = [l for l in tb.strip().splitlines() if l.strip()][-1]
            print(f"  x {name}\n      {msg[:400]}")
        for case, reason in res.skipped:
            # The FULL id, not the short name: a class-level skip (setUpClass)
            # has no test name of its own, and "WorkflowGrouping)" on its own
            # tells the reader nothing about how many claims just went dark.
            print(f"  ? {case.id().removeprefix('tests.')}  NOT VERIFIED"
                  f"\n      skipped: {reason[:200]}")
        ok = res.testsRun - bad - skipped
        print(f"\n  -> {ok}/{res.testsRun} green"
              + ("" if bad == 0 else f" - {bad} RED")
              + ("" if skipped == 0 else f" - {skipped} SKIPPED (claims NOT verified)"))
        if skipped and not bad:
            print(f"  !! {title} is NOT fully verified: {skipped} test(s) never ran.")
            print("     Treat this gate as UNKNOWN, not green -- the claims those")
            print("     tests protect (decision-gate numbers among them) have no")
            print("     support in this run.  A setUpClass skip is ONE entry for")
            print("     a WHOLE class, and unittest does not even count the tests")
            print("     it hides, so the number of unverified claims is a LOWER")
            print("     BOUND on what the skip cost.")

        if bad and first_red is None:
            first_red = title
            if not a.all:
                print("\n" + "!" * W)
                print(f"  STOPPED at {title}.")
                print("  Later gates were NOT run: fix this one first.")
                print("  (use --all for the full picture)")
                print("!" * W)
                break
        print()

    print("=" * W); print("  SUMMARY"); print("=" * W)
    any_skipped = 0
    for title, run, bad, skipped in summary:
        any_skipped += skipped
        mark = " x" if bad else ("??" if skipped else "OK")
        note = "" if skipped == 0 else f"   ({skipped} SKIPPED - NOT VERIFIED)"
        print(f"  {mark} {title:24s} {run - bad - skipped}/{run}{note}")
    if first_red:
        print(f"\n  First red gate: {first_red}")
        print("  The REPAIR ORDER is mandatory -- patching gate 2 while gate 1 is red is building on sand.")
    elif any_skipped:
        print(f"\n  NOT REPORTABLE: nothing is red, but {any_skipped} test(s) were SKIPPED.")
        print("  A skipped test is a claim with NO evidence in this run, not a claim")
        print("  that held.  Restore whatever the skip is waiting on (most often")
        print("  data/swebench_verified.jsonl, see swebench_fetch.py) and run again")
        print("  before quoting any number from this build.")
    else:
        print("\n  All three gates green => the results are REPORTABLE.")
    # A skip leaves the exit status 0 only when it is NOT a gate-blocking skip;
    # here every skip hides a claim, so it is reported as a non-zero status too.
    return 1 if (first_red or any_skipped) else 0

if __name__ == "__main__":
    sys.exit(main())
