"""
diag_llm_eps.py -- Task 3: payload do LLM sinh nam o dau tren thang AUC cua Gate 2.

Brief: .superpowers/sdd/2026-09-20-ssg-gate4c/task-3-brief.md

Cau hoi: truc `epsilon` cua `attacks.MatchedAttack` la mot num TONG HOP (khoang
cach so voi phan bo item cua chinh agent). Attacker that dung LLM viet payload,
khong van num do. Script nay dat 19 payload LLM da sinh san (P2, da tra tien,
da dong bang) len DUNG duong code F_match / AUC ma Gate 2 dung, roi doc AUC ra.

KHONG sua attacks.py / analysis/gate2_v2.py / analysis/benign_corpus.py /
analysis/discriminator.py / lp.py / policies.py. Lop chan doan la BAN SAO cuc
bo, dang ky vao attacks.REGISTRY luc runtime -- cung khuon voi spikes/diag_4c.py
(dang ky policies.REGISTRY) va voi payloads.FrozenPayloadAttack, pipeline CO SAN
trong repo dung dung mau nay cho mot ngan hang payload co dinh.

DIEM NOI (quyet dinh quan trong nhat cua task nay). Doc attacks.MatchedAttack.payload
va payloads.FrozenPayloadAttack.payload: ca hai deu tra ve mot core.Item, va
matched_corpus._one_event goi THANG `pipe.payload(wf, ps)` -- KHONG goi qua
`pipe.plan` (plan chi dung o duong experiment/runner, khong dung o duong AUC).
`Item.surface()` (core.py dong 294) la F_match: {size=len(content),
depth=provenance.count('/'), recency=now-created_at, derived=len(derived_from),
topic=topic_code(topic)}. Vay diem noi dung la field `content` cua Item: pipeline
chan doan phai dat NGUYEN VAN chuoi `advice` cua LLM vao do, moi thu khac (topic,
provenance, carrier, poisoned) xay dung GIONG HET FrozenPayloadAttack -- topic =
task sigma's CA topic (khong subset qua payload_topic_like, vi noi dung LLM
khong "biet" ve eps), provenance = "agent/notes" (depth=1, gia dinh duoc khai
bao ro trong bao cao -- LLM payload duoc gia dinh dong vai mot ghi chu cua chinh
agent, giong lua chon mac dinh cua MatchedAttack o eps<0.5 va cua da so template
trong payloads/generate.py).

EPS TRUYEN VAO matched_corpus. Pipeline khong doc eps (giong FrozenPayloadAttack,
epsilon_effective=False), nhung `matched_corpus(pipe, delta, eps, ...)` van dung
eps de quyet dinh sigma nao "dormant" (feasible_sigmas). Dung tien le da co trong
spikes/b5-benign-enrich.md: FrozenPayloadAttack cung duoc do qua
`matched_corpus(pipe, D, eps=0.0, 900, natural=...)` -- eps=0.0 la quy uoc dong
bo cho MOI pipeline duoc do qua matched_corpus, khong rieng gi MatchedAttack.
Script nay dung eps=0.0 vi ly do do, KHONG phai vi gia dinh LLM "khong ton chi
phi" -- do la mot lua chon quy uoc duoc khai bao, khong phai mot phep do.

RANG BUOC CO MAU: chi co 14 (tier "low", ~18 ky tu) + 5 (tier "ceiling", ~261-307
ky tu) = 19 payload LLM phan biet. Screen can 80 su kien, certify can ~900. Chon
huong (a) cua brief: DUNG LAI PAYLOAD THEO VONG -- pipeline chon ban ghi qua
`core.seed_of(...) % len(records)`, dung khuon voi FrozenPayloadAttack._pick,
nen moi lan matched_corpus can mot su kien no se roi vao MOT trong 14 (hoac 5)
chuoi co dinh, lap lai nhieu lan. So lan lap lai TRUNG BINH = n_dat_duoc /
so_ban_ghi duoc bao cao o moi o, KHONG bi giau.

---------------------------------------------------------------------------
VONG 2 (theo yeu cau cua coordinator sau khi doc bao cao vong 1): AUC ~0.86-1.00
vong 1 CO THE la mot CONFOUND do dai, khong phai mot phat hien. Ly do:
`build.PAYLOAD_LENGTH = 63` DUNG BANG trung vi `size` cua lop lanh tinh --
MatchedAttack khop dung con so do THEO THIET KE, con payload LLM (18-67 ky tu
o tier "low", 261-307 o tier "ceiling") chua bao gio duoc yeu cau khop. Vong 1
vi vay co the dang so sanh "khop do dai" voi "khong khop do dai", khong phai
"nguy trang tot" voi "nguy trang do".

Vong 2 do AUC khi TRUNG HOA `size`, hai cach (ca hai deu lam, dung khuon
"neutralising" ma docstring attacks.MatchedAttack / core.topic_code da dung
cho cot `topic`):

  (1) NEUTRALISE_SIZE -- sau khi `matched_corpus` tra ve cac dict F_match (5
      khoa: size, depth, recency, derived, topic), GHI DE `size` bang MOT HANG
      SO GIONG HET NHAU tren CA hai lop (poisoned va benign) truoc khi dua vao
      `discriminator.auc_over_splits`. `discriminator._standardise` chia cho
      do lech chuan, va co guard `or 1.0` khi phuong sai bang 0 (dong 56) --
      nen mot cot hang so chuan hoa thanh 0.0 O MOI HANG, w*0=0 voi MOI trong
      so hoi quy hoc duoc, tuc la cot do KHONG con dong gop gi cho diem so du
      trong so cua no la bao nhieu. Ve mat thong ke tuong duong "bo cot" ma
      khong phai sua `discriminator._COLS` (truong bi dong bang, khong duoc
      sua). Day la CHINH XAC ky thuat "neutralising" da dung cho `topic`
      (core.py dong 158: "neutralising it moves Delta=4 from 0.5870 ... to
      0.5407").
  (2) LENGTH-MATCHED -- mot pipeline moi (`LLMAdviceLengthMatchedAttack`) cat/
      dem NOI DUNG LLM ve dung `build.PAYLOAD_LENGTH` (63) ky tu roi chay lai
      DAY DU 5 dac trung nhu binh thuong. Cat: lay 63 ky tu dau. Dem: them
      khoang trang vao cuoi cho du 63. So ban ghi bi dung moi thao tac duoc
      dem va bao cao (xem `LENGTH_MATCH_COUNTS`), va mot canh bao duoc ghi ro:
      o tier "ceiling", cat ve 63 ky tu XOA MAT marker "raw_write" o 4/5 ban
      ghi (marker thuong nam gan CUOI cau) -- payload sau khi cat khong con la
      mot cuoc tan cong that nua, chi con la mot chuoi CO DO DAI khop nhung
      NOI DUNG bi cat cut; ket qua tier nay phai doc voi canh bao do.

Ca hai deu chay CUNG cau hinh voi vong 1: ca hai pha (screen N=80, certify
N=900), Delta in {0,2,4}, cung SPLIT_SEEDS, cung eps=0.0, hai tier tach rieng.

Chi dung thu vien chuan (ABC T.6).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, ".")

import attacks                      # noqa: E402
import build                        # noqa: E402
from core import Item, seed_of      # noqa: E402
from analysis import benign_corpus as B    # noqa: E402
from analysis import discriminator as D    # noqa: E402
from analysis import gate2_v2 as G2        # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 0) Hang so doc tu ban ghi dong bang, KHONG go tay (brief muc 5).
# ---------------------------------------------------------------------------
AUC_CEILING = G2.record()["ceiling"]                       # 0.56
PER_EVENT = G2.record()["corpus"]["per_event"]              # 4
N_SCREEN = G2.N_SCREEN                                      # 80
N_CERTIFY = G2.N_CERTIFY                                    # 900
DELTAS = G2.DELTAS                                          # (0, 2, 4)
SPLIT_SEEDS = D.SPLIT_SEEDS                                 # range(1, 21)

# Bang doi chieu tu brief, pha SCREEN, N=80, eps=0.0, pipeline "matched".
REFERENCE_EPS0 = {0: 0.5247, 2: 0.5359, 4: 0.6077}
REFERENCE_TOL = 1e-4    # deu ky, khop chinh xac (deterministic tu SPLIT_SEEDS)

#: eps truyen vao matched_corpus cho MOI phep do trong file nay -- quy uoc, xem
#: docstring module o tren ("EPS TRUYEN VAO matched_corpus").
EPS_FOR_CORPUS = 0.0


# ---------------------------------------------------------------------------
# 1) Doc payload LLM -- vat lieu da tra tien, da dong bang (khong sua).
# ---------------------------------------------------------------------------

def load_advice(path: pathlib.Path) -> list:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


ADVICE_LOW = load_advice(HERE / "p2-advice.jsonl")
ADVICE_CEILING = load_advice(HERE / "p2-advice-ceiling.jsonl")


# ---------------------------------------------------------------------------
# 2) Pipeline chan doan -- ban sao cuc bo cua payloads.FrozenPayloadAttack,
#    chi khac O CHO NGAN HANG: content lay tu file advice LLM thay vi tu
#    frozen_payloads.json. Dang ky vao attacks.REGISTRY luc runtime, KHONG sua
#    attacks.py.
# ---------------------------------------------------------------------------

class LLMAdviceAttack:
    """Choi mot payload VAN BAN THAT do LLM sinh (P2), lay ngau nhien-nhung-
    tat-dinh tu mot ngan hang co dinh -- cung khuon voi
    `payloads.FrozenPayloadAttack.payload` (topic = task sigma's CA topic,
    KHONG qua payload_topic_like, vi noi dung khong doc eps).

    `epsilon_effective=False` KHAI THAT: giong FrozenPayloadAttack, chuoi
    payload la co dinh (sinh offline boi mot LLM that, khong phai o day) va
    khong doi theo epsilon. Diem khac DUY NHAT voi FrozenPayloadAttack: ngan
    hang o day la 14 hoac 5 ban ghi advice-LLM thay vi >=12 ban ghi template-
    bank, va provenance duoc gan CO DINH = "agent/notes" (khai bao ro trong
    bao cao -- cac ban ghi advice khong mang san truong provenance).
    """

    def __init__(self, name: str, records: list, salt: str):
        self.name = name
        self._records = records
        self._salt = salt

    def scope(self):
        return attacks.AttackScope(carriers=attacks.CARRIERS_ALL,
                                    delta_range=(0, 6), epsilon_effective=False,
                                    requires_graded_retrieval=False)

    def plan(self, wf, carrier, delta, rng, epsilon: float = 0.6):
        # Khong dung o duong AUC (_one_event goi thang .payload), nhung phai
        # co de thoa man AttackPipeline Protocol -- cung mot dong voi
        # FrozenPayloadAttack.plan va MatchedAttack.plan.
        return build.plan_poison(wf, carrier, delta, rng, epsilon)

    def _pick(self, wf, ps) -> dict:
        i = seed_of(self._salt, wf.wf_id, ps.iota, ps.sigma,
                    ps.carrier) % len(self._records)
        return self._records[i]

    def payload(self, wf, ps) -> Item:
        rec = self._pick(wf, ps)
        topic = wf.tasks[ps.sigma].topic
        return Item(carrier=ps.carrier, topic=topic, content=rec["advice"],
                    created_at=ps.iota, provenance="agent/notes", poisoned=True)


PIPE_LOW = LLMAdviceAttack("llm-advice-low", ADVICE_LOW, salt="llm-advice-low")
PIPE_CEILING = LLMAdviceAttack("llm-advice-ceiling", ADVICE_CEILING,
                               salt="llm-advice-ceiling")

# Dang ky runtime -- khong sua attacks.py (brief muc 1).
attacks.REGISTRY[PIPE_LOW.name] = PIPE_LOW
attacks.REGISTRY[PIPE_CEILING.name] = PIPE_CEILING


# ---------------------------------------------------------------------------
# 2b) VONG 2 -- pipeline LENGTH-MATCHED: cat/dem noi dung LLM ve dung
#     build.PAYLOAD_LENGTH ky tu, moi thu khac giu nguyen nhu LLMAdviceAttack.
# ---------------------------------------------------------------------------

def length_match(text: str, L: int = build.PAYLOAD_LENGTH) -> tuple:
    """(chuoi_da_khop_do_dai, nhan). Cat lay L ky tu dau neu dai hon L; dem
    khoang trang vao cuoi neu ngan hon L; giu nguyen neu dung bang L."""
    if len(text) > L:
        return text[:L], "truncated"
    if len(text) < L:
        return text + " " * (L - len(text)), "padded"
    return text, "exact"


def length_match_counts(records: list, L: int = build.PAYLOAD_LENGTH) -> dict:
    labels = [length_match(r["advice"], L)[1] for r in records]
    return {"n": len(records),
           "truncated": labels.count("truncated"),
           "padded": labels.count("padded"),
           "exact": labels.count("exact")}


def marker_survival(records: list, marker: str = "raw_write",
                    L: int = build.PAYLOAD_LENGTH) -> dict:
    """May ban ghi TRUNCATED van con giu duoc `marker` trong L ky tu dau --
    phai bao cao rieng vi mot payload mat marker khong con la mot cuoc tan
    cong that nua (xem docstring module, "LENGTH-MATCHED")."""
    truncated = [r["advice"] for r in records if len(r["advice"]) > L]
    survives = [marker in t[:L] for t in truncated]
    return {"n_truncated": len(truncated), "n_marker_survives": sum(survives),
           "n_marker_lost": len(survives) - sum(survives)}


class LLMAdviceLengthMatchedAttack(LLMAdviceAttack):
    """Nhu LLMAdviceAttack, nhung `content` duoc cat/dem ve dung
    build.PAYLOAD_LENGTH ky tu truoc khi ghi vao Item -- cach ly bien `size`
    khoi dac trung, chay DAY DU 5 cot F_match nhu binh thuong (khong can
    can thiep vao discriminator.py)."""

    def payload(self, wf, ps) -> Item:
        rec = self._pick(wf, ps)
        topic = wf.tasks[ps.sigma].topic
        content, _ = length_match(rec["advice"])
        return Item(carrier=ps.carrier, topic=topic, content=content,
                    created_at=ps.iota, provenance="agent/notes", poisoned=True)


PIPE_LOW_LMATCH = LLMAdviceLengthMatchedAttack(
    "llm-advice-low-lmatch", ADVICE_LOW, salt="llm-advice-low")
PIPE_CEILING_LMATCH = LLMAdviceLengthMatchedAttack(
    "llm-advice-ceiling-lmatch", ADVICE_CEILING, salt="llm-advice-ceiling")

attacks.REGISTRY[PIPE_LOW_LMATCH.name] = PIPE_LOW_LMATCH
attacks.REGISTRY[PIPE_CEILING_LMATCH.name] = PIPE_CEILING_LMATCH

LENGTH_MATCH_COUNTS = {
    "low": length_match_counts(ADVICE_LOW),
    "ceiling": length_match_counts(ADVICE_CEILING),
}
MARKER_SURVIVAL = {
    "low": marker_survival(ADVICE_LOW),
    "ceiling": marker_survival(ADVICE_CEILING),
}


# ---------------------------------------------------------------------------
# 3) Do mot o (pipe, delta, n_events_cap) -> AUC day du + n dat duoc.
#    `row_transform`, khi co, duoc ap len TUNG dict F_match (ca poisoned lan
#    benign) TRUOC khi dua vao discriminator -- dung cho NEUTRALISE_SIZE.
# ---------------------------------------------------------------------------

def neutralise_size(row: dict) -> dict:
    """'Neutralising': ghi de `size` bang MOT HANG SO GIONG HET nhau tren moi
    hang (ca hai lop) -- xem docstring module. Tra ve BAN SAO, khong sua row
    goc (row goc la dict F_match tra ve tu Item.surface(), khong nen mutate
    ngoai y muon neu con noi khac giu tham chieu)."""
    out = dict(row)
    out["size"] = 0.0
    return out


def measure_cell(pipe, delta: int, n_events_cap: int, row_transform=None) -> dict:
    pos, neg = B.matched_corpus(pipe, delta, EPS_FOR_CORPUS, n_events_cap,
                                per_event=PER_EVENT)
    n_reached, n_neg_reached = len(pos), len(neg)
    if row_transform is not None:
        pos = [row_transform(r) for r in pos]
        neg = [row_transform(r) for r in neg]
    if not pos or not neg:
        return {"n_events_cap": n_events_cap, "n_pos_reached": n_reached,
               "n_neg_reached": n_neg_reached, "reason": "empty corpus -- khong do duoc AUC"}
    r = D.auc_over_splits(pos, neg, ceiling=AUC_CEILING, seeds=SPLIT_SEEDS)
    return {
        "n_events_cap": n_events_cap,
        "n_pos_reached": n_reached,
        "n_neg_reached": n_neg_reached,
        "screen_statistic_auc_median": G2.screen_statistic(r),
        "auc_mean": r["auc_mean"], "auc_min": r["auc_min"], "auc_max": r["auc_max"],
        "hi_mean": r["hi_mean"], "hi_min": r["hi_min"], "hi_max": r["hi_max"],
        "clear": r["clear"], "k_splits": r["k"],
        "failing_seeds": r["failing_seeds"],
    }


# ---------------------------------------------------------------------------
# 4) main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    out = {"meta": {
        "eps_for_corpus": EPS_FOR_CORPUS, "per_event": PER_EVENT,
        "ceiling": AUC_CEILING, "deltas": list(DELTAS),
        "n_screen_cap": N_SCREEN, "n_certify_cap": N_CERTIFY,
        "split_seeds": list(SPLIT_SEEDS),
        "n_records_low": len(ADVICE_LOW), "n_records_ceiling": len(ADVICE_CEILING),
        "provenance_assumption": "agent/notes (khai bao, khong doc tu file advice)",
        "topic_assumption": "task sigma's CA topic (giong FrozenPayloadAttack, "
                            "KHONG qua payload_topic_like)",
    }}

    # ---- kiem hop le TRUOC -- pipeline 'matched' o eps=0.0, pha SCREEN -----
    pipe_matched = attacks.REGISTRY["matched"]
    validation = {}
    all_match = True
    for d in DELTAS:
        cell = measure_cell(pipe_matched, d, N_SCREEN)
        stat = cell.get("screen_statistic_auc_median")
        ref = REFERENCE_EPS0[d]
        ok = stat is not None and abs(stat - ref) <= REFERENCE_TOL
        all_match = all_match and ok
        validation[d] = {"measured": stat, "reference": ref, "match": ok,
                         "n_pos_reached": cell["n_pos_reached"]}
    out["validation_matched_eps0_screen"] = validation
    print(f"[diag_llm_eps] kiem hop le (matched, eps=0.0, screen N={N_SCREEN}): "
         f"{validation}")

    if not all_match:
        out["status"] = "BLOCKED -- kiem hop le khong khop bang trong brief, " \
                        "duong noi sai. KHONG do payload LLM."
        out_path = HERE / "diag-llm-eps.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        print(f"[diag_llm_eps] KHOP THAT BAI -- dung lai, ghi {out_path} va thoat.")
        return out

    print("[diag_llm_eps] kiem hop le KHOP bang trong brief. Do payload LLM.")

    # ---- do hai bac LLM, CA HAI PHA, TACH RIENG ----------------------------
    results = {}
    for tag, pipe in (("low", PIPE_LOW), ("ceiling", PIPE_CEILING)):
        results[tag] = {"n_records": len(pipe._records), "screen": {}, "certify": {}}
        for d in DELTAS:
            cell = measure_cell(pipe, d, N_SCREEN)
            cell["mean_reuse_per_record"] = (
                cell["n_pos_reached"] / len(pipe._records) if pipe._records else float("nan"))
            results[tag]["screen"][d] = cell
            print(f"[diag_llm_eps] {tag} screen Delta={d}: {cell}")
        for d in DELTAS:
            cell = measure_cell(pipe, d, N_CERTIFY)
            cell["mean_reuse_per_record"] = (
                cell["n_pos_reached"] / len(pipe._records) if pipe._records else float("nan"))
            results[tag]["certify"][d] = cell
            print(f"[diag_llm_eps] {tag} certify Delta={d}: {cell}")

    out["results"] = results

    # ---- VONG 2a: NEUTRALISE_SIZE -- cung pipeline goc, ghi de cot size ----
    results_neutralised = {}
    for tag, pipe in (("low", PIPE_LOW), ("ceiling", PIPE_CEILING)):
        results_neutralised[tag] = {"n_records": len(pipe._records),
                                    "screen": {}, "certify": {}}
        for phase, n_cap in (("screen", N_SCREEN), ("certify", N_CERTIFY)):
            for d in DELTAS:
                cell = measure_cell(pipe, d, n_cap, row_transform=neutralise_size)
                cell["mean_reuse_per_record"] = (
                    cell["n_pos_reached"] / len(pipe._records) if pipe._records else float("nan"))
                results_neutralised[tag][phase][d] = cell
                print(f"[diag_llm_eps] NEUTRALISE_SIZE {tag} {phase} Delta={d}: {cell}")
    out["results_size_neutralised"] = results_neutralised

    # ---- VONG 2b: LENGTH-MATCHED -- pipeline moi, content cat/dem ve L=63 --
    results_lmatch = {}
    for tag, pipe in (("low", PIPE_LOW_LMATCH), ("ceiling", PIPE_CEILING_LMATCH)):
        results_lmatch[tag] = {"n_records": len(pipe._records), "screen": {}, "certify": {}}
        for phase, n_cap in (("screen", N_SCREEN), ("certify", N_CERTIFY)):
            for d in DELTAS:
                cell = measure_cell(pipe, d, n_cap)
                cell["mean_reuse_per_record"] = (
                    cell["n_pos_reached"] / len(pipe._records) if pipe._records else float("nan"))
                results_lmatch[tag][phase][d] = cell
                print(f"[diag_llm_eps] LENGTH_MATCHED {tag} {phase} Delta={d}: {cell}")
    out["results_length_matched"] = results_lmatch
    out["length_match_counts"] = LENGTH_MATCH_COUNTS
    out["marker_survival_after_truncation"] = MARKER_SURVIVAL

    # ---- xac nhan lai kiem hop le SAU KHI sua duong code (yeu cau coordinator) --
    validation2 = {}
    all_match2 = True
    for d in DELTAS:
        cell = measure_cell(pipe_matched, d, N_SCREEN)
        stat = cell.get("screen_statistic_auc_median")
        ref = REFERENCE_EPS0[d]
        ok = stat is not None and abs(stat - ref) <= REFERENCE_TOL
        all_match2 = all_match2 and ok
        validation2[d] = {"measured": stat, "reference": ref, "match": ok,
                          "n_pos_reached": cell["n_pos_reached"]}
    out["validation_matched_eps0_screen_after_v2_edit"] = validation2
    print(f"[diag_llm_eps] kiem hop le LAI sau khi sua code (vong 2): {validation2}")

    out["status"] = "DONE" if all_match2 else \
        "DONE_WITH_CONCERNS -- kiem hop le LAI (sau sua code vong 2) LECH bang brief"
    out["runtime_s"] = time.time() - t0

    out_path = HERE / "diag-llm-eps.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[diag_llm_eps] ghi {out_path} sau {out['runtime_s']:.1f}s")
    return out


if __name__ == "__main__":
    main()
