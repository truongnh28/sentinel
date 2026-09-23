#!/usr/bin/env python3
"""measure_kappa_commit.py -- what a commit audit costs when it runs the tests.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 2;
docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md P1.

THE ONE NUMBER THAT DECIDES THE SIGN.  Everything separating the USD cost table
from the CPU one reduces to kappa_commit / kappa_bar, and nobody has measured
it: the USD table DEFINES it as "score all four carriers" (4.00x) and the CPU
table MEASURES it without differential testing (1.43x, a lower bound).  The
crossover where B1 stops winning sits BETWEEN those two.  Stage 2 defines a
commit audit as "patch review + DIFFERENTIAL TESTING + provenance", and the
testing half is what this measures.

TWO SUBSTITUTIONS, BOTH DECLARED, BOTH FORCED.

  TESTS RUN AT HEAD, NOT AT base_commit.  A 2021 instance needs its era's
  dependency pins -- which is exactly what SWE-bench's per-instance Docker
  images encode and this project does not have.  Measured directly: requests at
  its 2014 base commit dies on `ModuleNotFoundError: cgi` (removed in Python
  3.13), and pylint at 2021 pulls a `wrapt` that dies on `formatargspec`
  (removed in 3.11).  The cost of running a test subset is a property of the
  SUITE, and suites grow, so running at HEAD is if anything an OVER-estimate --
  which is the safe direction for a quantity used as a lower bound elsewhere.

  ONLY REPOS WHOSE SUITE RUNS WITHOUT COMPILED DEPENDENCIES.  matplotlib,
  scikit-learn and astropy need numpy/C extensions built per environment; that
  cost is real but it is environment SETUP, not per-audit cost, and folding it
  in would inflate kappa_commit by a one-off.  Repos are skipped with a reason
  and the count is reported, not hidden.

WHAT IS TIMED.  resource.getrusage(RUSAGE_CHILDREN) around the pytest child,
user + system, median of REPEATS runs.  Environment build time is measured
separately and EXCLUDED: it is paid once per machine, not once per audit.

    python3 tools/measure_kappa_commit.py --per-repo 3 > spikes/kappa-commit.json
"""
from __future__ import annotations
import argparse
import datetime
import json
import os
import pathlib
import re
import resource
import shutil
import statistics
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import costs

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspace"
DATA = ROOT / "data" / "swebench_verified.jsonl"
SCRATCH = pathlib.Path(os.environ.get("SENTINEL_SCRATCH", "/tmp")) / "kappa-commit"

#: Repos whose suite is pure Python.  Declared before running, so a repo that
#: turns out to be slow cannot be dropped afterwards for being inconvenient.
CANDIDATES = {
    # `setuptools` goes into EVERY venv, not just these: sphinx imports
    # pkg_resources from it, and modern Python no longer bundles it.
    "sympy/sympy": ["mpmath"],
    "pytest-dev/pytest": [],
    "pylint-dev/pylint": [],
    "sphinx-doc/sphinx": [],
}

REPEATS = 3
PYTHON = "3.11"


def _cpu_children() -> float:
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime + r.ru_stime


_SUMMARY = re.compile(rb"(\d+) (passed|failed|error|errors)")


def _run(cmd, cwd, timeout=900) -> tuple:
    """(cpu_seconds, n_executed).  CPU of the CHILD, not wall clock.

    n_executed is parsed from pytest's own summary, and it is the guard this
    measurement cannot do without: a node id that no longer exists at HEAD makes
    pytest exit in under a tenth of a second having run NOTHING, and the timing
    would then be of pytest's startup.  A first version of this script reported
    0.07 CPU seconds for 74 tests, which is what that failure looks like.
    """
    before = _cpu_children()
    out = b""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return _cpu_children() - before, -1
    ran = 0
    for n, kind in _SUMMARY.findall(out):
        if kind in (b"passed", b"failed"):
            ran += int(n)
    return _cpu_children() - before, ran


def prepare(repo: str, extras: list) -> tuple:
    """A worktree at HEAD with its own venv.  Returns (path, build_seconds, err)."""
    src = WORKSPACE / repo
    if not (src / ".git").exists():
        return None, 0.0, "not cloned"
    wt = SCRATCH / repo.replace("/", "__")
    shutil.rmtree(wt, ignore_errors=True)
    wt.parent.mkdir(parents=True, exist_ok=True)
    # `worktree add` refuses a path git still has registered, and rmtree above
    # leaves exactly that state behind on a re-run. Prune first, or every run
    # after the first reports "worktree failed" for every repo -- which is what
    # it did.
    subprocess.run(["git", "-C", str(src), "worktree", "prune"],
                   capture_output=True)
    add = subprocess.run(["git", "-C", str(src), "worktree", "add", "-q",
                          "--detach", str(wt), "HEAD"], capture_output=True)
    if add.returncode != 0:
        return None, 0.0, f"worktree failed: {add.stderr.decode()[:120].strip()}"
    t0 = _cpu_children()
    subprocess.run(["uv", "venv", "-q", "--python", PYTHON, ".venv"],
                   cwd=wt, capture_output=True)
    # The PACKAGE ITSELF, not just pytest: sphinx's own tests import sphinx, and
    # a venv with only pytest collects nothing and exits in 0.07 CPU seconds --
    # which is what the first version of this script timed.
    subprocess.run(["uv", "pip", "install", "-q", "--python", ".venv/bin/python",
                    "-e", ".", "pytest", "setuptools", *extras],
                   cwd=wt, capture_output=True)
    build = _cpu_children() - t0
    if not (wt / ".venv" / "bin" / "python").exists():
        return None, build, "venv build failed"
    return wt, build, None


def measure_repo(repo: str, extras: list, rows: list, per_repo: int) -> dict:
    wt, build, err = prepare(repo, extras)
    if err:
        return {"skipped": err}
    out = {"env_build_cpu_seconds": round(build, 2), "instances": []}
    py = str(wt / ".venv" / "bin" / "python")
    for row in rows[:per_repo]:
        tests = json.loads(row["PASS_TO_PASS"])
        if not tests:
            continue
        # Node ids can name tests that no longer exist at HEAD. pytest reports
        # those as errors rather than silently running fewer, so the ran/asked
        # ratio below is a real denominator and is carried into the result.
        # TWO ID FORMATS IN ONE DATASET, and they are not interchangeable.
        # sphinx ships pytest node ids ("tests/x.py::test_y"); sympy ships BARE
        # FUNCTION NAMES ("test_point3D") because SWE-bench drives it with the
        # repo's own bin/test runner. Handing a bare name to pytest as a path
        # selects nothing, silently.
        sel = [t for t in tests][:120]
        if any("::" in t for t in sel):
            cmds = [t for t in sel if "::" in t]
        else:
            # -k over the suite: slower to collect, but it is the only way a
            # bare name selects anything at all.
            cmds = ["-k", " or ".join(sel[:40])]
        times, ran = [], 0
        for _ in range(REPEATS):
            cpu, n = _run([py, "-m", "pytest", "-q", "--no-header",
                           "-p", "no:cacheprovider", *cmds], cwd=wt)
            times.append(cpu)
            ran = max(ran, n)
        rec = {
            "instance_id": row["instance_id"],
            "n_tests_asked": len(tests),
            "n_tests_requested": len(sel),
            "selection": "node-ids" if any("::" in t for t in sel) else "-k names",
            "n_tests_executed": ran,
            "cpu_seconds_median": round(statistics.median(times), 3),
            "cpu_seconds_all": [round(t, 3) for t in times],
        }
        # `-k` matches by SUBSTRING, so "test_point" also selects test_point3D
        # and test_pointless: 43 names requested, 545 tests executed. The raw
        # total therefore OVER-states what this instance's audit would cost, and
        # over-stating kappa_commit is not a safe direction -- it flatters the
        # policies B1 is being compared against. Per-test cost x the number
        # actually asked for is the estimate that does not inherit the
        # over-selection.
        if ran:
            per = statistics.median(times) / ran
            rec["cpu_seconds_per_test"] = round(per, 4)
            rec["cpu_seconds_scaled"] = round(per * rec["n_tests_requested"], 3)
        # A run that executed nothing measured pytest's startup, not a suite.
        # It is recorded and EXCLUDED rather than dropped silently.
        rec["usable"] = ran >= max(1, len(sel) // 4)
        out["instances"].append(rec)
        print(f"  {row['instance_id']:36} {statistics.median(times):7.2f} s CPU "
              f"  {ran}/{len(sel)} executed"
              f"{'' if rec['usable'] else '   <- EXCLUDED'}", file=sys.stderr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-repo", type=int, default=3)
    a = ap.parse_args()

    by_repo: dict = {}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            by_repo.setdefault(r["repo"], []).append(r)

    per_repo_out, all_times = {}, []
    for repo, extras in CANDIDATES.items():
        print(f"[{repo}]", file=sys.stderr)
        res = measure_repo(repo, extras, by_repo.get(repo, []), a.per_repo)
        per_repo_out[repo] = res
        for inst in res.get("instances", []):
            if inst.get("usable") and "cpu_seconds_scaled" in inst:
                all_times.append(inst["cpu_seconds_scaled"])

    kbar = sum(costs.KAPPA_USD.values()) / len(costs.KAPPA_USD)
    review = costs.KAPPA_COMMIT_USD
    t_med = statistics.median(all_times) if all_times else None

    # The break-even: the CPU price at which B1 stops winning. Solving for it
    # is better than choosing a VM price, because it turns a missing input into
    # a threshold the reader can check against their own machine bill.
    # r* = (m* * kappa_bar - review) / T_test.  A NEGATIVE r* is not a price:
    # it says the review half ALONE already puts kappa_commit past the crossover,
    # so no CPU price can bring it back and the answer does not depend on the
    # machine bill at all.  Reporting a negative number as if it were a price
    # would be the kind of thing this project keeps finding in its own tables.
    breakeven = {}
    if t_med:
        for m in (1.43, 2.0):
            r = (m * kbar - review) / t_med
            breakeven[str(m)] = {
                "usd_per_cpu_second": round(r, 8),
                "meaning": ("no price can reach this ratio: the review half "
                            f"({review:.6f} USD) already exceeds {m} x kappa_bar "
                            f"({m * kbar:.6f} USD), so kappa_commit/kappa_bar is "
                            "above the crossover at ANY non-negative CPU price")
                if r < 0 else
                ("B1 keeps winning while a CPU second costs less than this"),
            }
    ratio_floor = review / kbar

    print(json.dumps({
        "t_test_basis": ("cpu_seconds_per_test x tests actually requested, NOT "
                         "the raw run total -- see the -k over-selection note"),
        "t_test_cpu_seconds": {
            "median": t_med,
            "min": min(all_times) if all_times else None,
            "max": max(all_times) if all_times else None,
            "n_instances": len(all_times),
        },
        "per_repo": per_repo_out,
        "review_half_usd": review,
        "kappa_bar_usd": kbar,
        "usd_per_cpu_second": costs.USD_PER_CPU_SECOND,
        "kappa_commit_over_kappa_bar_floor": round(ratio_floor, 3) if t_med else None,
        "crossover_band": [1.43, 2.0],
        "verdict": (("kappa_commit / kappa_bar >= %.2f from the review half alone, "
                     "which is already above the 1.43-2.0 crossover band. Adding "
                     "the measured test cost only raises it. The sign of RQ1 does "
                     "NOT depend on the CPU price." % ratio_floor)
                    if t_med and ratio_floor > 2.0 else
                    "the crossover is reachable; the CPU price decides"),
        "breakeven_usd_per_cpu_second": breakeven,
        "reading": ("kappa_commit(r) = review + T_test * r, with r the USD price "
                    "of a CPU second. B1 keeps winning only while kappa_commit "
                    "stays below about 2.0 * kappa_bar, so the breakeven r above "
                    "is the price at which the answer changes. Compare it with "
                    "the machine bill rather than picking a number here."),
        "caveats": [
            "tests run at HEAD, not at base_commit -- era pinning needs the "
            "per-instance Docker images this project does not have",
            "environment build time is measured and EXCLUDED: paid once per "
            "machine, not once per audit",
            "repos needing compiled dependencies are skipped, with the reason",
        ],
        "provenance": {
            "python": PYTHON, "repeats": REPEATS,
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
