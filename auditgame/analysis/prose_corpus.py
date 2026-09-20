"""Nap cac corpus noi dung va cap hoa chung, KHONG goi API.

VI SAO KHONG DUNG `matched_corpus`.  Ham do tra ve F_match feature dict va bi
rang buoc boi cap su kien cua gate-2 (screen 80 / certify 900).  Spec SS6 chot
rang detector noi dung cham NGOAI khung do, vi hai ly do.  Mot, SS3.3:
detector nay khong noi vao tro choi, nen khong co ly do bam cap su kien cua
tro choi.  Hai, cong suat: o (900, 900) be rong CI95 la 0,0534 > delta = 0,05
-- duong thoat cong suat KHONG di qua duoc bang chinh may moc cua gate-2; o
(660, 2294) be rong la 0,050.  Noi n_am re hon noi n_duong.

BA CAP LOP, ba cau hoi khac nhau -- do la ly do chung ton tai rieng:

  "prose"   payload A0/A1/A2  vs  prose_pool
            DA DO LA HONG.  prose_pool den tu mot quy trinh sinh khac, va
            tach duoc o punct_density 0,83-0,88 / mean_token_len 0,85-0,88
            NGAY CA KHI ca hai lop deu an toan (cong A: 0,956 / 0,854).
            Giu lai lam CHUNG CU cho ket luan do, khong phai de do.

  "paired"  co hai TU KHAI BAO  vs  an toan, sinh trong CUNG MOT lenh goi
            Van phong da bi xoa: moi dac trung be mat 0,46-0,55.  Con lai
            thuan la tu vung mang nghia: "bo qua" 0,997.

  "covert"  co hai DO HAM Y  vs  an toan, CAP TOI THIEU khac dung TEN HAM
            Tu vung khong con tach duoc.  Phat hien doi hoi BIET ham nao
            khong an toan -- tri thuc ve the gioi, khong phai dau hieu be mat.
"""
from __future__ import annotations
import json, os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PAYLOADS = os.path.join(os.path.dirname(_HERE), "payloads")

CONDITIONS = {
    "prose_a0": ("a0-advice.jsonl", "prose_pool.jsonl"),
    "prose_a1": ("a1-advice.jsonl", "prose_pool.jsonl"),
    "prose_a2": ("a2-advice.jsonl", "prose_pool.jsonl"),
    "gate_a": ("safe-advice.jsonl", "prose_pool.jsonl"),
    "paired": ("paired-harmful.jsonl", "paired-safe.jsonl"),
    "covert": ("covert-harmful.jsonl", "covert-safe.jsonl"),
}


def _read(name: str) -> list:
    path = os.path.join(_PAYLOADS, name)
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def texts(name: str) -> list:
    """Noi dung PHAN BIET, thu tu tat dinh."""
    seen, out = set(), []
    for row in _read(name):
        c = row["content"]
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def pair(condition: str) -> tuple:
    pos_f, neg_f = CONDITIONS[condition]
    return texts(pos_f), texts(neg_f)


def n_eff(condition: str) -> int:
    """So ban ghi PHAN BIET o lop duong -- khong phai so su kien.

    Ton tai thanh mot ham rieng de moi cho goi phai noi ro no dem cai gi.  O
    pha certify cu, 900 diem duong den tu <= 30 payload phan biet
    (mean_reuse_per_record = 2,67); coi phep lap la phep do doc lap chinh la
    loi ma SS7.5 tu cam.
    """
    return len(pair(condition)[0])


def heldout_split(condition: str) -> tuple:
    """(trong-lop, giu-rieng) cho dieu kien `covert`.

    Mot nua ten khong an toan chi xuat hien o nua giu rieng.  Mot D_lex hoc
    thuoc danh sach ten se sap o nua nay; mot detector hieu nghia thi khong.
    Do la toan bo ly do nua nay ton tai.
    """
    pos_f, neg_f = CONDITIONS[condition]
    ph, pn = _read(pos_f), _read(neg_f)
    fit = ([r["content"] for r in ph if not r.get("heldout")],
           [r["content"] for r in pn if not r.get("heldout")])
    held = ([r["content"] for r in ph if r.get("heldout")],
            [r["content"] for r in pn if r.get("heldout")])
    return fit, held
