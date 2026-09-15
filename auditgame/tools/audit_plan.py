#!/usr/bin/env python3
"""
audit_plan.py -- Machine-check eval/PLAN.md against the tree it plans.

WHY THIS EXISTS.  Three review passes found three defects, and they are one family:

    -k du_lieu_that          matched nothing      -> "Ran 0 tests ... OK"
    -k 'A or TuanThuDefense' matched half         -> OK, half the contract skipped
    doc["measured_from"]     had no producer      -> red with no instruction

Each one PASSED a check I had just run. Not because the claim held, but because the
SCAN WAS NARROWER THAN THE CLAIM: a regex requiring a letter after `-k ` never saw
the quoted form; an `or` let one live pattern carry a dead one; a key search stayed
inside the test block and never asked who writes the field.

The measurement layer already has a name for a check that passes without checking:
FALSE GREEN. These are three specimens of it one level up, in the plan. The plan's
own rule is that a defect found once becomes an invariant that cannot recur, so the
scans stop being ad-hoc scripts written and thrown away, and become this.

    python3 tools/audit_plan.py

Exit 0 clean, 1 with findings. Stdlib only, like everything else in the core.
"""
from __future__ import annotations
import ast
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
PLAN = HERE.parent.parent.parent / "261-Master-Proposal-Analysis" / "eval" / "PLAN.md"
DOCS = PLAN.parent.parent

#: Bare-name imports that are stdlib, packages, or otherwise not task-produced.
IGNORE_MODULES = {
    "__future__", "annotations", "os", "sys", "re", "json", "math", "random",
    "unittest", "pathlib", "subprocess", "statistics", "inspect", "textwrap",
    "time", "urllib", "datetime", "hashlib", "argparse", "io", "copy",
    "functools", "itertools", "dataclasses", "typing", "collections",
    "contextlib", "ast", "scipy", "sklearn", "numpy", "tests", "results",
    "spikes", "data", "hidden_tests", "analysis", "docker", "requirements",
}

#: Targets that are genuinely not in this vault, each with the reason it is
#: referenced anyway.  Listed rather than skipped: a silent skip is how a dead link
#: to a document that SHOULD exist hides among the ones that should not -- the same
#: shape as attacks.PENDING, which records refusals instead of dropping them.
#: Anything NOT on this list still fails the run.
KNOWN_ABSENT = {
    "REVIEWS.md": "part of the original FSE-2027-15 paper package, never imported here",
    "PLAN.md ": "same -- the paper's own plan, distinct from eval/PLAN.md",
    "analysis_best.md": "lives in the AutoResearchClaw artifact directory, outside the vault",
    "fse-2027-15-sentinel-stackelberg-security-game-explainer.md":
        "early draft, superseded by Giai-thich-khai-niem-FSE-2027.md",
    "fse-2027-15-sentinel-decuong-nghien-cuu.md":
        "early draft, superseded by De-cuong-nghien-cuu-chi-tiet-...md",
    "Phan-tich-FSE-2027-Portfolio.md": "portfolio-level doc, a different folder",
    "Phan-tich-chi-tiet-15-de-tai-FSE-2027.md": "same",
    "Huong-dan-tai-lap-...md": "an elided name inside prose, not a link",
}

VIETNAMESE = re.compile(
    r'[àáâãèéêìíòóôõùúýăđĩũơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', re.I)


def _blocks(text: str):
    """(language, body) for every fenced block.  Fence-aware on purpose.

    The plan holds a Dockerfile whose comments start with '#' and a ```markdown
    block whose first line is '# Spike t1'. A line-based scan reads both as
    headings. That is the same narrow-scope mistake in a different costume.
    """
    out, lang, buf, inside = [], None, [], False
    for line in text.split("\n"):
        m = re.match(r'^(?:```|~~~)(\w*)', line)
        if m:
            if inside:
                out.append((lang, "\n".join(buf))); buf, inside = [], False
            else:
                lang, inside = m.group(1) or "", True
            continue
        if inside:
            buf.append(line)
    return out


def _known_test_names() -> set:
    """Class, function and MODULE names the suite already has.

    Module stems matter: `unittest -k` matches against the full test id, so
    `-k test_replay` is valid even though no class is called that.
    """
    names = set()
    for f in (HERE / "tests").rglob("*.py"):
        names.add(f.stem)
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, (ast.ClassDef, ast.FunctionDef)):
                names.add(n.name)
    return names


def check_k_patterns(text: str, findings: list) -> None:
    """Every -k token resolves to something that exists or that a task creates.

    QUOTE-AWARE, and it splits inside the quotes. The version that missed
    TuanThuDefense required a letter right after `-k `, so `-k 'A or B'` was not
    examined at all -- it did not report a doubt, it reported nothing.
    """
    known = _known_test_names()
    known |= set(re.findall(r'^\s*(?:class|def)\s+(\w+)', text, re.M))
    known |= {m.rsplit("/", 1)[-1][:-3]
              for m in re.findall(r'Create:?\s*`([^`]+\.py)`', text)}
    for m in re.finditer(r"-k\s+(?:'([^']*)'|\"([^\"]*)\"|([A-Za-z_]\w*))", text):
        raw = m.group(1) or m.group(2) or m.group(3)
        line = text[:m.start()].count("\n") + 1
        for tok in re.findall(r'[A-Za-z_]\w*', raw):
            if tok in ("or", "and", "not"):
                continue
            if not any(tok in k for k in known):
                findings.append((line, "k-pattern",
                                 f"-k {tok!r} matches no test, class or module"))


def check_vietnamese_identifiers(text: str, findings: list) -> None:
    """No Vietnamese inside code blocks: the code/comment language is English.

    Vietnamese in PROSE is correct and expected; only fenced code is checked.
    """
    for lang, body in _blocks(text):
        if lang not in ("python", "py"):
            continue
        for i, line in enumerate(body.split("\n")):
            if VIETNAMESE.search(line):
                findings.append((None, "vi-in-code", line.strip()[:70]))


def check_python_parses(text: str, findings: list) -> None:
    """Full modules parse. Indented fragments are excluded, not silently passed."""
    for lang, body in _blocks(text):
        if lang not in ("python", "py") or body.startswith((" ", "\t", "}")):
            continue
        try:
            ast.parse(body)
        except SyntaxError as e:
            findings.append((None, "syntax", f"{e.msg} (block line {e.lineno})"))


def check_orphan_keys(text: str, findings: list) -> None:
    """A key a task's test ASSERTS must be produced somewhere in that same task.

    This is the measured_from defect generalised: the test was right, the step that
    should have written the field was never updated, and an executor following the
    step exactly gets a red test with no instruction. assertNotIn is skipped --
    asserting ABSENCE is the one case where appearing once is correct.

    THREE literal forms, and the third was a blind spot of exactly the family this
    file exists to catch. The first version matched only assertIn("key", ...) and
    doc["key"], so it never saw

        for k in ("measured_at", "n_audits", ...):
            self.assertIn(k, doc["provenance"])

    which is the form Task 22 actually uses. Verified by injecting a bogus key into
    that tuple: the check reported nothing. The scan was narrower than the claim,
    again -- so it now reads the tuple too.
    """
    for chunk in re.split(r'^### Task \d+', text, flags=re.M)[1:]:
        asserted = set(re.findall(r'assertIn\(\s*"([a-z_]{3,})"', chunk))
        asserted |= set(re.findall(r'doc(?:\.get)?[\[(]\s*"([a-z_]{3,})"', chunk))
        # Only the DICT-KEY form. The loop variable has to land in a subscript --
        # assertIn(k, doc["provenance"]) -- not in a plain string.
        #
        # Task 23 checks that a rendered report CONTAINS "spent", whose producer is
        # metrics.spend_table() and lives outside the plan entirely. Treating that
        # as an orphan key would be the mirror of the bug this file chases: a scan
        # WIDER than the claim, which is just as useless because it cries wolf.
        for tup in re.findall(
                r'for \w+ in \(([^)]*)\):\s*\n\s*self\.assertIn\(\s*\w+,\s*\w+\[', chunk):
            asserted |= set(re.findall(r'"([a-z_]{3,})"', tup))
        for key in sorted(asserted):
            if chunk.count(key) < 2:
                findings.append((None, "orphan-key",
                                 f'"{key}" asserted but nothing in the task produces it'))


def check_references(findings: list, absent: set) -> None:
    """Every `path.md` in the docs resolves.

    spikes/ and results/ are exempt: the plan tells you to CREATE those, so their
    absence is the plan working, not a dead link.
    """
    md = {str(p) for p in DOCS.rglob("*.md")}
    for p in DOCS.rglob("*.md"):
        for ref in re.findall(r'`((?:\.\./)?(?:[a-z_]+/)?[A-Za-z0-9._-]+\.md)`',
                              p.read_text(encoding="utf-8")):
            if ref.startswith(("spikes/", "results/")):
                continue
            if os.path.normpath(str(p.parent / ref)) in md:
                continue
            if ref.rsplit("/", 1)[-1] in KNOWN_ABSENT:
                absent.add(ref)
                continue
            findings.append((None, "dead-ref", f"{p.name} -> {ref}"))


def check_module_order(text: str, findings: list) -> None:
    """No task imports a module a LATER task creates.

    Task 0 listed `replay` in CORE_MODULES while Task 5 creates it, so Step 0.5
    could not go green -- and it failed with ModuleNotFoundError, which a TDD cycle
    reads as "fix the error", not as a gate.
    """
    existing = {f.stem for f in HERE.rglob("*.py")}
    chunks = re.split(r'^### Task (\d+)', text, flags=re.M)[1:]
    tasks = {int(chunks[i]): chunks[i + 1] for i in range(0, len(chunks), 2)}
    produced: dict = {}
    for n, chunk in tasks.items():
        for m in (re.findall(r'Create:?\s*`[^`]*?([a-z_0-9]+)\.py`', chunk)
                  + re.findall(r'Viết `([a-z_0-9/]+)\.py`', chunk)
                  + re.findall(r'`(h[1-5]_[a-z]+)\.py`', chunk)):
            produced.setdefault(m.rsplit("/", 1)[-1], n)
    for n in sorted(tasks):
        used = set(re.findall(r'^import ([a-z_0-9]+)', tasks[n], re.M))
        used |= set(re.findall(r'^from ([a-z_0-9]+) import', tasks[n], re.M))
        for mod in sorted(used - IGNORE_MODULES - existing):
            src = produced.get(mod)
            if src is None:
                findings.append((None, "no-producer", f"Task {n} imports `{mod}`, no task creates it"))
            elif src > n:
                findings.append((None, "order", f"Task {n} imports `{mod}`, created in Task {src}"))


def main() -> int:
    if not PLAN.exists():
        print(f"plan not found: {PLAN}")
        return 2
    text = PLAN.read_text(encoding="utf-8")
    findings: list = []
    for fn in (check_k_patterns, check_vietnamese_identifiers, check_python_parses,
               check_orphan_keys, check_module_order):
        fn(text, findings)
    absent: set = set()
    check_references(findings, absent)
    if absent:
        print(f"known-absent targets referenced ({len(absent)}), each with a reason "
              f"in KNOWN_ABSENT:")
        for a in sorted(absent):
            print(f"   {a:<62} {KNOWN_ABSENT[a.rsplit('/', 1)[-1]]}")
        print()

    if not findings:
        print(f"PLAN.md clean: {len(text.splitlines())} lines, "
              f"{len(re.findall(r'^### Task ', text, re.M))} tasks, "
              f"{len(re.findall(r'- \[ \] ', text))} open steps")
        return 0
    by_kind: dict = {}
    for line, kind, msg in findings:
        by_kind.setdefault(kind, []).append((line, msg))
    for kind in sorted(by_kind):
        print(f"\n{kind}  ({len(by_kind[kind])})")
        for line, msg in by_kind[kind]:
            print(f"   {('line ' + str(line)) if line else '':>10}  {msg}")
    print(f"\n{len(findings)} findings")
    return 1


if __name__ == "__main__":
    sys.exit(main())
