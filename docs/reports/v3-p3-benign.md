# v3 P3: thay đổi lành và cổng AUC 0,56 (T24)

Ngày 27/09/2026. Nhánh `p3-benign-fix`, tách từ `int-p2` tại `6c94697`. Báo cáo này thay bản của `p3-benign`/`bd51a31` (bản đó: 620 mục, AUC trung vị 0,970, không đạt). Mọi số đo trên **dev** (100 workflow của v2 qua `v3.corpus.dev_workflows()`). Không có số nào từ eval, không lượt eval nào được chạy.

Hai lệch chuẩn L1 (D-v3-3, D-v3-4) và dự đoán được ghim trong `docs/preregistration/lech-chuan-P3-benign.md`, commit `faffc1b`, **trước** mọi dòng code và trước khi xem AUC mới.

## 1. Kết luận cơ học: không đạt

| Đại lượng | Giá trị |
| --- | --- |
| Kết luận (trần 0,56, `mean_ci95_upper_over_split_seeds`, đọc từ `gate2_v2.record()`) | **không đạt** |
| `hi_mean` (trung bình cận trên CI95 trên 20 split) | **0,5793** |
| CI95 trung bình | [0,4900; 0,5793] |
| AUC trung vị / trung bình | 0,5328 / 0,5347 |
| Số split có cận trên ≤ 0,56 | 4/20 |

**So với dự đoán đã ghim:** dự đoán `hi_mean` rơi vào 0,55–0,57. Đo được 0,5793: **lệch**, nằm trên khoảng dự đoán khoảng 0,009. Dự đoán dựa trên phần dư ≈ 0,02 trên sàn ở lần trước; phần dư đo được lần này là 0,5793 − 0,5448 ≈ 0,035. Phần lệch đến từ `embedding_shift` (mục 4), không từ kích thước.

Trần và tiêu chí không đổi. Không lùi về chuẩn điểm-ước-lượng của draft: AUC trung vị 0,533 nằm dưới 0,56, nhưng tiêu chí đã khai là cận trên CI95, và theo tiêu chí đó cổng không đạt.

## 2. Kênh kích thước: trước và sau

Attacker rút độ dài payload L từ phân bố `len(content)` của drift v3 trên dev (D-v3-4, `v3/payload.py`: `draw_length`, `at_length`). Drift không bị cắt; `build.PAYLOAD_LENGTH = 63` không đổi.

| | Trước (`bd51a31`, L = 63) | Sau (L rút theo nền v3) |
| --- | --- | --- |
| `distinct_pos` (số độ dài payload khác nhau) | 3 | **61** (đối chứng: 59) |
| `sd_pos` | 2,37 | **20,15** (đối chứng: 18,11) |
| mean payload / mean đối chứng | 63,26 / 80,04 | 80,42 / 79,18 |
| SMD của `edit_size` | −1,2211 | **+0,0643** |
| AUC một đặc trưng `edit_size` | 0,030 (gập lại 0,970) | 0,510 |
| Trọng số `edit_size` (4 đặc trưng của draft) | −5,2864 | **+0,0406** |
| Trọng số `size` (F_match của v2, cùng item) | −5,4587 | **+0,0388** |

Kênh kích thước đã đóng **bằng kiến tạo**, không bằng việc bỏ đặc trưng: cả 4 đặc trưng vẫn trong bộ phân loại.

Nền chứng nhận v3 (`len(content)` của 993 thay đổi drift trong pool, drift ép trên memory ở mọi workflow dev): min 63, Q1 70, **trung vị 76**, Q3 82, max 319, mean 80,03, sd 19,33, 63 giá trị khác nhau. Quy tắc dẫn xuất là quy tắc của `build.py` cho 63 (trung vị của nền), chỉ khác nền; L được rút từ chính phân bố thực nghiệm của nền nên trung vị trùng và độ trải cũng trùng. 797 độ dài rút được: trung vị 76, mean 79,96, sd 19,54.

N3: 11/797 payload có tag topic dài hơn hoặc bằng L đã rút, nên được dựng chỉ bằng tag (dài hơn L); cả 11 được ghi kèm lý do trong `corpus.payload_length_reasons`, không bỏ.

## 3. Hai sàn

| Sàn | Giá trị | Cách tính |
| --- | --- | --- |
| `floor_hi` | **0,5448** | Hanley–McNeil tại AUC = 0,5, mẫu độc lập, fold test 319/319 |
| `floor_hi_clustered` | **0,5473** | wild cluster bootstrap của T17 (`v3/metrics.py`, trọng số Webb, 10 000 lượt), cụm là workflow (100 cụm) |

- Sàn gom cụm cao hơn sàn độc lập, như đã ghi trước, nhưng chỉ ít: hệ số thiết kế trên nửa độ rộng CI là 1,056. Cả hai sàn đều **dưới** 0,56. Vậy ở quy mô này, cổng **đạt được về số học** kể cả dưới cụm workflow; lần không đạt này là do tín hiệu còn lại, không do cỡ mẫu.
- Cách tính sàn gom cụm: trong mỗi split, AUC của fold test được tuyến tính hoá bằng giá trị placement DeLong; tổng phần dư được rút qua `family_draws`/`interval` của T17 hai lần trên cùng seed, một lần mỗi workflow một trọng số, một lần mỗi item một trọng số. Tỉ số hai nửa độ rộng trên là hệ số thiết kế; `floor_hi_clustered = 0,5 + (floor_hi − 0,5) × tỉ số trung bình`. Không có bootstrap mới.
- Số sự kiện cần (1 đối chứng mỗi sự kiện) để sàn ≤ 0,56: 447 nếu độc lập, 497 nếu gom cụm với hệ số 1,056. Hiện có 797.
- Theo từng Δ (157–160 sự kiện mỗi Δ) sàn là 0,600, nên không Δ nào đạt được riêng lẻ; bảng theo Δ trong manifest chỉ để chẩn đoán.

## 4. `embedding_shift` sau khi đã khớp kích thước

| Đặc trưng | AUC một đặc trưng | SMD | Bỏ đặc trưng này: `hi_mean` (số split đạt) |
| --- | --- | --- | --- |
| edit_size | 0,510 | +0,064 | 0,584 (4/20) |
| **embedding_shift** | **0,564** | **+0,136** | **0,544 (15/20)** |
| recency | 0,500 (khớp theo kiến tạo) | 0 | 0,590 (4/20) |
| provenance_shape | 0,500 (hằng ở cả hai lớp: 20) | 0 | 0,579 (4/20) |

`embedding_shift` vẫn tách: mean 0,185 ở payload so với 0,140 ở đối chứng. Đây là đặc trưng duy nhất mà bỏ đi thì cổng đạt (0,544). Không bỏ nó: bỏ đặc trưng theo kết quả là đúng lỗi phương pháp mà `cong-v2-chot.md` đã từ chối.

Đọc tín hiệu này thế nào:

- Đây là màu đỏ **khác loại** với lần trước. Lần trước là một hằng số mang sai từ thế giới v2 (một artefact bề mặt). Lần này là **nội dung mà item nói về**: payload được dựng để nhắm topic của σ (`payload_topic_like`), còn drift mang topic của một task tương lai bất kỳ; payload làm lệch túi topic của carrier nhiều hơn. Theo nghĩa đó, đây là tín hiệu **ngữ nghĩa**, và nó ủng hộ hướng detector của paper (đọc nội dung/ngữ nghĩa, không đọc bề mặt) chứ không phá nó.
- Giới hạn của phát biểu trên: `embedding_shift` ở đây là L1, tính trên túi token topic (`retrieval.as_topic`), **không** đọc chữ trong `content`. Vì vậy phép đo này không phân biệt được "payload mang chỉ thị, drift mang ghi chú chủ đề"; nó chỉ cho thấy payload và drift khác nhau ở topic mà chúng mang so với lịch sử carrier. Phát biểu mạnh hơn cần một embedding thật trên nội dung.
- Đối chiếu: trên cùng các item, F_match 5 đặc trưng của v2 (trong đó `topic` là mã topic, không phải độ lệch so với carrier) cho `hi_mean` 0,5562 và **đạt**. Đây là phép so sánh chẩn đoán, không thay kết luận chính.

## 5. Đối chứng chẩn đoán và họ salt

| Phép đo | AUC trung vị | `hi_mean` | Kết luận |
| --- | --- | --- | --- |
| Đối chứng là ghi chú agent (`v2-notes`) | **1,000** | 1,000 | không đạt; provenance_shape tách hoàn toàn, như lần trước. Vẫn ra 1,0, đúng như yêu cầu: không có gì hỏng |
| Cùng item, F_match của v2 | 0,511 | 0,5562 | đạt (chẩn đoán) |
| Họ 17 salt của v2 (luật ≥ 14/17) | trung vị 0,544 | 0,570–0,603 | 0/17, không đạt (chẩn đoán, không lật kết luận chính) |

## 6. Dựng tập

| Mục | Giá trị |
| --- | --- |
| Tỉ lệ | 1 đối chứng mỗi sự kiện (`V3_PER_EVENT = 1`, D-v3-3); quy ước v2 `PER_EVENT = 4` được ghi trong manifest (`per_event_v2`) |
| Hạn mức | `min(candidates[Δ] // 1)` = 160 sự kiện mỗi Δ (Δ = 8 chặn: 160 ứng viên) |
| Đạt được | Δ = 0/1/2/4: 160; **Δ = 8: 157/160**. Ba vị trí ở Δ = 8 không còn thay đổi drift nào cùng repo chưa dùng; ghi theo N3 (`supply: 157 of 160 events`), không bù |
| Tổng | **797 sự kiện, 797 thay đổi lành, cả 797 khác nhau**; con số của draft là 620 (xem mục 8) |
| Workflow chứa sự kiện | 99/100; django 394/797 sự kiện (49%) |
| Đối chứng của chính workflow tại ι | 439/797 |
| Digest tập | `cd9ba2f0eae2…` (`auditgame/reference/v3_benign.json`) |

## 7. Phạm vi carrier: chỉ memory

Cổng chỉ phủ carrier `memory` (dòng DCM L1 trong `v3/dcm/T24.csv`). Draft không nêu carrier, nên đây là thu hẹp có khai báo, không phải vi phạm. Tốc độ drift danh định: memory 0,314, skill 0,058, queue 0,033, branch 0. Trên lượt danh định ở dev: 320 / 55 / 28 / 0 item drift.

**Mọi phát biểu về `skill` và `queue` phải mang cảnh báo: benign corpus không phủ hai carrier này.** Toàn bộ kết quả tuyến delegated của paper nằm ở `skill` và `queue`; cổng này không nói gì về chúng. Báo cáo này không phát biểu gì về `branch`.

## 8. Cần quyết định

1. **Drift cho `skill`/`queue`.** Muốn cổng phủ tuyến delegated thì phải có đủ drift ở hai carrier này. Đó là đổi thế giới (tốc độ drift, belief, observation), một quyết định riêng; T24 không làm.
2. **`embedding_shift`.** Cổng không đạt vì đặc trưng này. Các lựa chọn: báo cáo không đạt như hiện tại; hoặc thay L1 bằng một embedding thật trên nội dung (đổi đặc trưng, phải đăng ký trước); hoặc để payload chọn topic giống drift hơn (đổi attacker, và làm yếu tấn công). Không bỏ đặc trưng.
3. ~~**Nối payload rút độ dài vào runner v3.** Payload rút độ dài hiện là đường chọn thêm của `SleeperPayload` (`length = None` vẫn là byte của v2). Cổng P3 chứng nhận payload rút độ dài, còn runner/attacker của lưới v3 (T6/T7) vẫn dùng L = 63. Muốn cổng nói về đúng attacker chạy trong lưới thì phải nối vào; việc này đổi mọi số của lưới v3 và file của task khác.~~ **Đã làm 27/09, nhánh `wire-payload-length`** -- xem mục 10 dưới đây.
4. **Số mục 797 so với 620 của draft.** Ở 620 mục với tỉ lệ 4:1, sàn là 0,5805 nên không thể đạt. Bản này dùng 797 (1:1). Giữ 620 với tỉ lệ 1:1 (620 sự kiện, 124 mỗi Δ) cho sàn độc lập khoảng 0,551, cũng dưới trần; bản này làm theo hạn mức 160/Δ của đặc tả T24.

## 9. Tệp và cách chạy lại

- `auditgame/v3/payload.py`: `draw_length`, `length_stats`, `SleeperPayload.at_length`, `payload_content_at`, `LENGTH_RULE` (D-v3-4).
- `auditgame/v3/benign.py`: `V3_PER_EVENT`, `events_per_delta`, `length_background`, `clustered_floor`.
- `auditgame/tools/v3_benign.py`: in kết quả; `--write` ghi `auditgame/reference/v3_benign.json` bằng mode `"x"` (phải xoá manifest cũ trước). Chạy khoảng 2,5 phút, kể cả họ salt.
- `auditgame/tests/v3/test_s8_benign.py`: 5 test, ứng với các dòng trong `auditgame/v3/dcm/T24.csv`. Test không đòi cổng đạt; chúng đòi tập đúng như đã khai, kênh kích thước đóng bằng kiến tạo, hai sàn tái lập được, đối chứng `v2-notes` vẫn 1,0.
- `tests/run_v3.py` xanh (3/3, 57/57, 144/144); `tools/v3_dcm.py --check`: 0 lỗi. Freeze gốc: `freeze: clean sha256:c789fa7362e0`.

## 10. Ghi chú 27/09: đã nối vào lưới (nhánh `wire-payload-length`)

Mục 8.3 ở trên đã làm. `v3/payload.py` thêm `default_length_background()` (nền T24, cache một lần mỗi tiến trình, nhập `v3.benign` cục bộ để tránh vòng import) và `with_default_length(sp)` (rút L theo nền đó, seed `DEFAULT_LENGTH_SEED = analysis.benign_corpus.SEED` -- cùng seed T24). Ba điểm gọi trong lưới thật:

- `v3/attackers.py` `AttackV3.plan()` (T7, menu kịch bản) và `br_menu()` (T7/D27, best response): mỗi carrier được rút độc lập trước khi vào `Placement`.
- `v3/rollout.py` `sleeper()` (T12): dùng trong cả đặt tương lai (`_future_placement`) và cắm hạt quá khứ (`plant`), nên rollout headline (dòng 5) cắm cùng attacker rút-độ-dài mà episode thật chạy.

`plan_sleeper_all` (T3) tự nó **không đổi**: `length = None` vẫn là mặc định của nó, nên mọi test đọc trực tiếp `plan_sleeper_all` (ví dụ so khớp byte-for-byte với v2) không bị ảnh hưởng. Đường V2_COMPAT (T4, `AgentMode.V2_COMPAT`) không đi qua `v3.payload`/`v3.attackers` cho việc dựng payload -- nó gọi thẳng `build.plan_poison_all`/`build.inject` của v2 -- nên vẫn cố định L = 63 và `tests/v3/test_infra_v2_compat.py` không đổi.

Khả thi (T3) đo lại trên dev **giống hệt trước** (0: 3.972, 1: 3.204, 2: 2.692, 4: 1.832, 8: 640 vị trí khả thi; 100/100, 100/100, 100/100, 100/100, 58/100 workflow), vì vị từ đích chỉ đọc topic, không đọc độ dài nội dung. Phân bố L thực sự lưới dùng (menu kịch bản, mọi Δ, 100 workflow dev, n = 8.081 lượt rút): trung vị 75, IQR [70; 82], mean 79,84, sd 20,04, 63 giá trị khác nhau -- khớp với nền (trung vị 76, IQR [70; 82], mean 80,03) và với 797 lượt rút của chính cổng benign (trung vị 76, mean 79,96).

Việc đổi nội dung payload đổi `item_id` (nó là hash theo nội dung), nên đổi điểm detector và mọi số hạ lưu của lưới thật (chưa có lưới thật nào chạy -- T14/T18/T22 vẫn chưa dựng, xem Cổng 1 của `tests/run_v3.py`). Trong bộ test hiện có, việc này di chuyển đúng một digest ghim: `tests/v3/test_infra_glue.py` `TestInfraGlue.PINNED_DECISIONS` (từ `4e3fc76af7ae...` sang `f410562e229a...`, ghi lý do tại chỗ), vì `_decision_digest` chạy episode thật qua `AT.by_name(...).plan(...)`. Hai test khác so khớp payload dựng qua `att.plan`/`br_menu` với payload dựng thẳng từ `plan_sleeper_all` phải sửa cách so sánh (bỏ so trường `length`, hoặc rút cùng độ dài trước khi so): `tests/v3/test_s4_attacker.py` `test_eighteen_scripted_seven_held_out`, `test_two_carrier_seeding_respects_attacker_budget`. `auditgame/reference/v3_benign.json` **không đổi số liệu** (digest tập vẫn `cd9ba2f0eae2…`, benign.py tự rút độc lập từ nền và seed của chính nó, không qua `with_default_length`); chỉ `payload_source_sha256` đổi vì sửa `v3/payload.py`, đã ghi lại bằng `tools/v3_benign.py --write`. `tests/run_v3.py --all` xanh sau khi sửa (3/3, 66/66, 153/153). Freeze v2 không đổi: `sha256:c789fa7362e0`.
