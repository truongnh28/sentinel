"""Draft S8 Table 1, "Benign matched changes": the benign changes and the AUC check (P3, T24).

Each test protects one DCM row of v3/dcm/T24.csv; its docstring carries the id and the
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
from core import CarrierStore

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

        L0+L1: V3_PER_EVENT = 1 control per event (D-v3-2; v2's PER_EVENT = 4 is recorded),
        a quota of min over Delta of candidates // 1 = 160 events per Delta (Delta = 8
        binds), so at most 800 events and as many distinct changes over Delta in (0, 1, 2,
        4, 8), not the draft's 620 (docs/preregistration/lech-chuan-P3-benign.md); a Delta
        short of its quota records the shortfall (N3); every control is a drift change of
        the payload's carrier and repo, read at the payload's age; the features are exactly
        the four the draft names; every workflow is a dev workflow; the manifest pins this
        corpus (digest) and this module (sha256)."""
        ev = self.events
        self.assertEqual(self.man["protocol"], T.protocol(),
                         "reference/v3_benign.json is stale: rerun tools/v3_benign.py --write")
        self.assertEqual(V.corpus_digest(ev), self.man["corpus"]["digest"])
        self.assertEqual((V.N_BENIGN_DRAFT, V.PER_EVENT, V.V3_PER_EVENT), (620, 4, 1))
        self.assertEqual(V.events_per_delta(self.runs), 160)
        self.assertEqual(V.FEATURES,
                         ("edit_size", "embedding_shift", "recency", "provenance_shape"))
        # N3: a Delta that cannot reach its quota of 160 says so; nothing is topped up.
        per_delta = {d: sum(e.delta == d for e in ev) for d in V.DELTAS}
        self.assertEqual({str(d): n for d, n in per_delta.items()},
                         self.man["corpus"]["per_delta"])
        short = {d for d, n in per_delta.items() if n < 160}
        self.assertEqual(short, {d for (w, d, i, why) in self.dropped
                                 if w is None and why.startswith("supply:")})
        self.assertTrue(all(n <= 160 for n in per_delta.values()))
        self.assertGreaterEqual(len(ev), 795)
        self.assertEqual(len(ev), self.man["corpus"]["n_events"])
        contents = [c.item.content for e in ev for c in e.controls]
        self.assertEqual(len(contents), len(ev))
        self.assertEqual(len(set(contents)), len(ev), "a benign change is used twice")
        self.assertEqual(self.man["corpus"]["n_distinct_benign"], self.man["corpus"]["n_benign"])
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
                self.assertIn(dev[c.wf_id].tasks[c.t].task_id, c.item.content)
        self.assertEqual({n["recency"] for n in neg}, set(V.DELTAS))
        self.assertEqual(sorted(n["recency"] for n in neg),
                         sorted(p["recency"] for p in pos for _ in range(V.V3_PER_EVENT)))

    def test_surface_discriminator_verdict_is_printed_against_0_56(self):
        """D8.benign: "verified by a two-sample test that a discriminator trained on surface
        features achieves AUC ≤ 0.56. Without this, false quarantine is free".

        L0: the ceiling is gate2_v2's 0.56, read and never restated; the criterion is v2's
        pinned one (mean CI95 upper bound over discriminator.SPLIT_SEEDS, test fraction
        0.4); the classifier is v2's algorithm (it reproduces discriminator.auc_with_ci on
        v2's five features exactly); the verdict in the manifest is the one the criterion
        gives on the rebuilt corpus -- "đạt" or "không đạt", never a relaxed ceiling."""
        self.assertEqual(V.CEILING, 0.56)
        self.assertEqual(G2.record()["ceiling"], V.CEILING)
        self.assertEqual(V.CRITERION, "mean_ci95_upper_over_split_seeds")
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
        want = V.PASS if s["hi_mean"] <= 0.56 else V.FAIL
        self.assertEqual(V.verdict(s), want)
        self.assertEqual(self.man["result"]["verdict"], want)
        self.assertIn(self.man["result"]["verdict"], ("đạt", "không đạt"))
        # T24: both floors are recorded; the clustered one is T17's wild bootstrap by
        # workflow and is reproduced from the live modules
        r = self.man["result"]
        self.assertEqual(r["floor_hi"], round(V.floor_hi(len(pos), len(neg)), 4))
        cf = V.clustered_floor(self.events)
        self.assertEqual(r["floor_hi_clustered"], cf["floor_hi_clustered"])
        self.assertEqual(r["clustered"]["ratio_mean"], cf["ratio_mean"])
        self.assertEqual(cf["n_workflows"], len({w for c in V.clusters_of(self.events)
                                                 for w in c}))
        p = self.man["protocol"]
        self.assertEqual((p["per_event"], p["per_event_v2"], p["deviation_ref"]),
                         (V.V3_PER_EVENT, 4, "docs/preregistration/lech-chuan-P3-benign.md"))
        self.assertTrue((pathlib.Path("..") / p["deviation_ref"]).is_file())
        # the diagnostic control class (v2's agent notes) must still separate completely:
        # provenance_shape tells them apart; anything else means something broke
        notes = V.build(self.runs, kind="v2-notes")
        pn, nn = V.rows_of(notes)
        sn = V.over_splits(pn, nn, V.FEATURES, seeds=(1, 2, 3))
        self.assertEqual((sn["auc_median"], sn["auc_min"]), (1.0, 1.0))
        self.assertEqual(self.man["comparisons"]["v2_notes_as_controls"]["main"]["auc_min"], 1.0)

    def test_benign_changes_are_the_agents_drift_process(self):
        """D4.drift: "A latent process independently modifies carriers benignly at rate β,
        with observation statistics matched to poisoning events."

        L1: a benign change is what v3's agent writes when the drift coin of the carrier
        fires (world_v2.drift_content through the payload's ingress provenance).  The
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

    def test_payload_length_drawn_from_v3_drift_closes_the_size_channel(self):
        """D8.benign: "620 benign carrier modifications generated to match poisoning events
        on surface statistics (edit size, embedding shift, recency, provenance shape)".

        L1, D-v3-3 (docs/preregistration/lech-chuan-P3-benign.md): the ATTACKER draws its
        payload length from the length distribution of v3's own drift on dev
        (payload.draw_length over benign.length_background), so edit size is matched by
        construction, spread included -- not by dropping the feature and not by cutting
        the drift.  build.PAYLOAD_LENGTH stays 63, the default payload stays v2's bytes,
        at L = 63 the drawn-length construction reproduces them, and a payload whose tag
        is at least L wide carries an N3 reason."""
        import build
        from v3 import payload as P
        self.assertEqual(build.PAYLOAD_LENGTH, 63)
        bg = P.length_stats(self.runs.lengths)
        self.assertEqual(self.man["corpus"]["payload_length_background"], bg)
        self.assertEqual(self.runs.lengths, V.length_background(self.runs))
        es = self.man["result"]["features"]["edit_size"]
        self.assertGreaterEqual(es["distinct_pos"], 40)
        # the spread is matched, not only the centre
        self.assertLess(abs(es["sd_pos"] - bg["sd"]), 0.25 * bg["sd"])
        pos, _ = V.rows_of(self.events)
        sizes = [p["edit_size"] for p in pos]
        import statistics
        self.assertLessEqual(abs(statistics.median(sizes) - bg["median"]), 2)
        self.assertLessEqual(abs(es["mean_pos"] - bg["mean"]), 2)
        self.assertLessEqual(abs(statistics.fmean(sizes) - bg["mean"]), 2)
        n_checked = 0
        for wf in self.runs.workflows[:20]:
            for sp in P.plan_sleeper_all(wf, V.CARRIER, 1, V.EPSILON):
                self.assertIsNone(sp.length)
                v2 = build.inject(CarrierStore(), wf, sp.spec())
                a, b = sp.item(wf), sp.at_length(build.PAYLOAD_LENGTH).item(wf)
                self.assertEqual((a.content, a.item_id), (v2.content, v2.item_id))
                self.assertEqual((b.content, b.item_id), (v2.content, v2.item_id))
                n_checked += 1
        self.assertGreater(n_checked, 20)
        why = []
        for e in self.events:
            self.assertIn(e.length, self.runs.lengths)
            if len(e.payload.content) != e.length:
                self.assertIsNotNone(e.length_reason)
                self.assertGreater(len(e.payload.content), e.length)
                why.append([e.wf_id, e.delta, e.iota, e.sigma, e.length, e.length_reason])
            else:
                self.assertIsNone(e.length_reason)
        self.assertEqual(self.man["corpus"]["payload_length_reasons"], why)


if __name__ == "__main__":
    unittest.main()
