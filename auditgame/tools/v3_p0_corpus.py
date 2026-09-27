#!/usr/bin/env python3
"""v3_p0_corpus.py -- sentinel-v3.md C14: the fresh eval split, built with the real code.

A P0 planning check for Sentinel v3, not a run.  It answers four questions before the
split is frozen:

1. Which repo families has NO v2 workflow touched?  (corpus_v2 decides what v2 touched.)
2. How many workflows does the v2 builder (corpus_v2: per repo, created_at order,
   consecutive windows of H ~ U{6..14}, two passes at offsets 0 and 3) cut from them,
   and how is the weight spread over families (Kish)?
3. Which Delta can each workflow host (sigma = iota + Delta <= H needs H >= Delta + 1)?
   Also reported, for information only: SPEC-P1a step 4 (a topic pair at distance Delta),
   which corpus_v2 did not apply.
4. How much of this depends on the builder's seed and on instance reuse?

Reads data/swebench_{full,multilingual}.jsonl.  Writes spikes/v3-p0/corpus.json.

    python3 tools/v3_p0_corpus.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import random
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import corpus_v2 as C
import draft_setup as D
from core import seed_of
from swebench_dataset import SWEBenchDataset

OUT = HERE / "spikes" / "v3-p0" / "corpus.json"
DELTAS = D.DELTAS                      # (0, 1, 2, 4, 8), draft SS8
H_MIN, H_MAX = D.H_RANGE               # (6, 14), draft SS8
V2_SEED = 2027                         # corpus_v2.make_corpus_v2's default seed
SEED_SCAN = range(1, 501)
TWO_PASS, ONE_PASS = (0, 3), (0,)      # corpus_v2.PASS_OFFSETS; one pass = no instance reuse

EXT_LANG = {".py": "Python", ".c": "C", ".h": "C", ".cc": "C++", ".cpp": "C++",
            ".cxx": "C++", ".hpp": "C++", ".go": "Go", ".rs": "Rust", ".java": "Java",
            ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
            ".ts": "TypeScript", ".tsx": "TypeScript", ".php": "PHP", ".rb": "Ruby"}
CPP_EXT = {".cc", ".cpp", ".cxx", ".hpp"}


def language(rows) -> str:
    """Majority language of the files the repo's gold and test patches touch.  A .h header
    counts as C++ in a repo that also has C++ sources (fmt's gold patches touch only .h)."""
    exts = [pathlib.PurePosixPath(p).suffix
            for r in rows for field in ("patch", "test_patch")
            for p in re.findall(r"^diff --git a/(\S+)", r.get(field, ""), re.M)]
    cpp = any(e in CPP_EXT for e in exts)
    langs = collections.Counter("C++" if (e == ".h" and cpp) else EXT_LANG[e]
                                for e in exts if e in EXT_LANG)
    return langs.most_common(1)[0][0] if langs else "?"


def kish(sizes) -> float:
    """Effective number of clusters, (sum n)^2 / sum n^2 (corpus_v2.kish)."""
    n = sum(sizes)
    return round(n * n / sum(s * s for s in sizes), 2) if n else 0.0


def cut(rows, repo, seed, offsets) -> list:
    """corpus_v2.make_corpus_v2's builder for ONE repo: same RNG, same windows."""
    out = []
    for off in offsets:
        rng = random.Random(seed_of(seed, repo, off))
        i = off
        while True:
            H = rng.randint(H_MIN, H_MAX)
            if i + H > len(rows):
                break
            out.append(rows[i:i + H])
            i += H
    return out


def build(families, seed, offsets) -> list:
    """The v3 split.  A family the builder cuts nothing from, but whose size is itself a
    legal H, becomes ONE workflow of all its instances ("H = family size").  That rule is
    not the v2 builder's and must be declared as a deviation."""
    wfs = []
    for repo, (pool, rows) in sorted(families.items()):
        segs = cut(rows, repo, seed, offsets)
        rule = "v2 builder"
        if not segs and H_MIN <= len(rows) <= H_MAX:
            segs, rule = [rows], "H = family size"
        for s in segs:
            wfs.append({"repo": repo, "pool": pool, "H": len(s), "rule": rule,
                        "instances": [r["instance_id"] for r in s]})
    return wfs


def describe(wfs, lang, hosts) -> dict:
    size = collections.Counter(w["repo"] for w in wfs)
    sizes = sorted(size.values(), reverse=True)
    top2 = sum(sizes[:2]) / len(wfs) if wfs else 0.0
    per_delta = {}
    for d in DELTAS:
        ok = [w for w in wfs if w["H"] >= d + 1]
        s = collections.Counter(w["repo"] for w in ok)
        per_delta[d] = {"workflows": len(ok), "families": len(s), "kish": kish(list(s.values())),
                        "step4_topic_pair": sum(hosts[(w["repo"], w["H"], w["instances"][0], d)]
                                                for w in ok)}
    all_d = [w for w in wfs if w["H"] >= max(DELTAS) + 1]
    s_all = collections.Counter(w["repo"] for w in all_d)
    return {
        "workflows": len(wfs), "families": len(size), "kish": kish(sizes),
        "top2_share": round(top2, 3),
        "by_family": dict(sorted(size.items(), key=lambda kv: (-kv[1], kv[0]))),
        "python_workflows": sum(1 for w in wfs if lang[w["repo"]] == "Python"),
        "H": sorted(w["H"] for w in wfs),
        "rules": dict(collections.Counter(w["rule"] for w in wfs)),
        "per_delta": per_delta,
        "hosting_every_delta": {"workflows": len(all_d), "families": len(s_all),
                                "kish": kish(list(s_all.values())),
                                "dropped_families": sorted(set(size) - set(s_all))},
    }


def scan(families, offsets) -> dict:
    n, k = [], []
    for seed in SEED_SCAN:
        wfs = build(families, seed, offsets)
        n.append(len(wfs))
        k.append(kish(list(collections.Counter(w["repo"] for w in wfs).values())))
    q = lambda xs: {"min": min(xs), "median": statistics.median(xs), "max": max(xs)}
    return {"seeds": f"{SEED_SCAN.start}..{SEED_SCAN.stop - 1}", "workflows": q(n), "kish": q(k)}


def main() -> int:
    # --- what v2 touched ---------------------------------------------------------------
    v2 = C.make_corpus_v2()
    v2_dev, v2_eval = C.split(v2)
    v2_repos = {w.repo for w in v2}
    v2_inst = {t.task_id for w in v2 for t in w.tasks}
    v2_eval_sizes = list(collections.Counter(w.repo for w in v2_eval).values())
    assert (len(v2), len(v2_dev), len(v2_eval)) == (100, 43, 57), "v2 corpus changed"
    assert kish(v2_eval_sizes) == 8.1, kish(v2_eval_sizes)          # v2-facts A.4: 8.10

    pools = {p: SWEBenchDataset(p, sweep_deltas=()) for p in ("full", "verified", "multilingual")}
    by = {p: ds._by_repo() for p, ds in pools.items()}
    lang = {repo: language(rows) for p in ("full", "multilingual") for repo, rows in by[p].items()}

    # --- 1. families no v2 workflow touched ----------------------------------------------
    fresh = {}
    for pool in ("full", "multilingual"):
        for repo, rows in by[pool].items():
            if repo not in v2_repos and len(rows) >= H_MIN:
                assert repo not in fresh, f"{repo} in two pools"
                fresh[repo] = (pool, rows)
    touched_ml = {r: len(v) for r, v in by["multilingual"].items() if r in v2_repos}
    ml_large = {r: len(v) for r, v in by["multilingual"].items() if len(v) >= H_MAX}
    assert set(ml_large) <= v2_repos, "a large Multilingual family was not used by v2"

    # step-4 topic pairs, for information: (repo, H, first instance, Delta) -> bool
    topic_ds = {"full": pools["full"], "multilingual": pools["multilingual"]}
    hosts = {}

    def fill_hosts(wfs):
        rows_of = {r["instance_id"]: r for _, (_, rows) in fresh.items() for r in rows}
        for w in wfs:
            rows = [rows_of[i] for i in w["instances"]]
            for d in DELTAS:
                key = (w["repo"], w["H"], w["instances"][0], d)
                if key not in hosts:
                    hosts[key] = w["H"] >= d + 1 and topic_ds[w["pool"]].hosts_delta(rows, d)

    # --- 2./3. the split, as sentinel-v3.md C14(a) cuts it, and without reuse ------------
    variants = {"two_pass": TWO_PASS, "one_pass": ONE_PASS}
    split, summary = {}, {}
    for name, offs in variants.items():
        wfs = build(fresh, V2_SEED, offs)
        fill_hosts(wfs)
        inst = [i for w in wfs for i in w["instances"]]
        assert not set(inst) & v2_inst, "a v3 eval instance is in a v2 workflow"
        reuse = collections.Counter(inst)
        assert max(reuse.values()) <= len(offs), "instance reused beyond the pass count"
        split[name] = wfs
        summary[name] = describe(wfs, lang, hosts)
        summary[name]["seed_scan"] = scan(fresh, offs)

    # --- C14(b): new instances on the v2 eval families that are Python ------------------
    ver_ids = {r["instance_id"] for rows in by["verified"].values() for r in rows}
    py_eval = sorted({w.repo for w in v2_eval if w.repo in by["full"]})
    new_inst = {repo: [r for r in by["full"][repo] if r["instance_id"] not in ver_ids]
                for repo in py_eval}
    c14b = {"families": len(py_eval),
            "instances": {r: len(v) for r, v in new_inst.items()},
            "instances_total": sum(len(v) for v in new_inst.values()),
            "one_pass_workflows": sum(len(cut(v, r, V2_SEED, ONE_PASS))
                                      for r, v in new_inst.items())}

    doc = {
        "what": "sentinel-v3.md C14: fresh eval split built with corpus_v2's builder (P0 check)",
        "v2": {"families": sorted(v2_repos), "eval_kish": kish(v2_eval_sizes),
               "eval_workflows": len(v2_eval), "eval_families": len(v2_eval_sizes),
               "multilingual_families_touched": touched_ml,
               "multilingual_families_with_14_plus": ml_large},
        "fresh_families": {r: {"pool": p, "instances": len(rows), "language": lang[r]}
                           for r, (p, rows) in sorted(fresh.items(),
                                                     key=lambda kv: (-len(kv[1][1]), kv[0]))},
        "languages": dict(collections.Counter(lang[r] for r in fresh)),
        "builder_seed": V2_SEED, "summary": summary, "c14b": c14b,
        "dev_candidates": {"v2_corpus_families": dict(collections.Counter(w.repo for w in v2)),
                           "v2_corpus_languages": dict(collections.Counter(
                               lang.get(w.repo, "?") for w in v2))},
        "split": split,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # --- report -------------------------------------------------------------------------
    print(f"v2: {len(v2)} workflows, eval {len(v2_eval)} / {len(v2_eval_sizes)} families, "
          f"Kish {kish(v2_eval_sizes)}")
    print(f"fresh families (>= {H_MIN} instances, no v2 workflow): {len(fresh)}; "
          f"languages {doc['languages']}")
    for r, f in doc["fresh_families"].items():
        print(f"  {r:32s} {f['pool']:12s} {f['instances']:3d}  {f['language']}")
    for name, s in summary.items():
        print(f"\n[{name}] seed {V2_SEED}: {s['workflows']} workflows / {s['families']} families, "
              f"Kish {s['kish']}, top-2 share {s['top2_share']:.0%}, Python {s['python_workflows']}; "
              f"rules {s['rules']}")
        print(f"  by family: {s['by_family']}")
        for d, v in s["per_delta"].items():
            print(f"  Delta={d}: {v['workflows']:2d} workflows / {v['families']:2d} families "
                  f"(Kish {v['kish']}); step-4 topic pair: {v['step4_topic_pair']}")
        e = s["hosting_every_delta"]
        print(f"  hosting every Delta (H >= 9): {e['workflows']} workflows / {e['families']} "
              f"families (Kish {e['kish']}); families lost: {e['dropped_families']}")
        sc = s["seed_scan"]
        print(f"  builder seeds {sc['seeds']}: workflows {sc['workflows']}, Kish {sc['kish']}")
    print(f"\nC14(b): {c14b['instances_total']} new instances on {c14b['families']} v2 eval "
          f"families (Python); one pass would cut {c14b['one_pass_workflows']} workflows")
    print(f"wrote {OUT.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
