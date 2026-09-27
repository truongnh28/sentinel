"""Draft S9 metrics, intervals, BH and the prediction scorecard (T17).  Each test protects
one DCM row of v3/dcm/T17.csv; its docstring carries the id and the verbatim draft
sentence.

Every record here is SYNTHETIC and built in this file.  No eval split and no v2 eval
record is read (plan S6; the plasmode is synthetic for that reason)."""
import math
import unittest

import numpy as np

import metrics_v2 as MV
from v3 import api as A
from v3 import config as C
from v3 import metrics as M
from v3 import scorecard as S

MATCH, REJECT, INCON = S.MATCH, S.REJECT, S.INCONCLUSIVE

_DEFAULT = dict(
    split="dev", world=C.PRIMARY.as_dict(), world_id=C.world_id(C.PRIMARY),
    cell=C.Cell(rho=0.0, delta=4).as_dict(), cell_id=C.cell_id(C.Cell(rho=0.0, delta=4)),
    delta=4, wf="w1", repo="r1", H=10, order=0, seed=1, policy="B1", attack="a1",
    placement=None, k=("memory",), iota=2, sigma=6, eps=None, harm=0.0, solved_sigma=True,
    harm_locked_at=None, detected_at=None, missed_before_sigma=False, fq=0, true_q=0,
    false_removed=0, benign_inspected=0, clean_lost_branch=0, t_lost=0, n_solved=10,
    spent=0.0, budget=41.0, audits={}, c_traj=(), quarantines=(), delta_hat=None,
    n_incidents_seen=0, line5_source=None, decision_log_sha256="")


def rec(**kw) -> dict:
    """A record through the frozen api.EpisodeRecord, so every field is the contract's."""
    return A.EpisodeRecord(**{**_DEFAULT, **kw}).to_dict()


def matrix_records(W, repos, policy, cols, delta=4, seeds=(1,)):
    """Records whose per-workflow harm in column j is W[i][j] on every seed."""
    out = []
    for i, row in enumerate(W):
        for j, h in enumerate(row):
            if h is None:
                continue
            for s in seeds:
                out.append(rec(wf=f"w{i}", repo=repos[i], policy=policy, attack=cols[j],
                               delta=delta, seed=s, harm=h))
    return out


# --- a synthetic plasmode: families with random effects, several columns, 10 seeds --------
MU = np.array([0.35, 0.33, 0.30, 0.25, 0.20, 0.30, 0.28])      # base column means
GAM = np.array([0.40, 0.30, 0.20, 0.30, 0.10, 0.35, 0.25])     # candidate's cut per column
ATT = tuple(f"a{c}" for c in range(len(MU)))
V3_SIZES = [5] * 14 + [4, 3, 2, 1, 1, 1]          # ~ the D-v3-1 split: 20 families, <= 5 each
C14A_SIZES = [5, 5, 1, 1] + [1] * 14               # the former C14(a) one-pass split, 18 families


def plasmode_truth():
    vb, vc = MU.max(), (MU * (1 - GAM)).max()
    return 100 * (vb - vc) / vb, vb - vc


def plasmode(rng, sizes, seeds=10):
    """E[p_base] = MU and E[p_cand] = MU (1 - GAM) exactly: family and workflow effects
    are independent, centred, and keep every p inside (0, 1)."""
    out = []
    for g, n in enumerate(sizes):
        u, v = rng.uniform(-0.10, 0.10), rng.uniform(-0.20, 0.20)
        for i in range(n):
            pb = MU + u + rng.uniform(-0.05, 0.05)
            pc = pb * (1 - GAM - v)
            for s in range(1, seeds + 1):
                hb, hc = rng.random(len(MU)) < pb, rng.random(len(MU)) < pc
                for c in range(len(MU)):
                    base = {"split": "dev", "attack": ATT[c], "delta": 4, "wf": f"f{g}w{i}",
                            "repo": f"f{g}", "seed": s}
                    out.append({**base, "policy": "B1", "harm": float(hb[c])})
                    out.append({**base, "policy": "Sentinel", "harm": float(hc[c])})
    return out


class TestS9Metrics(unittest.TestCase):
    # ------------------------------------------------------------------------------------
    def test_seven_metrics_of_section_9_3(self):
        """D9.metrics: "Clean completion and false quarantine. Audit cost (CPUminutes) and
        detection delay. Exploitability: best-response gain against the deployed policy.
        Empirical regret against B7 on small games."  With "Worst-case verified harm
        (primary): maximum over the held-out attacker class", seven metrics, each weighted
        by workflow (a per-workflow rate averaged over workflows)."""
        H = {("w1", "a1"): (1, 0), ("w1", "a2"): (1, 1), ("w2", "a1"): (0, 0), ("w2", "a2"): (0, 1)}
        per_wf = {"w1": dict(repo="r1", n_solved=10, t_lost=1, false_removed=1, benign_inspected=4,
                             fq=1, true_q=1, spent=8.0, iota=2, detected_at=5,
                             audits={"commit": [1, 2, 3]},
                             quarantines=((3, "memory"), (4, "skill"))),
                  "w2": dict(repo="r2", n_solved=5, t_lost=0, false_removed=0, benign_inspected=2,
                             fq=0, true_q=0, spent=4.0, iota=1, detected_at=None,
                             audits={"commit": [1]}, quarantines=())}
        recs = [rec(wf=w, attack=a, seed=s + 1, harm=float(h[s]), **per_wf[w])
                for (w, a), h in H.items() for s in range(2)]
        # best response: w1 always harmed under p1; w2 always harmed under p1 -> V_BR = 1
        for w in ("w1", "w2"):
            for s in range(1, 5):
                for pl, h in (("p1", 1.0), ("p2", 0.0)):
                    recs.append(rec(wf=w, attack="BR", placement=pl, seed=s, harm=h,
                                    **per_wf[w]))
        small = [rec(split="dev", wf=g, policy=p, attack=a, delta=1, harm=h)
                 for g, p, a, h in (("g1", "B1", "a1", .4), ("g1", "B1", "a2", .6),
                                    ("g1", "B7", "a1", .5), ("g1", "B7", "a2", .5),
                                    ("g2", "B1", "a1", .3), ("g2", "B1", "a2", .2),
                                    ("g2", "B7", "a1", .3), ("g2", "B7", "a2", .1))]
        m = M.seven_metrics(recs, "B1", ("a1", "a2"), (4,), small_game_recs=small)
        # 1. worst-case harm: columns a1 = (0.5 + 0) / 2, a2 = (1 + 0.5) / 2 -> V = 0.75
        self.assertAlmostEqual(m["worst_case_harm"], 0.75, places=12)
        self.assertEqual(m["worst_column"], "a2@4")
        self.assertAlmostEqual(m["worst_case_harm"],
                               MV.value(MV.harm_table(recs, "B1", {"a1", "a2"}, {4})), places=12)
        # 2. clean completion: w1 90%, w2 100% -> 95 by workflow (v2's pooled 93.33 beside it)
        self.assertAlmostEqual(m["clean_completion"], 95.0, places=9)
        self.assertAlmostEqual(m["side"]["v2_pooled"]["clean_completion"], 100 * (1 - 4 / 60), places=9)
        # 3. false quarantine: item level 25% and 0% -> 12.5; carrier level fq 1 and 0 per episode
        self.assertAlmostEqual(m["false_quarantine_pct"], 12.5, places=9)
        self.assertAlmostEqual(m["fq_per_ep"], 0.5, places=12)
        self.assertAlmostEqual(m["side"]["fq_share_of_quarantines_pct"], 50.0, places=9)
        self.assertEqual(m["side"]["quarantines_per_ep"]["memory"], 0.5)
        # 4. audit cost (CPU-minutes per episode) and audits per target
        self.assertAlmostEqual(m["audit_cost"], 6.0, places=12)
        self.assertAlmostEqual(m["side"]["audits_per_ep"]["commit"], 2.0, places=12)
        # 5. detection delay: w1 detected 3 tasks after iota; w2 never detected (rate 50%)
        self.assertAlmostEqual(m["detection_delay"], 3.0, places=12)
        self.assertAlmostEqual(m["side"]["detection_rate_pct"], 50.0, places=9)
        # 6. exploitability = cross-fitted V_BR - V_held-out = 1 - 0.75
        self.assertAlmostEqual(m["v_br"], 1.0, places=12)
        self.assertAlmostEqual(m["exploitability"], 0.25, places=12)
        # 7. regret vs B7 on small games: g1 0.6 - 0.5, g2 0.3 - 0.3
        self.assertAlmostEqual(m["regret_vs_b7"], 0.05, places=12)
        self.assertAlmostEqual(m["regret_max"], 0.1, places=12)
        self.assertEqual(m["regret"]["n_negative"], 0)
        # records are the frozen api's fields; two splits never mix; two cells never mix
        for f in ("harm", "t_lost", "n_solved", "fq", "false_removed", "spent", "detected_at"):
            self.assertIn(f, A.record_fields())
        with self.assertRaises(ValueError):
            M.worst_case_harm(recs + [rec(split="eval")], "B1", ("a1",), (4,))
        with self.assertRaises(ValueError):
            M.worst_case_harm(recs + [recs[0]], "B1", ("a1", "a2"), (4,))
        # a negative regret is counted, never clipped
        bad = small + [rec(wf="g3", policy="B1", attack="a1", delta=1, harm=.1),
                       rec(wf="g3", policy="B7", attack="a1", delta=1, harm=.3)]
        self.assertEqual(M.regret_vs_b7(bad, "B1")["n_negative"], 1)

    # ------------------------------------------------------------------------------------
    def test_wild_cluster_bootstrap_resamples_families_and_remaxes_columns(self):
        """D9.ci (R6, L2): "intervals are cluster-bootstrapped by repository" family;
        sentinel-v3.md S9: wild cluster bootstrap (Cameron-Gelbach-Miller), Webb weights.

        One Webb weight per FAMILY per draw multiplies the residuals of every workflow of
        that family, for both systems at once, and V* is re-maxed over the columns in every
        draw, so the interval pays for choosing the worst column."""
        cols = ("c1", "c2")
        repos = ["A", "A", "B", "C"]
        Wb = [[.9, .1], [.7, .3], [.1, .9], [.2, .8]]      # c1 worst in A, c2 worst in B and C
        Wc = [[.5, .1], [.4, .2], [.1, .6], [.1, .5]]
        recs = matrix_records(Wb, repos, "B1", cols) + matrix_records(Wc, repos, "Sentinel", cols)
        g = M.gain_ci(recs, "B1", "Sentinel", cols, (4,), n_boot=2000, seed=11, method="wild",
                      return_draws=True)
        F = g["draws"]["F"]
        self.assertEqual(F.shape, (2000, 3), "one weight per family (A, B, C) per draw")
        self.assertTrue(np.isin(F, M.WEBB).all(), "every weight is a Webb six-point value")
        self.assertEqual(sorted(np.round(M.WEBB ** 2, 12)), sorted(np.round([1.5, 1, .5] * 2, 12)))
        self.assertAlmostEqual(float(M.WEBB.mean()), 0.0, places=12)
        self.assertAlmostEqual(float((M.WEBB ** 2).mean()), 1.0, places=12)
        fam = {"A": 0, "B": 1, "C": 2}

        def v_star(W, b, only=None):
            vals = []
            for j in range(len(cols)):
                if only is not None and j != only:
                    continue
                mu = sum(r[j] for r in W) / len(W)
                vals.append(mu + sum(F[b, fam[repos[i]]] * (W[i][j] - mu)
                                     for i in range(len(W))) / len(W))
            return max(0.0, max(vals))

        argmax, strictly_above_fixed = set(), 0
        for b in range(0, 2000, 7):
            vb, vc = v_star(Wb, b), v_star(Wc, b)
            self.assertAlmostEqual(g["draws"]["base"][b], vb, places=12)
            self.assertAlmostEqual(g["draws"]["cand"][b], vc, places=12, msg="paired: same F")
            per_col = [v_star(Wb, b, j) for j in range(2)]
            argmax.add(int(np.argmax(per_col)))
            strictly_above_fixed += vb > per_col[1] + 1e-12       # c2 is the point's worst column
        self.assertEqual(argmax, {0, 1}, "the worst column changes across draws: re-maxed")
        self.assertGreater(strictly_above_fixed, 0)
        self.assertAlmostEqual(g["v_base"], 0.525, places=12)
        # only family totals matter: swapping residuals inside family A leaves every draw
        swapped = matrix_records([Wb[1], Wb[0], Wb[2], Wb[3]], repos, "B1", cols) + \
            matrix_records(Wc, repos, "Sentinel", cols)
        g2 = M.gain_ci(swapped, "B1", "Sentinel", cols, (4,), n_boot=2000, seed=11,
                       method="wild", return_draws=True)
        np.testing.assert_allclose(g2["draws"]["base"], g["draws"]["base"], atol=1e-12)
        # ...whereas splitting family A into two clusters changes them
        split = matrix_records(Wb, ["A", "A2", "B", "C"], "B1", cols) + \
            matrix_records(Wc, ["A", "A2", "B", "C"], "Sentinel", cols)
        g3 = M.gain_ci(split, "B1", "Sentinel", cols, (4,), n_boot=2000, seed=11,
                       method="wild", return_draws=True)
        self.assertEqual(g3["n_repos"], 4)
        self.assertFalse(np.allclose(g3["draws"]["base"], g["draws"]["base"]))
        # the interval and p come from the draws; the point is the data's
        self.assertEqual((g["abs_lo"], g["abs_hi"]), M.interval(g["draws"]["abs"], 0.05))
        self.assertEqual(g["p_abs"], M.p_value(g["draws"]["abs"]))
        self.assertAlmostEqual(g["abs_diff"], 0.525 - 0.35, places=12)
        # reproducible: same seed, same draws
        again = M.gain_ci(recs, "B1", "Sentinel", cols, (4,), n_boot=2000, seed=11,
                          method="wild", return_draws=True)
        np.testing.assert_array_equal(again["draws"]["base"], g["draws"]["base"])

    def test_gain_ci_agrees_with_metrics_v2_gain_ci_on_synthetic_records(self):
        """D9.ci: "intervals are cluster-bootstrapped by repository" -- the v3 intervals
        against v2's metrics_v2.gain_ci, on synthetic records only.

        pairs: every draw equals metrics_v2._value_multi on the families it drew, and
        the bounds agree with gain_ci to Monte Carlo error (1 pp; 0.01 harm).  wild: same
        point and the same D21 reliability fields; bounds within 3 pp / 0.02."""
        for k in range(3):
            recs = plasmode(np.random.default_rng(100 + k), V3_SIZES)
            ref = MV.gain_ci(recs, "B1", "Sentinel", set(ATT), {4}, n_boot=10000, seed=7)
            tb = MV.harm_table(recs, "B1", set(ATT), {4})
            for method, tol_rel, tol_abs in (("pairs", 1.0, 0.01), ("wild", 3.0, 0.02)):
                g = M.gain_ci(recs, "B1", "Sentinel", ATT, (4,), n_boot=10000, seed=7,
                              method=method, return_draws=True)
                self.assertEqual(round(g["gain"], 2), ref["gain"])
                for f in ("abs_diff", "v_base", "v_cand"):
                    self.assertEqual(round(g[f], 4), ref[f], f)
                for f in ("base_events", "rel_reliable", "n_repos", "n_workflows"):
                    self.assertEqual(g[f], ref[f], f)
                for f in ("lo", "hi"):
                    self.assertLessEqual(abs(g[f] - ref[f]), tol_rel, f"{method} {f} k={k}")
                for f in ("abs_lo", "abs_hi"):
                    self.assertLessEqual(abs(g[f] - ref[f]), tol_abs, f"{method} {f} k={k}")
                if method == "pairs":
                    fams = sorted({r["repo"] for r in recs})
                    wf_of = {f: sorted({r["wf"] for r in recs if r["repo"] == f}) for f in fams}
                    F = g["draws"]["F"]
                    for b in range(0, 10000, 97):
                        ws = [w for j, f in enumerate(fams) for _ in range(int(F[b, j]))
                              for w in wf_of[f]]
                        self.assertAlmostEqual(g["draws"]["base"][b], MV._value_multi(tb, ws),
                                               places=12)

    def test_wild_bootstrap_coverage_on_synthetic_plasmode(self):
        """D9.ci (R6): "Instances from one workflow are correlated"; the wild interval's
        coverage is checked on a plasmode before any v3 number.

        SYNTHETIC plasmode (no v2 eval record may be read): families with random effects,
        7 columns, 10 seeds, known true V and gain, in the D-v3-1 family structure (20
        families of <= 5) and the former C14(a) one (18 families, two big).  The 95% wild
        interval of both the relative gain and the absolute difference covers the truth
        at least 90% of the time; the pairs interval is computed beside it (R6)."""
        tg, ta = plasmode_truth()
        for label, sizes, seed in (("D-v3-1", V3_SIZES, 1), ("C14(a)", C14A_SIZES, 2)):
            rng = np.random.default_rng(seed)
            hit = {m: [0, 0] for m in M.METHODS}
            reps = 200
            for rep in range(reps):
                recs = plasmode(rng, sizes)
                for m in M.METHODS:
                    g = M.gain_ci(recs, "B1", "Sentinel", ATT, (4,), n_boot=999, seed=rep,
                                  method=m)
                    hit[m][0] += g["lo"] <= tg <= g["hi"]
                    hit[m][1] += g["abs_lo"] <= ta <= g["abs_hi"]
            cov = {m: (h[0] / reps, h[1] / reps) for m, h in hit.items()}
            for c in cov["wild"]:
                self.assertGreaterEqual(c, 0.90, f"{label}: wild coverage {cov}")
                self.assertLessEqual(c, 0.995, f"{label}: wild interval far too wide {cov}")
            for c in cov["pairs"]:
                self.assertGreaterEqual(c, 0.85, f"{label}: pairs coverage {cov}")

    # ------------------------------------------------------------------------------------
    def test_bh_at_q_005(self):
        """D9.bh (sentinel-v3.md S9: BH, q = 0.05): "Results are reported on the (Δ, χ)
        grid rather than pooled" -- many comparisons, so the D family is BH-adjusted.

        Benjamini & Hochberg (1995)'s own 15 p-values reject 4 at q = 0.05; the procedure
        is step-UP; a NaN p counts in m and is never rejected; a D hypothesis BH does not
        reject is INCONCLUSIVE even when its unadjusted CI excludes 0."""
        self.assertEqual(C.BH_Q, 0.05)
        p = [0.0001, 0.0004, 0.0019, 0.0095, 0.0201, 0.0278, 0.0298, 0.0344, 0.0459,
             0.3240, 0.4262, 0.5719, 0.6528, 0.7590, 1.000]
        r = M.bh(p)
        self.assertEqual(r["q"], 0.05)
        self.assertEqual(r["k"], 4)
        self.assertEqual(r["reject"], [True] * 4 + [False] * 11)
        self.assertAlmostEqual(r["p_adj"][0], 0.0015, places=12)
        self.assertAlmostEqual(r["p_adj"][3], 0.0095 * 15 / 4, places=12)
        self.assertEqual(r["p_adj"], [max(r["p_adj"][:i + 1]) for i in range(15)], "monotone")
        shuffled = [p[i] for i in (14, 3, 0, 9, 2, 1)]
        self.assertEqual(M.bh(shuffled)["reject"], [False, True, True, False, True, True])
        # step-up: 0.04 > 0.05/3 alone, but the largest passing rank carries it
        self.assertEqual(M.bh([0.04, 0.041, 0.042])["reject"], [True, True, True])
        self.assertEqual(M.bh([0.04, 0.041, 0.06])["reject"], [False, False, False])
        self.assertEqual(M.bh([0.01, float("nan")])["reject"], [True, False])
        self.assertEqual(M.bh([0.03, float("nan")])["reject"], [False, False], "NaN counts in m")
        # the D family: three hypotheses whose unadjusted 95% CIs all exclude 0
        est = lambda pt, pv: S.Estimate(lo=pt - 1, hi=pt + 1, point=pt * 2, p=pv)
        fam = [{"name": "x", "estimate": est(2, 0.001), "sign": +1},
               {"name": "y", "estimate": est(-2, 0.004), "sign": +1},
               {"name": "z", "estimate": est(2, 0.049), "sign": +1},
               {"name": "u", "estimate": est(0.5, 0.60), "sign": +1}]
        out = S.rule_D_family(fam, q=0.05)
        self.assertEqual([v.outcome for v in out], [MATCH, REJECT, INCON, INCON])
        self.assertIn("does not reject", out[2].reason)
        self.assertEqual(S.rule_D(fam[2]["estimate"].lo, fam[2]["estimate"].hi, +1).outcome, MATCH,
                         "unadjusted it would have matched")
        # an Estimate from bootstrap draws: p < alpha exactly when the interval excludes 0
        draws = np.linspace(-0.01, 0.99, 1000)
        e = S.Estimate.from_draws(0.5, draws, alpha=0.05)
        self.assertEqual((e.lo, e.hi), M.interval(draws, 0.05))
        self.assertEqual(int((draws <= 0).sum()), 10)
        self.assertAlmostEqual(e.p, 2 * 10 / 1000, places=12)
        self.assertEqual(e.p < 0.05, e.lo > 0 or e.hi < 0)

    # ------------------------------------------------------------------------------------
    def test_rule_P_match_reject_inconclusive_are_disjoint(self):
        """D9.ruleP (Q12): "Against held-out adaptive attacker policies the reduction is
        27.6%."  P: match if the whole 95% CI lies in [projection - delta; projection +
        delta]; reject if it does not meet that band; otherwise inconclusive, also when the
        CI is wider than 2 delta.  delta = 10 points (reductions), 0.10 (harm).

        The doc's case: projection 27.6, CI [29; 31].  Under the old rule ("reject if the CI
        does not contain the projection") with delta = 5 it both matched and was rejected;
        now it only matches, at delta = 10 and at delta = 5."""
        self.assertEqual((C.DELTA_REL_POINTS, C.DELTA_ABS_HARM), (10.0, 0.10))
        self.assertEqual((S.MARGIN["rel"], S.MARGIN["abs"]), (10.0, 0.10))
        p, d = 27.6, 10.0
        self.assertEqual(S.rule_P(29, 31, p, d).outcome, MATCH)
        self.assertEqual(S.rule_P(29, 31, p, 5.0).outcome, MATCH)
        self.assertFalse(29 <= p <= 31, "the old rule would have rejected it")
        # a CI disjoint from the band is rejected, on either side
        self.assertEqual(S.rule_P(40, 45, p, d).outcome, REJECT)
        self.assertEqual(S.rule_P(5, 17, p, d).outcome, REJECT)
        # boundaries: containment is inclusive; touching the band is meeting it
        self.assertEqual(S.rule_P(p - d, p + d, p, d).outcome, MATCH)
        self.assertEqual(S.rule_P(p + d, p + d + 3, p, d).outcome, INCON)
        self.assertEqual(S.rule_P(p - d - 3, p - d, p, d).outcome, INCON)
        self.assertEqual(S.rule_P(np.nextafter(p + d, 99), 45, p, d).outcome, REJECT)
        self.assertEqual(S.rule_P(20, 40, p, d).outcome, INCON)          # overlaps the top edge
        wide = S.rule_P(10, 45, p, d)
        self.assertEqual(wide.outcome, INCON)
        self.assertIn("wider than 2 delta", wide.reason)
        # harm scale
        self.assertEqual(S.rule_P(0.40, 0.50, 0.456, 0.10).outcome, MATCH)
        self.assertEqual(S.rule_P(0.20, 0.30, 0.456, 0.10).outcome, REJECT)
        # the three outcomes are disjoint and exhaustive over a grid of CIs
        grid = np.round(np.arange(0.0, 50.01, 0.8), 6)
        for lo in grid:
            for hi in grid[grid >= lo]:
                v = S.rule_P(float(lo), float(hi), p, d)
                inside = p - d <= lo and hi <= p + d
                disjoint = hi < p - d or lo > p + d
                self.assertFalse(inside and disjoint)
                self.assertEqual(v.outcome, MATCH if inside else REJECT if disjoint else INCON,
                                 (lo, hi))
        # no finite CI, no declared delta, an unreliable relative gain: inconclusive
        self.assertEqual(S.rule_P(float("nan"), 30, p, d).outcome, INCON)
        self.assertEqual(S.rule_P(29, 31, p, None).outcome, INCON)
        self.assertIn("no declared delta", S.rule_P(29, 31, p, None).reason)
        self.assertEqual(S.rule_P(29, 31, p, d, reliable=False).outcome, INCON)
        with self.assertRaises(ValueError):
            S.rule_P(31, 29, p, d)
        self.assertTrue(S.rule_P(29, 31, p, d).reason)

    def test_rule_D_signs(self):
        """D9.ruleD: "Heterogeneity shrinks the gain and delays the crossover".  D: match if
        the CI of the difference excludes 0 with the predicted sign; reject if it excludes 0
        with the other sign; otherwise inconclusive."""
        self.assertEqual(S.rule_D(1, 2, +1).outcome, MATCH)
        self.assertEqual(S.rule_D(1, 2, -1).outcome, REJECT)
        self.assertEqual(S.rule_D(-2, -1, -1).outcome, MATCH)
        self.assertEqual(S.rule_D(-2, -1, +1).outcome, REJECT)
        self.assertEqual(S.rule_D(-1, 1, +1).outcome, INCON)
        self.assertEqual(S.rule_D(0, 2, +1).outcome, INCON, "a bound at 0 does not exclude 0")
        self.assertEqual(S.rule_D(-2, 0, -1).outcome, INCON)
        self.assertEqual(S.rule_D(1e-12, 2, +1).outcome, MATCH)
        self.assertEqual(S.rule_D(float("nan"), 2, +1).outcome, INCON)
        for bad in (0, 2, None):
            with self.assertRaises(ValueError):
                S.rule_D(1, 2, bad)

    def test_rule_E_equivalence(self):
        """D9.ruleE: "At Δ ≤ 1 with uniform carriers the difference is within noise."  E:
        match if the CI of the difference lies in [-delta; delta]; reject if it lies wholly
        outside; otherwise inconclusive."""
        d = 10.0
        self.assertEqual(S.rule_E(-10, 10, d).outcome, MATCH)
        self.assertEqual(S.rule_E(-3, 4, d).outcome, MATCH)
        self.assertEqual(S.rule_E(10.5, 12, d).outcome, REJECT)
        self.assertEqual(S.rule_E(-12, -10.5, d).outcome, REJECT)
        self.assertEqual(S.rule_E(10, 12, d).outcome, INCON, "touching the edge is not outside")
        self.assertEqual(S.rule_E(-12, -10, d).outcome, INCON)
        self.assertEqual(S.rule_E(5, 15, d).outcome, INCON)
        self.assertEqual(S.rule_E(-15, 15, d).outcome, INCON, "wider than the band")
        self.assertEqual(S.rule_E(-0.05, 0.08, 0.10).outcome, MATCH)
        self.assertEqual(S.rule_E(-3, 4, None).outcome, INCON)

    def test_rule_N_non_inferiority(self):
        """D9.ruleN (H20): "a practitioner whose workflows are short should implement B1 and
        stop."  N on V_S - V_B1: match if the lower bound > -delta; reject if the upper bound
        < -delta; otherwise inconclusive (delta = 0.10 harm)."""
        d = C.DELTA_ABS_HARM
        self.assertEqual(S.rule_N(-0.05, 0.10, d).outcome, MATCH)
        self.assertEqual(S.rule_N(-0.30, -0.15, d).outcome, REJECT)
        self.assertEqual(S.rule_N(-0.20, 0.00, d).outcome, INCON)
        self.assertEqual(S.rule_N(-d, 0.05, d).outcome, INCON, "lower bound = -delta is not > -delta")
        self.assertEqual(S.rule_N(-0.30, -d, d).outcome, INCON, "upper bound = -delta is not < -delta")
        self.assertEqual(S.rule_N(np.nextafter(-d, 0), 0.2, d).outcome, MATCH)
        h20 = S.BY_ID["H20"].checks[0]
        self.assertEqual((h20.rule, h20.margin, S.MARGIN[h20.margin]), ("N", "abs", 0.10))

    def test_rule_G_lower_bound_15(self):
        """D9.4.gate (S9.4): "Worst-case harm against heldout attacker policies at equal
        budget is the preregistered primary endpoint against B1 with a 15% relative margin."
        G: the lower bound of the reduction is at least 15%."""
        self.assertEqual(C.GATE_MARGIN_PCT, 15.0)
        self.assertEqual(S.rule_G(15.0, 30.0).outcome, MATCH, "at least 15: inclusive")
        self.assertEqual(S.rule_G(22.0, 40.0).outcome, MATCH)
        self.assertEqual(S.rule_G(np.nextafter(15.0, 0), 30.0).outcome, INCON)
        self.assertEqual(S.rule_G(-5.0, 14.9).outcome, REJECT)
        self.assertEqual(S.rule_G(-5.0, 15.0).outcome, INCON)
        self.assertEqual(S.rule_G(20.0, 30.0, reliable=False).outcome, INCON)
        self.assertEqual(S.rule_G(float("nan"), 30.0).outcome, INCON)
        # H1 reads G and P on the same held-out gain
        e = S.Estimate(lo=18.0, hi=31.0, point=25.0, p=0.001)
        v = dict((ch.rule, res) for ch, res in S.score("H1", {"gain_heldout": e}))
        self.assertEqual(v["G"].outcome, MATCH)
        self.assertEqual(v["P"].outcome, MATCH)          # [18; 31] in [17.6; 37.6]

    # ------------------------------------------------------------------------------------
    def test_controls_are_read_before_any_sentinel_number(self):
        """D9.controls (D28, L2): "This is what makes worst-case harm computable" -- the
        oracle (+) and Delta = 0 (-) controls are read before any Sentinel number."""
        recs = []
        for w, rp in (("w1", "r1"), ("w2", "r2")):
            for d in (4, 8):
                recs.append(rec(wf=w, repo=rp, policy="Oracle", delta=d, harm=0.0))
                recs.append(rec(wf=w, repo=rp, policy="B1", delta=d, harm=0.6))
                recs.append(rec(wf=w, repo=rp, policy="Sentinel-v3", delta=d, harm=0.3))
            recs.append(rec(wf=w, repo=rp, policy="B1", delta=0, harm=0.5))
            recs.append(rec(wf=w, repo=rp, policy="B2", delta=0, harm=0.6))
        ro = M.Readout(recs)
        self.assertAlmostEqual(ro.worst_case_harm("B1", ("a1",), (4, 8))["v"], 0.6)
        with self.assertRaises(M.ControlsNotRead):
            ro.worst_case_harm("Sentinel-v3", ("a1",), (4, 8))
        with self.assertRaises(M.ControlsNotRead):
            ro.gain_ci("B1", "Sentinel-v3", ("a1",), (4, 8), n_boot=50)
        with self.assertRaises(M.ControlsNotRead):
            ro.side("Sentinel-v3", ("a1",), (4, 8))
        c = ro.controls("Oracle", "B1", ["B2"], ("a1",))
        self.assertTrue(c["ok"])
        self.assertAlmostEqual(ro.worst_case_harm("Sentinel-v3", ("a1",), (4, 8))["v"], 0.3)
        self.assertAlmostEqual(ro.gain_ci("B1", "Sentinel-v3", ("a1",), (4, 8),
                                          n_boot=50)["gain"], 50.0)
        # a failed positive control (Oracle above 0.05) blocks every Sentinel number
        bad = [dict(r, harm=0.3) if r["policy"] == "Oracle" else r for r in recs]
        ro2 = M.Readout(bad)
        self.assertFalse(ro2.controls("Oracle", "B1", ["B2"], ("a1",))["positive_ok"])
        with self.assertRaises(M.ControlsFailed):
            ro2.worst_case_harm("Sentinel-v3", ("a1",), (4, 8))
        # a failed negative control: a sweeper beats B1 at Delta = 0
        bad2 = [dict(r, harm=0.1) if r["policy"] == "B2" else r for r in recs]
        ro3 = M.Readout(bad2)
        self.assertFalse(ro3.controls("Oracle", "B1", ["B2"], ("a1",))["negative_ok"])
        with self.assertRaises(M.ControlsFailed):
            ro3.seven_metrics("Sentinel-v3", ("a1",), (4, 8))
        # a control with no record is not a passed control
        ro4 = M.Readout(recs)
        self.assertFalse(ro4.controls("Oracle", "B1", ["B9"], ("a1",))["ok"])
        self.assertEqual(M.CONTROL_MAX_HARM, 0.05)

    def test_table_rollout_fidelity_row_is_printed(self):
        """DA1.l5 (Q13, O12): "Line 5 is what runs at scale" -- from the precomputed table
        in every cell; the headline rollout is printed beside it as |V_table - V_rollout|
        with its CI.  Not a hypothesis: no verdict; above 0.10 the headline number carries
        the label "bảng lệch rollout"."""
        def recs_for(shift):
            out = []
            for i, rp in enumerate(("r1", "r1", "r2", "r3", "r4")):
                for s in (1, 2):
                    h = 0.2 + 0.05 * i
                    out.append(rec(wf=f"w{i}", repo=rp, policy="Sentinel-v3", seed=s, harm=h,
                                   line5_source="table"))
                    out.append(rec(wf=f"w{i}", repo=rp, policy="Sentinel-v3", seed=s,
                                   harm=h + shift, line5_source="rollout"))
            return out
        close = M.table_rollout_fidelity(recs_for(0.02), "Sentinel-v3", ("a1",), (4,), n_boot=500)
        self.assertAlmostEqual(close["abs_diff"], 0.02, places=12)
        self.assertFalse(close["flag"])
        self.assertEqual(close["label"], "")
        line = M.fidelity_line(close)
        self.assertIn("not a hypothesis", line)
        self.assertIn("V_table 0.3000", line)
        self.assertIn("V_rollout 0.3200", line)
        self.assertIn(f"[{close['abs_lo']:.4f}, {close['abs_hi']:.4f}]", line)
        self.assertNotIn(M.FIDELITY_LABEL, line)
        far = M.table_rollout_fidelity(recs_for(0.15), "Sentinel-v3", ("a1",), (4,), n_boot=500)
        self.assertTrue(far["flag"])
        self.assertEqual(far["label"], "bảng lệch rollout")
        self.assertIn("bảng lệch rollout", M.fidelity_line(far))
        self.assertEqual(C.TABLE_ROLLOUT_FLAG, 0.10)
        self.assertNotIn("outcome", far)
        missing = M.table_rollout_fidelity([r for r in recs_for(0.0) if r["line5_source"] == "table"],
                                           "Sentinel-v3", ("a1",), (4,), n_boot=50)
        self.assertTrue(math.isnan(missing["diff"]))
        self.assertIn("nan", M.fidelity_line(missing))

    def test_scorecard_frame_holds_h1_to_h20(self):
        """D9.scorecard (T4 of sentinel-v3.md): "They are placeholders that fix the analysis
        and presentation in advance, not measurements."  Each projection is a hypothesis
        with its rule, hashed before the run."""
        self.assertEqual([h.id for h in S.HYPOTHESES], [f"H{i}" for i in range(1, 21)])
        kinds = {"H1": "G + P", "H2": "P", "H3": "P + D; E trên arm chỉ đổi giá", "H4": "P",
                 "H5": "D", "H6": "D", "H7": "P", "H8": "D", "H9": "P", "H10": "P",
                 "H11": "P + D", "H12": "P + D", "H13": "D", "H14": "D", "H15": "D",
                 "H16": "D", "H17": "D", "H18": "D; E cho vế χ", "H19": "D", "H20": "N"}
        for h in S.HYPOTHESES:
            self.assertEqual(h.kind, kinds[h.id])
            letters = {x for x in "PDENG" if x in h.kind.replace("trên", "").replace("cho vế", "")}
            self.assertEqual({c.rule for c in h.checks}, letters, h.id)
            for c in h.checks:
                self.assertIn(c.margin, S.MARGIN)
                if c.rule == "D":
                    self.assertIn(c.sign, (1, -1))
                if c.rule == "P":
                    self.assertIsNotNone(c.projection)
        proj = {(h.id, c.quantity): c.projection for h in S.HYPOTHESES for c in h.checks
                if c.rule == "P"}
        self.assertEqual(proj[("H1", "gain_heldout")], 27.6)
        self.assertEqual(proj[("H4", "gain_delta0")], -1.2)
        self.assertEqual(proj[("H9", "exploitability_sentinel")], 0.09)
        self.assertEqual(proj[("H12", "v_minus_randomization")], 0.456)
        self.assertEqual(proj[("H11", "gain_llm")], 41.2)
        # nothing run yet: every check is 'not run', never an outcome
        allv = S.score_all({})
        self.assertTrue(all(res == S.NOT_RUN for rows in allv.values() for _, res in rows))
        # H18 / H19 put the draft beside the note: one estimate, opposite verdicts
        e = S.Estimate(lo=-2.0, hi=-0.5, point=-1.2, p=0.001)
        out = S.score_all({"gain_slope_in_kd": e})
        sides = {ch.side: res.outcome for ch, res in out["H19"]}
        self.assertEqual(sides, {"draft": REJECT, "note": MATCH})
        # the digest is stable and moves with a margin or a projection
        dg = S.rules_digest()
        self.assertRegex(dg, r"^[0-9a-f]{64}$")
        self.assertEqual(dg, S.rules_digest())
        self.assertEqual(S.spec()["margins"], {"rel": 10.0, "abs": 0.10})
        old = S.MARGIN["rel"]
        try:
            S.MARGIN["rel"] = 5.0
            self.assertNotEqual(dg, S.rules_digest())
        finally:
            S.MARGIN["rel"] = old
        self.assertEqual(dg, S.rules_digest())

    def test_learning_curve_prints_delta_hat_by_incidents_seen(self):
        """DA1.l1 (C12, R4, R5): "Δ, χb ← estimate delay and heterogeneity from history" --
        the learning curve: Delta-hat and harm by the number of post-mortems seen, the
        prior-only workflow reported apart."""
        recs = [rec(wf="w0", policy="Sentinel-v3", n_incidents_seen=0, order=0, delta_hat=1, harm=1.0),
                rec(wf="w1", policy="Sentinel-v3", n_incidents_seen=1, order=1, delta_hat=4, harm=0.0),
                rec(wf="w2", policy="Sentinel-v3", n_incidents_seen=2, order=2, delta_hat=4, harm=0.5),
                rec(wf="w2", policy="Sentinel-v3", n_incidents_seen=2, order=2, delta_hat=4, harm=0.0,
                    seed=2)]
        lc = M.learning_curve(recs, "Sentinel-v3", ("a1",), (4,))
        self.assertEqual([r["n_incidents_seen"] for r in lc], [0, 1, 2])
        self.assertEqual([r["prior_only"] for r in lc], [True, False, False])
        self.assertEqual([r["delta_hat_exact_pct"] for r in lc], [0.0, 100.0, 100.0])
        self.assertEqual([r["mean_harm"] for r in lc], [1.0, 0.0, 0.25])
        self.assertEqual(len(M.with_postmortems(recs)), 3)


if __name__ == "__main__":
    unittest.main()
