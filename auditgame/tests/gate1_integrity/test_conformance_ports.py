"""
GATE 1 -- CONFORMANCE CONTRACTS for the other three ports: Dataset - Agent - Defense.
Spec: pipelines/SPEC-Framework-Benchmark.md Parts 2.2-2.4 and Part 4.

Same principle as AttackPipeline's K1-K6: a port that does not declare its scope
is not a port -- it is a hidden constant.  And once declared, the scope must be
ENFORCEABLE.

Two invariants worth calling out, both born from bugs that were MEASURED:

  A2 -- `MockAgent` never wrote into queue/branch, so injecting there always gave
        n_c = 1 and pinned the ITEM DENSITY axis to a constant.
  F3 -- Sentinel declared that it used its belief, yet the ablation gave EXACTLY
        0.0000 at every Delta: C4 "blind Sentinel" was identical to Sentinel.
        Declaring "reads scores" while the score cannot change behaviour is RED,
        not a result.
"""
from __future__ import annotations
import random
import unittest

import agents
import datasets
import policies as P
import retrieval
from core import CarrierStore, Item, seed_of
from tests.fixtures import identifiers




# =========================================================== DatasetPipeline ==

class DatasetConformance(unittest.TestCase):

    def _each(self):
        self.assertTrue(datasets.REGISTRY, "dataset REGISTRY is empty")
        yield from datasets.REGISTRY.items()

    def test_D1_same_seed_yields_the_same_workflows(self):
        """The foundation of everything else.  `hash()` inside base_commit used to
        break this.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        for name, ds in self._each():
            with self.subTest(dataset=name):
                a = [(w.wf_id, tuple(t.base_commit for t in w.tasks))
                     for w in ds.workflows(4, 6, seed=11)]
                b = [(w.wf_id, tuple(t.base_commit for t in w.tasks))
                     for w in ds.workflows(4, 6, seed=11)]
                self.assertEqual(a, b, f"[{name}] workflows differ between two builds at the same seed")

    @staticmethod
    def _retrieval_probe(query_topic):
        """Ask the retrieval the RUNNER actually uses what it does with a topic
        that PARTIALLY overlaps the query.

        Returns (sim_high, sim_low, retrieved_names) for three planted items:
        `equal` (the same topic), `high` and `low` (strict subsets, so their
        Jaccard similarity to the query is |A|/|query|, strictly between 0 and 1
        and different from each other).

        Only usable when the topic is a token set; a string topic has no partial
        overlap to construct, which is itself the point -- see the caller.
        """
        tokens = sorted(query_topic)
        hi, lo = frozenset(tokens[:2]), frozenset(tokens[:1])
        store = CarrierStore()
        planted = {}
        for label, topic in (("equal", frozenset(query_topic)),
                             ("high", hi), ("low", lo)):
            it = Item(carrier="memory", topic=topic, content=f"probe item {label}",
                      created_at=0, provenance="agent/notes", poisoned=False)
            planted[store.write(it).item_id] = label
        got = {planted[i.item_id] for i in store.retrieve(query_topic)}
        return retrieval.sim(hi, query_topic), retrieval.sim(lo, query_topic), got

    def test_D2_topic_kind_is_declared_truthfully(self):
        """`topic_kind` decides which AttackPipeline may be used -- declare it
        wrongly and the framework will happily run a meaningless combination.

        The old version asserted `isinstance(topic, frozenset)` for "graded" and
        `isinstance(topic, str)` for "exact" -- the TYPE of the topic, not the
        BEHAVIOUR of retrieval.  datasets.py defines the two values by behaviour:
        graded is "Jaccard retrieval -> sim continuous", exact is "sim in {0,1}".
        A dataset can hand out token sets while core.CarrierStore.retrieve still
        compares them with `==`, and then the declaration is false even though
        every type check passes.  That is what swebench did: it declared "graded",
        which un-gated GradedAttack, whose payload topic is a strict SUBSET of
        sigma's and therefore can NEVER be retrieved under `==` -- every eps < 1
        would have reported harm == 0.

        So probe the behaviour: plant items whose similarity to the query topic is
        strictly between 0 and 1 and see whether retrieval separates them.
        A dataset declaring "graded" must retrieve the closer one; a dataset
        declaring "exact" must retrieve neither, and only the equal one.

        Thesis claim (vi): "cong nao khong khai pham vi thi khong phai cong".
        """
        for name, ds in self._each():
            with self.subTest(dataset=name, topic_kind=ds.scope().topic_kind):
                self._assert_topic_kind_truthful(name, ds)

    def _assert_topic_kind_truthful(self, name, ds):
        """The body of D2, factored out so D2b can prove it goes RED."""
        kind = ds.scope().topic_kind
        self.assertIn(kind, ("exact", "graded"))
        tasks = [t for w in ds.workflows(3, 4, seed=3) for t in w.tasks]
        topic = tasks[0].topic
        if isinstance(topic, str):
            # No partial overlap exists, so retrieval CANNOT be graded.
            self.assertEqual(
                kind, "exact",
                f"[{name}] declares {kind!r} but its topic is a plain string: "
                f"sim can only be 0 or 1, so epsilon has no surface to act on")
            return
        self.assertIsInstance(
            topic, frozenset, f"[{name}] topic is neither a string nor a token set")
        # A partial overlap needs >= 3 tokens to build two DISTINCT
        # strictly-between similarities.  Never skip here: a skip is a claim with
        # no evidence, and this is the claim that decides which attacker class
        # may run.
        probe = next((t.topic for t in tasks if len(t.topic) >= 3), None)
        self.assertIsNotNone(
            probe,
            f"[{name}] no task in 3 workflows has a topic with >= 3 tokens, so "
            f"the partial-overlap probe cannot be built and topic_kind cannot be "
            f"checked BEHAVIOURALLY at all")
        s_hi, s_lo, got = self._retrieval_probe(probe)
        # the fixture itself must be a partial overlap, or it proves nothing
        self.assertTrue(0.0 < s_lo < s_hi < 1.0,
                        f"probe is not a partial overlap: {s_lo} {s_hi}")
        self.assertIn("equal", got,
                      f"[{name}] retrieval missed an item with an IDENTICAL "
                      f"topic -- this is broken for any kind")
        if kind == "graded":
            self.assertIn(
                "high", got,
                f"[{name}] declares topic_kind='graded' (Jaccard retrieval, sim "
                f"continuous) but the retrieval the runner uses -- "
                f"core.CarrierStore.retrieve -- did not return an item at "
                f"sim={s_hi}. sim is still {{0,1}}, so epsilon has no surface and "
                f"any epsilon<1 attack reports a FAKE harm=0. Declare 'exact' "
                f"until retrieval.retrieved() is wired in with a theta fixed "
                f"from data.")
            self.assertNotIn(
                "low", got,
                f"[{name}] declares 'graded' but retrieval does not SEPARATE "
                f"sim={s_hi} from sim={s_lo}: a threshold that admits everything "
                f"is not a graded retrieval either")
        else:
            self.assertEqual(
                got, {"equal"},
                f"[{name}] declares topic_kind='exact' (sim in {{0,1}}) but "
                f"retrieval returned partially-matching items "
                f"{sorted(got - {'equal'})} at sim {s_hi} / {s_lo}. The "
                f"declaration is now understating the retrieval, which REFUSES "
                f"attacks that would in fact work.")

    def test_D2b_the_topic_kind_check_goes_red_on_a_false_graded_declaration(self):
        """D2 must be able to FAIL for the reason its name claims, and after
        swebench was corrected to "exact" no dataset in REGISTRY declares
        "graded" any more -- so D2's graded branch would never execute again and
        could rot green.  This drives the same check over two stand-in datasets
        that differ ONLY in the declaration, with identical token-set topics: the
        one declaring "exact" must pass and the one declaring "graded" must fail,
        because core.CarrierStore.retrieve is still equality.

        Thesis claim (vi): "phep kiem phai do duoc CAI NO NOI, khong phai kieu du lieu".
        """
        from core import Task, Workflow

        class _Stub:
            def __init__(self, kind):
                self.name, self._kind = f"stub-{kind}", kind

            def scope(self):
                return datasets.DatasetScope(
                    repos=frozenset({"stub/stub"}), topic_kind=self._kind,
                    has_hidden_tests=False, is_mock=True, instance_pool="stub")

            def workflows(self, n, H, seed):
                for i in range(n):
                    yield Workflow(
                        wf_id=f"stub-{i}", repo="stub/stub",
                        tasks=[Task(task_id=f"stub-{i}-{t}", repo="stub/stub",
                                    base_commit="0" * 7,
                                    topic=frozenset({"pkg", "sub", f"mod{t}"}),
                                    problem="")
                               for t in range(H)])

        self._assert_topic_kind_truthful("stub-exact", _Stub("exact"))
        with self.assertRaises(AssertionError) as ctx:
            self._assert_topic_kind_truthful("stub-graded", _Stub("graded"))
        self.assertIn("FAKE harm=0", str(ctx.exception))
    def test_D4_the_results_header_says_what_scored_the_harm_column(self):
        """`has_hidden_tests` was declared on DatasetScope, set twice, and read
        NOWHERE.  Harm is (public tests PASS) AND (hidden test FAILS), so on a
        dataset declaring no hidden tests the whole harm column comes from an AST
        proxy -- while the header printed only "is_mock=False", which a reader
        takes as "these are real numbers".  datasets.py's own docstring says a
        scope-violating combination must be REFUSED with a reason rather than
        have a number printed for it; a full harm grid was printed instead.

        Thesis claim (vi): "so that va so proxy khong duoc chung mot bang khong nhan".

        """
        import experiment
        for name, ds in self._each():
            sc = ds.scope()
            with self.subTest(dataset=name):
                head = "\n".join(experiment.scope_header(sc))
                self.assertIn(f"topic_kind={sc.topic_kind}", head)
                self.assertIn(f"has_hidden_tests={sc.has_hidden_tests}", head)
                marker = experiment.harm_scored_by(sc)
                if sc.has_hidden_tests:
                    self.assertEqual(marker, "HIDDEN TESTS")
                else:
                    self.assertIn("PROXY", marker)
                    self.assertIn("PROXY-SCORED", head,
                                  f"[{name}] declares has_hidden_tests=False but "
                                  f"the run header does not warn that the harm "
                                  f"column is proxy-scored")

    def test_D3_workflow_count_matches_the_request(self):
        """Thesis claim (vi): "so workflow dung nhu yeu cau"."""
        for name, ds in self._each():
            with self.subTest(dataset=name):
                self.assertEqual(len(list(ds.workflows(5, 4, seed=1))), 5)


# ============================================================= AgentPipeline ==

class AgentConformance(unittest.TestCase):

    def _each(self):
        self.assertTrue(agents.REGISTRY, "agent REGISTRY is empty")
        yield from agents.REGISTRY.items()

    def test_A1_deterministic_in_the_seed(self):
        """Thesis claim (vi): "tat dinh theo seed"."""
        for name, ag in self._each():
            with self.subTest(agent=name):
                def run():
                    st = CarrierStore()
                    ds = datasets.REGISTRY["mock"]
                    wf = next(iter(ds.workflows(1, 6, seed=5)))
                    return [ag.run_task(t, task, st, seed=2, marker="raw_write").solved
                            for t, task in enumerate(wf.tasks)]
                self.assertEqual(run(), run(), f"[{name}] is not deterministic")

    def test_A2_carriers_written_is_declared_truthfully(self):
        """Whatever carriers it declares it writes to, it MUST actually write to.

        A permanently empty carrier => injecting there gives n_c=1 every time =>
        'hiding in the crowd' cannot be measured and RQ2 is left with one axis.

        Thesis claim (vi): "nap trong dam dong" (RQ2).
        """
        ds = datasets.REGISTRY["mock"]
        for name, ag in self._each():
            declared = ag.scope().carriers_written
            observed = set()
            for i, wf in enumerate(ds.workflows(6, 8, seed=9)):
                st = CarrierStore()
                for t, task in enumerate(wf.tasks):
                    ag.run_task(t, task, st, seed=i, marker="raw_write")
                observed |= {c for c, v in st.items.items() if v}
            with self.subTest(agent=name):
                missing = set(declared) - observed
                self.assertFalse(missing,
                                 f"[{name}] declares it writes {sorted(missing)} but NEVER does")

    def test_A3_does_not_spend_budget(self):
        """Thesis claim (vi): "chi DefensePipeline duoc tieu ngan sach"."""
        for name, ag in self._each():
            with self.subTest(agent=name):
                used = identifiers(type(ag))
                for forbidden in ("charge", "budget", "spent"):
                    self.assertNotIn(forbidden, used,
                                     f"[{name}] touches the budget: {forbidden!r}")


# =========================================================== DefensePipeline ==

class DefenseConformance(unittest.TestCase):

    CARRIERS = ("memory", "skill", "queue", "branch")

    def _sig(self, p, n):
        return {c: P.CarrierSignal(p=p, n=n) for c in self.CARRIERS}

    def _sequence(self, name, signals, rng_seed=0, budget=17.95):
        pol = P.make_policy(name, budget, rng_seed, "mid")
        out = []
        for t in range(8):
            a = pol.choose(t, ["memory"], signals)
            if a is not None:
                pol.charge(P.cost_of(a))
            out.append(a)
        return out

    def test_F1_no_policy_exceeds_its_budget(self):
        """Thesis claim (vi): "moi chinh sach chay tren CUNG ngan sach B"."""
        for name in P.REGISTRY:
            with self.subTest(policy=name):
                pol = P.make_policy(name, 2.0, 1, "mid")
                for t in range(20):
                    a = pol.choose(t, ["memory"], self._sig(0.3, 5))
                    if a is not None:
                        pol.charge(P.cost_of(a))
                self.assertLessEqual(pol.spent, 2.0 + 1e-9,
                                     f"[{name}] spent {pol.spent}, over B=2.0")

    def test_F2_scope_actions_are_declared_truthfully(self):
        """Thesis claim (vi): "khai pham vi phai cuong che duoc"."""
        for name, cls in P.REGISTRY.items():
            pol = P.make_policy(name, 17.95, 1, "mid")
            declared = set(pol.scope().actions)
            with self.subTest(policy=name):
                observed = {a for a in self._sequence(name, self._sig(0.4, 5)) if a is not None}
                self.assertTrue(observed <= declared,
                                f"[{name}] takes UNDECLARED actions: {sorted(observed - declared)}")

    def test_F3_reads_scores_is_declared_truthfully(self):
        """Declaring that it reads scores => a score DIFFERENCE between carriers
        must change behaviour.

        The question must be asked with a difference, NOT with an absolute level:
        under a uniform belief, Sentinel's roulette weight is

            (belief/kappa_c) / SUM_j(belief/kappa_j) = (1/kappa_c) / SUM_j(1/kappa_j)

        -- the belief CANCELS.  That is the CORRECT behaviour; a score should only
        act through the difference BETWEEN carriers.  Asking with an absolute level
        asks the wrong question.

        The real invariant: Sentinel declared that it used its belief while the
        ablation gave EXACTLY 0.0000 at every Delta -- C4 "blind Sentinel" was
        identical to Sentinel.

        Thesis claim (vi): "khai 'doc diem' ma diem khong doi duoc hanh vi la DO".
        """
        cool = {c: P.CarrierSignal(p=0.05, n=5) for c in self.CARRIERS}
        hot = dict(cool, branch=P.CarrierSignal(p=0.95, n=5))
        for name in P.REGISTRY:
            pol = P.make_policy(name, 17.95, 1, "mid")
            if not pol.scope().reads_scores:
                continue
            with self.subTest(policy=name):
                self.assertNotEqual(
                    self._sequence(name, cool), self._sequence(name, hot),
                    f"[{name}] declares reads_scores=True but one CLEARLY HOT carrier "
                    f"(0.95 against 0.05) cannot change the action sequence -- the score "
                    f"takes no part in the decision.")

    def test_F4_randomized_is_declared_truthfully(self):
        """Declaring randomisation => changing rng_seed MUST change the action sequence.

        `rng_seed` used to be always 0, making Sentinel a DETERMINISTIC schedule
        repeated across every workflow -- while randomisation is this thesis's
        central claim.

        Thesis claim (vi): "ngau nhien hoa la don bay manh nhat".
        """
        for name in P.REGISTRY:
            pol = P.make_policy(name, 17.95, 1, "mid")
            if not pol.scope().randomized:
                continue
            with self.subTest(policy=name):
                sequences = {tuple(self._sequence(name, self._sig(0.4, 5), rng_seed=s))
                             for s in range(6)}
                self.assertGreater(
                    len(sequences), 1,
                    f"[{name}] declares randomized=True but 6 rng_seeds give the SAME sequence.")


if __name__ == "__main__":
    unittest.main()
