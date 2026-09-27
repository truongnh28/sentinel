"""v3/metrics.py -- draft S9.3 metrics on v3 records, the family wild cluster bootstrap, BH,
the learning curve, the controls read first, and the table-rollout fidelity row (plan T17).

RECORDS.  Every function takes api.EpisodeRecord objects or their dicts (to_dict()), so
the JSONL a run writes is read as it is.  Records from two splits never mix (ValueError).
The caller selects ONE cell (world, rho, chi, detector, K_d, budget) per call; the Delta
axis is the only cell axis a call may span (the headline pools Delta in {4, 8}, as v2's
harm_table does).  Two records for one (policy, column, workflow, seed) mean two cells
were mixed, and raise.

WEIGHTS.  Workflow-weighted throughout (plan T17): a workflow's value is the mean over its
seeds, a column's value the mean over the workflows present in it (metrics_v2.harm_table),
and every side metric is a per-workflow rate averaged over workflows.  v2's pooled
side() is returned beside it under "v2_pooled" as a cross-check.

WORST-CASE HARM V (draft S9.3 "maximum over the held-out attacker class").  V = max over
attacker columns (attack@delta) of the column's workflow-weighted mean harm, which is
metrics_v2.value(metrics_v2.harm_table(...)).

INTERVALS (draft S12 "cluster-bootstrapped by repository family"; sentinel-v3.md S9: wild
cluster bootstrap, Cameron-Gelbach-Miller, because there are only ~18-20 families).
The cluster is the record's `repo` (the repository family).  Declared before any v3
number (R6):

    wild   (primary)  W[w, c] = mu_c + e[w, c], with mu_c the column mean over the workflows
           present and e the workflow's residual.  One draw multiplies every residual of
           family g by the same Webb six-point weight v_g (+-sqrt(1/2), +-1, +-sqrt(3/2),
           each 1/6), for EVERY system of the call at once (paired), and re-takes
           V* = max_c (mu_c + sum_w v_g(w) e[w, c] / n_c) in every draw (D14): the interval
           pays for the choice of the worst column.  V* is floored at 0 (harm >= 0), as
           metrics_v2._value_multi does.
    pairs  (R6 fallback, printed beside wild if its plasmode coverage is poor)
           families drawn with replacement, v2's gain_ci as a vectorised port of
           tools/v3_p0_precision.gain_ci_np (not imported: plan S2 keeps v3 off v2 tools).

    The interval is the percentile interval of the draws, with metrics_v2._q's index
    convention; the bootstrap p-value of "estimate = 0" is 2 x the smaller tail share, so
    p < alpha exactly when the (1 - alpha) interval excludes 0.

    Draws come from numpy Generators seeded by core.seed_of("v3.metrics", method, seed).

RELIABILITY (D21 of v2, kept): a relative gain is READ only if the base shows at least
metrics_v2.MIN_BASE_EVENTS harm events in its worst column and at most
metrics_v2.MAX_ZERO_SHARE of the draws have a zero base value; otherwise only the absolute
difference is read (`rel_reliable`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import core
import metrics_v2 as MV
from v3 import config as C

N_BOOT = 10000
BOOT_SEED = 2026
ALPHA = 0.05
METHODS = ("wild", "pairs")
#: Webb (2014) six-point weights: mean 0, variance 1, symmetric.
WEBB = np.array([-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)])
#: D28: the positive control's ceiling at the headline Deltas (v2's value, not restated).
CONTROL_MAX_HARM = MV.CONTROL_MAX_HARM
#: T17 fidelity row: a headline number is labelled with this above config.TABLE_ROLLOUT_FLAG.
FIDELITY_LABEL = "bảng lệch rollout"

NAN = float("nan")


# ---------------------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------------------

def rows(recs) -> list:
    """Dicts from EpisodeRecord objects or dicts; one split only."""
    out = [r if isinstance(r, dict) else r.to_dict() for r in recs]
    splits = {r.get("split") for r in out}
    if len(splits) > 1:
        raise ValueError(f"records from several splits in one call: {sorted(map(str, splits))}")
    return out


def column(r) -> str:
    """The attacker column: attack@delta, as metrics_v2."""
    return f"{r['attack']}@{r['delta']}"


def pick(recs, policy, attacks, deltas) -> list:
    attacks, deltas = set(attacks), set(deltas)
    return [r for r in rows(recs)
            if r["policy"] == policy and r["attack"] in attacks and r["delta"] in deltas]


def _is_finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


# ---------------------------------------------------------------------------------------
# The workflow x column matrix (metrics_v2.harm_table as an array)
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Table:
    """W[w, c]: mean over seeds of `field` for workflow wfs[w] in column cols[c]; NaN when
    the workflow has no record in that column.  `events[c]` = the sum of `field` over the
    column's records (D21 counts harm events there)."""
    policy: str
    wfs: tuple
    cols: tuple
    W: np.ndarray
    repo_of: dict
    events: dict
    n_records: int

    def column_means(self) -> np.ndarray:
        m = ~np.isnan(self.W)
        den = m.sum(0)
        return np.where(den > 0, np.nan_to_num(self.W).sum(0) / np.maximum(den, 1), -np.inf)

    @property
    def value(self) -> float:
        """V: max over columns of the workflow-weighted column mean (metrics_v2.value)."""
        if not self.cols:
            return NAN
        return float(self.column_means().max())

    @property
    def worst_column(self) -> str | None:
        if not self.cols:
            return None
        means = self.column_means()
        return self.cols[int(np.argmax(means))]


def table(recs, policy, attacks, deltas, field="harm") -> Table:
    rs = pick(recs, policy, attacks, deltas)
    acc: dict = {}
    seen = set()
    repo_of: dict = {}
    for r in rs:
        key = (column(r), r["wf"], r["seed"])
        if key in seen:
            raise ValueError(f"two records for one episode {key} of {policy!r}: the call "
                             "mixes cells (select one world / rho / chi / detector / K_d / "
                             "budget per call)")
        seen.add(key)
        if repo_of.setdefault(r["wf"], r["repo"]) != r["repo"]:
            raise ValueError(f"workflow {r['wf']} is in two families")
        acc.setdefault(column(r), {}).setdefault(r["wf"], []).append(r[field])
    cols = tuple(sorted(acc))
    wfs = tuple(sorted({w for d in acc.values() for w in d}))
    W = np.full((len(wfs), len(cols)), np.nan)
    iw = {w: i for i, w in enumerate(wfs)}
    for j, c in enumerate(cols):
        for w, v in acc[c].items():
            W[iw[w], j] = sum(v) / len(v)
    events = {c: float(sum(sum(v) for v in acc[c].values())) for c in cols}
    return Table(policy, wfs, cols, W, repo_of, events, len(rs))


def worst_case_harm(recs, policy, attacks, deltas) -> dict:
    """Draft S9.3 primary: V and the column that attains it."""
    t = table(recs, policy, attacks, deltas)
    return {"v": t.value, "worst_column": t.worst_column, "n_workflows": len(t.wfs),
            "n_columns": len(t.cols), "n_records": t.n_records}


# ---------------------------------------------------------------------------------------
# The bootstrap engine
# ---------------------------------------------------------------------------------------

def rng_for(method: str, seed: int) -> np.random.Generator:
    return np.random.default_rng(core.seed_of("v3.metrics", method, seed))


def family_draws(n_fam: int, n_boot: int, rng: np.random.Generator, method: str) -> np.ndarray:
    """(n_boot x n_fam).  wild: one Webb weight per family per draw.  pairs: how often each
    family is drawn when n_fam families are drawn with replacement."""
    if method == "wild":
        return WEBB[rng.integers(len(WEBB), size=(n_boot, n_fam))]
    if method == "pairs":
        draw = rng.integers(n_fam, size=(n_boot, n_fam))
        out = np.zeros((n_boot, n_fam))
        np.add.at(out, (np.arange(n_boot)[:, None], draw), 1.0)
        return out
    raise ValueError(f"method={method!r} is not one of {METHODS}")


def boot_value(W: np.ndarray, fam: np.ndarray, F: np.ndarray, method: str) -> np.ndarray:
    """V* for every draw: max over columns of the re-weighted column mean, floored at 0."""
    m = ~np.isnan(W)
    X = np.nan_to_num(W)
    per_wf = F[:, fam]                                      # n_boot x n_wf
    if method == "pairs":
        num, den = per_wf @ X, per_wf @ m.astype(float)
        col = np.where(den > 0, num / np.where(den > 0, den, 1.0), -np.inf)
    elif method == "wild":
        n_c = m.sum(0)
        mu = np.where(n_c > 0, X.sum(0) / np.maximum(n_c, 1), 0.0)
        E = np.where(m, X - mu, 0.0)
        col = np.where(n_c > 0, mu + (per_wf @ E) / np.maximum(n_c, 1), -np.inf)
    else:
        raise ValueError(f"method={method!r} is not one of {METHODS}")
    if col.shape[1] == 0:
        return np.full(col.shape[0], np.nan)
    return np.maximum(0.0, col.max(1))


@dataclass(frozen=True)
class Boot:
    """Point values and bootstrap draws of V for several systems on COMMON family draws."""
    point: dict                     # name -> V
    draws: dict                     # name -> (n_boot,) V*
    families: tuple
    workflows: tuple
    method: str
    n_boot: int
    seed: int
    F: np.ndarray                   # the family draws (n_boot x n_fam), for tests


def boot_values(tables: dict, n_boot=N_BOOT, seed=BOOT_SEED, method="wild") -> Boot:
    """tables: name -> Table.  The workflows of every table are aligned on their union;
    one family draw per resample is shared by every table (paired)."""
    repo_of: dict = {}
    for t in tables.values():
        for w, rp in t.repo_of.items():
            if repo_of.setdefault(w, rp) != rp:
                raise ValueError(f"workflow {w} is in two families")
    wfs = tuple(sorted(repo_of))
    fams = tuple(sorted(set(repo_of.values())))
    ifam = {f: i for i, f in enumerate(fams)}
    fam = np.array([ifam[repo_of[w]] for w in wfs], dtype=int)
    F = family_draws(len(fams), n_boot, rng_for(method, seed), method)
    iw = {w: i for i, w in enumerate(wfs)}
    point, draws = {}, {}
    for name, t in tables.items():
        W = np.full((len(wfs), len(t.cols)), np.nan)
        for i, w in enumerate(t.wfs):
            W[iw[w]] = t.W[i]
        point[name] = t.value
        draws[name] = boot_value(W, fam, F, method)
    return Boot(point, draws, fams, wfs, method, n_boot, seed, F)


def quantile(xs, a) -> float:
    """metrics_v2._q without its rounding: xs sorted, index int(a * n)."""
    return float(xs[min(len(xs) - 1, int(a * len(xs)))]) if len(xs) else NAN


def interval(draws, alpha=ALPHA) -> tuple:
    """Percentile interval of the finite draws."""
    xs = np.sort(np.asarray(draws, dtype=float))
    xs = xs[np.isfinite(xs)]
    return quantile(xs, alpha / 2), quantile(xs, 1 - alpha / 2)


def p_value(draws, null=0.0) -> float:
    """Two-sided bootstrap p of `estimate = null`: 2 x the smaller tail share."""
    xs = np.asarray(draws, dtype=float)
    xs = xs[np.isfinite(xs)]
    if not len(xs):
        return NAN
    return float(min(1.0, 2.0 * min(np.mean(xs <= null), np.mean(xs >= null))))


# ---------------------------------------------------------------------------------------
# Gain and absolute difference (Table 2, S9.4)
# ---------------------------------------------------------------------------------------

def _empty_gain(alpha, method, n_boot) -> dict:
    return {"gain": NAN, "lo": NAN, "hi": NAN, "abs_diff": NAN, "abs_lo": NAN, "abs_hi": NAN,
            "alpha": alpha, "v_base": NAN, "v_cand": NAN, "n_zero_base": 0, "base_events": 0,
            "rel_reliable": False, "n_repos": 0, "n_workflows": 0, "method": method,
            "n_boot": n_boot, "p_abs": NAN, "p_rel": NAN}


def gain_ci(recs, base, cand, attacks, deltas, n_boot=N_BOOT, seed=BOOT_SEED, alpha=ALPHA,
            method="wild", return_draws=False) -> dict:
    """Relative gain 100 (V_base - V_cand) / V_base and absolute difference V_base - V_cand,
    each with a family-cluster bootstrap interval re-maxed over columns in every draw.
    The keys of metrics_v2.gain_ci, plus method, n_boot, p_abs, p_rel."""
    rs = rows(recs)
    tb, tc = table(rs, base, attacks, deltas), table(rs, cand, attacks, deltas)
    if not tb.cols or not tc.cols:
        return _empty_gain(alpha, method, n_boot)
    bt = boot_values({"base": tb, "cand": tc}, n_boot, seed, method)
    vb, vc = bt.point["base"], bt.point["cand"]
    b, c = bt.draws["base"], bt.draws["cand"]
    dif = b - c
    pos = b > 0
    rel = 100.0 * (b[pos] - c[pos]) / b[pos]
    zero = int((~pos).sum())
    events = tb.events[tb.worst_column]
    lo, hi = interval(rel, alpha)
    alo, ahi = interval(dif, alpha)
    out = {"gain": 100.0 * (vb - vc) / vb if vb else NAN, "lo": lo, "hi": hi,
           "abs_diff": vb - vc, "abs_lo": alo, "abs_hi": ahi, "alpha": alpha,
           "v_base": vb, "v_cand": vc, "n_zero_base": zero, "base_events": int(events),
           "rel_reliable": bool(vb > 0 and events >= MV.MIN_BASE_EVENTS
                                and zero <= MV.MAX_ZERO_SHARE * n_boot),
           "n_repos": len(bt.families), "n_workflows": len(bt.workflows),
           "method": method, "n_boot": n_boot, "p_abs": p_value(dif), "p_rel": p_value(rel)}
    if return_draws:
        out["draws"] = {"base": b, "cand": c, "rel": rel, "abs": dif, "F": bt.F}
    return out


def gain_ci_both(recs, base, cand, attacks, deltas, **kw) -> dict:
    """R6: wild (primary) and pairs side by side, never the prettier of the two."""
    return {m: gain_ci(recs, base, cand, attacks, deltas, method=m, **kw) for m in METHODS}


# ---------------------------------------------------------------------------------------
# Side metrics (S9.3), workflow-weighted
# ---------------------------------------------------------------------------------------

def _n_audits(v) -> int:
    return len(v) if isinstance(v, (list, tuple, set)) else int(v)


def _wf_mean(per_wf: dict) -> float:
    vals = [v for v in per_wf.values() if _is_finite(v)]
    return sum(vals) / len(vals) if vals else NAN


def side(recs, policy, attacks, deltas) -> dict:
    """Clean completion, false quarantine (carrier-level fq, O7; item-level false_removed,
    v2 D15), audit cost, detection delay -- each a per-workflow rate averaged over
    workflows, over every column and seed of the selection."""
    rs = pick(recs, policy, attacks, deltas)
    by: dict = {}
    for r in rs:
        by.setdefault(r["wf"], []).append(r)
    cc, fqp, fq_ep, fq_share, fr_ep, cost, cost_share, delay, det_rate = ({} for _ in range(9))
    targets = C.TARGETS
    per_target = {t: {} for t in targets}
    quar_by_carrier = {k: {} for k in C.CARRIERS}
    for w, g in by.items():
        solved = sum(r["n_solved"] for r in g)
        cc[w] = 100.0 * (1 - sum(r["t_lost"] for r in g) / solved) if solved else NAN
        insp = sum(r["benign_inspected"] for r in g)
        fqp[w] = 100.0 * sum(r["false_removed"] for r in g) / insp if insp else NAN
        fq_ep[w] = sum(r["fq"] for r in g) / len(g)
        nq = sum(r["fq"] + r["true_q"] for r in g)
        fq_share[w] = 100.0 * sum(r["fq"] for r in g) / nq if nq else NAN
        fr_ep[w] = sum(r["false_removed"] for r in g) / len(g)
        cost[w] = sum(r["spent"] for r in g) / len(g)
        bud = [r["spent"] / r["budget"] for r in g if r["budget"]]
        cost_share[w] = 100.0 * sum(bud) / len(bud) if bud else NAN
        for t in targets:
            per_target[t][w] = sum(_n_audits(r["audits"].get(t, 0)) for r in g) / len(g)
        for k in C.CARRIERS:
            quar_by_carrier[k][w] = sum(sum(1 for q in r["quarantines"] if q[1] == k)
                                        for r in g) / len(g)
        d = [r["detected_at"] - r["iota"] for r in g
             if r["detected_at"] is not None and r["iota"] is not None]
        delay[w] = sum(d) / len(d) if d else NAN
        att = [r for r in g if r["iota"] is not None]
        det_rate[w] = 100.0 * sum(r["detected_at"] is not None for r in att) / len(att) if att else NAN
    return {
        "clean_completion": _wf_mean(cc),
        "false_quarantine_pct": _wf_mean(fqp),               # item level (v2 D15)
        "false_removed_per_ep": _wf_mean(fr_ep),
        "fq_per_ep": _wf_mean(fq_ep),                        # carrier level (O7)
        "fq_share_of_quarantines_pct": _wf_mean(fq_share),
        "audit_cost": _wf_mean(cost),                        # CPU-minutes per episode
        "audit_cost_share_pct": _wf_mean(cost_share),
        "audits_per_ep": {t: _wf_mean(v) for t, v in per_target.items()},
        "quarantines_per_ep": {k: _wf_mean(v) for k, v in quar_by_carrier.items()},
        "detection_delay": _wf_mean(delay),
        "detection_rate_pct": _wf_mean(det_rate),
        "n_workflows": len(by), "n_episodes": len(rs),
        "v2_pooled": MV.side(rs, policy, set(attacks), set(deltas)),
    }


# ---------------------------------------------------------------------------------------
# Exploitability (S9.3) and regret against B7 (S9.3, small games)
# ---------------------------------------------------------------------------------------

def v_best_response(recs, policy, deltas) -> dict:
    """D27: the cross-fitted value against the best-response attacker.  BR records are the
    policy's records with a `placement`; V_BR is the max over the Deltas whose cross-fitted
    value is finite (a NaN one is listed, never compared)."""
    rs = [r for r in rows(recs) if r["policy"] == policy and r["placement"] is not None
          and r["delta"] in set(deltas)]
    by_delta = {}
    for d in sorted(set(deltas), key=str):
        sel = [{"wf": r["wf"], "placement": r["placement"], "seed": r["seed"], "harm": r["harm"]}
               for r in rs if r["delta"] == d]
        if sel:
            by_delta[d] = MV.crossfit_value(sel)["v_br"]
    ok = [v for v in by_delta.values() if _is_finite(v)]
    return {"v_br": max(ok) if ok else NAN, "v_br_by_delta": {str(d): v for d, v in by_delta.items()},
            "v_br_nan_deltas": sorted(str(d) for d, v in by_delta.items() if not _is_finite(v))}


def exploitability(recs, policy, heldout, deltas) -> dict:
    """Draft S9.3 "best-response gain against the deployed policy": V_BR - V_held-out, as
    v2's Table 2 (tools/run_draft_eval._table2_row)."""
    v = table(recs, policy, heldout, deltas).value
    br = v_best_response(recs, policy, deltas)
    ex = br["v_br"] - v if _is_finite(v) and _is_finite(br["v_br"]) else NAN
    return {"exploitability": ex, "v_heldout": v, **br}


def regret_vs_b7(recs, policy, b7="B7", tol=1e-9) -> dict:
    """Draft S9.3 "Empirical regret against B7 on small games".  Each small game is one
    workflow: regret_w = V_w(policy) - V_w(B7), with V_w the max over the game's attacker
    columns of the mean over seeds.  A regret below -tol means the ceiling was computed on
    another object than the policy (game.regret); it is counted, never clipped."""
    rs = rows(recs)
    def per_wf(p):
        acc: dict = {}
        for r in rs:
            if r["policy"] == p:
                acc.setdefault(r["wf"], {}).setdefault(column(r), []).append(r["harm"])
        return {w: max(sum(v) / len(v) for v in d.values()) for w, d in acc.items()}
    vp, vb = per_wf(policy), per_wf(b7)
    common = sorted(set(vp) & set(vb))
    reg = [vp[w] - vb[w] for w in common]
    return {"regret_mean": sum(reg) / len(reg) if reg else NAN,
            "regret_max": max(reg) if reg else NAN,
            "n_negative": sum(x < -tol for x in reg), "n_games": len(reg),
            "missing_b7": sorted(set(vp) - set(vb))}


def seven_metrics(recs, policy, heldout, deltas, small_game_recs=None, b7="B7") -> dict:
    """The seven S9.3 metrics of one system in one cell (Table 2 row)."""
    v = worst_case_harm(recs, policy, heldout, deltas)
    s = side(recs, policy, heldout, deltas)
    ex = exploitability(recs, policy, heldout, deltas)
    rg = (regret_vs_b7(small_game_recs, policy, b7) if small_game_recs is not None
          else {"regret_mean": NAN, "regret_max": NAN, "n_negative": 0, "n_games": 0,
                "missing_b7": []})
    return {"worst_case_harm": v["v"], "worst_column": v["worst_column"],
            "clean_completion": s["clean_completion"],
            "false_quarantine_pct": s["false_quarantine_pct"], "fq_per_ep": s["fq_per_ep"],
            "false_removed_per_ep": s["false_removed_per_ep"],
            "audit_cost": s["audit_cost"], "detection_delay": s["detection_delay"],
            "exploitability": ex["exploitability"], "v_br": ex["v_br"],
            "regret_vs_b7": rg["regret_mean"], "regret_max": rg["regret_max"],
            "side": s, "regret": rg, "n_workflows": v["n_workflows"]}


# ---------------------------------------------------------------------------------------
# Benjamini-Hochberg (sentinel-v3.md S9: q = 0.05)
# ---------------------------------------------------------------------------------------

def bh(pvals, q=C.BH_Q) -> dict:
    """Benjamini-Hochberg step-up.  A NaN p (no test possible) counts in m as p = 1:
    conservative, and never rejected.  Returns reject flags and adjusted p in input order."""
    p = [1.0 if not _is_finite(x) else float(x) for x in pvals]
    m = len(p)
    if not m:
        return {"reject": [], "p_adj": [], "k": 0, "threshold": NAN, "q": q, "m": 0}
    order = sorted(range(m), key=lambda i: p[i])
    k = 0
    for rank, i in enumerate(order, start=1):
        if p[i] <= rank * q / m:
            k = rank
    reject = [False] * m
    for i in order[:k]:
        reject[i] = True
    adj = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, p[i] * m / rank)
        adj[i] = min(1.0, running)
    return {"reject": reject, "p_adj": adj, "k": k,
            "threshold": k * q / m if k else 0.0, "q": q, "m": m}


# ---------------------------------------------------------------------------------------
# Learning curve (line 1, C12, R4, R5)
# ---------------------------------------------------------------------------------------

def learning_curve(recs, policy, attacks, deltas) -> list:
    """One row per number of post-mortems seen: Delta-hat and harm along the pinned order.
    Row 0 is the prior-only workflow (R4), reported apart."""
    rs = pick(recs, policy, attacks, deltas)
    by: dict = {}
    for r in rs:
        by.setdefault(r["n_incidents_seen"], []).append(r)
    out = []
    for n in sorted(by):
        g = by[n]
        wf_h: dict = {}
        for r in g:
            wf_h.setdefault(r["wf"], []).append(r["harm"])
        dh = [r["delta_hat"] for r in g if r["delta_hat"] is not None]
        exact = [r["delta_hat"] == r["delta"] for r in g
                 if r["delta_hat"] is not None and isinstance(r["delta"], int)]
        out.append({"n_incidents_seen": n, "n_episodes": len(g), "n_workflows": len(wf_h),
                    "mean_harm": _wf_mean({w: sum(v) / len(v) for w, v in wf_h.items()}),
                    "mean_delta_hat": sum(dh) / len(dh) if dh else NAN,
                    "delta_hat_exact_pct": 100.0 * sum(exact) / len(exact) if exact else NAN,
                    "prior_only": n == 0})
    return out


def with_postmortems(recs, min_seen=1) -> list:
    """R5: the records whose workflow had at least `min_seen` post-mortems before it."""
    return [r for r in rows(recs) if r["n_incidents_seen"] >= min_seen]


# ---------------------------------------------------------------------------------------
# Controls first (D28)
# ---------------------------------------------------------------------------------------

class ControlsNotRead(RuntimeError):
    """A Sentinel number was asked for before the controls were read."""


class ControlsFailed(RuntimeError):
    """The controls were read and failed: fix the world, do not read Sentinel (M1)."""


def is_sentinel(policy: str) -> bool:
    return str(policy).startswith("Sentinel")


class Readout:
    """Reads a run's numbers with the D28 controls first.  Baseline numbers may be read at
    any time; any number of a Sentinel-class system (is_sentinel) raises ControlsNotRead
    until controls() has run, and ControlsFailed if they failed."""

    def __init__(self, recs):
        self.recs = rows(recs)
        self._controls = None

    def controls(self, oracle, b1, sweepers, attacks, headline_deltas=C.HEADLINE_DELTAS,
                 zero_delta=0) -> dict:
        """(+) the oracle reaches CONTROL_MAX_HARM at the headline Deltas;
        (-) at Delta = 0 no sweep-only baseline beats B1 (metrics_v2.controls)."""
        v_or = table(self.recs, oracle, attacks, headline_deltas).value
        v_b1 = table(self.recs, b1, attacks, (zero_delta,)).value
        v_sw = {s: table(self.recs, s, attacks, (zero_delta,)).value for s in sweepers}
        res = MV.controls(v_or, v_b1, v_sw)
        finite = _is_finite(v_or) and _is_finite(v_b1) and all(map(_is_finite, v_sw.values()))
        if not finite:
            res = {**res, "positive_ok": False, "negative_ok": False, "ok": False,
                   "reason": "a control has no record"}
        self._controls = res
        return res

    def _guard(self, *policies) -> None:
        if not any(is_sentinel(p) for p in policies):
            return
        if self._controls is None:
            raise ControlsNotRead("D28: read the controls (Oracle at the headline Deltas, "
                                  "sweepers vs B1 at Delta = 0) before any Sentinel number")
        if not self._controls["ok"]:
            raise ControlsFailed(f"D28 controls failed: {self._controls}")

    def worst_case_harm(self, policy, attacks, deltas) -> dict:
        self._guard(policy)
        return worst_case_harm(self.recs, policy, attacks, deltas)

    def side(self, policy, attacks, deltas) -> dict:
        self._guard(policy)
        return side(self.recs, policy, attacks, deltas)

    def seven_metrics(self, policy, heldout, deltas, **kw) -> dict:
        self._guard(policy)
        return seven_metrics(self.recs, policy, heldout, deltas, **kw)

    def gain_ci(self, base, cand, attacks, deltas, **kw) -> dict:
        self._guard(base, cand)
        return gain_ci(self.recs, base, cand, attacks, deltas, **kw)


# ---------------------------------------------------------------------------------------
# Table-rollout fidelity (Q13, R2): printed, not a hypothesis
# ---------------------------------------------------------------------------------------

def table_rollout_fidelity(recs, policy, attacks, deltas, n_boot=N_BOOT, seed=BOOT_SEED,
                           alpha=ALPHA, method="wild") -> dict:
    """|V_table - V_rollout| of one system in one headline cell, from its records with
    line5_source 'table' and 'rollout', on common family draws.  `flag` when the point gap
    exceeds config.TABLE_ROLLOUT_FLAG: the headline number then carries FIDELITY_LABEL."""
    rs = rows(recs)
    tab = table([r for r in rs if r["line5_source"] == "table"], policy, attacks, deltas)
    rol = table([r for r in rs if r["line5_source"] == "rollout"], policy, attacks, deltas)
    if not tab.cols or not rol.cols:
        return {"policy": policy, "v_table": tab.value, "v_rollout": rol.value, "diff": NAN,
                "abs_diff": NAN, "lo": NAN, "hi": NAN, "abs_lo": NAN, "abs_hi": NAN,
                "flag": False, "label": "", "n_workflows": 0, "note": "a source has no record"}
    bt = boot_values({"table": tab, "rollout": rol}, n_boot, seed, method)
    d = bt.draws["table"] - bt.draws["rollout"]
    diff = bt.point["table"] - bt.point["rollout"]
    lo, hi = interval(d, alpha)
    alo, ahi = interval(np.abs(d), alpha)
    flag = abs(diff) > C.TABLE_ROLLOUT_FLAG
    return {"policy": policy, "v_table": bt.point["table"], "v_rollout": bt.point["rollout"],
            "diff": diff, "abs_diff": abs(diff), "lo": lo, "hi": hi, "abs_lo": alo,
            "abs_hi": ahi, "flag": flag, "label": FIDELITY_LABEL if flag else "",
            "n_workflows": len(bt.workflows), "method": method, "alpha": alpha, "note": ""}


def fidelity_line(row: dict) -> str:
    """The printed row.  It is not a hypothesis and has no verdict."""
    s = (f"table-rollout fidelity (not a hypothesis) {row['policy']}: "
         f"V_table {row['v_table']:.4f}, V_rollout {row['v_rollout']:.4f}, "
         f"|V_table - V_rollout| = {row['abs_diff']:.4f} "
         f"[{row['abs_lo']:.4f}, {row['abs_hi']:.4f}]; signed {row['diff']:+.4f} "
         f"[{row['lo']:+.4f}, {row['hi']:+.4f}]")
    if row["flag"]:
        s += f"  ** {row['label']} (> {C.TABLE_ROLLOUT_FLAG:g}) **"
    return s
