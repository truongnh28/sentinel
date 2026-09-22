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
| **Khung bài đã chốt** | **A′ — "bản đồ chế độ"** (chốt 18/09 tại điểm rẽ ngày 4). Trên thiết lập hiện tại, Sentinel thắng audit-at-commit (B1) trên hàm mất mát $L$ nhưng **thua B5 risk-score**. Bài phát biểu về *ranh giới chế độ*, không về Sentinel. |
| **Đang ở bước** | Stage 4 (chứng nhận cổng v2, ngày 6) và chuẩn bị Stage 8 (đóng băng). Stage 6 và 9 mới chạy trên thiết lập rút gọn, chưa đúng thiết lập draft (xem [§3.1](#31-tổng-quan-theo-stage)). |
| **Mốc kế tiếp** | **Ngày 6 (23/09):** chạy bảng chứng nhận cổng v2 một lần. Có attacker hợp lệ qua cổng thì giữ A′, không có thì lùi về **khung B** (benchmark tự phản biện). |
| **Rủi ro lớn nhất** | (1) Ô $\Delta = 4$ của cổng v2 vẫn đỏ. (2) Thiết lập draft (thư viện 28 policy, 18 attacker, attacker best-response, freeze) chưa dựng, ước tính 5–7 ngày công, sát mốc đóng băng 30/09. (3) Agent thật làm theo payload **0/7**, nên mọi số harm hiện có là harm dưới mô hình tiếp nhận của MockAgent. |
| **Kiểm thử** | `tests/run_all.py --all` ngày 22/09: **756 đạt · 2 không đạt · 13 bỏ qua**. Cổng 1 *UNKNOWN* (13 test cần Docker chưa chạy), cổng 2 đỏ 203/205, cổng 3 xanh 15/15 (chi tiết ở [§3.5](#35-kiểm-thử)). |

## Được bao nhiêu phần trăm

Đếm theo **hạng mục bàn giao được**: 51 hạng mục, chia tám nhóm. Quy ước: **✅ xong = 1 · 🟡 một phần = 0,5 · ❌ chưa làm = 0**.

**Tổng: 31,5 / 51 = 62%.**

| Nhóm | Tiến độ | Hạng mục |
|---|---|---|
| **A. Hạ tầng benchmark** | **89%** (8/9) | ✅ CarrierStore bốn carrier · ✅ Workflow từ SWE-bench Verified · ✅ Retrieval Jaccard với $\theta$ · ✅ MockAgent · ✅ Agent LLM thật (P2) · ✅ Oracle marker · 🟡 Oracle test ẩn (neo được 1/500) · ✅ Replay và sealed trace · 🟡 Harness Docker (13 test chưa chạy) |
| **B. Tấn công và ground truth** | **43%** (3/7) | ✅ Sinh $(\iota,\sigma)$ có lọc nổ sớm · ✅ Payload đóng băng và bộ sinh · 🟡 Thư viện attacker kịch bản (12/18) · ❌ Attacker best-response đọc $\pi_D$ · ❌ Marker duy nhất mỗi lần chạy · 🟡 Đo $\Delta$ thực (mới trên repo đề tài) · ❌ Validate harm trên tập con |
| **C. Corpus lành tính và cổng** | **50%** (2,5/5) | ✅ Corpus từ item SWE-bench thật · ✅ Ghép theo 5 đặc trưng bề mặt · 🟡 Cổng AUC v2, 20 split ($\Delta = 4$ còn đỏ) · ❌ Permutation test · ❌ $\beta_k$ |
| **D. Detector và tín hiệu** | **90%** (4,5/5) | ✅ Detector mô phỏng theo $d'$ · 🟡 Ba mức $(\psi,\varphi)$ của draft chạy như lưới riêng · ✅ CarrierSignal mean và bảng $\tau_{\text{sel}}$ · ✅ Sweep $d'$ liên tục, ra $d'^{*}$ · ✅ Detector nội dung $D_{\text{lex}}$, $D_{\text{llm}}$ |
| **E. Chính sách và lý thuyết** | **69%** (5,5/8) | ✅ B1–B6 · ✅ Minimax LP · ✅ Các biến thể SSG · ✅ Belief tính chính xác · ❌ Thư viện 28 policy · ❌ 240 game nhỏ giải chính xác · 🟡 $\rho$ (đang đo trong không gian proxy) · ✅ $\zeta$ |
| **F. Đo lường và kết quả** | **31%** (2,5/8) | ✅ Lưới $\Delta$ × detector trên MockAgent · ❌ Trục $\chi$ trong đường chính · ❌ $\Delta = 8$ · 🟡 100 workflow (hiện 40) · ❌ Worst-case trên held-out · ❌ Exploitability · ❌ Ablation đầy đủ · ✅ CI bootstrap theo cụm |
| **G. Tính toàn vẹn** | **50%** (2,5/5) | ✅ Ba cổng kiểm thử, 771 test · ✅ Tài liệu tiền đăng ký · 🟡 Digest rời (cổng v2, payload, prompt) · ❌ Manifest đóng băng toàn phần · ❌ Harness từ chối policy chưa đóng băng |
| **H. Tài liệu** | **75%** (3/4) | ✅ Phương pháp luận · ✅ Parameter Estimation Report · ✅ Reports và báo cáo tiến độ · ❌ Bản thảo ACM |

**Đọc các con số này thế nào.**
1. **Nhóm A và D gần xong, nhóm F mới 31%.** Cỗ máy đo đã chạy được, nhưng phần lớn *số để đưa vào bài* thì chưa có. Câu trả lời cho "bài viết được bao nhiêu" là **15–20%**, không phải 62%.
2. **Ba hạng mục kéo tụt cả ba nhóm B, E, G:** thư viện 28 policy, attacker best-response, manifest đóng băng. Làm xong ba thứ này thì nhóm F mở khoá theo, vì worst-case trên held-out và exploitability đều phụ thuộc chúng. Cả ba nằm trong [§3.4](#34-issue-cần-xử-lý) và [§4](#4-kế-hoạch-bổ-sung-đưa-các-hạng-mục-còn-thiếu-vào-sprint).
3. **Một phần công đã bỏ ra không nằm trong 51 hạng mục này:** hơn 60 spike, arm P2, detector nội dung, năm biến thể SSG. Chúng cho ra bốn phát hiện dưới đây, nhưng trong bản nộp nhiều thứ chỉ còn một dòng ở mục Threats.

**Bốn phát hiện đã có, không phụ thuộc phần còn thiếu:**
1. Detector bề mặt chỉ đạt $d' \le 0{,}50$, trong khi điểm hoà vốn so với audit-at-commit là $d'^{*} = 2{,}85$ ở $\Delta = 2$.
2. Detector nội dung sụp về ngẫu nhiên (AUC 0,479–0,518) khi attacker không tự khai báo.
3. Agent LLM thật không làm theo lời khuyên độc: 0/7 instance.
4. Không tồn tại điểm hoà vốn ở $\Delta \le 1$, khớp với Hệ quả 5 của draft.

---

## Lịch nước rút 14 ngày

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

### Ngày 6–14 (23/09–02/10) — còn lại

| Ngày | Việc phải xong | Đầu ra phải có | Ràng buộc |
|---|---|---|---|
| **6 — 23/09** | Chạy bảng chứng nhận v2 **một lần** → **điểm rẽ v2** | Bảng chứng nhận cho từng $\Delta$; chọn nhánh A′ hay B | Hiện $\Delta=0$ và $\Delta=2$ qua 20/20 split (0,519 và 0,529), $\Delta=4$ đỏ (0,587); pipeline *matched* cũng đỏ ở $\Delta=4$ (0,607–0,642). **Phải chốt trước khi chạy:** $\Delta=4$ vẫn đỏ thì chỉ chứng nhận $\Delta \in \{0,2\}$, hay lùi khung B |
| 7–9 — 24–26/09 | Chuỗi bảng $m$; lưới $N = 100$ trên MockAgent; G4 nhãn mù | $d'$ hiệu dụng theo $m$; lưới kết quả ở quy mô đủ; agreement của judge | **Hạn cứng G4: 26/09** |
| 7–11 (song song) | Dựng thiết lập draft: thư viện 28 policy, 18 attacker kèm best-response, freeze manifest, marker duy nhất — [issue #2–#5](#34-issue-cần-xử-lý) | Bảng kết quả chính so được với draft: worst-case trên held-out, exploitability | Chờ thầy chốt phạm vi |
| 7–11 (song song) | Đo các tham số còn gán tay: [W1–W6](#4-kế-hoạch-bổ-sung-đưa-các-hạng-mục-còn-thiếu-vào-sprint) | $\pi_0$, $\eta_Q$, $\beta$, $\kappa$ theo CPU-time, $\Delta$ thực, hằng số $c$ | W1 phải xong trước, vì đổi $\pi_0$ là phải sinh lại bảng $\tau_{\text{sel}}$ và chạy lại mọi bảng |
| 10–11 — 27–28/09 | Viết Evaluation, Threats, ablation RQ4 | Bản nháp các mục kết quả | Phụ thuộc hai dòng trên |
| 12 — 30/09 | **Đóng băng số**; chạy ba cổng lần cuối; artifact ẩn danh | Manifest hash; ba cổng xanh (hoặc đỏ có giải trình) | Sau mốc này không tham số nào được chỉnh |
| 13–14 — 01–02/10 | Bản cuối, format ACM, **nộp** | Bản nộp | Hạn 02/10 AoE |

**Điểm nghẽn.** Ba dòng của ngày 7–11 cộng lại khoảng **17 ngày công** nhưng chỉ có **5 ngày lịch**. Vì vậy phải cắt, và thứ tự ưu tiên đề xuất là: (1) thiết lập draft, vì không có nó thì không có bảng kết quả chính; (2) W1–W6, vì đây là phần biến "giá trị gán" thành "giá trị đo"; (3) chuỗi bảng $m$ và $N = 100$ ở quy mô rút gọn nếu cần.

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
| $\kappa(k)$ | 0,4 / 0,9 / 1,6 / 4,1 | M1 | **Tự đo** theo CPU-time: 4 checkpoint × ≥ 30 lần, user+sys, cố định tần số CPU, lấy trung vị. Bảng của draft chỉ là mốc đối chiếu | [PPL] Stage 2 · [PER] 5.6 |
| $\chi$ | 1,34 | M1 | Tính từ $\kappa$ mình đo, với công thức $\bar\kappa$ công bố trước. Hiện ra 2,11 (bảng draft) và 1,349 (bảng đo) — chênh lệch này phải báo cáo, không được chỉnh công thức để ra 1,34 | [PPL] Stage 2 · [PER] 5.7 |
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

| Stage | Việc phải làm | Đầu ra | Kết quả kỳ vọng |
|---|---|---|---|
| 0 | Viết tuple game; thứ tự cam kết; defender chỉ nhận `CarrierSignal(p, n)` | Đặc tả luật chơi | Cạnh bị cấm vắng mặt trong chữ ký hàm, có test cưỡng chế |
| 1 | Dựng workflow từ SWE-bench: sort `created_at`, cắt cửa sổ 6–14 task, topic từ gold patch, retrieval Jaccard với $\theta$ chốt trên dev | Danh sách workflow | 100 workflow; $\theta$ chốt trước khi nhìn kết quả; lọc instance flaky |
| 2 | Hiện thực 4 checkpoint audit; đo CPU-time; tính $\chi$ | $\kappa$, $\chi$ | Bảng $\kappa$ có sai số; draft dự phóng $\chi = 1{,}34$ |
| 3 | 18 attacker (7 held-out); sinh $(\iota,\sigma)$ theo $\Delta$ có lọc nổ sớm; marker duy nhất mỗi lần chạy; oracle harm; đo $\Delta$ thực | Thư viện attacker, oracle | Oracle validate trên tập con; phân phối $\Delta$ thực cùng thang với crossover |
| 4 | Corpus lành tính khớp bề mặt; cổng AUC; ước lượng $\beta_k$ | Corpus, AUC, $\beta$ | AUC ≤ 0,56 kèm CI và permutation test; 620 mẫu |
| 5 | Mô phỏng detector với 3 mức $(\psi,\varphi)$; CarrierSignal lấy mean posterior | Detector, $\gamma$ | Ba mức $\gamma$ = 0,55 / 0,73 / 0,86 |
| 6 | Belief; thư viện 28 policy; 240 game nhỏ giải chính xác; đo $\rho$; mở rộng thư viện bằng double oracle nếu $\rho$ lớn | Thư viện, $\rho$ | Draft: $\rho = 0{,}07$, cận Mệnh đề 6 = 0,42, regret đo được 0,09 |
| 7 | Tính tay trên game nhỏ và so với mã | Ví dụ khớp | Minimax 4×4: tất định 1,0, trộn 0,5; Bayes 0,10 → 0,44 → 0,85 |
| 8 | Đóng băng policy, attacker, hằng số, corpus, workflow bằng hash | `frozen/`, `MANIFEST.sha256`, tag `freeze-v1` | Harness tính lại hash và từ chối chạy nếu không khớp |
| 9 | Chạy lưới đầy đủ; worst-case trên held-out; exploitability; crossover; CI bootstrap theo cụm repo; hằng $c$ | Bảng kết quả trên lưới $(\Delta,\chi)$ | Draft (Bảng 2, $\Delta > 2$, $\chi = 1{,}34$, held-out): B1 0,412 → Sentinel 0,272 (−34,1%, CI [−42,6%; −25,1%], vượt ngưỡng 15%); held-out 27,6%; exploitability 0,34 → 0,09; cách ly nhầm 3,2% → 5,1%; crossover 2,1; RQ4 21,4%–39,8%, lớn nhất ở detector yếu; quét $\eta_Q$: 34,1% → 44,0% |
| 10 | Giải game; tuning chỉ trên dev, trước đóng băng | Nghiệm, ranh giới tuning | Khoảng cách dev và held-out báo cáo được (draft: 34,1% so với 27,6%) |

---

## 3. Trạng thái hiện tại

### 3.1 Tổng quan theo stage

**2 hoàn thành · 1 làm theo hướng khác · 8 một phần · 0 chưa bắt đầu.** Rà soát ngày 22/09 bằng cách đọc mã và chạy lại toàn bộ test.

| Stage | Trạng thái | Đã làm | Kết quả hiện có | Issue |
|---|---|---|---|---|
| 0 | ✅ Hoàn thành | Tuple game; loss ba số hạng (`metrics.loss`); `CarrierSignal(p, n)` chỉ có hai trường | Cạnh bị cấm cưỡng chế bằng chữ ký hàm và test | — |
| 1 | 🟡 Một phần | SWE-bench Verified đã nối; sort `created_at`; topic từ gold patch; $\theta = 0{,}5$ chốt trước khi đếm workflow | **14/58** workflow khả dụng ở $H = 8$; sweep hiện chạy 40 workflow | Thiếu workflow so với 100; chưa lọc instance flaky |
| 2 | 🟡 Một phần | Công thức $\chi$ công bố; $\kappa$ đo theo đơn giá chấm LLM | $\chi$ = 2,114 (bảng draft, $\bar\kappa$ = mean); 1,349 (bảng đo) | Chưa đo CPU-time; hai bảng **đảo thứ tự chi phí** (memory từ rẻ nhất thành đắt nhất); $\chi = 1{,}34$ của draft không ra được với công thức $\bar\kappa$ chuẩn nào |
| 3 | 🟡 Một phần | Sinh $(\iota,\sigma)$ có lọc nổ sớm; 12 attacker kịch bản; chia held-out bằng hash; đo $\Delta$ thực | $\Delta$ thực: trung vị 3, p75 10 ($n = 29$, lịch sử repo đề tài) | 12/18 attacker, đều gán cứng $(k,\Delta)$; held-out 6/12 thay vì 7/18; **chưa có attacker best-response**; **marker là hằng `"raw_write"`**; chưa có $\Delta = 8$; harm chấm bằng marker (test ẩn neo được 1/500) |
| 4 | 🟡 Một phần | Cổng v2 đóng băng 19/09: 5 đặc trưng, tiêu chí cận trên CI, 20 split; corpus từ item SWE-bench thật, ghép theo tuổi | v1 (4 đặc trưng): 0,5414. v2: $\Delta=0$ 0,519 · $\Delta=2$ 0,529 (20/20 split) · $\Delta=4$ **0,587** (1/20) | $\Delta = 4$ đỏ; 2 test cổng 2 đỏ; $\beta$ chưa đo; chưa có permutation test; ngưỡng 0,56 nằm trong dải nhiễu ở mọi $n \le 1800$ |
| 5 | ✅ Hoàn thành | Detector Gaussian theo $d'$, gộp bằng mean tỉ số likelihood; quét $d'$ liên tục; thử detector nội dung | $d'^{*}$ = 2,85 ($\Delta=2$), 0,95 ($\Delta=4$), không tồn tại ở $\Delta \le 1$; detector bề mặt $d' \le 0{,}50$ | Chưa chạy đúng 3 mức $(\psi,\varphi)$ của draft như một lưới riêng |
| 6 | 🟣 Hướng khác | Belief tính chính xác bằng liệt kê cửa sổ (thay particle filter); minimax LP và 5 biến thể SSG | Registry 17 policy; $\rho = 0{,}894$ trong không gian proxy | **Chưa có thư viện 28 policy** đóng vai "Sentinel" của draft; chưa có 240 game nhỏ; tên "B7" trong mã là LP đối thủ, còn trong draft B7 là oracle trần |
| 7 | 🟡 Một phần | `spikes/trace_one_episode.py` phát lại một episode với số thật | Minimax 4×4 khớp `game.minimax` ($V^* = 0{,}5$) | Chưa test hoá ví dụ 4×4; ví dụ Bayes Bernoulli chưa được mã kiểm |
| 8 | 🟡 Một phần | Digest rời: cổng v2, độ dài payload, prompt detector; payload đóng băng; tiền đăng ký | — | **Chưa có `frozen/`, `MANIFEST.sha256`**; harness chưa từ chối policy chưa đóng băng |
| 9 | 🟡 Một phần | Lưới $\Delta \in \{0,1,2,4\}$ × 3 detector trên MockAgent; chấm $L$; $\lambda_Q^{*}$; bootstrap theo workflow | Xem [§3.3](#33-so-với-giá-trị-dự-phóng-của-draft) | Chưa có worst-case trên held-out, exploitability, $\Delta = 8$, trục $\chi$ trong đường chính |
| 10 | 🟡 Một phần | LP Stackelberg (Conitzer–Sandholm); ranh giới tuning qua tiền đăng ký | — | Chưa có double oracle |

### 3.2 Trạng thái từng tham số

**7 hoàn thành · 3 một phần · 7 chưa thực hiện.**

| Tham số | Draft | Phương thức | Trạng thái | Giá trị hiện tại | Issue / việc còn lại |
|---|---|---|---|---|---|
| $\tau_{\text{sel}}$ | — | M1 | ✅ Hoàn thành | Bảng tham chiếu, 800.000 mẫu/ô | Sinh lại khi $\pi_0$ đổi |
| $\mathrm{AUC}_{\text{upper}}$ | ≤ 0,56 | M1 | ✅ Hoàn thành | 0,5414 (v1); cổng v2 ở §3.1 | Permutation test |
| $\varepsilon^{*}$ | — | M4 | ✅ Hoàn thành | 0; không tồn tại trên nền lành tính trung thực | — |
| $d'^{*}$ | — | M2 + M4 | ✅ Hoàn thành | 2,85 ($\Delta=2$); 0,95 ($\Delta=4$); không tồn tại ở $\Delta \le 1$ | — |
| $d'$ bề mặt | — | M1 | ✅ Hoàn thành | $\le 0{,}50$ | Thấp hơn cả mức "yếu" của draft ($d$ = 1,52) |
| $\zeta$ | — | M1 | ✅ Hoàn thành | 0,000 (mock); 0,119 khi $\beta = 0{,}5$ | Tách vai thế giới / mô hình để $\zeta$ có tác dụng |
| $\Delta$ thực | — | M1 | ✅ Đo sơ bộ | Trung vị 3, p75 10 ($n = 29$) | Quần thể đo không phải SWE-bench; cần co-change + `git bisect` |
| Chênh lệch ràng buộc | — | M1 | 🟡 Một phần | Độ phủ $-13{,}29\%$ | File kết quả chưa được commit, nên chưa tái lập được |
| $\chi$ | 1,34 | M1 | 🟡 Một phần | 2,114 (bảng draft); 1,349 (bảng đo) | Chốt quy ước chuẩn hoá khi quét |
| $\kappa(k)$ | 0,4 / 0,9 / 1,6 / 4,1 | M1 | 🟡 Một phần | Đường chính dùng bảng draft | Đo CPU-time |
| $\lambda_Q, \lambda_T$ | — | M2 + M4 | ❌ Chưa neo | Gán 0,10 / 0,50; $\lambda_Q^{*} \approx 0{,}036$–$0{,}05$ | $\lambda_T$ quyết định Sentinel thắng B1 ở 64/64 hay 22/64 ô; phải neo trước khi nhìn bảng kết quả |
| $\rho$ | 0,07 | M1 | ❌ Chưa đúng không gian | 0,894 (proxy) | Cần thư viện 28 policy và game nhỏ |
| $\eta_Q$ | — | M1 + M3 | ❌ Chưa thực hiện | Gán 2,0 | Đo phần gỡ; tính phần phục hồi |
| $\beta_k$ | — | M1 | ❌ Chưa thực hiện | Gán 0,25 | Luật ánh xạ commit → carrier |
| $\pi_0, b_0$ | — | M3 | ❌ Chưa thực hiện | Gán 0,10 | Suy dẫn 0,080 (thế giới) / 0,040 (mô hình); sinh lại $\tau_{\text{sel}}$ |
| $c$ | — | M1 | ❌ Chưa thực hiện | — | Tìm $B_{\min}$ từ posterior |
| Quy ước quét $\chi$ | — | Thiết kế | ❌ Chưa khai báo | Đề xuất neo $\kappa_{\min}$ | Khai báo trước khi chạy; báo cả ba quy ước |

Các tham số còn ❌ đã được lên lịch ở [§4](#4-kế-hoạch-bổ-sung-đưa-các-hạng-mục-còn-thiếu-vào-sprint): $\pi_0$ (W1), $\eta_Q$ (W2), $\beta_k$ (W3), $\kappa$ theo CPU-time (W4), $c$ (W6), $\rho$ (W7). Riêng $\lambda_Q, \lambda_T$ và quy ước quét $\chi$ là quyết định neo, làm cùng lúc với việc đóng băng.

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
| 2 | Chưa có thư viện 28 policy (Sentinel của draft) | Mọi so sánh với Bảng 2 của draft chưa có nghĩa | Dựng theo lưới ở §1.1; chờ thầy chốt phạm vi |
| 3 | 12/18 attacker, chưa có best-response | Không đo được held-out 27,6% và exploitability | Thêm 6 kịch bản; best-response brute-force trên $(k,\iota,\sigma)$, tái dùng `tools/evaluate_exploitability.py` |
| 4 | Chưa có freeze manifest và cơ chế từ chối | Không chứng minh được "không tune sau khi thấy kết quả" | `frozen/` + `MANIFEST.sha256` + kiểm hash trong harness, khoảng nửa ngày |
| 5 | Marker là hằng `"raw_write"` | Không đạt yêu cầu duy nhất mỗi lần chạy (§3.5 phương pháp luận) | `blake2b(repo \| ι \| σ \| seed)[:16]` |
| 6 | $\lambda_T$, $\pi_0$, quy ước $\chi$ chưa neo | Ba lựa chọn này đổi thứ hạng chính sách | Neo trên dev theo §1.3, đóng băng trước khi chạy held-out |
| 7 | Chưa có 240 game nhỏ; $\rho$ đo trong không gian proxy | Mệnh đề 6 chưa kiểm chứng được | W7 ở [§4](#4-kế-hoạch-bổ-sung-đưa-các-hạng-mục-còn-thiếu-vào-sprint); chỉ làm nếu thư viện 28 policy kịp |
| 8 | Gate 1 có 13 test chưa chạy (Docker) | Gate 1 ở trạng thái UNKNOWN | Dựng image `auditgame:latest`, chạy lại |
| 9 | Chỗ draft chưa chốt: $\chi = 1{,}34$; dòng ablation "bỏ benign-drift" (0,264) thấp hơn Sentinel đầy đủ (0,272); 15 repo so với 12 của SWE-bench | Ảnh hưởng cách trình bày phần so sánh | Hỏi thầy ý định thiết kế |
| 10 | Số tiền đăng ký của cổng v2 (0,519 / 0,529) khác giá trị cận in ra trong test hôm nay (0,5117 / 0,5247) | Có thể là thống kê khác nhau; cần xác nhận cổng đã đóng băng tái lập được | Chạy lại phép chứng nhận và đối chiếu trước ngày 6 |

**Phần làm vượt khỏi thiết lập draft:** sweep $d'$ liên tục, arm P2 với agent LLM thật, detector nội dung và prose world, 5 biến thể LP/SSG, $\kappa$ theo USD, sealed trace. Sweep $d'$ và P2 cho ra hai phát hiện mạnh nhất nên giữ. Không mở spike mới trước hạn nộp.

### 3.5 Kiểm thử

`tests/run_all.py --all` ngày 22/09/2026 (khoảng 7 phút): **756 đạt · 2 không đạt · 13 bỏ qua**.

| Cổng | Kết quả |
|---|---|
| Gate 1 — Integrity | 538/551, 13 bỏ qua nên tính là *UNKNOWN* |
| Gate 2 — Validity | 203/205, **đỏ** |
| Gate 3 — Power | 15/15 |

- Không đạt: `test_benign_corpus…test_one_split_cannot_decide_a_delta_of_the_certify_corpus`, một phát hiện đã ghi nhận: corpus đủ mạnh khiến tiêu chí đa phân hoạch mất tác dụng.
- Không đạt: `…some_epsilon_makes_the_payload_indistinguishable_at_every_delta` (pipeline `matched`, pha `screen`). Không $\varepsilon \in \{0;\ 0{,}2;\ 0{,}4;\ 0{,}7;\ 1{,}0\}$ nào đưa trung vị AUC ở $\Delta = 4$ xuống dưới trần (0,608 / 0,607 / 0,642 / 1,0 / 1,0). Liên quan trực tiếp tới điểm rẽ ngày 6.
- 13 bỏ qua: Docker daemon không chạy, cần image `auditgame:latest` (`docker build -t auditgame:latest .`).

---

## 4. Kế hoạch bổ sung: đưa các hạng mục còn thiếu vào sprint

Các hạng mục dưới đây trước đây xếp "sau hạn 02/10". Nay đưa vào sprint để tái lập đúng thiết lập draft. Thứ tự theo phụ thuộc: **W1 phải xong trước**, vì đổi $\pi_0$ làm sinh lại bảng $\tau_{\text{sel}}$ và chạy lại mọi bảng kết quả. W2–W5 độc lập nhau nên chạy song song được.

| # | Hạng mục | Việc cụ thể | Phụ thuộc | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| W1 | $\pi_0$, $b_0$ suy dẫn | Thay giá trị gán 0,10 bằng $\pi_0 = 1/12{,}51 = 0{,}080$ (thế giới) và 0,040 (mô hình); sinh lại `reference/score_table.json`; quét $\pi_0 \in \{0{,}04;0{,}08;0{,}10;0{,}20\}$ để xem thứ hạng có đổi không | — | 1 ngày | ⏳ Chưa bắt đầu |
| W2 | $\eta_Q$ | $\eta_Q(k) = c_{\text{detach}}(k) + c_{\text{restore}}(k)$: đo phần gỡ bằng hiệu CPU-time khi che carrier; phần phục hồi tính từ $n_{\text{live}}(k)$ đã đo (`costs.ITEMS_PER_AUDIT`); kiểm $\eta_Q(k) > \kappa(k)$ | — | 0,5 ngày | ⏳ Chưa bắt đầu |
| W3 | $\beta_k$ | Khai báo luật ánh xạ commit → carrier; đếm trên cửa sổ commit giữa hai task của 10 repo đã clone trong `auditgame/workspace/`; báo trung vị và dải theo repo; phân tích độ nhạy với một luật thay thế | — | 1 ngày | ⏳ Chưa bắt đầu |
| W4 | $\kappa$ theo CPU-time | Đổi phép đo trong `runner.py` từ `perf_counter` sang `process_time` (user+sys); chạy mỗi checkpoint ≥ 30 lần, lấy trung vị, báo phương sai; đối chiếu với hai bảng $\kappa$ hiện có | — | 0,5 ngày | ⏳ Chưa bắt đầu |
| W5 | $\Delta$ thực trên SWE-bench | Co-change (support, confidence) + lọc bằng đồ thị import trên 10 repo đã clone. **Đề xuất thay `git bisect` bằng SZZ** (`git blame` trên dòng mà gold patch sửa): bisect cần môi trường chạy được test ở mọi commit, tốn Docker cho từng repo | — | 1,5 ngày | ⏳ Chưa bắt đầu |
| W6 | Hằng số $c$ (Định lý 4) | Tìm $B_{\min}$ bằng tìm kiếm nhị phân trên ngân sách, lấy mốc là khối lượng posterior đặt lên window thật tại $\sigma$; tính $c$ từng ô rồi lấy max; hồi quy $\log c$ theo ba thừa số để kiểm dạng hàm của cận | W1 | 1 ngày | ⏳ Chưa bắt đầu |
| W7 | 240 game nhỏ + $\rho$ | Sinh lớp game nhỏ ($K \cdot H \le 40$), giải chính xác bằng LP hiện có; đo $\rho$ bằng TV trên vector xác suất hành động **theo từng task**, thay cho không gian proxy hiện tại; so với cận $H\rho\,\text{range}(L)$ của Mệnh đề 6 | Thư viện 28 policy (issue #2) | 2 ngày | ⏳ Chưa bắt đầu |
| W8 | Payload đã công bố | Port khuôn payload AgentPoison (trigger tối ưu hoá) và MINJA (bridging step + indication prompt) thành 2 attacker kịch bản, tính vào lớp 18 attacker | Issue #3 | 1 ngày | ⏳ Chưa bắt đầu |
| W9 | Nền lành tính thật, $N = 500$, 3 attacker LLM | Chạy trên toàn bộ 500 instance SWE-bench Verified với nền lành tính thật và attacker LLM | W8; ngân sách LLM | 3+ ngày | ⏳ Chưa bắt đầu |
| W10 | Biện hộ các tham số thiết kế | Sinh bằng chứng cho những số mà draft nêu nhưng không có nguồn: ablation $K = 2, 3$; phân phối độ dài workflow để chọn $H$; phân tích lực để chọn $N$ và số seed; $\rho$ bão hoà để biện hộ con số 28; ngưỡng AUC suy từ CI thay vì lấy 0,56 | W7 (cho $\rho$) | 1,5 ngày | ⏳ Chưa bắt đầu |

Kế hoạch triển khai chi tiết theo từng bước sẽ được viết riêng trong `docs/design/plans/`.

---

## Tài liệu

1. **[Phương pháp luận (bản đầy đủ)](docs/AuditGame-SE_Sentinel_Methodology_Full.md)** — tài liệu chuẩn cho khung stage của README này: bài toán, mô hình, lý thuyết, triển khai theo 11 stage, nguồn gốc tham số, đe doạ tính hợp lệ.
2. **[Phương pháp luận triển khai (bản có đối chiếu)](docs/Phuong-phap-luan-trien-khai.md)** — cùng nội dung, có thêm phần đối chiếu với kết quả đã đo.
3. **[Khảo sát nguồn](docs/Khao-sat-nguon-phuong-phap-luan.md)** — cơ sở trích dẫn cho tài liệu chính, kèm lệnh chạy harness và kế hoạch thực hiện.
4. **[Parameter Estimation Report](docs/AuditGame-SE_Parameter_Estimation_Report.md)** — bốn phương thức xác lập, kết quả các đại lượng đã ước lượng, thủ tục cho các tham số chưa xác lập.
5. **[Draft của thầy (bản tiếng Việt)](docs/thesis/FSE-2027-15-paper-vi.md)** — nguồn của các giá trị dự phóng.

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
