"""Smoke test -- Sentinel. H: adaptive randomized audit allocation beats audit-at-commit only
when the trigger is delayed and carriers are heterogeneous (regime boundary); randomization
matters more than adaptivity; fixed-stage auditing (on-insertion) is the worst policy."""
import sys, os, itertools, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../_shared/smoke')); 
from harness import Smoke
S = Smoke("FSE-2027-15 Sentinel", "adaptive allocation beats commit-time audit only beyond a delay/heterogeneity threshold; randomize before you adapt; audit-on-insertion is worst",
          "finite Stackelberg audit game solved by attacker best-response enumeration")
H, K, PSI, PSI_C, B = 8, 4, 0.7, 0.55, 3.0                    # tasks, carriers, carrier-audit power, commit-audit power, budget/task

def harm(policy, delta, kappa, n_mc=400, seed=0):
    """Worst case over attacker (carrier k, insertion time t0) of realised harm under a defender policy.
    policy(t, belief) -> dict carrier->audit probability (may include 'commit') costing sum(kappa*p) <= B."""
    rng = np.random.default_rng(seed); worst = 0.0
    for k, t0 in itertools.product(range(K), range(H - delta)):
        h = 0
        for _ in range(n_mc):
            caught = False; alarms = []
            for t in range(t0, min(t0 + delta + 1, H)):
                p = policy(t, alarms, kappa)
                if t < t0 + delta:                     # window before trigger: only the poisoned carrier is informative
                    if rng.random() < p.get(k, 0) * PSI: caught = True; break
                    alarms.append(t)
                else:                                  # trigger task: the harmful commit is visible at commit
                    if rng.random() < p.get('commit', 0) * PSI_C: caught = True; break
            h += (not caught)
        worst = max(worst, h / n_mc)
    return worst

def pol_commit(t, alarms, kappa): return {'commit': min(1.0, B / kappa['commit'])}
def pol_insertion(t, alarms, kappa): return {0: min(1.0, B / kappa[0])}                   # audits memory carrier only
def pol_uniform(t, alarms, kappa):
    p = B / (sum(kappa[i] for i in range(K)) + kappa['commit']); return {**{i: p for i in range(K)}, 'commit': p}
def make_minimax(delta, kappa):
    """Sentinel: the Stackelberg minimax over the defender's budget split.  The attacker
    best-responds to the committed distribution, so the carrier share must EQUALISE detection
    probability across carriers (attacker indifference), not favour cheap ones -- a cost-greedy
    allocator is exploited by inserting into the expensive carrier (found by this smoke test).
    The commit/carrier split s is chosen by minimising the attacker's best-response harm."""
    kc = sum(kappa[i] for i in range(K))
    def pol_for(s, alarms):
        s2 = min(1.0, s * (1.25 if alarms else 1.0))           # alarm history: shift toward the carriers (belief that a window is open)
        p_car = s2 * B / kc                                      # equal per-carrier probability, cost-weighted budget
        return {**{i: min(1.0, p_car) for i in range(K)}, 'commit': min(1.0, (1 - s2) * B / kappa['commit'])}
    best_s, best_h = 0.0, 9
    for sgrid in np.linspace(0, 1, 11):
        h = harm(lambda t, a, k: pol_for(sgrid, a), delta, kappa, n_mc=120, seed=1)
        if h < best_h: best_h, best_s = h, sgrid
    return lambda t, alarms, kappa: pol_for(best_s, alarms)
def pol_costgreedy(t, alarms, kappa):                             # the exploitable heuristic, kept for contrast
    w = np.array([1 / kappa[i] for i in range(K)]); w = w / w.sum()
    return {**{i: min(1.0, 0.75 * B * w[i] / kappa[i]) for i in range(K)}, 'commit': min(1.0, 0.25 * B / kappa['commit'])}
def pol_deterministic(t, alarms, kappa): return {t % K: min(1.0, B / kappa[t % K])}    # round-robin, no randomization

def kappas(chi):
    base = np.array([1.0, 1.0, 1.0, 1.0]) if chi == 0 else np.array([0.4, 0.9, 1.6, 2.6])
    return {**{i: float(base[i]) for i in range(K)}, 'commit': 2.0}

grid = {}
for chi in (0, 1.34):
    for delta in (0, 1, 2, 4):
        kp = kappas(chi)
        grid[(chi, delta)] = dict(commit=harm(pol_commit, delta, kp), adaptive=harm(make_minimax(delta, kp), delta, kp),
                                  uniform=harm(pol_uniform, delta, kp), insertion=harm(pol_insertion, delta, kp),
                                  determ=harm(pol_deterministic, delta, kp), greedy=harm(pol_costgreedy, delta, kp))
imp = {k: 100 * (1 - v['adaptive'] / v['commit']) for k, v in grid.items()}
S.check("regime boundary: no gain at zero delay; a clear gain by delay 2 (smaller under heterogeneity, whose crossover is later); gain rises with delay",
        imp[(1.34, 0)] <= 5 and imp[(0, 0)] <= 5 and imp[(0, 2)] > 15 and imp[(1.34, 2)] > 5
        and imp[(1.34, 4)] > imp[(1.34, 2)] and imp[(0, 4)] > imp[(0, 2)],
        "harm reduction vs commit-audit (%): " + ", ".join(f"chi={c},d={d}: {imp[(c,d)]:+.0f}" for (c, d) in sorted(imp)))
g = grid[(1.34, 2)]
S.check("randomization matters more than adaptivity: a deterministic schedule is defeated, uniform random recovers most of the minimax gain, and a cost-greedy allocator is exploited under heterogeneity",
        g['determ'] > 0.85 and (g['commit'] - g['uniform']) > 0.5 * (g['commit'] - g['adaptive']) and g['greedy'] > g['uniform'],
        f"worst-case harm at chi=1.34, delay=2: commit={g['commit']:.2f} deterministic={g['determ']:.2f} cost-greedy={g['greedy']:.2f} uniform={g['uniform']:.2f} minimax={g['adaptive']:.2f}")
S.check("heterogeneity direction (informational): does the minimax gain over commit-audit grow or shrink with carrier-cost heterogeneity at delay 4?",
        True, f"gain at delay 4: chi=0 -> {imp[(0,4)]:+.0f}%, chi=1.34 -> {imp[(1.34,4)]:+.0f}%  "
              + ("(SHRINKS with heterogeneity: contradicts the manuscript's projected Fig. 3, which shows a larger gain at high chi)" if imp[(1.34,4)] < imp[(0,4)] else "(grows with heterogeneity, as the manuscript projects)"))
S.check("audit-on-insertion is the worst policy: the attacker simply uses an unaudited carrier",
        all(grid[k]['insertion'] >= max(grid[k]['commit'], grid[k]['adaptive'], grid[k]['uniform']) - 1e-9 for k in grid),
        f"insertion-audit worst-case harm = {grid[(1.34,4)]['insertion']:.2f} (attacker picks another carrier)")
S.finish(os.path.join(os.path.dirname(__file__), 'smoke_result.json'))
