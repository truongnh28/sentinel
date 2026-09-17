# Chấm điểm phép quét `d′` bằng hàm mất mát `L` đã khai báo, với **bốn** policy

**Ngày đo:** 18/09/2026 · **Module:** `dprime_sweep.py`
**Test:** `tests/gate1_integrity/test_dprime_sweep.py`,
`tests/gate2_validity/test_dprime_break_even.py`,
`tests/gate3_power/test_dprime_sweep_power.py`

---

## 1. Câu hỏi

Cho tới batch này, `dprime_sweep.py` tính

$$\Delta_{\text{harm}} = \text{harm}_{B1} - \text{harm}_{\text{Sentinel}}$$

và **chỉ** thế. Nhưng mục tiêu phòng thủ **đã khai báo** (Đề cương II.7.3,
`metrics.loss`) là ba số hạng:

$$L = \mathbb{E}[\text{harm}] + \lambda_Q\,\mathbb{E}[Q_{\text{false}}]
      + \lambda_T\,\mathbb{E}[T_{\text{lost}}]$$

`harm` là **một** trong ba, và đúng là số hạng Sentinel mạnh nhất: Sentinel mua lợi
thế `harm` bằng cách **cách ly nhiều hơn hẳn**. Thêm nữa, bảng cũ chỉ có **hai**
policy, nên nó **không thể** trả lời câu hỏi quyết định khung bài: *Sentinel có hơn
`B5 risk-score` và `B6 two-stage` không?* — trong khi hai cài đặt độc lập đều báo
policy hai tầng có cổng detector **hơn** Sentinel.

Batch này làm ba việc và **không** làm việc thứ tư:

1. quét **bốn** policy: `B1 audit-at-commit`, `Sentinel`, `B5 risk-score`,
   `B6 two-stage`;
2. chấm điểm bằng `L` **bên cạnh** `harm`, ở **ba** mức `λ_Q`;
3. in **bảng chi tiêu** (`metrics.spend_table`) cạnh mọi bảng kết quả;
4. **không** đụng vào đường cong `harm` đã công bố — xem §2.1.

---

## 2. Cái đã làm

| | |
|---|---|
| Policy đo mỗi ô | `POLICIES = (B1, Sentinel, B5, B6)` — đúng khoá `policies.REGISTRY` |
| `d′*` dưới `L` | `break_even()` **y nguyên**, áp lên các ô bóng đã hiệu `L` (`as_loss_cells`) |
| Ba cột `λ_Q` | `0` · `λ̄` **đo theo từng ô** · `metrics.LAMBDA_Q = 0,10` |
| `λ̄` | `metrics.lambda_q_star` trên **bốn** policy của **chính ô đó** — **KẾT QUẢ**, không phải tham số |
| `λ_T` | `metrics.LAMBDA_T = 0,50`, không đổi |
| CI95 của `ΔL` | `runner.bootstrap_paired` trên **`L` theo từng workflow**, cùng đơn vị lấy mẫu với `harm` |
| Chi tiêu | `metrics.spend_table` tại điểm lưới **khai báo trước** `d′ = 2,2` (điểm gần `d′(mid) = 2,211` nhất), cộng cột `spent` ở **mọi** điểm lưới |

### 2.1 Đường cong `harm` cũ **tái lập nguyên vẹn** — chứng minh

`python3 dprime_sweep.py --n 40` trước và sau batch này cho **cùng từng ký tự** ở
mọi trường `harm`: `harm_b1`, `harm_sentinel`, `dharm`, `ci_lo`, `ci_hi`,
`n_feasible`, `n_total`, `reason` ở cả 70 ô (16 điểm lưới thô + các điểm mịn hoá).
`d′*` dưới `harm` vẫn là **không có / không có / 2,55 / 0,60** — đúng bảng in trong
`spikes/dprime-sweep.md` §5.

```bash
cd HCMUT/code/Sentinel/auditgame
git stash                       # về bản trước batch
python3 dprime_sweep.py --n 40 --json /tmp/BEFORE.json > /tmp/BEFORE.txt
git stash pop
python3 dprime_sweep.py --n 40 --json /tmp/AFTER.json  > /tmp/AFTER.txt
python3 - <<'EOF'
import json
K = ("d_prime","delta","harm_b1","harm_sentinel","dharm","ci_lo","ci_hi",
     "n_feasible","n_total","reason")
s = lambda doc: {d: [{k: c[k] for k in K} for c in cs]
                 for d, cs in doc["cells"].items()}
print(s(json.load(open("/tmp/BEFORE.json"))) == s(json.load(open("/tmp/AFTER.json"))))
EOF
# -> True
```

### 2.2 `policy_curve` — một bản sao **đã khai báo** của `runner.worst_case`

CI95 của `ΔL` cần `L` **theo từng workflow**, tức cần `Q_false` và `T_lost` theo
từng workflow. `runner.GridCell` chỉ giữ hai đại lượng đó ở dạng **trung bình**
(`per_wf` của nó là véc-tơ `harm`), và `runner.py` **đóng băng** trong batch này.
Nên `dprime_sweep.policy_curve` giữ **bản sao** của vòng lặp worst-case — đúng nước
đi mà `make_corpus` đã đi với `experiment.make_corpus`, và **ghim y hệt**:

> `tests/gate1_integrity/test_dprime_sweep.py`
> `::test_the_per_workflow_vectors_reproduce_runner_worst_case_exactly`
> khẳng định **mọi** vô hướng của bản sao **BẰNG** `runner.worst_case` trên cùng
> tham số, cho **cả bốn** policy.

**Vì sao không dịch khoảng tin cậy của `harm` đi một hằng số.** `ΔL` bằng
`Δharm` cộng một lượng phạt; nếu lấy khoảng `harm` rồi dịch, hai số hạng phạt vào
với **phương sai lấy mẫu bằng 0**, khoảng giữ nguyên **bề rộng** của khoảng `harm`.
`d′*` định nghĩa qua **cận dưới**, nên một khoảng hẹp hơn bằng chứng sẽ báo ngưỡng
**THẤP HƠN** mức dữ liệu cho phép. Ghim ở gate 3
(`test_the_loss_interval_is_not_the_harm_interval_shifted_by_a_constant`).

### 2.3 Kẻ tấn công vẫn tối đa hoá `harm`, không phải `L`

`policy_curve` lấy max trên lớp tấn công theo **`harm` trung bình**, đúng như
`runner.worst_case` định nghĩa, rồi đọc hai số hạng phạt tại đúng cấu hình mà lựa
chọn đó rơi vào. Một *worst case dưới `L`* là **một kẻ tấn công khác** và **một
phép đo khác**; không con số đóng băng nào ở đây là như vậy, nên nó không được tính
ở đây. Đây là **giới hạn**, ghi ở §8.

---

## 3. Chế độ `tau_sel` nào là **BẢN CHÍNH** — và vì sao chế độ mặc định **không** phải

`spikes/tau-sel-follows-dprime.md` §6 truy vết lời gọi và cho kết quả **cấu trúc**:
`scoring.tau_sel` chỉ tới được policy qua `policies.Policy.tau`, và `Policy.tau`
**chỉ** được gọi ở `RiskScore.choose` (**B5**) và `TwoStage.choose` (**B6**).

Hệ quả trực tiếp cho **chính batch này**:

* confound "`tau_sel` ghim ở `mid`" **TRƠ** với cặp `(B1, Sentinel)` — nên §2.1 tái
  lập được;
* confound đó **SỐNG** với đúng **hai policy vừa được thêm vào**.

Nó **không nhỏ**. §6 của spike kia đã đo: `harm` của B5 ở `d′ = 3,0` đi
`0,3829` (hàng `mid`) → `0,3649` (hàng `d3.0`, hàng của chính nó) → `0,2027`
(hàng `d0.0`). Một bảng **xếp hạng** Sentinel với B5/B6 mà đọc ngưỡng chọn-carrier
ở `d′ = 2,211` trong khi detector chạy ở `d′` khác thì đang phạt/thưởng B5/B6 vì
một lý do **không liên quan tới policy**.

> **QUYẾT ĐỊNH, ghi rõ:** **bản chính (headline) của mọi bảng `L` trong tài liệu
> này là chế độ `--tau-follows-dprime`** — mỗi điểm quét tra `tau_sel` ở hàng được
> hiệu chỉnh **tại chính `d′` đó**. Chế độ mặc định (`tau_sel` ghim ở `mid`) vẫn
> được chạy và vẫn được báo cáo, với **một** vai trò: **tái lập** cấu hình đã công
> bố (§2.1) và **đối chứng độ nhạy** (§7).

**Giá phải trả của bản chính:** cờ `--tau-follows-dprime` **tắt** bước mịn hoá
0,05 (bảng tham chiếu chỉ có hàng ở lưới thô, và không thể có hàng ở điểm mịn hoá
vì khoảng cần mịn hoá chỉ biết được *sau* khi đo xong lưới thô). Nên `d′*` ở bản
chính đọc ở độ phân giải **0,2**.

---

## 4. Bảng bốn policy — `harm`, `Q_false`, `T_lost`, `spent`, `L`

Bản chính (`--tau-follows-dprime`), 40 workflow, `H = 8`, `B = 17,95`, 3 seed.
Ba điểm `d′` đại diện cho **hai đầu và giữa** lưới; bảng đầy đủ 16 điểm × 4 `Δ` nằm
trong `--json` và in ra `stdout` ở mọi lần chạy.


#### `d' = 0.0`

| `Δ` | policy | `harm` | `Q_false` | `T_lost` | `spent` | `L(0)` | `L(0,10)` | feasible |
|:--:|:--|---:|---:|---:|---:|---:|---:|:--:|
| 0 | `B1 audit-at-commit` | 0.983 | 0.000 | 0.354 | 16.40 | 1.160 | 1.160 | 40/40 |
|  | `Sentinel` | 0.992 | 1.121 | 0.000 | 7.13 | 0.992 | 1.104 | 40/40 |
|  | `B5 risk-score` | 0.992 | 0.000 | 0.000 | 0.00 | 0.992 | 0.992 | 40/40 |
|  | `B6 two-stage` | 0.992 | 1.025 | 0.000 | 3.20 | 0.992 | 1.094 | 40/40 |
| 1 | `B1 audit-at-commit` | 1.000 | 0.000 | 0.308 | 16.40 | 1.154 | 1.154 | 40/40 |
|  | `Sentinel` | 1.000 | 1.096 | 0.000 | 7.41 | 1.000 | 1.110 | 40/40 |
|  | `B5 risk-score` | 1.000 | 0.000 | 0.000 | 0.00 | 1.000 | 1.000 | 40/40 |
|  | `B6 two-stage` | 1.000 | 0.967 | 0.000 | 3.20 | 1.000 | 1.097 | 40/40 |
| 2 | `B1 audit-at-commit` | 0.967 | 0.000 | 0.425 | 16.40 | 1.179 | 1.179 | 40/40 |
|  | `Sentinel` | 0.963 | 1.208 | 0.000 | 7.25 | 0.963 | 1.083 | 40/40 |
|  | `B5 risk-score` | 0.975 | 0.000 | 0.000 | 0.00 | 0.975 | 0.975 | 40/40 |
|  | `B6 two-stage` | 0.963 | 1.062 | 0.000 | 3.20 | 0.963 | 1.069 | 40/40 |
| 4 | `B1 audit-at-commit` | 0.779 | 0.000 | 0.532 | 16.40 | 1.045 | 1.045 | 37/40 |
|  | `Sentinel` | 0.779 | 1.009 | 0.000 | 7.02 | 0.779 | 0.880 | 37/40 |
|  | `B5 risk-score` | 0.779 | 0.000 | 0.000 | 0.00 | 0.779 | 0.779 | 37/40 |
|  | `B6 two-stage` | 0.779 | 0.919 | 0.000 | 3.20 | 0.779 | 0.871 | 37/40 |

#### `d' = 2.2`

| `Δ` | policy | `harm` | `Q_false` | `T_lost` | `spent` | `L(0)` | `L(0,10)` | feasible |
|:--:|:--|---:|---:|---:|---:|---:|---:|:--:|
| 0 | `B1 audit-at-commit` | 0.867 | 0.000 | 0.471 | 16.40 | 1.102 | 1.102 | 40/40 |
|  | `Sentinel` | 0.992 | 1.262 | 0.000 | 8.25 | 0.992 | 1.118 | 40/40 |
|  | `B5 risk-score` | 0.992 | 0.321 | 0.000 | 2.35 | 0.992 | 1.024 | 40/40 |
|  | `B6 two-stage` | 0.992 | 1.171 | 0.000 | 4.85 | 0.992 | 1.109 | 40/40 |
| 1 | `B1 audit-at-commit` | 0.808 | 0.000 | 0.454 | 16.40 | 1.035 | 1.035 | 40/40 |
|  | `Sentinel` | 0.900 | 1.329 | 0.000 | 8.90 | 0.900 | 1.033 | 40/40 |
|  | `B5 risk-score` | 0.817 | 0.250 | 0.000 | 1.40 | 0.817 | 0.842 | 40/40 |
|  | `B6 two-stage` | 0.958 | 1.092 | 0.000 | 4.65 | 0.958 | 1.068 | 40/40 |
| 2 | `B1 audit-at-commit` | 0.821 | 0.000 | 0.467 | 16.40 | 1.054 | 1.054 | 40/40 |
|  | `Sentinel` | 0.804 | 1.271 | 0.000 | 8.43 | 0.804 | 0.931 | 40/40 |
|  | `B5 risk-score` | 0.779 | 0.321 | 0.000 | 1.68 | 0.779 | 0.811 | 40/40 |
|  | `B6 two-stage` | 0.912 | 1.221 | 0.000 | 4.88 | 0.912 | 1.035 | 40/40 |
| 4 | `B1 audit-at-commit` | 0.779 | 0.000 | 0.532 | 16.40 | 1.045 | 1.045 | 37/40 |
|  | `Sentinel` | 0.518 | 1.243 | 0.000 | 8.12 | 0.518 | 0.642 | 37/40 |
|  | `B5 risk-score` | 0.599 | 0.225 | 0.000 | 1.25 | 0.599 | 0.622 | 37/40 |
|  | `B6 two-stage` | 0.721 | 0.914 | 0.000 | 3.77 | 0.721 | 0.812 | 37/40 |

#### `d' = 3.0`

| `Δ` | policy | `harm` | `Q_false` | `T_lost` | `spent` | `L(0)` | `L(0,10)` | feasible |
|:--:|:--|---:|---:|---:|---:|---:|---:|:--:|
| 0 | `B1 audit-at-commit` | 0.783 | 0.000 | 0.533 | 16.40 | 1.050 | 1.050 | 40/40 |
|  | `Sentinel` | 0.992 | 1.262 | 0.000 | 9.10 | 0.992 | 1.118 | 40/40 |
|  | `B5 risk-score` | 0.992 | 0.500 | 0.000 | 4.47 | 0.992 | 1.042 | 40/40 |
|  | `B6 two-stage` | 0.992 | 1.258 | 0.000 | 7.12 | 0.992 | 1.117 | 40/40 |
| 1 | `B1 audit-at-commit` | 0.758 | 0.000 | 0.475 | 16.40 | 0.996 | 0.996 | 40/40 |
|  | `Sentinel` | 0.863 | 1.300 | 0.000 | 10.12 | 0.863 | 0.993 | 40/40 |
|  | `B5 risk-score` | 0.504 | 0.346 | 0.000 | 2.33 | 0.504 | 0.539 | 40/40 |
|  | `B6 two-stage` | 0.946 | 1.212 | 0.000 | 6.54 | 0.946 | 1.067 | 40/40 |
| 2 | `B1 audit-at-commit` | 0.812 | 0.000 | 0.492 | 16.40 | 1.058 | 1.058 | 40/40 |
|  | `Sentinel` | 0.654 | 1.246 | 0.000 | 9.29 | 0.654 | 0.779 | 40/40 |
|  | `B5 risk-score` | 0.621 | 0.367 | 0.000 | 2.70 | 0.621 | 0.657 | 40/40 |
|  | `B6 two-stage` | 0.908 | 1.333 | 0.000 | 6.73 | 0.908 | 1.042 | 40/40 |
| 4 | `B1 audit-at-commit` | 0.779 | 0.000 | 0.532 | 16.40 | 1.045 | 1.045 | 37/40 |
|  | `Sentinel` | 0.342 | 1.185 | 0.000 | 7.92 | 0.342 | 0.461 | 37/40 |
|  | `B5 risk-score` | 0.365 | 0.360 | 0.000 | 1.93 | 0.365 | 0.401 | 37/40 |
|  | `B6 two-stage` | 0.721 | 1.054 | 0.000 | 4.80 | 0.721 | 0.826 | 37/40 |


### 4.1 Bảng chi tiêu — "cùng ngân sách" đúng với **TRẦN**, sai với **SỐ ĐÃ TIÊU**

`metrics.spend_table` đã tồn tại từ B5 và **chưa từng được gọi** từ phép quét này.
Tại điểm lưới khai báo `d′ = 2,2` (bản chính):

| `Δ` | `B1` | `Sentinel` | `B6 two-stage` | `B5 risk-score` | trần |
|:--:|---:|---:|---:|---:|---:|
| **0** | 16,40 (91%) | 8,25 (46%) | 4,85 (27%) | 2,35 (13%) | 17,95 |
| **1** | 16,40 (91%) | 8,90 (50%) | 4,65 (26%) | 1,40 (8%) | 17,95 |
| **2** | 16,40 (91%) | 8,43 (47%) | 4,88 (27%) | 1,68 (9%) | 17,95 |
| **4** | 16,40 (91%) | 8,12 (45%) | 3,77 (21%) | 1,25 (7%) | 17,95 |

Khoảng cách **7 – 13×** giữa `B1` và `B5` tại điểm lưới này. Đọc bảng này **cùng
lúc** với §6/§7: policy đánh bại Sentinel dưới `L` là policy tiêu khoảng **một phần
tư** số tiền Sentinel tiêu và **một phần mười** số tiền `B1` tiêu. Trên **toàn**
lưới, số đã tiêu chạy `B1` **16,40** (91%, không đổi) · `Sentinel` **6,94 – 10,12**
(39 – 56%) · `B6` **3,20 – 7,12** (18 – 40%) · `B5` **0,00 – 4,47** (0 – 25%). Ở
`d′ = 0,0` `B5` tiêu **0,00** — nó **không audit gì cả**, và đó là một sự thật cần
đứng cạnh mọi con số `harm` của nó.

---

## 5. `d′*(Δ)` — dưới `harm` (tái lập) và dưới `L` ở ba mức `λ_Q`

`d′*` vẫn là **đúng định nghĩa đã chốt** trong `dprime_sweep.break_even()`, áp lên
`ΔL = L(B1) − L(Sentinel)` **y hệt** cách nó đang được áp lên `Δharm`.


| `Δ` | `d′*` harm (mặc định, TÁI LẬP) | `d′*` harm (chạy theo `d′`) | `d′*` của `ΔL`, `λ_Q=0` | `d′*` của `ΔL`, `λ_Q=λ̄` | `d′*` của `ΔL`, `λ_Q=0,10` |
|:--:|:--|:--|:--|:--|:--|
| **0** | không có trong [0; 3] | không có trong [0; 3] | không có trong [0; 3] | không có trong [0; 3] | không có trong [0; 3] |
| **1** | không có trong [0; 3] | không có trong [0; 3] | **0.00** | không có trong [0; 3] | không có trong [0; 3] |
| **2** | **2.55** | **2.60** | **0.00** | không có trong [0; 3] | **2.00** |
| **4** | **0.60** | **0.60** | **0.00** | **0.60** | **0.00** |

**Đọc bảng này cho đúng ba việc nó nói.**

1. **Cột `λ_Q = 0` không phải "cùng kết quả cũ".** `L(λ_Q = 0) = harm + 0{,}5·T_lost`,
   và `T_lost` của B1 (patch sạch bị chặn ở cổng commit) là `0,31 … 0,53` trong khi
   `T_lost` của Sentinel là **0,000** ở mọi ô. Nên tính cả số hạng `T_lost`,
   Sentinel hơn B1 **trên toàn lưới** ở `Δ ∈ {1, 2, 4}` — `d′*` tụt về **0,00**.
   Đây là một kết quả **có lợi** cho Sentinel, và nó **chỉ** nói về cặp
   `(B1, Sentinel)`.
2. **Cột `λ_Q = 0,10`** kéo `d′*` của `Δ = 2` về 2,00 và giữ `Δ = 4` ở 0,00, nhưng
   `Δ = 0` và `Δ = 1` **không có** `d′*`.
3. **Cột `λ_Q = λ̄`** đọc ở **trọng số DI ĐỘNG** (mỗi ô ở `λ̄` của chính nó), nên nó
   là một **đường biên**, không phải một đường cong ở trọng số cố định. Ở bản chính
   nó là "không có" ở `Δ ∈ {0, 1, 2}` vì tại đúng `λ̄` hai đường `L` **cắt nhau**,
   `ΔL ≈ 0` và cận dưới không dương được. Đó là điều **phải** xảy ra theo định
   nghĩa của `λ̄`, và nó được ghi đúng như vậy chứ không được làm tròn thành một số.

**Và ba cột này KHÔNG PHẢI câu trả lời của khung bài.** Cả ba đều là phát biểu về
cặp `(B1, Sentinel)`. Câu hỏi quyết định khung bài nằm ở §6.

---

## 6. `λ̄ = λ_Q^*` theo **từng ô** — và ai thắng ở hai bên nó

`λ̄` là `metrics.lambda_q_star` trên **bốn** policy của **chính ô đó**: trọng số
nhỏ nhất `> 0` mà thứ hạng `L` **đổi người dẫn đầu**. `none` nghĩa là **không**
trọng số nào trong `(0; 5]` đổi được thứ hạng — một **câu trả lời**, không phải một
ô trống, và nó **không** được thay bằng 0, bằng 0,10, hay bằng `λ̄` của ô khác.

Ba cột cuối là **trọng số cắt theo CẶP**: `λ_Q` mà tại đó `L` của policy kia bằng
`L` của Sentinel. Đây đúng là đại lượng mà dạng phát biểu tiền-đăng-ký cần —
*"Sentinel hơn X với mọi `λ_Q < λ̄`"*, và ba kết cục của nó
được giữ **TÁCH BẠCH**:

* một số `λ` — hai đường `L` cắt nhau ở đó;
* **`hơn mọi λ_Q`** — Sentinel dẫn ở `λ_Q → 0` và khoảng cách chỉ **nới ra**;
* **`thua từ 0`** — Sentinel đã thua (hoặc hoà, rồi thua với mọi `λ_Q > 0`) ngay
  tại `λ_Q → 0`, nên **không tồn tại** dải `λ_Q` nào để phát biểu.


#### `Δ = 0`

| `d′` | `λ̄` | argmin `L` tại `λ_Q → 0` | argmin ngay trên `λ̄` | argmin tại `λ_Q = 0,10` | Sen vs `B1` | Sen vs `B5` | Sen vs `B6` |
|---:|---:|:--|:--|:--|:--|:--|:--|
| 0.0 | 0.1506 | Sen | B5 | B5 | 0.1506 | **thua từ 0** | **thua từ 0** |
| 0.2 | 0.1296 | Sen | B5 | B5 | 0.1296 | **thua từ 0** | **hơn mọi λ_Q** |
| 0.4 | 0.1350 | Sen | B5 | B5 | 0.1350 | **thua từ 0** | **thua từ 0** |
| 0.6 | 0.1408 | Sen | B5 | B5 | 0.1408 | **thua từ 0** | **thua từ 0** |
| 0.8 | 0.1294 | Sen | B5 | B5 | 0.1294 | **thua từ 0** | **thua từ 0** |
| 1.0 | 0.1164 | Sen | B5 | B5 | 0.1164 | **thua từ 0** | **thua từ 0** |
| 1.2 | 0.1066 | Sen | B5 | B5 | 0.1066 | **thua từ 0** | **thua từ 0** |
| 1.4 | 0.1077 | Sen | B5 | B5 | 0.1077 | **thua từ 0** | **thua từ 0** |
| 1.6 | 0.1010 | Sen | B5 | B5 | 0.1010 | **thua từ 0** | **thua từ 0** |
| 1.8 | 0.0953 | Sen | B5 | B5 | 0.0953 | **thua từ 0** | **thua từ 0** |
| 2.0 | 0.0908 | Sen | B5 | B5 | 0.0908 | **thua từ 0** | **thua từ 0** |
| 2.2 | 0.0875 | Sen | B5 | B5 | 0.0875 | **thua từ 0** | **thua từ 0** |
| 2.4 | 0.0542 | Sen | B5 | B5 | 0.0542 | **thua từ 0** | **thua từ 0** |
| 2.6 | 0.0471 | Sen | B5 | B5 | 0.0471 | **thua từ 0** | **thua từ 0** |
| 2.8 | 0.0462 | Sen | B5 | B5 | 0.0462 | **thua từ 0** | **thua từ 0** |
| 3.0 | 0.0462 | Sen | B5 | B5 | 0.0462 | **thua từ 0** | **thua từ 0** |

#### `Δ = 1`

| `d′` | `λ̄` | argmin `L` tại `λ_Q → 0` | argmin ngay trên `λ̄` | argmin tại `λ_Q = 0,10` | Sen vs `B1` | Sen vs `B5` | Sen vs `B6` |
|---:|---:|:--|:--|:--|:--|:--|:--|
| 0.0 | 0.1407 | Sen | B5 | B5 | 0.1407 | **thua từ 0** | **thua từ 0** |
| 0.2 | 0.1413 | Sen | B5 | B5 | 0.1413 | **thua từ 0** | **thua từ 0** |
| 0.4 | 0.1569 | Sen | B5 | B5 | 0.1569 | **thua từ 0** | **thua từ 0** |
| 0.6 | 0.0097 | Sen | B5 | B5 | 0.1048 | 0.0097 | 0.1538 |
| 0.8 | 0.0415 | Sen | B5 | B5 | 0.1237 | 0.0415 | 0.2903 |
| 1.0 | 0.0405 | Sen | B5 | B5 | 0.1163 | 0.0405 | 0.2250 |
| 1.2 | 0.0429 | Sen | B5 | B5 | 0.1107 | 0.0429 | 0.2128 |
| 1.4 | 0.0328 | Sen | B5 | B5 | 0.1111 | 0.0328 | 0.2069 |
| 1.6 | 0.0157 | Sen | B5 | B5 | 0.0812 | 0.0157 | 0.1818 |
| 1.8 | 0.0042 | Sen | B5 | B5 | 0.0773 | 0.0042 | 0.2292 |
| 2.0 | 0.5362 | B5 | B1 | B5 | 0.0970 | **thua từ 0** | 0.3721 |
| 2.2 | 0.8750 | B5 | B1 | B5 | 0.1019 | **thua từ 0** | 0.2456 |
| 2.4 | 1.1091 | B5 | B1 | B5 | 0.1078 | **thua từ 0** | 0.4474 |
| 2.6 | 1.1953 | B5 | B1 | B5 | 0.1054 | **thua từ 0** | 0.5600 |
| 2.8 | 1.0699 | B5 | B1 | B5 | 0.1109 | **thua từ 0** | 0.8182 |
| 3.0 | 1.4217 | B5 | B1 | B5 | 0.1026 | **thua từ 0** | 0.9524 |

#### `Δ = 2`

| `d′` | `λ̄` | argmin `L` tại `λ_Q → 0` | argmin ngay trên `λ̄` | argmin tại `λ_Q = 0,10` | Sen vs `B1` | Sen vs `B5` | Sen vs `B6` |
|---:|---:|:--|:--|:--|:--|:--|:--|
| 0.0 | 0.0103 | Sen | B6 | B5 | 0.1793 | 0.0103 | **thua từ 0** |
| 0.2 | 0.0126 | Sen | B6 | B5 | 0.1633 | 0.0126 | **thua từ 0** |
| 0.4 | 0.0126 | Sen | B6 | B5 | 0.1633 | 0.0126 | **thua từ 0** |
| 0.6 | 0.0496 | Sen | B5 | B5 | 0.1559 | 0.0496 | 0.1364 |
| 0.8 | 0.0496 | Sen | B5 | B5 | 0.1527 | 0.0496 | 0.1154 |
| 1.0 | 0.0547 | Sen | B5 | B5 | 0.1530 | 0.0547 | 0.1111 |
| 1.2 | 0.0669 | Sen | B5 | B5 | 0.1656 | 0.0669 | 0.5000 |
| 1.4 | 0.0323 | Sen | B5 | B5 | 0.1703 | 0.0323 | 0.3929 |
| 1.6 | 0.0157 | Sen | B5 | B5 | 0.1611 | 0.0157 | 0.3784 |
| 1.8 | 0.0150 | Sen | B5 | B5 | 0.1646 | 0.0150 | 0.6207 |
| 2.0 | 0.0160 | Sen | B5 | B5 | 0.1847 | 0.0160 | 1.6000 |
| 2.2 | 0.8571 | B5 | B1 | B5 | 0.1967 | **thua từ 0** | 2.1667 |
| 2.4 | 0.9157 | B5 | B1 | B5 | 0.2393 | **thua từ 0** | 18.5000 |
| 2.6 | 1.1579 | B5 | B1 | B5 | 0.2748 | **thua từ 0** | **hơn mọi λ_Q** |
| 2.8 | 1.1519 | B5 | B1 | B5 | 0.2862 | **thua từ 0** | 10.6000 |
| 3.0 | 1.1932 | B5 | B1 | B5 | 0.3244 | **thua từ 0** | **hơn mọi λ_Q** |

#### `Δ = 4`

| `d′` | `λ̄` | argmin `L` tại `λ_Q → 0` | argmin ngay trên `λ̄` | argmin tại `λ_Q = 0,10` | Sen vs `B1` | Sen vs `B5` | Sen vs `B6` |
|---:|---:|:--|:--|:--|:--|:--|:--|
| 0.0 | 0.2634 | Sen | B5 | B5 | 0.2634 | **thua từ 0** | **thua từ 0** |
| 0.2 | 1.1923 | B5 | B1 | B5 | 0.2691 | **thua từ 0** | **thua từ 0** |
| 0.4 | 0.2719 | Sen | B5 | B5 | 0.2719 | **thua từ 0** | **thua từ 0** |
| 0.6 | 0.0156 | Sen | B5 | B5 | 0.2826 | 0.0156 | 0.1765 |
| 0.8 | 0.0518 | Sen | B5 | B5 | 0.3038 | 0.0518 | 0.3889 |
| 1.0 | 0.0481 | Sen | B5 | B5 | 0.2963 | 0.0481 | 0.2121 |
| 1.2 | 0.0561 | Sen | B5 | B5 | 0.3092 | 0.0561 | 0.2041 |
| 1.4 | 0.0748 | Sen | B5 | B5 | 0.3347 | 0.0748 | 0.3137 |
| 1.6 | 0.0884 | Sen | B5 | B5 | 0.3295 | 0.0884 | 0.3115 |
| 1.8 | 0.1203 | Sen | B5 | Sen | 0.3559 | 0.1203 | 0.3846 |
| 2.0 | 0.0736 | Sen | B5 | B5 | 0.3559 | 0.0736 | 0.4000 |
| 2.2 | 0.0796 | Sen | B5 | B5 | 0.4239 | 0.0796 | 0.6164 |
| 2.4 | 0.0752 | Sen | B5 | B5 | 0.4413 | 0.0752 | 0.7324 |
| 2.6 | 0.0291 | Sen | B5 | B5 | 0.4924 | 0.0291 | 1.2889 |
| 2.8 | 0.0829 | Sen | B5 | B5 | 0.5465 | 0.0829 | 2.1429 |
| 3.0 | 0.0273 | Sen | B5 | B5 | 0.5932 | 0.0273 | 2.8966 |

### 6.1 Tổng hợp trên cả 64 ô (bản chính, `--tau-follows-dprime`)

| Sentinel đối đầu | thua ngay tại `λ_Q → 0` | hơn ở **mọi** `λ_Q` | có điểm cắt `λ̄` | `λ̄` nhỏ nhất · **trung vị** · lớn nhất | số ô có `λ̄ ≥ 0,10` |
|:--|:--:|:--:|:--:|:--|:--:|
| `B1 audit-at-commit` | **0**/64 | 0/64 | 64/64 | 0,0462 · **0,1529** · 0,5932 | **54**/64 |
| `B5 risk-score` | **33**/64 | **0**/64 | 31/64 | 0,0042 · **0,0415** · 0,1203 | **1**/31 |
| `B6 two-stage` | 24/64 | 3/64 | 37/64 | 0,1111 · **0,3846** · 18,50 | 37/37 |

Và thứ hạng tổng (`argmin L` trên cả bốn policy) ở hai mức minh hoạ. **Ô HOÀ
được tách riêng, không tính cho ai** — xem §6.2:

| | `B1` | `Sentinel` | `B5 risk-score` | `B6 two-stage` |
|:--|:--:|:--:|:--:|:--:|
| `argmin L` **duy nhất** tại `λ_Q = 0` | 0/64 | **28**/64 | 11/64 | 0/64 |
| … và **hoà** tại `λ_Q = 0` (25 ô) | 0 | 24 | 22 | 25 |
| `argmin L` **duy nhất** tại `λ_Q = 0,10` | 0/64 | **1**/64 | **63**/64 | 0/64 |
| … hoà tại `λ_Q = 0,10` | — | — | — | **0 ô: hết hoà** |

### 6.2 HAI CÁI BẪY ĐẾM, tìm ra khi tự soát — và cách chúng được xử lý

**(a) `min()` phá hoà theo thứ tự chèn dict.** Ở `λ_Q = 0`, **25/64** ô có `L` bằng
nhau **tới chữ số cuối** giữa hai hoặc ba policy — ở `Δ = 0` cả `Sentinel`, `B5`,
`B6` đều đứng ở `harm = 0,992` với `T_lost = 0,000`, nên `L(0)` của ba policy bằng
nhau **đúng bằng 0,0**. `min()` trả về policy **chèn trước**, và các curve được
chèn theo thứ tự `POLICIES = (B1, Sentinel, B5, B6)` — tức **mọi ô hoà đều rơi vào
tay Sentinel**. Đếm kiểu đó cho ra "Sentinel thắng 52/64", **gần gấp đôi** con số
thật là **28/64**. Đã sửa: `dprime_sweep.l_winners` trả **danh sách**, bảng in ra
`Sentinel=B5 risk-score=B6 two-stage` ở ô hoà, và ghim bằng gate 2
`ATieForTheBestLossIsReportedAsATieAndNotAsAWin`.

**(b) `metrics.lambda_q_star` KHÔNG THẤY điểm cắt tại đúng 0.** Nó chỉ nhận điểm
cắt trong `(1e-9; 5]`. Ở một ô hoà tại `λ_Q = 0` mà đối thủ có `Q_false` nhỏ hơn
hẳn, thứ hạng đổi **ngay trên 0** nhưng `λ_Q^*` bỏ qua nghiệm `x = 0` và trả về một
giá trị **lớn hơn**, đọc từ một cặp khác. Ví dụ `Δ = 0, d′ = 0,0`: `λ̄ = 0,1506` là
điểm cắt **Sentinel–B1**, trong khi `B5` đã vượt Sentinel với **mọi** `λ_Q > 0`.
`metrics.py` **đóng băng**, nên `λ̄` vẫn được báo cáo **đúng như hàm đó định nghĩa**
(dạng phát biểu tiền-đăng-ký ràng buộc như vậy) — nhưng **trên 25 ô hoà, `λ̄` là một
số ĐỌC TRẦN, không phải dải mà Sentinel thật sự dẫn.** Vì vậy **§7 KHÔNG dựa vào
`λ̄`**: nó dựa vào ba cột **cắt theo cặp** ở §6, nơi cả ba kết cục (`cắt tại λ` /
`hơn mọi λ_Q` / `thua từ 0`, trong đó "thua từ 0" bao gồm cả hoà-tại-0-rồi-thua)
được giữ **tách bạch**. Ghim bằng gate 2
`test_a_tie_at_zero_is_a_place_lambda_q_star_cannot_see_the_flip`.

---

## 7. CÂU TRẢ LỜI CHO KHUNG BÀI

Dạng phát biểu **tiền-đăng-ký** (tiền-đăng-ký v2 §9) và **ràng buộc**:
*"Sentinel **[hơn / không hơn]** X trên `L` với mọi `λ_Q < λ̄`"*, trong đó
`λ̄ = λ_Q^*` là **KẾT QUẢ** chứ không phải một tham số được chọn; `λ_Q = 0` và
`λ_Q = 0,10` là **MINH HOẠ**, không bao giờ là dòng tít.

> ### 7.1 `B5 risk-score` — **KHÔNG HƠN**
>
> **Sentinel KHÔNG hơn `B5 risk-score` trên `L`: không tồn tại `λ̄ > 0` để phát
> biểu.** Trên **33/64** ô, `B5` đã dẫn ngay tại `λ_Q → 0` (kể cả các ô
> hoà tại 0 rồi thua với mọi `λ_Q > 0`, §6.2b); trên 31 ô còn lại,
> điểm cắt Sentinel–B5 có trung vị **`λ̄ = 0,0415`** và lớn nhất **0,1203**, nên
> chỉ **1/31** ô giữ được Sentinel ở trên `B5` tới tận mức minh hoạ `0,10`.
> Trên **toàn lưới**, `Sentinel` **không** hơn `B5` ở **bất kỳ** `λ_Q` nào trên
> **bất kỳ** ô nào (cột "hơn ở mọi `λ_Q`" = **0/64**).

> ### 7.2 `B1 audit-at-commit` — **HƠN**, và dải rộng
>
> **Sentinel hơn `B1 audit-at-commit` trên `L` với mọi `λ_Q < λ̄`, `λ̄` đo được
> trong `[0,0462; 0,5932]`, trung vị `0,1529`.** Sentinel dẫn `B1` tại `λ_Q → 0`
> trên **64/64** ô, và **54/64** ô giữ được điều đó tới `λ_Q = 0,10`. Cơ chế nằm ở
> số hạng `T_lost`: `T_lost` của `B1` là `0,31 … 0,53`, của Sentinel là **0,000** ở
> mọi ô — cổng audit-tại-commit **chặn nhầm patch sạch**, còn Sentinel thì không.
> Đây cũng là lý do `d′*` của `ΔL` ở `λ_Q = 0` tụt về **0,00** (§5).

> ### 7.3 `B6 two-stage` — **HƠN có điều kiện**
>
> **Sentinel hơn `B6 two-stage` trên `L` với mọi `λ_Q < λ̄` trên 40/64 ô, `λ̄` đo
> được trong `[0,1111; 18,50]`, trung vị `0,3846`; trên 24/64 ô còn lại Sentinel
> không hơn ngay từ `λ_Q → 0`.** 24 ô đó là: **15/16 ô của `Δ = 0`**, cộng
> **`d′ ≤ 0,4`** ở cả ba `Δ` còn lại. Đó đúng là vùng `harm` của Sentinel và của
> `B6` **bằng nhau** (`Δ = 0`: cả hai đứng ở `0,992` trên toàn lưới; `d′ ≤ 0,4`:
> detector gần như mù nên không policy nào tách được ra), nên `ΔL` tại `λ_Q → 0`
> **bằng 0** và toàn bộ thứ hạng do số hạng `Q_false` quyết định — mà Sentinel
> cách ly nhiều hơn `B6` (`1,12` so với `1,03` ở `Δ = 0, d′ = 0,0`). **Ở đâu hai
> bên còn phân biệt được bằng `harm`, Sentinel hơn `B6` và hơn với biên rộng**
> (mọi điểm cắt đều `≥ 0,1111`, tức **trên** mức minh hoạ `0,10`).

### 7.4 Nói gọn lại — cái này quyết định khung bài nào được viết

**Khung "Sentinel là policy tốt nhất" KHÔNG chống đỡ được.** Cái đánh bại nó không
phải `B6` (hai cài đặt độc lập báo `B6` hơn Sentinel — **kết quả ở đây KHÔNG xác
nhận điều đó**, §7.3), mà là **`B5 risk-score`**, và biên thua **không mỏng**: `B5`
dẫn trên **63/64** ô ở mức `λ_Q = 0,10`, trong khi **tiêu 0,00 – 4,47** trên trần
17,95 (**0 – 25%**) so với **6,94 – 10,12** (**39 – 56%**) của Sentinel (§4.1).

**Cái vẫn đứng vững là một phát biểu hẹp hơn và đúng hơn:** Sentinel hơn `B1` —
đường cơ sở mà luận văn đang so — trên `L` **với mọi `λ_Q` dưới một `λ̄` đo được,
trung vị `0,1529`**, và cơ chế là `T_lost` chứ không phải `harm`.

### 7.5 Kết quả này **nhạy** hay **trơ** với chế độ `tau_sel`?

Chạy lại toàn bộ ở chế độ **mặc định** (`tau_sel` ghim ở `mid` — chế độ mà §3 nói là
**confound sống** với B5/B6) cho **cùng một kết luận**, không phải cùng con số:

| | bản chính (`d′`-theo-quét) | mặc định (ghim `mid`) |
|:--|:--|:--|
| ô | 64 | 70 (có mịn hoá) |
| Sen thua `B5` ngay tại `λ_Q → 0` | 33/64 | 31/70 |
| Sen hơn `B5` ở **mọi** `λ_Q` | **0**/64 | **0**/70 |
| điểm cắt Sen–B5, trung vị | 0,0415 | 0,0358 |
| `argmin L` **duy nhất** tại `λ_Q = 0` | Sen 28 · `B5` 11 · hoà 25 | Sen 36 · `B5` 11 · hoà 23 |
| `argmin L` tại `λ_Q = 0,10` (không còn ô hoà) | `B5` trên **63/64** | `B5` trên **69/70** |
| điểm cắt Sen–B1, trung vị | 0,1529 | 0,1590 |

Phán quyết §7.1 **không** phụ thuộc vào việc chọn chế độ nào. Nó được báo cáo từ
bản chính vì đó là chế độ mà ngưỡng của **mọi** policy được hiệu chỉnh tại `d′` mà
detector của chính nó đang chạy (§3); chế độ mặc định đứng đây làm **đối chứng độ
nhạy**.

---

## 8. Giới hạn

1. **Kẻ tấn công tối đa hoá `harm`, không phải `L`** (§2.3). `worst_case` dưới `L`
   là một phép đo khác và **chưa** được thực hiện. Nếu kẻ tấn công biết lái theo
   `Q_false`, mọi con số `L` ở đây là **cận dưới** của tổn thất.
2. **Bản chính không mịn hoá được** (§3): `d′*` đọc ở độ phân giải 0,2. Cột `d′*`
   `harm` của chế độ mặc định (2,55) và bản chính (2,60) **không** so trực tiếp
   được; so đúng là trên lưới thô, ở đó cả hai đều 2,60.
3. **Cột `λ_Q = λ̄` là đường biên, không phải đường cong trọng số cố định** (§5.3):
   trọng số **di động** theo từng ô. Hai cột `0` và `0,10` mới là cột đọc ở một
   trọng số.
4. **`λ_T = 0,50` không được quét.** Nó là hằng số `metrics.LAMBDA_T`, và giống
   `λ_Q` trước batch này, nó là **một tham số chưa có kết quả đi kèm**. Việc riêng.
5. **Mock agent**, oracle marker-AST, 40 workflow, `H = 8`, 3 seed, corpus seed
   `2026` — y như `dprime-sweep.md` §10.3–§10.4, không đổi.
6. **`harm` bão hoà với ba policy đọc điểm ở `Δ = 0`.** Trên **toàn** lưới
   `Δ = 0`, `Sentinel`, `B5` và `B6` đều đứng ở `harm = 0,992` — chỉ `B1` nhúc
   nhích (`0,983 → 0,783`). Ở đó `L` của ba policy kia **chỉ còn** số hạng
   `Q_false` và thứ hạng là thứ hạng của "ai cách ly ít nhất", **không** phải một
   phát biểu về phân bổ audit. Điều tương tự xảy ra ở `d′ ≤ 0,4` của mọi `Δ`, nơi
   detector gần như mù. Đọc §7.3 với điều đó trong đầu.
7. **`B5` ở `d′ = 0,0` tiêu `0,00`** — nó không audit gì cả. Đó là một policy hợp
   lệ dưới `L`, nhưng nó **không đo được** điều gì về chất lượng phân bổ ngân sách;
   nó chỉ nói rằng ở `λ_Q` đủ lớn, **không làm gì** là một lựa chọn tốt. Đây là
   cùng một họ với kết quả `NC1` của Toàn-cảnh §A.4, theo chiều ngược lại.

---

## 9. Tái lập — lệnh và seed cho **từng** con số

Mọi thứ chạy trên **mock agent**, không tốn LLM. Từ `HCMUT/code/Sentinel/auditgame`:

```bash
# BẢN CHÍNH -- mọi bảng §4, §5, §6, §7 (trừ cột "mặc định" của §7.5)
python3 dprime_sweep.py --n 40 --tau-follows-dprime --json /tmp/sweep-L-follows.json

# ĐỐI CHỨNG + TÁI LẬP đường cong harm đã công bố -- §2.1 và cột phải của §7.5
python3 dprime_sweep.py --n 40 --json /tmp/sweep-L-pinned.json
```

Tham số **cố định** của cả hai lệnh, đọc thẳng từ khối `run` của file `--json`:

| | |
|---|---|
| corpus | 40 workflow, `H = 8`, `corpus_seed = 2026` (`dprime_sweep.CORPUS_SEED`) |
| seed chạy | `(1, 2, 3)` |
| ngân sách | `B = 17,95` (trần; số đã tiêu ở §4.1) |
| `τ_det` | `1.17498679206609` **CỐ ĐỊNH** ⇒ `φ = Φ(−τ_det) = 0,12` ở **mọi** điểm |
| lưới | `d′ ∈ {0,0; 0,2; …; 3,0}`, 16 điểm |
| `Δ` | `(0, 1, 2, 4)` — **báo cáo theo từng ô, KHÔNG GỘP** |
| carrier | `memory, skill, queue, branch` |
| `λ_T` | `metrics.LAMBDA_T = 0,50` |
| `λ_Q` minh hoạ | `metrics.LAMBDA_Q = 0,10` |
| `λ̄` | `metrics.lambda_q_star`, **đo theo từng ô**, `hi = 5,0` |
| CI95 | `runner.bootstrap_paired`, `n_boot = 10000`, `seed = 2026`, đơn vị = **workflow** |

Số nào lấy từ đâu:

| Mục | Nguồn |
|---|---|
| §2.1 tái lập | so `cells` của hai lần chạy mặc định, đoạn script in ngay trong §2.1 |
| §4 bảng bốn policy | `cells[Δ][i].curves[policy]` trong `/tmp/sweep-L-follows.json` |
| §4.1 bảng chi tiêu | `metrics.spend_table`, in ra `stdout` dưới nhãn `budget CONSUMED at the declared reference d' = 2.2` |
| §5 `d′*` | khối `break_even` của file `--json`, và các dòng `d'* of d-L` trên `stdout` |
| §6 `λ̄` từng ô | `metrics.lambda_q_star` trên `curves` của ô; cũng in ở cột `lambda-bar` của bảng bốn policy |
| §6 cắt theo cặp | `dh = (harm_o − harm_s) + λ_T (T_o − T_s)`, `dq = Q_o − Q_s`, `λ = −dh/dq` khi `dq < 0`; ba kết cục giữ tách bạch (§6) |
| §6.1, §7 tổng hợp | đếm trên đúng 64 ô của `/tmp/sweep-L-follows.json` |
| §7.5 cột mặc định | `/tmp/sweep-L-pinned.json` (70 ô: 16 điểm thô + mịn hoá) |

### 9.1 Bất biến & cổng

- **`md5` hai đường `experiment.py` KHÔNG đổi**: `--n 20` =
  `5655bd4956206148c3744045e3d17f61`; `--dataset swebench --n 20` =
  `2140bbe796ce925a19631a1c7a88f5e0` (xác nhận sau batch).
- **Đường cong `harm` đã công bố không xê dịch một chữ số** (§2.1);
  `d′*` dưới `harm` vẫn **không có / không có / 2,55 / 0,60**.
- `metrics.py`, `runner.py`, `scoring.py`, `oracle.py`, `detector.py`,
  `policies.py` — **không sửa một dòng nào**.
- Ba cổng xanh: **447 / 111 / 14**, **zero skip** (tăng từ 444 / 100 / 9 — 19 test
  mới: 3 ở gate 1, 11 ở gate 2, 5 ở gate 3).
- **Hai cái bẫy đếm ở §6.2 được tìm ra khi TỰ SOÁT, không phải bởi một test đỏ.**
  Cái (a) đã được **sửa trong code** và ghim bằng test; cái (b) nằm trong
  `metrics.py` **đóng băng**, nên nó được **khai báo** và kết luận §7 được dựng để
  **không đi qua nó**. Con số "Sentinel dẫn 52/64 ô" của bản nháp đầu là **SAI** và
  không được trích ở đâu nữa — số đúng là **28/64 duy nhất + 24 ô hoà**.
- N3 giữ nguyên qua trục chấm điểm mới: một ô không dựng được attack, **và** một ô
  không có `λ̄`, đều mang **LÝ DO** và đều **chặn** phép quét `d′*` — không ô nào bị
  bỏ qua im lặng, không ô nào bị gán `harm = 0` hay một `λ_Q` đi mượn.
