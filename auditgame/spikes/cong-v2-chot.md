# Chốt Cổng 2 v2 — Hai Mục Quyết Định và Một Sửa Lỗi

Ngày: 18/09/2026  
Liên quan: `auditgame/spikes/cong-v2.md`, `auditgame/analysis/gate2_v2.py`, `auditgame/attacks.py`

---

## 1. Mục (1): Đặc trưng `topic` — GIỮ, không có gì để quyết

Bỏ `topic` vì nó làm $\Delta=4$ đỏ là **chọn đặc trưng theo kết quả** (outcome-based feature selection), vi phạm phương pháp luận khoa học. `F_match` là tập đặc trưng bề mặt mà người audit có thể quan sát, và `topic` phản ánh trực tiếp nội dung thẻ gợi nhớ mà kẻ tấn công tiêm vào.

Hai sự thật cùng đúng, mỗi cái kèm tên khâu rõ ràng:

1. **Ở khâu Sàng (Screen, $N=80$ sự kiện, trung vị điểm trên 20 split):**  
   Đặc trưng `topic` nằm ở **mức ngẫu nhiên / đoán mò** trên **mọi** hàng $\varepsilon$ và mọi $\Delta$ (dải đo: 0,4558–0,5973). Ở khâu sàng, `topic` không gánh bất kỳ hàng nào.

2. **Ở khâu Chứng nhận (Certify, $N=900$ sự kiện, cận trên CI trung bình trên 20 split):**  
   Ở $\Delta=4$, `topic` **có gánh ô**: trung hoà nó đưa ô từ mức đỏ về dưới trần 0,56. Hai kết quả không mâu thuẫn nhau vì cỡ mẫu và thống kê khác nhau (80 vs 900 sự kiện, trung vị điểm vs cận trên khoảng tin cậy).

=> **Quyết định:** Giữ nguyên `topic` trong `F_match` v2. Không bỏ đặc trưng để làm đẹp kết quả.

---

## 2. Mục (2): Đơn vị lặp lại là MUỐI, không phải split

## Tiêu chí chứng nhận phát biểu trên HỌ MUỐI

20/20 split trên **một** muối **không** là 20 xác nhận độc lập: các split chồng
nhau trên một corpus nhỏ. Bảng 17 muối cho thấy phán quyết **lật theo muối**
(8 xanh / 9 đỏ), nên:

- **Tiêu chí ngoài:** ≥ **80%** muối trong họ đã khai trước phải qua — với 17 muối là **14/17**.
  **Đây là HẰNG SỐ KHAI**, chốt ngày 18/09/2026, **không chỉnh khi thấy 8/17**.
- **Tiêu chí trong:** tiêu chí split hiện tại chỉ là điều kiện **bên trong một muối**.
- Họ muối khai trước, có ngày, vào bản ghi đóng băng.

Khi cổng 2 chỉ đạt 8/17 muối dưới họ khai trước, kết luận không phải là "chúng ta thất bại", mà là:
**Trần 0,56 nằm lọt trong dải nhiễu cấu trúc của benchmark ở cỡ mẫu hiện tại. Cổng phân giải bằng nhiễu muối chứ không phân giải được kẻ tấn công.** Đây là luận điểm phương pháp luận trung tâm của Khung B.

---

## 3. Ghi nhận sửa lỗi: `MatchedAttack` đi vòng qua `payload_content` (Task A1a)

Corpus AUC từng được dựng bằng một đường payload khác với đường game tiêm: `MatchedAttack.payload` tự tính độ dài theo ghi chú agent và bù `_FILLER`, khiến `PAYLOAD_LENGTH` không ràng buộc ô cổng công bố.

Lỗi này đã được sửa tại Task A1a:
- `MatchedAttack.payload` gọi trực tiếp `build.payload_content(topic, ps.marker)`.
- Đo lại bảng screen và certify: `size` không còn mang tải đơn cột ở $\varepsilon \ge 0,2$ (đã sụp từ 0,70–0,88 về mức ngang ngửa nhiễu nền).
- $\Delta=4$ vẫn đỏ ở khâu chứng nhận, phản ánh đúng thực tế đo lường.
