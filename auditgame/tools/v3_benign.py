#!/usr/bin/env python3
"""tools/v3_benign.py -- build the benign changes on dev and run the 4-feature check (P3, T24).

Writes the manifest reference/v3_benign.json (GENERATED, never hand-edited;
tests/v3/test_s8_benign.py checks it against the live modules) and prints the verdict:
"đạt" when the mean CI95 upper bound over v2's 20 split seeds is <= 0.56, else "không đạt".
The ceiling is read from analysis/gate2_v2.record(); nothing here can move it.

    cd auditgame
    ../.venv/bin/python tools/v3_benign.py            # measure, print, do not write
    ../.venv/bin/python tools/v3_benign.py --write    # also write the manifest

Dev only: v3.benign reads v3.corpus.dev_workflows() and nothing else.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build  # noqa: E402
from v3 import benign as V  # noqa: E402
from v3 import payload as P  # noqa: E402

MANIFEST = ROOT / "reference" / "v3_benign.json"
MODULE = ROOT / "v3" / "benign.py"
PAYLOAD_MODULE = ROOT / "v3" / "payload.py"


def module_sha(path: pathlib.Path = MODULE) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol() -> dict:
    return dict(
        n_benign_draft=V.N_BENIGN_DRAFT, per_event=V.V3_PER_EVENT, per_event_v2=V.PER_EVENT,
        deviation_ref=V.DEVIATION_REF,
        events_per_delta_rule="min over Delta of candidates[Delta] // per_event, balanced",
        carrier=V.CARRIER,
        seed=V.SEED, epsilon=V.EPSILON, deltas=list(V.DELTAS), features=list(V.FEATURES),
        v2_features=list(V.V2_FEATURES), control_kind="drift",
        diagnostic_control_kind="v2-notes", ceiling=V.CEILING, criterion=V.CRITERION,
        split_seeds=list(V.SPLIT_SEEDS), test_fraction=V.TEST_FRACTION,
        split="dev (v3.corpus.dev_workflows, 100 v2 workflows)",
        payload_length_rule=P.LENGTH_RULE, payload_length_v2=build.PAYLOAD_LENGTH,
        payload_length_background="len(content) of every drift change of the pool "
                                  "(v3.benign.length_background: forced drift on memory "
                                  "over every dev workflow)",
        source="v3/benign.py", source_sha256=module_sha(),
        payload_source="v3/payload.py", payload_source_sha256=module_sha(PAYLOAD_MODULE))


def corpus_record(events: list, runs, dropped: list) -> dict:
    contents = [c.item.content for ev in events for c in ev.controls]
    return dict(
        digest=V.corpus_digest(events), n_events=len(events), n_benign=len(contents),
        n_distinct_benign=len(set(contents)),
        dev_workflows=len(runs.workflows),
        workflows_hosting=len({ev.wf_id for ev in events}),
        per_delta={str(d): sum(1 for ev in events if ev.delta == d) for d in V.DELTAS},
        per_repo=dict(sorted(collections.Counter(ev.repo for ev in events).items())),
        own_task_controls=sum(1 for ev in events for c in ev.controls
                              if c.wf_id == ev.wf_id and c.t == ev.iota),
        events_per_delta=V.events_per_delta(runs),
        dropped=len(dropped), dropped_reasons=[list(d) for d in dropped],
        candidates={str(d): len(V.candidates(runs, d)) for d in V.DELTAS},
        pool_per_kind={k: sum(len(v) for (kk, _), v in runs.pools.items() if kk == k)
                       for k in V.CONTROL_KINDS},
        payload_length_background=P.length_stats(runs.lengths),
        payload_length_drawn=P.length_stats([ev.length for ev in events]),
        payload_length_reasons=[[ev.wf_id, ev.delta, ev.iota, ev.sigma, ev.length,
                                 ev.length_reason] for ev in events
                                if ev.length_reason is not None])


def _summary(s: dict) -> dict:
    keys = ("k", "auc_mean", "auc_median", "auc_min", "auc_max", "lo_mean", "hi_mean",
            "hi_min", "hi_max", "clear", "weights_mean")
    out = {k: (round(s[k], 4) if isinstance(s[k], float) else s[k]) for k in keys if k in s}
    out["per_seed"] = {str(k): list(v) for k, v in s["per_seed"].items()}
    return out


def run(salts: bool = True) -> dict:
    runs = V.dev_runs()
    dropped: list = []
    events = V.build(runs, dropped=dropped)
    m = V.measure(events)
    main = m.pop("main")
    result = dict(verdict=m.pop("verdict"), main=_summary(main), **m)
    result["per_delta"] = {str(k): v for k, v in result["per_delta"].items()}

    pos2, neg2 = V.v2_rows_of(events)
    s2 = V.over_splits(pos2, neg2, V.V2_FEATURES)
    notes = V.build(runs, kind="v2-notes")
    pn, nn = V.rows_of(notes)
    sn = V.over_splits(pn, nn, V.FEATURES)
    comparisons = {
        "v2_features_same_items": dict(features=list(V.V2_FEATURES), verdict=V.verdict(s2),
                                       main=_summary(s2),
                                       table=V.feature_table(pos2, neg2, V.V2_FEATURES)),
        "v2_notes_as_controls": dict(n_events=len(notes), verdict=V.verdict(sn),
                                     main=_summary(sn),
                                     table=V.feature_table(pn, nn, V.FEATURES)),
    }
    man = dict(what="v3 P3 (T24): benign changes (drift) matched 1:1 to sleeper payloads on "
                    "dev; 4-feature surface discriminator under v2's split protocol",
               protocol=protocol(), corpus=corpus_record(events, runs, dropped),
               result=result, comparisons=comparisons)
    if salts:
        man["salt_family"] = V.salt_family(runs)
    return man


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--no-salts", action="store_true")
    a = ap.parse_args()
    man = run(salts=not a.no_salts)
    r = man["result"]
    mm = r["main"]
    print(f"corpus: {man['corpus']['n_events']} events, {man['corpus']['n_benign']} benign "
          f"changes ({man['corpus']['n_distinct_benign']} distinct), dev only, "
          f"sha256 {man['corpus']['digest'][:12]}")
    print(f"AUC (4 features, {mm['k']} splits): median {mm['auc_median']}, mean "
          f"{mm['auc_mean']}, mean CI95 [{mm['lo_mean']}, {mm['hi_mean']}]; "
          f"{mm['clear']}/{mm['k']} splits clear {V.CEILING}")
    print(f"floor of the mean upper bound at AUC = 0.5 on this sample: {r['floor_hi']}")
    for c, row in r["features"].items():
        print(f"  {c:17s} single-feature AUC {row['auc_single']:.4f}  smd {row['smd']:+.3f}  "
              f"drop-one hi_mean {r['drop_one'][c]['hi_mean']}")
    for d, row in r["per_delta"].items():
        print(f"  Delta={d}: median {row['auc_median']}, hi_mean {row['hi_mean']} -> "
              f"{row['verdict']}")
    for name, c in man["comparisons"].items():
        print(f"  [{name}] median {c['main']['auc_median']}, hi_mean {c['main']['hi_mean']} "
              f"-> {c['verdict']}")
    if "salt_family" in man:
        sf = man["salt_family"]
        print(f"  salt family: {sf['passing']}/{sf['total']} salts pass -> {sf['verdict']}")
    print(f"VERDICT (ceiling {V.CEILING}, {V.CRITERION}): {r['verdict']}")
    if a.write:
        MANIFEST.write_text(json.dumps(man, indent=1, ensure_ascii=False, sort_keys=True)
                            + "\n", encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
