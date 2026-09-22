# Đối chiếu framework test với paper liên quan

Kiểm ngày 14/09/2026. Mục đích: framework của mình có đang làm theo chuẩn cộng đồng không, chỗ nào lệch, và lệch đó là **có lý** hay là **thiếu sót**.

---

## 0. Đính chính: HarnessSafe và MemSecBench CÓ THẬT

Trước đây tôi xếp hai cái này vào nhóm "reference khả nghi" vì trong danh mục tham khảo của proposal, tác giả để là `HarnessSafe Authors` / `MemSecBench Authors`. Kiểm lại:

| Ref | arXiv | Trạng thái |
|---|---|---|
| HarnessSafe [10] | **2608.06984** | ✅ có thật — 328 case, 7 họ carrier dai dẳng |
| MemSecBench [16] | **2607.27080** | ✅ có thật — 310 case, 48 bối cảnh |

Đó là **lỗi bibliography của proposal**, không phải paper bịa. Hệ quả: mục rủi ro trong `Thiet-ke-AuditGame-SE.md` §7 ghi *"chỉ dựng trên AgentPoison + MINJA"* — **sai, phải sửa**. Hai benchmark này gần đề tài hơn AgentPoison nhiều: HarnessSafe làm đúng khái niệm **carrier dai dẳng**, MemSecBench làm đúng khái niệm **nằm im rồi phát tác**.

---

## 1. Chuẩn cộng đồng: Agentic Benchmark Checklist (ABC)

`arXiv 2507.02825` — Zhu và cộng sự, *Establishing Best Practices for Building Rigorous Agentic Benchmarks*. Đây là thứ gần nhất với "chuẩn" cho việc mình đang làm. Kết luận của họ: lỗi thiết kế benchmark làm sai lệch hiệu năng **tới 100% tương đối**.

Ba nhóm của ABC **trùng khớp** ba cổng tôi đã thiết kế — đây là xác nhận độc lập, không phải tôi vẽ theo:

| Cổng của tôi | Nhóm ABC | Ghi chú |
|---|---|---|
| 1 · Liêm chính | **Task Validity** (T.1–T.10) | "task giải được **khi và chỉ khi** agent có năng lực cần đo" |
| 2 · Hiệu lực | **Outcome Validity** (O.a–O.i) | "kết quả chấm **thực sự** chỉ ra task thành công" |
| 3 · Đủ mạnh | **Reporting** (R.1–R.13) | thống kê · baseline · null control |

### Những ô ABC mà tôi đã có

| ABC | Nội dung | Chỗ tương ứng |
|---|---|---|
| **T.5** | *Isolate agents from ground truth* | N1 — bỏ `poisoned` khỏi `fires()` |
| **T.6** | *Freeze environment setup* | hash-freeze cấu hình |
| **T.10** | *Inspect outliers in pilot* | đúng cách tôi xử `Δ=0` ra +51% |
| **O.f.2** | *Eliminate non-determinism* | cổng 1 — và nó bắt được bug `hash()` |
| **R.10** | *Report statistical significance* | bootstrap ghép cặp + CI |
| **R.12** | *Appropriate baseline comparisons* | B1–B6 |
| **R.13** | *Report trivial/null control results* | control C1/C2/C3 |

**R.13 đáng chú ý:** ABC đưa null control thành **yêu cầu bắt buộc khi báo cáo**, vì τ-bench từng bị agent *không làm gì* vượt **38%** số task. Tôi đã có nó ở cổng 2 vì lý do riêng — hóa ra trùng chuẩn.

### Con số ABC tìm được ở các benchmark khác

| Benchmark | Lỗi | Sai lệch |
|---|---|---|
| τ-bench | trả lời rỗng vẫn tính đúng | **+38%** |
| τ-bench | liệt kê mọi đáp án vẫn tính đúng | **+40%** |
| KernelBench | fuzz thiếu ca biên | **+31%** |
| CVE-Bench | khớp chuỗi ngây thơ với SQLi theo thời gian | **+32,5%** |
| OSWorld | selector HTML hỏng | **−28%** |
| **SWE-Lancer** | **agent đọc được file test → 100% mà không giải** | hỏng hoàn toàn |
| **SWE-bench Verified** | **test case không đủ** | — |

Hai dòng cuối **trỏ thẳng vào oracle của tôi** — xem Mục 4.

---

## 2. Bảng đối chiếu phương pháp

| | AgentDojo | AgentPoison | MINJA | HarnessSafe | MemSecBench | **AuditGame-SE** |
|---|---|---|---|---|---|---|
| arXiv | 2406.13352 | 2407.12784 | 2503.03704 | 2608.06984 | 2607.27080 | *(đang dựng)* |
| Quy mô | 97 task · 629 ca | — | — | 328 ca | 310 ca · 48 bối cảnh | 100 wf × H |
| Chấm bằng | **hàm kiểm tất định** | ASR truy xuất/hành động | ISR + ASR | **bằng chứng thực thi** | **7 checkpoint** | test ẩn (tất định) |
| Không dùng LLM judge | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Đo **tiện ích** song song | ✅ *utility under attack* | ✅ *benign drop 0,74%* | — | — | ✅ *F2 giữ bộ nhớ lành* | ❌ **THIẾU** |
| Nhiều giai đoạn, không nhị phân | — | ASR-r/a/t | ISR/ASR | ✅ tiến trình chuỗi | ✅ W·E·F | ❌ **THIẾU** |
| Trạng thái dai dẳng xuyên task | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Độ trễ kích hoạt là **biến quét** | — | — | — | có lifecycle | có, không quét | ✅ **`Δ` — riêng của mình** |
| Phòng thủ **cùng ngân sách** | — | — | — | — | — | ✅ **riêng của mình** |
| Attacker **best-response** | ⚠ adaptive attack | — | — | — | — | ⚠ **xem Mục 5** |

Hai dòng cuối là **chỗ đứng của đề tài**: chưa benchmark nào coi **độ trễ là trục quét** và chưa ai **ép mọi phòng thủ dùng chung một ngân sách**. Đóng góp thật, không phải làm lại.

---

## 3. Ba thứ họ làm mà mình đang thiếu

### 3.1 · Chấm nhiều giai đoạn, không phải nhị phân ⚠ NẶNG

HarnessSafe nói thẳng: **"attack success rates cannot reflect distinct lifecycle progression patterns"** — ASR nhị phân không phân biệt được chuỗi tấn công bị chặn ở đâu.

MemSecBench chia làm **7 checkpoint**:

```
WRITE     W1 ghi được vào bộ nhớ    W2 ngữ nghĩa độc còn sống
EXECUTE   E1 được truy xuất         E2 được ÁP DỤNG        E3 gây hậu quả ra ngoài
FORGET    F1 xóa được mầm độc       F2 GIỮ NGUYÊN phần lành
```

Số của họ cho thấy vì sao chia nhỏ lại quan trọng:

| | | |
|---|---|---|
| MPSR — ghi vào được | **84,2%** | |
| E1 — được truy xuất | 76,1% | |
| **E2 — được áp dụng** | **53,7%** | ⬅ **nút thắt thật sự** |
| E2E-ASR | 50,3% | |

Nếu chỉ nhìn ASR = 50,3% thì **không biết** nút thắt nằm ở bước áp dụng. Cùng logic, `harm` nhị phân của tôi **không nói được audit chặn ở đâu** — mà với một bài về **phân bổ audit** thì "chặn ở giai đoạn nào" chính là tín hiệu cần nhất.

**Sửa:** giữ `harm` nhị phân làm chỉ số chính, thêm checkpoint tiến trình:
```
P1 payload còn sống tới σ     P2 được truy xuất tại σ
P3 được áp dụng vào patch     P4 vượt test công khai     P5 fail test ẩn = harm
```
Có P1–P5 thì mới trả lời được *Sentinel thắng B1 nhờ chặn sớm hơn, hay nhờ chặn nhiều hơn* — câu mà thầy chắc chắn sẽ hỏi.

### 3.2 · Tiện ích lành tính ⚠ NẶNG

AgentDojo có **utility under attack**. AgentPoison khoe **benign drop chỉ 0,74%**. MemSecBench có **F2 = giữ được bộ nhớ lành**, và tìm ra khoảng cách **86,3% → 62,5%**: xóa được mầm độc thì dễ, xóa mà **không phá phần lành** mới khó.

Hàm mất mát của đề tài có **ba** số hạng:
```
L = E[verified harm] + λ_Q·E[cách ly nhầm] + λ_T·E[task sạch bị mất]
                        └──────────── ĐANG KHÔNG ĐO ────────────┘
```

Prototype chỉ đo số hạng đầu. Nghĩa là một chính sách **cách ly sạch trơn mọi thứ** sẽ đạt `harm = 0` và **thắng tuyệt đối** — trong khi nó vô dụng. Đây không phải thiếu sót nhỏ, nó là **lỗ hổng cho phép thắng bằng cách gian lận**, đúng loại mà ABC O.g.3 và R.13 sinh ra để chặn.

**Sửa:** ghi `false_quarantine` và `clean_tasks_lost` vào trace, báo cáo **cả ba số hạng**, và thêm một baseline **"cách ly tất cả"** làm null control — nó phải **thua** rõ ràng, nếu không thì hàm mất mát sai.

### 3.3 · Oracle solver và kiểm nhiễm dữ liệu

- **ABC T.9** — cần một *automatic Oracle solver* chứng minh task giải được. Với mình: chạy **gold patch** của SWE-bench, phải đạt public ✓ **và** hidden ✓. Nếu gold patch fail test ẩn thì **test ẩn sai**, không phải agent sai. Chưa có.
- **ABC R.3** — chống nhiễm dữ liệu. SWE-bench nằm trong dữ liệu huấn luyện của mọi model hiện đại. Chưa xử.

---

## 4. Mối đe dọa trực tiếp tới oracle niêm phong

Hai phát hiện của ABC đánh đúng vào thiết kế oracle của tôi:

**① SWE-Lancer: agent đọc được file test → đạt 100% mà không giải gì.**
Oracle của tôi **dựa hoàn toàn** vào việc test ẩn nằm ngoài tầm với. Nhưng agent của tôi có **branch carrier dai dẳng** và **tool queue** — nhiều đường chạm tới filesystem hơn agent SWE-bench thường. Test ẩn phải nằm **ngoài container**, chấm sau khi horizon đóng. Cần một test riêng: *agent không có đường nào đọc được test ẩn*.

**② SWE-bench Verified dùng test case không đủ; agent pass mà patch không đúng — 7,7% (Lite) / 5,2% (Verified).**
Harm của tôi định nghĩa là `public ✓ ∧ hidden ✗`. Nếu test công khai yếu thì `public ✓` **không có nghĩa là giải được** — và harm bị quy gán nhầm. Tệ hơn: chính cái yếu đó là thứ payload khai thác, nên **sai số này không ngẫu nhiên, nó thiên vị theo hướng làm harm cao lên**.

> Đây là lý do mạnh để dùng **SWE-bench Verified** thay vì Lite, và để nói rõ trong luận văn rằng harm được đo **trên nền test công khai có sai số đã biết 5,2%**.

---

## 5. Một chỗ mình mạnh hơn họ — và một chỗ yếu hơn mình tưởng

**Mạnh hơn:** MemSecBench **cố ý không dùng ghép cặp sạch/nhiễm**. Họ phân nhánh Execute và Forget *từ cùng một trạng thái đã nhiễm được xác minh*. Cách đó xác minh **tấn công đã cắm được**; cách của tôi xác minh **task vốn giải được**. Hai cái **bù nhau, không thay nhau** — nên lấy cả hai:

```
cổng A (kiểu MemSecBench)  payload thực sự sống tới σ    → nếu không, attack không thành lập
cổng B (kiểu của tôi)      run sạch giải được task       → nếu không, LOẠI instance
chỉ instance qua CẢ HAI mới vào mẫu
```

**Yếu hơn mình tưởng:** văn liệu adaptive attack rất rõ — đánh giá phòng thủ trước **lớp tấn công đóng băng** thì **luôn lạc quan**. `worst_case` của tôi lấy MAX trên lớp `{memory, skill} × {0,1,2,4}`, và `plan_poison` **không hề nhìn chính sách phòng thủ**.

Với một bài **Stackelberg** thì đây là vấn đề nguyên tắc, không phải kỹ thuật: toàn bộ tiền đề là attacker **quan sát được phân bố** của defender rồi **best-response**. Attacker hiện tại không best-response, nên con số "worst-case" đang **lạc quan có hệ thống** — đúng thứ mà defender được lợi.

**Sửa:** thêm một attacker **best-response**: cho nó biết phân bố chính sách (không biết lần tung), chọn `(k, ι, σ)` cực đại hóa harm kỳ vọng. Đây mới đúng nghĩa SSE. Baseline `max` trên lớp liệt kê giữ lại làm **cận dưới**.

---

## 6. Kết luận — thứ tự làm đã đổi

| Ưu tiên | Việc | Vì sao lên/xuống |
|---|---|---|
| **1** ⬆ | Đo **cả ba** số hạng hàm mất mát | đang có đường thắng bằng gian lận (§3.2) |
| **2** ⬆ | Checkpoint P1–P5 | HarnessSafe: ASR nhị phân không đủ (§3.1) |
| **3** ⬆ | Attacker **best-response** | tiền đề Stackelberg đang không được thỏa (§5) |
| **4** = | N1–N4 (bốn đường nối) | giữ nguyên |
| **5** = | Cổng 1: tất định, `hash()` | giữ nguyên |
| **6** ⬇ | Control C1–C5 | vẫn cần, nhưng §3.2 khẩn hơn |
| **7** mới | Oracle solver bằng gold patch (ABC T.9) | rẻ, bắt được test ẩn sai |
| **8** mới | Test "không đường nào đọc được test ẩn" | SWE-Lancer hỏng vì đúng chỗ này |

**Ba việc đầu đều là thứ paper liên quan đã làm mà mình chưa.** Không phải tinh chỉnh — là lỗ hổng làm kết quả không đứng được trước phản biện.

---

## Nguồn

- [Establishing Best Practices for Building Rigorous Agentic Benchmarks (arXiv 2507.02825)](https://arxiv.org/abs/2507.02825)
- [AgentDojo (arXiv 2406.13352)](https://arxiv.org/abs/2406.13352)
- [AgentPoison (arXiv 2407.12784)](https://arxiv.org/abs/2407.12784)
- [MINJA — Memory Injection Attacks via Query-Only Interaction (arXiv 2503.03704)](https://arxiv.org/abs/2503.03704)
- [HarnessSafe (arXiv 2608.06984)](https://arxiv.org/abs/2608.06984)
- [MemSecBench (arXiv 2607.27080)](https://arxiv.org/abs/2607.27080)
- [Adaptive Attacks Break Defenses Against Indirect Prompt Injection (NAACL Findings 2025)](https://aclanthology.org/2025.findings-naacl.395.pdf)
