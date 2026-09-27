# Sentinel v3 — làm chặt hai lượt nhạy bổ sung (C1 = A7 provenance, C2 = stage world)

27/09/2026. Nhánh off `int-p2` (`4be2744`). DEV ONLY. Không chạm eval split, `v3/seal.py`, `frozen/`.
Mục tiêu: đóng lỗ hổng mà báo cáo chi phí P2 đã ghi — stage world chưa có test riêng trong
`tests/v3/`, và cả hai lượt nhạy bổ sung (`A7`, `stage`) chưa được smoke đầu-cuối trên dev — để
#7 (full dev grid) không bị chặn vì nó về sau.

`v3/grid.py` khai `SUPPLEMENTARY_SENSITIVITIES = ("A7", "stage")` ("lượt bổ sung sau lõi"). Hai
lượt này đã được đấu dây vào `stage_world.episode_in_world` / `StageEpisode` và bộ chọn observer
provenance của `runner.Episode`, nhưng thiếu test riêng và chưa smoke.

## 1. Test riêng: `tests/v3/test_stage_world.py`

`test_s4_sensitivity.py` (T20) đã chạy stage world như MỘT trong sáu lượt nhạy một-yếu-tố (câu
chuyện RQ4: mỗi switch lật đúng một yếu tố). Module mới bảo vệ hành vi RIÊNG của stage world ở
mức đơn vị, tất định (không Monte-Carlo), sáu test:

| Test | DCM id | Bảo vệ điều gì |
| --- | --- | --- |
| `test_stages_are_the_four_named_and_priced` | D8.stages | Bốn stage đúng thứ tự (insertion/retrieval/delegation/commit) và giá S7 0.4/0.9/1.6/4.1, bằng giá đơn vị của carrier nó kiểm dưới D2 |
| `test_stage_target_roundtrip_is_the_d2_mapping` | D4.defender | `STAGE_OF_TARGET`/`TARGET_OF_STAGE` là song ánh D2, round-trip hai chiều; `_to_stage`/`_to_target` ánh xạ một AuditAction đi và về nguyên vẹn |
| `test_c16_fixes_stage_depth` | D8.stages | Ô cố định depth theo carrier (C16); `stage_depths`/`stage_kappa` re-key giá trị ô; `StageEpisode.cost` = giá × depth, và từ chối k không phải stage, depth vượt ô, depth không dương |
| `test_gate_reading_inspects_objects_in_flight` | D8.stages | Gate đọc object đang bay ở task t (insertion/delegation thấy vật viết tại t, commit thấy patch của task); mọi object bị soi nằm trên trace `StageEpisode.inspected` gắn stage đã mua |
| `test_gate_accounting_true_false_rejections` | D8.stages | Kế toán L1: benign bị chặn → FQ/false_removed, poisoned → true_q và set detected_at; `StageGates` ghi seen/rejected và bỏ qua vật ingress ẩn (H8); blocks theo stage khớp fq + true_q |
| `test_carrier_policy_maps_onto_stages` | D4.defender | Policy carrier-world chạy qua `carrier_policy` — target → stage D2, quan sát ánh xạ về carrier target, lines 8-9 mặc định bị bỏ và giữ với `keep_quarantine`; forward `delta_hat`/`line5_source` |

Test dùng detector giả tất định (`_FakeDet`) cho phần kế toán gate để không phụ thuộc rút thăm,
và một ít workflow dev (3 wf × attacker held-out, 1 seed) cho các bất biến đầu-cuối.

**Đăng ký DCM.** Check 3 của `tools/v3_dcm.py` buộc mọi test không-infra phải có dòng DCM;
check 2 buộc file test thuộc `OWNED_TESTS` của task. Đã:
- Thêm sáu dòng vào `v3/dcm/T20.csv` (dùng lại nguyên văn hai câu draft D8.stages và D4.defender,
  cặp `(id, test)` là duy nhất vì `test` khác nhau; id nằm trong docstring của từng test).
- Thêm `test_stage_world.py` vào `OWNED_TESTS["T20"]` trong `tools/v3_dcm.py`.

## 2. Smoke dev đầu-cuối hai lượt bổ sung (bước 3)

Chạy `A7` và `stage` world qua runner T6: 4 workflow dev đầu × 7 attacker held-out (28 kế hoạch
khả thi mỗi world sau lọc N3), 1 seed, các hệ chạy được hôm nay. **Dòng 8 (Sentinel) dùng
tau/eta_Q PLACEHOLDER** (`sentinel.stub_parts`) vì bảng đã tuned đang được tạo ở worktree khác —
KHÔNG có số nào từ Sentinel ở đây là kết quả.

Chi phí: **336 episode, wall ~1.95s, cpu ~1.47s** (nhẹ). Trung bình mỗi (world, hệ):

| World | Hệ | n | harm | FQ | lost |
| --- | --- | --- | --- | --- | --- |
| A7 | B1 audit-at-commit | 28 | 0.179 | 0.00 | 1.96 |
| A7 | B2 uniform random | 28 | 0.214 | 2.86 | 0.71 |
| A7 | B3 audit-on-insertion | 28 | 0.321 | 6.07 | 0.00 |
| A7 | B4 audit-on-retrieval | 28 | 0.286 | 1.32 | 0.00 |
| A7 | B1-prov | 28 | 0.000 | 0.00 | 2.21 |
| A7 | Sentinel [PLACEHOLDER] | 28 | 0.071 | 0.25 | 0.50 |
| stage | B1 audit-at-commit | 28 | 0.179 | 2.32 | 1.96 |
| stage | B2 uniform random | 28 | 0.214 | 4.21 | 0.71 |
| stage | B3 audit-on-insertion | 28 | 0.000 | 7.25 | 0.00 |
| stage | B4 audit-on-retrieval | 28 | 0.000 | 3.50 | 0.00 |
| stage | B1-prov | 28 | 0.179 | 2.32 | 1.96 |
| stage | Sentinel [PLACEHOLDER] | 28 | 0.071 | 4.57 | 0.54 |

Hai dấu hiệu định tính khớp thiết kế một-yếu-tố (không phải headline):
- **A7**: `B1-prov` xuống harm 0.000 vì nó đọc kênh provenance thêm (C1); các hệ không đọc kênh
  (B1) không đổi so với A0 — đúng "A7 là kênh quan sát thêm, không thay đổi hệ không đọc".
- **stage**: `B1-prov` == `B1` (harm 0.179) vì stage world chỉ lật `audit_reading`, provenance vẫn
  A0, nên không có kênh provenance để đọc. Gate insertion/retrieval (B3/B4) đưa harm về 0 nhưng FQ
  cao hơn vì chặn thẳng object đang bay.

## 3. Lỗi tích hợp phát hiện + sửa (bước 4)

**Không có.** Smoke 336 episode chạy sạch, cả hai world định tuyến đúng (`A7` → `runner.Episode`
với observer mang provenance d'; `stage` → `StageEpisode`), mọi record mang đúng
`world.provenance` / `world.audit_reading`, `spent <= budget`. Không có counter thiếu hay định
tuyến sai. Không cần sửa code sản phẩm.

(Trong lúc viết test, một bất biến test bị đặt sai — ban đầu khẳng định gate `retrieval` chỉ thấy
vật viết tại t; thực ra retrieval kéo vật viết từ task trước, nên đổi sang `written_at <= t`. Đây
là sửa test, không phải bug sản phẩm.)

## 4. Trạng thái kiểm

- `tools/v3_dcm.py --check` → **0 problem(s)** (0 pending P2 row).
- `tests/run_v3.py` → **Every gate green** (bao gồm 6 test mới trong `test_stage_world.py`).

## Tệp đã đổi

- `auditgame/tests/v3/test_stage_world.py` (mới)
- `auditgame/v3/dcm/T20.csv` (thêm 6 dòng)
- `auditgame/tools/v3_dcm.py` (`OWNED_TESTS["T20"]` thêm `test_stage_world.py`)
- `docs/reports/v3-p2-supplementary.md` (báo cáo này)
