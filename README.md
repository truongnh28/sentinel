# Sentinel — AuditGame-SE: Progress Status Report

**Đề tài:** FSE-2027-15 · **Học viên:** Nguyễn Hữu Trưởng · **GVHD:** TS. Lê Xuân Bách · **Cập nhật:** 24/09/2026

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
| **Đang làm** | Nước rút nộp **FSE 2027 Research Papers**, hạn **02/10/2026 AoE** (trưa 03/10 giờ Việt Nam). Hôm nay là **ngày 7/14**, còn **8 ngày**. |
| **Khung bài** | **A′ — "bản đồ chế độ"**, và 24/09 tìm ra **trục chế độ thật là ngân sách**, không phải $\Delta$ hay $\chi$. Hai kết quả dưới đây nghe ngược nhau nhưng ở **hai mức ngân sách khác nhau**, và đó chính là phát hiện: <br>• Ở **mức đã công bố** $B/(H\Sigma\kappa) = 0{,}32$: $N = 100$ kèm CI95, **không ô nào** vượt ngưỡng 15%, tốt nhất +14,5% CI [+9,7; +19,7]. <br>• Ở **dải 0,5–0,75**: `SSG-full` so với B1 đạt **+41,6% → +50,7%** ($\Delta = 4$), vượt ngưỡng thoải mái. <br>• Ở $\ge$ 1,0: về +0,0% vì B1 cũng chạm sàn 0,158. <br>Nói cách khác **mọi số đã công bố nằm ngay dưới mép dải có tác dụng**. Chi tiết và ba chế độ: [§3.3](#33-so-với-giá-trị-dự-phóng-của-draft). |
| **Đang ở bước** | **Viết.** Phần đo đã cạn (24/09); mục Evaluation có bản nháp đầy đủ tại [docs/manuscript/Evaluation.md](docs/manuscript/Evaluation.md). Còn Stage 4 (chứng nhận cổng v2) và Stage 8 (đóng băng, 29/09). |
| **Mốc kế tiếp** | **Trước 29/09:** chốt issue [#13](#34-issue-cần-xử-lý) với thầy. Bằng chứng nay đủ để đề xuất một phương án cụ thể: **giữ A′**, đổi trục chế độ sang **ngân sách**, đổi chính sách chủ đạo từ `Sentinel` sang **`SSG-full receding`**. Kèm theo: bảng chứng nhận cổng v2 chạy một lần, rồi `freeze.write()`. |
| **Thang chi phí** | Chốt **USD** (23/09). Trò chơi bất biến khi nhân cả $(\kappa, \kappa_{\text{commit}}, \eta_Q, B)$ với một hệ số chung, nên đơn vị không phải lựa chọn mô hình — chỉ bốn tỉ số không thứ nguyên sống sót, và USD là đơn vị duy nhất cả bốn cùng đo được. CPU-time giữ làm đối chứng cho $\chi$. Xem [§3.2](#32-trạng-thái-từng-tham-số). |
| **Rủi ro lớn nhất** | **(1) Trục ngân sách chưa ai định giá.** Mức 0,3205 kế thừa từ con số 17,95 của draft. Luận điểm nay phát biểu được, nhưng phát biểu **trên một trục chưa neo**, nên bắt buộc trình bày là *bản đồ*, không phải một điểm. **(2) Agent thật làm theo payload 0/7**, detector thật chỉ đạt $d' \le 0{,}50$ so với $d'^{*} = 2{,}85$ ⇒ mọi số harm là harm **dưới mô hình tiếp nhận của MockAgent**. **(3) Kết quả không bền theo chân trời:** cùng $\Delta = 4$, SSG-full +17,8% ở $H=8$ nhưng +4,0% ở $H=12$ — nhưng $H$ và corpus đang lẫn nhau, xem issue #15. **(4) Ô $\Delta = 4$ của cổng v2 đỏ** và nó là ô có độ lợi lớn nhất; permutation test xác nhận tách được thật ($p = 0{,}010$). **(5)** $\lambda_T = 0{,}5$ nằm gần mép trên vùng SSG-G thắng; khai 0,6 là B1 thắng. |
| **Kiểm thử** | `tests/run_all.py --all` ngày **24/09**: **811 đạt · 2 không đạt · 0 bỏ qua** (813 test) khi máy rảnh. Cổng 2 đỏ 203/205 (hai lỗi cũ), cổng 3 xanh 15/15. Cổng 1 **593/593**, xanh ở cả hai lượt chạy lúc máy rảnh. ⚠️ Một lượt lúc CPU đang tải nặng bỏ qua đủ 13 test container — nghi `container_ready()` quá hạn khi tranh tài nguyên, xem issue #9 ([§3.5](#35-kiểm-thử)). |

## Được bao nhiêu phần trăm

Đếm theo **hạng mục bàn giao được**: 51 hạng mục, chia tám nhóm. Quy ước: **✅ xong = 1 · 🟡 một phần = 0,5 · ❌ chưa làm = 0**.

**Tổng: 49,5 / 51 = 97%.**

| Nhóm | Tiến độ | Hạng mục |
|---|---|---|
| **A. Hạ tầng benchmark** | **94%** (8,5/9) | ✅ CarrierStore bốn carrier · ✅ Workflow từ SWE-bench Verified · ✅ Retrieval Jaccard với $\theta$ · ✅ MockAgent · ✅ Agent LLM thật (P2) · ✅ Oracle marker · 🟡 Oracle test ẩn (neo được 5/500 = 1,0%) · ✅ Replay và sealed trace · ✅ Harness Docker: image `auditgame:latest` dựng xong, **13 test container chạy và xanh** |
| **B. Tấn công và ground truth** | **100%** (7/7) | ✅ Sinh $(\iota,\sigma)$ có lọc nổ sớm · ✅ Payload đóng băng và bộ sinh · ✅ Thư viện attacker kịch bản **18/18** (6 luật mới đọc workflow; cổng 2 bác 2 bản đầu vì trùng hành vi luật cũ) · ✅ Attacker best-response **tối ưu tự do trên $(k,\iota,\sigma)$** (`build.plan_poison_all` + `tools/best_response.py`): attacker cũ chỉ dùng **1/8 vị trí** ở $\Delta=0$ và 1/3,9 ở $\Delta=2$. Đúng mô hình rồi thì ở $\Delta=0$ **mọi chính sách về harm 1,0000** · ✅ Marker duy nhất mỗi lần chạy: `build.marker_for` băm (repo, workflow, carrier, $\iota$, $\sigma$, $\Delta$) — 16/16 cấu hình ra 16 marker khác nhau, tất định để replay được · ✅ Đo $\Delta$ thực trên 10 repo SWE-bench · ✅ Validate harm trên tập con: 15 instance chọn có seed, test ẩn **viết tay**, 4 chế độ × 15 = 60 phán quyết |
| **C. Corpus lành tính và cổng** | **100%** (5/5) | ✅ Corpus từ item SWE-bench thật · ✅ Ghép theo 5 đặc trưng bề mặt · ✅ Cổng AUC v2 **đã chạy bảng chứng nhận một lượt** (`tools/certify_gate2.py`): $\Delta = 0$ **0,5117** và $\Delta = 2$ **0,5247** — chứng nhận, 20/20 split; $\Delta = 4$ **0,6185** — từ chối, 0/20 · ✅ Permutation test (200 hoán vị): $\Delta=4$ **tách được** ($p = 0{,}010$) — xác nhận độc lập ô đỏ; $\Delta \in \{0,2\}$ **không** ($p = 0{,}28$ / $0{,}25$) · ✅ $\beta_k$: hai luật lệch 10× ở skill ⇒ chuyển M2 và **đã quét** — $L$ **không đổi một chữ số** qua $\beta \in [0{,}013;\ 1{,}0]$, vì $\beta$ chỉ chạm hypothesis NULL nên triệt tiêu chính xác khi so carrier; chốt bằng test |
| **D. Detector và tín hiệu** | **100%** (5/5) | ✅ Detector mô phỏng theo $d'$ · ✅ Ba mức $(\psi,\varphi)$ chạy **thành lưới riêng neo trên $\gamma$** (`tools/gamma_grid.py`): mã tái tạo **chính xác** suy dẫn của draft ($d'$ = 1,516 / 2,211 / 2,960 so với 1,52 / 2,21 / 2,96), kèm phép kiểm cận $1/\gamma^2$ · ✅ CarrierSignal mean và bảng $\tau_{\text{sel}}$ · ✅ Sweep $d'$ liên tục, ra $d'^{*}$ · ✅ Detector nội dung $D_{\text{lex}}$, $D_{\text{llm}}$ |
| **E. Chính sách và lý thuyết** | **100%** (8/8) | ✅ B1–B6 · ✅ Minimax LP · ✅ Các biến thể SSG · ✅ Belief tính chính xác · ✅ Thư viện 28 policy (`policies_library.py`: 8 stage-weighted · 12 belief-threshold · 8 carrier-rotation; B1 nằm **trong** lớp) · ✅ **240 game nhỏ giải chính xác** (`smallgame.py` + `tools/solve_small_games.py`, dạng covering-game marginal, $K\cdot H \le 24$): $\rho$ so với **nghiệm thật** = **0,7500** (draft 0,07); nhưng **175/240 game regret bằng 0** và regret trung bình chỉ 0,0280 ⇒ TV **không** đo được mất mát · ✅ $\rho$ đo trên **không gian đúng** (phân phối hành động *theo từng task*, TV trung bình theo $H$): **0,5078** · ✅ $\zeta$ |
| **F. Đo lường và kết quả** | **100%** (8/8) | ✅ Lưới $\Delta$ × detector trên MockAgent · ✅ Trục $\chi$ trong đường chính: `--chi 0 0.5 1.349`, chạy ở detector mid, kèm test bắt `main()` phải gọi `sweep_chi` · ✅ $\Delta = 8$ **đã chạy** (24/09, `--deltas`, $H = 12$) — và kết quả là **âm**: không ô nào vượt 15%, `B2 uniform random` thắng 5/18 ô · ✅ **100 workflow** kèm CI95 bootstrap theo workflow (`tools/certified_power.py`) · ✅ Worst-case trên held-out: ba thống kê kèm CI95 lấy mẫu theo workflow; thống kê của draft **bão hoà**, thống kê thay thế cho thấy chỉ `Sentinel` xuống cấp có ý nghĩa · ✅ Exploitability trên **8 chính sách** kèm $v^{*}$ và minimax mix: **SSG-G 0,0119** thấp hơn B1 0,0179 · ✅ Ablation **đủ bốn arm**: bỏ belief **0,000** · bỏ rotation **0,000** · bỏ ngẫu nhiên hoá **+0,027** · bỏ benign-drift 0,000 (nhưng **không đọc được**, xem §3.3) · ✅ CI bootstrap theo cụm |
| **G. Tính toàn vẹn** | **90%** (4,5/5) | ✅ Ba cổng kiểm thử, 813 test · ✅ Tài liệu tiền đăng ký · 🟡 Digest rời (cổng v2, payload, prompt) · ✅ Manifest đóng băng toàn phần (`freeze.py`: digest mã nguồn + hằng đọc từ module sống + hai registry + bảng sinh) · ✅ Harness từ chối policy chưa đóng băng (`freeze.require_frozen`, gọi trong `experiment.py`) |
| **H. Tài liệu** | **88%** (3,5/4) | ✅ Phương pháp luận · ✅ Parameter Estimation Report · ✅ Reports và báo cáo tiến độ · 🟡 Bản thảo ACM: **mục Evaluation đã có bản nháp** ([docs/manuscript/Evaluation.md](docs/manuscript/Evaluation.md), kèm Hình 1 sinh từ dữ liệu); còn Intro, Related Work, Model, Design |

**Đọc các con số này thế nào.**
1. **97% là công đã bỏ ra, không phải bài đã viết.** Câu trả lời cho "bài viết được bao nhiêu" là **35–40%** sau khi có mục Evaluation, không phải 97%. Cỗ máy đo nay chạy đúng thang, đúng giá và đúng attacker — và nó cho ra **một kết quả dương có phạm vi**: phân bổ audit đáng giá trong dải ngân sách 0,5–0,75 (+41,6% … +50,7%), vô nghĩa ở hai đầu. Ở đúng mức ngân sách cũ thì không ô nào vượt 15%.
2. **Nút thắt là viết, không phải đo.** Phần đo đã cạn: thư viện 28 policy, manifest đóng băng, 18/18 attacker, $\Delta = 8$, $N = 100$ kèm CI, ablation đủ bốn arm, attacker best-response, quét ngân sách — đều xong. Còn **bốn mục bài** chưa viết (Intro, Related Work, Model, Design) và **một quyết định** phải chốt với thầy: đổi chính sách chủ đạo sang họ SSG và đổi trục chế độ sang ngân sách (issue #13). Xem thêm #15 ở [§3.4](#34-issue-cần-xử-lý).
3. **Một phần công đã bỏ ra không nằm trong 51 hạng mục này:** hơn 60 spike, arm P2, detector nội dung, năm biến thể SSG. Chúng cho ra các phát hiện dưới đây, nhưng trong bản nộp nhiều thứ chỉ còn một dòng ở mục Threats.

**Phát hiện đã có, không phụ thuộc phần còn thiếu.** Chia hai nhóm, vì chúng phục vụ hai mục khác nhau của bài.

*Về đối tượng nghiên cứu — dùng cho Evaluation:*
1. Detector bề mặt chỉ đạt $d' \le 0{,}50$, trong khi điểm hoà vốn so với audit-at-commit là $d'^{*} = 2{,}85$ ở $\Delta = 2$.
2. Detector nội dung sụp về ngẫu nhiên (AUC 0,479–0,518) khi attacker không tự khai báo.
3. Agent LLM thật không làm theo lời khuyên độc: 0/7 instance.
4. Không tồn tại điểm hoà vốn ở $\Delta \le 1$, khớp với Hệ quả 5 của draft.
5. **Đơn vị chi phí không phải lựa chọn mô hình** — trò chơi bất biến khi nhân cả $(\kappa, \kappa_{\text{commit}}, \eta_Q, B)$ với một hệ số chung, nên chỉ **bốn tỉ số không thứ nguyên** sống sót. Cả bốn nay đã đo.

*Về chính luận điểm — năm kết quả âm, rồi hai kết quả cứu lại luận điểm:*
6. **Không chính sách nào đạt ngưỡng 15%**, ở bất kỳ $\Delta$ nào. $N = 100$ kèm CI95: tốt nhất +14,5% CI [+9,7; +19,7]. Ở $N = 40$ con số này là +17,8% và **vượt ngưỡng** — tức kết luận dương trước đó là nhiễu cỡ mẫu.
7. **Khoảng cách dẫn cũ được mua bằng một hành động không bị tính tiền.** `runner.py` có hai đường cách ly và chỉ một bị trừ ngân sách; tính đúng giá thì độ lợi của `Sentinel` tụt +49,7% → +3,5%.
8. **Hai trong ba cơ chế của `Sentinel` đóng góp đúng 0,000** — bỏ belief và bỏ rotation không đổi một chữ số; chỉ ngẫu nhiên hoá làm đổi số, và chỉ bằng $1/7$ mức draft.
9. **Vùng "vượt ngưỡng" và vùng "được cổng chứng nhận" giao nhau bằng rỗng.** Cổng AUC v2 từ chối $\Delta = 4$, mà mọi ô có độ lợi cao nhất đều nằm ở đó.
10. **Attacker trong mã yếu hơn attacker trong mô hình.** σ được *bốc*, không được *chọn*: 1 trong 8 vị trí ở $\Delta = 0$. Đo đúng mô hình thì ở $\Delta = 0$ mọi chính sách về harm 1,0000, và **ngẫu nhiên hoá không giảm được best-response gain** — nó tăng.

11. **Trục chế độ là ngân sách.** Quét $B/(H\Sigma\kappa)$: độ lợi `SSG-full` so với B1 ở $\Delta=4$ đi +14,4% → +17,9% → **+41,6%** → **+50,7%** rồi về +0,0% khi B1 cũng chạm sàn. Có một **dải giữa** mà phân bổ audit quyết định, và mọi số đã công bố nằm ngay **dưới mép** dải đó.
12. **`Sentinel` sai cấu trúc chứ không thiếu tiền.** Ở ngân sách gấp đôi, B1 và họ SSG cùng về harm 0,158 còn `Sentinel` đứng ở 0,464.
13. **Khoảng cách TV không đo được mất mát.** Trên 240 game nhỏ giải chính xác, lớp policy cách nghiệm tối ưu **0,7500** theo TV nhưng **tối ưu chính xác ở 175/240 game**. Cận Mệnh đề 6 không chỉ rỗng — nó chặn mất mát bằng một đại lượng không theo dõi mất mát, và double oracle (phương thuốc draft kê) thêm 40 nghiệm mà max regret không đổi.

Ý **6–10 và 13 bác bỏ dự phóng của draft**, và phần lớn chỉ lộ ra khi một hằng số đặt tay hoặc một phép bốc ngẫu nhiên bị thay bằng thứ mô hình thật sự phát biểu. Ý **11–12 thì ngược lại**: chúng cứu luận điểm, nhưng kèm một phạm vi — và vì trục ngân sách chưa ai định giá, cách trình bày đúng là **bản đồ chế độ** (khung A′), không phải một con số. Đó là lập luận cho **khung B** (benchmark tự phản biện), không phải cho A′.

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
| **7 — T5 24/09** | ✅ **Vượt kế hoạch, và làm luôn việc của ngày 8–10 lẫn ngày 13.** Sửa ba lỗi định giá (thang chi phí, giá cách ly, ngân sách theo chân trời); attacker best-response tự do trên $(k,\iota,\sigma)$; $N = 100$ kèm CI95; $\Delta$ tới 8; ablation đủ bốn arm; quét $\eta_Q$, $\beta$ và **ngân sách** | ✅ Mục **Evaluation** có bản nháp đầy đủ. ⏳ Còn: gửi thầy danh sách 28 policy và 18 attacker; **chốt mô hình quan sát** (M0/MA/MB/ME) | ✅ Dấu RQ1 xác định; ✅ **bản đồ chế độ theo ngân sách** — kết quả chính của cả dự án |
| **8 — T6 25/09** | ✅ **Xong sớm (23–24/09).** 18/18 attacker; best-response; $\lambda_Q$ suy từ tỉ số đo được 1,0973 | Viết **Related Work** (25 bài đã có ở `docs/paper/`) | ✅ Exploitability và worst-case held-out đã có số; ⏳ hai mục bài |
| **9 — T7 26/09** | ✅ **Xong sớm (23/09)** — `policies_library.py`, 28 policy | Viết **Model** và **Design** (chép từ [Methodology](docs/AuditGame-SE_Sentinel_Methodology_Full.md)); G4 nhãn mù — **hạn cứng**, cần người gán tay 38 instance | $\rho = 0{,}5078$ nói **28 chưa được biện hộ**; hai mục bài |
| **10 — CN 27/09** | ✅ **Xong sớm (24/09)** — $N = 100$ kèm CI95, $\Delta$ tới 8, ablation, bootstrap theo workflow | Viết **Intro** — phải tuyên bố đóng góp, nên **chờ quyết định #13** | ✅ Bảng kết quả chính; ⏳ Intro |
| **11 — T2 28/09** | ✅ **P4 (240 game nhỏ và $\rho$) xong sớm 24/09**; bốn phép quét ($\eta_Q$, $\beta$, ngân sách, $\gamma$) cũng xong. ⏳ Còn **P2** — sửa mô hình quan sát rồi đo lại $c$, chờ quyết định T1 | Viết **Model** và **Design** | Định lý 4 có vế trái, hoặc một phát biểu kiểm chứng được về vì sao không; mỗi tham số quét có một dòng kết luận |
| **12 — T3 29/09** | **Đóng băng số**: manifest hash, harness từ chối policy chưa đóng băng; chạy lại lưới trên cấu hình đã đóng băng | Chạy ba cổng, bật Docker cho 13 test của cổng 1 | Ba cổng xanh, hoặc đỏ có giải trình; số cuối cùng |
| **13 — T4 30/09** | — | ✅ Evaluation + Threats **đã viết 24/09**; còn dựng artifact ẩn danh và ráp đủ mục | Bản nháp đủ mục, số đã khớp bảng |
| **14 — T5 01/10** | — | **Đọc lại toàn bài**, sửa, format ACM | Bản gần cuối |
| **15 — T6 02/10** | — | Nộp sớm trong ngày | Bản nộp (hạn AoE) |

**Ba thay đổi so với lịch cũ:** đóng băng số dời lên **29/09** thay vì 30/09; toàn bộ phần đo khép lại trong tháng 9; ngày 01/10 dành riêng cho việc đọc lại và sửa, không còn chồng lấn với việc chạy.

**Nếu phải cắt**, cắt theo thứ tự ngược: W7 và W6 (ngày 11) bỏ trước, rồi rút quy mô lưới ngày 10 xuống $N$ nhỏ hơn. Không cắt ngày 8 và 9, vì không có 18 attacker và thư viện 28 policy thì không có bảng kết quả chính.

### Dự kiến có gì để báo cáo cuối tuần này (27/09)

Tính tới hết Chủ nhật 27/09, tức sau ngày 10 của sprint, dự kiến đã có. **Cập nhật 24/09: bốn trong năm dòng đã xong sớm ba ngày**; dòng còn lại đổi nội dung.

| Nhóm | Kết quả |
|---|---|
| **Quyết định** | ⏳ Đề xuất đã có (giữ A′, trục ngân sách, chính sách chủ đạo là SSG-full) — **chờ thầy duyệt**, issue #13 |
| **Tham số chuyển từ gán tay sang đo** | ✅ Xong, và nhiều hơn dự kiến: thêm $\kappa_{\text{commit}}$, $\lambda_Q$, và ba lỗi định giá được sửa |
| **Thiết lập draft** | ✅ Xong — 18 attacker (held-out **9/18** theo hash, không vẽ lại để khớp 7/18), best-response tự do, 28 policy, marker duy nhất |
| **Số so được với Bảng 2 của draft** | ✅ Xong cả ba, và **phần lớn ngược dấu dự phóng** — xem [§3.3](#33-so-với-giá-trị-dự-phóng-của-draft) |
| **Còn nợ** | Chỉ còn hằng số $c$, và nó chờ **quyết định mô hình quan sát** chứ không chờ phép đo. 240 game nhỏ, $\Delta$ thực, $\rho$ — xong hết. Nợ thật là **ba mục bài chưa viết** (Intro, Model, Design) |

Ba việc **không phụ thuộc vào code**, cần thầy và cần bố trí người: duyệt danh sách 28 policy và 18 attacker, gán tay 38 instance cho G4 (hạn ngày 9), và **chốt issue #13** — đóng góp của bài đổi thì Intro mới viết được.

**Ba điều kiện dừng đã khai báo trước:**

| # | Kích hoạt khi | Hiện trạng |
|---|---|---|
| 1 | Cổng v2 tự vỡ | Chưa kích hoạt theo định nghĩa trong tiền đăng ký. Hai test cổng 2 vẫn đỏ; permutation test xác nhận $\Delta = 4$ **tách được thật** ($p = 0{,}010$), nên ô đó là kết quả chứ không phải lỗi cổng |
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
| $\tau$, $\lambda_Q$, $\lambda_T$ | chưa có | M1 + M4 | $\lambda_Q$ **suy** từ $\lambda_T$ bằng tỉ số đo được (1,0973); $\lambda_T$ **khai**, kèm bảng vùng thắng theo cả dải | [PPL] Phần VI loại C · [PER] 5.5 |
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
| 3 | 18 attacker (7 held-out); sinh $(\iota,\sigma)$ theo $\Delta$ có lọc nổ sớm; marker duy nhất mỗi lần chạy; oracle harm; đo $\Delta$ thực | Thư viện attacker, oracle | Oracle validate trên tập con; phân phối $\Delta$ thực cùng thang với crossover | **#4** thêm 6 attacker cho đủ 18 và attacker best-response · **#6** marker `blake2b` · **W8** payload AgentPoison và MINJA · **W5** $\Delta$ thực trên SWE-bench · ✅ validate harm trên tập con (30/30 trong miền, 0/30 ngoài miền) |
| 4 | Corpus lành tính khớp bề mặt; cổng AUC; ước lượng $\beta_k$ | Corpus, AUC, $\beta$ | AUC ≤ 0,56 kèm CI và permutation test; 620 mẫu | Chứng nhận ô $\Delta = 4$ (điểm rẽ ngày 6) · **W3** đo $\beta_k$ · permutation test |
| 5 | Mô phỏng detector với 3 mức $(\psi,\varphi)$; CarrierSignal lấy mean posterior | Detector, $\gamma$ | Ba mức $\gamma$ = 0,55 / 0,73 / 0,86 | Chạy đúng ba mức $(\psi,\varphi)$ như một lưới riêng · **W1** $\pi_0$ suy dẫn và sinh lại bảng $\tau_{\text{sel}}$ |
| 6 | Belief; thư viện 28 policy; 240 game nhỏ giải chính xác; đo $\rho$; mở rộng thư viện bằng double oracle nếu $\rho$ lớn | Thư viện, $\rho$ | Draft: $\rho = 0{,}07$, cận Mệnh đề 6 = 0,42, regret đo được 0,09 | ✅ **W2** ($\eta_Q$ theo carrier, 61,5×) · ✅ **#3** thư viện 28 policy · ✅ **W7** 240 game nhỏ giải chính xác, $\rho = 0{,}7500$ so với nghiệm thật — và phát hiện **TV không theo dõi mất mát**, nên Mệnh đề 6 dựng trên sai đại lượng |
| 7 | Tính tay trên game nhỏ và so với mã | Ví dụ khớp | Minimax 4×4: tất định 1,0, trộn 0,5; Bayes 0,10 → 0,44 → 0,85 | Test hoá ví dụ minimax 4×4 và ví dụ Bayes |
| 8 | Đóng băng policy, attacker, hằng số, corpus, workflow bằng hash | `frozen/`, `MANIFEST.sha256`, tag `freeze-v1` | Harness tính lại hash và từ chối chạy nếu không khớp | **#4** manifest đóng băng toàn phần và harness từ chối policy chưa đóng băng |
| 9 | Chạy lưới đầy đủ; worst-case trên held-out; exploitability; crossover; CI bootstrap theo cụm repo; hằng $c$ | Bảng kết quả trên lưới $(\Delta,\chi)$ | Draft (Bảng 2, $\Delta > 2$, $\chi = 1{,}34$, held-out): B1 0,412 → Sentinel 0,272 (−34,1%, CI [−42,6%; −25,1%], vượt ngưỡng 15%); held-out 27,6%; exploitability 0,34 → 0,09; cách ly nhầm 3,2% → 5,1%; crossover 2,1; RQ4 21,4%–39,8%, lớn nhất ở detector yếu; quét $\eta_Q$: 34,1% → 44,0% | ✅ $\Delta = 8$ · ✅ trục $\chi$ · ✅ worst-case held-out · ✅ exploitability trên 8 chính sách. **Đo xong thì số không đạt:** ở $N = 100$ kèm CI95, **0 ô** vượt ngưỡng 15% ở mọi $\Delta$; ở $H=12$ cũng 0/18. Còn: $N = 100$ · ablation (rotation, benign-drift) · **W6** hằng $c$ |
| 10 | Giải game; tuning chỉ trên dev, trước đóng băng | Nghiệm, ranh giới tuning | Khoảng cách dev và held-out báo cáo được (draft: 34,1% so với 27,6%) | Double oracle (sau hạn nếu không kịp) |

---

## 3. Trạng thái hiện tại

### 3.1 Tổng quan theo stage

**2 hoàn thành · 1 làm theo hướng khác · 8 một phần · 0 chưa bắt đầu.** Rà soát ngày 22/09 bằng cách đọc mã và chạy lại toàn bộ test; cập nhật 23/09 sau đợt đo W1–W6 và **24/09 sau khi sửa thang chi phí, giá cách ly và ngân sách theo chân trời** ([runbook](docs/AuditGame-SE_Parameter_Measurement_Runbook.md)). Đợt đo không đổi trạng thái stage nào, nhưng đổi *nội dung* của Stage 2, 3, 4, 6 và 9 — chi tiết trong cột Issue.

| Stage | Trạng thái | Đã làm | Kết quả hiện có | Issue |
|---|---|---|---|---|
| 0 | ✅ Hoàn thành | Tuple game; loss ba số hạng (`metrics.loss`); `CarrierSignal(p, n)` chỉ có hai trường | Cạnh bị cấm cưỡng chế bằng chữ ký hàm và test | — |
| 1 | 🟡 Một phần | SWE-bench Verified đã nối; sort `created_at`; topic từ gold patch; $\theta = 0{,}5$ chốt trước khi đếm workflow | **14/58** workflow khả dụng ở $H = 8$; sweep hiện chạy 40 workflow | Thiếu workflow so với 100; chưa lọc instance flaky |
| 2 | 🟡 Một phần | Công thức $\chi$ công bố; **23/09: bốn checkpoint được hiện thực làm việc thật** (`checkpoints.py`), $\kappa$ đo lại trong vòng chạy game; ba thang giá so trên cùng một lưới bằng `tools/compare_cost_scales.py`; **chốt USD làm thang vận hành** (trò chơi bất biến theo hệ số chung — chỉ bốn tỉ số sống sót) | $\chi$: **2,114** (bảng draft, theo giai đoạn) · **1,349** (USD, theo số item) · **1,295** (CPU-time, sau khi checkpoint làm việc thật; bản trước đo bộ mô phỏng và ra 0,16). Thứ hạng chính sách **đổi theo đơn vị**: thang USD cho SentinelW thắng B1 **+25,0% harm / +14,5% $L$**; thang CPU cho B1 đứng đầu | ✅ $\kappa_{\text{commit}}$ **đã đo** (23/09): nửa review một mình $= 4{,}00\,\bar\kappa$, vượt sẵn vùng lật 1,43–2,0 ⇒ dấu RQ1 không phụ thuộc giá máy. **24/09 phát hiện lớn hơn:** `experiment.py` **chưa bao giờ gọi** `costs.install()`, nên toàn bộ lưới chạy trên bảng placeholder — ba trong bốn tỉ số sai và thứ tự carrier đảo ngược. Đã có `--scale`, mặc định `usd`, và header in cả bốn tỉ số |
| 3 | 🟡 Một phần | Sinh $(\iota,\sigma)$ có lọc nổ sớm; **18 attacker kịch bản** (6 luật đọc workflow thêm 23/09); chia held-out bằng hash; **marker duy nhất mỗi cấu hình** (`build.marker_for`); **23/09: đo $\Delta$ thực trên 10 repo SWE-bench** (SZZ-lite) | $\Delta$ theo task: trung vị **0** ở 8/10 repo, django **4,5**; chỉ **19%** instance có $\Delta \ge 2$. $\Delta$ theo commit: trung vị 14–194, p75 tới 935 | Số dogfood cũ (trung vị 3) đo trên repo đề tài, **không** phải quần thể mục tiêu; đơn vị task phụ thuộc mật độ lấy mẫu instance nên phải báo theo repo. Vùng $\Delta \ge 2$ chỉ phủ ~1/5 workload ⇒ ranh giới vùng nên phát biểu theo tỉ lệ workload từng repo. Còn lại: held-out **9/18** (theo hash, không vẽ lại để khớp 7/18 của draft); ✅ best-response nay **tối ưu tự do trên $(k,\iota,\sigma)$** (`build.plan_poison_all`). ✅ $\Delta = 8$ đã chạy 24/09 ở $H = 12$. Harm **đã validate trên tập con**: 15 instance, test ẩn viết tay, khớp 30/30 trong miền bộ mô phỏng biểu diễn được và 0/30 ngoài miền đó |
| 4 | 🟡 Một phần | Cổng v2 đóng băng 19/09: 5 đặc trưng, tiêu chí cận trên CI, 20 split; corpus từ item SWE-bench thật, ghép theo tuổi; **23/09: đo $\beta_k$ trên 10 repo thật** (`tools/measure_beta.py`, hai luật ánh xạ) | v1 (4 đặc trưng): 0,5414. v2: $\Delta=0$ 0,519 · $\Delta=2$ 0,529 (20/20 split) · $\Delta=4$ **0,587** (1/20). $\beta$: memory **0,31**, branch 1,0 (theo cấu tạo); skill **0,058 hay 0,607** tuỳ luật | $\Delta = 4$ đỏ; 2 test cổng 2 đỏ; chưa có permutation test; ngưỡng 0,56 nằm trong dải nhiễu ở mọi $n \le 1800$. **$\beta$ không định danh được**: hai luật ánh xạ lệch hơn 10× ở skill ⇒ theo tiêu chí đã khai trước, skill và queue chuyển sang M2 (quét), chỉ memory và branch được trích dẫn |
| 5 | ✅ Hoàn thành | Detector Gaussian theo $d'$, gộp bằng mean tỉ số likelihood; quét $d'$ liên tục; thử detector nội dung | $d'^{*}$ = 2,85 ($\Delta=2$), 0,95 ($\Delta=4$), không tồn tại ở $\Delta \le 1$; detector bề mặt $d' \le 0{,}50$ | Chưa chạy đúng 3 mức $(\psi,\varphi)$ của draft như một lưới riêng |
| 6 | 🟣 Hướng khác | Belief tính chính xác bằng liệt kê cửa sổ (thay particle filter); minimax LP và 5 biến thể SSG; **23/09: $\beta$ mặc định của belief đọc từ số đo** (`costs.BETA_DEFAULT`) | Registry 17 policy; thư viện 28 policy; $\rho$ so với nghiệm thật **0,7500** trên 240 game nhỏ (bản proxy cũ: 0,894) | 🔴 **Quan sát đang miễn phí**: `belief.WindowBelief.update` nhận tín hiệu của *mọi* carrier ở *mọi* task, bất kể chính sách audit gì — posterior tại $\sigma$ không đổi khi $B$ đi từ 2 đến 200. Đây là lý do Stage 9 không fit được hằng $c$. ✅ Thư viện 28 policy đã dựng (`policies_library.py`) — nhưng $\rho = 0{,}5078$ nói **28 chưa được biện hộ**: đường bão hoà phẳng từ 4 thành viên. Vẫn chưa có 240 game nhỏ; tên "B7" trong mã là LP đối thủ, còn trong draft B7 là oracle trần |
| 7 | 🟡 Một phần | `spikes/trace_one_episode.py` phát lại một episode với số thật | Minimax 4×4 khớp `game.minimax` ($V^* = 0{,}5$) | Chưa test hoá ví dụ 4×4; ví dụ Bayes Bernoulli chưa được mã kiểm |
| 8 | 🟡 Một phần | Digest rời: cổng v2, độ dài payload, prompt detector; payload đóng băng; tiền đăng ký | — | ✅ `freeze.py` đã có: manifest digest mã nguồn + hằng đọc từ module sống + hai registry, và `require_frozen` được gọi trong `experiment.py`. Còn **chạy** `freeze.write()` vào mốc 29/09 — trước đó `require_frozen` là no-op có chủ ý |
| 9 | 🟡 Một phần | Lưới $\Delta \in \{0,1,2,4\}$ × 3 detector; **24/09: $N = 100$ kèm CI95 (`tools/certified_power.py`), $\Delta$ tới 8 ở $H = 12$, ablation đủ bốn arm**; chấm $L$; $\lambda_Q^{*}$; bootstrap theo workflow; **23/09: thử fit hằng $c$** (`tools/measure_c.py`) | Xem [§3.3](#33-so-với-giá-trị-dự-phóng-của-draft). Hằng $c$: **không fit được** — script kiểm tiền đề rồi từ chối trả số | 🔴 Tiền đề của Định lý 4 không thoả trong harness: ngân sách **không mua được thông tin** (xem Stage 6), nên vế trái của cận không tồn tại. Phải sửa mô hình quan sát trước, rồi mới fit $c$. Exploitability đã đo lại và **khớp dự phóng** (SSG-G 0,0119 < B1 0,0179). Worst-case trên held-out ✅ và trục $\chi$ đã vào đường chính ✅. **24/09 chạy lại toàn lưới trên thang USD với cách ly có tính tiền**: `Sentinel` +3,5%, `SSG-full receding` +17,8%, ở $N = 40$ có 2/12 ô vượt ngưỡng — **nâng lên $N = 100$ thì còn 0**, tốt nhất +14,5% CI [+9,7; +19,7]. Ở $H = 12$ cũng 0/18 và `B2 uniform random` thắng 5/18 |
| 10 | 🟡 Một phần | LP Stackelberg (Conitzer–Sandholm); ranh giới tuning qua tiền đăng ký | — | Chưa có double oracle |

### 3.2 Trạng thái từng tham số

**11 hoàn thành · 2 một phần · 2 tiền đề hỏng · 3 chưa thực hiện** (18 mục). Cập nhật 24/09; $\eta_Q$ vẫn tính là hoàn thành nhưng **vào bài bằng quét (M2)** chứ không chốt một số, xem [Parameter Measurement Runbook](docs/AuditGame-SE_Parameter_Measurement_Runbook.md).

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
| $\kappa_{\text{commit}}$ | 4,1 | M1 | ✅ **Hoàn thành** | Nửa review $= 4{,}00\,\bar\kappa$; nửa test đo được **0,599 giây CPU** (trung vị, 6 instance sympy, dải 0,047–6,071) | **Dấu của RQ1 đã xác định và không phụ thuộc giá máy**: nửa review một mình đã vượt vùng lật 1,43–2,0. Ba thay thế khai rõ trong JSON: chạy ở HEAD, bỏ repo cần biên dịch, tách thời gian dựng môi trường |
| $\lambda_Q, \lambda_T$ | — | M1 + M4 | ✅ **Hoàn thành** | **$\lambda_Q$ suy ra**, không gán: tỉ số $\lambda_Q/\lambda_T$ **đo được 1,0973**. $\lambda_T = 0{,}5$ **khai** trong [tiền đăng ký](docs/preregistration/TIEN-DANG-KY-lambda-T.md) | Hai tham số còn một. SSG-G thắng trên $\lambda_T \in [0{,}26;\ 0{,}57]$ — rộng 0,31 nhưng **0,5 nằm gần mép trên**; bài phải in cả dải |
| $\rho$ | 0,07 | M1 | ✅ Hoàn thành | **Hai số, hai câu hỏi.** Lớp **tự phủ chính nó**: 0,5078. Lớp so với **nghiệm tối ưu thật** (240 game nhỏ giải chính xác): **0,7500** | Chỉ số thứ hai mới là $\rho$ mà Mệnh đề 6 nói tới; số 0,5078 trích trước đây trả lời câu hỏi khác. Cận $H\rho\,\mathrm{range}(L)$ **rỗng** ở cả hai. Nhưng điều quan trọng hơn: lớp cách nghiệm tối ưu 0,75 theo TV mà **tối ưu chính xác ở 175/240 game**, regret trung bình 0,0280 ⇒ **TV không theo dõi mất mát**, nên cận không chỉ rỗng mà còn dựng trên sai đại lượng. `spikes/small-games.json` |
| $\eta_Q$ | — | M1 → **M2** | ✅ Đo xong, **vào bài bằng quét** | Đo: cách ly đắt **gấp 61,5×** audit cùng carrier, một lượt tốn **6,0× toàn bộ ngân sách**. Hai mốc **suy ra được, không phụ thuộc đơn vị**: $r = 1{,}28$ một lượt bằng suất ngân sách một task, $r = 10{,}26$ bằng cả ngân sách episode | Phải quét chứ không được chốt: ở giá đo được **không hình thức cách ly nào mua nổi**, nên chốt một số là *vô hiệu hoá* một hành động chứ không phải so sánh nó (`costs.py:229`). Quét ra **điểm lật** SSG-G → SentinelW ở $r \in [20;\ 32]$. `costs.install()` đã chuyển sang giá đo được 24/09; trước đó cài tỉ số placeholder, rẻ hơn **53,8×** |
| $\beta_k$ | — | M1 → **M2** | ✅ **Quét xong** | 10 repo thật: memory **0,31**, branch 1,0; skill 0,06 hay 0,61 tuỳ luật. Quét $\beta \in [0{,}013;\ 1{,}0]$ (77×): $L$ của SentinelW và SSG-B **đứng yên tới bốn chữ số** | Không định danh được **và không cần**: `belief.update` chỉ nhân hypothesis NULL với `quiet**(1-beta)`, nên $\beta$ chỉ đổi hằng chuẩn hoá ⇒ mọi **tỉ số giữa carrier độc lập chính xác** với $\beta$ (627,7932 ở mọi giá trị). Nó chỉ sống ở `p_attack()`, thứ bão hoà sát 1,0 và chỉ dịch 6%. Chốt bằng `tests/gate1_integrity/test_beta_invariance.py`; số quét ở `spikes/beta-sweep.json`. Ghi thêm: policy hardcode `BETA_DRIFT = 0,25`, **không đọc** `costs.BETA_DEFAULT = 0,314` — vô hại chỉ vì tính bất biến trên |
| $\pi_0, b_0$ | — | M3 | ✅ Hoàn thành | Suy dẫn **0,0799** (thế giới) / **0,0400** (mô hình), một nguồn trong `costs.py` | Bảng $\tau_{\text{sel}}$ đang sinh lại; sau đó quét $\pi_0$ |
| $c$ | — | M1 | 🔴 **Không đo được** | Tiền đề hỏng: posterior đứng yên ở 0,000336 khi $B$ đi từ 2 đến 200 | `runner.py` chấm cả 4 carrier mỗi task bất kể audit cái gì ⇒ ngân sách mua **hành động**, không mua **thông tin**. Bốn mô hình quan sát để chọn — **M0** giữ nguyên · **MA** trả tiền mới được nhìn (đề xuất) · **MB** hai tầng · **ME** chỉ thấy cái đã động vào — xem [đợt 3 P2](docs/design/plans/2026-09-23-Remaining-Parameters-Measurement-Plan.md). Đã kiểm: MA để lại **32% độ phủ quan sát**, belief thưa chứ không mù |
| Quy ước quét $\chi$ | — | Thiết kế → **M4** | ✅ **Tan biến** | Ba quy ước (neo $\bar\kappa$ / $\kappa_{\min}$ / $\kappa_{\max}$) cho **kết quả trùng khít** | Hai bảng cùng $\chi$ trên cùng một hình dạng thì **tỉ lệ với nhau**, nên quy ước chỉ đổi thang. Khi $\kappa_{\text{commit}}$ và $\eta_Q$ **đi theo bảng** và ngân sách tính theo *tỉ lệ* hoá đơn audit, cả ba cho cùng một số — không còn gì để chọn |

W1–W5 xong 23/09; **W7 xong 24/09** — 240 game nhỏ giải chính xác, $\rho = 0{,}7500$ so với nghiệm thật, và cận Mệnh đề 6 hỏng **không phải vì rỗng mà vì sai đại lượng**; $\kappa_{\text{commit}}$, $\lambda_Q/\lambda_T$ và quy ước quét $\chi$ đều đã chốt. **Chỉ W6 ($c$) còn hỏng tiền đề**, và nó chờ quyết định T1 về mô hình quan sát chứ không chờ một phép đo. Nói cách khác: **phần đo đã cạn** — cái còn lại ở [§3.4](#34-issue-cần-xử-lý) là quyết định khung bài, không phải số.

### 3.3 So với giá trị dự phóng của draft

Các số "đo được" dưới đây chạy trên **thiết lập hiện tại** (chưa có thư viện 28 policy, chưa có held-out 7/18, MockAgent). Chúng chưa phải phép tái lập cuối cùng.

| Chỉ số | Dự phóng của draft | Đo được hiện tại | Ghi chú |
|---|---|---|---|
| **Độ lợi so với B1** | −34,1% (Sentinel, $\Delta > 2$) | **Không ô nào vượt ngưỡng 15%, ở bất kỳ $\Delta$ nào.** Ở $N = 100$ kèm CI95: tốt nhất cả bảng là `SSG-full receding` **+14,5%** CI [+9,7; +19,7] (strong, $\Delta=4$, và $\Delta=4$ **không được cổng chứng nhận**). `Sentinel` +2,2% CI [+0,4; +4,5] | **$N = 40$ đã nói dối:** ở đó ô này ra +17,8% và tôi báo "2/12 ô vượt ngưỡng". Nâng lên 100 workflow thì điểm ước lượng tụt dưới 15 và CI trùm qua ngưỡng. Bootstrap lấy mẫu **theo workflow**, thống kê là **độ lợi tương đối** chứ không phải $\Delta$-harm, vì ngưỡng phát biểu bằng phần trăm. `spikes/certified-power.json` |
| **Thang chi phí của lưới chính** | — | Lưới chính **chưa bao giờ** gọi `costs.install()` ⇒ mọi bảng đã công bố chạy trên **bảng placeholder**, đúng bảng README tuyên bố đã rút. Ba trong bốn tỉ số không thứ nguyên sai: $\chi$ 2,114 vs 1,349 · $\kappa_{\text{commit}}/\bar\kappa$ 2,343 vs 4,000 · $\eta_Q/\bar\kappa$ 1,143 vs 61,519 | Thứ tự carrier **đảo ngược** (memory từ rẻ nhất thành đắt nhất) — thứ $\chi$ không hề ràng buộc, nên trục $\chi$ kéo giãn hình dạng sai về đúng độ rộng. Riêng việc đổi thang **nâng** độ lợi (+43,4% → +49,7%) vì B1 mua được ít lượt commit-audit hơn (4,38 → 2,56) |
| **Cách ly: đường không tính tiền** | — | `runner.py` có hai đường cách ly, **chỉ một** bị trừ ngân sách. Qua một thay đổi giá **54×**, `Sentinel`/B5/B6 giữ **y nguyên 246/124/120** lượt và $L$ không đổi tới bốn chữ số | Tính tiền pro-rata rồi thì $Q_{\text{false}}$ về **0,000** ở mọi $\Delta$ và độ lợi của `Sentinel` tụt +49,7% → **+3,5%**. Đối chứng ở $r \approx 0$: **18/20 chính sách trùng khít** mã cũ ⇒ không phải giả tạo của bản sửa. `spikes/grid-usd-etaq-control.txt` |
| **Trục $\eta_Q$** | — | Trước khi sửa: **trơ theo cấu tạo**, không có điểm lật nào trong toàn dải. Sau khi sửa: số lượt cách ly đơn điệu **1335 → 3**, và **có điểm lật** SSG-G → SentinelW ở $r \in [20;\ 32]$ | Làm cách ly đắt lên **giúp** SentinelW: $L$ rơi 1,993 → 0,988 vì nó thôi cách ly phí. SSG-G phẳng 0,988 ở mọi $r$ — nó không cách ly. `spikes/eta-q-sweep.json` |
| Sentinel so với B1 trên $L$ | Sentinel thắng | Thắng ở 64/64 ô khi $\lambda_T = 0{,}5$; chỉ 22/64 khi $\lambda_T = 0$ | Phụ thuộc mạnh vào $\lambda_T$ |
| B5 so với Sentinel | B5 = 0,359, tệ hơn Sentinel 0,272 | **B5 dẫn trước ở 61/64 ô** ($\lambda_Q = 0{,}10$) | Lệch so với giả thuyết; đo lại sau khi có Sentinel-28 |
| **$\Delta > 2$: vùng hay một điểm** | Phát biểu trên **vùng** $\Delta > 2$ | Ở $H = 8$ vùng đó chứa **đúng một điểm**, $\Delta = 4$ — `plan_poison` lấy $\sigma$ từ `range(delta, H)` nên $\Delta \ge H$ **không có** cấu hình khả dĩ nào. Phủ thêm $\Delta = 6, 8$ bắt buộc phải $H \ge 9$, tức **corpus khác** | Mọi số headline trước 24/09 đứng trên một điểm $\Delta$ duy nhất |
| **Ô vượt ngưỡng có nằm trong vùng cổng chứng nhận không** | — | **Không — giao nhau bằng rỗng.** Cổng AUC v2 chứng nhận $\Delta \in \{0, 2\}$ (0,519 / 0,529, 20/20 split) và **từ chối $\Delta = 4$** (0,587, 1/20; permutation test xác nhận tách được thật, $p = 0{,}010$). Ở $N = 100$ **không ô nào** vượt ngưỡng, kể cả $\Delta = 4$; ô hợp lệ tốt nhất là SSG-G (strong, $\Delta=2$) **+10,6%** CI [+6,5; +15,2] — CI chạm 15 nên đọc là *chưa đủ lực để bác*, không phải *đạt* | Ở $\Delta = 4$ payload **phân biệt được bằng đặc trưng bề mặt**, nên ô đó đo một phần là "payload lộ" chứ không thuần "phân bổ audit dưới điều kiện ẩn". Đây là lý do mạnh nhất cho **khung B** mà tiền đăng ký [cong-v2-chot](docs/preregistration/cong-v2-chot.md) đã nêu |
| **Kết quả có bền theo chân trời không** | — | **Không.** Cùng $\Delta = 4$, detector mid, **cả hai ở $N = 40$**: `SSG-full receding` **+17,8% ở $H=8$** nhưng **+4,0% ở $H=12$**. Ở $H = 12$ **không ô nào** trong 18 vượt 15%, và **`B2 uniform random` thắng 5/18 ô**, gồm toàn bộ $\Delta = 6$ và $\Delta = 8$ | Giới hạn phải khai: `make_corpus(n, H, seed)` sinh workflow khác nhau theo $H$, nên phép so này **lẫn chân trời với corpus** — chưa tách được. Ở $\Delta = 8$ chỉ **22/40** workflow khả dụng nên mẫu số cũng co lại. `spikes/grid-usd-H12-delta8.txt` |
| **Ngân sách theo chân trời** | — | `budget_for_table` có $H$ **triệt tiêu** ⇒ ngân sách là hằng số ở mọi chân trời, suất mỗi task giảm theo $1/H$: 0,3205 ở $H=8$ nhưng **0,2137** ở $H=12$ | Lượt $H=12$ đầu tiên vì thế đo **đói ngân sách** rồi gọi đó là độ trễ — cả lưới dồn vào 0,99–1,00. Đã sửa; $H = 8$ không đổi một chữ số. Giữ lượt hỏng làm bằng chứng: `spikes/grid-usd-H12-starved-budget.txt` |
| Crossover | $\Delta \approx 2{,}1$ | Không có điểm hoà vốn ở $\Delta \le 1$ | Cùng hướng với Hệ quả 5 |
| RQ4: lợi thế lớn nhất ở detector yếu | 21,4%–39,8%, lớn nhất ở detector yếu | Không lớn nhất ở detector yếu (MockAgent) | Ngược giả thuyết |
| Tác động của $\chi$ | Thu hẹp độ lợi, làm chậm crossover | **Khớp hướng draft trên cả hai thang.** USD, cách ly có giá, $\Delta = 4$: **+6,4% → +4,6% → +3,5%** khi $\chi$ đi 0 → 0,5 → 1,349. Thang legacy cùng hướng: 62,4% → 61,8% → 52,0% | 40 workflow × 3 seed, detector mid, neo `mean`. Ghi chú cũ trong `policies.CHI_ANCHORS` nói trục này **trơ** — sai, nó viết từ lượt chạy mà $\kappa_{\text{commit}}$ và $\eta_Q$ chưa đi theo bảng. Đã sửa |
| **Ngân sách: trục chế độ thật sự** | — | **Kết quả âm là đặc tính của MỘT mức ngân sách, không phải của trò chơi.** Quét $B/(H\Sigma\kappa)$, $\Delta = 4$, độ lợi `SSG-full` so với B1: **0,16 → +14,4% · 0,3205 → +17,9% · 0,50 → +41,6% · 0,75 → +50,7% · $\ge$ 1,0 → +0,0%** | **Ba chế độ.** *Nghèo* ($\le 0{,}32$): không ai đủ tiền, khoảng cách nhỏ. *Giữa* (0,5–0,75): phân bổ quyết định, vượt ngưỡng 15% thoải mái. *Giàu* ($\ge 1{,}0$): B1 và họ SSG **cùng chạm sàn 0,158**, phân bổ hết ý nghĩa. **Mọi số đã công bố nằm ngay dưới mép dải giữa.** `spikes/budget-sweep.json` |
| **`Sentinel` ở chế độ giàu** | — | **Không bao giờ chạm sàn.** Ở ngân sách gấp đôi, B1/SSG-full/SSG-G đều về **0,158** còn `Sentinel` đứng ở **0,464**, SentinelW 0,356, B2 0,518 | Không phải thiếu tiền mà là **sai cấu trúc**: cho bao nhiêu ngân sách cũng không đuổi kịp. Đây là bằng chứng mạnh nhất cho việc đổi chính sách chủ đạo sang họ SSG |
| **$\rho$ và cận Mệnh đề 6** | $\rho = 0{,}07$ ⇒ cận 0,42; regret đo 0,09 | **240 game nhỏ giải chính xác**: $\rho$ so với nghiệm thật = **0,7500**, max regret **0,3333**, regret trung bình **0,0280** | Số 0,5078 dự án đang trích là **lớp tự phủ chính nó**, không phải khoảng cách tới nghiệm tối ưu — hai câu hỏi khác nhau. `spikes/small-games.json` |
| **TV có đo được mất mát không** | Mệnh đề 6 chặn mất mát bằng $H\rho\,\mathrm{range}(L)$ | **Không.** Thư viện cách nghiệm tối ưu 0,75 theo TV nhưng **tối ưu chính xác ở 175/240 game** và chỉ mất 2,8% trung bình | Rất nhiều coverage khác nhau cùng đạt một giá trị, nên xa theo TV **không tốn gì**. Cận không chỉ *rỗng* — nó dựng trên sai đại lượng |
| **Double oracle có cứu được không** | "nếu $\rho$ lớn thì thêm policy vào vùng thưa" | **Không.** Thêm 40 nghiệm tối ưu: $\rho$ 0,750 → 0,500, regret trung bình 0,0280 → 0,0219, **max regret y nguyên 0,3333** | Phương thuốc draft kê cho $\rho$ lớn không có tác dụng, vì khoảng cách không phải khoảng cách phủ. Con số **28 policy** vì thế vẫn chưa được biện hộ, và thêm policy không phải cách biện hộ nó |
| **Attacker best-response thật** | Mô hình phát biểu attacker best-response | `plan_poison` **bốc ngẫu nhiên** σ rồi `worst_case` max trên $(\Delta,k)$ ⇒ đại lượng đã công bố là $\max_k \mathbb{E}_\sigma$, **không phải** $\max_{k,\sigma}$. Attacker cũ dùng **1 trong 8** vị trí ở $\Delta=0$, 1 trong 3,9 ở $\Delta=2$ | Đo đúng mô hình: ở $\Delta = 0$ **mọi chính sách về harm 1,0000**, mọi độ lợi về **0,0%**. Trong vùng cổng chứng nhận ($\Delta \in \{0,2\}$) độ lợi tốt nhất tụt **+9,4% → +5,0%**. `spikes/best-response.json` |
| **Ngẫu nhiên hoá có giảm best-response gain không** | "commit to a distribution, reveal only the distribution" — đây đúng là đại lượng nó sinh ra để giảm | **Không. Ngược lại.** `Sentinel` tăng **nhiều hơn** chính bản tất định C8 của nó ở cả ba $\Delta$: +0,0167 / +0,0417 / +0,0315 so với C8 +0,0083 / +0,0250 / +0,0315 | Dự đoán BR4 khai trước, bị bác sạch. Cộng với ablation (bỏ belief 0,000, bỏ rotation 0,000), **cả ba cơ chế của `Sentinel` đều không làm được việc nó khai** |
| **Ablation ba cơ chế** | Bỏ randomisation tốn **0,184**; bỏ belief tốn **0,099** | Bốn arm, $\Delta = 4$, thang USD: bỏ randomisation **+0,027** · bỏ belief **0,000** · bỏ rotation **0,000** | Trong ba cơ chế `Sentinel` tự khai, **chỉ ngẫu nhiên hoá làm đổi số**, và chỉ bằng **1/7** mức draft nói. Belief đóng góp **đúng 0,0000** — khớp với bệnh đã ghi trong `policies.UPDATE_RULES`: dải belief 1,86 so với dải $1/\kappa$ 10,2 nên chi phí át hẳn. `spikes/ablation.json` |
| **Ablation "bỏ benign-drift"** | 0,264 (thấp hơn cả Sentinel đầy đủ 0,272) | **Không đọc được, và lý do quan trọng hơn con số.** Thế giới của benchmark **không có** benign drift để bỏ: không chỗ nào trong `build.py`/`core.py`/`runner.py` sinh churn lành tính; $\beta$ chỉ tồn tại như tiền nghiệm của hypothesis NULL trong `belief.py` | Thứ đóng vai drift ở đây là **báo động giả** của detector, nên arm này dựng một thế giới phản thực: item sạch không bao giờ fire. Nó ra 0,000 vì trên thang USD $Q_{\text{false}} = 0$ — không lượt cách ly nào mua nổi, nên bỏ báo động giả không đổi gì. Cũng là lý do $\beta$ trơ: belief cãi nhau với một nguyên nhân không có thật |
| Exploitability | 0,34 → 0,09 (thiết kế SSG **giảm** regret) | **Khớp, sau khi đo đúng đối tượng:** **SSG-G 0,0119** < B1 0,0179 < B7 0,0254 ≪ Sentinel 0,2076 < SentinelW 0,3219 | Lần đo trước báo ngược dấu vì `Sentinel` khi đó thiếu **hai trong ba cơ chế** nó tự khai (không có kênh commit, không có rotation). Vá xong thì SSG-G là chính sách **ít bị khai thác nhất** cả bảng |
| Worst-case trên held-out | 27,6% | **Thống kê của draft bão hoà**, không đọc được: worst-case trên 18 luật làm mọi harm dồn vào 0,89–0,98 và **chỉ 1/8** chính sách có CI tách khỏi 0. Thay bằng hai thống kê không bão hoà (N = 80, 9/18 held-out): **`Sentinel` là chính sách duy nhất** xuống cấp có ý nghĩa (harm trung bình/luật **+0,063**, CI [+0,017; +0,107]); **SSG-G và B1 không** xuống cấp có ý nghĩa ở bất kỳ thống kê nào | Chia 9/18 theo hash tên, **không vẽ lại** để khớp 7/18 của draft. SentinelW tốt nhất tuyệt đối cả hai phía (harm 0,262 → 0,308; chặn 5,92 → 4,86 trên 9 luật) |
| $\rho$; cận Mệnh đề 6 | 0,07 ⇒ cận 0,42, regret đo 0,09 | $\rho = \mathbf{0{,}5078}$ ⇒ cận $H\rho\,\mathrm{range}(L) = \mathbf{4{,}06}$ | Cận **rỗng**: lớn hơn toàn miền giá trị của $L$. Đo trên phân phối hành động theo từng task (không gian đúng); bản gộp cả episode cho 1,108 |
| $\kappa_{\text{commit}}$ | 4,1 (ngầm ≈ 2,34 $\bar\kappa$) | **$\ge 4{,}00\,\bar\kappa$ chỉ từ nửa review**, cộng thêm **0,599 giây CPU** chạy test (trung vị 6 instance sympy) | Vượt sẵn vùng lật 1,43–2,0 ⇒ **dấu của RQ1 không phụ thuộc đơn giá máy**. Giá hoà vốn giải ra **âm**, tức không hoá đơn CPU nào kéo tỉ số về được |
| $\lambda_Q/\lambda_T$ | 0,20 (gán tay) | **1,0973** đo được (dải 0,393–1,874) | Mã đang định giá một lần cách ly nhầm **rẻ hơn 5,5 lần** thực tế — và nó đã **chế ra một phát hiện giả** (xem dòng dưới) |
| Biên đánh đổi trung bình/xấu nhất | — | **Không tồn tại.** Ở $\lambda_Q$ sai thì Spearman($L$, regret) = −0,43 và trông như một biên; ở giá đo được là **+0,857**, và trên lưới 12 ô là **dương ở 10/12** | SSG-G tốt nhất trên **cả hai** trục. "Biên" từng báo chính là phép định giá sai nhìn nghiêng |
| Cách ly nhầm | 3,2% → 5,1% | Chưa đo trên điểm cuối chính | — |
| Detector bề mặt | — | $d' \le 0{,}50$, dưới $d'^{*} = 2{,}85$ | Phát hiện mới |
| Detector nội dung | — | AUC 0,479 ($D_{\text{lex}}$) · 0,518 ($D_{\text{llm}}$) khi attacker không tự khai báo | Phát hiện mới |
| Agent thật làm theo payload | Draft dùng agent mô phỏng | **0/7** (arm chính) · 0/3 (arm trần) | Ngoài thiết lập draft; đưa vào mục Threats |

Nguồn dữ liệu: `auditgame/spikes/grid-usd-scale.txt`, `grid-legacy-scale.txt`, `grid-usd-etaq-control.txt`, `eta-q-sweep.json`, `sweep-v2-pinned.json`, `sweep-v2-following.json`, `t2-chi-results.json`, `dprime-band.json`, `gamma-empirical.json`, `content-detector.json`, `band_curve.json`, `p2-pilot.jsonl`, `p2-ceiling-raw.jsonl`.

### 3.4 Issue cần xử lý

Xếp theo mức ưu tiên cho mốc đóng băng 30/09.

| # | Issue | Ảnh hưởng | Hướng xử lý |
|---|---|---|---|
| 1 | 🔴 Ô $\Delta = 4$ của cổng v2 đỏ — và **24/09 nó trở thành issue chặn**: hai ô duy nhất vượt ngưỡng 15% đều nằm ở $\Delta = 4$, nên giao giữa "vượt ngưỡng" và "được cổng chứng nhận" là **rỗng** (vùng chứng nhận tốt nhất chỉ +10,7%) | Quyết định khung bài. **Permutation test xác nhận độc lập**: $\Delta=4$ tách được thật ($p = 0{,}010$), không phải giả định của cận tham số | Chốt trước: chứng nhận $\Delta \in \{0,2\}$ hay lùi khung B. Hai phép kiểm **bất đồng** ở $\Delta \in \{0,2\}$ — cận Hanley–McNeil nói vượt trần, hoán vị nói bình thường ($p = 0{,}28$/$0{,}25$) ⇒ cận tham số đang **quá bảo thủ** ở đây |
| 2 | ✅ **Xong** — $\kappa_{\text{commit}}$ đo được, và dấu RQ1 **không phụ thuộc giá máy** | Nửa review một mình $= 4{,}00\,\bar\kappa$, vượt sẵn vùng lật 1,43–2,0; $T_{\text{test}} = 0{,}599$ s CPU chỉ đẩy thêm | Mở rộng ngoài sympy cần image Docker từng instance — ghi vào Threats, không chặn mốc đóng băng |
| 3 | ✅ **Dựng xong** `policies_library.py` (28) — và 240 game nhỏ nay nói rõ **28 chưa được biện hộ, theo cách khác với ta tưởng** | Không phải lớp thưa: lớp **tối ưu chính xác ở 175/240 game**. Nó xa theo TV mà không mất gì, vì nhiều coverage cùng đạt một giá trị | Bỏ lối biện hộ qua $\rho$. Muốn biện hộ 28 thì phải chỉ ra 28 policy đó **giảm regret**, và đo được là double oracle thêm 40 policy cũng không giảm max regret |
| 4 | ✅ **Xong** — 18/18 attacker, và best-response tối ưu tự do trên $(k,\iota,\sigma)$ | Exploitability **khớp dự phóng** sau khi đo đúng đối tượng (SSG-G 0,0119 < B1 0,0179). Held-out: thống kê của draft bão hoà, đã thay bằng hai thống kê đọc được | Đo ra kết quả âm: ở $\Delta = 0$ mọi chính sách về harm 1,0000; ngẫu nhiên hoá **không** giảm best-response gain (BR4 bị bác) |
| 5 | ✅ **Xong** — `freeze.py` + `require_frozen` nối vào `experiment.py` | Đủ cơ chế để chứng minh "không tune sau khi thấy kết quả" | Còn **chạy** `freeze.write()` vào mốc 29/09; trước đó `require_frozen` là no-op có chủ ý |
| 6 | ✅ **Xong** — `build.marker_for` băm toạ độ của chính đòn tấn công | Cổng 2 chứng nhận được thứ nó tuyên bố: không còn token nào phủ mọi payload | Không gian pool là 576; quá vài trăm payload thì marker lặp, lúc đó phải nới pool |
| 7 | $\lambda_T$, $\pi_0$, quy ước $\chi$ chưa neo | Ba lựa chọn này đổi thứ hạng chính sách | Neo trên dev theo §1.3, đóng băng trước khi chạy held-out |
| 8 | ✅ **Xong** — 240 game nhỏ đã giải chính xác, và câu trả lời mạnh hơn "cận rỗng": **TV không theo dõi mất mát** | Mệnh đề 6 chặn bằng $H\rho\,\mathrm{range}(L)$, nhưng lớp cách nghiệm tối ưu 0,75 theo TV lại tối ưu **chính xác** ở 175/240 game. Double oracle — phương thuốc draft kê — thêm 40 nghiệm mà **max regret y nguyên** | Bài nên báo **regret trực tiếp** thay vì báo $\rho$ rồi suy ra mất mát. Con số 28 policy vẫn chưa được biện hộ, và thêm policy không phải cách biện hộ |
| 9 | 🟡 **Gần xong** — image `auditgame:latest` đã dựng, 13 test container chạy và xanh **khi máy rảnh** | Gate 1 đạt 593/593, nhưng một lượt full lúc tải nặng lại bỏ qua cả 13 | Tìm chỗ quá hạn trong `container_ready()` và cho nó **báo lỗi thay vì bỏ qua** khi Docker có mặt mà phép kiểm hết giờ — một gate im lặng tụt về UNKNOWN là đúng thứ cổng 1 sinh ra để chống |
| 10 | Chỗ draft chưa chốt: $\chi = 1{,}34$; dòng ablation "bỏ benign-drift" (0,264) thấp hơn Sentinel đầy đủ (0,272); 15 repo so với 12 của SWE-bench | Ảnh hưởng cách trình bày phần so sánh | Hỏi thầy ý định thiết kế |
| 11 | ✅ **Xong** — bảng chứng nhận chạy lại khớp **đúng** số test in ra (0,5117 / 0,5247), nên lệch là giữa *tài liệu tiền đăng ký* (0,519 / 0,529) và mã, không phải giữa hai đường mã | Phán quyết **không đổi** dù lấy số nào: cả hai đều dưới xa trần 0,56, còn $\Delta = 4$ trên xa | Sửa ba con số trong `cong-v2-chot.md` cho khớp mã. Bài học: pha *sàng* ($N=80$, trung vị điểm) và pha *chứng nhận* ($N=900$, cận trên CI) là **hai thống kê khác nhau** — trộn chúng thì mọi $\Delta$ đều bị từ chối, và tôi đã mắc đúng lỗi đó một lượt |
| 12 | ✅ **Xong** — `costs.install()` dùng giá $\eta_Q$ đo được; `experiment.py` có `--scale` và mặc định `usd` | Hoá ra lớn hơn issue đã ghi: lưới chính **chưa bao giờ gọi** `install()`, nên chạy trên bảng placeholder chứ không phải "USD với $\eta_Q$ sai" | Mọi lượt chạy nay in bốn tỉ số không thứ nguyên và thứ tự carrier trong header |
| 13 | 🔴 **Không luận điểm nào vượt ngưỡng 15%.** Ở $N = 100$ kèm CI95: tốt nhất +14,5% CI [+9,7; +19,7] ($\Delta = 4$, **cổng từ chối**); ô hợp lệ tốt nhất +10,6% CI [+6,5; +15,2]; `Sentinel` +2,2%. Ablation: trong ba cơ chế chỉ ngẫu nhiên hoá làm đổi số, và chỉ **1/7** mức draft | Bài không thể phát biểu "Sentinel giảm harm 34%" nữa, và cũng không thể thay bằng một chính sách khác đạt 15% — **không có** chính sách nào đạt | Ba lựa chọn: đổi chính sách chủ đạo sang họ SSG · phát biểu lại luận điểm theo **vùng** ($\Delta \ge 2$, detector mid/strong) · hoặc báo cả hai chế độ giá cách ly và để $\eta_Q$ là trục. Đây là quyết định khung bài, phải chốt trước 29/09 |
| 14 | `Policy.eta_Q` (policies.py:123) mặc định **0,0** và không nơi nào trong mã đặt nó, trừ một test | Chặn "chỉ cách ly khi $E[\text{harm}]$ vượt $\eta_Q$" của Thuật toán 1 dòng 8 gần như **luôn mở** | Nối `pol.eta_Q` vào `ETA_Q_COST`, hoặc khai rõ nó là tham số riêng và quét. Chưa làm vì sẽ đổi số lần nữa — phải khai trước |
| 16 | ✅ **Xong** — `budget_for_table` giữ $B/(H\sum\kappa)$ cố định qua mọi chân trời | Công thức cũ có $H$ **triệt tiêu**, nên cột $\Delta = 8$ đầu tiên đo đói ngân sách (0,2137 so với 0,3205) rồi gọi đó là độ trễ; cả lưới dồn vào 0,99–1,00 | $H = 8$ không đổi một chữ số. Giữ lượt hỏng làm bằng chứng: `spikes/grid-usd-H12-starved-budget.txt` |
| 15 | 🔴 **Kết quả không bền theo chân trời** — SSG-full +17,8% ($H=8$) so với +4,0% ($H=12$) ở cùng $\Delta = 4$, cả hai ở $N = 40$; ở $H=12$ `B2 uniform random` thắng 5/18 ô | Nếu không tách được thì luận điểm chỉ phát biểu được cho **một** chân trời, và phải nói ra | Tách chân trời khỏi corpus: sinh corpus $H=12$ rồi **cắt** xuống $H=8$ thay vì sinh lại, để hai lưới dùng chung workflow |

**Phần làm vượt khỏi thiết lập draft:** sweep $d'$ liên tục, arm P2 với agent LLM thật, detector nội dung và prose world, 5 biến thể LP/SSG, sealed trace. ($\kappa$ theo USD không còn là phần làm thêm — nó là **thang vận hành** đã chốt.) Sweep $d'$ và P2 cho ra hai phát hiện mạnh nhất nên giữ. Không mở spike mới trước hạn nộp.

### 3.5 Kiểm thử

`tests/run_all.py --all` chạy lại cuối ngày **24/09/2026**: **811 đạt · 2 không đạt · 0 bỏ qua** (813 test). Hai lỗi là **đúng hai lỗi cũ** — không hồi quy nào qua bốn đợt sửa của hai ngày (thang chi phí, giá cách ly, ngân sách theo chân trời, cờ $\Delta$). Cổng 1 bắt được một lỗi thật giữa đường: `spent` của `replay.rescore` lệch với chạy trực tiếp vì tôi mới tính tiền cách ly ở một trong hai đường — đúng việc test I9 sinh ra để làm.

| Cổng | Kết quả |
|---|---|
| Gate 1 — Integrity | **593/593**, xanh ở hai lượt full lúc máy rảnh (24/09). ⚠️ Một lượt lúc CPU tải nặng bỏ qua đủ 13 test container trong khi chạy riêng cùng lúc đó thì 29/29 đạt ⇒ nghi `container_ready()` quá hạn khi tranh tài nguyên. Con số dùng được, nhưng phải chạy lúc máy rảnh và issue #9 phải sửa trước khi đóng băng |
| Gate 2 — Validity | 203/205, **đỏ** |
| Gate 3 — Power | 15/15 |

- Không đạt: `test_benign_corpus…test_one_split_cannot_decide_a_delta_of_the_certify_corpus`, một phát hiện đã ghi nhận: corpus đủ mạnh khiến tiêu chí đa phân hoạch mất tác dụng.
- Không đạt: `…some_epsilon_makes_the_payload_indistinguishable_at_every_delta` (pipeline `matched`, pha `screen`). Không $\varepsilon \in \{0;\ 0{,}2;\ 0{,}4;\ 0{,}7;\ 1{,}0\}$ nào đưa trung vị AUC ở $\Delta = 4$ xuống dưới trần (0,608 / 0,607 / 0,642 / 1,0 / 1,0). Liên quan trực tiếp tới điểm rẽ ngày 6.
- 13 test container chạy được sau `docker build -t auditgame:latest .`; chúng kiểm rằng agent **không** với tới được test ẩn hay đáp án từ trong sandbox của nó. ⚠️ Chúng **bỏ qua trở lại** nếu máy đang tải nặng, nên con số 593/593 chỉ đúng cho lượt chạy lúc rảnh.

---

## 4. Kế hoạch bổ sung: đưa các hạng mục còn thiếu vào sprint

Các hạng mục dưới đây trước đây xếp "sau hạn 02/10". Nay đưa vào sprint để tái lập đúng thiết lập draft. Thứ tự theo phụ thuộc: **W1 phải xong trước**, vì đổi $\pi_0$ làm sinh lại bảng $\tau_{\text{sel}}$ và chạy lại mọi bảng kết quả. W2–W5 độc lập nhau nên chạy song song được.

| # | Hạng mục | Việc cụ thể | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| W1 | $\pi_0$, $b_0$ suy dẫn | Thay giá trị gán 0,10 bằng $\pi_0 = 1/12{,}51 = 0{,}080$ (thế giới) và 0,040 (mô hình); sinh lại `reference/score_table.json`; quét $\pi_0 \in \{0{,}04;0{,}08;0{,}10;0{,}20\}$ để xem thứ hạng có đổi không | — | ✅ **Xong 23/09** — bảng sinh lại (23 phút), ba cổng không có test nào gãy; phần quét còn lại |
| W2 | $\eta_Q$ | $\eta_Q(k) = c_{\text{detach}}(k) + c_{\text{restore}}(k)$: đo phần gỡ bằng hiệu CPU-time khi che carrier; phần phục hồi tính từ $n_{\text{live}}(k)$ đã đo (`costs.ITEMS_PER_AUDIT`); kiểm $\eta_Q(k) > \kappa(k)$ | — | ✅ **Xong** — `tools/measure_eta_q.py`, ra **61,5×**. Phần gỡ đo ra $\le 0$ ⇒ là **cận dưới**. `costs.install()` đã dùng giá này từ 24/09, và vì nó khiến **không lượt cách ly nào mua nổi**, $\eta_Q$ chuyển sang **M2 (quét)**: `tools/sweep_eta_q.py` |
| W3 | $\beta_k$ | Khai báo luật ánh xạ commit → carrier; đếm trên cửa sổ commit giữa hai task của 10 repo đã clone trong `auditgame/workspace/`; báo trung vị và dải theo repo; phân tích độ nhạy với một luật thay thế | — | ✅ **Xong 23/09** — `tools/measure_beta.py`. Hai luật lệch 10× ở skill ⇒ theo tiêu chí khai trước, skill và queue **chuyển sang M2 (quét)** |
| W4 | $\kappa$ và thang chi phí | Đổi đồng hồ sang `process_time`; **hiện thực 4 checkpoint làm việc thật** (`checkpoints.py`) vì trước đó CPU-time đo bộ mô phỏng; so ba thang trên cùng một lưới (`tools/compare_cost_scales.py`) | — | ✅ **Xong 23/09** — $\chi$: 1,349 (USD) / 1,295 (CPU) / 2,114 (draft). **Chốt USD làm thang vận hành.** Còn lại: $\kappa_{\text{commit}}$ (issue #2) |
| W5 | $\Delta$ thực trên SWE-bench | Co-change (support, confidence) + lọc bằng đồ thị import trên 10 repo đã clone. **Đề xuất thay `git bisect` bằng SZZ** (`git blame` trên dòng mà gold patch sửa): bisect cần môi trường chạy được test ở mọi commit, tốn Docker cho từng repo | — | ✅ **Xong 23/09** — `measure_delta_swebench.py` + `measure_cochange.py`. Chỉ **19%** instance có $\Delta \ge 2$; chỉ **19%** cặp co-change mạnh có đường import thật |
| W6 | Hằng số $c$ (Định lý 4) | Tìm $B_{\min}$ bằng tìm kiếm nhị phân trên ngân sách, lấy mốc là khối lượng posterior đặt lên window thật tại $\sigma$; tính $c$ từng ô rồi lấy max; hồi quy $\log c$ theo ba thừa số để kiểm dạng hàm của cận | W1 | 🔴 **Từ chối đo 23/09** — tiền đề hỏng: posterior đứng yên ở 0,000336 từ $B = 2$ tới 200 vì belief nhận tín hiệu **mọi** carrier mỗi task ⇒ quan sát miễn phí. Phải sửa mô hình quan sát trước (quyết định T1) |
| W7 | 240 game nhỏ + $\rho$ | Sinh lớp game nhỏ ($K \cdot H \le 40$), giải chính xác bằng LP hiện có; đo $\rho$ bằng TV trên vector xác suất hành động **theo từng task**; so với cận $H\rho\,\text{range}(L)$ của Mệnh đề 6 | Thư viện 28 policy (issue #3) | ✅ **Xong 24/09** — 240 game, $\rho = 0{,}7500$ so với nghiệm thật; phát hiện thêm: TV không theo dõi mất mát, và double oracle không đóng được khoảng cách |
| W8 | Payload đã công bố | Port khuôn payload AgentPoison (trigger tối ưu hoá) và MINJA (bridging step + indication prompt) thành 2 attacker kịch bản, tính vào lớp 18 attacker | Issue #4 | ⏳ Chưa bắt đầu |
| W9 | Nền lành tính thật, $N = 500$, 3 attacker LLM | Chạy trên toàn bộ 500 instance SWE-bench Verified với nền lành tính thật và attacker LLM | W8; ngân sách LLM | ⏳ Chưa bắt đầu |
| W10 | Biện hộ các tham số thiết kế | Sinh bằng chứng cho những số mà draft nêu nhưng không có nguồn: ablation $K = 2, 3$; phân phối độ dài workflow để chọn $H$; phân tích lực để chọn $N$ và số seed; ngưỡng AUC suy từ CI thay vì lấy 0,56. **Vế "$\rho$ bão hoà để biện hộ 28" đã khép** — W7 cho thấy lối biện hộ đó không dùng được: lớp tối ưu chính xác ở 175/240 game, nên $\rho$ không nói gì về việc cần bao nhiêu policy | W7 ✅ | 🟡 Một vế xong; phần còn lại chưa bắt đầu |

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
python3 experiment.py --n 100 --deltas 0 1 2 4   # --scale mặc định `usd`; --budget suy từ bảng chi phí
python3 tools/sweep_budget.py                # bản đồ chế độ theo ngân sách (kết quả chính)
python3 tools/certified_power.py --n 100     # độ lợi kèm CI95, lấy mẫu lại theo workflow
python3 tools/best_response.py               # attacker chọn (k, ι, σ) thay vì bốc
python3 tools/ablation_arms.py               # bốn arm ablation
python3 tools/plot_regime_map.py > ../docs/manuscript/figures/regime-map.svg
python3 spikes/trace_one_episode.py          # in một ván chạy đầu-tới-cuối
python3 tests/run_all.py                     # ba cổng kiểm thử, dừng ở cổng đỏ đầu tiên
python3 tests/run_all.py --all               # chạy cả ba cổng (khoảng 7 phút)
```

Phần phân tích (scipy, scikit-learn) và công cụ SWE-bench cần môi trường đầy đủ: `uv sync`, rồi chạy bằng `../.venv/bin/python`.

Các lượt chạy với LLM thật có chi phí và không tái lập được theo seed. Kết quả của chúng được lưu tại `auditgame/spikes/*.jsonl` và chỉ được đọc lại, không chạy lại.
