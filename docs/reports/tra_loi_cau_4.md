# Câu 4 — Gom workflow theo repo có đủ N=100 workflow không? (a3, Bước 3.6)

Ngày đo: 2026-09-16.

**Đây là phép XÁC MINH, không phải phép khám phá** — câu 4 đã chốt ngày 16/09/2026
với đáp án `H=8` trên pool Verified cho **58 workflow · 42%**. Nhiệm vụ của bước
này chỉ là chạy đúng `retrieval.topic_of` (qua `topics.topic_of_instance`) trên dữ
liệu thật và xác nhận con số đó vẫn tái lập được.

Lệnh chạy:

```bash
cd auditgame
python3 -c "
import swebench_dataset as S
for pool in ('verified','full'):
    tk=S.SWEBenchDataset(pool).stats(H=8); can=100
    thieu=max(0,can-tk['non_reused_workflows'])
    print(f\"{pool:9s} {tk['instances']:>5d} instance · {tk['repos']:>2d} repo · \"
          f\"{tk['repos_with_H']:>2d} repo đủ 8 · {tk['non_reused_workflows']:>3d} wf KHÔNG dùng lại\")
    print(f\"          -> muốn {can} wf thì phải dùng lại {100*thieu/can:.0f}%\")"
```

## Số đo được

```
verified    500 instance · 12 repo · 10 repo đủ 8 ·  58 wf KHÔNG dùng lại
          -> muốn 100 wf thì phải dùng lại 42%
full       2294 instance · 12 repo · 12 repo đủ 8 · 281 wf KHÔNG dùng lại
          -> muốn 100 wf thì phải dùng lại 0%
```

Đã chạy lệnh trên trong **hai tiến trình Python riêng biệt** (không chỉ hai lần
gọi trong cùng một tiến trình) và `diff` hai output: **giống nhau từng byte**.
Kiểm tra thêm ở mức sâu hơn Bước 3.6 đòi hỏi — dựng `workflows(10, 8, seed=1)`
thật (bước duy nhất mà topic *dạng frozenset* thực sự chạm tới `Task.topic`) và
in `str(t.topic)` cho từng task ở hai tiến trình khác nhau — cũng khớp từng byte.
Điều này xác nhận topic không rơi vào con đường không tất định của thứ tự lặp
`frozenset` (xem mục "Bẫy tất định" bên dưới).

## Đối chiếu với con số đã chốt

| Pool | Instance | Repo | H=8 (đo được) | H=8 (đã chốt 16/09) |
|---|---|---|---|---|
| **Verified** | 500 | 12 | **58 wf · 42%** | **58 wf · 42%** |
| Full | 2294 | 12 | **281 wf · 0%** | 281 wf · 0% |

**Kết quả: KHỚP ĐÚNG cả hai con số cho pool Verified (58 workflow, 42% dùng
lại tối thiểu để đạt N=100) và pool Full (281 workflow, 0%).** Dữ liệu trên đĩa
(`data/swebench_verified.jsonl` = 500 dòng, `data/swebench_full.jsonl` = 2294
dòng) chưa đổi so với lúc chốt câu 4, và tokenization vẫn đi đúng qua
`retrieval.topic_of` (qua `topics.files_of_patch` + `topics.topic_of_instance`,
không có logic gom nhóm nào khác chen vào `_by_repo`/`_segments`). Không cần
dừng lại tìm nguyên nhân lệch — vì không có lệch.

## Đọc con số

- 12 repo trong Verified, nhưng chỉ 10/12 repo có ≥ 8 instance — 2 repo còn lại
  quá nhỏ để tạo dù chỉ một workflow H=8.
- 58 workflow "không dùng lại" (mỗi segment H=8 liên tiếp theo `created_at`, không
  chồng lấn) là con số THẬT của Verified ở H=8 — thấp hơn nhiều so với N=100 vì
  500 instance chia cho 12 repo, phân bố không đều giữa các repo.
- Muốn đủ N=100 workflow phải dùng lại 42% trong số đó — nằm trong ngưỡng trần
  tái sử dụng ≤ 2 lần/instance mà câu 4 đã chốt (42% với trần 2 vẫn ký được;
  xem lý do trong phần "Vì sao trần 2" ở `task-3-brief.md`).
- Trên pool Full, 12/12 repo đều đủ 8 instance và có sẵn 281 workflow không
  dùng lại — thừa xa N=100, nên tỉ lệ dùng lại cần thiết là 0%.

## Bẫy tất định (frozenset topic)

`topics.topic_of_instance` trả về `frozenset`, và thứ tự lặp của `frozenset`
phụ thuộc vào việc băm chuỗi được ngẫu nhiên hoá theo tiến trình
(`PYTHONHASHSEED`) — không tất định giữa hai lần chạy Python. `swebench_dataset.py`
bọc topic trong lớp con `Topic(frozenset)`, ghi đè `__str__`/`__repr__` thành
dạng chuẩn `"|".join(sorted(topic))`. Nhờ vậy mọi nơi topic từng có nguy cơ rơi
thẳng vào `core.seed_of` hay vào chuỗi nội dung (`agent.py`, `build.py`) đều tự
động nhận dạng chuỗi tất định — mà không phải sửa các file đó. Bằng chứng đo
được: chạy `workflows(10, 8, seed=1)` và in `str(topic)` của từng task ở hai
tiến trình Python riêng biệt cho kết quả **giống nhau từng byte** (xem trên).

---

## Cập nhật 2026-09-16 — Bước 4 của PHẦN 4 (SPEC-P1a) đã được hiện thực

Con số 58 / 42% ở trên vẫn đúng, nhưng nó trả lời **câu hỏi gom nhóm** (bước 1–3),
không phải câu hỏi "workflow có dựng được attack không". Bước 4 — *"LOẠI workflow
không có cặp (i, i+Δ) cùng topic vượt θ cho Δ cần quét"*, mà chính spec gọi là
**N3 ở mức dataset** — trước đây chưa hiện thực. Nay đã có trong
`SWEBenchDataset._segments`, và kết quả đo được là một **phát hiện**, không phải
một chi tiết:

| Pool | H | Workflow sau bước 1–3 | Sống sót bước 4 (Δ ∈ {0,1,2,4}, θ = 1.0) |
|---|---|---|---|
| Verified | 8 | 58 | **0** |
| Full | 8 | 281 | **2** |

Số workflow chịu được **từng** Δ riêng lẻ trên Verified: Δ=1 → 8, Δ=2 → 6, Δ=4 → 2
(Δ=0 là cắm-và-nổ cùng một task nên luôn được). Không workflow nào chịu được cả ba.

Vì sao: `build.plan_poison` **không** đòi task ι và task σ phải liên quan — nó chỉ
cấm topic của σ xuất hiện trong [ι, σ). Sau đó `build.inject` đóng dấu payload
bằng **chính topic của σ**, nên payload được truy xuất ở σ bất kể hai task thật có
liên quan hay không. Đo được: chỉ **7/560 = 1,25%** cặp task trong cùng workflow
chia sẻ topic trên dữ liệu thật (mock: 104/560 = 18,57%), và agent truy xuất được
trạng thái cũ ở **3,8%** task sạch trên dữ liệu thật so với **45,0%** trên mock.
Nói cách khác: "hai task liên quan" là **sản phẩm của phép tiêm**, đúng thứ mà
phép sắp theo `created_at` sinh ra để tránh.

Bộ lọc có tác dụng đúng như mong đợi ở từng Δ — với Δ=1 tỉ lệ cặp cùng topic tăng
1,25% → 7,59% và tỉ lệ truy xuất 3,8% → 20,3% — nhưng tập thoả **toàn bộ** lưới Δ
là rỗng.

Hệ quả: `datasets.py` ghi `swebench` vào `PENDING` **kèm lý do đo được** thay vì
`REGISTRY`, và `experiment.py --dataset swebench` in một lời từ chối thay vì một
bảng harm. Đây là N3 đúng nghĩa: ô ngoài phạm vi ghi **lý do**, không ghi harm = 0.

θ **không** được hạ để giữ số lượng. θ = 1.0 vì `core.CarrierStore.retrieve` so
topic bằng `==`; workflow được nhận ở θ = 0.5 vẫn không dựng được attack dưới `==`.
Đo thêm để định hướng: nếu truy xuất trở thành **graded**, số workflow sống sót
bước 4 trên Verified (Δ ∈ {1,2,4}) là 0 ở θ=1.0, 1 ở θ=0.75, **14 ở θ=0.5**,
21 ở θ=0.34. Tức là nút thắt thật sự là câu hỏi 3 (truy xuất graded), chứ không
phải kích thước pool.
