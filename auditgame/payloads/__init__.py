"""
payloads/__init__.py -- READER for the frozen payload corpus, and the
`FrozenPayloadAttack` pipeline that plays it.

Spec: task-llmpayload-brief.md; SPEC-AuditGame-SE Part 0.

MEASUREMENT CORE, STDLIB ONLY.  This is the runtime half of the frozen-payload
architecture: it reads payloads/frozen_payloads.json and NEVER calls an LLM and
NEVER imports payloads/generate.py (the infra tier that may).  The split is the
same one swebench_fetch.py keeps from the analysis that reads its output.

WHY A DIVERSE FROZEN BANK.  The current single-template attacker (attacks.py
MatchedAttack) writes ONE deprecation sentence, and three of the four F_match
features it produces are constant -- depth, derived and recency -- so the
distinguishability classifier is effectively one-variable (`size`) and
"AUC <= 0.56 => stealthy" really only certifies "the payload matched on length".
This bank varies the sentence, the `provenance` (hence `depth`), and whether a
record carries `derived_from` (hence `derived`), so the F_match measurement
exercises more than one axis.

SELF-SEALING.  A committed record is a FROZEN STRING, under the same no-edit rule
as a `content=` literal, because `item_id = blake2b(content)` seeds the detector.
The file carries `payloads_sha256`, a hash of its own payload records; `load_frozen`
recomputes it and REFUSES a mismatch (pattern: reference/score_table.json's
--check, and the sealed manifest).  The canonical form below is duplicated from
generate.py ON PURPOSE -- the reader must not import the infra tier -- and the
round trip is asserted in tests/gate1_integrity/test_frozen_payloads.py, so the
two cannot drift apart in silence.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
from dataclasses import dataclass

from core import Item, seed_of

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_PATH = HERE / "frozen_payloads.json"

#: The record keys the corpus is built from -- kept in step with generate.py's
#: RECORD_KEYS (asserted by the self-seal round trip test).
RECORD_KEYS = ("name", "content", "provenance", "derived_from")


class FrozenPayloadTampered(RuntimeError):
    """The committed corpus does not match its own self-seal.

    Raised rather than read-on-anyway: once committed, the payload strings seed
    item_id and therefore the detector, so an edited byte is a silently different
    world -- exactly the failure the no-edit rule on `content=` literals exists to
    prevent."""


@dataclass(frozen=True)
class FrozenPayload:
    """One record of the frozen corpus."""
    name: str
    content: str
    provenance: str
    derived_from: tuple = ()


def _canonical_records(records: list) -> str:
    """The byte string the self-seal hashes.  MUST match generate.canonical_records
    exactly (sorted keys, no incidental whitespace, ensure_ascii=False)."""
    norm = [{k: (list(r["derived_from"]) if k == "derived_from" else r[k])
             for k in RECORD_KEYS} for r in records]
    return json.dumps(norm, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _records_sha256(records: list) -> str:
    return hashlib.sha256(_canonical_records(records).encode("utf-8")).hexdigest()


def load_frozen(path=DEFAULT_PATH) -> list:
    """Read the frozen corpus, VERIFY the self-seal, return list[FrozenPayload].

    The seal is checked before anything downstream sees a record: a corpus whose
    hash does not match its `payloads_sha256` is not a corpus this build may
    measure with, because its item_ids would describe items nobody committed.
    """
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    records = doc.get("payloads")
    if not isinstance(records, list) or not records:
        raise FrozenPayloadTampered(f"{path}: no payload records")
    sealed = doc.get("payloads_sha256")
    actual = _records_sha256(records)
    if sealed != actual:
        raise FrozenPayloadTampered(
            f"{path}: payloads_sha256 {sealed!r} does not match the hash of the "
            f"records it seals ({actual!r}). A committed payload is a frozen string "
            f"(item_id is hashed from it); regenerate with payloads/generate.py "
            f"rather than editing the file by hand.")
    out = []
    for r in records:
        out.append(FrozenPayload(name=r["name"], content=r["content"],
                                 provenance=r["provenance"],
                                 derived_from=tuple(r.get("derived_from", ()))))
    return out


# --------------------------------------------------------------------------
# The held-out split -- by hash of the payload NAME, fixed before measurement
# --------------------------------------------------------------------------

def _held_out_share() -> float:
    """attackers.HELD_OUT_SHARE, the one share used everywhere a rule is withheld.
    Imported lazily so this reader has no import-time dependency on the attacker
    library."""
    import attackers
    return attackers.HELD_OUT_SHARE


def held_out(name: str) -> bool:
    """Is this payload in the held-out split?  Hash-based on the NAME, exactly like
    attackers._is_held_out, so the split is fixed by the name and cannot be re-drawn
    after a number is seen.  Deterministic through core.seed_of, never hash()."""
    h = seed_of("heldout", name) & 0xFFFF
    return (h / 0xFFFF) < _held_out_share()


def held_out_names(path=DEFAULT_PATH) -> set:
    return {p.name for p in load_frozen(path) if held_out(p.name)}


def development_names(path=DEFAULT_PATH) -> set:
    return {p.name for p in load_frozen(path) if not held_out(p.name)}


# --------------------------------------------------------------------------
# The pipeline -- same interface as attacks.MatchedAttack
# --------------------------------------------------------------------------

class FrozenPayloadAttack:
    """Plays a payload drawn deterministically from the frozen bank.

    Declares `epsilon_effective=False` HONESTLY: a frozen payload does not depend
    on epsilon (the string is fixed offline), so epsilon has no surface here.  This
    task is about SURFACE DIVERSITY, not the epsilon budget -- wiring a retrieval
    knob is left to the epsilon-as-budget finding (report says so explicitly).
    Declaring False rather than True is what keeps it out of K5's contract without
    lying, exactly as LegacyAttack does.

    The template is selected by core.seed_of over (wf, iota, sigma, carrier), so the
    choice is deterministic across processes (no hash(), no counter) -- K1/K1b -- and
    different events draw different records, which is what makes the corpus vary on
    depth / derived / provenance rather than repeat one template.
    """
    name = "frozen-payload"

    def __init__(self, path=DEFAULT_PATH):
        self._path = path
        self._bank = None            # loaded (and seal-checked) on first use

    def bank(self) -> list:
        if self._bank is None:
            self._bank = load_frozen(self._path)
        return self._bank

    def scope(self):
        # Imported here so `import payloads` does not require attacks at import time.
        from attacks import AttackScope, CARRIERS_ALL
        return AttackScope(carriers=CARRIERS_ALL, delta_range=(0, 6),
                           epsilon_effective=False, requires_graded_retrieval=False)

    def plan(self, wf, carrier, delta, rng: random.Random, epsilon: float = 0.6):
        import build
        return build.plan_poison(wf, carrier, delta, rng, epsilon)

    def _pick(self, wf, ps):
        bank = self.bank()
        i = seed_of("frozen-payload", wf.wf_id, ps.iota, ps.sigma, ps.carrier) % len(bank)
        return bank[i]

    def payload(self, wf, ps) -> Item:
        fp = self._pick(wf, ps)
        # topic is task sigma's, as MatchedAttack does, so the payload is retrieved
        # and age-matched the same way; the content is the FROZEN string, carrying
        # neither the topic nor the task id (its size is a property of the record,
        # spread across the benign length band by construction).
        topic = wf.tasks[ps.sigma].topic
        return Item(carrier=ps.carrier, topic=topic, content=fp.content,
                    created_at=ps.iota, provenance=fp.provenance,
                    poisoned=True, derived_from=fp.derived_from)
