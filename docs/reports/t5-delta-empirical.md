# Báo cáo Đo lường Thực nghiệm Độ trễ Nhân quả $\Delta$ từ Lịch sử Git Thật

**Ngày thực hiện:** 19/09/2026  
**Công cụ đo:** `auditgame/tools/measure_delta.py`  
**Dữ liệu xuất:** `auditgame/spikes/delta-empirical.json`  
**Đối tượng khảo sát (Dogfood):** Kho Obsidian cục bộ của dự án (toàn bộ commit lịch sử).  
**Cơ sở lý luận:** Đề cương §1.3 (Bước 2), `docs/thesis/eval/PLAN-Sau-Buoc-1.3.md` (Task T5).

---

## 1. Đặt vấn đề & Ý nghĩa Phương pháp luận

Trong Đề cương và toàn bộ các nghiên cứu trước đây (kể cả `sweep-loss-v2.md` và `dprime_sweep.py`), $\Delta$ luôn được khảo sát ở các giá trị **tổng hợp (synthetic)**:
$$\Delta \in \{0, 1, 2, 4\}$$
Chưa từng có một công cụ nào đo đạc xem: **Trong một hệ thống phát triển phần mềm với AI agent thật, $\Delta$ bằng bao nhiêu?**

**Ý tưởng đột phá của Task T5:**  
$\Delta$ là **độ trễ nhân quả (causal propagation delay)** giữa thời điểm một chỉ dẫn/trạng thái (instruction, plan, spec, prompt, policy) được ghi nhận và thời điểm sản phẩm hạ nguồn đầu tiên (code, tests, experimental pipelines) chịu tác động được commit.
Do đó, $\Delta$ là một thuộc tính cố hữu của quy trình làm việc (workflow property) và **đo được trên một hệ thống hoàn toàn bình thường, chưa từng bị tấn công**.

---

## 2. Kết quả Đo lường Thực nghiệm trên Kho Lưu trữ

Công cụ `tools/measure_delta.py` đã phân tích toàn bộ chuỗi commit có tác động tới các file chỉ dẫn trạng thái:
- Tập chỉ dẫn/trạng thái: `docs/superpowers/plans/*`, `docs/superpowers/specs/*`, `eval/PLAN*.md`, `.superpowers/*`, `CLAUDE.md`, `GEMINI.md`.
- Tập sản phẩm hạ nguồn: `HCMUT/code/*`, `auditgame/*`, `src/*`, các file mã nguồn `.py`.

### 2.1 Bảng phân bố thống kê của $\Delta$ (Đơn vị: Số commit / task):

| Thống kê | Giá trị thực nghiệm | Ý nghĩa thực tiễn |
|---|:---:|---|
| **Số lần ghi nhận trạng thái ($N$)** | **29** | Số lần cập nhật kế hoạch / đặc tả độc lập |
| **Cực tiểu ($\min \Delta$)** | **0** | Kế hoạch và mã nguồn được commit cùng lúc |
| **Phân vị 25 ($p_{25}$)** | **1.0** | Mã nguồn được hiện thực ngay commit tiếp theo |
| **Trung vị ($p_{50}$)** | **3.0** | Độ trễ lan truyền điển hình là 3 task |
| **Phân vị 75 ($p_{75}$)** | **10.0** | Giai đoạn nghiên cứu / rà soát kéo dài 10 task |
| **Phân vị 90 ($p_{90}$)** | **23.2** | Chuỗi nhiệm vụ phụ phức tạp trước khi merge code |
| **Cực đại ($\max \Delta$)** | **26** | Độ trễ dài nhất ghi nhận trong dự án |
| **Trung bình ($\bar{\Delta}$)** | **6.97** | Trung bình ~7 commit giữa đặc tả và hiện thực |

---

## 3. Đối chiếu với Lý thuyết và Thiết kế Lưới $\Delta$

1. **Khớp với dải khảo sát lý thuyết:**
   - Trung vị thực nghiệm $p_{50} = 3.0$ nằm trọn vẹn ở giữa hai điểm lưới trọng tâm của nghiên cứu: $\Delta = 2$ và $\Delta = 4$.
   - Giá trị $p_{25} = 1.0$ và $\min = 0$ khớp hoàn toàn với hai mốc $\Delta = 1$ và $\Delta = 0$ (nơi mà Hệ quả 5 chỉ ra rằng kiểm toán commit là tối ưu).
2. **Framework Worst-case:**
   - Trong khuôn khổ lý thuyết trò chơi an ninh (Stackelberg worst-case), kẻ tấn công sẽ tìm cách chèn độc tố vào những điểm có $\Delta$ lớn để tối đa hoá cửa sổ lan truyền và khả năng trốn thoát.
   - Số liệu thực tế chỉ ra $p_{75} = 10.0$ và $p_{90} = 23.2$, chứng minh rằng **trong quy trình làm việc thực tế của lập trình viên / agent, các cửa sổ lan truyền lớn ($\Delta \ge 4$) là hoàn toàn có thật và chiếm tỷ trọng đáng kể**, chứ không chỉ dừng lại ở $\Delta = 4$ như lưới mô phỏng.
3. **Đóng góp cho Bước 2 của §1.3:**
   - Giải quyết triệt để ô đánh dấu *"chưa đo"* ở Bước 2 trong §1.3 của Đề cương: Đã có công cụ tự động, có phân bố phân vị từ dữ liệu thật, có trace minh chứng từng commit.
