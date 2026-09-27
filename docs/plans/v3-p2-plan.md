# Sentinel v3 — Kế hoạch triển khai P2 ("Sim v3 theo chữ")

27/09/2026.

**Nguồn:**
- `sentinel-v3.md` (C1–C16);
- `docs/reports/v3-p0.md` và `docs/reports/v3-p0-chi-phi.md`;
- mã v2 trong `auditgame/`;
- draft FSE-2027-15 bản 07/09, sha256 `c37643f0…263a`. Đã kiểm lại: bản ở `docs/` trùng bản ở `261-Master-Proposal/`.

> **Cho người thực thi:** làm theo từng đợt ở mục 9. Task cùng đợt chạy song song, mỗi task trong một git worktree riêng, tách từ nhánh `v3`. Làm TDD: viết test mang tên câu draft trước, rồi mới viết mã. Plan này không chứa mã triển khai.

## Mục tiêu

Dựng sim v3 bám chữ draft:
- payload sleeper, lan qua nhiều carrier, gỡ cả carrier;
- mọi điểm C là một công tắc; trục ρ có ở mọi thế giới;
- Sentinel chạy đúng các dòng của Algorithm 1:
  - dòng 1: post-mortem;
  - dòng 2–3: giải chính xác, hoặc in bằng chứng bất khả;
  - dòng 5: **bảng tính trước (L1) ở mọi ô**, và rollout thật chỉ ở ô headline;
  - dòng 7: particle filter 2048 hạt;
  - dòng 8–9: gỡ cả carrier;
- DCM có test xanh cho mọi dòng thuộc P2;
- toàn bộ pipeline chạy được trên dev;
- tập eval được niêm phong tới P5.

## Không thuộc P2

- **P3:** giá audit đo thật, detector học, 620 thay đổi lành, payload đã công bố, 3 LLM attacker, hiệu chuẩn agent.
- **P4:** tinh chỉnh thật trên dev, dựng bảng dòng 5 bản cuối (sau tinh chỉnh), freeze.
- **P5:** mọi lượt chạy trên eval, kể cả rollout headline.

P2 để sẵn giao diện cắm cho các thành phần P3. Bảng dòng 5 trong P2 chỉ dựng bản pilot.

### Cổng: hiệu chuẩn agent (P3) chặn P4, không chặn P2

Hiệu chuẩn agent thật — đo `p = P(bản vá mang marker | payload được truy xuất)` — nằm trong P3, và phải **xong trước khi vào P4**. Tiền đăng ký: `docs/preregistration/TIEN-DANG-KY-P0.5-Hieu-Chuan-Agent-That.md`; plan thi hành: `docs/design/plans/2026-09-27-P0.5-Hieu-Chuan-Agent-That-Plan.md`.

**P2 không bị chặn.** `adoption_rate` là một field của `agent.MockAgent` mà `world_v2.StagedMockAgent` kế thừa, nên P2 dựng máy và `p` chỉ là một núm cắm vào sau. Giá trị của P2 không phụ thuộc `p` bằng bao nhiêu.

**P4 thì bị chặn, và bổ đề tỉ lệ KHÔNG che được chỗ này.** Bổ đề chỉ nói mức giảm *tương đối* bất biến theo `p`. Nhưng C6 đã chốt tinh chỉnh theo `L = harm + λ_Q·Q_false + λ_T·T_lost`, trong đó `Q_false` và `T_lost` **không phụ thuộc adoption** — chúng là hàm của chính sách audit và bộ dò. Chỉ `harm` co giãn theo `p`. Nên khi `p` nhỏ hơn 0,85 nhiều lần, cán cân của `L` dịch hẳn về phía phạt cách ly, và nghiệm tối ưu — `η_Q` lẫn hỗn hợp — dịch theo. Ở `p` đủ nhỏ, nghiệm hội tụ về B1 không cách ly.

Tinh chỉnh và freeze ở `adoption_rate = 0,85` rồi mới đo ra `p` nhỏ hơn nhiều, thì bộ mixture đã tối ưu cho một thế giới không tồn tại, và sửa nó là một nghiên cứu mới — đúng cái bẫy v2 đã dính với thư viện belief bị khoá.

Hệ quả cho thứ tự làm: **đẩy hiệu chuẩn agent lên đầu P3**, không để cuối. Nó tốn vài ngày và khoảng 10 USD, trong khi nó quyết định `p` mà cả P4 đứng trên.

## Đánh số dòng

DCM đánh số dòng Algorithm 1 theo draft, gồm 10 dòng. "Dòng 8" trong `sentinel-v3.md` tương ứng với dòng 8–9 của draft (mục 12).

---

## 1. Quyết định đã chốt

Người dùng chốt ngày 27/09. Không có chữ ký của thầy; người dùng là người quyết.

| # | Quyết định | Điểm | Task |
|---|---|---|---|
| Q1 | Cấu hình chính: A0 (commit chỉ đọc patch) × quét carrier × ρ ∈ {0; 0,25; 0,5; 1} (trục độ lộ nội dung) × tổn hại chốt tại σ × insertion audit thấy ingress × drift thoáng qua × gieo 1 carrier | C1, C2, C11 | T1, T5, T6 |
| Q2 | Độ nhạy: đổi một yếu tố mỗi lần | §9 v3 | T1, T20 |
| Q3 | Payload sleeper có vị từ đích; lan note → skill → patch → branch; gỡ cả carrier | C8, §4 | T3, T4, T6 |
| Q4 | Δ̂ từ post-mortem cùng ô, thứ tự ghim; phân vị thấp, tiên nghiệm khi chưa có dữ liệu; in đường học | L1, C12 | T10 |
| Q5 | Δ cố định theo ô; thêm cột "attacker chọn Δ" | C10 | T7, T10 |
| Q6 | χ ∈ {1,04; 1,33; 2,11}, dựng bằng cấu hình độ sâu cố định theo ô, thứ tự (memory, queue, skill, commit): (3,3,2,1), (3,2,1,1), toàn 1; chi phí tuyến tính theo độ sâu. Arm "χ chỉ đổi giá" nằm trong lưới H18 | C3, C16 | T1, T16 |
| Q7 | K_d ∈ {1, 2, 3} là một trục | H19 | T1, T4, T16 |
| Q8 | H18: b1 và {2; 1; 0,5} × B_min(Δ). Ngân sách chặn thì B1 giảm đều độ sâu commit | C4, H18 | T8, T16 |
| Q9 | 10 seed | L2 | T1 |
| Q10 | Eval C14 một lượt: 26 workflow / 18 họ, seed builder 2027, không dùng lại instance, trọng số theo workflow; có thể thay nếu tìm được nguồn tốt hơn. Dev là corpus v2 (100 workflow) | C14 | T2 |
| Q11 | Detector: mô hình khai báo, d′ ∈ {1,52; 2,21; 2,96}. Detector học làm sau | C15 | T5 |
| Q12 | Bảng điểm theo luật P, D, E, N, G; δ = 10 điểm (mức giảm tương đối), 0,10 (harm) | T4 | T17 |
| **Q13** | **Dòng 5 dùng bảng tính trước (L1) làm Sentinel chính ở mọi ô**, vì rollout mỗi task không khả thi: 228 ngày tới khoảng 105 năm (`v3-p0-chi-phi.md` §4). Rollout thật, 16–64 lần rút cho mỗi cặp (member, lớp attacker), chỉ chạy ở ô headline của Table 2 và được in cạnh bản dùng bảng. Ngân sách tính toán lõi: 509–1.039 CPU-giờ | Algorithm 1 dòng 5, L1 | T12, T14, T19 |
| **Q14** | Cắt các khối best response (mục 8) | `v3-p0-chi-phi.md` §6.3 | T22 |

### Kiểm số χ

Giá 0,4 / 0,9 / 1,6 / 4,1, chi phí tuyến tính theo độ sâu:

| Cấu hình độ sâu | κ | χ_range |
|---|---|---|
| (3,3,2,1) | (1,2; 2,7; 3,2; 4,1) | 2,9 / 2,8 = **1,036** |
| (3,2,1,1) | (1,2; 1,8; 1,6; 4,1) | 2,9 / 2,175 = **1,333** |
| toàn 1 | (0,4; 0,9; 1,6; 4,1) | 3,7 / 1,75 = **2,114** |

Commit ở độ sâu 1 trong **cả ba** ô χ. Vì vậy:
- b1 = 4,1·H ở mọi ô;
- B1 không còn chỗ để "giảm đều độ sâu commit" (R7).

### Ô headline (Table 2, C5)

Δ ∈ {4, 8}, χ = 1,33 (mức gần 1,34 nhất), detector vừa (d′ = 2,21), từng ρ.

### Giá trị L1 phải khai trong DCM trước khi viết mã của task tương ứng

**Đã chốt 27/09 (@truong):** chấp nhận cả 16 mặc định dưới đây, riêng O3 dùng q = 0,1 (theo C12 của `sentinel-v3.md`). Dòng DCM tương ứng vẫn phải ghi trước khi viết mã của task.

| # | Điểm | Đề xuất mặc định | Task |
|---|---|---|---|
| O1 | K_d của cấu hình chính | 2 (DELEGATED = {skill, queue}, D20 v2). K_d = 1 → {skill}; K_d = 3 → {skill, queue, memory} | T1 |
| O2 | Phạm vi truy xuất của sleeper, tách khỏi vị từ đích | Truy xuất: mọi task sau ι đều truy xuất được (ghi chú dùng chung, như t2 của Fig. 1). Vị từ đích: luật θ của v2 trên topic của σ. Planner chọn σ sao cho không task nào trong (ι, σ) thoả vị từ | T3 |
| O3 | Phân vị q, số quan sát tối thiểu, tiên nghiệm Δ̂₀ | q = 0,1; cần ít nhất 1 post-mortem; Δ̂₀ = 1. Nếu Δ̂ không trùng mức nào của lưới thì làm tròn xuống mức gần nhất (Hệ quả 6.6) | T10 |
| O4 | Nội dung post-mortem | Luôn công bố (k, ι, σ) thật sau mỗi workflow, kể cả khi không có harm | T10 |
| O5 | Lớp attacker ở cột "attacker chọn Δ" | Mỗi chuỗi dùng một Δ cố định; thêm một hỗn hợp khai trước: mỗi workflow rút Δ đều trên lưới | T7 |
| O6 | B1 khi ngân sách chặn mà commit đã ở độ sâu 1 | Giảm đều độ sâu (nếu còn > 1), rồi bỏ commit ở các task cách đều | T8 |
| O7 | Kế toán khi gỡ cả carrier | FQ = một lần gỡ carrier có c_t[k] = 0. Gỡ branch làm mất các patch sạch đã giải trong branch; số này cộng vào clean lost | T6 |
| O8 | Kênh checkpoint | ψ_c = φ_c: không mang thông tin về poison (t6 của Fig. 1: "passes tests") | T5 |
| O9 | d′ provenance của A7 | Giữ chỗ bằng d′ của detector; P3 đo thật | T5 |
| O10 | Trục thay cho độ sâu trong họ RO | Độ sâu cố định theo ô làm RO-d2 và RO-d3 trùng nhau. Thay bằng trục pha: pha ngẫu nhiên, hoặc bắt đầu ở carrier có hậu nghiệm cao nhất | T11 |
| O11 | β online | β nền lấy từ lượt sạch trên dev; cập nhật bằng post-mortem cùng ô (báo động nằm ngoài (k, [ι, σ)) tính là drift) | T9, T10 |
| O12 | Sai số Monte Carlo của dòng 5 | Bảng: SE mỗi ô bảng ≤ 0,09 (R = 32). Rollout headline: in SE, không lấy SE làm cổng | T14, T19 |
| O13 | N_A = 1 (mỗi hạt mang sẵn (k, ι, σ), dùng chung rollout cho mọi lớp attacker) | **Không dùng**: giữ nghĩa của "max theo π_A". Chỉ bật khi người dùng quyết, và phải khai | T12 |
| O14 | Ngân sách chặn (H18) trong chế độ bảng | Bảng không có khoá ngân sách. Dòng 5 loại member có hành động ở t vượt B_t; không còn member nào thì chọn "none" | T12, T16 |
| O15 | Bảng dùng ở thế giới độ nhạy và ở K_d ≠ 2 | Dùng bảng của thế giới chính, khai là "mô hình của Sentinel sai lệch một yếu tố". Bảng riêng cho từng thế giới là tuỳ chọn, có giá (R16) | T14, T20 |
| O16 | Đặc trưng của ngăn belief | p_attack chia 5 mức theo phân vị trên dev × carrier có hậu nghiệm cao nhất (4) × cờ "khối lượng trên carrier uỷ nhiệm > ½" (2) = 40 ngăn. Ngăn rỗng thì dùng ngăn gần nhất cùng h và ghi lý do (N3) | T14 |

---

## 2. Ràng buộc chung

**Nơi chạy.** Mọi lệnh chạy từ `HCMUT/code/Sentinel/auditgame/`. Tool nào cần scipy/numpy thì gọi bằng `../.venv/bin/python` (đã ghim trong `uv.lock`). Numpy chỉ dùng cho PF, rollout và bảng; lõi thế giới giữ stdlib như v2.

**Giữ v2 để gói tái lập v2 vẫn chạy được.**
- Không sửa:
  - file nào trong `freeze.SOURCE` hay `freeze.TABLES`;
  - `addendum_d35.py`, `freeze_d35.py`;
  - các tool v2 (`tools/run_draft_eval.py`, `tools/select_mixture.py`, `tools/v3_p0_*.py`).
- v3 nằm trong package mới `auditgame/v3/` và các tool `tools/v3_*.py`. v3 import từ v2, không vá v2.
- Test `test_v3_leaves_v2_freeze_clean` là bắt buộc. Nó đòi:
  - `freeze.header_line()`, gọi sau `costs.install(P)`, báo `freeze: clean sha256:c789fa7362e0`;
  - `freeze_d35.clean(...)` đúng.

**Tinh chỉnh.** Không tinh chỉnh theo số dự phóng của draft. P2 chỉ chạy smoke trên dev.

**Eval.** Không chạm eval (mục 6). Lượt P5 do người dùng tự gọi; trợ lý AI không tự chạy (D30, D35).

**Seed và N3.**
- Seed chỉ lấy từ `core.seed_of(...)`. Không dùng `hash()`, không dùng `random` ở cấp module. Numpy `Generator` được seed từ `seed_of`.
- N3: cấu hình không dựng được thì bỏ khỏi mẫu số và ghi lý do.

**DCM và test.**
- Mỗi lựa chọn L1/L2 có dòng DCM trước commit mã tương ứng.
- Test theo T3: tên test là câu draft nó bảo vệ; docstring chứa ID DCM và trích nguyên văn câu draft.

**Worktree.**
- Mỗi task làm trong worktree riêng: `git worktree add ../wt-v3-T<nn> -b v3-T<nn> v3`.
- Task chỉ sửa **file mình sở hữu** (mục 9).
- Xong task thì rebase lên `v3` và merge fast-forward. Đợt sau chỉ bắt đầu khi mọi task của đợt trước đã merge và `tests/run_v3.py` xanh trên `v3`.
- `config.py` và `api.py` (T1) đóng băng giao diện sau đợt 0. Muốn đổi thì phải qua một "vá giao diện" riêng, merge vào `v3` trước các task phụ thuộc.

---

## 3. Kiến trúc và bản đồ tái dùng

### Bố cục

```
auditgame/v3/
  config.py        công tắc (WorldV3), ô (Cell), PRIMARY, sensitivities(), hằng số v3
  api.py           giao thức và kiểu dùng chung: PolicyV3, Observation, EpisodeRecord,
                   BeliefAPI, EpisodeState (snapshot/resume), PostMortem, L5Source
  dcm/T<nn>.csv    mảnh DCM của từng task (mục 5)
  corpus.py        dev = corpus v2; builder eval C14 một lượt (chỉ trả digest)
  seal.py          niêm phong eval
  state.py         c_t ∈ {0,1}^4 suy từ store và vết derived_from
  payload.py       SleeperPayload, plan_sleeper_all (C8)
  agent.py         SleeperMockAgent: lan truyền, uỷ nhiệm theo K_d, ingress, drift
  observe.py       detector khai báo, commit review (ρ, A0/A7), checkpoint, hàm likelihood
  oracle.py        harm chốt/gỡ được, đọc cuối horizon
  runner.py        một episode, cộng snapshot/resume (cho rollout)
  sequence.py      chạy các workflow của một ô theo thứ tự ghim, mang post-mortem
  attackers.py     18 scripted / 7 held-out, BR (k, ι, ε[, Δ]), gieo 2 carrier
  baselines.py     B1–B6, cost-greedy, SW ngẫu nhiên, B1-prov, Oracle
  belief_pf.py     particle filter 2048 hạt, numpy
  belief_exact.py  bộ liệt kê chính xác làm chuẩn (H nhỏ)
  delta_hat.py     dòng 1
  library.py       28 member, ba họ
  rollout.py       động cơ rollout từ hạt (dùng runner.resume)
  line5.py         LP argmin_π max_πA L̂; hai nguồn L̂: TableSource, RolloutSource
  line5_table.py   ngăn belief, schema, tra bảng
  line8.py         dòng 8–9
  exact.py         dòng 2–3
  sentinel.py      lắp Algorithm 1, ablation, V3_REGISTRY
  budget.py        B_min(Δ), mức ngân sách, κ của arm "chỉ đổi giá", lịch khối
  grid.py          lưới main / sensitivity / h18 / kd / headline-rollout, gồm cả phần cắt BR
  stage_world.py   thế giới kiểm theo giai đoạn (C2)
  smallgame_v3.py  port 28 member sang 240 game nhỏ (H7, B7)
  metrics.py       bảy chỉ số §9.3, wild cluster bootstrap, BH, đường học
  scorecard.py     luật P, D, E, N, G
  freeze_v3.py     manifest v3 xếp lớp trên freeze v2
```

### Tái dùng từ v2

| Module v2 | v3 dùng gì | Cách dùng |
|---|---|---|
| `core.py` | `Item` (có `derived_from`), `CarrierStore`, `CARRIERS`, `seed_of`, `PoisonSpec` | Import nguyên. Gỡ cả carrier = vòng `quarantine` trên `live(k)` trong runner v3 |
| `build.py` | `marker_for`, `payload_content`, `PAYLOAD_LENGTH`, nội dung của `inject` | Import. Planner viết mới vì C8 bỏ ràng buộc ngủ yên |
| `retrieval.py` | `payload_topic_like`, `retrieved`, `THETA` | Vị từ đích |
| `world_v2.py` | `drift_content`; logic `DriftDetector` (drift_visible, ρ, d1, điểm độc lập D16); khái niệm `DELEGATED` | Bọc (compose). `DELEGATED` thay bằng bản đồ K_d |
| `agent.py` | Tỉ lệ của `MockAgent` (0,62 / 0,85 / 0,55 / 0,35) | Kernel danh định |
| `detector.py`, `scoring.py` | `Detector.from_operating_point`, `at_depth`, `fires`; `carrier_score`, `PI0` | Import |
| `carrier_runner.py` | `rs_of`, `survives`, thứ tự trong task (D3), các trường của `EpisodeResult` | Gọi hàm; mẫu cho runner v3 |
| `carrier_policies.py` | Logic `act` của B1–B6; `_SW`, `_TAUS`, `_FLOORS`; `OracleControl` | Adapter sang `api.PolicyV3` |
| `belief.py`, `belief_v2.py` | Liệt kê cửa sổ và giả thuyết NULL; công thức drift cạnh tranh; `item_posterior` | Chuẩn chính xác cho PF |
| `sentinel.py`, `addendum_d35.py` | `VARIANTS`, mẫu `REGISTRY`/`make_policy`; ý tưởng arm Δ sai | Mẫu |
| `attackers_v2.py` | `_RULES`, `held_out()`, `behavior_keys`, `tuning_attack_names`, `br_attacks` | Import rồi ánh xạ lên planner sleeper |
| `draft_setup.py` | `DELTAS`, `TARGET_KAPPA_DRAFT`, `SWEEP_CARRIERS`, `chi_range`, `kappa_bar`, `RHO_PATCH_GRID`, `SEEDS`, `ZETA`, `ETA_Q_GRID`, `BudgetSpec` | Import, không chép |
| `corpus_v2.py` | `make_corpus_v2()` (dev 100), `kish`, RNG của builder | Import |
| `metrics.py`, `metrics_v2.py` | `loss` và λ; `harm_table`, `value`, `crossfit_value`, `controls`, `side`, `gain_vs_best`, `gain_ci` | Import. `gain_ci` làm kiểm chéo phụ |
| `oracle.py`, `runner.hidden_ok_of` | `harm_of`, `default_oracle` | Import |
| `freeze.py`, `freeze_d35.py` | `_digest`, `header_line`, `require_frozen`, `pin_conflicts`; mẫu manifest xếp lớp, `clean()` | Mẫu cho `freeze_v3.py` |
| `tools/run_draft_eval.py` | `Refused`, `refusal`, `provenance`, `pin_records`, đọc shard (`Records`, `_load`) | Chép mẫu sang `tools/v3_run.py`, không import tool v2 |
| `tools/select_mixture.py` | `KERNELS` (ζ = 0,10), LP có ràng buộc FQ, luật hoà D32 | Mẫu cho `tools/v3_tune.py` |
| `gate_world.py` | Ngữ nghĩa `_Gates`, `STAGE_KAPPA` | Cho `stage_world.py` (C2) |
| `smallgame.py`, `lp.py` | `games`, `solve`, `tv`, `feasible`, `simplex_max` | Chuẩn chính xác, B7, H7, LP của dòng 5 |
| `tools/v3_p0_corpus.py` | `cut`, luật "H = cỡ họ" | Viết lại trong `v3/corpus.py`; test so digest với `spikes/v3-p0/corpus.json` |
| `theory/checks/thm4_budget.py`, `coverage.py` | Công thức Định lý 5.6, `block_schedule` (Mệnh đề 5.7), `minimax` | Port sang `v3/budget.py`; test so số với script |
| Script đo của `v3-p0-chi-phi.md` (scratchpad) | Cách đo clone + rollout (7,4 ms mỗi bộ) | Ý tưởng cho `runner.resume` và `tools/v3_build_table.py` |

---

## 4. Công tắc và ô thí nghiệm

### Biểu diễn

`v3/config.py` có hai dataclass frozen:
- `WorldV3`: các công tắc mô hình;
- `Cell`: các trục của lưới.

Cấu hình chính và các độ nhạy:
- `PRIMARY = WorldV3()` mang các giá trị chính.
- `sensitivities()` trả danh sách `(tên, WorldV3)`. Mỗi phần tử khác `PRIMARY` đúng một trường, và có test khoá điều này.

Nhận diện ô:
- Mỗi record ghi đủ trường của `WorldV3` và `Cell`, cộng `world_id` và `cell_id`.
- `cell_id` là 12 ký tự đầu của sha256 trên JSON chính tắc của ô.
- `cell_id` đồng thời là khoá lịch sử của Δ̂ và khoá của bảng dòng 5.

### Bảng công tắc

| Công tắc / trục | Trường | Giá trị (in đậm là chính) | C | Mức | Nơi tác động |
|---|---|---|---|---|---|
| Provenance ở commit | `WorldV3.provenance` | **A0**, A7 | C1 | L2 | `observe` |
| Cách đọc k | `WorldV3.audit_reading` | **carrier**, stage | C2 | L2 | `runner` hoặc `stage_world` |
| Tổn hại sau σ | `WorldV3.harm` | **locked**, reversible | C11 | L2 | `oracle` |
| Ingress | `WorldV3.ingress_visible` | **True**, False | §10.6, H8 | L1 | `observe` (insertion = audit memory) |
| Drift | `WorldV3.drift` | **transient**, persistent | Mệnh đề 5.11 | L1 | `agent`, `observe` |
| Gieo | `WorldV3.n_seeded` | **1**, 2 | §4 | L1 | `attackers` |
| Kernel thế giới | `WorldV3.kernel` | **nominal**; low/high chỉ khi tinh chỉnh | ζ | L0 | `agent` |
| Nguồn dòng 5 | `WorldV3.line5` | **table**, rollout (chỉ ô headline) | Q13 | L1 | `line5` |
| ρ | `Cell.rho` | 0; 0,25; 0,5; 1 (cả bốn nằm trong cấu hình chính) | D20 | L1 | `observe` |
| K_d | `Cell.k_delegated` | 1, **2**, 3 | H19 | L1 | `agent` |
| χ | `Cell.chi` | "1.04" → (3,3,2,1); **"1.33"** → (3,2,1,1); "2.11" → (1,1,1,1) | C3, C16 | L2 | giá và độ sâu trong `runner` |
| Δ | `Cell.delta` | 0, 1, 2, 4, 8, "attacker" | C10 | L0 + L1 | `attackers`, `delta_hat` |
| Detector | `Cell.dprime` | 1,52; **2,21**; 2,96 | C15 | L1 | `observe` |
| Ngân sách | `Cell.budget` | **b1**; 2, 1, 0,5 × B_min(Δ); cờ `price_only` | C4, H18 | L2 | `runner`, `budget` |

---

## 5. Ma trận tuân thủ draft (DCM, T2)

### Nơi đặt

- **Mảnh theo task:** `auditgame/v3/dcm/T<nn>.csv`. Mỗi task sở hữu đúng một mảnh, nên các worktree song song không đụng nhau.
- **Bản tổng hợp:** `tools/v3_dcm.py --render` ghép các mảnh thành `docs/v3/DCM.md`, kèm trạng thái test của lần chạy gần nhất. Chỉ T0 và T23 sinh file này; không sửa tay.
- **Bản chữ của draft:** `docs/v3/draft-2026-09-07.txt` (pdftotext), ghim kèm sha256 của cả PDF lẫn bản chữ.
- `freeze_v3` hash toàn bộ thư mục `v3/dcm/`.

### Định dạng

CSV UTF-8. Mỗi dòng là một cặp (câu quy định của draft, test bảo vệ nó). Một ID có thể xuất hiện ở nhiều mảnh; bản tổng hợp gộp các dòng theo ID. Dòng đầu mỗi mảnh là chú thích `#` ghi sha256 của PDF.

| Cột | Nội dung |
|---|---|
| `id` | `D<mục>.<tên>`, ví dụ `D4.state`, `D4.def1`, `DF1.t2`, `DA1.l5`, `D5.3.rand`, `D7.pf2048`, `D8.chi`, `D9.seeds` |
| `where` | Mục / trang / dòng lề của draft |
| `quote` | Trích nguyên văn một câu; cho phép `…` để lược |
| `level` | L0 / L1 / L2 |
| `c_ref` | C1–C16, Q1–Q14, O1–O16, D-số của v2 |
| `decision` | v3 dựng thế nào, một câu |
| `module` | Đường dẫn trong `auditgame/` |
| `test` | `tests/v3/<file>.py::<Class>::<test_name>` |
| `phase` | P2 / P3 / P4 / P5: pha chịu trách nhiệm làm test xanh |
| `result_ref` | Ô bảng hoặc trường record sẽ nhận kết quả (điền ở P5) |

### Cổng kiểm

`tools/v3_dcm.py --check` kiểm sáu điều:
1. Cặp (`id`, `test`) là duy nhất trên mọi mảnh.
2. Mọi dòng có `phase=P2` trỏ tới một test tồn tại và xanh.
3. Mọi test trong `tests/v3/` hoặc có dòng DCM, hoặc là test hạ tầng (`test_infra_*`).
4. Mọi `quote` có mặt nguyên văn trong bản chữ đã ghim, sau khi chuẩn hoá khoảng trắng.
5. sha256 của PDF khớp T1.
6. Docstring của test chứa đúng `id`.

Cổng G2 (100% dòng có test xanh) chỉ khép được sau P3. P2 khép phần `phase=P2`.

---

## 6. Niêm phong tập eval tới P5

Tập eval là danh sách instance, không phải kết quả. Thứ cần niêm phong là mọi lượt mô phỏng, dựng bảng hay tóm tắt chạy trên nó. Niêm phong dùng lại D33 của v2 và có năm lớp.

1. **Chỉ lộ digest.**
   - `v3/corpus.py` có `eval_digest()`: dựng split C14 một lượt (seed 2027) và chỉ trả sha256 của danh sách instance theo thứ tự ghim.
   - Hằng `EVAL_SPLIT_SHA256` được commit ở T2.
   - Không có hàm công khai nào trả workflow eval.
2. **Token.** `seal.eval_workflows(token)` chỉ nhận một `Unsealed`. `seal.unseal(run_meta)` chỉ trả token khi đủ năm điều kiện:
   - freeze v2 clean và không có PIN CONFLICT;
   - `freeze_v3.header_line()` clean;
   - `git status --porcelain auditgame/` rỗng;
   - có `frozen/V3-GATE4.json` do người dùng ghi ở Cổng 4, chứa digest manifest v3, digest luật bảng điểm và digest bảng dòng 5, và các digest này khớp bản sống;
   - `split == "eval"` được truyền tường minh.

   Thiếu một điều thì raise `SealedSplit` kèm lý do.
3. **Nhật ký chạm.** Mọi lần gọi `unseal` được ghi thêm một dòng vào `frozen/v3-unseal-log.jsonl`. Đây là bằng chứng cho "một lượt" của T6.
4. **Chặn tĩnh.** Test `test_no_v3_module_reads_eval_outside_seal` quét `v3/` và `tools/v3_*.py` và cấm ba thứ:
   - gọi `eval_workflows(` ở ngoài `tools/v3_run.py` và `tools/v3_headline_rollout.py`;
   - đọc `spikes/v3-p0/corpus.json`, trừ test so digest;
   - dùng literal `split="eval"` ở ngoài hai tool trên và `seal.py`.

   `tools/v3_build_table.py` và `tools/v3_tune.py` không có đường nào tới eval.
5. **Chặn khi tóm tắt.** Bộ tóm tắt từ chối record có `split=eval` nếu manifest không clean (mẫu `Refused`/`refusal`). Record được ghim bằng `pin_records`.

**Dev.** Dev là 100 workflow của `corpus_v2`, gồm cả 57 workflow eval của v2. Tập này đã bị chạm, nên chỉ còn vai trò dev. Test khẳng định dev và eval không chung họ, không chung instance.

---

## 7. Mốc đầu tiên (M1): thế giới v3 với baseline, chạy từ đầu đến cuối trên dev

**Vì sao làm lát này trước.** M1 kiểm thế giới trước khi xây Sentinel, phần đắt nhất. Các thành phần được kiểm là sleeper, lan truyền, gỡ cả carrier, harm chốt và L. Đối chứng và hình dạng của B1 không phụ thuộc Sentinel. Nếu thế giới lệch lý thuyết thì sửa thế giới, không tinh chỉnh.

**Phạm vi.**
- Đợt 0–3: T0–T9, trừ T9 không bắt buộc cho M1.
- Task tích hợp `M1`.
- Baseline: B1, B2, B3, B4, Oracle.

**Lát chạy.** Cấu hình chính; cả 4 mức ρ; χ = 1,33; detector vừa; K_d = 2; Δ ∈ {0, 1, 4}; 2 seed; 100 workflow dev; 18 cột scripted và BR cross-fit.

**Nghiệm thu.**
1. Xanh:
   - `test_figure1_replays_t1_to_t7`;
   - `test_state_is_carrier_bitvector_with_propagation`;
   - `test_attacker_menu_matches_cell`;
   - `test_ingress_visibility_is_a_switch`;
   - `test_one_action_per_task_within_budget`;
   - `test_checkpoint_channel_declared`;
   - `test_quarantine_removes_whole_carrier`;
   - `test_harm_read_at_horizon_end`;
   - `test_loss_matches_definition_1`.
2. Đối chứng D28 trên dev:
   - Oracle có V ≤ 0,05 ở Δ = 4;
   - ở Δ = 0, không baseline nào chỉ quét carrier thắng B1.
3. Kiểm chiều của B1, khai trước (không kiểm con số):
   - V(B1) không tăng theo ρ;
   - ở ρ = 0, B1 bỏ sót mọi harm chỉ đi qua đường uỷ nhiệm;
   - V(B1) gần phẳng theo Δ.

   Không đạt thì tìm lỗi trong thế giới, không chỉnh tham số.
4. Một episode B1 chạy ≤ 1,1 ms, tức ≤ 2 lần v2 (GĐ 3 của báo cáo chi phí). Có log thời gian.
5. `test_v3_leaves_v2_freeze_clean` xanh.

**Thời điểm.** Khoảng ngày thứ 9 theo đường tới hạn (mục 9).

---

## 8. Ngân sách tính toán và phần cắt best response (Q13, Q14)

### Ngân sách

Số liệu từ `v3-p0-chi-phi.md`. Máy M5, 10 nhân; thời gian thật = CPU-giờ / 5,7.

| Khối | Khi nào | CPU-giờ |
|---|---|---|
| Mô phỏng mọi khối, Sentinel dùng bảng (giá tra bảng ≈ 0,94 ms mỗi episode) | P5 (smoke dev ở P2) | ≈ 24; sau khi cắt BR còn ít hơn |
| Dựng bảng dòng 5: 36 ô (4 ρ × 3 χ × 3 detector) × 5 Δ̂ × 14 độ dài còn lại × 20–40 ngăn × 28 member × 6 lớp attacker × R = 32–64 | Bản cuối ở P4, sau tinh chỉnh. P2 dựng pilot ở ô headline (≈ 4/36 khối lượng, khoảng 9–34 CPU-giờ) | 77–309 |
| Rollout thật ở ô headline (Sentinel; 7 held-out + BR; R = 16–64) | P5, in cạnh bản bảng. P2 chỉ smoke trên dev (≈ 8 CPU-giờ) | 176–706 |
| Tuỳ chọn: ablation và Δ-oracle bằng rollout ở headline, R = 16 | P5, chỉ khi người dùng bật | +235 |
| **Lõi** | | **509–1.039**, tức 3,7–7,6 ngày với `--jobs 10` |

### Phần cắt best response

Phần cắt được định nghĩa trong `v3/grid.py` (T22) và hash vào manifest:

| Khối | Giữ lại |
|---|---|
| Lưới chính | BR ở detector headline, mọi (ρ, χ), mọi Δ (như D27) |
| Cột "attacker chọn Δ" | BR chỉ cho các hệ thống lớp Sentinel. Baseline không phụ thuộc Δ nên max theo Δ đọc lại từ khối BR chính |
| Độ nhạy và K_d | BR chỉ cho B1 và Sentinel, chỉ ở Δ ∈ {4, 8} |
| H18 | BR chỉ ở χ = 1,33 và hai mức b1, 2 × B_min; các mức khác chỉ chạy held-out. Khối H18 giảm khoảng 70% |
| Gieo 2 carrier, BR trên cặp vị trí (khối 4\*) | Tắt trong lõi |
| N_A = 1 | Không bật (O13) |

---

## 9. Đợt song song, quyền sở hữu file và công sức

### Đợt

Task cùng đợt độc lập với nhau: không task nào import module mà task kia đang viết, trừ `config.py` và `api.py` đã đóng băng.

| Đợt | Task (song song) | Điều kiện vào | Dài nhất |
|---|---|---|---|
| W0 | T0 → T1 (tuần tự, một agent) | — | 2,5 ngày |
| W1 | T2, T3, T5, T8, T16a, T17 | W0 đã merge | 1,5 (T3); T17 chạy tiếp 2 ngày |
| W2 | T4, T7 | T3 | 2 (T4) |
| W3 | T6, T9 | T4, T5 | 2,5 |
| M1 | M1 (tích hợp, một agent) | T2, T6, T7, T8, T17 | 0,5 |
| W4 | T10, T11, T13 | T6, T9, T8 | 1,5 |
| W5 | T12, T21 | T7, T9, T11 | 2,5 (T12) |
| W6 | T14, T18 | T12 | 2 (T14), cộng giờ máy của bảng pilot |
| W7 | T15 | T10, T12, T13, T14 | 1,5 |
| W8 | T16b, T19, T20, T22 | T15 | 2 |
| W9 | T23 | tất cả | 0,75 |

**Đường tới hạn** khoảng 19–20 ngày, tức khoảng 4 tuần, khớp mức 3–4 tuần của lộ trình. **Tổng công** khoảng 38 ngày công. Mức song song cao nhất là 6 agent, ở W1.

Chưa tính giờ máy:
- dựng bảng pilot trong P2: khoảng 2–6 giờ thật;
- dựng bảng cuối trong P4: 77–309 CPU-giờ.

### Quyền sở hữu file

Mọi đường dẫn tương đối với `auditgame/`. Mỗi task sở hữu mảnh `v3/dcm/T<nn>.csv` của mình, nên cột dưới đây không ghi lại mảnh DCM.

| Task | File sở hữu (tạo và sửa) |
|---|---|
| T0 | `v3/__init__.py`; `v3/dcm/README.md`; `tools/v3_dcm.py`; `../docs/v3/draft-2026-09-07.txt`; `../docs/v3/DCM.md` (bản đầu); `tests/run_v3.py`; `tests/v3/__init__.py`; `tests/v3/test_infra_dcm.py`; `tests/v3/test_infra_v2_intact.py` |
| T1 | `v3/config.py`; `v3/api.py`; `tests/v3/test_s8_config.py`; `tests/v3/test_infra_config.py` |
| T2 | `v3/corpus.py`; `v3/seal.py`; `tests/v3/test_s8_corpus.py`; `tests/v3/test_infra_seal.py` |
| T3 | `v3/state.py`; `v3/payload.py`; `tests/v3/test_s4_state_payload.py` |
| T4 | `v3/agent.py`; `tests/v3/test_s4_agent.py`; `tests/v3/test_infra_v2_compat.py` |
| T5 | `v3/observe.py`; `tests/v3/test_s4_observe.py` |
| T6 | `v3/runner.py`; `v3/oracle.py`; `tests/v3/test_s4_runner.py`; `tests/v3/test_fig1.py` |
| T7 | `v3/attackers.py`; `tests/v3/test_s4_attacker.py` |
| T8 | `v3/baselines.py`; `tests/v3/test_s5_baselines.py` |
| M1 | `tools/v3_m1_smoke.py`; `../docs/reports/v3-p2-m1.md` |
| T9 | `v3/belief_pf.py`; `v3/belief_exact.py`; `tests/v3/test_alg1_line7.py` |
| T10 | `v3/delta_hat.py`; `v3/sequence.py`; `tests/v3/test_alg1_line1.py` |
| T11 | `v3/library.py`; `tests/v3/test_s5_library.py` |
| T12 | `v3/rollout.py`; `v3/line5.py`; `v3/line8.py`; `tests/v3/test_alg1_line5_8.py` |
| T13 | `v3/exact.py`; `tests/v3/test_alg1_line23.py`; `../docs/reports/v3-p2-line23.md` |
| T14 | `v3/line5_table.py`; `tools/v3_build_table.py`; `tests/v3/test_alg1_line5_table.py`; `reference/v3_line5_table_pilot.npz` (không commit, ghim sha256); `../docs/reports/v3-p2-table.md` |
| T15 | `v3/sentinel.py`; `tests/v3/test_alg1_sentinel.py` |
| T16 | `v3/budget.py`; `tests/v3/test_s9_budget.py` |
| T17 | `v3/metrics.py`; `v3/scorecard.py`; `tests/v3/test_s9_metrics.py` |
| T18 | `tools/v3_tune.py`; `tests/v3/test_s5_tuning.py` |
| T19 | `tools/v3_headline_rollout.py`; `tests/v3/test_s9_rollout_check.py`; `../docs/reports/v3-p2-rollout-check.md` |
| T20 | `v3/stage_world.py`; `tests/v3/test_s4_sensitivity.py` |
| T21 | `v3/smallgame_v3.py`; `tools/v3_small_games.py`; `tests/v3/test_s8_smallgames.py` |
| T22 | `v3/grid.py`; `v3/freeze_v3.py`; `tools/v3_run.py`; `tests/v3/test_infra_grid.py`; `tests/v3/test_infra_freeze.py`; `../docs/reports/v3-p2-cost.md` |
| T23 | `../docs/reports/v3-p2.md`; `../docs/v3/DCM.md` (sinh lại) |

**Không task nào sửa:**
- file v2 (mục 2);
- `v3/config.py` và `v3/api.py` sau W0, trừ khi qua vá giao diện;
- file của task khác.

`tests/run_v3.py` tự tìm test, nên thêm file test không cần sửa nó.

---

## 10. Danh sách task

Công sức tính bằng ngày công, có trợ lý AI, làm TDD. Mỗi test là một dòng DCM có `phase=P2`, trừ test ghi "hạ tầng".

### T0 — Khung v3, DCM theo mảnh, bộ chạy test (W0; 1 ngày)

- **Tái dùng:**
  - mẫu `tests/run_all.py`: dừng ở cổng đỏ đầu tiên, đếm skip riêng;
  - `freeze.header_line` sau `costs.install(P)`;
  - `freeze_d35.clean`.
- **Làm gì:** dựng khung, gồm công cụ ghép mảnh DCM và các mảnh đầu cho §4, Fig. 1, Algorithm 1, §5.2–5.5, §7, §8 và §9.
- **Test hạ tầng:**
  - `test_dcm_id_test_pairs_are_unique`
  - `test_every_p2_dcm_row_names_an_existing_test`
  - `test_every_v3_test_is_a_dcm_row_or_infra`
  - `test_dcm_quotes_are_verbatim_in_pinned_draft`
  - `test_draft_pdf_sha256_is_pinned`
  - `test_v3_leaves_v2_freeze_clean`: freeze v2 và D35 đều clean, và không file v3 nào có trong `freeze.SOURCE`.
- **Nghiệm thu:**
  - `python3 tests/run_v3.py` chạy được;
  - `tests/run_all.py` của v2 cho đúng kết quả như trước khi làm T0.

### T1 — Công tắc, ô, giao diện chung (W0; 1,5 ngày)

- **Tái dùng:** hằng của `draft_setup`; `detector.operating_point`.
- **Làm gì:**
  - `config.py` theo mục 4, cùng mọi giá trị O đã chốt;
  - `api.py` gồm:
    - `PolicyV3`: `act(t, B_t)`, `observe(t, obs)`, `quarantine(t)`;
    - `Observation`;
    - `EpisodeRecord` (đủ trường cho T17);
    - `BeliefAPI`: `update`, `p_poisoned`, `carrier_mass`, `bin_features`;
    - `EpisodeState` (snapshot/resume);
    - `PostMortem`;
    - `L5Source`: trả ma trận L̂ [member × lớp attacker] kèm SE.

  Mục đích là để W1–W3 viết song song trên một hợp đồng chung.
- **Test:**
  - `test_chi_levels_realised_by_depth_configs` [`D8.chi`, C3/C16]
  - `test_detector_levels_are_three_dprimes` [`D8.detector`, C15]
  - `test_delta_grid_is_draft_grid_plus_attacker_column` [`D8.delta`, C10]
  - `test_ten_seeds` [`D9.seeds`, Q9]
  - `test_sensitivities_differ_from_primary_in_one_factor` (hạ tầng)
  - `test_cell_id_is_stable_across_processes` (hạ tầng)
  - `test_api_record_has_every_field_metrics_read` (hạ tầng)
- **Nghiệm thu:**
  - `PRIMARY` khớp Q1;
  - giao diện được review xong rồi mới đóng băng.

### T2 — Dev, eval, niêm phong (W1; 1 ngày)

- **Tái dùng:**
  - `corpus_v2.make_corpus_v2`, `kish`;
  - logic `cut`/`build` của `tools/v3_p0_corpus.py`, viết lại chứ không import;
  - mẫu `refusal`/`provenance`.
- **Test:**
  - `test_eval_split_is_c14_one_pass_26_workflows_18_families` [`D8.scale`, C14, L2]: seed 2027, Kish 10,24, và 14 workflow theo luật "H = cỡ họ" được đánh dấu
  - `test_eval_split_digest_matches_p0` (hạ tầng)
  - `test_eval_families_disjoint_from_dev` [`D8.heldout-family`]
  - `test_no_instance_reused_in_eval`
  - `test_family_size_rule_is_declared`
  - `test_delta8_cell_hosts_18_workflows_12_families`
  - `test_eval_split_refuses_without_unseal` (hạ tầng)
  - `test_every_unseal_attempt_is_logged` (hạ tầng)
  - `test_no_v3_module_reads_eval_outside_seal` (hạ tầng)
- **Nghiệm thu:**
  - `EVAL_SPLIT_SHA256` đã được commit trên nhánh;
  - dev có đúng 100 workflow.

### T3 — Trạng thái carrier và payload sleeper (W1; 1,5 ngày)

- **Tái dùng:**
  - `build.marker_for`, `payload_content`, `PAYLOAD_LENGTH`;
  - `retrieval.payload_topic_like` / `retrieved` / `THETA`;
  - mẫu liệt kê của `build.plan_poison_all`;
  - `Item.derived_from`.
- **Làm gì:**
  - `SleeperPayload`;
  - `plan_sleeper_all(wf, k, Δ, ε)`: σ = ι + Δ là task đầu tiên sau ι thoả vị từ đích; payload được truy xuất trước σ (O2, C8);
  - `CarrierState`: suy c_t từ các item sống.
- **Test:**
  - `test_state_is_carrier_bitvector_with_propagation` [`D4.state`], phần bitvector
  - `test_sleeper_is_retrieved_before_sigma_without_harm` [`D4.sigma`, C8]
  - `test_sleeper_activates_only_on_target_predicate` [`D4.sigma`]
  - `test_no_dormancy_constraint_on_retrieval` [C8]
  - `test_infeasible_placements_record_a_reason` (N3)
- **Nghiệm thu:** in bảng số chỗ gieo khả thi theo Δ trên dev. P0 dự báo 4(H − Δ) chỗ mỗi workflow; bảng đo được phải so với số này.

### T4 — Agent mock v3 (W2; 2 ngày)

- **Tái dùng:**
  - seed và cấu trúc của `world_v2.StagedMockAgent`;
  - `drift_content`, `BETA_WORLD`;
  - tỉ lệ danh định;
  - `select_mixture.KERNELS`.
- **Làm gì:**
  - note → skill (thừa kế poison);
  - queued call mang poison chạy ở task sau, qua đường uỷ nhiệm;
  - patch mang marker chỉ khi vị từ thoả và adoption thành công, rồi đi vào branch;
  - `patch_via` phân loại theo K_d;
  - cờ `ingress`;
  - drift thoáng qua hoặc dai dẳng.
- **Test:**
  - `test_state_is_carrier_bitvector_with_propagation` [`D4.state`], phần lan: (1,0,0,0) → (1,1,0,0) → … → (1,1,0,1)
  - `test_propagation_probabilities_are_the_declared_kernel` [L1]
  - `test_kd_axis_sets_delegated_carriers` [H19, O1]
  - `test_ingress_visibility_is_a_switch` [§10.6, H8]
  - `test_drift_transient_or_persistent_is_a_switch` [`D4.drift`]
  - `test_solved_draw_independent_of_world_switches` (N4)
  - `test_v2_compat_mode_reproduces_staged_mock_agent` (hạ tầng): khi vị từ trùng luật ngủ yên của v2 và tắt đường lan sang queue, kết quả trùng từng lần rút với v2 trên 20 workflow dev.
- **Nghiệm thu:** chế độ tương thích tái hiện v2. Đó là bằng chứng rằng mọi khác biệt về sau đến từ các điểm C.

### T5 — Mô hình quan sát (W1; 1 ngày)

- **Tái dùng:** bọc logic `world_v2.DriftDetector`; `detector.Detector`; `scoring.carrier_score`.
- **Làm gì:**
  - audit carrier dùng d′√depth, với depth theo ô;
  - commit: patch trực tiếp dùng d′√depth; patch uỷ nhiệm dùng ρ·d′;
  - A7 (O9);
  - checkpoint (O8);
  - ingress bị ẩn khỏi audit memory khi tắt công tắc;
  - **các hàm likelihood thuần** cho PF (T9) và rollout (T12).
- **Test:**
  - `test_checkpoint_channel_declared` [`D4.obs`]
  - `test_commit_sees_delegated_patch_with_rho_dprime_at_every_depth` [`D4.obs`, D20]
  - `test_a7_adds_provenance_signal_only_in_a7` [C1]
  - `test_insertion_audit_blind_to_ingress_when_switch_off` [H8]
  - `test_every_inspection_draws_an_independent_score` [`D4.obs`]
  - `test_detector_reads_no_ground_truth` [`D8.detector`]
- **Nghiệm thu:** công thức P_miss^B1 = Φ(z_{1−φ} − ρd′) khớp mô phỏng trong sai số Monte Carlo.

### T6 — Runner, oracle, loss, Figure 1 (W3; 2,5 ngày)

- **Tái dùng:**
  - thứ tự trong task và các trường record của `carrier_runner`;
  - `rs_of`, `survives`;
  - `oracle.harm_of`, `hidden_ok_of`;
  - `metrics.loss`.
- **Làm gì, thứ tự trong một task:**
  1. `act`;
  2. mua hành động nếu Σκ + κ(a_t) ≤ B (không áp nhịp chi D4);
  3. chèn payload ở ι;
  4. agent chạy;
  5. audit, rồi quan sát;
  6. dòng 7;
  7. dòng 8–9: gỡ **mọi** item sống của carrier;
  8. chốt harm tại σ nếu `locked`;
  9. oracle đọc branch cuối horizon.

  Record gồm: harm, FQ, số item lành bị gỡ, t_lost, clean lost do gỡ branch, detected_at, `missed_before_sigma`, quỹ đạo c_t, audits, spent, Δ̂, nguồn dòng 5, hash log quyết định.

  Runner có `snapshot()` và `resume(state, t)` để rollout dùng lại.
- **Test:**
  - `test_one_action_per_task_within_budget` [`D4.defender`]
  - `test_quarantine_removes_whole_carrier` [`D4.quarantine`]
  - `test_harm_read_at_horizon_end` [`D4.payoff`]
  - `test_locked_harm_is_not_undone_by_later_quarantine` [C11]
  - `test_reversible_harm_is_undone_by_branch_quarantine` [C11]
  - `test_loss_matches_definition_1` [`D4.def1`]
  - `test_false_quarantine_counts_clean_carrier_removals` [O7]
  - `test_episode_is_deterministic_in_workflow_and_seed` (D19)
  - `test_resume_from_snapshot_equals_full_run` (hạ tầng)
  - `test_figure1_replays_t1_to_t7` [`DF1.t1`–`DF1.t7`]: kịch bản H = 7, điểm detector bị ép:
    - t1: note độc vào memory; insertion audit (tỉ lệ 0,3) không được rút;
    - t2: skill được sinh, c = (1,1,0,0);
    - t3–t4: audit memory không nổ;
    - t5: skill chạy trên task thoả vị từ và sinh patch uỷ nhiệm;
    - t6: commit ở A0, ρ = 0, chấp nhận;
    - t7: oracle đọc harm = 1.

    Việc ánh xạ t5/t6 vào cùng task σ là L1 và có dòng DCM riêng.
- **Nghiệm thu:**
  - mọi test §4 thuộc T3–T6 xanh;
  - một episode B1 chạy ≤ 1,1 ms;
  - một lần clone/resume ≤ 0,5 ms (P0 đo 229 µs).

### T7 — Attacker v3 (W2; 1,5 ngày)

- **Tái dùng:**
  - `attackers_v2._RULES`, `held_out()` (giữ nguyên tên và hash);
  - mẫu `behavior_keys`, `tuning_attack_names`, `br_attacks`;
  - `metrics_v2.crossfit_value`.
- **Làm gì:**
  - 18 luật dựng trên `plan_sleeper_all`;
  - khoá hành vi có thêm kênh khi ingress bị ẩn;
  - BR liệt kê (k, ι, ε);
  - gieo 2 carrier;
  - cột "attacker chọn Δ" (O5);
  - hàm `attacker_classes()` trả 6 lớp hành vi D18 để dòng 5 dùng.
- **Test:**
  - `test_attacker_menu_matches_cell` [`D4.attacker`, C10]
  - `test_eighteen_scripted_seven_held_out` [`D8.attackers`]
  - `test_held_out_names_equal_v2_split` (hạ tầng)
  - `test_tuning_columns_never_realise_held_out_behaviour` [§5.5, D18]
  - `test_attacker_sees_policy_not_its_draw` [`D4.attacker`, `D5.3.rand`]
  - `test_two_carrier_seeding_respects_attacker_budget` [`D4.attacker`]
  - `test_attacker_chooses_delta_menu_is_declared` [C10, O5]
- **Nghiệm thu:** BR cross-fit chạy được trên dev.

### T8 — Baseline và đối chứng (W1; 1 ngày)

- **Tái dùng:** logic `act` của `carrier_policies`; `OracleControl`; mẫu `addendum_d35.B2CommitProb`. Mọi thứ viết trên `api.PolicyV3`.
- **Làm gì:**
  - B1–B6, cost-greedy (§10.1), SW ngẫu nhiên hoá (§11), B1-prov, Oracle (+);
  - policy chỉ chọn đích; độ sâu do ô quyết định;
  - baseline gỡ carrier đã audit nếu audit nổ;
  - B1 khi ngân sách chặn (O6).
- **Test:**
  - `test_b1_audits_the_commit_of_every_task` [`D5.2.b1`]
  - `test_b1_lowers_commit_depth_evenly_when_budget_binds` [Q8, O6]
  - `test_baselines_quarantine_whole_carrier_on_alarm` [O7]
  - `test_cost_greedy_audits_cheap_carriers_more` [§10.1]
  - `test_oracle_control_is_told_the_attacked_carrier_only` (D28)
  - `test_depth_is_fixed_by_cell_for_every_policy` [C16]

### M1 — Tích hợp mốc đầu (sau W3; 0,5 ngày)

- **Làm gì:** `tools/v3_m1_smoke.py` chạy lát ở mục 7 trên dev, tóm tắt bằng `v3/metrics.py` rồi ghi `docs/reports/v3-p2-m1.md`.
- **Nghiệm thu:** như mục 7. Không đạt thì dừng các đợt sau cho tới khi sửa xong thế giới.

### T9 — Particle filter 2048 hạt (W3; 2,5 ngày)

- **Tái dùng:** `belief.WindowBelief` và công thức drift của `belief_v2` làm chuẩn chính xác; các hàm likelihood của T5.
- **Làm gì:**
  - hạt trên (có tấn công hay không, c ∈ {0,1}⁴, ι, σ); drift cạnh tranh theo β_k; kernel lan khai báo;
  - resampling hệ thống, có resample-move khi ESS thấp;
  - tiên nghiệm trên σ − ι lấy từ Δ̂;
  - β online (O11);
  - `bin_features()` cho bảng (O16);
  - viết bằng numpy; P0 đo +10,1 µs mỗi task.
- **Test:**
  - `test_line7_particle_filter_has_2048_particles_over_c_iota_sigma` [`D7.pf2048`, `D5.1.belief`]
  - `test_pf_matches_exact_posterior_on_small_cases`: TV trung bình ≤ ngưỡng khai trước
  - `test_drift_is_a_competing_cause` [`D4.drift`, `D5.4`]
  - `test_belief_moves_after_commit_alarm_when_rho_positive` [`DA1.l7`]
  - `test_commit_alarm_is_uninformative_on_delegated_path_at_rho_zero_in_a0`
  - `test_alarm_at_t_raises_earlier_insertions_with_later_triggers` [câu §5.1]
  - `test_beta_estimated_online_from_clean_workflows` [`D7.beta`, O11]

### T10 — Dòng 1: Δ̂ từ post-mortem cùng ô (W4; 1,5 ngày)

- **Tái dùng:** ý tưởng arm Δ sai của `addendum_d35.DHAT` (chỉ dùng trong test).
- **Làm gì:**
  - lịch sử khoá theo (`cell_id`, hệ thống, cột attacker, seed);
  - thứ tự workflow `seed_of("v3-order", wf_id)` được ghi vào manifest;
  - post-mortem theo O4;
  - Δ̂ theo O3; χ̂ lấy từ bảng giá của ô;
  - `sequence.py` chạy chuỗi workflow và ghi `n_incidents_seen` để vẽ đường học;
  - arm oracle-Δ và arm chỉ dùng tiên nghiệm.
- **Test:**
  - `test_line1_delta_hat_is_low_quantile_of_same_cell_postmortems` [`DA1.l1`, C12]
  - `test_line1_uses_prior_before_first_postmortem`
  - `test_line1_never_reads_current_workflow_sigma`
  - `test_workflow_order_is_pinned_in_manifest`
  - `test_history_does_not_cross_cells_or_seeds`
  - `test_learning_curve_is_recorded`
  - `test_postmortem_is_the_only_cross_workflow_channel`
  - `test_no_headline_number_comes_from_the_oracle_arm`

### T11 — Thư viện 28 policy (W4; 1,5 ngày)

- **Tái dùng:** `_SW`, `_TAUS`, `_FLOORS`; logic của các họ SW, BT, RO qua adapter.
- **Làm gì:**
  - SW 8, BT 12, RO 8; trục độ sâu của RO thay theo O10;
  - member chỉ chọn hành động; dòng 8–9 nằm trong Sentinel;
  - τ nằm trong dải (p_floor, p₀).
- **Test:**
  - `test_library_has_28_members_in_three_families` [`D5.2.lib`]
  - `test_library_members_are_distinct_under_fixed_depth` [C16]
  - `test_prop61_each_family_has_a_member_that_changes_a_decision` (cổng trước tinh chỉnh)
  - `test_tau_inside_p_floor_p0_band`

### T12 — Động cơ rollout, LP của dòng 5, dòng 8–9 (W5; 2,5 ngày)

- **Tái dùng:** `runner.snapshot/resume` (T6); `lp.simplex_max` hoặc `linprog`; LP "min z" của `select_mixture`; `smallgame.solve` để kiểm.
- **Làm gì:**
  - `rollout.py`: từ một hạt, gán trạng thái ẩn (poison theo c, ι) lên bản sao của store quan sát được, rồi chạy tiếp bằng runner với member π và lớp attacker π_A dưới kernel danh định, dùng số ngẫu nhiên chung;
  - `line5.py`: một LP dùng chung cho hai nguồn L̂:
    - `TableSource` (chính, Q13);
    - `RolloutSource` (chỉ ở ô headline);
  - loại member vượt B_t (O14);
  - ghi x_t: công bố phân phối, không công bố lần rút;
  - `line8.py`: nếu Pr[poisoned] > τ và harm kỳ vọng > η_Q thì gỡ carrier có hậu nghiệm cao nhất.
- **Test:**
  - `test_line5_is_argmin_max_over_library_each_task` [`DA1.l5`]
  - `test_line5_table_and_rollout_sources_share_one_lp` [Q13]
  - `test_line5_attacker_class_excludes_held_out_behaviour` [§5.5]
  - `test_line5_reveals_distribution_not_draw` [`D5.3.rand`]
  - `test_line5_skips_unaffordable_members` [O14]
  - `test_line5_matches_exact_minimax_on_coverage_reduction`
  - `test_line8_quarantines_highest_posterior_carrier_when_tau_and_eta_q_exceeded` [`DA1.l8`]
  - `test_line8_does_nothing_below_tau`
- **Nghiệm thu:** đo thời gian mỗi bộ (member, lớp, lần rút) để so với 7,4 ms của P0.

### T13 — Dòng 2–3: giải chính xác khi KH ≤ 40 (W4; 1,5 ngày)

- **Tái dùng:** `smallgame.solve`, `lp.simplex_max`, `theory/checks/coverage.minimax`.
- **Làm gì:**
  - minimax dạng chuỗi trên cây lịch sử, quan sát rời rạc hoá, cho H nhỏ;
  - đếm trạng thái và đo thời gian với H = 2..6, K = 4; ngoại suy tới H ≤ 10;
  - ngưỡng khả thi khai trước: ≤ 10⁶ chuỗi và ≤ 60 s mỗi workflow. Đạt thì dùng; không đạt thì ghi log `line23: infeasible, states=…, runtime=…` và chuyển sang dòng 5 (L2).
- **Test:**
  - `test_line2_exact_when_KH_le_40_or_logs_infeasibility` [`DA1.l2`]
  - `test_exact_matches_smallgame_on_coverage_reduction`
  - `test_library_never_beats_exact_value`
- **Nghiệm thu:** có báo cáo `v3-p2-line23.md`. 20/26 workflow eval có H ≤ 10.

### T14 — Dựng bảng dòng 5 (W6; 2 ngày công, cộng giờ máy)

- **Tái dùng:** `rollout.py` (T12); ngăn belief (T9); lớp attacker (T7); dev (T2). Cách đo của `v3-p0-chi-phi.md` §2.
- **Làm gì:**
  - **Schema.** Khoá gồm (`cell_id` của thế giới chính, Δ̂ ∈ lưới, h = số task còn lại ∈ 1..14, ngăn belief). Giá trị là L̂ [28 × 6] kèm SE và số trạng thái nguồn.
  - **Lưu trữ.** File `.npz` float32, khoảng 70–140 MB. Không commit; ghim sha256 trong manifest. Lệnh dựng là tất định.
  - **Trạng thái nguồn.** Chạy các episode dev bằng một policy hành vi khai trước (hỗn hợp đều 28 member), lưu (b_t, store) ở mỗi t, xếp vào ngăn, rồi lấy tối đa S trạng thái mỗi ngăn.
  - **Giá trị.** R = 32 rollout cho mỗi (member, lớp) (O12). Ngăn rỗng xử lý theo O16.
  - **Pilot trong P2.** Dựng pilot ở 4 ô headline (4 ρ, χ = 1,33, mid): khoảng 9–34 CPU-giờ, tức 2–6 giờ thật. Đo giá thật, rồi ngoại suy cho 36 ô và so với ước lượng 77–309 CPU-giờ.
  - **Bản cuối** dựng ở P4, sau tinh chỉnh τ và η_Q, rồi mới freeze.
- **Test:**
  - `test_line5_table_is_built_on_dev_only` [§5.5, hạ tầng niêm phong]
  - `test_table_key_is_cell_deltahat_remaining_bin` [Q13, O16]
  - `test_table_build_is_deterministic` (hạ tầng)
  - `test_empty_bins_fall_back_with_a_reason` (N3)
  - `test_table_cell_se_below_declared_threshold` [O12]
- **Nghiệm thu:** có báo cáo `v3-p2-table.md` gồm:
  - giá đo được;
  - tỉ lệ ngăn rỗng;
  - SE;
  - sai lệch giữa bảng và rollout trên một mẫu trạng thái dev.

### T15 — Lắp Sentinel v3 và ablation (W7; 1,5 ngày)

- **Tái dùng:** `VARIANTS`, `REGISTRY`, `make_policy` của `sentinel.py`.
- **Làm gì:**
  - Sentinel = dòng 1, 2–3, 5 (bảng), 7, 8–9;
  - ablation:
    - −randomization: chính sách tất định tốt nhất trước BR (§5.3);
    - −alarm memory;
    - −transition uncertainty;
    - −benign-drift;
  - arm tham khảo: oracle-Δ, −regime estimate, "Sentinel-rollout" (chỉ cho ô headline);
  - `V3_REGISTRY`.
- **Test:**
  - `test_sentinel_runs_algorithm1_lines_in_order`
  - `test_minus_randomization_is_best_deterministic_policy` [`D5.3.rand`, H12]
  - `test_ablation_changes_at_least_one_decision_in_headline_cell` (cổng chung; không đạt thì in "không được vận dụng")
  - `test_sentinel_line5_source_is_table_outside_headline` [Q13]
  - `test_registry_names_are_unique` (hạ tầng)
- **Nghiệm thu:** Sentinel dùng bảng pilot chạy hết một ô headline dev, 1 seed, ở khoảng 1 ms mỗi episode.

### T16 — Lưới ngân sách H18 và trục K_d (T16a ở W1: 1 ngày; T16b ở W8: 0,5 ngày)

- **Tái dùng:** công thức Định lý 5.6 và `block_schedule` của `theory/checks/thm4_budget.py` (port, không import từ `theory/`); `BudgetSpec`, `target_kappa_for_chi` (chuyển sang thang range).
- **T16a:**
  - B_min(Δ) = K·κ̄·n_α·⌊(H − 1)/Δ⌋; Δ = 0 bị loại (khai);
  - cờ cho ô vi phạm điều kiện Δ ≥ K·n_α;
  - các mức b1 và {2; 1; 0,5} × B_min;
  - κ của arm chỉ đổi giá: giữ độ sâu và κ̄;
  - lịch khối (Mệnh đề 5.7) viết như một `PolicyV3`.
- **T16b:** smoke H18 và K_d trên dev bằng lưới của T22.
- **Test:**
  - `test_bmin_matches_theory_note_theorem_5_6` [`D6.thm4`, C13, H18]
  - `test_budget_levels_are_b1_and_multiples_of_bmin` [Q8]
  - `test_price_only_arm_keeps_depth_and_kbar` [C16]
  - `test_block_schedule_matches_proposition_5_7`
  - `test_missed_before_sigma_is_logged` [H18]
  - `test_kd_grid_runs_at_primary_for_every_rho` [H19]

### T17 — Metrics, kiểm định, bảng điểm (W1, chạy qua M1; 2 ngày)

- **Tái dùng:**
  - `metrics_v2.harm_table`, `value`, `crossfit_value`, `side`, `controls`, `gain_vs_best`;
  - `gain_ci` làm kiểm chéo;
  - plasmode của `tools/v3_p0_precision.py`.
- **Làm gì:**
  - bảy chỉ số §9.3, trọng số theo workflow;
  - wild cluster bootstrap theo họ (trọng số Webb, 18 cụm), lấy lại max theo cột ở mỗi lần rút;
  - BH với q = 0,05;
  - đường học;
  - đối chứng đọc trước;
  - luật P, D, E, N, G (δ_rel = 10, δ_abs = 0,10);
  - khung H1–H20;
  - dòng "độ trung thành bảng–rollout": in |V_bảng − V_rollout| kèm CI. Đây không phải giả thuyết. Nếu hiệu > 0,10 thì số headline mang nhãn "bảng lệch rollout".
- **Test:**
  - `test_seven_metrics_of_section_9_3` [`D9.metrics`]
  - `test_wild_cluster_bootstrap_resamples_families_and_remaxes_columns` [`D9.ci`, L2]
  - `test_wild_bootstrap_coverage_on_v2_plasmode`
  - `test_bh_at_q_005` [`D9.bh`]
  - `test_rule_P_match_reject_inconclusive_are_disjoint` (ca 27,6 / CI [29; 31])
  - `test_rule_D_signs`
  - `test_rule_E_equivalence`
  - `test_rule_N_non_inferiority`
  - `test_rule_G_lower_bound_15` [§9.4]
  - `test_controls_are_read_before_any_sentinel_number` (D28)
  - `test_table_rollout_fidelity_row_is_printed` [Q13]

### T18 — Công cụ tinh chỉnh trên dev (W6; 1 ngày; chỉ smoke)

- **Tái dùng:** `select_mixture` (`KERNELS`, LP có ràng buộc FQ, D32).
- **Làm gì:**
  - τ, η_Q và τ5 cho từng ρ, theo worst-case L trên dev (C6), lấy max qua 3 kernel ζ;
  - chỉ chạy member, không chạy Sentinel có rollout (GĐ 13);
  - ghi `reference/v3_tuned.json`.
- **Test:**
  - `test_tuning_reads_dev_only` (hạ tầng)
  - `test_tuning_objective_is_worst_case_L_over_three_kernels` [C6, `D5.robust`]
  - `test_eta_q_not_on_grid_edge_or_declared`
- **Nghiệm thu:** smoke với 1 seed và 5 workflow dev.

### T19 — Kiểm rollout ở ô headline (W8; 1 ngày, cộng khoảng 8 CPU-giờ dev)

- **Tái dùng:** `RolloutSource` (T12); `metrics.crossfit_value`; mẫu D33 cho record.
- **Làm gì:**
  - `tools/v3_headline_rollout.py` chạy Sentinel-rollout ở ô headline:
    - Δ ∈ {4, 8}, χ = 1,33, mid, 4 mức ρ;
    - 7 held-out và BR;
    - R ∈ {16, 32, 64} khai trước;
  - ghi record cạnh bản dùng bảng;
  - ablation bằng rollout là tuỳ chọn và phải khai;
  - trong P2 chỉ chạy trên dev (mẫu 20 workflow, R = 16). Lượt eval thuộc P5 (176–706 CPU-giờ).
- **Test:**
  - `test_headline_rollout_runs_only_in_table2_cell` [Q13, C5]
  - `test_rollout_and_table_records_share_episodes` (hạ tầng: cùng workflow, seed, cột)
  - `test_rollout_tool_refuses_eval_without_unseal` (hạ tầng)
- **Nghiệm thu:** `v3-p2-rollout-check.md` trên dev có sai lệch giữa bảng và rollout, kèm CI và thời gian thật mỗi episode.

### T20 — Thế giới độ nhạy, đổi một yếu tố mỗi lần (W8; 2 ngày)

- **Tái dùng:** `gate_world._Gates`, `GATE_BASELINES`, `STAGE_KAPPA`.
- **Làm gì:**
  - thế giới kiểm theo giai đoạn (C2): hành động là (giai đoạn, độ sâu); Sentinel và baseline chạy được trong đó;
  - smoke 6 độ nhạy trên dev;
  - bảng dùng ở độ nhạy theo O15.
- **Test:**
  - `test_stage_world_action_is_stage_and_depth` [C2]
  - `test_sentinel_runs_in_both_worlds` [C2]
  - `test_each_sensitivity_run_flips_exactly_one_factor` [Q2]
  - `test_h8_verdict_is_taken_from_ingress_visible_world` [H8]
  - `test_sensitivity_uses_primary_table_as_declared` [O15]

### T21 — Game nhỏ v3: B7 và H7 (W5; 1,5 ngày)

- **Tái dùng:** `smallgame.games`, `solve`, `tv`, `feasible`; `tools/solve_small_games.py`.
- **Test:**
  - `test_240_small_games_solved_exactly` [`D8.small`]
  - `test_ported_members_are_feasible`
  - `test_covering_radius_is_measured_against_pi_star` [H7, Prop. 6 đã sửa]
- **Nghiệm thu:** in regret so với B7 và bán kính phủ trên 240 game.

### T22 — Lưới, phần cắt BR, freeze v3, công cụ chạy (W8; 2 ngày)

- **Tái dùng:**
  - `freeze._digest`, `header_line`, `pin_conflicts`, `require_frozen`;
  - mẫu `freeze_d35`;
  - `Refused`, `refusal`, `provenance`, `pin_records`, đọc shard của `run_draft_eval`.
- **Làm gì:**
  - `grid.py` sinh các lưới main / sensitivity / h18 / kd / headline-rollout, với phần cắt BR theo mục 8;
  - đếm episode của từng khối vào `docs/reports/v3-p2-cost.md`, so với P0;
  - manifest v3 gồm:
    - digest nền v2;
    - sha256 của `v3/*.py`, `v3/dcm/`, `reference/v3_tuned.json`, bảng dòng 5, `tools/v3_run.py`, `tools/v3_tune.py`, `tools/v3_build_table.py`, `tools/v3_headline_rollout.py`;
    - các registry, held-out, cột tinh chỉnh;
    - `EVAL_SPLIT_SHA256`, thứ tự workflow;
    - định nghĩa lưới;
    - digest luật bảng điểm;
  - `v3_run --split {dev,eval}` là bắt buộc; chạy theo chuỗi (ô, hệ thống, attacker, seed); tóm tắt đọc đối chứng trước.
- **Test:**
  - `test_br_trims_match_declared_plan` [Q14]
  - `test_harness_refuses_policy_not_in_v3_manifest` [`D7.freeze`]
  - `test_eval_refused_on_dirty_or_missing_freeze` [`D5.5.freeze`, D33]
  - `test_records_are_pinned_by_sha256`
  - `test_dev_smoke_records_carry_every_switch`
  - `test_base_v2_and_d35_freezes_stay_clean`
- **Nghiệm thu:**
  - smoke toàn lưới trên dev ở 1 seed chạy xong;
  - tổng episode ≤ số của P0 sau khi cắt.

### T23 — Khép P2 (W9; 0,5–1 ngày)

- **Làm gì:**
  - `tests/run_v3.py` xanh;
  - `v3_dcm.py --check` xanh cho mọi dòng `phase=P2`;
  - báo cáo `v3-p2.md` ghi:
    - danh sách L1/L2;
    - các giá trị O đã chốt;
    - giá tính toán đo được so với P0;
    - sai lệch so với draft;
    - nhật ký mở niêm phong rỗng.
- **Nghiệm thu:** phần P2 của cổng G2 đạt.

---

## 11. Rủi ro kỹ thuật còn mở

| # | Rủi ro | Dấu hiệu / tính toán | Phương án |
|---|---|---|---|
| R1 | Giải chính xác belief MDP với H ≤ 10 không khả thi | Cây lịch sử cỡ (\|A\|·\|O\|)^H ≈ 10^10–10^13 ở H = 10. Belief trên (c, ι, σ) có khoảng 2⁴·H² điểm. 20/26 workflow eval có H ≤ 10, nên phần lớn tập rơi vào dòng 2–3 theo chữ | T13 đo, ngoại suy và ghi bằng chứng L2 cho từng workflow; dòng 5 chạy thay |
| R2 | Sai số xấp xỉ của bảng dòng 5 | Ngăn belief thô (40 ngăn) làm mất thông tin; trạng thái nguồn lấy từ dev (họ Python của v2) trong khi eval có 14 họ không phải Python | Đo sai lệch bảng–rollout trên dev (T14, T19) và ở ô headline eval (P5); in cạnh nhau; gắn nhãn khi hiệu > 0,10 |
| R3 | Giá dựng bảng vượt ước lượng | 77–309 CPU-giờ phụ thuộc số trạng thái mỗi ngăn và R. Bảng cuối phải dựng lại sau khi tinh chỉnh τ, η_Q | Pilot ở T14 đo giá thật trước. Tinh chỉnh chạy member, không cần bảng (GĐ 13). Chỉ dựng bảng cuối một lần, sau tinh chỉnh |
| R4 | Δ̂ gần như oracle ở ô Δ cố định | Mọi post-mortem trong một ô cho cùng một Δ, nên Δ̂ đúng từ workflow thứ hai trở đi | In đúng như vậy. H4 và H20 đọc ở nơi có thông tin. Workflow đầu, khi chỉ có tiên nghiệm, báo riêng |
| R5 | Workflow trong một ô không còn độc lập | Post-mortem nối các workflow; bootstrap theo họ giả định các cụm độc lập | Khai; thứ tự ghim trước. Báo thêm mức giảm trên các workflow đã có ít nhất 1 post-mortem |
| R6 | Wild cluster bootstrap cho thống kê max-của-trung-bình | Cameron–Gelbach–Miller viết cho hệ số hồi quy. Có 18 cụm, 14 họ chỉ có 1 workflow, Kish 10,24 | Khai định nghĩa trước; kiểm độ phủ trên plasmode. Độ phủ kém thì in cả bootstrap cặp theo họ, không chọn cái đẹp hơn |
| R7 | Độ sâu cố định theo ô χ | Commit ở độ sâu 1 trong cả ba cấu hình, nên B1 không "at maximum depth" và không có chỗ giảm độ sâu. RO-d2 trùng RO-d3 | O6, O10; ghi vào DCM là L1/L2 |
| R8 | Phạm vi truy xuất của sleeper (O2) | Truy xuất rộng làm lan truyền trước σ gần như chắc chắn và đổi số chỗ gieo khả thi. Ô Δ = 8 chỉ có 18 workflow / 12 họ | Chốt O2 trước T3; in bảng khả thi theo Δ; xu hướng theo Δ đọc trên tập con 18/12 |
| R9 | B_min(Δ) có lỗ | Không xác định ở Δ = 0; điều kiện cửa sổ Δ ≥ K·n_α hỏng ở Δ nhỏ | Bỏ Δ = 0 khỏi H18; gắn cờ các ô vi phạm; không nội suy |
| R10 | Gỡ cả carrier làm lệch chi phí giữa các carrier | Gỡ branch mất mọi patch sạch; gỡ memory gần như miễn phí trong agent mock | O7 khai trước; in FQ theo từng carrier; ghi là giới hạn của agent mock |
| R11 | PF suy biến | Báo động sắc (d′√3 ≈ 5,1 với detector mạnh) | Resample-move; test so với bộ liệt kê chính xác (T9) |
| R12 | Lớp attacker ở cột "attacker chọn Δ" (O5) | H20 phụ thuộc lớp này | Chốt trước T7; không đổi sau khi thấy số |
| R13 | v2 bị sửa ngoài ý muốn | v3 import nhiều module v2 | `test_v3_leaves_v2_freeze_clean` chạy trong mọi lượt `run_v3.py` |
| R14 | Xung đột merge giữa các worktree | Nhiều task cùng ghi DCM, test, registry | Mảnh DCM theo task, file test theo task, `config`/`api` đóng băng, registry chỉ lắp ở T15 và T22 |
| R15 | Giao diện `api.py` sai, phát hiện muộn | W1–W3 cùng code trên hợp đồng này | Review `api.py` trước khi đóng W0; vá giao diện là task riêng, merge trước các task phụ thuộc |
| R16 | Bảng của thế giới chính dùng ở thế giới độ nhạy (O15) | Sentinel mang mô hình sai lệch một yếu tố, nên hiệu ứng lẫn hai nguồn | Khai. Bảng riêng cho mỗi thế giới là tuỳ chọn: 4 ô mỗi thế giới, khoảng +11% giá bảng cho mỗi thế giới |
| R17 | Đĩa và ghim bảng | Bảng 70–140 MB; record eval khoảng 8,6 GB | Không commit; ghim sha256; lệnh dựng tất định để gói tái lập tự dựng lại |

---

## 12. Chỗ `sentinel-v3.md` cần đồng bộ với quyết định mới (ngoài mã P2)

- **C14 và §8.** Doc vẫn ghi 36 workflow / 18 họ, hai lượt (Kish 6,48). Q10 chốt một lượt: 26 / 18 (Kish 10,24); ô Δ = 8 còn 18 / 12.
- **Bảng điểm.** δ cũ là ±5 điểm / ±0,03. Q12 chốt 10 điểm / 0,10.
- **Algorithm 1.**
  - Doc ghi "tám dòng" và "dòng 8"; draft có 10 dòng, và quarantine ở dòng 8–9.
  - Doc gọi bảng dòng 5 là "dự phòng, chỉ dùng khi rollout không tính nổi". Q13 biến nó thành phương án chính, có bằng chứng ở `v3-p0-chi-phi.md`.
- **Người ký.** Cổng 0 và Cổng 4 ghi "thầy ký". Theo quyết định 27/09, người dùng quyết, và `frozen/V3-GATE4.json` do người dùng ghi.
- **Lõi tối thiểu.** Doc chưa nói K_d của cấu hình chính; O1 đề xuất 2. P0 chi phí (GĐ 10) cũng giả định 2.
