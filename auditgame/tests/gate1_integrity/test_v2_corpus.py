"""GATE 1 -- v2 corpus: real Verified + Multilingual workflows, H 6..14, reuse <= 2, family split."""
import collections
import unittest

import corpus_v2 as C
import draft_setup as D


class TestCorpusV2(unittest.TestCase):
    def setUp(self):
        self.wfs = C.make_corpus_v2()

    def test_size_and_families(self):
        self.assertLessEqual(len(self.wfs), D.N_WORKFLOWS)        # 100 built at seed 2027
        self.assertGreaterEqual(len(self.wfs), 90)
        self.assertGreaterEqual(len({w.repo for w in self.wfs}), 15)
        self.assertEqual({C.pool_of(w) for w in self.wfs}, set(D.POOLS))

    def test_horizon_range(self):
        Hs = {w.H for w in self.wfs}
        self.assertTrue(all(D.H_RANGE[0] <= h <= D.H_RANGE[1] for h in Hs))
        self.assertGreaterEqual(len(Hs), 7)

    def test_instance_reuse_capped(self):
        use = collections.Counter(t.task_id for w in self.wfs for t in w.tasks)
        self.assertLessEqual(max(use.values()), 2)

    def test_tasks_follow_history(self):
        for w in self.wfs:
            self.assertEqual({t.repo for t in w.tasks}, {w.repo})

    def test_split_puts_the_largest_family_in_dev(self):
        dev, ev = C.split(self.wfs)
        self.assertFalse({w.repo for w in dev} & {w.repo for w in ev})
        self.assertGreaterEqual(len(dev), D.DEV_SHARE * len(self.wfs))
        big = collections.Counter(w.repo for w in self.wfs).most_common(1)[0][0]
        self.assertIn(big, {w.repo for w in dev})
        self.assertGreaterEqual(C.kish(ev), 5.0)          # eval CI is not one repo in disguise

    def test_pools_do_not_perturb_each_other(self):
        # D8: H is seeded per repo, so dropping a pool leaves the other's workflows unchanged
        only_v = C.make_corpus_v2(pools=("verified",))
        key = lambda ws: sorted((w.repo, tuple(t.task_id for t in w.tasks)) for w in ws)
        both_v = [w for w in self.wfs if C.pool_of(w) == "verified"]
        self.assertTrue(set(key(both_v)) <= set(key(only_v)))

    def test_a_repo_cannot_change_pool_between_builds(self):
        """A repo's pool is fixed the first time it is built; a later build that sees it in
        another pool must fail loudly, not overwrite pool_of() for earlier workflows."""
        saved = dict(C._POOL_OF)
        try:
            C._POOL_OF["django/django"] = "multilingual"
            with self.assertRaises(ValueError):
                C.make_corpus_v2(n=99)            # a fresh cache key forces a rebuild
        finally:
            C._POOL_OF.clear()
            C._POOL_OF.update(saved)


if __name__ == "__main__":
    unittest.main()
