# Tiền đăng ký — attacker tối ưu tự do trên $(k, \iota, \sigma)$

**Ngày:** 24/09/2026 · **Khai trước khi chạy, trước mốc đóng băng 29/09**

---

## 1. Sự việc

Mô hình phát biểu attacker **best-response**: thấy chính sách đã cam kết rồi
chọn cấu hình xấu nhất cho nó. Mã thì không làm thế.

`build.plan_poison` lọc ra tập σ khả dĩ rồi **bốc ngẫu nhiên một phần tử**:

```python
cands = [s_ for s_ in range(delta, wf.H) if ...]   # build.py:293
s_ = rng.choice(cands)                             # build.py:298
```

`runner.worst_case` lấy max trên $(\Delta, k)$ — nhưng với **một** σ duy nhất đã
bốc sẵn cho mỗi $(wf, k, \Delta)$. Ở $H = 8$, $\Delta = 2$ tập `cands` có tới
**6** phần tử, nên attacker đang bị bỏ mất 5/6 lựa chọn.

$\iota = \sigma - \Delta$ nên bậc tự do thật là $(k, \sigma)$ với $\Delta$ cố
định theo cột. $\varepsilon$ giữ nguyên 0,6, không nằm trong lượt này.

**Hệ quả:** mọi số worst-case đã công bố là **lạc quan**. Chúng là
$\max_k \mathbb{E}_\sigma[\cdot]$ chứ không phải $\max_{k,\sigma}[\cdot]$.

## 2. Việc sẽ làm

Thêm `build.plan_poison_all` liệt kê **toàn bộ** σ khả dĩ, và đo worst-case lấy
max trên $(k, \sigma)$. Đường chính **chưa đổi** — đo trước bằng công cụ riêng,
rồi mới quyết định, vì nó làm mọi bảng phải chạy lại.

## 3. Dự đoán — khai trước khi chạy

| # | Dự đoán | Sai khi nào |
|---|---|---|
| BR1 | Harm worst-case **tăng ở mọi chính sách** | Đúng theo cấu tạo (max trên tập cha). Nếu có chính sách nào **không** tăng, tập con/cha đang bị tính sai — đây là kiểm tra tính đúng, không phải phát hiện |
| BR2 | **Độ lợi so với B1 thu hẹp.** B1 audit-at-commit **không phụ thuộc σ** — nó kiểm ở commit bất kể payload nằm đâu — nên harm của nó tăng **ít nhất**; các chính sách thích nghi bị σ khai thác nên tăng nhiều hơn | sai nếu độ lợi giữ nguyên hoặc nới rộng |
| BR3 | Thứ hạng **đổi ở ít nhất một ô** | sai nếu 12 ô giữ nguyên thứ tự |
| BR4 | Chính sách **ngẫu nhiên hoá tăng ít hơn** chính sách tất định: so `Sentinel` với `C8 deterministic sentinel`, vì đây đúng là đại lượng mà ngẫu nhiên hoá sinh ra để giảm | sai nếu C8 tăng ít hơn hoặc bằng `Sentinel` |

**Không sửa dự đoán sau khi thấy số.**

## 4. Điều phải nói dù kết quả ra sao

Nếu BR2 đúng thì mọi độ lợi đã báo — vốn đã **không ô nào đạt ngưỡng 15%** ở
$N = 100$ — còn tụt thêm. Khi đó kết luận "không chính sách nào đạt ngưỡng"
**mạnh lên**, chứ không yếu đi, vì nó được đo dưới một attacker đúng mô hình hơn.
