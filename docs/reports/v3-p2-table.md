# Sentinel v3 P2 — bảng dòng 5, bản pilot trên dev (T14)

27/09/2026. Chỉ chạy trên dev (corpus v2, 100 workflow), không chạm eval. Mã: `auditgame/v3/line5_table.py` (ngăn, schema, tra bảng, `table_digest()`, `load_table()`) và `auditgame/tools/v3_build_table.py` (dựng bảng, `--jobs`). File bảng và các báo cáo JSON nằm ở `auditgame/spikes/v3-table/` (thư mục tự bỏ qua trong git, không commit).

## Kết luận trước

- **Pilot:** 3 ô bảng headline (ρ ∈ {0; 0,5; 1}, χ = 1,33, detector mid) × Δ̂ = 4 × mọi h. Dựng được 822 khoá có trạng thái nguồn, trong 58 phút thật với `--jobs 8`, tốn **7,09 CPU-giờ**. Máy đang chạy tải khác song song: load average khoảng 25 trên 10 nhân. Vì vậy giá mỗi rollout đo được trong pilot cao hơn đo đơn luồng lúc máy rảnh khoảng 1,85 lần: 2,97 so với 1,61 ms ở h = 6.
- **SE không đạt ngưỡng O12:** chỉ 12% số khoá có SE lớn nhất ≤ 0,09. Có 92% khoá phải bù lên R = 64, và 88% vẫn vượt ngưỡng sau khi bù. SE trung vị là 0,20; theo h, SE tăng từ 0,07 (h = 1) lên 0,28 (h = 14). Nguyên nhân: loss của Định nghĩa 1 không bị chặn bởi 1, vì còn λ_Q·FQ và λ_T·số patch sạch bị mất khi gỡ branch. Muốn SE ≤ 0,09 ở h ≥ 6 cần R khoảng 300–600, tức giá gấp 5–10 lần. **Đây là quyết định của người dùng, không phải của T14:** nâng R, nới ngưỡng, hay dùng SE của hiệu giữa các member (số ngẫu nhiên chung).
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

## Việc còn mở cho người dùng / các task sau

1. **O12 không đạt ở R = 32–64** (xem trên). Chọn một trong ba: nâng R (giá × 5–10); đổi cổng sang SE của hiệu giữa các member (số ngẫu nhiên chung); hoặc nới ngưỡng. Phải khai trước khi dựng bản cuối ở P4.
2. Dòng 8–9 trong pilot dùng giá tạm. Bản cuối đọc `reference/v3_tuned.json` của T18.
3. `seal.reasons` so digest của Gate-4 với `table_digest()`. Nếu bảng chưa dựng, `table_digest()` trả `None`, nên một file Gate-4 ghi `null` sẽ lọt qua. Đề nghị T2/T23 cho seal từ chối khi digest sống là `None`. T14 không sửa `seal.py`.
