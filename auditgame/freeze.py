"""freeze.py -- the manifest, and the refusal that gives it teeth.

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 8;
README issues "manifest dong bang toan phan" and "harness tu choi policy chua
dong bang".

WHY A MANIFEST AND NOT A PROMISE.  The claim a benchmark has to support is "no
parameter was tuned after the results were seen".  Nothing in a paper can
establish that, and nothing in a repository can either -- unless the
configuration is pinned to a digest BEFORE the numbers are produced and the
harness refuses to run outside it afterwards.  `analysis/gate2_v2.record()`
already does this for the gate-2 cell; this module does it for the run.

WHAT IS IN THE CELL, AND WHY EACH FIELD.  Everything a number depends on and
nothing that it does not, because a manifest that moves for unrelated reasons
gets ignored within a week:

    source digests   the modules that decide behaviour.  Docs, tools and spikes
                     are NOT in here: editing a runbook must not invalidate a
                     result, or nobody will keep the manifest current.
    constants        the values a run is parameterised by, read off the LIVE
                     modules rather than restated -- the same rule gate2_v2
                     follows, so the record cannot drift from the code.
    policy names     both registries, sorted.  A policy that appears after the
                     freeze is the exact thing `require_frozen` refuses.
    table digests    reference/score_table.json, which is GENERATED from pi0:
                     a table rebuilt at another prior is a different experiment
                     wearing the same filename.

WHAT THIS DELIBERATELY DOES NOT DO.  It does not hash the SWE-bench data or the
cloned repositories.  They are large, externally owned and already pinned by
their own commit ids; hashing them would make the manifest expensive to check
and would still not establish provenance.  The instance ids and base commits
travel in the results instead.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent

#: Modules whose text decides what a number is.  A file not in here can be
#: edited without invalidating a frozen result, so the list is the claim.
SOURCE = (
    "build.py", "checkpoints.py", "core.py", "costs.py", "detector.py",
    "experiment.py", "lp.py", "metrics.py", "oracle.py", "policies.py",
    "policies_library.py", "retrieval.py", "runner.py", "scoring.py",
    "attackers.py", "belief.py", "theory.py",
)

#: Generated tables.  score_table.json is built FROM pi0, so it is a separate
#: entry: changing pi0 and forgetting to regenerate is exactly the drift this
#: catches.
TABLES = ("reference/score_table.json",)

MANIFEST_PATH = ROOT / "frozen" / "MANIFEST.json"


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def constants() -> dict:
    """The parameterisation, read off the live modules."""
    import costs
    import detector
    import policies as P
    import retrieval
    import scoring
    return {
        "pi0_world": scoring.PI0,
        "pi_attack": costs.PI_ATTACK,
        "theta": retrieval.THETA,
        "kappa": dict(P.KAPPA),
        "kappa_commit": P.KAPPA_COMMIT,
        "eta_q_cost": P.ETA_Q_COST,
        "beta_default": costs.BETA_DEFAULT,
        "detector_settings": {k: list(v) for k, v in sorted(detector.SETTINGS.items())},
        "chi_anchors": list(P.CHI_ANCHORS),
    }


def manifest() -> dict:
    import attackers
    import policies as P
    import policies_library as L
    return {
        "source": {f: _digest(ROOT / f) for f in sorted(SOURCE)},
        "tables": {f: _digest(ROOT / f) for f in sorted(TABLES)},
        "constants": constants(),
        "policies": sorted(P.REGISTRY),
        "policy_library": sorted(L.LIBRARY),
        "attackers": sorted(attackers.REGISTRY),
    }


def digest(man: dict | None = None) -> str:
    """One hex string for the whole configuration, for a results header."""
    man = manifest() if man is None else man
    blob = json.dumps(man, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def write(path: pathlib.Path = MANIFEST_PATH) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    man = manifest()
    man["digest"] = digest(man)
    path.write_text(json.dumps(man, indent=2, sort_keys=True, ensure_ascii=False)
                    + "\n", encoding="utf-8")
    return man["digest"]


def load(path: pathlib.Path = MANIFEST_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def drift(path: pathlib.Path = MANIFEST_PATH) -> list:
    """What has changed since the freeze, field by field.

    A list rather than a bool on purpose.  "The manifest does not match" sends a
    reader to diff two JSON files by hand; "kappa moved and score_table.json did
    not" tells them what happened.
    """
    frozen = load(path)
    if frozen is None:
        return ["no manifest: nothing has been frozen"]
    live = manifest()
    out = []
    for section in ("source", "tables"):
        for name in sorted(set(frozen[section]) | set(live[section])):
            a, b = frozen[section].get(name), live[section].get(name)
            if a != b:
                out.append(f"{section}/{name}: {'added' if a is None else 'removed' if b is None else 'changed'}")
    for key in sorted(set(frozen["constants"]) | set(live["constants"])):
        if frozen["constants"].get(key) != live["constants"].get(key):
            out.append(f"constants/{key}: {frozen['constants'].get(key)} -> "
                       f"{live['constants'].get(key)}")
    for section in ("policies", "policy_library", "attackers"):
        extra = set(live[section]) - set(frozen[section])
        gone = set(frozen[section]) - set(live[section])
        if extra:
            out.append(f"{section}: added {sorted(extra)}")
        if gone:
            out.append(f"{section}: removed {sorted(gone)}")
    return out


class NotFrozen(RuntimeError):
    """Raised instead of running. The message names what would have been run."""


def require_frozen(policy_name: str, path: pathlib.Path = MANIFEST_PATH) -> None:
    """Refuse a policy the manifest does not know.

    THE POINT OF THE REFUSAL is the case nobody plans for: a policy added after
    the freeze, run once, and reported beside frozen numbers.  It looks exactly
    like a frozen run in the output, so only the harness can tell the difference.

    A MISSING MANIFEST IS NOT AN ERROR HERE.  Most of this project's life is
    spent before the freeze, and a module that refuses to run without one would
    just get bypassed.  It refuses only once a freeze EXISTS -- at which point
    the claim being protected exists too.
    """
    frozen = load(path)
    if frozen is None:
        return
    known = set(frozen["policies"]) | set(frozen["policy_library"])
    if policy_name not in known:
        raise NotFrozen(
            f"policy {policy_name!r} is not in the frozen manifest "
            f"({path.name}, digest {frozen.get('digest', '?')[:12]}). "
            f"Freezing happened at {len(known)} policies; this one was added "
            f"afterwards. Re-freeze deliberately, or run it outside the "
            f"frozen configuration and label the numbers as such.")


def header_line(path: pathlib.Path = MANIFEST_PATH) -> str:
    """One line for a results table: frozen, drifted, or never frozen."""
    frozen = load(path)
    if frozen is None:
        return "freeze: NONE -- these numbers are not pinned to a configuration"
    d = drift(path)
    if not d:
        return f"freeze: clean sha256:{frozen['digest'][:12]}"
    return (f"freeze: DRIFTED from sha256:{frozen['digest'][:12]} "
            f"in {len(d)} place(s): {'; '.join(d[:3])}"
            + (" ..." if len(d) > 3 else ""))
