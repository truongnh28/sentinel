"""v3/attackers.py -- the draft's attacker class on v3 (T7; D4.attacker, C10, O5, D18, D27).

Draft S4: "The attacker chooses (k, iota, sigma, eps) ... Its budget constrains the number
of carriers it may seed and the magnitude of each.  It observes the defender's policy
(Stackelberg) but not its realised randomization."  v3 builds that as follows.

WHO CHOOSES DELTA (C10).  In a fixed-Delta cell the environment fixes Delta, and the
attacker chooses (k, iota, eps) with sigma = iota + Delta.  In the "attacker" column the
attacker chooses Delta too, through one of the classes O5 declares (`attacker_delta_menu`):
one fixed Delta per sequence for each Delta of the grid, and one mix that draws Delta
uniformly on the grid per workflow.  The column's value is the max over the classes
(`attacker_delta_value`).  T3's planner takes a concrete Delta only, so every entry point
resolves Delta first (`resolve_delta`).

SCRIPTED RULES (D8.attackers).  v2's 18 rules, same names, same held-out split (the same
seed_of("heldout-v2", name) hash): carrier (or v2's per-workflow uniform carrier), iota
rule first / mid / last over the feasible placements in increasing sigma, channel, eps.
Only the planner changes: T3's sleeper planner (C8) instead of v2's dormant one.  A rule
with no feasible placement on a workflow returns None and records why (N3): the cell
leaves the denominator.  The eps = 0.3 rules are often infeasible (sigma misses its own
predicate); that is T3's behaviour and it is kept.

BEHAVIOUR KEYS (D18).  Held-out hygiene is done on what an attacker can REALISE, not on
names: (carriers, iota rule, eps).  The channel joins the key only where it changes what
an audit sees -- ingress hidden from the insertion audit (S10.6, H8); where the insertion
audit sees ingress the channel is inert (D7).  With two seeded carriers the key holds the
realisable carrier pair.  A tuning column is a development or rule-BR column whose keys
never meet a held-out attacker's; line 5 uses the primary world's tuning columns as its
attacker classes (`attacker_classes`, O15).

BEST RESPONSE (D27, S7 "Game solver").  `br_menu` enumerates every feasible (k, iota, eps)
at Delta -- plus the channel where it matters, plus the carrier pair when two are seeded
-- over the declared eps grid BR_EPS.  The attacker's choice is cross-fitted (`crossfit`,
metrics_v2.crossfit_value): chosen on one half of the seeds, scored on the other, so the
draws the policy is scored with never enter the choice.  `br_systems` is the plan's S8
trim (Q14): which systems get a best-response block in which cell.

Nothing here takes an episode seed, a policy object or a draw: a placement is a function
of (workflow, Delta, world) and is fixed before the episode.

Stdlib only; imports v2, never patches it.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

import attackers_v2 as A2
import metrics_v2 as MV
from core import CARRIERS, seed_of
from v3 import config as C
from v3 import payload as P

# ---------------------------------------------------------------------------------------
# Declared values
# ---------------------------------------------------------------------------------------

IOTA_RULES = ("first", "mid", "last")
CHANNELS = ("write", "ingress")
#: The attacker's magnitude budget: each seed has eps <= EPS_MAX (draft S4, L1).  1.0 is
#: the largest eps of the scripted library and the top of payload_topic_like's range.
EPS_MAX = 1.0
#: v2's 18 rules, in v2's order: (carrier | "uniform", iota rule, channel, eps).
SCRIPTED_RULES = tuple(A2._RULES)
#: The eps grid the best response enumerates (L1): the eps values of the scripted library,
#: so the best responder's class contains every scripted rule's realisation.
BR_EPS = tuple(sorted({r[3] for r in SCRIPTED_RULES}))
#: The rule-BR columns (v2's br_attacks) use v2's eps.
RULE_BR_EPS = 0.6
#: Hash keys (core.seed_of), fixed here so they are declared once.
HELD_OUT_KEY = "heldout-v2"                 # v2's, unchanged: same split
SECOND_CARRIER_KEY = "v3-second-carrier"    # the second seeded carrier (n_seeded = 2)
DELTA_MIX_KEY = "v3-delta-mix"              # O5: the per-workflow uniform Delta draw
#: O13: one rollout per particle shared by every attacker class -- not used.
N_A_SHARED = C.N_A_SHARED_ROLLOUT


def _check_delta(delta) -> int:
    if isinstance(delta, bool) or not isinstance(delta, int) or delta < 0:
        raise ValueError(f"delta={delta!r}: plan at a concrete Delta; the "
                         f"{C.DELTA_ATTACKER!r} column resolves Delta first (resolve_delta)")
    return delta


def _check_eps(eps) -> float:
    if isinstance(eps, bool) or not isinstance(eps, (int, float)) or not 0 < eps <= EPS_MAX:
        raise ValueError(f"eps={eps!r} is outside the attacker's magnitude budget "
                         f"(0, {EPS_MAX}]")
    return float(eps)


# ---------------------------------------------------------------------------------------
# A realised attack
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Placement:
    """One realised attack: the sleeper payload(s) and the channel.  Evaluator-side: it
    names the poisoned carrier(s), so it must never reach a policy.

    payloads   1 or 2 SleeperPayload of T3, distinct carriers, one (iota, sigma, eps).
    channel    "write" | "ingress" (the agent's ingress flag, T4)."""
    payloads: tuple
    channel: str

    def __post_init__(self):
        ps = tuple(self.payloads)
        object.__setattr__(self, "payloads", ps)
        if not 1 <= len(ps) <= max(C.N_SEEDED):
            raise ValueError(f"{len(ps)} seeded carriers: the attacker's budget is at most "
                             f"{max(C.N_SEEDED)} (draft S4)")
        ks = [p.carrier for p in ps]
        if len(set(ks)) != len(ks):
            raise ValueError(f"carriers {ks} repeat: each seed is a distinct carrier")
        if len({(p.wf_id, p.iota, p.sigma, p.epsilon) for p in ps}) != 1:
            raise ValueError("the seeds of one attack share (workflow, iota, sigma, eps)")
        _check_eps(ps[0].epsilon)
        if self.channel not in CHANNELS:
            raise ValueError(f"channel={self.channel!r} is not one of {CHANNELS}")

    @property
    def k(self) -> tuple:
        return tuple(p.carrier for p in self.payloads)

    @property
    def wf_id(self) -> str:
        return self.payloads[0].wf_id

    @property
    def iota(self) -> int:
        return self.payloads[0].iota

    @property
    def sigma(self) -> int:
        return self.payloads[0].sigma

    @property
    def epsilon(self) -> float:
        return self.payloads[0].epsilon

    @property
    def delta(self) -> int:
        return self.sigma - self.iota

    @property
    def ingress(self) -> bool:
        return self.channel == "ingress"

    @property
    def id(self) -> str:
        """EpisodeRecord.placement: carriers, iota, sigma, eps, channel."""
        return f"{'+'.join(self.k)}:{self.iota}:{self.sigma}:e{self.epsilon}:{self.channel}"

    def within_budget(self, world: C.WorldV3) -> bool:
        return len(self.k) <= world.n_seeded and self.epsilon <= EPS_MAX


@dataclass(frozen=True)
class RuleInfeasible:
    """A scripted rule with no placement on a workflow at Delta (N3).  `detail` holds
    T3's per-candidate Infeasible records; `code` is their most common reason."""
    attack: str
    wf_id: str
    delta: int
    carrier: str
    epsilon: float
    code: str
    reason: str
    detail: tuple = ()


def _infeasible(name, wf, delta, k, eps, detail) -> RuleInfeasible:
    codes = Counter(r.code for r in detail)
    code = codes.most_common(1)[0][0] if codes else P.TOO_SHORT
    why = ", ".join(f"{c} x{n}" for c, n in sorted(codes.items())) or "no candidate"
    return RuleInfeasible(name, wf.wf_id, delta, k, eps, code,
                          f"no feasible sleeper for {k} at Delta = {delta}, eps = {eps} on "
                          f"H = {wf.H}: {why}", tuple(detail))


# ---------------------------------------------------------------------------------------
# Scripted rules (D8.attackers)
# ---------------------------------------------------------------------------------------


def _second_carrier(wf, name: str, first: str) -> str:
    """n_seeded = 2 (L1): the second carrier is drawn uniformly among the other three,
    per workflow and rule."""
    others = [k for k in CARRIERS if k != first]
    return others[seed_of(SECOND_CARRIER_KEY, wf.wf_id, name) % len(others)]


def _pick(cands: list, rule: str):
    return cands[{"first": 0, "mid": len(cands) // 2, "last": len(cands) - 1}[rule]]


@dataclass(frozen=True)
class AttackV3:
    """A scripted attacker: v2's rule on T3's sleeper planner."""
    name: str
    carrier_rule: str             # a carrier, or "uniform" (v2's per-workflow draw)
    iota_rule: str                # "first" | "mid" | "last"
    channel: str                  # "write" | "ingress"
    epsilon: float = 0.6

    def __post_init__(self):
        if self.carrier_rule not in CARRIERS + ("uniform",):
            raise ValueError(f"carrier rule {self.carrier_rule!r}")
        if self.iota_rule not in IOTA_RULES:
            raise ValueError(f"iota rule {self.iota_rule!r}")
        if self.channel not in CHANNELS:
            raise ValueError(f"channel {self.channel!r}")
        _check_eps(self.epsilon)

    def carriers(self, wf, world: C.WorldV3 = C.PRIMARY) -> tuple:
        """The carrier(s) this rule seeds on `wf`: its own (v2's uniform draw for
        "uniform"), plus a second one when the world seeds two."""
        k = A2._uniform_carrier(wf) if self.carrier_rule == "uniform" else self.carrier_rule
        if world.n_seeded == 1:
            return (k,)
        return (k, _second_carrier(wf, self.name, k))

    def plan(self, wf, delta: int, world: C.WorldV3 = C.PRIMARY,
             reasons: list | None = None) -> Placement | None:
        """The rule's placement at a concrete Delta, or None with a RuleInfeasible in
        `reasons` (N3)."""
        _check_delta(delta)
        ks = self.carriers(wf, world)
        detail: list = []
        cands = P.plan_sleeper_all(wf, ks[0], delta, self.epsilon, reasons=detail)
        if not cands:
            if reasons is not None:
                reasons.append(_infeasible(self.name, wf, delta, ks[0], self.epsilon, detail))
            return None
        # wire-payload-length: the length the grid actually writes is drawn (T24, D-v3-3),
        # not v2's fixed 63; each seeded carrier draws its own, seeded by its own coordinates.
        first = P.with_default_length(_pick(cands, self.iota_rule))
        pays = [first]
        for k in ks[1:]:
            # feasibility depends on the topics only, so the same (iota, sigma) holds
            second = next(p for p in P.plan_sleeper_all(wf, k, delta, self.epsilon)
                         if p.sigma == first.sigma)
            pays.append(P.with_default_length(second))
        return Placement(tuple(pays), self.channel)

    def plan_in_cell(self, wf, cell: C.Cell, world: C.WorldV3 = C.PRIMARY,
                     delta_class: "DeltaClass | None" = None,
                     reasons: list | None = None) -> Placement | None:
        return self.plan(wf, resolve_delta(cell, wf, delta_class), world, reasons)


def _build_scripted() -> dict:
    out = {}
    for k, rule, ch, eps in SCRIPTED_RULES:
        name = f"{k}-{rule}-{ch}-e{eps}"
        out[name] = AttackV3(name, k, rule, ch, eps)
    return out


SCRIPTED = _build_scripted()


def held_out() -> list:
    """v2's split, by v2's hash: the 7 names first in seed_of("heldout-v2", name) order."""
    return sorted(sorted(SCRIPTED, key=lambda n: seed_of(HELD_OUT_KEY, n))[:C.N_HELD_OUT])


def development() -> list:
    h = set(held_out())
    return sorted(n for n in SCRIPTED if n not in h)


def br_attacks() -> list:
    """v2's 16 rule-BR columns (carrier x channel x first/last, eps 0.6), same names."""
    return [AttackV3(f"br:{k}:{ch}:{rule}", k, rule, ch, RULE_BR_EPS)
            for k in CARRIERS for ch in CHANNELS for rule in ("first", "last")]


_BR_BY_NAME = {a.name: a for a in br_attacks()}


def by_name(name: str) -> AttackV3:
    if name in SCRIPTED:
        return SCRIPTED[name]
    if name in _BR_BY_NAME:
        return _BR_BY_NAME[name]
    raise KeyError(name)


# ---------------------------------------------------------------------------------------
# Behaviour keys and tuning columns (D18)
# ---------------------------------------------------------------------------------------


def _key(ks, rule, eps, channel, world) -> tuple:
    base = (tuple(sorted(ks)), rule, eps)
    return base if world.ingress_visible else base + (channel,)


def behavior_keys(a: AttackV3, world: C.WorldV3 = C.PRIMARY) -> frozenset:
    """Every behaviour this attacker can REALISE on some workflow in `world`:
    (carriers, iota rule, eps), plus the channel when ingress is hidden.  A uniform
    rule realises any carrier; with two seeded carriers, any pair holding the first."""
    firsts = CARRIERS if a.carrier_rule == "uniform" else (a.carrier_rule,)
    if world.n_seeded == 1:
        sets = {(k,) for k in firsts}
    else:
        sets = {tuple(sorted((k, x))) for k in firsts for x in CARRIERS if x != k}
    return frozenset(_key(ks, a.iota_rule, a.epsilon, a.channel, world) for ks in sets)


def realised_key(a: AttackV3, pl: Placement, world: C.WorldV3 = C.PRIMARY) -> tuple:
    """The behaviour key of one realisation of `a`."""
    return _key(pl.k, a.iota_rule, pl.epsilon, pl.channel, world)


def tuning_attack_names(world: C.WorldV3 = C.PRIMARY) -> list:
    """D18: development scripted + rule-BR columns whose behaviour can NEVER coincide
    with a held-out attacker's in `world`; one name per distinct behaviour set."""
    held = set().union(*(behavior_keys(SCRIPTED[n], world) for n in held_out()))
    out, seen = [], set()
    for n in development() + [b.name for b in br_attacks()]:
        keys = behavior_keys(by_name(n), world)
        if keys & held or keys in seen:
            continue
        seen.add(keys)
        out.append(n)
    return out


def attacker_classes() -> tuple:
    """The six D18 behaviour classes line 5 uses (T12, T14).  The line-5 table is built
    in the primary world (O15), so these are the primary world's tuning columns."""
    out = tuple(tuning_attack_names(C.PRIMARY))
    if len(out) != C.N_ATTACKER_CLASSES:
        raise AssertionError(f"{len(out)} tuning columns, config declares "
                             f"{C.N_ATTACKER_CLASSES}")
    return out


def realised_coincidences(workflows, deltas=None, world: C.WorldV3 = C.PRIMARY) -> list:
    """Where a tuning column's realised placement EQUALS a held-out rule's on the same
    workflow and Delta although their keys differ (e.g. 'first' and 'last' when a
    workflow has one feasible placement).  D18 is on keys; this is measured, not
    enforced, so the report can print it."""
    deltas = C.DELTAS if deltas is None else deltas
    held, out = held_out(), []
    for wf in workflows:
        for d in deltas:
            hp = {}
            for n in held:
                pl = SCRIPTED[n].plan(wf, d, world)
                if pl is not None:
                    hp.setdefault(pl.id, []).append(n)
            for n in tuning_attack_names(world):
                pl = by_name(n).plan(wf, d, world)
                if pl is not None and pl.id in hp:
                    out.append((wf.wf_id, d, n, tuple(hp[pl.id]), pl.id))
    return out


# ---------------------------------------------------------------------------------------
# "Attacker chooses Delta" (C10, O5)
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class DeltaClass:
    """One O5 class of the "attacker" column."""
    name: str
    kind: str                     # one of config.ATTACKER_DELTA_CLASSES
    delta: int | None             # the fixed Delta; None for the mix

    def delta_for(self, wf) -> int:
        """The Delta this class plays on `wf`.  The mix draws uniformly on the grid, per
        workflow (seed_of over the workflow id only: the same for every seed, system
        and cell, so the column stays paired)."""
        if self.delta is not None:
            return self.delta
        return C.DELTAS[seed_of(DELTA_MIX_KEY, wf.wf_id) % len(C.DELTAS)]


_DELTA_MENU = tuple(
    [DeltaClass(f"delta-fixed-{d}", C.ATTACKER_DELTA_CLASSES[0], d) for d in C.DELTAS]
    + [DeltaClass("delta-mix-uniform", C.ATTACKER_DELTA_CLASSES[1], None)])


def attacker_delta_menu() -> tuple:
    """O5, declared before any number: one fixed Delta per sequence for each Delta of the
    grid, then the uniform per-workflow mix."""
    return _DELTA_MENU


def delta_class(name: str) -> DeltaClass:
    for dc in _DELTA_MENU:
        if dc.name == name:
            return dc
    raise KeyError(name)


def resolve_delta(cell: C.Cell, wf, delta_class: DeltaClass | None = None) -> int:
    """The concrete Delta the attacker plays in `cell` on `wf`."""
    if cell.delta == C.DELTA_ATTACKER:
        if delta_class is None:
            raise ValueError("the 'attacker' column needs a Delta class (O5): "
                             "attacker_delta_menu()")
        if delta_class not in _DELTA_MENU:
            raise ValueError(f"{delta_class!r} is not a declared O5 class")
        return delta_class.delta_for(wf)
    if delta_class is not None:
        raise ValueError(f"cell Delta = {cell.delta} is fixed by the environment (C10); "
                         f"a Delta class belongs to the 'attacker' column only")
    return _check_delta(cell.delta)


def attacker_delta_value(values: dict) -> tuple:
    """The "attacker" column's value for one system: (max over the O5 classes, the class
    that attains it).  Ties go to the first class in menu order.  Every class must be
    present: a missing class would let the column understate the attacker."""
    names = [dc.name for dc in _DELTA_MENU]
    missing = [n for n in names if n not in values]
    if missing:
        raise ValueError(f"missing O5 classes {missing}")
    best = max(names, key=lambda n: (values[n], -names.index(n)))
    return values[best], best


# ---------------------------------------------------------------------------------------
# Best response (D27): the menu, the S8 trims, cross-fitting
# ---------------------------------------------------------------------------------------


def br_menu(wf, delta: int, world: C.WorldV3 = C.PRIMARY, eps_grid: tuple = BR_EPS,
            reasons: list | None = None) -> list:
    """EVERY feasible attack at a concrete Delta: (k, iota, eps) over the four carriers
    and eps_grid, sigma = iota + Delta; x channel when ingress is hidden; carrier pairs
    at one (iota, eps) when the world seeds two.  Order: eps, carriers, iota, channel.
    T3's Infeasible records go to `reasons` (N3)."""
    _check_delta(delta)
    for e in eps_grid:
        _check_eps(e)
    channels = ("write",) if world.ingress_visible else CHANNELS
    out = []
    for eps in eps_grid:
        # wire-payload-length: draw once per (carrier, sigma), before the Placement fan-out
        # over carrier pairs and channels, so every menu entry carries the drawn L (T24).
        per_k = {k: {p.sigma: P.with_default_length(p)
                    for p in P.plan_sleeper_all(wf, k, delta, eps, reasons=reasons)}
                 for k in CARRIERS}
        for ks in combinations(CARRIERS, world.n_seeded):
            for sigma in sorted(set.intersection(*(set(per_k[k]) for k in ks))):
                for ch in channels:
                    out.append(Placement(tuple(per_k[k][sigma] for k in ks), ch))
    return out


def cell_menu(wf, cell: C.Cell, world: C.WorldV3 = C.PRIMARY,
              delta_class: DeltaClass | None = None, reasons: list | None = None) -> list:
    """The best-response menu in `cell` (Delta resolved by resolve_delta)."""
    return br_menu(wf, resolve_delta(cell, wf, delta_class), world, reasons=reasons)


#: Plan S8 (Q14): the best-response blocks kept.  br_systems() implements it; T22's grid
#: reads it from here.
BR_TRIMS = {
    "main": "every system, headline detector, every (rho, chi), every Delta (D27)",
    "attacker-delta": "Sentinel-class systems only (baselines read max over Delta from main)",
    "sensitivity+kd": "B1 and Sentinel only, Delta in {4, 8}",
    "h18": "chi = 1.33 and budget in {b1, 2xBmin} only; other levels held-out only",
    "two-carrier-pairs": "off in the core (block 4*)",
    "n_a_shared": "not enabled (O13)",
}
BR_SYSTEMS = ("all", "sentinel", "b1+sentinel", "none")


def br_systems(cell: C.Cell, world: C.WorldV3 = C.PRIMARY, core: bool = True) -> str:
    """Which systems get a best-response block in (world, cell): one of BR_SYSTEMS.

    core=False lifts only the core-off pair block (4*), which then follows the
    sensitivity rule."""
    if world.n_seeded == 2 and core:
        return "none"
    h18 = cell.budget != C.BUDGET_PRIMARY or cell.price_only
    if h18:
        ok = (cell.chi == C.HEADLINE_CHI and not cell.price_only
              and cell.budget in ("b1", "2xBmin"))
        return "all" if ok else "none"
    if world != C.PRIMARY or cell.k_delegated != C.K_D_PRIMARY:
        return "b1+sentinel" if cell.delta in C.HEADLINE_DELTAS else "none"
    if cell.dprime != C.HEADLINE_DPRIME:
        return "none"
    return "sentinel" if cell.delta == C.DELTA_ATTACKER else "all"


def br_rows(wf, menu: list, run, seeds) -> list:
    """Rows {wf, placement, seed, harm} for crossfit: run(placement, seed) is the
    caller's episode (T6/T22) against the committed policy; None = not run (e.g. the N4
    survives filter)."""
    rows = []
    for pl in menu:
        for s in seeds:
            h = run(pl, s)
            if h is not None:
                rows.append({"wf": wf.wf_id, "placement": pl.id, "seed": s, "harm": h})
    return rows


def choose(rows, fold: int) -> dict:
    """wf -> the placement the attacker picks from the seeds with seed % 2 == fold only
    (the tie rule of metrics_v2.crossfit_value: the first of the sorted maxima)."""
    by: dict = {}
    for r in rows:
        if r["seed"] % 2 == fold:
            by.setdefault(r["wf"], {}).setdefault(r["placement"], []).append(r["harm"])
    out = {}
    for w, pl in by.items():
        mean = {p: sum(v) / len(v) for p, v in pl.items() if v}
        if mean:
            out[w] = max(sorted(mean), key=lambda p: mean[p])
    return out


def crossfit(rows) -> dict:
    """D27: metrics_v2.crossfit_value (chosen on one fold, scored on the other), plus the
    choices per workflow and fold for the qualitative analysis (S10.6)."""
    out = dict(MV.crossfit_value(rows))
    c0, c1 = choose(rows, 0), choose(rows, 1)
    out["choices"] = {w: {f: c.get(w) for f, c in ((0, c0), (1, c1)) if w in c}
                      for w in sorted(set(c0) | set(c1))}
    return out


# ---------------------------------------------------------------------------------------
# Report: feasibility of every rule on dev (N3)
# ---------------------------------------------------------------------------------------


def feasibility_by_rule(workflows, deltas=None, world: C.WorldV3 = C.PRIMARY) -> list:
    """One row per (rule, Delta): workflows with a placement, and the reasons of the
    others (N3: infeasible cells leave the denominator)."""
    deltas = C.DELTAS if deltas is None else deltas
    rows = []
    for name, att in SCRIPTED.items():
        for d in deltas:
            why: list = []
            ok = sum(att.plan(wf, d, world, why) is not None for wf in workflows)
            rows.append(dict(rule=name, delta=d, workflows=len(workflows), feasible=ok,
                             held_out=name in held_out(),
                             by_reason=dict(sorted(Counter(r.code for r in why).items()))))
    return rows


def _main() -> int:
    import corpus_v2
    dev = corpus_v2.make_corpus_v2()
    rows = feasibility_by_rule(dev)
    print(f"T7: scripted rules with a feasible placement on dev ({len(dev)} workflows); "
          f"* = held out")
    print(f"{'rule':30} " + " ".join(f"D={d:<3}" for d in C.DELTAS) + "  infeasible reasons")
    for name in SCRIPTED:
        rr = [r for r in rows if r["rule"] == name]
        why = Counter()
        for r in rr:
            why.update(r["by_reason"])
        mark = "*" if rr[0]["held_out"] else " "
        print(f"{mark}{name:29} " + " ".join(f"{r['feasible']:>5}" for r in rr)
              + "  " + ", ".join(f"{c} {n}" for c, n in sorted(why.items())))
    print("\nbest-response menu size on dev (sum over workflows), primary world:")
    for d in C.DELTAS:
        by_eps = {e: sum(len(br_menu(wf, d, eps_grid=(e,))) for wf in dev) for e in BR_EPS}
        print(f"  Delta = {d}: " + ", ".join(f"eps {e}: {n}" for e, n in by_eps.items())
              + f"; total {sum(by_eps.values())}")
    for world in (C.PRIMARY,) + tuple(w for n, w in C.sensitivities()
                                      if n in ("ingress-hidden", "seed-2")):
        print(f"tuning columns ({C.world_name(world)}): {tuning_attack_names(world)}")
    co = realised_coincidences(dev)
    print(f"realised coincidences tuning = held-out placement on dev (primary): {len(co)}")
    for row in Counter((c[2], c[3]) for c in co).most_common():
        print(f"  {row[0][0]} = {row[0][1]}: {row[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
