# Sentinel v3 — kết quả headline trên dev, đọc theo HAI metric (28/09/2026)

Báo cáo này trình bày kết quả headline của Study 2 trên **dev**, đọc song song theo hai metric, và nêu một **mâu thuẫn nội tại của draft** cần tác giả/thầy quyết trước khi chốt headline paper. Chưa có lượt eval P5 nào chạy.

## 0. Xuất xứ (provenance)

| | |
|---|---|
| Records | `spikes/v3-run/dev-headline-main/main.jsonl`, sha256 `e1db94d590f3…accde4a4`, 218.456 record (không commit, D33) |
| Quy mô | 100 workflow dev × 2 seed (1, 2) × 7 attacker held-out × Δ ∈ {0,1,2,4,8} × ρ ∈ {0; 0,25; 0,5; 1} |
| Ô bảng | χ = 1,33; d′ = 2,21; K_d = 2; ngân sách b1 (ô headline, lọc bằng `v3_run --headline`) |
| Bảng dòng 5 | `sha256:83ecff91b369…` (dựng headline-scoped, base-R 16, 0 top-up) |
| Tinh chỉnh | `reference/v3_tuned.json`, log sha256 `36550dae6ba0…` (40 workflow, 3 kernel, 2048 hạt) |
| Freeze | `freeze-v3: clean sha256:8144dc83734e` \| `freeze-d35: clean e46f8a5c2f94` \| base `clean c789fa7362e0` |
| Bootstrap | wild cluster (Webb), 17 họ repo, N = 10.000, α = 0,05, re-max qua cột trong từng lần rút |

**Chưa có trong lượt này (giữ TBD, N3):** B7 (T21 chưa cài), `Sentinel −transition uncertainty` (cần lượt tinh chỉnh `--nominal-only` đã hoãn), exploitability và RQ3 (cần block `br`), độ trung thực bảng-vs-rollout (cần thế giới rollout), và toàn bộ số eval held-out (P5).

## 1. Vấn đề metric — phát hiện chính của báo cáo này

Trong mã hiện tại:

- **Tinh chỉnh** (`tools/v3_tune.py:328`) tối ưu theo **`runner.loss_of`**, tức **L của Định nghĩa 1**: `L = harm + λ_Q·FQ + λ_T·(task sạch mất)`, với λ_Q = 0,54865 và λ_T = 0,5.
- **Đánh giá** (`metrics.worst_case_harm` → `metrics.table(..., field="harm")`, và `gain_ci` cũng mặc định `field="harm"`) báo cáo **V = worst-case HARM**. Docstring ghi "Draft S9.3 primary".

Tức **draft tinh chỉnh theo L nhưng khai báo V = harm là metric chính**. Hai metric này cho **kết luận trái ngược nhau**, nên việc chọn metric headline **quyết định kết luận của paper**.

## 2. Headline Δ ∈ {4, 8}: Sentinel so với B1, hai metric

| ρ | V_B1 (L) | V_Sent (L) | **gain theo L** | V_B1 (harm) | V_Sent (harm) | gain theo harm |
|---|---|---|---|---|---|---|
| 0 | 1,236 | 0,956 | **+22,6%** [+15,9; +33,5] | 0,787 | 0,821 | −4,3% [−11,2; +4,8] |
| 0,25 | 1,086 | 0,859 | **+20,9%** [+11,7; +37,0] | 0,646 | 0,792 | −22,6% [−32,3; −3,4] |
| 0,5 | 0,951 | 0,818 | **+14,0%** [+3,6; +23,8] | 0,512 | 0,750 | −46,4% [−62,2; −25,9] |
| 1 | 0,604 | 0,889 | **−47,2%** [−90,8; −13,0] | 0,197 | 0,774 | −292,9% [−483,2; −178,9] |

Theo **L**: Sentinel **thắng B1 ở ρ ≤ 0,5** (cả ba khoảng tin cậy không chứa 0) và **thua ở ρ = 1**. Theo **harm**: Sentinel thua ở mọi ρ.

## 3. Vì sao lật: B1 mua harm thấp bằng thiệt hại kèm

Số phụ (trung bình mỗi episode, gộp mọi ô):

| Hệ thống | harm | FQ | task sạch mất | chi phí audit |
|---|---|---|---|---|
| B1 audit-at-commit | 0,424 | **0,000** | **0,705** | 41,32 |
| Sentinel | 0,645 | 0,099 | **0,083** | 18,95 |
| Oracle (+) | 0,000 | 0,000 | 0,116 | 18,85 |

B1 đạt harm thấp nhưng **phá 0,705 task sạch mỗi episode** (clean-completion 90,4%), trong khi Sentinel chỉ mất 0,083 (clean-completion 98,6–99,2%) và FQ 0,099. Vì λ_T = 0,5, phần thiệt hại kèm của B1 cộng ≈ 0,35 vào L — đủ để đảo dấu so sánh. **Metric harm-only không tính phần này;** L của Định nghĩa 1 thì có.

Lưu ý: B1 có FQ = 0 nhưng vẫn mất task sạch, vì đó là thiệt hại kèm của các lần **cách ly ĐÚNG** (gỡ nhánh nhiễm cũng gỡ patch hợp lệ phía sau) — đúng ngữ nghĩa O7.

## 4. Bản đồ chế độ theo L (gain % [CI]) — khớp lý thuyết đã sửa

| ρ | Δ=0 | Δ=1 | Δ=2 | Δ=4 | Δ=8 |
|---|---|---|---|---|---|
| 0 | +20,2 [+14;+25] | +10,4 [+6;+17] | +14,3 [+10;+23] | +18,8 [+10;+28] | **+22,6** [+16;+35] |
| 0,25 | +8,9 [−4;+17] | +5,0 [−3;+15] | +7,8 [+1;+15] | +11,0 [−1;+25] | **+23,0** [+14;+41] |
| 0,5 | −14,5 [−29;−3] | −18,1 [−29;−7] | −15,1 [−24;−3] | +1,9 [−18;+15] | **+24,9** [+16;+40] |
| 1 | −56,5 [−112;−23] | −65,0 [−109;−42] | −77,4 [−116;−55] | −54,4 [−101;−19] | −27,8 [−79;+8] |

Hai chiều đều khớp **Hệ quả 5 (mô hình phủ) sau khi sửa**:

1. **gain không giảm theo Δ** ở mọi ρ (vd ρ = 0,5: −14,5 → −18,1 → −15,1 → +1,9 → **+24,9**). Δ càng lớn, phân bổ audit càng có chỗ thắng.
2. **gain giảm theo ρ** (ở Δ = 8: +22,6 → +23,0 → +24,9 → −27,8). Đúng với chặn `p_d − p_ρ`: ρ càng cao, review ở commit càng thấy nhiều, chặn càng co, âm được.
3. **Ranh giới chuyển chế độ** nằm quanh ρ ≈ 0,5: ở đó B1 thắng khi Δ ≤ 2 và Sentinel thắng khi Δ = 8.

Đây là điều đáng chú ý: **lý thuyết (đã sửa) tiên đoán đúng cả vùng nó thắng và vùng nó không thể thắng.** Con số dự phóng +27,6% của draft (B1 ≈ 0,412 / Sentinel ≈ 0,272) dựa trên **Định lý 4 hướng sai** mà rà soát lý thuyết đã phát hiện; hướng "Sentinel thắng" thì được xác nhận trên L ở ρ ≤ 0,5.

## 5. Sentinel so với các baseline khác (theo L, ô headline)

Ở ρ = 0,5, gain theo L so với B1:

| Hệ thống | gain L | FQ / episode |
|---|---|---|
| Oracle (+) | +48,4% | 0,000 |
| **Sentinel** | **+14,0%** | **0,099** |
| Sentinel [dhat=oracle] | +14,0% | 0,098 |
| Sentinel −alarm memory | +13,3% | 0,056 |
| Sentinel −randomization | +12,4% | 0,101 |
| Sentinel −benign-drift | −8,9% | **0,499** |
| B4 audit-on-retrieval | −37,5% | 0,864 |
| B6 two-stage | −55,0% | 0,878 |
| SW randomised | −70,7% | 1,121 |
| B2 uniform random | −94,7% | 1,707 |
| B5 risk-score | −105,9% | 1,964 |
| cost-greedy | −131,9% | 2,252 |
| B3 audit-on-insertion | −304,3% | 4,383 |

**Sentinel là hệ thống duy nhất không phải Oracle thắng được B1 theo L.** Mọi baseline phân bổ audit khác đều tệ hơn B1 rất nhiều, và nguyên nhân đọc thẳng từ cột FQ: chúng cách ly sai rất nhiều (B3 tới 4,38 FQ/episode) nên bị λ_Q phạt nặng. Đóng góp cốt lõi của Sentinel vì vậy là **phân bổ audit mà vẫn giữ FQ rất thấp**.

**Ablation (theo L):** thành phần chịu tải nhiều nhất là **mô hình hoá drift lành** — bỏ nó làm gain rơi từ +14,0% xuống −8,9% và FQ tăng 5 lần (0,099 → 0,499). Bỏ ngẫu nhiên hoá (+12,4%) hoặc bỏ nhớ báo động (+13,3%) gần như không đổi; `dhat=oracle` cũng bằng bản đầy đủ (+14,0%), tức ước Δ̂ của dòng 1 đã sát oracle ở ô này.

## 6. Kiểm tính toàn vẹn của lượt chạy

Đã kiểm, đều sạch:

- **Sentinel dùng bảng thật:** `line5_source = "table"` cho **cả 15.604** record Sentinel (không có bản dự phòng nào).
- **Δ̂ của dòng 1 chính xác:** trung bình 0,02 / 1,98 / 7,83 ở Δ = 0 / 2 / 8.
- **Dòng 8 bắn đúng:** tỉ lệ cách ly đúng carrier (true_q) 75–99% tuỳ ô.
- **Đối chứng D28 đạt ở mọi ρ:** Oracle = 0,000; vế âm đạt.
- `line23` báo "infeasible" ở K = 4, H = 10 — đúng như khai (kiểm tra game chính xác không khả thi ở K lớn), ghi theo N3, không phải lỗi.

### Cơ chế thua ở Δ nhỏ (đã truy)

Sentinel cần ~2–3 task tích luỹ belief để vượt τ = 0,9 rồi mới cách ly. So `detected_at` với `harm_locked_at` trên cột xấu nhất (ρ = 0,5):

| Δ | phát hiện | harm khoá | kết quả |
|---|---|---|---|
| 2 | 2,67 | 2,11 | **trễ một nhịp** → harm 0,842 |
| 8 | 2,70 | 8,35 | **kịp** → harm 0,619 |

Tấn công khoá harm *trong* cửa sổ trễ (Δ nhỏ) thì lọt; Δ lớn thì bị bắt. τ = 0,9 (cao, do tinh chỉnh ngại FQ) làm cửa sổ trễ rộng ra. Đây là **tính chất thật của chính sách**, không phải lỗi — và nó chính là cơ chế đứng sau "gain không giảm theo Δ" ở mục 4.

### Vệ sinh held-out còn nguyên

Bộ attacker tinh chỉnh (D18) **rời hoàn toàn** bộ held-out: `tuning_attack_names` chủ động loại mọi cột có behaviour-key giao với held-out (`if keys & held: continue`). Ba cột xấu nhất của held-out (`branch-first-write-e0.6`, `memory-mid-write-e0.3`, `queue-mid-write-e0.6`) **không** có trong bộ tinh chỉnh — đúng thiết kế. **Không được** thêm chúng vào bộ tinh chỉnh để cải thiện số: đó là train trên tập test.

## 7. Điều cần tác giả/thầy quyết

1. **Metric headline là gì?** Lập luận cho **L (Định nghĩa 1)**: chính paper định nghĩa nó là mục tiêu; policy được tinh chỉnh theo nó; bỏ qua thiệt hại kèm sẽ làm "audit hết ở commit" đẹp giả tạo (B1 phá 10% task sạch mà harm-only không tính). Nhưng **draft khai V = harm là primary (S9.3)**, nên đổi headline **phải khai một lệch chuẩn**. Khuyến nghị: báo cáo **cả hai**, lấy L làm headline, khai lệch chuẩn, và giữ V = harm như một cột của Table 2.
2. **Định khung kết quả.** Không phải "Sentinel thắng tuyệt đối", mà **bản đồ chế độ**: thắng ở ρ ≤ 0,5 (mạnh nhất khi Δ lớn), thua ở ρ = 1 — và **lý thuyết đã sửa tiên đoán đúng ranh giới này**. Đây là phát biểu mạnh hơn và trung thực hơn dự phóng +27,6% của draft.
3. **Chưa chốt được** cho tới khi có: block `br` (exploitability, RQ3), B7 (T21), lượt `--nominal-only` (cột −transition), và **P5 eval held-out** (cần người dùng ký `frozen/V3-GATE4.json`).

## 8. Tái lập

```
cd auditgame
../.venv/bin/python -m v3.freeze_v3 --write          # manifest (bước P4)
../.venv/bin/python tools/v3_build_table.py --tuned reference/v3_tuned.json \
    --chis 1.33 --dprimes 2.21 --base-r 16 --jobs 8  # bảng headline
../.venv/bin/python tools/v3_run.py --split dev --blocks main --headline --seeds 2 --jobs 8 \
    --systems "B1 audit-at-commit" ... "Sentinel -benign-drift"
```

Gain theo L tính bằng chính bộ bootstrap của `metrics.gain_ci`, chỉ đổi `field="loss"` sau khi gắn `runner.loss_of(rec)` vào mỗi record; không metric/CI nào được viết lại.

## 9. Bảng đầy đủ: exploitability và cánh −transition (28/09)

Mục này **bổ sung**, không thay thế mục 0–8: nó thêm hai thứ mục 0–8 phải để TBD — **exploitability** (cần block `br`) và **cánh ablation `Sentinel −transition uncertainty`** (cần lượt tinh chỉnh `--nominal-only`) — và đọc cả hai theo **hai metric** như mục 1 đã đặt ra. Không lượt mô phỏng nào được chạy lại; đây là tổng hợp trên bản ghi đã có.

### 9.0 Xuất xứ bổ sung

| Khối | Tệp | sha256 | Số dòng | Hệ thống |
|---|---|---|---|---|
| main (held-out) | `spikes/v3-run/dev-headline-main/main.jsonl` | `e1db94d590f3…` | 218.456 | 14 hệ |
| br (best-response) | `spikes/v3-run/dev-headline-br/br.jsonl` | `cba9efecc44d…` | 1.981.728 | 14 hệ |
| main-trans | `spikes/v3-run/dev-headline-main-trans/main.jsonl` | `3fbee05721c9…` | 15.604 | `Sentinel −transition uncertainty` |
| br-trans | `spikes/v3-run/dev-headline-br-trans/br.jsonl` | `e389807f92d4…` | 141.552 | `Sentinel −transition uncertainty` |

Giữ lại sau khi lọc: 218.456 main + 15.604 main-trans (mọi Δ) + 376.096 br + 26.864 br-trans (chỉ Δ ∈ {4, 8}) = 637.020 bản ghi, **đỉnh bộ nhớ 741 MB**.

Cách đọc tệp `br.jsonl` 2,08 GB: **stream từng dòng**, `json.loads` rồi *chiếu ngay* xuống 11 trường mà metric cần (`policy, wf, repo, seed, split, attack, delta, placement, harm, fq, t_lost`) và **bỏ Δ ∉ {4, 8}** trước khi giữ; các trường nặng (`c_traj`, `audits`, `quarantines`, `world`, `decision_log_sha256`) không bao giờ vào bộ nhớ, và chuỗi được `sys.intern`. Không có lúc nào cả tệp nằm trong RAM.

**Lệch xuất xứ phải khai (N3):**

- Hai lượt 14 hệ (`main`, `br`) mang `v3_manifest_live` `8144dc83734e`; hai lượt −transition mang `c238e058dfcb` — chúng có thêm `reference/v3_tuned_nominal.json` và log của nó, thứ mà lượt 14 hệ không có. **`grid_digest` giống nhau ở cả bốn lượt** (`acbe9bdc48fd`), nên ô bảng và cột attacker khớp nhau; nhưng đây **vẫn là hai manifest khác nhau**, và so sánh −transition với Sentinel là so **xuyên lượt**, không phải trong cùng một lượt.
- Header freeze của lượt `br` báo **freeze-v3 DRIFTED ở 1 chỗ** (`files/tools/v3_tune.py: changed`) — là **công cụ tinh chỉnh**, không phải module chính sách hay thế giới; JSON tinh chỉnh mà nó dùng vẫn là `reference/v3_tuned.json` không đổi. Ghi ở đây để không ai đọc lượt này như một lượt freeze sạch.
- Khối đối chứng D28 **của riêng** hai lượt −transition đọc `ok: false` **chỉ vì** một lượt một hệ không có bản ghi B1 / Oracle / sweeper để tính đối chứng. Bản ghi tự thân vẫn hợp lệ; đối chứng ở mục này tính trên **bản ghi đã trộn** theo từng ρ và đạt.

Đối chứng D28 **đạt ở cả 4 ρ** trên bản ghi đã trộn (Oracle = 0,000 ở Δ ∈ {4, 8}; vế âm đạt), nên mọi số Sentinel bên dưới đọc được qua `metrics.Readout` mà không chạm cửa `ControlsNotRead` / `ControlsFailed`.

### 9.1 Cách tính hai metric, gain và exploitability (không viết lại metric nào)

- **V(harm)**: `metrics.table(..., field="harm")` — primary của draft S9.3.
- **V(L)**: gắn `r["loss"] = runner.loss_of(r)` vào từng bản ghi rồi `metrics.table(..., field="loss")`; L = harm + λ_Q·FQ + λ_T·(task sạch mất), λ_Q = 0,54865, λ_T = 0,5.
- **Khoảng tin cậy V**: chính `metrics.boot_values` + `metrics.interval` (wild cluster Webb, N = 10.000, α = 0,05, re-max qua cột trong từng lần rút), một bộ rút họ **dùng chung** cho cả 15 hệ.
- **gain vs B1**: `metrics.gain_ci` nguyên bản cho harm; cho L là bản **sao nguyên thân hàm** `gain_ci` chỉ luồn thêm `field` (hàm gốc cứng `field="harm"`) — vẫn cùng `boot_values` / `interval`, vẫn rút theo cặp, vẫn re-max qua cột mỗi lần rút.
- **Exploitability** = V_BR − V_held-out, theo `metrics.exploitability` cho harm và bản sao cùng thân hàm cho L.

**Lệch thiết kế phải khai (N3).** Chỉ dẫn ban đầu là lấy V_BR theo `table(recs, policy, (grid.BR_COLUMN,), deltas, field="loss")`. **Không dùng được:** block `br` có 16–108 bản ghi *placement* cho mỗi (wf, seed, Δ, ρ), nên `table` ném đúng lỗi bảo vệ của nó — `two records for one episode ('BR@0', 'v2-007', 1)` (đã kiểm chứng). V_BR vì vậy lấy đúng đường của `metrics.v_best_response`: **cross-fit** qua `metrics_v2.crossfit_value` (D27), với L đưa vào chỗ harm cho bản metric L. Đây là cùng một đoạn mã đã được kiểm, chỉ đổi trường được cho điểm.

**Đối chiếu đường harm với `metrics.exploitability`:** trùng **khít từng bit** (so sánh `==` trên float) ở **16/16** trường hợp — 4 hệ × 4 ρ. Ví dụ:

| ρ | Hệ thống | của mục này | `metrics.exploitability` | trùng |
|---|---|---|---|---|
| 0 | Sentinel | -0,0652285714 | -0,0652285714 | ✔ |
| 0 | B1 audit-at-commit | -0,0651563218 | -0,0651563218 | ✔ |
| 0 | Sentinel -transition uncertainty | -0,0903666667 | -0,0903666667 | ✔ |
| 0 | Oracle (+) | 0,0000000000 | 0,0000000000 | ✔ |
| 0,25 | Sentinel | -0,0360528302 | -0,0360528302 | ✔ |
| 0,25 | B1 audit-at-commit | -0,1046414634 | -0,1046414634 | ✔ |
| 0,25 | Sentinel -transition uncertainty | -0,0360528302 | -0,0360528302 | ✔ |
| 0,25 | Oracle (+) | 0,0000000000 | 0,0000000000 | ✔ |
| 0,5 | Sentinel | -0,1451000000 | -0,1451000000 | ✔ |
| 0,5 | B1 audit-at-commit | -0,0815951220 | -0,0815951220 | ✔ |
| 0,5 | Sentinel -transition uncertainty | -0,1451000000 | -0,1451000000 | ✔ |
| 0,5 | Oracle (+) | 0,0000000000 | 0,0000000000 | ✔ |
| 1 | Sentinel | -0,1219095238 | -0,1219095238 | ✔ |
| 1 | B1 audit-at-commit | -0,0719696970 | -0,0719696970 | ✔ |
| 1 | Sentinel -transition uncertainty | -0,0329619048 | -0,0329619048 | ✔ |
| 1 | Oracle (+) | 0,0000000000 | 0,0000000000 | ✔ |

### 9.2 Table 2 đầy đủ — 15 hệ thống, hai metric, Δ ∈ {4, 8}

`gain` là so với B1 audit-at-commit (dương = tốt hơn B1). `exploit` = V_BR(cross-fit) − V_held-out; đọc mục 9.4 trước khi diễn giải dấu. `clean` = clean-completion %, `FQ/ep` = cách ly sai mỗi episode (mức carrier, O7), `t_lost/ep` = task sạch mất mỗi episode, `audit` = CPU-phút mỗi episode, `delay` = trễ phát hiện.

**ρ = 0**

| Hệ thống | V(L) [CI] | gain L % [CI] | V(harm) [CI] | gain harm % [CI] | exploit L | exploit harm | clean % | FQ/ep | t_lost/ep | audit | delay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 audit-at-commit | 1,236 [1,190; 1,369] | — (cơ sở) | 0,787 [0,735; 0,892] | — (cơ sở) | -0,062 | -0,065 | 90,4 | 0,000 | 0,663 | 40,88 | 4,97 |
| B2 uniform random | 1,956 [1,861; 2,058] | -58,3 [-68,4; -38,2] | 0,811 [0,726; 0,900] | -3,0 [-5,5; +6,5] | -0,077 | -0,034 | 97,3 | 1,544 | 0,190 | 21,41 | 1,26 |
| B3 audit-on-insertion | 3,846 [3,762; 3,968] | -211,2 [-223,8; -183,7] | 0,858 [0,817; 0,947] | -9,0 [-14,2; -3,9] | -0,068 | -0,053 | 100,0 | 4,386 | 0,000 | 11,96 | 0,00 |
| B4 audit-on-retrieval | 1,308 [1,206; 1,425] | -5,9 [-12,6; +5,8] | 0,879 [0,844; 0,953] | -11,7 [-20,8; -4,4] | -0,177 | -0,074 | 100,0 | 0,595 | 0,000 | 17,95 | 1,10 |
| B5 risk-score | 2,011 [1,953; 2,138] | -62,7 [-69,7; -50,4] | 0,792 [0,726; 0,873] | -0,5 [-5,0; +8,1] | -0,148 | -0,062 | 97,4 | 1,679 | 0,177 | 21,96 | 0,97 |
| B6 two-stage | 1,474 [1,382; 1,570] | -19,3 [-27,4; -3,1] | 0,858 [0,799; 0,942] | -9,0 [-14,2; -1,2] | -0,078 | -0,053 | 100,0 | 0,768 | 0,000 | 15,21 | 1,93 |
| cost-greedy | 2,235 [2,092; 2,380] | -80,8 [-87,5; -63,9] | 0,858 [0,784; 0,932] | -9,0 [-12,2; -0,1] | -0,201 | -0,081 | 99,0 | 2,044 | 0,076 | 17,77 | 1,10 |
| SW randomised | 1,746 [1,597; 1,899] | -41,3 [-54,5; -19,6] | 0,783 [0,707; 0,884] | +0,6 [-2,8; +8,6] | +0,034 | -0,094 | 95,0 | 0,977 | 0,346 | 28,53 | 1,95 |
| Oracle (+) | 0,491 [0,383; 0,603] | +60,3 [+53,7; +68,8] | 0,000 [0,000; 0,000] | +100,0 [+100,0; +100,0] | +0,023 | +0,000 | 97,8 | 0,000 | 0,145 | 20,03 | 0,00 |
| Sentinel | 0,956 [0,880; 1,048] | +22,6 [+15,9; +33,5] | 0,821 [0,762; 0,906] | -4,3 [-11,2; +4,8] | -0,152 | -0,065 | 98,6 | 0,078 | 0,093 | 18,60 | 2,12 |
| Sentinel [dhat=oracle] | 0,961 [0,882; 1,051] | +22,3 [+15,8; +33,4] | 0,821 [0,763; 0,906] | -4,3 [-11,4; +4,4] | -0,039 | -0,058 | 98,6 | 0,076 | 0,095 | 18,59 | 2,13 |
| Sentinel -randomization | 0,867 [0,804; 0,980] | +29,9 [+21,2; +40,1] | 0,827 [0,759; 0,935] | -5,1 [-12,3; +4,2] | -0,124 | -0,081 | 99,1 | 0,067 | 0,049 | 18,67 | 2,02 |
| Sentinel -alarm memory | 0,908 [0,860; 0,984] | +26,5 [+21,4; +34,9] | 0,815 [0,771; 0,901] | -3,6 [-11,0; +3,1] | -0,008 | +0,013 | 98,9 | 0,022 | 0,080 | 18,02 | 2,13 |
| Sentinel -benign-drift | 1,080 [1,002; 1,184] | +12,6 [+3,8; +24,8] | 0,821 [0,745; 0,905] | -4,3 [-10,4; +6,1] | -0,108 | -0,068 | 98,7 | 0,357 | 0,088 | 18,62 | 1,65 |
| Sentinel -transition uncertainty | 1,075 [0,976; 1,173] | +13,0 [+6,1; +25,9] | 0,792 [0,701; 0,885] | -0,5 [-7,6; +11,8] | -0,270 | -0,090 | 98,7 | 0,397 | 0,093 | 18,54 | 1,50 |

**ρ = 0,25**

| Hệ thống | V(L) [CI] | gain L % [CI] | V(harm) [CI] | gain harm % [CI] | exploit L | exploit harm | clean % | FQ/ep | t_lost/ep | audit | delay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 audit-at-commit | 1,086 [1,032; 1,279] | — (cơ sở) | 0,646 [0,614; 0,765] | — (cơ sở) | -0,107 | -0,105 | 90,4 | 0,000 | 0,663 | 40,88 | 5,08 |
| B2 uniform random | 1,899 [1,827; 2,001] | -74,9 [-88,1; -45,7] | 0,755 [0,689; 0,839] | -16,8 [-22,7; -0,0] | -0,047 | -0,019 | 97,3 | 1,544 | 0,190 | 21,41 | 1,26 |
| B3 audit-on-insertion | 3,846 [3,762; 3,968] | -254,0 [-275,3; -205,2] | 0,858 [0,817; 0,947] | -32,8 [-42,1; -17,4] | -0,068 | -0,053 | 100,0 | 4,386 | 0,000 | 11,96 | 0,00 |
| B4 audit-on-retrieval | 1,308 [1,206; 1,425] | -20,4 [-24,6; -6,1] | 0,879 [0,844; 0,953] | -36,0 [-44,5; -20,9] | -0,177 | -0,074 | 100,0 | 0,595 | 0,000 | 17,95 | 1,10 |
| B5 risk-score | 1,990 [1,892; 2,122] | -83,2 [-92,3; -59,7] | 0,762 [0,706; 0,820] | -17,9 [-26,5; +2,3] | -0,182 | -0,078 | 97,4 | 1,678 | 0,178 | 21,96 | 0,97 |
| B6 two-stage | 1,474 [1,382; 1,570] | -35,7 [-46,0; -11,1] | 0,858 [0,799; 0,942] | -32,8 [-41,9; -14,3] | -0,078 | -0,053 | 100,0 | 0,768 | 0,000 | 15,21 | 1,93 |
| cost-greedy | 2,216 [2,076; 2,358] | -104,0 [-108,1; -80,6] | 0,840 [0,763; 0,918] | -29,9 [-36,9; -11,7] | -0,182 | -0,096 | 99,0 | 2,044 | 0,076 | 17,77 | 1,10 |
| SW randomised | 1,652 [1,495; 1,834] | -52,1 [-72,4; -21,2] | 0,720 [0,626; 0,833] | -11,4 [-22,8; +7,8] | +0,047 | -0,112 | 95,0 | 0,977 | 0,346 | 28,53 | 1,96 |
| Oracle (+) | 0,491 [0,383; 0,603] | +54,8 [+49,3; +64,3] | 0,000 [0,000; 0,000] | +100,0 [+100,0; +100,0] | +0,023 | +0,000 | 97,8 | 0,000 | 0,145 | 20,03 | 0,00 |
| Sentinel | 0,859 [0,784; 0,953] | +20,9 [+11,7; +37,0] | 0,792 [0,703; 0,905] | -22,6 [-32,3; -3,4] | -0,057 | -0,036 | 98,7 | 0,067 | 0,090 | 19,19 | 2,07 |
| Sentinel [dhat=oracle] | 0,871 [0,799; 0,953] | +19,8 [+11,5; +36,1] | 0,804 [0,711; 0,905] | -24,3 [-32,9; -3,2] | -0,099 | -0,020 | 98,7 | 0,068 | 0,092 | 19,22 | 2,07 |
| Sentinel -randomization | 0,867 [0,810; 0,960] | +20,2 [+12,2; +34,1] | 0,774 [0,713; 0,864] | -19,7 [-28,7; -2,2] | -0,078 | -0,059 | 98,4 | 0,058 | 0,110 | 20,63 | 2,10 |
| Sentinel -alarm memory | 0,876 [0,821; 0,982] | +19,3 [+9,1; +33,0] | 0,810 [0,756; 0,904] | -25,2 [-35,3; -7,4] | -0,126 | -0,087 | 98,7 | 0,024 | 0,083 | 19,80 | 2,05 |
| Sentinel -benign-drift | 0,993 [0,948; 1,079] | +8,6 [-0,1; +23,0] | 0,811 [0,728; 0,912] | -25,5 [-33,6; -6,1] | -0,127 | -0,061 | 98,8 | 0,275 | 0,083 | 18,99 | 1,60 |
| Sentinel -transition uncertainty | 0,859 [0,784; 0,953] | +20,9 [+11,7; +37,0] | 0,792 [0,703; 0,905] | -22,6 [-32,3; -3,4] | -0,057 | -0,036 | 98,7 | 0,067 | 0,090 | 19,19 | 2,07 |

**ρ = 0,5**

| Hệ thống | V(L) [CI] | gain L % [CI] | V(harm) [CI] | gain harm % [CI] | exploit L | exploit harm | clean % | FQ/ep | t_lost/ep | audit | delay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 audit-at-commit | 0,951 [0,910; 1,066] | — (cơ sở) | 0,512 [0,450; 0,618] | — (cơ sở) | -0,118 | -0,082 | 90,4 | 0,000 | 0,663 | 40,88 | 4,90 |
| B2 uniform random | 1,852 [1,789; 1,967] | -94,7 [-109,6; -70,7] | 0,708 [0,633; 0,801] | -38,1 [-52,8; -19,5] | +0,007 | +0,009 | 97,3 | 1,544 | 0,190 | 21,41 | 1,26 |
| B3 audit-on-insertion | 3,846 [3,762; 3,968] | -304,3 [-324,3; -262,1] | 0,858 [0,817; 0,947] | -67,6 [-88,0; -48,7] | -0,068 | -0,053 | 100,0 | 4,386 | 0,000 | 11,96 | 0,00 |
| B4 audit-on-retrieval | 1,308 [1,206; 1,425] | -37,5 [-46,2; -20,9] | 0,879 [0,844; 0,953] | -71,7 [-98,9; -49,5] | -0,177 | -0,074 | 100,0 | 0,595 | 0,000 | 17,95 | 1,10 |
| B5 risk-score | 1,959 [1,875; 2,079] | -105,9 [-118,5; -85,3] | 0,708 [0,633; 0,788] | -38,3 [-53,4; -19,5] | -0,219 | -0,069 | 97,4 | 1,677 | 0,178 | 21,97 | 0,97 |
| B6 two-stage | 1,474 [1,382; 1,570] | -55,0 [-66,7; -32,8] | 0,858 [0,799; 0,942] | -67,6 [-87,6; -47,5] | -0,078 | -0,053 | 100,0 | 0,768 | 0,000 | 15,21 | 1,93 |
| cost-greedy | 2,206 [2,071; 2,343] | -131,9 [-139,6; -109,3] | 0,830 [0,746; 0,915] | -62,1 [-78,5; -40,8] | -0,182 | -0,093 | 99,0 | 2,044 | 0,076 | 17,77 | 1,10 |
| SW randomised | 1,623 [1,461; 1,828] | -70,7 [-91,7; -41,6] | 0,660 [0,530; 0,819] | -28,9 [-42,5; -6,8] | +0,028 | -0,093 | 95,0 | 0,977 | 0,346 | 28,53 | 1,97 |
| Oracle (+) | 0,491 [0,383; 0,603] | +48,4 [+41,2; +59,7] | 0,000 [0,000; 0,000] | +100,0 [+100,0; +100,0] | +0,023 | +0,000 | 97,8 | 0,000 | 0,145 | 20,03 | 0,00 |
| Sentinel | 0,818 [0,774; 0,910] | +14,0 [+3,6; +23,8] | 0,750 [0,678; 0,837] | -46,4 [-62,2; -25,9] | -0,151 | -0,145 | 99,2 | 0,164 | 0,058 | 18,21 | 1,83 |
| Sentinel [dhat=oracle] | 0,818 [0,769; 0,909] | +14,0 [+3,6; +24,7] | 0,750 [0,670; 0,837] | -46,4 [-61,6; -25,7] | -0,078 | -0,051 | 99,2 | 0,164 | 0,058 | 18,21 | 1,83 |
| Sentinel -randomization | 0,833 [0,804; 0,964] | +12,4 [+0,2; +22,7] | 0,744 [0,709; 0,842] | -45,3 [-73,5; -23,5] | -0,052 | -0,135 | 99,2 | 0,213 | 0,050 | 18,26 | 1,68 |
| Sentinel -alarm memory | 0,824 [0,817; 0,926] | +13,3 [+2,8; +20,4] | 0,756 [0,717; 0,856] | -47,6 [-70,4; -31,4] | -0,051 | -0,050 | 98,6 | 0,072 | 0,092 | 19,48 | 1,63 |
| Sentinel -benign-drift | 1,035 [0,960; 1,181] | -8,9 [-24,9; +6,0] | 0,780 [0,693; 0,885] | -52,2 [-68,2; -32,6] | -0,044 | -0,045 | 99,0 | 0,509 | 0,066 | 18,07 | 1,36 |
| Sentinel -transition uncertainty | 0,818 [0,774; 0,910] | +14,0 [+3,6; +23,8] | 0,750 [0,678; 0,837] | -46,4 [-62,2; -25,9] | -0,151 | -0,145 | 99,2 | 0,164 | 0,058 | 18,21 | 1,83 |

**ρ = 1**

| Hệ thống | V(L) [CI] | gain L % [CI] | V(harm) [CI] | gain harm % [CI] | exploit L | exploit harm | clean % | FQ/ep | t_lost/ep | audit | delay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 audit-at-commit | 0,604 [0,473; 0,769] | — (cơ sở) | 0,197 [0,138; 0,264] | — (cơ sở) | +0,000 | -0,072 | 90,4 | 0,000 | 0,663 | 40,88 | 5,05 |
| B2 uniform random | 1,755 [1,672; 1,878] | -190,7 [-275,2; -131,9] | 0,565 [0,549; 0,653] | -187,1 [-357,6; -122,5] | -0,074 | +0,013 | 97,3 | 1,544 | 0,190 | 21,41 | 1,26 |
| B3 audit-on-insertion | 3,846 [3,762; 3,968] | -536,9 [-711,6; -409,5] | 0,858 [0,817; 0,947] | -335,8 [-574,1; -222,7] | -0,068 | -0,053 | 100,0 | 4,386 | 0,000 | 11,96 | 0,00 |
| B4 audit-on-retrieval | 1,308 [1,206; 1,425] | -116,7 [-172,6; -73,9] | 0,879 [0,844; 0,953] | -346,4 [-576,9; -233,0] | -0,177 | -0,074 | 100,0 | 0,595 | 0,000 | 17,95 | 1,10 |
| B5 risk-score | 1,865 [1,797; 2,019] | -208,9 [-296,8; -154,8] | 0,661 [0,587; 0,748] | -235,4 [-413,6; -128,6] | -0,192 | -0,031 | 97,4 | 1,677 | 0,178 | 21,97 | 0,97 |
| B6 two-stage | 1,474 [1,382; 1,570] | -144,2 [-220,6; -85,3] | 0,858 [0,799; 0,942] | -335,8 [-563,8; -217,3] | -0,078 | -0,053 | 100,0 | 0,768 | 0,000 | 15,21 | 1,93 |
| cost-greedy | 2,178 [2,057; 2,311] | -260,7 [-347,3; -192,4] | 0,802 [0,725; 0,881] | -307,1 [-509,2; -188,3] | -0,167 | -0,099 | 99,0 | 2,044 | 0,076 | 17,77 | 1,09 |
| SW randomised | 1,439 [1,302; 1,598] | -138,4 [-203,4; -89,0] | 0,476 [0,417; 0,586] | -141,8 [-314,0; -68,1] | +0,015 | -0,057 | 95,0 | 0,977 | 0,346 | 28,53 | 2,01 |
| Oracle (+) | 0,491 [0,383; 0,603] | +18,7 [+14,1; +27,9] | 0,000 [0,000; 0,000] | +100,0 [+100,0; +100,0] | +0,023 | +0,000 | 97,8 | 0,000 | 0,145 | 20,03 | 0,00 |
| Sentinel | 0,889 [0,837; 0,943] | -47,2 [-90,8; -13,0] | 0,774 [0,692; 0,854] | -292,9 [-483,2; -178,9] | -0,181 | -0,122 | 98,8 | 0,185 | 0,076 | 18,01 | 1,83 |
| Sentinel [dhat=oracle] | 0,877 [0,822; 0,940] | -45,2 [-90,2; -10,5] | 0,762 [0,673; 0,850] | -286,8 [-481,2; -170,9] | -0,157 | -0,097 | 98,8 | 0,179 | 0,077 | 18,05 | 1,82 |
| Sentinel -randomization | 0,893 [0,829; 0,976] | -47,9 [-91,4; -13,8] | 0,762 [0,674; 0,856] | -286,8 [-490,1; -167,3] | -0,173 | -0,102 | 99,1 | 0,224 | 0,057 | 18,25 | 1,74 |
| Sentinel -alarm memory | 0,845 [0,808; 0,960] | -39,9 [-92,5; -9,2] | 0,774 [0,709; 0,871] | -292,9 [-502,7; -180,6] | -0,072 | -0,056 | 98,4 | 0,094 | 0,108 | 19,12 | 1,63 |
| Sentinel -benign-drift | 1,007 [0,933; 1,135] | -66,8 [-130,8; -26,0] | 0,744 [0,658; 0,831] | -277,7 [-468,2; -164,3] | -0,113 | -0,019 | 99,0 | 0,558 | 0,062 | 18,00 | 1,43 |
| Sentinel -transition uncertainty | 0,839 [0,787; 0,918] | -38,9 [-88,2; -6,4] | 0,780 [0,702; 0,877] | -295,9 [-503,2; -181,5] | -0,015 | -0,033 | 98,9 | 0,093 | 0,075 | 18,19 | 2,24 |

**Còn TBD trong Table 2 (N3):**

- **B7** — không có bản ghi B7 trong bất kỳ block nào; T21 chưa cài. Cả dòng B7 và cột `regret vs B7` của mọi hệ đều TBD.
- **Độ trung thực bảng-vs-rollout** — cần thế giới headline-rollout, lượt này không có.
- **Toàn bộ số eval (P5)** — chưa có lượt eval nào; `frozen/V3-GATE4.json` chưa được người dùng ký. Mọi con số ở đây là **dev**.

### 9.3 Table 3 — ablation, có cả cánh −transition

`V_Sent − V` là hiệu tuyệt đối do `gain_ci(base="Sentinel", cand=biến_thể).abs_diff`: **dương nghĩa là biến thể có V thấp hơn** (tốt hơn bản đầy đủ), âm nghĩa là bỏ thành phần đó làm xấu đi.

**ρ = 0**

| Biến thể | V(L) | V_Sent − V(L) | gain L % [CI] | V(harm) | V_Sent − V(harm) | gain harm % [CI] | exploit L | exploit harm | FQ/ep | clean % |
|---|---|---|---|---|---|---|---|---|---|---|
| Sentinel | 0,956 | — | +22,6 [+15,9; +33,5] | 0,821 | — | -4,3 [-11,2; +4,8] | -0,152 | -0,065 | 0,078 | 98,6 |
| Sentinel [dhat=oracle] | 0,961 | -0,004 | +22,3 [+15,8; +33,4] | 0,821 | +0,000 | -4,3 [-11,4; +4,4] | -0,039 | -0,058 | 0,076 | 98,6 |
| Sentinel -randomization | 0,867 | +0,090 | +29,9 [+21,2; +40,1] | 0,827 | -0,006 | -5,1 [-12,3; +4,2] | -0,124 | -0,081 | 0,067 | 99,1 |
| Sentinel -alarm memory | 0,908 | +0,048 | +26,5 [+21,4; +34,9] | 0,815 | +0,006 | -3,6 [-11,0; +3,1] | -0,008 | +0,013 | 0,022 | 98,9 |
| Sentinel -benign-drift | 1,080 | -0,124 | +12,6 [+3,8; +24,8] | 0,821 | +0,000 | -4,3 [-10,4; +6,1] | -0,108 | -0,068 | 0,357 | 98,7 |
| Sentinel -transition uncertainty | 1,075 | -0,119 | +13,0 [+6,1; +25,9] | 0,792 | +0,030 | -0,5 [-7,6; +11,8] | -0,270 | -0,090 | 0,397 | 98,7 |

**ρ = 0,25**

| Biến thể | V(L) | V_Sent − V(L) | gain L % [CI] | V(harm) | V_Sent − V(harm) | gain harm % [CI] | exploit L | exploit harm | FQ/ep | clean % |
|---|---|---|---|---|---|---|---|---|---|---|
| Sentinel | 0,859 | — | +20,9 [+11,7; +37,0] | 0,792 | — | -22,6 [-32,3; -3,4] | -0,057 | -0,036 | 0,067 | 98,7 |
| Sentinel [dhat=oracle] | 0,871 | -0,012 | +19,8 [+11,5; +36,1] | 0,804 | -0,011 | -24,3 [-32,9; -3,2] | -0,099 | -0,020 | 0,068 | 98,7 |
| Sentinel -randomization | 0,867 | -0,008 | +20,2 [+12,2; +34,1] | 0,774 | +0,019 | -19,7 [-28,7; -2,2] | -0,078 | -0,059 | 0,058 | 98,4 |
| Sentinel -alarm memory | 0,876 | -0,017 | +19,3 [+9,1; +33,0] | 0,810 | -0,017 | -25,2 [-35,3; -7,4] | -0,126 | -0,087 | 0,024 | 98,7 |
| Sentinel -benign-drift | 0,993 | -0,134 | +8,6 [-0,1; +23,0] | 0,811 | -0,019 | -25,5 [-33,6; -6,1] | -0,127 | -0,061 | 0,275 | 98,8 |
| Sentinel -transition uncertainty | 0,859 | +0,000 | +20,9 [+11,7; +37,0] | 0,792 | +0,000 | -22,6 [-32,3; -3,4] | -0,057 | -0,036 | 0,067 | 98,7 |

**ρ = 0,5**

| Biến thể | V(L) | V_Sent − V(L) | gain L % [CI] | V(harm) | V_Sent − V(harm) | gain harm % [CI] | exploit L | exploit harm | FQ/ep | clean % |
|---|---|---|---|---|---|---|---|---|---|---|
| Sentinel | 0,818 | — | +14,0 [+3,6; +23,8] | 0,750 | — | -46,4 [-62,2; -25,9] | -0,151 | -0,145 | 0,164 | 99,2 |
| Sentinel [dhat=oracle] | 0,818 | +0,000 | +14,0 [+3,6; +24,7] | 0,750 | +0,000 | -46,4 [-61,6; -25,7] | -0,078 | -0,051 | 0,164 | 99,2 |
| Sentinel -randomization | 0,833 | -0,015 | +12,4 [+0,2; +22,7] | 0,744 | +0,006 | -45,3 [-73,5; -23,5] | -0,052 | -0,135 | 0,213 | 99,2 |
| Sentinel -alarm memory | 0,824 | -0,007 | +13,3 [+2,8; +20,4] | 0,756 | -0,006 | -47,6 [-70,4; -31,4] | -0,051 | -0,050 | 0,072 | 98,6 |
| Sentinel -benign-drift | 1,035 | -0,218 | -8,9 [-24,9; +6,0] | 0,780 | -0,030 | -52,2 [-68,2; -32,6] | -0,044 | -0,045 | 0,509 | 99,0 |
| Sentinel -transition uncertainty | 0,818 | +0,000 | +14,0 [+3,6; +23,8] | 0,750 | +0,000 | -46,4 [-62,2; -25,9] | -0,151 | -0,145 | 0,164 | 99,2 |

**ρ = 1**

| Biến thể | V(L) | V_Sent − V(L) | gain L % [CI] | V(harm) | V_Sent − V(harm) | gain harm % [CI] | exploit L | exploit harm | FQ/ep | clean % |
|---|---|---|---|---|---|---|---|---|---|---|
| Sentinel | 0,889 | — | -47,2 [-90,8; -13,0] | 0,774 | — | -292,9 [-483,2; -178,9] | -0,181 | -0,122 | 0,185 | 98,8 |
| Sentinel [dhat=oracle] | 0,877 | +0,012 | -45,2 [-90,2; -10,5] | 0,762 | +0,012 | -286,8 [-481,2; -170,9] | -0,157 | -0,097 | 0,179 | 98,8 |
| Sentinel -randomization | 0,893 | -0,004 | -47,9 [-91,4; -13,8] | 0,762 | +0,012 | -286,8 [-490,1; -167,3] | -0,173 | -0,102 | 0,224 | 99,1 |
| Sentinel -alarm memory | 0,845 | +0,044 | -39,9 [-92,5; -9,2] | 0,774 | +0,000 | -292,9 [-502,7; -180,6] | -0,072 | -0,056 | 0,094 | 98,4 |
| Sentinel -benign-drift | 1,007 | -0,118 | -66,8 [-130,8; -26,0] | 0,744 | +0,030 | -277,7 [-468,2; -164,3] | -0,113 | -0,019 | 0,558 | 99,0 |
| Sentinel -transition uncertainty | 0,839 | +0,050 | -38,9 [-88,2; -6,4] | 0,780 | -0,006 | -295,9 [-503,2; -181,5] | -0,015 | -0,033 | 0,093 | 98,9 |

#### Cánh `Sentinel −transition uncertainty` so với Sentinel đầy đủ

| ρ | V(L) Sent | V(L) −trans | V(harm) Sent | V(harm) −trans | gain L Sent | gain L −trans | gain harm Sent | gain harm −trans | FQ/ep Sent | FQ/ep −trans |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0,956 | 1,075 | 0,821 | 0,792 | +22,6 | +13,0 | -4,3 | -0,5 | 0,078 | 0,397 |
| 0,25 | 0,859 | 0,859 | 0,792 | 0,792 | +20,9 | +20,9 | -22,6 | -22,6 | 0,067 | 0,067 |
| 0,5 | 0,818 | 0,818 | 0,750 | 0,750 | +14,0 | +14,0 | -46,4 | -46,4 | 0,164 | 0,164 |
| 1 | 0,889 | 0,839 | 0,774 | 0,780 | -47,2 | -38,9 | -292,9 | -295,9 | 0,185 | 0,093 |

**Phát hiện đáng chú ý — và đã truy tới bản ghi.** Ở **ρ = 0,25 và ρ = 0,5 cánh −transition cho số y hệt bản đầy đủ tới từng chữ số**, kể cả exploitability. Đã kiểm trực tiếp trên 3.901 episode mỗi ρ (khớp theo (ρ, Δ, cột, wf, seed)):

| ρ | episode khớp | (harm, fq, t_lost, spent) giống nhau | `decision_log_sha256` giống nhau |
|---|---|---|---|
| 0 | 3.901 | **2.051** | 0 |
| 0,25 | 3.901 | **3.901** | 0 |
| 0,5 | 3.901 | **3.901** | 0 |
| 1 | 3.901 | **2.636** | 0 |

Tức **không phải trùng bản ghi**: log quyết định khác nhau ở **100%** episode ở cả 4 ρ — chính sách thật sự hành xử khác (chuỗi audit, giá trị belief khác). Nhưng ở ρ = 0,25 và ρ = 0,5 nó **về đích ở cùng kết quả** trên mọi episode. Đọc đúng: **mô hình hoá bất định chuyển trạng thái là trung tính về kết quả ở hai ô giữa**, và chỉ có tác dụng ở hai đầu:

- **ρ = 0**: bỏ nó **làm xấu đi** — V(L) 0,956 → 1,075, gain L +22,6% → +13,0%, FQ/ep 0,078 → 0,397 (gấp 5 lần). Đây là ô nó gánh nhiều nhất.
- **ρ = 1**: theo **L** bỏ nó **làm tốt hơn** — V(L) 0,889 → 0,839, gain L −47,2% → −38,9%, FQ/ep 0,185 → 0,093. Nhưng theo **harm** thì **xấu hơn một chút** (V 0,774 → 0,780, gain −292,9% → −295,9%). Hai metric **không cùng chiều** ở ô này, nên phát biểu được chỉ là: ở ρ = 1 mô hình chuyển trạng thái đang **mua harm bằng FQ** — bỏ nó cắt FQ đi một nửa mà harm gần như không đổi, nên L tốt lên. Không đọc được thành "nên bỏ" khi headline metric chưa chốt (mục 7, điểm 1).

Kết luận cho ablation: cánh −transition **không** là cánh mạnh nhất. Xếp theo mức gánh tải ở ρ = 0,5 (theo L): `−benign-drift` (+14,0% → −8,9%) ≫ `−randomization` (+12,4%) ≈ `−alarm memory` (+13,3%) ≈ `−transition uncertainty` (+14,0%, không đổi). **Mô hình hoá drift lành vẫn là thành phần chịu tải chính**, như mục 5 đã nói; −transition chỉ hiện ra ở ρ = 0 và ρ = 1.

### 9.4 Dấu của exploitability: phải đọc kèm bộ estimator

Exploitability **âm ở gần như mọi hệ và mọi ρ** (xem Table 2). Điều đó **không** có nghĩa attacker best-response yếu hơn lớp held-out. Nguyên nhân là hai vế không cùng bộ estimator:

- **V_held-out** là **max qua 7 cột** held-out → bị thổi lên bởi chính phép chọn cột.
- **V_BR** là **cross-fit** (D27): chọn placement trên seed lẻ, cho điểm trên seed chẵn, rồi đổi vai. `metrics_v2.crossfit_value` cố ý làm vậy vì lấy max trên cùng seed đã thổi V lên (pilot 2b: B1 0,25 naive so với 0,125 cross-fit, giải tích 0,1275).

Để thấy rõ, cùng một hàm còn trả về giá trị **naive** (max qua placement, không cross-fit):

| ρ | Hệ thống | metric | V_BR cross-fit (Δ4 / Δ8) | V_BR naive (Δ4 / Δ8) | V_held-out | exploit cross-fit | exploit naive |
|---|---|---|---|---|---|---|---|
| 0 | Sentinel | L | 0,8042 / 0,6152 | 1,2403 / 1,1134 | 0,9564 | -0,152 | +0,284 |
| 0 | Sentinel | harm | 0,7562 / 0,6389 | 0,9747 / 0,8333 | 0,8214 | -0,065 | +0,153 |
| 0 | B1 audit-at-commit | L | 0,9904 / 1,1736 | 1,4141 / 1,3553 | 1,2358 | -0,062 | +0,178 |
| 0 | B1 audit-at-commit | harm | 0,6410 / 0,7222 | 0,9394 / 0,8421 | 0,7874 | -0,065 | +0,152 |
| 0,25 | Sentinel | L | 0,8021 / 0,7466 | 1,2626 / 1,1819 | 0,8589 | -0,057 | +0,404 |
| 0,25 | Sentinel | harm | 0,7564 / 0,7361 | 0,9747 / 0,8772 | 0,7925 | -0,036 | +0,182 |
| 0,25 | B1 audit-at-commit | L | 0,8397 / 0,9792 | 1,3056 / 1,2632 | 1,0862 | -0,107 | +0,219 |
| 0,25 | B1 audit-at-commit | harm | 0,5127 / 0,5417 | 0,8737 / 0,7632 | 0,6463 | -0,105 | +0,227 |
| 0,5 | Sentinel | L | 0,6665 / 0,4817 | 1,3551 / 1,2505 | 0,8177 | -0,151 | +0,537 |
| 0,5 | Sentinel | harm | 0,6049 / 0,5417 | 0,9747 / 0,8421 | 0,7500 | -0,145 | +0,225 |
| 0,5 | B1 audit-at-commit | L | 0,7219 / 0,8333 | 1,1616 / 1,1447 | 0,9512 | -0,118 | +0,210 |
| 0,5 | B1 audit-at-commit | harm | 0,3889 / 0,4306 | 0,7576 / 0,6491 | 0,5122 | -0,082 | +0,245 |
| 1 | Sentinel | L | 0,7075 / 0,6056 | 1,3598 / 1,2061 | 0,8888 | -0,181 | +0,471 |
| 1 | Sentinel | harm | 0,6519 / 0,4730 | 0,9747 / 0,7807 | 0,7738 | -0,122 | +0,201 |
| 1 | B1 audit-at-commit | L | 0,4469 / 0,6042 | 0,8056 / 0,8026 | 0,6038 | +0,000 | +0,202 |
| 1 | B1 audit-at-commit | harm | 0,1173 / 0,1250 | 0,3838 / 0,2982 | 0,1970 | -0,072 | +0,187 |

Dấu **lật theo estimator**: ví dụ Sentinel ở ρ = 0,5 theo harm, exploitability là **−0,145** khi cross-fit và **+0,225** khi naive. Vì D27 khai cross-fit là bản chính, cột `exploit` của Table 2 lấy cross-fit, và **naive được in bên cạnh chứ không thay chỗ** (R6). Phát biểu trung thực nhất đọc được từ lượt này là: **cột held-out xấu nhất đã khó bằng hoặc hơn attacker best-response ước lượng không chệch**, nên số held-out của Table 2 **không** đang đánh giá thấp đối thủ. Chưa được phát biểu là "chính sách không thể bị khai thác": đó là câu cần V_BR và V_held-out trên cùng một bộ estimator, và cần lượt eval P5 — **giữ TBD**.

### 9.5 Theo từng Δ — Sentinel và cánh −transition, hai metric

gain % so với B1. Δ ∈ {0, 1, 2} **không** có số exploitability: block `br` chỉ chạy ở Δ ∈ {4, 8} (TBD, N3).

**Theo L**

| ρ | Hệ thống | Δ=0 | Δ=1 | Δ=2 | Δ=4 | Δ=8 |
|---|---|---|---|---|---|---|
| 0 | Sentinel | +20,2 | +10,4 | +14,3 | +18,8 | +22,6 |
| 0 | Sentinel -transition uncertainty | +6,8 | +1,6 | -1,0 | +4,5 | +26,7 |
| 0,25 | Sentinel | +8,9 | +5,0 | +7,8 | +11,0 | +23,0 |
| 0,25 | Sentinel -transition uncertainty | +8,9 | +5,0 | +7,8 | +11,0 | +23,0 |
| 0,5 | Sentinel | -14,5 | -18,1 | -15,1 | +1,9 | +24,9 |
| 0,5 | Sentinel -transition uncertainty | -14,5 | -18,1 | -15,1 | +1,9 | +24,9 |
| 1 | Sentinel | -56,5 | -65,0 | -77,4 | -54,4 | -27,8 |
| 1 | Sentinel -transition uncertainty | -52,2 | -60,7 | -67,7 | -45,7 | -20,7 |

**Theo harm**

| ρ | Hệ thống | Δ=0 | Δ=1 | Δ=2 | Δ=4 | Δ=8 |
|---|---|---|---|---|---|---|
| 0 | Sentinel | -4,9 | -19,7 | -12,5 | -4,3 | -2,4 |
| 0 | Sentinel -transition uncertainty | -4,9 | -18,0 | -11,8 | -0,5 | +16,9 |
| 0,25 | Sentinel | -31,7 | -29,8 | -34,2 | -27,1 | -22,6 |
| 0,25 | Sentinel -transition uncertainty | -31,7 | -29,8 | -34,2 | -27,1 | -22,6 |
| 0,5 | Sentinel | -75,4 | -94,2 | -73,2 | -61,4 | -17,9 |
| 0,5 | Sentinel -transition uncertainty | -75,4 | -94,2 | -73,2 | -61,4 | -17,9 |
| 1 | Sentinel | -267,3 | -322,6 | -419,1 | -292,9 | -306,2 |
| 1 | Sentinel -transition uncertainty | -267,3 | -326,8 | -419,1 | -295,9 | -337,5 |

Hai chiều của mục 4 giữ nguyên, nhưng phát biểu chính xác hơn khi đọc đủ 5 Δ: **gain tăng đơn điệu trên vùng Δ ∈ {2, 4, 8}** — theo L ở **cả 4 ρ** và cho cả cánh −transition, theo harm ở ρ ≤ 0,5 (ở ρ = 1 theo harm nó tụt lại ở Δ = 8: −292,9% → −306,2%). Trên vùng Δ ∈ {0, 1} thì **không** đơn điệu (ρ = 0 theo L: +20,2% ở Δ = 0 rụng xuống +10,4% ở Δ = 1), nên câu "gain không giảm theo Δ" của mục 4 phải đọc là **từ Δ ≥ 2**. Chiều theo ρ cũng không đơn điệu: ở Δ = 8 theo L là +22,6 → +23,0 → +24,9 → −27,8 — phát biểu đúng là **gain sập khi ρ = 1**, không phải giảm dần theo ρ. Riêng theo harm ở ρ = 0, cánh −transition lật dấu ở Δ = 8 (+16,9% so với −2,4% của bản đầy đủ) — nhưng theo L cùng ô nó vẫn thấp hơn (+26,7% so với +22,6%), nên **không** đọc được thành "bỏ transition thì tốt hơn": hai metric không cùng chiều ở đó.

### 9.6 Ô nào của paper lấp được sau lượt này

Lượt này **không sửa paper**; đây chỉ là bản đồ ô lấp được (`\tbd` trong `HCMUT/paper-v3/sections/`).

**Lấp được ngay — cột `Exploit.` của `tab:main`** (`sections/results.tex`), cột `\tbd` thứ 5 của mỗi dòng. Giá trị lấy từ cột `exploit harm` của Table 2 mục 9.2 (cross-fit, D27) — **phải kèm chú thích của mục 9.4 về bộ estimator**:

| Panel | ρ | Dòng `results.tex` | Số hệ lấp được |
|---|---|---|---|
| B | 0 | 47–55 | 9 / 10 (B7 dòng 56 giữ `\tbd`) |
| C | 0,25 | 59–67 | 9 / 10 (B7 dòng 68 giữ `\tbd`) |
| D | 0,5 | 71–79 | 9 / 10 (B7 dòng 80 giữ `\tbd`) |
| E | 1 | 83–91 | 9 / 10 (B7 dòng 92 giữ `\tbd`) |

Cụ thể theo panel, thứ tự dòng B1 → B2 → B3 → B4 → B5 → B6 → cost-greedy → SW → \Sent{} (dòng B7 giữ `\tbd`):

| ρ | B1 | B2 | B3 | B4 | B5 | B6 | c-greedy | SW | Sentinel |
|---|---|---|---|---|---|---|---|---|---|
| 0 | -0,065 | -0,034 | -0,053 | -0,074 | -0,062 | -0,053 | -0,081 | -0,094 | -0,065 |
| 0,25 | -0,105 | -0,019 | -0,053 | -0,074 | -0,078 | -0,053 | -0,096 | -0,112 | -0,036 |
| 0,5 | -0,082 | +0,009 | -0,053 | -0,074 | -0,069 | -0,053 | -0,093 | -0,093 | -0,145 |
| 1 | -0,072 | +0,013 | -0,053 | -0,074 | -0,031 | -0,053 | -0,099 | -0,057 | -0,122 |

**Lấp được ngay — dòng `$-$ transition uncertainty (nominal kernel)` của `tab:ablations`** (`sections/results.tex:111`), 4 ô `\tbd` "Measured harm, by ρ":

| ô | ρ = 0 | ρ = 0,25 | ρ = 0,5 | ρ = 1 |
|---|---|---|---|---|
| `− transition uncertainty` V(harm) | 0,792 | 0,792 | 0,750 | 0,780 |

Bốn dòng ablation còn lại của `tab:ablations` (dòng 108–110, 112) cũng lấp được từ mục 9.3; dòng chú thích `results.tex:114–115` ("Measured false quarantine, exploitability and 'exercised' per variant and ρ") lấp được phần **false quarantine** và **exploitability** từ Table 3, còn **"exercised"** thì **chưa** — lượt này không đo đại lượng đó (TBD, N3).

**Lấp được ngay — hai ô văn xuôi về exploitability:**

- `results.tex:235` — "exploitability is \TBD{} (H9, H10)": lấp bằng bảng exploitability 9.2 **kèm nguyên đoạn 9.4**. Không được lấp bằng một con số trần: dấu của nó lật theo bộ estimator.
- `results.tex:276` — "\Sent{}'s exploitability \TBD{} (draft …)": như trên; ở đây draft chiếu 0,09, lượt này đo **âm** ở mọi ρ theo cross-fit, nên **không** so trực tiếp với 0,09 mà phải nói rõ hai bên khác bộ estimator.

**Vẫn TBD, có lý do:**

- `results.tex` dòng 56 / 68 / 80 / 92 — **B7 Exact minimax**: T21 chưa cài, không có bản ghi B7 ở bất kỳ block nào. Kéo theo `results.tex:221` (regret) cũng TBD.
- `results.tex:124–127` — đối chứng, số episode infeasible / bị loại, cổng AUC benign: cần đếm từ log lượt chạy, không nằm trong bản ghi episode.
- `results.tex:267` — độ trung thực bảng-vs-rollout: cần thế giới headline-rollout.
- `results.tex:291` — "effect of removing …" cho ô **không được thực thi** (*not exercised*): lượt này không đo cờ đó.
- `discussion.tex:14, 21, 25, 26, 30, 36`, `conclusion.tex:31`, `abstract.tex:46`, `theory.tex:300` (H7), `approach.tex:116, 155` — phần lớn cần **lượt eval P5** hoặc H7/H8/H11/H14 chưa chạy.
- **Mọi ô eval (P5)**: chưa có lượt eval; `frozen/V3-GATE4.json` chưa được người dùng ký. Không ô nào của paper được lấp bằng số **dev** mà không ghi rõ là dev.

**Số máy đọc được:** `spikes/v3-run/table2_3_full.json` (không commit — `spikes/` trong `.gitignore`, D33).
