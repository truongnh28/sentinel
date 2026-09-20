"""
diag_4c2.py -- Cong 4c task 2: phan dinh 77,8% con lai (0.094595) cua khoang cach
hoi quy SSG-up (receding) vs B7U (static), sau khi task 1 da cat nghia 22,2% do C
(_log_audit / done-crediting).

Brief: .superpowers/sdd/2026-09-20-ssg-gate4c/task-2-brief.md

Diem dung: task 1 (spikes/diag_4c.py) da chung minh nhanh KHONG-C (done=None,
"receding_SSGup_noC") van hoi quy so voi tinh (harm 0.545045 > 0.450450), va
nhanh nay KHONG dung self._done gi ca.  Nen moi do luong o day so sanh
  DiagB7U2       = B7U tinh (MinimaxLPUpstream, khong doi)
  DiagSSGUpNoC2  = SSG-up giai lai, EP done=None (tach hoan toan khoi C)
De 77,8% (0.094595 = 0.545045 - 0.450450) la dung cai can do, khong lay C xen vao.

Ba gia thuyet (xem brief SS "Ba gia thuyet"):
  (A) bien duyen (marginal) giai lai KHAC bien duyen tinh tu t=1 tro di, du t=0
      phai TRUNG (cung mot LP het).
  (B) mat tinh nhat quan thoi gian (MPC): coverage thuc te tren tung cua so
      (k,i,s) o cuoi van -- receding phu DAN DEU HON va MONG HON, tinh DON DAY
      hon vao mot tap con.
  (C) rang buoc mot-hanh-dong-moi-task siet KHAC nhau: tong khoi luong (Sigma_k
      u[k][t] + v[t]) ma moi ben THUC SU dung, cong don qua ca van.

KHONG sua lp.py / policies.py.  Cac lop chan doan la BAN SAO cuc bo dang ky vao
policies.REGISTRY luc runtime, giong het cach lam cua diag_4c.py.

Chi dung thu vien chuan (ABC T.6).
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import defaultdict

sys.path.insert(0, ".")

import policies as P          # noqa: E402
import lp                     # noqa: E402
import dprime_sweep as ds     # noqa: E402
from core import seed_of      # noqa: E402

# ---------------------------------------------------------------------------
# Hang so -- KHOP voi ssg-gates.json / diag-4c.json de so do so sanh duoc.
# ---------------------------------------------------------------------------
D_PRIME = 2.2
DELTA = 4                 # o hoi quy nang nhat trong bang cua brief
CLASS_DELTAS = (2, 4)     # lop upstream ma B7U / SSG-up dang chay (self.deltas)
BUDGET = 17.95
SEEDS = (1, 2, 3)
N_WF, H = 40, 8

# Tham chieu tu diag-4c.json (task 1), de kiem hop le TRUOC khi tin so o day.
REFERENCE = {
    "static": {"harm": 0.45045045045045046, "spent": 15.024324324324324},
    "receding_noC": {"harm": 0.545045045045045, "spent": 15.621171171171172},
}


# ---------------------------------------------------------------------------
# 1) Ban sao chan doan
# ---------------------------------------------------------------------------

class DiagB7U2(P.MinimaxLPUpstream):
    """B7U tinh, khong doi logic -- chi ghi (t, action, u_row, v) TRUOC khi ve.

    u_row/v o day CHINH LA self.u[:,t] / self.v[t] ma choose() goc dung -- xem
    MinimaxLP.choose trong policies.py dong 349-384.  Vi la ban tinh, u_row/v
    KHONG doi giua cac episode (chi phu thuoc H/B/kap/kc/deltas, deu co dinh),
    nen viec ghi lai o day chi la de doi chieu true-source-of-truth, khong phai
    de do phuong sai.
    """
    TRACE: list = []

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._ep = {"rng_seed": self.rng_seed, "t": [], "action": [],
                    "u_row": [], "v": []}
        type(self).TRACE.append(self._ep)

    def choose(self, t, retrieved_carriers, signals):
        if t < len(self.v):
            u_row = [self.u[i][t] for i in range(len(self._carriers))]
            v_val = self.v[t]
        else:
            u_row = [0.0] * len(self._carriers)
            v_val = 0.0
        act = super().choose(t, retrieved_carriers, signals)
        self._ep["t"].append(t)
        self._ep["action"].append(act)
        self._ep["u_row"].append(u_row)
        self._ep["v"].append(v_val)
        return act


class DiagSSGUpNoC2(P.SSGRecedingUpstream):
    """SSG-up giai lai, done EP CUNG =None (nhanh 'tat C' cua task 1).

    THAN CHOOSE() LA BAN SAO Y HET SSGReceding.choose() (policies.py dong
    433-459), CHI KHAC MOT CHO: done=None thay vi done=getattr(self,'_done',
    None).  Giong het DiagSSGUpNoC cua diag_4c.py, chi them ghi (u_row, v0,
    Hr, B_rem, n_win) TRUOC khi rut so ngau nhien -- day la bien duyen j=0 THAT
    SU duoc dung de chon hanh dong tai t nay.

    _log_audit VAN duoc goi khi co audit (giong ban goc va giong diag_4c.py) de
    _hist/_done ton tai neu co code khac doc -- khong anh huong vi done=None o
    day, KHONG doc lai _done trong bat ky lan goi lp.solve_remaining_lp nao.
    """
    TRACE: list = []

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._ep = {"rng_seed": self.rng_seed, "t": [], "action": [],
                    "u_row": [], "v0": [], "Hr": [], "B_rem": [], "n_win": []}
        type(self).TRACE.append(self._ep)

    def choose(self, t, retrieved_carriers, signals):
        kap = [P.KAPPA[c] for c in self._carriers]
        H_full = len(self.v) or 8
        B_rem = max(self.budget - self.spent, 0.0)
        u, v, _m, n_win = lp.solve_remaining_lp(
            K=len(self._carriers), H=H_full, t=t, B_rem=B_rem, kap=kap,
            kc=P.KAPPA_COMMIT, deltas=self.deltas, done=None)   # <-- C EP TAT
        act = None
        if n_win == 0 or not v:
            u_row = [0.0] * len(self._carriers)
            v0 = 0.0
        else:
            u_row = [u[i][0] for i in range(len(self._carriers))]
            v0 = v[0]
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
        self._ep["u_row"].append(u_row)
        self._ep["v0"].append(v0)
        self._ep["Hr"].append(H_full - t)
        self._ep["B_rem"].append(B_rem)
        self._ep["n_win"].append(n_win)
        return act


DIAG_B7U2_NAME = "DIAG B7U2 marginals"
DIAG_SSGUP_NOC2_NAME = "DIAG SSG-up2 noC marginals"

P.REGISTRY[DIAG_B7U2_NAME] = DiagB7U2
P.REGISTRY[DIAG_SSGUP_NOC2_NAME] = DiagSSGUpNoC2


# ---------------------------------------------------------------------------
# 2) Tien ich
# ---------------------------------------------------------------------------

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def dedup_by_rng_seed(trace):
    """rng_seed = seed_of(wf.wf_id, seed) -- KHONG phu thuoc carrier k hay Delta
    ma attacker dang thu (runner.paired dong 569).  Vi MinimaxLP.choose /
    SSGReceding.choose CHI doc (self.rng_seed, t, spent, budget) -- khong doc
    retrieved_carriers/signals -- hai lan goi cung rng_seed tao ra dung mot
    chuoi hanh dong.  policy_curve() thu (delta, carrier) x seeds cho MOI
    workflow va rng_seed CHI phu thuoc (wf_id, seed), nen voi 4 carrier duoc
    thu o Delta=4 co dinh, moi (wf, seed) xuat hien ~4 lan TRUNG HET trong
    TRACE.  Dedupe o day de moi (wf, seed) chi dong gop MOT episode cho thong
    ke phan bo cua so (gia thuyet B) va cho trung binh theo t (gia thuyet A/C)
    -- neu khong, trong so se lech theo so lan (d,k) kha thi cho tung workflow,
    khong con la trung binh tren cac workflow nua."""
    seen = {}
    for ep in trace:
        seen[ep["rng_seed"]] = ep     # episode CUOI CUNG voi cung seed de trung
    return list(seen.values())


CARRIERS_ORDER = list(P.CARRIERS) if hasattr(P, "CARRIERS") else None


def carriers_ordered():
    # MinimaxLP._carriers = list(CARRIERS) tu core.CARRIERS -- lay lai dung thu
    # tu bang cach doc mot instance da tao (an toan hon doan ten import).
    return None  # dat lai sau khi co it nhat 1 episode qua self._carriers


# ---------------------------------------------------------------------------
# 3) Chay do
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    wfs = ds.make_corpus(N_WF, H, seed=ds.CORPUS_SEED)

    DiagB7U2.TRACE = []
    DiagSSGUpNoC2.TRACE = []

    policies_to_run = (ds.B1, ds.SENTINEL, DIAG_B7U2_NAME, DIAG_SSGUP_NOC2_NAME)
    print(f"[diag_4c2] do o Delta={DELTA}, d'={D_PRIME}, lop {CLASS_DELTAS}, "
         f"B={BUDGET}, seeds={SEEDS}, N_WF={N_WF}, H={H}")
    print(f"[diag_4c2] policies={policies_to_run}")

    cell = ds.measure_cell(wfs, d_prime=D_PRIME, delta=DELTA, budget=BUDGET,
                           seeds=SEEDS, policies=policies_to_run)

    print(f"[diag_4c2] do xong sau {time.time() - t0:.1f}s, "
         f"n_feasible={cell.n_feasible}/{cell.n_total}, reason={cell.reason}")

    curves = cell.curves
    b7u_c = curves[DIAG_B7U2_NAME]
    ssgup_noc_c = curves[DIAG_SSGUP_NOC2_NAME]

    # ---- kiem hop le TRUOC khi tin so --------------------------------------
    tol = 1e-9
    ok_static = (abs(b7u_c.harm - REFERENCE["static"]["harm"]) < tol and
                abs(b7u_c.spent - REFERENCE["static"]["spent"]) < tol)
    ok_receding = (abs(ssgup_noc_c.harm - REFERENCE["receding_noC"]["harm"]) < tol and
                  abs(ssgup_noc_c.spent - REFERENCE["receding_noC"]["spent"]) < tol)
    print(f"[diag_4c2] kiem hop le: static khop={ok_static} "
         f"(harm={b7u_c.harm!r} spent={b7u_c.spent!r}), "
         f"receding_noC khop={ok_receding} "
         f"(harm={ssgup_noc_c.harm!r} spent={ssgup_noc_c.spent!r})")

    n_carriers = len(P.CARRIERS)

    # ---- dedupe theo rng_seed -----------------------------------------------
    ep_b7u = dedup_by_rng_seed(DiagB7U2.TRACE)
    ep_ssg = dedup_by_rng_seed(DiagSSGUpNoC2.TRACE)
    n_dup_b7u = len(DiagB7U2.TRACE) - len(ep_b7u)
    n_dup_ssg = len(DiagSSGUpNoC2.TRACE) - len(ep_ssg)

    # ==========================================================================
    # GIA THUYET (A): bien duyen dung o tung t
    # ==========================================================================
    # Tinh: mot hang so cho tung t (khong doi giua episode) -- lay tu episode
    # dau tien.
    static_u_by_t = [ep_b7u[0]["u_row"][t] for t in range(H)]
    static_v_by_t = [ep_b7u[0]["v"][t] for t in range(H)]
    # Xac nhan tinh THAT SU khong doi giua cac episode (neu khong, gia dinh sai).
    static_u_is_constant = all(
        all(abs(ep["u_row"][t][k] - static_u_by_t[t][k]) < 1e-9
            for t in range(H) for k in range(n_carriers))
        for ep in ep_b7u)
    static_v_is_constant = all(
        all(abs(ep["v"][t] - static_v_by_t[t]) < 1e-9 for t in range(H))
        for ep in ep_b7u)

    # Giai lai: trung binh tren cac episode (rng_seed) tai tung t.
    receding_u_mean_by_t = []
    receding_v_mean_by_t = []
    n_episodes_by_t = []
    for t in range(H):
        rows = [ep["u_row"][t] for ep in ep_ssg]
        v0s = [ep["v0"][t] for ep in ep_ssg]
        receding_u_mean_by_t.append([mean(r[k] for r in rows) for k in range(n_carriers)])
        receding_v_mean_by_t.append(mean(v0s))
        n_episodes_by_t.append(len(rows))

    l1_by_t = []
    for t in range(H):
        d = sum(abs(receding_u_mean_by_t[t][k] - static_u_by_t[t][k])
               for k in range(n_carriers))
        d += abs(receding_v_mean_by_t[t] - static_v_by_t[t])
        l1_by_t.append(d)

    match_at_t0 = l1_by_t[0] < 1e-6
    # "tu t=0" (brief): t=0 phai TRUNG vi cung mot LP. t>=1 la noi gia thuyet
    # (A) du doan se lech.
    l1_t0 = l1_by_t[0]
    l1_mean_t_ge_1 = mean(l1_by_t[1:])
    l1_max_t = l1_by_t.index(max(l1_by_t))
    l1_max = max(l1_by_t)

    hyp_A = {
        "static_marginal_constant_across_episodes": {
            "u": static_u_is_constant, "v": static_v_is_constant},
        "l1_distance_by_t": l1_by_t,
        "l1_distance_at_t0": l1_t0,
        "match_at_t0": match_at_t0,
        "l1_distance_mean_t_ge_1": l1_mean_t_ge_1,
        "l1_distance_max_t": l1_max_t,
        "l1_distance_max": l1_max,
        "static_u_by_t": static_u_by_t,
        "static_v_by_t": static_v_by_t,
        "receding_u_mean_by_t": receding_u_mean_by_t,
        "receding_v_mean_by_t": receding_v_mean_by_t,
        "n_episodes_by_t": n_episodes_by_t,
    }

    # ==========================================================================
    # GIA THUYET (C): tong khoi luong (Sigma_k u[k,t] + v[t]) THUC SU dung,
    # cong don qua ca van.  Dung CHINH cac hang da tinh o (A).
    # ==========================================================================
    static_mass_by_t = [sum(static_u_by_t[t]) + static_v_by_t[t] for t in range(H)]
    # Receding: trung binh mass moi episode (khong phai trung binh cua trung
    # binh) -- tinh mass TUNG episode roi trung binh, de giu dung phuong sai
    # giua cac episode cho phan bo (duoc dung o phan B).
    receding_mass_per_episode = []
    for ep in ep_ssg:
        m = sum(sum(ep["u_row"][t]) + ep["v0"][t] for t in range(H))
        receding_mass_per_episode.append(m)
    receding_total_mass_mean = mean(receding_mass_per_episode)
    static_total_mass = sum(static_mass_by_t)

    receding_mass_by_t_mean = [sum(sum(ep["u_row"][t]) + ep["v0"][t] for ep in ep_ssg) / len(ep_ssg)
                               for t in range(H)]

    # -- n_win / B_rem tho theo t, tong hop qua 95 episode da dedupe (ep_ssg) --
    # n_win chi phu thuoc (K, H, t, deltas) -- xem lp.solve_remaining_lp dong
    # 187-204 -- KHONG doc B_rem/kap, nen ve ly thuyet phai la hang so qua moi
    # episode tai cung t; kiem tra thuc te (khong gia dinh) bang
    # n_win_constant_across_episodes_by_t o duoi.  B_rem PHU THUOC duong chi
    # tieu thuc te (self.spent tich luy), nen dao dong giua cac episode.
    n_win_by_t_values = [[ep["n_win"][t] for ep in ep_ssg] for t in range(H)]
    n_win_constant_across_episodes_by_t = [
        all(v == vals[0] for v in vals) if vals else True
        for vals in n_win_by_t_values
    ]
    n_win_by_t = [vals[0] if vals else None for vals in n_win_by_t_values]

    brem_by_t_values = [[ep["B_rem"][t] for ep in ep_ssg] for t in range(H)]
    B_rem_by_t = [
        {"min": min(vals), "max": max(vals), "mean": mean(vals)}
        for vals in brem_by_t_values
    ]
    n_episodes_B_rem_leq_0_4_by_t = [
        sum(1 for v in vals if v <= 0.4) for vals in brem_by_t_values
    ]

    hyp_C = {
        "static_mass_by_t": static_mass_by_t,
        "static_total_mass": static_total_mass,
        "receding_mass_by_t_mean": receding_mass_by_t_mean,
        "receding_total_mass_mean": receding_total_mass_mean,
        "diff_receding_minus_static": receding_total_mass_mean - static_total_mass,
        "n_win_by_t": n_win_by_t,
        "n_win_constant_across_episodes_by_t": n_win_constant_across_episodes_by_t,
        "B_rem_by_t": B_rem_by_t,
        "n_episodes_B_rem_leq_0_4_by_t": n_episodes_B_rem_leq_0_4_by_t,
        "n_episodes": len(ep_ssg),
        "note": "mass(t) = Sigma_k u[k, .](t) + v(.)(t) la KHOI LUONG XAC SUAT "
                "ma LP cho phep dat cuoc tai t -- KHONG phai hanh dong da thuc "
                "hien.  mass < 1 nghia la con xac suat 'khong lam gi' o hang do; "
                "mass = 0 nghia la het cua so mo hoac het ngan sach (n_win=0 "
                "hoac B_rem=0 tai t do, xem interpretation ben duoi). "
                "n_win_by_t/B_rem_by_t tong hop qua " + str(len(ep_ssg)) +
                " episode da dedupe (ep_ssg), dung de doi chieu true-source "
                "cho van ban muc 4 cua bao cao -- KHONG suy dien tu mass.",
    }

    # ==========================================================================
    # GIA THUYET (B): coverage tich luy thuc te tren tung cua so (k,i,s)
    # ==========================================================================
    windows = []
    for d in CLASS_DELTAS:
        for k in range(n_carriers):
            for i in range(H - d):
                windows.append((k, i, i + d))

    carriers_list = None
    # Lay dung thu tu carrier tu mot instance da chay -- can mot policy that de
    # doc self._carriers.  Tao mot instance tam thoi cung tham so.
    tmp = P.MinimaxLPUpstream(name="tmp", budget=BUDGET, rng_seed=0, h=H,
                              deltas=CLASS_DELTAS)
    carriers_list = list(tmp._carriers)

    def window_coverage(ep):
        """{(k,i,s) -> so lan carrier k duoc audit thuc su trong [i,s)} cho 1 episode."""
        cov = defaultdict(int)
        for t, act in zip(ep["t"], ep["action"]):
            if act is None or act == "commit":
                continue
            if act not in carriers_list:
                continue
            k = carriers_list.index(act)
            for (kk, i, s) in windows:
                if kk == k and i <= t < s:
                    cov[(kk, i, s)] += 1
        return cov

    def window_stats(episodes):
        n_ep = len(episodes)
        covered_count = defaultdict(int)   # window -> so episode co >=1 audit
        total_count = defaultdict(int)     # window -> tong so audit tren tat ca episode
        for ep in episodes:
            cov = window_coverage(ep)
            for w in windows:
                c = cov.get(w, 0)
                total_count[w] += c
                if c >= 1:
                    covered_count[w] += 1
        prob = {w: covered_count[w] / n_ep if n_ep else float("nan") for w in windows}
        mean_count = {w: total_count[w] / n_ep if n_ep else float("nan") for w in windows}
        return prob, mean_count

    static_prob, static_mean_count = window_stats(ep_b7u)
    receding_prob, receding_mean_count = window_stats(ep_ssg)

    def dist_stats(prob_map):
        vals = list(prob_map.values())
        bins = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9]
        hist = {f">={b}": sum(1 for v in vals if v >= b) for b in bins}
        return {
            "min": min(vals), "max": max(vals), "mean": mean(vals),
            "n_windows": len(vals),
            "n_zero_coverage": sum(1 for v in vals if v <= 1e-9),
            "histogram_at_least": hist,
        }

    static_dist = dist_stats(static_prob)
    receding_dist = dist_stats(receding_prob)

    # "dan deu hon VA mong hon" (brief) doi hoi CA HAI: (1) it cua so co
    # coverage rat cao (>=0.75) hon, VA (2) it cua so co coverage = 0 hon
    # (nhieu cua so co coverage TRUNG BINH thap-vua hon la 0-hoac-cao). Do
    # bang do lech chuan cua phan bo coverage tren cac cua so (thap hon =
    # dan deu hon) va so cua so o cac dau mut (cao/0).
    def stdev(prob_map):
        vals = list(prob_map.values())
        m = mean(vals)
        var = mean((v - m) ** 2 for v in vals)
        return var ** 0.5

    static_std = stdev(static_prob)
    receding_std = stdev(receding_prob)

    more_even = receding_std < static_std
    thinner = receding_dist["mean"] < static_dist["mean"]
    min_lower = receding_dist["min"] <= static_dist["min"]

    hyp_B = {
        "n_windows": len(windows),
        "n_episodes_static": len(ep_b7u),
        "n_episodes_receding": len(ep_ssg),
        "static_distribution": static_dist,
        "receding_distribution": receding_dist,
        "static_stdev_across_windows": static_std,
        "receding_stdev_across_windows": receding_std,
        "receding_more_even_than_static": more_even,
        "receding_thinner_mean_than_static": thinner,
        "receding_min_window_leq_static_min": min_lower,
        "per_window_detail": [
            {"window": list(w), "static_prob": static_prob[w],
            "receding_prob": receding_prob[w],
            "static_mean_count": static_mean_count[w],
            "receding_mean_count": receding_mean_count[w]}
            for w in windows
        ],
    }

    # ==========================================================================
    # Ket luan
    # ==========================================================================
    total_gap_harm = ssgup_noc_c.harm - b7u_c.harm   # ~ 0.094595, muc tieu 77.8%

    verdict_A = "CHUA PHAN DINH"
    if match_at_t0 and l1_mean_t_ge_1 > 5 * max(l1_t0, 1e-9):
        verdict_A = "DUNG (lech ro tu t=1, trong khi t=0 trung)"
    elif not match_at_t0:
        verdict_A = "NGHI NGO (t=0 KHONG trung -- vi pham gia dinh nen doc lai)"
    elif l1_mean_t_ge_1 < 0.05:
        verdict_A = "BI BAC BO (bien duyen gan nhu trung suot van)"

    verdict_B = "CHUA PHAN DINH"
    if more_even and thinner:
        verdict_B = "DUNG (receding dan deu hon VA mong hon tren nhieu cua so)"
    elif not more_even and not thinner:
        verdict_B = "BI BAC BO (receding khong dan deu hon, khong mong hon)"

    verdict_C = "CHUA PHAN DINH"
    mass_diff_frac = (hyp_C["diff_receding_minus_static"] / static_total_mass
                      if static_total_mass else float("nan"))
    if abs(mass_diff_frac) < 0.02:
        verdict_C = "BI BAC BO (tong khoi luong cho phep gan nhu bang nhau, lech < 2%)"
    else:
        verdict_C = ("DUNG (chieu " +
                     ("TANG" if mass_diff_frac > 0 else "GIAM") +
                     f", lech {mass_diff_frac:+.1%})")

    conclusion = {
        "hypothesis_A_boundary_mismatch": {"verdict": verdict_A},
        "hypothesis_B_time_inconsistency": {"verdict": verdict_B},
        "hypothesis_C_per_task_row_budget": {"verdict": verdict_C},
        "total_regression_gap_harm_noC": total_gap_harm,
        "note": "Day la 0.094595 goc cua brief (77,8% cua tong khoang cach "
                "0.121622) -- do TRUC TIEP tren cap (static, receding_noC) o "
                "day, khong phai lay lai tu diag-4c.json, nen co the lech vai "
                "ULP so voi 0.094595 neu co bat ky khac biet nao trong duong "
                "chay; kiem hop le o tren (ok_static/ok_receding) la de dam bao "
                "khong co lech.",
    }

    out = {
        "meta": {"d_prime": D_PRIME, "delta": DELTA, "class_deltas": list(CLASS_DELTAS),
                 "budget": BUDGET, "seeds": list(SEEDS), "n_wf": N_WF, "H": H,
                 "n_feasible": cell.n_feasible, "n_total": cell.n_total,
                 "reason": cell.reason, "runtime_s": time.time() - t0,
                 "n_dedup_dropped_b7u": n_dup_b7u, "n_dedup_dropped_ssg": n_dup_ssg,
                 "n_unique_episodes_b7u": len(ep_b7u), "n_unique_episodes_ssg": len(ep_ssg)},
        "reference_diag_4c_json": REFERENCE,
        "validity_check": {
            "static_matches_reference": ok_static,
            "receding_noC_matches_reference": ok_receding,
            "measured_static": {"harm": b7u_c.harm, "spent": b7u_c.spent},
            "measured_receding_noC": {"harm": ssgup_noc_c.harm, "spent": ssgup_noc_c.spent},
        },
        "hypothesis_A": hyp_A,
        "hypothesis_B": hyp_B,
        "hypothesis_C": hyp_C,
        "conclusion": conclusion,
    }

    out_path = "spikes/diag-4c2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[diag_4c2] ghi {out_path}")

    # In gon ra console de doc nhanh khi chay tay.
    print(f"\n[diag_4c2] === TOM TAT ===")
    print(f"static: harm={b7u_c.harm:.6f} spent={b7u_c.spent:.6f}")
    print(f"receding_noC: harm={ssgup_noc_c.harm:.6f} spent={ssgup_noc_c.spent:.6f}")
    print(f"gap = {total_gap_harm:.6f}")
    print(f"(A) l1_t0={l1_t0:.4f} match_t0={match_at_t0} "
         f"l1_mean(t>=1)={l1_mean_t_ge_1:.4f} max_t={l1_max_t} max={l1_max:.4f} "
         f"-> {verdict_A}")
    print(f"(B) static std={static_std:.4f} mean={static_dist['mean']:.4f} "
         f"min={static_dist['min']:.4f} n_zero={static_dist['n_zero_coverage']} | "
         f"receding std={receding_std:.4f} mean={receding_dist['mean']:.4f} "
         f"min={receding_dist['min']:.4f} n_zero={receding_dist['n_zero_coverage']} "
         f"-> {verdict_B}")
    print(f"(C) static_total_mass={static_total_mass:.4f} "
         f"receding_total_mass_mean={receding_total_mass_mean:.4f} "
         f"diff={hyp_C['diff_receding_minus_static']:+.4f} ({mass_diff_frac:+.1%}) "
         f"-> {verdict_C}")

    return out


if __name__ == "__main__":
    main()
