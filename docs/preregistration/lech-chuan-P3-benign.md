# Lệch chuẩn P3: cổng benign-corpus của v3 (task T24)

Ngày 27/09/2026. Nhánh `p3-benign-fix`, tách từ `int-p2` tại `6c94697` (đã chứa `p3-benign`/`bd51a31`).

**File này được viết và commit TRƯỚC khi sửa bất kỳ dòng code nào và TRƯỚC khi chạy lại cổng.** Chưa có AUC mới nào được xem khi viết file này. Mọi con số dưới đây lấy từ lần chạy trước (`reference/v3_benign.json` của `bd51a31`) hoặc tính bằng công thức, không từ lần chạy mới.

## 1. Lần chạy trước và hai nguyên nhân

Lần chạy trước (620 thay đổi lành, 155 sự kiện × 4): AUC trung vị 0,970, CI95 trung bình [0,943; 0,998], 0/20 split đạt, kết luận **không đạt**. Có hai nguyên nhân độc lập.

### 1a. Cỡ mẫu: cổng bất khả thi về số học

`floor_hi = 0,5805` trong manifest là đúng. Đã kiểm độc lập bằng Hanley–McNeil ở AUC thật = 0,5 với `test_fraction = 0,4` (n₁ = 62, n₂ = 248). Nghĩa là **một corpus khớp hoàn hảo cũng không đạt 0,56 ở 620 mục**. Suy luận "cần khoảng 900" là sai:

| Sự kiện | Chung (thay đổi lành) | CI95 trên tại AUC thật = 0,5 | Đạt ≤ 0,56 |
|---|---|---|---|
| 155 | 620 (số của draft) | 0,5805 | không |
| 225 | 900 (ghi chú v2) | 0,5668 | không |
| 279 | 1116 | 0,5598 | có |

Mở rộng tới 1116 là bất khả thi: **Δ = 8 chỉ có 160 vị trí sleeper ứng viên** (`corpus.candidates`: 993 / 801 / 673 / 458 / 160 cho Δ = 0 / 1 / 2 / 4 / 8). Ở `PER_EVENT = 4`, Δ = 8 chặn thiết kế cân bằng ở 40 sự kiện mỗi Δ, tức 200 sự kiện / 800 chung, sàn 0,5708. Vẫn đỏ.

Nguyên nhân thật: CI của AUC bị chặn bởi lớp **nhỏ hơn**, nên tỉ lệ 4:1 tự phá công suất thống kê. Cùng pool 993 mục drift, cùng khoảng 800 mục:

| Đối chứng / sự kiện | Sự kiện / Δ | Tổng sự kiện | Tổng chung | Sàn | Đạt |
|---|---|---|---|---|---|
| 4 (quy ước v2) | 40 | 200 | 800 | 0,5708 | không |
| 2 | 80 | 400 | 800 | 0,5548 | có |
| **1** | 160 | 800 | 800 | **0,5448** | có |

### 1b. Kênh kích thước: hằng số mang sai từ thế giới v2

`build.py` ghi rõ `PAYLOAD_LENGTH = 63` là **trung vị** của `len(content)` trên 2294 mục memory lành của `benign_pool(pool=full, natural=False, seed 20260916)`; phân bố min 42, Q1 56, trung vị 63, Q3 72, max 549, mean 69,49. Comment cũng nêu vì sao phải là trung vị: hồi quy logistic đơn điệu theo `size`, nên `size` chỉ đóng góp bằng không khi hằng số nằm đúng trung vị lành. Và nó đã lường trước tình huống này: *"moving the certification background is a VISIBLE edit of this constant"*.

Nền chứng nhận của v3 là drift của chính agent v3, **không phải** pool `full` của v2:

| | mean | sd | số giá trị khác nhau |
|---|---|---|---|
| drift (lành) | 80,0435 | 19,2879 | 59 |
| payload | 63,2645 | 2,3694 | **3** |

SMD −1,2211; trọng số `size` đo được −5,4587 (trên F_match của v2, cùng các item; trên 4 đặc trưng của draft, trọng số `edit_size` là −5,2864). Payload ngắn hơn thì bị gắn cờ. Đây là hệ quả đã được ghi trước trong `build.py`, không phải bất ngờ.

### 1c. Hai đặc trưng còn lại (để đối chiếu, không sửa)

- `provenance_shape`: một giá trị duy nhất ở cả hai lớp (20,0), nên là hằng và đóng góp bằng không. Thực chất bộ phân loại đang dùng 3 đặc trưng.
- `recency`: khớp theo thiết kế, AUC 0,5.
- `embedding_shift`: AUC một đặc trưng 0,5575; mean_pos 0,1718 so với mean_neg 0,1332; SMD 0,1208. Đây là phần rủi ro còn lại.

## 2. Hai lệch chuẩn sẽ thực hiện

Cả hai ở level **L1**. Cả hai lệch khỏi **v2**, không lệch khỏi câu chữ của draft: draft (§8, Table 1) không nêu số đối chứng cho mỗi sự kiện và không nêu độ dài payload.

### D-v3-2: `PER_EVENT` 4 → 1 (lệch khỏi quy ước v2)

- **So với cái gì:** `analysis/benign_corpus.PER_EVENT = 4` là hợp đồng của v2. Draft chỉ nói "620 benign carrier modifications generated to match poisoning events", không nói bao nhiêu đối chứng cho một sự kiện.
- **Làm gì:** thêm hằng số phía v3 `V3_PER_EVENT = 1` trong `v3/benign.py`. `PER_EVENT = B.PER_EVENT` giữ nguyên (4) và được ghi vào manifest để so sánh. Không sửa v2.
- **Cỡ:** số sự kiện mỗi Δ = `min(candidates[Δ] // V3_PER_EVENT)` trên 5 giá trị Δ, cân bằng, mục tiêu 160 mỗi Δ, tức 800 sự kiện / 800 thay đổi lành.
- **Hệ quả phải khai:** tổng thay đổi lành là **800, không phải 620** như câu chữ của draft. Ở 620 mục, sàn 0,5805 đã vượt trần (bảng 1a); con số 620 của draft không thể đi cùng tiêu chí cận trên CI95 ≤ 0,56. Manifest ghi cả hai (`n_benign` dùng thật và `n_benign_draft = 620`).
- Giữ `n_distinct_benign == n_benign`: không đối chứng nào dùng hai lần.
- Nếu Δ nào không đủ sự kiện (vì hết đối chứng cùng repo), ghi lý do theo N3, không bù lặng lẽ.

### D-v3-3: độ dài payload rút theo phân bố nền v3 (lệch khỏi hằng số v2)

- **So với cái gì:** `build.PAYLOAD_LENGTH = 63` là hằng số của v2, dẫn xuất từ nền của v2. Draft không nói độ dài payload.
- **Chiều sửa: sửa attacker, KHÔNG cắt thế giới.** Cắt drift xuống 63 là chỉnh thế giới cho vừa một hằng số mang từ thế giới khác sang; reviewer sẽ đọc thành benchmark tự chỉnh bài kiểm tra tính hợp lệ của chính nó. `build.py` nằm trong `freeze.SOURCE`, không sửa. Không thêm hàm drift riêng cho v3.
- **Làm gì:** trong `v3/payload.py` (file của T3, đường `length_reason` đã có), thêm hàm rút L từ phân bố `len(content)` của drift v3 trên dev, seed từ `SEED`. Khớp cả phương sai, không chỉ trung bình: mục tiêu `distinct_pos` từ 3 lên cỡ 59, `sd_pos` từ 2,37 lên cỡ 19.
- **Quy tắc dẫn xuất:** đúng quy tắc `build.py` dùng cho 63 (trung vị của `len(content)` trên các mục memory lành của nền chứng nhận), chỉ khác nền: nền là drift của agent v3 trên dev. Manifest ghi trung vị, Q1, Q3, min, max, mean, sd của nền đó.
- **Attacker mạnh lên, không yếu đi:** `build.py` ghi 170/2248 sigma khả thi ở ε = 1,0 không đáp ứng được L = 63, và nền lành có đuôi dài; cho attacker rút L làm **nở** lớp attacker. Sigma nào không đáp ứng được L đã rút thì ghi lý do theo N3 (`build.payload_length_reason` áp cho L đó), không bỏ lặng lẽ.
- **Phạm vi:** payload rút độ dài là đường chọn thêm (opt-in) của `SleeperPayload`; mặc định vẫn là byte của v2 (L = 63), nên các lượt chạy v3 khác không đổi. Cổng P3 chứng nhận payload rút độ dài. Nối payload này vào runner v3 là một quyết định riêng, ngoài T24.

## 3. Những gì KHÔNG đổi

- `CEILING = 0,56` và `CRITERION = mean_ci95_upper_over_split_seeds` **không đổi**, và tiếp tục được đọc từ `analysis/gate2_v2.record()`. Không lùi về chuẩn điểm-ước-lượng của draft ("AUC ≤ 0.56") dù chuẩn đó lỏng hơn.
- 4 đặc trưng của draft giữ nguyên; không bỏ đặc trưng nào. Kênh kích thước phải đóng **bằng kiến tạo**.
- Giao thức split của v2 (20 seed, test 0,4, hồi quy logistic của v2, Hanley–McNeil) giữ nguyên.
- `CONTROL_KINDS` giữ cả `v2-notes` làm đối chứng chẩn đoán. Lần trước nó ra AUC 1,0 (provenance tách tuyệt đối); lần này **phải vẫn ra 1,0**, nếu không là có gì đã hỏng.
- Không đụng eval split, seal, `freeze.SOURCE`, `freeze.TABLES`. Chỉ dev.

## 4. Dự đoán ghim trước khi chạy

- **Sàn lý thuyết** (Hanley–McNeil, mẫu độc lập, 800/800, fold test 320/320): **0,5448**.
- Lần trước, `drop_one[edit_size]` cho AUC trung vị 0,5194 và `hi_mean` 0,6003 tại sàn 0,5805, tức phần tín hiệu dư trên sàn khoảng **0,02** (chủ yếu từ `embedding_shift`).
- Vậy nếu kênh kích thước đóng bằng kiến tạo, kỳ vọng `hi_mean` mới rơi vào **0,55–0,57**. Khoảng này cắt ngang trần 0,56, nên **kết quả thực sự chưa biết** trước khi chạy.
- **Cả đạt và không đạt đều báo cáo được**, và sẽ được báo cáo như đo được. Không đổi thiết kế sau khi xem AUC để lật kết luận.

## 5. Điều đã biết trước về cụm

`django/django` chiếm 87/155 sự kiện (56%) trên 73 workflow chứa sự kiện ở lần chạy trước. Công thức sàn ở mục 4 giả định mẫu độc lập, nên nó là **lạc quan**: sàn gom cụm theo workflow sẽ **cao hơn 0,5448**.

- Sàn gom cụm được tính bằng wild cluster bootstrap của T17 (`v3/metrics.py`: `family_draws` với trọng số Webb, `interval`), cụm là workflow; không viết bootstrap mới.
- Manifest ghi cả hai: `floor_hi` (độc lập, Hanley–McNeil) và `floor_hi_clustered`.
- Nếu sàn gom cụm vượt 0,56, đó là kết quả: cổng của draft không đạt được dưới cụm workflow ở quy mô dev hiện có. Báo cáo số sự kiện cần thiết. Không nới trần.

## 6. Phạm vi carrier

Cổng chỉ phủ `memory` (khai trong DCM, level L1; draft không nêu carrier nên đây là thu hẹp có khai báo). `branch` không có drift; `skill` và `queue` gần như không có. Mọi phát biểu về `skill`/`queue` phải mang cảnh báo rằng benign corpus không phủ chúng. Không tự tạo drift cho `skill`/`queue` trong T24; đó là đổi thế giới, một quyết định riêng.
