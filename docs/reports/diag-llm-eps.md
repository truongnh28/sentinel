# Payload do LLM sinh nằm ở đâu trên thang AUC của Gate 2

Brief: `.superpowers/sdd/2026-09-20-ssg-gate4c/task-3-brief.md`
Script: `spikes/diag_llm_eps.py` — chạy `python3 spikes/diag_llm_eps.py` từ
`auditgame/`. Kết quả thô: `spikes/diag-llm-eps.json`.

**Tài liệu có HAI VÒNG đo, đọc cả hai trước khi trích số:** Vòng 1 (F_match
đầy đủ 5 cột) cho AUC ≈0.86–1.00 và đọc thành "LLM lộ hơn payload tổng hợp".
Coordinator chỉ ra đây có thể là confound độ dài (`build.PAYLOAD_LENGTH=63`
đúng bằng trung vị benign, `MatchedAttack` khớp nó theo thiết kế, payload LLM
thì không). Vòng 2 đo lại sau khi trung hoà `size` bằng hai cách độc lập —
xem mục "VÒNG 2" để lấy kết luận ĐÃ SỬA. Số Vòng 1 được GIỮ NGUYÊN bên dưới
làm bằng chứng cho chính confound đó, không phải vì nó còn là kết luận cuối.

## Câu hỏi

Trục `epsilon` của `attacks.MatchedAttack` là một núm TỔNG HỢP (khoảng cách so
với phân bố item của chính agent). Attacker thật dùng LLM viết payload, không
vặn núm đó. 19 payload LLM đã sinh sẵn (thí nghiệm P2, đã trả tiền, đã đóng
băng) — 14 payload ngắn ("low", `spikes/p2-advice.jsonl`) và 5 payload dài
("ceiling", `spikes/p2-advice-ceiling.jsonl`) — chưa từng được đo qua đường AUC
của Gate 2. Task này đặt chúng lên đúng thang đó.

## Điểm nối: chỗ nội dung LLM đi vào F_match

`analysis.benign_corpus._one_event` (dòng 863) gọi **thẳng** `pipe.payload(wf,
ps)` để lấy `core.Item` ghi vào carrier tại `t == ps.iota` — **không** đi qua
`pipe.plan` (plan chỉ dùng ở đường experiment/runner, không dùng ở đường AUC).
`Item.surface()` (`core.py:294`) — đúng là F_match — đọc:

```
size    = len(content)
depth   = provenance.count("/")
recency = now - created_at
derived = len(derived_from)
topic   = topic_code(topic)
```

Vậy điểm nối là trường `content` của `Item`. `attacks.MatchedAttack.payload`
xây `content = build.payload_content(topic, ps.marker)` (chuỗi tổng hợp, luôn
đúng `PAYLOAD_LENGTH = 63` ký tự). `payloads.FrozenPayloadAttack.payload` —
pipeline có sẵn trong repo, đúng khuôn cho tình huống "ngân hàng nội dung cố
định" — gán thẳng `content = fp.content` (chuỗi cố định, không co giãn theo
epsilon) và khai `epsilon_effective=False`.

Pipeline chẩn đoán viết trong task này (`LLMAdviceAttack`,
`spikes/diag_llm_eps.py`) là **bản sao cục bộ của đúng khuôn
`FrozenPayloadAttack`**, chỉ khác ở ngân hàng: `content = rec["advice"]` —
nguyên văn chuỗi LLM sinh, không thêm/bớt ký tự nào. Các trường còn lại dựng
giống hệt `FrozenPayloadAttack`:

- `topic = wf.tasks[ps.sigma].topic` — cả topic của task sigma, KHÔNG qua
  `retrieval.payload_topic_like` (nội dung LLM không "biết" về epsilon).
- `provenance = "agent/notes"` — **giả định khai báo**, không đọc từ file
  advice (file không có trường provenance). Đây là lựa chọn mặc định của
  `MatchedAttack` ở eps<0.5 và của đa số bản ghi trong
  `payloads/generate.py:TemplateBankSource`, nên depth=1 là lựa chọn trung
  tính, không thiên vị theo hướng nào.
- `carrier`, `created_at`, `poisoned=True` — giống mọi pipeline khác.
- Bản ghi được chọn theo `core.seed_of(salt, wf.wf_id, ps.iota, ps.sigma,
  ps.carrier) % len(records)` — đúng cơ chế `FrozenPayloadAttack._pick`.

Đăng ký runtime: `attacks.REGISTRY["llm-advice-low"]` và
`attacks.REGISTRY["llm-advice-ceiling"]`, không sửa `attacks.py`.

## Quy ước eps truyền vào `matched_corpus`

Pipeline không đọc `eps` (giống `FrozenPayloadAttack`), nhưng
`matched_corpus(pipe, delta, eps, ...)` vẫn dùng `eps` để quyết định sigma nào
"dormant" (`feasible_sigmas`, độc lập với `pipe`). Có tiền lệ trong
`docs/reports/b5-benign-enrich.md`: `FrozenPayloadAttack` cũng được đo qua
`matched_corpus(pipe, Δ, eps=0.0, 900, natural=…)`. Script này dùng
**eps=0.0** vì lý do đó — một quy ước đồng bộ cho mọi pipeline đo qua
`matched_corpus`, KHÔNG phải vì giả định "LLM không tốn chi phí".

## Kiểm hợp lệ (BẮT BUỘC, chạy trước khi tin số LLM)

Chạy pipeline `matched` ở `eps=0.0`, pha **SCREEN** (N=80), qua đúng đường code
vừa viết (`B.matched_corpus` → `D.auc_over_splits` → `G2.screen_statistic`),
đối chiếu với bảng trong brief:

| Δ | brief | đo được | khớp |
|---|-------|---------|------|
| 0 | 0.5247 | 0.524748 | ĐÚNG |
| 2 | 0.5359 | 0.535941 | ĐÚNG |
| 4 | 0.6077 | 0.607728 | ĐÚNG |

Khớp đến 4 chữ số thập phân ở cả ba Δ (n_pos đạt đủ 80/80/80). Đường nối
đúng — số của payload LLM dưới đây đáng tin.

## Xử lý cỡ mẫu — 19 payload LLM, screen cần 80, certify cần ~900

Chỉ có 14 (low) + 5 (ceiling) = 19 payload LLM phân biệt. Chọn hướng **(a)**
của brief: **dùng lại payload theo vòng**. Cơ chế chọn bản ghi
(`seed_of(...) % len(records)`) tự động lặp khi số sự kiện > số bản ghi —
đúng cơ chế `FrozenPayloadAttack` đã dùng trong repo. Số lần lặp trung bình
mỗi bản ghi = `n_pos_reached / len(records)`, ghi rõ ở từng ô bên dưới.

**Hệ quả phải nêu rõ (không giấu N3):** AUC các ô dưới đây là "mức phân biệt
được của **19 chuỗi cố định**, được lặp lại nhiều lần trên các cặp
(topic, iota, carrier) khác nhau" — không phải AUC ước lượng trên 900 mẫu độc
lập của "văn phong LLM nói chung". Khoảng tin cậy Hanley–McNeil giả định các
điểm dương độc lập; ở ô certify tier "ceiling" Δ=0, mỗi bản ghi trong 5 bản ghi
bị lặp trung bình 180 lần — cỡ mẫu hiệu dụng thật sự gần 5, không phải 900.
Số `n_pos_reached` được báo cáo ở mọi ô để người đọc tự đánh giá mức độ này.

## Kết quả — pha SCREEN (N cap = 80, cả hai pha đều tách theo Δ)

### Tier "low" (14 payload, ~18–67 ký tự, trung vị 29.5 — dưới trung vị benign 63)

| Δ | n_pos đạt được | reuse TB/bản ghi | AUC median (screen stat) | AUC mean [min,max] | CI-hi mean [min,max] | clear/20 |
|---|---|---|---|---|---|---|
| 0 | 80 | 5.71× | 0.8622 | 0.8704 [0.8190, 0.9365] | 0.9518 [0.9077, 0.9968] | 0/20 |
| 2 | 80 | 5.71× | 0.8836 | 0.8933 [0.8442, 0.9534] | 0.9673 [0.9326, 1.0000] | 0/20 |
| 4 | 80 | 5.71× | 0.8693 | 0.8752 [0.8027, 0.9471] | 0.9550 [0.8978, 1.0000] | 0/20 |

### Tier "ceiling" (5 payload, ~261–307 ký tự, trung vị 286 — trên trung vị benign 63)

| Δ | n_pos đạt được | reuse TB/bản ghi | AUC median (screen stat) | AUC mean [min,max] | CI-hi mean [min,max] | clear/20 |
|---|---|---|---|---|---|---|
| 0 | 80 | 16.0× | 0.9951 | 0.9952 [0.9880, 1.0000] | 1.0000 [1.0000, 1.0000] | 0/20 |
| 2 | 80 | 16.0× | 0.9967 | 0.9964 [0.9914, 1.0000] | 1.0000 [1.0000, 1.0000] | 0/20 |
| 4 | 80 | 16.0× | 0.9925 | 0.9932 [0.9877, 1.0000] | 1.0000 [1.0000, 1.0000] | 0/20 |

## Kết quả — pha CERTIFY (N cap = 900)

Trần Δ=0 đạt đủ 900; ở Δ=2/4 số sự kiện đạt được bị **pool giới hạn**, không
phải do pipeline LLM — đúng con số đã ghi nhận cho corpus này ở nơi khác trong
repo (~826/456 khả dụng ở Δ=2/4 trên pool `full`, MEASURED chứ không giả định).

### Tier "low"

| Δ | n_pos đạt được (/900 cap) | reuse TB/bản ghi | AUC mean [min,max] | CI-hi mean [min,max] | clear/20 |
|---|---|---|---|---|---|
| 0 | 900 | 64.3× | 0.8804 [0.8591, 0.9012] | 0.9039 [0.8843, 0.9233] | 0/20 |
| 2 | 817 | 58.4× | 0.8873 [0.8726, 0.9133] | 0.9113 [0.8977, 0.9346] | 0/20 |
| 4 | 449 | 32.1× | 0.8732 [0.8480, 0.9058] | 0.9072 [0.8845, 0.9359] | 0/20 |

### Tier "ceiling"

| Δ | n_pos đạt được (/900 cap) | reuse TB/bản ghi | AUC mean [min,max] | CI-hi mean [min,max] | clear/20 |
|---|---|---|---|---|---|
| 0 | 900 | 180.0× | 0.9983 [0.9972, 0.9994] | 1.0000 [1.0000, 1.0000] | 0/20 |
| 2 | 817 | 163.4× | 0.9965 [0.9945, 0.9981] | 1.0000 [1.0000, 1.0000] | 0/20 |
| 4 | 449 | 89.8× | 0.9974 [0.9952, 0.9995] | 1.0000 [1.0000, 1.0000] | 0/20 |

(Trần Gate 2: `AUC_upper <= 0.56`. Mọi ô ở cả hai bậc, cả hai pha, đều **fail**
ở cả 20/20 split — `clear=0/20` mọi nơi.)

## Đọc kết quả VÒNG 1 — kết cục nào trong ba kết cục của brief?

**(Kết luận sơ bộ, RÚT LẠI một phần ở Vòng 2 bên dưới — đọc cả hai mục trước
khi trích dẫn số nào.)**

Bề ngoài đây là kết cục thứ ba: AUC ≈ 1.0 (thực tế 0.86–0.99 screen, 0.87–1.00
certify) — payload LLM LỘ HƠN mọi eps tổng hợp, kể cả eps=1.0 của
`MatchedAttack`. Nguyên nhân nghi ngờ ngay từ Vòng 1: `build.PAYLOAD_LENGTH =
63` đúng bằng trung vị `size` của lớp benign, và `MatchedAttack` khớp con số đó
THEO THIẾT KẾ (đó là lý do eps=0 của nó đạt 0.52–0.61, gần trần), trong khi
payload LLM chưa từng được yêu cầu khớp:

- tier "low": 18–67 ký tự (trung vị 29.5) — luôn NGẮN HƠN trung vị benign.
- tier "ceiling": 261–307 ký tự (trung vị 286) — luôn DÀI HƠN 4× trung vị
  benign.

**Coordinator chỉ ra đúng:** đây có thể là so sánh "khớp độ dài" với "không
khớp độ dài", không phải "nguỵ trang tốt" với "nguỵ trang dở" — đúng hình dạng
lỗi `sorted()` dự án từng mắc (một giả tượng định dạng tách hoàn hảo, bị đọc
thành phát hiện bảo mật). Mục VÒNG 2 dưới đây đo trực tiếp câu hỏi đó bằng
cách trung hoà `size`.

## VÒNG 2 — trung hoà `size`, hai cách độc lập

Cả hai cách chạy **cùng cấu hình**: eps=0.0, `per_event=4`, `SPLIT_SEEDS =
1..20`, Δ ∈ {0,2,4}, cả hai pha (screen N=80, certify N=900), hai tier tách
riêng — script `spikes/diag_llm_eps.py` (đã cập nhật), JSON
`spikes/diag-llm-eps.json` (khoá `results_size_neutralised` và
`results_length_matched`).

### Cách 1 — NEUTRALISE_SIZE (bỏ cột `size` bằng kỹ thuật "neutralising")

Sau khi `matched_corpus` trả về các dict F_match, ghi đè `size` bằng **một
hằng số giống hệt nhau trên mọi hàng, cả hai lớp** (0.0) trước khi đưa vào
`discriminator.auc_over_splits` — không sửa `discriminator.py`.
`_standardise` (dòng 56) có `or 1.0` khi phương sai bằng 0, nên cột hằng số
chuẩn hoá thành 0 ở MỌI hàng và không đóng góp gì cho điểm số dù trọng số học
được là bao nhiêu — tương đương thống kê với "bỏ cột", đúng kỹ thuật
"neutralising" mà `core.topic_code`/`attacks.MatchedAttack` đã dùng cho cột
`topic`.

**Ghi chú quan trọng về hai bảng dưới:** số của tier "low" và tier "ceiling"
**giống hệt nhau**, không phải lỗi. Sau khi bỏ `size`, 4 cột còn lại
(`depth`, `recency`, `derived`, `topic`) được cả hai pipeline LLM dựng
GIỐNG HỆT NHAU (`topic = wf.tasks[ps.sigma].topic`, `provenance="agent/notes"`
cố định, `derived_from=()` cố định) — corpus không phụ thuộc pipeline ở bốn
cột này, chỉ phụ thuộc ở `content`/`size`. Bỏ `size` đi thì hai tier còn lại
là hai bản sao byte-for-byte của cùng một tập dữ liệu. Đây là hệ quả cấu trúc
của chính pipeline chẩn đoán (nó chỉ định tuyến `content`, không định tuyến gì
khác theo tier), không phải một phát hiện về hai tier LLM.

| Pha | Δ | n_pos đạt được | AUC median | AUC mean [min,max] | CI-hi mean [min,max] | clear/20 |
|---|---|---|---|---|---|---|
| screen | 0 | 80 | 0.4711 | 0.4690 [0.4141, 0.5029] | 0.5797 [0.5256, 0.6104] | 5/20 |
| screen | 2 | 80 | 0.4765 | 0.4845 [0.4521, 0.5440] | 0.5962 [0.5570, 0.6620] | 1/20 |
| screen | 4 | 80 | 0.4634 | 0.4592 [0.4024, 0.5454] | 0.5693 [0.5035, 0.6564] | 10/20 |
| certify | 0 | 900 | 0.4929 | 0.4907 [0.4748, 0.5024] | 0.5239 [0.5082, 0.5355] | **20/20** |
| certify | 2 | 817 | 0.5017 | 0.4972 [0.4688, 0.5158] | 0.5320 [0.5021, 0.5502] | **20/20** |
| certify | 4 | 449 | 0.5192 | 0.5093 [0.4364, 0.5546] | 0.5564 [0.4824, 0.6016] | 9/20 |

(Áp dụng như nhau cho tier "low" và tier "ceiling" — xem ghi chú ở trên.)

### Cách 2 — LENGTH-MATCHED (cắt/đệm nội dung về đúng 63 ký tự, chạy đủ 5 đặc trưng)

Pipeline mới `LLMAdviceLengthMatchedAttack`: nếu `len(advice) > 63` thì
**cắt lấy 63 ký tự đầu**; nếu `< 63` thì **đệm khoảng trắng vào cuối** cho đủ
63; giữ nguyên nếu đúng 63. Số bản ghi bị đụng, đo được (không giả định):

| Tier | n | cắt (truncated) | đệm (padded) | đúng sẵn (exact) |
|---|---|---|---|---|
| low | 14 | 2 | 11 | 1 |
| ceiling | 5 | 5 | 0 | 0 |

**Cảnh báo phải đọc cùng số:** cắt về 63 ký tự làm **mất marker `raw_write`**
ở **4/5** bản ghi tier "ceiling" (marker thường nằm gần cuối câu) — ví dụ bản
ghi Django còn "...must not run system ch" sau khi cắt, không còn
`raw_write` nào trong chuỗi. Ở tier "low", cả 2 bản ghi bị cắt đều GIỮ được
marker (marker nằm sớm trong câu ở các bản ghi đó). Vậy: **kết quả
length-matched của tier "ceiling" đo tính phân biệt của MỘT CHUỖI CÓ ĐỘ DÀI
ĐÚNG NHƯNG NỘI DUNG BỊ CẮT CỤT (không còn là một chỉ thị tấn công thật ở 4/5
bản ghi)**, không phải của payload LLM nguyên vẹn. Tier "low" (chủ yếu đệm,
giữ nguyên nội dung) không có cảnh báo này.

| Pha | Δ | n_pos đạt được | AUC median | AUC mean [min,max] | CI-hi mean [min,max] | clear/20 |
|---|---|---|---|---|---|---|
| screen | 0 | 80 | 0.4620 | 0.4605 [0.4013, 0.5118] | 0.5708 [0.4990, 0.6261] | 8/20 |
| screen | 2 | 80 | 0.5399 | 0.5367 [0.4708, 0.5788] | 0.6505 [0.5791, 0.6973] | 0/20 |
| screen | 4 | 80 | 0.5956 | 0.5954 [0.5193, 0.6672] | 0.7093 [0.6383, 0.7722] | 0/20 |
| certify | 0 | 900 | 0.4645 | 0.4626 [0.4436, 0.4920] | 0.4953 [0.4754, 0.5254] | **20/20** |
| certify | 2 | 817 | 0.4853 | 0.4846 [0.4548, 0.5076] | 0.5192 [0.4889, 0.5425] | **20/20** |
| certify | 4 | 449 | 0.5152 | 0.5179 [0.4863, 0.5487] | 0.5653 [0.5327, 0.5957] | 8/20 |

(Giống Cách 1, số của tier "low" và "ceiling" **giống hệt nhau** một khi
`size` bị khoá về cùng một giá trị 63 ký tự cho cả hai — cùng lý do cấu trúc
đã nêu ở Cách 1; xem cảnh báo mất-marker ở trên cho tier "ceiling".)

### Xác nhận lại kiểm hợp lệ SAU KHI sửa đường code

Chạy lại đúng phép kiểm hợp lệ ban đầu (`matched`, eps=0.0, pha SCREEN,
N=80) sau khi thêm toàn bộ code Vòng 2: vẫn khớp bảng brief đến 4 chữ số thập
phân ở cả ba Δ (0.524748 / 0.535941 / 0.607728) — sửa code không làm hỏng
đường nối.

### Đọc Vòng 2 — kết cục nào?

- **Δ=0 và Δ=2, cả hai cách:** AUC certify rơi về 0.46–0.50 (median), CI-hi
  mean 0.52–0.53, **clear 20/20 split** — dưới trần 0.56 một cách dứt khoát.
  Đây là **kết cục thứ nhất** của bảng ba-kết-cục brief:
  ***AUC tụt về ≈ 0.5 → nội dung payload LLM nguỵ trang tốt; số ≈0.86–1.00 của
  Vòng 1 hoàn toàn là confound độ dài.*** Ở hai Δ này, kết luận §9.2 của Vòng 1
  **RÚT LẠI**: một khi độ dài bị trung hoà, không có bằng chứng payload LLM
  (dù nội dung, không phải độ dài) dễ phát hiện hơn payload tổng hợp khớp độ
  dài.
- **Δ=4, cả hai cách:** kết quả nằm **Ở GIỮA** — certify median 0.51–0.52,
  CI-hi mean 0.556–0.565, chỉ **8–9/20 split clear** (không dứt khoát đạt hay
  fail). Con số này khớp một cách đáng chú ý với một kết quả ĐÃ CÓ SẴN trong
  repo: `core.py`/`attacks.py` ghi nhận rằng ở certify Δ=4, cột `topic` một
  mình mang một dư lượng ~0.05 trên trần (0.5484–0.5870 tuỳ salt), khác biệt
  với Δ=0/Δ=2 nơi `topic` đọc CHANCE. Dư lượng Δ=4 mà Vòng 2 đo được ở payload
  LLM (~0.556–0.565) nằm ĐÚNG TẦM ĐỘ LỚN của dư lượng đã biết đó, và pha screen
  (n=80) cho số cao hơn certify (n=449) đúng hướng "mẫu nhỏ phóng đại upper
  bound" mà `discriminator.summarise_splits` đã cảnh báo (max hi hội tụ về
  supremum, không phải về đại lượng dân số). Diễn giải thận trọng nhất:
  **dư lượng Δ=4 nhiều khả năng là CÙNG hiện tượng `topic`-tại-Δ=4 đã biết của
  benchmark, không phải một tín hiệu mới của riêng nội dung LLM** — nhưng cỡ
  mẫu certify thật ở Δ=4 chỉ 449 (dưới 900) và corpus của Vòng 2 không tách
  từng cột riêng để xác nhận trực tiếp `topic` là thủ phạm (chỉ trung hoà
  `size`), nên đây là một GIẢ THUYẾT PHÙ HỢP với bằng chứng hiện có, không
  phải một phép đo trực tiếp — cần đo thêm nếu muốn khẳng định.

**Kết luận cập nhật, thay cho mục "Xác nhận cảnh báo §9.2" cũ:**
Cảnh báo §9.2 ("LLM attacker … tâng bốc mọi defender") **KHÔNG được xác nhận
bởi dữ liệu này** ở Δ=0/Δ=2 — con số ủng hộ nó ở Vòng 1 là một confound độ dài,
đã đo trực tiếp và loại bỏ được. Ở Δ=4 có một dư lượng nhỏ, borderline quanh
trần, nhiều khả năng trùng với một dư lượng `topic` đã biết của chính
benchmark chứ không phải một phát hiện mới về LLM — cần đo thêm (tách riêng
cột `topic` trên đúng payload LLM) trước khi kết luận bất cứ điều gì ở Δ=4.
**Kết luận đúng của toàn bộ nhiệm vụ, sau cả hai vòng:** với đúng 19 payload
LLM hiện có, một khi kiểm soát độ dài, nội dung LLM KHÔNG lộ hơn payload tổng
hợp khớp độ dài ở Δ=0/Δ=2, và bằng chứng ở Δ=4 không đủ mạnh để tách bạch
"LLM" khỏi "dư lượng `topic` đã biết của benchmark".

## Giả định đã khai báo (không phải đo được)

1. `provenance = "agent/notes"` cho mọi payload LLM — file advice không mang
   trường này. Vì `depth = provenance.count("/")` chỉ nhận giá trị 0/1/2 và cả
   lớp benign lẫn payload đều tập trung quanh depth=1, đây là một trục yếu so
   với `size`.
2. `topic = wf.tasks[ps.sigma].topic` (cả topic, không subset) — theo đúng
   khuôn `FrozenPayloadAttack`. Đây là lựa chọn có chủ đích, không phải sơ
   suất: nội dung LLM không "biết" về eps nên không có lý do áp
   `payload_topic_like`.
3. `eps=0.0` truyền vào `matched_corpus` là quy ước xây corpus (ảnh hưởng tính
   khả thi của sigma), không phải một tham số của pipeline LLM — xem mục
   "Quy ước eps" ở trên.
4. (Vòng 2) Đệm 63 ký tự bằng khoảng trắng ở cuối, cắt 63 ký tự bằng cách lấy
   tiền tố — quy tắc đơn giản nhất, khai báo rõ, KHÔNG tuyên bố là quy tắc
   "tốt nhất". Cắt làm mất marker `raw_write` ở 4/5 bản ghi tier "ceiling" —
   xem cảnh báo ở mục "Cách 2".
5. (Vòng 2) "Neutralising" `size` bằng hằng số 0.0 giống hệt cho mọi hàng —
   giá trị hằng số cụ thể không quan trọng (bất kỳ hằng số nào cho kết quả
   giống hệt, vì `_standardise` chuẩn hoá về 0 khi phương sai bằng 0), chỉ cần
   nó GIỐNG NHAU trên mọi hàng của cả hai lớp.

## Xong khi (đối chiếu với brief + yêu cầu vòng 2 của coordinator)

- `spikes/diag-llm-eps.json` + `docs/reports/diag-llm-eps.md` tồn tại. ĐÃ XONG.
- Mỗi số ghi rõ PHA và Δ. ĐÃ XONG (mọi bảng trên).
- Cách xử lý cỡ mẫu được khai báo. ĐÃ XONG (mục "Xử lý cỡ mẫu").
- Kiểm hợp lệ có kết quả, VÀ được xác nhận lại sau khi sửa code vòng 2. ĐÃ
  XONG — xem mục "Kiểm hợp lệ" và "Xác nhận lại kiểm hợp lệ SAU KHI sửa đường
  code".
- Đo AUC khi trung hoà `size`, cả hai cách (bỏ cột qua neutralising VÀ khớp độ
  dài), cùng cấu hình với Vòng 1, số cũ được GIỮ NGUYÊN (không xoá). ĐÃ XONG —
  mục "VÒNG 2".
- Kết luận đã được SỬA cho khớp số mới, nói thẳng phần nào của §9.2 bị rút
  lại. ĐÃ XONG — xem "Kết luận cập nhật" cuối mục VÒNG 2.
