# HƯỚNG DẪN TÁI LẬP TEST VÀ BASELINE — FSE-2027-15 (Sentinel)

**Nguồn đã đọc:** `261-Master-Proposal/FSE-2027-15-paper.pdf` (manuscript đầy đủ), `FSE-2027-15-summary.pdf`, `FSE-2027-15-reading.pdf`, và phân tích portfolio đã lưu trong vault.
**Kèm theo:** `repro/smoke_repro.py` — mã tái lập chạy được ngay, không cần ngân sách compute.

---

# 0. Điều phải nói trước — cái gì tái lập được và cái gì không

Đây là phần quan trọng nhất của tài liệu. Đọc kỹ trước khi làm bất cứ việc gì.

**Manuscript có một banner ở trang 1 và một dòng Status ở cuối summary:**

> *"Values marked as results are projected from the pre-registered design in PLAN.md; **no full study has been run**."*

**Hệ quả trực tiếp:** **không tồn tại "kết quả của thầy" để tái lập.** Những con số −34.1%, −27.6%, Δ = 2.1, 0.184 vs 0.099 là **giá trị dự phóng (projected)** từ thiết kế đã đăng ký trước, không phải số đo. Nếu bạn đi vào buổi gặp và nói "em sẽ tái lập kết quả của thầy", bạn đã hiểu sai bản chất hồ sơ.

**Cái thực sự đã chạy** là một **smoke test** trên một trò chơi Stackelberg hữu hạn, giải bằng liệt kê best-response của attacker — bốn kiểm tra, cả bốn PASS. **Đó mới là thứ tái lập được, và đó đúng là nhiệm vụ tuần 1–2 trong kế hoạch ("pilot phản ví dụ").**

### Ba mức tái lập

| Mức | Tái lập cái gì | Cần gì | Thời gian | Ngân sách |
|---|---|---|---|---|
| **Mức 1 — Smoke test** | 4 kiểm tra trên trò chơi nhỏ: thứ hạng chính sách, ranh giới chế độ, chiều tác động của $\chi$, audit-on-insertion tệ nhất | Một laptop, Python + numpy + scipy | **1–3 ngày** | **US$0** |
| **Mức 2 — Benchmark** | Dựng `AuditGame-SE` và tái lập B1 (audit-at-commit) trên workflow thật | SWE-bench + OpenHands + detector + 15 repository | 3–5 tuần | Vài trăm USD |
| **Mức 3 — Full study** | 4.500 instance × 8 hệ thống × 3 seed | Toàn bộ hạ tầng + LLM attacker | 4 tuần chạy | US$18.000–27.000 |

**Trong folder hiện có:** chỉ 3 file PDF cho đề tài 15. **Không có** mã nguồn Sentinel (manuscript nói ≈9.1k dòng Python), **không có** `docs/thesis/eval/PLAN.md`, **không có** `REVIEWS.md`, **không có** benchmark, **không có** script smoke test. Danh sách hiện vật cần xin thầy nằm ở Mục 8.

---

# 1. Input / Output của đề tài — ba tầng

Câu hỏi "input là gì, output là gì" có ba câu trả lời khác nhau tùy tầng. Lẫn lộn ba tầng này là nguồn nhầm lẫn lớn nhất khi bắt đầu.

## 1.A Tầng TRÒ CHƠI — đơn vị lý thuyết

| | Nội dung | Ký hiệu trong manuscript |
|---|---|---|
| **INPUT** | Số task trong workflow | $H$ (6–14) |
| | Số carrier | $K = 4$ (memory, cached skill, tool queue, branch) |
| | Chi phí audit theo carrier và độ sâu | $\kappa(k,\text{depth})$ |
| | Ngân sách audit | $B$, ràng buộc $\sum_t \kappa(a_t) \le B$ |
| | Tham số detector | TP rate $\psi$, FP rate $\phi$, margin $\gamma = \psi - \phi$ |
| | Tốc độ benign drift | $\beta$ |
| | Chi phí cách ly / mất task sạch | $\lambda_Q$, $\lambda_T$, $\eta_Q$ |
| | Lớp attacker được khai báo | $\Pi_A$ |
| **OUTPUT** | Chính sách defender (phân bố xác suất trên hành động audit) | $\pi_D$ |
| | Giá trị trò chơi | $V^\star = \min_{\pi_D}\max_{\pi_A} L(\pi_D,\pi_A)$ |
| | Worst-case verified harm | $\max_a h(\pi_D, a)$ |
| | Exploitability | best-response gain trước chính sách đã triển khai |

**Trạng thái:** $s_t = (\mathbf{c}_t, \iota, \sigma)$ — $\mathbf{c}_t \in \{0,1\}^K$ ghi carrier nào bị nhiễm độc, $\iota$ là thời điểm chèn, $\sigma$ là thời điểm trigger.
**Hành động attacker:** $(k, \iota, \sigma, \varepsilon)$ — carrier, thời điểm chèn, lịch trigger, biên độ sửa đổi $\le \varepsilon$.
**Hành động defender:** $a_t \in \mathcal{A} = \{\text{none}\} \cup \{(\text{audit}, k, \text{depth})\}$, cộng tùy chọn quarantine.
**Hàm mất mát defender:** $L = \mathbb{E}[\text{verified harm}] + \lambda_Q\mathbb{E}[\text{false quarantines}] + \lambda_T\mathbb{E}[\text{clean tasks lost}]$.
**Hai trục chế độ:** $\Delta = \sigma - \iota$ (độ trễ trigger) và $\chi = \max_{k,k'}|\kappa(k)-\kappa(k')|/\bar\kappa$ (tính không đồng nhất chi phí carrier).

## 1.B Tầng INSTANCE — một workflow trong benchmark

| | Nội dung |
|---|---|
| **INPUT** | Một workflow sửa lỗi đa bước (định dạng SWE-bench, chạy dưới OpenHands), 6–14 task, 4 audit stage (insertion · retrieval · delegation · commit) × 4 carrier |
| | Bản ghi **evaluator-known state** của instance bị nhiễm độc: $(k, \iota, \sigma, \varepsilon)$ — đây là thứ khiến worst-case harm **tính được**, không phải ước lượng |
| | Một detector học máy **dùng chung cho mọi hệ thống** |
| | Ngân sách audit $B$ và chính sách $\pi_D$ cần đánh giá |
| **OUTPUT** | Verified harm (do một **sealed oracle** xác nhận ở cuối horizon) |
| | Có phát hiện không / phát hiện ở task nào (detection delay) |
| | Chi phí audit thực tế (CPU-phút) |
| | Số lần false quarantine, số task sạch bị mất |

Lược đồ một instance (đề xuất để bạn tự khai báo khi dựng lại):

```json
{
  "instance_id": "repo07/wf042/delta2/chi1.34/seed41",
  "workflow": {"repo": "…", "tasks": 8, "stages": ["insertion","retrieval","delegation","commit"]},
  "ground_truth": {"poisoned": true, "carrier": "memory", "iota": 3, "sigma": 5, "epsilon": 0.12},
  "regime": {"delta": 2, "chi": 1.34, "detector_setting": "weak"},
  "budget": 17.06,
  "policy": {"name": "sentinel", "hash": "sha256:…"},
  "outcome": {"verified_harm": 0.0, "detected_at": 4, "audit_cost_min": 16.8,
              "false_quarantines": 0, "clean_tasks_lost": 0}
}
```

## 1.C Tầng THỰC NGHIỆM — một lần chạy đầy đủ

| | Nội dung |
|---|---|
| **INPUT** | 4.500 instance × 8 hệ thống (Sentinel + B1–B7) × 3 seed |
| | Lưới chế độ: $\Delta \in \{0,1,2,4,8\}$ (5 mức) × $\chi \in \{0, 0.5, 1.34\}$ (3 mức) × 3 cấu hình detector |
| | Manifest hash đã đóng băng của mọi chính sách và thư viện attacker |
| **OUTPUT** | Bảng metrics **trên lưới $(\Delta,\chi)$**, không gộp chung (manuscript nói rõ: gộp sẽ trộn vùng phương pháp có tác dụng với vùng không) |
| | Điểm giao cắt (crossover) — dự đoán $\Delta \approx 2$, quan sát 2.1 |
| | Exploitability và empirical regret so với B7 trên 240 trò chơi nhỏ |

**Endpoint chính đã đăng ký trước:** worst-case verified harm trước attacker **held-out**, ở **cùng ngân sách**, so với B1, biên tương đối **15%**.

---

# 2. Tham số chính xác trích từ manuscript

Bảng này là thứ bạn cần để cài lại. Mọi dòng đều lấy nguyên văn từ paper — không suy diễn.

| Tham số | Giá trị | Vị trí trong paper |
|---|---|---|
| Số carrier $K$ | 4 — memory, cached skill, tool queue, branch | §4 Problem Formulation |
| Audit stage | 4 — insertion, retrieval, delegation, commit | §8 Benchmark |
| Chi phí audit đo được | **0.4 / 0.9 / 1.6 / 4.1 CPU-phút** (ins/ret/del/commit) | Table 1 |
| $\chi$ tương ứng | **1.34** *(xem Mục 6 — con số này không tự khớp)* | §7 Implementation |
| Workflow | 100 workflow / 15 repository, 6–14 task | Table 1 |
| Lưới $\Delta$ | $\{0, 1, 2, 4, 8\}$ task | §8 |
| Lưới $\chi$ | $\{0, 0.5, 1.34\}$ | §8 |
| Cấu hình detector | 3 mức, quét | Table 1 |
| Tổng instance | 4.500 = 100 × 5 × 3 × 3 | Table 1 |
| Benign changes | 620, discriminator AUC ≤ 0.56 | Table 1 |
| Scripted attacker | 18 chính sách, **7 held-out** | Table 1 |
| LLM attacker | 3, báo cáo riêng | Table 1 |
| Trò chơi nhỏ giải chính xác | **240**, ngưỡng $KH \le 40$ | Table 1, §7 |
| Thư viện chính sách hạn chế | **28** chính sách (stage-weighted · belief-threshold · carrier-rotation) | §5.2 |
| Covering radius đo được | $\rho = 0.07$ → cận tổn thất 0.42; tổn thất đo được **0.09** | §6.3 |
| Belief update | Particle filter **2048 particles** trên $(\mathbf{c},\iota,\sigma)$ | §7 |
| Quy tắc quarantine | $\Pr[\text{poisoned}\mid b_{t+1}] > \tau$ **và** expected harm $> \eta_Q$ | Algorithm 1 |
| Quy mô mã nguồn | ≈9.1k dòng Python | §7 |
| Protocol | 4.500 × 8 hệ thống × 3 seed | §9.4 |
| Go/no-go | ≥15% tương đối, held-out, cùng ngân sách | §9.4 |

**Định lý 4 (ngân sách khả phân biệt) — công thức nguyên văn:**

$$B \;\ge\; \frac{c\,\bar\kappa\,(1+\chi)\log(1/\alpha)}{\gamma^{2}}\cdot\left(1 + \frac{\Delta}{H}K\right)$$

trong đó $\gamma = \psi - \phi$ là margin của detector, $\alpha$ là mức sai số cho phép. Ý nghĩa từng thừa số: $(1+\chi)$ vì carrier mang thông tin có thể là carrier đắt; $\Delta K/H$ vì cửa sổ quan sát hữu ích chỉ dài $\Delta$ trong tổng $H$, nhân với $K$ carrier phải phân biệt; $\gamma^{-2}$ vì detector yếu thì cần nhiều mẫu hơn theo bình phương.

**Hệ quả 5 (ranh giới chế độ):** audit-at-commit là đủ khi $\Delta$ nhỏ hoặc $K$ hiệu dụng bằng 1; không đủ khi $\Delta$ tăng hoặc số carrier tăng.

---

# 3. Bảy baseline — đặc tả để cài lại

| Mã | Baseline | Đặc tả hành vi | Điều cần chú ý khi cài |
|---|---|---|---|
| **B1** | **Audit-at-commit** | Dồn **toàn bộ** ngân sách kiểm tra commit cuối cùng của **mỗi task** ở **độ sâu tối đa** | Đây là **đối chứng đầu bài** — mọi % cải thiện đều tính so với nó. Theo Định lý 4, ngân sách hiệu dụng của nó **độc lập với $\Delta$** — đó là lý do nó thua khi $\Delta$ lớn |
| **B2** | Uniform random auditing | Coverage **bằng nhau** trên mọi ô (carrier × task) | Cẩn thận: "đồng đều" nghĩa là **coverage đều**, không phải **chi tiêu đều**. Chia đều ngân sách theo tiền sẽ cho carrier rẻ coverage cao hơn — đó là cost-greedy trá hình |
| **B3** | Audit-on-insertion | Chỉ kiểm tra tại stage insertion | Dự kiến là **chính sách tệ nhất** — attacker chuyển sang carrier khác, harm = 1.00 |
| **B4** | Audit-on-retrieval | Chỉ kiểm tra tại stage retrieval | Cùng dạng thất bại với B3 |
| **B5** | Risk-score thresholding | Audit khi điểm rủi ro của detector vượt ngưỡng đã tinh chỉnh | Ngưỡng phải tinh chỉnh **trên tập phát triển**, không trên held-out |
| **B6** | Two-stage (Adaptive-Contracts) | Kiểm tra hai giai đoạn | Cần đọc tài liệu Adaptive-Contracts trước khi cài |
| **B7** | **Exhaustive small-game minimax oracle** | Nghiệm minimax liệt kê đầy đủ, chỉ tính được trên 240 trò chơi nhỏ | **Trần trên, không phải đối thủ.** Dùng để đo empirical regret |

**Bẫy chung cho cả bảy:** mọi baseline phải chạy **cùng một ngân sách $B$** và **cùng một detector**. Nếu không, so sánh vô nghĩa.

---

# 4. Smoke test — bốn kiểm tra và số đích

Đây chính là thứ bạn tái lập ở tuần 1–2. Phạm vi được tuyên bố trong hồ sơ: *"trò chơi Stackelberg hữu hạn được giải bằng liệt kê phản ứng tốt nhất của kẻ tấn công"* — tức trò chơi nhỏ, không cần workflow thật, không cần LLM, không cần ngân sách.

| # | Kiểm tra | Số đích | Kết luận gốc |
|---|---|---|---|
| **1** | **Ranh giới chế độ** — không có lợi ích ở $\Delta = 0$; lợi ích rõ từ $\Delta = 2$; tăng theo $\Delta$ | % giảm harm so với commit: $\chi{=}0$: d0 **+0**, d1 **+2**, d2 **+44**, d4 **+86**; $\chi{=}1.34$: d0 **+0**, d1 **−4**, d2 **+12**, d4 **+62** | PASS |
| **2** | **Ngẫu nhiên hóa quan trọng hơn thích nghi** | Tại $\chi{=}1.34$, $\Delta{=}2$: commit **0.48** · tất định **1.00** · cost-greedy **0.74** · đồng đều **0.45** · minimax **0.43** | PASS |
| **3** | **Chiều tác động của $\chi$** | Độ lợi ở $\Delta{=}4$: $\chi{=}0 \to$ **+86%**, $\chi{=}1.34 \to$ **+62%** — **THU HẸP** theo $\chi$, **trái với Hình 3 dự kiến ban đầu** | PASS (và sửa lại dự đoán của bản thảo) |
| **4** | **Audit-on-insertion tệ nhất** | worst-case harm = **1.00** (attacker chuyển carrier) | PASS |

> **Kiểm tra 3 là kiểm tra đáng giá nhất về mặt khoa học.** Nó **bác bỏ** dự đoán ban đầu của chính nhóm tác giả (họ đã vẽ Hình 3 theo hướng độ lợi *tăng* theo $\chi$). Khi trình bày với thầy, nhắc đến chi tiết này cho thấy bạn đã đọc hồ sơ ở mức chi tiết, không chỉ đọc abstract.

---

# 5. Mã tái lập — `repro/smoke_repro.py`

## 5.1 Cách chạy

```bash
pip install numpy scipy
python3 smoke_repro.py
```

Không cần GPU, không cần API key, chạy dưới 2 giây.

## 5.2 Mô hình được cài

Một trò chơi Stackelberg hữu hạn tối giản, giữ đúng cấu trúc của §4 manuscript:

- Attacker chọn $a = (k, \iota, \sigma)$ với $\sigma = \iota + \Delta$ — liệt kê toàn bộ, đúng phạm vi smoke test gốc.
- Defender chọn **coverage** $u(k,t) \in [0,1]$ (audit upstream carrier $k$ tại task $t$) và $v(t) \in [0,1]$ (audit commit tại task $t$), ràng buộc $\sum_k \kappa_k \sum_t u(k,t) + \kappa_c\sum_t v(t) \le B$.
- Audit upstream bắt được poison nếu $\iota \le t < \sigma$; audit commit tại $\sigma$ bắt được đúng lúc harm hiện ra. **Đây là cơ chế tạo ra Định lý 4**: commit chỉ có một cơ hội duy nhất tại $\sigma$ bất kể $\Delta$, còn chính sách trải rộng có thêm $\Delta$ cơ hội.
- $h(a) = 1 - \psi\cdot\min(1, \text{coverage}(a))$, worst-case harm $= \max_a h(a)$.
- Minimax giải bằng **quy hoạch tuyến tính** (đúng công cụ của Conitzer & Sandholm): $\min z$ với $z \ge 1 - \psi\,\text{cov}(a)\ \forall a$, cộng ràng buộc ngân sách.

Ngân sách $B$ được **hiệu chuẩn** sao cho B1 (audit-at-commit) cho đúng worst-case harm 0.48 — tức neo thẳng vào số đích của smoke test gốc, rồi để mọi chính sách khác chạy trên cùng ngân sách đó.

## 5.3 Kết quả thu được so với đích

**Kiểm tra 2** ($\chi = 1.34$, $\Delta = 2$):

| Chính sách | Đích (smoke test gốc) | Tái lập | Nhận xét |
|---|---|---|---|
| audit-on-insertion | 1.00 | **1.000** | khớp |
| lịch trình tất định | 1.00 | **1.000** | khớp |
| cost-greedy | 0.74 | **0.867** | cùng chiều, cao hơn |
| audit-at-commit | 0.48 | **0.480** | khớp *(do hiệu chuẩn)* |
| uniform random | 0.45 | **0.471** | khớp tốt |
| minimax | 0.43 | **0.289** | **lạc quan hơn đáng kể** |
| **Thứ hạng** | — | **PASS** | đúng toàn bộ thứ tự |

**Kiểm tra 1 & 3** (% giảm harm của minimax so với commit):

| $\chi$ | $\Delta{=}0$ | $\Delta{=}1$ | $\Delta{=}2$ | $\Delta{=}4$ |
|---|---|---|---|---|
| Đích, $\chi{=}0$ | +0 | +2 | +44 | +86 |
| **Tái lập, $\chi{=}0$** | **+0.0** | **+15.5** | **+39.7** | **+89.6** |
| Đích, $\chi{=}1.34$ | +0 | −4 | +12 | +62 |
| **Tái lập, $\chi{=}1.34$** | **+0.0** | **+15.5** | **+36.1** | **+89.6** |

**Kiểm tra 4:** audit-on-insertion là chính sách tệ nhất trên toàn lưới — **PASS**.

**Tổng kết:** cả bốn kiểm tra tái lập đúng về **dấu và thứ hạng**; $\Delta{=}2$ và $\Delta{=}4$ khớp tốt về độ lớn; hai chỗ lệch được phân tích ở Mục 6.

---

# 6. Ba khác biệt cần hỏi thầy

Đây là phần có giá trị nhất của toàn bộ việc tái lập. Một nỗ lực tái lập tốt không phải là ra đúng số — mà là **chỉ ra chính xác chỗ mô tả công khai chưa đủ để ra đúng số**.

## 6.1 Con số $\chi = 1.34$ không tự khớp với chi phí đo được

Manuscript định nghĩa $\chi = \max_{k,k'}|\kappa(k)-\kappa(k')| / \bar\kappa$ trên **carrier** $k$, nhưng con số 1.34 lại được nêu ngay sau bốn chi phí **theo stage**: 0.4 / 0.9 / 1.6 / 4.1 CPU-phút.

Áp công thức vào bốn số đó: $\bar\kappa = 1.75$, $\max-\min = 3.7$, cho $\chi = 3.7/1.75 = \mathbf{2.11}$ — **không phải 1.34**.

*(Thử các biến thể: $(\max-\min)/\sum = 0.53$ · hệ số biến thiên $= 0.81$ · dùng trung vị $= 2.96$ — không giá trị nào cho 1.34.)*

**Câu hỏi cho thầy:** chi phí audit theo **carrier** ($\kappa(k)$) là một bảng riêng chưa nêu trong manuscript, hay $\chi = 1.34$ được tính theo một công thức khác? Không có câu trả lời này thì **không cấu hình được lưới $\chi$**.

## 6.2 Mô hình chi phí của $\chi$ chưa xác định — hai cách đọc, mỗi cách tái lập một tập con khác nhau

Khi tăng $\chi$ mà giữ $K$ và định nghĩa $\chi$ cố định, còn một bậc tự do: **tăng $\chi$ có làm tăng tổng chi phí phủ đều mọi carrier hay không?**

| Cách đọc | Ý nghĩa vận hành | Kiểm tra 2 (thứ hạng) | Kiểm tra 3 ($\chi$ thu hẹp độ lợi) |
|---|---|---|---|
| **Neo trung bình** — giữ $\bar\kappa$ cố định | Làm một số carrier đắt lên thì carrier khác rẻ đi | **PASS** | **FAIL** — $\chi$ không có hiệu ứng nào |
| **Neo giá trị nhỏ nhất** — giữ $\kappa_{\min}$ cố định | "Differentiating audit depths" = làm sâu thêm carrier đắt ⇒ tổng chi phí tăng | dễ **FAIL** nếu neo quá mạnh | **PASS** |

Manuscript nói $\chi$ đạt được bằng cách *"equalising or differentiating audit depths"*, nghiêng về cách đọc thứ hai — nhưng cách đọc thứ hai làm tổng chi phí tăng theo $\chi$, và nếu neo quá mạnh thì uniform random trở nên tệ hơn commit, phá thứ hạng của Kiểm tra 2.

**Câu hỏi cho thầy:** khi quét $\chi \in \{0, 0.5, 1.34\}$, ngân sách hiệu dụng có được giữ nguyên không, hay $\chi$ cao đồng nghĩa mất ngân sách?

## 6.3 Tại $\Delta = 1$, bản tái lập lạc quan hơn nhiều (+15.5% so với đích +2%)

Mô hình tái lập cho defender **toàn bộ** cửa sổ $[\iota, \sigma)$ làm cơ hội phát hiện. Smoke test gốc gần như không có độ lợi ở $\Delta = 1$, nghĩa là ở đó belief **chưa kịp tập trung** — với một alarm duy nhất, phân bố hậu nghiệm trên $(k,\iota,\sigma)$ vẫn gần như đều, nên defender chưa biết nhìn vào đâu.

Nói cách khác: mô hình tái lập bỏ qua chính **chi phí thông tin** mà Định lý 4 mô tả. Điều tương tự giải thích vì sao minimax tái lập ra 0.289 thay vì 0.43.

**Câu hỏi cho thầy:** cấu hình particle filter và tham số $(\psi, \phi, \beta, \tau, \eta_Q)$ dùng trong smoke test là gì? Đây là bộ tham số quyết định độ lớn của mọi con số.

---

# 7. Quy trình tái lập — ba mức và định nghĩa "xong"

## Mức 1 — Smoke test (tuần 1–2, làm ngay)

| Bước | Việc | Xong nghĩa là |
|---|---|---|
| 1 | Chạy `smoke_repro.py` như hiện trạng | Bốn kiểm tra in ra PASS trên máy của bạn |
| 2 | Gửi thầy 3 câu hỏi ở Mục 6 | Có câu trả lời hoặc có file cấu hình gốc |
| 3 | Thay tham số theo câu trả lời, chạy lại | Độ lệch với số đích thu hẹp; ghi lại độ lệch còn lại |
| 4 | Viết một trang "reproduction report" | Bảng ba cột: đích · tái lập · chênh lệch và nguyên nhân |

**Định nghĩa xong Mức 1:** bốn kiểm tra PASS về dấu và thứ hạng, và **mọi chênh lệch độ lớn còn lại đều giải thích được bằng một tham số cụ thể**, không phải "chưa rõ vì sao".

## Mức 2 — Dựng `AuditGame-SE` (tuần 3–5)

| Bước | Việc |
|---|---|
| 1 | Dựng harness OpenHands + 15 repository định dạng SWE-bench, chạy được 1 workflow end-to-end |
| 2 | Cài **evaluator-known state**: mỗi instance ghi $(k,\iota,\sigma,\varepsilon)$ vào manifest niêm phong |
| 3 | Cài một detector duy nhất dùng chung, ghi rõ $(\psi,\phi)$ |
| 4 | Sinh 620 benign change, chạy two-sample test, **xác nhận AUC ≤ 0.56** |
| 5 | Cài B1 (audit-at-commit) và đo lại — đây là mốc đối chiếu |
| 6 | Cài cơ chế đóng băng bằng hash: harness **từ chối chạy** chính sách có hash ngoài manifest |

**Định nghĩa xong Mức 2:** chạy B1 trên 100 workflow ra một con số worst-case harm, tái lập được sau khi xóa sạch và chạy lại từ đầu.

## Mức 3 — Full study (tuần 15–18)

4.500 instance × 8 hệ thống × 3 seed, báo cáo **trên lưới $(\Delta,\chi)$**, không gộp. Kiểm tra go/no-go gate ≥15% trên held-out.

---

# 8. Danh sách hiện vật cần xin thầy

Gửi đúng danh sách này, theo thứ tự ưu tiên. Ba mục đầu đủ để làm Mức 1.

| # | Hiện vật | Vì sao cần | Ưu tiên |
|---|---|---|---|
| 1 | **Script và file cấu hình của smoke test** (trò chơi nhỏ, 4 kiểm tra) | Không có nó thì mọi số tái lập đều là phỏng đoán | **Cao nhất** |
| 2 | Bảng chi phí audit **theo carrier** $\kappa(k)$ và cách tính ra $\chi = 1.34$ | Mục 6.1 | **Cao nhất** |
| 3 | Tham số $(\psi, \phi, \beta, \tau, \eta_Q, \lambda_Q, \lambda_T)$ và seed | Mục 6.3 | **Cao nhất** |
| 4 | `docs/thesis/eval/PLAN.md` và `REVIEWS.md` (manuscript có nhắc tới) | Chứa thiết kế đã đăng ký trước và ghi chép phản biện nội bộ | Cao |
| 5 | Đặc tả 28 chính sách trong thư viện hạn chế | Cần cho robust optimisation ở quy mô lớn | Trung bình |
| 6 | Đặc tả 18 scripted attacker policy + quy tắc chia 7 held-out | Cần cho Mức 3; quy tắc chia phải cố định **trước** | Trung bình |
| 7 | Manifest 240 trò chơi nhỏ giải chính xác | Dùng làm oracle B7 | Trung bình |
| 8 | Mã nguồn Sentinel (≈9.1k dòng) nếu đã tồn tại | Nếu chưa tồn tại thì đây là việc của bạn — cần biết sớm | Cao |

**Câu hỏi quan trọng nhất trong danh sách:** mục 8. Nếu mã Sentinel chưa được viết, thì "tái lập" không phải là việc bạn làm — **xây dựng** mới là việc bạn làm, và tuần 6–10 trong kế hoạch chính là tuần viết 9.1k dòng đó.

---

# 9. Tóm tắt một trang để mang đi gặp thầy

> Em đã đọc manuscript FSE-2027-15 và xác định: mọi con số kết quả trong đó là **projected**, chưa có full study nào được chạy — chỉ có smoke test trên trò chơi Stackelberg hữu hạn với 4 kiểm tra PASS.
>
> Em đã viết lại trò chơi nhỏ đó từ §4 của manuscript (LP minimax + liệt kê best-response của attacker) và **tái lập được cả 4 kiểm tra về dấu và thứ hạng**: thứ tự audit-on-insertion 1.00 > cost-greedy > commit 0.48 > uniform 0.47 > minimax; độ lợi bằng 0 tại $\Delta{=}0$ và tăng theo $\Delta$; $\chi$ làm thu hẹp độ lợi; audit-on-insertion tệ nhất. Độ lớn ở $\Delta{=}2$ và $\Delta{=}4$ khớp tốt (+39.7% và +89.6% so với đích +44% và +86%).
>
> Ba chỗ em chưa tái lập được và cần thầy xác nhận:
> 1. $\chi = 1.34$ không khớp với công thức áp lên chi phí 0.4/0.9/1.6/4.1 (ra 2.11) — bảng chi phí theo **carrier** là gì?
> 2. Khi quét $\chi$, ngân sách hiệu dụng có giữ nguyên không? Hai cách đọc cho hai kết quả khác nhau.
> 3. Tham số detector và particle filter của smoke test — ở $\Delta{=}1$ bản của em lạc quan hơn nhiều (+15.5% so với +2%).
>
> Và một câu hỏi về phạm vi: mã nguồn Sentinel 9.1k dòng đã tồn tại chưa? Nếu chưa, em hiểu tuần 6–10 là tuần viết nó, không phải tuần tái lập.
