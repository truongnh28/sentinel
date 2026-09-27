"""v3/sequence.py -- the workflows of one cell in the pinned order, carrying post-mortems (T10).

THE ORDER (C12).  Which post-mortems line 1 has seen depends on the order the workflows run
in, so the order is pinned before any run: workflows sorted by
core.seed_of("v3-order", wf_id) (ties by wf_id), written into a manifest with its sha256
(order_manifest / write_order_manifest).  The same order holds for every cell, system,
attacker column and seed.  run_sequence refuses a manifest whose order is not the rule's.

THE CHANNEL (C12, O4).  The ONLY thing that crosses a workflow boundary is the published
post-mortem (api.PostMortem): after every workflow, harm or not, the true (k, iota, sigma)
and the alarms raised.  run_sequence hands each episode a frozen Step -- the history key,
the workflow, its position, the line-1 arm, the earlier post-mortems of the same key and
line 1's output -- computed BEFORE the episode runs.  Step.context(template) is the
episode's EpisodeContext with those post-mortems filled in (the belief reads them for
beta, O11).

THE EPISODE.  The runner (T6) is not imported here: a caller passes `run_episode`, any
callable Step -> (record, PostMortem).  The record may be an api.EpisodeRecord or its dict;
run_sequence checks that it carries the step's identity and line-1 trace (delta_hat,
n_incidents_seen: the learning curve, metrics.learning_curve) and that the post-mortem is
of this workflow.  postmortem_from_record builds the O4 post-mortem from a record.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from typing import Callable

import core
from v3 import api as A
from v3 import config as C
from v3 import delta_hat as DH

ORDER_TAG = "v3-order"
ORDER_RULE = 'sorted by (core.seed_of("v3-order", wf_id), wf_id)'


class OrderMismatch(ValueError):
    """A manifest's order is not the pinned rule's, or its sha256 does not match."""


class MissingPostMortem(ValueError):
    """An episode returned no post-mortem (O4: one after EVERY workflow)."""


# ---------------------------------------------------------------------------------------
# The pinned order and its manifest
# ---------------------------------------------------------------------------------------

def order_key(wf_id: str) -> tuple:
    return (core.seed_of(ORDER_TAG, wf_id), wf_id)


def workflow_order(wf_ids) -> tuple:
    ids = list(wf_ids)
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate workflow ids")
    return tuple(sorted(ids, key=order_key))


def order_sha256(order) -> str:
    return hashlib.sha256(C.canonical_json(list(order)).encode("ascii")).hexdigest()


def order_manifest(wf_ids, split: str = "dev") -> dict:
    """The manifest entry that pins the order (freeze_v3, T22, embeds it)."""
    order = list(workflow_order(wf_ids))
    return {"tag": ORDER_TAG, "rule": ORDER_RULE, "split": split, "n": len(order),
            "order": order, "sha256": order_sha256(order)}


def verify_order_manifest(man: dict) -> None:
    order = list(man.get("order", ()))
    if man.get("tag") != ORDER_TAG or man.get("rule") != ORDER_RULE:
        raise OrderMismatch(f"manifest rule {man.get('rule')!r} is not {ORDER_RULE!r}")
    if man.get("sha256") != order_sha256(order):
        raise OrderMismatch("manifest order does not match its sha256")
    if order != list(workflow_order(order)):
        raise OrderMismatch("manifest order is not the pinned rule's order")
    if man.get("n", len(order)) != len(order):
        raise OrderMismatch("manifest n does not match its order")


def write_order_manifest(path, man: dict) -> None:
    verify_order_manifest(man)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(man, sort_keys=True, indent=1) + "\n")


def load_order_manifest(path) -> dict:
    with open(path, encoding="utf-8") as f:
        man = json.load(f)
    verify_order_manifest(man)
    return man


# ---------------------------------------------------------------------------------------
# One step of a sequence
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Step:
    """What one episode is told about the workflows before it: nothing but post-mortems."""
    key: DH.HistoryKey                 # system carries the line-1 arm (DH.system_name)
    wf_id: str
    order: int
    arm: str
    postmortems: tuple
    line1: DH.Line1

    def context(self, template: A.EpisodeContext) -> A.EpisodeContext:
        """The episode's context: `template` (built for this workflow) plus the step's
        post-mortems.  The template must be of this workflow, cell and seed."""
        if template.wf_id != self.wf_id:
            raise DH.LeakError(f"context of {template.wf_id} for step {self.wf_id}")
        if C.cell_id(template.cell) != self.key.cell_id or template.seed != self.key.seed:
            raise DH.LeakError("context of another cell or seed")
        if template.postmortems:
            raise DH.LeakError("the template already carries post-mortems")
        return dataclasses.replace(template, postmortems=self.postmortems)


#: One episode: Step -> (EpisodeRecord or its dict, PostMortem).
EpisodeFn = Callable[[Step], tuple]


def postmortem_from_record(rec, alarms=()) -> A.PostMortem:
    """O4: the published post-mortem of one episode -- its true (k, iota, sigma), harm
    and the alarms raised ((t, target), ...)."""
    r = rec if isinstance(rec, dict) else rec.to_dict()
    return A.PostMortem(cell_id=r["cell_id"], wf_id=r["wf"], order=r["order"], seed=r["seed"],
                        k=tuple(r["k"] or ()), iota=r["iota"], sigma=r["sigma"],
                        harm=r["harm"], H=r["H"], alarms=tuple(tuple(a) for a in alarms))


@dataclass
class SequenceResult:
    key: DH.HistoryKey
    arm: str
    manifest_sha256: str
    records: list
    postmortems: tuple

    def curve(self) -> list:
        """(n_incidents_seen, delta_hat, harm) per workflow, in the pinned order."""
        out = []
        for rec in self.records:
            r = rec if isinstance(rec, dict) else rec.to_dict()
            out.append((r["n_incidents_seen"], r["delta_hat"], r["harm"]))
        return out


def _check_record(rec, step: Step) -> None:
    r = rec if isinstance(rec, dict) else rec.to_dict()
    want = {"cell_id": step.key.cell_id, "seed": step.key.seed, "wf": step.wf_id,
            "order": step.order, "policy": step.key.system, "attack": step.key.attack,
            "delta_hat": step.line1.delta_hat,
            "n_incidents_seen": step.line1.n_incidents_seen}
    bad = {k: (r.get(k), v) for k, v in want.items() if r.get(k) != v}
    if bad:
        raise DH.LeakError(f"record disagrees with its step (got, want): {bad}")


def _check_postmortem(pm, step: Step) -> None:
    if pm is None:
        raise MissingPostMortem(f"no post-mortem after {step.wf_id} (O4)")
    if not isinstance(pm, A.PostMortem):
        raise TypeError(f"post-mortem is {type(pm).__name__}, not api.PostMortem")
    got = (pm.cell_id, pm.seed, pm.wf_id, pm.order)
    want = (step.key.cell_id, step.key.seed, step.wf_id, step.order)
    if got != want:
        raise DH.LeakError(f"post-mortem {got} is not of step {want}")


def run_sequence(key: DH.HistoryKey, manifest: dict, run_episode: EpisodeFn, *,
                 arm: str = DH.ARM_POSTMORTEM, true_delta: Callable | None = None,
                 kappa: dict | None = None, history: DH.DeltaHatHistory | None = None,
                 ) -> SequenceResult:
    """Run every workflow of `manifest` in its pinned order under `key`.

    key         (cell_id, system, attack, seed); the system is the untagged name, the arm's
                tag is added here (DH.system_name) and is what records must carry.
    true_delta  wf_id -> true Delta; the oracle arm only.
    kappa       the cell's price table, for chi-hat.
    history     a shared DeltaHatHistory; it must not already hold this (armed) key."""
    verify_order_manifest(manifest)
    if (arm == DH.ARM_ORACLE) != (true_delta is not None):
        raise ValueError("true_delta is given to the oracle arm and to no other arm")
    armed = dataclasses.replace(key, system=DH.system_name(key.system, arm))
    history = DH.DeltaHatHistory() if history is None else history
    if history.has(armed):
        raise DH.LeakError(f"history already holds {armed}: one sequence per key")
    records = []
    for order, wf in enumerate(manifest["order"]):
        pms = history.before(armed, order)
        l1 = DH.line1(arm, pms, wf_id=wf, order=order, cell_id=key.cell_id, seed=key.seed,
                      true_delta=true_delta(wf) if true_delta else None, kappa=kappa)
        step = Step(key=armed, wf_id=wf, order=order, arm=arm, postmortems=pms, line1=l1)
        rec, pm = run_episode(step)
        _check_postmortem(pm, step)
        _check_record(rec, step)
        history.add(armed, pm)
        records.append(rec)
    return SequenceResult(key=armed, arm=arm, manifest_sha256=manifest["sha256"],
                          records=records, postmortems=history.before(armed, len(records)))
