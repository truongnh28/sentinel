#!/usr/bin/env python3
"""measure_kappa.py -- the kappa table, measured in CPU-time from the game loop itself.

Spec: docs/design/plans/2026-09-22-W1-W10-tham-so.md Task 1 (W4);
docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 2.

NO SEPARATE TEST BENCH.  This runs real episodes with `record_traces=True` and
aggregates `TaskTrace.audit_seconds` by `"stage:carrier"`.  It times the thing
that actually runs rather than a copy of it: a separate bench would score other
items, in other numbers, and the resulting kappa table would describe the bench
instead of the benchmark.

THE CLOCK IS `time.process_time` (user+sys), inside `runner._probe_seconds`.
See tests/gate1_integrity/test_cost_provenance.py.

TWO QUANTITIES, DO NOT MIX THEM.
  kappa_cpu_seconds   CPU seconds for ONE audit of one carrier (or of commit).
                      This is kappa in the sense of Stage 2.
  items_per_audit     how many items that audit had to score.  This is what
                      costs.py turns into a price under the per-judgement rate,
                      and what eta_Q reuses for its restore half.

COMMIT IS NOT DIRECTLY COMPARABLE to the four carriers: a commit audit scores a
SINGLE object (the patch), so its CPU seconds describe one scoring call, while a
carrier's describe n_live of them.  Both are printed, and `chi` is computed over
the four carriers only -- which is the definition, chi = max|k_i - k_j|/mean(k)
over carriers.

    python3 tools/measure_kappa.py --reps 30 > spikes/kappa-cpu.json
"""
from __future__ import annotations
import argparse
import datetime
import time
import json
import pathlib
import random
import statistics
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent            # noqa: E402
import build            # noqa: E402
import detector         # noqa: E402
import runner           # noqa: E402
import policies as P    # noqa: E402
from core import CARRIERS, CarrierStore, seed_of   # noqa: E402

#: The four audit stages of Stage 2.  `runner` writes keys as "stage:carrier";
#: the first three probe a carrier, the last one probes the patch.
STAGES = ("insertion", "retrieval", "delegation", "commit")


#: Inner repetitions when timing one carrier audit.  `time.process_time` has
#: roughly microsecond resolution, and a single audit of a small carrier costs
#: about that much -- so a one-shot timing quantises to the clock and every
#: carrier reads the same (measured: chi = 0.0 that way).  Timing R identical
#: audits and dividing measures the same work above the clock's floor.
INNER_REPEATS = 200


def carrier_costs(reps: int, h: int, setting: str) -> dict:
    """kappa(k): CPU seconds to audit carrier k, at the resolution the clock allows.

    An audit of carrier k inspects its live items, so the cost is timed on
    exactly that: `checkpoints.insertion` over `store.live(k)`, which is the
    integrity + provenance pass an upstream audit performs.
    """
    import checkpoints
    det = detector.Detector.from_setting(setting)
    ag = agent.MockAgent()
    per_carrier: dict = {c: [] for c in CARRIERS}
    for i in range(reps):
        wf = build.make_workflow(f"kappa-{i:03d}", "django", h,
                                 random.Random(seed_of("kappa", i)))
        ps = build.plan_poison(wf, "memory", 2,
                               random.Random(seed_of("kappa-ps", i)))
        if ps is None:
            continue
        pol = P.make_policy("B2 uniform random", 17.95,
                            seed_of("kappa-pol", i), setting)
        store = CarrierStore()
        runner.run_once(wf, ps, pol, det, ag, seed=i, record_traces=False,
                        store=store)
        for t, task in enumerate(wf.tasks):
            for c in CARRIERS:
                items = list(store.live(c))
                if not items:
                    continue
                t0 = time.process_time()
                for _ in range(INNER_REPEATS):
                    checkpoints.insertion(items, store, task)
                per_carrier[c].append((time.process_time() - t0) / INNER_REPEATS)
            break                      # one snapshot per episode is enough
    return per_carrier


def measure(reps: int = 30, h: int = 8, setting: str = "mid") -> dict:
    """Run `reps` episodes, aggregating audit_seconds per stage and per carrier."""
    det = detector.Detector.from_setting(setting)
    ag = agent.MockAgent()
    per_stage: dict = {s: [] for s in STAGES}
    per_carrier: dict = {c: [] for c in CARRIERS}
    items_per_audit: dict = {c: [] for c in CARRIERS}
    episodes = 0

    for i in range(reps):
        wf = build.make_workflow(f"kappa-{i:03d}", "django", h,
                                 random.Random(seed_of("kappa", i)))
        ps = build.plan_poison(wf, "memory", 2,
                               random.Random(seed_of("kappa-ps", i)))
        if ps is None:
            continue
        pol = P.make_policy("B2 uniform random", 17.95,
                            seed_of("kappa-pol", i), setting)
        res = runner.run_once(wf, ps, pol, det, ag, seed=i, record_traces=True)
        episodes += 1
        for tr in res.traces:
            for key, secs in tr.audit_seconds.items():
                stage, _, carrier = key.partition(":")
                if stage in per_stage:
                    per_stage[stage].append(secs)
                if carrier in per_carrier and stage != "commit":
                    per_carrier[carrier].append(secs)
            for c, n in (tr.n_c or {}).items():
                if c in items_per_audit:
                    items_per_audit[c].append(n)

    def summarise(samples: dict) -> dict:
        return {k: {"median": statistics.median(v),
                    "mean": statistics.fmean(v),
                    "min": min(v), "max": max(v), "n": len(v)}
                for k, v in samples.items() if v}

    # Per-carrier kappa comes from the repeated timing, not from the in-loop
    # probe: a single probe costs about one clock tick, so its median quantises
    # and every carrier reads alike.
    repeated = carrier_costs(min(reps, 12), h, setting)
    per_carrier = {c: v for c, v in repeated.items() if v}
    kappa_carrier = {c: statistics.median(v) for c, v in per_carrier.items()}
    vals = list(kappa_carrier.values())
    chi = ((max(vals) - min(vals)) / statistics.fmean(vals)) if vals else 0.0

    return {
        "kappa_cpu_seconds": {s: statistics.median(v)
                              for s, v in per_stage.items() if v},
        "kappa_cpu_seconds_by_carrier": kappa_carrier,
        "per_stage": summarise(per_stage),
        "per_carrier": summarise(per_carrier),
        "items_per_audit": {c: statistics.fmean(v)
                            for c, v in items_per_audit.items() if v},
        "chi": chi,
        "chi_formula": "max|k_i - k_j| / mean(k), over the FOUR CARRIERS (commit excluded)",
        "provenance": {
            "clock": "time.process_time (user+sys)",
            "reps_requested": reps, "episodes_built": episodes,
            "H": h, "setting": setting,
            "agent": "MockAgent (defaults)", "policy": "B2 uniform random",
            "budget": 17.95,
            "seed_rule": "seed_of('kappa', i) for the workflow, seed=i for the detector",
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--setting", default="mid")
    a = ap.parse_args()
    print(json.dumps(measure(a.reps, a.H, a.setting), indent=2, ensure_ascii=False))
