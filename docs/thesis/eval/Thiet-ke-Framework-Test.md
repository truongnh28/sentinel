# Framework test AuditGame-SE — kiến trúc và lập luận

> ⚠ **Đã được mở rộng** (14/09/2026). Bốn đường nối N1–N4 ở §3 vẫn đúng và vẫn là nền. Nhưng **N1 chưa đủ**: đổi thang điểm sang $d'$ mà không đặc tả lại phía **tiêu thụ** điểm (`Policy.threshold`, `Sentinel.observe`, ngữ nghĩa carrier rỗng, phép gộp item→carrier) thì sinh ra số không quy được về nguyên nhân. Xem `SPEC-Tang-Do-va-Test.md` §2.5–2.6.
>
> Fixture tí hon ở §5 được giữ nguyên và mở thành **hai profile** (SPEC §7.2).
>
> ⚠ **Errata 15/09/2026 — §4 quy tắc đặt tên đã đổi.** Code và tên test viết bằng **tiếng Anh**; doc giữ tiếng Việt. Ánh xạ *tên test ↔ câu luận văn* **chuyển từ tên hàm vào docstring**, dưới dòng bắt buộc `Thesis claim (vi):`. Tính chất mà §4 bảo vệ giữ nguyên — khi test đỏ vẫn đọc ra câu luận văn — chỉ đổi chỗ đặt. Xem `PLAN.md`, mục *Ngôn ngữ*.
>
> **Phân vai.** `SPEC-Tang-Do-va-Test.md` là **quy phạm** (normative) — kết luận lấy theo nó. Doc này là **lập luận** (descriptive): nó ghi lại *vì sao* đi tới đó, kể cả những bước đã bị thay thế. Vết lập luận là tài sản khi bảo vệ, nên không xoá.

**Framework test không phải lưới an toàn cho code. Nó là LẬP LUẬN.**

Mỗi test bảo vệ **một câu** trong luận văn. Test đỏ ⇒ câu đó không viết được nữa. Nếu không nêu được câu nào bị mất khi test đỏ thì test đó thừa — đó là tiêu chí duy nhất để một test được vào framework, và là lý do doc này không đếm số test.

**Đọc cùng:** `SPEC-AuditGame-SE.md` (bản đặc tả gộp) · `Thiet-ke-Framework-Test-va-Danh-gia.md` (bất biến & giao thức) · `Thiet-ke-AuditGame-SE.md` (cơ chế dựng dataset)

---

## 1. Ba cổng, đi theo đúng thứ tự

Mọi phản bác mà thầy hoặc hội đồng có thể nêu đều rơi vào đúng một trong ba câu. Framework có ba tầng vì có ba câu.

```
             ┌─────────────────────────────────────────────┐
  CỔNG 1     │  LIÊM CHÍNH — thước có tự mâu thuẫn không?  │
             │  "chạy lại có ra đúng số đó không?"          │
             └────────────────────┬────────────────────────┘
                                  │  đỏ ⇒ MỌI số phía dưới VÔ GIÁ TRỊ
             ┌────────────────────▼────────────────────────┐
  CỔNG 2     │  HIỆU LỰC — thước đo ĐÚNG THỨ ta nói không? │
             │  "+51% đó là do phân bổ, hay do cái khác?"   │
             └────────────────────┬────────────────────────┘
                                  │  đỏ ⇒ số có thật, nhưng nói chuyện KHÁC
             ┌────────────────────▼────────────────────────┐
  CỔNG 3     │  ĐỦ MẠNH — có đủ tín hiệu để KẾT LUẬN không?│
             │  "40 workflow đủ tuyên bố ngưỡng 15% chưa?"  │
             └─────────────────────────────────────────────┘
                                  │  đỏ ⇒ số đúng và có nghĩa, nhưng CHƯA KẾT LUẬN ĐƯỢC
                                  ▼
                          kết quả BÁO CÁO ĐƯỢC
```

Ba kiểu hỏng hoàn toàn khác nhau, và **thứ tự là bắt buộc**: vá cổng 2 khi cổng 1 còn đỏ là vá lên cát.

| Cổng | Hỏng nghĩa là | Triệu chứng | Ai bắt |
|---|---|---|---|
| 1 | số **không có thật** | chạy lại ra khác | chính mình |
| 2 | số **nói chuyện khác** | control lệch đáp số | phản biện |
| 3 | số **chưa đủ nói** | CI phủ 0 | hội đồng |

---

## 2. Hai bằng chứng framework này đã bắt được (trước khi viết một dòng test)

Đây là phần thuyết phục nhất của thiết kế: chỉ **đọc theo cấu trúc ba cổng** đã lòi ra hai lỗi thật, mỗi cổng một lỗi.

### Cổng 1 bắt: `base_commit` đổi mỗi lần chạy

`build.py` dựng `base_commit` bằng `abs(hash((wf_id, t)))`. Đo thật, ba lần chạy liên tiếp cùng seed:

```
lần 1 →  007455c
lần 2 →  0897af3      ⚠ cùng seed, khác kết quả
lần 3 →  00b7fbd
```

`hash()` của Python randomize theo `PYTHONHASHSEED`. Đúng cái bẫy mà `seed_of()` sinh ra để tránh — và nó vẫn **sót lại** ở `build.py`.

**Câu bị mất nếu không sửa:** *"kết quả tái lập được"*. Tức là toàn bộ luận văn.

### Cổng 2 bắt: attack không dựng được bị tính thành `harm = 0`

`plan_poison` trả `None` khi workflow không có cặp `(ι, σ)` hợp lệ. Nhưng `worst_case` vẫn `per_wf.append(best)` với `best = 0.0`. Đo thật:

| `Δ` | workflow không dựng được attack | bị tính là |
|---|---|---|
| 0 | 0/40 | — |
| 1 | 0/40 | — |
| 2 | 0/40 | — |
| **4** | **2/40 (5%)** | **`harm = 0` cho MỌI chính sách** |

"Không tấn công được" đang bị đọc thành "phòng thủ thành công". Hai chuyện khác hẳn nhau.

Tệ hơn: tỉ lệ này **tăng theo `Δ`** — `Δ` càng lớn càng khó tìm chỗ nhét. Nên nó bơm số 0 giả vào đúng đầu lớn của trục `Δ`, tức **làm méo chính xu hướng mà RQ1 đi đo**. Một nhiễu ngẫu nhiên thì vô hại; nhiễu tương quan với biến độc lập thì giết kết luận.

**Câu bị mất:** *"độ lợi tăng theo `Δ`"* — RQ1.

> Hai lỗi này không lộ ra khi đọc code tìm bug. Chúng lộ ra khi hỏi **"con số này có thật không"** rồi **"nó nói về cái gì"**. Cấu trúc sinh ra phát hiện, không phải sự chăm chỉ.

---

## 3. Bốn đường nối cần mở trong code

Không phải test nào cũng viết được trên code hiện tại. Bốn chỗ phải mở đường trước — đây là phần **kiến trúc**, và mỗi cái đều làm code sạch hơn chứ không chỉ phục vụ test.

### N1 · Detector chỉ được nhìn điểm
```
hiện tại:  fires(score, item_is_poisoned)     ← ground truth lọt vào vòng quyết định
sau:       fires(score)                        ← ngưỡng thuần
           (ψ, φ) SUY RA từ độ tách d′ + ngưỡng τ, không phải khai rời
```
Mở đường này thì bất biến "không ai ngoài oracle đọc `poisoned`" thành **đúng theo cấu trúc**, khỏi cần dây bẫy. Và nó sửa luôn chiều RQ4 bị ngược — detector yếu lúc đó mới thực sự làm điểm kém thông tin đi.

### N2 · Chính sách phải dựng qua factory
```
hiện tại:  lambda n, b: cls(n, b)      ← rơi mất rng_seed ⇒ mọi workflow dùng CÙNG chuỗi ngẫu nhiên
sau:       make_policy(name, budget, rng_seed=seed_of(wf_id, seed, name))
```
Ngẫu nhiên hóa là **đòn bẩy mạnh nhất của Sentinel** theo ablation. Nếu chuỗi ngẫu nhiên trùng nhau trên mọi workflow thì ta đang đo **một lần tung xúc xắc lặp 40 lần**, không phải 40 mẫu.

### N3 · Tính khả thi là kết quả hạng nhất
```
hiện tại:  plan_poison → None → lặng lẽ thành 0.0
sau:       mỗi ô lưới trả  (harm, n_feasible, n_survived, n_total)
           harm CHỈ tính trên n_feasible;  n_feasible LUÔN in ra cạnh harm
```
Số nào không đi kèm mẫu số thì không báo cáo. Đây là cách cổng 2 được cưỡng chế chứ không phải ghi nhớ.

### N4 · Tập sống sót đóng băng một lần
```
hiện tại:  paired() chạy lại pha SẠCH cho từng chính sách
sau:       survivors(wf, seed) tính MỘT lần → freeze → dùng chung cho B1..B6 + Sentinel
```
Pha sạch không phụ thuộc chính sách. Chạy lại vừa tốn 7 lần, vừa mở cửa cho việc **so sánh trên hai tập instance khác nhau** — thiên lệch mà bảng kết quả trông vẫn bình thường.

---

## 4. Bố cục, và quy tắc đặt tên

```
auditgame/
├── (các module hiện có)
└── tests/
    ├── gate1_integrity/     chạy lại có ra đúng số đó không
    ├── gate2_validity/      số đó nói về cái gì
    ├── gate3_power/         đã đủ để kết luận chưa
    ├── fixtures.py          thế giới tí hon tất định
    └── run_all.py           chạy tuần tự, DỪNG ở cổng đầu tiên đỏ
```

**Quy tắc đặt tên: tên test là CÂU nó bảo vệ, không phải hàm nó gọi.**

| ✗ Tên theo hàm | ✓ Tên theo câu được bảo vệ (tên thật trong repo) |
|---|---|
| `test_plan_poison` | `test_an_unbuildable_attack_does_not_count_as_harm_zero` |
| `test_detector` | `test_no_one_but_the_oracle_reads_poisoned` |
| `test_worst_case` | `test_no_clean_carrier_reads_hotter_than_a_poisoned_one` |
| `test_seed` | `test_rerunning_the_same_seed_gives_an_identical_trace` |

Lý do không chỉ là thẩm mỹ: khi test đỏ, dòng báo lỗi **chính là** câu trong luận văn vừa mất chỗ dựa. Không cần dịch từ tên hàm sang ý nghĩa — chỗ đó là chỗ người ta lười, rồi bỏ qua test đỏ.

> **Errata — ngôn ngữ.** Tên test nay viết bằng **tiếng Anh** (xem `PLAN.md`, mục *Ngôn ngữ*). Ánh xạ tên↔câu luận văn chuyển vào docstring dưới dòng bắt buộc `Thesis claim (vi):`, nên khi test đỏ vẫn đọc ra câu tiếng Việt — chỉ đổi chỗ đặt, không mất.

**Nền chạy:** `unittest` của stdlib. Máy này **không có `pytest`, không có `hypothesis`, không có `numpy`/`scipy`** (đã kiểm, Python 3.14.6). Ràng buộc này thực ra tốt: benchmark mà người khác `git clone` rồi chạy được ngay bằng `python3 -m unittest` thì dễ được tái lập hơn nhiều.

**`run_all.py` dừng ở cổng đầu tiên đỏ** — cố ý. Chạy tiếp cổng 2 khi cổng 1 đỏ chỉ sinh ra một màn hình lỗi mà không cái nào đáng đọc.

---

## 5. Thế giới tí hon — điều kiện để test là lập luận, không phải bùa

Test trên 40 workflow ngẫu nhiên với ngân sách 17,95 thì **không ai kiểm được bằng tay**. Nó "xanh" nhưng không thuyết phục ai, kể cả chính mình.

Fixture phải nhỏ tới mức **tính nhẩm ra đáp số**:

```
2 workflow · H = 4 task · 1 carrier · Δ = 1 · B = 1,0
   → đúng 2 lựa chọn audit khả thi mỗi task
   → toàn bộ cây quyết định vẽ vừa một trang giấy
```

Chỉ ở cỡ này thì "đáp số bắt buộc" mới là **suy ra được**, chứ không phải chép từ lần chạy trước. Test chép output lần chạy trước là test **khóa chặt bug**, không phải test bảo vệ câu nào.

Quét lưới đầy đủ vẫn dùng cỡ thật — nhưng nó là **thí nghiệm**, không phải test.

---

## 6. Đầu ra: bảng kết quả tự mang theo bằng chứng

Cổng 3 không cưỡng chế được bằng assertion — nó cưỡng chế bằng **định dạng bắt buộc**. Mọi bảng kết quả in ra phải kèm bốn thứ, nếu không thì không phải bảng kết quả:

```
cấu hình   sha256:a3f1…   ← hash-freeze, chốt TRƯỚC khi chạy
khả thi    38/40          ← N3: đã loại workflow không dựng được attack
sống sót   26/38 (68%)    ← N4: tập ĐÓNG BĂNG, dùng chung mọi chính sách
Δharm      0,21  CI95 [0,08 ; 0,33]
```

Bốn dòng này trả lời sẵn bốn câu hỏi đầu tiên mà người phản biện sẽ hỏi. Một con số trần trụi không có chúng thì **người đọc buộc phải tin ta** — mà đó đúng là thứ framework này sinh ra để khỏi phải cầu xin.

---

## 7. Framework này bảo vệ chính xác những câu nào

Bản đồ cuối. Mỗi dòng là một câu sẽ nằm trong luận văn, và cột giữa là thứ duy nhất giữ nó đứng được.

| Câu trong luận văn | Giữ bởi | Cổng |
|---|---|---|
| "kết quả tái lập được" | trace giống hệt qua hai lần chạy | 1 |
| "chính sách không biết đâu là mầm độc" | N1 — không đường nào đọc tới `poisoned` | 1 |
| "mọi hệ thống cùng ngân sách `B`" | `Σκ ≤ B` cưỡng chế ở runner, không phó mặc chính sách | 1 |
| "nằm im đúng `Δ` task" | `fired_at − ι == Δ` | 1 |
| "worst-case, không phải trung bình" | `≥` mọi attacker đơn lẻ | 1 |
| "harm là do payload gây ra" | control không-tiêm ⇒ `harm ≡ 0` | 2 |
| "độ lợi đến từ **phân bổ**" | control `B=0` và `B=∞` ⇒ độ lợi `→ 0` | 2 |
| "`Δ=0` thì không còn lợi thế" | control `κ` phẳng tách thông tin khỏi chênh giá | 2 |
| "độ lợi **tăng theo `Δ`**" | N3 — số 0 giả không được bơm vào đầu lớn của `Δ` | 2 |
| "`χ` lớn ⇒ lợi thế lớn" | lớp attacker phải phủ **cả 4** carrier | 2 |
| "vượt ngưỡng 15%" | CI ghép cặp không phủ ngưỡng | 3 |
| "chi phí giảm hai bậc nhờ replay" | replay khớp bit lần chạy trực tiếp | 3 |

Dòng **"`χ` lớn ⇒ lợi thế lớn"** hiện **không có gì giữ**: `experiment.py` chỉ quét `carriers = ("memory","skill")`, tức hai carrier rẻ nhất. `χ` đo độ lệch chi phí **giữa các carrier**, mà lớp attacker lại bị bó vào `{0,4 ; 0,9}` — nên `χ` thực gần như cố định. **RQ2 chưa từng được kiểm, dù bảng vẫn in số.**

Đó là dòng trống đáng giá nhất trong bảng này. Không có cấu trúc ba cổng thì nó vẫn trống mà không ai biết.
