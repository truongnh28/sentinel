"""LlmDetector -- detector DOC NOI DUNG THAT, thay cho draw Gauss tong hop.

VI SAO CAN.  `Detector.score` doc DUY NHAT `item.poisoned` (su that nen) va
dung `item_id` lam HAT GIONG cho mot draw Gauss.  Noi dung chi doi HIEN THUC
HOA cua draw, khong doi KY VONG.  Nghia la khong co LLM nao thuc su dung
trong vong lap phong thu: d' la tham so quet, khong phai dai luong noi len tu
chu nghia.

Lop nay thay bang diem cua mot judge LLM doc `item.content`, lay tu CACHE
DONG BANG.  Offline-then-frozen: thieu khoa thi NEM, khong goi mang -- cung
ly do voi payload, vi `item_id = blake2b(content)` gieo hat cho phan con lai
cua he thong va LLM khong tat dinh ke ca o temperature 0.

CHUAN HOA.  Judge cham 0-10; `Detector` doi diem ~ N(d',1) duoi lop duong va
N(0,1) duoi lop am.  Ta chuan hoa bang trung binh/do lech cua LOP AM trong
cache (`_fit_from_cache`), nen thang do khop dung giao uoc cua `Detector`:
lop am ve quanh 0 voi do lech 1, va khoang cach hai lop chinh la d' THUC NGHIEM
cua judge -- khong con la tham so ta tu dat.

CANH BAO PHAM VI.  Muc lanh tinh TRONG TRO CHOI hien do `agent.py` sinh ra
bang bon khuon (`[topic] ghi chu tu <id>`, `commit`, ...).  Cho judge doc
chung thi no tach duoc ngay bang cach dem tu -- confound thu hai cua
20/09, nguyen ven.  Nen lop nay CHI co nghia tren mot the gioi tro choi bang
VAN XUOI; dung no tren the gioi mac dinh se cho d' cao gia tao.  Xem
TIEN-DANG-KY-Detector-Noi-Dung.md SS3.3.
"""
from __future__ import annotations
import statistics as st
from dataclasses import dataclass

from analysis import content_judge as J


class MissingJudgement(J.MissingJudgement):
    pass


@dataclass
class LlmDetector:
    """Giao dien tuong thich `Detector`, nhung diem den TU NOI DUNG."""

    cache: dict
    mu_neg: float
    sd_neg: float
    d_prime: float
    tau_det: float = 0.0
    tag: str = "default"

    @classmethod
    def from_cache(cls, pos_texts: list, neg_texts: list,
                   tag: str = "default", tau_det: float = 0.0):
        """Hieu chuan thang do tren HAI LOP DA CHAM san.

        d' duoc TINH RA tu cache, khong duoc dat vao.  Do la toan bo diem khac
        biet so voi `Detector`.
        """
        cache = J.load_cache()
        pos = [J.score(t, cache, tag) for t in pos_texts if J.key(t, tag) in cache]
        neg = [J.score(t, cache, tag) for t in neg_texts if J.key(t, tag) in cache]
        if len(pos) < 2 or len(neg) < 2:
            raise MissingJudgement(
                "can >= 2 ban ghi da cham moi lop de hieu chuan; "
                f"co pos={len(pos)} neg={len(neg)}. Chay build_judge_cache.")
        mu_n, sd_n = st.mean(neg), st.stdev(neg) or 1.0
        d = (st.mean(pos) - mu_n) / sd_n
        return cls(cache=cache, mu_neg=mu_n, sd_neg=sd_n, d_prime=d,
                   tau_det=tau_det, tag=tag)

    def score(self, item, now: int, seed: int) -> float:
        """Diem CHUAN HOA cua noi dung item.  KHONG doc `item.poisoned`.

        Do la ca y nghia cua lop nay: `Detector` doc su that nen, lop nay doc
        chu.  Neu hai lop cho cung ket qua thi kenh noi dung khong mang gi --
        va do la mot ket qua, khong phai mot loi.
        """
        k = J.key(item.content, self.tag)
        if k not in self.cache:
            raise MissingJudgement(
                f"chua cham: {item.content[:48]!r}. Chay build_judge_cache offline.")
        return (float(self.cache[k]) - self.mu_neg) / self.sd_neg

    def score_patch(self, has_marker: bool, task_id: str, seed: int) -> float:
        """N3: judge cham GHI CHU, khong cham ban va.  Ghi ly do, khong tra 0.0."""
        raise MissingJudgement(
            "LlmDetector khong cham patch -- judge doc ghi chu bo nho, khong doc "
            "diff. Dung Detector tong hop cho kenh commit, hoac dang ky mot judge "
            "rieng cho patch va ghi d' cua no rieng.")

    def deeper(self, depth: float):
        """Audit sau hon khong lam judge doc gioi hon -- tra ve CHINH NO.

        `Detector.deeper` nhan d' len theo sqrt(depth) vi no mo hinh hoa "nhin
        ky hon thi tin hieu manh hon".  Voi mot judge doc chu, doc lai cung mot
        cau khong cho them thong tin nao.  Ghi ro thay vi im lang ke thua.
        """
        return self
