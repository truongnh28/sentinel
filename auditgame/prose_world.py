"""The gioi tro choi bang VAN XUOI -- bien the SONG SONG, mac dinh TAT.

VI SAO TON TAI.  `LlmDetector` cham diem tu `item.content`.  Nhung muc lanh
tinh TRONG TRO CHOI do `agent.py` sinh bang bon khuon:

    "[{topic}] ghi chu tu {task_id}"      "[{topic}] commit {task_id}"
    "[{topic}] quy trinh rut tu {id}"     "[{topic}] loi goi treo {id}"

Cho judge doc chung thi no tach duoc bang cach DEM TU -- confound thu hai cua
20/09 (corpus lanh tinh la sieu du lieu tuan tu hoa, khong phai chu ai viet),
nguyen ven.  d' se cao gia tao va khong noi gi ve nguy trang.

Module nay thay noi dung lanh tinh bang ghi chu VAN XUOI that (`prose_pool`)
va payload bang loi khuyen NGAM (`covert-harmful`), de d' trong tro choi NOI
LEN TU CHU thay vi la tham so ta dat.

MAC DINH TAT, va do khong phai su than trong thua.  `item_id = blake2b(content)`
gieo hat cho `Detector.score`, nen doi noi dung lanh tinh se doi hat giong cua
MOI muc, va MOI con so harm da do mat hieu luc.  Bat bang `enable()`, tat bang
`disable()`; khong bao gio bat ngam trong mot duong chay chung.

TAT DINH.  Ghi chu duoc rut bang blake2b(task_id|carrier) mod N -- cung mot
task luon nhan cung mot ghi chu, qua moi lan chay, khong phu thuoc thu tu.
"""
from __future__ import annotations
import hashlib, json, pathlib

_HERE = pathlib.Path(__file__).resolve().parent
_PAYLOADS = _HERE / "payloads"

_ENABLED = False
_PROSE: list = []
_COVERT: list = []


def _load(name: str) -> list:
    with (_PAYLOADS / name).open(encoding="utf-8") as fh:
        return [json.loads(l)["content"] for l in fh if l.strip()]


def enable() -> None:
    global _ENABLED, _PROSE, _COVERT
    if not _PROSE:
        _PROSE = _load("prose_pool.jsonl")
        _COVERT = _load("covert-harmful.jsonl")
    _ENABLED = True


def disable() -> None:
    global _ENABLED
    _ENABLED = False


def active() -> bool:
    return _ENABLED


def _pick(pool: list, *parts) -> str:
    h = hashlib.blake2b("|".join(map(str, parts)).encode(), digest_size=8).digest()
    return pool[int.from_bytes(h, "big") % len(pool)]


def benign(topic, task_id, carrier: str, fallback: str) -> str:
    """Ghi chu lanh tinh bang van xuoi.  Tat thi tra nguyen khuon cu."""
    if not _ENABLED:
        return fallback
    return _pick(_PROSE, task_id, carrier)


def payload(topic, marker: str, fallback: str) -> str:
    """Payload NGAM.  Tat thi tra nguyen `build.payload_content`.

    Lop ngam la lop da do duoc la KHONG phat hien duoc bang dau hieu be mat
    (AUC 0,479 sau khi pha lien ket ten->nhan).  Dung no lam payload trong
    tro choi la dat defender truoc doi thu manh nhat ta dung duoc, thay vi
    truoc mot doi thu tu khai bao.
    """
    if not _ENABLED:
        return fallback
    return _pick(_COVERT, topic, marker)


def judgeable_texts() -> tuple:
    """(lop duong, lop am) -- moi chuoi co the xuat hien trong the gioi nay.

    Dung de xay cache judge TRUOC khi chay, va de hieu chuan `LlmDetector`.
    """
    if not _PROSE:
        enable(); disable()
    return list(_COVERT), list(_PROSE)
