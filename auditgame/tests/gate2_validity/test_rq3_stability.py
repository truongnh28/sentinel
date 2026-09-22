"""
GATE 2 -- RQ3 is a statement about an UPDATE RULE, not about statefulness.
Spec: docs/thesis/Danh-sach-diem-can-them.md C5.

"Randomisation is the strongest lever" gave three different answers across three
implementations of the same benchmark:

    draft                             randomisation +0.184, belief +0.099
    an independent run (its grid)     randomisation +0.131, belief -0.025
    this repo, after normalising      randomisation +0.069, belief +0.161

The three are not in conflict about the world. They ran different BELIEF UPDATE
RULES. Before normalisation the rule was `1 + 2*score`, calibrated for a [0,1]
scale, and on the posterior scale it spanned a belief range of 1.86 against a
1/kappa range of 10.2 -- so cost dominated and the belief contributed exactly
0.0000 at every Delta. Change the rule, change the answer.

So the ablation does not measure whether sequential state is worth having. It
measures how well one update rule is calibrated against the cost scale. RQ3 has to
be stated against a FROZEN rule, or swept and reported as a range. This file does
the second, which is strictly more informative and costs one more sweep.
"""
from __future__ import annotations
import random, unittest

import agent, build, detector, runner
import policies as P
from core import seed_of

N_WF, BUDGET, DELTA = 20, 17.95, 4


def _ablation(rule: str):
    """(belief contribution, randomisation contribution) under one update rule."""
    wfs = [build.make_workflow(f"wf-{i:03d}", "django", 8,
                               random.Random(seed_of("rq3", i))) for i in range(N_WF)]
    det, ag = detector.Detector.from_setting("mid"), agent.MockAgent()
    out = {}
    for name in ("Sentinel", "C4 blind sentinel", "C8 deterministic sentinel"):
        runner.reset_survivor_cache()
        cell = runner.worst_case(name, wfs, (DELTA,), list(P.KAPPA), det, ag,
                                 BUDGET, (1, 2), "mid", update_rule=rule)
        out[name] = cell.harm
    return (out["C4 blind sentinel"] - out["Sentinel"],
            out["C8 deterministic sentinel"] - out["Sentinel"])


class RQ3Stability(unittest.TestCase):

    def test_every_declared_update_rule_runs(self):
        """A rule in the registry that cannot run is a rule nobody swept.

        Thesis claim (vi): "quy tac cap nhat phai duoc FREEZE va cong bo".
        """
        self.assertGreaterEqual(len(P.UPDATE_RULES), 3,
                                "too few rules to call this a sweep")
        for name, fn in P.UPDATE_RULES.items():
            with self.subTest(rule=name):
                v = fn(0.25)
                self.assertGreaterEqual(v, 0.0, f"[{name}] negative evidence weight "
                                                f"-- the roulette wheel breaks")

    def test_the_ablation_answer_depends_on_the_update_rule(self):
        """The finding itself, asserted.

        If every rule agreed, RQ3 would be a statement about statefulness and could
        be quoted as one. It is not: the sign of the belief contribution flips
        across rules that are all defensible readings of the same design.

        A later change that makes the rules agree turns this RED, which is correct
        -- it would mean RQ3 became quotable, and the claim would have to be
        rewritten deliberately rather than drifting back.

        Thesis claim (vi): PHAN CHUNG cua "ngau nhien hoa la don bay manh nhat".
        """
        beliefs = {r: _ablation(r)[0] for r in P.UPDATE_RULES}
        spread = max(beliefs.values()) - min(beliefs.values())
        self.assertGreater(
            spread, 0.05,
            f"belief contribution varies by only {spread:.4f} across update rules "
            f"{ {k: round(v, 4) for k, v in beliefs.items()} } -- if the rules agree, "
            f"RQ3 is quotable and this test should be rewritten, not relaxed.")


if __name__ == "__main__":
    unittest.main()
