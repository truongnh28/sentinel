#!/usr/bin/env python3
"""run_permutation_test.py -- is the benign corpus separable at all?

Spec: docs/AuditGame-SE_Sentinel_Methodology_Full.md Stage 4;
docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md (group C).

WHAT THE GATE ALREADY HAD, AND WHAT WAS MISSING.  Gate 2 certifies the corpus by
comparing a held-out AUC against a 0.56 ceiling, with a Hanley-McNeil interval
around it.  That interval is PARAMETRIC: it assumes a particular model for the
score distributions, which a 5-feature logistic fit on a few dozen held-out rows
does not obviously satisfy.  The manuscript asks for a permutation test beside
it, and there was none -- the word did not appear anywhere in this project's
source.

The permutation null assumes nothing.  It destroys the only thing that could
make the classes separable -- which row carries which label -- and refits the
whole pipeline, splits included.  The statistic permuted is the one the gate
publishes (median AUC over the declared 20 splits), not a convenient scalar.

READ THE RESULT BACKWARDS FROM HABIT.  This gate certifies NON-separability, so
a HIGH p-value is the wanted outcome.  A low p says the corpus IS separable and
the gate has failed, whatever the ceiling says.

    python3 tools/run_permutation_test.py --n 200 > spikes/permutation-test.json
"""
from __future__ import annotations
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tests"))

from analysis import discriminator as D
from gate2_validity import test_benign_corpus as T


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=D.N_PERMUTATIONS)
    ap.add_argument("--events", type=int, default=T.N_SCREEN,
                    help="events per class; the screen size by default, because "
                         "the certify size costs len(seeds) x n fits per Delta")
    a = ap.parse_args()

    pipe = T._matched_pipe()
    out = {}
    for delta in T.DELTAS:
        pos, neg = T._matched_corpus(pipe, delta, 0.0, a.events)
        res = D.permutation_test(pos, neg, n=a.n)
        res["n_poisoned"], res["n_benign"] = len(pos), len(neg)
        # The parametric verdict, beside the assumption-free one, so a reader can
        # see whether the two agree.  They are answering the same question in two
        # ways; disagreement is itself the finding.
        par = D.auc_over_splits(pos, neg, ceiling=T.AUC_CEILING)
        res["parametric"] = {"auc_median": round(par["auc_median"], 4),
                             "ci_hi_mean": round(par["hi_mean"], 4),
                             "ceiling": T.AUC_CEILING,
                             "clears": f"{par['clear']}/{par['k']} splits"}
        out[delta] = res
        print(f"Delta={delta}  observed {res['observed']:.4f}  "
              f"null p50 {res['null_p50']:.4f} p95 {res['null_p95']:.4f}  "
              f"p={res['p_value']}", file=sys.stderr)

    print(json.dumps({
        "per_delta": out,
        "provenance": {
            "events_per_class": a.events,
            "permutations": a.n,
            "split_seeds": len(D.SPLIT_SEEDS),
            "date": datetime.date.today().isoformat(),
            "commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
