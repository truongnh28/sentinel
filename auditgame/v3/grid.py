"""v3/grid.py -- the run grid: which (world, cell, system, attacker column) a run holds, the
best-response trims of plan S8 (Q14), and the episode count of every block (T22).

Stdlib only.  Imports config (T1), attackers (T7: br_systems, BR_TRIMS, the attacker
columns), budget (T16a: B_min and its holes) and baselines (T8: the system names); it
restates none of their values.

BLOCKS (the P0 cost model's, docs/reports/v3-p0-chi-phi.md S3).  One Block is one record
file of tools/v3_run.py.  `p0` names the P0 block it is counted against.

    main                   held-out: every system x 7 held-out x rho 4 x chi 3 x detector 3
                           x Delta 5, primary world                               (P0 block 1)
    br                     best response in the main grid (D27): attackers.br_systems --
                           every system, headline detector, every (rho, chi, Delta) (block 2)
    attacker-delta         the "attacker chooses Delta" column (C10): br_systems -- the
                           Sentinel class only, headline detector, every (rho, chi) (block 3)
    sens:<name>            one-factor sensitivity worlds (Q2), held-out: every system x 7 x
                           rho 4 x Delta 5 at chi 1.33, mid detector              (block 4)
    sens-br:<name>         their best response: br_systems -- B1 and Sentinel, Delta in
                           {4, 8}; none in seed-2 (the pair block 4* is off)      (block 4)
    sens-attacker-delta:reversible
                           AUTHOR DECISION (27/09, Claude-proposed, pending the user): the
                           attacker-chooses-Delta column of the reversible-harm world is NOT
                           trimmed -- Sentinel, every position at every Delta, as P0 GD 9
                           costed it.  attackers.br_systems has no such branch (it returns
                           "none" there), so this block is the declared exception
                           UNTRIMMED_ATTACKER_DELTA                               (block 4)
    kd / kd-br             K_d in {1, 3} (K_d = 2 is the primary world, O1): B1 and
                           Sentinel, rho 4, chi 1.33, mid; best response per br_systems
                           (Delta in {4, 8})                                      (block 5)
    h18 / h18-br           the budget grid (H18, Q8): B1, Sentinel, the block schedule of
                           Prop. 5.7 and B2 uniform random x chi arms (3 depth cells + 2
                           price-only) x {b1, 2, 1, 0.5 x B_min} x rho 4, mid, Delta in
                           {1, 2, 4, 8}; the 9 (policy, depth chi) combinations at b1 already
                           in main are not rerun.  Best response per br_systems: chi 1.33 and
                           {b1, 2 x B_min} only                                   (block 6)

    Outside the core (counted, never in the core total):
    headline-rollout       Sentinel-rollout in the Table 2 cells (Q13, T19); costed by
                           rollout CPU-hours, not per episode
    sens:A7, sens:stage    C1 / C2 run these after the core ("luot bo sung sau loi")
    seed2-pairs            best response over carrier pairs when two are seeded (4*, off)

DROPPED CELLS (N3: out of the denominator, with the reason).  H18: Delta = 0 and the
attacker column (budget.BudgetUndefined -- B_min has no value there); every (rho, detector)
where budget.bmin flags COMMIT_SUFFICES (at the mid detector: rho = 1; B_min = 0, so every
multiple of it is a zero budget) at the three B_min levels -- the b1 level stays.  Cells
flagged WINDOW (Theorem 5.6(i)) are kept and carry the flag.  Per workflow, a Delta with
sigma past the horizon (Delta > H - 1) is out, as in P0 (Delta = 8 needs H >= 9).

COUNTING.  The P0 unit, so the totals compare with P0 line by line:
  * a held-out unit is one (workflow, Delta) pair x SEEDS x SURVIVAL;
  * a best-response unit is one POSITION 4 (H - Delta) per (workflow, Delta) x SEEDS x
    SURVIVAL (P0 GD 4: one sleeper per carrier and iota);
  * SURVIVAL = 0.62, P0 GD 3 (carrier_runner.survives at solve rate 0.62).
  With p0_model=True the grid is P0's own design (no S8 trims, no B_min drops), and on the
  P0 workflow unit (the secondary split, 26 workflows) it reproduces the P0 table exactly;
  tests/v3/test_infra_grid.py checks it.  Two further columns say what P0's unit leaves
  out of a best-response block, and neither is a trim:
  * `menu_bound`: T7's br_menu enumerates every eps of BR_EPS (the eps grid stays
    {0.3, 0.6, 1.0}, author decision 27/09, Claude-proposed, pending the user), the channel
    when ingress is hidden, and the 6 carrier pairs when two are seeded;
  * `dev_calibrated`: the menu actually feasible on dev per Delta (dev_menu_ratio).

The eval workflows are sealed (plan S6); the counts read only the pinned SHAPE,
corpus.EVAL_SUMMARY_PINNED (its H histogram), never an instance.
"""
from __future__ import annotations

import functools
import hashlib
from dataclasses import dataclass, replace
from itertools import product
from math import comb

from v3 import attackers as A
from v3 import baselines as BL
from v3 import budget as BU
from v3 import config as C
from v3 import corpus as K

# ---------------------------------------------------------------------------------------
# Systems (sentinel-v3.md S9; P0 GD 5: 16 systems, 6 of them in the Sentinel class)
# ---------------------------------------------------------------------------------------

B1 = BL.B1AuditAtCommit.name
B2 = BL.B2UniformRandom.name
#: B7 is the small-game minimax (T21); P0 GD 6 costs it per episode like B2.
B7 = "B7"
#: The Sentinel class (T15 builds V3_REGISTRY).  Names are PROVISIONAL until T15 lands;
#: freeze_v3 pins whatever T15 registers, and metrics.is_sentinel reads the prefix.
SENTINEL = "Sentinel"
SENTINEL_CLASS = (SENTINEL, "Sentinel oracle-Delta", "Sentinel -randomization",
                  "Sentinel -alarm memory", "Sentinel -transition uncertainty",
                  "Sentinel -benign-drift")
SENTINEL_ROLLOUT = "Sentinel-rollout"      # T15 reference arm, headline cells only (Q13)
BASELINE_SYSTEMS = (B1, B2, BL.B3AuditOnInsertion.name, BL.B4AuditOnRetrieval.name,
                    BL.B5RiskScore.name, BL.B6TwoStage.name, B7, BL.CostGreedy.name,
                    BL.StageWeightedRandomised.name, BL.OracleControl.name)
SYSTEMS = BASELINE_SYSTEMS + SENTINEL_CLASS
BLOCK_SCHEDULE = BU.BlockSchedule.name
H18_POLICIES = (B1, SENTINEL, BLOCK_SCHEDULE, B2)   # B2 = the "uniform random" of H18
PAIR = (B1, SENTINEL)

#: attackers.br_systems tag -> the systems it names.
BR_SETS = {"all": SYSTEMS, "sentinel": SENTINEL_CLASS, "b1+sentinel": PAIR, "none": ()}

# ---------------------------------------------------------------------------------------
# Declared values
# ---------------------------------------------------------------------------------------

SEEDS = C.SEEDS
SURVIVAL = 0.62                            # P0 GD 3
BR_POSITIONS_PER_TASK = len(C.CARRIERS)    # P0 GD 4: 4 (H - Delta) positions
HELD_OUT = tuple(A.held_out())
BR_COLUMN = "BR"                           # the column name of a best-response unit
CORE_SENSITIVITIES = ("reversible", "ingress-hidden", "drift-persistent", "seed-2")
SUPPLEMENTARY_SENSITIVITIES = ("A7", "stage")          # C1, C2: after the core
#: AUTHOR DECISION 27/09 (Claude-proposed, pending the user): the attacker-chooses-Delta
#: column of these sensitivity worlds is not trimmed; world -> its systems (P0 GD 9).
UNTRIMMED_ATTACKER_DELTA = {"reversible": (SENTINEL,)}
H18_DELTAS = tuple(d for d in C.DELTAS if d >= 1)      # Delta = 0 has no B_min (R9)
H18_CHI_ARMS = tuple((chi, False) for chi in C.CHI_LEVELS) + tuple(
    (chi, True) for chi in C.CHI_LEVELS if chi != C.CHI_PRIMARY)
H18_BMIN_LEVELS = tuple(b for b in C.BUDGET_LEVELS if b != C.BUDGET_PRIMARY)
KD_EXTRA = tuple(k for k in C.KD_LEVELS if k != C.K_D_PRIMARY)
HEADLINE_WORLD = replace(C.PRIMARY, line5="rollout")

#: P0's episode counts (docs/reports/v3-p0-chi-phi.md S3, S6.2), on its unit.
P0_EPISODES = {"main": 3_049_805, "br": 4_037_837, "attacker-delta": 1_514_189,
               "sensitivity": 1_944_320, "kd": 421_203, "h18": 5_423_264}
P0_TOTAL = 16_390_618
P0_SENTINEL_CLASS = 6_530_000              # "6,53 trieu", S3 (rounded in the report)
P0_OPTIONAL = {"seed2-pairs": 2_106_413}
P0_HEADLINE = {"held-out": 7_638, "br": 18_650}
P0_BLOCKS = tuple(P0_EPISODES)
#: P0 S2: ms per episode at H = 9.46 (baselines ~ B1 in a BR enumeration, 0.66; the
#: Sentinel class with a table lookup, 0.94), and the rollout model: clone 229 us + 106 us
#: per rollout task, x 28 members x 6 classes x R draws, at every task of the episode.
MS_BASELINE = 0.66
MS_SENTINEL = 0.94
ROLLOUT_CLONE_US = 229.0
ROLLOUT_TASK_US = 106.0
ROLLOUT_PAIRS = sum(C.LIBRARY_FAMILIES.values()) * C.N_ATTACKER_CLASSES   # 28 x 6


# ---------------------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Unit:
    """One (block, world, cell, system, column): a sequence per seed in tools/v3_run.py
    (the workflows of the split in pinned order, C12)."""
    block: str
    p0: str | None                 # the P0 block it is counted against; None = outside core
    world_name: str
    world: C.WorldV3
    cell: C.Cell
    system: str
    column: str                    # a held-out attacker name, or BR_COLUMN
    core: bool = True
    flags: tuple = ()              # e.g. budget.FLAG_WINDOW

    @property
    def is_br(self) -> bool:
        return self.column == BR_COLUMN


@dataclass(frozen=True)
class Dropped:
    block: str
    world_name: str
    cell: C.Cell
    systems: tuple
    reason: str


def _cells(rhos=C.RHO_GRID, chis=(C.CHI_PRIMARY,), dprimes=(C.DPRIME_PRIMARY,),
           deltas=C.DELTAS, **kw) -> list:
    return [C.Cell(rho=r, delta=d, chi=x, dprime=p, **kw)
            for r, x, p, d in product(rhos, chis, dprimes, deltas)]


def _held_out(block, p0, wname, world, cells, systems, core=True) -> list:
    return [Unit(block, p0, wname, world, c, s, a, core)
            for c in cells for s in systems for a in HELD_OUT]


def _br(block, p0, wname, world, cells, pick, core=True) -> list:
    return [Unit(block, p0, wname, world, c, s, BR_COLUMN, core)
            for c in cells for s in pick(c)]


def _p0_br_sensitivity(cell: C.Cell, world: C.WorldV3) -> str:
    """P0 GD 9-10, before the S8 trims: B1 and Sentinel at every Delta; none in seed-2."""
    return "none" if world.n_seeded == 2 else "b1+sentinel"


def h18_br(cell: C.Cell) -> str:
    """Plan S8 for the budget grid: best response only at chi = 1.33 and {b1, 2 x B_min}.
    A b1 depth cell reads as a main cell to br_systems, so the H18 rule is applied to it
    here; every other H18 cell goes through br_systems."""
    if cell.budget == C.BUDGET_PRIMARY and not cell.price_only:
        return "all" if cell.chi == C.HEADLINE_CHI else "none"
    return A.br_systems(cell)


def _bmin_hole(cell: C.Cell) -> str | None:
    """The B_min hole of an H18 cell (reason), or None.  The flags do not depend on H; the
    longest workflow (H = 14) is used to read them."""
    try:
        b = BU.bmin(cell, C.TABLE_H_MAX)
    except BU.BudgetUndefined as e:
        return str(e)
    if BU.FLAG_COMMIT_SUFFICES in b.flags and cell.budget != C.BUDGET_PRIMARY:
        return b.flags[b.flags.index(BU.FLAG_COMMIT_SUFFICES)]
    return None


def _window_flags(cell: C.Cell) -> tuple:
    if cell.budget == C.BUDGET_PRIMARY or not isinstance(cell.delta, int):
        return ()
    return tuple(f for f in BU.bmin(cell, C.TABLE_H_MAX).flags if f == BU.FLAG_WINDOW)


@functools.lru_cache(maxsize=4)
def _enumerate(p0_model: bool) -> tuple:
    units, dropped = [], []
    P = C.PRIMARY
    sens = dict(C.sensitivities())

    # 1-3: the main grid, its best response, the attacker column
    main_cells = _cells(chis=C.CHI_LEVELS, dprimes=C.DPRIME_LEVELS)
    units += _held_out("main", "main", "primary", P, main_cells, SYSTEMS)
    units += _br("br", "br", "primary", P, main_cells, lambda c: BR_SETS[A.br_systems(c, P)])
    att_cells = _cells(chis=C.CHI_LEVELS, dprimes=C.DPRIME_LEVELS, deltas=(C.DELTA_ATTACKER,))
    units += _br("attacker-delta", "attacker-delta", "primary", P, att_cells,
                 lambda c: BR_SETS[A.br_systems(c, P)])

    # 4: one-factor sensitivity worlds (Q2)
    for name in CORE_SENSITIVITIES + SUPPLEMENTARY_SENSITIVITIES:
        w, core = sens[name], name in CORE_SENSITIVITIES
        p0 = "sensitivity" if core else None
        cells = _cells()
        units += _held_out(f"sens:{name}", p0, name, w, cells, SYSTEMS, core)
        rule = ((lambda c, w=w: BR_SETS[_p0_br_sensitivity(c, w)]) if p0_model
                else (lambda c, w=w: BR_SETS[A.br_systems(c, w)]))
        units += _br(f"sens-br:{name}", p0, name, w, cells, rule, core)
        if name in UNTRIMMED_ATTACKER_DELTA:
            units += _br(f"sens-attacker-delta:{name}", p0, name, w,
                         _cells(deltas=(C.DELTA_ATTACKER,)),
                         lambda c, s=UNTRIMMED_ATTACKER_DELTA[name]: s, core)

    # 5: the K_d axis (H19)
    kd_cells = [c for k in KD_EXTRA for c in _cells(k_delegated=k)]
    units += _held_out("kd", "kd", "primary", P, kd_cells, PAIR)
    units += _br("kd-br", "kd", "primary", P, kd_cells,
                 (lambda c: PAIR) if p0_model else (lambda c: BR_SETS[A.br_systems(c, P)]))

    # 6: the budget grid (H18)
    for rho, (chi, po), b in product(C.RHO_GRID, H18_CHI_ARMS, C.BUDGET_LEVELS):
        for d in (0,) + H18_DELTAS + (C.DELTA_ATTACKER,):
            cell = C.Cell(rho=rho, delta=d, chi=chi, dprime=C.DPRIME_PRIMARY, budget=b,
                          price_only=po)
            in_main = b == C.BUDGET_PRIMARY and not po
            policies = tuple(p for p in H18_POLICIES if not (in_main and p in SYSTEMS))
            if d not in H18_DELTAS:
                why = _bmin_hole(cell)             # BudgetUndefined, at every level
                dropped.append(Dropped("h18", "primary", cell, policies, why))
                continue
            why = None if p0_model else _bmin_hole(cell)
            if why:
                dropped.append(Dropped("h18", "primary", cell, policies, why))
                continue
            fl = _window_flags(cell)
            for s in policies:
                units += [Unit("h18", "h18", "primary", P, cell, s, a, True, fl)
                          for a in HELD_OUT]
            br = "all" if p0_model else h18_br(cell)
            units += [Unit("h18-br", "h18", "primary", P, cell, s, BR_COLUMN, True, fl)
                      for s in policies if s in BR_SETS[br] or (br == "all" and s == BLOCK_SCHEDULE)]

    # outside the core
    head = [c for c in _cells(deltas=C.HEADLINE_DELTAS) if c.is_headline()]
    for c in head:
        C.check_world_cell(HEADLINE_WORLD, c)
    units += _held_out("headline-rollout", None, "headline-rollout", HEADLINE_WORLD, head,
                       (SENTINEL_ROLLOUT,), core=False)
    units += _br("headline-rollout-br", None, "headline-rollout", HEADLINE_WORLD, head,
                 lambda c: (SENTINEL_ROLLOUT,), core=False)
    units += _br("seed2-pairs", None, "seed-2", sens["seed-2"], _cells(),
                 lambda c: BR_SETS[A.br_systems(c, sens["seed-2"], core=False)], core=False)
    return tuple(units), tuple(dropped)


def units(p0_model: bool = False) -> tuple:
    """Every unit of the grid (plan S8 trims applied unless p0_model)."""
    return _enumerate(p0_model)[0]


def dropped(p0_model: bool = False) -> tuple:
    """Every cell left out, with its reason (N3)."""
    return _enumerate(p0_model)[1]


def blocks(p0_model: bool = False) -> list:
    """Block names in enumeration order."""
    seen = []
    for u in units(p0_model):
        if u.block not in seen:
            seen.append(u.block)
    return seen


# ---------------------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------------------


def histogram(split: str) -> dict:
    """H -> workflows.  'primary' / 'secondary': the pinned eval SHAPE (no instance);
    'dev': the 100 dev workflows."""
    if split == "dev":
        out: dict = {}
        for wf in K.dev_workflows():
            out[wf.H] = out.get(wf.H, 0) + 1
        return dict(sorted(out.items()))
    return {int(h): n for h, n in K.EVAL_SUMMARY_PINNED[split]["H_histogram"].items()}


def _pairs(hist: dict, delta: int) -> int:
    return sum(n for h, n in hist.items() if h >= delta + 1)


def _positions(hist: dict, delta: int) -> int:
    return sum(BR_POSITIONS_PER_TASK * (h - delta) * n for h, n in hist.items() if h >= delta + 1)


def _deltas_of(cell: C.Cell) -> tuple:
    return C.DELTAS if cell.delta == C.DELTA_ATTACKER else (cell.delta,)


def menu_factor(world: C.WorldV3) -> float:
    """T7's br_menu per P0 position: |BR_EPS| x channels x carrier sets / 4."""
    channels = 1 if world.ingress_visible else len(A.CHANNELS)
    sets = comb(len(C.CARRIERS), world.n_seeded)
    return len(A.BR_EPS) * channels * sets / BR_POSITIONS_PER_TASK


@functools.lru_cache(maxsize=1)
def dev_menu_ratio() -> dict:
    """Delta -> feasible br_menu size / 4 (H - Delta) positions, summed over dev, primary
    world (every eps of BR_EPS).  Dev only; the eval menu is sealed."""
    dev = K.dev_workflows()
    out = {}
    for d in C.DELTAS:
        pos = sum(BR_POSITIONS_PER_TASK * (wf.H - d) for wf in dev if wf.H >= d + 1)
        out[d] = sum(len(A.br_menu(wf, d)) for wf in dev) / pos
    return out


def episodes(u: Unit, hist: dict, seeds: int = len(SEEDS), survival: float = SURVIVAL,
             measure: str = "p0") -> float:
    """Expected episodes of one unit on a workflow histogram.  measure: 'p0' (P0's unit),
    'menu_bound' (T7's full menu), 'dev_calibrated' (the dev-feasible menu)."""
    k = seeds * survival
    if not u.is_br:
        return k * sum(_pairs(hist, d) for d in _deltas_of(u.cell))
    total = 0.0
    for d in _deltas_of(u.cell):
        p = _positions(hist, d)
        if measure == "menu_bound":
            p *= menu_factor(u.world)
        elif measure == "dev_calibrated":
            p *= dev_menu_ratio()[d] * menu_factor(u.world) / len(A.BR_EPS)
        elif measure != "p0":
            raise ValueError(measure)
        total += p
    return k * total


def rollout_seconds(u: Unit, hist: dict, R: int, seeds: int = len(SEEDS),
                    survival: float = SURVIVAL) -> float:
    """P0 S2 rollout model of one unit: per episode on a workflow of length H,
    (H clone + H(H+1)/2 task) us x 168 (member, class) pairs x R draws."""
    k = seeds * survival
    per = lambda h: (h * ROLLOUT_CLONE_US + ROLLOUT_TASK_US * h * (h + 1) / 2) * 1e-6 \
        * ROLLOUT_PAIRS * R
    total = 0.0
    for d in _deltas_of(u.cell):
        for h, n in hist.items():
            if h >= d + 1:
                total += n * per(h) * (BR_POSITIONS_PER_TASK * (h - d) if u.is_br else 1)
    return k * total


def count(split: str = "secondary", p0_model: bool = False, measure: str = "p0") -> dict:
    """block -> {'episodes', 'sentinel_class', 'units', 'p0', 'core'} on `split`."""
    hist = histogram(split)
    out: dict = {}
    for u in units(p0_model):
        row = out.setdefault(u.block, {"episodes": 0.0, "sentinel_class": 0.0, "units": 0,
                                       "p0": u.p0, "core": u.core})
        e = episodes(u, hist, measure=measure)
        row["episodes"] += e
        row["units"] += 1
        if u.system in SENTINEL_CLASS:
            row["sentinel_class"] += e
    return out


def by_p0_block(split: str = "secondary", p0_model: bool = False,
                measure: str = "p0") -> dict:
    """P0 block -> episodes (core blocks only), plus 'total'."""
    out = {b: 0.0 for b in P0_BLOCKS}
    for row in count(split, p0_model, measure).values():
        if row["core"]:
            out[row["p0"]] += row["episodes"]
    out["total"] = sum(out[b] for b in P0_BLOCKS)
    return out


def cpu_hours(split: str = "secondary", p0_model: bool = False,
              measure: str = "p0") -> dict:
    """Simulation CPU-hours of the core, table-lookup Sentinel (P0 S2 per-episode costs)."""
    hist = histogram(split)
    h = 0.0
    for u in units(p0_model):
        if u.core:
            ms = MS_SENTINEL if u.system in SENTINEL_CLASS else MS_BASELINE
            h += episodes(u, hist, measure=measure) * ms / 3.6e6
    return {"core_simulation": h}


def headline_rollout_hours(split: str = "secondary", R: int = 16) -> dict:
    """The headline rollout block (outside the core) in rollout CPU-hours."""
    hist = histogram(split)
    out = {"held-out": 0.0, "br": 0.0}
    for u in units():
        if u.block.startswith("headline-rollout"):
            out["br" if u.is_br else "held-out"] += rollout_seconds(u, hist, R) / 3600.0
    return out


# ---------------------------------------------------------------------------------------
# Chains (what tools/v3_run.py runs) and the definition that freeze_v3 hashes
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Chain:
    """One sequence: a unit at one seed, over every workflow of the split in pinned order."""
    unit: Unit
    seed: int


def chains(block_names=None, seeds=SEEDS, systems=None, core_only: bool = False) -> list:
    pick = None if block_names is None else set(block_names)
    out = []
    for u in units():
        if pick is not None and u.block not in pick:
            continue
        if core_only and not u.core:
            continue
        if systems is not None and u.system not in systems:
            continue
        out += [Chain(u, s) for s in seeds]
    return out


def all_systems() -> tuple:
    """Every system a run may build (the harness refuses the rest once frozen)."""
    seen = []
    for u in units():
        if u.system not in seen:
            seen.append(u.system)
    return tuple(seen)


def definition() -> dict:
    """The grid as data: axes, systems, trims, decisions, every unit and every drop.  The
    manifest (freeze_v3) hashes it, so a moved cell moves the freeze."""
    return {
        "systems": list(SYSTEMS), "sentinel_class": list(SENTINEL_CLASS),
        "h18_policies": list(H18_POLICIES), "held_out": list(HELD_OUT),
        "seeds": list(SEEDS), "survival": SURVIVAL,
        "br_trims": dict(A.BR_TRIMS), "br_eps": list(A.BR_EPS),
        "untrimmed_attacker_delta": {k: list(v) for k, v in UNTRIMMED_ATTACKER_DELTA.items()},
        "core_sensitivities": list(CORE_SENSITIVITIES),
        "supplementary_sensitivities": list(SUPPLEMENTARY_SENSITIVITIES),
        "h18_deltas": list(H18_DELTAS),
        "h18_chi_arms": [list(a) for a in H18_CHI_ARMS],
        "units": [[u.block, u.world_name, C.cell_id(u.cell), u.system, u.column, u.core,
                   list(u.flags)] for u in units()],
        "dropped": [[d.block, d.world_name, C.cell_id(d.cell), list(d.systems), d.reason]
                    for d in dropped()],
    }


def definition_digest() -> str:
    return hashlib.sha256(C.canonical_json(definition()).encode("ascii")).hexdigest()


# ---------------------------------------------------------------------------------------
# Report (docs/reports/v3-p2-cost.md)
# ---------------------------------------------------------------------------------------


def _fmt(x: float) -> str:
    return f"{round(x):,}".replace(",", ".")


def report_tables() -> str:
    """Markdown tables of the per-block counts (P0 unit, menu bound, dev-calibrated) on the
    P0 workflow unit (secondary, 26) and on the primary eval split (96)."""
    lines = []
    for split in ("secondary", "primary"):
        p0m = by_p0_block(split, p0_model=True)
        tr = by_p0_block(split)
        mb = by_p0_block(split, measure="menu_bound")
        dc = by_p0_block(split, measure="dev_calibrated")
        lines += [f"### {split} ({sum(histogram(split).values())} workflow)", "",
                  "| Khối P0 | P0 báo cáo | Mô hình P0 (tái tính) | Sau cắt, đơn vị P0 | "
                  "Sau cắt, menu đủ ε (cận trên) | Sau cắt, menu khả thi trên dev |",
                  "|---|---|---|---|---|---|"]
        for b in P0_BLOCKS + ("total",):
            rep = P0_TOTAL if b == "total" else P0_EPISODES[b]
            lines.append(f"| {b} | {_fmt(rep)} | {_fmt(p0m[b])} | {_fmt(tr[b])} | "
                         f"{_fmt(mb[b])} | {_fmt(dc[b])} |")
        cpu = {m: cpu_hours(split, measure=m)["core_simulation"]
               for m in ("p0", "menu_bound", "dev_calibrated")}
        lines += ["", "CPU-giờ mô phỏng lõi (Sentinel tra bảng): "
                  + ", ".join(f"{m} {v:.1f}" for m, v in cpu.items()), ""]
        for R in C.ROLLOUT_R_GRID:
            hr = headline_rollout_hours(split, R)
            lines.append(f"- Rollout headline R = {R}: held-out {hr['held-out']:.0f} "
                         f"CPU-giờ, BR {hr['br']:.0f} CPU-giờ")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] != ["--report"]:
        raise SystemExit("usage: python -m v3.grid --report")
    print(report_tables())
    for d in dropped():
        print(f"dropped {d.block} {C.cell_id(d.cell)} rho={d.cell.rho} delta={d.cell.delta} "
              f"chi={d.cell.chi} po={d.cell.price_only} budget={d.cell.budget}: {d.reason[:70]}")
