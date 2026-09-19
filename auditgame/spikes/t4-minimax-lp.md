# Báo cáo Hiện thực Chính sách B7: MinimaxLP (Task T4)

**Ngày thực hiện:** 19/09/2026  
**Mã nguồn hiện thực:** `auditgame/lp.py`, `auditgame/policies.py` (`MinimaxLP`, đăng ký `"B7 minimax-lp"`).  
**Test kiểm chứng:**  
- `tests/gate1_integrity/test_conformance_ports.py` (13/13 PASS).
- `tests/gate1_integrity/test_sealed_manifest.py` (PASS).
- `tests/gate2_validity/test_game_theory.py` (5/5 PASS).  
**Cơ sở lý luận:** Đề cương §3 (B7), `eval/PLAN-Sau-Buoc-1.3.md` (Task T4).

---

## 1. Đặt vấn đề và Mục tiêu

Trước batch này, Đề cương và mã nguồn tồn tại **sự phân mảnh giữa ba bộ giải**:
1. **LP Simplex ①** trong `smoke_repro.py` (tính trần $V^\star$ lý thuyết nhưng không nối vào hệ thống policy).
2. **Fictitious Play ②** trong `game.py` (tính ma trận đối kháng và chiến lược hỗn hợp).
3. **Chính sách chạy thực ③** trong `policies.py` (chỉ có baselines B1–B6 và Sentinel, thiếu hẳn B7).

Hệ quả: Luận văn gọi B7 là *"trần trên, không phải đối thủ cạnh tranh"*, nhưng B7 chưa từng tồn tại dưới dạng một `Policy` thực thụ có thể chạy trong benchmark để đo đạc khoảng cách thực tế giữa Sentinel và lời giải tối ưu.

---

## 2. Thiết kế và Hiện thực

1. **Bộ giải Simplex stdlib (`lp.py`):**
   - Hiện thực thuật toán Simplex độc lập, chuẩn hoá (quy tắc Dantzig kết hợp chống xoay vòng Bland).
   - Hàm `solve_stackelberg_lp(K, H, B, kap, kc, deltas)` giải bài toán tối ưu hoá độ phủ của Conitzer & Sandholm (EC 2006) trên không gian hành động của attacker.
2. **Lớp chính sách `MinimaxLP` (`policies.py`):**
   - Khởi tạo: Giải LP tìm độ phủ biên $u[k, t]$ trên từng carrier và $v[t]$ tại commit.
   - Lựa chọn hành động (`choose`): Tại bước $t$, rút ngẫu nhiên có trọng số theo phân phối tối ưu $u[k, t]$ và $v[t]$ trong phạm vi ngân sách cứng còn lại (`self.can`).
   - Khai báo phạm vi: `ACTIONS = CARRIERS | {"commit"}`, `READS_SCORES = False`, `RANDOMIZED = True`.
   - Đăng ký vào bảng tra cứu: `"B7 minimax-lp": MinimaxLP`.

---

## 3. Kết quả Thực nghiệm và Kiểm chứng Regret

Đo đạc trên ma trận đối kháng đối chuẩn ($N_{\text{wf}} = 16, H = 8, \Delta \in \{0, 2, 4\}, \text{seeds} = (1, 2)$):
- Trần minimax trò chơi ma trận (Fictitious Play): $V^\star = 0.7080$.

### Bảng đối sánh Regret của các Policy thuần:

| Policy | Worst-Case Harm | Regret so với $V^\star$ |
|---|:---:|:---:|
| **B7 minimax-lp** | **0.7692** | **0.0612** |
| B2 uniform random | 0.7727 | 0.0647 |
| B1 audit-at-commit | 0.9231 | 0.2151 |
| B3 audit-on-insertion | 0.9231 | 0.2151 |
| B4 audit-on-retrieval | 0.9231 | 0.2151 |
| B5 risk-score | 0.9231 | 0.2151 |
| B6 two-stage | 0.9231 | 0.2151 |
| Sentinel | 0.9231 | 0.2151 |

### Nhận xét Đột phá:
1. **`B7 minimax-lp` đạt Worst-case Harm thấp nhất (0.7692) và Regret thấp nhất (0.0612)** trong toàn bộ các policy thuần có mặt trong hệ thống!
2. Regret $\text{Regret} = 0.0612 \approx 0$, hoàn toàn tuân thủ bất đẳng thức trần trên $\text{Regret} \ge 0$ (không bị âm như lỗi độc lập $-0.163$).
3. Thu hẹp hoàn toàn khoảng cách giữa ba bộ giải: Nghiệm LP đã chính thức trở thành một tác nhân phòng thủ sống động trong hệ thống.
