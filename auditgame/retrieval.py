"""
retrieval.py -- GRADED RETRIEVAL (R).  Spec: docs/thesis/pipelines/SPEC-R-Truy-xuat.md

Problem: `CarrierStore.retrieve` matches topic strings EXACTLY, so the retrieval
function takes only two values {0, 1}.  AgentPoison attacks by optimising a
trigger in embedding space -- against a two-valued function there is NOTHING TO
OPTIMISE.  And `epsilon`, one of the four attacker knobs (k, iota, sigma,
epsilon), has no surface to act on: measured, the payload at eps=0.05 and
eps=0.95 is byte-for-byte IDENTICAL.

Fix: Jaccard similarity over MODULE TOKEN SETS.  Deterministic (no learning, no
sampling), no third-party dependency, and exact matching is the SPECIAL CASE
theta=1.

The trade-off the older docs conflated: exact matching buys bit-exact REPLAY, it
does NOT buy oracle determinism -- the oracle scores patches with pytest plus an
AST diff and never touches retrieval.  Determinism does not require discreteness,
so we get both.

WIRED IN (advisor question 3, answered).  `core.CarrierStore.retrieve` now routes
every lookup through `retrieved()` at the frozen THETA below, and `build.inject`
stamps the payload with `payload_topic_like()`.  The module note that used to sit
here -- "not yet wired into core.CarrierStore" -- described the state this file
was stranded in, not a design limit.
"""
from __future__ import annotations
import hashlib
import math

class Topic(frozenset):
    """A token set that stringifies CANONICALLY, as "|".join(sorted(...)).

    Why a subclass rather than a bare `frozenset`.  A frozenset's own str()/repr()
    walks its internal hash table, whose layout depends on Python's per-process
    string-hash randomisation (PYTHONHASHSEED).  Every topic in this system ends
    up inside an f-string (the payload's content template, the agent's note
    templates) or inside `core.seed_of`, which stringifies its arguments -- and
    `Item.__post_init__` hashes seed_of(carrier, topic, content, ...) into
    item_id, which in turn seeds detector.score.  So a bare frozenset here would
    give the SAME payload a different id, and therefore a different SCORE, on two
    runs of the same command.  That is the failure the project's hash() ban exists
    to prevent (core.seed_of), arriving through frozenset ordering instead.

    This lived in swebench_dataset, where only DATASET topics passed through it.
    It belongs here now because retrieval CONSTRUCTS topics as well: payload_topic
    returns a subset that no dataset ever saw, and that subset is stamped onto the
    payload item.  A canonical form defined only at the dataset boundary would
    have missed exactly the topics this module makes up.

    isinstance(x, frozenset) is still True, and equality / Jaccard / use as a dict
    key are all unaffected -- none of them depend on iteration order.  Only string
    conversion does.
    """
    def __str__(self) -> str:
        return "|".join(sorted(self))

    __repr__ = __str__

#: THE FROZEN RETRIEVAL THRESHOLD.  Derived from the measured |topic|
#: distribution in docs/reports/chot_theta.md, WRITTEN AND COMMITTED BEFORE the
#: resulting workflow count was looked at.  The short form of that argument:
#:
#:   * theta only distinguishes values that sit ON the attainable-sim grid; at
#:     the measured median |topic| = 4 (both pools) that grid is
#:     {0.25, 0.5, 0.75, 1.0} for a payload subset and {1/7, 1/3, 0.6, 1.0} for
#:     two full task topics.  A theta between two grid points IS the point above
#:     it, wearing a different number.
#:   * 1.0 is the `==` behaviour this module exists to generalise, and it sends
#:     every epsilon < 1 back to a fake harm of 0.
#:   * 0.25 admits EVERY epsilon, because payload_topic takes
#:     k = max(1, ceil(eps*m)) >= 1 -- the budget loses its failing end, which is
#:     the same defect that disqualified VerbosityAttack.
#:   * 0.75 needs |A & B| >= 6m/7, i.e. IDENTICAL topics for every m <= 6 -- and
#:     m <= 6 covers 95.4% of SWE-bench Verified.  It collapses back to exact
#:     matching on almost the whole corpus.
#:
#: 0.5 is what is left: the only grid point with a real graded band at the size
#: the corpus actually has.  It is a FROZEN parameter, in the same hash cell as
#: pi_0 / the aggregation / tau_sel (SPEC-R Part 2.2) -- not a knob.  Do not move
#: it to change how many workflows survive a filter; that is the one thing the
#: derivation was written down in advance to prevent.
THETA = 0.5


def as_topic(value) -> Topic:
    """Any topic representation -> a token SET, so one retrieval serves both pools.

    The mock's topic is a plain `str` ("orm"); swebench's is a
    `swebench_dataset.Topic`, a frozenset subclass.  A string becomes the
    ONE-TOKEN set {value}, which is what makes exact matching survive the switch:
    for two single-token sets Jaccard takes only {0, 1}, so `sim >= theta` is
    `a == b` for EVERY theta in (0, 1].  The mock therefore cannot move, at any
    theta, and if it does move that is a bug in the wiring rather than a
    consequence of it.

    The empty string is a legitimate one-token topic and stays one: collapsing it
    to the empty set would make sim() return 0.0 by the two-empty-sets
    convention, so two items with topic "" would stop matching each other when
    `==` says they do.
    """
    if isinstance(value, str):
        return Topic({value})
    if isinstance(value, frozenset):
        return value
    if isinstance(value, (set, list, tuple)):
        return Topic(value)
    raise TypeError(
        f"topic {value!r} is a {type(value).__name__}: retrieval understands a "
        f"str (one token) or a token set. Guessing a conversion here would "
        f"silently change which items a task retrieves.")


def topic_of(files) -> Topic:
    """Files touched by a gold patch -> set of module tokens.

        django/db/models/query.py  ->  {django, db, models, query}

    No model, no embedding -- just string splitting.  Being a SET, it does not
    depend on file order, which is what lets traces replay.
    """
    tokens = set()
    for path in files:
        for part in str(path).split("/"):
            part = part.rsplit(".", 1)[0] if "." in part else part
            if part:
                tokens.add(part)
    return Topic(tokens)


def sim(a: Topic, b: Topic) -> float:
    """Jaccard.  |A & B| / |A | B|.  Two empty sets are 0 by convention."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def retrieved(item_topic: Topic, task_topic: Topic, theta: float) -> bool:
    """theta=1 with equal token sets <=> exact match (today's behaviour)."""
    return sim(item_topic, task_topic) >= theta


def canonical_topic_string(topic) -> str:
    """A topic's CANONICAL identity string, `"|".join(sorted(tokens))`, for ANY
    shape `as_topic` accepts.

    THE ONE DEFINITION.  `core._canonical_topic_string` delegates here rather than
    re-joining, and `subset_priority` keys on it: a project with two spellings of
    "a topic's canonical form" has two, and they drift.

    The re-wrap in `Topic` is the whole point and is not redundant.  `as_topic`
    hands a bare `frozenset` straight BACK (it is already a token set), and a bare
    frozenset's `str()` walks its internal hash table, whose layout depends on
    PYTHONHASHSEED.  Anything keyed on that string then moves between two runs of
    the same command.  Re-wrapping forces `Topic.__str__`.
    """
    return str(Topic(str(t) for t in as_topic(topic)))


#: THE SALT the de-biased subset order is drawn under, named because it is a FREE
#: PARAMETER and naming it is what lets the frozen record pin it.
#:
#: NOTHING IN THE ATTACK MODEL PREFERS ONE STRING.  The model asks for a subset
#: drawn independently of the alphabet; every salt gives one, and each gives a
#: DIFFERENT one.  Measured over a 17-salt family (this literal plus
#: "payload_topic#1" .. "#16", docs/preregistration/cong-v2.md SS3.9), the certify cells move
#: far enough that cell verdicts change in both directions -- so the salt is not
#: an implementation detail, it is a parameter of the measurement, and it belongs
#: in the hash cell beside theta and the ceiling.  It was fixed in the
#: pre-registration (c85a936) before any number was measured and has not been
#: changed since; what was missing was not the discipline but the DISCLOSURE.
SUBSET_SALT = "payload_topic"

#: The rule in one sentence, for a reader.  It is pinned for readability; the
#: thing that makes the pin BITE is `subset_rule_fingerprint`, which digests what
#: the rule DOES rather than what it says it does.
SUBSET_RULE = ("k = max(1, ceil(eps * |B|)) tokens of B, ordered by "
               "(core.seed_of(SUBSET_SALT, canonical_topic_string(B), token), "
               "token); nested in eps")

#: The probe `subset_rule_fingerprint` is taken over.  FIXED LITERALS, so the
#: fingerprint is a property of the rule and not of whatever corpus is loaded.
#: The shapes are chosen to exercise what the rule can get wrong: an 8-token
#: topic wide enough that an alphabetical prefix is visible as one, a realistic
#: 5-token path set, a 3-token set whose grid is coarse, a 2-token set at the
#: alphabet's two ends, and a 1-token set (the mock's shape, where every rule
#: agrees and so the fingerprint must NOT depend on it alone).
_FINGERPRINT_PROBE = (
    ("alpha", "bravo", "delta", "echo", "golf", "hotel", "india", "kilo"),
    ("db", "django", "models", "query", "sql"),
    ("core", "forms", "utils"),
    ("apple", "zebra"),
    ("solo",),
)
_FINGERPRINT_EPS = (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0)


def subset_rule_fingerprint() -> str:
    """A digest of WHICH TOKENS the subset rule picks, over a fixed probe.

    WHY A BEHAVIOURAL DIGEST AND NOT A PROSE FIELD.  `analysis.gate2_v2` freezes
    the gate definition by hashing named fields, and a field whose value is a
    SENTENCE can go stale while staying green: the sentence still reads
    "pseudorandom subset" after the salt moves, after `sorted()` comes back, after
    the priority is keyed on the token alone.  This digest moves when any of those
    change, because it is taken over the rule's OUTPUT.  It is the same reason
    `screen_criterion` now names the statistic it reads instead of describing it.

    It is NOT a security digest (see gate2_v2's module docstring on md5): nothing
    adversarial reaches it.  It is a change detector.
    """
    lines = []
    for toks in _FINGERPRINT_PROBE:
        target = Topic(toks)
        for eps in _FINGERPRINT_EPS:
            lines.append(f"{target}@{eps}={payload_topic(target, eps)}")
    return hashlib.blake2b("\n".join(lines).encode("utf-8"),
                           digest_size=8).hexdigest()


def subset_priority(target: Topic, token: str, _key: str | None = None) -> int:
    """The de-biased order `payload_topic` picks its k tokens in.

    A pseudorandom but DETERMINISTIC priority, drawn through `core.seed_of` --
    blake2b over a string, never `hash()`, never a frozenset's iteration order.
    Two tokens of the same target never tie in practice, and `payload_topic`
    tie-breaks on the token itself anyway, so the order is total.

    WHY IT IS KEYED ON THE TARGET AS WELL AS ON THE TOKEN.  A priority that
    depended on the token alone would be ONE fixed pseudorandom permutation of the
    whole token universe: still uncorrelated with the alphabet, but the same token
    would be preferred (or skipped) in every topic it appears in, which is a
    global signature of its own.  Keying on the target makes the draw independent
    across topics.

    THE KEY IS `canonical_topic_string(target)`, NOT `str(target)`.  This
    docstring used to assert PYTHONHASHSEED-stability on the ground that
    `str(target)` is `Topic.__str__` -- true for a `Topic` and FALSE for a bare
    `frozenset`, which `as_topic` passes straight through and `payload_topic_like`
    routes through.  Measured, the same call returned ['django'] / ['query'] /
    ['query'] under PYTHONHASHSEED 0 / 1 / 2.  No published number depended on it
    (production callers pass `task.topic`, a `Topic`), and for a `Topic` the two
    spellings are the same string, so nothing moved when this was fixed -- but the
    property the docstring claims is now true of every input the function accepts,
    which is the same guard `core._canonical_topic_string` already applied 30
    lines away.

    `core` is imported HERE rather than at module scope because `core` imports
    `retrieval` at module scope; the deferred import resolves at call time, by
    which point both modules exist.  Duplicating blake2b here instead would give
    the project two seeding rules, which is the thing `seed_of` exists to prevent.

    `_key` IS THE HOISTED CANONICAL STRING, nothing more.  The key is a property
    of the TARGET, so `payload_topic` derives it ONCE and passes it down rather
    than making the sort key re-derive the same string |B| times per payload per
    epsilon over a 2248-topic supply.  Omitted, it is derived here, so every other
    caller and every mutation test still exercises the whole expression -- the
    order stays defined in exactly ONE place.

    THE SALT IS READ AT CALL TIME, from the module global, so that the salt
    sensitivity table in docs/preregistration/cong-v2.md SS3.9 can be REPRODUCED rather than
    taken on trust -- the same idiom `core.TOPIC_CODE_CHOICE` uses for the
    four-feature table.  It is a frozen field of `analysis.gate2_v2.record()`:
    changing it moves the digest.
    """
    import core
    return core.seed_of(SUBSET_SALT,
                        canonical_topic_string(target) if _key is None else _key,
                        token)


def payload_topic(target: Topic, eps: float) -> Topic:
    """Token set the attacker picks for the payload -- a SUBSET of task sigma's.

    |A| = ceil(eps * |B|), taken in a DETERMINISTIC PSEUDORANDOM order
    (`subset_priority`): reproducible, no sampling, and -- unlike the sorted order
    this used to take -- UNCORRELATED WITH THE ALPHABET.

    WHY THE SORTED ORDER HAD TO GO, stated here because the change looks cosmetic
    and is not.  This function used to return `Topic(sorted(target)[:k])`, the k
    lexicographically SMALLEST tokens, and its own docstring gave the reason as
    DETERMINISM ("taken in SORTED order: deterministic, no sampling").  Gate 2 v2
    then added a lexicographic code as an F_match feature (`core.topic_code`).
    Against a mean-of-token-codes feature the two decisions compose into a
    THEOREM -- the mean of the k smallest codes never exceeds the mean of all of
    them -- so the payload scored below the benign note it was cut from BY
    CONSTRUCTION, and the gate's red cell was measuring `sorted()` rather than any
    property of the attacker.  Review II ruling 1; the pre-registration is
    docs/preregistration/cong-v2.md SS0bis, committed before the re-measurement.

    The attack model never asked for the alphabet.  It asks for a SUBSET, and only
    for a subset: adding tokens OUTSIDE the target inflates the Jaccard
    denominator and DROPS sim, so a larger eps would weaken the attack -- exactly
    backwards from "distinguishability budget".  Since A is a subset of B,
    sim(A, B) = |A| / |B| ~= eps.  Every property the model and the old docstring
    require survives the change: A is a subset, |A| = k, sim = k/m to the same
    value at the same eps, the draw is deterministic across processes, and no
    token from outside the target ever enters.

    The subsets are also NESTED in eps -- the priority order is fixed per target,
    so a larger k keeps every token a smaller k chose.  That is what keeps sim and
    |A| monotone in epsilon (tests/gate1_integrity/test_retrieval.py pins both).

    THE SALT IS A FREE PARAMETER, AND THAT IS A RESULT, NOT A CAVEAT.  The rule
    above is de-biased with respect to the ALPHABET, which is what the artefact
    required; it is not de-biased with respect to WHICH pseudorandom subset, and
    nothing in the attack model prefers one.  Measured over a mechanical 17-salt
    family on the same corpus seed and the same criterion, the certify cells move
    enough to change verdicts in BOTH directions -- Delta=4 runs 0.5244 (19/20
    splits clearing) to 0.6426 (0/20) against 0.5870 (1/20) here, and the gate's
    overall verdict on MatchedAttack at eps*=0 splits 8 green / 9 red across the
    family.  So a cell quoted off this corpus must name the salt the way it names
    the seed, and a pass or a fail decided at a margin of ~0.03 around the 0.56
    ceiling is not presently resolvable by this benchmark.  `SUBSET_SALT` is
    therefore a frozen field of `analysis.gate2_v2.record()`.
    docs/preregistration/cong-v2.md SS3.9.

    Two opposing directions, and that is what makes it a budget:
        small eps -> few tokens -> low sim, may NOT clear theta -> attack fails
        large eps -> surely retrieved, but a wider tag on F_match, so EASIER to
                     spot
    """
    if not target:
        return Topic()
    k = max(1, math.ceil(eps * len(target)))
    # The canonical key is a property of the TARGET, so it is computed once here
    # rather than once per token inside the sort key: `payload_topic` runs once
    # per payload per epsilon over a 2248-topic supply, and re-deriving the same
    # string |B| times is work with no answer attached to it.
    key = canonical_topic_string(target)
    order = sorted(target, key=lambda t: (subset_priority(target, t, key), t))
    return Topic(order[:k])


def payload_topic_like(target, eps):
    """`payload_topic`, returned in the SAME REPRESENTATION the caller passed in.

    Two things depend on the representation and would break under a bare
    `payload_topic`:

    1. `Item.__post_init__` hashes `seed_of(carrier, topic, content, ...)`, and
       seed_of STRINGIFIES its arguments.  A plain `frozenset`'s str() walks its
       internal hash table, whose layout depends on PYTHONHASHSEED -- so a plain
       frozenset here would give the SAME payload a DIFFERENT item_id on two
       runs, and since detector.score seeds on item_id, a different SCORE too.
       That is the hash() ban arriving through frozenset ordering, the exact trap
       `swebench_dataset.Topic.__str__` was written to close.  Returning
       `type(target)(...)` keeps the Topic subclass, and with it the canonical
       "|".join(sorted(...)) form.
    2. On the mock a topic is a one-token `str`.  Its only non-empty subset is
       itself, so the honest answer at EVERY eps is that same string -- returned
       as a `str`, not as `frozenset({'orm'})`, because build.py interpolates the
       topic into the payload's content template and `[frozenset({'orm'})]` is a
       different byte string from `[orm]`.  This is what makes epsilon a genuine
       no-op on the mock (there is nothing for it to act on when |topic| = 1)
       instead of a silent rewrite of every recorded number.
    """
    if isinstance(target, str):
        return target
    tokens = payload_topic(as_topic(target), eps)
    return type(target)(tokens) if isinstance(target, frozenset) else tokens
