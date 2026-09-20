"""D_lex -- detector noi dung TAT DINH, chi thu vien chuan.

Sau dac trung, khong cai nao doc "y nghia": dem token, do dai token trung
binh, ty le type/token, mat do dau cau, mat do chu so, va log-ty-le trigram
ky tu so voi lat KHOP THAM SO (khong phai lat cham diem).

DU DOAN DA CHOT TRUOC (spec SS4): D_lex ~ 0,5 tren dieu kien `covert`, vi
phan biet loi khuyen tot voi loi khuyen xau o do la viec ngu nghia.  Tren
`paired` thi D_lex se CAO, nhung khong phai vi no hieu -- vi lop tan cong tu
khai bao ("bo qua" AUC 0,997).

HANG RAO PARITY.  Khop tham so CHI tren `attacks.ESTIMATION_PARITY`, cham CHI
tren parity con lai.  Khong co hang rao thi D_lex hoc chinh tap no se cham, va
AUC cao vi ghi nho chu khong vi tin hieu.

SIEU THAM SO lay y het `analysis.discriminator._fit`: 600 buoc, lr 0,3.  Ly do
chep tu docstring cua no -- do duoc tren corpus 4500 dong, AUC giu rieng GIONG
NHAU toi bon chu so thap phan o 300, 600, 1200 va 3000 buoc, vi AUC chi phu
thuoc THU HANG, ma thu hang on dinh truoc trong so rat lau.
"""
from __future__ import annotations
import collections, math, re
import attacks

WORD = re.compile(r"\w+", re.UNICODE)
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
DIGIT = re.compile(r"\d")

COLS = ("n_tokens", "mean_token_len", "type_token_ratio",
        "punct_density", "digit_density", "trigram_llr")


def _trigrams(text: str) -> list:
    t = text.lower()
    return [t[i:i + 3] for i in range(max(0, len(t) - 2))]


def background(pos: list, neg: list) -> dict:
    """Log-ty-le trigram, uoc luong CHI tren lat khop tham so.

    Laplace smoothing: mot trigram chua thay o mot lop khong duoc cho ra
    log(0).  Uoc luong tren ca hai lop cua lat khop, khong bao gio cham lat
    cham diem -- do la hang rao parity, va trigram la cho de thung nhat.
    """
    cp, cn = collections.Counter(), collections.Counter()
    for t in pos:
        cp.update(_trigrams(t))
    for t in neg:
        cn.update(_trigrams(t))
    tp, tn = sum(cp.values()) or 1, sum(cn.values()) or 1
    keys = set(cp) | set(cn)
    return {g: math.log((cp[g] + 1) / (tp + len(keys)))
               - math.log((cn[g] + 1) / (tn + len(keys))) for g in keys}


def features(text: str, bg: dict) -> list:
    toks = WORD.findall(text)
    n = len(toks) or 1
    chars = len(text) or 1
    tg = _trigrams(text)
    llr = sum(bg.get(g, 0.0) for g in tg) / (len(tg) or 1)
    return [float(len(toks)),
            sum(len(t) for t in toks) / n,
            len(set(toks)) / n,
            len(PUNCT.findall(text)) / chars,
            len(DIGIT.findall(text)) / chars,
            llr]


def _standardise(rows: list) -> tuple:
    cols = list(zip(*rows))
    mu = [sum(c) / len(c) for c in cols]
    sd = [(sum((v - m) ** 2 for v in c) / len(c)) ** 0.5 or 1.0
          for c, m in zip(cols, mu)]
    return [[(v - m) / s for v, m, s in zip(r, mu, sd)] for r in rows], mu, sd


def _fit(X: list, y: list, steps: int = 600, lr: float = 0.3) -> tuple:
    w, b = [0.0] * len(COLS), 0.0
    for _ in range(steps):
        gw, gb = [0.0] * len(COLS), 0.0
        for xi, yi in zip(X, y):
            z = sum(wj * v for wj, v in zip(w, xi)) + b
            e = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z)))) - yi
            for j in range(len(COLS)):
                gw[j] += e * xi[j]
            gb += e
        n = len(X) or 1
        w = [wj - lr * g / n for wj, g in zip(w, gw)]
        b -= lr * gb / n
    return w, b


def auc(pos_scores: list, neg_scores: list) -> float:
    if not pos_scores or not neg_scores:
        return float("nan")
    import bisect
    sn = sorted(neg_scores)
    tot = 0.0
    for a in pos_scores:
        lo, hi = bisect.bisect_left(sn, a), bisect.bisect_right(sn, a)
        tot += lo + (hi - lo) / 2.0
    return tot / (len(pos_scores) * len(neg_scores))


def split_by_parity(rows: list) -> tuple:
    """(khop tham so, cham diem) theo CHI SO -- tat dinh, khong rut ngau nhien."""
    p = attacks.ESTIMATION_PARITY
    return ([r for i, r in enumerate(rows) if i % 2 == p],
            [r for i, r in enumerate(rows) if i % 2 != p])


def evaluate(pos: list, neg: list) -> dict:
    """Khop tren parity uoc luong, cham tren parity con lai.  Tra AUC + n."""
    pf, ps = split_by_parity(pos)
    nf, ns = split_by_parity(neg)
    if not (pf and nf and ps and ns):
        return {"auc": None, "reason": "mot trong bon lat rong"}
    bg = background(pf, nf)
    Xr = [features(t, bg) for t in pf] + [features(t, bg) for t in nf]
    y = [1.0] * len(pf) + [0.0] * len(nf)
    Xs, mu, sd = _standardise(Xr)
    w, b = _fit(Xs, y)

    def score(t):
        x = features(t, bg)
        z = [(v - m) / s for v, m, s in zip(x, mu, sd)]
        return sum(wj * v for wj, v in zip(w, z)) + b

    a = auc([score(t) for t in ps], [score(t) for t in ns])
    return {"auc": a, "n_fit_pos": len(pf), "n_fit_neg": len(nf),
            "n_score_pos": len(ps), "n_score_neg": len(ns),
            "fit_parity": attacks.ESTIMATION_PARITY,
            "weights": dict(zip(COLS, w))}
