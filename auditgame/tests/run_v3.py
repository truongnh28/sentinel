#!/usr/bin/env python3
"""
run_v3.py -- Runs the v3 suite (tests/v3/) GATE BY GATE, stopping at the first red gate.

The same rules as tests/run_all.py, for the same reasons:
  * stopping is deliberate -- a later gate read while an earlier one is red is noise;
  * a SKIPPED test is reported apart from a green one, and a gate holding one is never
    called green: a skip is a claim with no evidence in this run.

    GATE 0  V2 INTACT   tests/v3/test_infra_v2_*.py  -- if red, v3 has moved v2's freeze
                                                        and every v2 number is in question
    GATE 1  INFRA       the other tests/v3/test_infra_*.py -- DCM, config/api, seal, freeze
    GATE 2  DRAFT       every other tests/v3/test_*.py -- the draft sentences (DCM rows)

Tests are discovered, so a task adds a test file without touching this runner.  After the
gates it prints how many DCM rows are PENDING (named test file not written yet); pending
is not green, and `tools/v3_dcm.py --check` fails on it (G2, T23).

    cd auditgame
    ../.venv/bin/python tests/run_v3.py
    ../.venv/bin/python tests/run_v3.py --all      # run every gate, do not stop
"""
from __future__ import annotations

import argparse
import io
import os
import pathlib
import sys
import unittest

W = 78
V3 = pathlib.Path("tests") / "v3"

GATES = [
    ("GATE 0 - V2 INTACT", lambda n: n.startswith("test_infra_v2_"),
     "v3 imports v2 and never patches it -- if red, v2's freeze has moved"),
    ("GATE 1 - INFRA", lambda n: n.startswith("test_infra_") and not n.startswith("test_infra_v2_"),
     "the DCM, the shared contract, the seal and the freeze hold together"),
    ("GATE 2 - DRAFT", lambda n: not n.startswith("test_infra_"),
     "each test protects one sentence of the pinned draft (a DCM row)"),
]


def gate_suite(pick) -> unittest.TestSuite:
    loader, suite = unittest.TestLoader(), unittest.TestSuite()
    for path in sorted(V3.glob("test_*.py")):
        if pick(path.name):
            suite.addTests(loader.loadTestsFromName(f"tests.v3.{path.stem}"))
    return suite


def run_gate(pick) -> unittest.TestResult:
    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=2).run(gate_suite(pick))
    res._log = buf.getvalue()
    return res


def pending_rows() -> list:
    from tools import v3_dcm
    rows, _ = v3_dcm.load()
    _, pending = v3_dcm.check_p2_tests_exist(rows, v3_dcm.collect_tests())
    return pending


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="run every gate, do not stop at the first red one")
    a = ap.parse_args()

    if not V3.is_dir():
        print("Must be run from the auditgame/ directory (cwd has to be on sys.path)")
        return 2
    # Drop this script's own directory (tests/) from the path: it holds the regular package
    # tests/tools/, which would shadow the namespace package tools/ (tools/v3_dcm.py).
    here = pathlib.Path(__file__).resolve().parent
    sys.path[:] = [p for p in sys.path if pathlib.Path(p or ".").resolve() != here]
    sys.path.insert(0, os.getcwd())

    first_red, summary = None, []
    for title, pick, gloss in GATES:
        print("=" * W); print(f"  {title}"); print(f"  {gloss}"); print("=" * W)
        res = run_gate(pick)
        bad = len(res.failures) + len(res.errors)
        skipped = len(res.skipped)
        summary.append((title, res.testsRun, bad, skipped))
        for case, tb in res.failures + res.errors:
            name = case.id().rsplit(".", 1)[-1].removeprefix("test_")
            msg = [l for l in tb.strip().splitlines() if l.strip()][-1]
            print(f"  x {name}\n      {msg[:400]}")
        for case, reason in res.skipped:
            print(f"  ? {case.id().removeprefix('tests.')}  NOT VERIFIED"
                  f"\n      skipped: {reason[:200]}")
        ok = res.testsRun - bad - skipped
        print(f"\n  -> {ok}/{res.testsRun} green"
              + ("" if bad == 0 else f" - {bad} RED")
              + ("" if skipped == 0 else f" - {skipped} SKIPPED (claims NOT verified)"))
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

    pending = pending_rows()
    print("=" * W); print("  SUMMARY"); print("=" * W)
    any_skipped = 0
    for title, run, bad, skipped in summary:
        any_skipped += skipped
        mark = " x" if bad else ("??" if skipped else "OK")
        note = "" if skipped == 0 else f"   ({skipped} SKIPPED - NOT VERIFIED)"
        print(f"  {mark} {title:24s} {run - bad - skipped}/{run}{note}")
    by_shard: dict = {}
    for r in pending:
        by_shard[r.shard] = by_shard.get(r.shard, 0) + 1
    print(f"\n  DCM: {len(pending)} P2 row(s) PENDING -- their test files are not written yet"
          + (f" ({', '.join(f'{s}: {n}' for s, n in sorted(by_shard.items()))})" if pending else ""))
    if pending:
        print("  Pending is not green: `tools/v3_dcm.py --check` fails until every one is written.")
    if first_red:
        print(f"\n  First red gate: {first_red}")
        print("  The REPAIR ORDER is mandatory: fix the earliest red gate first.")
    elif any_skipped:
        print(f"\n  NOT FULLY VERIFIED: nothing is red, but {any_skipped} test(s) were SKIPPED.")
    else:
        print("\n  Every gate green.")
    return 1 if (first_red or any_skipped) else 0


if __name__ == "__main__":
    sys.exit(main())
