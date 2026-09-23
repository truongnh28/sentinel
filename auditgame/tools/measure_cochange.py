#!/usr/bin/env python3
"""measure_cochange.py -- evolutionary coupling, filtered by the import graph.

Spec: docs/design/plans/2026-09-22-W1-W10-tham-so.md Task 5 (W5);
docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 3.7.

WHAT THIS ADDS TO measure_delta_swebench.py.  That script attributes a fix to the
last commit that touched THE SAME files -- self-coupling, which needs no coupling
table.  Stage 3.7 asks for the harder question: modules A and B that change
together, and the delay between A changing and B breaking.  Two quantities:

    support(A, B)      number of commits touching both modules
    confidence(A->B)   support(A, B) / (commits touching A)

CO-CHANGE ALONE IS NOT CAUSATION, AND THE IMPORT GRAPH IS THE FILTER.  Two
modules edited in the same commit may simply belong to one feature, one release
sweep or one reformat.  A pair is kept only when the source actually connects
them: some file of one module imports the other.  The script reports the counts
before and after that filter, because the SIZE of the drop is itself the finding
-- it says how much of the "coupling" in a repository is bookkeeping.

DELTA UNDER FILTERED ATTRIBUTION.  For each SWE-bench instance (downstream
modules B), the upstream candidate is the most recent commit before base_commit
touching a module A with confidence(A->B) >= MIN_CONFIDENCE and an import edge to
B.  Delta is then the distance to that commit, in the same two units as
measure_delta_swebench.py: instances of the repo, and commits.

    python3 tools/measure_cochange.py --per-repo 15 --commits 3000 > spikes/cochange.json
"""
from __future__ import annotations
import argparse
import collections
import datetime
import itertools
import json
import pathlib
import re
import statistics
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

WORKSPACE = pathlib.Path(__file__).resolve().parent.parent / "workspace"
DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "swebench_verified.jsonl"

_DIFF = re.compile(r"^diff --git a/(\S+) b/", re.MULTILINE)

#: A module is the first two path components: "django/db", "sympy/core".  File
#: level would make the pair space enormous and the supports too thin to read.
MODULE_DEPTH = 2

#: Commits touching more modules than this are release sweeps, reformats or
#: merges: they couple everything with everything and would swamp the table.
MAX_MODULES_PER_COMMIT = 8

#: A pair is "coupled" from this confidence up.  Declared before counting.
MIN_CONFIDENCE = 0.10
MIN_SUPPORT = 5


def module_of(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[:MODULE_DEPTH]) if len(parts) >= MODULE_DEPTH else parts[0]


def _git(repo: pathlib.Path, *args, timeout=120) -> str:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ""
    return out.stdout if out.returncode == 0 else ""


def commit_module_sets(repo: pathlib.Path, max_commits: int):
    """[(sha, {modules})] for the most recent `max_commits` commits."""
    raw = _git(repo, "log", f"-{max_commits}", "--name-only", "--pretty=format:%H")
    commits, sha, files = [], None, []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            if sha is not None:
                commits.append((sha, {module_of(f) for f in files}))
            sha, files = line, []
        else:
            files.append(line)
    if sha is not None:
        commits.append((sha, {module_of(f) for f in files}))
    return commits


def cochange_table(commits) -> tuple:
    """(support, touches) -- pair supports and per-module commit counts."""
    support: dict = collections.Counter()
    touches: dict = collections.Counter()
    for _sha, mods in commits:
        if not mods or len(mods) > MAX_MODULES_PER_COMMIT:
            continue
        for m in mods:
            touches[m] += 1
        for a, b in itertools.combinations(sorted(mods), 2):
            support[(a, b)] += 1
    return support, touches


def has_import_edge(repo: pathlib.Path, a: str, b: str) -> bool:
    """Does either module's source import the other?

    Approximate on purpose: it greps the import statements of one module's tree
    for the other's dotted name.  A false edge keeps a pair the filter should
    have dropped; a missed edge drops a real one.  Both directions are tried, so
    the usual case -- B importing the utility module A -- is caught.
    """
    for src, target in ((a, b), (b, a)):
        dotted = target.replace("/", ".")
        # POSIX ERE, not PCRE: `git grep -E` does not know \s or \b, and a
        # pattern using them matches nothing while looking like it works -- which
        # is exactly how this filter first reported a 0% survival rate.
        pattern = (r"^[[:space:]]*(from|import)[[:space:]]+[A-Za-z_.]*"
                   + dotted.replace(".", r"\."))
        # ONLY PYTHON SOURCE.  Documentation quotes imports in its examples, so
        # searching a whole tree makes every code module look coupled to the
        # release notes: django/db "imports" docs/releases at support 122.  The
        # pathspec keeps the edge a statement about source.
        if _git(repo, "grep", "-l", "-E", pattern,
                "--", f":(glob){src}/**/*.py").strip():
            return True
    return False


def filtered_delta(repo_path, rows, per_repo, coupled_pairs) -> dict:
    """Delta when the upstream commit must touch a COUPLED, IMPORT-LINKED module.

    measure_delta_swebench.py attributes a fix to the last commit touching the
    same files.  Here the candidate upstream module has to be a DIFFERENT module
    that (a) co-changes with the downstream module above the declared threshold
    and (b) is connected to it by an import edge.  Both units are reported, and
    instances with no surviving partner are counted rather than dropped quietly.
    """
    partners: dict = collections.defaultdict(set)
    for a, b in coupled_pairs:
        partners[a].add(b)
        partners[b].add(a)

    created = [datetime.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
               for r in rows]
    task_deltas, commit_deltas, no_partner = [], [], 0
    for idx, row in enumerate(rows[:per_repo]):
        downstream = {module_of(f) for f in _DIFF.findall(row.get("patch", ""))}
        cands = {m for d in downstream for m in partners.get(d, ())} - downstream
        if not cands:
            no_partner += 1
            continue
        best = None
        for m in sorted(cands)[:5]:
            line = _git(repo_path, "log", "-1", "--format=%H %cI",
                        f"{row['base_commit']}^", "--", m)
            if not line.strip():
                continue
            sha, iso = line.split()[0], line.split()[1]
            when = datetime.datetime.fromisoformat(iso)
            if best is None or when > best[1]:
                best = (sha, when)
        if best is None:
            no_partner += 1
            continue
        sha, when = best
        n = _git(repo_path, "rev-list", "--count", f"{sha}..{row['base_commit']}").strip()
        if n.isdigit():
            commit_deltas.append(int(n))
        task_deltas.append(sum(1 for c in created[:idx] if c > when))

    if not task_deltas:
        return {"n": 0, "instances_without_coupled_partner": no_partner}
    return {
        "n": len(task_deltas),
        "instances_without_coupled_partner": no_partner,
        "task": {"median": statistics.median(task_deltas),
                 "share_ge_2": sum(1 for d in task_deltas if d >= 2) / len(task_deltas),
                 "max": max(task_deltas)},
        "commit": ({"median": statistics.median(commit_deltas),
                    "max": max(commit_deltas)} if commit_deltas else None),
    }


def measure(per_repo: int, max_commits: int) -> dict:
    rows_by_repo: dict = collections.defaultdict(list)
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows_by_repo[row["repo"]].append(row)
    for rows in rows_by_repo.values():
        rows.sort(key=lambda r: r["created_at"])

    out: dict = {}
    for repo, rows in sorted(rows_by_repo.items()):
        path = WORKSPACE / repo
        if not (path / ".git").exists():
            continue
        commits = commit_module_sets(path, max_commits)
        support, touches = cochange_table(commits)

        coupled = [(a, b, s, s / touches[a], s / touches[b])
                   for (a, b), s in support.items()
                   if s >= MIN_SUPPORT
                   and max(s / touches[a], s / touches[b]) >= MIN_CONFIDENCE]
        coupled.sort(key=lambda r: -r[2])

        checked = coupled[:25]          # import check is the expensive part
        surviving = [r for r in checked if has_import_edge(path, r[0], r[1])]

        out[repo] = {
            "commits_scanned": len(commits),
            "modules": len(touches),
            "pairs_with_support": len(support),
            "pairs_coupled": len(coupled),
            "pairs_checked_against_import_graph": len(checked),
            "pairs_surviving_import_filter": len(surviving),
            "survival_rate": (len(surviving) / len(checked)) if checked else None,
            "delta_under_filtered_attribution": filtered_delta(
                path, rows, per_repo, [(r[0], r[1]) for r in surviving]),
            "top_pairs": [
                {"a": a, "b": b, "support": s,
                 "confidence_a_to_b": round(ca, 3), "confidence_b_to_a": round(cb, 3),
                 "import_edge": (a, b, s, ca, cb) in
                                [(x[0], x[1], x[2], x[3], x[4]) for x in surviving]}
                for a, b, s, ca, cb in checked[:8]
            ],
        }
    return {
        "per_repo": out,
        "thresholds": {"min_support": MIN_SUPPORT, "min_confidence": MIN_CONFIDENCE,
                       "module_depth": MODULE_DEPTH,
                       "max_modules_per_commit": MAX_MODULES_PER_COMMIT},
        "reading": ("The survival rate is the finding: it says what share of the "
                    "strongest evolutionary coupling in a repository is backed by "
                    "an actual import path, and what share is bookkeeping."),
        "provenance": {
            "support": "commits touching both modules, over the most recent "
                       f"{max_commits} commits",
            "confidence": "support / commits touching the module",
            "import_edge": "grep of import statements in one module's tree for "
                           "the other's dotted name, both directions",
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-repo", type=int, default=15)
    ap.add_argument("--commits", type=int, default=3000)
    a = ap.parse_args()
    print(json.dumps(measure(a.per_repo, a.commits), indent=2, ensure_ascii=False))
