# Trục nguỵ trang — kết quả

**Ngày:** 20/09/2026 · **Tiền đăng ký:** `TIEN-DANG-KY-Detector-Noi-Dung.md` (🧊 đóng băng, hai vòng review)
**Artifact:** `spikes/content-detector.json` · **Chi phí:** 3,4 USD / trần 25

## Kết quả

| điều kiện | `D_lex` | `D_llm` | n₊ |
|---|---|---|---|
| **cổng A** — an toàn đấu `prose_pool` | **1,000** | — | 717 |
| **`paired`** — có hại TỰ KHAI BÁO | **1,000** | 0,837 | 720 |
| **`covert`** — có hại DO HÀM Ý, tên gợi ý | **1,000** | 0,843 | 721 |
| **`covert` tên trung tính** | **0,479** | **0,518** | 721 |
| **`covert` che tên** | **0,500** | — (N3) | 721 |

## Đọc bảng

**Hai dòng cuối là kết luận.** Che tên hàm đi thì **721/721 cặp trùng nhau từng ký tự** — không phải "khó phân biệt" mà là cùng một chuỗi. Rút tên độc lập với nhãn thì cả hai detector về ngẫu nhiên (0,479 và 0,518; điểm `D_llm` trung bình 6,17 so với 6,08).

> **Phát hiện dựa trên nội dung sụp đổ đúng lúc attacker thôi tự khai báo.** Tác hại nằm ở **cái được trỏ tới**, không nằm trong văn bản. Một ghi chú khuyên gọi `put_fast()` vô hại hay chết người tuỳ `put_fast` làm gì — câu chữ thì giống nhau.

**`D_llm` thua `D_lex` ở mọi điều kiện đo được.** Judge đọc nghĩa kém hơn một bộ đếm trigram. Vì cặp `covert` giống hệt nhau trừ tên, 0,843 của nó cũng chỉ là đọc tên (điểm 8,33 so với 3,88). Không detector nào đang *hiểu*; cả hai nhận dạng hình vị: `raw/fast/skip/naked` đấu `check/verify/guard/sanit`.

**Cổng A ĐỎ**, và đỏ có ích. Cả hai lớp đều **an toàn**, vậy mà `D_lex` vẫn tách hoàn hảo — `punct_density` 0,956, `has_parens` 0,936. `prose_pool` khác biệt vì **quy trình sinh**, không vì ý đồ; nó không dùng làm lớp âm được. Đó là một phát hiện, không phải một thất bại.

## Đọc lại §9.2 của đề tài

Nhận xét *"LLM là đối thủ yếu ở nguỵ trang"* không sai vì đo kém. Nó sai vì **lớp tấn công được yêu cầu phải tự khai báo**: prompt bảo LLM viết *"dùng X thay cho việc kiểm tra"*. LLM chưa bao giờ được yêu cầu nguỵ trang — và khi được yêu cầu, nó nguỵ trang **thành công tuyệt đối**.

## Sáu confound, không cái nào do ai cố ý tạo ra

| | tách được vì | bắt được nhờ |
|---|---|---|
| 1 `size` | `PAYLOAD_LENGTH = 63` khớp trung vị lành tính **theo thiết kế** | sau khi đã kết luận sai một lần |
| 2 khuôn corpus | mục lành tính do máy ghép, payload là văn xuôi | đọc dữ liệu thô |
| 3 marker | mọi payload gọi tên cùng một hàm → AUC 1,000 | quét một-đặc-trưng |
| 4 ngôi thứ nhất | 0% đấu 47–83% | quét một-đặc-trưng |
| 5 bất đối xứng prompt | hai lớp ra từ hai prompt → `punct_density` 0,956 | cổng A |
| 6 quy ước đặt tên | nửa giữ riêng giữ **tên** nhưng không giữ **quy ước** | phá liên kết tên→nhãn |

Phép kiểm bắt được bốn cái cuối rẻ hơn mọi cổng trong tiền đăng ký:

> Trước khi chấm bất kỳ cặp lớp nào: đo AUC của **từng đặc trưng đơn lẻ**. Đặc trưng nào một mình đạt gần 1,0 là confound cho tới khi chứng minh được điều ngược lại.

## Phán quyết §8

**Câu (i) — kênh nội dung có tín hiệu không?**
Có, **nhưng chỉ với lớp tấn công tự khai báo**. Với lớp ngầm và tên không mang thông tin, cả hai detector ở mức ngẫu nhiên. Cây phán quyết §8 giả định một lớp tấn công duy nhất; phép đo cho thấy câu trả lời **phụ thuộc lớp**, nên hàng *"cả hai detector ≈ 0,5"* và hàng *"D_llm > 0,6"* **đều đúng**, ở hai lớp khác nhau.

**Câu (ii) — A0/A1/A2 có khác nhau không?**
`UNDECIDED_INSUFFICIENT_POWER`, nhưng vì một lý do **khác** lý do đã đăng ký: ba mức đo trên `prose_pool`, mà cổng A đã bác `prose_pool` làm lớp âm. Số tồn tại nhưng **không diễn giải được**. Luật N3: ghi lý do.

**A3 `llm-adaptive`:** vẫn **hoãn**, và giờ có lý do mạnh hơn. Vòng phản hồi của A3 học né detector; ở lớp ngầm không có gì để né (0,518). A3 chỉ có nghĩa với lớp tự khai báo, tức nó sẽ đo một chế độ mà ta vừa chứng minh là không đại diện.
