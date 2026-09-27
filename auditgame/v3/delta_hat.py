"""v3/delta_hat.py -- Algorithm 1 line 1: Delta-hat and chi-hat "from history" (T10).

WHAT "HISTORY" IS (C12, O3, O4).  Inside one workflow nothing observed before sigma depends
on sigma, so a within-workflow estimate of Delta is only the prior.  The history is
therefore the post-mortems of the EARLIER workflows of the same cell: after every workflow
the true (k, iota, sigma) is published (api.PostMortem, O4, harm or not), in the workflow
order pinned in the manifest (v3/sequence.py).  The history is keyed by
(cell_id, system, attacker column, seed) -- HistoryKey -- and never crosses keys.

THE ESTIMATOR (O3, decided 27/09, C12: q = 0.1).
    delays      sigma - iota of every earlier post-mortem that carries an attack; a clean
                workflow publishes a post-mortem (O4) but carries no delay.  The record's
                n_incidents_seen counts every post-mortem available (api, runner T6).
    quantile    the lower empirical q-quantile: the ceil(q n)-th smallest delay (so with
                n <= 10 delays and q = 0.1 it is the minimum).  A LOW quantile because an
                underestimate keeps the guarantee (Cor. 6.6).
    minimum     at least DHAT_MIN_POSTMORTEMS = 1 incident; before that, the prior 1.
    grid        rounded DOWN to the nearest level of config.DELTAS (Cor. 6.6); a delay
                above the grid maps to its top level.
chi-hat is chi_range of the cell's price table (ctx.kappa), draft S5.1's formula.

ARMS.  "postmortem" is line 1 (the only headline arm).  "oracle" is told the current
workflow's true Delta (an upper bound, C12); "prior" never leaves the prior (the
'-regime estimate' ablation).  An arm is carried in the system name (system_name), so no
oracle number can reach a headline row unnoticed (require_headline).

BETA (O11).  beta_evidence() reads the alarms of the post-mortems: an alarm outside
(k, [iota, sigma)) of the published attack counts as drift, as does every alarm of a clean
workflow.  The estimator itself (with the dev base rate) is the belief's (T9).

Stdlib only.  Imports config and api only (plan S9: T6 and T9 are written in parallel).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import draft_setup as D
from v3 import api as A
from v3 import config as C

Q = C.DHAT_QUANTILE
PRIOR = C.DHAT_PRIOR
MIN_POSTMORTEMS = C.DHAT_MIN_POSTMORTEMS
GRID = tuple(C.DELTAS)

ARM_POSTMORTEM = "postmortem"
ARM_ORACLE = "oracle"
ARM_PRIOR = "prior"
ARMS = (ARM_POSTMORTEM, ARM_ORACLE, ARM_PRIOR)
#: C12: every headline number comes from the non-oracle run.
HEADLINE_ARMS = (ARM_POSTMORTEM,)
_ARM_TAG = {ARM_POSTMORTEM: "", ARM_ORACLE: " [dhat=oracle]", ARM_PRIOR: " [dhat=prior]"}


class LeakError(ValueError):
    """Information that must not reach line 1 was offered to it: a post-mortem of another
    cell or seed, of the current workflow, or of a later one."""


class OracleInHeadline(ValueError):
    """A record of a non-headline arm (oracle or prior-only) reached a headline set."""


# ---------------------------------------------------------------------------------------
# The history's key
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class HistoryKey:
    """(cell_id, system, attacker column, seed): one Delta-hat history (plan T10)."""
    cell_id: str
    system: str
    attack: str
    seed: int

    @classmethod
    def of(cls, ctx: A.EpisodeContext, system: str, attack: str) -> "HistoryKey":
        return cls(cell_id=C.cell_id(ctx.cell), system=system, attack=attack, seed=ctx.seed)


@dataclass
class DeltaHatHistory:
    """The post-mortems of each key, in the pinned order."""
    _by_key: dict = field(default_factory=dict)

    def add(self, key: HistoryKey, pm: A.PostMortem) -> None:
        _same_run(pm, key.cell_id, key.seed)
        seen = self._by_key.setdefault(key, [])
        if seen and pm.order <= seen[-1].order:
            raise LeakError(f"post-mortem order {pm.order} after order {seen[-1].order}: "
                            f"the history follows the pinned order strictly")
        if any(p.wf_id == pm.wf_id for p in seen):
            raise LeakError(f"workflow {pm.wf_id} already has a post-mortem under {key}")
        seen.append(pm)

    def before(self, key: HistoryKey, order: int) -> tuple:
        """The post-mortems of `key` published before position `order`."""
        return tuple(p for p in self._by_key.get(key, ()) if p.order < order)

    def has(self, key: HistoryKey) -> bool:
        return bool(self._by_key.get(key))


def _same_run(pm: A.PostMortem, cell_id: str, seed: int) -> None:
    if not isinstance(pm, A.PostMortem):
        raise TypeError(f"line 1 reads api.PostMortem only, not {type(pm).__name__}")
    if pm.cell_id != cell_id:
        raise LeakError(f"post-mortem of cell {pm.cell_id} offered to cell {cell_id} (C12)")
    if pm.seed != seed:
        raise LeakError(f"post-mortem of seed {pm.seed} offered to seed {seed}")


# ---------------------------------------------------------------------------------------
# The estimator (O3)
# ---------------------------------------------------------------------------------------

def low_quantile(values, q: float = Q) -> float:
    """The lower empirical q-quantile: the ceil(q n)-th smallest value (n >= 1)."""
    v = sorted(values)
    if not v:
        raise ValueError("no values")
    if not 0.0 < q <= 1.0:
        raise ValueError(f"q={q} is not in (0, 1]")
    return v[max(0, math.ceil(q * len(v)) - 1)]


def round_down_to_grid(x, grid=GRID) -> int:
    """The largest grid level <= x (Cor. 6.6: round down, never up)."""
    below = [g for g in grid if g <= x]
    if not below:
        raise ValueError(f"{x} is below the grid {tuple(grid)}")
    return max(below)


def delays(postmortems) -> list:
    """sigma - iota of every post-mortem that carries an attack."""
    return [p.delay for p in postmortems if p.delay is not None]


def n_incidents(postmortems) -> int:
    return len(delays(postmortems))


def estimate(postmortems, *, q: float = Q, prior: int = PRIOR,
             min_n: int = MIN_POSTMORTEMS, grid=GRID) -> int:
    """O3: the low quantile of the delays seen, on the grid; the prior before min_n."""
    d = delays(postmortems)
    if len(d) < min_n:
        return prior
    return round_down_to_grid(low_quantile(d, q), grid)


def chi_hat(kappa: dict) -> float:
    """chi-hat from the cell's price table: draft S5.1's max |k - k'| / kappa-bar."""
    return D.chi_range(kappa)


# ---------------------------------------------------------------------------------------
# Line 1
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Line1:
    """What line 1 hands the rest of Algorithm 1 at the start of one workflow."""
    delta_hat: int
    chi_hat: float | None
    n_incidents_seen: int              # post-mortems available = len(ctx.postmortems), as
                                       # api.EpisodeRecord and runner (T6) define it; the
                                       # learning curve's x (metrics.learning_curve)
    n_delays: int                      # of those, the ones carrying an attack (O3's count)
    arm: str
    source: str                        # "prior" | "postmortem" | "oracle"


def line1(arm: str, postmortems, *, wf_id: str, order: int, cell_id: str, seed: int,
          true_delta: int | None = None, kappa: dict | None = None) -> Line1:
    """Delta-hat and chi-hat for workflow `wf_id` at position `order` of the pinned order.

    `postmortems` must all be of the same (cell_id, seed) and strictly earlier than `order`
    (LeakError otherwise).  `true_delta` is accepted by the oracle arm only."""
    if arm not in ARMS:
        raise ValueError(f"arm={arm!r} is not one of {ARMS}")
    pms = tuple(postmortems)
    for p in pms:
        _same_run(p, cell_id, seed)
        if p.wf_id == wf_id:
            raise LeakError(f"workflow {wf_id}'s own post-mortem offered to its line 1")
        if p.order >= order:
            raise LeakError(f"post-mortem at order {p.order} offered to order {order}")
    n, nd = len(pms), n_incidents(pms)
    chi = chi_hat(kappa) if kappa is not None else None
    if arm == ARM_ORACLE:
        if true_delta is None:
            raise ValueError("the oracle arm needs the workflow's true Delta")
        if isinstance(true_delta, bool) or true_delta not in GRID:
            raise ValueError(f"true Delta {true_delta!r} is not on the grid {GRID}")
        return Line1(true_delta, chi, n, nd, arm, "oracle")
    if true_delta is not None:
        raise ValueError(f"only the oracle arm is told the true Delta, not {arm!r}")
    if arm == ARM_PRIOR or nd < MIN_POSTMORTEMS:
        return Line1(PRIOR, chi, n, nd, arm, "prior")
    return Line1(estimate(pms), chi, n, nd, arm, "postmortem")


# ---------------------------------------------------------------------------------------
# Arms in system names; headline guard
# ---------------------------------------------------------------------------------------

def system_name(system: str, arm: str) -> str:
    if arm not in ARMS:
        raise ValueError(f"arm={arm!r} is not one of {ARMS}")
    return system + _ARM_TAG[arm]


def arm_of(name: str) -> str | None:
    """The line-1 arm a system name carries: a tagged arm, else None (untagged: a baseline
    or the post-mortem arm, both headline-eligible)."""
    for arm, tag in _ARM_TAG.items():
        if tag and name.endswith(tag):
            return arm
    return None


def _policy(r) -> str:
    return r["policy"] if isinstance(r, dict) else r.policy


def headline_records(recs) -> list:
    """The records a headline number may be computed from: no oracle or prior-only arm."""
    return [r for r in recs if arm_of(_policy(r)) in (None,) + HEADLINE_ARMS]


def require_headline(recs) -> None:
    bad = sorted({_policy(r) for r in recs if arm_of(_policy(r)) not in (None,) + HEADLINE_ARMS})
    if bad:
        raise OracleInHeadline(f"non-headline line-1 arms in a headline set: {bad} (C12)")


# ---------------------------------------------------------------------------------------
# beta from post-mortems (O11)
# ---------------------------------------------------------------------------------------

def _carrier(target: str) -> str:
    return C.CARRIER_OF_TARGET.get(target, target)


def is_drift_alarm(pm: A.PostMortem, t: int, target: str) -> bool:
    """O11: an alarm outside (k, [iota, sigma)) of the published attack is drift."""
    if pm.delay is None:
        return True
    return not (_carrier(target) in pm.k and pm.iota <= t < pm.sigma)


def beta_evidence(postmortems) -> dict:
    """Counts the belief's online beta update reads (T9 owns the estimator)."""
    pms = tuple(postmortems)
    alarms = [(p, t, tg) for p in pms for (t, tg) in p.alarms]
    return {"n_alarms": len(alarms),
            "n_drift_alarms": sum(is_drift_alarm(p, t, tg) for p, t, tg in alarms),
            "n_tasks": sum(p.H for p in pms),
            "n_workflows": len(pms),
            "n_clean_workflows": sum(p.delay is None for p in pms)}
