# Chấm điểm phép quét $d'$ bằng hàm mất mát $L$ trên Payload v2 — Bốn Policy

**Ngày đo:** 19/09/2026 · **Module:** `dprime_sweep.py`
**Dữ liệu:** `spikes/sweep-v2-following.json` (bản chính) và `spikes/sweep-v2-pinned.json` (đối chứng ghim)
**Thay thế:** Phán quyết v1 tại `docs/reports/sweep-loss-b5-b6.md` theo nguyên tắc tiền-đăng-ký.

> **ĐỌC BA DÒNG NÀY TRƯỚC.**
> 1. **Số v2 THAY số v1, KHÔNG CHỌN.** Sau khi sửa bug `MatchedAttack` ở Task A1a, kết quả đo lường v2 hoàn toàn thay thế v1.
> 2. **Sentinel KHÔNG hơn `B5 risk-score` trên $L$:** B5 dẫn trước trên **61/64** ô ở $\lambda_Q = 0,10$ và chỉ tiêu **7–13%** ngân sách so với 47–50% của Sentinel. Sentinel chỉ thắng B5 ở $\Delta = 4, d' \in [2,4; 2,8]$ khi $\lambda_Q \le 0,10$.
> 3. **Phát biểu duy nhất còn sống (Sentinel hơn B1) TREO vào $\lambda_T = 0,50$:** Ở $\lambda_T = 0$ (không phạt chặn nhầm patch sạch), số ô Sentinel dẫn trước co từ **64/64** xuống **26/64** ô (§7.2.1).

---

## 1. Nguyên tắc chốt TRƯỚC khi chạy (Pre-commitment)

1. **Số v2 THAY số v1, KHÔNG CHỌN:** Mọi con số v2 được ghi nhận trung thực theo thực nghiệm, không giữ lại con số thuận lợi từ v1.
2. **Luật so sánh ghép cặp (Common Random Numbers):** So sánh ghép cặp nội bộ trong từng phiên bản (cùng seed, cùng cấu hình payload v2). Tuyệt đối không so sánh chéo giữa v1 và v2.
3. **Hai chế độ đo:**
   - **Bản chính (`--tau-follows-dprime`):** $\tau_{\text{sel}}$ chạy theo từng điểm lưới $d'$, loại bỏ confound cố định ngưỡng chọn carrier cho B5/B6.
   - **Đối chứng ghim (`pinned`):** $\tau_{\text{sel}}$ ghim ở mức `mid` ($d' = 2,211$) để đối chiếu độ nhạy.
4. **Hàm mục tiêu phòng thủ:**
   $$L = \mathbb{E}[\text{harm}] + \lambda_Q \mathbb{E}[Q_{\text{false}}] + \lambda_T \mathbb{E}[T_{\text{lost}}]$$
   với $\lambda_T = 0,50$ và quét $\lambda_Q$.

---

## 2. Thiết lập thực nghiệm v2

| Đại lượng | Giá trị / Quy cách | Ghi chú |
|:---|:---|:---|
| Bốn policy so sánh | `B1 audit-at-commit`, `Sentinel`, `B5 risk-score`, `B6 two-stage` | Khai báo trong `policies.REGISTRY` |
| Lưới $d'$ | `[0.0, 0.2, 0.4, ..., 3.0]` (16 điểm) | Bản chính chạy lưới thô step 0.2 |
| Độ dịch $\Delta$ | `[0, 1, 2, 4]` | 4 mức độ dịch marker |
| Số workflow / seed | 40 workflow, $H=8$, seed `[1, 2, 3]` | 64 ô đánh giá (16 × 4) |
| Trần ngân sách | $B = 17,95$ | Chung cho cả 4 policy |
| Bug sửa ở A1a | `MatchedAttack.payload` gọi `build.payload_content` | Đúng `PAYLOAD_LENGTH = 63`, loại bỏ chênh lệch kích thước nhân tạo |

---

## 3. Bảng bốn policy — `harm`, `Q_false`, `T_lost`, `spent`, `L`

Dưới đây là kết quả đo lường tại ba điểm $d'$ đại diện (hai đầu và giữa lưới) ở bản chính (`--tau-follows-dprime`):

#### $d' = 0.0$

| $\Delta$ | Policy | `harm` | `Q_false` | `T_lost` | `spent` | $L(0)$ | $L(0,10)$ | Feasible |
|:--:|:---|---:|---:|---:|---:|---:|---:|:--:|
|  0   | `B1 audit-at-commit` | 0.983 | 0.000 | 0.354 | 16.40 | 1.160 | 1.160 |  40/40   |
|      | `Sentinel` | 0.992 | 1.121 | 0.000 | 7.13 | 0.992 | 1.104 |  40/40   |
|      | `B5 risk-score` | 0.992 | 0.000 | 0.000 | 0.00 | 0.992 | 0.992 |  40/40   |
|      | `B6 two-stage` | 0.992 | 1.025 | 0.000 | 3.20 | 0.992 | 1.094 |  40/40   |
|  1   | `B1 audit-at-commit` | 1.000 | 0.000 | 0.308 | 16.40 | 1.154 | 1.154 |  40/40   |
|      | `Sentinel` | 0.983 | 1.104 | 0.000 | 7.35 | 0.983 | 1.094 |  40/40   |
|      | `B5 risk-score` | 1.000 | 0.000 | 0.000 | 0.00 | 1.000 | 1.000 |  40/40   |
|      | `B6 two-stage` | 1.000 | 0.992 | 0.000 | 3.20 | 1.000 | 1.099 |  40/40   |
|  2   | `B1 audit-at-commit` | 0.967 | 0.000 | 0.425 | 16.40 | 1.179 | 1.179 |  40/40   |
|      | `Sentinel` | 0.963 | 1.204 | 0.000 | 7.18 | 0.963 | 1.083 |  40/40   |
|      | `B5 risk-score` | 0.975 | 0.000 | 0.000 | 0.00 | 0.975 | 0.975 |  40/40   |
|      | `B6 two-stage` | 0.967 | 1.021 | 0.000 | 3.20 | 0.967 | 1.069 |  40/40   |
|  4   | `B1 audit-at-commit` | 0.779 | 0.000 | 0.532 | 16.40 | 1.045 | 1.045 |  37/40   |
|      | `Sentinel` | 0.766 | 0.995 | 0.000 | 7.00 | 0.766 | 0.865 |  37/40   |
|      | `B5 risk-score` | 0.779 | 0.000 | 0.000 | 0.00 | 0.779 | 0.779 |  37/40   |
|      | `B6 two-stage` | 0.779 | 0.919 | 0.000 | 3.20 | 0.779 | 0.871 |  37/40   |

#### $d' = 2.2$

| $\Delta$ | Policy | `harm` | `Q_false` | `T_lost` | `spent` | $L(0)$ | $L(0,10)$ | Feasible |
|:--:|:---|---:|---:|---:|---:|---:|---:|:--:|
|  0   | `B1 audit-at-commit` | 0.867 | 0.000 | 0.471 | 16.40 | 1.102 | 1.102 |  40/40   |
|      | `Sentinel` | 0.992 | 1.208 | 0.000 | 8.44 | 0.992 | 1.113 |  40/40   |
|      | `B5 risk-score` | 0.992 | 0.408 | 0.000 | 2.82 | 0.992 | 1.033 |  40/40   |
|      | `B6 two-stage` | 0.992 | 1.258 | 0.000 | 5.57 | 0.992 | 1.118 |  40/40   |
|  1   | `B1 audit-at-commit` | 0.808 | 0.000 | 0.454 | 16.40 | 1.035 | 1.035 |  40/40   |
|      | `Sentinel` | 0.917 | 1.358 | 0.000 | 8.99 | 0.917 | 1.052 |  40/40   |
|      | `B5 risk-score` | 0.871 | 0.329 | 0.000 | 2.06 | 0.871 | 0.904 |  40/40   |
|      | `B6 two-stage` | 0.975 | 1.133 | 0.000 | 4.91 | 0.975 | 1.088 |  40/40   |
|  2   | `B1 audit-at-commit` | 0.821 | 0.000 | 0.467 | 16.40 | 1.054 | 1.054 |  40/40   |
|      | `Sentinel` | 0.808 | 1.375 | 0.000 | 8.94 | 0.808 | 0.946 |  40/40   |
|      | `B5 risk-score` | 0.829 | 0.338 | 0.000 | 1.95 | 0.829 | 0.863 |  40/40   |
|      | `B6 two-stage` | 0.925 | 1.242 | 0.000 | 4.80 | 0.925 | 1.049 |  40/40   |
|  4   | `B1 audit-at-commit` | 0.779 | 0.000 | 0.532 | 16.40 | 1.045 | 1.045 |  37/40   |
|      | `Sentinel` | 0.563 | 1.207 | 0.000 | 8.38 | 0.563 | 0.684 |  37/40   |
|      | `B5 risk-score` | 0.640 | 0.324 | 0.000 | 1.23 | 0.640 | 0.672 |  37/40   |
|      | `B6 two-stage` | 0.730 | 0.955 | 0.000 | 4.17 | 0.730 | 0.825 |  37/40   |

#### $d' = 3.0$

| $\Delta$ | Policy | `harm` | `Q_false` | `T_lost` | `spent` | $L(0)$ | $L(0,10)$ | Feasible |
|:--:|:---|---:|---:|---:|---:|---:|---:|:--:|
|  0   | `B1 audit-at-commit` | 0.783 | 0.000 | 0.533 | 16.40 | 1.050 | 1.050 |  40/40   |
|      | `Sentinel` | 0.992 | 1.267 | 0.000 | 9.06 | 0.992 | 1.118 |  40/40   |
|      | `B5 risk-score` | 0.992 | 0.533 | 0.000 | 4.61 | 0.992 | 1.045 |  40/40   |
|      | `B6 two-stage` | 0.992 | 1.242 | 0.000 | 7.02 | 0.992 | 1.116 |  40/40   |
|  1   | `B1 audit-at-commit` | 0.758 | 0.000 | 0.475 | 16.40 | 0.996 | 0.996 |  40/40   |
|      | `Sentinel` | 0.871 | 1.325 | 0.000 | 10.25 | 0.871 | 1.003 |  40/40   |
|      | `B5 risk-score` | 0.629 | 0.358 | 0.000 | 2.65 | 0.629 | 0.665 |  40/40   |
|      | `B6 two-stage` | 0.958 | 1.163 | 0.000 | 6.62 | 0.958 | 1.075 |  40/40   |
|  2   | `B1 audit-at-commit` | 0.812 | 0.000 | 0.492 | 16.40 | 1.058 | 1.058 |  40/40   |
|      | `Sentinel` | 0.675 | 1.242 | 0.000 | 9.72 | 0.675 | 0.799 |  40/40   |
|      | `B5 risk-score` | 0.642 | 0.429 | 0.000 | 2.49 | 0.642 | 0.685 |  40/40   |
|      | `B6 two-stage` | 0.912 | 1.313 | 0.000 | 6.33 | 0.912 | 1.044 |  40/40   |
|  4   | `B1 audit-at-commit` | 0.779 | 0.000 | 0.532 | 16.40 | 1.045 | 1.045 |  37/40   |
|      | `Sentinel` | 0.360 | 1.149 | 0.000 | 8.74 | 0.360 | 0.475 |  37/40   |
|      | `B5 risk-score` | 0.423 | 0.392 | 0.000 | 1.86 | 0.423 | 0.463 |  37/40   |
|      | `B6 two-stage` | 0.730 | 1.050 | 0.000 | 5.02 | 0.730 | 0.835 |  37/40   |

---

## 4. Bảng chi tiêu (Spend Table) tại $d' = 2,2$

Chi tiêu thực tế của các policy tại điểm tham chiếu $d' = 2,2$:

| $\Delta$ | `B1 audit-at-commit` | `Sentinel` | `B6 two-stage` | `B5 risk-score` | Trần ngân sách |
|:--:|---:|---:|---:|---:|---:|
| **0** | 16.40 (91%) | 8.44 (47%) | 5.57 (31%) | 2.82 (16%) | 17.95 |
| **1** | 16.40 (91%) | 8.99 (50%) | 4.91 (27%) | 2.06 (12%) | 17.95 |
| **2** | 16.40 (91%) | 8.94 (50%) | 4.80 (27%) | 1.95 (11%) | 17.95 |
| **4** | 16.40 (91%) | 8.38 (47%) | 4.17 (23%) | 1.23 (7%) | 17.95 |

> **Nhận xét then chốt:** `B5 risk-score` chỉ tiêu **7% – 16%** trần ngân sách ($1,23$ đến $2,82$), bằng khoảng **1/4 đến 1/7** chi phí của Sentinel ($8,38$ đến $8,94$), trong khi đạt điểm mất mát $L$ tốt hơn hẳn ở $\lambda_Q \ge 0,10$.

---

## 5. $d'^*(\Delta)$ — Dưới `harm` và dưới $L$ ở ba mức $\lambda_Q$

So sánh ngưỡng hoà vốn $d'^*$ xác định bởi quy tắc frozen `break_even`:

| $\Delta$ | $d'^*$ harm (pinned) | $d'^*$ harm (following) | $d'^*$ của $\Delta L, \lambda_Q=0$ | $d'^*$ của $\Delta L, \lambda_Q=\bar{\lambda}$ | $d'^*$ của $\Delta L, \lambda_Q=0,10$ |
|:--:|:---|:---|:---|:---|:---|
| **0** | không có trong [0; 3] | không có trong [0; 3] | không có trong [0; 3] | không có trong [0; 3] | không có trong [0; 3] |
| **1** | không có trong [0; 3] | không có trong [0; 3] | **0.00** | không có trong [0; 3] | không có trong [0; 3] |
| **2** | **2.85** | **3.00** | **0.00** | không có trong [0; 3] | **2.40** |
| **4** | **0.95** | **1.00** | **0.00** | **0.00** | **0.00** |

### Thay đổi so với v1:
- Tại $\Delta = 2$, $d'^*$ harm dịch từ **2.55** (v1) lên **2.85** (pinned) / **3.00** (following).
- Tại $\Delta = 2$, $d'^*$ của $\Delta L$ ở $\lambda_Q = 0,10$ dịch từ **2.00** (v1) lên **2.40** (v2).
- Tại $\Delta = 4$, $d'^*$ harm dịch từ **0.60** (v1) lên **0.95** (pinned) / **1.00** (following). $d'^*$ của $\Delta L$ ở $\lambda_Q = 0,10$ giữ nguyên **0.00**.
- Tại $\Delta = 0$ và $\Delta = 1$, không tồn tại $d'^*$ hoà vốn trên toàn dải [0, 3] dưới harm hay $\lambda_Q = 0,10$.

---

## 6. $\bar{\lambda}$ và $\lambda_{\times}$ theo từng ô (In trực tiếp từ công cụ)

- $\bar{\lambda} = \lambda_Q^*$ là nghiệm nhỏ nhất trên cả 4 policy.
- $\lambda_{\times}$ là điểm cắt theo từng cặp.

### $\Delta = 0$

```
  lambda-bar = metrics.lambda_q_star over all four policies  |  lambda-cross = the pairwise Sentinel-vs-X crossing
  policy keys abbreviated: B1 = B1 audit-at-commit, Sentinel = Sentinel, B5 = B5 risk-score, B6 = B6 two-stage
  d-prime  lambda-bar  argmin L @ lambda_Q = 0   argmin L @ lambda-bar+  argmin L @ lambda_Q=0.1                    Sen vs B1                 Sen vs B5                 Sen vs B6
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
     0.00      0.1506  Sentinel=B5=B6            B5                      B5                                            0.1506            behind from 0+            behind from 0+
     0.20      0.1305  Sentinel=B5=B6            B5                      B5                                            0.1305            behind from 0+   ahead at every lambda_Q
     0.40      0.1360  Sentinel=B5=B6            B5                      B5                                            0.1360            behind from 0+   ahead at every lambda_Q
     0.60      0.1408  Sentinel=B5=B6            B5                      B5                                            0.1408            behind from 0+            behind from 0+
     0.80      0.1350  Sentinel=B5=B6            B5                      B5                                            0.1350            behind from 0+            behind from 0+
     1.00      0.1189  Sentinel=B5=B6            B5                      B5                                            0.1189            behind from 0+            behind from 0+
     1.20      0.1066  Sentinel=B5=B6            B5                      B5                                            0.1066            behind from 0+            behind from 0+
     1.40      0.1123  Sentinel=B5=B6            B5                      B5                                            0.1123            behind from 0+            behind from 0+
     1.60      0.1045  Sentinel=B5=B6            B5                      B5                                            0.1045            behind from 0+            behind from 0+
     1.80      0.0983  Sentinel=B5=B6            B5                      B5                                            0.0983            behind from 0+            behind from 0+
     2.00      0.0955  Sentinel=B5=B6            B5                      B5                                            0.0955            behind from 0+            behind from 0+
     2.20      0.0914  Sentinel=B5=B6            B5                      B5                                            0.0914            behind from 0+   ahead at every lambda_Q
     2.40      0.0552  Sentinel=B5=B6            B5                      B5                                            0.0552            behind from 0+   ahead at every lambda_Q
     2.60      0.0479  Sentinel=B5=B6            B5                      B5                                            0.0479            behind from 0+   ahead at every lambda_Q
     2.80      0.0458  Sentinel=B5=B6            B5                      B5                                            0.0458            behind from 0+            behind from 0+
     3.00      0.0461  Sentinel=B5=B6            B5                      B5                                            0.0461            behind from 0+            behind from 0+
```

### $\Delta = 1$

```
  lambda-bar = metrics.lambda_q_star over all four policies  |  lambda-cross = the pairwise Sentinel-vs-X crossing
  policy keys abbreviated: B1 = B1 audit-at-commit, Sentinel = Sentinel, B5 = B5 risk-score, B6 = B6 two-stage
  d-prime  lambda-bar  argmin L @ lambda_Q = 0   argmin L @ lambda-bar+  argmin L @ lambda_Q=0.1                    Sen vs B1                 Sen vs B5                 Sen vs B6
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
     0.00      0.0151  Sentinel                  B5                      B5                                            0.1547                    0.0151                    0.1481
     0.20      0.0201  Sentinel                  B5                      B5                                            0.1581                    0.0201                    0.2667
     0.40      0.0201  Sentinel                  B5                      B5                                            0.1728                    0.0201                    0.2353
     0.60      0.0101  Sentinel                  B5                      B5                                            0.1147                    0.0101                    0.1538
     0.80      0.0099  Sentinel                  B5                      B5                                            0.1113                    0.0099                    0.1429
     1.00      0.0100  Sentinel                  B5                      B5                                            0.1029                    0.0100                    0.0769
     1.20      0.0137  Sentinel                  B5                      B5                                            0.1060                    0.0137                    0.1923
     1.40      0.0182  Sentinel                  B5                      B5                                            0.1224                    0.0182                    0.2759
     1.60      0.0083  Sentinel                  B5                      B5                                            0.0893                    0.0083                    0.1860
     1.80      0.5164  B5                        B1                      B5                                            0.0891            behind from 0+                    0.2222
     2.00      0.5692  B5                        B1                      B5                                            0.0942            behind from 0+                    0.2456
     2.20      0.5000  B5                        B1                      B5                                            0.0874            behind from 0+                    0.2593
     2.40      0.4568  B5                        B1                      B5                                            0.0798            behind from 0+                    0.2593
     2.60      0.6118  B5                        B1                      B5                                            0.1048            behind from 0+                    0.5833
     2.80      0.9276  B5                        B1                      B5                                            0.1124            behind from 0+                    0.7500
     3.00      1.0233  B5                        B1                      B5                                            0.0943            behind from 0+                    0.5385
```

### $\Delta = 2$

```
  lambda-bar = metrics.lambda_q_star over all four policies  |  lambda-cross = the pairwise Sentinel-vs-X crossing
  policy keys abbreviated: B1 = B1 audit-at-commit, Sentinel = Sentinel, B5 = B5 risk-score, B6 = B6 two-stage
  d-prime  lambda-bar  argmin L @ lambda_Q = 0   argmin L @ lambda-bar+  argmin L @ lambda_Q=0.1                    Sen vs B1                 Sen vs B5                 Sen vs B6
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
     0.00      0.0104  Sentinel                  B5                      B5                                            0.1799                    0.0104                    0.0227
     0.20      0.0126  Sentinel                  B5                      B5                                            0.1689                    0.0126                    0.0312
     0.40      0.0122  Sentinel                  B5                      B5                                            0.1689                    0.0122                    0.0312
     0.60      0.0122  Sentinel                  B5                      B5                                            0.1310                    0.0122                    0.0294
     0.80      0.0169  Sentinel                  B5                      B5                                            0.1287                    0.0169                    0.1071
     1.00      0.0161  Sentinel                  B5                      B5                                            0.1345                    0.0161                    0.1220
     1.20      0.0206  Sentinel                  B5                      B5                                            0.1313                    0.0206                    0.1818
     1.40      0.0369  Sentinel                  B5                      B5                                            0.1498                    0.0369                    0.4091
     1.60      0.0321  Sentinel                  B5                      B5                                            0.1444                    0.0321                    0.2973
     1.80      0.0462  Sentinel                  B5                      B5                                            0.1609                    0.0462                    0.6538
     2.00      0.0638  Sentinel                  B5                      B5                                            0.1841                    0.0638                    1.1818
     2.20      0.0201  Sentinel                  B5                      B5                                            0.1788                    0.0201                    0.8750
     2.40      0.0349  Sentinel                  B5                      B5                                            0.2253                    0.0349                    1.4074
     2.60      0.0039  Sentinel                  B5                      B5                                            0.2294                    0.0039                    1.1622
     2.80      0.9444  B5                        B1                      B5                                            0.2500            behind from 0+                    4.8889
     3.00      0.9709  B5                        B1                      B5                                            0.3087            behind from 0+   ahead at every lambda_Q
```

### $\Delta = 4$

```
  lambda-bar = metrics.lambda_q_star over all four policies  |  lambda-cross = the pairwise Sentinel-vs-X crossing
  policy keys abbreviated: B1 = B1 audit-at-commit, Sentinel = Sentinel, B5 = B5 risk-score, B6 = B6 two-stage
  d-prime  lambda-bar  argmin L @ lambda_Q = 0   argmin L @ lambda-bar+  argmin L @ lambda_Q=0.1                    Sen vs B1                 Sen vs B5                 Sen vs B6
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
     0.00      0.0136  Sentinel                  B5                      B5                                            0.2805                    0.0136                    0.1765
     0.20      0.0191  Sentinel                  B5                      B5                                            0.2805                    0.0191   ahead at every lambda_Q
     0.40      0.0244  Sentinel                  B5                      B5                                            0.2851                    0.0244   ahead at every lambda_Q
     0.60      0.0333  Sentinel                  B5                      B5                                            0.2902                    0.0333                    1.2000
     0.80      0.0161  Sentinel                  B5                      B5                                            0.2766                    0.0161                    0.5455
     1.00      0.0145  Sentinel                  B5                      B5                                            0.2694                    0.0145                    0.2143
     1.20      0.0249  Sentinel                  B5                      B5                                            0.2810                    0.0249                    0.2286
     1.40      0.0524  Sentinel                  B5                      B5                                            0.2879                    0.0524                    0.2340
     1.60      0.0343  Sentinel                  B5                      B5                                            0.3020                    0.0343                    0.1897
     1.80      0.0526  Sentinel                  B5                      B5                                            0.3281                    0.0526                    0.3617
     2.00      0.0357  Sentinel                  B5                      B5                                            0.3523                    0.0357                    0.3966
     2.20      0.0867  Sentinel                  B5                      B5                                            0.3993                    0.0867                    0.6607
     2.40      0.1042  Sentinel                  B5                      Sentinel                                      0.4474                    0.1042                    0.9074
     2.60      0.1475  Sentinel                  B5                      Sentinel                                      0.5418                    0.1475                    2.4444
     2.80      0.1445  Sentinel                  B5                      Sentinel                                      0.5659                    0.1445                    2.8148
     3.00      0.0833  Sentinel                  B5                      B5                                            0.5961                    0.0833                    3.7273
```

### 6.1 Tổng hợp trên toàn bộ 64 ô (Bản chính `--tau-follows-dprime`)

| Sentinel đối đầu | Thua ngay tại $\lambda_Q \to 0^+$ | Hơn ở mọi $\lambda_Q$ | Có $\lambda_{\times}$ | $\lambda_{\times}$ nhỏ nhất · **Trung vị** · Lớn nhất | Số ô $\lambda_{\times} \ge 0,10$ |
|:---|:---:|:---:|:---:|:---|:---:|
| `B1 audit-at-commit` | **0**/64 | 0/64 | 64/64 | 0.0458 · **0.1426** · 0.5961 | **51**/64 |
| `B5 risk-score` | **25**/64 | 0/64 | 39/64 | 0.0039 · **0.0201** · 0.1475 | **3**/39 |
| `B6 two-stage` | **11**/64 | 8/64 | 45/64 | 0.0227 · **0.2593** · 4.8889 | **40**/45 |

### 6.2 Thứ hạng tổng (`argmin L` trên cả 4 policy)

| Tiêu chí đếm trên 64 ô | `B1` | `Sentinel` | `B5 risk-score` | `B6 two-stage` | Số ô hoà |
|:---|:---:|:---:|:---:|:---:|:---:|
| `argmin L` **duy nhất** tại $\lambda_Q = 0$ | 0/64 | **39**/64 | 9/64 | 0/64 | **16** (Sentinel=B5=B6 tại $\Delta=0$) |
| `argmin L` **duy nhất** tại $\lambda_Q = 0,10$ | 0/64 | **3**/64 | **61**/64 | 0/64 | **0** (hết ô hoà) |

---

## 7. CÂU TRẢ LỜI CHO KHUNG BÀI (Phán quyết khung)

### 7.1 `B5 risk-score` — KHÔNG HƠN

> **Phán quyết:** **Sentinel KHÔNG hơn `B5 risk-score` trên $L$.**
> 
> - Trên **25/64** ô, Sentinel thua B5 ngay từ $\lambda_Q \to 0^+$.
> - Trên 39 ô có điểm cắt, $\lambda_{\times}$ có trung vị chỉ **0,0201** (chỉ cần $\lambda_Q > 0,02$, B5 đã vượt Sentinel).
> - Chỉ duy nhất **3/64** ô (ở $\Delta = 4, d' \in \{2,4; 2,6; 2,8\}$) Sentinel giữ được vị trí dẫn đầu ở $\lambda_Q = 0,10$.
> - Hơn nữa, B5 đạt hiệu năng $L$ vượt trội này với chi phí chỉ bằng **1/4 đến 1/7** ngân sách của Sentinel (7%–13% so với 47%–50% trần ngân sách).
> 
> Phán quyết này **hoàn toàn trơ với $\lambda_T$** vì cả Sentinel và B5 đều có $T_{\text{lost}} = 0,000$ ở mọi ô.

### 7.2 `B1 audit-at-commit` — HƠN, có điều kiện $\lambda_T$

> **Phán quyết:** **Sentinel hơn `B1 audit-at-commit` trên $L$ với mọi $\lambda_Q < \lambda_{\times}$, với trung vị $\lambda_{\times} = 0,1426$ (ở $\lambda_T = 0,50$).**
> 
> - Tại $\lambda_Q \to 0^+$, Sentinel dẫn trước B1 trên **64/64** ô.
> - Tại $\lambda_Q = 0,10$, Sentinel dẫn trước trên **51/64** ô.
> - Cơ chế: Lợi thế này hoàn toàn đến từ số hạng $T_{\text{lost}}$ (B1 làm mất $0,31$ đến $0,53$ patch sạch tại cổng commit, trong khi Sentinel có $T_{\text{lost}} = 0,000$).

#### 7.2.1 Độ nhạy với $\lambda_T$

Vì chiến thắng trước B1 phụ thuộc vào việc tính giá patch sạch bị chặn oan ($T_{\text{lost}}$), ta quét lại 64 ô ở ba mức $\lambda_T$:

| $\lambda_T$ | Sentinel hơn B1 tại $\lambda_Q \to 0^+$ | Thua | Có $\lambda_{\times}$ | $\lambda_{\times}$ nhỏ nhất | **Trung vị** | Lớn nhất |
|---:|:---:|:---:|:---:|---:|---:|---:|
| **0.00** | **26/64** | 38 | 26 | 0.0035 | **0.0417** | 0.3647 |
| **0.25** | **58/64** | 6 | 58 | 0.0008 | **0.0728** | 0.4804 |
| **0.50** | **64/64** | 0 | 64 | 0.0458 | **0.1426** | 0.5961 |

> **Kết luận về $\lambda_T$:** Ở $\lambda_T = 0,00$ (khi chặn nhầm patch sạch không bị phạt), câu tuyên bố "Sentinel hơn B1" co lại chỉ còn **26/64** ô. Chiến thắng trước B1 là phát biểu về **giá trị bảo toàn thông lượng patch**, không phải về harm đơn thuần.

### 7.3 `B6 two-stage` — HƠN có điều kiện

> **Phán quyết:** **Sentinel hơn `B6 two-stage` trên $L$ với $\lambda_Q < \lambda_{\times}$ trên 53/64 ô**, trung vị $\lambda_{\times} = 0,2593$. Trên 40/45 ô có điểm cắt, $\lambda_{\times} \ge 0,10$. Sentinel thua B6 trên 11 ô (chủ yếu tại $\Delta = 0$ nơi harm ngang nhau và B6 có false quarantine thấp hơn).

---

## 8. Kết luận khung cho luận văn FSE 2027

1. **Bác bỏ khung khẳng định cực đoan:** Không thể tuyên bố *"Sentinel là cơ chế kiểm toán tối ưu nhất trong mọi điều kiện"*, vì `B5 risk-score` vượt trội hơn về mất mát $L$ ở mọi mức $\lambda_Q \ge 0,02$ và tiêu ít ngân sách hơn đáng kể.
2. **Xác lập khung đóng góp thực sự:**
   - Sentinel giải quyết triệt để sự tắc nghẽn thông lượng ($T_{\text{lost}}$) của cơ chế kiểm toán tại commit (`B1`), bảo toàn 100% patch sạch với trần ngân sách thực nghiệm.
   - Khi kẻ tấn công dịch marker tinh vi ($\Delta = 4$), với detector mạnh ($d' \ge 2,4$), Sentinel ngăn chặn harm tốt hơn B5 đủ để bù đắp lượng false quarantine ở $\lambda_Q \le 0,10$.
   - Sự phân tầng rõ ràng giữa 4 policy cung cấp cơ sở phương pháp luận cho việc lựa chọn cơ chế phòng thủ dựa trên hàm chi phí thực tế của tổ chức.
