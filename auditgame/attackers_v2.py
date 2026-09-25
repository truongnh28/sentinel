"""attackers_v2.py -- the draft's attacker class on v2 (D7, D18, D27).

Delta is the regime parameter of a cell (draft SS8), so a scripted attacker picks the
rest of (k, iota, sigma, eps): a carrier (or a per-workflow uniform carrier), WHEN
(earliest / middle / latest feasible placement) and eps.  The channel ("write" or
repository "ingress") is kept in the names for the record, but in the carrier world
both land in the store an audit reads, so it does not change behaviour (D7).  That is
why held-out hygiene is done on BEHAVIOUR keys (k, iota rule, eps), not on names (D18).

`placements` enumerates every feasible (k, iota, sigma) at Delta: the Stackelberg best
response (SS4: the attacker "observes the defender's policy ... but not its realised
randomization") maximises over them, cross-fitted (D27).
"""
from __future__ import annotations

from dataclasses import dataclass

import build
import draft_setup as D
from core import CARRIERS, seed_of


def _uniform_carrier(wf) -> str:
    return CARRIERS[seed_of("uniform-v2", wf.wf_id) % len(CARRIERS)]


@dataclass(frozen=True)
class Attack:
    name: str
    carrier_rule: object          # carrier name, or wf -> carrier
    iota_rule: str                # "first" | "mid" | "last"
    channel: str                  # "write" | "ingress" (inert in the carrier world, D7)
    epsilon: float = 0.6

    def plan(self, wf, delta: int):
        k = self.carrier_rule(wf) if callable(self.carrier_rule) else self.carrier_rule
        cands = build.plan_poison_all(wf, k, delta, self.epsilon)
        if not cands:
            return None
        i = {"first": 0, "mid": len(cands) // 2, "last": len(cands) - 1}[self.iota_rule]
        return cands[i], self.channel


_RULES = [
    ("memory", "first", "write", 0.6), ("memory", "last", "write", 0.6),
    ("memory", "last", "ingress", 0.6), ("skill", "first", "write", 0.6),
    ("skill", "last", "write", 0.6), ("skill", "last", "ingress", 0.6),
    ("queue", "first", "write", 0.6), ("queue", "last", "ingress", 0.6),
    ("branch", "first", "write", 0.6), ("branch", "last", "write", 0.6),
    ("branch", "last", "ingress", 0.6), ("uniform", "mid", "write", 0.6),
    ("uniform", "last", "ingress", 0.6), ("memory", "last", "ingress", 0.3),
    ("skill", "last", "write", 1.0), ("queue", "mid", "write", 0.6),
    ("branch", "mid", "ingress", 0.6), ("memory", "mid", "write", 0.3),
]

SCRIPTED = {}
for _k, _i, _c, _e in _RULES:
    _n = f"{_k}-{_i}-{_c}-e{_e}"
    SCRIPTED[_n] = Attack(_n, _uniform_carrier if _k == "uniform" else _k, _i, _c, _e)


def held_out() -> list:
    return sorted(sorted(SCRIPTED, key=lambda n: seed_of("heldout-v2", n))[:D.N_HELD_OUT])


def development() -> list:
    h = set(held_out())
    return sorted(n for n in SCRIPTED if n not in h)


def br_attacks() -> list:
    return [Attack(f"br:{k}:{ch}:{rule}", k, rule, ch)
            for k in CARRIERS for ch in ("write", "ingress") for rule in ("first", "last")]


def by_name(name: str) -> Attack:
    if name in SCRIPTED:
        return SCRIPTED[name]
    for a in br_attacks():
        if a.name == name:
            return a
    raise KeyError(name)


def behavior_keys(a: Attack) -> frozenset:
    """Every (carrier, iota rule, eps) this attacker can REALISE on some workflow.
    A uniform-carrier rule can realise any carrier, so it carries four keys."""
    ks = CARRIERS if callable(a.carrier_rule) else (a.carrier_rule,)
    return frozenset((k, a.iota_rule, a.epsilon) for k in ks)


def tuning_attack_names() -> list:
    """D18: dev scripted + BR columns whose behaviour can NEVER coincide with a held-out
    attacker's on any workflow; one name per distinct behaviour set."""
    held = set().union(*(behavior_keys(SCRIPTED[n]) for n in held_out()))
    out, seen = [], set()
    for n in development() + [b.name for b in br_attacks()]:
        keys = behavior_keys(by_name(n))
        if keys & held or keys in seen:
            continue
        seen.add(keys)
        out.append(n)
    return out


def placements(wf, delta: int, epsilon: float = 0.6) -> list:
    """Every feasible PoisonSpec at Delta over all carriers -- the attacker's full menu."""
    return [ps for k in CARRIERS for ps in build.plan_poison_all(wf, k, delta, epsilon)]
