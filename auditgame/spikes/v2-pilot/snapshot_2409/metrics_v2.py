"""metrics_v2.py -- draft SS9.3 metrics on v2 records (D13, D14, D15, D21)."""
from __future__ import annotations

import random

#: D21, declared before any v2 number: a relative gain is READ only if the base policy
#: shows at least this many harm events in its worst column, AND at most this share of
#: bootstrap resamples have a zero base value.  Otherwise it is printed "không đọc được"
#: and only the absolute difference is interpreted.
MIN_BASE_EVENTS = 10
MAX_ZERO_SHARE = 0.01


def harm_table(recs, policy, attacks, deltas) -> dict:
    acc: dict = {}
    for r in recs:
        if r["policy"] == policy and r["attack"] in attacks and r["delta"] in deltas:
            acc.setdefault(f"{r['attack']}@{r['delta']}", {}).setdefault(r["wf"], []).append(r["harm"])
    return {c: {w: sum(v) / len(v) for w, v in d.items()} for c, d in acc.items()}


def value(tab) -> float:
    means = [sum(d.values()) / len(d) for d in tab.values() if d]
    return max(means) if means else float("nan")


def _value_multi(tab, ws) -> float:
    best = 0.0
    for d in tab.values():
        vals = [d[w] for w in ws if w in d]
        if vals:
            best = max(best, sum(vals) / len(vals))
    return best


def gain_ci(recs, base, cand, attacks, deltas, n_boot=10000, seed=2026) -> dict:
    """Relative gain AND absolute harm difference, both with a repo-cluster CI (D14, D4c).

    Near the floor V(base) ~ 0 the relative gain is mostly noise, so the absolute
    difference V(base) - V(cand) is reported beside it, always.  A resample whose base
    value is 0 has no relative gain; it is COUNTED (n_zero_base) rather than silently
    dropped, and the relative CI is marked unreliable when that count is not negligible.
    """
    tb, tc = harm_table(recs, base, attacks, deltas), harm_table(recs, cand, attacks, deltas)
    repo_of = {r["wf"]: r["repo"] for r in recs}
    wfs = sorted({w for d in tb.values() for w in d})
    repos = sorted({repo_of[w] for w in wfs})
    by_repo = {rp: [w for w in wfs if repo_of[w] == rp] for rp in repos}
    vb, vc = value(tb), value(tc)
    point = 100.0 * (vb - vc) / vb if vb else float("nan")
    # D21: harm EVENTS of the base in its worst column -- the pre-declared readability count
    worst_col = max(tb, key=lambda c: sum(tb[c].values()) / len(tb[c])) if tb else None
    events = sum(r["harm"] for r in recs
                 if r["policy"] == base and worst_col == f"{r['attack']}@{r['delta']}")
    rng, rel, dif, zero = random.Random(seed), [], [], 0
    for _ in range(n_boot):
        ws = [w for _ in repos for w in by_repo[repos[rng.randrange(len(repos))]]]
        b, c = _value_multi(tb, ws), _value_multi(tc, ws)
        dif.append(b - c)
        if b > 0:
            rel.append(100.0 * (b - c) / b)
        else:
            zero += 1
    rel.sort()
    dif.sort()

    def q(xs, a):
        return round(xs[int(a * len(xs))], 4) if xs else float("nan")

    return {"gain": round(point, 2), "lo": q(rel, 0.025), "hi": q(rel, 0.975),
            "abs_diff": round(vb - vc, 4), "abs_lo": q(dif, 0.025), "abs_hi": q(dif, 0.975),
            "v_base": round(vb, 4), "v_cand": round(vc, 4),
            "n_zero_base": zero, "base_events": int(events),
            "rel_reliable": vb > 0 and events >= MIN_BASE_EVENTS and zero <= MAX_ZERO_SHARE * n_boot,
            "n_repos": len(repos), "n_workflows": len(wfs)}


def gain_vs_best(recs, baselines, cand, attacks, deltas, n_boot=10000, seed=2026) -> dict:
    """D22: the candidate against the BEST baseline of the cell, as an absolute harm
    difference (positive = candidate better).  The best baseline is re-chosen inside every
    bootstrap resample, so the interval pays for the selection -- conservative against the
    candidate.  Relative gain is not reported: the best baseline may sit near 0."""
    tabs = {b: harm_table(recs, b, attacks, deltas) for b in baselines}
    tc = harm_table(recs, cand, attacks, deltas)
    repo_of = {r["wf"]: r["repo"] for r in recs}
    wfs = sorted({w for d in tc.values() for w in d})
    repos = sorted({repo_of[w] for w in wfs})
    by_repo = {rp: [w for w in wfs if repo_of[w] == rp] for rp in repos}
    vals = {b: value(t) for b, t in tabs.items()}
    best = min(vals, key=lambda b: (vals[b], b))
    vb, vc = vals[best], value(tc)
    rng, dif = random.Random(seed), []
    for _ in range(n_boot):
        ws = [w for _ in repos for w in by_repo[repos[rng.randrange(len(repos))]]]
        b = min(_value_multi(t, ws) for t in tabs.values())
        dif.append(b - _value_multi(tc, ws))
    dif.sort()

    def q(a):
        return round(dif[int(a * len(dif))], 4) if dif else float("nan")

    return {"best_baseline": best, "v_best": round(vb, 4), "v_cand": round(vc, 4),
            "abs_diff": round(vb - vc, 4), "abs_lo": q(0.025), "abs_hi": q(0.975),
            "n_repos": len(repos), "n_workflows": len(wfs)}


def side(recs, policy, attacks, deltas) -> dict:
    rs = [r for r in recs if r["policy"] == policy and r["attack"] in attacks and r["delta"] in deltas]
    solved = sum(r["n_solved"] for r in rs)
    touched = sum(r["benign_touched"] for r in rs)
    delays = [r["detected_at"] - r["iota"] for r in rs
              if r["detected_at"] is not None and r["iota"] is not None]
    means = [sum(d.values()) / len(d) for d in harm_table(recs, policy, attacks, deltas).values() if d]
    return {
        "clean_completion": 100.0 * (1 - sum(r["t_lost"] for r in rs) / solved) if solved else float("nan"),
        "false_quarantine_pct": 100.0 * sum(r["false_objects"] for r in rs) / touched if touched else float("nan"),
        "detection_delay": sum(delays) / len(delays) if delays else float("nan"),
        "exploitability": (max(means) - sum(means) / len(means)) if means else float("nan"),
    }
