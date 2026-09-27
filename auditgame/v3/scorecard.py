"""v3/scorecard.py -- the prediction scorecard: rules P, D, E, N, G and the H1-H20 frame
(sentinel-v3.md "Bang diem du doan"; plan Q12, T17).

Every projected number of the draft is a hypothesis.  The rules are hashed before the run
(rules_digest(), into frozen/V3-GATE4.json at Gate 4) and are not changed after a number
is seen.  Each rule returns a Verdict whose outcome is one of

    MATCH = "khớp", REJECT = "bác", INCONCLUSIVE = "không kết luận"

with the reason.  The rules, as written in sentinel-v3.md:

  P (one number)   MATCH if the whole 95% CI lies in [projection - delta; projection + delta];
                   REJECT if the CI does not meet that band; otherwise INCONCLUSIVE, also
                   when the CI is wider than 2 delta.  Containment is inclusive, "does not
                   meet" is strict (a CI touching the band meets it), so the two outcomes
                   are disjoint whenever lo <= hi.
  D (direction)    MATCH if the CI of the difference excludes 0 with the predicted sign;
                   REJECT if it excludes 0 with the other sign; otherwise INCONCLUSIVE.
                   "Excludes 0" is strict: a bound at 0 does not exclude it.  The whole D
                   family is BH-adjusted at q = 0.05 (rule_D_family).
  E (equivalence)  MATCH if the CI of the difference lies in [-delta; delta] (inclusive);
                   REJECT if it lies wholly outside [-delta; delta] (lo > delta or
                   hi < -delta); otherwise INCONCLUSIVE.
  N (non-superiority, H20) on V_S - V_B1: MATCH if the lower bound > -delta; REJECT if the
                   upper bound < -delta; otherwise INCONCLUSIVE.
  G (gate, S9.4)   the lower bound of the reduction is at least 15%: MATCH if lo >= 15.
                   REJECT if hi < 15 (the data exclude a 15% reduction); otherwise
                   INCONCLUSIVE.  The draft states only the passing condition; REJECT vs
                   INCONCLUSIVE splits "not passed" and is declared here, before any number.

Margins (Q12): delta = config.DELTA_REL_POINTS (10 points) for relative reductions and
config.DELTA_ABS_HARM (0.10) for harm.  No other margin is declared: a P or E check on a
quantity of another kind (a crossover Delta, a percentage of clean completion or FQ, a TV
radius, a budget) carries margin None and returns INCONCLUSIVE with the reason "no
declared delta" until the user declares one -- T17 does not invent margins.

A relative quantity whose D21 reliability flag is False (metrics.gain_ci's rel_reliable)
is INCONCLUSIVE under P and G: only the absolute difference is read then.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import math
from dataclasses import asdict, dataclass, field

from v3 import config as C

MATCH, REJECT, INCONCLUSIVE = "khớp", "bác", "không kết luận"
OUTCOMES = (MATCH, REJECT, INCONCLUSIVE)
NOT_RUN = "chưa chạy"
RULES = ("P", "D", "E", "N", "G")
#: margin kinds (Q12); None = no margin declared.
MARGIN = {"rel": C.DELTA_REL_POINTS, "abs": C.DELTA_ABS_HARM, None: None}


@dataclass(frozen=True)
class Verdict:
    rule: str
    outcome: str
    reason: str
    hypothesis: str = ""
    quantity: str = ""
    side: str = ""                     # "draft" / "note" for the H18-H20 pairs
    detail: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.rule not in RULES:
            raise ValueError(f"rule {self.rule!r} is not one of {RULES}")
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome {self.outcome!r} is not one of {OUTCOMES}")


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _ci(rule, lo, hi):
    """None if the CI can be ruled on, else an INCONCLUSIVE verdict.  lo > hi raises."""
    if not (_finite(lo) and _finite(hi)):
        return Verdict(rule, INCONCLUSIVE, f"no finite CI ({lo}, {hi})", detail={"lo": lo, "hi": hi})
    if lo > hi:
        raise ValueError(f"CI lower bound {lo} exceeds upper bound {hi}")
    return None


def _no_margin(rule, margin, lo, hi):
    if margin is None:
        return Verdict(rule, INCONCLUSIVE, "no declared delta for this quantity (Q12 declares "
                       "10 points for reductions and 0.10 for harm only)",
                       detail={"lo": lo, "hi": hi})
    if not _finite(margin) or margin <= 0:
        raise ValueError(f"delta must be a positive number, got {margin!r}")
    return None


# ---------------------------------------------------------------------------------------
# The five rules
# ---------------------------------------------------------------------------------------

def rule_P(lo, hi, projection, delta, reliable=True) -> Verdict:
    bad = _ci("P", lo, hi) or _no_margin("P", delta, lo, hi)
    if bad:
        return bad
    if not reliable:
        return Verdict("P", INCONCLUSIVE, "relative quantity not readable (D21): read the "
                       "absolute difference", detail={"lo": lo, "hi": hi})
    b_lo, b_hi = projection - delta, projection + delta
    d = {"lo": lo, "hi": hi, "projection": projection, "delta": delta, "band": (b_lo, b_hi)}
    if b_lo <= lo and hi <= b_hi:
        return Verdict("P", MATCH, f"CI [{lo:g}; {hi:g}] lies in [{b_lo:g}; {b_hi:g}]", detail=d)
    if hi < b_lo or lo > b_hi:
        return Verdict("P", REJECT, f"CI [{lo:g}; {hi:g}] does not meet [{b_lo:g}; {b_hi:g}]",
                       detail=d)
    why = "wider than 2 delta" if hi - lo > 2 * delta else "overlaps the band's edge"
    return Verdict("P", INCONCLUSIVE, f"CI [{lo:g}; {hi:g}] {why} [{b_lo:g}; {b_hi:g}]", detail=d)


def rule_D(lo, hi, sign) -> Verdict:
    """sign = +1 if the prediction is difference > 0, -1 if < 0."""
    if sign not in (1, -1):
        raise ValueError(f"sign must be +1 or -1, got {sign!r}")
    bad = _ci("D", lo, hi)
    if bad:
        return bad
    d = {"lo": lo, "hi": hi, "sign": sign}
    if lo > 0 or hi < 0:
        got = 1 if lo > 0 else -1
        if got == sign:
            return Verdict("D", MATCH, f"CI [{lo:g}; {hi:g}] excludes 0 with the predicted sign "
                           f"{sign:+d}", detail=d)
        return Verdict("D", REJECT, f"CI [{lo:g}; {hi:g}] excludes 0 with the opposite sign "
                       f"{got:+d}", detail=d)
    return Verdict("D", INCONCLUSIVE, f"CI [{lo:g}; {hi:g}] does not exclude 0", detail=d)


def rule_E(lo, hi, delta) -> Verdict:
    bad = _ci("E", lo, hi) or _no_margin("E", delta, lo, hi)
    if bad:
        return bad
    d = {"lo": lo, "hi": hi, "delta": delta}
    if -delta <= lo and hi <= delta:
        return Verdict("E", MATCH, f"CI [{lo:g}; {hi:g}] lies in [{-delta:g}; {delta:g}]", detail=d)
    if lo > delta or hi < -delta:
        return Verdict("E", REJECT, f"CI [{lo:g}; {hi:g}] lies wholly outside "
                       f"[{-delta:g}; {delta:g}]", detail=d)
    return Verdict("E", INCONCLUSIVE, f"CI [{lo:g}; {hi:g}] straddles an edge of "
                   f"[{-delta:g}; {delta:g}]", detail=d)


def rule_N(lo, hi, delta) -> Verdict:
    """On V_S - V_B1 (harm; positive = Sentinel worse)."""
    bad = _ci("N", lo, hi) or _no_margin("N", delta, lo, hi)
    if bad:
        return bad
    d = {"lo": lo, "hi": hi, "delta": delta}
    if lo > -delta:
        return Verdict("N", MATCH, f"lower bound {lo:g} > -{delta:g}: Sentinel does not beat "
                       "B1 by more than delta", detail=d)
    if hi < -delta:
        return Verdict("N", REJECT, f"upper bound {hi:g} < -{delta:g}: Sentinel beats B1 by "
                       "more than delta", detail=d)
    return Verdict("N", INCONCLUSIVE, f"CI [{lo:g}; {hi:g}] contains -{delta:g}", detail=d)


def rule_G(lo, hi, margin=C.GATE_MARGIN_PCT, reliable=True) -> Verdict:
    bad = _ci("G", lo, hi)
    if bad:
        return bad
    d = {"lo": lo, "hi": hi, "margin": margin}
    if not reliable:
        return Verdict("G", INCONCLUSIVE, "relative gain not readable (D21)", detail=d)
    if lo >= margin:
        return Verdict("G", MATCH, f"lower bound {lo:g} >= {margin:g}%", detail=d)
    if hi < margin:
        return Verdict("G", REJECT, f"upper bound {hi:g} < {margin:g}%: a {margin:g}% "
                       "reduction is excluded", detail=d)
    return Verdict("G", INCONCLUSIVE, f"lower bound {lo:g} < {margin:g}% <= upper bound "
                   f"{hi:g}", detail=d)


# ---------------------------------------------------------------------------------------
# Estimates and the D family under BH
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Estimate:
    """What a rule reads: a CI at level 1 - alpha, the point, the bootstrap p of 'value =
    0' (D family), and D21's reliability flag for relative quantities."""
    lo: float
    hi: float
    point: float = float("nan")
    p: float = float("nan")
    reliable: bool = True
    alpha: float = 0.05

    @classmethod
    def from_draws(cls, point, draws, alpha=0.05, reliable=True) -> "Estimate":
        from v3 import metrics as M
        lo, hi = M.interval(draws, alpha)
        return cls(lo, hi, point, M.p_value(draws), reliable, alpha)


def rule_D_family(items, q=C.BH_Q) -> list:
    """items: dicts {name, estimate: Estimate, sign}.  BH over the family's p-values; a
    hypothesis BH does not reject is INCONCLUSIVE whatever its unadjusted CI says; a
    rejected one is MATCH or REJECT by the sign of its point estimate (which, for a
    bootstrap p below alpha, is the sign of its whole CI).  Items sharing a `name` share
    one test (the draft / note sides of H18-H19)."""
    from v3 import metrics as M
    names = list(dict.fromkeys(it["name"] for it in items))
    p_of = {}
    for it in items:
        p_of.setdefault(it["name"], it["estimate"].p)
    res = M.bh([p_of[n] for n in names], q)
    rej = dict(zip(names, res["reject"]))
    adj = dict(zip(names, res["p_adj"]))
    out = []
    for it in items:
        e, s, n = it["estimate"], it["sign"], it["name"]
        d = {"lo": e.lo, "hi": e.hi, "point": e.point, "p": e.p, "p_adj": adj[n], "sign": s,
             "q": q, "m": res["m"]}
        if not _finite(e.point) or not _finite(e.p):
            out.append(Verdict("D", INCONCLUSIVE, "no finite estimate or p", quantity=n,
                               side=it.get("side", ""), detail=d))
        elif not rej[n]:
            out.append(Verdict("D", INCONCLUSIVE, f"BH at q = {q:g} does not reject 0 "
                               f"(p = {e.p:.4g}, adjusted {adj[n]:.4g})", quantity=n,
                               side=it.get("side", ""), detail=d))
        else:
            got = 1 if e.point > 0 else -1
            outcome = MATCH if got == s else REJECT
            out.append(Verdict("D", outcome, f"BH at q = {q:g} rejects 0 (adjusted p "
                               f"{adj[n]:.4g}); estimate sign {got:+d}, predicted {s:+d}",
                               quantity=n, side=it.get("side", ""), detail=d))
    return out


# ---------------------------------------------------------------------------------------
# The H1-H20 frame (sentinel-v3.md table; projections are the draft's numbers)
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Check:
    rule: str                          # P / D / E / N / G
    quantity: str                      # the estimate this check reads
    projection: float | None = None    # P only
    margin: str | None = None          # "rel" / "abs" / None (P, E, N)
    sign: int = 0                      # D only
    side: str = "draft"                # "draft" or "note" (H3, H18-H20)
    where: str = ""                    # cell / world the quantity is read in


@dataclass(frozen=True)
class Hypothesis:
    id: str
    claim: str
    kind: str                          # the doc's "Loại" column, verbatim
    checks: tuple


HEAD = "headline cells (Delta in {4, 8}, chi 1.33, d' 2.21), each rho, held-out attackers"

HYPOTHESES = (
    Hypothesis("H1", "worst-case harm falls at least 15% vs B1, held-out, equal budget "
               "(projected 27.6%)", "G + P",
               (Check("G", "gain_heldout", where=HEAD),
                Check("P", "gain_heldout", 27.6, "rel", where=HEAD))),
    Hypothesis("H2", "from dev (34.1%) to held-out (27.6%) about 1/5 is lost", "P",
               (Check("P", "gain_dev", 34.1, "rel", where=HEAD),
                Check("P", "gain_drop_dev_to_heldout", 34.1 - 27.6, "rel", where=HEAD))),
    Hypothesis("H3", "crossover at Delta ~ 2 (2.1) when chi = 0, later at chi = 1.34; the "
               "'does not change with chi' part applies to the price-only arm only",
               "P + D; E trên arm chỉ đổi giá",
               (Check("P", "crossover_delta_chi_low", 2.1, None),
                Check("D", "crossover_delta_chi_high_minus_low", sign=+1),
                Check("E", "gain_diff_price_only_arm", margin="rel",
                      where="H18 grid, price-only arm"))),
    Hypothesis("H4", "at Delta = 0 Sentinel is 1.2% worse than B1 (locked harm, C11)", "P",
               (Check("P", "gain_delta0", -1.2, "rel", where="Delta = 0"),)),
    Hypothesis("H5", "heterogeneity shrinks the gain: 34.8 -> 24.8% (Delta 4), 42.4 -> 33.1% "
               "(Delta 8)", "D",
               (Check("D", "gain_hetero_minus_uniform_d4", sign=-1, where="Delta = 4"),
                Check("D", "gain_hetero_minus_uniform_d8", sign=-1, where="Delta = 8"))),
    Hypothesis("H6", "cost-greedy is worse than uniform random", "D",
               (Check("D", "v_costgreedy_minus_random", sign=+1, where=HEAD),)),
    Hypothesis("H7", "regret vs B7 0.09; coverage radius 0.07; bound 0.42 (240 small games)",
               "P",
               (Check("P", "regret_vs_b7", 0.09, "abs", where="240 small games"),
                Check("P", "coverage_radius_tv", 0.07, None, where="240 small games"))),
    Hypothesis("H8", "B3 is the worst (0.441); best response inserts through ingress "
               "(verdict from the ingress-visible world)", "D",
               (Check("D", "v_b3_minus_worst_other", sign=+1, where="ingress-visible world"),)),
    Hypothesis("H9", "exploitability 0.09 (Sentinel), 0.34 (B1)", "P",
               (Check("P", "exploitability_sentinel", 0.09, "abs", where=HEAD),
                Check("P", "exploitability_b1", 0.34, "abs", where=HEAD))),
    Hypothesis("H10", "clean completion 92.6% vs 94.1%; FQ 5.1% vs 3.2%", "P",
               (Check("P", "clean_completion_sentinel", 92.6, None, where=HEAD),
                Check("P", "clean_completion_b1", 94.1, None, where=HEAD),
                Check("P", "fq_pct_sentinel", 5.1, None, where=HEAD),
                Check("P", "fq_pct_b1", 3.2, None, where=HEAD))),
    Hypothesis("H11", "LLM attackers: reduction 41.2%, every policy does better", "P + D",
               (Check("P", "gain_llm", 41.2, "rel", where="LLM class"),
                Check("D", "v_llm_minus_scripted_max_over_policies", sign=-1,
                      where="LLM class"))),
    Hypothesis("H12", "ablations: -randomization 0.456 (worse than B1), -alarm memory 0.371, "
               "-transition 0.318, -drift 0.264 with FQ 19.8%", "P + D",
               (Check("P", "v_minus_randomization", 0.456, "abs", where=HEAD),
                Check("P", "v_minus_alarm_memory", 0.371, "abs", where=HEAD),
                Check("P", "v_minus_transition", 0.318, "abs", where=HEAD),
                Check("P", "v_minus_drift", 0.264, "abs", where=HEAD),
                Check("P", "fq_pct_minus_drift", 19.8, None, where=HEAD),
                Check("D", "v_minus_randomization_minus_b1", sign=+1, where=HEAD))),
    Hypothesis("H13", "reduction 21.4-39.8% by detector, largest when the detector is weakest",
               "D", (Check("D", "gain_weak_minus_strong_detector", sign=+1),)),
    Hypothesis("H14", "the eta_Q sweep: reduction rises 34.1 -> 44.0% as quarantine gets "
               "cheap", "D", (Check("D", "gain_cheap_minus_expensive_quarantine", sign=+1),)),
    Hypothesis("H15", "B5 is steered by the attacker: FQ 8.1% without lower harm", "D",
               (Check("D", "fq_pct_b5_minus_b1", sign=+1, where=HEAD),)),
    Hypothesis("H16", "the best response against Sentinel spreads over the carriers", "D",
               (Check("D", "br_carrier_spread_sentinel_minus_b1", sign=+1, where=HEAD),)),
    Hypothesis("H17", "stage-weighted randomisation reaches more than half of Sentinel's "
               "benefit", "D",
               (Check("D", "sw_random_benefit_minus_half_sentinel_benefit", sign=+1, where=HEAD),)),
    Hypothesis("H18", "draft (Theorem 4): the budget must grow with Delta and chi; note "
               "(Thm 5.6): the minimum budget falls like H/Delta; 'independent of chi' only "
               "on the price-only arm", "D; E cho vế χ",
               (Check("D", "bmin_slope_in_delta", sign=+1, side="draft", where="H18 grid"),
                Check("D", "bmin_slope_in_delta", sign=-1, side="note", where="H18 grid"),
                Check("E", "bmin_diff_chi_price_only", margin=None, side="note",
                      where="H18 grid, price-only arm"))),
    Hypothesis("H19", "draft (Corollary 5): commit is less sufficient with more carriers; note "
               "(Cor. 6.1): the reduction shrinks as K grows", "D",
               (Check("D", "gain_slope_in_kd", sign=+1, side="draft", where="K_d axis"),
                Check("D", "gain_slope_in_kd", sign=-1, side="note", where="K_d axis"))),
    Hypothesis("H20", "note (Prop. 6.3(a)): in the attacker-chooses-Delta column, with Delta = 0 "
               "available, Sentinel does not beat B1 (locked harm, C11)", "N",
               (Check("N", "v_sentinel_minus_b1_attacker_delta", margin="abs", side="note",
                      where="column 'attacker chooses Delta'"),)),
)
BY_ID = {h.id: h for h in HYPOTHESES}


def score(hid: str, estimates: dict) -> list:
    """The verdicts of one hypothesis.  `estimates`: quantity -> Estimate.  A check whose
    quantity is missing is NOT_RUN (reported apart, never an outcome).  D checks here use
    the unadjusted CI; the scorecard's D verdicts come from score_all's BH family."""
    h = BY_ID[hid]
    out = []
    for ch in h.checks:
        e = estimates.get(ch.quantity)
        if e is None:
            out.append((ch, NOT_RUN))
            continue
        out.append((ch, _apply(ch, e, hid)))
    return out


def _apply(ch: Check, e: Estimate, hid: str = "") -> Verdict:
    if ch.rule == "P":
        v = rule_P(e.lo, e.hi, ch.projection, MARGIN[ch.margin], reliable=e.reliable)
    elif ch.rule == "D":
        v = rule_D(e.lo, e.hi, ch.sign)
    elif ch.rule == "E":
        v = rule_E(e.lo, e.hi, MARGIN[ch.margin])
    elif ch.rule == "N":
        v = rule_N(e.lo, e.hi, MARGIN[ch.margin])
    else:
        v = rule_G(e.lo, e.hi, reliable=e.reliable)
    return Verdict(v.rule, v.outcome, v.reason, hid, ch.quantity, ch.side, v.detail)


def score_all(estimates: dict, q=C.BH_Q) -> dict:
    """hid -> [(Check, Verdict | NOT_RUN)].  P, E, N, G per check; every D check of every
    hypothesis with an estimate forms ONE BH family at q."""
    out = {}
    fam = []
    for h in HYPOTHESES:
        rows = []
        for ch in h.checks:
            e = estimates.get(ch.quantity)
            if e is None:
                rows.append([ch, NOT_RUN])
            elif ch.rule == "D":
                rows.append([ch, None])
                fam.append({"name": ch.quantity, "estimate": e, "sign": ch.sign,
                            "side": ch.side, "_slot": (h.id, len(rows) - 1)})
            else:
                rows.append([ch, _apply(ch, e, h.id)])
        out[h.id] = rows
    for it, v in zip(fam, rule_D_family(fam, q)):
        hid, i = it["_slot"]
        out[hid][i][1] = Verdict(v.rule, v.outcome, v.reason, hid, v.quantity, v.side, v.detail)
    return {hid: [tuple(r) for r in rows] for hid, rows in out.items()}


def spec() -> dict:
    """The declared rules as data: margins, gate, BH q, outcomes, and every check."""
    return {"outcomes": list(OUTCOMES), "rules": list(RULES),
            "margins": {"rel": MARGIN["rel"], "abs": MARGIN["abs"]},   # what _apply reads
            "gate_margin_pct": C.GATE_MARGIN_PCT, "bh_q": C.BH_Q,
            "hypotheses": [{"id": h.id, "claim": h.claim, "kind": h.kind,
                            "checks": [asdict(c) for c in h.checks]} for h in HYPOTHESES]}


def rules_digest() -> str:
    """sha256 over the declared spec and the source of the rule functions: what Gate 4
    pins (plan S6), so neither a margin nor a rule's code can move unseen."""
    src = "".join(inspect.getsource(f) for f in (_ci, _no_margin, rule_P, rule_D, rule_E,
                                                  rule_N, rule_G, rule_D_family, _apply))
    blob = C.canonical_json(spec()) + "\n" + src
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
