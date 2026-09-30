# P5 — H18 và H19 trên bản ghi HELD-OUT (eval)

**Ngày:** 29/09/2026 · **Split:** `eval` · **Script:** `auditgame/tools/v3_p5_h18_heldout.py`
**Máy đọc được:** `auditgame/spikes/v3-run/h_verdicts_eval.json` (cùng hình dạng với `h_verdicts.json`, `split: "eval"`) — nằm trên đĩa, **không commit**, đúng như bản dev của nó: `.gitignore:105` loại cả `auditgame/spikes/v3-run/` (D33, bản ghi lượt chạy không vào repo). Chạy lại bằng `--run` là dựng lại được.
**Đối chiếu:** `docs/reports/v3-p2-headline-dual-metric.md` §10 (verdict dev, `h_verdicts.json`, 28/09)

**Không lượt mô phỏng nào được chạy.** Đây là phân tích thuần trên bản ghi đã có trên đĩa:
`tools/v3_run.py` **không** được gọi, `frozen/v3-unseal-log.jsonl` **không** được ghi thêm, **không**
grant nào bị tiêu. Không tune, không build bảng.

```
freeze-v3: clean sha256:9c4c0d018b18  |  freeze-d35: clean sha256:e46f8a5c2f94  |  base freeze: clean sha256:c789fa7362e0
freeze: clean sha256:c789fa7362e0
```

Gate 4 (`frozen/V3-GATE4.json`) ghim `v3_manifest = 9c4c0d018b18…`, `scorecard_rules =
21b8c093254a…`; cả hai **còn khớp** với bản sống, và `grid.definition_digest()` vẫn là
`acbe9bdc48fd…`. Script nằm **ngoài** mặt phẳng băm (`freeze_v3` băm `v3/*.py`, `v3/dcm/**` và
5 đường dẫn trong `freeze_v3.FILES`; `freeze.SOURCE/TABLES` là mặt v2; `docs/` không nằm trong
cả hai), nên tạo nó **không** làm manifest dịch.

---

## 0. Xuất xứ và cách tính

| Khối | Tệp | sha256 (đã `shasum -c`) | Số dòng | Nội dung |
|---|---|---|---|---|
| h18 | `spikes/v3-run/eval-p1-h18kd/h18.jsonl` | `c308dabc52d0…` **OK** | 322.002 | B1 / B2 / Sentinel; **chỉ** 2× / 1× / 0,5×B_min; ρ ∈ {0; 0,25; 0,5} |
| kd | `spikes/v3-run/eval-p1-h18kd/kd.jsonl` | `7eba661457e4…` **OK** | 248.400 | B1 + Sentinel, K_d ∈ {1, 3}, mức b1, mọi ρ |
| main (đọc lại) | `spikes/v3-run/eval-pass1/main.jsonl` | — (xem §0.1) | 931.500 | **mức b1** của H18 và ô K_d = 2 của H19 |

**Cách tính — không viết lại metric nào.** `v3/metrics.table`, `boot_values`, `interval`,
`p_value`, `gain_ci`, `h18_miss_curve`, `h18_miss_change` và `v3/scorecard.Estimate` /
`score_all` / `rule_D_family` nguyên bản. Bootstrap wild cluster (Webb) theo họ repo,
N = 10.000, α = 0,05, re-max qua cột trong từng lần rút, **một** bộ rút họ dùng chung cho mọi
bảng của cùng một lời gọi. BH: `score_all` chạy **một lần cho mỗi (metric, ρ)**, q = 0,05 →
m = 2 (H18 và H19), **đúng như dev**. V(harm): `field="harm"`. V(L): Định nghĩa 1
(`runner.loss_of`) **đổi nhãn** vào đúng trường `gain_ci` cho điểm — đã kiểm:
`table(..., field="loss").value` và đường đổi nhãn cho **cùng một float**
(0,8805822291877743, so sánh `==`).

**Bằng chứng phương pháp đúng là phương pháp của dev.** Script dev **chưa từng được lưu** — đây
chính là lỗ hổng mục này lấp. Nên script này có cờ `--dev-selfcheck`: chạy **đúng pipeline này**
trên các khối **dev** rồi diff với `h_verdicts.json`. Kết quả: **56/56 con số khớp bit-for-bit**
(so sánh `repr` của float với H18; ≤ 1e-9 với độ dốc H19), gồm cả
`-0.17648412333179936`, CI `[-0.25996934493062374, -0.11651738746531606]`, và cả 8 độ dốc H19.
**Không còn bước nào mơ hồ.**

### 0.1 `eval-pass1/main.jsonl` — lập tính so sánh được từ chính bản ghi

Thư mục đó **không có `summary.json`**: lệnh bị kill về sau, trong khối `br`. Nên tính so sánh
được lập **từ bản ghi**: tập `(hệ, cột, ô)` quan sát được của `main.jsonl` **bằng đúng** tập mà
grid sống phát sinh cho khối `main` tại ô headline (χ = 1,33; d′ = 2,21) với 15 hệ đã khai —
**2.100 = 2.100, `identical: true`, không lệch một phần tử nào** — và grid digest sống là
`acbe9bdc48fd…`, đúng ghim Gate 4. Thêm vào: `split = "eval"` trên cả 931.500 dòng, cùng một
`world_id = 99c17340b36d` với khối h18/kd, mức b1, K_d = 2, `price_only = false`, đúng 7 cột
held-out, 96 workflow / 20 họ repo. Grant tương ứng có trong `frozen/v3-unseal-log.jsonl`
(28/09 18:10Z, `blocks: null`, `granted: true`, cùng `eval_split_sha256 = e34e747c36f1…`).

**`spikes/v3-run/eval-pass1/br.jsonl` KHÔNG được đọc** — 7,8 GB dở dang của lượt bị kill, đã
khai là **không phải kết quả**.

### 0.2 Đối chứng D28 trên khối main eval (bổ sung, không phải check của khung H)

**ĐẠT ở cả 4 ρ**: (+) Oracle @ Δ∈{4,8} = 0,0000; (−) ở Δ = 0 không sweeper nào thắng B1
(B1 0,757 / 0,631 / 0,459 / 0,286 theo ρ; ba sweeper 0,8718 ở mọi ρ). **Đọc trên harm**, và cố ý:
đối chứng (+) là ngưỡng **harm** (`CONTROL_MAX_HARM`). Đọc nó trên L thì nó **hỏng do cấu tạo**
— Oracle (+) vẫn trả FQ và task sạch mất, nên V(L) của nó là 0,431 ở ρ = 0 dù thế giới không
có lỗi nào. Đó là **dùng sai đối chứng, không phải phát hiện**, nên không báo cáo.

### 0.3 Lệch phải khai (N3) — lệch thứ nhất **giống hệt dev**

1. **Khối `h18` không có mức b1.** `grid.py` chỉ phát sinh unit b1 của cánh H18 cho
   `BlockSchedule`, hệ **duy nhất** của `H18_POLICIES` không nằm trong 15 hệ đã khai; B1 / B2 /
   Sentinel ở b1 thuộc khối `main`. `H18_CRITERION` vẫn khai `fixed_level = "b1"`. Nên b1 được
   đọc từ `eval-pass1/main.jsonl`, **đúng như dev đọc từ `dev-headline-main/main.jsonl`**, và
   **biên chỉ lấy trên 3 trong 4 hệ H18** (`block-schedule` vắng — đã xác nhận trên **cả hai**
   phía: khối h18 eval chỉ có `['B1 audit-at-commit', 'B2 uniform random', 'Sentinel']`).
2. **ρ = 1 bị loại khỏi khối `h18`** ở mọi mức ≠ b1 (`_bmin_hole` → `FLAG_COMMIT_SUFFICES`).
   Kiểm định b1 **tại ρ = 1 thì CÓ** đo (nó đến từ khối main).
3. **O15**: K_d ≠ 2 dùng lại bảng dòng 5 của thế giới chính.
4. Lượt này **không có** `h18-br` / `kd-br` → không có exploitability trên hai trục đó.

---

## 1. H18 trên held-out — hướng của ngân sách theo Δ

**Quy ước dấu, kiểm hai lần.** Đại lượng đã đăng ký là
`h18_miss_change_d8_minus_d4` = V_miss(Δ = 8) **trừ** V_miss(Δ = 4) của **biên** (tỉ lệ bỏ lọt
thấp nhất trên các hệ H18 có mặt, lấy lại trong **từng** lần rút), tại mức ngân sách đã khai
**b1**, cột held-out xấu nhất, chỉ workflow có **H ≥ 9** (giữ được cả hai Δ).
**Âm = bỏ lọt GIẢM khi Δ tăng = hướng của vế note.** Vế **draft** (Định lý 4 như in: ngân sách
phải **tăng** theo Δ) dự đoán **+1**; vế **note** (Thm 5.6: ngân sách tối thiểu rơi như H/Δ) dự
đoán **−1**. Hai vế dùng **một** kiểm định, một p, một ô BH (cùng `quantity`).
Kiểm số học: 0,0314 − 0,2007 = **−0,1693** ✓.

| ρ | biên Δ=4 | biên Δ=8 | **thay đổi** | CI 95% | p | p (BH) | verdict **draft** (+1) | verdict **note** (−1) |
|---|---|---|---|---|---|---|---|---|
| 0 | 0,2007 | 0,0314 | **−0,1693** | [−0,2167; −0,1276] | 0,0000 | 0,0000 | **bác** | **khớp** |
| 0,25 | 0,2007 | 0,0265 | **−0,1743** | [−0,2353; −0,1305] | 0,0000 | 0,0000 | **bác** | **khớp** |
| 0,5 | 0,2007 | 0,0234 | **−0,1774** | [−0,2285; −0,1352] | 0,0000 | 0,0000 | **bác** | **khớp** |
| 1 | 0,2007 | 0,0314 | **−0,1693** | [−0,2229; −0,1319] | 0,0000 | 0,0000 | **bác** | **khớp** |

n = **55 workflow trên 20 họ repo** (dev: 65 trên 13); BH q = 0,05, m = 2.
Thay đổi theo từng hệ ở ρ = 0: B1 **0,000** · B2 **−0,169** · Sentinel **−0,292**.
Thống kê chính là `missed_before_sigma`, nên **không phụ thuộc chọn L hay harm**: hai metric cho
**cùng một** verdict, như dev.

**Hình dạng đường cong theo mức ngân sách (biên, ρ = 0):**

| Mức ngân sách | biên Δ=4 | biên Δ=8 | B1 | B2 (Δ4/Δ8) | Sentinel (Δ4/Δ8) |
|---|---|---|---|---|---|
| b1 *(từ khối main)* | 0,201 | 0,031 | 1,00 / 1,00 | 0,201 / 0,031 | 0,334 / 0,042 |
| 2×B_min | 0,928 | 0,813 | 1,00 / 1,00 | 0,928 / 0,813 | 0,991 / 0,848 |
| 1×B_min | 0,931 | 0,898 | 1,00 / 1,00 | 1,000 / 0,898 | 0,931 / 0,990 |
| 0,5×B_min | 0,998 | 1,000 | 1,00 / 1,00 | 0,998 / 1,000 | 1,000 / 1,000 |

Cùng hình dạng như dev: **B1 bỏ lọt 100% ở mọi mức và mọi Δ** (nó chỉ audit ở commit), ở
**0,5×B_min mọi hệ gần như bỏ lọt hết**, và từ 1×B_min lên b1 tỉ lệ bỏ lọt sập từ ~0,90–0,93
xuống 0,201 (Δ=4) / 0,031 (Δ=8).

Ngoài mức đã khai, **cùng** thống kê ở **2×B_min** trên held-out **cũng âm và CI loại 0** ở cả
3 ρ có mặt (ρ=0: −0,116 [−0,152; −0,061], p = 0; ρ=0,25: −0,243 [−0,308; −0,170], p = 0;
ρ=0,5: −0,050 [−0,089; −0,008], p = 0,012) — **mạnh hơn dev**, nơi cả 3 ô đều không kết luận.
In ở đây để khỏi ai đọc verdict b1 như phát biểu về mọi mức; nó **không** thay verdict.

**Một chi tiết mới của held-out (N3).** Trên dev, biên ở b1 do **B2** giữ ở cả 4 ρ và không đổi
theo ρ. Trên eval, B2 vẫn bất biến theo ρ (0,2007 / 0,0314), nhưng ở **ρ = 0,25 và 0,5, Δ = 8
biên do chính Sentinel giữ** (0,0265 và 0,0234, thấp hơn B2), nên `|thay đổi|` **lớn hơn** một
chút ở hai ô đó. Điều này **củng cố**, không làm yếu, kết luận.

---

## 2. H19 trên held-out — độ dốc của gain theo K_d

`gain_slope_in_kd` = gain(K_d = 3) − gain(K_d = 1) so với B1, ô headline Δ ∈ {4, 8}, **cùng một**
bộ rút họ cho cả bốn bảng (B1/Sentinel × K_d ∈ {1,3}) nên hiệu được rút **theo cặp**. K_d = 2
lấy từ khối `main`. **O15 áp dụng cho K_d ≠ 2.** n = 94 workflow / 20 họ repo.

Theo **L** (headline) — gain % [CI]:

| ρ | K_d = 1 | K_d = 2 *(main)* | K_d = 3 | **độ dốc (3−1)** | CI 95% | p | draft (+1) | note (−1) |
|---|---|---|---|---|---|---|---|---|
| 0 | +31,7 [+25,4; +36,4] | +30,0 | +30,2 [+24,2; +34,6] | **−1,47** | [−3,38; +0,53] | 0,1556 | không kết luận | không kết luận |
| 0,25 | +28,2 [+20,2; +34,7] | +27,7 | +27,2 [+18,9; +33,2] | **−0,93** | [−5,53; +1,61] | 0,4498 | không kết luận | không kết luận |
| 0,5 | +8,5 [−0,4; +21,6] | +8,6 | +8,4 [−0,4; +21,3] | **−0,08** | [−1,83; +1,86] | 0,9426 | không kết luận | không kết luận |
| 1 | −46,7 [−61,5; −27,5] | −48,2 | −47,3 [−62,1; −28,2] | **−0,59** | [−4,14; +2,88] | 0,7658 | không kết luận | không kết luận |

Theo **harm** — gain % [CI]:

| ρ | K_d = 1 | K_d = 2 *(main)* | K_d = 3 | **độ dốc (3−1)** | CI 95% | p | draft (+1) | note (−1) |
|---|---|---|---|---|---|---|---|---|
| 0 | +7,2 [−1,4; +15,4] | +4,3 | +4,3 [−2,8; +12,7] | **−2,89** | [−4,90; +0,47] | 0,0860 | không kết luận | không kết luận |
| 0,25 | −2,1 [−13,1; +7,9] | −3,3 | −4,1 [−15,5; +4,7] | **−2,03** | [−8,06; +0,88] | 0,1578 | không kết luận | không kết luận |
| 0,5 | −36,0 [−53,8; −10,4] | −39,1 | −39,2 [−56,7; −13,0] | **−3,22** | [−5,33; +0,03] | 0,0518 | không kết luận | không kết luận |
| 1 | −345,3 [−426,4; −241,5] | −354,1 | −352,9 [−432,2; −250,9] | **−7,58** | [−18,90; +5,00] | 0,2568 | không kết luận | không kết luận |

**Kết luận H19 (cả hai metric): KHÔNG KẾT LUẬN ở mọi ρ và cả hai vế** — CI của độ dốc chứa 0 ở
**cả 8 ô** (p nhỏ nhất 0,0518, ρ = 0,5 theo harm, sát y hệt dev 0,0574), BH ở q = 0,05 không bác
0. Trục K_d ∈ {1, 3} trên held-out **cũng không tách được** "commit càng thiếu khi carrier nhân
lên" (draft, +1) khỏi "gain co lại khi K tăng" (note Cor. 6.1, −1). **Y như dev.**

**Khác dev một điểm đáng ghi:** trên dev độ dốc **không cùng dấu theo ρ** (theo L: −3,5 ở ρ = 0
nhưng +4,6 ở ρ = 1); trên held-out **cả 8 độ dốc đều âm**, tức hướng nhất quán hơn — nhưng
**không ô nào có ý nghĩa**, nên đây là một quan sát về hình dạng, **không** là verdict cho vế
note. Nói nó ủng hộ note sẽ là đọc quá số liệu.

**Kiểm chéo:** cột K_d = 2 đọc từ khối `main` cho **+30,0 / +27,7 / +8,6 / −48,2** theo L —
**đúng** các số headline held-out đã giao ở pass 1 (+30,0% / +27,7% trên L ở ρ thấp), nên đường
tính của mục này và của bảng headline khớp nhau.

---

## 3. Dev so với held-out, đặt cạnh nhau

### H18 — `h18_miss_change_d8_minus_d4` tại b1

| ρ | dev: thay đổi [CI] p | **eval: thay đổi [CI] p** | dev draft/note | **eval draft/note** |
|---|---|---|---|---|
| 0 | −0,1765 [−0,2600; −0,1165] 0,0000 | **−0,1693 [−0,2167; −0,1276] 0,0000** | bác / khớp | **bác / khớp** |
| 0,25 | −0,1765 [−0,2600; −0,1165] 0,0000 | **−0,1743 [−0,2353; −0,1305] 0,0000** | bác / khớp | **bác / khớp** |
| 0,5 | −0,1765 [−0,2570; −0,1165] 0,0000 | **−0,1774 [−0,2285; −0,1352] 0,0000** | bác / khớp | **bác / khớp** |
| 1 | −0,1765 [−0,2527; −0,1165] 0,0000 | **−0,1693 [−0,2229; −0,1319] 0,0000** | bác / khớp | **bác / khớp** |

Tỉ lệ bỏ lọt nền: dev **0,189 → 0,012**; **eval 0,2007 → 0,0314 / 0,0265 / 0,0234 / 0,0314**
(theo ρ). n: dev 65 wf / 13 họ; eval 55 wf / 20 họ.

### H19 — độ dốc theo K_d

| metric | ρ | dev độ dốc [CI] p | **eval độ dốc [CI] p** | dev | **eval** |
|---|---|---|---|---|---|
| L | 0 | −3,46 [−6,90; +1,09] 0,182 | **−1,47 [−3,38; +0,53] 0,156** | không kết luận | **không kết luận** |
| L | 0,25 | +3,45 [−2,07; +5,50] 0,340 | **−0,93 [−5,53; +1,61] 0,450** | không kết luận | **không kết luận** |
| L | 0,5 | +0,78 [−5,81; +3,45] 0,773 | **−0,08 [−1,83; +1,86] 0,943** | không kết luận | **không kết luận** |
| L | 1 | +4,58 [−1,05; +11,39] 0,121 | **−0,59 [−4,14; +2,88] 0,766** | không kết luận | **không kết luận** |
| harm | 0 | −3,22 [−8,74; +2,02] 0,175 | **−2,89 [−4,90; +0,47] 0,086** | không kết luận | **không kết luận** |
| harm | 0,25 | +1,84 [−4,35; +8,57] 0,714 | **−2,03 [−8,06; +0,88] 0,158** | không kết luận | **không kết luận** |
| harm | 0,5 | −2,32 [−10,27; +0,27] 0,057 | **−3,22 [−5,33; +0,03] 0,052** | không kết luận | **không kết luận** |
| harm | 1 | 0,00 [−16,21; +11,32] 1,000 | **−7,58 [−18,90; +5,00] 0,257** | không kết luận | **không kết luận** |

### Phát biểu thẳng

> **Kết luận dev GIỮ trên held-out.** H18: ở mức ngân sách đã khai b1, tỉ lệ bỏ lọt **giảm** khi
> Δ đi từ 4 lên 8, CI loại 0, ở **mọi ρ** → **vế note (Thm 5.6) khớp; vế draft (Định lý 4 như in)
> bị bác** — **cùng dấu, cùng verdict, ở cả 4 ρ và cả hai metric**, trên bản ghi held-out chưa
> ai đụng. Cùng chiều với rà soát lý thuyết 27/09 rằng **Định lý 4 bị đảo hướng**. H19: **không
> kết luận** ở mọi ρ và cả hai vế, **cũng y như dev** — giữ nguyên là "không kết luận", không
> phải "khớp".

Không có số nào trái với dev. Không criterion nào được viết lại, không metric nào bị đổi:
verdict đọc bằng đúng `scorecard.H18_CRITERION` và `rule_D_family` với `rules_digest`
`21b8c093254a…` mà Gate 4 ghim.

---

## 4. KHÔNG ĐO ĐƯỢC — có lý do, **không bao giờ là 0** (N3)

| Hạng mục | Vì sao |
|---|---|
| **Vế χ của H18** (`bmin_diff_chi_price_only`, rule E) | Khối h18 eval **không có arm price-only** và chỉ có χ = 1,33 → không có gì để so. Giống dev. Ngoài ra Q12 **không** khai δ cho đại lượng kiểu ngân sách, nên check sẽ INCONCLUSIVE ngay cả khi có số. |
| **Exploitability / V_BR trên trục H18 và K_d** | Lượt eval này không chạy `h18-br` / `kd-br`. `eval-pass1/br.jsonl` là **7,8 GB dở dang của lượt bị kill, đã khai không phải kết quả** → không đọc. |
| **Thống kê H18 ở ρ = 1 cho mọi mức < b1** | Lệch đã khai: `FLAG_COMMIT_SUFFICES` loại ρ = 1 khỏi khối h18 ở mọi mức ≠ b1. (Kiểm định b1 tại ρ = 1 **thì đo được**.) |
| **Biên H18 trên đủ 4 hệ H18** | `block-schedule` vắng trên eval **đúng như** trên dev → biên chỉ trên 3/4 hệ. |
| **H20** (rule N, cột attacker chọn Δ) | Lượt eval này **không có khối `attacker-delta`** nào (grant thứ tư chạy `h18` + `kd`). V_S − V_B1 không lập được. Trên dev, check này TBD vì **lý do khác**: khối có, nhưng `attackers.br_systems` trim cột đó về lớp Sentinel nên **không có bản ghi B1**. → **KHÔNG ĐO**, không phải 0, không phải INCONCLUSIVE. |
| **Sáu thế giới độ nhạy + khối seed2-pairs** (dev §10.4) | Không có khối `sens:*` / `seed2-pairs` trong lượt eval này. |
| **Tái lập float dev `0,8980696428571429`** (alias_check) | Đó là số dev. Phía eval có alias_check riêng: `0,8805822291877743`, `identical: true`. Một lượt held-out không thể tái lập một float dev. |

---

## 5. Tái lập

```sh
cd auditgame
../.venv/bin/python tools/v3_p5_h18_heldout.py --check-freeze     # ghim, không đổi gì
../.venv/bin/python tools/v3_p5_h18_heldout.py --dev-selfcheck    # 56/56 khớp h_verdicts.json
../.venv/bin/python tools/v3_p5_h18_heldout.py --run              # ghi h_verdicts_eval.json
```

Script từ chối chạy nếu `freeze_v3` không clean, nếu digest manifest / `rules_digest` /
`grid_digest` rời ghim Gate 4, hoặc nếu `records.sha256` không verify. Mỗi tệp được **stream
từng dòng** và chiếu ngay xuống 14 trường metric đọc (+ `loss`); `c_traj`, `audits`,
`quarantines`, `world`, `decision_log_sha256` **không bao giờ** vào bộ nhớ. Toàn bộ ba khối
(1,5 GB bản ghi) chạy trong ~15 giây.
