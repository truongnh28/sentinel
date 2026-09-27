"""v3/state.py -- the carrier part of the draft's state s_t = (c_t, iota, sigma) (T3).

Draft S4: "c_t in {0,1}^K records which of K carriers (memory records, cached skills,
tool queue entries, branch derivations) are poisoned", K = 4.  v3 reads c_t off the
store instead of tracking it by hand:

    c_t[k] = 1  iff  some LIVE item of carrier k is poisoned

in core.CARRIERS order (memory, skill, queue, branch).  Several bits can be 1 at once:
the poison propagates note -> skill -> patch -> branch, each hop a new item whose
`derived_from` names the item(s) it came from (core.Item).  That trail is what
`lineage` and `CarrierState.edges` read; the copies outlive their sources, so removing
the note leaves the skill (and its bit) in place -- Fig. 1's "The poison is now in two
carriers".

Removing a carrier (lines 8-9, the draft's "removes a carrier") is the runner's loop of
store.quarantine over store.live(k) (plan S3, T6).  Here it only has its consequence:
once no live item of k is poisoned, c_t[k] = 0.

GROUND TRUTH.  `Item.poisoned` is evaluator-only, so c_t is evaluator-only too: it feeds
the record (EpisodeRecord.c_traj), the oracle and rollouts' HiddenState, never a policy.

Stdlib only; imports v2, never patches it.
"""
from __future__ import annotations

from dataclasses import dataclass

from core import CARRIERS, CarrierStore, Item


def c_of(store: CarrierStore) -> tuple:
    """c_t in {0,1}^4, core.CARRIERS order: 1 iff a live item of the carrier is poisoned."""
    return tuple(int(any(it.poisoned for it in store.live(k))) for k in CARRIERS)


def bits(c) -> str:
    """(1, 1, 0, 1) -> "1101", the form EpisodeRecord.c_traj carries."""
    if len(c) != len(CARRIERS) or any(b not in (0, 1) for b in c):
        raise ValueError(f"c={c!r} is not a {len(CARRIERS)}-bit vector")
    return "".join(str(int(b)) for b in c)


def from_bits(s: str) -> tuple:
    """"1101" -> (1, 1, 0, 1)."""
    if len(s) != len(CARRIERS) or set(s) - {"0", "1"}:
        raise ValueError(f"{s!r} is not a {len(CARRIERS)}-bit string")
    return tuple(int(ch) for ch in s)


def _index(store: CarrierStore) -> dict:
    """item_id -> Item over EVERY item ever written, quarantined ones included: the
    trail of a live copy may run through a removed source."""
    return {it.item_id: it for k in CARRIERS for it in store.items[k]}


def lineage(store: CarrierStore, item: Item) -> tuple:
    """The carriers the poison crossed to reach `item`, root first, e.g.
    ("memory", "skill", "branch") for note -> skill -> patch.  Follows the first
    poisoned parent in derived_from at each hop; a root is its own lineage."""
    idx = _index(store)
    path, cur, seen = [item.carrier], item, {item.item_id}
    while cur.derived_from:
        parents = [idx[p] for p in cur.derived_from if p in idx and idx[p].poisoned]
        if not parents or parents[0].item_id in seen:
            break
        cur = parents[0]
        seen.add(cur.item_id)
        path.append(cur.carrier)
    return tuple(reversed(path))


def trail_problems(store: CarrierStore) -> list:
    """Poisoned items whose derived_from trail does not hold: a parent id that is not in
    the store, or a parent that is not poisoned.  Empty when the propagation trail is
    consistent (every derived poisoned item came from poison)."""
    idx = _index(store)
    out = []
    for k in CARRIERS:
        for it in store.items[k]:
            if not it.poisoned:
                continue
            for p in it.derived_from:
                if p not in idx:
                    out.append(f"{it.item_id} ({k}): parent {p} is not in the store")
                elif not idx[p].poisoned:
                    out.append(f"{it.item_id} ({k}): parent {p} ({idx[p].carrier}) is clean")
    return out


@dataclass(frozen=True)
class CarrierState:
    """c_t with the trail that produced it.

    c        {0,1}^4 in core.CARRIERS order.
    seeded   carriers holding a live poison ROOT (no derived_from: the attacker's write).
    edges    (parent carrier, child carrier) of every live derived poisoned item, sorted:
             the hops the poison has made, e.g. (("memory", "skill"), ("skill", "branch")).
    """
    c: tuple
    seeded: tuple = ()
    edges: tuple = ()

    @classmethod
    def of(cls, store: CarrierStore) -> "CarrierState":
        idx = _index(store)
        seeded, edges = set(), set()
        for it in store.live():
            if not it.poisoned:
                continue
            if not it.derived_from:
                seeded.add(it.carrier)
            for p in it.derived_from:
                if p in idx and idx[p].poisoned:
                    edges.add((idx[p].carrier, it.carrier))
        order = {k: i for i, k in enumerate(CARRIERS)}
        return cls(c=c_of(store),
                   seeded=tuple(k for k in CARRIERS if k in seeded),
                   edges=tuple(sorted(edges, key=lambda e: (order[e[0]], order[e[1]]))))

    @property
    def bits(self) -> str:
        return bits(self.c)

    @property
    def poisoned(self) -> bool:
        """Some carrier holds poison now (Pr[poisoned] of Algorithm 1 line 8, as truth)."""
        return any(self.c)

    def carriers(self) -> tuple:
        """The poisoned carriers, core.CARRIERS order."""
        return tuple(k for k, b in zip(CARRIERS, self.c) if b)

    def __getitem__(self, k: str) -> int:
        return self.c[CARRIERS.index(k)]
