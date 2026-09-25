"""carrier_policies.py -- (Task 4 stub: only the base class; Task 6 replaces this file.)

policies of the carrier world: baselines B1..B6 (SS9.2), the
positive control, and the 28-policy library of SS5.2 (8 SW + 12 BT + 8 RO).

Contract with carrier_runner.run_carrier:
  act(t) -> (target, depth) | None        ONE action per task (SS4)
  affordable(t, cost), charge(cost), spent  pacing spent <= B*(t+1)/H for every policy (D4)
  observe(t, obs)                          obs: carrier_runner.Observation | None
  remove(t, k, firing, deep, live) -> items to quarantine among the FIRING items of carrier k
Baselines "quarantine on any anomaly" (SS4: drift is what makes that rule non-optimal).
Library members carry the drift belief and remove by Algorithm 1 line 8 (D11), because
they run inside Sentinel.
"""
from __future__ import annotations

import random

import draft_setup as D
from core import CARRIERS, seed_of


class CarrierPolicy:
    def __init__(self, budget, kappa, H, rng_seed=0, setting="mid", cfg=None):
        self.budget, self.kappa, self.H = budget, kappa, H
        self.rng_seed, self.setting = rng_seed, setting
        self.cfg = cfg or {}
        self.spent = 0.0
        self.last = None                 # the last Observation, None if nothing was bought

    def affordable(self, t, cost) -> bool:
        return self.spent + cost <= self.budget * (t + 1) / self.H * (1 + 1e-9)

    def charge(self, cost) -> None:
        self.spent += cost

    def rng(self, *tag) -> random.Random:
        return random.Random(seed_of(self.rng_seed, *tag))

    def act(self, t):
        return None

    def observe(self, t, obs) -> None:
        self.last = obs

    def remove(self, t, k, firing, deep, live) -> list:
        return [it for it, _ in firing]                  # quarantine on any anomaly
