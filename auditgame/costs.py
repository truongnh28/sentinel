"""Audit cost table, priced in LLM inference dollars.

WHY THIS FILE EXISTS.  `policies.KAPPA` carried its own confession -- "the
placeholder awaiting the lab's per-carrier cost table" -- and its four numbers
came from the per-STAGE costs of manuscript section 7, not from the cost of
auditing a carrier.  Every number here is measured on this system instead.

    kappa(k) = items_scored(k) x usd_per_judgement

WHERE THE NUMBERS COME FROM
  usd_per_judgement   payloads/judge-cache.json -- 1200 records for USD 0.594
  items_scored(k)     20 instrumented episodes counting core.CarrierStore.live

THE ORDERING NEARLY REVERSES against the placeholder: memory was the cheapest
carrier to audit (0.4) and is now the most expensive (0.00264); skill was 0.9
and is now the cheapest.  Since chi (Toan-canh section 4.6) measures the SHAPE
of the cost vector and not its magnitude, this is not a rescaling -- it changes
which carrier the attacker wants, and therefore the game.

USING IT.  These are a DIFFERENT UNIT from policies.KAPPA. Set both KAPPA and
KAPPA_COMMIT together, and set the budget with `budget_for` so the fraction of
the total audit bill stays comparable with the pre-USD tables.
"""
from __future__ import annotations

#: payloads/judge-cache.json: 1200 judgements for USD 0.594.
USD_PER_JUDGEMENT = 0.594 / 1200

#: Items a single audit of this carrier has to score.  Measured over 20
#: instrumented episodes; the spread matters as much as the mean, so the max
#: is recorded beside it.
ITEMS_PER_AUDIT = {"memory": 5.34, "skill": 1.12, "queue": 1.55, "branch": 4.50}
ITEMS_PER_AUDIT_MAX = {"memory": 9, "skill": 4, "queue": 4, "branch": 8}

KAPPA_USD = {c: n * USD_PER_JUDGEMENT for c, n in ITEMS_PER_AUDIT.items()}

#: An audit at commit is the last gate, so it scores EVERY carrier.
KAPPA_COMMIT_USD = sum(KAPPA_USD.values())

#: The placeholder, kept so the two can be compared in one place rather than
#: from memory.  Do not import this to run with -- it is here as evidence.
KAPPA_PLACEHOLDER = {"memory": 0.4, "skill": 0.9, "queue": 1.6, "branch": 4.1}

#: The pre-USD tables ran at budget 17.95 against a per-step total of 7.0, i.e.
#: 32.1% of the bill for auditing everything.  Holding the FRACTION fixed is
#: what makes the USD tables comparable with them.
LEGACY_BUDGET = 17.95
LEGACY_TOTAL_PER_STEP = sum(KAPPA_PLACEHOLDER.values())


def budget_fraction(H: int = 8) -> float:
    """The share of a full audit bill the legacy budget bought."""
    return LEGACY_BUDGET / (H * LEGACY_TOTAL_PER_STEP)


def budget_for(H: int = 8) -> float:
    """Budget in USD that buys the SAME SHARE as the legacy 17.95 did."""
    return budget_fraction(H) * H * sum(KAPPA_USD.values())


#: Quarantine cost, carried over BY RATIO rather than by number.
#:
#: `policies.ETA_Q_COST = 2.0` sat at about 1.25x the mean placeholder kappa.
#: Copying the 2.0 into a USD run would make quarantine ~1400x the mean carrier
#: cost, so no policy could ever afford the action -- and a policy that cannot
#: afford an action is not being compared, it is being disabled. The tables
#: published before 2026-09-20 did not trip over this only because the policies
#: in them never quarantine; `Sentinel` does, so its L10 was measured against a
#: quarantine that was far too cheap relative to auditing.
ETA_Q_RATIO_TO_MEAN_KAPPA = 2.0 / (sum(KAPPA_PLACEHOLDER.values()) / len(KAPPA_PLACEHOLDER))
ETA_Q_USD = ETA_Q_RATIO_TO_MEAN_KAPPA * (sum(KAPPA_USD.values()) / len(KAPPA_USD))


def install(policies_module) -> dict:
    """Point a policies module at the USD table.  Returns what was replaced.

    KAPPA, KAPPA_COMMIT and ETA_Q_COST move TOGETHER. Leaving the commit
    channel on the old scale would make it ~1800x every carrier and silently
    delete it from the action space; leaving quarantine there does the same to
    quarantine. Either way the comparison stops being a comparison.
    """
    old = {"KAPPA": dict(policies_module.KAPPA),
           "KAPPA_COMMIT": policies_module.KAPPA_COMMIT,
           "ETA_Q_COST": policies_module.ETA_Q_COST}
    policies_module.KAPPA = dict(KAPPA_USD)
    policies_module.KAPPA_COMMIT = KAPPA_COMMIT_USD
    policies_module.ETA_Q_COST = ETA_Q_USD
    return old


def restore(policies_module, old: dict) -> None:
    """Undo `install`, so a shared process is not left on the USD scale."""
    for k, v in old.items():
        setattr(policies_module, k, v)
