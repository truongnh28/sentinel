"""v3/audit_checks.py -- the four audit checks of draft S7, doing real work on a real repo (P3).

Draft S7 "Audit actions": "Insertion audit (content and provenance check on new memory
records), retrieval audit (consistency check of retrieved records against sources),
delegation audit (contract and evidence check), commit audit (patch review, differential
testing, provenance of contributing skills).  Costs are measured, not assigned: 0.4, 0.9,
1.6 and 4.1 CPU-minutes respectively."  sentinel-v3.md S8, row "Gia audit": implement the
four checks as S7 describes, then measure; print the measured numbers even if they differ.

WHY NOT checkpoints.py.  v2's checkpoints.py is frozen (freeze.py SOURCE) and inspects the
in-RAM mock store: microseconds per call, no repository, no tests.  Its commit() says so
itself -- "DIFFERENTIAL TESTING IS NOT DONE HERE".  This module is the v3 version: every
check reads a git repository at the instance's base_commit, and the two stages S7 defines
by testing (delegation's evidence, commit's differential testing) run the tests.

THE RECORDS.  A dev task (a SWE-bench instance of the v2 corpus) is materialised into the
four records an agent working on it would leave behind (`materialise`):
    memory  a note naming the functions the fix touches, citing each source file with the
            blob id it was read from                                   -> insertion
    queue   a pending tool call "edit these hunks, then run these tests", quoting the
            pre-image lines it will edit                               -> retrieval
    skill   the fix as a reusable procedure: the patch, its CONTRACT (the signatures of
            the functions it edits) and its EVIDENCE (the FAIL_TO_PASS tests it claims to
            make pass, with the test patch that defines them)          -> delegation
    commit  the patch that lands on the branch, the test patch, and the skills of the
            workflow that contributed to it                            -> commit
Materialising is setup (blob ids are read once, from the repo) and is not timed.  No record
carries a label: the dev instances hold no poison, and nothing here reads one.

DEPTH.  v3's observation model reads depth d as d independent looks (observe.sweep_dprime:
d' sqrt(d)).  A depth-d audit of a target is therefore the check run on the d most recent
records of that target (task t, t-1, ..., t-d+1), each record one look; tools/
v3_measure_kappa.py times each look and composes depths by summing looks of the same
workflow.  Whether kappa(k, d) is linear in d (Q6) is then a measured fact, not an
assumption.

WHAT IS TIMED.  CpuClock: this process's user+sys (time.process_time) plus the user+sys of
every waited-for child (resource.RUSAGE_CHILDREN), so the git and test subprocesses count.
Preparing the checkout (git worktree at base_commit) and resetting it after a check are
setup, timed separately by the tool and excluded from kappa: an agent's workspace is
already at the commit the audit reads.

NO SIDE EFFECTS ON ANY RESULT.  A check returns findings; nothing is fed back.
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import resource
import subprocess
import time

STAGE_OF_TARGET = {"memory": "insertion", "queue": "retrieval",
                   "skill": "delegation", "commit": "commit"}

#: Imperative phrases a note should not carry (the payload shapes of v2's corpus: "use X
#: instead", "always", "ignore"); a content check flags them, it does not block.
INSTRUCTION_MARKERS = re.compile(
    r"\b(ignore (all|previous)|always (use|call|run)|instead of|deprecated|do not (run|test)"
    r"|skip (the )?tests?|curl |wget |base64|eval\(|exec\()", re.I)

_DIFF_FILE = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.M)
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@ ?(.*)$")
_DEF = re.compile(r"\b(?:def|class)\s+([A-Za-z_]\w*)")
_DJ_TEST = re.compile(r"^(\w+) \(([\w.]+)\)")
_OUTCOME = re.compile(r"^(test\w*)\b.*?(?:\.\.\. )?\b(ok|FAIL|ERROR|skipped|expected failure|"
                      r"unexpected success|XFAIL|F|E|f|X|s)\s*$")


class CpuClock:
    """user+sys of this process and of its waited-for children, in seconds."""

    @staticmethod
    def now() -> float:
        ch = resource.getrusage(resource.RUSAGE_CHILDREN)
        return time.process_time() + ch.ru_utime + ch.ru_stime


# ---------------------------------------------------------------------------------------
# git and diff helpers
# ---------------------------------------------------------------------------------------

def git(repo: str, *args, check=True, input_=None) -> bytes:
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, input=input_)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])}: {p.stderr.decode()[:200]}")
    return p.stdout


def blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def diff_files(patch: str) -> list:
    return [b for _, b in _DIFF_FILE.findall(patch or "")]


def hunks(patch: str) -> list:
    """[(path, old_start, pre_image_lines, context_def)] of a unified diff."""
    out, path, cur = [], None, None
    for line in (patch or "").splitlines():
        m = _DIFF_FILE.match(line)
        if m:
            path, cur = m.group(2), None
            continue
        h = _HUNK.match(line)
        if h and path:
            cur = [path, int(h.group(1)), [], h.group(3)]
            out.append(cur)
            continue
        if cur is not None and line[:1] in (" ", "-"):
            cur[2].append(line[1:])
    return [tuple(x) for x in out]


def is_test_path(p: str) -> bool:
    return "/tests/" in f"/{p}" or os.path.basename(p).startswith("test")


def defined_names(src: bytes) -> set:
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return set()
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def signatures(src: bytes) -> dict:
    """name -> ast.dump of its arguments, for every def in the module."""
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return {}
    return {n.name: ast.dump(n.args) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


# ---------------------------------------------------------------------------------------
# Records (setup, not timed)
# ---------------------------------------------------------------------------------------

def materialise(row: dict, repo: str) -> dict:
    """The four records a dev task leaves behind (module docstring)."""
    base, patch, tpatch = row["base_commit"], row["patch"], row["test_patch"]
    src_files = [p for p in diff_files(patch) if not is_test_path(p)] or diff_files(patch)
    sources = []
    for p in src_files:
        try:
            bid = git(repo, "rev-parse", f"{base}:{p}").decode().strip()
        except RuntimeError:
            bid = None                                   # a file the patch creates
        sources.append({"path": p, "blob": bid})
    hk = hunks(patch)
    claims = sorted({m for _, _, _, ctx in hk for m in _DEF.findall(ctx)})
    import json as _json
    f2p = _json.loads(row["FAIL_TO_PASS"]) if isinstance(row["FAIL_TO_PASS"], str) else row["FAIL_TO_PASS"]
    p2p = _json.loads(row["PASS_TO_PASS"]) if isinstance(row["PASS_TO_PASS"], str) else row["PASS_TO_PASS"]
    tfiles = diff_files(tpatch)
    memory = {"task": row["instance_id"], "base": base, "sources": sources, "claims": claims,
              "text": f"fix for {row['instance_id']}: touches {', '.join(claims) or 'module level'}"
                      f" in {', '.join(src_files)}"}
    queue = {"task": row["instance_id"], "base": base,
             "call": {"tool": "run_tests", "files": tfiles, "tests": f2p},
             "quotes": [{"path": p, "start": s, "lines": ls} for p, s, ls, _ in hk],
             "sources": sources, "test_patch": tpatch}
    skill = {"task": row["instance_id"], "base": base, "patch": patch, "contract": claims,
             "evidence": {"tests": f2p, "test_patch": tpatch}, "sources": sources}
    commit = {"task": row["instance_id"], "base": base, "patch": patch, "test_patch": tpatch,
              "test_files": tfiles, "f2p": f2p, "p2p": p2p}
    return {"memory": memory, "queue": queue, "skill": skill, "commit": commit}


# ---------------------------------------------------------------------------------------
# Test running (django: tests/runtests.py; sympy: bin/test), both at --parallel 1
# ---------------------------------------------------------------------------------------

def django_label(name: str):
    m = _DJ_TEST.match(name)
    return f"{m.group(2)}.{m.group(1)}" if m else None


def module_label(path: str, family: str):
    if family == "django":
        if not path.startswith("tests/") or not path.endswith(".py"):
            return None
        return path[len("tests/"):-3].replace("/", ".")
    return path


_SYMPY_NAMED = r"""
import importlib, sys, traceback
files, names = sys.argv[1].split(','), set(sys.argv[2].split(','))
for f in files:
    mod = importlib.import_module(f[:-3].replace('/', '.'))
    for n in sorted(names):
        fn = getattr(mod, n, None)
        if fn is None:
            continue
        try:
            fn(); print(n, 'ok')
        except Exception as e:
            print(n, 'XFAIL' if type(e).__name__ == 'XFail' else 'F')
"""


def run_tests(wt: str, py: str, family: str, targets: list, names: list = None,
              timeout: int = 1800) -> dict:
    """Run tests in the worktree; return per-test outcomes.  `names` selects tests by name."""
    env = dict(os.environ, PYTHONPATH=wt, PYTHONDONTWRITEBYTECODE="1")
    if family == "django":
        labels = [x for x in (django_label(n) for n in (names or [])) if x] if names else \
                 [x for x in (module_label(p, family) for p in targets) if x]
        if not labels:
            return {"ran": 0, "outcomes": {}, "selected": 0}
        cmd = [py, "tests/runtests.py", "--verbosity", "2", "--parallel", "1", *labels]
    else:
        files = [p for p in targets if p.endswith(".py")]
        if not files:
            return {"ran": 0, "outcomes": {}, "selected": 0}
        if names:
            # bin/test's -k takes one keyword in old sympy and several in new; calling the
            # named functions directly selects exactly them in every version.
            cmd = [py, "-c", _SYMPY_NAMED, ",".join(files), ",".join(names)]
        else:
            cmd = [py, "bin/test", "-C", "--verbose", *files]
    try:
        p = subprocess.run(cmd, cwd=wt, env=env, capture_output=True, timeout=timeout)
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        timed_out = False
    except subprocess.TimeoutExpired as e:
        out = ((e.stdout or b"") + (e.stderr or b"")).decode("utf-8", "replace")
        timed_out = True
    outcomes = {}
    for line in out.splitlines():
        m = _OUTCOME.match(line.strip())
        if m:
            outcomes[m.group(1) + line.strip()[len(m.group(1)):].split(" ...")[0][:120]] = m.group(2)
    return {"ran": len(outcomes), "outcomes": outcomes, "timed_out": timed_out,
            "selected": len(names) if names else len(targets)}


def apply(wt: str, patch: str, check_only=False) -> bool:
    args = ["apply", "--whitespace=nowarn"] + (["--check"] if check_only else [])
    p = subprocess.run(["git", "-C", wt, *args], input=patch.encode(), capture_output=True)
    return p.returncode == 0


# ---------------------------------------------------------------------------------------
# The four checks.  One call = one look = one record.
# ---------------------------------------------------------------------------------------

def insertion(rec: dict, repo: str) -> dict:
    """Content + provenance of a new memory record: every cited source resolves at base and
    hashes to the cited blob; every function the note claims is defined in a cited source;
    the text carries no instruction-shaped content."""
    f = {"sources": 0, "blob_mismatch": 0, "unresolved": 0, "claims": len(rec["claims"]),
         "claims_undefined": 0, "markers": 0}
    defined = set()
    for s in rec["sources"]:
        f["sources"] += 1
        if not s["blob"]:
            f["unresolved"] += 1
            continue
        try:
            data = git(repo, "cat-file", "blob", f"{rec['base']}:{s['path']}")
        except RuntimeError:
            f["unresolved"] += 1
            continue
        if blob_id(data) != s["blob"]:
            f["blob_mismatch"] += 1
        if s["path"].endswith(".py"):
            defined |= defined_names(data)
    f["claims_undefined"] = sum(1 for c in rec["claims"] if c not in defined)
    f["markers"] = len(INSTRUCTION_MARKERS.findall(rec["text"]))
    return f


def retrieval(rec: dict, repo: str) -> dict:
    """Consistency of a retrieved queue record against its sources: every quoted pre-image
    still occurs verbatim in the source at base, the cited blobs still match, and every
    test the call names exists in the named test files (at base, or added by the test
    patch the call carries)."""
    f = {"quotes": 0, "quote_missing": 0, "blob_mismatch": 0, "tests": 0, "test_missing": 0}
    cache = {}

    def read(path):
        if path not in cache:
            try:
                cache[path] = git(repo, "cat-file", "blob", f"{rec['base']}:{path}")
            except RuntimeError:
                cache[path] = b""
        return cache[path]

    for s in rec["sources"]:
        if s["blob"] and blob_id(read(s["path"])) != s["blob"]:
            f["blob_mismatch"] += 1
    for q in rec["quotes"]:
        f["quotes"] += 1
        text = read(q["path"]).decode("utf-8", "replace").splitlines()
        want = q["lines"]
        lo = max(0, q["start"] - 1)
        if text[lo:lo + len(want)] != want:
            # the record may be stale by a few lines; search the whole file
            n = len(want)
            if not any(text[i:i + n] == want for i in range(0, max(0, len(text) - n + 1))):
                f["quote_missing"] += 1
    added = "\n".join(l[1:] for l in rec["test_patch"].splitlines() if l.startswith("+"))
    corpus = added + "\n" + "\n".join(read(p).decode("utf-8", "replace")
                                      for p in rec["call"]["files"])
    for name in rec["call"]["tests"]:
        f["tests"] += 1
        m = _DJ_TEST.match(name)
        if m or re.fullmatch(r"\w+", name):
            key = m.group(1) if m else name
            found = re.search(r"\bdef\s+" + re.escape(key) + r"\b", corpus)
        else:                                   # django names some tests by docstring
            found = name.strip() in corpus
        if not found:
            f["test_missing"] += 1
    return f


def delegation(rec: dict, wt: str, py: str, family: str) -> dict:
    """Contract + evidence of a delegated skill.  Contract: apply the skill's patch and
    compare, before and after, the signatures of the functions it claims to edit (a skill
    that silently changes an interface breaks its contract).  Evidence: apply the test
    patch and run the FAIL_TO_PASS tests it cites; they must pass."""
    f = {"applies": False, "contract_changed": 0, "evidence_tests": len(rec["evidence"]["tests"]),
         "evidence_ran": 0, "evidence_failed": 0}
    files = [s["path"] for s in rec["sources"] if s["path"].endswith(".py")]
    pre = {p: signatures(_read(wt, p)) for p in files}
    f["applies"] = apply(wt, rec["patch"]) and apply(wt, rec["evidence"]["test_patch"])
    if not f["applies"]:
        return f
    post = {p: signatures(_read(wt, p)) for p in files}
    for name in rec["contract"]:
        a = [pre[p][name] for p in files if name in pre[p]]
        b = [post[p][name] for p in files if name in post[p]]
        if a and b and a != b:
            f["contract_changed"] += 1
    names = rec["evidence"]["tests"]
    targets = [p for p in diff_files(rec["evidence"]["test_patch"]) if p.endswith(".py")]
    if family == "sympy":
        names = [n.split()[0] for n in names]
    else:
        names = [n if _DJ_TEST.match(n) else (_by_docstring(wt, targets, n) or n) for n in names]
    r = run_tests(wt, py, family, targets, names=names)
    f["evidence_ran"] = r["ran"]
    f["evidence_failed"] = sum(1 for v in r["outcomes"].values() if v not in ("ok", "."))
    f["timed_out"] = r.get("timed_out", False)
    return f


def commit(rec: dict, wt: str, py: str, family: str, repo: str, lineage: list) -> dict:
    """Patch review + differential testing + provenance of contributing skills.
    Review: the patch applies; every changed Python file still compiles; diff size.
    Differential testing: with the test patch applied, run the touched test modules on
    the pre-patch tree and on the post-patch tree and compare per-test outcomes.
    Provenance: which cached skill the agent drew on is not recorded, so every skill the
    workflow cached before this task (`lineage`) counts as contributing and has its cited
    blobs re-hashed at its own base (the provenance half of `insertion`)."""
    f = {"applies": False, "compile_errors": 0, "added": 0, "removed": 0, "ran_pre": 0,
         "ran_post": 0, "flipped": 0, "lineage": 0, "lineage_mismatch": 0}
    for line in rec["patch"].splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            f["added"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            f["removed"] += 1
    if not apply(wt, rec["patch"], check_only=True) or not apply(wt, rec["test_patch"]):
        return f
    targets = rec["test_files"]
    pre = run_tests(wt, py, family, targets)
    apply(wt, rec["patch"])
    f["applies"] = True
    for p in diff_files(rec["patch"]):
        if p.endswith(".py") and os.path.exists(os.path.join(wt, p)):
            try:
                compile(_read(wt, p), p, "exec")
            except SyntaxError:
                f["compile_errors"] += 1
    post = run_tests(wt, py, family, targets)
    f["ran_pre"], f["ran_post"] = pre["ran"], post["ran"]
    f["flipped"] = sum(1 for k, v in post["outcomes"].items() if pre["outcomes"].get(k) != v)
    f["timed_out"] = pre.get("timed_out", False) or post.get("timed_out", False)
    for sk in lineage:
        for s in sk["sources"]:
            if not s["blob"]:
                continue
            f["lineage"] += 1
            try:
                data = git(repo, "cat-file", "blob", f"{sk['base']}:{s['path']}")
            except RuntimeError:
                f["lineage_mismatch"] += 1
                continue
            if blob_id(data) != s["blob"]:
                f["lineage_mismatch"] += 1
    return f


def _by_docstring(wt: str, files: list, doc: str):
    """A django test named by its docstring's first line -> "test_x (module.Class)"."""
    for p in files:
        lines = _read(wt, p).decode("utf-8", "replace").splitlines()
        for i, line in enumerate(lines):
            if doc.strip() not in line or i == 0:
                continue
            for j in range(i - 1, max(-1, i - 4), -1):
                m = re.match(r"\s*(?:async\s+)?def\s+(test\w*)", lines[j])
                if m:
                    cls = next((re.match(r"class\s+(\w+)", lines[k]).group(1)
                                for k in range(j, -1, -1) if re.match(r"class\s+\w+", lines[k])), None)
                    lab = module_label(p, "django")
                    if cls and lab:
                        return f"{m.group(1)} ({lab}.{cls})"
    return None


def _read(wt: str, path: str) -> bytes:
    try:
        with open(os.path.join(wt, path), "rb") as fh:
            return fh.read()
    except OSError:
        return b""
