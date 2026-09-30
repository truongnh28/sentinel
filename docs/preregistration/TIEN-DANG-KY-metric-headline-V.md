# Tiền đăng ký: metric headline của Study 2 — V = harm hay L (Định nghĩa 1)?

**Viết 28/09/2026, TRƯỚC khi chạy bất kỳ lượt eval P5 nào.** Lượt eval chưa chạy; `frozen/V3-GATE4.json` chưa tồn tại; `frozen/v3-unseal-log.jsonl` rỗng. Mục đích của tài liệu này là **chốt metric headline trước khi thấy số eval**, để lựa chọn không thành post-hoc.

## 1. Vấn đề phát hiện được (trên dev, 28/09)

Mã hiện tại dùng **hai metric khác nhau cho hai việc**:

| Việc | Metric | Vị trí trong mã |
|---|---|---|
| Tinh chỉnh τ, η_Q, τ5, trọng số SW | **L (Định nghĩa 1)** = `harm + λ_Q·FQ + λ_T·(task sạch mất)` | `tools/v3_tune.py:328` → `runner.loss_of(rec)` |
| Báo cáo V của Table 2 và `gain_ci` | **harm đơn thuần** | `metrics.worst_case_harm` → `metrics.table(..., field="harm")` (mặc định) |

λ_Q = 0,54865; λ_T = 0,5. Docstring của `worst_case_harm` ghi "Draft S9.3 primary", tức **draft khai V = harm là metric chính**, trong khi policy lại được tối ưu theo L.

**Hai metric cho kết luận trái ngược nhau** trên dev (ô headline χ=1,33, d′=2,21, Δ∈{4,8}, 100 workflow × 2 seed, chi tiết ở `docs/reports/v3-p2-headline-dual-metric.md`):

| ρ | gain theo **L** | gain theo **harm** |
|---|---|---|
| 0 | +22,6% [+15,9; +33,5] | −4,3% [−11,2; +4,8] |
| 0,25 | +20,9% [+11,7; +37,0] | −22,6% [−32,3; −3,4] |
| 0,5 | +14,0% [+3,6; +23,8] | −46,4% [−62,2; −25,9] |
| 1 | −47,2% [−90,8; −13,0] | −292,9% [−483,2; −178,9] |

Nguyên nhân: B1 audit-at-commit đạt harm thấp nhưng **phá 0,705 task sạch mỗi episode** (clean-completion 90,4%, FQ = 0 — đó là thiệt hại kèm của các lần cách ly ĐÚNG, ngữ nghĩa O7). Sentinel mất 0,083 task sạch (clean 98,6–99,2%) với FQ 0,099. Metric harm-only **không tính** phần thiệt hại kèm đó; L thì có.

## 2. Quyết định đăng ký

**Headline của Study 2 là L của Định nghĩa 1.** V = worst-case harm vẫn được báo cáo, như một cột của Table 2.

Căn cứ:

1. **Chính paper định nghĩa L là mục tiêu.** Định nghĩa 1 phát biểu `L = harm + λ_Q FQ + λ_T (task sạch mất)`. Nếu headline không phải L thì paper đang tối ưu một thứ và tuyên bố một thứ khác.
2. **Policy được tinh chỉnh theo L.** Chấm một policy bằng metric khác metric nó được tối ưu là so lệch; nó phạt Sentinel vì đã đánh đổi harm để giữ task sạch — đúng cái đánh đổi mà L yêu cầu.
3. **Harm-only thưởng cho thiệt hại kèm.** Một chính sách "cách ly thật nhiều" hạ được harm bằng cách phá công việc hợp lệ; harm-only cho nó điểm cao. Đó là lỗ hổng đo lường, không phải ưu điểm của chính sách.
4. **λ_Q, λ_T đã được đăng ký trước** (`TIEN-DANG-KY-lambda-T.md`; λ_Q dẫn xuất từ đo lường, không phải trọng số tự do). Dùng L **không** đưa thêm bậc tự do nào vào phân tích.

## 3. Đây là một lệch chuẩn, khai rõ

Draft khai V = harm là primary (S9.3). Đổi headline sang L vì vậy là **lệch chuẩn D-v3-6**, mức L1 (đổi cách đọc kết quả, không đổi thế giới, không đổi policy, không đổi dữ liệu).

- **Không** đổi: thế giới, policy, bộ attacker, tập chia, λ_Q, λ_T, luật bootstrap, luật scorecard.
- **Chỉ** đổi: metric nào là headline. Cả hai đều được in.
- Table 2 sẽ có **cả hai cột** (V_harm và V_L) ở mọi ô, nên người đọc kiểm chéo được và không mất thông tin nào.
- `metrics.gain_ci` giữ nguyên; gain theo L tính bằng chính bộ bootstrap đó, chỉ truyền `field="loss"` sau khi gắn `runner.loss_of(rec)` vào mỗi record. Không viết lại metric hay CI nào.

## 4. Dự đoán ghim trước lượt eval

Ghim trước khi chạy P5, dựa trên dev và trên mô hình phủ (Hệ quả 5 sau khi sửa):

1. **Theo L, gain của Sentinel so với B1 sẽ dương ở ρ ≤ 0,25** và âm ở ρ = 1.
2. **Gain không giảm theo Δ** ở mỗi ρ (Hệ quả 5). Cụ thể gain tại Δ = 8 ≥ gain tại Δ = 4 ở mọi ρ, sai số bootstrap cho phép.
3. **Ranh giới chuyển chế độ nằm trong khoảng ρ ∈ [0,25; 1]**, và ở ρ = 0,5 dấu của gain **phụ thuộc Δ** (âm ở Δ nhỏ, dương ở Δ = 8).
4. **Theo harm-only, gain sẽ âm ở mọi ρ** — và nếu điều này xảy ra thì nó là bằng chứng cho mục 1 của §2, không phải bằng chứng Sentinel kém.
5. Trên eval (repo held-out + attacker held-out), **độ lớn gain theo L sẽ nhỏ hơn dev** ở cùng ρ, vì attacker held-out của eval chưa từng vào quá trình tinh chỉnh.

Sai so với các dự đoán này đều được ghi lại nguyên trạng, không hiệu chỉnh sau (N3).

## 5. Những gì tài liệu này KHÔNG cho phép

- **Không** thêm bất kỳ attacker held-out nào vào bộ tinh chỉnh. `attackers.tuning_attack_names` chủ động loại mọi cột có behaviour-key giao với held-out (`if keys & held: continue`); vệ sinh này giữ nguyên. Ba cột xấu nhất trên dev (`branch-first-write-e0.6`, `memory-mid-write-e0.3`, `queue-mid-write-e0.6`) **không** được đưa vào tinh chỉnh.
- **Không** chỉnh lại λ_Q hay λ_T sau khi thấy số. Chúng đã đăng ký trước.
- **Không** chỉnh lại τ, η_Q theo kết quả eval. Chúng đã ghim trong `reference/v3_tuned.json` (log sha256 `36550dae6ba0…`) trước Cổng 4.
- **Không** đổi số hạt particle filter (2048, S7) để đổi chi phí hay kết quả.

## 6. Hiệu lực

Tài liệu này chỉ có hiệu lực nếu được chốt **trước** khi `frozen/V3-GATE4.json` được ký. Tại thời điểm viết: chưa có tệp Cổng 4, log unseal rỗng, chưa có record eval nào. Tác giả/giảng viên hướng dẫn xác nhận mục §2 trước khi ký Cổng 4; nếu chọn giữ V = harm làm headline thì ghi lại tại đây và **không** cần D-v3-6.
