"""
GATE 2 -- VALIDITY for the B-lite detector model: "what is that number about?"

Red here => `m`, `tau` or `d'_eff` is a real number about something OTHER than the
quantity the pre-registration defines.

The binding text is `261-Master-Proposal-Analysis/TIEN-DANG-KY-m-x-va-F-detect-v2.md`,
frozen 18/09/2026 before the first line of this code.  Four of its choices each
REPLACED an earlier one that was wrong, and each replacement has a recorded reason;
these tests exist so that reverting any of them goes red rather than quiet:

    m(x) = v1(x)           v1 ALONE.  v1 has a weight of 1 and there is no other
                           term, because v3 is identically 0 on both classes and
                           giving a dead component 1/3 is a CHOICE wearing the
                           clothes of a non-informative prior.
    v2 outside m           provenance is a VALIDITY CONDITION.  Declaring true
                           provenance is a dominant strategy for the attacker, so
                           v2 does not measure audit power -- it defines the
                           attack family.
    v3 dropped             with its reason, not silently.
    tau calibrated         phi is held fixed by CALIBRATING tau to the benign
                           distribution, NOT by forcing m(benign) = 0.  The
                           consequence -- tau becomes a FUNCTION of d' -- is the
                           thing that makes this sweep incomparable with the
                           existing one, so it is pinned here.
"""
from __future__ import annotations
import inspect
import unittest
from statistics import NormalDist

import agent
import detector
import fdetect
from core import CarrierStore, Item
from tests.fixtures import profile_A


_N = NormalDist()


class ScriptedJudge:
    """The INJECTED judge, offline.  A fixed table keyed by CONTENT, plus a call
    log -- so a test can show the table runs it once per unique item and that no
    path invents a value for an item it was never given."""
    name = "scripted"

    def __init__(self, table, default=None):
        self.table = dict(table)
        self.default = default
        self.asked = []

    def pin(self) -> fdetect.JudgePin:
        return fdetect.JudgePin(model="scripted", version="test-0",
                                temperature=0.0, seed=None,
                                prompt_sha=fdetect.prompt_sha())

    def violation(self, item) -> float:
        self.asked.append(item.content)
        if item.content in self.table:
            return self.table[item.content]
        if self.default is None:
            raise KeyError(item.content)
        return self.default


def benign_items() -> list:
    """Every item a REAL benign workflow writes, drift included.

    Not hand-built Items: the claim under test is about what the agent actually
    produces, and a hand-built stand-in would only test the test.
    """
    pr = profile_A()
    store = CarrierStore()
    ag = agent.MockAgent(drift_rate=0.9)
    for t, task in enumerate(pr.workflows[0].tasks):
        ag.run_task(t, task, store, seed=7, marker="raw_write")
    return [it for it in store.live() if not it.poisoned]


class MIsV1Alone(unittest.TestCase):
    """The pre-registration's section 2, and the one it replaced."""

    def test_m_is_v1_and_nothing_else(self):
        """`m(x) = v1(x)`.  Not a weighted sum, and not v1 blended with anything.

        Thesis claim (vi): "m(x) = v1(x)" -- thanh phan duy nhat con tin hieu.
        """
        j = ScriptedJudge({"c": 0.37})
        it = Item(carrier="memory", topic="orm", content="c", created_at=0,
                  provenance="agent/notes", poisoned=False)
        self.assertEqual(fdetect.m(it, j), fdetect.v1(it, j))
        self.assertEqual(fdetect.m(it, j), 0.37)

    def test_m_does_not_move_when_provenance_moves(self):
        """Two items, SAME content, provenance legitimate in one and a lie in the
        other.  `m` must be identical and `v2` must differ -- that is exactly what
        "v2 is outside m" means, stated as a number rather than as prose."""
        j = ScriptedJudge({"same text": 0.42})
        honest = Item(carrier="memory", topic="orm", content="same text",
                      created_at=0, provenance="agent/notes", poisoned=False)
        lying = Item(carrier="memory", topic="orm", content="same text",
                     created_at=0, provenance="repo/docs/conventions.md",
                     poisoned=True)
        self.assertEqual(fdetect.m(honest, j), fdetect.m(lying, j))
        self.assertNotEqual(fdetect.v2(honest), fdetect.v2(lying))

    def test_m_is_not_zero_on_a_benign_item(self):
        """v1 GAVE UP the `m(benign) = 0` constraint of v1 of the pre-registration.

        Nothing in this module may clamp, floor or special-case a benign item back
        to zero: v1 is a judgement, it is never exactly 0, and forcing it to be
        would binarise the very continuous surface the model is built on.
        """
        j = ScriptedJudge({}, default=0.21)
        for it in benign_items()[:20]:
            self.assertEqual(fdetect.m(it, j), 0.21,
                             f"a benign item was pushed off the judge's value: {it.item_id}")

    def test_v3_is_not_implemented_and_the_reason_is_recorded(self):
        """v3 (lineage) is DROPPED.  A dropped component with no recorded reason
        is indistinguishable from a forgotten one."""
        self.assertFalse(hasattr(fdetect, "v3"),
                         "v3 is implemented; the pre-registration drops it")
        self.assertIn("v3", fdetect.__doc__)
        reason = fdetect.V3_DROPPED
        for token in ("derived_from", "_one_event"):
            self.assertIn(token, reason,
                          f"the recorded reason does not name {token}, one of the "
                          "two independently measured causes")


class V2IsExactAndZeroOnBenign(unittest.TestCase):
    """G1 of the pre-registration's section 5 -- an IMPLEMENTATION gate, not a
    scientific one: v2 is an exact check, so 0 on benign is by construction and a
    non-zero there is a bug in this file."""

    def test_v2_is_zero_on_every_item_a_benign_workflow_writes(self):
        items = benign_items()
        self.assertGreater(len(items), 10, "the benign fixture produced nothing")
        for it in items:
            self.assertEqual(fdetect.v2(it), 0.0,
                             f"v2 fired on a benign item: {it.carrier} "
                             f"{it.provenance!r} -- v2 must be 0 on benign BY "
                             "CONSTRUCTION")

    def test_v2_fires_on_a_payload_that_claims_a_repository_file_as_its_origin(self):
        """The registered payload templates claim `repo/docs/conventions.md`, an
        origin the carrier write surface cannot produce."""
        it = Item(carrier="memory", topic="orm", content="x", created_at=0,
                  provenance="repo/docs/conventions.md", poisoned=True)
        self.assertEqual(fdetect.v2(it), 1.0)

    def test_v2_grades_a_channel_lie_below_an_origin_lie(self):
        """An attacker that repairs the ROOT still has to name the channel the
        carrier it sits in actually has.  `agent/skills` inside `memory` is not a
        write this agent can perform, so it is half a violation, not none."""
        channel_lie = Item(carrier="memory", topic="orm", content="x", created_at=0,
                           provenance="agent/skills", poisoned=True)
        origin_lie = Item(carrier="memory", topic="orm", content="x", created_at=0,
                          provenance="repo/docs/conventions.md", poisoned=True)
        self.assertEqual(fdetect.v2(channel_lie), 0.5)
        self.assertGreater(fdetect.v2(origin_lie), fdetect.v2(channel_lie))

    def test_the_channel_table_covers_every_provenance_the_agent_writes(self):
        """The table is the thing that makes "0 on benign" true.  If the agent
        grows a fifth write channel and the table does not, every item on it reads
        as a provenance lie -- so the table is checked against the LIVE agent."""
        seen = {(it.carrier, it.provenance) for it in benign_items()}
        missing = seen - set(fdetect.LEGITIMATE_CHANNELS)
        self.assertEqual(missing, set(),
                         f"the agent writes channels the table does not carry: {missing}")

    def test_v2_does_not_read_the_ground_truth_label(self):
        """`poisoned` is the evaluator's answer key (core.Item).  A validity
        condition that reads it certifies nothing."""
        src = inspect.getsource(fdetect.v2) + inspect.getsource(fdetect.v2_clauses)
        self.assertNotIn("poisoned", src)

    def test_v2_carries_no_lineage_clause(self):
        """v3 is dropped; sneaking lineage into v2 would reinstate it under
        another name.  The only benign item with a non-empty `derived_from` is one
        the agent labelled poisoned, so a lineage clause looks harmless here and
        is exactly the component the pre-registration measured dead."""
        src = inspect.getsource(fdetect.v2) + inspect.getsource(fdetect.v2_clauses)
        self.assertNotIn("derived_from", src)


class TauIsCalibratedAndFollowsDPrime(unittest.TestCase):
    """Section 1 and section 4 of the pre-registration."""

    def test_tau_at_d_prime_zero_is_the_existing_sweeps_fixed_threshold(self):
        """At d' = 0 the two models coincide, so the calibration must reproduce
        z(1 - phi) exactly.  A calibration that does not is not a generalisation of
        the flag model, it is a different model."""
        got = fdetect.tau_of_dprime(0.0, [0.3, 0.5, 0.9], phi=0.12)
        self.assertAlmostEqual(got, _N.inv_cdf(0.88), places=6)
        self.assertAlmostEqual(got, detector.operating_point(0.85, 0.12)[1], places=6)

    def test_tau_is_a_function_of_d_prime_under_b_lite(self):
        """THE CONSEQUENCE THAT HAS TO BE DECLARED.  In the existing sweep tau sits
        still at z(0.88) because the benign mean is exactly 0.  Under B-lite the
        benign mean is d' * mean(m) != 0, so tau MOVES with d' -- and the two
        sweeps are therefore not directly comparable.

        Thesis claim (vi): "tau thanh ham cua d'".
        """
        m_benign = [0.2, 0.3, 0.4, 0.5]
        taus = [fdetect.tau_of_dprime(dp, m_benign, phi=0.12)
                for dp in (0.0, 1.0, 2.0, 3.0)]
        self.assertEqual(taus, sorted(taus))
        self.assertGreater(taus[-1], taus[0] + 0.5)

    def test_tau_stands_still_only_when_m_is_identically_zero(self):
        """The degenerate case the old model assumed, kept as a boundary check."""
        flat = [fdetect.tau_of_dprime(dp, [0.0, 0.0, 0.0], phi=0.12)
                for dp in (0.0, 1.5, 3.0)]
        for t in flat:
            self.assertAlmostEqual(t, _N.inv_cdf(0.88), places=6)

    def test_the_calibration_holds_phi_at_its_declared_value(self):
        """Neyman-Pearson, stated as a round trip: fix the false-alarm rate, then
        read the realised rate back off the SAME set and get the same number."""
        m_benign = [0.05, 0.31, 0.62, 0.9, 0.44]
        for phi in fdetect.PHI_GRID:
            for dp in (0.0, 1.4, 2.8):
                tau = fdetect.tau_of_dprime(dp, m_benign, phi=phi)
                self.assertAlmostEqual(
                    fdetect.phi_realised(tau, dp, m_benign), phi, places=6)

    def test_the_phi_grid_is_the_manuscripts_three_settings(self):
        """0.12 is a constant COPIED from the manuscript and is the last undeclared
        one in this chain.  The sensitivity grid is the three settings themselves,
        read off `detector.SETTINGS` rather than pasted, so the two cannot drift.
        """
        self.assertEqual(fdetect.PHI_HEADLINE, detector.SETTINGS["mid"][1])
        self.assertEqual(set(fdetect.PHI_GRID),
                         {phi for _, phi in detector.SETTINGS.values()})
        self.assertEqual(fdetect.PHI_GRID, (0.06, 0.12, 0.20))

    def test_every_reported_quantity_is_producible_at_every_phi(self):
        table = fdetect.tau_table([0.1, 0.4, 0.8], (0.0, 1.0, 2.0))
        self.assertEqual(sorted({phi for phi, _ in table}), sorted(fdetect.PHI_GRID))
        self.assertEqual(len(table), 3 * 3)

    def test_the_calibration_refuses_an_empty_benign_set(self):
        with self.assertRaises(fdetect.NotMeasured):
            fdetect.tau_of_dprime(1.0, [], phi=0.12)


class CalibrationAndReportAreDisjoint(unittest.TestCase):
    """Section 4 condition 2.  The existing holdout separates ATTACKER from BENIGN;
    it does NOT separate CALIBRATION from EVALUATION, and calibrating and reporting
    on one set makes the reported phi an optimistic number."""

    KEYS = [f"item-{i:03d}" for i in range(40)]

    def test_the_two_subsets_are_disjoint_and_exhaust_the_benign_set(self):
        cal, rep = fdetect.calibration_report_split(self.KEYS)
        self.assertEqual(set(cal) & set(rep), set())
        self.assertEqual(sorted(cal + rep), sorted(self.KEYS))
        self.assertEqual(len(cal), 20)

    def test_the_split_does_not_depend_on_the_input_order(self):
        cal_a, rep_a = fdetect.calibration_report_split(self.KEYS)
        cal_b, rep_b = fdetect.calibration_report_split(list(reversed(self.KEYS)))
        self.assertEqual(sorted(cal_a), sorted(cal_b))
        self.assertEqual(sorted(rep_a), sorted(rep_b))

    def test_the_split_is_not_a_name_sort(self):
        """`sorted(keys)[:k]` is deterministic AND biased -- it selects by name.
        That is the defect gate 2 v2 found in its own subset rule; it does not get
        to recur here."""
        cal, _ = fdetect.calibration_report_split(self.KEYS)
        self.assertNotEqual(sorted(cal), sorted(self.KEYS)[:20])

    def test_the_split_moves_with_its_declared_seed(self):
        cal_a, _ = fdetect.calibration_report_split(self.KEYS, seed=1)
        cal_b, _ = fdetect.calibration_report_split(self.KEYS, seed=2)
        self.assertNotEqual(sorted(cal_a), sorted(cal_b))

    def test_the_split_refuses_a_duplicated_key(self):
        with self.assertRaises(ValueError):
            fdetect.calibration_report_split(["a", "b", "a"])


class DPrimeEffIsPerAttacker(unittest.TestCase):
    """G2 and G3: reported PER ATTACKER.  Never `min`, never a pooled mean -- a
    pooled number averages the regime where the method works with the one where it
    does not, which is the single thing this grid exists to keep apart."""

    def _table(self):
        j = ScriptedJudge({"a1": 0.8, "a2": 0.4, "b1": 0.1, "b2": 0.3})
        items = [Item(carrier="memory", topic="orm", content=c, created_at=0,
                      provenance="repo/docs/conventions.md", poisoned=True)
                 for c in ("a1", "a2", "b1", "b2")]
        return fdetect.MTable.build(items, j), items

    def test_d_prime_eff_is_d_prime_times_the_attackers_own_mean_m(self):
        table, items = self._table()
        loud = fdetect.AttackSample(name="loud", items=tuple(items[:2]))
        self.assertAlmostEqual(fdetect.d_prime_eff(loud, table, 2.0), 2.0 * 0.6)

    def test_two_attackers_are_reported_separately(self):
        table, items = self._table()
        loud = fdetect.AttackSample(name="loud", items=tuple(items[:2]))
        quiet = fdetect.AttackSample(name="quiet", items=tuple(items[2:]))
        got = fdetect.d_prime_eff_by_attack([loud, quiet], table, 2.0)
        self.assertEqual(sorted(got), ["loud", "quiet"])
        self.assertAlmostEqual(got["loud"], 1.2)
        self.assertAlmostEqual(got["quiet"], 0.4)

    def test_d_prime_eff_refuses_a_collection_of_attackers(self):
        """The one call that would silently produce a pooled number."""
        table, items = self._table()
        pair = [fdetect.AttackSample(name="a", items=tuple(items[:2])),
                fdetect.AttackSample(name="b", items=tuple(items[2:]))]
        with self.assertRaises(TypeError):
            fdetect.d_prime_eff(pair, table, 2.0)

    def test_there_is_no_pooled_or_min_aggregate_in_the_module(self):
        for name in dir(fdetect):
            self.assertNotIn("pooled", name.lower())

    def test_an_attacker_with_no_items_refuses_rather_than_scoring_zero(self):
        table, _ = self._table()
        empty = fdetect.AttackSample(name="nothing", items=())
        with self.assertRaises(fdetect.NotMeasured):
            fdetect.d_prime_eff(empty, table, 2.0)


class NoAucBridge(unittest.TestCase):
    def test_the_chain_never_converts_through_the_auc_bridge(self):
        """`d' = sqrt(2) * Phi^-1(AUC)` is explicitly rejected in the
        pre-registration: m is a violation score with near-zero mass, further from
        equal-variance Gaussian than the case already thrown out."""
        import fdetect_g4
        for mod in (fdetect, fdetect_g4):
            src = inspect.getsource(mod)
            body = "\n".join(l for l in src.splitlines()
                             if "REJECT" not in l and "never" not in l.lower())
            self.assertNotIn("2 ** 0.5", body)
            self.assertNotIn("sqrt(2)", body)
            self.assertNotIn("auc", body.lower().replace("because", ""))


if __name__ == "__main__":
    unittest.main()
