# Plan các phần đến hạn nộp — 25/09 → 02/10/2026

**Hạn:** FSE 2027 Research Papers, **02/10/2026 AoE** (trưa 03/10 giờ VN). Còn 8 ngày tính cả hôm nay.
**Đọc cùng:** [plan v2](2026-09-24-Faithful-Draft-v2-Plan.md) (Task 0–12, phần dựng và chạy) · [README](../../../README.md) §3.4 (issue) · [Evaluation](../../manuscript/Evaluation.md) · [Related Work](../../manuscript/Related-Work.md).

Plan này không lặp lại các bước của plan v2. Nó làm ba việc: (1) chốt phạm vi, gồm ba hạng mục **không làm trước hạn** và cách khai chúng ở Threats; (2) xếp **các mục của bài** chạy song song với phần dựng v2; (3) nêu những quyết định đang chặn.

---

## 1. Phạm vi: ba hạng mục ra khỏi bản nộp, khai ở Threats

| # | Hạng mục | Hiểu là | Không làm, nghĩa là | Đã có gì để khai |
|---|---|---|---|---|
| **T-A** | Agent LLM thật | Chạy lưới chính với agent LLM thay cho MockAgent | Mọi số harm vẫn là harm **dưới mô hình tiếp nhận của MockAgent** | Pilot P2: `deepseek-v4.1-flash`, $T = 0$, 14 instance, 7 chấm được, **tuân thủ 0/7**. Arm control: 6/14 patch sạch (agent không bất tài). Arm ceiling (lời khuyên ~300 ký tự có lập luận): 5 instance, 3 chấm được, **tuân thủ 0/3** (`spikes/p2-pilot.jsonl`, `p2-control.jsonl`, `p2-ceiling-raw.jsonl`) |
| **T-B** | Workflow SWE-bench thật | **Thực thi** task trên repo thật: agent sửa code thật, nền lành tính là ghi chú của agent thật, harm chấm bằng test ẩn thật (item C/D, W9) | Workflow **thật về trình tự và topic** (metadata SWE-bench, `corpus_v2`), **mô phỏng về thực thi** | M3 chạy 8 instance `pytest` end-to-end (12,6 s, hạ tầng chạy được). Test ẩn viết tay 15/500 = 3,0%. Nền lành mock: trung vị 62 ký tự, còn 18–42 ký tự cho lời khuyên, 1/15 task không còn chỗ. $\Delta$ đo trên repo thật: chỉ 19% instance có $\Delta \ge 2$ |
| **T-C** | Attacker LLM | Ba attacker LLM (A1 informed, A2 hybrid, A3 adaptive) trong lớp attacker đã khai | Lớp attacker = **18 luật kịch bản + best response liệt kê**. Mọi bảo đảm phát biểu với lớp này | Spike 20/09, **trước đóng băng**: nội dung A0 (bịt mắt) qua cổng, AUC 0,465–0,502, 20/20 split. Nội dung A1/A2 (được cho biết $\pi_D$) **trượt cổng** ở mọi $\Delta$: trung vị AUC 0,59–0,76, 0/20 split (`spikes/attacker-llm-a1a2.json`). A3 chưa chạy |

**Cách đọc T-B.** Plan v2 viết "100 workflow thật" và Task 2 vẫn làm như đã định: trình tự theo `created_at`, topic lấy từ gold patch, 17 repo. Cái **không** làm là thực thi. Trong bài phải dùng đúng cặp chữ *"real in sequence and topic, simulated in execution"*, tránh để người đọc hiểu "workflow thật" là agent đã chạy trên repo.

### 1.1 Luật đi kèm

1. **Không một task nào của plan v2 được gọi LLM.** Soát lại: Task 3 dùng `StagedMockAgent`, Task 5 dùng 18 luật kịch bản, Task 2 chỉ đọc metadata. Đúng như thế, nên plan v2 **không phải cắt gì** vì phạm vi này.
2. **Số từ pilot chỉ vào Threats, không vào bảng kết quả.** Mỗi số trích phải có con trỏ file (luật II.4). Riêng T-C, chỉ trích **AUC cổng**: cổng v2 là một phần của manifest và `validity_check` trong file đã khớp tham chiếu. **Không** trích cột `harm_axis`: nó chạy trên ngân sách 17,95 cũ, trước đóng băng.
3. **Không mở spike mới** cho ba hạng mục này trước 02/10. Cả ba vào mục Future work cùng một câu về major revision.

---

## 2. Một lỗi phải chặn trước Task 3 của v2

Plan v2, Task 3 (`world_v2.py`) gieo lượt rút của agent bằng `seed_of(seed, t)`, `seed_of(seed, t, "solve")` và `seed_of(seed, t, "drift-v2", c)`, **không có `wf_id`** (dòng 832, 874, 884 của plan v2). Đó chính là **issue #20** của v1: với một seed, task thứ $t$ của cả 100 workflow nhận cùng một kết cục, và CI bootstrap theo workflow hẹp hơn thật.

v2 là mã mới, v1 không bị sửa, nên sửa ở v2 **không tốn gì**:

- [ ] Thêm `wf_id` vào cả ba lời gọi `seed_of` trong `StagedMockAgent`. Sửa luôn test "open gates reproduce MockAgent": so với một `MockAgent` cũng gieo theo `wf_id`, hoặc ghi rõ phép so khớp chỉ đúng khi cố định một workflow.
- [ ] Ghi một dòng vào tiền đăng ký v2 (Task 0) **trước** khi viết mã: *"v2 agent seeds include wf_id; v1 does not (issue #20)."*
- [ ] Còn v1 thì quyết theo #20 (§5). Nếu bài chạy bằng số v2 thì #20 chỉ còn là một dòng Threats về bản dự phòng.

---

## 3. Các mục của bài

Thứ tự viết đi theo **phụ thuộc**, không theo thứ tự trong bài. Model và Design mô tả thiết lập v2, nên viết được ngay khi tiền đăng ký v2 đã chốt. Evaluation và Intro thì phải chờ số.

| Mục | Nội dung | Nguồn | Phụ thuộc | Ngày | Xong khi |
|---|---|---|---|---|---|
| **§3 Model** | Trò chơi Stackelberg; carrier, bốn giai đoạn $(stage, depth)$; ngữ nghĩa audit **chặn ở cổng** (Q3); $\eta_Q$ là ngưỡng Bayes $\lambda_Q/(1+\lambda_Q)$ (Q5); $L$ và bốn tỉ số không thứ nguyên; attacker tổng-không trên $L$ | [Methodology](../../AuditGame-SE_Sentinel_Methodology_Full.md), plan v2 Q1–Q5 | Task 0 v2 (tiền đăng ký) | **26/09** | Mọi ký hiệu dùng ở §4–§6 đều được định nghĩa ở đây. Không có số kết quả |
| **§4 Design** | Benchmark: `corpus_v2` (17 repo, H 6–14, dev = django), 18 attacker / 7 held-out, oracle marker, cổng AUC v2, ba cổng kiểm thử, manifest đóng băng. Chính sách: B1–B6, thư viện 28, Sentinel-A1 | plan v2 Task 1–9, README §1 | Task 2, 5 có mã | **27/09** | Mỗi thành phần có một dòng "vì sao thế này" và trỏ tới tiền đăng ký |
| **§6.7 Threats** | T-A, T-B, T-C (bản nháp ở §4 dưới) + các mục cũ đã sửa | §1 của plan này | Không | **25/09** | Bản nháp vào `Evaluation.md` |
| **§7 Related Work** | Đã có nháp. Việc còn lại: nối T-C với #24 *Adaptive Attacks Break IPI Defenses* và #25 *The Attacker Moves Second*; sửa 2 mục phải viết lại theo §7.7 | [Related-Work.md](../../manuscript/Related-Work.md) | Không | **28/09** | Không còn mục `[verify]` |
| **§6 Evaluation** | Viết lại theo v2: Bảng 2 (5 chỉ số), Bảng 3 (4 ablation), RQ1–RQ4, crossover, kiểm độ nhạy. **Dựng vỏ bảng và chú thích trước khi có số** | plan v2 Task 12 | Task 12 v2 (30/09) | vỏ **29/09**, số **30/09** | Mọi số trỏ tới một file trong `spikes/v2/` |
| **§1 Intro + Abstract** | Đóng góp, phát biểu theo khung đã chốt (§5) | Bảng ánh xạ kết cục → khung | #13 **và** số v2 | **30/09** | Đóng góp nào cũng có một RQ và một bảng |
| **§8 Discussion / Future work** | Ba hạng mục T-A/B/C thành ba hướng major revision; W8 (AgentPoison/MINJA) | §1 | Không | **29/09** | ≤ nửa trang |
| **Artifact ẩn danh** | Bỏ tên học viên và GVHD, bỏ README tiếng Việt khỏi gói, giữ `frozen/MANIFEST.json` và hướng dẫn chạy lại ba bảng | README "Chạy" | Đóng băng v2 | **01/10** | Chạy lại được từ một clone sạch |

### 3.1 Sửa những chỗ đã cũ trong `Evaluation.md` §6.7 (làm cùng hôm nay)

- *"Horizon and corpus are confounded … we have not done it"* → **đã tách** (issue #15, kết quả H2: hiệu ứng mẫu, không phải chân trời). Viết lại thành một câu về độ bền theo mẫu ở $N = 40$.
- *"593 of 593"* → **624/624** ở bản v1 đóng băng. Khi có v2 thì cập nhật số của v2.
- Mục *"The agent is a mock agent"* được thay bằng T-A (§4), vì bản cũ thiếu arm control và arm ceiling. Hai arm đó làm yếu cách giải thích "agent bất tài" (6/14) và "lời khuyên quá ngắn" (chỉ 0/3, mẫu rất nhỏ, không đủ để nói là loại được).

---

## 4. Bản nháp Threats cho ba hạng mục (tiếng Anh, dán thẳng vào §6.7)

> **T-A — The agent is simulated, and a real one did not take the bait.**
> Every harm number in this paper is harm under the mock agent's reception
> model, in which a retrieved poisoned item is acted on with probability one.
> We tested that assumption once, with a real LLM agent (`deepseek-v4.1-flash`,
> temperature 0) on 14 SWE-bench instances: of the 7 that could be scored, the
> agent followed the injected advice in **0**. Two further arms speak against the
> obvious explanations, though on small samples. Without injection the same agent produced a clean patch
> on 6 of 14 instances, so it is not failing to work. Given longer, reasoned
> advice (about 300 characters) it adopted it in 0 of the 3 scorable instances
> out of 5. The absolute harm
> values are therefore upper bounds on what a current reasoning model would
> suffer. The policy *comparisons* survive only if the reception probability does
> not depend on the audit policy; we argue this but have not measured it. Running
> the main grid with a real agent is the threat we would most like to remove.
> (`spikes/p2-pilot.jsonl`, `p2-control.jsonl`, `p2-ceiling-raw.jsonl`)

> **T-B — Workflows are real in sequence and topic, simulated in execution.**
> Workflows are built from SWE-bench Verified and Multilingual metadata: tasks
> are ordered by creation date within a repository, topics come from the gold
> patch, and retrieval uses those topics. No task is executed. The agent does not
> edit the repository, the benign background is written by the mock agent
> rather than by an agent working on the code, and harm is scored by a sealed
> marker oracle; hand-written hidden tests cover 15 of 500 instances (3%). Two
> measured facts suggest the gap is not neutral. First, the mock background is
> short (median 62 characters), which leaves a payload 18–42 characters for its
> advice once it has matched the topic; a real agent's notes run to hundreds of
> characters and would relax that budget in a direction we have not measured.
> Second, measured on the cloned repositories, only 19% of instances have a
> trigger delay $\Delta \ge 2$, so the delays in our grid are more common here
> than in the corpus. End-to-end execution is built and runs on 8 `pytest`
> instances; it was not run at scale.

> **T-C — The attacker class contains no LLM attacker.**
> The attacker class is 18 scripted rules, 7 held out, plus an exact best
> response by enumeration over carrier and placement. Every guarantee in this
> paper is stated against that class. An adaptive LLM attacker lies outside it,
> and recent work shows that adaptive attackers break defences evaluated against
> fixed ones [#24, #25]. A pilot run before the configuration was frozen,
> reported here only as context, cuts both ways. Content written by an LLM that
> was told nothing about the defence passed the benign-corpus gate (AUC
> 0.465–0.502, 20 of 20 splits). Content written by an LLM that was told the
> committed policy failed it at every $\Delta$ (median AUC 0.59–0.76, 0 of 20
> splits). Informing the attacker made its content *easier* to detect. We did not
> run the adaptive variant, which learns from what was caught. None of these
> numbers enters a result table. (`spikes/attacker-llm-a1a2.json`)

**Việc phải soát trước khi dán:** (1) T-A: ✅ đã đếm lại từ jsonl 25/09 — pilot 14 bản ghi, 7 chấm được (còn lại 5 không ra patch, 2 anchor rỗng), 0/7; control 6/14; ceiling **0/3 chấm được trên 5** (Toàn cảnh ghi "0%" trên N=5 là gộp cả 2 ca không ra patch); (2) T-B: xác nhận 15/500 và 19% vẫn đúng sau khi v2 đổi corpus sang 17 repo; con số 19% đo trên 10 repo Verified; (3) T-C: số tham chiếu [#24, #25] khớp khoá BibTeX ở Related Work.

---

## 5. Quyết định đang chặn

| # | Quyết định | Chặn mục nào | Hạn | Nếu tới hạn chưa có |
|---|---|---|---|---|
| **#13** | Khung bài: trục ngân sách / trục $\Delta$ / trục $\eta_Q$ | Intro, Abstract | **27/09 tối** | Theo đề xuất đã gửi: (1) trục ngân sách, (2) làm dự phòng |
| **Ánh xạ v2** | Kết cục v2 → khung nào. **Phải ghi vào tiền đăng ký v2 trước Task 11 (đóng băng)**, đúng luật "không chọn khung sau khi nhìn số" | Intro | **28/09**, trước khi chạy eval qua đêm | Không chạy eval cho tới khi có |
| **v1 hay v2** | Số trong bài lấy từ bản nào | Evaluation | Luật cắt của plan v2: v2 không đóng băng được hết 29/09 thì dùng v1 | v1 + bảng "chỗ lệch với draft" |
| **#20** (v1) | Sửa / giữ / bootstrap hai chiều | Chỉ ảnh hưởng nếu bài dùng v1 | 29/09 | (b): báo headline ở 10 seed, ghi vào Threats |
| **#19 G4** | 38 nhãn tay + chạy judge mức 3 | Một dòng Threats | **26/09** (hạn cứng cũ) | Mức 3 không dùng; ghi *`F_detect` chưa có tín hiệu đã đo* vào Threats |

---

## 6. Lịch gộp

Cột "dựng v2" chép từ plan v2, không đổi. Cột "viết" chạy song song, và không mục nào dồn về 01–02/10.

| Ngày | Dựng v2 | Viết | Cần thầy / cần người |
|---|---|---|---|
| **T6 25/09** | Task 0 (thêm dòng seed #20) · 1 · 2 · 3 (sửa seed) | §6.7 Threats: T-A/B/C + sửa §3.1 | Gửi thầy plan này + nhắc #13 |
| **T7 26/09** | Task 4 · gate 4.6 · 5 | **§3 Model** | G4: người gán nhãn (hạn cứng) |
| **CN 27/09** | Task 6 · 7 | **§4 Design** | **#13** chốt |
| **T2 28/09** | Task 8 · 9 · tinh chỉnh qua đêm | Related Work sửa nốt · **ghi ánh xạ v2 → khung vào tiền đăng ký** | — |
| **T3 29/09** | Task 11 đóng băng · eval qua đêm | Vỏ bảng §6 · Discussion / Future work | Quyết v1 hay v2 nếu v2 trượt |
| **T4 30/09** | Task 12 — **đóng băng số** | Điền số §6 · **Intro + Abstract** | — |
| **T5 01/10** | — | Đọc lại toàn bài · format ACM · artifact ẩn danh | Thầy đọc |
| **T6 02/10** | — | Nộp sớm trong ngày | Bấm nút |

**Nếu phải cắt**, cắt theo thứ tự: Discussion rút còn một đoạn → Related Work giữ nguyên nháp → Design trỏ sang artifact thay vì mô tả đủ. **Không cắt:** Threats (§4), vì ba hạng mục ra khỏi phạm vi chỉ đứng được khi đã khai; và vỏ bảng §6, vì 30/09 không đủ giờ để vừa dựng bảng vừa điền số.

---

**Một dòng:** agent LLM thật, workflow thực thi trên repo thật và attacker LLM ra khỏi bản nộp, khai ở Threats bằng ba đoạn đã có số đo và con trỏ file. Plan v2 không cần cắt gì vì phạm vi này, nhưng **Task 3 phải gieo seed theo `wf_id`**, nếu không v2 mang lại đúng lỗi #20. Model, Design và Threats viết từ hôm nay, song song với phần dựng; Intro chờ #13 và ánh xạ v2, mà ánh xạ này phải chốt **trước** khi chạy eval.
