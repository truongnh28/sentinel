#!/usr/bin/env python3
"""measure_delta_swebench.py -- the real trigger delay Delta, in TASK units.

Spec: docs/design/plans/2026-09-22-W1-W10-tham-so.md Task 5 (W5);
docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 3.7.

Delta is the number of tasks between the upstream change that introduced a
problem and the downstream task where it surfaces.  The crossover the thesis
predicts sits at Delta ~ 2, and that prediction is only interesting if real
workflows have Delta on the same scale -- so Delta has to be measured on the
repositories the benchmark is built from, not assumed.

THE OPERATIONALISATION, AND WHY THIS ONE.
For each SWE-bench instance:
  downstream  the instance itself: an issue whose fix edits a known set of files.
  upstream    the last commit BEFORE the instance's base_commit that touched any
              of those same files -- an SZZ-style blame on the files the fix had
              to change.
  Delta       how many instances of that repository sit between the upstream
              commit's date and the instance's created_at.  That is the distance
              in TASK units, which is what the Delta grid is indexed by.

WHY SZZ AND NOT `git bisect`.  Bisect needs an environment that can run the
tests at every commit, which means one Docker image per repository per era.  The
plan rules that out for this sprint, so the upstream commit is found by blame on
the touched files instead, and the weaker inference is declared here rather than
implied.

WHAT THIS DOES NOT ESTABLISH.  Co-change and blame give evolutionary
correlation, not causation: the last commit to touch a file is not necessarily
the commit that broke it.  The number below is the scale of the delay, not a
claim about which commit is at fault.

    python3 tools/measure_delta_swebench.py --per-repo 25 > spikes/delta-swebench.json
"""
from __future__ import annotations
import argparse
import collections
import datetime
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


def touched_files(patch: str) -> list:
    """Source files a gold patch edits, from its own diff headers."""
    return _DIFF.findall(patch or "")


def _git(repo: pathlib.Path, *args) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args],
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def _upstream_commit(repo: pathlib.Path, base_commit: str, files: list):
    """The last commit before `base_commit` touching any of `files`: (sha, date).

    Two units come out of this, and they answer different questions:
      TASK distance   how many instances of the repo sit in between -- the unit
                      the Delta grid uses, but also a property of how densely
                      the benchmark sampled this repo.
      COMMIT distance how many commits sit in between -- independent of the
                      benchmark's sampling, and the number to quote when asking
                      whether real delays are on the scale of the crossover.
    """
    best = None
    for f in files[:5]:                      # five files is enough to date the area
        line = _git(repo, "log", "-1", "--format=%H %cI", f"{base_commit}^", "--", f)
        if not line:
            continue
        sha, iso = line.split(" ", 1)
        when = datetime.datetime.fromisoformat(iso)
        if best is None or when > best[1]:
            best = (sha, when)
    return best


def measure(per_repo: int = 25) -> dict:
    rows_by_repo: dict = collections.defaultdict(list)
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows_by_repo[row["repo"]].append(row)
    for rows in rows_by_repo.values():
        rows.sort(key=lambda r: r["created_at"])

    per_repo_out: dict = {}
    all_deltas: list = []
    for repo, rows in sorted(rows_by_repo.items()):
        path = WORKSPACE / repo
        if not (path / ".git").exists():
            continue
        created = [datetime.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                   for r in rows]
        deltas = []
        commit_deltas = []
        for idx, row in enumerate(rows[:per_repo]):
            files = touched_files(row.get("patch", ""))
            if not files:
                continue
            up = _upstream_commit(path, row["base_commit"], files)
            if up is None:
                continue
            sha, when = up
            n_commits = _git(path, "rev-list", "--count", f"{sha}..{row['base_commit']}")
            if n_commits.isdigit():
                commit_deltas.append(int(n_commits))
            # Delta in TASK units: instances of this repo between the upstream
            # commit and this instance.  Zero means the area was last touched
            # after the previous instance -- the same task window.
            d = sum(1 for c in created[:idx] if c > when)
            deltas.append(d)
        if deltas:
            per_repo_out[repo] = {
                "n": len(deltas),
                "median": statistics.median(deltas),
                "mean": statistics.fmean(deltas),
                "p75": statistics.quantiles(deltas, n=4)[2] if len(deltas) >= 4 else None,
                "max": max(deltas),
                "share_ge_2": sum(1 for d in deltas if d >= 2) / len(deltas),
                "distribution": sorted(deltas),
                "commit_distance": ({
                    "median": statistics.median(commit_deltas),
                    "p75": (statistics.quantiles(commit_deltas, n=4)[2]
                            if len(commit_deltas) >= 4 else None),
                    "max": max(commit_deltas), "n": len(commit_deltas),
                } if commit_deltas else None),
            }
            all_deltas.extend(deltas)

    pooled = {
        "n": len(all_deltas),
        "median": statistics.median(all_deltas) if all_deltas else None,
        "p75": statistics.quantiles(all_deltas, n=4)[2] if len(all_deltas) >= 4 else None,
        "share_ge_2": (sum(1 for d in all_deltas if d >= 2) / len(all_deltas)
                       if all_deltas else None),
    } if all_deltas else None

    return {
        "per_repo": per_repo_out,
        "pooled_do_not_quote_alone": pooled,
        "reading": ("Delta is reported PER REPOSITORY; the pooled row is there for "
                    "orientation only, because SWE-bench Verified is dominated by "
                    "django (231/500) and a pooled median is django's median."),
        "provenance": {
            "downstream": "SWE-bench Verified instance (issue + gold patch)",
            "upstream": "last commit before base_commit touching a file the gold "
                        "patch edits (SZZ-style blame, first 5 files)",
            "delta_unit": "instances of the same repository in between",
            "why_not_bisect": "bisect needs a runnable test environment at every "
                              "commit, i.e. one Docker image per repo per era",
            "per_repo_limit": per_repo,
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-repo", type=int, default=25)
    a = ap.parse_args()
    print(json.dumps(measure(a.per_repo), indent=2, ensure_ascii=False))
