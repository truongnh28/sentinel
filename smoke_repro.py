#!/usr/bin/env python3
"""
smoke_repro.py — Tái lập SMOKE TEST của đề xuất FSE-2027-15 (Sentinel).

PHẠM VI (đúng như hồ sơ gốc tuyên bố cho smoke test):
    "một trò chơi Stackelberg hữu hạn được giải bằng liệt kê phản ứng tốt nhất
     của kẻ tấn công"
Không cần workflow thật, không cần LLM, không cần ngân sách compute.

MỤC TIÊU: tái lập *cơ chế, dấu và thứ hạng* của 4 kiểm tra trong smoke test gốc.
KHÔNG phải: khớp từng chữ số. Mã nguồn Sentinel (~9.100 dòng) không công khai và
mọi con số trong manuscript là *dự phóng (projected)*.

PHỤ THUỘC: không có. Chỉ thư viện chuẩn Python >= 3.8.
    (scipy là tùy chọn — dùng --crosscheck để đối chiếu nghiệm LP nếu có sẵn.)

CHẠY:
    python3 smoke_repro.py              # chạy 5 kiểm tra, in báo cáo
    python3 smoke_repro.py --json out.json
    python3 smoke_repro.py --crosscheck # đối chiếu LP với scipy nếu cài được

MÃ THOÁT: 0 nếu mọi kiểm tra PASS, 1 nếu có kiểm tra FAIL.

Tài liệu đi kèm:
    ../../261-Master-Proposal-Analysis/Huong-dan-tai-lap-test-va-baseline-FSE-2027-15.md
    ../../261-Master-Proposal-Analysis/Toan-canh-de-tai-FSE-2027-15-Sentinel.md
"""
from __future__ import annotations
import argparse, json, sys

# ═══════════════════════════════════════════════════════════════════ CẤU HÌNH

CFG = dict(
    K=4,                    # số carrier: memory / cached skill / tool queue / branch
    H=8,                    # số task trong một workflow (manuscript: 6–14)
    psi=0.95,               # true-positive rate của detector
    kappa_bar=2.00,         # chi phí audit trung bình một carrier (HIỆU CHUẨN)
    kappa_commit=4.10,      # chi phí audit commit đo được (manuscript §7)
    commit_harm_target=0.48,  # hiệu chuẩn B sao cho audit-at-commit ra đúng 0.48
    het_model="mean",       # "mean" | "min" — xem carrier_costs()
)
CARRIERS = ["memory", "skill", "queue", "branch"]

# Chi phí audit theo GIAI ĐOẠN, đo được, manuscript §7 (chèn/truy xuất/ủy quyền/commit)
PUBLISHED_STAGE_COSTS = [0.4, 0.9, 1.6, 4.1]
PUBLISHED_CHI = 1.34        # con số manuscript nêu ngay sau bốn chi phí trên

# Số đích của smoke test gốc (Huong-dan-tai-lap... Mục 4)
TARGET_CHECK2 = {           # tại chi=1.34, delta=2
    "audit-on-insertion": 1.00,
    "deterministic":      1.00,
    "cost-greedy":        0.74,
    "audit-at-commit":    0.48,
    "uniform random":     0.45,
    "minimax":            0.43,
}
TARGET_GAIN = {             # % giảm harm của minimax so với audit-at-commit
    0.00: {0: 0.0, 1:  2.0, 2: 44.0, 4: 86.0},
    1.34: {0: 0.0, 1: -4.0, 2: 12.0, 4: 62.0},
}

# ═══════════════════════════════════════════════════════════════════ MÔ HÌNH

def carrier_costs(chi, K, cfg):
    """Sinh vector chi phí carrier thỏa ĐÚNG định nghĩa chi = (max-min)/mean.

    Còn một bậc tự do mà manuscript chưa chốt (xem Mục 6.2 của hướng dẫn tái lập):
    tăng chi thì TỔNG chi phí phủ đều mọi carrier có tăng theo không?

      "mean" — neo giá trị TRUNG BÌNH. sum(kappa) = K*kappa_bar, hằng số theo chi.
               => làm carrier này đắt lên thì carrier khác rẻ đi.
      "min"  — neo giá trị NHỎ NHẤT. Khớp cách diễn đạt "differentiating audit
               depths" của manuscript: làm sâu thêm carrier đắt => TỔNG chi phí
               TĂNG theo chi.

    Neo của "min" đặt tại kappa_bar (KHÔNG phải kappa_lo=0.4 đo được) để tại chi=0
    hai mô hình TRÙNG NHAU và cột chi=0 so sánh được. Neo tại 0.4 chỉ co giãn toàn
    bộ thang chi phí xuống 5 lần, làm hai mô hình không còn chung gốc.
    """
    model = cfg["het_model"]
    if K == 1:
        return [cfg["kappa_bar"]]
    off = [-0.5 + i / (K - 1) for i in range(K)]          # linspace(-0.5, 0.5, K)
    if model == "mean":
        kap = [cfg["kappa_bar"] * (1.0 + chi * o) for o in off]
    else:
        if chi >= 2.0:                                     # r = (2+chi)/(2-chi) phân kỳ
            raise ValueError(f"het_model='min' chỉ định nghĩa với chi < 2, nhận {chi}")
        lo = cfg["kappa_bar"]   # xem docstring: neo để chi=0 trùng mean-model
        r = (2.0 + chi) / (2.0 - chi)                      # kappa_hi / kappa_lo
        kap = [lo + (lo * r - lo) * i / (K - 1) for i in range(K)]
    _assert_chi(kap, chi)
    return kap

def _assert_chi(kap, chi):
    """Bất biến: vector sinh ra phải thỏa đúng định nghĩa chi."""
    mean = sum(kap) / len(kap)
    got = (max(kap) - min(kap)) / mean
    assert abs(got - chi) < 1e-9, f"chi sinh sai: yêu cầu {chi}, thực tế {got:.6f}"

def budget(cfg):
    """Hiệu chuẩn B để audit-at-commit cho đúng worst-case harm = 0.48.

    audit-at-commit trải đều ngân sách lên commit của mọi task:
        v = B / (kappa_commit * H),  harm = 1 - psi * v
    """
    v_needed = (1.0 - cfg["commit_harm_target"]) / cfg["psi"]
    return v_needed * cfg["kappa_commit"] * cfg["H"]

def attacker_actions(K, H, delta):
    """a = (k, iota, sigma) với sigma = iota + delta <= H-1. Liệt kê toàn bộ."""
    return [(k, i, i + delta) for k in range(K) for i in range(H - delta)]

def coverage(u, v, a):
    """u[k][t]: coverage audit upstream carrier k tại task t. v[t]: coverage commit.

    Audit upstream bắt được poison nếu chạy trong cửa sổ [iota, sigma).
    Audit commit tại sigma bắt đúng lúc harm hiện ra.

    ĐÂY LÀ CƠ CHẾ SINH RA THEOREM 4: commit chỉ có MỘT cơ hội tại sigma bất kể
    delta, còn chính sách trải rộng có thêm delta cơ hội bên trong cửa sổ.
    """
    k, i, s = a
    return sum(u[k][t] for t in range(i, s)) + v[s]

def harm(u, v, a, psi):
    return 1.0 - psi * min(1.0, coverage(u, v, a))

def worst_case(u, v, K, H, delta, psi):
    return max(harm(u, v, a, psi) for a in attacker_actions(K, H, delta))

def cost_of(u, v, kap, kc):
    return sum(kap[k] * sum(u[k]) for k in range(len(kap))) + kc * sum(v)

# ══════════════════════════════════════════════════════════════ SIMPLEX (LP)

def simplex_max(c, A, b, tol=1e-9, max_iter=50000):
    """max c^T x  s.t.  A x <= b,  x >= 0,  với b >= 0.

    Vì mọi b >= 0 nên cơ sở slack ban đầu đã khả thi — không cần pha 1.
    Dùng quy tắc Dantzig, chuyển sang quy tắc Bland sau 500 bước để chống xoay vòng.
    """
    m, n = len(A), len(c)
    assert all(bi >= -tol for bi in b), "simplex_max yêu cầu b >= 0"
    T = [list(A[i]) + [1.0 if j == i else 0.0 for j in range(m)] + [b[i]] for i in range(m)]
    T.append([-ci for ci in c] + [0.0] * m + [0.0])
    basis = [n + i for i in range(m)]
    for it in range(max_iter):
        obj = T[m]
        cand = [j for j in range(n + m) if obj[j] < -tol]
        if not cand:
            break
        pc = min(cand, key=lambda j: obj[j]) if it < 500 else min(cand)
        pr, best = -1, None
        for i in range(m):
            if T[i][pc] > tol:
                r = T[i][-1] / T[i][pc]
                if best is None or r < best - 1e-12 or (abs(r - best) <= 1e-12 and basis[i] < basis[pr]):
                    best, pr = r, i
        if pr < 0:
            raise RuntimeError("LP không bị chặn — mô hình sai")
        pv = T[pr][pc]
        T[pr] = [x / pv for x in T[pr]]
        for i in range(m + 1):
            if i != pr and abs(T[i][pc]) > tol:
                f = T[i][pc]
                T[i] = [a - f * bb for a, bb in zip(T[i], T[pr])]
        basis[pr] = pc
    else:
        raise RuntimeError("simplex không hội tụ")
    x = [0.0] * n
    for i in range(m):
        if basis[i] < n:
            x[basis[i]] = T[i][-1]
    return x, T[m][-1]

# ══════════════════════════════════════════════════════════════════ BASELINE
# Mỗi chính sách trả về (u, v) với u[k][t], v[t] trong [0,1].

def _zeros(K, H):
    return [[0.0] * H for _ in range(K)], [0.0] * H

def p_commit(K, H, B, kap, kc, **_):
    """B1 — dồn toàn bộ ngân sách vào audit commit của mọi task."""
    u, v = _zeros(K, H)
    c = min(1.0, B / (kc * H))
    return u, [c] * H

def p_deterministic(K, H, B, kap, kc, **_):
    """Lịch trình TẤT ĐỊNH: xoay vòng carrier theo task, coverage = 1.
    Attacker quan sát được lịch nên chỉ việc chọn carrier không nằm trong cửa sổ."""
    u, v = _zeros(K, H)
    spent = 0.0
    for t in range(H):
        k = t % K
        if spent + kap[k] <= B:
            u[k][t] = 1.0
            spent += kap[k]
    return u, v

def p_on_insertion(K, H, B, kap, kc, **_):
    """B3 — chỉ audit tại điểm chèn 'điển hình' (carrier memory)."""
    u, v = _zeros(K, H)
    c = min(1.0, B / (kap[0] * H))
    u[0] = [c] * H
    return u, v

def p_cost_greedy(K, H, B, kap, kc, **_):
    """Phân bổ tỉ lệ NGHỊCH với chi phí — audit carrier rẻ nhiều hơn."""
    u, v = _zeros(K, H)
    w = [1.0 / kap[k] for k in range(K)]
    s = sum(w)
    for k in range(K):
        u[k] = [min(1.0, (B * w[k] / s) / (kap[k] * H))] * H
    return u, v

def p_uniform(K, H, B, kap, kc, **_):
    """B2 — ngẫu nhiên ĐỒNG ĐỀU: coverage bằng nhau trên mọi ô (không phải chi phí
    bằng nhau). c * (H*sum(kap) + H*kc) = B."""
    total = H * (sum(kap) + kc)
    c = min(1.0, B / total)
    return [[c] * H for _ in range(K)], [c] * H

def p_minimax(K, H, B, kap, kc, delta=0, psi=1.0, **_):
    """B7 — nghiệm minimax chính xác bằng quy hoạch tuyến tính.

        max  m
        s.t. m <= coverage(a)        với mọi hành động a của attacker
             sum_k kap_k*sum_t u[k,t] + kc*sum_t v[t] <= B
             0 <= u, v, m <= 1

    worst-case harm = 1 - psi*m*, vì
        max_a [1 - psi*min(1,cov(a))] = 1 - psi*min(1, min_a cov(a))
    và cận trên m <= 1 đã lo phần min(1, .).

    Đây đúng là công cụ của Conitzer & Sandholm (EC 2006): SSE tính bằng LP.
    """
    nU, nV = K * H, H
    n = nU + nV + 1
    im = n - 1                                    # chỉ số biến m
    c = [0.0] * n
    c[im] = 1.0
    A, b = [], []
    for (k, i, s) in attacker_actions(K, H, delta):    # m - cov(a) <= 0
        row = [0.0] * n
        for t in range(i, s):
            row[k * H + t] = -1.0
        row[nU + s] += -1.0
        row[im] = 1.0
        A.append(row); b.append(0.0)
    row = [0.0] * n                                    # ràng buộc ngân sách
    for k in range(K):
        for t in range(H):
            row[k * H + t] = kap[k]
    for t in range(H):
        row[nU + t] = kc
    A.append(row); b.append(B)
    for j in range(n):                                 # cận trên 1 cho mọi biến
        row = [0.0] * n
        row[j] = 1.0
        A.append(row); b.append(1.0)
    x, _ = simplex_max(c, A, b)
    u = [[x[k * H + t] for t in range(H)] for k in range(K)]
    v = [x[nU + t] for t in range(H)]
    return u, v

POLICIES = [
    ("audit-on-insertion", p_on_insertion),
    ("deterministic",      p_deterministic),
    ("cost-greedy",        p_cost_greedy),
    ("audit-at-commit",    p_commit),
    ("uniform random",     p_uniform),
    ("minimax",            p_minimax),
]

# ═══════════════════════════════════════════════════════════════════ CHẠY

def run(chi, delta, cfg=None, het_model=None, K=None):
    cfg = dict(cfg or CFG)
    if het_model:
        cfg["het_model"] = het_model
    K = K if K is not None else cfg["K"]
    H, psi, kc = cfg["H"], cfg["psi"], cfg["kappa_commit"]
    kap = carrier_costs(chi, K, cfg)
    B = budget(cfg)
    out = {}
    for name, fn in POLICIES:
        u, v = fn(K=K, H=H, B=B, kap=kap, kc=kc, delta=delta, psi=psi)
        assert cost_of(u, v, kap, kc) <= B + 1e-6, f"{name} vượt ngân sách"
        out[name] = worst_case(u, v, K, H, delta, psi)
    # bất biến: minimax phải tối ưu, không chính sách nào được tốt hơn
    best_other = min(x for k, x in out.items() if k != "minimax")
    assert out["minimax"] <= best_other + 1e-6, \
        f"minimax ({out['minimax']:.4f}) tệ hơn {best_other:.4f} — LP sai"
    return out

def saturated(chi, delta, het_model=None, K=None):
    """minimax có đạt coverage tối đa m=1 không? Nếu có thì độ lợi BÃO HÒA và
    mọi hiệu ứng của chi bị che mất."""
    r = run(chi=chi, delta=delta, het_model=het_model, K=K)
    return r["minimax"] <= 1.0 - CFG["psi"] + 1e-9

def gain(r):
    """% giảm worst-case harm của minimax so với audit-at-commit."""
    c = r["audit-at-commit"]
    return 100.0 * (c - r["minimax"]) / c

# ═══════════════════════════════════════════════════════════════════ KIỂM TRA

def hr(title):
    print("\n" + "═" * 78)
    print(title)
    print("═" * 78)

def check2(results):
    hr("KIỂM TRA 2 — ngẫu nhiên hóa quan trọng hơn thích nghi   (chi=1.34, delta=2)")
    r = run(chi=1.34, delta=2)
    results["check2"] = r
    print(f"  {'chính sách':22s} {'đích':>7} {'tái lập':>9}   nhận xét")
    print("  " + "-" * 62)
    for name, _ in POLICIES:
        tgt, got = TARGET_CHECK2[name], r[name]
        d = abs(got - tgt)
        note = "khớp" if d < 0.02 else ("cùng chiều, lệch độ lớn" if d < 0.25 else "LỆCH ĐÁNG KỂ")
        print(f"  {name:22s} {tgt:7.2f} {got:9.3f}   {note}")
    order = ["audit-on-insertion", "cost-greedy", "audit-at-commit", "uniform random", "minimax"]
    ok = all(r[order[i]] >= r[order[i + 1]] - 1e-9 for i in range(len(order) - 1))
    print(f"\n  → thứ hạng đúng như smoke test gốc: {'PASS' if ok else 'FAIL'}")
    print("    (kiểm tra tuyên bố về DẤU và THỨ HẠNG, không tuyên bố khớp chữ số)")
    return ok

def check13(results):
    hr("KIỂM TRA 1 & 3 — ranh giới chế độ và chiều tác động của chi")
    deltas = (0, 1, 2, 4)
    allok = True
    results["check13"] = {}
    for model in ("mean", "min"):
        desc = ("neo TRUNG BÌNH — sum(kappa) hằng số theo chi"
                if model == "mean" else
                "neo NHỎ NHẤT — sum(kappa) TĂNG theo chi")
        print(f"\n  [het_model = {model}]  {desc}")
        print(f"    {'chi':>5} │ " + " │ ".join(f"d={d:<7}" for d in deltas))
        print("    " + "─" * 46)
        rows = {}
        for chi in (0.00, 1.34):
            cells = [gain(run(chi=chi, delta=d, het_model=model)) + 0.0 for d in deltas]
            cells = [0.0 if abs(g) < 1e-9 else g for g in cells]
            rows[chi] = cells
            tgt = " ".join(f"{TARGET_GAIN[chi][d]:+.0f}" for d in deltas)
            print(f"    {chi:>5.2f} │ " + " │ ".join(f"{g:+7.1f}%" for g in cells)
                  + f"   (đích: {tgt})")
        results["check13"][model] = rows
        zero = all(abs(rows[c][0]) < 1e-6 for c in rows)
        inc = all(rows[c][i] <= rows[c][i + 1] + 1e-9 for c in rows for i in range(len(deltas) - 1))
        narrow = any(rows[1.34][i] < rows[0.00][i] - 1e-9 for i in range(len(deltas)))
        print(f"    KT1a  độ lợi = 0 tại delta=0        : {'PASS' if zero else 'FAIL'}")
        print(f"    KT1b  độ lợi TĂNG theo delta        : {'PASS' if inc else 'FAIL'}")
        sat = [d for d in deltas if saturated(1.34, d, het_model=model)]
        print(f"    KT3   chi THU HẸP độ lợi            : "
              f"{'PASS' if narrow else 'FAIL — chi không có hiệu ứng nào'}")
        if sat:
            cap = max(max(r) for r in rows.values())
            print(f"    ⚠  BÃO HÒA tại delta={sat} — minimax đạt coverage tối đa m=1 nên")
            print(f"       độ lợi kịch trần {cap:.1f}% và mọi hiệu ứng của chi bị che ở đó.")
            print(f"       Smoke test gốc KHÔNG bão hòa (+86/+62) ⇒ ngân sách hiệu dụng")
            print(f"       của họ CHẶT HƠN mô hình này. Đây là khác biệt thứ tư cần hỏi.")
        if model == "mean" and not narrow:
            print("          ↳ ĐÚNG NHƯ LÝ THUYẾT: xem mục CẤU TRÚC bên dưới.")
        allok = allok and zero and inc and (narrow or model == "mean")
    return allok

def check4(results):
    hr("KIỂM TRA 4 — audit-on-insertion là chính sách TỆ NHẤT")
    ok = True
    for chi in (0.00, 0.50, 1.34):
        for d in (0, 1, 2, 4):
            r = run(chi=chi, delta=d)
            if r["audit-on-insertion"] < max(r.values()) - 1e-9:
                ok = False
                print(f"    FAIL tại chi={chi}, delta={d}")
    r = run(1.34, 2)
    results["check4"] = r["audit-on-insertion"]
    print(f"  tệ nhất trên toàn lưới (3 chi × 4 delta) : {'PASS' if ok else 'FAIL'}")
    print(f"  worst-case harm của nó (chi=1.34, d=2)   : {r['audit-on-insertion']:.3f}   (đích 1.00)")
    print("  cơ chế: attacker chỉ việc chèn qua carrier không được theo dõi.")
    return ok

def diag_single_carrier(results):
    """CHẨN ĐOÁN (không nằm trong 4 kiểm tra gốc, không quyết định mã thoát)."""
    hr("CHẨN ĐOÁN A — Hệ quả 5, vế 'một carrier': mô hình này KHÔNG tái lập được")
    print("  Hệ quả 5: commit đủ khi delta nhỏ HOẶC khi chỉ có một carrier (K=1).")
    print("  KT1 đã kiểm vế delta — PASS. Đây kiểm vế K=1.\n")
    print(f"    {'delta':>5} │ {'commit':>8} │ {'minimax':>8} │ {'độ lợi':>8}")
    print("    " + "─" * 40)
    ok = True
    gains = []
    for d in (0, 1, 2, 4):
        r = run(chi=0.0, delta=d, K=1)
        g = gain(r)
        gains.append(g)
        print(f"    {d:>5} │ {r['audit-at-commit']:8.3f} │ {r['minimax']:8.3f} │ {g:+7.1f}%")
    ok = all(g < 1e-6 for g in gains)
    results["diag_single_carrier"] = gains
    print(f"\n  → K=1: minimax KHÔNG vượt được commit? {'ĐÚNG' if ok else 'SAI'}")
    if not ok:
        print("""
  DIỄN GIẢI — đây là giới hạn của mô hình tái lập, không phải phản bác Hệ quả 5.

  Mô hình này gộp HAI lợi thế khác nhau của việc audit upstream:
    (a) LỢI THẾ THÔNG TIN — biết nhìn carrier nào. Đây là thứ Theorem 4 và
        Hệ quả 5 nói tới, và nó BIẾN MẤT khi K=1.
    (b) CHÊNH LỆCH GIÁ — audit upstream (kappa_bar=2.0) rẻ hơn audit commit
        (kappa_commit=4.1), nên với cửa sổ delta ta mua được nhiều coverage hơn
        trên cùng ngân sách. Cái này KHÔNG biến mất khi K=1.

  Vì (b) còn nguyên, minimax vẫn thắng ở K=1 — bằng một cơ chế mà Hệ quả 5 không
  hề dựa vào. Cùng bản chất với khác biệt 6.3: mô hình tái lập bỏ qua chi phí
  thông tin, nên LẠC QUAN một cách có hệ thống.

  HỎI THẦY: trong smoke test gốc, audit upstream và audit commit có cùng chi phí
  đơn vị không? Nếu có thì (b) triệt tiêu và K=1 sẽ ra đúng Hệ quả 5.""")
    return ok

# ══════════════════════════════════════════════════════ PHÁT HIỆN CẦN HỎI THẦY

def report_discrepancies():
    hr("BA KHÁC BIỆT CẦN HỎI THẦY  (giá trị nhất của việc tái lập)")

    print("\n  6.1 — chi = 1.34 KHÔNG suy ra được từ chi phí đã công bố")
    k = PUBLISHED_STAGE_COSTS
    mean = sum(k) / len(k)
    chi_calc = (max(k) - min(k)) / mean
    print(f"      manuscript §7: chi phí đo được = {k} CPU-phút (theo GIAI ĐOẠN)")
    print(f"      manuscript định nghĩa chi trên CARRIER: chi = (max-min)/mean")
    print(f"      áp công thức:  mean={mean:.2f}  max-min={max(k)-min(k):.1f}"
          f"  →  chi = {chi_calc:.2f}")
    print(f"      manuscript lại nêu:  chi = {PUBLISHED_CHI}")
    for nm, val in (("(max-min)/sum", (max(k)-min(k))/sum(k)),
                    ("hệ số biến thiên", (sum((x-mean)**2 for x in k)/len(k))**0.5/mean),
                    ("(max-min)/trung vị", (max(k)-min(k))/((k[1]+k[2])/2))):
        print(f"        thử biến thể {nm:20s} = {val:.2f}")
    print(f"      → không biến thể nào cho {PUBLISHED_CHI}. HỎI: bảng chi phí theo")
    print(f"        carrier là bảng riêng chưa nêu, hay chi tính bằng công thức khác?")
    print(f"        Không có câu trả lời thì KHÔNG CẤU HÌNH ĐƯỢC lưới chi.")

    print("\n  6.2 — mô hình chi phí của chi chưa xác định (hai cách đọc)")
    print("      'equalising or differentiating audit depths' nghiêng về neo NHỎ NHẤT,")
    print("      nhưng cách đó làm tổng chi phí tăng theo chi. HỎI: khi quét chi,")
    print("      ngân sách hiệu dụng giữ nguyên hay chi cao đồng nghĩa mất ngân sách?")

    print("\n  6.3 — tại delta=1 bản tái lập LẠC QUAN hơn nhiều so với đích (+2%)")
    g = gain(run(chi=0.0, delta=1))
    print(f"      tái lập: {g:+.1f}%   ·   đích: +2.0%")
    print("      Mô hình này cho defender TOÀN BỘ cửa sổ [iota,sigma) làm cơ hội")
    print("      phát hiện, tức bỏ qua CHI PHÍ THÔNG TIN mà Theorem 4 mô tả: với một")
    print("      alarm duy nhất, hậu nghiệm trên (k,iota,sigma) còn gần như đều nên")
    print("      defender chưa biết nhìn vào đâu. Cùng lý do khiến minimax tái lập")
    print("      lạc quan hơn đích. HỎI: cấu hình particle filter và (psi,phi,beta,tau,eta_Q)?")

def report_structure():
    hr("PHÁT HIỆN CẤU TRÚC — vì sao neo TRUNG BÌNH cho chi hiệu ứng BẰNG KHÔNG")
    print("""
  Trong mô hình này, ràng buộc của attacker chỉ phụ thuộc iota (qua v[iota+delta]),
  KHÔNG phụ thuộc carrier k. Nên mọi carrier đối mặt cùng một bài toán con, nghiệm
  tối ưu u[k,·] giống hệt nhau với mọi k, và tổng chi phí upstream

        sum_k kappa_k * sum_t u[k,t]  =  (sum_k kappa_k) * U

  chỉ phụ thuộc TỔNG sum(kappa), không phụ thuộc PHÂN BỐ của nó.

  Với neo TRUNG BÌNH thì sum(kappa) = K*kappa_bar là hằng số theo chi
  ⇒ nghiệm LP bất biến theo chi ⇒ độ lợi hệt nhau. Đây là kết quả của mô hình,
  KHÔNG phải lỗi số học.

  Hệ quả: muốn chi có hiệu ứng, hoặc (a) neo NHỎ NHẤT để sum(kappa) tăng theo chi,
  hoặc (b) mô hình phải cho commit audit PHỤ THUỘC CARRIER — lúc đó phân bố chi phí
  mới có chỗ tác động. Manuscript chưa nói rõ là cái nào. Đây là dạng chặt hơn của
  câu hỏi 6.2 và nên hỏi thầy cùng lúc.""")
    a = run(chi=0.00, delta=2, het_model="mean")["minimax"]
    b = run(chi=1.34, delta=2, het_model="mean")["minimax"]
    print(f"  Kiểm chứng: minimax(chi=0) = {a:.6f} · minimax(chi=1.34) = {b:.6f}"
          f" · lệch = {abs(a-b):.2e}")

# ═══════════════════════════════════════════════════════════════════ CROSSCHECK

def crosscheck():
    hr("ĐỐI CHIẾU LP VỚI SCIPY (tùy chọn)")
    try:
        from scipy.optimize import linprog
    except ImportError:
        print("  scipy không có sẵn — bỏ qua. Simplex nội bộ đã tự kiểm bằng bất biến")
        print("  'minimax phải tối ưu' trong mọi lần run().")
        return True
    import itertools
    ok = True
    for chi, d in itertools.product((0.0, 1.34), (0, 1, 2, 4)):
        cfg = dict(CFG); K, H = cfg["K"], cfg["H"]
        kap, B, kc = carrier_costs(chi, K, cfg), budget(cfg), cfg["kappa_commit"]
        nU, n = K * H, K * H + H + 1
        c = [0.0] * n; c[n - 1] = -1.0
        A, b = [], []
        for (k, i, s) in attacker_actions(K, H, d):
            row = [0.0] * n
            for t in range(i, s): row[k * H + t] = -1.0
            row[nU + s] += -1.0; row[n - 1] = 1.0
            A.append(row); b.append(0.0)
        row = [0.0] * n
        for k in range(K):
            for t in range(H): row[k * H + t] = kap[k]
        for t in range(H): row[nU + t] = kc
        A.append(row); b.append(B)
        r = linprog(c, A_ub=A, b_ub=b, bounds=[(0, 1)] * n, method="highs")
        mine = run(chi=chi, delta=d)["minimax"]
        theirs = 1.0 - CFG["psi"] * (-r.fun)
        d_ok = abs(mine - theirs) < 1e-6
        ok = ok and d_ok
        print(f"  chi={chi:<5} d={d}: nội bộ {mine:.6f} · scipy {theirs:.6f} "
              f"{'OK' if d_ok else 'LỆCH'}")
    return ok

# ═══════════════════════════════════════════════════════════════════ MAIN

def main():
    ap = argparse.ArgumentParser(description="Tái lập smoke test FSE-2027-15 Sentinel")
    ap.add_argument("--json", metavar="FILE", help="ghi kết quả ra file JSON")
    ap.add_argument("--crosscheck", action="store_true", help="đối chiếu LP với scipy nếu có")
    args = ap.parse_args()

    print("╔" + "═" * 76 + "╗")
    print("║ TÁI LẬP SMOKE TEST — FSE-2027-15 Sentinel" + " " * 34 + "║")
    print("║ Trò chơi Stackelberg hữu hạn · LP minimax · liệt kê best-response" + " " * 10 + "║")
    print("╚" + "═" * 76 + "╝")
    B = budget(CFG)
    print(f"  K={CFG['K']} carrier · H={CFG['H']} task · psi={CFG['psi']} · "
          f"kappa_commit={CFG['kappa_commit']}")
    print(f"  Ngân sách B = {B:.3f} (hiệu chuẩn để audit-at-commit ra đúng "
          f"harm {CFG['commit_harm_target']})")
    print("  Phụ thuộc: chỉ thư viện chuẩn Python.")

    results, checks, diags = {}, {}, {}
    checks["KT2  thứ hạng chính sách"] = check2(results)
    checks["KT1&3 ranh giới chế độ"]   = check13(results)
    checks["KT4  on-insertion tệ nhất"] = check4(results)
    diags["A  Hệ quả 5 vế K=1"]        = diag_single_carrier(results)
    report_structure()
    report_discrepancies()
    if args.crosscheck:
        checks["đối chiếu scipy"] = crosscheck()

    hr("TỔNG KẾT")
    print("  BỐN KIỂM TRA CỦA SMOKE TEST GỐC  (quyết định mã thoát)")
    for k, v in checks.items():
        print(f"    {'PASS' if v else 'FAIL'}  {k}")
    print("\n  CHẨN ĐOÁN BỔ SUNG  (không quyết định mã thoát — là phát hiện, không phải lỗi)")
    for k, v in diags.items():
        print(f"    {'khớp' if v else 'KHÔNG khớp'}  {k}")
    allok = all(checks.values())
    print(f"\n  → {'TÁI LẬP THÀNH CÔNG' if allok else 'CÓ KIỂM TRA FAIL'}: "
          f"{sum(checks.values())}/{len(checks)} kiểm tra gốc PASS")
    print("\n  Nhắc lại phạm vi: tái lập DẤU và THỨ HẠNG của smoke test gốc.")
    print("  Mọi con số kết quả trong manuscript là DỰ PHÓNG, chưa chạy nghiên cứu đầy đủ.")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"config": CFG, "budget": B, "checks": checks, "diagnostics": diags,
                       "results": results}, f, ensure_ascii=False, indent=2)
        print(f"\n  Đã ghi {args.json}")
    return 0 if allok else 1

if __name__ == "__main__":
    sys.exit(main())
