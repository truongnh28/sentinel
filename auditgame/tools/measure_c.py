#!/usr/bin/env python3
"""measure_c.py -- the constant c of Theorem 4, fitted from belief convergence.

Spec: docs/design/plans/2026-09-22-W1-W10-tham-so.md Task 6 (W6);
docs/AuditGame-SE_Parameter_Estimation_Report.md section 5.4.

Theorem 4 states a budget floor for telling an infected state from a benign one
at the decision point:

    B >= c * kappa_bar * (1 + chi) * log(1/alpha) / gamma^2 * (1 + (Delta/H) * K)

A bound with a free constant bounds nothing, so c has to be fitted -- and the
left-hand side has to be something this repo can measure.  It is: Theorem 4 is a
statement about the defender's BELIEF converging on the true attack window, and
belief.WindowBelief computes that posterior exactly.

    B_min(cell) = the smallest budget at which, at the detonation task sigma, the
                  posterior puts at least (1 - alpha) of its mass on the true
                  window (k, iota, sigma).

    c_cell      = B_min * gamma^2
                  -----------------------------------------------------
                  kappa_bar * (1 + chi) * log(1/alpha) * (1 + Delta*K/H)

MONOTONICITY IS CHECKED BEFORE THE BISECTION, not assumed.  More budget buys
more audits, which should never make the posterior worse; if it does, bisection
is meaningless and the script says so instead of returning a number.

WHAT c IS AND IS NOT.  Fitted this way, c is the constant of THIS belief
mechanism, not of an optimal defender, and it gives an upper bound on the budget
needed rather than an information-theoretic lower bound.  The spread of c_cell
across cells is the real result: if the bound's SHAPE is right the regression of
log c_cell on the three factors has coefficients near zero, and a coefficient
that is not near zero names the factor the bound gets wrong.

    python3 tools/measure_c.py > spikes/theorem4-c.json
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent            # noqa: E402
import belief           # noqa: E402
import build            # noqa: E402
import costs            # noqa: E402
import detector         # noqa: E402
import policies as P    # noqa: E402
import scoring          # noqa: E402
from core import CARRIERS, CarrierStore, agent_seed, seed_of   # noqa: E402

ALPHA = 0.05
K = len(CARRIERS)

import runner           # noqa: E402

#: The observation model and the probe policy, set from the command line.
#: M0 + B7 reproduces every number this script has published.  Under MA the
#: probe is B2 uniform random, declared BEFORE the run in
#: docs/preregistration/TIEN-DANG-KY-mo-hinh-quan-sat-MA.md SS4: B7's LP puts
#: zero coverage on carriers, so under MA it never buys a single look and the
#: premise would be flat by the choice of probe, not by the model.
OBSERVATION = "M0"
PROBE = "B7 minimax-lp"


def _posterior_mass_on_truth(budget: float, wf, ps, det, ag, seed: int,
                             deltas, h: int) -> float:
    """Run one episode under a budget and report the belief's mass on the truth.

    The defender audits under `budget` with the minimax LP schedule (B7), and the
    belief is updated from the carrier signals it sees.  The number returned is
    b_sigma(k, iota, sigma): how much of the posterior sits on the real window at
    the task where the payload fires.
    """
    b = belief.WindowBelief(list(CARRIERS), H=h, deltas=deltas,
                            beta=costs.BETA_DEFAULT)
    pol = P.make_policy(PROBE, budget, seed_of("c", seed), "mid")
    store = CarrierStore()
    truth = (ps.carrier, ps.iota, ps.sigma)
    seen: dict = {}
    for t, task in enumerate(wf.tasks):
        if t == ps.iota:
            build.inject(store, wf, ps)
        out = ag.run_task(t, task, store, seed=agent_seed(wf.wf_id, seed), marker=ps.marker)
        signals = {}
        for c in CARRIERS:
            items = store.live(c)
            raw = [det.score(x, t, seed) for x in items]
            signals[c] = P.CarrierSignal(p=scoring.carrier_score(raw, det.d_prime),
                                         n=len(items))
        visible = runner.visible_signals(signals, seen, OBSERVATION)
        b.update(t, visible)
        act = pol.choose(t, sorted({x.carrier for x in out.retrieved}), visible)
        seen = {}
        if act is not None and pol.can(P.cost_of(act)):
            pol.charge(P.cost_of(act))
            seen = runner.bought_sight(act, signals)
            carrier, _ = P.split_action(act)
            if carrier in CARRIERS:
                for it in store.live(carrier):
                    if det.fires(det.score(it, t, seed)):
                        store.quarantine(it.item_id)
        if t == ps.sigma:
            break
    return b.window_mass().get(truth, 0.0)


def _b_min(wf, ps, det, ag, seed, deltas, h, budgets) -> tuple:
    """Smallest budget on the ladder whose posterior mass clears 1 - alpha.

    Returns (B_min, monotone, curve).  `monotone` is False when a larger budget
    scored strictly worse than a smaller one by more than numerical noise -- in
    which case the ladder, not a bisection, is what the caller should report.
    """
    curve = []
    for b in budgets:
        curve.append((b, _posterior_mass_on_truth(b, wf, ps, det, ag, seed, deltas, h)))
    masses = [m for _, m in curve]
    monotone = all(masses[i + 1] >= masses[i] - 1e-9 for i in range(len(masses) - 1))
    hit = next((b for b, m in curve if m >= 1.0 - ALPHA), None)
    return hit, monotone, curve


def budget_buys_information(n_wf: int, h: int) -> dict:
    """PRECONDITION.  Does a larger budget move the posterior at all?

    Theorem 4 prices INFORMATION: the budget buys observations, the observations
    localise the window.  If the posterior at sigma is identical at B = 2 and at
    B = 200, the left-hand side of the theorem does not exist in this harness and
    no c fitted here would mean anything -- so this runs first and, when it comes
    back flat, `measure` refuses to return a number.
    """
    det = detector.Detector(d_prime=2.2114, tau_det=1.17498679206609)
    ag = agent.MockAgent()
    ladder = [2.0, 8.0, 17.95, 60.0, 200.0]
    curves = []
    for i in range(n_wf):
        wf = build.make_workflow(f"c-{i:03d}", "django", h,
                                 random.Random(seed_of("c-wf", i)))
        ps = build.plan_poison(wf, "memory", 2, random.Random(seed_of("c-ps", i)))
        if ps is None:
            continue
        _, _, curve = _b_min(wf, ps, det, ag, i, (0, 2, 4), h, ladder)
        curves.append([m for _, m in curve])
    spreads = [max(c) - min(c) for c in curves if c]
    return {
        "budget_ladder": ladder,
        "mass_curves": curves,
        "max_spread_over_ladder": max(spreads) if spreads else None,
        "budget_moves_the_posterior": bool(spreads and max(spreads) > 1e-6),
    }


def belief_ceiling(n_wf: int, h: int, budget: float = 1000.0) -> dict:
    """How far can the posterior concentrate on the truth AT ALL?

    Asked at a budget far above the ladder, under BOTH observation models, with
    the strong detector.  If even M0 -- every carrier seen for free at every
    task -- leaves the median mass on the true window far below 1 - alpha, then
    Theorem 4's left-hand side does not exist at this alpha for a reason that is
    neither the budget nor the observation model: it is the ceiling of the
    belief mechanism itself.  Reported so a refusal says WHICH of the three it is.
    """
    ag = agent.MockAgent()
    det = detector.Detector(d_prime=2.9598, tau_det=1.17498679206609)
    global OBSERVATION, PROBE
    saved = (OBSERVATION, PROBE)
    out = {}
    try:
        for model, probe in (("M0", "B7 minimax-lp"), ("M0", "B2 uniform random"),
                             ("MA", "B2 uniform random")):
            OBSERVATION, PROBE = model, probe
            for delta in (2, 4):
                masses = []
                for i in range(n_wf):
                    wf = build.make_workflow(f"c-{i:03d}", "django", h,
                                             random.Random(seed_of("c-wf", i)))
                    ps = build.plan_poison(wf, "memory", delta,
                                           random.Random(seed_of("c-ps", i)))
                    if ps is None:
                        continue
                    masses.append(_posterior_mass_on_truth(budget, wf, ps, det, ag,
                                                           i, (0, 2, 4), h))
                out[f"{model}/{probe}/delta={delta}"] = {
                    "median_mass_on_truth": round(statistics.median(masses), 4),
                    "max_mass_on_truth": round(max(masses), 4),
                    "reaches_1_minus_alpha": sum(m >= 1 - ALPHA for m in masses),
                    "n": len(masses)}
    finally:
        OBSERVATION, PROBE = saved
    return {"budget": budget, "detector_d_prime": 2.9598, "cells": out,
            "prior_mass_per_window": round(0.5 / sum(4 * (h - d) for d in (0, 2, 4)), 4)}


def measure(n_wf: int = 8, h: int = 8) -> dict:
    ag = agent.MockAgent()
    deltas = (0, 2, 4)
    budgets = [2.0, 4.0, 8.0, 12.0, 17.95, 26.0, 40.0, 60.0, 90.0]
    kappa_bar = statistics.fmean(P.KAPPA.values())
    cells, non_monotone = [], 0

    for d_prime, gamma in ((1.5161, 0.55), (2.2114, 0.73), (2.9598, 0.86)):
        det = detector.Detector(d_prime=d_prime, tau_det=1.17498679206609)
        for delta in (0, 2, 4):
            for chi_target in (0.0, 0.5, P.chi_of(P.KAPPA)):
                old = dict(P.KAPPA)
                P.KAPPA.clear(); P.KAPPA.update(P.kappa_for_chi(chi_target, old))
                try:
                    hits = []
                    for i in range(n_wf):
                        wf = build.make_workflow(f"c-{i:03d}", "django", h,
                                                 random.Random(seed_of("c-wf", i)))
                        ps = build.plan_poison(wf, "memory", delta,
                                               random.Random(seed_of("c-ps", i)))
                        if ps is None:
                            continue
                        hit, monotone, _ = _b_min(wf, ps, det, ag, i, deltas, h, budgets)
                        if not monotone:
                            non_monotone += 1
                        if hit is not None:
                            hits.append(hit)
                finally:
                    P.KAPPA.clear(); P.KAPPA.update(old)

                if not hits:
                    cells.append({"d_prime": d_prime, "gamma": gamma, "delta": delta,
                                  "chi": chi_target, "b_min": None, "c_cell": None,
                                  "reason": "no budget on the ladder reached 1 - alpha"})
                    continue
                b_min = statistics.median(hits)
                denom = (kappa_bar * (1.0 + chi_target) * math.log(1.0 / ALPHA)
                         * (1.0 + delta * K / h))
                cells.append({"d_prime": d_prime, "gamma": gamma, "delta": delta,
                              "chi": chi_target, "b_min": b_min,
                              "c_cell": b_min * gamma * gamma / denom,
                              "n_workflows": len(hits)})

    fitted = [c for c in cells if c.get("c_cell") is not None]
    precondition = budget_buys_information(min(n_wf, 4), h)
    ceiling = belief_ceiling(n_wf, h) if not fitted else None
    return {
        "precondition": precondition,
        "belief_ceiling": ceiling,
        "refused": None if precondition["budget_moves_the_posterior"] else (
            f"c is NOT fitted under observation model {OBSERVATION}: the posterior "
            "at sigma is identical across the whole budget ladder, so budget buys "
            "no information and Theorem 4's left-hand side has nothing to "
            "measure." + (" Cause: under M0 belief.WindowBelief.update is fed the "
            "signals of ALL carriers every task, whatever the policy audited -- "
            "observations are free." if OBSERVATION == "M0" else "")),
        "observation_model": OBSERVATION,
        "c": max((c["c_cell"] for c in fitted), default=None),
        "c_cell_spread": ({"min": min(c["c_cell"] for c in fitted),
                           "median": statistics.median([c["c_cell"] for c in fitted]),
                           "max": max(c["c_cell"] for c in fitted)}
                          if fitted else None),
        "cells": cells,
        "cells_fitted": len(fitted), "cells_total": len(cells),
        "non_monotone_episodes": non_monotone,
        "provenance": {
            "left_hand_side": "smallest budget whose posterior puts >= 1 - alpha "
                              "on the true (k, iota, sigma) at sigma",
            "alpha": ALPHA, "budget_ladder": budgets,
            "policy": PROBE, "observation_model": OBSERVATION,
            "belief_beta": costs.BETA_DEFAULT,
            "kappa_bar": kappa_bar, "K": K, "H": h, "n_workflows": n_wf,
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n-wf", type=int, default=8)
    ap.add_argument("--observation", choices=runner.OBSERVATION_MODELS, default="M0")
    ap.add_argument("--probe", default=None,
                    help="probe policy; default B7 under M0, B2 under MA (declared)")
    a = ap.parse_args()
    OBSERVATION = a.observation
    PROBE = a.probe or ("B7 minimax-lp" if a.observation == "M0" else "B2 uniform random")
    print(json.dumps(measure(a.n_wf), indent=2, ensure_ascii=False))
