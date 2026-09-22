# Parameter Estimation Methodology for Sentinel / AuditGame-SE

**Đề tài:** *Where to Look: Audit-Allocation Games against Adaptive Persistent Poisoning in Software Workflows* (FSE-2027-15)
**Học viên:** Nguyễn Hữu Trưởng · **Giảng viên hướng dẫn:** TS. Lê Xuân Bách
**Đơn vị:** RAISE Lab, Trường Đại học Bách khoa – ĐHQG-HCM
**Ngày:** 22/09/2026

---

## Tóm tắt

Mô hình Sentinel phụ thuộc vào khoảng hai mươi tham số — chi phí audit theo carrier, chất lượng detector, tốc độ trôi lành tính, trọng số hàm mất mát, và các hằng số trong những cận lý thuyết. Trong bản thảo gốc, phần lớn các giá trị này được khai báo mà không có nguồn gốc thực nghiệm. Vì đóng góp chính của đề tài là một ranh giới vùng tham số hoá bởi độ trễ $\Delta$ và độ dị tính chi phí $\chi$, một tham số không có nguồn gốc làm suy yếu trực tiếp tuyên bố chính.

Báo cáo này đề xuất một khung phân loại tham số theo **bốn phương thức xác lập** — đo trực tiếp, neo rồi quét, suy dẫn từ thiết kế, và khử tham số bằng cách phát biểu lại kết luận dưới dạng ngưỡng — cùng ba nguyên tắc thực hiện: tiền đăng ký có kiểm chứng được, đóng băng theo nhóm phụ thuộc, và tách vai trò "thế giới" khỏi vai trò "mô hình của defender". Khung này được áp dụng cho toàn bộ tham số của mô hình.

Kết quả gồm hai phần. **Thứ nhất**, tám đại lượng đã được ước lượng; trong đó ngưỡng chọn carrier $\tau_{\text{sel}}$ được nâng từ tham số chọn lên đại lượng đo, và điểm hoà vốn của detector được xác định là $d'^\* = 2{,}85$ tại $\Delta = 2$. **Thứ hai**, với chín tham số chưa xác lập, báo cáo đề xuất thủ tục ước lượng cụ thể; đáng chú ý là tiên nghiệm $\pi_0$ suy dẫn được bằng $0{,}080$ từ dữ liệu sẵn có (giá trị đang dùng là $0{,}10$), và hằng số $c$ của Định lý 4 fit được trực tiếp từ posterior của defender mà không cần giải các trò chơi nhỏ.

Quá trình ước lượng cũng làm lộ ra ba phát hiện ảnh hưởng tới kết luận của đề tài: (i) dưới detector dựa trên đặc trưng bề mặt, độ phân tách đo được $d' \le 0{,}502$ nằm dưới điểm hoà vốn, tức phân bổ thích nghi không vượt được audit-at-commit; (ii) yêu cầu không-khả-phân-biệt của corpus lành tính và ba mức detector khai báo trong bản thảo loại trừ nhau; (iii) tác động của $\chi$ lên nghiệm minimax phụ thuộc vào một quy ước chuẩn hoá chưa từng được khai báo.

**Từ khoá:** Stackelberg security game, ước lượng tham số, tiền đăng ký, đầu độc lưu giữ, phân bổ kiểm toán.

---

## 1. Đặt vấn đề

### 1.1 Bối cảnh

Sentinel mô hình hoá bài toán phân bổ ngân sách kiểm toán hữu hạn trên bốn carrier lưu giữ (memory, cached skill, tool queue, branch) của một agent lập trình, trước một attacker quan sát được chính sách và có thể gieo payload ngủ đông $\Delta$ task trước khi kích hoạt. Bài toán được đặt dưới dạng Stackelberg security game [1, 2] với trạng thái $s_t = (\mathbf{c}_t, \iota, \sigma)$. Hàm mất mát của defender là

$$L = \mathbb{E}[\text{harm}] + \lambda_Q\,\mathbb{E}[Q_{\text{false}}] + \lambda_T\,\mathbb{E}[T_{\text{lost}}] \tag{1}$$

và kết quả lý thuyết trung tâm (Định lý 4) phát biểu một cận dưới cho ngân sách cần thiết:

$$B \ \ge\ \frac{c\,\bar\kappa\,(1+\chi)\,\log(1/\alpha)}{\gamma^2}\left(1 + \frac{\Delta}{H}K\right) \tag{2}$$

### 1.2 Vấn đề nghiên cứu

Phương trình (1) và (2) cùng cơ chế mô phỏng chứa các tham số thuộc bốn bản chất khác nhau: thuộc tính của thế giới ($\kappa$, $\beta$, $\Delta$), mức khó được kiểm soát ($\psi, \varphi$), sở thích của tổ chức ($\lambda_Q, \lambda_T$), và hằng số của chứng minh ($c$, $\rho$). Bản thảo gốc khai báo giá trị cho hầu hết các tham số này nhưng không nêu cách xác lập, và một số giá trị không tái tạo được từ chính dữ liệu bản thảo cung cấp: với $\kappa = (0{,}4;\,0{,}9;\,1{,}6;\,4{,}1)$, công thức $\chi = \max_{k,k'}|\kappa(k)-\kappa(k')|/\bar\kappa$ cho $2{,}11$ chứ không phải $1{,}34$ như được báo.

Câu hỏi của báo cáo này:

> **RQ-P.** Với mỗi tham số của mô hình, giá trị của nó nên được xác lập bằng phương thức nào để kết luận của đề tài không phụ thuộc vào một lựa chọn tuỳ ý — và nếu không xác lập được, kết luận nên được phát biểu lại thế nào?

### 1.3 Đóng góp

1. Một khung phân loại bốn phương thức xác lập tham số, mở rộng phân loại bốn loại (thiết kế / đo / chọn có neo / output) của tài liệu phương pháp luận bằng hai phương thức mới là *suy dẫn* và *khử* (Mục 2).
2. Ba nguyên tắc thực hiện có thể cưỡng chế bằng mã (Mục 3).
3. Kết quả ước lượng cho tám đại lượng đã hoàn thành (Mục 4).
4. Thủ tục ước lượng cho chín tham số chưa xác lập (Mục 5).
5. Ba phát hiện về tính nhất quán nội tại của mô hình (Mục 6).

---

## 2. Cơ sở phương pháp luận

### 2.1 Bốn phương thức xác lập tham số

**Bảng 1.** Các phương thức xác lập tham số.

| Ký hiệu | Phương thức | Nội dung | Điều kiện áp dụng |
|---|---|---|---|
| **M1** | Đo trực tiếp | Thiết kế phép đo có quy trình, ước lượng sai số và tái lập được | Tham số là thuộc tính của một quần thể quan sát được |
| **M2** | Neo rồi quét | Neo vào một đại lượng đo được, chọn một dải hợp lý, báo kết quả trên toàn dải | Tham số là mức khó hoặc sở thích cần được kiểm soát |
| **M3** | Suy dẫn | Chứng minh giá trị tham số là hệ quả tất định của thiết kế thí nghiệm | Tham số bị ràng buộc bởi cấu trúc thí nghiệm dù được khai báo như đầu vào |
| **M4** | Khử tham số | Phát biểu lại kết luận dưới dạng điều kiện ngưỡng, để giá trị tham số không còn xuất hiện trong kết luận | Tham số không đo được và không neo được |

M1 và M2 tương ứng với loại B và loại C trong tài liệu phương pháp luận. M3 và M4 là hai phương thức bổ sung, được rút ra từ quá trình thực hiện.

**Về M3.** Một số tham số được khai báo như đầu vào độc lập nhưng thực chất bị thiết kế thí nghiệm xác định. Khi đó, việc quét tham số (M2) tạo ra một trục biến thiên không tương ứng với bất kỳ sự thay đổi nào của thế giới. Vì vậy M3 cần được thử trước M2.

**Về M4.** Phương thức này đổi dạng của tuyên bố từ "với tham số $\theta = \theta_0$, kết quả là $X$" sang "kết quả $X$ đạt được khi và chỉ khi $\theta$ thoả điều kiện $\mathcal{C}$". Tuyên bố mới hẹp hơn về phạm vi nhưng không phụ thuộc lựa chọn của tác giả; người đọc tự xác định $\theta$ của hệ thống mình và tự kiểm tra điều kiện $\mathcal{C}$. Nguyên tắc này tương đồng với việc tài liệu phương pháp luận coi ranh giới vùng $(\Delta, \chi)$ là đầu ra hữu ích nhất, nhưng được áp dụng cho từng tham số riêng lẻ.

**Bảng 2.** Ba trường hợp áp dụng M4 đã thực hiện.

| Tham số ban đầu | Đại lượng thay thế | Dạng tuyên bố mới |
|---|---|---|
| Biên độ nhiễu $\varepsilon$ | $\varepsilon^\* = \max\{\varepsilon : \mathrm{AUC}_{\text{upper}}(\varepsilon) \le 0{,}56\}$ | Kết quả tại ngân sách khả phân biệt lớn nhất mà corpus còn chứng nhận |
| Trọng số $\lambda_Q$ | $\lambda_Q^\*$ = trọng số nhỏ nhất làm đổi chính sách tối ưu | Chính sách A tốt hơn B khi và chỉ khi $\lambda_Q < \lambda_Q^\*$ |
| Điểm vận hành $(\psi,\varphi)$ | $d'^\*$ = độ phân tách hoà vốn với audit-at-commit | Phân bổ thích nghi có lợi khi và chỉ khi $d' \ge d'^\*(\Delta)$ |

### 2.2 Mô hình detector và các đại lượng dẫn xuất

Mọi chính sách dùng chung một detector, để biến được nghiên cứu là *phân bổ* chứ không phải *chất lượng phát hiện*. Theo lý thuyết phát hiện tín hiệu [3], điểm thô của item được mô hình hoá là $s \sim \mathcal{N}(d'\cdot\mathbb{1}[\text{poisoned}],\,1)$, và detector báo động khi $s > \tau_{\det}$. Khi đó:

$$\varphi = \Phi(-\tau_{\det}),\qquad \psi = \Phi(d' - \tau_{\det}),\qquad \gamma = \psi - \varphi \tag{3}$$

Nghịch đảo (3) cho $d' = z(\psi) - z(\varphi)$ và $\tau_{\det} = z(1-\varphi)$. Ba mức khai báo trong bản thảo ứng với $d' = 1{,}516;\ 2{,}211;\ 2{,}960$, khớp với các giá trị hình học 1,52 / 2,21 / 2,96 trong tài liệu phương pháp luận.

Điểm carrier được gộp bằng trung bình tỉ số hợp lý (mean-$\Lambda$) rồi chuyển thành posterior:

$$\Lambda(s) = e^{d's - d'^2/2},\qquad p_c = \frac{\pi_0\,\bar\Lambda}{\pi_0\,\bar\Lambda + 1 - \pi_0} \tag{4}$$

Phép gộp trung bình được chọn thay cho phép lấy max vì $\mathbb{E}[\max_n \mathcal{N}(0,1)] \approx \sqrt{2\ln n}$ tăng theo số item, làm carrier đông item trông nghi ngờ hơn dù hoàn toàn sạch [4]. Phương trình (4) cho thấy $\pi_0$ xác định toàn bộ thang posterior mà mọi chính sách quan sát — đây là lý do $\pi_0$ được xử lý riêng ở Mục 5.3.

---

## 3. Nguyên tắc thực hiện

### 3.1 Tiền đăng ký có kiểm chứng được

Mọi phép ước lượng tuân theo tiền đăng ký [5]: lưới tham số, tiêu chí phán quyết và hướng dự đoán được ghi và commit trước khi chạy, nhằm tránh việc đặt giả thuyết sau khi biết kết quả [6].

Rà soát quá trình thực hiện cho thấy một khuyết tật: trong phép đo $\varepsilon^\*$, lưới tham số và kết quả nằm trong cùng một commit, nên thứ tự "luật trước, số sau" chỉ dựa trên tường thuật mà không kiểm được từ lịch sử phiên bản. Báo cáo đề xuất nâng thành quy tắc:

> **Quy tắc R1.** Luật phán quyết phải nằm trong một commit riêng, đứng trước và không chứa kết quả. Thứ tự nhân quả khi đó kiểm chứng được bằng `git log`.

### 3.2 Đóng băng theo nhóm phụ thuộc

Đóng băng riêng lẻ một tham số là vô nghĩa khi nó được tính từ tham số khác. Các tham số được tổ chức thành nhóm; mỗi nhóm được băm (hash) chung và phải thay đổi đồng thời.

**Bảng 3.** Các nhóm đóng băng.

| Nhóm | Thành phần | Lý do phụ thuộc | Cưỡng chế hiện tại |
|---|---|---|---|
| G1 — Giao diện điểm | $\pi_0$, luật gộp, bảng $\tau_{\text{sel}}$, $\theta$, phạm vi dataset | $\tau_{\text{sel}}$ được tính từ $\pi_0$ và luật gộp | Có (hash cấu hình) |
| G2 — Cổng khả phân biệt | Tập đặc trưng $F_{\text{match}}$, độ dài payload, luật seed, $\theta$ | AUC là phát biểu về một tập đặc trưng cụ thể | Có (digest) |
| G3 — Thang chi phí | $\kappa(k)$, $\kappa_{\text{commit}}$, $\eta_Q$, $B$, quy ước chuẩn hoá khi quét $\chi$ | Một thành phần sai thang loại bỏ ngầm một hành động khỏi không gian hành động | Chưa |
| G4 — Lớp attacker | Tập $\Delta$, tập carrier, $\varepsilon$ | Nghiệm minimax chỉ có hiệu lực trên lớp nó được giải | Một phần |

Hạn chế hiện tại: chưa có manifest bao phủ $\lambda_Q$, $\lambda_T$, $\beta$, $c$, thư viện chính sách và thư viện attacker; harness chưa từ chối chạy khi hash của chính sách không khớp manifest.

### 3.3 Tách vai trò "thế giới" và "mô hình của defender"

Ba tham số xuất hiện ở hai vai trò khác nhau trong mô phỏng.

**Bảng 4.** Các tham số hai vai trò.

| Tham số | Vai trò thế giới (bộ sinh dữ liệu) | Vai trò mô hình (niềm tin của defender) | Hệ quả nếu dùng chung một giá trị |
|---|---|---|---|
| $\beta$ | Tốc độ carrier thực sự trôi | Khối lượng tiên nghiệm của giả thuyết NULL | Defender biết chính xác tốc độ trôi |
| $\pi_0$ | Tỉ lệ item bị gieo độc | Tiên nghiệm trong posterior (4) | Posterior được hiệu chỉnh hoàn hảo |
| $\Pi_A$ | Lớp attacker thực sự chạy | Lớp window mà LP được giải trên | Defender giải minimax trên đúng lớp attacker sẽ dùng |

Dùng chung một giá trị cho cả hai vai trò tương đương với việc cung cấp cho defender thông tin mà trong thực tế nó không có. Đại lượng $\zeta$ của Định lý 3 — khoảng cách total-variation giữa kernel thật và kernel defender sử dụng — chính là thước đo sự lệch này. Kết quả đo: $\zeta = 0{,}000$ trên mô phỏng mặc định và $\zeta = 0{,}119$ khi tốc độ trôi thật bằng $0{,}5$. Như vậy, trong cấu hình hiện tại, cận bền vững của Định lý 3 suy biến về cận chính xác.

> **Quy tắc R2.** Mỗi tham số hai vai trò được biểu diễn bằng hai biến riêng biệt, và thí nghiệm phải có ít nhất một cấu hình lệch.

---

## 4. Kết quả: các đại lượng đã ước lượng

### 4.1 Ngưỡng chọn carrier $\tau_{\text{sel}}$ (M1)

Tài liệu phương pháp luận xếp $\tau$ vào nhóm tham số chọn có neo. Báo cáo này định nghĩa nó như một phân vị của phân phối null, khiến nó trở thành đại lượng đo được:

$$\tau_{\text{sel}}(n_c, d', K) = Q_{1-\alpha_c(K)}\big(p_c \mid \text{carrier sạch}, n_c\big),\qquad \alpha_c(K) = 1-(1-\alpha_{\text{task}})^{1/K} \tag{5}$$

với $\alpha_{\text{task}} = 0{,}05$, giữ tỉ lệ báo động giả cố định *trên mỗi task* bất kể số carrier được chấm. Bảng tham chiếu được sinh bằng Monte Carlo với 800.000 mẫu mỗi ô, $n_c \in [0; 30]$, seed cố định; thông tin nguồn gốc lưu trong chính tệp kết quả và script sinh từ chối ghi đè.

**Kết quả phụ.** Hướng phụ thuộc của $\tau_{\text{sel}}$ theo $n_c$ đảo chiều giữa các mức detector: giảm từ 0,299 xuống 0,174 ở mức yếu, nhưng tăng từ 0,153 lên 0,246 ở mức mạnh. Dùng một ngưỡng cố định sẽ tạo thiên lệch đổi dấu giữa hai nhánh của RQ4, không thể hiệu chỉnh bằng một hằng số.

### 4.2 Cổng không-khả-phân-biệt (M1)

Corpus lành tính được xây từ các item thật của SWE-bench, ghép cặp theo tuổi với payload (tại thời điểm kích hoạt, tuổi của payload bằng chính xác $\Delta$). Tính không-khả-phân-biệt được kiểm định bằng classifier two-sample test [7]: AUC của hồi quy logistic trên tập đặc trưng bề mặt $F_{\text{match}}$, khoảng tin cậy theo Hanley–McNeil [8], lặp trên 20 phép chia train/test khai báo trước. Tiêu chí chấp nhận là **cận trên** của khoảng tin cậy không vượt 0,56 — chặt hơn đề xuất ban đầu dùng ước lượng điểm.

Kết quả trên bốn đặc trưng: $\mathrm{AUC}_{\text{upper}} = 0{,}5414$. Tuy nhiên, một quy tắc không tham số dựa trên đặc trưng `topic` — không thuộc cổng — tách được payload với AUC $0{,}9492$ trên cùng corpus. Kết quả của cổng vì vậy chỉ là phát biểu về tập đặc trưng đã khai báo, không phải về tính khó phân biệt nói chung.

### 4.3 Ngân sách khả phân biệt $\varepsilon^\*$ (M4)

$\varepsilon$ chỉ đóng vai trò ngân sách khi nó có cả lợi ích (tăng xác suất payload được truy xuất) lẫn chi phí (tăng khả năng bị phát hiện). Với định nghĩa ở Bảng 2 và lưới $\varepsilon$ chốt trước:

- Trên nền lành tính tiêu chuẩn: $\varepsilon^\* = 0$.
- Trên nền lành tính trung thực hơn (item có nội dung tự nhiên): **không tồn tại** $\varepsilon$ nào thoả tiêu chí, với mọi $\Delta$ và mọi phép chia; giá trị tốt nhất là $\mathrm{AUC}_{\text{upper}} = 0{,}7056$.

### 4.4 Điểm hoà vốn của detector $d'^\*$ (M2 và M4)

Thay cho ba điểm khai báo, $d'$ được quét liên tục trên $[0;\,3{,}0]$ với bước $0{,}2$, trong khi giữ $\tau_{\det} = z(1-0{,}12)$ cố định. Nhờ đó $\varphi = 0{,}12$ tại mọi điểm và mọi khác biệt được quy cho $\psi$ — khác với ba mức khai báo vốn thay đổi đồng thời cả $\psi$ và $\varphi$. Bảng $\tau_{\text{sel}}$ được sinh lại cho từng giá trị $d'$ để loại bỏ nhiễu do dùng ngưỡng hiệu chỉnh cho một $d'$ khác.

**Bảng 5.** Điểm hoà vốn $d'^\*$ giữa phân bổ thích nghi và audit-at-commit.

| $\Delta$ | $d'^\*$ (seed chính) | Dải qua 5 seed corpus |
|---|---|---|
| 0 | không tồn tại | — |
| 1 | không tồn tại | — |
| 2 | 2,85 | 2,6 – 3,0 |
| 4 | 0,95 | 1,0 – 1,4 |

Tại $\Delta \le 1$ không có điểm hoà vốn, nhất quán với Hệ quả 5: khi trigger kích hoạt gần như tức thì, audit-at-commit là đủ.

### 4.5 Độ phân tách thực nghiệm của detector bề mặt (M1)

Trên corpus ghép cặp (80 sự kiện dương, 320 item lành tính thật), đánh giá qua 10 phép chia tại ngưỡng $\tau_{\det} = 1{,}175$:

**Bảng 6.** Độ phân tách đo được theo $\Delta$ và $\varepsilon$.

| $\Delta$ | $\varepsilon = 0$ | $\varepsilon = 0{,}2$ | $\varepsilon = 0{,}4$ | $\varepsilon = 0{,}7$ | $d'^\*$ |
|---|---|---|---|---|---|
| 0 | 0,000 | 0,000 | 0,000 | 5,26 | — |
| 2 | 0,155 | 0,084 | 0,000 | 5,26 | 2,85 |
| 4 | 0,288 | 0,284 | 0,502 | 5,26 | 0,95 |

Ở $\varepsilon \le 0{,}4$ — vùng attacker ngụy trang thành công — $d' \le 0{,}502$ và $\gamma \le 0{,}13$, đều dưới điểm hoà vốn. Ở $\varepsilon = 0{,}7$, payload bị phát hiện hoàn toàn (AUC = 1,0), tức attacker không có lý do để chi tới mức đó. Ý nghĩa của kết quả này được thảo luận ở Mục 6.1.

### 4.6 Chênh lệch giữa ràng buộc kỳ vọng và ràng buộc cứng (M1)

Nghiệm LP ràng buộc ngân sách theo kỳ vọng, trong khi chính sách khi thực thi bị ràng buộc cứng trên từng lượt chạy. Mô phỏng Monte Carlo 1.000 lần ($K = 4$, $H = 8$, $B = 17{,}95$, $\Delta = 2$, $\kappa_k = 2{,}0$, $\kappa_{\text{commit}} = 4{,}1$):

**Bảng 7.** Độ lệch giữa nghiệm LP và thực thi.

| Đại lượng | Nghiệm LP | Thực thi cứng | Chênh lệch |
|---|---|---|---|
| Độ phủ trung bình | 0,2805 | 0,2432 | $-13{,}29\%$ |
| Chi tiêu trung bình | 17,95 | 15,56 | $-13{,}3\%$ |

Phần ngân sách không dùng được là phần dư không đủ mua thêm một lượt audit trọn vẹn ở cuối workflow. Mọi độ lợi tính từ nghiệm LP vì vậy lạc quan khoảng 13%.

### 4.7 Các đại lượng khác

**Bảng 8.** Các đại lượng đã ước lượng một phần.

| Đại lượng | Phương pháp | Kết quả | Mức hoàn thành |
|---|---|---|---|
| $\chi$ | Công thức với $\bar\kappa$ là trung bình cộng, công bố tường minh | 2,114 (bảng bản thảo); 1,349 (bảng đo trên hệ thống) | Hoàn thành công thức; quy ước quét chưa chốt (Mục 5.7) |
| $\kappa(k)$ | Số item cần chấm mỗi lượt audit × đơn giá một lượt chấm LLM | memory 5,34 · skill 1,12 · queue 1,55 · branch 4,50 item | Một phần (Mục 5.6) |
| $\Delta$ thực | Khoảng cách commit giữa thay đổi đặc tả và thay đổi mã trong lịch sử phiên bản | $n=29$; trung vị 3; p75 10; p90 23 | Một phần (Mục 5.8) |
| $\lambda_Q^\*$ | Giao điểm chính xác của các đường $L$ tuyến tính theo $\lambda_Q$ | 0,036 – 0,05 tuỳ cấu hình | Một phần (Mục 5.5) |
| $\rho$ | Bán kính phủ trong không gian phân phối chi tiêu | 0,894 (thư viện 10 chính sách tại thời điểm đo) | Một phần (Mục 5.9) |

---

## 5. Phương pháp đề xuất cho các tham số chưa xác lập

Mỗi tiểu mục trình bày: định nghĩa, vai trò trong mô hình, hệ quả khi ước lượng sai, hiện trạng, thủ tục đề xuất, phương pháp kiểm chứng, và giới hạn của thủ tục.

### 5.1 Tốc độ trôi lành tính $\beta_k$

**Định nghĩa.** Xác suất carrier $k$ bị thay đổi vì lý do thông thường trong một task.

**Vai trò.** $\beta$ là nguyên nhân cạnh tranh với đầu độc. Khi $\beta = 0$, mọi báo động đều là bằng chứng của đầu độc và chính sách "cách ly tất cả" trở thành tối ưu. $\beta$ quá nhỏ dẫn tới cách ly quá mức; quá lớn khiến defender không bao giờ cách ly và suy biến về audit-at-commit.

**Hiện trạng.** Chưa ước lượng; đang dùng giá trị gán $0{,}25$.

**Thủ tục đề xuất.**

1. *Khai báo luật ánh xạ (quyết định thiết kế).* Carrier nằm ngoài repository nên không có commit nào trực tiếp thay đổi carrier. Cần khai báo trước một ánh xạ từ tệp thay đổi sang carrier:

   | Carrier | Mẫu đường dẫn | Lập luận |
   |---|---|---|
   | memory | `*.md`, `docs/**`, `*.rst`, `CHANGELOG*` | Hướng dẫn dạng văn bản |
   | skill | Tệp được ít nhất $N$ tệp khác import; `utils/`, `helpers/` | Mã tái sử dụng |
   | queue | `setup.py`, `tox.ini`, `.github/**`, `Makefile` | Cấu hình công cụ |
   | branch | Mọi commit | Branch tích luỹ mọi thay đổi, nên $\beta_{\text{branch}} = 1$ theo định nghĩa |

2. *Xác định cửa sổ quan sát.* Với mỗi cặp task liên tiếp trong workflow, lấy tập commit giữa `base_commit` của hai task — đây là khoảng thời gian thực mà một task chiếm.
3. *Ước lượng.* $\hat\beta_k = n_k / n$, với $n_k$ là số commit trong cửa sổ khớp mẫu của carrier $k$ và $n$ là tổng số commit trong cửa sổ.
4. *Báo cáo theo repository.* Vì phân bố instance SWE-bench lệch mạnh (django chiếm 231/500 instance Verified), giá trị gộp phản ánh chủ yếu một repository. Báo cáo trung vị và khoảng $[\min, \max]$ qua các repository.
5. *Phân tích độ nhạy với luật ánh xạ.* Lặp lại với ít nhất một luật ánh xạ thay thế. Nếu kết luận định tính thay đổi giữa các luật, $\beta$ không định danh được và phải chuyển sang M2 (quét trên dải đo được).
6. *Tách vai trò* theo Quy tắc R2.

**Kiểm chứng.** (a) $\hat\beta$ nằm trong dải đã quét; (b) khi $\beta_{\text{thế giới}} \ne \beta_{\text{mô hình}}$, tỉ lệ cách ly nhầm dịch theo hướng dự đoán; (c) $\zeta > 0$ trong cấu hình lệch.

**Giới hạn.** Đồng thay đổi (co-change) là tương quan tiến hoá, không phải quan hệ nhân quả [9]. Luật ánh xạ là một phép tương tự có lập luận, chưa được kiểm chứng trên hành vi agent thật.

### 5.2 Chi phí cách ly $\eta_Q$

**Định nghĩa.** Chi phí loại một carrier khỏi vòng lặp, bao gồm chạy lại task không có carrier đó và phục hồi nội dung hợp lệ bị xoá theo.

**Vai trò.** $\eta_Q$ đưa cách ly vào ràng buộc ngân sách như một hành động có giá. Nếu quá rẻ, cách ly lấn át audit và benchmark không còn đo phân bổ; nếu quá đắt, không chính sách nào chọn được hành động này.

**Hiện trạng.** Giá trị gán $2{,}0 \approx 1{,}14\,\bar\kappa$; phiên bản theo đơn vị tiền tệ chỉ bảo toàn tỉ lệ này, nên tỉ lệ 1,14 vẫn chưa có nguồn.

**Thủ tục đề xuất.** Phân tách thành hai thành phần có cơ chế khác nhau:

$$\eta_Q(k) = c_{\text{gỡ}}(k) + c_{\text{phục hồi}}(k) \tag{6}$$

1. *$c_{\text{gỡ}}(k)$ — đo trực tiếp (M1).* Chạy task với carrier $k$ bị che, lấy hiệu thời gian CPU so với chạy bình thường; tối thiểu 30 lần, cố định tần số CPU, lấy trung vị.
2. *$c_{\text{phục hồi}}(k)$ — suy dẫn (M3).* Cách ly xoá mọi item của carrier, kể cả item sạch; chi phí phục hồi bằng $n_{\text{live}}(k)$ nhân đơn giá ghi một item. Cả hai thừa số đều đã được đo, nên thành phần này tính được ngay.
3. *Theo carrier.* Vì $n_{\text{live}}$ chênh 4,8 lần giữa memory và skill, giá trị vô hướng hiện tại là một đơn giản hoá cần được khai báo hoặc thay bằng $\eta_Q(k)$.
4. *Báo cáo như một trục kết quả (M2).* Chi phí phục hồi thấp hơn làm chính sách tối ưu cách ly mạnh tay hơn; vì vậy báo cáo thêm $\eta_Q^\*$, giá trị tại đó chính sách "cách ly tất cả" không còn thua dưới $L$.

**Kiểm chứng.** Bất đẳng thức $\eta_Q(k) > \kappa(k)$ với mọi $k$; chính sách đối chứng "cách ly tất cả" phải thua dưới $L$ trên toàn dải đã quét.

**Giới hạn.** Chi phí mất tri thức khi một skill bị xoá không đo được bằng thời gian CPU; giá trị đo được là cận dưới.

### 5.3 Tiên nghiệm mỗi item $\pi_0$ và belief khởi đầu $b_0$

**Định nghĩa.** $\pi_0 = \Pr[\text{một item sống bất kỳ là payload}]$ trước khi quan sát bằng chứng.

**Vai trò.** Theo (4) và (5), $\pi_0$ xác định thang posterior mà mọi chính sách quan sát, xác định toàn bộ bảng $\tau_{\text{sel}}$, và là mẫu số của tỉ số bằng chứng trong belief. Đây là tham số có phạm vi ảnh hưởng rộng nhất trong mô hình.

**Hiện trạng.** Gán $\pi_0 = 0{,}10$, được ghi chú trong mã là "hằng số mô hình, không suy từ dữ liệu". Ngoài ra, $\pi_0$ không nhất quán với tiên nghiệm tồn tại tấn công $\pi_{\text{attack}} = 0{,}5$ dùng trong belief; hai tham số cùng mô tả tỉ lệ nền nhưng được đặt độc lập.

**Thủ tục đề xuất (M3).** $\pi_0$ không phải thuộc tính của thế giới mà là hệ quả của thiết kế episode: mỗi episode gieo đúng một payload giữa $n$ item sống tại thời điểm quyết định. Do đó

$$\pi_0 = \frac{\Pr[\text{có tấn công}]}{\mathbb{E}[n_{\text{tổng}}]} \tag{7}$$

1. $\mathbb{E}[n_{\text{tổng}}] = 5{,}34 + 1{,}12 + 1{,}55 + 4{,}50 = 12{,}51$, đo trên 20 episode có ghi nhận chi tiết.
2. Trong nhánh bị gieo của thiết kế ghép cặp, $\Pr[\text{có tấn công}] = 1$, suy ra $\pi_0^{\text{thế giới}} = 1/12{,}51 = 0{,}0799$.
3. Với defender không biết chắc có tấn công ($\pi_{\text{attack}} = 0{,}5$): $\pi_0^{\text{mô hình}} = 0{,}5 \times 0{,}0799 = 0{,}040$. Hai giá trị này ứng với hai vai trò theo Quy tắc R2.
4. Sinh lại bảng $\tau_{\text{sel}}$ (nhóm G1) và chạy lại các bảng kết quả.
5. *Kiểm chứng bằng M2.* Lặp với $\pi_0 \in \{0{,}04;\ 0{,}08;\ 0{,}10;\ 0{,}20\}$; nếu thứ hạng chính sách thay đổi, $\pi_0$ phải được báo cáo như một trục.

Belief khởi đầu $b_0$ hiện chia đều $\pi_{\text{attack}}$ trên các window khả thi của lớp $\Pi_A$. Như vậy $b_0$ không phải tham số độc lập mà được xác định bởi $\pi_{\text{attack}}$ và $\Pi_A$, và thừa hưởng mọi giới hạn của lớp attacker đã khai báo.

**Kiểm chứng.** Thay đổi $\pi_0$ phải làm thay đổi hash cấu hình và mọi dòng của bảng $\tau_{\text{sel}}$.

**Giới hạn.** Giá trị suy dẫn là tỉ lệ nền của benchmark, không phải của một hệ thống thực.

### 5.4 Hằng số $c$ của Định lý 4

**Định nghĩa.** Hằng số không thứ nguyên trong (2), quy đổi số quan sát mang thông tin thành chi phí audit.

**Vai trò.** Một cận có hằng số tự do không kiểm chứng được. Không có $c$, Định lý 4 chỉ phát biểu về dạng hàm của ngân sách cần thiết.

**Hiện trạng.** Chưa có kiểm chứng số.

**Thủ tục đề xuất.** Tài liệu phương pháp luận đề xuất fit $c$ trên 240 trò chơi nhỏ giải bằng quy nạp lùi. Báo cáo đề xuất một thủ tục khác, dựa trên quan sát rằng vế trái của (2) là một phát biểu về sự hội tụ của belief — đại lượng mà mô hình đã tính chính xác.

1. *Định nghĩa vế trái.* $B_{\min}$ của một ô thí nghiệm là ngân sách nhỏ nhất sao cho tại thời điểm kích hoạt $\sigma$, posterior của defender đặt khối lượng ít nhất $1-\alpha$ lên window thật $(k, \iota, \sigma)$.
2. *Kiểm tra tính đơn điệu.* Xác nhận khối lượng posterior trên window thật không giảm theo $B$ — điều kiện cần để tìm kiếm nhị phân có nghĩa.
3. *Tính $c$ từng ô.* Trên lưới $(\Delta, \chi, \gamma)$, tìm $B_{\min}$ bằng tìm kiếm nhị phân và tính
   $$c_{\text{ô}} = \frac{B_{\min}\,\gamma^2}{\bar\kappa\,(1+\chi)\,\log(1/\alpha)\,(1 + \Delta K/H)} \tag{8}$$
4. *Báo cáo.* $c = \max_{\text{ô}} c_{\text{ô}}$ là giá trị nhỏ nhất để cận đúng trên toàn lưới. Phân bố của $c_{\text{ô}}$ cho biết dạng hàm của cận có phù hợp hay không.
5. *Kiểm tra từng thừa số.* Hồi quy $\log c_{\text{ô}}$ theo $\log(1+\chi)$, $\log(1+\Delta K/H)$ và $\log(1/\gamma^2)$. Nếu dạng hàm của cận đúng, các hệ số hồi quy phải xấp xỉ bằng 0 vì các thừa số tương ứng đã được chia ra; một hệ số khác 0 có ý nghĩa thống kê chỉ ra thừa số bị mô tả sai.
6. *Kiểm tra tính không thứ nguyên.* $c$ phải không đổi khi đổi đơn vị của $\kappa$; kiểm tra bằng cách chạy trên hai bảng chi phí khác đơn vị.

**Kiểm chứng.** Fit $c$ trên các ô phát triển và kiểm tra cận trên các ô giữ lại.

**Giới hạn.** $c$ fit được là hằng số của cơ chế belief cụ thể trong mô hình, không phải của defender tối ưu, và cho cận trên của ngân sách cần thiết thay vì cận dưới lý thuyết thông tin.

### 5.5 Trọng số hàm mất mát $\lambda_Q$, $\lambda_T$

**Vai trò.** Cả ba số hạng của (1) đều cần thiết: khi $\lambda_Q = \lambda_T = 0$, chính sách cách ly mọi carrier ở task đầu đạt harm bằng 0 và trở thành tối ưu dù làm hệ thống ngừng hoạt động.

**Hiện trạng.** Giá trị gán $0{,}10$ và $0{,}50$; đã thay bằng $\lambda_Q^\*$ theo M4. Vì chính sách tối ưu không thay đổi đơn điệu theo $\lambda_Q$ (một chính sách có $T_{\text{lost}}$ lớn có thể bị loại ở mọi giá trị), $\lambda_Q^\*$ được tính chính xác từ giao điểm các đường $L$ tuyến tính theo $\lambda_Q$ thay vì bằng tìm kiếm nhị phân.

**Thủ tục đề xuất.** Giá trị $\lambda_Q^\*$ chỉ trở thành kết luận khi biết dải hợp lý của $\lambda_Q$:

1. $\lambda_T$ được neo vào giá trị một task sạch, xấp xỉ bằng chi phí chạy lại task đó (đo được).
2. $\lambda_Q$ được neo vào chi phí một lần cách ly nhầm, tức $\eta_Q$ cộng chi phí dựng lại nội dung. Như vậy $\lambda_Q$ và $\eta_Q$ định giá cùng một sự kiện ở hai vị trí khác nhau (hàm mất mát và ràng buộc ngân sách), và cần được ràng buộc nhất quán.
3. Kết luận được phát biểu dạng so sánh: nếu $\lambda_Q^\*$ nằm dưới dải đo được, thứ hạng chính sách bền vững; nếu nằm trong dải, kết luận phải nêu điều kiện.
4. Quy về cùng đơn vị: $\lambda$ mang đơn vị "harm trên một sự kiện".

**Giới hạn.** $\lambda$ phản ánh ưu tiên của tổ chức; không tồn tại một giá trị "đúng" duy nhất.

### 5.6 Chi phí audit $\kappa(k)$

**Hiện trạng.** Tồn tại hai bảng chi phí.

**Bảng 9.** Hai bảng chi phí audit.

| Bảng | Nguồn | $\chi$ | Sử dụng |
|---|---|---|---|
| Bảng bản thảo: 0,4 / 0,9 / 1,6 / 4,1 | Chi phí theo *giai đoạn* audit, không phải theo carrier | 2,114 | Thí nghiệm chính |
| Bảng đo: số item mỗi lượt audit × đơn giá chấm | Đo trên hệ thống | 1,349 | Một phép quét phụ |

Ba vấn đề cần xử lý:

1. *Thứ tự chi phí đảo ngược.* Memory từ carrier rẻ nhất trở thành đắt nhất. Vì $\chi$ đo hình dạng của vector chi phí, thay đổi này đổi carrier mà attacker ưu tiên, tức đổi chính trò chơi.
2. *Trùng giá trị cấu trúc.* Trong bảng bản thảo, $\kappa_{\text{branch}} = \kappa_{\text{commit}} = 4{,}1$. Trùng hợp này triệt tiêu lợi thế giá khi attacker gieo vào branch; thực nghiệm cho thấy mở lớp attacker từ hai lên bốn carrier đổi dấu độ lợi tại $\Delta = 0$ (từ $+38{,}3\%$ thành $-17{,}8\%$).
3. *Trùng khớp với giá trị bản thảo.* Bảng đo cho $\chi = 1{,}349$, gần như trùng với $1{,}34$ của bản thảo. Cần xác nhận số liệu nền không được điều chỉnh để đạt giá trị này; nếu độc lập, đây là một bằng chứng hỗ trợ đáng kể và nên được báo cáo.

**Thủ tục đề xuất.**

1. Đo song song theo thời gian CPU: bốn checkpoint, tối thiểu 30 lần, đo user+sys thay vì thời gian thực, cố định tần số CPU, lấy trung vị và báo phương sai. Đơn vị tiền tệ phụ thuộc giá và phiên bản mô hình; thời gian CPU thì không.
2. *Nguyên tắc đơn vị.* Đơn vị triệt tiêu trong $\chi$ nhưng không triệt tiêu trong $B$. Ngân sách vì vậy được phát biểu dưới dạng **tỉ lệ của chi phí audit toàn bộ** (hiện là 32,1%), giúp các bảng chi phí khác đơn vị so sánh được.
3. Chọn một bảng cho thí nghiệm chính và khai báo rõ bảng nào sinh ra mỗi kết quả.
4. *Độ sâu audit.* Cấu trúc chi phí $\kappa(k, \text{depth})$ và độ phân tách $d' \propto \sqrt{\text{depth}}$ đã được cài đặt nhưng chưa chính sách nào sử dụng. Hệ quả của Định lý 4 — tăng độ sâu audit tại commit không cung cấp thông tin về danh tính carrier — cần một nhánh thí nghiệm riêng: audit-at-commit ở độ sâu 1, 2, 4 được dự đoán không cải thiện theo $\Delta$.

### 5.7 Quy ước chuẩn hoá khi quét $\chi$

**Định nghĩa.** Khi $\chi$ thay đổi, cần giữ cố định một đại lượng của vector chi phí. Ba lựa chọn được khảo sát:

**Bảng 10.** Độ lợi của nghiệm minimax so với audit-at-commit tại $\Delta = 2$ theo ba quy ước.

| Quy ước | Đại lượng cố định | $\sum_k\kappa_k$ khi $\chi$ từ 0 lên 1,34 | Độ lợi | Lợi thế thu hẹp khi $\chi$ tăng? |
|---|---|---|---|---|
| A (hiện hành) | $\bar\kappa$ | Không đổi (8,0) | 39,7% ở mọi $\chi$ | Không |
| B | $\kappa_{\min}$ | 8,0 → 24,24 | 39,7% → 36,1% | Có |
| C | $\bar\kappa$, audit commit theo carrier | Không đổi | 66,7% ở mọi $\chi$ | Không |

**Phân tích.** Dưới quy ước A, harm không phụ thuộc carrier, nên attacker tối ưu luôn chọn carrier có độ phủ thấp nhất, buộc nghiệm minimax san bằng độ phủ: $u[k,t] = U(t)$. Khi đó

$$\sum_k \kappa_k \sum_t u[k,t] = \Big(\sum_k \kappa_k\Big)\sum_t U(t) \tag{9}$$

chỉ phụ thuộc tổng chi phí, không phụ thuộc phân bố chi phí giữa các carrier. Như vậy, việc $\chi$ không tác động lên nghiệm minimax dưới quy ước A là hệ quả cấu trúc của mô hình, không phải sai sót đo lường.

**Mâu thuẫn cần giải quyết.** Một phép quét trước đó trên chính sách chạy thực tế ghi nhận $\chi$ làm dịch điểm crossover từ $\Delta^\* = 1{,}67$ lên $2{,}83$, trái với kết quả bất biến của nghiệm LP. Hai phép đo dùng hai đường tính khác nhau.

**Thủ tục đề xuất.**

1. Khai báo quy ước trước khi chạy như một quyết định thiết kế.
2. Đề xuất quy ước B, với lập luận ngữ nghĩa: $\chi$ mô tả việc audit carrier đắt tốn kém hơn, không phải việc carrier đắt tăng giá thì carrier rẻ giảm giá tương ứng.
3. Vì quy ước B làm tổng chi phí tăng, ngân sách phải được biểu diễn theo tỉ lệ (Mục 5.6), tránh việc quét $\chi$ đồng thời thay đổi ngân sách hiệu dụng.
4. Chạy cả chính sách thực tế và nghiệm LP trên cùng quy ước và cùng ngân sách tỉ lệ. Nếu $\chi$ chỉ tác động lên chính sách thực tế, giả thuyết cần kiểm định là $\chi$ tác động thông qua ràng buộc cứng (Mục 4.6) chứ không qua nghiệm kỳ vọng.
5. Báo cáo cả ba quy ước, tương tự cách báo cáo hai lớp attacker song song.

### 5.8 Độ trễ thực tế $\Delta$

**Hiện trạng.** Đã đo trên lịch sử phiên bản của chính repository đề tài ($n = 29$, trung vị 3, p75 10). Kết quả ủng hộ giả thuyết vì trung vị lớn hơn crossover dự đoán, nhưng quần thể đo không phải quần thể mục tiêu.

**Thủ tục đề xuất.** (1) Tính đồng thay đổi (support, confidence) giữa các cặp module trên các repository SWE-bench [9]; (2) lọc tương quan giả bằng đồ thị import; (3) dùng `git bisect` với test bị hỏng để xác định commit gây lỗi; (4) đếm khoảng cách commit, báo theo từng repository; (5) đối chiếu với kết quả hiện có; (6) mở rộng lưới $\Delta$ tới 8, vì p75 đo được là 10 trong khi lưới hiện tại dừng ở 4.

**Giới hạn.** Thứ tự theo thời gian tạo không cho quan hệ nhân quả; đồng thay đổi chỉ cho tương quan.

### 5.9 Bán kính phủ $\rho$

**Định nghĩa.** $\rho = \max_{\pi^\*}\min_{\pi\in\Pi}\mathrm{TV}(\pi, \pi^\*)$.

**Hiện trạng.** Phép đo hiện tại dùng không gian phân phối chi tiêu trên các hành động, nên hai chính sách có cùng phân phối chi tiêu nhưng khác thời điểm audit không phân biệt được — trong khi thời điểm là nội dung chính của bài toán. Phép đo cũng thực hiện trên tập baseline và biến thể thay vì thư viện chính sách tham số hoá mà Mệnh đề 6 đề cập.

**Thủ tục đề xuất.** Chọn một trong hai hướng:

- *(a) Đo đúng không gian.* Ghi vector xác suất hành động mà chính sách cam kết tại mỗi task và tính
  $$\mathrm{TV}(\pi,\pi') = \frac{1}{H}\sum_{t=1}^{H}\frac{1}{2}\sum_a\big|\pi_t(a) - \pi'_t(a)\big| \tag{10}$$
- *(b) Thu hẹp Mệnh đề 6* về không gian phân phối chi tiêu và nêu rõ giới hạn.

Trong cả hai hướng, việc tính $\rho$ đòi hỏi nghiệm tối ưu $\pi^\*$ trên một lớp trò chơi giải được chính xác. Nghiệm minimax hiện có được tính trên ma trận payoff của chính thư viện, tức là một cận trong thư viện chứ không phải tối ưu của không gian chính sách đầy đủ.

---

## 6. Thảo luận

### 6.1 Detector bề mặt không đạt điểm hoà vốn

So sánh Bảng 5 và Bảng 6: ở vùng attacker ngụy trang thành công ($\varepsilon \le 0{,}4$), độ phân tách đo được $d' \le 0{,}502$, trong khi điểm hoà vốn là $2{,}85$ tại $\Delta = 2$ và $0{,}95$ tại $\Delta = 4$. Do đó, **với detector chỉ dựa trên đặc trưng bề mặt, phân bổ thích nghi không vượt được audit-at-commit**. Để đạt $d'^\*$ cần một detector đọc được ngữ nghĩa nội dung, nhưng loại detector này có chi phí đơn vị cao hơn nhiều, dẫn tới thay đổi $\kappa$ và do đó thay đổi chính bài toán ngân sách. Kết quả này được dự báo trong kế hoạch trước khi đo và là kết quả quan trọng nhất của quá trình ước lượng.

### 6.2 Mâu thuẫn nội tại giữa corpus lành tính và mức detector

Tài liệu phương pháp luận yêu cầu đồng thời: (a) corpus lành tính đạt $\mathrm{AUC} \le 0{,}56$ trên đặc trưng bề mặt, và (b) ba mức detector được neo vào đường ROC của một detector thật, với mức mạnh nhất $\psi = 0{,}92$, $\varphi = 0{,}06$. Kết quả Mục 4.5 cho thấy corpus thoả (a) thì detector bề mặt chỉ đạt $d' \approx 0$, nên (b) không thể thoả trên cùng corpus. Hai hướng xử lý: coi $(\psi, \varphi)$ là biến kiểm soát thuần tuý không neo vào detector bề mặt, hoặc neo vào một detector nội dung. Theo khung Mục 2, hướng thứ hai tương ứng với việc tách thang $d'$ thành hai tầng — bề mặt và nội dung — với chi phí khác nhau.

### 6.3 Tác động của $\chi$ phụ thuộc quy ước chuẩn hoá

Như Mục 5.7 đã phân tích, tác động của $\chi$ lên nghiệm minimax phụ thuộc quy ước chuẩn hoá. Vì $\chi$ là một trong hai trục của ranh giới vùng — đóng góp chính của đề tài — quy ước này cần được khai báo và biện luận trong luận văn thay vì để ngầm định.

### 6.4 Tiến độ theo từng phương thức

M1 hoàn thành với các đại lượng định nghĩa được như phân vị của phân phối null ($\tau_{\text{sel}}$, AUC) hoặc như độ lệch giữa hai định nghĩa của cùng một ràng buộc (Mục 4.6). M4 hoàn thành cho ba tham số khó nhất ($\varepsilon$, $\lambda_Q$, $d'$). M3 chưa được khai thác, dù áp dụng được ngay cho $\pi_0$ và một phần của $\eta_Q$ với chi phí gần như bằng không.

---

## 7. Hạn chế và mối đe doạ tính hợp lệ

1. **Tính hợp lệ nội tại — hàm harm.** Harm hiện được chấm bằng sự có mặt của marker trong patch. Việc thay bằng test ẩn thật đã được thử: họ test đầu tiên neo được 5/500 instance Verified, còn 1/500 sau khi loại các trường hợp từ chối cả patch chuẩn; trần ước tính cho mọi template đơn là khoảng 11%. Độ lệch giữa marker và test thật đã được đo trên một tập con: khớp 30/30 ở hai chế độ mô phỏng tạo ra được, 0/30 ở hai chế độ không tạo ra được, với hướng sai số được xác định (bỏ sót harm khi agent làm theo payload nhưng đặt tên khác; thổi phồng harm khi tên xuất hiện ở tệp không mang thuộc tính cần giữ). Các kết luận vì vậy mang tính **bán tổng hợp** (semi-synthetic).
2. **Tính hợp lệ nội tại — marker.** Marker hiện là một chuỗi cố định, chưa duy nhất theo từng lần chạy như thiết kế.
3. **Tính hợp lệ ngoại tại — quy mô.** Với $H = 8$ trên tập Verified, 14 trong 58 workflow thoả điều kiện tại mọi $\Delta$ được quét, so với 100 workflow theo thiết kế. Lưới $\Delta$ chưa gồm giá trị 8.
4. **Tính hợp lệ ngoại tại — quần thể.** $\beta$, $\Delta$ thực và $\kappa$ là thuộc tính của một quần thể repository cụ thể; các giá trị suy dẫn ($\pi_0$, $\varepsilon^\*$) là của benchmark, không phải của hệ thống thực.
5. **Tính hợp lệ cấu trúc.** Thư viện chính sách tham số hoá và lớp trò chơi nhỏ giải chính xác chưa được xây dựng. Ước lượng tham số không khắc phục được hai thiếu hụt này; nếu không thực hiện, Định lý 4 và Mệnh đề 6 nên được trình bày là kết quả lý thuyết chưa có kiểm chứng số.
6. **Không tái tạo số liệu bản thảo.** Các giá trị $\chi = 1{,}34$ và $\rho = 0{,}07$ của bản thảo không tái tạo được bằng các quy trình trên. Báo cáo trình bày quy trình tái lập được thay vì cố gắng đạt các giá trị đó.
7. **Trạng thái kiểm thử** (ngày 20/09/2026): cổng 1 đạt 538/551 với 13 bỏ qua do chưa dựng môi trường container; cổng 2 đạt 203/205, hai test không đạt là kết quả khoa học (không giá trị $\varepsilon$ nào đạt trần AUC) chứ không phải lỗi cài đặt; cổng 3 chưa chạy.

---

## 8. Kế hoạch thực hiện

Thứ tự thực hiện được xác định bởi quan hệ phụ thuộc giữa các tham số.

**Bảng 11.** Kế hoạch thực hiện.

| Bước | Công việc | Phương thức | Phụ thuộc | Ước lượng công sức |
|---|---|---|---|---|
| 0 | Áp dụng Quy tắc R1 cho mọi phép đo sau | — | — | Không đáng kể |
| 1 | Suy dẫn $\pi_0$ theo (7); tách hai vai trò; sinh lại bảng $\tau_{\text{sel}}$; chạy lại bảng kết quả | M3 | Bước 0 | Thấp (tính toán lại) |
| 2 | Ước lượng $\beta_k$; tách hai vai trò; đo $\zeta$ trong cấu hình lệch | M1 | Bước 0 | Thấp – trung bình |
| 3 | Ước lượng $\eta_Q$ theo (6); neo dải $\lambda_Q$, $\lambda_T$ | M1 + M3 | Bước 0 | Trung bình |
| 4 | Chốt bảng $\kappa$ và quy ước chuẩn hoá $\chi$; chuyển ngân sách sang tỉ lệ; giải mâu thuẫn Mục 5.7 | Thiết kế + M1 | Bước 0 | Trung bình |
| 5 | Fit $c$ theo (8); hồi quy kiểm tra từng thừa số | M1 | Bước 1, 4 | Trung bình – cao |

**Các việc độc lập, thực hiện song song:** mở rộng lưới $\Delta$ tới 8; đo $\kappa$ theo thời gian CPU; bổ sung kiểm định hoán vị (1.000 lần) cho cổng AUC; nhánh thí nghiệm độ sâu audit.

---

## 9. Kết luận

Báo cáo đề xuất một khung bốn phương thức xác lập tham số và ba nguyên tắc thực hiện, rồi áp dụng cho toàn bộ tham số của mô hình Sentinel. Tám đại lượng đã được ước lượng; chín tham số còn lại có thủ tục ước lượng cụ thể, trong đó hai tham số — $\pi_0$ và thành phần phục hồi của $\eta_Q$ — suy dẫn được từ dữ liệu sẵn có.

Kết quả quan trọng nhất không phải một giá trị tham số mà là một điều kiện: phân bổ thích nghi chỉ có lợi so với audit-at-commit khi detector đạt độ phân tách tối thiểu $d'^\*(\Delta)$, và detector dựa trên đặc trưng bề mặt không đạt điều kiện này trên corpus thoả yêu cầu không-khả-phân-biệt. Phát biểu dưới dạng điều kiện này không phụ thuộc vào giá trị $(\psi,\varphi)$ được chọn — vốn là điểm yếu nhất của bản thảo gốc — và cho phép người thực hành tự kiểm tra trên hệ thống của mình.

Hai vấn đề cần được thống nhất với giảng viên hướng dẫn trước khi tiếp tục:

1. Lựa chọn quy ước chuẩn hoá khi quét $\chi$ (Mục 5.7), vì lựa chọn này quyết định trục $\chi$ của ranh giới vùng có nội dung thực nghiệm hay không.
2. Hướng xử lý mâu thuẫn giữa corpus lành tính và mức detector (Mục 6.2): giữ $(\psi,\varphi)$ là biến kiểm soát thuần tuý, hay chuyển sang detector nội dung với chi phí tương ứng.

---

## Tài liệu tham khảo

[1] M. Tambe. *Security and Game Theory: Algorithms, Deployed Systems, Lessons Learned.* Cambridge University Press, 2011.

[2] V. Conitzer, T. Sandholm. Computing the optimal strategy to commit to. *Proc. ACM EC*, 2006.

[3] D. M. Green, J. A. Swets. *Signal Detection Theory and Psychophysics.* Wiley, 1966.

[4] H. A. David, H. N. Nagaraja. *Order Statistics*, 3rd ed. Wiley, 2003.

[5] B. A. Nosek, C. R. Ebersole, A. C. DeHaven, D. T. Mellor. The preregistration revolution. *PNAS* 115(11):2600–2606, 2018.

[6] N. L. Kerr. HARKing: Hypothesizing after the results are known. *Personality and Social Psychology Review* 2(3):196–217, 1998.

[7] D. Lopez-Paz, M. Oquab. Revisiting classifier two-sample tests. *ICLR*, 2017.

[8] J. A. Hanley, B. J. McNeil. The meaning and use of the area under a receiver operating characteristic (ROC) curve. *Radiology* 143(1):29–36, 1982.

[9] T. Zimmermann, P. Weißgerber, S. Diehl, A. Zeller. Mining version histories to guide software changes. *IEEE TSE* 31(6):429–445, 2005.

[10] C. E. Jimenez et al. SWE-bench: Can language models resolve real-world GitHub issues? *ICLR*, 2024.

[11] A. C. Cameron, D. L. Miller. A practitioner's guide to cluster-robust inference. *Journal of Human Resources* 50(2):317–372, 2015.

[12] J. Robinson. An iterative method of solving a game. *Annals of Mathematics* 54(2):296–301, 1951.

---

## Phụ lục A. Bảng tổng hợp trạng thái tham số

| Tham số | Ý nghĩa | Phương thức | Trạng thái | Giá trị / kết quả |
|---|---|---|---|---|
| $\tau_{\text{sel}}$ | Ngưỡng chọn carrier | M1 | Hoàn thành | Bảng tham chiếu, 800.000 mẫu/ô |
| $\mathrm{AUC}_{\text{upper}}$ | Tính không-khả-phân-biệt của payload | M1 | Hoàn thành | 0,5414 (bốn đặc trưng) |
| $\varepsilon^\*$ | Ngân sách khả phân biệt | M4 | Hoàn thành | 0; không tồn tại trên nền trung thực |
| $d'^\*$ | Điểm hoà vốn của detector | M2 + M4 | Hoàn thành | 2,85 ($\Delta{=}2$); 0,95 ($\Delta{=}4$) |
| $d'$ bề mặt | Độ phân tách thực nghiệm | M1 | Hoàn thành | $\le 0{,}502$ |
| Chênh lệch ràng buộc | Kỳ vọng so với cứng | M1 | Hoàn thành | $-13{,}29\%$ độ phủ |
| $\zeta$ | Sai số kernel | M1 | Hoàn thành | 0,000; 0,119 khi $\beta{=}0{,}5$ |
| $\chi$ | Độ dị tính chi phí | M1 | Một phần | 2,114 / 1,349; quy ước chưa chốt |
| $\kappa(k)$ | Chi phí audit | M1 | Một phần | Hai bảng song song |
| $\Delta$ thực | Độ trễ nhân quả | M1 | Một phần | Trung vị 3 ($n{=}29$) |
| $\lambda_Q, \lambda_T$ | Trọng số mất mát | M4 | Một phần | $\lambda_Q^\* \approx 0{,}036$–$0{,}05$ |
| $\rho$ | Bán kính phủ | M1 | Một phần | 0,894, không gian proxy |
| $\eta_Q$ | Chi phí cách ly | M1 + M3 | Chưa thực hiện | Giá trị gán 2,0 |
| $\beta_k$ | Tốc độ trôi lành tính | M1 | Chưa thực hiện | Giá trị gán 0,25 |
| $\pi_0$, $b_0$ | Tiên nghiệm | M3 | Chưa thực hiện | Đề xuất 0,080 (thay cho 0,10) |
| $c$ | Hằng số Định lý 4 | M1 | Chưa thực hiện | — |
| Quy ước $\chi$ | Chuẩn hoá khi quét | Thiết kế | Chưa khai báo | Đề xuất quy ước B |

## Phụ lục B. Ánh xạ tới mã nguồn

Mã nguồn: đường dẫn tương đối so với `auditgame/` của repo Sentinel. Báo cáo đo và tiền đăng ký: tương đối so với `docs/`.

| Nội dung | Vị trí |
|---|---|
| Detector, phương trình (3) | `detector.py` |
| Posterior mean-$\Lambda$, phương trình (4); $\pi_0$ | `scoring.py` |
| Sinh bảng $\tau_{\text{sel}}$, phương trình (5) | `reference/gen_score_table.py`, `reference/score_table.json` |
| Hàm mất mát (1), $\lambda_Q^\*$, hash cấu hình | `metrics.py` |
| Belief trên window, giả thuyết NULL, $\beta$ | `belief.py` |
| Chính sách, $\kappa$, $\eta_Q$, công thức $\chi$ | `policies.py` |
| Bảng chi phí đo được | `costs.py` |
| Nghiệm minimax LP | `lp.py`; giá trị minimax trong thư viện: `game.py` |
| $\rho$, $\zeta$ | `theory.py` |
| Cổng AUC, corpus lành tính | `analysis/discriminator.py`, `analysis/benign_corpus.py` |
| Quét $d'$ | `dprime_sweep.py`; `preregistration/dprime-sweep.md` |
| $\varepsilon^\*$ | `preregistration/eps-ngan-sach-that.md` |
| $d'$ thực nghiệm | `tools/measure_gamma.py`; `reports/t6-gamma-analysis.md` |
| Chênh lệch ràng buộc | `reports/t3-budget-analysis.md` |
| Ba quy ước $\chi$ | `tools/evaluate_chi_variants.py`; `reports/t2-chi-analysis.md` |
| $\Delta$ thực | `tools/measure_delta.py`; `spikes/delta-empirical.json` |
| Test ẩn và độ lệch marker | `hidden_tests/registry.py`, `hidden_tests/agreement.py` |
