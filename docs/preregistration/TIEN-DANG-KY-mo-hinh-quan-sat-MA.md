# Tiền đăng ký — mô hình quan sát MA: trả tiền mới được nhìn (T1 / P2)

**Ngày:** 24/09/2026 · **Khai trước khi sửa mã và trước khi chạy, trước mốc đóng băng 29/09**

---

## 1. Sự việc

`runner.run_once` tính tín hiệu carrier cho **cả bốn carrier ở mọi task** rồi mới
gọi `pol.choose`. Nên chính sách audit gì thì defender vẫn thấy mọi thứ, và
ngân sách chỉ mua **hành động**, không mua **thông tin**. `tools/measure_c.py`
đo được hệ quả: posterior tại $\sigma$ đứng yên khi $B$ đi từ 2 đến 200, nên
tiền đề của Định lý 4 không thoả và hằng $c$ không fit được.

Đây là mô hình **M0** (quan sát miễn phí toàn phần). Kế hoạch
([P2](../design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md)) đề xuất
**MA làm mô hình chính, giữ M0 làm đối chứng, báo cả hai bảng**.

## 2. Việc sẽ làm

**MA:** chính sách chỉ thấy posterior của carrier mà nó **đã trả tiền audit ở
bước trước**, đúng giá trị lượt audit đó đọc được. Carrier không được audit trả
về `CarrierSignal(p = π₀, n = số item thật)` — tức **không có bằng chứng**, không
phải "sạch" và cũng không phải thiếu khoá. Số item $n$ là siêu dữ liệu, không phải
tín hiệu detector, nên vẫn thấy miễn phí.

Commit-audit **không** làm lộ carrier nào: nó kiểm patch, không kiểm carrier.

Cài bằng cờ `runner.OBSERVATION ∈ {"M0", "MA"}` và `--observation` ở
`experiment.py`; **mặc định M0**, nên mọi bảng cũ giữ nguyên từng chữ số. `replay`
áp cùng mô hình. `tools/measure_c.py` chạy cả hai.

## 3. Dự đoán — khai trước khi chạy

| # | Dự đoán | Sai khi nào |
|---|---|---|
| MA1 | **Harm của mọi chính sách đọc điểm tăng hoặc giữ nguyên, không giảm** — kể cả `Sentinel` và họ SSG. Đây là dự đoán **ngược chiều mong muốn**: chúng đang được cho thông tin miễn phí | có chính sách đọc điểm nào giảm harm có ý nghĩa dưới MA |
| MA2 | **B1 audit-at-commit y hệt** dưới M0 và MA: nó không đọc tín hiệu | B1 lệch dù chỉ một chữ số — khi đó mô hình quan sát đã rò vào đường không đọc tín hiệu, là **lỗi**, không phải kết quả |
| MA3 | **Ngân sách mua được thông tin** dưới MA: `budget_buys_information()` trả `True` | vẫn phẳng — khi đó script **tiếp tục từ chối** trả $c$, và đó là kết quả |
| MA4 | Khoảng cách B1 − họ SSG **hẹp lại** dưới MA | nới rộng |

Cam kết: **báo cả hai bảng** (M0 và MA) cạnh nhau dù số MA xấu hơn, kèm độ phủ
quan sát (tỉ lệ cặp carrier × task được nhìn).

Chọn bảng nào làm headline vẫn là **quyết định của thầy** (issue #13, T1); tài liệu
này chỉ khai việc đo.

---

## 4. Phụ lục (24/09, trước khi chạy `measure_c` dưới MA) — chính sách thăm dò

`tools/measure_c.py` đo tiền đề bằng **B7 minimax-lp**. Dưới MA, B7 là probe vô
dụng, và lý do đã **đo được trước**, không suy ra từ $c$: LP của nó đặt **0 độ phủ
lên carrier** (`spikes/budget-gap.json`, `carrier_coverage_lp = 0`), và trên 6
workflow nó chọn `commit` 24 lần, `none` 24 lần, **không một** lượt audit carrier.
Dưới MA nó không bao giờ mua được một lần nhìn, nên tiền đề sẽ phẳng vì **cách chọn
probe**, không phải vì mô hình quan sát.

**Probe dưới MA: `B2 uniform random`.** Nó audit carrier (24 queue, 18 memory,
6 commit trên cùng 6 workflow) và **không thích nghi**, nên nó đo đúng câu Định lý 4
hỏi — ngân sách mua quan sát thì posterior có hội tụ không — mà không trộn vào
chất lượng của một luật chọn thông minh.

Dưới M0 giữ B7 như cũ, để số M0 đã công bố không đổi. Báo cả hai probe dưới MA nếu
cần, nhưng **B2 là số chính, khai ở đây trước khi chạy**.
