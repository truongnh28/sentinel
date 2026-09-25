"""attackers_v2.py -- the draft's attacker class on v2 (D7).

Delta is the regime parameter of a cell (draft SS8), so an attacker chooses the
rest of (k, iota, sigma, eps): carrier, WHEN (earliest / middle / latest feasible
placement), CHANNEL (direct write passes the insertion gate; repository ingress
does not -- draft SS10.6) and eps.
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
    channel: str                  # "write" | "ingress"
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


def rule_key(a: Attack) -> tuple:
    """What the attacker DOES; two names with one key are one attacker."""
    k = "uniform" if callable(a.carrier_rule) else a.carrier_rule
    return (k, a.iota_rule, a.channel, a.epsilon)


def tuning_attack_names() -> list:
    """D18: dev scripted rules + the BR columns that are not a held-out rule in disguise."""
    held = {rule_key(SCRIPTED[n]) for n in held_out()}
    return development() + [b.name for b in br_attacks() if rule_key(b) not in held]


def by_name(name: str) -> Attack:
    if name in SCRIPTED:
        return SCRIPTED[name]
    for a in br_attacks():
        if a.name == name:
            return a
    raise KeyError(name)
