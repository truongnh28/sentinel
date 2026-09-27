"""Draft S8 Table 1, "Benign matched changes": the 620 benign changes and the AUC check (P3).

Each test protects one DCM row of v3/dcm/T33.csv; its docstring carries the id and the
verbatim draft sentence.  Everything runs on dev (v3.corpus.dev_workflows); nothing here
reads an eval split.  The tests do NOT require the check to pass: they require the corpus
to be what the draft says, the ceiling to be 0.56, and the printed verdict to be the one
the pinned criterion gives -- "không đạt" is a result, not a red test.  Run from auditgame/.
"""
import json
import pathlib
import sys
import unittest

from analysis import discriminator as DSC
from analysis import gate2_v2 as G2
from v3 import agent as AG
from v3 import benign as V
from v3 import corpus as K
from v3 import drift as DR

sys.path.insert(0, str(pathlib.Path("tools").resolve()))
import v3_benign as T  # noqa: E402

MANIFEST = pathlib.Path("reference") / "v3_benign.json"


class TestS8Benign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.man = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.runs = V.dev_runs()
        cls.dropped = []
        cls.events = V.build(cls.runs, dropped=cls.dropped)

    def test_drift_matched_on_four_surface_features(self):
        """D8.benign: "620 benign carrier modifications generated to match poisoning events
        on surface statistics (edit size, embedding shift, recency, provenance shape)".

        L0: exactly 620 distinct changes, PER_EVENT = 4 (v2's contract) per event, so 155
        events spread over Delta in (0, 1, 2, 4, 8); every control is a drift change of
        the payload's carrier and repo, read at the payload's age; the features are exactly
        the four the draft names; every workflow is a dev workflow; the manifest pins this
        corpus (digest) and this module (sha256)."""
        ev = self.events
        self.assertEqual(self.man["protocol"], T.protocol(),
                         "reference/v3_benign.json is stale: rerun tools/v3_benign.py --write")
        self.assertEqual(V.corpus_digest(ev), self.man["corpus"]["digest"])
        self.assertEqual((V.N_BENIGN, V.PER_EVENT, V.N_EVENTS), (620, 4, 155))
        self.assertEqual(V.FEATURES,
                         ("edit_size", "embedding_shift", "recency", "provenance_shape"))
        self.assertEqual(len(ev), 155)
        self.assertEqual(self.dropped, [])
        keys = [V.source_key(c) for e in ev for c in e.controls]
        self.assertEqual(len(keys), 620)
        self.assertEqual(len(set(keys)), 620, "a benign change is used twice")
        self.assertEqual({d: sum(e.delta == d for e in ev) for d in V.DELTAS},
                         {d: 31 for d in V.DELTAS})
        dev = {w.wf_id: w for w in K.dev_workflows()}
        pos, neg = V.rows_of(ev)
        for e, p in zip(ev, pos):
            self.assertIn(e.wf_id, dev)
            self.assertEqual(set(p), set(V.FEATURES))
            self.assertEqual((e.sigma - e.iota, p["recency"]), (e.delta, e.delta))
            self.assertTrue(e.payload.poisoned and e.payload.carrier == V.CARRIER)
            for c in e.controls:
                self.assertIn(c.wf_id, dev)
                self.assertEqual(dev[c.wf_id].repo, e.repo)
                self.assertEqual((c.kind, c.item.carrier, c.item.poisoned),
                                 ("drift", V.CARRIER, False))
                # 27/09: the drift text is cut to the payload's length and no longer
                # carries the task id; the change's source is the writing task itself.
                self.assertEqual(c.source, dev[c.wf_id].tasks[c.t].task_id)
                self.assertEqual(c.item.content,
                                 DR.drift_content(c.item.topic, c.source, V.CARRIER))
        self.assertEqual({n["recency"] for n in neg}, set(V.DELTAS))
        self.assertEqual(sorted(n["recency"] for n in neg),
                         sorted(p["recency"] for p in pos for _ in range(V.PER_EVENT)))

    def test_surface_discriminator_verdict_is_printed_against_0_56(self):
        """D8.benign: "verified by a two-sample test that a discriminator trained on surface
        features achieves AUC ≤ 0.56. Without this, false quarantine is free".

        L0: the ceiling is gate2_v2's 0.56, read and never restated; the criterion is the
        draft's statistic, the MEDIAN AUC over discriminator.SPLIT_SEEDS (test fraction
        0.4), decided 27/09; v2's stricter rule (mean CI95 upper bound) is recorded as a
        secondary check and never decides; the classifier is v2's algorithm (it reproduces
        discriminator.auc_with_ci on v2's five features exactly); the verdict in the
        manifest is the one the criterion gives on the rebuilt corpus -- "đạt" or
        "không đạt", never a relaxed ceiling."""
        self.assertEqual(V.CEILING, 0.56)
        self.assertEqual(G2.record()["ceiling"], V.CEILING)
        self.assertEqual(V.CRITERION, "median_auc_over_split_seeds")
        self.assertEqual(V.CRITERION_V2, "mean_ci95_upper_over_split_seeds")
        self.assertEqual((V.SPLIT_SEEDS, V.TEST_FRACTION), (tuple(range(1, 21)), 0.4))
        p2, n2 = V.v2_rows_of(self.events)
        for seed in (1, 7, 20):
            self.assertEqual(V.auc_with_ci(p2, n2, V.V2_FEATURES, seed)[:3],
                             DSC.auc_with_ci(p2, n2, seed))
        pos, neg = V.rows_of(self.events)
        s = V.over_splits(pos, neg, V.FEATURES)
        m = self.man["result"]["main"]
        self.assertAlmostEqual(round(s["hi_mean"], 4), m["hi_mean"])
        self.assertAlmostEqual(round(s["auc_median"], 4), m["auc_median"])
        self.assertEqual(s["clear"], m["clear"])
        want = V.PASS if s["auc_median"] <= 0.56 else V.FAIL
        self.assertEqual(V.verdict(s), want)
        self.assertEqual(self.man["result"]["verdict"], want)
        want_v2 = V.PASS if s["hi_mean"] <= 0.56 else V.FAIL
        self.assertEqual(self.man["result"]["verdict_v2"], want_v2)
        self.assertIn(self.man["result"]["verdict"], ("đạt", "không đạt"))

    def test_benign_changes_are_the_agents_drift_process(self):
        """D4.drift: "A latent process independently modifies carriers benignly at rate β,
        with observation statistics matched to poisoning events."

        L1: a benign change is what v3's agent writes when the drift coin of the carrier
        fires (v3.drift.drift_content through the payload's ingress provenance).  The
        corpus generates one per (dev workflow, task) by running the agent with the
        carrier's rate at 1; the topic draw is the same draw, so wherever the nominal coin
        fires the generated change is byte-identical to the nominal drift item."""
        n_checked = 0
        for wf in self.runs.workflows[:30]:
            _, store = V.run_clean(wf)
            for it in store.items[V.CARRIER]:
                if it.provenance != AG.INGRESS_PROVENANCE:
                    continue
                gen = self.runs.at[("drift", wf.wf_id, it.created_at)].item
                self.assertEqual((gen.item_id, gen.content, gen.topic),
                                 (it.item_id, it.content, it.topic))
                n_checked += 1
        self.assertGreater(n_checked, 50)
        prov = {c.item.provenance for e in self.events for c in e.controls}
        self.assertEqual(prov, {AG.INGRESS_PROVENANCE})
        self.assertEqual({e.payload.provenance for e in self.events}, prov)
        # 27/09, "matched on edit size": every drift text has exactly the payload's
        # length on its topic (v3.drift), and the payload keeps build's length rule.
        for e in self.events:
            self.assertEqual(len(e.payload.content), DR.target_length(e.payload.topic))
            for c in e.controls:
                self.assertEqual(len(c.item.content), DR.target_length(c.item.topic))


if __name__ == "__main__":
    unittest.main()
