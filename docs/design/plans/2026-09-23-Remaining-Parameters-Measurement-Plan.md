# Remaining Parameters — Measurement Plan (đợt 3)

**Ngày:** 23/09/2026 · **Sửa đổi:** 24/09/2026 · **Đóng băng số:** 29/09 · **Nộp:** 02/10 AoE · **Còn:** 6 ngày làm đo
**Nối tiếp:** [đợt 1 — W1–W10](2026-09-22-W1-W10-tham-so.md) · [đợt 2](2026-09-23-tham-so-dot-2.md)
**Kết quả đã có:** [runbook](../../AuditGame-SE_Parameter_Measurement_Runbook.md) · [biểu đồ](../../AuditGame-SE_Parameter_Measurement_Charts.html)

> **Về bản sửa đổi 24/09.** Bản 23/09 có sáu lỗi logic/phương pháp mà **đã biết
> được ngay từ 23/09**, không cần nhìn kết quả; bản này sửa trực tiếp các lỗi đó
> trong thân plan (bản gốc nằm trong git, commit `0f37d42`). Những gì chỉ biết
> được **sau khi chạy** thì không trộn vào thân plan — chúng nằm riêng ở
> [§4](#4-đối-chiếu-sau-khi-chạy-2409), để plan không trông như đoán trước được
> kết quả của chính nó.
>
> | # | Lỗi ở bản 23/09 | Sửa ở |
> |---|---|---|
> | E1 | P1 để trống giá CPU nhưng khai trước, chạy lưới và nghiệm thu bằng tỉ số $\kappa_{\text{commit}}/\bar\kappa$ — thứ chỉ tính được khi có giá | P1 bước 1, 4, 5, nghiệm thu |
> | E2 | $R/\bar\kappa = 4{,}00$ là **hằng đẳng thức** (`KAPPA_COMMIT_USD = sum(KAPPA_USD.values())`, $\bar\kappa$ là trung bình của đúng bốn số đó), không phải phép đo; plan không kiểm giả định đứng sau nó | P1 bước 2 (mới) |
> | E3 | "Differential testing" thực ra là một lần chạy `PASS_TO_PASS`; bấm giờ ghi `time.process_time` (chỉ đo tiến trình cha); trung vị bỏ mất lần chạy lạnh; tiêu chí chọn repo lệch xuống | P1 bước 3–4 |
> | E4 | P1 tính ngưỡng lật trên M0 trong khi P2 đổi mô hình chính sang MA; không nói RQ1 báo dưới mô hình nào | P2, §2, §3 |
> | E5 | P3 gán $\lambda_T$ = 0,0868 **USD** — nhưng $\lambda_T$ là trọng số trong đơn vị **harm**; chỉ **tỉ số** $\lambda_Q/\lambda_T$ đo được. Đối chiếu $\lambda_Q^{*}$ (trọng số) với tỉ số là so hai đại lượng khác loại | P3 |
> | E6 | P4 kiểm "thêm policy thì $\rho$ không tăng" — đúng theo định nghĩa của min, không kiểm được gì; P5–P7 không có tiêu chí thống kê cho "thứ hạng giữ"; P7 gọi là "khai trước" dù số của cả ba quy ước đã biết | P4, P5–P7 |

---

## 0. Còn đúng chín thứ chưa đo

Đếm từ [README §3.2](../../../README.md). Đợt 2 đã xong **T3** (chốt thang USD) và **T8** (bốn checkpoint làm việc thật); phần còn lại chia ba loại, và trộn chúng là hỏng:

| # | Tham số | Loại | Vì sao chưa có | Chặn cái gì |
|---|---|---|---|---|
| **P1** | $\kappa_{\text{commit}}$ | Đo được, chưa đo | Nửa test chưa đo; nửa review là **giả định** "commit chấm mọi carrier" | **Dấu của RQ1** |
| **P2** | $c$ (Định lý 4) | Chọn mô hình quan sát, rồi đo | Quan sát đang miễn phí ⇒ vế trái không tồn tại | Định lý 4 có phần thực nghiệm hay không |
| **P3** | $\lambda_Q, \lambda_T$ | Neo **tỉ số**, khai $\lambda_T$ | Đang gán tay 0,10 / 0,50 | Tuyên bố chính của khung A′ |
| **P4** | $\rho$ | Chuỗi phụ thuộc | Đang đo trong không gian proxy | Mệnh đề 6 |
| **P5** | $\beta$ (skill, queue) | Báo dạng dải | Hai luật ánh xạ lệch 10× | Tính trung thực |
| **P6** | $\pi_0$, $\pi_{\text{attack}}$, $\tau_{\text{quarantine}}$ | Báo dạng dải | Mới có một điểm, chưa có dải | Tính trung thực |
| **P7** | Quy ước quét $\chi$ | Khai báo | Chưa chọn quy ước chuẩn hoá | Trục RQ2 |
| **P8** | Chênh lệch ràng buộc | Chạy lại, commit | File `reports/t3-budget-analysis.md` chưa commit | Tái lập |
| **P9** | $K$, $H$, $N$, ngưỡng AUC | Biện hộ thiết kế | Lấy theo draft, chưa có bằng chứng | Câu hỏi hội đồng |

**Nguyên tắc giữ nguyên từ đợt 1–2:** chạy từ trong `auditgame/`; code và chú thích **tiếng Anh**; mỗi giá trị kèm `provenance` (seed, số lần lặp, ngày, commit SHA); **dự đoán khai trước khi chạy**, bằng commit riêng; sau 29/09 không chỉnh tham số nào.

**Nguyên tắc thêm ở bản sửa đổi:**
- **Mọi con số dẫn trong plan phải có file nguồn.** Ba số của bản 23/09 chưa tìm được nguồn trong repo — posterior 0,000336, "10,3 lượt audit / 32% độ phủ", "22/64 ô khi $\lambda_T = 0$" — nên được đánh dấu **[cần dẫn nguồn]** bên dưới cho tới khi có đường dẫn tới JSON sinh ra chúng.
- **"Khai trước" chỉ áp dụng cho thứ chưa nhìn thấy số.** Lựa chọn đưa ra sau khi đã biết số thì ghi là *post-hoc*, và báo mọi phương án.
- **Mỗi so sánh thứ hạng kèm tiêu chí thống kê** (định nghĩa ở P5–P7), không dùng ước lượng điểm.

---

## 1. Bảng ưu tiên — quy tắc cắt

Xếp theo **một câu hỏi duy nhất: không có nó thì bài mất cái gì.**

| # | Việc | Công sức | Không có thì mất | Quyết định |
|---|---|---|---|---|
| **P1** | $\kappa_{\text{commit}}$: kiểm giả định review + đo test | 1,25 ngày | Kết luận chính **không có dấu** | **Không cắt** |
| **P3** | Neo tỉ số $\lambda_Q/\lambda_T$, quét $\lambda_T$ | Nửa ngày | Tuyên bố chính đứng trên số gán tay | **Không cắt** |
| **P2** | Chọn mô hình quan sát (MA) → đo $c$ | 1 ngày | Định lý 4 không có nhánh thực nghiệm | **Không cắt** |
| **P5+P6** | Bốn phép quét | Nửa ngày | Bài khẳng định cái nó không định danh được | **Không cắt** |
| **P7** | Quy ước quét $\chi$ | 1 giờ | Trục RQ2 không đọc được | **Không cắt** (rẻ) |
| **P8** | Chênh lệch ràng buộc | 1 giờ | Một dòng 🟡 không tái lập được | **Không cắt** (rẻ) |
| — | Lưới chính $N = 100$ dưới mô hình đã chốt | Nửa ngày (chạy nền) | Bảng chính của bài | **Không cắt** |
| **P4** | $\rho$ đúng không gian | 1 ngày + phụ thuộc 28 policy (1,5 ngày) | Mệnh đề 6 không kiểm được | **Cắt được** |
| **P9** | Biện hộ $K, H, N$ | Nửa ngày | Hội đồng hỏi thì không có số | **Cắt trước tiên** |

**Tổng không cắt: ≈ 4 ngày** (bản 23/09 ghi 3,25 vì bỏ sót lưới $N = 100$ và bước kiểm giả định của P1). Còn 6 ngày ⇒ **chỉ còn ~2 ngày đệm, và P4 một mình đã cần 2,5**. Vì vậy P4 mặc định **bị cắt**; chỉ mở lại nếu cuối 26/09 P1–P3 đã xong và nghiệm thu.

---

## P1 — $\kappa_{\text{commit}}$: kiểm giả định review, rồi đo phần test

**Vì sao đây là việc số một.** Đo trên lưới: mọi khác biệt giữa thang USD và
thang CPU quy về đúng tỉ số $\kappa_{\text{commit}}/\bar\kappa$, và **vùng lật đo
được là $m^{*} \in [1{,}43;\ 2{,}0]$** ([tiền đăng ký thang USD](../../preregistration/TIEN-DANG-KY-thang-van-hanh-USD.md), dòng 80).
Thang USD cho 4,00 — **trên** vùng lật; thang CPU cho 1,43 — **ở mép dưới** vùng
lật. Hai thang nằm hai phía, nên hiện tại kết luận chính của bài chưa có dấu.

**Con số 4,00 không phải phép đo (E2).** Trong `costs.py`:

```python
KAPPA_COMMIT_USD = sum(KAPPA_USD.values())   # "an audit at commit scores EVERY carrier"
```

và $\bar\kappa$ là trung bình của đúng bốn số đó, nên $R/\bar\kappa = K = 4$ **với
mọi giá**. Tức là dấu của RQ1 dưới thang USD đứng trên **một giả định mô hình**:
*review lúc commit phải chấm toàn bộ item sống của cả bốn carrier.* Nếu review
thật chỉ chấm phần diff của commit thì $R$ nhỏ hơn. Viết $R = f \cdot K\bar\kappa$
với $f$ = tỉ lệ item mà review commit thực sự phải chấm; khi đó B1 thắng lại nếu

$$f \cdot 4 + \frac{T_{\text{test}} \cdot r}{\bar\kappa} < m^{*}
\quad\Longrightarrow\quad \text{với } r = 0:\ f < f^{*} = m^{*}/4 \in [0{,}36;\ 0{,}50].$$

**Không cần dựng lại hạ tầng SWE-bench.** Docker daemon không chạy, và
`Dockerfile` ở gốc repo **không dùng được cho việc này**: nó là môi trường của
**agent**, tự khai trong chính comment đầu file là *"Deliberately NOT the
environment the measurement runs in"*, và nó đặt `PIP_NO_INDEX=1` / `UV_NO_INDEX=1`
— không mạng lúc chạy, nên không cài được phụ thuộc của repo dưới thử nghiệm.
Vì vậy P1 dựng **venv trên máy chủ**, không qua image đó. Bù lại:
- 10 repo đã clone sẵn trong `auditgame/workspace/`;
- `data/swebench_verified.jsonl` **đã có** `FAIL_TO_PASS`, `PASS_TO_PASS`, `test_patch`, `environment_setup_commit`.

**Files:** tạo `tools/measure_kappa_commit.py`, `spikes/kappa-commit.json`; sửa `costs.py`.

- [ ] **Bước 1 — khai trước, commit riêng.** Ghi vào `docs/preregistration/` một
      trang. Chỉ khai những đại lượng **tính được mà không cần giá máy** (E1):
  - $f$ (bước 2): dự đoán và ngưỡng $f^{*} \in [0{,}36;\ 0{,}50]$;
  - $T_{\text{test}}$ (bước 3): dự đoán theo giây CPU, cả bản ấm lẫn bản lạnh;
  - $r^{*}$ (bước 4): dấu của nó. Nếu $f \cdot 4 \ge 2{,}0$ thì $r^{*} < 0$, tức
    **không có giá máy nào** làm B1 thắng — khai trước rằng đây là một kết quả
    hợp lệ, không phải lỗi.

  Cam kết báo cả khi kết quả làm B1 thắng.
- [ ] **Bước 2 — kiểm giả định "commit chấm mọi carrier" (mới, E2).** Trên các
      instance đo ở bước 3, đếm số item carrier mà diff của commit (`patch` +
      `test_patch`) **thực sự chạm tới**, chia cho số item sống — ra $f$ theo
      instance. Báo trung vị và dải. Nếu phần lớn instance có $f < f^{*}$ thì
      giả định của `KAPPA_COMMIT_USD` là **cận trên**, và bài phải báo RQ1 dưới
      cả hai mô hình review (toàn bộ / chỉ diff). Chưa đo được $f$ thì ghi rõ
      trong bài rằng dấu của RQ1 dưới thang USD **phụ thuộc giả định này**.
- [ ] **Bước 3 — chọn instance, khai tiêu chí trước.** Ưu tiên repo thuần Python,
      ít phụ thuộc biên dịch: `psf/requests`, `pytest-dev/pytest`, `sympy/sympy`.
      Tiêu chí loại: dựng venv thất bại, hoặc tập test không chạy nổi trong 10
      phút. **Khai trước:** tối thiểu **n ≥ 15 instance, trải trên ≥ 2 repo**; dưới
      mức đó thì $T_{\text{test}}$ chỉ báo kèm dải, không báo trung vị như một con
      số. **Repo và instance bị loại phải đếm và báo**, và bài ghi rõ tiêu chí loại
      **lệch về phía rẻ** (loại đúng những repo nặng: django, astropy,
      scikit-learn) ⇒ $T_{\text{test}}$ đo được là **cận dưới**.
- [ ] **Bước 4 — đo (E3).** Với mỗi instance: dựng venv ở
      `environment_setup_commit`, `git checkout base_commit`, rồi chạy
      **differential testing thật** — hai lần chạy, trước và sau khi áp `patch` +
      `test_patch`:
  - **trước vá:** `PASS_TO_PASS` (phải xanh);
  - **sau vá:** `PASS_TO_PASS` ∪ `FAIL_TO_PASS` (phải xanh hết).

  $T_{\text{test}}$ = tổng hai lần. Nếu không áp được patch (thiếu phụ thuộc, lỗi
  dựng) thì chỉ đo lần trước vá và **gắn nhãn cận dưới** cho instance đó.

  **Bấm giờ.** Lấy **hiệu** `resource.getrusage(RUSAGE_CHILDREN)` (user + sys)
  trước/sau mỗi tiến trình con — `RUSAGE_CHILDREN` cộng dồn nên phải lấy hiệu;
  **không** dùng `time.process_time` (chỉ đo tiến trình cha). Ghi thêm
  **wall-clock** (`time.perf_counter`), vì máy ảo tính tiền theo vCPU-giờ, không
  theo giây CPU: test nặng I/O sẽ có CPU < wall. Lặp 3 lần, báo **cả hai**:
  - **lần 1 (lạnh)** — gần với audit thật, vốn chạy trên checkout mới;
  - **trung vị lần 2–3 (ấm).**

  Tách **thời gian dựng môi trường** ra khỏi số báo — nó là chi phí một lần.
- [ ] **Bước 5 — KHÔNG chốt giá CPU; giải ngược ra giá hoà vốn.** Đơn giá máy sẽ
      được cấp sau, nên `costs.py` chừa đúng một hằng:

```python
#: USD per CPU second for running a repository's test suite.  DELIBERATELY
#: UNSET: the VM price is an input this project does not own.  Everything
#: below is reported as a function of it, and `breakeven_cpu_price()` says
#: which side of the answer a given price lands on.
USD_PER_CPU_SECOND = None
```

  Báo cáo **ba đại lượng, tách rời**, không trộn:

  - $f$ — tỉ lệ item review commit phải chấm (bước 2);
  - $R = f \cdot K\bar\kappa$ — phần review, tính bằng lượt chấm;
  - $T_{\text{test}}$ — giây CPU (và wall) của differential testing, lạnh và ấm, trung vị và dải.

  Khi đó $\kappa_{\text{commit}}(r) = R + T_{\text{test}} \cdot r$, và ngưỡng lật là

  $$r^{*} = \frac{m^{*}\bar\kappa - R}{T_{\text{test}}}, \qquad m^{*} \in [1{,}43;\ 2{,}0]$$

  Báo $r^{*}$ ở **cả hai mép** của $m^{*}$. **$r^{*} < 0$** nghĩa là riêng phần
  review đã vượt vùng lật: dấu của RQ1 **không phụ thuộc giá máy**, nhưng
  **phụ thuộc $f$** — và câu kết luận phải nói cả hai điều. $r^{*} > 0$ thì câu
  kết luận là: *"B1 chỉ còn thắng nếu một giây CPU rẻ hơn $r^{*}$ USD."*
  `breakeven_cpu_price()` in $r^{*}$ và nhận `USD_PER_CPU_SECOND` khi có để trả
  lời thẳng.
- [ ] **Bước 6 — đặt kết quả lên đường quét, không chạy một điểm (E1).**
      Chạy `python3 tools/compare_cost_scales.py --n 20 --seeds 2 --sweep-commit`
      để có đường harm theo $\kappa_{\text{commit}}/\bar\kappa$, rồi **đánh dấu
      trên đường đó** vùng $\kappa_{\text{commit}}/\bar\kappa$ mà $(f, T_{\text{test}}, r)$
      cho ra, với $r$ chạy trên dải giá máy hợp lý. Đối chiếu với runbook §1.7.
      **Nếu P2 chốt MA làm mô hình chính thì bước này chạy lại sau P2** (E4) —
      MA làm các chính sách đọc điểm dịch chuyển trong khi B1 đứng yên, nên
      $m^{*}$ dưới MA có thể khác $m^{*}$ dưới M0.

**Nghiệm thu:** $f$ (hoặc một câu nói rõ nó chưa đo), $T_{\text{test}}$ lạnh/ấm kèm
dải và nhãn **cận dưới**, $r^{*}$ ở hai mép $m^{*}$, và một câu phát biểu được:
*"dưới giả định review chấm tỉ lệ $f$ item, B1 thắng/thua với mọi giá máy / khi
giá máy dưới $r^{*}$"* — dưới đúng mô hình quan sát mà RQ1 báo cáo.

**Lối thoát nếu trượt:** giữ cách trình bày theo lưới — khai 4,00 là **giả định
review toàn bộ**, 1,43 là **cận dưới** (thiếu differential testing), và báo bảng
kết quả trên cả dải. Vẫn nộp được; chỉ yếu hơn một con số.

---

## P2 — Mô hình quan sát: bốn lựa chọn, rồi đo lại $c$

**Vấn đề đo được.** Posterior tại $\sigma$ đứng yên ở **0,000336** khi $B$ đi từ
2 đến 200 **[cần dẫn nguồn: file JSON của phép đo này]**. Nguyên nhân nằm ở
`runner.py`: mỗi task, detector chấm **mọi item sống của cả bốn carrier**, rồi
`signals` đủ bốn carrier đi thẳng vào `pol.choose` và `belief.update` — **bất kể
chính sách trả tiền audit cái gì**. Ngân sách vì vậy chỉ mua **hành động**, không
mua **thông tin**. Định lý 4 nói ngân sách mua thông tin; trong harness thì không,
nên vế trái của cận không tồn tại. Đây là lỗi mô hình, không phải lỗi phép đo.

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
> mua **10,3 lượt audit carrier mỗi episode** **[cần dẫn nguồn]**, so với
> $K \cdot H = 32$ ô carrier-task: **32% độ phủ quan sát** (lên tới 90% nếu chỉ
> audit carrier rẻ nhất). Belief vẫn có 10 quan sát mỗi episode thay vì 32 — thưa
> đi, không tắt.

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

**RQ1 báo dưới mô hình nào (E4) — phải chốt cùng lúc với chọn MA, trước khi
chạy.** Đề xuất: **bảng chính của RQ1 dưới MA** (cùng mô hình với Định lý 4, để
bài chỉ có một thế giới), **M0 là bảng phụ**. Hệ quả: ngưỡng lật $m^{*}$ của P1
phải đo lại dưới MA (P1 bước 6).

**MB ghi vào Threats/Future work** như mô hình trung thực hơn, kèm lý do không
làm kịp trong 6 ngày. Nếu P1 xong sớm thì MB là thứ đáng làm tiếp, không phải P4.

### Các bước

- [ ] **Bước 0 — liệt kê từ code, trước khi khai (mới).** Đọc `policies.py` và
      lập danh sách **chính sách nào thực sự đọc `signals`** trong `choose` (và qua
      belief). Chỉ những chính sách đó mới bị MA tác động; những chính sách không
      đọc thì dưới MA phải **giống hệt** M0 — đây là một kiểm tra tự động, không
      phải dự đoán. Bản 23/09 viết "mọi chính sách đọc điểm, kể cả Sentinel" mà
      chưa kiểm Sentinel có đọc hay không.
- [ ] **Bước 1 — khai trước, commit riêng.** Ghi mô hình cũ, mô hình mới, danh
      sách ở bước 0, mô hình báo RQ1, và **dự đoán ngược chiều mong muốn: harm
      của các chính sách trong danh sách bước 0 sẽ xấu đi**, vì chúng đang được
      cho thông tin miễn phí. Khai trước cả tiêu chí "xấu đi" theo tiêu chí thống
      kê ở P5–P7, không theo số điểm. Cam kết báo cả hai bảng dù số xấu đi.
- [ ] **Bước 2 — test trước khi sửa.**
      `test_an_unaudited_carrier_does_not_move_the_belief`: một carrier không ai
      trả tiền để nhìn thì không được làm dịch posterior. Thêm
      `test_a_policy_that_ignores_signals_is_identical_under_MA`: kiểm tra ở bước 0.
- [ ] **Bước 3 — sửa** `runner.py` (chỉ truyền signals của carrier đã audit),
      `belief.py` (`update` nhận dict thưa), `policies.py` (mọi chính sách đọc
      điểm phải chịu được signals thiếu). Thêm cờ chọn mô hình để chạy được cả
      M0 lẫn MA từ một binary — không fork mã.
- [ ] **Bước 4 — đo lại $c$** bằng `tools/measure_c.py` (đã có, kèm tiền đề
      `budget_buys_information()`). Tiền đề vẫn không thoả thì script **phải tiếp
      tục từ chối**, và đó là kết quả.
- [ ] **Bước 5 — báo cả hai bảng** cạnh nhau, M0 so với MA, **kèm CI bootstrap
      theo workflow**, kèm độ phủ quan sát đo được (không dùng con số 32% ước tính
      ở trên) để người đọc biết MA thưa tới đâu.

**Nghiệm thu:** $c$ có số, hoặc một phát biểu kiểm chứng được về vì sao cận không
áp dụng cho harness này — cộng với một bảng nói giá của thông tin là bao nhiêu,
và RQ1 được báo dưới đúng một mô hình đã khai.

---

## P3 — Neo tỉ số $\lambda_Q/\lambda_T$, khai và quét $\lambda_T$

Giữ **T2 của đợt 2**, sửa đơn vị (E5). Việc rẻ nhất có ảnh hưởng lớn nhất:
Sentinel thắng B1 ở **64/64 ô khi $\lambda_T = 0{,}5$ nhưng chỉ 22/64 khi
$\lambda_T = 0$** **[cần dẫn nguồn cho 22/64; 64/64 ở
[tiền đăng ký m-x v2](../../preregistration/TIEN-DANG-KY-m-x-va-F-detect-v2.md), dòng 192]**.

**Đơn vị.** Hàm mất mát là $L = \text{harm} + \lambda_Q\, Q_{\text{false}} + \lambda_T\, T_{\text{lost}}$,
nên $\lambda_Q, \lambda_T$ là **số sự kiện harm tương đương** với một lần cách ly
nhầm / một task sạch bị mất — không phải USD. Không phép đo nào trong dự án định
giá được một sự kiện harm, nên **$\lambda_T$ không đo được; nó phải khai và quét**.
Cái đo được là **tỉ số** giữa hai sự kiện mà dự án định giá được bằng USD:

- [ ] Giá một task sạch bị mất = chi phí chạy lại nó = **0,0868 USD** (trung vị arm P2, `spikes/eta-q.json`).
- [ ] Giá một lần cách ly nhầm = $\eta_Q$ **(giá cách ly, đo ở `spikes/eta-q.json`)** của carrier đó = **0,034–0,163 USD**.
      Lưu ý tên: `Policy.eta_Q` trong `policies.py` là **ngưỡng harm**, không phải
      giá này — test ở dưới phải đọc đúng biến giá.
- [ ] Tỉ số đo được $\lambda_Q/\lambda_T = \eta_Q^{\text{price}}/0{,}0868$ = **0,39–1,88** theo carrier.
      Vì $\lambda_Q$ ghép theo từng carrier, hàm mất mát nhận **$\lambda_Q$ theo
      carrier** $= \text{tỉ số}_c \cdot \lambda_T$, không dùng một hằng chung.
- [ ] **Ràng buộc nhất quán, viết thành test:** giá cách ly dùng trong ràng buộc
      ngân sách và tỉ số dùng trong hàm mất mát phải lấy từ **cùng một hằng** —
      hai bên lệch nhau là lỗi, không phải lựa chọn.
- [ ] **Quét $\lambda_T$** trên $\{0;\ 0{,}1;\ 0{,}25;\ 0{,}5;\ 0{,}75;\ 1\}$ với
      $\lambda_Q$ ghim theo tỉ số, và báo **giá trị $\lambda_T$ mà người thắng đổi**.
- [ ] **Đối chiếu $\lambda_Q^{*}$ đúng loại.** $\lambda_Q^{*} \approx 0{,}036$–$0{,}05$
      là một **trọng số**, tính ở một giá trị $\lambda_T$ cố định. Phải ghi rõ giá
      trị $\lambda_T$ đó, đổi sang tỉ số $\lambda_Q^{*}/\lambda_T$, rồi mới so với
      dải 0,39–1,88: **dưới** dải ⇒ thứ hạng vững; **trong** dải ⇒ kết luận nêu
      điều kiện. So thẳng 0,036 với 0,39 là so hai đại lượng khác loại.

**Nghiệm thu:** một câu viết được vào bài: *"một lần cách ly nhầm đo được bằng
0,39–1,88 lần một task sạch bị mất; với tỉ số đó, người thắng giữ nguyên khi một
task sạch bị mất đáng dưới X sự kiện harm, và đổi thành Y ở trên mức đó."*

---

## P4 — $\rho$ đúng không gian (kèm 28 policy)

Giữ nguyên **T4 + T5 của đợt 2**. Đây là hạng mục **cắt được** — và theo §1 là
**mặc định cắt** — cắt nó không làm bài sai, chỉ làm Mệnh đề 6 không có phần kiểm
chứng.

- [ ] **28 policy** sinh theo lưới ba họ của Stage 6B: 8 stage-weighted (gồm B1 = $(0,0,0,1)$) · 12 belief-threshold ($\tau \in \{0{,}3; 0{,}5; 0{,}7; 0{,}9\}$ × 3 độ sâu) · 8 carrier-rotation. Liệt kê đủ 28 dòng vào phụ lục, **gửi thầy duyệt trước khi chạy, hạn trả lời 26/09 tối**; quá hạn thì P4 cắt hẳn.
- [ ] Ít nhất một họ phải phát ra `"memory@2"`, nếu không hệ quả *"tăng độ sâu không mua được danh tính carrier"* vẫn không có nhánh thực nghiệm.
- [ ] **240 game nhỏ** $K \cdot H \le 40$, giải chính xác bằng quy nạp lùi trên belief rời rạc hoá — **không** dùng `lp.solve_stackelberg_lp`, vì đó là nghiệm marginal chứ không phải $\pi^{*}$ đầy đủ. **Báo sai số rời rạc hoá:** giải lại ở lưới belief mịn gấp đôi trên một mẫu game và báo $|\rho_{\text{mịn}} - \rho_{\text{thô}}|$.
- [ ] $\rho = \max_{\pi^{*}} \min_{\pi \in \Pi} \mathrm{TV}$ trên **vector xác suất hành động tại từng task**, trung bình theo $H$.
- [ ] **Bão hoà, không phải đơn điệu (E6).** Thêm policy thì $\rho$ không tăng là
      **đúng theo định nghĩa** của min, nên không kiểm. Thay vào đó: khai trước
      **một thứ tự thêm policy** (theo họ, rồi theo tham số), vẽ $\rho(|\Pi|)$ theo
      thứ tự đó, và khai trước tiêu chí bão hoà (ví dụ: 5 policy cuối không làm
      $\rho$ giảm quá sai số rời rạc hoá). Con số 28 được biện hộ bằng đường bão
      hoà đó, không phải vì draft ghi 28.

---

## P5 + P6 + P7 — Bốn phép quét và một khai báo

Không chốt được thì quét, và **phép quét là kết quả**, không phải thất bại.

**Tiêu chí "thứ hạng giữ" (E6), dùng chung cho mọi phép quét ở đây và cho P2:**
với mỗi cặp chính sách so sánh (ít nhất Sentinel–B1), tính CI 95% bootstrap
**theo workflow** của hiệu harm tại mỗi điểm quét. *Thứ hạng đổi* tại một điểm khi
CI của hiệu **loại trừ 0 với dấu ngược** dấu ở điểm mặc định. CI chứa 0 thì báo
là **không phân biệt được**, không phải "giữ". Mỗi phép quét giữ các tham số khác
ở mặc định (quét từng tham số một) — ghi rõ trong bài rằng tương tác giữa các tham
số **không được kiểm**.

- [ ] **$\beta$ (skill, queue):** quét $\{0{,}01;\ 0{,}06;\ 0{,}30;\ 0{,}61\}$ — hai đầu là hai luật ánh xạ đang bất đồng. Báo thứ hạng trên cả dải.
- [ ] **$\pi_0$:** đã có bảng $\tau_{\text{sel}}$ ở 0,080; sinh thêm ở $\{0{,}04;\ 0{,}20\}$ (23 phút mỗi bảng, **chạy nền qua đêm**) để có phép quét bốn điểm thật.
- [ ] **$\pi_{\text{attack}}$:** quét $\{0{,}25;\ 0{,}5;\ 0{,}75\}$. Thứ hạng không đổi thì một câu trong bài là đủ.
- [ ] **$\tau_{\text{quarantine}}$:** đang là 0,0 nên cách ly **vô điều kiện**. Quét $\{0;\ 0{,}5;\ 0{,}8;\ 0{,}95\}$ và báo.
- [ ] **P7 — quy ước quét $\chi$ (post-hoc, ghi đúng là post-hoc).** Số của hai
      quy ước **đã biết trước khi chọn** — neo $\bar\kappa$ làm $\chi$ **trơ**
      (39,7% ở mọi $\chi$), neo $\kappa_{\min}$ ra 39,7% → 36,1% — nên đây **không
      phải** tiền đăng ký. Làm: (a) chọn quy ước chính bằng **lý do không phụ
      thuộc số** (quy ước nào giữ nguyên đại lượng mà RQ2 hỏi), viết lý do trước;
      (b) **báo cả ba** (neo $\bar\kappa$, neo $\kappa_{\min}$, neo tổng) trong bài,
      ghi rõ lựa chọn là post-hoc. Việc này 1 giờ và mở khoá trục RQ2.

**Nghiệm thu:** mỗi tham số một dòng, dạng *"thứ hạng giữ trên toàn dải"*,
*"thứ hạng đổi tại giá trị X"* hoặc *"không phân biệt được từ X trở lên"* — theo
đúng tiêu chí CI ở trên.

---

## P8 — Chênh lệch ràng buộc (1 giờ)

- [ ] Chạy lại phân tích ngân sách kỳ vọng (LP) so với ràng buộc cứng, ghi ra `reports/t3-budget-analysis.md`, **commit file kết quả kèm provenance**. Con số $-13{,}29\%$ độ phủ hiện không tái lập được vì file chưa vào repo; nếu chạy lại ra số khác thì báo số mới và ghi chênh lệch, không giữ số cũ.

---

## P9 — Biện hộ tham số thiết kế (cắt trước tiên)

- [ ] $K = 4$: ablation $K = 2, 3$ — kết luận định tính giữ hay đổi.
- [ ] $H$: phân phối độ dài chuỗi instance liên tiếp dựng được, theo từng repo.
- [ ] $N$ và số seed: phân tích lực — độ rộng CI cần để phát biểu ngưỡng 15% (cổng 3 đã có test).
- [ ] Ngưỡng AUC: suy từ CI của corpus thay vì lấy 0,56, vì đã biết 0,56 nằm trong dải nhiễu ở mọi $n \le 1800$.

---

## 2. Thứ tự chạy

Thứ tự đổi so với bản 23/09 (E4): **chốt mô hình quan sát trước**, rồi mới tính
ngưỡng lật của P1 dưới mô hình đó.

```
23/09 tối   P7 viết lý do chọn quy ước χ, báo cả ba   ·   P8 chạy lại, commit   [2 giờ]
            gửi thầy: quyết định §3 (mô hình quan sát + mô hình báo RQ1)
            chạy nền: sinh bảng τ_sel tại π₀ = 0,04 và 0,20

24/09       P1 bước 1–4   khai trước → đếm f → dựng venv → differential testing
            P2 bước 0–1   liệt kê chính sách đọc signals → khai trước MA
25/09       P2 bước 2–5   sửa mô hình quan sát → đo lại c → bảng M0/MA có CI
26/09       P1 bước 5–6   r*, rồi đặt lên đường quét DƯỚI mô hình đã chốt
            P3            neo tỉ số, quét λ_T
            (hạn thầy trả lời 28 policy — quá hạn thì P4 cắt hẳn)
27/09       P5 + P6       bốn phép quét, tiêu chí CI
            chạy nền: lưới chính N = 100 dưới mô hình đã chốt
28/09       ĐỆM — dùng cho P1/P2 trượt; nếu không trượt: P4 (chỉ khi 28 policy đã duyệt)
            viết Evaluation
29/09       ĐÓNG BĂNG SỐ
```

**Cắt theo thứ tự nếu trễ:** P9 → P4 → phép quét $\pi_{\text{attack}}$ →
phép quét $\tau_{\text{quarantine}}$. **Không cắt** P1, P2, P3, phép quét $\beta$
và $\pi_0$, lưới $N = 100$. P1 quyết định dấu của kết luận; P2 quyết định Định lý
4 có phần thực nghiệm và RQ1 sống trong thế giới nào; P3 quyết định tuyên bố chính
đứng hay đổ.

---

## 3. Quyết định cần thầy, trước khi chạy

1. **Mô hình quan sát (P2) — chọn một trong bốn**, xem bảng ở P2:
   **M0** giữ nguyên (phải phát biểu lại Định lý 4) · **MA** trả tiền mới được
   nhìn (đề xuất; 1 ngày; belief thưa chứ không mù) · **MB** hai tầng quét rẻ +
   audit sâu (trung thực nhất, 1,5–2 ngày) · **ME** chỉ thấy cái đã động vào (rẻ,
   nhưng **không** chữa được Định lý 4). MA dự kiến làm harm của các chính sách
   đọc điểm xấu đi — có chấp nhận số xấu hơn để định lý có phần thực nghiệm không?

2. **RQ1 báo dưới mô hình nào (mới, E4).** Đề xuất: MA là bảng chính, M0 là bảng
   phụ — để RQ1 và Định lý 4 cùng một thế giới. Chốt cùng lúc với câu 1.

3. **Mô hình review lúc commit (mới, E2).** Draft ngầm giả định review commit chấm
   **mọi** carrier ($f = 1$), và dấu của RQ1 dưới thang USD đứng trên giả định đó.
   Có chấp nhận báo RQ1 dưới cả hai mô hình (toàn bộ / chỉ diff) nếu $f$ đo được
   rơi dưới $f^{*} \approx 0{,}36$–$0{,}50$ không?

4. ~~Giá CPU cho $\kappa_{\text{commit}}$~~ — **đã gỡ khỏi đường tới hạn.** Đơn
   giá máy sẽ được cấp sau; `USD_PER_CPU_SECOND` để trống và mọi kết quả báo theo
   ngưỡng hoà vốn $r^{*}$. Phép đo **không chờ** con số này.

Các quyết định còn lại phải chốt **trước** khi chạy, không phải sau khi nhìn số.

---

## 4. Đối chiếu sau khi chạy (24/09)

*Mục này ghi những gì chỉ biết được **sau khi chạy**. Nó không sửa thân plan ở
trên; nó cho biết các lỗi E1–E6 đã để lại dấu gì trong kết quả, và việc gì còn phải
làm trước khi đóng băng.*

| Hạng mục | Kết quả | Lỗi của bản 23/09 còn in dấu | Việc còn lại |
|---|---|---|---|
| P1 | `spikes/kappa-commit.json`: $T_{\text{test}}$ = 0,599 s CPU (trung vị), dải 0,047–6,071, **n = 6, chỉ sympy**; một instance có ba lần chạy 894 / 67 / 77 s. README kết luận "dấu RQ1 không phụ thuộc giá máy" vì $R/\bar\kappa = 4{,}00$ đã vượt vùng lật ⇒ $r^{*} < 0$ | **E2**: kết luận đó đứng hoàn toàn trên giả định $f = 1$, chưa được kiểm. **E3**: n = 6 < 15, một repo, trung vị bỏ mất lần lạnh (894 s), chỉ chạy lần trước vá | Đếm $f$ (P1 bước 2); sửa câu README thành *"không phụ thuộc giá máy, **với điều kiện** review commit chấm mọi carrier"*; gắn nhãn cận dưới cho $T_{\text{test}}$ |
| P2 | `spikes/observation-M0-vs-MA.json`: dự đoán MA1 (harm không giảm) **bị bác** — 25 ô giảm, 19 tăng, 16 giữ; **Sentinel không đổi** dưới MA; B1 giống hệt | Bản 23/09 viết "kể cả Sentinel" mà chưa kiểm Sentinel có đọc signals không — bước 0 lẽ ra đã bắt được. Kết quả là ước lượng điểm, N = 40 × 3 seed, **không có CI** | Thêm CI bootstrap cho bảng M0/MA; ghi trong bài rằng dự đoán tiền đăng ký bị bác; xác nhận RQ1 báo dưới mô hình nào (§3 câu 2) |
| P3 | `spikes/lambda-anchors.json`: tỉ số đo được 0,39–1,88 (trung bình 1,10), gán tay 0,2 thấp hơn 5,49×; người thắng đổi tại $\lambda_T = 0{,}5$ và $0{,}75$. File đã tự ghi đúng rằng $\lambda_T$ *"no measurement here can supply"* | E5 được sửa **trong code** nhưng câu $\lambda_T = 0{,}0868$ USD trong plan cũ vẫn có thể bị trích sai | Đổi $\lambda_Q^{*}$ sang dạng tỉ số trước khi đưa vào bài; lưới chỉ có seed (1, 2), N = 20 ⇒ cần CI trước khi nói "đổi tại 0,5" |
| P4, P7, P8 | Có `spikes/small-games.json`, `spikes/rq2-chi-axis.json`, `docs/reports/t3-budget-analysis.md` | Chưa đối chiếu trong bản sửa đổi này | Kiểm P4 có đường bão hoà theo thứ tự khai trước không; kiểm P7 có báo cả ba quy ước và ghi post-hoc không |
| Đóng băng | Commit `9f78967` (24/09) — sớm hơn mốc 29/09 | — | Mọi sửa ở các dòng trên nếu đụng tới số phải đi qua quy trình mở băng, không sửa thẳng |
