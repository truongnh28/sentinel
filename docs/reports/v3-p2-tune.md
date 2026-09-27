# Sentinel v3 P2 — nối bộ lọc hạt thật vào công cụ tinh chỉnh (T18, P4)

27/09/2026. Việc: nối bộ lọc hạt thật (`v3/belief_pf.py`, T9) và line 8 thật (`v3/line8.py`, T12) vào `auditgame/tools/v3_tune.py`, vốn trước đó chỉ chạy `--smoke` với `StubAlarmBelief`. Chỉ chạy trên dev (`require_dev`, `seal.SealedSplit`), không có đường nào tới eval. Số đo sinh bằng `cd auditgame && ../.venv/bin/python tools/v3_tune.py --real`.

## Đã nối gì

- **Belief factory thật.** Chế độ `--real` (đồng nghĩa `--belief pf`) đặt `belief_factory = pf_belief_factory` (bao `v3.belief_pf.make_belief`, N = 2048 hạt, prior Δ `'at-least'` quanh Δ-hat của line 1). Nhãn ghi vào `setup.belief` là `ParticleBelief (v3.belief_pf, N = 2048 particles, Delta prior 'at-least' from line 1's Delta-hat)`. `--smoke` giữ nguyên: vẫn dùng stub, vẫn cấm ghi vào `reference/`.
- **Line 8 thật, một nguồn sự thật.** Adapter `line8_real(belief, tau, eta_q)` trả `v3.line8.Line8(tau, eta_q).decide(belief)`. `decide` chỉ **đọc** (không điều kiện hoá belief); `MemberWithLine8.quarantine` mới điều kiện hoá sau khi có carrier — đúng như với `line8_rule`. Đã kiểm `line8_real` trùng `line8_rule` trên **21.875** trường hợp (mọi tổ hợp khối lượng carrier × τ × η_Q trên belief stub): 0 lệch. Cả hai dùng cùng phép so sánh chặt `p_poisoned > τ ∧ expected_harm > η_Q` và cùng luật hoà argmax theo thứ tự `config.CARRIERS`.
- **Dải Prop. 6.1 cho member BT.** `band_of(belief) = library.band_prop61(prior_p_attack(), uninformable_share())`, đúng như Sentinel dựng ở eval (`v3.sentinel.band_of`, hợp đồng T11). Trên mọi ô headline (mọi ρ, Δ) dải này là hằng **(0, 0,5)**: sweep của chính carrier bị gieo luôn cung cấp thông tin nên không hypothesis tấn công nào "không thể suy" (f = 0). Vì hằng, một dải dựng một lần từ belief đại diện là trùng khớp với dải per-context của eval, không có khe hở fidelity. `main()` dựng dải này một lần từ workflow dev đầu tiên, thế giới `PRIMARY`, ô (ρ₀, Δ = 4).
- **Member đọc belief (BT) vào cuộc.** `default_members(belief_factory, band)` khi có `belief_factory` thật **và** dải sẽ trả đủ **28** member (8 SW + 12 BT + 8 RO); không có dải chỉ trả 16 (SW + RO). Đã xác nhận.

Không đụng `freeze.SOURCE`/`freeze.TABLES`; `freeze.header_line()` vẫn `freeze: clean sha256:c789fa7362e0`. Không đụng eval/seal, không ghi `frozen/V3-GATE4.json`. File ra mở chế độ `"x"`.

## Chi phí thật (giờ CPU)

Đo trên máy này (Python 3.14, numpy 2.5.3, scipy 1.18.1), một tiến trình:

| Bước | ms/episode (đo) | episode (lượt đầy đủ) | giờ CPU (lượt đầy đủ) |
|---|---|---|---|
| `tau5` (baseline B5, không belief) | 2,64 | 172.800 | 0,13 |
| `sw_weights` (baseline SW, không belief) | 2,24 | 172.800 | 0,11 |
| `line8` (28 member × bộ lọc hạt) | **11,63** | 32.256.000 | **104,16** |
| **Tổng lượt đầy đủ 3 kernel** | | | **≈ 104,4 giờ CPU** |
| Biến thể `--nominal-only` (1 kernel) | | ≈ 10,75 triệu (line8) | **≈ 34,8 giờ CPU** |

Bước `line8` áp đảo vì mỗi trong 5 τ × 8 η_Q × 28 member chạy một lượt `measure` đầy đủ (3 kernel × 2 Δ × 6 tuning-attacker × 100 workflow dev × 2 seed), mỗi episode kéo theo một bộ lọc 2048 hạt. Ngoại suy bằng `v3_tune.extrapolate` từ lượt kiểm chứng (ms/episode đo thật của bước line8).

Kết luận chi phí: lượt đầy đủ ~104 giờ CPU + biến thể nominal ~35 giờ CPU ≈ **~140 giờ CPU** một tiến trình. Quá đắt để xong trong một phiên; theo đúng phương án dự phòng của việc, đã kiểm chứng wiring đầu-cuối, commit, rồi khởi động lượt đầy đủ ở nền và báo ETA.

## Kiểm chứng wiring (mẫu con — KHÔNG phải giá trị tinh chỉnh thật)

Lượt kiểm chứng đầu-cuối: 2 workflow dev, 1 seed, ρ ∈ {0; 0,25}, lưới rút gọn (τ = 0,5; η_Q ∈ {0; 0,1; 0,5}; tau5 ∈ {0; 0,3}; sw ∈ {commit3, sweeps}), 28 member thật, bộ lọc hạt thật, `line8_real`. Chạy 143,4 s, `check_tuned` chấp nhận, log ghi ra khớp `log_sha256`.

| ρ | tau5 | sw_weights | τ | η_Q | worst-case L (minimax) | khai mép η_Q |
|---|---|---|---|---|---|---|
| 0 | 0,0 | commit3 | 0,5 | 0,0 | 0,4630 | có (mép DƯỚI lưới rút gọn) |
| 0,25 | 0,0 | commit3 | 0,5 | 0,0 | 0,4630 | có (mép DƯỚI lưới rút gọn) |

Đây chỉ là số **chứng minh đường ống chạy đúng** trên mẫu con với lưới rút gọn; **không** dùng làm giá trị tinh chỉnh. η_Q = 0 rơi vào mép dưới của lưới rút gọn nên mang `eta_q_edge` (đúng luật: giữ nguyên, kèm khai, không tinh chỉnh lại trên lưới rộng hơn). `check_tuned` từ chối một giá trị mép không khai. Giá trị (tau5, sw_weights, τ, η_Q, khai mép) theo từng ρ **thật** sẽ do lượt đầy đủ sinh ra.

- `log_sha256` (lượt kiểm chứng): `0b2349088cfff91f571c32eac113bc79d4572053c7d7fa3e35dd54f43629a360`.
- Worst-case theo kernel: minimax lấy max qua 3 kernel (nominal/low/high, ζ = 0,10) và qua các cột (tuning-attacker × Δ), đúng C6 / D5.robust; test `test_tuning_objective_is_worst_case_L_over_three_kernels` khoá.

## Trạng thái lượt đầy đủ

- `reference/v3_tuned.json` (3 kernel) và `reference/v3_tuned_nominal.json` (`--nominal-only`): sinh bằng `tools/v3_tune.py --real` / `--real --nominal-only`, mở chế độ `"x"` (nếu file đã có thì dừng và báo, không ghi đè). Kèm log chọn `<out>.log.jsonl`, `log_sha256` trong output khớp sha256 của log ghi ra; `check_tuned` chấp nhận; η_Q ở mép mang `edge_declaration`.
- Chưa tồn tại khi viết báo cáo này (mode `"x"` an toàn). Lượt đầy đủ đã khởi động ở nền; do ~104 + ~35 giờ CPU, dự kiến không xong trong phiên. Khi xong, hai file cùng `<out>.log.jsonl` là kết quả để commit vào `reference/`.

## Kiểm thử

- `../.venv/bin/python tests/run_v3.py`: **mọi cổng xanh** (Gate 0 3/3, Gate 1 66/66, Gate 2 155/155; 0 hàng P2 pending).
- `../.venv/bin/python tools/v3_dcm.py --check`: **0 vấn đề**.
- `tests/v3/test_s5_tuning.py`: 4/4 xanh (chưa đổi test; wiring thật là hoàn thiện hành vi đã khai, không đổi hành vi đã khai, nên không sửa hàng DCM T18).
