"""v3/api.py -- the shared interface every v3 task codes against (plan S3, T1).

FROZEN after wave W0 (plan S2): change it only through an interface patch merged into
branch v3 before the tasks that depend on it.  Stdlib only; numpy stays inside the
modules that need it (PF, rollout, table).

WHO PRODUCES / WHO CONSUMES
    AuditAction, Observation   runner (T6) -> PolicyV3, BeliefAPI.  Built by observe (T5).
    EpisodeContext             runner / sequence (T6, T10) -> policy factories.
    PolicyV3, PolicyBase       baselines (T8), library (T11), budget schedule (T16),
                               Sentinel (T15) -> runner (T6).
    BeliefAPI, BinFeatures,    belief_pf / belief_exact (T9) -> library BT members (T11),
    BeliefFactory, Hypothesis
                               line 5 / line 8 (T12), table (T14), Sentinel (T15).
    HiddenState, EpisodeState  runner snapshot()/resume() (T6) -> rollout (T12).
    PostMortem                 runner (T6) -> sequence and line 1 (T10).  The ONLY channel
                               across workflows (C12, O4).
    LossMatrix, L5Source       line5 TableSource / RolloutSource (T12, T14) -> line 5 LP.
    EpisodeRecord              runner (T6) -> metrics / scorecard (T17), tools (T22).

WHAT THE DEFENDER MAY SEE.  Observation, EpisodeContext and PostMortem are the defender's
information set.  Nothing in them names which item or carrier is poisoned; HiddenState
and the outcome fields of EpisodeRecord are evaluator-only and must never reach a policy.
"""
from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field, fields
from typing import Callable, Protocol, runtime_checkable

from v3 import config as C

# ---------------------------------------------------------------------------------------
# Actions and observations (draft S4: A = {none} U {(audit, k, depth)}; o_t)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditAction:
    """(audit, k, depth).  `target` is one of config.TARGETS in the carrier world
    (C2 primary) or a stage name in the stage world (T20).  `depth` is the cell's
    depth for that target (C16); a policy chooses the target, the cell the depth,
    except where a declared rule lowers it (O6)."""
    target: str
    depth: int


@dataclass(frozen=True)
class Observation:
    """o_t: what the defender learns at task t (draft S4), given every task.

    requested   what the policy asked for; bought is what the runner could afford
                (sum kappa + kappa(a_t) <= B, plan T6).  None = "none".
    scores      one raw detector score per inspected object, in the order of
                `written_at`; for a commit audit, the patch's single score.
    alarm       any score over the detector threshold.
    written_at  the task at which each inspected object was written -- observable
                store metadata, never its poison label.
    checkpoint  the executable checkpoint outcome (True = passed); O8: psi_c = phi_c.
    provenance  A7 only (C1): the provenance score of the contributing skills; None in A0.
    """
    t: int
    requested: AuditAction | None
    bought: AuditAction | None
    scores: tuple = ()
    alarm: bool = False
    written_at: tuple = ()
    checkpoint: bool | None = None
    provenance: float | None = None

    @property
    def n_items(self) -> int:
        return len(self.scores)


@dataclass(frozen=True)
class EpisodeContext:
    """What a policy is told when it is built for one episode (the committed setup)."""
    world: C.WorldV3
    cell: C.Cell
    wf_id: str
    seed: int
    H: int
    budget: float                          # B for the whole episode
    depths: dict                           # target -> depth (cell.depths())
    kappa: dict                            # target -> price at that depth
    delegated: tuple                       # carriers seen only via delegated patches (O1)
    postmortems: tuple = ()                # PostMortem of earlier workflows, same cell (C12)
    rng_seed: int = 0                      # for the policy's OWN randomisation (core.seed_of)


# ---------------------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------------------


@runtime_checkable
class PolicyV3(Protocol):
    """A defender policy for one episode.  Order within task t (runner, plan T6):
    act -> buy if affordable -> inject -> agent -> audit -> observe -> quarantine."""
    name: str

    def act(self, t: int, B_t: float) -> AuditAction | None:
        """The audit action for task t given the REMAINING budget B_t (None = none)."""

    def observe(self, t: int, obs: Observation) -> None:
        """Line 7: take o_t in.  Called at every task, also when nothing was bought."""

    def quarantine(self, t: int) -> str | None:
        """Lines 8-9: the carrier (config.CARRIERS) whose every live item is removed
        after o_t, or None."""

    def decision_log(self) -> list:
        """JSON-serialisable decisions (e.g. the line-5 distribution x_t, never the
        realised draw's seed).  The runner hashes it into EpisodeRecord.decision_log_sha256."""


#: Builds a fresh policy per episode.
PolicyFactory = Callable[[EpisodeContext], PolicyV3]


class PolicyBase:
    """Defaults for PolicyV3: observes nothing, never quarantines, logs nothing."""
    name = "base"

    def __init__(self, ctx: EpisodeContext):
        self.ctx = ctx
        self._log: list = []

    def act(self, t: int, B_t: float) -> AuditAction | None:
        return None

    def observe(self, t: int, obs: Observation) -> None:
        return None

    def quarantine(self, t: int) -> str | None:
        return None

    def decision_log(self) -> list:
        return list(self._log)

    def action(self, target: str) -> AuditAction:
        """The cell's action on `target`: depth is the cell's, not the policy's (C16)."""
        return AuditAction(target, self.ctx.depths[target])


# ---------------------------------------------------------------------------------------
# Belief (line 7) -- implemented by belief_pf / belief_exact (T9)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Hypothesis:
    """One particle / exact hypothesis over s_t = (c_t, iota, sigma) (draft S4)."""
    attacked: bool
    c: tuple                               # {0,1}^4 in config.CARRIERS order
    iota: int | None
    sigma: int | None


@dataclass(frozen=True)
class BinFeatures:
    """Raw features of the line-5 table's belief bin (O16).  Binning p_attack into 5
    dev quantiles is line5_table's (T14); the other two coordinates are exact here."""
    p_attack: float                        # Pr[attacked | b_t]
    top_carrier: str                       # carrier with the highest Pr[c[k] = 1 | b_t]
    delegated_mass: float                  # posterior mass on the cell's delegated carriers

    @property
    def delegated_high(self) -> bool:
        return self.delegated_mass > C.BIN_DELEGATED_MASS_THRESHOLD


@runtime_checkable
class BeliefAPI(Protocol):
    """b_t over (c, iota, sigma) with benign drift as a competing cause (draft S5.1, S7)."""

    def update(self, t: int, obs: Observation) -> None:
        """Line 7: b_{t+1} <- Update(b_t, a_t, o_t, beta)."""

    def condition_on_quarantine(self, t: int, carrier: str) -> None:
        """After lines 8-9: every live item of `carrier` is gone, so c[carrier] = 0."""

    def p_poisoned(self) -> float:
        """Pr[poisoned | b_t]: some carrier holds poison now."""

    def carrier_mass(self) -> dict:
        """carrier -> Pr[c[k] = 1 | b_t], for every carrier in config.CARRIERS."""

    def expected_harm(self) -> float:
        """Line 8's 'expected harm': Pr[the poison reaches harm by the horizon | b_t]."""

    def bin_features(self) -> BinFeatures:
        """O16 features for the line-5 table."""

    def sample(self, n: int, seed: int) -> list:
        """n Hypothesis draws from b_t (for rollouts, T12), seeded by core.seed_of."""


#: Builds b_0 for one episode from the committed setup and line 1's Delta-hat (None = the
#: prior of O3).  beta's online update (O11) reads ctx.postmortems.
BeliefFactory = Callable[[EpisodeContext, "int | None"], BeliefAPI]


# ---------------------------------------------------------------------------------------
# Snapshot / resume (rollouts, T12) -- produced by runner (T6)
# ---------------------------------------------------------------------------------------


@dataclass
class HiddenState:
    """Evaluator-only state.  A rollout sets it from a Hypothesis; a policy never sees it."""
    attacked: bool
    c: tuple                               # {0,1}^4 in config.CARRIERS order
    k: tuple = ()                          # seeded carrier(s)
    iota: int | None = None
    sigma: int | None = None
    eps: float | None = None
    harm_locked: bool = False              # C11: harm fixed at sigma (world.harm == "locked")


@dataclass
class EpisodeState:
    """Everything needed to continue an episode from the START of task t.

    store      the core.CarrierStore (deep-copied by clone()); its items' `poisoned`
               labels are evaluator-only.
    counters   running values of EpisodeRecord's outcome fields.
    private    runner-owned (policy / agent state, draw positions); opaque to others.
    """
    wf_id: str
    seed: int
    t: int
    remaining: float
    store: object
    hidden: HiddenState
    counters: dict = field(default_factory=dict)
    private: dict = field(default_factory=dict)

    def clone(self) -> "EpisodeState":
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------------------
# Post-mortem (line 1, C12, O4)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PostMortem:
    """Published after EVERY workflow of a cell (O4), harm or not: the true (k, iota,
    sigma), plus the alarms the defender raised (for the online beta update, O11)."""
    cell_id: str
    wf_id: str
    order: int                             # position in the pinned workflow order
    seed: int
    k: tuple                               # seeded carrier(s); () if no attack
    iota: int | None
    sigma: int | None
    harm: float
    H: int
    alarms: tuple = ()                     # ((t, target), ...) of every alarm

    @property
    def delay(self) -> int | None:
        return None if self.iota is None or self.sigma is None else self.sigma - self.iota


# ---------------------------------------------------------------------------------------
# Line 5 sources (Q13): one LP, two sources of L-hat
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class LossMatrix:
    """L-hat [member x attacker class] with its Monte Carlo SE (O12)."""
    members: tuple
    classes: tuple
    L: tuple                               # len(members) rows of len(classes) floats
    se: tuple                              # same shape
    n: tuple                               # same shape: rollouts / source states used
    source: str                            # "table" | "rollout"
    note: str = ""                         # e.g. the O16 empty-bin fallback reason

    def __post_init__(self):
        shape = (len(self.members), len(self.classes))
        for name in ("L", "se", "n"):
            m = getattr(self, name)
            if len(m) != shape[0] or any(len(row) != shape[1] for row in m):
                raise ValueError(f"LossMatrix.{name} is not {shape[0]} x {shape[1]}")
        if self.source not in C.LINE5:
            raise ValueError(f"source={self.source!r} is not one of {C.LINE5}")


@runtime_checkable
class L5Source(Protocol):
    name: str                              # "table" | "rollout"

    def matrix(self, t: int, belief: BeliefAPI, B_t: float, delta_hat: int,
               ctx: EpisodeContext) -> LossMatrix:
        """L-hat(pi, pi_A | b_t, B_t) for every library member and attacker class."""


# ---------------------------------------------------------------------------------------
# The record (plan T6; read by metrics T17)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EpisodeRecord:
    """One episode.  Identity first, then outcomes.  Flat except `world`, `cell` and the
    per-task / per-target containers, so metrics_v2's readers apply unchanged."""
    # identity (config.identity plus the run's coordinates)
    split: str                             # "dev" | "eval"
    world: dict
    world_id: str
    cell: dict
    cell_id: str
    delta: object                          # = cell["delta"], flat for metrics_v2
    wf: str
    repo: str                              # repository family: the bootstrap cluster
    H: int
    order: int                             # position in the pinned workflow order
    seed: int
    policy: str                            # system name
    attack: str                            # attacker column
    placement: str | None                  # best-response placement id (cross-fit, D27)
    # the attack as realised (evaluator-known state, draft S8)
    k: tuple
    iota: int | None
    sigma: int | None
    eps: float | None
    # outcomes (Definition 1: L = harm + lambda_Q FQ + lambda_T clean lost)
    harm: float
    solved_sigma: bool
    harm_locked_at: int | None             # C11
    detected_at: int | None
    missed_before_sigma: bool              # H18
    fq: int                                # O7: carrier quarantines with c_t[k] = 0
    true_q: int                            # carrier quarantines with c_t[k] = 1
    false_removed: int                     # benign items removed by quarantines
    benign_inspected: int                  # benign objects audited (FQ %, v2 D15)
    clean_lost_branch: int                 # O7: clean patches lost with a branch quarantine
    t_lost: int                            # clean tasks lost (includes clean_lost_branch)
    n_solved: int
    spent: float                           # audit cost, CPU-minutes
    budget: float
    audits: dict                           # target -> tasks it was bought
    c_traj: tuple                          # c_t per task, e.g. ("1000", "1100", ...)
    quarantines: tuple                     # ((t, carrier), ...)
    # Sentinel's own trace (None / "" for baselines)
    delta_hat: int | None
    n_incidents_seen: int                  # post-mortems available (learning curve)
    line5_source: str | None               # "table" | "rollout" | "exact" | None
    decision_log_sha256: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, d: dict) -> "EpisodeRecord":
        names = {f.name for f in fields(cls)}
        missing, extra = names - set(d), set(d) - names
        if missing or extra:
            raise ValueError(f"record fields: missing {sorted(missing)}, extra {sorted(extra)}")
        tup = {"k", "c_traj"}
        return cls(**{n: (tuple(v) if n in tup and v is not None else
                          tuple(tuple(x) for x in v) if n == "quarantines" else v)
                      for n, v in d.items()})


def record_fields() -> tuple:
    return tuple(f.name for f in fields(EpisodeRecord))


#: The fields each S9.3 metric (and the learning curve, controls, fidelity row) reads.
#: tests/v3/test_infra_config.py checks that EpisodeRecord carries every one of them, and
#: every field v2's metrics_v2 reads.
METRIC_FIELDS = {
    "worst_case_harm": ("harm", "policy", "attack", "delta", "wf", "seed", "cell_id"),
    "clean_completion": ("t_lost", "n_solved"),
    "false_quarantine": ("fq", "true_q", "false_removed", "benign_inspected"),
    "audit_cost": ("spent", "budget", "audits"),
    "detection_delay": ("detected_at", "iota"),
    "exploitability": ("harm", "placement", "attack", "seed", "wf"),
    "regret_vs_b7": ("harm", "policy", "wf"),
    "wild_cluster_bootstrap": ("repo", "wf"),
    "learning_curve": ("n_incidents_seen", "delta_hat", "order"),
    "controls": ("policy", "delta", "harm"),
    "table_rollout_fidelity": ("line5_source",),
    "h18_missed_before_sigma": ("missed_before_sigma", "sigma"),
    "loss_definition_1": ("harm", "fq", "t_lost"),
}
