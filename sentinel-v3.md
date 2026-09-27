# Sentinel v3 — Thiết kế thực nghiệm bám sát draft FSE-2027-15

Sep 27, 2026 · @truong

v3 dựng lại Sentinel và AuditGame-SE theo đúng chữ của draft FSE-2027-15 (bản 07/09/2026). Mọi chỗ lệch chữ đều có bằng chứng. Mọi số dự phóng của draft được kiểm như một giả thuyết đã tiền đăng ký: số có thể không đẹp, nhưng số không có bằng chứng thì không được dùng.

## Phạm vi

v3 là nền của cả bài báo viết lại bám draft lẫn luận văn. Ngày 27/09 đã chốt không nộp FSE ngày 02/10; bài v2 (khung bản đồ regime) chỉ còn là tài liệu tham chiếu.

- **Mục tiêu 1:** tái hiện đủ Table 1, Table 2, Table 3, Figure 3 và §10.2–§10.6 của draft, đúng hàng, đúng cột; cột dự phóng đặt cạnh cột đo.
- **Mục tiêu 2:** kiểm bằng thí nghiệm các kết quả lý thuyết đã chứng minh hoặc sửa trong ghi chú lý thuyết (`theory/`).
- **Mục tiêu 3:** đưa đủ ba lớp attacker của draft vào, kể cả 3 LLM attacker.
- **Mục tiêu 4:** làm lõi tối thiểu trước (mục Lộ trình); phần còn lại xếp sau và khai trước dưới dạng lượt bổ sung có freeze riêng.
- **Không làm:** dùng 57 workflow eval của v2 cho bất kỳ khẳng định xác nhận nào; tập này đã bị chạm hai lần (lượt chính và D35). Chúng vẫn được dùng làm dev cho v3, vì tập eval v3 tách rời hoàn toàn.
- **Không làm:** dùng số v2 làm kết quả v3. Dữ liệu v2 chỉ còn vai trò tập dev và bằng chứng thiết kế.
- **Người quyết:** @truong tự chốt C1–C16 ngày 27/09 (mục "Quyết định đã chốt"); không chờ chữ ký của thầy. Bù lại, mọi quyết định được ghi ngày, lý do và hash ở Cổng 0, trước khi viết code P2, và không sửa sau khi thấy số. Mọi điểm C vẫn cài dạng công tắc.
- **Thời gian:** 3–4 tháng chỉ đủ cho lõi tối thiểu cộng một phần phần sau; toàn bộ phạm vi dài hơn. Chi phí từng khối ghi ở mục Rủi ro.

## Cách chứng minh trung thực

Mỗi con số cuối cùng phải đi qua đủ sáu công cụ dưới đây; thiếu một thì số đó không được in.

| # | Công cụ | Làm gì | Bằng chứng nộp kèm |
| --- | --- | --- | --- |
| T1 | Draft là tài liệu tiền đăng ký | Draft 07/09 tự ghi "no experiment has yet been executed", nên mọi số dự phóng là dự đoán có trước mọi phép đo. Ghim sha256 của PDF | Hash và commit có ngày, trong gói tái lập |
| T2 | Ma trận tuân thủ draft (DCM) | Mỗi câu quy định của draft có một ID (ví dụ `D4.def1`, `D7.pf2048`), nối tới module, test và kết quả; mỗi dòng mang một mức L0/L1/L2 | DCM trong repo; 100% dòng có test |
| T3 | Test đặt tên theo câu draft | Tên test là chính câu nó bảo vệ; có test kịch bản Figure 1 chạy đủ 7 bước t1–t7 | Log test |
| T4 | Bảng điểm dự đoán | Mỗi số dự phóng là một giả thuyết; luật khớp/bác khóa trước lượt chạy | Luật đã hash |
| T5 | Chứng minh hoặc phản ví dụ | Không bỏ định lý nào; kiểm số trên 240 game nhỏ | Chứng minh có người kiểm, không chỉ AI |
| T6 | Một lượt trên tập mới | Tập eval chưa ai chạm, freeze, đối chứng đọc trước, từ chối có lý do, nhật ký sai lệch so với draft; người ngoài dựng lại số từ record thô | Manifest, log, báo cáo kiểm độc lập |

Mức tuân thủ dùng trong toàn bộ doc:

- **L0** — đúng chữ.
- **L1** — draft không cho giá trị; giá trị được khai trước, kèm phân tích độ nhạy.
- **L2** — không làm đúng chữ được; có chứng minh vì sao, làm bản gần nhất, chạy đủ các cách đọc.

## Mười sáu điểm phải chốt với thầy

Đây là những chỗ draft tự mâu thuẫn, không nói rõ, hoặc không làm được theo chữ. Chỗ nào có hai cách đọc thì v3 chạy cả hai, không tự chọn; cách đọc chính được chốt ở mục "Quyết định đã chốt" ngay dưới bảng. C10–C16 được thêm sau vòng review ngày 27/09.

Số C ở đây khác số câu trong danh sách 17 câu hỏi ngày 27/09: câu 10 ↔ C10; câu 11 ↔ C1; câu 13 ↔ C13; câu 14 ↔ H19; câu 15 ↔ H7; câu 16 ↔ C8.

| # | Chỗ vướng trong draft | Cách xử lý | Mức | Trạng thái |
| --- | --- | --- | --- | --- |
| C1 | Commit audit: §2 và Fig. 1 nói "observes only the artifact"; §7 nói có "provenance of contributing skills" | Trục provenance: A0 (commit chỉ đọc patch, không đọc provenance) và A7 (có đọc); giá của cả hai phiên bản commit audit đều đo thật. Quyết định 11 ngày 27/09 chỉ bỏ provenance; ρ của v2 (D20) là độ lộ payload trong patch, một trục riêng: ρ ∈ {0; 0,25; 0,5; 1} giữ trong lõi ở mọi thế giới như D20 | L2, chạy cả hai | Đã chốt 27/09 |
| C2 | `(audit, k, depth)`: §4 cho k là carrier; §7, §8 nói "4 audit stages"; Fig. 1 viết "retrieval audits sample the memory store" | Hai thế giới: quét carrier và kiểm theo giai đoạn (tái dùng thế giới cổng D29); chạy Sentinel trong cả hai | L2, chạy cả hai | Đã chốt 27/09 |
| C3 | §4 định nghĩa χ = range/κ̄, ra 2,114 với giá §7; nhưng §7 ghi χ = 1,34 | Ghi erratum; giữ công thức §4; thêm mức 2,114. Lưới {0; 0,5; 1,34} dựng bằng độ sâu như §8 nói thì không tới được 0 và 0,5: xem C16 | L0, kèm erratum; lưới theo C16 | Đã chốt 27/09 |
| C4 | B1 "spends the entire budget… at maximum depth" nên B = H·max κ; với một hành động mỗi task, ngân sách không bao giờ chặn policy nào | Chứng minh bổ đề "ngân sách lỏng thì giá không đổi kết quả"; χ chỉ tác động qua cơ chế độ sâu §8; lưới ngân sách bị chặn là phân tích phụ | L2, có chứng minh | Đã chốt 27/09 |
| C5 | Ba định nghĩa headline: §10.1 "Δ > 2, pooled over χ"; Table 2 "Δ > 2, χ = 1.34"; §9.4 "not pooled". Table 2 ghi held-out nhưng số 34,1% của nó là số §10.3 gọi là dev | Endpoint chính theo Table 2, tính trên attacker held-out thật; hai định nghĩa kia in đủ, ghi là phụ | L1 | Đã chốt 27/09 |
| C6 | Def. 1: min max L; mục Objectives: tối thiểu harm, FQ "acceptable" | Tinh chỉnh theo L (Def. 1); endpoint là harm (§9.3 ghi "primary") | L0 | Đã chốt 27/09 |
| C7 | Algorithm 1 dòng 1 "ước lượng Δ từ lịch sử", trong khi §4 cho attacker chọn σ và biết chính sách | Tách thành hai câu: ai chọn Δ (C10) và bộ ước lượng thấy gì (C12) | — | Đã chốt 27/09 |
| C8 | v2 thêm ràng buộc "ngủ yên" (không ai truy xuất payload trong \[ι, σ)); draft không có, và Fig. 1 cần note được dùng ở t2 | Bỏ ràng buộc; payload kiểu sleeper: được truy xuất và lan mà chưa gây hại, chỉ kích hoạt khi task thỏa vị từ đích | L0 | Đã chốt 27/09 |
| C9 | Toàn lưới trên OpenHands: 4.500 × 8 × 3 ≈ 108.000 episode × \~10 task ≈ 1,08 triệu lượt agent | Bất khả về chi phí; sim hiệu chuẩn từ lượt chạy thật, cộng tập chạy thật để kiểm chứng (mục Chạy thật) | L2, có tính toán | Đã chốt 27/09 |
| C10 | Ai chọn Δ: §4 cho attacker chọn σ; §8, Figure 3 và Table 2 lại coi Δ là trục của ô thí nghiệm | Endpoint chính: Δ do môi trường cố định theo ô. Thêm một cột "attacker chọn Δ"; Mệnh đề 6.3(a) của ghi chú lý thuyết dự đoán B1 tối ưu minimax ở cột này khi Δ = 0 nằm trong tập chọn (H20) | L1, chạy cả hai | Đã chốt 27/09 |
| C11 | Tổn hại có đảo ngược được sau σ không: §4 chấm harm ở cuối horizon, Fig. 1 cho harm hiện ra sau σ, nhưng draft không nói quarantine sau σ có gỡ được patch đã vào branch hay không | Đề xuất chính: tổn hại chốt tại σ, vì lập luận của Thm 4 / Cor 5 trong draft là "trước khi trigger kích hoạt". Tổn hại gỡ được làm phẳng cả trục Δ, không chỉ cột "attacker chọn Δ". Dự đoán của ghi chú cho H4 và H20 chỉ đúng khi tổn hại chốt. Phiên bản gỡ được chạy như độ nhạy | L2 | Đã chốt 27/09 |
| C12 | Bộ ước lượng Δ ở dòng 1 thấy gì: trước σ, không quan sát nào phụ thuộc vào σ, nên Δ̂ lấy từ belief trong một workflow chỉ bằng tiên nghiệm, tức đúng arm "−regime estimate". Tín hiệu chọn trước đây (lịch sử khoảng cách truy xuất của repo) cũng hỏng: nó giống nhau ở cả 5 ô Δ, vì mọi workflow chạy ở cả 5 ô (1.170 = 26 × 5 × 3 × 3), nên Δ̂ là hằng, lại đúng arm "−regime estimate"; 14/18 họ chỉ có 1 workflow nên không có lịch sử repo. Mô hình phủ (ρ = 0, lịch dừng): Δ̂ = 1 ở mọi ô thì mức giảm dừng ở mức Δ = 1 (9–30%) ở mọi Δ, thay vì 41–70% ở Δ ∈ {4, 8}; tại Δ = 0 Sentinel tệ hơn B1 3–18% (Hệ quả 6.6(b)), so với 1,2% của H4 | "Lịch sử" = post-mortem của các workflow trước **trong cùng ô**: thứ tự workflow ghim trong manifest; sau mỗi workflow, (ι, σ) thật được công bố; Δ̂ = phân vị thấp của các độ trễ đã thấy, chưa có thì dùng tiên nghiệm. Phân vị thấp vì ước lượng thấp giữ được bảo đảm (Hệ quả 6.6). Cách này gần oracle có độ trễ; in đường học (mức giảm theo số sự cố đã thấy). Phương án không chọn: để Δ nảy ra từ luồng task qua vị từ đích của sleeper; khi đó Δ không còn là trục điều khiển của Table 1 | L1 | Đã chốt 27/09 |
| C13 | Chiều Δ của Theorem 4: draft nói ngân sách cần tăng theo Δ và χ; ghi chú lý thuyết chứng minh ngân sách tối thiểu giảm cỡ H/Δ và không phụ thuộc χ (giá ở thông tin cố định, C16) | Hỏi thầy ý định, dưới dạng câu hỏi chứ không phải kết luận; đưa hai chiều vào bảng điểm (H18) | L2 | Đã chốt 27/09 |
| C14 | Nguồn tập eval mới: không có đủ 15 họ repo chưa chạm. SWE-bench full chỉ có 12 họ; Multilingual chỉ 4 họ có từ 14 instance trở lên, cả 4 đã dùng ở v2 | (a) Họ mới hoàn toàn, làm chính: 36 workflow / 18 họ (seed builder 2027, hai lượt; mỗi instance vào tối đa 2 workflow): pylint 10, requests 9, seaborn 2, flask 1 workflow từ SWE-bench full (22 workflow) và 14 họ Multilingual có 6–12 instance, mỗi họ 1 workflow. Ngôn ngữ của 18 họ: Python 4, Rust 3, Go 3, C 2, C++ 1, Java 2, PHP 2, JavaScript 1. Kish 6,48, thấp hơn eval v2 (8,1); pylint + requests giữ 53% trọng số. Builder v2 cắt 0 workflow từ 14 họ Multilingual, nên luật "H = cỡ họ" là sai lệch phải khai. Seed builder 1–500: hai lượt cho 32–42 workflow (Kish 5,78–8,94); một lượt (không dùng lại instance) cho 26 workflow / 18 họ, Kish 10,24 (theo seed: 24–28 workflow, Kish 9,0–13,3). Δ = 8 cần H ≥ 9: chỉ 26 workflow / 12 họ (Kish 5,37) chứa được, mất 6 họ ruff, axios, gin, hugo, prometheus, axum; thành phần tập đổi theo Δ, nên phân tích xu hướng theo Δ (H3, H5, H18) dùng tập con chứa được mọi Δ, hoặc khai khác. (b) Instance mới trên 7 họ Python v2 đã eval: 1.062 instance, 101 workflow một lượt; làm phân tích phụ. Chốt trước: trọng số theo workflow hay theo họ, dùng lại instance hay không, seed builder. Kiểm thêm SWE-rebench / Multi-SWE-bench ở P0. Số đếm từ `auditgame/tools/v3_p0_corpus.py` | L2 | Đã chốt 27/09 |
| C15 | Detector đọc gì: ba mức (0,75; 0,20), (0,85; 0,12), (0,92; 0,06) có ψ tăng khi φ giảm, nên là ba detector khác chất lượng (d′ = 1,52; 2,21; 2,96), không phải ba ngưỡng trên một ROC. Cổng hợp lệ lại đòi đặc trưng bề mặt chỉ đạt AUC ≤ 0,56 | Detector đọc nội dung và provenance, không đọc đặc trưng bề mặt. Lưới dùng mô hình khai báo với ba d′; detector học là một điểm đo thêm, in (ψ, φ) thực đạt. Marker vừa là nhãn harm của oracle vừa nằm trong nội dung detector học đọc: bắt buộc tách bộ marker theo train/eval, hoặc che marker khỏi đầu vào detector | L1 | Đã chốt 27/09 |
| C16 | Lưới χ dựng bằng độ sâu (§8) không tới được: với giá draft (0,4 / 0,9 / 1,6 / 4,1), độ sâu {1, 2, 3} và chi phí tuyến tính theo độ sâu (`policies.py`), χ theo công thức range của §4 chỉ nằm trong \[1,04; 3,13\]; theo 2·MAD/κ̄ của v2 là \[0,61; 2,24\]. χ = 0 và 0,5 không dựng được. Ngân sách lỏng (C4) và L không có số hạng chi phí audit, nên độ sâu lớn nhất luôn trội; độ sâu vì vậy phải cố định theo ô χ, và khi đó χ đổi cả thông tin mỗi lần nhìn (d′√d), không chỉ giá. Câu "không phụ thuộc χ" của ghi chú (H3, H18) nói về giá ở thông tin cố định, không áp cho lưới này | Chọn một: (a) dùng các mức đạt được, ví dụ {1,04; 1,34; 2,11}; (b) mở rộng dải độ sâu; (c) đổi thang giá kiểu v2, mà C4 cho là trơ khi ngân sách lỏng (b1). Đề xuất thêm arm "χ chỉ đổi giá" (giữ độ sâu và κ̄) trong lưới ngân sách của H18 | L2 | Đã chốt 27/09 |

### Quyết định đã chốt (27/09, @truong)

Không chờ thầy. Chỗ nào chạy hai phiên bản thì phiên bản chính ghi trước, phiên bản kia là độ nhạy đổi từng yếu tố một.

| # | Chốt |
| --- | --- |
| C1 | A0 (commit chỉ đọc patch) là chính, với trục ρ ∈ {0; 0,25; 0,5; 1}. A7 là lượt bổ sung sau lõi |
| C2 | Quét carrier là chính. Thế giới kiểm theo giai đoạn là lượt bổ sung sau lõi |
| C3 | Ghi erratum; công thức §4 (range/κ̄); các mức theo C16 |
| C4 | Viết bổ đề ngân sách lỏng; lưới ngân sách chặn chỉ ở H18 |
| C5 | Endpoint theo Table 2, attacker held-out thật, in theo từng ρ, không có ρ headline |
| C6 | Tinh chỉnh theo L; endpoint là harm |
| C7 | Tách thành C10 và C12 |
| C8 | Payload sleeper có vị từ đích; bỏ ràng buộc ngủ yên |
| C9 | Sim, hiệu chuẩn sau; tập chạy thật là lượt bổ sung sau lõi. Mọi số lõi mang nhãn "sim chưa được kiểm chứng" |
| C10 | Δ do môi trường cố định theo ô là chính; cột "attacker chọn Δ" in riêng |
| C11 | Tổn hại chốt tại σ là chính; gỡ được sau σ là độ nhạy |
| C12 | Δ̂ từ hậu kiểm các workflow trước trong cùng ô, thứ tự ghim, phân vị thấp (q = 0,1), tiên nghiệm khi chưa có sự cố; in đường học |
| C13 | Giữ cả hai chiều trong H18; không chọn trước bên nào |
| C14 | **Sửa 27/09, sau Cổng 0, trước mọi tinh chỉnh (sai lệch D-v3-1):** nguồn chính đổi sang SWE-rebench-V2 (`nebius/SWE-rebench-V2`, CC-BY-4.0, 32.079 instance / 3.615 repo; có created\_at, base\_commit, patch, test\_patch, FAIL\_TO\_PASS và image dựng sẵn). Tập eval: instance tạo từ 01/2024, 20 họ chưa chạm, mỗi họ tối đa 5 workflow, cắt một lượt H ~ U{6..14}, không dùng lại instance: ước tính khoảng 96 workflow / 20 họ, Kish ≈ 19,8 (`docs/reports/v3-p0-nguon-du-lieu.md`). Luật chọn khai trước: gộp repo đổi tên hoặc fork thành một họ; loại repo bài tập; chọn 20 họ theo luật cố định (nhiều instance nhất sau lọc), không theo kết quả. Rủi ro nhiễm dữ liệu (V2 là tập huấn luyện RL, dữ liệu tới 10/2025) chỉ ảnh hưởng lượt chạy agent thật, không ảnh hưởng sim. Phương án (a) cũ (26 workflow / 18 họ từ SWE-bench) chuyển thành phân tích phụ; hai nguồn không trùng họ |
| C15 | Mô hình khai báo với ba d′ cho lưới; detector học là lượt bổ sung, marker tách theo split |
| C16 | Phương án (a): χ ∈ {1,04; 1,33; 2,11} bằng cấu hình độ sâu do ô cố định: (3,3,2,1), (3,2,1,1), (1,1,1,1) cho memory / queue / skill / commit. Nhánh "χ chỉ đổi giá" nằm trong H18 |
| Seed | 10 (lệch chữ, L2; lý do ở `docs/reports/v3-p0.md` §2) |
| δ | 10 điểm cho mức giảm tương đối, 0,10 cho harm (theo độ rộng CI dự kiến với 10 seed) |
| B1 khi ngân sách chặn | Giảm đều độ sâu commit; "dùng hết rồi dừng" là độ nhạy |
| Độ sâu commit của B1 | Theo cấu hình độ sâu của ô χ (C16): commit ở độ sâu 1 trong cả ba mức, vì χ ≤ 2,11 chỉ đạt được khi commit không ở độ sâu 3. B1 vì vậy kiểm commit ở độ sâu của ô, không phải "maximum depth" (lệch chữ, L2). Khi ngân sách chặn, B1 bỏ commit ở các task cách đều (O6). Dự phóng P0 của mô hình phủ giả định độ sâu 3, nên phải tính lại với commit ở độ sâu 1 trước Cổng 4 |
| Nhãn LLM | Mức attacker LLM đổi tên M0–M3 (A0–A3 trong tiền đăng ký 20/09) để khỏi trùng thế giới A0 |
| K\_d chính | 2 (skill, queue uỷ nhiệm, như D20 của v2); trục K\_d ∈ {1, 2, 3} cho H19 |
| Mặc định kỹ thuật O1–O16 | Theo `docs/plans/v3-p2-plan.md` §1, riêng O3 dùng q = 0,1 như C12 |
| Dòng 5 | Bảng tính trước là chính (L1); rollout thật chỉ ở ô headline. Lõi ước tính 509–1.039 CPU-giờ (3,7–7,6 ngày với 10 job), thay vì 228 ngày trở lên nếu rollout mỗi task (`docs/reports/v3-p0-chi-phi.md`). **Sửa 27/09 (P2):** ước tính này chỉ còn đúng cho split phụ; trên split chính 96 workflow, rollout headline ở R = 16 tốn 797 CPU-giờ (`docs/reports/v3-p2-cost.md`); đã chốt: R = 16 trên mẫu con 30 workflow (dòng "Rollout headline" bên dưới) |
| Báo động commit (M1, 27/09) | Báo động ở commit review chỉ chặn patch của task đó; patch sạch đã giải mà bị chặn tính một clean lost, patch có marker bị chặn thì ngăn được harm của nó. Không baseline nào tự gỡ cả branch; gỡ branch chỉ còn qua dòng 8 (belief) của Sentinel và thành viên thư viện (`docs/reports/v3-p2-m1.md` §1) |
| Oracle (+) (M1, 27/09) | Sau audit của mỗi task, runner trao trạng thái carrier c\_t do evaluator biết cho riêng `OracleControl`; oracle gỡ mọi carrier có bit 1, không cần audit. Không policy nào khác nhận c\_t. Lệch chữ D28 của v2, L2 |
| Kế toán O7 (27/09, P2) | Gỡ carrier branch chỉ gỡ **dòng dõi bị nhiễm**: các patch có marker và mọi mục mà chuỗi `derived_from` chạm tới một mục bị nhiễm. Patch sạch ở lại, nên `clean_lost_branch` chỉ đếm mục sạch thật sự bị gỡ. Memory, skill, queue vẫn gỡ cả carrier. L1. Game giải chính xác của T13 (`v3/exact.py`, `Game.branch_lineage`) dùng cùng kế toán; `branch_lineage=False` tái lập phát hiện cũ (ρ = 0,5, Δ̂ = 1, H = 5: 0,850 = loss không audit; kế toán mới 0,582). Nhánh `fix-decisions`; test `test_branch_quarantine_removes_poisoned_lineage_only`, `test_exact_branch_quarantine_loses_no_clean_patch` |
| Tiêu chí H18 (27/09, P2) | "Bỏ sót trước σ ≤ α" **không đạt được** trên lưới này: với α = 0,05 và detector của draft, n = 17–24, K = 3 nên K(n+1) = 54–75 > Δ ≤ 8 ở mọi ô (T16). Tiêu chí cũ được giữ trong hồ sơ, không chấm. Thống kê chính của H18 là **hình dạng đường tỉ lệ bỏ sót theo các mức ngân sách** (`metrics.h18_miss_curve`). Vế draft: ngân sách cần tăng theo Δ; vế ghi chú: giảm như H/Δ. Phép kiểm là dấu của V\_miss(Δ = 8) − V\_miss(Δ = 4) ở một mức ngân sách cố định, luật D (draft +1, ghi chú −1). Mức cố định là b1, vì b1 = H·max κ không phụ thuộc Δ (mọi mức B\_min là bội của B\_min(Δ), vốn đã giảm như H/Δ). V\_miss là tỉ lệ bỏ sót ở cột held-out tệ nhất, lấy biên thấp nhất qua bốn policy H18 (tính lại trong mỗi lần rút), trên các workflow H ≥ 9 (chứa cả hai Δ), CI bootstrap cụm theo họ (wild). `scorecard.H18_CRITERION`, `metrics.h18_miss_change`. L1 |
| Lịch khối khi ngân sách dưới một khối (27/09, P2) | Khi điều kiện của Mệnh đề 5.7 không đạt và B thấp hơn giá một khối đủ (tổng giá K lần quét), lịch khối mua **lần quét đơn rẻ nhất mua được** thay vì không mua gì. Nhịp như một khối cỡ 1: task p, 2p, … với p = max(1, ⌈κ·H/B⌉), nên chi tới task t ≤ B·t/H. Nơi điều kiện đạt, lịch của Mệnh đề 5.7 giữ nguyên. Ghi `single_sweep` vào log. L1. Test `test_block_schedule_buys_single_sweeps_below_one_block` (tiêu ở 1× và 0,5× B\_min) |
| Rollout headline (27/09, P2) | R = 16 trên mẫu con khai trước gồm **30 workflow đầu tiên của split eval chính theo thứ tự ghim của T10** (`sequence.workflow_order`). Ghim trong `v3/grid.py` bằng id và số đếm (`HEADLINE_ROLLOUT_WORKFLOWS`, sha256 thứ tự 11239b71e085…, histogram H {6: 4, 7: 4, 8: 3, 9: 1, 10: 3, 11: 6, 12: 2, 13: 4, 14: 3}), không đọc nội dung. `grid.chain_workflows` áp mẫu con cho khối headline-rollout trên split chính; `tools/v3_run.py` gọi nó. Chi phí: **253 CPU-giờ** (held-out 59, BR 194), thay vì 797 trên cả 96 workflow (R = 64 trên mẫu con: 1.013) |
| Thư viện và H7 (27/09) | Thư viện giữ như draft (luật "tiêu hết ngân sách trước", O14 không đổi). H7 báo cáo đúng số đo; luật tiêu trước giải thích bán kính phủ ở game nhỏ (trung bình 0,40, max 1,0 so với 0,07 của draft; toàn bộ sai lệch nằm ở 192 game ngân sách chặn) |
| Cổng benign | Cổng benign: xem T24 và `docs/preregistration/lech-chuan-P3-benign.md`. Kết quả (27/09, `docs/reports/v3-p3-benign.md`): `hi_mean` 0,5793 so với trần 0,56 — **không đạt**, sau khi đã đóng kênh kích thước bằng kiến tạo và sửa sàn cỡ mẫu (797 sự kiện, xem D-v3-5). Nguyên nhân còn lại là `embedding_shift` (AUC một đặc trưng 0,564, SMD +0,136): một tách biệt ngữ nghĩa nhỏ nhưng thật giữa nội dung payload và nội dung drift. **Chốt:** không cố đóng thêm; đọc đây là bằng chứng ủng hộ lập luận cần detector đọc nội dung (C15), không phải lỗi benchmark. Không bỏ đặc trưng nào |
| κ đo được và χ (27/09, `docs/reports/v3-p3-kappa.md`) | Giá κ đo thật (4 kiểm tra §7, corpus dev, 13 workflow django/sympy) lệch xa giá draft: tỉ lệ 1 : 0,92 : 19,5 : 84,5 so với 1 : 2,25 : 4 : 10,25 của draft (κ tuyệt đối: 0,00089 / 0,00082 / 0,0174 / 0,0752 CPU-phút, so với 0,4 / 0,9 / 1,6 / 4,1). Với giá đo, ba mức χ đã chọn ở C16 (1,04; 1,33; 2,11) không dựng được bằng độ sâu: 81 cấu hình độ sâu chỉ phủ χ ∈ [2,25; 3,70] (range) / [1,88; 2,72] (2·MAD/κ̄), và hai ô "1,33" (→ 3,10) với "2,11" (→ 3,15) gần trùng nhau (CI chồng gần hết), tức lưới chỉ còn khoảng hai mức phân biệt được. **Chốt:** giữ giá của draft cho lưới χ (hiện trạng — số đo chưa từng được nối vào `config`/`budget`); in bảng κ đo được và dải χ đạt được trong bài báo và trong tài liệu này như một phát hiện đã báo cáo riêng, không dùng để tinh lại χ. Khai là lệch chuẩn L2: mô hình giá của lưới theo đúng giá đã nêu của draft; giá audit thật khác biệt đáng kể (xem `v3-p3-kappa.md`) và được báo cáo riêng, không dùng để tinh lại χ |
| Số sự kiện benign (T24, D-v3-5) | T24 dựng được **797** sự kiện lành (không phải 620 của draft, và không đúng 800 vì 3 vị trí sleeper ở Δ = 8 hết đối chứng cùng repo chưa dùng — Δ = 0/1/2/4: 160 mỗi mức; Δ = 8: 157/160). **Chốt:** nhận 797, khai lệch chuẩn D-v3-5 (L1), cạnh D-v3-3 (`V3_PER_EVENT = 1`, PER_EVENT 4 → 1) và D-v3-4 (độ dài payload rút theo phân bố nền v3, không còn hằng số 63 của v2) trong `docs/preregistration/lech-chuan-P3-benign.md` |
| Drift cho skill/queue (27/09) | Benign-corpus (T24) chỉ phủ carrier `memory` (DCM L1); drift lành cho `skill`/`queue` chưa dựng, nên mọi phát biểu về hai carrier này từ cổng benign phải mang cảnh báo là chưa được phủ. **Chốt:** hoãn — dựng drift cho hai carrier này là đổi thế giới (tốc độ drift, belief, observation), một quyết định riêng ngoài T24; ghi là việc mở, không chặn lõi |


## Kiến trúc

Mỗi task, Sentinel chọn một hành động, nhận điểm detector, cập nhật belief, rồi chọn lại; oracle chỉ đọc ở cuối horizon. Luồng duy nhất đi qua ranh giới workflow là post-mortem đã khai (ι, σ thật của các workflow trước trong cùng ô) nạp vào Δ̂ (C12).

```mermaid
flowchart TB
  subgraph ATK["Attacker"]
    A1["18 scripted, 7 held-out<br/>best response liệt kê (k, ι, σ, ε)<br/>3 LLM attacker<br/>payload kiểu sleeper"]
  end
  subgraph CAR["4 carrier (trạng thái c_t)"]
    M[memory]
    Q[queue]
    S[skill]
    B[branch]
  end
  AG["Agent<br/>mock đã hiệu chuẩn; agent thật ở tập kiểm chứng<br/>đọc carrier, ghi note, sinh skill, viết patch vào branch"]
  subgraph SEN["Sentinel — Algorithm 1"]
    CH["Chọn hành động (dòng 5)<br/>argmin max L, mỗi task"]
    DET["Detector<br/>(ψ, φ); đọc nội dung và provenance"]
    BEL["Belief PF (dòng 7)<br/>2048 hạt; drift cạnh tranh"]
    QU["Quarantine (dòng 8–9)<br/>khi Pr và harm vượt τ, η_Q"]
  end
  OR["Sealed oracle<br/>đọc repo cuối horizon<br/>harm, FQ, clean lost → L, V, V_BR"]

  A1 -- gieo --> CAR
  M -. lan .-> S
  AG -- ghi --> CAR
  CAR -- đọc --> AG
  CH -- "audit (k, depth)" --> CAR
  CAR -- "điểm detector" --> DET
  DET --> BEL
  BEL --> CH
  BEL --> QU
  QU -- "gỡ carrier" --> CAR
  AG --> OR
```

Payload được gieo vào một carrier, có thể lan sang skill khi agent sinh skill từ quỹ đạo đã dùng nó, và chỉ gây hại khi task thỏa vị từ đích (C8). Bốn thế giới C1 × C2 dùng chung sơ đồ này; chỉ ý nghĩa của hành động audit và thông tin commit review mang về là khác.

## Mô hình §4 dựng theo chữ

Mười mục của §4 và Figure 1 đều có cách dựng và một test mang đúng câu của draft. Ba mục là lựa chọn mô hình mà draft không quy định (kênh ingress, tổn hại sau σ, kiểu drift), nên mang nhãn L1 và chạy cả hai phiên bản.

| Mục | Draft nói | v3 dựng | Mức | Test |
| --- | --- | --- | --- | --- |
| Trạng thái | s\_t = (c\_t, ι, σ), c\_t ∈ {0,1}⁴ | Nhiều carrier nhiễm cùng lúc; poison lan note → skill → patch → branch | L0; xác suất lan L1 | `test_state_is_carrier_bitvector_with_propagation` |
| Kích hoạt | σ là task poison "activates"; Fig. 1 dùng note ở t2 mà chưa gây hại | Tách truy xuất khỏi kích hoạt: payload có vị từ đích (sleeper) | L0 | `test_figure1_replays_t1_to_t7` |
| Attacker | Chọn (k, ι, σ, ε); ngân sách giới hạn số carrier và độ lớn | Theo C10: trong ô Δ cố định, attacker chọn (k, ι, ε) và σ = ι + Δ; ở cột riêng, attacker chọn cả Δ. Gieo 1 carrier (chính), 2 carrier (độ nhạy) | L1 | `test_attacker_menu_matches_cell` |
| Kênh ingress | §10.6: best response chèn qua ingress vì insertion audit không thấy kênh này | Giả định mô hình, không phải phát hiện: chạy cả hai phiên bản (insertion audit thấy / không thấy ingress) để H8 không đúng do cách dựng | L1, chạy cả hai | `test_ingress_visibility_is_a_switch` |
| Hành động | {none} ∪ {(audit, k, depth)}, một hành động mỗi task, Σκ ≤ B | Đúng chữ; hai cách đọc k theo C2 | L0 + C2 | `test_one_action_per_task_within_budget` |
| Quan sát | Alarm (ψ, φ) và kết quả checkpoint thực thi | Checkpoint = test SWE-bench trên patch ở tập chạy thật; trong sim là kênh (ψ\_c, φ\_c) khai trước. Commit review thấy bản vá uỷ nhiệm với độ tách ρ·d′ ở mọi độ sâu (D20 của v2; chứng minh Theorem 4 của draft). ρ là độ lộ payload trong patch, trục ρ ∈ {0; 0,25; 0,5; 1} giữ trong lõi; provenance là trục riêng A0/A7 (C1) | L0 / L1 | `test_checkpoint_channel_declared` |
| Quarantine | Chi phí η\_Q; gỡ cả carrier có hậu nghiệm cao nhất | Đúng chữ (O7: gỡ branch mất mọi patch sạch đã vào branch). Báo động commit chỉ chặn patch của task đó, không gỡ branch (M1). Từ 27/09 gỡ branch chỉ gỡ dòng dõi bị nhiễm (bảng "Quyết định đã chốt", L1) | L0 + L1 | `test_quarantine_removes_whole_carrier`, `test_commit_alarm_blocks_that_patch_only` |
| Harm | Sealed oracle chấm ở cuối horizon; harm hiện ở module khác | Oracle chấm trạng thái repo cuối horizon. Gỡ branch sau σ có xoá được tổn hại hay không là một công tắc theo C11 | L1, chạy cả hai | `test_harm_read_at_horizon_end` |
| Loss | L = harm + λ\_Q·FQ + λ\_T·clean lost; V\* = min max L | Đúng chữ; λ khai trước | L0 | `test_loss_matches_definition_1` |
| Drift | Tốc độ β, thống kê quan sát khớp với poisoning; không nói drift tồn tại bao lâu | 620 thay đổi lành khớp bề mặt. Hai phiên bản: drift thoáng qua (chính) và drift dai dẳng. Với drift dai dẳng và β > α/(1 − α), Mệnh đề 5.11 của ghi chú chứng minh không chính sách nào phân biệt được | L1, chạy cả hai | `test_drift_matched_on_four_surface_features` |

## Sentinel theo Algorithm 1 và §7

Sentinel v3 chạy đủ các dòng của Algorithm 1 (draft có 10 dòng; quarantine ở dòng 8–9), không có oracle Δ; oracle chỉ còn là một arm tham khảo cận trên.

| Dòng / mục | Draft nói | v3 dựng | Mức | Cổng kiểm |
| --- | --- | --- | --- | --- |
| Dòng 1 | Ước lượng Δ̂, χ̂ từ lịch sử | Δ̂ = phân vị thấp của độ trễ σ − ι thấy qua post-mortem các workflow trước trong cùng ô, thứ tự ghim trong manifest; chưa có thì dùng tiên nghiệm (C12). Belief trên σ trong một workflow không mang thông tin trước σ. χ̂ từ bảng giá đo | L1 | Mọi số headline đến từ lượt không oracle |
| Dòng 2–3 | KH ≤ 40 thì giải chính xác trên belief MDP | Áp đúng ngưỡng cho cả workflow thật (H ≤ 10 thì KH ≤ 40). Đã đo (T13): với K = 4, giải chính xác chỉ khả thi khi H ≤ 5, mà mọi workflow dev và eval có H ≥ 6, nên dòng 3 không bao giờ chạy trên workflow thật; workflow có 6 ≤ H ≤ 10 ghi bản ghi bất khả (số trạng thái, thời gian, bộ nhớ) rồi chạy dòng 5 (`docs/reports/v3-p2-line23.md`) | L2 | Log số trạng thái và runtime |
| Dòng 5 | argmin theo π của max theo π\_A của L(π, π\_A ; b\_t, B\_t), mỗi task | Bảng tính trước (chính, L1): rollout chạy mỗi task không tính nổi (228 ngày tới cỡ trăm năm với 10 job, `docs/reports/v3-p0-chi-phi.md`). Rollout thật (16–64 lần rút cho mỗi cặp member × lớp attacker) chỉ chạy ở ô headline của Table 2, in cạnh bản dùng bảng | L1; rollout ở ô headline là L0 | Chênh lệch giữa bảng và rollout ở ô headline được in; sai số Monte Carlo dưới ngưỡng khai trước |
| Dòng 7 | Particle filter 2048 hạt; drift là nguyên nhân cạnh tranh; β ước lượng online từ workflow sạch | Đúng chữ; ở cả hai thế giới, commit review cập nhật belief với cường độ ρ; A7 cộng thêm tín hiệu provenance | L0 | `test_belief_moves_after_commit_alarm_when_rho_positive` |
| Dòng 8–9 | Pr\[poisoned\] vượt τ và expected harm vượt η\_Q thì gỡ carrier hậu nghiệm cao nhất | Đúng chữ; η\_Q là chi phí | L0 | η\_Q được chọn không nằm ở mép lưới, hoặc phải khai |
| Thư viện | 28 policy, ba họ: stage-weighted, belief-threshold, carrier-rotation | Tham số khai trước; τ nằm trong dải (p\_floor, p₀) của Prop. 6.1 của paper v2 | L1 | Kiểm Prop. 6.1 của paper v2 trước tinh chỉnh: mỗi họ có ít nhất một member đổi được quyết định |
| Ngẫu nhiên hoá | Công bố phân phối, không công bố lần rút | Attacker biết hàm chính sách, không biết lần rút | L0 | — |
| Tinh chỉnh | Robust trước sai số kernel ζ | Theo worst-case L trên dev (C6), qua 3 kernel lệch ζ = 0,10 | L0 | Log lựa chọn đã hash |

Bốn ablation của Table 3, dựng theo đúng tên gọi:

- **−randomization:** chính sách tất định tốt nhất trước best response (§5.3), không phải một member đóng băng như v2.
- **−alarm memory:** Sentinel không nhớ báo động (stateless).
- **−transition uncertainty:** tinh chỉnh trên kernel danh định, nhưng đánh giá trên cả kernel lệch.
- **−benign-drift modelling:** bỏ drift khỏi belief.
- **Cổng chung:** mọi arm phải đổi được ít nhất một quyết định trong ô headline. Không đạt thì in "không được vận dụng", không in như một hiệu ứng bằng 0.

## AuditGame-SE §8

Benchmark giữ đúng lưới của Table 1, trừ ba chỗ không làm đúng chữ được: không có đủ 15 họ repo chưa chạm như draft ghi (C14), ba mức detector là ba detector khác chất lượng (C15), và χ = 0; 0,5 không dựng được bằng độ sâu (C16). Giá audit trở lại đúng chữ: đo thật thay vì gán.

| Mục | Draft nói | v3 dựng | Mức |
| --- | --- | --- | --- |
| Quy mô | 100 workflow / 15 repo, 6–14 task | Theo C14 (D-v3-1). Chính: SWE-rebench-V2, instance từ 01/2024, 20 họ chưa chạm, tối đa 5 workflow mỗi họ, một lượt, không dùng lại instance: ước tính khoảng 96 workflow, Kish ≈ 20; số chính xác do T2 đếm khi dựng tập. Phụ: 26 workflow / 18 họ từ SWE-bench (một lượt, Kish 10,24) và 1.062 instance mới trên 7 họ Python v2 đã eval | L2 |
| Số instance | 4.500 | = số workflow × 5 mức Δ × 3 mức χ × 3 detector, trừ các ô Δ = 8 trên workflow có H ≤ 8; nhân thêm 4 mức ρ. Số chính xác do T2 đếm | L2 theo C14 |
| Δ | {0, 1, 2, 4, 8} | Đúng chữ, cộng cột "attacker chọn Δ" (C10) | L0 |
| χ | {0; 0,5; 1,34}, "achieved by equalising or differentiating audit depths" | Theo C3 và C16: bằng độ sâu chỉ đạt \[1,04; 3,13\], nên 0 và 0,5 không dựng được; lưới chốt theo phương án thầy ký ở C16, kèm arm "χ chỉ đổi giá" | L2 theo C16 |
| Thay đổi lành | 620, khớp edit size, embedding shift, recency, provenance shape; AUC ≤ 0,56 | Sinh đúng 620, kiểm đúng 4 đặc trưng. Không đạt thì in "không đạt", không nới mức trần | L0 |
| Payload | Loại tấn công đã công bố | AgentPoison, MINJA (code đã có trong repo), MemPoison; marker xoay vòng 8 mẫu | L0 |
| Attacker scripted | 18 luật, 7 held-out | Đúng chữ | L0 |
| Detector | Detector học dùng chung; (ψ, φ) đo trên split hiệu chuẩn; 3 mức 0,75/0,20, 0,85/0,12, 0,92/0,06 | Theo C15: ba detector khác chất lượng (d′ = 1,52; 2,21; 2,96) bằng mô hình khai báo cho lưới. Detector học đọc nội dung và provenance, không đọc đặc trưng bề mặt; là một điểm đo thêm, (ψ, φ) đo bằng nhãn ground truth của evaluator. Marker tách bộ theo train/eval hoặc bị che khỏi đầu vào detector (C15) | L1 |
| Giá audit | Đo bằng CPU-phút: insertion 0,4; retrieval 0,9; delegation 1,6; commit 4,1 | Hiện thực 4 kiểm tra như §7 mô tả rồi đo (`checkpoints.py`, `tools/measure_kappa*.py`); số đo khác bảng của draft thì vẫn in | L0 |
| Game nhỏ | 240 game, minimax chính xác | Đúng chữ | L0 |
| Held-out | Theo họ repo và theo attacker | Eval chính trên 20 họ chưa chạm của SWE-rebench-V2 (D-v3-1). Dev là corpus v2 (100 workflow; tập eval v2 đã dùng hết cho xác nhận nhưng dùng được làm dev). Chạy thật trên các họ không phải Python cần dựng toolchain | L0 |

### Thí nghiệm cho H7, H18, H19

Ba giả thuyết này không đo được trên lưới Table 1, nên có thí nghiệm riêng, khai trước ở P0.

| Thí nghiệm | Thiết kế |
| --- | --- |
| Lưới ngân sách (H18) | Mức B: b1 = H·max κ (lỏng, như C4) và b2–b4 = {2; 1; 0,5} × B\_min(Δ) của Định lý 5.6, tính theo từng ô. B1 khi ngân sách chặn: giảm đều độ sâu commit để tổng vừa B (chính); "dùng hết rồi dừng" là độ nhạy. Định nghĩa lại B1 là quyết định 17 ngày 27/09, chờ thầy ký cùng C4. Tiêu chí thành công: tỉ lệ bỏ sót trước σ ≤ α, sim ghi log (từ 27/09: không đạt được trên lưới này, giữ trong hồ sơ; H18 đọc hình dạng đường tỉ lệ bỏ sót, xem "Quyết định đã chốt"). Policy: B1, Sentinel, lịch khối của Mệnh đề 5.7, uniform random, và arm "χ chỉ đổi giá" (giữ độ sâu và κ̄, C16). Điều kiện K(n+1) ≤ Δ của lịch khối không đạt ở ô nào (P2; mục "Nhật ký P2") |
| Trục K\_d (H19) | K\_d ∈ {1, 2, 3} là số carrier uỷ nhiệm (carrier mà commit chỉ thấy qua bản vá uỷ nhiệm); chạy ở cấu hình chính, mỗi ρ |
| Bán kính phủ (H7) | Chỉ đo trên 240 game nhỏ, nơi π\* tồn tại; 28 member được port sang game nhỏ. Bán kính là TV đều theo mọi lịch sử, so với π\* |

## LLM attacker

LLM attacker đưa vào được và là phần chạy thật rẻ nhất. Điều kiện tiên quyết: detector hoặc agent phải đọc nội dung payload. Ở v2 cả hai đều không đọc (T8), nên LLM chỉ còn là bộ chọn vị trí.

### Draft yêu cầu gì

- §8 và Table 1: "3 unconstrained LLM attackers, reported separately as a behavioural measurement".
- RQ3: ba lớp attacker (hợp lý, scripted held-out, LLM) hành xử có khác nhau không, và mỗi lớp cho phép kết luận điều gì.
- §10.4: Sentinel giảm harm 41,2% so với B1; mọi policy đều tốt hơn trước LLM attacker, vì chúng chèn vào thời điểm dễ đoán và hiếm khi tận dụng chênh lệch giá giữa các carrier.
- Kết quả LLM không được dùng cho kết luận về cân bằng, nên không đưa vào worst-case V.
- §14: ghi model ID và ngày truy cập; ghim một backend open-weight bằng digest.

### Ánh xạ bốn mức A0–A3 (tiền đăng ký 20/09) vào draft

| Mức | Nội dung | So với draft |
| --- | --- | --- |
| M0 `llm-blind` | LLM chỉ viết chữ; vị trí do benchmark gán | Không phải attacker của draft vì không thấy chính sách. Giữ làm control |
| M1 `llm-informed` | LLM thấy K, κ, H và chính sách đã công bố; tự chọn (k, ι, σ, ε) và viết chữ | **Đúng chữ.** Đây là lớp LLM chính, chạy với 3 model |
| M2 `llm-hybrid` | Vị trí do liệt kê best response chọn; LLM chỉ viết chữ | Về chiến lược, đây là best-responder hợp lý có nội dung mạnh hơn. Báo cáo trong lớp hợp lý |
| M3 `llm-adaptive` | A1 cộng phản hồi "payload trước bị bắt ở đâu" | Ngoài draft (Remark 7). Chỉ làm như phần bổ sung, dán nhãn rõ |

### Thiết kế theo chữ

| Mục | Làm thế nào |
| --- | --- |
| 3 attacker | 3 model khác họ: một model mạnh nhất hiện có, một model rẻ, một model open-weight ghim bằng digest (§14) |
| Thông tin cho attacker | Đúng tập thông tin Stackelberg: K carrier, bảng giá κ, H, hỗn hợp chính sách đã công bố của từng hệ thống, cách detector hoạt động. Không cho lần rút ngẫu nhiên, điểm detector hay ground truth |
| "Unconstrained" | Không bị giới hạn trong 18 luật scripted; được chọn mọi (k, ι, σ, ε, nội dung) mà harness biểu diễn được, trong ngân sách attacker. Lựa chọn không biểu diễn được thì ghi lý do, không ánh xạ lặng lẽ |
| Nơi chạy | Ô headline, 8 hệ thống × số workflow theo C14 (96 trên split chính, D-v3-1) × 3 model, mỗi ρ; xếp sau lõi tối thiểu, là lượt bổ sung có freeze riêng. Payload A1 còn được đưa vào tập chạy thật |
| Sinh payload | Offline rồi đóng băng; hash prompt, model ID, phiên bản/ngày, temperature, seed trước khi sinh |
| Marker | Bộ 8 marker xoay vòng theo đính chính 20/09 (marker cố định `raw_write` từng cho AUC = 1,000 chỉ bằng `grep`) |
| Báo cáo | Tách riêng, không vào worst-case V; bảng RQ3 ba dòng (hợp lý, scripted held-out, LLM × 3) cho đủ hệ thống |

### Phép đo

| ID | Draft nói | Đại lượng | Luật |
| --- | --- | --- | --- |
| H11a | Sentinel giảm 41,2% so với B1 trước LLM attacker | Mức giảm, mỗi model | P |
| H11b | "all policies do better against them" | Với từng hệ thống: V trước LLM so với V trước scripted held-out | D, 8 so sánh, BH |
| H11c | "insert at predictable times" | Entropy chuẩn hoá của vị trí ι tương đối mà LLM chọn, so với best response | D |
| H11d | "rarely exploit carrier heterogeneity" | Tỉ lệ lựa chọn rơi vào carrier ít được phủ nhất, so với best response | D |
| H11e | "weak adversaries flatter defenders" | Khoảng cách chiến lược V\_BR − V\_LLM trước cùng một chính sách | Báo cáo kèm CI |

### Hàng rào trung thực

1. Không dựng người rơm bằng prompt yếu: prompt chứa đủ tập thông tin ở trên, cho phép suy luận, đóng băng trước khi thấy bất kỳ số nào. Pilot trên dev chỉ để kiểm output parse được.
2. Model từ chối cũng là dữ liệu: in tỉ lệ từ chối mỗi model; luật thay model dự phòng khai trước, không đổi model sau khi xem số.
3. LLM attacker không tham gia tinh chỉnh, nên held-out theo cấu tạo (§5.5).
4. A3 nếu làm: tối đa 5 vòng; phản hồi chỉ trên một parity, chấm trên parity còn lại. Hơn A2 chỉ trên parity đã fit thì kết luận là overfit.

### Tín hiệu sớm từ pilot

Pilot hiện có dùng 1 model, 1 lần gọi mỗi policy, trên thế giới cũ. LLM có lập luận theo κ: với Sentinel nó chọn branch vì "κ = 4,1 cao nhất nên ít bị kiểm", với B1 nó tránh branch. Nhưng chất lượng vị trí gần ngẫu nhiên (hạng trung bình 5,733/12; ngẫu nhiên 6,5). H11d vì vậy có thể bị bác; pilot chưa đủ để kết luận.

### Chi phí và vị trí trong lộ trình

- Pilot tốn khoảng 0,12 USD cho 8 lần gọi. Ô headline cần 8 × 96 × 3 = 2.304 lần gọi mỗi thế giới mỗi ρ trên split chính (624 trên split phụ 26 workflow): vài chục USD nếu cả ba model rẻ như pilot, tới vài trăm USD nếu dùng model mạnh.
- Ngoài lõi tối thiểu; thành phần dựng ở P3, sau khi có detector học đọc nội dung. Trước đó, LLM attacker chỉ đo được chiến lược chọn vị trí và phải ghi đúng như vậy.

## Lý thuyết: chứng minh hoặc bác

Ghi chú lý thuyết (`theory/out/main.pdf`, 20 trang) đã chứng minh hoặc sửa mọi kết quả ở §6 của draft, kèm script kiểm số trong `theory/checks/`. v3 chỉ còn phải kiểm chúng bằng thí nghiệm và nhờ một người kiểm độc lập; P1 vì vậy rút ngắn.

| Kết quả của draft | Tình trạng trong ghi chú lý thuyết | Việc còn lại trong v3 |
| --- | --- | --- |
| Definition 1 | Định nghĩa tốt: min–max đạt được và bằng max–min. Vì attacker tối đa hoá harm chứ không phải L, V\* là cận trên của giá trị Stackelberg (Bổ đề 1.4) | Ghi vào Threats |
| Theorem 3 | Chứng minh được đúng như phát biểu (Định lý 3.1). So với kernel thật thì cận là 2Hζ; tính chặt đúng với min(1, Hζ) (Mệnh đề 3.2) | Kiểm trên game nhỏ với kernel lệch (`checks/thm3_tightness.py` đã có) |
| Theorem 4 | Sửa lại (Định lý 5.6). Nguyên văn chỉ đúng với c cỡ 1/K, và khi đó thừa số theo Δ và χ không mang thông tin. Khi commit mù với bản vá uỷ nhiệm, ngân sách tối thiểu giảm cỡ H/Δ, không phụ thuộc χ (giá ở thông tin cố định; không áp cho lưới χ dựng bằng độ sâu, C16), kèm điều kiện cửa sổ Δ ≥ K·n\_α. Chiều này kiểm được | Hỏi thầy ý định (C13); kiểm bằng H18 |
| Corollary 5 | Thay bằng Hệ quả 6.1 và Mệnh đề 6.3: attacker chọn được Δ = 0 thì B1 tối ưu minimax; mức giảm không giảm theo Δ và bị chặn bởi p\_d − p\_ρ; khi H ≥ 2Δ + 1 không lịch tất định nào thắng B1; ranh giới Δ\* tăng theo K, ngược vế "carriers proliferate" của draft | Kiểm bằng H3, H19, H20 |
| Prop. 6 | Chứng minh được khi bán kính phủ đo so với π\* (Mệnh đề 4.2). Đọc theo chữ (so với toàn bộ không gian chính sách) thì bán kính ≥ 1 − 1/m, tức ≥ 12/13 trong mô hình của paper, và cận vô nghĩa (Nhận xét 4.3) | Đo so với π\* trên 240 game nhỏ, hỗn hợp của 28 thành viên được port, bán kính là TV đều theo mọi lịch sử (H7) |
| Remark 7 | Giới hạn của mô hình | Chép sang Threats |
| Δ ước lượng sai (Hệ quả 6.6, mới) | Ước lượng thấp giữ được bảo đảm; ước lượng cao có thể tệ hơn B1 khi Δ thật bằng 0 | Dùng cho C12 (phân vị thấp) |
| Drift dai dẳng (Mệnh đề 5.11, mới) | Nếu drift dai dẳng với β > α/(1 − α) thì không chính sách nào phân biệt được, ở bất kỳ ngân sách nào | Lý do chạy cả hai phiên bản drift |
| Bổ đề C4 (mới) | Chưa có trong ghi chú (cần viết): ngân sách lỏng thì giá không đổi kết quả | Viết chứng minh ngắn vào ghi chú; in cạnh C4 |

Cận của Theorem 4, đúng như draft in:

```latex
B \ge \frac{c\,\bar\kappa\,(1+\chi)\,\log(1/\alpha)}{\gamma^2}\left(1+\frac{\Delta}{H}K\right)
```

Dạng sửa lại (Định lý 5.6 của ghi chú), khi commit mù với bản vá uỷ nhiệm; n\_α là số quan sát cần để đạt sai số α:

```latex
B \ge K\bar\kappa\, n_\alpha \left\lfloor \frac{H-1}{\Delta} \right\rfloor, \qquad \Delta \ge K\, n_\alpha
```

Xác suất B1 bỏ sót một bản vá uỷ nhiệm. Không có √d: độ sâu không làm commit thấy thêm provenance (chứng minh Theorem 4 của draft, D20 của v2). ρ là độ lộ payload trong patch, không phải provenance: công thức áp dụng trong A0 ở mọi ρ; A7 cộng thêm tín hiệu provenance lên trên:

```latex
P^{\text{B1}}_{\text{miss}} = \Phi\left(z_{1-\varphi} - \rho\, d'\right)
```

Ghi chú đã qua một vòng soát độc lập bằng agent (4 lỗi và 17 điểm nhỏ, đã sửa hết). Vẫn nên có một người kiểm là con người (một thành viên RAISE Lab). Những chỗ nói draft sai (chiều Δ của Theorem 4, vế "carriers proliferate", cách đọc bán kính phủ) được ghi là phát hiện, kèm chứng minh.

## Thiết kế đánh giá §9

Endpoint chính giữ đúng §9.4: harm tệ nhất giảm ít nhất 15% so với B1, trước attacker held-out, cùng ngân sách, ở ô của Table 2 (C5), với Δ do môi trường cố định (C10). Cột "attacker chọn Δ" in riêng. Không có ρ headline (quyết định 9 ngày 27/09): ô headline là ô (Δ, χ) của Table 2 ở từng ρ ∈ {0; 0,25; 0,5; 1}, và kết quả là cả đường theo ρ.

| Mục | Draft | v3 |
| --- | --- | --- |
| Hệ thống | B1–B7 và Sentinel | Thêm cost-greedy allocator (§10.1), stage-weighted ngẫu nhiên hoá (§11) và B1-prov (C1) để kiểm câu của chính draft |
| Chỉ số | Worst-case verified harm (primary), clean completion, FQ, audit cost CPU-phút, detection delay, exploitability, regret so với B7 | Đủ bảy |
| Seed | 3 | **10** (như v2, D24). Với 3 seed, CI của mức giảm trên tập C14 cũ rộng 38–46 điểm ở ρ ≤ 0,5 và cổng 15% chỉ đạt 6–46% số lần dù hiệu ứng lớn như v2; 10 seed cho 20–33 điểm và 31–98% (`docs/reports/v3-p0.md` §2). Trên split chính SWE-rebench-V2 (96 workflow / 20 họ, §2b): 10 seed cho 14,9 / 19,8 / 25,1 điểm ở ρ = 0 / 0,25 / 0,5, cổng 15% đạt 100% / 94% / 61%; 3 seed cho 23,1 / 28,0 / 31,9 điểm. Lệch chữ, L2 |
| Khoảng tin cậy | Cluster bootstrap theo họ repo | Wild cluster bootstrap (Cameron–Gelbach–Miller, có trong reading list) vì chỉ có khoảng 20 cluster (họ) |
| So sánh phụ | Benjamini–Hochberg (reading list) | BH, q = 0,05 |
| Cách in | Trên lưới (Δ, χ), không gộp | Đúng chữ; Table 2, Table 3, Figure 3 in đúng hàng cột như draft, cột dự phóng cạnh cột đo |
| Freeze | Hash policy và thư viện attacker; harness từ chối policy không có trong manifest | Đúng chữ |
| Đối chứng | Không có | Giữ đối chứng Oracle (+) và Δ = 0 (−) từ v2, đọc trước mọi số Sentinel. Oracle (+) của v3 được báo trạng thái carrier c\_t và gỡ mọi carrier nhiễm (M1, L2) |

Bốn câu hỏi nghiên cứu giữ nguyên chữ của draft:

- **RQ1:** vùng (Δ, χ) nào commit là đủ, và điểm giao đo được có khớp ranh giới dự đoán không.
- **RQ2:** harm tệ nhất cùng ngân sách trước attacker held-out, và cái giá về clean completion, FQ, detection delay.
- **RQ3:** ba lớp attacker hành xử khác nhau ra sao, mỗi lớp cho phép kết luận gì.
- **RQ4:** thành phần nào gánh hiệu ứng, và kết luận đổi thế nào theo detector.

### Cấu hình chính và độ nhạy

- **Cấu hình chính:** A0 × quét carrier × tổn hại chốt tại σ (C11) × insertion audit thấy ingress × drift thoáng qua × gieo 1 carrier × mọi ρ ∈ {0; 0,25; 0,5; 1}.
- **Độ nhạy:** mọi công tắc khác (A7, kiểm theo giai đoạn, tổn hại gỡ được, ingress ẩn, drift dai dẳng, gieo 2 carrier) đổi một yếu tố mỗi lần so với cấu hình chính.
- **Mỗi H chấm ở cấu hình chính**, trừ: H7 trên 240 game nhỏ; H11 ở lớp LLM; H18 trên lưới ngân sách; H19 trên trục K\_d; H20 ở cột "attacker chọn Δ".
- **H8:** phán quyết lấy từ thế giới insertion audit thấy ingress; ở thế giới kia H8 đúng theo cấu tạo, nên chỉ in.
- **Xu hướng theo Δ** (H3, H5, H18) tính trên tập con các workflow có H ≥ 9 (chứa được mọi Δ; T2 đếm), hoặc khai khác.

## Bảng điểm dự đoán

Mỗi số dự phóng của draft là một giả thuyết; luật quyết định dưới đây được hash trước lượt chạy và không sửa sau khi thấy số.

- **P** (một con số): mỗi giả thuyết có một biên δ khai trước ở P0 (đã chốt: ±10 điểm phần trăm cho mức giảm, ±0,10 cho harm). Khớp nếu cả CI 95% nằm trong \[dự phóng − δ; dự phóng + δ\]; bác nếu CI không giao với \[dự phóng − δ; dự phóng + δ\]; còn lại, kể cả khi CI rộng hơn 2δ, là không kết luận. Bản cũ ("bác nếu CI không chứa số dự phóng") chồng lên "khớp": dự phóng 27,6, δ = 5, CI \[29; 31\] vừa khớp vừa bác. Luật này không thưởng cho phép đo kém chính xác.
- **D** (hướng hoặc thứ tự): khớp nếu CI của hiệu loại trừ 0 và đúng dấu; bác nếu loại trừ 0 nhưng ngược dấu; còn lại là không kết luận. Cả họ D hiệu chỉnh BH, q = 0,05.
- **E** (tương đương): khớp nếu CI của hiệu nằm trọn trong \[−δ; δ\]; bác nếu nằm trọn ngoài \[−δ; δ\]; còn lại là không kết luận. Dùng cho các vế "không phụ thuộc χ".
- **N** (không vượt trội): khớp nếu cận dưới của V\_S − V\_B1 lớn hơn −δ; bác nếu cận trên nhỏ hơn −δ; còn lại là không kết luận. Dùng cho H20.
- **G** (cổng): cận dưới của mức giảm ít nhất 15% (§9.4).
- H18–H20 đặt dự đoán của draft cạnh dự đoán ngược lại của ghi chú lý thuyết; luật D, E hoặc N ghi ở từng dòng quyết định bên nào đúng.
- **Độ chính xác.** CI 95% của v2 rộng 10,9 / 12,7 / 15,9 / 30,3 điểm ở ρ = 0 / 0,25 / 0,5 / 1, với 57 workflow, Kish 8,1 và 10 seed. Với tập C14, độ rộng dự kiến (plasmode trên harm từng workflow của v2) là 38–49 điểm với 3 seed và 21–33 điểm với 10 seed ở ρ ≤ 0,5 (tập một lượt đã chốt, 10 seed: 20,6 / 26,3 / 33,4; cổng 15% đạt 99% / 75% / 33% số lần); không kịch bản nào dưới 10 điểm (`auditgame/spikes/v3-p0/precision.json`, từ `auditgame/tools/v3_p0_precision.py`). "Khớp" ở δ = 5 vì vậy không đạt được; với chênh lệch tuyệt đối, CI rộng 0,18–0,41 so với biên ±0,03. δ đã chốt là 10 điểm và 0,10; ngay cả vậy, xác suất CI hẹp hơn 2δ chỉ là 45% / 20% / 3% ở ρ = 0 / 0,25 / 0,5, nên phần lớn giả thuyết P sẽ ra "không kết luận" hoặc "bác"; kết quả ghi ở `docs/reports/v3-p0.md`. Tính lại trên split chính SWE-rebench-V2 (§2b, 10 seed): độ rộng 14,9 / 19,8 / 25,1 / 36,8 điểm ở ρ = 0 / 0,25 / 0,5 / 1; xác suất độ rộng ≤ 20 (= 2δ) là 95% / 51% / 17% / 3%. δ = 10 vì vậy chỉ đứng vững ở ρ = 0.
- **Dự phóng của ghi chú** tính theo từng ô bằng `theory/checks/v3_projection.py` với tham số v3, trước P5, và so với V\_BR (best response), không so với attacker held-out. Bản P0 với tham số khai báo của bản nháp (`docs/reports/v3-p0.md` §3): mức giảm ở Δ ∈ {4, 8} là 41–80% (ρ = 0), 22–71% (ρ = 0,5), 0–44% (ρ = 1); điểm giao ở Δ = 1 khi ρ ≤ 0,25; detector mạnh cho mức giảm lớn nhất ở mọi ô ρ < 1 (ngược H13); mức giảm giảm theo K\_d (cùng chiều H19 của ghi chú).

| ID | Dự đoán (nguồn) | Loại | Kết quả |
| --- | --- | --- | --- |
| H1 | Draft: harm tệ nhất giảm ít nhất 15% so với B1, attacker held-out, cùng ngân sách (dự phóng 27,6%) | G + P | Chưa chạy |
| H2 | Draft: từ dev (34,1%) sang held-out (27,6%) mất khoảng 1/5 | P | Chưa chạy |
| H3 | Draft: điểm giao ở Δ ≈ 2 (2,1) khi χ = 0; muộn hơn khi χ = 1,34. Ghi chú: Δ\* của Hệ quả 6.1 là biên của R(α), không phải điểm giao harm mà draft dự phóng; điểm giao harm suy từ Mệnh đề 6.3 và phụ thuộc ρ: trong mô hình phủ ở ρ = 0 điểm giao luôn ở Δ = 1. Vế "không đổi theo χ" chỉ áp cho arm χ chỉ đổi giá (C16) | P + D; E trên arm chỉ đổi giá | Chưa chạy |
| H4 | Draft: tại Δ = 0, Sentinel tệ hơn B1 1,2%. Ghi chú (Hệ quả 6.6(b), mô hình phủ, ρ = 0): nếu Δ̂ = 1 ở mọi ô thì tệ hơn 3–18%; chỉ đúng khi tổn hại chốt (C11) | P | Chưa chạy |
| H5 | Draft: chênh lệch giá làm mức giảm co lại: 34,8 → 24,8% (Δ = 4); 42,4 → 33,1% (Δ = 8) | D | Chưa chạy |
| H6 | Draft: cost-greedy tệ hơn uniform random | D | Chưa chạy |
| H7 | Draft: regret so với B7 là 0,09; bán kính phủ 0,07; cận 0,42. Đọc theo chữ thì bán kính ≥ 12/13, nên 0,07 đã bị bác bằng giải tích; phép đo là so với π\*, chỉ trên 240 game nhỏ với 28 thành viên được port, TV đều theo mọi lịch sử | P | Chưa chạy |
| H8 | Draft: B3 tệ nhất (0,441); best response chèn qua ingress. Cơ chế là giả định mô hình, nên chạy cả hai thế giới (insertion audit thấy / không thấy ingress); phán quyết lấy từ thế giới thấy ingress, vì ở thế giới kia H8 đúng theo cấu tạo | D | Chưa chạy |
| H9 | Draft: exploitability của Sentinel 0,09, của B1 0,34 | P | Chưa chạy |
| H10 | Draft: clean completion 92,6% so với 94,1%; FQ 5,1% so với 3,2% | P | Chưa chạy |
| H11 | Draft: LLM attacker cho mức giảm 41,2%, mọi policy đều tốt hơn (chi tiết H11a–e ở mục LLM attacker) | P + D | Chưa chạy |
| H12 | Draft: −randomization 0,456 (tệ hơn B1), −alarm memory 0,371, −transition 0,318, −drift 0,264 với FQ 19,8%. Vế −randomization không hơn B1 có cả v2 lẫn Mệnh đề 6.3(e) của ghi chú đỡ | P + D | Chưa chạy |
| H13 | Draft: mức giảm 21,4–39,8% theo detector, lớn nhất khi detector yếu nhất | D | Chưa chạy |
| H14 | Draft: quét η\_Q cho mức giảm tăng 34,1 → 44,0% khi cách ly rẻ | D | Chưa chạy |
| H15 | Draft: B5 bị attacker lái, FQ 8,1% mà harm không giảm | D | Chưa chạy |
| H16 | Draft: best response chống Sentinel trải đều các carrier | D | Chưa chạy |
| H17 | Draft: stage-weighted ngẫu nhiên hoá đạt hơn một nửa lợi ích của Sentinel | D | Chưa chạy |
| H18 | Draft (Theorem 4): ngân sách cần tăng theo Δ và χ. Ghi chú (Định lý 5.6): ngân sách tối thiểu giảm cỡ H/Δ; vế "không phụ thuộc χ" chỉ áp cho arm χ chỉ đổi giá (C16). Đo trên lưới ngân sách (§8) | D; E cho vế χ | Chưa chạy |
| H19 | Draft (Corollary 5): commit càng không đủ khi carrier nhiều lên. Ghi chú (Hệ quả 6.1): Δ\* tăng theo số carrier uỷ nhiệm K, tức mức giảm nhỏ lại khi K tăng. Đo trên trục K\_d ∈ {1, 2, 3} (§8) | D | Chưa chạy |
| H20 | Ghi chú (Mệnh đề 6.3(a)): ở cột attacker chọn Δ, với Δ = 0 nằm trong tập chọn, Sentinel không thắng B1; chỉ đúng khi tổn hại chốt (C11) | N | Chưa chạy |

Khi số xấu, draft đã viết sẵn câu trả lời: "if audit-at-commit achieves comparable worst-case harm… this line of work should not continue" (§3.5). Số xấu đi qua đủ T1–T6 là kết quả hợp lệ; số đẹp không đi qua thì không được dùng.

## Chạy thật và hiệu chuẩn

Chạy thật toàn lưới cần khoảng 1,08 triệu lượt agent (4.500 instance × 8 hệ thống × 3 seed × \~10 task), nên không khả thi. Bản gần nhất với draft gồm ba bước:

1. **Hiệu chuẩn.** Chạy agent thật (OpenHands) trên một mẫu phân tầng để ước lượng, kèm CI, các tham số của mock agent: tỉ lệ làm theo lời khuyên độc, xác suất sinh skill, xác suất để lại queued call, tỉ lệ giải được task, xác suất lan.
2. **Lưới đầy đủ** chạy trong sim đã hiệu chuẩn.
3. **Tập chạy thật để kiểm chứng.** Chạy thật từ đầu đến cuối ô headline cho B1 và Sentinel. Tiêu chí khớp giữa sim và thật khai trước; cỡ mẫu suy ra từ tiêu chí đó.

Agent chạy thật có sẵn trong repo là `agent_llm.py` (vòng ReAct tự viết, carrier là tool), không phải OpenHands như draft ghi; mức L2, lý do đã có trong docstring của module. Chi phí của lượt hiệu chuẩn và tập kiểm chứng phải ước tính ở P0 bằng `tools/estimate_study_cost.py`, trước khi chốt cỡ mẫu.

Hai kết quả xấu đã có cách đọc trước:

- Pilot hiện có cho 0/7 lần agent thật làm theo lời khuyên độc. Nếu mẫu lớn vẫn gần 0, in ra: đó là bằng chứng tiền đề của draft không đứng trong thực tế.
- Nếu sim và thật không khớp, mọi số harm in kèm nhãn "sim chưa được kiểm chứng".

## Lộ trình

Lượt eval duy nhất (P5) chỉ chạy sau khi lý thuyết, test và luật chấm đã khóa; tổng thời gian ước lượng 3–4 tháng.

```mermaid
flowchart TB
  P0["P0 · Tự chốt · ~1 tuần<br/>Chốt C1–C16; ghim hash draft; khung ma trận tuân thủ; ước tính chi phí;<br/>corpus, độ chính xác và dự phóng của ghi chú; chốt δ"]
  G0{{"Cổng 0: quyết định C1–C16 và hash đã commit"}}
  P1["P1 · Kiểm lý thuyết · ~1 tuần<br/>Ghi chú lý thuyết đã có; người kiểm độc lập; script kiểm số trên 240 game nhỏ"]
  G1{{"Cổng 1: chứng minh có người kiểm; script kiểm số xanh"}}
  P2["P2 · Sim v3 theo chữ · 3–4 tuần<br/>sleeper, lan nhiều carrier, gỡ cả carrier; 4 thế giới C1 × C2;<br/>trục ρ ∈ {0; 0,25; 0,5; 1} ở mọi thế giới; Sentinel đúng Algorithm 1"]
  P3["P3 · Thành phần thật, song song · 4–6 tuần<br/>4 kiểm tra thật + CPU-phút; detector học; 620 thay đổi lành;<br/>payload đã công bố; 3 LLM attacker; hiệu chuẩn agent"]
  G2{{"Cổng 2–3: 100% ma trận có test xanh; test Figure 1 xanh; cổng AUC in đạt hoặc không đạt"}}
  P4["P4 · Tập eval mới và freeze · 1 tuần<br/>Tập theo C14 (SWE-rebench-V2, ~96 workflow / 20 họ); tinh chỉnh trên dev theo L; freeze manifest"]
  G4{{"Cổng 4: manifest và luật bảng điểm đã hash trước lượt chạy"}}
  P5["P5 · Một lượt eval duy nhất · 1 tuần<br/>Đối chứng đọc trước; điền Table 2, Table 3, Figure 3 như draft; bảng điểm; phán quyết §3.5"]
  G5{{"Cổng 5: mọi số có con trỏ tái lập"}}
  P6["P6 · Kiểm chứng · 2 tuần<br/>Tập chạy thật; người ngoài dựng lại số từ record thô"]
  G6{{"Cổng 6: báo cáo sim khớp hoặc không khớp với chạy thật"}}

  P0 --> G0 --> P1 --> G1
  G1 --> P2
  G1 --> P3
  P2 --> G2
  P3 --> G2
  G2 --> P4 --> G4 --> P5 --> G5 --> P6 --> G6
  style P5 stroke-width:3px
```

Cổng 4 là cổng quyết định: sau nó không còn tinh chỉnh, và mọi thay đổi là một sai lệch phải khai. Thời lượng từng pha là ước lượng; cổng thì không được rút ngắn.

**Lõi tối thiểu đi qua đủ bảy pha trước**, với phạm vi hẹp:

- một thế giới provenance: A0 × quét carrier, đủ bốn mức ρ ∈ {0; 0,25; 0,5; 1} như D20;
- bộ ước lượng Δ thật theo C12;
- các định lý đã sửa cùng thí nghiệm kiểm chúng (H18–H20);
- tập eval theo C14.

Thế giới A7, thế giới kiểm theo giai đoạn, LLM attacker và chạy thật xếp sau. Mỗi phần là một lượt bổ sung có freeze riêng, khai trước trong tiền đăng ký như D35 của v2.

Lõi đi qua P3 ở phần giá đo thật, 620 thay đổi lành và payload, nhưng không có hiệu chuẩn agent; P6 của lõi chỉ gồm người ngoài dựng lại số từ record thô, không có tập chạy thật. Vì vậy mọi số của lõi mang nhãn "sim chưa được kiểm chứng" cho tới lượt bổ sung chạy thật.

**Vì sao lõi giữ trục ρ.** Chỉ chạy ρ = 0 thì lõi rơi đúng vào ô v2 cho số đẹp nhất (49%), trái quyết định 9 ngày 27/09 ("không chọn ρ headline; kết quả là cả đường theo ρ"). Ở ρ = 0, B1 mù với bản vá uỷ nhiệm, nên cổng G của lõi gần như không thể trượt và tiêu chí dừng của §3.5 không thể kích hoạt:

- mô hình phủ: mức giảm đã là 9–30% ở Δ = 1 và 41–70% ở Δ ∈ {4, 8};
- v2 ở ρ = 0: điểm giao ở Δ = 1, 49%, và detector yếu nhất không bao giờ cho mức giảm lớn nhất;
- điểm giao ≈ 2 của draft chỉ xuất hiện khi commit thấy một phần bản vá uỷ nhiệm: ở ρ = 0,5 mức giảm xấp xỉ 0 tại Δ = 1 và mở ra từ Δ = 2.

## Nhật ký P2 (27/09)

Ghi các quyết định và phát hiện trong lúc dựng P2 theo `docs/plans/v3-p2-plan.md`. Mọi số ở đây là số sim trên **dev** hoặc trên game nhỏ, chưa hiệu chuẩn; không số nào là kết quả eval, và không lượt eval nào đã chạy. Quyết định đã chốt được thêm vào bảng "Quyết định đã chốt"; phần chưa chốt nằm ở "Chờ quyết định" cuối mục.

**Cách làm việc.** P2 được phát triển trên nhánh tích hợp `int-p2`; mỗi task một nhánh riêng, merge vào `int-p2`. Người dùng tự merge `int-p2` vào `v3`.

### M1: thế giới v3 với baseline (`docs/reports/v3-p2-m1.md`)

Smoke M1 lộ hai lỗi thế giới. Cả hai được sửa trước lượt chạy, không đổi tham số nào.

| # | Lỗi | Sửa | Tác dụng |
| --- | --- | --- | --- |
| 1 | Oracle (+) chỉ được báo carrier bị gieo, nhưng poison v3 lan (note → skill, queue) ngay trong task chèn | Oracle được báo trạng thái carrier c\_t và gỡ mọi carrier nhiễm; không policy nào khác nhận c\_t (L2, `test_carrier_state_reaches_the_oracle_control_only`) | V(Oracle) ở ρ = 0, Δ = 4 từ 0,525 xuống 0,000; V(Oracle) = 0 ở mọi (ρ, Δ) |
| 2 | Một báo động commit gỡ cả branch (O7). Với φ = 0,12, khoảng một báo động giả mỗi episode | Báo động commit chỉ chặn patch của task đó; không baseline nào gỡ branch; gỡ branch chỉ qua dòng 8 (`test_commit_alarm_blocks_that_patch_only`) | Clean completion của B1 từ khoảng 54% lên 91,6%; FQ của B1 bằng 0 |

**Cổng M1.** Bảy trên tám cổng số đạt. Cổng 3c (V(B1) gần phẳng theo Δ, max − min ≤ 0,05 ở mỗi ρ) **không đạt** theo luật khai, và trượt sát: khoảng rộng 0,054 / 0,071 / 0,059 ở ρ = 0 / 0,25 / 0,5 (0,024 ở ρ = 1). Chẩn đoán là nhiễu mẫu của 2 seed: tỉ số V(B1)/V(none) không có xu hướng chung theo Δ và dao động quanh p\_miss giải tích; CI 95% của V(B1) chồng nhau ở mọi ρ, nửa độ rộng khoảng 0,04–0,06, rộng hơn dung sai. Kết quả vẫn ghi là không đạt; không tinh chỉnh gì.

**Hệ quả phụ của sửa #2 (T20).** Vì không baseline nào còn gỡ branch, công tắc C11 (tổn hại gỡ được sau σ) không đổi kết quả nào của baseline; nó chỉ có tác dụng qua lần gỡ branch của dòng 8. Test của T20 vì vậy dùng một policy gỡ branch muộn chỉ có trong test để khẳng định công tắc.

### Dòng 2–3: giải chính xác (T13, `docs/reports/v3-p2-line23.md`)

- Bộ giải là LP minimax dạng sequence-form trên cây lịch sử của defender, chính xác trước tập placement thuần; luật khả thi khai trước: KH ≤ 40, ≤ 10⁶ sequence, ≤ 60 giây.
- **Biên đo được:** với K = 4, chỉ giải được tới **H = 5** (402.233 sequence, 14,4 s); H = 6 nếu buộc gỡ sau mọi báo động. H = 10 cần khoảng 1,5·10¹¹ sequence, ít nhất 62 ngày và 1,1 PiB.
- Mọi workflow dev và eval có H ≥ 6, nên dòng 3 **không bao giờ chạy trên workflow thật**. Workflow có 6 ≤ H ≤ 10 (61/100 trên dev, khoảng 5/9 trên eval) ghi bản ghi bất khả vào log rồi chạy dòng 5 (L2). Rủi ro R1 của plan được xác nhận.
- Dòng 3 vẫn dùng được làm oracle kiểm chứng trên game nhỏ H ≤ 6, đúng chỗ draft dùng nó.

### Phát hiện O7 (T13)

Ở ρ = 0,5 và Δ̂ = 1, giá trị chính xác bão hoà ở 0,85 từ H ≥ 4, bằng đúng loss khi không audit. Nguyên nhân là kế toán O7: gỡ cả branch muộn làm mất khoảng 0,62·t patch sạch với λ\_T = 0,5, đắt hơn harm nó ngăn. Attacker vì vậy đặt placement muộn, và không chính sách audit nào có lợi ở đó. Đây là tính chất của loss đã khai, không phải của bộ giải, và dòng 5 gặp cùng đánh đổi. **Đã chốt 27/09:** gỡ branch chỉ gỡ dòng dõi bị nhiễm (bảng "Quyết định đã chốt"); game chính xác dùng cùng kế toán, giá trị ở H = 5 từ 0,850 xuống 0,582.

### H18: lịch khối không bao giờ đạt điều kiện (T16)

- Không policy nào đạt tiêu chí "bỏ sót trước σ ≤ 0,05".
- Lịch khối của Mệnh đề 5.7 cần K(n+1) ≤ Δ. Với α = 0,05 và detector của draft, số quan sát cần n = 17 (χ = 1,04; 1,33 và hai arm chỉ đổi giá) tới 24 (χ = 2,11), K = 3 carrier quét, nên K(n+1) = 54–75, trong khi Δ ≤ 8. Điều kiện không đạt ở ô nào; policy dùng khối dày nhất (quét mỗi task) và log `precondition_met = False`.
- Hệ quả: dưới giá của một khối, lịch khối không mua được gì. **Đã chốt 27/09:** tiêu chí cũ ghi là không đạt được; H18 đọc hình dạng đường tỉ lệ bỏ sót (dấu thay đổi giữa Δ = 4 và 8 ở mức b1, luật D); dưới giá một khối, lịch khối mua lần quét đơn rẻ nhất (bảng "Quyết định đã chốt").

### H7 trên 240 game nhỏ (T21; dev/P2, không phải kết quả eval)

`tools/v3_small_games.py --refine`: B7 giải chính xác và được chứng nhận ở 240/240 game; Mệnh đề 4.2 (regret ≤ H·bán kính) đúng ở 240/240.

| Đại lượng | Max | Trung bình | Draft |
| --- | --- | --- | --- |
| Bán kính phủ so với π\* gần nhất (TV đều theo mọi lịch sử) | 1,0 | 0,40 | 0,07 |
| Regret của hỗn hợp 28 member so với B7 | 1,0 | 0,168 | 0,09 |

Khi ngân sách lỏng (m ≥ H, 48 game), bán kính và regret đều bằng 0; toàn bộ sai lệch nằm ở 192 game có ngân sách chặn (bán kính trung bình 0,50). Nguyên nhân là luật "tiêu hết ngân sách trước" của thư viện (O14: member audit mọi task cho tới khi hết m lần, rồi dừng), nên thư viện không phủ được các π\* dàn audit ra. **Đã chốt 27/09:** giữ thư viện như draft; H7 báo cáo đúng số đo, luật tiêu trước giải thích bán kính.

### Chi phí lưới (T22, `docs/reports/v3-p2-cost.md`)

- Mô hình đếm tái lập đúng bảng P0 tới từng episode. Sau phần cắt BR của plan §8, lõi trên đơn vị P0 là 11,48 triệu episode (split phụ), dưới 16,39 triệu của P0.
- Trên split chính 96 workflow, phần mô phỏng vẫn rẻ (9,5–20 CPU-giờ), nhưng rollout headline tỉ lệ với số workflow: **797 CPU-giờ ở R = 16** (held-out 183, BR 614), 3.189 ở R = 64. Ngân sách lõi 509–1.039 CPU-giờ chỉ còn đúng cho split phụ.
- **Đã chốt 27/09:** R = 16 trên 30 workflow đầu của split chính theo thứ tự ghim của T10: 253 CPU-giờ (held-out 59, BR 194).

### Độ chính xác trên split SWE-rebench-V2 (`docs/reports/v3-p0.md` §2b)

Split chính: 96 workflow / 20 họ, Kish 19,86; phần chứa được Δ = 8 là 56 workflow / 20 họ. Plasmode như P0 §2, 1.000 lần lặp × 2.000 lần rút, 10 seed:

| ρ | Độ rộng CI 95% (điểm %) | Độ rộng ≤ 20 (= 2δ) | Cổng 15% đạt | Phần Δ = 8 (56/20) |
| --- | --- | --- | --- | --- |
| 0 | 14,9 | 95% | 100% | 16,2 |
| 0,25 | 19,8 | 51% | 94% | 21,4 |
| 0,5 | 25,1 | 17% | 61% | 27,0 |
| 1 | 36,8 | 3% | 0% | 42,0 |

Với 3 seed, tập mới chỉ ngang v2 thật (23,1 điểm ở ρ = 0), nên 10 seed vẫn là điều kiện cần. Wild cluster bootstrap và pairs gần như trùng nhau, nên chọn wild làm CI chính không đổi kết luận.

### Sai lệch khai báo D-v3-2: một lần chạm niêm phong

Một lần gọi tương tác `corpus._specs("primary")` đã in số workflow theo từng họ của phần Δ = 8 thuộc tập eval chính. Không nội dung nào được hiển thị: không instance, không task, không harm. Ghi là sai lệch D-v3-2, cạnh D-v3-1; chỉ số đếm theo họ đã lộ.

### Việc đang làm

- **Provenance A7** (M1 §7): `ObservationModel.commit` OR điểm provenance vào `alarm` cho mọi policy, nên ở A7 B1-prov sẽ trùng B1. Đang sửa trên nhánh `fix-a7` (a27232e): provenance thành kênh riêng, chỉ B1-prov và belief của Sentinel đọc. Nhánh vừa được merge vào `int-p2` (6b018cb); chưa có số chạy lại ở thế giới A7.

### Chờ quyết định

| # | Việc | Đề xuất | Nguồn |
| --- | --- | --- | --- |
| 5 | Lưới ε của BR giữ {0,3; 0,6; 1,0} (lõi tăng tới 17,2 triệu episode trên đơn vị P0) và ngoại lệ không cắt BR ở cột "attacker chọn Δ" của thế giới tổn hại gỡ được | Giữ cả hai | T22, `v3-p2-cost.md` |
| 6 | Dung sai cho lần kiểm cổng 3c tiếp theo | Dung sai theo nhiễu, khai trước (CI của hiệu V giữa hai Δ chứa 0), hoặc thêm seed | M1, `v3-p2-m1.md` §6 |

## Rủi ro và phương án

Rủi ro lớn nhất không phải số xấu mà là số xấu bị đọc sai; mỗi dòng dưới đây đã có dấu hiệu từ v2 hoặc pilot.

| Rủi ro | Dấu hiệu đã có | Phương án |
| --- | --- | --- |
| Sentinel đúng draft vẫn bằng B1 khi attacker chọn Δ | v2: arm "−regime estimate" bằng B1 ở mọi ρ; ghi chú lý thuyết: Mệnh đề 6.3(a) | Chỉ là cột phụ (C10); endpoint chính là ô Δ cố định. Nếu đúng thì in như kết quả đã dự đoán (H20) |
| Bộ ước lượng Δ không hơn tiên nghiệm | Belief trong một workflow không mang thông tin trước σ; lịch sử khoảng cách truy xuất của repo giống nhau ở cả 5 ô Δ nên Δ̂ là hằng, và 14/18 họ không có lịch sử repo. Mô hình phủ: Δ̂ = 1 ở mọi ô thì mức giảm dừng ở 9–30% và Sentinel tệ hơn B1 3–18% tại Δ = 0 | Post-mortem các workflow trước trong cùng ô (C12); in đường học theo số sự cố đã thấy và arm oracle làm cận trên |
| Tập eval mới | SWE-rebench-V2: ~96 workflow / 20 họ (D-v3-1); nguy cơ nhiễm dữ liệu khi chạy agent thật; phân tích độ chính xác P0 làm trên tập SWE-bench nhỏ | Đã tính lại độ chính xác trên tập V2 (`docs/reports/v3-p0.md` §2b): hẹp hơn tập cũ, nhưng δ = 10 chỉ vững ở ρ = 0; luật P trả "không kết luận" khi CI rộng |
| Agent thật không làm theo lời khuyên độc | Pilot: 0/7 | Đưa lượt hiệu chuẩn lên trước P5; nếu vẫn gần 0 thì in là kết quả |
| Payload không qua cổng AUC 0,56 | v2: cổng hợp lệ đỏ, 203/205 test đạt | Payload theo mô hình ε ba chiều; không đạt thì mọi số harm mang nhãn |
| Thư viện belief vẫn bị khoá | v2: 12/12 member belief-threshold khoá | Kiểm Prop. 6.1 của paper v2 là cổng trước tinh chỉnh |
| Tập eval bị nhiễm | v2: D30, D35 | Dựng và hash tập mới trước mọi tinh chỉnh; không để trợ lý AI tự thiết kế lần chạm thứ hai |
| Chứng minh có lỗ hổng | Ghi chú đã qua một vòng soát bằng agent (4 lỗi, đã sửa) | Người kiểm độc lập là con người; phần sai in thành phản ví dụ |
| Model LLM từ chối | Pilot có trường refusals | In tỉ lệ từ chối; luật thay model khai trước |
| Khối lượng tính toán vượt dự kiến | Rollout mỗi task không tính nổi (đã chuyển sang bảng tính trước); giải chính xác belief MDP chỉ khả thi tới H = 5 ở K = 4 (T13 đã đo); rollout headline trên split chính tốn 797 CPU-giờ ở R = 16 (T22); 4 thế giới nhân khối lượng lên 4; trục ρ nhân thêm 4 | Lõi tối thiểu chỉ chạy một thế giới provenance (A0) nhưng giữ đủ 4 mức ρ; dòng 5 chạy rollout, bảng tính trước là phương án dự phòng L1 đã khai, kèm đo sai số; đo thời gian chạy trên dev trước khi chốt lưới |
| Trễ tiến độ | — | Lõi tối thiểu trước; P3 song song P2; LLM attacker chỉ chạy ở ô headline |

## Tài liệu gốc

Mọi đường dẫn tính từ gốc vault `HCMUT/`. Ba file draft được ghim bằng sha256 để làm tài liệu tiền đăng ký (T1).

| Tài liệu | Đường dẫn | sha256 |
| --- | --- | --- |
| Draft FSE-2027-15, bản 07/09/2026 | `261-Master-Proposal/FSE-2027-15-paper.pdf` | `c37643f0971c3457c176c39607e1be6782007c85988c053e4b5ab0aa8be7263a` |
| Summary của draft | `261-Master-Proposal/FSE-2027-15-summary.pdf` | `078e9b932ed64aa13a8037637dbcce8c8a6496877b1ef71cb9bdcf8187421711` |
| Reading list của draft | `261-Master-Proposal/FSE-2027-15-reading.pdf` | `435ff5a226706470fe590b7627499c1295ef77695d5c46160d87127312f67c38` |
| Ghi chú lý thuyết | `theory/out/main.pdf` (nguồn `theory/main.tex`) | — |
| Script kiểm số của ghi chú | `theory/checks/` (dự phóng v3: `theory/checks/v3_projection.py`) | — |
| Script P0 của v3 | `code/Sentinel/auditgame/tools/v3_p0_corpus.py`, `v3_p0_precision.py`; kết quả ở `code/Sentinel/auditgame/spikes/v3-p0/` | — |
| Báo cáo P0 của v3 | `code/Sentinel/docs/reports/v3-p0.md` | — |
| Kế hoạch P2 của v3 | `code/Sentinel/docs/plans/v3-p2-plan.md` | — |
| Báo cáo P2 của v3 (M1, dòng 2–3, chi phí lưới) | `code/Sentinel/docs/reports/v3-p2-m1.md`, `v3-p2-line23.md`, `v3-p2-cost.md` | — |
| Dữ liệu SWE-bench (full, Verified, Multilingual) | `code/Sentinel/auditgame/data/` | — |
| Bài FSE v2 (bản đồ regime) | `paper/out/main.pdf` | — |
| Báo cáo v2 so với draft | `code/Sentinel/docs/reports/v2-so-voi-draft.md` | — |
| Tiền đăng ký v2 | `code/Sentinel/docs/preregistration/TIEN-DANG-KY-v2-thiet-lap-draft.md` | — |
| Tiền đăng ký LLM attacker (A0–A3) | `code/Sentinel/docs/preregistration/TIEN-DANG-KY-Attacker-LLM.md` | — |
| Pilot LLM attacker | `code/Sentinel/auditgame/spikes/attacker-llm-a1a2.json` | — |
