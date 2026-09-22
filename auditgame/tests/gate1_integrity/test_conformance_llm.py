"""
GATE 1 -- CONFORMANCE CONTRACTS for the fifth port: LLMPipeline (L1-L4).
Spec: docs/thesis/pipelines/SPEC-Framework-Benchmark.md Parts 1.1 and 2.5; docs/thesis/pipelines/SPEC-P2-Agent.md
      Parts 1b-2 and docs/thesis/eval/PLAN.md Task 15 (p2.2).

WHY A FIFTH PORT AT ALL.  `AgentScope` used to carry `deterministic` and
`cost_usd_per_task`.  Both are properties of the MODEL, not of the scaffold: swap
the scaffold and they do not move, swap the model and they move hard.  A settable
thing hiding inside another port is the hidden constant Rule 1 forbids, and it is
also what makes "is the effect from the model or from the system" unanswerable.

WHAT THESE TESTS REFUSE TO LET HAPPEN.  Every one of L1-L4 is a way the budget can
be wrong while every number on the screen still looks fine:

  L1  the prices are from the past           -> the budget is a number about 2025
  L2  a declared cache that hits 0%          -> the budget is wrong by up to 50x,
                                                SILENTLY, invoice after the run
  L3  `deterministic` declared wrong         -> I1 and replay lose their footing
  L4  no estimate before running             -> money runs out mid-grid and half
                                                the table is unreadable

AND ONE THING THESE TESTS DO NOT DO.  They do not invent the measurements.  There
is no API key in this environment and not one real call has been made in this
build, so the cache-hit rate, the token counts, the cost per task and the `solved`
rate are all ABSENT WITH A RECORDED REASON (rule N3), never a plausible zero.  The
tests below check exactly that: that reading one of them RAISES rather than
returning a number nobody measured.
"""
from __future__ import annotations
import datetime
import inspect
import unittest

import agent_llm
import llms


class PricesAreExternalFacts(unittest.TestCase):
    """L1 -- prices expire."""

    def test_L1_prices_are_not_older_than_90_days(self):
        """LLM prices are EXTERNAL FACTS and they expire.  The prices verified on
        2026-09-15 differ sharply from the ones in the model's memory.

        Thesis claim (vi): "gia LLM la du kien ngoai, het han duoc".
        """
        today = datetime.date.today()
        for name, pipe in llms.REGISTRY.items():
            with self.subTest(model=name):
                scope = pipe.scope()
                age = scope.prices_age_days(today)
                self.assertLessEqual(
                    age, llms.MAX_PRICE_AGE_DAYS,
                    f"[{name}] prices were verified on {scope.priced_at}, {age} days "
                    f"ago. RE-VERIFY THEM against the provider's price page and "
                    f"update priced_at -- a budget quoted from stale prices is a "
                    f"number about the past wearing today's date.")
                scope.check_prices_fresh(today=today)

    def test_L1_a_price_older_than_90_days_is_refused_not_warned(self):
        """A stale price that merely prints a warning is a stale price that gets
        used -- the gate has to REFUSE.

        Thesis claim (vi): "gia qua han thi TU CHOI, khong phai canh bao".
        """
        scope = llms.REGISTRY[llms.DEFAULT_MODEL].scope()
        priced = datetime.date.fromisoformat(scope.priced_at)
        stale = priced + datetime.timedelta(days=llms.MAX_PRICE_AGE_DAYS + 1)
        with self.assertRaises(llms.StalePrices):
            scope.check_prices_fresh(today=stale)
        fresh = priced + datetime.timedelta(days=llms.MAX_PRICE_AGE_DAYS)
        scope.check_prices_fresh(today=fresh)   # the boundary itself still passes

    def test_L1_the_prices_are_the_ones_verified_on_2026_09_15(self):
        """The numbers in SPEC-P2-Agent Part 1b are the audited ones; a price that
        drifted away from that table is a price nobody checked.

        Thesis claim (vi): "gia trong ma phai khop bang da kiem ngay 15/09/2026".
        """
        flash = llms.REGISTRY["deepseek-flash"].scope()
        pro = llms.REGISTRY["deepseek-v4-pro"].scope()
        for scope in (flash, pro):
            self.assertEqual(scope.priced_at, llms.PRICES_VERIFIED_AT)
        # PEAK list prices, USD per 1M tokens; off-peak is half (offpeak_discount).
        self.assertEqual((flash.price_in_miss, flash.price_in_hit, flash.price_out),
                         (0.30, 0.006, 1.20))
        self.assertEqual((pro.price_in_miss, pro.price_in_hit, pro.price_out),
                         (1.32, 0.044, 3.96))
        for scope in (flash, pro):
            self.assertEqual(scope.offpeak_discount, 0.5,
                             "SPEC-P2-Agent Part 1b: off-peak is half of peak")
            self.assertEqual(scope.context_window, 1_000_000)

    def test_L1_a_cache_hit_is_50x_cheaper_on_flash_and_30x_on_pro(self):
        """The most important number in the price table, and the reason
        price_in_hit is a separate field instead of an average.

        Thesis claim (vi): "cache-hit re hon cache-miss 50 lan (flash), 30 lan (pro)".
        """
        flash = llms.REGISTRY["deepseek-flash"].scope()
        pro = llms.REGISTRY["deepseek-v4-pro"].scope()
        self.assertAlmostEqual(flash.price_in_miss / flash.price_in_hit, 50.0, places=6)
        self.assertAlmostEqual(pro.price_in_miss / pro.price_in_hit, 30.0, places=6)

    def test_L1_the_declared_peak_hours_actually_decide_the_price(self):
        """A declared field that changes no number is decoration -- the same thing
        the `reads_scores` ablation caught at the policy port.  These windows pick
        the price tier, and off-peak is a factor of two.

        Thesis claim (vi): "gio peak khai ra phai thuc su quyet dinh gia".
        """
        scope = llms.REGISTRY[llms.DEFAULT_MODEL].scope()
        self.assertEqual(scope.peak_hours_utc, ((1, 4), (6, 10)))
        wed = datetime.date(2026, 9, 16)      # a Wednesday
        sat = datetime.date(2026, 9, 19)      # a Saturday
        self.assertEqual(wed.weekday(), 2)
        self.assertEqual(sat.weekday(), 5)
        peak = [datetime.datetime.combine(wed, datetime.time(h)) for h in (1, 3, 6, 9)]
        off = ([datetime.datetime.combine(wed, datetime.time(h)) for h in (0, 4, 5, 10, 23)]
               + [datetime.datetime.combine(sat, datetime.time(h)) for h in (2, 7)])
        for when in peak:
            self.assertFalse(scope.is_offpeak(when), f"{when} is inside a peak window")
        for when in off:
            self.assertTrue(scope.is_offpeak(when), f"{when} is outside every peak window")
        kw = dict(tokens_in=1_200_000, tokens_out=15_000, cache_hit=0.9)
        at_peak = scope.cost_per_task(offpeak=scope.is_offpeak(peak[0]), **kw)
        at_off = scope.cost_per_task(offpeak=scope.is_offpeak(off[0]), **kw)
        self.assertAlmostEqual(at_peak / at_off, 2.0, places=6)


class ADeclaredCacheOwesAMeasuredHitRate(unittest.TestCase):
    """L2 -- the sharpest of the four."""

    def test_L2_a_declared_cache_must_show_a_measured_hit_rate(self):
        """Declaring a cache that in practice hits 0% makes the budget wrong by up to
        50x -- and it fails SILENTLY, with the invoice arriving after the run.

        Thesis claim (vi): "khai co cache thi ti le hit do duoc phai vuot nguong".
        """
        for name, pipe in llms.REGISTRY.items():
            scope = pipe.scope()
            if not scope.supports_prompt_cache:
                continue
            with self.subTest(model=name):
                # No hit rate has ever been measured in this build -> REFUSE.
                with self.assertRaises(llms.NotMeasured) as ctx:
                    scope.check_cache_hit(llms.measured_cache_hit_rate())
                self.assertIn("cache_hit_rate", str(ctx.exception))
                # A measured rate BELOW the declared threshold is refused too: the
                # budget table of SPEC-P2-Agent Part 1b is computed at 90%.
                with self.assertRaises(llms.CacheBelowDeclared):
                    scope.check_cache_hit(0.0)
                with self.assertRaises(llms.CacheBelowDeclared):
                    scope.check_cache_hit(llms.DECLARED_CACHE_HIT - 0.01)
                scope.check_cache_hit(llms.DECLARED_CACHE_HIT)

    def test_L2_the_cache_hit_rate_is_absent_with_a_reason_not_a_zero(self):
        """N3 at the level of a single cell: an unmeasured rate records the REASON.
        0.0 is a perfectly plausible hit rate and would never be questioned again.

        Thesis claim (vi): "chua do duoc thi ghi LY DO, khong ghi so 0".
        """
        self.assertIsNone(llms.measured_cache_hit_rate())
        reason = llms.pending_reason("cache_hit_rate")
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 80, "a one-word reason is not a reason")

    def test_L2_declaring_no_cache_owes_no_hit_rate(self):
        """The contract is conditional: it binds only a scope that DECLARES a cache.
        A scope that declares none is not forced to measure one.

        Thesis claim (vi): "khong khai cache thi khong no ti le hit".
        """
        no_cache = llms.REGISTRY[llms.DEFAULT_MODEL].scope().without_prompt_cache()
        self.assertFalse(no_cache.supports_prompt_cache)
        no_cache.check_cache_hit(None)      # nothing owed, nothing raised


class DeterminismIsDeclaredTruthfully(unittest.TestCase):
    """L3."""

    def test_L3_every_llm_scope_declares_deterministic_False(self):
        """Question 6, closed 15/09/2026: `False`.  Declaring True would demand a
        bit-identical repeat call to prove it -- and that needs a key this build
        does not have, so a True here could never be checked at all.

        Thesis claim (vi): "LLM khai deterministic=False, va khai True thi phai
        chung minh duoc".
        """
        for name, pipe in llms.REGISTRY.items():
            with self.subTest(model=name):
                self.assertFalse(
                    pipe.scope().deterministic,
                    f"[{name}] declares deterministic=True. L3 then requires a "
                    f"repeat-call proof, which needs a provider key; this build has "
                    f"none, so the claim would enter the table unchecked.")

    def test_L3_a_scope_claiming_determinism_must_hand_over_the_repeat_proof(self):
        """The enforcement, not just the convention: a True declaration without a
        measured repeat is refused rather than believed.

        Thesis claim (vi): "khai tat dinh ma khong co bang chung lap lai thi bi tu choi".
        """
        liar = llms.REGISTRY[llms.DEFAULT_MODEL].scope().claiming_determinism()
        self.assertTrue(liar.deterministic)
        with self.assertRaises(llms.NotMeasured):
            liar.check_determinism(repeat_outputs=None)
        with self.assertRaises(llms.DeterminismViolated):
            liar.check_determinism(repeat_outputs=("a", "b"))
        liar.check_determinism(repeat_outputs=("a", "a"))


class CostIsEstimatedBeforeRunning(unittest.TestCase):
    """L4 -- the gate that has to fire before a single dollar is spent."""

    def test_L4_cost_is_estimated_BEFORE_running(self):
        """Running out of money mid-grid leaves half the table unreadable.

        Thesis claim (vi): "uoc luong chi phi TRUOC khi chay".
        """
        sig = inspect.signature(llms.LLMScope.estimate_cost)
        self.assertEqual(
            [p for p in sig.parameters if p != "self"][:6],
            ["n_wf", "H", "seeds", "tokens_in", "tokens_out", "cache_hit"])
        scope = llms.REGISTRY[llms.DEFAULT_MODEL].scope()
        # The grid cost is n_wf x H x seeds x cost_usd_per_task, and it is a pure
        # function of DECLARED prices plus MEASURED tokens: nothing has to run.
        kw = dict(tokens_in=1_200_000, tokens_out=15_000, cache_hit=0.9, offpeak=True)
        one = scope.cost_per_task(**kw)
        # seeds=3, not 1: a grid that ignored `seeds` entirely would agree with the
        # formula at seeds=1 and under-quote the real run by a factor of 3.
        grid = scope.estimate_cost(100, 8, 3, **kw)
        self.assertAlmostEqual(grid, 100 * 8 * 3 * one, places=9)
        self.assertGreater(grid, 0.0)
        for n_wf, H, seeds in ((100, 8, 1), (7, 8, 3), (100, 6, 3)):
            with self.subTest(n_wf=n_wf, H=H, seeds=seeds):
                self.assertAlmostEqual(scope.estimate_cost(n_wf, H, seeds, **kw),
                                       n_wf * H * seeds * one, places=9)
                self.assertNotAlmostEqual(scope.estimate_cost(n_wf, H, seeds, **kw),
                                          grid, places=9)

    def test_L4_an_estimate_over_the_declared_cap_refuses_before_spending(self):
        """A gate that stops halfway has already spent the money it was there to
        protect.  It refuses BEFORE, and it prints the estimate next to the cap.

        Thesis claim (vi): "vuot tran thi tu choi TRUOC khi tieu dong nao".
        """
        scope = llms.REGISTRY[llms.DEFAULT_MODEL].scope()
        kw = dict(tokens_in=1_200_000, tokens_out=15_000, cache_hit=0.9, offpeak=True)
        est = scope.estimate_cost(100, 8, 1, **kw)
        with self.assertRaises(llms.BudgetExceeded) as ctx:
            scope.refuse_if_over_budget(100, 8, 1, cap_usd=est / 2, **kw)
        msg = str(ctx.exception)
        self.assertIn(f"{est:.2f}", msg, "the refusal must print the ESTIMATE")
        self.assertIn(f"{est / 2:.2f}", msg, "the refusal must print the CAP")
        self.assertAlmostEqual(
            scope.refuse_if_over_budget(100, 8, 1, cap_usd=est * 2, **kw), est,
            places=9)

    def test_L4_an_estimate_cannot_be_built_out_of_unmeasured_tokens(self):
        """The estimate is only as real as its inputs.  None in means refusal out,
        because a zero here reads as "this grid is free".

        Thesis claim (vi): "thieu so token do duoc thi khong uoc luong duoc".
        """
        scope = llms.REGISTRY[llms.DEFAULT_MODEL].scope()
        good = dict(tokens_in=1_200_000, tokens_out=15_000, cache_hit=0.9)
        for missing in ("tokens_in", "tokens_out", "cache_hit"):
            with self.subTest(missing=missing):
                kw = dict(good, **{missing: None})
                with self.assertRaises(llms.NotMeasured):
                    scope.estimate_cost(100, 8, 1, **kw)

    def test_L4_the_estimate_assumes_PEAK_unless_offpeak_is_stated(self):
        """Off-peak halves the bill.  Defaulting to it turns the budget gate into an
        optimist, and an optimistic gate lets through exactly the run it exists to
        stop.

        Thesis claim (vi): "mac dinh uoc luong theo gia PEAK, khong tu cho giam gia".
        """
        scope = llms.REGISTRY[llms.DEFAULT_MODEL].scope()
        kw = dict(tokens_in=1_200_000, tokens_out=15_000, cache_hit=0.9)
        peak = scope.estimate_cost(100, 8, 1, **kw)
        offpeak = scope.estimate_cost(100, 8, 1, offpeak=True, **kw)
        self.assertAlmostEqual(peak / offpeak, 2.0, places=6)
        self.assertAlmostEqual(scope.estimate_cost(100, 8, 1, offpeak=False, **kw),
                               peak, places=9)

    def test_L4_the_estimate_reproduces_the_budget_table_of_the_spec(self):
        """Arithmetic check against SPEC-P2-Agent Part 1b.  Those five rows are the
        reason the manuscript's 18-27k USD is not a blocking constraint, so the
        formula behind them has to be the one in the code.

        NOTE: 1.2M in / 15k out is the spec's ASSUMPTION, which the same sentence
        says must be MEASURED at p2.2.  This test pins the FORMULA, not the tokens.

        Thesis claim (vi): "cong thuc chi phi trong ma dung ra dung bang ngan sach
        cua spec".
        """
        flash = llms.REGISTRY["deepseek-flash"].scope()
        pro = llms.REGISTRY["deepseek-v4-pro"].scope()
        A = dict(tokens_in=1_200_000, tokens_out=15_000)     # the spec's assumption
        rows = [
            (flash, dict(A, cache_hit=0.9), True, 24),
            (flash, dict(A, cache_hit=0.9), False, 48),
            (flash, dict(A, cache_hit=0.0), True, 151),
            (pro, dict(A, cache_hit=0.9), True, 106),
            (pro, dict(A, cache_hit=0.0), False, 1315),
        ]
        for scope, kw, offpeak, expected in rows:
            with self.subTest(model=scope.model, cache=kw["cache_hit"], offpeak=offpeak):
                got = scope.estimate_cost(100, 8, 1, offpeak=offpeak, **kw)
                self.assertEqual(round(got), expected)
        self.assertEqual(
            round(flash.estimate_cost(13_500, 8, 1, cache_hit=0.9, offpeak=True, **A)),
            3266, "the 108,000-call column of the same table")


class TheTableMayNotMixTwoModels(unittest.TestCase):
    """The hard constraint attached to the question-10 decision."""

    def test_one_table_may_not_hold_numbers_from_two_models(self):
        """Half the rows priced 4.3x the other half, under one heading, is not a
        comparison -- it is two experiments printed as one.

        Thesis claim (vi): "CAM TRON: khong bang nao chua so tu hai model".
        """
        self.assertEqual(llms.refuse_mixed_models(["deepseek-flash"] * 5),
                         "deepseek-flash")
        with self.assertRaises(llms.MixedModels) as ctx:
            llms.refuse_mixed_models(["deepseek-flash", "deepseek-v4-pro"])
        self.assertIn("deepseek-flash", str(ctx.exception))
        self.assertIn("deepseek-v4-pro", str(ctx.exception))
        # A table that names NO model is refused too: "which model produced this"
        # having no answer is the same defect as its having two.
        with self.assertRaises(llms.MixedModels):
            llms.refuse_mixed_models([])

    def test_the_header_prints_the_model_and_the_cache_hit_rate(self):
        """Both are printed in the HEADER because both change every number in the
        body, and a reader cannot recover either one from the rows.

        Thesis claim (vi): "model va ti le cache-hit in trong header".
        """
        scope = llms.REGISTRY[llms.DEFAULT_MODEL].scope()
        head = llms.results_header(scope, cache_hit=0.9)
        self.assertIn("deepseek-flash", head)
        self.assertIn(scope.priced_at, head)
        self.assertIn("90.0%", head)

    def test_an_unmeasured_cache_hit_rate_prints_NOT_MEASURED_in_the_header(self):
        """The header is where a reader decides whether to trust the table.  A blank
        or a 0% there is the same lie as a fabricated cell.

        Thesis claim (vi): "cache-hit chua do thi header in NOT MEASURED kem ly do".
        """
        scope = llms.REGISTRY[llms.DEFAULT_MODEL].scope()
        head = llms.results_header(scope, cache_hit=None)
        self.assertIn("NOT MEASURED", head)
        self.assertNotIn("0.0%", head)
        self.assertIn("cache_hit_rate", head, "the header carries the REASON's key")


class Question10IsAThresholdDeclaredBeforeTheMeasurement(unittest.TestCase):
    """Choosing the model after seeing the results is choosing the model by results."""

    def test_flash_is_the_default_and_the_scaffold_agrees(self):
        """One default, in one place.  Two defaults that drift apart is a run whose
        model nobody can name afterwards.

        Thesis claim (vi): "flash la mac dinh, va scaffold khai cung mot mac dinh".
        """
        self.assertEqual(llms.DEFAULT_MODEL, "deepseek-flash")
        self.assertEqual(agent_llm.DEFAULT_MODEL, llms.DEFAULT_MODEL)
        self.assertIn(llms.DEFAULT_MODEL, llms.REGISTRY)

    def test_the_question_10_threshold_was_declared_before_any_measurement_existed(self):
        """A threshold written down after the number is not a threshold, it is a
        description of the number.

        Thesis claim (vi): "nguong 20% duoc khai TRUOC khi co bat ky so do nao".
        """
        self.assertEqual(llms.FLASH_SOLVED_THRESHOLD, 0.20)
        decided = datetime.date.fromisoformat(llms.QUESTION_10_DECIDED_AT)
        self.assertEqual(decided, datetime.date(2026, 9, 16))
        # ... and the measurement it branches on does not exist yet.
        self.assertIsNone(llms.measured_flash_solved_rate())
        self.assertIn("solved_rate", llms.PENDING_MEASUREMENT)

    def test_the_branch_is_applied_to_a_measured_rate_not_chosen_by_hand(self):
        """The rule is code applied to a number, so that the model is picked by the
        threshold and not by whoever looks at the table first.

        Thesis claim (vi): "luat re nhanh la ma ap len so do duoc, khong phai lua chon".
        """
        with self.assertRaises(llms.NotMeasured) as ctx:
            llms.resolve_question_10(llms.measured_flash_solved_rate())
        self.assertIn("solved", str(ctx.exception))
        below = llms.resolve_question_10(0.19)
        self.assertEqual((below.main, below.sweep),
                         ("deepseek-v4-pro", "deepseek-flash"))
        # The outcome carries the rule it was decided by, so a table quoting it can
        # print the threshold and its declaration date beside the chosen model.
        self.assertEqual(below.threshold, llms.FLASH_SOLVED_THRESHOLD)
        self.assertEqual(below.declared_at, llms.QUESTION_10_DECIDED_AT)
        self.assertEqual(below.measured_solved, 0.19)
        for bad in (-0.01, 1.01):
            with self.subTest(solved=bad), self.assertRaises(ValueError):
                llms.resolve_question_10(bad)
        for rate in (0.20, 0.35, 1.0):
            with self.subTest(solved=rate):
                out = llms.resolve_question_10(rate)
                self.assertEqual((out.main, out.sweep),
                                 ("deepseek-flash", "deepseek-flash"))

    def test_falling_back_to_pro_multiplies_the_flash_budget_by_4_3(self):
        """The cost of the branch, declared next to the branch: a budget quoted on
        flash is not a budget for a run that fell back to pro.

        Thesis claim (vi): "roi vao pro thi ngan sach flash phai nhan 4,3".
        """
        self.assertEqual(llms.PRO_COST_MULTIPLIER, 4.3)
        flash = llms.REGISTRY["deepseek-flash"].scope()
        pro = llms.REGISTRY["deepseek-v4-pro"].scope()
        A = dict(tokens_in=1_200_000, tokens_out=15_000, cache_hit=0.9, offpeak=True)
        measured = (pro.estimate_cost(100, 8, 1, **A)
                    / flash.estimate_cost(100, 8, 1, **A))
        # The spec's leverage table quotes 4.3x; the prices give 4.39x at 90% cache
        # and 4.35x with no cache, so the declared constant is the rounded one.
        self.assertAlmostEqual(measured, llms.PRO_COST_MULTIPLIER, delta=0.1)
        below = llms.resolve_question_10(0.19)
        self.assertEqual(below.budget_multiplier, llms.PRO_COST_MULTIPLIER)
        self.assertEqual(llms.resolve_question_10(0.5).budget_multiplier, 1.0)


class NothingUnmeasuredIsQuietlyAZero(unittest.TestCase):
    """Rule N3, checked on this module's own books."""

    def test_the_spike_of_step_15_4_is_recorded_as_owed_not_as_done(self):
        """No key, no call, no spike.  The honest state of p2.2 is "owed", and it is
        written down as such next to everything it would have measured.

        Thesis claim (vi): "spike 5 instance chua chay duoc, va dieu do duoc ghi lai".
        """
        for q in ("spike_5_instances", "cache_hit_rate", "tokens_in_per_task",
                  "tokens_out_per_task", "cost_usd_per_task", "solved_rate"):
            with self.subTest(quantity=q):
                self.assertGreater(len(llms.pending_reason(q)), 80)
        for getter in (llms.measured_cache_hit_rate, llms.measured_flash_solved_rate,
                       llms.measured_tokens_per_task, llms.measured_cost_per_task):
            with self.subTest(getter=getter.__name__):
                self.assertIsNone(getter())

    def test_reading_an_unmeasured_cost_raises_instead_of_returning_zero(self):
        """`agents.AgentScope` reads 0.0 as "mock, free".  On a paid API that value
        is a false declaration, and it is the field the L4 gate reads.

        Thesis claim (vi): "doc chi phi chua do thi NEM LOI, khong tra ve 0.0".
        """
        with self.assertRaises(llms.NotMeasured) as ctx:
            llms.require_measured_cost_per_task()
        self.assertIn("cost_usd_per_task", str(ctx.exception))
        agent = agent_llm.LlmAgent(client=None, cost_usd_per_task=None)
        with self.assertRaises(agent_llm.NotMeasured):
            agent.scope()

    def test_llms_extends_the_one_pending_table_instead_of_starting_a_second(self):
        """Two tables of reasons is one table nobody reads.  Every quantity
        agent_llm records as owed is still owed here, with the same words.

        Thesis claim (vi): "mot bang LY DO duy nhat, khong phai hai".
        """
        for q, reason in agent_llm.PENDING_MEASUREMENT.items():
            with self.subTest(quantity=q):
                self.assertEqual(llms.PENDING_MEASUREMENT[q], reason)
        self.assertGreater(len(llms.PENDING_MEASUREMENT),
                           len(agent_llm.PENDING_MEASUREMENT))
        with self.assertRaises(KeyError):
            llms.pending_reason("a_quantity_nobody_wrote_a_reason_for")

    def test_a_pipeline_without_a_key_refuses_loudly_instead_of_mocking(self):
        """The one thing that must not happen: a quiet fallback to MockAgent, a grid
        that runs, a table that prints, and every number in it a simulation.

        Thesis claim (vi): "khong co key thi TU CHOI am i, khong lang le chay mock".
        """
        pipe = llms.REGISTRY[llms.DEFAULT_MODEL]
        self.assertIs(llms.MissingAPIKey, agent_llm.MissingAPIKey)
        with self.assertRaises(llms.MissingAPIKey) as ctx:
            pipe.client(key_env="AUDITGAME_KEY_THAT_DOES_NOT_EXIST")
        self.assertIn("AUDITGAME_KEY_THAT_DOES_NOT_EXIST", str(ctx.exception))

    def test_the_llm_port_declares_its_scope_like_every_other_port(self):
        """A port that does not declare its scope is not a port, it is a hidden
        constant -- the same sentence the other four ports are held to.

        Thesis claim (vi): "cong nao khong khai pham vi thi khong phai cong".
        """
        self.assertTrue(llms.REGISTRY, "LLM REGISTRY is empty")
        for name, pipe in llms.REGISTRY.items():
            with self.subTest(model=name):
                self.assertEqual(pipe.name, name)
                scope = pipe.scope()
                self.assertIsInstance(scope, llms.LLMScope)
                self.assertEqual(scope.model, name)
                self.assertEqual(scope.provider, "deepseek")
                self.assertGreater(scope.max_output, 0)
                self.assertGreater(scope.context_window, scope.max_output)
                self.assertEqual(scope, pipe.scope(), "scope() is not stable")
                self.assertTrue(callable(pipe.client),
                                "the port's only route to the network is client()")


if __name__ == "__main__":
    unittest.main()
