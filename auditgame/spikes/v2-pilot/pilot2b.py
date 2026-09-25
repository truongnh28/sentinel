"""Pilot 2b -- same world as pilot 2; adds a PHASE-RANDOMIZED rotation and a CROSS-FITTED best
response (placement chosen on odd seeds, scored on even seeds and vice versa), which removes the
upward bias of taking a max over noisy per-placement means.  DEV only (django)."""
import json, random, time
from concurrent.futures import ProcessPoolExecutor

import build
import pilot2 as P2
from core import seed_of


class RotatePhase:
    name = "rotation m>s>q @3, random phase"
    def __init__(self, H, rs): self.ph = random.Random(seed_of(rs, "phase")).randrange(3)
    def act(self, t): return ("sweep", P2.CARRIERS3[(t + self.ph) % 3], 3)
    def observe(self, t, k, post): pass


POL = {"B1": P2.B1, "Uniform": P2.Uniform, "Rotate": P2.Rotate, "RotatePhase": RotatePhase,
       "Thompson": P2.Thompson, "Oracle": P2.Oracle}


def job(args):
    name, delta, rho = args
    Pc = POL[name]
    naive, xfit = [], []
    for wf in P2.dev():
        by_pl = {}
        for k in P2.CARRIERS3:
            for ps in build.plan_poison_all(wf, k, delta):
                for s in P2.SEEDS:
                    rs = seed_of(wf.wf_id, s)
                    if not (random.Random(seed_of(rs, ps.sigma, "solve")).random() < 0.62):
                        continue
                    if Pc is P2.Oracle:
                        h = P2.run(wf, ps, P2.Oracle, s, rho, 0.0)[0]
                    else:
                        P2.POLICIES.append(Pc) if Pc not in P2.POLICIES else None
                        h = P2.run(wf, ps, Pc, s, rho, 0.0)[0]
                    by_pl.setdefault((k, ps.iota), {})[s] = h
        if not by_pl:
            continue
        mean = lambda d, keep: [v for s, v in d.items() if keep(s)]
        full = {pl: sum(d.values()) / len(d) for pl, d in by_pl.items()}
        naive.append(max(full.values()))
        vals = []
        for pick, score in ((lambda s: s % 2 == 1, lambda s: s % 2 == 0), (lambda s: s % 2 == 0, lambda s: s % 2 == 1)):
            sel = {pl: mean(d, pick) for pl, d in by_pl.items()}
            sel = {pl: sum(v) / len(v) for pl, v in sel.items() if v}
            if not sel:
                continue
            best = max(sel, key=sel.get)
            sc = mean(by_pl[best], score)
            if sc:
                vals.append(sum(sc) / len(sc))
        if vals:
            xfit.append(sum(vals) / len(vals))
    return name, delta, rho, sum(naive) / len(naive), sum(xfit) / len(xfit)


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(n, d, r) for n in POL for d in P2.DELTAS for r in (0.25, 1.0)]
    with ProcessPoolExecutor(10) as ex:
        out = list(ex.map(job, jobs))
    json.dump(out, open("pilot2b.json", "w"))
    T = {(n, d, r): (a, b) for n, d, r, a, b in out}
    for r in (1.0, 0.25):
        print(f"\n== rho_patch={r}, drift match=0: V_BR  naive-max | CROSS-FITTED")
        print(f"{'policy':12s}" + "".join(f"     D={d:<9d}" for d in P2.DELTAS))
        for n in POL:
            print(f"{n:12s}" + "".join(f"  {T[(n,d,r)][0]:.3f}|{T[(n,d,r)][1]:.3f} " for d in P2.DELTAS))
    print(f"\ndone in {time.time()-t0:.0f}s")
