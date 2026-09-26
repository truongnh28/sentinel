# Sai lệch đã khai: một lượt smoke đã chạm tập eval (25/09/2026)

**Đừng mở `eval-summary.json` trước khi thầy chọn `HEADLINE_RHO` (D20).**

Khi dựng lại plan ngày 25/09, trợ lý (Claude) chạy một lượt smoke của công cụ eval để kiểm đường ống. Lượt đó dùng **tập eval** (16 repo held-out) và **7 attacker held-out**, với:

- bảng tinh chỉnh rút gọn `v2_tuned_smoke.json`: chỉ ρ = 0,25, 1 seed, gộp detector; lưới η_Q và τ₅ **trước** khi mở rộng;
- 3 seed eval, Δ ∈ {0, 4, 8}, ρ ∈ {0,25; 1}, detector mid;
- driver `smoke_eval.py` (bỏ qua freeze).

Cấu hình đó không đóng băng và **không phải** cấu hình của nghiên cứu.

Trình tự, ghi đúng như đã xảy ra:
1. Mọi quyết định thiết kế của plan 25/09 (mô hình carrier, thư viện, dòng 1/5/7/8, drift tạm thời, trần FQ 10%, cross-fit, đối chứng, Bonferroni, 10 seed, thế giới phụ) đã được viết thành code **trước** lượt chạy này.
2. Một lượt tinh chỉnh thử **trên dev**, chạy trước lượt smoke, cho η_Q và τ₅ tối ưu nằm ở mép dưới lưới.
3. Lượt smoke chạm tập eval.
4. **Sau** lượt smoke, dựa trên (2) và trên các lượt tinh chỉnh dev tiếp theo:
   - lưới η_Q và τ₅ được nới xuống tới 0 (luật ngây thơ);
   - η_Q hoà thì chọn FQ% thấp nhất;
   - phép quét η_Q đổi từ hệ số nhân sang giá trị tuyệt đối (hệ quả của việc nới lưới).
   Các sửa công cụ không đổi số: `--split dev`, tóm tắt phép quét, `costs.install` cho header.

Người duy nhất đã xem số là trợ lý; số không được đưa cho học viên hay thầy.

Vì vậy tập eval **không còn nguyên vẹn tuyệt đối**. Việc này được khai ở mục Sai lệch của tiền đăng ký v2. Công cụ eval trong plan nay có `--split dev` để lượt smoke không bao giờ chạm eval nữa.
