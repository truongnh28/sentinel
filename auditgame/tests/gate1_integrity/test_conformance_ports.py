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
from core import CarrierStore, seed_of


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

    def test_D2_topic_kind_is_declared_truthfully(self):
        """`topic_kind` decides which AttackPipeline may be used -- declare it
        wrongly and the framework will happily run a meaningless combination.

        Thesis claim (vi): "cong nao khong khai pham vi thi khong phai cong".
        """
        for name, ds in self._each():
            kind = ds.scope().topic_kind
            with self.subTest(dataset=name, topic_kind=kind):
                self.assertIn(kind, ("exact", "graded"))
                topic = next(iter(ds.workflows(1, 4, seed=3))).tasks[0].topic
                if kind == "exact":
                    self.assertIsInstance(topic, str,
                                          f"[{name}] declares exact but topic is not a string")
                else:
                    self.assertIsInstance(topic, frozenset,
                                          f"[{name}] declares graded but topic is not a token set")

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
        import inspect
        for name, ag in self._each():
            with self.subTest(agent=name):
                src = inspect.getsource(type(ag))
                for forbidden in ("charge", "budget", "spent"):
                    self.assertNotIn(forbidden, src,
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
