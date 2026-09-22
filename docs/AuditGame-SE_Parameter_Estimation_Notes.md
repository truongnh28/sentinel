# Parameter Estimation Notes — Sentinel / AuditGame-SE

**Đề tài:** FSE-2027-15 (RAISE Lab, HCMUT) · **Ngày:** 22/09/2026
**Phạm vi:** định nghĩa, ý nghĩa, và **thủ tục ước lượng** cho mọi tham số chưa xác lập của mô hình.
**Nối với:** `docs/thesis/Toan-canh-de-tai-FSE-2027-15-Sentinel.md` §3 (bảng ký hiệu), `docs/thesis/Danh-sach-diem-can-them.md` (trạng thái thi hành), `docs/AuditGame-SE_Sentinel_Methodology_Full.md` Phần VI (bốn loại tham số), và mã trong `auditgame/`.

> **Tài liệu này không báo kết quả.** Nó báo *cách lấy* kết quả. Mỗi mục trả lời đúng ba câu: tham số này **nghĩa là gì**, **nếu sai thì hỏng ở đâu**, và **xác lập nó bằng thủ tục nào**.

---

## 0. Vấn đề

Phản biện nặng nhất nhắm vào Sentinel không phải "mô hình có đúng không" mà là một câu ngắn hơn:

> *"0,85 ở đâu ra?"*

Bản thảo gốc khai ba mức detector $(\psi,\varphi)$, bốn chi phí $\kappa$, một $\chi = 1{,}34$, một $\rho = 0{,}07$ — và không một con số nào có nguồn. Với một đề tài mà **đóng góp chính là một ranh giới vùng tham số hoá bởi $(\Delta, \chi)$**, mọi tham số không có nguồn là một trục có thể bị bác bỏ bằng một câu hỏi.

Cách sửa **không phải** là bảo vệ 0,85 hay hơn. Có bốn đường thoát, và đường mạnh nhất không nằm trong tài liệu phương pháp luận gốc — nó là thứ dự án đã tự tìm ra qua sáu tháng đo: **khử tham số**, biến một con số không trả lời được thành một *ngưỡng* hoặc một *kết quả báo cáo*.

---

## 1. Nguyên lý: bốn đường thoát khỏi "chúng tôi chọn"

| Đường | Tên | Làm gì | Khi nào dùng | Giá |
|---|---|---|---|---|
| **Đ1** | **ĐO** | Thiết kế một phép đo có quy trình, sai số, và tái lập được | Tham số là thuộc tính của **thế giới** (chi phí, tốc độ trôi, độ trễ) | Tốn công đo, nhưng kết luận vững nhất |
| **Đ2** | **NEO rồi QUÉT** | Neo vào một đại lượng đo được, chọn vài điểm vận hành, **báo trên cả dải** | Tham số là **sở thích** hoặc **mức khó** ta muốn kiểm soát | Kết luận phải giữ trên cả dải, nếu không thì vô nghĩa |
| **Đ3** | **SUY** | Chứng minh tham số là **hệ quả tất định** của thiết kế đã có, không phải đầu vào độc lập | Tham số tưởng là tự do nhưng thực ra bị ràng buộc bởi cấu trúc thí nghiệm | Gần như miễn phí — chỉ cần nhận ra |
| **Đ4** | **KHỬ** | Định nghĩa lại tuyên bố dưới **dạng ngưỡng**, để giá trị tham số không còn xuất hiện trong kết luận | Tham số không đo được và cũng không neo được vào gì | Đổi phát biểu: mạnh hơn về tính trung thực, hẹp hơn về phạm vi |

### 1.1 Đ4 là đóng góp phương pháp luận, không phải lối thoát

Ba ví dụ đã thi hành trong dự án, và cả ba đều đổi **hình dạng của tuyên bố**:

| Tham số không trả lời được | Sau khi khử | Tuyên bố mới |
|---|---|---|
| $\varepsilon$ — biên độ nhiễu attacker nên là bao nhiêu? | $\varepsilon^\* = \max\{\varepsilon : \mathrm{AUC}_{\text{upper}}(\varepsilon) \le 0{,}56\}$ | *"Ở ngân sách khả phân biệt lớn nhất mà corpus còn chứng nhận được, harm là X"* |
| $\lambda_Q$ — một lần cách ly nhầm đáng giá bao nhiêu? | $\lambda_Q^\*$ = trọng số nhỏ nhất làm **đổi thứ hạng** | *"Sentinel thắng nếu và chỉ nếu một lần cách ly nhầm rẻ hơn $1/20$ lần lọt lưới"* |
| $(\psi,\varphi)$ — 0,85 ở đâu ra? | quét $d' \in [0; 3{,}0]$, $\varphi$ **cố định** 0,12, tìm $d'^\*$ hoà vốn | *"Sentinel vượt audit-at-commit khi và chỉ khi detector đạt $d' \ge 2{,}85$ tại $\Delta=2$"* |

Nhận xét chung cho cả ba: **tham số biến từ một giả định thành một điều kiện**. Người đọc không phải tin 0,85; họ đo $d'$ của hệ mình rồi tra bảng. Đây đúng là điều Phần VI mô tả là "đầu ra hữu ích nhất" — nhưng áp cho *tham số*, không chỉ cho $(\Delta,\chi)$.

Nguyên văn trong `spikes/dprime-sweep.md` §1: *"Cách sửa không phải là bảo vệ 0,85 hay hơn. Là thôi chọn. Câu hỏi không được trả lời — nó tan đi."*

### 1.2 Đ3 là đường bị bỏ sót nhiều nhất

Một số tham số **trông như** tự do nhưng bị thiết kế thí nghiệm ràng buộc chặt. Ví dụ điển hình là $\pi_0$ (§3.3): mỗi episode gieo **đúng một** payload vào **một** carrier, giữa $n$ item sống — nên xác suất tiên nghiệm một item bất kỳ là payload **không phải lựa chọn**, nó là $1/\mathbb{E}[n]$, tính được từ dữ liệu đã có trong repo. Đ3 luôn phải thử trước Đ2: một tham số suy được mà lại đem quét là tự tạo ra một trục nhiễu.

---

## 2. Ba luật bắt buộc kèm mọi ước lượng

### 2.1 Luật ba câu hỏi

Mỗi tham số phải trả lời: **loại gì** (Đ1/Đ2/Đ3/Đ4) · **xác lập thế nào** (thủ tục, sai số) · **kiểm chứng thế nào** (test nào đỏ nếu sai). Tham số không có câu thứ ba là tham số sẽ trôi âm thầm.

### 2.2 Luật tiền-đăng-ký, và khuyết tật đã tự phát hiện

Luật phán quyết — lưới tham số, tiêu chí, hướng dự đoán — phải được viết và **commit trước** khi chạy phép đo. Dự án đã thi hành luật này ở mọi spike.

**Nhưng có một khuyết tật đã tự khai, và tài liệu này nâng nó thành luật cứng.** `spikes/eps-ngan-sach-that.md` §3 tự ghi mục **M9**: lưới `GRID` và các con số kết quả **nằm cùng một commit**, nên thứ tự nhân quả dựa trên *tường thuật*, không kiểm được từ `git log`.

> **Luật T1 (bắt buộc từ nay).** Luật phán quyết đi vào **một commit riêng, trước**, không chứa một con số kết quả nào. Phép đo đi vào commit sau. Ai chỉ có repository cũng kiểm được thứ tự bằng `git log --follow`. Chi phí: một lệnh `git commit`. Lợi: biến một lời cam kết thành một bằng chứng.

### 2.3 Luật ô hash — tham số nào phải đóng băng cùng nhau

Đóng băng riêng lẻ là vô nghĩa khi một tham số được **tính từ** tham số khác. Bốn ô hiện hành:

| Ô | Thành phần | Vì sao cùng một ô | Cưỡng chế |
|---|---|---|---|
| **H1 — giao diện điểm** | $\pi_0$ · luật gộp (mean-$\Lambda$) · bảng $\tau_{\text{sel}}$ · $\theta$ · scope dataset | $\tau_{\text{sel}}$ được **tính từ** $\pi_0$ và luật gộp. Đổi $\pi_0$ mà giữ bảng cũ là dùng một ngưỡng hiệu chỉnh cho thế giới khác | `metrics.config_sha` ✅ |
| **H2 — cổng khả phân biệt** | $F_{\text{match}}$ · $L$ (độ dài payload) · luật seed sự kiện · $\theta$ | AUC là phát biểu về **tập đặc trưng cụ thể**; thêm một cột là một cổng khác | md5 `gate2_v2` ✅ |
| **H3 — thang giá** | $\kappa(k)$ · $\kappa_{\text{commit}}$ · $\eta_Q$ · $B$ · quy ước neo khi quét $\chi$ | Để một thành phần ở thang cũ là **xoá một hành động khỏi không gian hành động** mà không ai thấy | `costs.install()` ⚠️ chưa cưỡng chế |
| **H4 — lớp attacker** | $\Pi_A$ (tập $\Delta$) · tập carrier · $\varepsilon$ | Nghiệm minimax **chỉ rộng bằng lớp nó được giải trên đó** | khai báo per-policy ✅, chưa vào manifest |

> **Việc còn thiếu:** không có manifest phủ $\lambda_Q, \lambda_T, \beta, c$, thư viện chính sách và thư viện attacker. Và không có **mã từ chối** — harness hiện không tính lại hash của policy nạp vào rồi từ chối chạy nếu lệch. Freeze hiện là *lời hứa*, chưa là *ràng buộc*.

### 2.4 Luật hai vai — tham số của THẾ GIỚI và tham số của MÔ HÌNH DEFENDER

Đây là luật dễ vi phạm nhất và hậu quả nặng nhất: nó **âm thầm đưa đáp án cho defender**.

Ba tham số xuất hiện **hai lần**, ở hai vai khác nhau:

| Tham số | Vai thế giới (bộ sinh) | Vai mô hình (defender tin gì) | Nếu gộp một |
|---|---|---|---|
| $\beta$ | `MockAgent(drift_rate=β)` — carrier thực sự trôi bao nhiêu | `WindowBelief(beta=β)` — khối lượng tiên nghiệm cho giả thuyết NULL | Defender biết chính xác tốc độ trôi ⇒ phân biệt trôi/độc dễ hơn thực tế |
| $\pi_0$ | tỉ lệ item độc mà thiết kế gieo | `scoring.PI0` trong posterior | Defender biết base rate thật ⇒ posterior hiệu chỉnh hoàn hảo |
| $\Pi_A$ | lớp attacker **thật sự** chạy | `MinimaxLP.DELTAS` — lớp LP được giải trên | Defender giải minimax trên đúng lớp attacker sẽ dùng ⇒ Stackelberg thành thông tin hoàn hảo |

> **Luật T2.** Mỗi tham số hai vai phải có **hai tên biến khác nhau** trong mã, và phải tồn tại ít nhất một phép đo ở chế độ **lệch** ($\beta_{\text{world}} \ne \beta_{\text{model}}$). Đây chính là vai của $\zeta$ trong Định lý 3: $\zeta$ đo khoảng cách total-variation giữa kernel thật và kernel defender dùng. Đo được: $\zeta = 0{,}000$ trên mock (mô phỏng *là* mô hình) và $\zeta = 0{,}119$ khi $\beta_{\text{world}} = 0{,}5$. Nghĩa là **cận bền vững của Định lý 3 hiện không làm việc gì cả**, và nó chỉ bắt đầu làm việc khi hai vai được tách.

---

## 3. Sổ tham số — các tham số chưa xác lập

Mỗi mục theo cùng một khuôn: **Định nghĩa · Ý nghĩa · Nếu sai · Trạng thái · Thủ tục · Kiểm chứng · Không tuyên bố.**

---

### 3.1 $\beta_k$ — tốc độ trôi lành tính theo carrier

**Định nghĩa.** $\beta_k$ = xác suất, trên một task, carrier $k$ bị sửa đổi vì lý do **thông thường** (ghi chú được viết lại, skill được tinh chỉnh, nhánh nhận commit khác) — không phải do attacker.

**Ý nghĩa.** Đây là **nguyên nhân cạnh tranh**. Không có nó thì mọi alarm là bằng chứng của đầu độc, "cách ly tất cả" là tối ưu, và $\lambda_Q$ định giá một rủi ro không tồn tại. Nó là thứ làm câu hỏi *"thay đổi này có lành tính không?"* trở thành một câu hỏi mà thế giới có thể đặt ra.

**Nếu sai.** $\beta$ quá nhỏ ⇒ giả thuyết NULL không bao giờ hấp thu được bằng chứng ⇒ cách ly quá tay ⇒ $Q_{\text{false}}$ phồng ⇒ mọi kết luận ở $\lambda_Q > 0$ đảo chiều. $\beta$ quá lớn ⇒ NULL hấp thu mọi thứ ⇒ không bao giờ cách ly ⇒ Sentinel suy biến về B1.

**Trạng thái: 0%.** Chỉ là knob. `policies.SentinelWindow.BETA_DRIFT = 0.25` và `MockAgent(drift_rate=…)` — cả hai là số gán, không nguồn.

**Thủ tục.**

> **Bước 0 (khai báo, loại A).** Carrier sống **ngoài** repo, nên không có commit nào "chạm memory". Phải khai một **luật ánh xạ** commit → carrier. Đây là *quyết định mô hình hoá*, không phải phép đo, và phải được công bố trước:

| Carrier | Tập mẫu đường dẫn | Lý lẽ |
|---|---|---|
| memory | `*.md`, `docs/**`, `*.rst`, `CHANGELOG*` | hướng dẫn dạng văn bản người đọc được — đúng thứ agent ghi vào memory |
| skill | file được ≥ $N$ file khác `import` (từ import graph), `utils/`, `helpers/`, `_base.py` | mã tái dùng được — đúng thứ bước rút skill sinh ra |
| queue | `setup.py`, `tox.ini`, `.github/**`, `Makefile`, `scripts/` | cấu hình công cụ và điểm vào |
| branch | *mọi* commit | branch tích luỹ mọi thứ ⇒ $\beta_{\text{branch}} = 1{,}0$ **theo cấu tạo**, khai là suy ra chứ không phải đo |

1. **Cửa sổ đo.** Với mỗi cặp task liên tiếp của một workflow, lấy khoảng commit giữa `base_commit(t)` và `base_commit(t+1)`. Đó là khoảng thời gian thực mà một task chiếm — không phải một khoảng tuỳ ý.
2. **Đếm.** $\hat\beta_k = n_k / n$, với $n_k$ là số commit trong cửa sổ chạm tập mẫu của carrier $k$, và $n$ là tổng số commit trong cửa sổ.
3. **Báo theo dải, không theo điểm.** Tính riêng trên từng repo trong 12 repo SWE-bench, báo $[\min, \max]$ và trung vị. Phần VI đã đòi điều này ("dải theo repo"); lý do là phân bố instance lệch rất mạnh (django 231/500 Verified, flask 1/500) nên một con số gộp là con số của django.
4. **Độ nhạy với luật ánh xạ** — bắt buộc. Chạy **ít nhất hai** luật ánh xạ hợp lý (ví dụ: luật trên, và một luật chỉ dùng import graph không dùng tên thư mục). Nếu kết luận *"bỏ benign-drift làm $Q_{\text{false}}$ tăng"* đổi dấu giữa hai luật thì $\beta$ **không định danh được** và phải chuyển sang Đ2: quét $\beta \in \{0; \hat\beta_{\min}; \hat\beta_{\text{med}}; \hat\beta_{\max}\}$ và báo trên cả dải.
5. **Tách hai vai** theo luật T2: $\hat\beta$ đi vào `MockAgent`, còn `WindowBelief` nhận một $\beta_{\text{model}}$ riêng. Bắt buộc có một ô đo ở chế độ lệch.

**Kiểm chứng.** `tests/gate1_integrity/test_benign_drift.py` đã khẳng định đơn điệu: $\beta \uparrow$ ⇒ churn $\uparrow$ ⇒ $Q_{\text{false}} \uparrow$. Thêm: (a) $\hat\beta$ phải nằm trong dải đã quét; (b) $\beta_{\text{world}} \neq \beta_{\text{model}}$ phải làm $Q_{\text{false}}$ dịch đúng chiều dự đoán; (c) $\zeta > 0$ ở chế độ lệch.

**Không tuyên bố.** Co-change là tương quan tiến hoá, không phải nhân quả. Luật ánh xạ commit → carrier **chưa được kiểm chứng** đối với hành vi agent thật; nó là một tương đồng có lý lẽ, không phải một phép đo.

---

### 3.2 $\eta_Q$ — chi phí cách ly

**Định nghĩa.** Chi phí loại một carrier khỏi vòng lặp: gỡ nó ra, chạy lại task mà không có nó, rồi phục hồi phần nội dung hợp lệ đã bị xoá theo.

**Ý nghĩa.** Là **cái giá làm "cách ly tất cả" không còn miễn phí**, ở phía *ràng buộc ngân sách* (khác với $\lambda_Q$, ở phía *hàm mất mát*). Phải là một **hành động có giá**, không chỉ một ngưỡng — vì nếu chỉ là ngưỡng thì chính sách suy biến của §A.4 không biểu diễn được, và cái test loại bỏ nó không viết được.

**Nếu sai.** $\eta_Q$ quá rẻ ⇒ cách ly chi phối audit, benchmark không còn đo phân bổ. Quá đắt ⇒ không policy nào mua được hành động đó ⇒ *"một chính sách không mua nổi một hành động thì không phải đang được so sánh, nó đang bị vô hiệu hoá"* (nguyên văn `costs.py`). Đây không phải rủi ro giả định: `ETA_Q_COST = 2.0` sang thang USD sẽ thành **~1400×** $\bar\kappa$ nếu copy nguyên con số.

**Trạng thái: 30%.** `ETA_Q_COST = 2.0` là placeholder ($\approx 1{,}14\,\bar\kappa$ của bảng placeholder). `ETA_Q_USD` chỉ mang **tỉ lệ** đó sang thang USD — nên bản thân tỉ lệ 1,14 vẫn là số chưa đo.

**Thủ tục.** $\eta_Q$ có **hai thành phần co giãn khác nhau**, nên phải đo riêng rồi cộng:

$$\eta_Q(k) = c_{\text{gỡ}}(k) + c_{\text{phục hồi}}(k)$$

1. **$c_{\text{gỡ}}(k)$ — chi phí chạy lại không có carrier.** Đo trực tiếp: chạy task với carrier $k$ bị che (`harness` đã có cơ chế mount/không mount), lấy hiệu CPU-time so với chạy bình thường. ≥30 lần, pin CPU frequency, lấy trung vị.
2. **$c_{\text{phục hồi}}(k)$ — chi phí dựng lại nội dung lành tính đã bị xoá.** Cách ly xoá **mọi** item của carrier, kể cả item sạch; phục hồi = ghi lại $n_{\text{live}}(k)$ item đó. Đơn giá ghi một item đã đo được: `USD_PER_JUDGEMENT = 0,594/1200`. Và $n_{\text{live}}(k)$ cũng đã đo: $\{5{,}34 \cdot 1{,}12 \cdot 1{,}55 \cdot 4{,}50\}$ trên 20 episode có instrument. Nên $c_{\text{phục hồi}}$ **tính được ngay từ dữ liệu đã có** — đây là một ứng dụng của Đ3.
3. **Bỏ giả định vô hướng.** $\eta_Q$ hiện là một số duy nhất cho cả bốn carrier, nhưng $n_{\text{live}}$ lệch 4,8× giữa memory (5,34) và skill (1,12). Hoặc chuyển sang $\eta_Q(k)$, hoặc khai rõ đơn giản hoá và đo xem nó đổi kết luận bao nhiêu.
4. **Báo như một trục, không như một điểm** (Đ2). Phần IX quy tắc 5 nói thẳng: phục hồi rẻ hơn ⇒ cách ly rẻ hơn ⇒ lợi thế tăng 34,1% → 44,0%. Vậy $\eta_Q$ **là một trục kết quả**. Quét nó và báo $\eta_Q^\*$: giá trị mà NC1 "cách ly tất cả" thôi bị thua dưới $L$.

**Kiểm chứng.** Bất đẳng thức kiểm được: $\eta_Q(k) > \kappa(k)\ \forall k$ — nếu sai, cách ly thắng audit một cách tầm thường và benchmark không đo gì. Và NC1 **phải thua** dưới $L$ ở mọi $\eta_Q$ trong dải đã quét (đây là control, không phải đối thủ).

**Không tuyên bố.** Chi phí phục hồi *ngữ nghĩa* — một skill bị xoá thì tri thức trong nó mất, không chỉ mất bytes — không đo được bằng CPU-time. Đo được là cận dưới.

---

### 3.3 $\pi_0$ / $b_0$ — tiên nghiệm mỗi item, và belief khởi đầu

**Định nghĩa.** $\pi_0 = \Pr[\text{một item sống bất kỳ là payload}]$ trước khi thấy bằng chứng nào. $b_0$ = belief khởi đầu trên không gian trạng thái.

**Ý nghĩa.** Là **cái neo của toàn bộ thang posterior**. Ba hệ quả trực tiếp: (a) carrier rỗng trả về $\pi_0$ — nghĩa là *"chưa quan sát"*, không phải *"đã biết sạch"*; (b) $\tau_{\text{sel}}$ là phân vị của $p_c$ nên **mọi hàng của bảng tham chiếu đều là hàm của $\pi_0$**; (c) tỉ lệ bằng chứng mà belief dùng là $p/\pi_0$, định nghĩa *đối với* $\pi_0$.

**Nếu sai.** $\pi_0$ lệch ⇒ cả bảng $\tau_{\text{sel}}$ lệch ⇒ điểm vận hành của B5/B6/Sentinel lệch ⇒ so sánh chính sách mất nghĩa. Đây là tham số có **fan-out lớn nhất** trong toàn hệ.

**Trạng thái: 0%, và tự khai.** `scoring.py:29` ghi nguyên văn: *"a MODEL CONSTANT, NOT derived from the dataset"*. Nặng hơn: nó **không nhất quán** với `WindowBelief(pi_attack=0.5)` — hai tham số cùng nói về base rate của tấn công, đặt độc lập, không ai bắt chúng khớp nhau.

**Thủ tục — đây là ứng dụng sạch nhất của Đ3, và gần như miễn phí.**

$\pi_0$ **không phải** thuộc tính của thế giới. Nó là **hệ quả tất định của thiết kế episode**: mỗi episode gieo **đúng một** payload vào **một** carrier, giữa $n$ item sống tại thời điểm quyết định. Vậy:

$$\pi_0 = \Pr[\text{có tấn công}] \times \frac{1}{\mathbb{E}[n_{\text{tổng}}]}$$

1. **$\mathbb{E}[n_{\text{tổng}}]$ đã đo rồi.** `costs.ITEMS_PER_AUDIT` = $5{,}34 + 1{,}12 + 1{,}55 + 4{,}50 = 12{,}51$ item sống, trên 20 episode có instrument.
2. **Thiết kế ghép cặp luôn gieo** ⇒ $\Pr[\text{có tấn công}] = 1$ trong nhánh nhiễm. Vậy $\pi_0 = 1/12{,}51 = \mathbf{0{,}0799}$.
3. **Đối chiếu.** Giá trị đang dùng là 0,10 — lệch **25%** so với một con số **suy được**. Không cần đo thêm gì; chỉ cần thay và sinh lại bảng.
4. **Buộc hai tham số khớp nhau.** Nếu belief dùng `pi_attack = 0.5` (defender không chắc có tấn công), thì $\pi_0$ mà *defender* dùng phải là $0{,}5 \times 0{,}0799 = 0{,}040$, còn $\pi_0$ mà *bộ sinh* dùng là 0,0799. Đây lại là luật T2: hai vai, hai tên biến. Hiện tại chúng là một biến mang giá trị của cả hai, tức defender được cho biết chắc chắn có tấn công.
5. **Đ2 làm kiểm chứng.** Sinh lại bảng ở $\pi_0 \in \{0{,}04; 0{,}08; 0{,}10; 0{,}20\}$, xem thứ hạng chính sách có giữ không. Nếu không giữ, $\pi_0$ trở thành một trục phải báo.
6. **$b_0$ suy tiếp từ $\pi_0$.** `WindowBelief` chia đều $\pi_{\text{attack}}$ trên các window khả thi — đó là *uniform trên lớp đã khai*, và lớp đã khai lại là $\Pi_A$ (ô hash H4). Nên $b_0$ không phải tham số độc lập: nó là $\pi_{\text{attack}}$ + lớp $\Pi_A$. Phải nói ra, vì "chọn $b_0$ uniform" nghe như một lựa chọn vô hại trong khi nó thừa hưởng toàn bộ hẹp hòi của $\Pi_A$.

**Kiểm chứng.** Test đã có: đổi $\theta$ phải làm `config_sha` dịch. Thêm: đổi $\pi_0$ **phải** làm `config_sha` dịch **và** làm mọi hàng `score_table.json` dịch — nếu bảng không dịch, bảng đang không thực sự tính từ $\pi_0$.

**Không tuyên bố.** $\pi_0$ suy ra ở trên là base rate **của benchmark này**, không phải của một workflow thật. Trong hệ thật, tỉ lệ nhiễm là đại lượng cần đo riêng, và $1/12{,}51$ không nói gì về nó.

---

### 3.4 $c$ — hằng số của Định lý 4

**Định nghĩa.** Hằng số không chiều trong

$$B \ \ge\ \frac{c\,\bar\kappa\,(1+\chi)\,\log(1/\alpha)}{\gamma^2}\left(1 + \frac{\Delta}{H}K\right)$$

**Ý nghĩa.** $c$ hấp thu mọi thứ mà chứng minh để lại ở dạng "tỉ lệ với": nó dịch một phép đếm *số quan sát mang thông tin* thành một *hoá đơn audit*.

**Nếu sai — hoặc nếu không có.** Một cận có hằng số tự do thì **không bound cái gì cả**. Định lý 4 là kết quả quyết định của đề tài; không có $c$ thì nó là một phát biểu về hình dạng, không phải một phát biểu kiểm được.

**Trạng thái: 0%.** Không có mã nào kiểm cận này. `theory.py` tự viết: *"một chứng minh không có hệ quả chạy được thì không thể bị chính benchmark bên cạnh nó phản bác"*.

**Thủ tục — điểm mấu chốt là nhận ra Định lý 4 nói về BELIEF, và belief đã có mã.**

Phần IV Stage 9.8 đề nghị fit $c$ trên 240 game nhỏ giải bằng quy nạp lùi. **Không cần** — 240 game nhỏ chưa tồn tại, mà vế trái của cận đo được trực tiếp từ `belief.WindowBelief`:

1. **Định nghĩa vế trái đo được.** $B_{\min}(\text{ô})$ = ngân sách nhỏ nhất mà tại thời điểm quyết định $\sigma$, posterior của defender đặt khối lượng $\ge 1-\alpha$ lên window thật $(k,\iota,\sigma)$. Đây chính xác là "phân biệt trạng thái nhiễm với lành tính với sai số $\le \alpha$" — và `WindowBelief.window_mass()` trả về đúng phân phối đó.
2. **Lưới.** $(\Delta, \chi, \gamma) \times$ thang $B$. Với mỗi ô, tìm $B_{\min}$ bằng chia đôi trên $B$ (đơn điệu: thêm ngân sách không làm belief tệ đi — **phải assert điều này trước**, nếu không chia đôi vô nghĩa).
3. **Tính $c$ theo ô.**
   $$c_{\text{ô}} = \frac{B_{\min}\,\gamma^2}{\bar\kappa\,(1+\chi)\,\log(1/\alpha)\,(1 + \Delta K/H)}$$
4. **Báo phân bố, không chỉ báo max.** $c = \max_{\text{ô}} c_{\text{ô}}$ là $c$ nhỏ nhất làm cận giữ khắp nơi. Nhưng **phân bố của $c_{\text{ô}}$ mới là kết quả**: nếu $c_{\text{ô}}$ chênh nhau nhiều bậc thì **hình dạng cận sai**, và đó là một phát hiện, không phải một thất bại.
5. **Dùng $c_{\text{ô}}$ như một phép kiểm từng thừa số.** Đây là giá trị lớn nhất của thủ tục này: hồi quy $\log c_{\text{ô}}$ theo $\log(1+\chi)$, $\log(1+\Delta K/H)$, $\log(1/\gamma^2)$. Nếu cận đúng, mọi hệ số phải bằng 0 (vì các thừa số đã bị chia ra). Hệ số khác 0 đáng kể **chỉ ra đúng thừa số nào sai**. Cụ thể: nếu $c_{\text{ô}}$ giảm đơn điệu theo $\chi$, điều đó xác nhận phép đo *"$\chi$ rỗng"* ở §3.7 và nói thẳng rằng thừa số $(1+\chi)$ phải bỏ.
6. **Kiểm tính không chiều.** $c$ phải **không** phụ thuộc đơn vị của $\kappa$ (vì $\bar\kappa$ mang đơn vị). Chạy cả bảng placeholder và bảng USD, assert $c$ khớp. Đây là một test rẻ và bắt được cả một lớp lỗi.

**Kiểm chứng.** (a) đơn điệu của belief theo $B$; (b) bất biến đơn vị ở bước 6; (c) cận giữ trên **mọi** ô ở $c$ đã fit — và fit trên tập dev, kiểm trên các ô held-out.

**Không tuyên bố.** $c$ fit theo cách này là hằng số cho **cơ chế belief cụ thể** này, không phải cho defender tối ưu. Nó cho cận trên của $B$ cần thiết, không cho cận dưới thông tin lý thuyết.

---

### 3.5 $\lambda_Q$, $\lambda_T$ — trọng số của hàm mất mát

**Định nghĩa.** $L = \mathbb{E}[\text{harm}] + \lambda_Q \mathbb{E}[Q_{\text{false}}] + \lambda_T \mathbb{E}[T_{\text{lost}}]$.

**Ý nghĩa.** Cần đủ ba số hạng: ở $\lambda_Q = \lambda_T = 0$, "cách ly tất cả ở $t=1$" đạt harm **0,000 chính xác** ⇒ $L = 0$ ⇒ tối ưu, trong khi đã đóng cửa hệ thống. Đã đo đúng nghiệm suy biến đó.

**Trạng thái: 50%, và đây là trạng thái đúng.** Giá trị 0,10 / 0,50 tự khai *"NOT derived from anything"*. Nhưng đã thay bằng $\lambda_Q^\*$ (Đ4): trọng số nhỏ nhất làm đổi thứ hạng, giải **chính xác** bằng giao điểm các đường affine (không chia đôi — vì winner không đơn điệu theo $\lambda_Q$: một chính sách có $T_{\text{lost}}$ lớn sẽ ở ngoài cuộc đua ở **mọi** $\lambda_Q$). Đo được $\lambda_Q^\* \approx 0{,}036$–$0{,}05$ tuỳ cấu hình.

**Thủ tục — giữ Đ4, nhưng neo cái DẢI để $\lambda_Q^\*$ có nghĩa.**

$\lambda_Q^\* = 0{,}05$ chỉ là một kết luận nếu ta biết dải $\lambda_Q$ hợp lý nằm ở đâu. Vậy:

1. **$\lambda_T$ ≈ giá trị một task sạch** = chi phí chạy lại nó. Đo được: CPU-time (hoặc USD) của một task agent, đã có instrument.
2. **$\lambda_Q$ ≈ chi phí một lần cách ly nhầm** = $\eta_Q$ + chi phí dựng lại nội dung lành tính. Tức **$\lambda_Q$ và $\eta_Q$ là cùng một sự kiện định giá ở hai chỗ**: $\eta_Q$ ở ràng buộc ngân sách, $\lambda_Q$ ở hàm mất mát. Hiện chúng độc lập hoàn toàn — một điểm không nhất quán phải sửa hoặc phải khai.
3. **Phát biểu kết luận dưới dạng so sánh.** Nếu $\lambda_Q^\*$ nằm **dưới** dải đo được ⇒ thứ hạng vững trong mọi hệ thực tế. Nếu **trong** dải ⇒ không vững, và phải nói: *"Sentinel thắng ở tổ chức coi một lần cách ly nhầm rẻ hơn $1/20$ lần lọt lưới; ngược lại B5 thắng."* Đó là một phát biểu người đọc tự áp cho hệ của mình được.
4. **Chuẩn hoá đơn vị.** Ba số hạng của $L$ phải cùng đơn vị. Harm nhị phân, $Q_{\text{false}}$ đếm, $T_{\text{lost}}$ đếm — nên $\lambda$ mang đơn vị "harm trên một sự kiện". Phải nói ra, nếu không $\lambda$ là một số không đơn vị đặt cạnh hai phép đếm.

**Kiểm chứng.** `lambda_q_star` trả `None` khi không trọng số nào trong $(0, 5]$ đổi được winner — và `None` ở đó là tín hiệu **$Q_{\text{false}}$ chưa được đo thật**, không phải tín hiệu "một chính sách trội tuyệt đối". Phải có test phân biệt hai trường hợp đó.

**Không tuyên bố.** $\lambda$ là sở thích của tổ chức, không phải hằng số của tự nhiên. Không có giá trị "đúng" nào để đo tới.

---

### 3.6 $\kappa(k)$ — chi phí audit, và học thuyết đơn vị

**Định nghĩa.** Chi phí một lần audit carrier $k$ ở độ sâu 1.

**Trạng thái: 70%, nhưng có hai bảng song song và bảng đang dùng là placeholder.**

| Bảng | Giá trị | $\chi$ | Ai dùng |
|---|---|---|---|
| placeholder (chi phí **theo giai đoạn** của bản thảo §7) | 0,4 / 0,9 / 1,6 / 4,1 | **2,114** | `experiment.py` — tức **mọi bảng chính** |
| USD-judge (đo trên hệ này) | $\{5{,}34; 1{,}12; 1{,}55; 4{,}50\} \times 0{,}594/1200$ | **1,3493** | chỉ `spikes/ssg_sweep.py` |

Ba điều phải xử lý, không thể để nguyên:

1. **Thứ tự carrier gần như đảo.** memory từ **rẻ nhất** (0,4) thành **đắt nhất** (0,00264). Vì $\chi$ đo **hình dạng** vector chi phí chứ không đo độ lớn, đây không phải phép đổi thang — nó **đổi carrier mà attacker muốn**, tức đổi luôn trò chơi.
2. **$\kappa_{\text{branch}} = \kappa_{\text{commit}} = 4{,}1$ chính xác** trong bảng placeholder. Đây là một **trùng hợp cấu tạo** triệt tiêu lợi thế giá của Sentinel khi attacker trốn vào `branch` — và nó đã đo được: mở lớp attacker từ 2 lên 4 carrier **đảo dấu kết luận** ở $\Delta = 0$ ($+38{,}3\% \to -17{,}8\%$). Mọi bảng chính hiện mang trùng hợp này.
3. **$\chi(\text{USD}) = 1{,}3493$ tái tạo đúng $\chi = 1{,}34$ của bản thảo.** Nếu đây là trùng hợp độc lập thì nó là bằng chứng rất mạnh và **phải được nói ra**. Nếu `ITEMS_PER_AUDIT` từng được chỉnh để ra 1,34 thì đó là fit ngược và **phải khai**. `costs.py` hiện không nhắc gì đến con số này — khoảng trống đó phải được lấp bằng một câu, theo hướng nào cũng được, nhưng phải có.

**Thủ tục.**

1. **Đo theo CPU-phút song song với USD.** Bốn checkpoint, ≥30 lần trên commit mẫu, đo CPU-time (user+sys, **không** wall-clock), pin CPU frequency, lấy trung vị, báo cả phương sai. Lý do cần cả hai: USD-judge trôi theo giá và theo model (phải pin version + ghi bảng giá), CPU-phút thì không.
2. **Học thuyết đơn vị — nâng lên thành nguyên tắc.** $\chi$ là hình dạng nên **đơn vị triệt tiêu trong $\chi$ nhưng KHÔNG triệt tiêu trong $B$**. Nên ngân sách phải phát biểu dưới dạng **phần của hoá đơn audit đầy đủ**, không phải một con số tuyệt đối. `costs.budget_fraction()` đã làm đúng điều này (17,95 trên hoá đơn 7,0/bước = 32,1%); cần nâng từ một tiện ích thành một luật, và mọi bảng phải in phần trăm đó.
3. **Công bố công thức $\bar\kappa$ tường minh** — khuyến nghị arithmetic mean, đã thi hành trong `policies.chi_of`, và đã khai thẳng rằng $0{,}4/0{,}9/1{,}6/4{,}1$ cho **2,11 không phải 1,34**.
4. **Chọn một bảng cho đường chính** và gọi `costs.install()` trong `experiment.py`, hoặc khai rõ mọi bảng dùng placeholder.
5. **Độ sâu.** $\kappa(k, \text{depth})$ và $d' \propto \sqrt{\text{depth}}$ đã cài, nhưng **không policy nào phát ra `"memory@2"`** — nên hệ quả then chốt của Định lý 4 (*"tăng độ sâu không mua được **danh tính** carrier"*) chưa có nhánh thực nghiệm. Đây là một test quan trọng còn thiếu: B1 ở độ sâu 1, 2, 4 phải **không** cải thiện theo trục $\Delta$, trong khi phân bổ upstream thì có.

---

### 3.7 Quy ước neo khi quét $\chi$ — một tham số bị bỏ sót hoàn toàn

**Đây là mục quan trọng nhất của tài liệu này**, vì nó là một tham số mà **không tài liệu nào trước đây nhận ra là tham số**.

**Định nghĩa.** Khi quét trục $\chi$, phải giữ **cái gì** cố định? Ba lựa chọn, ba trò chơi khác nhau:

| Phương án | Giữ cố định | $\sum_k \kappa_k$ khi $\chi$ tăng | KT3 (lợi thế thu hẹp khi $\chi$↑) |
|---|---|---|---|
| **A. Neo trung bình** (hiện hành) | $\bar\kappa$ | **bất biến** = 8,0 | **FAIL** — trục $\chi$ hoàn toàn rỗng |
| **B. Neo nhỏ nhất** | $\kappa_{\min}$ | tăng: 8,0 → 24,24 | **PASS** — thu hẹp đúng chiều (39,7% → 36,1%) |
| **C. Commit theo carrier** | $\bar\kappa$, $v(t) \to v(k,t)$ | bất biến | **FAIL** — vẫn rỗng do đối xứng |

**Ý nghĩa, và vì sao $\chi$ rỗng là chuyện CẤU TRÚC chứ không phải đo sai.** Dưới phương án A, harm **không phụ thuộc carrier $k$**, nên attacker best-response luôn khai thác carrier có độ phủ thấp nhất, nên nghiệm minimax buộc phải **san bằng độ phủ trên mọi carrier**: $u[k,t] = U(t)$. Khi đó

$$\sum_k \kappa_k \sum_t u[k,t] = \Big(\sum_k \kappa_k\Big) \cdot \sum_t U(t)$$

chỉ phụ thuộc **tổng** chi phí, hoàn toàn không phụ thuộc **phân bố**. Đo được: $\text{minimax}(\chi=0) = \text{minimax}(\chi=1{,}34) = 0{,}289333$, lệch đúng 0, và gain bất biến $+39{,}7\%$ ở $\Delta = 2$ qua cả bốn giá trị $\chi$.

**Nếu sai.** Đây là **một trong hai trục của ranh giới vùng** — thứ mà Phần IV gọi là "đóng góp hữu ích nhất". Nếu giữ phương án A, RQ2 không có nội dung thực nghiệm và ranh giới vùng chỉ còn một trục sống.

**Trạng thái: đã đo cả ba phương án, chưa chốt.** Có một dấu hiệu mâu thuẫn phải giải trước khi chốt: phép quét *runtime* trước đó (A3) báo $\chi$ **có** dịch crossover, $\Delta^\* : 1{,}67 \to 2{,}83$, trong khi phép quét *minimax LP* báo bất biến. Hai phép đo trên hai đường khác nhau — phải giải thích được vì sao, hoặc một trong hai sai.

**Thủ tục.**

1. **Khai phương án như một quyết định loại A, trước khi chạy.** Nó không phải một chi tiết cài đặt; nó quyết định KT3 pass hay fail. Khai sau khi thấy kết quả là HARKing.
2. **Chọn phương án B**, với lý lẽ ngữ nghĩa (không phải lý lẽ kết quả): $\chi$ nghĩa là *"audit một memory record thì rẻ, audit toàn bộ dẫn xuất của một branch thì đắt"*. Cái tăng khi carrier phân hoá là **chi phí của carrier đắt**, không phải "carrier đắt tăng thì carrier rẻ giảm bù lại". Neo $\kappa_{\min}$ là bản dịch đúng của câu đó; neo $\bar\kappa$ là một tiện lợi toán học.
3. **Nhưng B làm $\sum \kappa$ tăng 3× ⇒ ngân sách hiệu dụng giảm.** Nên phải dùng học thuyết đơn vị ở §3.6 bước 2: $B$ phát biểu theo **phần của hoá đơn đầy đủ**, để quét $\chi$ không bí mật quét luôn ngân sách. Nếu không làm, trục RQ2 bị lẫn với chính đại lượng RQ1 giữ cố định — đúng lớp lỗi mà `kappa_for_chi` đã cảnh báo.
4. **Giải mâu thuẫn A3 vs T2.** Chạy cả hai đường (runtime Sentinel, và minimax LP) trên **cùng** một phương án neo, cùng một $B$-theo-phần-trăm. Nếu $\chi$ vẫn rỗng trên LP mà không rỗng trên runtime, thì kết luận là: *$\chi$ tác động qua **ràng buộc cứng từng ván** (knapsack), không qua nghiệm minimax kỳ vọng* — một phát biểu chính xác hơn và thú vị hơn cả hai phát biểu hiện có, và nó nối thẳng với gap 13,29% ở §4.4.
5. **Báo cả ba phương án trong luận văn.** Lớp $\Pi_A$ đã được xử lý theo lối này (B7 và B7U báo cạnh nhau, vì *lớp đã khai là một phần của tuyên bố*). Quy ước neo $\chi$ đáng được đối xử y như vậy.

**Không tuyên bố.** Không có phương án nào "đúng"; có phương án **được khai** và phương án **bị ngầm**. Lỗi duy nhất là để nó ngầm.

---

### 3.8 $\Delta$ thực — độ trễ nhân quả trong workflow thật

**Định nghĩa.** Số task (hoặc commit) giữa lúc trạng thái thượng nguồn bị sửa và lúc artifact hạ nguồn gãy.

**Ý nghĩa.** Crossover $\approx 2$ chỉ thuyết phục nếu $\Delta$ thực tế **cùng thang**. Đây là con số mà người làm thực tế sẽ đo cho hệ của họ rồi tra Hệ quả 5.

**Trạng thái: 60%.** Đã đo bằng `tools/measure_delta.py` trên git history **của chính repo luận văn**: $n = 29$, min 0, p25 1, **trung vị 3**, p75 10, p90 23,2, max 26, mean 6,97. Kết quả ủng hộ đề tài (trung vị 3 > crossover 2). Nhưng đó là *dogfooding*, không phải quy trình Stage 3.7.

**Thủ tục để nâng lên 100%.**

1. **Co-change / logical coupling** trên 12 repo SWE-bench: tính support và confidence cho từng cặp module.
2. **Lọc tương quan giả bằng import graph**: cặp module không có đường phụ thuộc nào thì co-change là đồng thời, không phải nhân quả.
3. **`git bisect run <test>`** để tìm commit thực sự gây gãy, thay vì suy từ khoảng cách thời gian.
4. **Đếm khoảng cách commit** giữa "A đổi" và "B gãy" ⇒ phân bố $\Delta$ thực, báo theo từng repo.
5. **Đối chiếu với dogfood $n=29$.** Nếu hai phân bố cùng thang, con số dogfood trở thành một xác nhận độc lập — giá trị hơn nhiều so với việc bỏ nó đi.
6. **Mở lưới $\Delta$.** Lưới hiện tại là $\{0,1,2,4\}$; **$\Delta = 8$ vắng mặt** trong cả `experiment.py` và `SWEEP_DELTAS`, mà p75 đo được là 10 — tức ô mà đề tài mạnh nhất, và cũng là ô thực tế nhất, đang không được chạy.

**Không tuyên bố.** Sắp theo `created_at` cho **thứ tự thời gian**, không cho nhân quả; topic-overlap cho **tương quan**. Quan hệ phụ thuộc thật phải đo riêng, đúng bằng thủ tục trên.

---

### 3.9 $\rho$ — covering radius của thư viện chính sách

**Định nghĩa.** $\rho = \max_{\pi^\*} \min_{\pi \in \Pi} \mathrm{TV}(\pi, \pi^\*)$ — bán kính $\varepsilon$-net của thư viện trong không gian phân phối hành động.

**Ý nghĩa.** Mệnh đề 6 dùng $\rho$ để định giá việc thu hẹp từ không gian chính sách vô hạn chiều xuống một thư viện hữu hạn: $V(\Pi) - V^\* \le H\rho\,\mathrm{range}(L)$.

**Trạng thái: 40%, và đang đo sai không gian.** `theory.covering_radius` đo trong không gian **audit-marginal** (phân phối chi tiêu trên 5 hành động), không phải TV giữa phân phối hành động tại mỗi belief. Docstring tự khai giới hạn: *"hai chính sách cùng marginal nhưng khác timing thì không phân biệt được"* — mà **timing chính là toàn bộ nội dung của bài toán này**. Đo được $\rho = 0{,}894$ trên 10 chính sách (bản thảo báo 0,07). Thêm nữa, nó đo trên `REGISTRY` — vốn là *baseline + biến thể*, không phải thư viện 28 chính sách ba họ mà Mệnh đề 6 nói về.

**Thủ tục — hai lựa chọn, phải chọn một và nói ra.**

**Lựa chọn (a) — đo đúng không gian.** Ghi lại, tại mỗi task $t$, **vector xác suất hành động** mà chính sách cam kết (không phải hành động đã bốc). Mọi chính sách trong thư viện đã là phân phối tường minh, nên vector này lấy được không cần ước lượng. Rồi
$$\mathrm{TV}(\pi, \pi') = \frac{1}{H}\sum_t \frac{1}{2}\sum_a |\pi_t(a) - \pi'_t(a)|$$
Timing bây giờ có mặt, vì chỉ số $t$ có mặt.

**Lựa chọn (b) — hạ phạm vi Mệnh đề 6.** Phát biểu lại nó trên proxy marginal, và nói thẳng rằng cận không bao phủ chênh lệch về timing. Trung thực, và rẻ.

**Trong cả hai trường hợp**, còn thiếu $\pi^\*$ để lấy max: cần **optimum thật** trên ít nhất một lớp game giải được. Hiện `game.py` cho minimax bằng fictitious play **trên chính ma trận của thư viện** — tức một trần *bên trong* thư viện, không phải optimum của không gian đầy đủ. Test đã tự khai điều này: *"hằng số của nó KHÔNG được kiểm"*. Nên đường duy nhất tới $\rho$ thật là dựng lớp game nhỏ ($KH \le 40$ sau rời rạc hoá belief) và giải bằng quy nạp lùi — việc mà Phần IV đặt ở Stage 6C và hiện chưa có.

**Kiểm chứng.** Đã có và cần giữ: thêm thành viên vào thư viện **không được** làm $\rho$ tăng; nếu tăng thì đại lượng đó không phải covering radius và Mệnh đề 6 không bound gì. Và: $V^\*$ không được tăng khi thư viện lớn lên.

---

## 4. Bốn khuôn đã kiểm nghiệm — dùng lại, đừng thiết kế lại

Phần này tồn tại vì *"làm một cách khoa học nhất"* được trả lời tốt nhất bằng cách chỉ vào những khuôn đã chạy được trong chính dự án.

### 4.1 Khuôn Đ1 — $\tau_{\text{sel}}$: cách biến một ngưỡng thành một phép đo

Phần VI xếp $\tau$ vào loại C (chọn có neo). Mã đã đưa nó lên loại B (đo):

- **Định nghĩa toán học trước, số sau.** $\tau_{\text{sel}}(n_c, \text{setting}, K)$ = phân vị $(1 - \alpha_c(K))$ của $p_c$ trên carrier **sạch**, với $\alpha_c(K) = 1-(1-\alpha_{\text{task}})^{1/K}$. Không còn gì để chọn: cho $\alpha_{\text{task}} = 0{,}05$, ngưỡng là một đại lượng **tính được**.
- **Sinh bằng script, không sửa tay.** 800.000 mẫu mỗi ô, $n = 0..30$, seed 20260915. Script **từ chối ghi đè** nếu file đã tồn tại; có chế độ `--check` sinh lại và so bytes.
- **Provenance nằm trong chính file JSON**: 20 field gồm seed, số mẫu, phiên bản Python, ngày đo, luật ngưỡng, `status: MEASURED`, và một cảnh báo *"KHÔNG sửa tay"*.
- **Và nó phát hiện một artefact mà không ai đoán trước**: hướng phụ thuộc theo $n$ **đảo chiều** giữa weak (0,299 → 0,174) và strong (0,153 → 0,246). Giữ $\tau$ cố định sẽ tạo một thiên lệch **đổi dấu** giữa hai nhánh của RQ4 — không phải một offset hằng số trừ đi được.

> **Rút ra:** đại lượng nào định nghĩa được như một **phân vị của phân bố null** thì luôn đo được, không bao giờ phải chọn. Áp ngay cho $\pi_0$ (§3.3) và $\eta_Q$ (§3.2).

### 4.2 Khuôn Đ4 — $\varepsilon^\*$: định nghĩa ngưỡng trước, chấp nhận kết quả âm

- **Hai chiều là điều kiện tiên quyết.** $\varepsilon$ chỉ là một *ngân sách* nếu tiêu nhiều thì **được truy xuất chắc hơn** (chiều lợi) **và dễ bị nhận ra hơn** (chiều tốn). Khuyết tật đầu tiên phát hiện được: $\varepsilon$ chỉ có chiều tốn ⇒ không phải ngân sách, chỉ là một cách tự làm khó mình.
- **Lưới và tiêu chí chốt trong test viết theo TDD, trước khi cài.**
- **Kết quả âm được ship, không bị chôn:** $\varepsilon^\* = 0$; và trên nền benign **trung thực** (`natural=True`) thì $\varepsilon^\*$ **RỖNG** — không một $\varepsilon$, không một $\Delta$, không một split nào trong 20 vượt được trần 0,56 (tốt nhất 0,7056).
- **Phạm vi được nói kèm mọi con số.** AUC $= 0{,}5414$ là phát biểu về **bốn** đặc trưng $F_{\text{match}}$; một quy tắc **không tham số** trên trục `topic` — cột thứ năm, không nằm trong cổng — tách được payload ở **AUC 0,9492** trên đúng corpus đó. Con số 0,5414 không phải phát biểu về tính khó phân biệt nói chung, và tài liệu nói ra điều đó ngay trên bảng.

> **Rút ra:** một ngưỡng chỉ có nghĩa khi tập đặc trưng, nền so sánh, và salt subset đều được nêu cạnh nó. Áp cho mọi cổng AUC về sau.

### 4.3 Khuôn Đ2 — quét $d'$: bỏ ba điểm khai báo, lấy cả đường cong

- **Tham số hoá một chiều đúng nghĩa.** Giữ $\tau_{\det} = z(1-0{,}12)$ **cố định**, quét $d'$, nên $\varphi = 0{,}12$ ở **mọi** điểm và $\psi = \Phi(d' - \tau_{\det})$ là đại lượng dẫn xuất. Ba setting cũ dịch $\psi$ **và** $\varphi$ cùng lúc ⇒ chênh lệch giữa hai setting không quy được cho bên nào. Có một test riêng giữ điều này.
- **Confound được khai, không bị phát hiện sau.** Chuỗi `setting` đồng thời là khoá tra bảng $\tau_{\text{sel}}$, nên quét $d'$ mà giữ `setting="mid"` là để ngưỡng đứng yên ở mức hiệu chỉnh cho $d' = 2{,}211$. Đã sửa bằng cách sinh thêm các hàng `d0.0..d3.0` trong cùng bảng tham chiếu, và có test ghim cách viết tên hàng.
- **Tuyên bố đổi sang dạng ngưỡng:** $d'^\* = 2{,}85$ tại $\Delta = 2$; $0{,}95$ tại $\Delta = 4$; **null** tại $\Delta = 0, 1$ (không tồn tại điểm hoà vốn). Kèm **dải qua 5 seed corpus**: 2,6–3,0 và 1,0–1,4.
- **Và nó dẫn tới phát hiện quyết định của đề tài.** $d'$ đo được trên corpus qua cổng: $\le 0{,}50$, $\gamma \le 0{,}13$ — **dưới xa** $d'^\*$. Nghĩa là dưới detector bề mặt, **Sentinel không hoà vốn** so với audit-at-commit. Bản kế hoạch đã dự báo đúng điều này trước khi đo: *"Nếu $d'$ đo được nằm dưới $d'^\*$ của T1 — đó là phát hiện quan trọng nhất mà đề tài này có thể đưa ra."*

> **Rút ra:** khi một tham số không neo được vào thực nghiệm, đừng bảo vệ nó — quét nó và phát biểu dạng ngưỡng. Và **hai stage có thể loại trừ nhau**: cổng Stage 4 ($\mathrm{AUC} \le 0{,}56$) và ba mức Stage 5 ($\psi = 0{,}92$) **không cùng tồn tại được** trên một corpus. Đây là mâu thuẫn nội tại của tài liệu phương pháp luận, và nó chỉ lộ ra vì cả hai đầu đều đã được đo.

### 4.4 Khuôn Đ1 trên một độ lệch — gap kỳ vọng vs ràng buộc cứng

Lý thuyết ràng buộc ngân sách theo **kỳ vọng**: $\sum_k \kappa_k \sum_t u[k,t] + \kappa_c \sum_t v[t] \le B$. Runtime ràng buộc **cứng từng ván**: $\text{spent} + \text{cost}(a) \le B$. Hai cơ chế **không tương đương**, và độ lệch đo được bằng Monte Carlo 1000 lần:

| Đại lượng | LP (kỳ vọng) | Thực thi cứng | Gap |
|---|---|---|---|
| Độ phủ trung bình $u$ | 0,2805 | 0,2432 | **−13,29%** |
| Chi tiêu | 17,95 (100%) | 15,56 (86,7%) | −2,39 |

13,3% ngân sách bị kẹt dưới dạng "tiền lẻ" không đủ mua thêm một lượt audit nguyên vẹn ở cuối quy trình.

> **Rút ra:** mọi chỗ mà **lý thuyết và thực thi dùng hai định nghĩa khác nhau của cùng một ràng buộc** là một đại lượng đo được. Đo nó biến một "mối lo tiềm ẩn" thành một con số công bố được — và mọi con số độ lợi phải mang kèm chú thích *lạc quan ~13%*.

---

## 5. Thứ tự thi hành

Thứ tự bị ràng buộc bởi phụ thuộc, không phải bởi độ dễ.

```
   [T1] luật commit riêng trước    ─── phải có TRƯỚC mọi phép đo dưới đây
        │
        ├─► (1) π₀ suy ra = 1/12,51        ← Đ3, gần như miễn phí, fan-out lớn nhất
        │        │
        │        └─► sinh lại score_table  ← τ_sel là hàm của π₀ (ô hash H1)
        │                │
        │                └─► mọi bảng harm phải chạy lại
        │
        ├─► (2) β_k từ commit history      ← Đ1, độc lập, rẻ
        │        └─► tách β_world / β_model (T2) ─► ζ bắt đầu làm việc
        │
        ├─► (3) η_Q = c_gỡ + c_phục hồi    ← Đ1 + Đ3 (c_phục hồi tính từ dữ liệu đã có)
        │        └─► neo dải λ_Q ─► λ_Q* trở thành một kết luận
        │
        ├─► (4) chốt bảng κ + quy ước neo χ ← loại A, phải khai TRƯỚC khi chạy
        │        └─► B theo phần trăm hoá đơn ─► quét χ không lẫn với quét B
        │                └─► giải mâu thuẫn A3 (Δ*: 1,67→2,83) vs LP (χ rỗng)
        │
        └─► (5) c của Định lý 4 qua B_min của belief
                 └─► hồi quy log c_ô theo từng thừa số
                          └─► kiểm (1+χ) có thật hay không ── nối lại với (4)
```

**Ba việc không phụ thuộc gì, làm song song được:** mở lưới $\Delta$ đến 8 · đo $\kappa$ bằng CPU-phút · thêm permutation test $B = 1000$ cho cổng AUC.

**Hai việc là xây bộ giải, không phải ước lượng tham số:** lớp game nhỏ giải bằng quy nạp lùi (điều kiện cần cho $\rho$ thật và cho hằng số Mệnh đề 6), và thư viện chính sách tham số hoá. Nếu không làm, cách trung thực là hạ Định lý 4 và Mệnh đề 6 xuống *"kết quả lý thuyết chưa có kiểm chứng số"* — đúng như `theory.py` đã tự viết.

---

## 6. Bảng tổng hợp

| Tham số | Ý nghĩa một câu | Đường | Trạng thái | Việc còn lại |
|---|---|---|---|---|
| $\tau_{\text{sel}}$ | ngưỡng chọn carrier trên posterior | Đ1 | ✅ **đo** — 800k mẫu/ô, có provenance | sinh lại nếu $\pi_0$ đổi |
| AUC (cổng) | payload có tầm thường phân biệt được không | Đ1 | ✅ **đo** — C2ST, 20 split, cận trên CI | permutation test $B=1000$ |
| $\varepsilon^\*$ | ngân sách khả phân biệt lớn nhất còn chứng nhận được | Đ4 | ✅ **đo** — $=0$; rỗng trên nền trung thực | — |
| $d'^\*$ | ngưỡng hoà vốn của chất lượng detector | Đ4+Đ2 | ✅ **đo** — 2,85 / 0,95; null ở $\Delta\le1$ | — |
| $\gamma$ thực nghiệm | detector bề mặt mạnh tới đâu | Đ1 | ✅ **đo** — $d'\le0{,}50$, dưới $d'^\*$ | chuyển sang detector nội dung |
| gap knapsack | lý thuyết lạc quan hơn thực thi bao nhiêu | Đ1 | ✅ **đo** — $-13{,}29\%$ | in kèm mọi bảng độ lợi |
| $\zeta$ | sai số kernel, vế phải cận Định lý 3 | Đ1 | ✅ **đo** — 0,000 mock · 0,119 ở $\beta{=}0{,}5$ | tách hai vai để nó làm việc |
| $\chi$ | độ dị tính chi phí carrier | Đ1 | ✅ công thức công bố — 2,114 / 1,349 | chốt quy ước neo (§3.7) |
| $\kappa(k)$ | chi phí audit mỗi carrier | Đ1 | ⚠️ **70%** — hai bảng, đường chính dùng placeholder | CPU-phút; chốt một bảng; giải trùng hợp 1,34 |
| $\Delta$ thực | độ trễ nhân quả thật | Đ1 | ⚠️ **60%** — $n{=}29$ dogfood, trung vị 3 | co-change + bisect trên SWE-bench; mở lưới tới $\Delta{=}8$ |
| $\lambda_Q,\lambda_T$ | giá cách ly nhầm / mất task sạch | Đ4 | ⚠️ **50%** — $\lambda_Q^\*\approx0{,}04$–$0{,}05$ | neo dải; buộc khớp với $\eta_Q$ |
| $\rho$ | bán kính phủ của thư viện | Đ1 | ⚠️ **40%** — 0,894, sai không gian | đo TV theo $t$, **hoặc** hạ phạm vi Mệnh đề 6 |
| $\eta_Q$ | chi phí cách ly | Đ1+Đ3 | ❌ **30%** — placeholder 2,0 | $c_{\text{gỡ}}$ đo, $c_{\text{phục hồi}}$ tính; per-carrier |
| $\beta_k$ | tốc độ trôi lành tính | Đ1 | ❌ **0%** — knob 0,25 | luật ánh xạ + đếm commit + độ nhạy |
| $\pi_0 / b_0$ | tiên nghiệm mỗi item | **Đ3** | ❌ **0%** — fiat 0,10 | **suy ra $=0{,}080$**; buộc khớp `pi_attack` |
| $c$ | hằng số Định lý 4 | Đ1 | ❌ **0%** — không có mã | $B_{\min}$ từ belief + hồi quy từng thừa số |
| quy ước neo $\chi$ | giữ gì cố định khi quét $\chi$ | **loại A** | ❌ **chưa khai** — và đây là lý do $\chi$ rỗng | chọn phương án B, khai trước, báo cả ba |
| 28 chính sách, $N{=}2048$ | thư viện, particle filter | — | thay bằng minimax LP · posterior liệt kê chính xác | khai là lệch có chủ ý, không phải thiếu sót |

---

## 7. Những gì tài liệu này không tuyên bố

1. **Không có tham số nào ở đây là hằng số của tự nhiên.** $\lambda$ là sở thích tổ chức; $\pi_0$ là hệ quả thiết kế; $\beta$ và $\kappa$ là thuộc tính của một quần thể repo cụ thể. Mỗi con số đi kèm một câu về quần thể nó được đo trên.
2. **$\varepsilon$, $\theta$, $\pi_0$ suy được là số của benchmark này, không phải của hệ thật.** Chúng làm cho benchmark có nghĩa, không làm cho thế giới có nghĩa.
3. **Mọi thủ tục đo bằng git history đo tương quan tiến hoá.** Co-change không phải nhân quả; luật ánh xạ commit → carrier là tương đồng có lý lẽ, chưa được kiểm chứng đối với agent thật.
4. **Số của học viên sẽ khác bản thảo, và đó là đúng đắn.** $\chi$ của bạn không phải 1,34 nếu bạn công bố công thức $\bar\kappa$ của mình; $\rho$ của bạn không phải 0,07 nếu bạn đo trên thư viện của mình. Trình bày quy trình tái lập được, rồi nói thẳng rằng con số bản thảo không tái tạo được.
5. **Harm vẫn do marker proxy chấm.** Họ test ẩn H1 neo được 5/500 instance, sau cổng V1 còn 1/500, trần cho bất kỳ template đơn nào $\approx 11\%$. Độ lệch proxy vs test thật **đã đo**: khớp 30/30 trên hai mode mô phỏng sinh được, 0/30 trên hai mode nó không sinh được, và **hướng** của sai số được báo (mode C hạ thấp harm, mode D thổi phồng). Mọi kết luận phải mang chữ **semi-synthetic**.
6. **Không tham số nào ở đây sửa được ba lỗ cấu trúc**: thư viện 28 chính sách, 240 game nhỏ, và quy mô thật (14 workflow khả dụng ở $H{=}8$ trên Verified, so với 100 mà Stage 9 đòi). Ước lượng tham số tốt trên một lưới nhỏ vẫn là một lưới nhỏ.
