# Báo Cáo Đo Đạc & Dự Phóng Chi Phí LLM (Task B)

**Ngày phân tích:** 2026-09-19  
**Mô hình đo thực tế:** `deepseek-v4.1-flash` (nhà cung cấp: `deepseek`)  
**Bảng giá niêm yết (2026-09-15):** Peak: $0.3/1M in (miss), $0.006/1M in (hit), $1.2/1M out. Off-peak: giảm 50% (x0.5).

---

## 1. Dữ liệu Token Đo Thật từ Pilot P2

- **Tổng số lượt gọi wire API:** 136 calls (135 có trường usage).
- **Tổng prompt tokens qua wire:** 9,158,222 (trong đó cached: 7,755,520 -> tỉ lệ hit thực tế: **84.68%**).
- **Tổng completion tokens qua wire:** 1,236,270.
- **Số instance SWE-bench đã đo:** 13/14 instances.
- **Trung bình mỗi task SWE-bench:**
  - `tokens_in`: **689,484** tokens
  - `tokens_out`: **89,360** tokens
  - `cache_hit`: **72.38%**
  - `cost_usd_per_task` (Flash Peak): **$0.1674** (~14.2 cent)
  - `cost_usd_per_task` (Flash Off-peak): **$0.0837** (~7.1 cent)
  - `cost_usd_per_task` (Pro Peak): **$0.6272** (~51.9 cent)
  - `cost_usd_per_task` (Pro Off-peak): **$0.3136** (~26.0 cent)

---

## 2. Bảng Dự Phóng Chi Phí Các Quy Mô Nghiên Cứu (`estimate_cost`)

| Quy mô kịch bản | Số Task ($N \times H \times seeds$) | Flash Peak | Flash Off-peak | Pro Peak (dự phòng) | Pro Off-peak |
|---|---|---|---|---|---|
| **Pilot P2 (14 instances)** | 14 | **$2.34** | **$1.17** | $8.78 | $4.39 |
| **Spike mini (100 wf, H=8)** | 800 | **$133.88** | **$66.94** | $501.74 | $250.87 |
| **Intermediate benchmark (500 wf, H=8)** | 4,000 | **$669.41** | **$334.71** | $2,508.72 | $1,254.36 |
| **Standard benchmark (1,000 wf, H=8)** | 8,000 | **$1,338.82** | **$669.41** | $5,017.43 | $2,508.72 |
| **Full study grid (13,500 wf, H=8)** | 108,000 | **$18,074.08** | **$9,037.04** | $67,735.37 | $33,867.69 |

---

## 3. Khuyến Nghị Phân Bổ Ngân Sách (Gỡ Bỏ Chỗ Trống §1)

1. **Pilot và Spikes (L2/L4):** Với chi phí thực tế ~$0.14/task, trần $100 USD (L2) và $500 USD (L4) hoàn toàn dư giả (cho phép chạy tới >3,500 tasks).
2. **Full Study Grid (13,500 wf $\times$ H=8):**
   - Nếu chạy toàn bộ trên `deepseek-flash` trong giờ off-peak: **$7,690.50 USD** (chỉ chiếm ~15.4% quỹ tài trợ 50k).
   - Nếu chạy peak: **$15,381.00 USD** (~30.8% quỹ).
   - Nếu rơi vào nhánh Question 10 (chuyển sang `pro`): Off-peak tốn **$28,023.51 USD**, Peak tốn **$56,047.02 USD**.
3. **Khuyến nghị trần full study cấp tại Cổng G2:**
   - **Trần cấp đề xuất:** **$16,000 USD** (đủ cho 100% full study trên Flash ở giá Peak, hoặc chạy Off-peak kèm 100% reruns).
   - Dự phòng $19,000 USD còn lại giữ nguyên cho nhánh fallback Pro hoặc mở rộng mô hình thứ hai.