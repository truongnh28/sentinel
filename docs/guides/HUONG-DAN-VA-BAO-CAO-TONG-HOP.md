# BÁO CÁO TỔNG KẾT KỸ THUẬT & SỔ TAY VẬN HÀNH DỰ ÁN SENTINEL (FSE 2027)

> **Mục tiêu tài liệu:** Tổng kết toàn diện kết quả thực thi kế hoạch FSE 2027 (bản 2), phân tích sâu các phát hiện khoa học, đồng thời cung cấp hướng dẫn sử dụng chi tiết về cách chạy mã nguồn, lọc và xử lý dữ liệu (data filtering & processing), kiểm thử hệ thống ba cổng, và quy trình tái lập con trỏ số liệu cho bài báo.
>
> **Phiên bản:** v2.0 (Khung B là Mặc định · Khung A′ là Tiềm năng tương lai)  
> **Thời điểm cập nhật:** 19/09/2026  
> **Trạng thái:** Toàn bộ 8 hạng mục kỹ thuật tự động đã hoàn tất và đóng băng trên nhánh `master`.

---

# PHẦN I: BÁO CÁO TỔNG KẾT & ĐÁNH GIÁ KỸ THUẬT

## 1. Bối cảnh & Định vị Học thuật (Khung B là Mặc định)

Trước thềm nộp bài FSE 2027 (hạn 02/10/2026 AoE), toàn bộ dự án Sentinel được định vị dứt khoát trên **Khung B (Framework B)**:
- **Hiện thực đã được đo lường:**
  1. Không có kẻ tấn công nào vượt qua Cổng 2 (Gate 2) một cách hợp lệ khi loại bỏ các giả tượng sắp xếp nhân tạo (`sorted()`).
  2. Trần phân giải $0.56$ nằm lọt thỏm bên trong dải nhiễu cấu trúc ngẫu nhiên của tập ngữ cảnh (corpus noise band) ở mọi quy mô $n \le 1800$.
  3. Thí nghiệm pilot trên agent reasoning thực tế (`deepseek-v4.1-flash`) cho thấy $0/14$ instance tuân thủ lời khuyên độc hại: mô hình tiếp nhận giả định $P(\text{harm} \mid \text{retrieved}) = 1$ hoàn toàn sụp đổ trên LLM thực tế.
  4. Phép quét tổn thất $L$ đa chiều trên payload v2 chứng minh chính sách Sentinel không thắng được baseline chấm điểm rủi ro $B5$ (`B5 risk-score`), khi $B5$ dẫn trước trên $61/64$ ô ở $\lambda_Q = 0.10$ và chỉ tiêu tốn $7–13\%$ ngân sách so với $47–50\%$ của Sentinel.
- **Giá trị đóng góp cốt lõi của Khung B:** Không cố gắng vẽ ra một hệ thống phòng thủ "bất bại" dựa trên các con số ảo, mà **vạch trần giới hạn phương pháp luận** của các cổng kiểm định so khớp bề mặt (surface-matching gates) trong bảo mật agentic coding, đồng thời làm rõ sự khác biệt bản chất giữa mô hình tiếp nhận giả lập (MockAgent) và hành vi phản biện của mô hình ngôn ngữ lớn thực tế.

---

## 2. Chi tiết 8 Hạng mục Công việc Đã Hoàn tất

| STT | Mã Task | Commit Hash | Nội dung Thay đổi & Trách nhiệm Kỹ thuật | Trạng thái |
|:---:|:---:|:---:|:---|:---:|
| 1 | **A1a** | `3da9363` | **Fix Bug Đường Tiêm Payload:** Sửa `MatchedAttack.payload` gọi qua `build.payload_content` thay vì tự dựng chuỗi sai lệch kích thước; bổ sung invariant test bảo vệ; đo lại toàn bộ ma trận Screen và Certify. | Hoàn tất |
| 2 | **A1b** | `ce55c56` | **Chốt Hai Quyết định Phương pháp luận:** Giữ đặc trưng `topic` trong $F_{\text{match}}$ (báo cáo trung thực hai khâu); xác lập **Họ muối (Salt Family)** với ngưỡng $\ge 80\%$ ($14/17$ muối) là đơn vị lặp lại độc lập thay vì split đơn lẻ. Tạo spike `docs/preregistration/cong-v2-chot.md`. | Hoàn tất |
| 3 | **D1** | `4edb4f9` | **Sweep Chấm $L$ trên Payload v2:** Chạy lại toàn bộ lưới $d'$ trên v2 ở 2 chế độ (`pinned` và `following`); tạo spike `docs/reports/sweep-loss-v2.md`; xác nhận phán quyết Khung B (Sentinel thua B5 trên $L$). | Hoàn tất |
| 4 | **A2** | `fbd4c09` | **Đóng Băng Gate 2 v2:** Hiện thực tiêu chí họ muối trong `analysis/gate2_v2.py`; sinh `reference/gate2_v2.json` với Dual MD5s (`single-salt` và `17-salt family`). | Hoàn tất |
| 5 | **A3** | `1392edc` | **Đường Cong Dải Nhiễu theo Quy mô $n$:** Tạo module `analysis/band_vs_n.py` và test `test_band_vs_n.py`; đo thực nghiệm trên $n \in \{100, 200, 400, 900, 1800\}$ qua họ muối; tạo spike `docs/reports/dai-theo-n.md`. | Hoàn tất |
| 6 | **P1–P4**| `cb48e90` | **Thí nghiệm P2 Ba Arm & Đọc Mô Hình Tiếp Nhận:** Tạo bộ điều phối `spikes/p2_arms.py`, kiểm thử `test_p2_arms.py`, ghi nhận spike `docs/reports/p2-three-arms.md`; xác nhận **Giả thuyết (ii)**: Agent từ chối làm theo `raw_write`, chứng minh mọi số harm trong bài là harm dưới MockAgent. | Hoàn tất |
| 7 | **C1–C3**| `bd27d9a` | **Cập nhật Toàn diện Bài Báo LaTeX:** Đồng bộ `benchmark.tex`, `threats.tex`, `certification.tex`; tuân thủ Luật II.4 (`\repro` với `\nolinkurl`); biên dịch `main.pdf` 13 trang ACM, 0 lỗi, giảm `\PENDING` từ 18 còn 13. | Hoàn tất |
| 8 | **B1–B7**| `e5fc2d3` | **Hiện Thực B-lite Detector & Giao Thức G4:** Xây dựng `fdetect.py` ($m = v_1$, ràng buộc $v_2$, hiệu chuẩn $\tau(d')$, per-attacker $d'_{\mathrm{eff}}$, `RepoContext` validation) và `fdetect_g4.py` ($n=38, \theta=0.75$, Clopper-Pearson exact qua bisection). 34 tests GREEN. | Hoàn tất |

---

## 3. Bốn Phát Hiện Thực Nghiệm & Phương Pháp Luận Cốt Lõi

### (1) Sự Sụp Đổ Kênh Chủ Đề (`topic` Channel Collapse)
- **Hiện tượng:** Ở phiên bản v1, kênh `topic` đạt AUC cao nhân tạo ($0.88 - 0.93$).
- **Nguyên nhân:** Hàm trích xuất đặc trưng `retrieval.payload_topic` sử dụng `sorted(tokens)[:k]`. Thứ tự sắp xếp chữ cái biến một đặc trưng nội dung thành một đặc trưng định dạng giả tạo mà Python hash order vô tình làm lộ.
- **Hệ quả thực tế:** Khi loại bỏ `sorted()`, tín hiệu của kênh `topic` lập tức sụp đổ về mức đoán ngẫu nhiên ($0.49 - 0.53$). Một định lý toán học/thuật toán đã bị đọc nhầm thành một phép đo thực nghiệm bảo mật.

### (2) Đơn Vị Lặp Lại Khoa Học: Họ Muối (Salt Family)
- **Thực tế:** Trên tập ngữ cảnh hữu hạn ($n=900$), việc lặp lại 20/20 split ngẫu nhiên trên **cùng một muối (salt)** không phải là 20 phép đo độc lập vì các split bị chồng chéo dữ liệu nghiêm trọng.
- **Quy luật:** Khi quét trên họ 17 muối khai trước, kết quả lật ngược hoàn toàn ($8$ muối xanh, $9$ muối đỏ).
- **Quyết định:** Đơn vị tái lập chuẩn khoa học phải là **Họ muối**, với tiêu chí tiền-đăng-ký là $\ge 80\%$ muối vượt qua ($14/17$ muối).

### (3) Định Luật Thu Hẹp Dải Nhiễu theo $n$ ($n$-Scaling Law)
- **Đo lường:** Đường cong dải nhiễu theo quy mô ngữ cảnh $n \in \{100, 200, 400, 900, 1800\}$:
  - $n = 100$: Dải $[0.4975; 0.6059]$, bề rộng $0.1084$.
  - $n = 400$: Dải $[0.5186; 0.5985]$, bề rộng $0.0799$.
  - $n = 900$: Dải $[0.5323; 0.6027]$, bề rộng $0.0704$.
  - $n = 1800$: Dải $[0.5385; 0.5933]$, bề rộng $0.0548$.
- **Kết luận:** Mặc dù dải nhiễu thu hẹp đơn điệu theo $n$, trần phân giải $0.56$ luôn lọt thỏm bên trong dải $[lo; hi]$ ở mọi kích thước khảo sát. Hàm `resolving_n` trả về ngoại lệ `Unresolved`. Đây là kết quả trung tâm của Khung B: **Một cổng so khớp bề mặt ở quy mô benchmark hiện hành không có đủ độ nhạy để phân giải kẻ tấn công đạt ngưỡng $0.56$.**

### (4) Thất Bại của Mô Hình Tiếp Nhận trên LLM Thực Tế (Threat P11)
- **Kết quả pilot 3 arm:**
  - Control Arm: Tỉ lệ sinh patch $64.3\%$, vượt qua test kiểm thử $50\%$.
  - Main Arm: Sinh patch tương đương, nhưng **$0/14$ trường hợp** làm theo hàm bị đầu độc `raw_write`.
- **Bản chất:** LLM reasoning thực tế (như DeepSeek) có khả năng tự kiểm tra tính nhất quán với kho mã, từ chối các hướng dẫn độc hại gợi ý các hàm không tồn tại trong codebase.
- **Tác động đến bài báo:** Toàn bộ các bảng số liệu harm công bố trong bài được dán nhãn rõ ràng là **"Tổn thất dưới mô hình tiếp nhận giả lập (MockAgent)"**, loại bỏ rủi ro bị phản biện đánh gục do giả định $P(\text{harm} \mid \text{retrieved}) = 1$ thiếu căn cứ.

---

## 4. Bảng Kiểm Tra Hiện Trạng Hệ Thống Cổng (Gates Ledger)

```
==============================================================================
  KẾT QUẢ KIỂM TRA HỆ THỐNG BA CỔNG (GATES SYSTEM RUN_ALL)
==============================================================================
  CỔNG 1 — INTEGRITY (515/528 Passed, 13 Skipped):
    - 515 tests: Đạt tuyệt đối (toàn bộ invariants, fixtures, và thí nghiệm mock).
    - 13 skipped: Do máy kiểm thử không có Docker daemon (bảo lưu cho môi trường CI full).
    
  CỔNG 2 — VALIDITY (200/202 Passed, 2 Pre-registered Structural RED):
    - 200 tests: Đạt tuyệt đối (toàn bộ kiểm thử dải nhiễu, detector, F_match, split).
    - 2 tests RED: Giữ nguyên theo luật N3 và tiền-đăng-ký:
      1. test_matched_epsilon_budget: Bước nhảy MockAgent từ 0.44 -> 1.0 (Threat P9).
      2. test_feature_overlap: Đơn split trên 1 muối không thể kết luận (Task A1b).

  CỔNG 3 — POWER (15/15 Passed):
    - 15 tests: Đạt 100% về kích thước mẫu và độ tin cậy thống kê.

  BÀI BÁO LATEX (ACM ART 13 TRANG):
    - File main.pdf: Biên dịch thành công 13 trang, 0 lỗi cú pháp.
    - \PENDING slots: Giảm từ 18 xuống còn 13 (chỉ còn các ô dành riêng cho số liệu học viên).
==============================================================================
```

---

# PHẦN II: SỔ TAY VẬN HÀNH & HƯỚNG DẪN SỬ DỤNG

## 1. Cấu Trúc Thư Mục & Vai Trò Các Tệp Tin Chính

```
auditgame/
├── analysis/                     # Các module phân tích toán học & thống kê
│   ├── band_vs_n.py              # Tính bề rộng dải nhiễu theo quy mô n và họ muối
│   ├── gate2_v2.py               # Đóng băng định nghĩa Gate 2 v2 (17 muối, ngưỡng 80%)
│   ├── benign_corpus.py          # Sinh ngữ cảnh benign và ghép cặp
│   └── discriminator.py          # Tính AUC trên các split
├── scripts/                      # Các công cụ hỗ trợ chạy đo & render
│   ├── measure_band_vs_n.py      # Script tự động đo đường cong dải nhiễu và xuất JSON
│   └── render_sweep_v2.py        # Script đọc file JSON sweep và tạo bảng markdown báo cáo
├── spikes/                       # Hồ sơ thực nghiệm chi tiết
│   ├── sweep-loss-v2.md          # Báo cáo kết quả sweep tổn thất L trên v2
│   ├── dai-theo-n.md             # Báo cáo thực nghiệm đường cong dải nhiễu theo n
│   ├── p2-three-arms.md          # Phân tích thực nghiệm 3 arm trên LLM thực tế
│   ├── sweep-v2-following.json   # Dữ liệu quét L chế độ tau-follows-dprime (1.0 MB)
│   └── sweep-v2-pinned.json      # Dữ liệu quét L chế độ ghim ngưỡng (1.1 MB)
├── tests/                        # Hệ thống ba cổng kiểm thử tự động
│   ├── run_all.py                # Script chạy toàn bộ 3 cổng
│   ├── gate1_integrity/          # Cổng 1: Đảm bảo số liệu là thật, không giả mạo
│   ├── gate2_validity/           # Cổng 2: Đảm bảo số liệu đo đúng khái niệm
│   └── gate3_power/              # Cổng 3: Đảm bảo công suất thống kê
├── dprime_sweep.py               # Module chạy quét lưới d' và tính hàm mất mát L
├── fdetect.py                    # Mô hình B-lite detector cấp độ 3 (RepoContext)
├── fdetect_g4.py                 # Giao thức thỏa thuận đồng thuận G4 & Clopper-Pearson
└── build.py, attacks.py, core.py # Lõi giả lập AuditGame
```

---

## 2. Hướng Dẫn Chạy Kiểm Thử Hệ Thống Ba Cổng

### Chạy nhanh từng cổng riêng biệt
Tất cả các kiểm thử đều sử dụng thư viện chuẩn của Python (`unittest`), không dùng `pytest` hay `numpy`:

```bash
cd auditgame

# 1. Chạy Cổng 1 (Integrity)
python3 -m unittest discover tests/gate1_integrity

# 2. Chạy Cổng 2 (Validity)
python3 -m unittest discover tests/gate2_validity

# 3. Chạy Cổng 3 (Power)
python3 -m unittest discover tests/gate3_power
```

### Chạy toàn bộ 3 cổng bằng `run_all.py`
```bash
# Chạy dừng ở cổng lỗi đầu tiên (mặc định)
python3 tests/run_all.py

# Chạy toàn bộ cả 3 cổng để xem bức tranh tổng thể
python3 tests/run_all.py --all
```
> **Lưu ý khi đọc log:**
> - Gate 1 hiển thị `13 SKIPPED`: Đây là các test đòi hỏi Docker container thực tế (chạy môi trường SWE-bench cách ly). Việc skip là hoàn toàn bình thường khi chạy trên host không bật Docker daemon.
> - Gate 2 hiển thị `2 RED`: Đây là **hai test được chủ động bảo lưu màu đỏ** theo đúng quy định của bài báo và kế hoạch đã phê duyệt (phản ánh đặc tính bước nhảy MockAgent và giới hạn của đơn split). Tuyệt đối không được chỉnh sửa mã nguồn để ép hai test này chuyển sang màu xanh.

---

## 3. Hướng Dẫn Chạy & Tái Lập Các Thí Nghiệm Cốt Lõi

### 3.1. Chạy Phép Quét Tổn Thất $L$ (`dprime_sweep.py`)
Phép quét đánh giá bốn chính sách phòng thủ (`B1 audit-at-commit`, `Sentinel`, `B5 risk-score`, `B6 two-stage`) trên 40 workflows:

```bash
# Chế độ 1: Bản chính - Ngưỡng tau chạy theo d' (tau-follows-dprime)
python3 dprime_sweep.py --n 40 --tau-follows-dprime --json spikes/sweep-v2-following.json

# Chế độ 2: Đối chứng - Ghim ngưỡng tau cố định ở mức mid (pinned)
python3 dprime_sweep.py --n 40 --json spikes/sweep-v2-pinned.json
```

### 3.2. Render Báo Cáo Markdown từ Dữ Liệu Quét JSON
Sau khi sinh ra các file `.json`, chạy script sau để tự động tổng hợp số liệu vào [docs/reports/sweep-loss-v2.md](../reports/sweep-loss-v2.md):

```bash
python3 scripts/render_sweep_v2.py
```

### 3.3. Đo Đường Cong Dải Nhiễu theo Quy mô $n$ (`band_vs_n`)
Để đo lường sự thu hẹp của dải nhiễu trên các kích thước corpus khác nhau:

```bash
python3 scripts/measure_band_vs_n.py
```
Kết quả được lưu vào `spikes/band_curve.json` và phân tích trong `docs/reports/dai-theo-n.md`.

### 3.4. Kiểm Thử Detector B-lite & Giao Thức $G_4$
Kiểm tra tính đúng đắn của bộ lọc detector và thuật toán chia đôi Clopper-Pearson:

```bash
python3 -m unittest tests/gate2_validity/test_fdetect_model.py tests/gate2_validity/test_fdetect_g4.py
```

---

## 4. Kỹ Thuật Lọc Dữ Liệu (Filtering) & Xử Lý Thống Kê (Data Processing)

### 4.1. Lọc Ô Khả Thi (Usable Cell Filtering)
Trong `dprime_sweep.py`, mỗi ô lưới được định danh bởi cặp $(d', \Delta)$. Một ô chỉ được đưa vào so sánh khi đạt tiêu chuẩn **usable**:
```python
# Điều kiện lọc ô khả thi:
cell.usable = (cell.n_feasible == cell.n_total) and (cell.reason is None)
```
- **Quy tắc xử lý:** Task `sympy-16597` không có payload khả thi dưới thẻ định dạng của simulator, làm giảm số workflow khả thi trên một số ô. Luật N3 yêu cầu: Ô nào không đủ điều kiện so sánh phải ghi nhận rõ `reason="infeasible_task"` chứ không được giả định ngầm `harm = 0` hoặc loại bỏ trong im lặng.

### 4.2. Tính Toán và Gán Trọng Số Hàm Tổn Thất Phòng Vệ ($L$)
Hàm mất mát tổng thể kết hợp cả rủi ro an ninh và chi phí vận hành:
$$L = \mathbb{E}[\text{harm}] + \lambda_Q \mathbb{E}[Q_{\text{false}}] + \lambda_T \mathbb{E}[T_{\text{lost}}]$$
- $\text{harm} \in [0, 1]$: Tỉ lệ payload độc hại bị thực thi.
- $Q_{\text{false}}$: Số lần cảnh báo giả làm phiền lập trình viên.
- $T_{\text{lost}}$: Tỉ lệ patch sạch bị chặn nhầm.
- **Quy trình lọc độ nhạy:**
  1. Quét $\lambda_Q \in [0.00, 0.50]$ để tìm điểm hòa vốn ($\lambda_Q^*$).
  2. Cắt lát độ nhạy theo $\lambda_T \in \{0.00, 0.25, 0.50\}$. Kết quả lọc cho thấy: Lợi thế duy nhất của Sentinel trước B1 biến mất khi $\lambda_T = 0$ (ưu thế co từ $64/64$ xuống chỉ còn $26/64$ ô).

### 4.3. Phân Chia Tập Hiệu Chuẩn & Báo Cáo Không Bị Rò Rỉ
Module `fdetect.py` chia tách tập item thành hai nửa độc lập:
- **Tập hiệu chuẩn (Calibration set):** Dùng để xác định ngưỡng phát hiện $\tau(d')$.
- **Tập báo cáo (Report set):** Dùng để đo lường $d'_{\mathrm{eff}}$.
- **Nguyên tắc kỹ thuật:** Phải sử dụng hoán vị ngẫu nhiên có hạt giống (`random.Random(seed).shuffle()`), tuyệt đối **cấm sử dụng `sorted()[:k]`**. Bài học từ sự cố sụp đổ kênh `topic` cho thấy bất kỳ thao tác sắp xếp đơn thuần nào cũng có thể tạo ra kênh rò rỉ giả tạo giữa hai tập dữ liệu.

### 4.4. Tính Khoảng Tin Cậy Chính Xác Clopper-Pearson qua Bisection
Module `fdetect_g4.py` cài đặt hàm tính khoảng tin cậy tỷ lệ nhị thức chính xác mà không cần phụ thuộc thư viện ngoài (`scipy`):
- **Cấm hoàn toàn:** Không quy đổi qua công thức Gaussian xấp xỉ $d' = \sqrt{2}\Phi^{-1}(\text{AUC})$ (công thức này giả định phân phối chuẩn đối xứng, hoàn toàn sai lệch trên mẫu nhỏ $n=38$).
- **Thuật toán chia đôi (Bisection):** Tính trực tiếp nghiệm của hàm tích lũy nhị thức:
  $$\sum_{j=k}^n \binom{n}{j} p^j (1-p)^{n-j} = \frac{\alpha}{2}$$
  Đảm bảo độ chính xác tuyệt đối tới 4 chữ số thập phân, xác nhận rằng tại $n=38, k=34$, chặn dưới khoảng tin cậy $95\%$ đạt $0.7516 \ge 0.75$.

---

## 5. Quy Trình Truy Vết & Tái Lập Số Liệu Bài Báo (LaTeX Law II.4)

Mọi con số xuất hiện trong bản thảo [HCMUT/paper/](file:///Users/truong.nh/Me/obsidian/HCMUT/paper) đều phải tuân thủ nghiêm ngặt **Luật II.4 (Zero Un-reproduced Numbers)**:
- **Cú pháp tái lập:**
  ```latex
  \repro{path/to/record.json}{anchor.json.path}
  ```
  Ví dụ: `\repro{reference/gate2_v2.json}{single_salt.md5}`
- **Quy tắc biên dịch:**
  Nếu một con số chưa có kết quả thực nghiệm để neo vào, bắt buộc phải dùng thẻ `\PENDING{Lý do}`. Khi bật chế độ `\PendingStrictOn`, trình biên dịch sẽ báo lỗi cứng nếu phát hiện ô số liệu trống mà không được khai báo.
- **Lệnh biên dịch bài báo PDF:**
  ```bash
  cd /Users/truong.nh/Me/obsidian/HCMUT/paper
  PATH="/Library/TeX/texbin:$PATH" latexmk -pdf -interaction=nonstopmode main.tex
  ```

---

## 6. Kế Hoạch Hành Động Còn Lại Dành Riêng Cho Học Viên

| Nhiệm vụ | Thời hạn | Trách nhiệm | Hướng dẫn thực hiện |
|:---|:---:|:---:|:---|
| **Task 8: Bảng bấm giờ $t_1$ human baseline** | 26/09/2026 | Học viên | Bấm giờ thời gian một kỹ sư con người đọc và phát hiện payload độc hại trên tập 15 task; điền số vào `sections/results.tex`. |
| **G4: 38 nhãn tay mù + Người thứ hai** | 26/09/2026 | Học viên | Hai người gán nhãn độc lập (mù nhãn nhau) trên 38 ghi chú bộ nhớ để tính hệ số thỏa thuận Cohen's Kappa trong `fdetect_g4.py`. |
| **Task B8: Batch API cho Judge thật** | Tùy chọn | Học viên | Nếu muốn có số thực tế cho Khung A', xuất `export OPENAI_API_KEY="..."` và chạy batch qua adapter `fdetect.OpenAIJudgeClient`. Nếu không kịp, giữ nguyên thiết kế Khung B như hiện tại. |
| **Nộp bài FSE 2027** | 02/10/2026 AoE | Học viên | Kiểm tra bản in `main.pdf` 13 trang và nộp lên hệ thống HotCRP/EasyChair. |

---
*Tài liệu này được tạo tự động và đóng băng cùng toàn bộ mã nguồn trên kho lưu trữ Sentinel.*
