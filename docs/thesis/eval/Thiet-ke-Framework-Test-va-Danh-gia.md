# Thiết kế framework test và đánh giá — AuditGame-SE

> ⚠ **Đã bị thay thế một phần** (14/09/2026). Ba mục dưới đây đã được sửa ở `SPEC-Tang-Do-va-Test.md`.
>
> | Mục ở doc này | Trạng thái | Thay bằng |
> |---|---|---|
> | §3 · C3 ngân sách ∞ — *"mọi chính sách audit hết"* | **đáp số sai** — $B\to\infty$ không đổi được TẬP HÀNH ĐỘNG của B1/B3/B4 | SPEC §6.3 |
> | §3 · C4+C5 trình bày cộng tính | **thiếu số hạng tương tác** — đây là ablation hai nhân tố | SPEC §6.3 |
> | §2 · I10 đơn điệu theo $B$ | **không phải bất biến** — có 6 phản ví dụ đo được | SPEC §6.2, hạ xuống cổng 2 |
> | §4 · sửa I7 bằng $d'$ + $\tau$ | **đúng nhưng chưa đủ** — không đặc tả phía TIÊU THỤ điểm (`threshold`, `observe`, carrier rỗng) | SPEC §2.5–2.6 |
>
> **Phân vai.** `SPEC-Tang-Do-va-Test.md` là **quy phạm** (normative) — kết luận lấy theo nó. Doc này là **lập luận** (descriptive): nó ghi lại *vì sao* đi tới đó, kể cả những bước đã bị thay thế. Vết lập luận là tài sản khi bảo vệ, nên không xoá.

**Nguyên tắc:** chưa kiểm chứng được **phép đo** thì đừng sửa **mô hình**. Sửa mô hình khi thước còn lệch thì số mới ra cũng không quy được về nguyên nhân nào.

Prototype đang cho hai kết quả đáng ngờ (`Δ=0` độ lợi +51% · chiều RQ4 ngược). Phản ứng sai là lao vào sửa mô hình. Phản ứng đúng là dựng bộ đo có khả năng **nói cho ta biết một con số là thật hay là artifact** — rồi để chính nó chẩn đoán hai bất thường kia.

Doc này chỉ nói về **đo và đánh giá**. Tối ưu (chỉnh Sentinel, sửa `Δ=0`, cắm LLM thật) nằm sau, và **phải** nằm sau.

**Đọc cùng:** `SPEC-AuditGame-SE.md` (bản đặc tả gộp) · `Thiet-ke-AuditGame-SE.md` (cơ chế dựng dataset) · `docs/guides/Huong-dan-tai-lap-test-va-baseline-FSE-2027-15.md`

---

## 1. Hai tầng test, đừng trộn

Đây là chỗ dễ lẫn nhất, và lẫn thì mọi kết luận về sau đều treo.

| Tầng | Câu hỏi | Trả lời bằng | Sai thì |
|---|---|---|---|
| **A — test framework** | Cái thước có đúng không? | Bất biến · control · assertion | Mọi số ở tầng B vô giá trị |
| **B — đánh giá hệ thống** | Sentinel có hơn B1 không? | Quét lưới · bootstrap ghép cặp | Kết luận sai, nhưng biết là sai |

Hai bất thường hiện tại lộ ra ở **tầng B** (thấy số trông lạ). Nếu có tầng A thì chúng lộ ra dưới dạng **assertion đỏ** — kèm luôn nguyên nhân. Mục 3 chứng minh điều đó: một control duy nhất tách được +51% thành hai thành phần.

---

## 2. Tầng A — mười bất biến của bộ đo

Mỗi bất biến là một phát biểu **kiểm được bằng máy**, không phải quy ước code review.

### I1 · Tái lập bit-đối-bit
Cùng `(seed, cấu hình)` → trace giống hệt. Kiểm bằng hash trace hai lần chạy.
> Nền của mọi thứ còn lại. Đã xử bằng `seed_of()` blake2b, nhưng **chưa có test**.

### I2 · Cách ly ground truth
Không chính sách nào được đọc cờ `poisoned`.
```
Item.poisoned  ──✗──>  Policy.choose()
               ──✓──>  Detector       (duy nhất, và chỉ để cưỡng chế ψ/φ)
```
Kiểm bằng **dây bẫy**: bọc `Item` sao cho đọc `.poisoned` trong lúc thân `Policy.choose` đang chạy thì **ném exception**. Đây là bất biến quan trọng nhất — vi phạm nó thì toàn bộ benchmark thành vô nghĩa mà số vẫn trông rất đẹp.

### I3 · `Δ` khai phải bằng `Δ` thực
`fired_at − ι` **==** `Δ` khai báo, với mọi instance hợp lệ.
> Đúng con bug đã xảy ra một lần (payload nổ ngay tại `ι`). Nó phải là assertion, không phải điều ta hy vọng.

### I4 · Khả thi ngân sách
Với **mọi** chính sách, mọi lần chạy: `Σκ(aₜ) ≤ B`.
> `runner.run_once` hiện gọi `pol.charge(...)` **vô điều kiện** sau `choose`. Các chính sách tự kiểm bằng `can()`, nhưng không có gì ở tầng runner cưỡng chế. Một baseline viết cẩu thả sẽ **âm thầm vượt ngân sách và thắng** — đúng kiểu lỗi khiến bài báo bị rút.

### I5 · `κ` đo được, không gán
`KAPPA` phải suy từ `audit_seconds` trong trace, không phải hằng số viết tay.
> Hiện đang gán tạm từ chi phí **theo giai đoạn** §7, trong khi `χ` định nghĩa **theo carrier**. Đây là gốc của mâu thuẫn `χ = 1,34` vs `2,11`. Test: `KAPPA` phải load từ file đo, và file đó phải có provenance.

### I6 · Bộ instance sống sót phải ĐÔNG NHẤT giữa các chính sách
Run sạch **không phụ thuộc chính sách** → tập sống sót phải tính **một lần** rồi đóng băng, dùng chung cho cả B1..B6 và Sentinel.
> `paired()` hiện chạy lại pha sạch cho **từng** chính sách. Vừa tốn gấp 7 lần, vừa mở đường cho việc so sánh trên **hai tập instance khác nhau** — thiên lệch mà không ai thấy. Sửa: `survivors(wf, seed)` có cache, freeze trước khi quét.

### I7 · Tương thích detector (⚠ đang VI PHẠM — xem Mục 4)
TPR/FPR **thực nghiệm** sinh ra từ `raw_score` + ngưỡng phải **khớp** `(ψ, φ)` đã khai.

### I8 · Worst-case là MAX
`worst_case ≥ harm` của **mọi** attacker đơn lẻ trong lớp. Và phải chốt rõ là **max-của-trung-bình-seed** (đang dùng) chứ không phải max-của-max — hai đại lượng khác nhau, chọn cái nào cũng được nhưng phải ghi ra.

### I9 · Tương đương replay
Replay từ trace phải cho **đúng** con số của lần chạy trực tiếp, trên mọi ô mà cách ly không kích hoạt.
> Đây là điều kiện để **đòn bẩy giảm chi phí hai bậc** là hợp pháp. Không có test này thì replay chỉ là lời hứa.

### I10 · Đơn điệu theo ngân sách
`harm` không tăng khi `B` tăng, với mọi chính sách.
> Đơn điệu theo `Δ` thì **KHÔNG** đưa vào đây — đó là **giả thuyết cần kiểm** (RQ1), không phải bất biến của bộ đo. Lẫn hai loại này là tự chứng minh điều mình muốn.

---

## 3. Tầng A — năm control, và cách chúng chẩn đoán `Δ=0`

Control = chạy ở cấu hình mà ta **biết trước** đáp số. Lệch đáp số ⇒ bộ đo sai, dừng lại.

| # | Control | Đặt gì | Đáp số bắt buộc |
|---|---|---|---|
| **C1** | không tiêm | `ps = None` | `harm == 0` **tất định**, mọi chính sách |
| **C2** | ngân sách 0 | `B = 0` | mọi chính sách **trùng nhau**, độ lợi `= 0` |
| **C3** | ngân sách ∞ | `B = 10⁶` | mọi chính sách audit hết, độ lợi `→ 0` |
| **C4** | **Sentinel mù** | bỏ belief, giữ ngẫu nhiên hóa + trọng số `1/κ` | độ lợi còn lại = **thuần chênh lệch giá** |
| **C5** | **κ phẳng** | `κ(k) = c` với mọi `k`, `κ_commit = c` | độ lợi còn lại = **thuần thông tin** |

**C1** là thứ bắt lỗi quy-gán-harm. Nếu có chính sách nào cho `harm > 0` khi không tiêm thì oracle đang chấm cả hỏng-tự-nhiên thành thiệt hại.

**C4 + C5 giải trực tiếp bất thường ①.** Độ lợi +51% tại `Δ=0` là tổng của hai kênh mà mô hình đang gộp:

```
độ lợi(Δ=0) = 51%
      ├── C4 đo được phần chênh lệch giá   (upstream κ=0,4 rẻ hơn commit κ=4,1)
      └── C5 đo được phần thông tin        (PHẢI ≈ 0 tại Δ=0)
```

Dự đoán: **C5 sẽ cho ≈ 0 và C4 cho ≈ 51%.** Nếu đúng vậy thì `Δ=0` **không phải bug của Sentinel** — nó là hệ quả của việc khai `κ_upstream ≠ κ_commit`, và câu hỏi cho thầy thu về đúng một câu: *smoke test gốc có cho upstream audit và commit audit cùng chi phí đơn vị không?* Hai con đường độc lập (`smoke_repro` với `K=1`, và prototype với `Δ=0`) cùng chỉ về câu hỏi này.

Điểm đáng nói: **kết luận đó có được mà không sửa một dòng mô hình nào.** Đó là lý do framework đo phải đi trước.

---

## 4. Một lỗi bộ đo tìm ra khi đọc code — và nó giải thích RQ4

Bất biến **I7 đang bị vi phạm**, theo cách giải thích trọn vẹn chiều RQ4 bị ngược.

Hiện tại `(ψ, φ)` và `raw_score` là **hai núm rời nhau**:

```
detector.raw_score(item)  →  N(0,62 ; 0,17) nếu độc · N(0,38 ; 0,17) nếu sạch
                             ⇧ KHÔNG phụ thuộc (ψ, φ) chút nào
detector.fires(score, poisoned)  →  score > 1 − (ψ nếu độc, ngược lại φ)
                             ⇧ dùng GROUND TRUTH, không dùng phân bố trên
```

Hệ quả theo hai bước:

1. Đổi detector `weak → strong` **không đổi** điểm mà B5/B6/Sentinel nhìn thấy. Nó chỉ làm audit upstream **bắt trúng nhiều hơn**.
2. Sentinel audit upstream **nhiều hơn** B1 (vì rẻ hơn). Nên detector mạnh **có lợi cho Sentinel hơn** cho B1.

⇒ độ lợi **tăng** theo độ mạnh detector. Đúng như prototype in ra, và **ngược** manuscript.

Mô hình đúng phải là: detector yếu ⇒ điểm **kém thông tin hơn** (hai phân bố chồng nhau nhiều hơn). Lúc đó B5 risk-score **sụp** vì nó lái hoàn toàn theo điểm, còn Sentinel **xuống dốc êm** vì có ngẫu nhiên hóa làm sàn. Đó mới là cơ chế sinh ra "lợi thế lớn nhất khi detector yếu nhất".

**Sửa ở tầng đo, không phải tầng mô hình:** tham số hóa `raw_score` bằng **độ tách** `d′` của hai phân bố, suy `(ψ, φ)` ra **từ** `d′` cộng ngưỡng, rồi để `fires()` chỉ còn là so sánh ngưỡng thuần — bỏ hẳn tham số `poisoned`. Khi đó I7 thành hằng đúng theo cấu trúc, và I2 mạnh lên: **không còn ai** đọc ground truth ngoài oracle.

| | Hiện tại | Sau khi sửa |
|---|---|---|
| Núm điều khiển | `ψ`, `φ` rời rạc | `d′` + ngưỡng `τ` |
| `fires()` cần `poisoned` | **có** ⚠ | không |
| Detector yếu ảnh hưởng điểm | không | **có** |
| Quét `(ψ,φ)` hậu kỳ | được | được (quét `τ` là đủ) |

Đây là **sửa phép đo**, không phải tối ưu hệ thống — nên nó thuộc phase này.

---

## 5. Tầng B — giao thức đánh giá

### 5.1 Đơn vị phân tích
Là cặp **(workflow, seed)**, **không** phải task. H task trong một workflow chia nhau trạng thái carrier nên không độc lập; coi chúng là mẫu độc lập sẽ làm khoảng tin cậy hẹp giả.

### 5.2 Chỉ số
| Chỉ số | Định nghĩa | Lưu ý |
|---|---|---|
| `harm` | nhị phân lọt lưới, theo bảng chân trị oracle | đã chốt |
| `Δharm` | `h_B1 − h_Sentinel` (**tuyệt đối**) | chỉ số **chính** |
| `gain%` | `Δharm / h_B1` | **chỉ báo khi `h_B1 ≥ 0,05`** |
| `spent` | `Σκ` thật đã dùng | kiểm I4 |
| `kept/total` | tỉ lệ instance hợp lệ | kiểm I6 |

> **Lý do hạ `gain%` xuống hàng phụ:** `experiment.py` đang chia cho `max(h_B1, 1e-9)`. Khi `h_B1 → 0` (ngân sách lớn, hoặc `Δ` nhỏ) tỉ số này nổ hoặc đổi dấu tùy ý. Đúng vào những ô mà ta cần đọc `Δ=0` thì nó bất định nhất. Báo tuyệt đối, kèm tỉ số **khi mẫu số còn nghĩa**.

### 5.3 Thống kê
**Bootstrap ghép cặp trên workflow** — ghép cặp vì cùng một tập workflow chạy qua mọi chính sách, nên chênh lệch mới là đại lượng có phương sai nhỏ.

```
lặp 10.000 lần:
    bốc lại có hoàn lại N workflow
    tính Δharm trên mẫu bốc
→ CI 95% = phân vị 2,5 / 97,5
```

Với `N=40` và harm nhị phân, CI rộng cỡ **±0,10–0,15**. Nghĩa là **40 workflow không đủ** để tuyên bố ngưỡng 15%. Con số cần: xấp xỉ `N ≥ 300` cho nửa-độ-rộng `±0,05`. Đây là ràng buộc phải nói với thầy sớm, vì nó đổi ngân sách.

### 5.4 Tiền-đăng-ký
Trước khi chạy bất kỳ lần nào tính điểm: ghi ra file và **hash-freeze**
- các ô lưới sẽ báo cáo — **toàn bộ** `Δ × χ × detector`, không chọn lọc về sau
- ngưỡng gate `≥ 15%`, ở ô nào, đo bằng chỉ số nào
- tiêu chí bác bỏ từng RQ

Không có bước này thì việc chọn ô sau khi thấy số là **chọn lọc hậu kỳ** — và nó sẽ bị hỏi ngay ở hội đồng.

### 5.5 Tiêu chí BÁC BỎ từng RQ
Thiếu mục này thì không phải nghiên cứu. Cái gì cũng "đúng" được nếu không nói trước cái gì sẽ làm nó sai.

| RQ | Khẳng định | **Bác bỏ nếu** |
|---|---|---|
| RQ1 | độ lợi tăng theo `Δ` | `Δharm` không đơn điệu, hoặc CI tại `Δ=4` phủ 0 |
| RQ2 | `χ` lớn ⇒ độ lợi lớn | `Δharm` bằng nhau trong CI giữa `χ` thấp và cao |
| RQ3 | ngẫu nhiên hóa là đòn bẩy mạnh nhất | ablation cho belief đóng góp ≥ ngẫu nhiên hóa |
| RQ4 | độ lợi lớn nhất khi detector yếu nhất | `Δharm(weak) < Δharm(strong)` ngoài CI |

**RQ4 đang bị bác bỏ trên prototype.** Sau khi sửa I7 (Mục 4) thì mới biết đó là lỗi phép đo hay khẳng định của manuscript thật sự sai. Tôi nghiêng về lỗi phép đo.

---

## 6. Thứ tự làm

| # | Việc | Xong nghĩa là | Chặn cái gì |
|---|---|---|---|
| **T0** | `tests/` + I1, I3, I4, I8 | 4 assertion xanh | tất cả |
| **T1** | Dây bẫy I2 · sửa I6 freeze survivor | đọc `poisoned` trong policy → nổ | mọi số so sánh |
| **T2** | Sửa I7: `d′` thay `(ψ,φ)` | `fires()` không còn nhận `poisoned` | RQ4 |
| **T3** | Control C1–C3 | 3 đáp số khớp | quy-gán harm |
| **T4** | **Control C4 + C5** | tách được +51% thành hai kênh | **chẩn đoán `Δ=0`** |
| **T5** | Bootstrap ghép cặp + CI | mọi ô có khoảng tin cậy | phát biểu gate |
| **T6** | Tiền-đăng-ký + hash-freeze | file có hash | tính chính danh |
| **T7** | Test tương đương replay I9 | replay khớp bit | đòn bẩy chi phí |
| — | ⟨ranh giới⟩ | **tới đây thước mới đáng tin** | |
| **T8+** | tối ưu: sửa mô hình, chỉnh Sentinel, cắm LLM | — | — |

T0–T7 chạy trên mock agent, **tốn 0 đồng**, mất khoảng một tuần. Sau T7 thì mọi thay đổi mô hình đều **quy được về nguyên nhân** — trước T7 thì không.

---

## 7. Ngoài phạm vi phase này

Nêu rõ để không tự trôi sang việc khác:

- ✗ sửa độ lợi `Δ=0` — **T4 phải nói trước** đó là bug hay là artifact của `κ`
- ✗ chỉnh tham số Sentinel — chỉnh khi thước còn lệch thì không phân biệt được "tốt hơn" với "khớp artifact hơn"
- ✗ cắm `LlmAgent` / LLM thật — chỉ đổi `agent`, không đổi gì trong tầng đo; và nó tốn tiền
- ✗ chốt `χ = 1,34` — chờ `κ` đo được ở I5

---

## 8. Nợ kỹ thuật tìm ra khi đọc code

Không thuộc tầng bất biến nhưng phải ghi lại:

|     | Chỗ                            | Vấn đề                                                                                                                                         |
| --- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | `runner.py` nhánh audit commit | `o.writes[0]` — **IndexError** nếu task không ghi gì                                                                                           |
| D2  | cùng chỗ                       | điểm alarm lấy từ `writes[0]` tùy ý, và truyền `True` cứng cho `item_is_poisoned` ⇒ commit audit bắt được với xác suất `ψ` bất kể patch ra sao |
| D3  | `paired()`                     | chạy lại pha sạch cho từng chính sách — thừa 7 lần (xem I6)                                                                                    |
| D4  | `worst_case()`                 | `lambda n, b: cls(n, b)` mất `rng_seed` ⇒ B2 và Sentinel dùng **cùng** chuỗi ngẫu nhiên trên mọi workflow                                      |
| D5  | `experiment.py`                | `carriers = ("memory","skill")` — bỏ `queue` và `branch`, nên `χ` **chưa từng được quét thật** ⇒ RQ2 hiện **chưa có dữ liệu**                  |

**D5 là nặng nhất.** Lớp attacker đang bị giới hạn ở hai carrier rẻ nhất, mà `χ` lại chính là đại lượng đo **độ lệch chi phí giữa các carrier**. Quét `χ` mà chỉ dùng `{0,4 ; 0,9}` thì `χ` thực luôn nhỏ và gần như cố định — **RQ2 chưa được kiểm, dù bảng vẫn in ra số.** Đây đúng là loại lỗi mà framework test tồn tại để bắt.
