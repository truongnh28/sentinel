# Sentinel v3 P2 — H7: thư viện không biết CHỜ, giải thích trên game nhỏ

27/09/2026. Phân tích giải tích trên **240 game nhỏ** (dev/P2), **không phải kết quả eval**. Không chạm split nào, không chạm eval, `v3/seal.py`, `frozen/`. Chỉ giải chính xác bằng backward induction / LP trên game nhỏ (không Monte-Carlo). Không đổi tham số, không đổi mã sản phẩm: dùng nguyên `v3/smallgame_v3.py` như đã khai ở T21.

- Bộ giải: `v3/smallgame_v3.py` (B7 = π\* chính xác, 28 member được port, regret so với B7). Tool: `tools/v3_small_games.py`.
- Câu hỏi mở của P2 §5: *"thư viện 28 member không biết CHỜ — giải thích H7 trên game nhỏ."*

## 1. "Chờ" là hành động gì, và vì sao member không có nó

Game nhỏ: K carrier, H task, cửa sổ payload dài Δ+1, ngân sách m lần audit. Mỗi task người thủ chọn audit MỘT carrier hoặc **none** (không audit, chỉ số K). Vì audit hoặc bắt (kết thúc, L=0) hoặc im lặng, mọi lịch sử còn mở chỉ là chuỗi hành động của chính người thủ, và một policy thuần là một **lịch** s ∈ {0..K}^H với ≤ m audit (Kuhn: policy hành vi = phân phối trên các lịch).

**CHỜ** = chọn **none** ở task t trong khi ngân sách VẪN CÒN (used < m), để dành audit cho task muộn hơn khi belief rõ hơn hoặc để phủ một cửa sổ đặt muộn. Đây là một hành động hợp lệ trong không gian policy đầy đủ mà π\* dùng.

**Vì sao 28 member không CHỜ được** (`v3/library.py`, xác nhận từng họ):

- Mỗi member chỉ chọn **target** audit của task (`Member.distribution` trả phân phối trên các target); **không member nào có "none" trong phân phối**. SW trả trọng số cố định trên (memory, queue, skill, commit); BT trả commit hoặc một sweep; RO trả target kế trong vòng. Cả ba luôn chỉ ra một carrier để audit.
- "none" chỉ xuất hiện khi **ngân sách đã cạn**: đây là luật O14 — dòng 5 mới bỏ member không đủ ngân sách, member tự nó luôn tiêu (`smallgame_v3.leaves`: `if used >= g.m: a = none`). Nên mỗi member tiêu đủ m audit vào **m task đầu** (0..m−1) rồi none từ task m trở đi.
- Hệ quả: mọi member (và mọi hỗn hợp của chúng) là một policy **dồn ngân sách về đầu** (front-loaded). Nó không thể hoãn một audit sang task muộn, cũng không thể rải audit ra (bỏ task này để audit task sau).

Vậy "không biết chờ" = lớp policy của thư viện bị giới hạn vào các lịch audit đúng m task đầu, none phần đuôi. Đây chính là điều cần lượng hoá.

## 2. Ba lớp policy so sánh (đều giải chính xác)

Trên mỗi game giải LP minimax `min_P max_c Pr_P[bỏ sót cửa sổ c]`:

| Lớp | Định nghĩa | Giá trị |
| --- | --- | --- |
| **B7 = π\*** (được chờ) | LP trên MỌI lịch (≤ m audit, đặt audit ở bất kỳ task nào) | `V*` |
| **Tốt nhất KHÔNG chờ** (front-loaded) | LP chỉ trên các lịch dồn đầu: audit task 0..min(m,H)−1, none phần đuôi — lớp mà luật O14 áp đặt | `V_nowait` |
| **Hỗn hợp 28 member** (line 5) | LP trên hỗn hợp của 28 member được port | `V_mixture` |

`V_nowait` là chặn dưới tốt nhất mà **bất kỳ** người thủ "tiêu-trước, không-chờ" có thể đạt — không phụ thuộc thư viện cụ thể. Nên:

- **gap chờ** = `V_nowait − V*` = giá trị thuần của khả năng CHỜ (tách khỏi mọi hạn chế khác của thư viện).
- **regret thư viện** = `V_mixture − V*` = regret thật của 28 member so với B7 (đúng số T21 báo cáo).

## 3. Kết quả chính xác trên 240 game

| Đại lượng | Max | Trung bình | Trung vị |
| --- | --- | --- | --- |
| gap chờ = V_nowait − V\* (toàn bộ 240) | 1,000 | 0,168 | 0,125 |
| — 192 game ngân sách chặn (m < H) | 1,000 | 0,210 | 0,167 |
| — 48 game ngân sách lỏng (m ≥ H) | 0,000 | 0,000 | 0,000 |
| regret thư viện = V_mixture − V\* (toàn bộ 240) | 1,000 | 0,168 | 0,125 |
| — 192 game ngân sách chặn | 1,000 | 0,210 | 0,167 |
| — 48 game ngân sách lỏng | 0,000 | 0,000 | 0,000 |

**Kết quả then chốt: `V_mixture = V_nowait` trên cả 240 game** — sai khác lớn nhất `max |V_mixture − V_nowait| = 9,2·10⁻¹⁵` (nhiễu số). Nói cách khác:

> Toàn bộ regret của thư viện 28 member so với B7 **đúng bằng** gap chờ, không nhiều hơn một chút nào. Trong 141 game ngân sách chặn có regret > 0, tỉ số gap-chờ / regret-thư-viện = 1,000 ở **mọi** game (min = median = mean = 1,000).

Điều này tách bạch hai giới hạn:
- **Chọn target** (repertoire hạn chế: 8 trọng số SW, 12 ngưỡng BT, 8 vòng RO, belief stub) **không mất gì**: hỗn hợp 28 member đã đạt đúng giá trị tối ưu của lớp không-chờ.
- **Không biết chờ** (dồn ngân sách về đầu) là **nguyên nhân duy nhất** của regret so với B7.

Chi tiết:
- **48 game ngân sách lỏng (m ≥ H):** gap chờ = 0 và regret = 0 ở tất cả. Khi mua được audit mọi task, không cần dành dụm, nên chờ vô giá trị và thư viện tối ưu.
- **192 game ngân sách chặn (m < H):** 51 game có gap chờ = 0 (dồn đầu không hại vì cấu trúc cửa sổ), 141 game còn lại gap chờ > 0 và bằng đúng regret.

**gap chờ theo Δ (192 game chặn):** Δ=0: 0,172; Δ=1: 0,267; Δ=2: 0,279; Δ=3: 0,245; Δ=4: 0,125; Δ=5: 0,000. Chờ đáng giá nhất ở Δ trung bình. Khi Δ rất lớn (Δ=5, cửa sổ phủ gần hết H=6) một audit bất kỳ đã trúng cửa sổ dù đặt ở đâu, nên dồn đầu không hại (gap 0). Khi Δ=0 (cửa sổ đơn) dồn đầu chỉ phủ được task đầu, cửa sổ muộn thoát hết. **gap chờ theo m (192 game chặn):** m=1: 0,168; m=2: 0,252; m=3: 0,236.

## 4. Ví dụ đọc tay

**(a) H=3, K=2, m=1, Δ=0** (cửa sổ đơn, một audit).
- π\* rải đều 1 audit trên 6 vị trí (t, carrier), mỗi vị trí xác suất 1/6, none ở 2 task còn lại: `V* = 5/6 ≈ 0,833`. Nó **CHỜ**: ở lịch sử rỗng nó chơi none với xác suất 2/3 (chỉ 1/3 audit ngay task 0); sau một none nữa nó chơi none xác suất 1/2.
- Không-chờ buộc audit task 0: chỉ phủ (0, carrier đó); attacker đặt ở 5 vị trí kia → sống chắc → `V_nowait = 1,0`. Thư viện cũng đúng 1,0. **gap = 0,167.**

**(b) H=6, K=2, m=2, Δ=3** — game gap lớn nhất (gap = 1,000).
- π\* là lịch đơn `(none, none, audit c0, audit c1, none, none)`: audit carrier 0 ở t=2, carrier 1 ở t=3. Cửa sổ dài 4 của một carrier bắt đầu ở ι ∈ {0,1,2}; audit ở giữa (t=2 cho c0, t=3 cho c1) nằm trong **mọi** cửa sổ của carrier đó → `V* = 0` (bắt chắc). Hai audit đặt đúng chỗ phủ toàn bộ.
- π\* **CHỜ ở t=0 và t=1** (none dù còn đủ 2 audit) để đặt audit vào giữa. Không-chờ phải audit t=0,1; mọi cửa sổ bắt đầu ι ≥ 2 (ví dụ {2,3,4,5}) không được phủ → attacker sống chắc → `V_nowait = V_mixture = 1,0`. **gap = 1,0** (cực đại: thắng tuyệt đối thành thua tuyệt đối chỉ vì không biết chờ).

## 5. Verdict H7

**Game nhỏ chính xác ỦNG HỘ và làm sắc H7.** H7 khẳng định không member nào trong 28 member có thể hoãn/chờ để tích belief rồi mới audit; luật "tiêu ngân sách trước" (O14) khoá mọi member vào lịch dồn đầu. Bằng lời giải chính xác backward-induction trên 240 game, ta không chỉ xác nhận điều đó mà còn định lượng chặt: **toàn bộ regret của thư viện 28 member so với B7 (trung bình 0,168, tối đa 1,0 trên 240 game; trung bình 0,210 trên 192 game ngân sách chặn) đúng bằng giá trị của việc CHỜ** — `V_mixture = V_nowait` tới 10⁻¹⁴ trên cả 240 game, nên repertoire target hạn chế không mất gì và việc không-biết-chờ giải thích 100% khoảng cách tới ceiling. Khi ngân sách lỏng (m ≥ H) chờ vô giá trị và thư viện tối ưu (regret 0 trên 48 game). Kết quả này khớp và giải thích chính xác số bán kính phủ của T21 (trung bình 0,40, toàn bộ sai lệch nằm ở game ngân sách chặn): thư viện không phủ được các π\* rải/hoãn audit vì không có hành động "none tự nguyện". Đây là hệ quả của thiết kế thư viện đã chốt (giữ như draft, luật tiêu-trước), không phải lỗi bộ giải.

## 6. Không đổi DCM

Kết quả này **khẳng định và làm sắc**, không thay đổi, các dòng DCM đã khai ở T21: `D5.2.lib` (member audit mọi task tới khi hết m rồi none — O14), `D9.3.regret` (regret = V(conv Π) − V\*), `D6.3.radius`/`D6.3.prop6`. Không có dòng DCM nào khẳng định "regret = gap chờ" nên không cần thêm/sửa dòng. DCM giữ nguyên.

## 7. Tái lập

Số ở §3–§4 dùng nguyên `v3/smallgame_v3.py`. `V_nowait` là LP minimax trên lớp lịch dồn đầu (audit task 0..min(m,H)−1, none đuôi), dùng lại `smallgame_v3.miss_matrix` và cùng dạng LP HiGHS như `solve_exact`. `V*`, `V_mixture` từ `smallgame_v3.solve_exact` và `library_values`. "Trạng thái chờ" = lịch sử π\* đạt tới nơi nó chơi none với used < m. Chạy nhẹ (chỉ game nhỏ, không Monte-Carlo, một tiến trình vài giây).

```
cd auditgame
../.venv/bin/python tools/v3_small_games.py            # B7, regret, bán kính (T21)
```

## 8. Kiểm tra

- `../.venv/bin/python tests/run_v3.py` — "Every gate green".
- `../.venv/bin/python tools/v3_dcm.py --check` — 0 problem.
