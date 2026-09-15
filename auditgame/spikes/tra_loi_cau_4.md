# Câu 4 — Gom workflow theo repo có đủ N=100 workflow không? (a3, Bước 3.6)

Ngày đo: 2026-09-16.

**Đây là phép XÁC MINH, không phải phép khám phá** — câu 4 đã chốt ngày 16/09/2026
với đáp án `H=8` trên pool Verified cho **58 workflow · 42%**. Nhiệm vụ của bước
này chỉ là chạy đúng `retrieval.topic_of` (qua `topics.topic_of_instance`) trên dữ
liệu thật và xác nhận con số đó vẫn tái lập được.

Lệnh chạy:

```bash
cd HCMUT/code/Sentinel/auditgame
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
