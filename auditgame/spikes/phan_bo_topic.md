# Phân bố |topic| thật trên SWE-bench Verified (a2, Bước 2.5)

Ngày đo: 2026-09-16.

Lệnh chạy:

```bash
cd HCMUT/code/Sentinel/auditgame
python3 -c "
import json, topics
rows=[json.loads(l) for l in open('data/swebench_verified.jsonl')]
p=topics.distribution(rows)
print('n =',p['n'],'  trung vị |topic| =',p['median'])
print('histogram:',p['hist'])"
```

## Số đo được

```
n = 500   trung vị |topic| = 4
histogram: {2: 17, 3: 217, 4: 148, 5: 83, 6: 12, 7: 8, 8: 8, 9: 4, 10: 1, 11: 1, 32: 1}
```

Đã chạy lại lệnh trên hai lần liên tiếp: cùng `n`, cùng `median`, cùng `hist` từng
chữ số — không có rò rỉ thứ tự lặp của `frozenset` vào kết quả (measurement chỉ
dùng `len(topic)`, không dùng nội dung topic để băm hay in chuỗi).

## Đối chiếu với dự đoán

`PLAN.md` (dòng 287, bảng "Đợt 1") dự đoán trung vị = 4 trước khi đo. Số đo được
trên toàn bộ 500 instance của SWE-bench Verified **khớp đúng: trung vị = 4**.

Theo cổng quyết định ở `PLAN.md` (mục "Cổng quyết định — đọc trước khi bắt đầu",
sau Task 2): trung vị $\le 3$ ⇒ dừng, phải token hoá mịn hơn (đổi thiết kế);
trung vị $> 3$ ⇒ đi tiếp, chốt $\theta$ bằng dữ liệu. Với trung vị đo được là 4
(> 3), điều kiện dừng **không** kích hoạt — có thể chốt $\theta$ dựa trên phân bố
này ở task sau.

## Đọc histogram

- Phần lớn instance (217/500 ≈ 43%) có |topic| = 3, tức gold patch sửa đúng một
  file có đường dẫn 3 cấp (ví dụ `astropy/modeling/separable.py`).
- 17 instance có |topic| = 2 (patch chỉ chạm một file 2 cấp, hoặc topic của các
  file trùng lặp nhiều token).
- Đuôi phải trải khá dài (đến |topic| = 32 cho đúng 1 instance) — vài patch gold
  chạm rất nhiều file/thư mục khác nhau. Trung vị (4) ổn định hơn trung bình cho
  loại phân bố lệch phải như thế này, đúng lý do `distribution()` báo cáo
  `median` chứ không phải `mean`.
