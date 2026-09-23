# Parameter Measurement Runbook — Sentinel / AuditGame-SE

**Đề tài:** FSE-2027-15 · **Học viên:** Nguyễn Hữu Trưởng · **GVHD:** TS. Lê Xuân Bách
**Ngày:** 23/09/2026 · **Phạm vi:** W1, W2, W3, W4, W5, W6 của [plan W1–W10](design/plans/2026-09-22-W1-W10-tham-so.md)

> **Tài liệu này dùng để làm gì.** Mỗi mục là một tham số: nó nghĩa là gì, đo bằng cách nào, **lệnh chạy từng bước**, kết quả thu được, và điều gì trong kết quả đó cần được nói ra khi bảo vệ. Ai cầm repo cũng chạy lại được toàn bộ.
>
> **Bản có biểu đồ:** `docs/AuditGame-SE_Parameter_Measurement_Charts.html` — cùng số liệu, bảy biểu đồ, mở bằng trình duyệt.
>
> **Quy ước chung.** Mọi lệnh chạy **từ trong thư mục `auditgame/`**, vì các module import phẳng (`import core`). Lõi đo chỉ dùng thư viện chuẩn. Mọi file kết quả đều mang khối `provenance` ghi seed, số lần lặp, ngày và commit SHA.

---

## Bảng tổng hợp kết quả đợt này

| Tham số | Phương thức | Kết quả | Trạng thái |
|---|---|---|---|
| $\kappa$ theo CPU-time | M1 — đo | **$\chi = 1{,}295$** sau khi bốn checkpoint làm việc thật (bản đầu: 0,16) | ✅ Đã thành thang vận hành; commit vẫn thiếu differential testing |
| $\pi_0$ | M3 — suy dẫn | $\pi_0^{\text{thế giới}} = 1/12{,}51 = 0{,}0799$; $\pi_0^{\text{mô hình}} = 0{,}0400$ | ✅ Đã suy dẫn và nối một nguồn |
| $\eta_Q$ | M1 + M3 | Cách ly đắt **gấp 61,5 lần** audit cùng carrier | ✅ Đo được |
| $\beta_k$ | M1 → **M2** | memory 0,31 · skill 0,06 hoặc 0,61 tuỳ luật · branch 1,0 | ⚠️ **Không định danh được** → phải quét |
| $c$ (Định lý 4) | M1 | **Từ chối trả số** | 🔴 Tiền đề không thoả: ngân sách không mua được thông tin |
| $\Delta$ thực trên SWE-bench | M1 | Trung vị **0 task** ở 8/10 repo; django **4,5**; theo commit: 14–194 | ✅ Đo được, và nó đổi cách đọc ranh giới vùng |

**Hai phát hiện quan trọng hơn cả năm con số trên** nằm ở mục 1.5 và 5.4.

---

## 1. $\kappa$ — chi phí audit, đo bằng CPU-time (W4)

### 1.1 Tham số này là gì

$\kappa(k)$ là chi phí một lần audit carrier $k$. Nó là một trong hai đại lượng sinh ra trục $\chi$ của ranh giới vùng, nên nếu $\kappa$ gán tay thì $\chi$ vô nghĩa, và toàn bộ luận điểm "carrier phân hoá chi phí đẩy crossover ra sau" mất gốc.

### 1.2 Vì sao phải là CPU-time, không phải wall-clock

Wall-clock đếm cả khoảng thời gian tiến trình bị hệ điều hành cho ra rìa. Cùng một phép audit chạy trên hai máy bận khác nhau sẽ cho hai $\kappa$ khác nhau, và bảng chi phí hết tái lập — đúng cái tính chất duy nhất mà Stage 2 cần ở nó.

Điều này được **cưỡng chế bằng test**, không phải bằng lời hứa: một detector giả ngủ 50 ms mỗi item được đưa vào đúng hàm bấm giờ; nếu đồng hồ là wall-clock thì 4 item cho 0,2 s và test đỏ.

```python
# tests/gate1_integrity/test_cost_provenance.py
secs = runner._probe_seconds(_SleepingDetector(), items, t=0, seed=1)
self.assertLess(secs, 0.05)
```

Kèm một test đối chứng: một detector làm việc thật phải hiện ra thời gian dương. Không có nó thì `return 0.0` cũng làm test đầu xanh.

### 1.3 Chạy từng bước

```bash
cd auditgame

# 1. Test phải đỏ trước khi sửa (đồng hồ đang là perf_counter)
python3 -m unittest tests.gate1_integrity.test_cost_provenance -v

# 2. Sau khi ba chỗ bấm giờ trong runner.py đổi sang time.process_time: phải xanh
python3 -m unittest tests.gate1_integrity.test_cost_provenance.TheAuditClockCountsWorkNotWaiting -v

# 3. Đo, ghi kết quả kèm provenance
python3 tools/measure_kappa.py --reps 30 > spikes/kappa-cpu.json

# 4. Đọc bảng
python3 -c "
import json; d=json.load(open('spikes/kappa-cpu.json'))
print(d['kappa_cpu_seconds']); print('chi =', round(d['chi'],4))"
```

### 1.4 Cách đo hoạt động thế nào

Không dựng bàn đo riêng. `tools/measure_kappa.py` chạy **episode thật** với `record_traces=True`, rồi gộp `TaskTrace.audit_seconds` theo khoá `"stage:carrier"`. Lý do: một bàn đo riêng sẽ chấm những item khác, với số lượng khác, nên bảng $\kappa$ thu được nói về bàn đo chứ không nói về benchmark.

Kết quả (30 episode, $H = 8$, detector `mid`, chính sách B2):

| Giai đoạn | CPU-time trung vị (giây) | Số mẫu |
|---|---|---|
| insertion | 0,000006 | 644 |
| retrieval | 0,000007 | 281 |
| delegation | 0,000006 | 68 |
| commit | 0,000013 | 238 |

| Carrier | CPU-time trung vị | Số item mỗi lần audit |
|---|---|---|
| memory | 0,000007 | 4,86 |
| skill | 0,000006 | 0,85 |
| queue | 0,000006 | 1,71 |
| branch | 0,000006 | 4,23 |

$$\chi_{\text{CPU}} = 0{,}16$$

### 1.5 Bốn checkpoint được hiện thực, và κ đo lại (23/09, đợt 2)

Bản đầu của mục này báo $\chi_{\text{CPU}} = 0{,}16$ và ghi rằng con số đó đo **bộ mô phỏng** chứ không đo audit, vì bốn checkpoint chưa làm việc thật. Đợt 2 đã hiện thực chúng trong `checkpoints.py`, mỗi phép kiểm soi đúng thứ mà tên nó nói:

| Giai đoạn | Việc thật sự làm |
|---|---|
| insertion | Băm lại `item_id` từ nội dung (phát hiện bản ghi bị viết đè dưới id cũ); kiểm dạng `provenance`; đối chiếu token topic với nội dung |
| retrieval | Tính lại độ khớp giữa bản ghi và yêu cầu đã kéo nó ra, từ chính nội dung chứ không tin trường `topic` đã lưu |
| delegation | Đi ngược chuỗi `derived_from` trong kho: tổ tiên còn tồn tại không, có còn băm đúng không, có chung token không |
| commit | Đi ngược **toàn bộ** chuỗi dẫn xuất bắc cầu qua các carrier của bản ghi mà commit mang theo, băm lại từng tổ tiên |

Hai bất biến giữ nguyên: không phép kiểm nào đọc `Item.poisoned`, và không phép kiểm nào có tác dụng phụ.

**κ đo lại, sau khi các checkpoint làm việc thật:**

| Carrier | κ (giây CPU, một lượt audit carrier) | Item mỗi lượt |
|---|---|---|
| memory | 1,45 × 10⁻⁵ | 4,86 |
| branch | 1,07 × 10⁻⁵ | 4,23 |
| queue | 4,78 × 10⁻⁶ | 1,71 |
| skill | 3,64 × 10⁻⁶ | 0,85 |

$$\chi_{\text{CPU}} = 1{,}295$$

Theo giai đoạn: commit 12 µs · delegation 3 µs · insertion 2 µs · retrieval 1 µs — đúng thứ tự định tính mà draft khẳng định.

**Về độ phân giải:** một lượt audit tốn cỡ đúng một tick của `process_time`, nên đo một phát thì mọi carrier đọc như nhau ($\chi = 0{,}0$). Các số trên đo bằng cách lặp 200 lượt giống hệt rồi chia.

**Ba giá trị χ giờ nói gì:** 2,114 là bảng của draft (chi phí theo *giai đoạn*, bị dùng như bảng theo carrier), 1,349 là bảng USD, **1,295 là bảng CPU-time**. Hai bảng sau gần nhau vì cả hai đều bị chi phối bởi số item mỗi lượt audit.

### 1.6 Bốn thang giá, cùng một lưới — và đơn vị quyết định ai thắng

Câu hỏi "nếu $\kappa$ là USD thì kết quả ra sao" được trả lời bằng một công cụ
chạy lại được, `tools/compare_cost_scales.py`, chứ không bằng một lần chạy tay:

```bash
cd auditgame
python3 tools/compare_cost_scales.py --n 20 --seeds 2 --sweep-commit \
    > spikes/cost-scale-comparison.json
```

**Ngân sách phải cùng một luật cho mọi thang.** `costs.budget_for_table(kappa, H)`
cho mỗi thang đúng **32,1%** của hoá đơn audit đầy đủ — đúng tỉ lệ mà 17,95 của
bảng cũ từng mua. Trước đợt này `budget_for_cpu` nhân tỉ lệ đó với
$(\sum_k \kappa_k + \kappa_{\text{commit}})$ còn `budget_for` chỉ nhân với
$\sum_k \kappa_k$, nên thang CPU âm thầm chạy với ngân sách giàu hơn 1,36 lần
thang USD mà nó đang được đem ra so. Hai hàm nay gọi chung một hàm.

| Chính sách | $L$ draft | $L$ **USD** | $L$ CPU |
|---|---|---|---|
| B1 audit-at-commit | 0,988 | 1,000 | **0,512** |
| B5 risk-score | 0,955 | 0,955 | 0,955 |
| B6 two-stage | 1,058 | 1,008 | 1,008 |
| Sentinel | 1,012 | 0,970 | 0,973 |
| SentinelW window-belief | 0,993 | **0,855** | 0,902 |
| SSG-G guarded | **0,925** | 0,988 | 0,762 |
| B7 minimax-lp | 1,038 | 1,038 | 0,625 |
| NC1 quarantine-everything | 1,400 | 1,000 | 1,000 |

*(20 workflow, $H = 8$, $\Delta = 2$, detector mid, seed 1–2; $\eta_Q$ đo được.)*

**Thứ hạng đổi hẳn theo đơn vị** — điều mà bản ghi trước đây nói là "không đổi",
và đó là do lần chạy tay kia dùng ngân sách không cùng luật:

- **USD:** SentinelW → B5 → Sentinel → SSG-G → B1 → NC1 → B6 → B7
- **CPU:** B1 → B7 → SSG-G → SentinelW → B5 → Sentinel → NC1 → B6

**Trả lời trực tiếp câu hỏi.** Trên thang USD, hướng của kết luận chính (RQ1)
**đúng như draft mong đợi**:

| So với B1 | harm | $L$ |
|---|---|---|
| Sentinel | **+15,0%** | +3,0% |
| SentinelW window-belief | **+25,0%** | **+14,5%** |
| SSG-G guarded | +10,0% | +1,2% |

Trên thang CPU thì **ngược dấu toàn bộ**: Sentinel −126,7%, SentinelW −80,0%,
SSG-G −46,7% theo harm. Cùng một mã, cùng một lưới, cùng một tỉ lệ ngân sách.

### 1.7 Toàn bộ khác biệt giữa hai thang nằm ở **một** con số

Hai thang chỉ khác nhau ở giá của một lượt audit tại commit, tính theo bội số của
$\bar\kappa$:

| Thang | $\kappa_{\text{commit}} / \bar\kappa$ | Lượt commit mua được mỗi episode ($H = 8$) |
|---|---|---|
| draft | 2,34 | 4,38 |
| **USD** | **4,00** (định nghĩa: chấm cả bốn carrier) | 2,56 |
| **CPU** | **1,43** (đo, *thiếu* differential testing) | 7,19 |

Quét $\kappa_{\text{commit}}$ như bội số của $\bar\kappa$, giữ nguyên bảng carrier
và ngân sách, cho **hai thang kết quả trùng khít nhau** — bằng chứng rằng mọi
khác biệt còn lại chỉ là bậc hai:

| $m = \kappa_{\text{commit}}/\bar\kappa$ | lượt/episode | harm B1 | harm Sentinel | thắng |
|---|---|---|---|---|
| 1,00 | 10,26 | 0,375 | 0,850 | B1 |
| **1,43** ← đo được | 7,17 | 0,375 | 0,850 | B1 |
| 2,00 | 5,13 | 0,875 | 0,850 | Sentinel |
| 3,00 | 3,42 | 0,975 | 0,850 | Sentinel |
| **4,00** ← USD | 2,56 | 1,000 | 0,850 | Sentinel |
| ≥ 6 | ≤ 1,71 | 1,000 | 0,850 | Sentinel |

**Ngưỡng lật nằm giữa 5,13 và 7,17 lượt commit mỗi episode 8 task.** Khi B1 còn
mua được audit ở gần như mọi commit thì nó thắng đậm; khi không, nó về đáy bảng.

**Vì sao điều này là vấn đề, chứ không phải một kết quả.** Không thang nào trong
hai thang đo được $\kappa_{\text{commit}}$ thật:

- Thang **USD** *định nghĩa* nó bằng "chấm cả bốn carrier" — một giả định mô hình.
- Thang **CPU** *đo* nó, nhưng thiếu differential testing (đòi image Docker từng
  instance), nên $1{,}43\bar\kappa$ là **cận dưới**.

Giá trị thật nằm **trên cả hai**, và ngưỡng lật lại nằm **giữa** chúng. Nói cách
khác: kết luận chính của luận văn hiện do một đại lượng chưa đo quyết định, và
biết dấu của nó chỉ cần đo đúng một thứ — chi phí thật của một lượt audit tại
commit có chạy test. **Đây là phép đo có giá trị cao nhất còn lại.**

### 1.7b `Sentinel` không có kênh commit — nên so sánh RQ1 là so hai kênh rời nhau

`policies.Sentinel` khai `ACTIONS = frozenset(CARRIERS)`: nó audit bốn carrier và
không làm gì khác. Kiểm chứng bằng cách đếm hành động trên 80 quyết định, với
$\kappa_{\text{commit}}$ hạ xuống **rẻ hơn cả carrier rẻ nhất**: vẫn **0 lần**
chọn commit. Vì vậy $L$ của nó phẳng tuyệt đối trên toàn bộ dải quét ở §1.7 —
đó là tính chất của không gian hành động, không phải lỗi.

Hệ quả: "Sentinel so với B1" hiện là **một chính sách chỉ audit carrier so với
một chính sách chỉ audit tại commit**, và thang giá quyết định kênh nào rẻ. Hai
chính sách có **cả hai** kênh là `SentinelW window-belief` và `SSG-G guarded`;
bảng ở §1.6 đã thêm chúng, và chúng mới là nơi câu hỏi "đơn vị nào" nói về
*phân bổ* chứ không nói về *với tới được hay không*.

### 1.7c Cách ly: giá đo được làm nó không mua nổi — và điều đó **cải thiện** SentinelW

Với $\eta_Q$ **đo được** ($61{,}5 \times \kappa$), một lượt cách ly tốn **6,0 lần**
toàn bộ ngân sách episode, trên **cả hai** thang. NC1 "cách ly tất cả" vì vậy
không hành động lần nào: chi 0%, $Q_{\text{false}} = 0$, harm 1,000 — *bị vô hiệu
hoá, không phải được so sánh*.

`costs.py` đang giữ **hai** giá cho cùng một đại lượng, lệch nhau 54 lần:
`ETA_Q_USD` (chở tỉ lệ của bảng placeholder sang, $1{,}14\bar\kappa$) và
`eta_q(k)` (đo được, $61{,}5\bar\kappa$). `costs.install()` vẫn cài cái thứ nhất,
nên **mọi bảng USD công bố trước hôm nay chạy trên giá cách ly placeholder** — kể
cả `spikes/ssg-sweep-usd.json`. Cột `usd-legacy-etaQ` trong JSON giữ lại đúng
cấu hình đó làm tang chứng.

Giá đúng **không** làm hỏng kết quả — nó làm tốt lên:

| SentinelW trên thang USD | $L$ | harm | $Q_{\text{false}}$ |
|---|---|---|---|
| $\eta_Q$ placeholder (rẻ) | 1,095 | 0,825 | 2,70 |
| $\eta_Q$ **đo được** (đắt) | **0,855** | **0,750** | **0,93** |

Cách ly đắt buộc SentinelW thôi cách ly bừa, và cả harm lẫn $L$ đều giảm. Đây là
lập luận mạnh cho việc đo $\eta_Q$ tử tế chứ không đặt tay.

**Ba lối ra cho NC1, phải chọn một trước khi đóng băng:** nâng ngân sách để cách
ly nằm trong tầm với và nói rõ ngân sách đó tương ứng bao nhiêu phần hoá đơn; giữ
ngân sách và báo cáo rằng dưới giá đo được thì cách ly không phải một nước đi;
hoặc đo lại $\eta_Q$ trên agent thật thay vì suy từ tỉ lệ USD.

### 1.7d Kết luận: đơn vị của $\kappa$ là **tự do** — chỉ bốn tỉ số sống sót

Mọi chỗ dùng chi phí trong mã đều hoặc là **tỉ số với một chi phí khác**
(`belief[c] / KAPPA[c]`), hoặc là **so với ngân sách** (`can()`). Nên nhân cả
$(\kappa, \kappa_{\text{commit}}, \eta_Q, B)$ với cùng một hệ số thì trò chơi
không đổi. Kiểm chứng: nhân bảng USD với $10^{3}, 10^{6}, 10^{-6}$ — $L$ của cả
tám chính sách **giống hệt**. (Dưới $10^{-9}$ thì dung sai của bộ giải LP mới cắn;
ngoài tầm mọi thang thực tế.)

> **Một lỗi phải sửa để điều trên đúng.** `Policy.can()` dùng biên độ **tuyệt
> đối** `1e-9` — một đại lượng *cùng đơn vị với* $\kappa$, nên nó mang nghĩa khác
> nhau trên mỗi bảng giá. Ở hệ số $10^{-6}$ nó phình thành 6% ngân sách và làm
> $L$ của SentinelW nhảy 0,855 → 0,8625. Đã đổi sang biên độ **tương đối**;
> **0 ô** trong bảng kết quả dịch, ba cổng không đổi.

Vậy câu hỏi đúng không phải "đơn vị nào" mà là **"bốn tỉ số này đo được trong đơn
vị nào"**:

| Tỉ số | Trạng thái | Đo được trong đơn vị nào |
|---|---|---|
| Hình dạng vector carrier ($\chi$) | ✅ **Xong** | Cả hai: USD 1,349, CPU 1,295 — hai phép đo độc lập **đồng ý** |
| $\eta_Q / \bar\kappa = 61{,}5$ | ✅ Xong | **Chỉ USD.** Nửa phục hồi là *agent ghi lại item* = token; CPU-time không định giá được — nửa gỡ đo ra $\le 0$ vì che một carrier thì *bớt* việc |
| $\kappa_{\text{commit}} / \bar\kappa$ | ❌ **Chưa đo, trong bất kỳ đơn vị nào** | USD *giả định* 4,00; CPU *đo* 1,43 nhưng thiếu differential testing |
| $B / (H \sum_k \kappa_k)$ | 🟡 Thừa kế | Quyết định thiết kế (M3), hiện 32,1% kế thừa từ 17,95 — phải khai, không phải đo |

**Khuyến nghị: lấy USD làm thang vận hành.**

1. Đó là đơn vị duy nhất **mọi thành phần cùng sống trên một thang** — đặc biệt
   $\eta_Q$, thứ chỉ tồn tại ở đó.
2. Đơn giá có thật và đã đóng băng: 1200 lượt chấm hết 0,594 USD
   (`payloads/judge-cache.json`), giá token `deepseek-v4.1-flash` chốt 15/09.
3. Người đọc diễn giải được một ngân sách bằng đô la; không ai diễn giải được
   $8{,}6 \times 10^{-5}$ giây CPU.

**CPU-time giữ lại làm đối chứng cho $\chi$, không làm thang vận hành.** Giá trị
của nó nằm ở chỗ nó xác nhận *hình dạng* bằng một phép đo hoàn toàn độc lập —
1,295 so với 1,349. Nhưng thứ nó bấm giờ là mấy phép kiểm toàn vẹn Python của
chính harness này, chứ không phải audit mà phương pháp luận mô tả: một lượt
insertion audit thật là một LLM đọc nội dung, và cái đó tính bằng USD.

**Bảng draft rút khỏi đường chính.** $\chi = 2{,}114$ của nó là chi phí theo
*giai đoạn* bị dùng như bảng theo *carrier*, và chính nó mâu thuẫn với con số
1,34 mà draft tự công bố.

**Còn $\kappa_{\text{commit}}$ thì báo cáo theo lưới, không báo một số.** Nó quyết
định dấu của RQ1 và chưa ai đo, nên đúng theo quy tắc của chính dự án —
*"REPORT ON THE GRID, DO NOT POOL"* (`experiment.py`) — bảng kết quả phải quét
$\kappa_{\text{commit}}/\bar\kappa$ và khai rõ 4,00 là **giả định**, 1,43 là
**cận dưới**, ngưỡng lật nằm **giữa** hai con số đó.

### 1.8 ⚠️ Ghi chú cũ giữ lại làm hồ sơ

Bốn checkpoint của Stage 2 (kiểm nội dung + nguồn gốc, kiểm nhất quán, kiểm hợp đồng, review patch + **differential testing**) **chưa được hiện thực như audit thật**. Cái đang được bấm giờ là phép chấm điểm mô phỏng — một lần lấy mẫu Gauss cho mỗi item. Vì vậy:

- $\chi_{\text{CPU}} = 0{,}16$ **không** phải là $\chi$ của bài toán; nó nói rằng chấm một item ở carrier nào cũng tốn như nhau trong bộ mô phỏng.
- Ba giá trị $\chi$ hiện có nói ba chuyện khác nhau: **2,114** (bảng của draft, theo *giai đoạn* audit), **1,349** (bảng đo theo đơn giá chấm LLM, theo *số item* mỗi carrier), **0,16** (CPU-time của bộ mô phỏng).
- Muốn có $\kappa$ đúng nghĩa Stage 2 thì phải hiện thực bốn checkpoint làm việc thật — đặc biệt commit audit phải chạy test suite của repo. Đó là việc lớn hơn một phép đo.

**Khuyến nghị:** dùng bảng theo đơn giá chấm LLM ($\chi = 1{,}349$) làm bảng vận hành, báo cáo $\chi_{\text{CPU}}$ như một phép đối chứng cho thấy chi phí *mô phỏng* là đồng nhất, và khai rõ rằng $\kappa$ theo CPU-minute của draft chưa tái lập được vì bốn checkpoint chưa làm việc thật.

---

## 2. $\pi_0$ — tiên nghiệm mỗi item, suy dẫn (W1)

### 2.1 Tham số này là gì và vì sao nó quan trọng nhất

$\pi_0$ là xác suất một item sống bất kỳ là payload, trước khi thấy bằng chứng nào. Nó có **fan-out lớn nhất** trong toàn hệ: posterior của mọi carrier đi qua nó, bảng $\tau_{\text{sel}}$ được **sinh ra từ** nó, và tỉ số bằng chứng của belief định nghĩa **đối với** nó.

Trước đợt này nó là `PI0 = 0.10`, kèm chú thích tự khai trong mã: *"a MODEL CONSTANT, NOT derived from the dataset"*.

### 2.2 Cách suy dẫn

$\pi_0$ **không phải** thuộc tính của thế giới mà là hệ quả của cách dựng episode: mỗi episode gieo **đúng một** payload giữa $\mathbb{E}[n_{\text{total}}]$ item sống tại thời điểm quyết định.

$$\pi_0^{\text{thế giới}} = \frac{1}{\mathbb{E}[n_{\text{total}}]} = \frac{1}{12{,}51} = 0{,}0799$$

$\mathbb{E}[n_{\text{total}}] = 5{,}34 + 1{,}12 + 1{,}55 + 4{,}50$ đã có sẵn trong `costs.ITEMS_PER_AUDIT`, đo trên 20 episode có ghi vết.

**Hai vai, hai số** (quy tắc R2). Defender không biết chắc episode này có bị tấn công hay không; belief khởi đầu đặt xác suất đó là $\pi_{\text{attack}} = 0{,}5$. Nên:

$$\pi_0^{\text{mô hình}} = \pi_{\text{attack}} \times \pi_0^{\text{thế giới}} = 0{,}0400$$

Dùng chung một số cho cả hai vai là lặng lẽ cho defender biết chắc rằng có tấn công.

### 2.3 Một nguồn duy nhất, cưỡng chế bằng test

`scoring.py` và `reference/gen_score_table.py` giờ đều `import costs` rồi đọc `costs.PI0_WORLD`, thay vì mỗi nơi tự khai một hằng số. Có ba test giữ điều này, trong đó test quan trọng nhất so $\pi_0$ trong bảng đã đóng băng với $\pi_0$ đang hiệu lực:

```python
def test_the_frozen_table_was_generated_at_the_pi0_in_force(self):
    table = json.loads(path.read_text(encoding="utf-8"))
    self.assertAlmostEqual(table["provenance"]["pi0"], scoring.PI0, places=6)
```

Test này **đang đỏ cho tới khi bảng được sinh lại** — và đó chính là việc của nó: nó phát hiện đúng tình huống "ngưỡng chọn carrier đang đọc từ một bảng sinh ở tiên nghiệm khác".

### 2.4 Chạy từng bước

```bash
cd auditgame

# 1. Lưu bảng cũ để so sánh
cp reference/score_table.json /tmp/score_table_pi0_010.json

# 2. Sinh lại — khoảng 23 phút, 800.000 mẫu mỗi ô
python3 reference/gen_score_table.py --force

# 3. Xem ngưỡng dịch bao nhiêu
python3 - <<'EOF'
import json
old = json.load(open('/tmp/score_table_pi0_010.json'))
new = json.load(open('reference/score_table.json'))
for s in ("weak", "mid", "strong"):
    o = old["tables"][s]["rows"][5]["tau_sel"]["4"]
    n = new["tables"][s]["rows"][5]["tau_sel"]["4"]
    print(f"{s}: tau_sel(n=5,K=4) {o:.4f} -> {n:.4f}")
EOF

# 4. Chạy toàn bộ test và xử lý từng test đỏ theo đúng một quy tắc:
#    test khẳng định TÍNH CHẤT  -> tính chất phải vẫn đúng, không sửa test
#    test khoá cứng GIÁ TRỊ cũ  -> cập nhật giá trị, ghi lý do trong commit
python3 tests/run_all.py --all 2>&1 | tail -20
```

### 2.5 Kết quả: bảng $\tau_{\text{sel}}$ sau khi sinh lại

Sinh lại mất 23 phút, 800.000 mẫu mỗi ô, ngày đo 23/09. Ngưỡng chọn carrier giảm đều:

| Mức detector | $n$ | $\tau_{\text{sel}}$ cũ ($\pi_0 = 0{,}10$) | mới ($\pi_0 = 0{,}0799$) | Đổi |
|---|---|---|---|---|
| weak | 5 | 0,3673 | 0,3122 | −0,055 |
| weak | 20 | 0,2586 | 0,2143 | −0,044 |
| mid | 5 | 0,5044 | 0,4432 | −0,061 |
| mid | 20 | 0,4117 | 0,3537 | −0,058 |
| strong | 5 | 0,5368 | 0,4754 | −0,061 |
| strong | 20 | 0,5081 | 0,4468 | −0,061 |

**Tính chất vẫn giữ** — đây mới là điều phải kiểm, không phải giá trị. Hướng phụ thuộc theo $n$ đảo chiều giữa hai mức detector, và điều đó đúng ở cả $K = 1$ lẫn $K = 4$:

| | $n = 1 \to 8$ (cũ) | $n = 1 \to 8$ (mới) |
|---|---|---|
| weak, $K=1$ | 0,299 → 0,222 (giảm) | 0,250 → 0,182 (giảm) |
| strong, $K=1$ | 0,153 → 0,237 (tăng) | 0,124 → 0,196 (tăng) |

Vì vậy, theo quy tắc xử lý test đỏ: test nào khẳng định *tính chất* thì phải vẫn xanh; chỉ test khoá cứng *giá trị* mới được cập nhật, kèm lý do.

### 2.6 π₀ có làm đổi thứ hạng chính sách không

Chạy cùng lưới ($\Delta = 2$, detector `mid`, 20 workflow, 2 seed) trên hai bảng:

| Chính sách | $L$ với bảng mới | $L$ với bảng cũ |
|---|---|---|
| B1 audit-at-commit | 0,800 | 0,800 |
| Sentinel | 0,873 | 0,873 |
| B5 risk-score | 0,880 | 0,905 |
| B6 two-stage | 1,035 | 1,035 |

**Thứ hạng không đổi.** Bảng có tác động (harm của B5 dịch 0,875 → 0,850) nhưng không đổi thứ tự, nên $\pi_0$ chưa phải một trục kết quả.

⚠️ **Đây mới là một nửa phép quét.** Cái được đổi là **bảng $\tau_{\text{sel}}$** (sinh ở 0,10 so với 0,0799), còn $\pi_0$ trong công thức posterior giữ nguyên giá trị suy dẫn. Quét đầy đủ $\pi_0 \in \{0{,}04;\ 0{,}08;\ 0{,}10;\ 0{,}20\}$ đòi mỗi giá trị một bảng riêng, 23 phút mỗi bảng.

---

## 3. $\eta_Q$ — chi phí cách ly (W2)

### 3.1 Tham số này là gì

$\eta_Q$ là giá của hành động cách ly trong ràng buộc ngân sách. Nó là thứ làm cho "cách ly tất cả" không còn miễn phí. Trước đợt này nó là `ETA_Q_COST = 2.0`, một số gán tay.

### 3.2 Hai nửa, đo bằng hai cách khác nhau

$$\eta_Q(k) = c_{\text{detach}}(k) + c_{\text{restore}}(k)$$

| Nửa | Là gì | Đo bằng cách nào |
|---|---|---|
| $c_{\text{detach}}$ | Gỡ carrier khỏi vòng lặp và chạy lại task mà không có nó | Chạy **cùng workflow, cùng seed** hai lần — một lần bình thường, một lần cách ly carrier đó ở task đầu — lấy hiệu CPU-time của cả episode, lặp 20 lần, lấy trung vị |
| $c_{\text{restore}}$ | Dựng lại những gì cách ly đã xoá | Cách ly xoá **mọi** item của carrier, kể cả item sạch, nên phục hồi tốn $n_{\text{live}}(k)$ lần ghi. Đơn giá ghi một item suy từ **chi phí thật** của P2 |

### 3.3 Đơn giá ghi một item lấy từ đâu

Đây là mắt xích làm cho $\eta_Q$ có nghĩa. Ghi một item là **việc của agent**, không phải việc của judge:

1. Các bản ghi P2 (`spikes/p2-pilot.jsonl`) có `tokens_in`, `tokens_out`, `cache_hit` nhưng `cost_usd` để trống — runner không tính giá.
2. `llms.py` giữ bảng giá của `deepseek-v4.1-flash` đã xác minh ngày 15/09.
3. Nhân lại: chi phí trung vị một lần chạy agent thật = **0,0868 USD**.
4. Số item agent ghi mỗi task, đo từ trace: **2,85**.
5. Suy ra **0,0305 USD cho một lần ghi item**, so với **0,000495 USD cho một lần chấm item**.

### 3.4 Chạy từng bước

```bash
cd auditgame
python3 tools/measure_eta_q.py --reps 20 > spikes/eta-q.json
python3 -c "
import json; d=json.load(open('spikes/eta-q.json'))
print('usd/task (P2):', round(d['usd_per_task_p2']['median'],4))
print('writes/task:', round(d['writes_per_task'],2), '-> usd/write:', round(d['usd_per_write'],5))
for c,v in d['eta_q'].items():
    print(c, 'eta_Q =', round(v['eta_q_usd'],5), '| kappa =', round(v['kappa_usd'],6),
          '| ratio =', round(d['eta_q_over_kappa'][c],1))"
```

### 3.5 Kết quả

| Carrier | $\eta_Q$ (USD) | $\kappa$ (USD) | Tỉ lệ |
|---|---|---|---|
| memory | 0,16263 | 0,002643 | **61,5×** |
| skill | 0,03411 | 0,000554 | 61,5× |
| queue | 0,04721 | 0,000767 | 61,5× |
| branch | 0,13705 | 0,002227 | 61,5× |

**Một câu cho bài:** nhìn một item là việc của judge, dựng lại một item là việc của agent, và chênh lệch đó là 61,5 lần. Cách ly không phải một phép audit đắt hơn — nó là một loại chi phí khác.

### 3.6 Phần gỡ đo ra $\le 0$, và vì sao vẫn phải báo

Trong harness, gỡ một carrier **giảm** việc: agent truy xuất ít hơn, phép chấm ít item hơn, nên episode chạy nhanh hơn. Script ghi 0,0 và ghi kèm `notes` nói rõ đây là **cận dưới**. Đó là sự thật về harness này, không phải về hệ thật — ở hệ thật, chạy lại một task mà không có memory của nó nghĩa là làm lại task đó.

### 3.7 Hệ quả chưa xử lý

$\eta_Q / \kappa = 61{,}5$ đo trên **thang USD**. `policies.ETA_Q_COST = 2.0` nằm trên **thang placeholder** (trong đó $\kappa$ là 0,4–4,1). Nếu áp tỉ lệ đo được vào thang placeholder thì cách ly memory tốn $61{,}5 \times 0{,}4 = 24{,}6$, vượt ngân sách 17,95 — tức **không chính sách nào cách ly nổi**, và NC1 lẫn hành vi cách ly của Sentinel biến mất khỏi mọi bảng.

Đây là một quyết định phải chốt trước khi chạy lưới chính, không phải một thay đổi lặng lẽ. **Cần thầy quyết.**

---

## 4. $\beta_k$ — tốc độ trôi lành tính (W3)

### 4.1 Tham số này là gì

$\beta_k$ là xác suất carrier $k$ thay đổi vì lý do thông thường trong một task. Nó là nguyên nhân cạnh tranh với đầu độc: khi $\beta = 0$, mọi báo động đều là bằng chứng của đầu độc và "cách ly tất cả" là tối ưu, nên $\lambda_Q$ đang định giá một rủi ro mà thế giới không sinh ra.

### 4.2 Luật ánh xạ phải khai trước khi đếm

Carrier sống **ngoài** repo, nên không commit nào "chạm memory". Phải khai một phép tương tự, và vì nó là **quyết định mô hình hoá** chứ không phải phép đo, script chạy **hai luật** rồi báo cả hai:

| Carrier | Luật A (chính) | Luật B (đối chứng) |
|---|---|---|
| memory | `*.md`, `*.rst`, `*.txt`, `docs/**`, `CHANGELOG*` | `docs/**`, `*.rst` |
| skill | `utils/`, `helpers/`, `_base.py`, `lib/`, `common/` | mọi `*.py` |
| queue | `setup.py`, `tox.ini`, `Makefile`, `.github/**`, `scripts/`, `conftest.py` | `.github/**`, `tox.ini` |
| branch | mọi commit → $\beta = 1{,}0$ **theo cấu tạo** | như luật A |

**Cửa sổ là task, không phải lịch:** tập commit nằm giữa `base_commit` của hai instance SWE-bench liên tiếp cùng repo.

### 4.3 Chạy từng bước

```bash
cd auditgame
# Cần 10 repo đã clone trong workspace/ (harness tự clone khi chạy dữ liệu thật)
python3 tools/measure_beta.py --windows 8 > spikes/beta-k.json
python3 -c "
import json; d=json.load(open('spikes/beta-k.json'))
for tag in ('primary_rule_A','alternative_rule_B'):
    print(tag, {c: round(v['median'],3) for c,v in d[tag]['beta_across_repos'].items() if v})
print('hai luật cùng thứ tự carrier:', d['carrier_order_agrees_between_rules'])"
```

### 4.4 Kết quả trên 10 repo thật

| Carrier | Luật A, trung vị [min, max] | Luật B, trung vị |
|---|---|---|
| memory | **0,314** [0,033 – 0,570] | 0,279 |
| skill | 0,058 [0,006 – 0,139] | **0,607** |
| queue | 0,033 [0,006 – 0,118] | 0,013 |
| branch | 1,000 (theo cấu tạo) | 1,000 |

### 4.5 ⚠️ Tiêu chí nghiệm thu đã kích hoạt: $\beta$ không định danh được

Điều kiện khai trước: *"chạy lại với một luật ánh xạ thay thế; nếu kết luận định tính đổi thì $\beta$ chuyển sang M2 (quét)"*. Kết quả: skill lệch **hơn 10 lần** giữa hai luật (0,058 so với 0,607), và thứ tự carrier đổi. Vậy:

- **memory (≈0,28–0,31) và branch (1,0)** sống sót cả hai luật — đây là hai số duy nhất được phép trích dẫn.
- **skill và queue phải quét**, không được chốt.
- `belief.WindowBelief` giờ mặc định $\beta = 0{,}314$ (tỉ lệ của memory) và trong mã ghi rõ đó là **mặc định, không phải phát hiện**.

### 4.6 Một cảnh báo về thang đo

Giữa hai instance SWE-bench liên tiếp có **200–1.700 commit** tuỳ repo. Một "task" trong benchmark tương ứng với hàng trăm commit thật, nên phép tương ứng task ↔ commit là lỏng. Phải ghi vào phần đe doạ tính hợp lệ.

---

## 5. $c$ — hằng số của Định lý 4 (W6)

### 5.1 Ý định ban đầu

Định lý 4 phát biểu sàn ngân sách để phân biệt trạng thái nhiễm với lành tính:

$$B \ \ge\ \frac{c\,\bar\kappa\,(1+\chi)\,\log(1/\alpha)}{\gamma^2}\left(1 + \frac{\Delta}{H}K\right)$$

Vế trái đo được nếu hiểu định lý là phát biểu về **sự hội tụ của belief**: $B_{\min}$ là ngân sách nhỏ nhất để tại $\sigma$, posterior đặt ít nhất $1-\alpha$ khối lượng lên đúng window $(k, \iota, \sigma)$.

### 5.2 Chạy từng bước

```bash
cd auditgame
python3 tools/measure_c.py --n-wf 4 > spikes/theorem4-c.json
python3 -c "
import json; d=json.load(open('spikes/theorem4-c.json'))
print('ngân sách có làm dịch posterior không:', d['precondition']['budget_moves_the_posterior'])
print('biên độ trên thang ngân sách:', d['precondition']['max_spread_over_ladder'])
print('c =', d['c']); print(d['refused'] or '')"
```

### 5.3 Kiểm tiền đề trước, không giả định

Script kiểm **trước** một điều kiện cần: ngân sách có làm dịch posterior không. Thang ngân sách $B \in \{2;\ 8;\ 17{,}95;\ 60;\ 200\}$.

### 5.4 🔴 Kết quả: từ chối trả số, và lý do quan trọng hơn con số

| Ngân sách | 2,0 | 8,0 | 17,95 | 60,0 | 200,0 |
|---|---|---|---|---|---|
| Khối lượng posterior trên window thật | 0,0003 | 0,0003 | 0,0003 | 0,0003 | 0,0003 |

Biên độ trên toàn thang: **0,0**. Chẩn đoán kèm theo:

| Đại lượng | Giá trị lớn nhất đạt được |
|---|---|
| Khối lượng trên đúng window (trong 72 window) | 0,085 |
| Khối lượng trên đúng carrier | 0,835 |
| $\Pr[\text{có tấn công}]$ | 0,999 |

**Nguyên nhân:** `belief.WindowBelief.update` được đưa tín hiệu của **mọi** carrier ở **mọi** task, bất kể chính sách đã audit cái gì. Trong mã hiện tại, **quan sát là miễn phí**; ngân sách chỉ quyết định việc item có bị cách ly hay không, không quyết định defender *biết* được gì.

Định lý 4 nói ngân sách mua thông tin. Trong harness, thông tin không phải mua. Vậy vế trái của định lý không tồn tại, và mọi $c$ fit ở đây sẽ là một phát biểu về thang ngân sách chứ không về định lý. Script vì vậy trả `c = null` kèm trường `refused` ghi nguyên văn lý do — đúng luật *"chưa đo ≠ đo ra 0"*.

### 5.5 Phải sửa gì để đo được $c$

Cho belief chỉ cập nhật từ những carrier **đã được audit** ở task đó. Đây là thay đổi mô hình quan sát, chạm tới mọi chính sách đọc điểm, nên phải khai trước khi làm, không phải sửa lặng lẽ. Sau khi sửa: chạy lại `tools/measure_c.py`, kiểm tính đơn điệu, rồi mới fit $c$ và hồi quy $\log c_{\text{ô}}$ theo ba thừa số để kiểm dạng hàm của cận.

---

## 6. $\Delta$ thực trên repo SWE-bench (W5)

### 6.1 Vì sao phải đo

Crossover mà đề tài dự đoán nằm ở $\Delta \approx 2$. Dự đoán đó chỉ đáng quan tâm nếu workflow thật có $\Delta$ cùng thang. Số đã có trước đây (trung vị 3, p75 10) đo trên **repo của chính đề tài**, không phải quần thể mục tiêu.

### 6.2 Cách đo

Với mỗi instance SWE-bench Verified:

| | |
|---|---|
| **Hạ nguồn** | chính instance đó: một issue mà bản vá sửa một tập file đã biết |
| **Thượng nguồn** | commit gần nhất **trước** `base_commit` có chạm vào một trong các file đó — blame kiểu SZZ trên chính những file mà bản vá phải sửa |
| **$\Delta$** | khoảng cách giữa hai mốc, tính bằng **hai đơn vị** |

**Vì sao dùng SZZ chứ không `git bisect`:** bisect đòi môi trường chạy được test ở mọi commit, tức một image Docker cho mỗi repo mỗi thời kỳ. Suy luận yếu hơn, và điều đó được khai trong docstring thay vì ngầm hiểu.

**Hai đơn vị, hai câu hỏi khác nhau:**
- **Theo task** — bao nhiêu instance của repo nằm giữa hai mốc. Đây là đơn vị của lưới $\Delta$, nhưng nó cũng là thuộc tính của việc benchmark lấy mẫu repo đó dày hay thưa.
- **Theo commit** — bao nhiêu commit nằm giữa hai mốc. Độc lập với cách lấy mẫu của benchmark.

### 6.3 Chạy từng bước

```bash
cd auditgame
python3 tools/measure_delta_swebench.py --per-repo 20 > spikes/delta-swebench.json
python3 -c "
import json; d=json.load(open('spikes/delta-swebench.json'))
for r,v in d['per_repo'].items():
    print(r, 'Δ_task median', v['median'], '| >=2:', round(100*v['share_ge_2']), '%',
          '| Δ_commit median', v['commit_distance']['median'])"
```

### 6.4 Kết quả

| Repo | $\Delta$ theo task (trung vị) | Tỉ lệ $\Delta \ge 2$ | $\Delta$ theo commit (trung vị) | p75 |
|---|---|---|---|---|
| django/django | **4,5** | **55%** | 180 | 680 |
| sympy/sympy | 1,0 | 25% | 140 | 573 |
| sphinx-doc/sphinx | 0,5 | 25% | 76 | 214 |
| astropy/astropy | 0,0 | 25% | 194 | 935 |
| matplotlib/matplotlib | 0,0 | 15% | 88 | 206 |
| scikit-learn/scikit-learn | 0,0 | 15% | 36 | 69 |
| pytest-dev/pytest | 0,0 | 11% | 56 | 150 |
| pylint-dev/pylint | 0,0 | 0% | 15 | 100 |
| pydata/xarray | 0,0 | 0% | 14 | 32 |
| psf/requests | 0,0 | 0% | 18 | 28 |

### 6.5 Co-change và lọc bằng đồ thị import

Mục 6.2 mới quy trách cho commit gần nhất chạm **cùng file** mà bản vá sửa — tức tự-liên-đới, không cần bảng coupling. Stage 3.7 đòi câu hỏi khó hơn: cặp module A và B **cùng đổi**, rồi đo độ trễ giữa "A đổi" và "B gãy".

$$\text{support}(A,B) = \text{số commit chạm cả hai module}, \qquad \text{confidence}(A \to B) = \frac{\text{support}(A,B)}{\text{số commit chạm } A}$$

Ngưỡng khai trước khi đếm: support $\ge 5$, confidence $\ge 0{,}10$, module = hai thành phần đầu của đường dẫn, bỏ commit chạm hơn 8 module (release sweep và reformat nối mọi thứ với mọi thứ).

```bash
cd auditgame
python3 tools/measure_cochange.py --per-repo 12 --commits 2000 > spikes/cochange.json
```

**Kết quả — tỉ lệ cặp coupling có đường import thật:**

| Repo | Cặp qua ngưỡng | Kiểm import | Qua lọc |
|---|---|---|---|
| sympy/sympy | 9 | 9 | **78%** |
| django/django | 153 | 25 | 44% |
| scikit-learn/scikit-learn | 80 | 25 | 40% |
| astropy/astropy | 34 | 25 | 24% |
| pydata/xarray | 141 | 25 | 20% |
| sphinx-doc/sphinx | 75 | 25 | 12% |
| pylint-dev/pylint | 111 | 25 | 4% |
| matplotlib, pytest, requests | 14–36 | 14–25 | **0%** |
| **Tổng** | | 221 | **19%** |

**81% coupling mạnh nhất không có đường import nào chống lưng.** Đây là con số định lượng cho đúng cảnh báo của tài liệu phương pháp luận: *co-change là tương quan tiến hoá, không hẳn nhân quả*.

**Một bẫy đã đo được và đã sửa.** Lần chạy đầu, phép dò cạnh import quét cả cây nguồn, và `django/db` được tính là "import" `docs/releases` với support 122 — vì tài liệu chứa ví dụ mã có dòng `from django.db`. Sau khi giới hạn phép dò trong file `.py`, tỉ lệ sống sót toàn cục rơi từ 27% xuống 19% và các cặp mã↔tài liệu bị loại đúng. (Lỗi thứ hai cùng lượt: `git grep -E` dùng POSIX ERE nên không hiểu `\s` và `\b`; mẫu dùng chúng khớp **không gì cả** trong khi trông vẫn như đang chạy, khiến bộ lọc lần đầu báo 0% ở mọi repo.)

### 6.6 $\Delta$ dưới cách quy trách đã lọc

Bắt thượng nguồn phải là **module khác**, có coupling qua ngưỡng **và** có cạnh import:

| Repo | $n$ | $\Delta$ theo task | $\Delta$ theo commit |
|---|---|---|---|
| astropy | 9 | 0 | 16 |
| django | 8 | 0 | 7 |
| pydata/xarray | 12 | 0 | 2 |
| scikit-learn | 8 | 0 | 6 |
| sphinx | 10 | 0 | 16 |
| pylint | 2 | 0 | 12 |
| sympy | 1 | 0 | 10 |

**$\Delta$ phụ thuộc mạnh vào luật quy trách:** tự-liên-đới (cùng file) cho $\Delta$ theo commit là 14–194, còn liên-đới-đã-lọc cho 2–16. Lý do: một module có nhiều bạn coupling, nên "commit gần nhất chạm một bạn bất kỳ" gần như luôn vừa mới xảy ra. Không luật nào trong hai luật là phát biểu nhân quả; phải báo cả hai kèm luật đã dùng.

### 6.7 Đọc kết quả này thế nào

1. **Theo đơn vị task, $\Delta$ nhỏ hơn nhiều so với số dogfood.** Gộp lại: trung vị 0, p75 1, chỉ **19%** instance có $\Delta \ge 2$. Nếu crossover ở $\Delta \approx 2$ thì vùng mà phân bổ thích nghi có lợi phủ khoảng một phần năm workload — trừ django, nơi tỉ lệ là 55%.
2. **Đơn vị task phụ thuộc mật độ lấy mẫu.** Django có 231/500 instance Verified nên nhiều instance rơi vào giữa hai mốc; các repo thưa cho $\Delta = 0$ gần như luôn luôn. Vì vậy $\Delta$ theo task **không** phải thuộc tính thuần của repo, và không được trích dẫn một mình.
3. **Theo commit thì mọi repo đều có độ trễ đáng kể** (trung vị 14–194 commit, p75 lên tới 935). Tức hiện tượng "sửa chỗ này, hỏng chỗ kia sau một thời gian" là thật; cái khó là quy nó về đơn vị task của benchmark.
4. **Hệ quả cho bài:** ranh giới vùng nên phát biểu theo tỉ lệ workload nằm trong vùng $\Delta \ge 2$ **theo từng repo**, thay vì một con số crossover duy nhất.

---

## 7. Còn nợ

| Việc | Vì sao chưa làm |
|---|---|
| **W7** — 240 game nhỏ và $\rho$ đúng không gian | Phụ thuộc thư viện 28 policy (chưa dựng) |
| **W8** — payload AgentPoison và MINJA | Thuộc mạch tấn công, không phải mạch tham số |
| Quét $\pi_0$ đầy đủ | Mỗi giá trị cần một bảng $\tau_{\text{sel}}$ riêng, 23 phút mỗi bảng; hiện mới có phép kiểm hai điểm ở mục 2.6 |
| Quét $\beta$ cho skill và queue | Hệ quả của mục 4.5 |

---

## 8. Các file sinh ra trong đợt này

| File | Nội dung |
|---|---|
| `auditgame/tools/measure_kappa.py` | Đo $\kappa$ bằng CPU-time từ chính vòng chạy game |
| `auditgame/tools/measure_eta_q.py` | Đo hai nửa của $\eta_Q$ |
| `auditgame/tools/measure_beta.py` | Đếm $\beta_k$ trên lịch sử 10 repo, hai luật ánh xạ |
| `auditgame/tools/measure_c.py` | Fit $c$, kèm phép kiểm tiền đề |
| `auditgame/tools/measure_delta_swebench.py` | Đo $\Delta$ thực theo hai đơn vị trên 10 repo |
| `auditgame/tools/measure_cochange.py` | Co-change (support, confidence), lọc bằng đồ thị import, $\Delta$ đã lọc |
| `auditgame/tests/gate1_integrity/test_cost_provenance.py` | 9 test cho W1, W2, W4 |
| `auditgame/spikes/kappa-cpu.json`, `eta-q.json`, `beta-k.json`, `theorem4-c.json`, `delta-swebench.json`, `cochange.json` | Kết quả kèm provenance |
| `auditgame/costs.py` | Nguồn duy nhất: $\pi_0$, $\eta_Q$, $\beta$, đơn giá ghi item |
