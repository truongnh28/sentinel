# Sentinel v3 P2 — bảng dòng 5, bản pilot trên dev (T14)

27/09/2026. Chỉ chạy trên dev (corpus v2, 100 workflow), không chạm eval. Mã: `auditgame/v3/line5_table.py` (ngăn, schema, tra bảng, `table_digest()`, `load_table()`) và `auditgame/tools/v3_build_table.py` (dựng bảng, `--jobs`). File bảng và các báo cáo JSON nằm ở `auditgame/spikes/v3-table/` (thư mục tự bỏ qua trong git, không commit).

## Kết luận trước

- **Pilot:** 3 ô bảng headline (ρ ∈ {0; 0,5; 1}, χ = 1,33, detector mid) × Δ̂ = 4 × mọi h. Dựng được 822 khoá có trạng thái nguồn, trong 58 phút thật với `--jobs 8`, tốn **7,09 CPU-giờ**. Máy đang chạy tải khác song song: load average khoảng 25 trên 10 nhân. Vì vậy giá mỗi rollout đo được trong pilot cao hơn đo đơn luồng lúc máy rảnh khoảng 1,85 lần: 2,97 so với 1,61 ms ở h = 6.
- **SE không đạt ngưỡng O12:** chỉ 12% số khoá có SE lớn nhất ≤ 0,09. Có 92% khoá phải bù lên R = 64, và 88% vẫn vượt ngưỡng sau khi bù. SE trung vị là 0,20; theo h, SE tăng từ 0,07 (h = 1) lên 0,28 (h = 14). Nguyên nhân: loss của Định nghĩa 1 không bị chặn bởi 1, vì còn λ_Q·FQ và λ_T·số patch sạch bị mất khi gỡ branch. Muốn SE ≤ 0,09 ở h ≥ 6 cần R khoảng 300–600, tức giá gấp 5–10 lần. **Đây là quyết định của tác giả, không phải của T14:** nâng R, nới ngưỡng, hay dùng SE của hiệu giữa các member (số ngẫu nhiên chung).
- **Ngăn rỗng:** 51% khoá (858 trên 1.680 của các Δ̂ đã dựng) không có trạng thái nguồn và dùng ngăn gần nhất cùng h. Không khoá nào phải lùi sang h khác.
- **Ngoại suy cho bản đầy đủ** (36 ô × 5 Δ̂; phase A chạy thật trên cả 36 ô, được 51.366 khoá có trạng thái):
  - theo giá đo trong pilot, có bù R: **453 CPU-giờ**; chỉ R = 32: 230 CPU-giờ;
  - quy về máy rảnh (÷ 1,85): khoảng 245 / 124 CPU-giờ;
  - ước lượng của P0/plan là 77–309 CPU-giờ;
  - phase A (trạng thái nguồn) cho cả 36 ô tốn 0,75 CPU-giờ, chạy 6 phút 22 giây thật với 8 job.
- **Bảng so với rollout** trên 24 trạng thái dev mới (seed nguồn 3, không dùng để dựng bảng; mỗi trạng thái R = 32):
  - chênh lệch |L̂| trung bình 0,21;
  - regret trung bình khi dùng x_t của bảng, đo trên rollout, là 0,16 (lớn nhất 0,67);
  - 54% số trạng thái có regret > 0,10.

  Rollout một trạng thái cũng có SE 0,03–0,43, nên các con số này lẫn nhiễu và thiên lên. Chưa tách được sai số do ngăn (R2) khỏi sai số Monte Carlo.

## Thiết kế đã khai (DCM `v3/dcm/T14.csv`)

| Điểm | Chọn |
|---|---|
| Khoá | `table_key_id` (ρ, χ, d′; thế giới chính, K_d = 2, b1: O14, O15) × Δ̂ ∈ {0, 1, 2, 4, 8} × h = H − t ∈ 1..14 × 40 ngăn |
| Ngăn (O16) | 5 mức p_attack theo phân vị 20/40/60/80% của mọi trạng thái nguồn trong ô bảng (ngưỡng lưu trong bảng) × carrier có hậu nghiệm cao nhất × cờ "khối lượng trên carrier uỷ nhiệm > ½" |
| Trạng thái nguồn | mọi workflow dev × (6 lớp attacker + không tấn công) × seed nguồn (1, 2) (D24). Seed episode = 10·seed + chỉ số lớp. Policy hành vi: hỗn hợp đều 28 member rút mỗi task (dòng 5 với x đều trên các member trả được), dòng 7 là PF của T9 dựng với Δ̂, cộng dòng 8–9. Ghi b_t ở đầu mỗi task. Giữ tối đa S = 32 trạng thái mỗi khoá, theo thứ tự `seed_of` |
| Giá trị (O12) | R = 32 lần rút cho mỗi (member, lớp), chia vòng tròn cho các trạng thái của khoá. Mỗi lần rút là một giả thuyết lấy từ b_t của trạng thái, dùng chung cho mọi cặp (member, lớp). SE = sd/√n. SE > 0,09 thì bù một lần lên R = 64; vẫn vượt thì bật `se_flag` và ghi vào note của lookup |
| Ngăn rỗng (O16, N3) | ngăn gần nhất cùng h (khoảng cách = \|Δmức\| + [khác carrier] + [khác cờ]; hoà thì lấy chỉ số nhỏ hơn). Không có ngăn nào ở h đó thì lùi sang h gần nhất (mở rộng O16, đã khai). Δ̂ chưa dựng thì raise `KeyError` |
| PF | `MOVE_ON_ALARM` bật khi chạy và phát lại episode nguồn (b_t là belief của chính Sentinel), **tắt trong rollout**: một rollout đo được 2,8 → 1,5 ms. T9 đo được move chỉ có tác dụng ở khoảng 1/500 bước |
| Band của BT | `band_prop61(p0, f)` với f là phần không thông tin được khi chỉ quan sát commit. T15 phải dùng cùng band |
| Dòng 8–9 | τ, η_Q đã tinh chỉnh của T18 (`--tuned`). **Pilot dùng giá tạm (0,5; 0,1)**, có ghi trong meta. Build không phải pilot sẽ từ chối nếu thiếu `--tuned` |
| Digest | `table_digest()` băm nội dung (tên mảng, dtype, shape, bytes), không băm file zip. Bảng chưa dựng thì trả `None` |
| Lưu trữ | `spikes/v3-table/v3_line5_table.npz` (bản vận hành, P4) và `v3_line5_table_pilot.npz`. Khác đường `reference/` trong plan để khỏi sửa `.gitignore` gốc; thư mục có `.gitignore` riêng |

Pilot digest: `sha256:1198b5e42cdf06261b0175d51e56c761c9f66ef2964397c970cc6744409669be` (file 0,56 MB nén; bản đầy đủ ước khoảng 20 MB nén).

## Số đo pilot theo h (ô ρ ∈ {0; 0,5; 1}, Δ̂ = 4, 8 job, máy có tải)

| h | khoá | CPU-giây/khoá | ms/rollout | SE trung vị | tỉ lệ SE ≤ 0,09 | số trạng thái trung vị |
|---|---|---|---|---|---|---|
| 1 | 82 | 6,6 | 0,79 | 0,071 | 0,63 | 21,5 |
| 2 | 78 | 12,9 | 1,28 | 0,120 | 0,31 | 32 |
| 3 | 81 | 17,6 | 1,72 | 0,137 | 0,20 | 32 |
| 4 | 71 | 22,4 | 2,13 | 0,171 | 0,10 | 32 |
| 5 | 71 | 28,4 | 2,65 | 0,187 | 0,03 | 32 |
| 6 | 70 | 32,0 | 2,97 | 0,196 | 0 | 32 |
| 7 | 79 | 37,1 | 3,45 | 0,194 | 0 | 26 |
| 8 | 66 | 41,7 | 3,88 | 0,220 | 0 | 22,5 |
| 9 | 60 | 44,1 | 4,10 | 0,231 | 0 | 15 |
| 10 | 51 | 47,5 | 4,42 | 0,238 | 0 | 12 |
| 11 | 46 | 50,9 | 4,73 | 0,245 | 0 | 15,5 |
| 12 | 40 | 53,7 | 5,00 | 0,258 | 0 | 14 |
| 13 | 21 | 54,9 | 5,11 | 0,262 | 0 | 16 |
| 14 | 6 | 55,1 | 5,13 | 0,279 | 0 | 20,5 |

Theo từng ô bảng (560 khoá mỗi ô ở Δ̂ = 4):

| Ô bảng | có trạng thái | ngăn gần nhất | bù R = 64 | vẫn vượt 0,09 | SE lớn nhất |
|---|---|---|---|---|---|
| ρ = 0 | 275 | 285 | 252 | 237 | 0,293 |
| ρ = 0,5 | 278 | 282 | 258 | 249 | 0,303 |
| ρ = 1 | 269 | 291 | 243 | 235 | 0,293 |

(Ánh xạ ô → `table_key_id` nằm trong meta của bảng.)

Không chạy ρ = 0,25 và Δ̂ khác 4: pilot được giới hạn khoảng 1 giờ thật. Phase A cho thấy mỗi (ô bảng, Δ̂) có 269–300 khoá có trạng thái; số này gần như không đổi theo ρ và Δ̂.

## Tái lập

```
cd auditgame
../.venv/bin/python tools/v3_build_table.py --sources-only --jobs 8                       # 36 ô, 6 phút
../.venv/bin/python tools/v3_build_table.py --pilot --headline --rhos 0 0.5 1 --deltas 4 --jobs 8
../.venv/bin/python tools/v3_build_table.py --pilot --extrapolate
../.venv/bin/python tools/v3_build_table.py --pilot --fidelity 24 --jobs 8
```

## Việc còn mở

1. ~~**O12 không đạt ở R = 32–64**~~ — đã chốt 27/09/2026, xem mục dưới (line5-se-diff).
2. Dòng 8–9 trong pilot dùng giá tạm. Bản cuối đọc `reference/v3_tuned.json` của T18.
3. `seal.reasons` so digest của Gate-4 với `table_digest()`. Nếu bảng chưa dựng, `table_digest()` trả `None`, nên một file Gate-4 ghi `null` sẽ lọt qua. Đề nghị T2/T23 cho seal từ chối khi digest sống là `None`. T14 không sửa `seal.py`.

## 27/09/2026 — line5-se-diff: đổi cổng O12 sang SE của hiệu giữa các member

Quyết định của tác giả (không phải T14): pilot ở trên cho thấy ngưỡng SE tuyệt đối 0,09 không đạt được ở R = 32–64 (88% khoá vẫn vượt sau khi bù). Cổng bù đổi sang **SE của HIỆU giữa hai member gần nhau nhất** (member đạt argmin theo ước lượng điểm và đối thủ gần nhất), tính từ hiệu từng cặp lượt rút (không gộp hai SE độc lập) — đây đúng là đại lượng dòng 5 cần (member nào tốt hơn), không phải giá trị loss tuyệt đối.

**Xác nhận số ngẫu nhiên chung (CRN).** Đọc `v3/rollout.py` và `tools/v3_build_table.py::draws()`: trong một lượt rút r, MỌI (member, lớp) dùng chung một giả thuyết hạt (`hyp = belief.sample(1, seed_of(DRAW_TAG, ..., r))`, rút một lần cho cả 6 lớp), một seed thế giới (`seed_of(WORLD_TAG, wf_id, seed, t, r)` — không phụ thuộc member lẫn lớp) và một seed ngẫu nhiên hoá riêng của member (`seed_of(MEMBER_TAG, wf_id, seed, t, r)` — không phụ thuộc tên member). CRN được chia sẻ **đầy đủ**, không phải một phần. Đo thực nghiệm trên một trạng thái dev thật (4–6 member, 2 lớp, R = 32, nhiều h): tỉ lệ SE(hiệu cặp) / sqrt(SE_i² + SE_j²) (mức giảm so với gộp hai SE độc lập) trung bình **0,86** ở h thấp và giảm dần còn **0,6–0,7** ở h ≈ 7, nghĩa là mức giảm phương sai từ CRN **khiêm tốn** (14–40%), không phải gần triệt tiêu như lý thuyết CRN lý tưởng — vì các member có chính sách khác nhau, hành động khác nhau làm kho lưu trữ rẽ nhánh sớm dù cùng seed. Quyết định "đổi cổng sang SE hiệu" vẫn hợp lý vì đại lượng liên quan (khoảng cách giữa hai member gần nhất trong xếp hạng minimax) có quy mô khác hẳn SE tuyệt đối của một loss không bị chặn, không phải vì CRN triệt tiêu gần hết nhiễu.

**Ngưỡng mặc định.** `config.TABLE_DIFF_SE_MAX = 0,15` (tham số dòng lệnh `--diff-se-max`), chọn từ phân phối diff-SE đo trên mẫu dev nhỏ theo h (R = 32, 4–6 member, 2 lớp): trung vị 0,02–0,10 ở mọi h, đỉnh đo được 0,17 ở h lớn. 0,15 để lọt phần lớn khoá ở R = 32, chỉ bù cho đuôi nhiễu nhất — khác hẳn 0,09 cũ vốn không khớp quy mô của loss không bị chặn.

**Pilot lặp lại cùng quy mô T14** (3 ô headline ρ ∈ {0; 0,5; 1}, χ = 1,33, mid detector, Δ̂ = 4, mọi h, `--jobs 8`):

| Số đo | T14 (SE tuyệt đối) | line5-se-diff (SE hiệu) |
| --- | --- | --- |
| Khoá dựng | 822 | 822 (giống hệt) |
| CPU-giờ pilot | 7,09 | **3,50** |
| Giờ thật (wall) | 0,97 (58 phút) | **0,46** (28 phút) |
| Khoá bù lên R = 64 | 92% | **0%** |
| Khoá vẫn vượt ngưỡng sau bù | 88% | **0%** |
| SE trung vị | 0,20 (tuyệt đối) | diff-SE trung vị **0,050**; SE tuyệt đối (chẩn đoán phụ) trung vị vẫn 0,118, `se_flag` ở 75% khoá |

Không khoá nào cần bù ở quy mô pilot này: mọi diff-SE (kể cả đỉnh 0,146 ở h = 12) đều dưới ngưỡng 0,15, kể cả tại h = 14 (đỉnh cũ của SE tuyệt đối, 0,28). Theo h: diff-SE trung vị tăng đều 0,00 (h=1) → 0,097 (h=14), đỉnh 0,146 ở h=12 — dưới ngưỡng ở mọi h đo được, còn nhiều biên an toàn (≈ 0,03 ở đỉnh). SE tuyệt đối (chẩn đoán phụ, không còn là cổng) vẫn tăng 0,061 → 0,163, giống hệt pilot T14, và vẫn được ghi vào bảng và vào `note` của `lookup()`.

**Ngoại suy cho bản đầy đủ** (36 ô × 5 Δ̂, 51.366 khoá có trạng thái, dùng `tools/v3_build_table.py --pilot --extrapolate`):

- **223,7 CPU-giờ** (không có khoá nào bù, nên bằng con số "chỉ R = 32" là 223,9 CPU-giờ) — so với 453 CPU-giờ có bù / 230 CPU-giờ chỉ R = 32 của T14. Giảm gần **một nửa** so với ước lượng có bù của T14, và xấp xỉ ước lượng "chỉ R = 32" của T14 (khớp, vì không còn khoá nào cần bù).
- Lưu ý máy đo T14 có tải song song (load average ≈ 25/10 nhân, hệ số hiệu chỉnh 1,85×); pilot này đo lúc máy tương đối rảnh (load average ≈ 3/10 nhân), nên hai con số CPU-giờ không hoàn toàn cùng điều kiện tải — xu hướng (bù R giảm mạnh) là điều chắc chắn, còn con số CPU-giờ tuyệt đối nên đối chiếu lại khi dựng bản cuối ở P4 trên máy cùng điều kiện.
- Ước lượng gốc của P0/plan: 77–309 CPU-giờ — 223,7 CPU-giờ nằm trong khoảng này.

**Mã.** `v3/config.py` (`TABLE_DIFF_SE_MAX`), `v3/line5_table.py` (mảng bảng mới `diff_se`, `diff_gap`, `diff_flag`, `diff_pair`; `note` của `lookup()` nay luôn có dòng diff-SE, và dòng SE tuyệt đối chỉ khi `se_flag` — không còn gate), `tools/v3_build_table.py` (`_diff_stats`, cổng bù trong `value_job`, tham số `--diff-se-max`). Test: `tests/v3/test_alg1_line5_table.py::test_diff_se_gates_the_top_up_not_absolute_se`, `::test_diff_se_beats_combining_independent_se`. Nhánh `line5-se-diff`.
