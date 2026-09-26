"""run_draft_eval.py -- draft SS9.4 on the frozen v2 configuration.

Main grid (carrier world): every system of sentinel.REGISTRY x 34 columns (18 scripted +
16 BR) x Delta x detector x rho; chi = 1.34, budget b1, 10 seeds.
Best response (D27): every system x Delta x rho at the headline detector, every feasible
placement, cross-fitted.
Sweeps (headline detector, every rho, held-out class, Delta in {4, 8}): line-8 threshold,
drift match, persistent drift; budget share x chi (EXPLORATORY, D4b) on Delta in {2, 4, 8}.
Secondary world (D29): the four gate baselines on the held-out class.
Summaries (D33): every record file is streamed once into temporary shards and read back one
(rho, setting) cell at a time.  The controls come first; a failed one withholds every other
number (D28).  The eval split runs, and is summarised, only on a clean freeze.

    python3 tools/run_draft_eval.py --jobs 10 --split eval
    python3 tools/run_draft_eval.py --split eval --summarise-only    # + the run's own cut flags
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import inspect
import json
import math
import pathlib
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import attackers_v2 as A
import carrier_policies as CP
import carrier_runner as R
import corpus_v2 as C
import costs
import draft_setup as D
import freeze
import gate_world as G
import metrics as M
import metrics_v2 as MV
import policies as P
import sentinel as S
from tools.select_mixture import make_world

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "spikes" / "v2"
SWEEPERS = ("B3 audit-on-insertion", "B4 audit-on-retrieval")
BUDGET_DELTAS = (2, 4, 8)          # the budget sweep (D4b)
#: D14: every CI resamples metrics_v2's frozen default.  Read off the signature, so the n_boot
#: written beside each CI is the one that ran (D33).
N_BOOT = inspect.signature(MV.gain_ci).parameters["n_boot"].default
HEADLINE_ALPHA = 0.05              # D25: a HEADLINE_RHO point is a one-point endpoint, 95% CI
WITHHELD = "D28: a control failed; no Sentinel number was computed"
#: What the summaries read of a record; every other field is dropped as the file is streamed.
MAIN_FIELDS = ("policy", "attack", "delta", "wf", "repo", "seed", "harm", "detected_at", "iota",
               "n_solved", "t_lost", "false_removed", "benign_inspected")
#: The other record files, sharded by rho: the fields read, and the flag that skips the stage
#: (--skip-sweeps skips D29's world too).
BY_RHO = {"eval-br.jsonl": (("policy", "delta", "v_br"), "skip_br"),
          "sweep-eta.jsonl": (MAIN_FIELDS + ("eta_q",), "skip_sweeps"),
          "sweep-match.jsonl": (MAIN_FIELDS + ("match",), "skip_sweeps"),
          "sweep-persistent-drift.jsonl": (MAIN_FIELDS + ("drift_visible",), "skip_sweeps"),
          "sweep-budget-EXPLORATORY.jsonl": (MAIN_FIELDS + ("chi", "budget"), "skip_sweeps"),
          "eval-gate-world.jsonl": (("policy", "attack", "delta", "wf", "repo", "seed", "harm",
                                     "false_blocks"), "skip_sweeps")}
PRESENT = ("rho_patch", "delta", "setting", "seed")      # distinct values, per file, in `run`


@dataclasses.dataclass(frozen=True)
class Job:
    policy: str
    attack: str
    delta: int
    setting: str
    rho_patch: float
    chi: float = D.HEADLINE_CHI
    budget: D.BudgetSpec = D.BudgetSpec()
    eta_q: float | None = None           # None = the tuned line-8 threshold
    match: float = D.DRIFT_MATCH
    drift_visible: int | None = D.DRIFT_VISIBLE_TASKS


def workflows(split):
    """The eval split for the study; "dev" only for the pipeline smoke (Task 12 Step 2),
    which must never read an eval number before the freeze."""
    dev, ev = C.split(C.make_corpus_v2())
    return {"dev": dev, "eval": ev}[split]


def work(args):
    job, tuned, seeds, split = args
    K = D.target_kappa_for_chi(job.chi)
    world = make_world(job.setting, "nominal", job.rho_patch, job.match, job.drift_visible)
    out = []
    for wf in workflows(split):
        got = A.by_name(job.attack).plan(wf, job.delta)
        if got is None:
            continue
        for s in seeds:
            if not R.survives(wf, got[0], s):
                continue
            pol = S.make_policy(job.policy, budget=job.budget.budget(wf.H), kappa=K, H=wf.H,
                                rng_seed=R.rs_of(wf, s), setting=job.setting, tuned=tuned,
                                rho_patch=job.rho_patch, delta=job.delta,
                                eta_q=job.eta_q, drift_match=job.match,
                                attacked=got[0].carrier)
            r = R.run_carrier(wf, got, pol, world, s, K)
            rec = {k: v for k, v in dataclasses.asdict(r).items() if k != "audits"}
            rec.update({k: v for k, v in dataclasses.asdict(job).items() if k != "budget"})
            rec.update(budget=job.budget.label(), wf=wf.wf_id, repo=wf.repo, seed=s,
                       audits=r.audits)
            out.append(rec)
    return out


def br_work(args):
    """D27: every feasible placement at Delta, cross-fitted per workflow."""
    (policy, delta, setting, rho), tuned, seeds, split = args
    K = D.TARGET_KAPPA_DRAFT
    world = make_world(setting, "nominal", rho)
    rows, repo_of = [], {}
    for wf in workflows(split):
        repo_of[wf.wf_id] = wf.repo
        for ps in A.placements(wf, delta):
            for s in seeds:
                if not R.survives(wf, ps, s):
                    continue
                pol = S.make_policy(policy, budget=D.budget_b1(wf.H), kappa=K, H=wf.H,
                                    rng_seed=R.rs_of(wf, s), setting=setting, tuned=tuned,
                                    rho_patch=rho, delta=delta, attacked=ps.carrier)
                r = R.run_carrier(wf, (ps, "write"), pol, world, s, K)
                rows.append({"wf": wf.wf_id, "placement": (ps.carrier, ps.iota), "seed": s,
                             "harm": r.harm})
    per_wf = {}
    for w in sorted({r["wf"] for r in rows}):          # sorted: key order free of PYTHONHASHSEED
        per_wf[w] = MV.crossfit_value([r for r in rows if r["wf"] == w])["v_br"]
    return {"policy": policy, "delta": delta, "setting": setting, "rho_patch": rho,
            **MV.crossfit_value(rows), "per_wf": per_wf, "repo_of": repo_of}


def gate_work(args):
    (name, attack, delta, rho), seeds, split = args
    world = make_world(D.HEADLINE_DETECTOR, "nominal", rho)
    out = []
    for wf in workflows(split):
        got = A.by_name(attack).plan(wf, delta)
        if got is None:
            continue
        for s in seeds:
            if not R.survives(wf, got[0], s):
                continue
            g = G.run_gate(wf, got, name, world, s, D.budget_b1(wf.H))
            out.append({"policy": name, "attack": attack, "delta": delta, "rho_patch": rho,
                        "wf": wf.wf_id, "repo": wf.repo, "seed": s, "harm": g.harm,
                        "false_blocks": g.false_blocks, "t_lost": g.t_lost, "n_solved": g.n_solved})
    return out


def run(fn, items, jobs, path):
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    with ProcessPoolExecutor(jobs) as ex, open(path, "w") as fh:
        for recs in ex.map(fn, items, chunksize=2):
            for r in (recs if isinstance(recs, list) else [recs]):
                fh.write(json.dumps(r, default=str) + "\n")
                n += 1
    return n


def ref_rho() -> float:
    return D.HEADLINE_RHO if D.HEADLINE_RHO is not None else D.REF_RHO_FALLBACK


class Refused(RuntimeError):
    """The eval split must not be simulated or summarised on this tree (D33)."""


def _clean(header: str) -> bool:
    return header.startswith("freeze: clean") and "PIN CONFLICT" not in header


def refusal(a, header: str) -> str | None:
    """D33: the eval split runs only on a clean freeze (no drift, no pin conflict) and on a rho
    grid that holds the reference rho the controls are read at (D23).  None = go."""
    if a.split != "eval":
        return None
    if not _clean(header):
        return f"the freeze is not clean: {header}"
    if ref_rho() not in a.rhos:
        return f"the reference rho {ref_rho():g} (D23) is not in --rhos {a.rhos}"
    return None


def provenance() -> dict:
    """D33: what the run was made from -- the commit, whether auditgame/ had uncommitted
    changes, and the two tools freeze.SOURCE leaves out (how the world is built, how it is read)."""
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                                  check=True).stdout.rstrip("\n")
        except (OSError, subprocess.CalledProcessError):
            return None
    status = git("status", "--porcelain", "--", ".")
    return {"git_head": git("rev-parse", "--short", "HEAD"),
            "git_clean": None if status is None else status == "",
            "git_dirty": status.splitlines()[:50] if status else [],
            "sha256": {f"tools/{n}": hashlib.sha256((ROOT / "tools" / n).read_bytes()).hexdigest()
                       for n in ("run_draft_eval.py", "select_mixture.py")}}


def pin_records(names) -> pathlib.Path:
    """D33: the raw records are not committed, so this pins them -- sha256, lines and bytes of
    every jsonl the run wrote.  Check with `shasum -a 256 -c eval-records.sha256` inside OUT."""
    rows = []
    for name in names:
        h, lines, size = hashlib.sha256(), 0, 0
        with open(OUT / name, "rb") as fh:
            while chunk := fh.read(1 << 20):
                h.update(chunk)
                lines += chunk.count(b"\n")
                size += len(chunk)
        rows.append((h.hexdigest(), lines, size, name))
    path = OUT / "eval-records.sha256"
    path.write_text("# raw v2 records of this run, not committed (D33); lines  bytes  file:\n"
                    + "".join(f"#   {n}  {b}  {f}\n" for _, n, b, f in rows)
                    + "".join(f"{h}  {f}\n" for h, _, _, f in rows))
    return path


def simulate(a) -> list:
    """Every stage of the run; returns the record files written."""
    tuned, seeds = S.load_tuned(), tuple(a.seeds)
    cols = list(A.SCRIPTED) + [x.name for x in A.br_attacks()]

    grid = [Job(p, c, d, st, rho) for rho in a.rhos
            for st in (D.DETECTORS if (rho == ref_rho() or not a.rho_mid_only) else [D.HEADLINE_DETECTOR])
            for p in S.REGISTRY for c in cols for d in a.deltas]
    print("main", run(work, [(j, tuned, seeds, a.split) for j in grid], a.jobs, OUT / "eval-main.jsonl"), flush=True)
    written = ["eval-main.jsonl"]

    if not a.skip_br:
        br = [((p, d, D.HEADLINE_DETECTOR, rho), tuned, seeds, a.split)
              for p in S.REGISTRY for d in a.deltas for rho in a.rhos]
        print("br", run(br_work, br, a.jobs, OUT / "eval-br.jsonl"), flush=True)
        written.append("eval-br.jsonl")

    if not a.skip_sweeps:
        pair = ("B1 audit-at-commit", "Sentinel-A1")
        ho, hd = A.held_out(), list(D.HEADLINE_DELTAS)
        sweeps = {
            "sweep-eta": [Job("Sentinel-A1", c, d, D.HEADLINE_DETECTOR, rho, eta_q=e)
                          for c in ho for d in hd for rho in a.rhos for e in D.ETA_Q_GRID],
            "sweep-match": [Job(p, c, d, D.HEADLINE_DETECTOR, rho, match=m)
                            for p in pair for c in ho for d in hd for rho in a.rhos for m in (0.0, 0.5, 1.0)],
            "sweep-persistent-drift": [Job(p, c, d, D.HEADLINE_DETECTOR, rho, drift_visible=None)
                                       for p in pair for c in ho for d in hd for rho in a.rhos],
            "sweep-budget-EXPLORATORY": [Job(p, c, d, D.HEADLINE_DETECTOR, rho, chi=chi,
                                             budget=D.BudgetSpec("share", sh))
                                         for p in pair for c in ho for d in BUDGET_DELTAS
                                         for rho in a.rhos for chi in D.CHIS
                                         for sh in (0.25, 0.5, 0.75, 1.0)],
        }
        for name, g in sweeps.items():
            print(name, run(work, [(j, tuned, seeds, a.split) for j in g], a.jobs, OUT / f"{name}.jsonl"), flush=True)
            written.append(f"{name}.jsonl")
        gate = [((n, c, d, rho), seeds, a.split) for n in G.GATE_BASELINES for c in ho for d in hd for rho in a.rhos]
        print("gate", run(gate_work, gate, a.jobs, OUT / "eval-gate-world.jsonl"), flush=True)
        written.append("eval-gate-world.jsonl")
    return written


def main(argv=None):
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(D.SEEDS))        # cut (c)
    ap.add_argument("--deltas", type=int, nargs="+", default=list(D.DELTAS))      # cut (b)
    ap.add_argument("--rhos", type=float, nargs="+", default=list(D.RHO_PATCH_GRID))
    ap.add_argument("--rho-mid-only", action="store_true")                        # cut (a)
    ap.add_argument("--skip-br", action="store_true")                             # smoke only
    ap.add_argument("--skip-sweeps", action="store_true")                         # smoke only; D29's world too
    ap.add_argument("--split", choices=("eval", "dev"), required=True)            # D33: no default; smoke: dev
    ap.add_argument("--summarise-only", action="store_true")                      # recovery: re-read the records
    a = ap.parse_args(argv)
    if a.split == "dev":
        OUT = OUT.parent / "v2-smoke-dev"
    # The manifest is written through the operating installation (freeze.write_operating);
    # a reader compares against the same one, as every v1 tool does.  v2 never reads P.KAPPA.
    costs.install(P)
    header = freeze.header_line()
    print(header, flush=True)
    why = refusal(a, header)
    if why:
        print(f"refused (D33): {why}", flush=True)
        return 2
    for name in S.REGISTRY:
        freeze.require_frozen(name)
    meta = {"split": a.split, "seeds": list(a.seeds), "deltas": list(a.deltas), "rhos": list(a.rhos),
            "rho_mid_only": a.rho_mid_only, "skip_br": a.skip_br, "skip_sweeps": a.skip_sweeps,
            "summarise_only": a.summarise_only, "header_start": header, **provenance()}
    if not a.summarise_only:
        print("records", pin_records(simulate(a)), flush=True)
    try:
        summary = summarise(meta)
    except Refused as e:
        print(f"refused (D33): {e}", flush=True)
        return 2
    return 0 if summary["controls"]["ok"] else 1


# ------------------------------------------------------------------ summaries (D33)

@dataclasses.dataclass
class Records:
    """One record file after its single streamed pass."""
    fields: tuple
    shards: dict                  # cut key -> temporary shard, records in file order
    read: int = 0                 # records in the file
    kept: int = 0                 # records sharded; the rest never feed a number
    present: dict = dataclasses.field(default_factory=dict)   # PRESENT field -> distinct values

    def cell(self, key) -> list:
        """One shard as dicts, repeated strings interned: a cell costs ~0.5 KB a record."""
        if key not in self.shards:
            return []
        with open(self.shards[key]) as fh:
            return [dict(zip(self.fields, [sys.intern(v) if type(v) is str else v
                                           for v in json.loads(line)])) for line in fh]


def _load(name, tmp, cut, fields, attacks=None) -> Records | None:
    """Stream OUT/name once: count every record and note its PRESENT values, and write those whose
    attack is in `attacks` (every one if None), cut to `fields`, to the shard of their `cut` key.
    File order is kept, so every mean sums in the order it always did.  None if the file is
    absent: that stage did not run, and its section says "not run"."""
    path = OUT / name
    if not path.exists():
        return None
    out, seen, fhs = Records(tuple(fields), {}), {f: set() for f in PRESENT}, {}
    with open(path) as fh, contextlib.ExitStack() as stack:
        for line in fh:
            r = json.loads(line)
            out.read += 1
            for f in PRESENT:
                if f in r:
                    seen[f].add(r[f])
            if attacks is not None and r["attack"] not in attacks:
                continue
            k = tuple(r[c] for c in cut)
            if k not in fhs:
                out.shards[k] = tmp / f"{path.stem}.{len(fhs)}"
                fhs[k] = stack.enter_context(open(out.shards[k], "w"))
            fhs[k].write(json.dumps([r[f] for f in fields]) + "\n")
            out.kept += 1
    out.present = {f: sorted(v) for f, v in seen.items() if v}
    return out


def _summarised() -> list:
    """The main-grid columns a summary reads (held-out, development, D18 tuning).  The 16 BR
    columns never feed a number, so they are dropped as the file is streamed."""
    return sorted(set(A.held_out()) | set(A.development()) | set(A.tuning_attack_names()))


def _pick(recs, policies, attacks, deltas) -> list:
    return [r for r in recs if r["policy"] in policies and r["attack"] in attacks and r["delta"] in deltas]


def _n(rs) -> dict:
    """N3/Q6: the workflows, repos and episodes behind a row.  An episode is one (workflow,
    attacker, Delta, seed); every system of a row plays the same ones (planning and survival do
    not depend on the policy)."""
    return {"n_workflows": len({r["wf"] for r in rs}), "n_repos": len({r["repo"] for r in rs}),
            "n_episodes": len({(r["wf"], r["attack"], r["delta"], r["seed"]) for r in rs})}


def _gain(recs, base, cand, attacks, deltas, **kw) -> dict:
    """MV.gain_ci, stamped with its resample count (D14) and its episodes (N3)."""
    return {**MV.gain_ci(recs, base, cand, attacks, deltas, **kw), "n_boot": N_BOOT,
            "n_episodes": _n(_pick(recs, (base, cand), attacks, deltas))["n_episodes"]}


def _vs_best(recs, baselines, cand, attacks, deltas, **kw) -> dict:
    """MV.gain_vs_best (D22), stamped the same way."""
    return {**MV.gain_vs_best(recs, baselines, cand, attacks, deltas, **kw), "n_boot": N_BOOT,
            "n_episodes": _n(_pick(recs, (*baselines, cand), attacks, deltas))["n_episodes"]}


def _as_loss(rs) -> list:
    """D15: each episode's L = harm + lambda_Q Q_false + lambda_T T_lost (metrics.loss and its
    lambdas) in the harm slot, so V's column structure reads it unchanged."""
    return [{**r, "harm": M.loss(r["harm"], r["false_removed"], r["t_lost"])} for r in rs]


def _v_br(by_delta: dict) -> dict:
    """D27: V_BR is the max over the Deltas whose cross-fitted value is finite; a NaN one (e.g.
    one seed leaves nothing to cross-fit) is listed, never compared, so order cannot matter."""
    ok = [v for v in by_delta.values() if math.isfinite(v)]
    return {"v_br_crossfit": max(ok) if ok else float("nan"),
            "v_br_by_delta": {str(d): v for d, v in sorted(by_delta.items())},
            "v_br_nan_deltas": sorted(d for d, v in by_delta.items() if not math.isfinite(v))}


def _per_episode(rs, field) -> float:
    return sum(r[field] for r in rs) / len(rs) if rs else float("nan")


def _table2_row(hl, p, ho, hd, v_brs) -> dict:
    """Table 2 for one system: V and the worst-case L on the same columns (D13, D15), V_BR
    (D27), the side metrics, and N.  `v_brs`: (policy, Delta) -> v_br, None if BR did not run."""
    rs = _pick(hl, [p], ho, hd)
    v = MV.value(MV.harm_table(rs, p, ho, hd))
    row = {"worst_case_harm": v, "worst_case_L": MV.value(MV.harm_table(_as_loss(rs), p, ho, hd))}
    if v_brs is None:
        row.update(v_br_crossfit="not run", exploitability="not run")
    else:
        row.update(_v_br({d: v_brs[(p, d)] for d in hd if (p, d) in v_brs}))
        v_br = row["v_br_crossfit"]
        row["exploitability"] = (v_br - v) if v == v and v_br == v_br else float("nan")
    return {**row, **MV.side(rs, p, ho, hd), **_n(rs)}


def _gate_row(g, p, ho, hd) -> dict:
    rs = [r for r in g if r["policy"] == p]
    return {"worst_case_harm": MV.value(MV.harm_table(rs, p, ho, hd)),
            "false_blocks_per_ep": _per_episode(rs, "false_blocks"), **_n(_pick(rs, [p], ho, hd))}


def denominators(meta: dict) -> dict:
    """N3: per stage, the (workflow, seed) pairs each (attacker, Delta) started from and what left
    them, with why -- recomputed from the split's workflows and the run's seeds.  Planning and
    survival depend on neither the policy nor the world (carrier_runner.survives), so nothing is
    re-simulated.  BR: the (workflow, placement, seed) triples of the D27 menu."""
    wfs, seeds = workflows(meta["split"]), meta["seeds"]
    ho, hd, memo = A.held_out(), list(D.HEADLINE_DELTAS), {}
    kinds = ("pairs", "infeasible", "non_surviving", "used")

    def pair(a, d):
        if (a, d) not in memo:
            c = dict.fromkeys(kinds, 0)
            for wf in wfs:
                got = A.by_name(a).plan(wf, d)
                for s in seeds:
                    c["pairs"] += 1
                    c["infeasible" if got is None else
                      "used" if R.survives(wf, got[0], s) else "non_surviving"] += 1
            memo[(a, d)] = c
        return memo[(a, d)]

    def stage(attacks, deltas):
        cols = {f"{a}@{d}": pair(a, d) for a in attacks for d in deltas}
        return {"total": {k: sum(c[k] for c in cols.values()) for k in kinds}, "columns": cols}

    def menu(d):
        tried = survived = 0
        for wf in wfs:
            for ps in A.placements(wf, d):
                for s in seeds:
                    tried += 1
                    survived += R.survives(wf, ps, s)
        return {"tried": tried, "survived": survived}

    out = {"reasons": {"infeasible": "attacker rule has no placement at this Δ and H",
                       "non_surviving": "N4: the task at σ is not solved in the clean run",
                       "br": "N4: a menu placement whose task at σ is not solved in the clean run "
                             "is dropped (tried - survived)"},
           "workflows": len(wfs), "seeds": list(seeds),
           "main": stage(_summarised(), meta["deltas"]),
           "br": "not run" if meta["skip_br"] else {str(d): menu(d) for d in meta["deltas"]}}
    if meta["skip_sweeps"]:
        out.update(sweeps="not run", sweep_budget="not run", gate_world="not run")
    else:
        out.update(sweeps=stage(ho, hd), sweep_budget=stage(ho, BUDGET_DELTAS), gate_world=stage(ho, hd))
    return out


def summarise(meta: dict) -> dict:
    """The summary step, self-contained: it installs the cost table itself, takes the run's
    parameters from `meta` (split, seeds, deltas, rhos, skip flags; main() builds it) and the
    rest from the records.  The eval split is summarised only on a clean freeze.  Controls
    first (D28): if one fails, eval-summary.json holds run, controls and the withholding and
    nothing else is computed.  Returns the summary written to eval-summary.json."""
    costs.install(P)
    header = freeze.header_line()
    if meta["split"] == "eval" and not _clean(header):
        raise Refused(f"the freeze is no longer clean at summary time: {header}")
    for name in ("eval-summary.json", "eval-sweeps-summary.json"):
        (OUT / name).unlink(missing_ok=True)       # a summary on disk is always this step's
    C.make_corpus_v2()                        # fills C._POOL_OF for the Verified-only row
    ho, dev, tune = A.held_out(), A.development(), A.tuning_attack_names()
    hd = list(D.HEADLINE_DELTAS)
    b1, s = "B1 audit-at-commit", "Sentinel-A1"
    with tempfile.TemporaryDirectory(prefix="run_draft_eval-") as tmp:
        tmp = pathlib.Path(tmp)
        read = {"eval-main.jsonl": _load("eval-main.jsonl", tmp, ("rho_patch", "setting"), MAIN_FIELDS,
                                         attacks=set(_summarised()))}
        for name, (fields, skip) in BY_RHO.items():
            read[name] = None if meta[skip] else _load(name, tmp, ("rho_patch",), fields)
        main = read["eval-main.jsonl"]
        if main is None:
            raise FileNotFoundError(f"{OUT / 'eval-main.jsonl'}: no main grid to summarise")
        rhos, ref = main.present.get("rho_patch", []), ref_rho()
        if ref not in rhos:
            raise ValueError(f"the reference rho {ref:g} (D23) has no main-grid record (rho {rhos})")
        for field, key in (("rho_patch", "rhos"), ("delta", "deltas"), ("seed", "seeds")):
            if set(main.present.get(field, [])) != set(meta[key]):
                raise ValueError(f"eval-main.jsonl holds {field} {main.present.get(field)}, the run "
                                 f"says {meta[key]}: summarise with the arguments that simulated it")
        fam_alpha = D.FAMILY_ALPHA / max(1, len(rhos))
        meta = {**meta, "ref_rho": ref, "headline_rho": D.HEADLINE_RHO, "family_alpha": fam_alpha,
                "n_boot": N_BOOT, "lambda_Q": M.LAMBDA_Q, "lambda_T": M.LAMBDA_T,
                "header_summary": header,
                "records_read": {n: x.read if x else "not run" for n, x in read.items()},
                "records_kept": {n: x.kept for n, x in read.items() if x},
                "present": {n: x.present for n, x in read.items() if x}}

        hl = main.cell((ref, D.HEADLINE_DETECTOR))
        ctrl = MV.controls(
            MV.value(MV.harm_table(hl, S.CONTROL, ho, hd)),
            MV.value(MV.harm_table(hl, b1, ho, [0])),
            {p: MV.value(MV.harm_table(hl, p, ho, [0])) for p in SWEEPERS})
        ctrl.update(_n(_pick(hl, [S.CONTROL], ho, hd) + _pick(hl, [b1, *SWEEPERS], ho, [0])))
        del hl
        if not ctrl["ok"]:
            summary = {"run": meta, "controls": ctrl, "withheld": WITHHELD}
            _write(OUT / "eval-summary.json", summary)
            print("controls FAILED (D28): Sentinel numbers withheld -- find the fault, fix, re-run", flush=True)
            return summary
        print("controls ok", flush=True)

        summary = {"run": meta, "freeze": header, "controls": ctrl, "family_alpha": fam_alpha,
                   "curve_rho": {}, "curve_rho_vs_best": {}, "by_rho": {}}
        br, b1_mid = read["eval-br.jsonl"], {}
        for rho in rhos:
            key = f"{rho:g}"
            hl = main.cell((rho, D.HEADLINE_DETECTOR))
            alpha = HEADLINE_ALPHA if D.HEADLINE_RHO is not None and rho == D.HEADLINE_RHO else fam_alpha
            g = _gain(hl, b1, s, ho, hd, alpha=alpha)
            g["meets_margin"] = bool(g["rel_reliable"] and g["lo"] >= D.MARGIN_PCT)
            summary["curve_rho"][key] = g
            summary["curve_rho_vs_best"][key] = _vs_best(hl, list(CP.BASELINES), s, ho, hd, alpha=fam_alpha)
            v_brs = None if br is None else {(x["policy"], x["delta"]): x["v_br"] for x in br.cell((rho,))}
            held = _gain(hl, b1, s, ho, hd)        # the transfer rows and rq4's mid read the same cell
            by = summary["by_rho"][key] = {
                "table2": {p: _table2_row(hl, p, ho, hd, v_brs) for p in S.REGISTRY},
                "table3_ablations": {p: _gain(hl, p, s, ho, hd) for p in S.VARIANTS if p != s},
                "figure3_gain_by_delta": {str(d): _gain(hl, b1, s, ho, [d])
                                          for d in sorted({r["delta"] for r in hl})},
                "transfer_dev_vs_heldout": {"dev_attackers": _gain(hl, b1, s, dev, hd),
                                            "heldout_attackers": held},
                "transfer_tuning_vs_heldout": {"tuning_attackers": _gain(hl, b1, s, tune, hd),
                                               "heldout_attackers": held},
                "verified_only": _gain([r for r in hl if C._POOL_OF.get(r["repo"]) == "verified"],
                                       b1, s, ho, hd),
            }
            b1_mid[rho] = _pick(hl, [b1], ho, hd)
            del hl                                 # one (rho, setting) cell in memory at a time
            settings = sorted(st for r_, st in main.shards if r_ == rho)
            by["rq4_detectors"] = {st: held if st == D.HEADLINE_DETECTOR else
                                   _gain(main.cell((rho, st)), b1, s, ho, hd) for st in settings}
        gate = read["eval-gate-world.jsonl"]
        if gate is None:
            summary["gate_world"] = "not run"
        else:
            summary["gate_world"] = {}
            for (rho,) in sorted(gate.shards):
                g = gate.cell((rho,))
                summary["gate_world"][f"{rho:g}"] = {p: _gate_row(g, p, ho, hd) for p in G.GATE_BASELINES}
        summary["denominators"] = denominators(meta)
        held_keys = set().union(*(A.behavior_keys(A.SCRIPTED[n]) for n in ho))
        summary["transfer_note"] = {
            "dev_attackers_with_heldout_keys": [n for n in dev if A.behavior_keys(A.by_name(n)) & held_keys],
            "note": "D18: these development attackers can realise a held-out behaviour key (k, iota "
                    "rule, eps), so transfer_dev_vs_heldout is not a clean transfer; "
                    "transfer_tuning_vs_heldout reads the D18 tuning columns instead"}
        _write(OUT / "eval-summary.json", summary)
        print("curve_rho", json.dumps({k: {x: v[x] for x in ("gain", "lo", "abs_diff", "rel_reliable", "meets_margin")}
                                       for k, v in summary["curve_rho"].items()}), flush=True)
        summarise_sweeps(meta, read, b1_mid)
    return summary


def summarise_sweeps(meta, read, b1_mid) -> dict:
    """The sweeps, read on the held-out class at Delta in {4, 8} (budget: {2, 4, 8}), per rho.
    Line 8: Sentinel's worst-case harm and FQ% at every eta_Q of the grid (SS11: "as quarantine
    becomes cheap"), and its gain_ci over B1: B1 has no line 8, so the main grid's B1 records
    at the same cell (`b1_mid`) pair with every eta, on the Deltas both ran.  Budget x chi is
    EXPLORATORY (D4b); each entry carries range/kbar beside the 2*MAD key (D2).  `read`: the
    files summarise() streamed."""
    ho, hd = A.held_out(), list(D.HEADLINE_DELTAS)
    b1, s = "B1 audit-at-commit", "Sentinel-A1"
    paired = [d for d in hd if d in meta["deltas"]]
    out = {"run": meta}
    eta = read["sweep-eta.jsonl"]
    if eta is None:
        out["eta"] = "not run"
    else:
        out["eta"] = {}
        for (rho,) in sorted(eta.shards):
            rs_all = eta.cell((rho,))
            for e in sorted({r["eta_q"] for r in rs_all}):
                rs = [r for r in rs_all if r["eta_q"] == e]
                out["eta"].setdefault(f"{rho:g}", {})[f"{e:g}"] = {
                    "worst_case_harm": MV.value(MV.harm_table(rs, s, ho, hd)), **MV.side(rs, s, ho, hd),
                    **_n(_pick(rs, [s], ho, hd)),
                    "gain_ci": {**_gain(b1_mid.get(rho, []) + rs, b1, s, ho, paired), "deltas": paired}}
    for name, key in (("sweep-match.jsonl", "match"), ("sweep-persistent-drift.jsonl", "drift_visible")):
        recs = read[name]
        if recs is None:
            out[key] = "not run"
            continue
        out[key] = {}
        for (rho,) in sorted(recs.shards):
            rs_all = recs.cell((rho,))
            for v in sorted({r[key] for r in rs_all}, key=str):
                level = "persistent" if v is None else str(v)      # drift_visible None: never fades (D6)
                out[key].setdefault(f"{rho:g}", {})[level] = _gain([r for r in rs_all if r[key] == v],
                                                                   b1, s, ho, hd)
    bud = read["sweep-budget-EXPLORATORY.jsonl"]
    if bud is None:
        out["budget_EXPLORATORY"] = "not run"
    else:
        out["budget_EXPLORATORY"] = {}
        for (rho,) in sorted(bud.shards):
            by = {}
            for r in bud.cell((rho,)):
                by.setdefault((r["chi"], r["budget"], r["delta"]), []).append(r)
            chis, shares, deltas = (sorted({k[i] for k in by}) for i in range(3))
            for chi in chis:
                chi_range = round(D.chi_range(D.target_kappa_for_chi(chi)), 4)
                for sh in shares:
                    for d in deltas:
                        out["budget_EXPLORATORY"].setdefault(f"{rho:g}", {}).setdefault(
                            f"chi={chi:g}", {}).setdefault(sh, {})[str(d)] = {
                            **_gain(by.get((chi, sh, d), []), b1, s, ho, [d]), "chi_range": chi_range}
    _write(OUT / "eval-sweeps-summary.json", out)
    return out


def _finite(x):
    """NaN and +-inf become null: the summaries are strict JSON."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_finite(v) for v in x]
    return x


def _write(path, obj) -> None:
    path.write_text(json.dumps(_finite(obj), indent=2, allow_nan=False, ensure_ascii=False, default=str),
                    encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
