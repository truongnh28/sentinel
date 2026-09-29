# Sentinel v3 — chi phí tính toán của lõi tối thiểu (P0)

27/09/2026. Đây là số để lập kế hoạch cho [sentinel-v3.md](../../sentinel-v3.md), mục Rủi ro, dòng "Khối lượng tính toán vượt dự kiến". Không có lượt eval nào được chạy. Mọi phép đo thời gian chạy trên **split dev của v2** (django, 43 workflow). Thời gian lượt eval v2 chỉ được đọc lại từ `eval-log.txt`, `eval-summary.json` và mtime của file record, không mở `eval-main.jsonl`.

Máy đo: Apple M5, 10 nhân (4 nhân hiệu năng + 6 nhân tiết kiệm), RAM 16 GB, `.venv/bin/python`.

Mỗi giả định được đánh số **[GĐ n]** và liệt kê đủ ở §7.

## Kết luận trước

- **Nếu mọi episode Sentinel chạy rollout ở dòng 5 đúng chữ, lõi tối thiểu không chạy được trên máy này.** Tùy cách đọc "rollout từ 2048 particle", tổng thời gian là 228 ngày, 600 ngày, hoặc khoảng 105 năm (§4).
- **Nếu bỏ rollout, toàn bộ lõi chỉ tốn khoảng 24 CPU-giờ**, tức khoảng 4 giờ chạy thật với `--jobs 10`. Phần mô phỏng rất rẻ: một episode B1 tốn 0,55 ms, một episode Sentinel v2 tốn 0,84 ms.
- **Dòng 5 chiếm hơn 99,9% chi phí.** Một episode Sentinel có rollout đắt hơn một episode không có rollout từ khoảng 16.000 lần (cách đọc B) tới 2,7 triệu lần (cách đọc A).
- Trong phần rollout, bốn khối lớn nhất gần ngang nhau: liệt kê best response (24%), cột "attacker chọn Δ" (24%), lưới ngân sách H18 (20%) và lưới chính (16%).
- Trong phần không rollout, tinh chỉnh trên dev chiếm 84%. Riêng việc tìm chính sách tất định cho ablation −randomization đã tốn 16 CPU-giờ.
- **Phương án đề xuất (§6) tốn khoảng 510–1.040 CPU-giờ, tức 4–8 ngày.** Sentinel dùng bảng tính trước (phương án dự phòng L1 mà doc đã khai) ở mọi ô. Rollout thật chỉ chạy ở ô headline của Table 2 và in kèm để đối chiếu.

## 1. Lượt eval v2 đo được gì

`run_draft_eval.py --jobs 10 --split eval` chạy một lần ngày 25/09. Mốc bắt đầu lấy từ dòng đầu của `eval-log.txt`. Mốc kết thúc của từng giai đoạn là mtime của file record mà giai đoạn đó ghi ra, vì file được đóng khi giai đoạn chạy xong.

| Giai đoạn | Kết thúc | Thời gian thật | Số record | Thời gian thật mỗi record |
| --- | --- | --- | --- | --- |
| Bắt đầu (`eval-log.txt`) | 16:00:46 | — | — | — |
| Lưới chính `eval-main` | 16:19:51 | 19 phút 05 giây | 8.501.064 episode | 0,135 ms |
| Best response `eval-br` | 16:25:20 | 5 phút 29 giây | 260 job (mỗi job liệt kê hàng nghìn episode) | — |
| Quét η_Q, match, drift dai dẳng | 16:26:03 | 43 giây | 245.056 | 0,18 ms |
| Quét ngân sách, thăm dò | 16:27:14 | 71 giây | 605.760 | 0,12 ms |
| Thế giới cổng (D29) | 16:27:21 | 7 giây | 61.264 | 0,11 ms |
| Tổng hợp số (D33) | 16:29:47 | 2 phút 26 giây | đọc 9,41 triệu record | — |
| **Tổng** | | **29 phút** | | |

**Độ tăng tốc thật khi chạy song song.** Lưới chính v2 có trung bình 9,75 task mỗi episode, và đo đơn luồng trên dev cho trung bình 78,8 µs mỗi task qua 13 hệ thống. Lưới chính vì vậy cần 1,81 CPU-giờ nếu chạy đơn luồng. Chạy thật mất 1.145 giây, nên độ tăng tốc thật là **5,7 lần với 10 tiến trình**. Không đạt 10 lần vì 6 trong 10 nhân của M5 là nhân tiết kiệm, và tiến trình cha phải tự ghi JSON (4,5 GB). Mọi con số thời gian thật trong báo cáo này lấy CPU-giờ chia 5,7 **[GĐ 1]**.

## 2. Chi phí mỗi episode, đo trên dev

Script `time_v2_dev.py` gọi thẳng các hàm `work`, `br_work` và `gate_work` của `run_draft_eval.py` với `split="dev"`. Nó đo `make_policy` cộng `run_carrier` cho cả 13 hệ thống, dùng 13 cột attacker (6 cột tinh chỉnh và 7 cột held-out), 5 mức Δ, 2 seed, ρ = 0,25, detector mid. Mỗi hệ thống chạy 3.315 episode. Kết quả được quy về độ dài trung bình của tập eval v3, H = 9,46.

| Loại | µs mỗi task | ms mỗi episode (H = 9,46) | Ghi chú |
| --- | --- | --- | --- |
| B1 audit-at-commit | 57,6 | 0,55 | rẻ nhất |
| B2–B6, Oracle(+) | 61–78 | 0,58–0,74 | |
| 28 member của thư viện | 86–119 (trung bình 101) | 0,96 | đây là thứ một rollout thực thi |
| Sentinel-A1 của v2 (rút member, belief cửa sổ đúng 140 cửa sổ) | 88,8 | 0,84 | 1,5 lần B1 |
| Bốn ablation của v2 | 89–97 | 0,85–0,92 | |
| Cộng particle filter 2048 hạt, viết bằng numpy (dòng 7) | +10,1 | +0,10 | nếu viết Python thuần: +171 µs |
| **Sentinel v3, chưa có rollout** | **≈ 99** | **≈ 0,94** | |
| Một episode trong liệt kê best response | như episode thường | B1 0,66; Sentinel 1,04 | Ở Δ = 4: 5.696 episode trên dev, B1 3,7 giây, Sentinel 5,9 giây |

**Rollout ở dòng 5.** Script `time_pf_rollout.py` dựng trạng thái giữa episode (store sau nửa đầu), deepcopy store và member, rồi chạy tiếp vòng lặp của `run_carrier` tới hết horizon. Đo trên 3.360 rollout:

- clone trạng thái mất 229 µs; mỗi task của rollout mất 106 µs;
- chạy rollout ở mọi task t của một episode dài H tốn H·229 + 106·H(H+1)/2 µs, tức **7,4 ms cho mỗi bộ (member, lớp attacker, lần rút)** khi H = 9,46;
- một episode Sentinel phải làm việc đó cho 28 member × N_A lớp attacker × R lần rút. Lấy N_A = 6, bằng số cột tinh chỉnh D18 của v2 **[GĐ 2]**.

| Cách đọc "rollout từ 2048 particle" | Số rollout mỗi task | Chi phí rollout mỗi episode Sentinel | So với episode không rollout |
| --- | --- | --- | --- |
| A: mỗi cặp (member, attacker) rollout từ đủ 2048 hạt | 344.064 | **2.553 giây** (43 phút) | × 2,7 triệu |
| B: tổng 2048 rollout mỗi task, chia cho 168 cặp (≈ 12 mỗi cặp) | 2.048 | **15,2 giây** | × 16.000 |
| C: 32 rollout mỗi cặp (sai số chuẩn Monte Carlo của harm nhị phân ≤ 0,09) | 5.376 | **39,9 giây** | × 42.000 |

Các phần còn lại không đáng kể: một lần giải LP hỗn hợp 28 × 30 mất 1,3 ms; một LP cỡ B7 (13 hành động × 150 cửa sổ) mất 0,9 ms; một lần rút particle mất 11 µs.

## 3. Lưới lõi v3 và số episode

**Đơn vị.** Tập eval là 26 workflow một lượt theo C14 (`spikes/v3-p0/corpus.json`), H trung bình 9,46. Ô Δ = 8 còn 18 workflow, nên trên cả trục Δ có 122 lượt (workflow, Δ). Chạy 10 seed, và 62% episode sống sót qua bộ lọc `survives` (dev đo được 62,9%) **[GĐ 3]**. Một bộ (hệ thống, cột attacker, ρ, χ, detector) trên cả 5 mức Δ vì vậy cho 756 episode. Khi liệt kê best response, v3 bỏ ràng buộc ngủ yên (C8), nên mỗi workflow có 4(H − Δ) vị trí đặt; cả 5 mức Δ cộng lại được 3.392 vị trí, tức 21.030 episode cho mỗi bộ (hệ thống, ρ, χ) **[GĐ 4]**.

**Hệ thống: 16.** Gồm B1–B7, cost-greedy, stage-weighted ngẫu nhiên, Oracle(+), Sentinel, Sentinel với Δ oracle (cận trên theo C12) và 4 ablation. Trong đó 6 hệ thống thuộc lớp Sentinel (có belief và rollout): Sentinel, Sentinel Δ-oracle và 4 ablation. Đối chứng Δ = 0 đọc từ cột Δ = 0 của B1, B3, B4, nên không tốn thêm **[GĐ 5]**. B7 dùng LP tính trước cho từng (H, ô) và được tính giá như B2 **[GĐ 6]**.

| Khối | Thiết kế | Episode | Trong đó lớp Sentinel |
| --- | --- | --- | --- |
| 1. Lưới chính | 16 hệ thống × 7 held-out × ρ 4 × χ 3 × detector 3 × Δ 5 | 3.049.805 | 1.143.677 |
| 2. Liệt kê best response | 16 hệ thống × ρ 4 × χ 3, detector headline, mọi vị trí ở mọi Δ **[GĐ 7]** | 4.037.837 | 1.514.189 |
| 3. Cột "attacker chọn Δ" | chỉ 6 hệ thống lớp Sentinel (baseline không phụ thuộc Δ nên đọc lại khối 2) × ρ 4 × χ 3, mọi vị trí ở mọi Δ **[GĐ 8]** | 1.514.189 | 1.514.189 |
| 4. Bốn độ nhạy | Mỗi công tắc (tổn hại gỡ được, ingress ẩn, drift dai dẳng, gieo 2 carrier): 16 hệ thống × 7 held-out × ρ 4, χ = 1,34, detector mid, Δ 5. Cộng best response cho B1 và Sentinel ở ba công tắc đầu, và cột chọn Δ cho Sentinel ở công tắc "tổn hại gỡ được" **[GĐ 9]** | 1.944.320 | 844.787 |
| 5. Trục K_d | 2 mức mới (K_d = 2 đã là thế giới chính, vì DELEGATED = {skill, queue}) × {B1, Sentinel} × ρ 4, χ = 1,34, detector mid, Δ 5; held-out và best response **[GĐ 10]** | 421.203 | 210.602 |
| 6. Lưới ngân sách H18 | 4 policy (B1, Sentinel, lịch khối của Mệnh đề 5.7, uniform random) × 5 mức χ (3 mức dựng bằng độ sâu, 2 mức "χ chỉ đổi giá") × 4 mức B, trừ 9 tổ hợp đã có trong lưới chính; ρ 4, detector mid, Δ ∈ {1, 2, 4, 8}; held-out và best response **[GĐ 11]** | 5.423.264 | 1.298.528 |
| **Tổng phía eval** | | **16,39 triệu** | **6,53 triệu** |
| 4*. Gieo 2 carrier, best response trên cặp vị trí (tùy chọn, không cộng vào tổng) | 6(H − Δ)² cặp mỗi workflow, B1 và Sentinel | 2.106.413 | 1.053.206 |
| 7. Tinh chỉnh trên dev | Dev là toàn bộ corpus v2 (100 workflow, H trung bình 9,93), 2 seed, 6 cột D18, mỗi ρ: (b) η_Q: 28 member × 3 kernel × 8 η × Δ ∈ {4, 8}; (c) hỗn hợp: 28 × 3 detector × 3 kernel × 5 Δ × 3 χ; (d) −randomization: 28 member × best response trên dev × 3 kernel × 3 detector × 3 χ **[GĐ 12]** | 66,18 triệu episode của member | không có rollout **[GĐ 13]** |

## 4. CPU-giờ và thời gian thật

Mô phỏng tính theo µs mỗi task đo được của từng hệ thống (§2). Rollout tính theo 7,4 ms cho mỗi bộ (member, lớp attacker, lần rút) như ở §2, nhân với 28 × 6 × R. Thời gian thật = CPU-giờ / 5,7.

| Khối | Mô phỏng, CPU-giờ | Rollout B, CPU-giờ | Rollout C, CPU-giờ | Rollout A, CPU-giờ |
| --- | --- | --- | --- | --- |
| 1. Lưới chính | 0,69 | 5.125 | 13.452 | 860.919 |
| 2. Best response | 0,96 | 7.427 | 19.497 | 1.247.806 |
| 3. Attacker chọn Δ | 0,43 | 7.427 | 19.497 | 1.247.806 |
| 4. Độ nhạy | 0,44 | 3.928 | 10.311 | 659.921 |
| 5. Trục K_d | 0,09 | 1.015 | 2.665 | 170.531 |
| 6. Lưới ngân sách H18 | 1,17 | 6.322 | 16.595 | 1.062.104 |
| 7. Tinh chỉnh dev | 19,90 | — | — | — |
| **Tổng CPU-giờ** | **23,7** | **31.245** | **82.017** | **5.249.086** |
| **Thời gian thật, `--jobs 10`** | **4,2 giờ** | **228 ngày** | **600 ngày** | **≈ 105 năm** |
| (4*) Gieo 2 carrier, cặp vị trí | 0,49 | 5.599 | 14.697 | 940.587 |

Chi tiết khối 7: (b) η_Q tốn 0,97 CPU-giờ, (c) hỗn hợp 2,98, (d) −randomization 15,95.

**Hệ số nhân nếu đổi lựa chọn:**
- Tập hai lượt (36 workflow) thay cho 26: phía eval × 1,42.
- Chạy đủ 34 cột như lưới chính v2 (18 scripted + 16 BR) thay cho 7 held-out: khối 1 × 4,9, thành 14,8 triệu episode.
- Nếu dòng 2–3 (giải chính xác belief MDP khi KH ≤ 40, tức H ≤ 10) thay rollout cho các workflow đó, chỉ còn 38% khối lượng rollout (phần của các workflow có H > 10). Nhưng giá của lời giải chính xác chưa đo được, vì chưa có code **[GĐ 14]**.
- Nếu particle filter viết bằng Python thuần thay vì numpy: phần mô phỏng của lớp Sentinel khoảng × 2,6, tổng mô phỏng tăng thêm dưới 3 CPU-giờ.

## 5. Khối nào chiếm chi phí

- **Rollout ở dòng 5 quyết định mọi thứ.** Ở cả ba cách đọc, rollout lớn hơn toàn bộ phần mô phỏng từ 1.300 lần trở lên.
- Chi phí rollout tỉ lệ với số episode lớp Sentinel (6,53 triệu). Chia theo khối: best response 24%, attacker chọn Δ 24%, lưới ngân sách H18 20%, lưới chính 16%, độ nhạy 13%, K_d 3%.
- **Best response là khối lớn nhất, vì nó nhân lên theo số vị trí.** Mỗi bộ (hệ thống, ρ, χ) cần 21.030 episode, trong khi một cột held-out chỉ cần 756, tức gấp 28 lần. Ba khối 2, 3 và 6 lớn chủ yếu vì phải liệt kê best response.
- **Khi không có rollout,** tinh chỉnh trên dev chiếm 84% (19,9 trên 23,7 CPU-giờ). Phần lớn là best response trên dev để chọn chính sách tất định cho −randomization.

## 6. Cách cắt chi phí

Ở cách đọc nhẹ nhất (B), chi phí vẫn là 228 ngày, gấp khoảng 16 lần mức hai tuần. Cả ba cách dưới đây đều cần thiết. Cách 1 và 2 là lựa chọn thiết kế, nên phải khai trong tiền đăng ký trước Cổng 4.

1. **Dùng bảng tính trước (L1) làm Sentinel ở mọi ô.** Doc đã khai phương án này là dự phòng "chỉ dùng khi rollout không tính nổi", và §4 là bằng chứng rằng rollout không tính nổi. Bảng lưu giá trị L(member, lớp attacker | ô, số task còn lại, ngăn belief) và được dựng một lần bằng rollout trên dev: 36 ô × 5 Δ × 14 độ dài còn lại × 20–40 ngăn belief × 28 × 6 × R = 32–64 lần rút. Chi phí dựng bảng là **77–309 CPU-giờ (0,6–2,3 ngày)**. Sau đó mỗi episode Sentinel chỉ còn giá tra bảng, khoảng 0,94 ms, và toàn lưới quay về khoảng 24 CPU-giờ.
2. **Chạy rollout thật chỉ ở ô headline của Table 2** (Δ ∈ {4, 8}, χ = 1,34, detector mid, 4 mức ρ). Chạy cho Sentinel, với cả 7 held-out và best response, và in cạnh bản dùng bảng để đo sai số của phương án dự phòng. Số episode là 7.638 (held-out) cộng 18.650 (best response).

   | R mỗi cặp | Held-out | Best response | Cộng 4 ablation và Δ-oracle, held-out |
   | --- | --- | --- | --- |
   | 16 (sai số chuẩn ≤ 0,125) | 47 CPU-giờ | 129 CPU-giờ | +235 CPU-giờ |
   | 32 (≤ 0,09) | 94 | 259 | +470 |
   | 64 (≤ 0,0625) | 188 | 518 | +939 |

   Ghi chú: rollout ở cách đọc A cho riêng ô headline vẫn tốn 22.575 CPU-giờ (165 ngày). Cách đọc A vì vậy không làm được ở bất kỳ phạm vi nào.
3. **Cắt các khối best response.**
   - Best response ở H18: chỉ giữ ở χ = 1,34 và b1/b2. Khối 6 giảm khoảng 70%.
   - Best response ở độ nhạy và K_d: chỉ giữ ở Δ ∈ {4, 8}.
   - Nếu mỗi particle đã mang sẵn (k, ι, σ), rollout có thể dùng chung cho cả 6 lớp attacker, tức N_A = 1. Khi đó mọi con số rollout ở trên chia 6. Cách này đổi ý nghĩa của "max theo π_A", nên phải khai.
   - Cách không đổi thiết kế: viết lại vòng lặp mô phỏng dạng vector hoặc numba để chạy nhiều particle cùng lúc. Mức tăng tốc chưa đo được, nên không tính vào đây.

**Kế hoạch đề xuất:** mô phỏng mọi khối với Sentinel dùng bảng (24 CPU-giờ), cộng dựng bảng (tới 309 CPU-giờ), cộng rollout headline với R = 16–64 (176–706 CPU-giờ). Tổng là **509–1.039 CPU-giờ, tức 3,7–7,6 ngày** trên máy này với `--jobs 10`. Chạy thêm ablation bằng rollout ở headline với R = 16 thì cộng 1,7 ngày. Bộ đếm workflow dưới C12 (post-mortem theo thứ tự trong ô) buộc các workflow của một ô chạy tuần tự, nhưng vẫn còn hàng trăm luồng độc lập (hệ thống × cột × ô × seed), nên không làm giảm độ song song.

**Đĩa.** Mỗi record khoảng 525 byte (đo trên dev; v2: 4,5 GB cho 8,5 triệu record). 16,4 triệu record phía eval vì vậy chiếm khoảng 8,6 GB. Bước tổng hợp theo kiểu D33 mất khoảng 4–5 phút (v2: 146 giây cho 9,4 triệu record).

## 7. Giả định

- **[GĐ 1]** Độ tăng tốc 5,7 lần là của v2 trên chính máy này với `--jobs 10`. Log không ghi `--jobs`; lấy giá trị mặc định 10, trùng lệnh ghi trong docstring. Mốc bắt đầu là dòng thời gian đầu của `eval-log.txt`; mốc kết thúc là mtime của file.
- **[GĐ 2]** "Lớp attacker" ở dòng 5 là 6 lớp hành vi của cột tinh chỉnh D18. Nếu hiểu là 3 lớp của draft (hợp lý, scripted, LLM) thì mọi con số rollout chia 2.
- **[GĐ 3]** Thế giới v3 (payload sleeper, lan nhiều carrier, gỡ cả carrier) có giá mỗi task bằng thế giới v2. Nếu gấp 2 lần, phần mô phỏng vẫn dưới 2 ngày và không đổi kết luận. Tỉ lệ sống sót 0,62 lấy từ `survives(solve_rate=0.62)`.
- **[GĐ 4]** Liệt kê best response trong v3 dùng mọi vị trí đặt 4(H − Δ), vì C8 bỏ ràng buộc ngủ yên. Trên dev, v2 có 916 vị trí ở Δ = 4, còn v3 có 1.108.
- **[GĐ 5]** Đối chứng Δ = 0 là ô Δ = 0 của B1 và các sweeper, như D28 của v2, nên không có episode riêng.
- **[GĐ 6]** B7 giải LP một lần cho mỗi (H, ô) và lưu lại. Một lần giải mất 0,9 ms. Giá mỗi task lấy bằng B2, cost-greedy cũng vậy; stage-weighted ngẫu nhiên lấy bằng `L-SW-uniform`.
- **[GĐ 7]** Best response ở lưới chính chạy ở detector headline cho mọi (ρ, χ), như v2 (D27) mở rộng thêm trục χ. Nếu chạy cả 3 detector, khối 2 × 3.
- **[GĐ 8]** Cột "attacker chọn Δ" chỉ chạy lại cho các hệ thống mà hành vi phụ thuộc ô Δ. Với baseline, max theo Δ đọc được từ khối 2.
- **[GĐ 9]** Mỗi độ nhạy là một lát của lưới chính (mọi hệ thống, held-out, mọi ρ, χ = 1,34, detector mid, mọi Δ), cộng best response cho B1 và Sentinel, như v2 làm với cặp (B1, Sentinel). Nếu mỗi độ nhạy chạy đủ lưới chính thì khối 4 lớn khoảng × 9. Best response trên cặp vị trí khi gieo 2 carrier được tách ra thành khối 4* tùy chọn.
- **[GĐ 10]** Trục K_d chỉ cần B1 và Sentinel, vì H19 đo mức giảm. K_d = 2 là thế giới chính nên không chạy lại.
- **[GĐ 11]** Lịch khối của Mệnh đề 5.7 là policy mới, tính giá như B2. Δ = 0 bị loại khỏi lưới ngân sách vì B_min(Δ) chỉ định nghĩa khi Δ ≥ 1. Tiêu chí bỏ sót ≤ α cần cả held-out và best response.
- **[GĐ 12]** Tinh chỉnh v3 theo `select_mixture.py` (2 seed, 6 cột, 3 kernel), cộng trục χ cho bước (c), vì χ theo C16 đổi độ sâu nên đổi hành vi. Bước (d) cho −randomization là mới.
- **[GĐ 13]** Tinh chỉnh chạy member, không chạy Sentinel có rollout. Nếu η_Q phải tinh chỉnh bằng chính Sentinel có rollout, cần thêm 8 η × 3 kernel × số episode dev của lớp Sentinel, nhân với giá rollout ở §2. Phần này không làm được nếu không có bảng.
- **[GĐ 14]** Chưa tính: giá giải chính xác ở dòng 2–3 (chưa có code); 240 game nhỏ (H7); thế giới A7; thế giới kiểm theo giai đoạn; LLM attacker; chạy thật; dựng 620 thay đổi lành; detector học. Tất cả nằm ngoài lõi hoặc chưa có code để đo.

## Tái lập

Các script nằm trong thư mục scratchpad của phiên này, không nằm trong repo. Cả ba chỉ đọc code và `corpus.json`, và không ghi gì vào `spikes/`.

- `time_v2_dev.py` → `timing_v2_dev.json`: đo thời gian các hàm của `run_draft_eval.py` trên split dev, mất khoảng 3 phút.
- `time_pf_rollout.py` → `timing_pf.json`: đo particle filter, clone trạng thái, rollout và LP.
- `v3_cost_model.py` → `v3_cost.json`: đếm episode và tính CPU-giờ.

`tools/estimate_study_cost.py` không dùng được cho việc này, vì nó chỉ ước lượng tiền token LLM của lượt chạy thật (P2), không ước lượng CPU của sim.
