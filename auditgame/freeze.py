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
    pins             the four digests that were ALREADY BEING TAKEN somewhere
                     else -- the gate-2 definition, the frozen payload bank, the
                     judge prompt template, the subset rule.  See `pins()` for why
                     gathering them here is the point rather than a convenience.

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
    #: The hidden-test scoring path.  `oracle.py` alone was not the claim: what
    #: the real oracle scores is decided by which families `registry.FAMILIES`
    #: holds and by what their checks accept.  Registering R1 moved the instances
    #: the oracle can score from 1 to 15 without touching a single byte of
    #: oracle.py, which is exactly the edit this list has to notice.  The R1
    #: yardstick modules (agreement, r1_fixtures, r1_gold, r1_subset) are NOT in
    #: here: they measure the proxy, they do not score a run.
    "hidden_tests/registry.py", "hidden_tests/h1_deprecation.py",
    "hidden_tests/r1_tier.py", "hidden_tests/per_instance.py",
    "hidden_tests/diffutil.py",
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


def pins() -> dict:
    """The digests this project was ALREADY TAKING, gathered into the one cell.

    WHY THIS EXISTS.  Three configurations were pinned by three separate digests,
    each with its own private notion of "clean", and the run-level manifest covered
    none of them:

        gate 2 v2      `analysis/gate2_v2.md5()` over the frozen definition, with
                       `FROZEN_MD5` as its committed declaration.
        payload bank   `payloads/frozen_payloads.json`, which self-seals: the file
                       carries `payloads_sha256` over its own records.
        judge prompt   `fdetect.prompt_sha()` over the frozen prompt template --
                       the only one of the three with no declaration at all, so
                       nothing could tell you it had moved.

    Each of those catches its own file being edited.  None of them catches the OTHER
    two, and `freeze.digest()` caught neither, so "freeze: clean" was printable on a
    run whose gate-2 criterion, payload corpus or judge prompt had changed since the
    numbers were produced.  Scattered digests do not compose; one cell does.

    TWO VALUES PER PIN, NOT ONE, wherever a declaration exists.  A pin whose live
    digest is copied into the manifest and whose own declaration has drifted is
    WORSE than no pin: the manifest goes on reporting clean while the artefact and
    the module that generates it say different things.  `pin_conflicts()` reads that
    second column, and it answers BEFORE any freeze exists -- the drift it finds is
    a fact about the tree, not about the manifest.

    THE IMPORTS ARE LOCAL, the same rule `constants()` already follows.  `freeze`
    is imported by `experiment.py` and by anything that only wants
    `require_frozen`; pulling `analysis.gate2_v2` -- and through it `build`,
    `benign_corpus` and `discriminator` -- into module scope would make a refusal
    check drag the analysis stack behind it, and would put `freeze` in the import
    cycle of modules that `gate2_v2` itself reads.  Measured, the four pins cost
    about 25 ms on a cold call and nothing on the next.
    """
    import payloads
    import retrieval
    from analysis import gate2_v2
    import fdetect

    doc = json.loads((ROOT / "payloads" / "frozen_payloads.json")
                     .read_text(encoding="utf-8"))
    return {
        "gate2_v2": {"live": gate2_v2.md5(), "declared": gate2_v2.FROZEN_MD5},
        "payload_bank": {
            "live": payloads._records_sha256(doc["payloads"]),
            "declared": doc["payloads_sha256"],
        },
        # NO DECLARATION EXISTS for either of these, so `declared` is None: the
        # digest IS the declaration, which is exactly why they belong in a cell
        # something else checks.  A pin with no declaration catches "this moved
        # since the freeze" and CANNOT catch "this disagrees with its artefact",
        # and the two are different claims -- `pin_conflicts` only makes the
        # second, and only where there is a second column to make it against.
        "judge_prompt": {"live": fdetect.prompt_sha(), "declared": None},
        # ALSO a field of gate2_v2's record, and listed separately on purpose: the
        # gate-2 md5 moves for any of twenty fields, so it says THAT the definition
        # changed and never WHICH part.  With both entries, a drift report that
        # names gate2_v2 and subset_rule together localises the edit to the tag
        # rule -- the one field whose silent replacement moved a certify cell from
        # 1/20 to 19/20 splits (docs/preregistration/cong-v2.md S3.9).
        "subset_rule": {"live": retrieval.subset_rule_fingerprint(),
                        "declared": None},
    }


def pin_conflicts(p: dict | None = None) -> list:
    """Pins whose LIVE digest disagrees with their own committed declaration.

    Independent of the freeze, and reported by `header_line` even when no manifest
    exists: `gate2_v2.md5() != FROZEN_MD5` means the gate-2 definition has been
    edited without regenerating `reference/gate2_v2.json`, and that is true whether
    or not anybody has frozen anything.  Folding it into `drift()` would have hidden
    it until the freeze, which is the one moment it is too late to find.
    """
    p = pins() if p is None else p
    return [f"pins/{k}: live {v['live'][:12]} != declared {v['declared'][:12]}"
            for k, v in sorted(p.items())
            if v.get("declared") and v["live"] != v["declared"]]


def manifest() -> dict:
    import attackers
    import policies as P
    import policies_library as L
    return {
        "source": {f: _digest(ROOT / f) for f in sorted(SOURCE)},
        "tables": {f: _digest(ROOT / f) for f in sorted(TABLES)},
        "constants": constants(),
        "pins": pins(),
        "policies": sorted(P.REGISTRY),
        "policy_library": sorted(L.LIBRARY),
        "attackers": sorted(attackers.REGISTRY),
        #: THE HELD-OUT SPLIT, not just the names.  The methodology's tuning table
        #: forbids "changing the held-out set after looking"; the split is a hash
        #: of each name against attackers.HELD_OUT_SHARE, so moving the share or
        #: the hash moves WHICH attackers are held out without renaming any of
        #: them -- invisible to the `attackers` list above.
        "held_out_attackers": sorted(attackers.held_out()),
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
    #: `.get("pins", {})` and not `frozen["pins"]`: a manifest written before pins
    #: existed is a real file on somebody's disk, and a KeyError there would make
    #: the whole drift report unreadable rather than reporting one missing section.
    fpins, lpins = frozen.get("pins", {}), live.get("pins", {})
    for key in sorted(set(fpins) | set(lpins)):
        a = (fpins.get(key) or {}).get("live")
        b = (lpins.get(key) or {}).get("live")
        if a == b:
            continue
        if a is None:
            out.append(f"pins/{key}: added")
        elif b is None:
            out.append(f"pins/{key}: removed")
        else:
            out.append(f"pins/{key}: {a[:12]} -> {b[:12]}")
    for section in ("policies", "policy_library", "attackers", "held_out_attackers"):
        extra = set(live.get(section, [])) - set(frozen.get(section, []))
        gone = set(frozen.get(section, [])) - set(live.get(section, []))
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
    """One line for a results table: frozen, drifted, or never frozen.

    A pin conflict is reported in EVERY one of those three states, including
    "never frozen".  `gate2_v2.md5() != FROZEN_MD5` says the gate-2 definition and
    its committed artefact disagree right now; that is a fact about the tree the
    table was produced on, and holding it back until a freeze exists would hide it
    for the whole period in which it is still cheap to fix.
    """
    conflicts = pin_conflicts()
    tail = (f"  |  PIN CONFLICT: {'; '.join(conflicts)}" if conflicts else "")
    frozen = load(path)
    if frozen is None:
        return ("freeze: NONE -- these numbers are not pinned to a configuration"
                + tail)
    d = drift(path)
    if not d:
        return f"freeze: clean sha256:{frozen['digest'][:12]}" + tail
    return (f"freeze: DRIFTED from sha256:{frozen['digest'][:12]} "
            f"in {len(d)} place(s): {'; '.join(d[:3])}"
            + (" ..." if len(d) > 3 else "") + tail)


def write_operating(path: pathlib.Path = MANIFEST_PATH) -> str:
    """Write THE manifest: from the configuration a run actually uses.

    MEASURED MISTAKE, 2026-09-24.  The first freeze was written from a bare
    interpreter, where policies.KAPPA is still the draft placeholder; every run
    calls costs.install() first and moves to the USD table, so the very first
    run after freezing reported DRIFTED in kappa, kappa_commit and eta_q_cost.
    A manifest has to be written through the SAME installation step the harness
    runs, or it pins a configuration nothing executes.

    The installation is undone afterwards (costs.restore), so calling this from
    a test or a notebook leaves the module state as it found it.
    """
    import costs
    import policies as P
    old = costs.install(P)
    try:
        return write(path)
    finally:
        costs.restore(P, old)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] != ["--write"]:
        raise SystemExit("usage: python3 freeze.py --write   "
                         "(writes frozen/MANIFEST.json from the operating configuration)")
    print(write_operating())
