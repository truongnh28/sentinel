#!/usr/bin/env python3
"""
dprime_sweep.py -- Sweep d' CONTINUOUSLY and locate the break-even d'*.

WHY THIS MODULE EXISTS.  The thesis reported three DECLARED operating points
copied from the manuscript -- weak (0.75, 0.20), mid (0.85, 0.12), strong
(0.92, 0.06) -- and had no answer to "where does 0.85 come from?".  The answer is
not a better defence of 0.85.  It is to stop choosing: d' becomes a SWEPT
PARAMETER, the result is reported across the whole range, and the claim is
restated as a THRESHOLD --

    "Sentinel reduces harm if and only if the audit reaches d' > d'*."

This needs no new subsystem.  detector.Detector(d_prime, tau_det) already takes an
arbitrary d'; everything below is measurement, not mechanism.

WHAT IS HELD FIXED, AND WHY THAT PARAMETERISATION.  tau_det is held at the `mid`
setting's threshold, tau_det = z(1 - 0.12) = 1.17498679206609.  That makes this a
genuinely ONE-DIMENSIONAL sweep: phi = Phi(-tau_det) = 0.12 does not move, only
psi = Phi(d' - tau_det) does.  Sweeping (psi, phi) jointly -- which is what the
three declared settings do -- moves the false-alarm rate and the detection rate at
the same time, so a difference between two settings cannot be attributed to either
one.  Here it can: every point on the curve is the SAME false-alarm rate.

WHAT IS NOT HELD FIXED, AND WHERE THAT LEAKS (declared, not discovered later).
`setting` is also the key into the FROZEN tau_sel table (scoring.tau_sel), the
carrier-level selection threshold.  It is calibrated per d': tau_sel is the
(1 - alpha_c) quantile of the clean posterior, which depends on d'.  In the
DEFAULT mode this sweep keeps setting="mid" at every d', so the policies'
carrier-selection threshold stays calibrated at d' = 2.211 while the detector runs
at the swept d'.  That is a real confound at d' far from 2.211 and it is reported
as one.  The detector's own d' DOES reach the policies, through
runner -> scoring.carrier_score(raw, det.d_prime), so the belief model tracks the
sweep even though the threshold does not.

    --tau-follows-dprime  REMOVES that confound.

The reference table now carries a row per grid point, keyed by d' itself and
generated at the SAME fixed phi = 0.12 this sweep runs at (reference/
gen_score_table.py, names "d0.0" .. "d3.0"); under the flag each swept point looks
its threshold up in its OWN row.  scoring.py is untouched -- tau_sel is a dict
lookup by setting NAME, so a new name is all it takes.  The default is unchanged
so the published curve reproduces verbatim, and the two modes are reported side by
side rather than one replacing the other.

The flag turns the step-0.05 REFINEMENT off, and that is a limitation, not an
oversight: the table has rows at the coarse grid only.  It could not have rows at
the refinement points either, since which bracket gets refined is not known until
the coarse grid has been measured.  d'* under --tau-follows-dprime is therefore
read at the resolution of the coarse grid, 0.2.

WHAT THE TWO MODES ACTUALLY MEASURED (spikes/tau-sel-follows-dprime.md).  The two
curves are IDENTICAL, cell for cell, at every (d', Delta) of the grid.  The reason
is STRUCTURAL rather than statistical: scoring.tau_sel is reached only through
policies.Policy.tau, and only B5 risk-score and B6 two-stage call it.  Neither
policy of the pair Delta-harm is defined through -- B1 audit-at-commit and
Sentinel -- ever reads the table, so the pinned row could not have moved this
number in either direction.  The confound is real for any result that involves B5
or B6; for THIS one it is inert, and that is now measured rather than assumed
(gate 2, TheDeclaredConfoundIsInertForThisDeltaHarmPair, which carries its own
sensitivity control).

READ THAT RESULT FOR EXACTLY WHAT IT IS.  Because the intervention cannot reach
either policy of the pair, the new-mode run carries NO information about whether
the reversal at Delta = 0 is a real mechanism: the two curves had to agree either
way, and a test that could not have failed is not evidence.  What it establishes
is an ELIMINATION -- "tau_sel pinned at mid" is struck off the list of candidate
explanations for the reversal and for the placement of Delta=2's d'* -- and
nothing more.  The reversal itself is still unexplained.

WHAT IS SCORED: HARM, AND ALSO THE DECLARED OBJECTIVE L.  Until this batch the
sweep computed Delta-harm = harm_B1 - harm_Sentinel and nothing else, while the
declared defender objective (De-cuong II.7.3, metrics.loss) is

    L = E[harm] + lambda_Q E[Q_false] + lambda_T E[T_lost].

harm is ONE of the three terms, and it is the term Sentinel is strongest on:
Sentinel buys its harm advantage by quarantining far more than B1 does, so a
threshold read off harm alone is read off the term that flatters it.  The harm
curve is UNCHANGED and still printed first -- the published d'* reproduces
verbatim -- and the L scoring is ADDED beside it:

  * the cell measures FOUR policies, not two: B1 audit-at-commit, Sentinel,
    B5 risk-score, B6 two-stage.  "Sentinel beats B1" is nearly free (B1 audits
    only the commit); the frame decision turns on the two score-reading baselines.
  * d'* under L is `break_even` -- the SAME frozen rule -- applied to L-differenced
    shadow cells (`as_loss_cells`), at THREE declared lambda_Q: 0, each cell's own
    lambda-bar, and metrics.LAMBDA_Q.  The first and last are ILLUSTRATIONS.
  * lambda-bar is metrics.lambda_q_star over the cell's own four policies: a
    RESULT, measured per (Delta, d'), never a setting.  Where it does not exist the
    cell says so and is excluded from that column under N3 -- it is not given
    another cell's weight, and not given 0 or 0.10.
  * metrics.spend_table is printed beside every Delta.  "Every policy runs on the
    same budget B" is true of the CAP and false of the SPEND, and the difference
    reaches 40x between policies.

WHICH tau_sel MODE THE L TABLES SHOULD BE READ IN -- THE CHOICE HAS CHANGED.  The
confound declared above is INERT for B1 and Sentinel (spikes/tau-sel-follows-
dprime.md SS6: scoring.tau_sel is reached only through policies.Policy.tau, whose
only callers are RiskScore and TwoStage).  It is LIVE for B5 and B6, which are
exactly the two policies added here.  Under the DEFAULT mode B5 and B6 select
carriers at a threshold calibrated for d' = 2.211 no matter where the detector is,
and the measured size of that is not small: B5's harm at d' = 3.0 moves 0.3829 ->
0.3649 between the pinned row and its own row, and 0.2027 at the d0.0 row.  So for
any table that RANKS Sentinel against B5/B6, --tau-follows-dprime is the mode in
which every policy's threshold is calibrated at the d' its own detector runs at,
and it is the one the L result is reported from.  The default mode is still run and
still reported, as the reproduction of the published configuration.  The cost of
the headline mode is resolution: it forces refinement off (see above), so d'* under
L is read at the coarse grid's 0.2.

WHAT THE CLAIM FORM ACTUALLY NEEDS, AND THE AMENDMENT THAT SAYS SO (18/09/2026).
tien-dang-ky v2 SS9 pre-registered the boundary of the claim as lambda-bar =
metrics.lambda_q_star.  Measuring exposed two reasons that function cannot express
the pre-registered sentence -- "Sentinel beats X for all lambda_Q < boundary" is
about ONE PAIR, while lambda_q_star is about the argmin over ALL FOUR policies; and
it accepts roots in (1e-9, 5] only, so on the 25 of 64 cells where L(0) TIES it
skips the flip that happens immediately above 0 and returns a larger number read
off a different pair.  So the boundary is now measured PAIRWISE and reported under
its own name, lambda-cross (`pairwise_crossing`), with lambda-bar reported beside
it unchanged.  Two names because they are two numbers: over the same 64 cells
lambda-bar runs [0.0042 ; 1.4217] and the Sentinel-B1 lambda-cross runs
[0.0462 ; 0.5932].  Reporting the second under the first's symbol would have been a
silent change of definition.

AND TWO CONVENTIONS AT ZERO, WHICH DISAGREE ON 25 CELLS (AT_ZERO, ABOVE_ZERO).  At
exactly 0 a tie is a tie; in the limit from above it has already broken.  Each
count printed below says which convention it is in, because a table and its own
summary once disagreed for exactly this reason.

THE SURVIVING CLAIM RESTS ON AN UNSWEPT CONSTANT, AND THE RUN SAYS SO.  Sentinel
beats B1 through the T_lost term alone, and T_lost enters L weighted by
metrics.LAMBDA_T = 0.50, which this project has never swept.  `lambda_t_table`
re-scores the SAME cells at lambda_T in {0, 0.25, 0.50} -- 64/64 cells at 0.50,
22/64 at 0 -- and that table is printed by every run.  The B5 and B6 verdicts do
not move with it: all three score-reading policies have T_lost = 0.000 everywhere.

THE ATTACKER'S OBJECTIVE IS STILL HARM.  `policy_curve` takes the max over the
attacker class of mean HARM, exactly as runner.worst_case defines it, and reads the
penalty terms off the configuration that choice lands on.  A worst case under L
would be a different attacker and a different measurement; it is not what any
frozen number here is, so it is not what is computed.

What IS computed, because "every L here is a lower bound" says nothing about a
RANKING on its own: `--l-attacker-probe` re-runs the same attacker class with L as
its objective at three DECLARED cells and prints how far each policy's L moves.
Measured: every policy's L rises, no probe cell changes a ranking, and the
direction of the DIFFERENCE is not uniform (it deepens Sentinel's deficit against
B5 at Delta = 0 and narrows it at Delta = 4).  That is a probe, not a worst case.

THE DEFINITION OF d'* -- FIXED BEFORE ANY NUMBER WAS LOOKED AT:

    d'* = the SMALLEST d' in the grid such that the CI95 LOWER BOUND of
          Delta-harm is > 0 at that d' AND at EVERY LARGER d' in the grid.

The "and at every larger d'" clause is the whole point.  Without it a single noise
crossing near the bottom of the grid gets reported as a threshold.  This project
has already been burned once by choosing a summarisation rule after seeing the
data (finding P7), so the rule is `break_even()` below and it was written first.

If Delta-harm is NOT monotone in d', that is REPORTED (`is_monotone`), not
smoothed: it is a result about the method.  If a Delta cell never separates from
zero anywhere in the grid, d'* is None -- "no break-even in this range" is an
answer, an interpolated number would not be.

N3.  A (d', Delta) cell on which no attack could be built on any workflow carries
a REASON, not harm = 0.0, and is excluded from the break-even scan -- it is not
"the defense held".
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from dataclasses import dataclass, asdict, field

import agent
import build
import detector
import metrics
import runner
from core import seed_of

#: The two policies Delta-harm is defined through.  Delta-harm = harm_B1 - harm_Sentinel.
B1 = "B1 audit-at-commit"
SENTINEL = "Sentinel"

#: The two comparators the FRAME DECISION needs beside that pair.  "Sentinel beats
#: B1" is not the question the thesis has to answer -- B1 audits only the commit, so
#: beating it on harm is nearly free.  The question is whether Sentinel also holds
#: up against the two score-reading baselines, and under the DECLARED objective L
#: rather than harm alone.  Spelled with the policies.REGISTRY keys verbatim: a
#: renamed policy must be a KeyError at measurement time, not a missing column.
B5 = "B5 risk-score"
B6 = "B6 two-stage"

#: Measured at every cell, in this order.  B1 and Sentinel come FIRST so the pair
#: Delta-harm is defined through is measured exactly as it was before B5/B6 existed
#: (pinned by test_adding_b5_and_b6_does_not_move_the_b1_sentinel_pair).
POLICIES = (B1, SENTINEL, B5, B6)

#: The grid point the printed spend table is read at -- DECLARED, not chosen after
#: seeing which one flatters a policy.  2.2 is the grid point nearest mid's
#: d' = 2.211, the operating point every frozen number in the thesis already uses.
#: The per-policy `spent` column of policy_table carries the other fifteen points.
SPEND_REFERENCE_D_PRIME = 2.2

#: The THREE declared lambda_Q columns of the L report.  0 and metrics.LAMBDA_Q are
#: ILLUSTRATIONS and never the headline (tien-dang-ky v2 SS9); the reportable
#: quantity is lambda-bar, which is MEASURED per cell.  0.10 is read off
#: metrics.LAMBDA_Q rather than pasted, so the column cannot drift away from the
#: weight metrics.py declares.
LQ_ZERO = "lambda_Q=0"
LQ_BAR = "lambda_Q=lambda-bar (per cell)"
LQ_DEFAULT = f"lambda_Q={metrics.LAMBDA_Q}"

#: TWO CONVENTIONS, TWO LABELS -- and they do not agree, so they may not share a
#: name.  AT_ZERO is the weight EXACTLY 0, where three policies can hold the same
#: L and a tie is reported as a tie.  ABOVE_ZERO is the limit from above, where a
#: tie at 0 has already broken in favour of whoever quarantines less: on this
#: corpus the two readings differ on 25 of 64 cells (at 0: B5 11 sole / Sentinel
#: 28 sole / 25 tied; at 0+: B5 33 / Sentinel 28 / B6 3).  Writing "lambda_Q -> 0"
#: over a column computed at 0.0 is what made a table and its own summary
#: disagree, so the arrow now means the limit and nothing else.
AT_ZERO = "lambda_Q = 0"
ABOVE_ZERO = "lambda_Q -> 0+"

#: FIXED false-alarm rate for the whole sweep: tau_det from the `mid` setting.
#: Read off detector.SETTINGS rather than pasted as a literal, so the sweep cannot
#: drift away from the setting it claims to inherit.
TAU_DET = detector.operating_point(*detector.SETTINGS["mid"])[1]

#: The frozen tau_sel table row this sweep reads by DEFAULT (see module docstring).
SETTING = "mid"

#: Coarse grid: d' in {0.0, 0.2, ..., 3.0} -- 16 points, step 0.2.
GRID = tuple(round(0.2 * i, 2) for i in range(16))

#: Refinement step, used only inside the bracket that already contains d'*.
REFINE_STEP = 0.05

#: The corpus seed, the same one experiment.py's mock path uses.  Named so the
#: --json artefact can record WHICH corpus a sweep ran on instead of implying it.
CORPUS_SEED = 2026

#: The Delta cells.  REPORTED SEPARATELY, NEVER POOLED (project rule): a pooled
#: number averages the regime where the method helps with the regime where it does
#: not, which is the single thing this grid exists to keep apart.
DELTAS = (0, 1, 2, 4)

#: D5 -- the attacker class must cover all four carriers.
CARRIERS = ("memory", "skill", "queue", "branch")


def setting_for(d_prime: float, tau_follows_dprime: bool = False) -> str:
    """Which tau_sel row a swept point reads.

    Default: "mid" at every d' -- the declared confound, kept so the published
    curve reproduces.  Under the flag: the row calibrated AT this d'.

    The name spelling MIRRORS reference/gen_score_table.sweep_setting_name and is
    duplicated rather than imported, because reference/ is a directory of frozen
    artifacts and not an importable package.  A drift between the two spellings is
    a KeyError in the middle of a long run, so it is pinned by the gate-2 test
    test_the_following_mode_reads_the_tau_sel_row_calibrated_at_the_swept_d_prime.
    """
    return f"d{d_prime:.1f}" if tau_follows_dprime else SETTING


@dataclass
class PolicyCurve:
    """ONE policy at ONE (d', Delta) cell, WITH the per-workflow vectors.

    runner.GridCell already carries harm, q_false, t_lost and spent_mean -- but
    q_false and t_lost only as MEANS; its `per_wf` is the harm vector alone.  The
    CI95 of Delta-L needs a per-workflow L, so it needs all three per workflow.

    Why that matters rather than being a convenience.  The alternative is to take
    the harm interval and shift it by the mean penalty difference.  That gives the
    Q_false and T_lost terms NO sampling variability at all, so the interval keeps
    the harm interval's WIDTH while its centre moves -- and d'* is defined by a
    lower bound, so an interval narrower than the evidence reports the threshold
    LOWER than the data supports.  That is the defect class this module exists to
    avoid (see `break_even`), so the vectors are measured instead.
    """
    harm: float
    q_false: float
    t_lost: float
    spent: float
    n_feasible: int
    n_total: int
    per_wf_harm: list
    per_wf_q_false: list
    per_wf_t_lost: list
    per_wf_spent: list

    def loss(self, lambda_Q: float, lambda_T: float = metrics.LAMBDA_T) -> float:
        """L = harm + lambda_Q Q_false + lambda_T T_lost, through metrics.loss."""
        return metrics.loss(self.harm, self.q_false, self.t_lost,
                            lambda_Q, lambda_T)

    def per_wf_loss(self, lambda_Q: float,
                    lambda_T: float = metrics.LAMBDA_T) -> list:
        """The bootstrap UNIT for Delta-L: one L per workflow, same unit as harm."""
        return [metrics.loss(h, q, t, lambda_Q, lambda_T)
                for h, q, t in zip(self.per_wf_harm, self.per_wf_q_false,
                                   self.per_wf_t_lost)]

    def terms(self) -> tuple:
        """(harm, q_false, t_lost) -- the shape metrics.lambda_q_star reads."""
        return (self.harm, self.q_false, self.t_lost)


@dataclass
class SweepCell:
    """One (d', Delta) cell.  N3: harm never travels without its denominator, and a
    cell that could not be built carries WHY instead of a number."""
    d_prime: float
    delta: int
    harm_b1: float
    harm_sentinel: float
    dharm: float
    ci_lo: float
    ci_hi: float
    n_feasible: int
    n_total: int
    reason: str | None = None       # not None => excluded from every average
    #: {policy name -> PolicyCurve} over POLICIES.  Added by the L scoring; the six
    #: fields above are BYTE-FOR-BYTE what they were before it existed, so the
    #: published harm curve reproduces from the same cell.
    curves: dict = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.reason is None


def make_detector(d_prime: float) -> detector.Detector:
    """The detector at one point of the sweep: swept d', FIXED tau_det.

    Not `Detector.from_operating_point`, which would take a (psi, phi) pair and so
    move phi as well -- that is the two-dimensional move this sweep exists to
    replace.
    """
    return detector.Detector(d_prime, TAU_DET)


def make_corpus(n: int, H: int, seed: int = CORPUS_SEED) -> list:
    """The same corpus experiment.py's `--dataset mock` path builds.

    Copied in shape, not imported, for one reason only: importing experiment would
    execute nothing harmful but would couple an additive measurement to the frozen
    driver.  The seeding is identical -- ONE rng shared across the corpus -- so a
    sweep point at d' = d'(mid) reproduces experiment.py's `mid` row exactly, and
    tests/gate1_integrity/test_dprime_sweep.py asserts precisely that.
    """
    rng = random.Random(seed)
    return [build.make_workflow(f"wf-{i:03d}", "django", H, rng) for i in range(n)]


def policy_curve(policy_name, wfs, deltas, carriers, det, ag, budget, seeds,
                 setting: str, update_rule: str = "ratio",
                 objective_lambda_Q: float | None = None,
                 objective_lambda_T: float = metrics.LAMBDA_T) -> PolicyCurve:
    """runner.worst_case, KEEPING the per-workflow Q_false / T_lost / spent vectors.

    THIS IS A COPY OF A FROZEN LOOP, AND IT IS DECLARED AS ONE.  runner.py may not
    be modified in this batch, and runner.worst_case discards the two vectors the
    L interval needs (its GridCell keeps q_false and t_lost as means only).  The
    same move make_corpus already makes against experiment.make_corpus, pinned the
    same way: gate 1's
    test_the_per_workflow_vectors_reproduce_runner_worst_case_exactly asserts every
    scalar of this function EQUALS runner.worst_case's on the same arguments, for
    all four policies.  If the two ever drift, that test is the thing that says so.

    The attacker's objective is UNCHANGED BY DEFAULT and stays harm: `best` is the
    max over the attacker class of MEAN HARM, exactly as runner.worst_case defines
    it, and the penalty terms are read off the configuration that choice lands on.
    Every number this module reports is measured that way.

    `objective_lambda_Q` is NOT that measurement and does not replace it.  It is
    the PROBE behind the batch's own first concern -- "the attacker maximises harm
    while the defender is scored with L, so every L number is a lower bound on
    loss".  That sentence is true per policy and says nothing about a RANKING,
    which is what every reportable claim here is; a bound that moves all four
    policies by the same amount moves no ranking at all.  Passing a weight makes
    the attacker maximise L = harm + lambda_Q Q_false + lambda_T T_lost over the
    SAME attacker class, so the direction can be measured at declared cells
    (L_ATTACKER_PROBE_CELLS, --l-attacker-probe) instead of argued.  None keeps the
    frozen loop, and L(0, 0) is harm, so the probe at zero weights reproduces it
    exactly (pinned by gate 2).
    """
    per_wf, qf, tl, sp = [], [], [], []
    for wf in wfs:
        best = None                                  # None = no feasible attack yet
        bh = bq = bt = bs = 0.0
        for d in deltas:
            for k in carriers:
                rng = random.Random(seed_of(wf.wf_id, d, k))
                ps = build.plan_poison(wf, k, d, rng)
                if ps is None:
                    continue                         # configuration cannot be built
                hs, qs, ts, ss = [], [], [], []
                for s in seeds:
                    r = runner.paired(wf, ps, policy_name, det, ag, s, budget,
                                      setting, update_rule)
                    if r is None:
                        continue
                    hs.append(r.harm); qs.append(r.false_quarantine)
                    ts.append(r.t_lost); ss.append(r.spent)
                if hs:
                    m = sum(hs) / len(hs)
                    q = sum(qs) / len(qs)
                    t = sum(ts) / len(ts)
                    obj = m if objective_lambda_Q is None else metrics.loss(
                        m, q, t, objective_lambda_Q, objective_lambda_T)
                    if best is None or obj > best:
                        best = obj
                        bh = m
                        bq = q
                        bt = t
                        bs = sum(ss) / len(ss)
        if best is not None:        # N3: drop from the DENOMINATOR, never turn into 0.0
            per_wf.append(bh); qf.append(bq); tl.append(bt); sp.append(bs)

    n = len(per_wf)

    def mean(v):
        return sum(v) / n if n else float("nan")

    return PolicyCurve(harm=mean(per_wf), q_false=mean(qf), t_lost=mean(tl),
                       spent=mean(sp), n_feasible=n, n_total=len(wfs),
                       per_wf_harm=per_wf, per_wf_q_false=qf,
                       per_wf_t_lost=tl, per_wf_spent=sp)


#: The (d', Delta) cells the attacker-objective probe is read at -- DECLARED here,
#: not picked after seeing which one gives the answer the text wants.  One cell at
#: the reference d' in the regime where the policies separate (Delta = 2), one in
#: the saturated regime the L ranking is dominated by Q_false in (Delta = 0), and
#: one at low d' and the largest Delta.
L_ATTACKER_PROBE_CELLS = ((2.2, 2), (2.2, 0), (0.6, 4))


def l_attacker_probe(wfs, budget: float, seeds, cells=L_ATTACKER_PROBE_CELLS,
                     lambda_Q: float = metrics.LAMBDA_Q,
                     lambda_T: float = metrics.LAMBDA_T,
                     tau_follows_dprime: bool = True,
                     carriers=CARRIERS, policies=POLICIES) -> str:
    """How much does the ranking move when the ATTACKER is scored with L too?

    The batch's first concern, measured rather than asserted.  Each declared cell
    is measured twice -- once with the frozen harm-maximising attacker, once with
    an L-maximising one over the same attacker class -- and the table prints the
    MOVE in each policy's L.  What matters for this project's claims is not that
    each L rises (it must: a maximum cannot fall) but whether the rises DIFFER
    between policies, because only a difference moves a ranking.
    """
    ag = agent.MockAgent()
    out = [f"  ATTACKER OBJECTIVE PROBE -- harm-max vs L-max over the SAME attacker",
           f"  class, at declared cells.  lambda_Q = {lambda_Q}, lambda_T = "
           f"{lambda_T}; tau_follows_dprime={tau_follows_dprime}.",
           f"  Read the MOVE row: a rise shared by all four policies moves no "
           f"ranking."]
    for d_prime, delta in cells:
        det = make_detector(d_prime)
        setting = setting_for(d_prime, tau_follows_dprime)
        out.append(f"\n  [d' = {d_prime}  Delta = {delta}  tau_sel row {setting!r}]")
        out.append(f"  {'policy':<24}{'objective':<10}{'harm':>8}{'Q_fal':>8}"
                   f"{'T_lost':>8}{'L':>10}{'feas':>9}")
        for name in policies:
            got = {}
            for label, lq in (("harm", None), (f"L@{lambda_Q}", lambda_Q)):
                runner.reset_survivor_cache()
                c = policy_curve(name, wfs, (delta,), carriers, det, ag, budget,
                                 seeds, setting, objective_lambda_Q=lq,
                                 objective_lambda_T=lambda_T)
                got[label] = c
                out.append(f"  {name:<24}{label:<10}{_fmt(c.harm, 8)}"
                           f"{_fmt(c.q_false, 8)}{_fmt(c.t_lost, 8)}"
                           f"{_fmt(c.loss(lambda_Q, lambda_T), 10, 4)}"
                           f"{c.n_feasible:>6d}/{c.n_total:<3d}")
            a, b = got["harm"], got[f"L@{lambda_Q}"]
            out.append(f"  {'':<24}{'MOVE':<10}{b.harm - a.harm:>+8.3f}"
                       f"{b.q_false - a.q_false:>+8.3f}"
                       f"{b.t_lost - a.t_lost:>+8.3f}"
                       f"{b.loss(lambda_Q, lambda_T) - a.loss(lambda_Q, lambda_T):>+10.4f}")
    return "\n".join(out)


def measure_cell(wfs, d_prime: float, delta: int, budget: float, seeds,
                 carriers=CARRIERS, ag=None, setting: str = SETTING,
                 policies=POLICIES) -> SweepCell:
    """Delta-harm, its CI95, and the FOUR policy curves at ONE (d', Delta) cell.

    The CI comes from runner.bootstrap_paired, whose resampling unit is the
    WORKFLOW -- untouched here.  Cases from one workflow share a task chain and a
    clean-run outcome, so resampling by case gives falsely narrow intervals; a
    break-even read off a falsely narrow interval is a fiction.

    B5 and B6 are measured BESIDE the pair, never instead of it: harm_b1,
    harm_sentinel, dharm, ci_lo and ci_hi are computed from exactly the two
    policies they were computed from before, so the published curve reproduces.
    """
    det = make_detector(d_prime)
    ag = ag or agent.MockAgent()
    cells = {}
    for name in policies:
        runner.reset_survivor_cache()
        cells[name] = policy_curve(name, wfs, (delta,), carriers, det, ag,
                                   budget, seeds, setting)
    b1, sn = cells[B1], cells[SENTINEL]

    empty = [n for n in policies if cells[n].n_feasible == 0]
    if empty:
        # N3: no attack could be built on ANY workflow in this cell.  That is not
        # harm = 0 and it is not "the defense held" -- it is an absent measurement,
        # and it says so.
        #
        # Checked over EVERY policy, not over the pair alone.  Delta-harm needs B1
        # and Sentinel, but the L RANKING is taken over all four: a policy with no
        # feasible workflow has harm = NaN, so its L is NaN, `l_winners` finds no
        # minimum and the argmin column prints a bare `--` -- an absent measurement
        # with no reason attached, which is the one thing N3 forbids.
        return SweepCell(d_prime=d_prime, delta=delta,
                         harm_b1=float("nan"), harm_sentinel=float("nan"),
                         dharm=float("nan"), ci_lo=float("nan"), ci_hi=float("nan"),
                         n_feasible=0, n_total=b1.n_total,
                         reason=f"no attack could be built at Delta={delta} on any "
                                f"of the {b1.n_total} workflows for "
                                + ", ".join(empty)
                                + ("" if len(empty) == len(policies) else
                                   f"; the L ranking is taken over {len(policies)} "
                                   f"policies and cannot be read with one of them "
                                   f"absent"),
                         curves=cells)
    if len(b1.per_wf_harm) != len(sn.per_wf_harm):
        # bootstrap_paired pairs BY INDEX.  Two different lengths means the two
        # policies dropped different workflows, and the pairing would be a lie.
        return SweepCell(d_prime=d_prime, delta=delta,
                         harm_b1=b1.harm, harm_sentinel=sn.harm,
                         dharm=float("nan"), ci_lo=float("nan"), ci_hi=float("nan"),
                         n_feasible=min(b1.n_feasible, sn.n_feasible),
                         n_total=b1.n_total,
                         reason=f"B1 kept {b1.n_feasible} workflows and Sentinel "
                                f"{sn.n_feasible}: the paired CI has no pairing",
                         curves=cells)

    lo, hi = runner.bootstrap_paired(b1.per_wf_harm, sn.per_wf_harm)
    return SweepCell(d_prime=d_prime, delta=delta,
                     harm_b1=b1.harm, harm_sentinel=sn.harm,
                     dharm=b1.harm - sn.harm, ci_lo=lo, ci_hi=hi,
                     n_feasible=b1.n_feasible, n_total=b1.n_total,
                     curves=cells)


def break_even(cells) -> float | None:
    """d'* -- the DECLARED definition, and the only one this module computes.

        d'* = min { d' : CI95_lo(Delta-harm) > 0 at d' AND at every larger d'
                         in the grid }

    Implemented as a scan DOWNWARD from the largest d', extending the run while the
    lower bound stays above zero and stopping at the first point that breaks it.
    That is the same statement, and it makes the "and stays" clause structural
    rather than a comment: a lone positive point below a negative one can never be
    returned, because the scan has already stopped.

    Returns None when no suffix of the grid qualifies -- "there is no break-even in
    this range" is an answer.  A cell carrying a REASON (N3) breaks the run exactly
    as a non-positive bound does: an absent measurement cannot support "and stays".
    """
    star = None
    for c in sorted(cells, key=lambda c: c.d_prime, reverse=True):
        if c.usable and c.ci_lo > 0.0:
            star = c.d_prime
        else:
            break
    return star


def is_monotone(cells) -> bool:
    """Is Delta-harm non-decreasing in d' across the usable cells of one Delta?

    Reported, never enforced.  A non-monotone curve is a result about the method --
    more audit quality not always buying more advantage -- and smoothing it would
    delete the finding.
    """
    vals = [c.dharm for c in sorted(cells, key=lambda c: c.d_prime) if c.usable]
    return all(a <= b + 1e-12 for a, b in zip(vals, vals[1:]))


# ------------------------------------------------------- scoring with L ----
#
# WHY THIS EXISTS.  Everything above scores the sweep with HARM.  The DECLARED
# defender objective (De-cuong II.7.3, metrics.loss) is
#
#     L = E[harm] + lambda_Q E[Q_false] + lambda_T E[T_lost]
#
# and harm is ONE of its three terms.  Sentinel buys its harm advantage by
# quarantining far more than B1 does, so a d'* read off harm alone is a threshold
# on the term that flatters it.  Nothing below replaces the harm curve: the harm
# cells are read, never mutated, and `break_even` is reused VERBATIM rather than
# reimplemented, so "the same frozen rule, applied to the L-difference" is
# structural instead of a claim in a comment.


def dloss(cell: SweepCell, lambda_Q: float,
          lambda_T: float = metrics.LAMBDA_T) -> float:
    """Delta-L = L(B1) - L(Sentinel) at one cell, same orientation as Delta-harm."""
    return (cell.curves[B1].loss(lambda_Q, lambda_T)
            - cell.curves[SENTINEL].loss(lambda_Q, lambda_T))


def loss_interval(cell: SweepCell, lambda_Q: float,
                  lambda_T: float = metrics.LAMBDA_T) -> tuple:
    """CI95 of Delta-L -- the SAME bootstrap and the SAME unit as Delta-harm.

    Per-workflow L on both sides, then runner.bootstrap_paired.  Not the harm
    interval shifted by the mean penalty difference: that would keep the harm
    interval's width and give the two penalty terms no sampling variability at all.
    """
    return runner.bootstrap_paired(cell.curves[B1].per_wf_loss(lambda_Q, lambda_T),
                                   cell.curves[SENTINEL].per_wf_loss(lambda_Q,
                                                                     lambda_T))


def lambda_bar(cell: SweepCell, lambda_T: float = metrics.LAMBDA_T):
    """lambda-bar at one cell = metrics.lambda_q_star over the cell's FOUR policies.

    A RESULT, never a setting (tien-dang-ky v2 SS9).  None means no weight in
    (0, 5] changes the winner -- one policy dominates on every term -- and None is
    an ANSWER: it is reported as "none", never replaced by 0, by metrics.LAMBDA_Q,
    or by another cell's value.
    """
    if not cell.usable or not cell.curves:
        return None
    return metrics.lambda_q_star({k: c.terms() for k, c in cell.curves.items()},
                                 lambda_T=lambda_T)


#: Two L values this close are the SAME number for ranking purposes.  Not a
#: tolerance invented to make a result come out: at Delta = 0 every score-reading
#: policy sits at the identical harm and T_lost, so their L(0) agree bit for bit
#: and the difference here is exactly 0.0.
L_TIE = 1e-12


def l_winners(cell: SweepCell, lambda_Q: float,
              lambda_T: float = metrics.LAMBDA_T, tol: float = L_TIE) -> list:
    """EVERY policy holding the smallest L at this weight.

    A list, not a name, because `min()` breaks a tie by INSERTION ORDER and the
    curves are inserted in POLICIES order with Sentinel second.  On the published
    corpus a quarter of the grid ties at lambda_Q = 0 -- at Delta = 0 Sentinel, B5
    and B6 all sit at harm 0.992 with T_lost 0.000 -- and a bare min() hands 24 of
    those 25 cells to Sentinel, overstating the headline by nearly 2x.  (The 25th,
    Delta = 4 at d' = 0.2, ties B5 with B6 and does NOT include Sentinel, so min()
    would have given that one to B5: the inflated count was 28 sole + 24 tied = 52,
    not 53.)  A tie is a tie and it is reported as one.
    """
    if not cell.curves:
        return []
    best = min(c.loss(lambda_Q, lambda_T) for c in cell.curves.values())
    return [k for k, c in cell.curves.items()
            if c.loss(lambda_Q, lambda_T) <= best + tol]


def l_winner_text(cell: SweepCell, lambda_Q: float,
                  lambda_T: float = metrics.LAMBDA_T) -> str:
    """The argmin as printed: "B5 risk-score", or "Sentinel=B5 risk-score" on a tie."""
    w = l_winners(cell, lambda_Q, lambda_T)
    return "=".join(w) if w else "--"


# ------------------------------------ the claim form's OWN quantity --------
#
# RULING 1 (controller, 18/09/2026).  tien-dang-ky v2 SS9 pre-registered
# lambda-bar = metrics.lambda_q_star.  That function answers a question about the
# argmin over ALL FOUR policies, and it cannot see a crossing at exactly 0 (it
# accepts roots in (1e-9, 5] only), so on the 25 cells that tie at lambda_Q = 0 it
# CANNOT express the pre-registered claim "Sentinel beats X for all lambda_Q <
# lambda-bar", which is a statement about ONE PAIR.  The pairwise crossing below is
# the measurement that claim actually needs.  It is a DIFFERENT quantity and it
# carries a DIFFERENT name -- lambda-cross -- because reporting it under the
# pre-registered symbol would be a silent change of definition.  Both are reported
# side by side everywhere the claim is made, and the amendment is dated in the
# spike.

#: The names, kept apart on purpose (see above).  Printed, not just commented, so
#: a reader of the table cannot take one for the other.
LAMBDA_BAR_NAME = "lambda-bar = metrics.lambda_q_star over all four policies"
LAMBDA_CROSS_NAME = "lambda-cross = the pairwise Sentinel-vs-X crossing"

#: The THREE outcomes of a pairwise comparison, kept apart.  Collapsing the first
#: two into "no crossing" loses the difference between "Sentinel wins at every
#: weight" and "Sentinel never wins"; collapsing a tie-at-zero-then-lose into
#: "crossing at 0" turns a cell Sentinel loses into a cell with a range to state.
CROSSES = "crosses"
AHEAD_EVERYWHERE = "ahead at every lambda_Q"
BEHIND_FROM_ZERO = "behind from 0+"
NO_MEASUREMENT = "no measurement at this cell"

#: lambda_T values the surviving claim is re-scored at.  0.50 is metrics.LAMBDA_T,
#: the project default, and it has NEVER been swept -- it is exactly the kind of
#: unpublished constant lambda_Q was before this batch.  0 is the other end: score
#: the objective with the T_lost term switched off.  0.25 sits between them so the
#: row is a curve and not two points.  Read off metrics.LAMBDA_T rather than pasted
#: so the grid cannot drift away from the weight metrics.py declares.
LAMBDA_T_GRID = (0.0, 0.25, metrics.LAMBDA_T)


def pairwise_crossing(cell: SweepCell, other: str,
                      lambda_T: float = metrics.LAMBDA_T,
                      sentinel: str = SENTINEL, tol: float = L_TIE) -> tuple:
    """(outcome, lambda) for "Sentinel vs `other`" at one cell -- the quantity the
    PRE-REGISTERED claim form is stated in.

    Both L curves are affine in lambda_Q, so

        D(lambda_Q) = L_other - L_Sentinel = dh + lambda_Q * dq,
        dh = (harm_o - harm_s) + lambda_T (T_o - T_s),   dq = Q_o - Q_s

    and Sentinel leads exactly where D > 0.  The sign of dh decides the limit at
    0+; if Sentinel leads there, it keeps leading forever when dq >= 0 and
    otherwise until the single root -dh/dq.

    A TIE AT EXACTLY ZERO IS NOT A WIN AND NOT A CROSSING AT ZERO.  When dh == 0
    the comparison is decided by dq alone, so a cell where Sentinel ties on harm
    and quarantines more is BEHIND at every positive weight -- it has no range to
    state, and calling its crossing "0" would put it in the table as if it had one.

    Returns (CROSSES, x), (AHEAD_EVERYWHERE, None), (BEHIND_FROM_ZERO, None), or
    (NO_MEASUREMENT, None) on a cell that carries a REASON or lacks a curve (N3).
    """
    if not cell.usable or other not in cell.curves or sentinel not in cell.curves:
        return (NO_MEASUREMENT, None)
    o, sn = cell.curves[other], cell.curves[sentinel]
    dh = (o.harm - sn.harm) + lambda_T * (o.t_lost - sn.t_lost)
    dq = o.q_false - sn.q_false
    if dh != dh or dq != dq:                       # NaN: nothing to compare
        return (NO_MEASUREMENT, None)
    ahead_at_0 = dh > tol or (abs(dh) <= tol and dq > tol)
    if not ahead_at_0:
        return (BEHIND_FROM_ZERO, None)
    if dq >= -tol:                                 # the gap only widens
        return (AHEAD_EVERYWHERE, None)
    return (CROSSES, -dh / dq)


def pairwise_text(cell: SweepCell, other: str,
                  lambda_T: float = metrics.LAMBDA_T) -> str:
    """The pairwise verdict as printed: a number, or WHICH of the other outcomes."""
    kind, x = pairwise_crossing(cell, other, lambda_T)
    return f"{x:.4f}" if kind == CROSSES else kind


def pairwise_summary(cells, other: str,
                     lambda_T: float = metrics.LAMBDA_T) -> dict:
    """The pairwise verdict counted over a set of cells, with the three outcomes
    kept apart and the median taken ONLY over the cells that actually cross.

    A median over cells with no crossing would be a median over numbers that do not
    exist; a count of "cells with a crossing >= 0.10" over cells with no crossing
    would be the same error wearing a percentage.
    """
    kinds = [pairwise_crossing(c, other, lambda_T) for c in cells]
    kinds = [(k, x) for k, x in kinds if k != NO_MEASUREMENT]
    xs = sorted(x for k, x in kinds if k == CROSSES)
    ahead_everywhere = sum(1 for k, _ in kinds if k == AHEAD_EVERYWHERE)
    behind = sum(1 for k, _ in kinds if k == BEHIND_FROM_ZERO)
    return {
        "other": other,
        "lambda_T": lambda_T,
        "n": len(kinds),
        "behind_from_zero": behind,
        "ahead_everywhere": ahead_everywhere,
        #: "ahead at 0+", i.e. every cell that is not behind the moment the weight
        #: leaves zero.  Under the ABOVE_ZERO convention, never the AT_ZERO one.
        "ahead_at_zero": len(xs) + ahead_everywhere,
        "crossings": xs,
        "min": min(xs) if xs else None,
        "median": statistics.median(xs) if xs else None,
        "max": max(xs) if xs else None,
        "crossing_at_or_above_default": sum(1 for x in xs if x >= metrics.LAMBDA_Q),
    }


def _flat(rows) -> list:
    """{delta: [cell]} or [cell] -> [cell].  The pairwise counts are over CELLS and
    the Delta cells are never pooled into an average, only counted."""
    if isinstance(rows, dict):
        return [c for d in sorted(rows) for c in rows[d]]
    return list(rows)


def lambda_t_sensitivity(rows, other: str = B1,
                         lambda_Ts=LAMBDA_T_GRID) -> list:
    """The surviving claim re-scored at several lambda_T -- one summary per weight.

    WHY THIS EXISTS.  "Sentinel beats B1" is bought by the T_lost term (B1's commit
    gate blocks clean patches; Sentinel's T_lost is 0.000 at every cell), and
    T_lost enters L weighted by lambda_T = 0.50 -- a constant this project has
    never swept.  A claim whose only support is an unswept constant has to be
    reported together with its dependence on that constant, measured.
    """
    cells = _flat(rows)
    return [pairwise_summary(cells, other, lt) for lt in lambda_Ts]


def lambda_t_table(rows, other: str = B1, lambda_Ts=LAMBDA_T_GRID) -> str:
    """The lambda_T sensitivity of the pairwise verdict, as printed."""
    out = [f"  Sentinel vs {other}, re-scored at several lambda_T "
           f"(lambda_T = {metrics.LAMBDA_T} is metrics.LAMBDA_T, NEVER SWEPT)",
           f"  {'lambda_T':>9}{'ahead at 0+':>13}{'behind':>9}{'crosses':>9}"
           f"{'min':>9}{'median':>9}{'max':>9}",
           "  " + "-" * 67]
    for s in lambda_t_sensitivity(rows, other, lambda_Ts):
        n = s["n"]
        out.append(f"  {s['lambda_T']:>9.2f}"
                   + f"{s['ahead_at_zero']}/{n}".rjust(13)
                   + f"{s['behind_from_zero']:>9d}{len(s['crossings']):>9d}"
                   + _fmt(float('nan') if s['min'] is None else s['min'], 9, 4)
                   + _fmt(float('nan') if s['median'] is None else s['median'], 9, 4)
                   + _fmt(float('nan') if s['max'] is None else s['max'], 9, 4))
    return "\n".join(out)


def _loss_shadow(cell: SweepCell, lambda_Q: float | None,
                 lambda_T: float = metrics.LAMBDA_T,
                 reason: str | None = None) -> SweepCell:
    """The same cell re-expressed with L in the harm fields, so `break_even` -- the
    FROZEN rule -- applies to it unchanged.

    A shadow, not an edit: the caller's cells are never touched.  N3 travels with
    it, and gains one more way to be absent -- a cell with no weight to be scored
    at (lambda-bar is None) is NOT silently skipped and NOT given someone else's
    weight; it carries WHY, and `break_even` stops at it exactly as it stops at a
    cell where no attack could be built.
    """
    why = reason or cell.reason
    if why is None and (B1 not in cell.curves or SENTINEL not in cell.curves):
        why = ("the cell carries no per-policy curves, so L cannot be computed "
               "from it")
    if why is not None:
        return SweepCell(d_prime=cell.d_prime, delta=cell.delta,
                         harm_b1=float("nan"), harm_sentinel=float("nan"),
                         dharm=float("nan"), ci_lo=float("nan"),
                         ci_hi=float("nan"), n_feasible=cell.n_feasible,
                         n_total=cell.n_total, reason=why, curves=cell.curves)
    lo, hi = loss_interval(cell, lambda_Q, lambda_T)
    return SweepCell(d_prime=cell.d_prime, delta=cell.delta,
                     harm_b1=cell.curves[B1].loss(lambda_Q, lambda_T),
                     harm_sentinel=cell.curves[SENTINEL].loss(lambda_Q, lambda_T),
                     dharm=dloss(cell, lambda_Q, lambda_T), ci_lo=lo, ci_hi=hi,
                     n_feasible=cell.n_feasible, n_total=cell.n_total,
                     curves=cell.curves)


def as_loss_cells(cells, lambda_Q: float,
                  lambda_T: float = metrics.LAMBDA_T) -> list:
    """One Delta's curve, re-expressed as Delta-L at a FIXED lambda_Q."""
    return [_loss_shadow(c, lambda_Q, lambda_T) for c in cells]


def as_loss_cells_at_own_lambda_bar(cells,
                                    lambda_T: float = metrics.LAMBDA_T) -> list:
    """Each cell scored at ITS OWN lambda-bar.

    READ THIS COLUMN FOR WHAT IT IS.  The weight MOVES from cell to cell, so this
    is a boundary curve -- "at the weight where this cell's ranking turns over" --
    and not a fixed-weight curve like the other two.  It is reported because
    lambda-bar is the reportable quantity and is measured per (Delta, d'); the
    fixed-weight columns at 0 and metrics.LAMBDA_Q are the ones to read for a
    single weight.
    """
    out = []
    for c in cells:
        lb = lambda_bar(c, lambda_T)
        out.append(_loss_shadow(c, lb, lambda_T,
                                reason=None if lb is not None else
                                "no lambda-bar at this cell: no lambda_Q in (0, 5] "
                                "changes the L-ranking, so there is no own weight "
                                "to score it at"))
    return out


def break_even_loss(cells, lambda_Q: float,
                    lambda_T: float = metrics.LAMBDA_T):
    """d'* of Delta-L at a fixed lambda_Q -- `break_even`, unchanged, on L-cells."""
    return break_even(as_loss_cells(cells, lambda_Q, lambda_T))


def break_even_loss_at_own_lambda_bar(cells,
                                      lambda_T: float = metrics.LAMBDA_T):
    """d'* of Delta-L with every cell at its own lambda-bar."""
    return break_even(as_loss_cells_at_own_lambda_bar(cells, lambda_T))


def loss_break_evens(cells, lambda_T: float = metrics.LAMBDA_T) -> dict:
    """The THREE declared columns, in the declared order.

    lambda_Q = 0 and metrics.LAMBDA_Q are ILLUSTRATIONS; the middle column is the
    measured boundary.  Reporting only one of the three would turn the result into
    a statement about that one weight.
    """
    return {
        LQ_ZERO: break_even_loss(cells, 0.0, lambda_T),
        LQ_BAR: break_even_loss_at_own_lambda_bar(cells, lambda_T),
        LQ_DEFAULT: break_even_loss(cells, metrics.LAMBDA_Q, lambda_T),
    }


def refinement_points(star: float | None, grid=GRID, step: float = REFINE_STEP) -> tuple:
    """The d' values to measure inside the bracket that already contains d'*.

    DECLARED BEFORE MEASURING, like the definition itself: if d'* lands on a coarse
    grid point, the true crossing lies somewhere in (previous point, d'*], so that
    open interval -- and only it -- is re-measured at `step`.  The d'* rule is then
    re-applied to the MERGED grid; nothing is interpolated, because an interpolated
    d'* is a number with fabricated precision.

    Empty when there is no d'*, and empty when d'* is the smallest grid point
    (nothing below it was measured, so there is no bracket to refine).
    """
    ordered = sorted(grid)
    if star is None or star <= ordered[0]:
        return ()
    below = max(g for g in ordered if g < star)
    n = int(round((star - below) / step))
    return tuple(round(below + step * i, 4) for i in range(1, n))


def sweep(wfs, grid=GRID, deltas=DELTAS, budget: float = 17.95, seeds=(1, 2, 3),
          carriers=CARRIERS, progress=None, tau_follows_dprime: bool = False) -> dict:
    """The full d' x Delta measurement.  Returns {delta: [SweepCell, ...]}."""
    ag = agent.MockAgent()
    out = {d: [] for d in deltas}
    for dp in grid:
        for d in deltas:
            cell = measure_cell(wfs, dp, d, budget, seeds, carriers, ag,
                                setting_for(dp, tau_follows_dprime))
            out[d].append(cell)
            if progress:
                progress(cell)
    return out


def refine_brackets(rows: dict, wfs, budget: float, seeds, carriers=CARRIERS,
                    ag=None, tau_follows_dprime: bool = False) -> dict:
    """Re-measure each Delta's bracket at step REFINE_STEP, in place.

    The tau_sel row is threaded from the SAME rule the coarse pass used.  It would
    be very easy not to: measure_cell defaults `setting` to SETTING, so an
    unthreaded call here silently measures the refined cells at the "mid" row and
    appends them to a table of d'-row cells, producing ONE curve made of two
    different thresholds with nothing anywhere to say so.

    Threaded, a refinement point asks for the row calibrated at ITS OWN d' -- which
    the frozen table does not have, since the names are one decimal wide and the
    bracket is unknown until the coarse grid is measured -- and the run dies with a
    KeyError.  That is the correct outcome: a two-phase refined run has to generate
    its bracket's rows first, and failing loudly is what says so.  Today's CLI
    forces refinement off under --tau-follows-dprime, so this path is unreachable
    from the command line; it is threaded anyway because the trap outlives the flag.
    """
    for delta, cells in rows.items():
        for dp in refinement_points(break_even(cells)):
            cells.append(measure_cell(wfs, dp, delta, budget, seeds, carriers, ag,
                                      setting_for(dp, tau_follows_dprime)))
    return rows


def json_payload(rows: dict, *, n: int, H: int, budget: float, seeds, deltas,
                 grid, tau_follows_dprime: bool, refined: bool,
                 corpus_seed: int = CORPUS_SEED,
                 loss_columns: dict | None = None) -> dict:
    """The --json artefact: the cells, AND the identity of the run that made them.

    The cells alone cannot say which of the two tau_sel modes measured them -- on
    the published corpus the two modes agree cell for cell, so two archived files
    are indistinguishable without the run block.  An archived measurement that
    cannot name its own configuration is a number with no recipe behind it.
    """
    return {
        "run": {
            "module": "dprime_sweep.py",
            "n_workflows": n,
            "H": H,
            "budget": budget,
            "seeds": list(seeds),
            "corpus_seed": corpus_seed,
            "deltas": list(deltas),
            "grid": list(grid),
            "tau_det": TAU_DET,
            "tau_follows_dprime": bool(tau_follows_dprime),
            "tau_sel_rows": (f"{setting_for(grid[0], True)!r} .. "
                             f"{setting_for(grid[-1], True)!r}, one per grid point"
                             if tau_follows_dprime else
                             f"{SETTING!r} at every grid point -- declared confound"),
            "refined": bool(refined),
            "refine_step": REFINE_STEP if refined else None,
            "policies": list(POLICIES),
            "lambda_T": metrics.LAMBDA_T,
            "lambda_Q_columns": [LQ_ZERO, LQ_BAR, LQ_DEFAULT],
            "spend_reference_d_prime": SPEND_REFERENCE_D_PRIME,
        },
        "cells": {str(d): [asdict(c) for c in sorted(rows[d], key=lambda c: c.d_prime)]
                  for d in deltas},
        #: d'* under harm AND under L, so a reader of the artefact does not have to
        #: re-derive the headline from the cells.  The harm entry is the published
        #: number and is computed by the same call it always was.
        #: `loss_columns` lets the caller hand in the three L columns it has
        #: already computed.  Each one is a break_even scan over bootstrapped
        #: cells, and the run used to compute the same three columns three times
        #: over -- in the per-Delta report, in the frame answer, and again here --
        #: which was most of the non-measurement cost of a run.
        "break_even": {
            str(d): {"harm": break_even(rows[d]),
                     **((loss_columns or {}).get(d) or loss_break_evens(rows[d]))}
            for d in deltas},
    }


# ----------------------------------------------------------------- report ----

def table(rows) -> str:
    """One Delta's curve, dense enough to read the shape off the page."""
    lines = [f"  {'d-prime':>8}{'psi':>8}{'harm B1':>10}{'harm Sen':>10}"
             f"{'d-harm':>10}{'CI95 lo':>10}{'CI95 hi':>10}{'feas':>9}"]
    lines.append("  " + "-" * 73)
    for c in sorted(rows, key=lambda c: c.d_prime):
        if not c.usable:
            lines.append(f"  {c.d_prime:>8.2f}{'':>8}  REASON: {c.reason}")
            continue
        psi = make_detector(c.d_prime).psi
        lines.append(f"  {c.d_prime:>8.2f}{psi:>8.3f}{c.harm_b1:>10.3f}"
                     f"{c.harm_sentinel:>10.3f}{c.dharm:>+10.3f}{c.ci_lo:>+10.3f}"
                     f"{c.ci_hi:>+10.3f}{c.n_feasible:>5d}/{c.n_total:<3d}")
    return "\n".join(lines)


def _fmt(x: float, w: int = 9, p: int = 3) -> str:
    """A number, or a dash where there is none.  NEVER 0.000 for "not measured"."""
    return f"{'--':>{w}}" if x != x else f"{x:>{w}.{p}f}"


def policy_table(rows, lambda_T: float = metrics.LAMBDA_T) -> str:
    """One Delta's FOUR-policy curve: the terms of L, what each policy SPENT, and
    the weight at which the ranking turns over.

    Every harm number carries its feasible denominator (N3) and every L number
    carries the spend that bought it: "all policies run on the same budget B" is
    true of the CAP and false of the SPEND, and a table without the spend column
    reads four policies as comparable when one of them declined to play.

    lambda-bar and the two argmin columns are printed ONCE per d', on the first row
    of that d's block, because they are properties of the cell and not of a policy.
    """
    lq = metrics.LAMBDA_Q
    out = [f"  {'d-prime':>7} {'policy':<24}{'harm':>8}{'Q_fal':>8}{'T_lost':>8}"
           f"{'spent':>8}{'L(0)':>8}{'L(bar)':>8}{'L(' + str(lq) + ')':>8}"
           f"{'feas':>9}  {'lambda-bar':>10}  argmin L (0 | bar+ | " + str(lq) + ")",
           "  " + "-" * 118]
    for c in sorted(rows, key=lambda c: c.d_prime):
        lb = lambda_bar(c, lambda_T)
        lb_txt = "none" if lb is None else f"{lb:.4f}"
        if not c.usable:
            out.append(f"  {c.d_prime:>7.2f}  REASON: {c.reason}")
            continue
        if not c.curves:
            out.append(f"  {c.d_prime:>7.2f}  (no per-policy curves on this cell; "
                       f"feasible {c.n_feasible}/{c.n_total}; "
                       f"lambda-bar = {lb_txt})")
            continue
        base = l_winner_text(c, 0.0, lambda_T)
        above = "--" if lb is None else l_winner_text(c, lb + 1e-6, lambda_T)
        at_lq = l_winner_text(c, lq, lambda_T)
        tail = f"  {lb_txt:>10}  {base} | {above} | {at_lq}"
        for i, name in enumerate(POLICIES):
            cur = c.curves.get(name)
            head = f"  {c.d_prime:>7.2f} " if i == 0 else f"  {'':>7} "
            if cur is None:
                out.append(f"{head}{name:<24}  REASON: not measured at this cell")
                continue
            lbar = float("nan") if lb is None else cur.loss(lb, lambda_T)
            out.append(f"{head}{name:<24}{_fmt(cur.harm, 8)}"
                       f"{_fmt(cur.q_false, 8)}{_fmt(cur.t_lost, 8)}"
                       f"{_fmt(cur.spent, 8, 2)}{_fmt(cur.loss(0.0, lambda_T), 8)}"
                       f"{_fmt(lbar, 8)}{_fmt(cur.loss(lq, lambda_T), 8)}"
                       f"{cur.n_feasible:>6d}/{cur.n_total:<3d}"
                       + (tail if i == 0 else ""))
    return "\n".join(out)


def _short(name: str) -> str:
    """"B5 risk-score" -> "B5".  ONLY for the wide per-cell table, whose columns
    cannot hold four registry keys joined by "=" without running into each other.
    The header prints the mapping, and every other table keeps the keys verbatim."""
    return name.split()[0]


def pairwise_table(rows, lambda_T: float = metrics.LAMBDA_T) -> str:
    """One Delta's cells with BOTH weights side by side: lambda-bar (four-policy,
    pre-registered) and lambda-cross (pairwise, what the claim form needs).

    This is the table the spike's per-cell section is transcribed from, and it is
    printed rather than assembled by hand because the last hand-typed copy of it
    turned 24 tied cells into 24 Sentinel wins.  The argmin columns are the cell's
    own, at the two conventions that do not agree (AT_ZERO, ABOVE_ZERO), printed
    under labels that say which is which.
    """
    lq = metrics.LAMBDA_Q
    keys = ", ".join(f"{_short(n)} = {n}" for n in POLICIES)
    out = [f"  {LAMBDA_BAR_NAME}  |  {LAMBDA_CROSS_NAME}",
           f"  policy keys abbreviated: {keys}",
           f"  {'d-prime':>7}{'lambda-bar':>12}  {'argmin L @ ' + AT_ZERO:<26}"
           f"{'argmin L @ lambda-bar+':<24}{'argmin L @ lambda_Q=' + str(lq):<26}"
           + "".join(f"{'Sen vs ' + _short(n):>26}" for n in POLICIES
                     if n != SENTINEL),
           "  " + "-" * 173]
    for c in sorted(rows, key=lambda c: c.d_prime):
        if not c.usable:
            out.append(f"  {c.d_prime:>7.2f}  REASON: {c.reason}")
            continue
        lb = lambda_bar(c, lambda_T)
        lb_txt = "none" if lb is None else f"{lb:.4f}"

        def argmin(lq_):
            w = l_winners(c, lq_, lambda_T)
            return "=".join(_short(n) for n in w) if w else "--"

        above = "--" if lb is None else argmin(lb + 1e-6)
        out.append(f"  {c.d_prime:>7.2f}{lb_txt:>12}  {argmin(0.0):<26}"
                   f"{above:<24}{argmin(lq):<26}"
                   + "".join(f"{pairwise_text(c, n, lambda_T):>26}"
                             for n in POLICIES if n != SENTINEL))
    return "\n".join(out)


def loss_table(rows, lambda_Q: float, lambda_T: float = metrics.LAMBDA_T) -> str:
    """One Delta's Delta-L curve at a FIXED lambda_Q -- the same layout as `table`,
    so the L curve and the harm curve can be read against each other line by line."""
    lines = [f"  {'d-prime':>8}{'L B1':>10}{'L Sen':>10}"
             f"{'d-L':>10}{'CI95 lo':>10}{'CI95 hi':>10}{'feas':>9}"]
    lines.append("  " + "-" * 65)
    for c in sorted(as_loss_cells(rows, lambda_Q, lambda_T),
                    key=lambda c: c.d_prime):
        if not c.usable:
            lines.append(f"  {c.d_prime:>8.2f}  REASON: {c.reason}")
            continue
        lines.append(f"  {c.d_prime:>8.2f}{c.harm_b1:>10.3f}"
                     f"{c.harm_sentinel:>10.3f}{c.dharm:>+10.3f}{c.ci_lo:>+10.3f}"
                     f"{c.ci_hi:>+10.3f}{c.n_feasible:>5d}/{c.n_total:<3d}")
    return "\n".join(lines)


def spend_report(rows, budget: float,
                 d_prime: float = SPEND_REFERENCE_D_PRIME) -> str:
    """metrics.spend_table at the DECLARED reference grid point.

    metrics.spend_table has existed since B5 and had never been called from
    anywhere in this sweep, so a reader of the d' curve could not see that the
    policies being compared do not spend the same money.  The grid point is
    declared in SPEND_REFERENCE_D_PRIME rather than chosen per Delta, so it cannot
    be the point that flatters whichever policy the text is arguing for.
    """
    at = [c for c in rows if abs(c.d_prime - d_prime) < 1e-9]
    if not at or not at[0].curves:
        return (f"  no spend table: nothing measured at the declared reference "
                f"d' = {d_prime}")
    if not at[0].usable:
        # N3.  A refused cell can still carry finite per-policy spends -- a cell
        # loses its pairing, or a policy loses its denominator, long before the
        # audit budget stops being spent -- so filtering NaN is not the same check
        # as asking whether the cell is reportable.  Printing the table anyway
        # would put four comparable-looking numbers under a d' at which this module
        # reports nothing else.
        return (f"  no spend table at the declared reference d' = {d_prime:.1f}  "
                f"REASON: {at[0].reason}")
    spent = {k: v.spent for k, v in at[0].curves.items() if v.spent == v.spent}
    if not spent:
        return (f"  no spend table at d' = {d_prime}: every policy's spend is "
                f"absent (no feasible workflow in this cell)")
    body = metrics.spend_table(spent, budget)
    return (f"  budget CONSUMED at the declared reference d' = {d_prime:.1f} "
            f"(cap is shared, spend is not)\n"
            + "\n".join("  " + ln for ln in body.splitlines()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--n", type=int, default=40, help="number of workflows")
    ap.add_argument("--H", type=int, default=8, help="tasks per workflow")
    ap.add_argument("--budget", type=float, default=17.95)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--no-refine", action="store_true",
                    help="skip the step-0.05 refinement inside the bracket")
    ap.add_argument("--tau-follows-dprime", action="store_true",
                    help="look tau_sel up in the row calibrated at the SWEPT d' "
                         "(rows d0.0..d3.0) instead of the fixed `mid` row; "
                         "implies --no-refine, see the module docstring")
    ap.add_argument("--l-attacker-probe", action="store_true",
                    help="measure the DECLARED probe cells twice -- harm-maximising"
                         " attacker and L-maximising attacker -- and print how far"
                         " each policy's L moves, then exit.  This is the batch's"
                         " own first concern, measured (see l_attacker_probe)")
    ap.add_argument("--json", metavar="FILE",
                    help="write the cells AND a `run` block naming the corpus, the "
                         "grid, the seeds and which tau_sel mode produced them")
    a = ap.parse_args()

    wfs = make_corpus(a.n, a.H, seed=CORPUS_SEED)
    seeds = tuple(range(1, a.seeds + 1))
    if a.l_attacker_probe:
        print("=" * 78)
        print("AuditGame-SE -- does an L-MAXIMISING attacker move the L RANKING?")
        print("=" * 78)
        print(f"{a.n} workflows - H={a.H} - B={a.budget} - {a.seeds} seeds - "
              f"corpus seed {CORPUS_SEED}")
        print(l_attacker_probe(wfs, a.budget, seeds,
                              tau_follows_dprime=a.tau_follows_dprime))
        return 0
    # The table has tau_sel rows at the COARSE grid only, and cannot have more:
    # which bracket gets refined is unknown until the coarse grid is measured.
    refine = not a.no_refine and not a.tau_follows_dprime

    print("=" * 78)
    print("AuditGame-SE -- d' sweep and break-even d'* (mock agent, no LLM spend)")
    print("=" * 78)
    print(f"tau_det  = {TAU_DET!r}  FIXED  =>  phi = Phi(-tau_det) = "
          f"{make_detector(0.0).phi:.4f} at every point")
    if a.tau_follows_dprime:
        print(f"tau_sel  = frozen table, row {setting_for(GRID[0], True)!r} .. "
              f"{setting_for(GRID[-1], True)!r} -- FOLLOWS the swept d', "
              f"generated at the same phi = {make_detector(0.0).phi:.2f}")
    else:
        print(f"tau_sel  = frozen table, setting={SETTING!r} (calibrated at "
              f"d'={detector.operating_point(*detector.SETTINGS['mid'])[0]:.3f})"
              f"  -- CONFOUND, declared")
    print(f"grid     = {GRID[0]} .. {GRID[-1]} step 0.2  ({len(GRID)} points)"
          + (f", refined at step {REFINE_STEP} in the bracket" if refine else
             ", NOT refined (the tau_sel table has rows at the coarse grid only)"
             if a.tau_follows_dprime else ""))
    print(f"deltas   = {DELTAS}   REPORTED PER CELL, NEVER POOLED")
    print(f"{a.n} workflows - H={a.H} - B={a.budget} - {a.seeds} seeds - "
          f"carriers: {', '.join(CARRIERS)}")
    print("d'* = smallest d' whose CI95 lower bound of d-harm is > 0 AND stays > 0")
    print("      at every larger d' in the grid.  Declared before measuring.")
    print("=" * 78)

    rows = sweep(wfs, GRID, DELTAS, a.budget, seeds,
                 tau_follows_dprime=a.tau_follows_dprime)

    if refine:
        refine_brackets(rows, wfs, a.budget, seeds,
                        tau_follows_dprime=a.tau_follows_dprime)

    summary = {}
    #: The three L columns per Delta, computed ONCE.  Each column is a break_even
    #: scan over 10 000-resample bootstrapped cells; they are read three times
    #: below (per-Delta report, frame answer, --json artefact).
    loss_cols = {d: loss_break_evens(rows[d]) for d in DELTAS}
    for d in DELTAS:
        print(f"\n[Delta = {d}]")
        print(table(rows[d]))
        star = break_even(rows[d])
        mono = is_monotone(rows[d])
        summary[d] = (star, mono)
        print(f"  d'* = " + ("none in [0.0, 3.0] -- the CI95 lower bound never "
                             "stays above 0" if star is None else f"{star:.2f}"))
        print(f"  d-harm monotone in d': {'YES' if mono else 'NO'}")

        # ---- the DECLARED objective, beside the harm curve above -------------
        print(f"\n  [Delta = {d}]  FOUR POLICIES under L = harm + lambda_Q Q_false"
              f" + lambda_T T_lost   (lambda_T = {metrics.LAMBDA_T})")
        print(policy_table(rows[d]))
        print()
        print(f"  [Delta = {d}]  the CLAIM FORM's own quantity, per cell: "
              f"lambda-bar (four policies) BESIDE lambda-cross (pairwise)")
        print(pairwise_table(rows[d]))
        print()
        print(spend_report(rows[d], a.budget))

        cols = loss_cols[d]
        print(f"\n  d'* of d-L = L(B1) - L(Sentinel), the SAME frozen rule:")
        for k, v in cols.items():
            print(f"    {k:<34}" + ("none in [0.0, 3.0]" if v is None
                                    else f"d'* = {v:.2f}"))
        print(f"\n  d-L at lambda_Q = 0 (illustration, NOT the headline):")
        print(loss_table(rows[d], 0.0))
        print(f"\n  d-L at lambda_Q = {metrics.LAMBDA_Q} (illustration, NOT the "
              f"headline):")
        print(loss_table(rows[d], metrics.LAMBDA_Q))

    print("\n" + "=" * 78)
    print("WHERE THE THREE DECLARED SETTINGS LAND")
    print("=" * 78)
    for name in ("weak", "mid", "strong"):
        dp = detector.operating_point(*detector.SETTINGS[name])[0]
        verdict = " ".join(
            f"D={d}:" + ("n/a" if summary[d][0] is None
                         else ("above" if dp >= summary[d][0] else "BELOW"))
            for d in DELTAS)
        print(f"  {name:<7} d'={dp:.3f}   {verdict}")

    print("\n" + "=" * 78)
    print("THE FRAME ANSWER -- claim form PRE-REGISTERED (tien-dang-ky v2 SS9)")
    print("=" * 78)
    print("  Read as: Sentinel [beats / does not beat] X on L for all lambda_Q <")
    print("  lambda-bar, where lambda-bar = lambda_q_star is a RESULT, measured per")
    print("  (Delta, d') cell.  lambda_Q = 0 and 0.10 are ILLUSTRATIONS, never the")
    print("  headline.  A TIE for the smallest L is counted as a tie and not as a")
    print("  win: the curves are inserted in POLICIES order with Sentinel second, so")
    print("  min() would hand 24 of the 25 tied cells to Sentinel (see l_winners).")
    print("  READ lambda-bar WITH ITS LIMIT: metrics.lambda_q_star only accepts a")
    print("  crossing in (1e-9, 5], so where two policies TIE at lambda_Q = 0 the")
    print("  flip that happens immediately above 0 is invisible to it and the")
    print("  reported lambda-bar is read off some other pair -- an UPPER reading on")
    print("  those cells, not the range over which Sentinel actually leads.  The")
    print("  claim form's own quantity is therefore the PAIRWISE crossing, printed")
    print(f"  under its own name ({LAMBDA_CROSS_NAME}) and")
    print("  amended into the pre-registration on 18/09/2026, with lambda-bar")
    print("  reported beside it.")
    print(f"  TWO CONVENTIONS, AND THEY DISAGREE: '{AT_ZERO}' is computed at")
    print(f"  exactly 0, where a tie is a tie; '{ABOVE_ZERO}' is the limit from")
    print("  above, where a tie has already broken toward whoever quarantines")
    print("  less.  Each count below says which one it is in.")
    for d in DELTAS:
        usable = [c for c in sorted(rows[d], key=lambda c: c.d_prime) if c.usable]
        bars = [lambda_bar(c) for c in usable]
        have = [b for b in bars if b is not None]
        strict = [c.d_prime for c in usable if l_winners(c, 0.0) == [SENTINEL]]
        tied = [c.d_prime for c in usable
                if len(l_winners(c, 0.0)) > 1 and SENTINEL in l_winners(c, 0.0)]
        print(f"\n  [Delta = {d}]  usable cells {len(usable)}/{len(rows[d])}")
        print(f"    Sentinel is the SOLE argmin L at {AT_ZERO} on "
              f"{len(strict)}/{len(usable)} cells"
              + (f" (d' = {min(strict):.2f} .. {max(strict):.2f})" if strict
                 else " -- NO cell")
              + f"; TIED for it on {len(tied)} more")
        print(f"    lambda-bar measured on {len(have)}/{len(usable)} cells"
              + (f", range [{min(have):.4f} ; {max(have):.4f}]" if have else
                 " -- none in (0, 5] on any cell"))
        for other in (n for n in POLICIES if n != SENTINEL):
            ps = pairwise_summary(usable, other)
            print(f"    vs {other:<20} ahead at {ABOVE_ZERO} on "
                  f"{ps['ahead_at_zero']}/{ps['n']}"
                  f" (behind {ps['behind_from_zero']}, ahead at EVERY lambda_Q "
                  f"{ps['ahead_everywhere']}); lambda-cross on "
                  f"{len(ps['crossings'])}"
                  + ("" if not ps["crossings"] else
                     f", [{ps['min']:.4f} ; {ps['max']:.4f}], median "
                     f"{ps['median']:.4f}, >= {metrics.LAMBDA_Q} on "
                     f"{ps['crossing_at_or_above_default']}"))
        for k, v in loss_cols[d].items():
            print(f"    d'* of d-L, {k:<34}"
                  + ("none in [0.0, 3.0]" if v is None else f"d'* = {v:.2f}"))

    all_usable = [c for d in DELTAS for c in rows[d] if c.usable]
    print("\n" + "=" * 78)
    print("OVER THE WHOLE GRID -- and what the surviving claim rests on")
    print("=" * 78)
    for other in (n for n in POLICIES if n != SENTINEL):
        ps = pairwise_summary(all_usable, other)
        print(f"  Sentinel vs {other:<20} ahead at {ABOVE_ZERO} on "
              f"{ps['ahead_at_zero']}/{ps['n']}; behind {ps['behind_from_zero']}; "
              f"ahead at EVERY lambda_Q {ps['ahead_everywhere']}")
        if ps["crossings"]:
            print(f"    lambda-cross on {len(ps['crossings'])} cells: "
                  f"[{ps['min']:.4f} ; {ps['max']:.4f}], median "
                  f"{ps['median']:.4f}, >= {metrics.LAMBDA_Q} on "
                  f"{ps['crossing_at_or_above_default']}")
    print()
    print("  THE SURVIVING CLAIM IS LOAD-BEARING ON AN UNSWEPT CONSTANT.")
    print("  Sentinel's win over B1 is bought by the T_lost term, and T_lost enters")
    print(f"  L weighted by lambda_T = {metrics.LAMBDA_T} (metrics.LAMBDA_T), which")
    print("  this project has never swept.  Re-scored over the SAME cells:")
    print(lambda_t_table(all_usable, B1))
    print("  The B5 and B6 comparisons do NOT move with lambda_T: all three")
    print("  score-reading policies have T_lost = 0.000 at every cell, so the term")
    print("  cancels and only the comparison against B1 depends on this constant.")

    if a.json:
        doc = json_payload(rows, n=a.n, H=a.H, budget=a.budget, seeds=seeds,
                           deltas=DELTAS, grid=GRID,
                           tau_follows_dprime=a.tau_follows_dprime, refined=refine,
                           loss_columns=loss_cols)
        with open(a.json, "w") as fh:
            json.dump(doc, fh, indent=2)
        print(f"\n  wrote {a.json}  (run block records the mode: "
              f"tau_follows_dprime={doc['run']['tau_follows_dprime']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
