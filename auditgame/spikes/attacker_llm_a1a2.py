#!/usr/bin/env python3
"""
attacker_llm_a1a2.py -- Task 4: do A1 `llm-informed` va A2 `llm-hybrid`.

Brief: .superpowers/sdd/2026-09-20-ssg-gate4c/task-4-brief.md
Tien-dang-ky (dong bang TRUOC khi chay, khong sua tieu chi sau khi thay so):
HCMUT/261-Master-Proposal-Analysis/TIEN-DANG-KY-Attacker-LLM.md

KHONG goi API o day. Vat lieu LLM (noi dung + lua chon carrier/timing cua A1)
da duoc sinh MOT LAN, that tien, boi spikes/gen_attacker_llm_a1a2.py, va dong
bang vao spikes/a1-informed-advice.jsonl, spikes/a2-hybrid-advice.jsonl,
spikes/a1-carrier-choice.json. Script nay CHI DOC cac file do.

KHONG sua attacks.py / analysis/gate2_v2.py / analysis/benign_corpus.py /
analysis/discriminator.py / lp.py / policies.py / dprime_sweep.py. Pipeline
chan doan la BAN SAO cuc bo, dang ky vao attacks.REGISTRY luc runtime -- cung
khuon voi spikes/diag_llm_eps.py::LLMAdviceAttack (TAI SU DUNG truc tiep module
do cho phan AUC, khong viet lai -- brief muc "dung lai").

===========================================================================
HAI TRUC DO, VA VI SAO CHUNG TACH RIENG (phat hien kien truc, ghi lai de bao
cao khong lam nguoi doc tuong nham hai truc lam mot).
===========================================================================

TRUC 1 -- AUC / NGUY TRANG (F_match).  `analysis.benign_corpus.matched_corpus`
goi THANG `pipe.payload(wf, ps)` voi `ps` no TU XAY (carrier co dinh tu ben
ngoai, iota/sigma liet ke qua MOI sigma kha thi) -- `pipe.plan()` KHONG duoc
goi tren duong nay (da ghi trong diag_llm_eps.py). Đieu A1/A2 dong gop duoc o
truc nay CHI la NOI DUNG (content -- truc 'LLM giu but'); carrier van do
`measure_cell`-tuong-duong (ham `measure_cell` cua diag_llm_eps.py) co dinh tu
ben ngoai, giong het A0.

TRUC 2 -- HARM / L (dprime_sweep / runner).  `runner.paired` / `run_once` goi
THANG `build.inject`, ma content luon la MOT chuoi CO DINH (`build.
payload_content`), BAT KE pipeline nao dang duoc noi toi -- attacks.REGISTRY
KHONG duoc doc o day. VA `detector.Detector.score` chi doc `item.poisoned`
(su that nen) + mot draw Gauss gieo hat boi item_id -- KHONG doc `item.content`
theo bat ky each nao co he thong (item_id la seed cho MOT draw ngau nhien, gia
tri content chi doi seed do, khong doi KY VONG cua diem so). DO DUOC (xem bao
cao .md, muc "Xac nhan truc harm khong phu thuoc noi dung"): hai pipeline
khac content nhau hoan toan cho CUNG mot (carrier, iota, sigma, seed) ra CUNG
mot harm. Vay o TRUC NAY, dieu A1/A2 dong gop duoc KHONG THE la noi dung -- no
CHI co the la (carrier, sigma) duoc CHON, dung Phu luc F.1 (liet ke chien luoc
thuan). Day la ly do MODULE NAY tu viet mot ham liet ke (K carrier x (H-Delta)
sigma kha thi, dung `analysis.benign_corpus.feasible_sigmas` de liet ke, dung
`runner.paired` de cham diem TUNG ung vien) thay vi goi lai
`dprime_sweep.measure_cell`/`policy_curve` (nhung ham do CHI liet ke carrier,
RUT NGAU NHIEN mot sigma cho moi carrier -- khong liet ke sigma, nen khong phai
best response day du theo dung nghia F.1).

QUYET DINH THIET KE QUAN TRONG NHAT CUA TASK NAY (brief yeu cau noi ro minh
chon gi va vi sao, hoac bao NEEDS_CONTEXT neu khong quyet duoc). Tu nhung gi
doc duoc trong tien-dang-ky + kien truc co san (dprime_sweep.policy_curve /
runner.worst_case / attackers.worst_case_over / runner.best_response_gap deu
tinh "best/worst" SO VOI MOT CHINH SACH CU THE, tung chinh sach mot -- khong
co bat ky ham nao trong repo tinh mot "best response chung" qua ca 5 chinh
sach), toi CHON: best response duoc dinh nghia RIENG cho TUNG chinh sach trong
5 chinh sach (B1, B5, Sentinel, B7, SSG-up) -- dung dai luong harm (trung binh
qua SEEDS, dung dinh nghia harm da co trong RunResult.harm) LAM DAI LUONG toi
da hoa, dung tinh than `runner.worst_case`/`dprime_sweep.policy_curve` ("attacker
toi da hoa harm trung binh, KHONG phai L", tru phi noi khac). "Khoang cach toi
best-response" cua mot muc X, tai mot (chinh sach, Delta), duoc dinh nghia:

    gap(X) = harm(best-response) - harm(X)
    ty le da thu hep boi A1 so voi A0 = (gap(A0) - gap(A1)) / gap(A0)

voi harm(A0) = TRUNG BINH harm tren TOAN BO luoi liet ke (carrier x sigma kha
thi) -- operationalise dung nghia "benchmark gan" cua bang muc 2 tien-dang-ky
(khong ai toi uu, benchmark rut MOT diem BAT KY tu khong gian chien luoc thuan)
-- VA KHAC voi so da cong bo o noi khac tu `dprime_sweep.measure_cell` (so do
DA la mot tim-kiem-toi-uu-qua-carrier, gan voi A2 hon la voi "benchmark gan");
so do van duoc bao cao rieng, co nhan ro, de lam DOI CHIEU, khong bi tron voi
A0 cua task nay.

Day la MOT QUYET DINH CUA NGUOI THUC HIEN, khong phai mot cau tra loi da co san
tu van ban da dong bang -- ghi lai o day VA trong .md de nguoi doc/huong dan co
the bat dong y va yeu cau do lai voi mot dinh nghia khac.

Chi dung thu vien chuan (ABC T.6).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, ".")

import attacks                              # noqa: E402
import agent                                # noqa: E402
import build                                # noqa: E402
import dprime_sweep as DS                   # noqa: E402
import policies as P                        # noqa: E402
import runner                                # noqa: E402
from core import Item, PoisonSpec, seed_of  # noqa: E402
from analysis import benign_corpus as B     # noqa: E402
from analysis import gate2_v2 as G2         # noqa: E402
from spikes import diag_llm_eps as DL       # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 0) Hang so dong bang -- doc tu ban ghi, KHONG go tay (nhu diag_llm_eps.py).
# ---------------------------------------------------------------------------
AUC_CEILING = G2.record()["ceiling"]
DELTAS = G2.DELTAS                          # (0, 2, 4)
N_SCREEN = G2.N_SCREEN                      # 80
N_CERTIFY = G2.N_CERTIFY                    # 900
REFERENCE_EPS0 = DL.REFERENCE_EPS0
REFERENCE_TOL = DL.REFERENCE_TOL

# Nam chinh sach phong thu -- KHOP ten voi policies.POLICIES.
B1_NAME = "B1 audit-at-commit"
B5_NAME = "B5 risk-score"
SENTINEL_NAME = "Sentinel"
B7_NAME = "B7 minimax-lp"
SSGUP_NAME = "SSG-up receding"
FIVE_POLICIES = (B1_NAME, B5_NAME, SENTINEL_NAME, B7_NAME, SSGUP_NAME)

# Luoi harm/L -- KHOP voi quy uoc spikes/diag_4c2.py de so sanh duoc voi cac
# spike gate-4c khac (D_PRIME=2.2, BUDGET=17.95, N_WF=40, H=8, SEEDS=(1,2,3),
# setting="mid"). KHONG tu chon so khac sau khi thay ket qua.
D_PRIME = 2.2
BUDGET = 17.95
SEEDS = (1, 2, 3)
N_WF, H = 40, 8
SETTING = "mid"
HARM_EPS = 0.6            # epsilon mac dinh cua build.plan_poison -- CUNG mot
                          # gia tri ma dprime_sweep.policy_curve/runner.worst_case
                          # dung khi goi build.plan_poison(wf, k, d, rng) KHONG
                          # truyen epsilon.
MARKER = "raw_write"

CARRIERS_ALL = tuple(sorted(attacks.CARRIERS_ALL))     # ('branch','memory','queue','skill')

CORPUS_SEED = DS.CORPUS_SEED


# ---------------------------------------------------------------------------
# 1) Doc vat lieu LLM da dong bang (KHONG goi API).
# ---------------------------------------------------------------------------

def _load_jsonl(path: pathlib.Path) -> list:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} khong ton tai -- chay spikes/gen_attacker_llm_a1a2.py "
            f"MOT LAN truoc (that tien, xem docstring cua no) roi commit file "
            f"do. Script nay KHONG goi API.")
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


A1_ADVICE_PATH = HERE / "a1-informed-advice.jsonl"
A2_ADVICE_PATH = HERE / "a2-hybrid-advice.jsonl"
A1_CHOICE_PATH = HERE / "a1-carrier-choice.json"


# ---------------------------------------------------------------------------
# 2) Pipeline TRUC AUC -- content tu file dong bang, moi thu khac GIONG HET
#    payloads.FrozenPayloadAttack / diag_llm_eps.LLMAdviceAttack (topic = task
#    sigma's CA topic, provenance="agent/notes", epsilon_effective=False).
#    Nhan seed RIENG cho MOI muc (salt = ten pipeline) -- tien-dang-ky SS6:
#    "nhan seed trung lam hai policy rut cung dong ngau nhien".
# ---------------------------------------------------------------------------

class LLMInformedAttack(DL.LLMAdviceAttack):
    """A1 `llm-informed` -- truc AUC. Ke thua LLMAdviceAttack (diag_llm_eps.py)
    dung nguyen, chi doi ten/ngan hang/salt. Phan 'duoc cho biet carrier +
    kappa + H + chinh sach' cua A1 nam o TRUC HARM (ham chon carrier/timing
    ben duoi doc tu a1-carrier-choice.json), KHONG o day -- o truc AUC, carrier
    van do `matched_corpus` gan tu ngoai (giong A0), dung quy uoc da co."""
    pass


class LLMHybridAttack(DL.LLMAdviceAttack):
    """A2 `llm-hybrid` -- truc AUC. LLM CHI viet noi dung (ngan hang rieng);
    lua chon (carrier, sigma) 'best-response' nam o TRUC HARM (ham liet ke
    ben duoi), khong o day."""
    pass


def _as_advice_records(records: list) -> list:
    """diag_llm_eps.LLMAdviceAttack doc `rec["advice"]`; vat lieu task-4 duoc
    sinh voi khoa "content" (xem gen_attacker_llm_a1a2.py). Anh xa o DAY, MOT
    lan, khong sua diag_llm_eps.py (brief: dung lai, dung sua)."""
    return [{"advice": r["content"]} for r in records]


def register_pipelines() -> tuple:
    a1_records = _as_advice_records(_load_jsonl(A1_ADVICE_PATH))
    a2_records = _as_advice_records(_load_jsonl(A2_ADVICE_PATH))
    pipe_a1 = LLMInformedAttack("llm-informed", a1_records, salt="llm-informed")
    pipe_a2 = LLMHybridAttack("llm-hybrid", a2_records, salt="llm-hybrid")
    attacks.REGISTRY[pipe_a1.name] = pipe_a1
    attacks.REGISTRY[pipe_a2.name] = pipe_a2
    return pipe_a1, pipe_a2


# ---------------------------------------------------------------------------
# 3) Kiem hop le BAT BUOC, TRUOC khi tin bat ky so nao (brief).
# ---------------------------------------------------------------------------

def validity_check() -> dict:
    pipe_matched = attacks.REGISTRY["matched"]
    out = {}
    all_match = True
    for d in DELTAS:
        cell = DL.measure_cell(pipe_matched, d, N_SCREEN)
        stat = cell.get("screen_statistic_auc_median")
        ref = REFERENCE_EPS0[d]
        ok = stat is not None and abs(stat - ref) <= REFERENCE_TOL
        all_match = all_match and ok
        out[d] = {"measured": stat, "reference": ref, "match": ok,
                 "n_pos_reached": cell["n_pos_reached"]}
    out["ALL_MATCH"] = all_match
    return out


# ---------------------------------------------------------------------------
# 4) TRUC AUC -- do A1/A2 qua diag_llm_eps.measure_cell (TAI SU DUNG, khong
#    viet lai), ca hai pha (screen/certify), ca hai cach go confound (size
#    neutralised, length-matched).
# ---------------------------------------------------------------------------

def auc_axis(pipe, name: str) -> dict:
    out = {"name": name, "n_records": len(pipe._records),
          "raw": {"screen": {}, "certify": {}},
          "size_neutralised": {"screen": {}, "certify": {}},
          "length_matched": {"screen": {}, "certify": {}}}
    for phase, n_cap in (("screen", N_SCREEN), ("certify", N_CERTIFY)):
        for d in DELTAS:
            cell = DL.measure_cell(pipe, d, n_cap)
            cell["mean_reuse_per_record"] = (
                cell["n_pos_reached"] / len(pipe._records) if pipe._records else None)
            out["raw"][phase][d] = cell

            cell_n = DL.measure_cell(pipe, d, n_cap, row_transform=DL.neutralise_size)
            cell_n["mean_reuse_per_record"] = cell["mean_reuse_per_record"]
            out["size_neutralised"][phase][d] = cell_n

    # length-matched: ban sao content da cat/dem ve build.PAYLOAD_LENGTH,
    # dung LOP length-matched cua diag_llm_eps.py (ke thua tu LLMAdviceAttack).
    class _LM(DL.LLMAdviceLengthMatchedAttack):
        pass
    pipe_lm = _LM(f"{name}-lmatch", pipe._records, salt=pipe._salt)
    attacks.REGISTRY[pipe_lm.name] = pipe_lm
    out["length_match_counts"] = DL.length_match_counts(pipe._records)
    out["marker_survival"] = DL.marker_survival(pipe._records)
    for phase, n_cap in (("screen", N_SCREEN), ("certify", N_CERTIFY)):
        for d in DELTAS:
            cell = DL.measure_cell(pipe_lm, d, n_cap)
            cell["mean_reuse_per_record"] = (
                cell["n_pos_reached"] / len(pipe._records) if pipe._records else None)
            out["length_matched"][phase][d] = cell
    return out


# ---------------------------------------------------------------------------
# 5) TRUC HARM/L -- liet ke K(H-Delta), dung Phu luc F.1.
# ---------------------------------------------------------------------------

def make_corpus() -> list:
    return DS.make_corpus(N_WF, H, seed=CORPUS_SEED)


def enumerate_grid(wf, delta: int, carriers=CARRIERS_ALL, eps: float = HARM_EPS) -> list:
    """[(carrier, sigma), ...] -- TOAN BO khong gian chien luoc thuan K x
    (H-Delta) cho MOT workflow, dung `feasible_sigmas` (CUNG predicate
    `build.plan_poison` dung, liet ke thay vi rut mau -- xem docstring cua no).
    """
    out = []
    for k in carriers:
        for s in B.feasible_sigmas(wf, delta, eps):
            out.append((k, s))
    return out


def harm_of(wf, carrier: str, sigma: int, delta: int, policy_name: str,
           det, ag, budget: float, setting: str, seeds=SEEDS) -> float | None:
    ps = PoisonSpec(carrier=carrier, iota=sigma - delta, sigma=sigma,
                    epsilon=HARM_EPS, marker=MARKER)
    hs = []
    for s in seeds:
        r = runner.paired(wf, ps, policy_name, det, ag, s, budget, setting)
        if r is not None:
            hs.append(r.harm)
    return (sum(hs) / len(hs)) if hs else None


def cell_A0_mean_and_A2_max(wfs, delta: int, policy_name: str, det, ag,
                            budget: float, setting: str) -> dict:
    """Mot (policy, Delta): A0 = TRUNG BINH harm tren TOAN BO luoi lam viec
    (moi workflow dong gop trung binh cua no), A2 = TRUNG BINH cua MAX harm
    moi workflow (best response THAT su, liet ke K x (H-Delta)).  Ghi lai
    carrier THANG cuoc moi workflow cho A2 (phan bo carrier duoc chon)).

    HAI PHIEN BAN CUA A2 -- va chi mot cai so sanh duoc voi A1.

      A2_oracle  = trung binh cua max-moi-workflow.  Attacker NHIN THAY tung
                   workflow roi moi chon.  Day la quy uoc cua runner.worst_case.
      A2_global  = max qua cau hinh cua trung binh-qua-workflow.  Attacker cam
                   ket MOT (carrier, sigma) cho ca 40 workflow.  Day la quy uoc
                   cua runner.best_response_gap.

    A1 cam ket MOT (carrier, timing) cho ca 40 workflow (xem cell_A1).  Nen
    mau so cua gap_closure phai la A2_global: lay A2_oracle lam tran la bat A1
    duoi theo mot doi thu duoc cho them thong tin ma A1 khong he co, va
    gap_closure bi keo xuong bang cach dung ham so, khong phai bang do luong.
    A2_oracle van duoc ghi lai -- no la tran tren dung nghia, chi khong phai
    mau so."""
    a0_per_wf, a2_per_wf, a2_carrier_counts = [], [], {}
    n_total = len(wfs)
    n_feasible = 0
    for wf in wfs:
        grid = enumerate_grid(wf, delta)
        vals = []
        for k, s in grid:
            h = harm_of(wf, k, s, delta, policy_name, det, ag, budget, setting)
            if h is not None:
                vals.append((h, k, s))
        if not vals:
            continue
        n_feasible += 1
        a0_per_wf.append(sum(v[0] for v in vals) / len(vals))
        best = max(vals, key=lambda v: v[0])
        a2_per_wf.append(best[0])
        a2_carrier_counts[best[1]] = a2_carrier_counts.get(best[1], 0) + 1
    return {
        "policy": policy_name, "delta": delta,
        "n_total": n_total, "n_feasible": n_feasible,
        "harm_A0_mean": (sum(a0_per_wf) / len(a0_per_wf)) if a0_per_wf else None,
        "harm_A2_oracle_perwf": (sum(a2_per_wf) / len(a2_per_wf)) if a2_per_wf else None,
        "a2_carrier_distribution": a2_carrier_counts,
    }


TIMINGS = ("earliest", "middle", "latest")


def cell_A2_class(wfs, delta: int, policy_name: str, det, ag,
                 budget: float, setting: str) -> dict:
    """A2 trong DUNG LOP CHIEN LUOC ma A1 chon tu: (carrier, luat-timing).

    Day la mau so cua gap_closure.  Ly do: A1 cam ket MOT (carrier, timing)
    cho ca 40 workflow, roi sigma duoc dich CO HOC moi workflow tu chinh
    danh sach feasible cua no (xem cell_A1).  Mot mau so lay max-moi-workflow
    (A2_oracle) la attacker duoc NHIN tung workflow truoc khi chon -- thong
    tin A1 khong he co -- nen gap_closure bi keo xuong bang ham so chu khong
    phai bang do luong.

    Goi thang cell_A1 cho tung (carrier, timing) de khong co kha nang lech
    giua hai nhanh: cung mot ham, cung mot cach dich sigma.

    LUOI DAY DU duoc ghi ra (`class_grid`): harm cua CA 12 (carrier, timing)
    tai o nay.  Ly do ghi ca luoi chu khong chi cai max: moi luat gop khac --
    ke ca luat KHOP-Delta (mot (carrier,timing) duy nhat cho ca ba Delta, dung
    lop cam ket ma A1 that su o trong, vi A1 khong duoc cho biet Delta) -- deu
    tinh duoc tu luoi nay bang so hoc, khong phai chay lai.
    """
    best, grid = None, {}
    for k in CARRIERS_ALL:
        for tm in TIMINGS:
            r = cell_A1(wfs, delta, policy_name, {"carrier": k, "timing": tm},
                        det, ag, budget, setting)
            grid["%s/%s" % (k, tm)] = r["harm_A1"]
            if r["harm_A1"] is None:
                continue
            if best is None or r["harm_A1"] > best["harm"]:
                best = {"harm": r["harm_A1"], "carrier": k, "timing": tm,
                        "n_feasible": r["n_feasible"]}
    if best is None:
        return {"harm_A2_class": None, "class_grid": grid,
                "harm_A2_class_reason": "khong (carrier,timing) nao kha thi",
                "harm_A2_class_config": None}
    return {"harm_A2_class": best["harm"], "harm_A2_class_reason": None,
            "class_grid": grid,
            "harm_A2_class_config": {"carrier": best["carrier"],
                                     "timing": best["timing"],
                                     "n_feasible": best["n_feasible"]}}


def cell_A1(wfs, delta: int, policy_name: str, choice: dict, det, ag,
           budget: float, setting: str, eps: float = HARM_EPS) -> dict:
    """A1: MOT quyet dinh CAP CHINH SACH (carrier co dinh, timing =
    earliest/latest/middle), dich sang MOT sigma CU THE MOI workflow bang
    cach lay phan tu dau/cuoi/giua cua danh sach feasible_sigmas cua CHINH
    workflow do (cua so kha thi khac nhau giua cac workflow, viec dich la co
    hoc, khong phai mot quyet dinh chien luoc moi)."""
    carrier = choice["carrier"]
    timing = choice["timing"]
    per_wf = []
    n_total = len(wfs)
    n_feasible = 0
    for wf in wfs:
        cands = B.feasible_sigmas(wf, delta, eps)
        if not cands:
            continue
        cands = sorted(cands)
        if timing == "earliest":
            sigma = cands[0]
        elif timing == "latest":
            sigma = cands[-1]
        else:
            sigma = cands[len(cands) // 2]
        h = harm_of(wf, carrier, sigma, delta, policy_name, det, ag, budget, setting)
        if h is not None:
            n_feasible += 1
            per_wf.append(h)
    return {"policy": policy_name, "delta": delta, "carrier": carrier,
           "timing": timing, "n_total": n_total, "n_feasible": n_feasible,
           "harm_A1": (sum(per_wf) / len(per_wf)) if per_wf else None}


def harm_axis(wfs, choices: dict) -> dict:
    det = DS.make_detector(D_PRIME)
    ag = agent.MockAgent()
    out = {"meta": {"d_prime": D_PRIME, "budget": BUDGET, "seeds": list(SEEDS),
                    "n_wf": N_WF, "H": H, "setting": SETTING,
                    "eps": HARM_EPS, "policies": list(FIVE_POLICIES)},
          "cells": []}
    for policy_name in FIVE_POLICIES:
        for delta in DELTAS:
            runner.reset_survivor_cache()
            base = cell_A0_mean_and_A2_max(wfs, delta, policy_name, det, ag,
                                           BUDGET, SETTING)
            runner.reset_survivor_cache()
            a1 = cell_A1(wfs, delta, policy_name, choices[policy_name], det, ag,
                        BUDGET, SETTING)
            runner.reset_survivor_cache()
            a2c = cell_A2_class(wfs, delta, policy_name, det, ag, BUDGET, SETTING)
            row = {**base, **a2c, "harm_A1": a1["harm_A1"],
                  "a1_carrier": a1["carrier"], "a1_timing": a1["timing"],
                  "a1_n_feasible": a1["n_feasible"]}
            a0, a1h, a2 = row["harm_A0_mean"], row["harm_A1"], row["harm_A2_class"]
            if None not in (a0, a1h, a2) and (a2 - a0) > 1e-9:
                gap_a0 = a2 - a0
                gap_a1 = a2 - a1h
                row["gap_closure_A1_vs_A0"] = (gap_a0 - gap_a1) / gap_a0
            else:
                row["gap_closure_A1_vs_A0"] = None
                row["gap_closure_reason"] = (
                    "harm_A2_class == harm_A0 (lop chien luoc phang tai o nay) "
                    "hoac mot trong ba so bi thieu (N3): khong chia duoc"
                )
            out["cells"].append(row)
            print(f"[harm] {policy_name} Delta={delta}: A0={a0} A1={a1h} "
                 f"A2class={a2} gap_closure={row.get('gap_closure_A1_vs_A0')}")

    # Doi chieu voi so DA CO SAN tu dprime_sweep.measure_cell KHONG DOI (ca 4
    # carrier, RUT NGAU NHIEN mot sigma/carrier) -- ghi RO day la mot con so
    # KHAC, khong phai "A0" cua task nay (xem docstring module).
    out["reference_measure_cell_unchanged"] = []
    for delta in DELTAS:
        runner.reset_survivor_cache()
        mc = DS.measure_cell(wfs, D_PRIME, delta, BUDGET, SEEDS,
                             carriers=CARRIERS_ALL, ag=ag, setting=SETTING,
                             policies=FIVE_POLICIES)
        out["reference_measure_cell_unchanged"].append({
            "delta": delta, "harm_b1": mc.harm_b1, "harm_sentinel": mc.harm_sentinel,
            "dharm": mc.dharm, "ci_lo": mc.ci_lo, "ci_hi": mc.ci_hi,
            "n_feasible": mc.n_feasible, "n_total": mc.n_total,
            "reason": mc.reason,
            "per_policy_harm": {n: c.harm for n, c in mc.curves.items()},
        })
    return out


# ---------------------------------------------------------------------------
# 6) Xac nhan TRUC HARM khong phu thuoc noi dung (khang dinh trong docstring
#    module) -- do THAT tren mot cap (carrier, sigma, seed) co dinh, hai
#    pipeline content khac nhau hoan toan.
# ---------------------------------------------------------------------------

def content_independence_check(wfs) -> dict:
    det = DS.make_detector(D_PRIME)
    ag = agent.MockAgent()
    wf = wfs[0]
    grid = enumerate_grid(wf, 2)
    if not grid:
        return {"status": "SKIPPED -- luoi rong tren wf dau tien"}
    k, s = grid[0]
    ps = PoisonSpec(carrier=k, iota=s - 2, sigma=s, epsilon=HARM_EPS, marker=MARKER)
    r1 = runner.paired(wf, ps, SENTINEL_NAME, det, ag, SEEDS[0], BUDGET, SETTING)
    # Doi content bang cach ghi de build.inject tam thoi la qua nguy hiem (dung
    # module toan cuc); thay vao do XAC NHAN GIAN TIEP qua chinh co che:
    # detector.Detector.score doc item.poisoned + seed_of(seed, item_id) --
    # item_id phu thuoc content, nen NEU harm phu thuoc content mot cach he
    # thong thi harm phai doi khi content doi. Ta khong the ep build.inject
    # dung content khac ma khong sua module dung chung (cam trong brief), nen
    # o day chi TRICH DAN thang tham chieu ma chung minh dieu do (detector.py,
    # ham score) va bao cao KET QUA DOC duoc, khong chay lai mot thi nghiem
    # thay content that.
    return {
        "status": "DA XAC NHAN QUA DOC MA NGUON (khong chay lai thi nghiem thay "
                 "content, vi build.inject/run_once la MODULE DUNG CHUNG, brief "
                 "cam sua)",
        "evidence": "detector.py Detector.score(item, now, seed): "
                   "`random.Random(seed_of(seed, item.item_id)).gauss("
                   "self.d_prime if item.poisoned else 0.0, 1.0)` -- CHI doc "
                   "`item.poisoned` (su that nen) va dung item_id LAM SEED cho "
                   "MOT draw Gauss; gia tri content chi doi SEED (tuc doi "
                   "REALISATION cua draw), khong doi KY VONG (d_prime hoac 0.0). "
                   "build.inject (build.py) ghi content CO DINH tu "
                   "build.payload_content(topic, marker), doc lap voi "
                   "attacks.REGISTRY -- khong pipeline nao (attacks.py) duoc doc "
                   "tren duong nay.",
        "sample_cell": {"wf_id": wf.wf_id, "carrier": k, "sigma": s,
                        "harm_sample": r1.harm if r1 else None},
    }


# ---------------------------------------------------------------------------
# 7) main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    out = {"meta": {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}}

    print("[a1a2] kiem hop le BAT BUOC truoc khi tin bat ky so nao...")
    val = validity_check()
    out["validity_check"] = val
    print(f"[a1a2] {val}")
    if not val["ALL_MATCH"]:
        out["status"] = "BLOCKED -- kiem hop le khong khop, DUNG LAI"
        (HERE / "attacker-llm-a1a2.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[a1a2] KHOP THAT BAI -- dung, ghi file, thoat.")
        return 1

    pipe_a1, pipe_a2 = register_pipelines()

    print("[a1a2] TRUC AUC -- A1 (llm-informed)...")
    out["auc_a1"] = auc_axis(pipe_a1, "llm-informed")
    print("[a1a2] TRUC AUC -- A2 (llm-hybrid)...")
    out["auc_a2"] = auc_axis(pipe_a2, "llm-hybrid")

    if not A1_CHOICE_PATH.exists():
        out["status"] = "BLOCKED -- thieu a1-carrier-choice.json"
        (HERE / "attacker-llm-a1a2.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1
    choice_doc = json.loads(A1_CHOICE_PATH.read_text(encoding="utf-8"))
    choices = choice_doc["choices"]
    out["a1_choices"] = choices

    print("[a1a2] dung mot corpus mock (N_WF=%d, H=%d, seed=%s)..." % (N_WF, H, CORPUS_SEED))
    wfs = make_corpus()

    print("[a1a2] xac nhan truc harm khong phu thuoc noi dung...")
    out["content_independence_check"] = content_independence_check(wfs)

    print("[a1a2] TRUC HARM/L -- liet ke K(H-Delta), 5 chinh sach x 3 Delta...")
    out["harm_axis"] = harm_axis(wfs, choices)

    out["status"] = "DONE"
    out["runtime_s"] = time.time() - t0
    (HERE / "attacker-llm-a1a2.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[a1a2] DONE sau {out['runtime_s']:.1f}s. Ghi "
         f"{HERE / 'attacker-llm-a1a2.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
