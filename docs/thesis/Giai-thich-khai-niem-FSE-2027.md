# Giải thích các khái niệm & thuật ngữ dùng trong Portfolio FSE-2027 (RAISE Lab)

Tài liệu này giải thích các khái niệm, ký hiệu và thuật ngữ xuất hiện lặp lại trong hai bản phân tích (`Phan-tich-FSE-2027-Portfolio.md` và `Phan-tich-chi-tiet-15-de-tai-FSE-2027.md`), để đọc nhanh mà không cần đoán nghĩa. Ví dụ dòng thông tin đầu mỗi đề tài:

> **Mã đề xuất nội bộ:** P9 · **Độ dài:** 8 trang nội dung chính / 9 trang tổng · **Số RQ:** 4 · **Smoke test:** HOLDS (4/4)

Các khái niệm bên dưới được nhóm theo thứ tự xuất hiện trong dòng này, sau đó mở rộng ra toàn bộ các khái niệm khác của portfolio.

---

## 1. Mã đề xuất nội bộ (ví dụ: P9)

Mỗi trong 15 đề xuất nghiên cứu ban đầu được lab đánh số nội bộ theo dạng `P1`–`P15` (thứ tự soạn thảo/nộp đề xuất, không phản ánh chất lượng hay độ ưu tiên). Khi tổng hợp thành portfolio, TS. Bách xếp hạng lại toàn bộ 15 đề xuất theo mức độ ưu tiên/khả thi và gán mã mới dạng `FSE-2027-01` đến `FSE-2027-15` — đây là mã dùng xuyên suốt hai bản phân tích để tham chiếu và xếp hạng.

- **Mã nội bộ (Pxx):** thứ tự nộp ban đầu, chỉ có ý nghĩa lịch sử/hành chính.
- **Mã ranking (FSE-2027-xx):** thứ tự ưu tiên trong portfolio — số càng nhỏ càng được xếp hạng cao (không nhất thiất là dễ hơn, mà là được đánh giá tổng thể tốt hơn về mức độ chín muồi + tính khả thi + đóng góp).

Hai mã này không tương ứng 1–1 theo thứ tự số học (ví dụ P9 có thể ứng với FSE-2027-13, không phải FSE-2027-09) — luôn tra theo bảng ánh xạ trong phần Overview của mỗi đề tài, không suy đoán từ số.

## 2. Độ dài (X trang nội dung chính / Y trang tổng)

Mỗi đề xuất là một tài liệu PDF/Word độc lập. Con số này mô tả độ dài của chính tài liệu đề xuất đó (proposal document), không phải độ dài luận văn tương lai:

- **Trang nội dung chính:** số trang chứa phần lập luận khoa học — Problem, Gap, cơ chế (mechanisms), định lý (theorems), câu hỏi nghiên cứu (RQ), thiết kế thực nghiệm.
- **Trang tổng:** trang nội dung chính + các phần phụ lục (bảng baseline chi tiết, chứng minh định lý đầy đủ, danh sách benchmark, smoke-test log, bảng ngân sách chi tiết…).

Chênh lệch giữa hai con số cho biết đề xuất đó "nặng phụ lục" tới đâu — ví dụ 8/9 nghĩa là phụ lục rất mỏng (chỉ 1 trang), trong khi một đề xuất khác có thể là 10/22 (phụ lục dài gấp đôi phần chính, thường do bảng baseline hoặc chứng minh định lý dài).

## 3. Số RQ (Research Questions)

RQ là các câu hỏi nghiên cứu hình thức mà đề xuất cam kết trả lời bằng thực nghiệm — mỗi RQ thường đi kèm một **kết quả dự kiến (projected finding)**, tức là con số/kết luận mà nhóm *dự đoán* thực nghiệm đầy đủ sẽ cho ra (không phải kết quả đã có, trừ phần được smoke test xác nhận — xem mục 4). Số RQ dao động 3–5 trong toàn portfolio; nhiều RQ hơn không đồng nghĩa với đề tài khó hơn, mà thường phản ánh việc đề xuất tách nhỏ một câu hỏi lớn thành nhiều câu hỏi con để dễ đánh giá độc lập từng phần (ví dụ: 1 RQ về mức độ phổ biến của vấn đề, 1 RQ về hiệu quả cơ chế, 1 RQ về chi phí, 1 RQ về so sánh với baseline mạnh nhất).

## 4. Smoke test & ký hiệu HOLDS (n/n)

**Smoke test** là một hoặc vài thực nghiệm quy mô nhỏ mà nhóm đã *chạy thật* trước khi nộp đề xuất, nhằm kiểm tra xem giả thuyết cốt lõi (core hypothesis) của cơ chế đề xuất có tín hiệu hợp lý hay không, trước khi đầu tư toàn bộ ngân sách 8–24 tuần vào nghiên cứu đầy đủ. Đây là bằng chứng thực nghiệm *duy nhất* đã tồn tại tại thời điểm đề xuất — mọi con số khác trong đề xuất (headline results, RQ findings) đều là dự kiến, chưa chạy.

Ký hiệu kết luận gồm ba mức:
- **HOLDS** — toàn bộ các kiểm tra (check) trong smoke test đều xác nhận đúng như giả thuyết.
- **PARTIAL** — một số kiểm tra xác nhận, một số không hoặc cho kết quả trái chiều; nhóm phải điều chỉnh phạm vi hoặc phương pháp (xem mục "correction forced by execution" trong bản phân tích chi tiết).
- **FAILS** — giả thuyết cốt lõi không được xác nhận ở quy mô nhỏ (không đề tài nào trong 15 đề tài rơi vào trường hợp này — nếu có, thường coi là dấu hiệu cần thiết kế lại đề xuất).

Số trong ngoặc, ví dụ **(4/4)**, là tỷ lệ **số kiểm tra cụ thể đạt / tổng số kiểm tra đã chạy** trong smoke test đó — không phải tỷ lệ phần trăm hay điểm số. "HOLDS (4/4)" nghĩa là smoke test gồm 4 phép kiểm tra riêng biệt (ví dụ: so sánh với từng baseline khác nhau, hoặc kiểm tra từng điều kiện biên khác nhau), và cả 4 đều cho kết quả ủng hộ giả thuyết. Bản phân tích chi tiết liệt kê từng kiểm tra này trong bảng "Bằng chứng smoke test" (cột "Kiểm tra cụ thể" / "Kết quả" / "Chi tiết số liệu").

---

## 5. Các khái niệm khác dùng trong bản phân tích chi tiết

### Vấn đề (Problem) & Khoảng trống (Gap)
- **Problem:** hiện tượng/lỗi cụ thể trong hệ thống coding-agent nhiều bước mà đề xuất muốn giải quyết (ví dụ: agent dùng lại một "bài học" đã lỗi thời từ memory).
- **Gap:** lý do vì sao các phương pháp/hệ thống hiện có (baseline mạnh nhất hiện tại) *không* giải quyết được Problem — thường là vì chúng giải một bài toán liền kề nhưng không giải đúng bài toán cốt lõi.

### Cơ chế (mechanism) vs. Định lý (theorem)
- **Mechanism:** một thành phần kỹ thuật cụ thể mà đề xuất *xây dựng* (thuật toán, giao thức, cấu trúc dữ liệu, quy tắc quyết định).
- **Theorem:** một khẳng định *có thể chứng minh được bằng toán học* về hành vi của (các) cơ chế đó (ví dụ: cận trên của tỷ lệ lỗi, điều kiện hội tụ, tính an toàn trong mọi trường hợp). Không phải đề tài nào cũng có theorem — các đề tài thiên hệ thống có thể chỉ có mechanism.

### Benchmark mới / Baseline SOTA
- **Benchmark mới:** bộ dữ liệu đánh giá do chính nhóm xây dựng riêng cho đề tài này (vì chưa có bộ dữ liệu công khai nào đo đúng hiện tượng cần đo).
- **Dữ liệu nền / hạ tầng thực nghiệm:** nguồn dữ liệu gốc (repository, benchmark có sẵn) mà benchmark mới được xây dựng dựa trên, cùng harness thực thi dùng chung cho toàn portfolio (**OpenHands** — một framework mã nguồn mở để chạy coding agent tự động trên các tác vụ sửa lỗi).
- **Baseline SOTA đối chứng:** danh sách các phương pháp hiện có (state-of-the-art) mà hệ thống đề xuất phải so sánh và vượt qua; thường đánh số **B1, B2, B3...** theo mức độ đơn giản đến phức tạp — B1 thường là "không làm gì" hoặc phương pháp ngây thơ nhất, các B ở giữa là hệ thống SOTA thực sự, B cuối đôi khi là "oracle" (biết trước đáp án — dùng làm cận trên lý thuyết, không phải đối thủ cạnh tranh thực sự).
- **SWE-bench format:** định dạng dữ liệu chuẩn trong nghiên cứu coding agent (bug report + repository + patch đúng + bộ test để chấm), do benchmark SWE-bench phổ biến hóa — toàn bộ portfolio dùng chung quy ước này để đảm bảo có thể so sánh chéo.

### Kết quả đầu bài (Headline results)
Là các con số *dự kiến* (chưa chạy thật, trừ phần trùng với smoke test) mà nhóm cam kết sẽ đạt được nếu giả thuyết đúng — dùng để đánh giá "đề tài có đáng làm hay không" trước khi đầu tư công sức, và sau này dùng làm tiêu chí nghiệm thu khi luận văn hoàn thành.

### Go/no-go gate
Một ngưỡng số cụ thể được định nghĩa *trước khi* chạy thực nghiệm đầy đủ, dùng để quyết định khách quan xem đề tài có "thành công" hay cần thu hẹp phạm vi/điều chỉnh hướng đi. Ví dụ: "nếu margin so với baseline mạnh nhất dưới 2 điểm phần trăm → sáp nhập vào đề tài khác thay vì công bố độc lập." Gate giúp tránh tình trạng tự diễn giải kết quả có lợi cho mình sau khi đã thấy số liệu (p-hacking / hindsight bias).

### Kế hoạch, ngân sách & rủi ro (Plan & Budget)
- **Thời lượng dự kiến:** số tuần ước tính để hoàn thành đề tài (8–24 tuần tùy đề tài).
- **Ngân sách inference:** chi phí gọi API LLM hoặc GPU-giờ cho backend mã nguồn mở, ước tính bằng USD hoặc GPU-giờ — đây thường là chi phí chiếm phần lớn ngân sách của các đề tài liên quan nhiều đến chạy agent.
- **Compute & lưu trữ:** chi phí hạ tầng khác — CPU-giờ cho container, model checking, lưu trữ artifact/checkpoint (đơn vị TB).
- **Rủi ro & phản ứng (risk & response):** với mỗi rủi ro kỹ thuật có thể xảy ra (ví dụ "cơ chế không tổng quát hóa"), nhóm nêu sẵn phương án ứng phó cụ thể (thu hẹp phạm vi, đổi hướng báo cáo, v.v.) — thể hiện đề xuất đã được suy nghĩ kỹ về khả năng thất bại, không chỉ về kịch bản thành công.

### Wave plan
Portfolio 15 đề tài được nhóm chia thành 3 "wave" (đợt) triển khai theo thời gian — không phải tất cả 15 đề tài được làm cùng lúc:
- **Wave 1:** ưu tiên cao nhất, triển khai ngay, thường là các đề tài rẻ/nền tảng cho các đề tài khác.
- **Wave 2:** triển khai có điều kiện, phụ thuộc vào kết quả của Wave 1 (ví dụ "chỉ làm nếu Wave 1 phát hiện vấn đề X").
- **Wave 3:** các đề tài còn lại, mức độ ưu tiên/phụ thuộc thấp hơn hoặc cần pilot riêng trước khi bắt đầu chính thức.

### "Điều chỉnh do smoke test buộc phải thực hiện" (correction forced by execution)
Một số đề xuất, sau khi chạy smoke test, phát hiện giả thuyết ban đầu cần điều chỉnh (ví dụ: một baseline hóa ra mạnh hơn dự kiến, hoặc một điều kiện biên bị bỏ sót) — trường/dòng này ghi lại chính xác điều gì đã buộc nhóm phải sửa lại phạm vi/cách tiếp cận so với bản thảo gốc, thể hiện tính trung thực khoa học (không giấu kết quả bất lợi).

---

*Tài liệu này là phần bổ sung cho `Phan-tich-FSE-2027-Portfolio.md` và `Phan-tich-chi-tiet-15-de-tai-FSE-2027.md`, dùng để tra cứu nhanh thuật ngữ khi đọc hai bản phân tích đó.*
