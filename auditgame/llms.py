"""
llms.py -- The LLMPipeline PORT, and the budget gate L1-L4.
Spec: docs/thesis/pipelines/SPEC-Framework-Benchmark.md Parts 1.1 and 2.5;
      docs/thesis/pipelines/SPEC-P2-Agent.md Parts 1b-2; docs/thesis/eval/PLAN.md Task 15 (p2.2).

WHY A FIFTH PORT.  `AgentScope` carried `deterministic` and `cost_usd_per_task`.
Both are properties of the MODEL: change the scaffold and they do not move, change
the model and they move hard.  A settable thing hiding inside another port is the
hidden constant Rule 1 forbids -- and with `22-From-Model-Scaling-to-System-
Scaling.pdf` in the portfolio, the question "is the effect from the model or from
the system" cannot be answered while the model is a parameter of the system.

WHAT THIS MODULE IS AND IS NOT.  It is the DECLARATION and the ARITHMETIC: prices,
their verification date, the peak/off-peak windows, the cost formula, the
pre-flight budget refusal, the no-mixed-models rule and the question-10 branch.
It is NOT a measurement.  There is no API key in this environment and this build
has never made one real call, so every quantity that has to be OBSERVED --
tokens in/out per task, the cache-hit rate, the cost per task, flash's `solved`
rate -- is absent WITH ITS RECORDED REASON (rule N3) and raises when read.  A
plausible zero in any of those cells would be indistinguishable from a
measurement, and would never be questioned again.

THE SENTENCE THIS FILE EXISTS FOR.  A declared cache that in practice hits 0% is
wrong by up to 50x, and it is wrong SILENTLY: the invoice arrives after the run.
So `supports_prompt_cache=True` is not a description here, it is a DEBT -- L2
refuses to price a grid until someone hands over a measured hit rate.

DEPENDENCY TIER.  Pure stdlib plus `agent_llm` (itself stdlib plus the measurement
core).  The HTTP client stays infra: it is reached only through
`agent_llm.api_client`, which imports `os` and `urllib` at CALL time, so importing
this module never depends on a package or on the environment.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, replace
from typing import Optional, Protocol

import agent_llm
from agent_llm import MissingAPIKey, NotMeasured


# ================================================ DECLARED BEFORE ANY MEASUREMENT

#: The day the prices below were read off the provider's own page.  MANDATORY,
#: because a price is an EXTERNAL FACT with an expiry date: the prices verified on
#: this date differ sharply from the ones in the model's memory.  See L1.
PRICES_VERIFIED_AT = "2026-09-15"

#: How old a price may be before the gate refuses.  Not a soft warning: a warning
#: on a stale price is a stale price that gets used anyway.
MAX_PRICE_AGE_DAYS = 90

#: The cache-hit rate the budget table of SPEC-P2-Agent Part 1b is COMPUTED AT.
#: Declaring a cache commits to reaching it -- L2 refuses anything lower, and
#: refuses hardest when nobody measured it at all.
DECLARED_CACHE_HIT = 0.90

#: Peak pricing windows, UTC, as half-open hour ranges, Monday-Friday only.
#: SPEC-P2-Agent Part 1b: "Peak = 01:00-04:00 and 06:00-10:00 UTC, Mon-Fri".
PEAK_HOURS_UTC = ((1, 4), (6, 10))
PEAK_WEEKDAYS = (0, 1, 2, 3, 4)

#: QUESTION 10, CLOSED 16/09/2026.  `deepseek-flash` is the DEFAULT, plus a BRANCH
#: RULE: if flash's MEASURED `solved` rate on the 5-instance spike of step 15.4 is
#: below FLASH_SOLVED_THRESHOLD, the main run uses pro and the sweep uses flash;
#: otherwise flash throughout.
#:
#: THE THRESHOLD IS WRITTEN DOWN HERE BEFORE THE MEASUREMENT EXISTS, and that is
#: the whole point: a threshold chosen after seeing the number is not a threshold,
#: it is a description of the number.  `measured_flash_solved_rate()` returns None
#: in this build and `resolve_question_10` refuses on None, so the branch can only
#: ever be taken by applying this rule to a real measurement.
QUESTION_10_DECIDED_AT = "2026-09-16"
FLASH_SOLVED_THRESHOLD = 0.20

#: What falling back to pro costs, declared next to the branch that would cause
#: it: the question-11 budget is computed on flash, and pro multiplies it.
#: SPEC-P2-Agent Part 1b, "three levers": pro -> flash is 4.3x.
PRO_COST_MULTIPLIER = 4.3

#: The default model of the whole build, in ONE place.  `agent_llm` reads its
#: scaffold default from the same string (a conformance test pins the two
#: together): two defaults that drift apart is a run whose model nobody can name.
DEFAULT_MODEL = agent_llm.DEFAULT_MODEL


# ============================================================ THE OWED NUMBERS

#: ONE table of reasons, not two.  `agent_llm.PENDING_MEASUREMENT` already records
#: every quantity Task 14 could not supply; this module ADDS to it rather than
#: starting a rival table, because two tables of reasons is one table nobody
#: reads.  Rule N3: an absent quantity records the REASON, never `harm = 0`.
PENDING_MEASUREMENT: dict = dict(agent_llm.PENDING_MEASUREMENT, **{
    "spike_5_instances": (
        "PLAN Task 15 step 15.4 -- run 5 SWE-bench instances through the Task 14 "
        "agent loop and MEASURE tokens in/out, the real prompt-cache hit rate and "
        "flash's `solved` rate. It has NOT been run: there is no API key in this "
        "environment and the spike is the first thing in this build that would "
        "spend money. Everything downstream of it (step 15.5's replacement of the "
        "1.2M-token assumption, the cost_usd_per_task the L4 gate reads, and the "
        "question-10 branch) is therefore owed, not done."),
    "budget_cap_usd": (
        "SPEC-P2-Agent Part 5, question 7: the DeepSeek backend is settled but L4 "
        "still needs a concrete ceiling, and that ceiling is a decision by the "
        "person paying, not a value this module may invent. `refuse_if_over_budget` "
        "therefore takes `cap_usd` as a required argument instead of defaulting to "
        "one -- a default cap is a cap nobody agreed to."),
    "grid_cost_usd": (
        "The grid estimate is n_wf x H x seeds x cost_usd_per_task, and its third "
        "input is a measurement this build does not have. `estimate_cost` computes "
        "it from tokens that must be PASSED IN; it refuses on None rather than "
        "substituting the 1.2M/15k assumption of SPEC-P2-Agent Part 1b, which that "
        "same sentence says must be measured at p2.2, not fixed by that table."),
})


def pending_reason(quantity: str) -> str:
    """The recorded reason a quantity is absent.  KeyError is deliberate: a
    quantity nobody wrote a reason for is not 'pending', it is forgotten."""
    return PENDING_MEASUREMENT[quantity]


class StalePrices(RuntimeError):
    """Prices older than MAX_PRICE_AGE_DAYS.  A budget quoted from them is a number
    about the past wearing today's date."""


class CacheBelowDeclared(RuntimeError):
    """A MEASURED cache-hit rate below the declared one.  The budget table was
    computed at the declared rate; the run will cost more than the table says."""


class DeterminismViolated(RuntimeError):
    """`deterministic=True` was declared and the repeat call disagreed.  I1 and
    replay both rest on this bit."""


class BudgetExceeded(RuntimeError):
    """The pre-flight estimate is over the declared cap.  Raised BEFORE a dollar is
    spent -- stopping halfway has already spent the money the gate protects."""


class MixedModels(RuntimeError):
    """Numbers from two models under one heading.  That is not a comparison, it is
    two experiments printed as one table."""


# -------- the measured quantities, each ABSENT WITH A REASON, never a zero ------

def measured_cache_hit_rate() -> Optional[float]:
    """The real prompt-cache hit rate, or None.

    None, not 0.0: 0.0 is a perfectly plausible hit rate, it would flow straight
    into the budget and it would never be questioned again.  The reason lives at
    PENDING_MEASUREMENT["cache_hit_rate"].
    """
    return None


def measured_flash_solved_rate() -> Optional[float]:
    """Flash's `solved` rate on the 5-instance spike, or None.

    This is the input to the question-10 branch, so a fabricated value here would
    pick the model for the whole thesis.  See PENDING_MEASUREMENT["solved_rate"]
    and ["spike_5_instances"].
    """
    return None


def measured_tokens_per_task():
    """(tokens_in, tokens_out) per task, or None.

    NOT the 1.2M / 15k of SPEC-P2-Agent Part 1b: that is the spec's own assumption,
    and the same sentence says it must be MEASURED at p2.2 rather than fixed by
    that table.  Returning it from here would turn an assumption into a reading.
    """
    return None


def measured_cost_per_task() -> Optional[float]:
    """USD per task, or None.  `agents.AgentScope` reads 0.0 as 'mock, free'."""
    return None


def require_measured_cost_per_task() -> float:
    """The cost the L4 gate needs, or a loud refusal."""
    value = measured_cost_per_task()
    if value is None:
        raise NotMeasured("cost_usd_per_task is not measured: "
                          + pending_reason("cost_usd_per_task"))
    return float(value)


# ===================================================================== L-SCOPE

@dataclass(frozen=True)
class LLMScope:
    """What one model IS, declared and machine-enforceable.

    `price_in_hit` is a separate field from `price_in_miss` not for tidiness: at
    DeepSeek a hit is 50x cheaper on flash and 30x on pro, so averaging the two
    puts the budget out by two orders of magnitude.

    All three prices are the PEAK list prices in USD per 1M tokens; off-peak is
    `offpeak_discount` times them (0.5 at DeepSeek).  Storing peak and deriving
    off-peak keeps the conservative number the primary one -- see `estimate_cost`.
    """
    provider: str
    model: str
    priced_at: str                 # ISO date; prices are external facts, see L1
    price_in_miss: float           # USD / 1M tokens, peak, prompt cache MISSED
    price_in_hit: float            # USD / 1M tokens, peak, prompt cache HIT
    price_out: float               # USD / 1M tokens, peak
    supports_prompt_cache: bool
    offpeak_discount: float        # 1.0 = no discount
    peak_hours_utc: tuple
    deterministic: bool            # almost always False -- question 6
    context_window: int
    max_output: int

    # ------------------------------------------------------------------ L1 --

    def prices_age_days(self, today: Optional[datetime.date] = None) -> int:
        """How many days old these prices are.  Negative is possible and is left
        alone: a `priced_at` in the future is a typo, and L1 is not the place to
        silently repair one."""
        day = today or datetime.date.today()
        return (day - datetime.date.fromisoformat(self.priced_at)).days

    def check_prices_fresh(self, today: Optional[datetime.date] = None,
                           max_age_days: int = MAX_PRICE_AGE_DAYS) -> int:
        """L1.  Raise `StalePrices` rather than warn: a warning on a stale price is
        a stale price that gets used."""
        age = self.prices_age_days(today)
        if age > max_age_days:
            raise StalePrices(
                f"[{self.model}] prices were verified on {self.priced_at}, {age} "
                f"days ago (limit {max_age_days}). LLM prices are EXTERNAL FACTS "
                f"and they expire -- re-verify them against the provider's price "
                f"page and update priced_at before quoting any budget.")
        return age

    # ------------------------------------------------------------------ L2 --

    def check_cache_hit(self, measured: Optional[float],
                        declared: float = DECLARED_CACHE_HIT) -> Optional[float]:
        """L2, the sharpest of the four.

        Binds only a scope that DECLARES a cache; a scope declaring none owes no
        hit rate.  For one that does: None is refused HARDER than a low number,
        because a missing hit rate fails silently and a low one at least shows up.
        """
        if not self.supports_prompt_cache:
            return measured
        if measured is None:
            raise NotMeasured(
                f"[{self.model}] declares supports_prompt_cache=True, so the "
                f"cache_hit_rate must be MEASURED before any budget may be quoted. "
                f"It is not: " + pending_reason("cache_hit_rate"))
        if measured < declared:
            raise CacheBelowDeclared(
                f"[{self.model}] measured cache-hit rate {measured:.1%} is below the "
                f"declared {declared:.1%}. The budget table was computed at the "
                f"declared rate, so the run costs more than the table says -- by up "
                f"to {self.price_in_miss / self.price_in_hit:.0f}x on the input side.")
        return measured

    def without_prompt_cache(self) -> "LLMScope":
        """The same model declared WITHOUT a cache.  Used to show that L2 is
        conditional on the declaration rather than universal."""
        return replace(self, supports_prompt_cache=False)

    # ------------------------------------------------------------------ L3 --

    def claiming_determinism(self) -> "LLMScope":
        """The same model declaring `deterministic=True` -- the declaration L3
        exists to disbelieve."""
        return replace(self, deterministic=True)

    def check_determinism(self, repeat_outputs=None):
        """L3.  A scope declaring determinism must hand over the repeat call that
        proves it; a scope declaring False owes nothing.

        Question 6 closed `False` on 15/09/2026, and three consequences follow:
        the trace records the REAL output rather than a seed to regenerate it,
        bootstrap resamples over BOTH seed and workflow, and I1 is restated as
        "same trace => same score".
        """
        if not self.deterministic:
            return repeat_outputs
        if repeat_outputs is None:
            raise NotMeasured(
                f"[{self.model}] declares deterministic=True, which is a claim about "
                f"a REPEAT CALL. No repeat call exists in this build: "
                + pending_reason("wire_format_verified"))
        distinct = set(repeat_outputs)
        if len(distinct) > 1:
            raise DeterminismViolated(
                f"[{self.model}] declares deterministic=True but {len(repeat_outputs)} "
                f"calls on the same input gave {len(distinct)} different outputs. I1 "
                f"and replay both rest on this bit being true.")
        return repeat_outputs

    # ------------------------------------------------------------------ L4 --

    def is_offpeak(self, when: datetime.datetime) -> bool:
        """Whether `when` (UTC) falls outside every peak window.

        `peak_hours_utc` is a declared field, so it has to DECIDE something --
        a field that changes no number is decoration, which is exactly what the
        `reads_scores` ablation caught at the policy port.
        """
        if when.weekday() not in PEAK_WEEKDAYS:
            return True
        return not any(lo <= when.hour < hi for lo, hi in self.peak_hours_utc)

    def _tier(self, offpeak: bool) -> float:
        return self.offpeak_discount if offpeak else 1.0

    def cost_per_task(self, tokens_in, tokens_out, cache_hit,
                      offpeak: bool = False) -> float:
        """USD for ONE task, from DECLARED prices and MEASURED tokens.

        Every input is required and none may be None.  A None quietly read as 0
        prices the grid at zero, and "this grid is free" is the one budget answer
        nobody double-checks.
        """
        for label, value, reason_key in (
                ("tokens_in", tokens_in, "tokens_in_per_task"),
                ("tokens_out", tokens_out, "tokens_out_per_task"),
                ("cache_hit", cache_hit, "cache_hit_rate")):
            if value is None:
                raise NotMeasured(
                    f"[{self.model}] cannot price a task: {label} is not measured. "
                    + pending_reason(reason_key))
        if not 0.0 <= cache_hit <= 1.0:
            raise ValueError(f"cache_hit must be a rate in [0, 1], got {cache_hit!r}")
        tier = self._tier(offpeak)
        million_in, million_out = tokens_in / 1e6, tokens_out / 1e6
        price_in = cache_hit * self.price_in_hit + (1.0 - cache_hit) * self.price_in_miss
        return tier * (million_in * price_in + million_out * self.price_out)

    def estimate_cost(self, n_wf, H, seeds, tokens_in, tokens_out, cache_hit,
                      *, offpeak: bool = False) -> float:
        """L4.  The whole grid, BEFORE running any of it.

            cost = n_wf x H x seeds x cost_usd_per_task

        `offpeak` defaults to FALSE, i.e. to the PEAK price, on purpose. Off-peak
        halves the bill; a gate that assumes the discount is an optimistic gate,
        and an optimistic gate lets through exactly the run it exists to stop.
        """
        per_task = self.cost_per_task(tokens_in, tokens_out, cache_hit,
                                      offpeak=offpeak)
        return int(n_wf) * int(H) * int(seeds) * per_task

    def refuse_if_over_budget(self, n_wf, H, seeds, *, cap_usd,
                              tokens_in, tokens_out, cache_hit,
                              offpeak: bool = False) -> float:
        """L4's teeth: estimate, compare, and REFUSE before spending anything.

        `cap_usd` has no default. A default ceiling is a ceiling nobody agreed to --
        see PENDING_MEASUREMENT["budget_cap_usd"].
        """
        estimate = self.estimate_cost(n_wf, H, seeds, tokens_in, tokens_out,
                                      cache_hit, offpeak=offpeak)
        if estimate > cap_usd:
            raise BudgetExceeded(
                f"[{self.model}] estimated ${estimate:.2f} for {n_wf} x {H} x {seeds} "
                f"= {int(n_wf) * int(H) * int(seeds)} agent calls, over the declared "
                f"cap of ${cap_usd:.2f}. REFUSED BEFORE RUNNING: stopping half way "
                f"through leaves half the grid unreadable and the money already "
                f"spent. Raise the cap deliberately, cut the grid, or turn on the "
                f"cache ({self.price_in_miss / self.price_in_hit:.0f}x on input).")
        return estimate


# ====================================================================== PORTS

class LLMPipeline(Protocol):
    name: str
    def scope(self) -> LLMScope: ...
    def client(self, **kw): ...


def _deepseek_scope(model, in_miss, in_hit, out, max_output) -> LLMScope:
    """Prices are the PEAK column of SPEC-P2-Agent Part 1b, verified 15/09/2026."""
    return LLMScope(
        provider="deepseek", model=model, priced_at=PRICES_VERIFIED_AT,
        price_in_miss=in_miss, price_in_hit=in_hit, price_out=out,
        supports_prompt_cache=True, offpeak_discount=0.5,
        peak_hours_utc=PEAK_HOURS_UTC,
        # Question 6, closed 15/09/2026. An LLM is not deterministic, and
        # declaring True would demand a repeat-call proof this build cannot make.
        deterministic=False,
        context_window=1_000_000, max_output=max_output)


class DeepSeekModel:
    """One DeepSeek model behind the port.  `scope()` is the declaration; `client()`
    is the only way to reach the network, and it refuses loudly without a key."""
    name: str = ""
    _scope: LLMScope = None

    def scope(self) -> LLMScope:
        return self._scope

    def client(self, key_env: str = agent_llm.API_KEY_ENV,
               base_url: str = agent_llm.DEFAULT_BASE_URL):
        """The real client, or `MissingAPIKey`.

        There is NO fallback to a mock here and there must never be one: the grid
        would run, the table would print, and every number in it would have come
        from a simulation labelled as a real agent.
        """
        return agent_llm.api_client(model=self.name, key_env=key_env,
                                    base_url=base_url)


class DeepSeekFlash(DeepSeekModel):
    """The DEFAULT (question 10).  A cache hit is 50x cheaper than a miss here --
    the largest single cost lever in the whole build."""
    name = "deepseek-flash"
    _scope = _deepseek_scope(name, 0.30, 0.006, 1.20, 8_192)


class DeepSeekV4Pro(DeepSeekModel):
    """The fallback the question-10 branch may select: 4.3x flash on cost, and a
    hit is 30x cheaper than a miss."""
    name = "deepseek-v4-pro"
    _scope = _deepseek_scope(name, 1.32, 0.044, 3.96, 8_192)


class DeepSeekV41Flash(DeepSeekModel):
    """The frozen wire model used by OpenCode pilot runs and arms."""
    name = "deepseek-v4.1-flash"
    _scope = _deepseek_scope(name, 0.30, 0.006, 1.20, 8_192)


REGISTRY: dict = {p.name: p for p in (DeepSeekFlash(), DeepSeekV4Pro(), DeepSeekV41Flash())}


# ============================================ NO TABLE MIXES TWO MODELS (L1-L4)

def refuse_mixed_models(models) -> str:
    """The one model every row in a table came from, or `MixedModels`.

    Half the rows priced 4.3x the other half, under one heading, is not a
    comparison -- it is two experiments printed as one.
    """
    distinct = sorted({str(m) for m in models})
    if not distinct:
        raise MixedModels("an empty table declares no model at all")
    if len(distinct) > 1:
        raise MixedModels(
            "this table mixes numbers from " + " and ".join(distinct) +
            ". Forbidden: the two differ by "
            f"{PRO_COST_MULTIPLIER}x in cost and by an unmeasured amount in "
            "`solved`, so rows from both under one heading are two experiments "
            "printed as one. Split the table and print the model in each header.")
    return distinct[0]


def results_header(scope: LLMScope, cache_hit: Optional[float] = None,
                   today: Optional[datetime.date] = None) -> str:
    """The header every L1-L4 table must carry.

    MODEL and CACHE-HIT RATE, because both change every number in the body and
    neither can be recovered from the rows. An unmeasured hit rate prints
    NOT MEASURED with the key of its recorded reason -- never a blank and never
    0.0%, which reads exactly like a measurement of a cold cache.
    """
    age = scope.prices_age_days(today)
    lines = [
        f"model: {scope.model}  (provider {scope.provider}, "
        f"deterministic={scope.deterministic})",
        f"prices: priced_at {scope.priced_at} ({age} days old, "
        f"limit {MAX_PRICE_AGE_DAYS}), USD/1M peak "
        f"in-miss {scope.price_in_miss} / in-hit {scope.price_in_hit} / "
        f"out {scope.price_out}, off-peak x{scope.offpeak_discount}",
    ]
    if not scope.supports_prompt_cache:
        lines.append("cache-hit rate: no prompt cache declared")
    elif cache_hit is None:
        lines.append(
            f"cache-hit rate: NOT MEASURED "
            f"[PENDING_MEASUREMENT.cache_hit_rate] -- {pending_reason('cache_hit_rate')}")
    else:
        lines.append(f"cache-hit rate: {cache_hit:.1%} measured "
                     f"(declared {DECLARED_CACHE_HIT:.1%})")
    return "\n".join(lines)


# ============================================================ QUESTION 10 RULE

@dataclass(frozen=True)
class Question10:
    """Which model runs where, and what it does to the budget."""
    main: str
    sweep: str
    budget_multiplier: float
    threshold: float
    measured_solved: float
    declared_at: str


def resolve_question_10(flash_solved_rate: Optional[float]) -> Question10:
    """Apply the branch rule DECLARED on 16/09/2026 to a MEASURED rate.

    flash `solved` < FLASH_SOLVED_THRESHOLD  =>  pro for the main run, flash for
    the sweep, and the question-11 budget (computed on flash) times
    PRO_COST_MULTIPLIER.  Otherwise flash throughout and the budget stands.

    None is refused rather than defaulted. Defaulting would mean the model for the
    whole thesis was picked by whichever branch happened to be the fallback, and
    picking a model after looking at the results is picking a model BY the results.
    """
    if flash_solved_rate is None:
        raise NotMeasured(
            "the question-10 branch needs flash's MEASURED `solved` rate from the "
            "5-instance spike of step 15.4, and there is none: "
            + pending_reason("spike_5_instances")
            + " The threshold itself was declared on " + QUESTION_10_DECIDED_AT
            + f" as {FLASH_SOLVED_THRESHOLD:.0%}, before any measurement existed, so "
            + "it is waiting on the number and not the other way round.")
    rate = float(flash_solved_rate)
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"`solved` is a rate in [0, 1], got {flash_solved_rate!r}")
    if rate < FLASH_SOLVED_THRESHOLD:
        return Question10(main="deepseek-v4-pro", sweep="deepseek-flash",
                          budget_multiplier=PRO_COST_MULTIPLIER,
                          threshold=FLASH_SOLVED_THRESHOLD, measured_solved=rate,
                          declared_at=QUESTION_10_DECIDED_AT)
    return Question10(main="deepseek-flash", sweep="deepseek-flash",
                      budget_multiplier=1.0, threshold=FLASH_SOLVED_THRESHOLD,
                      measured_solved=rate, declared_at=QUESTION_10_DECIDED_AT)
