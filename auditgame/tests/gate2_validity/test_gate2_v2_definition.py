"""
GATE 2 -- the v2 DEFINITION of the gate, and the three holes it closes at once.

Spec: docs/thesis/MO-HINH-EPSILON-BA-CHIEU.md (the epsilon model
this payload construction implements); review II.3 (close all three holes AT ONCE,
freeze the definition, then run the table once).

The v1 gate had three known holes, two of them pointing in OPPOSITE directions, so
its verdict meant nothing:

    hole                         gate was      closed by
    F_match lacks `topic`        TOO LOOSE     core.Item.surface() grows `topic`
    `_one_event` at seed=1       TOO STRICT    a per-workflow seed through seed_of
    benign-corpus leakage        too loose     `holdout` (already closed; verified)

NO CERTIFICATION VERDICT IS DRAWN HERE.  This file pins the DEFINITION -- which
features, which seed rule, which L, which theta, which criterion -- and the md5
over it.  Running the certification table against that definition is a separate
step, deliberately: a definition that can still move is a definition that can be
moved after the table is seen.
"""
from __future__ import annotations
import json
import pathlib
import random
import subprocess
import sys
import unittest

import attacks
import build
import core
import retrieval
from analysis import benign_corpus as B
from analysis import discriminator as D
from analysis import gate2_v2
from core import CarrierStore, Item, PoisonSpec, Task, Workflow


def _token_wf(token_sets, wf_id="w", repo="r"):
    """A workflow whose task topics are the given TOKEN SETS -- the graded shape,
    which is the only shape on which `topic` carries anything at all (a mock topic
    is one token and has itself as its only non-empty subset)."""
    return Workflow(wf_id=wf_id, repo=repo, tasks=[
        Task(task_id=f"t{i}", repo=repo, base_commit="0" * 7,
             topic=retrieval.Topic(toks), problem="")
        for i, toks in enumerate(token_sets)])


def _item(topic, content="c", provenance="agent/notes"):
    return Item(carrier="memory", topic=topic, content=content, created_at=0,
                provenance=provenance, poisoned=False)


# ======================================================================== 1 ====
class TopicJoinsTheMeasuredFeatureSpace(unittest.TestCase):
    """HOLE 1, closed.  `F_match` IS `core.Item.surface()` by definition, and until
    v2 it was {size, depth, recency, derived}.  `topic` was outside it, which is
    the channel tests/gate2_validity/test_matched_epsilon_budget.py measured at
    Mann-Whitney AUC 0.9492 on the v1 corpus.  A gate that cannot see the axis its
    own attacker moves on is TOO LOOSE, and it is loose in OUR favour.
    """

    def test_the_surface_and_F_MATCH_still_name_one_thing(self):
        """The anchor the whole gate rests on: the feature set the discriminator
        scores is EXACTLY the feature set the attacker has to match.

        Thesis claim (vi): "F_match dung bang Item.surface(), khong phai mot ban sao".
        """
        self.assertEqual(frozenset(_item("t").surface(now=1)), D.F_MATCH)

    def test_topic_is_one_of_the_features_gate_two_v2_scores(self):
        """Thesis claim (vi): "topic da vao F_match v2"."""
        self.assertIn("topic", D.F_MATCH)
        self.assertIn("topic", _item("t").surface(now=1))

    def test_the_topic_feature_is_a_number_the_discriminator_can_consume(self):
        """`discriminator._standardise` does arithmetic on every column, so a
        feature that is not a real number takes the whole gate down.

        Thesis claim (vi): "dac trung topic phai la SO".
        """
        for topic in ("orm", retrieval.Topic({"db", "models"}), retrieval.Topic()):
            with self.subTest(topic=topic):
                v = _item(topic).surface(now=1)["topic"]
                self.assertIsInstance(v, float)
                self.assertEqual(v, float(v))      # not a NaN

    def test_it_separates_WHICH_tokens_at_an_identical_token_COUNT(self):
        """The requirement that rules out the lazy feature.  `len(topic)` would be
        a second copy of what `size` already carries (measured on the epsilon
        model page: five real topics x five epsilons give 15 distinct `size`
        values with exactly ONE collision), so a count adds nothing.  What is NOT
        in `size` is WHICH tokens were kept.

        Thesis claim (vi): "dac trung topic phai phan biet TOKEN NAO, khong phai
        BAO NHIEU token".
        """
        a = _item(retrieval.Topic({"alpha", "beta"})).surface(now=1)["topic"]
        b = _item(retrieval.Topic({"yankee", "zulu"})).surface(now=1)["topic"]
        self.assertEqual(len(retrieval.Topic({"alpha", "beta"})),
                         len(retrieval.Topic({"yankee", "zulu"})))
        self.assertNotEqual(
            a, b,
            "two topics of the SAME size get the same feature value, so the "
            "feature is a token COUNT wearing another name and the channel it "
            "was added to close is still open.")

    def test_it_is_ordered_so_a_linear_discriminator_can_actually_read_it(self):
        """Being able to tell tokens apart is not enough: the discriminator is a
        LOGISTIC REGRESSION, i.e. monotone in each column, so a nominal
        fingerprint would be noise to it and the gate would be no harder at all.
        The code is MONOTONE IN LEXICOGRAPHIC ORDER of the canonical topic string,
        so a column the discriminator can fit a weight on.

        NOTE WHAT THIS TEST NO LONGER CLAIMS.  Until review II it was paired with
        a test asserting that `sorted(target)[:k]` scores BELOW the topic it was
        cut from -- which was true by theorem, not by measurement, and was the
        artefact the red cell was reading.  Order is still required, for the
        reason above; what is gone is the sorted subset rule that turned it into a
        guaranteed separation.

        Thesis claim (vi): "ma token phai co THU TU, khong thi hoi quy tuyen tinh
        khong doc duoc".
        """
        vals = [_item(retrieval.Topic({t})).surface(now=1)["topic"]
                for t in ("aaa", "mmm", "zzz")]
        self.assertEqual(vals, sorted(vals),
                         f"single-token codes are not lexicographically ordered: "
                         f"{vals}")

    def test_the_subset_rule_is_not_the_alphabetical_prefix(self):
        """THE DE-BIASING, and the test that goes red if `sorted()` comes back.

        `retrieval.payload_topic` used to return `Topic(sorted(target)[:k])` -- the
        k lexicographically SMALLEST tokens -- for the reason its own docstring
        gave: DETERMINISM.  Composed with a lexicographic topic code, that made
        `code(subset) <= code(whole)` a THEOREM rather than a measurement, so the
        gate's certification cell was reading `sorted()` and not the attacker.
        Review II ruling 1; pre-registered in docs/preregistration/cong-v2.md SS0bis.

        A deterministic pseudorandom k-subset keeps every property the attack
        model asks for and drops the one it never asked for.  On a topic whose
        tokens are far apart in the alphabet, the rule must pick something OTHER
        than the alphabetical prefix at least once across the grid -- otherwise
        the priority is correlated with the alphabet again.

        Thesis claim (vi): "tap con cua payload KHONG duoc la tien to bang chu
        cai -- neu khong, cong do chinh `sorted()` chu khong do ke tan cong".
        """
        whole = retrieval.Topic({"alpha", "bravo", "delta", "echo", "golf",
                                 "hotel", "india", "kilo"})
        differs = False
        for eps in (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875):
            part = retrieval.payload_topic(whole, eps)
            if set(part) != set(sorted(whole)[:len(part)]):
                differs = True
        self.assertTrue(
            differs,
            "payload_topic returned the alphabetical prefix at EVERY epsilon on "
            "an 8-token topic. The subset rule is lexicographic again, so a "
            "lexicographic topic feature separates the classes by theorem and "
            "the certification cell measures sorted(), not MatchedAttack.")

    def test_the_de_biased_rule_keeps_every_property_the_attack_model_requires(self):
        """De-biasing must cost NOTHING the model or the old docstring relied on.

        Five properties, all of them asserted rather than argued: the tag is a
        SUBSET (so the Jaccard denominator is not inflated and a larger epsilon is
        never weaker), |A| = ceil(eps*m), sim = k/m, the subsets are NESTED in
        epsilon (which is what keeps sim and |A| monotone), and the draw is
        reproducible -- `subset_priority` goes through `core.seed_of`, i.e.
        blake2b over the canonical string, never `hash()`.

        Thesis claim (vi): "khu thien lech ma KHONG mat mot tinh chat nao cua mo
        hinh tan cong".
        """
        import math
        whole = retrieval.Topic({"db", "django", "models", "query", "sql"})
        m = len(whole)
        prev = None
        for eps in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
            with self.subTest(eps=eps):
                a = retrieval.payload_topic(whole, eps)
                k = max(1, math.ceil(eps * m))
                self.assertTrue(a <= whole, "the tag is not a subset of sigma's topic")
                self.assertEqual(len(a), k, "|A| != ceil(eps*|B|)")
                self.assertAlmostEqual(retrieval.sim(a, whole), k / m, places=12)
                if prev is not None:
                    self.assertTrue(prev <= a,
                                    f"subsets are not nested in epsilon: "
                                    f"{sorted(prev)} -> {sorted(a)}")
                prev = a
                self.assertEqual(a, retrieval.payload_topic(whole, eps),
                                 "the draw is not reproducible within a process")

    def test_the_subset_rule_is_stable_across_PYTHONHASHSEED(self):
        """The de-biased rule is the one place a `hash()` would be easiest to
        reach for, and it would make every published AUC un-recheckable: the
        payload's topic reaches `Item.__post_init__`, which hashes it into
        `item_id`, which seeds `detector.score`.

        THE PROBE COVERS EVERY SHAPE THE RULE ACCEPTS, not just the one that is
        stable by construction.  `subset_priority` keys on the target's canonical
        string, and until this was widened the probe passed only a
        `retrieval.Topic`, whose `__str__` is canonical already -- so the test
        certified a property of `Topic`, not of the rule.  `as_topic` hands a bare
        `frozenset` straight back (`:99-101`) and `payload_topic_like` routes one
        through at `:235`, and a bare frozenset's `str()` walks its hash table:
        measured, the same call returned ['django'] / ['query'] / ['query'] under
        PYTHONHASHSEED 0 / 1 / 2.  No published number moved -- production callers
        pass `task.topic`, a `Topic` -- but a test quoted for "the subset rule is
        PYTHONHASHSEED-stable" has to probe the rule's whole domain, or it is
        narrower than the claim it is quoted for.  `set` and `list` are here for
        the same reason: `as_topic` accepts them too.

        Thesis claim (vi): "quy tac tap con phai on dinh qua PYTHONHASHSEED, voi
        MOI dang dau vao no nhan".
        """
        shapes = {
            "Topic": "retrieval.Topic({'django', 'db', 'models', 'query', 'sql'})",
            "bare frozenset": "frozenset({'django', 'db', 'models', 'query', 'sql'})",
            "set": "{'django', 'db', 'models', 'query', 'sql'}",
            "list": "['django', 'db', 'models', 'query', 'sql']",
        }
        for shape, literal in shapes.items():
            code = ("import sys; sys.path.insert(0, '.')\n"
                    "import retrieval\n"
                    f"t = {literal}\n"
                    "print([sorted(retrieval.payload_topic(retrieval.as_topic(t), e))\n"
                    "       for e in (0.2, 0.4, 0.6, 0.8)])\n"
                    "print([sorted(retrieval.payload_topic_like(t, e))\n"
                    "       for e in (0.2, 0.4, 0.6, 0.8)])\n")
            outs = set()
            for h in ("0", "1", "2", "424242"):
                r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                   text=True, cwd=str(pathlib.Path(build.__file__).parent),
                                   env={"PYTHONHASHSEED": h, "PATH": "/usr/bin:/bin"})
                self.assertEqual(r.returncode, 0, f"run failed at HASHSEED={h}: "
                                                  f"{r.stderr[-400:]}")
                outs.add(r.stdout)
            with self.subTest(shape=shape):
                self.assertEqual(
                    len(outs), 1,
                    f"the subset rule moves with PYTHONHASHSEED when the target is "
                    f"a {shape}: {outs}. `subset_priority` must key on the "
                    f"CANONICAL topic string for every shape `as_topic` accepts, "
                    f"the way core._canonical_topic_string already does.")

    def test_the_frozen_record_PINS_the_subset_rule_that_decides_the_cell(self):
        """THE PIN THE FIRST FIX FORGOT.  Review II ruling 1 replaced the subset
        rule; ruling 5 froze the parameters the cell is decided by; and the two
        did not meet.  `record()` named the topic FEATURE and not the subset RULE
        that feature is read through -- so the digest was blind to the single
        decision that moves the certify cells furthest.  Measured, by rebuilding the tree at
        `0c585b4` and changing the salt literal alone: `gate2_v2.md5()` came back
        byte-identical at `45274180520227436a90f03ca1dd21db` and the definition
        suite was unchanged (28 of 29 pass; the 29th errors only because the
        extracted tree carries no `data/`).  Over a 17-salt family the Delta=4
        cell runs from 0.5244 (19 of 20 splits clearing) to 0.6426 (0 of 20),
        against 0.5870 (1 of 20) shipped.  A digest that cannot see that is not
        freezing the definition, it is freezing a subset of it.

        Two fields, because two things can move independently:

          * `salt` -- the literal `core.seed_of` is keyed on.  It is a FREE
            PARAMETER: nothing in the attack model prefers one string, and the
            draw it induces is a different draw for each one.
          * `fingerprint` -- a digest of the rule's OUTPUT over a fixed probe.
            A prose `mechanism` string cannot go stale-but-green, because the
            fingerprint moves when the tokens the rule picks move, whatever the
            prose says.  That is the same defect this file flags in
            `screen_criterion`, and it is closed the same way.

        Thesis claim (vi): "quy tac tap con VA hat muoi cua no phai nam trong o
        bam -- doi mot trong hai la md5 PHAI doi".
        """
        rec = gate2_v2.record()
        self.assertIn("subset_rule", rec,
                      "the frozen record does not name the subset rule at all")
        sr = rec["subset_rule"]
        self.assertEqual(sr["salt"], retrieval.SUBSET_SALT)
        self.assertEqual(sr["mechanism"], retrieval.SUBSET_RULE)
        self.assertEqual(sr["fingerprint"], retrieval.subset_rule_fingerprint())

    def test_changing_the_subset_SALT_moves_the_digest(self):
        """The salt is the parameter this pin exists for, so it gets its own test.

        Not a test about shopping: the salt was fixed in the pre-registration
        (`c85a936`) before any measurement, and it is the second-WORST of the
        family at Delta=4.  It is a test about VISIBILITY -- whoever changes it
        next must move the digest doing so, and therefore say so.

        Thesis claim (vi): "doi hat muoi la doi dinh nghia cong, khong phai doi
        mot chi tiet cai dat".
        """
        before = retrieval.SUBSET_SALT
        base = gate2_v2.md5()
        try:
            retrieval.SUBSET_SALT = before + "#1"
            self.assertNotEqual(
                base, gate2_v2.md5(),
                "changing the subset salt left the frozen digest unchanged. The "
                "salt decides which tokens the payload carries and moves the "
                "certify cells by more than the criterion's own margin; a freeze "
                "that does not react to it is decorative.")
        finally:
            retrieval.SUBSET_SALT = before
        self.assertEqual(gate2_v2.md5(), base, "the salt was not restored")

    def test_changing_the_subset_MECHANISM_moves_the_digest(self):
        """The salt is not the only way to change which tokens get stamped.

        The fingerprint is taken over the rule's OUTPUT, so putting `sorted()[:k]`
        back -- the exact regression review II ruling 1 removed -- moves the
        digest even though the salt, the prose and every other field are
        untouched.

        Thesis claim (vi): "dua `sorted()` tro lai PHAI lam md5 doi".
        """
        base = gate2_v2.md5()
        before = retrieval.payload_topic
        try:
            retrieval.payload_topic = lambda target, eps: retrieval.Topic(
                sorted(target)[:max(1, __import__("math").ceil(eps * len(target)))]
            ) if target else retrieval.Topic()
            self.assertNotEqual(
                base, gate2_v2.md5(),
                "restoring the alphabetical-prefix subset rule left the frozen "
                "digest unchanged: the freeze covers the rule's NAME and not its "
                "BEHAVIOUR.")
        finally:
            retrieval.payload_topic = before
        self.assertEqual(gate2_v2.md5(), base, "the rule was not restored")

    def test_the_subset_rule_fingerprint_is_itself_PYTHONHASHSEED_stable(self):
        """A pinned digest that moves between two runs of the same code would make
        the freeze unfalsifiable -- every checker would get a different answer and
        none could tell a real edit from a re-run.

        Thesis claim (vi): "van tay quy tac tap con phai tai lap duoc giua cac
        tien trinh".
        """
        code = ("import sys; sys.path.insert(0, '.')\n"
                "import retrieval\n"
                "print(retrieval.subset_rule_fingerprint())\n")
        outs = set()
        for h in ("0", "1", "2", "424242"):
            r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                               text=True, cwd=str(pathlib.Path(build.__file__).parent),
                               env={"PYTHONHASHSEED": h, "PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 0, f"run failed at HASHSEED={h}: "
                                              f"{r.stderr[-400:]}")
            outs.add(r.stdout.strip())
        self.assertEqual(len(outs), 1,
                         f"the subset-rule fingerprint moves with PYTHONHASHSEED: {outs}")

    def test_the_topic_feature_is_the_one_the_frozen_record_NAMES(self):
        """Four defensible lexicographic codes of a token set span AUC 0.45 to
        1.00 on this corpus (docs/preregistration/cong-v2.md SS3.7), so `features` containing
        the string "topic" does not pin the feature.  `topic_feature` does, and
        `core.topic_code` has to BE the candidate it names -- not agree with it by
        hand.

        Thesis claim (vi): "dac trung topic phai duoc GOI TEN trong ban ghi dong
        bang, khong phai ngu y".
        """
        name = gate2_v2.record()["topic_feature"]
        self.assertIn(name, core.TOPIC_CODE_CANDIDATES)
        self.assertEqual(name, core.TOPIC_CODE_CHOICE)
        for topic in ("orm", retrieval.Topic({"db", "models"}),
                      retrieval.Topic({"django", "db", "models", "query"}),
                      retrieval.Topic()):
            with self.subTest(topic=topic):
                self.assertEqual(core.topic_code(topic),
                                 core.TOPIC_CODE_CANDIDATES[name](topic))

    def test_all_four_candidate_features_stay_runnable_and_tell_topics_apart(self):
        """The sensitivity table in the spike is only checkable if the rejected
        candidates are still CODE.  Keeping them runnable is what stops
        "we measured four" from becoming an unverifiable sentence.

        Thesis claim (vi): "ba ung vien bi loai van phai CHAY DUOC de bang do
        nhay tai lap duoc".
        """
        self.assertEqual(set(core.TOPIC_CODE_CANDIDATES),
                         {"canonical", "mean", "max", "sum"})
        a = retrieval.Topic({"alpha", "beta"})
        b = retrieval.Topic({"yankee", "zulu"})
        for name, fn in sorted(core.TOPIC_CODE_CANDIDATES.items()):
            with self.subTest(candidate=name):
                self.assertIsInstance(fn(a), float)
                self.assertEqual(fn(retrieval.Topic()), 0.0)
                self.assertNotEqual(fn(a), fn(b),
                                    f"candidate {name!r} gives two different "
                                    f"topics the same code")
                self.assertLess(fn(a), fn(b),
                                f"candidate {name!r} is not monotone in "
                                f"lexicographic order, so a logistic regression "
                                f"cannot read it")

    def test_the_canonical_candidate_really_is_the_string_the_codebase_hashes(self):
        """The ground review II ruling 2 named, asserted so that it can FAIL.  The
        claim is not "a canonical string is nice"; it is "this exact string is
        already this project's identity for a topic" -- `retrieval.Topic.__str__`,
        which `core.seed_of` stringifies and `Item.__post_init__` hashes into
        `item_id`, which `detector.score` seeds on.  The claim is TRUE, and it is
        kept assertable even though the candidate was not the one shipped: a
        ground that is discarded for a different reason is not a ground that was
        wrong, and the next reviewer needs to be able to check it.

        Thesis claim (vi): "ly do chon dac trung phai KIEM TRA DUOC trong code,
        khong phai mot cau van".
        """
        t = retrieval.Topic({"query", "db", "models", "django"})
        self.assertEqual(str(t), "db|django|models|query")
        self.assertEqual(core.TOPIC_CODE_CANDIDATES["canonical"](t),
                         core._code8(str(t)))
        # the same string is what seed_of actually hashes, hence what item_id is
        self.assertEqual(core.seed_of(t), core.seed_of(str(t)))

    def test_the_SHIPPED_feature_is_the_one_not_displaced_by_taking_a_subset(self):
        """THE GROUND THE CHOICE ACTUALLY RESTS ON, and the test that goes red if
        a displaced candidate is shipped again.

        The attack model's one structural difference between the classes is that a
        payload's tag is a SUBSET of a task topic while a benign note carries the
        whole one.  So a topic feature that is systematically displaced by
        subsetting separates the classes BY CONSTRUCTION, and the gate reads its
        own payload-construction rule instead of the attacker.  That is review II
        finding 1, and `sorted(target)[:k]` was only one way to arrive at it:
        `canonical` (the canonical string opens with min(tokens), and
        min(A) >= min(B)), `max` and `sum` are each displaced too.

        `mean` is the only one of the four that is not: for a uniformly drawn
        k-subset A of B, E[mean(A)] = mean(B).  Asserted here as a COUNT over real
        topics rather than as an inequality, because the counts are what the spike
        publishes and what a reviewer can re-run: the shipped feature must displace
        UP about as often as it displaces DOWN, while each rejected candidate must
        be lopsided.

        Thesis claim (vi): "dac trung duoc giao phai la cai KHONG bi phep lay tap
        con lam lech -- neu khong, Phat hien 1 quay lai duoi mot lop ao khac".
        """
        rng = random.Random(20260918)
        alphabet = [f"{a}{b}{c}" for a in "abcdefgmnoqrstwxyz"
                    for b in "aeiou" for c in "bcdfglmnprstv"]
        topics = [retrieval.Topic(rng.sample(alphabet, rng.randint(3, 7)))
                  for _ in range(400)]

        def displacement(fn):
            up = down = 0
            for t in topics:
                a, b = fn(retrieval.payload_topic(t, 0.0)), fn(t)
                up += a > b + 1e-15
                down += a < b - 1e-15
            return up, down

        up, down = displacement(core.topic_code)
        self.assertGreater(min(up, down), 0.35 * (up + down),
                           f"the SHIPPED topic feature is displaced by taking a "
                           f"subset ({up} up / {down} down of {len(topics)}). The "
                           f"classes then separate by a theorem and the gate is "
                           f"measuring payload_topic, not the attacker.")
        for name in ("canonical", "max", "sum"):
            with self.subTest(rejected=name):
                u, d = displacement(core.TOPIC_CODE_CANDIDATES[name])
                self.assertLess(
                    min(u, d), 0.35 * (u + d),
                    f"candidate {name!r} is no longer lopsided under subsetting "
                    f"({u} up / {d} down). It was rejected FOR being lopsided, so "
                    f"either the subset rule or the candidate has changed and the "
                    f"choice has to be re-argued rather than inherited.")

    def test_the_feature_does_not_depend_on_PYTHONHASHSEED(self):
        """The project's reproducibility rule, applied to the new column.  A
        feature read off a `frozenset` is one `hash()` away from making the
        published AUC un-recheckable -- exactly the trap `core.seed_of` and
        `retrieval.Topic.__str__` exist to close.

        Thesis claim (vi): "dac trung moi phai on dinh qua PYTHONHASHSEED".
        """
        code = ("import sys; sys.path.insert(0, '.')\n"
                "import retrieval\n"
                "from core import Item\n"
                "t = retrieval.Topic({'django', 'db', 'models', 'query'})\n"
                "it = Item(carrier='memory', topic=t, content='c', created_at=0,\n"
                "          provenance='agent/notes', poisoned=False)\n"
                "print(repr(it.surface(now=1)['topic']))\n")
        outs = set()
        for h in ("0", "1", "424242"):
            r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                               text=True, cwd=str(pathlib.Path(build.__file__).parent),
                               env={"PYTHONHASHSEED": h, "PATH": "/usr/bin:/bin"})
            self.assertEqual(r.returncode, 0, f"run failed at HASHSEED={h}: "
                                              f"{r.stderr[-400:]}")
            outs.add(r.stdout)
        self.assertEqual(len(outs), 1,
                         f"the topic feature moves with PYTHONHASHSEED: {outs}")


# ======================================================================== 2 ====
class TheEventSeedIsDrawnPerWorkflow(unittest.TestCase):
    """HOLE 2 (P8), closed.  `_one_event` ran EVERY workflow at `seed=1`, so one
    draw of the agent's adoption / induction / queue / drift coins stood for the
    whole corpus.  That makes the benign class narrower than the population it is
    supposed to represent, i.e. the gate was TOO STRICT -- the opposite direction
    from hole 1, which is why review II.3 forbids closing them one at a time.
    """

    def test_the_seed_is_deterministic_in_the_workflow(self):
        """Every draw in this module descends from core.seed_of, so a rebuilt
        corpus is byte-identical.  hash() is banned: PYTHONHASHSEED randomises it.

        Thesis claim (vi): "hat giong su kien deterministic qua seed_of".
        """
        wf = _token_wf([("a",), ("b",)], wf_id="wf-000")
        self.assertEqual(B.event_seed(B.SEED, wf), B.event_seed(B.SEED, wf))

    def test_the_seed_is_NOT_constant_across_workflows(self):
        """The hole itself.  If this passes with a constant the corpus is one
        agent run repeated, and `n_neg` counts draws that are not independent.

        Thesis claim (vi): "hat giong phai DOI theo workflow, khong phai hang so 1".
        """
        seeds = {B.event_seed(B.SEED, _token_wf([("a",)], wf_id=f"wf-{i:03d}"))
                 for i in range(20)}
        self.assertGreater(
            len(seeds), 1,
            "every workflow draws the same event seed, so P8 is not closed.")
        self.assertNotEqual(seeds, {1})

    def test_the_corpus_builder_actually_uses_it(self):
        """A helper nothing calls closes nothing.  The seeds `_one_event` hands
        `MockAgent.run_task` are captured and must (a) not be the literal 1 for
        every workflow and (b) be the helper's own answer.

        Thesis claim (vi): "duong chay THAT phai dung hat giong do, khong con seed=1".
        """
        import agent
        seen = []
        real = agent.MockAgent.run_task

        def spy(self, t, task, store, seed, marker):
            seen.append(seed)
            return real(self, t, task, store, seed, marker)

        agent.MockAgent.run_task = spy
        try:
            pipe = attacks.REGISTRY["matched"]
            _pos, _neg = B.matched_corpus(pipe, 2, 0.0, 12)
        finally:
            agent.MockAgent.run_task = real
        self.assertTrue(seen, "no agent run happened -- the corpus was empty")
        self.assertGreater(
            len(set(seen)), 1,
            f"every event ran the agent at the same seed {set(seen)}: P8 is open.")
        self.assertNotIn(1, set(seen),
                         "the literal seed 1 is still being handed to the agent.")


# ======================================================================== 3 ====
class ThePayloadIsBuiltAtAFrozenTotalLength(unittest.TestCase):
    """HOLE 1's other half, from the three-dimensional epsilon model.  Under v1 the
    topic tokens were interpolated into `content`, so `size` -- an F_match feature
    -- moved with k and therefore with epsilon: measured on the model page, five
    real topics x five epsilons gave 15 distinct sizes with ONE collision, i.e.
    `size` nearly determined k.  At a frozen total length L the topic tokens and
    the advice SHARE one budget and `size` stops varying with epsilon, so the size
    channel closes BY CONSTRUCTION rather than by adding a feature.
    """

    GRID = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

    def _wf(self):
        # four tokens, so the attainable k grid is 1..4 and eps really moves it;
        # short tokens, so the tag fits inside L at every k (see the reason test).
        return _token_wf([("aa", "bb", "cc", "dd"), ("ee", "ff"),
                          ("gg", "hh", "ii"), ("jj", "kk", "ll", "mm")])

    def _payload(self, wf, eps):
        return build.inject(CarrierStore(), wf,
                            PoisonSpec(carrier="memory", iota=1, sigma=3,
                                       epsilon=eps))

    def test_size_does_not_move_with_epsilon(self):
        """THE invariant this construction exists for.

        Thesis claim (vi): "size la HANG SO theo epsilon -- kenh size dong theo
        cau tao".
        """
        wf = self._wf()
        sizes = {eps: self._payload(wf, eps).surface(now=3)["size"]
                 for eps in self.GRID}
        self.assertEqual(
            set(sizes.values()), {build.PAYLOAD_LENGTH},
            f"the payload's size still moves with epsilon: {sizes}. L is not "
            f"frozen and `size` is still a proxy for k.")

    def test_epsilon_still_buys_retrievability(self):
        """The budget must keep its UPSIDE, or L just removed the only thing
        epsilon did.  sim = k/m is strictly increasing in k.

        Thesis claim (vi): "epsilon van mua duoc kha nang truy xuat".
        """
        wf = self._wf()
        target = retrieval.as_topic(wf.tasks[3].topic)
        sims = [retrieval.sim(retrieval.as_topic(self._payload(wf, e).topic), target)
                for e in self.GRID]
        self.assertEqual(sims, sorted(sims), f"sim must be non-decreasing: {sims}")
        self.assertLess(sims[0], sims[-1], f"epsilon cannot change sim: {sims}")

    def test_what_epsilon_now_PAYS_is_advice_characters_not_size(self):
        """The cost side, moved from `size` to the third dimension of the model:
        L_advice = L - L_topic(k), so a wider tag leaves less room for the advice
        and (model SS4a) less harm.  `size` no longer carries it.

        Thesis claim (vi): "gia cua epsilon nay la SO KY TU LOI KHUYEN, khong phai
        size".
        """
        wf = self._wf()
        adv = [build.payload_advice_chars(
                   retrieval.payload_topic_like(wf.tasks[3].topic, e))
               for e in self.GRID]
        self.assertEqual(adv, sorted(adv, reverse=True),
                         f"advice budget must be non-increasing in eps: {adv}")
        self.assertLess(adv[-1], adv[0],
                        f"epsilon costs nothing at all: {adv}")

    def test_the_payload_still_names_its_marker_at_the_median_tag(self):
        """The one FROZEN-DATA change this task authorises, and the reason for it.
        The advice is built INSTRUCTION FIRST so that the budget squeezes the
        justification, never the marker: truncating the old word order at the
        corpus's median tag length cut the payload off inside `raw_write`, which
        is a payload naming a function that does not exist.  Model SS4a wants harm
        to DEGRADE with L_advice, not to be destroyed by where the cut lands.

        Thesis claim (vi): "cat vao phan GIAI THICH, khong bao gio cat vao lenh".
        """
        wf = self._wf()
        for eps in self.GRID:
            with self.subTest(eps=eps):
                self.assertIn("raw_write", self._payload(wf, eps).content)

    def test_a_tag_wider_than_L_records_a_REASON_instead_of_a_silent_truncation(self):
        """Rule N3 at the payload.  A topic whose tag alone is wider than L cannot
        be built at L, and the model (SS4a) says exactly what that is: L_advice
        falls to 0 and harm collapses.  It must be READABLE, not guessed at from a
        size that quietly stopped being L.

        Thesis claim (vi): "tag rong hon L thi GHI LY DO, khong cat im lang".
        """
        wide = retrieval.Topic({f"token{i:03d}" for i in range(12)})
        self.assertGreater(len(build.payload_tag(wide)), build.PAYLOAD_LENGTH)
        self.assertEqual(build.payload_advice_chars(wide), 0)
        reason = build.payload_length_reason(wide)
        self.assertIsNotNone(reason)
        self.assertIn("L", reason)
        self.assertIsNone(build.payload_length_reason(retrieval.Topic({"db"})))

    def test_the_LIVE_injection_path_records_that_reason_instead_of_dropping_it(self):
        """RULE N3, AND THE HOLE IT HAD (review II ruling 3).  Writing a reason
        that only a test ever calls is not recording it.  `build.inject` never
        invoked `payload_length_reason`, so 170 of the 2248 feasible sigmas at
        eps = 1.0 (7.6%, widest tag 506 characters) were built tag-only in
        SILENCE while the frozen record and the spike asserted size == 63 -- the
        exact silent value N3 forbids.

        Two things are asserted, and the second is the one that goes red if the
        wiring is removed: the payload of an over-wide tag really is built
        tag-only (so the invariant genuinely does not hold for it), and `inject`
        puts the REASON into the observation sink for exactly those events and for
        no others.

        The reason must NOT reach `provenance`: `provenance` is a scored feature
        (`depth`), so a reason written there would inject signal into the thing
        being measured.  Asserted too.

        Thesis claim (vi): "duong chay THAT phai GHI LY DO, khong phai chi co mot
        test goi ham do".
        """
        wide = retrieval.Topic({f"token{i:03d}" for i in range(12)})
        narrow = retrieval.Topic({"db"})
        wf = _token_wf([tuple(narrow), tuple(wide)])
        reasons = {}
        store = CarrierStore()
        thin = build.inject(store, wf,
                            PoisonSpec(carrier="memory", iota=0, sigma=0,
                                       epsilon=1.0), length_reasons=reasons)
        self.assertEqual(len(thin.content), build.PAYLOAD_LENGTH)
        self.assertEqual(reasons, {},
                         "a payload that fits L recorded a length reason")
        fat = build.inject(store, wf,
                           PoisonSpec(carrier="memory", iota=0, sigma=1,
                                      epsilon=1.0), length_reasons=reasons)
        self.assertGreater(len(fat.content), build.PAYLOAD_LENGTH)
        self.assertEqual(fat.content, build.payload_tag(fat.topic),
                         "an over-wide tag was truncated instead of built "
                         "tag-only; the reason would then describe nothing")
        self.assertIn(fat.item_id, reasons,
                      "build.inject built a payload it could not build at L and "
                      "recorded NO reason. That is the silent value N3 forbids.")
        self.assertIn("L_advice = 0", reasons[fat.item_id])
        self.assertNotIn("L", fat.provenance)
        self.assertEqual(fat.provenance, thin.provenance,
                         "the reason leaked into `provenance`, which is the "
                         "scored feature `depth`")

    def test_payload_content_asks_payload_length_reason_rather_than_re_deciding(self):
        """ONE decision site.  The tag-only branch and the reason for it have to be
        the same expression, or they can disagree -- which is how the reason came
        to be computed by nothing but a test in the first place.

        Mutating `payload_length_reason` so that it fires on a NARROW topic must
        therefore change what `payload_content` builds for that topic.  If it does
        not, `payload_content` is still deciding for itself and the two can drift.

        Thesis claim (vi): "quyet dinh va LY DO cua no phai la MOT bieu thuc".
        """
        wide = retrieval.Topic({f"token{i:03d}" for i in range(12)})
        narrow = retrieval.Topic({"db"})
        self.assertEqual(build.payload_content(wide, "raw_write"),
                         build.payload_tag(wide))
        self.assertEqual(len(build.payload_content(narrow, "raw_write")),
                         build.PAYLOAD_LENGTH)
        real = build.payload_length_reason
        build.payload_length_reason = lambda topic: "mutated: always a reason"
        try:
            # With the reason firing everywhere, the tag-only branch must fire
            # everywhere too. That is what proves the branch READS it.
            self.assertEqual(build.payload_content(narrow, "raw_write"),
                             build.payload_tag(narrow),
                             "payload_content decided the tag-only branch for "
                             "itself instead of asking payload_length_reason")
        finally:
            build.payload_length_reason = real
        self.assertEqual(len(build.payload_content(narrow, "raw_write")),
                         build.PAYLOAD_LENGTH)


# ======================================================================== 4 ====
class TheGateTwoV2DefinitionIsFrozen(unittest.TestCase):
    """The freeze itself.  Same discipline as `reference/score_table.json` and
    `metrics.config_sha`: the parameters that must move TOGETHER sit in ONE hash
    cell, and a test pins the digest so that moving one of them silently is
    impossible.
    """

    def test_the_record_carries_every_field_the_criterion_is_stated_in(self):
        """A freeze that omits a parameter freezes nothing about it.

        Thesis claim (vi): "ban ghi phai chua DU tham so cua tieu chi".
        """
        rec = gate2_v2.record()
        self.assertEqual(sorted(rec["features"]), sorted(D.F_MATCH))
        self.assertEqual(rec["payload_length_L"], build.PAYLOAD_LENGTH)
        self.assertEqual(rec["theta"], retrieval.THETA)
        self.assertEqual(tuple(rec["split_seeds"]), tuple(D.SPLIT_SEEDS))
        self.assertEqual(rec["test_fraction"], 0.4)
        self.assertEqual(rec["ceiling"], 0.56)
        self.assertEqual(rec["criterion"], "mean_ci95_upper_over_split_seeds")
        self.assertEqual(rec["event_seed_rule"], B.EVENT_SEED_RULE)
        self.assertEqual(rec["date"], "2026-09-18")
        # REVIEW II RULING 5 -- the parameters the red cell is ACTUALLY decided
        # by. The record used to pin the certify criterion and four corpus
        # fields; the benign background alone moved the cell by 0.0421, and the
        # SCREEN phase is what ends the test. Two people could satisfy the same
        # md5 and report different numbers.
        self.assertEqual(rec["screen_criterion"], gate2_v2.SCREEN_CRITERION)
        self.assertEqual(tuple(rec["epsilon_grid"]), tuple(gate2_v2.EPSILON_GRID))
        self.assertEqual(tuple(rec["deltas"]), tuple(gate2_v2.DELTAS))
        self.assertEqual(rec["n_events"], {"screen": gate2_v2.N_SCREEN,
                                           "certify": gate2_v2.N_CERTIFY})
        self.assertEqual(rec["corpus"]["natural"], B.NATURAL)
        self.assertEqual(rec["corpus"]["per_event"], B.PER_EVENT)
        self.assertEqual(rec["corpus"]["holdout"], B.HOLDOUT)
        self.assertEqual(rec["topic_feature"], core.TOPIC_CODE_CHOICE)
        self.assertEqual(rec["payload_length_rule"], build.PAYLOAD_LENGTH_RULE)
        # FIX 2 -- the subset rule and its salt. Measured on the tree at
        # 0c585b4: with the salt alone changed the digest came back identical and
        # the definition suite was unchanged, while the Delta=4 certify cell moves
        # across a 17-salt family from 1/20 to as many as 19/20 splits clearing.
        self.assertEqual(rec["subset_rule"]["salt"], retrieval.SUBSET_SALT)
        self.assertEqual(rec["subset_rule"]["mechanism"], retrieval.SUBSET_RULE)
        self.assertEqual(rec["subset_rule"]["fingerprint"],
                         retrieval.subset_rule_fingerprint())
        # SALT FAMILY -- the replication unit is the salt, not the split.
        self.assertEqual(rec["replication_unit"], "salt")
        self.assertEqual(rec["salt_family"], list(gate2_v2.SALT_FAMILY))
        self.assertEqual(rec["salt_criterion"], gate2_v2.SALT_CRITERION)

    def test_the_gate_test_reads_the_protocol_off_the_frozen_record(self):
        """A pinned criterion that the gate does not actually run is decorative.
        `tests/gate2_validity/test_benign_corpus.py` imports the ceiling, both
        sample sizes, the epsilon grid and the delta set from `gate2_v2`, so the
        digest covers what the cell was measured under.

        Thesis claim (vi): "tieu chi duoc GHIM phai dung la tieu chi duoc CHAY".
        """
        from tests.gate2_validity import test_benign_corpus as T
        self.assertEqual(T.AUC_CEILING, gate2_v2.record()["ceiling"])
        self.assertEqual(T.N_SCREEN, gate2_v2.N_SCREEN)
        self.assertEqual(T.N_CERTIFY, gate2_v2.N_CERTIFY)
        self.assertEqual(tuple(T.EPSILONS), tuple(gate2_v2.EPSILON_GRID))
        self.assertEqual(tuple(T.DELTAS), tuple(gate2_v2.DELTAS))
        #: `per_event` was in the hash cell but NOT in the gate test: the test
        #: took it from a literal default of 4 in `_matched_corpus`'s signature,
        #: so the record's field and the number the corpus was built with could
        #: part company silently, which is exactly the failure `natural` and
        #: `holdout` are covered against.
        self.assertEqual(T.PER_EVENT, gate2_v2.record()["corpus"]["per_event"])

    def test_the_screen_criterion_NAMES_the_statistic_the_screen_READS(self):
        """`screen_criterion` was free text.  Nothing bound the sentence to the
        `auc_median` the screen actually indexes out of `auc_over_splits`, so a
        screen switched to `auc_max` -- a strictly different and much harsher
        criterion on an 80-event fold -- would not have moved the digest by one
        bit.  The only test on the field was a tautology (`rec["screen_criterion"]
        == SCREEN_CRITERION`).

        It is bound by giving the record a NAMED KEY and one accessor, and making
        the gate test read the statistic through that accessor instead of
        spelling it.  Changing the screen then requires editing a frozen field.

        Thesis claim (vi): "tieu chi sang phai GOI TEN dai luong ma no doc, khong
        phai mo ta bang van xuoi".
        """
        import inspect
        from tests.gate2_validity import test_benign_corpus as T
        stat = gate2_v2.SCREEN_CRITERION["statistic"]
        def _row(x):
            return {f: x for f in D.F_MATCH}
        probe = D.auc_over_splits([_row(v) for v in (1.0, 2.0, 3.0, 4.0)] * 8,
                                  [_row(v) for v in (1.5, 2.5, 3.5, 0.5)] * 8,
                                  ceiling=0.56, seeds=D.SPLIT_SEEDS[:3])
        self.assertIn(stat, probe,
                      f"screen_criterion names statistic {stat!r}, which "
                      f"discriminator.auc_over_splits does not return")
        self.assertEqual(gate2_v2.screen_statistic(probe), probe[stat],
                         "gate2_v2.screen_statistic does not read the field")
        src = inspect.getsource(T)
        self.assertIn("screen_statistic", src,
                      "the gate test does not read the screened statistic through "
                      "gate2_v2.screen_statistic")
        for literal in (f'["{stat}"]', f"['{stat}']"):
            self.assertNotIn(
                literal, src,
                f"the gate test still indexes {literal} directly. The screened "
                f"statistic must come from gate2_v2.screen_statistic, or the "
                f"pinned criterion and the criterion that runs are two objects "
                f"that happen to agree today.")

    def test_the_md5_is_the_one_the_definition_was_frozen_at(self):
        """THE PIN.  Any edit to a frozen field moves this digest, and moving it
        is then a visible edit to the criterion rather than a quiet one.

        Thesis claim (vi): "md5 dinh nghia cong 2 v2 duoc GHIM".
        """
        self.assertEqual(gate2_v2.md5(), gate2_v2.FROZEN_MD5)

    def test_the_committed_artefact_agrees_with_the_live_definition(self):
        """`reference/gate2_v2.json` is the artefact a reader cites; the live
        modules are what the gate actually runs on.  If they disagree, the cited
        definition is not the measured one -- the same failure `score_table.json`'s
        "do not hand-edit" warning exists to prevent.

        Thesis claim (vi): "file dong bang phai KHOP voi dinh nghia song".
        """
        doc = json.loads(pathlib.Path(gate2_v2.PATH).read_text(encoding="utf-8"))
        self.assertEqual(doc["md5"], gate2_v2.FROZEN_MD5)
        self.assertEqual(doc["md5_single_salt"], gate2_v2.FROZEN_MD5_SINGLE_SALT)
        self.assertEqual(doc["record"], gate2_v2.record())

    def test_moving_any_frozen_parameter_moves_the_digest(self):
        """A hash cell that does not react is decorative.  Each field is perturbed
        one at a time and the digest must move for every one of them.

        Thesis claim (vi): "doi bat ky tham so dong bang nao la md5 PHAI doi".
        """
        base = gate2_v2.md5()
        rec = gate2_v2.record()
        for field, value in (("payload_length_L", rec["payload_length_L"] + 1),
                             ("theta", 0.75),
                             ("ceiling", 0.6),
                             ("test_fraction", 0.3),
                             ("split_seeds", list(range(1, 20))),
                             ("features", sorted(set(rec["features"]) - {"topic"})),
                             ("event_seed_rule", "constant-1"),
                             ("criterion", "max_ci95_upper_over_split_seeds"),
                             ("screen_criterion", "max_over_split_seeds"),
                             ("screen_criterion",
                              dict(rec["screen_criterion"], statistic="auc_max")),
                             ("epsilon_grid", [0.0, 0.5, 1.0]),
                             ("deltas", [0, 2]),
                             ("n_events", {"screen": 80, "certify": 620}),
                             ("topic_feature", "canonical"),
                             ("payload_length_rule", "content is always exactly L"),
                             ("corpus", dict(rec["corpus"], natural=True)),
                             ("corpus", dict(rec["corpus"], per_event=8)),
                             ("corpus", dict(rec["corpus"], holdout=1)),
                             ("subset_rule",
                              dict(rec["subset_rule"], salt="some_other_salt")),
                             ("subset_rule",
                              dict(rec["subset_rule"], fingerprint="0" * 16)),
                             ("subset_rule",
                              dict(rec["subset_rule"],
                                   mechanism="k smallest tokens of B")),
                             ("replication_unit", "split"),
                             ("salt_family", list(gate2_v2.SALT_FAMILY[:5])),
                             ("salt_criterion",
                              dict(rec["salt_criterion"], threshold=0.9))):
            with self.subTest(field=field):
                self.assertNotEqual(
                    base, gate2_v2.md5(dict(rec, **{field: value})),
                    f"perturbing {field!r} left the digest unchanged: the freeze "
                    f"does not cover it.")

    def test_the_record_says_out_loud_that_no_verdict_is_drawn_here(self):
        """Review II.3's order: close, freeze, THEN run the table once.  A frozen
        definition carrying a verdict would be a verdict taken before the freeze.

        THE CHECK IS "NO MEASURED AUC", NOT "NO OCCURRENCE OF THE LETTERS auc".
        It used to be the second, and that is why `screen_criterion` could only
        ever be prose: the moment the record NAMES the statistic it reads
        (`auc_median`, which is the whole point of binding it) the blanket string
        ban fires on a field that carries no measurement at all.  So the ban is
        stated as what it means: "auc" may appear only as a STATISTIC NAME, in the
        two criterion fields, and never next to a digit.  Adding
        `certify_auc=0.587` to the record still goes red, which is the property
        this test exists for.

        Thesis claim (vi): "ban ghi dinh nghia KHONG mang phan quyet nao -- ten
        dai luong thi duoc, GIA TRI do duoc thi khong".
        """
        rec = gate2_v2.record()
        allowed = {"criterion", "screen_criterion"}
        for field, value in rec.items():
            blob = json.dumps(value, ensure_ascii=False).lower()
            if "auc" not in blob and "auc" not in field.lower():
                continue
            with self.subTest(field=field):
                self.assertIn(field, allowed,
                              f"{field!r} mentions an AUC. The frozen record "
                              f"carries the DEFINITION; a measured value in it "
                              f"would be a verdict taken before the freeze.")
                self.assertFalse(
                    any(ch.isdigit() for ch in blob),
                    f"{field!r} carries an AUC beside a digit: that is a "
                    f"measurement, not a criterion. {blob}")
        self.assertEqual(rec["criterion"], "mean_ci95_upper_over_split_seeds")
        self.assertEqual(rec["screen_criterion"]["statistic"], "auc_median")
        self.assertEqual(rec["verdict"], "NOT DRAWN -- certification is a separate step")


if __name__ == "__main__":
    unittest.main()
