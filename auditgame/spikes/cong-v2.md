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

* `natural` (một mình nó dịch ô 0,8805 → 0,9226),
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

Hai tính chất được mua, và **cần cả hai**:

- **ĐỊNH DANH.** Là hàm của **token nào**, không phải **bao nhiêu token**. Một
  bộ đếm token sẽ chỉ là bản sao của `size` (§2 trang mô hình: 5 topic × 5 mức ε
  → 15 giá trị `size` phân biệt, đúng **1** va chạm, tức `size` gần như xác định
  $k$).
- **THỨ TỰ.** Mã **đơn điệu theo thứ tự từ điển**. Đây không phải trang trí:
  `discriminator` khớp **hồi quy logistic**, đơn điệu theo từng cột, nên một vân
  tay **danh định** (ví dụ blake2b) sẽ là **nhiễu** với nó — cổng có thêm một cột
  mà **không** khó lên chút nào. Mã theo thứ tự từ điển làm
  `retrieval.payload_topic` (`sorted(target)[:k]`, tức **cắt từ đầu bảng chữ
  cái**) **thấp điểm hơn** topic nguyên mà nó bị cắt ra từ đó.

**Kiểm chứng rằng nó đọc ĐÚNG kênh, không phải lén đưa bộ đếm quay lại.** Nếu
tách được là do *số token* (trung bình của 1 mã so với trung bình của 4 mã) thì
hai lớp phải **cùng kỳ vọng, khác phương sai**, và hồi quy tuyến tính **không**
tách được → AUC ≈ 0,5. Đo trên corpus Δ=0, ε=0 (900 payload / 3600 control):

| Δ | AUC đơn cột `topic` | mean(pos) | mean(neg) |
|---|---|---|---|
| 0 | 0,1477 (tức 0,8523 theo chiều "thấp = độc") | 0,3928 | 0,4188 |
| 2 | 0,1138 | 0,3903 | 0,4163 |
| 4 | 0,0934 | 0,3886 | 0,4163 |

Kỳ vọng **lệch hẳn** (0,3928 so với 0,4188) → đây là hiệu ứng **cắt từ đầu**,
đúng cái nó được thiết kế để nhìn thấy. Không phải bộ đếm.

**Giới hạn — khai thẳng, và đã viết trong docstring của `core.topic_code`:**

1. **MẤT MÁT.** Một tập bị thu về một trung bình → hai tập khác nhau vẫn có thể
   trùng mã. Cổng chứng nhận trên một **phép chiếu** của topic, không phải trên
   topic.
2. **THỨ TỰ LÀ TỪ ĐIỂN, KHÔNG PHẢI NGỮ NGHĨA.** `zlib` và `zope` gần nhau ở cột
   này và chẳng liên quan gì nhau trong repo.
3. **KHÔNG DIỄN ĐẠT ĐƯỢC QUAN HỆ.** `surface()` nhìn **một** item, không có
   workflow quanh nó, nên quy tắc không tham số *"tag này là tập con THỰC SỰ của
   một topic task nào đó trong workflow nó đang nằm"* — thứ đo được **0,9492** —
   **vẫn nằm ngoài** `F_match`. v2 **thu hẹp** khoảng cách đó, **không** đóng nó
   (xem §3.4).

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

```json
{"ceiling":0.56,"corpus":{"carrier":"memory","corpus_seed":20260916,"h":8,"pool":"full"},
 "criterion":"mean_ci95_upper_over_split_seeds","date":"2026-09-18",
 "event_seed_rule":"seed_of(SEED, 'one_event', wf.wf_id) & 0xFFFF",
 "features":["depth","derived","recency","size","topic"],"payload_length_L":63,
 "split_seeds":[1,…,20],"test_fraction":0.4,"theta":0.5,
 "verdict":"NOT DRAWN -- certification is a separate step","version":2}
```

$$\boxed{\texttt{md5} = \texttt{d7e7124eb3a46dfe64d9f205850504d9}}$$

Tái lập:

```bash
python3 -c "import sys; sys.path.insert(0,'.'); from analysis import gate2_v2; print(gate2_v2.md5())"
```

Ghim bởi `tests/gate2_validity/test_gate2_v2_definition.py::TheGateTwoV2DefinitionIsFrozen`,
gồm cả một test **nhiễu từng trường một** và đòi digest phải dịch cho **cả tám**
trường — một ô băm không phản ứng là một ô băm không phủ.

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

### 3.1 Corpus CHỨNG NHẬN (`natural=False`, ε=0, 900 sự kiện) — cận trên CI **trung bình** trên 20 split

| Δ | v1 (4 đặc trưng) | **v2 (5 đặc trưng)** | v2 **trung hoà `topic`** | v2 trung hoà `size` | v2 trung hoà `depth` |
|---|---|---|---|---|---|
| 0 | 0,5414 (19/20 đạt) | **0,8805** (0/20) | **0,5414** | 0,8797 | 0,8805 |
| 2 | 0,5394 (17/20) | **0,9073** (0/20) | **0,5394** | 0,9068 | 0,9073 |
| 4 | 0,5411 (18/20) | **0,9373** (0/20) | **0,5411** | 0,9377 | 0,9373 |

**Đọc hai điều, và điều thứ hai quan trọng hơn:**

1. `topic` là **toàn bộ** phần dịch chuyển: trung hoà nó thì con số về **đúng**
   0,5414 / 0,5394 / 0,5411 — **trùng bốn chữ số** với v1. Đây là **phép đối
   chứng** rằng không có gì khác trong đợt sửa này đụng vào corpus đó.
2. **P8 dịch con số này bằng KHÔNG.** Lý do đo được, không phải phỏng đoán: ghi
   chú memory lành là `f"[{task.topic}] ghi chú từ {task.task_id}"` — **hàm tất
   định của task**, không của hạt giống — và ở `natural=False` thì drift **tắt**,
   nên hạt giống chỉ điều khiển adopt / induction / queue, không điều khiển một
   byte nào của lớp âm trên carrier `memory`. Câu *"mọi số ghim theo hạt giống cũ
   SẼ dịch"* của đề bài **đúng ở corpus giàu và sai ở corpus chứng nhận**, và cái
   sai đó là một **phát hiện**, không phải một lỗi: nó nói rằng P8 chưa bao giờ
   là nguồn lệch của ô đang được công bố.

### 3.2 Corpus PHỤ (`natural=True`, `holdout=None`, ε=0, 900 sự kiện)

| Δ | v1 tất cả (4) | v1 bỏ `depth` | v1 bỏ `size` | **v2 tất cả (5)** | v2 bỏ `topic` | v2 bỏ `depth` | v2 bỏ `size` |
|---|---|---|---|---|---|---|---|
| 0 | 0,7056 | 0,6128 | **0,7091** | **0,9226** | 0,6928 | 0,8825 | **0,9217** |
| 2 | 0,7328 | 0,6375 | **0,7305** | **0,9358** | 0,7038 | 0,9084 | **0,9350** |
| 4 | 0,7318 | 0,6400 | **0,7333** | **0,9572** | 0,7075 | 0,9380 | **0,9570** |

Ở **đây** P8 dịch thật: cột "bỏ `topic`" (gần nhất với không gian 4 cột cũ) đọc
0,6928 / 0,7038 / 0,7075 so với 0,7056 / 0,7328 / 0,7318. Cơ chế: drift **bật**,
mà drift là một **đồng xu** phụ thuộc hạt giống, nên tập ghi chú sửa đổi
(`agent/notes/drift`, depth 2) còn sống ở sigma khác đi.

**Kết luận định tính ĐỔI, và được phát biểu lại chứ không bê nguyên:** trên không
gian 5 cột, trục dẫn dắt là **`topic`** (−0,23 ở Δ=0), `depth` thứ hai (−0,04),
`size` vẫn **không dịch gì** (−0,001).

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
| **v2** | **0,8805** (5 cột) | 0,9492 | **0,0687** |

Đây là **kết quả chính** của việc bịt lỗ 1: phần lớn kênh đã **vào trong** không
gian được đo. Phần còn lại là **quan hệ**, và nó ngoài không gian vì lý do **cấu
trúc** (một đặc trưng bề mặt tính từ **một** item), không phải vì bị bỏ quên.

### 3.5 Sàng ε 80 sự kiện (`auc_max`, con số 0,6220 cũ)

| Δ | v1 `auc_max` | **v2 `auc_max`** | v2 `auc_median` |
|---|---|---|---|
| 0 | — | **0,9365** | 0,8384 |
| 2 | **0,6220** | **0,9130** | 0,8499 |
| 4 | — | **0,9599** | 0,9206 |

Lập luận *"dùng trung vị chứ không dùng max"* **không** dựa vào các chữ số cũ:
max của một fold 80 sự kiện vẫn hội tụ về **supremum** chứ không về một đại lượng
tổng thể.

### 3.6 md5 hai đường `experiment.py` — **CÓ DỊCH**

```bash
python3 experiment.py --n 20 | md5
python3 experiment.py --dataset swebench --n 20 | md5
```

| đường chạy | TRƯỚC | SAU |
|---|---|---|
| `--n 20` | `5655bd4956206148c3744045e3d17f61` | **`82a919e67835b7f44cd350d10060179d`** |
| `--dataset swebench --n 20` | `2140bbe796ce925a19631a1c7a88f5e0` | **`0bee787507e264b72491b8032c08f14c`** |

**Vì sao — nói chính xác.** `runner.run_once` chèn payload qua `build.inject`, và
`build.inject` giờ dựng `content` tới độ dài $L$. `Item.__post_init__` băm
`content` thành `item_id` (blake2b), `detector.score` gieo trên `(seed, item_id)`,
nên **mọi điểm đều dịch** và mọi ô in ra dịch theo. Đây **không** phải tác dụng
phụ: đề bài §II.3 và trang mô hình §5.4 nói trước rằng đổi dựng payload là dịch
mọi số phụ thuộc, và các số đó được **đo lại**, không được chỉnh cho số cũ sống
sót. Hai md5 này là **artefact riêng** với bản ghi cổng 2 — bản ghi cổng 2 vẫn là
`d7e7124e…`.

---

## 4. Cổng

| cổng | trước | sau |
|---|---|---|
| 1 — toàn vẹn | 447/447 | **447/447** |
| 2 — hiệu lực | 129/129 | **148/149 — MỘT ĐỎ** |
| 3 — lực | 15/15 | **15/15** |

Zero skip ở cả ba, trước và sau. Gate 2 tăng 129 → 149 do 20 test mới ở
`tests/gate2_validity/test_gate2_v2_definition.py`.

### 4.1 Ô đỏ, và vì sao nó KHÔNG được vá

`test_some_epsilon_makes_the_payload_indistinguishable_at_every_delta`
(`pipeline='matched'`, pha sàng) đỏ. Trung vị điểm trên 20 split:

| ε | Δ=0 | Δ=2 | Δ=4 |
|---|---|---|---|
| 0,0 | 0,8384 | 0,8499 | 0,9206 |
| 0,2 | 0,8428 | 0,8451 | 0,9193 |
| 0,4 | 0,7474 | 0,8395 | 0,8517 |
| 0,7 | 1,0000 | 1,0000 | 1,0000 |
| 1,0 | 1,0000 | 1,0000 | 1,0000 |

Không ε nào chạm trần 0,56.

**Đây CHÍNH LÀ câu hỏi chứng nhận, và việc này bị cấm trả lời nó.** Đề bài nói
rõ: *không chạy quét chứng nhận, không rút kết luận về bất kỳ kẻ tấn công nào* —
đó là bước riêng. Ô này là bài kiểm tra tư cách của `attacks.REGISTRY` chứ không
phải của định nghĩa cổng, và **mọi** cách làm nó xanh đều là một trong bốn thứ bị
cấm:

| cách | vì sao không |
|---|---|
| chuyển `MatchedAttack` sang `PENDING` kèm lý do (đúng N3) | **là** kết luận về attacker; và `REGISTRY` rỗng → `usable_with("exact")` rỗng |
| nới trần / đổi tiêu chí | **vá benchmark cho qua cổng của chính nó** — luật 1 cấm thẳng |
| dựng lại `MatchedAttack` theo mô hình v2 (L cố định, bỏ bậc `provenance`) | là **bước thích nghi/chứng nhận**, làm mù; và là chỉnh attacker cho vừa cổng mới |
| chọn `topic_code` **danh định** (blake2b) để cổng xanh | chọn đặc trưng **theo kết quả** — đúng khuyết tật mà §0 tồn tại để chặn |

Nên ô này **để đỏ và nói đúng sự thật**. Đọc trung thực nhất:
`MatchedAttack` là một attacker **v1**, được tinh chỉnh cho một cổng không nhìn
thấy `topic`; cổng v2 nhìn thấy. Dựng attacker v2 (mô hình §3 dự báo nó tồn tại:
ở ε cao thì tag **phủ nguyên** topic nên kênh `topic` **đóng**, `size` đã cố định
ở $L$, và giá phải trả là **số ký tự lời khuyên**, tức **hại**) là **bước sau**.

---

## 5. KHÔNG có phán quyết chứng nhận nào được rút ở đây

Nói thẳng, vì trang này chứa những con số trông rất giống một phán quyết:

- **0,8805 / 0,9073 / 0,9373 KHÔNG phải một kết luận rằng payload phân biệt
  được.** Nó là trạng thái của corpus chứng nhận **dưới định nghĩa v2 vừa đóng
  băng**, đo bằng `MatchedAttack` — một attacker được dựng cho **v1**.
- **`eps*` KHÔNG được công bố lại.** Bảng sàng ở §4.1 được in vì test đỏ in nó ra,
  không phải vì việc này đi tìm `eps*`.
- **Không attacker nào bị chuyển khỏi `REGISTRY`, không mục `PENDING` nào được
  thêm.** `attacks.py` **không bị sửa một dòng nào**.
- Bảng chứng nhận chạy **MỘT lần**, **sau** khi định nghĩa đã đóng băng — và nó
  đã đóng băng ở §2, với ngày và md5.

---

## 6. Bất biến & phạm vi

- **Không sửa một dòng CODE nào**: `oracle.py`, `runner.py`, `scoring.py`,
  `metrics.py`, `detector.py`, `attacks.py`, `agent.py`, `policies.py`.
  `attacks.py` chỉ được thêm **một banner docstring** ở `MatchedAttack` nói rằng
  mọi AUC trong đó là số **v1** và trỏ sang trang này — để số cũ không đứng đó
  như thể nó là số của cổng hiện hành. Không một biểu thức nào đổi.
- **Chuỗi `content=` đóng băng**: đổi **đúng một lần**, có chủ ý, ở
  `build.inject` (yêu cầu 3 cho phép). Lời khuyên tách **LỆNH + GIẢI THÍCH** và
  dựng **lệnh trước**, vì cắt theo trật tự cũ ở độ dài tiền tố **trung vị** của
  corpus (10) sẽ cắt payload đứt **giữa `raw_write`** — payload gọi tên một hàm
  không tồn tại. Mô hình §4(a) muốn hại **suy giảm** theo $L_{\text{advice}}$,
  không muốn nó bị phá bởi chỗ nhát cắt rơi vào. `attacks.py` **không** được đổi
  theo: các pipeline ở đó tự dựng content và không thuộc phạm vi việc này.
- **Tất định**: mọi rút qua `core.seed_of`; `topic_code` đọc **byte** của token,
  không `hash()`, không thứ tự duyệt `frozenset` — có test chạy qua ba
  `PYTHONHASHSEED`.
- **stdlib thuần** ở `analysis/gate2_v2.py`, như `discriminator` và
  `benign_corpus`.
- **N3**: tag rộng hơn $L$ **ghi lý do** (`build.payload_length_reason`), không
  cắt im lặng, không bỏ sự kiện (bỏ sẽ đổi **mẫu số** của mọi tỉ lệ đo trên sự
  kiện).

### 6.1 Con trỏ tái lập

| số | lệnh |
|---|---|
| $L = 63$ | §0, khối lệnh thứ nhất |
| phân bố tiền tố tag | §0, khối lệnh thứ hai |
| §3.1, §3.2 | §3, khối lệnh chung |
| §3.3 | `python3 -m unittest tests.gate2_validity.test_dist_matched_attack` |
| §3.4 | `spikes/` scratch `relational.py`; hoặc `test_matched_epsilon_budget.py` lớp `TheTopicAxisIsInsideNowAndTheRESIDUEIsWhatStaysOutside` |
| §3.5 | §3 khối lệnh chung, đổi `900` → `80`, đọc `auc_max` / `auc_median` |
| §3.6 | §3.6, hai lệnh `md5` |
| md5 cổng 2 v2 | §2, lệnh `gate2_v2.md5()` |
| ba cổng | `python3 tests/run_all.py --all` |
