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

#: E[n_total] -- live items at the decision point, summed over the four
#: carriers.  Measured on the same 20 instrumented episodes as ITEMS_PER_AUDIT.
EXPECTED_ITEMS_TOTAL = sum(ITEMS_PER_AUDIT.values())          # 12.51

#: pi0 is NOT a hand-picked model constant: it follows from how an episode is
#: built.  Each episode seeds EXACTLY ONE payload among E[n_total] live items,
#: so inside the injected arm the probability that an arbitrary live item is the
#: payload is 1 / E[n_total].  scoring.py imports this rather than declaring its
#: own, because reference/score_table.json is GENERATED from it: two independent
#: copies would let the thresholds be read off a table built at another prior.
PI0_WORLD = 1.0 / EXPECTED_ITEMS_TOTAL                        # 0.0799

#: The defender does not know whether this episode is under attack at all; the
#: belief starts that probability at pi_attack = 0.5 (belief.WindowBelief).  The
#: pi0 the DEFENDER works with is therefore the world's pi0 times pi_attack --
#: two roles, two numbers, per rule R2 of the parameter estimation report.  Using
#: one number for both silently hands the defender the certainty of an attack.
PI_ATTACK = 0.5
PI0_MODEL = PI_ATTACK * PI0_WORLD                             # 0.0400

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


def budget_for_table(kappa: dict, H: int = 8) -> float:
    """Budget on ANY kappa table that buys the same share as the legacy 17.95.

    ONE RULE FOR EVERY SCALE, and it has to be one function: `budget_for_cpu`
    once multiplied the same fraction by (sum(kappa) + kappa_commit) while this
    one used sum(kappa) alone, so the CPU scale silently ran on a budget 1.36x
    richer than the USD scale it was being compared against.

    The commit channel is NOT in the denominator because it is not in the legacy
    one either: LEGACY_TOTAL_PER_STEP is the four carriers, and KAPPA_COMMIT was
    a separate number beside them.  Putting it in here would change what "the
    same share" means, which is the one thing this function exists to hold fixed.
    """
    return budget_fraction(H) * H * sum(kappa.values())


def budget_for(H: int = 8) -> float:
    """Budget in USD that buys the SAME SHARE as the legacy 17.95 did."""
    return budget_for_table(KAPPA_USD, H)


# ===================================================== CPU-TIME SCALE (Stage 2)
#
# kappa as Stage 2 defines it: the CPU cost of the four audit checkpoints doing
# the work they are named for.  Measured by tools/measure_kappa.py through
# `checkpoints.py`, after those four stopped being one Gaussian draw each.
#
# WHY THE CARRIERS DIFFER NOW.  An audit of a carrier inspects its live items:
# re-hashes each record, parses its content into tokens, walks its lineage.  So
# the cost follows how much there is to inspect -- memory carries 4.86 live items
# on average, skill 0.85 -- and the ordering memory > branch > queue > skill is
# a consequence of the store, not of a table someone wrote down.
#
# RESOLUTION.  A single audit costs about one tick of `time.process_time`, so
# the numbers below come from timing 200 identical audits and dividing; a
# one-shot timing quantises to the clock and reports every carrier alike
# (measured that way: chi = 0.0).
KAPPA_CPU = {"memory": 1.454e-5, "skill": 3.64e-6,
             "queue": 4.78e-6, "branch": 1.070e-5}

#: The commit checkpoint, timed in the game loop itself: it reviews the record a
#: commit carries and walks its whole transitive lineage across carriers.
#: LOWER BOUND -- Stage 2 also asks for differential testing, which needs the
#: per-instance Docker image and is not run here.
KAPPA_COMMIT_CPU = 1.2e-5

#: chi of the CPU table, for the record: 1.295, against 1.349 for the USD table
#: and 2.114 for the manuscript's.  The first two agree because both are driven
#: by items-per-audit; the third is a per-STAGE table wearing a per-carrier name.

#: eta_Q / kappa, the one dimensionless thing the USD measurement produced:
#: rebuilding an item is agent work, looking at one is judge work, and that gap
#: is 61.5x (spikes/eta-q.json).  Carried across to the CPU scale as a RATIO
#: rather than re-measured, because MockAgent's write costs nothing like a real
#: agent's -- so this is a declared transfer, not a measurement in this unit.
ETA_Q_OVER_KAPPA = 61.5


def install_cpu(policies_module) -> dict:
    """Point a policies module at the CPU-time table.  Returns what was replaced.

    Budget is NOT set here: it is a fraction of the full audit bill, so the
    caller sets it with `budget_for_cpu(H)` -- otherwise switching scales
    silently switches how much auditing the budget buys.
    """
    old = {"KAPPA": dict(policies_module.KAPPA),
           "KAPPA_COMMIT": policies_module.KAPPA_COMMIT,
           "ETA_Q_COST": policies_module.ETA_Q_COST}
    policies_module.KAPPA = dict(KAPPA_CPU)
    policies_module.KAPPA_COMMIT = KAPPA_COMMIT_CPU
    policies_module.ETA_Q_COST = ETA_Q_OVER_KAPPA * (sum(KAPPA_CPU.values())
                                                     / len(KAPPA_CPU))
    return old


def budget_for_cpu(H: int = 8) -> float:
    """Budget in CPU seconds buying the SAME SHARE as the legacy 17.95 did."""
    return budget_for_table(KAPPA_CPU, H)


#: BENIGN DRIFT RATE, counted on the real history of the ten SWE-bench repos
#: (tools/measure_beta.py, spikes/beta-k.json).  Median across repositories under
#: mapping rule A; the range across repos is in the JSON and is wide.
#:
#: NOT IDENTIFIED FOR skill AND queue.  The script also runs an alternative
#: mapping rule B, and the two disagree by an order of magnitude on skill
#: (0.058 vs 0.607) -- which was the pre-declared trigger for moving beta from
#: M1 (measure) to M2 (sweep).  memory (0.31 vs 0.28) and branch (1.0 by
#: construction) survive both rules; those two are the only ones to quote.
BETA_RULE_A = {"memory": 0.314, "skill": 0.058, "queue": 0.033, "branch": 1.0}
BETA_RULE_B = {"memory": 0.279, "skill": 0.607, "queue": 0.013, "branch": 1.0}

#: What a belief should start from when it needs one number: memory's rate, the
#: only measured carrier both mapping rules agree on.  It is a DEFAULT, not a
#: finding -- results that depend on it have to show the sweep.
BETA_DEFAULT = BETA_RULE_A["memory"]

#: CPU seconds to DETACH a carrier from the loop: re-run the task without it.
#: Measured by tools/measure_eta_q.py, which runs the same workflow twice on the
#: same seed -- once normally, once quarantining the carrier at the first task --
#: and takes the median CPU-time difference over the episode.  Zeros here mean
#: "not measured yet", and eta_q() then reports the restore half alone.
DETACH_SECONDS = {"memory": 0.0, "skill": 0.0, "queue": 0.0, "branch": 0.0}

#: Seconds -> USD, so the detach half can be added to the restore half.  One
#: judgement is one scored item, and tools/measure_kappa.py times exactly that,
#: so the rate is USD_PER_JUDGEMENT per scoring call divided by the CPU seconds
#: a scoring call takes.  Both numbers come from this repo's own measurements.
SECONDS_PER_JUDGEMENT = 6.5e-6        # spikes/kappa-cpu.json, median per item
SECONDS_TO_USD = USD_PER_JUDGEMENT / SECONDS_PER_JUDGEMENT


#: USD to WRITE one item, as opposed to judging one.  Measured: the median cost
#: of a real agent task in the P2 pilot (token counts of spikes/p2-pilot.jsonl
#: priced through llms.py at the frozen deepseek-v4.1-flash prices) divided by
#: the mean number of items an agent writes per task.  See
#: tools/measure_eta_q.py and spikes/eta-q.json.
#:
#: IT IS 61x USD_PER_JUDGEMENT, and that ratio is the whole story of eta_Q:
#: looking at an item is judge work, rebuilding one is agent work.
USD_PER_WRITE = 0.030452


def eta_q_parts(carrier: str) -> dict:
    """The two halves of eta_Q(k), priced in the same unit as KAPPA_USD.

    detach   re-running the task with the carrier masked -- measured.
    restore  rebuilding what the quarantine destroyed.  Quarantine removes EVERY
             item of the carrier, clean ones included, so restoring costs
             n_live(k) writes.  It is not a constant: n_live differs 4.8x between
             memory and skill, so one scalar eta_Q for all four carriers is a
             rounding that has to be declared rather than a fact.
    """
    return {"detach": DETACH_SECONDS[carrier] * SECONDS_TO_USD,
            "restore": ITEMS_PER_AUDIT[carrier] * USD_PER_WRITE}


def eta_q(carrier: str) -> float:
    """eta_Q(k) = detach + restore.  See eta_q_parts for what each half is."""
    return sum(eta_q_parts(carrier).values())


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
