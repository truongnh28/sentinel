#!/usr/bin/env python3
"""measure_eta_q.py -- the two halves of eta_Q, each with its own provenance.

Spec: docs/design/plans/2026-09-22-W1-W10-tham-so.md Task 3 (W2);
docs/AuditGame-SE_Parameter_Estimation_Report.md section 5.2.

eta_Q(k) = detach(k) + restore(k), and the two halves are measured differently
because they are different events:

  detach(k)   what it costs to take carrier k out of the loop and run the task
              without it.  Measured here by running the SAME workflow on the
              SAME seed twice -- once normally, once quarantining k at the first
              task -- and taking the CPU-time difference of the whole episode.

  restore(k)  what it costs to rebuild what the quarantine destroyed.  A
              quarantine removes EVERY item of the carrier, clean ones included,
              so restoring costs n_live(k) writes.  A write is agent work, not
              judge work, so it is priced from the REAL agent runs of P2:
              usd_per_task comes from the recorded token counts of
              spikes/p2-pilot.jsonl priced through llms.py, and writes_per_task
              from the instrumented episodes.

WHY THE DETACH HALF CAN COME OUT AT OR BELOW ZERO HERE, AND WHAT THAT MEANS.
In the simulator, removing a carrier removes work: the agent retrieves less and
the probe scores fewer items, so the episode can run FASTER without it.  That is
a fact about this harness, not about deployment, where re-running a task without
its memory means doing the task again.  When the measured difference is <= 0 the
script reports 0.0 and says so in `notes`, and eta_Q then rests on its restore
half alone -- a LOWER BOUND, which is the honest reading.

    python3 tools/measure_eta_q.py --reps 30 > spikes/eta-q.json
"""
from __future__ import annotations
import argparse
import datetime
import json
import pathlib
import random
import statistics
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent            # noqa: E402
import build            # noqa: E402
import costs            # noqa: E402
import detector         # noqa: E402
import llms             # noqa: E402
import runner           # noqa: E402
import policies as P    # noqa: E402
from core import CARRIERS, seed_of   # noqa: E402

P2_PILOT = pathlib.Path(__file__).resolve().parent.parent / "spikes" / "p2-pilot.jsonl"


class _QuarantineOnceAt(P.Policy):
    """Quarantines one named carrier at the first task, then does nothing.

    Local to this tool on purpose: it is a measuring instrument, not a policy
    anyone should be able to select in an experiment.
    """
    ACTIONS = frozenset()
    carrier: str = "memory"

    def choose(self, t, retrieved_carriers, signals):
        if t == 0:
            return P.QUARANTINE_PREFIX + self.carrier
        return None


def _episode_cpu_seconds(wf, ps, pol, det, ag, seed) -> float:
    t0 = time.process_time()
    runner.run_once(wf, ps, pol, det, ag, seed=seed)
    return time.process_time() - t0


def measure_detach(reps: int, h: int, setting: str) -> dict:
    """CPU-time difference between quarantining a carrier and not, per carrier."""
    det = detector.Detector.from_setting(setting)
    ag = agent.MockAgent()
    deltas: dict = {c: [] for c in CARRIERS}
    for i in range(reps):
        wf = build.make_workflow(f"etaq-{i:03d}", "django", h,
                                 random.Random(seed_of("etaq", i)))
        ps = build.plan_poison(wf, "memory", 2,
                               random.Random(seed_of("etaq-ps", i)))
        if ps is None:
            continue
        for c in CARRIERS:
            base_pol = P.make_policy("B1 audit-at-commit", 17.95,
                                     seed_of("etaq-pol", i), setting)
            base = _episode_cpu_seconds(wf, ps, base_pol, det, ag, seed=i)
            q_pol = _QuarantineOnceAt(name=f"quarantine-{c}", budget=17.95,
                                      rng_seed=seed_of("etaq-pol", i),
                                      setting=setting)
            q_pol.carrier = c
            quarantined = _episode_cpu_seconds(wf, ps, q_pol, det, ag, seed=i)
            deltas[c].append(quarantined - base)
    return {c: {"median_delta_seconds": statistics.median(v),
                "mean_delta_seconds": statistics.fmean(v),
                "n": len(v)}
            for c, v in deltas.items() if v}


def usd_per_task_from_p2() -> dict:
    """Price the recorded P2 token counts through the frozen price table.

    The rows carry `cost_usd: null` -- the runner never priced them -- but they
    do carry tokens_in, tokens_out and the cache-hit rate, and llms.py carries
    the prices those were bought at.  So the cost is recoverable, and recovering
    it here keeps one source for the prices.
    """
    scope = llms.REGISTRY["deepseek-v4.1-flash"].scope()
    rows = [json.loads(l) for l in P2_PILOT.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    per_task = []
    for r in rows:
        t_in, t_out = r.get("tokens_in"), r.get("tokens_out")
        if not t_in or not t_out:
            continue
        hit = r.get("cache_hit") or 0.0
        usd = (t_in * hit * scope.price_in_hit
               + t_in * (1.0 - hit) * scope.price_in_miss
               + t_out * scope.price_out) / 1e6
        per_task.append(usd)
    return {"median": statistics.median(per_task),
            "mean": statistics.fmean(per_task),
            "min": min(per_task), "max": max(per_task), "n": len(per_task),
            "model": scope.model, "priced_at": scope.priced_at}


def writes_per_task(reps: int, h: int, setting: str) -> float:
    """Mean number of items the agent writes in one task, from real traces."""
    det = detector.Detector.from_setting(setting)
    ag = agent.MockAgent()
    counts = []
    for i in range(reps):
        wf = build.make_workflow(f"wpt-{i:03d}", "django", h,
                                 random.Random(seed_of("wpt", i)))
        ps = build.plan_poison(wf, "memory", 2,
                               random.Random(seed_of("wpt-ps", i)))
        if ps is None:
            continue
        pol = P.make_policy("B1 audit-at-commit", 17.95, seed_of("wpt-pol", i), setting)
        res = runner.run_once(wf, ps, pol, det, ag, seed=i, record_traces=True)
        for tr in res.traces:
            counts.append(len(tr.writes or []))
    return statistics.fmean(counts) if counts else float("nan")


def measure(reps: int = 30, h: int = 8, setting: str = "mid") -> dict:
    detach = measure_detach(reps, h, setting)
    task_usd = usd_per_task_from_p2()
    per_task_writes = writes_per_task(min(reps, 10), h, setting)
    usd_per_write = task_usd["median"] / per_task_writes if per_task_writes else float("nan")

    notes = []
    eta = {}
    for c in CARRIERS:
        d = detach.get(c, {}).get("median_delta_seconds", 0.0)
        if d <= 0:
            notes.append(f"detach({c}) measured at {d:.6f}s <= 0: in this harness "
                         f"removing a carrier removes work, so the detach half is "
                         f"reported as 0 and eta_Q is a LOWER BOUND")
            d = 0.0
        restore_writes = costs.ITEMS_PER_AUDIT[c]
        eta[c] = {
            "detach_seconds": d,
            "detach_usd": d * costs.SECONDS_TO_USD,
            "restore_items": restore_writes,
            "restore_usd": restore_writes * usd_per_write,
            "eta_q_usd": d * costs.SECONDS_TO_USD + restore_writes * usd_per_write,
            "kappa_usd": costs.KAPPA_USD[c],
        }
    ratio = {c: eta[c]["eta_q_usd"] / costs.KAPPA_USD[c] for c in eta}

    return {
        "eta_q": eta,
        "eta_q_over_kappa": ratio,
        "usd_per_write": usd_per_write,
        "usd_per_task_p2": task_usd,
        "writes_per_task": per_task_writes,
        "detach_raw": detach,
        "notes": notes,
        "provenance": {
            "detach_clock": "time.process_time (user+sys), whole episode",
            "restore_price": "P2 pilot token counts priced through llms.py "
                             "(deepseek-v4.1-flash), divided by writes per task",
            "reps": reps, "H": h, "setting": setting,
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
