#!/usr/bin/env python3
"""certify_gate2.py -- the benign-corpus gate, run once, as a table.

Spec: docs/preregistration/cong-v2.md, cong-v2-chot.md.

WHAT THE GATE IS FOR.  Before any harm number may be quoted, the injected
corpus has to be indistinguishable from a benign one on SURFACE features alone.
If a logistic regression on five surface features can separate them, then a
defender could find the payload without any of the machinery this paper is
about, and the harm table would be measuring a detectable payload rather than
audit allocation.

THE CRITERION, AS PRE-REGISTERED, IS TWO PHASES WITH DIFFERENT STATISTICS --
and mixing them is the mistake this script was written wrong once to make
(cong-v2-chot.md sections 1-2):

  Screen    N = 80 events,  MEDIAN POINT ESTIMATE over 20 splits
  Certify   N = 900 events, MEAN CI UPPER BOUND over 20 splits

Running the certify statistic at the screen's sample size refuses everything:
at N = 80 the Hanley-McNeil interval is wide enough that hi_mean lands at
0.61..0.70 whatever the corpus looks like, so the verdict would be an artefact
of sample size rather than a property of the payload.  Both phases are run here
and reported separately, and the certification verdict is read off the certify
phase alone.

In both phases the verdict is a property of the DECLARED SPLIT SET (20 seeds),
never of one split -- the spread of `hi` across splits is wider than the margin
the ceiling is cleared by.

WHY THIS SCRIPT EXISTS SEPARATELY FROM THE TEST.  The gate2 tests assert the
criterion; the sprint plan also owes a CERTIFICATION TABLE -- one run, one
artifact, a verdict per Delta that can be cited.  It also reconciles two numbers
that had drifted apart (README issue 11): the pre-registration records 0.519 and
0.529, while the test output prints 0.5117 and 0.5247.  If those are the same
statistic they must match; if they are different statistics the table has to say
which one the verdict is read off.

    python3 tools/certify_gate2.py > spikes/gate2-certification.json
"""
from __future__ import annotations
import argparse, datetime, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import analysis.benign_corpus as B
import analysis.discriminator as D
import analysis.gate2_v2 as G
import attacks

CEILING = 0.56

#: The pre-registered numbers this run has to reproduce or explain
#: (docs/preregistration/cong-v2-chot.md, README issue 11).
PREREGISTERED = {0: 0.519, 2: 0.529, 4: 0.587}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--deltas", type=int, nargs="+", default=[0, 2, 4])
    ap.add_argument("--screen-events", type=int, default=80)
    ap.add_argument("--certify-events", type=int, default=900)
    ap.add_argument("--pipeline", default="matched")
    ap.add_argument("--epsilon", type=float, default=0.0,
                    help="0.0 is the declared payload; the gate certifies THAT, "
                         "not a perturbed one")
    a = ap.parse_args()

    pipe = attacks.REGISTRY[a.pipeline]
    rows = []
    for d in a.deltas:
        scr_pos, scr_neg = B.matched_corpus(pipe, d, a.epsilon, a.screen_events)
        scr = D.auc_over_splits(scr_pos, scr_neg, ceiling=CEILING,
                                seeds=D.SPLIT_SEEDS)
        cer_pos, cer_neg = B.matched_corpus(pipe, d, a.epsilon, a.certify_events)
        cer = D.auc_over_splits(cer_pos, cer_neg, ceiling=CEILING,
                                seeds=D.SPLIT_SEEDS)
        # EACH PHASE IS READ OFF ITS OWN DECLARED STATISTIC.
        verdict = "certify" if cer["hi_mean"] <= CEILING else "refuse"
        pre = PREREGISTERED.get(d)
        rows.append({
            "delta": d,
            "screen": {"n_events": a.screen_events,
                       "n_pos": len(scr_pos), "n_neg": len(scr_neg),
                       "statistic": "auc_median",
                       "value": round(scr["auc_median"], 4),
                       "auc_mean": round(scr["auc_mean"], 4),
                       "hi_mean": round(scr["hi_mean"], 4),
                       "passes": scr["auc_median"] <= CEILING},
            "certify": {"n_events": a.certify_events,
                        "n_pos": len(cer_pos), "n_neg": len(cer_neg),
                        "statistic": "hi_mean",
                        "value": round(cer["hi_mean"], 4),
                        "auc_median": round(cer["auc_median"], 4),
                        "hi_max": round(cer["hi_max"], 4),
                        "splits_clearing": cer["clear"],
                        "failing_seeds": cer["failing_seeds"]},
            "ceiling": CEILING,
            "verdict": verdict,
            "preregistered": pre,
            "delta_vs_preregistered": (round(cer["hi_mean"] - pre, 4)
                                       if pre is not None else None),
        })
        print(f"D={d}  screen(median,N={a.screen_events}) {scr['auc_median']:.4f}"
              f"   certify(hi_mean,N={a.certify_events}) {cer['hi_mean']:.4f}"
              f"  clears {cer['clear']}/{cer['k']}  -> {verdict.upper()}"
              f"   (prereg {pre})", file=sys.stderr)

    certified = [r["delta"] for r in rows if r["verdict"] == "certify"]
    refused = [r["delta"] for r in rows if r["verdict"] == "refuse"]
    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "gate_digest": G.md5(),
        "setup": {"pipeline": a.pipeline, "epsilon": a.epsilon,
                  "screen_events": a.screen_events,
                  "certify_events": a.certify_events, "ceiling": CEILING,
                  "split_seeds": list(D.SPLIT_SEEDS),
                  "verdict_statistic": "hi_mean at the certify sample size",
                  "verdict_rule": "certify iff hi_mean <= ceiling over the "
                                  "declared split set, at N = certify_events; "
                                  "the screen phase uses auc_median at N = "
                                  "screen_events and does not decide"},
        "rows": rows,
        "certified_deltas": certified,
        "refused_deltas": refused,
        "consequence": ("Harm numbers may be quoted for Delta in "
                        f"{certified}; cells at {refused} carry a payload a "
                        "surface classifier can find, so a reduction measured "
                        "there is partly a statement about payload visibility "
                        "rather than about audit allocation."),
    }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
