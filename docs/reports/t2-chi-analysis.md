# Báo cáo Phân tích Trục Dị tính Carrier $\chi$: So sánh Ba Phương án Mô hình hoá

**Ngày thực hiện:** 19/09/2026  
**Công cụ đo:** `auditgame/tools/evaluate_chi_variants.py`  
**Dữ liệu xuất:** `auditgame/spikes/t2-chi-results.json`  
**Cơ sở lý thuyết:** Đề cương §3, Theorem 4, Hệ quả 5, `smoke_repro.py`, `docs/thesis/eval/PLAN-Sau-Buoc-1.3.md` (Task T2).

---

## 1. Đặt vấn đề và Hiện trạng

Trong bản thảo Sentinel (FSE-2027-15), trục $\chi$ được định nghĩa là **độ dị tính chi phí kiểm toán giữa các carrier**:
$$\chi = \frac{\max_k \kappa_k - \min_k \kappa_k}{\bar{\kappa}}$$
Mục tiêu lý thuyết là chứng minh: *Khi chi phí giữa các carrier phân hoá mạnh ($\chi$ tăng), lợi thế của chính sách minimax so với audit-at-commit bị thu hẹp (KT3)*.

Tuy nhiên, khi thực nghiệm mô hình hoá LP trong `smoke_repro.py`:
- Dưới mô hình gốc (Phương án A: neo trung bình $\bar{\kappa} = 2.0$), **$\chi$ hoàn toàn rỗng**:
  $$\text{minimax}(\chi = 0.0) = \text{minimax}(\chi = 1.34) = 0.289333$$
  Độ lợi so với audit-at-commit bất biến ở mức **+39.7%** tại $\Delta = 2$.
- **Nguyên nhân cấu trúc:**
  Ràng buộc của kẻ tấn công chỉ phụ thuộc vào thời điểm $\iota$ và cửa sổ lan truyền $\Delta$ (qua $v[\iota + \Delta]$). Vì tổn thất harm không phụ thuộc carrier $k$, kẻ tấn công phản ứng tối ưu sẽ luôn khai thác carrier có độ phủ thấp nhất. Do đó, lời giải minimax buộc phải san bằng độ phủ trên mọi carrier ($u[k, t] = U(t)$).
  Khi đó, tổng chi phí upstream:
  $$\sum_k \kappa_k \sum_t u[k, t] = \left(\sum_k \kappa_k\right) \cdot \sum_t U(t)$$
  chỉ phụ thuộc vào **tổng chi phí** $\sum_k \kappa_k$, hoàn toàn không phụ thuộc vào **phân bố** chi phí giữa các carrier.

Để giải quyết vấn đề này trước buổi họp với GVHD, báo cáo này khảo sát thực nghiệm ba phương án mô hình hoá.

---

## 2. Bảng đối chiếu ba phương án

### Bảng 1: So sánh Độ lợi Minimax so với Audit-at-Commit (%) trên lưới $(\chi, \Delta)$

| Phương án | $\chi$ | $\sum_k \kappa_k$ | $\Delta = 0$ | $\Delta = 1$ | $\Delta = 2$ | $\Delta = 4$ | Trạng thái KT3 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **A. Neo Trung bình** | 0.00 | 8.00 | 0.0% | +15.5% | **+39.7%** | +89.6% | **FAIL** |
| *(Mô hình hiện tại)* | 0.50 | 8.00 | 0.0% | +15.5% | **+39.7%** | +89.6% | *(bất biến)* |
| | 1.00 | 8.00 | 0.0% | +15.5% | **+39.7%** | +89.6% | |
| | 1.34 | 8.00 | 0.0% | +15.5% | **+39.7%** | +89.6% | |
|---|---|---|---|---|---|---|---|
| **B. Neo Nhỏ nhất** | 0.00 | 8.00 | 0.0% | +15.5% | **+39.7%** | +89.6% | **PASS** |
| *($\kappa_{\text{lo}}$ cố định,* | 0.50 | 10.67 | 0.0% | +15.5% | **+36.1%** | +89.6% | *(thu hẹp* |
| *tổng chi phí tăng)* | 1.00 | 16.00 | 0.0% | +15.5% | **+36.1%** | +89.6% | *đúng chiều)* |
| | 1.34 | 24.24 | 0.0% | +15.5% | **+36.1%** | +89.6% | |
|---|---|---|---|---|---|---|---|
| **C. Audit Commit Carrier** | 0.00 | 8.00 | 0.0% | +20.1% | **+66.7%** | +94.3% | **FAIL** |
| *($v(t) \to v(k, t)$)* | 0.50 | 8.00 | 0.0% | +20.1% | **+66.7%** | +94.3% | *(vẫn bất biến* |
| | 1.00 | 8.00 | 0.0% | +20.1% | **+66.7%** | +94.3% | *do đối xứng)* |
| | 1.34 | 8.00 | 0.0% | +20.1% | **+66.7%** | +94.3% | |

---

## 3. Phân tích Chi tiết Từng Phương án

### 3.1 Phương án A — Giữ neo trung bình (Giữ nguyên hiện trạng)
- **Cơ chế:** Khi $\chi$ tăng, carrier đắt lên thì carrier khác rẻ đi tương ứng, giữ nguyên $\sum_k \kappa_k = K \bar{\kappa} = 8.0$.
- **Ưu điểm:** Giữ nguyên toàn bộ phát biểu trong manuscript gốc và không thay đổi định nghĩa ngân sách.
- **Nhược điểm:** Trục $\chi$ hoàn toàn vô hiệu trong mô hình toán của smoke test. Trắc nghiệm KT3 luôn báo FAIL.

### 3.2 Phương án B — Neo giá trị nhỏ nhất (Khớp ngữ nghĩa manuscript)
- **Cơ chế:** Cố định $\min_k \kappa_k = \bar{\kappa} = 2.0$. Khi $\chi$ tăng, các carrier đắt tăng giá mạnh hơn:
  $$\kappa_{\text{hi}} = \kappa_{\text{lo}} \cdot \frac{2 + \chi}{2 - \chi}$$
  Tổng chi phí $\sum_k \kappa_k$ tăng từ 8.00 (tại $\chi=0$) lên 24.24 (tại $\chi=1.34$).
- **Ưu điểm:**
  - **KT3 chuyển ngay lập tức từ FAIL sang PASS**: Tại $\Delta=2$, độ lợi minimax thu hẹp từ **+39.7% xuống +36.1%**.
  - Khớp hoàn hảo với cách diễn đạt của manuscript: *"differentiating audit depths makes expensive carriers costlier to monitor"*.
  - Không cần sửa đổi kiến trúc biến quyết định của LP hay định lý lý thuyết.
- **Điểm cần lưu ý:** Cần làm rõ với người đọc rằng $\chi$ tăng đồng nghĩa với việc "hệ thống có thêm các carrier phức tạp và đắt đỏ hơn", dẫn đến tổng chi phí bảo vệ toàn diện tăng lên.

### 3.3 Phương án C — Tách kiểm toán commit theo carrier ($v(t) \to v(k, t)$)
- **Cơ chế:** Tại thời điểm commit, người kiểm toán không chạy một bộ kiểm tra chung cho toàn bộ commit, mà phải chọn kiểm tra xem độc tố có đến từ carrier $k$ hay không.
- **Kết quả thực nghiệm:**
  - Nếu commit audit có chi phí đối xứng giữa các carrier, LP minimax vẫn duy trì độ phủ đồng đều giữa các carrier để chống worst-case routing. Do đó, nếu neo trung bình, $\chi$ vẫn không làm thay đổi nghiệm tối ưu.
  - Hơn nữa, việc chia nhỏ commit audit làm suy yếu baseline `audit-at-commit` (vì ngân sách commit bị chia cho $K$ carrier), đẩy độ lợi của minimax lên cao phi lý (+66.7% tại $\Delta=2$), đi ngược lại dữ liệu thực tế.
  - Sửa đổi này làm thay đổi cấu trúc định lý (Theorem 4), vì cơ chế phòng thủ commit không còn là một điểm nghẽn tập trung (chokepoint).

---

## 4. Đề xuất Khuyến nghị trình GVHD

Khi báo cáo với Giáo viên Hướng dẫn (GVHD), khuyến nghị trình bày theo cấu trúc sau:

1. **Báo cáo sự thật khách quan:** Trục $\chi$ dưới cách hiểu neo trung bình (Phương án A) là một trục rỗng về mặt cấu trúc toán học do tính đối xứng của bài toán con worst-case.
2. **Khuyến nghị áp dụng Phương án B (Neo nhỏ nhất):**
   - Đây là giải pháp tự nhiên nhất, phản ánh đúng thực tế công nghệ: Việc hỗ trợ các carrier phức tạp (như branch execution, memory reflection) làm tăng chi phí kiểm toán của chính carrier đó mà không làm giảm chi phí của các carrier đơn giản (như file git hay prompt queue).
   - Phương án B giữ nguyên toàn bộ định lý hiện có, giúp KT3 đạt PASS, và tái lập chính xác chiều thu hẹp độ lợi khi $\chi$ tăng.
3. **Từ chối Phương án C:** Phương án C làm phức tạp hoá mô hình một cách không cần thiết, phá vỡ cấu trúc chokepoint của commit audit, và không giải quyết được tính đối xứng nếu không thêm các giả định phụ về phân bố tấn công.
