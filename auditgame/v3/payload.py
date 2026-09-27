"""v3/payload.py -- the sleeper payload and its planner (T3; C8, O2, N3).

WHAT CHANGES FROM v2 (C8).  v2's planner (build.plan_poison_all) required the payload
to lie DORMANT: no task in [iota, sigma) may retrieve it.  The draft has no such
constraint, and Figure 1 needs the note to be used at t2 ("A skill is induced from a
trajectory that used the note"), long before the trigger.  v3 separates the two things
v2 had tied together (O2):

    RETRIEVAL   once written at iota, the payload is a shared note: EVERY task from
                iota on retrieves it while it is live (`retrieve`, `retrievable_at`).
    ACTIVATION  the payload does harm only on a task that meets its TARGET PREDICATE:
                v2's THETA rule on sigma's topic.  The payload topic is
                retrieval.payload_topic_like(topic_sigma, eps) and task t meets the
                predicate iff retrieval.retrieved(payload topic, topic_t, THETA)
                (`predicate`, `activates_at`).

sigma is the task at which the poison activates (draft S4), i.e. the FIRST task from
iota on that meets the predicate.  So the planner keeps a placement (k, iota, sigma =
iota + Delta, eps) only if sigma meets its own predicate and no task in [iota, sigma)
does (config.SLEEPER_NO_EARLY_TARGET).  The window includes iota because the runner
writes the payload before the agent runs task iota (plan T6, steps 3-4), so task iota
already reads it; for Delta = 0 that is what lets the payload fire at sigma = iota.

THE PAYLOAD IS v2's, BYTE FOR BYTE.  The marker is build.marker_for over the same
coordinates as build._spec, and the item is built by build.inject, so content, topic
and item_id -- and therefore every detector score seeded on item_id -- are v2's for
the same placement.  `SleeperPayload.spec()` is the v2 PoisonSpec.

N3.  A candidate that cannot be built is not dropped in silence: `plan_sleeper_all`
writes an `Infeasible` record with a reason into the `reasons` sink, one per candidate
sigma in [Delta, H), or one per workflow when H <= Delta.

Stdlib only; imports v2, never patches it.
"""
from __future__ import annotations

from dataclasses import dataclass

import build
import retrieval
from core import CARRIERS, CarrierStore, Item, PoisonSpec, Workflow

# ---------------------------------------------------------------------------------------
# Reasons a candidate placement cannot be built (N3)
# ---------------------------------------------------------------------------------------

#: A task in [iota, sigma) already meets the target predicate: the poison would activate
#: before sigma, so the declared Delta would not be the true one (v2's contamination bug).
EARLY_TARGET = "early-target"
#: eps buys so few of sigma's tokens that sigma itself does not meet the payload's
#: predicate (Jaccard < THETA): the payload would never activate at sigma.
SIGMA_MISSES_PREDICATE = "sigma-misses-own-predicate"
#: The workflow has no task sigma = iota + Delta with iota >= 0 (H <= Delta).
TOO_SHORT = "workflow-too-short"
REASON_CODES = (EARLY_TARGET, SIGMA_MISSES_PREDICATE, TOO_SHORT)


@dataclass(frozen=True)
class Infeasible:
    """One candidate placement that could not be built, and why (N3).  sigma / iota are
    None for the workflow-level TOO_SHORT record."""
    wf_id: str
    carrier: str
    delta: int
    epsilon: float
    iota: int | None
    sigma: int | None
    code: str                  # the first cause found (sigma's own predicate is checked first)
    reason: str                # every cause, in words
    codes: tuple = ()          # every cause's code (a candidate can fail both checks)


# ---------------------------------------------------------------------------------------
# The sleeper payload
# ---------------------------------------------------------------------------------------


def _meets(payload_topic, task_topic, theta: float | None = None) -> bool:
    th = retrieval.THETA if theta is None else theta
    return retrieval.retrieved(retrieval.as_topic(payload_topic),
                               retrieval.as_topic(task_topic), th)


@dataclass(frozen=True)
class SleeperPayload:
    """(k, iota, sigma, eps) of draft S4, as a sleeper (C8).  Evaluator-side: it names
    the poisoned carrier, so it must never reach a policy."""
    wf_id: str
    repo: str
    carrier: str               # k
    iota: int                  # the task at which it is written
    sigma: int                 # the first task from iota on that meets the predicate
    epsilon: float
    marker: str                # build.marker_for over the attack's coordinates
    topic: object              # payload topic: payload_topic_like(target_topic, eps)
    target_topic: object       # sigma's topic
    length_reason: str | None  # build.payload_length_reason: built tag-only, and why

    @property
    def delta(self) -> int:
        return self.sigma - self.iota

    def spec(self) -> PoisonSpec:
        """The v2 PoisonSpec for the same placement (equal to build._spec's)."""
        return PoisonSpec(carrier=self.carrier, iota=self.iota, sigma=self.sigma,
                          epsilon=self.epsilon, marker=self.marker)

    # --- O2: retrieval and activation are separate ---------------------------------
    def retrievable_at(self, t: int) -> bool:
        """O2: every task from iota on can retrieve the payload (while it is live)."""
        return t >= self.iota

    def predicate(self, task_topic, theta: float | None = None) -> bool:
        """The target predicate: v2's THETA rule of the payload topic on the task's."""
        return _meets(self.topic, task_topic, theta)

    def activates_at(self, t: int, task_topic) -> bool:
        """The payload activates at task t iff it is there and t meets the predicate.
        Whether the activation becomes a marked patch (adoption) is the agent's (T4)."""
        return self.retrievable_at(t) and self.predicate(task_topic)

    def activation_tasks(self, wf: Workflow) -> tuple:
        """Every task that would activate the payload if it stayed live; sigma first."""
        return tuple(t for t, task in enumerate(wf.tasks) if self.activates_at(t, task.topic))

    # --- the item ---------------------------------------------------------------------
    def item(self, wf: Workflow) -> Item:
        """The payload Item, built by v2's build.inject (same bytes, same item_id)."""
        self._check_wf(wf)
        return build.inject(CarrierStore(), wf, self.spec())

    def _check_wf(self, wf: Workflow) -> None:
        if wf.wf_id != self.wf_id:
            raise ValueError(f"sleeper planned on {self.wf_id!r}, not {wf.wf_id!r}")


def inject(store: CarrierStore, wf: Workflow, sleeper: SleeperPayload,
           length_reasons: dict | None = None) -> Item:
    """Write the payload into carrier k of `store` (the runner calls this at iota)."""
    sleeper._check_wf(wf)
    return build.inject(store, wf, sleeper.spec(), length_reasons)


def is_sleeper_root(item: Item) -> bool:
    """A payload written by the attacker: poisoned with no derivation trail.  Items the
    agent derives from it (a skill, a patch) carry derived_from and are not roots."""
    return bool(item.poisoned) and not item.derived_from


def retrieve(store: CarrierStore, task_topic) -> list:
    """O2 retrieval for one task: v2's topic join (core.CarrierStore.retrieve at THETA)
    plus every live sleeper root, which every task after iota retrieves.  Store order,
    no duplicates.  Only roots are shared notes; how derived poisoned items (a skill) are
    retrieved is the agent's (T4)."""
    want = retrieval.as_topic(task_topic)
    return [it for it in store.live()
            if is_sleeper_root(it)
            or retrieval.retrieved(retrieval.as_topic(it.topic), want, retrieval.THETA)]


# ---------------------------------------------------------------------------------------
# The planner
# ---------------------------------------------------------------------------------------


def _check_args(k: str, delta) -> None:
    if k not in CARRIERS:
        raise ValueError(f"carrier {k!r} is not one of {CARRIERS} (seed a carrier, "
                         f"not an audit target)")
    if isinstance(delta, bool) or not isinstance(delta, int) or delta < 0:
        raise ValueError(f"delta={delta!r}: the planner takes a concrete Delta >= 0; the "
                         f"'attacker' column resolves Delta before planning (T7, O5)")


def plan_sleeper_all(wf: Workflow, k: str, delta: int, epsilon: float = 0.6, *,
                     reasons: list | None = None,
                     theta: float | None = None) -> list:
    """EVERY feasible sleeper placement (k, iota, sigma = iota + Delta, eps) on `wf`, in
    increasing sigma -- the attacker's menu at this Delta and carrier (no rng: the
    best response enumerates, the scripted rules pick first / mid / last, T7).

    A candidate sigma in [Delta, H) is feasible iff sigma meets its own target predicate
    and no task in [iota, sigma) does (module docstring).  Every other candidate is
    appended to `reasons` as an Infeasible record (N3); when H <= Delta one
    workflow-level record is appended.  `theta` exists for tests only, as in v2."""
    _check_args(k, delta)
    th = retrieval.THETA if theta is None else theta
    tp = [retrieval.as_topic(t.topic) for t in wf.tasks]
    sink = reasons if reasons is not None else []
    repo = getattr(wf, "repo", "?")
    if wf.H <= delta:
        sink.append(Infeasible(wf.wf_id, k, delta, epsilon, None, None, TOO_SHORT,
                               f"H = {wf.H} <= Delta = {delta}: no task sigma = iota + "
                               f"Delta with iota >= 0", (TOO_SHORT,)))
        return []
    out = []
    for sigma in range(delta, wf.H):
        iota = sigma - delta
        target = wf.tasks[sigma].topic
        pay = retrieval.payload_topic_like(target, epsilon)
        pt = retrieval.as_topic(pay)
        causes = []
        if not retrieval.retrieved(pt, tp[sigma], th):
            causes.append((SIGMA_MISSES_PREDICATE,
                           f"sigma = {sigma} does not meet its own predicate at eps = "
                           f"{epsilon}: Jaccard {retrieval.sim(pt, tp[sigma]):.3f} < "
                           f"THETA = {th}"))
        early = [j for j in range(iota, sigma) if retrieval.retrieved(pt, tp[j], th)]
        if early:
            causes.append((EARLY_TARGET,
                           f"task {early[0]} in [iota = {iota}, sigma = {sigma}) meets the "
                           f"target predicate, so the payload would activate before sigma "
                           f"(all: {early})"))
        if causes:
            sink.append(Infeasible(wf.wf_id, k, delta, epsilon, iota, sigma, causes[0][0],
                                   "; ".join(c[1] for c in causes),
                                   tuple(c[0] for c in causes)))
            continue
        out.append(SleeperPayload(
            wf_id=wf.wf_id, repo=repo, carrier=k, iota=iota, sigma=sigma, epsilon=epsilon,
            marker=build.marker_for(repo, wf.wf_id, k, iota, sigma, delta),
            topic=pay, target_topic=target,
            length_reason=build.payload_length_reason(pay)))
    return out


def plan_sleeper_all_carriers(wf: Workflow, delta: int, epsilon: float = 0.6, *,
                              reasons: list | None = None) -> list:
    """Every feasible placement over every carrier (v2's attackers_v2.placements)."""
    return [p for k in CARRIERS
            for p in plan_sleeper_all(wf, k, delta, epsilon, reasons=reasons)]


# ---------------------------------------------------------------------------------------
# Acceptance of T3: feasible placements per Delta on dev, against P0's 4(H - Delta)
# ---------------------------------------------------------------------------------------


def feasibility_table(workflows, deltas=None, epsilon: float = 0.6) -> list:
    """One row per Delta: P0's prediction sum_wf 4 * max(0, H - Delta) (every carrier,
    every sigma in [Delta, H)), the feasible placements measured, the infeasible ones by
    reason, and the workflows with at least one feasible placement."""
    from v3 import config as C
    deltas = C.DELTAS if deltas is None else deltas
    rows = []
    for d in deltas:
        feas = n_wf = 0
        why: list = []
        for wf in workflows:
            got = plan_sleeper_all_carriers(wf, d, epsilon, reasons=why)
            feas += len(got)
            n_wf += bool(got)
        by = {c: sum(1 for r in why if r.code == c and r.sigma is not None) for c in REASON_CODES}
        rows.append(dict(delta=d, epsilon=epsilon, workflows=len(workflows),
                         workflows_feasible=n_wf,
                         predicted=sum(4 * max(0, wf.H - d) for wf in workflows),
                         feasible=feas, infeasible=sum(by.values()), by_reason=by,
                         too_short=sum(1 for r in why if r.code == TOO_SHORT) // len(CARRIERS)))
    return rows


def _main() -> int:
    import corpus_v2
    dev = corpus_v2.make_corpus_v2()
    print(f"T3 acceptance: feasible sleeper placements on dev ({len(dev)} workflows), "
          f"all 4 carriers; P0 predicts 4(H - Delta) per workflow")
    for eps in (0.3, 0.6, 1.0):
        print(f"\neps = {eps}")
        print(f"{'Delta':>5} {'predicted':>9} {'feasible':>8} {'share':>6} "
              f"{'early':>6} {'sigma-miss':>10} {'wf ok':>6} {'wf H<=D':>7}")
        for r in feasibility_table(dev, epsilon=eps):
            share = r["feasible"] / r["predicted"] if r["predicted"] else 0.0
            print(f"{r['delta']:>5} {r['predicted']:>9} {r['feasible']:>8} {share:>6.1%} "
                  f"{r['by_reason'][EARLY_TARGET]:>6} {r['by_reason'][SIGMA_MISSES_PREDICATE]:>10} "
                  f"{r['workflows_feasible']:>6} {r['too_short']:>7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
