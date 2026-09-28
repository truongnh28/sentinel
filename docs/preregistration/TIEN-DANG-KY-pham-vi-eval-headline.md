# Tiền đăng ký: lượt eval P5 thu hẹp về các ô tiêu đề (lệch chuẩn D-v3-7)

**Viết 29/09/2026, 00:5x — TRƯỚC khi `frozen/V3-GATE4.json` được ký và trước khi bất kỳ bản ghi eval nào tồn tại.** Tại thời điểm viết: không có tệp Cổng 4, `frozen/v3-unseal-log.jsonl` rỗng, chưa có record eval nào.

## 1. Thiết kế gốc nói gì

Kế hoạch S6/D33 quy định lượt eval là **một lượt duy nhất trên toàn bộ split đã ghim**. Lưới eval quét 36 ô bảng (ρ ∈ {0; 0,25; 0,5; 1} × χ ∈ {1,04; 1,33; 2,11} × d′ ∈ {1,52; 2,21; 2,96}) ở các khối `main`, `br`, `attacker-delta`.

Công cụ `tools/v3_run.py` vì vậy từ chối cờ `--headline` khi `--split eval` ("an eval run is the whole pinned split").

## 2. Lệch chuẩn sẽ thực hiện (D-v3-7, mức L1)

**Lượt eval P5 chỉ phủ các ô tiêu đề: χ = 1,33 và d′ = 2,21, đủ bốn ρ và đủ Δ ∈ {0, 1, 2, 4, 8}.** Các khối `sens:*`, `kd`, `h18`, `seed2-pairs` vốn đã nằm ở ô tiêu đề nên không bị ảnh hưởng. Cờ `--headline` được cho phép với `--split eval`; đây là một thay đổi mã, khai ở đây.

## 3. Lý do — nói thẳng, đây là ràng buộc nguồn lực, không phải lý do khoa học

Bảng dòng 5 cho cả 36 ô cần khoảng 111 CPU-giờ còn lại (đo được: 26–35 job/phút trên 10 nhân, 47.526 job còn thiếu), tức **khoảng 22–28 giờ máy**. Lịch của đề tài không còn khoảng đó trước mốc phải nộp. Bảng cho **4 ô tiêu đề đã dựng xong** (digest `sha256:83ecff91b369…`, base-R 16, 0 khoá phải bù).

Không viện lý do khoa học nào cho việc thu hẹp này. Nó là ràng buộc thời gian, và được khai trước khi thấy bất kỳ số eval nào.

## 4. Vì sao phần lõi khoa học vẫn còn nguyên

Các tiên đoán của lý thuyết đã sửa (Hệ quả 5, mô hình phủ) phát biểu trên **hai trục Δ và ρ**:

- G(0) = 0 (B1 minimax-tối-ưu khi attacker được chọn Δ = 0);
- gain không giảm theo Δ (ghi nhận là đơn điệu từ Δ ≥ 2);
- gain bị chặn bởi p_d − p_ρ, chặn này đóng về đúng 0 tại ρ = 1.

**Cả hai trục đó đều nằm đủ trong các ô tiêu đề** (đủ 4 ρ, đủ 5 Δ). Vì vậy lượt eval thu hẹp vẫn kiểm được toàn bộ các tiên đoán trung tâm, gồm cả H18 (chiều của Định lý 4 sau khi sửa).

χ (không đồng nhất giá audit) và d′ (độ mạnh detector) là **trục thứ cấp**. Cái mất là:

- **H3** (trục χ, điểm giao theo χ) — không đo;
- **H5** (không đồng nhất so với đều) — không đo;
- **H13** (trục d′) — không đo;
- **H18 vế χ** (luật E) — không đo;
- Bảng `tab:rq1` các hàng χ = 1,04 và χ = 2,11, và `tab:detector` các hàng detector yếu/mạnh — giữ trống với lý do này.

Cả năm mục trên được ghi là **không đo** (N3), **không** ghi 0, và **không** suy ra từ ô tiêu đề.

## 5. Ghi chú đã biết trước, không liên quan tới lệch chuẩn này

Lưới χ đã khai ({1,04; 1,33; 2,11}) **không đạt được ở giá audit đo thật** (đo được χ ở các mức 2,58 / 3,10 / 3,15; xem `docs/reports/v3-p3-kappa.md`). Nghĩa là dù có dựng bảng đủ 36 ô thì trục χ vẫn mang một sai đặc tả đã khai. Điều này **làm giảm** phần mất mát của D-v3-7, nhưng **không phải** lý do để thu hẹp: quyết định thu hẹp là do thời gian.

## 6. Những gì KHÔNG đổi

- Tập eval, thứ tự ghim, luật chọn split: không đổi.
- Policy, giá trị tuned (`reference/v3_tuned.json`, log sha256 `36550dae6ba0…`), bảng dòng 5 (`sha256:83ecff91b369…`), luật scorecard: không đổi, và chính chúng được ghim vào tệp Cổng 4.
- λ_Q = 0,54865, λ_T = 0,5: không đổi.
- Vệ sinh giữ ngoài của bộ attacker tinh chỉnh (`tuning_attack_names` loại mọi cột giao behaviour-key với held-out): không đổi.
- Metric headline vẫn là L của Định nghĩa 1 với V = harm in kèm (D-v3-6).
## 6b. Thiết kế HAI LƯỢT, khai trước khi ký (thay cho luật một-lượt)

Tác giả quyết định sẽ chạy **hai lượt eval theo kế hoạch**, và khai cả hai **tại đây, trước khi tệp Cổng 4 tồn tại**:

| | Phạm vi | Trạng thái |
|---|---|---|
| **Lượt 1** (tài liệu này) | Ô tiêu đề: χ = 1,33; d′ = 2,21; đủ 4 ρ; đủ Δ ∈ {0,1,2,4,8} | Tiền đăng ký, chạy ngay |
| **Lượt 2** | Phần còn lại của lưới: χ ∈ {1,04; 2,11} × d′ ∈ {1,52; 2,96} và các ô kết hợp, tức 32 ô ngoài tiêu đề | Tiền đăng ký **tại đây**, chạy sau khi bảng dòng 5 đủ 36 ô dựng xong |

Vì sao hai lượt mà vẫn hợp lệ:

1. **Phạm vi của cả hai lượt được ghim ở đây, trước khi thấy bất kỳ số eval nào.** Lượt 2 không phải một lần "nhìn thêm" sau khi đã biết kết quả; nó là phần còn lại của một thiết kế đã khai.
2. **Policy không thể đổi giữa hai lượt.** Tệp Cổng 4 ghim digest của manifest v3, luật scorecard và bảng dòng 5. Nếu policy, giá trị tuned hay bảng thay đổi, `seal.reasons` sẽ báo lệch digest và **từ chối** lượt 2. Tự do duy nhất còn lại là phạm vi ô, và phạm vi đã ghim ở mục 6b này.
3. **Bảng dòng 5 của các ô tiêu đề không đổi giữa hai lượt.** Ngăn được tính theo từng ô (phân vị của chính trạng thái nguồn của ô đó) và mọi rút số đều keyed, nên entry của 4 ô tiêu đề **giống hệt** dù bảng có 4 hay 36 ô. Lượt 2 vì vậy **không** làm thay đổi số của lượt 1.
4. **Mọi lần unseal đều được ghi** vào `frozen/v3-unseal-log.jsonl`. Hai dòng sẽ xuất hiện. Đó là bằng chứng công khai cho đúng thiết kế hai lượt này, không phải dấu vết của một lần lách.

**Điểm yếu phải thừa nhận:** hai lượt trên cùng một tập held-out vẫn yếu hơn một lượt, vì trên nguyên tắc các quyết định của lượt 2 có thể bị ảnh hưởng bởi kết quả lượt 1. Biện pháp giảm thiểu là ba điều trên: phạm vi ghim trước, policy bị digest chặn không cho đổi, và dự đoán của lượt 2 ghim ngay dưới đây.

### Dự đoán ghim cho LƯỢT 2 (trước khi lượt 1 chạy)

1. **H3** (trục χ): điểm giao theo χ nằm trong khoảng χ đo được, và gain theo L **giảm** khi χ tăng (audit đắt hơn ⇒ phân bổ khó bù hơn).
2. **H13** (trục d′): gain theo L **tăng** theo d′ (detector mạnh hơn ⇒ belief hữu ích hơn ⇒ phân bổ có lợi hơn).
3. **H5**: không-đồng-nhất giá audit làm gain theo L **lớn hơn** so với cánh giá đều ở cùng ρ.
4. Dấu của gain ở các ô ngoài tiêu đề **cùng dấu với ô tiêu đề tại cùng ρ** ở ρ = 0 và ρ = 1.
5. Lượt 2 **không** làm đổi bất kỳ số nào của lượt 1 (kiểm được: so lại entry bảng của 4 ô tiêu đề, phải trùng bit).

Sai so với năm dự đoán này được ghi nguyên trạng, không hiệu chỉnh sau (N3). Nếu lượt 2 **không** chạy được (hết thời gian, hết nguồn lực), các giả thuyết ở mục 4 vẫn ghi là **không đo**, không suy diễn từ lượt 1.

## 7. Dự đoán ghim (bổ sung cho các dự đoán ở `TIEN-DANG-KY-metric-headline-V.md`)

Trên phạm vi thu hẹp này, ghim trước khi chạy:

1. Dấu của gain theo L trên eval **cùng dấu với dev** ở ρ = 0 và ρ = 1 (dương ở ρ = 0, âm ở ρ = 1).
2. **Độ lớn** gain trên eval **nhỏ hơn** trên dev ở cùng ρ, vì attacker giữ ngoài của eval chưa từng vào quá trình tinh chỉnh.
3. H18 giữ kết luận: vế bản sửa khớp, vế bản in của Định lý 4 bị bác.
4. Theo harm đơn thuần, gain âm ở mọi ρ.

Sai so với bốn dự đoán này được ghi nguyên trạng, không hiệu chỉnh sau (N3).

## 8. Hiệu lực

Tài liệu này chỉ có hiệu lực nếu được chốt **trước** khi `frozen/V3-GATE4.json` tồn tại. Người ký Cổng 4 xác nhận đã đọc mục 2, 3 và 4 — tức chấp nhận rằng H3, H5, H13 và vế χ của H18 sẽ **không có số** trong lượt này.
