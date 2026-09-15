"""
GATE 1 -- INTEGRITY: "are the numbers real?"
Red here => EVERY number at gates 2 and 3 is WORTHLESS.

A test's NAME states the claim it defends, not the function it calls.  When it
goes red, the failure line IS the sentence in the thesis that just lost its
support; the Vietnamese wording of that sentence lives in the docstring under
`Thesis claim (vi):`.
"""
from __future__ import annotations
import os, subprocess, sys, unittest

from core import CarrierStore
import build, runner, policies as P
from tests.fixtures import profile_A, profile_B, ScriptedDetector, ScriptedAgent


class Gate1Integrity(unittest.TestCase):

    # ---------------------------------------------------------------- I1 ----
    def test_rerunning_the_same_seed_gives_an_identical_trace(self):
        """Thesis claim (vi): "ket qua tai lap duoc" -- i.e. the entire thesis."""
        code = ("import random, build;"
                "print(build.make_workflow('wf-000','django',8,random.Random(2026))"
                ".tasks[0].base_commit)")
        got = []
        for seed in ("0", "1"):                      # different PYTHONHASHSEED values
            env = dict(os.environ, PYTHONHASHSEED=seed)
            got.append(subprocess.run([sys.executable, "-c", code], env=env,
                                      capture_output=True, text=True,
                                      cwd=os.getcwd()).stdout.strip())
        self.assertEqual(got[0], got[1],
                         f"base_commit changes with PYTHONHASHSEED ({got[0]} vs {got[1]}): "
                         "build.py uses hash() for base_commit. It must use seed_of().")

    # ---------------------------------------------------------------- I2 ----
    def test_no_one_but_the_oracle_reads_poisoned(self):
        """Thesis claim (vi): "chinh sach khong biet dau la mam doc"."""
        pr, det, ag = profile_A(), ScriptedDetector(), ScriptedAgent()
        with pr.kappa_applied():
            runner.run_once(pr.workflows[0], pr.specs[0],
                            P.REGISTRY["B3 audit-on-insertion"]("x", pr.budget),
                            det, ag, seed=1)
        self.assertEqual(det.legacy_calls, 0,
                         f"the runner passed ground truth into fires() {det.legacy_calls} times. "
                         "N1 (SS2.2) must remove the second parameter of fires().")

    # ---------------------------------------------------------------- I3 ----
    def test_payload_is_not_retrieved_before_sigma(self):
        """Thesis claim (vi): "nam im dung Delta task"."""
        pr = profile_A()
        wf, ps = pr.workflows[0], pr.specs[0]
        store = CarrierStore()
        build.inject(store, wf, ps)
        ag = ScriptedAgent()
        for t, task in enumerate(wf.tasks):
            o = ag.run_task(t, task, store, seed=1, marker=ps.marker)
            if t < ps.sigma:
                self.assertFalse([i for i in o.retrieved if i.poisoned],
                                 f"payload retrieved at t={t} < sigma={ps.sigma} "
                                 f"=> the real Delta is below the declared one ({ps.delta})")

    # ---------------------------------------------------------------- I4 ----
    def test_no_policy_exceeds_the_budget(self):
        """Thesis claim (vi): "moi he thong chay tren cung ngan sach B"."""
        for pr in (profile_A(), profile_B()):
            with pr.kappa_applied():
                for name, cls in P.REGISTRY.items():
                    pol = cls("x", pr.budget)
                    r = runner.run_once(pr.workflows[0], pr.specs[0], pol,
                                        ScriptedDetector(), ScriptedAgent(), seed=1)
                    self.assertLessEqual(
                        r.spent, pr.budget + 1e-9,
                        f"[profile {pr.name}] {name} spent {r.spent} > B={pr.budget}. "
                        "The runner must ENFORCE this, not delegate it to Policy.can().")

    # --------------------------------------------------------------- I12 ----
    def test_an_unbuildable_attack_does_not_count_as_harm_zero(self):
        """The unbuildable rate RISES with Delta (measured: 0% at Delta<=2, 5% at
        Delta=4), so fake zeros are pumped into exactly the large end of the Delta
        axis => the noise CORRELATES with the independent variable.

        Thesis claim (vi): "do loi tang theo Delta" (RQ1) -- without fake zeros.
        """
        from tests.fixtures import _wf
        from core import PoisonSpec
        wf = _wf("INF", ["a", "a", "a", "a"])       # every topic identical => Delta=1 is infeasible
        import random
        self.assertIsNone(build.plan_poison(wf, "memory", 1, random.Random(0)),
                          "bad fixture: this was supposed to be infeasible")
        pr = profile_A()
        with pr.kappa_applied():
            cell = runner.worst_case(
                "B1 audit-at-commit", [wf], (1,), ("memory",),
                ScriptedDetector(), ScriptedAgent(), pr.budget, (1,), "weak")
        self.assertEqual(
            cell.n_feasible, 0,
            f"an INFEASIBLE workflow is still counted in the denominator: n_feasible="
            f"{cell.n_feasible}/{cell.n_total}.")
        self.assertNotEqual(
            cell.harm, 0.0,
            f"a corpus of entirely INFEASIBLE workflows returns harm={cell.harm} instead "
            "of being dropped from the denominator. 'could not be attacked' is being read "
            "as 'the defense succeeded' -- and that rate RISES with Delta, so it pumps fake "
            "zeros into exactly the large end of the axis RQ1 measures.")
        self.assertTrue(
            cell.harm != cell.harm,          # NaN: nothing to average
            f"a cell with no feasible workflow must return NaN, not {cell.harm}")

    # ---------------------------------------------------------------- I6 ----
    def test_the_survivor_set_is_identical_across_policies(self):
        """The CLEAN phase does not depend on the audit policy -- it only asks "can
        the agent solve this task".  But `paired()` re-ran the clean phase UNDER THE
        POLICY BEING MEASURED, so if solving depends on carrier state then each
        policy drops a DIFFERENT set of instances -- a bias whose results table
        still looks perfectly normal.

        The agent here solves a task ONLY IF the previous task's note is still
        alive.  That is a real causal channel (a wrong quarantine costs the agent
        its context), and it turns the structural defect into something observable:
        B3 audit-on-insertion quarantines a lot and drops instances, B1
        audit-at-commit never touches memory and keeps them.

        Thesis claim (vi): "moi chinh sach so sanh tren CUNG tap instance".
        """
        from dataclasses import dataclass
        from core import CarrierStore, Task
        from agent import Outcome

        @dataclass
        class ContextSensitiveAgent(ScriptedAgent):
            """Solves a task only if the previous task's note is still alive."""
            def run_task(self, t, task, store, seed, marker):
                prior_alive = any(it.created_at == t - 1 for it in store.live("memory"))
                o = ScriptedAgent.run_task(self, t, task, store, seed, marker)
                return Outcome(retrieved=o.retrieved, writes=o.writes,
                               patch_has_marker=o.patch_has_marker,
                               solved=(t == 0 or prior_alive))

        pr = profile_A()
        det = ScriptedDetector(poisoned_score=2.0, clean_score=2.0, tau=1.0)  # fires on EVERY item
        ag = ContextSensitiveAgent()

        survivors = {}
        with pr.kappa_applied():
            for name in ("B1 audit-at-commit", "B3 audit-on-insertion"):
                survivors[name] = [
                    runner.paired(wf, ps, name, det, ag, 1, pr.budget, "weak") is not None
                    for wf, ps in zip(pr.workflows, pr.specs)]

        a, b = survivors["B1 audit-at-commit"], survivors["B3 audit-on-insertion"]
        self.assertEqual(
            a, b,
            f"the survivor set DIFFERS between two policies: B1={a} B3={b}. "
            f"The clean phase is running UNDER the policy being measured, so each "
            f"policy compares on a different instance set. Needs N4: survivors() "
            f"computed ONCE then frozen, shared by every policy.")

    # --------------------------------------------------------------- I13 ----
    def test_random_sequences_differ_between_workflows(self):
        """Randomisation is Sentinel's STRONGEST lever according to the ablation
        (RQ3).  Identical sequences => we are measuring one dice roll repeated N
        times.

        Thesis claim (vi): "40 mau", not "1 mau lap 40 lan".
        """
        self.assertTrue(hasattr(P, "make_policy"),
                        "policies.make_policy() does not exist yet (N2). runner.worst_case "
                        "uses `lambda n, b: cls(n, b)`, so rng_seed falls back to 0 for EVERY "
                        "workflow => B2 and Sentinel share one random sequence.")


if __name__ == "__main__":
    unittest.main()
