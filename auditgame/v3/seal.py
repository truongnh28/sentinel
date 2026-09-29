"""v3/seal.py -- the eval splits stay sealed until P5 (plan S6, T2; v2's D33 pattern).

What is sealed is not the instance list (its digest is committed in v3/corpus.py) but every
simulation, table or summary run on it.  Five layers (plan S6):

  1. Only digests leave v3/corpus.py (eval_digest, EVAL_SPLIT_SHA256).
  2. A token.  eval_workflows(token, split) is the ONE accessor of eval workflows and takes
     only an Unsealed, which unseal(run_meta) issues when every condition holds:
       a. run_meta["split"] == "eval", passed explicitly;
       b. the Gate-4 file frozen/V3-GATE4.json exists -- written by the user at Gate 4,
          never by a tool -- and names the committed split digests;
       c. the v2 freeze is clean with no PIN CONFLICT (after costs.install(policies), as
          every v2 run reads it), and freeze_v3.header_line() is clean;
       d. the Gate-4 file's digests (v3 manifest, scorecard rules, line-5 table) match the
          live ones (LIVE_DIGESTS);
       e. `git status --porcelain` of auditgame/ is empty.
     Any miss raises SealedSplit with every reason found.
  3. Every unseal() attempt, granted or refused, appends one line to
     frozen/v3-unseal-log.jsonl: the evidence for "one pass" (T6 of sentinel-v3.md).
  4. A static guard (tests/v3/test_infra_seal.py) keeps eval_workflows( and split="eval"
     out of every v3 module and v3 tool but the two P5 tools, and the corpus builders and
     data out of everything but corpus.py and this file.
  5. Summaries refuse eval records on an unclean tree (refusal(), the D33 `refusal`).

In P2 the Gate-4 file does not exist and freeze_v3 / scorecard / line5_table are not built,
so unseal() always refuses: nothing in P2 can load an eval workflow.
"""
from __future__ import annotations

import datetime
import importlib
import json
import pathlib
import subprocess

from v3 import corpus

ROOT = pathlib.Path(__file__).resolve().parent.parent               # auditgame/
GATE_PATH = ROOT / "frozen" / "V3-GATE4.json"
LOG_PATH = ROOT / "frozen" / "v3-unseal-log.jsonl"

#: What the Gate-4 file must carry.  The two split digests are checked against the
#: committed constants; the other three against the live value LIVE_DIGESTS computes.
GATE_FIELDS = ("eval_split_sha256", "secondary_split_sha256", "v3_manifest",
               "scorecard_rules", "line5_table", "signed_by", "date")
#: gate field -> (module, zero-argument function returning the live digest).  The owners
#: build them later: freeze_v3 (T22), scorecard (T17), line5_table (T14).  Until a module
#: or function exists, unseal refuses and says which.
LIVE_DIGESTS = {
    "v3_manifest": ("v3.freeze_v3", "digest"),
    "scorecard_rules": ("v3.scorecard", "rules_digest"),
    "line5_table": ("v3.line5_table", "table_digest"),
}
#: freeze_v3's one-line status, read like freeze.header_line (T22).
V3_FREEZE_HEADER = ("v3.freeze_v3", "header_line")


class SealedSplit(RuntimeError):
    """The eval split is sealed: this tree / this call may not read it (plan S6)."""


_ISSUER = object()
#: Every token unseal() issued in this process.  eval_workflows accepts only these, so an
#: Unsealed made by object.__new__ (skipping __init__) is refused too.
_ISSUED: list = []


class Unsealed:
    """A token that unseal() issued.  Built anywhere else, it refuses to exist."""
    __slots__ = ("run_meta", "granted_at", "digests")

    def __init__(self, issuer, run_meta: dict, granted_at: str, digests: dict):
        if issuer is not _ISSUER:
            raise SealedSplit("an Unsealed token is issued only by seal.unseal()")
        self.run_meta = dict(run_meta)
        self.granted_at = granted_at
        self.digests = dict(digests)


# ---------------------------------------------------------------------------------------
# The conditions
# ---------------------------------------------------------------------------------------


def _clean(header: str) -> bool:
    """v2's D33 reading of a freeze line."""
    return header.startswith("freeze: clean") and "PIN CONFLICT" not in header


def _v3_clean(header: str) -> bool:
    return (header.startswith("freeze") and "clean" in header and "DRIFT" not in header
            and "NONE" not in header and "PIN CONFLICT" not in header)


def _v2_freeze_header() -> str:
    import costs
    import freeze
    import policies as P
    old = costs.install(P)
    try:
        return freeze.header_line()
    finally:
        costs.restore(P, old)


def _live(module: str, func: str):
    """(value, None) or (None, why it is not available)."""
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        return None, f"{module} is not built ({e.__class__.__name__})"
    fn = getattr(mod, func, None)
    if not callable(fn):
        return None, f"{module}.{func}() does not exist"
    return fn(), None


def _git_status() -> str | None:
    try:
        return subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_head() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def reasons(run_meta: dict) -> list:
    """Every reason unseal(run_meta) would refuse ([] = it would grant).  Checked in the
    order of the module docstring; all of them are collected, none short-circuits."""
    out = []
    split = run_meta.get("split") if isinstance(run_meta, dict) else None
    if split != "eval":
        out.append(f"run_meta must say split='eval' explicitly (got {split!r})")

    gate = None
    if not GATE_PATH.exists():
        out.append(f"no Gate-4 file {GATE_PATH.name} (written by the user at "
                   "Gate 4, never by a tool)")
    else:
        try:
            gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            out.append(f"the Gate-4 file is not readable JSON: {e}")
        if gate is not None:
            missing = [f for f in GATE_FIELDS if f not in gate]
            if missing:
                out.append(f"the Gate-4 file lacks {missing}")
            if gate.get("eval_split_sha256") != corpus.EVAL_SPLIT_SHA256:
                out.append("the Gate-4 file's eval_split_sha256 is not the committed "
                           "corpus.EVAL_SPLIT_SHA256")
            if gate.get("secondary_split_sha256") != corpus.SECONDARY_SPLIT_SHA256:
                out.append("the Gate-4 file's secondary_split_sha256 is not the committed "
                           "corpus.SECONDARY_SPLIT_SHA256")

    header = _v2_freeze_header()
    if not _clean(header):
        out.append(f"the v2 freeze is not clean: {header}")
    v3h, why = _live(*V3_FREEZE_HEADER)
    if why:
        out.append(f"freeze_v3: {why}")
    elif not _v3_clean(str(v3h)):
        out.append(f"freeze_v3 is not clean: {v3h}")

    for key, (module, func) in LIVE_DIGESTS.items():
        live, why = _live(module, func)
        if why:
            out.append(f"{key}: {why}")
        elif gate is not None and gate.get(key) != live:
            out.append(f"{key}: the Gate-4 file's digest is not the live one")

    status = _git_status()
    if status is None:
        out.append("git status of auditgame/ could not be read")
    elif status.strip():
        out.append(f"auditgame/ has uncommitted changes ({len(status.splitlines())} path(s))")
    return out


# ---------------------------------------------------------------------------------------
# unseal, eval_workflows
# ---------------------------------------------------------------------------------------


def _log(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True, default=str) + "\n")


def unseal(run_meta: dict) -> Unsealed:
    """Plan S6 layer 2: the token, or SealedSplit with every reason.  Layer 3: the attempt
    is logged BEFORE the answer, granted or not."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    why = reasons(run_meta)
    digests = {"eval_split_sha256": corpus.EVAL_SPLIT_SHA256,
               "secondary_split_sha256": corpus.SECONDARY_SPLIT_SHA256}
    _log({"at": now, "granted": not why, "reasons": why, "git_head": _git_head(),
          "run_meta": run_meta if isinstance(run_meta, dict) else repr(run_meta),
          **digests})
    if why:
        raise SealedSplit("eval stays sealed: " + "; ".join(why))
    token = Unsealed(_ISSUER, run_meta, now, digests)
    _ISSUED.append(token)
    return token


def eval_workflows(token, split: str = "primary") -> list:
    """THE accessor of eval workflows.  `token` must be an Unsealed from unseal(); the
    split is rebuilt and must hash to the committed digest before a workflow is returned."""
    if not isinstance(token, Unsealed) or not any(token is t for t in _ISSUED):
        raise SealedSplit(f"eval_workflows needs an Unsealed token from seal.unseal(), "
                          f"got {type(token).__name__}")
    want = {"primary": corpus.EVAL_SPLIT_SHA256,
            "secondary": corpus.SECONDARY_SPLIT_SHA256}.get(split)
    if want is None:
        raise ValueError(f"split={split!r} is not one of {corpus.SPLITS}")
    if corpus.eval_digest(split) != want:
        raise SealedSplit(f"the rebuilt {split} split does not hash to its committed digest")
    return corpus._materialise(split)


# ---------------------------------------------------------------------------------------
# Layer 5: summaries
# ---------------------------------------------------------------------------------------


def refusal(split: str, header: str) -> str | None:
    """D33: a summary of `split` records built on a tree whose freeze line is `header`.
    None = go.  Eval records are summarised only on a clean freeze."""
    if split != "eval":
        return None
    if not _clean(header) and not _v3_clean(header):
        return f"eval records are summarised only on a clean freeze: {header}"
    return None
