"""
sealed_trace.py -- THE SEAL LINE, applied to a written-out trace.

Spec: SPEC-P1b-Trace.md Part 1; Task 19's split of `carriers/` from
`carriers-sealed/`, one level up.

WHY THIS FILE EXISTS.  `results/M3-trace.json` is Task 17's named deliverable and
it was committed whole.  Committed whole, it is THE ANSWER KEY: a `poisoned` flag
on every one of the run's item records, the planted payload's full record under
`injected`, and a `correct` verdict beside every quarantine.  That is the ground
truth for every item plus whether each quarantine was right -- exactly what
`.gitignore` already refuses to publish for `carriers-sealed/`, in the words
"publishing it would hand over the labels the benchmark exists to infer".

The acceptance line the artefact has to meet is "the trace carries all nine field
groups of SPEC-P1b Part 1", and that claim needs the trace's SHAPE, not its
labels.  So the artefact is split on the line this codebase already draws
everywhere else:

    <name>-trace.json    PUBLIC.  Committed.  Nine field groups, every write
                         record, every query, every score, every checkpoint --
                         and no evaluator verdict.  Replay's `_rebuild` reads it
                         unchanged: rebuilding a carrier needs content,
                         provenance and timestamps, not labels.
    <name>-sealed.json   THE ANSWER KEY.  gitignored beside `carriers-sealed/`.
                         The three stripped groups, keyed back to the task and
                         the item they came off.

WHAT IS NOT DONE HERE.  The public trace is not "anonymised" and does not pretend
the run was clean: `is_sigma` and the P1..P5 `checkpoints` stay, because they are
two of the nine field groups the acceptance line is about.  What goes is the
per-item VERDICT -- which item was the payload, which write inherited from it,
and whether a quarantine hit.  Someone holding only the public file can replay the
run's mechanics and cannot grade it, which is the whole point of an oracle being
sealed.

WHAT THE SPLIT DOES NOT CLOSE, SAID HERE SO NOBODY REPORTS MORE THAN IT BUYS.
The payload's item_id is still VISIBLE in the public trace -- it has to be: it is
in the carrier snapshots (`before`/`after`, the "state" field group) and in
`retrieved` at sigma, and removing it would mean removing the group whose absence
costs "no replay is possible".  Since the payload is planted by the harness rather
than written by the agent, it is the one id that appears in `after(iota)` without
appearing in `writes(iota)`, so a reader who diffs the two can identify it.

That residual is deliberate and it is not the same thing as what was removed.  The
benchmark's whole premise is that a defender has to INFER which item is poisoned
from observable state; the public trace gives exactly that state.  What it must
never do is hand over the LABEL -- `"poisoned": true` beside the item, the
evaluator's own verdict on each quarantine -- because that is not an inference, it
is the answer key, and it is what an evaluator's ground truth is FOR.  A run whose
payload is trivially inferable from its snapshots is a statement about this run's
injection being harness-planted, and closing it means planting through the agent's
own write path, not censoring the trace.

AND NOTHING SILENTLY SCORES A STRIPPED TRACE.  `load` REFUSES when the sealed
sibling is absent rather than handing back traces whose every item reads
`poisoned` = False.  That would be Rule N3's fake zero in its worst form: a full,
normal-looking grid in which the defence held everywhere because nothing was ever
poisoned.
"""
from __future__ import annotations
import json
import pathlib

#: Fields stripped from the trace itself.  `injected` is the planted payload's
#: FULL record -- item id, content, provenance and its `poisoned` flag -- i.e. the
#: single answer the whole benchmark exists to make an evaluator infer.
GROUND_TRUTH_TRACE_FIELDS = ("injected",)

#: Stripped from every record in `writes`.  `poisoned` is core.Item's own
#: docstring's "GROUND TRUTH -- audit policies must NOT read this"; a published
#: list of them is that rule holding inside the process and broken in the repo.
GROUND_TRUTH_WRITE_FIELDS = ("poisoned",)

#: Stripped from every record in `quarantines`.  `correct` is the manifest's
#: verdict on one quarantine -- true positive or false -- which is the lambda_Q
#: half of the answer key.
GROUND_TRUTH_QUARANTINE_FIELDS = ("correct",)

#: Bumped when the shape of the sealed file changes.  Separate from
#: `core.TRACE_FORMAT` on purpose: the public trace and the answer key are two
#: artefacts with two audiences, and one version number for both means a reader of
#: either cannot tell which one moved.
SEALED_FORMAT = 1


class SealedLabelsMissing(RuntimeError):
    """The sealed half of a trace was asked for and is not there.

    A distinct type because the caller's correct response is distinct: this is not
    a corrupt file and not an empty run, it is a SCORE THAT CANNOT BE COMPUTED --
    the run left the denominator (N3).  Catching it and defaulting to "nothing was
    poisoned" is the one thing that must never happen.
    """


def sealed_path(path) -> pathlib.Path:
    """Where the answer key for `path` lives.

    `results/M3-trace.json` -> `results/M3-sealed.json`, so the pair reads as one
    artefact in two halves rather than as a file and a mysterious suffix.  A path
    that does not end in `-trace` simply gains `-sealed`.
    """
    p = pathlib.Path(path)
    stem = p.stem[:-len("-trace")] if p.stem.endswith("-trace") else p.stem
    return p.with_name(f"{stem}-sealed{p.suffix}")


def split_doc(doc: dict) -> tuple:
    """(public doc, sealed doc) from the full trace document.

    Works on the SERIALISED form -- plain dicts, after `core.dumps` has already
    resolved dataclasses, frozensets and tuples.  Splitting before serialisation
    would mean this file owning a second opinion about how a Topic is written
    down, and two opinions about that is the bug `core.dumps` exists to prevent.
    """
    public_traces, sealed_traces = [], []
    for tr in doc.get("traces", []):
        tr = dict(tr)
        sealed = {"t": tr.get("t"), "task_id": tr.get("task_id")}

        for f in GROUND_TRUTH_TRACE_FIELDS:
            if f in tr:
                sealed[f] = tr.pop(f)

        writes, write_labels = [], {}
        for w in tr.get("writes", []):
            w = dict(w)
            stripped = {f: w.pop(f) for f in GROUND_TRUTH_WRITE_FIELDS if f in w}
            if stripped:
                # Keyed on item_id, not on position: a reader re-attaching these
                # is holding Items, and an index would silently re-label the wrong
                # write the first time the list order changed.
                write_labels[w["item_id"]] = stripped
            writes.append(w)
        tr["writes"] = writes
        sealed["writes"] = write_labels

        quarantines, q_labels = [], {}
        for q in tr.get("quarantines", []):
            q = dict(q)
            stripped = {f: q.pop(f) for f in GROUND_TRUTH_QUARANTINE_FIELDS if f in q}
            if stripped:
                q_labels[q["item_id"]] = stripped
            quarantines.append(q)
        tr["quarantines"] = quarantines
        sealed["quarantines"] = q_labels

        public_traces.append(tr)
        sealed_traces.append(sealed)

    public = dict(doc, traces=public_traces)
    sealed = {"sealed_format": SEALED_FORMAT, "format": doc.get("format"),
              "traces": sealed_traces}
    return public, sealed


def merge_doc(public: dict, sealed: dict) -> dict:
    """Put the answer key back.  Exact inverse of `split_doc`.

    Matched on `t`, and it REFUSES a mismatch rather than merging what lines up:
    two halves of different runs merge into a trace whose every field is real and
    whose labels belong to another workflow, and nothing downstream could tell.
    """
    if sealed.get("format") != public.get("format"):
        raise SealedLabelsMissing(
            f"the sealed half declares trace format {sealed.get('format')!r} and "
            f"the public half {public.get('format')!r}: these are not two halves "
            f"of one run")
    by_t = {s.get("t"): s for s in sealed.get("traces", [])}
    out = []
    for tr in public.get("traces", []):
        s = by_t.get(tr.get("t"))
        if s is None:
            raise SealedLabelsMissing(
                f"task t={tr.get('t')!r} has no entry in the sealed half, so its "
                f"item labels are gone. A missing label is NOT 'not poisoned'")
        if s.get("task_id") != tr.get("task_id"):
            raise SealedLabelsMissing(
                f"task t={tr.get('t')!r} is {tr.get('task_id')!r} in the public "
                f"trace and {s.get('task_id')!r} in the sealed half: these halves "
                f"are from different runs")
        tr = dict(tr)
        for f in GROUND_TRUTH_TRACE_FIELDS:
            tr[f] = s.get(f)
        labels = s.get("writes", {})
        tr["writes"] = [dict(w, **labels.get(w["item_id"], {}))
                        for w in tr.get("writes", [])]
        q_labels = s.get("quarantines", {})
        tr["quarantines"] = [dict(q, **q_labels.get(q["item_id"], {}))
                             for q in tr.get("quarantines", [])]
        out.append(tr)
    return dict(public, traces=out)


def write(path, doc: dict, render) -> dict:
    """Write the two halves.  `core.dump_traces` is the only caller.

    `render` is `core.dumps`, passed in rather than imported: `core` imports this
    module inside `dump_traces`, and a module-level import back would be a cycle.
    """
    path = pathlib.Path(path)
    public, sealed = split_doc(doc)
    path.write_text(render(public), encoding="utf-8")
    sp = sealed_path(path)
    sp.write_text(render(sealed), encoding="utf-8")
    return {"public": path, "sealed": sp}


def load(path) -> list:
    """The traces WITH their labels -- what a re-score needs.

    `core.load_traces` reads the public half alone and is right to: it is the
    reader for the artefact that ships.  Anything that has to grade the run --
    `replay.rescore` scores `det.score(item)`, which draws on 1[poisoned] -- comes
    through here instead, and gets a refusal rather than an unlabelled world.
    """
    import core
    path = pathlib.Path(path)
    sp = sealed_path(path)
    if not sp.is_file():
        raise SealedLabelsMissing(
            f"{path} is the PUBLIC half of a trace and {sp} is not here, so the "
            f"per-item `poisoned` labels, the planted payload and the quarantine "
            f"verdicts are all absent. Scoring anyway would report a run in which "
            f"nothing was poisoned and the defence held everywhere -- Rule N3's "
            f"fake zero, filling a whole grid. The sealed half is gitignored "
            f"beside carriers-sealed/ because it is the answer key; regenerate "
            f"both halves with `python3 m3.py` on a clean carrier root, or score "
            f"only what the public trace can answer (its shape, not its verdicts)")
    public = json.loads(path.read_text(encoding="utf-8"))
    sealed = json.loads(sp.read_text(encoding="utf-8"))
    merged = merge_doc(public, sealed)
    got = merged.get("format")
    if got != core.TRACE_FORMAT:
        raise ValueError(f"trace format {got!r}, this build reads "
                         f"{core.TRACE_FORMAT!r}")
    return [core._trace_from_dict(d) for d in merged["traces"]]


def ground_truth_fields_in(doc: dict) -> list:
    """Every ground-truth field still present in a trace document, by location.

    The checker the acceptance test reads.  It walks the document rather than
    asking `split_doc` what it would strip, so a field added to a trace and not to
    the constants above shows up as UNSTRIPPED instead of as an empty list.
    """
    found = []
    for tr in doc.get("traces", []):
        where = f"traces[t={tr.get('t')}]"
        for f in GROUND_TRUTH_TRACE_FIELDS:
            if tr.get(f) is not None:
                found.append(f"{where}.{f}")
        for i, w in enumerate(tr.get("writes", [])):
            for f in GROUND_TRUTH_WRITE_FIELDS:
                if f in w:
                    found.append(f"{where}.writes[{i}].{f}")
        for i, q in enumerate(tr.get("quarantines", [])):
            for f in GROUND_TRUTH_QUARANTINE_FIELDS:
                if f in q:
                    found.append(f"{where}.quarantines[{i}].{f}")
    return found
