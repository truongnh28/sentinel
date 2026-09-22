"""Scan EVERY SINGLE FEATURE between two classes, looking for one that alone
nearly separates them.

docs/preregistration/TIEN-DANG-KY-Detector-Noi-Dung.md section 12.6:

    Before scoring any pair of classes: print a few samples of each, and
    measure the AUC of EVERY SINGLE FEATURE. Any feature that alone reaches
    close to 1.0 is a confound until proven otherwise.

This check is cheaper than every gate in that document, and as of 2026-09-20 it
has caught SEVEN confounds, none of which anyone put there on purpose:

  1 size          PAYLOAD_LENGTH = 63 matches the benign median BY DESIGN
  2 corpus shape  benign items are assembled by a machine; payloads are prose
  3 marker        every payload names the same function       -> AUC 1.000
  4 first person  0.0% on one side against 47-83% on the other -> 0.733/0.917
  5 prompt asymmetry  two prompts leave two fingerprints       -> 0.956
  6 naming convention the held-out half held out NAMES, not the CONVENTION
  7 note genre    the negative class differs in KIND of advice, not in harm

Four of the seven were caught by this file. The other three were caught by
reading raw samples, which is the same discipline one step earlier.
"""
from __future__ import annotations
import collections, json, re, sys

WORD = re.compile(r"\w+", re.UNICODE)
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
DIGIT = re.compile(r"\d")
FIRST_PERSON = re.compile(r"\b(tôi|mình|chúng ta|ta nên|em)\b", re.IGNORECASE)


def auc(pos: list, neg: list) -> float:
    """AUC = P(positive score > negative score), ties at 1/2. Symmetric about 0.5."""
    if not pos or not neg:
        return float("nan")
    sn = sorted(neg)
    import bisect
    tot = 0.0
    for a in pos:
        lo = bisect.bisect_left(sn, a)
        hi = bisect.bisect_right(sn, a)
        tot += lo + (hi - lo) / 2.0
    return tot / (len(pos) * len(neg))


def sym(a: float) -> float:
    """Distance from 0.5, ignoring direction -- a feature that separates the
    WRONG WAY is a confound too. 0 = useless, 0.5 = perfect separation."""
    return abs(a - 0.5)


FEATURES = {
    "len_chars": lambda t: float(len(t)),
    "n_tokens": lambda t: float(len(WORD.findall(t))),
    "mean_token_len": lambda t: (sum(len(w) for w in WORD.findall(t))
                                 / max(len(WORD.findall(t)), 1)),
    "type_token_ratio": lambda t: (len(set(WORD.findall(t)))
                                   / max(len(WORD.findall(t)), 1)),
    "punct_density": lambda t: len(PUNCT.findall(t)) / max(len(t), 1),
    "digit_density": lambda t: len(DIGIT.findall(t)) / max(len(t), 1),
    "first_person": lambda t: 1.0 if FIRST_PERSON.search(t) else 0.0,
    "has_colon": lambda t: 1.0 if ":" in t else 0.0,
    "has_backtick": lambda t: 1.0 if "`" in t else 0.0,
    "has_parens": lambda t: 1.0 if "(" in t else 0.0,
    "starts_bracket": lambda t: 1.0 if t.startswith("[") else 0.0,
    "n_commas": lambda t: float(t.count(",")),
    "ends_period": lambda t: 1.0 if t.rstrip().endswith(".") else 0.0,
    "upper_ratio": lambda t: sum(c.isupper() for c in t) / max(len(t), 1),
}


def scan(pos: list, neg: list, top_tokens: int = 12) -> dict:
    out = {"n_pos": len(pos), "n_neg": len(neg), "features": {}, "tokens": {}}
    for name, f in FEATURES.items():
        out["features"][name] = auc([f(t) for t in pos], [f(t) for t in neg])
    # Unigrams: which single token separates hardest on its own
    vocab = collections.Counter()
    for t in pos + neg:
        vocab.update(set(w.lower() for w in WORD.findall(t)))
    cand = [w for w, n in vocab.items() if n >= 5]
    scored = []
    for w in cand:
        a = auc([1.0 if w in t.lower() else 0.0 for t in pos],
                [1.0 if w in t.lower() else 0.0 for t in neg])
        scored.append((sym(a), a, w))
    scored.sort(reverse=True)
    out["tokens"] = [{"token": w, "auc": a} for _, a, w in scored[:top_tokens]]
    return out


def report(tag: str, res: dict, alarm: float = 0.20) -> int:
    print(f"=== {tag}  (n+={res['n_pos']}, n-={res['n_neg']}) ===")
    rows = sorted(res["features"].items(), key=lambda kv: -sym(kv[1]))
    n_alarm = 0
    for name, a in rows:
        flag = ""
        if sym(a) >= alarm:
            flag = "  <-- CONFOUND"
            n_alarm += 1
        print(f"  {name:<20} AUC {a:.3f}{flag}")
    print("  -- strongest single tokens --")
    for row in res["tokens"][:6]:
        flag = "  <-- CONFOUND" if sym(row["auc"]) >= alarm else ""
        if flag:
            n_alarm += 1
        print(f"  {row['token']:<20} AUC {row['auc']:.3f}{flag}")
    return n_alarm


def load(path: str) -> list:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l)["content"] for l in fh if l.strip()]


if __name__ == "__main__":
    pos, neg = load(sys.argv[1]), load(sys.argv[2])
    n = report(f"{sys.argv[1]} vs {sys.argv[2]}", scan(pos, neg))
    print(f"\n{n} features over the alarm threshold.")
    raise SystemExit(1 if n else 0)
