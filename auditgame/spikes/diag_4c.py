"""
diag_4c.py -- Cong 4c: phan dinh vi sao SSGRecedingUpstream (SSG-up) hoi quy so
voi MinimaxLPUpstream (B7U) tren o (Delta=4, d'=2.2), lop (2,4).

Brief: .superpowers/sdd/2026-09-20-ssg-gate4c/task-1-brief.md

KHONG sua lp.py / policies.py. Cac lop chan doan la BAN SAO cuc bo, dang ky vao
policies.REGISTRY luc runtime (khong sua file), roi do bang dprime_sweep.measure_cell
tren dung corpus/budget/seeds cua ssg-gates.json de so sanh duoc.

Hai gia thuyet phai phan dinh (xem brief SS "Hai gia thuyet"):
  (i)  THAM LAM SOM -- duong chi tich luy theo t cua SSG-up nam TREN duong cua
       B7U o nua dau van.
  (ii) C BI BO / SAI -- `done` (self._done) rong hoac sai, nen LP nghi chua phu
       gi va phu lai cho da phu. Do bang: (a) _done co duoc dien khong theo t,
       (b) bat/tat C (ep done=None) co doi harm khong.

Chi dung thu vien chuan (ABC T.6).
"""
from __future__ import annotations

import json
import random
import sys
import time

sys.path.insert(0, ".")

import policies as P          # noqa: E402
import lp                     # noqa: E402
import dprime_sweep as ds     # noqa: E402
from core import seed_of      # noqa: E402

# ---------------------------------------------------------------------------
# Hang so o dang chan doan -- KHOP voi ssg-gates.json de so do so sanh duoc.
# ---------------------------------------------------------------------------
D_PRIME = 2.2
DELTA = 4                 # o hoi quy nang nhat trong bang cua brief
CLASS_DELTAS = (2, 4)     # lop upstream ma B7U / SSG-up dang chay
BUDGET = 17.95
SEEDS = (1, 2, 3)
N_WF, H = 40, 8

REFERENCE = {
    # tu auditgame/spikes/ssg-gates.json, gate_4b[delta=4, d'=2.2].in_class["(2,4)"]
    "static": {"policy": "B7U minimax-lp upstream", "harm": 0.45045045045045046,
               "spent": 15.024324324324324},
    "receding": {"policy": "SSG-up receding", "harm": 0.5720720720720721,
                 "spent": 15.407207207207206},
}


# ---------------------------------------------------------------------------
# 1) Ban sao chan doan: cung logic choose() cua policies.py, chi them ghi log.
#    Khong ke thua tu mot mixin can can thiep vao __init__ theo kieu MRO tinh
#    te -- copy nguyen van than choose() roi them 4 dong ghi log la it rui ro
#    doc-sai hon, va de doi chieu tung dong voi ban goc trong policies.py.
# ---------------------------------------------------------------------------

class DiagB7U(P.MinimaxLPUpstream):
    """B7U tinh, chi them ghi (t, action, spent_after) vao TRACE cap lop."""
    TRACE: list = []          # [{ "t": [...], "spent": [...] }, ...] -- moi phan tu 1 episode

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._ep = {"t": [], "action": [], "spent_after": []}
        type(self).TRACE.append(self._ep)

    def choose(self, t, retrieved_carriers, signals):
        act = super().choose(t, retrieved_carriers, signals)
        cost = P.cost_of(act)
        self._ep["t"].append(t)
        self._ep["action"].append(act)
        self._ep["spent_after"].append(self.spent + cost)
        return act


class DiagSSGUp(P.SSGRecedingUpstream):
    """SSG-up nhu hien tai (done=getattr(self,'_done',None)), them ghi log
    (t, action, spent_after, len(_done), sum(_done.values())) moi buoc."""
    TRACE: list = []

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._ep = {"t": [], "action": [], "spent_after": [],
                    "done_n": [], "done_sum": []}
        type(self).TRACE.append(self._ep)

    def choose(self, t, retrieved_carriers, signals):
        act = super().choose(t, retrieved_carriers, signals)
        cost = P.cost_of(act)
        done = getattr(self, "_done", None)
        self._ep["t"].append(t)
        self._ep["action"].append(act)
        self._ep["spent_after"].append(self.spent + cost)
        self._ep["done_n"].append(len(done) if done else 0)
        self._ep["done_sum"].append(sum(done.values()) if done else 0)
        return act


class DiagSSGUpNoC(P.SSGRecedingUpstream):
    """Gia thuyet (ii), nhanh 'tat C': BAN SAO cua SSGReceding.choose() (xem
    policies.py dong 433-459), chi khac DUY NHAT mot cho -- done=None ep cung,
    thay vi done=getattr(self, '_done', None). Cung SEED_TAG nen cung dong rng
    y het ban co C -- khac biet harm chi co the den tu done=None.
    _log_audit VAN duoc goi (khong anh huong vi done bi bo o day) de _hist/_done
    van ton tai giong het, phong khi co code khac doc chung -- hien tai khong co."""
    TRACE: list = []

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._ep = {"t": [], "action": [], "spent_after": []}
        type(self).TRACE.append(self._ep)

    def choose(self, t, retrieved_carriers, signals):
        kap = [P.KAPPA[c] for c in self._carriers]
        u, v, _m, n_win = lp.solve_remaining_lp(
            K=len(self._carriers), H=len(self.v) or 8, t=t,
            B_rem=max(self.budget - self.spent, 0.0), kap=kap,
            kc=P.KAPPA_COMMIT, deltas=self.deltas, done=None)   # <-- C EP TAT
        act = None
        if n_win == 0 or not v:
            act = None
        else:
            opts = []
            if v[0] > 1e-9 and self.can(P.KAPPA_COMMIT):
                opts.append(("commit", v[0]))
            for i, c in enumerate(self._carriers):
                if u[i][0] > 1e-9 and self.can(P.KAPPA[c]):
                    opts.append((c, u[i][0]))
            if opts:
                r = random.Random(seed_of(self.rng_seed, t, self.SEED_TAG)).random()
                acc = 0.0
                for c, w in opts:
                    acc += w
                    if r <= acc:
                        act = c
                        self._log_audit(t, c)
                        break
        cost = P.cost_of(act)
        self._ep["t"].append(t)
        self._ep["action"].append(act)
        self._ep["spent_after"].append(self.spent + cost)
        return act


DIAG_B7U_NAME = "DIAG B7U instrumented"
DIAG_SSGUP_NAME = "DIAG SSG-up instrumented"
DIAG_SSGUP_NOC_NAME = "DIAG SSG-up noC"

P.REGISTRY[DIAG_B7U_NAME] = DiagB7U
P.REGISTRY[DIAG_SSGUP_NAME] = DiagSSGUp
P.REGISTRY[DIAG_SSGUP_NOC_NAME] = DiagSSGUpNoC


# ---------------------------------------------------------------------------
# 2) Chay do
# ---------------------------------------------------------------------------

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def cum_spend_by_t(trace, H):
    """Trung binh cong don spent_after tai moi t, tren TAT CA episode da ghi
    (moi episode = 1 lan chay chinh sach tren 1 (workflow, carrier tan cong,
    seed) -- khong chi 'attack thang' ma policy_curve chon lam dai dien, vi
    TRACE ghi lai o ngay trong choose() cho MOI lan goi, khong phan biet dai
    dien hay khong). Tra ve (list t, list mean_spent, list n_episode_tai_t)."""
    buckets = {t: [] for t in range(H)}
    for ep in trace:
        for t, s in zip(ep["t"], ep["spent_after"]):
            buckets[t].append(s)
    ts = sorted(buckets)
    return ts, [mean(buckets[t]) for t in ts], [len(buckets[t]) for t in ts]


def done_stats_by_t(trace, H):
    buckets_n = {t: [] for t in range(H)}
    buckets_sum = {t: [] for t in range(H)}
    for ep in trace:
        for t, n, s in zip(ep["t"], ep["done_n"], ep["done_sum"]):
            buckets_n[t].append(n)
            buckets_sum[t].append(s)
    ts = sorted(buckets_n)
    return (ts, [mean(buckets_n[t]) for t in ts], [mean(buckets_sum[t]) for t in ts])


def main():
    t0 = time.time()
    wfs = ds.make_corpus(N_WF, H, seed=ds.CORPUS_SEED)

    # Reset TRACE truoc khi do (cac lop dang ky mot lan, TRACE la list cap lop
    # va co the con lai tu mot lan chay truoc trong cung process).
    DiagB7U.TRACE = []
    DiagSSGUp.TRACE = []
    DiagSSGUpNoC.TRACE = []

    policies_to_run = (ds.B1, ds.SENTINEL, DIAG_B7U_NAME, DIAG_SSGUP_NAME,
                       DIAG_SSGUP_NOC_NAME)
    print(f"[diag_4c] do o Delta={DELTA}, d'={D_PRIME}, lop {CLASS_DELTAS}, "
         f"B={BUDGET}, seeds={SEEDS}, N_WF={N_WF}, H={H}")
    print(f"[diag_4c] policies={policies_to_run}")

    cell = ds.measure_cell(wfs, d_prime=D_PRIME, delta=DELTA, budget=BUDGET,
                           seeds=SEEDS, policies=policies_to_run)

    print(f"[diag_4c] do xong sau {time.time() - t0:.1f}s, "
         f"n_feasible={cell.n_feasible}/{cell.n_total}, reason={cell.reason}")

    curves = cell.curves
    b7u_c = curves[DIAG_B7U_NAME]
    ssgup_c = curves[DIAG_SSGUP_NAME]
    ssgup_noc_c = curves[DIAG_SSGUP_NOC_NAME]

    # ---- gia thuyet (i): duong chi tich luy theo t ------------------------
    ts_b7u, spend_b7u, n_b7u = cum_spend_by_t(DiagB7U.TRACE, H)
    ts_ssgup, spend_ssgup, n_ssgup = cum_spend_by_t(DiagSSGUp.TRACE, H)
    ts_noc, spend_noc, n_noc = cum_spend_by_t(DiagSSGUpNoC.TRACE, H)

    # ---- gia thuyet (ii)(a): _done co duoc dien khong theo t ---------------
    ts_done, done_n_mean, done_sum_mean = done_stats_by_t(DiagSSGUp.TRACE, H)
    n_episodes_ssgup = len(DiagSSGUp.TRACE)
    n_episodes_nonempty_done_ever = sum(
        1 for ep in DiagSSGUp.TRACE if any(n > 0 for n in ep["done_n"]))

    # ---- gia thuyet (ii)(b): bat/tat C, so harm ----------------------------
    delta_harm_C = ssgup_noc_c.harm - ssgup_c.harm     # + nghia la tat C lam harm TANG (C dang giup)
    delta_spent_C = ssgup_noc_c.spent - ssgup_c.spent

    # ---- ket luan ------------------------------------------------------------
    # Gia thuyet (i) doc DUNG NGHIA DEN: "dom audit vao DAU van VA can tien
    # TRUOC KHI cua so MUON mo" -- do la hai dieu kien, khong phai mot:
    #   (a) gap duong tu nhung t SOM NHAT (t=0,1) -- "dom vao dau"
    #   (b) gap AM (SSG-up CHI TIEU IT HON tinh) o CUOI van -- "can tien,
    #       bo trong cua so muon" -- dau hieu THIEU chi cuoi van, khong phai
    #       thieu ma la CHI NHIEU HON suot.
    half = H // 2
    greedy_gap = [spend_ssgup[t] - spend_b7u[t] for t in range(H)]
    greedy_first_half = mean(greedy_gap[:half])
    greedy_second_half = mean(greedy_gap[half:])

    front_loaded_from_t0 = greedy_gap[0] > 0.05 and greedy_gap[1] > 0.05
    max_gap = max(greedy_gap)
    max_gap_t = greedy_gap.index(max_gap)
    final_gap = greedy_gap[-1]
    starved_late = final_gap < -0.05   # SSG-up chi IT HON tinh o task cuoi cung

    C_never_filled = (n_episodes_nonempty_done_ever == 0)
    C_toggle_changes_harm = abs(delta_harm_C) > 1e-9
    # % cua khoang cach harm (receding - static) ma viec tat C xoa duoc
    static_harm = b7u_c.harm
    total_gap_harm = ssgup_c.harm - static_harm       # +0.1216 trong brief
    explained_by_C = (delta_harm_C * -1.0) / total_gap_harm if total_gap_harm else float("nan")
    # delta_harm_C = noC - withC; -delta_harm_C = withC - noC = phan harm
    # C GAY RA (neu duong, C lam harm TANG THEM so voi khong co C).

    conclusion = {
        "hypothesis_i_early_greed_literal": {
            "front_loaded_from_t0": front_loaded_from_t0,
            "starved_late_window": starved_late,
            "gap_at_t0": greedy_gap[0],
            "gap_at_t1": greedy_gap[1],
            "gap_at_final_t": final_gap,
            "max_gap": max_gap,
            "max_gap_at_t": max_gap_t,
            "greedy_gap_mean_first_half": greedy_first_half,
            "greedy_gap_mean_second_half": greedy_second_half,
            "note": "gap(t) = chi_trung_binh(SSG-up, t) - chi_trung_binh(B7U, t). "
                    "Gia thuyet (i) dung nghia den doi hoi CA HAI: gap duong ngay "
                    "tu t=0/t=1 (dom som), VA gap AM o t cuoi (can tien, bo cua so "
                    "muon). Do duoc: gap(t0)~0, gap(t1)<0 (KHONG dom tu dau); "
                    "gap(t=cuoi)>0 (SSG-up VAN chi NHIEU HON tinh o task cuoi -- "
                    "KHONG can tien / KHONG bo cua so muon). Gap duong lon nhat "
                    "roi vao GIUA van, khong phai dau van.",
        },
        "hypothesis_ii_a_done_filled": {
            "C_never_filled": C_never_filled,
            "n_episodes_total": n_episodes_ssgup,
            "n_episodes_done_nonempty_ever": n_episodes_nonempty_done_ever,
        },
        "hypothesis_ii_b_toggle_C": {
            "C_toggle_changes_harm": C_toggle_changes_harm,
            "delta_harm_noC_minus_withC": delta_harm_C,
            "delta_spent_noC_minus_withC": delta_spent_C,
            "total_regression_gap_harm_receding_minus_static": total_gap_harm,
            "fraction_of_regression_gap_removed_by_dropping_C": explained_by_C,
            "note": "delta_harm_noC_minus_withC < 0 nghia la BO C lam harm GIAM "
                    "(tot hon) -> C, NHU HIEN TAI, DANG LAM HARM TE HON, khong "
                    "phai giup. fraction_of_regression_gap_removed_by_dropping_C "
                    "la ty le cua (receding_harm - static_harm) bien mat khi tat C.",
        },
    }

    out = {
        "meta": {"d_prime": D_PRIME, "delta": DELTA, "class_deltas": list(CLASS_DELTAS),
                 "budget": BUDGET, "seeds": list(SEEDS), "n_wf": N_WF, "H": H,
                 "n_feasible": cell.n_feasible, "n_total": cell.n_total,
                 "reason": cell.reason, "runtime_s": time.time() - t0},
        "reference_ssg_gates_json": REFERENCE,
        "reproduced": {
            "static_B7U": {"harm": b7u_c.harm, "spent": b7u_c.spent,
                          "n_feasible": b7u_c.n_feasible},
            "receding_SSGup": {"harm": ssgup_c.harm, "spent": ssgup_c.spent,
                              "n_feasible": ssgup_c.n_feasible},
            "receding_SSGup_noC": {"harm": ssgup_noc_c.harm, "spent": ssgup_noc_c.spent,
                                  "n_feasible": ssgup_noc_c.n_feasible},
            "B1": {"harm": curves[ds.B1].harm, "spent": curves[ds.B1].spent},
            "Sentinel": {"harm": curves[ds.SENTINEL].harm, "spent": curves[ds.SENTINEL].spent},
        },
        "hypothesis_i_spend_curve": {
            "t": ts_b7u,
            "static_B7U_mean_cum_spend": spend_b7u,
            "static_B7U_n_episodes_by_t": n_b7u,
            "receding_SSGup_mean_cum_spend": spend_ssgup,
            "receding_SSGup_n_episodes_by_t": n_ssgup,
            "n_episodes_total_B7U": len(DiagB7U.TRACE),
            "n_episodes_total_SSGup": len(DiagSSGUp.TRACE),
            "gap_ssgup_minus_b7u_by_t": greedy_gap,
            # noC: kiem tra rieng xem "chinh viec giai lai" (khong lien quan C)
            # co tu no da chi nhieu hon tinh hay khong -- neu co, phan con lai
            # cua hoi quy (ngoai C) nam o co che giai-lai, khong phai o C.
            "receding_SSGup_noC_mean_cum_spend": spend_noc,
            "receding_SSGup_noC_n_episodes_by_t": n_noc,
            "gap_noC_minus_b7u_by_t": [spend_noc[t] - spend_b7u[t] for t in range(H)],
        },
        "hypothesis_ii_done_by_t": {
            "t": ts_done,
            "done_n_mean": done_n_mean,
            "done_sum_mean": done_sum_mean,
            "n_episodes": n_episodes_ssgup,
            "n_episodes_done_nonempty_ever": n_episodes_nonempty_done_ever,
        },
        "conclusion": conclusion,
    }

    out_path = "spikes/diag-4c.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[diag_4c] ghi {out_path}")

    return out


if __name__ == "__main__":
    main()
