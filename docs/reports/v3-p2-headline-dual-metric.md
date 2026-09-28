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

## 10. H-verdict từ các block còn lại (H18, H19, H20, thế giới độ nhạy)

Mục này **bổ sung** mục 0–9: nó chấm bảng điểm H1–H20 (`v3/scorecard.py`) trên **các block còn lại** của lượt dev — ngân sách (H18), trục K_d (H19), cột attacker chọn Δ (H20), sáu thế giới độ nhạy và khối hai carrier có hạt — và đọc **cả hai metric** như tiền đăng ký `docs/preregistration/TIEN-DANG-KY-metric-headline-V.md` yêu cầu (**L của Định nghĩa 1 là headline, V = harm in kèm**). Không lượt mô phỏng nào được chạy lại; không metric, CI hay luật nào được viết lại.

### 10.0 Xuất xứ và cách đọc

| Khối | Tệp | sha256 | Số dòng | Nội dung đọc được |
|---|---|---|---|---|
| h18 | `dev-headline-rest/h18.jsonl` | `e76d222e88fa…` | 81.918 | B1 / B2 / Sentinel; **chỉ** 2×B_min, 1×B_min, 0,5×B_min; ρ ∈ {0; 0,25; 0,5} |
| h18-br | `dev-headline-rest-br/h18-br.jsonl` | `74bf548f9fdc…` | 212.832 | cột BR, **chỉ** mức 2×B_min |
| kd | `dev-headline-rest/kd.jsonl` | `16d19cdb997d…` | 62.416 | B1 + Sentinel, K_d ∈ {1, 3}, mọi Δ, mọi ρ |
| kd-br | `dev-headline-rest-br/kd-br.jsonl` | `7556c0793ec5…` | 107.456 | cột BR, K_d ∈ {1, 3}, Δ ∈ {4, 8} |
| attacker-delta | `dev-headline-rest/attacker-delta.jsonl` | `fec41c53e1e9…` | 849.312 | **chỉ lớp Sentinel** (6 hệ), cột BR, Δ = `attacker` |
| sens:* (6) | `dev-headline-rest/sens_*.jsonl` | `xem records.sha256` | 234.060 mỗi thế giới | 15 hệ, 7 cột held-out, mọi Δ, mọi ρ |
| sens-br:* (5) | `dev-headline-rest-br/sens-br_*.jsonl` | `xem records.sha256` | 53.728 / 107.456 | **chỉ B1 + Sentinel**, cột BR, Δ ∈ {4, 8} |
| sens-attacker-delta:reversible | `dev-headline-rest-br/sens-attacker-delta_reversible.jsonl` | `a9994b3b8090…` | 141.552 | **chỉ Sentinel**, cột BR, Δ = `attacker` |
| seed2-pairs | `dev-headline-rest/seed2-pairs.jsonl` | `59c425a9ced7…` | 80.592 | B1 + Sentinel, cột BR, Δ ∈ {4, 8}, thế giới hai carrier có hạt |
| main (đọc lại) | `dev-headline-main/main.jsonl` | `e1db94d590f3…` | 218.456 | **mức b1** của H18 và ô K_d = 2 của H19 (xem lệch dưới đây) |

**Cách tính (không viết lại gì).** `v3/metrics.table`, `boot_values`, `interval`, `p_value`, `gain_ci`, `h18_miss_change` và `v3/scorecard.Estimate` / `score_all` / `rule_*` nguyên bản; bootstrap wild cluster (Webb) theo họ repo, N = 10.000, α = 0,05, re-max qua cột trong từng lần rút, một bộ rút họ dùng chung cho mọi hệ của cùng một lời gọi.

- **V(harm)**: `field="harm"`. **V(L)**: gắn `r["loss"] = runner.loss_of(r)` rồi `field="loss"`.
- **gain vs B1 theo L**: dùng **chính** `metrics.gain_ci` (hàm cứng `field="harm"`) sau khi **đặt L vào đúng trường mà `gain_ci` cho điểm** — đây là đổi nhãn trường được cho điểm, không phải bản sao hàm. Đã kiểm: `table(..., field="loss").value` và đường đổi nhãn cho **cùng một float** (0,8981, so sánh `==`).
- **V_BR**: `metrics_v2.crossfit_value` (D27) gọi **theo từng workflow**, các giá trị cross-fit đó xếp thành một `metrics.Table` một cột rồi đưa qua đúng bootstrap họ của module này; điểm của bảng bằng đúng `crossfit_value` trên toàn bộ hàng. Giá trị **naive** in kèm (R6, mục 9.4): dấu của exploitability lật theo bộ estimator.
- **Họ BH**: `score_all` chạy **một lần cho mỗi (metric, ρ)** — `HEAD` của khung ghi "each rho", nên mỗi ρ là một thể hiện riêng của cùng một check; họ D của một lần chạy gồm các check D có estimate ở ρ đó (ở lượt này m = 2: H18 và H19). `rules_digest` = `21b8c093254a…`.

**Lệch phải khai (N3):**

1. **Khối `h18` không có mức b1.** `grid.py` chỉ phát sinh unit b1 (không price-only) cho `BlockSchedule` — hệ duy nhất của `H18_POLICIES` không nằm trong `SYSTEMS` — còn B1 / B2 / Sentinel ở b1 thuộc khối `main`. Lượt này chạy 15 hệ, **không có `BlockSchedule`**, nên khối `h18` **rỗng ở b1**. `H18_CRITERION` lại khai `fixed_level = "b1"`. Vì vậy mức b1 được đọc từ `dev-headline-main/main.jsonl` (cùng `grid_digest` `acbe9bdc48fd`, khác manifest — đúng cảnh báo xuyên-lượt của mục 9.0), và **biên (frontier) chỉ lấy trên 3 trong 4 hệ H18**.
2. **`h18-br` chỉ có mức 2×B_min** (luật `attackers.br_systems` cho ô ngân sách), nên không có exploitability ở b1 hay ở các mức B_min thấp hơn.
3. **ρ = 1 bị loại khỏi khối `h18`** ở mọi mức ≠ b1 (`_bmin_hole` → `FLAG_COMMIT_SUFFICES`): khai trước, không phải lỗi.
4. **O15**: các thế giới độ nhạy và K_d ≠ 2 **cố ý dùng lại bảng dòng 5 của thế giới chính** (misspecification đã khai). Mọi số Sentinel ở mục 10.2 và 10.4 phải đọc kèm điều đó: chúng đo một chính sách bị đặt lệch bảng, không phải một chính sách được tinh chỉnh lại cho thế giới đó.
5. **Bộ nhớ.** Mỗi tệp được **stream từng dòng** một lần, `json.loads` rồi chiếu ngay xuống 21 trường mà metric đọc (`policy, wf, repo, seed, split, attack, delta, harm, fq, t_lost, placement, sigma, H, missed_before_sigma` + 6 trường ô + `loss`), chuỗi `sys.intern`; các trường nặng (`c_traj`, `audits`, `quarantines`, `world`, `decision_log_sha256`) **không bao giờ** vào bộ nhớ. Không lúc nào có cả tệp trong RAM. **Đỉnh RSS 1,75 GB**, ở bước H20 (khối `attacker-delta`: 849.312 bản ghi đã chiếu cùng lúc trong RAM); bước chiếu thì O(1).

### 10.1 H18 — hướng của ngân sách theo Δ (khai báo 27/09)

Thống kê chính của H18 là **tỉ lệ bỏ lọt trước σ** (`missed_before_sigma`), nên nó **không phụ thuộc việc chọn L hay harm**: hai metric cho **cùng một verdict** ở mục này. Biên = tỉ lệ bỏ lọt thấp nhất trên các hệ H18 có mặt, lấy lại trong từng lần rút; cột held-out xấu nhất; chỉ workflow có H ≥ 9 (giữ cả Δ = 4 và 8).

**Hình dạng đường cong theo mức ngân sách** (biên, ρ = 0; `metrics.h18_miss_curve`):

| Mức ngân sách | biên ở Δ = 4 | biên ở Δ = 8 | B1 | B2 | Sentinel (Δ4 / Δ8) |
|---|---|---|---|---|---|
| b1 *(từ khối main)* | 0,189 | 0,012 | 1,00 / 1,00 | 0,189 / 0,012 | 0,361 / 0,038 |
| 2×B_min | 0,836 | 0,844 | 1,00 / 1,00 | 0,836 / 0,844 | 0,955 / 0,878 |
| 1×B_min | 0,852 | 0,906 | 1,00 / 1,00 | 0,964 / 0,906 | 0,852 / 1,000 |
| 0,5×B_min | 1,000 | 1,000 | 1,00 / 1,00 | 1,000 / 1,000 | 1,000 / 1,000 |

Đọc được ngay: **B1 bỏ lọt 100% ở mọi mức và mọi Δ** (nó chỉ audit ở commit, nên không bao giờ bắt trước σ), nên biên luôn do B2 hoặc Sentinel giữ. Ở **0,5×B_min mọi hệ bỏ lọt 100%** — mức đó không mua được gì. Từ 1×B_min lên b1 tỉ lệ bỏ lọt sập từ ~0,85–0,91 xuống 0,189 (Δ=4) và 0,012 (Δ=8).

**Kiểm định đã khai** (rule D trên V_miss(Δ=8) − V_miss(Δ=4) tại **b1**; `metrics.h18_miss_change`):

| ρ | biên Δ=4 | biên Δ=8 | thay đổi | CI 95% | p | verdict vế **draft** (+1) | verdict vế **note** (−1) |
|---|---|---|---|---|---|---|---|
| 0 | 0,189 | 0,012 | **−0,176** | [−0,260; −0,117] | 0,0000 | **bác** | **khớp** |
| 0,25 | 0,189 | 0,012 | **−0,176** | [−0,260; −0,117] | 0,0000 | **bác** | **khớp** |
| 0,5 | 0,189 | 0,012 | **−0,176** | [−0,257; −0,117] | 0,0000 | **bác** | **khớp** |
| 1 | 0,189 | 0,012 | **−0,176** | [−0,253; −0,117] | 0,0000 | **bác** | **khớp** |

(n = 65 workflow trên 13 họ repo; BH q = 0,05, hai vế dùng **một** kiểm định vì cùng `quantity`.)

Biên ở b1 giống nhau ở cả 4 ρ vì nó do **B2 uniform random** giữ, và tỉ lệ bỏ lọt của B2 không đổi theo ρ ở ô này (ρ chỉ mở kênh review ở commit, thứ B2 không dùng). Thay đổi theo từng hệ ở ρ = 0: B1 0,000 · B2 −0,176 · Sentinel −0,324.

**Kết luận H18 (cả hai metric):** ở mức ngân sách đã khai b1, tỉ lệ bỏ lọt **giảm** khi Δ đi từ 4 lên 8, khoảng tin cậy loại 0, ở **mọi ρ** → **vế note (Thm 5.6: ngân sách tối thiểu rơi như H/Δ) khớp; vế draft (Định lý 4 như in: ngân sách phải tăng theo Δ) bị bác.** Đây là lần đầu một vế của H18 được chấm; nó cùng chiều với phát hiện của rà soát lý thuyết 27/09 rằng **Định lý 4 bị đảo hướng**.

Ngoài mức đã khai, cùng thống kê ở **2×B_min** thì **không kết luận** ở cả 3 ρ có mặt (ρ=0: 0,007 [−0,062; 0,080], p = 0,8442; ρ=0,25: −0,094 [−0,173; 0,009], p = 0,0696; ρ=0,5: −0,043 [−0,122; 0,022], p = 0,1592) — in ở đây để không ai đọc verdict b1 như một phát biểu về mọi mức ngân sách.

**Vẫn TBD trong H18:** vế χ (`bmin_diff_chi_price_only`, rule E) — khối `h18` của lượt này **không có arm price-only** và chỉ có χ = 1,33, nên không có gì để so; ngoài ra Q12 **không** khai δ cho đại lượng kiểu ngân sách, nên check đó sẽ INCONCLUSIVE ngay cả khi có số (N3).

### 10.2 H19 — độ dốc của gain theo K_d

`gain_slope_in_kd` = gain(K_d = 3) − gain(K_d = 1) so với B1, ô headline Δ ∈ {4, 8}, cùng một bộ rút họ cho cả bốn bảng (B1/Sentinel × K_d ∈ {1,3}), nên hiệu số được rút **theo cặp**. K_d = 2 lấy từ khối `main` để thấy đủ ba điểm; **K_d ≠ 2 dùng lại bảng dòng 5 của K_d = 2 (O15)**.

Theo **L** (headline) — gain % [CI]:

| ρ | K_d = 1 | K_d = 2 *(main)* | K_d = 3 | độ dốc (3 − 1) | CI 95% | p | verdict draft (+1) | verdict note (−1) |
|---|---|---|---|---|---|---|---|---|
| 0 | +27,3 [+20,4; +35,7] | +22,6 | +23,9 [+16,9; +34,6] | **−3,5** | [−6,9; +1,1] | 0,1820 | không kết luận | không kết luận |
| 0,25 | +19,2 [+11,0; +35,0] | +20,9 | +22,6 [+12,1; +37,6] | **+3,4** | [−2,1; +5,5] | 0,3396 | không kết luận | không kết luận |
| 0,5 | +14,0 [+3,2; +26,7] | +14,0 | +14,8 [+4,2; +23,4] | **+0,8** | [−5,8; +3,5] | 0,7730 | không kết luận | không kết luận |
| 1 | −50,7 [−96,5; −14,7] | −47,2 | −46,2 [−90,2; −11,7] | **+4,6** | [−1,0; +11,4] | 0,1214 | không kết luận | không kết luận |

Theo **harm** — gain % [CI]:

| ρ | K_d = 1 | K_d = 2 *(main)* | K_d = 3 | độ dốc (3 − 1) | CI 95% | p | verdict draft (+1) | verdict note (−1) |
|---|---|---|---|---|---|---|---|---|
| 0 | −1,1 [−7,3; +8,1] | −4,3 | −4,3 [−11,2; +4,7] | **−3,2** | [−8,7; +2,0] | 0,1746 | không kết luận | không kết luận |
| 0,25 | −23,4 [−35,5; −3,1] | −22,6 | −21,6 [−31,7; −1,8] | **+1,8** | [−4,3; +8,6] | 0,7138 | không kết luận | không kết luận |
| 0,5 | −44,1 [−59,0; −23,8] | −46,4 | −46,4 [−62,3; −26,1] | **−2,3** | [−10,3; +0,3] | 0,0574 | không kết luận | không kết luận |
| 1 | −292,9 [−480,2; −181,9] | −292,9 | −292,9 [−490,7; −175,6] | **+0,0** | [−16,2; +11,3] | 1,0000 | không kết luận | không kết luận |

**Kết luận H19 (cả hai metric):** **không kết luận ở mọi ρ và cả hai vế.** Khoảng tin cậy của độ dốc chứa 0 ở tất cả 8 ô (p nhỏ nhất là 0,0574, ρ = 0,5 theo harm), và BH ở q = 0,05 không bác 0. Trục K_d ∈ {1, 3} trên dev **không tách được** "commit càng thiếu khi carrier nhân lên" (draft, +1) khỏi "gain co lại khi K tăng" (note Cor. 6.1, −1). Đáng ghi thêm: độ dốc không chỉ nhỏ mà còn **không cùng dấu theo ρ** (theo L: −3,5 ở ρ = 0 nhưng +4,6 ở ρ = 1), tức hình dạng theo K_d **phụ thuộc ρ**, điều mà cả hai vế đều không phát biểu.

**Kiểm chéo quan trọng:** cột K_d = 2 đọc từ khối `main` cho **đúng** các số của mục 2 (theo L: +22,6 / +20,9 / +14,0 / −47,2; theo harm: −4,3 / −22,6 / −46,4 / −292,9), nên đường tính của mục 10 và của mục 2 khớp nhau.

Exploitability trên trục K_d (`kd-br`, B1 + Sentinel, Δ ∈ {4, 8}) **chưa** đưa vào mục này: nó không phải một check nào của khung H, và không có hệ nào khác để so — giữ như số phụ trong `spikes/v3-run/h_verdicts.json`.

### 10.3 H20 — cột "attacker chọn Δ": vẫn TBD, và vì sao

H20 là một check **rule N** trên `v_sentinel_minus_b1_attacker_delta` = V_S − V_B1 trong cột attacker chọn Δ, với δ = 0,10 (harm). **Không tính được ở lượt này:** luật trim của khung (`attackers.br_systems`: ở Δ = `attacker` trong thế giới chính trả về `"sentinel"`) cho cột đó **chỉ cho lớp Sentinel**. Khối `attacker-delta` đúng như vậy — 6 hệ (S, S -alarm memory, S -benign-drift, S -randomization, S -transition uncertainty, S [dhat=oracle]), **không có bản ghi B1 nào** — và khối `sens-attacker-delta:reversible` chỉ có Sentinel. Không có V_B1 thì không lập được hiệu số mà rule N đọc → **TBD (N3)**. Không được thay V_B1 của cột này bằng V_B1 của cột held-out: hai bên khác bộ estimator (mục 9.4).

Những gì khối này **có** trả lời, in ra để không mất thông tin:

**(a) Menu của attacker có Δ = 0, và Δ nhỏ chiếm phần lớn nó.** Đếm Δ = σ − ι trên các placement được chạy (mỗi ρ giống nhau, cùng menu): Δ=0: 11.740 · Δ=1: 9.244 · Δ=2: 7.688 · Δ=4: 5.056 · Δ=8: 1.660. Tức tiền đề của Prop. 6.3(a) ("có 0 trong menu") **đúng** trong thiết kế lượt chạy.

**(b) V_BR (cross-fit, D27) của lớp Sentinel khi attacker được chọn Δ**, hai metric:

| ρ | metric | Sentinel | −alarm memory | −benign-drift | −randomization | −transition | [dhat=oracle] |
|---|---|---|---|---|---|---|---|
| 0 | L | 0,8048 [0,717; 0,893] | 0,8012 [0,706; 0,896] | 0,9791 [0,857; 1,101] | 0,8201 [0,753; 0,888] | 1,0391 [0,971; 1,108] | 0,8319 [0,752; 0,911] |
| 0 | harm | 0,7442 [0,666; 0,821] | 0,7442 [0,666; 0,821] | 0,7442 [0,666; 0,821] | 0,7442 [0,668; 0,820] | 0,6919 [0,637; 0,746] | 0,7471 [0,672; 0,821] |
| 0,25 | L | 0,7961 [0,711; 0,881] | 0,7324 [0,644; 0,818] | 0,9874 [0,902; 1,075] | 0,7761 [0,691; 0,861] | 0,7961 [0,711; 0,881] | 0,8022 [0,671; 0,932] |
| 0,25 | harm | 0,7616 [0,687; 0,835] | 0,7381 [0,659; 0,816] | 0,7500 [0,679; 0,820] | 0,7500 [0,680; 0,819] | 0,7616 [0,687; 0,835] | 0,7442 [0,661; 0,827] |
| 0,5 | L | 0,7600 [0,665; 0,854] | 0,7758 [0,705; 0,845] | 0,9766 [0,867; 1,087] | 0,8375 [0,762; 0,913] | 0,7600 [0,665; 0,854] | 0,8325 [0,779; 0,886] |
| 0,5 | harm | 0,6882 [0,635; 0,741] | 0,7093 [0,631; 0,787] | 0,6845 [0,632; 0,737] | 0,7267 [0,656; 0,798] | 0,6882 [0,635; 0,741] | 0,7326 [0,678; 0,787] |
| 1 | L | 0,7515 [0,679; 0,822] | 0,7347 [0,672; 0,796] | 1,0092 [0,904; 1,116] | 0,8647 [0,780; 0,949] | 0,7883 [0,721; 0,853] | 0,8109 [0,743; 0,876] |
| 1 | harm | 0,7619 [0,693; 0,829] | 0,7440 [0,668; 0,819] | 0,7619 [0,688; 0,833] | 0,7412 [0,657; 0,825] | 0,7619 [0,688; 0,833] | 0,7471 [0,675; 0,818] |

So với mục 9.2 (cùng bộ estimator cross-fit, thế giới chính): ở ρ = 0 theo L, V_BR của Sentinel là **0,8048** khi attacker chọn Δ, so với 0,8042 ở Δ = 4 và 0,6152 ở Δ = 8. Nghĩa là **cho attacker quyền chọn Δ đưa giá trị về gần đúng cột Δ khó nhất**, không cao hơn — đúng điều một max trên menu phải làm, và đúng cơ chế C11 (Δ nhỏ thì harm khoá trong cửa sổ trễ, mục 6). Cùng kết luận ở cả 4 ρ và cả hai metric. Giá trị **naive** in kèm trong `h_verdicts.json` (ví dụ ρ=0 theo L: 1,5089 so với 0,8048 cross-fit) — mục 9.4 vẫn áp dụng.

**(c) Thế giới reversible là nơi duy nhất so được trực tiếp** cột attacker-Δ với cột Δ ∈ {4, 8} *trong cùng một lượt* (có cả `sens-attacker-delta:reversible` và `sens-br:reversible`), cho Sentinel:

| ρ | metric | V_BR(attacker chọn Δ) | V_BR(Δ ∈ {4,8}) | hiệu | CI 95% | p |
|---|---|---|---|---|---|---|
| 0 | L | 0,5252 | 0,5118 | 0,0134 | [−0,082; 0,110] | 0,8004 |
| 0 | harm | 0,4583 | 0,4125 | 0,0458 | [−0,117; 0,211] | 0,6110 |
| 0,25 | L | 0,5692 | 0,5459 | 0,0233 | [−0,063; 0,111] | 0,6254 |
| 0,25 | harm | 0,4118 | 0,5000 | −0,0882 | [−0,264; 0,087] | 0,3556 |
| 0,5 | L | 0,4520 | 0,4266 | 0,0253 | [−0,077; 0,126] | 0,6568 |
| 0,5 | harm | 0,3512 | 0,2938 | 0,0574 | [−0,042; 0,158] | 0,3124 |
| 1 | L | 0,4125 | 0,3980 | 0,0144 | [−0,042; 0,072] | 0,6318 |
| 1 | harm | 0,4136 | 0,2468 | 0,1667 | [0,073; 0,260] | 0,0000 |

Cột attacker-Δ cao hơn cột Δ ∈ {4, 8} ở **7 trong 8 ô** (ô còn lại, ρ = 0,25 theo harm, thấp hơn 0,088 nhưng CI chứa 0), và **cao hơn có ý nghĩa** ở đúng một ô: ρ = 1 theo harm (+0,167 [+0,073; +0,260], p = 0). Đọc trung thực: quyền chọn Δ có giá trị cho attacker, rõ nhất ở chỗ Sentinel đã yếu nhất (ρ = 1). Đây **không** là verdict H20 — H20 cần so với B1.

### 10.4 Sáu thế giới độ nhạy một nhân tố

Mỗi thế giới đổi **đúng một** công tắc so với thế giới chính (`config.sensitivities`), mọi trục khác giữ ô headline (χ = 1,33; d′ = 2,21; K_d = 2; b1; Δ ∈ {4, 8}; 7 cột held-out). **O15 áp dụng: bảng dòng 5 vẫn là bảng của thế giới chính.**

#### 10.4.1 Đối chứng D28 trước đã — và thế giới `stage` KHÔNG ĐẠT

| Thế giới | đối chứng (+) Oracle @ Δ∈{4,8} | (−) B1 @ Δ=0 | sweeper @ Δ=0 (B3 / B4 / B6) | ok |
|---|---|---|---|---|
| A7 | 0,0000 | 0,7614 | 0,8506 / 0,8506 / 0,8506 | **ĐẠT** |
| drift-persistent | 0,0000 | 0,7614 | 0,8506 / 0,8506 / 0,8506 | **ĐẠT** |
| ingress-hidden | 0,0000 | 0,7614 | 0,8506 / 0,8506 / 0,8506 | **ĐẠT** |
| reversible | 0,0000 | 0,7614 | 0,8506 / 0,8506 / 0,8506 | **ĐẠT** |
| seed-2 | 0,0000 | 0,7614 | 0,8506 / 0,8506 / 0,8506 | **ĐẠT** |
| stage | 0,8415 | 0,7614 | 0,0120 / 0,0640 / 0,2622 | **KHÔNG ĐẠT** |

Năm thế giới đầu **đạt ở cả 4 ρ**. Thế giới **`stage` (audit đọc theo stage) không đạt, sai cả hai vế**: Oracle (+) lên **0,841** thay vì 0 (nó không còn cách ly được carrier bị nhiễm khi audit đọc theo stage), và vế (−) đổ hoàn toàn — ở Δ = 0 ba sweeper đạt 0,012 / 0,064 / 0,262, **tốt hơn B1 (0,761)**, tức một sweep chạy sau agent lại chặn được thứ mà theo thiết kế nó không thể chặn.

Theo **D28 / M1** ("the controls were read and failed: fix the world, do not read Sentinel"), **không đọc số Sentinel của thế giới `stage`** trong báo cáo này — `metrics.Readout` cũng sẽ ném `ControlsFailed`. Chỉ ghi lại: V_B1(L) ở `stage` là 2,1339 / 2,0132 / 1,8408 / 1,4788 theo ρ (so với 1,236 / 1,086 / 0,951 / 0,604 ở thế giới chính) — audit theo stage làm B1 mất thêm rất nhiều task sạch, và FQ/episode của B1 nhảy từ 0,000 lên 1,207. **Đây là một việc cần sửa thế giới, không phải một kết quả.**

#### 10.4.2 gain của Sentinel so với B1 trong từng thế giới đọc được, hai metric

| Thế giới | ρ | V_B1(L) | V_S(L) | **gain L %** [CI] | V_B1(harm) | V_S(harm) | gain harm % [CI] |
|---|---|---|---|---|---|---|---|
| A7 | 0 | 1,2358 | 0,9408 | **+23,9** [+17,4; +33,6] | 0,7874 | 0,7857 | +0,2 [−6,2; +10,4] |
| A7 | 0,25 | 1,0862 | 0,8616 | **+20,7** [+12,4; +36,8] | 0,6463 | 0,7560 | −17,0 [−26,5; +5,7] |
| A7 | 0,5 | 0,9512 | 0,8248 | **+13,3** [+2,4; +20,7] | 0,5122 | 0,7321 | −42,9 [−60,1; −21,2] |
| A7 | 1 | 0,6038 | 0,9102 | **−50,7** [−97,4; −15,8] | 0,1970 | 0,7679 | −289,8 [−481,9; −174,9] |
| drift-persistent | 0 | 1,2358 | 0,9953 | **+19,5** [+11,8; +26,4] | 0,7874 | 0,8538 | −8,4 [−18,9; +0,6] |
| drift-persistent | 0,25 | 1,0862 | 0,9486 | **+12,7** [+2,9; +27,9] | 0,6463 | 0,8095 | −25,2 [−38,0; −7,1] |
| drift-persistent | 0,5 | 0,9512 | 0,9946 | **−4,6** [−11,9; +3,5] | 0,5122 | 0,7500 | −46,4 [−72,2; −23,9] |
| drift-persistent | 1 | 0,6038 | 0,9989 | **−65,4** [−124,8; −27,4] | 0,1970 | 0,7798 | −295,9 [−493,2; −183,9] |
| ingress-hidden | 0 | 1,2358 | 0,9206 | **+25,5** [+14,1; +31,9] | 0,7874 | 0,8214 | −4,3 [−15,1; +2,7] |
| ingress-hidden | 0,25 | 1,0862 | 0,9016 | **+17,0** [+7,2; +30,8] | 0,6463 | 0,8103 | −25,4 [−37,0; −13,3] |
| ingress-hidden | 0,5 | 0,9512 | 0,8822 | **+7,3** [−7,6; +20,0] | 0,5122 | 0,7560 | −47,6 [−71,1; −29,7] |
| ingress-hidden | 1 | 0,6038 | 0,8668 | **−43,6** [−91,4; −12,3] | 0,1970 | 0,7560 | −283,8 [−479,6; −180,5] |
| reversible | 0 | 1,2358 | 0,7008 | **+43,3** [+35,8; +50,2] | 0,7874 | 0,6264 | +20,4 [+13,9; +28,4] |
| reversible | 0,25 | 1,0862 | 0,6810 | **+37,3** [+29,0; +48,0] | 0,6463 | 0,5846 | +9,6 [−4,7; +23,0] |
| reversible | 0,5 | 0,9512 | 0,7105 | **+25,3** [+18,7; +33,7] | 0,5122 | 0,5538 | −8,1 [−34,3; +6,0] |
| reversible | 1 | 0,6038 | 0,5605 | **+7,2** [−43,7; +33,3] | 0,1970 | 0,4598 | −133,4 [−291,7; −60,9] |
| seed-2 | 0 | 1,2358 | 0,8820 | **+28,6** [+20,1; +39,2] | 0,7874 | 0,7917 | −0,5 [−8,1; +10,1] |
| seed-2 | 0,25 | 1,0862 | 0,8320 | **+23,4** [+19,0; +34,0] | 0,6463 | 0,7500 | −16,0 [−27,9; +3,5] |
| seed-2 | 0,5 | 0,9512 | 0,8214 | **+13,6** [+0,9; +28,7] | 0,5122 | 0,6726 | −31,3 [−50,2; −13,2] |
| seed-2 | 1 | 0,6038 | 0,7682 | **−27,2** [−65,6; −1,1] | 0,1970 | 0,6369 | −223,4 [−375,2; −144,4] |

**Bản đồ chế độ của mục 4 sống sót cả năm thế giới đọc được, theo L**: gain dương và CI loại 0 ở ρ ≤ 0,25 trong **5/5** thế giới; ở ρ = 1 âm và CI loại 0 trong 4/5 (reversible thì không kết luận: +7,2 [−43,7; +33,3]). Ranh giới **dịch** theo thế giới, đúng chỗ đáng kể nhất:

- **`drift-persistent` đẩy ranh giới sớm lên:** ở ρ = 0,5 gain theo L là **−4,6 [−11,9; +3,5]** (không kết luận) thay vì +14,0 của thế giới chính, và ở ρ = 0,25 chỉ còn +12,7 [+2,9; +27,9]. Drift lành dai dẳng là công tắc đắt nhất cho Sentinel — cùng chiều với mục 5 (mô hình hoá drift lành là thành phần chịu tải chính).
- **`ingress-hidden`** cũng làm ρ = 0,5 mất ý nghĩa (+7,3 [−7,6; +20,0]).
- **`reversible` là thế giới thuận nhất, và là thế giới duy nhất Sentinel thắng B1 *theo cả harm*:** ρ = 0 gain harm **+20,4% [+13,9; +28,4]** (và L +43,3% [+35,8; +50,2]). Khi harm hoàn lại được sau σ, việc cách ly muộn của Sentinel vẫn cứu được harm, nên lỗ hổng đo lường của metric harm-only (mục 3) tự khép lại.
- **`A7` và `seed-2`** gần thế giới chính (gain L +23,9 / +28,6 ở ρ = 0).

Theo **harm**, ngoài `reversible` thì gain âm hoặc không kết luận ở mọi thế giới và mọi ρ — đúng dự đoán ghim số 4 của tiền đăng ký.

**Một quan sát phải khai (N3):** V và các số phụ của **B1 giống hệt thế giới chính** (bit-wise trên trung bình harm 0,42399384773135 và t_lost 0,70494744937196 mỗi episode) ở **A7, drift-persistent, ingress-hidden, reversible và stage**; chỉ `seed-2` đổi harm của B1 (0,4619) và `stage` đổi FQ của B1. Đây **đúng như khai**, không phải lỗi: bốn công tắc kia chỉ đổi kênh quan sát hoặc niềm tin, thứ B1 không dùng, và `v3/observe.py` ghi rõ *"A7 READING (L2, fix-a7 27/09): provenance is an EXTRA observation channel … a plain policy (B1, …) behaves identically in A0 and A7"*. Hệ **duy nhất** đọc kênh A7 là `B1-prov` (`v3/baselines.py:212`), và **`B1-prov` không nằm trong 15 hệ của lượt này** → thế giới A7 ở đây chỉ đo tác động lên Sentinel, **không** đo điều A7 được dựng để đo. Cần một lượt có `B1-prov` trước khi phát biểu bất cứ điều gì về A7.

#### 10.4.3 Ablation trong từng thế giới (theo L, ρ = 0,5)

| Thế giới | Sentinel | [dhat=oracle] | −randomization | −alarm memory | −benign-drift | −transition |
|---|---|---|---|---|---|---|
| A7 | +13,3 | +13,3 | +10,4 | +8,1 | −8,9 | +13,3 |
| drift-persistent | −4,6 | −5,0 | −13,2 | −0,6 | −36,2 | −4,6 |
| ingress-hidden | +7,3 | +3,6 | +2,2 | +13,1 | −18,8 | +7,3 |
| reversible | +25,3 | +26,1 | +33,9 | +13,9 | +5,6 | +25,3 |
| seed-2 | +13,6 | +13,6 | +14,7 | +8,2 | −16,6 | +13,6 |

`−benign-drift` là cánh tệ nhất trong **5/5** thế giới đọc được (rơi 20–32 điểm so với bản đầy đủ), khớp mục 5. `−transition uncertainty` **bằng đúng** bản đầy đủ ở cả 5 thế giới tại ρ = 0,5 (outcome-identical ở ô này, đúng cảnh báo "outcome-identical is not inactive" của paper). `−randomization` lật dấu theo thế giới: **tốt hơn** bản đầy đủ ở `reversible` (+33,9 so với +25,3) và ở `seed-2` (+14,7 so với +13,6), nhưng tệ hơn ở `A7`, `drift-persistent`, `ingress-hidden`.

#### 10.4.4 Exploitability trong từng thế giới (cross-fit D27, in kèm naive)

| Thế giới | ρ | metric | V_held-out | V_BR cross-fit | exploit [CI] | exploit naive |
|---|---|---|---|---|---|---|
| A7 | 0 | L | 0,9408 | 0,7359 | −0,205 [−0,336; −0,127] | 0,389 |
| A7 | 0 | harm | 0,7857 | 0,6772 | −0,108 [−0,194; −0,031] | 0,179 |
| A7 | 0,25 | L | 0,8616 | 0,7601 | −0,101 [−0,187; −0,019] | 0,507 |
| A7 | 0,25 | harm | 0,7560 | 0,6875 | −0,068 [−0,148; 0,012] | 0,209 |
| A7 | 0,5 | L | 0,8248 | 0,6374 | −0,187 [−0,323; −0,137] | 0,639 |
| A7 | 0,5 | harm | 0,7321 | 0,5833 | −0,149 [−0,294; −0,014] | 0,243 |
| A7 | 1 | L | 0,9102 | 0,6920 | −0,218 [−0,303; −0,145] | 0,528 |
| A7 | 1 | harm | 0,7679 | 0,6312 | −0,137 [−0,225; −0,047] | 0,207 |
| drift-persistent | 0 | L | 0,9953 | 0,8585 | −0,137 [−0,263; −0,081] | 0,413 |
| drift-persistent | 0 | harm | 0,8538 | 0,7722 | −0,082 [−0,220; 0,000] | 0,121 |
| drift-persistent | 0,25 | L | 0,9486 | 0,8370 | −0,112 [−0,214; −0,055] | 0,453 |
| drift-persistent | 0,25 | harm | 0,8095 | 0,7405 | −0,069 [−0,174; 0,009] | 0,155 |
| drift-persistent | 0,5 | L | 0,9946 | 0,7163 | −0,278 [−0,412; −0,215] | 0,608 |
| drift-persistent | 0,5 | harm | 0,7500 | 0,6420 | −0,108 [−0,227; −0,050] | 0,215 |
| drift-persistent | 1 | L | 0,9989 | 0,7475 | −0,251 [−0,367; −0,187] | 0,585 |
| drift-persistent | 1 | harm | 0,7798 | 0,6173 | −0,162 [−0,251; −0,083] | 0,180 |
| ingress-hidden | 0 | L | 0,9206 | 0,8461 | −0,074 [−0,222; −0,053] | 0,391 |
| ingress-hidden | 0 | harm | 0,8214 | 0,7438 | −0,078 [−0,208; −0,034] | 0,153 |
| ingress-hidden | 0,25 | L | 0,9016 | 0,7743 | −0,127 [−0,293; −0,012] | 0,410 |
| ingress-hidden | 0,25 | harm | 0,8103 | 0,7688 | −0,042 [−0,188; 0,011] | 0,164 |
| ingress-hidden | 0,5 | L | 0,8822 | 0,7240 | −0,158 [−0,294; −0,098] | 0,615 |
| ingress-hidden | 0,5 | harm | 0,7560 | 0,6203 | −0,136 [−0,254; −0,054] | 0,219 |
| ingress-hidden | 1 | L | 0,8668 | 0,7280 | −0,139 [−0,251; −0,072] | 0,635 |
| ingress-hidden | 1 | harm | 0,7560 | 0,6076 | −0,148 [−0,254; −0,064] | 0,219 |
| reversible | 0 | L | 0,7008 | 0,5118 | −0,189 [−0,313; −0,088] | 0,533 |
| reversible | 0 | harm | 0,6264 | 0,4125 | −0,214 [−0,352; −0,087] | 0,343 |
| reversible | 0,25 | L | 0,6810 | 0,5459 | −0,135 [−0,276; −0,016] | 0,571 |
| reversible | 0,25 | harm | 0,5846 | 0,5000 | −0,085 [−0,214; 0,002] | 0,380 |
| reversible | 0,5 | L | 0,7105 | 0,4266 | −0,284 [−0,383; −0,203] | 0,592 |
| reversible | 0,5 | harm | 0,5538 | 0,2938 | −0,260 [−0,396; −0,201] | 0,375 |
| reversible | 1 | L | 0,5605 | 0,3980 | −0,162 [−0,266; −0,109] | 0,726 |
| reversible | 1 | harm | 0,4598 | 0,2468 | −0,213 [−0,322; −0,130] | 0,444 |
| seed-2 | 0 | L | 0,8820 | 0,7431 | −0,139 [−0,300; −0,026] | 0,572 |
| seed-2 | 0 | harm | 0,7917 | 0,7244 | −0,067 [−0,167; 0,010] | 0,183 |
| seed-2 | 0,25 | L | 0,8320 | 0,6972 | −0,135 [−0,268; −0,019] | 0,635 |
| seed-2 | 0,25 | harm | 0,7500 | 0,6776 | −0,072 [−0,189; 0,022] | 0,225 |
| seed-2 | 0,5 | L | 0,8214 | 0,6616 | −0,160 [−0,265; −0,063] | 0,729 |
| seed-2 | 0,5 | harm | 0,6726 | 0,6218 | −0,051 [−0,152; 0,030] | 0,302 |
| seed-2 | 1 | L | 0,7682 | 0,7156 | −0,053 [−0,171; 0,020] | 0,739 |
| seed-2 | 1 | harm | 0,6369 | 0,5823 | −0,055 [−0,195; 0,035] | 0,333 |

Dấu **âm ở mọi thế giới, mọi ρ, cả hai metric** theo cross-fit và **dương ở mọi ô** theo naive — y như mục 9.4 trên thế giới chính, nên kết luận của mục 9.4 giữ nguyên và **không mở rộng**: cột held-out xấu nhất đã khó bằng hoặc hơn attacker best-response ước lượng không chệch; "không khai thác được" thì **vẫn TBD**. Với `seed-2`, V_BR lấy từ khối `seed2-pairs` (khối ngoài core, luật `br_systems(..., core=False)`), là khối duy nhất trong nhóm này có **cả B1**.

#### 10.4.5 H8 trong các thế giới độ nhạy: "B3 là tệ nhất" **chỉ đúng theo L**

`v_b3_minus_worst_other` = V(B3) − max V trên các hệ còn lại (bỏ Oracle), cùng bộ rút họ, re-max qua cột trong từng lần rút. Ô đã khai của H8 là **thế giới ingress-visible** (= thế giới chính, khối `main`) nên **verdict khung vẫn TBD**; đây là bản đọc trong 5 thế giới độ nhạy:

| Thế giới | ρ | theo L | theo harm |
|---|---|---|---|
| A7 | 0 | 1,611 [1,474; 1,780] (so với cost-greedy) | −0,021 [−0,084; 0,007] (so với B4 audit-on-retrieval) |
| A7 | 0,5 | 1,639 [1,508; 1,802] (so với cost-greedy) | −0,021 [−0,084; 0,007] (so với B4 audit-on-retrieval) |
| drift-persistent | 0 | 1,366 [1,191; 1,577] (so với cost-greedy) | −0,021 [−0,085; 0,004] (so với B4 audit-on-retrieval) |
| drift-persistent | 0,5 | 1,394 [1,226; 1,598] (so với cost-greedy) | −0,021 [−0,085; 0,007] (so với B4 audit-on-retrieval) |
| ingress-hidden | 0 | 0,798 [0,676; 0,926] (so với cost-greedy) | −0,017 [−0,046; 0,006] (so với B4 audit-on-retrieval) |
| ingress-hidden | 0,5 | 0,826 [0,711; 0,948] (so với cost-greedy) | −0,017 [−0,046; 0,006] (so với B4 audit-on-retrieval) |
| reversible | 0 | 1,611 [1,474; 1,780] (so với cost-greedy) | −0,021 [−0,084; 0,007] (so với B4 audit-on-retrieval) |
| reversible | 0,5 | 1,639 [1,508; 1,802] (so với cost-greedy) | −0,021 [−0,084; 0,007] (so với B4 audit-on-retrieval) |
| seed-2 | 0 | 1,561 [1,436; 1,761] (so với cost-greedy) | 0,000 [−0,022; 0,000] (so với B4 audit-on-retrieval) |
| seed-2 | 0,5 | 1,589 [1,472; 1,780] (so với cost-greedy) | 0,000 [−0,022; 0,000] (so với B4 audit-on-retrieval) |

Theo **L**, B3 tệ hơn hệ tệ thứ hai (cost-greedy) từ **+0,80 đến +1,67** với CI loại 0 ở mọi ô — "B3 là tệ nhất" **đúng và rất rõ**. Theo **harm**, B3 **không** tệ nhất: hiệu số là −0,021 đến 0,000, CI chứa 0 (p ≈ 0,77–1,00), và hệ ngang nó là B4 audit-on-retrieval. Lý do đọc thẳng từ mục 5, nơi B3 cách ly sai 4,38 lần mỗi episode ở thế giới chính: đó là thứ L phạt và harm-only không thấy. Đây là **ví dụ thứ hai** (sau mục 2) cho thấy việc chọn metric headline đổi kết luận của một hypothesis.

### 10.5 Bảng điểm sau mục 10: chấm được gì, TBD vì sao (N3)

| H | Rule | Trạng thái sau mục 10 | theo L | theo harm | Lý do nếu TBD |
|---|---|---|---|---|---|
| **H18** | D (+ E cho vế χ) | **CHẤM ĐƯỢC** (vế Δ) | vế draft **bác**, vế note **khớp** ở cả 4 ρ | **y như L** (thống kê là tỉ lệ bỏ lọt, không phụ thuộc metric) | vế χ TBD: không có arm price-only, và Q12 không khai δ cho ngân sách |
| **H19** | D | **CHẤM ĐƯỢC** | **không kết luận** cả hai vế, mọi ρ | **không kết luận** cả hai vế, mọi ρ | — |
| H1 | G + P | TBD | — | — | cần ô HEAD của thế giới chính (khối `main`, đã đọc ở mục 2–9 nhưng không phải nhiệm vụ của mục này) và lượt eval P5 cho `gain_heldout` |
| H2 | P | TBD | — | — | cần cả gain dev và gain held-out của **eval** (P5): chưa có lượt eval |
| H3 | P + D; E | TBD | — | — | cần trục χ (χ = 0 / 1,34) và **arm price-only**: lượt này chạy `--headline` nên chỉ có χ = 1,33, và khối `h18` không có arm price-only |
| H4 | P | TBD | — | — | `gain_delta0` ở ô Δ = 0 của thế giới chính — khối `main`, ngoài phạm vi mục này |
| H5 | D | TBD | — | — | cần gain ở χ uniform so với χ heterogeneous: không có trục χ trong lượt này |
| H6 | D | TBD | — | — | cần B2 và cost-greedy trong ô HEAD của thế giới chính (khối `main`) |
| H7 | P | TBD | — | — | cần 240 small game và **B7** (T21 chưa cài) |
| H8 | D | TBD | — | — | ô đã khai là thế giới **ingress-visible** (= thế giới chính); mục 10.4.5 chỉ đọc được trong 5 thế giới độ nhạy |
| H9 | P | TBD | — | — | `exploitability_*` ở ô HEAD thế giới chính (mục 9.2 có số; verdict cần P5 và cùng bộ estimator hai vế — mục 9.4) |
| H10 | P | TBD | — | — | clean completion và FQ % ở ô HEAD thế giới chính; ngoài ra Q12 **không** khai δ cho đại lượng phần trăm → sẽ INCONCLUSIVE |
| H11 | P + D | TBD | — | — | cần attacker LLM (addendum chưa chạy) |
| H12 | P + D | TBD | — | — | V tuyệt đối của các cánh ở ô HEAD thế giới chính; mục 10.4.3 chỉ là bản đọc trong thế giới độ nhạy |
| H13 | D | TBD | — | — | cần trục d′ (weak / strong detector): lượt này chỉ có d′ = 2,21 |
| H14 | D | TBD | — | — | cần sweep η_Q: không có block nào |
| H15 | D | TBD | — | — | `fq_pct_b5_minus_b1` ở ô HEAD thế giới chính |
| H16 | D | TBD | — | — | `br_carrier_spread_sentinel_minus_b1`: **không có estimator nào trong `v3/metrics.py`** cho "độ tản qua carrier"; T17 không tự đặt định nghĩa (N3) |
| H17 | D | TBD | — | — | `sw_random_benefit_minus_half_sentinel_benefit` ở ô HEAD thế giới chính |
| H20 | N | TBD | — | — | cột attacker chọn Δ **không có bản ghi B1** (luật trim `br_systems` → `"sentinel"`): không lập được V_S − V_B1 (mục 10.3) |

**Không có ô nào ghi 0 cho một đại lượng chưa đo.** Mọi TBD ở trên là `NOT_RUN` của `scorecard.score_all` (quantity không có `Estimate`), chứ không phải một outcome.

**Số máy đọc được:** `spikes/v3-run/h_verdicts.json` (không commit — `spikes/` trong `.gitignore`, D33): đủ verdict theo (metric, ρ), toàn bộ số H18 / H19 / H20, sáu thế giới độ nhạy, exploitability cross-fit và naive, và đối chứng D28 từng thế giới.

### 10.6 Ô nào của paper lấp được sau mục 10

Mục này **không sửa paper**; đây là bản đồ ô.

**Lấp được ngay — `sections/hypotheses.tex`, hai cột "Measured" và "Verdict":**

| Dòng | H | Measured | Verdict |
|---|---|---|---|
| 44 (ô cuối dòng H18) | **H18** | b1: tỉ lệ bỏ lọt của biên rơi 0,189 → 0,012 từ Δ=4 sang Δ=8; thay đổi −0,176 [−0,260; −0,117], p = 0, ở cả 4 ρ (cùng số cho L và harm) | **bác** vế draft · **khớp** vế note (Thm 5.6). Vế χ (rule E) giữ `\tbd` |
| 47 | **H19** | độ dốc gain(K=3) − gain(K=1): theo L −3,5 / +3,4 / +0,8 / +4,6 theo ρ, CI chứa 0 ở mọi ρ; theo harm −3,2 / +1,8 / −2,3 / 0,0, CI chứa 0 | **không kết luận** (cả hai vế, cả hai metric) |
| 50 | **H20** | — | giữ `\tbd`: cột attacker-Δ không có B1 (nêu lý do, đừng để trống) |

**Lấp được ngay — `sections/extra-tables.tex`, `tab:bounds`:**

| Dòng | Ô | Giá trị |
|---|---|---|
| 26 | H18 Measured + Verdict | như trên; "$\chi$-free on the price-only arm" giữ `\tbd` (không có arm price-only trong lượt) |
| 27 | H19 Measured + Verdict | như trên |
| 29 | H20 Measured + Verdict | giữ `\tbd` + lý do |

**Lấp được một phần — `sections/results.tex`:**

- **dòng 289–292** (`\TBD{...direction of the minimum budget on the budget grid (H18); gain along $\Kd$ (H19); the attacker-chooses-$\Dl$ column (H20)}`): lấp **H18** và **H19** bằng mục 10.1 và 10.2; **H3 / H4 / H7 / H20** trong cùng câu đó giữ `\TBD` (lý do ở mục 10.5).
- **dòng 472–477** (`\TBD{world A7 …; stage audits; harm reversible after $\sigma$; hidden ingress; persistent drift; two seeded carriers; $\Kd \in \{1, 3\}$; …}`): lấp bằng mục 10.4 cho **reversible, hidden ingress, persistent drift, two seeded carriers** và **K_d ∈ {1,3}**. **`stage` không được lấp bằng số** — phải viết là đối chứng D28 không đạt (mục 10.4.1). **A7 không được lấp** như một kết quả về A7: hệ đọc kênh A7 (`B1-prov`) không có trong lượt (mục 10.4.2). "the secondary 26-workflow split" và các addendum vẫn `\TBD`.

**Không lấp được (và vì sao):** `tab:rq1` (mọi dòng Measured — cần trục χ), `tab:detector` (cần trục d′), `tab:rq3` (cần LLM, B7), `tab:refarms` (cần rollout và `-regime estimate`), `results.tex:410` (ablation ở ô HEAD), và toàn bộ ô eval — chưa có lượt P5, `frozen/V3-GATE4.json` chưa được ký.

