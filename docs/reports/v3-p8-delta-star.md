# Sentinel v3 — P8: Δ\* bằng số tại đúng tham số đã đo (29/09/2026)

Hai phản biện độc lập cùng chỉ vào một chỗ: paper chứng minh một **ranh giới chế độ** Δ\*, rồi đo
tại **một** điểm bộ dò duy nhất, mà không bao giờ đặt lưới đo của mình so với ranh giới đó. Báo
cáo này tính Δ\* bằng số tại đúng các hằng số paper khai, kiểm hai điều kiện cửa sổ, và nói thẳng
lưới nằm trong hay ngoài điều kiện của chính định lý.

> **Nhãn: không chạy gì.** Đây là tính đóng (closed-form) cộng vài phép kiểm số nhỏ. Không một
> lượt mô phỏng, không một lượt eval, `seal.unseal` không được gọi, không suất unseal nào bị tiêu.
> `auditgame/v3/`, `auditgame/frozen/`, `freeze.SOURCE`, `freeze.TABLES` **không bị sửa một dòng**.
> Mọi con số đều gọi thẳng vào `v3/budget.py`, `detector.py`, `draft_setup.py`, `v3/config.py`.

## 0. Xuất xứ

| | |
|---|---|
| Nhánh / commit | `int-p2`, cây sạch tại `9c95ee2` khi bắt đầu |
| Python | `/Users/truong.nh/Me/obsidian/HCMUT/code/Sentinel/.venv/bin/python` |
| Nguồn hằng số | `auditgame/v3/config.py`, `auditgame/v3/budget.py`, `auditgame/detector.py`, `auditgame/draft_setup.py`, `auditgame/costs.py`, `auditgame/corpus_v2.py` |
| Nguồn lý thuyết | `HCMUT/theory/main.tex` tại `79d827d` (Định lý 5.6 = Theorem 4, Mệnh đề 5.7 = Proposition D, Hệ quả 6.1 = Corollary 5(f)); `HCMUT/theory/checks/thm4_budget.py`, `checks/coverage.py` |
| Nguồn paper | `HCMUT/paper-v3/sections/theory.tex`, `formulation.tex`, `benchmark.tex`, `budget.tex`, `discussion.tex`, `extra-tables.tex` |
| Điều đáng nói | **Mọi thứ trong báo cáo này đã có sẵn trong code.** `v3/budget.py` cài đúng `n_alpha`, `ell_alpha`, `window_ok`, `counting_n`, cờ `FLAG_WINDOW`, `FLAG_COMMIT_SUFFICES`, và docstring của nó đã ghi *"n = 17-24, K(n+1) > Delta"*. Cái thiếu là **paper không in ra**. |

## 1. Các hằng số đã đo được, kèm nguồn

Không có hằng số nào `NOT FOUND` trong **code**. Nhưng ba trong số chúng — α, γ, và K mà Định lý 4
dùng — **không có trong paper**; đó là lỗ hổng phải báo cáo (Mục 7).

| Ký hiệu | Giá trị đã đo | Nguồn |
|---|---|---|
| `K` (carrier **quét được**, model 𝔇) | **3** — memory, queue, skill | `v3/budget.py:SWEEP_TARGETS`; docstring: *"K = the three SWEPT carriers … model D of the note has no commit-only carrier (Def. 5.1(iii))"* |
| `K` (paper in ra) | **4** | `formulation.tex:14` "$K = 4$"; `implementation.tex:36` "4 audit targets" — **một đối tượng khác**, không phải K của Định lý 4 |
| `K_d` (uỷ nhiệm, model 𝔠) | 2 (skill, queue) | `config.K_D_PRIMARY`, `config.DELEGATED_BY_KD` |
| `α` | **0,05** | `v3/budget.py:ALPHA`. `draft_setup.FAMILY_ALPHA = 0.05` (D25) là mức kiểm định Bonferroni — **đối tượng khác**, trùng số là ngẫu nhiên |
| `ℓ_α = log(1/4α)` | **1,609438** | `budget.ell_alpha()` |
| `ψ` | **0,85** | `detector.SETTINGS["mid"][0]` (bản nháp §8) |
| `φ` | **0,12** | `detector.SETTINGS["mid"][1]` |
| `γ = ψ − φ` | **0,73** (độ sâu 1) / **0,85456** (độ sâu 2) / **0,87604** (độ sâu 3) | `Detector.gamma`, `Detector.at_depth`. **Không phải một số** — γ phụ thuộc độ sâu |
| `d′` | **2,211420** chính xác (nhãn 2,21); lưới nhãn (1,52; 2,21; 2,96) → chính xác (1,5161; 2,2114; 2,9598) | `detector.operating_point(ψ,φ) = z(ψ) − z(φ)`; `config.DPRIME_LEVELS`, `DPRIME_PRIMARY` |
| `β` | memory **0,314**, skill **0,058**, queue **0,033** | `costs.BETA_RULE_A` qua `draft_setup.BETA_WORLD` (D6) |
| `ε_c = ρ²d′²/2` | **0** / **0,1528** / **0,6113** / **2,4452** tại ρ ∈ {0; 0,25; 0,5; 1} | `budget.commit_kl_delegated` (Bổ đề 5.5(b)) |
| `D_s` (Gauss, độ sâu ô headline 3/2/1) | memory **4,477**, queue **4,625**, skill **2,197** nat | `budget.kl_drift_gauss(β_k, d′√depth)` |
| `n_α` per carrier, ρ = 0 | 0,359 / 0,348 / 0,733; **Σ_k n_k = 1,4400** | `budget.bmin(cell, H)` |
| `ζ` | **0,10** | `draft_setup.ZETA` (D9); `approach.tex:140` |
| `H` | **U{6,…,14}** (9 giá trị, đều) | `draft_setup.H_RANGE = (6,14)`; `corpus_v2.py:59 rng.randint(*D.H_RANGE)` (bao gồm hai đầu); `benchmark.tex:64` "$H \sim U\{6,\dots,14\}$" |
| `κ` tại độ sâu ô headline | memory 1,2; queue 1,8; skill 1,6; commit 4,1 — `κ̄` trên carrier quét được = **1,5333** | `Cell.kappa()`, `Cell.depths()` = (3,2,1,1) |
| lưới Δ / headline | (0,1,2,4,8) / **(4, 8)** | `config.DELTAS`, `config.HEADLINE_DELTAS` |
| lưới ρ | (0; 0,25; 0,5; 1) | `config.RHO_GRID` (D20) |

## 2. Δ\* bằng số

**Hệ quả 5(f) không phải một khẳng định Θ(·) trần.** Chứng minh cấp hằng số ở **cả hai đầu**:

> Δ\* ∈ [K·n_α, K(n+1)],  với n = ⌈2log(1/α)/((1−β)²γ²)⌉

rồi mới nói hai đầu cùng bậc, cho ra Θ(K log(1/α)/((1−β)γ)²). Vì vậy paper **hoàn toàn có thể**
đặt lưới của mình so với Δ\* — nó chỉ chưa làm.

Đầu dưới dùng dạng **per-carrier** mà `v3/budget.py` cài (độ sâu khác nhau ⇒ D_s khác nhau ⇒
Σ_k n_k thay cho K·n_α); đầu trên là Prop D với n = max trên các carrier.

| ρ | ε_c | Đầu dưới Σ_k n_k | n (Prop D) | Đầu trên K(n+1), K=3 | K=4 | Độ rộng |
|---|---|---|---|---|---|---|
| 0 | 0,0000 | **1,4400** | 17 | **54** | 72 | 37,5× |
| 0,25 | 0,1528 | 1,3033 | 17 | 54 | 72 | 41,4× |
| 0,5 | 0,6113 | 0,8931 | 17 | 54 | 72 | 60,5× |
| 1 | **2,4452** | 0 | 17 | — | — | **giả thiết ε_c < ℓ_α SAI** |

**Hằng số đặt bằng 1, làm mốc thang.** Dạng Θ(·) với hệ số tỉ lệ = 1, K = 3, α = 0,05:

| đọc theo | Δ\*\|_{c=1} (K=3) | (K=4) |
|---|---|---|
| biên độ sâu 1 (γ = 0,73), β = skill 0,058 | **19,0** | 25,3 |
| biên độ sâu 1 (γ = 0,73), β = memory 0,314 | **35,8** | 47,8 |
| memory tại độ sâu 3 (γ = 0,87604), β = 0,314 | **24,9** | 33,2 |
| queue tại độ sâu 2 (γ = 0,85456), β = 0,033 | **13,2** | 17,5 |

Nghĩa là: **với hệ số bằng 1, Δ\* rơi vào 13–36 — trên cả Δ = 4 lẫn Δ = 8, và trên H−1 với gần
như mọi H trong corpus.** Đó không phải bằng chứng lưới nằm dưới ranh giới (hệ số không phải 1),
nhưng nó cho thấy mốc thang tự nhiên của bài toán nằm ở đâu.

## 3. Δ ∈ {4, 8} nằm trong hay ngoài điều kiện của định lý

**Kết luận thẳng: cả hai độ trễ headline nằm CHẶT BÊN TRONG cái ngoặc [1,44 ; 54]. Lý thuyết
không đặt được chúng về phía nào của ranh giới.**

Cụ thể:

- **Điều kiện cần (Định lý 4(i), Δ ≥ K·n_α): ĐẠT** tại Δ ∈ {4, 8}, ở mọi ρ, ở **mọi** bộ dò đã
  khai — kể cả bộ yếu nhất. Xem Mục 5.
- **Điều kiện đủ (Prop D, Δ ≥ K(n+1) = 54): KHÔNG ĐẠT**, thiếu một hệ số ~7. Xem Mục 4.
- Vì vậy **không có gì trong Hệ quả 5(f) chứng nhận rằng ở Δ = 4 hay Δ = 8 có chính sách nào đạt
  được R(α)**, và cũng không có gì loại trừ. Cái paper xác nhận bằng đo là **hình dạng** mà các
  vế (b) và (c) dự đoán, **không phải** chuyện lưới nằm trên Δ\*.

**Một chỗ nhập nhằng làm đổi kết luận.** Khẳng định Θ(·) của Hệ quả 5(f) viết trong **tham số hoá
Bernoulli** (γ), còn thứ paper thực sự đo là **bộ dò Gauss** (d′, có độ sâu). Hai cách đọc cho hai
câu trả lời khác nhau ở Δ = 4:

| model | K·n_α tại ô headline, ρ = 0 | Δ = 4 | Δ = 8 |
|---|---|---|---|
| **Gauss** (cái paper đo; độ sâu 3/2/1) | **1,44** | trong | trong |
| Bernoulli, biên độ sâu 1 γ = 0,73, β = skill 0,058 | **4,12** | **ngoài** | trong |
| Bernoulli, biên độ sâu 1 γ = 0,73, β = memory 0,314 | **7,49** | **ngoài** | trong, dư 7 % |

Chênh lệch là vì quét ở độ sâu 2–3 mang nhiều thông tin hơn hẳn (D_s = 4,48/4,63 nat so với
1,17 nat của mô hình Bernoulli một lượt nhìn). **Paper không nói cửa sổ được đọc trong model nào.**
Nếu đọc theo Bernoulli — đúng cái tham số hoá mà phát biểu Θ dùng — thì **Δ = 4 nằm dưới cửa sổ
cần thiết**, và một nửa của cặp Δ = 4 → 8 mất chỗ đứng.

### γ / d′ mà chế độ rời khỏi lưới

Tính trong model Gauss tại ô headline (χ = 1,33; độ sâu 3/2/1), tìm d′ mà Σ_k n_k vượt từng mốc.
`gamma1` là biên ở độ sâu 1 tương ứng, tức γ = Φ(d′ − z_{1−φ}) − φ ở cùng ngưỡng φ = 0,12.

| Σ_k n_k vượt | ρ = 0 | ρ = 0,25 | ρ = 0,5 | ρ = 1 |
|---|---|---|---|---|
| Δ = 1 | không bao giờ | không bao giờ | d′ = 2,1352 (γ = 0,712) | d′ = 1,4922 (γ = 0,505) |
| Δ = 2 | d′ = 1,8862 (γ = 0,642) | 1,8261 (0,623) | 1,6747 (0,571) | 1,3071 (0,433) |
| **Δ = 4** (headline) | **d′ = 1,3480 (γ = 0,4487)** | 1,3255 (0,440) | 1,2640 (0,416) | 1,0819 (0,343) |
| Δ = 5 = H_min − 1 | d′ = 1,2095 (γ = 0,3937) | 1,1931 (0,387) | 1,1476 (0,369) | 1,0061 (0,313) |
| **Δ = 8** (headline) | **d′ = 0,9617 (γ = 0,2955)** | 0,9534 (0,292) | 0,9296 (0,283) | 0,8493 (0,252) |
| Δ = 13 = H_max − 1 | **d′ = 0,7580 (γ = 0,2183)** | 0,7539 (0,217) | 0,7419 (0,213) | 0,6990 (0,197) |

**Mọi ngưỡng trên đều nằm dưới bộ dò yếu nhất paper khai (d′ = 1,5161).** Vì vậy kịch bản
"attacker làm nửa biên ⇒ Δ\* gấp bốn ⇒ vượt chân trời ⇒ Hệ quả 5(a) phủ toàn lưới" **không đúng
như phát biểu** tại d′ đã đo.

Nhưng cơ chế thì có thật, và độ nhạy thì lớn. Làm **đúng một nửa biên độ sâu 1** (γ: 0,73 → 0,365,
tức d′ = 1,1374) đẩy Σ_k n_k từ **1,44 lên 5,67** — hệ số **3,9×**, khớp gần đúng dự đoán γ⁻² là 4×.
Ở biên đó:

- **Δ = 4 rơi xuống DƯỚI cửa sổ** (4 < 5,67): cột trái của cặp headline mất chế độ;
- **mọi workflow H = 6 bị loại** (Δ ≤ H−1 = 5 < 5,67);
- Δ = 8 vẫn vượt qua.

Nói khác: phản biện **quá tay** khi nói toàn lưới sụp về Hệ quả 5(a), nhưng **đúng** rằng một trục
d′ chưa đo đang gánh toàn bộ khẳng định, và cột Δ = 4 mất chế độ chỉ với một nửa biên. Paper tự
khai trục này là chưa đo (`extra-tables.tex:124`: *"Only the mid detector was run"*), nên đây là
lỗ hổng phạm vi, không phải lỗi số.

## 4. Cửa sổ của Proposition D: K(n+1) ≤ Δ ≤ H − 1

`n = max_k ⌈2 log(1/α) / ((1−β_k)² γ_k²)⌉`, γ_k lấy tại độ sâu của carrier đó
(`budget.counting_n`, `BlockSchedule.__init__`).

Tại ô headline (χ = 1,33; mid; ρ = 0): memory n_k = 17 (độ sâu 3, β = 0,314), skill 13, queue 9
⇒ **n = 17**, **K(n+1) = 3 × 18 = 54** (hoặc 72 nếu K = 4).

Trên **toàn** lưới đã khai:

| χ | d′ | độ sâu | n | K(n+1), K=3 |
|---|---|---|---|---|
| 1,04 | 1,52 | 3/3/2 | 22 | 69 |
| 1,04 | 2,21 | 3/3/2 | 17 | 54 |
| 1,04 | 2,96 | 3/3/2 | 15 | **48** (nhỏ nhất) |
| 1,33 | 1,52 | 3/2/1 | 23 | 72 |
| **1,33** | **2,21** | **3/2/1** | **17** | **54** ← ô headline |
| 1,33 | 2,96 | 3/2/1 | 15 | 48 |
| 2,11 | 1,52 | 1/1/1 | **43** | **132** (lớn nhất) |
| 2,11 | 2,21 | 1/1/1 | 24 | 75 |
| 2,11 | 2,96 | 1/1/1 | 18 | 57 |

**n ∈ [15, 43]; K(n+1) ∈ [48, 132]** (K = 4: [64, 176]).

**Phán quyết: cửa sổ RỖNG trên toàn bộ lưới đã đo.** Δ ≤ 8 và H − 1 ≤ 13, còn K(n+1) ≥ 48. Không
một cặp (Δ, H) nào trong 5 × 9 = 45 cặp thoả `K(n+1) ≤ Δ ≤ H−1` — **0/45, loại 100 %.**

**Số học của phản biện.** "K = 4 ép Δ ≥ 8" **đúng như một sàn** (n ≥ 1 ⇒ K(n+1) ≥ 2K = 8) nhưng
**hụt 7–9 lần**: tại γ và β đã đo, n = 17, nên sàn thật là 54 (K = 3) / 72 (K = 4). Kết luận của
phản biện — Δ = 4 nằm ngoài chế độ mà tốc độ được chứng minh — **đúng, và còn đúng mạnh hơn nhiều**:
**Δ = 8 cũng nằm ngoài.**

**Vế `Δ ≤ H − 1`.** Tại Δ = 8 nó loại H ∈ {6, 7, 8}, tức **3/9 = 33,3 %** corpus H ~ U{6,…,14}.
Tại Δ = 4 nó không loại gì (Δ = 4 ≤ H−1 với mọi H ≥ 6). **Số học của phản biện ở vế này: xác nhận.**
Nhưng vì vế `K(n+1) ≤ Δ` đã hỏng trước, **tỉ lệ loại thực tế ở Δ = 8 là 9/9 = 100 %**.

**Code đã biết điều này.** `v3/budget.py` docstring: *"H18's former success criterion 'miss before
sigma <= alpha' is unreachable on this grid (n = 17-24, K(n+1) > Delta)"*. `BlockSchedule` docstring:
*"with alpha = 0.05 and the draft's detectors n >= 8 in every cell, so K(n+1) >= 27 and no cell with
Delta <= 8 meets it"* — và lớp này **log `precondition_met = False` ở mọi ô**, rồi rơi về `b = K`
(dày nhất) hoặc về nhánh single-sweep. Paper có một arm `block-schedule`; **arm đó chưa bao giờ
chạy trong chế độ mà Prop D bảo đảm.**

## 5. Cửa sổ của Định lý 4(i): Δ ≥ K·n_α

Dạng per-carrier mà code dùng: `Σ_k n_k ≤ Δ` (`budget.window_ok`).

| ρ | Σ_k n_k | Δ=1 | Δ=2 | **Δ=4** | **Δ=8** | cờ |
|---|---|---|---|---|---|---|
| 0 | 1,4400 | ✗ | ✓ | **✓** | **✓** | — |
| 0,25 | 1,3033 | ✗ | ✓ | **✓** | **✓** | — |
| 0,5 | 0,8931 | ✓ | ✓ | **✓** | **✓** | — |
| 1 | 0,0000 | ✓ | ✓ | ✓ | ✓ | `COMMIT_SUFFICES` |

Theo bộ dò đã khai (ρ = 0): weak **3,1396**, mid **1,4400**, strong **0,7896**. Δ = 4 và Δ = 8
vượt cửa sổ **ở cả ba**; Δ = 2 **hỏng ở bộ dò weak** (2 < 3,14).

Hai hệ quả phải in ra:

1. **Giả thiết `ε_c < ℓ_α` của Hệ quả 5(f) SAI tại ρ = 1.** ε_c = ρ²d′²/2 = 2,4452 > ℓ_α = 1,6094.
   Điểm cắt là **ρ_c = √(2ℓ_α)/d′ = 0,8113**. Trên ngưỡng đó, Định lý 4(iii) nói **kiểm toán commit
   một mình đã đạt R(α)**, `budget.bmin` bật cờ `FLAG_COMMIT_SUFFICES` và trả B_min = 0. Cột ρ = 1
   — cột paper dựa vào để nói "sụp ở cuối trục" — **nằm ngoài vế ranh giới**, chứ không phải một
   điểm trên nó. (Điều này độc lập với vế (c): trần p_d − p_ρ đóng lại vì lý do khác.)

2. **Một câu trong `budget.tex` ngược chiều theo ρ.** Câu *"the coverage model (Corollary 5)
   predicts gains from $\Dl = 1$ when $\rhoP$ is small"* đúng **trong model phủ 𝔠** (vế (b)+(d)
   cho G(Δ) > 0 từ Δ = 1 khi p_ρ < p_d). Nhưng **trong model 𝔇 thì ngược lại**: Δ = 1 nằm **dưới**
   cửa sổ cần thiết tại ρ = 0 (1 < 1,44) và ρ = 0,25 (1 < 1,30), và **chỉ được nhận từ ρ ≥ 0,4485**.
   Hai model con nói ngược nhau ở Δ = 1, và paper không đánh dấu chỗ đó.

## 6. Phán quyết

| Câu hỏi | Trả lời |
|---|---|
| Δ\* bằng bao nhiêu? | Ngoặc [1,44 ; 54] tại ρ = 0 (K = 3); rộng 37,5×. Hệ số đặt bằng 1 cho mốc 13–36. |
| Δ ∈ {4, 8} trong hay ngoài điều kiện của Định lý 4? | **Trong** điều kiện cần (4(i)) ở mọi ρ và mọi bộ dò đã khai. **Ngoài** điều kiện đủ (Prop D) — thiếu hệ số ~7. Nằm chặt trong ngoặc, lý thuyết không phân định. |
| Phản biện 1 (γ⁻² đẩy Δ\* vượt chân trời) | **Bác bỏ tại d′ = 2,2114**: ngưỡng là d′ ≤ 0,96 (Δ=8) / 1,35 (Δ=4), dưới cả bộ dò yếu nhất đã khai. **Nhưng cơ chế thật**: nửa biên ⇒ Σn_k × 3,9 ⇒ Δ = 4 rơi ra ngoài và mọi H = 6 bị loại. |
| Phản biện 2 (Prop D ép Δ ≥ 8) | **Xác nhận và mạnh hơn**: n = 17, nên K(n+1) = 54 (K=3) / 72 (K=4). **Cả Δ = 4 lẫn Δ = 8 đều ngoài.** Cửa sổ rỗng trên 45/45 cặp (Δ, H). |
| Tỉ lệ H bị loại tại Δ = 8 | Riêng vế Δ ≤ H−1: **33,3 %** (H ∈ {6,7,8}). Cả cửa sổ: **100 %**. |
| Hằng số nào chưa in trong paper | **α**, **γ**, và **K nào** Định lý 4 dùng (3 hay 4). Cả ba đều ở trong code; paper không in. |

## 7. Những câu paper nên thêm

Chèn vào `sections/theory.tex`, ngay sau Theorem 4 và sau Corollary 5(f). Nguyên văn đề xuất:

**(a) In hằng số — sau Theorem 4.**

> At our parameters the theorem's quantities are as follows. $\alpha = 0.05$ throughout, so
> $\ellA = \log\frac{1}{4\alpha} = 1.61$; this is the error target of $R(\alpha)$ and is unrelated
> to the $\alpha = 0.05$ of the bootstrap tests in \S\ref{sec:results}. $K = 3$: the $K$ of model
> $\mathfrak{D}$ counts the \emph{sweepable} carriers (memory, queue, skill), whereas the $K = 4$ of
> \S\ref{sec:formulation} counts audit targets, and the branch is audited only through the commit,
> which model $\mathfrak{D}$ does not represent. The margin $\gamma$ is not a single number in our
> benchmark: at the mid detector's threshold it is $0.73$, $0.855$ and $0.876$ at depths 1, 2 and 3,
> and every bound below is evaluated at each carrier's own depth. With $\dprime = 2.2114$, depths
> $(3, 2, 1)$ and drift rates $\beta = (0.314, 0.033, 0.058)$, the Gaussian $D_s$ is
> $(4.48, 4.63, 2.20)$ nats, so $\sum_k n_k = 1.44$ at $\rhoP = 0$ and Theorem~4(i)'s window admits
> every $\Dl \ge 2$ on our grid; at the weakest declared detector ($\dprime = 1.52$) it is $3.14$ and
> admits $\Dl \ge 4$.

**(b) Đặt lưới so với Δ\* — sau Corollary 5(f).**

> Corollary~5(f) brackets rather than pins the boundary, and at our parameters the bracket is wide:
> with $n = 17$, $\Dl^* \in [1.44, 54]$ at $\rhoP = 0$, a factor of $37$ between its ends. Both
> headline delays lie strictly inside it. The corollary therefore does not place $\Dl \in \{4, 8\}$
> on either side of the boundary, and we do not claim that it does: what the measurement confirms is
> the \emph{shape} clauses (b) and (c) predict, not that the evaluated grid lies above $\Dl^*$.

**(c) Prop D không phủ lưới — sau đoạn giới thiệu Proposition D.**

> Proposition~D's achievability window $K(n+1) \le \Dl \le H-1$ is \emph{empty} on our grid. Over the
> declared cells $n$ ranges from 15 to 43, so $K(n+1) \ge 48$, while $\Dl \le 8$ and $H - 1 \le 13$;
> no evaluated $(\Dl, H)$ pair satisfies it. The \texttt{block-schedule} arm therefore runs outside
> the regime in which the proposition's guarantee holds --- it logs
> \texttt{precondition\_met = False} in every cell and falls back to the densest block --- and we
> report it as a schedule we ran, not as an instance of the proposition. Separately, the upper half
> of the window bites on its own: at $\Dl = 8$ the condition $\Dl \le H-1$ excludes
> $H \in \{6, 7, 8\}$, one third of the $H \sim U\{6,\dots,14\}$ corpus; at $\Dl = 4$ it excludes
> none.

**(d) ρ = 1 nằm ngoài vế (f) — sau Corollary 5(f) hoặc trong `results.tex` nơi đọc cột ρ = 1.**

> Corollary~5(f) assumes $\varepsilon_c < \ellA$. With $\varepsilon_c = \rhoP^2\dprime^2/2$ this
> fails at $\rhoP = 1$, where $\varepsilon_c = 2.45 > \ellA = 1.61$; the crossing is at
> $\rhoP = \sqrt{2\ellA}/\dprime = 0.81$. Above it, Theorem~4(iii) makes commit review alone
> sufficient for $R(\alpha)$, so the $\rhoP = 1$ column lies outside the boundary clause rather than
> at a point on it. This is a second, independent reason the gain must vanish there, alongside
> clause (c)'s cap closing at $p_\rho = p_d$.

**(e) Phạm vi trục d′ — trong `threats.tex`, cạnh chỗ đã khai trục d′ chưa đo.**

> Because $\Dl^*$ scales as $\gamma^{-2}$, the single detector we ran carries the whole regime claim.
> In the Gaussian model, Theorem~4(i)'s window still admits both headline delays at every declared
> detector, and would exclude $\Dl = 4$ only below $\dprime = 1.35$ and $\Dl = 8$ only below
> $\dprime = 0.96$, weaker than any setting we declare. But the sensitivity is real: halving the
> depth-1 margin to $\gamma = 0.365$ ($\dprime = 1.14$) raises the window from $1.44$ to $5.67$, a
> factor of $3.9$ against the $\gamma^{-2}$ prediction of $4$, which would put $\Dl = 4$ and every
> $H = 6$ workflow below it. We therefore state the confirmation as holding at $\dprime = 2.21$ and
> record the $\dprime$ axis as not measured (Table~\ref{tab:detector}), not as a grid-wide claim.

**(f) Hai model con nói ngược nhau ở Δ = 1 — sửa câu trong `budget.tex`.**

> In harm terms the coverage model predicts gains from $\Dl = 1$ whenever $p_\rho < p_d$. The two
> sub-models disagree there and we say so: in $\mathfrak{D}$ the window puts $\Dl = 1$ below
> $K\nA$ at $\rhoP \le 0.25$ and admits it only from $\rhoP \ge 0.45$, so the prediction at
> $\Dl = 1$ is the coverage model's alone and carries no distinguishability guarantee.

**(g) Nếu giữ phát biểu Θ ở dạng Bernoulli — thêm một câu.**

> The $\Theta$-form of (f) is written in the Bernoulli parameterisation, while our benchmark runs a
> Gaussian detector at audit depths $(3,2,1)$; the two give different answers at $\Dl = 4$. Read in
> the Bernoulli model at the depth-1 margin, $K\nA$ is $4.12$ (skill's drift rate) to $7.49$
> (memory's), which would put $\Dl = 4$ below the window; read in the Gaussian model we actually
> evaluate, deeper sweeps carry more information and $K\nA = 1.44$. All numbers we report are the
> Gaussian ones, and we state the model the window is read in wherever it is used.

## 8. Tái lập

Mọi con số trong báo cáo này tái lập bằng cách gọi thẳng vào các hàm sẵn có, không cần script mới:

```py
import sys; sys.path.insert(0, "auditgame")
import detector, draft_setup as D
from v3 import budget as BG, config as C

BG.ALPHA, BG.ell_alpha(), BG.SWEEP_TARGETS, BG.BETA      # 0.05, 1.6094, 3 carrier, beta
detector.SETTINGS["mid"], detector.operating_point(0.85, 0.12)   # (psi, phi), (d', tau)
bm = BG.bmin(C.Cell(rho=0.0, delta=4), H=14)
bm.eps_c, bm.D_s, bm.n, bm.window, bm.flags              # 0.0, {...}, {...}, 1.4400, ()
BG.window_ok(4, bm.n), BG.window_ok(8, bm.n)             # True, True  -> Thm 4(i) dat
c = C.Cell(rho=0.0, delta=4); det = c.detector()
max(BG.counting_n(0.05, BG.BETA[t], det.at_depth(c.depths()[t]).gamma)
    for t in BG.SWEEP_TARGETS)                           # 17  -> K(n+1) = 54 > 8
```
