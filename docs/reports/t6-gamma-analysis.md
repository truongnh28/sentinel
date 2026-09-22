# Báo cáo Đo lường Thực nghiệm Điểm làm việc của Detector: Khảo sát $(\psi, \phi, \gamma, d')$ và Đối chiếu Ngưỡng Hoà vốn $d'^\star$

**Ngày thực hiện:** 19/09/2026  
**Công cụ đo:** `auditgame/tools/measure_gamma.py`  
**Dữ liệu xuất:** `auditgame/spikes/gamma-empirical.json`  
**Tập dữ liệu:** Matched Case-Control Corpus (`analysis/benign_corpus.py`), $N_{\text{screen}} = 80$ events, $N_{\text{neg}} = 320$ items benign thật từ SWE-bench instances, bộ đặc trưng bề mặt $F_{\text{match}}$ (`size`, `depth`, `recency`, `derived`, `topic`).  
**Cơ sở lý luận:** Đề cương §1.3 (Bước 3), `docs/thesis/eval/PLAN-Sau-Buoc-1.3.md` (Task T6), `dprime-sweep.md` (T1).

---

## 1. Đặt vấn đề và Mục tiêu (Task T6)

Trong bản thảo Sentinel (FSE-2027-15 §8), chất lượng của detector được giả định thông qua **ba giá trị khai báo**:
- `weak`: $(\psi = 0.75, \phi = 0.20) \implies d' = 1.516, \gamma = 0.55$.
- `mid`: $(\psi = 0.85, \phi = 0.12) \implies d' = 2.211, \gamma = 0.73$.
- `strong`: $(\psi = 0.92, \phi = 0.06) \implies d' = 2.960, \gamma = 0.86$.

Tại các giá trị này, detector được gán sẵn độ phân tách rất cao ($d' \in [1.5, 3.0]$). Tuy nhiên, **chưa từng có phép đo nào đối chiếu các mức khai báo này với một bộ phân loại thực nghiệm trên tập dữ liệu có nhãn**.

Mục tiêu của Task T6:
1. Xác định chính xác mối quan hệ giữa AUC thực nghiệm và độ phân tách $d'$, độ mở rộng biên $\gamma = \psi - \phi$.
2. Đo đạc thực nghiệm $(\psi, \phi, \gamma, d')$ trên corpus benign thật đối sánh với payload ngụy trang theo ngân sách xáo trộn $\epsilon$.
3. **Đối chiếu quyết định:** So sánh $d'$ đo được với ngưỡng hoà vốn $d'^\star$ đã đo ở Task T1 (§1.3 Bước 4).

---

## 2. Kết quả Đo lường Thực nghiệm

### 2.1 Bảng 1: Ba mức khai báo trong Bản thảo (Lý thuyết)

| Thiết lập | $\psi$ (TPR) | $\phi$ (FPR) | $\gamma = \psi - \phi$ (Margin) | $d'$ (Separability) | $\tau_{\text{det}}$ | AUC tương đương |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **weak** | 0.7500 | 0.2000 | 0.5500 | 1.5161 | 0.8416 | 0.8582 |
| **mid** | 0.8500 | 0.1200 | 0.7300 | 2.2114 | 1.1750 | 0.9411 |
| **strong** | 0.9200 | 0.0600 | 0.8600 | 2.9598 | 1.5548 | 0.9818 |

---

### 2.2 Bảng 2: Kết quả Đo Thực nghiệm trên Corpus Benign Thật ($F_{\text{match}}$)

*(Đo trên 10 train/test splits độc lập, đánh giá tại ngưỡng tham chiếu $\tau_{\text{det}} = 1.175$ của mức `mid`)*

| $\Delta$ | $\epsilon$ (Ngân sách lỗi) | AUC Mean | $d'$ đo được | $\psi$ | $\phi$ | $\gamma$ | $d'^\star$ Hoà vốn (T1) | Vượt ngưỡng hoà vốn? |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0** | 0.0 (khớp tuyệt đối) | 0.4908 | **0.0000** | 0.120 | 0.120 | 0.000 | *null (không có)* | ❌ **KHÔNG** |
| 0 | 0.2 | 0.4723 | **0.0000** | 0.120 | 0.120 | 0.000 | *null* | ❌ **KHÔNG** |
| 0 | 0.4 | 0.4654 | **0.0000** | 0.120 | 0.120 | 0.000 | *null* | ❌ **KHÔNG** |
| 0 | 0.7 | 1.0000 | 5.2595 | 1.000 | 0.120 | 0.880 | *null* | ❌ **KHÔNG** |
|---|---|---|---|---|---|---|---|---|
| **2** | 0.0 (khớp tuyệt đối) | 0.5436 | **0.1550** | 0.154 | 0.120 | 0.034 | **2.85** | ❌ **KHÔNG** |
| 2 | 0.2 | 0.5238 | **0.0843** | 0.138 | 0.120 | 0.018 | **2.85** | ❌ **KHÔNG** |
| 2 | 0.4 | 0.4860 | **0.0000** | 0.120 | 0.120 | 0.000 | **2.85** | ❌ **KHÔNG** |
| 2 | 0.7 | 1.0000 | 5.2595 | 1.000 | 0.120 | 0.880 | **2.85** | ✅ **CÓ** |
|---|---|---|---|---|---|---|---|---|
| **4** | 0.0 (khớp tuyệt đối) | 0.5808 | **0.2884** | 0.188 | 0.120 | 0.068 | **0.95** | ❌ **KHÔNG** |
| 4 | 0.2 | 0.5797 | **0.2844** | 0.187 | 0.120 | 0.067 | **0.95** | ❌ **KHÔNG** |
| 4 | 0.4 | 0.6386 | **0.5017** | 0.250 | 0.120 | 0.130 | **0.95** | ❌ **KHÔNG** |
| 4 | 0.7 | 1.0000 | 5.2595 | 1.000 | 0.120 | 0.880 | **0.95** | ✅ **CÓ** |

---

## 3. Phát hiện Khoa học Quyết định (Core Insight)

Đúng như dự báo tại **`docs/thesis/eval/PLAN-Sau-Buoc-1.3.md` (Mục 3.4)**:  
*"Nếu $d'$ đo được nằm dưới $d'^\star$ của T1 — đó là phát hiện quan trọng nhất mà đề tài này có thể đưa ra."*

Thực nghiệm cho thấy hai sự thật khách quan:

1. **Bộ phân loại bề mặt ($F_{\text{match}}$) hoàn toàn bất lực trước kẻ tấn công thích ứng:**
   - Khi kẻ tấn công ngụy trang payload để khớp với phân bố ghi chú của agent ($\epsilon \le 0.4$, ngụy trang chiều dài, độ sâu provenance, topic token), AUC thực nghiệm dao động từ **0.46 đến 0.63**.
   - Độ phân tách tương ứng chỉ đạt **$d' \le 0.50$**, và biên phân tách $\gamma = \psi - \phi \le 0.13$.
   - Mức $d' \le 0.50$ này **thấp hơn rất nhiều so với ngưỡng hoà vốn $d'^\star = 2.85$ (tại $\Delta=2$) và $d'^\star = 0.95$ (tại $\Delta=4$)**.
   - **Hệ quả:** Dưới một detector chỉ dựa trên đặc trưng thống kê bề mặt (surface anomaly detector), Sentinel **KHÔNG THỂ HOÀ VỐN** so với audit-at-commit. Lợi thế lý thuyết của Sentinel sụp đổ nếu không có detector ngữ nghĩa mạnh.

2. **Muốn Sentinel phát huy tác dụng, bắt buộc phải dùng Kiểm toán Ngữ nghĩa ($F_{\text{detect}}$):**
   - Ba mức khai báo trong manuscript (`weak` $d'=1.52$, `mid` $d'=2.21$, `strong` $d'=2.96$) **không thể đạt được bằng các bộ lọc bề mặt rẻ tiền**.
   - Để vượt qua ngưỡng hoà vốn $d'^\star = 2.85$, hệ thống phòng thủ bắt buộc phải thực hiện kiểm toán ngữ nghĩa sâu (semantic inspection qua LLM hoặc chuyên gia mã nguồn) để bóc tách tính hợp lệ của mã (`F_DETECT`).
   - Nhưng kiểm toán ngữ nghĩa sâu lại có chi phí đơn vị $\kappa_k$ cao hơn rất nhiều (gấp hàng chục lần so với kiểm tra bề mặt), điều này làm thay đổi bài toán ngân sách $B$ và chi phí tổng thể của hệ thống.

Đây là một luận điểm khoa học có sức nặng cực lớn cho Chương 5 của Luận văn: Nó phân định ranh giới giữa *khả năng tồn tại trên lý thuyết* và *điều kiện cần về công nghệ detector trong thực tế*.
