"""v3/budget.py -- the H18 budget grid (T16a): B_min(Delta), the budget levels, the
price-only chi arm, and the block schedule of Proposition 5.7 as a PolicyV3.

Stdlib only (plan S2).  Ported from theory/checks/thm4_budget.py, not imported from it.

SOURCES.  The theory note HCMUT/theory/main.tex S5: Theorem 5.6 (dl:4sua, the corrected
Theorem 4 of the draft), Proposition 5.7 (md:datduoc, the block schedule), Proposition
5.9 (md:doichieu), Lemma 5.5 (bd:cuthe, the Gaussian case).  sentinel-v3.md "Thi nghiem
cho H7, H18, H19"; plan Q8, O14, R9, T16.

B_min(Delta) -- Theorem 5.6(ii).  With l_alpha = log(1/(4 alpha)) and
n_alpha = (l_alpha - eps_c)^+ / D_s, every policy that meets R(alpha) with budget B has

    B >= K kbar n_alpha floor((H-1)/Delta)          (Delta >= 1)
    Delta >= K n_alpha                              (window, (i))

`bmin_formula` is that expression, verbatim.  `bmin(cell, H)` evaluates it on a v3 cell
with these declared readings (L1, DCM row D6.thm4):

  * alpha = ALPHA = 0.05, the value of every check in theory/checks/ (and v2's
    scoring.ALPHA_TASK).  H18's success criterion is "miss before sigma <= alpha".
  * K = the three SWEPT carriers (memory, queue, skill).  The branch carrier is audited only
    through the commit, and model D of the note has no commit-only carrier (Def. 5.1(iii));
    kbar is taken over the swept carriers, never over the commit price (Remark 5.10(2)).
  * D_s per carrier: the Gaussian case of Lemma 5.5(b) with the paper's detector,
    F_1 = N(mu, 1), mu = d' sqrt(depth) at the cell's depth for that carrier,
    F_0 = (1 - beta_k) N(0,1) + beta_k N(mu,1) with beta_k = draft_setup.BETA_WORLD
    (transient drift, D6), D_s = KL(F_0 || F_1) by quadrature (theory check part D).
  * eps_c = rho^2 d'^2 / 2: the commit audit of a delegated patch, "for every depth"
    (Lemma 5.5(b)), taken for every placement -- the draft's S2 premise that the commit
    observes only the artifact.  rho = 0 gives eps_c = 0 (Prop. 5.9's premise).
  * The depth configuration makes D_s differ across carriers, so the theorem is applied
    per carrier, as its proof already does: window k needs sum_t q_{k,t} >= n_k with
    n_k = (l_alpha - eps_c)^+ / D_{s,k}, hence
        B_min = floor((H-1)/Delta) * sum_k kappa_k n_k,   window: sum_k n_k <= Delta.
    With a common D_s this IS K kbar n_alpha floor((H-1)/Delta) (tested).

  Holes (R9), flagged and never interpolated: Delta = 0 and the "attacker" column have no
  B_min (BudgetUndefined); a cell with sum_k n_k > Delta violates the window condition
  (flag WINDOW); a cell with eps_c >= l_alpha has B_min = 0 because the commit audit alone
  meets R(alpha), Theorem 5.6(iii) (flag COMMIT_SUFFICES).

BUDGET LEVELS (Q8): b1 = H * max kappa (loose, C4: every task can buy the dearest audit;
4.1 H in every depth cell because the commit is at depth 1, plan S1), and
{2, 1, 0.5} x B_min(Delta) per cell.

PRICE-ONLY ARM (C16): the depths stay the primary cell's (3, 2, 1, 1); the four prices are
moved affinely about their mean, kappa' = kbar + lam (kappa - kbar), so kbar and the order
of prices are held and chi_range becomes the chi of the named depth cell (plan T16:
draft_setup.target_kappa_for_chi on the range scale).

BLOCK SCHEDULE (Prop. 5.7): see `block_schedule` and `BlockSchedule`.

T16b: the H18 cells (`h18_cells`), the K_d axis of H19 (`kd_cells`), and H18's success
criterion read from the runner's logged `missed_before_sigma` (`miss_rate`).
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass, field

import draft_setup as D
from v3 import api
from v3 import config as C

ALPHA = 0.05
#: The swept carriers of model D (K = 3); the commit is the branch carrier's only audit.
SWEEP_TARGETS = tuple(t for t in C.TARGETS if C.CARRIER_OF_TARGET[t] != "branch")
BETA = {t: D.BETA_WORLD[C.CARRIER_OF_TARGET[t]] for t in SWEEP_TARGETS}
MULTIPLE = {"2xBmin": 2.0, "1xBmin": 1.0, "0.5xBmin": 0.5}

FLAG_WINDOW = "window: sum_k n_k > Delta (Theorem 5.6(i)); no policy meets R(alpha) here"
FLAG_COMMIT_SUFFICES = ("commit-suffices: eps_c >= l_alpha, the commit audit alone meets "
                        "R(alpha) (Theorem 5.6(iii)); B_min = 0")


class BudgetUndefined(ValueError):
    """The cell has no B_min (Delta = 0 or the attacker column, R9).  The grid drops it and
    records the message as the reason (N3)."""


# ---------------------------------------------------------------------------------------
# Theorem 5.6
# ---------------------------------------------------------------------------------------

def ell_alpha(alpha: float = ALPHA) -> float:
    """l_alpha = log(1 / (4 alpha)) (Lemma 5.4, Bretagnolle-Huber)."""
    if not 0.0 < alpha < 0.25:
        raise ValueError(f"alpha={alpha} must lie in (0, 1/4) (Def. 5.1(ix))")
    return math.log(1.0 / (4.0 * alpha))


def n_alpha(ell: float, eps_c: float, D_s: float) -> float:
    """n_alpha = (l_alpha - eps_c)^+ / D_s (Theorem 5.6)."""
    if D_s <= 0.0:
        raise ValueError(f"D_s={D_s} must be positive")
    return max(0.0, ell - eps_c) / D_s


def _check_delta(H: int, delta) -> None:
    if isinstance(delta, bool) or not isinstance(delta, int):
        raise BudgetUndefined(f"Delta={delta!r}: B_min is defined for a fixed integer "
                              "delay only; the attacker column has none (R9)")
    if delta < 1:
        raise BudgetUndefined(f"Delta={delta}: B_min is defined for Delta >= 1 only; "
                              "Delta = 0 is dropped from H18 (Theorem 5.6(ii), R9)")
    if delta > H - 1:
        raise BudgetUndefined(f"Delta={delta} > H-1={H - 1}: no placement fits (Def. 5.1(i))")


def bmin_formula(H: int, delta: int, K: int, kbar: float, n_alpha: float) -> float:
    """Theorem 5.6(ii), verbatim: B >= K kbar n_alpha floor((H-1)/Delta)."""
    _check_delta(H, delta)
    return K * kbar * n_alpha * ((H - 1) // delta)


def bmin_carriers(H: int, delta: int, kappa: dict, n: dict) -> float:
    """The per-carrier form of Theorem 5.6(ii): floor((H-1)/Delta) sum_k kappa_k n_k."""
    _check_delta(H, delta)
    return ((H - 1) // delta) * sum(kappa[k] * n[k] for k in n)


def window_ok(delta: int, n: dict) -> bool:
    """Theorem 5.6(i) per carrier: sum_k n_k <= Delta (= K n_alpha <= Delta if common)."""
    return sum(n.values()) <= delta + 1e-12


# ---------------------------------------------------------------------------------------
# The Gaussian case (Lemma 5.5(b); theory check part D)
# ---------------------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def kl_drift_gauss(beta: float, mu: float, steps: int = 6000) -> float:
    """D_s = KL((1-beta) N(0,1) + beta N(mu,1) || N(mu,1)), Simpson on [-12, mu + 12]."""
    if not 0.0 <= beta < 1.0:
        raise ValueError(f"beta={beta} must lie in [0, 1)")
    if beta == 0.0:
        return mu * mu / 2.0
    lo, hi = -12.0, mu + 12.0
    h = (hi - lo) / steps
    c = 1.0 / math.sqrt(2.0 * math.pi)
    l1b, lb = math.log(1.0 - beta), math.log(beta)

    def g(x: float) -> float:
        f0 = c * ((1.0 - beta) * math.exp(-x * x / 2.0) + beta * math.exp(-(x - mu) ** 2 / 2.0))
        a = l1b + mu * mu / 2.0 - mu * x           # log of the N(0,1)/N(mu,1) term
        m = max(a, lb)
        return f0 * (m + math.log(math.exp(a - m) + math.exp(lb - m)))

    s = g(lo) + g(hi)
    s += 4.0 * sum(g(lo + (2 * i - 1) * h) for i in range(1, steps // 2 + 1))
    s += 2.0 * sum(g(lo + 2 * i * h) for i in range(1, steps // 2))
    return s * h / 3.0


def commit_kl_delegated(rho: float, dprime: float) -> float:
    """D_c of a commit audit on a delegated patch: rho^2 d'^2 / 2, every depth (Lemma 5.5(b))."""
    return rho * rho * dprime * dprime / 2.0


# ---------------------------------------------------------------------------------------
# Prices: the depth cells and the price-only arm
# ---------------------------------------------------------------------------------------

def price_only_kappa(chi: str) -> dict:
    """C16: the primary depths and kbar, prices moved so that chi_range = the chi of the
    depth cell `chi` (1.036 for "1.04", 2.114 for "2.11")."""
    if chi == C.CHI_PRIMARY:
        raise ValueError(f"chi={chi} is the primary cell: the price-only arm moves AWAY from it")
    base = C.Cell(rho=0.0, delta=1).kappa()                      # primary depths (3,2,1,1)
    target = D.chi_range(C.Cell(rho=0.0, delta=1, chi=chi).kappa())
    kb = D.kappa_bar(base)
    lam = target / D.chi_range(base)
    out = {t: kb + lam * (v - kb) for t, v in base.items()}
    if any(v <= 0 for v in out.values()):
        raise ValueError(f"chi={chi}: the price-only arm gives a non-positive price {out}")
    return out


def cell_kappa(cell: C.Cell) -> dict:
    """Price per target in the cell: the depth cell's (config), or the price-only arm's."""
    return price_only_kappa(cell.chi) if cell.price_only else cell.kappa()


# ---------------------------------------------------------------------------------------
# B_min of a cell, and the budget levels
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class BMin:
    value: float
    H: int
    delta: int
    alpha: float
    ell: float
    eps_c: float
    D_s: dict                              # swept target -> D_s
    n: dict                                # swept target -> n_k
    kappa: dict                            # swept target -> price at the cell's depth
    flags: tuple = field(default=())

    @property
    def window(self) -> float:
        return sum(self.n.values())

    @property
    def window_ok(self) -> bool:
        return window_ok(self.delta, self.n)


def bmin(cell: C.Cell, H: int, alpha: float = ALPHA) -> BMin:
    """B_min(Delta) of Theorem 5.6(ii) for one cell and workflow length H (module doc)."""
    _check_delta(H, cell.delta)
    kappa_all, depths = cell_kappa(cell), cell.depths()
    dprime = cell.detector().d_prime
    ell = ell_alpha(alpha)
    eps_c = commit_kl_delegated(cell.rho, dprime)
    D_s = {t: kl_drift_gauss(BETA[t], dprime * math.sqrt(depths[t])) for t in SWEEP_TARGETS}
    n = {t: n_alpha(ell, eps_c, D_s[t]) for t in SWEEP_TARGETS}
    kappa = {t: kappa_all[t] for t in SWEEP_TARGETS}
    flags = []
    if not window_ok(cell.delta, n):
        flags.append(FLAG_WINDOW)
    if eps_c >= ell:
        flags.append(FLAG_COMMIT_SUFFICES)
    return BMin(value=bmin_carriers(H, cell.delta, kappa, n), H=H, delta=cell.delta,
                alpha=alpha, ell=ell, eps_c=eps_c, D_s=D_s, n=n, kappa=kappa,
                flags=tuple(flags))


def b1(cell: C.Cell, H: int) -> float:
    """The loose level (C4): H x max kappa, the dearest audit at every task."""
    return H * max(cell_kappa(cell).values())


def budget_of(cell: C.Cell, H: int) -> float:
    """B for the whole episode at the cell's budget level (Q8).  Raises BudgetUndefined
    where B_min has no value (Delta = 0, the attacker column); flags are on bmin()."""
    if cell.budget == "b1":
        return b1(cell, H)
    return MULTIPLE[cell.budget] * bmin(cell, H).value


# ---------------------------------------------------------------------------------------
# Proposition 5.7: the block schedule
# ---------------------------------------------------------------------------------------

def counting_n(alpha: float, beta: float, gamma: float) -> int:
    """n = ceil(2 log(1/alpha) / ((1-beta)^2 gamma^2)) (Prop. 5.7)."""
    return math.ceil(2.0 * math.log(1.0 / alpha) / ((1.0 - beta) ** 2 * gamma ** 2))


def schedule_with_block(H: int, b: int, order: list) -> list:
    """sched[t] for t = 1..H (index 0 unused): for every j with (j+1) b <= H, sweep the
    carriers of `order` (cheapest first) at tasks (j+1)b - K + 1, ..., (j+1)b."""
    K = len(order)
    if b < K:
        raise ValueError(f"block length b={b} < K={K}")
    sched = [None] * (H + 1)
    j = 0
    while (j + 1) * b <= H:
        for i, k in enumerate(order):
            sched[(j + 1) * b - K + 1 + i] = k
        j += 1
    return sched


def block_schedule(H: int, K: int, delta: int, n: int, kappa: list) -> tuple:
    """Prop. 5.7 verbatim (port of thm4_budget.block_schedule): b = floor(Delta/(n+1)),
    requires K(n+1) <= Delta <= H-1; returns (sched, b), sched[t] a carrier index."""
    if not (K * (n + 1) <= delta <= H - 1):
        raise ValueError(f"Prop. 5.7 needs K(n+1) <= Delta <= H-1: K={K}, n={n}, "
                         f"Delta={delta}, H={H}")
    b = delta // (n + 1)
    order = sorted(range(K), key=lambda k: kappa[k])
    return schedule_with_block(H, b, order), b


def counting_threshold(n: int, psi: float, phi_beta: float) -> float:
    """T_theta = 1{S_theta >= n (psi + phi_beta) / 2} (Prop. 5.7)."""
    return n * (psi + phi_beta) / 2.0


def binom_tails(n: int, psi: float, phi_beta: float) -> tuple:
    """Exact error of the counting test: (P_null(T = 1), P_theta(T = 0))."""
    k0 = math.ceil(counting_threshold(n, psi, phi_beta))

    def pmf(k, p):
        return math.comb(n, k) * p ** k * (1.0 - p) ** (n - k)
    err0 = sum(pmf(k, phi_beta) for k in range(k0, n + 1))
    err1 = sum(pmf(k, psi) for k in range(0, k0))
    return err0, err1


class BlockSchedule(api.PolicyBase):
    """Prop. 5.7 as a PolicyV3 (H18).

    Sweeps the K = 3 swept carriers, cheapest first, in the last K tasks of every block of
    length b, at the cell's depths; runs the counting test on each carrier's alarms and
    quarantines the carrier it rejects.  Declared readings (L1, DCM row D6.thm4):

      * n = max over carriers of counting_n(alpha, beta_k, gamma_k), gamma_k = psi - phi
        of the cell's detector at that carrier's depth; the observation is obs.alarm.
      * b = floor(Delta / (n+1)) when K(n+1) <= Delta <= H-1 (the proposition).  Otherwise
        the proposition does not apply -- with alpha = 0.05 and the draft's detectors
        n >= 8 in every cell, so K(n+1) >= 27 and no cell with Delta <= 8 meets it -- and b = K, the densest block
        schedule (a sweep at every task), is used; precondition_met = False is logged.
      * b is then raised to ceil(K kbar H / B) if needed, so that the spend up to task t
        stays within B t / H (Prop. 5.7(c)); budget_paced = True is logged.
      * The test at task t uses the first min(n, m) sweeps of the carrier within the last
        Delta tasks [t-Delta+1, t]; at t = sigma - 1 that window is [iota, sigma-1], so
        with the precondition met this is T_theta exactly.  Evaluated after every sweep
        (sequential; Remark 5.8 on the union over carriers applies).
      * The runner's t is 0-based (v2 carrier_runner); task number = t + 1.
    """
    name = "block-schedule"

    def __init__(self, ctx: api.EpisodeContext, alpha: float = ALPHA):
        super().__init__(ctx)
        cell, H = ctx.cell, ctx.H
        if isinstance(cell.delta, bool) or not isinstance(cell.delta, int) or cell.delta < 1:
            raise BudgetUndefined(f"Delta={cell.delta!r}: the block schedule needs a fixed "
                                  "Delta >= 1 (Prop. 5.7)")
        self.delta = cell.delta
        det = cell.detector()
        self.alpha = alpha
        self.psi, self.phi_beta, n_k = {}, {}, {}
        for t in SWEEP_TARGETS:
            d = det.at_depth(ctx.depths[t])
            self.psi[t] = d.psi
            self.phi_beta[t] = d.phi + BETA[t] * (d.psi - d.phi)
            n_k[t] = counting_n(alpha, BETA[t], d.gamma)
        self.n = max(n_k.values())
        K = len(SWEEP_TARGETS)
        self.order = sorted(SWEEP_TARGETS, key=lambda t: ctx.kappa[t])   # stable on ties
        self.precondition_met = K * (self.n + 1) <= self.delta <= H - 1
        b_theory = self.delta // (self.n + 1) if self.precondition_met else K
        spend_per_block = sum(ctx.kappa[t] for t in SWEEP_TARGETS)
        if ctx.budget <= 0:
            b_budget = H + 1                                   # no block fits
        else:
            b_budget = math.ceil(spend_per_block * H / ctx.budget - 1e-9)
        self.b = max(b_theory, b_budget, K)
        self.budget_paced = self.b > b_theory
        self.sched = schedule_with_block(H, self.b, self.order)
        self._hist = {t: [] for t in SWEEP_TARGETS}           # (t, alarm) of bought sweeps
        self._pending = None
        self._log.append({"b": self.b, "n": self.n, "order": list(self.order),
                          "precondition_met": self.precondition_met,
                          "budget_paced": self.budget_paced})

    def act(self, t: int, B_t: float) -> api.AuditAction | None:
        task = t + 1
        target = self.sched[task] if 1 <= task < len(self.sched) else None
        if target is None:
            return None
        if self.ctx.kappa[target] > B_t + 1e-9:
            self._log.append({"t": t, "unaffordable": target})
            return None
        self._log.append({"t": t, "sweep": target})
        return self.action(target)

    def observe(self, t: int, obs: api.Observation) -> None:
        a = obs.bought
        if a is None or a.target not in self._hist:
            return
        k = a.target
        self._hist[k].append((t, bool(obs.alarm)))
        win = [al for (s, al) in self._hist[k] if s >= t - self.delta + 1][: self.n]
        m, S = len(win), sum(win)
        if m and S >= counting_threshold(m, self.psi[k], self.phi_beta[k]) - 1e-12:
            self._pending = C.CARRIER_OF_TARGET[k]
            self._hist[k] = []
            self._log.append({"t": t, "reject": k, "S": S, "m": m})

    def quarantine(self, t: int) -> str | None:
        q, self._pending = self._pending, None
        return q


def block_schedule_factory(ctx: api.EpisodeContext) -> BlockSchedule:
    return BlockSchedule(ctx)


# ---------------------------------------------------------------------------------------
# T16b: the H18 grid, the K_d axis (H19), and H18's success criterion
# ---------------------------------------------------------------------------------------
#
# The axes below are the declaration of sentinel-v3.md S8 ("Thi nghiem cho H7, H18, H19");
# T22's grid.py can read them from here (as it reads attackers.BR_TRIMS), so the smoke of
# T16b and the grid run the same cells.

#: H18: Delta = 0 has no B_min (R9) and the attacker column neither; both are dropped.
H18_DELTAS = tuple(d for d in C.DELTAS if not isinstance(d, bool) and d >= 1)
#: H18's chi arms (chi, price_only): the three depth cells (C16(a)) and the two
#: price-only arms (C16), which hold the primary depths and kbar.
H18_CHI_ARMS = tuple((chi, False) for chi in C.CHI_LEVELS) + tuple(
    (chi, True) for chi in C.CHI_LEVELS if chi != C.CHI_PRIMARY)
#: sentinel-v3.md S8: "Policy: B1, Sentinel, lich khoi cua Menh de 5.7, uniform random".
#: "Sentinel" is T15's system; the price-only arm is a cell arm (H18_CHI_ARMS), not a policy.
H18_POLICIES = ("B1 audit-at-commit", "Sentinel", BlockSchedule.name, "B2 uniform random")


def h18_cells() -> list:
    """Every H18 cell: rho x Delta >= 1 x chi arm x budget level, at the primary detector
    and K_d (sentinel-v3.md S8; the chi arms of C16)."""
    return [C.Cell(rho=rho, delta=delta, chi=chi, price_only=po, budget=level)
            for rho in C.RHO_GRID for delta in H18_DELTAS for chi, po in H18_CHI_ARMS
            for level in C.BUDGET_LEVELS]


def kd_cells(deltas: tuple = C.DELTAS) -> list:
    """H19: K_d in {1, 2, 3} "chay o cau hinh chinh, moi rho" -- every rho and every fixed
    Delta, every other axis primary (chi 1.33, mid detector, b1).  K_d = 2 is the primary
    cell itself.  The attacker column is not on this axis (declared)."""
    return [C.Cell(rho=rho, delta=delta, k_delegated=kd)
            for kd in C.KD_LEVELS for rho in C.RHO_GRID for delta in deltas]


@dataclass(frozen=True)
class MissRate:
    """H18's success criterion, "ti le bo sot truoc sigma <= alpha", over the ATTACKED
    episodes (an unattacked record has nothing to miss).  `meets` is rate <= alpha."""
    n_attacked: int
    n_missed: int
    alpha: float

    @property
    def rate(self) -> float | None:
        return self.n_missed / self.n_attacked if self.n_attacked else None

    @property
    def meets(self) -> bool | None:
        r = self.rate
        return None if r is None else r <= self.alpha + 1e-12


def miss_rate(records, alpha: float = ALPHA) -> MissRate:
    """The miss-before-sigma rate of EpisodeRecords (or their dicts), read from the logged
    field `missed_before_sigma` (api.METRIC_FIELDS["h18_missed_before_sigma"])."""
    n = m = 0
    for rec in records:
        r = rec if isinstance(rec, dict) else rec.to_dict()
        if r["sigma"] is None:
            continue
        n += 1
        m += bool(r["missed_before_sigma"])
    return MissRate(n_attacked=n, n_missed=m, alpha=alpha)
