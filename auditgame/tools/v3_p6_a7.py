#!/usr/bin/env python3
"""tools/v3_p6_a7.py -- P6: make the A7 sensitivity world measure A7 (DEV SPLIT ONLY).

WHY THIS FILE EXISTS.  The A7 world (config.PROVENANCE = ("A0", "A7"), D7.commit-prov)
exists to ask ONE question: does a commit audit that can also read the PROVENANCE of the
contributing skills change the conclusions?  Provenance is an EXTRA observation channel
(L2, fix-a7 27/09, v3/observe.py:26): Observation.alarm is the patch score's in every
world, and only a system that declares `reads_provenance` uses the channel.  Among the
baselines exactly one does -- B1-prov (v3/baselines.py:212) -- and B1-prov is NOT in
grid.SYSTEMS, so grid.units() emits no unit for it and the P2 dev run
(spikes/v3-run/dev-headline-rest/sens_A7.jsonl, 15 systems) contained no reader on the
baseline side.  Confirmed empirically by --diagnose: all NINE non-Sentinel systems are
bit-identical to the primary world's records, field for field, once `world` / `world_id` / `policy`
are removed.  The Sentinel class does differ (Sentinel is a reader too, sentinel.py:511),
so the P2 A7 rows measure a Sentinel-side effect only; the contrast the world was built
for -- the same commit audit with and without the provenance channel -- was never run.
docs/reports/v3-p2-headline-dual-metric.md section 10.4.2 declares exactly that.

WHAT IT RUNS.  Two blocks on the DEV split at the headline cells (chi = config.CHI_PRIMARY,
d' = config.DPRIME_PRIMARY, every rho of RHO_GRID and every Delta of DELTAS, the seven
held-out attacker columns, the first two seeds of config.SEEDS, the P2 dev scale), three systems:

    a7   world = the A7 sensitivity world (config.sensitivities()["A7"])
    a0   world = config.PRIMARY (A0), the same cells -- the anchor

    B1 audit-at-commit   the commit audit that does NOT read the channel
    B1-prov              the SAME audit that DOES read it   <-- the contrast pair
    Sentinel             the headline system, to ask whether the CONCLUSION moves

THE SYSTEM LIST, JUSTIFIED.  The contrast is carried by the pair (B1, B1-prov) INSIDE the
A7 world: same policy class, same budget rule, same depth, same cell, same world -- the one
difference is that B1-prov's commit alarm is "patch score OR provenance score over
tau_det".  Comparing B1-prov in A7 against B1-prov in A0 would give the same contrast but
across two worlds; the within-A7 pair is cleaner and is what "an audit that reads the
provenance channel vs the same audit without it" means.  Sentinel is in the list because
the paper's conclusion is a GAIN over the best baseline: if B1-prov beats B1 in A7, that
gain shrinks, and that -- not the B1-prov row itself -- is what would make a paper sentence
wrong.  Nothing else is run: every other baseline is provably bit-identical between A0 and
A7 (--diagnose), so re-running it would buy no information.

THE FREEZE.  v3/ is untouched: B1-prov already exists, is already in the frozen manifest
(49 policies), and reaches the episode loop through baselines.ALL, so tools/v3_run.py's
policy_factory builds it without a change.  The one thing grid.py will not do is EMIT a
unit for it, so this module builds grid.Unit / grid.Chain objects itself and hands them to
v3_run.simulate -- the same runner seam, the same validate_record, the same pin_records.
This file is in tools/ and is none of freeze_v3.FILES, so the v3 manifest stays at Gate 4's
signed pin sha256:9c4c0d018b18 and the base freeze at sha256:c789fa7362e0; --check-freeze
proves it and every mode runs it first.

DEV ONLY.  There is no --split: the split is "dev", hard-coded.  seal.unseal is never
called, tools/v3_run.py is never invoked as a process, no unseal grant is consumed, nothing
is appended to frozen/v3-unseal-log.jsonl.  Every number this module prints is a
DEVELOPMENT-SPLIT number (N3) and says nothing about held-out.

METHOD (nothing here re-specifies a metric; every estimate comes from v3/metrics.py).
  * wild cluster bootstrap over repo families, Webb weights, N = metrics.N_BOOT = 10000,
    alpha = 0.05, V re-maxed over the attacker columns in every draw, one shared set of
    family draws per call so a difference is drawn paired (metrics.boot_values).
  * V(harm) = field "harm".  V(L) = Definition 1, L = harm + lambda_Q fq + lambda_T t_lost
    (runner.loss_of).  metrics.gain_ci hard-codes field="harm", so for L the scored field is
    RELABELLED (row["harm"] <- L), exactly as tools/v3_p5_h18_heldout.as_metric does;
    alias_check proves the relabelled path and table(..., field="loss") agree exactly.
  * Deltas: config.HEADLINE_DELTAS (4, 8), the headline reading.
  * BH (metrics.bh, q = config.BH_Q = 0.05): ONE family per metric over the four rho of the
    primary test (m = 4).  The primary test is the A7 contrast B1 -> B1-prov; the Sentinel
    gains are reported as descriptive re-reads of the same records and are NOT added to
    that family (they are not independent questions about the channel).
  * pairs bootstrap is printed beside wild for the primary test (R6: never the prettier).

USAGE
    ../.venv/bin/python tools/v3_p6_a7.py --check-freeze
    ../.venv/bin/python tools/v3_p6_a7.py --diagnose
    ../.venv/bin/python tools/v3_p6_a7.py --run --jobs 8
    ../.venv/bin/python tools/v3_p6_a7.py --analyse
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent            # auditgame/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from v3 import attackers as A                                    # noqa: E402
from v3 import baselines as BL                                   # noqa: E402
from v3 import config as C                                       # noqa: E402
from v3 import corpus as K                                       # noqa: E402
from v3 import freeze_v3 as F                                    # noqa: E402
from v3 import grid as G                                         # noqa: E402
from v3 import metrics as M                                      # noqa: E402
from v3 import runner as R                                       # noqa: E402

import v3_p5_h18_heldout as P5                                   # noqa: E402  (the estimator)
import v3_run as RUN                                             # noqa: E402  (the runner seam)

SPLIT = "dev"                                    # D33: this module has no eval mode
OUT = ROOT / "spikes" / "v3-run" / "dev-p6-a7"
OUT_JSON = ROOT / "spikes" / "v3-run" / "a7_verdict.json"
P2_A7 = ROOT / "spikes" / "v3-run" / "dev-headline-rest" / "sens_A7.jsonl"
P2_MAIN = ROOT / "spikes" / "v3-run" / "dev-headline-main" / "main.jsonl"

B1 = BL.B1AuditAtCommit.name                     # "B1 audit-at-commit"
B1P = BL.B1Provenance.name                       # "B1-prov"
SENTINEL = G.SENTINEL                            # "Sentinel"
SYSTEMS = (B1, B1P, SENTINEL)
BLOCK_A7, BLOCK_A0 = "a7", "a0"                  # NOT "main": v3_run.summarise is not used
HELD_OUT = tuple(A.held_out())
HEAD_DELTAS = tuple(C.HEADLINE_DELTAS)
RHOS = tuple(C.RHO_GRID)
METRICS = ("harm", "L")
#: the fields the estimator reads; the heavy ones (c_traj, audits, decision_log) never load
KEEP = P5.KEEP
NAN = float("nan")


# ---------------------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------------------

def check_freeze(strict=True) -> dict:
    """tools/v3_p5_h18_heldout.check_freeze verbatim: Gate 4's signed pins must not have
    moved (v3 manifest, scorecard rules, grid digest, the clean base line)."""
    return P5.check_freeze(strict=strict)


# ---------------------------------------------------------------------------------------
# The grid this module builds (grid.py emits no B1-prov unit; it is not edited)
# ---------------------------------------------------------------------------------------

def worlds() -> dict:
    sens = dict(C.sensitivities())
    return {BLOCK_A7: ("A7", sens["A7"]), BLOCK_A0: ("primary", C.PRIMARY)}


def headline_cells() -> list:
    """The sensitivity block's cells (grid._cells default): every rho x every Delta at the
    primary chi and detector -- exactly the cells sens:A7 ran on in P2."""
    cells = G._cells()
    assert all(c.chi == C.CHI_PRIMARY and c.dprime == C.DPRIME_PRIMARY for c in cells)
    return cells


#: the P2 dev scale: the FIRST TWO seeds of config.SEEDS, as `--seeds 2` gave
#: spikes/v3-run/dev-headline-rest (100 dev workflows x 2 seeds).  Declared so this run is
#: comparable with the P2 A7 rows it replaces, not tuned for precision.
SEEDS = C.SEEDS[:2]


def chains(seeds=SEEDS) -> list:
    """One Chain per (block, world, cell, system, held-out column, seed).  `core=False`:
    these units are outside the core grid, like every supplementary sensitivity."""
    out = []
    for block, (wname, world) in worlds().items():
        for cell in headline_cells():
            C.check_world_cell(world, cell)
            for s in SYSTEMS:
                for col in HELD_OUT:
                    u = G.Unit(block, None, wname, world, cell, s, col, False, ())
                    out += [G.Chain(u, sd) for sd in seeds]
    return out


def run(jobs: int, workflows: int = 0, out: pathlib.Path = OUT) -> dict:
    """Simulate on dev through v3_run.simulate (the one runner seam).  No seal, no token,
    no eval."""
    info = check_freeze()
    header = F.header_line()
    print(header, flush=True)
    print("DEV SPLIT ONLY (N3): no held-out claim follows from this run", flush=True)
    chs = chains()
    for name in sorted({ch.unit.system for ch in chs}):
        F.require_frozen(name)                    # draft S7: refuse an unfrozen policy
        RUN.policy_factory(name)                  # refuse a missing factory before running
    missing = RUN.missing_parts(sorted({ch.unit.system for ch in chs}))
    if missing:
        raise SystemExit(f"not run: Sentinel's parts are missing: {'; '.join(missing)}")
    wfs = K.dev_workflows()
    wfs = wfs[:workflows] if workflows else wfs
    print(f"{len(chs)} chains, {len(wfs)} dev workflows, systems {list(SYSTEMS)}, "
          f"jobs {jobs}", flush=True)
    written = RUN.simulate(chs, wfs, SPLIT, out, jobs, token=None, stub=False)
    pin = RUN.pin_records(out, written)
    meta = {"split": SPLIT, "tool": "tools/v3_p6_a7.py", "blocks": sorted(worlds()),
            "systems": list(SYSTEMS), "seeds": list(SEEDS), "n_chains": len(chs),
            "n_workflows": len(wfs), "jobs": jobs, "parts": "frozen",
            "header_start": header, "freeze": info, "records_sha256": str(pin),
            **RUN.provenance(),
            "sha256_self": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
    (out / "summary.json").write_text(json.dumps(meta, indent=1, default=str) + "\n",
                                      encoding="utf-8")
    print("records", pin, flush=True)
    return meta


# ---------------------------------------------------------------------------------------
# The diagnosis: the P2 A7 records vs the P2 primary records, bit for bit
# ---------------------------------------------------------------------------------------

def diagnose(a7: pathlib.Path = P2_A7, main: pathlib.Path = P2_MAIN) -> dict:
    """Digest every P2 record with `world` / `world_id` removed and key it by
    (policy, cell_id, attack, wf, seed).  A system whose A7 digests all equal the primary
    world's did not read the channel -- the A7 switch changed nothing for it.  Cheap: one
    streaming pass per file, no simulation."""
    def load(path):
        out = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                body = {k: v for k, v in d.items()
                        if k not in ("world", "world_id", "policy")}
                out[(d["policy"], d["cell_id"], d["attack"], d["wf"], d["seed"])] = \
                    hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        return out
    a, m = load(a7), load(main)
    per = {}
    for p in sorted({k[0] for k in a}):
        ka = [k for k in a if k[0] == p]
        sh = [k for k in ka if k in m]
        same = sum(1 for k in sh if a[k] == m[k])
        per[p] = {"n_a7": len(ka), "n_shared": len(sh), "identical": same,
                  "differ": len(sh) - same,
                  "reads_channel": None if not sh else bool(len(sh) - same)}
    out = {"a7_file": str(a7.relative_to(ROOT)), "main_file": str(main.relative_to(ROOT)),
           "n_a7": len(a), "n_main": len(m), "b1_prov_present": B1P in {k[0] for k in a},
           "per_policy": per}
    for p, r in per.items():
        print(f"{p:34} n_a7 {r['n_a7']:6} shared {r['n_shared']:6} "
              f"identical {r['identical']:6} differ {r['differ']:6}")
    print(f"B1-prov present in the P2 A7 records: {out['b1_prov_present']}")
    return out


# ---------------------------------------------------------------------------------------
# Loading this run's records
# ---------------------------------------------------------------------------------------

def load(out: pathlib.Path = OUT) -> tuple:
    """(bags, meta): bags[(block, rho)] -> projected rows at the headline Deltas."""
    bags = collections.defaultdict(list)
    meta = {}
    digests = collections.defaultdict(dict)
    for block in worlds():
        path = out / f"{block}.jsonl"
        n, pols, wfs, repos, worlds_seen = 0, set(), set(), set(), set()
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                n += 1
                pols.add(d["policy"]); wfs.add(d["wf"]); repos.add(d["repo"])
                worlds_seen.add(d["world"]["provenance"])
                key = (d["policy"], d["cell_id"], d["attack"], d["wf"], d["seed"])
                body = {k: v for k, v in d.items()
                        if k not in ("world", "world_id", "policy")}
                digests[block][key] = hashlib.sha256(
                    json.dumps(body, sort_keys=True).encode()).hexdigest()
                if d["attack"] in HELD_OUT and d["delta"] in HEAD_DELTAS:
                    r = {k: d[k] for k in KEEP}
                    r["loss"] = R.loss_of(d)
                    bags[(block, d["cell"]["rho"])].append(r)
        meta[block] = {"file": str(path.relative_to(ROOT)), "n_records": n,
                       "policies": sorted(pols), "n_workflows": len(wfs),
                       "n_repos": len(repos), "provenance": sorted(worlds_seen)}
    return bags, meta, digests


def a0_identity(digests: dict) -> dict:
    """The integrity check the L2 reading predicts: in A0 the observation carries NO
    provenance, so B1-prov must be B1, record for record."""
    d = digests[BLOCK_A0]
    keys = [k for k in d if k[0] == B1]
    pairs = [(k, (B1P,) + k[1:]) for k in keys]
    both = [(x, y) for x, y in pairs if y in d]
    same = sum(1 for x, y in both if d[x] == d[y])
    return {"claim": "in A0 (no provenance channel) B1-prov is B1, record for record",
            "n_compared": len(both), "identical": same, "differ": len(both) - same,
            "holds": bool(both) and same == len(both)}


def reproduces_p2(digests: dict, p2_a7: pathlib.Path = P2_A7) -> dict:
    """This run's A7 block must reproduce the P2 A7 records BIT FOR BIT for the two systems
    P2 did run (B1, Sentinel).  If it does, the only new thing in the file is B1-prov, and
    the A7 rows of docs/reports/v3-p2-headline-dual-metric.md are not being restated -- they
    are being joined by a reader.  (The P2 run carried an older v3 manifest digest,
    c238e058dfcb, so this is a check, not an assumption.)"""
    old = {}
    with open(p2_a7, encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            if d["policy"] not in (B1, SENTINEL):
                continue
            body = {k: v for k, v in d.items() if k not in ("world", "world_id", "policy")}
            old[(d["policy"], d["cell_id"], d["attack"], d["wf"], d["seed"])] = \
                hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    mine = digests[BLOCK_A7]
    out = {}
    for pol in (B1, SENTINEL):
        sh = [k for k in mine if k[0] == pol and k in old]
        same = sum(1 for k in sh if mine[k] == old[k])
        out[pol] = {"n_compared": len(sh), "identical": same, "differ": len(sh) - same}
    out["holds"] = all(v["n_compared"] and not v["differ"]
                       for k, v in out.items() if k != "holds")
    out["p2_file"] = str(p2_a7.relative_to(ROOT))
    return out


def a7_reader_check(digests: dict) -> dict:
    """The other side: B1 must be bit-identical between A0 and A7 (it ignores the channel),
    while B1-prov must differ somewhere (it reads it)."""
    out = {}
    for p in (B1, B1P, SENTINEL):
        ka = [k for k in digests[BLOCK_A7] if k[0] == p]
        both = [k for k in ka if k in digests[BLOCK_A0]]
        same = sum(1 for k in both if digests[BLOCK_A7][k] == digests[BLOCK_A0][k])
        out[p] = {"n_compared": len(both), "identical": same, "differ": len(both) - same}
    return out


# ---------------------------------------------------------------------------------------
# The estimates
# ---------------------------------------------------------------------------------------

def as_metric(rows: list, metric: str) -> list:
    return P5.as_metric(rows, metric)


def alias_check(rows: list, policy: str) -> dict:
    a = M.table(rows, policy, HELD_OUT, HEAD_DELTAS, field="loss").value
    b = M.table(as_metric(rows, "L"), policy, HELD_OUT, HEAD_DELTAS, field="harm").value
    return {"table_field_loss": a, "alias_field_harm": b, "identical": bool(a == b)}


def _gain(rows, base, cand, metric, method="wild") -> dict:
    g = M.gain_ci(as_metric(rows, metric), base, cand, HELD_OUT, HEAD_DELTAS, method=method)
    return {k: g[k] for k in ("gain", "lo", "hi", "abs_diff", "abs_lo", "abs_hi", "v_base",
                              "v_cand", "p_abs", "p_rel", "rel_reliable", "base_events",
                              "n_repos", "n_workflows", "n_zero_base", "method", "n_boot",
                              "alpha")}


def _v(rows, policy, metric) -> dict:
    t = M.table(as_metric(rows, metric), policy, HELD_OUT, HEAD_DELTAS)
    return {"v": t.value, "worst_column": t.worst_column, "n_workflows": len(t.wfs),
            "n_records": t.n_records}


def mechanism(bags: dict) -> dict:
    """Why L and harm disagree: the per-episode means of the three L components over the
    same selection (held-out columns, headline Deltas).  Descriptive, no interval -- L's
    weights are runner.LAMBDA_Q / LAMBDA_T, not re-derived here."""
    out = {}
    for block in worlds():
        for rho in RHOS:
            rs = bags[(block, rho)]
            for pol in SYSTEMS:
                g = [r for r in rs if r["policy"] == pol]
                if not g:
                    out.setdefault(block, {}).setdefault(str(rho), {})[pol] = {
                        "refused": "no records in this selection"}
                    continue
                n = len(g)
                out.setdefault(block, {}).setdefault(str(rho), {})[pol] = {
                    "n_episodes": n,
                    "harm_per_ep": sum(r["harm"] for r in g) / n,
                    "fq_per_ep": sum(r["fq"] for r in g) / n,
                    "t_lost_per_ep": sum(r["t_lost"] for r in g) / n,
                    "L_per_ep": sum(r["loss"] for r in g) / n}
    return out


def analyse(out: pathlib.Path = OUT) -> dict:
    info = check_freeze()
    bags, meta, digests = load(out)
    res = {"split": SPLIT, "label": "DEVELOPMENT SPLIT (N3): says nothing about held-out",
           "freeze": info, "records": meta,
           "deltas": list(HEAD_DELTAS), "rhos": list(RHOS),
           "estimator": {"bootstrap": "wild cluster by repo family, Webb weights",
                         "n_boot": M.N_BOOT, "alpha": M.ALPHA,
                         "bh_q": C.BH_Q, "bh_family": "one per metric over the 4 rho of the "
                                                      "primary test (m = 4)"},
           "integrity": {"a0_b1prov_is_b1": a0_identity(digests),
                         "a7_vs_a0_by_policy": a7_reader_check(digests),
                         "reproduces_p2_a7": reproduces_p2(digests)},
           "alias_check": {}, "primary": {}, "sentinel": {}, "levels": {}, "bh": {},
           "mechanism": mechanism(bags)}

    for metric in METRICS:
        rows0 = bags[(BLOCK_A7, RHOS[0])]
        res["alias_check"][metric] = alias_check(rows0, B1P) if metric == "L" else "n/a"
        prim, sent, lev = {}, {}, {}
        for rho in RHOS:
            a7 = bags[(BLOCK_A7, rho)]
            a0 = bags[(BLOCK_A0, rho)]
            if not a7:
                prim[str(rho)] = {"refused": "no A7 records at this rho"}
                continue
            # PRIMARY TEST: inside A7, does the channel-reading audit beat the blind one?
            prim[str(rho)] = {m: _gain(a7, B1, B1P, metric, m) for m in M.METHODS}
            # the conclusion-level re-read: Sentinel's gain over each baseline, in A7
            sent[str(rho)] = {
                "vs_B1_in_A7": _gain(a7, B1, SENTINEL, metric),
                "vs_B1prov_in_A7": _gain(a7, B1P, SENTINEL, metric),
                "vs_B1_in_A0": _gain(a0, B1, SENTINEL, metric),
                "vs_best_baseline_in_A7": None,
            }
            vb1 = _v(a7, B1, metric)["v"]
            vbp = _v(a7, B1P, metric)["v"]
            best = B1P if vbp < vb1 else B1
            sent[str(rho)]["best_baseline_in_A7"] = best
            sent[str(rho)]["vs_best_baseline_in_A7"] = _gain(a7, best, SENTINEL, metric)
            lev[str(rho)] = {"A7": {p: _v(a7, p, metric) for p in SYSTEMS},
                             "A0": {p: _v(a0, p, metric) for p in SYSTEMS}}
        res["primary"][metric] = prim
        res["sentinel"][metric] = sent
        res["levels"][metric] = lev
        ps = [prim[str(r)]["wild"]["p_abs"] if "wild" in prim[str(r)] else NAN for r in RHOS]
        res["bh"][metric] = {"rhos": list(RHOS), "p_abs": ps, **M.bh(ps, q=C.BH_Q)}
    return res


# ---------------------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------------------

def report(res: dict) -> None:
    print(res["label"])
    ig = res["integrity"]["a0_b1prov_is_b1"]
    print(f"\nintegrity: in A0, B1-prov == B1 on {ig['identical']}/{ig['n_compared']} "
          f"records -> holds={ig['holds']}")
    for p, r in res["integrity"]["a7_vs_a0_by_policy"].items():
        print(f"  A7 vs A0  {p:24} identical {r['identical']:6} differ {r['differ']:6}")
    rp = res["integrity"]["reproduces_p2_a7"]
    print(f"reproduces the P2 A7 records for B1 / Sentinel: holds={rp['holds']}  "
          + "; ".join(f"{k}: {v['identical']}/{v['n_compared']}"
                      for k, v in rp.items() if isinstance(v, dict)))
    print("\nmechanism (A7, per-episode means over held-out x headline Deltas):")
    print(f"{'rho':>5} {'system':>20} {'harm':>8} {'fq':>8} {'t_lost':>8} {'L':>8}")
    for rho in res["rhos"]:
        for pol, m in res["mechanism"]["a7"][str(rho)].items():
            if "refused" in m:
                print(f"{rho:>5} {pol:>20} REFUSED: {m['refused']}")
                continue
            print(f"{rho:>5} {pol:>20} {m['harm_per_ep']:8.4f} {m['fq_per_ep']:8.4f} "
                  f"{m['t_lost_per_ep']:8.4f} {m['L_per_ep']:8.4f}")
    for metric in METRICS:
        print(f"\n=== PRIMARY TEST, V({metric}): B1 -> B1-prov inside A7 "
              f"(Delta in {res['deltas']}) ===")
        print(f"{'rho':>5} {'V(B1)':>8} {'V(B1-prov)':>11} {'abs diff':>9} "
              f"{'[95% CI]':>22} {'p':>7} {'gain %':>8} {'[95% CI]':>20} {'p':>7}")
        for rho in res["rhos"]:
            g = res["primary"][metric].get(str(rho), {})
            if "wild" not in g:
                print(f"{rho:>5} REFUSED: {g.get('refused')}")
                continue
            w = g["wild"]
            print(f"{rho:>5} {w['v_base']:8.4f} {w['v_cand']:11.4f} {w['abs_diff']:9.4f} "
                  f"[{w['abs_lo']:9.4f};{w['abs_hi']:9.4f}] {w['p_abs']:7.4f} "
                  f"{w['gain']:8.2f} [{w['lo']:8.2f};{w['hi']:8.2f}] {w['p_rel']:7.4f}")
        b = res["bh"][metric]
        print(f"BH q={b['q']} m={b['m']} reject={b['reject']} p_adj="
              f"{[round(x, 4) for x in b['p_adj']]}")
        print(f"pairs bootstrap (R6), abs diff: "
              + "; ".join(f"rho {r}: {res['primary'][metric][str(r)]['pairs']['abs_diff']:.4f} "
                          f"p {res['primary'][metric][str(r)]['pairs']['p_abs']:.4f}"
                          for r in res["rhos"]
                          if "pairs" in res["primary"][metric].get(str(r), {})))
        print(f"\n--- conclusion-level, V({metric}): Sentinel's gain ---")
        print(f"{'rho':>5} {'vs B1 (A0)':>22} {'vs B1 (A7)':>22} {'vs B1-prov (A7)':>22} "
              f"{'best baseline in A7':>20}")
        for rho in res["rhos"]:
            s = res["sentinel"][metric].get(str(rho))
            if not s:
                continue
            def f(k):
                g = s[k]
                return f"{g['gain']:7.1f} [{g['lo']:6.1f};{g['hi']:6.1f}]"
            print(f"{rho:>5} {f('vs_B1_in_A0'):>22} {f('vs_B1_in_A7'):>22} "
                  f"{f('vs_B1prov_in_A7'):>22} {s['best_baseline_in_A7']:>20}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check-freeze", action="store_true")
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--jobs", type=int, default=8, help="dev is multiprocess; <= 8 by request")
    ap.add_argument("--workflows", type=int, default=0, help="smoke: the first N dev workflows")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    a = ap.parse_args(argv)
    if not any((a.check_freeze, a.diagnose, a.run, a.analyse)):
        ap.error("pick a mode: --check-freeze / --diagnose / --run / --analyse")
    got = check_freeze()
    print(json.dumps({k: got[k] for k in ("freeze_v3_header", "freeze_base_header",
                                          "v3_manifest_live", "grid_digest_live", "ok")},
                     indent=1))
    if a.diagnose:
        d = diagnose()
        (ROOT / "spikes" / "v3-run" / "a7_diagnosis.json").write_text(
            json.dumps(d, indent=1) + "\n", encoding="utf-8")
    if a.run:
        run(a.jobs, a.workflows, a.out)
    if a.analyse:
        res = analyse(a.out)
        report(res)
        OUT_JSON.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
        print(f"\nwrote {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
