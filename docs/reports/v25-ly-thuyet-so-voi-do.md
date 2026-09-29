# v2.5 — Lý thuyết đặt cạnh số đo v2

**Ngày:** 27/09/2026 · **Trạng thái:** hậu kiểm (post hoc), không phải kiểm định xác nhận

> ### ⚠ Nhãn phải đi kèm mọi dòng của doc này
> Ghi chú lý thuyết (`theory/`) viết ngày **26/09**. Lượt eval v2 chạy ngày **25/09**. Mô hình toán vì vậy được dựng **sau** khi đã thấy số đo.
>
> Mọi chỗ khớp dưới đây là **kiểm tra nhất quán**, không phải kiểm định. Kết quả xác nhận duy nhất của v2 vẫn là endpoint đã tiền đăng ký (mức giảm của Sentinel-A1 so với B1 theo đường ρ).
>
> Doc này tồn tại để trả lời một câu: **chỗ nào lý thuyết KHÔNG khớp số đo.** Ba chỗ đó ở §3, và chúng quan trọng hơn các dòng khớp ở §2.

---

## 1. Bảng đối chiếu

Mô hình phủ của ghi chú lý thuyết (Mục 6), chạy bằng LP minimax chính xác, đặt cạnh số đo của lượt eval v2. Tham số bộ dò lấy đúng giá trị paper khai, không tinh chỉnh gì: `p_s = p_d = 0,9960`, adoption 0,85; đơn vị tổn hại = adoption × miss.

| ρ_patch | p_ρ | Trần lý thuyết | B1 mô hình | B1 **đo** | Mức giảm LP (H=9) | Mức giảm **đo** | Lệch |
|---|---|---|---|---|---|---|---|
| 0 | 0,120 | 0,745 | 0,748 | **0,7981** | 0,475 | **0,3927** | −0,082 |
| 0,25 | 0,267 | 0,620 | 0,623 | **0,7154** | 0,368 | **0,3517** | −0,016 |
| 0,5 | 0,472 | 0,445 | 0,448 | **0,5387** | 0,229 | **0,2318** | +0,003 |
| 1 | 0,850 | 0,124 | 0,128 | **0,1943** | 0,029 | **0,0171** | −0,012 |

Hai quan sát đọc thẳng từ bảng:

- **B1 của mô hình thấp hơn B1 đo ở mọi ρ**, chênh 0,05–0,09. Mô hình phủ làm kiểm toán tại commit **trông tốt hơn** bộ mô phỏng cho thấy.
- **Mức giảm khớp rất sát ở ρ = 0,25 và ρ = 0,5** (lệch 0,016 và 0,003), nhưng mô hình **vượt** số đo 0,082 ở ρ = 0. §3.3 nói vì sao.

Nguồn: `theory/checks/coverage.py` (cần numpy + scipy) và `auditgame/spikes/v2/eval-summary.json`, khối `by_rho[ρ].table2`.

---

## 2. Từng phát biểu, và phán quyết

| # | Phát biểu của ghi chú | Số đo v2 | Phán quyết |
|---|---|---|---|
| 1 | **Mệnh đề 6.3(a).** Attacker chọn được Δ, có Δ = 0 trong tập chọn ⇒ B1 tối ưu minimax | Arm `−regime estimate` (một hỗn hợp chung cho mọi Δ) có V = **0,7981379731379731**, B1 có V = **0,7981379731379731** — bằng nhau tới chữ số cuối, ở cả bốn ρ | **Khớp, bằng nhau chính xác** |
| 2 | Ở Δ = 0, Sentinel chơi như B1 | Mức giảm = 0,0000 ở Δ = 0, cả bốn ρ | Khớp |
| 3 | **Mệnh đề 6.3(b).** Mức giảm không giảm theo Δ, và G(0) = 0 | ρ = 0: 0 → 0,196 → 0,290 → 0,390 → 0,393. ρ = 0,25: 0 → 0,059 → 0,217 → 0,305 → 0,352. ρ = 1: 0 → 0 → 0 → 0,017 → 0,028. **ρ = 0,5: 0 → −0,023 → 0,072 → 0,180 → 0,237** | **Lệch ở một ô** — xem §3.2 |
| 4 | **Mệnh đề 6.3(c).** Trần G ≤ p_d − p_ρ; ở ρ = 1 trần là 0,1460 | Mức giảm đo ở ρ = 1: 0,0171 (Δ=4) và 0,0279 (Δ=8) — đều dưới trần | Khớp |
| 5 | **Mệnh đề 6.3(e).** Khi H ≥ 2Δ+1, không lịch tất định nào thắng B1 | `−randomization` V = 0,8471 ở ρ = 0 và 0,25, **tệ hơn** B1 (0,7981 và 0,7154); bằng B1 ở ρ = 0,5 và 1. **Nhưng** lịch xen kẽ cố định của D35 có V = 0,7025 ở mọi ρ, tức **thắng** B1 ở ρ = 0 và ρ = 0,25 | **Điều kiện của mệnh đề không thoả trên corpus v2** — xem §3.1 |
| 6 | Ở ρ = 1, đạo hàm của lịch i.i.d. đổi dấu khi Δ > 11,38, nên dưới ngưỡng đó không có mức giảm | Đo ở ρ = 1: Δ = 4 cho 0,0171, Δ = 8 cho 0,0279; **cả hai CI đều chứa 0**. Cả hai Δ đều dưới ngưỡng 11,38 | **Khớp, và là dự đoán định lượng** |
| 7 | LP chính xác ở ρ = 1 cho mức giảm 0,029 | Đo 0,0171 | Khớp về bậc độ lớn |

---

## 3. Ba chỗ đáng kể

### 3.1 Điều kiện của Mệnh đề 6.3(e) KHÔNG thoả trên corpus v2 — và điều đó giải thích một dự đoán đã trượt

Mệnh đề 6.3(e) đòi **H ≥ 2Δ+1**. Corpus v2 có H ∼ U{6,…,14}. Đếm trên đúng 57 workflow của tập eval:

| Δ | Điều kiện | Số workflow thoả |
|---|---|---|
| 4 | H ≥ 9 | **35/57** (61,4%) |
| 8 | H ≥ 17 | **0/57** (0,0%) |

Ô headline là Δ ∈ {4, 8}, và V là max theo cột. Cột quyết định V ở ρ ≤ 0,25 là một cột Δ = 8 — tức **đúng chỗ điều kiện thoả 0%**.

Hệ quả, và đây là phần có giá trị:

- Bài **không được** viện Mệnh đề 6.3(e) để giải thích vì sao lịch cố định thua, ở ô headline. Điều kiện của nó không đứng ở đó.
- Điều này **giải thích** dự đoán **P9b đã trượt** trong D35. P9b nói lịch xen kẽ cố định tệ hơn B1; đo được nó **tốt hơn** B1 ở ρ = 0 (0,7025 so với 0,7981) và ở ρ = 0,25 (0,7025 so với 0,7154). Ghi chú lý thuyết còn in sẵn phản ví dụ cùng dạng: ở H = 9, Δ = 8, ρ = 1, lịch tất định tốt nhất có miss 0,0040 so với B1 0,1500.
- Nói cách khác: **một dự đoán trượt của v2 được lý thuyết giải thích hậu kiểm, bằng một điều kiện có thể kiểm trước.** Đây là dạng đóng góp mạnh nhất mà v2.5 có.

Việc phải làm: đếm này (`H ≥ 2Δ+1` trên corpus) là **kiểm được trước khi chạy**. Nó vào bài như một cổng, giống Prop. 6.1 đối với thư viện belief.

### 3.2 Đơn điệu theo Δ trượt ở đúng một ô

Mệnh đề 6.3(b) nói mức giảm không giảm theo Δ. Đo được ở **ρ = 0,5, Δ = 1**: mức giảm **−4,46%** (tuyệt đối −0,0229), tức âm, trong khi Δ = 0 cho đúng 0.

Khoảng tin cậy của ô đó là [−0,0777; 0,0170] — **chứa 0**. Nên đây là **ước lượng điểm đi ngược**, không phải vi phạm có ý nghĩa thống kê.

Cách viết trung thực: nêu ô này, nêu CI, và không tuyên bố mệnh đề bị bác. Giấu nó đi thì mất đúng thứ làm doc này đáng tin.

### 3.3 Khoảng cách ở ρ = 0 chính là mất mát do thư viện hạn chế

Ở ρ = 0, LP cho mức giảm 0,475 còn đo được 0,3927 — mô hình vượt 0,082. Ba ρ còn lại khớp trong 0,016.

Cách đọc: LP là **nghiệm tối ưu**, còn Sentinel chơi bằng **thư viện 28 thành viên**. Khoảng cách 0,082 vì vậy là **mất mát do hạn chế thư viện**, đúng đại lượng Mệnh đề 6 chặn. Dấu cũng đúng chiều: nghiệm hạn chế không thể tốt hơn nghiệm tối ưu.

Đây là chỗ Mệnh đề 6 lần đầu có một con số thực nghiệm đi kèm. Nhưng phải khai kèm: bán kính phủ đo trên thư viện 8 policy của mô hình game nhỏ là **0,7500**, không phải 0,07 như draft dự phóng, nên cận của Mệnh đề 6 ở dạng đó rất lỏng và **không** giải thích được con số 0,082. Cái khớp ở đây là **chiều**, không phải độ lớn.

---

## 4. Nghĩa gì với bài v2.5

- **Trục bài đứng được.** Một mô hình phủ một trang, không tinh chỉnh, tái hiện được hình dạng của toàn bộ bản đồ regime, kể cả các kết quả âm. Đó là đóng góp, với điều kiện nhãn post hoc đi kèm từng dòng.
- **Ba chỗ ở §3 vào thẳng bài**, không giấu. §3.1 là phần mạnh nhất: nó biến một dự đoán trượt thành một cổng kiểm được trước.
- **Không được viết** rằng lý thuyết "dự đoán" số đo. Nó được dựng sau. Câu đúng: *mô hình ở §2 được xây sau khi đã thấy kết quả ở §3; sự khớp là kiểm tra nhất quán, không phải kiểm định.*
- **Kiểm định thật chỉ có ở v3**, nơi H18–H20 được khoá trước lượt chạy.

---

## 5. Dựng lại

| Số | Lệnh / file |
|---|---|
| Bảng §1, cột lý thuyết | `theory/checks/coverage.py` (numpy + scipy) |
| Bảng §1, cột đo | `auditgame/spikes/v2/eval-summary.json`, `by_rho[ρ].table2[hệ thống].worst_case_harm` |
| Mức giảm theo Δ (§2 dòng 3, 6) | cùng file, `by_rho[ρ].figure3_gain_by_delta[Δ]` |
| Lịch xen kẽ cố định (§2 dòng 5, §3.1) | `auditgame/spikes/v2-addendum/d35-summary.json`, `rows[ρ]["A1 fixed interleave"]` |
| Đếm H (§3.1) | `corpus_v2.make_corpus_v2()` rồi `corpus_v2.split()`, đếm `len(w.tasks)` trên nhánh eval |
| Bán kính phủ 0,7500 (§3.3) | `auditgame/spikes/v2/small-games.json` |
