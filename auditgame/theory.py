"""
theory.py -- The declared theoretical quantities: rho, zeta, and the checks on them.

Spec: Toan-canh SS3 notation table; Danh-sach-diem-can-them.md B5, B6, C4.

rho and zeta are in the notation table and appear in two of the three theoretical
results, and neither had any code. A proof with no executable consequence cannot be
contradicted by the benchmark published beside it -- the same failure mode as a
claim with no test.

Both are computed here in a deliberately SMALL way, and the limits are stated:

  rho    covering radius of the policy library, measured in AUDIT MARGINAL space.
         A policy is represented by where it actually spends, which is what the
         attacker routes around. This is a proxy: two policies with the same
         marginal but different timing are indistinguishable to it.
  zeta   total-variation distance between two transition kernels, estimated by
         sampling. Zero in the mock by construction, because the simulator IS the
         model -- so the robust bound collapses to the exact one, and saying so
         keeps that an explicit assumption rather than a silent one.
"""
from __future__ import annotations
import random

import build
import runner
from core import CARRIERS, CarrierStore, seed_of

#: Coordinates of the marginal: the four carriers plus commit.
ACTIONS = tuple(CARRIERS) + ("commit",)

#: Grid step for the simplex sweep in covering_radius(). 0.2 gives 126 points over
#: five coordinates, enough to locate the radius to about one step while staying
#: inside a gate-test budget. Stated because the answer depends on it.
SIMPLEX_STEP = 0.2


def _dist(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _simplex_points(k: int, step: float):
    """Every lattice point of the k-simplex at the given step."""
    n = int(round(1.0 / step))

    def rec(left, depth):
        if depth == k - 1:
            yield (left,)
            return
        for i in range(left + 1):
            for rest in rec(left - i, depth + 1):
                yield (i,) + rest

    for pt in rec(n, 0):
        yield tuple(v / n for v in pt)


def covering_radius(library, step: float = SIMPLEX_STEP) -> float:
    """rho = max over the simplex of the distance to the nearest library member.

    What Proposition 6 charges for using a finite library instead of the full
    policy space. Adding members can only cover the space better, so rho must never
    rise when the library grows -- if it did, this would not be a covering radius
    and the proposition would bound nothing.

    Measured on a LATTICE, not the continuum, so the value is a lower bound that
    tightens as `step` shrinks. Declared rather than hidden: the number depends on
    the grid.
    """
    if not library:
        return float("inf")
    k = len(library[0])
    return max(min(_dist(p, m) for m in library)
               for p in _simplex_points(k, step))


def audit_marginal(policy_name, wfs, det, ag, budget, seeds, setting) -> tuple:
    """Where a policy actually spends, as a distribution over ACTIONS.

    Measured by running it, not read off its declaration: a policy that CLAIMS to
    audit four carriers but always picks the cheapest has a marginal that says so.
    """
    import policies as P
    import scoring
    counts = {a: 0 for a in ACTIONS}
    for i, wf in enumerate(wfs):
        ps = build.plan_poison(wf, "memory", 2, random.Random(seed_of(wf.wf_id, 2, "memory")))
        if ps is None:
            continue
        for s in seeds:
            pol = P.make_policy(policy_name, budget, seed_of(wf.wf_id, s), setting)
            st, a2 = CarrierStore(), ag
            for t, task in enumerate(wf.tasks):
                if t == ps.iota:
                    build.inject(st, wf, ps)
                o = a2.run_task(t, task, st, seed=s, marker=ps.marker)
                sig = {}
                for c in CARRIERS:
                    items = st.live(c)
                    raw = [det.score(x, t, s) for x in items]
                    sig[c] = P.CarrierSignal(
                        p=scoring.carrier_score(raw, det.d_prime), n=len(items))
                act = pol.choose(t, sorted({x.carrier for x in o.retrieved}), sig)
                if act is None:
                    continue
                pol.charge(P.cost_of(act))
                carrier, _ = P.split_action(act.split(":")[-1] if ":" in act else act)
                if carrier in counts:
                    counts[carrier] += 1
    total = sum(counts.values())
    if not total:
        return tuple(1.0 / len(ACTIONS) for _ in ACTIONS)
    return tuple(counts[a] / total for a in ACTIONS)


def library_covering_radius(policy_names, wfs, det, ag, budget, seeds,
                            setting) -> float:
    """rho for the real library, using each policy's MEASURED audit marginal."""
    lib = [audit_marginal(n, wfs, det, ag, budget, seeds, setting)
           for n in policy_names]
    return covering_radius(lib)


def zeta_of(agent_a, agent_b, n_wf: int = 12, seeds=(1, 2), horizon: int = 8) -> float:
    """Total-variation distance between two transition kernels, estimated.

    The kernel here is "given a task, what does the carrier store look like after",
    summarised by the distribution of writes over carriers. Two identical agents
    give exactly 0, which is the mock's situation -- the simulator IS the model, so
    the robust Stackelberg bound collapses to the exact one.

    That is worth asserting rather than assuming. On real data the agent is an LLM
    and the model is a simulator, zeta stops being zero, and the robust bound starts
    doing work it currently does not do.
    """
    def kernel(ag):
        counts = {c: 0 for c in CARRIERS}
        for i in range(n_wf):
            wf = build.make_workflow(f"z-{i:03d}", "django", horizon,
                                     random.Random(seed_of("zeta", i)))
            for s in seeds:
                st = CarrierStore()
                for t, task in enumerate(wf.tasks):
                    for it in ag.run_task(t, task, st, seed=s, marker="raw_write").writes:
                        counts[it.carrier] += 1
        tot = sum(counts.values()) or 1
        return {c: counts[c] / tot for c in CARRIERS}

    ka, kb = kernel(agent_a), kernel(agent_b)
    return 0.5 * sum(abs(ka[c] - kb[c]) for c in CARRIERS)
