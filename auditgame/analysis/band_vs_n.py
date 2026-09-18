"""band_vs_n.py -- how much corpus does a surface-matching gate need?

The certify cells sit at 0.51-0.64 with the 0.56 ceiling INSIDE the construction's
own noise band, so a cell published within ~0.03 of the ceiling carries no
information about the attacker, green or red.  That is a property of n, not of this
benchmark, and this module measures the relationship.

The unit of replication is the SALT, not the split: splits overlap on a small
corpus, so 20/20 splits on one salt is not twenty independent confirmations.
"""
from __future__ import annotations
import statistics

import attacks
import retrieval
from analysis import benign_corpus, discriminator

MIN_SALTS = 3


class Unresolved(Exception):
    """No corpus size tried resolves the ceiling.  Carries the largest n tried."""


def _certify_statistic(n: int, salt: str, delta: int = 0, eps: float = 0.0) -> float:
    """Certify phase statistic (mean CI95 upper bound over splits) under a given salt."""
    orig = retrieval.SUBSET_SALT
    try:
        retrieval.SUBSET_SALT = salt
        pipe = attacks.REGISTRY["matched"]
        pos, neg = benign_corpus.matched_corpus(pipe, delta, eps, n)
        r = discriminator.auc_over_splits(pos, neg, ceiling=0.56, seeds=discriminator.SPLIT_SEEDS)
        return r["hi_mean"]
    finally:
        retrieval.SUBSET_SALT = orig


def band_width(n: int, salts, delta: int = 0, eps: float = 0.0) -> dict:
    """Spread of the certify statistic across the salt family at corpus size n."""
    if len(salts) < MIN_SALTS:
        raise ValueError(
            f"a band needs at least {MIN_SALTS} salts; {len(salts)} has no spread, "
            f"and a zero-width band read as resolution is exactly the claim this "
            f"module exists to refuse")
    vals = [_certify_statistic(n, s, delta=delta, eps=eps) for s in salts]
    return {"n": n, "lo": min(vals), "hi": max(vals),
            "width": max(vals) - min(vals), "median": statistics.median(vals),
            "salts": len(salts), "values": vals}


def band_curve(n_grid, salts, delta: int = 0, eps: float = 0.0) -> list:
    """(n, width) for each n.  The figure frame B is built on."""
    return [(n, band_width(n, salts, delta=delta, eps=eps)["width"]) for n in n_grid]


def resolving_n(n_grid, salts, ceiling: float = 0.56, margin: float = 0.0,
                delta: int = 0, eps: float = 0.0) -> int | None:
    """Smallest n whose band does NOT straddle the ceiling.  None if no n does.

    None is a RESULT, not a failure: it says a gate of this shape cannot resolve
    this ceiling at any corpus size this project can build, and that is the central
    finding rather than a reason to move the ceiling.
    """
    tried = sorted(n_grid)
    for n in tried:
        b = band_width(n, salts, delta=delta, eps=eps)
        if not (b["lo"] - margin <= ceiling <= b["hi"] + margin):
            return n
    widest = band_width(tried[-1], salts, delta=delta, eps=eps)
    raise Unresolved(
        f"no n up to {tried[-1]} resolves the {ceiling} ceiling; at n = {tried[-1]} "
        f"the band is [{widest['lo']:.4f}; {widest['hi']:.4f}] over {widest['salts']} "
        f"salts. This is a result about the corpus sizes TRIED, not about all n.")
