"""
discriminator.py -- Is a poisoning event distinguishable from a benign change?

Spec: docs/thesis/eval/SPEC-AuditGame-SE.md Part 0; docs/thesis/QUYET-DINH.md question 1.

STDLIB ONLY, deliberately.  The plan once placed this in an "analysis tier" that
may use sklearn, but gate 2 imports it, and gate tests are part of the measurement
core that has to stay clone-and-run (ABC T.6).  Logistic regression on five
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
    topic     WHICH tokens the tag has |  is the tag JUSTIFIED by the task

`topic` IS THE v2 ADDITION, and it is the only column that is not a count.  It is
`core.topic_code` -- the mean lexicographic code of the topic's tokens -- and the
pairing rule above applies to it exactly as it does to `derived`: this column says
which tokens are there, it does NOT say whether carrying them is legitimate, and
it cannot say whether the tag is a strict subset of the surrounding workflow's
task topics (a surface feature sees one item).  See `core.topic_code` for the
choice and for the three limits of it.
"""
from __future__ import annotations
import math
import random
import statistics

F_MATCH = frozenset({"size", "depth", "recency", "derived", "topic"})
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


#: The DECLARED SET of train/test splits every published AUC is summarised over.
#:
#: WHY A SET AND NOT A CONSTANT.  `auc_with_ci` shuffles once, under `seed`, and
#: everything downstream -- the point estimate, the Hanley-McNeil interval, the
#: verdict -- is conditional on that one shuffle.  Pinning it to a single literal
#: makes the published criterion read "AUC_upper <= 0.56 AT SPLIT SEED 7", and the
#: split's own noise is LARGER than the margin that criterion was clearing by.
#: MEASURED on the certify corpus (pool=full, eps*=0, per_event=4), 20 splits:
#:
#:     Delta   CI upper at seed 7   CI upper across SPLIT_SEEDS
#:       0           0.5532            0.4978 .. 0.5791
#:       2           0.5413            0.4888 .. 0.5684
#:       4           0.5383            0.4994 .. 0.5655
#:
#: The bound swings +/- 0.04 on nothing but the shuffle, while Delta=0 was
#: published as clearing the 0.56 ceiling by 0.0068.  Advisor question 8 adopted
#: the CI upper bound PRECISELY because "the threshold sits inside sampling
#: noise"; leaving a second, larger noise source pinned to a literal and then
#: quoting four decimals defeats the reason the criterion was chosen.
#:
#: TWENTY, and they are 1..20 rather than a hand-picked list: a set somebody chose
#: is a seed 7 with more steps.  The number is declared here so that adding or
#: removing a seed is a visible edit to the criterion rather than a quiet one.
SPLIT_SEEDS = tuple(range(1, 21))


def summarise_splits(per_seed: dict, ceiling: float) -> dict:
    """Collapse {seed -> (auc, lo, hi)} into the summary a verdict is read off.

    WHICH SUMMARY IS THE CRITERION, and why it is the MEAN of the upper bounds
    rather than their MAXIMUM.  Both are properties of the declared set, so both
    answer the "arbitrary constant" objection; they do not answer the same
    question.

      max(hi)   asks "is there a split at which the interval fails to close".
                Its expectation GROWS WITH len(SPLIT_SEEDS) -- it converges to the
                supremum, not to a population quantity -- so the criterion would
                change every time somebody adds a seed.  It is also dominated by
                the fold SIZE rather than by the payload: measured on the screen
                corpus (80 events), max(auc) at epsilon = 0 reaches 0.6220 at
                Delta = 2, and at epsilon = 0 the payload is byte-length matched
                to the agent's note BY CONSTRUCTION.  A statistic that reports an
                indistinguishable payload as separable because the fold is small
                is measuring the fold -- the same confound class age-matching
                exists to remove.

      mean(hi)  asks "where does the interval sit once the shuffle is averaged
                out".  Stable in len(SPLIT_SEEDS), and it keeps every bit of the
                sample-size honesty question 8 bought, because each hi still
                carries the Hanley-McNeil width of a SINGLE test fold: a corpus
                too small to close the interval still fails.  Measured, it does
                fail exactly where it should -- pool=verified, eps*=0:
                Delta=2 mean(hi) 0.5629 (7/20 splits clear), Delta=4 0.5898
                (5/20) -- which is the power argument the pool decision rests on,
                restated without seed 7's 0.0038.

    `clear` (how many splits clear the ceiling on their own) is returned BESIDE the
    criterion, never instead of it: a reader who prefers the max rule can apply it
    from these fields, and a cell that clears on the mean while failing at 3 of 20
    splits has to say so out loud.  Nothing here moves the 0.56 ceiling.
    """
    aucs = [v[0] for v in per_seed.values()]
    his = [v[2] for v in per_seed.values()]
    return dict(
        k=len(per_seed),
        auc_mean=statistics.fmean(aucs), auc_median=statistics.median(aucs),
        auc_min=min(aucs), auc_max=max(aucs),
        hi_mean=statistics.fmean(his), hi_min=min(his), hi_max=max(his),
        clear=sum(1 for h in his if h <= ceiling),
        failing_seeds=sorted(s for s, v in per_seed.items() if v[2] > ceiling),
    )


def auc_over_splits(poisoned: list, benign: list, ceiling: float,
                    seeds=SPLIT_SEEDS, test_fraction: float = 0.4) -> dict:
    """`auc_with_ci` over EVERY declared split, summarised -- see SPLIT_SEEDS.

    The corpus is built once by the caller and handed in, so the cost of the whole
    declared set is len(seeds) logistic fits and no extra harvesting.  MEASURED:
    the certify phase over 20 splits and three Deltas costs 49s against 2.5s at one
    split -- which is what "20 is cheap" means here.
    """
    per_seed = {s: auc_with_ci(poisoned, benign, seed=s,
                               test_fraction=test_fraction) for s in seeds}
    out = summarise_splits(per_seed, ceiling)
    out["per_seed"] = {s: tuple(round(x, 4) for x in v) for s, v in per_seed.items()}
    return out


def auc_with_ci(poisoned: list, benign: list, seed: int,
                test_fraction: float = 0.4) -> tuple:
    """HELD-OUT AUC of a logistic regression on F_MATCH, plus its 95% CI.

    `poisoned` and `benign` are lists of the dicts Item.surface() returns.

    HELD-OUT is not optional: fitting five features to a few dozen samples gives a
    training AUC near 1.0 whatever the corpus looks like, so a training number
    would certify any corpus at all.

    `seed` draws ONE shuffle, so everything this returns is conditional on it.  No
    published verdict may be read off a single call: the criterion is a property of
    the DECLARED SPLIT SET (see SPLIT_SEEDS and `auc_over_splits`), because the
    spread of `hi` across splits is wider than the margin the 0.56 ceiling is
    cleared by.  This function stays single-split on purpose -- it is the unit
    `auc_over_splits` is built from, and a test perturbing one split needs it.
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
