#!/usr/bin/env python3
"""tools/v3_build_table.py -- build the line-5 table on DEV (plan T14; Q13, O12, O15, O16).

    cd auditgame
    ../.venv/bin/python tools/v3_build_table.py --sources-only --jobs 8     # key counts, 36 cells
    ../.venv/bin/python tools/v3_build_table.py --pilot --rhos 0 --deltas 4 --jobs 8
    ../.venv/bin/python tools/v3_build_table.py --tuned reference/v3_tuned.json --jobs 10  # P4
    ../.venv/bin/python tools/v3_build_table.py --tuned reference/v3_tuned.json --base-r 16 --jobs 10
        # ^ half the base draw budget at the SAME diff-SE gate (line5-r-configurable)

THREE PHASES (plan T14 "Trang thai nguon", "Gia tri")
  A. SOURCES.  In every table cell (rho, chi, detector; primary world, K_d = 2, b1) and every
     Delta-hat, every dev workflow is run with a declared BEHAVIOUR policy -- the uniform
     mixture of the 28 library members, drawn per task exactly as line 5 draws from x_t
     (x uniform over the affordable members), with line 7 (T9's particle filter, built with
     the Delta-hat) and lines 8-9 (v3/line8.py) -- once per (attacker class, source seed)
     plus once unattacked.  The cell's Delta is the Delta-hat (R4: in a fixed-Delta cell
     line 1's Delta-hat is the cell's Delta from the second workflow on).  At the start of
     every task t the raw O16 features of b_t are recorded with h = H - t.  A class whose
     rule has no feasible placement at that Delta is skipped and counted (N3).
  B. BINS.  Per table cell the four p_attack edges are the dev quantiles of every recorded
     state of that cell (v3/line5_table.py); each state gets its key (Delta-hat, h, bin);
     at most S_MAX states per key are kept, in the order of core.seed_of(PICK_TAG, key,
     state) -- deterministic, not the first ones met.
  C. VALUES.  Per filled key, R draws per (member, class) (R = --base-r, default C.TABLE_R =
     32), assigned round-robin to the key's kept states (draw r starts from state r mod S).
     Draw r: the source episode is replayed to task t (deterministic: every draw of the
     episode is keyed on its seed), a hypothesis is drawn from ITS b_t with seed_of(DRAW_TAG,
     key, r), and the SAME hypothesis is planted for every (member, class) (common random
     numbers, as T12's engine does) and rolled out by rollout.RolloutEngine (world draws
     keyed on r).  L-hat is the mean over the draws, SE = sd / sqrt(n).  A key whose CRN
     diff-SE exceeds config.TABLE_DIFF_SE_MAX (0.15) is topped up ONCE to R_MAX = 2*base_r
     (32/64 at the default; base_r = 16 -> 16/32), still over sets diff_flag (O12,
     line5-se-diff).  Because draw r is keyed on r alone, a smaller base_r uses a strict
     sub-sequence of the default draws -- same keying, same diff-SE gate, ~half the budget,
     the SAME Sentinel policy under test (this is the Monte-Carlo draw budget, not a defender
     parameter).  Empty keys fall back by O16 (v3/line5_table.resolve_fallbacks).

DECLARED CHOICES (L1; DCM T14)
  * behaviour policy = uniform mixture of the 28 members, per task, plus lines 7-9 (plan T14);
  * sources: every dev workflow x (6 attacker classes + unattacked) x SOURCE_SEEDS (v2's dev
    tuning seeds D24); episode seed = 10 * source seed + class index, so no two states of
    a key share a rollout's world draws;
  * S_MAX = 32 states per key (= R: every draw can start from its own state);
  * BT band: library.band_prop61(p0, f) with f = the belief's commit-only uninformable share
    (Prop. 6.1: below tau a BT member buys only the commit);
  * lines 8-9 in the behaviour policy and in every rollout: the tuned (tau, eta_Q) of the
    cell's rho from reference/v3_tuned.json (T18).  Without it (P2 pilot only) the
    PILOT_LINE8 placeholder (tau 0.5, eta_Q 0.1: mid-grid of T18's TAU_Q_GRID and v2's
    ETA_Q_GRID) is used and written into the table's meta;
  * particle filter: MOVE_ON_ALARM as declared (True) while the source episode runs and is
    replayed -- b_t is Sentinel's own belief -- and OFF inside rollouts (ROLLOUT_MOVE_ON_ALARM):
    a rollout's continuation belief is the member's view of the future, the move halves
    its cost (measured 2.8 -> 1.5 ms per rollout), and T9 measured it matters in ~1 of
    500 steps.

DEV ONLY (plan S6, T14 test_line5_table_is_built_on_dev_only).  Workflows come from
v3.corpus.dev_workflows() and nowhere else; `require_dev` refuses any other split with
seal.SealedSplit, and the tool never holds a seal token.

--jobs N runs phases A and C in N worker processes; the result does not depend on N
(the table's content digest is the same: test_table_build_is_deterministic).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import pathlib
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np                                               # noqa: E402

import draft_setup as D                                          # noqa: E402
from core import seed_of                                         # noqa: E402
from v3 import api as A                                          # noqa: E402
from v3 import attackers as AT                                   # noqa: E402
from v3 import belief_pf as BP                                   # noqa: E402
from v3 import config as C                                       # noqa: E402
from v3 import corpus                                            # noqa: E402
from v3 import library as LIB                                    # noqa: E402
from v3 import line5_table as T                                  # noqa: E402
from v3 import line8 as L8                                       # noqa: E402
from v3 import rollout as RO                                     # noqa: E402
from v3 import runner as RU                                      # noqa: E402
from v3 import seal                                              # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent             # auditgame/
DEV = RU.DEV
CLEAN = "unattacked"
SOURCE_SEEDS = tuple(D.TUNE_SEEDS)                                 # (1, 2), D24
S_MAX = 32
PILOT_LINE8 = (0.5, 0.1)
ROLLOUT_MOVE_ON_ALARM = False
BEHAVIOUR_TAG = "v3-table-behaviour"
PICK_TAG = "v3-table-pick"
DRAW_TAG = "v3-table-draw"
TUNED_PATH = ROOT / "reference" / "v3_tuned.json"


# ---------------------------------------------------------------------------------------
# Dev only
# ---------------------------------------------------------------------------------------


def require_dev(split: str) -> None:
    if split != DEV:
        raise seal.SealedSplit(f"tools/v3_build_table.py builds on {DEV!r} only; split "
                               f"{split!r} is refused (plan S6: the table never reads eval)")


_DEV_CACHE: list = []


def dev_workflows() -> list:
    if not _DEV_CACHE:
        _DEV_CACHE.extend(corpus.dev_workflows())
    return _DEV_CACHE


def check_dev(workflows) -> None:
    ids = {w.wf_id for w in dev_workflows()}
    bad = [w.wf_id for w in workflows if w.wf_id not in ids]
    if bad:
        raise seal.SealedSplit(f"workflows {bad[:3]} are not dev: the table is built on dev only")


# ---------------------------------------------------------------------------------------
# Table cells and settings
# ---------------------------------------------------------------------------------------


def table_cell(rho, chi=C.CHI_PRIMARY, dprime=C.DPRIME_PRIMARY) -> dict:
    c = C.Cell(rho=rho, delta=0, chi=chi, dprime=dprime)
    return {"rho": c.rho, "chi": c.chi, "dprime": c.dprime}


def cell_of(tc: dict, delta_hat: int) -> C.Cell:
    """The source episodes' cell: primary world, K_d = 2, b1, Delta = Delta-hat (O14, O15)."""
    return C.Cell(rho=tc["rho"], delta=delta_hat, chi=tc["chi"], dprime=tc["dprime"])


def tc_id(tc: dict) -> str:
    return C.table_key_id(cell_of(tc, 0))


def all_table_cells() -> list:
    return [table_cell(r, x, d) for r in C.RHO_GRID for x in C.CHI_LEVELS
            for d in C.DPRIME_LEVELS]


def headline_table_cells() -> list:
    return [table_cell(r) for r in C.RHO_GRID]


def line8_for(settings: dict, rho: float):
    tl = settings["line8"]
    if tl is None:
        return None
    tau, eta = tl[f"{float(rho):g}"]
    return L8.Line8(tau, eta)


def line8_settings(tuned_path, rhos, pilot: bool) -> tuple:
    """{rho: (tau, eta_Q)} and its provenance."""
    if tuned_path is not None:
        tuned = json.loads(pathlib.Path(tuned_path).read_text())
        if tuned.get("smoke"):
            raise ValueError(f"{tuned_path} is a smoke result; the table reads a real tuning")
        out = {}
        for r in rhos:
            blk = tuned["rho"][f"{float(r):g}"]
            if blk.get("tau") is None or blk.get("eta_q") is None:
                raise ValueError(f"{tuned_path}: tau / eta_Q of rho {r:g} not tuned "
                                 f"({blk.get('line8_reason')})")
            out[f"{float(r):g}"] = (float(blk["tau"]), float(blk["eta_q"]))
        return out, f"tuned: {tuned_path} (log sha256 {tuned.get('log_sha256')})"
    if not pilot:
        raise ValueError("the operating table needs the tuned tau / eta_Q (--tuned, T18); only "
                         "a --pilot build may use the placeholder")
    return ({f"{float(r):g}": PILOT_LINE8 for r in rhos},
            f"PILOT placeholder tau = {PILOT_LINE8[0]}, eta_Q = {PILOT_LINE8[1]} (not tuned)")


@contextlib.contextmanager
def move_on_alarm(on: bool):
    keep = BP.MOVE_ON_ALARM
    BP.MOVE_ON_ALARM = on
    try:
        yield
    finally:
        BP.MOVE_ON_ALARM = keep


# ---------------------------------------------------------------------------------------
# The behaviour policy (phase A)
# ---------------------------------------------------------------------------------------


class Behaviour(A.PolicyBase):
    """Uniform mixture of the 28 members drawn per task (line 5 with x uniform over the
    affordable members), line 7 = T9's particle filter at Delta-hat, lines 8-9."""
    name = "table-behaviour"

    def __init__(self, ctx: A.EpisodeContext, delta_hat, line8, members=None):
        super().__init__(ctx)
        self.belief = BP.make_belief(ctx, delta_hat)
        f = self.belief.uninformable_share(("commit",))
        self.band = LIB.band_prop61(self.belief.prior_p_attack(), f)
        names = LIB.MEMBERS if members is None else members
        self.members = {n: LIB.make_member(n, ctx, belief=self.belief, band=self.band)
                        for n in names}
        self.line8 = line8
        self.features: list = []           # (t, BinFeatures at the start of t)

    def act(self, t, B_t):
        self.features.append((t, self.belief.bin_features()))
        dists = [m.distribution(t) for m in self.members.values()]
        ok = [d for d in dists if all(self.ctx.kappa[k] <= B_t + 1e-9
                                      for k, p in d.items() if p > 0)]
        if not ok:
            return None
        q = {k: sum(d.get(k, 0.0) for d in ok) / len(ok) for k in C.TARGETS}
        r = random.Random(seed_of(self.ctx.rng_seed, BEHAVIOUR_TAG, t)).random()
        acc, pick = 0.0, None
        for k in C.TARGETS:
            if q[k] <= 0.0:
                continue
            acc += q[k]
            pick = k
            if r < acc:
                break
        return self.action(pick)

    def observe(self, t, obs):
        self.belief.update(t, obs)

    def quarantine(self, t):
        return None if self.line8 is None else self.line8.quarantine(t, self.belief)


def episode_seed(src_seed: int, cls_index: int) -> int:
    return 10 * src_seed + cls_index


def source_episode(wf, tc: dict, delta_hat: int, cls: str, cls_index: int, src_seed: int,
                   settings: dict):
    """The source episode (not yet run), or None when the class cannot place (N3)."""
    cell = cell_of(tc, delta_hat)
    pl = None if cls == CLEAN else AT.by_name(cls).plan(wf, delta_hat)
    if cls != CLEAN and pl is None:
        return None
    l8 = line8_for(settings, tc["rho"])
    members = settings.get("members")
    return RU.Episode(wf, pl, lambda ctx: Behaviour(ctx, delta_hat, l8, members), C.PRIMARY,
                      cell, episode_seed(src_seed, cls_index), attack=cls)


def source_classes(settings: dict) -> tuple:
    return tuple(settings["classes"]) + (CLEAN,)


# ---------------------------------------------------------------------------------------
# Worker state
# ---------------------------------------------------------------------------------------

_W: dict = {}


def _init_worker(settings: dict) -> None:
    _W["settings"] = settings
    _W["wfs"] = {w.wf_id: w for w in dev_workflows()}


def _settings() -> dict:
    return _W["settings"]


# ---------------------------------------------------------------------------------------
# Phase A: sources
# ---------------------------------------------------------------------------------------


def source_job(job: tuple) -> dict:
    """job = (tc, delta_hat, wf_ids).  Rows: (wf_id, cls_index, src_seed, t, h, p_attack,
    top carrier index, flag)."""
    tc, dh, wf_ids = job
    st = _settings()
    c0, w0 = time.process_time(), time.perf_counter()
    rows, skipped, n_ep = [], 0, 0
    with move_on_alarm(True):
        for wid in wf_ids:
            wf = _W["wfs"][wid]
            for ci, cls in enumerate(source_classes(st)):
                for s in st["source_seeds"]:
                    ep = source_episode(wf, tc, dh, cls, ci, s, st)
                    if ep is None:
                        skipped += 1
                        continue
                    ep.run()
                    n_ep += 1
                    for t, f in ep.policy.features:
                        rows.append((wid, ci, s, t, ep.H - t, float(f.p_attack),
                                     C.CARRIERS.index(f.top_carrier), int(f.delegated_high)))
    return {"tc": tc, "delta_hat": dh, "rows": rows, "skipped": skipped, "episodes": n_ep,
            "cpu": time.process_time() - c0, "wall": time.perf_counter() - w0}


def run_pool(fn, jobs: list, n_jobs: int, settings: dict, progress, label: str) -> list:
    out = [None] * len(jobs)
    t0 = time.perf_counter()
    if n_jobs <= 1:
        _init_worker(settings)
        for i, j in enumerate(jobs):
            out[i] = fn(j)
            _progress(progress, label, i + 1, len(jobs), t0)
        return out
    with ProcessPoolExecutor(n_jobs, initializer=_init_worker, initargs=(settings,)) as ex:
        futs = {ex.submit(fn, j): i for i, j in enumerate(jobs)}
        done = 0
        from concurrent.futures import as_completed
        for f in as_completed(futs):
            out[futs[f]] = f.result()
            done += 1
            _progress(progress, label, done, len(jobs), t0)
    return out


def say(msg: str) -> None:
    """print, flushed: the progress lines reach a redirected log as they happen."""
    print(msg, flush=True)


def _progress(progress, label, done, total, t0):
    if progress and (done == total or done % max(1, total // 20) == 0):
        progress(f"  {label}: {done}/{total} jobs, {time.perf_counter() - t0:.0f} s")


# ---------------------------------------------------------------------------------------
# Phase B: bins and selection
# ---------------------------------------------------------------------------------------


def select(tc: dict, results: list, s_max: int = S_MAX) -> dict:
    """results: phase-A outputs of ONE table cell.  Returns {edges, keys: {(dh, h, b):
    [state, ...]}, counts: {(dh, h, b): n states seen}}; a state is (wf_id, cls_index,
    src_seed, t)."""
    p = [r[5] for res in results for r in res["rows"]]
    edges = T.edges_of(p)
    cid = tc_id(tc)
    groups: dict = {}
    for res in results:
        dh = res["delta_hat"]
        for (wid, ci, s, t, h, pa, top, fl) in res["rows"]:
            b = T.bin_of(T.p_level(pa, edges), top, fl)
            groups.setdefault((dh, h, b), []).append((wid, ci, s, t))
    keys, counts = {}, {}
    for k in sorted(groups):
        sts = sorted(set(groups[k]), key=lambda x: (seed_of(PICK_TAG, cid, *k, *x), x))
        keys[k] = sts[:s_max]
        counts[k] = len(sts)
    return {"edges": edges, "keys": keys, "counts": counts}


# ---------------------------------------------------------------------------------------
# Phase C: values
# ---------------------------------------------------------------------------------------


def replay(tc: dict, dh: int, state: tuple):
    """The source episode replayed to the start of task t: (EpisodeState, b_t, band)."""
    wid, ci, s, t = state
    st = _settings()
    ep = source_episode(_W["wfs"][wid], tc, dh, source_classes(st)[ci], ci, s, st)
    with move_on_alarm(True):
        while ep.t < t:
            ep.step()
        snap = ep.snapshot()
    pol = snap.private["episode"].policy
    return snap, pol.belief, pol.band


def draws(tc, dh, h, b, states, r_lo, r_hi, cache, rollout_fn=None) -> dict:
    """(member, class) -> losses of draws r_lo..r_hi-1 (draw r from state r mod S)."""
    st = _settings()
    members, classes = tuple(st["members"]), tuple(st["classes"])
    cid = tc_id(tc)
    out = {(m, c): [] for m in members for c in classes}
    l8 = line8_for(st, tc["rho"])
    for r in range(r_lo, r_hi):
        j = r % len(states)
        if j not in cache:
            snap, belief, band = replay(tc, dh, states[j])
            eng = RO.RolloutEngine(band, l8, members=members, classes=classes)
            cache[j] = (snap, belief, eng, RO.observed(snap))
        snap, belief, eng, base = cache[j]
        hyp = belief.sample(1, seed_of(DRAW_TAG, cid, dh, h, b, r))[0]
        with move_on_alarm(st["rollout_move_on_alarm"]):
            for c in classes:
                if rollout_fn is not None:
                    for m in members:
                        out[(m, c)].append(rollout_fn(snap, hyp, m, c, r))
                    continue
                pep, info = eng.planted(base, hyp, c)
                for m in members:
                    out[(m, c)].append(eng.run(pep, info, m, belief, r).loss)
    return out


def _stats(losses: dict, members, classes) -> tuple:
    Lm = np.zeros((len(members), len(classes)))
    se = np.zeros_like(Lm)
    for i, m in enumerate(members):
        for j, c in enumerate(classes):
            v = np.asarray(losses[(m, c)], float)
            Lm[i, j] = v.mean()
            se[i, j] = v.std(ddof=1) / math.sqrt(len(v)) if len(v) > 1 else 0.0
    return Lm, se


def _diff_stats(losses: dict, members, classes, Lm: np.ndarray) -> tuple:
    """line5-se-diff (27/09/2026): the top-up gate.  V(m) = max_c L-hat[m, c] (the minimax
    value line 5 reads); best/second = the two smallest V by point estimate.  Each is scored
    at its OWN argmax class, over the CRN-paired per-draw losses of that (member, class) --
    v3/rollout.py and draws() share one hypothesis, one world seed and one member-
    randomisation seed across every (member, class) of a draw r, so loss_i(r) and loss_j(r)
    are paired, not independent: sd(loss_i - loss_j) is the right variance, not combining
    sd(loss_i) and sd(loss_j) as if independent.  Returns (diff_se, gap, (best, second)) with
    gap = V(second) - V(best); n < 2 (fewer than 2 members) returns diff_se = 0.0, no pair."""
    if len(members) < 2:
        return 0.0, 0.0, (-1, -1)
    V = Lm.max(axis=1)
    cidx = Lm.argmax(axis=1)
    order = np.argsort(V, kind="stable")
    best, second = int(order[0]), int(order[1])
    cb, cs = classes[int(cidx[best])], classes[int(cidx[second])]
    a = np.asarray(losses[(members[best], cb)], float)
    b = np.asarray(losses[(members[second], cs)], float)
    n = min(len(a), len(b))
    d = a[:n] - b[:n]
    diff_se = float(d.std(ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    gap = float(V[second] - V[best])
    return diff_se, gap, (best, second)


def value_job(job: tuple) -> dict:
    """job = (tc, dh, h, b, states).  L-hat, SE (secondary diagnostic), diff-SE (the top-up
    gate: line5-se-diff, 27/09/2026) and n for one key."""
    tc, dh, h, b, states = job
    st = _settings()
    members, classes = tuple(st["members"]), tuple(st["classes"])
    c0, w0 = time.process_time(), time.perf_counter()
    cache: dict = {}
    fn = st.get("rollout_fn")
    losses = draws(tc, dh, h, b, states, 0, st["r"], cache, fn)
    Lm, se = _stats(losses, members, classes)
    diff_se, diff_gap, pair = _diff_stats(losses, members, classes, Lm)
    n = st["r"]
    if diff_se > st["diff_se_max"] and st["r_max"] > st["r"]:
        more = draws(tc, dh, h, b, states, st["r"], st["r_max"], cache, fn)
        for k in losses:
            losses[k] += more[k]
        Lm, se = _stats(losses, members, classes)
        diff_se, diff_gap, pair = _diff_stats(losses, members, classes, Lm)
        n = st["r_max"]
    return {"tc": tc, "key": (dh, h, b), "L": Lm, "se": se, "n": n, "states": len(states),
            "se_flag": bool(se.max() > st["se_max"]),               # secondary, not gated
            "diff_se": diff_se, "diff_gap": diff_gap, "diff_pair": pair,
            "diff_flag": bool(diff_se > st["diff_se_max"]),
            "rollouts": n * len(members) * len(classes),
            "cpu": time.process_time() - c0, "wall": time.perf_counter() - w0}


# ---------------------------------------------------------------------------------------
# The build
# ---------------------------------------------------------------------------------------


def base_r_and_max(base_r: int) -> tuple:
    """line5-r-configurable (27/09/2026): the base draw budget and its SINGLE top-up ceiling.

    The top-up DOUBLES the base budget: R_MAX = 2 * base_r.  This preserves O12's "one
    top-up" design at any base_r and keeps R_MAX >= base_r.  base_r = C.TABLE_R (32) gives
    (32, 64) -- the declared default (plan S8 "R = 32-64"), byte-identical to before.  A
    smaller base_r (e.g. 16 -> (16, 32)) uses the first base_r keyed draws, a strict
    sub-sequence of the base_r = 32 draws (draws are keyed on r via seed_of(DRAW_TAG, ...),
    independent of base_r), and the top-up adds r = base_r.. under the UNCHANGED diff-SE
    gate (config.TABLE_DIFF_SE_MAX = 0.15).  This is only the Monte-Carlo draw budget, not a
    defender parameter: the Sentinel policy under test is unchanged."""
    base_r = int(base_r)
    if base_r < 1:
        raise ValueError(f"--base-r must be >= 1 (got {base_r})")
    return base_r, 2 * base_r


def settings_of(*, rhos, pilot: bool, tuned=None, members=None, classes=None,
                r: int = T.R, r_max: int = T.R_MAX, se_max: float = T.SE_MAX,
                diff_se_max: float = T.DIFF_SE_MAX, s_max: int = S_MAX,
                source_seeds=SOURCE_SEEDS,
                rollout_move_on_alarm: bool = ROLLOUT_MOVE_ON_ALARM, rollout_fn=None) -> dict:
    l8, l8_src = line8_settings(tuned, rhos, pilot)
    return {"members": list(LIB.MEMBERS if members is None else members),
            "classes": list(AT.attacker_classes() if classes is None else classes),
            "r": int(r), "r_max": int(r_max), "se_max": float(se_max),
            "diff_se_max": float(diff_se_max), "s_max": int(s_max),
            "source_seeds": list(source_seeds), "line8": l8, "line8_source": l8_src,
            "rollout_move_on_alarm": bool(rollout_move_on_alarm), "pilot": bool(pilot),
            "rollout_fn": rollout_fn}


def sources(tcs, deltas, workflows, settings, jobs: int, progress=say) -> dict:
    """Phase A + B.  {tc_id: select(...) + {"tc", "episodes", "skipped", "cpu"}}."""
    chunk = max(1, math.ceil(len(workflows) / 4))
    ids = [w.wf_id for w in workflows]
    todo = [(tc, dh, tuple(ids[i:i + chunk])) for tc in tcs for dh in deltas
            for i in range(0, len(ids), chunk)]
    res = run_pool(source_job, todo, jobs, settings, progress, "sources")
    out = {}
    for tc in tcs:
        mine = [x for x in res if x["tc"] == tc]
        sel = select(tc, mine, settings["s_max"])
        sel.update(tc=tc, episodes=sum(x["episodes"] for x in mine),
                   skipped=sum(x["skipped"] for x in mine),
                   cpu=sum(x["cpu"] for x in mine), wall=sum(x["wall"] for x in mine))
        out[tc_id(tc)] = sel
    return out


def build(*, tcs, deltas, workflows=None, settings: dict, jobs: int = 1, split: str = DEV,
          progress=say) -> tuple:
    """Phases A-C.  Returns (Line5Table, report dict)."""
    require_dev(split)
    workflows = dev_workflows() if workflows is None else list(workflows)
    check_dev(workflows)
    for dh in deltas:
        T.delta_pos(dh)
    t0 = time.perf_counter()
    src = sources(tcs, deltas, workflows, settings, jobs, progress)
    t_src = time.perf_counter() - t0
    vjobs = [(s["tc"], dh, h, b, sts) for cid, s in sorted(src.items())
             for (dh, h, b), sts in sorted(s["keys"].items())]
    vjobs.sort(key=lambda j: (-j[2], j[1], j[3], tc_id(j[0])))    # long rollouts first
    t1 = time.perf_counter()
    vals = run_pool(value_job, vjobs, jobs, settings, progress, "values")
    t_val = time.perf_counter() - t1
    members, classes = settings["members"], settings["classes"]
    cells, meta_cells = {}, {}
    for cid, s in sorted(src.items()):
        arr = T.empty_cell(len(members), len(classes))
        filled = np.zeros(arr["reason"].shape, bool)
        for v in vals:
            if tc_id(v["tc"]) != cid:
                continue
            dh, h, b = v["key"]
            ix = (T.delta_pos(dh), T.h_pos(h), b)
            arr["L"][ix], arr["se"][ix] = v["L"], v["se"]
            arr["n"][ix], arr["states"][ix] = v["n"], v["states"]
            arr["se_flag"][ix] = v["se_flag"]
            arr["diff_se"][ix], arr["diff_gap"][ix] = v["diff_se"], v["diff_gap"]
            arr["diff_flag"][ix] = v["diff_flag"]
            arr["diff_pair"][ix] = v["diff_pair"]
            filled[ix] = True
        arr["src"], arr["reason"] = T.resolve_fallbacks(filled, deltas)
        cells[cid] = arr
        meta_cells[cid] = {**s["tc"], "edges": list(s["edges"]), "built_deltas": list(deltas)}
    meta = {"schema": T.SCHEMA_VERSION, "split": DEV, "pilot": settings["pilot"],
            "members": list(members), "classes": list(classes), "deltas": list(T.DELTA_KEYS),
            "h_max": T.H_MAX, "n_bins": T.N_BINS, "quantiles": list(T.QUANTILES),
            "r": settings["r"], "r_max": settings["r_max"], "se_max": settings["se_max"],
            "diff_se_max": settings["diff_se_max"],
            "top_up_gate": "crn_pairwise_diff_se (line5-se-diff, 27/09/2026)",
            "s_max": settings["s_max"], "source_seeds": settings["source_seeds"],
            "workflows": [w.wf_id for w in workflows], "line8": settings["line8"],
            "line8_source": settings["line8_source"],
            "rollout_move_on_alarm": settings["rollout_move_on_alarm"],
            "move_on_alarm_sources": True, "behaviour": "uniform mixture of the members, "
            "per task, affordable only; lines 7-9", "band": "band_prop61(p0, f_commit)",
            "test_rollout_fn": settings["rollout_fn"] is not None, "cells": meta_cells}
    table = T.Line5Table(meta, cells)
    report = {"sources": {cid: {"episodes": s["episodes"], "skipped": s["skipped"],
                                "cpu_s": s["cpu"], "states": sum(s["counts"].values()),
                                "keys": len(s["keys"]), "edges": list(s["edges"])}
                          for cid, s in src.items()},
              "values": [{"tc": tc_id(v["tc"]), "delta_hat": v["key"][0], "h": v["key"][1],
                          "bin": v["key"][2], "states": v["states"], "n": v["n"],
                          "se_max": float(v["se"].max()), "se_flag": v["se_flag"],
                          "diff_se": v["diff_se"], "diff_gap": v["diff_gap"],
                          "diff_pair": v["diff_pair"], "diff_flag": v["diff_flag"],
                          "rollouts": v["rollouts"], "cpu_s": v["cpu"], "wall_s": v["wall"]}
                         for v in vals],
              "wall_s": {"sources": t_src, "values": t_val}, "jobs": jobs}
    return table, report


# ---------------------------------------------------------------------------------------
# Table vs rollout on fresh dev states (plan T14 acceptance)
# ---------------------------------------------------------------------------------------

#: The fidelity sample's source seed: not one of SOURCE_SEEDS, so no sampled state was
#: used to build the table.
FIDELITY_SEED = 3


def fidelity_states(table: T.Line5Table, tcs, deltas, n: int, settings: dict) -> list:
    """n dev states (tc, dh, state, h, features) from FIDELITY_SEED episodes, spread over
    the table's cells in seed_of order."""
    _init_worker(settings)
    cands = []
    for tc in tcs:
        for dh in deltas:
            for w in dev_workflows():
                for ci in range(len(source_classes(settings))):
                    cands.append((seed_of("v3-table-fidelity", tc_id(tc), dh, w.wf_id, ci),
                                  tc, dh, w.wf_id, ci))
    cands.sort(key=lambda x: x[0])
    out = []
    for _, tc, dh, wid, ci in cands:
        if len(out) >= n:
            break
        ep = source_episode(_W["wfs"][wid], tc, dh, source_classes(settings)[ci], ci,
                            FIDELITY_SEED, settings)
        if ep is None:
            continue
        with move_on_alarm(True):
            ep.run()
        t = seed_of("v3-table-fidelity-t", wid, ci) % ep.H
        out.append((tc, dh, (wid, ci, FIDELITY_SEED, t), ep.H - t, ep.policy.features[t][1]))
    return out


def fidelity_job(job: tuple) -> dict:
    """Rollout L-hat (R draws from the state itself) for one sampled state."""
    tc, dh, state, h, f = job
    st = _settings()
    c0 = time.process_time()
    losses = draws(tc, dh, h, -1, [state], 0, st["r"], {})
    Lm, se = _stats(losses, st["members"], st["classes"])
    return {"tc": tc, "dh": dh, "state": state, "h": h, "features": f, "L": Lm, "se": se,
            "cpu": time.process_time() - c0}


def fidelity(table: T.Line5Table, tcs, deltas, n: int, settings: dict, jobs: int,
             progress=say) -> dict:
    """Table vs rollout on n fresh dev states: per state the mean |L-hat difference|, the
    two minimax values, and the rollout loss of the table's x_t above the rollout's own
    minimax (the price line 5 pays for reading the table)."""
    from v3 import line5 as L5
    sts = fidelity_states(table, tcs, deltas, n, settings)
    res = run_pool(fidelity_job, sts, jobs, settings, progress, "fidelity")
    rows = []
    for r in res:
        key = L5.TableKey(tc_id(r["tc"]), r["dh"], r["h"], r["features"])
        m = table.lookup(key)
        Lt = np.asarray(m.L, float)
        Lr = r["L"]
        xt, vt = L5.minimax(Lt.tolist())
        xr, vr = L5.minimax(Lr.tolist())
        rows.append({"tc": tc_id(r["tc"]), "delta_hat": r["dh"], "h": r["h"],
                     "fallback": "nearest" in m.note,
                     "mean_abs_diff": float(np.abs(Lt - Lr).mean()),
                     "value_table": vt, "value_rollout": vr,
                     "regret": float(L5.mixture_value(xt, Lr.tolist()) - vr),
                     "rollout_se_max": float(r["se"].max()), "cpu_s": r["cpu"]})
    arr = lambda k: np.array([x[k] for x in rows], float)             # noqa: E731
    return {"n": len(rows), "rows": rows,
            "mean_abs_diff": float(arr("mean_abs_diff").mean()) if rows else None,
            "value_gap_mean": float((arr("value_table") - arr("value_rollout")).mean())
            if rows else None,
            "regret_mean": float(arr("regret").mean()) if rows else None,
            "regret_max": float(arr("regret").max()) if rows else None,
            "share_regret_over_flag": float((arr("regret") > C.TABLE_ROLLOUT_FLAG).mean())
            if rows else None}


# ---------------------------------------------------------------------------------------
# Extrapolation (report)
# ---------------------------------------------------------------------------------------


def cost_model(values: list) -> dict:
    """CPU seconds per rollout as a function of h (least squares a + b h over the keys)."""
    h = np.array([v["h"] for v in values], float)
    y = np.array([v["cpu_s"] / v["rollouts"] for v in values], float)
    if len(set(h)) < 2:
        return {"a": float(y.mean()), "b": 0.0}
    b, a = np.polyfit(h, y, 1)
    return {"a": float(a), "b": float(b)}


def extrapolate(counts: dict, values: list, r: int = T.R) -> dict:
    """counts: {tc_id: {(dh, h, b): n}} of every table cell (phase A on the full grid).
    CPU-hours of phase C for every filled key: the pilot's mean CPU per key at the same h
    (top-ups included; the linear cost-per-rollout fit where the pilot has no such h), and
    the R = 32-only figure (no top-up) from the per-rollout fit."""
    cm = cost_model(values)
    per_pair = len(LIB.MEMBERS) * C.N_ATTACKER_CLASSES
    by_h: dict = {}
    for v in values:
        by_h.setdefault(v["h"], []).append(v["cpu_s"])
    mean_h = {h: float(np.mean(x)) for h, x in by_h.items()}
    secs = secs32 = 0.0
    keys = 0
    for cid, ks in counts.items():
        for (dh, h, b) in ks:
            keys += 1
            per_roll = cm["a"] + cm["b"] * h
            secs32 += per_roll * per_pair * r
            secs += mean_h.get(h, per_roll * per_pair * r)
    topup = float(np.mean([v["n"] > r for v in values])) if values else 0.0
    return {"keys": keys, "cpu_hours": secs / 3600.0, "cpu_hours_r32_only": secs32 / 3600.0,
            "cost_per_rollout": cm, "topup_rate": topup,
            "mean_cpu_s_per_key_by_h": {str(h): mean_h[h] for h in sorted(mean_h)}}


# ---------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    raise TypeError(type(o))


def make_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", default=DEV, help="only 'dev' is accepted")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--pilot", action="store_true", help="P2 pilot: placeholder line 8 "
                    "allowed, writes line5_table.PILOT_PATH")
    ap.add_argument("--sources-only", action="store_true",
                    help="phases A-B only: states and filled keys per table cell")
    ap.add_argument("--rhos", type=float, nargs="+", default=list(C.RHO_GRID))
    ap.add_argument("--chis", nargs="+", default=list(C.CHI_LEVELS))
    ap.add_argument("--dprimes", type=float, nargs="+", default=list(C.DPRIME_LEVELS))
    ap.add_argument("--headline", action="store_true",
                    help="the 4 headline table cells (chi 1.33, mid detector, every rho)")
    ap.add_argument("--deltas", type=int, nargs="+", default=list(T.DELTA_KEYS))
    ap.add_argument("--tuned", type=pathlib.Path, default=None)
    ap.add_argument("--diff-se-max", type=float, default=T.DIFF_SE_MAX,
                    help="line5-se-diff (27/09/2026): top up a key once to R_MAX when the "
                         "CRN-paired diff-SE of its two closest members exceeds this (default "
                         "%(default)s; the old absolute SE stays a reported diagnostic only)")
    ap.add_argument("--base-r", type=int, default=T.R,
                    help="line5-r-configurable (27/09/2026): base Monte-Carlo draws per "
                         "(member, class) per key; the single diff-SE top-up doubles it to "
                         "R_MAX = 2*base_r (default %(default)s -> 32/64, byte-identical to "
                         "before). A smaller base_r (e.g. 16 -> 16/32) uses the first base_r "
                         "keyed draws at the SAME diff-SE gate (0.15): same precision, ~half "
                         "the draw budget. Draw budget only -- the Sentinel policy is unchanged")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--report", type=pathlib.Path, default=None)
    ap.add_argument("--fidelity", type=int, default=0, metavar="N",
                    help="no build: table vs rollout on N fresh dev states of the built table")
    ap.add_argument("--extrapolate", action="store_true",
                    help="no build: CPU-hours of phase C for every key in sources.json, at "
                         "the cost per rollout measured in the build report")
    return ap


def main(argv=None) -> int:
    a = make_parser().parse_args(argv)
    require_dev(a.split)
    if a.headline:
        a.chis, a.dprimes = [C.CHI_PRIMARY], [C.DPRIME_PRIMARY]
    tcs = [table_cell(r, x, d) for r in a.rhos for x in a.chis for d in a.dprimes]
    base_r, r_max = base_r_and_max(a.base_r)
    settings = settings_of(rhos=a.rhos, pilot=a.pilot or a.sources_only, tuned=a.tuned,
                          diff_se_max=a.diff_se_max, r=base_r, r_max=r_max)
    out = a.out or (T.PILOT_PATH if a.pilot else T.TABLE_PATH)
    rep_path = a.report or out.with_suffix(".report.json")
    if a.fidelity:
        table = T.Line5Table.load(out)
        tcs = [{k: v for k, v in m.items() if k in ("rho", "chi", "dprime")}
               for m in table.meta["cells"].values()]
        deltas = sorted({d for m in table.meta["cells"].values() for d in m["built_deltas"]})
        settings = settings_of(rhos=[tc["rho"] for tc in tcs], pilot=table.meta["pilot"],
                               tuned=a.tuned)
        fid = fidelity(table, tcs, deltas, a.fidelity, settings, a.jobs)
        p = out.with_suffix(".fidelity.json")
        p.write_text(json.dumps(fid, default=_json_default, indent=1) + "\n")
        print(f"wrote {p}: {fid['n']} states, mean |dL| {fid['mean_abs_diff']:.4f}, regret "
              f"mean {fid['regret_mean']:.4f} max {fid['regret_max']:.4f}")
        return 0
    if a.extrapolate:
        rep = json.loads(rep_path.read_text())
        srcs = json.loads((T.TABLE_DIR / "sources.json").read_text())
        counts = {cid: {(dh, h, b): n for dh, h, b, n in c["keys"]}
                  for cid, c in srcs["cells"].items()}
        ex = extrapolate(counts, rep["values"])
        head = {cid: ks for cid, ks in counts.items()
                if srcs["cells"][cid]["tc"]["chi"] == C.CHI_PRIMARY
                and srcs["cells"][cid]["tc"]["dprime"] == C.DPRIME_PRIMARY}
        ex_head = extrapolate(head, rep["values"])
        src_cpu = sum(c["cpu_s"] for c in srcs["cells"].values()) / 3600.0
        res = {"full": ex, "headline_4_cells": ex_head, "sources_cpu_hours_36_cells": src_cpu}
        p = out.with_suffix(".extrapolation.json")
        p.write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps(res, indent=1))
        return 0
    print(f"line-5 table on dev: {len(tcs)} table cells x Delta-hat {a.deltas}; "
          f"{settings['line8_source']}; jobs {a.jobs}")
    if a.sources_only:
        t0 = time.perf_counter()
        src = sources(tcs, a.deltas, dev_workflows(), settings, a.jobs)
        rep = {cid: {"tc": s["tc"], "episodes": s["episodes"], "skipped": s["skipped"],
                     "cpu_s": s["cpu"], "edges": s["edges"],
                     "keys": [[dh, h, b, n] for (dh, h, b), n in sorted(s["counts"].items())]}
               for cid, s in src.items()}
        rep_path = a.report or (T.TABLE_DIR / "sources.json")
        rep_path.parent.mkdir(parents=True, exist_ok=True)
        rep_path.write_text(json.dumps({"cells": rep, "wall_s": time.perf_counter() - t0,
                                        "jobs": a.jobs}, default=_json_default) + "\n")
        n_keys = sum(len(s["keys"]) for s in src.values())
        print(f"wrote {rep_path}: {n_keys} filled keys of "
              f"{len(tcs) * len(a.deltas) * T.H_MAX * T.N_BINS}")
        return 0
    t0 = time.perf_counter()
    table, rep = build(tcs=tcs, deltas=a.deltas, settings=settings, jobs=a.jobs)
    digest = table.save(out)
    rep.update(digest=digest, path=str(out), wall_total_s=time.perf_counter() - t0,
               summary=table.summary())
    rep_path.write_text(json.dumps(rep, default=_json_default, indent=1) + "\n")
    cpu = sum(v["cpu_s"] for v in rep["values"]) + sum(s["cpu_s"] for s in rep["sources"].values())
    print(f"wrote {out} ({digest}); report {rep_path}; CPU {cpu / 3600:.2f} h, wall "
          f"{rep['wall_total_s'] / 3600:.2f} h")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
