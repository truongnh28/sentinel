#!/usr/bin/env python3
"""v3_measure_kappa.py -- kappa of the four S7 audit checks, in CPU-minutes, on DEV (P3).

sentinel-v3.md S8 row "Gia audit": implement the four checks as draft S7 describes, then
measure; the draft's 0.4 / 0.9 / 1.6 / 4.1 CPU-minutes are printed next to the measured
values, and the measured ones are printed even when they differ.  The checks are
v3/audit_checks.py; this tool samples dev tasks, times each look, and summarises.

DEV ONLY.  Workflows come from v3.corpus.dev_workflows() (the v2 corpus, Q10) and from
nowhere else; `_dev_only` refuses any workflow whose id is not a v2 corpus id.  The eval
splits are never built here.

SAMPLE (declared before any timing).
    families   the dev families whose test suites run from a plain venv, without compiled
               extensions and without per-instance Docker images: django (43 of the 100
               dev workflows) and sympy (15).  Others are listed in the output as not
               measured, with the reason.
    workflows  per family, N_WF[family] workflows with at least AUDIT_AT + 1 tasks, drawn
               by random.Random(seed_of("v3-kappa", family)).sample over the sorted ids.
    looks      the audit happens at task t = AUDIT_AT (the 4th task); a depth-d audit of a
               target is the check on the records of tasks t, t-1, ..., t-d+1
               (audit_checks, DEPTH).  So each workflow contributes 3 looks per target,
               and kappa(k, d) of that workflow is the sum of its first d looks.
    reps       every look is timed REPS times; the look's cost is the median of its reps.
    envs       python 3.9 venvs (django < 5.0, sympy; SWE-bench runs sympy on 3.9) and a
               3.11 venv for django 5.0; tests run at the instance's base_commit.
Mean and 95% CI are over workflows (bootstrap, B = 10000, seeded); the t-interval is
printed beside it.

    ../.venv/bin/python tools/v3_measure_kappa.py run --family django
    ../.venv/bin/python tools/v3_measure_kappa.py run --family sympy
    ../.venv/bin/python tools/v3_measure_kappa.py summarise   # -> reference/v3_kappa_measured.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import pathlib
import random
import statistics
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent            # auditgame/
sys.path.insert(0, str(ROOT))

import draft_setup as D                                            # noqa: E402
from core import seed_of                                           # noqa: E402
from v3 import audit_checks as A                                   # noqa: E402
from v3 import corpus                                              # noqa: E402

WORK = ROOT / "workspace" / "kappa"          # gitignored: repo clones, venvs, worktrees
RAW = ROOT / "spikes" / "v3-kappa"
OUT = ROOT / "reference" / "v3_kappa_measured.json"

TARGETS = ("memory", "queue", "skill", "commit")
DEPTHS = (1, 2, 3)
AUDIT_AT = 3
REPS = 3
N_WF = {"django": 8, "sympy": 5}
FAMILY_REPO = {"django": "django/django", "sympy": "sympy/sympy"}
NOT_MEASURED = {
    "sphinx-doc/sphinx": "suite needs era-pinned docutils/jinja2 per instance (Docker image)",
    "scikit-learn/scikit-learn": "compiled extensions built per environment",
    "matplotlib/matplotlib": "compiled extensions built per environment",
    "pydata/xarray": "numpy/pandas pinned per instance",
    "astropy/astropy": "compiled extensions built per environment",
    "pytest-dev/pytest": "setuptools_scm build per commit; 3 workflows only",
    "non-Python families": "no toolchain in this environment (sentinel-v3.md: Held-out row)",
}
CHI_CONFIGS = {"1.04": (3, 3, 2, 1), "1.33": (3, 2, 1, 1), "2.11": (1, 1, 1, 1)}
B_BOOT = 10000


def _rows() -> dict:
    rows = {}
    for f in ("swebench_verified.jsonl", "swebench_full.jsonl"):
        for line in (ROOT / "data" / f).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows.setdefault(r["instance_id"], r)
    return rows


def _dev_only(wfs: list) -> list:
    for w in wfs:
        if not w.wf_id.startswith("v2-"):
            raise RuntimeError(f"{w.wf_id} is not a dev (v2 corpus) workflow")
    return wfs


def sample(family: str) -> list:
    wfs = _dev_only(corpus.dev_workflows())
    pool = sorted(w.wf_id for w in wfs
                  if w.repo == FAMILY_REPO[family] and len(w.tasks) > AUDIT_AT)
    chosen = sorted(random.Random(seed_of("v3-kappa", family)).sample(pool, N_WF[family]))
    by_id = {w.wf_id: w for w in wfs}
    return [by_id[i] for i in chosen]


def _python(family: str, version: str) -> str:
    env = "env-sy39" if family == "sympy" else ("env-dj311" if version == "5.0" else "env-dj39")
    return str(WORK / env / "bin" / "python")


def _reset(wt: str, base: str) -> float:
    t0 = A.CpuClock.now()
    subprocess.run(["git", "-C", wt, "checkout", "-f", "-q", "--detach", base], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", wt, "clean", "-fdxq"], check=True, capture_output=True)
    return A.CpuClock.now() - t0


def run(family: str, reps: int) -> dict:
    rows = _rows()
    repo = str(WORK / family)
    wt = str(WORK / f"wt-{family}")
    if not pathlib.Path(wt).exists():
        subprocess.run(["git", "-C", repo, "worktree", "add", "-q", "--detach", wt, "HEAD"],
                       check=True, capture_output=True)
    out = {"family": family, "reps": reps, "workflows": []}
    for w in sample(family):
        recs = [A.materialise(rows[t.task_id], repo) for t in w.tasks[:AUDIT_AT + 1]]
        wrec = {"wf_id": w.wf_id, "looks": []}
        for j in range(AUDIT_AT, AUDIT_AT - max(DEPTHS), -1):          # t, t-1, t-2
            row = rows[w.tasks[j].task_id]
            py = _python(family, row["version"])
            r = recs[j]
            lineage = [recs[i]["skill"] for i in range(j)]
            look = {"task": row["instance_id"], "version": row["version"], "python": py.split("/")[-3],
                    "cpu": {}, "findings": {}, "setup_cpu": []}
            for target in TARGETS:
                times = []
                for _ in range(reps):
                    if target in ("skill", "commit"):
                        look["setup_cpu"].append(_reset(wt, r["commit"]["base"]))
                    t0 = A.CpuClock.now()
                    if target == "memory":
                        f = A.insertion(r["memory"], repo)
                    elif target == "queue":
                        f = A.retrieval(r["queue"], repo)
                    elif target == "skill":
                        f = A.delegation(r["skill"], wt, py, family)
                    else:
                        f = A.commit(r["commit"], wt, py, family, repo, lineage)
                    times.append(A.CpuClock.now() - t0)
                look["cpu"][target] = times
                look["findings"][target] = f
            print(f"  {w.wf_id} {row['instance_id']:32} " + "  ".join(
                f"{k[:3]} {statistics.median(v):8.3f}s" for k, v in look["cpu"].items()),
                file=sys.stderr, flush=True)
            wrec["looks"].append(look)
        out["workflows"].append(wrec)
    out["date"] = datetime.date.today().isoformat()
    out["commit"] = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                   text=True, cwd=ROOT).stdout.strip()
    return out


# ---------------------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------------------

def usable(look: dict, target: str) -> bool:
    """A test-running look that executed no test timed pytest's / runtests' startup, not an
    audit (measure_kappa_commit's lesson); it is excluded and counted."""
    f = look["findings"][target]
    if target == "skill":
        return bool(f.get("applies")) and f.get("evidence_ran", 0) > 0
    if target == "commit":
        return bool(f.get("applies")) and f.get("ran_post", 0) > 0
    return True


def per_workflow(raws: list) -> tuple:
    """{wf: {target: {d: cpu seconds}}} over workflows whose d looks are all usable."""
    table, excluded = {}, []
    for raw in raws:
        for w in raw["workflows"]:
            rec = {}
            for target in TARGETS:
                costs = []
                for look in w["looks"]:
                    if not usable(look, target):
                        excluded.append((w["wf_id"], look["task"], target))
                        break
                    costs.append(statistics.median(look["cpu"][target]))
                rec[target] = {d: sum(costs[:d]) for d in DEPTHS if len(costs) >= d}
            table[(raw["family"], w["wf_id"])] = rec
    return table, excluded


def _t975(n: int) -> float:
    t = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31, 9: 2.26,
         10: 2.23, 11: 2.20, 12: 2.18, 13: 2.16, 14: 2.14, 15: 2.13, 20: 2.09, 30: 2.04}
    return t.get(n, 1.96 if n > 30 else t[max(k for k in t if k <= n)])


def stats(xs: list, rng: random.Random) -> dict:
    n = len(xs)
    m = statistics.fmean(xs)
    sd = statistics.stdev(xs) if n > 1 else 0.0
    boots = sorted(statistics.fmean(rng.choices(xs, k=n)) for _ in range(B_BOOT))
    return {"mean": m, "sd": sd, "n": n,
            "ci95_boot": [boots[int(0.025 * B_BOOT)], boots[int(0.975 * B_BOOT) - 1]],
            "ci95_t": [m - _t975(n - 1) * sd / math.sqrt(n), m + _t975(n - 1) * sd / math.sqrt(n)]
            if n > 1 else [m, m]}


def chi_of(kappa: dict) -> dict:
    return {"chi_range": D.chi_range(kappa), "chi_2mad": D.chi_reported(kappa)}


def summarise(raws: list) -> dict:
    table, excluded = per_workflow(raws)
    rng = random.Random(seed_of("v3-kappa-boot"))
    keys = sorted(table)
    minutes = lambda s: s / 60.0                                      # noqa: E731

    def block(sel):
        out = {}
        for target in TARGETS:
            out[target] = {}
            for d in DEPTHS:
                xs = [minutes(table[k][target][d]) for k in sel if d in table[k][target]]
                if len(xs) >= 2:
                    out[target][str(d)] = stats(xs, rng)
        return out

    pooled = block(keys)
    by_family = {fam: block([k for k in keys if k[0] == fam]) for fam in sorted({k[0] for k in keys})}

    # chi per depth configuration, with a paired bootstrap over workflows (one resample of
    # workflows moves all four targets together).
    complete = [k for k in keys if all(d in table[k][t] for t in TARGETS for d in DEPTHS)]
    chis = {}
    for label, cfg in CHI_CONFIGS.items():
        dep = dict(zip(TARGETS, cfg))
        point = {t: pooled[t][str(dep[t])]["mean"] for t in TARGETS}
        boots = {"chi_range": [], "chi_2mad": []}
        for _ in range(B_BOOT):
            s = rng.choices(complete, k=len(complete))
            kap = {t: statistics.fmean(table[k][t][dep[t]] for k in s) for t in TARGETS}
            for name, v in chi_of(kap).items():
                boots[name].append(v)
        draft = {t: D.TARGET_KAPPA_DRAFT[t] * dep[t] for t in TARGETS}
        linear = {t: pooled[t]["1"]["mean"] * dep[t] for t in TARGETS}
        chis[label] = {
            "depths_memory_queue_skill_commit": list(cfg),
            "kappa_cpu_min_measured": point,
            "measured": {n: {"point": v, "ci95_boot": [sorted(boots[n])[int(0.025 * B_BOOT)],
                                                        sorted(boots[n])[int(0.975 * B_BOOT) - 1]]}
                         for n, v in chi_of(point).items()},
            "measured_linear_in_depth": chi_of(linear),
            "draft_prices": chi_of(draft),
        }

    lin = {t: {str(d): pooled[t][str(d)]["mean"] / (d * pooled[t]["1"]["mean"]) for d in DEPTHS}
           for t in TARGETS}
    n_looks = sum(len(w["looks"]) for r in raws for w in r["workflows"])
    return {
        "unit": "CPU-minutes per audit (user+sys of the process and its children)",
        "draft_S7_cpu_min": dict(D.TARGET_KAPPA_DRAFT),
        "stage_of_target": A.STAGE_OF_TARGET,
        "kappa_cpu_min": pooled,
        "kappa_cpu_min_by_family": by_family,
        "depth_linearity_kappa_d_over_d_kappa_1": lin,
        "chi_by_depth_config": chis,
        "chi_draft_table_depth1": chi_of(dict(D.TARGET_KAPPA_DRAFT)),
        "looks_excluded": [list(x) for x in excluded],
        "sample": {
            "split": "dev (v3.corpus.dev_workflows, the v2 corpus); eval never built",
            "workflows": {r["family"]: [w["wf_id"] for w in r["workflows"]] for r in raws},
            "n_workflows": len(keys), "n_looks": n_looks, "audit_at_task": AUDIT_AT,
            "reps_per_look": sorted({r["reps"] for r in raws}),
            "families_not_measured": NOT_MEASURED,
        },
        "clock": "time.process_time + RUSAGE_CHILDREN (user+sys); checkout/reset excluded",
        "setup_cpu_min_per_reset_median": minutes(statistics.median(
            s for r in raws for w in r["workflows"] for lk in w["looks"] for s in lk["setup_cpu"])),
        "raw": [f"spikes/v3-kappa/{r['family']}.json" for r in raws],
        "provenance": {"runs": {r["family"]: {"date": r["date"], "commit": r["commit"]}
                                for r in raws},
                       "tool": "tools/v3_measure_kappa.py", "checks": "v3/audit_checks.py",
                       "bootstrap": {"B": B_BOOT, "seed": "seed_of('v3-kappa-boot')"}},
        "wired_into_config": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--family", choices=sorted(N_WF), required=True)
    r.add_argument("--reps", type=int, default=REPS)
    sub.add_parser("summarise")
    a = ap.parse_args()
    if a.cmd == "run":
        RAW.mkdir(parents=True, exist_ok=True)
        res = run(a.family, a.reps)
        (RAW / f"{a.family}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        return 0
    raws = [json.loads(p.read_text()) for p in sorted(RAW.glob("*.json"))]
    res = summarise(raws)
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({t: {d: round(v["mean"], 4) for d, v in res["kappa_cpu_min"][t].items()}
                      for t in TARGETS}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
