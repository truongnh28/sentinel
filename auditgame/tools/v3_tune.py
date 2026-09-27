#!/usr/bin/env python3
"""tools/v3_tune.py -- the v3 tuning tool, on DEV only (plan T18; C6, D5.robust, D5.5).

WHAT IS TUNED, PER rho (the defender knows rho, Assumption 2 / D20)
    tau5        B5's escalation threshold (baselines.B5RiskScore, tuned["tau5"]),
                over draft_setup.TAU5_GRID.
    sw_weights  the SW randomised baseline's weight vector (tuned["sw_weights"]), over
                carrier_policies._SW minus "commit" (= B1) and "uniform" (= B2).
    tau, eta_Q  line 8's two thresholds (Alg. 1: "if Pr[poisoned | b_t+1] > tau and
                expected harm > eta_Q then quarantine the highest-posterior carrier"),
                over TAU_Q_GRID x draft_setup.ETA_Q_GRID.  A pair is scored by the
                minimax over the library members, each run standalone with line 8 at
                that pair (the LP of v2's select_mixture: min z s.t. x.M[:, col] <= z
                for every column; D32's tie rule: among optimal mixtures the lowest FQ).

THE OBJECTIVE (C6, D5.robust).  Definition 1's L = harm + lambda_Q FQ + lambda_T clean
tasks lost (runner.loss_of), averaged per column over dev workflows x seeds; a column is
(tuning attacker, Delta) with the tuning attackers of D18 (attackers.tuning_attack_names)
at the headline Deltas {4, 8} (chi = 1.33, mid detector, K_d = 2, b1).  The worst case is
the MAX over the three kernels of config.KERNEL (nominal, low, high: zeta = 0.10 apart,
agent.KERNELS) and over the columns.  Ties at 4 decimals go to the lower FQ, then to the
earlier grid value.

ETA_Q ON THE GRID EDGE.  sentinel-v3.md (Algorithm 1 table, lines 8-9): "eta_Q duoc chon
khong nam o mep luoi, hoac phai khai".  An eta_Q at either end of the grid is kept -- the
rule is not re-run on a wider grid after seeing numbers -- and the result carries the
declaration (`edge_declaration`); `check_tuned` refuses an edge value without one.

THE SELECTION LOG.  Every candidate's measurement and every choice is one entry; the log
is written next to the output (<out>.log.jsonl) and its sha256 over the canonical JSON is
pinned in the output (`log_sha256`), so a tuned value can be traced to its evidence.

DEV ONLY (plan S6: "tools/v3_tune.py khong co duong nao toi eval").  Workflows come from
v3.corpus.dev_workflows() and nowhere else; `require_dev` refuses any other split with
seal.SealedSplit and the tool never holds a seal token.  Only members and baselines run --
never Sentinel with rollouts (GD 13).

PLUGGABLE PARTS (T9 and T12 are not merged yet).
    members         name -> build(ctx, belief) -> PolicyV3 (a library member; default: the
                    v3.library members that can run with what is given).
    belief_factory  api.BeliefFactory (the particle filter of T9 in P4).  Without one,
                    only belief-free members run and line 8 cannot run, so tau / eta_Q are
                    recorded as not tuned, with the reason.
    line8           line8(belief, tau, eta_q) -> carrier | None; default `line8_rule`, the
                    draft's sentence verbatim.  T15 / P4 pass T12's v3.line8.
StubAlarmBelief below is a SMOKE-ONLY stand-in for the particle filter (independent
per-carrier Bayes on alarms); it is not a model, and a result built with it is marked.

    cd auditgame
    ../.venv/bin/python tools/v3_tune.py --smoke --out /tmp/x/v3_tuned_smoke.json
    ../.venv/bin/python tools/v3_tune.py --real                # P4: the particle filter (T9)
                                                              # and v3.line8 (T12) ->
                                                              # reference/v3_tuned.json
    ../.venv/bin/python tools/v3_tune.py --real --nominal-only # -transition uncertainty:
                                                              # reference/v3_tuned_nominal.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import carrier_policies as CP
import draft_setup as D
from v3 import api as A
from v3 import attackers as AT
from v3 import baselines as BL
from v3 import belief_pf as PF
from v3 import config as C
from v3 import corpus
from v3 import library as LIB
from v3 import line8 as L8
from v3 import runner as R
from v3 import seal

ROOT = pathlib.Path(__file__).resolve().parent.parent              # auditgame/
TUNED_PATH = ROOT / "reference" / "v3_tuned.json"
#: The -transition uncertainty ablation's tuning (T15, sentinel.TUNED_NOMINAL_PATH): the
#: same tuning with the robust objective restricted to the nominal kernel (--nominal-only).
TUNED_NOMINAL_PATH = ROOT / "reference" / "v3_tuned_nominal.json"
NOMINAL_ONLY = ("nominal",)
DEV = R.DEV

#: The three kernels of the robust objective (D5.robust): config.KERNEL, zeta apart.
KERNELS = C.KERNEL
#: The headline Deltas the tuning columns are measured at (Table 2, C5).
TUNE_DELTAS = C.HEADLINE_DELTAS
#: v2's dev tuning seeds (D24).
TUNE_SEEDS = tuple(D.TUNE_SEEDS)
#: Line 8's Pr[poisoned] threshold tau: declared here before any v3 number (L1).  v2 had
#: no tau (its line 8 was item-level on eta_Q alone), so the grid spans (0, 1) evenly.
TAU_Q_GRID = (0.1, 0.3, 0.5, 0.7, 0.9)
#: Line 8's eta_Q grid: v2's (D11), from the naive rule 0 to above the Bayes value.
ETA_Q_GRID = tuple(D.ETA_Q_GRID)
TAU5_GRID = tuple(D.TAU5_GRID)
#: SW randomised candidates: v2's _SW minus the two that repeat another baseline.
SW_CANDIDATES = tuple(k for k in CP._SW if k not in ("commit", "uniform"))
#: Ties in the objective at this many decimals (v2's D32 rounding).
TIE_DECIMALS = 4
#: Numerical slack for "the same worst case" in the second LP (D32).
TIE_TOL = 1e-9
#: The smoke of plan T18: 1 seed, 5 dev workflows.
SMOKE_SEEDS = (1,)
SMOKE_N_WORKFLOWS = 5


# ---------------------------------------------------------------------------------------
# The seal: dev only
# ---------------------------------------------------------------------------------------


def require_dev(split: str) -> None:
    """Plan S6: the tuning tool has no road to eval.  Anything but dev is refused."""
    if split != DEV:
        raise seal.SealedSplit(f"tools/v3_tune.py tunes on {DEV!r} only; split {split!r} is "
                               f"refused (plan S6, D5.5: tuning never reads eval)")


def dev_workflows(n: int | None = None) -> list:
    """The dev workflows (v3.corpus.dev_workflows), the first n in corpus order."""
    wfs = corpus.dev_workflows()
    return wfs if n is None else wfs[:n]


# ---------------------------------------------------------------------------------------
# Line 8 (pluggable) and a smoke-only belief
# ---------------------------------------------------------------------------------------


def line8_rule(belief: A.BeliefAPI, tau: float, eta_q: float) -> str | None:
    """Alg. 1 lines 8-9: if Pr[poisoned | b_t+1] > tau and expected harm > eta_Q, the
    highest-posterior carrier (ties in config.CARRIERS order), else None."""
    if belief.p_poisoned() > tau and belief.expected_harm() > eta_q:
        mass = belief.carrier_mass()
        return max(C.CARRIERS, key=lambda k: (mass.get(k, 0.0), -C.CARRIERS.index(k)))
    return None


def line8_real(belief: A.BeliefAPI, tau: float, eta_q: float) -> str | None:
    """P4's line 8: route through T12's v3.line8 (a single source of truth) via the tool's
    (belief, tau, eta_q) callable.  `Line8.decide` READS only -- it does not condition the
    belief; MemberWithLine8.quarantine conditions it after this returns a carrier, exactly
    as it does for `line8_rule`.  The two agree on every belief: `Line8.fires` is the same
    strict pair of comparisons and `highest_posterior_carrier` the same argmax with the
    same config.CARRIERS tie order (verified on a smoke case, T18/P4)."""
    return L8.Line8(tau, eta_q).decide(belief)


def band_of(belief: A.BeliefAPI) -> LIB.Band:
    """The Prop. 6.1 band (p_floor, p0) from the belief's own prior, exactly as Sentinel
    builds it at eval (v3.sentinel.band_of; T11 contract): band_prop61(p0, f), p0 =
    prior_p_attack(), f = uninformable_share() over every target.  On the headline cells
    this is the constant (0, p0): every seeded carrier's own sweep informs its hypothesis,
    so no attack hypothesis is uninformable (f = 0), for every rho and Delta.  A BT member's
    tau is then p_floor + u (p0 - p_floor) with u a declared band position (library)."""
    return LIB.band_prop61(belief.prior_p_attack(), belief.uninformable_share())


def pf_belief_factory(ctx: A.EpisodeContext, delta_hat=None) -> A.BeliefAPI:
    """api.BeliefFactory: T9's real particle filter (v3.belief_pf.make_belief), betas at the
    pinned dev base (belief_pf.beta_base) unless ctx carries post-mortems."""
    return PF.make_belief(ctx, delta_hat)


#: The particle filter's label recorded in the tuned output's setup.belief (real mode).
PF_LABEL = (f"ParticleBelief (v3.belief_pf, N = {PF.N_PARTICLES} particles, Delta prior "
            f"{PF.DELTA_PRIOR!r} from line 1's Delta-hat)")


class StubAlarmBelief:
    """SMOKE ONLY -- not the particle filter.  Independent per-carrier Bayes on alarms:
    prior Pr[c[k] = 1] = p0 / 4; an alarm on carrier k multiplies its odds by psi / phi,
    a quiet audit that inspected items by (1 - psi) / (1 - phi), at the audit's depth.
    Expected harm = Pr[poisoned] x the share of the horizon still ahead."""

    def __init__(self, ctx: A.EpisodeContext, delta_hat=None, p0: float = 0.5):
        self.ctx, self.t = ctx, 0
        self.m = {k: p0 / len(C.CARRIERS) for k in C.CARRIERS}
        self.det = ctx.cell.detector()

    def update(self, t, obs):
        self.t = t + 1
        if obs.bought is None or not obs.scores:
            return
        k = C.CARRIER_OF_TARGET[obs.bought.target]
        d = self.det.at_depth(obs.bought.depth)
        lr = d.psi / d.phi if obs.alarm else (1 - d.psi) / (1 - d.phi)
        p = self.m[k]
        odds = p / (1 - p) * lr if p < 1 else math.inf
        self.m[k] = 1.0 if math.isinf(odds) else odds / (1 + odds)

    def condition_on_quarantine(self, t, carrier):
        self.m[carrier] = 0.0

    def p_poisoned(self):
        return 1.0 - math.prod(1.0 - v for v in self.m.values())

    def carrier_mass(self):
        return dict(self.m)

    def expected_harm(self):
        return self.p_poisoned() * max(0, self.ctx.H - self.t) / self.ctx.H

    def bin_features(self):
        top = max(C.CARRIERS, key=lambda k: self.m[k])
        dm = sum(self.m[k] for k in self.ctx.delegated)
        return A.BinFeatures(self.p_poisoned(), top, dm)

    def sample(self, n, seed):
        raise NotImplementedError("the stub belief does not sample (no rollouts in T18)")


def stub_belief_factory(ctx, delta_hat=None):
    return StubAlarmBelief(ctx, delta_hat)


class MemberWithLine8(A.PolicyBase):
    """A library member run standalone for tuning: the member chooses a_t; the shared
    belief takes o_t (line 7); line 8 at (tau, eta_Q) names the carrier to remove, and the
    belief is conditioned on it.  Without a belief, line 8 does not run."""

    def __init__(self, ctx, member, belief, tau, eta_q, line8=line8_rule):
        super().__init__(ctx)
        self.member, self.belief = member, belief
        self.tau, self.eta_q, self.line8 = tau, eta_q, line8
        self.name = member.name

    def act(self, t, B_t):
        return self.member.act(t, B_t)

    def observe(self, t, obs):
        if self.belief is not None:
            self.belief.update(t, obs)
        self.member.observe(t, obs)

    def quarantine(self, t):
        if self.belief is None or self.tau is None:
            return None
        k = self.line8(self.belief, self.tau, self.eta_q)
        if k is not None:
            self.belief.condition_on_quarantine(t, k)
            self._log.append({"t": t, "quarantine": k})
        return k

    def decision_log(self):
        return ([{"line8_tau": self.tau, "line8_eta_q": self.eta_q}]
                + self.member.decision_log() + list(self._log))


def default_members(belief_factory=None, band: LIB.Band | None = None) -> dict:
    """name -> build(ctx, belief).  Without a belief only the belief-free members (SW and
    RO with a random phase); with one, the RO-posterior members too; BT needs the band."""
    out = {}
    for n in LIB.MEMBERS:
        cls, kw = LIB.LIBRARY[n]
        reads = cls is LIB.BeliefThreshold or (cls is LIB.CarrierRotation
                                               and kw["phase"] == "posterior")
        if reads and belief_factory is None:
            continue
        if cls is LIB.BeliefThreshold and band is None:
            continue
        out[n] = (lambda nn: lambda ctx, b: LIB.make_member(nn, ctx, belief=b, band=band))(n)
    return out


# ---------------------------------------------------------------------------------------
# Measurement: mean L per (kernel, column)
# ---------------------------------------------------------------------------------------


def worlds(world: C.WorldV3 = C.PRIMARY, kernels=KERNELS) -> dict:
    """kernel -> the world that differs from `world` in the kernel only."""
    return {k: replace(world, kernel=k) for k in kernels}


def cells(rho: float, deltas=TUNE_DELTAS) -> list:
    """The headline cells at rho (Table 2, C5)."""
    return [C.Cell(rho=rho, delta=d) for d in deltas]


class Plans:
    """Placement cache: (attack, workflow, Delta, n_seeded) -> Placement or None (N3)."""

    def __init__(self):
        self._c: dict = {}
        self.infeasible: list = []

    def get(self, attack, wf, delta, world):
        key = (attack, wf.wf_id, delta, world.n_seeded)
        if key not in self._c:
            why: list = []
            self._c[key] = AT.by_name(attack).plan(wf, delta, world, why)
            self.infeasible.extend((r.attack, r.wf_id, r.delta, r.code) for r in why)
        return self._c[key]


def measure(build, rho: float, workflows, seeds, *, attacks, deltas=TUNE_DELTAS,
            world: C.WorldV3 = C.PRIMARY, split: str = DEV, plans: Plans | None = None,
            kernels=KERNELS) -> dict:
    """One policy under the three kernels: {"L": {kernel: {col: mean L}}, "fq": {kernel:
    FQ per episode}, "episodes": n, "seconds": s}.  build(ctx) -> PolicyV3."""
    require_dev(split)
    plans = plans or Plans()
    t0 = time.perf_counter()
    L, FQ, n = {}, {}, 0
    for kern, w in worlds(world, kernels).items():
        cols, fq, ne = {}, 0, 0
        for cell in cells(rho, deltas):
            for an in attacks:
                for wf in workflows:
                    pl = plans.get(an, wf, cell.delta, w)
                    if pl is None:
                        continue
                    for s in seeds:
                        rec = R.run_episode(wf, pl, build, w, cell, s, split=DEV,
                                            attack=an).record
                        if rec.split != DEV:
                            raise AssertionError("a tuning record left dev")
                        cols.setdefault(f"{an}@{cell.delta}", []).append(R.loss_of(rec))
                        fq += rec.fq
                        ne += 1
        L[kern] = {c: sum(v) / len(v) for c, v in sorted(cols.items())}
        FQ[kern] = fq / ne if ne else 0.0
        n += ne
    return {"L": L, "fq": FQ, "episodes": n, "seconds": time.perf_counter() - t0}


def worst_case(L: dict, kernels=KERNELS) -> float:
    """C6 / D5.robust: max over the three kernels and over the columns of mean L."""
    missing = [k for k in kernels if k not in L]
    if missing:
        raise ValueError(f"worst case over {kernels} needs every kernel; missing {missing}")
    vals = [v for k in kernels for v in L[k].values()]
    if not vals:
        raise ValueError("no feasible column (N3): nothing to take a worst case over")
    return max(vals)


def robust_matrix(L: dict, kernels=KERNELS) -> dict:
    """col -> max over the three kernels (the columns every kernel measured)."""
    common = set.intersection(*(set(L[k]) for k in kernels))
    return {c: max(L[k][c] for k in kernels) for c in sorted(common)}


def _r(x: float) -> float:
    return round(float(x), 12)


def choose(cands: list) -> dict:
    """cands: [{"param": p, "value": v, "fq": f}, ...] in grid order.  The lowest value at
    TIE_DECIMALS, then the lowest FQ, then the earlier grid value."""
    if not cands:
        raise ValueError("no candidate")
    return min(enumerate(cands), key=lambda ic: (round(ic[1]["value"], TIE_DECIMALS),
                                                 round(ic[1]["fq"], TIE_DECIMALS), ic[0]))[1]


def minimax(M: dict, F: dict, cap: float | None = None) -> dict:
    """min_x max_col sum_pi x_pi M[pi][col], sum x = 1, x >= 0, optionally x.F <= cap;
    then, among mixtures within TIE_TOL of that value, the lowest x.F (D32).
    M: member -> {col: robust L}; F: member -> FQ per episode."""
    from scipy.optimize import linprog
    names = sorted(M)
    cols = sorted(set.intersection(*(set(M[n]) for n in names)))
    if not names or not cols:
        raise ValueError("minimax over an empty matrix")
    P = len(names)
    A_ub = [[M[n][c] for n in names] + [-1.0] for c in cols]
    b_ub = [0.0] * len(cols)
    base = dict(A_eq=[[1.0] * P + [0.0]], b_eq=[1.0],
                bounds=[(0, None)] * P + [(None, None)], method="highs")
    cap_ok = True
    if cap is not None:
        res = linprog(c=[0.0] * P + [1.0], A_ub=A_ub + [[F[n] for n in names] + [0.0]],
                      b_ub=b_ub + [cap], **base)
        cap_ok = res.status == 0
    if cap is None or not cap_ok:
        res = linprog(c=[0.0] * P + [1.0], A_ub=A_ub, b_ub=b_ub, **base)
    z = float(res.x[-1])
    tie = linprog(c=[F[n] for n in names], A_ub=[row[:P] for row in A_ub],
                  b_ub=[z + TIE_TOL] * len(cols), A_eq=[[1.0] * P], b_eq=[1.0],
                  bounds=[(0, None)] * P, method="highs")
    xs = tie.x if tie.status == 0 else res.x[:P]
    x = {n: round(float(v), 6) for n, v in zip(names, xs) if v > 1e-6}
    return {"mixture": x, "value": z, "fq": sum(w * F[n] for n, w in x.items()),
            "cap_ok": cap_ok, "columns": len(cols)}


# ---------------------------------------------------------------------------------------
# Deterministic --jobs N: the per-candidate measurements run in worker processes
# ---------------------------------------------------------------------------------------
#
# Each per-candidate measurement -- one `measure(build, rho, ...)` call, i.e. one (step,
# rho, candidate) with its own keyed-seed episodes -- is independent and deterministic given
# its inputs (every draw goes through core.seed_of via R.run_episode / belief_pf, never a
# worker-order-dependent RNG).  So they distribute across N processes exactly as
# tools/v3_build_table.py distributes its phases (same ProcessPoolExecutor pattern; the
# result does not depend on N).
#
# DETERMINISM.  The pool computes a CONTENT-KEYED cache {measure-key -> measure result};
# results are placed back by job index, never by completion order.  The selection log and
# every choice are then assembled by re-running the ORIGINAL single-process control flow
# (tune / tune_rho) with `run` reading the cache instead of measuring -- so the log is built
# in the same canonical order, the minimax LP and `choose` (the tie rule: value at 4 dp,
# then lower FQ, then earlier grid value) run in the main process exactly as before, and the
# tuned JSON and its `log_sha256` are byte-identical to the --jobs 1 run.  Only the wall-clock
# `timing` block differs (it is not part of `log_sha256` and never was reproducible).


def _mkey(step: str, rho: float, param: dict) -> tuple:
    """The content key of one measurement: (step, rho, candidate...).  Built identically at
    enumeration time and inside `run`, so a cached result is found by content, not order."""
    r = float(rho)
    if step == "tau5":
        return ("tau5", r, param["tau5"])
    if step == "sw_weights":
        return ("sw_weights", r, param["sw_weights"])
    if step == "line8":
        return ("line8", r, param["tau"], param["eta_q"], param["member"])
    raise ValueError(f"unknown measurement step {step!r}")


def _enumerate_jobs(rhos, tau5_grid, sw_grid, tau_grid, eta_grid, members, belief_factory):
    """Every measurement `tune_rho` will ask for, in the canonical (control-flow) order:
    per rho -- tau5 candidates, sw_weights candidates, then (tau, eta, member) for line 8
    when a belief factory is given.  Each job is (key, step, rho, descriptor); the worker
    rebuilds the policy from the descriptor (never a pickled closure)."""
    jobs = []
    for rho in rhos:
        r = float(rho)
        for v in tau5_grid:
            jobs.append((_mkey("tau5", r, {"tau5": v}), "tau5", r, ("tau5", v)))
        for w in sw_grid:
            jobs.append((_mkey("sw_weights", r, {"sw_weights": w}), "sw_weights", r, ("sw", w)))
        if belief_factory is not None:
            for tau in tau_grid:
                for eta in eta_grid:
                    for name in members:
                        p = {"tau": tau, "eta_q": eta, "member": name}
                        jobs.append((_mkey("line8", r, p), "line8", r,
                                     ("line8", tau, eta, name)))
    return jobs


#: Per-worker state, set once by the pool initializer (mirrors v3_build_table._W).
_W: dict = {}


def _init_worker(settings: dict) -> None:
    _W["settings"] = settings
    by = {w.wf_id: w for w in corpus.dev_workflows()}
    _W["wfs"] = [by[i] for i in settings["wf_ids"]]


def _worker_build(desc: tuple, st: dict):
    """Reconstruct the candidate's `build(ctx) -> PolicyV3` from a picklable descriptor,
    exactly as the single-process control flow builds it in tune_rho."""
    kind = desc[0]
    if kind == "tau5":
        return BL.factory(BL.B5RiskScore.name, tuned={"tau5": desc[1]})
    if kind == "sw":
        return BL.factory(BL.StageWeightedRandomised.name, tuned={"sw_weights": desc[1]})
    if kind == "line8":
        _, tau, eta, name = desc
        bf, l8, band, dh_mode = st["belief_factory"], st["line8"], st["band"], st["delta_hat"]

        def build(ctx):
            dh = ctx.cell.delta if dh_mode == "cell" else None
            b = bf(ctx, dh)
            return MemberWithLine8(ctx, LIB.make_member(name, ctx, belief=b, band=band),
                                   b, tau, eta, l8)
        return build
    raise ValueError(f"unknown job descriptor {desc!r}")


def _measure_job(job: tuple) -> dict:
    """One measurement in a worker.  Its own Plans() cache -- placement is deterministic, so
    a per-worker cache changes nothing but avoids re-planning within the job."""
    _key, step, rho, desc = job
    st = _W["settings"]
    build = _worker_build(desc, st)
    return measure(build, rho, _W["wfs"], st["seeds"], attacks=st["attacks"],
                   deltas=st["deltas"], world=st["world"], plans=Plans(),
                   kernels=st["kernels"])


def _run_measure_pool(jobs: list, n_jobs: int, settings: dict, progress=print) -> dict:
    """Run every measurement across n_jobs processes; return {key -> measure result}.
    Results are placed by job index (not completion order), so the cache is identical for
    any n_jobs."""
    out: list = [None] * len(jobs)
    t0 = time.perf_counter()
    with ProcessPoolExecutor(n_jobs, initializer=_init_worker, initargs=(settings,)) as ex:
        futs = {ex.submit(_measure_job, jobs[i]): i for i in range(len(jobs))}
        done = 0
        for f in as_completed(futs):
            out[futs[f]] = f.result()
            done += 1
            if progress and (done == len(jobs) or done % max(1, len(jobs) // 20) == 0):
                progress(f"  measure: {done}/{len(jobs)} jobs, "
                         f"{time.perf_counter() - t0:.0f} s")
    return {jobs[i][0]: out[i] for i in range(len(jobs))}


# ---------------------------------------------------------------------------------------
# eta_Q on the grid edge
# ---------------------------------------------------------------------------------------


def edge_declaration(eta_q: float, grid=ETA_Q_GRID) -> str | None:
    """None if eta_Q lies strictly inside the grid; else the declaration the result must
    carry (sentinel-v3.md, Algorithm 1 table, lines 8-9)."""
    g = sorted(grid)
    if eta_q not in g:
        raise ValueError(f"eta_Q = {eta_q} is not on the grid {g}")
    if eta_q == g[0]:
        return (f"eta_Q = {eta_q:g} is the LOWER edge of the grid {g}: the dev objective does "
                f"not bound eta_Q from below; kept as chosen, not re-tuned on a wider grid")
    if eta_q == g[-1]:
        return (f"eta_Q = {eta_q:g} is the UPPER edge of the grid {g}: the dev objective does "
                f"not bound eta_Q from above; kept as chosen, not re-tuned on a wider grid")
    return None


def check_tuned(tuned: dict) -> None:
    """Refuse a result whose eta_Q sits on the grid edge without its declaration."""
    grid = tuned.get("grids", {}).get("eta_q", list(ETA_Q_GRID))
    for rho, blk in tuned.get("rho", {}).items():
        e = blk.get("eta_q")
        if e is None:
            if not blk.get("line8_reason"):
                raise ValueError(f"rho {rho}: eta_Q not tuned and no reason given")
            continue
        need = edge_declaration(e, grid)
        if need is not None and blk.get("eta_q_edge") != need:
            raise ValueError(f"rho {rho}: eta_Q = {e} is on the grid edge and is not declared")


# ---------------------------------------------------------------------------------------
# The selection log
# ---------------------------------------------------------------------------------------


def log_sha256(log: list) -> str:
    """sha256 over the canonical JSON of the whole log (config.canonical_json)."""
    return hashlib.sha256(C.canonical_json(log).encode("ascii")).hexdigest()


def log_lines(log: list) -> str:
    return "".join(C.canonical_json(e) + "\n" for e in log)


def _git_head() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


# ---------------------------------------------------------------------------------------
# The tuning
# ---------------------------------------------------------------------------------------


def _entry(step, rho, param, m, kernels=KERNELS) -> dict:
    return {"step": step, "rho": rho, "candidate": param,
            "worst_L": _r(worst_case(m["L"], kernels)),
            "by_kernel": {k: _r(max(m["L"][k].values())) for k in kernels if m["L"][k]},
            "fq": {k: _r(v) for k, v in m["fq"].items()}, "episodes": m["episodes"]}


def tune_rho(rho, workflows, seeds, *, attacks, members, belief_factory, line8, tau5_grid,
             sw_grid, tau_grid, eta_grid, deltas, world, fq_cap, delta_hat, log, timing,
             progress=print, kernels=KERNELS, cache=None) -> dict:
    plans = Plans()
    blk: dict = {}
    kw = dict(attacks=attacks, deltas=deltas, world=world, plans=plans, kernels=kernels)

    def run(step, param, build):
        # --jobs N: the measurement was already computed in a worker; read it by content key
        # (identical for any N).  Otherwise measure here, exactly as the single-process tool.
        if cache is not None:
            m = cache[_mkey(step, rho, param)]
        else:
            m = measure(build, rho, workflows, seeds, **kw)
        e = _entry(step, rho, param, m, kernels)
        log.append(e)
        tm = timing.setdefault(step, {"episodes": 0, "seconds": 0.0})
        tm["episodes"] += m["episodes"]
        tm["seconds"] += m["seconds"]
        return m, e

    # a. tau5 (B5)
    cands = []
    for v in tau5_grid:
        m, e = run("tau5", {"tau5": v}, BL.factory(BL.B5RiskScore.name, tuned={"tau5": v}))
        cands.append({"param": v, "value": e["worst_L"], "fq": max(m["fq"].values())})
    ch = choose(cands)
    blk["tau5"] = ch["param"]
    log.append({"step": "tau5", "rho": rho, "choice": ch["param"], "worst_L": ch["value"]})
    progress(f"rho {rho:g}  tau5 = {ch['param']}  worst L {ch['value']:.4f}")

    # b. sw_weights (SW randomised)
    cands = []
    for w in sw_grid:
        m, e = run("sw_weights", {"sw_weights": w},
                   BL.factory(BL.StageWeightedRandomised.name, tuned={"sw_weights": w}))
        cands.append({"param": w, "value": e["worst_L"], "fq": max(m["fq"].values())})
    ch = choose(cands)
    blk["sw_weights"] = ch["param"]
    log.append({"step": "sw_weights", "rho": rho, "choice": ch["param"],
                "worst_L": ch["value"]})
    progress(f"rho {rho:g}  sw_weights = {ch['param']}  worst L {ch['value']:.4f}")

    # c. (tau, eta_Q): minimax over the members, each with line 8 at the pair
    if belief_factory is None:
        blk.update(tau=None, eta_q=None, eta_q_edge=None,
                   line8_reason="no belief factory: line 8 cannot run (T9 not merged); "
                                "tau and eta_Q not tuned")
        log.append({"step": "line8", "rho": rho, "choice": None,
                    "reason": blk["line8_reason"]})
        progress(f"rho {rho:g}  tau / eta_Q: not tuned ({blk['line8_reason']})")
        return blk
    cands = []
    for tau in tau_grid:
        for eta in eta_grid:
            M, F = {}, {}
            for name, mk in members.items():
                def build(ctx, mk=mk, tau=tau, eta=eta):
                    dh = ctx.cell.delta if delta_hat == "cell" else None
                    b = belief_factory(ctx, dh)
                    return MemberWithLine8(ctx, mk(ctx, b), b, tau, eta, line8)
                m, _e = run("line8", {"tau": tau, "eta_q": eta, "member": name}, build)
                M[name] = robust_matrix(m["L"], kernels)
                F[name] = max(m["fq"].values())
            mm = minimax(M, F, fq_cap)
            log.append({"step": "line8-minimax", "rho": rho, "candidate":
                        {"tau": tau, "eta_q": eta}, "value": _r(mm["value"]),
                        "fq": _r(mm["fq"]), "mixture": mm["mixture"],
                        "cap_ok": mm["cap_ok"]})
            cands.append({"param": (tau, eta), "value": mm["value"], "fq": mm["fq"],
                          "mixture": mm["mixture"]})
    ch = choose(cands)
    tau, eta = ch["param"]
    blk.update(tau=tau, eta_q=eta, eta_q_edge=edge_declaration(eta, eta_grid),
               line8_value=_r(ch["value"]), line8_mixture=ch["mixture"])
    log.append({"step": "line8", "rho": rho, "choice": {"tau": tau, "eta_q": eta},
                "value": _r(ch["value"]), "eta_q_edge": blk["eta_q_edge"]})
    progress(f"rho {rho:g}  tau = {tau}  eta_Q = {eta}  minimax L {ch['value']:.4f}"
             + (f"  [{blk['eta_q_edge']}]" if blk["eta_q_edge"] else ""))
    return blk


def tune(*, workflows=None, seeds=TUNE_SEEDS, rhos=C.RHO_GRID, split: str = DEV,
         attacks=None, members: dict | None = None, belief_factory=None,
         band: LIB.Band | None = None, line8=line8_rule, tau5_grid=TAU5_GRID,
         sw_grid=SW_CANDIDATES, tau_grid=TAU_Q_GRID, eta_grid=ETA_Q_GRID,
         deltas=TUNE_DELTAS, world: C.WorldV3 = C.PRIMARY, fq_cap: float | None = None,
         delta_hat: str = "cell", smoke: bool = False, belief_label: str | None = None,
         progress=print, kernels=KERNELS, jobs: int = 1) -> dict:
    """The whole tuning.  Returns {"tuned": ..., "log": [...]}; tuned["log_sha256"] pins
    the log.  `delta_hat` = "cell" gives the belief the cell's Delta (v2's tuning passed
    the regime, D9b), "prior" gives None (O3's prior).  `kernels` = NOMINAL_ONLY is the
    -transition uncertainty ablation's tuning (the worst case over the nominal kernel
    only); the result records its kernels (tuned["kernels"])."""
    require_dev(split)
    kernels = tuple(kernels)
    if not kernels or any(k not in KERNELS for k in kernels):
        raise ValueError(f"kernels={kernels!r} must be a non-empty subset of {KERNELS}")
    if delta_hat not in ("cell", "prior"):
        raise ValueError(f"delta_hat={delta_hat!r}")
    workflows = dev_workflows() if workflows is None else list(workflows)
    dev_ids = {w.wf_id for w in dev_workflows()}
    if not {w.wf_id for w in workflows} <= dev_ids:
        raise seal.SealedSplit("tools/v3_tune.py was handed a workflow that is not dev")
    attacks = tuple(AT.tuning_attack_names(world) if attacks is None else attacks)
    if members is None:
        members = default_members(belief_factory, band)
    t0 = time.perf_counter()
    log: list = []
    timing: dict = {}
    out_rho = {}
    # --jobs N > 1: measure every candidate across N processes into a content-keyed cache,
    # then assemble the log and choices below by the same single-process control flow (the
    # tuned JSON and log_sha256 do not depend on N; only the wall-clock timing does).
    cache = None
    if jobs and jobs > 1:
        jobs_list = _enumerate_jobs(rhos, tuple(tau5_grid), tuple(sw_grid), tuple(tau_grid),
                                    tuple(eta_grid), members, belief_factory)
        if jobs_list:
            settings = {"wf_ids": [w.wf_id for w in workflows], "seeds": tuple(seeds),
                        "attacks": attacks, "deltas": tuple(deltas), "world": world,
                        "kernels": kernels, "belief_factory": belief_factory, "line8": line8,
                        "delta_hat": delta_hat, "band": band}
            cache = _run_measure_pool(jobs_list, jobs, settings, progress)
    for rho in rhos:
        out_rho[f"{rho:g}"] = tune_rho(
            float(rho), workflows, tuple(seeds), attacks=attacks, members=members,
            belief_factory=belief_factory, line8=line8, tau5_grid=tuple(tau5_grid),
            sw_grid=tuple(sw_grid), tau_grid=tuple(tau_grid), eta_grid=tuple(eta_grid),
            deltas=tuple(deltas), world=world, fq_cap=fq_cap, delta_hat=delta_hat, log=log,
            timing=timing, progress=progress, kernels=kernels, cache=cache)
    for tm in timing.values():
        tm["ms_per_episode"] = (1000.0 * tm["seconds"] / tm["episodes"]
                                if tm["episodes"] else None)
    tuned = {
        "split": DEV, "smoke": bool(smoke), "objective": "worst-case L over kernels "
        f"{list(kernels)} (zeta = {C.ZETA}) and tuning columns (C6, D5.robust)",
        "kernels": list(kernels),
        "grids": {"tau5": list(tau5_grid), "sw_weights": list(sw_grid),
                  "tau": list(tau_grid), "eta_q": list(eta_grid)},
        "setup": {"seeds": list(seeds), "workflows": [w.wf_id for w in workflows],
                  "deltas": list(deltas), "attacks": list(attacks),
                  "members": sorted(members) if belief_factory is not None else [],
                  "belief": belief_label if belief_factory is not None else None,
                  "line8": getattr(line8, "__module__", "?") + "." + getattr(
                      line8, "__qualname__", "?"),
                  "fq_cap": fq_cap, "delta_hat": delta_hat, "world": world.as_dict(),
                  "lambda_Q": R.LAMBDA_Q, "lambda_T": R.LAMBDA_T, "git_head": _git_head()},
        "rho": out_rho,
        "timing": {"total_seconds": time.perf_counter() - t0, "steps": timing},
        "log_sha256": log_sha256(log),
    }
    check_tuned(tuned)
    return {"tuned": tuned, "log": log}


def tuned_for(tuned: dict, rho: float) -> dict:
    """baselines.make_baseline(tuned=...) for one rho: {"tau5", "sw_weights"} and more."""
    return dict(tuned["rho"][f"{float(rho):g}"])


def write(result: dict, out: pathlib.Path) -> tuple:
    """Write <out> and <out>.log.jsonl; the log's sha256 must match the pin."""
    tuned, log = result["tuned"], result["log"]
    if tuned["smoke"] and out.resolve() in (TUNED_PATH.resolve(), TUNED_NOMINAL_PATH.resolve()):
        raise ValueError(f"a smoke result may not be written to {out}")
    kern = tuple(tuned.get("kernels", KERNELS))
    if out.resolve() == TUNED_PATH.resolve() and kern != tuple(KERNELS):
        raise ValueError(f"{TUNED_PATH.name} holds the robust tuning over {KERNELS}, not {kern}")
    if out.resolve() == TUNED_NOMINAL_PATH.resolve() and kern != NOMINAL_ONLY:
        raise ValueError(f"{TUNED_NOMINAL_PATH.name} holds the nominal-kernel-only tuning "
                         f"(--nominal-only), not kernels {kern}")
    if log_sha256(log) != tuned["log_sha256"]:
        raise AssertionError("the selection log does not match its pinned sha256")
    out.parent.mkdir(parents=True, exist_ok=True)
    lp = out.with_name(out.stem + ".log.jsonl")
    out.write_text(json.dumps(tuned, indent=2, sort_keys=True) + "\n")
    lp.write_text(log_lines(log))
    return out, lp


# ---------------------------------------------------------------------------------------
# Extrapolation of the full cost from a run's timing
# ---------------------------------------------------------------------------------------


def extrapolate(tuned: dict, *, n_workflows: int = C.DEV_N_WORKFLOWS,
                n_seeds: int = len(TUNE_SEEDS), n_rhos: int = len(C.RHO_GRID),
                n_members: int = sum(C.LIBRARY_FAMILIES.values()),
                line8_ms: float | None = None) -> dict:
    """Scale a run's episode counts to the full tuning (every dev workflow, the tuning
    seeds, every rho, the full grids, the 28 members).  line8_ms overrides the measured
    ms / episode of the line-8 step (the particle filter will cost more than the stub)."""
    st = tuned["timing"]["steps"]
    su = tuned["setup"]
    scale = (n_workflows / len(su["workflows"])) * (n_seeds / len(su["seeds"])) \
        * (n_rhos / len(tuned["rho"]))
    g = tuned["grids"]
    out = {}
    for step, tm in st.items():
        ep = tm["episodes"] * scale
        ms = tm["ms_per_episode"]
        if step == "line8":
            ep *= (len(TAU_Q_GRID) * len(ETA_Q_GRID) / (len(g["tau"]) * len(g["eta_q"]))) \
                * (n_members / max(1, len(su["members"])))
            ms = line8_ms if line8_ms is not None else ms
        elif step == "tau5":
            ep *= len(TAU5_GRID) / len(g["tau5"])
        elif step == "sw_weights":
            ep *= len(SW_CANDIDATES) / len(g["sw_weights"])
        out[step] = {"episodes": round(ep), "ms_per_episode": ms,
                     "cpu_hours": ep * (ms or 0.0) / 3.6e6}
    out["total_cpu_hours"] = sum(v["cpu_hours"] for v in out.values())
    return out


# ---------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--smoke", action="store_true",
                    help=f"plan T18's smoke: {len(SMOKE_SEEDS)} seed, "
                         f"{SMOKE_N_WORKFLOWS} dev workflows, the stub belief")
    ap.add_argument("--split", default=DEV, help="only 'dev' is accepted")
    ap.add_argument("--seeds", type=int, nargs="+")
    ap.add_argument("--n-workflows", type=int)
    ap.add_argument("--rhos", type=float, nargs="+", default=list(C.RHO_GRID))
    ap.add_argument("--belief", choices=("none", "stub", "pf"), default=None,
                    help="'stub' is smoke-only; 'pf' is P4's real particle filter (T9) with "
                         "line 8 = v3.line8 (T12); default 'stub' under --smoke, else 'none'")
    ap.add_argument("--real", action="store_true",
                    help="P4's real tuning: shorthand for --belief pf (the particle filter "
                         "and v3.line8); tunes tau / eta_Q over the full library")
    ap.add_argument("--fq-cap", type=float, default=None)
    ap.add_argument("--jobs", type=int, default=1,
                    help="worker processes for the per-candidate measurements (default 1 = "
                         "single process, exactly as before).  The tuned JSON and its "
                         "log_sha256 are identical for any N; only the wall-clock timing "
                         "differs.  A full --real run is ~104 CPU-h; --jobs 8 finishes in "
                         "~13 h on this 10-core machine.")
    ap.add_argument("--nominal-only", action="store_true",
                    help="the -transition uncertainty ablation's tuning: worst case over the "
                         f"nominal kernel only, written to {TUNED_NOMINAL_PATH.name}")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    a = ap.parse_args(argv)
    kernels = NOMINAL_ONLY if a.nominal_only else KERNELS
    if a.out is None:
        a.out = TUNED_NOMINAL_PATH if a.nominal_only else TUNED_PATH
    require_dev(a.split)
    if a.real and a.smoke:
        ap.error("--real (the particle filter) and --smoke (the stub) are exclusive")
    if a.real and a.belief in (None, "pf"):
        a.belief = "pf"
    elif a.real:
        ap.error(f"--real means --belief pf, not --belief {a.belief}")
    belief = a.belief or ("stub" if a.smoke else "none")
    if belief == "stub" and not a.smoke:
        ap.error("--belief stub is smoke-only")
    if belief == "pf" and a.smoke:
        ap.error("--belief pf is the real filter; drop --smoke (use --n-workflows for a "
                 "subsample correctness run)")
    seeds = tuple(a.seeds or (SMOKE_SEEDS if a.smoke else TUNE_SEEDS))
    n = a.n_workflows or (SMOKE_N_WORKFLOWS if a.smoke else None)
    # The three pluggable parts (T18 docstring): the belief factory, line 8, the belief label.
    if belief == "pf":
        bf, line8, belief_label = pf_belief_factory, line8_real, PF_LABEL
    elif belief == "stub":
        bf, line8, belief_label = stub_belief_factory, line8_rule, "StubAlarmBelief (smoke only)"
    else:
        bf, line8, belief_label = None, line8_rule, None
    # BT members read the Prop. 6.1 band; build it once from a representative dev belief
    # (band_of is constant over the headline cells).  Without a real belief there is no band.
    band = None
    if bf is not None and belief == "pf":
        wf0 = dev_workflows(1)[0]
        ctx0 = R.context(wf0, C.PRIMARY, C.Cell(rho=float(a.rhos[0]),
                                                delta=TUNE_DELTAS[0]), seeds[0])
        band = band_of(bf(ctx0, ctx0.cell.delta))
    res = tune(workflows=dev_workflows(n), seeds=seeds, rhos=a.rhos, belief_factory=bf,
               band=band, line8=line8, fq_cap=a.fq_cap, smoke=a.smoke,
               belief_label=belief_label, kernels=kernels, jobs=a.jobs)
    out, lp = write(res, a.out)
    t = res["tuned"]
    print(f"\nwrote {out} and {lp}; log sha256 {t['log_sha256']}")
    print(f"total {t['timing']['total_seconds']:.1f} s")
    for step, tm in t["timing"]["steps"].items():
        print(f"  {step:11} {tm['episodes']:>8} episodes  {tm['seconds']:8.1f} s  "
              f"{tm['ms_per_episode']:.3f} ms/episode")
    ex = extrapolate(t)
    print("extrapolated to the full tuning (100 dev workflows, seeds (1, 2), 4 rho, full "
          "grids, 28 members; line 8 at the measured ms/episode):")
    for step, v in ex.items():
        if step != "total_cpu_hours":
            print(f"  {step:11} {v['episodes']:>12} episodes  {v['cpu_hours']:8.2f} CPU-h")
    print(f"  total {ex['total_cpu_hours']:.2f} CPU-h")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
