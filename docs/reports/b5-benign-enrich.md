# b5 — Làm giàu corpus benign: đo lại F_match trên NỀN LÀNH THẬT

Ngày: 2026-09-17 (Task 27). Nguồn: `analysis/benign_corpus.py`
(`harvest_natural`, `benign_pool(natural=True)`, `matched_corpus(natural=True)`),
`analysis/discriminator.py` (`auc_over_splits`, `SPLIT_SEEDS`),
`tests/gate2_validity/test_benign_corpus.py` (lớp `TheEnrichedBenignBackground`).

Tái lập bảng AUC: chạy `matched_corpus(pipe, Δ, eps=0.0, 900, natural=…)` rồi
`auc_over_splits(pos, neg, 0.56)` cho `pipe ∈ {attacks.REGISTRY["matched"],
payloads.FrozenPayloadAttack()}`, `natural ∈ {False, True}`, `Δ ∈ {0,2,4}`.

---

## 1. Phát hiện được xác nhận lại: nền cũ ĐỒNG PHỤC trên depth/derived

`harvest` cũ chạy **một bước MockAgent trên store RỖNG**. Đo trên toàn pool `full`,
carrier `memory` (2294 item):

| đặc trưng | `harvest` (cũ) | ghi chú |
|---|---|---|
| depth   | `{1}` | mọi item là `agent/notes`, một dấu `/` |
| derived | `{0}` | không item lành nào có cha |
| size    | 42–549 | **size KHÔNG hằng** — chỗ này brief nói nhẹ |
| recency | =Δ | ép bằng ghép cặp tuổi, đúng thiết kế |

Tức là 2/4 đặc trưng (`depth`, `derived`) là **hằng số**, còn `recency` là hằng số
**có chủ ý** (ghép cặp tuổi). Chỉ `size` biến thiên. Định nghĩa benign vì thế trùng
đúng hình dạng payload (payload cũng là ghi lần đầu: depth 1, derived 0) → **vòng
tròn**.

## 2. Làm giàu bằng ĐỘNG LỰC agent, không gán tay

`harvest_natural` chạy **workflow H task đầy đủ** — cắt `rows` của repo thành đoạn
H instance liên tiếp **y như `SWEBenchDataset._raw_segments`** (SPEC-P1a Phần 4
bước 1–3) rồi chạy mỗi đoạn trong **một store dùng chung**, với **benign churn bật**
(`agent.MockAgent(drift_rate=NATURAL_DRIFT_RATE)`, bước 6 của `agent.py`).

Bằng chứng độ trải đến từ agent chứ không phải gán tay:

- Item lành vẫn do **agent GHI RA** (như `harvest` cũ gọi agent thay vì format
  chuỗi) — template ghi chú là dữ liệu đóng băng, `item_id = blake2b(content)`.
- Độ sâu 2 **chỉ** đến từ bước drift: mọi item memory depth-2 có provenance
  **đúng `agent/notes/drift`** (test
  `test_the_enriched_depth_spread_is_the_agents_own_drift_not_hand_assigned`).
- Tắt churn (`drift_rate=0.0`) → **độ trải biến mất**, depth quay về `{1}` (đo:
  counts `{1: 2248}` ở drift=0.0 so với `{1: 2248, 2: 1101}` ở 0.5). Full workflow
  **một mình không đủ** — churn là cơ chế sinh depth-2 trên carrier memory.

Độ trải đo được trên nền giàu (drift=0.5), carrier `memory`:

| đặc trưng | `harvest` cũ | `harvest_natural` | dải đo |
|---|---|---|---|
| **depth**   | `{1}` | **`{1, 2}`** | counts `{1: 2248, 2: 1101}` |
| derived | `{0}` | `{0}` | **vẫn hằng — xem §4** |
| size    | 42–549 | 42–557 | drift nối `" (rev t)"` nên đuôi dài ra |
| recency | =Δ | =Δ | ghép cặp tuổi được giữ (test khẳng định) |

## 3. Bảng AUC — {MatchedAttack, FrozenBank} × {nền cũ, nền giàu} × Δ

eps=0.0, pool `full`, carrier `memory`, `N_CERTIFY=900`, 20 seed chia
(`SPLIT_SEEDS`). Cột chính là **cận trên CI95 TRUNG BÌNH** (`hi_mean`) — tiêu chí câu
8; kèm ước lượng điểm (`auc_mean`) và số seed tự vượt trần 0.56 (`clear`).

### MatchedAttack

| Δ | nền cũ `hi_mean` (clear) | nền giàu `hi_mean` (clear) | **Δ(giàu−cũ)** | điểm cũ→giàu |
|---|---|---|---|---|
| 0 | 0.5414 (19/20) **ĐẠT** | **0.7056 (0/20) TRƯỢT** | **+0.1642** | 0.5081 → 0.6727 |
| 2 | 0.5394 (17/20) **ĐẠT** | **0.7328 (0/20) TRƯỢT** | **+0.1934** | 0.5047 → 0.6991 |
| 4 | 0.5411 (18/20) **ĐẠT** | **0.7318 (0/20) TRƯỢT** | **+0.1907** | 0.4945 → 0.6859 |

Nền cũ tái lập **đúng từng chữ số** con số đã ghim (`docs/reports/b5-auc.md`:
0.5414 / 0.5394 / 0.5411) — xác nhận harness đo đúng.

### FrozenBank (`FrozenPayloadAttack`)

| Δ | nền cũ `hi_mean` (clear) | nền giàu `hi_mean` (clear) | **Δ(giàu−cũ)** | điểm cũ→giàu |
|---|---|---|---|---|
| 0 | 0.7710 (0/20) TRƯỢT | 0.8145 (0/20) TRƯỢT | **+0.0435** | 0.7398 → 0.7850 |
| 2 | 0.7779 (0/20) TRƯỢT | 0.8386 (0/20) TRƯỢT | **+0.0607** | 0.7403 → 0.8042 |
| 4 | 0.8131 (0/20) TRƯỢT | 0.8618 (0/20) TRƯỢT | **+0.0487** | 0.7654 → 0.8180 |

Nền cũ tái lập đúng con số ghi trong `attacks.PENDING["frozen-payload"]`
(0.7710 / 0.7779 / 0.8131). FrozenBank có `n_pos` nhỏ hơn (900/614/359 so với
900/826/456) vì 3/12 record mang `derived_from` nên **bị đọc là item lan truyền và
loại** khỏi lớp sự kiện (`poisoned and not derived_from`) — hành vi cũ, không đổi.

## 4. Đọc kết quả — CẢ HAI kết luận cũ đều được kiểm, và không cái nào "cứu" được

**MatchedAttack TĂNG mạnh (≈0.54 → ≈0.73), lật từ ĐẠT sang TRƯỢT ở mọi Δ.** Đây
đúng là bằng chứng brief dự báo: MatchedAttack được **tinh chỉnh** để khớp nền suy
biến — payload của nó cố định `depth=1` ("Already matched, nothing to interpolate").
Trên nền cũ `depth` là hằng ở **cả hai lớp** nên không phân biệt gì; chỉ còn `size`,
mà `size` được khớp → AUC ≈ 0.5. Trên nền giàu, lớp benign trải sang depth 2, còn
payload vẫn kẹt ở depth 1 → **`depth` thành trục phân biệt thật**. Nó chỉ từng khớp
được một corpus suy biến.

Quy công đặc trưng (nền giàu = corpus PHỤ `natural=True, holdout=None`, carrier
`memory`, cận trên CI **trung bình** trên `SPLIT_SEEDS` (20), trung hoà từng đặc
trưng một bằng cách đặt cột đó về hằng 0 ở **cả hai** lớp):

| pipe | Δ | tất cả | bỏ `depth` | Δ-lệch | bỏ `size` | Δ-lệch | trục dẫn dắt |
|---|---|---|---|---|---|---|---|
| MatchedAttack | 0 | 0.7056 | **0.6128** | −0.0928 | 0.7091 | +0.0035 | **`depth`** |
| MatchedAttack | 2 | 0.7328 | **0.6375** | −0.0953 | 0.7305 | −0.0023 | **`depth`** |
| MatchedAttack | 4 | 0.7318 | **0.6400** | −0.0918 | 0.7333 | +0.0015 | **`depth`** |
| FrozenBank | 2 | 0.8386 | 0.8414 | +0.0028 | **0.6676** | −0.1710 | **`size`** |

`0/20` split vượt trần ở **cả chín** ô của MatchedAttack. `recency` và `derived`
khớp do cấu tạo ở hai phía nên không trung hoà ở đây.

> **RÚT một con số.** Bản trước, và `attacks.py` cùng
> `tests/gate2_validity/test_dist_matched_attack.py` chép theo, có câu *"trung hoà
> `depth` bằng tay đưa nó từ 0,78 xuống 0,71"*. **Không Δ nào, không corpus nào
> (chính hay phụ), không thống kê nào (cận trên trung bình hay ước lượng điểm)
> trong kho này cho ra cặp 0,78 → 0,71.** Cặp gần nhất là hàng Δ=2 ở trên
> (0,7328 → 0,6375). Con số cũ **bị rút**, không được phát biểu lại; ba hàng đo
> được ở trên thay chỗ nó, mỗi hàng kèm Δ và kèm corpus. Kết luận **định tính**
> không đổi và vẫn đứng: `depth` là trục dẫn dắt, phần dư là `size`.

Với MatchedAttack, `depth` một mình gần như giải thích hết (bỏ `size` còn 0.7305);
`size` cũng nhích lên (drift làm ghi chú dài ra, payload khớp bản gốc nên **ngắn
hơn** phân bố đã churn). Với FrozenBank, trục dẫn dắt là `size` (record đóng băng nằm
gọn trong dải 51–62 ký tự) — nên **làm giàu nền không cứu được nó**.

**FrozenBank KHÔNG giảm — nó TĂNG (≈+0.05).** Giả thuyết "đa dạng tệ hơn chỉ vì nền
nghèo" **KHÔNG đảo chiều**: sự tách được của FrozenBank vốn do `size`, một trục nền
giàu không chạm tới; thêm depth-2 vào lớp benign còn giúp tách các payload depth
0/1 (payload nông hơn trung bình benign). Kết luận cũ ("đa dạng làm tệ hơn") **được
củng cố**, không bị lật.

**Không attacker nào đạt 0.56 trên nền trung thực, ở bất kỳ Δ nào.** Theo brief, đây
**không** phải lỗi cần giấu: **bài toán nguỵ trang khó hơn cái nền cũ khiến ta
tưởng.** Nền đồng phục cũ khiến MatchedAttack trông như đã giải xong việc nguỵ trang;
nó chưa. Đó là câu cho vòng thiết kế tiếp (và cho thầy).

**Vì sao `derived` vẫn hằng — sự thật cấu trúc, không phải thiếu sót.** `agent.py`
chỉ đặt `derived_from` **kèm `poisoned=True`** (skill/branch inherit khi thấy độc;
drift ghi bản sửa không cha). Nên **không item lành memory nào có thể mang cha**, dù
chạy workflow gì. Payload đọc-thành-sự-kiện cũng `derived=0`, nên `derived` **chưa
bao giờ** phân biệt hai lớp — trục mà vòng tròn thật sự ghim là `depth`, và đó là
trục được gỡ. Nền lành thật có mang item benign-nhưng-derived hay không thì cần agent
thật (§6).

## 5. Bền vững với lựa chọn drift_rate (không phải dao trên lưỡi)

`NATURAL_DRIFT_RATE = 0.5` là **vật thay thế**. Quét (MatchedAttack, Δ=2, N=900):

| drift_rate | `hi_mean` | `auc_mean` | clear | đối chứng depth-2 |
|---|---|---|---|---|
| 0.3 | 0.6754 | 0.6406 | 0/20 | 977/3304 |
| 0.5 | 0.7328 | 0.6991 | 0/20 | 1286/3304 |
| 0.8 | 0.7546 | 0.7214 | 0/20 | 1468/3304 |

Kết luận định tính (MatchedAttack TRƯỢT trên nền giàu, AUC cao hơn hẳn 0.56) **không
phụ thuộc** giá trị cụ thể — mọi rate đều 0/20.

## 6. Còn chờ agent thật / key — `PENDING_MEASUREMENT["benign_real_agent"]`

Vẫn là MockAgent. Nền lành TRUNG THỰC cần agent LLM thật chạy sạch trên instance
thật (cần key), y như nửa `public ✓` của harm. Ghi tại
`analysis/benign_corpus.PENDING_MEASUREMENT["benign_real_agent"]`. Hai thứ số hôm
nay **không** thay được: (1) **tỉ lệ churn** do `NATURAL_DRIFT_RATE` chọn thay,
agent thật là đại lượng **đo được**; (2) `derived` không lấy được độ trải từ agent
này (sự thật cấu trúc). **Con số hôm nay là SÀN DƯỚI** của độ phân biệt: nền thật
chỉ có thể trải RỘNG HƠN, không hẹp hơn.

## 7. Bất biến & cổng

- **md5 hai đường experiment KHÔNG đổi**: `experiment.py --n 20` =
  `5655bd4956206148c3744045e3d17f61`; `--dataset swebench --n 20` =
  `2140bbe796ce925a19631a1c7a88f5e0` (bắt trước, xác nhận sau).
- `harvest` cũ và mọi số ghim theo nó **không đụng tới** — chỉ **thêm**
  `harvest_natural` đứng cạnh, `natural=False` là mặc định ở khắp nơi.
- Ba cổng xanh: **357 / 35 / 5**, zero skip (Gate 2 tăng 29→35 do 6 test mới).
- Hợp đồng không-trùng-control mỗi sự kiện: `harvest_natural` **từ chối** khi cung
  không đủ `n_per_event` (test khẳng định). K2/K3, tất định qua `seed_of`, stdlib
  thuần, không `hash()`/`itertools.count`.
