#!/usr/bin/env python3
"""tools/v3_run.py -- run the v3 grid (v3/grid.py) on dev, or on eval once unsealed (T22).

    cd auditgame
    ../.venv/bin/python tools/v3_run.py --split dev --count             # episodes per block
    ../.venv/bin/python tools/v3_run.py --split dev --seeds 1 --workflows 5 --blocks main
    ../.venv/bin/python tools/v3_run.py --split eval                    # P5 only, by the user

`--split` has no default (D33).  Order of a run, each step refusing before the next:

  1. the freeze line: freeze_v3.header_line() (v3, D35 and the v2 base, under
     costs.install as every v2 run reads it);
  2. eval only: seal.unseal(run_meta) -- the Gate-4 file, clean freezes, matching digests, a
     clean auditgame/ tree; any miss is SealedSplit and the run stops with exit 2 BEFORE a
     workflow is loaded.  Every attempt is logged by seal (frozen/v3-unseal-log.jsonl);
  3. freeze_v3.require_frozen for every system the selected grid builds (draft S7: "the
     evaluation harness refuses to run a policy whose hash is not in the frozen manifest");
  4. the chains of v3/grid.py: one sequence per (unit, seed), the workflows of the split in
     pinned order (C12: line 1's post-mortems follow that order), one record file per block;
  5. every record is validated (validate_record: it carries every WorldV3 and Cell field of
     its chain, both ids, and the split), then the files are pinned by sha256 (pin_records,
     D33) -- the raw records are not committed;
  6. the summary reads the D28 controls first (metrics.Readout) and refuses eval records on
     an unclean freeze (seal.refusal).

THE RUNNER SEAM.  The ONE call into the episode loop is `episode_runner()`, which returns
`run_chain` (T6's runner, T10's sequence, T20's stage world, T12's rollout driver):
  * the workflows of the split run in T10's pinned order (sequence.workflow_order, C12),
    after v2's N4 survives filter; `order` is the position among the kept workflows;
  * a held-out chain of a system with line 1 (the Sentinel class, T15) runs through
    sequence.run_sequence: the post-mortems of the earlier workflows of the same (cell,
    system, column, seed) are carried, line 1's arm is read off the name (delta_hat.
    arm_of), the oracle arm is told each placement's true Delta, and every record is
    checked against its step (Delta-hat, n_incidents_seen);
  * every other chain (baselines, and every best-response chain) runs the same order
    directly: a baseline has no line 1 (its record carries delta_hat None, which
    run_sequence's step check refuses), and a best-response chain enumerates a MENU of
    placements per workflow, so no single post-mortem per workflow exists -- its episodes
    get no post-mortem (Delta-hat is line 1's prior), as before (declared, L1);
  * the episode is runner.Episode in the carrier reading, stage_world.StageEpisode in the
    stage reading (a system with its own lines 8-9 -- the Sentinel class -- keeps them:
    keep_quarantine=True), and in the rollout world (world.line5 = "rollout",
    Sentinel-rollout) it is driven by rollout.drive(ep, ep.policy.source), which binds the
    state before every task.
Everything else is coded against api.EpisodeRecord.  Systems enter through
`policy_factory`: baselines (T8), the block schedule (T16) and T15's V3_REGISTRY (the
Sentinel class, its ablations, the line-1 arms and Sentinel-rollout; every factory is
bound to the placement with `for_placement`, so the oracle arm gets the true Delta, also
in the attacker-chooses-Delta column).  B7 (T21) raises PolicyMissing until it lands, and
a run naming it stops with exit 3 before anything is simulated.  Sentinel's parts (T14's
line-5 table, T18's tuned tau / eta_Q) are checked with sentinel.check_ready before
anything is simulated; a missing part stops the run with exit 3 and names it.

DEV SMOKE PARTS.  `--stub-parts` (dev only; refused with eval) runs the Sentinel class on
sentinel.stub_parts(): the StubTable and placeholder tau / eta_Q.  Its numbers are not
results; the summary says so ("parts": "stub") and the default output is dev-stub/.

EVAL TOKEN.  T6's runner takes the seal.Unsealed token; a token is valid only in the
process that unsealed, so an eval run simulates in-process (--jobs is ignored there).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from v3 import api                                            # noqa: E402
from v3 import config as C                                    # noqa: E402
from v3 import corpus as K                                    # noqa: E402
from v3 import freeze_v3 as F                                 # noqa: E402
from v3 import grid as G                                      # noqa: E402
from v3 import seal                                           # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent          # auditgame/
OUT_ROOT = ROOT / "spikes" / "v3-run"
SPLITS = ("dev", "eval")
EXIT_REFUSED = 2
EXIT_NO_RUNNER = 3


class Refused(RuntimeError):
    """The eval split must not be simulated or summarised on this tree (D33, plan S6)."""


class RunnerMissing(RuntimeError):
    """T6's runner / T10's sequence is not on this branch."""


class PolicyMissing(RuntimeError):
    """The system's owning task has not landed its factory yet."""


# ---------------------------------------------------------------------------------------
# The seams
# ---------------------------------------------------------------------------------------


def episode_runner():
    """THE one call into the episode loop: run_chain(chain, workflows, factory_of, split,
    token=None) -> list[api.EpisodeRecord] (module docstring)."""
    try:
        from v3 import runner  # noqa: F401  (T6)
        from v3 import sequence  # noqa: F401  (T10)
    except ImportError as e:
        raise RunnerMissing(f"needs T6 (v3/runner.py) and T10 (v3/sequence.py): {e}") from e
    return run_chain


def _placements(chain: G.Chain, wf) -> list:
    """(attack column, placement, best_response) of one workflow in a chain.  A held-out
    rule with no placement, or a Delta past the horizon, yields nothing (N3)."""
    from v3 import attackers as AT
    u = chain.unit
    if u.is_br:
        if u.cell.delta == C.DELTA_ATTACKER:
            deltas = [dc.delta for dc in AT.attacker_delta_menu() if dc.delta is not None]
        else:
            deltas = [u.cell.delta]
        return [(G.BR_COLUMN, pl, True) for d in deltas if wf.H >= d + 1
                for pl in AT.br_menu(wf, d, u.world)]
    if wf.H < u.cell.delta + 1:
        return []
    pl = AT.by_name(u.column).plan(wf, u.cell.delta, u.world)
    return [] if pl is None else [(u.column, pl, False)]


def schedule(chain: G.Chain, workflows: list) -> list:
    """[(wf, [(column, placement, best_response), ...])] in T10's pinned order (C12), the
    workflows with no surviving placement left out (N3; v2's N4 survives filter: the sigma
    task is solved in the clean run, P0 GD 3 counts with it)."""
    import carrier_runner as CR
    from v3 import sequence as SQ
    by_id = {wf.wf_id: wf for wf in workflows}
    out = []
    for wf_id in SQ.workflow_order(by_id):
        wf = by_id[wf_id]
        kept = [x for x in _placements(chain, wf) if CR.survives(wf, x[1], chain.seed)]
        if kept:
            out.append((wf, kept))
    return out


def has_line1(system: str) -> bool:
    """A system with Algorithm 1's line 1 (T15's V3_REGISTRY): its chain carries the
    post-mortems through sequence.run_sequence."""
    try:
        from v3 import sentinel as S
    except ImportError:
        return False
    return system in S.V3_REGISTRY


def episode(chain: G.Chain, wf, pl, factory, split: str, token=None, **kw):
    """One episode of the chain's world (module docstring): runner.Episode, or the stage
    world's StageEpisode; driven by rollout.drive in the rollout world."""
    from v3 import stage_world as SW
    u = chain.unit
    ep = SW.episode_in_world(wf, pl, factory, u.world, u.cell, chain.seed,
                             keep_quarantine=has_line1(u.system), split=split, token=token,
                             **kw)
    if u.world.line5 == "rollout":
        src = getattr(ep.policy, "source", None)
        if src is None or getattr(src, "name", None) != "rollout":
            raise ValueError(f"{u.system!r} in the rollout world has no rollout source")
        from v3 import rollout as RO
        return RO.drive(ep, src)
    return ep.run()


def _run_sequenced(chain: G.Chain, sched: list, factory_of, split: str, token=None) -> list:
    """A held-out chain of a line-1 system through T10's sequence.run_sequence."""
    from v3 import budget as BU
    from v3 import delta_hat as DH
    from v3 import sequence as SQ
    u = chain.unit
    arm = DH.arm_of(u.system) or DH.ARM_POSTMORTEM
    base = u.system[: len(u.system) - len(DH.system_name("", arm))]
    by_id = {wf.wf_id: (wf, kept[0][1]) for wf, kept in sched}
    man = SQ.order_manifest(list(by_id), split=split)
    key = DH.HistoryKey(C.cell_id(u.cell), base, u.column, chain.seed)

    def run_one(step):
        wf, pl = by_id[step.wf_id]
        eo = episode(chain, wf, pl, factory_of(pl), split, token, order=step.order,
                     attack=u.column, best_response=False, postmortems=step.postmortems)
        return eo.record, eo.postmortem

    true_delta = ((lambda wf_id: int(by_id[wf_id][1].delta)) if arm == DH.ARM_ORACLE
                  else None)
    res = SQ.run_sequence(key, man, run_one, arm=arm, true_delta=true_delta,
                          kappa=BU.cell_kappa(u.cell))
    return list(res.records)


def run_chain(chain: G.Chain, workflows: list, factory_of, split: str, token=None) -> list:
    """One chain (module docstring): the workflows in pinned order, the survivors only."""
    u = chain.unit
    workflows = G.chain_workflows(u, workflows, split)      # headline rollout: 27/09 subsample
    sched = schedule(chain, workflows)
    if not u.is_br and has_line1(u.system):
        return _run_sequenced(chain, sched, factory_of, split, token)
    out, pms = [], []
    for order, (wf, kept) in enumerate(sched):
        for col, pl, br in kept:
            eo = episode(chain, wf, pl, factory_of(pl), split, token, order=order,
                         attack=col, best_response=br, postmortems=tuple(pms))
            out.append(eo.record)
            if not br:
                pms.append(eo.postmortem)
    return out


def policy_factory(name: str, parts=None):
    """System name -> factory_of(placement) -> api.PolicyFactory.  Baselines (T8; the
    Oracle is told the placement's carriers, D28), the block schedule (T16) and T15's
    V3_REGISTRY (bound to the placement: `for_placement` gives the oracle-Delta arm the
    true Delta).  `parts` (sentinel.Parts) binds the Sentinel class to explicit parts (the
    dev smoke's stub); None = the frozen parts, resolved at the first episode.  B7 (T21)
    is not yet here."""
    from v3 import baselines as BL
    from v3 import budget as BU
    if name == BL.OracleControl.name:
        return lambda pl: BL.factory(name, attacked=tuple(pl.k))
    if name in BL.ALL:
        f = BL.factory(name)
        return lambda pl: f
    if name == BU.BlockSchedule.name:
        return lambda pl: BU.block_schedule_factory
    try:
        from v3 import sentinel as S  # T15
    except ImportError as e:
        raise PolicyMissing(f"{name!r}: needs its owning task (T15 v3/sentinel.py "
                            f"V3_REGISTRY; B7: T21)") from e
    reg = getattr(S, "V3_REGISTRY", {})
    if name not in reg:
        raise PolicyMissing(f"{name!r} is not in v3.sentinel.V3_REGISTRY")
    f = reg[name] if parts is None else reg[name].with_parts(parts)
    return f.for_placement


def sentinel_parts(stub: bool):
    """The parts the Sentinel class runs on: None (the frozen parts) or, for a dev smoke,
    sentinel.stub_parts()."""
    if not stub:
        return None
    from v3 import sentinel as S
    return S.stub_parts()


def missing_parts(systems, parts=None) -> list:
    """sentinel.check_ready over the Sentinel-class systems among `systems` (empty = ready;
    no Sentinel-class system = nothing to check)."""
    names = [n for n in systems if has_line1(n)]
    if not names:
        return []
    from v3 import sentinel as S
    return S.check_ready(names, parts)


# ---------------------------------------------------------------------------------------
# Refusals, provenance, pins (the D33 pattern of run_draft_eval, rewritten for v3)
# ---------------------------------------------------------------------------------------


def refusal(split: str, header: str) -> str | None:
    """D33 for summaries: eval records are read only on a strictly clean v3 freeze line
    (v3, D35 and v2 clean).  None = go."""
    if split != "eval":
        return None
    if not F.clean(header):
        return f"the v3 freeze is not clean: {header}"
    return seal.refusal(split, header)


def provenance() -> dict:
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
            "v3_manifest_live": F.digest(),
            "grid_digest": G.definition_digest(),
            "sha256": {"tools/v3_run.py": hashlib.sha256(pathlib.Path(__file__)
                                                         .read_bytes()).hexdigest()}}


def pin_records(out: pathlib.Path, names) -> pathlib.Path:
    """D33: sha256, lines and bytes of every record file; check with
    `shasum -a 256 -c records.sha256` inside `out`."""
    rows = []
    for name in names:
        h, lines, size = hashlib.sha256(), 0, 0
        with open(out / name, "rb") as fh:
            while chunk := fh.read(1 << 20):
                h.update(chunk)
                lines += chunk.count(b"\n")
                size += len(chunk)
        rows.append((h.hexdigest(), lines, size, name))
    path = out / "records.sha256"
    path.write_text("# raw v3 records of this run, not committed (D33); lines  bytes  file:\n"
                    + "".join(f"#   {n}  {b}  {f}\n" for _, n, b, f in rows)
                    + "".join(f"{h}  {f}\n" for h, _, _, f in rows), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------------------


def validate_record(rec: api.EpisodeRecord, chain: G.Chain, split: str) -> None:
    """A record must carry every switch of its chain (plan S4): every WorldV3 and Cell
    field, both ids, the split, the system, the seed; the attack column unless BR."""
    u = chain.unit
    want = C.identity(u.world, u.cell)
    bad = []
    if rec.split != split:
        bad.append(f"split {rec.split!r} != {split!r}")
    for key in ("world", "cell"):
        got = getattr(rec, key)
        missing = [f for f in want[key] if f not in got]
        if missing:
            bad.append(f"{key} lacks {missing}")
        elif got != want[key]:
            bad.append(f"{key} {got} != {want[key]}")
    for key in ("world_id", "cell_id"):
        if getattr(rec, key) != want[key]:
            bad.append(f"{key} {getattr(rec, key)} != {want[key]}")
    if rec.delta != u.cell.delta and u.cell.delta != C.DELTA_ATTACKER:
        bad.append(f"delta {rec.delta!r} != cell delta {u.cell.delta!r}")
    if rec.policy != u.system:
        bad.append(f"policy {rec.policy!r} != {u.system!r}")
    if rec.seed != chain.seed:
        bad.append(f"seed {rec.seed} != {chain.seed}")
    if not u.is_br and rec.attack != u.column:
        bad.append(f"attack {rec.attack!r} != {u.column!r}")
    if u.is_br and rec.placement is None:
        bad.append("a best-response record has no placement")
    if bad:
        raise ValueError(f"record of {u.block}/{u.system}/{u.column}/seed {chain.seed}: "
                         + "; ".join(bad))


def _work(args) -> list:
    chain, workflows, split, stub = args
    recs = episode_runner()(chain, workflows,
                            policy_factory(chain.unit.system, sentinel_parts(stub)), split)
    for r in recs:
        validate_record(r, chain, split)
    return [r.to_json() for r in recs]


def simulate(chains: list, workflows: list, split: str, out: pathlib.Path, jobs: int = 1,
             run_chain=None, token=None, stub: bool = False) -> list:
    """Run every chain; one jsonl per block in `out`.  `run_chain` overrides the seam (the
    tests pass a stub).  jobs > 1 runs dev chains in worker processes.  `stub` (dev only)
    runs the Sentinel class on sentinel.stub_parts()."""
    if stub and split != "dev":
        raise Refused("stub parts are a dev smoke only")
    parts = sentinel_parts(stub)
    out.mkdir(parents=True, exist_ok=True)
    by_block: dict = {}
    for ch in chains:
        by_block.setdefault(ch.unit.block, []).append(ch)
    in_process = run_chain is not None or jobs <= 1 or token is not None
    written = []
    for block, chs in by_block.items():
        name = block.replace(":", "_") + ".jsonl"
        with open(out / name, "w", encoding="utf-8") as fh:
            if in_process:
                rc = run_chain or episode_runner()
                kw = {} if token is None else {"token": token}
                for ch in chs:
                    for r in rc(ch, workflows, policy_factory(ch.unit.system, parts), split,
                                **kw):
                        validate_record(r, ch, split)
                        fh.write(r.to_json() + "\n")
            else:
                with ProcessPoolExecutor(jobs) as ex:
                    for lines in ex.map(_work, [(ch, workflows, split, stub) for ch in chs],
                                        chunksize=4):
                        fh.writelines(line + "\n" for line in lines)
        written.append(name)
    return written


def load_records(path: pathlib.Path) -> list:
    with open(path, encoding="utf-8") as fh:
        return [api.EpisodeRecord.from_dict(json.loads(line)) for line in fh if line.strip()]


def summarise(out: pathlib.Path, split: str, header: str) -> dict:
    """Controls first (D28), on the main block's held-out columns, one cell per rho at the
    primary chi and detector: the Oracle at the headline Deltas and the Delta = 0 sweepers
    against B1.  Refuses eval records on an unclean freeze.  The Table 2 / Table 3
    read-out is T17's scorecard over these files, after the controls."""
    why = refusal(split, header)
    if why:
        raise Refused(why)
    from v3 import baselines as BL
    from v3 import metrics as M
    main = out / "main.jsonl"
    if not main.exists():
        return {"split": split, "header": header, "controls": None,
                "note": "no main block in this run"}
    recs = [r.to_dict() for r in load_records(main)]
    per_rho = {}
    for rho in C.RHO_GRID:
        sel = [r for r in recs if r["cell"]["rho"] == rho
               and r["cell"]["chi"] == C.CHI_PRIMARY and r["cell"]["dprime"] == C.DPRIME_PRIMARY]
        per_rho[str(rho)] = M.Readout(sel).controls(
            BL.OracleControl.name, BL.B1AuditAtCommit.name, BL.SWEEP_ONLY, list(G.HELD_OUT))
    ok = all(c["ok"] for c in per_rho.values())
    return {"split": split, "header": header, "controls": {"ok": ok, "by_rho": per_rho}}


# ---------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------


def workflows_for(a, token=None) -> list:
    if a.split == "eval":
        return seal.eval_workflows(token, "primary")
    wfs = K.dev_workflows()
    return wfs[: a.workflows] if a.workflows else wfs


def main(argv=None, run_chain=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split", choices=SPLITS, required=True)          # D33: no default
    ap.add_argument("--blocks", nargs="+", default=None,
                    help="block names of v3/grid.py (default: every core block)")
    ap.add_argument("--systems", nargs="+", default=None)
    ap.add_argument("--seeds", type=int, default=len(C.SEEDS),
                    help="the first N seeds of config.SEEDS (smoke: 1)")
    ap.add_argument("--workflows", type=int, default=0, help="dev only: the first N")
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--count", action="store_true", help="print the grid counts and stop")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--stub-parts", action="store_true",
                    help="DEV SMOKE ONLY: the Sentinel class on sentinel.stub_parts() (the "
                         "StubTable, placeholder tau / eta_Q); no number is a result")
    ap.add_argument("--headline", action="store_true",
                    help="dev only: keep only headline cells (chi = CHI_PRIMARY, dprime = "
                         "DPRIME_PRIMARY); matches a headline-scoped line-5 table. A strict "
                         "subset of the chains -- no number changes, only which cells run.")
    a = ap.parse_args(argv)
    if a.split == "eval" and a.workflows:
        ap.error("--workflows cuts dev only: an eval run is the whole pinned split")
    if a.split == "eval" and a.headline:
        ap.error("--headline cuts dev only: an eval run is the whole pinned split")
    if a.split == "eval" and a.stub_parts:
        ap.error("--stub-parts is a dev smoke only: an eval run reads the frozen parts")

    header = F.header_line()
    print(header, flush=True)
    if a.count:
        for b, row in G.count("dev" if a.split == "dev" else "primary").items():
            print(f"{b:40} units {row['units']:6}  episodes {row['episodes']:14,.0f}"
                  f"  {'core' if row['core'] else 'outside core'}")
        return 0

    run_meta = {"split": a.split, "tool": "tools/v3_run.py", "blocks": a.blocks,
                "systems": a.systems, "seeds": a.seeds}
    if a.stub_parts:
        run_meta["parts"] = "stub"
        print("DEV SMOKE ONLY: Sentinel on stub parts (StubTable, placeholder tau / eta_Q) "
              "-- no number here is a result", flush=True)
    token = None
    if a.split == "eval":
        try:
            token = seal.unseal(run_meta)
        except seal.SealedSplit as e:
            print(f"refused (plan S6, D33): {e}", flush=True)
            return EXIT_REFUSED

    chains = G.chains(a.blocks, seeds=C.SEEDS[: a.seeds], systems=a.systems,
                      core_only=a.blocks is None)
    if a.headline:
        chains = [ch for ch in chains if ch.unit.cell.chi == C.CHI_PRIMARY
                  and ch.unit.cell.dprime == C.DPRIME_PRIMARY]
        print(f"--headline: {len(chains)} chains at cells chi={C.CHI_PRIMARY} "
              f"dprime={C.DPRIME_PRIMARY}", flush=True)
    for name in sorted({ch.unit.system for ch in chains}):
        F.require_frozen(name)
    try:
        for name in sorted({ch.unit.system for ch in chains}):
            policy_factory(name)
    except PolicyMissing as e:
        print(f"not run: {e}", flush=True)
        return EXIT_NO_RUNNER
    parts = sentinel_parts(a.stub_parts)
    missing = missing_parts(sorted({ch.unit.system for ch in chains}), parts)
    if missing:
        print(f"not run: Sentinel's parts are missing: {'; '.join(missing)} (sentinel."
              f"check_ready; a dev smoke may pass --stub-parts)", flush=True)
        return EXIT_NO_RUNNER
    if run_chain is None:
        try:
            episode_runner()
        except RunnerMissing as e:
            print(f"not run: {e}", flush=True)
            return EXIT_NO_RUNNER

    out = a.out or OUT_ROOT / (a.split + ("-stub" if a.stub_parts else ""))
    wfs = workflows_for(a, token)
    meta = {**run_meta, "header_start": header, "n_chains": len(chains),
            "n_workflows": len(wfs), "parts": "stub" if a.stub_parts else "frozen",
            **provenance()}
    written = simulate(chains, wfs, a.split, out, a.jobs, run_chain=run_chain, token=token,
                       stub=a.stub_parts)
    print("records", pin_records(out, written), flush=True)
    try:
        summary = summarise(out, a.split, F.header_line())
    except Refused as e:
        print(f"refused (D33): {e}", flush=True)
        return EXIT_REFUSED
    (out / "summary.json").write_text(json.dumps({"meta": meta, **summary}, indent=1,
                                                 default=str) + "\n", encoding="utf-8")
    ctl = summary.get("controls")
    return 0 if ctl is None or ctl.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
