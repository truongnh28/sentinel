"""
tools/measure_delta.py -- Empirical measurement of causal delay Delta from git history.

Concept:
  Delta is the causal propagation delay between an upstream instruction/state modification
  (e.g., plan, spec, policy, guideline) and the downstream artifact modification
  (e.g., code implementation, tests, experimental pipelines).

Inputs:
  - Git repository path
  - List/glob of instruction/state paths (e.g. docs/superpowers/plans/**, docs/superpowers/specs/**, eval/PLAN*.md)
  - List/glob of implementation/code paths (e.g. HCMUT/code/**, src/**)

Outputs:
  - Distribution of Delta (commits/tasks between state change and affected code change)
  - Summary percentiles (min, p25, median/p50, p75, p90, max)
  - Full trace of (state_commit -> first_downstream_code_commit) pairs
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import subprocess
import sys
from pathlib import Path


DEFAULT_STATE_PATTERNS = [
    "docs/superpowers/plans/*",
    "docs/superpowers/specs/*",
    "eval/PLAN*.md",
    "HCMUT/261-Master-Proposal-Analysis/eval/PLAN*.md",
    "*.agents/*",
    "*.superpowers/*",
    "CLAUDE.md",
    "GEMINI.md",
    "AGENTS.md",
]

DEFAULT_CODE_PATTERNS = [
    "HCMUT/code/*",
    "auditgame/*",
    "src/*",
    "*.py",
    "*.ts",
    "*.js",
]


def run_git(args: list[str], cwd: str) -> str:
    res = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return res.stdout.strip()


def matches_any(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path.split("/")[-1], pat):
            return True
        # also match path prefix if pattern ends in /*
        if pat.endswith("/*"):
            prefix = pat[:-2]
            if path.startswith(prefix):
                return True
    return False


def get_commit_history(repo_root: str, max_commits: int = 500) -> list[dict]:
    # git log in reverse chronological order: hash, subject, files
    raw = run_git(["log", f"-n{max_commits}", "--pretty=format:COMMIT:%H|%s", "--name-only"], cwd=repo_root)
    commits = []
    current = None
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("COMMIT:"):
            parts = line[7:].split("|", 1)
            h = parts[0]
            subj = parts[1] if len(parts) > 1 else ""
            current = {"hash": h, "subject": subj, "files": []}
            commits.append(current)
        elif current is not None:
            current["files"].append(line)
    # Return chronological order (oldest first)
    commits.reverse()
    return commits


def measure_deltas(
    repo_root: str,
    state_patterns: list[str] = DEFAULT_STATE_PATTERNS,
    code_patterns: list[str] = DEFAULT_CODE_PATTERNS,
    max_commits: int = 500,
) -> dict:
    commits = get_commit_history(repo_root, max_commits)
    n = len(commits)

    traces = []
    deltas = []

    for i, c in enumerate(commits):
        has_state = any(matches_any(f, state_patterns) for f in c["files"])
        has_code = any(matches_any(f, code_patterns) for f in c["files"])

        # If this commit modified state/instructions
        if has_state:
            # If it ALSO modified code in the exact same commit, delta = 0
            if has_code:
                traces.append({
                    "state_hash": c["hash"][:7],
                    "state_subject": c["subject"],
                    "code_hash": c["hash"][:7],
                    "code_subject": c["subject"],
                    "delta": 0,
                    "same_commit": True,
                })
                deltas.append(0)
            else:
                # Look forward for the first subsequent commit that modified code
                found = False
                for j in range(i + 1, n):
                    next_c = commits[j]
                    next_has_code = any(matches_any(f, code_patterns) for f in next_c["files"])
                    if next_has_code:
                        delta = j - i
                        traces.append({
                            "state_hash": c["hash"][:7],
                            "state_subject": c["subject"],
                            "code_hash": next_c["hash"][:7],
                            "code_subject": next_c["subject"],
                            "delta": delta,
                            "same_commit": False,
                        })
                        deltas.append(delta)
                        found = True
                        break
                if not found:
                    # Unfinished propagation / still pending downstream
                    traces.append({
                        "state_hash": c["hash"][:7],
                        "state_subject": c["subject"],
                        "code_hash": None,
                        "code_subject": "PENDING (no downstream commit yet)",
                        "delta": None,
                        "same_commit": False,
                    })

    # Calculate percentiles
    valid_deltas = [d for d in deltas if d is not None]
    valid_deltas.sort()

    def percentile(p):
        if not valid_deltas:
            return float("nan")
        k = (len(valid_deltas) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return valid_deltas[int(k)]
        return valid_deltas[f] * (c - k) + valid_deltas[c] * (k - f)

    stats = {
        "count": len(valid_deltas),
        "min": valid_deltas[0] if valid_deltas else None,
        "p25": percentile(25),
        "median_p50": percentile(50),
        "p75": percentile(75),
        "p90": percentile(90),
        "max": valid_deltas[-1] if valid_deltas else None,
        "mean": sum(valid_deltas) / len(valid_deltas) if valid_deltas else None,
    }

    return {
        "stats": stats,
        "distribution": valid_deltas,
        "traces": traces,
    }


def main():
    parser = argparse.ArgumentParser(description="Measure Causal Propagation Delay Delta from Git Log")
    parser.add_argument("--repo", type=str, default=".", help="Path to git repository root")
    parser.add_argument("--max-commits", type=int, default=500, help="Max commits to analyze")
    parser.add_argument("--json", type=str, help="Output JSON path")
    args = parser.parse_args()

    repo_path = str(Path(args.repo).resolve())
    print(f"Measuring empirical causal delay Delta on repository: {repo_path}")
    res = measure_deltas(repo_path, max_commits=args.max_commits)

    stats = res["stats"]
    print("\n=======================================================")
    print("Empirical Delta Distribution (Unit: Commits / Tasks):")
    print(f"  Total state modifications measured: {stats['count']}")
    print(f"  Min Delta:    {stats['min']}")
    print(f"  p25:          {stats['p25']:.1f}")
    print(f"  Median (p50): {stats['median_p50']:.1f}")
    print(f"  p75:          {stats['p75']:.1f}")
    print(f"  p90:          {stats['p90']:.1f}")
    print(f"  Max Delta:    {stats['max']}")
    print(f"  Mean Delta:   {stats['mean']:.2f}")
    print("=======================================================")

    print("\nRecent State-to-Code Causal Propagation Traces:")
    for tr in res["traces"][-10:]:
        d_str = f"Delta={tr['delta']}" if tr["delta"] is not None else "Delta=PENDING"
        same_str = " (same commit)" if tr["same_commit"] else ""
        print(f"  [{tr['state_hash']}] {tr['state_subject'][:35]:<35} -> [{tr['code_hash'] or '...':<7}] {tr['code_subject'][:30]:<30} | {d_str}{same_str}")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=2)
        print(f"\nWrote results to {args.json}")


if __name__ == "__main__":
    main()
