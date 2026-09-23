# Remaining Parameters — Measurement Plan (đợt 3)

**Ngày:** 23/09/2026 · **Đóng băng số:** 29/09 · **Nộp:** 02/10 AoE · **Còn:** 6 ngày làm đo
**Nối tiếp:** [đợt 1 — W1–W10](2026-09-22-W1-W10-tham-so.md) · [đợt 2](2026-09-23-tham-so-dot-2.md)
**Kết quả đã có:** [runbook](../../AuditGame-SE_Parameter_Measurement_Runbook.md) · [biểu đồ](../../AuditGame-SE_Parameter_Measurement_Charts.html)

---

## 0. Còn đúng chín thứ chưa đo

Đếm từ [README §3.2](../../../README.md). Đợt 2 đã xong **T3** (chốt thang USD) và **T8** (bốn checkpoint làm việc thật); phần còn lại chia ba loại, và trộn chúng là hỏng:

| # | Tham số | Loại | Vì sao chưa có | Chặn cái gì |
|---|---|---|---|---|
| **P1** | $\kappa_{\text{commit}}$ | Đo được, chưa đo | Commit audit chưa chạy differential testing | **Dấu của RQ1** |
| **P2** | $c$ (Định lý 4) | Chọn mô hình quan sát, rồi đo | Quan sát đang miễn phí ⇒ vế trái không tồn tại | Định lý 4 có phần thực nghiệm hay không |
| **P3** | $\lambda_Q, \lambda_T$ | Neo, không đo | Đang gán tay 0,10 / 0,50 | Tuyên bố chính của khung A′ |
| **P4** | $\rho$ | Chuỗi phụ thuộc | Đang đo trong không gian proxy | Mệnh đề 6 |
| **P5** | $\beta$ (skill, queue) | Báo dạng dải | Hai luật ánh xạ lệch 10× | Tính trung thực |
| **P6** | $\pi_0$, $\pi_{\text{attack}}$, $\tau_{\text{quarantine}}$ | Báo dạng dải | Mới có một điểm, chưa có dải | Tính trung thực |
| **P7** | Quy ước quét $\chi$ | Khai báo | Chưa chọn quy ước chuẩn hoá | Trục RQ2 |
| **P8** | Chênh lệch ràng buộc | Chạy lại, commit | File `reports/t3-budget-analysis.md` chưa commit | Tái lập |
| **P9** | $K$, $H$, $N$, ngưỡng AUC | Biện hộ thiết kế | Lấy theo draft, chưa có bằng chứng | Câu hỏi hội đồng |

**Nguyên tắc giữ nguyên từ đợt 1–2:** chạy từ trong `auditgame/`; code và chú thích **tiếng Anh**; mỗi giá trị kèm `provenance` (seed, số lần lặp, ngày, commit SHA); **dự đoán khai trước khi chạy**, bằng commit riêng; sau 29/09 không chỉnh tham số nào.

---

## 1. Bảng ưu tiên — quy tắc cắt

Xếp theo **một câu hỏi duy nhất: không có nó thì bài mất cái gì.**

| # | Việc | Công sức | Không có thì mất | Quyết định |
|---|---|---|---|---|
| **P1** | $\kappa_{\text{commit}}$ có chạy test | 1 ngày | Kết luận chính **không có dấu** | **Không cắt** |
| **P3** | Neo $\lambda_Q, \lambda_T$ | Nửa ngày | Tuyên bố chính đứng trên số gán tay | **Không cắt** |
| **P2** | Chọn mô hình quan sát (MA) → đo $c$ | 1 ngày | Định lý 4 không có nhánh thực nghiệm | **Không cắt** |
| **P5+P6** | Bốn phép quét | Nửa ngày | Bài khẳng định cái nó không định danh được | **Không cắt** |
| **P7** | Quy ước quét $\chi$ | 1 giờ | Trục RQ2 không đọc được | **Không cắt** (rẻ) |
| **P8** | Chênh lệch ràng buộc | 1 giờ | Một dòng 🟡 không tái lập được | **Không cắt** (rẻ) |
| **P4** | $\rho$ đúng không gian | 1 ngày + phụ thuộc 28 policy (1,5 ngày) | Mệnh đề 6 không kiểm được | **Cắt được** |
| **P9** | Biện hộ $K, H, N$ | Nửa ngày | Hội đồng hỏi thì không có số | **Cắt trước tiên** |

**Tổng không cắt: 3,25 ngày.** Còn 6 ngày, nên P4 vào được nếu P1 không trượt. Nếu P1 trượt thì P4 bị cắt, không phải ngược lại.

---

## P1 — $\kappa_{\text{commit}}$: cho commit audit chạy test thật

**Vì sao đây là việc số một.** Đo trên lưới: mọi khác biệt giữa thang USD và thang CPU quy về đúng tỉ số $\kappa_{\text{commit}}/\bar\kappa$. Thang USD *giả định* 4,00; thang CPU *đo* 1,43 nhưng thiếu differential testing. **Ngưỡng lật nằm giữa hai con số đó** — nên hiện tại kết luận chính của bài chưa có dấu.

**Không cần dựng lại hạ tầng SWE-bench.** Docker daemon không chạy, và
`Dockerfile` ở gốc repo **không dùng được cho việc này**: nó là môi trường của
**agent**, tự khai trong chính comment đầu file là *"deliberately NOT the
environment the measurement runs in"*, và nó đặt `PIP_NO_INDEX=1` / `UV_NO_INDEX=1`
— không mạng lúc chạy, nên không cài được phụ thuộc của repo dưới thử nghiệm.
Vì vậy P1 dựng **venv trên máy chủ**, không qua image đó. Bù lại:
- 10 repo đã clone sẵn trong `auditgame/workspace/`;
- `data/swebench_verified.jsonl` **đã có** `FAIL_TO_PASS`, `PASS_TO_PASS`, `environment_setup_commit`.

Nên đo được trực tiếp: *chạy đúng tập test mà instance đó khai, trên chính repo đó, và bấm giờ.*

**Files:** tạo `tools/measure_kappa_commit.py`, `spikes/kappa-commit.json`; sửa `costs.py`.

- [ ] **Bước 1 — khai trước, commit riêng.** Ghi vào `docs/preregistration/` một trang: dự đoán $\kappa_{\text{commit}}/\bar\kappa$ **lớn hơn 4,00** (vì chạy test đắt hơn chấm điểm vài bậc), và cam kết báo cả khi nó rơi dưới 2,00 — tức khi B1 vẫn thắng.
- [ ] **Bước 2 — chọn repo chạy được, khai tiêu chí trước.** Ưu tiên repo thuần Python, ít phụ thuộc biên dịch: `psf/requests`, `pytest-dev/pytest`, `sympy/sympy`. Tiêu chí loại: dựng venv thất bại, hoặc tập `PASS_TO_PASS` không chạy nổi trong 10 phút. **Repo bị loại phải đếm và báo**, không bỏ im.
- [ ] **Bước 3 — đo.** Với mỗi instance chọn được: `git checkout base_commit`, dựng venv, chạy tập `PASS_TO_PASS` (đây chính là differential testing: tập test phải giữ nguyên xanh sau khi vá), bấm bằng `time.process_time` của tiến trình con (`resource.getrusage(RUSAGE_CHILDREN)`), lặp 3 lần, lấy trung vị. Tách riêng **thời gian dựng môi trường** ra khỏi số báo — nó là chi phí một lần, không phải chi phí mỗi lượt audit.
- [ ] **Bước 4 — KHÔNG chốt giá CPU; giải ngược ra giá hoà vốn.** Đơn giá máy sẽ được cấp sau, nên `costs.py` chừa đúng một hằng:

```python
#: USD per CPU second for running a repository's test suite.  DELIBERATELY
#: UNSET: the VM price is an input this project does not own.  Everything
#: below is reported as a function of it, and `breakeven_cpu_price()` says
#: which side of the answer a given price lands on.
USD_PER_CPU_SECOND = None
```

  Báo cáo **hai đại lượng đo được, tách rời**, không trộn:

  - $T_{\text{test}}$ — giây CPU chạy tập `PASS_TO_PASS`, trung vị và dải theo repo;
  - $R$ — phần review tính bằng lượt chấm, đã đo (`KAPPA_COMMIT_USD`).

  Khi đó $\kappa_{\text{commit}}(r) = R + T_{\text{test}} \cdot r$, và thứ cần
  biết **không phải $r$ mà là ngưỡng lật**:

  $$r^{*} = \frac{m^{*}\bar\kappa - R}{T_{\text{test}}}, \qquad m^{*} \in [1{,}43;\ 2{,}00]$$

  Một câu kết luận không cần biết giá máy: *"B1 chỉ còn thắng nếu một giây CPU
  rẻ hơn $r^{*}$ USD; giá máy của anh/chị nằm bên nào của con số đó?"* Đây là
  cách tốt hơn chọn bừa một mức giá, vì nó biến đầu vào thiếu thành một **ngưỡng
  quyết định**. Hàm `breakeven_cpu_price()` in ra $r^{*}$ và nhận `USD_PER_CPU_SECOND`
  khi có để trả lời thẳng.
- [ ] **Bước 5 — chạy lại lưới** với $\kappa_{\text{commit}}$ đo được: `python3 tools/compare_cost_scales.py --n 20 --seeds 2 --sweep-commit`. Đối chiếu với đường quét đã có ở runbook §1.7: điểm đo mới phải **rơi đúng lên đường đó**. Nếu không, có chỗ chưa nối đúng.

**Nghiệm thu:** một con số cho $\kappa_{\text{commit}}/\bar\kappa$ kèm dải theo repo, và một câu phát biểu được: *"dưới giá đo được, B1 mua được N lượt commit audit mỗi episode, nên nó thắng / thua"*.

**Lối thoát nếu trượt:** giữ nguyên cách trình bày theo lưới — khai 4,00 là **giả định**, 1,43 là **cận dưới**, và báo cáo bảng kết quả trên cả dải. Cách này vẫn nộp được; nó chỉ yếu hơn một con số.

---

## P2 — Mô hình quan sát: bốn lựa chọn, rồi đo lại $c$

**Vấn đề đo được.** Posterior tại $\sigma$ đứng yên ở **0,000336** khi $B$ đi từ
2 đến 200. Nguyên nhân nằm ở `runner.py`: mỗi task, detector chấm **mọi item
sống của cả bốn carrier**, rồi `signals` đủ bốn carrier đi thẳng vào
`pol.choose` và `belief.update` — **bất kể chính sách trả tiền audit cái gì**.
Ngân sách vì vậy chỉ mua **hành động**, không mua **thông tin**. Định lý 4 nói
ngân sách mua thông tin; trong harness thì không, nên vế trái của cận không tồn
tại. Đây là lỗi mô hình, không phải lỗi phép đo.

### Bốn mô hình, và cái giá của từng cái

| | Mô hình | Ai được quan sát | Ngân sách mua thông tin? | Công sức |
|---|---|---|---|---|
| **M0** | **Quan sát miễn phí toàn phần** (hiện tại) | Cả 4 carrier, mọi task | ❌ Không | 0 |
| **MA** | **Trả tiền mới được nhìn** | Chỉ carrier đã audit bước đó | ✅ Trực tiếp | 1 ngày |
| **MB** | **Hai tầng: quét rẻ + audit sâu** | Cả 4 ở $d'$ thấp; carrier đã audit ở $d'$ cao | ✅ Qua phần **chênh** $d'$ | 1,5–2 ngày |
| **ME** | **Chỉ thấy cái đã động vào** | Carrier mà task này đọc/ghi | ❌ Không (nhưng thật hơn M0) | Nửa ngày |

**M0 — giữ nguyên.** Không phải vô lý: một scanner tĩnh chạy trên mọi thứ là có
thật, và khi đó $\kappa$ là giá của **audit sâu**, không phải giá của việc nhìn.
Nhưng nếu giữ M0 thì **Định lý 4 phải phát biểu lại** về một đại lượng khác, và
bài phải nói rõ rằng cận như đang viết không có phần thực nghiệm.

**MA — trả tiền mới được nhìn.** Đúng nghĩa Định lý 4 nhất: cận là một phát biểu
về **nhận dạng tuần tự**, chỉ có nghĩa khi mỗi lượt audit sinh ra một quan sát.

> **Kiểm trước khi chọn — MA có làm belief mù không?** Không. Ngân sách hiện tại
> mua **10,3 lượt audit carrier mỗi episode**, so với $K \cdot H = 32$ ô
> carrier-task: **32% độ phủ quan sát** (lên tới 90% nếu chỉ audit carrier rẻ
> nhất). Belief vẫn có 10 quan sát mỗi episode thay vì 32 — thưa đi, không tắt.

**MB — hai tầng.** Trung thực nhất với hệ thống thật: pipeline thật đúng là có
scanner rẻ chạy khắp nơi **cộng** review đắt. Giữ được cả hai: tín hiệu rẻ nuôi
belief, tiền mua **độ lợi thông tin**. Định lý 4 khi đó phát biểu về phần chênh
$d'_{\text{sâu}} - d'_{\text{quét}}$. Giá phải trả: cần một tầng detector thứ hai
và phải khai giá của tầng quét — thêm nửa ngày tới một ngày so với MA.

**ME — chỉ thấy cái đã động vào.** Rẻ và thật hơn M0 (không ai nhìn thấy carrier
mà task này không chạm tới), nhưng quan sát vẫn **miễn phí**, nên **không** chữa
được Định lý 4. Dùng được như một biến thể kèm theo, không dùng làm lời giải.

### Đề xuất

**Chọn MA làm mô hình chính, giữ M0 làm control** — và **chênh lệch giữa hai
bảng chính là giá của thông tin**, tức là thứ Định lý 4 nói. Hai bảng cạnh nhau
là một kết quả báo cáo được, kể cả khi số của MA xấu hơn.

**MB ghi vào Threats/Future work** như mô hình trung thực hơn, kèm lý do không
làm kịp trong 6 ngày. Nếu P1 xong sớm thì MB là thứ đáng làm tiếp, không phải P4.

### Các bước

- [ ] **Bước 1 — khai trước, commit riêng.** Ghi mô hình cũ, mô hình mới, và
      **dự đoán ngược chiều mong muốn: harm của mọi chính sách đọc điểm sẽ xấu
      đi**, kể cả Sentinel, vì chúng đang được cho thông tin miễn phí. Cam kết
      báo cả hai bảng dù số xấu đi.
- [ ] **Bước 2 — test trước khi sửa.**
      `test_an_unaudited_carrier_does_not_move_the_belief`: một carrier không ai
      trả tiền để nhìn thì không được làm dịch posterior.
- [ ] **Bước 3 — sửa** `runner.py` (chỉ truyền signals của carrier đã audit),
      `belief.py` (`update` nhận dict thưa), `policies.py` (mọi chính sách đọc
      điểm phải chịu được signals thiếu). Thêm cờ chọn mô hình để chạy được cả
      M0 lẫn MA từ một binary — không fork mã.
- [ ] **Bước 4 — đo lại $c$** bằng `tools/measure_c.py` (đã có, kèm tiền đề
      `budget_buys_information()`). Tiền đề vẫn không thoả thì script **phải tiếp
      tục từ chối**, và đó là kết quả.
- [ ] **Bước 5 — báo cả hai bảng** cạnh nhau, M0 so với MA, kèm độ phủ quan sát
      (32%) để người đọc biết MA thưa tới đâu.

**Nghiệm thu:** $c$ có số, hoặc một phát biểu kiểm chứng được về vì sao cận không
áp dụng cho harness này — cộng với một bảng nói giá của thông tin là bao nhiêu.

---

## P3 — Neo $\lambda_Q$ và $\lambda_T$

Giữ nguyên **T2 của đợt 2**. Việc rẻ nhất có ảnh hưởng lớn nhất: Sentinel thắng B1 ở **64/64 ô khi $\lambda_T = 0{,}5$ nhưng chỉ 22/64 khi $\lambda_T = 0$**.

- [ ] $\lambda_T$ = giá một task sạch bị mất = chi phí chạy lại nó = **0,0868 USD** (trung vị arm P2, `spikes/eta-q.json`).
- [ ] $\lambda_Q$ = giá một lần cách ly nhầm = $\eta_Q$ của carrier đó = **0,034–0,163 USD**.
- [ ] **Ràng buộc nhất quán, viết thành test:** $\lambda_Q$ và $\eta_Q$ là **cùng một sự kiện** được định giá ở hai chỗ — hàm mất mát và ràng buộc ngân sách. Hai bên lệch nhau là lỗi, không phải lựa chọn.
- [ ] Tỉ lệ đo được $\lambda_Q/\lambda_T = \eta_Q/0{,}0868$ = **0,39–1,88**. Đối chiếu với $\lambda_Q^{*} \approx 0{,}036$–$0{,}05$: nếu $\lambda_Q^{*}$ nằm **dưới** dải đo được thì thứ hạng vững; nằm **trong** thì kết luận phải nêu điều kiện.

**Nghiệm thu:** một câu viết được vào bài: *"thứ hạng giữ khi một lần cách ly nhầm rẻ hơn X lần một task bị mất, và chi phí đo được cho tỉ lệ Y."*

---

## P4 — $\rho$ đúng không gian (kèm 28 policy)

Giữ nguyên **T4 + T5 của đợt 2**. Đây là hạng mục **cắt được**, và cắt nó không làm bài sai — chỉ làm Mệnh đề 6 không có phần kiểm chứng.

- [ ] **28 policy** sinh theo lưới ba họ của Stage 6B: 8 stage-weighted (gồm B1 = $(0,0,0,1)$) · 12 belief-threshold ($\tau \in \{0{,}3; 0{,}5; 0{,}7; 0{,}9\}$ × 3 độ sâu) · 8 carrier-rotation. Liệt kê đủ 28 dòng vào phụ lục, **gửi thầy duyệt trước khi chạy**.
- [ ] Ít nhất một họ phải phát ra `"memory@2"`, nếu không hệ quả *"tăng độ sâu không mua được danh tính carrier"* vẫn không có nhánh thực nghiệm.
- [ ] **240 game nhỏ** $K \cdot H \le 40$, giải chính xác bằng quy nạp lùi trên belief rời rạc hoá — **không** dùng `lp.solve_stackelberg_lp`, vì đó là nghiệm marginal chứ không phải $\pi^{*}$ đầy đủ.
- [ ] $\rho = \max_{\pi^{*}} \min_{\pi \in \Pi} \mathrm{TV}$ trên **vector xác suất hành động tại từng task**, trung bình theo $H$.
- [ ] Kiểm tính đơn điệu: thêm policy thì $\rho$ **không được tăng**. Con số 28 biện hộ bằng $\rho$ bão hoà, không phải vì draft ghi 28.

---

## P5 + P6 + P7 — Bốn phép quét và một khai báo

Không chốt được thì quét, và **phép quét là kết quả**, không phải thất bại.

- [ ] **$\beta$ (skill, queue):** quét $\{0{,}01;\ 0{,}06;\ 0{,}30;\ 0{,}61\}$ — hai đầu là hai luật ánh xạ đang bất đồng. Báo thứ hạng trên cả dải.
- [ ] **$\pi_0$:** đã có bảng $\tau_{\text{sel}}$ ở 0,080; sinh thêm ở $\{0{,}04;\ 0{,}20\}$ (23 phút mỗi bảng, **chạy nền qua đêm**) để có phép quét bốn điểm thật.
- [ ] **$\pi_{\text{attack}}$:** quét $\{0{,}25;\ 0{,}5;\ 0{,}75\}$. Thứ hạng không đổi thì một câu trong bài là đủ.
- [ ] **$\tau_{\text{quarantine}}$:** đang là 0,0 nên cách ly **vô điều kiện**. Quét $\{0;\ 0{,}5;\ 0{,}8;\ 0{,}95\}$ và báo.
- [ ] **P7 — quy ước quét $\chi$:** khai **trước khi chạy** một trong ba, và báo cả ba nếu kịp: neo $\bar\kappa$ (hiện dùng, và nó làm $\chi$ **trơ** — 39,7% ở mọi $\chi$) · neo $\kappa_{\min}$ (đề xuất; ra 39,7% → 36,1%) · neo tổng. Việc này 1 giờ và mở khoá trục RQ2.

**Nghiệm thu:** mỗi tham số một dòng, dạng *"thứ hạng giữ trên toàn dải"* hoặc *"thứ hạng đổi tại giá trị X"*.

---

## P8 — Chênh lệch ràng buộc (1 giờ)

- [ ] Chạy lại phân tích ngân sách kỳ vọng (LP) so với ràng buộc cứng, ghi ra `reports/t3-budget-analysis.md`, **commit file kết quả**. Con số $-13{,}29\%$ độ phủ hiện không tái lập được vì file chưa vào repo.

---

## P9 — Biện hộ tham số thiết kế (cắt trước tiên)

- [ ] $K = 4$: ablation $K = 2, 3$ — kết luận định tính giữ hay đổi.
- [ ] $H$: phân phối độ dài chuỗi instance liên tiếp dựng được, theo từng repo.
- [ ] $N$ và số seed: phân tích lực — độ rộng CI cần để phát biểu ngưỡng 15% (cổng 3 đã có test).
- [ ] Ngưỡng AUC: suy từ CI của corpus thay vì lấy 0,56, vì đã biết 0,56 nằm trong dải nhiễu ở mọi $n \le 1800$.

---

## 2. Thứ tự chạy

```
23/09 tối   P7 khai quy ước χ   ·   P8 chạy lại và commit      [2 giờ, rẻ]
            khởi động chạy nền: sinh bảng τ_sel tại π₀ = 0,04 và 0,20

24/09       P1 bước 1–3   khai trước → dựng venv → đo test thật
25/09       P1 bước 4–5   quy sang USD, chạy lại lưới   ·   P3 neo λ
26/09       P2            khai trước → sửa mô hình quan sát → đo lại c
27/09       P5 + P6       bốn phép quét   ·   chạy lưới chính N = 100
28/09       P4            chỉ khi P1 không trượt   ·   viết Evaluation
29/09       ĐÓNG BĂNG SỐ
```

**Cắt theo thứ tự ngược nếu trễ:** P9 → P4 → (giữ lại phần quét $\beta$ của P5).
**Không cắt P1, P2, P3.** P1 quyết định dấu của kết luận; P2 quyết định Định lý 4 có phần thực nghiệm; P3 quyết định tuyên bố chính đứng hay đổ.

---

## 3. Quyết định cần thầy, trước khi chạy

1. **Mô hình quan sát (P2) — chọn một trong bốn**, xem bảng ở P2:
   **M0** giữ nguyên (phải phát biểu lại Định lý 4) · **MA** trả tiền mới được
   nhìn (đề xuất; 1 ngày; độ phủ quan sát còn 32%, belief thưa chứ không mù) ·
   **MB** hai tầng quét rẻ + audit sâu (trung thực nhất, 1,5–2 ngày) ·
   **ME** chỉ thấy cái đã động vào (rẻ, nhưng **không** chữa được Định lý 4).
   MA sẽ làm harm của **mọi** chính sách đọc điểm xấu đi, kể cả Sentinel — có
   chấp nhận số xấu hơn để định lý có phần thực nghiệm không?

2. ~~Giá CPU cho $\kappa_{\text{commit}}$~~ — **đã gỡ khỏi đường tới hạn.** Đơn giá máy sẽ được cấp sau; `USD_PER_CPU_SECOND` để trống và mọi kết quả báo theo ngưỡng hoà vốn $r^{*}$. Phép đo **không chờ** con số này.

Quyết định còn lại phải chốt **trước** khi chạy, không phải sau khi nhìn số.
