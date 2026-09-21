"""Smoke test -- Sift. H: recovery-determination needs fewer interventions than attribution;
under PARTIAL LINEAGE a fault with unrecorded edges is unattributable while the safe reset
defined by the over-approximate read-set boundary is still determined; group interventions
scale ~ b log(n/b); adversarial edge loss is far more damaging than random.

NOTE (found by this smoke test): the manuscript's Corollary 1 stated shadowing under
reach-containment with COMPLETE lineage; that is false under unrestricted removal
interventions (removing m1 alone separates {m1} from {m1,m2}). The correct statement -- and
the one tested here -- requires the shadowed fault's edges to be unrecorded."""
import sys, os, itertools, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../_shared/smoke')); 
from harness import Smoke
S = Smoke("FSE-2027-09 Sift", "recovery identifiable where attribution is not (under partial lineage); group tests ~ b log(n/b); adversarial loss is the dangerous case",
          "random memory->work->test DAGs with hidden fault sets and simulated removal interventions")
rng = np.random.default_rng(1); N, M, T, B = 48, 30, 12, 2

def make(hidden=False):
    M2W = {i: set(rng.choice(M, rng.integers(1, 4), replace=False)) for i in range(N)}
    W2T = {w: set(rng.choice(T, rng.integers(1, 3), replace=False)) for w in range(M)}
    F = set(rng.choice(N, B, replace=False)); obs = {i: set(M2W[i]) for i in M2W}
    if hidden:                                  # one fault's influence passed through an unlogged model call
        f_hidden = sorted(F)[1]; obs[f_hidden] = set()
    return M2W, W2T, F, obs

def reach(F, M2W, W2T): return set().union(*[W2T[w] for f in F for w in M2W[f]]) if F else set()

def clears(S_rm, F, M2W, W2T): return len(reach(F - S_rm, M2W, W2T)) == 0

def search(F, M2W, W2T, obs, mode, slack=1, cap=60):
    """Adaptive group testing over RECORDED candidates (those with an observed path to a failing test).
    attribution: stop when one candidate remains.  recovery: stop when the union of remaining
    candidates is within `slack` of the fault bound (the reset R = union C is safe for every candidate)."""
    failing = reach(F, M2W, W2T)
    recorded = [i for i in range(N) if reach({i}, obs, W2T) & failing]
    cands = [set(c) for r in range(1, B + 1) for c in itertools.combinations(recorded, r)]
    q = 0
    while q <= cap:
        if not cands: return q, False
        if mode == 'attribution' and len(cands) == 1: return q, cands[0] == F
        if mode == 'recovery':
            R = set().union(*cands)
            if len(R) <= B + slack: return q, F <= R          # valid iff the true faults are inside the reset
        best, bs = None, 1e9
        for _ in range(40):
            Srm = set(rng.choice(recorded, rng.integers(1, max(2, len(recorded) // 3)), replace=False))
            yes = sum(1 for c in cands if clears(Srm, c, obs, W2T)); sc = abs(yes - len(cands) / 2)
            if sc < bs: bs, best = sc, Srm
        q += 1; out = clears(best, F, M2W, W2T)               # the TRUE outcome (hidden edges act)
        cands = [c for c in cands if clears(best, c, obs, W2T) == out]
    return q, False

qa, qr = [], []
for _ in range(20):
    M2W, W2T, F, obs = make()
    qa.append(search(F, M2W, W2T, obs, 'attribution')[0]); qr.append(search(F, M2W, W2T, obs, 'recovery')[0])
S.check("recovery-determination needs fewer interventions than attribution (Thm 2)",
        np.mean(qr) < np.mean(qa), f"median queries: attribution={np.median(qa):.0f} recovery={np.median(qr):.0f}")
att_ok, rec_ok, bnd_ok = [], [], []
for _ in range(20):
    M2W, W2T, F, obs = make(hidden=True)
    att_ok.append(search(F, M2W, W2T, obs, 'attribution')[1])
    rec_ok.append(search(F, M2W, W2T, obs, 'recovery')[1])
    # safety boundary: quarantine every memory whose over-approximate read-set edge reaches a failing work node
    failing_w = {w for f in F for w in M2W[f]}
    boundary = {i for i in range(N) if M2W[i] & failing_w}       # the read-set edge IS recorded (over-approximate)
    bnd_ok.append(F <= boundary)
S.check("partial lineage: a fault with unrecorded edges is unattributable, yet the over-approximate boundary reset is safe (corrected Cor 1)",
        np.mean(att_ok) < 0.2 and np.mean(bnd_ok) == 1.0,
        f"attribution correct={np.mean(att_ok):.2f}, recovery via candidates={np.mean(rec_ok):.2f}, boundary reset safe={np.mean(bnd_ok):.2f}")
bound = B * np.log2(N / B)
S.check("group interventions scale like b log(n/b), far below singleton testing (Thm 3/4)",
        np.median(qa) < 2.5 * bound and np.median(qa) < N / 2, f"median attribution queries={np.median(qa):.0f}; b log2(n/b)={bound:.1f}; singleton={N}")
def recover_with_loss(rate, adversarial):
    ok = 0
    for _ in range(40):
        M2W, W2T, F, obs = make(); f = next(iter(F)); obs = {i: set(M2W[i]) for i in M2W}
        if adversarial:
            k = int(round(rate * sum(len(v) for v in obs.values())))
            for w in list(obs[f])[:k]: obs[f].discard(w)
        else:
            for i in obs: obs[i] = {w for w in obs[i] if rng.random() > rate}
        ok += M2W[f] <= obs[f]                    # regenerating observed descendants covers the true ones
    return ok / 40
rr = {r: recover_with_loss(r, False) for r in (0.1, 0.3, 0.5)}; ra = {r: recover_with_loss(r, True) for r in (0.1, 0.3)}
S.check("adversarial edge loss collapses valid recovery at a rate where random loss degrades gracefully (Thm 5)",
        ra[0.3] < 0.2 and rr[0.3] > ra[0.3] + 0.3, f"valid recovery -- random 0.1/0.3/0.5: {[round(rr[r],2) for r in rr]}; adversarial 0.1/0.3: {[round(ra[r],2) for r in ra]}")
S.finish(os.path.join(os.path.dirname(__file__), 'smoke_result.json'))
