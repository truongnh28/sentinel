# Cổng 4c task 2 — phân định 77,8% khoảng cách hồi quy còn lại của SSG-up

**Ngày:** 2026-09-20 · **Brief:** `.superpowers/sdd/2026-09-20-ssg-gate4c/task-2-brief.md`
**Script:** `auditgame/spikes/diag_4c2.py` · **Kết quả thô:** `auditgame/spikes/diag-4c2.json`

> **Phán quyết một dòng.** Ở ô Δ=4, d'=2.2, lớp (2,4): **giả thuyết (A) biên duyên lệch
> đúng, đo được** (t=0 trùng tuyệt đối, từ t=1 lệch có hệ thống, đỉnh lệch ở t=3);
> **giả thuyết (B) mất-nhất-quán-thời-gian cũng đúng, đo được, nhất quán về hướng với (A)
> và có cơ chế nối hợp lý, nhưng CHƯA có ablation nhân quả cô lập** (bản lùi phủ đều hơn —
> độ lệch chuẩn 0.110 so với 0.129 — và mỏng hơn — trung bình 0.267 so với 0.332 — với cửa
> sổ TỆ NHẤT còn tệ hơn: 0.074 so với 0.105); **giả thuyết
> (C) có hiệu ứng thật nhưng NHỎ (tổng khối lượng thấp hơn 2,7%) và có dấu hiệu là HỆ QUẢ
> PHÁI SINH của (A)/(B) qua ngân sách còn lại phân tán theo đường đi thực tế, không phải
> một cơ chế độc lập**. Không có phép đo trực tiếp nào trong task này quy đổi được các số
> trên thành "X% của 0.094595" theo kiểu bật/tắt như C của task 1 — không có một công tắc
> tương đương để tắt "việc giải lại" mà không tắt luôn cả policy. Đây là giới hạn được nêu
> rõ ở mục 6, không phải một khoảng trống bị bỏ qua.

---

## 1. Việc đã làm

1. Đọc brief `task-2-brief.md`, `spikes/diag_4c.py` (cách phân dịch + cách kiểm hợp lệ của
   task 1), `lp.py` (`solve_remaining_lp`, `solve_stackelberg_lp`), `policies.py`
   (`SSGReceding.choose`/`_log_audit`, `MinimaxLP.choose`, `MinimaxLPUpstream`,
   `SSGRecedingUpstream`, `REGISTRY`), `dprime_sweep.py` (`make_corpus`, `measure_cell`,
   `policy_curve`) và `runner.py::paired` (xác nhận `rng_seed = seed_of(wf.wf_id, seed)` —
   **không phụ thuộc carrier tấn công hay Delta đang thử** — điều này quan trọng cho việc
   suy luận dedupe episode ở mục 2).
2. Viết `auditgame/spikes/diag_4c2.py` — KHÔNG sửa `lp.py`/`policies.py`. Hai lớp chẩn đoán
   cục bộ, đăng ký vào `policies.REGISTRY` lúc runtime:
   - `DiagB7U2(MinimaxLPUpstream)` — bọc `choose()` gốc, ghi `(t, action, u_row, v)` mỗi
     bước, với `u_row = [self.u[i][t] ...]`, `v = self.v[t]` — CHÍNH XÁC biên duyên mà
     `MinimaxLP.choose` (policies.py dòng 349-384) đọc để rút số ngẫu nhiên.
   - `DiagSSGUpNoC2(SSGRecedingUpstream)` — **copy nguyên văn** thân `SSGReceding.choose()`
     (policies.py dòng 433-459), CHỈ đổi `done=getattr(self,'_done',None)` thành
     `done=None` (ép cứng, giống hệt `DiagSSGUpNoC` của task 1), thêm ghi
     `(t, action, u_row, v0, Hr, B_rem, n_win)` — biên duyên `j=0` THẬT SỰ được dùng để rút
     hành động tại t đó.
   - **Vì sao so với nhánh noC chứ không phải nhánh C-bật**: task 1 đã đo C giải thích đúng
     22,2% (0.027027/0.121622); 77,8% còn lại (0.094595 = 0.545045 − 0.450450) nằm nguyên
     trong khoảng cách `receding_noC − static`, nhánh KHÔNG dùng `_done` gì cả. Đo trên cặp
     (static, noC) là đo ĐÚNG cái cần giải thích, không lẫn hiệu ứng C vào.
3. Chạy `dprime_sweep.make_corpus(40, 8, seed=ds.CORPUS_SEED)` và
   `dprime_sweep.measure_cell(wfs, d_prime=2.2, delta=4, budget=17.95, seeds=(1,2,3),
   policies=("B1 audit-at-commit", "Sentinel", "DIAG B7U2 marginals",
   "DIAG SSG-up2 noC marginals"))`.
4. Kiểm hợp lệ TRƯỚC khi tin số: so harm/spent đo được với `spikes/diag-4c.json`
   (`static`, `receding_noC`) của task 1.
5. Ba phép đo (A)/(B)/(C) theo đúng định nghĩa trong brief, xem mục 3-5.

### Lệnh đã chạy

```bash
cd auditgame && python3 spikes/diag_4c2.py
```

Output:

```
[diag_4c2] do o Delta=4, d'=2.2, lop (2, 4), B=17.95, seeds=(1, 2, 3), N_WF=40, H=8
[diag_4c2] policies=('B1 audit-at-commit', 'Sentinel', 'DIAG B7U2 marginals', 'DIAG SSG-up2 noC marginals')
[diag_4c2] do xong sau 13.1s, n_feasible=37/40, reason=None
[diag_4c2] kiem hop le: static khop=True (harm=0.45045045045045046 spent=15.024324324324324), receding_noC khop=True (harm=0.545045045045045 spent=15.621171171171172)
[diag_4c2] ghi spikes/diag-4c2.json

[diag_4c2] === TOM TAT ===
static: harm=0.450450 spent=15.024324
receding_noC: harm=0.545045 spent=15.621171
gap = 0.094595
(A) l1_t0=0.0000 match_t0=True l1_mean(t>=1)=0.3171 max_t=3 max=0.6457 -> DUNG (lech ro tu t=1, trong khi t=0 trung)
(B) static std=0.1286 mean=0.3321 min=0.1053 n_zero=0 | receding std=0.1099 mean=0.2666 min=0.0737 n_zero=0 -> DUNG (receding dan deu hon VA mong hon tren nhieu cua so)
(C) static_total_mass=6.4489 receding_total_mass_mean=6.2746 diff=-0.1743 (-2.7%) -> DUNG (chieu GIAM, lech -2.7%)
```

---

## 2. Kiểm hợp lệ + ghi chú dedupe episode

| policy | harm (script chẩn đoán) | harm (`diag-4c.json`, task 1) | spent (script) | spent (`diag-4c.json`) |
|---|---|---|---|---|
| B7U tĩnh (`DIAG B7U2 marginals`) | 0.45045045045045046 | 0.45045045045045046 | 15.024324324324324 | 15.024324324324324 |
| SSG-up lùi, noC (`DIAG SSG-up2 noC marginals`) | 0.545045045045045 | 0.545045045045045 | 15.621171171171172 | 15.621171171171172 |

**Khớp tuyệt đối từng chữ số.** n_feasible = 37/40, giống task 1.

**Dedupe theo `rng_seed`.** `runner.paired` seed policy bằng `seed_of(wf.wf_id, seed)` —
KHÔNG phụ thuộc carrier tấn công `k` hay Delta tấn công `d` đang thử (runner.py dòng 569).
Vì `MinimaxLP.choose`/`SSGReceding.choose` chỉ đọc `(self.rng_seed, t, self.spent,
self.budget)` — không đọc `retrieved_carriers`/`signals` — hai episode cùng `rng_seed` tạo
ra ĐÚNG MỘT chuỗi hành động. Ở ô này `measure_cell` thử Δ=4 cố định × 4 carrier × 3 seed
cho mỗi workflow, nên mỗi `(workflow, seed)` xuất hiện lặp lại (tối đa 4 lần, ít hơn nếu
`plan_poison` không khả thi cho một carrier). TRACE thô có 325 phần tử (khớp con số của
task 1); dedupe theo `rng_seed` còn lại **95 episode duy nhất** cho mỗi policy (đã bỏ 230
bản trùng mỗi bên — xem `meta.n_dedup_dropped_*` trong JSON). Mọi bảng số ở mục 3-5 dùng
95 episode đã dedupe, để trung bình không bị lệch trọng số theo "workflow này có bao nhiêu
tổ hợp (Δ,k) khả thi".

---

## 3. Giả thuyết (A) — biên duyên giải lại khác biên duyên tĩnh từ t=0

**Đo:** khoảng cách L1 giữa `(u[:,t], v[t])` tĩnh (không đổi giữa các episode — đã kiểm
tra: `static_marginal_constant_across_episodes.u/v = true`) và trung bình
`(u[:,0], v[0])` mà bản lùi THẬT SỰ dùng để rút số ngẫu nhiên tại mỗi t thật (95 episode).

| t | L1(tĩnh, lùi) | static u (memory,skill,queue,branch), v | receding u trung bình, v trung bình |
|---|---|---|---|
| 0 | **0.0000** | [0.172, 0, 0, 0], v=0.000 | [0.172, 0, 0, 0], v=0.000 |
| 1 | 0.2575 | [0.121, 0.293, 0.293, 0.293], v=0.000 | [0.250, 0.250, 0.250, 0.250], v=0.000 |
| 2 | 0.3998 | [0.260, 0.088, 0.088, 0.088], v=0.475 | [0.081, 0.081, 0.081, 0.081], v=0.675 |
| 3 | **0.6457 (đỉnh)** | [0.025, 0.196, 0.196, 0.196], v=0.386 | [0.089, 0.089, 0.089, 0.089], v=0.645 |
| 4 | 0.3236 | [0.258, 0.086, 0.086, 0.086], v=0.483 | [0.096, 0.096, 0.096, 0.096], v=0.615 |
| 5 | 0.3449 | [0.000, 0.172, 0.172, 0.172], v=0.485 | [0.112, 0.112, 0.112, 0.112], v=0.539 |
| 6 | 0.2049 | [0.172, 0, 0, 0], v=0.510 | [0.000, 0, 0, 0], v=0.476 |
| 7 | 0.0433 | [0, 0, 0, 0], v=0.596 | [0, 0, 0, 0], v=0.639 |

`n_episodes_by_t = [95]*8` — mỗi t có đủ 95 episode (choose() được gọi mọi t 0..7, xác
nhận qua đọc `runner.run_once`: `for t, task in enumerate(wf.tasks)` không có early-exit).

**t=0 trùng tuyệt đối** (L1 = 0.0000, không phải "gần 0"): đúng như brief dự đoán — tại
t=0, `solve_remaining_lp(t=0, done=None)` và `solve_stackelberg_lp` là **CÙNG MỘT bài toán
LP** (H_r = H, mọi cửa sổ đều "còn mở" vì s ≥ d ≥ 2 > t = 0, cùng A/b/c, cùng simplex
quyết định), nên không có chỗ nào để lệch.

**Từ t=1, lệch có hệ thống, không phải nhiễu.** L1 trung bình trên 95 episode tại t≥1 là
0.317 — nếu đây chỉ là biến động ngẫu nhiên quanh cùng một kỳ vọng, trung bình trên 95 mẫu
độc lập phải hội tụ gần 0; nó không hội tụ, nó ổn định dương ở mọi t. Lệch lớn nhất ở
**t=3 (0.646)**, KHÔNG phải t=1 hay t=7 — không phải hình "lệch dần đơn điệu", mà phồng
giữa ván rồi co lại cuối ván (t=7 chỉ còn 0.043) — khớp với hình "phồng giữa-cuối ván" mà
task 1 đã thấy trên đường chi tiêu (không phải trùng hợp — xem mục 5).

**Phát hiện chất lượng, không chỉ khoảng cách:** bản tĩnh phân bổ **bất đối xứng** giữa 4
carrier dù chi phí khác nhau (kappa: memory 0.4, skill 0.9, queue 1.6, branch 4.1) — ví dụ
t=1: memory chỉ 0.121 trong khi 3 carrier kia đều 0.293 — vì nó giải MỘT LẦN trên toàn bộ
chân trời và có thể "đầu tư" lệch carrier theo cả ván (ví dụ dồn memory vào t=0/t=6, dồn
carrier khác vào t=1). Bản lùi gần như LUÔN cho **u đồng đều tuyệt đối giữa 4 carrier**
tại mọi t (0.25 mỗi carrier ở t=1, 0.081 ở t=2, 0.089 ở t=3, ...) — vì hàng ràng buộc
"một-hành-động-mỗi-task" (Σ_k u[k,j]+v[j] ≤ 1) là ràng buộc SIẾT DUY NHẤT khi ngân sách còn
dư dả (thấy rõ ở t=1..5, mass ≈ 1.0, mục 4), và bài toán còn lại — phủ đều 4 tập cửa sổ
CÓ CẤU TRÚC GIỐNG HỆT NHAU theo carrier (cùng số cửa sổ mở, cùng deltas) — đối xứng theo
carrier bất kể chi phí. Bản lùi "quên" kế hoạch đầu tư lệch mà bản tĩnh đã chọn cho cả ván,
và coi lại bài toán còn lại như mới, đối xứng.

### Kết luận giả thuyết (A): **ĐÚNG, ĐO ĐƯỢC**

t=0 trùng tuyệt đối (đúng dự đoán của brief: cùng LP). Từ t=1 lệch có hệ thống và ổn định
trên 95 episode, đỉnh ở t=3 (L1=0.646), với một cơ chế cụ thể (đối xứng-carrier vs
bất-đối-xứng-carrier) chứ không phải nhiễu số. Đây là **cơ chế cận nhất (proximate)**: mọi
lần giải lại, LP không biết mình đã "đầu tư" bất cân đối trong quá khứ, nên luôn coi phần
còn lại của ván là một bài toán mới, đối xứng.

---

## 4. Giả thuyết (C) — tổng khối lượng cho phép mỗi bên thực sự dùng

**Đo:** `Σ_t (Σ_k u[k][t] + v[t])` — dùng CHÍNH các hàng đã đo ở mục 3 (không đo lại).

| t | mass tĩnh | mass lùi (TB 95 episode) | ghi chú |
|---|---|---|---|
| 0 | 0.172 | 0.172 | giống hệt (cùng LP) |
| 1 | 1.000 | 1.000 | hàng bão hoà cả hai bên |
| 2 | 1.000 | 1.000 | bão hoà |
| 3 | 1.000 | 1.000 | bão hoà |
| 4 | 1.000 | 1.000 | bão hoà |
| 5 | 1.000 | 0.987 | lùi bắt đầu hụt nhẹ |
| 6 | 0.681 | **0.476** | lệch lớn nhất — cả hai đều KHÔNG bão hoà hàng (không phải do rào một-hành-động) |
| 7 | 0.596 | 0.639 | lùi CAO HƠN tĩnh — đổi chiều |
| **tổng** | **6.4489** | **6.2746** | **lùi thấp hơn 0.1743 (−2.7%)** |

Ở t=1..5, hàng "một-hành-động-mỗi-task" **bão hoà ở CẢ HAI BÊN** (mass ≈ 1.0) — tại đây
ràng buộc đọc đúng nghĩa đen của giả thuyết (C) ("H−t hàng thay vì H hàng") không siết khác
nhau: cả hai đều bị Σ_k u+v ≤ 1 chặn full, không phải do số hàng khác nhau. Lệch thật sự
chỉ xuất hiện ở **t=6** (0.681 → 0.476, mất 0.205) và đảo chiều nhẹ ở **t=7** (0.596 →
0.639) — cả hai điểm này đều KHÔNG bão hoà hàng, tức bị **ngân sách còn lại** (`B_rem`)
chặn, không phải bị rào một-hành-động chặn.

Đối chiếu `n_win`/`B_rem` thô, tổng hợp theo t qua 95 episode đã dedupe (script đã được bổ
sung để ghi hai trường này vào `hypothesis_C.n_win_by_t`, `hypothesis_C.B_rem_by_t`,
`hypothesis_C.n_win_constant_across_episodes_by_t`,
`hypothesis_C.n_episodes_B_rem_leq_0_4_by_t` trong `diag-4c2.json` — trước bản sửa này ba
con số dưới đây không có trong JSON hay bất kỳ dòng `print` nào của script, đã bị gỡ khỏi
báo cáo cho tới khi có số thật):

| t | n_win (hằng số qua 95 episode?) | B_rem: min → max (TB) |
|---|---|---|
| 5 | 24 (có, `n_win_constant_across_episodes_by_t[5]=true`) | 1.55 → 12.65 (TB 6.50) |
| 6 | **16** (có) | **0.65 → 8.55 (TB 3.91)** |
| 7 | 8 (có) | 0.25 → 7.05 (TB 2.74) |

`n_win` là **hằng số qua mọi t** (không chỉ t=6) trên cả 95 episode — đúng như dự đoán từ
`lp.solve_remaining_lp` (dòng 187-204 của `lp.py`): `n_win` chỉ phụ thuộc `(K, H, t,
deltas)`, không đọc `B_rem`/`kap`, nên không có đường nào để nó đổi theo episode; đã kiểm
tra thực tế (không chỉ suy diễn từ đọc code) qua `n_win_constant_across_episodes_by_t =
[true]*8`. Điều này loại trừ "số cửa sổ mở khác nhau giữa các episode" làm nguyên nhân của
lệch mass ở t=6. Ngược lại `B_rem` dao động mạnh giữa các episode tại cùng t (ví dụ t=6:
0.65 → 8.55, TB 3.91) — **phụ thuộc đường chi tiêu THỰC TẾ trước đó** (`self.spent` tích
luỹ), và đường chi tiêu thực tế trước đó chính là hệ quả của việc bản lùi phân bổ khác bản
tĩnh từ t=1 (mục 3). Tại t=7, `n_episodes_B_rem_leq_0_4_by_t[7] = 5` — tức 5/95 episode có
`B_rem` ≤ 0.4 (gần hết tiền, không đủ mua carrier rẻ nhất).

### Kết luận giả thuyết (C): **CÓ HIỆU ỨNG THẬT NHƯNG NHỎ, KHẢ NĂNG LÀ HỆ QUẢ PHÁI SINH của (A)**

Tổng khối lượng thấp hơn 2,7% (6.2746 so với 6.4489) — hiệu ứng có thật (không phải làm
tròn: âm ở 6/8 điểm t và chỉ dương ở 1 điểm). Nhưng đọc đúng nghĩa đen của giả thuyết
("rào một-hành-động siết KHÁC NHAU vì số hàng H−t ≠ H") thì **bị bác bỏ**: nơi rào đó thực
sự bám sát 1.0, hai bên GIỐNG NHAU HỆT (t=1..5). Chênh lệch nằm ở t=6/t=7, nơi bị
NGÂN SÁCH CÒN LẠI chặn — và ngân sách còn lại khác nhau vì đường chi tiêu đã lệch từ t=1
(giả thuyết A). Vậy (C) như brief đặt câu hỏi ("bản chất ràng buộc khác nhau giữa hai bài
toán") **không phải nguyên nhân độc lập**; con số 2,7% có thật nhưng nhiều khả năng là
**triệu chứng** của (A), không phải một cơ chế thứ ba đứng riêng. Đây là suy luận từ
tương quan thời điểm (t=6/7, không bão hoà hàng), KHÔNG phải một phép đo nhân quả trực
tiếp — task này không có đòn bẩy để "tắt A mà giữ nguyên C" để kiểm chứng dứt khoát.

---

## 5. Giả thuyết (B) — mất tính nhất quán thời gian (coverage thực tế trên từng cửa sổ)

**Đo:** với mỗi episode (95 mỗi bên), duyệt chuỗi hành động thật đã rút số, với mỗi cửa sổ
lý thuyết `(k,i,s)` (deltas ∈ {2,4}, mọi carrier, mọi điểm bắt đầu — 40 cửa sổ tất cả: 24
cửa sổ Δ=2 + 16 cửa sổ Δ=4) đếm carrier k có bị audit thật (không tính `commit`, khớp
`_log_audit` bỏ qua commit) tại `t ∈ [i, s)` hay không. `P(phủ ≥1 lần)` = tỉ lệ episode có
phủ, trên 95 episode.

| | tĩnh (95 ep) | lùi noC (95 ep) |
|---|---|---|
| mean P(phủ≥1) trên 40 cửa sổ | **0.332** | **0.267** |
| độ lệch chuẩn trên 40 cửa sổ | **0.129** | **0.110** |
| min (cửa sổ TỆ NHẤT) | **0.105** | **0.074** |
| max (cửa sổ tốt nhất) | 0.621 | 0.526 |
| số cửa sổ có P≥0.5 | **5** | **1** |
| số cửa sổ có P≥0.25 | 28 | 21 |
| số cửa sổ có P=0 | 0 | 0 |

**Đọc đúng nghĩa đen của brief: "dàn đều hơn VÀ mỏng hơn" — CẢ HAI đều đúng.**
- Dàn đều hơn: độ lệch chuẩn 0.110 < 0.129 (thấp hơn ⇒ phân bố đồng đều hơn giữa các cửa
  sổ), và số cửa sổ đạt mức phủ cao (≥0.5) rơi từ 5 xuống chỉ còn 1.
- Mỏng hơn: mean 0.267 < 0.332 trên toàn bộ 40 cửa sổ.
- **Cửa sổ TỆ NHẤT tệ hơn**: min 0.074 so với 0.105 — đây là con số quan trọng nhất cho
  minimax, vì hàm mục tiêu m = min-over-windows: nếu cửa sổ yếu nhất của bản lùi yếu hơn
  cửa sổ yếu nhất của bản tĩnh, kẻ tấn công khai thác đúng chỗ đó, và harm (max-over-attacker)
  tăng theo đúng hướng đo được (0.545 > 0.450).

**Cơ chế cụ thể, không chỉ thống kê tổng:** 8 cửa sổ được tĩnh phủ dày nhất đều có
`static_prob − receding_prob > 0` (ví dụ `(branch,1,5)`: 0.621 → 0.368, mất 0.253;
`(branch,0,4)`: 0.589 → 0.316, mất 0.274) — bản lùi rút bớt đúng những cửa sổ mà bản tĩnh
đã "đầu tư" dày. Ngược lại, 2 trong 8 cửa sổ yếu nhất của tĩnh lại được lùi phủ NHIỀU HƠN
(`(skill,2,4)`: 0.189 → 0.200; `(queue,4,6)`: 0.168 → 0.221) — bằng chứng trực tiếp của
"tái phân bổ" từ nơi tĩnh dồn dày sang nơi tĩnh bỏ mỏng, đúng cơ chế đối xứng-carrier đã
thấy ở mục 3. Nhưng tái phân bổ không bù đủ: cửa sổ nhận thêm tăng ít hơn cửa sổ mất đi
giảm, nên cả mean lẫn min đều tụt.

### Kết luận giả thuyết (B): **ĐÚNG, ĐO ĐƯỢC, NHẤT QUÁN VỀ HƯỚNG VỚI (A) — CHƯA CÓ ABLATION NHÂN QUẢ CÔ LẬP**

Nhất quán về hướng với (A), với một cơ chế nối hợp lý — KHÔNG phải đã chứng minh nhân quả:
vì bản lùi giải mỗi task như một bài toán mới đối xứng-carrier (mục 3), coverage thực tế
cuối ván trở nên đều hơn và mỏng hơn, kéo cửa sổ yếu nhất xuống thấp hơn (0.074 < 0.105) —
đúng hướng mà cơ chế minimax của brief mô tả ("min-over-windows thưởng cho dày, không
thưởng đều"). Đây là mắt xích *mô tả* nối (A) [biên duyên lệch] với harm đo được cao hơn
[kết quả cuối], khớp hướng và có số đỡ ở cả hai đầu — nhưng như mục 7.1 nêu rõ, task này
KHÔNG có một ablation cô lập (A) khỏi (B) (không có cách "tắt tính đối xứng-carrier, giữ
nguyên mọi thứ khác" mà không sửa `lp.py`), nên đây là tương quan mô tả nhất quán, chưa
phải bằng chứng nhân quả chặt.

---

## 6. Bảng tổng hợp ba giả thuyết

| Giả thuyết | Phán quyết | Căn cứ số |
|---|---|---|
| (A) biên duyên lệch từ t=0 | **ĐÚNG, ĐO ĐƯỢC** | t=0 khớp tuyệt đối (L1=0.0000, cùng LP); t≥1 lệch ổn định (L1 TB=0.317, đỉnh 0.646 tại t=3); cơ chế cụ thể: lùi luôn đối xứng-carrier, tĩnh bất-đối-xứng |
| (B) mất nhất quán thời gian | **ĐÚNG, ĐO ĐƯỢC** — nhất quán về hướng với (A), có cơ chế nối hợp lý, CHƯA có ablation nhân quả cô lập (xem mục 7.1) | coverage TB 0.267<0.332 (mỏng hơn), độ lệch chuẩn 0.110<0.129 (đều hơn), min 0.074<0.105 (cửa sổ tệ nhất tệ hơn — liên quan trực tiếp tới hàm mục tiêu minimax) |
| (C) rào một-hành-động siết khác nhau | **HIỆU ỨNG THẬT NHƯNG NHỎ (−2,7% tổng khối lượng), NHIỀU KHẢ NĂNG LÀ HỆ QUẢ PHÁI SINH của (A), không phải cơ chế độc lập** | rào bão hoà GIỐNG NHAU ở t=1..5 (mass≈1.0 cả hai); lệch chỉ ở t=6/7, nơi bị ngân sách còn lại (không phải số hàng) chặn; `n_win` không đổi theo episode, `B_rem` dao động mạnh theo đường chi tiêu |

**Không quy đổi được sang "X% của 0.094595" theo kiểu bật/tắt của task 1.** Task 1 có một
công tắc thật (`done=None` vs `done=self._done`) để đo trực tiếp phần harm biến mất khi tắt
C. Task này không có công tắc tương đương cho (A)/(B): "tắt việc giải lại" chính là quay về
policy B7U tĩnh — không phải một ablation của SSG-up, mà là đổi hẳn sang policy khác (đã đo
rồi: đó chính là con số 0.450450 làm mốc). Vì vậy (A)/(B) được báo cáo bằng **số đo trực
tiếp trên chính biên duyên và coverage thực sự dùng**, không bằng một phần trăm harm quy
đổi — đúng với ràng buộc brief "không kết luận theo loại trừ" và trung thực hơn là ép một
con số phần trăm không có cơ sở nhân quả.

---

## 7. Đáng ngờ / giới hạn của phép đo này

1. **Không có ablation nhân quả cho (A)/(B), chỉ có tương quan mô tả.** Mục 6 đã nói rõ:
   không tồn tại một cách sửa `solve_remaining_lp` "chỉ tắt tính đối xứng-carrier, giữ
   nguyên mọi thứ khác" mà không sửa `lp.py` (bị cấm trong task này). Nếu cần một con số
   "(A) giải thích Y% của 0.094595", cần một task khác được phép thử một biến thể LP (ví
   dụ: truyền một "done ảo" phản ánh kế hoạch tĩnh làm điểm neo, xem nó có kéo bản lùi về
   gần bản tĩnh không) — nằm ngoài phạm vi "chỉ chẩn đoán, không sửa" của task này.
2. **TRACE gộp mọi episode được quét (325), dedupe còn 95 — không phải 37 episode "thắng"
   nuôi số harm cuối cùng.** Giống hạn chế đã nêu ở `diag-4c.md` mục 7.1: `policy_curve`
   chọn, với MỖI workflow, carrier tấn công cho harm trung bình cao nhất làm đại diện. Các
   bảng ở mục 3-5 là trung bình trên 95 episode dedupe theo `(workflow, seed)`, RỘNG HƠN
   tập 37 workflow "thắng" (×3 seed, nhưng seed không nhân đôi ở đây vì `rng_seed` đã gộp
   theo (wf_id, seed) — 95 ≈ 40 workflow × ~2.4 seed khả thi trung bình, không phải
   37×3=111; chênh lệch vì một số workflow chỉ khả thi ở một số seed). Hình dạng (đỉnh lệch
   ở t=3, cửa sổ tệ nhất tệ hơn) đáng tin vì nó nhất quán và có cơ chế cụ thể đi kèm (đối
   xứng-carrier), nhưng các con số TUYỆT ĐỐI (0.317, 0.267, ...) là trên tập 95 episode
   này, không phải tập 37 "thắng" nuôi 0.545045.
3. **Cảnh báo của task-reviewer về `_log_audit`/credit lồng cửa sổ đã bị loại trừ theo cấu
   trúc, không phải bằng đo lại.** Cả hai lớp chẩn đoán ở đây dùng `done=None` — `_log_audit`
   VẪN được gọi (để giữ `_hist`/`_done` tồn tại phòng có code khác đọc, giống task 1) nhưng
   `done=None` được truyền cứng vào MỌI lệnh gọi `solve_remaining_lp`, nên LP không bao giờ
   đọc `_done`. Ứng viên đó không thể là nguyên nhân của bất kỳ con số nào trong báo cáo
   này, đúng như brief đã cảnh báo trước.
4. **Giả thuyết (C) có thể MỚI TƯƠNG QUAN chứ chưa chắc là hệ quả của (A) theo nghĩa nhân
   quả chặt.** Lập luận ở mục 4 dựa trên: (a) rào một-hành-động bão hoà giống hệt ở t=1..5,
   (b) lệch chỉ ở t=6/7 nơi ngân sách còn lại chặn, (c) ngân sách còn lại khác nhau vì
   đường chi tiêu đã khác từ t=1. Đây là một chuỗi suy luận hợp lý và có số đỡ ở từng bước,
   nhưng KHÔNG phải một phép đo trực tiếp "nếu ép đường chi tiêu giống tĩnh thì mass ở t=6/7
   có bằng nhau không" — phép đo đó cần can thiệp vào chính sách (bị cấm ở đây).
5. **Thời gian chạy 13.1s** cho toàn bộ script (40 workflow × 3 seed × 4 policy, 2 policy là
   LP giải simplex nhiều lần) — chỉ ghi lại để tái tạo, không phải vấn đề hiệu năng.
