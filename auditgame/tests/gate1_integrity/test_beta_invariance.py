"""Beta cannot change which carrier a policy picks, and the reason is algebraic.

Spec: docs/design/plans/2026-09-23-tham-so-dot-2.md W3; costs.BETA_RULE_A/B.

WHY THIS TEST EXISTS.  tools/measure_beta.py read the benign churn of ten real
SWE-bench repositories under two defensible mapping rules and they disagree by
10x on skill (0.058 vs 0.607).  By the pre-declared criterion that moved beta
from M1 to M2, so the paper owes a sweep rather than a value -- and a sweep that
comes back flat is only worth quoting if the flatness is a property of the model
rather than of the twenty workflows it happened to run on.

It is a property of the model.  belief.WindowBelief.update multiplies ONLY the
null hypothesis by quiet**(1-beta); every window hypothesis is untouched.  So
beta moves the normaliser z and nothing else, and carrier_mass sums windows
alone -- every carrier is scaled by the same 1/z and every RATIO between them is
exactly independent of beta.  A policy comparing carriers therefore cannot see
beta at all.

What beta does survive in is p_attack(), the null's own mass, which is the term
the commit channel is weighted by.  That is measured here too, so the claim is
"beta is inert for carrier choice, and weak for the commit channel", not the
stronger thing the flat sweep on its own might be read as.
"""
import unittest

import belief
import policies as P
from core import CARRIERS

BETAS = (0.013, 0.058, 0.25, 0.314, 0.607, 1.0)


def _belief_after_alarms(beta, loud="memory", steps=3):
    wb = belief.WindowBelief(list(CARRIERS), H=8, deltas=(0, 1, 2, 4), beta=beta)
    sig = {c: P.CarrierSignal(p=(0.9 if c == loud else 0.1), n=5)
           for c in CARRIERS}
    for t in range(steps):
        wb.update(t, sig)
    return wb


class BetaIsInertForCarrierChoice(unittest.TestCase):

    def test_every_ratio_between_carriers_is_independent_of_beta(self):
        """The claim the sweep rests on, checked exactly rather than by eye."""
        ref = None
        for b in BETAS:
            m = _belief_after_alarms(b).carrier_mass(2)
            total = sum(m.values())
            shares = {c: m[c] / total for c in CARRIERS}
            if ref is None:
                ref = shares
                continue
            for c in CARRIERS:
                self.assertAlmostEqual(
                    shares[c], ref[c], places=12,
                    msg=f"carrier {c} share moved with beta={b}: "
                        f"{shares[c]} vs {ref[c]}. beta is supposed to touch "
                        f"only the NULL hypothesis, so it must cancel in every "
                        f"carrier-vs-carrier comparison.")

    def test_beta_does_move_the_null_so_the_sweep_is_not_measuring_nothing(self):
        """The control on the control.

        If p_attack were also flat, the sweep would be consistent with beta
        never being read at all -- which is exactly the defect found elsewhere
        in this codebase (experiment.py never called costs.install()).  It is
        read; it simply cancels where policies compare carriers.
        """
        lo = _belief_after_alarms(min(BETAS)).p_attack()
        hi = _belief_after_alarms(max(BETAS)).p_attack()
        self.assertGreater(lo - hi, 1e-6,
                           "p_attack did not move across the whole beta range, "
                           "so nothing proves beta is consumed at all")

    def test_the_policies_hardcode_a_beta_the_measurement_does_not_supply(self):
        """Recorded, not enforced as correct: the two belief-carrying policies
        pin BETA_DRIFT = 0.25 while costs.BETA_DEFAULT is the measured 0.314.

        Harmless only BECAUSE of the invariance above.  The test exists so that
        if someone later makes beta matter, this disagreement is already named
        rather than discovered again.
        """
        import costs
        for cls in (P.SentinelWindow, P.SSGBelief):
            self.assertNotEqual(
                cls.BETA_DRIFT, costs.BETA_DEFAULT,
                f"{cls.__name__}.BETA_DRIFT now equals costs.BETA_DEFAULT -- "
                f"if that was deliberate, delete this test; it is here to "
                f"record that the two were NOT wired together.")


if __name__ == "__main__":
    unittest.main()
