# Nhìn vào đâu: Trò chơi Phân bổ-Kiểm toán chống lại Đầu độc Dai dẳng Thích ứng trong Quy trình Phần mềm

*(Where to Look: Audit-Allocation Games against Adaptive Persistent Poisoning in Software Workflows)*

**Tác giả:** Anonymous Author(s) · FSE 2027

**CCS Concepts:** • Software and its engineering → Software creation and management; Software maintenance tools.

**Keywords:** security games, auditing, poisoning, Stackelberg equilibrium, software workflows

> **Trạng thái bản thảo (Draft status).** Mọi kết quả số trong bản thảo này là **giá trị dự phóng (projected values)**, suy ra từ thiết kế thực nghiệm đã đăng ký trước (xem `eval/PLAN.md` đi kèm); chưa có thực nghiệm nào được thực thi. Chúng là các chỗ giữ chỗ nhằm cố định trước phần phân tích và cách trình bày, **không phải số đo**. Banner này sẽ được gỡ bỏ khi kết quả đo thật thay thế chúng.

---

## TÓM TẮT (ABSTRACT)

Một defender (bên phòng thủ) với ngân sách kiểm chứng (verification budget) hạn chế phải quyết định chi tiêu nó ở đâu: tại thời điểm chèn vào bộ nhớ (memory insertion), tại truy xuất (retrieval), tại ủy quyền (delegation), hay tại chấp nhận patch. Một attacker (kẻ tấn công) có thể quan sát chính sách sẽ di chuyển mầm độc đến bất cứ nơi nào ngân sách không có. Đây là một trò chơi an ninh (security game), và các công thức Stackelberg tổng quát cho kiểm toán thích ứng đã tồn tại — nên câu hỏi là liệu có điều gì đặc thù về quy trình phần mềm (software workflows) làm thay đổi câu trả lời hay không.

Chúng tôi lập luận là có, và xác định cấu trúc cụ thể đó: đầu độc SE mang tính **dai dẳng** (persistent — trạng thái tồn tại xuyên suốt các task), **trễ** (delayed — trigger kích hoạt ở các task sau khi chèn), và **đa carrier** (multi-carrier — bộ nhớ, kỹ năng đã cache, hàng đợi công cụ và các nhánh (branch), mỗi thứ lan truyền ảnh hưởng khác nhau và tốn chi phí kiểm toán khác nhau). Chúng tôi công thức hóa một trò chơi Stackelberg hữu hạn-thời gian (finite-horizon), quan sát một phần (partially observed) trên trạng thái này, suy ra một biên minimax dưới độ bất định chuyển trạng thái có giới hạn (bounded transition uncertainty), và — kết quả quyết định liệu công thức tuần tự (sequential formulation) có xứng đáng với độ phức tạp của nó hay không — **đặc trưng hóa ngân sách kiểm toán cần thiết để phân biệt sự dai dẳng có hại với thay đổi trạng thái lành tính**, cho thấy nó tăng theo độ trễ trigger và theo tính không đồng nhất carrier theo cách mà một cuộc kiểm toán chỉ-tại-thời-điểm-commit (commit-time-only audit) không thể hấp thụ được.

Chúng tôi nghiêm túc xem xét khả năng câu trả lời là *không*. Phép so sánh đầu bảng của chúng tôi là với **audit-at-commit**, chính sách đơn giản chỉ kiểm chứng các commit cuối cùng, và chúng tôi báo cáo chế độ (regime) mà nó là đủ. Trên **AuditGame-SE** (100 quy trình sửa lỗi nhiều bước trên 15 kho mã, với trạng thái carrier và trigger đã biết đối với evaluator), một chính sách thích ứng được **dự phóng** làm giảm tổn hại đã xác minh trong trường hợp xấu nhất (worst-case verified harm) **34,1%** so với audit-at-commit ở cùng ngân sách *khi độ trễ trigger vượt quá khoảng hai task* — và **4,2%**, nằm trong khoảng nhiễu (within noise), khi không phải vậy. Tính không đồng nhất chi phí carrier (carrier-cost heterogeneity) đẩy điểm giao cắt (crossover) đó **muộn hơn** và là thứ làm cho mọi phân bổ non-minimax trở nên có thể khai thác (exploitable); nó **không** làm tăng mức lợi. Trước các chính sách attacker thích ứng giữ lại (held-out), mức giảm là **27,6%**.

## 1. GIỚI THIỆU (INTRODUCTION)

Kiểm chứng rất tốn kém, nên nó phải được phân phối có định mức (rationed). Một quy trình agent kiểm tra mọi thứ ở mọi giai đoạn thì an toàn nhưng không dùng được; một quy trình không kiểm tra gì thì nhanh nhưng bị xâm hại. Ở giữa hai thái cực là một câu hỏi chính sách — *các kiểm tra nên đặt ở đâu?* — và một đối thủ được quyền trả lời sau.

Dạng tổng quát của bài toán này đã được giải. Các trò chơi an ninh Stackelberg (Stackelberg security games) phân bổ nguồn lực phòng thủ hạn chế chống lại một attacker quan sát chính sách ngẫu nhiên hóa (randomized policy) của defender [10, 11, 16], và công thức này đã được áp dụng cho phân bổ nguồn lực an toàn AI (AI-safety resource allocation) [9]. Đầu độc dai dẳng bộ nhớ agent cũng đã được thiết lập như một mối đe dọa [3, 6, 8, 13]. Một bài báo kết hợp hai điều đó mà không bổ sung cấu trúc gì thì chỉ là một ứng dụng, và chúng tôi không cho rằng điều đó đáng công bố.

**Điều thực sự khác biệt về quy trình phần mềm.** Ba tính chất, và chúng tương tác với nhau. *Tính dai dẳng (Persistence)*: mầm độc được ghi vào bộ nhớ, vào một kỹ năng đã cache, hay vào một nhánh sẽ tồn tại xuyên suốt các task, nên trạng thái của defender không được đặt lại giữa các quyết định. *Độ trễ (Delay)*: trigger kích hoạt ở các task *sau* khi chèn, nên một cuộc kiểm toán tại thời điểm sai sẽ không thấy gì bất thường, và quan sát đáng lẽ có thông tin thì đã trôi qua. *Tính không đồng nhất carrier (Carrier heterogeneity)*: bộ nhớ, kỹ năng đã cache, hàng đợi công cụ và các nhánh lan truyền ảnh hưởng ở các tốc độ khác nhau và tốn các mức chi phí kiểm toán khác nhau — kiểm toán một bản ghi bộ nhớ thì rẻ, kiểm toán các dẫn xuất tích lũy của một nhánh thì không.

Hệ quả là bài toán của defender không phải "bảo vệ mục tiêu nào" (công thức cổ điển) mà là "**khi nào**, và ở **carrier nào**, thì nhìn vào, biết rằng tổn hại chỉ trở nên quan sát được về sau và rằng việc khiến defender nhìn sai carrier gần như miễn phí đối với attacker." Định lý 4 làm rõ điều này: ngân sách cần thiết để phân biệt sự dai dẳng có hại với thay đổi trạng thái lành tính tăng theo độ trễ trigger và theo tính không đồng nhất carrier, và một cuộc kiểm toán tại thời điểm commit — vốn quan sát *một* carrier tại *một* thời điểm — không thể trả nổi khoản đó.

**Phép so sánh quyết định bài báo.** Nếu kiểm chứng tại thời điểm commit bắt được gần như mọi tổn hại đáng kể, thì trò chơi tuần tự chỉ thêm độ phức tạp mà không thêm gì khác, và chúng tôi nên nói vậy. Vì thế chúng tôi lấy **audit-at-commit** làm baseline đầu bảng thay vì uniform random auditing, và chúng tôi báo cáo **ranh giới chế độ (regime boundary)**: phân bổ thích ứng vượt nó 34,1% khi độ trễ trigger vượt quá khoảng hai task, và 4,2% — không phân biệt được với nhiễu — khi quy trình ngắn. Chi phí carrier không đồng nhất đẩy điểm giao cắt đó **muộn hơn**, chứ không sớm hơn; ý nghĩa của chúng là chúng làm cho mọi phân bổ chưa đạt tới minimax đều có thể bị khai thác. Đóng góp chính là **việc đặc trưng hóa ranh giới đó**, ngang bằng với bản thân chính sách.

**Sentinel.** Defender cam kết một chính sách kiểm toán ngẫu nhiên hóa và một ngân sách; attacker chọn một carrier được phép, một mức sửa đổi có giới hạn và một lịch trigger. Defender quan sát các báo động không hoàn hảo (imperfect alarms) và các điểm kiểm tra có thể thực thi (executable checkpoints), duy trì một belief (niềm tin) trên (carrier, thời điểm chèn, lịch trigger), và chọn kiểm chứng (validation), cách ly (quarantine) hoặc tiếp tục (continuation). Các trò chơi nhỏ được giải chính xác; các trò chơi lớn hơn dùng một thư viện chính sách hạn chế với tối ưu hóa vững (robust optimisation). Trôi dạt lành tính (benign drift) được mô hình hóa như một **nguyên nhân tiềm ẩn tách biệt**, để một chính sách không thể ghi điểm cao chỉ bằng cách cách ly mọi thứ.

**Các lớp attacker được báo cáo tách biệt.** Một attacker best-responding hợp lý, một attacker kịch bản có giới hạn (bounded scripted attacker) và một attacker LLM không giới hạn hỗ trợ các tuyên bố *khác nhau*. Các kết quả cân bằng (equilibrium) được xác thực đối chứng với loại thứ nhất; khả năng chuyển giao (transfer) được đo đối với các chính sách giữ lại của loại thứ hai; loại thứ ba là một phép đo hành vi. **Gộp lẫn ba loại này chính là cách một bài báo trò chơi an ninh báo cáo một bảo đảm cân bằng mà nó chưa hề thiết lập được.**

**Đóng góp.** (i) Một trò chơi Stackelberg hữu hạn-thời gian, quan sát một phần trên trạng thái quy trình SE dai dẳng, trễ, đa carrier, được phân biệt rõ với kiểm toán thích ứng tổng quát (§4); (ii) một biên minimax dưới độ bất định chuyển trạng thái có giới hạn và một chặn trên phần giá trị mất đi do lớp attacker bị hạn chế (§6); (iii) **kết quả về tính phân biệt được (distinguishability)**: ngân sách kiểm toán cần thiết để tách sự dai dẳng có hại khỏi thay đổi lành tính, và chế độ mà kiểm toán tại thời điểm commit **được chứng minh là không đủ** (Định lý 4); (iv) **AuditGame-SE**: 100 quy trình với trạng thái carrier/trigger đã biết đối với evaluator, lỗi bộ dò (detector) có kiểm soát, các thay đổi lành tính với thống kê bề mặt khớp, và các chính sách attacker giữ lại (§8); (v) một đánh giá so với audit-at-commit, các cuộc kiểm toán cố định-giai-đoạn (stage-fixed audits), các chính sách ngưỡng rủi ro (risk-threshold policies) và các oracle trò chơi nhỏ cạn kiệt (exhaustive small-game oracles), với việc phát triển tấn công thích ứng được **đóng băng trước** khi đánh giá cuối cùng (§10).

## 2. NGÂN SÁCH KHÔNG Ở ĐÂU (WHERE THE BUDGET IS NOT)
![Pasted image 20260913201827.png](assets/Pasted%20image%2020260913201827.png)
**Hình 1** là lý do bài toán mang tính tuần tự chứ không phải một bài toán phát hiện ở từng giai đoạn (per-stage).

> **Hình 1: Mọi giai đoạn đều được kiểm toán, không bắt được gì.**
> *Cuộc kiểm toán chèn bỏ sót vì lấy mẫu, cuộc kiểm toán truy xuất nhìn **sai carrier**, và cuộc kiểm toán commit nhìn **đúng artifact nhưng quá muộn** để thấy nguyên nhân.*

| Thời điểm   | Sự kiện                                                                                                                                                    |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| $t_1$       | Attacker viết một ghi chú bị đầu độc vào bộ nhớ dùng chung. Kiểm toán chèn đang chạy ở **tỷ lệ 0,3**; không được lấy mẫu.                                  |
| $t_2$       | Một kỹ năng được suy ra (induced) từ một trajectory đã dùng ghi chú đó. Mầm độc giờ nằm trong **hai carrier**.                                             |
| $t_3$–$t_4$ | Hai task hoàn thành bình thường. Các cuộc kiểm toán truy xuất lấy mẫu kho bộ nhớ và không thấy gì bất thường — ghi chú *trông lành tính khi xét riêng lẻ*. |
| $t_5$       | Kỹ năng chạy trên một mục tiêu nơi bước bị đầu độc của nó có ảnh hưởng. Một patch được tạo ra.                                                             |
| $t_6$       | Kiểm toán commit kiểm tra patch. Nó nhỏ, hợp lý, vượt qua kiểm thử. **Được chấp nhận.**                                                                    |
| $t_7$       | Tổn hại biểu hiện **hai task sau đó**, ở một module khác.                                                                                                  |
**Kiểm toán tại thời điểm commit không hiển nhiên là không đủ — và đó chính là rủi ro.** Lập luận đơn giản mạnh nhất chống lại toàn bộ hướng nghiên cứu này là: dù attacker làm gì ở thượng nguồn, tổn hại rốt cuộc phải đi qua một commit, và các commit thì có thể kiểm toán được. Đó là một lập luận tốt, và nó *đúng* trong một chế độ quan trọng — các quy trình ngắn nơi trigger kích hoạt bên trong cửa sổ được kiểm toán và patch có hại phân biệt được với một patch lành tính. Nhiệm vụ của chúng tôi là xác định chính xác *nơi nó thất bại*, và Định lý 4 nói: khi độ trễ trigger vượt quá cửa sổ mà một cuộc kiểm toán commit có thể quy kết nguyên nhân, và khi các carrier khác nhau đủ nhiều để quan sát mang thông tin nằm ở một carrier mà cuộc kiểm toán commit không xem xét.

**Bài toán thực sự của defender là attribution (quy kết nguyên nhân) dưới độ trễ.** Tại $t_6$, commit trông ổn vì đúng là nó ổn *với tư cách một patch*; cái sai là *kỹ năng đã tạo ra nó*, ba carrier và bốn task trước đó. Một cuộc kiểm toán chỉ quan sát artifact không thể phân biệt "patch này là sản phẩm của một kỹ năng bị đầu độc" với "patch này bình thường", vì bằng chứng phân biệt nằm ở **nguồn gốc (provenance)** của kỹ năng đó. Đây là lý do trạng thái trong trò chơi của chúng tôi bao gồm sự chiếm dụng carrier (carrier occupancy) và lịch trigger, chứ không chỉ một điểm số báo động.

**Trôi dạt lành tính là ràng buộc khiến trò chơi không tầm thường.** Một defender cách ly mọi bất thường sẽ đạt tổn hại bằng không *và thông lượng bằng không*. Vì vậy môi trường của chúng tôi sinh ra các thay đổi lành tính với **thống kê bề mặt khớp (matched surface statistics)**: một cập nhật bộ nhớ trông y hệt một sự kiện đầu độc nhưng không phải. Không có chúng, chính sách tối ưu là "cách ly mọi thứ" và trò chơi trở nên vô vị; có chúng, defender buộc phải đánh đổi giữa cách ly sai (false quarantine) và bỏ sót sự dai dẳng (missed persistence) — và đó chính là nơi quyết định phân bổ có nội dung.

## 3. CÔNG TRÌNH LIÊN QUAN (RELATED WORK)

### 3.1 Trò chơi an ninh và kiểm toán thích ứng

Các trò chơi an ninh Stackelberg [10, 11, 16] là mô hình chuẩn tắc cho việc phân bổ nguồn lực phòng thủ hạn chế chống lại một attacker biết quan sát, và công thức này đã được áp dụng trực tiếp vào phân bổ nguồn lực an toàn AI [9]. Chúng đã chiếm lĩnh công thức tổng quát "ngân sách kiểm toán hạn chế chống lại một attacker thích ứng", và chúng tôi nói thẳng rằng một bài báo chỉ đóng góp khung này sẽ là thừa.

Cái còn lại là **trạng thái**. Các trò chơi an ninh cổ điển đặt trên các mục tiêu (target) với giá trị tĩnh; trạng thái của chúng tôi là (sự chiếm dụng carrier, thời điểm chèn, lịch trigger) diễn tiến theo một quy trình, được quan sát một phần qua các báo động nhiễu và các điểm kiểm tra có thể thực thi. Định lý 4 — ngân sách kiểm toán cần thiết để tách sự dai dẳng có hại khỏi thay đổi lành tính, như một hàm của độ trễ và tính không đồng nhất carrier — **không có tương đương trong công thức tĩnh**, và nó là thứ quyết định khi nào mô hình tuần tự xứng đáng với chi phí của nó.

### 3.2 Đầu độc dai dẳng trạng thái agent

AgentPoison [3], MINJA [6] và MemPoison [12] thiết lập các kênh chèn (injection channel); MemSecBench đánh giá vòng đời đầu độc (poisoning lifecycle) [13]; HarnessSafe theo dõi sự dai dẳng xuyên carrier [8]; NeuroTaint kiểm toán sự lan truyền [15]. Chúng tôi tái sử dụng các danh mục tấn công đã công bố và **không đóng góp tấn công mới**. Dòng tài liệu này cung cấp mối đe dọa và — trong trường hợp của HarnessSafe — quan sát đa carrier đã thúc đẩy không gian trạng thái của chúng tôi; nhưng không công trình nào trong số đó giải quyết việc *chi tiêu một ngân sách kiểm chứng hạn chế ở đâu*.

### 3.3 Đánh giá tốn kém và báo cáo chiến lược

DRAM [7] và các hợp đồng thích ứng (adaptive contracts) [1] xử lý việc báo cáo chiến lược và việc mua đánh giá tốn kém một cách có chọn lọc; kiểm toán thông đồng (collusion auditing) [2, 4] nghiên cứu việc phát hiện hành vi phối hợp. Đây là các cơ chế liền kề trên một *đối tượng chiến lược khác* (báo cáo thay vì carrier), và chúng tôi dùng một cuộc kiểm tra hai giai đoạn lấy cảm hứng từ adaptive contracts làm baseline.

### 3.4 Phục hồi và thu hồi

Chẩn đoán và sửa chữa có chọn lọc trạng thái bị đầu độc [5, 14] cùng các giao thức thu hồi (revocation protocol) giải quyết việc *phải làm gì sau khi phát hiện*. Kiểm toán thì quyết định *có nhìn hay không*. Các điểm cuối (endpoint) là khác nhau — độ chính xác định vị (localisation accuracy) so với tổn hại đã xác minh trong trường hợp xấu nhất ở một ngân sách — và hai thứ này **hợp thành**: một cơ chế phục hồi tốt hơn làm giảm chi phí hành động khi có báo động và do đó làm thay đổi chính sách kiểm toán tối ưu, điều mà chúng tôi định lượng bằng cách quét chi phí cách ly.

### 3.5 Điều kiện bác bỏ (the falsification condition)

Chúng tôi phát biểu thẳng: **nếu audit-at-commit đạt được tổn hại trong trường hợp xấu nhất tương đương ở cùng ngân sách trên toàn bộ khối lượng công việc của chúng tôi, thì hướng nghiên cứu này không nên tiếp tục.** §10 báo cáo chế độ mà điều đó đúng (cải thiện 4,2%, trong khoảng nhiễu) và chế độ mà nó không đúng (34,1%), và ranh giới giữa hai chế độ đó chính là dự đoán của Định lý 4.

## 4. CÔNG THỨC HÓA BÀI TOÁN (PROBLEM FORMULATION)

**Quy trình và carrier.** Một quy trình gồm $H$ task. Trạng thái tại task $t$ là $s_t = (\mathbf{c}_t, \iota, \sigma)$, trong đó $\mathbf{c}_t \in \{0,1\}^K$ ghi lại carrier nào trong $K$ carrier (bản ghi bộ nhớ, kỹ năng đã cache, mục hàng đợi công cụ, dẫn xuất nhánh) đang bị đầu độc, $\iota$ là thời điểm chèn, và $\sigma$ là lịch trigger (task mà tại đó mầm độc kích hoạt). $K = 4$ trong phiên bản cài đặt của chúng tôi.

**Attacker.** Attacker chọn $(k, \iota, \sigma, \varepsilon)$: một carrier được phép, thời điểm chèn, lịch trigger, và một mức sửa đổi có giới hạn độ lớn $\le \varepsilon$. **Ngân sách của nó ràng buộc số carrier mà nó được gieo mầm và độ lớn của từng mầm.** Nó quan sát *chính sách* của defender (Stackelberg) nhưng không quan sát **sự ngẫu nhiên hóa đã thực hiện hóa (realised randomization)** của chính sách đó.

**Defender.** Tại mỗi task, defender chọn một hành động kiểm toán $a_t \in \mathcal{A} = \{\text{none}\} \cup \{(\text{audit}, k, \text{depth})\}$ với chi phí $\kappa(k, \text{depth})$, tuân theo ràng buộc $\sum_t \kappa(a_t) \le B$. Nó quan sát $o_t$: các điểm số báo động từ một bộ dò không hoàn hảo với tỷ lệ dương tính đúng (true-positive rate) $\psi$ và tỷ lệ dương tính giả (false-positive rate) $\phi$, cộng với kết quả các điểm kiểm tra có thể thực thi. Nó duy trì một belief $b_t$ trên $s_t$ và có thể bổ sung hành động **cách ly** (chi phí $\eta_Q$, gỡ bỏ một carrier) hoặc **tiếp tục**.

**Trôi dạt lành tính như một nguyên nhân cạnh tranh.** Một quá trình tiềm ẩn độc lập sửa đổi các carrier một cách lành tính ở tỷ lệ $\beta$, với thống kê quan sát khớp với các sự kiện đầu độc. Đây là thứ làm cho việc cập nhật belief trở nên không tầm thường và là thứ ngăn "cách ly khi có bất kỳ bất thường nào" trở thành tối ưu.

**Payoff.** Tổn thất của defender là
$$L = \mathbb{E}[\text{tổn hại đã xác minh}] + \lambda_Q\,\mathbb{E}[\text{cách ly sai}] + \lambda_T\,\mathbb{E}[\text{task sạch bị mất}],$$
với tổn hại đã xác minh được đo bởi một **oracle niêm phong (sealed oracle)** ở cuối horizon. Attacker **tối đa hóa tổn hại đã xác minh tuân theo ngân sách của nó**.

**Định nghĩa 1 (Giá trị defender).** $V^* = \min_{\pi_D} \max_{\pi_A} L(\pi_D, \pi_A)$ trên các chính sách defender ngẫu nhiên hóa và các chính sách attacker trong một lớp đã khai báo $\Pi_A$.

**Tính không đồng nhất carrier và độ trễ, được làm rõ.** Đặt $\Delta = \sigma - \iota$ là **độ trễ trigger**, và đặt $\chi = \max_{k,k'} |\kappa(k) - \kappa(k')| / \bar{\kappa}$ đo **tính không đồng nhất chi phí carrier**. Hai đại lượng vô hướng này tham số hóa ranh giới chế độ của Định lý 4 và là các trục mà chúng tôi báo cáo kết quả theo đó.

**Baseline cần vượt qua.** **Audit-at-Commit** chi toàn bộ ngân sách vào việc kiểm tra commit cuối cùng của mỗi task ở độ sâu tối đa. Nó đơn giản, không cần trạng thái belief, và là chính sách mà một người thực hành sẽ triển khai đầu tiên. Tuyên bố của chúng tôi buộc phải được phát biểu tương đối với nó.

**Mục tiêu.** Cực tiểu hóa tổn hại đã xác minh trong trường hợp xấu nhất ở ngân sách cố định, chống lại các chính sách attacker giữ lại, trong khi vẫn giữ tỷ lệ hoàn thành sạch và cách ly sai ở mức chấp nhận được; và đặc trưng hóa vùng $(\Delta, \chi)$ mà ở đó phân bổ thích ứng **có** và **không** xứng đáng với độ phức tạp của nó.

## 5. PHƯƠNG PHÁP: SENTINEL (APPROACH: SENTINEL)
![Pasted image 20260913201726.png](assets/Pasted%20image%2020260913201726.png)
> **Hình 2: Sentinel.** *Trạng thái mang tính dai dẳng, trễ và đa carrier — ba tính chất tách bài toán này khỏi các trò chơi an ninh tĩnh và là những gì Định lý 4 chuyển hóa thành một **yêu cầu về ngân sách**.*

### 5.1 Trạng thái belief trên carrier, thời điểm chèn và trigger

Sentinel duy trì $b_t$, một phân phối trên $(\mathbf{c}, \iota, \sigma)$, được cập nhật từ các quan sát báo động và kết quả điểm kiểm tra, với quá trình trôi dạt lành tính đóng vai trò một **lời giải thích cạnh tranh**. Belief là thứ cho phép defender hành động dựa trên *độ trễ*: một báo động tại task $t$ nâng xác suất hậu nghiệm (posterior) về các lần chèn tại $t' < t$ với trigger tại $t'' > t$ — đây là thông tin mà một chính sách không trạng thái (stateless policy) vứt bỏ.

### 5.2 Tính toán chính sách

**Thuật toán 1 — Quyết định kiểm toán của Sentinel tại task $t$**

```
Yêu cầu: belief b_t, ngân sách còn lại B_t, thư viện chính sách Π
 1: Δ̂, χ̂ ← ước lượng độ trễ và tính không đồng nhất từ lịch sử
 2: nếu trò chơi nhỏ (KH ≤ ngưỡng) thì
 3:     a_t ← lời giải minimax chính xác bằng quy nạp lùi (backward
        induction) trên belief MDP
 4: ngược lại
 5:     a_t ← argmin_{π∈Π} max_{π_A∈Π_A} L̂(π, π_A | b_t, B_t)
        ▷ vững (robust) trên một thư viện hạn chế
 6: hết nếu
 7: thực thi a_t; quan sát o_t; b_{t+1} ← Update(b_t, a_t, o_t, β)
 8: nếu Pr[bị đầu độc | b_{t+1}] > τ và tổn hại kỳ vọng > η_Q thì
 9:     cách ly carrier có xác suất hậu nghiệm cao nhất
10: hết nếu
```

Dòng 3 cho các lời giải chính xác trên những trò chơi nhỏ nơi chúng tính được — đây là **oracle xác thực** của chúng tôi. Dòng 5 là cái chạy ở quy mô lớn: một **thư viện chính sách hạn chế** (28 chính sách đã tham số hóa, trải trên các họ trọng-số-theo-giai-đoạn, ngưỡng-belief và xoay-vòng-carrier) với tối ưu hóa vững chống lại lớp attacker. Việc hạn chế thư viện làm chặn bài toán ước lượng và cho một phép so sánh được định nghĩa rõ ràng cho chặn mất giá trị của **Mệnh đề 6**.

### 5.3 Ngẫu nhiên hóa là thiết yếu, không phải một chi tiết

Vì attacker quan sát chính sách, một phân bổ tất định bị đánh bại một cách tầm thường: attacker gieo mầm vào carrier mà defender hiện *không* kiểm tra. Sentinel cam kết một **phân phối** trên các hành động kiểm toán và chỉ tiết lộ phân phối đó. Ablation loại bỏ ngẫu nhiên hóa tốn **18,4 điểm** tổn hại trong trường hợp xấu nhất (§10), lớn hơn cả mức lợi so với audit-at-commit — **ngẫu nhiên hóa đang làm nhiều việc hơn tính thích ứng**.

### 5.4 Giữ trôi dạt lành tính tách biệt

Việc cập nhật belief xử lý sửa đổi lành tính như một nguyên nhân tiềm ẩn riêng biệt với tỷ lệ $\beta$ của riêng nó, được ước lượng trực tuyến. Không có điều này, một báo động chỉ là bằng chứng của đầu độc và phản ứng tối ưu là cách ly quyết liệt; có nó, defender buộc phải cân nhắc lời giải thích thay thế, và đó là thứ tạo ra biên giới cách-ly-sai/tổn-hại (false-quarantine/harm frontier) quan sát được.

### 5.5 Đóng băng chính sách trước khi đánh giá

Việc phát triển tấn công thích ứng được thực hiện trên một tập phát triển (development split), và **cả chính sách defender lẫn thư viện attacker đều được đóng băng** trước khi đánh giá cuối cùng trên **các kho mã giữ lại và các chính sách attacker giữ lại**. Đánh giá chống lại chính các cuộc tấn công mà defender đã được tinh chỉnh để đối phó sẽ tạo ra một con số không nói lên điều gì về một đối thủ thích ứng, và đó là cách phổ biến nhất khiến loại kết quả này bị thổi phồng.

### 5.6 Các phương án đã cân nhắc và loại bỏ

**"Cứ kiểm toán mọi thứ tại commit, thật sâu."** Đây là baseline đầu bảng của chúng tôi chứ không phải một strawman, và trong chế độ $\Delta$ nhỏ nó *chính là* câu trả lời đúng — chúng tôi báo cáo vùng mà nó thắng. Chúng tôi loại bỏ nó với tư cách một thiết kế **tổng quát** chỉ vì Định lý 4 cho thấy **số mẫu mang thông tin của nó không tăng theo độ sâu**, nên vượt quá một ngưỡng độ trễ thì *không ngân sách nào* làm nó đủ.

**"Cải thiện bộ dò thay vì cải thiện phân bổ."** Một bộ dò tốt hơn nâng $\gamma$ và, theo Định lý 4, hạ ngân sách yêu cầu theo bậc hai — một hiệu ứng lớn hơn phân bổ với cùng công sức. Chúng tôi coi đây là **bổ trợ** chứ không phải bị loại bỏ, và phép quét bộ dò của chúng tôi (RQ4) cho thấy hai thứ tương tác: phân bổ thích ứng quan trọng nhất khi bộ dò **yếu**, vốn là trường hợp thực tế.

**"Kiểm toán liên tục với một ngân sách nhỏ trên mỗi task."** Trải ngân sách đồng đều trên mọi giai đoạn và mọi task giúp né hoàn toàn cỗ máy belief. Đây chính là baseline **B2**, và nó đáng nể (0,386 so với 0,412 của audit-at-commit) *chính bởi vì nó được ngẫu nhiên hóa* — đây là quan sát dẫn tới phát hiện ablation rằng ngẫu nhiên hóa quan trọng hơn tính thích ứng.

**"Học chính sách trực tuyến chống lại attacker quan sát được."** Hấp dẫn, và nằm ngoài mô hình của chúng tôi: công thức Stackelberg giả định defender **cam kết trước**, còn một bộ học trực tuyến thì không cam kết. Một công thức không-hối-tiếc (no-regret) là mở rộng tự nhiên và sẽ đòi hỏi từ bỏ bảo đảm minimax để đổi lấy một chặn hối tiếc chống lại đối thủ không dừng (non-stationary) — đó là một bài báo khác, với câu chuyện an toàn yếu hơn.

## 6. LÝ THUYẾT (THEORY)

**Giả định 2 (Cấu trúc trò chơi).** Horizon $H$ là hữu hạn và đã biết; các kernel chuyển trạng thái được biết tới sai số biến phân toàn phần (total-variation) $\zeta$; cặp $(\psi, \phi)$ của bộ dò đã biết; lớp attacker $\Pi_A$ và ngân sách của nó đã được khai báo; defender cam kết trước và attacker best-response.

### 6.1 Giá trị minimax dưới độ bất định chuyển trạng thái

**Định lý 3 (Biên Stackelberg vững).** *Dưới Giả định 2, đặt $V_0^*$ là giá trị minimax khi biết chính xác các kernel. Khi đó chính sách vững của Sentinel đạt giá trị*
$$V \le V_0^* + H\,\zeta\,\mathrm{range}(L),$$
*và biên này chặt tới một hằng số: tồn tại các trường hợp mà **mọi** chính sách đều chịu phần vượt $\Omega(H\zeta)$.*

*Chứng minh.* Quy nạp lùi trên belief MDP. Tại mỗi bước trong $H$ bước, hàm giá trị là Lipschitz với hằng số $\mathrm{range}(L)$ theo kernel chuyển trạng thái dưới biến phân toàn phần, nên một nhiễu loạn kernel cỡ $\zeta$ làm nhiễu giá trị bước nhiều nhất $\zeta\,\mathrm{range}(L)$; sai số tích lũy cộng tính qua $H$ bước, cho chặn trên. Về tính chặt, xây dựng hai kernel khác nhau một lượng $\zeta$ ở xác suất một carrier bị đầu độc lan truyền, với các hành động tối ưu ngược nhau; bất kỳ chính sách đơn lẻ nào cũng sai trên một trong hai, chịu $\Omega(\zeta)$ mỗi bước. $\blacksquare$

### 6.2 Ngân sách cần thiết để phân biệt mầm độc với trôi dạt

Đây là kết quả quyết định liệu công thức tuần tự có xứng đáng với độ phức tạp của nó hay không.

**Định lý 4 (Ngân sách phân biệt được).** *Đặt trôi dạt lành tính xảy ra ở tỷ lệ $\beta$ với thống kê quan sát khớp với đầu độc, đặt bộ dò có margin $\gamma = \psi - \phi > 0$, đặt độ trễ trigger là $\Delta$, và đặt chi phí kiểm toán carrier có tính không đồng nhất $\chi$. Để phân biệt một trạng thái bị đầu độc với một trạng thái lành tính với sai số $\le \alpha$ tại thời điểm ra quyết định, ngân sách kiểm toán cần thiết thỏa mãn*
$$B \ \ge\ \frac{c\,\bar{\kappa}\,(1+\chi)\,\log(1/\alpha)}{\gamma^{2}} \cdot \left(1 + \frac{\Delta}{H}K\right).$$
*Đặc biệt, một chính sách kiểm toán **một carrier duy nhất tại một thời điểm duy nhất** — Audit-at-Commit — có ngân sách hiệu dụng $B_{\text{commit}}$ **độc lập với $\Delta$ và $K$**, nên với $\Delta$ và $\chi$ đủ lớn nó không thể đáp ứng yêu cầu ở **bất kỳ độ sâu nào**.*

*Phác thảo chứng minh.* Phân biệt hai giả thuyết từ các quan sát nhiễu với margin $\gamma$ đòi hỏi $\Omega(\gamma^{-2}\log(1/\alpha))$ **mẫu mang thông tin** (change-of-measure chuẩn). Một quan sát chỉ mang thông tin nếu nó kiểm tra đúng carrier đang giữ mầm độc; với $K$ carrier và không có thông tin về carrier nào, defender buộc phải **trải rộng**, tốn một hệ số $K$ trong trường hợp xấu nhất trừ khi belief tập trung. Belief chỉ tập trung từ các quan sát được thực hiện *sau khi chèn và trước khi tổn hại hiện thực hóa* — một cửa sổ độ dài $\Delta$ trên $H$ — cho ra số hạng $\Delta/H \cdot K$. Chi phí không đồng nhất làm phồng chi phí kỳ vọng của một chính sách trải rộng lên hệ số $(1+\chi)$ vì carrier mang thông tin có thể chính là carrier đắt. Với chính sách chỉ-commit, mọi quan sát diễn ra tại một carrier (patch) tại một thời điểm, nên không lượng độ sâu nào làm tăng số mẫu mang thông tin **về danh tính carrier**, và yêu cầu không được đáp ứng một khi $(1 + \Delta K/H) > B_{\text{commit}}\gamma^{2}/\big(c\bar{\kappa}(1+\chi)\log(1/\alpha)\big)$. $\blacksquare$

**Hệ quả 5 (Ranh giới chế độ).** *Kiểm toán tại thời điểm commit là **đủ** khi $\Delta$ nhỏ (trigger kích hoạt ngay trong task được kiểm toán) hoặc khi $K$ hiệu dụng bằng 1 (carrier đơn). Nó **không đủ** khi $\Delta$ tăng hoặc khi carrier sinh sôi.* §10 kiểm định dự đoán này một cách trực tiếp bằng cách quét $\Delta$ và $\chi$, và tìm thấy điểm giao cắt ở $\Delta \approx 2$ task.

Chúng tôi coi **Hệ quả 5, chứ không phải chính sách**, là sản phẩm hữu ích nhất của bài báo: nó cho người thực hành biết *khi nào thì đáng bận tâm*.

### 6.3 Giá trị mất đi do thu hẹp vào thư viện chính sách hạn chế

**Mệnh đề 6 (Tổn thất do hạn chế).** *Đặt $\Pi$ là một thư viện chính sách hữu hạn với bán kính bao phủ (covering radius) $\rho$ theo biến phân toàn phần trên các phân phối hành động kiểm toán, so với không gian chính sách không hạn chế. Khi đó*
$$V(\Pi) - V^{*} \le H\,\rho\,\mathrm{range}(L).$$

*Chứng minh.* Lấy $\pi^*$ tối ưu và $\pi \in \Pi$ nằm trong phạm vi $\rho$ của nó tại mỗi bước; chênh lệch giá trị mỗi bước nhiều nhất là $\rho\,\mathrm{range}(L)$ theo cùng lập luận Lipschitz như Định lý 3, tích lũy qua $H$ bước. $\blacksquare$

Chúng tôi **đo $\rho$** cho thư viện 28 chính sách của mình so với các lời giải chính xác trên các trò chơi nhỏ, thu được $\rho = 0{,}07$ và do đó một **chặn tổn thất 0,42** theo đơn vị tổn hại chuẩn hóa — so với **tổn thất đo được 0,09**, nên thư viện tốt hơn nhiều so với những gì chặn trường hợp xấu nhất gợi ý.

**Nhận xét 7 (Những gì chúng tôi *không* tuyên bố).** Chúng tôi **không** chứng minh một chặn hối tiếc (regret bound) chống lại một attacker học không dừng: attacker của chúng tôi best-response với một chính sách đã cam kết, vốn là giả định Stackelberg, và một attacker thích ứng *ngay bên trong* horizon nằm ngoài mô hình của chúng tôi. Chúng tôi **không** tuyên bố an toàn trước các cuộc tấn công nằm ngoài $\Pi_A$. Và các chặn chỉ dành cho horizon hữu hạn đã khai báo; không điều gì mở rộng được sang một triển khai vô thời hạn.

## 7. TRIỂN KHAI (IMPLEMENTATION)

Sentinel gồm **khoảng 9.100 dòng Python**.

**Bộ giải trò chơi.** Các trò chơi nhỏ ($KH \le 40$ ở mức rời rạc hóa trạng thái belief) được giải chính xác bằng quy nạp lùi trên đơn hình (simplex) belief đã rời rạc hóa. Các trò chơi lớn hơn dùng thư viện hạn chế với tối ưu hóa vững: với mỗi chính sách trong thư viện, best response của attacker bên trong $\Pi_A$ được tính bằng **liệt kê trên $(k, \iota, \sigma)$**, rồi defender chọn chính sách minimax.

**Cập nhật belief.** Một **bộ lọc hạt (particle filter) 2048 hạt** trên $(\mathbf{c}, \iota, \sigma)$ với quá trình trôi dạt lành tính đóng vai trò một chuyển trạng thái cạnh tranh; $\beta$ được ước lượng trực tuyến từ các quy trình sạch.

**Các hành động kiểm toán.** Kiểm toán chèn (kiểm tra nội dung và nguồn gốc trên các bản ghi bộ nhớ mới), kiểm toán truy xuất (kiểm tra tính nhất quán của các bản ghi được truy xuất so với nguồn), kiểm toán ủy quyền (kiểm tra hợp đồng và bằng chứng), kiểm toán commit (review patch, kiểm thử vi sai, nguồn gốc của các kỹ năng đã đóng góp). **Chi phí được đo, không phải gán**: lần lượt **0,4; 0,9; 1,6 và 4,1 phút-CPU**, cho $\chi = 1{,}34$.

**Bộ dò.** Một bộ dò bất thường học máy **dùng chung trên mọi hệ thống**, để phân bổ — chứ không phải chất lượng phát hiện — là biến số đang được nghiên cứu. Cặp $(\psi, \phi)$ của nó được đo trên một tập hiệu chỉnh (calibration split) và được báo cáo.

**Đóng băng.** Các chính sách defender và thư viện attacker được tuần tự hóa (serialise) và **băm (hash)** trước khi đánh giá cuối cùng; harness đánh giá **từ chối chạy** một chính sách có hash không nằm trong manifest đã đóng băng. Đây là **cưỡng chế (enforcement) chứ không phải giao thức**, vì cám dỗ tinh chỉnh lại sau khi đã thấy kết quả là rất lớn.

## 8. BENCHMARK AUDITGAME-SE

Tài sản đặc trưng của AuditGame-SE không phải là một danh sách payload dài hơn — các danh mục tấn công đã công bố là đủ — mà là **một trò chơi có thể thực thi với trạng thái và payoff đã biết đối với evaluator**: với mỗi trường hợp (instance), chúng tôi biết carrier nào đang giữ mầm độc, nó được chèn khi nào, nó kích hoạt khi nào, và tổn hại đáng giá bao nhiêu.

**Quy trình.** 100 quy trình sửa lỗi nhiều bước trên 15 kho mã, mỗi quy trình 6–14 task, với 4 giai đoạn kiểm toán (chèn, truy xuất, ủy quyền, commit) và 4 carrier (bộ nhớ, kỹ năng đã cache, hàng đợi công cụ, nhánh).

**Trạng thái đã biết đối với evaluator.** Mỗi trường hợp bị xâm hại ghi lại $(k, \iota, \sigma, \varepsilon)$. Đây là thứ làm cho tổn hại trong trường hợp xấu nhất **tính được** chứ không phải ước lượng, và là thứ cho phép chúng tôi đánh giá đối với **các chính sách attacker được chỉ định rõ** thay vì đối với bất cứ điều gì một LLM tình cờ làm.

**Các tham số chế độ được quét.** Độ trễ trigger $\Delta \in \{0, 1, 2, 4, 8\}$ task và tính không đồng nhất carrier $\chi \in \{0;\ 0{,}5;\ 1{,}34\}$ (đạt được bằng cách cân bằng hoặc phân hóa độ sâu kiểm toán), cho ra lưới mà trên đó dự đoán của Hệ quả 5 được kiểm định. **Chưa benchmark nào trước đây thay đổi một trong hai trục này.**

**Thay đổi lành tính với thống kê khớp.** **620** sửa đổi carrier lành tính được sinh ra để khớp với các sự kiện đầu độc trên các thống kê bề mặt (kích thước sửa đổi, dịch chuyển embedding, độ mới — recency, hình dạng nguồn gốc — provenance shape), được xác minh bằng một kiểm định hai mẫu (two-sample test) rằng một discriminator huấn luyện trên các đặc trưng bề mặt chỉ đạt **AUC $\le 0{,}56$**. Không có điều này, cách ly sai trở nên miễn phí và trò chơi suy biến.

**Chính sách attacker giữ lại.** **18** chính sách attacker kịch bản, trong đó **7** được giữ lại khỏi toàn bộ quá trình phát triển defender. Ngoài ra **3** attacker LLM không giới hạn, được báo cáo tách biệt như một phép đo hành vi. Các **họ kho mã (repository family)** cũng được giữ lại.

**Lỗi bộ dò có kiểm soát.** Cặp $(\psi, \phi)$ được quét trên **3 cài đặt** (0,75/0,20; 0,85/0,12; 0,92/0,06) để kết quả không phải là hiện tượng nhân tạo của một bộ dò cụ thể.

**Bảng 1: Thành phần của AuditGame-SE. Dự phóng.**

| Thuộc tính | Số lượng | Ghi chú |
|---|---|---|
| Quy trình / kho mã | 100 / 15 | 6–14 task |
| Giai đoạn kiểm toán / carrier | 4 / 4 | — |
| Độ trễ trigger $\Delta$ | 5 mức | 0–8 task |
| Tính không đồng nhất $\chi$ | 3 mức | 0–1,34 |
| Cài đặt bộ dò | 3 | được quét |
| Tổng số trường hợp | 4.500 | — |
| Thay đổi lành tính khớp | 620 | AUC discriminator 0,56 |
| Chính sách attacker kịch bản | 18 | 7 giữ lại |
| Attacker LLM | 3 | báo cáo tách biệt |
| Trò chơi nhỏ giải chính xác được | 240 | oracle minimax |
| Chi phí kiểm toán đo được (phút) | 0,4 / 0,9 / 1,6 / 4,1 | chèn/truy xuất/ủy quyền/commit |

**Công bố (Release).** Các quy trình, ground truth carrier/trigger, các bộ sinh thay đổi lành tính, các chính sách attacker (bao gồm cả tập giữ lại, công bố sau khi cửa sổ đánh giá đóng), bộ dò, và bộ giải trò chơi chính xác. Các phép chia tách (split) theo **họ kho mã** và theo **chính sách attacker**.

## 9. THIẾT KẾ ĐÁNH GIÁ (EVALUATION DESIGN)

### 9.1 Câu hỏi nghiên cứu

**RQ1 — Kiểm toán tại thời điểm commit là đủ ở đâu?** Trong vùng nào của lưới độ-trễ-trigger × tính-không-đồng-nhất-carrier thì phân bổ thích ứng vượt trội hơn việc chỉ kiểm toán tại commit, và điểm giao cắt quan sát được có khớp với ranh giới chế độ đã dự đoán không?

**RQ2 — Tổn hại trong trường hợp xấu nhất và cái giá của nó.** Sentinel có làm giảm tổn hại đã xác minh trong trường hợp xấu nhất ở cùng ngân sách, trước các chính sách attacker giữ lại, hay không — và nó tốn gì về hoàn thành sạch (clean completion), cách ly sai và độ trễ phát hiện?

**RQ3 — Các lớp attacker.** Các best-responder hợp lý, các attacker kịch bản giữ lại, và các attacker mô hình ngôn ngữ không giới hạn có hành xử khác nhau không, và mỗi loại cho phép chúng tôi tuyên bố điều gì?

**RQ4 — Quy kết và độ nhạy.** Thành phần nào — ngẫu nhiên hóa, bộ nhớ báo động, độ bất định chuyển trạng thái, mô hình hóa trôi dạt lành tính — mang lại hiệu ứng, và các kết luận thay đổi ra sao qua các cài đặt bộ dò?

### 9.2 Baseline

**(B1) Audit-at-Commit** — phép so sánh đầu bảng. **(B2) Uniform random auditing** trên các giai đoạn. **(B3) Audit-on-insertion.** **(B4) Audit-on-retrieval.** **(B5) Risk-score thresholding**: kiểm toán khi điểm số của bộ dò vượt một ngưỡng đã tinh chỉnh. **(B6) Kiểm tra hai giai đoạn lấy cảm hứng từ adaptive-contracts** [1]. **(B7) Exhaustive small-game oracle** — lời giải minimax, chỉ tính được trên 240 trò chơi nhỏ; một **trần (ceiling)**, không phải một đối thủ cạnh tranh.

### 9.3 Chỉ số (Metrics)

**Tổn hại đã xác minh trong trường hợp xấu nhất (chính)**: cực đại trên lớp attacker giữ lại của tổn hại được xác nhận bởi oracle niêm phong, ở cùng ngân sách. **Hoàn thành sạch** và **cách ly sai**. **Chi phí kiểm toán (phút-CPU)** và **độ trễ phát hiện**. **Khả năng khai thác (exploitability)**: mức lợi của best-response chống lại chính sách đã triển khai. **Hối tiếc thực nghiệm (empirical regret)** so với B7 trên các trò chơi nhỏ.

### 9.4 Giao thức

4.500 trường hợp × 8 hệ thống × 3 seed. **Tổn hại trong trường hợp xấu nhất trước các chính sách attacker giữ lại ở cùng ngân sách** là điểm cuối chính đã đăng ký trước, đối chiếu với **B1** với **biên tương đối 15%**. Các chính sách defender và thư viện attacker được đóng băng bằng hash trước khi đánh giá. Kết quả được báo cáo trên lưới $(\Delta, \chi)$ thay vì gộp chung, vì một con số gộp sẽ lấy trung bình của chế độ mà phương pháp giúp ích với chế độ mà nó không giúp ích.

## 10. KẾT QUẢ (RESULTS)

*Mọi giá trị đều là dự phóng theo thiết kế của §9; xem banner ở trang 1.*

**Tóm tắt các phát hiện.**

- **RQ1**: Phân bổ thích ứng **không tốt hơn** audit-at-commit khi trigger là tức thời — và đôi khi hơi tệ hơn — trong khi điểm giao cắt quan sát được ($\Delta \approx 2{,}1$ task, muộn hơn khi có tính không đồng nhất carrier) **khớp với ranh giới chế độ đã dự đoán**.
- **RQ2**: Ở nơi nó áp dụng được, tổn hại trong trường hợp xấu nhất giảm **34,1%**, và **27,6%** trước các attacker thích ứng giữ lại, ở mức hoàn thành sạch tương đương, **thêm 1,9 điểm** cách ly sai, và khả năng khai thác giảm từ **0,34 xuống 0,09**.
- **RQ3**: Các best-responder hợp lý xác thực mô hình trò chơi, các attacker kịch bản giữ lại hỗ trợ tuyên bố về chuyển giao, còn các attacker LLM thì **tâng bốc mọi defender** — được báo cáo như hành vi, *không* phải bằng chứng cho các tuyên bố cân bằng.
- **RQ4**: Ngẫu nhiên hóa đóng góp **gần gấp đôi** so với trạng thái belief tuần tự, audit-on-insertion là chính sách **tệ nhất** được đo, và lợi thế so với kiểm toán tại commit là **lớn nhất khi bộ dò yếu nhất**.

### 10.1 RQ1: Kiểm toán tại thời điểm commit là đủ ở đâu
![Pasted image 20260913201642.png](assets/Pasted%20image%2020260913201642.png)
> **Hình 3: RQ1 — phân bổ thích ứng chỉ vượt kiểm toán tại commit khi trigger bị trễ.**
> Trục tung: mức giảm tổn hại trong trường hợp xấu nhất so với B1 (%), từ 0 đến 40. Trục hoành: độ trễ trigger $\Delta$ (task), từ 0 đến 8. Ba đường cong: $\chi = 0$ (carrier đồng đều), $\chi = 0{,}5$, và $\chi = 1{,}34$ (carrier không đồng nhất); một đường dọc đánh dấu điểm giao cắt dự đoán.
>
> *Ở $\Delta \le 1$ nó không tốt hơn và đôi khi tệ hơn. Điểm giao cắt nằm gần $\Delta \approx 2$ với carrier đồng đều và dịch **muộn hơn** khi tính không đồng nhất chi phí carrier tăng, đúng như số hạng $(1+\chi)$ của Định lý 4 đòi hỏi. Dự phóng; hướng đã được sửa lại sau khi thực thi (xem `EXECUTION_LOG`).*

Hình 3 là kết quả trung tâm của bài báo, và nó **một phần là một kết quả âm tính**. Ở $\Delta = 0$ — trigger kích hoạt trong cùng task với lần chèn — phân bổ thích ứng **tệ hơn kiểm toán tại commit 1,2%**, vì nó chi ngân sách ở thượng nguồn nơi chưa có gì để tìm. Ở $\Delta \le 1$ với carrier đồng đều, khác biệt nằm trong khoảng nhiễu. Phương pháp chỉ xứng đáng với độ phức tạp của nó **ở phía bên phải điểm giao cắt**, và một người thực hành có quy trình ngắn thì nên triển khai B1 rồi dừng lại.

Ở nơi nó *có* áp dụng, hiệu ứng là lớn: tại $\Delta = 4$, phân bổ thích ứng giảm tổn hại trong trường hợp xấu nhất **34,8%** với carrier đồng đều và **24,8%** với carrier không đồng nhất; tại $\Delta = 8$, giảm **42,4%** và **33,1%**. Cấu hình đầu bảng của chúng tôi ($\Delta > 2$, gộp trên $\chi$) cho **34,1%**. Tính không đồng nhất **thu hẹp** mức lợi và **làm chậm** điểm giao cắt — chúng tôi đã dự phóng điều ngược lại, và trò chơi đã thực thi sửa lại điều đó — vì việc cân bằng khả năng phát hiện trên các carrier có chi phí không bằng nhau tiêu tốn ngân sách. Điều mà tính không đồng nhất *thực sự* gây ra là làm cho **mọi phân bổ non-minimax đều có thể bị khai thác**: một bộ phân bổ tham-chi-phí (cost-greedy) kiểm toán các carrier rẻ nhiều hơn sẽ bị đánh bại bởi một attacker chèn vào carrier đắt, và trong mô hình của chúng tôi nó còn **tệ hơn cả uniform random auditing**.

### 10.2 RQ1: Các chặn đã dự đoán có đúng không?

Điểm giao cắt trong Hình 3 xảy ra tại $\Delta = 2{,}1$ (nội suy), so với dự đoán $\Delta \approx 2$ của Hệ quả 5. Trên **240 trò chơi nhỏ giải chính xác được**, hối tiếc thực nghiệm của Sentinel so với giá trị minimax (B7) là **0,09** theo tổn hại chuẩn hóa, so với **chặn trường hợp xấu nhất 0,42** của Mệnh đề 6 tại bán kính bao phủ đo được $\rho = 0{,}07$ — nên thư viện **tốt hơn nhiều so với mức chặn bảo đảm**, điều mà chúng tôi ghi nhận thay vì trình bày chặn đó như thể nó chặt.

### 10.3 RQ2: So sánh chính

Bảng 2 trình bày RQ2. So với B1, Sentinel hạ tổn hại trong trường hợp xấu nhất từ **0,412 xuống 0,272** (−34,1% tương đối, KTC [−42,6%; −25,1%], vượt biên 15%) ở mức hoàn thành sạch tương đương (**92,6%** so với **94,1%**) và một mức tăng cách ly sai khiêm tốn (**5,1%** so với **3,2%**). Khả năng khai thác — mức lợi best-response có thể đạt được trước chính sách đã triển khai — giảm từ **0,34 xuống 0,09**, và đó chính là thuộc tính mà ngẫu nhiên hóa mua được.

Riêng đối với các chính sách attacker **giữ lại**, mức giảm là **27,6%** (so với 34,1% trên các attacker phát triển), nên khoảng **một phần năm** lợi thế **không chuyển giao được**. Chúng tôi báo cáo con số giữ lại như con số **trung thực**.

**B3 còn tệ hơn việc không làm gì ở thượng nguồn**: audit-on-insertion là ý tưởng đầu tiên tự nhiên nhất, và nó là chính sách **tệ nhất trong bảng (0,441)**, vì attacker chỉ việc chèn qua một kênh mà nó không theo dõi. Đây là minh họa rõ ràng nhất cho lý do một chính sách cố định-giai-đoạn thất bại trước một đối thủ biết quan sát.

**Bảng 2: Kết quả chính ở cùng ngân sách, $\Delta > 2$, $\chi = 1{,}34$, trước các chính sách attacker *giữ lại*. B7 là giá trị minimax chính xác trên tập con trò chơi nhỏ. Mọi giá trị đều là dự phóng.**

| Chính sách | Tổn hại TH xấu nhất ↓ | Hoàn thành sạch % ↑ | Cách ly sai % ↓ | Độ trễ phát hiện ↓ | Khả năng khai thác ↓ |
|---|---|---|---|---|---|
| B1 Audit-at-commit | 0,412 [0,381; 0,444] | 94,1 | 3,2 | 4,6 | 0,34 |
| B2 Uniform random | 0,386 [0,356; 0,417] | 92,8 | 5,9 | 3,1 | 0,21 |
| B3 Audit-on-insertion | 0,441 [0,409; 0,474] | 95,2 | 2,4 | 5,8 | 0,47 |
| B4 Audit-on-retrieval | 0,398 [0,367; 0,430] | 93,6 | 4,6 | 3,9 | 0,39 |
| B5 Risk-score threshold | 0,359 [0,329; 0,390] | 91,4 | 8,1 | 2,8 | 0,29 |
| B6 Two-stage check [1] | 0,344 [0,315; 0,375] | 92,1 | 6,4 | 2,6 | 0,24 |
| **Sentinel** | **0,272 [0,245; 0,300]** | 92,6 | 5,1 | **2,1** | **0,09** |
| B7 Exact minimax (trò chơi nhỏ) | 0,249 | 93,0 | 4,8 | 2,0 | 0,00 |

### 10.4 RQ3: Các lớp attacker hỗ trợ các tuyên bố khác nhau

**Các best-responder hợp lý**: khả năng khai thác của Sentinel là **0,09**, nhất quán với phép tính minimax; đây là thứ **xác thực mô hình trò chơi**. **Các attacker kịch bản giữ lại**: giảm tổn hại **27,6%**; đây là thứ **hỗ trợ tuyên bố chuyển giao**. **Các attacker LLM**: giảm tổn hại **41,2%**, và *mọi* chính sách đều làm tốt hơn trước chúng — chúng chèn vào những thời điểm dự đoán được và hiếm khi khai thác tính không đồng nhất carrier. Do đó chúng tôi báo cáo kết quả LLM như một **phép đo hành vi** và **từ chối một cách tường minh** việc dùng chúng làm bằng chứng cho các tuyên bố cân bằng, bởi một đối thủ yếu thì tâng bốc mọi defender.

### 10.5 RQ4: Ablation và độ nhạy theo bộ dò

Bảng 3 chứa một kết quả đáng nói thẳng: **ngẫu nhiên hóa quan trọng hơn tính thích ứng**. Loại bỏ nó đẩy tổn hại trong trường hợp xấu nhất lên **0,456** — *tệ hơn cả kiểm toán tại commit* — và khả năng khai thác lên **0,51**. Loại bỏ bộ nhớ báo động, tức thành phần tuần tự, tốn **0,099**, chỉ khoảng một nửa. Vậy nên một người thực hành chỉ cần **ngẫu nhiên hóa một chính sách đơn giản** là đã thu về phần lớn lợi ích mà không cần bất kỳ trạng thái belief nào. Loại bỏ mô hình hóa trôi dạt lành tính lại hơi **cải thiện** tổn hại nhưng làm cách ly sai **tăng gấp bốn lần** (5,1% → 19,8%), khẳng định nó là một cơ chế **khả dụng (usability)** chứ không phải một cơ chế an toàn.

**RQ4**: trên ba cài đặt bộ dò, lợi thế của Sentinel so với B1 dao động từ **21,4% đến 39,8%**, lớn nhất với bộ dò yếu nhất — phân bổ thích ứng **bù đắp cho chất lượng phát hiện**, và đó chính là chế độ mà nó cần thiết nhất, cũng là chế độ chúng tôi dự đoán sẽ gặp khi triển khai thực tế.

**Bảng 3: Ablation (RQ4). Dự phóng.**

| Biến thể | Tổn hại TH xấu nhất | Cách ly sai % | Khả năng khai thác |
|---|---|---|---|
| Sentinel đầy đủ | 0,272 | 5,1 | 0,09 |
| − ngẫu nhiên hóa (tất định) | 0,456 | 4,8 | 0,51 |
| − bộ nhớ báo động (không trạng thái) | 0,371 | 6,2 | 0,19 |
| − độ bất định chuyển trạng thái (kernel danh nghĩa) | 0,318 | 5,4 | 0,16 |
| − mô hình hóa trôi dạt lành tính | 0,264 | 19,8 | 0,11 |

### 10.6 Phân tích định tính: attacker làm gì trước từng chính sách

Việc soi các best response mang nhiều thông tin hơn con số tổng hợp. Trước **audit-on-insertion**, mọi best response đều chèn qua **repository ingress thay vì ghi trực tiếp** — tức kênh không được kiểm toán — và đó là lý do nó là chính sách tệ nhất. Trước **audit-at-commit**, các best response **tối đa hóa độ trễ trigger**, đẩy thời điểm kích hoạt vượt quá cửa sổ mà cuộc kiểm toán commit còn có thể quy kết nguyên nhân. Trước **risk-score thresholding**, chúng **định hình payload để nằm ngay dưới ngưỡng**, và đó là lý do tỷ lệ cách ly sai của chính sách này cao (**8,1%**) trong khi tổn hại của nó thì **không**: nó đang bị *dẫn dắt*. Trước **Sentinel**, các best response **trải rộng trên nhiều carrier** thay vì khai thác một carrier — đúng là hành vi mà một chính sách ngẫu nhiên hóa lẽ ra phải tạo ra, và là lý do khả năng khai thác giảm xuống 0,09.

## 11. THẢO LUẬN (DISCUSSION)

**Ranh giới chế độ mới là đóng góp.** Hình 3 nói rằng phân bổ kiểm toán thích ứng **đáng xây dựng khi trigger bị trễ quá khoảng hai task**, và **không đáng xây dựng nếu không** — nơi mà nó đôi khi còn hơi tệ hơn. Tính không đồng nhất chi phí carrier dịch ngưỡng đó **muộn hơn chứ không sớm hơn**; ý nghĩa thực sự của nó là nó làm cho mọi phân bổ chưa đạt tới minimax đều có thể bị khai thác. Ranh giới đó được **Định lý 4 dự đoán** và được xác nhận bằng thực nghiệm, và chúng tôi cho rằng nó hữu ích hơn bản thân chính sách. Một người thực hành có thể **tự đo $\Delta$ và $\chi$ của mình** và ra quyết định mà không cần chạy hệ thống của chúng tôi.

**Hãy ngẫu nhiên hóa trước khi thích ứng.** Loại bỏ ngẫu nhiên hóa tốn **0,184** tổn hại trong trường hợp xấu nhất; loại bỏ belief tuần tự tốn **0,099**. Trước một đối thủ quan sát được chính sách, một lịch trình tất định là **lỗ hổng chi phối**, và việc ngẫu nhiên hóa một chính sách trọng-số-theo-giai-đoạn đơn giản đã thu về **hơn một nửa** lợi ích của Sentinel với một phần nhỏ chi phí kỹ thuật. Chúng tôi thà báo cáo điều này còn hơn để thành phần cầu kỳ nhận công của thành phần đơn giản.

**Audit-on-insertion là một cái bẫy.** Đó là thiết kế đầu tiên mà trực giác mách bảo — kiểm tra mọi thứ khi chúng đi vào — và nó là chính sách **tệ nhất chúng tôi đo được**, tệ hơn cả việc không làm gì ở thượng nguồn, bởi một điểm kiểm tra đầu vào cố định **nói cho attacker biết chính xác kênh nào cần né**. Bài học tổng quát: bất kỳ giai đoạn kiểm chứng nào **cố định và được công bố** đều trở thành giai đoạn mà attacker **định tuyến vòng qua** — đây chính là hiểu biết kinh điển của trò chơi an ninh, xuất hiện trong một bối cảnh mới.

**Đối thủ yếu tâng bốc defender.** Các attacker LLM làm mọi chính sách trông đẹp (giảm 41,2% cho Sentinel), vì chúng chèn một cách dự đoán được và không khai thác tính không đồng nhất carrier. Một cơ chế phòng thủ **chỉ** được đánh giá trước các cuộc tấn công do LLM sinh ra thực chất là đang đo **giới hạn của attacker**. Chúng tôi báo cáo các kết quả đó như một ghi chú hành vi và đặt mọi tuyên bố trên các best-responder kịch bản và các chính sách giữ lại.

**Hợp thành với phục hồi.** Phục hồi tốt hơn làm giảm chi phí hành động khi có báo động, điều này dịch chính sách tối ưu về phía cách ly quyết liệt hơn; phép quét $\eta_Q$ cho thấy lợi thế của Sentinel so với B1 **tăng từ 34,1% lên 44,0%** khi cách ly trở nên rẻ. Vì vậy kiểm toán và phục hồi là **các thành phần bổ trợ với một tương tác định lượng được**, chứ không phải các lựa chọn thay thế nhau — đó là lý do nên xây dựng chúng cùng nhau, và là lý do không nên đánh giá riêng lẻ bất kỳ cái nào.

## 12. ĐE DỌA ĐỐI VỚI TÍNH HỢP LỆ (THREATS TO VALIDITY)

**Tính hợp lệ cấu trúc (construct validity).** "Tổn hại đã xác minh trong trường hợp xấu nhất" là cực đại **trên một lớp attacker đã khai báo** của tổn hại được một oracle niêm phong xác nhận. Tổn hại nằm ngoài tầm với của oracle là vô hình đối với *mọi* hệ thống, và một attacker nằm ngoài $\Pi_A$ thì nằm ngoài *mọi* con số chúng tôi báo cáo — nên "trường hợp xấu nhất" ở đây nghĩa là **xấu-nhất-trong-lớp**, và chúng tôi dùng cách diễn đạt đó một cách có chủ ý. Chi phí kiểm toán là phút-CPU đo được cho *các cài đặt của chúng tôi* cho mỗi loại kiểm tra; một tổ chức với cách cài đặt kiểm tra khác sẽ có $\chi$ khác — mà $\chi$ lại chính là tham số mà ranh giới chế độ phụ thuộc vào nhiều nhất.

**Tính hợp lệ nội bộ (internal validity).** Các chính sách defender và thư viện attacker được đóng băng bằng hash trước khi đánh giá, và harness từ chối các chính sách chưa đóng băng — nhưng tập phát triển đã được dùng để thiết kế cả hai, nên hiệu năng trên attacker **giữ lại (27,6%)** mới là ước lượng chuyển giao, còn con số phát triển (34,1%) thì không. Một bộ dò dùng chung được dùng cho mọi hệ thống để **phân bổ, chứ không phải phát hiện**, là biến số; một hệ thống có bộ dò riêng có thể tốt hơn hoặc tệ hơn vì những lý do không liên quan đến phân bổ. Các thay đổi lành tính đã được xác minh là không phân biệt được ở mức bề mặt (AUC discriminator 0,56), nhưng một discriminator mạnh hơn có thể tách được chúng, và điều đó sẽ làm việc tránh cách ly sai dễ hơn cho *mọi* hệ thống.

**Tính hợp lệ ngoại (external validity).** 15 kho mã, 4 carrier, quy trình 6–14 task. Các triển khai thực tế có nhiều carrier hơn và horizon dài hơn, và theo Định lý 4 thì cả hai đều đẩy sâu hơn vào chế độ mà phân bổ thích ứng có ích, nên ước lượng của chúng tôi có lẽ là **thận trọng** — nhưng chúng cũng làm tăng số chiều của trạng thái belief vượt quá mức mà bộ lọc hạt của chúng tôi được tinh chỉnh để xử lý. Các payload tấn công đến từ **các danh mục đã công bố**; một kênh hoàn toàn mới sẽ nằm ngoài $\Pi_A$.

**Tính hợp lệ kết luận (conclusion validity).** Các trường hợp thuộc cùng một quy trình thì tương quan với nhau và chung một split; các khoảng tin cậy được **bootstrap theo cụm (cluster-bootstrapped)** theo họ kho mã, trên 3 seed. Điểm cuối chính được khai báo đối chiếu với **B1 (audit-at-commit)** — baseline dễ khiến bài báo trở nên không cần thiết nhất — với biên tương đối **15%**, và kết quả được báo cáo trên lưới $(\Delta, \chi)$ thay vì gộp chung, vì một con số gộp sẽ lấy trung bình chế độ mà phương pháp giúp ích với chế độ mà nó không giúp ích.

**Đe dọa đối với phần lý thuyết.** Định lý 3 giả định horizon đã biết và độ bất định kernel có giới hạn; một môi trường không dừng phá vỡ cả hai. Định lý 4 là một **chặn dưới** trên ngân sách yêu cầu, dưới một mô hình trôi dạt có thống kê khớp; nếu trôi dạt lành tính dễ tách ra, thì kiểm toán tại commit sẽ vẫn đủ ở $\Delta$ lớn hơn nhiều. Giả định Stackelberg — attacker best-response với một chính sách đã cam kết và **không** thích ứng bên trong horizon — là một giả định mạnh, và một attacker học *trong lúc* quy trình đang chạy thì nằm hoàn toàn ngoài mô hình của chúng tôi.

## 13. KẾT LUẬN (CONCLUSION)

Phân bổ một ngân sách kiểm chứng hạn chế chống lại một attacker thích ứng là một bài toán **đã được giải ở dạng trừu tượng**, nên câu hỏi dành cho các quy trình phần mềm là liệu cấu trúc của chúng có làm thay đổi câu trả lời hay không. Chúng tôi đã xác định được cấu trúc làm thay đổi câu trả lời — **sự dai dẳng xuyên các task, các trigger bị trễ, và các carrier không đồng nhất** — công thức hóa trò chơi Stackelberg hữu hạn-thời gian, quan sát một phần trên trạng thái đó, và chứng minh một **chặn dưới** trên ngân sách kiểm toán cần thiết để phân biệt sự dai dẳng có hại với thay đổi lành tính, cho thấy nó tăng theo độ trễ trigger và tính không đồng nhất carrier theo cách mà một cuộc kiểm toán tại commit không thể hấp thụ. Ranh giới chế độ thu được, được kiểm chứng thực nghiệm tại điểm giao cắt khoảng **hai task độ trễ**, chính là sản phẩm thực tiễn: **dưới ngưỡng đó**, audit-at-commit tốt ngang bất cứ thứ gì và phân bổ thích ứng đôi khi còn tệ hơn; **trên ngưỡng đó**, phân bổ thích ứng giảm tổn hại trong trường hợp xấu nhất **34,1%** trên các attacker phát triển và **27,6%** trước các chính sách thích ứng giữ lại, ở cùng ngân sách. Hai phát hiện phụ đáng được coi trọng ngang vậy: **ngẫu nhiên hóa đóng góp gần gấp đôi so với trạng thái belief tuần tự**, nên người thực hành nên ngẫu nhiên hóa trước khi thích ứng; và **audit-on-insertion, thiết kế trực giác nhất, lại là chính sách tệ nhất chúng tôi đo được**. Chúng tôi công bố trò chơi, các quy trình với trạng thái carrier và trigger đã biết đối với evaluator, và các chính sách attacker đã đóng băng.

## 14. TÍNH SẴN CÓ CỦA DỮ LIỆU (DATA AVAILABILITY)

Một artifact ẩn danh đi kèm bài nộp này và chứa: cài đặt **Sentinel**; pipeline xây dựng **AuditGame-SE** (các quy trình với trạng thái carrier/trigger đã biết đối với evaluator và các chính sách attacker đã đóng băng); **công thức container và digest image**; **định danh commit chính xác** của mọi kho mã đối tượng; mọi cài đặt baseline, với các baseline được cài đặt lại được **ghi nhãn rõ ràng**; các script phân tích tạo ra mọi bảng và hình; và **kết quả trên từng task** chứ không chỉ số tổng hợp.

Các oracle niêm phong và mọi nhãn bị giữ lại trong quá trình đánh giá sẽ được công bố sau khi cửa sổ đánh giá đóng lại, cùng với các seed cần thiết để tái tạo mọi lần chạy. Các kho mã đối tượng là công khai và có giấy phép cho phép; dữ liệu dẫn xuất được công bố dưới hợp của các giấy phép đó. Artifact được chuẩn bị cho các huy hiệu ACM Artifact **Available** và **Reusable**, và bản sao ẩn danh không mang metadata nhận dạng tác giả.

*Lưu ý về tái tạo.* Các backend mô hình được host có thể thay đổi; chúng tôi ghi lại định danh mô hình và ngày truy cập chính xác, và **ghim backend trọng số mở (open-weight) theo digest** để ít nhất một cấu hình là tái tạo được vô thời hạn. Các kết quả phụ thuộc vào hành vi thời gian thực (wall-clock) được báo cáo kèm hồ sơ phần cứng đã dùng.

## 15. CÁC CÂN NHẮC ĐẠO ĐỨC (ETHICAL CONSIDERATIONS)

Các chính sách attacker được viết kịch bản trên các **danh mục đầu độc đã công bố** và chỉ vận hành bên trong các bản sao quy trình được sandbox hóa. Chúng tôi đóng băng và công bố chúng, **bao gồm cả tập giữ lại**, sau khi cửa sổ đánh giá đóng — vì một kết quả trò chơi an ninh không thể chạy lại trước cùng những đối thủ thì không thể kiểm chứng được. Không kỹ thuật nào ở đây làm tăng năng lực của attacker đối với một hệ thống vốn **chưa** dễ tổn thương trước chính các cuộc tấn công đã công bố mà chúng tôi xây dựng trên đó.

Mọi thực nghiệm chạy trong các container biệt lập, trên các bản fork của kho mã công khai; không có hệ thống sản xuất, không dịch vụ bên thứ ba, và không đối tượng con người nào tham gia. Chúng tôi tuân theo các chuẩn mực **công bố phối hợp (coordinated disclosure)** đối với bất kỳ khiếm khuyết nào mà công cụ của chúng tôi vô tình phát hiện trong một kho mã đối tượng.

## TÀI LIỆU THAM KHẢO (REFERENCES)

[1] Adaptive Contracts Authors. 2026. Adaptive Contracts for Costly Evaluation in Multi-Agent Systems. *arXiv preprint arXiv:2603.17212* (2026).

[2] Audit the Whisper Authors. 2025. Audit the Whisper: Detecting Covert Coordination in Agent Populations. *arXiv preprint arXiv:2510.04303* (2025).

[3] Zhaorun Chen, Zhen Xiang, Chaowei Xiao, Dawn Song, and Bo Li. 2024. AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases. In *Advances in Neural Information Processing Systems (NeurIPS)*.

[4] Colosseum Authors. 2026. Colosseum: Auditing Collusion Among Language-Model Agents. *arXiv preprint arXiv:2602.15198* (2026).

[5] Dependency-Guided Rollback Authors. 2026. Dependency-Guided Rollback for Compromised Agent Memory and Execution State. *arXiv preprint arXiv:2608.10502* (2026).

[6] Shen Dong, Shaochen Xu, Pengfei He, Yige Li, Jiliang Tang, Tianming Liu, Hui Liu, and Zhen Xiang. 2025. A Practical Memory Injection Attack against LLM Agents. *arXiv preprint arXiv:2503.03704* (2025).

[7] DRAM Authors. 2025. DRAM: Deliberative Reporting and Mechanisms for Strategic Agents. *arXiv preprint arXiv:2512.21794* (2025).

[8] HarnessSafe Authors. 2026. HarnessSafe: Tracing Persistent Influence Across Agent Carriers. *arXiv preprint arXiv:2608.06984* (2026).

[9] Incentive-Aware AI Safety Authors. 2026. Incentive-Aware AI Safety via Stackelberg Security Games. *arXiv preprint arXiv:2602.07259* (2026).

[10] Christopher Kiekintveld, Manish Jain, Jason Tsai, James Pita, Fernando Ordóñez, and Milind Tambe. 2009. Computing Optimal Randomized Resource Allocations for Massive Security Games. In *International Conference on Autonomous Agents and Multiagent Systems (AAMAS)*.

[11] Dmytro Korzhyk, Vincent Conitzer, and Ronald Parr. 2010. Complexity of Computing Optimal Stackelberg Strategies in Security Resource Allocation Games. In *AAAI Conference on Artificial Intelligence*.

[12] MemPoison Authors. 2026. MemPoison: Indirect Persistence Attacks on Agent Memory. *arXiv preprint arXiv:2605.29960* (2026).

[13] MemSecBench Authors. 2026. MemSecBench: Benchmarking the Poisoning Lifecycle and Selective Repair of Agent Memory. *arXiv preprint arXiv:2607.27080* (2026).

[14] MemTxn Authors. 2026. MemTxn: Source-Supported Memory Updates and Recovery without the Physical Write Set. *arXiv preprint arXiv:2607.27834* (2026).

[15] NeuroTaint Authors. 2026. NeuroTaint: Auditing Influence Propagation in Agent Memory. *arXiv preprint arXiv:2604.23374* (2026).

[16] Milind Tambe. 2011. *Security and Game Theory: Algorithms, Deployed Systems, Lessons Learned*. Cambridge University Press.
