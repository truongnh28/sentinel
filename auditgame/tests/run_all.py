#!/usr/bin/env python3
"""
run_all.py -- Runs the suite GATE BY GATE, stopping at the first red gate.

Stopping is DELIBERATE.  Running gate 2 while gate 1 is red only produces a screen
full of failures none of which is worth reading: if a number cannot be reproduced,
asking "what does it mean" is a meaningless question.

    cd HCMUT/code/Sentinel/auditgame
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
        summary.append((title, res.testsRun, bad))

        for case, tb in res.failures + res.errors:
            name = case.id().rsplit(".", 1)[-1].removeprefix("test_")
            # the last line of the traceback is the message -- the CLAIM that just lost its support
            msg = [l for l in tb.strip().splitlines() if l.strip()][-1]
            print(f"  x {name}\n      {msg[:400]}")
        ok = res.testsRun - bad
        print(f"\n  -> {ok}/{res.testsRun} green"
              + ("" if bad == 0 else f" - {bad} RED"))

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
    for title, run, bad in summary:
        mark = "OK" if bad == 0 else " x"
        print(f"  {mark} {title:24s} {run - bad}/{run}")
    if first_red:
        print(f"\n  First red gate: {first_red}")
        print("  The REPAIR ORDER is mandatory -- patching gate 2 while gate 1 is red is building on sand.")
    else:
        print("\n  All three gates green => the results are REPORTABLE.")
    return 1 if first_red else 0

if __name__ == "__main__":
    sys.exit(main())
