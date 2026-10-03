# Sentinel v3 P2 — T23: khép P2 (báo cáo hợp nhất, khung + kiểm kê)

27/09/2026. Đây là bản **khung** của báo cáo khép P2 (plan §10, task T23, đợt W9). Nó dựng sẵn mọi phần **không** phụ thuộc ba thứ còn đang chạy hoặc chưa chạy:

- **#5** — bảng dòng 5 **bản đầy đủ đã tinh chỉnh** (T14 bản cuối) và **giá trị tinh chỉnh thật** τ / η_Q / τ5 (T18, `reference/v3_tuned.json`);
- **#6** — kiểm rollout ở ô headline (T19, `tools/v3_headline_rollout.py` + `docs/reports/v3-p2-rollout-check.md`);
- **#7** — kết quả toàn lưới (lượt `v3_run` đầy đủ / scorecard H1–H20).

Mọi ô phụ thuộc #5/#6/#7 để **TBD** kèm lý do (N3: không ghi 0 hay số bịa cho thứ chưa đo). Khi #5–#7 về, chỉ còn điền các chỗ TBD này và **render lại `docs/v3/DCM.md`** (bước cuối của T23, xem §7).

- Nhánh dựng khung: tách từ `int-p2` tại `4be2744` (`git reset --hard int-p2`).
- Số cổng và DCM dưới đây đo **một lần** trên worktree này; không sửa mã nào (read-only trên code), nên số này khớp `int-p2` sạch.
- Nguồn: `docs/plans/v3-p2-plan.md` (T23 ở §10); các báo cáo `v3-p2-*.md` và `v3-p3-*.md`; `sentinel-v3.md`; `docs/preregistration/lech-chuan-P3-benign.md`.

---

## 1. Trạng thái cổng (đo một lần trên worktree này)

`cd auditgame && ../.venv/bin/python tests/run_v3.py` — **"Every gate green"**:

| Cổng | Nội dung | Kết quả |
|---|---|---|
| Gate 0 — V2 INTACT | v3 import v2 và không vá; freeze v2 chưa dịch | **3/3 xanh** |
| Gate 1 — INFRA | DCM, hợp đồng chung, niêm phong, freeze khớp nhau | **66/66 xanh** |
| Gate 2 — DRAFT | mỗi test bảo vệ một câu draft (một dòng DCM) | **155/155 xanh** |
| **Tổng** | | **224/224 xanh** |
| DCM | Dòng P2 pending (test chưa viết) | **0 pending** |

- `freeze.header_line()` (nền v2): `clean sha256:c789fa7362e0` — sạch.
- `freeze_d35`: `clean sha256:e46f8a5c2f94` — sạch.
- `freeze_v3` (khi dựng manifest sống trong lượt kiểm): `clean sha256:d5a19b52a820`.
- Sentinel chưa "ready" đúng như mong đợi ở P2: `sentinel.check_ready` báo còn thiếu **line-5 table (T14)**, **tuned τ / η_Q (`v3_tuned.json`, T18)**, **nominal-kernel tuning (`v3_tuned_nominal.json`, T18)**. Đây là các blocker #5, không phải lỗi P2.

`cd auditgame && ../.venv/bin/python tools/v3_dcm.py --check` — **0 vấn đề** (0 dòng P2 pending tính là vấn đề).

Kiểm sáu điều của cổng DCM (plan §5) đều qua: cặp (id, test) duy nhất; mọi dòng P2 trỏ test tồn tại và xanh; mọi test v3 hoặc có dòng DCM hoặc là `test_infra_*`; mọi `quote` có nguyên văn trong bản chữ đã ghim; sha256 PDF khớp; docstring test chứa đúng `id`.

**Phần P2 của cổng G2 đạt.** (G2 100% chỉ khép được sau P3; đây là phần `phase=P2`.)

---

## 2. Kiểm kê DCM (trạng thái sống các mảnh)

Đọc trực tiếp các mảnh `v3/dcm/T<nn>.csv` ở HEAD hiện tại:

| Số liệu | Giá trị |
|---|---|
| Số mảnh | 22 (`T01`–`T18`, `T20`, `T21`, `T22`, `T24`; T13 có; **T19 chưa có** — blocker #6; T23 không sở hữu mảnh) |
| Tổng dòng dữ liệu | 201 |
| Số `id` duy nhất | 96 |
| Theo pha | **P2: 196**, P3: 5 |
| Theo level | L1: 93; L0: 56; L2: 35; L0+L1: 12; L0+L2: 3; L1+L2: 2 |
| PDF draft ghim | sha256 `c37643f0…263a` (07/09/2026) |
| Bản chữ ghim | `docs/v3/draft-2026-09-07.txt` sha256 `7915e2cc…c24e` |

**Cảnh báo N3 — `docs/v3/DCM.md` đã commit là BẢN CŨ.** File render đã commit còn ghi "shards 19; rows 53; ids 43" và "P2: 5 green / 48 pending" — đó là ảnh chụp từ một trạng thái đầu P2, **không** phản ánh 201 dòng / 0 pending hiện tại. Chỉ T0 và T23 được sinh file này (plan §5). **Render lại `docs/v3/DCM.md` là bước cuối của T23** và nằm ngoài phạm vi bản khung này (bản khung chỉ ghi vào file báo cáo mới). Bước đó: `cd auditgame && ../.venv/bin/python tools/v3_dcm.py --render`, rồi commit `docs/v3/DCM.md`. Xem §7.

---

## 3. Sổ mốc / task P2 (T0–T24, M1)

Trạng thái đọc từ: sự có mặt của module/tool ở `int-p2`, các báo cáo, và lịch sử commit. "merged" = đã vào `int-p2`.

| Task | Nội dung | Trạng thái | Bằng chứng (test / báo cáo / commit) |
|---|---|---|---|
| T0 | Khung v3, DCM theo mảnh, bộ chạy test | **merged** | `tests/run_v3.py` chạy; `test_infra_dcm`, `test_infra_v2_intact` xanh; `tools/v3_dcm.py` |
| T1 | Công tắc, ô, `api.py` (hợp đồng chung) | **merged** | `v3/config.py`, `v3/api.py`; `test_s8_config` xanh; `PRIMARY`, `EVAL_SOURCE_PRIMARY` (D-v3-1) |
| T2 | Dev, eval, niêm phong | **merged** | `v3/corpus.py`, `v3/seal.py`; `EVAL_SPLIT_SHA256`, `SECONDARY_SPLIT_SHA256`; `test_s8_corpus` |
| T3 | Trạng thái carrier + payload sleeper | **merged** | `v3/state.py`, `v3/payload.py`; `test_s4_state_payload` |
| T4 | Agent mock v3 (lan truyền, uỷ nhiệm, drift) | **merged** | `v3/agent.py`; `test_s4_agent`; chế độ V2_COMPAT tái hiện v2 |
| T5 | Mô hình quan sát | **merged** | `v3/observe.py`; `test_s4_observe`; A7 tách kênh provenance (`a27232e`, merge `6b018cb`) |
| T6 | Runner, oracle, loss, Figure 1 | **merged** | `v3/runner.py`, `v3/oracle.py`; `test_fig1`, `test_s4_runner`; sửa #1/#2 của M1 |
| T7 | Attacker v3 (18 scripted / 7 held-out, BR, gieo 2) | **merged** | `v3/attackers.py`; `test_s4_attacker`; `br_systems`/`BR_TRIMS` |
| T8 | Baseline + đối chứng | **merged** | `v3/baselines.py`; `test_s5_baselines`; B1–B6, cost-greedy, SW, B1-prov, Oracle |
| **M1** | Tích hợp mốc đầu trên dev | **merged** | `tools/v3_m1_smoke.py`; **`docs/reports/v3-p2-m1.md`**; 7/8 cổng số đạt, 3c là nhiễu mẫu (§9 của báo cáo M1, `3f3fcbc`) |
| T9 | Particle filter 2048 hạt | **merged** | `v3/belief_pf.py`, `v3/belief_exact.py`; `test_alg1_line7` |
| T10 | Dòng 1: Δ̂ từ post-mortem cùng ô | **merged** | `v3/delta_hat.py`, `v3/sequence.py`; `test_alg1_line1`; `sequence.workflow_order` |
| T11 | Thư viện 28 policy | **merged** | `v3/library.py`; `test_s5_library`; `band_prop61` |
| T12 | Rollout, LP dòng 5, dòng 8–9 | **merged** | `v3/rollout.py`, `v3/line5.py`, `v3/line8.py`; `test_alg1_line5_8` |
| T13 | Dòng 2–3: giải chính xác khi KH ≤ 40 | **merged** | `v3/exact.py`; `test_alg1_line23`; **`docs/reports/v3-p2-line23.md`** |
| **T14** | Dựng bảng dòng 5 | **PILOT merged; bản đầy đủ PENDING (#5)** | `v3/line5_table.py`, `tools/v3_build_table.py`; **`docs/reports/v3-p2-table.md`** (pilot). Chờ τ/η_Q của T18 để dựng bản cuối; `reference/v3_tuned.json` chưa có nên build không pilot bị từ chối. Bảng `.npz` không commit (dev artifact) |
| T15 | Lắp Sentinel v3 + ablation | **merged** | `v3/sentinel.py`; `test_alg1_sentinel`; `V3_REGISTRY` (`2f6f976`). Cổng "changes-a-decision" ghi NOT EXERCISED |
| T16 | Lưới ngân sách H18 + trục K_d | **merged** (T16a + T16b) | `v3/budget.py`; `test_s9_budget`; `B_min(Δ)`, lịch khối (Mệnh đề 5.7); smoke H18/K_d qua lưới T22 |
| T17 | Metrics, kiểm định, bảng điểm | **merged** | `v3/metrics.py`, `v3/scorecard.py`; `test_s9_metrics`; wild cluster bootstrap, luật P/D/E/N/G |
| **T18** | Công cụ tinh chỉnh trên dev | **wiring merged; lượt tinh chỉnh đầy đủ IN PROGRESS (#5)** | `tools/v3_tune.py`; **`docs/reports/v3-p2-tune.md`**; PF thật + line8 thật đã nối (`77feb5e`); `--jobs` tất định (`ec60a5a`). **`reference/v3_tuned.json` / `v3_tuned_nominal.json` CHƯA tồn tại** — lượt ~104 + ~35 CPU-giờ chạy nền, chưa xong |
| **T19** | Kiểm rollout ô headline | **PENDING / chưa bắt đầu (#6)** | **`tools/v3_headline_rollout.py` chưa có**; không có mảnh DCM T19; **`docs/reports/v3-p2-rollout-check.md` chưa có** |
| T20 | Thế giới độ nhạy (C2) | **merged** | `v3/stage_world.py`; `test_s4_sensitivity`; B1-prov đưa vào để chạm thế giới A7 (`79558c4`); nhánh reversible (`508060e`) |
| T21 | Game nhỏ v3 (B7, H7) | **merged** | `v3/smallgame_v3.py`, `tools/v3_small_games.py`; `test_s8_smallgames`; H7 regret vs B7 (`f400039`, merge `90b1203`) |
| T22 | Lưới, cắt BR, freeze v3, công cụ chạy | **code merged; lượt toàn lưới đầy đủ PENDING (#7)** | `v3/grid.py`, `v3/freeze_v3.py`, `tools/v3_run.py`; `test_infra_grid`, `test_infra_freeze`; **`docs/reports/v3-p2-cost.md`**. Smoke dev một phần đã chạy; smoke toàn lưới còn chờ T15/T19/T20 nối đủ (xem §5) |
| **T23** | Khép P2 (báo cáo hợp nhất) | **IN PROGRESS** (file này) | Bản khung này; DCM.md render lại là bước cuối |
| T24 | Cổng benign-corpus P3 | **merged** (P3, làm sớm) | `v3/benign.py`, `tools/v3_benign.py`; `reference/v3_benign.json`; **`docs/reports/v3-p3-benign.md`**; preregistration `faffc1b`; verdict **không đạt** (`hi_mean` 0,5793 > 0,56) |

**Tóm tắt:** trên 25 lát (T0–T24 + M1): **21 đã merge trọn**; **4 còn hở** — T14 (pilot xong, bản cuối chờ #5), T18 (wiring xong, lượt tinh chỉnh chờ #5), T19 (chưa bắt đầu, #6), T22 (code xong, lượt toàn lưới chờ #7). T23 đang làm.

---

## 4. Sổ lệch chuẩn D-v3 (D-v3-1 … D-v3-5)

Đánh số **theo `sentinel-v3.md` + preregistration** (bản đã sửa va chạm ID, commit `f427eb7`). Mọi lệch chuẩn ở đây lệch khỏi **v2** hoặc khỏi **số của draft**, không lệch khỏi câu chữ quy định của draft; đều **khai trước khi chạy lại / trước khi xem số mới**.

| ID | Level | Lệch cái gì → thành gì | Vì sao | Nguồn |
|---|---|---|---|---|
| **D-v3-1** | L2 | Nguồn eval **chính** đổi từ SWE-bench (26 wf / 18 họ) sang **SWE-rebench-V2** (`nebius/SWE-rebench-V2`): instance từ 01/2024, 20 họ chưa chạm, ≤ 5 wf/họ, một lượt H ~ U{6..14}, không dùng lại instance → **96 wf / 20 họ, Kish 19,86**. SWE-bench cũ thành **phân tích phụ** (26 wf / 18 họ, Kish 10,24) | Nguồn có `created_at`/`base_commit`/`patch`/`test_patch`/image dựng sẵn, đủ cho lượt agent thật; corpus lớn hơn, Kish gần gấp đôi. Sửa **sau Cổng 0, trước mọi tinh chỉnh** | `sentinel-v3.md` C14 (dòng 83); `v3/config.py` `EVAL_SOURCE_PRIMARY`; `v3/corpus.py`; `v3/dcm/T02.csv` (`D8.scale`) |
| **D-v3-2** | — (thủ tục) | **Một lần chạm niêm phong**: gọi tương tác `corpus._specs("primary")` đã in số workflow **theo họ** của phần Δ = 8 của eval chính | Sự cố thao tác, khai để minh bạch. **Không** lộ nội dung: không instance, không task, không harm — chỉ số đếm theo họ | `sentinel-v3.md` §"Sai lệch khai báo D-v3-2" (dòng 508) |
| **D-v3-3** | L1 | `PER_EVENT` **4 → 1** (`V3_PER_EVENT = 1`): một đối chứng lành cho mỗi sự kiện poison, không phải 4 | Ở tỉ lệ 4:1, lớp nhỏ hơn chặn CI của AUC nên tự phá công suất; 1:1 hạ sàn Hanley–McNeil xuống 0,5448. `PER_EVENT = 4` của v2 vẫn ghi trong manifest (`per_event_v2`), không sửa v2 | preregistration §D-v3-3 (dòng 54); `v3/benign.py` `V3_PER_EVENT` |
| **D-v3-4** | L1 | Độ dài payload **rút theo phân bố nền drift v3 trên dev**, không còn hằng số `PAYLOAD_LENGTH = 63` của v2 (khớp cả phương sai: `distinct_pos` 3 → ~59, `sd_pos` 2,37 → ~19) | Nền chứng nhận của v3 là drift agent v3, không phải pool v2; hằng 63 mang sai từ thế giới khác nên kênh kích thước tách hai lớp. **Sửa attacker, không cắt thế giới** (không đụng `build.py` ∈ `freeze.SOURCE`). Đã nối làm mặc định cho payload lưới (`c10bd9e`, nhánh `wire-payload-length`) | preregistration §D-v3-4 (dòng 63); `v3/payload.py` `draw_length` / `with_default_length` |
| **D-v3-5** | L1 | Số sự kiện lành thực dựng là **797**, không phải 620 (số draft) và không đúng 800 (thiết kế cân bằng): Δ = 0/1/2/4 mỗi mức 160; **Δ = 8 chỉ 157** vì 3 vị trí sleeper hết đối chứng cùng repo chưa dùng | 620 mục cho sàn 0,5805 > trần 0,56 nên bất khả thi về số học; N3: ghi lý do thiếu 3 sự kiện thay vì bù lặng lẽ | `sentinel-v3.md` "Số sự kiện benign (T24, D-v3-5)" (dòng 105) |

**Cảnh báo N3 — va chạm ID còn sót trong comment mã (phạm vi đã soát lại đầy đủ 27/09).** Bản sửa `f427eb7` cập nhật đánh số trong các file `.md`, nhưng **comment/docstring trong mã vẫn theo lược đồ CŨ (trước khi D-v3-2 được gán cho lần chạm niêm phong)**, tạo một lệch **off-by-one** cho cặp T24, ảnh hưởng cả hai nhãn:

- **per_event → phải là D-v3-3** (mã đang ghi `D-v3-2`): `v3/benign.py` dòng 11, 98, 264; `tests/v3/test_s8_benign.py` dòng 39. (Lưu ý: T23 agent ghi nhầm `config.py:98` — thực ra là `benign.py:98`; `v3/config.py` không có nhãn này.)
- **độ dài payload rút theo nền → phải là D-v3-4** (mã đang ghi `D-v3-3`): `v3/attackers.py:237`, `v3/rollout.py:122`, `v3/benign.py` dòng 19/193/197/244, `v3/payload.py` (7 chỗ: 33/47/131/174/198/236), `tests/v3/test_s8_benign.py:162`, `tests/v3/test_infra_glue.py:205`.
- **KHÔNG đụng `v3/dcm/T24.csv`**: dòng D8.benign đã dùng `D-v3-3` cho `V3_PER_EVENT` — tức đã đúng chuẩn.

Đây là lệch **nhãn tài liệu trong mã**, không đổi hành vi. **Đã thử sửa ngày 27/09 rồi hoàn tác**, vì: sửa comment trong `v3/benign.py` và `v3/payload.py` đổi `source_sha256` / `payload_source_sha256` mà `reference/v3_benign.json` ghim (`tools/v3_benign.py::protocol()`), làm test `test_drift_matched_on_four_surface_features` đỏ ("manifest stale"). Đóng lại đòi chạy `tools/v3_benign.py --write` (dựng lại corpus benign 797 sự kiện + đổi digest ghim, ghi mode "x" nên phải xử lý ghi đè). Vì việc này đổi **artifact đã ghim** và corpus benign dù sao cũng dựng lại ở P4/#8, nên **để chung vào bước #8**: (1) hai lượt thay theo THỨ TỰ trên từng file — `D-v3-3`→`D-v3-4` trước, rồi `D-v3-2`→`D-v3-3` (tránh dịch kép), trừ `T24.csv`; (2) `../.venv/bin/python tools/v3_benign.py --write` để làm mới manifest; (3) `tests/run_v3.py` xanh lại. Đã kiểm: không tệp nào trong phạm vi trên có sẵn `D-v3-4`, nên thứ tự hai lượt an toàn.

---

## 5. Số P2 đã đo (không phụ thuộc #5/#6/#7)

### 5.1. Giá tính toán đo được so với P0

Nguồn: `docs/reports/v3-p2-cost.md` + `../.venv/bin/python -m v3.grid --report`. Không chạy lượt eval nào; số eval chỉ đọc **hình dạng** đã ghim.

- **Mô hình đếm tái lập đúng P0** trên đơn vị của P0 (split phụ 26 wf): cả 6 khối khớp `v3-p0-chi-phi.md` §3 tới từng episode (`test_p0_model_reproduces_the_p0_cost_table`).
- **Sau khi cắt BR (mục 8), lõi = 11,48 triệu ≤ 16,39 triệu (−30%)** trên đơn vị P0 — đạt nghiệm thu T22. Khối H18 giảm 78%, K_d giảm 62%, độ nhạy giảm 20%.
- **Hai thứ làm số thật lớn hơn đơn vị P0 (không phải cắt, cần lưu ý):**
  1. Lưới ε của BR giữ {0,3; 0,6; 1,0} → lõi đã cắt lên **17,2 triệu (vượt P0 5%)**; cận trên 23,7 triệu.
  2. Eval chính đổi sang SWE-rebench-V2 96 wf (D-v3-1) → lõi 43,3 triệu (đơn vị P0), 65,5 triệu (hiệu chỉnh ε). Mô phỏng vẫn rẻ (9,5–20 CPU-giờ); cái đắt là **rollout headline** vì tỉ lệ với số workflow: R = 16 → 797 CPU-giờ (P0 tính 176). Ngân sách lõi 509–1.039 CPU-giờ của Q13 vì vậy chỉ còn đúng cho split phụ.
- **Giá bảng dòng 5 (đo lại dưới tải chuẩn):** hằng số đề nghị **≈ 2,9 ms/rollout (CPU, `--jobs 10`) ≈ 225 CPU-giờ** cho bản đầy đủ, tái lập ước lượng line5-se-diff 223,7 CPU-giờ (lệch 0,6%); nằm trong khoảng P0/plan 77–309 CPU-giờ. Hệ số phồng song song trên CPU-time chỉ 1,05× (1,85× cũ là của **wall-clock**, không vào CPU-giờ).
- Chưa tính (như P0): dựng bảng dòng 5 (~225 CPU-giờ, dev, không phụ thuộc số wf eval) và tinh chỉnh trên dev (~104 + ~35 CPU-giờ, T18).

### 5.2. M1 (thế giới v3, chạy từ đầu đến cuối trên dev)

Nguồn: `docs/reports/v3-p2-m1.md`. **7/8 cổng số đạt.** Đối chứng D28: V(Oracle) = 0 ở mọi (ρ, Δ); V(B1) giảm chặt theo ρ (0,775 → 0,163 ở Δ = 0); một episode B1 0,797 ms (≤ 1,1 ms). Cổng 3c (V(B1) phẳng theo Δ) **không đạt theo luật khai (2 seed)**, nhưng kiểm lại 6 seed cho thấy đây là **nhiễu mẫu** (mọi KTC của hiệu chứa 0), không phải lỗi thế giới. `test_v3_leaves_v2_freeze_clean` xanh.

### 5.3. Dòng 2–3 (giải chính xác)

Nguồn: `docs/reports/v3-p2-line23.md`. K = 4 nên KH ≤ 40 ⇔ H ≤ 10; eval rút H ~ U{6..14} nên ~5/9 wf rơi vào dòng 2. Dev (v2): 61/100 wf có H ≤ 10. Ngưỡng khả thi khai trước (≤ 10⁶ chuỗi, ≤ 60 s/wf); không đạt thì log `line23: infeasible` và chuyển dòng 5. Ba test xanh (`test_exact_matches_smallgame_on_coverage_reduction` khớp `smallgame.solve` tới 1e-6 trên 192 game).

### 5.4. Niêm phong eval

- `frozen/v3-unseal-log.jsonl`: **chưa tồn tại → nhật ký mở niêm phong RỖNG** (đúng cho P2: không lượt eval nào chạy).
- `frozen/V3-GATE4.json`: **vắng** (đúng — do tác giả ghi ở Cổng 4, chưa tới).
- Freeze v2 và D35 sạch; không file v2 nào bị sửa.

---

## 6. Sai lệch so với draft (ngoài sổ D-v3)

Từ `sentinel-v3.md` §12 của plan và các quyết định 27/09:

- **C14 / §8.** Draft/doc cũ: 36 wf / 18 họ hai lượt (Kish 6,48). Chốt: một lượt; chính 96 / 20 (Kish 19,86, D-v3-1), phụ 26 / 18 (Kish 10,24); ô Δ = 8 còn ít wf hơn.
- **Bảng điểm.** δ cũ ±5 điểm / ±0,03 → **Q12: 10 điểm / 0,10** (mức giảm tương đối / harm).
- **Algorithm 1.** Doc gọi "tám dòng"/"dòng 8"; draft có **10 dòng**, quarantine ở **dòng 8–9**. DCM đánh số theo draft (10 dòng).
- **Bảng dòng 5.** Doc gọi là "dự phòng"; **Q13** biến nó thành phương án **chính** ở mọi ô (rollout thật chỉ ở ô headline), có bằng chứng chi phí ở `v3-p0-chi-phi.md`.
- **Người ký.** Cổng 0 / Cổng 4 ghi "thầy ký"; theo quyết định 27/09 **tác giả quyết**, `frozen/V3-GATE4.json` do tác giả ghi.
- **Cổng benign P3 (T24).** Verdict **không đạt** (`hi_mean` 0,5793 > trần 0,56) sau khi đóng kênh kích thước bằng kiến tạo; nguyên nhân còn lại là `embedding_shift` — đọc là **bằng chứng ủng hộ cần detector đọc nội dung (C15)**, không phải lỗi benchmark.

---

## 7. Chỗ còn TBD (chỉ điền sau #5–#7) và bước cuối

Mọi ô dưới đây để **TBD** với lý do; không ghi 0 hay số bịa (N3).

| # | Chờ | Sẽ điền gì vào báo cáo khép |
|---|---|---|
| #5a | **T18 lượt tinh chỉnh đầy đủ** (`reference/v3_tuned.json`, `v3_tuned_nominal.json`) | **TBD** — giá trị τ / η_Q / τ5 thật theo từng ρ (3 kernel), khai mép η_Q; worst-case L. *Hiện chỉ có số kiểm-chứng-wiring, KHÔNG phải giá trị tinh chỉnh.* |
| #5b | **T14 bảng dòng 5 bản đầy đủ** (dựng sau tinh chỉnh, P4) | **TBD** — tỉ lệ ngăn rỗng, SE theo h, độ trung thành bảng–rollout bản cuối, digest bảng. *Hiện chỉ có pilot 3 ô headline; SE không đạt O12 ở pilot (12% khoá ≤ 0,09) — cần quyết R / ngưỡng.* |
| #6 | **T19 kiểm rollout headline** (`tools/v3_headline_rollout.py`, `v3-p2-rollout-check.md`) | **TBD** — |V_bảng − V_rollout| kèm CI ở ô headline (Δ ∈ {4,8}, χ = 1,33, mid, 4 ρ; R ∈ {16,32,64}); thời gian thật/episode. Nhãn "bảng lệch rollout" nếu hiệu > 0,10. |
| #7 | **T22 lượt toàn lưới đầy đủ** (`v3_run`, scorecard) | **TBD** — bảng điểm H1–H20, Table 2/Table 3 trên dev; đối chứng đọc trước; số episode thực tế so với dự phóng §5.1. *Smoke toàn lưới ở P2 chưa chạy trọn: còn chờ nối đủ lớp Sentinel (T15 đã có), B7 (T21 đã có), Sentinel-rollout (T19, #6), thế giới stage (T20 đã có).* |
| Bước cuối T23 | Sau khi #5–#7 điền xong | **Render lại `docs/v3/DCM.md`** (`tools/v3_dcm.py --render`) để thay bản cũ ở §2; xác nhận lại `run_v3.py` xanh và `v3_dcm.py --check` 0 vấn đề; commit. |

Danh sách O đã chốt (O1–O16) và L1/L2 đầy đủ nằm trong plan §1 và trong các mảnh DCM; bản khép cuối trích lại nguyên trạng cùng `result_ref` khi #7 điền số.

---

## 8. Tái lập (số ở báo cáo này)

```
cd auditgame
../.venv/bin/python tests/run_v3.py            # Every gate green: 3/3, 66/66, 155/155; 0 pending
../.venv/bin/python tools/v3_dcm.py --check     # 0 problem(s)
../.venv/bin/python -m v3.grid --report         # số episode theo khối, split phụ + chính
```

Bản khung dựng trên `int-p2` (`4be2744`); không sửa mã nào, nên cổng và DCM khớp `int-p2` sạch.
