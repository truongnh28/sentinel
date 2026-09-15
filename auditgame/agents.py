"""
agents.py -- The AgentPipeline PORT.
Spec: pipelines/SPEC-Framework-Benchmark.md Part 2.2.

Swap this port to answer: *do the results depend on the agent backend?*

`carriers_written` is the DUAL constraint to `AttackScope.carriers`.  If the agent
never writes to `queue`, then injecting there always gives n_c = 1 and the ITEM
DENSITY axis is pinned to a constant.  Measured in the measurement layer, SS2.6:
at a fixed tau, FP runs from 0.076 (n=1) down to 0.019 (n=20) -- n_c is a REAL
evasion axis.

    chi  = the COST spread across carriers
    n_c  = item DENSITY within a carrier

TWO DIFFERENT AXES.  An empty carrier erases the second one, and RQ2 is left with
half its data -- exactly the D5 bug.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

import agent as _agent_mod
from core import CARRIERS


@dataclass(frozen=True)
class AgentScope:
    carriers_written: frozenset
    deterministic: bool
    cost_usd_per_task: float       # 0.0 = mock; > 0 forces a declared budget
    drift_rate: float = 0.0        # beta -- benign churn the world produces


class AgentPipeline(Protocol):
    name: str
    def scope(self) -> AgentScope: ...
    def run_task(self, t, task, store, seed, marker): ...


class MockAgentPipeline:
    """`agent.MockAgent` wrapped as a port.  Behaviour unchanged.

    Declares all four carriers -- and that is only true AFTER D5.  Before it, the
    agent wrote only memory and skill, so declaring four would be caught at once
    by A2.
    """
    name = "mock"

    def __init__(self, **kw):
        self._inner = _agent_mod.MockAgent(**kw)

    def scope(self) -> AgentScope:
        return AgentScope(carriers_written=frozenset(CARRIERS),
                          deterministic=True, cost_usd_per_task=0.0,
                          drift_rate=self._inner.drift_rate)

    def run_task(self, t, task, store, seed, marker):
        return self._inner.run_task(t, task, store, seed, marker)


REGISTRY: dict = {a.name: a for a in (MockAgentPipeline(),)}

#: Adapters not yet built, each WITH ITS REASON.
PENDING: dict = {
    "openhands": (
        None,
        "OpenHands is NOT present in code/ (only AgentPoison, MINJA, Sentinel are), "
        "and running it for real costs money. cost_usd_per_task > 0 also forces a "
        "declared budget before it may enter the grid. See "
        "pipelines/SPEC-Phan-ra-Pipeline.md P2."),
}
