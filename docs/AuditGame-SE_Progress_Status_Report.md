# Sentinel / AuditGame-SE: Implementation Phases and Current Status

**Đề tài:** FSE-2027-15 · **Học viên:** Nguyễn Hữu Trưởng · **GVHD:** TS. Lê Xuân Bách
**Ngày:** 22/09/2026 · **Mốc code:** `efb951e` (repo Sentinel)

---

## Tình hình trong 30 giây

| | |
|---|---|
| **Đang làm** | Nước rút nộp **FSE 2027 Research Papers**, hạn **02/10/2026 AoE**. Hôm nay là **ngày 5/14**, còn **10 ngày**. |
| **Khung bài đã chốt** | **A′ — "bản đồ chế độ"** (chốt 18/09 tại điểm rẽ ngày 4): Sentinel thắng audit-at-commit (B1) trên hàm mất mát $L$, nhưng **thua B5 risk-score**. Bài phát biểu về *ranh giới chế độ*, không về Sentinel. |
| **Mốc kế tiếp** | **Ngày 6 (23/09)** — bảng chứng nhận cổng v2: có attacker hợp lệ qua cổng thì giữ A′, không có thì lùi về **khung B** (benchmark tự phản biện). |
| **Rủi ro lớn nhất** | Trên agent thật (P2), tỉ lệ làm theo payload là **0/7** ⇒ mọi số harm hiện có là harm dưới mô hình MockAgent. |
| **Kiểm thử** | `tests/run_all.py --all` ngày 22/09: **756 đạt · 1 không đạt · 13 bỏ qua**. Test không đạt là một phát hiện đã ghi nhận (corpus đủ mạnh khiến tiêu chí đa phân hoạch mất tác dụng); 13 bỏ qua do chưa dựng image Docker. |

## Cần thầy quyết

1. **Cách viết Đe doạ 3 (P2, 0/7 tuân thủ).** Giữ tuyên bố với nhãn *"harm dưới mô hình tiếp nhận của MockAgent"*, hay chạy thêm arm model thứ hai (hiện chưa chạy) trước khi đóng băng số ngày 30/09?
2. **Quy ước chuẩn hoá khi quét $\chi$.** Neo $\bar\kappa$ (hiện hành) làm trục $\chi$ rỗng theo cấu trúc; neo $\kappa_{\min}$ làm $\chi$ có tác dụng. Lựa chọn quyết định trục $\chi$ của ranh giới vùng có nội dung hay không.
3. **Vai trò của $(\psi,\varphi)$.** Detector bề mặt chỉ đạt $d' \le 0{,}50$, detector nội dung sụp về ngẫu nhiên khi attacker không tự khai báo. Coi $(\psi,\varphi)$ là biến kiểm soát thuần tuý, hay nêu điều kiện "cần detector đạt $d'^\*$" làm kết luận chính?

---

## 1. Tiến độ theo 11 stage của phương pháp luận

Khung stage theo `AuditGame-SE_PartIV_Detailed.md`. Trạng thái: **Hoàn thành** · **Một phần** · **Làm theo hướng khác** (lệch có chủ ý, đã ghi lý do) · **Chưa thực hiện**.

| Stage | Nội dung | Trạng thái | Đã có | Còn thiếu |
|---|---|---|---|---|
| 0 | Giả định, luật chơi | Hoàn thành | Tuple game; hàm mất mát ba số hạng; defender chỉ nhận `CarrierSignal(p, n)` — cạnh bị cấm cưỡng chế bằng chữ ký hàm và test | — |
| 1 | Môi trường, workflow SWE-bench | Một phần | SWE-bench Verified đã nối; sort `created_at`; topic từ gold patch; $\theta = 0{,}5$ chốt trước khi đếm workflow | Chỉ **14/58** workflow khả dụng ở $H=8$ (cần 100); chưa lọc instance flaky |
| 2 | Chi phí audit $\kappa \to \chi$ | Một phần | Công thức $\chi$ công bố ($2{,}11 \ne 1{,}34$ của bản thảo); $\kappa$ đo theo đơn giá chấm LLM | Chưa đo theo CPU-phút; thí nghiệm chính vẫn dùng bảng bản thảo; quy ước quét $\chi$ chưa chốt |
| 3 | Attacker, ground truth, oracle | Một phần | Sinh $(\iota,\sigma)$ có lọc nổ sớm; 12 attacker kịch bản, 6 held-out chia bằng hash; $\Delta$ thực đo được (trung vị 3) | 18 attacker; attacker best-response đọc $\pi_D$; marker duy nhất mỗi lần chạy; $\Delta = 8$; harm vẫn chấm bằng marker (test ẩn neo được 1/500) |
| 4 | Corpus lành tính, cổng AUC, $\beta$ | Hoàn thành | Cổng v2 đóng băng 19/09: 5 đặc trưng, tiêu chí cận trên CI, 20 split; corpus từ item SWE-bench thật, ghép theo tuổi | $\beta$ chưa đo; chưa có permutation test |
| 5 | Detector $\psi/\varphi/\gamma$ | Hoàn thành | $d'$ suy từ $(\psi,\varphi)$; quét $d'$ liên tục → $d'^\* = 2{,}85$ ($\Delta{=}2$), $0{,}95$ ($\Delta{=}4$); detector nội dung đã thử | — |
| 6 | Belief, thư viện policy, $\rho$ | Làm theo hướng khác | Belief trên window tính **chính xác** (thay particle filter); minimax LP (B7, B7U, SSG receding/guarded) thay thư viện 28 policy | 240 game nhỏ giải chính xác; $\rho$ đo đúng không gian |
| 7 | Ví dụ tính tay | Hoàn thành | `trace_one_episode.py` phát lại một episode bằng tay với số thật | — |
| 8 | Đóng băng bằng hash | Một phần | Hash cấu hình; digest cổng v2; payload đóng băng; 10 tài liệu tiền đăng ký | Manifest phủ toàn bộ policy/attacker/hằng số; harness từ chối policy chưa đóng băng |
| 9 | Chạy lưới, tính output | Một phần | Lưới $\Delta \in \{0,1,2,4\}$ × 3 detector trên mock, chấm $L$, $\lambda_Q^\*$, bootstrap theo workflow, bảng chi tiêu | $N = 100$; $\Delta = 8$; trục $\chi$ trong đường chính |
| 10 | Tối ưu, ranh giới tuning | Một phần | LP Stackelberg (Conitzer–Sandholm); ranh giới tuning thực thi qua tiền đăng ký | Double oracle |

**Tóm lại:** 4 stage hoàn thành, 1 làm theo hướng khác, 6 một phần, không stage nào chưa bắt đầu.

---

## 2. Lịch nước rút 14 ngày (bản chốt sau review của thầy)

| Ngày | Việc | Trạng thái | Kết quả |
|---|---|---|---|
| 1 — 18/09 | P2 runner; $\tau_{\text{sel}}$ chạy theo $d'$ | Hoàn thành | $\tau_{\text{sel}}$ theo $d'$ đã tách được confound |
| 2 — 19/09 | Chạy P2 → **điểm rẽ P2** | Hoàn thành | 14 instance, 7 chấm được: **0 B / 0 C / 0 D**, tuân thủ **0/7**. Điều kiện dừng #2 không kích hoạt theo quy tắc, nhưng tiền đề đe doạ không tái tạo được trên agent thật |
| 3–5 — 20–22/09 | Cổng v2 trọn gói; sweep chấm $L$ có B5, B6 | Hoàn thành | Cổng v2 đóng băng 19/09 (qua điều kiện dừng #3); sweep chấm $L$ trên payload v2 xong |
| 4 — 21/09 | **Điểm rẽ L** → A hay A′ | Hoàn thành sớm (18/09) | **Khung A′**: thắng B1 ở 64/64 ô, thua B5 (không có ranh giới $\lambda_Q > 0$) |
| **6 — 23/09** | **Bảng chứng nhận v2 → điểm rẽ v2** | **Tiếp theo** | Ô chứng nhận $\Delta{=}0$: 0,519 và $\Delta{=}2$: 0,529 qua 20/20 split; $\Delta{=}4$ còn đỏ (0,587) |
| 7–9 — 24–26/09 | Chuỗi bảng `m`; lưới $N{=}100$ trên MockAgent; G4 nhãn mù | Chưa đến | Hạn G4: 26/09 |
| 10–11 — 27–28/09 | Evaluation, threats, ablation | Chưa đến | — |
| 12 — 30/09 | **Đóng băng số**; chạy 3 cổng lần cuối | Chưa đến | — |
| 13–14 — 01–02/10 | Bản cuối, format ACM, **nộp** | Chưa đến | AoE = trưa 03/10 giờ Việt Nam |

**Ba điều kiện dừng:** #1 cổng v2 tự vỡ — chưa kích hoạt · #2 P2 âm nặng — không kích hoạt theo quy tắc (xem ngày 2) · #3 v2 chưa đóng băng hết ngày 5 — đã qua.

---

## 3. Trạng thái ước lượng tham số

Chi tiết phương pháp: [Parameter Estimation Report](AuditGame-SE_Parameter_Estimation_Report.md). Bốn phương thức xác lập: **M1** đo trực tiếp · **M2** neo rồi quét · **M3** suy dẫn từ thiết kế thí nghiệm · **M4** khử tham số (phát biểu kết luận dưới dạng ngưỡng).

**7 hoàn thành · 5 một phần · 5 chưa thực hiện.**

| Tham số | Ý nghĩa | Phương thức | Trạng thái | Giá trị / kết quả | Việc còn lại |
|---|---|---|---|---|---|
| $\tau_{\text{sel}}$ | Ngưỡng chọn carrier trên posterior | M1 | ✅ Hoàn thành | Bảng tham chiếu, 800.000 mẫu/ô | Sinh lại khi $\pi_0$ đổi |
| $\mathrm{AUC}_{\text{upper}}$ | Payload có tầm thường phân biệt được không | M1 | ✅ Hoàn thành | 0,5414 (bốn đặc trưng) | Permutation test |
| $\varepsilon^{*}$ | Ngân sách khả phân biệt lớn nhất còn chứng nhận được | M4 | ✅ Hoàn thành | 0; không tồn tại trên nền lành tính trung thực | — |
| $d'^{*}$ | Điểm hoà vốn của detector so với audit-at-commit | M2 + M4 | ✅ Hoàn thành | 2,85 ($\Delta=2$); 0,95 ($\Delta=4$); không tồn tại ở $\Delta \le 1$ | — |
| $d'$ bề mặt | Độ phân tách thực nghiệm của detector bề mặt | M1 | ✅ Hoàn thành | $\le 0{,}50$ | — |
| Chênh lệch ràng buộc | Ngân sách kỳ vọng (LP) so với ràng buộc cứng | M1 | ✅ Hoàn thành | Độ phủ $-13{,}29\%$ | Commit file kết quả |
| $\zeta$ | Sai số kernel, vế phải cận Định lý 3 | M1 | ✅ Hoàn thành | 0,000 (mock); 0,119 khi $\beta = 0{,}5$ | Tách vai thế giới / mô hình để $\zeta$ có tác dụng |
| $\chi$ | Độ dị tính chi phí giữa các carrier | M1 | 🟡 Một phần | 2,114 (bảng bản thảo); 1,349 (bảng đo) | Chốt quy ước chuẩn hoá khi quét |
| $\kappa(k)$ | Chi phí audit mỗi carrier | M1 | 🟡 Một phần | Hai bảng song song; đường chính dùng bảng bản thảo | Đo CPU-phút; chốt một bảng |
| $\Delta$ thực | Độ trễ nhân quả trong workflow thật | M1 | 🟡 Một phần | Trung vị 3, p75 10 ($n = 29$, lịch sử repo đề tài) | Co-change + `git bisect` trên repo SWE-bench |
| $\lambda_Q, \lambda_T$ | Trọng số cách ly nhầm / mất task sạch | M4 | 🟡 Một phần | $\lambda_Q^{*} \approx 0{,}036$–$0{,}05$ | Neo dải hợp lý; ràng buộc nhất quán với $\eta_Q$ |
| $\rho$ | Bán kính phủ của thư viện policy | M1 | 🟡 Một phần | 0,894, đo trong không gian proxy | Đo TV theo từng task, hoặc thu hẹp Mệnh đề 6 |
| $\eta_Q$ | Chi phí cách ly | M1 + M3 | ❌ Chưa thực hiện | Giá trị gán 2,0 | Đo phần gỡ; tính phần phục hồi từ dữ liệu có sẵn |
| $\beta_k$ | Tốc độ trôi lành tính theo carrier | M1 | ❌ Chưa thực hiện | Giá trị gán 0,25 | Luật ánh xạ commit → carrier, đếm commit, độ nhạy |
| $\pi_0, b_0$ | Tiên nghiệm mỗi item, belief khởi đầu | M3 | ❌ Chưa thực hiện | Giá trị gán 0,10 | Thay bằng giá trị suy dẫn $1/12{,}51 = 0{,}080$; sinh lại bảng $\tau_{\text{sel}}$ |
| $c$ | Hằng số của Định lý 4 | M1 | ❌ Chưa thực hiện | — | Tìm $B_{\min}$ từ posterior, hồi quy kiểm tra từng thừa số |
| Quy ước quét $\chi$ | Giữ đại lượng nào cố định khi quét $\chi$ | Thiết kế | ❌ Chưa khai báo | Đề xuất neo $\kappa_{\min}$ | Khai báo trước khi chạy; báo cả ba quy ước |

---

## 4. Các phát hiện đã có (ảnh hưởng tới nội dung bài)

| Phát hiện | Số liệu | Vào bài ở đâu |
|---|---|---|
| Detector bề mặt không đạt hoà vốn | $d' \le 0{,}50$ so với $d'^\* = 2{,}85$ ($\Delta{=}2$) | Kết quả chính (dạng điều kiện) |
| Detector nội dung sụp khi attacker không tự khai báo | AUC 0,479 ($D_{\text{lex}}$) và 0,518 ($D_{\text{llm}}$) khi tên hàm trung tính | Kết quả; đe doạ |
| Agent thật không làm theo payload | 0/7 tuân thủ (P2) | Đe doạ 3 — nặng nhất |
| Sentinel thắng B1 nhờ số hạng $T_{\text{lost}}$ | Dẫn B1 ở 64/64 ô khi $\lambda_T{=}0{,}5$, chỉ 22/64 khi $\lambda_T{=}0$ | Điều kiện của tuyên bố chính |
| $\chi$ không tác động lên nghiệm minimax | Độ lợi 39,7% ở mọi $\chi$ (quy ước neo trung bình) | Cần thầy quyết (mục 2) |
| Ngân sách kỳ vọng lạc quan hơn thực thi | Độ phủ $-13{,}29\%$ | Chú thích mọi bảng độ lợi |
| Không có điểm hoà vốn ở $\Delta \le 1$ | $d'^\*$ không tồn tại | Khớp Hệ quả 5 |

---

## 5. Việc còn lại cho luận văn sau hạn 02/10 (major revision / đề cương)

- Đo các tham số còn thiếu: $\beta$, $\eta_Q$, suy dẫn $\pi_0 = 0{,}080$, hằng số $c$ (chi tiết trong `AuditGame-SE_Parameter_Estimation_Report.md`).
- Nền lành tính thật (item D), $N = 500$, 3 attacker LLM, payload đã công bố (AgentPoison/MINJA).
- Thư viện policy tham số hoá và lớp game nhỏ giải chính xác — điều kiện để kiểm chứng số cho Mệnh đề 6.
- Manifest đóng băng toàn phần có cưỡng chế.

---

## Nguồn

Kế hoạch nước rút: `HCMUT/261-Master-Proposal-Analysis/PLAN-VIEC-CON-LAI.md` (vault) · Khung stage: `docs/AuditGame-SE_PartIV_Detailed.md` · P2: `docs/reports/p2-three-arms.md` · Detector nội dung: `docs/reports/content-detector.md` · $d'^\*$: `docs/preregistration/dprime-sweep.md` · Ước lượng tham số: `docs/AuditGame-SE_Parameter_Estimation_Report.md`.
