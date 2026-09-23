# Tiền đăng ký — đóng đường cách ly không bị tính tiền

**Ngày:** 24/09/2026 · **Khai trước khi chạy lại, trước mốc đóng băng 29/09**

---

## 1. Sự việc

`runner.py` có **hai** đường đưa một item vào cách ly, và **chỉ một** bị trừ ngân sách:

| Đường | Ở đâu | Có `pol.charge`? |
|---|---|---|
| Hành động trực tiếp `quarantine:<carrier>` | runner.py:423–436 | **Có** — `pol.charge(P.cost_of(act))` |
| Hệ quả của một lượt audit | runner.py:446–459 | **Không** |

Đường thứ hai vẫn ghi `_quarantine_record`, vẫn cộng vào `true_quarantine` /
`false_quarantine`, vẫn bị $\lambda_Q$ tính tiền trong hàm mất mát $L$. Nghĩa là
nó **bị phạt trong lúc chấm điểm nhưng không bị ràng buộc trong lúc quyết định**
— đúng thứ `policies.py:624` đã viết ra: *"quarantine was effectively free —
penalised only through $\lambda_Q$ in the loss, which is a preference, not a
constraint."* Bản sửa hồi đó **thêm** hành động trực tiếp chứ không đóng đường cũ.

Thêm một chi tiết: `Policy.eta_Q` (policies.py:123) là field riêng của policy,
**mặc định 0,0**, không nối gì với `ETA_Q_COST`. Không chỗ nào trong mã đặt nó
ngoài một test. Nên chặn `expected_harm(...) <= pol.eta_Q` gần như luôn mở.

## 2. Đo được: giá không chạm tới ba chính sách

Quét $r = \eta_Q/\bar\kappa$ từ 1,143 tới 61,519 (`tools/sweep_eta_q.py`,
$n = 20$, $\Delta = 2$, detector mid):

| Chính sách | Q ở $r=1{,}143$ | Q ở $r=61{,}5$ | $L$ ở 1,143 | $L$ ở 61,5 |
|---|---:|---:|---:|---:|
| NC1 quarantine-everything | 550 | **0** | 3,6432 | 1,0000 |
| SentinelW window-belief | 350 | 176 | 2,1015 | 1,1801 |
| **Sentinel** | 246 | **246** | 1,3809 | **1,3809** |
| B5 risk-score | 124 | 124 | 1,0533 | 1,0533 |
| B6 two-stage | 120 | 120 | 1,1920 | 1,1920 |
| B1, SSG-G | 0 | 0 | — | — |

`Sentinel`, B5, B6 **không đổi một lượt nào** qua thay đổi giá 54×, và $L$ của
chúng đứng yên tới bốn chữ số. Chúng chỉ đi đường miễn phí.

Hệ quả cho kết quả đã công bố: **không có điểm lật nào** trong toàn dải — SSG-G
thắng ở mọi $r$ — vì chính sách nào cách ly thì không trả tiền, còn chính sách
thắng thì không cách ly. Trục $\eta_Q$ hiện **trơ theo cấu tạo**, không phải theo
phát hiện.

## 3. Việc sẽ làm, và lựa chọn bị loại

**Chọn:** tính **pro-rata** — một lượt audit gỡ $m$ item khỏi carrier $k$ đang có
$n$ item sống thì bị trừ $\eta_Q \cdot m/n$, và không được gỡ nếu không đủ tiền.

Ở $m = n$ nó bằng đúng giá hành động trực tiếp, nên hai đường **cùng giá cho
cùng một việc** — đó là điều kiện để so sánh chúng có nghĩa. Không thêm hằng số
mới, và vẫn bất biến theo hệ số chung.

**Loại — tính trọn $\eta_Q$ mỗi lần gỡ:** làm đường có mục tiêu đắt hơn đường bán
buôn cho cùng một item, tức phạt sự chính xác.

**Loại — tính theo giá ghi lại từng item (`USD_PER_WRITE`):** đúng về đo lường
(nửa phục hồi *là* $n_{\text{live}}$ lượt ghi) nhưng đưa một hằng số thứ hai vào
mô hình hành động, trong khi pro-rata suy ra được cùng con số từ $\eta_Q$ sẵn có.

## 4. Dự đoán — khai trước khi chạy

| # | Dự đoán | Sai khi nào |
|---|---|---|
| Q1 | Số lượt cách ly của `Sentinel`, B5, B6 **trở nên nhạy giá**; ở $r = 61{,}5$ tụt về 0 | còn lượt nào ở $r = 61{,}5$ |
| Q2 | **Harm của ba chính sách đó tăng** ở $r = 61{,}5$ | cách ly đang gỡ payload miễn phí; nếu harm không tăng thì cách ly không phải thứ giúp chúng |
| Q3 | Ở $r = 1{,}143$ số lượt **giảm nhưng vẫn > 0** | một lượt bán buôn chỉ tốn 11% ngân sách |
| Q4 | **Xuất hiện điểm lật** trong $r \in [1{,}14;\ 61{,}5]$, và **khoảng cách dẫn của SSG-G nới rộng theo $r$** | sai nếu thứ hạng vẫn bất động như bảng §2 |
| Q5 | Gain `Sentinel` vs B1 ở $\Delta = 4$ **giảm** so với mức legacy +43,4% | sai nếu giữ nguyên hoặc tăng |

**Không sửa dự đoán sau khi thấy số.**

## 5. Điều phải nói trong bài dù kết quả ra sao

Ở giá đo được, **mọi** hình thức cách ly đều vượt ngân sách episode — kể cả gỡ
đúng một item, vì một lượt ghi lại tốn $19{,}7\,\bar\kappa$ so với ngân sách
$10{,}26\,\bar\kappa$. Nên kết luận đúng không phải "cách ly là hành động tồi" mà
**"ở thang giá này, cách ly không phải là một hành động"**, và mọi kết quả trước
đây có dính cách ly đều chạy trên một hành động lẽ ra không mua được.
