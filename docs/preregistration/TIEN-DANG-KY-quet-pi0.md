# Tiền đăng ký — quét $\pi_0$ (#18)

**Ngày:** 24/09/2026 · **Khai trước khi viết công cụ và trước khi chạy. Cấu hình đóng băng `sha256:ab6179a2ed4a` không đổi.**

---

## 1. Sự việc

$\pi_0 = 1/E[n_{\text{total}}] = 0{,}0799$ được **suy dẫn**, không phải chọn tay
(`costs.PI0_WORLD`, M3). Nhưng chưa ai kiểm xem thứ hạng chính sách có đổi khi
$\pi_0$ dịch chuyển hay không. Một người phản biện hợp lý sẽ hỏi: "0,0799 là trung
bình trên 20 episode đo — nếu nó là 0,04 hay 0,20 thì kết luận còn đứng không?"

## 2. Việc sẽ làm

$\pi_0$ đi vào mô hình qua **ba đường**:

1. `scoring.posterior` / `scoring.carrier_score`: posterior mà chính sách đọc.
2. `scoring.tau_sel`: bảng ngưỡng sinh **từ** $\pi_0$ (`reference/score_table.json`).
3. Các biến đổi bằng chứng `p / π₀` ở `belief.py` và `policies.py`.

**Bảng $\tau_{\text{sel}}$ không cần sinh lại (23 phút mỗi giá trị).** $\tau_{\text{sel}}$
là một **thống kê thứ tự** của $p_c$ trên carrier sạch (`ps[int((1-α_c)M)]`, không nội suy),
và $p = \pi_0\bar\Lambda / (\pi_0\bar\Lambda + 1 - \pi_0)$ đơn điệu tăng theo $\bar\Lambda$.
Nên thống kê thứ tự của $p$ ở $\pi_0'$ **bằng đúng** ảnh của thống kê thứ tự ở $\pi_0$
qua phép đổi $p \mapsto \bar\Lambda \mapsto p'$. Công cụ đổi bảng bằng công thức này
và một test kiểm tính đúng trên mẫu tổng hợp.

Công cụ `tools/sweep_pi0.py` đặt $\pi_0$ cho **cả ba đường** trong một context
manager, rồi trả lại nguyên trạng. File đóng băng **không bị ghi**. Manifest sẽ báo
DRIFTED trong lúc chạy, và đó là đúng: đây là phép kiểm độ nhạy, không phải cấu hình.

**Lưới:** $\pi_0 \in \{0{,}04;\ 0{,}0799;\ 0{,}10;\ 0{,}20\}$. 0,04 là `PI0_MODEL`
($\pi_{\text{attack}}\cdot\pi_0$), tức cận dưới có lý do. 0,20 là gấp 2,5 lần.
**Ô:** ngân sách 0,3205 (bảng đã công bố) và 0,75 (dải của #13, #17);
$\Delta \in \{2, 4\}$; detector mid; $N = 40$, 3 seed, USD.
**Chính sách:** tập của `sweep_budget.py`, thêm `SSG-up receding` và `B5 risk-score`
(đọc ngưỡng trực tiếp, nên nhạy $\pi_0$ nhất).

## 3. Dự đoán — khai trước khi chạy

| # | Dự đoán | Sai khi nào |
|---|---|---|
| π1 | **B1, B2, `SSG-full`, `SSG-up` y hệt từng chữ số** ở mọi $\pi_0$. Không chính sách nào trong bốn cái này đọc `.p` (`SSGReceding.choose` chỉ giải LP trên $\kappa$, $B$ và $\Delta$) | lệch dù một chữ số — khi đó $\pi_0$ rò vào đường không đọc tín hiệu, là **lỗi** |
| π2 | Hệ quả của π1: **kết luận của #13/#17 (`SSG-up` ở 0,75) không thể đổi theo $\pi_0$** | — (suy ra từ π1) |
| π3 | Chính sách đọc tín hiệu (`Sentinel`, `SentinelW`, `SSG-G`, B5) **có dịch chuyển**, nhưng chính sách tốt nhất của mỗi ô (share × Δ) **không đổi ở ít nhất 3/4 ô** | chính sách tốt nhất đổi ở ≥ 2 ô |
| π4 | Ở 0,3205, **không ô nào vượt 15%** ở bất kỳ $\pi_0$ nào — kết quả rỗng không phải do $\pi_0$ | có $\pi_0$ nào đó làm một ô vượt 15% |

## 4. Nếu dự đoán sai

- π1 sai → dừng, tìm đường rò, không báo số.
- π3 hoặc π4 sai → báo đúng như đo, và ghi vào README như một **giới hạn**: kết luận
  về chính sách đọc tín hiệu phụ thuộc $\pi_0$ và $\pi_0$ được suy dẫn từ 20 episode.
