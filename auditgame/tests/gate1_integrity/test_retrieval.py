"""
GATE 1 -- graded retrieval (R).
Spec: pipelines/SPEC-R-Truy-xuat.md

A test's NAME states the claim it defends; the Vietnamese wording of that claim
lives in the docstring under `Thesis claim (vi):`.
"""
from __future__ import annotations
import random
import subprocess
import sys
import unittest

import build
import retrieval
from core import CarrierStore, Item, seed_of


class GradedRetrieval(unittest.TestCase):

    def test_exact_match_is_the_special_case_theta_equals_one(self):
        """If R cannot reproduce the old table, we cannot tell "R changed the
        conclusion" from "R has a bug".  A design constraint, not a convenience.

        Thesis claim (vi): "R khong thay the hanh vi cu, no tong quat hoa".
        """
        a = retrieval.topic_of(["django/db/models/query.py"])
        b = retrieval.topic_of(["django/db/models/query.py"])
        c = retrieval.topic_of(["django/db/models/sql/compiler.py"])
        self.assertTrue(retrieval.retrieved(a, b, theta=1.0),
                        "EQUAL token sets must be retrieved at theta=1")
        self.assertFalse(retrieval.retrieved(a, c, theta=1.0),
                         "DIFFERENT token sets must not be retrieved at theta=1")

    def test_sim_is_deterministic_across_calls(self):
        """The function does not learn and does not sample.

        Thesis claim (vi): "replay khop bit".
        """
        a = retrieval.topic_of(["a/b/c.py", "a/d.py"])
        b = retrieval.topic_of(["a/b/e.py"])
        vals = {retrieval.sim(a, b) for _ in range(50)}
        self.assertEqual(len(vals), 1, f"sim is not deterministic: {vals}")

    def test_epsilon_controls_retrievability(self):
        """Measured on the current version: the payload at eps=0.05 and eps=0.95 is
        byte-for-byte IDENTICAL, same item_id.  A quarter of the attack space is a
        no-op.

        Thesis claim (vi): "epsilon la ngan sach phan biet", not a decorative parameter.
        """
        target = retrieval.topic_of(["django/db/models/query.py",
                                     "django/db/models/sql/compiler.py"])
        sims = [retrieval.sim(retrieval.payload_topic(target, eps), target)
                for eps in (0.2, 0.5, 0.8, 1.0)]
        self.assertEqual(sims, sorted(sims),
                         f"sim must be NON-DECREASING in epsilon, measured {sims}")
        self.assertLess(sims[0], sims[-1],
                        f"epsilon cannot change sim: {sims} -- still a no-op")
        self.assertAlmostEqual(sims[-1], 1.0, places=9,
                               msg="eps=1 must coincide exactly with task sigma's topic")

    def test_larger_epsilon_makes_a_larger_payload(self):
        """Without this second dimension, epsilon is just a free "make it stronger"
        knob and the distinguishability budget does not exist.  `size` is an
        F_match feature.

        Thesis claim (vi): "epsilon danh doi truy xuat LAY do kho phat hien".
        """
        target = retrieval.topic_of([f"pkg/mod{i}/file{i}.py" for i in range(5)])
        sizes = [len(retrieval.payload_topic(target, eps))
                 for eps in (0.2, 0.5, 0.8, 1.0)]
        self.assertEqual(sizes, sorted(sizes), f"|A| must be non-decreasing: {sizes}")
        self.assertLess(sizes[0], sizes[-1],
                        f"epsilon cannot change the payload size: {sizes}")

    def test_payload_is_a_subset_of_the_target_topic(self):
        """If the payload added tokens OUTSIDE the target, the Jaccard denominator
        would inflate and sim would DROP -- a larger epsilon would weaken the
        attack, exactly backwards from the intended semantics.

        Thesis claim (vi): "sim(A,B) = eps" -- a simple relation, checkable by hand.
        """
        target = retrieval.topic_of(["a/b.py", "c/d.py", "e/f.py"])
        for eps in (0.1, 0.4, 0.7, 1.0):
            with self.subTest(eps=eps):
                self.assertTrue(
                    retrieval.payload_topic(target, eps) <= target,
                    "the payload must be a SUBSET of the target topic")

    def test_topic_does_not_depend_on_file_order(self):
        """Whatever order the gold patch lists files in, the topic must come out
        the same.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        x = retrieval.topic_of(["a/b.py", "c/d.py"])
        y = retrieval.topic_of(["c/d.py", "a/b.py"])
        self.assertEqual(x, y, "topic depends on file order => traces do not replay")


class GradedRetrievalIsWiredIntoTheStore(unittest.TestCase):
    """The functions above are the DESIGN; this class is about whether the
    measurement core actually uses them.  For a long time it did not:
    retrieval.py ended with "not yet wired into core.CarrierStore", so every test
    in the class above could pass while the runner still compared topics with
    `==`.  A module that is only imported proves nothing.
    """

    @staticmethod
    def _store(*topics):
        st = CarrierStore()
        for i, tp in enumerate(topics):
            st.write(Item(carrier="memory", topic=tp, content=f"item {i}",
                          created_at=0, provenance="agent/notes", poisoned=False))
        return st

    def test_the_store_retrieves_a_partial_topic_match(self):
        """The whole point of R, at the only place that decides anything: an item
        whose topic OVERLAPS the task's enough must come back from
        core.CarrierStore.retrieve.  Under `==` it never could, which is why
        epsilon had no surface and why 58 of 58 real workflows were dropped.

        Thesis claim (vi): "truy xuat cua LOI da la Jaccard, khong con la ==".
        """
        query = retrieval.topic_of(["django/db/models/query.py"])
        near = retrieval.Topic({"django", "db", "models"})       # sim = 3/4
        far = retrieval.Topic({"django"})                        # sim = 1/4
        self.assertAlmostEqual(retrieval.sim(near, query), 0.75, places=9)
        self.assertAlmostEqual(retrieval.sim(far, query), 0.25, places=9)
        got = {i.content for i in self._store(query, near, far).retrieve(query)}
        self.assertIn("item 0", got, "an IDENTICAL topic must always be retrieved")
        self.assertIn("item 1", got,
                      f"core.CarrierStore.retrieve did not return an item at "
                      f"sim=0.75 with theta={retrieval.THETA}: retrieval is "
                      f"still two-valued, so epsilon has no surface to act on")
        self.assertNotIn("item 2", got,
                         "retrieval returned an item at sim=0.25, below "
                         "theta -- a threshold that admits everything is not a "
                         "graded retrieval either")

    def test_exact_matching_is_recovered_at_theta_one(self):
        """SPEC-R Part 2.3 makes this a DESIGN CONSTRAINT, not a convenience: if
        the graded store cannot reproduce the exact-matching table, "R changed the
        conclusion" cannot be told apart from "R has a bug".

        Thesis claim (vi): "R khong thay the hanh vi cu, no tong quat hoa".
        """
        query = retrieval.topic_of(["django/db/models/query.py"])
        near = retrieval.Topic({"django", "db", "models"})
        got = {i.content for i in self._store(query, near).retrieve(query, theta=1.0)}
        self.assertEqual(got, {"item 0"},
                         "at theta=1.0 the store must retrieve equal topics and "
                         "nothing else, i.e. exactly what `==` did")

    def test_a_single_token_topic_is_two_valued_at_every_theta(self):
        """THE MOCK INVARIANT, as a property rather than as a diff.

        Every number recorded for this benchmark was measured on the mock, whose
        topic is one token.  Jaccard on one-token sets takes only {0, 1}, so
        `sim >= theta` is `a == b` for EVERY theta in (0, 1] -- which is why
        wiring graded retrieval in cannot move the mock table, and why a mock
        number that DOES move is a bug in the wiring rather than a consequence
        of it.  Asserted over the mock's own topic vocabulary.

        Thesis claim (vi): "voi topic mot token, moi theta deu tai lap phep so bang".
        """
        for theta in (0.01, 0.25, 0.5, 0.75, 1.0):
            for a in build.TOPICS:
                for b in build.TOPICS:
                    with self.subTest(theta=theta, a=a, b=b):
                        self.assertEqual(
                            retrieval.retrieved(retrieval.as_topic(a),
                                                retrieval.as_topic(b), theta),
                            a == b,
                            f"theta={theta} separates mock topics {a!r}/{b!r} "
                            f"differently from `==`, so the recorded mock "
                            f"numbers would move")

    def test_the_payload_topic_keeps_the_representation_it_was_given(self):
        """`Item.__post_init__` hashes seed_of(carrier, topic, ...) into item_id,
        and seed_of STRINGIFIES its arguments -- so the payload's topic reaching
        the Item as a bare `frozenset` would give it a PYTHONHASHSEED-dependent
        id, and detector.score seeds on that id.  A string topic must come back a
        string for the same reason: build.py interpolates it into the payload's
        frozen content template, and "[frozenset({'orm'})]" is not "[orm]".

        Thesis claim (vi): "ket qua tai lap duoc" -- khong phu thuoc PYTHONHASHSEED.
        """
        self.assertEqual(retrieval.payload_topic_like("orm", 0.05), "orm")
        self.assertEqual(retrieval.payload_topic_like("orm", 0.95), "orm")
        target = retrieval.topic_of(["django/db/models/query.py"])
        got = retrieval.payload_topic_like(target, 0.5)
        self.assertIsInstance(got, retrieval.Topic)
        self.assertEqual(str(got), "|".join(sorted(got)),
                         "a payload topic that does not stringify canonically "
                         "gives the same payload a different item_id per process")

    def test_the_payload_item_id_is_stable_across_PYTHONHASHSEED(self):
        """The property above, end to end and ACROSS PROCESSES -- the only place
        frozenset iteration order can actually be observed.  Runs build.inject on
        a token-set topic, which is the path that did not exist before epsilon
        was given a surface.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        code = (
            "import random, build, retrieval\n"
            "from core import Task, Workflow, PoisonSpec, CarrierStore\n"
            "tp = [retrieval.topic_of(['pkg/a/b%d.py' % i, 'pkg/c/d%d.py' % i])\n"
            "      for i in range(4)]\n"
            "wf = Workflow(wf_id='w', repo='r', tasks=[\n"
            "    Task(task_id='t%d' % i, repo='r', base_commit='0'*7,\n"
            "         topic=tp[i], problem='') for i in range(4)])\n"
            "ps = PoisonSpec(carrier='memory', iota=1, sigma=3, epsilon=0.5)\n"
            "it = build.inject(CarrierStore(), wf, ps)\n"
            "print(it.item_id, str(it.topic), it.content)\n")
        outs = set()
        for h in ("0", "1", "424242"):
            r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                               text=True, env={"PYTHONHASHSEED": h, "PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 0, f"run failed at HASHSEED={h}: {r.stderr[-400:]}")
            outs.add(r.stdout)
        self.assertEqual(len(outs), 1,
                         f"the payload changes with PYTHONHASHSEED:\n"
                         f"{chr(10).join(sorted(outs))}")


class EpsilonHasASurface(unittest.TestCase):
    """Advisor question 3, at the injection site.  Measured before this task: the
    payload at eps=0.05 and eps=0.95 was byte-for-byte identical, same item_id,
    because build.inject stamped it with sigma's WHOLE topic.
    """

    @staticmethod
    def _wf():
        from core import Task, Workflow
        tp = [retrieval.topic_of([f"pkg/mod{i}/a{i}.py", f"pkg/mod{i}/b{i}.py"])
              for i in range(6)]
        return Workflow(wf_id="w", repo="r", tasks=[
            Task(task_id=f"t{i}", repo="r", base_commit="0" * 7,
                 topic=tp[i], problem="") for i in range(6)])

    def _payload(self, wf, eps):
        from core import PoisonSpec, CarrierStore
        ps = PoisonSpec(carrier="memory", iota=1, sigma=3, epsilon=eps)
        return build.inject(CarrierStore(), wf, ps)

    def test_epsilon_changes_the_injected_payload_on_a_token_set_topic(self):
        """The knob (k, iota, sigma, epsilon) that did nothing at all.

        Thesis claim (vi): "epsilon la ngan sach phan biet", not a decorative parameter.
        """
        wf = self._wf()
        lo, hi = self._payload(wf, 0.05), self._payload(wf, 0.95)
        self.assertNotEqual(
            lo.content, hi.content,
            "the payload at eps=0.05 and eps=0.95 is byte-for-byte identical -- "
            "epsilon is still a no-op")
        self.assertNotEqual(lo.item_id, hi.item_id)

    def test_epsilon_buys_retrievability_and_pays_in_size(self):
        """What makes it a BUDGET rather than a "make it stronger" knob: the two
        ends pull against each other.  `size` is an F_match feature, so the
        payload that is certain to be retrieved is also the easiest to spot.

        Thesis claim (vi): "epsilon danh doi truy xuat LAY do kho phat hien".
        """
        wf = self._wf()
        target = wf.tasks[3].topic
        sims, sizes = [], []
        for eps in (0.25, 0.5, 0.75, 1.0):
            it = self._payload(wf, eps)
            sims.append(retrieval.sim(retrieval.as_topic(it.topic), target))
            sizes.append(it.surface(now=3)["size"])
        self.assertEqual(sims, sorted(sims), f"sim must be non-decreasing: {sims}")
        self.assertEqual(sizes, sorted(sizes), f"size must be non-decreasing: {sizes}")
        self.assertLess(sims[0], sims[-1], f"epsilon cannot change sim: {sims}")
        self.assertLess(sizes[0], sizes[-1],
                        f"epsilon buys retrievability for FREE -- size does not "
                        f"grow with it: {sizes}. There is no budget, only a dial.")

    def test_a_small_epsilon_can_miss_the_target_entirely(self):
        """The FAILING end, which is the half a budget needs and the half every
        earlier pipeline lacked.  At eps low enough that |A|/|B| < theta, the
        payload is NOT retrieved at sigma and the attack simply misses.

        Thesis claim (vi): "epsilon nho -> khong vuot theta -> tan cong TRUOT".
        """
        from core import CarrierStore, PoisonSpec
        # |B| = 4 tokens, so eps=0.25 gives |A| = 1 and sim = 0.25 < theta = 0.5.
        wf = self._wf()
        target = wf.tasks[3].topic
        self.assertEqual(len(target), 4, "fixture drifted: |sigma topic| != 4")
        st = CarrierStore()
        low = build.inject(st, wf, PoisonSpec(carrier="memory", iota=1, sigma=3,
                                              epsilon=0.25))
        self.assertNotIn(low.item_id, [i.item_id for i in st.retrieve(target)],
                         f"a payload at sim="
                         f"{retrieval.sim(retrieval.as_topic(low.topic), target)} "
                         f"was retrieved anyway at theta={retrieval.THETA}: "
                         f"epsilon has no failing end, so it is not a budget")
        st2 = CarrierStore()
        high = build.inject(st2, wf, PoisonSpec(carrier="memory", iota=1, sigma=3,
                                                epsilon=1.0))
        self.assertIn(high.item_id, [i.item_id for i in st2.retrieve(target)],
                      "eps=1.0 must be retrieved at sigma, or the attack can "
                      "never fire and the failing end above proves nothing")


class DormancyHoldsUnderGradedRetrieval(unittest.TestCase):

    def test_the_payload_is_not_retrievable_before_sigma_on_real_topics(self):
        """`plan_poison` guarantees the payload lies dormant for exactly Delta
        tasks.  It used to check `tp[j] != tp[sigma]` -- set INEQUALITY against
        SIGMA's topic.  Both halves broke under graded retrieval: the payload no
        longer carries sigma's whole topic (epsilon narrows it), and `!=` is not
        the predicate the store uses, so a merely OVERLAPPING earlier task would
        pull the payload up and the true Delta would be smaller than the declared
        one -- the measured 23-44% contamination bug, returning through the
        threshold instead of through eager insertion.

        Driven over REAL topics, because on the mock the old and new predicates
        coincide and the regression would be invisible.

        Thesis claim (vi): "payload nam im dung Delta task, khong no som".
        """
        import swebench_dataset
        ds = swebench_dataset.SWEBenchDataset(sweep_deltas=())
        wfs = list(ds.workflows(12, 8, seed=2026))
        checked = 0
        for i, wf in enumerate(wfs):
            for delta in (1, 2, 4):
                ps = build.plan_poison(wf, "memory", delta,
                                       random.Random(seed_of("dorm", i, delta)))
                if ps is None:
                    continue           # N3: unbuildable, not a zero
                st = CarrierStore()
                payload = build.inject(st, wf, ps)
                for t in range(ps.iota, ps.sigma):
                    got = [x.item_id for x in st.retrieve(wf.tasks[t].topic)]
                    self.assertNotIn(
                        payload.item_id, got,
                        f"wf {wf.wf_id} d={delta}: the payload planted at "
                        f"iota={ps.iota} is retrievable at t={t} < sigma="
                        f"{ps.sigma}, so the real Delta is smaller than the "
                        f"declared one and the RQ1 axis is contaminated")
                self.assertIn(
                    payload.item_id,
                    [x.item_id for x in st.retrieve(wf.tasks[ps.sigma].topic)],
                    f"wf {wf.wf_id} d={delta}: the payload is not retrievable at "
                    f"sigma either, so it can never fire")
                checked += 1
        self.assertGreater(checked, 10,
                           f"only {checked} configurations exercised -- too few "
                           f"for this claim to rest on")


if __name__ == "__main__":
    unittest.main()
