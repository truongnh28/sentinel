"""v3/corpus.py -- dev = the v2 corpus; the two eval splits, exposed ONLY as digests (T2).

Plan S6 layer 1, C14 as amended by D-v3-1 (27/09, after Gate 0, before any tuning).

THREE SPLITS.
    dev        corpus_v2.make_corpus_v2(): all 100 v2 workflows (Q10).  v2 has run on every
               one of them, so they are development data only.  dev_workflows() is the
               only public function here that returns workflows.
    primary    config.EVAL_SOURCE_PRIMARY: SWE-rebench-V2 (nebius/SWE-rebench-V2),
               instances created on/after 2024-01-01, 20 untouched families, at most 5
               workflows each, one pass, no instance reused.  EVAL_SPLIT_SHA256.
    secondary  config.EVAL_SOURCE_SECONDARY: the former C14(a), the SWE-bench one-pass
               split of tools/v3_p0_corpus.py (26 workflows / 18 families, builder seed
               2027, the "H = family size" rule declared as a deviation).
               SECONDARY_SPLIT_SHA256.

THE SEAL.  An eval split is a list of instances, not a result; what must stay sealed until
P5 is every simulation, table or summary run on it.  So this module builds the eval splits
only to HASH them and to count their shape (eval_digest, eval_summary: families, H, Kish,
languages -- never an instance and never an outcome).  The only road to eval workflows is
v3/seal.py: its accessor takes only a token that seal.unseal() issues at P5.  The
underscore builders below are for seal.py and for the tests; tests/v3/test_infra_seal.py
fails if any other v3 module or v3 tool names them.

THE PRIMARY RULES (declared before the split was built; D-v3-1, C14).
  1. Source: data/swerebench_v2_index.jsonl.gz, a reduced copy of SWE-rebench-V2 at
     revision REBENCH_REVISION, pinned by data/swerebench_v2.manifest.json (sha256).
  2. Keep instances with created_at >= CREATED_FROM.
  3. Family = the repository, case-insensitive, with renamed / transferred / forked repos
     merged by the explicit list ALIASES.  Sharing a name after the owner is NOT enough
     (Sage/carbon, a React design system, is not briannesbitt/Carbon, a PHP date library):
     the groups that share a name and are different projects are listed in
     DISTINCT_SAME_NAME, and a test checks that every same-name group that could touch the
     choice (step 5) or the exclusion (step 4) is resolved one way or the other.
  4. Drop every family v2 touched (corpus_v2, case-insensitive, after aliases) and every
     family of the secondary split; drop exercise / solution repositories (EXERCISE_OWNERS,
     EXERCISE_NAME_RE).
  5. Choose the N_FAMILIES families with the most remaining instances (ties by name).  The
     rule reads counts only, never a result.
  6. Per family, v2's builder (corpus_v2): instances in (created_at, instance_id) order,
     consecutive windows of H ~ U{6..14} drawn by random.Random(seed_of(BUILDER_SEED,
     family, 0)), ONE pass from offset 0, so no instance is reused; keep the first
     CAP_PER_FAMILY windows.
  7. Pinned order (the order line 1's post-mortems follow, C12): chronological by each
     workflow's first instance (created_at, instance_id).  wf_id = v3e-NNN in that order.
  Weights are per workflow (Q10); Kish = (sum n)^2 / sum n^2 over families.

REALISED (builder seed 2027; pinned in EVAL_SUMMARY_PINNED and checked by the tests):
    primary    96 workflows / 20 families (16 at the cap of 5, 4 with 4), 941 instances,
               Kish 19.86; languages by family: Python 8, Rust 4, Kotlin 2, TypeScript 2,
               PHP 1, C# 1, Java 1, Scala 1; H in 6..14; 56 workflows / 20 families
               (Kish 17.23) have H >= 9 and so host Delta = 8.
    secondary  26 workflows / 18 families, Kish 10.24 (14 by "H = family size");
               18 workflows / 12 families host Delta = 8.

REBUILDING THE DATA.  From auditgame/, with the parquet of REBENCH_REVISION downloaded:
    <venv>/bin/python -m v3.corpus --fetch path/to/train-00000-of-00001.parquet
writes the two .jsonl.gz files and the manifest.  pyarrow is needed only for this step.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import io
import json
import pathlib
import random
import re

import corpus_v2
import draft_setup as D
from core import Task, Workflow, seed_of
from v3 import config as C

ROOT = pathlib.Path(__file__).resolve().parent.parent               # auditgame/
DATA = ROOT / "data"

# ---------------------------------------------------------------------------------------
# Dev (Q10)
# ---------------------------------------------------------------------------------------

DEV_SEED = 2027                          # corpus_v2.make_corpus_v2's default


def dev_workflows() -> list:
    """Dev = the whole v2 corpus, 100 workflows (Q10).  It holds v2's 57 eval workflows
    too: v2 has been run on all of them, so they are development data now."""
    wfs = corpus_v2.make_corpus_v2(D.N_WORKFLOWS, DEV_SEED)
    if len(wfs) != C.DEV_N_WORKFLOWS:
        raise RuntimeError(f"dev has {len(wfs)} workflows, not {C.DEV_N_WORKFLOWS}")
    return wfs


# ---------------------------------------------------------------------------------------
# Primary eval source: SWE-rebench-V2 (D-v3-1)
# ---------------------------------------------------------------------------------------

SOURCE = C.EVAL_SOURCE_PRIMARY
REBENCH_DATASET = "nebius/SWE-rebench-V2"
REBENCH_REVISION = "475dd5e8703bb5fb22dd3c60b5d038b019eba1e0"
REBENCH_PARQUET = "data/train-00000-of-00001.parquet"
INDEX_FILE = DATA / "swerebench_v2_index.jsonl.gz"          # all 32,079 rows, small fields
POOL_FILE = DATA / "swerebench_v2_eval_pool.jsonl.gz"       # full rows of the 20 families
MANIFEST_FILE = DATA / "swerebench_v2.manifest.json"

CREATED_FROM = f"{SOURCE.created_from}-01"                   # "2024-01-01", inclusive
N_FAMILIES = SOURCE.n_families                               # 20
CAP_PER_FAMILY = SOURCE.cap_per_family                       # 5
H_MIN, H_MAX = SOURCE.h_range                                # (6, 14)
BUILDER_SEED = 2027                                          # decided (T2), as Q10's
ONE_PASS_OFFSET = 0

QUALITY_FLAGS = ("B1", "B2", "B3", "B4", "B5", "B6")
#: The reduced copy keeps these fields (index: all rows; pool: the 20 chosen families).
INDEX_FIELDS = ("instance_id", "repo", "created_at", "base_commit", "image_name",
                "language", "license", "flags", "difficulty", "intent_completeness",
                "n_fail_to_pass")
POOL_FIELDS = ("instance_id", "repo", "created_at", "base_commit", "patch", "test_patch",
               "FAIL_TO_PASS", "image_name", "language", "license", "flags", "difficulty",
               "intent_completeness", "problem_statement")

#: Rule 3: renamed, transferred or forked repositories -> the family they belong to
#: (lower case).  Every pair shares its name after the owner and is the same project
#: (a GitHub transfer / rename, or a fork that continued it).
ALIASES = {
    "keepsafe/aiohttp": "aio-libs/aiohttp",
    "dalance/veryl": "veryl-lang/veryl",
    "rust-analyzer/rust-analyzer": "rust-lang/rust-analyzer",
    "apple/swift-syntax": "swiftlang/swift-syntax",
    "friendsofphp/php-cs-fixer": "php-cs-fixer/php-cs-fixer",
    "raphlinus/pulldown-cmark": "pulldown-cmark/pulldown-cmark",
    "google/jax": "jax-ml/jax",
    "pipxproject/pipx": "pypa/pipx",
    "theacodes/nox": "wntrblm/nox",
    "jmcgeheeiv/pyfakefs": "pytest-dev/pyfakefs",
    "mattgodbolt/compiler-explorer": "compiler-explorer/compiler-explorer",
    "ota-meshi/eslint-plugin-svelte": "sveltejs/eslint-plugin-svelte",
    "tomwhite/cubed": "cubed-dev/cubed",
    "rochacbruno/dynaconf": "dynaconf/dynaconf",
    "pions/webrtc": "pion/webrtc",
    "andig/evcc": "evcc-io/evcc",
    "alan-turing-institute/sktime": "sktime/sktime",
    "greyli/apiflask": "apiflask/apiflask",
    "segmentio/parquet-go": "parquet-go/parquet-go",
    "deislabs/ratify": "ratify-project/ratify",
    "petermattis/pebble": "cockroachdb/pebble",
    "hpcng/warewulf": "warewulf/warewulf",
    "twitter/compose-rules": "mrmans0n/compose-rules",
    "yannickcr/eslint-plugin-react": "jsx-eslint/eslint-plugin-react",
    "xjamundx/eslint-plugin-promise": "eslint-community/eslint-plugin-promise",
    "syuilo/aiscript": "aiscript-dev/aiscript",
    "crossplane/provider-aws": "crossplane-contrib/provider-aws",
    "cqfn/diktat": "analysis-dev/diktat",
    "jlongster/prettier": "prettier/prettier",
    "weaveworks/eksctl": "eksctl-io/eksctl",
}

#: Rule 3: groups that share a name after the owner and are DIFFERENT projects.
DISTINCT_SAME_NAME = {
    "carbon": ("sage/carbon", "briannesbitt/carbon"),      # React design system / PHP dates
    "redis": ("redis/redis", "go-redis/redis"),            # the server / a Go client
    "framework": ("laravel/framework", "maizzle/framework", "spiral/framework"),
    "cli": ("cli/cli", "dapr/cli", "smallstep/cli", "netlify/cli", "kyma-project/cli",
            "openfga/cli", "exercism/cli", "urfave/cli", "hetznercloud/cli", "supabase/cli",
            "sveltejs/cli"),
    "nexus": ("bluebrain/nexus", "gammazero/nexus"),
    "pie": ("php/pie", "elliotchance/pie"),
    "core": ("oclif/core", "api-platform/core", "ocr-d/core", "cogentcore/core",
             "mostjs/core", "artusjs/core"),
    "sdk": ("meltano/sdk", "dfinity/sdk"),
    "sdk-java": ("serverlessworkflow/sdk-java", "temporalio/sdk-java"),
    "prism": ("echolabsdev/prism", "prismjs/prism", "ruby/prism"),
    "pebble": ("cockroachdb/pebble", "pebbletemplates/pebble"),
    "operator": ("knative/operator", "canonical/operator", "tektoncd/operator"),
    "cbor": ("fxamacker/cbor", "pyfisch/cbor"),
    "toml": ("burntsushi/toml", "toml-rs/toml"),
    "faker": ("joke2k/faker", "bxcodec/faker", "fakerphp/faker"),
}

#: Rule 4: exercise / solution repositories are not software projects with a history.
EXERCISE_OWNERS = ("exercism", "thealgorithms")
EXERCISE_NAME_RE = re.compile(r"(dailycodingproblem|leetcode|advent-?of-?code|"
                              r"(^|[-_])(exercises|solutions|katas)($|[-_]))", re.I)


def family_of(repo: str) -> str:
    """Rule 3: the family of a repository (lower case, after ALIASES)."""
    r = repo.lower()
    return ALIASES.get(r, r)


def is_exercise(repo: str) -> bool:
    """Rule 4: an exercise / solution repository."""
    owner, _, name = repo.lower().partition("/")
    return owner in EXERCISE_OWNERS or bool(EXERCISE_NAME_RE.search(name))


# ---------------------------------------------------------------------------------------
# Data files (reduced copy + sha256 manifest)
# ---------------------------------------------------------------------------------------


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _read_jsonl_gz(path: pathlib.Path) -> tuple:
    raw = gzip.decompress(path.read_bytes())
    return raw, [json.loads(l) for l in raw.decode("utf-8").splitlines() if l]


def manifest() -> dict:
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def verify_data() -> list:
    """Problems with the reduced copy against its sha256 manifest ([] = intact).  The
    sha256 is taken over the DECOMPRESSED jsonl, so a different gzip build cannot move it."""
    out, man = [], manifest()
    for name, want in man["files"].items():
        path = DATA / name
        if not path.exists():
            out.append(f"{name}: missing")
            continue
        raw, rows = _read_jsonl_gz(path)
        if _sha256(raw) != want["sha256_jsonl"]:
            out.append(f"{name}: sha256 {_sha256(raw)[:12]} != manifest {want['sha256_jsonl'][:12]}")
        if len(rows) != want["rows"]:
            out.append(f"{name}: {len(rows)} rows != manifest {want['rows']}")
    return out


_INDEX: list = []


def _index() -> list:
    """Every SWE-rebench-V2 row, small fields only (no patch, no tests)."""
    if not _INDEX:
        raw, rows = _read_jsonl_gz(INDEX_FILE)
        want = manifest()["files"][INDEX_FILE.name]["sha256_jsonl"]
        if _sha256(raw) != want:
            raise RuntimeError(f"{INDEX_FILE.name} does not match its sha256 manifest")
        _INDEX.extend(rows)
    return _INDEX


# ---------------------------------------------------------------------------------------
# What v2 and the secondary split touched (rule 4)
# ---------------------------------------------------------------------------------------


def v2_repos() -> set:
    """Every repository any v2 workflow used (dev and v2 eval alike)."""
    return {w.repo for w in dev_workflows()}


def touched_families() -> set:
    """Rule 4: v2's families and the secondary split's, case-insensitive, after aliases."""
    sec = {s["family"] for s in _build_secondary()}
    return {family_of(r) for r in v2_repos() | sec}


# ---------------------------------------------------------------------------------------
# The builder (rules 5-7) -- private: seal.py and the tests only
# ---------------------------------------------------------------------------------------


def _cut(rows: list, family: str, seed: int, cap: int | None) -> list:
    """corpus_v2's builder for ONE family, one pass from offset 0: consecutive windows of
    H ~ U{H_MIN..H_MAX}; stops at the first window that does not fit, or at `cap`."""
    rng = random.Random(seed_of(seed, family, ONE_PASS_OFFSET))
    out, i = [], ONE_PASS_OFFSET
    while cap is None or len(out) < cap:
        H = rng.randint(H_MIN, H_MAX)
        if i + H > len(rows):
            break
        out.append(rows[i:i + H])
        i += H
    return out


def _candidate_families() -> dict:
    """Rules 2-4: family -> its rows created on/after CREATED_FROM, in (created_at,
    instance_id) order, v2 / secondary / exercise families removed."""
    touched = touched_families()
    fam: dict = {}
    for r in _index():
        if r["created_at"] < CREATED_FROM or is_exercise(r["repo"]):
            continue
        f = family_of(r["repo"])
        if f in touched:
            continue
        fam.setdefault(f, []).append(r)
    for rows in fam.values():
        rows.sort(key=lambda r: (r["created_at"], r["instance_id"]))
    return fam


def _chosen_families() -> list:
    """Rule 5: the N_FAMILIES largest candidate families, ties by name."""
    fam = _candidate_families()
    return sorted(fam, key=lambda f: (-len(fam[f]), f))[:N_FAMILIES]


def _build_primary() -> list:
    """The primary eval split as specs, in the pinned order (rule 7)."""
    fam = _candidate_families()
    specs = []
    for f in _chosen_families():
        for w, seg in enumerate(_cut(fam[f], f, BUILDER_SEED, CAP_PER_FAMILY)):
            specs.append({"family": f, "window": w, "rule": "v2 builder",
                          "first": (seg[0]["created_at"], seg[0]["instance_id"]),
                          "instances": [r["instance_id"] for r in seg]})
    specs.sort(key=lambda s: s["first"])
    for i, s in enumerate(specs):
        s["wf_id"] = f"v3e-{i:03d}"
        del s["first"]
    return specs


# ---------------------------------------------------------------------------------------
# Secondary eval source: the SWE-bench one-pass split (former C14(a))
# ---------------------------------------------------------------------------------------

SECONDARY = C.EVAL_SOURCE_SECONDARY
SECONDARY_POOLS = ("full", "multilingual")
_SECONDARY: list = []


def _secondary_rows() -> dict:
    """tools/v3_p0_corpus.py, rewritten: repo -> (pool, rows in created_at order) for every
    SWE-bench full / Multilingual repo with >= H_MIN instances and no v2 workflow."""
    from swebench_dataset import SWEBenchDataset
    v2 = v2_repos()
    fresh = {}
    for pool in SECONDARY_POOLS:
        for repo, rows in SWEBenchDataset(pool, sweep_deltas=())._by_repo().items():
            if repo not in v2 and len(rows) >= H_MIN:
                if repo in fresh:
                    raise ValueError(f"{repo} is in two pools")
                fresh[repo] = (pool, rows)
    return fresh


def _build_secondary() -> list:
    """The secondary split as specs, in P0's order (by repo).  A repo the builder cuts
    nothing from but whose size is itself a legal H is ONE workflow of all its instances:
    the "H = family size" rule, a declared deviation from v2's builder (C14(a))."""
    if _SECONDARY:
        return [dict(s) for s in _SECONDARY]
    specs = []
    for repo, (pool, rows) in sorted(_secondary_rows().items()):
        segs = _cut(rows, repo, SECONDARY.builder_seed, None)
        rule = "v2 builder"
        if not segs and H_MIN <= len(rows) <= H_MAX:
            segs, rule = [rows], "H = family size"
        for w, s in enumerate(segs):
            specs.append({"family": repo, "pool": pool, "window": w, "rule": rule,
                          "instances": [r["instance_id"] for r in s]})
    for i, s in enumerate(specs):
        s["wf_id"] = f"v3s-{i:03d}"
    _SECONDARY.extend(specs)
    return [dict(s) for s in specs]


# ---------------------------------------------------------------------------------------
# Public: digests and shape only
# ---------------------------------------------------------------------------------------

SPLITS = ("primary", "secondary")


def _specs(split: str) -> list:
    if split == "primary":
        return _build_primary()
    if split == "secondary":
        return _build_secondary()
    raise ValueError(f"split={split!r} is not one of {SPLITS}")


def _digest_of(specs: list, split: str) -> str:
    src = SOURCE if split == "primary" else SECONDARY
    body = {"source": src.name, "dataset": src.dataset,
            "revision": REBENCH_REVISION if split == "primary" else "swebench_{full,multilingual}.jsonl",
            "workflows": [[s["wf_id"], s["family"], s["instances"]] for s in specs]}
    return _sha256(C.canonical_json(body).encode("ascii"))


def eval_digest(split: str = "primary") -> str:
    """sha256 of the split's instance list in its pinned order -- all that leaves here."""
    return _digest_of(_specs(split), split)


def kish(sizes) -> float:
    """(sum n)^2 / sum n^2 over families (corpus_v2.kish, on counts)."""
    sizes = list(sizes)
    n = sum(sizes)
    return n * n / sum(s * s for s in sizes) if n else 0.0


def _language(split: str, specs: list) -> dict:
    if split == "primary":
        per: dict = {}
        for r in _index():
            f = family_of(r["repo"])
            per.setdefault(f, collections.Counter())[r["language"]] += 1
        return {f: per[f].most_common(1)[0][0] for f in {s["family"] for s in specs}}
    from swebench_dataset import SWEBenchDataset   # P0's rule: majority language of patch files
    ext = {".py": "python", ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp",
           ".hpp": "cpp", ".go": "go", ".rs": "rust", ".java": "java", ".js": "js",
           ".jsx": "js", ".mjs": "js", ".ts": "ts", ".tsx": "ts", ".php": "php", ".rb": "ruby"}
    out = {}
    for pool in SECONDARY_POOLS:
        for repo, rows in SWEBenchDataset(pool, sweep_deltas=())._by_repo().items():
            if repo not in {s["family"] for s in specs}:
                continue
            exts = [pathlib.PurePosixPath(p).suffix for r in rows
                    for fld in ("patch", "test_patch")
                    for p in re.findall(r"^diff --git a/(\S+)", r.get(fld, ""), re.M)]
            cpp = any(e in (".cc", ".cpp", ".cxx", ".hpp") for e in exts)
            c = collections.Counter("cpp" if (e == ".h" and cpp) else ext[e]
                                    for e in exts if e in ext)
            out[repo] = c.most_common(1)[0][0] if c else "?"
    return out


def eval_summary(split: str = "primary") -> dict:
    """The split's SHAPE: counts only, no instance and no outcome."""
    specs = _specs(split)
    fam = collections.Counter(s["family"] for s in specs)
    lang = _language(split, specs)
    hs = [len(s["instances"]) for s in specs]
    per_delta = {}
    for d in C.DELTAS:
        ok = collections.Counter(s["family"] for s in specs if len(s["instances"]) >= d + 1)
        per_delta[str(d)] = {"workflows": sum(ok.values()), "families": len(ok),
                             "kish": round(kish(ok.values()), 2)}
    return {
        "split": split,
        "workflows": len(specs),
        "families": len(fam),
        "kish": round(kish(fam.values()), 2),
        "instances": sum(hs),
        "workflows_per_family": dict(sorted(fam.items(), key=lambda kv: (-kv[1], kv[0]))),
        "languages_by_family": dict(collections.Counter(lang[f] for f in fam)),
        "languages_by_workflow": dict(collections.Counter(lang[s["family"]] for s in specs)),
        "H_histogram": {str(h): n for h, n in sorted(collections.Counter(hs).items())},
        "rules": dict(collections.Counter(s["rule"] for s in specs)),
        "per_delta": per_delta,
    }


# ---------------------------------------------------------------------------------------
# Materialise -- seal.py only
# ---------------------------------------------------------------------------------------


def _materialise(split: str) -> list:
    """core.Workflow objects of an eval split.  Called by seal.eval_workflows only, after
    it has checked the token; tests/v3/test_infra_seal.py fails if anything else calls it."""
    specs = _specs(split)
    if split == "primary":
        raw, rows = _read_jsonl_gz(POOL_FILE)
        if _sha256(raw) != manifest()["files"][POOL_FILE.name]["sha256_jsonl"]:
            raise RuntimeError(f"{POOL_FILE.name} does not match its sha256 manifest")
        by_id = {r["instance_id"]: r for r in rows}
    else:
        by_id = {r["instance_id"]: r for _, (_, rs) in _secondary_rows().items() for r in rs}
    import topics
    from swebench_dataset import Topic
    wfs = []
    for s in specs:
        wfs.append(Workflow(wf_id=s["wf_id"], repo=s["family"], tasks=[
            Task(task_id=i, repo=s["family"], base_commit=by_id[i]["base_commit"],
                 topic=Topic(topics.topic_of_instance(by_id[i])),
                 problem=by_id[i].get("problem_statement", "") or "")
            for i in s["instances"]]))
    return wfs


# ---------------------------------------------------------------------------------------
# Rebuilding the reduced copy from the parquet (maintenance; needs pyarrow)
# ---------------------------------------------------------------------------------------


def _gz(lines: list) -> tuple:
    raw = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in lines).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0, filename="") as fh:
        fh.write(raw)
    return raw, buf.getvalue()


def fetch(parquet: pathlib.Path) -> dict:
    """Write INDEX_FILE, POOL_FILE and MANIFEST_FILE from the SWE-rebench-V2 parquet of
    REBENCH_REVISION.  The pool holds the chosen families' rows created on/after
    CREATED_FROM, so it is written after the index and the choice (rules 2-5)."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    parquet = pathlib.Path(parquet)
    small = ["instance_id", "repo", "created_at", "base_commit", "image_name", "language",
             "license", "meta"]
    tab = pq.read_table(parquet, columns=small + ["FAIL_TO_PASS"])
    n_f2p = pc.fill_null(pc.list_value_length(tab["FAIL_TO_PASS"]), 0).to_pylist()
    t = tab.select(small).to_pylist()
    for r, n in zip(t, n_f2p):
        r["n_fail_to_pass"] = n
    n_rows = len(t)
    del tab

    def flags(r):
        det = ((r.get("meta") or {}).get("llm_metadata") or {}).get("detected_issues") or {}
        return {b: bool(det.get(b)) for b in QUALITY_FLAGS}

    def llm(r, k):
        return ((r.get("meta") or {}).get("llm_metadata") or {}).get(k)

    t.sort(key=lambda r: r["instance_id"])
    index = [{"instance_id": r["instance_id"], "repo": r["repo"], "created_at": r["created_at"],
              "base_commit": r["base_commit"], "image_name": r["image_name"],
              "language": r["language"], "license": r["license"], "flags": flags(r),
              "difficulty": llm(r, "difficulty"),
              "intent_completeness": llm(r, "intent_completeness"),
              "n_fail_to_pass": r["n_fail_to_pass"]} for r in t]
    raw_i, gz_i = _gz(index)
    INDEX_FILE.write_bytes(gz_i)
    MANIFEST_FILE.write_text(json.dumps({"files": {INDEX_FILE.name: {
        "sha256_jsonl": _sha256(raw_i), "rows": len(index)}}}) + "\n", encoding="utf-8")
    _INDEX.clear()
    chosen = set(_chosen_families())
    keep = [r["instance_id"] for r in t
            if r["created_at"] >= CREATED_FROM and family_of(r["repo"]) in chosen
            and not is_exercise(r["repo"])]
    full = pq.read_table(parquet, columns=small + ["patch", "test_patch", "FAIL_TO_PASS",
                                                   "problem_statement"])
    full = full.filter(pc.is_in(full["instance_id"], value_set=pa.array(keep))).to_pylist()
    full.sort(key=lambda r: r["instance_id"])
    pool = [{"instance_id": r["instance_id"], "repo": r["repo"], "created_at": r["created_at"],
             "base_commit": r["base_commit"], "patch": r["patch"], "test_patch": r["test_patch"],
             "FAIL_TO_PASS": list(r["FAIL_TO_PASS"] or []), "image_name": r["image_name"],
             "language": r["language"], "license": r["license"], "flags": flags(r),
             "difficulty": llm(r, "difficulty"),
             "intent_completeness": llm(r, "intent_completeness"),
             "problem_statement": r["problem_statement"]} for r in full]
    raw_p, gz_p = _gz(pool)
    POOL_FILE.write_bytes(gz_p)
    man = {
        "what": "reduced copy of SWE-rebench-V2 for the v3 primary eval split (D-v3-1, T2)",
        "dataset": REBENCH_DATASET, "revision": REBENCH_REVISION, "file": REBENCH_PARQUET,
        "license": "CC-BY-4.0 (dataset); each repository under its own license",
        "parquet_sha256": _sha256(parquet.read_bytes()), "parquet_bytes": parquet.stat().st_size,
        "parquet_rows": n_rows,
        "rebuild": "cd auditgame && <venv>/bin/python -m v3.corpus --fetch <parquet>",
        "sha256_over": "the decompressed jsonl (one json.dumps(sort_keys=True) row per line)",
        "files": {
            INDEX_FILE.name: {"sha256_jsonl": _sha256(raw_i), "sha256_gz": _sha256(gz_i),
                              "rows": len(index), "fields": list(INDEX_FIELDS),
                              "rows_are": "every row of the parquet"},
            POOL_FILE.name: {"sha256_jsonl": _sha256(raw_p), "sha256_gz": _sha256(gz_p),
                             "rows": len(pool), "fields": list(POOL_FIELDS),
                             "rows_are": (f"rows created on/after {CREATED_FROM} of the "
                                          f"{N_FAMILIES} chosen families (rules 2-5)")},
        },
    }
    MANIFEST_FILE.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return man


# ---------------------------------------------------------------------------------------
# Pinned (T2 acceptance: committed on the branch)
# ---------------------------------------------------------------------------------------

#: sha256 of the primary split (plan S6 layer 1).  Built 27/09 before any v3 tuning.
EVAL_SPLIT_SHA256 = "e34e747c36f1581941b7fad46c82a3f64475bb73522a4eb95cf6458c7e820fa0"
#: sha256 of the secondary split: the one-pass split P0 built (tools/v3_p0_corpus.py).
SECONDARY_SPLIT_SHA256 = "ed4e3dcb55e757b73d81bf8b7005e88f1f56685c396c745acd6dc0cfb71f5123"

#: The realised shapes (eval_summary), pinned.  Shape only: counts, never an outcome.
#: Delta = 8 needs sigma = iota + 8 <= H, so H >= 9; Delta <= 4 fits every H >= 6.
EVAL_SUMMARY_PINNED = {
    "primary": {
        "workflows": 96, "families": 20, "kish": 19.86, "instances": 941,
        "H_histogram": {"6": 16, "7": 14, "8": 10, "9": 3, "10": 10, "11": 14, "12": 7,
                        "13": 6, "14": 16},
        "languages_by_family": {"python": 8, "rust": 4, "kotlin": 2, "ts": 2, "php": 1,
                                "csharp": 1, "java": 1, "scala": 1},
        "languages_by_workflow": {"python": 39, "rust": 19, "ts": 10, "kotlin": 9, "php": 5,
                                  "csharp": 5, "java": 5, "scala": 4},
        "rules": {"v2 builder": 96},
        "delta8": {"workflows": 56, "families": 20, "kish": 17.23},
    },
    "secondary": {
        "workflows": 26, "families": 18, "kish": 10.24, "instances": 246,
        "H_histogram": {"6": 2, "7": 4, "8": 2, "9": 6, "10": 6, "11": 1, "12": 2, "13": 1,
                        "14": 2},
        "languages_by_family": {"python": 4, "rust": 3, "go": 3, "c": 2, "java": 2, "php": 2,
                                "cpp": 1, "js": 1},
        "languages_by_workflow": {"python": 12, "rust": 3, "go": 3, "c": 2, "java": 2,
                                  "php": 2, "cpp": 1, "js": 1},
        "rules": {"H = family size": 14, "v2 builder": 12},
        "delta8": {"workflows": 18, "families": 12, "kish": 7.36},
    },
}


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="v3 eval corpus maintenance (T2)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fetch", metavar="PARQUET", help="rebuild the reduced SWE-rebench-V2 copy")
    g.add_argument("--digest", action="store_true", help="print both digests and shapes")
    a = ap.parse_args()
    if a.fetch:
        m = fetch(pathlib.Path(a.fetch))
        print(json.dumps({k: v for k, v in m["files"].items()}, indent=1))
    else:
        for sp in SPLITS:
            print(sp, eval_digest(sp))
            print(json.dumps(eval_summary(sp), indent=1))
    sys.exit(0)
