"""Draft S8 workload: dev, the primary eval split (D-v3-1) and the secondary one (T2).

Each test protects one DCM row of v3/dcm/T02.csv; its docstring carries the id and the
verbatim draft sentence.  The tests build the eval splits to check their SHAPE (families,
H, instances); no policy runs on them (plan S6).  Run from auditgame/.
"""
import collections
import json
import pathlib
import random
import unittest

import corpus_v2
import draft_setup as D
from core import seed_of
from v3 import config as C
from v3 import corpus as K

P0_CORPUS = pathlib.Path("spikes") / "v3-p0" / "corpus.json"


def _index_by_id():
    return {r["instance_id"]: r for r in K._index()}


class TestS8Corpus(unittest.TestCase):
    def test_eval_split_is_one_pass_20_untouched_families_capped_at_5(self):
        """D8.scale (C14, Q10, D-v3-1): "100 multi-step repair workflows over 15
        repositories, 6–14 tasks each".

        L2: the eval split is config.EVAL_SOURCE_PRIMARY -- SWE-rebench-V2 instances created
        from 2024-01-01, the 20 largest untouched families, v2's builder cut once (offset 0,
        builder seed 2027) and capped at 5 workflows per family.  Realised: 96 workflows /
        20 families, Kish 19.86; the split hashes to the committed EVAL_SPLIT_SHA256."""
        src = C.EVAL_SOURCE_PRIMARY
        self.assertEqual((src.dataset, src.created_from, src.n_families, src.cap_per_family),
                         ("nebius/SWE-rebench-V2", "2024-01", 20, 5))
        self.assertEqual((src.h_range, src.one_pass, src.reuse_instances),
                         (D.H_RANGE, True, False))
        self.assertEqual((K.CREATED_FROM, K.N_FAMILIES, K.CAP_PER_FAMILY, K.BUILDER_SEED),
                         ("2024-01-01", 20, 5, 2027))

        specs = K._build_primary()
        self.assertEqual(K.eval_digest("primary"), K.EVAL_SPLIT_SHA256)
        by_id = _index_by_id()
        cand = K._candidate_families()
        chosen = K._chosen_families()

        # rule 5: the 20 largest candidate families, by count only
        self.assertEqual(len(chosen), 20)
        self.assertEqual({s["family"] for s in specs}, set(chosen))
        smallest = min(len(cand[f]) for f in chosen)
        self.assertTrue(all(len(cand[f]) <= smallest for f in cand if f not in chosen))

        per = collections.defaultdict(list)
        for s in specs:
            per[s["family"]].append(s)
            self.assertTrue(D.H_RANGE[0] <= len(s["instances"]) <= D.H_RANGE[1], s["wf_id"])
            for i in s["instances"]:                       # rule 2
                self.assertGreaterEqual(by_id[i]["created_at"], "2024-01-01", i)
                self.assertEqual(K.family_of(by_id[i]["repo"]), s["family"], i)
        for fam, ws in per.items():
            self.assertLessEqual(len(ws), 5, fam)
            # one pass: consecutive windows from offset 0 of the created_at-ordered history,
            # with H drawn by v2's per-repo RNG
            ws.sort(key=lambda s: s["window"])
            rows = [r["instance_id"] for r in cand[fam]]
            rng, i = random.Random(seed_of(2027, fam, 0)), 0
            for w in ws:
                H = rng.randint(*D.H_RANGE)
                self.assertEqual(w["instances"], rows[i:i + H], f"{fam} window {w['window']}")
                i += H
            if len(ws) < 5:                                # stopped because the next did not fit
                self.assertGreater(i + rng.randint(*D.H_RANGE), len(rows), fam)

        # rule 7: pinned order is chronological by first instance
        firsts = [(by_id[s["instances"][0]]["created_at"], s["instances"][0]) for s in specs]
        self.assertEqual(firsts, sorted(firsts))
        self.assertEqual([s["wf_id"] for s in specs], [f"v3e-{i:03d}" for i in range(len(specs))])

        summ, pin = K.eval_summary("primary"), K.EVAL_SUMMARY_PINNED["primary"]
        for key in ("workflows", "families", "kish", "instances", "H_histogram",
                    "languages_by_family", "languages_by_workflow", "rules"):
            self.assertEqual(summ[key], pin[key], key)
        self.assertEqual(summ["per_delta"]["8"], pin["delta8"])
        self.assertEqual((summ["workflows"], summ["families"], summ["kish"]), (96, 20, 19.86))
        sizes = collections.Counter(s["family"] for s in specs).values()
        self.assertAlmostEqual(K.kish(sizes), sum(sizes) ** 2 / sum(n * n for n in sizes))

    def test_eval_families_disjoint_from_dev(self):
        """D8.heldout-family (C14): "Repository families are also held out."

        Neither eval split shares a family (case-insensitive, after ALIASES) or an instance
        with dev -- the 100 v2 workflows -- and the two eval splits share none either."""
        dev = K.dev_workflows()
        dev_fams = {K.family_of(w.repo) for w in dev}
        dev_inst = {t.task_id for w in dev for t in w.tasks}
        prim, sec = K._build_primary(), K._build_secondary()
        by_id = _index_by_id()
        prim_fams = {s["family"] for s in prim}
        prim_repo_fams = {K.family_of(by_id[i]["repo"]) for s in prim for i in s["instances"]}
        sec_fams = {K.family_of(s["family"]) for s in sec}
        v2_fams = {K.family_of(r) for r in K.v2_repos()}
        self.assertEqual(v2_fams, dev_fams)
        self.assertEqual(len(v2_fams), 17)
        for name, fams in (("primary", prim_fams | prim_repo_fams), ("secondary", sec_fams)):
            self.assertEqual(fams & dev_fams, set(), f"{name} shares a family with dev")
        self.assertEqual(prim_fams & sec_fams, set(), "primary shares a family with secondary")
        prim_inst = {i for s in prim for i in s["instances"]}
        sec_inst = {i for s in sec for i in s["instances"]}
        self.assertEqual(prim_inst & dev_inst, set())
        self.assertEqual(sec_inst & dev_inst, set())
        self.assertEqual(prim_inst & sec_inst, set())
        # the raw repositories behind a primary family never lowercase to a touched one
        touched = K.touched_families()
        for s in prim:
            for i in s["instances"]:
                self.assertNotIn(by_id[i]["repo"].lower(), touched, i)

    def test_no_instance_reused_in_eval(self):
        """D12.instances (C14, Q10): "Instances from one workflow are correlated".

        One pass: every instance is in at most one workflow of either eval split, so no
        two eval workflows are correlated through a shared instance."""
        for split in K.SPLITS:
            specs = K._specs(split)
            n = collections.Counter(i for s in specs for i in s["instances"])
            self.assertEqual(max(n.values()), 1, f"{split}: an instance is reused")
            self.assertEqual(sum(n.values()), K.EVAL_SUMMARY_PINNED[split]["instances"])
        self.assertFalse(C.EVAL_SOURCE_PRIMARY.reuse_instances)
        self.assertFalse(C.EVAL_SOURCE_SECONDARY.reuse_instances)

    def test_family_rule_is_declared_and_applied(self):
        """D8.release-splits (C14, D-v3-1): "Splits by repository family and by attacker
        policy."

        A family is a repository, case-insensitive, with renamed / forked repos merged by
        the explicit ALIASES; a shared name after the owner alone merges nothing (the
        same-name groups that are different projects are DISTINCT_SAME_NAME), and every
        same-name group that could move the choice or the exclusion is resolved one way or
        the other.  Exercise repositories are dropped by a declared rule."""
        short = lambda r: r.lower().split("/")[1]
        for old, new in K.ALIASES.items():
            self.assertEqual(old, old.lower())
            self.assertEqual(short(old), short(new), f"{old} -> {new}")
            self.assertNotIn(new, K.ALIASES, "aliases resolve in one step")
        for name, group in K.DISTINCT_SAME_NAME.items():
            self.assertEqual({short(r) for r in group}, {name})
            self.assertEqual(len({K.family_of(r) for r in group}), len(group))

        # exercise rule: drops the P0 report's cases, keeps look-alikes
        for r in ("vaskoz/dailycodingproblem-go", "TheAlgorithms/Java", "exercism/python"):
            self.assertTrue(K.is_exercise(r), r)
        for r in ("kata-containers/agent", "sqlkata/querybuilder", "onnx/sklearn-onnx",
                  "learningequality/studio"):
            self.assertFalse(K.is_exercise(r), r)

        # case-insensitive exclusion: v2's phpoffice/phpspreadsheet is PHPOffice/PhpSpreadsheet
        # in SWE-rebench-V2 (49 instances from 2024) and stays out
        repos = {r["repo"] for r in K._index()}
        self.assertIn("PHPOffice/PhpSpreadsheet", repos)
        self.assertIn("phpoffice/phpspreadsheet", K.touched_families())
        chosen = K._chosen_families()
        self.assertNotIn("phpoffice/phpspreadsheet", chosen)
        # a shared name is not a family: Sage/carbon stays although briannesbitt/Carbon
        # (secondary split) is touched
        self.assertIn("briannesbitt/carbon", K.touched_families())
        self.assertIn("sage/carbon", chosen)
        # a rename is: dalance/veryl is merged into veryl-lang/veryl
        self.assertIn("veryl-lang/veryl", chosen)
        self.assertEqual(K.family_of("dalance/veryl"), "veryl-lang/veryl")

        # every same-name group that could touch the choice or the exclusion is resolved
        cand, touched = K._candidate_families(), K.touched_families()
        threshold = min(len(cand[f]) for f in chosen)
        post = collections.Counter(r["repo"].lower() for r in K._index()
                                   if r["created_at"] >= K.CREATED_FROM)
        groups = collections.defaultdict(set)
        for r in repos | set(touched):
            groups[short(r)].add(r.lower())
        for name, members in groups.items():
            fams = {K.family_of(m) for m in members}
            if len(fams) < 2:
                continue
            relevant = ((fams & set(chosen)) or (fams & touched)
                        or sum(post[m] for m in members) >= threshold)
            if relevant:
                declared = set(K.DISTINCT_SAME_NAME.get(name, ()))
                self.assertLessEqual(fams, declared,
                                     f"same-name group {name!r} {sorted(members)} is neither "
                                     f"aliased nor declared distinct")

    def test_secondary_split_is_the_p0_one_pass_split(self):
        """D8.scale (C14(a), Q10): "100 multi-step repair workflows over 15 repositories,
        6–14 tasks each".

        The secondary analysis is the former C14(a) split exactly as P0 built it
        (tools/v3_p0_corpus.py, one pass, builder seed 2027): 26 workflows / 18 families,
        Kish 10.24, 14 of them by the declared "H = family size" rule; 18 workflows / 12
        families host Delta = 8."""
        self.assertEqual(C.EVAL_SOURCE_SECONDARY.builder_seed, 2027)
        p0 = json.loads(P0_CORPUS.read_text(encoding="utf-8"))
        want = [(w["repo"], w["rule"], w["instances"]) for w in p0["split"]["one_pass"]]
        got = [(s["family"], s["rule"], s["instances"]) for s in K._build_secondary()]
        self.assertEqual(got, want)
        self.assertEqual(p0["builder_seed"], 2027)
        self.assertEqual(K.eval_digest("secondary"), K.SECONDARY_SPLIT_SHA256)

        summ, pin = K.eval_summary("secondary"), K.EVAL_SUMMARY_PINNED["secondary"]
        p0s = p0["summary"]["one_pass"]
        self.assertEqual((summ["workflows"], summ["families"], summ["kish"]),
                         (p0s["workflows"], p0s["families"], p0s["kish"]))
        self.assertEqual((summ["workflows"], summ["families"], summ["kish"]), (26, 18, 10.24))
        self.assertEqual(summ["rules"], p0s["rules"])
        self.assertEqual(summ["rules"]["H = family size"], 14)
        self.assertEqual({k: summ["per_delta"]["8"][k] for k in ("workflows", "families")},
                         {k: p0s["per_delta"]["8"][k] for k in ("workflows", "families")})
        for key in ("workflows", "families", "kish", "instances", "H_histogram",
                    "languages_by_family", "languages_by_workflow", "rules"):
            self.assertEqual(summ[key], pin[key], key)
        self.assertEqual(summ["per_delta"]["8"], pin["delta8"])

    def test_dev_is_the_v2_corpus_100_workflows(self):
        """D5.5.dev-split (Q10): "Adaptive attack development is performed on a
        development split".

        Dev is the whole v2 corpus, 100 workflows, v2's eval workflows included: v2 has run
        on all of them, so from v3 on they are development data only."""
        dev = K.dev_workflows()
        self.assertEqual(len(dev), C.DEV_N_WORKFLOWS)
        self.assertEqual(len(dev), 100)
        self.assertEqual([w.wf_id for w in dev], [w.wf_id for w in corpus_v2.make_corpus_v2()])
        v2_dev, v2_eval = corpus_v2.split(corpus_v2.make_corpus_v2())
        self.assertEqual((len(v2_dev), len(v2_eval)), (43, 57))
        self.assertEqual({w.wf_id for w in dev}, {w.wf_id for w in v2_dev + v2_eval})


if __name__ == "__main__":
    unittest.main()
