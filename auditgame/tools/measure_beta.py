#!/usr/bin/env python3
"""measure_beta.py -- benign drift rate beta_k, counted on real repository history.

Spec: docs/design/plans/2026-09-22-W1-W10-tham-so.md Task 4 (W3);
docs/AuditGame-SE_Parameter_Estimation_Report.md section 5.1.

beta_k is the probability that carrier k changes for ORDINARY reasons during one
task.  It is the competing cause: with beta = 0 every alarm is evidence of
poisoning and "quarantine everything" is optimal, so lambda_Q would be pricing a
risk the world never produces.

THE MAPPING RULE IS A MODELLING DECISION, DECLARED HERE BEFORE ANY COUNTING.
Carriers live OUTSIDE the repository, so no commit literally "touches memory".
What follows is a stated analogy, not a measurement, and the script therefore
runs it twice -- rule A below and rule B, its alternative -- and reports both.
If the qualitative conclusion differs between them, beta is not identified by
this procedure and has to move to M2 (swept), which the report must say.

  RULE A (primary)
    memory  docs and notes a human reads:  *.md, *.rst, *.txt, docs/**, CHANGELOG*
    skill   reusable code:                 utils/, helpers/, _base.py, lib/, common/
    queue   tooling and entry points:      setup.py, setup.cfg, tox.ini, Makefile,
                                           .github/**, scripts/, conftest.py
    branch  every commit -- a branch accumulates everything, so beta_branch = 1.0
            BY CONSTRUCTION.  Derived, not measured; reported as such.

  RULE B (alternative, for the sensitivity check)
    memory  documentation only:            docs/**, *.rst
    skill   any file imported by >= 2 other files in the same commit's tree is
            approximated by: any *.py under a package root that is not a test
    queue   CI configuration only:         .github/**, tox.ini
    branch  every commit

THE WINDOW IS THE TASK, NOT THE CALENDAR.  A workflow's tasks are consecutive
SWE-bench instances ordered by created_at, so the commits that fall between two
tasks are the commits between their base_commit values.  That interval is what
one task occupies in the repository's own history, which is the unit beta is
defined on.

REPORTED PER REPOSITORY, NEVER POOLED.  SWE-bench is dominated by django
(231/500 Verified); a pooled number would be django's number wearing everyone
else's name.

    python3 tools/measure_beta.py --repos 10 --windows 40 > spikes/beta-k.json
"""
from __future__ import annotations
import argparse
import datetime
import fnmatch
import json
import pathlib
import statistics
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from core import CARRIERS   # noqa: E402

WORKSPACE = pathlib.Path(__file__).resolve().parent.parent / "workspace"
DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "swebench_verified.jsonl"

RULE_A = {
    "memory": ["*.md", "*.rst", "*.txt", "docs/*", "*/docs/*", "CHANGELOG*", "*/CHANGELOG*"],
    "skill": ["*/utils/*", "*/helpers/*", "*_base.py", "*/lib/*", "*/common/*",
              "*/util.py", "*/utils.py"],
    "queue": ["setup.py", "setup.cfg", "tox.ini", "Makefile", ".github/*",
              "*/.github/*", "scripts/*", "conftest.py", "*/conftest.py"],
}
RULE_B = {
    "memory": ["docs/*", "*/docs/*", "*.rst"],
    "skill": ["*.py"],
    "queue": [".github/*", "*/.github/*", "tox.ini"],
}


def _matches(path: str, patterns) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def _commits_between(repo: pathlib.Path, older: str, newer: str):
    """Commits strictly after `older` up to `newer`, with the files they touch."""
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--name-only", "--pretty=format:%H",
         f"{older}..{newer}"],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None
    commits, files = [], []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            if files or commits:
                commits.append(files)
            files = []
        else:
            files.append(line)
    if files:
        commits.append(files)
    return commits


def _instances_by_repo() -> dict:
    by_repo: dict = {}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        by_repo.setdefault(row["repo"], []).append(row)
    for rows in by_repo.values():
        rows.sort(key=lambda r: r["created_at"])
    return by_repo


def measure(max_windows: int = 40, rule=RULE_A, rule_name: str = "A") -> dict:
    by_repo = _instances_by_repo()
    per_repo: dict = {}
    for repo, rows in sorted(by_repo.items()):
        path = WORKSPACE / repo
        if not (path / ".git").exists():
            continue
        counts = {c: 0 for c in CARRIERS}
        total_commits = 0
        windows = 0
        for older, newer in zip(rows, rows[1:]):
            if windows >= max_windows:
                break
            commits = _commits_between(path, older["base_commit"], newer["base_commit"])
            if not commits:
                continue
            windows += 1
            for files in commits:
                total_commits += 1
                counts["branch"] += 1          # by construction: every commit
                for carrier in ("memory", "skill", "queue"):
                    if any(_matches(f, rule[carrier]) for f in files):
                        counts[carrier] += 1
        if total_commits:
            per_repo[repo] = {
                "beta": {c: counts[c] / total_commits for c in CARRIERS},
                "commits": total_commits, "windows": windows,
                "commits_per_window": total_commits / windows,
            }

    def across(carrier: str):
        vals = [v["beta"][carrier] for v in per_repo.values()]
        return {"median": statistics.median(vals), "min": min(vals),
                "max": max(vals), "n_repos": len(vals)} if vals else None

    return {
        "rule": rule_name,
        "beta_across_repos": {c: across(c) for c in CARRIERS},
        "per_repo": per_repo,
        "provenance": {
            "window": "commits between the base_commit of two consecutive "
                      "SWE-bench Verified instances of the same repo",
            "mapping_rule": rule,
            "branch_note": "beta_branch = 1.0 by construction, not measured",
            "max_windows_per_repo": max_windows,
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--windows", type=int, default=40,
                    help="max task windows per repository")
    a = ap.parse_args()
    primary = measure(a.windows, RULE_A, "A")
    alternative = measure(a.windows, RULE_B, "B")
    same_order = (sorted(primary["beta_across_repos"], key=lambda c: -primary["beta_across_repos"][c]["median"])
                  == sorted(alternative["beta_across_repos"], key=lambda c: -alternative["beta_across_repos"][c]["median"]))
    print(json.dumps({
        "primary_rule_A": primary,
        "alternative_rule_B": alternative,
        "carrier_order_agrees_between_rules": same_order,
        "reading": ("beta is identified by this procedure only if the two rules "
                    "agree on the qualitative picture; if they disagree, beta "
                    "moves to M2 and must be swept"),
    }, indent=2, ensure_ascii=False))
