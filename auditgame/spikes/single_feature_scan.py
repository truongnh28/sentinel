"""Quet TUNG DAC TRUNG DON LE giua hai lop, tim cai nao mot minh gan tach duoc.

SS12.6 cua TIEN-DANG-KY-Detector-Noi-Dung.md:

    Truoc khi cham bat ky cap lop nao: in vai mau moi lop, va do AUC cua TUNG
    dac trung don le.  Dac trung nao mot minh dat gan 1,0 la mot confound cho
    toi khi chung minh duoc dieu nguoc lai.

Phep kiem nay re hon moi cong trong van ban do, va tinh den 20/09 no da bat
duoc BON confound:

  1 `size`        PAYLOAD_LENGTH = 63 khop trung vi lanh tinh THEO THIET KE
  2 khuon corpus  muc lanh tinh do may ghep, payload la van xuoi
  3 marker        moi payload goi ten cung mot ham -> AUC 1,000
  4 ngoi thu nhat prose_pool 0,0% vs A1 46,7% / A2 83,3% -> AUC 0,733 / 0,917

Khong cai nao do ai co y tao ra.  Khong cai nao bi bat boi mot cong duoc
thiet ke de bat no.
"""
from __future__ import annotations
import collections, json, re, sys

WORD = re.compile(r"\w+", re.UNICODE)
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
DIGIT = re.compile(r"\d")
FIRST_PERSON = re.compile(r"\b(tôi|mình|chúng ta|ta nên|em)\b", re.IGNORECASE)


def auc(pos: list, neg: list) -> float:
    """AUC = P(diem duong > diem am), hoa nhau tinh 1/2.  Doi xung quanh 0,5."""
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
    """Do lech khoi 0,5, khong ke chieu -- mot dac trung tach NGUOC cung la
    confound.  0 = vo dung, 0,5 = tach hoan hao."""
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
    # Unigram: token nao mot minh tach manh nhat
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
    print("  -- token don le manh nhat --")
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
    print(f"\n{n} dac trung vuot nguong bao dong.")
    raise SystemExit(1 if n else 0)
