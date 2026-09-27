# Sentinel v3 P2 — số episode của lưới sau khi cắt BR (T22)

27/09/2026. Số liệu sinh bằng `cd auditgame && ../.venv/bin/python -m v3.grid --report`. Lưới nằm trong `auditgame/v3/grid.py`, và định nghĩa của nó được hash vào manifest v3 (`v3/freeze_v3.py`). Không có lượt eval nào được chạy. Số của tập eval chỉ đọc **hình dạng** đã ghim (`corpus.EVAL_SUMMARY_PINNED`, tức histogram của H), không đọc instance nào.

## Kết luận trước

- **Mô hình đếm tái lập đúng P0.** Tính bằng thiết kế của P0 (không cắt, không loại ô) trên đơn vị workflow của P0 (split phụ, 26 workflow), cả 6 khối khớp bảng §3 của `v3-p0-chi-phi.md` tới từng episode. Rollout headline khớp §6.2: 7.638 + 18.650 episode, 47 / 129 CPU-giờ ở R = 16. Test `test_p0_model_reproduces_the_p0_cost_table` khoá điều này.
- **Sau khi cắt theo mục 8, lõi đạt nghiệm thu T22 trên đơn vị của P0: 11,48 triệu ≤ 16,39 triệu (−30%).** Khối H18 giảm 78%, nhiều hơn mức "khoảng 70%" plan ghi, vì các ô ρ = 1 ở ba mức B_min bị loại. Khối K_d giảm 62%, khối độ nhạy giảm 20%.
- **Hai thứ làm số thật lớn hơn đơn vị của P0. Chúng không phải phần cắt, và cần người dùng biết:**
  1. **Lưới ε của BR giữ {0,3; 0,6; 1,0}** (quyết định tác giả, chờ người dùng). P0 đếm mỗi vị trí (k, ι) một lần. `br_menu` của T7 thì đếm mọi ε khả thi. Trên dev, số phần tử menu khả thi gấp 1,42 (ở Δ = 8) tới 2,31 lần (ở Δ = 0) số vị trí. Với hệ số đó, lõi đã cắt tăng lên 17,2 triệu, **vượt P0 5%**. Cận trên (mọi ε đều khả thi) là 23,7 triệu.
  2. **Tập eval chính đã đổi sang SWE-rebench-V2, 96 workflow (D-v3-1), sau khi P0 tính.** Trên tập này, lõi đã cắt là 43,3 triệu episode theo đơn vị P0, và 65,5 triệu nếu hiệu chỉnh ε theo dev. Phần mô phỏng vẫn rẻ: 9,5–20 CPU-giờ. Cái đắt lên là **rollout headline, vì nó tỉ lệ với số workflow**: ở R = 16 là 797 CPU-giờ (P0 tính 176); ở R = 64 là 3.189 CPU-giờ (P0 tính 706). Ngân sách lõi 509–1.039 CPU-giờ của Q13 vì vậy chỉ còn đúng cho split phụ. Trên split chính, cần chọn giữa ba hướng: R nhỏ hơn, rollout một mẫu con workflow, hoặc nới ngân sách.
- Chưa tính (như P0): dựng bảng dòng 5 (77–309 CPU-giờ, chạy trên dev, không phụ thuộc số workflow eval) và tinh chỉnh trên dev.

## Bảng theo khối

Các cột:
- **P0 báo cáo:** số trong `v3-p0-chi-phi.md`.
- **Mô hình P0:** số tái tính từ lưới bằng thiết kế của P0.
- **Sau cắt:** áp phần cắt của mục 8 cộng việc loại ô H18. Tính theo ba cách:
  - *đơn vị P0*: một episode cho mỗi vị trí 4(H − Δ);
  - *menu đủ ε*: nhân thêm |BR_EPS| = 3, và nhân 2 kênh ở thế giới ingress ẩn (cận trên);
  - *khả thi trên dev*: nhân tỉ lệ menu khả thi / vị trí đo trên dev theo từng Δ.

Mọi cột dùng 10 seed và nhân tỉ lệ sống sót 0,62 (GĐ 3 của P0). Runner v3 áp đúng bộ lọc này (`survives` của v2, N4) trong `run_chain_t6`.

### Split phụ (26 workflow, đơn vị của P0)

| Khối P0 | P0 báo cáo | Mô hình P0 | Sau cắt, đơn vị P0 | Sau cắt, menu đủ ε | Sau cắt, khả thi trên dev |
|---|---|---|---|---|---|
| 1. Lưới chính | 3.049.805 | 3.049.805 | 3.049.805 | 3.049.805 | 3.049.805 |
| 2. Best response | 4.037.837 | 4.037.837 | 4.037.837 | 12.113.510 | 7.898.260 |
| 3. Attacker chọn Δ | 1.514.189 | 1.514.189 | 1.514.189 | 4.542.566 | 2.961.847 |
| 4. Độ nhạy | 1.944.320 | 1.944.320 | 1.551.488 | 2.055.424 | 1.755.294 |
| 5. Trục K_d | 421.203 | 421.203 | 159.315 | 308.512 | 202.356 |
| 6. H18 | 5.423.264 | 5.423.264 | 1.172.147 | 1.649.894 | 1.366.451 |
| **Tổng lõi** | **16.390.618** | **16.390.618** | **11.484.781** | **23.719.712** | **17.234.013** |

CPU-giờ mô phỏng lõi, với Sentinel tra bảng (0,94 ms mỗi episode) và baseline 0,66 ms: 2,5 / 5,3 / 3,8. Rollout headline (ngoài lõi) theo R = 16 / 32 / 64: held-out 47 / 94 / 188 CPU-giờ; BR 129 / 259 / 517 CPU-giờ.

### Split chính (96 workflow, SWE-rebench-V2)

| Khối P0 | Mô hình P0 | Sau cắt, đơn vị P0 | Sau cắt, menu đủ ε | Sau cắt, khả thi trên dev |
|---|---|---|---|---|
| 1. Lưới chính | 10.999.296 | 10.999.296 | 10.999.296 | 10.999.296 |
| 2. Best response | 15.765.658 | 15.765.658 | 47.296.973 | 30.704.168 |
| 3. Attacker chọn Δ | 5.912.122 | 5.912.122 | 17.736.365 | 11.514.063 |
| 4. Độ nhạy | 7.187.734 | 5.678.902 | 7.721.430 | 6.494.637 |
| 5. Trục K_d | 1.619.341 | 613.453 | 1.229.286 | 788.731 |
| 6. H18 | 20.932.390 | 4.284.646 | 6.165.478 | 5.042.199 |
| **Tổng lõi** | **62.416.541** | **43.254.077** | **91.148.829** | **65.543.095** |

CPU-giờ mô phỏng lõi: 9,5 / 20,2 / 14,5. Rollout headline theo R = 16 / 32 / 64: held-out 183 / 366 / 732 CPU-giờ; BR 614 / 1.229 / 2.457 CPU-giờ. Đĩa: khoảng 525 byte mỗi record (P0 §6), nên 43–66 triệu record chiếm 23–34 GB.

Ngoài lõi, trên split chính (đơn vị P0):
- A7 và stage (C1, C2, chạy sau lõi): mỗi thế giới 1,22 triệu held-out cộng 0,15 triệu BR;
- khối 4\*: 0,15 triệu.

## Phần cắt và các quyết định đã áp

Phần cắt đọc từ `attackers.br_systems` / `BR_TRIMS` của T7, import chứ không chép:
- **lưới chính:** mọi hệ thống, detector headline, mọi (ρ, χ, Δ);
- **cột attacker chọn Δ:** 6 hệ thống lớp Sentinel;
- **độ nhạy và K_d:** B1 và Sentinel, chỉ ở Δ ∈ {4, 8};
- **H18:** chỉ ở χ = 1,33 và {b1, 2 × B_min};
- **gieo 2 carrier:** khối cặp vị trí tắt trong lõi.

Ở H18, ô b1 với χ độ sâu trông giống ô lưới chính đối với `br_systems`. Vì vậy `grid.h18_br` áp luật H18 cho ô đó: chỉ lịch khối mới được thêm BR ở χ = 1,33. Còn B1, Sentinel và B2 ở b1 thì đã có trong khối BR chính.

**Hai quyết định của tác giả (Claude đề xuất, chờ người dùng):**
1. **Lưới ε của BR giữ {0,3; 0,6; 1,0}.** Giá của nó là hai cột "menu" ở trên.
2. **Không cắt BR ở cột "attacker chọn Δ" của thế giới tổn hại gỡ được.** `br_systems` trả "none" cho ô này. Lưới vì vậy giữ nó như một ngoại lệ khai báo, `UNTRIMMED_ATTACKER_DELTA = {"reversible": ("Sentinel",)}`, theo GĐ 9 của P0. Khối này có 84.122 episode trên đơn vị P0 và 328.451 trên split chính.

**Ô bị loại khỏi H18** (N3; lý do lưu trong `grid.dropped()`), tổng 220 ô:
- 160 ô có Δ = 0 hoặc thuộc cột attacker. B_min không xác định ở đó (`BudgetUndefined`).
- 60 ô có ρ = 1 ở detector mid, tại ba mức B_min. `bmin` gắn cờ COMMIT_SUFFICES cho các ô này: B_min = 0, nên mọi bội của nó đều là ngân sách 0. Mức b1 ở ρ = 1 vẫn được giữ.

33 ô vi phạm điều kiện cửa sổ của Định lý 5.6(i), chủ yếu ở Δ = 1 (và ở Δ = 2 với χ = 2,11). Các ô này được giữ lại và mang cờ WINDOW trong `Unit.flags`: không policy nào đạt R(α) ở đó.

## Smoke trên dev với runner T6

`tools/v3_run.py` chạy các khối main, br, h18, h18-br, kd và sens:reversible trên runner của T6, với các hệ thống xây được hôm nay (B1, B2, B3, B4, B6, Oracle, lịch khối), 1 seed và 5 workflow dev. Kết quả: 162.926 episode trong 340 giây đơn luồng, tức khoảng 2,1 ms mỗi episode. Con số này gồm cả lập menu BR, kiểm record và ghi JSON, nên chưa phải số đo của riêng runner.

Đối chứng D28 trên mẫu nhỏ này **không đạt ở vế dương**: Oracle cho V = 0,67 ở Δ ∈ {4, 8}, trong khi ngưỡng là ≤ 0,05. Vế âm đạt. Mẫu 5 workflow × 1 seed quá nhỏ để kết luận. Nhưng đây đúng là loại lệch mà M1 phải xem trong thế giới, không phải trong tham số.

Smoke toàn lưới vẫn chưa chạy được. Còn thiếu:
- lớp Sentinel (T15);
- B7 (T21);
- Sentinel-rollout (T19);
- thế giới stage (T20).

## Rollout headline sau quyết định 27/09

Rollout headline chạy R = 16 trên một mẫu con khai trước: 30 workflow đầu tiên của split eval chính theo thứ tự ghim của T10 (`sequence.workflow_order`). Mẫu con được ghim trong `v3/grid.py` (`HEADLINE_ROLLOUT_WORKFLOWS`, sha256 thứ tự `11239b71e085…`) chỉ bằng id và số đếm. Histogram H của 30 workflow: {6: 4, 7: 4, 8: 3, 9: 1, 10: 3, 11: 6, 12: 2, 13: 4, 14: 3}. `grid.chain_workflows` chỉ áp mẫu con cho khối headline-rollout trên split chính.

| Rollout headline | held-out | BR | Tổng |
|---|---|---|---|
| R = 16, cả 96 workflow (trước quyết định) | 183 | 614 | 797 |
| **R = 16, mẫu con 30 workflow** | **59** | **194** | **253** |
| R = 64, mẫu con 30 workflow | 237 | 776 | 1.013 |

Đơn vị là CPU-giờ rollout, theo mô hình P0 §2 (`grid.headline_rollout_hours`).

## Đo lại chi phí bảng dòng 5 dưới tải chuẩn (matched load)

27/09/2026. Chỉ chạy dev. Mục tiêu (P2 mục 4): đưa ra **một** hằng số chi phí bảo vệ được cho bản dựng bảng dòng 5 đầy đủ, đo dưới tải có kiểm soát/đối sánh, và cập nhật lại ước lượng. Lý do phải đo lại: pilot của T14 chạy khi máy đang có tải khác (load ≈ 25/10 nhân) nên báo cáo hệ số phồng ms/rollout ≈ 1,85× so với đo đơn luồng lúc rảnh; hai pilot (T14 và line5-se-diff) chạy dưới tải KHÁC nhau nên ms/rollout của chúng không so sánh trực tiếp được, và con số 223,7 CPU-giờ (sau khi đổi cổng sang SE hiệu giữa member ở nhánh line5-se-diff, đã merge) đặt trên một hằng số chi phí không chắc.

**Kết luận trước.**

- **Đơn vị chiếu phải là CPU-giây/rollout (`time.process_time`), không phải wall/rollout.** `value_job` trong `tools/v3_build_table.py` ghi `cpu = time.process_time()`; `extrapolate()` và dòng in "CPU … h" cộng đúng đại lượng này. Bản chiếu 223,7 CPU-giờ cũng dựng từ process_time. Đây là mấu chốt: hệ số 1,85× mà báo cáo cũ lo ngại là hiện tượng của **wall-clock** khi chạy song song, **không** đi vào CPU-giờ.
- **Hằng số đề nghị: ≈ 2,9 ms/rollout (CPU, đo ở đúng `--jobs 10` của bản dựng P4), tức ≈ 225 CPU-giờ cho bản đầy đủ.** Đo lại bằng chính công cụ (`--pilot --extrapolate`) ở `--jobs 10` cho **225,1 CPU-giờ** (51.596 khoá filled × 5.376 rollout/khoá = 277,4 triệu rollout; 0% khoá bù dưới cổng CRN diff-SE, ngưỡng 0,15 đã merge) — **tái lập gần khít** con số 223,7 CPU-giờ của line5-se-diff (lệch 0,6%; số khoá 51.596 so với 51.366 do đã nối chiều dài payload của T24 vào lưới, c10bd9e). Bản chiếu cũ vì vậy **bảo vệ được**, không lệch 1,85×.
- **Hệ số phồng do song song, trên CPU-time, chỉ 1,05×** (đo back-to-back đơn luồng vs `--jobs 10`, cùng tập khoá). Phồng của **wall**/rollout dưới `--jobs 10` là 1,2–1,9× tuỳ tải nền — đây chính là "1,85×" mà báo cáo cũ thấy, và nó là hệ quả của **độ song song/tranh chấp lịch**, không phải công CPU tăng.

### Máy và phương pháp

Máy: 10 nhân (`os.cpu_count() = 10`). Mọi số đo dưới đây ghi kèm load average lúc đo (N3: không ghi 0 cho thứ không đo; ghi rõ điều kiện). **Hạn chế đo (N3):** suốt phiên máy dùng chung có ≈ 8 tiến trình python ngoài chạy 100% (các worktree/agent khác), load nền dao động 4–95; **không lấy được nền máy rảnh thật**. Vì vậy mức tuyệt đối của CPU-giây/rollout vẫn trôi theo tải nền (đo được h = 6: ≈ 1,8 ms/rollout lúc load ≈ 3, lên ≈ 2,9 ms/rollout lúc tranh chấp). Hệ số song song (tỉ số back-to-back) ít bị ảnh hưởng hơn vì hai lần đo có tải nền gần trùng.

Vi chuẩn (microbenchmark) đo phase C (`value_job`) trên một ô bảng (ρ = 0, χ = 1,33, mid), Δ̂ = 4: chạy phase A+B rồi lấy tập con 2 khoá mỗi h (h = 1..14, 28 khoá, 150.528 rollout), chạy (a) đơn luồng trong tiến trình rồi (b) qua `ProcessPoolExecutor(10)` trên **cùng** tập khoá, có luồng nền lấy mẫu `os.getloadavg()`. Đối chứng công cụ: `--pilot --headline --rhos 0 --deltas 4 --jobs 10` (274 khoá, tái lập quy mô một ô của T14) rồi `--sources-only` (36 ô, phân bố h của toàn lưới) và `--pilot --extrapolate` (chiếu bằng chính `extrapolate()`).

### Số đo vi chuẩn (28 khoá, 150.528 rollout)

| Chế độ | CPU (s) | ms/rollout (CPU) | wall/CPU mỗi khoá | load (min/mean/max) | song song hiệu dụng |
|---|---|---|---|---|---|
| Đơn luồng | 414,1 | 2,75 | 1,06 | 3,64 / 16,95 / 26,77 | — |
| `--jobs 10` | 435,9 | 2,90 | **1,94** | 19,74 / 34,62 / 44,29 | 4,26× |

- **Hệ số phồng song song trên CPU-time = 2,90 / 2,75 = 1,05×.** Theo h: ≈ 1,6 ở h = 1 (chi phí cố định lấn át khoá rẻ) giảm còn ≈ 1,02 ở h = 14 (khoá đắt, chiếm phần lớn chi phí); trọng số theo chi phí ≈ 1,07.
- **wall/CPU mỗi khoá nhảy từ 1,06 (đơn luồng) lên 1,94 (`--jobs 10`):** worker bị deschedule khoảng nửa thời gian khi máy quá tải (10 worker + ≈ 25 tiến trình ngoài trên 10 nhân). Đây là nguồn của "1,85×" trong báo cáo cũ; nó **không** vào CPU-giờ.

### Chi phí CPU mỗi rollout theo h (đối chứng công cụ, `--jobs 10`)

Từ `mean_cpu_s_per_key_by_h` của pilot công cụ chia cho 5.376 rollout/khoá:

| h | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ms/rollout (CPU) | 0,85 | 1,25 | 1,76 | 2,06 | 2,52 | 2,88 | 3,23 | 3,71 | 3,90 | 4,24 | 4,65 | 4,97 | 5,32 | 5,54 |

Pilot công cụ này (274 khoá, `--jobs 10`): CPU 1,18 giờ, wall 0,14 giờ (8,4 phút) — song song hiệu dụng 8,2× vì lần chạy này bắt đầu lúc load ≈ 4 (thấp hơn vi chuẩn), trong khi CPU/khoá vẫn ≈ 15,5 s như lúc tải nặng → **CPU-time bền với tải, wall/độ-song-song mới là thứ đổi theo tải.** 0% khoá bù (cổng CRN diff-SE), khớp line5-se-diff.

### Ngoại suy bản đầy đủ (36 ô × 5 Δ̂)

Phân bố khoá theo h của toàn lưới (`--sources-only`, `spikes/v3-table/sources.json`, 51.596 khoá filled): h1–7 mỗi mức ≈ 4.500–4.700, giảm dần còn 2.632 (h12), 1.590 (h13), 350 (h14). Rollout/khoá = R(32) × 28 member × 6 lớp = 5.376; tổng 277,4 triệu rollout, 0% bù.

| Cơ sở hằng số | ms/rollout (CPU, trọng số chi phí) | CPU-giờ bản đầy đủ |
|---|---|---|
| Đối chứng công cụ `--jobs 10` (`extrapolate()`) | **2,92** | **225,1** |
| Vi chuẩn `--jobs 10` (tính tay theo h) | 2,55 | 196,8 |
| Vi chuẩn đơn luồng (tính tay theo h) | 2,39 | 184,3 |
| line5-se-diff cũ (jobs 8, load ≈ 3) | 2,92 | 223,7 |

Chênh giữa 196,8 (vi chuẩn) và 225,1 (công cụ) là do tải nền và pha h khác nhau giữa hai lần đo, không do phương pháp; cả hai đều nằm quanh ước lượng gốc P0/plan 77–309 CPU-giờ và quanh 223,7. **Wall-clock ở `--jobs 10`:** ≈ 27 giờ nếu giữ song song 8,2× (như pilot công cụ lúc load thấp), lên ≈ 53 giờ khi tranh chấp nặng (song song 4,26×).

### Hằng số nên dùng và lý do

Dùng **CPU ms/rollout ≈ 2,9 đo ở đúng `--jobs 10`** (→ **≈ 225 CPU-giờ**, và ≈ 27–53 giờ wall tuỳ tải nền). Lý do:

1. Đơn vị chiếu là `process_time`, nên phải đo bằng `process_time`; hệ số 1,85× là của **wall** và không đi vào CPU-giờ.
2. Đo ở đúng concurrency mà bản dựng P4 chạy (`--jobs 10`), đã bao gồm tranh chấp song song (chỉ 1,05× trên CPU-time), nên hằng số ổn định.
3. Con số 225,1 tái lập line5-se-diff 223,7 trong 0,6% dù đo ở tải và jobs khác → xác nhận 223,7 là ước lượng bảo vệ được, hơi thiên **an toàn** (cận trên) cho máy đang tranh chấp; cận dưới lúc máy rảnh (đo được ≈ 1,8 ms/rollout ở h = 6, load ≈ 3) rơi vào khoảng ≈ 180 CPU-giờ.

Khi dựng bản cuối ở P4, ghi lại loadavg lúc chạy kèm bản chiếu; nếu load nền < 5, chi phí CPU thực sẽ ở cận dưới của khoảng này.

### Tái lập

```
cd auditgame
../.venv/bin/python tools/v3_build_table.py --sources-only --jobs 8                        # phân bố h toàn lưới
../.venv/bin/python tools/v3_build_table.py --pilot --headline --rhos 0 --deltas 4 --jobs 10 # pilot một ô, ghi CPU/khoá theo h
../.venv/bin/python tools/v3_build_table.py --pilot --extrapolate                           # 225,1 CPU-giờ (jobs 10)
```

So sánh đơn luồng vs `--jobs 10` (hệ số phồng song song trên CPU-time) làm bằng vi chuẩn tạm trong scratchpad (không commit); phương pháp: lấy tập con khoá cố định, chạy `value_job` một lần đơn luồng rồi một lần qua `ProcessPoolExecutor(10)`, so `cpu_s / rollouts` của hai lần.
