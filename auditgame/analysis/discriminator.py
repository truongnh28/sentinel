"""
discriminator.py -- Is a poisoning event distinguishable from a benign change?

Spec: eval/SPEC-AuditGame-SE.md Part 0; QUYET-DINH.md question 1.

STDLIB ONLY, deliberately.  The plan once placed this in an "analysis tier" that
may use sklearn, but gate 2 imports it, and gate tests are part of the measurement
core that has to stay clone-and-run (ABC T.6).  Logistic regression on four
features is forty lines; a dependency that splits the code into two
implementations would cost more than it saves.

F_MATCH is EXACTLY what core.Item.surface() exposes.  That is not a coincidence to
be maintained by hand -- gate 2 asserts the two agree, so adding a surface feature
without adding it here goes red.

F_DETECT is listed for documentation only.  It is NOT a feature list the code ever
computes: the detector is parameterised by (psi, phi) => (d', tau_det), and keeping
it that way is what makes the operating point a SWEPT PARAMETER rather than an
emergent property.  Implementing it would reintroduce detection quality as the
confound that the one-shared-detector rule exists to remove, and would kill RQ4.

The pairing below is the part that is easy to get wrong.  `derived` and
`lineage_consistency` look like the same thing and are not: one COUNTS parents,
the other asks whether those parents justify the child.  Written down here because
a disjointness check at the level of NAMES passes while the substance overlaps.

    F_MATCH  (surface counts, cheap)   |  F_DETECT  (semantic, expensive)
    size      content length           |  is the content semantically anomalous
    depth     provenance path segments |  is that provenance actually legitimate
    recency   age in tasks             |  --
    derived   NUMBER of parents        |  is the lineage CONSISTENT
"""
from __future__ import annotations
import math
import random

F_MATCH = frozenset({"size", "depth", "recency", "derived"})
F_DETECT = frozenset({"semantic_anomaly", "provenance_legitimacy", "lineage_consistency"})

_COLS = tuple(sorted(F_MATCH))          # fixed order, so weights stay comparable


def _standardise(rows: list) -> list:
    cols = list(zip(*rows))
    mu = [sum(c) / len(c) for c in cols]
    sd = [(sum((v - m) ** 2 for v in c) / len(c)) ** 0.5 or 1.0 for c, m in zip(cols, mu)]
    return [[(v - m) / s for v, m, s in zip(r, mu, sd)] for r in rows]


def _fit(X: list, y: list, steps: int = 600, lr: float = 0.3) -> tuple:
    """Batch gradient descent.  600 steps, not 3000: measured on the 4500-row corpus,
    the held-out AUC is IDENTICAL to four decimals at 300, 600, 1200 and 3000 steps,
    because AUC depends only on the RANKING and that stabilises long before the
    weights do.  600 keeps a safety margin at a quarter of the cost."""
    w, b = [0.0] * len(_COLS), 0.0
    for _ in range(steps):
        gw, gb = [0.0] * len(_COLS), 0.0
        for xi, yi in zip(X, y):
            z = sum(wj * v for wj, v in zip(w, xi)) + b
            e = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z)))) - yi
            for j in range(len(_COLS)):
                gw[j] += e * xi[j]
            gb += e
        n = len(X)
        w = [wj - lr * g / n for wj, g in zip(w, gw)]
        b -= lr * gb / n
    return w, b


def _auc(scores: list, labels: list) -> float:
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return float("nan")
    return sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))


def _hanley_mcneil(auc: float, n_pos: int, n_neg: int) -> tuple:
    """95% CI for an AUC.  Closed form, no bootstrap needed at this size.

    The CRITERION is applied to the upper bound, which is STRICTER than testing the
    point estimate -- not cheaper.  Reason: at n=310 the standard error is 0.023, so
    a measured 0.56 covers a true 0.60.  A bare point estimate does not survive the
    first question a reviewer asks.
    """
    q1 = auc / (2.0 - auc)
    q2 = 2.0 * auc * auc / (1.0 + auc)
    var = (auc * (1 - auc) + (n_pos - 1) * (q1 - auc * auc)
           + (n_neg - 1) * (q2 - auc * auc)) / (n_pos * n_neg)
    se = math.sqrt(max(var, 0.0))
    return max(0.0, auc - 1.96 * se), min(1.0, auc + 1.96 * se)


def auc_with_ci(poisoned: list, benign: list, seed: int,
                test_fraction: float = 0.4) -> tuple:
    """HELD-OUT AUC of a logistic regression on F_MATCH, plus its 95% CI.

    `poisoned` and `benign` are lists of the dicts Item.surface() returns.

    HELD-OUT is not optional: fitting four features to a few dozen samples gives a
    training AUC near 1.0 whatever the corpus looks like, so a training number
    would certify any corpus at all.
    """
    rows = [[float(f[c]) for c in _COLS] for f in poisoned + benign]
    y = [1.0] * len(poisoned) + [0.0] * len(benign)
    X = _standardise(rows)
    idx = list(range(len(X)))
    random.Random(seed).shuffle(idx)
    cut = int(len(idx) * (1.0 - test_fraction))
    tr, te = idx[:cut], idx[cut:]
    w, b = _fit([X[i] for i in tr], [y[i] for i in tr])
    sc = [sum(wj * v for wj, v in zip(w, X[i])) + b for i in te]
    lab = [y[i] for i in te]
    a = _auc(sc, lab)
    n_pos = int(sum(lab))
    lo, hi = _hanley_mcneil(a, n_pos, len(lab) - n_pos)
    return a, lo, hi
