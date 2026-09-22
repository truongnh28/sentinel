# Sentinel — AuditGame-SE: Progress Status Report

**Đề tài:** FSE-2027-15 · **Học viên:** Nguyễn Hữu Trưởng · **GVHD:** TS. Lê Xuân Bách · **Cập nhật:** 22/09/2026

Repo này chứa mã nguồn và tài liệu của đề tài Sentinel. Đề tài mô hình hoá việc phân bổ audit như một trò chơi Stackelberg giữa bên phòng thủ và kẻ tấn công. Kẻ tấn công đầu độc các *carrier* dai dẳng của một coding agent (`memory · skill · queue · branch`), và thiệt hại chỉ lộ ra sau độ trễ $\Delta$ task. Benchmark **AuditGame-SE** dựng workflow từ SWE-bench, tiêm payload, chạy agent (mock hoặc LLM thật), chấm harm bằng oracle niêm phong, rồi so sánh các chính sách audit B1–B7 với Sentinel.

README này là **báo cáo tiến độ**: đang làm gì, tới đâu, và việc gì cần quyết. Hướng dẫn chạy nằm ở cuối trang.

---

## Status

| | |
|---|---|
| **Đang làm** | Nước rút nộp **FSE 2027 Research Papers**, hạn **02/10/2026 AoE** (trưa 03/10 giờ Việt Nam). Hôm nay là **ngày 5/14**, còn **10 ngày**. |
| **Khung bài đã chốt** | **A′ — "bản đồ chế độ"** (chốt 18/09 tại điểm rẽ ngày 4). Sentinel thắng audit-at-commit (B1) trên hàm mất mát $L$, nhưng **thua B5 risk-score**. Bài phát biểu về *ranh giới chế độ*, không về Sentinel. |
| **Mốc kế tiếp** | **Ngày 6 (23/09):** chạy bảng chứng nhận cổng v2 một lần. Có attacker hợp lệ qua cổng thì giữ A′, không có thì lùi về **khung B** (benchmark tự phản biện). Ánh xạ kết quả → khung đã chốt trước. |
| **Rủi ro lớn nhất** | Trên agent thật (P2, `deepseek-v4.1-flash`), tỉ lệ làm theo payload là **0/7**. Mọi số harm hiện có là harm dưới mô hình tiếp nhận của MockAgent. |
| **Kiểm thử** | `tests/run_all.py --all` ngày 22/09: **756 đạt · 1 không đạt · 13 bỏ qua** (chi tiết ở mục [Chạy](#chạy)). |

## Cần thầy quyết

1. **Cách viết Đe doạ 3 — agent thật không làm theo payload (0/7).** Giữ tuyên bố với nhãn *"harm dưới mô hình tiếp nhận của MockAgent"*, hay chạy thêm arm model thứ hai (chưa chạy) trước khi đóng băng số ngày 30/09?
2. **Quy ước chuẩn hoá khi quét $\chi$.** Neo $\bar\kappa$ (hiện hành) làm trục $\chi$ rỗng theo cấu trúc: độ lợi 39,7% ở mọi $\chi$. Neo $\kappa_{\min}$ thì $\chi$ có tác dụng (39,7% → 36,1%). Lựa chọn này quyết định trục $\chi$ của ranh giới vùng có nội dung hay không.
3. **Vai trò của $(\psi, \varphi)$.** Detector bề mặt chỉ đạt $d' \le 0{,}50$; detector nội dung sụp về ngẫu nhiên khi attacker không tự khai báo. Coi $(\psi,\varphi)$ là biến kiểm soát thuần tuý, hay đưa điều kiện "detector phải đạt $d'^{*}$" thành kết luận chính?

---

## Lịch nước rút 14 ngày

| Ngày | Việc | Trạng thái | Kết quả |
|---|---|---|---|
| 1 — 18/09 | P2 runner; $\tau_{\text{sel}}$ chạy theo $d'$ | ✅ Hoàn thành | Đã tách được confound của phép quét $d'$ |
| 2 — 19/09 | Chạy P2 → **điểm rẽ P2** | ✅ Hoàn thành | 14 instance, 7 chấm được: 0 B / 0 C / 0 D, tuân thủ **0/7**. Điều kiện dừng #2 không kích hoạt theo quy tắc, nhưng tiền đề đe doạ không tái tạo được trên agent thật |
| 3–5 — 20–22/09 | Cổng v2 trọn gói; sweep chấm $L$ có B5, B6 | ✅ Hoàn thành | Cổng v2 đóng băng 19/09 (qua điều kiện dừng #3); sweep chấm $L$ trên payload v2 |
| 4 — 21/09 | **Điểm rẽ L** → A hay A′ | ✅ Xong sớm (18/09) | **Khung A′**: thắng B1 ở 64/64 ô; thua B5, không tồn tại ranh giới $\lambda_Q > 0$ |
| **6 — 23/09** | **Bảng chứng nhận v2 → điểm rẽ v2** | ▶️ **Tiếp theo** | Ô chứng nhận $\Delta=0$: 0,519 và $\Delta=2$: 0,529 qua 20/20 split; $\Delta=4$ còn đỏ (0,587) |
| 7–9 — 24–26/09 | Chuỗi bảng `m`; lưới $N=100$ trên MockAgent; G4 nhãn mù | ⏳ Chưa đến | Hạn G4: 26/09 |
| 10–11 — 27–28/09 | Evaluation, threats, ablation RQ4 | ⏳ Chưa đến | — |
| 12 — 30/09 | **Đóng băng số**; chạy 3 cổng lần cuối; artifact ẩn danh | ⏳ Chưa đến | — |
| 13–14 — 01–02/10 | Bản cuối, format ACM, **nộp** | ⏳ Chưa đến | — |

**Ba điều kiện dừng:** #1 cổng v2 tự vỡ — chưa kích hoạt · #2 P2 âm nặng — không kích hoạt theo quy tắc (xem ngày 2) · #3 v2 chưa đóng băng hết ngày 5 — đã qua.

---

## Tiến độ theo 11 stage của phương pháp luận

Khung stage theo [tài liệu phương pháp luận](docs/Phuong-phap-luan-trien-khai.md), Phần IV. **4 hoàn thành · 1 làm theo hướng khác · 6 một phần · 0 chưa bắt đầu.**

| Stage | Nội dung | Trạng thái | Đã có | Còn thiếu |
|---|---|---|---|---|
| 0 | Giả định, luật chơi | ✅ Hoàn thành | Tuple game; loss ba số hạng; defender chỉ nhận `CarrierSignal(p, n)` — cạnh bị cấm cưỡng chế bằng chữ ký hàm và test | — |
| 1 | Môi trường, workflow SWE-bench | 🟡 Một phần | SWE-bench Verified đã nối; sort `created_at`; topic từ gold patch; $\theta = 0{,}5$ chốt trước khi đếm workflow | Chỉ **14/58** workflow khả dụng ở $H=8$ (cần 100); chưa lọc instance flaky |
| 2 | Chi phí audit $\kappa \to \chi$ | 🟡 Một phần | Công thức $\chi$ công bố ($2{,}11 \ne 1{,}34$ của bản thảo); $\kappa$ đo theo đơn giá chấm LLM | Đo theo CPU-phút; thí nghiệm chính vẫn dùng bảng $\kappa$ của bản thảo; quy ước quét $\chi$ |
| 3 | Attacker, ground truth, oracle | 🟡 Một phần | Sinh $(\iota,\sigma)$ có lọc nổ sớm; 12 attacker kịch bản, 6 held-out chia bằng hash; $\Delta$ thực đo được (trung vị 3) | 18 attacker; attacker best-response đọc $\pi_D$; marker duy nhất mỗi lần chạy; $\Delta = 8$; harm vẫn chấm bằng marker (test ẩn neo được 1/500) |
| 4 | Corpus lành tính, cổng AUC, $\beta$ | ✅ Hoàn thành | Cổng v2 đóng băng 19/09: 5 đặc trưng, tiêu chí cận trên CI, 20 split; corpus từ item SWE-bench thật, ghép theo tuổi | $\beta$ chưa đo; permutation test |
| 5 | Detector $\psi / \varphi / \gamma$ | ✅ Hoàn thành | $d'$ suy từ $(\psi,\varphi)$; quét $d'$ liên tục → $d'^{*} = 2{,}85$ ($\Delta=2$), $0{,}95$ ($\Delta=4$); detector nội dung đã thử | — |
| 6 | Belief, thư viện policy, $\rho$ | 🟣 Hướng khác | Belief trên window tính chính xác (thay particle filter); minimax LP — B7, B7U, SSG receding/guarded — thay thư viện 28 policy | 240 game nhỏ giải chính xác; $\rho$ đo đúng không gian |
| 7 | Ví dụ tính tay | ✅ Hoàn thành | `spikes/trace_one_episode.py` phát lại một episode bằng tay với số thật | — |
| 8 | Đóng băng bằng hash | 🟡 Một phần | Hash cấu hình; digest cổng v2; payload đóng băng; tài liệu tiền đăng ký | Manifest phủ toàn bộ policy / attacker / hằng số; harness từ chối policy chưa đóng băng |
| 9 | Chạy lưới, tính output | 🟡 Một phần | Lưới $\Delta \in \{0,1,2,4\}$ × 3 detector trên mock; chấm $L$; $\lambda_Q^{*}$; bootstrap theo workflow; bảng chi tiêu | $N = 100$; $\Delta = 8$; trục $\chi$ trong đường chính |
| 10 | Tối ưu, ranh giới tuning | 🟡 Một phần | LP Stackelberg (Conitzer–Sandholm); ranh giới tuning thực thi qua tiền đăng ký | Double oracle |

---

## Trạng thái ước lượng tham số

Chi tiết phương pháp: [Parameter Estimation Report](docs/AuditGame-SE_Parameter_Estimation_Report.md). Bốn phương thức xác lập: **M1** đo trực tiếp · **M2** neo rồi quét · **M3** suy dẫn từ thiết kế thí nghiệm · **M4** khử tham số (phát biểu kết luận dưới dạng ngưỡng).

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

## Phát hiện đã có — kết quả đo khác với dự phóng

Mọi số hiệu năng trong bản thảo gốc là giá trị dự phóng. Các phép đo đã chạy trong repo cho thấy những điểm sau:

| Phát hiện | Số liệu | Dữ liệu |
|---|---|---|
| Trên $L$ (payload v2, $\lambda_Q = 0{,}10$), B5 risk-score dẫn trước Sentinel | 61/64 ô lưới | `auditgame/spikes/sweep-v2-pinned.json`, `sweep-v2-following.json` |
| Sentinel thắng B1 chủ yếu nhờ số hạng $T_{\text{lost}}$ | Dẫn B1 ở 64/64 ô khi $\lambda_T = 0{,}5$, chỉ 22/64 khi $\lambda_T = 0$ | sweep chấm $L$ (`dprime_sweep.py`) |
| Detector bề mặt không đạt điểm hoà vốn | $d' \le 0{,}50$ so với $d'^{*} = 2{,}85$ ($\Delta=2$) | `auditgame/spikes/gamma-empirical.json`, `dprime-band.json` |
| Detector nội dung sụp khi attacker không tự khai báo | AUC 0,479 ($D_{\text{lex}}$) · 0,518 ($D_{\text{llm}}$) | `auditgame/spikes/content-detector.json` |
| Agent LLM thật không làm theo lời khuyên độc, nên giả định $P(\text{harm} \mid \text{retrieved}) = 1$ không đứng | 0/7 instance chấm được ở arm chính; 0/3 ở arm trần (lời khuyên ~300 ký tự) | `auditgame/spikes/p2-pilot.jsonl`, `p2-ceiling-raw.jsonl` |
| Ngưỡng AUC 0,56 của cổng bề mặt nằm trong dải nhiễu của corpus | ở mọi cỡ mẫu $n \le 1800$ | `auditgame/spikes/band_curve.json` |
| $\chi$ không tác động lên nghiệm minimax (quy ước neo $\bar\kappa$) | độ lợi 39,7% ở mọi $\chi$ | `auditgame/spikes/t2-chi-results.json` |
| Ngân sách kỳ vọng của LP lạc quan hơn thực thi có ràng buộc cứng | độ phủ $-13{,}29\%$ | Monte Carlo 1.000 lần trên `smoke_repro.p_minimax`; file kết quả chưa được commit |
| Trên MockAgent, lợi thế của Sentinel không lớn nhất khi detector yếu nhất, trái với dự đoán RQ4 | — | `python3 experiment.py --n 40` |
| Không có điểm hoà vốn ở $\Delta \le 1$, khớp Hệ quả 5 | $d'^{*}$ không tồn tại | `auditgame/spikes/dprime-band.json` |

---

## Sau hạn 02/10 — cho luận văn và major revision

- Đo các tham số còn thiếu: $\beta$, $\eta_Q$, suy dẫn $\pi_0 = 0{,}080$ (thay cho giá trị gán 0,10), hằng số $c$ của Định lý 4.
- Nền lành tính thật, $N = 500$, 3 attacker LLM, payload đã công bố (AgentPoison, MINJA).
- Thư viện policy tham số hoá và lớp game nhỏ giải chính xác — điều kiện để kiểm chứng số cho Mệnh đề 6.
- Manifest đóng băng toàn phần, có cưỡng chế trong harness.

---

## Tài liệu

1. **[Phương pháp luận triển khai](docs/Phuong-phap-luan-trien-khai.md)** — tài liệu chính: bài toán, mô hình, lý thuyết, triển khai theo 11 stage, nguồn gốc tham số, đe doạ tính hợp lệ.
2. **[Khảo sát nguồn](docs/Khao-sat-nguon-phuong-phap-luan.md)** — cơ sở trích dẫn cho tài liệu chính, kèm lệnh chạy harness và kế hoạch thực hiện.
3. **[Parameter Estimation Report](docs/AuditGame-SE_Parameter_Estimation_Report.md)** — báo cáo phương pháp ước lượng tham số: bốn phương thức xác lập, kết quả các đại lượng đã ước lượng, thủ tục cho các tham số chưa xác lập.

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
python3 tests/run_all.py --all               # chạy cả ba cổng
```

Phần phân tích (scipy, scikit-learn) và công cụ SWE-bench cần môi trường đầy đủ: `uv sync`, rồi chạy bằng `../.venv/bin/python`.

Trạng thái kiểm thử ngày 22/09/2026 (`--all`): **756 đạt · 1 không đạt · 13 bỏ qua**.
- Không đạt: `test_benign_corpus…test_one_split_cannot_decide_a_delta_of_the_certify_corpus`, một phát hiện đã ghi nhận: corpus đủ mạnh khiến tiêu chí đa phân hoạch mất tác dụng.
- 13 bỏ qua: cần image Docker `auditgame:latest` (`docker build -t auditgame:latest .`).

Các lượt chạy với LLM thật có chi phí và không tái lập được theo seed. Kết quả của chúng được lưu tại `auditgame/spikes/*.jsonl` và chỉ được đọc lại, không chạy lại.
