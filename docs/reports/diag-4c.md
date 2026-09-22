# Cổng 4c — Chẩn đoán hồi quy của SSGRecedingUpstream trên lớp upstream (2,4)

**Ngày:** 2026-09-20 · **Brief:** `.superpowers/sdd/2026-09-20-ssg-gate4c/task-1-brief.md`
**Script:** `auditgame/spikes/diag_4c.py` · **Kết quả thô:** `auditgame/spikes/diag-4c.json`

> **Phán quyết một dòng.** Cả hai giả thuyết trong brief, **đọc đúng nghĩa đen**, đều
> **BỊ BÁC BỎ**: SSG-up không "tham lam sớm rồi cạn tiền" (nó vẫn tiêu NHIỀU HƠN tĩnh ở
> TASK CUỐI CÙNG, không hề bỏ trống cửa sổ muộn), và `_done` (C) không hề rỗng (điền ở
> 325/325 ván). Nhưng bật/tắt C **CÓ** đổi harm: tắt C (ép `done=None`) làm harm giảm
> 0.0270 (từ 0.5721 xuống 0.5450) — tức C, NHƯ ĐANG CÀI, làm harm TỆ HƠN so với không có
> nó. Đó là **22.2%** của khoảng cách hồi quy (+0.1216). **77.8% còn lại không được cắt
> nghĩa bởi C** — nó tồn tại y hệt (thậm chí lớn hơn ở task cuối) trong nhánh đã tắt C —
> nên phải gán cho một cơ chế thứ ba (bản thân việc giải lại LP mỗi task), CHƯA được
> phân định trong phạm vi task này.

---

## 1. Việc đã làm

1. Đọc brief `task-1-brief.md`, đọc `lp.py` (`solve_remaining_lp`, `solve_stackelberg_lp`),
   `policies.py` (`SSGReceding`/`SSGRecedingUpstream`/`MinimaxLP`/`MinimaxLPUpstream`,
   `REGISTRY`), và `dprime_sweep.py` (`make_corpus`, `measure_cell`, `policy_curve`) và
   `runner.py` (`paired`, `run_once` — xác nhận `pol.choose(t,...)` được gọi trước, rồi
   `pol.charge(cost)` ngay sau, nên `self.spent` trong `choose()` là chi TRƯỚC hành động
   này).
2. Viết `auditgame/spikes/diag_4c.py` — KHÔNG sửa `lp.py`/`policies.py`. Ba lớp chẩn đoán
   cục bộ, đăng ký vào `policies.REGISTRY` lúc runtime (không sửa file):
   - `DiagB7U(MinimaxLPUpstream)` — bọc `choose()` gốc, ghi `(t, action, spent_after)`
     mỗi bước vào một list cấp lớp `TRACE` (mỗi phần tử = một episode/instance).
   - `DiagSSGUp(SSGRecedingUpstream)` — bọc `choose()` gốc y hệt, thêm ghi
     `len(self._done)` và `sum(self._done.values())` mỗi bước.
   - `DiagSSGUpNoC(SSGRecedingUpstream)` — **copy nguyên văn** thân
     `SSGReceding.choose()` (policies.py dòng 433–459), CHỈ đổi
     `done=getattr(self, "_done", None)` thành `done=None` (ép cứng). Dùng CÙNG
     `seed_of(self.rng_seed, t, self.SEED_TAG)` với bản gốc (`SEED_TAG = "ssg_receding_up"`
     kế thừa nguyên) nên dòng ngẫu nhiên giống hệt — khác biệt harm đo được CHỈ có thể
     đến từ `done=None`, không lẫn với nhiễu seed.
3. Chạy `dprime_sweep.make_corpus(40, 8, seed=ds.CORPUS_SEED)` và
   `dprime_sweep.measure_cell(wfs, d_prime=2.2, delta=4, budget=17.95, seeds=(1,2,3),
   policies=("B1 audit-at-commit","Sentinel","DIAG B7U instrumented",
   "DIAG SSG-up instrumented","DIAG SSG-up noC"))` — đúng ô hồi quy nặng nhất trong bảng
   của brief (Δ=4, d'=2.2, lớp (2,4)). `B1` và `Sentinel` có mặt trong tuple vì
   `measure_cell` đòi.
4. **Kiểm tra hợp lệ của chính script chẩn đoán** trước khi tin số: so `DIAG B7U
   instrumented` và `DIAG SSG-up instrumented` (chỉ bọc thêm log, không đổi hành vi) với
   `auditgame/spikes/ssg-gates.json` (`gate_4b`, `delta=4, d'=2.2, "(2,4)"`).

### Lệnh đã chạy

```bash
cd auditgame && time python3 spikes/diag_4c.py
```

Output:

```
[diag_4c] do o Delta=4, d'=2.2, lop (2, 4), B=17.95, seeds=(1, 2, 3), N_WF=40, H=8
[diag_4c] policies=('B1 audit-at-commit', 'Sentinel', 'DIAG B7U instrumented', 'DIAG SSG-up instrumented', 'DIAG SSG-up noC')
[diag_4c] do xong sau 21.5s, n_feasible=37/40, reason=None
[diag_4c] ghi spikes/diag-4c.json
python3 spikes/diag_4c.py  21.41s user 0.06s system 99% cpu 21.518 total
```

---

## 2. Kiểm tra hợp lệ: script chẩn đoán có tái tạo đúng ssg-gates.json không

| policy | harm (script chẩn đoán) | harm (`ssg-gates.json`) | spent (script) | spent (`ssg-gates.json`) |
|---|---|---|---|---|
| B7U tĩnh (`DIAG B7U instrumented`) | 0.45045045045045046 | 0.45045045045045046 | 15.024324324324324 | 15.024324324324324 |
| SSG-up lùi (`DIAG SSG-up instrumented`) | 0.5720720720720721 | 0.5720720720720721 | 15.407207207207206 | 15.407207207207206 |

**Khớp tuyệt đối từng chữ số.** Việc bọc `choose()` để ghi log không làm lệch hành vi —
số trong các phần dưới đây đáng tin theo nghĩa "đo trên đúng hệ thống đang hồi quy", không
phải một bản sao đã trôi.

n_feasible = 37/40 workflow (3 workflow không xây được attack ở Δ=4, d'=2.2 — giống hệt
mẫu số 37 ẩn sau 0.45045045… = x/37 trong ssg-gates.json).

---

## 3. Giả thuyết (i) — THAM LAM SỚM: đường chi tích luỹ theo t

Trung bình cộng dồn `self.spent` (dự đoán ngay sau `choose()`, trước khi `runner.charge`
áp dụng — tức giá trị `self.spent` sẽ có sau bước này) tại mỗi t, trên **325 episode**
(mọi tổ hợp workflow × carrier tấn công × seed mà `runner.survives()` giữ lại ở Δ=4 —
xem mục "Đáng ngờ / giới hạn" bên dưới về việc đây là TOÀN BỘ episode được quét, không
chỉ episode "thắng" mà `policy_curve` chọn làm đại diện harm của mỗi workflow).

| t | B7U tĩnh | SSG-up (C bật) | SSG-up (C tắt/noC) | gap SSGup−B7U | gap noC−B7U |
|---|---|---|---|---|---|
| 0 | 0.073 | 0.074 | 0.074 | **+0.001** | +0.001 |
| 1 | 2.197 | 1.990 | 1.882 | **−0.207** | −0.315 |
| 2 | 4.958 | 5.268 | 5.168 | +0.310 | +0.210 |
| 3 | 7.838 | 8.352 | 8.195 | +0.515 | +0.358 |
| 4 | 10.703 | 11.647 | 11.571 | **+0.944 (đỉnh)** | +0.868 |
| 5 | 13.205 | 14.130 | 14.051 | +0.925 | +0.847 |
| 6 | 14.479 | 15.101 | 15.199 | +0.622 | +0.721 |
| 7 | 15.122 | 15.416 | 15.641 | **+0.294** | **+0.519** |

Tín hiệu dự đoán của giả thuyết (i), đọc đúng nghĩa đen trong brief, cần **CẢ HAI**:
(a) đường lùi nằm TRÊN đường tĩnh **ngay từ đầu ván** (t=0, t=1), và (b) đường lùi tụt
XUỐNG DƯỚI đường tĩnh ở cuối ván (cạn tiền, bỏ trống cửa sổ muộn).

- (a) **KHÔNG xảy ra**: gap(t=0) = +0.001 (≈0), gap(t=1) = **−0.207** (SSG-up tiêu ÍT
  HƠN tĩnh ở task 1, không phải nhiều hơn).
- (b) **KHÔNG xảy ra**: gap(t=7, task cuối) = **+0.294**, vẫn DƯƠNG. SSG-up không hề bị
  starve — nó tiêu nhiều hơn tĩnh cho đến tận task cuối cùng. Không có dấu vết "cạn tiền
  trước khi cửa sổ muộn mở".
- Điều thật sự xảy ra: gap dương LỚN NHẤT rơi vào **GIỮA ván (t=4, +0.944)**, không phải
  đầu ván. Đây là "quá chi ở giữa-cuối ván trải dài", khác hẳn hình dạng "dồn đầu rồi
  starve" mà giả thuyết (i) mô tả.

### Kết luận giả thuyết (i): **BỊ BÁC BỎ** (đúng nghĩa đen)

Cơ chế thật không phải "thấy ngân sách đầy cho chân trời ngắn dần nên dồn audit đầu ván".
Nó là một dạng quá-chi lan toả suốt phần giữa-cuối ván (t=2..7), không giảm cường độ khi
gần hết ngân sách. Đây LÀ nguyên nhân khiến `spent` tổng của lùi cao hơn tĩnh
(15.407 > 15.024, đúng số trong brief), nhưng KHÔNG phải qua cơ chế "tham lam sớm" mà
brief nêu.

---

## 4. Giả thuyết (ii)(a) — C có được điền không

Trên **325 episode** của `DIAG SSG-up instrumented`, `self._done` (đọc ngay sau mỗi
`choose()`):

| t | |_done| trung bình | Σ_done.values() trung bình |
|---|---|---|
| 0 | 0.369 | 0.369 |
| 1 | 4.369 | 4.369 |
| 2 | 6.071 | 6.108 |
| 3 | 8.188 | 8.397 |
| 4 | 9.849 | 10.228 |
| 5 | 11.511 | 11.975 |
| 6 | 11.548 | 12.012 |
| 7 | 11.548 | 12.012 |

`n_episodes_done_nonempty_ever = 325 / 325` — **`_done` được điền trong 100% ván**, tăng
đơn điệu theo t (khớp `_log_audit` cộng dồn key `(k,i,s)` mỗi lần audit thật xảy ra), và
KHÔNG rỗng suốt ván ở bất kỳ episode nào.

### Kết luận giả thuyết (ii)(a) ("C rỗng suốt ván"): **BỊ BÁC BỎ**

`done=getattr(self, "_done", None)` ở policies.py dòng 439 và `_log_audit` ở dòng 457
hoạt động đúng như đọc code: C được truyền, và C có nội dung. Nhánh phụ "C bị bỏ" trong
giả thuyết (ii) là sai — đúng như phỏng đoán ban đầu (đã đọc code) trong brief, giờ có số
đo xác nhận.

---

## 5. Giả thuyết (ii)(b) — bật/tắt C có đổi harm không

So `DIAG SSG-up instrumented` (C bật, như hiện tại) với `DIAG SSG-up noC` (C ép `done=None`
tại MỌI bước, cùng dòng rng — xem mục 1.2):

| | harm | spent |
|---|---|---|
| B7U tĩnh (mốc so sánh) | 0.450450 | 15.024324 |
| SSG-up, C bật (hiện tại) | 0.572072 | 15.407207 |
| SSG-up, C tắt (`done=None`) | 0.545045 | 15.621171 |
| **Δharm (C tắt − C bật)** | **−0.027027** | |
| **Δspent (C tắt − C bật)** | **+0.213964** | |

Khoảng cách hồi quy so với tĩnh: `0.572072 − 0.450450 = +0.121622` (khớp đúng brief:
+0.1216).
Khoảng cách khi tắt C: `0.545045 − 0.450450 = +0.094595`.
**Tỉ lệ khoảng cách hồi quy mà việc tắt C xoá được: `0.027027 / 0.121622 = 22.2%`.**

Diễn giải: tắt C làm chính sách tiêu **NHIỀU HƠN** (15.621 > 15.407) nhưng harm lại
**THẤP HƠN** (0.545 < 0.572). Đây là phản trực giác: nếu C chỉ đơn thuần "làm cho LP nghĩ
ngân sách còn nhiều hơn thực" (dẫn tới quá-chi), tắt C (an toàn, không tín dụng gì) phải
làm chính sách tiêu ÍT HƠN. Số đo cho thấy ngược lại — tắt C làm LP tiêu **nhiều hơn nữa**
mà vẫn hiệu quả hơn (harm thấp hơn) trên mỗi đồng tiêu. Điều này gợi ý C không "bị bỏ" (đã
bác bỏ ở mục 4) mà **tín dụng SAI chỗ**: một số audit đã làm được `_done` ghi nhận là "đã
phủ cửa sổ (k,i,s)" khiến LP giảm yêu cầu phủ trong tương lai cho đúng cửa sổ đó, nhưng
LP sau đó dùng phần ngân sách "tiết kiệm được" để phủ CHỖ KHÁC kém hiệu quả hơn so với khi
nó cứ phủ lại toàn bộ một cách "ngu" (noC). Đây là suy luận về CƠ CHẾ, không phải số đo
trực tiếp — được gắn nhãn rõ là suy luận, không phải kết luận đo được.

Kiểm tra chéo bằng đường chi theo t (bảng mục 3, hai cột cuối): đường noC vẫn có hình dạng
"phồng giữa ván, không starve cuối ván" giống hệt đường C-bật — thậm chí gap ở t=7 CÒN LỚN
HƠN (+0.519 so với +0.294). Nghĩa là cái "phồng giữa-cuối ván" không đến từ C — nó tồn tại
y hệt (và mạnh hơn) khi C bị tắt hoàn toàn.

### Kết luận giả thuyết (ii)(b): **CÓ HIỆU ỨNG THẬT, NHƯNG CHỈ MỘT PHẦN**

Bật/tắt C **CÓ** đổi harm (−0.027, không phải nhiễu — cùng dòng rng, chỉ khác `done`), nên
nhánh "C SAI" của giả thuyết (ii) (đọc là "C hoạt động sai hướng" thay vì "C bị bỏ") là
**ĐÚNG MỘT PHẦN, ĐO ĐƯỢC**: C, như đang cài, đang làm harm tệ hơn 0.027 so với việc không
dùng nó — tức 22.2% khoảng cách hồi quy. Nhưng **77.8% khoảng cách hồi quy còn lại
KHÔNG biến mất khi tắt C** (0.545 vẫn cách tĩnh 0.095, không về 0.450) — phần này thuộc về
một cơ chế khác (nhiều khả năng là bản thân việc giải lại LP mỗi task, xem mục 3 — "phồng
giữa ván" tồn tại độc lập với C), **CHƯA được phân định trong phạm vi task này**.

---

## 6. Bảng tổng hợp bốn giả thuyết

| Giả thuyết | Đọc đúng nghĩa đen | Phán quyết | Căn cứ số |
|---|---|---|---|
| (i) Tham lam sớm | dồn đầu ván VÀ cạn tiền cuối ván | **BỊ BÁC BỎ** | gap(t=0)=+0.001, gap(t=1)=−0.207 (không dồn đầu); gap(t=7)=+0.294>0 (không cạn tiền, không bỏ trống cửa sổ muộn) |
| (ii)(a) C rỗng suốt ván | `_done` không bao giờ được điền | **BỊ BÁC BỎ** | 325/325 episode có `_done` không rỗng; Σ_done tăng đơn điệu 0.37→12.01 theo t |
| (ii)(b) C sai hướng | bật/tắt C đổi harm | **ĐÚNG, ĐO ĐƯỢC, MỘT PHẦN** | Δharm(tắt C) = −0.027 = 22.2% của khoảng cách hồi quy +0.1216 |
| (còn lại) cơ chế thứ ba chưa đặt tên trong brief | quá-chi lan toả t=2..7, đỉnh giữa ván, tồn tại cả khi tắt C | **CHƯA PHÂN ĐỊNH — CẦN TASK RIÊNG** | 77.8% khoảng cách hồi quy còn lại sau khi tắt C; hình dạng đường chi noC giống hệt (thậm chí nặng hơn ở đuôi) đường chi C-bật |

---

## 7. Đáng ngờ / giới hạn của phép đo này

1. **TRACE gộp mọi episode được quét, không chỉ episode "thắng".** `policy_curve` chọn,
   với MỖI workflow, carrier tấn công cho harm trung bình (qua 3 seed) CAO NHẤT làm đại
   diện cho harm được báo cáo của workflow đó. `DiagB7U.TRACE`/`DiagSSGUp.TRACE` ghi lại
   TẤT CẢ 325 episode được quét (mọi carrier, mọi seed), không lọc theo "ai thắng". Bảng
   chi-theo-t ở mục 3 vì vậy là trung bình trên một tập RỘNG HƠN tập 37 episode "thắng"
   nuôi số harm/spent cuối cùng. Đã kiểm tra: spend tại t=7 trong bảng chi-theo-t
   (15.122 tĩnh / 15.416 lùi) khớp RẤT GẦN với `spent` chính thức từ `measure_cell`
   (15.024 / 15.407) — sai lệch < 1% — nên hình dạng đường cong (không starve cuối ván,
   đỉnh giữa ván) đáng tin, nhưng các con số TUYỆT ĐỐI trong bảng mục 3 không phải là
   trung bình trên đúng 37 episode "thắng" mà `ssg-gates.json` báo cáo.
2. **`spent_after` trong log là GIÁ TRỊ SẼ CÓ, không phải giá trị đọc trực tiếp từ
   `pol.charge`.** Script tính `self.spent + P.cost_of(act)` ngay trong `choose()`, dựa
   trên việc đọc `runner.run_once` (dòng 396-397: `pol.charge(P.cost_of(act))` gọi NGAY
   SAU `pol.choose()` trả về, không có bước nào xen giữa). Đây là suy ra từ đọc code, đã
   đối chiếu tổng cuối cùng (t=7) khớp `measure_cell` nên tin được, nhưng không phải một
   phép đo trực tiếp trường `self.spent` sau khi `charge` thật sự chạy.
3. **Diễn giải cơ chế ở mục 5 (tín dụng sai chỗ) là suy luận, chưa đo trực tiếp.** Số đo
   xác nhận: tắt C → tiêu nhiều hơn + harm thấp hơn. Số đo KHÔNG trực tiếp cho biết CHỖ
   NÀO trong `solve_remaining_lp` phân bổ sai — cần một task riêng đọc `u[k][j]`/`v[j]`
   per-carrier để xác nhận, ngoài phạm vi task này.
4. **77.8% phần dư chưa được cắt nghĩa** — đây là kết quả thật của việc phân định trung
   thực (đúng yêu cầu brief "không kết luận theo loại trừ"), không phải một lỗ hổng của
   phép đo: cả hai giả thuyết trong brief đã bị bác bỏ hoặc chỉ giải thích một phần, và
   báo cáo này KHÔNG gán phần dư đó cho bất kỳ cơ chế nào chưa đo trực tiếp.
5. **Thời gian chạy 21.5s** cho toàn bộ script (40 workflow × 3 seed × 5 policy, trong đó
   3 policy là LP receding/static giải simplex nhiều lần) — không phải vấn đề về hiệu
   năng, chỉ ghi lại để tái tạo.
