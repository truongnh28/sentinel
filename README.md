# Sentinel — AuditGame-SE: Progress Status Report

**Đề tài:** FSE-2027-15 · **Học viên:** Nguyễn Hữu Trưởng · **GVHD:** TS. Lê Xuân Bách · **Cập nhật:** 22/09/2026

Repo này chứa mã nguồn và tài liệu của đề tài Sentinel. Đề tài mô hình hoá việc phân bổ audit như một trò chơi Stackelberg giữa bên phòng thủ và kẻ tấn công. Kẻ tấn công đầu độc các *carrier* dai dẳng của một coding agent (`memory · skill · queue · branch`), và thiệt hại chỉ lộ ra sau độ trễ $\Delta$ task. Benchmark **AuditGame-SE** dựng workflow từ SWE-bench, tiêm payload, chạy agent (mock hoặc LLM thật), chấm harm bằng oracle niêm phong, rồi so sánh các chính sách audit B1–B7 với Sentinel.

Đề tài hiện thực draft *Where to Look: Audit-Allocation Games against Adaptive Persistent Poisoning in Software Workflows*. Các con số hiệu năng trong draft là **giá trị dự phóng**, tức giả thuyết cần kiểm chứng. Hướng tái lập đã chốt: **dựng đúng thiết lập của draft, rồi đo xem số ra bao nhiêu**. Mỗi tham số phải tự có nguồn gốc — đo, suy dẫn, hoặc biện hộ kèm kiểm chứng — để trả lời được câu hỏi "vì sao là số này"; giá trị trong draft chỉ là mốc đối chiếu. Mọi tham số chốt trên tập dev và đóng băng trước khi đánh giá; không tham số nào được chỉnh theo kết quả.

README này là **báo cáo tiến độ**. Đọc [Status](#status) và [Được bao nhiêu phần trăm](#được-bao-nhiêu-phần-trăm) là nắm được toàn cảnh; bốn phần sau đi vào chi tiết:
1. [Cách tái lập tham số](#1-cách-tái-lập-tham-số) — bảng tra, trỏ sang tài liệu gốc thay vì chép lại thủ tục
2. [Các stage phải làm và kết quả kỳ vọng](#2-các-stage-phải-làm-và-kết-quả-kỳ-vọng)
3. [Trạng thái hiện tại](#3-trạng-thái-hiện-tại): đã tới bước nào, kết quả ra sao, có issue gì
4. [Kế hoạch bổ sung](#4-kế-hoạch-bổ-sung-đưa-các-hạng-mục-còn-thiếu-vào-sprint): các hạng mục trước đây xếp sau hạn, nay đưa vào sprint

Khung stage theo [tài liệu phương pháp luận](docs/AuditGame-SE_Sentinel_Methodology_Full.md), Phần IV. Hướng dẫn chạy nằm ở cuối trang.

---

## Status

| | |
|---|---|
| **Đang làm** | Nước rút nộp **FSE 2027 Research Papers**, hạn **02/10/2026 AoE** (trưa 03/10 giờ Việt Nam). Hôm nay là **ngày 5/14**, còn **10 ngày**. |
| **Khung bài đã chốt** | **A′ — "bản đồ chế độ"** (chốt 18/09 tại điểm rẽ ngày 4). Bài phát biểu về *ranh giới chế độ*, không về Sentinel. ⚠️ **Cần soát lại trên lưới đầy đủ:** trên lưới nhỏ chạy 23/09 với thang USD đã chốt, `SentinelW window-belief` đạt $L = 0{,}855$ — thắng **cả** B5 (0,955) lẫn B1 (1,000). Đây là 20 workflow · 2 seed, chưa phải thiết lập chứng nhận, nên là *dấu hiệu phải kiểm*, không phải kết quả. |
| **Đang ở bước** | Stage 4 (chứng nhận cổng v2, ngày 6) và chuẩn bị Stage 8 (đóng băng, 29/09). Stage 6 và 9 mới chạy trên thiết lập rút gọn, chưa đúng thiết lập draft (xem [§3.1](#31-tổng-quan-theo-stage)). |
| **Mốc kế tiếp** | **Ngày 6 (23/09):** chạy bảng chứng nhận cổng v2 một lần. Có attacker hợp lệ qua cổng thì giữ A′, không có thì lùi về **khung B** (benchmark tự phản biện). |
| **Thang chi phí** | Chốt **USD** (23/09). Trò chơi bất biến khi nhân cả $(\kappa, \kappa_{\text{commit}}, \eta_Q, B)$ với một hệ số chung, nên đơn vị không phải lựa chọn mô hình — chỉ bốn tỉ số không thứ nguyên sống sót, và USD là đơn vị duy nhất cả bốn cùng đo được. CPU-time giữ làm đối chứng cho $\chi$. Xem [§3.2](#32-trạng-thái-từng-tham-số). |
| **Rủi ro lớn nhất** | (1) Ô $\Delta = 4$ của cổng v2 vẫn đỏ. (2) Thiết lập draft (thư viện 28 policy, 18 attacker, attacker best-response, freeze) chưa dựng, trong khi mốc đóng băng số đã dời lên 29/09 để chừa ngày 01/10 cho việc đọc lại toàn bài. (3) Agent thật làm theo payload **0/7**, nên mọi số harm hiện có là harm dưới mô hình tiếp nhận của MockAgent. (4) **$\kappa_{\text{commit}}$ chưa đo quyết định dấu của RQ1**: trên thang USD SentinelW thắng B1 +25,0% harm, trên thang CPU-time B1 đứng đầu, và ngưỡng lật nằm giữa hai giá trị hiện có. |
| **Kiểm thử** | `tests/run_all.py --all` ngày **23/09**: **765 đạt · 2 không đạt · 13 bỏ qua** — đúng hai lỗi cũ, không hồi quy. Cổng 1 *UNKNOWN* (547/560, 13 test cần Docker), cổng 2 đỏ 203/205, cổng 3 xanh 15/15 (chi tiết ở [§3.5](#35-kiểm-thử)). |

## Được bao nhiêu phần trăm

Đếm theo **hạng mục bàn giao được**: 51 hạng mục, chia tám nhóm. Quy ước: **✅ xong = 1 · 🟡 một phần = 0,5 · ❌ chưa làm = 0**.

**Tổng: 32,5 / 51 = 64%.**

| Nhóm | Tiến độ | Hạng mục |
|---|---|---|
| **A. Hạ tầng benchmark** | **89%** (8/9) | ✅ CarrierStore bốn carrier · ✅ Workflow từ SWE-bench Verified · ✅ Retrieval Jaccard với $\theta$ · ✅ MockAgent · ✅ Agent LLM thật (P2) · ✅ Oracle marker · 🟡 Oracle test ẩn (neo được 1/500) · ✅ Replay và sealed trace · 🟡 Harness Docker (13 test chưa chạy) |
| **B. Tấn công và ground truth** | **50%** (3,5/7) | ✅ Sinh $(\iota,\sigma)$ có lọc nổ sớm · ✅ Payload đóng băng và bộ sinh · 🟡 Thư viện attacker kịch bản (12/18) · ❌ Attacker best-response đọc $\pi_D$ · ❌ Marker duy nhất mỗi lần chạy · ✅ Đo $\Delta$ thực trên 10 repo SWE-bench (không còn là repo đề tài) · ❌ Validate harm trên tập con |
| **C. Corpus lành tính và cổng** | **60%** (3/5) | ✅ Corpus từ item SWE-bench thật · ✅ Ghép theo 5 đặc trưng bề mặt · 🟡 Cổng AUC v2, 20 split ($\Delta = 4$ còn đỏ) · ❌ Permutation test · 🟡 $\beta_k$ đo trên 10 repo thật; skill và queue chuyển sang quét |
| **D. Detector và tín hiệu** | **90%** (4,5/5) | ✅ Detector mô phỏng theo $d'$ · 🟡 Ba mức $(\psi,\varphi)$ của draft chạy như lưới riêng · ✅ CarrierSignal mean và bảng $\tau_{\text{sel}}$ · ✅ Sweep $d'$ liên tục, ra $d'^{*}$ · ✅ Detector nội dung $D_{\text{lex}}$, $D_{\text{llm}}$ |
| **E. Chính sách và lý thuyết** | **69%** (5,5/8) | ✅ B1–B6 · ✅ Minimax LP · ✅ Các biến thể SSG · ✅ Belief tính chính xác · ❌ Thư viện 28 policy · ❌ 240 game nhỏ giải chính xác · 🟡 $\rho$ (đang đo trong không gian proxy) · ✅ $\zeta$ |
| **F. Đo lường và kết quả** | **31%** (2,5/8) | ✅ Lưới $\Delta$ × detector trên MockAgent · ❌ Trục $\chi$ trong đường chính · ❌ $\Delta = 8$ · 🟡 100 workflow (hiện 40) · ❌ Worst-case trên held-out · ❌ Exploitability · ❌ Ablation đầy đủ · ✅ CI bootstrap theo cụm |
| **G. Tính toàn vẹn** | **50%** (2,5/5) | ✅ Ba cổng kiểm thử, 780 test · ✅ Tài liệu tiền đăng ký · 🟡 Digest rời (cổng v2, payload, prompt) · ❌ Manifest đóng băng toàn phần · ❌ Harness từ chối policy chưa đóng băng |
| **H. Tài liệu** | **75%** (3/4) | ✅ Phương pháp luận · ✅ Parameter Estimation Report · ✅ Reports và báo cáo tiến độ · ❌ Bản thảo ACM |

**Đọc các con số này thế nào.**
1. **Nhóm A và D gần xong, nhóm F mới 31%.** Cỗ máy đo đã chạy được, nhưng phần lớn *số để đưa vào bài* thì chưa có. Câu trả lời cho "bài viết được bao nhiêu" là **15–20%**, không phải 64%.
2. **Ba hạng mục kéo tụt cả ba nhóm B, E, G:** thư viện 28 policy, attacker best-response, manifest đóng băng. Làm xong ba thứ này thì nhóm F mở khoá theo, vì worst-case trên held-out và exploitability đều phụ thuộc chúng. Cả ba nằm trong [§3.4](#34-issue-cần-xử-lý) và [§4](#4-kế-hoạch-bổ-sung-đưa-các-hạng-mục-còn-thiếu-vào-sprint).
3. **Một phần công đã bỏ ra không nằm trong 51 hạng mục này:** hơn 60 spike, arm P2, detector nội dung, năm biến thể SSG. Chúng cho ra bốn phát hiện dưới đây, nhưng trong bản nộp nhiều thứ chỉ còn một dòng ở mục Threats.

**Bốn phát hiện đã có, không phụ thuộc phần còn thiếu:**
1. Detector bề mặt chỉ đạt $d' \le 0{,}50$, trong khi điểm hoà vốn so với audit-at-commit là $d'^{*} = 2{,}85$ ở $\Delta = 2$.
2. Detector nội dung sụp về ngẫu nhiên (AUC 0,479–0,518) khi attacker không tự khai báo.
3. Agent LLM thật không làm theo lời khuyên độc: 0/7 instance.
4. Không tồn tại điểm hoà vốn ở $\Delta \le 1$, khớp với Hệ quả 5 của draft.
5. **Đơn vị chi phí không phải lựa chọn mô hình** — trò chơi bất biến khi nhân cả $(\kappa, \kappa_{\text{commit}}, \eta_Q, B)$ với một hệ số chung, nên chỉ bốn tỉ số không thứ nguyên sống sót. Ba trong bốn đã đo; cái thứ tư, $\kappa_{\text{commit}}/\bar\kappa$, **quyết định dấu của RQ1** và chưa ai đo ở bất kỳ đơn vị nào.

---

## Lịch nước rút

Bốn từ dùng xuyên suốt bảng dưới:
- **Điểm rẽ** — mốc đã khai báo trước: tới ngày đó nhìn số rồi chọn nhánh theo quy tắc, không bàn lại.
- **Cổng v2** — phép chứng nhận rằng payload không phân biệt được với nền lành tính: AUC phải nằm dưới trần trên cả 20 split.
- **$m(x)$** — độ lộ nội dung của một item, đại lượng attacker tìm cách kéo xuống; "chuỗi bảng $m$" là dãy bảng đo $d'$ hiệu dụng theo $m$.
- **G4** — phép kiểm agreement giữa LLM judge và nhãn tay: $n = 38$, cận dưới Clopper–Pearson $\ge 0{,}75$.

### Ngày 1–5 (18–22/09) — đã qua

| Ngày | Việc | Kết quả |
|---|---|---|
| 1 — 18/09 | P2 runner; $\tau_{\text{sel}}$ chạy theo $d'$ | Tách được confound của phép quét $d'$ |
| 2 — 19/09 | Chạy P2 → **điểm rẽ P2** | 14 instance, 7 chấm được: tuân thủ **0/7**. Điều kiện dừng #2 không kích hoạt theo quy tắc, nhưng tiền đề đe doạ không tái tạo được trên agent thật |
| 3 — 20/09 | **Điểm rẽ L** → khung A hay A′ (xong sớm từ 18/09) | Chọn **A′**: thắng B1 ở 64/64 ô, thua B5, không tồn tại ranh giới $\lambda_Q > 0$ |
| 4–5 — 21–22/09 | Cổng v2 trọn gói; sweep chấm $L$ có B5, B6 | Cổng v2 đóng băng 19/09 (qua điều kiện dừng #3); sweep chấm $L$ trên payload v2 |

### Ngày 6–13 (23–30/09) — còn lại, dồn xong trước 01/10

Mọi việc đo và chạy phải khép lại trong tháng 9, để hai ngày 01–02/10 chỉ còn đọc lại toàn bài, sửa và nộp. Vì vậy các mạch chạy song song thay vì nối đuôi.

| Ngày | Mạch đo và dựng | Mạch bài và kiểm | Đầu ra phải có |
|---|---|---|---|
| **6 — T4 23/09** | ✅ **Đã làm nhiều hơn kế hoạch.** W1–W5 xong trong một ngày: $\pi_0$ suy dẫn + sinh lại $\tau_{\text{sel}}$ · $\eta_Q$ theo carrier · $\beta_k$ trên 10 repo · **4 checkpoint audit làm việc thật** (`checkpoints.py`) rồi đo lại $\kappa$ · $\Delta$ thực + co-change trên SWE-bench. W6 ($c$) **từ chối đo**, tiền đề hỏng. **Chốt thang chi phí USD.** ⏳ Còn: bảng chứng nhận v2 (điểm rẽ), marker `blake2b` | — | 5 tham số chuyển từ gán tay sang đo; $\chi$ = 1,349 (USD) / 1,295 (CPU); [runbook](docs/AuditGame-SE_Parameter_Measurement_Runbook.md) + [biểu đồ](docs/AuditGame-SE_Parameter_Measurement_Charts.html) + [plan đợt 3](docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md) |
| **7 — T5 24/09** | **P1** — đo $\kappa_{\text{commit}}$ có chạy test thật (`PASS_TO_PASS` trên repo đã clone) | Gửi thầy danh sách 28 policy và 18 attacker để duyệt; **chốt mô hình quan sát** (M0/MA/MB/ME) | Dấu của RQ1 được xác định, hoặc một ngưỡng $r^{*}$ phát biểu được |
| **8 — T6 25/09** | Thêm 6 attacker cho đủ 18, chia lại held-out 7; attacker best-response. **P3** — neo $\lambda_Q, \lambda_T$ vào chi phí đo được | — | **Exploitability** và **worst-case trên held-out** lần đầu có số; tuyên bố chính hết đứng trên số gán tay |
| **9 — T7 26/09** | Thư viện 28 policy, chạy được như một hệ thống | G4 nhãn mù — **hạn cứng**, cần người gán tay 38 instance | "Sentinel-28" so được với B1 và B5 |
| **10 — CN 27/09** | Chạy lưới chính: $N = 100$ × $\Delta \in \{0,1,2,4,8\}$ × 3 $\chi$ × 3 detector × 3 seed | Chuỗi bảng $m$ | Bảng kết quả chính; ablation; CI bootstrap theo cụm |
| **11 — T2 28/09** | **P2** (sửa mô hình quan sát → đo lại $c$) · **P4** (240 game nhỏ và $\rho$) nếu P1 không trượt · **P5–P7** bốn phép quét · P9 nếu còn giờ | — | Định lý 4 có vế trái, hoặc một phát biểu kiểm chứng được về vì sao không; mỗi tham số quét có một dòng kết luận |
| **12 — T3 29/09** | **Đóng băng số**: manifest hash, harness từ chối policy chưa đóng băng; chạy lại lưới trên cấu hình đã đóng băng | Chạy ba cổng, bật Docker cho 13 test của cổng 1 | Ba cổng xanh, hoặc đỏ có giải trình; số cuối cùng |
| **13 — T4 30/09** | — | Viết Evaluation, Threats, ablation RQ4; dựng artifact ẩn danh | Bản nháp đủ mục, số đã khớp bảng |
| **14 — T5 01/10** | — | **Đọc lại toàn bài**, sửa, format ACM | Bản gần cuối |
| **15 — T6 02/10** | — | Nộp sớm trong ngày | Bản nộp (hạn AoE) |

**Ba thay đổi so với lịch cũ:** đóng băng số dời lên **29/09** thay vì 30/09; toàn bộ phần đo khép lại trong tháng 9; ngày 01/10 dành riêng cho việc đọc lại và sửa, không còn chồng lấn với việc chạy.

**Nếu phải cắt**, cắt theo thứ tự ngược: W7 và W6 (ngày 11) bỏ trước, rồi rút quy mô lưới ngày 10 xuống $N$ nhỏ hơn. Không cắt ngày 8 và 9, vì không có 18 attacker và thư viện 28 policy thì không có bảng kết quả chính.

### Dự kiến có gì để báo cáo cuối tuần này (27/09)

Tính tới hết Chủ nhật 27/09, tức sau ngày 10 của sprint, dự kiến đã có:

| Nhóm | Kết quả |
|---|---|
| **Quyết định** | Nhánh A′ hay B, kèm bảng chứng nhận v2 theo từng $\Delta$ |
| **Tham số chuyển từ gán tay sang đo** | $\kappa$ theo CPU-time, $\chi$ tính lại, $\pi_0 = 0{,}080$ kèm bảng $\tau_{\text{sel}}$ mới, $\eta_Q$ theo carrier, $\beta_k$ |
| **Thiết lập draft** | 18 attacker với 7 held-out, attacker best-response, thư viện 28 policy, marker duy nhất mỗi lần chạy |
| **Số so được với Bảng 2 của draft** | Worst-case trên held-out, exploitability, và bảng kết quả trên lưới đầy đủ |
| **Còn nợ** | $\Delta$ thực trên SWE-bench, hằng số $c$, 240 game nhỏ và $\rho$ — nằm ở ngày 11 |

Hai việc **không phụ thuộc vào code**, cần thầy và cần bố trí người: duyệt danh sách 28 policy và 18 attacker (gửi ngày 7), và gán tay 38 instance cho G4 (hạn ngày 9).

**Ba điều kiện dừng đã khai báo trước:**

| # | Kích hoạt khi | Hiện trạng |
|---|---|---|
| 1 | Cổng v2 tự vỡ | Chưa kích hoạt theo định nghĩa trong tiền đăng ký. Hai test cổng 2 đang đỏ, cần đối chiếu với định nghĩa này trước ngày 6 |
| 2 | P2 cho kết quả âm nặng | Không kích hoạt theo quy tắc (xem ngày 2), dù tiền đề đe doạ không tái tạo được trên agent thật |
| 3 | Cổng v2 chưa đóng băng hết ngày 5 | Đã qua — đóng băng 19/09 |

---

## 1. Cách tái lập tham số

**Nguyên tắc.**
1. **Không tham số nào được dùng chỉ vì draft ghi như vậy.** Mọi số dự phóng trong draft đều chưa có nguồn gốc, nên mỗi tham số phải trả lời được câu hỏi của hội đồng: *"vì sao là số này?"* Giá trị của draft chỉ đóng vai **mốc đối chiếu**, không phải nguồn.
2. Mỗi tham số vì vậy phải có **một phương thức xác lập** (M1–M4 dưới đây), làm trên tập dev và đóng băng **trước khi đánh giá**. Tham số thiết kế (không đo được) thì phải có **lập luận biện hộ + một kiểm chứng**, ví dụ $K = 4$ biện hộ bằng bốn họ carrier của HarnessSafe và kiểm bằng ablation $K = 2, 3$.
3. Sau đóng băng, không tham số nào được chỉnh theo kết quả held-out (ranh giới tuning ở Stage 10).
4. Tham số dựa vào giả định mạnh thì phải quét và báo cáo như một trục, thay vì chốt một giá trị.
5. Nếu giá trị đo được **khác** giá trị của draft (ví dụ $\chi$: 2,11 so với 1,34), báo cáo giá trị đo được và nêu rõ chênh lệch; không sửa công thức để ra số của draft.

**Bốn phương thức xác lập** (chi tiết: [Parameter Estimation Report](docs/AuditGame-SE_Parameter_Estimation_Report.md), mục 5):
- **M1 — đo trực tiếp:** có quy trình đo và sai số.
- **M2 — neo rồi quét:** neo vào một đại lượng đo được, rồi quét quanh giá trị neo.
- **M3 — suy dẫn từ thiết kế thí nghiệm:** tham số là hệ quả của cách dựng episode.
- **M4 — khử tham số:** phát biểu kết luận dưới dạng ngưỡng ("thứ hạng giữ khi $\lambda_Q < \lambda_Q^{*}$").

### 1.1 Bảng tra: tham số nào, thủ tục nằm ở đâu

Thủ tục chi tiết **không chép lại ở đây**. Bảng dưới trỏ tới mục tương ứng trong hai tài liệu gốc: **[PPL]** = [phương pháp luận](docs/AuditGame-SE_Sentinel_Methodology_Full.md), **[PER]** = [Parameter Estimation Report](docs/AuditGame-SE_Parameter_Estimation_Report.md).

| Tham số | Giá trị trong draft | Phương thức | Tóm tắt cách xác lập | Thủ tục chi tiết |
|---|---|---|---|---|
| $K = 4$ | 4 carrier | Thiết kế, có kiểm chứng | Biện hộ bằng bốn họ state dai dẳng của HarnessSafe; kiểm bằng ablation $K = 2, 3$ | [PPL] Phần VI loại A |
| $H$ | 6–14 | Suy từ dữ liệu | Chọn từ phân phối độ dài chuỗi instance liên tiếp dựng được; báo số workflow khả dụng theo từng $H$ | [PPL] Stage 1 |
| Lưới $\Delta$ | $\{0,1,2,4,8\}$ | Suy từ dữ liệu | Neo vào phân phối $\Delta$ thực đo được (trung vị 3, p75 10), phủ hai bên crossover dự đoán | [PPL] Stage 3.7 · [PER] 5.8 |
| Lưới $\chi$ | $\{0;\ 0{,}5;\ 1{,}34\}$ | Suy từ $\kappa$ đo được | Hai mốc đầu là đồng nhất và trung gian; mốc thứ ba là **$\chi$ đo được của mình**, không phải 1,34 của draft | [PPL] Stage 2 · [PER] 5.7 |
| Quy mô lưới, số seed | 100 workflow × 8 hệ thống × 3 seed | Suy từ phân tích lực | Chọn $N$ từ độ rộng CI cần thiết để phát biểu ngưỡng 15% (cổng 3 hiện có test cho việc này) | [PPL] Stage 9 |
| 3 mức $(\psi,\varphi)$ | (0,75; 0,20) · (0,85; 0,12) · (0,92; 0,06) | M2 | Neo vào ROC của detector thật rồi chọn ba điểm vận hành; ánh xạ sang $d$ = 1,52 / 2,21 / 2,96. Hiện detector thật chỉ đạt $d' \le 0{,}50$, nên phải nêu rõ ba mức là **biến kiểm soát**, không phải detector đo được | [PPL] §9.1, Stage 5 |
| Thư viện 28 policy | 28, ba họ, không có danh sách | Thiết kế, có kiểm chứng | Sinh theo lưới 8 + 12 + 8; con số 28 biện hộ bằng $\rho$ bão hoà (thêm policy không giảm $\rho$ nữa), không phải vì draft ghi 28 | [PPL] Stage 6B, 6D |
| 18 attacker, 7 held-out | 18/7, không có danh sách | Thiết kế, có kiểm chứng | Mỗi attacker là một *giả thuyết* về chỗ yếu của defender (cost-max/min, delay-max, uniform, ingress, best-response); held-out chia bằng hash của tên để không chọn được tập dễ | [PPL] Stage 3.3 |
| $\kappa(k)$ | 0,4 / 0,9 / 1,6 / 4,1 | M1 | **Tự đo**, thang vận hành **USD** = số item mỗi lượt audit × đơn giá chấm; đối chứng bằng CPU-time của 4 checkpoint thật (`checkpoints.py`, đồng hồ `process_time`, lặp 200 lần vì một lượt tốn cỡ một tick). Đơn vị triệt tiêu — xem hộp ở [§3.2](#32-trạng-thái-từng-tham-số). Bảng draft chỉ là mốc đối chiếu | [PPL] Stage 2 · [PER] 5.6 |
| $\chi$ | 1,34 | M1 | Tính từ $\kappa$ mình đo, với công thức $\bar\kappa$ công bố trước (`policies.chi_of`, một định nghĩa duy nhất). Ra **1,349** (USD) và **1,295** (CPU) — hai phép đo độc lập đồng ý; 2,114 là bảng draft. Chênh lệch phải báo cáo, không được chỉnh công thức để ra 1,34 | [PPL] Stage 2 · [PER] 5.7 |
| $\beta_k$ | chưa có | M1 (dự phòng M2) | Luật ánh xạ commit → carrier, đếm trên cửa sổ commit giữa hai task | [PPL] Stage 4 bước 5 · [PER] 5.1 |
| $\varepsilon$ | trung vị `edit_size` benign | M1 | Percentile của phân phối diff-size benign | [PPL] Stage 3.4 |
| $\Delta$ thực | chưa có | M1 | Co-change + lọc bằng đồ thị import; quy về khoảng cách task | [PPL] Stage 3.7 · [PER] 5.8 |
| $\pi_0$, $b_0$ | chưa có | M3 | Suy từ thiết kế episode, rồi quét để kiểm | [PER] 5.3 |
| $\tau$, $\lambda_Q$, $\lambda_T$ | chưa có | M2 + M4 | Neo vào chi phí đo được, báo ngưỡng $\lambda^{*}$ tại đó thứ hạng đổi | [PPL] Phần VI loại C · [PER] 5.5 |
| $\eta_Q$ | chưa có | M1 + M3 | Tách phần gỡ (đo) và phần phục hồi (suy từ $n_{\text{live}}$) | [PER] 5.2 |
| $\rho$ | 0,07 | M1 | TV theo xác suất hành động từng task, $\pi^{*}$ từ game nhỏ giải chính xác | [PPL] Stage 6D · [PER] 5.9 |
| $N$ hạt | 2048 | Thiết kế | Belief hiện tính chính xác nên không cần | [PPL] Stage 6A |
| $c$ (Định lý 4) | chưa có | M1 | $B_{\min}$ từ độ hội tụ của posterior, lấy max theo ô, hồi quy kiểm từng thừa số | [PER] 5.4 |
| AUC cổng bề mặt | ≤ 0,56 | M1 | Classifier two-sample test, kèm CI và permutation test | [PPL] Stage 4 |

---

## 2. Các stage phải làm và kết quả kỳ vọng

Cột "Kết quả kỳ vọng" ghi tiêu chí đạt của stage, kèm giá trị dự phóng của draft nếu có. Giá trị dự phóng là mục tiêu kiểm chứng, không phải mục tiêu tinh chỉnh.

Cột **"TODO còn lại"** là danh sách việc phải làm, gắn mã: **W…** là workstream ở [§4](#4-kế-hoạch-bổ-sung-đưa-các-hạng-mục-còn-thiếu-vào-sprint), **#…** là issue ở [§3.4](#34-issue-cần-xử-lý). Các bước thực hiện chi tiết nằm trong [plan W1–W10](docs/design/plans/2026-09-22-W1-W10-tham-so.md).

| Stage | Việc phải làm | Đầu ra | Kết quả kỳ vọng | TODO còn lại |
|---|---|---|---|---|
| 0 | Viết tuple game; thứ tự cam kết; defender chỉ nhận `CarrierSignal(p, n)` | Đặc tả luật chơi | Cạnh bị cấm vắng mặt trong chữ ký hàm, có test cưỡng chế | — |
| 1 | Dựng workflow từ SWE-bench: sort `created_at`, cắt cửa sổ 6–14 task, topic từ gold patch, retrieval Jaccard với $\theta$ chốt trên dev | Danh sách workflow | 100 workflow; $\theta$ chốt trước khi nhìn kết quả; lọc instance flaky | Lọc instance flaky · nâng lên 100 workflow · biện hộ $H$ và cỡ mẫu (**W10**) |
| 2 | Hiện thực 4 checkpoint audit; đo CPU-time; tính $\chi$ | $\kappa$, $\chi$ | Bảng $\kappa$ có sai số; draft dự phóng $\chi = 1{,}34$ | ✅ **W4 xong** (4 checkpoint thật, $\chi = 1{,}349$ USD / 1,295 CPU, chốt thang USD) · **#2** đo $\kappa_{\text{commit}}$ có chạy test · chốt quy ước chuẩn hoá khi quét $\chi$ |
| 3 | 18 attacker (7 held-out); sinh $(\iota,\sigma)$ theo $\Delta$ có lọc nổ sớm; marker duy nhất mỗi lần chạy; oracle harm; đo $\Delta$ thực | Thư viện attacker, oracle | Oracle validate trên tập con; phân phối $\Delta$ thực cùng thang với crossover | **#4** thêm 6 attacker cho đủ 18 và attacker best-response · **#6** marker `blake2b` · **W8** payload AgentPoison và MINJA · **W5** $\Delta$ thực trên SWE-bench · validate harm trên tập con |
| 4 | Corpus lành tính khớp bề mặt; cổng AUC; ước lượng $\beta_k$ | Corpus, AUC, $\beta$ | AUC ≤ 0,56 kèm CI và permutation test; 620 mẫu | Chứng nhận ô $\Delta = 4$ (điểm rẽ ngày 6) · **W3** đo $\beta_k$ · permutation test |
| 5 | Mô phỏng detector với 3 mức $(\psi,\varphi)$; CarrierSignal lấy mean posterior | Detector, $\gamma$ | Ba mức $\gamma$ = 0,55 / 0,73 / 0,86 | Chạy đúng ba mức $(\psi,\varphi)$ như một lưới riêng · **W1** $\pi_0$ suy dẫn và sinh lại bảng $\tau_{\text{sel}}$ |
| 6 | Belief; thư viện 28 policy; 240 game nhỏ giải chính xác; đo $\rho$; mở rộng thư viện bằng double oracle nếu $\rho$ lớn | Thư viện, $\rho$ | Draft: $\rho = 0{,}07$, cận Mệnh đề 6 = 0,42, regret đo được 0,09 | ✅ **W2 xong** ($\eta_Q$ theo carrier, 61,5×) · **#3** dựng thư viện 28 policy · **W7** 240 game nhỏ và $\rho$ đúng không gian |
| 7 | Tính tay trên game nhỏ và so với mã | Ví dụ khớp | Minimax 4×4: tất định 1,0, trộn 0,5; Bayes 0,10 → 0,44 → 0,85 | Test hoá ví dụ minimax 4×4 và ví dụ Bayes |
| 8 | Đóng băng policy, attacker, hằng số, corpus, workflow bằng hash | `frozen/`, `MANIFEST.sha256`, tag `freeze-v1` | Harness tính lại hash và từ chối chạy nếu không khớp | **#4** manifest đóng băng toàn phần và harness từ chối policy chưa đóng băng |
| 9 | Chạy lưới đầy đủ; worst-case trên held-out; exploitability; crossover; CI bootstrap theo cụm repo; hằng $c$ | Bảng kết quả trên lưới $(\Delta,\chi)$ | Draft (Bảng 2, $\Delta > 2$, $\chi = 1{,}34$, held-out): B1 0,412 → Sentinel 0,272 (−34,1%, CI [−42,6%; −25,1%], vượt ngưỡng 15%); held-out 27,6%; exploitability 0,34 → 0,09; cách ly nhầm 3,2% → 5,1%; crossover 2,1; RQ4 21,4%–39,8%, lớn nhất ở detector yếu; quét $\eta_Q$: 34,1% → 44,0% | Lưới đầy đủ: $\Delta = 8$, trục $\chi$ vào đường chính, $N = 100$ · worst-case trên held-out · exploitability · ablation · **W6** hằng số $c$ |
| 10 | Giải game; tuning chỉ trên dev, trước đóng băng | Nghiệm, ranh giới tuning | Khoảng cách dev và held-out báo cáo được (draft: 34,1% so với 27,6%) | Double oracle (sau hạn nếu không kịp) |

---

## 3. Trạng thái hiện tại

### 3.1 Tổng quan theo stage

**2 hoàn thành · 1 làm theo hướng khác · 8 một phần · 0 chưa bắt đầu.** Rà soát ngày 22/09 bằng cách đọc mã và chạy lại toàn bộ test; cập nhật 23/09 sau đợt đo W1–W6 ([runbook](docs/AuditGame-SE_Parameter_Measurement_Runbook.md)). Đợt đo không đổi trạng thái stage nào, nhưng đổi *nội dung* của Stage 2, 3, 4, 6 và 9 — chi tiết trong cột Issue.

| Stage | Trạng thái | Đã làm | Kết quả hiện có | Issue |
|---|---|---|---|---|
| 0 | ✅ Hoàn thành | Tuple game; loss ba số hạng (`metrics.loss`); `CarrierSignal(p, n)` chỉ có hai trường | Cạnh bị cấm cưỡng chế bằng chữ ký hàm và test | — |
| 1 | 🟡 Một phần | SWE-bench Verified đã nối; sort `created_at`; topic từ gold patch; $\theta = 0{,}5$ chốt trước khi đếm workflow | **14/58** workflow khả dụng ở $H = 8$; sweep hiện chạy 40 workflow | Thiếu workflow so với 100; chưa lọc instance flaky |
| 2 | 🟡 Một phần | Công thức $\chi$ công bố; **23/09: bốn checkpoint được hiện thực làm việc thật** (`checkpoints.py`), $\kappa$ đo lại trong vòng chạy game; ba thang giá so trên cùng một lưới bằng `tools/compare_cost_scales.py`; **chốt USD làm thang vận hành** (trò chơi bất biến theo hệ số chung — chỉ bốn tỉ số sống sót) | $\chi$: **2,114** (bảng draft, theo giai đoạn) · **1,349** (USD, theo số item) · **1,295** (CPU-time, sau khi checkpoint làm việc thật; bản trước đo bộ mô phỏng và ra 0,16). Thứ hạng chính sách **đổi theo đơn vị**: thang USD cho SentinelW thắng B1 **+25,0% harm / +14,5% $L$**; thang CPU cho B1 đứng đầu | **Toàn bộ khác biệt quy về một số chưa ai đo**: $\kappa_{\text{commit}}/\bar\kappa$ — USD *định nghĩa* 4,00, CPU *đo* 1,43 nhưng thiếu differential testing nên là cận dưới, còn **ngưỡng lật nằm giữa hai giá trị đó** (5,13–7,17 lượt commit mỗi episode). Đo chi phí thật của một lượt commit audit có chạy test là phép đo giá trị cao nhất còn lại |
| 3 | 🟡 Một phần | Sinh $(\iota,\sigma)$ có lọc nổ sớm; 12 attacker kịch bản; chia held-out bằng hash; **23/09: đo $\Delta$ thực trên 10 repo SWE-bench** (SZZ-lite, `tools/measure_delta_swebench.py`) | $\Delta$ theo task: trung vị **0** ở 8/10 repo, django **4,5**; chỉ **19%** instance có $\Delta \ge 2$. $\Delta$ theo commit: trung vị 14–194, p75 tới 935 | Số dogfood cũ (trung vị 3) đo trên repo đề tài, **không** phải quần thể mục tiêu; đơn vị task phụ thuộc mật độ lấy mẫu instance nên phải báo theo repo. Vùng $\Delta \ge 2$ chỉ phủ ~1/5 workload ⇒ ranh giới vùng nên phát biểu theo tỉ lệ workload từng repo. Còn lại: 12/18 attacker; held-out 6/12; **chưa có attacker best-response**; **marker là hằng `"raw_write"`**; chưa có $\Delta = 8$ |
| 4 | 🟡 Một phần | Cổng v2 đóng băng 19/09: 5 đặc trưng, tiêu chí cận trên CI, 20 split; corpus từ item SWE-bench thật, ghép theo tuổi; **23/09: đo $\beta_k$ trên 10 repo thật** (`tools/measure_beta.py`, hai luật ánh xạ) | v1 (4 đặc trưng): 0,5414. v2: $\Delta=0$ 0,519 · $\Delta=2$ 0,529 (20/20 split) · $\Delta=4$ **0,587** (1/20). $\beta$: memory **0,31**, branch 1,0 (theo cấu tạo); skill **0,058 hay 0,607** tuỳ luật | $\Delta = 4$ đỏ; 2 test cổng 2 đỏ; chưa có permutation test; ngưỡng 0,56 nằm trong dải nhiễu ở mọi $n \le 1800$. **$\beta$ không định danh được**: hai luật ánh xạ lệch hơn 10× ở skill ⇒ theo tiêu chí đã khai trước, skill và queue chuyển sang M2 (quét), chỉ memory và branch được trích dẫn |
| 5 | ✅ Hoàn thành | Detector Gaussian theo $d'$, gộp bằng mean tỉ số likelihood; quét $d'$ liên tục; thử detector nội dung | $d'^{*}$ = 2,85 ($\Delta=2$), 0,95 ($\Delta=4$), không tồn tại ở $\Delta \le 1$; detector bề mặt $d' \le 0{,}50$ | Chưa chạy đúng 3 mức $(\psi,\varphi)$ của draft như một lưới riêng |
| 6 | 🟣 Hướng khác | Belief tính chính xác bằng liệt kê cửa sổ (thay particle filter); minimax LP và 5 biến thể SSG; **23/09: $\beta$ mặc định của belief đọc từ số đo** (`costs.BETA_DEFAULT`) | Registry 17 policy; $\rho = 0{,}894$ trong không gian proxy | 🔴 **Quan sát đang miễn phí**: `belief.WindowBelief.update` nhận tín hiệu của *mọi* carrier ở *mọi* task, bất kể chính sách audit gì — posterior tại $\sigma$ không đổi khi $B$ đi từ 2 đến 200. Đây là lý do Stage 9 không fit được hằng $c$. Vẫn chưa có thư viện 28 policy và 240 game nhỏ; tên "B7" trong mã là LP đối thủ, còn trong draft B7 là oracle trần |
| 7 | 🟡 Một phần | `spikes/trace_one_episode.py` phát lại một episode với số thật | Minimax 4×4 khớp `game.minimax` ($V^* = 0{,}5$) | Chưa test hoá ví dụ 4×4; ví dụ Bayes Bernoulli chưa được mã kiểm |
| 8 | 🟡 Một phần | Digest rời: cổng v2, độ dài payload, prompt detector; payload đóng băng; tiền đăng ký | — | **Chưa có `frozen/`, `MANIFEST.sha256`**; harness chưa từ chối policy chưa đóng băng |
| 9 | 🟡 Một phần | Lưới $\Delta \in \{0,1,2,4\}$ × 3 detector trên MockAgent; chấm $L$; $\lambda_Q^{*}$; bootstrap theo workflow; **23/09: thử fit hằng $c$ của Định lý 4** (`tools/measure_c.py`) | Xem [§3.3](#33-so-với-giá-trị-dự-phóng-của-draft). Hằng $c$: **không fit được** — script kiểm tiền đề rồi từ chối trả số | 🔴 Tiền đề của Định lý 4 không thoả trong harness: ngân sách **không mua được thông tin** (xem Stage 6), nên vế trái của cận không tồn tại. Phải sửa mô hình quan sát trước, rồi mới fit $c$. Vẫn chưa có worst-case trên held-out, exploitability, $\Delta = 8$, trục $\chi$ trong đường chính |
| 10 | 🟡 Một phần | LP Stackelberg (Conitzer–Sandholm); ranh giới tuning qua tiền đăng ký | — | Chưa có double oracle |

### 3.2 Trạng thái từng tham số

**11 hoàn thành · 2 một phần · 2 tiền đề hỏng · 3 chưa thực hiện** (18 mục). Cập nhật 23/09 sau đợt đo W1–W6, xem [Parameter Measurement Runbook](docs/AuditGame-SE_Parameter_Measurement_Runbook.md).

> **Đơn vị của $\kappa$ đã chốt: USD.** Trò chơi **bất biến** khi nhân cả
> $(\kappa, \kappa_{\text{commit}}, \eta_Q, B)$ với một hệ số chung — kiểm chứng qua
> $10^{3}$, $10^{6}$, $10^{-6}$, $L$ của cả tám chính sách giống hệt. Nên đơn vị
> không phải lựa chọn mô hình; chỉ **bốn tỉ số không thứ nguyên** sống sót, và USD
> được chọn vì là đơn vị duy nhất cả bốn cùng đo được — đặc biệt $\eta_Q$, thứ chỉ
> tồn tại ở đó. CPU-time giữ làm **đối chứng độc lập cho $\chi$** (1,295 so với
> 1,349), không làm thang vận hành. Bảng draft rút khỏi đường chính.
> Chi tiết: [runbook §1.7d](docs/AuditGame-SE_Parameter_Measurement_Runbook.md).

| Tham số | Draft | Phương thức | Trạng thái | Giá trị hiện tại | Issue / việc còn lại |
|---|---|---|---|---|---|
| $\tau_{\text{sel}}$ | — | M1 | ✅ Hoàn thành | Bảng tham chiếu, 800.000 mẫu/ô | Sinh lại khi $\pi_0$ đổi |
| $\mathrm{AUC}_{\text{upper}}$ | ≤ 0,56 | M1 | ✅ Hoàn thành | 0,5414 (v1); cổng v2 ở §3.1 | Permutation test |
| $\varepsilon^{*}$ | — | M4 | ✅ Hoàn thành | 0; không tồn tại trên nền lành tính trung thực | — |
| $d'^{*}$ | — | M2 + M4 | ✅ Hoàn thành | 2,85 ($\Delta=2$); 0,95 ($\Delta=4$); không tồn tại ở $\Delta \le 1$ | — |
| $d'$ bề mặt | — | M1 | ✅ Hoàn thành | $\le 0{,}50$ | Thấp hơn cả mức "yếu" của draft ($d$ = 1,52) |
| $\zeta$ | — | M1 | ✅ Hoàn thành | 0,000 (mock); 0,119 khi $\beta = 0{,}5$ | Tách vai thế giới / mô hình để $\zeta$ có tác dụng |
| $\Delta$ thực | — | M1 | ✅ Hoàn thành | SWE-bench, 10 repo: trung vị **0 task** (django 4,5); theo commit 14–194; chỉ **19%** instance có $\Delta \ge 2$ | Đơn vị task phụ thuộc mật độ lấy mẫu — báo theo repo, không gộp |
| Chênh lệch ràng buộc | — | M1 | 🟡 Một phần | Độ phủ $-13{,}29\%$ | File kết quả chưa được commit, nên chưa tái lập được |
| $\chi$ | 1,34 | M1 | ✅ Hoàn thành | **1,349** (USD, thang vận hành); 1,295 (CPU, đối chứng); 2,114 là bảng draft — đã rút | Hai phép đo **độc lập** ra cùng hình dạng vì cùng bị chi phối bởi số item mỗi lượt audit. Còn lại là quy ước chuẩn hoá khi quét (dòng riêng bên dưới) |
| $\kappa(k)$ — carrier | 0,4 / 0,9 / 1,6 / 4,1 | M1 | ✅ Hoàn thành | **USD**: memory 0,002643 · branch 0,002228 · queue 0,000767 · skill 0,000554. Đối chứng CPU-time qua 4 checkpoint thật (`checkpoints.py`): 1,45e−5 · 1,07e−5 · 4,78e−6 · 3,64e−6 giây | Hai đơn vị cho cùng hình dạng ⇒ phần carrier khép lại. Thứ tự **đảo ngược** so với bảng draft: memory rẻ nhất → đắt nhất |
| $\kappa_{\text{commit}}$ | 4,1 | M1 | 🔴 **Chưa đo, ở bất kỳ đơn vị nào** | USD **giả định** $4{,}00\,\bar\kappa$ (chấm cả bốn carrier); CPU **đo** $1{,}43\,\bar\kappa$ nhưng thiếu differential testing ⇒ cận dưới | **Quyết định dấu của RQ1.** Ngưỡng lật nằm **giữa hai con số đó** (5,13–7,17 lượt commit mỗi episode). Đo được **không cần dựng lại SWE-bench**: 10 repo đã clone và dữ liệu đã có `PASS_TO_PASS`. Đơn giá VM để trống — kết quả báo theo **giá hoà vốn** $r^{*}$, xem [đợt 3 P1](docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md) |
| $\lambda_Q, \lambda_T$ | — | M2 + M4 | ❌ Chưa neo | Gán 0,10 / 0,50; $\lambda_Q^{*} \approx 0{,}036$–$0{,}05$ | $\lambda_T$ quyết định Sentinel thắng B1 ở 64/64 hay 22/64 ô; phải neo trước khi nhìn bảng kết quả |
| $\rho$ | 0,07 | M1 | ❌ Chưa đúng không gian | 0,894 (proxy) | Cần thư viện 28 policy và game nhỏ |
| $\eta_Q$ | — | M1 + M3 | ✅ Hoàn thành | **Chỉ đo được bằng USD** — nửa phục hồi là agent ghi lại item = token; CPU-time không định giá được (nửa gỡ đo ra $\le 0$). Cách ly đắt **gấp 61,5×** audit cùng carrier; một lượt tốn **6,0× toàn bộ ngân sách** ⇒ NC1 không hành động lần nào | Đây là lý do thang vận hành phải là USD. `costs.install()` vẫn cài giá **placeholder** (rẻ hơn 54×) ⇒ mọi bảng USD trước 23/09 chạy trên giá sai. Giá đúng lại **cải thiện** SentinelW ($L$ 1,095 → 0,855) vì nó thôi cách ly bừa |
| $\beta_k$ | — | M1 → **M2** | 🟡 Một phần | 10 repo thật: memory **0,31**, branch 1,0; skill 0,06 hay 0,61 tuỳ luật ánh xạ | Hai luật không đồng ý ⇒ skill và queue phải quét, không chốt |
| $\pi_0, b_0$ | — | M3 | ✅ Hoàn thành | Suy dẫn **0,0799** (thế giới) / **0,0400** (mô hình), một nguồn trong `costs.py` | Bảng $\tau_{\text{sel}}$ đang sinh lại; sau đó quét $\pi_0$ |
| $c$ | — | M1 | 🔴 **Không đo được** | Tiền đề hỏng: posterior đứng yên ở 0,000336 khi $B$ đi từ 2 đến 200 | `runner.py` chấm cả 4 carrier mỗi task bất kể audit cái gì ⇒ ngân sách mua **hành động**, không mua **thông tin**. Bốn mô hình quan sát để chọn — **M0** giữ nguyên · **MA** trả tiền mới được nhìn (đề xuất) · **MB** hai tầng · **ME** chỉ thấy cái đã động vào — xem [đợt 3 P2](docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md). Đã kiểm: MA để lại **32% độ phủ quan sát**, belief thưa chứ không mù |
| Quy ước quét $\chi$ | — | Thiết kế | ❌ Chưa khai báo | Đề xuất neo $\kappa_{\min}$ | Khai báo trước khi chạy; báo cả ba quy ước |

W1–W5 đã xong trong đợt 23/09; W6 ($c$) hỏng tiền đề và W7 ($\rho$) còn chờ thư viện 28 policy. Việc đo **giá trị cao nhất còn lại** là $\kappa_{\text{commit}}$ có chạy test thật — nó là số duy nhất quyết định dấu của kết luận chính. Riêng $\lambda_Q, \lambda_T$ và quy ước quét $\chi$ là quyết định neo, làm cùng lúc với việc đóng băng.

### 3.3 So với giá trị dự phóng của draft

Các số "đo được" dưới đây chạy trên **thiết lập hiện tại** (chưa có thư viện 28 policy, chưa có held-out 7/18, MockAgent). Chúng chưa phải phép tái lập cuối cùng.

| Chỉ số | Dự phóng của draft | Đo được hiện tại | Ghi chú |
|---|---|---|---|
| Độ lợi so với B1 | −34,1% (Sentinel, $\Delta > 2$) | Minimax LP: **39,7%** ở $\Delta = 2$ | Đo trên LP, chưa phải Sentinel-28 |
| Sentinel so với B1 trên $L$ | Sentinel thắng | Thắng ở 64/64 ô khi $\lambda_T = 0{,}5$; chỉ 22/64 khi $\lambda_T = 0$ | Phụ thuộc mạnh vào $\lambda_T$ |
| B5 so với Sentinel | B5 = 0,359, tệ hơn Sentinel 0,272 | **B5 dẫn trước ở 61/64 ô** ($\lambda_Q = 0{,}10$) | Lệch so với giả thuyết; đo lại sau khi có Sentinel-28 |
| Crossover | $\Delta \approx 2{,}1$ | Không có điểm hoà vốn ở $\Delta \le 1$ | Cùng hướng với Hệ quả 5 |
| RQ4: lợi thế lớn nhất ở detector yếu | 21,4%–39,8%, lớn nhất ở detector yếu | Không lớn nhất ở detector yếu (MockAgent) | Ngược giả thuyết |
| Tác động của $\chi$ | Thu hẹp độ lợi, làm chậm crossover | Neo $\bar\kappa$: không tác động (39,7% ở mọi $\chi$); neo $\kappa_{\min}$: 39,7% → 36,1% | Phụ thuộc quy ước chuẩn hoá |
| Ngẫu nhiên hoá > thích nghi | Bỏ randomization tốn 0,184 harm | Ví dụ 4×4 khớp | Ablation đầy đủ chưa chạy |
| Held-out; exploitability | 27,6%; 0,34 → 0,09 | Chưa đo | Cần attacker best-response và held-out 7/18 |
| $\rho$; regret | 0,07; 0,09 | $\rho = 0{,}894$ (proxy) | Chưa so được |
| Cách ly nhầm | 3,2% → 5,1% | Chưa đo trên điểm cuối chính | — |
| Detector bề mặt | — | $d' \le 0{,}50$, dưới $d'^{*} = 2{,}85$ | Phát hiện mới |
| Detector nội dung | — | AUC 0,479 ($D_{\text{lex}}$) · 0,518 ($D_{\text{llm}}$) khi attacker không tự khai báo | Phát hiện mới |
| Agent thật làm theo payload | Draft dùng agent mô phỏng | **0/7** (arm chính) · 0/3 (arm trần) | Ngoài thiết lập draft; đưa vào mục Threats |

Nguồn dữ liệu: `auditgame/spikes/sweep-v2-pinned.json`, `sweep-v2-following.json`, `t2-chi-results.json`, `dprime-band.json`, `gamma-empirical.json`, `content-detector.json`, `band_curve.json`, `p2-pilot.jsonl`, `p2-ceiling-raw.jsonl`.

### 3.4 Issue cần xử lý

Xếp theo mức ưu tiên cho mốc đóng băng 30/09.

| # | Issue | Ảnh hưởng | Hướng xử lý |
|---|---|---|---|
| 1 | Ô $\Delta = 4$ của cổng v2 đỏ; test *matched* mới đỏ | Quyết định khung bài ở ngày 6 | Chốt trước: chứng nhận $\Delta \in \{0,2\}$ hay lùi khung B |
| 2 | $\kappa_{\text{commit}}$ chưa đo ⇒ **dấu của RQ1 chưa xác định** | Thang USD cho SentinelW thắng B1 **+25,0% harm**; thang CPU cho B1 đứng đầu. Toàn bộ khác biệt quy về một số, ngưỡng lật nằm giữa hai giá trị hiện có | Chạy tập `PASS_TO_PASS` trên repo đã clone, dựng venv trên máy chủ (`Dockerfile` ở gốc là môi trường của **agent**, `PIP_NO_INDEX=1`, không dùng được). Báo $T_{\text{test}}$ và giá hoà vốn $r^{*}$, không chốt giá VM. Nếu không kịp: báo theo lưới và khai 4,00 là **giả định**, 1,43 là **cận dưới** |
| 3 | Chưa có thư viện 28 policy (Sentinel của draft) | Mọi so sánh với Bảng 2 của draft chưa có nghĩa | Dựng theo lưới ở §1.1; chờ thầy chốt phạm vi |
| 4 | 12/18 attacker, chưa có best-response | Không đo được held-out 27,6% và exploitability | Thêm 6 kịch bản; best-response brute-force trên $(k,\iota,\sigma)$, tái dùng `tools/evaluate_exploitability.py` |
| 5 | Chưa có freeze manifest và cơ chế từ chối | Không chứng minh được "không tune sau khi thấy kết quả" | `frozen/` + `MANIFEST.sha256` + kiểm hash trong harness, khoảng nửa ngày |
| 6 | Marker là hằng `"raw_write"` | Không đạt yêu cầu duy nhất mỗi lần chạy (§3.5 phương pháp luận) | `blake2b(repo \| ι \| σ \| seed)[:16]` |
| 7 | $\lambda_T$, $\pi_0$, quy ước $\chi$ chưa neo | Ba lựa chọn này đổi thứ hạng chính sách | Neo trên dev theo §1.3, đóng băng trước khi chạy held-out |
| 8 | Chưa có 240 game nhỏ; $\rho$ đo trong không gian proxy | Mệnh đề 6 chưa kiểm chứng được | W7 ở [§4](#4-kế-hoạch-bổ-sung-đưa-các-hạng-mục-còn-thiếu-vào-sprint); chỉ làm nếu thư viện 28 policy kịp |
| 9 | Gate 1 có 13 test chưa chạy (Docker) | Gate 1 ở trạng thái UNKNOWN | Dựng image `auditgame:latest`, chạy lại |
| 10 | Chỗ draft chưa chốt: $\chi = 1{,}34$; dòng ablation "bỏ benign-drift" (0,264) thấp hơn Sentinel đầy đủ (0,272); 15 repo so với 12 của SWE-bench | Ảnh hưởng cách trình bày phần so sánh | Hỏi thầy ý định thiết kế |
| 11 | Số tiền đăng ký của cổng v2 (0,519 / 0,529) khác giá trị cận in ra trong test hôm nay (0,5117 / 0,5247) | Có thể là thống kê khác nhau; cần xác nhận cổng đã đóng băng tái lập được | Chạy lại phép chứng nhận và đối chiếu trước ngày 6 |
| 12 | `costs.install()` vẫn cài $\eta_Q$ **placeholder** (rẻ hơn giá đo 54×) | Mọi bảng USD công bố trước 23/09, kể cả `spikes/ssg-sweep-usd.json`, chạy trên giá cách ly sai | Chuyển `install()` sang `eta_q(k)` đo được rồi chạy lại các spike USD; giá đúng **cải thiện** SentinelW nên không mất kết quả |

**Phần làm vượt khỏi thiết lập draft:** sweep $d'$ liên tục, arm P2 với agent LLM thật, detector nội dung và prose world, 5 biến thể LP/SSG, sealed trace. ($\kappa$ theo USD không còn là phần làm thêm — nó là **thang vận hành** đã chốt.) Sweep $d'$ và P2 cho ra hai phát hiện mạnh nhất nên giữ. Không mở spike mới trước hạn nộp.

### 3.5 Kiểm thử

`tests/run_all.py --all` chạy lại **23/09/2026** sau khi đổi $\pi_0$, nối `checkpoints.py` và sửa biên độ ngân sách trong `Policy.can()` (khoảng 7,5 phút): **765 đạt · 2 không đạt · 13 bỏ qua**. Hai lỗi là **đúng hai lỗi cũ** — không có hồi quy nào.

| Cổng | Kết quả |
|---|---|
| Gate 1 — Integrity | 547/560 (+9 test mới về nguồn gốc chi phí và 4 checkpoint), 13 bỏ qua nên vẫn tính là *UNKNOWN* |
| Gate 2 — Validity | 203/205, **đỏ** |
| Gate 3 — Power | 15/15 |

- Không đạt: `test_benign_corpus…test_one_split_cannot_decide_a_delta_of_the_certify_corpus`, một phát hiện đã ghi nhận: corpus đủ mạnh khiến tiêu chí đa phân hoạch mất tác dụng.
- Không đạt: `…some_epsilon_makes_the_payload_indistinguishable_at_every_delta` (pipeline `matched`, pha `screen`). Không $\varepsilon \in \{0;\ 0{,}2;\ 0{,}4;\ 0{,}7;\ 1{,}0\}$ nào đưa trung vị AUC ở $\Delta = 4$ xuống dưới trần (0,608 / 0,607 / 0,642 / 1,0 / 1,0). Liên quan trực tiếp tới điểm rẽ ngày 6.
- 13 bỏ qua: Docker daemon không chạy, cần image `auditgame:latest` (`docker build -t auditgame:latest .`).

---

## 4. Kế hoạch bổ sung: đưa các hạng mục còn thiếu vào sprint

Các hạng mục dưới đây trước đây xếp "sau hạn 02/10". Nay đưa vào sprint để tái lập đúng thiết lập draft. Thứ tự theo phụ thuộc: **W1 phải xong trước**, vì đổi $\pi_0$ làm sinh lại bảng $\tau_{\text{sel}}$ và chạy lại mọi bảng kết quả. W2–W5 độc lập nhau nên chạy song song được.

| # | Hạng mục | Việc cụ thể | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| W1 | $\pi_0$, $b_0$ suy dẫn | Thay giá trị gán 0,10 bằng $\pi_0 = 1/12{,}51 = 0{,}080$ (thế giới) và 0,040 (mô hình); sinh lại `reference/score_table.json`; quét $\pi_0 \in \{0{,}04;0{,}08;0{,}10;0{,}20\}$ để xem thứ hạng có đổi không | — | ✅ **Xong 23/09** — bảng sinh lại (23 phút), ba cổng không có test nào gãy; phần quét còn lại |
| W2 | $\eta_Q$ | $\eta_Q(k) = c_{\text{detach}}(k) + c_{\text{restore}}(k)$: đo phần gỡ bằng hiệu CPU-time khi che carrier; phần phục hồi tính từ $n_{\text{live}}(k)$ đã đo (`costs.ITEMS_PER_AUDIT`); kiểm $\eta_Q(k) > \kappa(k)$ | — | ✅ **Xong 23/09** — `tools/measure_eta_q.py`, ra **61,5×**. Phần gỡ đo ra $\le 0$ ⇒ là **cận dưới**; `costs.install()` còn phải chuyển sang giá này (issue #12) |
| W3 | $\beta_k$ | Khai báo luật ánh xạ commit → carrier; đếm trên cửa sổ commit giữa hai task của 10 repo đã clone trong `auditgame/workspace/`; báo trung vị và dải theo repo; phân tích độ nhạy với một luật thay thế | — | ✅ **Xong 23/09** — `tools/measure_beta.py`. Hai luật lệch 10× ở skill ⇒ theo tiêu chí khai trước, skill và queue **chuyển sang M2 (quét)** |
| W4 | $\kappa$ và thang chi phí | Đổi đồng hồ sang `process_time`; **hiện thực 4 checkpoint làm việc thật** (`checkpoints.py`) vì trước đó CPU-time đo bộ mô phỏng; so ba thang trên cùng một lưới (`tools/compare_cost_scales.py`) | — | ✅ **Xong 23/09** — $\chi$: 1,349 (USD) / 1,295 (CPU) / 2,114 (draft). **Chốt USD làm thang vận hành.** Còn lại: $\kappa_{\text{commit}}$ (issue #2) |
| W5 | $\Delta$ thực trên SWE-bench | Co-change (support, confidence) + lọc bằng đồ thị import trên 10 repo đã clone. **Đề xuất thay `git bisect` bằng SZZ** (`git blame` trên dòng mà gold patch sửa): bisect cần môi trường chạy được test ở mọi commit, tốn Docker cho từng repo | — | ✅ **Xong 23/09** — `measure_delta_swebench.py` + `measure_cochange.py`. Chỉ **19%** instance có $\Delta \ge 2$; chỉ **19%** cặp co-change mạnh có đường import thật |
| W6 | Hằng số $c$ (Định lý 4) | Tìm $B_{\min}$ bằng tìm kiếm nhị phân trên ngân sách, lấy mốc là khối lượng posterior đặt lên window thật tại $\sigma$; tính $c$ từng ô rồi lấy max; hồi quy $\log c$ theo ba thừa số để kiểm dạng hàm của cận | W1 | 🔴 **Từ chối đo 23/09** — tiền đề hỏng: posterior đứng yên ở 0,000336 từ $B = 2$ tới 200 vì belief nhận tín hiệu **mọi** carrier mỗi task ⇒ quan sát miễn phí. Phải sửa mô hình quan sát trước (quyết định T1) |
| W7 | 240 game nhỏ + $\rho$ | Sinh lớp game nhỏ ($K \cdot H \le 40$), giải chính xác bằng LP hiện có; đo $\rho$ bằng TV trên vector xác suất hành động **theo từng task**, thay cho không gian proxy hiện tại; so với cận $H\rho\,\text{range}(L)$ của Mệnh đề 6 | Thư viện 28 policy (issue #3) | ⏳ Chưa bắt đầu |
| W8 | Payload đã công bố | Port khuôn payload AgentPoison (trigger tối ưu hoá) và MINJA (bridging step + indication prompt) thành 2 attacker kịch bản, tính vào lớp 18 attacker | Issue #4 | ⏳ Chưa bắt đầu |
| W9 | Nền lành tính thật, $N = 500$, 3 attacker LLM | Chạy trên toàn bộ 500 instance SWE-bench Verified với nền lành tính thật và attacker LLM | W8; ngân sách LLM | ⏳ Chưa bắt đầu |
| W10 | Biện hộ các tham số thiết kế | Sinh bằng chứng cho những số mà draft nêu nhưng không có nguồn: ablation $K = 2, 3$; phân phối độ dài workflow để chọn $H$; phân tích lực để chọn $N$ và số seed; $\rho$ bão hoà để biện hộ con số 28; ngưỡng AUC suy từ CI thay vì lấy 0,56 | W7 (cho $\rho$) | ⏳ Chưa bắt đầu |

Kế hoạch triển khai chi tiết theo từng bước: [đợt 1 — W1–W10](docs/design/plans/2026-09-22-W1-W10-tham-so.md) · [đợt 2](docs/design/plans/2026-09-23-tham-so-dot-2.md) · **[đợt 3 — chín tham số còn lại](docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md)** (P1 $\kappa_{\text{commit}}$ · P2 $c$ · P3 $\lambda$ · P4 $\rho$ · P5–P7 các phép quét · P8 chênh lệch ràng buộc · P9 biện hộ thiết kế).

---

## Tài liệu

1. **[Phương pháp luận (bản đầy đủ)](docs/AuditGame-SE_Sentinel_Methodology_Full.md)** — tài liệu chuẩn cho khung stage của README này: bài toán, mô hình, lý thuyết, triển khai theo 11 stage, nguồn gốc tham số, đe doạ tính hợp lệ.
2. **[Phương pháp luận triển khai (bản có đối chiếu)](docs/Phuong-phap-luan-trien-khai.md)** — cùng nội dung, có thêm phần đối chiếu với kết quả đã đo.
3. **[Khảo sát nguồn](docs/Khao-sat-nguon-phuong-phap-luan.md)** — cơ sở trích dẫn cho tài liệu chính, kèm lệnh chạy harness và kế hoạch thực hiện.
4. **[Parameter Estimation Report](docs/AuditGame-SE_Parameter_Estimation_Report.md)** — bốn phương thức xác lập, kết quả các đại lượng đã ước lượng, thủ tục cho các tham số chưa xác lập.
5. **[Parameter Measurement Runbook](docs/AuditGame-SE_Parameter_Measurement_Runbook.md)** — đợt đo 23/09: từng tham số đo thế nào, lệnh chạy từng bước, kết quả và cái gì còn thiếu. Mục §1.7d chốt đơn vị của $\kappa$.
6. **[Parameter Measurement Charts](docs/AuditGame-SE_Parameter_Measurement_Charts.html)** — cùng số liệu, dạng biểu đồ đọc được trong một lượt.
7. **[Draft của thầy (bản tiếng Việt)](docs/thesis/FSE-2027-15-paper-vi.md)** — nguồn của các giá trị dự phóng.

Mục lục đầy đủ: [docs/README.md](docs/README.md).

## Cấu trúc

```
Sentinel/
├── README.md            báo cáo tiến độ (trang này)
├── Dockerfile           môi trường của AGENT (không phải của phép đo)
├── pyproject.toml, uv.lock
├── docs/                tài liệu phương pháp luận
└── auditgame/           benchmark — chạy mọi lệnh từ trong thư mục này
    ├── core.py build.py runner.py policies.py detector.py oracle.py …
    ├── analysis/        corpus benign, discriminator, cổng 2
    ├── hidden_tests/    oracle test ẩn
    ├── payloads/        payload đóng băng và bộ sinh
    ├── reference/       bảng tra đi kèm mã (score_table.json, gate2_v2.json)
    ├── spikes/          script thí nghiệm và dữ liệu kết quả .json/.jsonl
    ├── scripts/ tools/  tiện ích đo đạc
    ├── results/         trace công khai (M3-trace.json)
    └── tests/           ba cổng kiểm thử: gate1_integrity · gate2_validity · gate3_power
```

## Chạy

Lõi đo lường chỉ dùng thư viện chuẩn của Python. Các module được import phẳng (`import core`), nên **mọi lệnh chạy từ trong `auditgame/`**.

```bash
cd auditgame
python3 experiment.py --n 40                 # quét lưới (Δ × χ × detector) trên MockAgent (vài phút)
python3 spikes/trace_one_episode.py          # in một ván chạy đầu-tới-cuối
python3 tests/run_all.py                     # ba cổng kiểm thử, dừng ở cổng đỏ đầu tiên
python3 tests/run_all.py --all               # chạy cả ba cổng (khoảng 7 phút)
```

Phần phân tích (scipy, scikit-learn) và công cụ SWE-bench cần môi trường đầy đủ: `uv sync`, rồi chạy bằng `../.venv/bin/python`.

Các lượt chạy với LLM thật có chi phí và không tái lập được theo seed. Kết quả của chúng được lưu tại `auditgame/spikes/*.jsonl` và chỉ được đọc lại, không chạy lại.
