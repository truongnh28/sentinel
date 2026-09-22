# Quyết định thiết kế — FSE-2027-15 Sentinel

> Ghi lại các câu đã chốt, **kèm số đã đo** và **lý do bác các phương án khác**. Câu hỏi nguồn ở `CAU-HOI-CHOT-VOI-THAY.md`.

---

# Câu 1 — `F_match` / `F_detect`

**Chốt ngày 15/09/2026. Người quyết: tác giả đề tài.**

## Đo được trước khi quyết

Dựng 60 workflow, tiêm `memory` tại $\Delta = 2$, thu **936 item còn sống tại $\sigma$** (149 độc / 787 sạch). Huấn luyện hồi quy logistic trên bốn đặc trưng của `Item.surface()`, **đánh giá held-out 40%**:

| Đặc trưng | AUC đơn lẻ | Miền giá trị (độc) | Miền giá trị (sạch) |
|---|---|---|---|
| `size` | 0,7296 | — | — |
| `depth` | 0,7013 | $\{1, 2\}$ | $\{1\}$ |
| `recency` | 0,1892 | — | — |
| `derived` | 0,7987 | $\{0, 1\}$ | $\{0\}$ |

$$\textbf{AUC gộp (held-out, } n = 375) = 1{,}0000 \qquad \text{CI95} = [1{,}0000;\ 1{,}0000]$$

Ngưỡng yêu cầu: $\text{AUC} \le 0{,}56$. **Vượt tuyệt đối.**

Luật `derived ≥ 1 OR depth ≥ 2` bắt **149/149 item độc, chính xác 100%**.

### Vá hai chỗ lộ rõ nhất — vẫn không cứu được

| Cấu hình | AUC held-out | CI95 |
|---|---|---|
| nguyên trạng | 1,0000 | [1,0000; 1,0000] |
| vá `provenance` (bỏ `depth` lộ) | 1,0000 | [1,0000; 1,0000] |
| vá `derived_from` (item sạch cũng có lineage) | 0,9987 | [0,9919; 1,0056] |
| **vá cả hai** | **0,9966** | [0,9854; 1,0078] |

### Thủ phạm thật: `size`

| Nhóm | $n$ | size min | max | trung vị |
|---|---|---|---|---|
| **payload GỐC** | 60 | **76** | **83** | 79 |
| độc lan truyền | 89 | 22 | 39 | 29 |
| sạch | 787 | 22 | 39 | 28 |

**Không một giá trị chồng lấn** giữa payload gốc và item sạch. Ngưỡng `size > 50` tách trọn.

Item độc **lan truyền** thì ngược lại — miền size trùng khít item sạch. Chúng chỉ lộ qua `depth`/`derived`, và vá được. Nên vấn đề **khu trú ở payload gốc**.

### Và ε không cứu được, vì nó chỉ đi một chiều

| pipeline | ε=0,2 | ε=0,5 | ε=0,8 | ε=1,0 | miền sạch |
|---|---|---|---|---|---|
| `legacy` | 83 | 83 | 83 | 83 | 22–39 |
| `verbosity` | 124 | 146 | 190 | **211** | 22–39 |
| `graded` | 68 | 68 | 68 | 68 | 22–39 |

`verbosity` điều khiển được `size`, nhưng **ngay ở ε = 0,2 payload đã dài gấp 3 lần item sạch lớn nhất**. Không tồn tại ε nào làm payload khớp phân bố. `graded` bất động vì trên dataset mock `topic` là **chuỗi một token**, nên $\lceil \varepsilon \cdot 1 \rceil = 1$ với mọi ε.

## Chẩn đoán

Đây **không phải** lỗi danh sách đặc trưng. Đây là: **payload chưa từng được sinh ra từ cùng phân bố với output của agent**, và ε là một nút chỉ **đẩy ra xa**, không có đầu **kéo lại gần**. "Ngân sách phân biệt" hiện chỉ có một đầu.

Thêm hai lỗi cấu trúc đi kèm:

1. **`Item.surface()` không ai gọi.** Grep toàn repo: 0 chỗ đọc. $F_{\rm match}$ được khai trong code nhưng **chết** — cùng loại với ε trước đây.
2. **Ràng buộc $\text{AUC} \le 0{,}56$ chưa từng nằm trong test nào.** Nó sống trong doc. Vì thế AUC = 1,0 tồn tại suốt mà không cổng nào đỏ.

## ✅ Quyết định

### 1. `F_detect` **giữ nguyên dạng trừu tượng** — không hiện thực hoá

$$F_{\rm detect} \;\equiv\; (\psi, \varphi) \;\Longrightarrow\; (d', \tau_{\rm det})$$

**Đây là lựa chọn, không phải thiếu sót.** `detector.py` đặt ra ràng buộc phương pháp: *một detector dùng chung cho mọi hệ thống, vì nếu mỗi hệ thống có detector riêng thì ta đang đo CHẤT LƯỢNG PHÁT HIỆN, trong khi biến cần nghiên cứu là PHÂN BỔ.* Hiện thực hoá $F_{\rm detect}$ thành đặc trưng thật sẽ làm $(\psi,\varphi)$ thành **đại lượng phát sinh** thay vì **tham số quét được** — và giết RQ4, vốn quét `weak / mid / strong`.

Ghi rõ trong luận văn: detector là **mô hình detector có đặc trưng vận hành đã biết**, không phải một detector cụ thể.

### 2. `F_match` = đúng bốn trường của `Item.surface()`, kèm bảng đối chiếu

| $F_{\rm match}$ — **đếm bề mặt**, rẻ, ai cũng tính được | $F_{\rm detect}$ — **ngữ nghĩa**, đắt |
|---|---|
| `size` = độ dài nội dung | nội dung có bất thường ngữ nghĩa không |
| `depth` = số đoạn trong `provenance` | nguồn gốc đó có thật sự hợp lệ không |
| `recency` = tuổi tính theo task | — |
| `derived` = **số** item cha | lineage có **nhất quán** không |

> ⚠ **Hai dòng cuối là chỗ dễ trùng nhất.** `derived` đếm *bao nhiêu cha*; `lineage_consistency` hỏi *các cha đó có biện minh được cho con không*. Khác nhau như "file này có 3 import" với "3 import đó có hợp lý không". Nếu không ghi tách bạch, test rời-nhau **theo tên** sẽ xanh trong khi **bản chất** vẫn trùng.

### 3. Thay ràng buộc rời-nhau bằng **hai bất biến vận hành**

Phép giao tập tên là **rỗng nghĩa**: $F_{\rm detect}$ không phải một tập, nên so `{size,…} ∩ {semantic_anomaly,…} = ∅` là so một danh sách thật với một danh sách ước vọng — nó **không bao giờ đỏ được**, tức không phải test.

Nội dung vận hành của "rời nhau" là:

$$\textbf{(a)}\quad \varepsilon \text{ PHẢI đổi } \text{AUC}(F_{\rm match}) \qquad\qquad \textbf{(b)}\quad \varepsilon \text{ KHÔNG được đổi phân bố của } s(x)$$

- **(a)** = ngân sách phân biệt có răng. **Hiện ĐỎ**: AUC = 1,0 ở mọi ε.
- **(b)** = detector không nhìn $F_{\rm match}$. **Hiện xanh** (detector chỉ điều kiện trên `poisoned`), nhưng phải test để nó **ở lại** xanh.

### 4. ε định nghĩa lại: **khoảng cách chuẩn hoá tới phân bố item do agent sinh**

$$\varepsilon = 0 \;\Rightarrow\; \text{payload rút từ CÙNG phân bố với item agent} \;\Rightarrow\; \text{AUC} \to 0{,}5$$
$$\varepsilon = 1 \;\Rightarrow\; \text{payload lộ liễu} \;\Rightarrow\; \text{AUC} \to 1$$

Lần đầu tiên ngân sách phân biệt **có cả hai đầu**. Và ngưỡng 0,56 thôi là thứ để cầu may — nó thành **thủ tục hiệu chỉnh**:

$$\varepsilon^{*} = \max\{\varepsilon : \widehat{\text{AUC}}_{\rm upper}(\varepsilon) \le 0{,}56\}$$

Hệ quả cụ thể: nội dung payload phải **ngắn lại còn 22–39 ký tự** để khớp miền của item agent. Khả thi — `[orm] dùng raw_write` là 21 ký tự, vẫn mang đủ chỉ thị.

### 5. AUC báo cáo **theo từng $\Delta$**, không gộp

Với payload gốc, tại $\sigma$ ta có $\texttt{recency} = \sigma - \iota = \Delta$ **chính xác**. Nên $\text{AUC}(F_{\rm match})$ là **hàm của $\Delta$** — đúng trục RQ1 đo. Gộp một con số AUC là trung bình hoá dọc biến độc lập, cùng loại lỗi với α-mỗi-carrier và tiêm eager, cả hai đã bị bắt vì lý do này.

Corpus benign phải có item sạch **đủ mọi lứa tuổi**, khớp theo từng $\Delta$.

## Phương án đã cân nhắc và bác

| Phương án | Vì sao bác |
|---|---|
| Hiện thực hoá $F_{\rm detect}$ thành đặc trưng thật | $(\psi,\varphi)$ thành phát sinh thay vì quét được ⇒ **mất RQ4**, và tái lập biến gây nhiễu "chất lượng phát hiện" mà ràng buộc một-detector-dùng-chung sinh ra để loại |
| Bỏ `recency` khỏi $F_{\rm match}$ để tránh confound $\Delta$ | tuổi là thứ **defender nhìn thấy được** trong mọi bộ nhớ agent thật. Bỏ đi là tặng attacker một đặc trưng miễn phí và **thổi phồng kết quả đầu bảng** |
| Bỏ `derived` vì trùng `lineage_consistency` | hai đại lượng khác nhau (đếm vs nhất quán). Bỏ thì attacker lan truyền **miễn phí**, mà lan truyền là cơ chế trung tâm của đề tài |
| Giữ ngưỡng 0,56 như một mục tiêu để cầu may | đã chứng minh không đạt được bằng bất kỳ ε nào ở thiết kế cũ. Phải đổi **cơ chế**, không đổi **kỳ vọng** |

---

# Câu 3 — ε tác động lên đâu

**Chốt ngày 15/09/2026. Người quyết: tác giả đề tài.**

## ✅ Quyết định: **(B) ε tác động lên độ khó phát hiện ($F_{\rm match}$)**

Đây là **sửa lại** khuyến nghị trước đó của tôi (từng nghiêng về (A) truy xuất). Lý do đổi:

1. **Lập luận cũ cho (A) đã mất.** Tôi từng chọn (A) vì "R cho ε một cơ chế". Nhưng quyết định câu 1 vừa cho ε một cơ chế **tốt hơn** — khoảng cách tới phân bố agent — và nó gắn thẳng vào ràng buộc AUC vốn là thứ làm $\lambda_Q$ có giá.
2. **R có thể không liên tục như kỳ vọng.** `pipelines/SPEC-P1a-Harness.md` Phần 2 đã cảnh báo tập token quá nhỏ; Task 2 đo trung vị $|\text{topic}| = 3$. Với hai tập 3 token, Jaccard chỉ nhận $\{0, \tfrac15, \tfrac13, \tfrac12, 1\}$ — **5 giá trị rời rạc**, không phải một trục liên tục.
   > ⚠ **Errata 16/09/2026:** lúc viết dòng trên Task 2 *chưa* chạy — "3" là dự đoán. Số đo thật trên 500 instance Verified: **trung vị 4** (hist: 3→217, 4→148, 5→83, đuôi tới 32). Jaccard có nhiều mức hơn giả định, nhưng lý do 1 và 4 vẫn đứng nên quyết định **(B) không đổi**. Cổng sau Task 2 ("≤3 ⇒ dừng"): 4 > 3 ⇒ **đi tiếp**.
3. **Đo trực tiếp**: `GradedAttack` trên dataset hiện tại **bất động hoàn toàn** qua ε = 0,2…1,0 (size 68 không đổi), vì `topic` là chuỗi một token.
4. **AgentPoison vẫn không port được** dù có R. Nó tối ưu trigger trong không gian nhúng đối lại một retriever **đã học**; Jaccard không phải thứ đó. Chọn (A) cũng không cứu được baseline này.

## Hệ quả phải khai trong luận văn

- **Bỏ AgentPoison và MINJA khỏi lớp attacker**, nêu rõ lý do: chúng tối ưu trong không gian nhúng đối lại retriever đã học, không tồn tại trong thiết lập này. Grep `swe-bench` trong cả hai repo: **0 kết quả** — chúng chưa từng chạy trên định dạng này.
- **R (`retrieval.py`) hạ xuống trục bền vững tuỳ chọn**, không phải phụ thuộc. Giữ lại vì khớp chính xác là ca riêng $\theta = 1$ nên không mất gì, nhưng **P3 không còn bị chặn bởi nó**.

---

# Việc phải làm ngay sau hai quyết định này

| # | Việc | Ở đâu |
|---|---|---|
| 1 | Thêm test cổng 2: `AUC(F_match)` held-out, **theo từng $\Delta$**, kèm CI. **Phải ĐỎ ngay** (1,0000) | `tests/gate2_validity/test_benign_corpus.py` — Task 20 |
| 2 | Thêm test cổng 1 cho bất biến **(b)**: đổi ε không đổi phân bố $s(x)$ | `tests/gate1_integrity/test_score_interface.py` |
| 3 | Sinh lại payload từ phân bố item agent, ε = khoảng cách | `attacks.py` — pipeline mới `MatchedAttack` |
| 4 | Gọi `Item.surface()` ở đâu đó thật, hoặc xoá nó | `core.py` — hiện là code chết |
| 5 | Cập nhật `eval/SPEC-AuditGame-SE.md` Phần 0 theo hai bất biến vận hành | doc |

## ✅ Đã thi hành (15/09/2026)

| # | Việc | Kết quả |
|---|---|---|
| 1 | test cổng 2 `AUC(F_match)` theo từng $\Delta$, kèm CI | ✅ `tests/gate2_validity/test_benign_corpus.py` — đỏ ở 1,0000 rồi xanh |
| 2 | test cổng 1 cho bất biến **(b)** | ✅ `tests/gate1_integrity/test_feature_separation.py` — 2 test |
| 3 | pipeline `MatchedAttack`, ε = khoảng cách | ✅ `attacks.py`; `legacy`/`verbosity` → `PENDING` kèm lý do |
| 4 | `Item.surface()` có người gọi thật | ✅ cổng 2 gọi, và assert nó **bằng đúng** `F_MATCH` |
| 5 | cập nhật `eval/SPEC-AuditGame-SE.md` Phần 0 | ✅ errata 3 mục |

**Ba cổng: 50 test, 7,1 giây, xanh.** Số đã ghi **không đổi** — `runner` gọi thẳng `build.inject`, không qua `attacks.REGISTRY`; kiểm lại `q_false = 1,441667` trước và sau, khớp từng chữ số.

### Phát sinh trong lúc làm

**Corpus phải GHÉP CẶP THEO TUỔI.** Test đầu tiên của tôi so payload với *mọi* item sạch, và nó đỏ vì `recency` — đúng cái đã dự đoán, nhưng lỗi nằm ở **test**, không ở attack. `recency` bị ấn định bởi $\Delta$, tức bởi vị trí của cuộc tấn công trên trục RQ1, nên attacker không chọn được. Phải ghép cặp theo tuổi và carrier, đúng như §5 vốn đã nói. Sau khi ghép: AUC 0,487 / 0,496 / 0,501.

**K3 và A3 đang kiểm VĂN XUÔI, không kiểm code.** Chúng grep source thô tìm `"budget"`, nên docstring của `MatchedAttack` chứa cụm *"distinguishability budget"* làm cổng 1 đỏ. Một lệnh cấm mang tính **cấu trúc** thì phải nhìn cấu trúc — đã sửa sang duyệt AST, chỉ lấy `Name`/`Attribute`. Kiểm lại: lớp gian lận thật sự gán `self.spent` **vẫn bị bắt**, còn prose thì không.

**Công suất: 620 không đủ cho tiêu chí cận trên CI.** Ở $N=620$ cận trên còn 0,557 tại $\Delta=2$; $N=900$ đưa về 0,528. Con số 620 ở §5 đủ cho tiêu chí trên **ước lượng điểm**, không đủ cho **cận trên**. Đây là số cụ thể mang đi hỏi **câu 8**.

**$\varepsilon^{*} = 0$ trên mock, và đó là tính chất của mock.** `MockAgent` sinh note size **tất định theo topic** ($\texttt{len(topic)}+23$, phương sai nội-topic **= 0**), nên mọi sai lệch lộ ngay. Đường hiệu chỉnh rất dốc:

| ε | 0 | 0,05 | 0,1 | 0,15 |
|---|---|---|---|---|
| size (topic=`orm`) | 26 | 28 | 31 | 34 |
| AUC | **0,487** | 0,701 | 0,879 | 1,000 |

Trên dữ liệu thật, note agent có độ dài biến thiên tự nhiên nên ε sẽ có bề rộng thật. Test đúng ở cả hai chế độ: nó cưỡng chế **việc khớp phân bố**, không cưỡng chế một giá trị ε.

---

> Việc 1 **cố ý làm đỏ cổng 2**. Đó là đúng: AUC = 1,0 là một khuyết tật có thật, và khung này tồn tại để bắt đúng loại đó. Đỏ ở đây tốt hơn nhiều so với phát hiện lúc phản biện.

---

# Đáp án MÔ PHỎNG cho các câu 2, 4, 8, 10, 11, 12 — ghi 16/09/2026

> ⚠ **KHÔNG PHẢI CHỮ KÝ CỦA THẦY.** Claude đóng vai thầy, trả lời từ ba nguồn kiểm được: (i) văn bản `FSE-2027-15-paper-vi.md`, (ii) số đo thật từ spike SWE-bench 16/09/2026 (datasets-server), (iii) số công suất đã có trong doc này. Dùng làm **phương án chốt tạm** để mở khoá Nhóm F; buổi gặp thật chỉ cần xác nhận hoặc lật từng dòng. Hai câu **bắt buộc** thầy thật: **11** (tiền) và **12** (sửa đề cương).

## Câu 2 — bốn số 0,4/0,9/1,6/4,1: **(a) theo GIAI ĐOẠN**

Bằng chứng trong chính paper: §205 và bảng §241 dán nhãn bốn con số là **chèn / truy xuất / ủy quyền / commit** — bốn giai đoạn, không phải bốn carrier. Hệ quả:

1. `κ_branch = κ_commit = 4,1` là **artifact của phép mượn sai bảng** (`branch` nhận giá của *giai đoạn commit*), không phải sự thật của bài toán.
2. Bảng 4-carrier (−17,8% tại Δ=0) hạ cấp từ *kết quả* xuống *phân tích độ nhạy trên bảng giá sai nguồn*. **Task 22 chặn cách đọc bảng đầu**, không còn là nợ kỹ thuật.
3. **Phát hiện tái lập cho chương đối chiếu:** áp công thức χ của §102 lên bốn số §205 ra **2,114**; paper in **1,34**. Hai đại lượng không suy ra được từ nhau bằng công thức đã in — đúng mâu thuẫn `test_cost_axes` đã bắt.
4. Kết quả âm ở Δ nhỏ **không phải thất bại**: §21/§285 của paper tự báo cáo crossover Δ≈2 và "4,2%, trong khoảng nhiễu". Ranh giới chế độ là đúng THỂ LOẠI kết quả của paper gốc — nhưng phải tính lại trên κ đo thật.

## Câu 4 — quy mô: **Verified · H=8 · N=100 · dùng lại 42%, trần 2 lần/instance**

Số đo 16/09/2026 (spike, tokenization đúng `retrieval.topic_of`):

| Pool | Instance | Repo | H=6 | **H=8** | H=10 |
|---|---|---|---|---|---|
| Verified | 500 | **12** | 78 wf · 22% | **58 wf · 42%** | 46 wf · 54% |
| Full | 2294 | **12** | 376 wf · 0% | **281 wf · 0%** | 224 wf · 0% |

(wf = workflow không dùng lại; % = mức dùng lại tối thiểu cho 100 workflow.)

- Bảng chính: **Verified** vì `FAIL_TO_PASS` đã kiểm định người — `solved` là nửa oracle. H=8 nằm trong khoảng 6–14 của §215.
- Ràng buộc dùng lại: mỗi instance xuất hiện **≤ 2 workflow** (800/500 = 1,6), `instance_source` trong manifest ghi rõ.
- Lý do trần: hai workflow chung instance thì kết quả clean-run **tương quan**, mà bootstrap bốc theo workflow giả định độc lập — dùng lại đậm làm CI hẹp giả. 42% trần-2 ký được; 4,8× (N=300 trên Verified) thì không.

## Câu 8 — tiêu chí AUC: **(b) cận trên CI95, áp THEO TỪNG Δ**

- Tiêu chí: $\widehat{\mathrm{AUC}}_{\text{upper}} \le 0{,}56$, held-out, theo từng Δ (nhất quán quyết định câu 1.5).
- Cỡ corpus: số công suất trong doc này — 620 cho cận trên 0,557 tại Δ=2 (trượt 0,003), 900 đưa về 0,528 ⇒ **~900 sự kiện đánh giá cho ô Δ bị siết**, 620 cho ô còn lại. Corpus thu hoạch bằng máy; khâu người là soát (Task 8 đo).
- **Một corpus phục vụ hai việc**: tiêu chí AUC này và hiệu chỉnh $\varepsilon^*$ (câu 1.4). Không dựng hai corpus.

## Câu 10 — model: **flash mặc định + luật rẽ nhánh sau Task 15**

- Spike 5 instance đo `solved` và cache-hit thật. **Nếu `solved` của flash < 20%** ⇒ pro cho main run, flash cho sweep; ngược lại flash toàn tuyến.
- **Cấm trộn**: không bảng nào chứa số từ hai model; model + cache-hit in trong header (L1–L4 cưỡng chế).
- Ngân sách câu 11 tính trên flash; rơi vào pro thì nhân 4,3.

## Câu 11 — N: **(b) là phát biểu chính; (a) N=300 có điều kiện — và kéo theo full pool** ⚠ chờ thầy thật

- Phát biểu chính: Δharm kèm CI95 theo từng ô $(\Delta, \chi)$, **không** tuyên bố pass/fail ngưỡng 15%.
- N=300 chạy nếu Task 15 xác nhận chi phí (ước tính \$3.266 phải được số đo xác nhận). N=300 × H=8 = 2400 slot > 500 ⇒ **bắt buộc full pool**: N=100 Verified là bảng chính, N=300 full là bảng power, khai rủi ro chất lượng test + nhiễm. Ghi cả hai vào tiền-đăng-ký trước khi chạy.
- (c) bác: phương sai giữa-workflow chi phối, thêm seed không mua được gì.

## Câu 12 — repo: **12, sửa đề cương** ⚠ chờ thầy thật

Cả hai pool đều đúng **12 repo** (đo 16/09/2026) — con số 15 không lấy được từ SWE-bench ở bất kỳ pool nào; "15 kho" của paper thuộc dataset riêng chưa công bố. Sửa đề cương về 12 kèm một câu: *"Paper báo cáo 15 kho trên dataset chưa công bố; bản tái lập dùng SWE-bench Verified (12 kho, FAIL_TO_PASS đã kiểm định người). Repo là đơn vị gom workflow, không phải biến độc lập."* Không vá 3 repo từ nguồn khác — mua rủi ro, không mua power.

## Hệ quả chặn sau bộ đáp án này

| Mốc | Trước | Sau |
|---|---|---|
| Nhóm F (Task 13–17) | chặn bởi câu 4, 10 | **chỉ còn chặn tài nguyên** (Docker, tiền API) |
| Task 20 bước 20.6 | chặn bởi câu 8 | mở — tiêu chí = cận trên CI, theo từng Δ |
| Câu 1, 3 | tự quyết | **phê chuẩn mô phỏng**, kèm errata trung vị 4 ở câu 3 |
