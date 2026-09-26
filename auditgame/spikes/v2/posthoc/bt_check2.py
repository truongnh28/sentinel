"""Code-only: the reachable floor of p_attack, and which library members can ever leave commit."""
import pathlib
import sys, json, random
AUDITGAME = pathlib.Path(__file__).resolve().parents[3]     # auditgame/
sys.path.insert(0, str(AUDITGAME))
import belief_v2, draft_setup as D, carrier_policies as CP
from core import CARRIERS
TU = json.load(open(AUDITGAME / "reference" / "v2_tuned.json"))
betas = TU["betas"]
# 1. analytic floor: windows never informable (never active, or carrier never swept) keep a fixed ratio to NULL
for H in range(6, 15):
    bel = belief_v2.DriftBelief(CARRIERS, H, D.DELTAS, betas)
    unin = [w for w in bel.windows if w[0] not in D.SWEEP_CARRIERS or not any(bel.active(w, t) for t in range(H))]
    f = len(unin) / len(bel.windows)
    print(f"H={H:2d} windows={len(bel.windows):3d} uninformable={len(unin):3d} f={f:.4f} floor f/(1+f)={f/(1+f):.4f}")
# 2. empirical: drive the belief with the quietest possible sweep evidence on every carrier, every task
lo = 1.0
for H in range(6, 15):
    bel = belief_v2.DriftBelief(CARRIERS, H, D.DELTAS, betas)
    for t in range(H):
        for k in D.SWEEP_CARRIERS:
            bel.update(t, {k: 1e-9})
            lo = min(lo, bel.p_attack())
print("lowest p_attack under maximally quiet sweeps, H 6..14:", round(lo, 4))
# 3. members: which library entries are commit-only by construction
b1like = [n for n, (cls, kw) in CP.LIBRARY.items()
          if (cls is CP.CarrierWeighted and kw["weights"] == (0, 0, 0, 1)) or (cls is CP.BeliefThreshold and kw["tau"] >= 0.5)]
print("library size", len(CP.LIBRARY), "commit-only:", len(b1like), "distinct behaviours <=", len(CP.LIBRARY) - len(b1like) + 1)
print("BT tau<0.5:", [n for n, (cls, kw) in CP.LIBRARY.items() if cls is CP.BeliefThreshold and kw["tau"] < 0.5])
# 4. tuned cells: any member whose ACTION reads the belief (BT with tau < 0.5)?
cells = [(r, k) for r in TU["rho"] for k in TU["rho"][r]["mix"]]
reads = [(r, k, part) for r, k in cells for part in ("robust", "nominal")
         for n in TU["rho"][r]["mix"][k][part] if n.startswith("L-BT-0.3")]
reads += [(r, k, "pure") for r, k in cells if TU["rho"][r]["mix"][k]["pure"].startswith("L-BT-0.3")]
print("tuned cells:", len(cells), " cells weighting a belief-reading member:", reads)
