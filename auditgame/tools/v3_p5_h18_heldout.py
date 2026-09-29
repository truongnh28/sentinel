"""tools/v3_p5_h18_heldout.py -- H18 and H19 on the HELD-OUT (eval) records, P5.

WHY THIS FILE EXISTS.  The dev H18/H19 verdicts (spikes/v3-run/h_verdicts.json, reported in
docs/reports/v3-p2-headline-dual-metric.md section 10) were produced by a script that was
never saved.  This module is that script, written down, so the held-out side is reproducible
and so the next run does not have to re-derive the method from a report.

IT RUNS NOTHING.  This is a pure analysis over records already on disk: no simulation, no
table build, no tuning, and above all NO eval run -- tools/v3_run.py is never invoked, the
unseal log is never appended to, no grant is consumed.  It reads
seal/freeze digests only to refuse if the frozen configuration moved.

IT IS OUTSIDE THE FROZEN SURFACE.  freeze_v3.FILES pins reference/v3_tuned.json and the four
v3 run tools (v3_run, v3_tune, v3_build_table, v3_headline_rollout); freeze_v3 hashes v3/*.py
and v3/dcm/**; freeze.SOURCE/TABLES pin the v2 surface.  This file is none of them, so
creating it leaves the v3 manifest at sha256:9c4c0d018b18 (Gate 4's signed pin) and the base
freeze at sha256:c789fa7362e0.  Checked by --check-freeze, which this module runs first.

METHOD (replicated from the dev side, not re-specified; nothing here rewrites a metric).
  * every number comes from v3/metrics.py and v3/scorecard.py verbatim: metrics.table,
    boot_values, interval, p_value, gain_ci, h18_miss_curve, h18_miss_change,
    scorecard.Estimate / score_all / rule_D_family.
  * wild cluster bootstrap (Webb weights) by repo family, N = 10000, alpha = 0.05, re-max
    over attacker columns per draw, one family draw shared by every table of a call.
  * BH: scorecard.score_all, q = 0.05, ONE family per (metric, rho) -- the H frame's HEAD
    says "each rho", so each rho is a separate instance of the same check.  With H18 and H19
    the only D checks with an estimate, m = 2, as on dev.
  * V(harm): field="harm".  V(L): Definition 1, L = harm + lambda_Q fq + lambda_T t_lost
    (runner.loss_of).  metrics.gain_ci hard-codes field="harm", so for L the scored field is
    RELABELLED (row["harm"] <- L) rather than the function copied; _alias_check proves the
    relabelled path and table(..., field="loss") give the same float.
  * H18: rule D on the sign of V_miss(Delta = 8) - V_miss(Delta = 4) at the declared fixed
    budget level b1, frontier = the lowest miss rate over the H18 policies present, re-taken
    in every draw, worst held-out column, workflows with H >= 9.
    SIGN CONVENTION: the quantity is d8 MINUS d4.  Draft (Theorem 4 as printed: the budget
    must grow with Delta) predicts +1; the note (Thm 5.6: the minimum budget falls like
    H/Delta) predicts -1.  Both sides share one test, one p, one BH slot.
  * H19: gain_slope_in_kd = gain(K_d = 3) - gain(K_d = 1) vs B1 in the headline cell
    (Delta in {4, 8}), the four tables (B1/Sentinel x K_d in {1,3}) on ONE set of family
    draws so the difference is drawn paired.  K_d = 2 is read from the main block for the
    third point (O15: K_d != 2 reuses the primary world's line-5 table).

THE CARRIED DEVIATION (dev's first declared deviation, which holds identically on eval).
  The h18 block has NO b1 level: grid.py emits the b1 unit of the H18 arm only for
  BlockSchedule, which is not one of the fifteen systems the run declares, so B1 / B2 /
  Sentinel at b1 live in the `main` block.  H18_CRITERION nonetheless declares
  fixed_level = "b1".  So b1 is read from the eval main block
  (spikes/v3-run/eval-pass1/main.jsonl), exactly as dev read it from dev-headline-main, and
  the frontier covers 3 of the 4 H18 policies (block-schedule absent).  That run directory
  has no summary.json -- the command was killed later, during the `br` block -- so its
  comparability is established from the records themselves; see _main_comparability.

USAGE
    ../.venv/bin/python tools/v3_p5_h18_heldout.py --check-freeze
    ../.venv/bin/python tools/v3_p5_h18_heldout.py --run
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import subprocess
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent            # auditgame/
sys.path.insert(0, str(ROOT))

import freeze                                                     # noqa: E402
import costs                                                      # noqa: E402
import policies as P2                                             # noqa: E402
from v3 import attackers as A                                     # noqa: E402
from v3 import config as C                                        # noqa: E402
from v3 import freeze_v3                                          # noqa: E402
from v3 import grid as G                                          # noqa: E402
from v3 import metrics as M                                       # noqa: E402
from v3 import runner as R                                        # noqa: E402
from v3 import scorecard as SC                                    # noqa: E402

RUN = ROOT / "spikes" / "v3-run"
H18KD = RUN / "eval-p1-h18kd"
MAIN = RUN / "eval-pass1" / "main.jsonl"
#: --dev-selfcheck reads the DEV blocks instead, to prove this script's method reproduces
#: the dev numbers of h_verdicts.json bit for bit (the dev script itself was never saved).
DEV_H18KD = RUN / "dev-headline-rest"
DEV_MAIN = RUN / "dev-headline-main" / "main.jsonl"
DEV_VERDICTS = RUN / "h_verdicts.json"
OUT_JSON = RUN / "h_verdicts_eval.json"
GATE4 = ROOT / "frozen" / "V3-GATE4.json"

#: What must not have moved.  Gate 4's signed pins.
PIN_V3_MANIFEST = "9c4c0d018b1869941e35e5fe1ebe54bfa3f872b7d4adfb4194c66a2ef5c0eeb6"
PIN_RULES = "21b8c093254abbff09876db07b5b5eca19034b71457434a56f270dea171c840c"
PIN_GRID = "acbe9bdc48fd49a6f49e76f9cbc003a4d50b3341d27d3ca0ede6d85d62fd4e64"
PIN_BASE_HEADER = "freeze: clean sha256:c789fa7362e0"

HELD_OUT = tuple(A.held_out())
H18_POLICIES = tuple(G.H18_POLICIES)
DELTAS = M.H18_DELTA_PAIR                       # (4, 8)
HEAD_DELTAS = tuple(C.HEADLINE_DELTAS)          # (4, 8)
RHOS = (0.0, 0.25, 0.5, 1.0)
LEVELS = tuple(C.BUDGET_LEVELS)                 # b1, 2xBmin, 1xBmin, 0.5xBmin
KD_PAIR = (1, 3)
KD_MAIN = 2
B1 = "B1 audit-at-commit"
SENTINEL = "Sentinel"
#: the 21 fields the metrics read, and nothing else: c_traj / audits / quarantines / world /
#: decision_log_sha256 never enter memory (dev's deviation 5, same discipline).
KEEP = ("policy", "wf", "repo", "seed", "split", "attack", "delta", "harm", "fq", "t_lost",
        "sigma", "H", "missed_before_sigma")
NAN = float("nan")


# ---------------------------------------------------------------------------------------
# Guards: the frozen configuration must not have moved, and no eval run may happen here
# ---------------------------------------------------------------------------------------

def _base_header() -> str:
    """freeze.header_line() read through the operating installation, as every v2 run reads
    it (freeze_v3._with_costs does the same); a bare interpreter shows spurious drift."""
    old = costs.install(P2)
    try:
        return freeze.header_line()
    finally:
        costs.restore(P2, old)


def check_freeze(strict=True) -> dict:
    v3_line, base_line = freeze_v3.header_line(), _base_header()
    gate = json.loads(GATE4.read_text())
    got = {
        "freeze_v3_header": v3_line,
        "freeze_base_header": base_line,
        "v3_manifest_live": freeze_v3.digest(),
        "rules_digest_live": SC.rules_digest(),
        "grid_digest_live": G.definition_digest(),
        "gate4": gate,
    }
    bad = []
    if not freeze_v3.clean(v3_line):
        bad.append(f"v3 freeze not clean: {v3_line}")
    if base_line != PIN_BASE_HEADER:
        bad.append(f"base freeze moved: {base_line!r} != {PIN_BASE_HEADER!r}")
    if got["v3_manifest_live"] != PIN_V3_MANIFEST != gate["v3_manifest"]:
        bad.append("v3 manifest digest moved off Gate 4's signed pin")
    if got["rules_digest_live"] != PIN_RULES != gate["scorecard_rules"]:
        bad.append("scorecard rules_digest moved off Gate 4's signed pin")
    if got["grid_digest_live"] != PIN_GRID:
        bad.append(f"grid definition_digest moved: {got['grid_digest_live']}")
    got["ok"], got["problems"] = not bad, bad
    if strict and bad:
        raise SystemExit("REFUSING: " + "; ".join(bad))
    return got


def verify_records_sha256(run_dir: pathlib.Path) -> dict:
    """shasum -a 256 -c records.sha256, as declared.  A digest mismatch aborts."""
    f = run_dir / "records.sha256"
    r = subprocess.run(["shasum", "-a", "256", "-c", f.name], cwd=run_dir,
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.strip().splitlines() if l]
    if r.returncode != 0:
        raise SystemExit(f"REFUSING: records.sha256 does not verify in {run_dir}:\n{r.stdout}"
                         f"{r.stderr}")
    return {"file": str(f.relative_to(ROOT)), "result": lines}


# ---------------------------------------------------------------------------------------
# Streaming projection
# ---------------------------------------------------------------------------------------

def _project(d: dict) -> dict:
    r = {k: d[k] for k in KEEP}
    for k in ("policy", "wf", "repo", "attack"):
        r[k] = sys.intern(r[k])
    r["loss"] = R.loss_of(d)
    return r


def stream(path: pathlib.Path, keep):
    """Yield (cell, projected row) for the rows `keep(record, cell)` accepts.  One pass, one
    json.loads, projected immediately: the heavy fields never enter memory."""
    with open(path) as fh:
        for line in fh:
            d = json.loads(line)
            c = d["cell"]
            if keep(d, c):
                yield c, _project(d), d


def load_blocks(h18kd: pathlib.Path = H18KD, main: pathlib.Path = MAIN) -> dict:
    """Everything the two hypotheses need, bucketed, in three streaming passes."""
    bags = {"h18_level": collections.defaultdict(list),   # (rho, level) -> rows  (non-b1)
            "h18_b1": collections.defaultdict(list),      # rho -> rows           (from main)
            "kd": collections.defaultdict(list),          # (rho, k_d) -> rows
            "main_kd2": collections.defaultdict(list),    # rho -> rows (B1+Sentinel)
            "controls": collections.defaultdict(list)}    # rho -> rows (D28 controls)
    meta = {}

    # --- h18 block: every budget level it holds (b1 is absent; see the carried deviation)
    h18_cells, h18_pols, h18_n = set(), set(), 0
    def keep_h18(d, c):
        return (d["policy"] in H18_POLICIES and d["attack"] in HELD_OUT
                and d["delta"] in DELTAS)
    for c, r, d in stream(h18kd / "h18.jsonl", lambda d, c: True):
        h18_n += 1
        h18_cells.add(c["budget"]); h18_pols.add(d["policy"])
        if keep_h18(d, c):
            bags["h18_level"][(c["rho"], c["budget"])].append(r)
    meta["h18"] = {"n_records": h18_n, "levels": sorted(h18_cells),
                   "policies": sorted(h18_pols)}

    # --- kd block: the K_d axis, headline Deltas, B1 + Sentinel
    kd_n, kd_kd, kd_pols, kd_lvl = 0, set(), set(), set()
    for c, r, d in stream(h18kd / "kd.jsonl", lambda d, c: True):
        kd_n += 1
        kd_kd.add(c["k_delegated"]); kd_pols.add(d["policy"]); kd_lvl.add(c["budget"])
        if (d["policy"] in (B1, SENTINEL) and d["attack"] in HELD_OUT
                and d["delta"] in HEAD_DELTAS):
            bags["kd"][(c["rho"], c["k_delegated"])].append(r)
    meta["kd"] = {"n_records": kd_n, "k_delegated": sorted(kd_kd),
                  "policies": sorted(kd_pols), "levels": sorted(kd_lvl)}

    # --- main block: the b1 level of H18, the K_d = 2 point of H19, and the D28 controls
    sweepers = ("B3 audit-on-insertion", "B4 audit-on-retrieval", "B6 two-stage")
    ctrl_pols = {"Oracle (+)", B1, *sweepers}
    m_n, m_units, m_wfs, m_repos, m_pols = 0, set(), set(), set(), set()
    for c, r, d in stream(main, lambda d, c: True):
        m_n += 1
        m_units.add((d["policy"], d["attack"], c["rho"], c["delta"], c["k_delegated"],
                     c["chi"], c["dprime"], c["budget"], c["price_only"]))
        m_wfs.add(d["wf"]); m_repos.add(d["repo"]); m_pols.add(d["policy"])
        if c["budget"] != "b1" or c["k_delegated"] != KD_MAIN:
            continue
        if d["attack"] in HELD_OUT and d["policy"] in ctrl_pols and d["delta"] in (0, *HEAD_DELTAS):
            bags["controls"][c["rho"]].append(r)
        if d["attack"] not in HELD_OUT:
            continue
        if d["policy"] in H18_POLICIES and d["delta"] in DELTAS:
            bags["h18_b1"][c["rho"]].append(r)
        if d["policy"] in (B1, SENTINEL) and d["delta"] in HEAD_DELTAS:
            bags["main_kd2"][c["rho"]].append(r)
    meta["main"] = {"n_records": m_n, "n_workflows": len(m_wfs), "n_repos": len(m_repos),
                    "policies": sorted(m_pols)}
    meta["main_comparability"] = _main_comparability(m_units, m_pols)
    return bags, meta


def _main_comparability(observed_units: set, policies: set) -> dict:
    """eval-pass1/ has no summary.json (the command was killed during the `br` block), so
    comparability with the h18/kd run is established from the records: the observed
    (system, column, cell) set of main.jsonl must be EXACTLY the set the live grid emits
    for the `main` block at the headline (chi, d') with these systems -- and the live grid
    digest is Gate 4's pin, checked by check_freeze.  If that set matches, main.jsonl was
    produced by the same grid definition, whatever its manifest was."""
    want = {(u.system, u.column, u.cell.rho, u.cell.delta, u.cell.k_delegated, u.cell.chi,
             u.cell.dprime, u.cell.budget, u.cell.price_only)
            for u in G.units()
            if u.block == "main" and u.system in policies
            and u.cell.chi == "1.33" and u.cell.dprime == 2.21}
    return {"how": "observed (system, column, cell) set of main.jsonl vs the live grid's "
                   "`main` block at the headline (chi = 1.33, d' = 2.21)",
            "grid_digest": G.definition_digest(),
            "n_grid_units": len(want), "n_observed_units": len(observed_units),
            "identical": want == observed_units,
            "only_in_grid": sorted(map(str, list(want - observed_units)[:5])),
            "only_in_records": sorted(map(str, list(observed_units - want)[:5]))}


# ---------------------------------------------------------------------------------------
# The two metrics: harm, and L relabelled into the scored field
# ---------------------------------------------------------------------------------------

def as_metric(rows: list, metric: str) -> list:
    """metrics.gain_ci hard-codes field="harm"; for L the scored field is relabelled, not
    copied.  `harm` rows are returned untouched."""
    if metric == "harm":
        return rows
    if metric != "L":
        raise ValueError(metric)
    return [{**r, "harm": r["loss"]} for r in rows]


def alias_check(rows: list, policy: str) -> dict:
    """Dev's alias_check: table(..., field="loss").value and the relabelled path must give
    the same float (compared with ==, not a tolerance)."""
    a = M.table(rows, policy, HELD_OUT, HEAD_DELTAS, field="loss").value
    b = M.table(as_metric(rows, "L"), policy, HELD_OUT, HEAD_DELTAS, field="harm").value
    return {"table_field_loss": a, "alias_field_harm": b, "identical": bool(a == b)}


# ---------------------------------------------------------------------------------------
# H18
# ---------------------------------------------------------------------------------------

def h18_curve(bags: dict) -> dict:
    """rho -> level -> Delta -> {policy: V_miss, frontier}.  b1 comes from the main block;
    a level a rho has no records at is recorded as None (NOT measured -- never 0)."""
    out = {}
    for rho in RHOS:
        per = {}
        for lvl in LEVELS:
            recs = bags["h18_b1"][rho] if lvl == "b1" else bags["h18_level"].get((rho, lvl))
            if not recs:
                per[lvl] = None
                continue
            pols = sorted({r["policy"] for r in recs})
            per[lvl] = M.h18_miss_curve({lvl: recs}, pols, HELD_OUT)[lvl]
        out[str(rho)] = per
    return out


def h18_change(bags: dict) -> dict:
    """The declared test at b1, plus the same statistic at 2xBmin (reported beside, never
    instead: the verdict is b1's)."""
    out = {}
    for rho in RHOS:
        recs = bags["h18_b1"][rho]
        if not recs:
            out[str(rho)] = None
            continue
        pols = sorted({r["policy"] for r in recs})
        res = M.h18_miss_change(recs, pols, HELD_OUT)
        res = {**res, "policies_present": pols,
               "missing_policy": sorted(set(H18_POLICIES) - set(pols))}
        out[str(rho)] = res
    at2 = {}
    for rho in RHOS:
        recs = bags["h18_level"].get((rho, "2xBmin"))
        if not recs:
            at2[str(rho)] = None
            continue
        pols = sorted({r["policy"] for r in recs})
        at2[str(rho)] = M.h18_miss_change(recs, pols, HELD_OUT)
    out["at_2xBmin"] = at2
    return out


# ---------------------------------------------------------------------------------------
# H19: the slope of the gain along K_d, drawn paired
# ---------------------------------------------------------------------------------------

def _rel(base_draws, cand_draws):
    return 100.0 * (base_draws - cand_draws) / base_draws


def kd_slope(bags: dict, rho: float, metric: str) -> dict:
    """gain(K_d = 3) - gain(K_d = 1) vs B1, Delta in {4, 8}, the four tables on ONE set of
    family draws (paired).  Returns the per-K_d gains, the slope, its CI and p."""
    tabs, pts = {}, {}
    for kd in KD_PAIR:
        rows = as_metric(bags["kd"].get((rho, kd), []), metric)
        if not rows:
            return {"available": False, "reason": f"no kd={kd} records at rho={rho}"}
        for name, pol in (("base", B1), ("cand", SENTINEL)):
            t = M.table(rows, pol, HELD_OUT, HEAD_DELTAS)
            if not t.cols:
                return {"available": False, "reason": f"no {pol} table at kd={kd}"}
            tabs[(kd, name)] = t
    bt = M.boot_values(tabs)
    gains, rels = {}, {}
    for kd in KD_PAIR:
        b, c = bt.draws[(kd, "base")], bt.draws[(kd, "cand")]
        vb, vc = bt.point[(kd, "base")], bt.point[(kd, "cand")]
        pts[kd] = (vb, vc)
        rels[kd] = (b, c)
        gains[kd] = {"gain": 100.0 * (vb - vc) / vb if vb else NAN,
                     "v_base": vb, "v_cand": vc, "abs_diff": vb - vc}
    # one joint mask: a draw enters the paired slope only if BOTH bases are positive
    pos = np.ones_like(rels[KD_PAIR[0]][0], dtype=bool)
    for kd in KD_PAIR:
        pos &= rels[kd][0] > 0
    for kd in KD_PAIR:
        b, c = rels[kd]
        r = _rel(b[pos], c[pos])
        lo, hi = M.interval(r)
        gains[kd].update({"lo": lo, "hi": hi, "p_rel": M.p_value(r)})
    slope_draws = (_rel(*[x[pos] for x in rels[KD_PAIR[1]]])
                   - _rel(*[x[pos] for x in rels[KD_PAIR[0]]]))
    lo, hi = M.interval(slope_draws)
    point = gains[KD_PAIR[1]]["gain"] - gains[KD_PAIR[0]]["gain"]
    # D21 reliability, as gain_ci reads it, on both K_d ends
    rel_ok = all(tabs[(kd, "base")].events[tabs[(kd, "base")].worst_column]
                 >= __import__("metrics_v2").MIN_BASE_EVENTS for kd in KD_PAIR)
    return {"available": True,
            f"gain_kd{KD_PAIR[0]}": gains[KD_PAIR[0]], f"gain_kd{KD_PAIR[1]}": gains[KD_PAIR[1]],
            "slope": {"point": point, "lo": lo, "hi": hi, "p": M.p_value(slope_draws),
                      "reliable": bool(rel_ok), "n_draws": int(pos.sum())},
            "n_repos": len(bt.families), "n_workflows": len(bt.workflows),
            "method": bt.method, "n_boot": bt.n_boot}


def kd2_main(bags: dict, rho: float, metric: str) -> dict:
    """The K_d = 2 point, read from the main block (the third point of the K_d curve;
    O15 applies to K_d != 2, not to this one)."""
    rows = as_metric(bags["main_kd2"].get(rho, []), metric)
    if not rows:
        return {"available": False, "reason": f"no main K_d=2 records at rho={rho}"}
    g = M.gain_ci(rows, B1, SENTINEL, HELD_OUT, HEAD_DELTAS)
    return {"available": True, **{k: g[k] for k in ("gain", "lo", "hi", "abs_diff", "v_base",
                                                   "v_cand", "p_rel", "rel_reliable")}}


# ---------------------------------------------------------------------------------------
# D28 controls (an addition to dev's section 10, reported not scored)
# ---------------------------------------------------------------------------------------

def controls(bags: dict, rho: float, metric: str = "harm") -> dict:
    """D28 on the eval main block.  ON HARM ONLY, and deliberately: the positive control is
    "the oracle reaches CONTROL_MAX_HARM", a harm threshold.  Read on L it fails by
    construction -- Oracle (+) pays FQ and clean-lost, so V(L) > 0 for it with no world
    defect at all (measured: V_oracle(L) = 0.431 at rho = 0).  Reading D28 on L would be a
    misapplication of the control, not a finding, so it is not reported."""
    if metric != "harm":
        raise ValueError("D28's positive control is a harm threshold; do not read it on L")
    rows = as_metric(bags["controls"].get(rho, []), metric)
    if not rows:
        return {"available": False, "reason": f"no control records at rho={rho}"}
    ro = M.Readout(rows)
    res = ro.controls("Oracle (+)", B1,
                      ("B3 audit-on-insertion", "B4 audit-on-retrieval", "B6 two-stage"),
                      HELD_OUT)
    return {"available": True, **{k: (bool(v) if isinstance(v, (bool, np.bool_)) else v)
                                  for k, v in res.items()}}


# ---------------------------------------------------------------------------------------
# Scoring: one BH family per (metric, rho), exactly as dev
# ---------------------------------------------------------------------------------------

def _est(d, key_point="point") -> SC.Estimate:
    return SC.Estimate(lo=d["lo"], hi=d["hi"], point=d[key_point], p=d["p"],
                       reliable=bool(d.get("reliable", True)), alpha=d.get("alpha", 0.05))


def score(h18: dict, h19: dict) -> tuple:
    """(verdicts, raw).  verdicts: hid -> metric -> "rho=x" -> [rows].  H18's statistic is
    missed_before_sigma, so it does not depend on the metric choice: the same Estimate is
    scored under both, which is why both metrics give the same H18 verdict."""
    verdicts = {"H18": {}, "H19": {}, "H20": {}}
    raw = {}
    for metric in ("L", "harm"):
        for rho in RHOS:
            est = {}
            ch = h18["change"].get(str(rho))
            if ch and M._is_finite(ch.get("point")):
                est["h18_miss_change_d8_minus_d4"] = _est(ch)
            sl = h19["by_rho"].get(str(rho), {}).get(metric, {})
            if sl.get("available") and M._is_finite(sl["slope"]["point"]):
                est["gain_slope_in_kd"] = _est(sl["slope"])
            allv = SC.score_all(est)
            raw[f"{metric}|rho={rho}"] = {
                hid: [{"rule": c.rule, "quantity": c.quantity, "side": c.side,
                       "where": c.where,
                       "outcome": (v if isinstance(v, str) else v.outcome),
                       "reason": ("" if isinstance(v, str) else v.reason),
                       "detail": ({} if isinstance(v, str) else v.detail)}
                      for c, v in rows]
                for hid, rows in allv.items() if hid in ("H18", "H19")}
            for hid in ("H18", "H19"):
                verdicts[hid].setdefault(metric, {})[f"rho={rho}"] = \
                    raw[f"{metric}|rho={rho}"][hid]
    verdicts["H20"] = {
        "status": "NOT MEASURED",
        "reason": "this eval run has no `attacker-delta` block at all (the fourth grant ran "
                  "blocks h18 + kd only), so V_S - V_B1 in the attacker-chooses-Delta column "
                  "cannot be formed.  On dev the same check was TBD for a different reason: "
                  "the block existed but attackers.br_systems trims that column to the "
                  "Sentinel class, so there was no B1 record.  Not 0, not INCONCLUSIVE: "
                  "unmeasured.",
    }
    return verdicts, raw


# ---------------------------------------------------------------------------------------
# Not measured (N3: a reason, never a zero)
# ---------------------------------------------------------------------------------------

def not_measured(meta: dict) -> list:
    return [
        {"what": "H18 chi side -- bmin_diff_chi_price_only (rule E)",
         "why": "the eval h18 block has no price-only arm and only chi = 1.33, so there is "
                "nothing to difference.  Identical to dev, where the same check was TBD; "
                "and Q12 declares no delta for a budget-scale quantity, so it would be "
                "INCONCLUSIVE even with a number."},
        {"what": "H18 / H19 exploitability, V_BR (cross-fit D27)",
         "why": "the BR blocks (h18-br, kd-br) were not run in this eval pass.  The only "
                "br.jsonl on the eval side, spikes/v3-run/eval-pass1/br.jsonl, is a 7.8 GB "
                "partial from a killed run and is declared not-a-result; it was not read."},
        {"what": "H18 statistic at rho = 1 for any level below b1",
         "why": "declared deviation: grid._bmin_hole -> FLAG_COMMIT_SUFFICES drops rho = 1 "
                "from the h18 block at every level != b1.  The b1 test AT rho = 1 IS "
                "measured (it comes from the main block)."},
        {"what": "H18 frontier over all four H18 policies",
         "why": "block-schedule is absent on eval exactly as on dev (grid gives it the only "
                "b1 H18 unit, and it is not one of the fifteen declared systems), so the "
                "frontier covers 3 of 4 H18 policies: "
                f"{meta['h18']['policies']}."},
        {"what": "H20 (rule N, attacker-chooses-Delta column)",
         "why": "no attacker-delta block in this eval pass; see verdicts.H20."},
        {"what": "the six one-factor sensitivity worlds and the seeded two-carrier block",
         "why": "no sens:* / seed2-pairs block in this eval pass; dev's section 10.4 has no "
                "held-out counterpart yet."},
        {"what": "dev's alias_check float 0.8980696428571429",
         "why": "that is a dev number; the eval side's own alias check is reported under "
                "estimator.alias_check.  A held-out run cannot reproduce a dev float."},
    ]


# ---------------------------------------------------------------------------------------
# The dev self-check: does this script's method reproduce h_verdicts.json?
# ---------------------------------------------------------------------------------------

def dev_selfcheck() -> dict:
    """Run exactly this pipeline over the DEV blocks and compare with h_verdicts.json.  The
    dev script was never saved, so this is the only evidence that the method here is the
    method that produced the dev numbers.  H18 is compared bit for bit (repr equality of the
    floats); H19's slope is compared to 1e-9, because the dev file records no per-draw mask
    and the joint positive-base mask of kd_slope() is a reconstruction (stated, not hidden)."""
    dev = json.loads(DEV_VERDICTS.read_text())
    bags, meta = load_blocks(DEV_H18KD, DEV_MAIN)
    got_h18, got_h19 = h18_change(bags), {}
    for rho in RHOS:
        got_h19[str(rho)] = {m: kd_slope(bags, rho, m) for m in ("L", "harm")}
    rows = []
    for rho in RHOS:
        a, b = dev["numbers"]["h18"]["change"].get(str(rho)), got_h18.get(str(rho))
        for key in ("point", "lo", "hi", "p"):
            rows.append({"what": f"h18 rho={rho} {key}", "dev": a and a.get(key),
                         "got": b and b.get(key),
                         "exact": bool(a and b and repr(a[key]) == repr(b[key]))})
        for d in ("4", "8"):
            av = (a or {}).get("frontier", {}).get(d)
            bv = (b or {}).get("frontier", {}).get(int(d))
            rows.append({"what": f"h18 rho={rho} frontier d{d}", "dev": av, "got": bv,
                         "exact": bool(av is not None and repr(av) == repr(bv))})
        for m in ("L", "harm"):
            a2 = dev["numbers"]["h19"]["by_rho"].get(str(rho), {}).get(m, {}).get("slope", {})
            b2 = got_h19[str(rho)][m].get("slope", {})
            for key in ("point", "lo", "hi", "p"):
                av, bv = a2.get(key), b2.get(key)
                ok = (av is not None and bv is not None
                      and M._is_finite(av) and M._is_finite(bv) and abs(av - bv) < 1e-9)
                rows.append({"what": f"h19 rho={rho} {m} slope {key}", "dev": av, "got": bv,
                             "exact": bool(ok)})
    n_ok = sum(1 for r in rows if r["exact"])
    return {"blocks": meta, "n_checks": len(rows), "n_reproduced": n_ok,
            "all_reproduced": n_ok == len(rows), "rows": rows}


# ---------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------

def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        x = float(x)
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def run() -> dict:
    fz = check_freeze()
    digests = {"eval-p1-h18kd": verify_records_sha256(H18KD)}
    bags, meta = load_blocks()

    h18 = {"policies_present": meta["h18"]["policies"],
           "missing_policy": sorted(set(H18_POLICIES) - set(meta["h18"]["policies"])),
           "levels": {"h18_block": meta["h18"]["levels"],
                      "b1_source": "spikes/v3-run/eval-pass1/main.jsonl"},
           "curve": h18_curve(bags), "change": h18_change(bags)}

    h19 = {"by_rho": {}}
    for rho in RHOS:
        h19["by_rho"][str(rho)] = {
            m: {**kd_slope(bags, rho, m), "gain_kd2_main": kd2_main(bags, rho, m)}
            for m in ("L", "harm")}

    ctrl = {"metric": "harm (see controls(): D28's positive control is a harm threshold)",
            "by_rho": {str(rho): controls(bags, rho, "harm") for rho in RHOS}}
    selfcheck = dev_selfcheck()
    verdicts, raw = score(h18, h19)

    ac_rows = bags["main_kd2"].get(0.0, [])
    out = {
        "generated": "2026-09-29",
        "report": "docs/reports/v3-p5-h18-heldout.md",
        "script": "auditgame/tools/v3_p5_h18_heldout.py",
        "split": "eval",
        "metrics": {"headline": "L (Definition 1), field=loss", "also_reported": "V = harm",
                    "lambda_Q": R.LAMBDA_Q, "lambda_T": R.LAMBDA_T,
                    "prereg": "docs/preregistration/TIEN-DANG-KY-metric-headline-V.md"},
        "estimator": {
            "bootstrap": "wild cluster (Webb) by repo family, N=10000, alpha=0.05, re-max "
                         "over columns per draw, shared family draws",
            "bh": "scorecard.rule_D_family, q=0.05, one family per (metric, rho)",
            "rules_digest": fz["rules_digest_live"],
            "sign_convention": "h18_miss_change_d8_minus_d4 = V_miss(Delta=8) - "
                               "V_miss(Delta=4) of the frontier at budget level b1; draft "
                               "predicts +1 (budget must grow with Delta), note predicts -1 "
                               "(minimum budget falls like H/Delta).  Negative = misses FALL "
                               "as Delta grows = the note's direction.",
            "h19_slope": "gain_slope_in_kd = gain(K_d=3) - gain(K_d=1) vs B1, headline "
                         "Delta in {4, 8}, four tables on one shared set of family draws",
            "alias_check": alias_check(ac_rows, SENTINEL) if ac_rows else None,
            "method_validation": {
                "how": "--dev-selfcheck: this exact pipeline re-run over the dev blocks and "
                       "diffed against spikes/v3-run/h_verdicts.json (the dev script was "
                       "never saved, so this is the evidence the method matches)",
                **{k: selfcheck[k] for k in ("n_checks", "n_reproduced", "all_reproduced")},
            },
        },
        "freeze": {"freeze_v3_header": fz["freeze_v3_header"],
                   "freeze_base_header": fz["freeze_base_header"],
                   "v3_manifest_live": fz["v3_manifest_live"],
                   "grid_digest_live": fz["grid_digest_live"],
                   "gate4": fz["gate4"]},
        "inputs": {"records_sha256": digests, "blocks": meta,
                   "br_jsonl": "NOT READ: spikes/v3-run/eval-pass1/br.jsonl is a partial "
                               "from a killed run, declared not-a-result",
                   "no_run_performed": "analysis only: tools/v3_run.py was not invoked, the "
                                       "unseal log was not appended to, no grant consumed"},
        "deviations": [
            "h18 block has no b1 level (grid gives b1 only to BlockSchedule, which was not "
            "run); the declared H18 fixed level b1 is read from eval-pass1/main.jsonl, same "
            f"grid_digest {PIN_GRID[:12]}, its own run dir has no summary.json (killed during "
            "the br block) so comparability is established from the records; the frontier "
            "covers 3 of 4 H18 policies -- IDENTICAL to the dev deviation",
            "rho=1 dropped from the h18 block at every level != b1 (FLAG_COMMIT_SUFFICES)",
            "O15: K_d != 2 reuses the primary world's line-5 table",
            "no h18-br / kd-br in this pass: no exploitability on either axis",
        ],
        "d28_controls_main_block": ctrl,
        "verdicts": verdicts,
        "not_measured": not_measured(meta),
        "numbers": {"h18": h18, "h19": h19},
        "scorecard_raw": raw,
    }
    OUT_JSON.write_text(json.dumps(_jsonable(out), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return out


def _fmt(x, n=4):
    return "n/a" if x is None or not M._is_finite(x) else f"{x:.{n}f}"


def print_summary(out: dict) -> None:
    print(out["freeze"]["freeze_v3_header"])
    print(out["freeze"]["freeze_base_header"])
    print()
    print("H18  h18_miss_change_d8_minus_d4 at b1 (frontier over "
          f"{out['numbers']['h18']['policies_present']})")
    print(f"{'rho':>6} {'miss d4':>9} {'miss d8':>9} {'change':>9} {'CI':>26} {'p':>8} "
          f"{'p_adj':>8}  draft(+1)      note(-1)")
    for rho in RHOS:
        ch = out["numbers"]["h18"]["change"].get(str(rho))
        if ch is None:
            print(f"{rho:>6}  NOT MEASURED")
            continue
        det = {r["side"]: r for r in out["scorecard_raw"][f"L|rho={rho}"]["H18"]
               if r["rule"] == "D"}
        fr = ch.get("frontier", {})
        ci = f"[{_fmt(ch['lo'])}, {_fmt(ch['hi'])}]"
        padj = det.get("draft", {}).get("detail", {}).get("p_adj")
        print(f"{rho:>6} {_fmt(fr.get(4) or fr.get('4')):>9} "
              f"{_fmt(fr.get(8) or fr.get('8')):>9} {_fmt(ch['point']):>9} {ci:>26} "
              f"{_fmt(ch['p']):>8} {_fmt(padj):>8}  "
              f"{det.get('draft', {}).get('outcome', '?'):<14} "
              f"{det.get('note', {}).get('outcome', '?')}")
    print()
    for metric in ("L", "harm"):
        print(f"H19  gain_slope_in_kd, metric = {metric}")
        for rho in RHOS:
            s = out["numbers"]["h19"]["by_rho"][str(rho)][metric]
            if not s.get("available"):
                print(f"  rho={rho}: NOT MEASURED -- {s.get('reason')}")
                continue
            sl = s["slope"]
            det = {r["side"]: r for r in out["scorecard_raw"][f"{metric}|rho={rho}"]["H19"]}
            print(f"  rho={rho:<5} kd1 {_fmt(s['gain_kd1']['gain'],1):>7} "
                  f"kd2 {_fmt(s['gain_kd2_main'].get('gain'),1):>7} "
                  f"kd3 {_fmt(s['gain_kd3']['gain'],1):>7}  slope {_fmt(sl['point'],2):>7} "
                  f"[{_fmt(sl['lo'],2)}, {_fmt(sl['hi'],2)}] p {_fmt(sl['p'])}  "
                  f"draft {det.get('draft', {}).get('outcome')} / "
                  f"note {det.get('note', {}).get('outcome')}")
        print()
    print(f"written: {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-freeze", action="store_true",
                    help="print the freeze headers and the pins, change nothing")
    ap.add_argument("--run", action="store_true", help="the analysis")
    ap.add_argument("--dev-selfcheck", action="store_true",
                    help="re-run this method on the DEV blocks and diff against "
                         "h_verdicts.json (evidence the method matches the unsaved dev one)")
    a = ap.parse_args()
    if a.check_freeze:
        print(json.dumps(_jsonable(check_freeze(strict=False)), indent=1))
    elif a.dev_selfcheck:
        check_freeze()
        res = dev_selfcheck()
        for r in res["rows"]:
            print(f"{'OK ' if r['exact'] else 'DIFF'}  {r['what']:<34} dev={r['dev']!r:<24} "
                  f"got={r['got']!r}")
        print(f"\n{res['n_reproduced']}/{res['n_checks']} reproduced")
    elif a.run:
        print_summary(run())
    else:
        raise SystemExit("usage: v3_p5_h18_heldout.py --check-freeze | --run | "
                         "--dev-selfcheck")
