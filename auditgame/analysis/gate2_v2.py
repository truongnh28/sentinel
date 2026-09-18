"""
gate2_v2.py -- THE FROZEN DEFINITION of gate 2, version 2.

Spec: eval/SPEC-AuditGame-SE.md Part 0; QUYET-DINH.md question 8; review II.3
("close all three holes AT ONCE, freeze the definition with a date and an md5,
then run the certification table ONCE").

WHY A RECORD AND NOT A PARAGRAPH.  Gate 2 certifies that a poisoned event is not
separable from benign drift on F_match.  That sentence is only a claim if every
parameter behind it is pinned: WHICH features, WHICH seed rule builds the corpus,
WHICH payload length, WHICH theta, and WHICH summary of WHICH splits at WHICH
ceiling.  v1 left three of those loose -- `topic` was outside the feature set,
`_one_event` ran every workflow at the literal seed 1, and the payload's length
moved with epsilon -- and two of the three erred in OPPOSITE directions, so the
verdict was not merely imprecise, it was uninterpretable.  This module is the
single hash cell those parameters now sit in, built the way `metrics.config_sha`
builds its own: a canonical byte string over named fields, one digest, and a test
that goes red when any field moves.

NO VERDICT LIVES HERE.  The record carries the DEFINITION and nothing measured
against it -- `verdict` says so in as many words, and a test asserts the record
contains no AUC at all.  Running the certification table is the NEXT step, on
purpose: a definition that can still be edited after the table is read is a
definition that can be edited to suit it.

THE DIGEST IS md5 AND THAT IS NOT A SECURITY CLAIM.  Like `config_sha`'s sha256
it is a CHANGE DETECTOR over a canonical serialisation of parameters this project
itself writes; nothing adversarial reaches it.  md5 is what the task specified and
what the spike quotes, so it is what is pinned.

STDLIB ONLY, like `discriminator` and `benign_corpus`: gate 2 imports this and the
measurement core has to stay clone-and-run (ABC T.6).
"""
from __future__ import annotations
import hashlib
import json
import pathlib

import build
import core
import retrieval
from analysis import benign_corpus, discriminator

#: The day the definition was frozen.  It is a FIELD of the hashed record, not a
#: comment beside it: a freeze whose date is not in the cell can be back-dated.
FROZEN_DATE = "2026-09-18"

#: The committed artefact a reader cites.  Same relationship as
#: `reference/score_table.json` has to `reference/gen_score_table.py`: the file is
#: GENERATED (see `write()`), never hand-edited, and a test asserts it still agrees
#: with the live modules.
PATH = str(pathlib.Path(__file__).resolve().parent.parent
           / "reference" / "gate2_v2.json")

#: THE PIN.  Any edit to any field of `record()` moves this, so moving it is a
#: visible edit to the criterion rather than a quiet one.  Regenerate with
#:     python3 -c "from analysis import gate2_v2; gate2_v2.write()"
#: and the test that pins it will tell you the new digest.
FROZEN_MD5 = "45274180520227436a90f03ca1dd21db"

#: THE CERTIFICATION PROTOCOL, owned HERE because the record is what pins it.
#: `tests/gate2_validity/test_benign_corpus.py` imports these instead of defining
#: its own copies, so the criterion the gate runs and the criterion the digest
#: covers are one object.
#:
#: WHY THE SCREEN PHASE IS IN THE CELL AT ALL (review II ruling 5).  The record's
#: `criterion` field pins the CERTIFY phase -- the mean CI95 upper bound over the
#: split seeds.  But the gate's red cell is decided by the SCREEN phase, which
#: runs first, on a different sample size, under a different summary, and can end
#: the test before the certify phase is ever reached.  Pinning only the criterion
#: that runs second is pinning the half that did not decide the verdict.
N_SCREEN = 80             # phase 1 sample: a RANKING question, deliberately cheap
N_CERTIFY = 900           # phase 2 sample: question 8's event count (a CAP)
EPSILON_GRID = (0.0, 0.2, 0.4, 0.7, 1.0)
DELTAS = (0, 2, 4)
SCREEN_CRITERION = ("median_point_estimate_over_split_seeds <= ceiling at EVERY "
                    "delta; eps_star = max passing epsilon")


def record(**overrides) -> dict:
    """The definition, read off the LIVE modules rather than restated here.

    Every field is fetched from the module that owns it -- the feature set from
    `discriminator.F_MATCH`, the seed rule from `benign_corpus.EVENT_SEED_RULE`,
    L from `build.PAYLOAD_LENGTH`, theta from `retrieval.THETA`, the split set and
    the fold size from `discriminator` -- so the record cannot drift away from the
    code the way a copied constant does.  That is the same reason
    `tests/gate2_validity/test_benign_corpus.py` asserts F_MATCH equals
    `Item.surface()`'s keys instead of listing four names twice.

    `overrides` exists for ONE caller: the test that perturbs one field at a time
    and requires the digest to move.  A hash cell that does not react to a field
    is a hash cell that does not cover it, and the only honest way to show it
    reacts is to move something.
    """
    rec = dict(
        version=2,
        date=FROZEN_DATE,
        #: F_match -- EXACTLY core.Item.surface()'s keys.  `topic` is the v2
        #: addition; see core.topic_code for the choice and its three limits.
        features=sorted(discriminator.F_MATCH),
        #: How the corpus seeds the agent run each event is read off.  P8.
        event_seed_rule=benign_corpus.EVENT_SEED_RULE,
        #: The frozen total content length of the payload.  With it fixed, `size`
        #: stops varying with epsilon and the size channel closes by construction
        #: -- EXCEPT where the tag alone is already as wide as L, which the rule
        #: below states rather than leaving to a reader to discover.
        payload_length_L=build.PAYLOAD_LENGTH,
        payload_length_rule=build.PAYLOAD_LENGTH_RULE,
        #: WHICH of `core.TOPIC_CODE_CANDIDATES` the `topic` column is.  Four
        #: defensible lexicographic codes of a token set span AUC 0.45 to 1.00 on
        #: this corpus, so "features includes topic" does not pin the feature: an
        #: under-specified topic feature is how the `sorted()` artefact recurs.
        topic_feature=core.TOPIC_CODE_CHOICE,
        #: The frozen retrieval threshold, already in metrics.config_sha's cell --
        #: repeated here because the corpus's dormancy filter is stated against it.
        theta=retrieval.THETA,
        #: The criterion, named rather than described: the MEAN of the 95% CI
        #: UPPER bounds over the declared split set.  Not the max (its expectation
        #: grows with the size of the set) and not the point estimate (at n=310 the
        #: standard error is 0.023).  See discriminator.summarise_splits.
        criterion="mean_ci95_upper_over_split_seeds",
        #: The criterion that runs FIRST and that actually decides the red cell.
        screen_criterion=SCREEN_CRITERION,
        #: The grid the screen ranks over.  A criterion stated without its grid is
        #: not reproducible: "no epsilon reaches the ceiling" is a claim about a
        #: SET of epsilons.
        epsilon_grid=list(EPSILON_GRID),
        deltas=list(DELTAS),
        n_events=dict(screen=N_SCREEN, certify=N_CERTIFY),
        split_seeds=list(discriminator.SPLIT_SEEDS),
        test_fraction=0.4,
        ceiling=0.56,
        #: The corpus the criterion is read off, pinned so that "gate 2 certifies"
        #: names one population.  `natural`, `per_event` and `holdout` joined the
        #: cell at review II ruling 5: the choice of benign background alone moved
        #: the cell by 0.0421 under the definition as shipped -- more than the
        #: criterion's own margin -- so a record without it lets two people satisfy
        #: the same md5 and report different numbers.
        corpus=dict(pool=benign_corpus.POOL, carrier=benign_corpus.CARRIER,
                    h=benign_corpus.H, corpus_seed=benign_corpus.SEED,
                    natural=benign_corpus.NATURAL,
                    per_event=benign_corpus.PER_EVENT,
                    holdout=benign_corpus.HOLDOUT),
        verdict="NOT DRAWN -- certification is a separate step",
    )
    rec.update(overrides)
    return rec


def canonical(rec: dict | None = None) -> str:
    """The exact bytes the digest is taken over.

    `sort_keys=True` and `ensure_ascii=False`, so the serialisation depends on the
    VALUES and not on dict insertion order or on the ASCII-escaping of a
    Vietnamese string -- the same trap `core.dumps` closes for traces, one level
    up.  A digest over a non-canonical form would move when nothing moved.
    """
    return json.dumps(record() if rec is None else rec,
                      sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def md5(rec: dict | None = None) -> str:
    """md5 over `canonical(rec)`.  See the module docstring on why md5."""
    return hashlib.md5(canonical(rec).encode("utf-8")).hexdigest()


def write(path: str | None = None) -> str:
    """(Re)generate the committed artefact.  DO NOT HAND-EDIT the JSON.

    Same warning `reference/score_table.json` carries in its own provenance block:
    edit the code and regenerate, or the artefact and the thing it claims to
    describe say different things and the test that compares them goes red --
    which is the test doing its job, not a nuisance.
    """
    rec = record()
    doc = dict(what="gate 2 v2 -- the FROZEN definition, not a result",
               md5=md5(rec), generated_by="analysis/gate2_v2.py::write",
               warning="Generated file. Do not hand-edit -- change the code and "
                       "regenerate, or the pinned md5 and the live definition "
                       "part company.",
               record=rec)
    p = pathlib.Path(PATH if path is None else path)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False,
                            sort_keys=True) + "\n", encoding="utf-8")
    return doc["md5"]


if __name__ == "__main__":
    print(write())
