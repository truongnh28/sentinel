"""LlmDetector -- a detector that READS THE NOTE, in place of a synthetic draw.

WHY IT EXISTS.  `Detector.score` reads exactly one thing, `item.poisoned`, and
uses `item_id` as the SEED of a Gaussian draw.  Content therefore changes the
REALISATION of the draw and never its EXPECTATION.  No LLM has ever been inside
the defence loop: d' was a swept parameter, not a quantity that emerged from
words.

This class scores `item.content` with an LLM judge, read from a FROZEN CACHE.
Offline-then-frozen: a missing key RAISES rather than calling the network --
same reason as the payloads, since `item_id = blake2b(content)` seeds the rest
of the system and an LLM is not deterministic even at temperature 0.

SCALE.  The judge answers on 0-10; `Detector` promises scores ~ N(d', 1) under
the positive class and N(0, 1) under the negative one.  `from_cache` calibrates
on the NEGATIVE class actually present, so the scale keeps that contract and
the gap between the classes IS the judge's EMPIRICAL d' -- not a number we set.

SCOPE WARNING.  In-game benign items are what `agent.py` writes.  On the default
world those are four templates (`[topic] ghi chú từ <id>`, `commit`, ...) and a
judge separates them by counting words -- the second confound of 2026-09-20,
intact.  This class is only meaningful on a PROSE world whose negative class
also carries the payloads' MINIMAL-PAIR TWINS; without them the judge scores
note GENRE (d' = +10.6 against ordinary advice, -0.12 against the twins).
See TIEN-DANG-KY-Detector-Noi-Dung.md section 3.3 and `prose_world`.
"""
from __future__ import annotations
import re
import statistics as st
from dataclasses import dataclass

from analysis import content_judge as J

#: `agent.py` records a revision of an earlier note as "<content> (rev 3)".
#: That is the SAME note, so re-judging it is meaningless -- and the cache has
#: no entry for the new string.  Strip the suffix and look up the original.
_REV = re.compile(r"\s*\(rev \d+\)\s*$")


class MissingJudgement(J.MissingJudgement):
    pass


@dataclass
class LlmDetector:
    """`Detector`-compatible, but the score comes FROM THE CONTENT."""

    cache: dict
    mu_neg: float
    sd_neg: float
    d_prime: float
    tau_det: float = 0.0
    tag: str = "default"
    #: The COMMIT channel scores a PATCH, not a note, and the judge does not
    #: read diffs.  Delegate it, and treat that detector's d' as a DECLARED
    #: value -- never pool it with the MEASURED d' of the note channel.
    patch_detector: object = None
    patch_d_prime_is_declared: bool = True

    @classmethod
    def from_cache(cls, pos_texts: list, neg_texts: list,
                   tag: str = "default", tau_det: float = 0.0):
        """Calibrate the scale on two ALREADY-JUDGED classes.

        d' is COMPUTED from the cache, never passed in.  That is the whole
        difference from `Detector`.
        """
        cache = J.load_cache()
        pos = [J.score(t, cache, tag) for t in pos_texts if J.key(t, tag) in cache]
        neg = [J.score(t, cache, tag) for t in neg_texts if J.key(t, tag) in cache]
        if len(pos) < 2 or len(neg) < 2:
            raise MissingJudgement(
                "need >= 2 judged records per class to calibrate; "
                f"have pos={len(pos)} neg={len(neg)}. Run build_judge_cache.")
        mu_n, sd_n = st.mean(neg), st.stdev(neg) or 1.0
        return cls(cache=cache, mu_neg=mu_n, sd_neg=sd_n,
                   d_prime=(st.mean(pos) - mu_n) / sd_n,
                   tau_det=tau_det, tag=tag)

    def score(self, item, now: int, seed: int) -> float:
        """Normalised score of the item's CONTENT.  Does NOT read `poisoned`.

        That is the entire point: `Detector` reads ground truth, this reads
        words.  If the two agree, the content channel carries nothing -- and
        that is a result, not a bug.
        """
        txt = item.content
        k = J.key(txt, self.tag)
        if k not in self.cache:
            k = J.key(_REV.sub("", txt), self.tag)
        if k not in self.cache:
            raise MissingJudgement(
                f"not judged: {txt[:48]!r}. Run build_judge_cache offline.")
        return (float(self.cache[k]) - self.mu_neg) / self.sd_neg

    def fires(self, score: float) -> bool:
        """PURE threshold, same contract as `Detector.fires`.

        No parameter through which ground truth can enter -- the score already
        came from the words alone.
        """
        return score > self.tau_det

    def score_patch(self, has_marker: bool, task_id: str, seed: int) -> float:
        """COMMIT channel -- delegated, because the judge reads notes not diffs.

        N3: never return 0.0 here.  With no delegate this RAISES, because a
        silent zero is exactly the fake zero the rule forbids.  When delegated,
        that channel's d' is a DECLARED value and must be reported separately
        from the MEASURED d' of the note channel.
        """
        if self.patch_detector is None:
            raise MissingJudgement(
                "LlmDetector does not score patches -- the judge reads memory "
                "notes, not diffs. Supply `patch_detector`, or register a "
                "separate patch judge and report its d' on its own.")
        return self.patch_detector.score_patch(has_marker, task_id, seed)

    def at_depth(self, depth: float):
        """Auditing deeper does not make a judge read better -- return SELF.

        `Detector.at_depth` scales d' by sqrt(depth), modelling "look harder,
        get more signal". Reading the same sentence again yields nothing more,
        and inheriting that boost silently would assert otherwise.

        This is a REAL DIFFERENCE from the synthetic detector, not an omission:
        a policy that buys depth gets no extra signal here, only the extra cost.
        Any comparison against `Detector` must state it.
        """
        return self
