# Khai bổ sung: lượt eval 1 được chạy bằng nhiều lệnh song song trên các block rời nhau

**Viết 29/09/2026 ~08:0x, TRƯỚC khi phóng các lệnh song song.** Bổ sung cho `TIEN-DANG-KY-pham-vi-eval-headline.md` (lệch chuẩn D-v3-7). Không đổi phạm vi, không đổi policy, không đổi metric.

## 1. Vấn đề

`tools/v3_run.py` buộc lượt eval chạy **đơn tiến trình**: dòng `in_process = run_chain is not None or jobs <= 1 or token is not None`. Token của `seal.unseal` là object trong-tiến-trình và `eval_workflows` xác thực bằng *identity* trên danh sách `_ISSUED` riêng của mỗi process, nên token không băng qua ranh giới process. Vì vậy `--jobs` bị vô hiệu với eval.

Không sửa được mã: tệp Cổng 4 đã ghim `v3_manifest = 9c4c0d018b18…`; sửa `tools/v3_run.py` sẽ đổi digest đó và `seal.reasons` sẽ **từ chối** mọi lượt eval tiếp theo. Cơ chế hoạt động đúng như thiết kế.

Ở một nhân, phần còn lại của lượt 1 (≈108.120 chain trên 133.720) cần khoảng **22 giờ**.

## 2. Việc sẽ làm

Lượt 1 được chạy bằng **sáu lệnh `tools/v3_run.py` riêng, song song, trên các tập block RỜI NHAU**, mỗi lệnh vẫn đơn tiến trình, mỗi lệnh ghi vào thư mục đầu ra riêng:

| Lệnh | Block | Chain |
|---|---|---|
| 1 | `sens:reversible` | 22.400 |
| 2 | `sens:ingress-hidden` | 22.400 |
| 3 | `sens:drift-persistent` | 22.400 |
| 4 | `sens:seed-2` | 22.400 |
| 5 | `h18`, `kd`, `attacker-delta` | 17.040 |
| 6 | `br`, `h18-br`, `kd-br`, `sens-br:*`, `sens-attacker-delta:reversible` | 4.680 |

Block `main` (22.400 chain) **đã chạy xong** trước khai bổ sung này, bằng một lệnh đơn, và số của nó đã được dùng.

## 3. Điều này đổi gì, và KHÔNG đổi gì

**Đổi:** `frozen/v3-unseal-log.jsonl` sẽ có **bảy dòng** thay vì một — một dòng của lệnh `main` đã chạy (2026-09-28T18:10:14Z) và sáu dòng của các lệnh trên. Mọi dòng đều `granted`, `split=eval`, `headline=true`.

**KHÔNG đổi:**

1. **Phạm vi.** Tập hợp các block và ô đúng như D-v3-7 đã khai. Không thêm một ô, một block, một hệ thống nào.
2. **Không có phép nhìn-rồi-quyết.** Sáu lệnh được **phóng cùng lúc, trước khi bất kỳ kết quả nào của chúng được xem**. Việc chia block là chia theo chi phí tính toán, quyết định trước khi chạy, ghi ở mục 2.
3. **Policy bị digest chặn.** Cổng 4 ghim manifest, luật scorecard và bảng dòng 5; nếu bất kỳ thứ nào đổi giữa các lệnh thì `seal.reasons` từ chối. Sáu lệnh vì vậy chạy đúng một policy đã đóng băng.
4. **Kết quả không phụ thuộc cách chia.** Mọi rút ngẫu nhiên đi qua seed keyed (`core.seed_of`); post-mortem của dòng 1 chỉ mang trong cùng `(cell, system, column, seed)`; không có trạng thái chia sẻ giữa các block. Nên số thu được **giống hệt** lượt chạy một lệnh, và điều này **kiểm được**: block `main` đã chạy đơn lệnh và các block khác không đọc gì của nó.
5. **Vẫn là lượt 1.** Lượt 2 (32 ô ngoài tiêu đề) vẫn như D-v3-7 đã khai: đã tiền đăng ký, chưa chạy.

## 4. Điểm yếu phải thừa nhận

Bằng chứng "một lượt" trong log yếu hơn: người đọc không thể chỉ đếm số dòng log để kết luận không có phép nhìn-rồi-quyết, mà phải tin mục 3.2 (sáu lệnh phóng cùng lúc). Bù lại có ba thứ kiểm được độc lập: dấu thời gian của sáu dòng log nằm trong cùng một phút; `run_meta` của mỗi dòng ghi đúng tập block đã khai ở mục 2; và policy bị digest Cổng 4 chặn không cho đổi.

Nếu chọn cách trung thực nhất thì nên chạy một lệnh 22 giờ. Việc chia sáu là **đánh đổi vì thời gian**, do tác giả quyết, khai ở đây.

## 5. Không đổi kết luận đã có

Số headline (Table 2, ô tiêu đề, Δ ∈ {4,8}) đến từ block `main` **đã chạy xong bằng một lệnh đơn trước khai bổ sung này**. Sáu lệnh chỉ thêm: exploitability (`br`), H18/H19 phía eval (`h18`, `kd`), bốn thế giới độ nhạy, và cột attacker-chọn-Δ. Không lệnh nào tính lại số của `main`.
