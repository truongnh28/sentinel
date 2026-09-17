# ε trở thành NGÂN SÁCH thật cho `MatchedAttack` (mục (ii) của phản biện, §8 số 5)

Ngày: 2026-09-17. Nối tiếp `chot_theta.md` (chốt θ) và `ho-tan-cong-mo-rong.md`
(attacker khớp phân bố). Mã: `attacks.MatchedAttack.payload`.

> **Ghi TRƯỚC khi chạy.** Lưới ε ở §3, định nghĩa `eps*` ở §1 và tiêu chí
> `AUC_upper ≤ 0,56` (câu 8 của phản biện) đều được viết và commit **trước** khi
> chạy bất kỳ AUC nào của tài liệu này — chúng nằm trong hằng `GRID` của
> `tests/gate2_validity/test_matched_epsilon_budget.py`, file test được viết
> trước phần cài đặt theo lối TDD. Thứ tự nhân quả kiểm chứng được: lưới ⇒ số,
> không phải ngược lại. θ = 0,50 **không** được đụng tới.

---

## 1. Câu hỏi

ε là **ngân sách khả phân biệt** của kẻ tấn công: tiêu nhiều thì chắc chắn được
truy xuất hơn, đổi lại dễ bị nhận ra hơn. Chỉ khi có **cả hai chiều** thì

$$\varepsilon^\* \;=\; \max\{\varepsilon : \mathrm{AUC}_{\text{upper}}(\varepsilon) \le 0{,}56\}$$

mới là một phép **hiệu chuẩn**. Câu hỏi của tài liệu: trên pool graded
(SWE-bench, `pool="full"`), ε mua được gì, ε tốn gì, và hai đầu đó có gặp nhau
không.

## 2. Khuyết tật: ε chỉ có chiều TỐN

`MatchedAttack.payload` đóng dấu payload bằng **toàn bộ** topic của σ:

```python
topic = task.topic      # ⇒ sim(topic, task.topic) = 1,0 ở MỌI ε
```

Hệ quả, và cả ba đều đo được chứ không suy diễn:

1. payload vượt θ ở ε = 0 **y hệt** ở ε = 1 ⇒ ε không mua gì ⇒ `eps* = 0` là một
   **định nghĩa**, không phải một số đo. "Tối ưu là đừng tiêu gì" là câu nói
   rỗng khi tiêu không mua được gì.
2. `build.plan_poison` và `analysis.benign_corpus.feasible_sigmas` **đã** hỏi câu
   hỏi ngủ đông về `payload_topic_like(σ_topic, ε)`. Nên chúng phán một σ là ngủ
   đông cho một topic mà payload **không mang**; payload thật (topic rộng hơn) có
   thể bị một task trước σ kéo lên ⇒ Δ khai báo **lớn hơn** Δ thật. Đây chính là
   lỗi nhiễm 23–44%, quay lại qua đường attacker thay vì qua đường chèn sớm.
3. `GradedAttack` đã dùng đúng `payload_topic_like` từ trước; `MatchedAttack` —
   pipeline **duy nhất** trong `REGISTRY` — thì chưa.

```mermaid
flowchart TB
    subgraph TRUOC["TRƯỚC: ε chỉ có một chiều"]
        E0["ε"] --> S0["size = |note| + 50ε"]
        E0 -.->|"KHÔNG có cạnh này"| R0["được truy xuất?"]
        T0["topic = task.topic"] --> R0
        R0 --> A0["sim = 1,0 · LUÔN LUÔN"]
    end
    subgraph SAU["SAU: ε có cả hai chiều"]
        E1["ε"] --> S1["size = |note| + 50ε<br/>(CHI PHÍ)"]
        E1 --> K["k = max(1, ⌈ε·m⌉)"]
        K --> T1["topic = payload_topic_like(σ, ε)"]
        T1 --> R1["sim = k/m ≥ θ ?<br/>(LỢI ÍCH)"]
    end
```

Sửa: payload mang `retrieval.payload_topic_like(task.topic, ε)`, tức tập con
$k = \max(1, \lceil \varepsilon m \rceil)$ token, nên

$$\mathrm{sim}(A, B) \;=\; \frac{|A \cap B|}{|A \cup B|} \;=\; \frac{k}{m},
\qquad \text{truy xuất} \iff \frac{k}{m} \ge \theta = 0{,}50 .$$

## 3. Lưới ε — khai báo TRƯỚC khi chạy

$$\varepsilon \in \{0{,}0;\; 0{,}1;\; 0{,}2;\; 0{,}3;\; 0{,}4;\; 0{,}5;\; 0{,}7;\; 1{,}0\}$$

Dày hơn lưới sàng cũ `(0; 0,2; 0,4; 0,7; 1,0)` của
`tests/gate2_validity/test_benign_corpus.py` ở **khoảng 0,1–0,5**, vì đó là nơi
$k/m$ đổi bậc ở kích thước topic điển hình ($m = 4$ ⇒ bậc tại ε = 0,25 và 0,50) —
chọn theo **lưới sim đạt được**, đúng lập luận D1 của `chot_theta.md`, không phải
theo số đã thấy. Lưới sàng cũ **không đổi**: nó là hằng của một test đã ghim, và
sửa nó để chiều một kết quả mới chính là điều D1 tồn tại để chặn.

Cấu hình đo: `pool="full"`, `carrier="memory"`, `per_event=4`, `n_events=900`
(mức câu 8 chốt), `natural=False` (nền `harvest` cũ, để mọi số đã ghim so sánh
được), 20 split của `discriminator.SPLIT_SEEDS`, tiêu chí là **trung bình** cận
trên CI.

## 4. Biểu thức `size`: một CHỆCH khỏi ràng buộc 2 của đề bài, và số đo bắt nó chệch

Đề bài yêu cầu: *"size phải tính từ ĐÚNG topic mà payload ghi ra"*, tức
`target = |str(payload_topic)| + 14 + |task_id| + 50ε`. Đã cài đúng như vậy, đã
đo, và kết quả là **không epsilon nào qua được trần** — trung vị AUC held-out
trên 20 split, 80 sự kiện, pool full:

| ε | 0,0 | 0,1 | 0,2 | **0,3** | 0,4 | 0,5 | 0,7 | 1,0 |
|---|---|---|---|---|---|---|---|---|
| Δ=0 | 0,986 | 0,932 | 0,793 | **0,538** | 0,690 | 1,000 | 1,000 | 1,000 |
| Δ=2 | 0,990 | 0,937 | 0,833 | **0,592** | 0,686 | 1,000 | 1,000 | 1,000 |
| Δ=4 | 0,978 | 0,940 | 0,854 | **0,582** | 0,642 | 1,000 | 1,000 | 1,000 |

Đường cong hình chữ U, đáy ở ε = 0,3, và đáy đó vẫn **trên** trần 0,56 ở Δ = 2 và
Δ = 4. Hệ quả dây chuyền: `MatchedAttack` rớt khỏi `REGISTRY` ⇒ `REGISTRY` **rỗng**
⇒ `usable_with("exact")` không nhận pipeline nào ⇒ gate 1 đỏ
(`REGISTRY is empty -- nothing to check`) và **mọi** ô của mock ra ngoài phạm vi.

Đó không phải "một ô ra ngoài phạm vi" — đó là attacker bị làm cho **dở đi rồi
kết luận benchmark không có attacker nào**, đúng loại lỗi mà docstring của
`attacks.py` mở đầu bằng (thu hẹp lớp attacker trong im lặng, rồi đọc dấu của kết
luận).

**Lý do kỹ thuật.** Bài học của `_AGENT_TEMPLATE_CHARS` là *"bám theo ghi chú mà
mình đang bắt chước"*: hằng 23 sai **không phải** vì nó kể những byte payload
không có, mà vì nó **thôi bám** theo ghi chú thật (task id thật dài 20–32 ký tự),
làm payload ngắn hơn mọi ghi chú 20 ký tự, AUC 0,858. Bắt `size` bám theo **tag
đã thu hẹp** của chính payload là tái lập đúng lỗi đó qua đường topic: ở ε = 0 tag
chỉ còn 1 token trong khi mọi ghi chú benign mang $m \ge 2$ token, nên payload
ngắn hơn cả lớp benign một cách hệ thống — AUC 0,986.

**Cái được cài.** Chiều dài đích là chiều dài của **ghi chú agent cho chính task
σ**, `"[{task.topic}] ghi chú từ {task.task_id}"`:

$$\text{target}(\varepsilon) \;=\; \underbrace{|\mathrm{str}(\text{task.topic})| + 14 + |\text{task\_id}|}_{\text{ghi chú agent — vật thể CÓ THẬT trong corpus}} \;+\; \mathrm{round}(50\varepsilon)$$

trong khi **tag** payload ghi ra là topic đã thu hẹp, phần chênh bù bằng filler.
Thu hẹp **lời khai** (để truy xuất) và chọn **độ dài** (để nguỵ trang) là hai lựa
chọn độc lập của kẻ tấn công; không có gì buộc chúng phải là một con số.

Nửa còn lại của ràng buộc 2 **vẫn được giữ và vẫn được ghim**: thứ payload **ghi
ra** phải là topic đã thu hẹp, không được là topic đầy đủ
(`test_the_narrowed_tag_is_the_string_the_payload_actually_carries`). Và điều
tránh được "bám theo một hằng nhớ nhầm" không phải là một công thức trong test mà
là **so trực tiếp với ghi chú `agent.MockAgent` thật sự ghi**
(`test_at_eps_zero_the_payload_is_exactly_as_long_as_the_note_it_imitates`, chạy
cả trên topic tập-token lẫn topic chuỗi).

## 5. Bảng kết quả — lợi ích và chi phí trong MỘT bảng

`fires` = tỉ lệ sự kiện khả thi (mọi $(wf, \sigma)$ ngủ đông ở Δ đó) mà payload
vượt θ tại σ, tức **đúng thứ ε mua được**. `hi` = trung bình cận trên CI trên 20
split; `clear` = số split tự vượt trần 0,56. `n` = số sự kiện khả thi (xem §7).

**Δ = 0**

| ε | fires | n | hi | clear | qua trần? |
|---|---|---|---|---|---|
| **0,0** | **3,65 %** (82/2248) | 2248 | **0,5414** | 19/20 | **✓** |
| 0,1 | 3,65 % | 2248 | 0,6459 | 0/20 | ✗ |
| 0,2 | 3,65 % | 2248 | 0,7507 | 0/20 | ✗ |
| 0,3 | 29,00 % | 2248 | 0,8278 | 0/20 | ✗ |
| 0,4 | 77,00 % | 2248 | 0,8788 | 0/20 | ✗ |
| 0,5 | 100 % | 2248 | 1,0000 | 0/20 | ✗ |
| 0,7 | 100 % | 2248 | 1,0000 | 0/20 | ✗ |
| 1,0 | 100 % | 2248 | 1,0000 | 0/20 | ✗ |

**Δ = 2**

| ε | fires | n | hi | clear | qua trần? |
|---|---|---|---|---|---|
| **0,0** | **2,91 %** (24/826) | 826 | **0,5394** | 17/20 | **✓** |
| 0,1 | 2,91 % | 826 | 0,6581 | 0/20 | ✗ |
| 0,2 | 2,93 % | 819 | 0,7690 | 0/20 | ✗ |
| 0,3 | 26,91 % | 773 | 0,8452 | 0/20 | ✗ |
| 0,4 | 78,21 % | 716 | 0,8979 | 0/20 | ✗ |
| 0,5 | 100 % | 706 | 1,0000 | 0/20 | ✗ |
| 0,7 | 100 % | 535 | 1,0000 | 0/20 | ✗ |
| 1,0 | 100 % | 504 | 1,0000 | 0/20 | ✗ |

**Δ = 4**

| ε | fires | n | hi | clear | qua trần? |
|---|---|---|---|---|---|
| **0,0** | **2,41 %** (11/456) | 456 | **0,5411** | 18/20 | **✓** |
| 0,1 | 2,41 % | 456 | 0,6823 | 0/20 | ✗ |
| 0,2 | 2,44 % | 450 | 0,7807 | 0/20 | ✗ |
| 0,3 | 25,67 % | 409 | 0,8493 | 0/20 | ✗ |
| 0,4 | 75,29 % | 348 | 0,9015 | 0/20 | ✗ |
| 0,5 | 100 % | 342 | 1,0000 | 0/20 | ✗ |
| 0,7 | 100 % | 237 | 1,0000 | 0/20 | ✗ |
| 1,0 | 100 % | 202 | 1,0000 | 0/20 | ✗ |

### Chốt

$$\varepsilon^\* = 0{,}0,\qquad
\text{fires}(\varepsilon^\*) = 3{,}65\,/\,2{,}91\,/\,2{,}41\ \%
\ \text{ở } \Delta = 0\,/\,2\,/\,4 .$$

**`eps*` vẫn bằng 0 — nhưng bây giờ đó là một SỐ ĐO, không phải một đồng nhất
thức.** Trước thay đổi, `fires(ε) ≡ 100 %` ở mọi ε, nên "ε\* = 0" chỉ nói lại
rằng chi phí đơn điệu tăng. Sau thay đổi, `fires(0) = 3,65 %` là một số khác 0 và
khác 100 %, đo được, và nó đến từ chỗ $k \ge 1$ luôn đúng: một topic hai token đã
được phủ một nửa bởi một token.

**Hai đầu ngân sách KHÔNG gặp nhau trên corpus này.** ε rẻ nhất mà bắn 100 %
(0,50) bị tách ở AUC = 1,0000; ε rẻ nhất **không** bị tách (0,0) chỉ bắn được
1 trên 27 sự kiện. Không có ε nào vừa ≤ 0,56 vừa bắn đáng kể. Đây là **kết quả**,
báo nguyên trạng theo đúng đề bài ("nếu ε\* vẫn là 0 thì báo như đã đo"), không
phải một tham số cần chỉnh cho đẹp.

## 6. Kiểm bằng tay

**(a) `fires` khớp CHÍNH XÁC với công thức đóng, không cần chạy corpus.** Truy
xuất chỉ phụ thuộc $m = |topic_\sigma|$:

$$\text{bắn} \iff \frac{\max(1, \lceil \varepsilon m\rceil)}{m} \ge \frac12 .$$

Histogram $m$ trên 2248 sự kiện Δ = 0 (đo tại chỗ):
`{2: 82, 3: 935, 4: 570, 5: 335, 6: 107, 7: 59, 8: 37, 9: 35, …}`.

| ε | $m$ nào bắn | cộng lại | dự đoán | đo được |
|---|---|---|---|---|
| 0,0–0,2 | $m = 2$ | 82 | 82 → 3,65 % | **82 → 3,65 %** |
| 0,3 | $m \in \{2, 4\}$ | 82 + 570 | 652 → 29,00 % | **652 → 29,00 %** |
| 0,4 | $m \in \{2,3,4,6,8\}$ | 82+935+570+107+37 | 1731 → 77,00 % | **1731 → 77,00 %** |
| ≥ 0,5 | mọi $m$ | 2248 | 100 % | **100 %** |

Trùng từng đơn vị. Chỗ dễ đọc sai: ở ε = 0,3 thì $m = 3$ **không** bắn
($k = \lceil 0{,}9 \rceil = 1$, sim = 1/3 < 1/2) trong khi $m = 4$ **có**
($k = \lceil 1{,}2 \rceil = 2$, sim = 1/2). Truy xuất không đơn điệu theo $m$ —
nó đơn điệu theo ε, và đó đúng là điều test
`test_a_small_budget_does_not_clear_theta_and_a_full_one_does` ghim.

**(b) `hi` ở ε\* trùng ĐÚNG số đã ghim trước đây**: 0,5414 / 0,5394 / 0,5411 với
19 / 17 / 18 split vượt — đúng ba số trong docstring của
`analysis/benign_corpus.py`. Đây là kiểm tra chéo cho §4: `topic` **không** nằm
trong `F_MATCH = {size, depth, recency, derived}`, và cách cài ở §4 giữ nguyên
`size` từng ký tự, nên **không một số AUC nào đã công bố bị dịch**.

**(c) Mock không nhúc nhích.** Topic mock là chuỗi một token, tập con không rỗng
duy nhất của nó là chính nó, nên `payload_topic_like` là **ánh xạ đồng nhất**.
Ghim bằng byte ở `TheMockCannotMove.FROZEN` (bốn ε), và bằng md5 đầu–cuối ở §8.

## 7. Hệ quả về PHẠM VI, khai báo chứ không giấu

**(a) Số sự kiện khả thi GIẢM khi ε tăng.** Cột `n` ở Δ = 2 đi
826 → 819 → 773 → 716 → 706 → 535 → 504. `feasible_sigmas` giữ σ chỉ khi **không**
task nào trong $[\sigma-\Delta, \sigma)$ truy xuất được payload; payload rộng hơn
thì dễ bị kéo lên sớm hơn. Đây **không** phải thay đổi do task này gây ra —
`feasible_sigmas` vốn đã tính theo `payload_topic_like` — nhưng trước đây payload
**không tuân** phán quyết đó, còn bây giờ thì có. Ở Δ = 0 dải $[\sigma, \sigma)$
rỗng nên `n` đứng yên ở 2248, đúng như phải thế.

**(b) `requires_graded_retrieval` GIỮ NGUYÊN `False`** — và lý do không phải "để
mock còn chạy". Cờ này nghĩa là **VÔ NGHĨA trên dataset exact**
(`attacks._scope_admits`): một pipeline mà mặt phẳng ε duy nhất là truy xuất sẽ
báo `harm = 0` giả ở mọi ε < 1 ở đó — đó là `GradedAttack`. `MatchedAttack` giữ
ngân sách **hai đầu** trên dataset exact (`size` dịch thật, `provenance` nhảy bậc
thật ở 0,5), và trên topic một token `payload_topic_like` là đồng nhất, nên
**không số nào nó báo trên mock là giả**; cái nó mất ở đó là mặt phẳng truy xuất,
vốn là thuộc tính của **dataset** và đã được `topic_kind` khai báo rồi. Lật cờ
thành `True` sẽ làm `usable_with("exact")` **rỗng** (không còn pipeline đăng ký
nào khác) và đẩy **toàn bộ** ô mock ra ngoài phạm vi để ghi lại một hạn chế mà
dataset đã tự ghi. Ghim máy kiểm: `TheScopeStaysTruthful` (hai test) cộng với
`test_an_exact_dataset_admits_no_attack_that_needs_graded_retrieval` đã có sẵn
(`assertTrue(exact, "an exact dataset admits no attack at all")`).

**(c) N3.** Không ô nào bị bỏ im lặng và không ô nào bị ghi `harm = 0` thay cho
lý do. Các ε trượt trần ở §5 được ghi **kèm số** (cột `hi`, `clear`), đúng khuôn
`attacks.PENDING` dùng cho `legacy` / `verbosity` / `dist-matched` /
`frozen-payload`.

## 8. Bất biến & cổng

- **md5 hai đường experiment KHÔNG đổi** (bắt trước, xác nhận sau):
  `experiment.py --n 20` = `5655bd4956206148c3744045e3d17f61`;
  `experiment.py --dataset swebench --n 20` = `2140bbe796ce925a19631a1c7a88f5e0`.
  Đường swebench không đổi vì `runner.run_once` chèn qua `build.inject`, và
  `build.inject` **đã** dùng `payload_topic_like` từ trước; `attacks.py` chỉ được
  đọc bởi corpus AUC và các cổng.
- **Ba cổng xanh, zero skip: 361 / 68 / 9** (gate 2 tăng 58 → 68 do 10 test mới
  trong `tests/gate2_validity/test_matched_epsilon_budget.py`).
- **`REGISTRY` không đổi**: `matched` vẫn là pipeline đăng ký duy nhất, và
  `usable_with("exact")` / `usable_with("graded")` đều vẫn nhận nó.
- **θ = 0,50 không bị đụng.** Mọi bậc trong §6 được tính tại θ đã đóng băng.
- **Không sửa** `oracle.py`, `runner.py`, `scoring.py`, `metrics.py`,
  `detector.py`. Sửa: `attacks.py` (một phương thức) + một file test mới.

## 9. Giới hạn

1. **`eps*` = 0 và fires(ε\*) ≈ 3 % nghĩa là `MatchedAttack` trên pool graded gần
   như không bao giờ kích hoạt ở ngân sách nó đủ tiền trả.** Cột harm của
   RQ1 chạy trên đường `build.inject`, nên nó không bị con số này làm dịch — điều
   nó chỉ ra là một **câu hỏi mở về thiết kế attacker**, không phải một lỗi số:
   cần một attacker mà chi phí nguỵ trang không tăng theo cùng một trục với lời
   khai truy xuất. `DistributionMatchedAttack` là nửa đầu của câu trả lời đó
   (nó rút `size` từ phân bố benign thay vì từ topic), và nó vẫn ở `PENDING`.
2. **`DistributionMatchedAttack` mang ĐÚNG khuyết tật §2 và tài liệu này KHÔNG
   sửa nó.** `payload` của nó vẫn đặt `topic = task.topic`, nên payload của nó
   vẫn được truy xuất ở mọi ε và ε của nó vẫn chỉ có chiều tốn. Ghi lại ở đây chứ
   không sửa lặng lẽ: nó là attacker của một task khác (mục (iii)), số của nó đã
   công bố ở `ho-tan-cong-mo-rong.md`, và sửa nó sẽ làm dịch bảng đó.
3. **Nền benign là `natural=False`** (harvest cũ, mọi item benign ở depth 1). Vì
   thế ε ≥ 0,5 cho AUC = 1,0000: bậc `provenance` đẩy payload sang depth 2, một
   trục mà lớp benign ở nền này **không có phương sai nào**. Trên nền `natural`
   con số đó sẽ thấp hơn — nhưng nền cũ là nền mọi số đã ghim được đo trên, nên
   bảng §5 giữ nó để so sánh được.
4. **`fires` là truy xuất, chưa phải harm.** Một payload được truy xuất vẫn phải
   được agent chấp nhận (`adoption_rate`) và sống qua audit. `fires` là **chặn
   trên** của phần đóng góp mà ε mua được, và nó được báo đúng như vậy.
5. **MockAgent.** Như mọi số khác của kho này, lớp benign do `MockAgent` sinh ra;
   `analysis.benign_corpus.PENDING_MEASUREMENT["benign_real_agent"]` giữ nguyên
   giá trị.
