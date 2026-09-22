# MATH FOUNDATION — Cơ sở toán học cho đề tài FSE-2027-15 (Sentinel)

**Đề tài:** *Where to Look: Audit-Allocation Games against Adaptive Persistent Poisoning*
**Học viên:** Nguyễn Hữu Trưởng — 2470573 · **GVHD:** TS. Lê Xuân Bách (RAISE Lab)
**Mục đích của file này:** gom toàn bộ công cụ toán cần dùng, từ kiến thức nền tối thiểu đến khung chứng minh của bốn kết quả lý thuyết, thành một tài liệu tra cứu duy nhất.

> **Quy ước đánh dấu trong file**
> — Nội dung **trích nguyên văn** từ manuscript được ghi rõ "(manuscript §x)".
> — Nội dung là **tái dựng của tôi** (suy ra từ manuscript, chưa được xác nhận) được đánh dấu ⟨**tái dựng**⟩ — phải đối chiếu với GVHD trước khi đưa vào luận văn.
> — Khối `> 📐` giải thích trực giác cho một khái niệm toán trước khi phát biểu chính thức.

> **Lưu ý về đánh số định lý.** Manuscript đánh số **Theorem 3 · Theorem 4 · Corollary 5 · Proposition 6**. Các tài liệu tiếng Việt trước đó trong vault gọi chúng là "Định lý 1–4" theo thứ tự xuất hiện. File này dùng **số của manuscript** để tra cứu không nhầm.

---

# MỤC LỤC

| Phần | Nội dung                                                     | Dùng cho                 |
| ---- | ------------------------------------------------------------ | ------------------------ |
| 1    | Kiến thức nền tối thiểu: lồi, xác suất, quy hoạch tuyến tính | Toàn bộ                  |
| 2    | Lý thuyết trò chơi: Nash → minimax → Stackelberg             | Mô hình hóa (Ch.3)       |
| 3    | Stackelberg Security Games và biểu diễn coverage             | Cơ chế (Ch.4)            |
| 4    | Ra quyết định tuần tự: MDP → POMDP → belief MDP              | Belief state, Theorem 3  |
| 5    | Kiểm định giả thuyết và giới hạn mẫu                         | **Theorem 4**            |
| 6    | Tối ưu hóa bền vững và tổn thất do giới hạn                  | Theorem 3, Proposition 6 |
| 7    | Bốn kết quả lý thuyết: phát biểu + khung chứng minh          | Ch.4 luận văn            |
| 8    | Đặc tả formal đầy đủ của Sentinel                            | Ch.3–4 luận văn          |
| 9    | Lộ trình học toán có đầu ra kiểm chứng được                  | Giai đoạn 0              |
| 10   | Phụ lục: ký hiệu, sai lầm thường gặp, từ điển                | Tra cứu                  |

---

# PHẦN 1 — KIẾN THỨC NỀN TỐI THIỂU

Đây là danh sách **đủ và không thừa**. Không cần học giải tích hàm, không cần đo lường (measure theory), không cần tối ưu phi tuyến nâng cao.

## 1.1 Tập lồi và đơn hình

**Định nghĩa 1.1 (Đơn hình xác suất).** Với tập hữu hạn $S = \{s_1,\dots,s_n\}$,
$$\Delta(S) = \Big\{\, p \in \mathbb{R}^n : p_i \ge 0,\ \sum_{i=1}^n p_i = 1 \,\Big\}.$$
Đây là tập mọi **phân bố xác suất** trên $S$, và là không gian chiến lược hỗn hợp của người chơi.

**Tính chất cần nhớ:**

| Tính chất | Phát biểu | Vì sao cần |
|---|---|---|
| Lồi | $p, q \in \Delta(S) \Rightarrow \lambda p + (1-\lambda)q \in \Delta(S)$ | Bảo đảm bài toán tối ưu là LP |
| Compact | Đóng và bị chặn | Bảo đảm cực trị **đạt được** (Weierstrass) |
| Đỉnh (extreme points) | Chính là các chiến lược thuần $e_i$ | Lý do LP luôn có nghiệm tại đỉnh, và lý do best response của attacker luôn có thể chọn **thuần** |

**Định nghĩa 1.2 (Hàm Lipschitz).** $f$ là $L$-Lipschitz theo chuẩn $\|\cdot\|$ nếu $|f(x)-f(y)| \le L\|x-y\|$.

> 📐 **Vì sao Lipschitz là khái niệm quan trọng nhất của Phần 6–7**
> Toàn bộ Theorem 3 và Proposition 6 chỉ là một câu: *"giá trị trò chơi thay đổi không nhanh hơn tuyến tính so với sai số đầu vào, và sai số cộng dồn qua $H$ bước."* Hằng số Lipschitz ở đây là $\mathrm{range}(L) = \max L - \min L$ — biên độ của hàm mất mát.

## 1.2 Xác suất

**Công thức Bayes** (hòn đá tảng của belief update):
$$\Pr[s \mid o] = \frac{\Pr[o \mid s]\,\Pr[s]}{\sum_{s'}\Pr[o \mid s']\,\Pr[s']}.$$

**Định nghĩa 1.3 (Khoảng cách biến phân toàn phần — total variation).** Với hai phân bố $P,Q$ trên cùng không gian hữu hạn,
$$\|P-Q\|_{TV} = \tfrac12\sum_{x}|P(x)-Q(x)| = \max_{A}|P(A)-Q(A)|.$$

Đây là **đúng** loại chuẩn mà Assumption 2 của manuscript dùng để đo bất định về transition kernel ($\zeta$).

**Định nghĩa 1.4 (Phân kỳ KL).** $\mathrm{KL}(P\|Q) = \sum_x P(x)\log\frac{P(x)}{Q(x)}$.

**Bất đẳng thức Pinsker** (cầu nối TV ↔ KL — cần cho Theorem 4):
$$\|P-Q\|_{TV} \le \sqrt{\tfrac12 \mathrm{KL}(P\|Q)}.$$

**Trường hợp Bernoulli** (dùng trực tiếp cho detector): với $P = \mathrm{Bern}(\psi)$, $Q = \mathrm{Bern}(\phi)$ và $\gamma = \psi-\phi$,
$$\|P-Q\|_{TV} = \gamma, \qquad \mathrm{KL}(P\|Q) \;\ge\; 2\gamma^2 .$$

> 📐 **Đây chính là nguồn gốc của số hạng $\gamma^{-2}$ trong Theorem 4.** Hai giả thuyết càng giống nhau (γ nhỏ) thì càng cần nhiều mẫu để phân biệt, và số mẫu tỉ lệ nghịch với **bình phương** của margin.

**Bất đẳng thức Hoeffding** (dùng để đặt cận sai số hữu hạn mẫu): với $X_1,\dots,X_n$ độc lập trong $[0,1]$,
$$\Pr\Big[\big|\tfrac1n\textstyle\sum X_i - \mu\big| \ge t\Big] \le 2e^{-2nt^2}.$$

## 1.3 Quy hoạch tuyến tính

**Dạng chuẩn.** $\min_x c^\top x$ s.t. $Ax \le b$, $x \ge 0$.

**Định lý 1.5 (Đối ngẫu mạnh).** Nếu bài toán gốc (primal) khả thi và bị chặn thì bài toán đối ngẫu $\max_y b^\top y$ s.t. $A^\top y \le c$, $y \le 0$ cũng vậy, và **hai giá trị tối ưu bằng nhau**.

**Bù trừ (complementary slackness).** Tại nghiệm tối ưu: ràng buộc nào **không chặt** thì biến đối ngẫu tương ứng bằng 0, và ngược lại.

> 📐 **Vì sao đối ngẫu quan trọng cho đề tài này**
> Trong LP minimax của Sentinel, **biến đối ngẫu của ràng buộc "$z \ge$ harm của hành động $a$" chính là xác suất mà attacker tối ưu chọn hành động $a$**. Nói cách khác: giải LP của defender là giải luôn chiến lược hỗn hợp của attacker. Đây không phải mẹo — đó là định lý minimax được viết lại. Khi debug, hãy in ra biến đối ngẫu: nó cho biết attacker đang nhắm vào đâu.

**Công cụ:** `scipy.optimize.linprog(method="highs")` đủ cho toàn bộ đề tài ở quy mô smoke test và trò chơi nhỏ. Quy mô lớn hơn: `PuLP` + CBC, hoặc Gurobi nếu lab có license.

---

# PHẦN 2 — LÝ THUYẾT TRÒ CHƠI

## 2.1 Trò chơi dạng chuẩn

**Định nghĩa 2.1.** Một trò chơi dạng chuẩn hai người là bộ ba $\langle (A_1,A_2), (u_1,u_2)\rangle$ với $A_i$ là tập hành động và $u_i : A_1\times A_2 \to \mathbb{R}$ là hàm lợi ích.

**Chiến lược hỗn hợp** $x \in \Delta(A_1)$, $y \in \Delta(A_2)$. Lợi ích kỳ vọng là **song tuyến tính**:
$$u_1(x,y) = \sum_{a\in A_1}\sum_{b\in A_2} x_a\, y_b\, u_1(a,b) = x^\top U_1 y .$$

> 📐 Tính song tuyến tính là lý do mọi thứ sau đây giải được bằng LP. Nếu payoff phi tuyến theo chiến lược hỗn hợp thì toàn bộ bộ công cụ này sụp.

## 2.2 Best response và cân bằng Nash

**Định nghĩa 2.2 (Best response).** $\mathrm{BR}_2(x) = \arg\max_{y\in\Delta(A_2)} u_2(x,y)$.

**Bổ đề 2.3.** Tập best response luôn chứa **một chiến lược thuần**. *(Vì $u_2(x,\cdot)$ tuyến tính trên đơn hình compact ⇒ cực đại đạt tại một đỉnh.)*

> 📐 **Bổ đề 2.3 là thứ khiến smoke test chạy được.** Nó cho phép tìm best response của attacker bằng **liệt kê hữu hạn** trên $(k,\iota,\sigma)$ thay vì tối ưu trên một không gian liên tục. Đúng như manuscript §7: *"the attacker's best response within $\Pi_A$ is computed by enumeration over $(k,\iota,\sigma)$"*.

**Định nghĩa 2.4 (Cân bằng Nash).** $(x^\*,y^\*)$ sao cho $x^\* \in \mathrm{BR}_1(y^\*)$ và $y^\* \in \mathrm{BR}_2(x^\*)$.

**Định lý 2.5 (Nash, 1951).** Mọi trò chơi hữu hạn đều có ít nhất một cân bằng Nash hỗn hợp.

## 2.3 Trò chơi tổng-không và định lý minimax

**Định nghĩa 2.6.** Trò chơi tổng-không: $u_1 = -u_2 =: u$.

**Định lý 2.7 (von Neumann, 1928).** Với trò chơi tổng-không hữu hạn:
$$\max_{x\in\Delta(A_1)}\ \min_{y\in\Delta(A_2)} x^\top U y \;=\; \min_{y}\ \max_{x} x^\top U y \;=:\; V^\star .$$

**Hệ quả 2.8 (Giải bằng LP).** Giá trị $V^\star$ và chiến lược tối ưu của người chơi tối thiểu hóa là nghiệm của
$$\min_{y,\,z} \; z \quad \text{s.t.}\quad z \;\ge\; (U y)_a \ \ \forall a \in A_1,\qquad y \in \Delta(A_2).$$

> 📐 **Đây chính xác là LP đã cài trong `smoke_repro.py`.** Biến $z$ là worst-case harm; mỗi ràng buộc ứng với **một hành động thuần của attacker** — và theo Bổ đề 2.3, liệt kê hành động thuần là đủ.

## 2.4 Trò chơi Stackelberg và cam kết

**Định nghĩa 2.9 (Trò chơi Stackelberg).** Leader cam kết $x \in \Delta(A_1)$ **trước** và công khai; follower quan sát $x$ rồi chọn $y \in \mathrm{BR}_2(x)$.

**Định nghĩa 2.10 (Strong Stackelberg Equilibrium — SSE).** Cặp $(x^*,y^*)$ với
$$x^* \in \arg\max_{x}\ u_1\big(x,\; \tau(x)\big), \qquad \tau(x) = \arg\max_{y\in \mathrm{BR}_2(x)} u_1(x,y).$$
Quy ước "tie-breaking có lợi cho leader" ($\tau$) là cái làm nên chữ **Strong**; không có nó, cực đại có thể không đạt được (WSE có thể không tồn tại).

**Định lý 2.11 (Giá trị của cam kết).** Trong mọi trò chơi hữu hạn, giá trị SSE của leader **≥** giá trị Nash tốt nhất của leader. Trong trò chơi tổng-không, hai giá trị **bằng nhau**.

> 📐 **Kết quả phản trực giác quan trọng nhất của cả đề tài.** "Đi trước và bị quan sát" nghe như bất lợi, nhưng cam kết một **phân bố** không bao giờ làm leader tệ hơn Nash — vì leader luôn có thể cam kết đúng chiến lược Nash của mình. Đây là lý do bài toán an ninh (bên phòng thủ buộc phải vận hành công khai) được mô hình bằng Stackelberg mà không mất mát gì.
>
> **Cảnh báo:** điều này chỉ đúng khi leader cam kết chiến lược **hỗn hợp** và chỉ tiết lộ **phân bố**, không tiết lộ **kết quả rút thăm**. Manuscript §5.3 nói đúng điều này: *"Sentinel commits to a distribution over audit actions and reveals only the distribution."*

## 2.5 Tính SSE — thuật toán Conitzer & Sandholm (EC 2006)

**Ý tưởng:** phân hoạch không gian chiến lược leader theo **hành động nào của follower là best response**. Với mỗi hành động thuần $b \in A_2$, giải một LP:

$$
\begin{aligned}
\max_{x}\quad & \sum_{a} x_a\, u_1(a,b) \\
\text{s.t.}\quad & \sum_a x_a\, u_2(a,b) \;\ge\; \sum_a x_a\, u_2(a,b') && \forall b' \in A_2 \quad (\text{$b$ là best response})\\
& x \in \Delta(A_1).
\end{aligned}
$$

Lấy nghiệm tốt nhất trong $|A_2|$ LP → SSE.

**Độ phức tạp:**

| Trường hợp | Kết quả |
|---|---|
| Một loại follower, hữu hạn | **Đa thức** — $|A_2|$ lần giải LP |
| Nhiều loại follower (Bayesian Stackelberg) | **NP-hard** |
| Trò chơi dạng mở rộng (extensive-form) | NP-hard nói chung |

> ⟨**tái dựng**⟩ Sentinel ở quy mô nhỏ rơi vào trường hợp thứ nhất (một lớp attacker khai báo $\Pi_A$) ⇒ giải được chính xác bằng LP. Manuscript §7 nói trò chơi nhỏ ($KH \le 40$) được giải **bằng backward induction trên belief MDP rời rạc hóa**, tức là dùng công cụ Phần 4 chứ không phải LP thuần — cần hỏi GVHD vì sao chọn backward induction thay vì multiple-LP.

## 2.6 Exploitability

**Định nghĩa 2.12.** Với chính sách defender $x$ đã triển khai,
$$\mathrm{Expl}(x) \;=\; \max_{a \in \Pi_A} h(x,a) \;-\; \min_{x'}\max_{a\in\Pi_A} h(x',a) \;=\; H(x) - H(x^\star) \;\ge\; 0 .$$

Đây là **độ lợi mà attacker thu được nhờ khai thác điểm yếu** của một chính sách không tối ưu. Manuscript §9.3 gọi là *"best-response gain against the deployed policy"*. Smoke test báo cáo giảm từ 0.34 xuống 0.09.

**Tính chất:** $\mathrm{Expl}(x) = 0 \iff x$ là nghiệm minimax. Đây là chỉ số kiểm tra tính đúng đắn tốt nhất cho phần cài đặt — nếu code của bạn tính ra chính sách có $\mathrm{Expl} < 0$, bạn có lỗi.

---

# PHẦN 3 — STACKELBERG SECURITY GAMES VÀ BIỂU DIỄN COVERAGE

## 3.1 Cấu trúc chuẩn của một SSG

| Thành phần | Ký hiệu | Trong Sentinel |
|---|---|---|
| Tập mục tiêu | $T = \{1,\dots,n\}$ | Các cặp (carrier $k$, task $t$) |
| Nguồn lực phòng thủ | $m$ đơn vị | Ngân sách audit $B$ |
| Lịch phân bổ (schedule) | $J \subseteq T$ khả thi | Tập audit thực hiện được trong một workflow |
| Chiến lược hỗn hợp defender | phân bố trên các schedule | phân bố trên các kế hoạch audit |
| **Vector coverage** | $c \in [0,1]^n$, $c_i = \Pr[\text{target } i \text{ được bảo vệ}]$ | $u(k,t)$, $v(t)$ |
| Lợi ích attacker khi tấn công $i$ | $U^a(i,c_i) = c_i\,U^a_{\text{cov}}(i) + (1-c_i)\,U^a_{\text{unc}}(i)$ | $h = 1 - \psi\cdot\text{cov}$ |

**Điểm mấu chốt:** lợi ích của attacker là hàm **tuyến tính theo $c_i$**. Nhờ vậy toàn bộ bài toán rút gọn từ "phân bố trên $2^n$ schedule" xuống "vector $n$ chiều $c$" — đây là bước giảm chiều làm cho SSG khả thi về mặt tính toán.

## 3.2 Từ phân bố trên schedule về marginal coverage

**Vấn đề.** Không phải mọi vector $c \in [0,1]^n$ đều **hiện thực hóa được** bằng một phân bố trên các schedule khả thi.

**Định lý 3.1 (Birkhoff–von Neumann, dạng dùng trong SSG).** Nếu tập schedule khả thi là "đơn vị nguồn lực gán tự do cho từng target" thì mọi $c$ thỏa $\sum_i c_i \le m$, $0\le c_i\le 1$ đều hiện thực hóa được bằng một phân bố trên các schedule.

**Hệ quả:** với cấu trúc ngân sách đơn giản (mỗi audit tiêu $\kappa$, tổng $\le B$), có thể **tối ưu trực tiếp trên $c$** rồi phân rã ngược ra lịch ngẫu nhiên. Với ràng buộc lịch phức tạp (ví dụ không được audit hai lần cùng task), điều này **không còn đúng** và phải dùng thuật toán tách cột (column generation).

> ⟨**tái dựng**⟩ Mô hình trong `smoke_repro.py` dùng đúng phép rút gọn này: tối ưu trên $u(k,t), v(t) \in [0,1]$ với ràng buộc ngân sách tuyến tính. Cần xác nhận với GVHD rằng ràng buộc lịch của Sentinel đủ đơn giản để phép rút gọn hợp lệ — nếu không, cận thu được là **lạc quan** (một phần lý giải vì sao bản tái lập cho minimax 0.289 thay vì 0.43).

## 3.3 Best response của attacker

$$a^{BR}(c) = \arg\max_{a\in\Pi_A} h(c, a), \qquad h(c,a) \;=\; 1 - \psi\cdot\min\Big(1, \textstyle\sum_{(k,t)\in W(a)} c_{k,t}\Big)$$

với $W(a) = \{(k,t) : \iota \le t < \sigma\} \cup \{\text{commit at } \sigma\}$ là **cửa sổ quan sát hữu ích** của hành động $a$. ⟨**tái dựng**⟩

> 📐 **$W(a)$ là toàn bộ nội dung vật lý của đề tài, viết bằng một dòng.**
> — Với **audit-at-commit**: chỉ có đúng một ô trong $W(a)$ nằm trong vùng chính sách này phủ, **bất kể $\Delta$ bằng bao nhiêu**. Đó là mệnh đề "$B_{\text{commit}}$ độc lập với $\Delta$" của Theorem 4.
> — Với chính sách trải rộng: $|W(a)|$ tăng theo $\Delta$ ⇒ có thêm cơ hội.
> — Với $\Delta = 0$: $W(a)$ chỉ còn một ô, hai bên bằng nhau ⇒ đây là **chứng minh một dòng cho Corollary 5 ở biên $\Delta = 0$**.

## 3.4 LP minimax của Sentinel (dạng tường minh, đã cài đặt)

Biến: $u(k,t)$ với $k\in[K], t\in[H]$; $v(t)$ với $t\in[H]$; và $z$.

$$
\begin{aligned}
\min_{u,v,z}\quad & z \\
\text{s.t.}\quad & z \;\ge\; 1 - \psi\Big(\sum_{t=\iota}^{\sigma-1} u(k,t) \;+\; v(\sigma)\Big) && \forall\, a=(k,\iota,\sigma) \in \Pi_A \\
& \sum_{k}\kappa_k \sum_t u(k,t) \;+\; \kappa_c\sum_t v(t) \;\le\; B && \text{(ngân sách)}\\
& 0 \le u,v \le 1,\qquad 0 \le z \le 1 .
\end{aligned}
$$

**Ba ghi chú kỹ thuật:**

1. Hàm $\min(1,\cdot)$ **không** cần mô hình hóa tường minh: ràng buộc cận dưới cộng với $z \ge 0$ đã xử lý đúng trường hợp coverage vượt 1.
2. Số ràng buộc $= |\Pi_A| = K\cdot(H-\Delta)$ — tuyến tính, không bùng nổ.
3. **Biến đối ngẫu** của nhóm ràng buộc thứ nhất chính là chiến lược hỗn hợp tối ưu của attacker (Mục 1.3). In nó ra để kiểm tra: nếu khối lượng dồn vào một carrier duy nhất, chính sách của bạn đang để hở carrier đó.

---

# PHẦN 4 — RA QUYẾT ĐỊNH TUẦN TỰ DƯỚI BẤT ĐỊNH

## 4.1 MDP hữu hạn chân trời

**Định nghĩa 4.1.** $\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, P, R, H\rangle$ với $P(s'\mid s,a)$ là kernel chuyển trạng thái, $R(s,a)$ là phần thưởng, $H$ là chân trời hữu hạn.

**Phương trình Bellman (backward induction).** Đặt $V_H(s) = 0$; với $t = H-1, \dots, 0$:
$$V_t(s) \;=\; \max_{a\in\mathcal{A}}\Big\{ R(s,a) + \sum_{s'} P(s'\mid s,a)\,V_{t+1}(s') \Big\}.$$

Với bài toán tối thiểu hóa mất mát (trường hợp của defender), thay $\max$ bằng $\min$.

> 📐 Backward induction là thuật toán mà manuscript §7 nói dùng cho các trò chơi nhỏ ($KH \le 40$). Nó chính xác, không xấp xỉ, và chạy trong $O(H\,|\mathcal{S}|\,|\mathcal{A}|\,|\mathcal{S}|)$.

## 4.2 POMDP và belief state

Trong Sentinel, defender **không quan sát được** trạng thái thật $s_t = (\mathbf{c}_t, \iota, \sigma)$ — chỉ thấy điểm alarm của một detector không hoàn hảo. Đây là một **POMDP**.

**Định nghĩa 4.2.** $\langle \mathcal{S},\mathcal{A},P,R,\Omega,O,H\rangle$ bổ sung tập quan sát $\Omega$ và mô hình quan sát $O(o\mid s',a)$.

**Định nghĩa 4.3 (Belief).** $b_t \in \Delta(\mathcal{S})$, $b_t(s) = \Pr[s_t = s \mid a_{0:t-1}, o_{1:t}]$.

**Định lý 4.4 (Belief là thống kê đủ).** Chính sách tối ưu của POMDP chỉ cần phụ thuộc $b_t$, không cần toàn bộ lịch sử. Do đó POMDP quy về một **MDP trên không gian belief** ("belief MDP") với không gian trạng thái $\Delta(\mathcal{S})$.

**Cập nhật Bayes (bộ lọc belief).**
$$b_{t+1}(s') \;=\; \frac{O(o_{t+1}\mid s',a_t)\ \sum_{s} P(s'\mid s,a_t)\, b_t(s)}{\displaystyle\sum_{s''} O(o_{t+1}\mid s'',a_t) \sum_{s} P(s''\mid s,a_t)\, b_t(s)} .$$

**Cụ thể hóa cho Sentinel.** ⟨**tái dựng**⟩ Không gian trạng thái ẩn là $(k,\iota,\sigma)$ (carrier bị chèn, thời điểm chèn, thời điểm trigger), cộng giả thuyết "sạch". Với quan sát alarm nhị phân $o_{t}\in\{0,1\}$ sau khi audit carrier $k_t$ tại task $t$:

$$
\Pr[o_t = 1 \mid k,\iota,\sigma] \;=\;
\begin{cases}
\psi & \text{nếu } k_t = k \text{ và } \iota \le t < \sigma \quad (\text{có poison, detector báo đúng})\\
\phi & \text{ngược lại} \quad (\text{benign drift hoặc audit trượt, detector báo sai})
\end{cases}
$$

và posterior:
$$b_{t+1}(k,\iota,\sigma) \;\propto\; \Pr[o_t \mid k,\iota,\sigma]\cdot b_t(k,\iota,\sigma).$$

> 📐 **Đây là công thức tạo ra câu "một alarm bây giờ nâng posterior về các lần chèn sớm hơn và trigger muộn hơn"** (manuscript §5.1). Lý do: các bộ ba $(k,\iota,\sigma)$ thỏa $\iota \le t < \sigma$ được nhân với $\psi$, các bộ ba khác chỉ được nhân với $\phi < \psi$. Chuẩn hóa lại ⇒ khối lượng xác suất dịch về phía các bộ ba có **$\iota$ nhỏ hơn $t$ và $\sigma$ lớn hơn $t$**. Không có gì huyền bí — chỉ là Bayes.

**Benign drift làm gì trong công thức này.** Nếu bỏ giả thuyết "thay đổi lành tính" khỏi không gian trạng thái, thì mọi alarm chỉ có một lời giải thích (bị nhiễm độc), posterior tăng đơn điệu, và chính sách tối ưu hội tụ về "quarantine mọi thứ". Thêm giả thuyết thứ ba với tốc độ $\beta$ đưa vào mẫu số một số hạng cạnh tranh, giữ posterior không bão hòa. Đây là nội dung toán học của manuscript §5.4.

## 4.3 Cấu trúc hàm giá trị trên không gian belief

**Định lý 4.5 (Smallwood–Sondik, 1973).** Với POMDP chân trời hữu hạn, hàm giá trị tối ưu $V_t : \Delta(\mathcal{S}) \to \mathbb{R}$ là **tuyến tính từng khúc và lồi (piecewise-linear convex)**:
$$V_t(b) = \max_{\alpha \in \Gamma_t} \langle \alpha, b\rangle$$
với $\Gamma_t$ là một tập hữu hạn các $\alpha$-vector.

**Hệ quả thực hành:** có thể rời rạc hóa đơn hình belief thành lưới rồi làm backward induction — đúng như manuscript §7 mô tả (*"solved exactly by backward induction over a discretised belief simplex"*). Sai số rời rạc hóa được kiểm soát bằng chính lập luận Lipschitz ở Phần 6.

## 4.4 Particle filter (bộ lọc hạt)

Khi $|\mathcal{S}|$ quá lớn để giữ belief dạng bảng, biểu diễn belief bằng $N$ hạt có trọng số $\{(s^{(i)}, w^{(i)})\}_{i=1}^N$. Manuscript §7 dùng $N = 2048$.

**Thuật toán SIR (Sequential Importance Resampling), một bước:**

1. **Dự đoán:** với mỗi hạt, lấy mẫu $s^{(i)}_{t+1} \sim P(\cdot \mid s^{(i)}_t, a_t)$ — bao gồm cả khả năng benign drift với tốc độ $\beta$.
2. **Cập nhật trọng số:** $w^{(i)} \leftarrow w^{(i)}\cdot O(o_{t+1}\mid s^{(i)}_{t+1}, a_t)$.
3. **Chuẩn hóa:** $w^{(i)} \leftarrow w^{(i)}/\sum_j w^{(j)}$.
4. **Resample** khi effective sample size $\mathrm{ESS} = 1/\sum_i (w^{(i)})^2$ tụt dưới ngưỡng (thường $N/2$).

**Sai số:** ước lượng particle filter hội tụ với tốc độ $O(1/\sqrt{N})$. Với $N = 2048$, sai số chuẩn $\approx 0.022$ — cùng bậc với các chênh lệch 0.02–0.03 giữa các chính sách trong smoke test. **Đây là một threat to validity phải ghi vào luận văn:** nếu hai chính sách chênh nhau 0.02 thì chưa phân biệt được nếu chỉ chạy một seed.

> 📐 **Lỗi kinh điển với particle filter: suy biến (degeneracy).** Sau vài bước, gần như toàn bộ trọng số dồn vào một hạt và belief mất đa dạng. Dấu hiệu: ESS tụt nhanh. Cách xử lý: resample + thêm nhiễu nhỏ (roughening). Kiểm tra đầu tiên khi kết quả belief-based trông "quá tốt" hoặc "quá tệ".

## 4.5 Bổ đề mô phỏng (simulation lemma) — động cơ của Theorem 3

**Bổ đề 4.6.** Cho hai MDP cùng $(\mathcal{S},\mathcal{A},R,H)$ nhưng kernel khác nhau $P$ và $\tilde P$ với $\max_{s,a}\|P(\cdot\mid s,a)-\tilde P(\cdot\mid s,a)\|_{TV} \le \zeta$. Với mọi chính sách $\pi$:
$$\big|V^\pi_P - V^\pi_{\tilde P}\big| \;\le\; H\,\zeta\,\mathrm{range}(R)$$
với $\mathrm{range}(R) = \max R - \min R$.

**Chứng minh (phác thảo, 4 dòng).**
Đặt $\delta_t = |V^\pi_{P,t} - V^\pi_{\tilde P,t}|$. Tại mỗi bước,
$$\delta_t \;\le\; \underbrace{\big|\textstyle\sum_{s'}(P-\tilde P)(s')\,V_{t+1}(s')\big|}_{\le\ \zeta\,\mathrm{range}(V_{t+1})\ \le\ \zeta\,\mathrm{range}(R)\cdot(H-t)} \;+\; \delta_{t+1}.$$
Bất đẳng thức thứ nhất là định nghĩa của TV (cặp đôi với hàm bị chặn). Cộng dồn từ $t=H$ về $t=0$ cho $O(H\zeta\,\mathrm{range}(R))$. $\square$

> 📐 **Ba chữ cần nhớ: "Lipschitz + cộng dồn".** Mọi cận trong Phần 6–7 của đề tài đều có dạng *(hằng số Lipschitz) × (sai số mỗi bước) × (số bước)*. Khi đọc Theorem 3 và Proposition 6, hãy nhận ra chúng là **cùng một chứng minh** áp cho hai loại sai số khác nhau: sai số kernel ($\zeta$) và sai số thư viện chính sách ($\rho$).

---

# PHẦN 5 — KIỂM ĐỊNH GIẢ THUYẾT VÀ GIỚI HẠN MẪU (CHO THEOREM 4)

Đây là phần toán **xa lạ nhất** với nền backend/AIOps, và là phần sinh ra kết quả quan trọng nhất của đề tài. Đọc kỹ.

## 5.1 Đặt bài toán như một bài kiểm định giả thuyết

Tại thời điểm ra quyết định, defender phải phân biệt:

$$H_0:\ \text{trạng thái carrier thay đổi do \textbf{benign drift} (tốc độ } \beta)$$
$$H_1:\ \text{trạng thái carrier thay đổi do \textbf{poisoning bền vững}}$$

Mỗi lần audit cho một quan sát: alarm với xác suất $\psi$ dưới $H_1$, với xác suất $\phi$ dưới $H_0$. Đặt $\gamma = \psi - \phi > 0$ là **margin của detector**.

## 5.2 Bổ đề Neyman–Pearson và tỉ số hợp lý

**Bổ đề 5.1 (Neyman–Pearson).** Với mức sai lầm loại I cố định, phép kiểm định tối ưu (cực tiểu sai lầm loại II) là phép kiểm định **tỉ số hợp lý**: bác bỏ $H_0$ khi
$$\Lambda_n = \prod_{i=1}^{n}\frac{\Pr[o_i\mid H_1]}{\Pr[o_i \mid H_0]} \;>\; \text{ngưỡng}.$$

Nghĩa là: **không có cách nào thông minh hơn** để dùng $n$ quan sát. Mọi cận dưới về số mẫu suy ra từ đây đều là cận dưới **cho mọi phương pháp**, không riêng phương pháp của ta.

## 5.3 Số mẫu cần thiết — nguồn gốc của $\gamma^{-2}$

**Định lý 5.2 (Chernoff–Stein, dạng rút gọn).** Để phân biệt $H_0$ và $H_1$ với xác suất sai $\le \alpha$ cần
$$n \;\gtrsim\; \frac{\log(1/\alpha)}{\mathrm{KL}(P_1\|P_0)} .$$

Với hai phân bố Bernoulli cách nhau margin $\gamma$, theo Mục 1.2 ta có $\mathrm{KL} \ge 2\gamma^2$, do đó

$$\boxed{\;n \;\gtrsim\; \frac{\log(1/\alpha)}{2\gamma^{2}}\;}$$

> 📐 **Trực giác bằng con số.** Detector tốt với $\gamma = 0.5$ cần $n \approx 2\log(1/\alpha)$ mẫu; detector yếu với $\gamma = 0.1$ cần $n \approx 50\log(1/\alpha)$ — **gấp 25 lần**. Đây là lý do manuscript §5.6 nói cải thiện detector làm giảm ngân sách yêu cầu **theo bình phương**, và cũng là lý do RQ4 kết luận *"adaptive allocation matters most when the detector is weak"*: khi $\gamma$ nhỏ, số mẫu cần lớn, và **phân bổ mẫu ở đâu** mới trở thành yếu tố quyết định.

## 5.4 Từ số mẫu sang ngân sách — ba thừa số của Theorem 4

Manuscript phát biểu:
$$B \;\ge\; \frac{c\,\bar\kappa\,(1+\chi)\log(1/\alpha)}{\gamma^{2}}\cdot\left(1 + \frac{\Delta}{H}K\right).$$

Đọc công thức theo bốn thừa số, mỗi thừa số một ý nghĩa vật lý:

| Thừa số | Nguồn gốc toán học | Ý nghĩa |
|---|---|---|
| $\dfrac{\log(1/\alpha)}{\gamma^2}$ | Chernoff–Stein + Pinsker (Mục 5.3) | Số **mẫu thông tin** cần để phân biệt hai giả thuyết |
| $\bar\kappa$ | Định nghĩa chi phí | Mỗi mẫu tốn một lần audit; giá trung bình một lần audit |
| $(1+\chi)$ | Cận xấu nhất trên chi phí carrier | Carrier mang thông tin **có thể là carrier đắt nhất**; hệ số phồng chi phí khi phải phủ đều các carrier lệch giá |
| $\Big(1 + \frac{\Delta}{H}K\Big)$ | Đếm cửa sổ quan sát hữu ích | Quan sát chỉ có ích trong cửa sổ dài $\Delta$ trên tổng $H$; nhân $K$ vì phải phân biệt **carrier nào** trong $K$ carrier |

**Hệ quả cho audit-at-commit.** Chính sách này lấy toàn bộ quan sát tại **một carrier, một thời điểm** (bản patch tại commit). Tăng độ sâu audit làm quan sát chính xác hơn nhưng **không làm tăng số mẫu độc lập về danh tính carrier** — đây là điểm mấu chốt, và nó là một áp dụng của nguyên lý *data processing*: xử lý sâu hơn trên cùng một mẫu không tạo ra thông tin mới về một biến mà mẫu đó không chứa.

Do đó $B_{\text{commit}}$ **không phụ thuộc $\Delta$**, và điều kiện đủ thất bại khi

$$\Big(1 + \frac{\Delta K}{H}\Big) \;>\; \frac{B_{\text{commit}}\,\gamma^2}{c\,\bar\kappa\,(1+\chi)\log(1/\alpha)} .$$

**Corollary 5 (ranh giới chế độ) là đọc ngược bất đẳng thức trên:** vế trái nhỏ khi $\Delta$ nhỏ hoặc $K = 1$ ⇒ commit là đủ; vế trái lớn khi $\Delta$ hoặc $K$ tăng ⇒ commit không đủ.

> 📐 **Kiểm tra tính nhất quán mà bạn nên tự làm ngay:** đặt $\Delta = 0$ vào công thức — thừa số cuối bằng 1, ngân sách yêu cầu là nhỏ nhất, và commit đạt đúng mức đó. Điều này khớp với cả smoke test (+0% tại $\Delta = 0$) lẫn mô hình tái lập. Một công thức mà bạn kiểm tra được ở biên là một công thức bạn đã hiểu.

## 5.5 Phiên bản tuần tự: SPRT

Vì defender quan sát **tuần tự** và có thể dừng sớm, công cụ đúng là **Sequential Probability Ratio Test** (Wald, 1945): tích lũy log-tỉ số hợp lý $\log\Lambda_n$ và dừng khi vượt một trong hai ngưỡng $\log\frac{1-\alpha_2}{\alpha_1}$ hoặc $\log\frac{\alpha_2}{1-\alpha_1}$.

**Tính chất then chốt:** SPRT tối ưu về **số mẫu kỳ vọng** trong lớp các phép kiểm định có cùng mức sai lầm. Số mẫu kỳ vọng vẫn tỉ lệ $\log(1/\alpha)/\gamma^2$ — nên Theorem 4 giữ nguyên dạng, chỉ đổi hằng số $c$.

> ⟨**tái dựng**⟩ Manuscript không nói rõ dùng SPRT hay kiểm định cố định mẫu. Đây là một câu hỏi tốt cho GVHD, vì hằng số $c$ trong Theorem 4 phụ thuộc lựa chọn này.

---

# PHẦN 6 — TỐI ƯU HÓA BỀN VỮNG VÀ TỔN THẤT DO GIỚI HẠN

## 6.1 Bài toán đối ứng bền vững (robust counterpart)

Khi kernel $P$ chỉ biết đến sai số $\zeta$ theo TV, tập bất định là quả cầu
$$\mathcal{U}_\zeta(P) = \{\tilde P : \|\tilde P(\cdot\mid s,a) - P(\cdot\mid s,a)\|_{TV} \le \zeta \ \ \forall s,a\}.$$

Chính sách bền vững giải
$$\pi_{\text{rob}} \in \arg\min_{\pi}\ \max_{\tilde P \in \mathcal{U}_\zeta(P)}\ V^\pi_{\tilde P}.$$

Đây là **minimax lồng hai lớp**: lớp ngoài với attacker, lớp trong với bất định mô hình. Assumption 2 của manuscript khai báo chính xác cấu trúc này.

## 6.2 Covering radius và thư viện chính sách hạn chế

**Định nghĩa 6.1.** Thư viện hữu hạn $\Pi$ có **bán kính phủ** $\rho$ nếu với mọi chính sách $\pi^\*$ trong không gian đầy đủ, tồn tại $\pi \in \Pi$ sao cho tại mỗi bước
$$\|\pi(\cdot\mid b) - \pi^\*(\cdot\mid b)\|_{TV} \;\le\; \rho .$$

Manuscript đo được $\rho = 0.07$ cho thư viện 28 chính sách.

**Proposition 6 (Restriction loss).**
$$V(\Pi) - V^\star \;\le\; H\,\rho\,\mathrm{range}(L).$$

**Chứng minh** dùng **đúng** Bổ đề 4.6, chỉ thay nguồn sai số: thay vì kernel lệch $\zeta$, ở đây phân bố hành động lệch $\rho$; giá trị mỗi bước lệch không quá $\rho\,\mathrm{range}(L)$; cộng dồn qua $H$ bước. $\square$

**Con số trong manuscript:** $\rho = 0.07$ cho cận $0.42$ (đơn vị harm chuẩn hóa), trong khi tổn thất **đo được** chỉ $0.09$.

> 📐 **Cận lỏng gấp gần 5 lần — và đó là chuyện bình thường.** Cận worst-case giả định sai số $\rho$ xảy ra **ở mọi bước và luôn theo hướng bất lợi nhất**. Thực tế các sai số triệt tiêu lẫn nhau. Cách trình bày đúng trong luận văn: báo cáo **cả hai** (cận lý thuyết và giá trị đo được) và nói rõ khoảng cách — đó là dấu hiệu của một công trình trung thực, không phải một điểm yếu.

## 6.3 Vì sao dùng minimax thay vì học trực tuyến

Đây là câu hỏi phản biện chắc chắn sẽ gặp, và câu trả lời là toán học, không phải sở thích:

| Tiêu chí | Minimax (Stackelberg) | Học trực tuyến (no-regret) |
|---|---|---|
| Đảm bảo | Cận **worst-case tuyệt đối** trên harm | Cận **regret** so với lớp so sánh, trung bình theo thời gian |
| Giả định về đối thủ | Best-respond với chính sách đã cam kết | Có thể phi tĩnh (non-stationary) |
| Mâu thuẫn cấu trúc | — | **Học trực tuyến không "cam kết"** — mà cam kết là giả định định nghĩa của Stackelberg |
| Câu chuyện an toàn | Mạnh: biết trước điều tệ nhất | Yếu hơn: có thể tệ tùy ý ở giai đoạn đầu |

Manuscript §5.6 nói đúng điều này và xếp học trực tuyến là **hướng mở rộng khác**, không phải phương án bị bác.

---

# PHẦN 7 — BỐN KẾT QUẢ LÝ THUYẾT: PHÁT BIỂU VÀ KHUNG CHỨNG MINH

## 7.0 Bản đồ công cụ

| Kết quả (số của manuscript) | Công cụ toán cần | Phần trong file này |
|---|---|---|
| **Theorem 3** — Robust Stackelberg bound | Bổ đề mô phỏng + backward induction + TV | 1.2, 4.1, 4.5 |
| **Theorem 4** — Distinguishability budget | Neyman–Pearson, Chernoff–Stein, Pinsker, đếm cửa sổ | 1.2, 5.1–5.4 |
| **Corollary 5** — Regime boundary | Hệ quả đại số của Theorem 4 | 5.4 |
| **Proposition 6** — Restriction loss | Bổ đề mô phỏng + covering radius | 4.5, 6.2 |

**Nhận xét quan trọng về khối lượng công việc:** bốn kết quả này dùng **đúng hai** ý tưởng chứng minh — "Lipschitz + cộng dồn" (Theorem 3, Proposition 6) và "giới hạn thông tin + đếm mẫu" (Theorem 4, Corollary 5). Không phải bốn kỹ thuật độc lập.

## 7.1 Theorem 3 — Robust Stackelberg bound

**Phát biểu (manuscript §6.1, nguyên văn).** Dưới Assumption 2, gọi $V_0^\*$ là giá trị minimax khi kernel biết chính xác. Khi đó chính sách bền vững của Sentinel đạt
$$V \;\le\; V_0^\* + H\,\zeta\,\mathrm{range}(L),$$
và cận này **chặt tới một hằng số**: tồn tại các instance mà **mọi** chính sách chịu mức vượt $\Omega(H\zeta)$.

**Khung chứng minh (manuscript đưa 4 dòng; đây là phiên bản mở rộng để bạn viết đầy đủ):**

| Bước | Việc phải làm | Công cụ |
|---|---|---|
| 1 | Phát biểu chính xác Assumption 2: $H$ hữu hạn và biết; kernel biết đến sai số TV $\zeta$; $(\psi,\phi)$ biết; $\Pi_A$ và ngân sách khai báo; defender cam kết trước | — |
| 2 | Viết backward induction trên **belief MDP** | 4.1–4.2 |
| 3 | Chứng minh $V_t$ là $\mathrm{range}(L)$-Lipschitz theo kernel dưới chuẩn TV | 1.1, 1.2 |
| 4 | Nhiễu kernel $\zeta$ ⇒ nhiễu giá trị mỗi bước $\le \zeta\,\mathrm{range}(L)$ | 4.5 |
| 5 | Cộng dồn qua $H$ bước ⇒ cận trên | — |
| 6 | **Phần chặt (tightness):** dựng hai kernel lệch nhau $\zeta$ ở xác suất lan truyền của carrier bị nhiễm, sao cho hành động tối ưu **ngược nhau**; mọi chính sách đơn lẻ sai ở một trong hai, chịu $\Omega(\zeta)$ mỗi bước | Xây dựng phản ví dụ |

> 📐 **Bước 6 là bước người mới hay bỏ.** Chỉ có cận trên thì định lý yếu: có thể cận đó quá lỏng và thực tế tốt hơn nhiều. Phần "tight up to a constant" mới là phần khẳng định cận này **không cải thiện được** về mặt bậc. Cách làm: xây dựng cụ thể hai instance, không cần tổng quát.

**Chỗ dễ sai:** $\mathrm{range}(L)$ phải là biên độ của **toàn bộ** hàm mất mát $L = \mathbb{E}[\text{harm}] + \lambda_Q\mathbb{E}[\text{FQ}] + \lambda_T\mathbb{E}[\text{clean lost}]$, không chỉ của phần harm. Nếu $\lambda_Q$ lớn, $\mathrm{range}(L)$ lớn theo và cận nới ra.

## 7.2 Theorem 4 — Distinguishability budget

**Phát biểu (manuscript §6.2, nguyên văn).** Cho benign drift xảy ra với tốc độ $\beta$ với thống kê quan sát khớp với poisoning; cho detector có margin $\gamma = \psi - \phi > 0$; cho độ trễ trigger là $\Delta$ và chi phí audit theo carrier có tính không đồng nhất $\chi$. Để phân biệt trạng thái bị nhiễm độc với trạng thái lành tính với sai số $\le \alpha$ tại thời điểm ra quyết định, ngân sách audit cần thỏa
$$B \;\ge\; \frac{c\,\bar\kappa\,(1+\chi)\log(1/\alpha)}{\gamma^{2}}\cdot\left(1 + \frac{\Delta}{H}K\right).$$

**Khung chứng minh:**

| Bước | Việc phải làm | Công cụ |
|---|---|---|
| 1 | Hình thức hóa $H_0$ / $H_1$ và mô hình quan sát Bernoulli$(\phi)$ / Bernoulli$(\psi)$ | 5.1 |
| 2 | Áp Neyman–Pearson: phép kiểm định tối ưu là tỉ số hợp lý ⇒ cận dưới áp cho **mọi** phương pháp | 5.2 |
| 3 | Áp Chernoff–Stein + Pinsker ⇒ $n \gtrsim \log(1/\alpha)/\gamma^2$ | 5.3 |
| 4 | Chuyển từ "số mẫu" sang "ngân sách": mỗi mẫu tốn một audit; chi phí trung bình $\bar\kappa$; hệ số phồng $(1+\chi)$ ở trường hợp xấu nhất về danh tính carrier | 5.4 |
| 5 | Đếm cửa sổ quan sát hữu ích: chỉ $\Delta$ trên $H$ task cho mẫu có ích về danh tính carrier; nhân $K$ ⇒ thừa số $(1+\Delta K/H)$ | 5.4 |
| 6 | Trường hợp riêng commit-only: mọi quan sát tại một carrier một thời điểm ⇒ tăng độ sâu không tăng số mẫu độc lập ⇒ $B_{\text{commit}}$ độc lập $\Delta$ | Nguyên lý data processing |

**Ba chỗ phải cẩn thận:**

1. **Hằng số $c$ chưa xác định** trong manuscript. Nó phụ thuộc lựa chọn kiểm định cố định mẫu hay SPRT (Mục 5.5). Trong luận văn phải nêu rõ $c$ là gì hoặc tuyên bố kết quả ở dạng $\Theta(\cdot)$.
2. **Giả định độc lập giữa các quan sát** ẩn trong bước 3. Các lần audit liên tiếp trên **cùng** một carrier có thể tương quan. Nếu có tương quan, số mẫu hiệu dụng giảm và cận phải nới. Đây là một threat to validity cần ghi.
3. **Thừa số $(1+\chi)$ là cận trên xấu nhất**, không phải giá trị chính xác — nó giả định carrier mang thông tin đúng là carrier đắt nhất. Smoke test cho thấy $\chi$ **thu hẹp** độ lợi, khớp chiều với thừa số này.

## 7.3 Corollary 5 — Regime boundary

**Phát biểu (manuscript §6.2).** Audit tại thời điểm commit là **đủ** khi $\Delta$ nhỏ (trigger kích hoạt trong chính task được audit) hoặc khi $K$ hiệu dụng bằng 1 (một carrier duy nhất); và **không đủ** khi $\Delta$ tăng hoặc số carrier tăng.

**Khung chứng minh:** thuần đại số từ Theorem 4 — xem bất đẳng thức cuối Mục 5.4. Hai trường hợp biên:

- $\Delta = 0$: cửa sổ quan sát rỗng ngoài thời điểm $\sigma$; mọi chính sách đều chỉ có một cơ hội ⇒ commit tối ưu.
- $K = 1$: không có bài toán **danh tính carrier** để phân biệt ⇒ thừa số $K$ biến mất, bài toán rút về phát hiện thuần túy.

**Đây là kết quả mà manuscript tự gọi là "the paper's most useful output".** Trong luận văn nên tách thành một mục riêng, không chôn trong phần chứng minh Theorem 4.

## 7.4 Proposition 6 — Restriction loss

**Phát biểu (manuscript §6.3).** Cho thư viện hữu hạn $\Pi$ có bán kính phủ $\rho$ theo TV trên phân bố hành động audit, so với không gian chính sách không hạn chế. Khi đó
$$V(\Pi) - V^\star \;\le\; H\,\rho\,\mathrm{range}(L).$$

**Khung chứng minh:** lấy $\pi^\*$ tối ưu và $\pi\in\Pi$ nằm trong bán kính $\rho$ tại mỗi bước; chênh lệch giá trị mỗi bước $\le \rho\,\mathrm{range}(L)$ theo cùng lập luận Lipschitz của Theorem 3; cộng dồn qua $H$ bước.

**Việc thực nghiệm đi kèm:** đo $\rho$ cho thư viện 28 chính sách **so với nghiệm chính xác trên 240 trò chơi nhỏ**. Đây là lý do 240 trò chơi nhỏ tồn tại trong benchmark — chúng không phải để so sánh hiệu năng, mà để **đo $\rho$ và kiểm chứng cận**.

---

# PHẦN 8 — ĐẶC TẢ FORMAL ĐẦY ĐỦ CỦA SENTINEL

Gom mọi mảnh ở trên thành một trang duy nhất — đây là bản có thể copy thẳng vào Chương 3 luận văn.

## 8.1 Trò chơi

**Người chơi:** defender (leader), attacker (follower).

**Workflow:** $H$ task; $K = 4$ carrier $\{$memory, cached skill, tool queue, branch$\}$.

**Trạng thái:** $s_t = (\mathbf{c}_t, \iota, \sigma)$ với $\mathbf{c}_t \in \{0,1\}^K$, $\iota$ = thời điểm chèn, $\sigma$ = thời điểm trigger. Độ trễ $\Delta = \sigma - \iota$.

**Hành động attacker:** $(k, \iota, \sigma, \varepsilon)$ — carrier, thời điểm chèn, lịch trigger, biên độ sửa đổi $\le\varepsilon$; bị ràng buộc bởi ngân sách của attacker; thuộc lớp khai báo $\Pi_A$.

**Hành động defender:** $a_t \in \mathcal{A} = \{\text{none}\}\cup\{(\text{audit},k,\text{depth})\}$, chi phí $\kappa(k,\text{depth})$, ràng buộc $\sum_t \kappa(a_t) \le B$; cộng tùy chọn quarantine chi phí $\eta_Q$.

**Quan sát:** $o_t$ = điểm alarm từ detector không hoàn hảo $(\psi,\phi)$, cộng kết quả checkpoint thực thi được.

**Nhiễu nền:** benign drift, tốc độ $\beta$, thống kê quan sát khớp với poisoning.

**Hàm mất mát defender:**
$$L \;=\; \mathbb{E}[\text{verified harm}] \;+\; \lambda_Q\,\mathbb{E}[\text{false quarantines}] \;+\; \lambda_T\,\mathbb{E}[\text{clean tasks lost}].$$

**Giá trị defender:**
$$V^\star \;=\; \min_{\pi_D}\ \max_{\pi_A \in \Pi_A}\ L(\pi_D,\pi_A).$$

**Hai trục chế độ:**
$$\Delta = \sigma - \iota, \qquad \chi \;=\; \frac{\max_{k,k'}\big|\kappa(k)-\kappa(k')\big|}{\bar\kappa}.$$

## 8.2 Thuật toán Sentinel tại task $t$ (manuscript Algorithm 1)

```
Input: belief b_t, ngân sách còn lại B_t, thư viện chính sách Π
 1: ước lượng Δ̂, χ̂ từ lịch sử
 2: if trò chơi nhỏ (K·H ≤ ngưỡng) then
 3:     a_t ← nghiệm minimax chính xác bằng backward induction trên belief MDP
 4: else
 5:     a_t ← argmin_{π∈Π} max_{π_A∈Π_A} L̂(π, π_A | b_t, B_t)      ⊳ robust trên thư viện hạn chế
 6: end if
 7: thực hiện a_t; quan sát o_t; b_{t+1} ← Update(b_t, a_t, o_t, β)
 8: if Pr[poisoned | b_{t+1}] > τ  và  expected harm > η_Q then
 9:     quarantine carrier có posterior cao nhất
10: end if
```

**Ba quyết định toán học ẩn trong 10 dòng này:**

1. **Dòng 3 vs 5** — ngưỡng $KH \le 40$ là ranh giới giữa "giải chính xác" và "giải xấp xỉ". Proposition 6 tồn tại để **định lượng cái giá của dòng 5**.
2. **Dòng 7** — `Update` là bộ lọc Bayes ở Mục 4.2, hiện thực bằng particle filter 2048 hạt.
3. **Dòng 8** — quy tắc quarantine hai điều kiện. Điều kiện thứ hai (expected harm $> \eta_Q$) là thứ ngăn "quarantine mọi thứ" — nó là phiên bản quyết định của việc mô hình hóa benign drift.

## 8.3 Bảng ký hiệu tổng hợp

| Ký hiệu | Ý nghĩa | Xuất hiện ở |
|---|---|---|
| $H$ | số task trong workflow (6–14) | 8.1 |
| $K$ | số carrier ($=4$) | 8.1 |
| $\mathbf{c}_t$ | vector nhiễm độc của các carrier | 8.1 |
| $\iota,\ \sigma$ | thời điểm chèn, thời điểm trigger | 8.1 |
| $\Delta = \sigma-\iota$ | độ trễ trigger | 5.4, 7.3 |
| $\varepsilon$ | biên độ sửa đổi của attacker | 8.1 |
| $\kappa(k,\text{depth}),\ \bar\kappa$ | chi phí audit, chi phí trung bình | 5.4 |
| $\chi$ | tính không đồng nhất chi phí carrier | 5.4, 7.3 |
| $B$ | ngân sách audit | 3.4, 7.2 |
| $\psi,\ \phi,\ \gamma=\psi-\phi$ | TP rate, FP rate, margin detector | 5.1 |
| $\beta$ | tốc độ benign drift | 4.2 |
| $\alpha$ | mức sai số cho phép khi phân biệt | 7.2 |
| $b_t$ | belief tại task $t$ | 4.2 |
| $\tau,\ \eta_Q$ | ngưỡng posterior, ngưỡng harm để quarantine | 8.2 |
| $\lambda_Q,\ \lambda_T$ | trọng số false quarantine, clean task lost | 8.1 |
| $L,\ \mathrm{range}(L)$ | hàm mất mát, biên độ | 7.1 |
| $V^\star,\ V_0^\*$ | giá trị minimax, giá trị khi kernel biết chính xác | 7.1 |
| $\zeta$ | bán kính bất định kernel theo TV | 6.1, 7.1 |
| $\Pi,\ \rho$ | thư viện chính sách hạn chế (28), bán kính phủ ($=0.07$) | 6.2, 7.4 |
| $\Pi_A$ | lớp attacker khai báo | 8.1 |
| $\mathrm{Expl}(x)$ | exploitability | 2.6 |

---

# PHẦN 9 — LỘ TRÌNH HỌC TOÁN CÓ ĐẦU RA KIỂM CHỨNG ĐƯỢC

Đây là bản chi tiết hóa Giai đoạn 0 (4–8 tuần) thành **bài tập cụ thể**. Nguyên tắc: mỗi khối kết thúc bằng một hiện vật GVHD nhìn thấy được, không phải "đã đọc xong".

| # | Khối toán | Nguồn chính | Bài tập bắt buộc | Đầu ra kiểm chứng được | Thời lượng |
|---|---|---|---|---|---|
| 1 | Lồi, đơn hình, Lipschitz | Shoham & Leyton-Brown, Appendix | Chứng minh Bổ đề 2.3 (best response luôn có nghiệm thuần) | Nửa trang chứng minh viết tay | 2 ngày |
| 2 | LP và đối ngẫu | Bất kỳ giáo trình OR nhập môn | Giải một trò chơi tổng-không $3\times3$ bằng LP; đối chiếu với nghiệm tính tay | Notebook + so sánh hai nghiệm | 3 ngày |
| 3 | Nash, minimax | Coursera *Game Theory* I (tuần 1–3) | Tính cân bằng Nash của Matching Pennies và một trò chơi $2\times2$ tổng-không | Ghi chú 2 trang | 4 ngày |
| 4 | Stackelberg & SSE | Conitzer & Sandholm (EC 2006) | Cài **multiple-LP**; kiểm chứng $V_{\text{SSE}} \ge V_{\text{Nash}}$ trên 100 trò chơi ngẫu nhiên | Script + biểu đồ phân tán hai giá trị | 5 ngày |
| 5 | Security games & coverage | Survey IJCAI 2018 (Sinha et al.) | Lập bảng ánh xạ SSG chuẩn → Sentinel (Mục 3.1) | Bảng 6 dòng đã điền | 3 ngày |
| 6 | **LP minimax của Sentinel** | Mục 3.4 file này | Chạy `smoke_repro.py`; in **biến đối ngẫu** và giải thích attacker đang nhắm đâu | Reproduction report một trang | 3 ngày |
| 7 | MDP & backward induction | Kochenderfer et al., ch.7 | Cài backward induction cho một MDP 5 trạng thái, $H=4$ | Notebook | 3 ngày |
| 8 | POMDP & belief update | Kochenderfer et al., ch.19–20 | Cài bộ lọc Bayes cho không gian $(k,\iota,\sigma)$ với $K=2,H=4$; kiểm chứng "alarm nâng posterior về chèn sớm hơn" | Biểu đồ posterior trước/sau một alarm | 5 ngày |
| 9 | Particle filter | Kochenderfer et al., ch.19 | Cài SIR 2048 hạt; vẽ ESS theo thời gian; bật/tắt resampling | Biểu đồ ESS cho thấy suy biến khi tắt resampling | 4 ngày |
| 10 | Kiểm định giả thuyết | Bất kỳ giáo trình thống kê toán | Mô phỏng: cần bao nhiêu mẫu để phân biệt Bern(0.6) với Bern(0.5) ở $\alpha=0.05$? So với $\log(1/\alpha)/2\gamma^2$ | Biểu đồ số mẫu mô phỏng vs công thức | 4 ngày |
| 11 | **Theorem 4** | Mục 5.4, 7.2 file này | Viết lại chứng minh 6 bước bằng lời của mình; kiểm tra biên $\Delta=0$ và $K=1$ | Bản chứng minh 2 trang | 5 ngày |
| 12 | Robust optimization | arXiv:1609.09341 (survey ML cho SSG) | Chứng minh Bổ đề 4.6 (simulation lemma) đầy đủ | 1 trang chứng minh | 4 ngày |
| 13 | **Theorem 3 & Proposition 6** | Mục 7.1, 7.4 file này | Nhận ra hai định lý dùng **cùng một** chứng minh; viết cả hai từ một bổ đề chung | Bản viết chung 2 trang | 4 ngày |

**Tổng: ~49 ngày làm việc ≈ 7 tuần** — khớp với khung 4–8 tuần của Giai đoạn 0 nếu làm tập trung.

**Thứ tự bắt buộc:** 1→2→3→4 phải tuần tự. Nhánh 7→8→9 có thể chạy song song với 5→6. Khối 10 độc lập, có thể làm bất cứ lúc nào. Khối 11, 12, 13 phải sau tất cả.

> 📐 **Khối 6 là khối cho lợi ích tức thì lớn nhất.** Sau 3 ngày bạn có một reproduction report để mang đi gặp GVHD, trong khi các khối khác mất vài tuần mới ra hiện vật. Nếu thời gian gấp, làm khối 1, 2, 6 trước và báo cáo sớm.

---

# PHẦN 10 — PHỤ LỤC

## 10.1 Bảy sai lầm toán học thường gặp trong đề tài loại này

| # | Sai lầm | Hậu quả | Cách phát hiện sớm |
|---|---|---|---|
| 1 | Nhầm **Nash** với **Stackelberg** khi viết công thức | Toàn bộ mô hình sai cấu trúc thông tin | Hỏi: ai cam kết trước? Nếu có người cam kết trước, đó là Stackelberg |
| 2 | Cho attacker thấy **kết quả rút thăm** thay vì **phân bố** | Randomization mất tác dụng, kết quả sụp về mức tất định | Kiểm tra: nếu chính sách tất định và ngẫu nhiên cho cùng harm, bạn đã rò rỉ kết quả rút thăm |
| 3 | Tối ưu trên **marginal coverage** khi ràng buộc lịch không cho phép | Cận thu được **lạc quan** (tốt hơn thực tế) | Thử phân rã ngược $c$ ra một phân bố trên schedule; nếu không được, phép rút gọn sai (Mục 3.2) |
| 4 | Bỏ giả thuyết **benign drift** khỏi không gian belief | Chính sách tối ưu suy biến thành "quarantine mọi thứ" | Nếu false quarantine rate tiến về 100%, đây là nguyên nhân |
| 5 | Giả định các quan sát audit **độc lập** khi chúng tương quan | Theorem 4 cho cận quá lạc quan | Đo tương quan giữa các lần audit liên tiếp cùng carrier |
| 6 | Dùng **average-case** thay vì **worst-case** harm | Mất toàn bộ đảm bảo an ninh; attacker thích nghi phá ngay | Kiểm tra: metric có phải $\max_a$ không, hay là $\mathbb{E}_a$? |
| 7 | Gộp kết quả trên toàn lưới $(\Delta,\chi)$ thành một con số | Trộn vùng phương pháp có tác dụng với vùng không — manuscript §9.4 cấm điều này tường minh | Luôn báo cáo bảng trên lưới, không pooled |

## 10.2 Ba kiểm tra tính đúng đắn để chạy trên mọi bản cài đặt

1. **Exploitability không âm.** $\mathrm{Expl}(x) \ge 0$ với mọi $x$, và $= 0$ đúng khi $x$ là nghiệm minimax. Nếu code cho giá trị âm, LP hoặc hàm harm sai dấu.
2. **Biên $\Delta = 0$.** Mọi chính sách hợp lý phải cho cùng worst-case harm tại $\Delta = 0$ (Corollary 5). Nếu minimax tốt hơn commit tại $\Delta=0$, mô hình cửa sổ quan sát $W(a)$ của bạn sai.
3. **Đơn điệu theo ngân sách.** Tăng $B$ không bao giờ làm worst-case harm tăng. Nếu có, ràng buộc ngân sách trong LP viết sai chiều.

## 10.3 Từ điển Anh–Việt thuật ngữ toán

| English | Tiếng Việt | Ghi chú |
|---|---|---|
| Mixed / pure strategy | Chiến lược hỗn hợp / thuần | |
| Best response | Phản ứng tốt nhất | Giữ nguyên tiếng Anh trong công thức |
| Strong Stackelberg Equilibrium | Cân bằng Stackelberg mạnh | Viết tắt SSE |
| Commitment | Cam kết | Cam kết **phân bố**, không phải hành động |
| Coverage vector | Vector phủ | |
| Belief state | Trạng thái niềm tin | |
| Posterior update | Cập nhật hậu nghiệm | |
| Belief MDP | MDP trên không gian niềm tin | |
| Backward induction | Quy nạp lùi | |
| Particle filter | Bộ lọc hạt | |
| Effective sample size (ESS) | Cỡ mẫu hiệu dụng | |
| Total variation distance | Khoảng cách biến phân toàn phần | |
| KL divergence | Phân kỳ KL | Không dịch "divergence" thành "phân kỳ hàm số" |
| Likelihood ratio test | Kiểm định tỉ số hợp lý | |
| Type I / Type II error | Sai lầm loại I / loại II | |
| Sample complexity | Độ phức tạp mẫu | |
| Covering radius | Bán kính phủ | |
| Uncertainty set | Tập bất định | |
| Robust counterpart | Bài toán đối ứng bền vững | |
| Simulation lemma | Bổ đề mô phỏng | |
| Exploitability | Khả năng bị khai thác | Giữ nguyên tiếng Anh trong bảng số liệu |
| Regret | Hối tiếc | Giữ nguyên tiếng Anh |
| Tight up to a constant | Chặt tới một hằng số | |

## 10.4 Nguồn tài liệu theo khối toán

| Khối | Nguồn | Truy cập |
|---|---|---|
| Game theory nền | Shoham & Leyton-Brown, *Multiagent Systems* | Miễn phí — masfoundations.org |
| Stackelberg equilibrium | Conitzer & Sandholm, "Computing the Optimal Strategy to Commit to", EC 2006 | PDF của tác giả tại cs.cmu.edu/~sandholm |
| Security games | Sinha, Fang, An, Kiekintveld, Tambe, IJCAI 2018 | ijcai.org/proceedings/2018/0775.pdf |
| Security games (sách) | Tambe, *Security and Game Theory* | Cambridge UP · mượn qua Internet Archive |
| MDP / POMDP / belief | Kochenderfer, Wheeler, Wray, *Algorithms for Decision Making*, ch.7, 19–20 | Miễn phí — algorithmsbook.com |
| ML cho SSG | "Machine Learning Techniques for Stackelberg Security Games: a Survey" | arXiv:1609.09341 |
| Kiểm định giả thuyết | Bất kỳ giáo trình thống kê toán (Casella & Berger ch.8) | — |
| LP trong thực hành | `scipy.optimize.linprog`, `PuLP` | Tài liệu chính thức |

## 10.5 Danh sách câu hỏi toán cần GVHD xác nhận

Gom từ các chỗ đánh dấu ⟨**tái dựng**⟩ trong file:

| # | Câu hỏi | Vị trí | Vì sao quan trọng |
|---|---|---|---|
| 1 | Trò chơi nhỏ giải bằng **backward induction trên belief MDP** hay **multiple-LP kiểu Conitzer–Sandholm**? Vì sao chọn cách đó? | 2.5 | Quyết định toàn bộ kiến trúc phần solver |
| 2 | Ràng buộc lịch audit có đủ đơn giản để tối ưu trực tiếp trên **marginal coverage** không? | 3.2 | Nếu không, mọi cận đang dùng là lạc quan |
| 3 | Công thức chính xác của mô hình quan sát và cửa sổ $W(a)$ | 3.3, 4.2 | Đây là chỗ bản tái lập lệch nhiều nhất tại $\Delta=1$ |
| 4 | Hằng số $c$ trong Theorem 4 — kiểm định cố định mẫu hay SPRT? | 5.5, 7.2 | Ảnh hưởng độ lớn của mọi con số ngân sách |
| 5 | Các quan sát audit có được giả định độc lập không? Nếu có, đã kiểm tra chưa? | 7.2 | Threat to validity của Theorem 4 |
| 6 | $\mathrm{range}(L)$ tính trên toàn bộ $L$ (gồm $\lambda_Q,\lambda_T$) hay chỉ phần harm? | 7.1 | Quyết định độ chặt của Theorem 3 |
| 7 | Bảng chi phí theo **carrier** $\kappa(k)$ và cách ra $\chi = 1.34$ | 8.3 | Đã nêu trong hướng dẫn tái lập — vẫn chưa có lời giải |

---

*File này được xây dựng từ `FSE-2027-15-paper.pdf` (manuscript đầy đủ, §4–§7) đối chiếu với các tài liệu đã lưu trong vault. Mọi phần đánh dấu ⟨tái dựng⟩ là suy luận chưa được xác nhận và phải rà soát với TS. Lê Xuân Bách trước khi đưa vào luận văn.*
