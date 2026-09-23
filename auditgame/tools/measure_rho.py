#!/usr/bin/env python3
"""measure_rho.py -- the covering radius, in the space Proposition 6 is about.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 6D;
docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md P4.

WHAT WAS WRONG WITH THE OLD NUMBER.  `theory.library_covering_radius` measures
rho over the AUDIT MARGINAL: one distribution over actions per policy, pooled
across the whole episode.  Two policies that audit memory every task and two
that audit it only at t=0 and t=7 have the SAME marginal and completely
different behaviour -- and the thing an attacker routes around is the behaviour.
Proposition 6 bounds the loss of using a finite library instead of the full
policy space, so the distance has to separate policies an attacker can tell
apart.  Measured here on the PER-TASK action distribution instead:

    d(pi, pi') = (1/H) sum_t TV( p_t(pi), p_t(pi') )

TWO QUESTIONS, AND THEY ARE DIFFERENT.

  COVER    how far is each policy we actually care about from its nearest
           library member.  This is the operational rho: it says what the
           covering argument costs on the policies in the paper.

  SATURATE does adding members stop helping?  Stage 6D asks for the library
           SIZE to be justified this way rather than by quoting 28.  Measured
           by greedily growing a subset and recording rho at each size; a curve
           that flattens says the class is dense enough, and where it flattens
           is the number to report.

The old value is printed beside the new one, because the gap between them is
the finding: it says how much of the previous rho was an artifact of pooling.

    python3 tools/measure_rho.py --n 12 --seeds 2 > spikes/rho.json
"""
from __future__ import annotations
import argparse
import datetime
import json
import pathlib
import random
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent
import build
import detector
import experiment
import policies as P
import policies_library as L
import runner
import theory
from core import CARRIERS, seed_of

#: The action alphabet a per-task distribution is taken over.  "none" is a real
#: choice, not a missing value: a policy that declines to audit at t is doing
#: something an attacker can exploit, and folding it into the other bins would
#: make a frugal policy look like a busy one.
ALPHABET = tuple(CARRIERS) + ("commit", "quarantine", "none")

#: Policies the covering argument has to cover: the ones the paper reports.
TARGETS = ["B1 audit-at-commit", "B5 risk-score", "B6 two-stage",
           "B7 minimax-lp", "Sentinel", "SentinelW window-belief",
           "SSG-G guarded"]


def _bin(action) -> str:
    if action is None:
        return "none"
    if action.startswith(P.QUARANTINE_PREFIX) or action == P.QUARANTINE_ALL:
        return "quarantine"
    carrier, _ = P.split_action(action)
    return carrier if carrier in ALPHABET else "none"


def profile(make, name, wfs, det, ag, budget, seeds, H) -> list:
    """Per-task action distribution: H vectors over ALPHABET."""
    counts = [{a: 0 for a in ALPHABET} for _ in range(H)]
    for wf in wfs:
        ps = build.plan_poison(wf, "memory", 2,
                               random.Random(seed_of(wf.wf_id, 2, "memory")))
        if ps is None:
            continue
        for s in seeds:
            pol = make(name, budget, rng_seed=seed_of(wf.wf_id, s))
            r = runner.run_once(wf, ps, pol, det, ag, seed=s, record_traces=True)
            for tr in (r.traces or []):
                if tr.t < H:
                    counts[tr.t][_bin(getattr(tr, "action", None))] += 1
    out = []
    for c in counts:
        tot = sum(c.values())
        out.append(tuple(c[a] / tot for a in ALPHABET) if tot
                   else tuple(1.0 / len(ALPHABET) for _ in ALPHABET))
    return out


def distance(p: list, q: list) -> float:
    """Mean over tasks of the total-variation distance at that task."""
    n = min(len(p), len(q))
    return sum(0.5 * sum(abs(a - b) for a, b in zip(p[t], q[t]))
               for t in range(n)) / n


def saturation(lib: dict, targets: dict) -> list:
    """rho as the library grows, members added greedily most-useful-first.

    Greedy, not random: the question is whether a WELL-CHOSEN library of size m
    suffices, and a random subset answers a different and easier question.
    """
    chosen, curve = [], []
    remaining = list(lib)
    while remaining:
        best, best_rho = None, None
        for cand in remaining:
            sub = chosen + [cand]
            rho = max(min(distance(t, lib[m]) for m in sub)
                      for t in targets.values())
            if best_rho is None or rho < best_rho:
                best, best_rho = cand, rho
        chosen.append(best)
        remaining.remove(best)
        curve.append({"size": len(chosen), "added": best, "rho": round(best_rho, 4)})
    return curve


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--H", type=int, default=8)
    ap.add_argument("--budget", type=float, default=17.95)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--detector", default="mid")
    a = ap.parse_args()

    wfs = experiment.make_corpus(a.n, a.H, seed=2026)
    det, ag = detector.Detector.from_setting(a.detector), agent.MockAgent()
    seeds = tuple(range(1, a.seeds + 1))

    lib = {nm: profile(lambda n, b, rng_seed: L.make(n, b, rng_seed=rng_seed),
                       nm, wfs, det, ag, a.budget, seeds, a.H)
           for nm in L.LIBRARY}
    tgt = {nm: profile(lambda n, b, rng_seed: P.make_policy(n, b, rng_seed=rng_seed),
                       nm, wfs, det, ag, a.budget, seeds, a.H)
           for nm in TARGETS}

    nearest = {nm: min(lib, key=lambda m: distance(p, lib[m]))
               for nm, p in tgt.items()}
    per_target = {nm: {"nearest": nearest[nm],
                       "distance": round(distance(tgt[nm], lib[nearest[nm]]), 4)}
                  for nm in tgt}
    rho = max(v["distance"] for v in per_target.values())

    old = theory.library_covering_radius(TARGETS, wfs, det, ag, a.budget,
                                         seeds, a.detector)

    curve = saturation(lib, tgt)
    # Where the curve stops paying: the first size after which no addition buys
    # more than 0.01.  Declared as a threshold rather than read off by eye.
    knee = next((c["size"] for i, c in enumerate(curve)
                 if all(curve[j]["rho"] > c["rho"] - 0.01
                        for j in range(i + 1, len(curve)))), len(curve))

    print(json.dumps({
        "rho_per_task_tv": round(rho, 4),
        "rho_old_audit_marginal_space": round(old, 4),
        "per_target": per_target,
        "saturation_curve": curve,
        "saturates_at": knee,
        "alphabet": list(ALPHABET),
        "reading": ("rho is the worst distance from a policy the paper reports "
                    "to its nearest library member, measured on PER-TASK action "
                    "distributions. The old number pooled over the episode, so "
                    "two policies with the same totals and different timing "
                    "looked identical."),
        "provenance": {
            "grid": f"{a.n} workflows, H={a.H}, B={a.budget}, "
                    f"detector {a.detector}, seeds {seeds}",
            "library_size": len(L.LIBRARY),
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
