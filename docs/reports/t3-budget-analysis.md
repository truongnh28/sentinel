# Báo cáo Phân tích Ràng buộc Ngân sách: Cứng vs Kì vọng (Task T3)

**Ngày thực hiện:** 19/09/2026  
**Công cụ đo:** Mô phỏng Monte Carlo 1.000 lần trên nghiệm Simplex LP (`smoke_repro.p_minimax`).  
**Dữ liệu xuất:** `auditgame/spikes/t3-budget-gap.json`  
**Cơ sở lý luận:** Phụ lục F.5, `docs/thesis/eval/PLAN-Sau-Buoc-1.3.md` (Task T3).

---

## 1. Đặt vấn đề & Khác biệt Cấu trúc

Trong toàn bộ lý thuyết trò chơi Stackelberg (Theorem 4, `smoke_repro.p_minimax`):
- Ngân sách được ràng buộc theo **giá trị kỳ vọng**:
  $$\sum_k \kappa_k \sum_t u[k, t] + \kappa_{\text{commit}} \sum_t v[t] \le B$$
- Trong khi đó, trong môi trường thực thi (`policies.Policy.can`, runtime benchmark):
  $$\text{spent} + \text{cost}(a) \le B \quad (\text{Ràng buộc cứng từng ván chơi})$$

Hai cơ chế này **không tương đương nhau**:
Khi một chính sách ngẫu nhiên hoá rút hành động độc lập tại mỗi bước với xác suất $u[k, t]$, tổng chi phí thực tế là một biến ngẫu nhiên.
1. Khi chi phí thực tế vượt quá $B$ ở các bước cuối, ràng buộc cứng sẽ **chặn đứng (truncate)** các lượt kiểm toán tiếp theo.
2. Khi chi phí thực tế rơi vào nhánh dưới $B$, một phần ngân sách bị **bỏ phí (unspent)**.

Câu hỏi của Task T3: **Bảng 2 trong đề cương (nghiệm LP) đang lạc quan hơn thực tế bao nhiêu phần trăm?**

---

## 2. Kết quả Đo lường Thực nghiệm (1.000 Lượt Monte Carlo)

Cấu hình khảo sát: $K = 4$ carriers, $H = 8$ tasks, $B = 17.95$, $\Delta = 2$, $\kappa = [2.0, 2.0, 2.0, 2.0]$, $\kappa_{\text{commit}} = 4.10$.

| Đại lượng | Nghiệm LP (Kỳ vọng) | Thực thi Cứng (Monte Carlo) | Độ lệch (Gap) |
|---|:---:|:---:|:---:|
| **Độ phủ trung bình ($u$)** | **0.2805** | **0.2432** | **-13.29%** |
| **Chi tiêu trung bình** | **17.95** (100%) | **15.56** (86.7%) | **-2.39 đơn vị** |
| **Tỷ lệ lãng phí ngân sách** | 0% | 13.3% | — |

### Phân tích Độ lệch:
1. **Mức độ lạc quan của Bảng 2:**
   - Nghiệm LP giả định có thể mua các phần lẻ của kiểm toán và trung bình hoá tuyệt đối trên kỳ vọng.
   - Khi chạy thực tế có chặn cứng, độ phủ trung bình giảm từ **0.2805 xuống 0.2432**, tức **giảm 13.29%**.
   - Do đó, mọi con số độ lợi trong Bảng 2 của đề cương mang tính **lạc quan khoảng 13%** do hiệu ứng Knapsack ngẫu nhiên.
2. **Nguyên nhân cốt lõi:**
   - Do không thể bù trừ ngân sách giữa các ván chơi độc lập, hệ thống chỉ tiêu được trung bình **15.56 / 17.95** ngân sách. 13.3% ngân sách còn lại bị kẹt dưới dạng "tiền lẻ" không đủ mua thêm một lượt kiểm toán nguyên vẹn ở cuối quy trình.

---

## 3. Khuyến nghị Kỹ thuật cho Hiện thực Policy (Task T4)

Khi hiện thực `MinimaxLP` vào `policies.REGISTRY`:
1. **Phương án khuyến nghị:** Giữ nguyên quy tắc lấy mẫu độc lập theo marginal $u[k, t]$ kết hợp kiểm tra `self.can(cost)`.
2. **Khai báo tính lạc quan:** Trong báo cáo và luận văn, công bố rõ ràng con số suy giảm **13.29%** giữa nghiệm LP lý thuyết và chính sách ngẫu nhiên hoá chạy thực tế, biến một "mối lo ngại tiềm ẩn" thành một **kết quả định lượng rõ ràng**.
