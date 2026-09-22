# Tiền-đăng-ký v2 — `m(x)`, `F_detect`, hiệu chuẩn `τ`, và G4

**Thay cho:** [[TIEN-DANG-KY-m-x-va-F-detect]] (v1, 17/09/2026). v1 **giữ nguyên làm hồ sơ**, không sửa thân.
**Trả lời cho:** [[Y-THAY-duyet-tien-dang-ky-va-pham-vi]] — A.1, A.3, A.4, A.5, C.2, C.4.
**Ngày:** 18/09/2026. **Mốc code:** `393a22b`.

> **VĂN BẢN CHỐT TRƯỚC KHI ĐO.** Mọi con số ở đây là **định nghĩa**, không phải kết quả. Chưa có phép đo `F_detect` nào chạy.
>
> **Điều kiện hiệu lực** (C.4): đây là bước 1 trong bảy bước. Commit văn bản này **trước dòng code đầu tiên** của việc 4. Xác nhận của GVHD: **16/09/2026, họp online** — miệng, cho nội dung trao đổi; xác nhận cho **bản viết** còn để trống ở [[Y-THAY-duyet-tien-dang-ky-va-pham-vi]].

---

## 0. v1 sai ở đâu — ba dòng, để không lặp

| v1 chốt | v2 | vì sao |
|---|---|---|
| `m(lành) = 0` **theo cấu tạo**, G1 là cổng 0/N tuyệt đối | **bác** | tự mâu thuẫn: §2 của v1 chốt `m = v₁`, mà `v₁` là một **khoảng cách** hoặc một **phán đoán** — không bao giờ đúng 0 trên lành. Ép 0/N buộc phải nhị phân hoá `v₁` ⇒ giết chính bề mặt liên tục mà v1 lập luận để giữ |
| $w = (\tfrac13,\tfrac13,\tfrac13)$ | **bác** | §4 của v1 **đã chứng minh `v₃ ≡ 0`** về cấu trúc cho cả hai lớp. Đặt ⅓ cho một thành phần chết không phải "không tiên nghiệm" — đó là một lựa chọn |
| *"`d'_eff ≤ d'/3` là hệ quả của định nghĩa"* | **xoá** | trần đó là **artefact của `w`**, không phải phát hiện. Phản biện một câu: *chọn `v₁` đáng ⅓ thì tất nhiên ra ⅓* |
| *"không duyệt mức 3 ⇒ `d'_eff → 0` là kết quả"* | **xoá** | **chưa đo ≠ đo ra 0.** Không chạy mức 3 thì có *"tín hiệu nội dung chưa hiện thực"*, không có phép đo |

---

## 1. Mô hình, và cách `φ` thật sự được giữ cố định

$$s(x) \;\sim\; \mathcal{N}\big(d' \cdot m(x),\; 1\big), \qquad m(x) \in [0,1]$$

`m(x)` là **độ lộ nội dung**; attacker kéo `m` xuống. `d'_eff(a) = d' \cdot \mathbb{E}[m(x) \mid x \sim a]`.

**`m(x)` KHÔNG bằng 0 trên item lành.** Ràng buộc v1 đặt ra bị bác — nhưng **vấn đề v1 nêu là thật**: nếu `m̄_lành > 0` thì

$$\varphi \;=\; \Pr(s > \tau \mid \text{lành}) \;=\; \Phi\big(d' \cdot \bar m_{\text{lành}} - \tau\big)$$

trôi theo `d'`. Cách đóng **không** phải ép `m(lành) = 0`, mà là **hiệu chuẩn `τ`**:

$$\boxed{\;\tau(d') \;=\; \text{phân vị } 0{,}88 \text{ của } \big\{\,d' \cdot m(x) + \mathcal{N}(0,1) \;:\; x \text{ lành}\,\big\}\;}$$

Đây là Neyman–Pearson đúng nghĩa: **cố định tỉ lệ báo động giả, đo power**. Phép quét `d'` vẫn nguyên hiệu lực.

**Hệ quả phải khai, vì nó khác sweep hiện tại.** Trong sweep đang có (`spikes/dprime-sweep.md`), `τ` **đứng yên** ở $z(0{,}88)$ — hợp lệ vì mô hình cờ có mean lành **đúng bằng 0**. Dưới B-lite mean lành là $d'\cdot\bar m_{\text{lành}} \neq 0$, nên **`τ` thành hàm của `d'`**. Hai sweep không so sánh trực tiếp được; phải nói rõ cái nào đang được trích.

`v₂`, `v₃` bằng 0 trên lành **theo cấu tạo** — nhưng chúng **không còn nằm trong `m`** (§2).

---

## 2. `m(x)` — chốt

$$\boxed{\;m(x) \;=\; v_1(x)\;}$$

| thành phần | vai trong v2 | lý do |
|---|---|---|
| $v_1$ **nội dung** | **là `m`** | thành phần **duy nhất còn tín hiệu** sau best-response |
| $v_2$ **provenance** | **điều kiện hợp lệ** (như `F_match`) | khai provenance thật là **chiến lược trội** cho attacker — không có gì để đánh đổi. Nó không đo sức mạnh audit; nó **định nghĩa họ tấn công** |
| $v_3$ **lineage** | **BỎ**, ghi lý do | $\equiv 0$ ở **cả hai lớp**, hai lý do độc lập đã đo: agent chỉ điền `derived_from` kèm `poisoned=True`, và `_one_event` loại payload dẫn xuất. Nếu sau này sửa corpus cho lineage có nghĩa thì **mở lại, có ngày** |

Không còn câu hỏi trọng số. Không còn trần giả.

`v₂` **vẫn được hiện thực và vẫn báo cáo** — như **luật phụ**, để bắt attacker scripted nào nói dối về provenance. Nó **không** nằm trong tuyên bố chính.

---

## 3. `F_detect` chỉ có thể là mức 3 — và đây là hệ quả v1 chưa rút

v1 đổi tên `semantic_anomaly → style_divergence` cho mức 2 (thống kê bề mặt, không key). **Đổi tên đúng.** Nhưng hệ quả thì v1 viết ra mà không rút:

> Mức 2 là **thống kê bề mặt**. Nguyên tắc §3.1 của doc gốc: **audit phải giàu hơn sàng miễn phí, không thì không ai trả $\kappa$.**

`F_match` = `{size, depth, recency, derived}` **đã là** thống kê bề mặt, và nó miễn phí. Nên mức 2 không chỉ *yếu* — nó **bị loại về cấu trúc**, vì dùng nó là **đếm hai lần với `F_match`**.

⇒ **`v₁` thật chỉ có thể là mức 3: một LLM judge.** Ghi thẳng vào tiền-đăng-ký.

⇒ Mức 3 chính là lớp phòng thủ mà arXiv:2503.00061 phá. **Không phải lý do tránh** — B-lite tồn tại để cho attacker đúng bề mặt đó. Nhưng attacker trong game best-respond trên **lưới rời rạc**, không phải gradient chống judge, nên `d'_eff` đo được là **cận trên** (P6). Viết sẵn vào II.12, không chờ phản biện.

---

## 4. Hiệu chuẩn `τ` — ba điều kiện, thiếu một là lặp lỗi B.1

| # | điều kiện | vì sao |
|---|---|---|
| **1. Thứ tự** | Chỉ hiệu chuẩn **sau** khi corpus lành đã **sửa P8** và **vá rò rỉ** — tức sau bước 3 của C.4 | hiệu chuẩn trên corpus nhiễm là lặp **đúng** lỗi vừa cấm cho chứng nhận |
| **2. Tách tập** | Trong nội bộ tập lành, chia **tập hiệu chuẩn** (tính `τ(d')`) và **tập báo cáo** (phân bố `m(lành)`, `φ` thực đo) **rời nhau**, chia theo seed khai trước | cùng một tập ⇒ `τ` overfit ⇒ `φ = 0,12` báo cáo là số lạc quan. **Holdout hiện tại chỉ tách attacker/lành — chưa tách calibration/evaluation** |
| **3. Nguồn của `φ`** | `φ = 0,12` là **`φ` của setting `mid` chép từ manuscript §8** — hằng số khai, không đo | áp luật II.4 cho chính nó. Sau khi `d'` thành tham số quét, đây là **hằng số khai cuối cùng còn lại** |

**Xử lý (3):** giữ **0,12 làm điểm chính**, **và** báo cáo độ nhạy tại $\varphi \in \{0{,}06;\ 0{,}12;\ 0{,}20\}$ — đúng ba giá trị `strong`/`mid`/`weak` gốc. Rẻ, và đóng câu *"0,12 ở đâu ra"* **trước** khi bị hỏi.

---

## 5. Cổng đo — chốt trước

| # | phép đo | cổng chốt TRƯỚC | nếu đỏ |
|---|---|---|---|
| **G1** | `v₂` bằng 0 trên lành | **test hiện thực**, không phải cổng khoa học — `v₂` là kiểm tra chính xác nên bằng 0 theo cấu tạo | lỗi hiện thực, sửa code |
| **G2** | $\bar m(a)$ của **từng** attacker trên corpus tiêm | báo cáo **từng attacker**; không `min`, không trung bình gộp | — |
| **G3** | $d'_{\text{eff}}(a) = d' \cdot \bar m(a)$ | cùng lưới `d'`, cùng `τ(d')` đã hiệu chuẩn, cùng `SPLIT_SEEDS` | — |
| **G4** | agreement giữa LLM judge và nhãn tay | **§6 dưới đây** | mức 3 **chưa có tín hiệu đã đo** — **không phải** "đo ra 0" |

**Không quy đổi qua cầu $d' = \sqrt2\,\Phi^{-1}(\mathrm{AUC})$** ở bất kỳ đâu trong mạch này. `m` là điểm vi phạm có khối lượng gần 0, xa Gaussian đồng phương sai hơn cả trường hợp thầy đã bác.

---

## 6. G4 viết lại đầy đủ — và một con số tôi phải sửa của thầy

v1 chỉ ghi *"$n \ge 15$, Clopper–Pearson"*. **Không đủ để nói điều cần nói.**

### 6.1 Ba số đã kiểm, không chép

Tính bằng bisection trên đuôi nhị thức, stdlib, không scipy:

| | kết quả |
|---|---|
| $n = 15$, **15/15** ⇒ cận dưới CP 95% | **0,7820** |
| $n$ nhỏ nhất cho agreement quan sát 0,90 ⇒ cận dưới ≥ 0,75 | **33** (không phải 40) |
| nhưng $n = 36$ và $n = 37$ **TRƯỢT** | **0,7394** và **0,7458** |

**Cận dưới KHÔNG đơn điệu theo $n$**, vì $k = \mathrm{round}(0{,}9n)$ nhảy bậc: tại $n = 36$ thì $0{,}9 \times 36 = 32{,}4 \Rightarrow k = 32$, tỉ lệ thực **0,889 < 0,90**.

⇒ Theo **đúng** định nghĩa kiểu `d′*` của dự án — *nhỏ nhất mà **mọi** $n$ lớn hơn đều đạt* — con số phải ghim là:

$$\boxed{\;n_{G4} \;=\; 38\;}$$

Ghim 33 là ghim một số mà chính $n = 36$ phá. Ước lượng $n \approx 40$ của thầy **an toàn nhưng không tối thiểu**; 38 là số đúng, 40 là 38 cộng biên.

### 6.2 Chốt G4

| mục | chốt |
|---|---|
| ngưỡng chấp nhận | cận dưới CP 95% của agreement judge–nhãn tay $\ge \theta_{G4} = \mathbf{0{,}75}$ |
| agreement kỳ vọng khai trước | **0,90** |
| cỡ mẫu | $n_{G4} = \mathbf{38}$, **suy từ** $\theta_{G4}$ — không suy từ tài nguyên |
| nếu 15 là trần tài nguyên | giữ 15, **viết hệ quả về độ rộng CI vào II.12**, và **không** phát biểu "judge đạt" — chỉ phát biểu **khoảng** |
| người gán nhãn tay | **mù** với output của judge; thứ tự instance trộn theo seed khai trước |
| judge | hash-freeze **prompt + model ID + version/date + temperature + seed nếu có**. Ghim prompt mà không ghim model là **đóng băng một nửa** |
| nếu đỏ | mức 3 **không dùng được**; `F_detect` **chưa có tín hiệu đã đo** |

---

## 7. Thứ tự vào việc 4 — bảy bước, không đảo

```
1. Tiền-đăng-ký (văn bản này), commit          ← cổng thật
2. P2 chạy xong                                 ← là thước đo, không đứng sau gì
3. Sửa P8 + (iii) đủ để có ≥ 1 attacker hợp lệ  ← chưa có thì F_detect không có gì để đo
4. G4 trên giấy theo §6
5. Hiện thực v₁ mức 3; chạy G4
6. Hiệu chuẩn τ(d') trên tập hiệu chuẩn lành    ← §4, sau bước 3
7. RỒI MỚI đo m(x) → d'_eff(a) trên tập báo cáo
```

**Ràng buộc về vai:** số từ `F_detect` vào đề cương ở vai *bằng chứng thiết kế chạy được* và *threat đã định lượng* — **không** ở vai kết quả luận văn.

---

## 8. P7 — giữ nguyên, đã ký

> **Chốt 17/09/2026.** Tiêu chí gate 2 là **`mean` của cận trên CI95 trên `SPLIT_SEEDS = (1..20)`**, `test_fraction = 0.4`, trần **0,56**; `clear` **luôn báo cạnh tiêu chí, không bao giờ thay nó**.

Lý do chọn `mean` **không phụ thuộc dữ liệu pilot** — đó là điều kiện để nó được chốt trước: $\max(\text{hi})$ có kỳ vọng **tăng theo $|\mathcal S|$** (hội tụ về supremum, không về một đại lượng tổng thể), nên tiêu chí sẽ đổi mỗi lần thêm seed. Đó là tính chất của thống kê, không phải của số liệu.

**Ghi kèm:** trần **0,56** cũng là **số khai từ manuscript**, không phải số đo của luận văn này. Giữ nguyên, không nới — chính vì nó có trước mọi phép đo ở đây.

---

## 9. Bổ sung 18/09 (cùng ngày, theo IV.4 của [[Y-THAY-review-plan-nuoc-rut]]) — dạng phát biểu theo $\lambda_Q$, chốt trước khi có ba cột

Sweep $d'$ chấm bằng **L** ($h + \lambda_Q \cdot Q_{\text{false}} + \lambda_T \cdot T_{\text{lost}}$, `metrics.loss`) sẽ in ba cột $\lambda_Q \in \{0;\ \lambda_Q^*;\ 0{,}10\}$. Ba cột là để **hiểu cấu trúc, không phải để chọn**. Chốt trước:

> Tuyên bố chính phát biểu ở **dạng khoảng**: *"Sentinel [thắng / không thắng] X trên L với mọi $\lambda_Q < \bar\lambda$"*, trong đó $\bar\lambda = \lambda_Q^*$ **là kết quả**, không phải lựa chọn. Cột $\lambda_Q = 0$ là điểm tham chiếu harm-only (so với bản gốc); cột $0{,}10$ là giá trị mặc định **đã khai là không suy từ đâu** (`metrics.py`) — cả hai là minh hoạ, **không** là tiêu đề. Người đọc có $\lambda_Q$ của riêng họ tra vào khoảng.

### 9.1 Sửa đổi 18/09/2026 — thao tác hoá ranh giới cho phát biểu **theo cặp**

**Đổi cái gì.** §9 chốt ranh giới của dạng phát biểu là `λ̄ = λ_Q^*`
(`metrics.lambda_q_star`). Từ 18/09/2026, ranh giới được báo cáo là **`λ_×`** —
**điểm cắt theo CẶP**: nghiệm `λ_Q` của `L_X(λ_Q) = L_Sentinel(λ_Q)`, với ba kết
cục giữ **tách bạch** (một số `λ_×`; Sentinel hơn ở **mọi** `λ_Q`; Sentinel
**thua từ `0+`**, bao gồm cả hoà tại đúng 0 rồi thua với mọi `λ_Q > 0`).

**Vì sao.** Dạng phát biểu đã chốt — *"Sentinel [hơn / không hơn] **X** trên `L`
với mọi `λ_Q < ranh giới`"* — là mệnh đề về **một cặp**. `lambda_q_star` không
biểu diễn được mệnh đề đó trên **25/64 ô** (39% lưới), vì hai lý do độc lập:
(i) nó trả lời về `argmin L` trên **cả bốn** policy, không phải về một cặp; và
(ii) nó chỉ nhận nghiệm trong `(1e-9; 5]`, nên ở 25 ô mà `L(0)` **hoà**, cú đổi
ngôi xảy ra **ngay trên 0** bị bỏ qua và hàm trả về một số **lớn hơn**, đọc từ
một cặp khác — tức một số **ĐỌC TRẦN**, không phải dải mà Sentinel thật sự dẫn.
`metrics.py` đang **đóng băng**, nên hàm không được sửa; cái được sửa là **đại
lượng báo cáo**, và nó mang **tên riêng** để không đổi định nghĩa trong im lặng.

**Báo cáo cả hai phiên bản** (đúng quy tắc đóng băng ở cuối §9). Trên đúng 64 ô
của bản chính (`--tau-follows-dprime`, corpus seed 2026, seeds `(1,2,3)`):

| đại lượng | đo được trên | dải | trung vị |
|:--|:--:|:--|:--:|
| `λ̄ = λ_Q^*` (bốn policy, **đã tiền-đăng-ký**) | 64/64 ô | `[0,0042; 1,4217]` | 0,0813 |
| `λ_×` Sentinel–`B1` (**cặp, sửa đổi này**) | 64/64 ô | `[0,0462; 0,5932]` | **0,1529** |
| `λ_×` Sentinel–`B5` | 31/64 ô | `[0,0042; 0,1203]` | 0,0415 |
| `λ_×` Sentinel–`B6` | 37/64 ô | `[0,1111; 18,5000]` | 0,3846 |

**Không đổi cái gì.** `λ_Q = 0` và `λ_Q = 0,10` vẫn là **MINH HOẠ**, không bao
giờ là dòng tít; ranh giới vẫn là **KẾT QUẢ ĐO**, không phải tham số được chọn;
`λ̄` vẫn được báo cáo nguyên nghĩa cũ **bên cạnh** `λ_×` ở mọi chỗ phát biểu.

**Nguồn số và cách tái lập:** `spikes/sweep-loss-b5-b6.md` §6.0–§6.2 và §7;
`python3 dprime_sweep.py --n 40 --tau-follows-dprime`
(`dprime_sweep.pairwise_crossing`, `pairwise_table`), corpus seed 2026,
seeds `(1, 2, 3)`, `B = 17,95`, `H = 8`.

---

**Văn bản này đóng băng ngày 18/09/2026, trước dòng code đầu tiên của việc 4.**
Đổi bất kỳ mục nào về sau = **đổi tiền-đăng-ký**: ghi ngày, ghi lý do, và báo **cả hai** phiên bản trong luận văn.
