"""v3/exact.py -- Algorithm 1 lines 2-3: the exact minimax solve of a small game (plan T13).

Draft, Algorithm 1:  "2: if game is small (KH <= threshold) then 3: a_t <- exact minimax
solution by backward induction on the belief MDP".  Draft S7 "Game solver": "Small games
(KH <= 40 belief-state discretisation) are solved exactly by backward induction over a
discretised belief simplex."  K = 4 carriers (config.CARRIERS), so KH <= 40 <=> H <= 10.

WHAT IS SOLVED (plan T13, "minimax dang chuoi tren cay lich su, quan sat roi rac hoa").
The defender's game at one workflow, with the observation discretised to what the
defender reads off an audit: alarm / quiet.  The attacker commits BEFORE the episode to a
pure placement j = (k, iota, sigma = iota + Delta-hat) knowing the defender's committed
(randomised) policy; the defender minimises the worst-case expected loss

    L = E[harm] + lambda_Q E[false quarantines] + lambda_T E[clean tasks lost]   (Def. 1)

over EVERY observation-dependent randomised policy.  Against a finite set of pure
placements, a perfect-recall behavioural policy is represented exactly by its SEQUENCE
FORM (one realisation weight per (information set, action)), expected loss is linear in
it, and min-max is one LP (Koller-Megiddo-von Stengel).  Backward induction on the
belief MDP and this LP agree on the value; the LP is the form in which the minimax (not
Bayes) value is exact, so no belief discretisation error enters: the "discretised belief
simplex" of the draft is the finite set of beliefs the history tree reaches.

THE GAME (declared, L2 -- the abstraction the exact solve needs; the sim itself is v3's
runner).  Within task t, the runner's order (plan T6): act -> buy -> inject -> agent ->
audit -> observe -> quarantine.

    hidden state z = (c over the three sweep carriers memory/queue/skill, phase), phase in
        pre | marked-direct | marked-delegated | harm (locked at sigma, C11) | clean.
    inject      at iota the attacker writes carrier k (a sweep carrier; seeding the branch
                is not in this game's attacker set).
    agent       iota <= t < sigma: while some poisoned source is live it is retrieved (O2)
                and propagates: skill <- 1 w.p. skill induction, queue <- 1 w.p. queue
                rate (agent.kernel_of, inherit = 1).  At sigma: if a poisoned source is
                live, the patch carries the marker w.p. adoption, routed "delegated" iff a
                live poisoned source is a delegated carrier (O1, any-delegated rule).
    audit       one action per task from {none} U {(audit, target, cell depth)} that the
                remaining budget affords (hard: sum kappa <= B on EVERY path).
                sweep k:  Pr[quiet] = (1 - phi)(1 - beta_k Pr[drift item fires])
                          x (Pr[miss] of the poisoned item if c[k] = 1)
                          -- one benign object plus a transient drift event (D6), the
                          same means as observe.py.
                commit:   the patch written at t; Pr[miss] = observe.p_miss_commit
                          (rho d' on a delegated patch, d' sqrt(d) direct, A7 provenance).
    response    after an alarm the defender chooses quarantine (whole carrier of the
                audited target) or continue ("choose"; "always" = quarantine on alarm).
                A quarantine of a clean carrier is one FQ (O7); a branch quarantine loses
                the clean patches written since the last one (solve rate each, O7).
                A branch quarantine at sigma removes the marked patch before harm locks.
    close       end of task sigma: a marked patch still in the branch is harm 1 (locked).

The checkpoint is not in the tree: O8 makes its likelihood ratio 1, so it is merged.

FEASIBILITY (plan T13, declared before measuring; config.LINE23_*).  A game is solved
exactly iff KH <= 40 AND its tree has <= 10^6 sequences AND build + LP finish in <= 60 s.
Otherwise `line23` returns an InfeasibleRecord (sequence count, decision nodes, runtime,
memory) and logs `line23: infeasible, states=..., runtime=...`; Sentinel then runs line 5
(L2).  The sequence count is exact and computed before anything is built, so a refused
game costs milliseconds.  docs/reports/v3-p2-line23.md holds the measured frontier.

Used by: Sentinel (T15) through `line23(ctx, delta_hat)`; the small-games port (T21)
through `build_tree` / `solve_tree` / `evaluate`.  The 28-member library is T11's: until
it lands, `STAND_INS` are declared stand-ins (B1, uniform, insertion, rotation, stationary
mixes) used only by tests.

numpy / scipy (HiGHS) here; the world core stays stdlib.
"""
from __future__ import annotations

import argparse
import itertools
import json
import logging
import math
import random
import resource
import sys
import time
from dataclasses import dataclass, field, asdict

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

import metrics as M2
from core import seed_of

from v3 import api as A
from v3 import config as C
from v3 import observe as O

LOG = logging.getLogger("v3.line23")

#: K of "KH <= threshold": the draft's number of carriers.
K_CARRIERS = len(C.CARRIERS)
THRESHOLD_KH = C.LINE23_KH_THRESHOLD
MAX_SEQUENCES = C.LINE23_MAX_SEQUENCES
MAX_SECONDS = C.LINE23_MAX_SECONDS

PHASES = ("pre", "marked-direct", "marked-delegated", "harm", "clean")
_PRE, _MD, _MG, _HARM, _CLEAN = range(5)
NONE = "none"
QUARANTINE, CONTINUE = "quarantine", "continue"
RESPOND = ("choose", "always")
#: The hidden sweep carriers of the v3 game (draft_setup.SWEEP_CARRIERS order).
HIDDEN_V3 = tuple(t for t in C.TARGETS if t != "commit")

#: The worlds the exact game models.  Anything else goes to line 5 with a reason.
SUPPORTED = {"audit_reading": ("carrier",), "harm": ("locked",), "ingress_visible": (True,),
             "drift": ("transient",), "n_seeded": (1,)}


# ---------------------------------------------------------------------------------------
# The game
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Game:
    """A finite audit game over a history tree (module docstring).

    hidden      carriers poison can live in (bits of z).
    targets     auditable targets: hidden carriers and/or "commit" (the branch's patch).
    seedable    carriers the attacker may seed.
    deltas      trigger delays the attacker may use (line 3 uses (Delta-hat,)).
    q_clean / q_poison  per sweep target: Pr[quiet | clean carrier], Pr[quiet | poisoned].
    q_commit    Pr[quiet] of the commit review per phase name ("pre", "marked-direct", ...).
    p_skill / p_queue / adoption   the declared kernel (agent.kernel_of).
    activate_after_audit   True = the payload fires at the END of task sigma, so an audit
                at sigma still removes it (smallgame's window {iota..iota+Delta});
                False = the agent at sigma runs before the audit (v3, plan T6 order).
    """
    H: int
    hidden: tuple
    targets: tuple
    seedable: tuple
    deltas: tuple
    budget: float
    cost: dict
    q_clean: dict
    q_poison: dict
    q_commit: dict
    delegated: tuple = ()
    p_skill: float = 0.0
    p_queue: float = 0.0
    adoption: float = 1.0
    solve_rate: float = 0.0
    lam_q: float = 0.0
    lam_t: float = 0.0
    respond: str = "choose"
    activate_after_audit: bool = False
    name: str = ""

    def __post_init__(self):
        if self.respond not in RESPOND:
            raise ValueError(f"respond={self.respond!r} is not one of {RESPOND}")
        for t in self.targets:
            if t != "commit" and t not in self.hidden:
                raise ValueError(f"target {t!r} is not a hidden carrier")
        if any(k not in self.hidden for k in self.seedable):
            raise ValueError("a seedable carrier is not hidden")

    @property
    def K(self) -> int:
        """Auditable carriers: the K of KH for this game."""
        return len(self.targets)

    def strategies(self) -> list:
        """The attacker's pure placements (k, iota, sigma)."""
        return [(k, i, i + d) for d in self.deltas for k in self.seedable
                for i in range(self.H - d) if d >= 0]

    def describe(self) -> dict:
        d = asdict(self)
        d["K"] = self.K
        return d


def v3_game(ctx: A.EpisodeContext, delta_hat: int, *, respond: str = "choose",
            targets: tuple | None = None, kernel: dict | None = None) -> Game:
    """The line-3 game of one episode: the cell's depths, prices, detector, rho,
    delegated set and budget, the world's kernel, Definition 1's lambdas (v2 metrics)."""
    unsupported = world_unsupported(ctx.world)
    if unsupported:
        raise ValueError(f"the exact game does not model {unsupported}")
    cell = ctx.cell
    det = cell.detector()
    dprime, tau, phi = det.d_prime, det.tau_det, det.phi
    if kernel is None:
        from v3 import agent as AG            # merged (T4); only its declared kernel is read
        kernel = AG.kernel_of(ctx.world)
    beta = kernel["drift"]
    targets = tuple(C.TARGETS) if targets is None else tuple(targets)
    q_clean, q_poison = {}, {}
    for k in HIDDEN_V3:
        d = ctx.depths[k]
        dp = O.sweep_dprime(dprime, d)
        p_drift_fires = O.p_alarm(O.item_mean(False, True, dp), tau)
        q_clean[k] = (1.0 - phi) * (1.0 - beta.get(k, 0.0) * p_drift_fires)
        q_poison[k] = q_clean[k] * O.p_miss(O.item_mean(True, False, dp), tau)
    prov = dprime if ctx.world.provenance == "A7" else None
    dc = ctx.depths["commit"]
    q_commit = {
        "pre": (1.0 - phi) ** (2 if prov is not None else 1),
        "marked-direct": O.p_miss_commit(cell.rho, dprime, phi, via="direct", depth=dc,
                                         dprime_provenance=prov),
        "marked-delegated": O.p_miss_commit(cell.rho, dprime, phi, via="delegated", depth=dc,
                                            dprime_provenance=prov),
    }
    q_commit["harm"] = q_commit["clean"] = q_commit["pre"]
    return Game(H=ctx.H, hidden=HIDDEN_V3, targets=targets, seedable=HIDDEN_V3,
                deltas=(int(delta_hat),), budget=float(ctx.budget),
                cost={t: float(ctx.kappa[t]) for t in targets},
                q_clean=q_clean, q_poison=q_poison, q_commit=q_commit,
                delegated=tuple(ctx.delegated),
                p_skill=kernel["skill_induction"] * kernel["skill_inherits"],
                p_queue=kernel["queue"] * kernel["queue_inherits"],
                adoption=kernel["adoption"], solve_rate=kernel["solve"],
                lam_q=M2.LAMBDA_Q, lam_t=M2.LAMBDA_T, respond=respond,
                activate_after_audit=False, name=f"v3:{C.cell_id(cell)}:H{ctx.H}")


def coverage_game(H: int, K: int, delta: int, m: int) -> Game:
    """smallgame.py's game in this solver's terms: K sweep carriers, perfect detection
    (psi = 1, phi = 0), no propagation, no commit, unit prices and budget m, window
    {iota..iota+delta} (the payload fires at the END of task sigma), harm 1 if not caught."""
    hidden = tuple(f"c{k}" for k in range(K))
    return Game(H=H, hidden=hidden, targets=hidden, seedable=hidden, deltas=(delta,),
                budget=float(m), cost={k: 1.0 for k in hidden},
                q_clean={k: 1.0 for k in hidden}, q_poison={k: 0.0 for k in hidden},
                q_commit={p: 1.0 for p in PHASES}, adoption=1.0, respond="always",
                activate_after_audit=True, name=f"coverage:H{H}K{K}d{delta}m{m}")


def world_unsupported(world: C.WorldV3) -> str:
    """'' if the exact game models `world`, else the switches it does not."""
    bad = [f"{k}={getattr(world, k)!r}" for k, ok in SUPPORTED.items()
           if getattr(world, k) not in ok]
    return ", ".join(bad)


# ---------------------------------------------------------------------------------------
# Counting (before anything is built)
# ---------------------------------------------------------------------------------------

def count_tree(game: Game) -> dict:
    """Exact sequence and decision-node counts of the full tree (no pruning), by a DP over
    the spent budget.  This is the "states" the feasibility rule reads."""
    spent = {0.0: 1}
    n_seq = n_dec = n_audit_nodes = 0
    for _t in range(game.H):
        nxt: dict = {}
        for s, cnt in spent.items():
            n_dec += cnt
            n_audit_nodes += cnt
            n_seq += cnt                                     # none
            nxt[s] = nxt.get(s, 0) + cnt
            for a in game.targets:
                c = game.cost[a]
                if s + c > game.budget + 1e-9:
                    continue
                s2 = round(s + c, 9)
                n_seq += cnt
                if game.respond == "choose":
                    n_dec += cnt                             # the response node
                    n_seq += 2 * cnt
                    nxt[s2] = nxt.get(s2, 0) + 3 * cnt       # quiet, quarantine, continue
                else:
                    nxt[s2] = nxt.get(s2, 0) + 2 * cnt       # quiet, alarm
        spent = nxt
    return {"sequences": n_seq, "decision_nodes": n_dec, "audit_nodes": n_audit_nodes,
            "leaves": sum(spent.values())}


# ---------------------------------------------------------------------------------------
# Hidden-state machinery
# ---------------------------------------------------------------------------------------

class _Model:
    """The game's transitions as dense matrices over z (J x Z x Z per task)."""

    def __init__(self, game: Game):
        self.g = game
        self.nb = len(game.hidden)
        self.Z = (1 << self.nb) * len(PHASES)
        self.J = game.strategies()
        self.idx = {k: i for i, k in enumerate(game.hidden)}
        g, Z = game, self.Z
        self.phase = np.array([z >> self.nb for z in range(Z)])
        self.bits = np.array([z & ((1 << self.nb) - 1) for z in range(Z)])
        # Pr[alarm | z] and the quarantine map per target
        self.p_alarm, self.qmat, self.fq = {}, {}, {}
        for a in g.targets:
            pa = np.zeros(Z)
            qm = np.zeros((Z, Z))
            fq = np.zeros(Z)
            for z in range(Z):
                ph, b = z >> self.nb, z & ((1 << self.nb) - 1)
                if a == "commit":
                    pa[z] = 1.0 - g.q_commit[PHASES[ph]]
                    if ph in (_MD, _MG):
                        qm[z, self._z(b, _CLEAN)] = 1.0     # the marked patch is removed
                    else:
                        qm[z, z] = 1.0
                        if ph != _HARM:
                            fq[z] = g.lam_q                  # clean branch removed
                else:
                    i = self.idx[a]
                    on = (b >> i) & 1
                    pa[z] = 1.0 - (g.q_poison[a] if on else g.q_clean[a])
                    qm[z, self._z(b & ~(1 << i), ph)] = 1.0
                    if not on:
                        fq[z] = g.lam_q
            self.p_alarm[a], self.qmat[a], self.fq[a] = pa, qm, fq
        self.harm = np.isin(self.phase, (_MD, _MG)).astype(float)
        self.marked = self.harm.copy()
        lock = np.zeros((Z, Z))
        for z in range(Z):
            ph, b = z >> self.nb, z & ((1 << self.nb) - 1)
            lock[z, self._z(b, _HARM) if ph in (_MD, _MG) else z] = 1.0
        self.lock = lock
        self.pre = [self._task_matrix(t, before_audit=True) for t in range(g.H)]
        self.post = [self._task_matrix(t, before_audit=False) for t in range(g.H)]
        self.post_identity = [all(np.array_equal(m, np.eye(Z)) for m in self.post[t])
                              if self.J else True for t in range(g.H)]
        self.z0 = self._z(0, _PRE)

    def _z(self, bits: int, phase: int) -> int:
        return (phase << self.nb) | bits

    def _activate(self, dist: dict) -> dict:
        g, out = self.g, {}
        for (b, ph), p in dist.items():
            if ph != _PRE:
                out[(b, ph)] = out.get((b, ph), 0.0) + p
                continue
            live = [k for k in g.hidden if (b >> self.idx[k]) & 1]
            if not live:
                out[(b, _CLEAN)] = out.get((b, _CLEAN), 0.0) + p
                continue
            via = _MG if any(k in g.delegated for k in live) else _MD
            out[(b, via)] = out.get((b, via), 0.0) + p * g.adoption
            if g.adoption < 1.0:
                out[(b, _CLEAN)] = out.get((b, _CLEAN), 0.0) + p * (1.0 - g.adoption)
        return out

    def _propagate(self, dist: dict) -> dict:
        g = self.g
        out: dict = {}
        for (b, ph), p in dist.items():
            if not b:
                out[(b, ph)] = out.get((b, ph), 0.0) + p
                continue
            branches = [(b, 1.0)]
            for k, pk in (("skill", g.p_skill), ("queue", g.p_queue)):
                if k not in self.idx or pk <= 0.0:
                    continue
                bit = 1 << self.idx[k]
                nb = []
                for bb, q in branches:
                    if bb & bit:
                        nb.append((bb, q))
                    else:
                        nb += [(bb | bit, q * pk), (bb, q * (1.0 - pk))]
                branches = nb
            for bb, q in branches:
                out[(bb, ph)] = out.get((bb, ph), 0.0) + p * q
        return out

    def _task_matrix(self, t: int, before_audit: bool) -> np.ndarray:
        g, Z = self.g, self.Z
        mats = np.zeros((len(self.J), Z, Z))
        for j, (k, iota, sigma) in enumerate(self.J):
            for z in range(Z):
                dist = {(z & ((1 << self.nb) - 1), z >> self.nb): 1.0}
                if before_audit:
                    if t == iota:
                        (b, ph), = dist
                        dist = {(b | (1 << self.idx[k]), ph): 1.0}
                    if iota <= t < sigma:
                        dist = self._propagate(dist)
                    if t == sigma and not g.activate_after_audit:
                        dist = self._activate(dist)
                elif t == sigma and g.activate_after_audit:
                    dist = self._activate(dist)
                for (b, ph), p in dist.items():
                    mats[j, z, self._z(b, ph)] += p
        return mats


# ---------------------------------------------------------------------------------------
# The tree
# ---------------------------------------------------------------------------------------

class Budget(Exception):
    """Raised inside the build when the declared wall-clock cap is passed."""


@dataclass
class Tree:
    """The defender's history tree in sequence form.

    Decision nodes are numbered in creation order (parents first).  For node d:
    node_t[d], node_kind[d] ("audit" | "response"), node_parent_seq[d] (-1 at the root),
    node_seqs[d] (its sequence ids), node_labels[d] (the matching action labels).
    seq_cost[s, j] is the expected loss sequence s adds against placement j, weighted by
    nature's probability of reaching it; so L_j(r) = seq_cost[:, j] . r exactly.
    child[(d, label, outcome)] is the decision node that follows (outcome "-" when the
    action has no observation: none, or a response)."""
    game: Game
    strategies: list
    node_t: list
    node_kind: list
    node_parent_seq: list
    node_seqs: list
    node_labels: list
    seq_cost: np.ndarray
    child: dict
    build_seconds: float
    counts: dict = field(default_factory=dict)

    @property
    def n_sequences(self) -> int:
        return int(self.seq_cost.shape[0])

    @property
    def n_nodes(self) -> int:
        return len(self.node_t)


def build_tree(game: Game, *, deadline: float | None = None, keep_children: bool = True) -> Tree:
    """Forward pass over the history tree, level by level, vectorised over nodes and
    placements.  W has shape (J, N, Z): the joint probability of the observation history
    and the hidden state, per placement."""
    t0 = time.perf_counter()
    m = _Model(game)
    J, Z = len(m.J), m.Z
    node_t, node_kind, node_parent_seq, node_seqs, node_labels = [], [], [], [], []
    child: dict = {}
    costs: list = []
    n_seq = 0

    def new_nodes(n, t, kind, parent_seqs):
        start = len(node_t)
        node_t.extend([t] * n)
        node_kind.extend([kind] * n)
        node_parent_seq.extend(int(p) for p in parent_seqs)
        node_seqs.extend([] for _ in range(n))
        node_labels.extend([] for _ in range(n))
        return np.arange(start, start + n)

    def add_seqs(nodes, label, cost_nj):
        nonlocal n_seq
        ids = np.arange(n_seq, n_seq + len(nodes))
        n_seq += len(nodes)
        for d, s in zip(nodes.tolist(), ids.tolist()):
            node_seqs[d].append(s)
            node_labels[d].append(label)
        costs.append(np.ascontiguousarray(cost_nj.T) if J else np.zeros((len(nodes), 0)))
        return ids

    def check_time():
        if deadline is not None and time.perf_counter() > deadline:
            raise Budget()

    # the root
    W = np.zeros((J, 1, Z))
    W[:, 0, m.z0] = 1.0
    spent = np.zeros(1)
    lastbq = np.full(1, -1)
    nodes = new_nodes(1, 0, "audit", [-1])
    for t in range(game.H):
        check_time()
        W = np.matmul(W, m.pre[t]) if J else W
        last = t == game.H - 1
        kids = []                                 # (W, spent, lastbq, parent_seq, (node, label, outcome))

        def close(Wb):
            """End of task t: activation after the audit (coverage game), then harm locks."""
            if J and not m.post_identity[t]:
                Wb = np.matmul(Wb, m.post[t])
            loss = (Wb * m.harm).sum(-1)
            return np.matmul(Wb, m.lock), loss

        def quarantine(Wb, a, lb):
            """Remove the carrier of target a: FQ, the branch's clean patches, the map."""
            loss = (Wb * m.fq[a]).sum(-1)
            if a == "commit":
                n_tasks = (t - lb).astype(float)[None, :]
                loss = loss + game.lam_t * game.solve_rate * (
                    n_tasks * Wb.sum(-1) - (Wb * m.marked).sum(-1))
            return np.matmul(Wb, m.qmat[a]), loss

        # none
        Wc, loss = close(W)
        seq = add_seqs(nodes, NONE, loss)
        kids.append((Wc, spent, lastbq, seq, nodes, NONE, "-"))
        for a in game.targets:
            check_time()
            ok = spent + game.cost[a] <= game.budget + 1e-9
            if not ok.any():
                continue
            sub = nodes[ok]
            Ws, sp, lb = W[:, ok, :], spent[ok] + game.cost[a], lastbq[ok]
            Wq = Ws * (1.0 - m.p_alarm[a])
            Wa = Ws * m.p_alarm[a]
            Wq_c, loss_q = close(Wq)
            if game.respond == "always":
                Wr, loss_r = quarantine(Wa, a, lb)
                Wr_c, loss_rc = close(Wr)
                seq = add_seqs(sub, a, loss_q + loss_r + loss_rc)
                kids.append((Wq_c, sp, lb, seq, sub, a, "quiet"))
                lb2 = np.full_like(lb, t) if a == "commit" else lb
                kids.append((Wr_c, sp, lb2, seq, sub, a, "alarm"))
            else:
                seq = add_seqs(sub, a, loss_q)
                kids.append((Wq_c, sp, lb, seq, sub, a, "quiet"))
                resp = new_nodes(len(sub), t, "response", seq)
                if keep_children:
                    for d, r in zip(sub.tolist(), resp.tolist()):
                        child[(d, a, "alarm")] = r
                Wr, loss_r = quarantine(Wa, a, lb)
                Wr_c, loss_rc = close(Wr)
                s_q = add_seqs(resp, QUARANTINE, loss_r + loss_rc)
                lb2 = np.full_like(lb, t) if a == "commit" else lb
                kids.append((Wr_c, sp, lb2, s_q, resp, QUARANTINE, "-"))
                Wn_c, loss_n = close(Wa)
                s_c = add_seqs(resp, CONTINUE, loss_n)
                kids.append((Wn_c, sp, lb, s_c, resp, CONTINUE, "-"))
        if last:
            break
        # next level: every child is a decision node of task t + 1 (zero-mass ones dropped)
        Ws_, sps, lbs, pars, keys = [], [], [], [], []
        for Wk, sp, lb, seq, src, label, outcome in kids:
            mass = Wk.sum(axis=(0, 2)) if J else np.ones(Wk.shape[1])
            keep = mass > 0.0
            Ws_.append(Wk[:, keep, :])
            sps.append(sp[keep]); lbs.append(lb[keep]); pars.append(seq[keep])
            keys.append((src[keep], label, outcome))
        W = np.concatenate(Ws_, axis=1)
        spent = np.concatenate(sps)
        lastbq = np.concatenate(lbs)
        par = np.concatenate(pars)
        nodes = new_nodes(len(par), t + 1, "audit", par)
        if keep_children:
            pos = 0
            for src, label, outcome in keys:
                for d in src.tolist():
                    child[(d, label, outcome)] = int(nodes[pos])
                    pos += 1
    cost = np.vstack(costs) if costs else np.zeros((0, J))
    return Tree(game=game, strategies=m.J, node_t=node_t, node_kind=node_kind,
                node_parent_seq=node_parent_seq, node_seqs=node_seqs,
                node_labels=node_labels, seq_cost=cost, child=child,
                build_seconds=time.perf_counter() - t0, counts=count_tree(game))


# ---------------------------------------------------------------------------------------
# Solve and evaluate
# ---------------------------------------------------------------------------------------

@dataclass
class Solution:
    value: float                  # min over policies of max over placements of L
    r: np.ndarray                 # realisation weights per sequence
    per_strategy: np.ndarray      # L_j at the optimum
    lp_seconds: float
    status: str

    def behaviour(self, tree: Tree, d: int) -> dict:
        """The defender's action distribution at decision node d (the published x_t)."""
        seqs, labels = tree.node_seqs[d], tree.node_labels[d]
        w = np.clip(self.r[seqs], 0.0, None)
        tot = w.sum()
        if tot <= 1e-12:              # unreachable under the plan: the passive action
            return {lab: float(lab in (NONE, CONTINUE)) for lab in labels}
        return {lab: float(x / tot) for lab, x in zip(labels, w)}


def _flow_matrix(tree: Tree):
    """Sequence-form constraints: sum_a r(d, a) = r(parent seq of d), = 1 at the root."""
    rows, cols, vals = [], [], []
    for d, seqs in enumerate(tree.node_seqs):
        rows += [d] * len(seqs); cols += seqs; vals += [1.0] * len(seqs)
        p = tree.node_parent_seq[d]
        if p >= 0:
            rows.append(d); cols.append(p); vals.append(-1.0)
    n = tree.n_sequences
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(tree.n_nodes, n + 1))
    b = np.zeros(tree.n_nodes)
    b[0] = 1.0
    return A, b


def solve_tree(tree: Tree, *, time_limit: float | None = None) -> Solution:
    """min v  s.t.  seq_cost[:, j] . r <= v for every placement j, r in the sequence-form
    polytope.  HiGHS (scipy.optimize.linprog)."""
    t0 = time.perf_counter()
    n, J = tree.n_sequences, len(tree.strategies)
    if J == 0:                                  # no placement fits the horizon
        r = np.zeros(n)
        # play "none" everywhere: realisation weight 1 on every none-sequence on the path
        sol = Solution(0.0, r, np.zeros(0), 0.0, "trivial: no attacker placement")
        return sol
    A_eq, b_eq = _flow_matrix(tree)
    Cs = sparse.csr_matrix(tree.seq_cost.T)
    A_ub = sparse.hstack([Cs, -np.ones((J, 1))], format="csr")
    c = np.zeros(n + 1)
    c[-1] = 1.0
    opts = {"presolve": True}
    if time_limit is not None:
        opts["time_limit"] = max(1.0, float(time_limit))
    res = linprog(c, A_ub=A_ub, b_ub=np.zeros(J), A_eq=A_eq, b_eq=b_eq,
                  bounds=[(0, None)] * n + [(None, None)], method="highs", options=opts)
    dt = time.perf_counter() - t0
    if res.status != 0:
        raise RuntimeError(f"exact LP status {res.status}: {res.message}")
    r = res.x[:n]
    return Solution(float(res.x[-1]), r, tree.seq_cost.T @ r, dt, "optimal")


def realisation(tree: Tree, behaviour) -> np.ndarray:
    """r of a behavioural policy: behaviour(tree, d) -> {label: prob} at decision node d."""
    r = np.zeros(tree.n_sequences)
    for d in range(tree.n_nodes):
        p = tree.node_parent_seq[d]
        reach = 1.0 if p < 0 else r[p]
        if reach == 0.0:
            continue
        dist = behaviour(tree, d)
        tot = sum(dist.get(lab, 0.0) for lab in tree.node_labels[d])
        if abs(tot - 1.0) > 1e-9:
            raise ValueError(f"behaviour at node {d} puts {tot} on the affordable actions "
                             f"{tree.node_labels[d]}")
        for s, lab in zip(tree.node_seqs[d], tree.node_labels[d]):
            r[s] = reach * dist.get(lab, 0.0)
    return r


def evaluate(tree: Tree, behaviour) -> dict:
    """Exact worst-case loss of a given policy in the same game: max_j L_j."""
    r = realisation(tree, behaviour)
    per = tree.seq_cost.T @ r if len(tree.strategies) else np.zeros(0)
    return {"value": float(per.max()) if len(per) else 0.0, "per_strategy": per}


# ---------------------------------------------------------------------------------------
# Declared stand-ins for the library (T11 owns the 28 members)
# ---------------------------------------------------------------------------------------

def _history(tree: Tree, d: int) -> list:
    """[(t, label, outcome), ...] from the root to decision node d (children map walk)."""
    if not hasattr(tree, "_parent_of"):
        parent = {}
        for (src, label, outcome), dst in tree.child.items():
            parent[dst] = (src, label, outcome)
        tree._parent_of = parent
    out, cur = [], d
    while cur in tree._parent_of:
        src, label, outcome = tree._parent_of[cur]
        out.append((tree.node_t[src], label, outcome))
        cur = src
    return out[::-1]


def _dist(labels, want: dict) -> dict:
    """Renormalise `want` over the affordable labels; 'none' / 'continue' take the rest."""
    w = {lab: want.get(lab, 0.0) for lab in labels}
    tot = sum(w.values())
    if tot <= 0:
        return {lab: float(lab in (NONE, CONTINUE)) for lab in labels}
    return {lab: v / tot for lab, v in w.items()}


def stand_in(name: str, *, quarantine_on_alarm: bool = True, mix: float = 0.5):
    """A behavioural policy by name (declared stand-ins until T11's library lands):
    b1 (commit every task), uniform (every affordable action but none), insertion (the
    memory sweep), rotation (targets in turn), mix (commit w.p. `mix`, else a uniform
    sweep: coverage.py's stationary schedule), recheck (re-audit an alarmed target at
    the next task, else commit), idle (never audit)."""
    def behaviour(tree: Tree, d: int) -> dict:
        labels = tree.node_labels[d]
        if tree.node_kind[d] == "response":
            return _dist(labels, {QUARANTINE if quarantine_on_alarm else CONTINUE: 1.0})
        targets = [x for x in labels if x != NONE]
        sweeps = [x for x in tree.game.targets if x != "commit"]
        t = tree.node_t[d]
        if name == "idle":
            want = {NONE: 1.0}
        elif name == "b1":
            want = {"commit": 1.0}
        elif name == "uniform":
            want = {x: 1.0 for x in targets}
        elif name == "insertion":
            want = {sweeps[0]: 1.0} if sweeps else {}
        elif name == "rotation":
            order = list(tree.game.targets)
            want = {order[t % len(order)]: 1.0}
        elif name == "mix":
            want = {"commit": mix}
            want.update({k: (1.0 - mix) / max(1, len(sweeps)) for k in sweeps})
        elif name == "recheck":
            hist = _history(tree, d)
            prev = [h for h in hist if h[0] == t - 1 and h[2] == "alarm"]
            want = {prev[0][1]: 1.0} if prev else {"commit": 1.0}
        else:
            raise ValueError(f"unknown stand-in {name!r}")
        return _dist(labels, want)
    behaviour.__name__ = f"{name}{'' if quarantine_on_alarm else '-noq'}"
    return behaviour


STAND_INS = ("idle", "b1", "uniform", "insertion", "rotation", "mix", "recheck")


# ---------------------------------------------------------------------------------------
# Lines 2-3 of Algorithm 1
# ---------------------------------------------------------------------------------------

def peak_rss_bytes() -> int:
    """Process peak resident set size (ru_maxrss: bytes on darwin, KiB on linux)."""
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(r if sys.platform == "darwin" else r * 1024)


def memory_estimate_bytes(counts: dict, J: int, Z: int) -> int:
    """What the build and the LP hold at minimum: the cost matrix (sequences x J), the
    flow constraints (~2 nonzeros per sequence, 16 bytes each) and the widest level of W
    (J x nodes x Z), all float64."""
    widest = counts["leaves"] if counts["leaves"] else 1
    return int(8 * counts["sequences"] * J + 32 * counts["sequences"] + 8 * J * widest * Z)


@dataclass
class InfeasibleRecord:
    """Evidence that line 3 is not computable for this game (plan T13, R1)."""
    reason: str                    # "sequences" | "runtime" | "world" | "not-small"
    H: int
    K: int
    KH: int
    states: int                    # sequences of the tree (exact count)
    decision_nodes: int
    strategies: int
    runtime_s: float               # wall time spent before refusing
    memory_bytes: int              # memory_estimate_bytes (lower bound for the full solve)
    peak_rss_bytes: int
    detail: str = ""

    def log_line(self) -> str:
        return (f"line23: infeasible, states={self.states}, runtime={self.runtime_s:.3f}s, "
                f"memory={self.memory_bytes / 2**20:.1f}MiB, reason={self.reason}, "
                f"H={self.H}, K={self.K}, KH={self.KH}"
                + (f", {self.detail}" if self.detail else ""))


@dataclass
class Line23:
    """What lines 2-3 return for one workflow.  kind: 'exact' (line 3 runs), 'line5'
    (KH above the threshold: the draft's else-branch), 'infeasible' (small by KH but not
    computable within the declared limits: line 5 runs, L2)."""
    kind: str
    tree: Tree | None = None
    solution: Solution | None = None
    record: InfeasibleRecord | None = None
    seconds: float = 0.0

    @property
    def exact(self) -> bool:
        return self.kind == "exact"


def is_small(H: int, K: int = K_CARRIERS) -> bool:
    """Line 2: KH <= threshold (S7: 40)."""
    return K * H <= THRESHOLD_KH


def solve_game(game: Game, *, K_draft: int = K_CARRIERS, max_sequences: int = MAX_SEQUENCES,
               max_seconds: float = MAX_SECONDS) -> Line23:
    """Lines 2-3 on a built game: the threshold, the declared limits, then the solve."""
    t0 = time.perf_counter()
    counts = count_tree(game)
    J = len(game.strategies())
    Z = (1 << len(game.hidden)) * len(PHASES)

    def refuse(reason, detail=""):
        rec = InfeasibleRecord(reason=reason, H=game.H, K=K_draft, KH=K_draft * game.H,
                               states=counts["sequences"], decision_nodes=counts["decision_nodes"],
                               strategies=J, runtime_s=time.perf_counter() - t0,
                               memory_bytes=memory_estimate_bytes(counts, J, Z),
                               peak_rss_bytes=peak_rss_bytes(), detail=detail)
        if reason != "not-small":
            LOG.warning(rec.log_line())
        return Line23("line5" if reason == "not-small" else "infeasible", record=rec,
                      seconds=rec.runtime_s)

    if not is_small(game.H, K_draft):
        return refuse("not-small", f"KH={K_draft * game.H} > {THRESHOLD_KH}")
    if counts["sequences"] > max_sequences:
        return refuse("sequences", f"{counts['sequences']} > {max_sequences} sequences")
    deadline = t0 + max_seconds
    try:
        tree = build_tree(game, deadline=deadline)
        left = deadline - time.perf_counter()
        if left <= 0:
            raise Budget()
        sol = solve_tree(tree, time_limit=left)
    except Budget:
        return refuse("runtime", f"build passed {max_seconds:.0f} s")
    except RuntimeError as e:          # HiGHS time limit or failure
        return refuse("runtime", str(e))
    dt = time.perf_counter() - t0
    if dt > max_seconds:
        return refuse("runtime", f"{dt:.1f} s > {max_seconds:.0f} s")
    return Line23("exact", tree=tree, solution=sol, seconds=dt)


def line23(ctx: A.EpisodeContext, delta_hat: int, *, respond: str = "choose",
           max_sequences: int = MAX_SEQUENCES, max_seconds: float = MAX_SECONDS) -> Line23:
    """Algorithm 1 lines 2-3 for one workflow (called once, at t = 0)."""
    if not is_small(ctx.H):
        return solve_game(_shell(ctx, delta_hat, respond), max_sequences=max_sequences,
                          max_seconds=max_seconds)
    why = world_unsupported(ctx.world)
    if why:
        rec = InfeasibleRecord(reason="world", H=ctx.H, K=K_CARRIERS, KH=K_CARRIERS * ctx.H,
                               states=0, decision_nodes=0, strategies=0, runtime_s=0.0,
                               memory_bytes=0, peak_rss_bytes=peak_rss_bytes(),
                               detail=f"exact game does not model {why}")
        LOG.warning(rec.log_line())
        return Line23("infeasible", record=rec)
    return solve_game(v3_game(ctx, delta_hat, respond=respond),
                      max_sequences=max_sequences, max_seconds=max_seconds)


def _shell(ctx, delta_hat, respond) -> Game:
    """A Game carrying only H and K, for the not-small branch (no model needed)."""
    t = tuple(C.TARGETS)
    one = {k: 1.0 for k in HIDDEN_V3}
    return Game(H=ctx.H, hidden=HIDDEN_V3, targets=t, seedable=HIDDEN_V3,
                deltas=(int(delta_hat),), budget=float(ctx.budget),
                cost={x: float(ctx.kappa[x]) for x in t}, q_clean=one, q_poison=one,
                q_commit={p: 1.0 for p in PHASES}, respond=respond)


# ---------------------------------------------------------------------------------------
# The policy: line 3's plan walked along the realised history
# ---------------------------------------------------------------------------------------

class ExactLine3Policy(A.PolicyBase):
    """Plays the exact plan: at each decision node it draws from the plan's distribution
    (published in the decision log, never the draw -- D5.3.rand).  act() at the task's
    audit node, observe() moves along (action, alarm), quarantine() plays the response
    node.  If the realised history leaves the tree (the runner bought something else, or
    Sentinel's line 8 overrode the response via `follow_quarantine`), the policy logs it
    and returns None from then on (the caller falls back to line 5)."""
    name = "exact-line3"

    def __init__(self, ctx: A.EpisodeContext, result: Line23):
        super().__init__(ctx)
        if not result.exact:
            raise ValueError("ExactLine3Policy needs an exact line-2/3 result")
        self.tree, self.sol = result.tree, result.solution
        self.node = 0
        self.off_tree = False
        self._pending = None           # the action requested at this task

    def _draw(self, t: int, dist: dict, what: str) -> str:
        r = random.Random(seed_of(self.ctx.rng_seed, "v3-exact", what, t)).random()
        acc = 0.0
        for lab, p in dist.items():
            acc += p
            if r < acc:
                return lab
        return list(dist)[-1]

    def _leave(self, t: int, why: str) -> None:
        self.off_tree = True
        self._log.append({"t": t, "line": 3, "off_tree": why})

    def act(self, t: int, B_t: float):
        if self.off_tree:
            return None
        if self.tree.node_t[self.node] != t or self.tree.node_kind[self.node] != "audit":
            self._leave(t, f"at node {self.node}, expected task {t}")
            return None
        dist = self.sol.behaviour(self.tree, self.node)
        self._log.append({"t": t, "line": 3, "x_t": dist})
        lab = self._draw(t, dist, "act")
        self._pending = lab
        return None if lab == NONE else self.action(lab)

    def observe(self, t: int, obs: A.Observation) -> None:
        if self.off_tree:
            return
        bought = obs.bought.target if obs.bought is not None else NONE
        if bought != self._pending:
            self._leave(t, f"bought {bought!r}, planned {self._pending!r}")
            return
        outcome = "-" if bought == NONE else ("alarm" if obs.alarm else "quiet")
        nxt = self.tree.child.get((self.node, bought, outcome))
        if nxt is None:
            if t == self.tree.game.H - 1 and self.tree.node_kind[self.node] == "audit" \
                    and outcome != "alarm":
                self.node = -1                 # the leaf
                return
            if outcome == "alarm" and self.tree.game.respond == "always":
                self.node = self.tree.child.get((self.node, bought, "alarm"), -1)
                return
            self._leave(t, f"no child for ({bought}, {outcome})")
            return
        self.node = nxt

    def quarantine(self, t: int):
        if self.off_tree or self.node < 0 or self.tree.node_kind[self.node] != "response":
            return None
        dist = self.sol.behaviour(self.tree, self.node)
        self._log.append({"t": t, "line": 3, "response": dist})
        lab = self._draw(t, dist, "respond")
        target = self._alarmed_target()
        nxt = self.tree.child.get((self.node, lab, "-"), -1)
        self.node = nxt
        return C.CARRIER_OF_TARGET[target] if lab == QUARANTINE else None

    def _alarmed_target(self) -> str:
        p = self.tree.node_parent_seq[self.node]
        for d in range(self.node - 1, -1, -1):
            if p in self.tree.node_seqs[d]:
                return self.tree.node_labels[d][self.tree.node_seqs[d].index(p)]
        raise RuntimeError("response node without an audit parent")


# ---------------------------------------------------------------------------------------
# The feasibility frontier (docs/reports/v3-p2-line23.md)
# ---------------------------------------------------------------------------------------

def _frontier_ctx(H: int, cell: C.Cell) -> A.EpisodeContext:
    kappa = cell.kappa()
    return A.EpisodeContext(world=C.PRIMARY, cell=cell, wf_id="frontier", seed=0, H=H,
                            budget=max(kappa.values()) * H,    # b1: never binds (C4)
                            depths=cell.depths(), kappa=kappa,
                            delegated=cell.delegated())


def frontier(H_max: int = 10, K_values=(1, 2, 3, 4), respond=RESPOND, delta_hat: int = 1,
             rho: float = 0.5, max_seconds: float = MAX_SECONDS) -> list:
    """For each K (auditable targets, commit first then memory, queue, skill) and each H,
    count the tree and, when within the limits, build and solve it.  K = 4 is the v3 game."""
    cell = C.Cell(rho=rho, delta=4)
    order = ("commit",) + HIDDEN_V3
    rows = []
    for resp in respond:
        for K in K_values:
            targets = tuple(t for t in C.TARGETS if t in order[:K])
            refused = False
            for H in range(2, H_max + 1):
                ctx = _frontier_ctx(H, cell)
                g = v3_game(ctx, delta_hat, respond=resp, targets=targets)
                cnt = count_tree(g)
                row = {"respond": resp, "K_targets": K, "H": H, "KH_draft": K_CARRIERS * H,
                       "sequences": cnt["sequences"], "decision_nodes": cnt["decision_nodes"],
                       "strategies": len(g.strategies())}
                if refused or cnt["sequences"] > MAX_SEQUENCES:
                    row["status"] = "infeasible:sequences" if cnt["sequences"] > MAX_SEQUENCES \
                        else "not-run:smaller-H-over-time"
                    rows.append(row)
                    continue
                rss0 = peak_rss_bytes()
                res = solve_game(g, max_seconds=max_seconds)
                row.update({"status": res.kind if res.exact else f"infeasible:{res.record.reason}",
                            "seconds": round(res.seconds, 3), "peak_rss_mib":
                            round(peak_rss_bytes() / 2**20, 1), "rss_before_mib":
                            round(rss0 / 2**20, 1)})
                if res.exact:
                    row.update({"build_s": round(res.tree.build_seconds, 3),
                                "lp_s": round(res.solution.lp_seconds, 3),
                                "value": round(res.solution.value, 6),
                                "memory_est_mib": round(memory_estimate_bytes(
                                    cnt, row["strategies"], 40) / 2**20, 1)})
                else:
                    refused = True
                rows.append(row)
                print(json.dumps(row), flush=True)
    return rows


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frontier", action="store_true")
    ap.add_argument("--H-max", type=int, default=10)
    ap.add_argument("--K", type=int, nargs="*", default=[1, 2, 3, 4])
    ap.add_argument("--respond", nargs="*", default=list(RESPOND))
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    if a.frontier:
        rows = frontier(a.H_max, tuple(a.K), tuple(a.respond))
        if a.out:
            with open(a.out, "w") as f:
                json.dump(rows, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
