# Thiết kế AuditGame-SE — cơ chế và kế hoạch dựng

**Bối cảnh:** `AuditGame-SE` là **đóng góp** của đề tài FSE-2027-15, không phải dữ liệu tải về được. Manuscript liệt kê nó ở mục Datasets với nhãn **New**, và §14 nói artifact chỉ công bố *sau khi cửa sổ đánh giá đóng*. Nên phải tự dựng.

**Trạng thái:** đã có prototype chạy được ở `auditgame/` — mock agent, không phụ thuộc thư viện ngoài, không gọi LLM. Dùng để kiểm chứng thiết kế trước khi tiêu tiền.

**Đọc cùng:** `SPEC-AuditGame-SE.md` (bản đặc tả gộp, thay thế phần thiết kế ở đây) · `../Toan-canh-de-tai-FSE-2027-15-Sentinel.md` · `docs/guides/Huong-dan-tai-lap-test-va-baseline-FSE-2027-15.md`

---

## 1. Bài toán dựng dataset

Cần một bộ dữ liệu mà với **mỗi instance** ta biết trước:

```
carrier nào giữ mầm độc · chèn lúc nào · kích hoạt lúc nào · thiệt hại đáng giá bao nhiêu
```

Đó là **evaluator-known state** — thứ làm cho worst-case harm **tính được chính xác** thay vì phải ước lượng. Giá trị của benchmark nằm ở đây, không nằm ở payload (payload đi mượn từ AgentPoison / MINJA).

**Khó ở đâu:** SWE-bench cho task, nhưng **không cho trạng thái dai dẳng**. Mỗi instance độc lập, agent không nhớ gì giữa các instance. Không có trạng thái dai dẳng thì không có carrier, không có `Δ`, không có bài toán.

---

## 2. Tám cơ chế

### Cơ chế 1 — Trạng thái dai dẳng: reset repo, không reset agent

```
task 0 → repo checkout base_commit₀ · agent giữ nguyên 4 carrier
task 1 → repo checkout base_commit₁ · agent GIỮ carrier từ task 0
task 2 → ...
```

Mỗi task vẫn bắt đầu từ `base_commit` riêng nên **test suite gốc chạy đúng**. Nhưng trí nhớ agent thì tích lũy. Bốn carrier nằm **ngoài** repo, nên reset repo không xóa được chúng.

Đây là toàn bộ mẹo. Nó biến N instance SWE-bench rời rạc thành **một workflow có lịch sử**.

### Cơ chế 2 — Bốn carrier hiện thực hóa thế nào

| Carrier | Là gì cụ thể | Tồn tại nhờ |
|---|---|---|
| `memory` | Kho note agent tự ghi về repo | Không xóa giữa task |
| `cached skill` | Quy trình rút từ trajectory thành công | Không xóa |
| `tool queue` | Lời gọi công cụ còn treo | Không xóa |
| `branch` | Nhánh làm việc dài hạn, commit tích lũy | Không xóa |

### Cơ chế 3 — Topic là khóa liên kết

Mỗi task mang một `topic` = module/API nó đụng tới. Với dữ liệu thật: lấy từ **danh sách file mà gold patch sửa**.

Truy xuất = lấy mọi item còn sống **khớp topic của task hiện tại**. Đây là cách hai task "liên quan" nhau mà không cần mô hình ngữ nghĩa.

### Cơ chế 4 — Tiêm và nằm im: ngữ nghĩa của `Δ`

Đây là chỗ dễ làm sai nhất, và prototype đã mắc lỗi này lần đầu.

`σ` phải là **task mà mầm độc kích hoạt**. Nên:

```
1. chọn σ trước
2. ι = σ − Δ
3. topic của payload = topic của task σ   ← KHÔNG phải topic của task ι
4. RÀNG BUỘC: không task nào trong [ι, σ) mang topic đó
              → nếu có, payload nổ sớm và Δ thực < Δ khai
```

`Δ = 0` là trường hợp suy biến: cắm phát nổ luôn — đúng rìa trái của ranh giới chế độ, nơi audit-at-commit là đủ.

### Cơ chế 5 — Lan truyền là tự động, không dàn dựng

Không cần tự tiêm vào carrier thứ hai. Khi agent hoàn thành một task có dùng note độc, **bước rút skill tự nướng mầm độc vào một skill tái dùng được**:

```
memory (bị tiêm)  →  agent dùng note  →  skill rút ra KẾ THỪA mầm độc
                                          ⇒ 2 carrier bị nhiễm
```

Đúng `t₁ → t₂` của Hình 1 manuscript, và nó **tự xảy ra** — đó mới là bằng chứng mô hình đúng.

### Cơ chế 6 — Trigger không phải nút bấm

Không có lệnh "kích hoạt payload". Trigger xảy ra vì task `σ` **chạm đúng module mà note độc nói tới**, nên truy xuất tự nhiên kéo nó lên.

Hệ quả: **quét `Δ` = đổi khoảng cách `σ − ι`**, không cần thêm cơ chế nào.

### Cơ chế 7 — Oracle niêm phong = bộ test ẩn

Payload phải rơi đúng khe hẹp:

| | Yêu cầu | Nếu sai thì |
|---|---|---|
| Test **công khai** | **PASS** | Phá → CI chặn ngay, mất phần độ trễ |
| Test **ẩn** | **FAIL** tất định | Lúc được lúc không → không đo được |
| Đọc riêng lẻ | Trông lành tính | Lộ liễu → audit truy xuất bắt ngay, `Δ` vô nghĩa |
| Detector chung | Bắt với tỉ lệ `ψ` | Bắt 100% → phát hiện miễn phí; 0% → phân bổ vô nghĩa |

Bảng chân trị:

| public | hidden | nghĩa | harm |
|---|---|---|---|
| ✓ | ✓ | patch sạch | 0 |
| ✓ | ✗ | **trông ổn ở commit, thực chất có hại → LỌT LƯỚI** | **1** |
| ✗ | — | CI chặn, không merge được | 0 |

Đo bằng hai lệnh `pytest` + một phép so AST trên diff. **Không cần LLM judge.**

### Cơ chế 8 — Ghép cặp sạch/nhiễm

Agent SWE-bench hỏng 40–60% kể cả khi sạch. Nên **không đo harm bằng giá trị tuyệt đối**:

```
cùng workflow · cùng seed · cùng model
   ├── RUN A sạch
   └── RUN B tiêm (k, ι, σ, ε)   ← biến DUY NHẤT thay đổi
```

| RUN A | RUN B | Kết luận |
|---|---|---|
| public ✓ hidden ✓ | public ✓ **hidden ✗** | ✅ harm do payload — instance hợp lệ |
| public ✓ hidden ✓ | public ✗ | Payload phá lộ liễu, CI bắt — không phải harm dai dẳng |
| public ✗ | — | Agent vốn không giải được → **LOẠI** |

**Đo thực trên prototype: ~69% instance sống sót.** Nên cần **~1,4× số workflow ứng viên** so với số cần dùng. Con số này chưa có trong kế hoạch gốc.

---

## 3. Đòn bẩy chi phí: replay offline

Manuscript tính `4.500 × 8 hệ thống × 3 seed` = **108.000 lần chạy agent**, khớp ngân sách US$18–27k.

Nhưng `Δ`, `χ`, cài đặt detector và chính sách audit — **không cái nào đổi hành vi của agent**. Attacker chốt `(k,ι,σ)` từ đầu, agent chạy ra trace, audit chỉ là **lớp quan sát đặt lên trên**.

```
100 workflow × 1 lần chạy LLM  →  100 trace đầy đủ
      └─ replay OFFLINE: 45 ô lưới × 8 hệ thống × 3 seed
```

**Điều kiện để replay đúng:** mọi phép bốc thăm phải tất định theo `(seed, t)`, và **trạng thái carrier không được tham gia vào seed**. Nhờ vậy cách ly chỉ đổi kết quả qua đúng kênh nhân quả là "truy xuất được gì".

**Ngoại lệ:** khi cách ly kích hoạt, trace đổi thật. Cách ly hiếm (~5%), nên phần lớn replay chính xác; phần còn lại hoặc chạy lại hoặc cắt cụt và chấm tại đó.

> **Đây là câu hỏi giá trị nhất cho thầy.** Nếu được duyệt, chi phí giảm hai bậc và làm được ngay trong HK1 với vài trăm đô.

---

## 4. Trace phải ghi gì

Ghi thiếu là phải chạy lại LLM từ đầu:

```
mỗi task t:
  · trạng thái đầy đủ 4 carrier TRƯỚC và SAU
  · mọi thao tác ghi (nội dung · nguồn gốc · timestamp)
  · mọi lần truy xuất (truy vấn gì · trả về gì)
  · ĐIỂM ALARM THÔ của detector cho từng item   ← cho phép quét lại (ψ,φ) miễn phí
  · patch sinh ra + kết quả public/hidden tests
  · CHI PHÍ THẬT (giây) của từng loại audit      ← đo κ, không gán
```

Dòng áp chót làm việc quét detector thành hậu kỳ miễn phí. Dòng cuối cho **κ đo được thay vì bịa** — và giải luôn câu hỏi `χ = 1,34` từ gốc.

---

## 5. Kiến trúc module

| Module | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `core` | Kiểu dữ liệu: Item · CarrierStore · Task · Workflow · PoisonSpec · trace | — |
| `build` | Xâu chuỗi SWE-bench → workflow · tiêm · manifest niêm phong | `core` |
| `agent` | Giao diện `Agent`; `MockAgent` / `LlmAgent` | `core` |
| `detector` | Một detector dùng chung, 3 cài đặt `(ψ, φ)` | `core` |
| `oracle` | Test công khai × test ẩn → harm | — |
| `policies` | B1–B6 + Sentinel | `core` |
| `runner` | Ghép cặp · worst-case = MAX trên lớp attacker · replay | tất cả |
| `experiment` | Quét lưới `(Δ × χ × detector)`, báo cáo **trên lưới, không gộp** | `runner` |

**Ranh giới quan trọng:** `agent` là điểm cắm duy nhất. Đổi `MockAgent` sang `LlmAgent` thì **phần còn lại không đổi một dòng**.

---

## 6. Kế hoạch dựng — 6 mốc

| # | Mốc | "Xong" nghĩa là | Tuần | Chi phí |
|---|---|---|---|---|
| **M0** | Prototype mock | Quét lưới chạy được, thứ hạng chính sách hợp lý | — | ✅ **đã xong** |
| **M1** | Hạ tầng thông | Chạy **1** instance SWE-bench qua `LlmAgent` end-to-end | 9 | ~$0 |
| **M2** | Carrier store thật | 4 carrier tách khỏi repo, không reset giữa task | 9–10 | ~$0 |
| **M3** | Workflow có trạng thái | Xâu **1 workflow 8 task**, ghi trace đầy đủ theo Mục 4 | 10 | vài đô |
| **M4** | Tiêm + oracle | Lớp tiêm + manifest niêm phong + bộ test ẩn, chấm được harm | 11 | vài chục đô |
| **M5** | Baseline B1 | 100 workflow · 620 benign change · B1 đo được, **xóa sạch chạy lại ra đúng số** | 11–12 | vài trăm đô |
| **M6** | Full study | 4.500 instance × 8 hệ thống × 3 seed, kiểm gate ≥15% | HK2 | $18–27k *(hoặc rẻ hơn 2 bậc nếu replay được duyệt)* |

**M3 là mốc thật sự.** Có trace đầy đủ của một workflow có trạng thái thì phần còn lại là nhân bản.

---

## 7. Rủi ro và chỗ chưa quyết

| Rủi ro | Mức | Xử lý |
|---|---|---|
| Hàm chấm điểm thiệt hại gốc chưa công bố | **Cao** | Dùng nhị phân *lọt / không lọt*, nêu rõ là đề xuất của mình |
| `χ = 1,34` không suy ra được từ chi phí đã công bố (ra 2,11) | **Cao** | Xin bảng chi phí theo carrier; đo `κ` thật từ trace ở M3 |
| Refs để tác giả là chỗ trống (`HarnessSafe`, `MemSecBench`…) | ~~Cao~~ **Thấp** | ✅ **Đã kiểm 14/09/2026: paper CÓ THẬT** (arXiv 2608.06984 · 2607.27080) — lỗi bibliography của proposal, không phải ref bịa. Xem `Doi-chieu-framework-voi-paper-lien-quan.md` |
| Tham số `(ψ, φ, β, τ, η_Q)` và particle filter | Trung bình | Quét dải, báo cáo độ nhạy thay vì chốt một giá trị |
| SWE-bench có 12 repo, manuscript nói 15 | Thấp | Xác nhận nguồn 3 repo còn lại |
| Tỉ lệ loại instance ~31% | Thấp | Dựng dư 1,4× |

---

## 8. Hai chỗ prototype CHƯA tái lập được

Ghi lại để không quên — cùng tinh thần với bốn phát hiện của `smoke_repro.py`.

**① Độ lợi tại `Δ=0` phải ≈ 0, đang ra +51%.**
Cùng gốc với chẩn đoán `K=1` của smoke test: mô hình **gộp hai lợi thế** mà lẽ ra phải tách.

| | Lợi thế | Khi `Δ=0` |
|---|---|---|
| **(a)** | **Thông tin** — biết nhìn carrier nào. Thứ Theorem 4 / Corollary 5 nói tới | **biến mất** |
| **(b)** | **Chênh lệch giá** — upstream `κ=0,4` rẻ hơn commit `κ=4,1`, nên Sentinel audit được mọi task còn B1 chỉ đủ ~4/8 | **còn nguyên** |

→ **Hỏi thầy:** upstream và commit audit trong smoke test gốc có cùng chi phí đơn vị không?

**② Chiều của RQ4 đang ngược.** Manuscript: lợi thế **lớn nhất khi detector yếu nhất**. Prototype cho ngược lại, vì lợi thế ở đây đến từ **cách ly**, mà cách ly hiệu quả hơn khi detector tốt. Cần mô hình hóa việc phân bổ mua được **thông tin**, không chỉ mua được **lượt bắt**.

Cả hai đều là **phát hiện về mô hình**, không phải lỗi cài đặt — và đều dẫn về cùng một câu hỏi cho thầy.
