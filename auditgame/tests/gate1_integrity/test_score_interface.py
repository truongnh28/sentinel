"""
GATE 1 -- the score interface (B0.5).  Spec: SPEC-Tang-Do-va-Test.md SS2.5-2.6.

A test's NAME states the claim it defends; the Vietnamese wording of that claim
lives in the docstring under `Thesis claim (vi):`.

These tests sample from the SPECIFIED distribution directly and do not go through
Detector -- because B0.5 fixes the INTERFACE while B1 wires the detector in.  That
boundary is deliberate: if these tests had to wait for B1, B0.5 could no longer
gate B1.
"""
from __future__ import annotations
import math, random, statistics, unittest

import scoring
from core import seed_of

SETTINGS = ("weak", "mid", "strong")
M = 40_000                       # enough to separate 0.097 from 0.128; keeps the test under ~10s


def _sample_carrier(n: int, poisoned: bool, d_prime: float, rng: random.Random) -> float:
    """Aggregate score of an n-item carrier.  `poisoned` => exactly ONE poisoned item."""
    raw = [rng.gauss(d_prime if (poisoned and i == 0) else 0.0, 1.0) for i in range(n)]
    return scoring.carrier_score(raw, d_prime)


class ScoreInterface(unittest.TestCase):

    def test_no_clean_carrier_reads_hotter_than_a_poisoned_one(self):
        """RQ2 and RQ4 are both read through this aggregation.  If a crowded CLEAN
        carrier reads hotter than one CONTAINING the payload, then the carrier score
        is measuring ITEM COUNT rather than poison -- and both RQs lose their ground.

        This is B0.5's PRIMARY test.  Red under noisy-OR and max-p, green under
        mean-Lambda.

        Thesis claim (vi): "chi lon => loi the lon" (RQ2) and "phan bo bu cho chat
        luong phat hien" (RQ4).
        """
        for setting in SETTINGS:
            dp = scoring.d_prime_of(setting)
            clean, pois = {}, {}
            for n in (1, 2, 9, 20):
                rng = random.Random(seed_of("sep", setting, n))
                clean[n] = statistics.fmean(_sample_carrier(n, False, dp, rng) for _ in range(M))
                if n > 1:
                    pois[n] = statistics.fmean(_sample_carrier(n, True, dp, rng) for _ in range(M))
            with self.subTest(setting=setting):
                self.assertGreater(
                    min(pois.values()), max(clean.values()),
                    f"[{setting}] separation BROKEN: max(clean)={max(clean.values()):.4f} "
                    f">= min(poisoned)={min(pois.values()):.4f}. The aggregation is measuring "
                    f"item count, not poison. clean={ {k: round(v,4) for k,v in clean.items()} } "
                    f"poisoned={ {k: round(v,4) for k,v in pois.items()} }")

    def test_an_empty_carrier_is_unobserved_not_known_clean(self):
        """An empty carrier must give pi0, not 0.  Harmless before D5 because
        queue/branch were always empty; AFTER D5, empty no longer means safe.

        Thesis claim (vi): "carrier rong la CHUA QUAN SAT, khong phai DA BIET SACH".
        """
        for setting in SETTINGS:
            with self.subTest(setting=setting):
                self.assertAlmostEqual(
                    scoring.carrier_score([], scoring.d_prime_of(setting)), scoring.PI0,
                    places=12, msg="an empty carrier must return the prior pi0")

    def test_weighted_lambda_scale_is_right_skewed(self):
        """The LEFT side of the sandwich bound, tested through an EXACTLY EQUIVALENT
        quantity:

            max(-C/n, -pi0) < E[p_c|clean,n] - pi0  <=>  E[X^3/(1+pi0 X)] >= 0

        One scalar instead of a grid: cheaper, and when it goes red it names the
        EXACT cause (Lambda_bar's right skew no longer beats the weight) rather than
        "some cell is off".

        The comparison threshold is MONTE CARLO ERROR, not an absolute 0 -- the
        margin shrinks like 1/n^2 (weak runs 70.2 -> 0.22 over n=1..50).

        Thesis claim (vi): "chan kep cua thien lech gop".
        """
        for setting in SETTINGS:
            dp = scoring.d_prime_of(setting)
            for n in (1, 2, 9, 20):
                rng = random.Random(seed_of("cubic", setting, n))
                vals = []
                for _ in range(M):
                    lam = sum(scoring.likelihood_ratio(rng.gauss(0.0, 1.0), dp)
                              for _ in range(n)) / n
                    x = lam - 1.0
                    vals.append(x ** 3 / (1.0 + scoring.PI0 * x))
                mean = statistics.fmean(vals)
                se = statistics.stdev(vals) / math.sqrt(M)
                with self.subTest(setting=setting, n=n):
                    self.assertGreater(
                        mean, -3.0 * se,
                        f"[{setting} n={n}] E[X^3/(1+pi0*X)]={mean:.4g} is more than "
                        f"3*SE={3*se:.4g} below zero: the left side of the -C/n sandwich "
                        f"bound NO LONGER HOLDS, so the aggregation's bias magnitude "
                        f"cannot be stated.")

    def test_drift_matches_reference_table(self):
        """Does the frozen table still describe the aggregation that is running?

        Red means the table and the code have drifted apart -- and since tau_sel is
        looked up FROM this table, every B5/B6 operating point becomes wrong.

        Thesis claim (vi): "bang da freeze con mo ta dung phep gop dang chay".
        """
        for setting in SETTINGS:
            dp = scoring.d_prime_of(setting)
            for n in (1, 2, 9, 20):
                rng = random.Random(seed_of("drift", setting, n))
                vals = [_sample_carrier(n, False, dp, rng) for _ in range(M)]
                mean = statistics.fmean(vals)
                se = statistics.stdev(vals) / math.sqrt(M)
                ref = scoring.expected_clean_score(n, setting)
                with self.subTest(setting=setting, n=n):
                    self.assertLess(
                        abs(mean - ref), 4.0 * se,
                        f"[{setting} n={n}] measured {mean:.5f} vs table {ref:.5f}, "
                        f"off by {abs(mean-ref):.5f} > 4*SE={4*se:.5f}. "
                        f"Table and code have drifted apart -- regenerate the table, do not "
                        f"hand-edit it.")

    def test_aggregation_bias_is_always_negative(self):
        """The RIGHT side of the sandwich bound: algebra, no Jensen needed.

        X^2/(1+pi0*X) > 0 POINTWISE because 1+pi0*X = pi0*Lambda_bar + (1-pi0) > 0.
        So a small carrier is UNDER-rated, never inflated -- the aggregation's error
        falls on the SAFE side for the conclusion.

        Thesis claim (vi): "thien lech gop luon am".
        """
        for setting in SETTINGS:
            for n in (1, 2, 9, 20, 30):
                with self.subTest(setting=setting, n=n):
                    self.assertLess(
                        scoring.expected_clean_score(n, setting), scoring.PI0,
                        f"[{setting} n={n}] E[p_c|clean] >= pi0: the bias changed sign, "
                        f"the aggregation is INFLATING clean carriers.")

    def test_item_id_is_stable_across_constructions(self):
        """item_id must be a FUNCTION OF CONTENT, not a counter.

        A module-level `core._ids = itertools.count(1)` made item_id depend on HOW
        MANY Items had been created earlier in the same process.  Not just a label
        change: the detector seeds on seed_of(seed, item_id), so it changed the
        SCORES too.  Measured: B5 gave 0.417 / 0.583 / 0.333 across THREE identical
        worst_case calls -- a 0.25 swing on the harm scale, larger than the thesis's
        own 15% gate.

        Same class as hash() in build.py, but harder to see: hash() varies between
        processes, this one varies WITHIN one process with call order.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        from core import Item

        def make():
            return Item(carrier="memory", topic="orm", content="note",
                        created_at=1, provenance="agent/notes", poisoned=False)

        ids = [make().item_id for _ in range(5)]
        self.assertEqual(
            len(set(ids)), 1,
            f"item_id changes across IDENTICAL constructions: {ids}. "
            f"A global counter => 'the results are reproducible' loses its support, and "
            f"since the detector seeds on item_id, the SCORES change too.")
        # and two items with different content must still be DISTINGUISHABLE
        other = Item(carrier="memory", topic="orm", content="a DIFFERENT note",
                     created_at=1, provenance="agent/notes", poisoned=False)
        self.assertNotEqual(other.item_id, ids[0],
                            "two items with different content must have different ids")

    def test_injection_does_not_change_the_score_of_clean_items(self):
        """The claim under test is runner.py's OPENING sentence:

            "Run the pair on the same seed, changing EXACTLY one variable: inject or not"

        With a global counter, inject() consumed a count value => EVERY item created
        afterwards shifted id => shifted detector score.  Measured: 0/9 clean notes
        shared an id between the two arms, 17 ids appeared in only one arm.  So
        injection did not merely add a payload -- it RESHUFFLED THE SCORES of every
        clean item behind it.

        Heavier than B5's 0.25 swing: B5 is ONE baseline, pairing is the MEASUREMENT
        METHOD.  If this claim is false, every clean/injected comparison is
        meaningless.

        Thesis claim (vi): "tiem khong doi diem cua item sach".
        """
        import random
        import build, agent, detector
        from core import CarrierStore

        det = detector.Detector.from_setting("mid")
        ag = agent.MockAgent()

        wf = build.make_workflow("wf-000", "django", 8, random.Random(seed_of(2026, 0)))
        ps = build.plan_poison(wf, "memory", 2, random.Random(seed_of(9, 0)))

        def arm(do_inject: bool) -> dict:
            st = CarrierStore()
            for t, task in enumerate(wf.tasks):
                if do_inject and t == ps.iota:      # LAZY, matching runner.run_once
                    build.inject(st, wf, ps)
                ag.run_task(t, task, st, seed=1, marker=ps.marker)
            # ONLY clean items CREATED BEFORE sigma.  After sigma, divergence is
            # genuinely CAUSAL: the payload fires, so branch commits inherit the
            # poison (D5).  Before sigma, NO mechanism may make the two arms differ
            # -- that is the actual invariant, and it is stricter than a count with
            # a tolerance.
            return {it.item_id: round(det.score(it, 7, 1), 9)
                    for it in st.live()
                    if not it.poisoned and it.created_at < ps.sigma}

        clean, injected = arm(False), arm(True)
        drift = {k: (clean[k], injected[k])
                 for k in set(clean) & set(injected) if clean[k] != injected[k]}

        self.assertFalse(
            drift,
            f"injection CHANGED THE SCORE of {len(drift)} clean items: {list(drift.items())[:3]}. "
            f"The clean/injected pairing no longer 'changes exactly one variable'.")
        self.assertEqual(
            set(clean), set(injected),
            f"clean items BEFORE sigma differ between the two arms: "
            f"clean-only={sorted(set(clean)-set(injected))[:3]} "
            f"injected-only={sorted(set(injected)-set(clean))[:3]}. "
            f"Injection is reshuffling identities, not merely adding a payload.")

    def test_alpha_is_a_per_task_budget_not_a_per_carrier_one(self):
        """A policy scores ALL FOUR carriers each task.  Taking alpha_c=5% per
        carrier gives FP/task = 1-0.95^4 = 18.5%, not 5%.  And budget spent on a
        false alarm IS the mechanism that generates the T_lost measured in SS4.1.

        Thesis claim (vi): "alpha la ngan sach MOI TASK, khong phai moi carrier".
        """
        for k in (1, 2, 3, 4):
            with self.subTest(K=k):
                per_task = 1.0 - (1.0 - scoring.alpha_carrier(k)) ** k
                self.assertAlmostEqual(
                    per_task, scoring.ALPHA_TASK, places=12,
                    msg=f"K={k}: FP/task={per_task:.4f} != alpha_task={scoring.ALPHA_TASK}")

    def test_tau_sel_is_indexed_by_both_n_and_setting(self):
        """tau_sel REVERSES DIRECTION across settings: weak decreases with n, strong
        INCREASES.

        RQ4 compares weak against strong.  A fixed tau makes the n_c bias run in
        OPPOSITE directions on the two branches -- a sign-flipping artifact, not
        something that can be subtracted out.

        Thesis claim (vi): "tau_sel chi so theo CA n_c LAN cai dat detector".
        """
        w = [scoring.tau_sel(n, "weak", 1) for n in (1, 2, 9, 20, 30)]
        s = [scoring.tau_sel(n, "strong", 1) for n in (1, 2, 9, 20, 30)]
        self.assertLess(w[-1], w[0], f"weak must DECREASE with n, measured {w}")
        self.assertGreater(s[-1], s[0], f"strong must INCREASE with n, measured {s}")
        self.assertGreater(
            max(w + s) - min(w + s), 0.05,
            "the tau_sel range is too narrow to conclude anything -- recheck the reference table")


if __name__ == "__main__":
    unittest.main()
