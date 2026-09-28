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
