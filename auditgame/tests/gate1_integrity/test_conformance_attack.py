"""
GATE 1 -- CONFORMANCE CONTRACT for AttackPipeline (K1-K6).
Spec: pipelines/SPEC-Framework-Benchmark.md Part 2.1 and Part 4.

This suite runs against EVERY pipeline in `attacks.REGISTRY`.  A new pipeline does
not enter the results table until it passes all of them.

K5 and K6 came from REAL bugs in this repository, not from theory:
  K5 -- epsilon was declared in PoisonSpec, written into the manifest, and READ
        NOWHERE AT ALL: the payload at eps=0.05 and 0.95 was byte-identical.
  K6 -- a global counter made injection shuffle the identity of EVERY clean item
        after it: measured, 0/9 clean notes kept their id across the two arms of
        the paired design.
"""
from __future__ import annotations
import random
import subprocess
import sys
import unittest

import attacks
import build
from core import CarrierStore, seed_of
from tests.fixtures import identifiers




def _wfs(n=12, H=8):
    return [build.make_workflow(f"wf-{i:03d}", "django", H, random.Random(seed_of("K", i)))
            for i in range(n)]


class AttackPipelineConformance(unittest.TestCase):
    """Replays the whole contract for each registered pipeline."""

    def _each(self):
        self.assertTrue(attacks.REGISTRY, "REGISTRY is empty -- nothing to check")
        for name, pipe in attacks.REGISTRY.items():
            yield name, pipe

    # ------------------------------------------------------------------ K1 --
    def test_K1_same_seed_yields_the_same_result(self):
        """Same seed => IDENTICAL PoisonSpec and payload, even across PYTHONHASHSEED.

        `hash()` in build.py and `itertools.count` in core.py each broke this.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        for name, pipe in self._each():
            with self.subTest(pipeline=name):
                wf = _wfs(1)[0]
                out = []
                for _ in range(3):
                    ps = pipe.plan(wf, "memory", 2, random.Random(7))
                    if ps is None:
                        out.append(None); continue
                    out.append((ps.carrier, ps.iota, ps.sigma, ps.epsilon,
                                pipe.payload(wf, ps).item_id))
                self.assertEqual(len(set(map(repr, out))), 1,
                                 f"[{name}] not deterministic within one process: {out}")

    def test_K1b_deterministic_across_PYTHONHASHSEED(self):
        """Reproducible across processes with different PYTHONHASHSEED values.

        Thesis claim (vi): "ket qua tai lap duoc".
        """
        code = (
            "import random, build, attacks\n"
            "from core import seed_of\n"
            "wf = build.make_workflow('wf-000','django',8,random.Random(seed_of('K',0)))\n"
            "for n,p in sorted(attacks.REGISTRY.items()):\n"
            "    ps = p.plan(wf,'memory',2,random.Random(7))\n"
            "    print(n, ps and (ps.iota, ps.sigma, round(ps.epsilon,6)),\n"
            "          ps and p.payload(wf, ps).item_id)\n")
        outs = set()
        for h in ("0", "1", "424242"):
            r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                               text=True, env={"PYTHONHASHSEED": h, "PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 0, f"run failed at HASHSEED={h}: {r.stderr[-400:]}")
            outs.add(r.stdout)
        self.assertEqual(len(outs), 1,
                         f"results change with PYTHONHASHSEED:\n{chr(10).join(sorted(outs))}")

    # ------------------------------------------------------------------ K2 --
    def test_K2_cannot_read_ground_truth(self):
        """An attack must not receive a `CarrierStore` -- it could read other items'
        `.poisoned`.

        Checked by SIGNATURE, not by a tripwire: a structural prohibition is
        stronger than a disciplinary one.

        Thesis claim (vi): "khong ai ngoai oracle duoc doc nhan that".
        """
        import inspect
        for name, pipe in self._each():
            with self.subTest(pipeline=name):
                for meth in ("plan", "payload"):
                    params = inspect.signature(getattr(pipe, meth)).parameters
                    bad = [p for p in params if "store" in p.lower()]
                    self.assertFalse(bad, f"[{name}].{meth} takes {bad} -- can read ground truth")

    # ------------------------------------------------------------------ K3 --
    def test_K3_does_not_spend_budget(self):
        """Only the DefensePipeline may spend budget.  If an attack spends it
        covertly, sum(kappa) <= B means nothing.

        Thesis claim (vi): "moi chinh sach chay tren CUNG ngan sach B".
        """
        for name, pipe in self._each():
            with self.subTest(pipeline=name):
                used = identifiers(type(pipe))
                for forbidden in ("charge", "budget", "spent"):
                    self.assertNotIn(forbidden, used,
                                     f"[{name}] touches the budget: {forbidden!r}")

    # ------------------------------------------------------------------ K4 --
    def test_K4_scope_declares_carriers_truthfully(self):
        """Whatever `carriers` it declares, it must be able to target ALL of them.

        This is the invariant that stops D5 recurring: a silent
        `carriers=("memory","skill")` restriction flipped the sign of Sentinel vs B1
        (+51% -> -18% at Delta=0).

        Thesis claim (vi): "khai pham vi phai cuong che duoc".
        """
        wfs = _wfs(20)
        for name, pipe in self._each():
            sc = pipe.scope()
            for k in sorted(sc.carriers):
                with self.subTest(pipeline=name, carrier=k):
                    ok = any(pipe.plan(wf, k, 2, random.Random(seed_of(k, i))) is not None
                             for i, wf in enumerate(wfs))
                    self.assertTrue(ok, f"[{name}] declares it can target {k!r} but plan() is always None")

    def test_K4b_scope_declares_delta_range_truthfully(self):
        """Thesis claim (vi): "khai pham vi phai cuong che duoc"."""
        wfs = _wfs(20)
        for name, pipe in self._each():
            lo, hi = pipe.scope().delta_range
            for d in (lo, hi):
                with self.subTest(pipeline=name, delta=d):
                    ok = any(pipe.plan(wf, "memory", d, random.Random(seed_of(d, i))) is not None
                             for i, wf in enumerate(wfs))
                    self.assertTrue(ok, f"[{name}] declares delta_range={lo}..{hi} but d={d} is always None")

    # ------------------------------------------------------------------ K5 --
    def test_K5_epsilon_declared_effective_must_be_effective(self):
        """`epsilon_effective=True` => changing epsilon MUST change something measurable.

        The original bug: the payload at eps=0.05 and eps=0.95 was byte-identical,
        same item_id.  A quarter of the attack space (k, iota, sigma, epsilon) was
        a no-op.

        Thesis claim (vi): "epsilon la ngan sach phan biet", not a decorative parameter.
        """
        wf = _wfs(1)[0]
        for name, pipe in self._each():
            if not pipe.scope().epsilon_effective:
                continue
            with self.subTest(pipeline=name):
                seen = set()
                for eps in (0.1, 0.4, 0.7, 1.0):
                    ps = pipe.plan(wf, "memory", 2, random.Random(7), epsilon=eps)
                    self.assertIsNotNone(ps, f"[{name}] plan() is None at eps={eps}")
                    it = pipe.payload(wf, ps)
                    seen.add((it.content, tuple(sorted(it.topic))
                              if not isinstance(it.topic, str) else it.topic,
                              it.provenance))
                self.assertGreater(
                    len(seen), 1,
                    f"[{name}] declares epsilon_effective=True but the payload is UNCHANGED "
                    f"across eps=0.1..1.0 -- epsilon is still a decorative parameter.")

    # ------------------------------------------------------------------ K6 --
    def test_K6_injection_does_not_alter_clean_items_before_sigma(self):
        """The clean/injected pairing is the MEASUREMENT METHOD, not a baseline.

        Before sigma, NO mechanism may make the two arms differ.  Note this is the
        strict pre-sigma invariant (equality, no tolerance): after sigma, branch
        commits legitimately inherit the poison, so a whole-run comparison would go
        red for a causally correct reason.

        Thesis claim (vi): "tiem khong doi diem cua item sach".
        """
        import agent, detector
        det = detector.Detector.from_setting("mid")
        for name, pipe in self._each():
            with self.subTest(pipeline=name):
                wf = _wfs(1)[0]
                ps = pipe.plan(wf, "memory", 2, random.Random(7))
                if ps is None:
                    continue
                ag = agent.MockAgent()

                def arm(do_inject):
                    st = CarrierStore()
                    for t, task in enumerate(wf.tasks):
                        if do_inject and t == ps.iota:
                            st.write(pipe.payload(wf, ps))
                        ag.run_task(t, task, st, seed=1, marker=ps.marker)
                    return {i.item_id: round(det.score(i, 7, 1), 9)
                            for i in st.live()
                            if not i.poisoned and i.created_at < ps.sigma}

                a, b = arm(False), arm(True)
                self.assertEqual(
                    set(a), set(b),
                    f"[{name}] injection changes clean item identity before sigma: "
                    f"clean-only={sorted(set(a)-set(b))[:3]} injected-only={sorted(set(b)-set(a))[:3]}")
                drift = {k for k in set(a) & set(b) if a[k] != b[k]}
                self.assertFalse(drift,
                                 f"[{name}] injection changes the SCORE of clean items: {sorted(drift)[:3]}")


class WhichAttacksADatasetAdmits(unittest.TestCase):
    """`attacks.usable_with` is the gate between the dataset port and the attack
    port, and it had NO caller and NO test -- so its scope was never checked
    against the claim it makes.
    """

    def test_a_graded_dataset_unblocks_only_what_was_blocked_on_retrieval_kind(self):
        """The old version did `ok.update(PENDING)` the moment a dataset declared
        "graded", which re-admitted EVERY pending pipeline. `legacy` and
        `verbosity` are pending because no epsilon reaches AUC_upper <= 0.56 on
        F_match -- a property of the PAYLOAD, which no retrieval kind can change.
        Declaring a dataset graded would have put two attacks gate 2 already ruled
        out back into the attacker class, and worst_case takes a MAX over that
        class, so the harm table would have risen for a reason with no evidence
        behind it.

        Thesis claim (vi): "cong nao khong khai pham vi thi khong phai cong".
        """
        graded = attacks.usable_with("graded")
        for name, (_p, _reason, blockers) in attacks.PENDING.items():
            with self.subTest(pending=name, blockers=sorted(blockers)):
                if blockers <= {attacks.BLOCKER_RETRIEVAL_KIND}:
                    self.assertIn(name, graded,
                                  f"[{name}] is blocked only on retrieval kind, so "
                                  f"a graded dataset must admit it")
                else:
                    self.assertNotIn(
                        name, graded,
                        f"[{name}] is pending on {sorted(blockers)}, which a "
                        f"graded dataset does NOT lift, yet usable_with('graded') "
                        f"admitted it")

    def test_an_exact_dataset_admits_no_attack_that_needs_graded_retrieval(self):
        """An attack declaring requires_graded_retrieval=True on an exact dataset
        is the MEANINGLESS combination datasets.py's docstring says must be
        refused with a reason rather than scored: its payload topic is a strict
        subset of sigma's, which `==` retrieval never returns, so every epsilon<1
        cell would report harm 0 for a reason that has nothing to do with the
        defense.

        Thesis claim (vi): "o ngoai pham vi thi ghi LY DO, khong ghi harm=0".
        """
        exact = attacks.usable_with("exact")
        for name, p in {**attacks.REGISTRY,
                        **{n: q for n, (q, _r, _b) in attacks.PENDING.items()}}.items():
            with self.subTest(attack=name):
                if p.scope().requires_graded_retrieval:
                    self.assertNotIn(name, exact,
                                     f"[{name}] needs graded retrieval but an "
                                     f"exact dataset admitted it")
        self.assertTrue(exact, "an exact dataset admits no attack at all")

    def test_every_registered_attack_is_admitted_by_the_kind_it_declares_for(self):
        """usable_with filters REGISTRY on the same scope check it applies to
        PENDING -- a pipeline does not become admissible merely by being
        registered.

        Thesis claim (vi): "pham vi phai may kiem duoc, khong phai loi hua".
        """
        for kind in ("exact", "graded"):
            ok = attacks.usable_with(kind)
            for name, p in attacks.REGISTRY.items():
                with self.subTest(topic_kind=kind, attack=name):
                    needs = p.scope().requires_graded_retrieval
                    self.assertEqual(name in ok, (kind == "graded") or not needs)

    def test_an_unknown_topic_kind_is_refused_rather_than_guessed(self):
        """Falling through to "not graded" would silently refuse a whole attacker
        class for a dataset whose declaration was merely misspelt.

        Thesis claim (vi): "khong doan; khong biet thi bao loi".
        """
        with self.assertRaises(ValueError):
            attacks.usable_with("jaccard")


if __name__ == "__main__":
    unittest.main()
