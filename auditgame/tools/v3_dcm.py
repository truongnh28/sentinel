#!/usr/bin/env python3
"""tools/v3_dcm.py -- the draft compliance matrix (DCM): load, check, render (plan S5).

The DCM is kept as one CSV shard per task, auditgame/v3/dcm/T<nn>.csv, so parallel
worktrees never write the same file.  Each row pairs ONE sentence of the pinned draft with
the ONE test that protects it.  This tool merges the shards.

    cd auditgame
    ../.venv/bin/python tools/v3_dcm.py --check     # the six checks, strict (G2, T23)
    ../.venv/bin/python tools/v3_dcm.py --render    # write ../docs/v3/DCM.md (T0, T23 only)
    ../.venv/bin/python tools/v3_dcm.py --pending   # rows whose test file is not written yet

THE SIX CHECKS (plan S5 "Cong kiem"):
  1. (id, test) is unique across every shard.
  2. every phase=P2 row names a test that exists and is green.
  3. every test in tests/v3/ is a DCM row or an infrastructure test (file test_infra_*).
  4. every quote is verbatim in the pinned draft text, after normalisation.
  5. the draft PDF's sha256 matches the pin (and every shard's header names it).
  6. the docstring of each named test contains the row's id.

PENDING IS NOT GREEN.  The plan declares a row BEFORE its code ("Moi lua chon L1/L2 co dong
DCM truoc commit ma tuong ung"), so between waves a P2 row may name a test in a file its
task has not written yet.  Such a row is PENDING.  The tests run by tests/run_v3.py accept
a pending row only when (a) the named file does not exist at all and (b) that file belongs
to the shard's task in the plan's ownership table (S9); once the file exists, the named
class and method must exist in it.  `--check` is strict: a pending row is a failure there,
because G2 closes only when every P2 row has a green test.

NORMALISATION FOR CHECK 4.  Both sides are NFKC-normalised and every run of whitespace is
collapsed to one space.  NFKC maps the PDF's mathematical italic letters (U+1D70E, ...) to
the plain Greek and Latin letters, so a quote is written in readable characters; it
changes no word.  A quote may elide with U+2026 (the ellipsis character): every fragment
must then appear, in order.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata
import unittest
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent          # auditgame/
REPO = ROOT.parent                                             # code/Sentinel/
DCM_DIR = ROOT / "v3" / "dcm"
TESTS_DIR = ROOT / "tests" / "v3"
DRAFT_PDF = REPO / "docs" / "FSE-2027-15-paper.pdf"
#: The vault copy the plan names (261-Master-Proposal/).  Checked when present.
DRAFT_PDF_VAULT = REPO.parent.parent / "261-Master-Proposal" / "FSE-2027-15-paper.pdf"
DRAFT_TXT = REPO / "docs" / "v3" / "draft-2026-09-07.txt"
DCM_MD = REPO / "docs" / "v3" / "DCM.md"

#: T1 of sentinel-v3.md: the draft of 07/09/2026 is the preregistration document.
DRAFT_PDF_SHA256 = "c37643f0971c3457c176c39607e1be6782007c85988c053e4b5ab0aa8be7263a"
#: `pdftotext docs/FSE-2027-15-paper.pdf` (poppler 26.08.0, default reading-order mode).
DRAFT_TXT_SHA256 = "7915e2cc55896a6c0ec208642360f5dda443d9d7311bbd1c324564380af5c24e"
SHARD_HEADER = f"# draft-pdf-sha256: {DRAFT_PDF_SHA256}"

COLUMNS = ("id", "where", "quote", "level", "c_ref", "decision", "module", "test", "phase",
           "result_ref")
PHASES = ("P2", "P3", "P4", "P5")
ELLIPSIS = "\u2026"
ID_RE = re.compile(r"^D[0-9A-Z][0-9A-Za-z.\-]*$")
LEVEL_RE = re.compile(r"^L[012](\+L[012])*$")
TEST_RE = re.compile(r"^tests/v3/(test_\w+\.py)::(\w+)::(test_\w+)$")
SHARD_RE = re.compile(r"^T(\d\d)\.csv$")

#: Plan S9, the test files each task owns.  A shard's rows may name tests in these only.
OWNED_TESTS = {
    "T00": ("test_infra_dcm.py", "test_infra_v2_intact.py"),
    "T01": ("test_s8_config.py", "test_infra_config.py"),
    "T02": ("test_s8_corpus.py", "test_infra_seal.py"),
    "T03": ("test_s4_state_payload.py",),
    "T04": ("test_s4_agent.py", "test_infra_v2_compat.py"),
    "T05": ("test_s4_observe.py",),
    "T06": ("test_s4_runner.py", "test_fig1.py"),
    "T07": ("test_s4_attacker.py",),
    "T08": ("test_s5_baselines.py",),
    "T09": ("test_alg1_line7.py",),
    "T10": ("test_alg1_line1.py",),
    "T11": ("test_s5_library.py",),
    "T12": ("test_alg1_line5_8.py",),
    "T13": ("test_alg1_line23.py",),
    "T14": ("test_alg1_line5_table.py",),
    "T15": ("test_alg1_sentinel.py",),
    "T16": ("test_s9_budget.py",),
    "T17": ("test_s9_metrics.py",),
    "T18": ("test_s5_tuning.py",),
    "T19": ("test_s9_rollout_check.py",),
    "T20": ("test_s4_sensitivity.py",),
    "T21": ("test_s8_smallgames.py",),
    "T22": ("test_infra_grid.py", "test_infra_freeze.py"),
    "T24": ("test_s8_benign.py",),
}


@dataclass(frozen=True)
class Row:
    id: str
    where: str
    quote: str
    level: str
    c_ref: str
    decision: str
    module: str
    test: str
    phase: str
    result_ref: str
    shard: str                         # "T03"
    line: int                          # 1-based line in the shard file

    @property
    def loc(self) -> str:
        return f"{self.shard}.csv:{self.line}"


# ---------------------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------------------

def shard_paths(dcm_dir: pathlib.Path = DCM_DIR) -> list:
    return sorted(p for p in dcm_dir.glob("*.csv") if SHARD_RE.match(p.name))


def load(dcm_dir: pathlib.Path = DCM_DIR) -> tuple:
    """(rows, problems).  Problems are format errors: a malformed shard still yields the
    rows it can, so one bad line does not hide the rest of the matrix."""
    rows, problems = [], []
    for path in shard_paths(dcm_dir):
        shard = path.stem
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or lines[0].strip() != SHARD_HEADER:
            problems.append(f"{path.name}:1: first line must be {SHARD_HEADER!r}")
        body = "\n".join(lines[1:]) + "\n"
        reader = csv.reader(io.StringIO(body))
        header = next(reader, None)
        if tuple(header or ()) != COLUMNS:
            problems.append(f"{path.name}:2: columns must be {','.join(COLUMNS)}")
            continue
        for i, rec in enumerate(reader, start=3):
            if not rec or all(not x.strip() for x in rec):
                continue
            if len(rec) != len(COLUMNS):
                problems.append(f"{path.name}:{i}: {len(rec)} fields, expected {len(COLUMNS)}")
                continue
            vals = dict(zip(COLUMNS, (x.strip() for x in rec)))
            rows.append(Row(**vals, shard=shard, line=i))
    return rows, problems


def check_format(rows: list) -> list:
    out = []
    for r in rows:
        if not ID_RE.match(r.id):
            out.append(f"{r.loc}: id {r.id!r} is not D<section>.<name>")
        if not LEVEL_RE.match(r.level):
            out.append(f"{r.loc}: level {r.level!r} is not L0/L1/L2")
        if r.phase not in PHASES:
            out.append(f"{r.loc}: phase {r.phase!r} is not one of {PHASES}")
        if not TEST_RE.match(r.test):
            out.append(f"{r.loc}: test {r.test!r} is not tests/v3/<file>.py::<Class>::<test_name>")
        for col in ("where", "quote", "decision", "module"):
            if not getattr(r, col):
                out.append(f"{r.loc}: empty {col}")
    return out


# ---------------------------------------------------------------------------------------
# Draft text
# ---------------------------------------------------------------------------------------

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip()


def draft_text(path: pathlib.Path = DRAFT_TXT) -> str:
    return normalize(path.read_text(encoding="utf-8"))


def quote_in(quote: str, text_normalized: str) -> bool:
    parts = [normalize(p) for p in quote.split(ELLIPSIS)]
    parts = [p for p in parts if p]
    if not parts:
        return False
    pos = 0
    for p in parts:
        i = text_normalized.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------
# Tests on disk (static: nothing is imported)
# ---------------------------------------------------------------------------------------

def collect_tests(tests_dir: pathlib.Path = TESTS_DIR) -> dict:
    """'tests/v3/<file>::<Class>::<test>' -> docstring ('' if none), for every test method
    of every unittest-style class in tests/v3/test_*.py."""
    out = {}
    for path in sorted(tests_dir.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if (isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name.startswith("test")):
                    out[f"tests/v3/{path.name}::{node.name}::{item.name}"] = (
                        ast.get_docstring(item) or "")
    return out


def is_infra(test_id: str) -> bool:
    return test_id.split("::", 1)[0].split("/")[-1].startswith("test_infra_")


def test_file_of(test_id: str) -> str:
    return test_id.split("::", 1)[0].split("/")[-1]


# ---------------------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------------------

def check_unique(rows: list) -> list:
    """Check 1."""
    seen, out = {}, []
    for r in rows:
        key = (r.id, r.test)
        if key in seen:
            out.append(f"{r.loc}: ({r.id}, {r.test}) already at {seen[key]}")
        else:
            seen[key] = r.loc
    return out


def check_p2_tests_exist(rows: list, tests: dict, tests_dir: pathlib.Path = TESTS_DIR,
                         strict: bool = False) -> tuple:
    """Check 2, existence half.  Returns (problems, pending rows).

    Not strict: a row is PENDING when its test file does not exist and the file belongs to
    the shard's task (plan S9).  Strict: pending rows are problems too."""
    out, pending = [], []
    for r in rows:
        if r.phase != "P2":
            continue
        fname = test_file_of(r.test)
        owned = OWNED_TESTS.get(r.shard)
        if owned is None:
            out.append(f"{r.loc}: shard {r.shard} is not a task of the plan (S9)")
            continue
        if fname not in owned:
            out.append(f"{r.loc}: {fname} is not a test file of {r.shard} (owns {', '.join(owned)})")
            continue
        if r.test in tests:
            continue
        if not (tests_dir / fname).exists():
            pending.append(r)
            if strict:
                out.append(f"{r.loc}: {r.test} is PENDING ({fname} not written)")
            continue
        out.append(f"{r.loc}: {r.test} does not exist ({fname} is written but has no such test)")
    return out, pending


def check_every_test_covered(rows: list, tests: dict) -> list:
    """Check 3."""
    named = {r.test for r in rows}
    return [f"{t}: neither a DCM row nor an infrastructure test (test_infra_*.py)"
            for t in sorted(tests) if not is_infra(t) and t not in named]


def check_quotes(rows: list, text_normalized: str) -> list:
    """Check 4."""
    return [f"{r.loc}: {r.id} quote is not verbatim in the pinned draft: {r.quote[:90]!r}"
            for r in rows if not quote_in(r.quote, text_normalized)]


def check_pins(dcm_dir: pathlib.Path = DCM_DIR) -> list:
    """Check 5: the PDF (repo copy, and the vault copy when present), the pinned text, and
    every shard's header."""
    out = []
    if not DRAFT_PDF.exists():
        out.append(f"draft PDF missing: {DRAFT_PDF}")
    elif sha256_file(DRAFT_PDF) != DRAFT_PDF_SHA256:
        out.append(f"{DRAFT_PDF.name}: sha256 {sha256_file(DRAFT_PDF)[:12]} != pinned "
                   f"{DRAFT_PDF_SHA256[:12]}")
    if DRAFT_PDF_VAULT.exists() and sha256_file(DRAFT_PDF_VAULT) != DRAFT_PDF_SHA256:
        out.append(f"vault copy {DRAFT_PDF_VAULT}: sha256 differs from the pin")
    if not DRAFT_TXT.exists():
        out.append(f"pinned draft text missing: {DRAFT_TXT}")
    elif sha256_file(DRAFT_TXT) != DRAFT_TXT_SHA256:
        out.append(f"{DRAFT_TXT.name}: sha256 {sha256_file(DRAFT_TXT)[:12]} != pinned "
                   f"{DRAFT_TXT_SHA256[:12]}")
    for p in shard_paths(dcm_dir):
        first = p.read_text(encoding="utf-8").splitlines()[:1]
        if first != [SHARD_HEADER]:
            out.append(f"{p.name}: header does not name the pinned PDF sha256")
    return out


def check_docstrings(rows: list, tests: dict) -> list:
    """Check 6 (for rows whose test exists)."""
    return [f"{r.loc}: docstring of {r.test} does not contain {r.id!r}"
            for r in rows if r.test in tests and r.id not in tests[r.test]]


def run_tests(test_ids: list) -> dict:
    """Run the named tests; test_id -> 'green' | 'RED' | 'skipped' | 'missing'."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    status = {}
    for tid in sorted(set(test_ids)):
        m = TEST_RE.match(tid)
        name = f"tests.v3.{m.group(1)[:-3]}.{m.group(2)}.{m.group(3)}"
        loader = unittest.TestLoader()
        try:
            suite = loader.loadTestsFromName(name)
        except (AttributeError, ImportError):
            status[tid] = "missing"
            continue
        res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        if res.failures or res.errors or loader.errors:
            status[tid] = "RED"
        elif res.skipped:
            status[tid] = "skipped"
        elif res.testsRun == 0:
            status[tid] = "missing"
        else:
            status[tid] = "green"
    return status


def check_all(strict: bool, run: bool = True) -> tuple:
    """Every check.  Returns (problems, pending, status)."""
    rows, problems = load()
    tests = collect_tests()
    problems += check_format(rows)
    problems += check_unique(rows)
    p2, pending = check_p2_tests_exist(rows, tests, strict=strict)
    problems += p2
    problems += check_every_test_covered(rows, tests)
    problems += check_quotes(rows, draft_text())
    problems += check_pins()
    problems += check_docstrings(rows, tests)
    status = {}
    if run:
        status = run_tests([r.test for r in rows if r.test in tests])
        problems += [f"{r.loc}: {r.test} is {status[r.test]}" for r in rows
                     if r.phase == "P2" and r.test in status and status[r.test] != "green"]
    return problems, pending, status


# ---------------------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------------------

def _cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def render(rows: list, tests: dict, status: dict) -> str:
    def st(r):
        if r.test in status:
            return status[r.test]
        if r.test not in tests:
            return "pending" if not (TESTS_DIR / test_file_of(r.test)).exists() else "missing"
        return "not run"

    by_id: dict = {}
    for r in rows:
        by_id.setdefault(r.id, []).append(r)
    counts: dict = {}
    for r in rows:
        counts.setdefault(r.phase, {}).setdefault(st(r), 0)
        counts[r.phase][st(r)] += 1
    stats = sorted({s for c in counts.values() for s in c})
    out = [
        "# Sentinel v3 -- draft compliance matrix (DCM)",
        "",
        "GENERATED by `auditgame/tools/v3_dcm.py --render` from the shards in "
        "`auditgame/v3/dcm/T<nn>.csv`. Do not edit by hand: edit the shard and re-render "
        "(only T0 and T23 commit this file, plan S5).",
        "",
        f"- Draft FSE-2027-15 (07/09/2026) PDF sha256: `{DRAFT_PDF_SHA256}`",
        f"- Pinned text `docs/v3/draft-2026-09-07.txt` sha256: `{DRAFT_TXT_SHA256}`",
        f"- Shards: {len(shard_paths())}; rows: {len(rows)}; ids: {len(by_id)}",
        "- Test status is from the run this render made. `pending` = the test file is not "
        "written yet (its task has not run); only `green` closes a P2 row.",
        "",
        "| phase | " + " | ".join(stats) + " |",
        "|---|" + "---|" * len(stats),
    ]
    for ph in sorted(counts):
        out.append(f"| {ph} | " + " | ".join(str(counts[ph].get(s, 0)) for s in stats) + " |")
    out += ["", "| id | where | quote | level | c_ref | decision | module | test | phase | "
            "status | result_ref | shard |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i in sorted(by_id):
        for r in sorted(by_id[i], key=lambda r: (r.test, r.shard)):
            out.append("| " + " | ".join(_cell(x) for x in (
                r.id, r.where, r.quote, r.level, r.c_ref, r.decision, f"`{r.module}`",
                f"`{r.test}`", r.phase, st(r), r.result_ref, r.shard)) + " |")
    return "\n".join(out) + "\n"


def regenerate_text_sha() -> str | None:
    """sha256 of a fresh pdftotext of the pinned PDF, or None if pdftotext is absent."""
    exe = shutil.which("pdftotext")
    if exe is None:
        return None
    res = subprocess.run([exe, str(DRAFT_PDF), "-"], capture_output=True, check=True)
    return hashlib.sha256(res.stdout).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="the six checks, strict")
    g.add_argument("--render", action="store_true", help="write docs/v3/DCM.md")
    g.add_argument("--pending", action="store_true", help="list pending P2 rows")
    a = ap.parse_args()
    if a.pending:
        rows, _ = load()
        _, pending = check_p2_tests_exist(rows, collect_tests())
        for r in pending:
            print(f"{r.loc}  {r.id:18s} {r.test}")
        print(f"{len(pending)} pending P2 row(s)")
        return 0
    if a.check:
        problems, pending, status = check_all(strict=True)
        for p in problems:
            print(f"  x {p}")
        print(f"DCM check: {len(problems)} problem(s) "
              f"({len(pending)} pending P2 row(s) counted as problems)")
        return 1 if problems else 0
    problems, pending, status = check_all(strict=False)
    rows, _ = load()
    DCM_MD.write_text(render(rows, collect_tests(), status), encoding="utf-8")
    print(f"wrote {DCM_MD.relative_to(REPO)}: {len(rows)} rows, {len(pending)} pending")
    for p in problems:
        print(f"  x {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
