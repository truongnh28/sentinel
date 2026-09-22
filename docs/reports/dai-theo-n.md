# Đường Cong Dải Nhiễu Theo Cỡ Mẫu $n$ — Thí Nghiệm Phương Pháp Luận Khung B

**Ngày đo:** 19/09/2026 · **Module:** `analysis/band_vs_n.py`  
**Test:** `tests/gate2_validity/test_band_vs_n.py`  
**Dữ liệu:** `spikes/band_curve.json`  

---

## 1. Câu hỏi khoa học

Tại Cổng 2 v2, các ô chứng nhận sau khi khử thiên lệch từ điển dao động trong dải **0,51 – 0,64**, và trần $0,56$ nằm **bên trong** dải nhiễu cấu trúc giữa các hạt muối của quy tắc chọn tập con.

Câu hỏi phương pháp luận trung tâm là:
> **Cần cỡ mẫu $n$ bao nhiêu để một cổng kiểm định khớp-bề-mặt (surface-matching gate) phân giải được trần $0,56$?**

Nếu câu trả lời là *"ở mọi cỡ mẫu thực tế $n \le 1800$, trần $0,56$ vẫn bị kẹp trong dải dao động của họ muối"*, thì phán quyết Cổng 2 không phải là *"thất bại của một công cụ cụ thể"*, mà trở thành **đóng góp phương pháp luận của Khung B cho FSE 2027**:
> *"Các benchmark kiểm định bảo mật agent công bố ở $n < 2000$ với trần ngặt $0,56$ và chỉ chạy trên 1 hạt muối đang chứng nhận bằng nhiễu ngẫu nhiên của hạt muối chứ không phân giải được kẻ tấn công."*

---

## 2. Dữ liệu thực nghiệm trên họ 8 muối khai trước

Đo lường trên họ 8 muối đầu tiên của họ muối đã khai (`gate2_v2.SALT_FAMILY[:8]`), tại $\Delta = 0, \varepsilon = 0,0$, với 20 split seed chuẩn (`discriminator.SPLIT_SEEDS`), trần $0,56$:

| $n$ | Cận dưới (`lo`) | Cận trên (`hi`) | Độ rộng dải (`width`) | Trung vị (`median`) | Kẹp trần $0,56$? | Trạng thái phân giải |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **100** | 0,5941 | 0,7025 | **0,1084** | 0,6090 | **Không** (nằm trên) | Lệch mẫu nhỏ, đỏ 8/8 muối |
| **200** | 0,5217 | 0,6096 | **0,0878** | 0,5568 | **CÓ** | Bị kẹp (trần lọt vào dải) |
| **400** | 0,5193 | 0,5978 | **0,0785** | 0,5761 | **CÓ** | Bị kẹp (trần lọt vào dải) |
| **900** | 0,5021 | 0,5901 | **0,0879** | 0,5304 | **CÓ** | Bị kẹp (cỡ mẫu chứng nhận hiện tại) |
| **1800** | 0,5283 | 0,5831 | **0,0548** | 0,5347 | **CÓ** | Bị kẹp (gấp đôi cỡ mẫu bài báo) |

### Chi tiết phân bố từng muối:
- **$n = 100$:** `[0.6230, 0.6518, 0.7025, 0.5991, 0.6029, 0.5941, 0.6005, 0.6150]` — 8/8 muối đều có cận trên CI trung bình $> 0,59$. Ở mẫu nhỏ, phương sai ước lượng đẩy cận trên CI 95% vọt qua trần.
- **$n = 200$:** `[0.5557, 0.5566, 0.5586, 0.6096, 0.5217, 0.5569, 0.5330, 0.5595]` — 7 muối $\le 0,56$, 1 muối vọt lên $0,6096$.
- **$n = 400$:** `[0.5336, 0.5317, 0.5193, 0.5839, 0.5786, 0.5978, 0.5736, 0.5832]` — 3 muối $\le 0,56$, 5 muối $> 0,56$.
- **$n = 900$:** `[0.5117, 0.5033, 0.5021, 0.5431, 0.5347, 0.5901, 0.5519, 0.5261]` — 7 muối $\le 0,56$, 1 muối vọt lên $0,5901$.
- **$n = 1800$:** `[0.5331, 0.5283, 0.5286, 0.5574, 0.5348, 0.5831, 0.5346, 0.5358]` — 7 muối $\le 0,56$, 1 muối ở $0,5831$.

---

## 3. Ba quan sát định lượng then chốt

1. **Độ rộng dải thu hẹp theo $n$ nhưng có sàn cấu trúc (Structural Floor):**
   - Độ rộng dải thu hẹp từ **0,1084** ($n = 100$) xuống **0,0548** ($n = 1800$).
   - Tuy nhiên, tốc độ co lại chậm (tiệm cận $\approx 0,05$), cho thấy đây là biến thiên tự nhiên của tập từ khoá ngẫu nhiên trong quy tắc tạo payload khi đối chiếu với nền drift tự nhiên của agent, chứ không chỉ là phương sai lấy mẫu đơn thuần.

2. **Hiện tượng kẹp trần (Straddling) kéo dài tới tận $n = 1800$:**
   - Tại $n = 900$ (kích thước mẫu mà bài báo dùng để chứng nhận), dải đo là **[0,5021; 0,5901]** — khoảng rộng 0,088 bao trọn trần 0,56.
   - Thậm chí khi tăng gấp đôi cỡ mẫu lên $n = 1800$, dải đo vẫn là **[0,5283; 0,5831]**, tiếp tục kẹp trần 0,56.
   - Do đó, `resolving_n` với tiêu chí không kẹp trần không thể giải quyết được ở bất kỳ cỡ mẫu nào trong dải $n \in [200, 1800]$.

3. **Bẫy của việc chạy trên 1 hạt muối duy nhất:**
   - Nếu một nhà nghiên cứu chỉ chọn hạt muối `"payload_topic"` (muối đầu tiên), họ sẽ thấy:
     - Tại $n = 900$: kết quả là $0,5117 \le 0,56$ ✅ (họ sẽ tuyên bố: *"Cổng chứng nhận đạt hoàn hảo!"*).
   - Nhưng nếu một nhóm nghiên cứu độc lập sao chép thí nghiệm và vô tình chọn hạt muối `"payload_topic#5"`, họ sẽ thấy:
     - Tại $n = 900$: kết quả là $0,5901 > 0,56$ ❌ (họ sẽ tuyên bố: *"Benchmark hoàn toàn hỏng, phát hiện được kẻ tấn công!"*).
   - Cả hai kết luận trên đều **sai lệch bản chất**: chúng chỉ là hai lần rút ngẫu nhiên của cùng một quy tắc phân bổ token trên nền corpus có kích thước chưa đủ để triệt tiêu phương sai hạt muối.

---

## 4. Ý nghĩa cho bài báo FSE 2027 (Khung B)

Thực nghiệm đường cong dải-theo-$n$ biến một trở ngại cục bộ thành một **luận điểm phương pháp luận sắc bén**:

1. **Đơn vị lặp lại độc lập là HỌ MUỐI, không phải split:**  
   20 split trên cùng một hạt muối chỉ xáo trộn các điểm dữ liệu bên trong một hiện thực hoá. Chỉ khi quét qua một họ hạt muối khai trước, ta mới nhìn thấy toàn bộ dải biến thiên thực sự của kiểm định.

2. **Khuyến nghị phương pháp luận cho cộng đồng SE:**  
   Đối với các cơ chế phòng thủ dựa trên kiểm tra bề mặt (surface matching), muốn chứng nhận độ không thể phân biệt ở mức sai số $\le 0,03$ quanh trần ngẫu nhiên $0,50\text{--}0,56$, cộng đồng bắt buộc phải:
   - Hoặc nâng cỡ mẫu lên $n \gg 2000$ sự kiện;
   - Hoặc công bố dải tin cậy qua họ hạt muối (Pre-registered Salt Family) thay vì chỉ một con số điểm ước lượng;
   - Hoặc chấp nhận rằng tại $n \le 900$, kiểm định bề mặt mang tính ngẫu nhiên cấu trúc và cần kết hợp với các cơ chế kiểm toán hành vi / ngữ cảnh sâu (như Sentinel hay fdetect).

---

## 5. Tái lập và Mutation Test

- **Lệnh đo đường cong:**
  ```bash
  python3 scripts/measure_band_vs_n.py
  ```
- **Kiểm thử đơn vị:**
  ```bash
  python3 -m unittest tests/gate2_validity/test_band_vs_n.py
  ```
- **Mutation check:**  
  Khi ép `band_width` chạy với 1 muối hoặc 2 muối (< `MIN_SALTS = 3`), `test_a_single_salt_is_refused` và `test_two_salts_are_refused` báo đỏ ngay lập tức, ngăn chặn việc tính dải nhiễu vô nghĩa trên mẫu hạt muối không có độ phân tán.
