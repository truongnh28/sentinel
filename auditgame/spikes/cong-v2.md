# cong-v2 — Cổng 2 phiên bản 2: bịt ba lỗ trong MỘT lần, rồi đóng băng

Ngày: 2026-09-18. Nguồn: `core.Item.surface`, `analysis/benign_corpus.py`
(`_one_event`), `build.inject`, `reference/gate2_v2.json`,
`tests/gate2_validity/test_gate2_v2_definition.py`.

**Việc này KHÔNG rút bất kỳ phán quyết chứng nhận nào về bất kỳ kẻ tấn công nào.**
Chạy bảng chứng nhận là **bước riêng**, cố ý tách ra (luật §II.3: bịt hết ba lỗ
cùng lúc → đóng băng định nghĩa kèm ngày và md5 → **sau đó** mới chạy bảng **một
lần**). Trang này ghi cái đã bịt, cách chọn `L`, bản ghi đóng băng, và **mọi** con
số đã xê dịch, kèm lệnh tái lập.

---

## 0. Chọn $L$

> **RÚT LẠI MỘT KHẲNG ĐỊNH (rà soát II, phán quyết 4).** Bản trước của mục này
> viết rằng phần này "được viết và **commit trước** khi bất kỳ số AUC v2 nào được
> đo". **Khẳng định đó không có bằng chứng và được rút.** Reflog của nhánh
> `gate2-v2` chỉ có **một** commit cho toàn bộ việc đó, **31 giây** sau khi
> checkout — tức không hề có một commit tiền-đăng-ký đứng trước phép đo. Cái
> **đúng** và **giữ nguyên** là bản thân phép dẫn: $L$ = **trung vị** của
> `len(content)` trên 2294 item `memory` lành của `benign_pool()` (pool `full`,
> `natural=False`, seed 20260916), phân bố ghi đủ dưới đây, lệnh tái lập kèm
> theo, và trung vị là gợi ý của chính đề bài — nên số bậc tự do là **nhỏ**.
> Nhưng "nhỏ" không phải "đã tiền-đăng-ký", và trang này không được nói như thể
> hai thứ đó là một. Xem §0bis cho một tiền-đăng-ký **thật sự có thứ tự trong
> git**.

Chọn $L$ **sau** khi thấy khả năng tách sẽ là chọn tham số theo kết quả — đó là
khuyết tật mà kỷ luật tiền-đăng-ký của dự án tồn tại để chặn. Dưới đây là phép
dẫn và phân bố đo được, **không kèm** khẳng định về thứ tự.

**Tổng thể lành được đọc:** `benign_pool()` mặc định — pool `full`, carrier
`memory`, `natural=False`, `seed = 20260916`. Đây là **đúng** tổng thể mà lớp âm
của corpus chứng nhận cổng 2 được rút ra (`matched_corpus(..., natural=False)`),
và nó **không** phụ thuộc vào hạt giống của `_one_event` nên **không** bị lỗ P8
làm xê dịch — chọn pool thay vì các hàng corpus là để `L` đứng độc lập với chính
bản sửa này.

Lệnh:

```bash
cd HCMUT/code/Sentinel/auditgame
python3 - <<'PY'
import statistics, collections, sys; sys.path.insert(0, ".")
from analysis import benign_corpus as B
for nat in (False, True):
    pool = B.benign_pool(natural=nat)
    lens = sorted(len(it.content) for (r, c), items in pool.items()
                  if c == B.CARRIER for it in items)
    q = statistics.quantiles(lens, n=4)
    print(nat, len(lens), lens[0], q[0], statistics.median(lens), q[2], lens[-1],
          round(statistics.fmean(lens), 4), collections.Counter(lens).most_common(3))
PY
```

| nền | $n$ | min | Q1 | **trung vị** | Q3 | max | trung bình | mode |
|---|---|---|---|---|---|---|---|---|
| `natural=False` (nền cổng 2 chứng nhận) | 2294 | 42 | 56 | **63** | 72 | 549 | 69,4856 | 62 (116), 56 (104), 55 (97) |
| `natural=True` (nền trung thực) | 3349 | 42 | 59 | **66** | 78 | 557 | 72,7719 | 62 (138), 63 (133), 64 (121) |

**CHỐT: $L = 63$** — **trung vị** của `len(content)` trên nền `natural=False`.

Ba lý do, ghi thành lời trước khi có số:

1. **Trung vị, không phải trung bình.** Phân bố lệch phải mạnh (mean 69,49 >
   median 63, max 549 so với Q3 72): trung bình bị cái đuôi dài kéo đi, trung vị
   thì không. Đề bài cũng nói trung vị là lựa chọn tự nhiên.
2. **Vì sao trung vị lại là điểm đúng cho một hằng số.** Bộ phân biệt là hồi quy
   **logistic**, tức **đơn điệu theo từng đặc trưng**. Một lớp dương **hằng** ở
   giữa một lớp âm **trải** thì với trọng số dương nó bị xếp dưới nửa trên của lớp
   âm, với trọng số âm nó bị xếp dưới nửa dưới — nên đóng góp của `size` vào AUC
   tiến về 0,5 **chỉ khi** hằng số đó nằm ở **trung vị**. Đặt $L$ ở trung bình hay
   ở mode đều lệch khỏi điểm cân bằng đó. Đây là lý do cấu tạo, không phải thẩm mỹ.
3. **Vì sao nền `natural=False`.** Corpus mà cổng 2 **chứng nhận** hôm nay là
   `natural=False` (xem `tests/gate2_validity/test_benign_corpus.py`). Chọn $L$
   theo nền trung thực (66) sẽ là chọn theo một tổng thể mà tiêu chí không đọc.
   Chênh lệch giữa hai nền là **3 ký tự**, được ghi ở đây để ai muốn đổi nền
   chứng nhận biết phải dời $L$ bao nhiêu — và việc dời đó phải là một sửa đổi
   **thấy được** của bản ghi đóng băng, không phải một thay đổi thầm lặng.

**Giới hạn của $L$ cố định, đo được và khai thẳng.** Tiền tố nhãn `[{topic}] ` mà
payload buộc phải mang không phải lúc nào cũng lọt vào 63 ký tự. Đo trên chính
các sigma khả thi của corpus:

```bash
python3 - <<'PY'
import statistics, sys; sys.path.insert(0, ".")
import retrieval
from analysis import benign_corpus as B
for delta in (0, 2, 4):
    _ds, wfs = B.hosting_workflows(delta)
    for eps in (0.0, 1.0):
        pre = sorted(len(f"[{retrieval.payload_topic_like(wf.tasks[s].topic, eps)}] ")
                     for wf in wfs for s in B.feasible_sigmas(wf, delta, eps))
        q = statistics.quantiles(pre, n=4)
        print(delta, eps, len(pre), pre[0], q[0], statistics.median(pre), q[2], pre[-1])
PY
```

| Δ | ε | n | min | Q1 | trung vị | Q3 | max |
|---|---|---|---|---|---|---|---|
| 0 | 0,0 | 2248 | 4 | 7 | 10 | 11 | 32 |
| 0 | 1,0 | 2248 | 13 | 24 | 30 | 39 | **506** |
| 2 | 0,0 | 826 | 4 | 7 | 10 | 11 | 25 |
| 2 | 1,0 | 504 | 13 | 25 | 31 | 40 | **298** |
| 4 | 0,0 | 456 | 4 | 7 | 10 | 11 | 26 |
| 4 | 1,0 | 202 | 16 | 27 | 33 | 47 | **451** |

Ở ε = 0 tiền tố **luôn** lọt (max 32 < 63). Ở ε = 1 cái đuôi **không** lọt. Đây là
đúng dạng bậc thang mà `MO-HINH-EPSILON-BA-CHIEU.md` §4(a) dự báo: khi
$L_{\text{advice}} = L - L_{\text{topic}}(k)$ tụt xuống 0, lời khuyên biến mất và
hại sập về 0. Nó được **ghi thành lý do** (luật N3), không bị bịt bằng cách nới
$L$: `build.payload_length_reason(topic)` trả về lý do, và `provenance` **giữ
nguyên** — `provenance` là một đặc trưng **được chấm** (`depth`), nhét lý do vào
đó là bơm tín hiệu vào chính thứ đang đo.

---

## 0bis. TIỀN ĐĂNG KÝ cho lần đo lại (rà soát II) — commit RIÊNG, TRƯỚC khi đo

**Trang này được commit một mình, không kèm một dòng code nào, không kèm một con
số mới nào.** Thứ tự phải **nhìn thấy được trong git**, không phải được khẳng
định bằng văn xuôi — đó chính là phán quyết 4 của đợt rà soát II, và là thứ lần
trước đã **không** làm.

### 0bis.1 Vì sao phải đo lại: `sorted()` là ARTEFACT CÀI ĐẶT, không phải mô hình

`retrieval.payload_topic` trả về `Topic(sorted(target)[:k])` — $k$ token **nhỏ
nhất theo từ điển**. `core.topic_code` (bản v2 đã giao) là **trung bình mã từ
điển** của các token. Với $A = \text{sorted}(B)[:k] \subseteq B$:

$$\operatorname{mean}_{t \in A} \operatorname{code}(t) \;\le\; \operatorname{mean}_{t \in B} \operatorname{code}(t)$$

là một **định lý**, không phải một phép đo: trung bình của $k$ phần tử nhỏ nhất
không bao giờ vượt trung bình của cả tập. Nên hai lớp tách nhau **theo cấu tạo**,
và ô đỏ ở §4.1 đang đo `sorted()` chứ không đo `MatchedAttack`.

Bằng chứng quyết định rằng `sorted()` **không** phải tiếng nói của mô hình tấn
công, mà là một lựa chọn cài đặt:

* docstring của chính `payload_topic` chọn thứ tự sắp xếp **vì TẤT ĐỊNH**:
  *"taken in SORTED order: deterministic, no sampling"*. Lý do là tái lập, không
  phải là mô hình.
* mô hình tấn công chỉ đòi payload mang một **TẬP CON** của topic task sigma
  (để $\operatorname{sim}(A,B) = |A|/|B| \approx \varepsilon$, không làm phồng
  mẫu số Jaccard). Nó **không** đòi tập con đó phải là tiền tố bảng chữ cái.

### 0bis.2 Quy tắc tập con ĐÃ KHỬ THIÊN LỆCH — chốt ở đây, trước khi đo

Thay `sorted(target)[:k]` bằng một **tập con $k$ phần tử giả ngẫu nhiên tất
định**, gieo qua `core.seed_of` (blake2b, **không** `hash()`):

```python
k = max(1, ceil(eps * len(target)))
order = sorted(target, key=lambda t: (seed_of("payload_topic", str(target), t), t))
A = Topic(order[:k])
```

Mọi tính chất mà **mô hình** và **docstring** đòi đều giữ nguyên, và đây là toàn
bộ danh sách:

| tính chất | giữ? | vì sao |
|---|---|---|
| $A \subseteq B$ | có | lấy từ chính `target` |
| $\lvert A\rvert = k$ | có | cùng công thức $k$ |
| $\operatorname{sim}(A,B) = k/m$ | có | $A$ là tập con nên Jaccard $= \lvert A\rvert/\lvert B\rvert$ |
| đơn điệu theo $\varepsilon$ | có | thứ tự ưu tiên **cố định** cho mỗi `target` → các $A$ **lồng nhau** |
| tất định qua tiến trình | có | `seed_of` = blake2b trên chuỗi; `str(target)` là dạng chuẩn `"\|".join(sorted(...))` |
| không `hash()`, không thứ tự duyệt `frozenset` | có | như trên |
| không token lạ | có | tập con |

Cái **mất đi** là đúng thứ phải mất: mối tương quan giữa "được chọn vào tag" và
"đứng đầu bảng chữ cái". Sau khi khử, bất kỳ khả năng tách nào còn lại trên cột
`topic` là **đo được**, không phải **suy ra được**.

Quy tắc mới chảy qua **một** chỗ (`retrieval.payload_topic`), nên nó tự động
chảy vào `retrieval.payload_topic_like`, `build.inject`, `build.plan_poison`,
`attacks.*.payload`, `analysis/benign_corpus.py::feasible_sigmas` và
`tests/gate2_validity/test_matched_epsilon_budget.py`. Đó là điều kiện để cổng
không còn vừa **bắt buộc** một chữ ký vừa **chấm điểm** chính chữ ký đó.

### 0bis.3 Đặc trưng `topic` — CHỐT trên LÝ DO ĐÃ KHAI, trước khi thấy bảng

> **LỰA CHỌN Ở MỤC NÀY ĐÃ BỊ §0bis.4b THAY THẾ.** Mục này giữ nguyên, không sửa
> một chữ, vì nó là **cái đã được tiền-đăng-ký** và một bản tiền-đăng-ký bị viết
> lại sau khi thấy số thì không còn là tiền-đăng-ký. Bốn ứng viên, định nghĩa
> $\operatorname{code}_8$, và **nghĩa vụ trung thực ở §0bis.4 vẫn còn hiệu lực
> nguyên vẹn**. Cái đổi là **ứng viên được chọn**: `canonical` → `mean`, vì
> `canonical` vi phạm chính tiêu chí loại mà §0bis.1 đã khai. Lý do, bảng đếm
> không-AUC, và phần khai báo đầy đủ về thứ tự: **§0bis.4b**.


Có nhiều mã từ điển đều "hợp lệ" cho một tập token. **Bốn** ứng viên được khai ở
đây, và cả bốn sẽ được đo và **công bố cạnh nhau** ở §3.7 để không ai phải tin
lựa chọn này trên lời:

| tên | định nghĩa | ghi chú |
|---|---|---|
| **`canonical`** | $\operatorname{code}_8\big(\texttt{"\|".join(sorted(tokens))}\big)$ | **ĐƯỢC CHỌN** |
| `mean` | $\frac{1}{\lvert T\rvert}\sum_t \operatorname{code}_8(t)$ | bản đã giao ở v2 |
| `max` | $\max_t \operatorname{code}_8(t)$ | |
| `sum` | $\sum_t \operatorname{code}_8(t)$ | |

với $\operatorname{code}_8(s) = \operatorname{int}_{256}(\operatorname{utf8}(s)_{[0:8]}) / 2^{64}$ —
**đúng** nguyên hàm byte→phân số mà `TOPIC_CODE_BYTES = 8` đã có, không đổi.

**LÝ DO CHỌN `canonical`, và lý do này độc lập với mọi AUC:** chuỗi
`"|".join(sorted(tokens))` là dạng mà **chính codebase này đã coi là CĂN CƯỚC của
một topic** — không phải một dạng mới nghĩ ra cho cổng 2:

* `retrieval.Topic.__str__` **là** chuỗi đó, và `__repr__ = __str__`;
* `core.seed_of` **chuỗi hoá** đối số của nó (`"|".join(map(str, parts))`), nên
  cái nó thực sự băm chính là chuỗi chuẩn này;
* `core.Item.__post_init__` băm `seed_of(carrier, topic, content, …)` thành
  `item_id`, và `detector.score` gieo trên `item_id` — nên **điểm số của cả
  benchmark** đã phụ thuộc vào đúng chuỗi này từ trước việc này rất lâu;
* `core.item_from_record` và docstring của `swebench_dataset.Topic` đều nêu đích
  danh dạng đó là lý do tồn tại của lớp `Topic`.

Nói cách khác: **đặc trưng đọc đúng cái mà hệ thống vốn đã dùng làm định danh
topic.** Ba ứng viên kia là các bản tóm tắt được **phát minh ở cổng 2**; không
chỗ nào khác trong repo coi trung bình / max / tổng mã token là căn cước của một
topic.

**GIỚI HẠN, khai thẳng ngay tại đây chứ không đợi bảng:** cửa sổ 8 byte làm
`canonical` đọc **xấp xỉ token đứng đầu bảng chữ cái** (cộng vài byte kế). Vì vậy
nó **gần như không nhạy** với việc một tập con bỏ đi token nào **sau** ký tự thứ
~8. Đó vừa là lý do nó ổn định trước phép cắt tập con, vừa là một **phép chiếu
rất mất mát**. 8 byte là con số `TOPIC_CODE_BYTES` đã có và có lý do riêng của
nó (mantissa `float` 53 bit — quá 6–7 byte thì bit thấp bị làm tròn mất), nên
đọc nhiều byte hơn **không** mua thêm gì; giới hạn này là **nội tại** của việc ép
một chuỗi thành **một** số thực.

### 0bis.4 NGHĨA VỤ TRUNG THỰC (rà soát II, phán quyết 2b) — viết TRƯỚC khi đo

Phải nói thẳng ba câu sau, và chúng được viết ở đây, **trước** commit đo:

1. **Đặc trưng được chọn `canonical` được kỳ vọng là đặc trưng khiến ô đỏ chuyển
   xanh.** Người rà soát đã đo bốn ứng viên trải AUC 0,45–1,00 và đã nêu tên
   `canonical` trong chỉ thị. Nên **không** có chuyện giả vờ rằng lựa chọn này
   được làm mù.
2. **Lý do chọn không phải là kết quả đó.** Lý do — "đây là dạng chuẩn mà
   `seed_of` / `item_id` / `Topic.__str__` **đã** dùng làm căn cước" — là một sự
   kiện **kiểm tra được trong code**, có từ trước việc này, và có thể bác bỏ
   được: nếu `Topic.__str__` không phải dạng đó, lý do sụp.
3. **Nhưng thứ tự của chính việc CHỌN thì không được tiền-đăng-ký.** Cái commit
   này ghim là thứ tự của **phép đo** (chốt quy tắc + đặc trưng → rồi mới đo),
   **không** phải thứ tự của việc chọn giữa các lý do — việc chọn đó do người rà
   soát làm **khi đã cầm bảng bốn ứng viên trên tay**. Cách duy nhất làm điều đó
   kiểm tra được là **công bố cả bốn số** (§3.7) để người đọc tự thấy độ nhạy.
   Trang này không được nói mạnh hơn thế.

### 0bis.4b SỬA ĐỔI TIỀN ĐĂNG KÝ — `canonical` bị CHÍNH tiêu chí ở §0bis.1 loại

**Đây là một sửa đổi của bản tiền-đăng-ký, và nó được commit RIÊNG, trước lần đo
cuối.** Khai thẳng và ngay dòng đầu: **khi viết mục này, bảng AUC bốn ứng viên ở
pha sàng ĐÃ được đo và đã được nhìn thấy.** Không có cách nào nói khác đi. Cái
mục này làm được, và chỉ làm được, là đưa ra một **lý do không dùng đến AUC** cho
việc đổi lựa chọn, đặt nó thành một số **đếm được**, và để bảng AUC nằm cạnh
(§3.7) cho người đọc tự đối chiếu.

**Vấn đề.** §0bis.1 phát biểu tiêu chí loại: một đặc trưng mà hai lớp tách nhau
**theo định lý** thì đo `sorted()` chứ không đo kẻ tấn công. Áp đúng tiêu chí đó
lên **bốn** ứng viên — chứ không chỉ lên ứng viên `mean` của bản v2 — thì ba
trong bốn **rụng**, và `canonical` là một trong ba:

| ứng viên | quan hệ với $A \subseteq B$ | có phải định lý? |
|---|---|---|
| `max` | $\max(A) \le \max(B)$ — thống kê thứ tự | **CÓ**, một chiều tuyệt đối |
| `sum` | $\sum_A \le \sum_B$, **lại còn quảng tính** theo $\lvert A\rvert$ | **CÓ**, và trùng `size` |
| `canonical` | chuỗi chuẩn mở đầu bằng $\min(\cdot)$, mà $\min(A) \ge \min(B)$ | **CÓ**, lệch **lên** |
| `mean` | $\mathbb{E}[\operatorname{mean}(A)] = \operatorname{mean}(B)$ với $A$ là tập con **đều** | **KHÔNG** — **không thiên lệch** |

`canonical` không thoát: nó chỉ **đổi chiều** bất đẳng thức, không bỏ nó. Chuỗi
`"|".join(sorted(A))` mở đầu bằng token **nhỏ nhất** của $A$, và bỏ bớt token chỉ
có thể làm token nhỏ nhất **lớn lên** — nên payload bị đẩy **lên** một cách hệ
thống, đúng như `sorted()[:k]` đẩy `mean` **xuống** một cách hệ thống.

**Đo trực tiếp, KHÔNG có bộ phân biệt, KHÔNG có corpus, KHÔNG có AUC.** Trên
đúng 2248 topic task sigma khả thi ở Δ=0, thay topic bằng chính tập con mà quy
tắc đã khử thiên lệch stamp lên payload ($\varepsilon = 0$, $k = 1$), rồi **đếm**
xem mã dịch lên hay dịch xuống (lệnh đầy đủ ở §6.1, dòng "độ dịch tập con"):

| ứng viên | trung bình mã của **topic nguyên** | của **tập con** | **độ dịch** | tập con **cao hơn** | **thấp hơn** | bằng |
|---|---|---|---|---|---|---|
| `canonical` | 0,3903 | 0,4168 | **+0,0265** | **1640** | 293 | 315 |
| `max` | 0,4469 | 0,4168 | **−0,0301** | **0** | **1669** | 579 |
| `sum` | 1,8387 | 0,4168 | **−1,4219** | **0** | **2248** | 0 |
| `mean` | 0,4170 | 0,4168 | **−0,0002** | 1091 | 1157 | 0 |

`max` và `sum` **một chiều tuyệt đối** (0 ngoại lệ trên 2248). `canonical` lệch
lên ở **1640/2248**. `mean` **cân**: 1091 lên, 1157 xuống, độ dịch $-2 \times
10^{-4}$ — đúng bằng không trong sai số của một tổng thể 2248 phần tử.

**Quyết định của bản sửa đổi: giữ `mean`, tức đúng đặc trưng đã giao ở v2.** Lý
do — *"ứng viên duy nhất trong bốn cái mà kỳ vọng KHÔNG bị dịch bởi phép lấy tập
con, tức ứng viên duy nhất không tái tạo lại Phát hiện 1 dưới một lớp áo khác"* —
là một tính chất **toán học**, phát biểu và kiểm tra được **không cần một số AUC
nào**, và bảng đếm ở trên là bản đo của chính nó.

**Hệ quả cho việc đối chiếu với chỉ thị rà soát II.** Chỉ thị đó chốt `canonical`
**vì cho rằng nó là cái sẽ qua cổng**. Đo được: **không**. Ở pha sàng,
`canonical` cho 0,7806 / 0,7456 / 0,7572 (Δ = 0/2/4, ε = 0) — **trên** trần 0,56
ở mọi Δ — trong khi `mean` cho 0,4952 / 0,4643 / 0,4770. Nên **câu mà phán quyết
2(b) yêu cầu viết ("đặc trưng được chọn là đặc trưng VỪA HAY qua cổng") KHÔNG
viết được cho `canonical`**, vì tiền đề của nó sai; còn nếu viết cho `mean` thì
nó đúng — nhưng lý do chọn `mean` ở trên là **bảng đếm không-AUC**, không phải
cái kết quả đó. Cả hai vế đều được công bố ở §3.7 để không ai phải tin trên lời.

**Cái bản sửa đổi này KHÔNG được phép nói.** Nó không được nói rằng lựa chọn
`mean` là **mù**. Nó không mù. Nó chỉ (a) đứng trên một lý do kiểm tra được
không dùng AUC, (b) là lý do **đã được khai ở §0bis.1** trước khi bất cứ gì được
đo trong đợt này, và (c) đi kèm **cả bốn con số**.

**`canonical`, `max`, `sum` được GIỮ LẠI làm code chạy được**
(`core.TOPIC_CODE_CANDIDATES`), chứ không bị xoá, để bảng §3.7 tái lập được và
để lần rà soát sau kiểm lại được bảng đếm này.

### 0bis.5 Những gì sẽ được GHIM thêm vào ô băm (phán quyết 5)

Bản ghi v1-của-v2 mới chỉ ghim `corpus(pool, carrier, h, corpus_seed)`. Các tham
số sau **cũng quyết định ô đỏ** mà chưa được ghim, nên **md5 sẽ đổi** — và đổi là
đúng:

* `natural` (một mình nó dịch ô **0,0421** — hơn cả biên mà tiêu chí đạt),
* `per_event`, `holdout`,
* `n_events` của **cả hai** pha (sàng 80 / chứng nhận 900),
* **tiêu chí PHA SÀNG** — thứ thực sự quyết định ô đỏ, trong khi bản ghi cũ chỉ
  ghim tiêu chí pha chứng nhận (`mean_ci95_upper_over_split_seeds`),
* lưới $\varepsilon$ và tập $\Delta$ mà tiêu chí sàng đọc trên đó,
* **tên đặc trưng `topic` đang dùng** (`topic_feature`), để việc đổi đặc trưng là
  một sửa đổi **thấy được** của digest,
* quy tắc độ dài payload **kèm ngoại lệ** của nó (phán quyết 3).

### 0bis.6 Sẽ đo gì, bằng lệnh nào — khai trước

1. Bảng **bốn đặc trưng** × {Δ=0,2,4} ở ε=0, pha sàng (80 sự kiện, trung vị điểm
   trên 20 split) **và** pha chứng nhận (900 sự kiện, cận trên CI trung bình) cho
   đặc trưng được chọn.
2. Toàn bộ lưới sàng ε × Δ cho đặc trưng được chọn, để phát biểu lại ô đỏ
   (phán quyết 6): **hàng ε nào đỏ, và đặc trưng nào gánh hàng đó** — đo bằng
   trung hoà từng cột một.
3. Ba cổng: `python3 tests/run_all.py`.

Trần 0,56 **không** bị đụng. Tiêu chí **không** bị đụng. Nếu sau khi khử thiên
lệch ô vẫn đỏ, **để đỏ** và gọi tên đặc trưng gánh nó.

---

## 1. Ba lỗ, và cái nào bịt bằng gì

| lỗ | cổng v1 lệch về | bịt bằng | ở đâu |
|---|---|---|---|
| `F_match` thiếu `topic` | **QUÁ LỎNG** (lợi cho ta) | `core.Item.surface()` mọc cột `topic` = `core.topic_code` | `core.py`, `analysis/discriminator.py` |
| P8: `_one_event` chạy **mọi** workflow ở `seed=1` | **QUÁ CHẶT** | rút hạt giống **theo workflow** qua `core.seed_of` | `analysis/benign_corpus.py::event_seed` |
| rò rỉ corpus lành | quá lỏng | **ĐÃ BỊT TỪ TRƯỚC** (`holdout`) — chỉ **kiểm lại** | `tests/gate2_validity/test_dist_matched_attack.py` |

Hai lỗ đầu lệch **ngược chiều nhau**, nên đúng như luật §II.3: bịt từng cái một
thì mỗi lần đo lại là một phán quyết về một cổng vẫn còn lệch. Bịt **cùng một
lần**.

Thêm (yêu cầu 3, từ `MO-HINH-EPSILON-BA-CHIEU.md` §5.1): `build.inject` dựng
`content` tới **độ dài cố định $L$**, nên `size` **thôi biến thiên theo ε** và
kênh `size` đóng **theo cấu tạo** chứ không phải nhờ thêm một đặc trưng.

### 1.1 `topic_code` — chọn gì, và giới hạn của nó

$$\mathrm{topic\_code}(T) \;=\; \frac{1}{|T|}\sum_{t \in T} \frac{\mathrm{int}_{256}\big(\mathrm{utf8}(t)_{[0:8]}\big)}{2^{64}}$$

Công thức **không đổi** so với bản v2. Cái đổi là nó nay là **một ứng viên được
GỌI TÊN** trong `core.TOPIC_CODE_CANDIDATES`, được **ghim** trong bản ghi
(`topic_feature = "mean"`), và **lý do chọn** đã khác hẳn — xem §0bis.4b.

**LÝ DO ĐÚNG (v2.1):** với $A$ là tập con $k$ phần tử lấy **đều** từ $B$,

$$\mathbb{E}\big[\operatorname{mean}_{t \in A} \operatorname{code}(t)\big] \;=\; \operatorname{mean}_{t \in B} \operatorname{code}(t)$$

— **không thiên lệch** dưới phép lấy tập con. Đây là tính chất **duy nhất** cần
thiết, vì khác biệt **cấu trúc** duy nhất giữa hai lớp là payload mang một **tập
con** còn ghi chú lành mang **nguyên** topic. Một đặc trưng bị phép lấy tập con
**dịch** thì tách hai lớp **theo cấu tạo**, và cổng đọc chính quy tắc dựng payload
của mình. Ba ứng viên kia đều bị dịch (§0bis.4b).

> **LÝ DO CŨ (v2) BỊ RÚT.** Bản trước biện minh cho `topic_code` bằng lập luận
> **THỨ TỰ**: *"mã theo thứ tự từ điển làm `payload_topic` (`sorted(target)[:k]`,
> cắt từ đầu bảng chữ cái) thấp điểm hơn topic nguyên mà nó bị cắt ra"*, kèm bảng
> "đo trên corpus Δ=0" cho AUC đơn cột 0,8523 và mean(pos) 0,3928 so với
> mean(neg) 0,4188. **Toàn bộ khối đó là một ĐỊNH LÝ được đọc nhầm thành một phép
> đo**: trung bình của $k$ phần tử **nhỏ nhất** không bao giờ vượt trung bình của
> cả tập. Cái "kiểm chứng rằng nó đọc đúng kênh, không phải lén đưa bộ đếm quay
> lại" cũng vô hiệu — nó loại được giả thuyết "bộ đếm", nhưng **không** loại được
> giả thuyết "`sorted()`", mà đó mới là giả thuyết đúng. Sau khi khử thiên lệch,
> cột này đọc **mức ngẫu nhiên** ở **mọi** ô (§3.5b).

**Thứ tự VẪN cần**, nhưng vì một lý do hẹp hơn: `discriminator` khớp **hồi quy
logistic**, đơn điệu theo từng cột, nên một vân tay **danh định** (blake2b) sẽ là
**nhiễu** với nó. Có thứ tự **không** giống với **bị phép lấy tập con làm lệch** —
và ba ứng viên bị loại chính là chỗ thấy rõ sự khác nhau đó.

**Giới hạn — khai thẳng, và đã viết trong docstring của `core.topic_code`:**

1. **MẤT MÁT.** Một tập bị thu về một trung bình → hai tập khác nhau vẫn có thể
   trùng mã. Đọc nhiều byte hơn **không** cứu được: quá 6–7 byte thì mantissa
   `float` làm tròn mất bit thấp. Cổng chứng nhận trên một **phép chiếu** của
   topic, không phải trên topic.
2. **KHÔNG THIÊN LỆCH ≠ MÙ.** Không thiên lệch nói lớp dương không bị **dịch** so
   với lớp âm; nó **không** nói gì về **phương sai**, mà lấy tập con thì **có**
   thổi phương sai. Hồi quy logistic đơn điệu theo cột không đọc được khác biệt
   thuần phương sai — nên cột đọc ~0,5 — nhưng một bộ phân biệt **phi tuyến** thì
   có thể, và cổng này **không** chứng nhận trước loại đó. Ô Δ=4 ở §4.1 là một
   trường hợp đo được của đúng giới hạn này.
3. **THỨ TỰ LÀ TỪ ĐIỂN, KHÔNG PHẢI NGỮ NGHĨA.** `zlib` và `zope` gần nhau ở cột
   này và chẳng liên quan gì nhau trong repo.
4. **KHÔNG DIỄN ĐẠT ĐƯỢC QUAN HỆ.** `surface()` nhìn **một** item, không có
   workflow quanh nó, nên quy tắc *"tag này là tập con THỰC SỰ của một topic task
   nào đó trong workflow nó đang nằm"* — đo được **0,9492** — **vẫn nằm ngoài**
   `F_match`, và v2 **không** thu hẹp được nó (§3.4).

### 1.2 P8 — hạt giống theo workflow

```python
EVENT_SEED_RULE = "seed_of(SEED, 'one_event', wf.wf_id) & 0xFFFF"
```

**Theo workflow, không theo sự kiện.** Một workflow là **một** lần chạy của
**một** agent qua H task; các sự kiện đọc ra từ nó là các cửa sổ `(iota, sigma)`
khác nhau **trên cùng lần chạy đó**. Cho mỗi cửa sổ một dòng ngẫu nhiên riêng
nghĩa là cùng một workflow được chạy bởi nhiều agent khác nhau cùng lúc.

### 1.3 Rò rỉ — CHỈ kiểm lại, không làm lại

`holdout = 1 - attacks.ESTIMATION_PARITY` vẫn cho **giao đúng bằng RỖNG** giữa
ước lượng của attacker và lớp âm **được chấm** (không chỉ pool nạp thêm). Khẳng
định `a_ids & c_ids == set()` **xanh trước và sau**. Chỉ **kích thước** lớp âm
xê dịch, vì P8 (xem §3.3).

---

## 2. Bản ghi đóng băng — `reference/gate2_v2.json`

Cùng kỷ luật `reference/score_table.json` và `metrics.config_sha`: các tham số
**phải cùng dịch** thì nằm trong **một ô băm**, và có test ghim digest.

**BẢN GHI ĐÃ MỞ RỘNG (phán quyết 5).** Bản v2 chỉ ghim
`corpus(pool, carrier, h, corpus_seed)` và tiêu chí **pha chứng nhận**. Nhưng ô
đỏ được quyết bởi **pha sàng**, chạy trước; và và việc chọn **nền lành nào** một mình
dời ô **0,0421** — hơn cả biên mà tiêu chí đạt. Hai người thoả cùng md5 vẫn có
thể báo cáo hai con số khác nhau.
Các trường **mới vào ô băm**:

| trường mới | vì sao nó quyết định ô |
|---|---|
| `corpus.natural` | chọn **nền lành nào** — một mình dời ô **0,0421** |
| `corpus.per_event` | là **hợp đồng** (`harvest` từ chối pool không cấp đủ) → quyết repo nào sống sót |
| `corpus.holdout` | chọn **parity segment** → quyết corpus có rò rỉ hay không |
| `n_events` (`screen` 80, `certify` 900) | hai cỡ mẫu của hai pha |
| `screen_criterion` | **thứ thực sự quyết ô đỏ**, trước đây không được ghim |
| `epsilon_grid`, `deltas` | *"không ε nào đạt trần"* là khẳng định về **một TẬP** ε |
| `topic_feature` | bốn mã từ điển hợp lệ trải AUC 0,45–1,00 → `"topic"` trong `features` **không** ghim được đặc trưng |
| `payload_length_rule` | ghim $L$ **kèm ngoại lệ** — `payload_length_L = 63` một mình đọc như *"size luôn bằng 63"*, mà 7,6% sự kiện ở ε=1 không thoả |

```json
{"ceiling":0.56,"corpus":{"carrier":"memory","corpus_seed":20260916,"h":8,"holdout":null,"natural":false,"per_event":4,"pool":"full"},"criterion":"mean_ci95_upper_over_split_seeds","date":"2026-09-18","deltas":[0,2,4],"epsilon_grid":[0.0,0.2,0.4,0.7,1.0],"event_seed_rule":"seed_of(SEED, 'one_event', wf.wf_id) & 0xFFFF","features":["depth","derived","recency","size","topic"],"n_events":{"certify":900,"screen":80},"payload_length_L":63,"payload_length_rule":"len(content) == payload_length_L exactly when len(payload_tag(topic)) < payload_length_L; otherwise the payload is the tag alone and build.payload_length_reason(topic) states why","screen_criterion":"median_point_estimate_over_split_seeds <= ceiling at EVERY delta; eps_star = max passing epsilon","split_seeds":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],"test_fraction":0.4,"theta":0.5,"topic_feature":"mean","verdict":"NOT DRAWN -- certification is a separate step","version":2}
```

$$\boxed{\texttt{md5} = \texttt{45274180520227436a90f03ca1dd21db}}$$

Digest **đã dịch** khỏi `d7e7124eb3a46dfe64d9f205850504d9` của bản v2 — **đúng
như phải thế**: các trường mới vào ô, và `topic_feature` đổi từ (ngầm) `mean`
thành (tường minh) `mean`.

Tái lập:

```bash
python3 -c "import sys; sys.path.insert(0,'.'); from analysis import gate2_v2; print(gate2_v2.md5())"
```

Ghim bởi `tests/gate2_validity/test_gate2_v2_definition.py::TheGateTwoV2DefinitionIsFrozen`,
gồm một test **nhiễu từng trường một** đòi digest phải dịch cho **17** phép
nhiễu (kể cả ba phép nhiễu riêng vào `corpus.natural`, `corpus.per_event`,
`corpus.holdout`) — một ô băm không phản ứng là một ô băm không phủ.

**Và tiêu chí được GHIM đúng là tiêu chí được CHẠY.**
`tests/gate2_validity/test_benign_corpus.py` **import** trần, hai cỡ mẫu, lưới ε
và tập Δ **từ `gate2_v2`** thay vì tự khai lại, và có một test khẳng định hai bên
bằng nhau. Trước đây chúng là hằng số chép tay trong file test — tức digest phủ
một tiêu chí, còn cổng chạy một tiêu chí khác.

**Bản ghi KHÔNG mang phán quyết.** Trường `verdict` nói thẳng điều đó và có một
test khẳng định trong bản ghi **không có chữ `auc` nào**.

```mermaid
flowchart LR
  A["bịt 3 lỗ<br/>(MỘT lần)"] --> B["đóng băng định nghĩa<br/>ngày + md5"]
  B --> C["chạy bảng chứng nhận<br/>MỘT lần"]
  C --> D["phán quyết"]
  A -.->|"việc NÀY dừng ở đây"| B
  style C fill:#eee,stroke-dasharray: 5 5
  style D fill:#eee,stroke-dasharray: 5 5
```

---

## 3. Mọi con số đã dịch — TRƯỚC → SAU

Lệnh chung cho §3.1–§3.2 (`ablate.py` trong scratchpad, nội dung in dưới đây):

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
import attacks
from analysis import benign_corpus as B, discriminator as D
pipe = attacks.REGISTRY["matched"]
neutral = lambda rows, col: [dict(r, **{col: 0.0}) for r in rows]
for natural in (False, True):
    for delta in (0, 2, 4):
        pos, neg = B.matched_corpus(pipe, delta, 0.0, 900, natural=natural)
        r = D.auc_over_splits(pos, neg, ceiling=0.56)
        cols = {c: D.auc_over_splits(neutral(pos, c), neutral(neg, c),
                                     ceiling=0.56)["hi_mean"] for c in sorted(D.F_MATCH)}
        print(natural, delta, len(pos), len(neg), round(r["hi_mean"], 4),
              f"{r['clear']}/{r['k']}", {k: round(v, 4) for k, v in cols.items()})
PY
```

### 3.1 Corpus CHỨNG NHẬN (`natural=False`, ε*=0) — cận trên CI **trung bình** trên 20 split

> **BẢNG NÀY ĐÃ ĐƯỢC ĐO LẠI TOÀN BỘ (rà soát II).** Cột "v2 (đã giao)" trong bản
> trước — 0,8805 / 0,9073 / 0,9373 — được đo **dưới quy tắc tập con
> `sorted()[:k]`**, tức dưới đúng artefact mà phán quyết 1 nói tới. Nó **không
> phải** một phép đo về `MatchedAttack` và không được trích dẫn như vậy. Ba con
> số đó **bị rút**, không phải bị sửa.

| Δ | v1 (4 đặc trưng) | v2 **đã giao**, `sorted()[:k]` — **ĐÃ RÚT** | **v2.1 khử thiên lệch (5 đặc trưng)** | điểm ước lượng | $n_{\text{pos}}$ |
|---|---|---|---|---|---|
| 0 | 0,5414 (19/20 đạt) | ~~0,8805 (0/20)~~ | **0,5190** (**20/20 đạt**) ✅ | 0,4860 | 900 (trần) |
| 2 | 0,5394 (17/20) | ~~0,9073 (0/20)~~ | **0,5292** (**20/20 đạt**) ✅ | 0,4945 | 817 |
| 4 | 0,5411 (18/20) | ~~0,9373 (0/20)~~ | **0,5870** (**1/20**) ❌ | 0,5394 | 449 |

**Đọc ba điều.**

1. **Khử thiên lệch quy tắc tập con đưa hai trong ba ô về DƯỚI trần, và đưa số
   split tự đạt lên 20/20** — cao hơn cả v1 (19/20 và 17/20). Cái v2 "phát hiện"
   ở Δ = 0 và Δ = 2 là `sorted()`, không phải kẻ tấn công.
2. **Ô Δ = 4 vẫn đỏ** (0,5870 so với trần 0,56), và nó được mổ xẻ riêng ở §4.1 —
   đó là kết quả **thật**, không phải artefact, và nó **không** giống cái ô đỏ
   mà bản trước công bố.
3. **Đặc trưng `topic` KHÔNG còn là phần dịch chuyển.** Bảng đơn cột ở §3.5b cho
   thấy nó nằm ở **mức ngẫu nhiên** (0,46–0,52) trên **mọi** hàng ε và **mọi** Δ.

### 3.2 Corpus PHỤ (`natural=True`, `holdout=None`, ε=0, 900 sự kiện)

| Δ | v1 tất cả (4) | v1 bỏ `depth` | v1 bỏ `size` | **v2 tất cả (5)** | v2 bỏ `topic` | v2 bỏ `depth` | v2 bỏ `size` |
|---|---|---|---|---|---|---|---|
| 0 | 0,7056 | 0,6128 | **0,7091** | **0,9226** | 0,6928 | 0,8825 | **0,9217** |
| 2 | 0,7328 | 0,6375 | **0,7305** | **0,9358** | 0,7038 | 0,9084 | **0,9350** |
| 4 | 0,7318 | 0,6400 | **0,7333** | **0,9572** | 0,7075 | 0,9380 | **0,9570** |

> **CÁC CỘT v2 Ở BẢNG TRÊN ĐƯỢC ĐO DƯỚI `sorted()[:k]` VÀ KHÔNG ĐƯỢC TRÍCH DẪN
> NHƯ MỘT PHÉP ĐO VỀ KẺ TẤN CÔNG.** Chúng được giữ lại vì **cột P8** (so sánh
> "v1 tất cả" với "v2 bỏ `topic`") vẫn đọc được: hai cột đó đều **không** chứa
> `topic`, nên chênh lệch giữa chúng là **P8**, không phải artefact. Nền
> `natural=True` **không** phải nền cổng chứng nhận (§3.1) và **không** được đo
> lại ở đợt này — đo lại nó là việc của bước chứng nhận, cùng với quyết định
> `natural` ở §3.5c.

Ở **đây** P8 dịch thật (và phần này ĐỨNG): cột "bỏ `topic`" (gần nhất với không
gian 4 cột cũ) đọc 0,6928 / 0,7038 / 0,7075 so với 0,7056 / 0,7328 / 0,7318.
Cơ chế: drift **bật**, mà drift là một **đồng xu** phụ thuộc hạt giống.

**Kết luận định tính của bản v2 — *"trục dẫn dắt là `topic`, −0,23 ở Δ=0"* —
BỊ RÚT.** Nó đo `sorted()`. Trên corpus **chứng nhận** đã khử thiên lệch, trục
dẫn dắt là **`size`** (từ ε ≥ 0,2) và **`depth`** (từ ε ≥ 0,7), còn `topic` ở
**mức ngẫu nhiên** — xem bảng đơn cột §3.5b.

### 3.3 Số rò rỉ (corpus `natural=True`)

| đại lượng | TRƯỚC | SAU | vì sao |
|---|---|---|---|
| pool nạp thêm: ước lượng / pool / chung | 1618 / 3349 / 1168 | **không đổi** | `harvest_natural` gieo theo `(seed, repo, offset)`, không qua `_one_event` |
| corpus MẶC ĐỊNH: control phân biệt / của attacker | 2540 / 766 | **2444 / 783** | P8 — đồng xu drift rơi khác |
| corpus HOLDOUT: control phân biệt | 1988 | **1899** | P8, như trên |
| corpus HOLDOUT: giao với ước lượng | **0** | **0** | tính chất mà ô chính dựa vào — **không** dịch |

### 3.4 Quy tắc QUAN HỆ không tham số — đo lại, **không đổi**

*"tag của item này là tập con THỰC SỰ của một topic task nào đó trong workflow nó
nằm"* — cần ngữ cảnh workflow, nên **vẫn ngoài** `F_match` v2.

| Δ | payload bị gắn cờ | control bị gắn cờ | MW-AUC |
|---|---|---|---|
| 0 | 900/900 | 366/3600 | **0,9492** |
| 2 | 826/826 | 325/3304 | **0,9508** |
| 4 | 456/456 | 198/1824 | **0,9457** |

Không đổi, vì nó đọc **topic**, mà topic không dịch. Cái dịch là thứ nó được đọc
**đối chiếu với**:

| | cổng chứng nhận | quy tắc quan hệ | **khoảng cách** |
|---|---|---|---|
| v1 | 0,5414 (4 cột) | 0,9492 | **0,4078** |
| ~~v2 đã giao~~ | ~~0,8805 (5 cột)~~ | 0,9492 | ~~0,0687~~ **RÚT** |
| **v2.1 khử thiên lệch** | **0,5190** (5 cột) | 0,9492 | **0,4302** |

Đây là **kết quả chính** của việc bịt lỗ 1: phần lớn kênh đã **vào trong** không
gian được đo. Phần còn lại là **quan hệ**, và nó ngoài không gian vì lý do **cấu
trúc** (một đặc trưng bề mặt tính từ **một** item), không phải vì bị bỏ quên.

### 3.5 Sàng ε 80 sự kiện — TOÀN LƯỚI, sau khi khử thiên lệch

Trung vị điểm trên 20 split, trần 0,56. Đây là pha **quyết định** ô đỏ (nó chạy
trước và có thể kết thúc test), nên nó được in đủ chứ không chỉ một hàng.

| ε | Δ=0 | Δ=2 | Δ=4 | đạt trần ở **mọi** Δ? |
|---|---|---|---|---|
| **0,0** | **0,4952** | **0,4643** | **0,4770** | **CÓ** ✅ |
| 0,2 | 0,5779 | 0,6245 | 0,5693 | không |
| 0,4 | 0,8160 | 0,8056 | 0,7931 | không |
| 0,7 | 1,0000 | 1,0000 | 1,0000 | không |
| 1,0 | 1,0000 | 1,0000 | 1,0000 | không |

**So với bản trước** (mọi hàng đều 0,74–1,00, **không** hàng nào đạt trần): hàng
ε = 0 **chuyển từ 0,8384 / 0,8499 / 0,9206 xuống 0,4952 / 0,4643 / 0,4770**. Pha
sàng vì thế **đạt**, `eps* = 0,0`, và test **đi tiếp** sang pha chứng nhận — điều
bản trước không bao giờ tới.

### 3.5b ĐẶC TRƯNG NÀO GÁNH HÀNG NÀO — bảng ĐƠN CỘT, **PHA SÀNG**

Bảng "bỏ một cột" **không** trả lời được câu này khi **hai** cột cùng tách hoàn
hảo: bỏ cột nào thì cột kia vẫn giữ AUC ở 1,0. Nên mỗi cột được đo **một mình**
(bốn cột còn lại bị làm phẳng về 0,0 — `discriminator` đòi đủ `F_MATCH`, nên cô
lập một cột là **san phẳng hàng xóm**, không phải xoá chúng).

| ε | Δ | **gộp** | `size` | `depth` | `recency` | `derived` | `topic` |
|---|---|---|---|---|---|---|---|
| 0,0 | 0 | 0,4952 | 0,4832 | 0,5000 | 0,5000 | 0,5000 | 0,5182 |
| 0,0 | 2 | 0,4643 | 0,5100 | 0,5000 | 0,5000 | 0,5000 | 0,4643 |
| 0,0 | 4 | 0,4770 | 0,4937 | 0,5000 | 0,5000 | 0,5000 | 0,4926 |
| 0,2 | 0 | 0,5779 | **0,7029** | 0,5000 | 0,5000 | 0,5000 | 0,5034 |
| 0,2 | 2 | 0,6245 | **0,7179** | 0,5000 | 0,5000 | 0,5000 | 0,4670 |
| 0,2 | 4 | 0,5693 | **0,7551** | 0,5000 | 0,5000 | 0,5000 | 0,4931 |
| 0,4 | 0 | 0,8160 | **0,8369** | 0,5000 | 0,5000 | 0,5000 | 0,4753 |
| 0,4 | 2 | 0,8056 | **0,8497** | 0,5000 | 0,5000 | 0,5000 | 0,4558 |
| 0,4 | 4 | 0,7931 | **0,8768** | 0,5000 | 0,5000 | 0,5000 | 0,5973 |
| 0,7 | 0 | 1,0000 | 0,9009 | **1,0000** | 0,5000 | 0,5000 | 0,4664 |
| 0,7 | 2 | 1,0000 | 0,9255 | **1,0000** | 0,5000 | 0,5000 | 0,5075 |
| 0,7 | 4 | 1,0000 | 0,9374 | **1,0000** | 0,5000 | 0,5000 | 0,5419 |
| 1,0 | 0 | 1,0000 | 0,9250 | **1,0000** | 0,5000 | 0,5000 | 0,4711 |
| 1,0 | 2 | 1,0000 | 0,9611 | **1,0000** | 0,5000 | 0,5000 | 0,4630 |
| 1,0 | 4 | 1,0000 | 0,9562 | **1,0000** | 0,5000 | 0,5000 | 0,5047 |

**ĐÂY LÀ KẾT QUẢ QUAN TRỌNG NHẤT CỦA CẢ ĐỢT SỬA, VÀ NÓ PHẢI ĐƯỢC NÓI THẲNG —
KÈM PHA CỦA NÓ:**

> **Ở PHA SÀNG** (80 sự kiện, trung vị điểm), **`topic` nằm ở mức NGẪU NHIÊN trên
> MỌI hàng — kể cả mọi hàng ĐỎ.** Khoảng đo được là 0,4558–0,5973 trên toàn lưới
> 15 ô. Ở pha sàng nó **không gánh** một hàng nào.

> ⚠️ **KẾT QUẢ PHA SÀNG NÀY KHÔNG SUY RỘNG SANG PHA CHỨNG NHẬN.** Ở pha chứng
> nhận, Δ = 4 (449 sự kiện, cận trên CI trung bình), **`topic` CÓ gánh ô**: trung
> hoà nó đưa ô từ **0,5870 (1/20 split)** xuống **0,5407 (15/20)**. Hai sự thật
> này **cùng đúng** và một người đọc lướt sẽ đâm chúng vào nhau. Chúng khác nhau
> vì **cỡ mẫu** (80 so với 449) và vì **tiêu chí** (trung vị **điểm** so với
> **cận trên CI trung bình**): dư lượng ~0,05 của `topic` ở Δ = 4 **không phân
> giải được** trên một fold 80 sự kiện. Chi tiết và phép tách lực: **§4.1**.

Với **đúng phạm vi đó**, kết luận vẫn đứng: **"kênh topic" — cái phát hiện đã
thúc đẩy toàn bộ đợt dựng lại cổng này, và ở một vòng rà soát trước từng bị gọi
là mối đe doạ nặng nhất của dự án — CHƯA BAO GIỜ MỞ Ở QUY MÔ ĐÃ ĐƯỢC TỐ.** Con
số 0,9492 / 0,8805 là `sorted()` **của chính benchmark** nhìn qua một đặc trưng
từ điển: một **định lý** bị đọc nhầm thành một **phép đo**. Cái còn lại sau khi
khử thiên lệch **không** phải một kênh 0,88 — nó là một **dư lượng 0,5484** ở
**một** Δ, trên corpus **nhỏ nhất**, và nó vẫn đủ làm đỏ một ô.

Cái **thật sự** gánh các hàng đỏ, và **cả hai đều có TRƯỚC v2**:

* **`size`**, từ **ε ≥ 0,2** (0,70 → 0,88 khi ε tăng). Nguồn: `MatchedAttack` tự
  dựng `content` của nó và **không** đi qua `build.payload_content`, nên
  `PAYLOAD_LENGTH` **không** ràng buộc corpus AUC — đúng khoảng trống phạm vi đã
  được ghi ở mục 5 phần "Quan ngại" của báo cáo trước.
* **`depth`**, từ **ε ≥ 0,7**, và nó tách **HOÀN HẢO**: **1,0000**. Nguồn:
  `provenance` của payload có 2 dấu `/`, của ghi chú lành có 1. v2 **không đụng
  vào cột này một dòng nào**.

`recency` và `derived` đọc **đúng 0,5000** ở mọi ô — ghép cặp theo tuổi khoá
`recency`, và không lớp nào có item dẫn xuất. Đó là bằng chứng bảng này đọc đúng.

### 3.5c HỆ QUẢ CHO `F_match` v2 — MỘT QUYẾT ĐỊNH CẦN ĐƯỢC NÊU, KHÔNG PHẢI RÚT

Trục thứ năm được thêm vào `F_match` để **bịt một kênh mà phép đo bây giờ nói là
không tồn tại**. Đó là hệ quả trực tiếp của §3.5b và nó phải được ghi thành lời
chứ không để ngầm.

Bằng chứng, gom lại:

| câu hỏi | bằng chứng |
|---|---|
| `topic` có gánh hàng đỏ nào **ở PHA SÀNG** không? | **Không.** 0,4558–0,5973 trên cả 15 ô (§3.5b) |
| `topic` có gánh ô nào **ở PHA CHỨNG NHẬN** không? | **CÓ — đúng một: Δ = 4.** Trung hoà nó: 0,5870 (1/20) → 0,5407 (15/20) (§4.1) |
| `topic` có làm ô chứng nhận dịch không? | Δ=0: 0,5414 (v1, 4 cột) → **0,5190** (v2.1, 5 cột). Dịch **xuống** 0,02 |
| Vậy 0,8805 của bản trước là gì? | `sorted()[:k]` × mã từ điển = định lý (§0bis.1, §3.7) |
| Quy tắc QUAN HỆ (0,9492) có bị `topic` bắt không? | **Không** — nó cần ngữ cảnh workflow, vẫn ngoài `F_match` (§3.4) |

**Quyết định NÀY KHÔNG PHẢI VIỆC CỦA TRANG NÀY RÚT.** Giữ `topic` trong `F_match`
hay bỏ ra là một sửa đổi **định nghĩa cổng**, phải đi kèm md5 mới và một lần rà
soát. Trang này chỉ **ghi bằng chứng và nêu quyết định**:

* **Lý do GIỮ:** cột này **không hề trơ**. Ở pha chứng nhận nó là cột **duy
  nhất** nhìn thấy dư lượng Δ=4 (§4.1) — trung hoà nó thì ô từ 0,5870 xuống
  0,5407. Và nếu một attacker tương lai **chọn** token theo một quy luật có
  tương quan với bảng chữ cái, `topic` sẽ **nhìn thấy**; cổng không có nó thì mù
  trước cả hai.
* **Lý do BỎ:** nó được thêm vào dựa trên một con số (0,9492 / 0,8805) mà bây
  giờ biết là đọc artefact. Thứ thật sự còn lại nhỏ hơn hai bậc về ý nghĩa —
  một dư lượng 0,5484 ở **một** Δ trên corpus **nhỏ nhất** — nên giữ trục đó mà
  **không** nói rõ điều đó là để một trục đứng trong định nghĩa cổng với một lý
  do đã bị bác.
* **Điều KHÔNG được làm:** bỏ `topic` **để** ô Δ=4 xanh. Bỏ nó **SẼ** làm ô đó
  xanh (0,5407, 15/20) — và **chính vì thế** động cơ đó là sai: đó là **chọn
  không gian đặc trưng theo kết quả**, đúng khuyết tật mà §0bis tồn tại để chặn.
  Nếu `topic` bị bỏ thì phải bỏ vì lý do ở gạch đầu dòng trên, **trước** khi
  nhìn ô, và phải đi kèm md5 mới.

### 3.6 md5 hai đường `experiment.py` — đo lại lần hai

```bash
python3 experiment.py --n 20 | md5
python3 experiment.py --dataset swebench --n 20 | md5
```

| đường chạy | v1 (gốc) | v2 đã giao | **v2.1 khử thiên lệch** | dịch? |
|---|---|---|---|---|
| `--n 20` (mock) | `5655bd49…3e17f61` | `82a919e67835b7f44cd350d10060179d` | **`82a919e67835b7f44cd350d10060179d`** | **KHÔNG** |
| `--dataset swebench --n 20` | `2140bbe7…a7b88e0` | `0bee787507e264b72491b8032c08f14c` | **`a201efec2bb552b6299e3264acea9596`** | **CÓ** |

**Việc mock KHÔNG dịch là một phép ĐỐI CHỨNG, không phải một sự may mắn.** Trên
mock, topic của một task là một `str` **một token**; tập con **không rỗng** duy
nhất của nó là chính nó, nên `payload_topic_like` là **ánh xạ đồng nhất** ở mọi ε
và **không** quy tắc tập con nào — sắp xếp hay giả ngẫu nhiên — có thể dời được
một byte. Digest mock đứng yên đúng bằng giá trị v2 đã công bố, tức lần khử
thiên lệch này **chỉ** chạm vào thứ nó phải chạm: các topic **nhiều token** của
dữ liệu thật.

**Đường swebench dịch, và lý do là dây chuyền đã biết:** quy tắc mới chọn **token
khác** → `topic` của payload đổi → `content` đổi (nhãn `[{topic}] `) →
`Item.__post_init__` băm `content` vào `item_id` → `detector.score` gieo trên
`(seed, item_id)` → **mọi** điểm và **mọi** ô in ra dịch. Các số này được **đo
lại**, không được chỉnh cho số cũ sống sót. Hai digest này là **artefact riêng**
với bản ghi cổng 2.

### 3.7 BẢNG ĐỘ NHẠY BỐN ĐẶC TRƯNG — nghĩa vụ (a) của phán quyết 2

Cả bốn ứng viên, **cùng một corpus**, **cùng quy tắc tập con đã khử thiên lệch**,
ε = 0. Công bố cạnh nhau để không ai phải tin lựa chọn ở §0bis.4b trên lời.

```bash
cd HCMUT/code/Sentinel/auditgame
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
import core, attacks
from analysis import benign_corpus as B, discriminator as D, gate2_v2 as G2
pipe = attacks.REGISTRY["matched"]
for name in ("canonical", "mean", "max", "sum"):
    core.TOPIC_CODE_CHOICE = name          # topic_code tra cuu LUC GOI
    for d in G2.DELTAS:
        pos, neg = B.matched_corpus(pipe, d, 0.0, G2.N_CERTIFY)
        r = D.auc_over_splits(pos, neg, ceiling=0.56, seeds=D.SPLIT_SEEDS)
        print(name, d, len(pos), round(r["auc_mean"], 4), round(r["hi_mean"], 4),
              f"{r['clear']}/{r['k']}")
PY
```

**Pha CHỨNG NHẬN** (900 sự kiện — là **trần**, cận trên CI **trung bình** trên 20
split, trần 0,56):

| đặc trưng | Δ=0 | Δ=2 | Δ=4 | số split tự đạt |
|---|---|---|---|---|
| **`mean`** (ĐƯỢC GIAO) | **0,5190** ✅ | **0,5292** ✅ | **0,5870** ❌ | 20/20, 20/20, **1/20** |
| `canonical` (phán quyết 2 chốt) | 0,7977 ❌ | 0,8249 ❌ | 0,8266 ❌ | 0/20 ở cả ba |
| `max` | 0,8233 ❌ | 0,8355 ❌ | 0,8836 ❌ | 0/20 ở cả ba |
| `sum` | 1,0000 ❌ | 1,0000 ❌ | 1,0000 ❌ | 0/20 ở cả ba |

**Pha SÀNG** (80 sự kiện, **trung vị** điểm trên 20 split), ε = 0:

| đặc trưng | Δ=0 | Δ=2 | Δ=4 |
|---|---|---|---|
| **`mean`** | **0,4952** | **0,4643** | **0,4770** |
| `canonical` | 0,7806 | 0,7456 | 0,7572 |
| `max` | 0,7403 | 0,8256 | 0,7984 |
| `sum` | 1,0000 | 1,0000 | 1,0000 |

**Đọc bảng này cùng bảng đếm ở §0bis.4b thì thấy đúng một chuyện:** thứ tự của
bốn cột AUC **trùng khớp** thứ tự của bốn độ dịch. `sum` dịch mạnh nhất
(−1,4219) và đọc 1,0000; `max` và `canonical` dịch cỡ ±0,03 và đọc 0,74–0,88;
`mean` dịch −0,0002 và đọc ~0,5. AUC ở đây **không** đo kẻ tấn công — nó đo
**độ thiên lệch của chính đặc trưng dưới phép lấy tập con**. Đó là toàn bộ luận
điểm của Phát hiện 1, và bảng này là bản đo của nó trên bốn ứng viên thay vì một.

### 3.8 NGUỒN CUNG sigma khả thi — MỘT ĐẠI LƯỢNG ĐO ĐƯỢC ĐÃ DỊCH

**Không phải chi tiết phụ.** Quy tắc tập con đã khử thiên lệch chọn **token
khác**, nên vị từ **nằm im** (`sim(tag, topic task sớm hơn) >= theta`) bật/tắt ở
một **tập sigma khác**. Corpus vì thế được rút từ một nguồn cung khác, và nguồn
cung là một đại lượng **được đo**, không phải một hằng số:

| Δ | ε | cung TRƯỚC (`sorted()[:k]`) | cung SAU (khử thiên lệch) |
|---|---|---|---|
| 0 | 0,0 | 2248 | **2248** (không đổi) |
| 2 | 0,0 | **826** | **817** |
| 4 | 0,0 | **456** | **449** |
| 2 | 1,0 | 504 | **504** (không đổi) |
| 4 | 1,0 | 202 | **202** (không đổi) |

**Cơ chế, đo được chứ không phỏng đoán.** Ở Δ = 0 không có cửa sổ `[iota, sigma)`
nào để bật vị từ nằm im, nên **mọi** sigma khả thi ở **mọi** quy tắc → 2248
không đổi. Ở ε = 1,0 tập con **là** nguyên topic với **mọi** quy tắc → 504 / 202
không đổi. Cung chỉ dịch ở đúng vùng mà quy tắc thực sự **chọn** — Δ ≥ 2 và
ε < 1 — và nó dịch **xuống** (826→817, 456→449, tức −1,1% và −1,5%): một token
lấy ngẫu nhiên đôi khi trùng topic của một task sớm hơn ở mức ≥ theta, còn token
nhỏ nhất theo từ điển thì đã tình cờ ít trùng hơn. Đây cũng là một dạng
**thiên lệch của `sorted()`**, ở một đại lượng khác: nó làm nguồn cung của corpus
**cao hơn** thực tế.

Nguồn cung đầy đủ trên toàn lưới (cùng lệnh, thay `eps`):

| Δ \ ε | 0,0 | 0,2 | 0,4 | 0,7 | 1,0 |
|---|---|---|---|---|---|
| 0 | 2248 | 2248 | 2248 | 2248 | 2248 |
| 2 | **817** | 813 | 707 | 517 | 504 |
| 4 | **449** | 444 | 341 | 223 | 202 |

Phân bố độ dài nhãn `[{topic}] ` cũng dịch ở ε = 0, và **chỉ** ở ε = 0:

| Δ | ε | n | min | Q1 | trung vị | Q3 | max | ≥ L | % |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0,0 | 2248 | 4 | 8 | 9 | 11 | **35** (trước: 32) | 0 | 0,0 |
| 0 | 1,0 | 2248 | 13 | 24 | 30 | 39 | **506** (không đổi) | **170** | **7,6** |
| 2 | 1,0 | 504 | 13 | 25 | 31 | 40 | 298 | 45 | 8,9 |
| 4 | 1,0 | 202 | 16 | 27 | 33 | 47 | 451 | 29 | 14,4 |

Con số **170 / 2248 = 7,6%** mà phán quyết 3 dựa vào **đứng nguyên**, vì ở ε = 1
tập con là nguyên topic ở cả hai quy tắc.

---

---

## 4. Cổng

| cổng | v1 | v2 đã giao | **v2.1 khử thiên lệch** |
|---|---|---|---|
| 1 — toàn vẹn | 447/447 | 447/447 | **447/447** |
| 2 — hiệu lực | 129/129 | 148/149 — MỘT ĐỎ | **156/158 — HAI ĐỎ** |
| 3 — lực | 15/15 | 15/15 | **15/15** |

Zero skip ở cả ba.

> ⚠️ **"HAI ĐỎ" KHÔNG CÓ NGHĨA LÀ HAI THẤT BẠI.** Người đọc lướt sẽ đọc thành
> vậy, nên nói thẳng ngay đây: **một ô ĐỎ VÌ HỎNG, một ô ĐỎ VÌ ĐẠT QUÁ ĐẬM.**
> Câu trạng thái trung thực trong một dòng:
>
> **cổng 2 ở 156/158 — một ô KHÔNG ĐẠT, và một ô ĐẠT dứt khoát tới mức một cái
> bẫy đã được đặt sẵn phải lên tiếng.**

| # | test | đỏ vì | chiều | § |
|---|---|---|---|---|
| 1 | `test_some_epsilon_makes_the_payload_indistinguishable_at_every_delta` | ô chứng nhận Δ=4 **KHÔNG ĐẠT** (0,5870 so với trần 0,56; 1/20 split) | **thất bại thật** | §4.1 |
| 2 | `test_one_split_cannot_decide_a_delta_of_the_certify_corpus` | Δ=0 và Δ=2 **ĐẠT với 20/20 split** | **bẫy nhất trí, nhánh ĐẠT** | §4.2 |

Ô đỏ số 1 **không còn là cùng một ô** với bản trước: bản trước đỏ ở **pha sàng**
(không ε nào chạm trần ở bất kỳ Δ nào); bản này **qua** pha sàng và đỏ ở **pha
chứng nhận, đúng một Δ**.

Ô đỏ số 2 **chưa từng tồn tại** ở v1 hay v2, và không phải vì nó mới được viết —
nó có từ trước — mà vì **nhánh của nó chưa bao giờ được chạm tới**. Nó là một
bẫy hai chiều; v1 và v2 luôn rơi vào nhánh *nhất trí HỎNG* (hoặc không nhất
trí). Đây là lần đầu tiên corpus rơi vào nhánh *nhất trí ĐẠT*, nên đây cũng là
lần đầu tiên **có người phải nghĩ về nó**.

### 4.1 Ô ĐỎ — phát biểu lại theo đúng bằng chứng (phán quyết 6)

**Câu của bản trước:** *"`MatchedAttack` hỏng ở MỌI epsilon dưới cổng mới"*, kèm
dự báo *"ở ε cao kênh `topic` đóng lại"*.
**Cả hai đều SAI, và phép đo bác cả hai.**

#### Pha sàng — ε = 0 ĐẠT ở mọi Δ

| ε | Δ=0 | Δ=2 | Δ=4 | đạt trần 0,56? |
|---|---|---|---|---|
| **0,0** | **0,4952** | **0,4643** | **0,4770** | **ĐẠT** ✅ |
| 0,2 | 0,5779 | 0,6245 | 0,5693 | không — **`size`** gánh |
| 0,4 | 0,8160 | 0,8056 | 0,7931 | không — **`size`** gánh |
| 0,7 | 1,0000 | 1,0000 | 1,0000 | không — **`depth`** tách **hoàn hảo** |
| 1,0 | 1,0000 | 1,0000 | 1,0000 | không — **`depth`** tách **hoàn hảo** |

`eps* = 0,0`, và test **đi tiếp** sang pha chứng nhận.

#### Pha chứng nhận ở ε* = 0 — đỏ ở ĐÚNG Δ = 4

| Δ | cận trên CI trung bình | điểm ước lượng | split tự đạt | $n_{\text{pos}}$ | kết luận |
|---|---|---|---|---|---|
| 0 | **0,5190** | 0,4860 | **20/20** | 900 (trần) | **ĐẠT** ✅ |
| 2 | **0,5292** | 0,4945 | **20/20** | 817 | **ĐẠT** ✅ |
| 4 | **0,5870** | 0,5394 | **1/20** | 449 | **HỎNG** ❌ |

#### ĐẶC TRƯNG NÀO GÁNH Δ = 4 — và nó KHÔNG hỏng vì thiếu lực **một mình**

Ablation trên **chính corpus chứng nhận** ở ε* = 0, Δ = 4 (449 payload / 1796
control), mỗi cột đo **một mình** và đo **khi bị trung hoà**:

| cột | **một mình**: điểm / cận trên | **bị trung hoà**: cận trên | split tự đạt khi trung hoà |
|---|---|---|---|
| **`topic`** | **0,5484 / 0,5960** | **0,5407** ✅ | **15/20** |
| `size` | 0,4938 / 0,5407 | 0,5960 ❌ | 1/20 |
| `depth` | **0,5000** / 0,5471 | 0,5870 | 1/20 |
| `recency` | **0,5000** / 0,5471 | 0,5870 | 1/20 |
| `derived` | **0,5000** / 0,5471 | 0,5870 | 1/20 |
| *(tất cả)* | — / **0,5870** | — | 1/20 |

**CÂU TRẢ LỜI, phát biểu chính xác:**

> **Ô Δ = 4 do `topic` gánh.** Trung hoà `topic` đưa ô từ **0,5870 (1/20)** xuống
> **0,5407 (15/20)** — **dưới** trần. Không cột nào khác làm được điều đó:
> `depth`, `recency`, `derived` đọc **đúng 0,5000** khi đứng một mình ở ε = 0
> (không mang tín hiệu nào), và trung hoà `size` làm ô **xấu đi** (0,5870 →
> 0,5960).

**Và nó KHÔNG hỏng vì thiếu lực một mình — tính ra được:**

* nửa bề rộng khoảng ở Δ = 4 là $0{,}5870 - 0{,}5394 = 0{,}0476$ (449 sự kiện);
  ở Δ = 0 là $0{,}5190 - 0{,}4860 = 0{,}0330$ (900 sự kiện).
* **Giả sử** Δ = 4 có độ chính xác của Δ = 0: $0{,}5394 + 0{,}0330 = 0{,}5724$ —
  **vẫn trên trần**. Nên **lực không giải thích hết**.
* **Giả sử ngược lại**, Δ = 4 có điểm ước lượng của Δ = 0 nhưng giữ bề rộng của
  chính nó: $0{,}4860 + 0{,}0476 = 0{,}5336$ — **đạt**.

⇒ Cái làm ô đỏ là **ĐIỂM ƯỚC LƯỢNG 0,5394**, không phải khoảng tin cậy; và điểm
ước lượng đó do **`topic`** mang (`topic` một mình: 0,5484; bỏ `topic` đi thì
điểm về ≈ 0,493). Nguồn cung thiếu (449 so với mục tiêu ~900) **làm nặng thêm**
nhưng **không** là nguyên nhân đủ.

**Tái lập phép tách lực này** (mọi số vào là `auc_mean` và `hi_mean` của chính
lệnh ablation ở dưới — không có hằng số nào được nhập tay):

```bash
cd HCMUT/code/Sentinel/auditgame
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
import attacks
from analysis import benign_corpus as B, discriminator as D, gate2_v2 as G2
pipe, CEIL = attacks.REGISTRY["matched"], G2.record()["ceiling"]
r = {}
for d in (0, 4):
    pos, neg = B.matched_corpus(pipe, d, 0.0, G2.N_CERTIFY)
    r[d] = D.auc_over_splits(pos, neg, ceiling=CEIL, seeds=D.SPLIT_SEEDS)
    print(d, len(pos), round(r[d]["auc_mean"], 4), round(r[d]["hi_mean"], 4))
w0 = r[0]["hi_mean"] - r[0]["auc_mean"]          # be rong nua khoang o Delta=0
w4 = r[4]["hi_mean"] - r[4]["auc_mean"]          # ... o Delta=4
print("Delta=4 voi do chinh xac cua Delta=0:", round(r[4]["auc_mean"] + w0, 4),
      ">" if r[4]["auc_mean"] + w0 > CEIL else "<=", CEIL)
print("Delta=4 voi diem uoc luong cua Delta=0:", round(r[0]["auc_mean"] + w4, 4),
      ">" if r[0]["auc_mean"] + w4 > CEIL else "<=", CEIL)
PY
```

#### Đây là một dư lượng, KHÔNG phải một kênh — và giới hạn nào của `mean` nó chạm

`mean` **không thiên lệch** về **kỳ vọng** dưới phép lấy tập con (§0bis.4b), và ở
Δ = 0 / Δ = 2 nó đọc đúng như vậy: 0,4842 và 0,4905 khi đứng một mình. Ở Δ = 4 nó
đọc 0,5484 — lệch khỏi 0,5 khoảng **2 sai số chuẩn** ($\mathrm{SE} \approx
0{,}024$ ở $n = 449$).

Đúng giới hạn **1b** đã ghi ở docstring `core.topic_code`: *không thiên lệch
không có nghĩa là mù*. Lấy tập con **không** dịch kỳ vọng nhưng **có** thổi
**phương sai**, và Δ = 4 là corpus **nhỏ nhất** (449 sự kiện, chỉ 117 workflow
chủ nhà), nơi một dư lượng cỡ đó vừa đủ đẩy **cận trên** qua trần.

**Ô này ĐỂ ĐỎ.** Không nới trần, không đổi tiêu chí, không bỏ cột `topic` (bỏ nó
**để** ô xanh là chọn đặc trưng theo kết quả — đúng thứ §0bis tồn tại để chặn),
không sửa `attacks.py`. Ba việc mà bước **chứng nhận** phải làm với nó:

1. **Nâng $n$ ở Δ = 4.** Trần 900 không đạt được vì **nguồn cung** chỉ có 449
   (§3.8). Đó là một giới hạn của **pool**, và nó đo được.
2. **Quyết định `topic` ở lại `F_match` hay không** (§3.5c) — với bằng chứng,
   không phải với ô đỏ này.
3. **Nếu `topic` ở lại**, dư lượng 0,5484 ở Δ = 4 là thứ một attacker v2 phải
   khớp; nó **không** giống kênh 0,9492 mà `MatchedAttack` từng bị tố.

---

### 4.2 Ô ĐỎ THỨ HAI — đỏ vì corpus **QUÁ MẠNH**, và nó phải ở đó

`test_one_split_cannot_decide_a_delta_of_the_certify_corpus` đỏ với thông điệp:

> *every split clears 0.56 at Delta [0, 2] (bounds: {0: 0.519, 2: 0.5292}). The
> corpus is now strong enough that the multi-split criterion buys nothing THERE —
> say so and simplify deliberately rather than letting a test stay green on a
> claim it no longer makes.*

**Đây là một CÁI BẪY ĐƯỢC ĐẶT CÓ CHỦ Ý, và nó vừa nổ đúng như thiết kế.** Test
này ghi nhận một phát hiện của v1 — *"một split không được quyết một Δ"* — và
được viết để đỏ ở **cả hai** chiều nhất trí:

* **nhất trí HỎNG** → báo cáo là hỏng (đúng cái bản v2 gặp, 0/20 ở cả ba Δ);
* **nhất trí ĐẠT** → **đỏ**, và nói rằng tiêu chí đa-split *có thể* đơn giản hoá
  được — nhưng đó phải là một **quyết định có chủ ý**, không phải một test lặng
  lẽ xanh trên một khẳng định nó không còn đưa ra nữa.

Sau khi khử thiên lệch, Δ=0 và Δ=2 **đạt với 20/20 split**. Nên bẫy nổ ở chiều
**thứ hai**, chiều mà v1 và v2 chưa bao giờ chạm tới.

**KHÔNG SỬA, và lý do là chính lý do việc này tồn tại.** Đơn giản hoá tiêu chí
đa-split là **sửa định nghĩa cổng** — nó dịch md5, nó cần một vòng rà soát, và
làm nó **ngay sau khi vừa nhìn thấy con số** là đúng thứ kỷ luật tiền-đăng-ký ở
§0bis tồn tại để chặn. Nới test cho xanh thì còn tệ hơn: đó là **vá benchmark cho
qua cổng của chính nó**.

**Quyết định được NÊU RA, không được rút ở đây:** với corpus v2.1, tiêu chí
20-split có còn mua gì ở Δ=0 và Δ=2 không? Bằng chứng để trả lời đã có sẵn trong
chính thông điệp đỏ — `hi_max > hi_min` vẫn đúng ở mọi Δ (split **vẫn** làm cận
trên dao động), chỉ là **không split nào vượt trần** ở hai Δ đó. Hai sự thật đó
khác nhau, và ai đơn giản hoá tiêu chí phải phân biệt được chúng.

---

## 5. KHÔNG có phán quyết chứng nhận nào được rút ở đây

Nói thẳng, vì trang này chứa những con số trông rất giống một phán quyết:

- **0,5190 / 0,5292 / 0,5870 KHÔNG phải một phán quyết chứng nhận.** Nó là trạng
  thái của corpus chứng nhận **dưới định nghĩa v2.1 vừa đóng băng**, đo bằng
  `MatchedAttack` — một attacker được dựng cho **v1**. Việc hai trong ba ô **đạt
  trần với 20/20 split** là một **phép đo**, không phải một giấy chứng nhận.
- **`eps*` KHÔNG được công bố lại như một kết quả.** Nó được in vì pha sàng nay
  **đi qua** và test phải chọn một ε để chứng nhận.
- **Không attacker nào bị chuyển khỏi `REGISTRY`, không mục `PENDING` nào được
  thêm.** `attacks.py` **không bị đổi một biểu thức nào** — chỉ banner docstring
  của `MatchedAttack` được **phát biểu lại**, vì banner cũ nói hai điều mà phép đo
  bây giờ bác.
- **Bảng chứng nhận chạy MỘT lần, SAU khi định nghĩa đóng băng** — và nó đã đóng
  băng ở §2, với ngày và md5 `45274180520227436a90f03ca1dd21db`.

### 5.1 Những khẳng định của bản trước bị RÚT

| khẳng định của bản v2 | trạng thái |
|---|---|
| ô chứng nhận Δ=0/2/4 = **0,8805 / 0,9073 / 0,9373** | **RÚT** — đo dưới `sorted()[:k]` (§3.1) |
| *"`MatchedAttack` hỏng ở MỌI ε dưới cổng mới"* | **RÚT** — ε=0 **đạt** ở mọi Δ (§4.1) |
| *"ở ε cao kênh `topic` đóng lại"* | **RÚT** — `topic` **chưa bao giờ mở**; ε cao hỏng vì `depth` (§3.5b) |
| *"khoảng cách cổng ↔ quy tắc quan hệ thu từ 0,4078 xuống 0,0687"* | **RÚT** — dựa trên ô 0,8805; khoảng cách thật là **0,4302** (§3.4) |
| $L = 63$ *"viết và commit trước khi nhìn AUC"* | **RÚT** ordering claim (§0); phép dẫn **giữ** |

---

## 6. Bất biến & phạm vi

- **Không sửa**: `oracle.py`, `runner.py`, `scoring.py`, `metrics.py`,
  `detector.py`. `attacks.py`, `agent.py`, `policies.py` không đổi **một biểu
  thức** nào — `attacks.py` chỉ được phát biểu lại **một banner docstring**.
- **`retrieval.payload_topic` ĐÃ ĐỔI**, và đó là thay đổi trung tâm của đợt này:
  từ `sorted(target)[:k]` sang một tập con giả ngẫu nhiên tất định gieo qua
  `core.seed_of`. Mọi tính chất mô hình đòi đều giữ (§0bis.2), và nó chảy qua
  **một** chỗ nên `feasible_sigmas`, `plan_poison`, `build.inject`,
  `attacks.*.payload` và các test đều đi theo — cổng không còn vừa **bắt buộc**
  một chữ ký vừa **chấm điểm** chính chữ ký đó.
- **`core.topic_code` KHÔNG đổi công thức** (vẫn là trung bình mã token), nhưng
  nay là **một lựa chọn được GỌI TÊN** trong `TOPIC_CODE_CANDIDATES` và được
  **ghim** trong bản ghi. Ba ứng viên bị loại **vẫn là code chạy được**.
- **N3, đã BẮT VÀO ĐƯỜNG CHẠY THẬT** (phán quyết 3): `build.payload_length_reason`
  trước đây **không** được một dòng code sản phẩm nào gọi — chỉ một test gọi. Nay
  (a) `payload_content` **hỏi nó** để quyết nhánh tag-only, nên quyết định và lý
  do là **một biểu thức**; (b) `build.inject` gọi nó trên **mọi** lần chèn và ghi
  `item_id -> lý do` vào một **bồn quan sát** `length_reasons` (cùng thành ngữ
  `control_ids` của `matched_corpus`: không rút nào, hạt giống nào, byte nào phụ
  thuộc vào nó); (c) bản thân **quy tắc kèm ngoại lệ** vào ô băm
  (`payload_length_rule`), nên định nghĩa được công bố **không còn** khẳng định
  `size == 63` trần trụi. Lý do **cố ý không** ghi vào `provenance` —
  `provenance` là đặc trưng **được chấm** (`depth`).
- **Tất định**: mọi rút qua `core.seed_of`; `subset_priority` và `topic_code` đọc
  **byte**, không `hash()`, không thứ tự duyệt `frozenset` — có test chạy qua ba
  `PYTHONHASHSEED` cho **cả hai**.
- **stdlib thuần** ở `analysis/gate2_v2.py`.
- **Chuỗi `content=`**: **không** đổi thêm lần nào ở đợt này (lần đổi duy nhất là
  ở v2, xem §6 bản trước — vẫn còn hiệu lực).

### 6.1 Con trỏ tái lập

| số | lệnh |
|---|---|
| $L = 63$ | §0, khối lệnh thứ nhất |
| phân bố tiền tố tag, nguồn cung sigma | §3.8 |
| **độ dịch tập con** (bảng đếm 4 ứng viên) | §0bis.4b, khối lệnh trong mục |
| §3.1 (ô chứng nhận) | §3.7, khối lệnh chung, đọc `mean` |
| §3.5 / §3.5b (lưới sàng, đơn cột) | §3.7 khối lệnh, đổi `N_CERTIFY`→`N_SCREEN`; đơn cột = san phẳng 4 cột còn lại về 0,0 |
| §3.7 (bốn ứng viên) | §3.7, khối lệnh trong mục |
| §3.3 | `python3 -m unittest tests.gate2_validity.test_dist_matched_attack` |
| §3.4 | `test_matched_epsilon_budget.py`, lớp `TheTopicAxisIsInsideNowAndTheRESIDUEIsWhatStaysOutside` |
| §3.6 | §3.6, hai lệnh `md5` |
| §4.1 (ablation corpus chứng nhận) | §3.7 khối lệnh, thêm vòng cô lập/trung hoà từng cột |
| §4.1 **phép tách LỰC vs ĐIỂM ƯỚC LƯỢNG** | §4.1, khối lệnh ngay dưới bảng ablation |
| §4.1 `topic` gánh Δ=4 (0,5870 → 0,5407) | §4.1, cùng khối lệnh ablation, đọc dòng `topic` |
| md5 cổng 2 v2.1 | §2, lệnh `gate2_v2.md5()` |
| ba cổng | `python3 tests/run_all.py` |

---

## 7. SỔ QUYẾT ĐỊNH CÒN NỢ — nêu ra, KHÔNG rút ở đây

Đợt này đo và ghi; nó **không** sửa định nghĩa cổng ngoài những gì phán quyết 1,
3 và 5 chỉ định. Ba quyết định dưới đây **đã đủ bằng chứng để trả lời** nhưng
**không phải việc của trang này** — mỗi cái đều dịch md5 và cần một vòng rà soát.
Ghi thành sổ để không cái nào chìm.

| # | quyết định | bằng chứng đã có | vì sao KHÔNG rút ở đây |
|---|---|---|---|
| 1 | `topic` **ở lại** `F_match` hay **ra**? | §3.5b (pha sàng: mức ngẫu nhiên, 15/15 ô), §4.1 (pha chứng nhận: gánh Δ=4, 0,5870→0,5407), §3.5c (cả hai phía lập luận) | Đổi tập đặc trưng = đổi **định nghĩa cổng**. Và bỏ nó **sẽ** làm ô Δ=4 xanh → rút nó **sau khi** thấy ô là chọn không gian đặc trưng **theo kết quả** |
| 2 | Tiêu chí **20-split** có còn mua gì ở Δ=0 và Δ=2? | §4.2 (20/20 đạt ở cả hai; nhưng `hi_max > hi_min` **vẫn** đúng ở mọi Δ) | Đơn giản hoá tiêu chí = đổi **định nghĩa cổng**; và làm ngay sau khi thấy số là đúng thứ §0bis chặn |
| 3 | `n_events = 900` có nên là **một số theo Δ**? | §3.8 (cung ở Δ=4 chỉ có **449**), §4.1 (bề rộng khoảng 0,0476 so với 0,0330) | Bản ghi đang ghim một **mục tiêu mà pool không đạt được** ở một Δ. Trung thực chỉ vì số **đạt được** được in cạnh nó |

**Hai điều KHÔNG nằm trong sổ này, vì chúng không phải quyết định mở:**

* **Nới trần 0,56** — bị cấm thẳng. Trần là của câu hỏi 8.
* **Sửa `MatchedAttack` cho vừa cổng** — đó là bước **chứng nhận**, và chỉnh
  attacker cho vừa một cổng nó chưa được đo lại là đúng thứ khuyết tật mà toàn bộ
  kỷ luật này tồn tại để chặn.

### 7.1 Và một điều đợt này KHÔNG làm được

`MatchedAttack` tự dựng `content` và **không** đi qua `build.payload_content`,
nên `PAYLOAD_LENGTH` **chưa bao giờ** ràng buộc corpus AUC. Đó là lý do `size`
gánh **mọi** hàng từ ε ≥ 0,2 (§3.5b: 0,70 → 0,88). Báo cáo trước ước lượng khe hở
này ở mức 0,0008 và gọi nó là "khoảng trống phạm vi"; bây giờ nó **đo được** và
nó là **kênh lớn nhất còn lại** giữa câu *"kênh size đóng theo cấu tạo"* và
corpus mà cổng thật sự đọc. Đóng nó là việc của bước chứng nhận, vì nó **đổi một
attacker**.

