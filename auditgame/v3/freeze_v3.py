"""v3/freeze_v3.py -- the v3 manifest, layered on the v2 freeze (T22; D7.freeze, D33).

Draft S7 "Freezing": "Defender policies and the attacker library are serialised and hashed
before final evaluation; the evaluation harness refuses to run a policy whose hash is not in
the frozen manifest."  This module is that manifest for v3, built on v2's freeze.py and on
freeze_d35.py's layering: the base freeze (frozen/MANIFEST.json, sha256:c789fa7362e0) and
the D35 addendum's freeze stay clean and untouched; this manifest pins what v3 adds.

WHAT IS IN THE CELL (plan T22):
    base          the v2 and D35 manifest digests the v3 freeze sits on
    source        sha256 of every v3/*.py
    dcm           sha256 of every file under v3/dcm/ (the per-task DCM shards)
    files         reference/v3_tuned.json (T18) and the v3 run tools; None = not built yet
    line5_table   v3.line5_table.table_digest() (T14); None = not built yet
    registries    every policy name a run may build: baselines (T8), the block schedule
                  (T16), the library (T11), Sentinel's V3_REGISTRY (T15), and the grid's
                  systems (T22) -- require_frozen refuses anything else
    attackers     the 18 scripted names, the held-out split, development, the D18 tuning
                  columns, the rule-BR columns, the O5 Delta classes, the BR eps grid
    splits        EVAL_SPLIT_SHA256 and SECONDARY_SPLIT_SHA256 (each a digest of the
                  instance list IN pinned order) and the dev workflow order
    grid          grid.definition_digest(): every unit, trim and drop
    scorecard     scorecard.rules_digest() (T17)
    config        PRIMARY, the sensitivities, the O1-O16 values

When to write it: at P4, after tuning and the final line-5 table (plan S1 "P4 ... freeze"),
through the operating installation, like v2's freeze.write_operating:
    ../.venv/bin/python -m v3.freeze_v3 --write
In P2 no v3 manifest exists; header_line() then reads "freeze-v3: NONE", which seal.unseal
treats as not clean, so eval stays sealed.

Imports of other tasks' modules are local and tolerant (a module not built yet pins None):
a manifest that moves when one of them lands is exactly right before the freeze, and after
the freeze it is DRIFT.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import pathlib

import freeze
import freeze_d35

ROOT = pathlib.Path(__file__).resolve().parent.parent               # auditgame/
V3_DIR = ROOT / "v3"
DCM_DIR = V3_DIR / "dcm"
MANIFEST_PATH = ROOT / "frozen" / "MANIFEST-V3.json"
#: Plan T22: files outside v3/ that decide a v3 number.  Absent ones pin None.
FILES = ("reference/v3_tuned.json", "tools/v3_run.py", "tools/v3_tune.py",
         "tools/v3_build_table.py", "tools/v3_headline_rollout.py")
PREFIX = "freeze-v3"
SECTIONS = ("base", "source", "dcm", "files", "line5_table", "registries", "attackers",
            "splits", "grid", "scorecard", "config")


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _optional(module: str, attr: str):
    """getattr(import module, attr), or None when the owning task has not landed it."""
    try:
        mod = importlib.import_module(module)
    except ImportError:
        return None
    return getattr(mod, attr, None)


def _with_costs(fn):
    """Run fn under costs.install(policies), as every v2 run reads the v2 freeze."""
    import costs
    import policies as P
    old = costs.install(P)
    try:
        return fn()
    finally:
        costs.restore(P, old)


# ---------------------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------------------


def registries() -> dict:
    from v3 import baselines as BL
    from v3 import budget as BU
    from v3 import grid as G
    lib = _optional("v3.library", "LIBRARY")
    reg = _optional("v3.sentinel", "V3_REGISTRY")
    return {
        "baselines": sorted(BL.ALL),
        "budget": [BU.BlockSchedule.name],
        "library": None if lib is None else sorted(lib),
        "sentinel": None if reg is None else sorted(reg),
        "grid_systems": sorted(G.all_systems()),
    }


def known_policies(man: dict) -> set:
    """Every name a manifest lets the harness build."""
    r = man.get("registries", {})
    out = set()
    for key in ("baselines", "budget", "library", "sentinel", "grid_systems"):
        out |= set(r.get(key) or ())
    return out


def _attackers() -> dict:
    from v3 import attackers as A
    return {
        "scripted": sorted(A.SCRIPTED),
        "held_out": list(A.held_out()),
        "development": list(A.development()),
        "tuning": list(A.tuning_attack_names()),
        "rule_br": [a.name for a in A.br_attacks()],
        "delta_classes": [dc.name for dc in A.attacker_delta_menu()],
        "br_eps": list(A.BR_EPS),
        "eps_max": A.EPS_MAX,
    }


def _splits() -> dict:
    from v3 import corpus as K
    return {"eval_split_sha256": K.EVAL_SPLIT_SHA256,
            "secondary_split_sha256": K.SECONDARY_SPLIT_SHA256,
            "dev_order": [wf.wf_id for wf in K.dev_workflows()]}


def _config() -> dict:
    from v3 import config as C
    return {"primary": C.PRIMARY.as_dict(),
            "sensitivities": {n: w.as_dict() for n, w in C.sensitivities()},
            "decided_o": C.DECIDED_O}


def manifest() -> dict:
    from v3 import grid as G
    from v3 import scorecard as SC
    base, d35 = freeze.load(), freeze_d35.load()
    table = _optional("v3.line5_table", "table_digest")
    return {
        "base": {"v2": base["digest"] if base else None,
                 "d35": d35["digest"] if d35 else None},
        "source": {p.name: _sha(p) for p in sorted(V3_DIR.glob("*.py"))},
        "dcm": {p.relative_to(DCM_DIR).as_posix(): _sha(p)
                for p in sorted(DCM_DIR.rglob("*"))
                if p.is_file() and "__pycache__" not in p.parts},
        "files": {f: (_sha(ROOT / f) if (ROOT / f).exists() else None) for f in FILES},
        "line5_table": table() if callable(table) else None,
        "registries": registries(),
        "attackers": _attackers(),
        "splits": _splits(),
        "grid": G.definition_digest(),
        "scorecard": SC.rules_digest(),
        "config": _config(),
    }


def digest(man: dict | None = None) -> str:
    """The live v3 manifest digest (seal.LIVE_DIGESTS["v3_manifest"]).  A written
    manifest's own "digest" field is left out, so digest(load()) is its frozen value."""
    man = manifest() if man is None else {k: v for k, v in man.items() if k != "digest"}
    return hashlib.sha256(json.dumps(man, sort_keys=True, separators=(",", ":"))
                          .encode()).hexdigest()


def write(path: pathlib.Path | None = None) -> str:
    path = MANIFEST_PATH if path is None else path
    man = manifest()
    man["digest"] = digest(man)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(man, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return man["digest"]


def write_operating(path: pathlib.Path | None = None) -> str:
    """Write the manifest through the operating installation (v2's measured mistake of
    24/09: a manifest written from a bare interpreter pins what nothing executes)."""
    path = MANIFEST_PATH if path is None else path
    return _with_costs(lambda: write(path))


def load(path: pathlib.Path | None = None) -> dict | None:
    path = MANIFEST_PATH if path is None else path
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def drift(path: pathlib.Path | None = None) -> list:
    """What changed since the v3 freeze, section by section (file by file for files)."""
    path = MANIFEST_PATH if path is None else path
    frozen = load(path)
    if frozen is None:
        return ["no v3 manifest: nothing has been frozen"]
    live, out = manifest(), []
    for sec in SECTIONS:
        a, b = frozen.get(sec), live.get(sec)
        if a == b:
            continue
        if isinstance(a, dict) and isinstance(b, dict) and sec in ("source", "dcm", "files"):
            for k in sorted(set(a) | set(b)):
                if a.get(k) != b.get(k):
                    kind = ("added" if k not in a else "removed" if k not in b else "changed")
                    out.append(f"{sec}/{k}: {kind}")
        else:
            out.append(f"{sec}: changed")
    return out


# ---------------------------------------------------------------------------------------
# The refusal and the header
# ---------------------------------------------------------------------------------------


class NotFrozen(RuntimeError):
    """Raised instead of running a policy the v3 manifest does not know."""


def require_frozen(policy_name: str, path: pathlib.Path | None = None) -> None:
    """Refuse a policy absent from the v3 manifest (draft S7 "Freezing").  As in v2, a
    missing manifest refuses nothing: before P4 every run is a dev run, and the eval split
    is sealed by seal.unseal, which needs this manifest clean."""
    path = MANIFEST_PATH if path is None else path
    frozen = load(path)
    if frozen is None:
        return
    known = known_policies(frozen)
    if policy_name not in known:
        raise NotFrozen(
            f"policy {policy_name!r} is not in the frozen v3 manifest ({path.name}, "
            f"digest {frozen.get('digest', '?')[:12]}); {len(known)} policies were frozen. "
            f"Re-freeze deliberately, or run it outside the frozen configuration and label "
            f"the numbers as such.")


def header_line(path: pathlib.Path | None = None) -> str:
    """One line: the v3 freeze, then the D35 line, which carries the v2 base line.  Read
    under costs.install(policies) (done here), so the v2 line is the one every v2 run
    reads.  seal.unseal reads it as clean only when it starts with "freeze", says "clean",
    and holds no DRIFT, NONE or PIN CONFLICT anywhere -- base lines included."""
    path = MANIFEST_PATH if path is None else path
    base = _with_costs(freeze_d35.header_line)
    frozen = load(path)
    if frozen is None:
        return f"{PREFIX}: NONE -- no v3 manifest  |  {base}"
    d = drift(path)
    if d:
        return (f"{PREFIX}: DRIFTED from sha256:{frozen['digest'][:12]} in {len(d)} "
                f"place(s): {'; '.join(d[:3])}{' ...' if len(d) > 3 else ''}  |  {base}")
    if frozen.get("base", {}).get("v2") != (freeze.load() or {}).get("digest"):
        return f"{PREFIX}: DRIFTED -- the v2 base digest moved  |  {base}"
    return f"{PREFIX}: clean sha256:{frozen['digest'][:12]}  |  {base}"


def clean(line: str) -> bool:
    """The strict reading: v3, D35 and v2 all clean, no pin conflict."""
    return (line.startswith(f"{PREFIX}: clean") and freeze_d35.clean(line.split("  |  ", 1)[-1])
            and "DRIFT" not in line and "NONE" not in line and "PIN CONFLICT" not in line)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--write"]:
        print(write_operating())
    elif sys.argv[1:] == ["--header"]:
        print(header_line())
    else:
        raise SystemExit("usage: python -m v3.freeze_v3 --write | --header   "
                         "(--write belongs to P4, after tuning and the final table)")
