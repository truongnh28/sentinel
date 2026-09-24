# Tiền đăng ký — sửa seed của agent (#20)

**Ngày:** 25/09/2026 · **Khai trước khi sửa mã và trước khi chạy lại.**

## 1. Lỗi

`MockAgent.run_task` gieo bằng `seed_of(seed, t)`. `runner.run_once` truyền vào **seed thô**, không có
`wf_id`. Với một seed, task thứ $t$ của mọi workflow nhận cùng một lượt rút (adopt, skill,
queue, drift, solve). Độ biến thiên giữa các workflow vì vậy chỉ đến từ cấu trúc workflow, còn
độ biến thiên của agent thực ra chỉ có $3 \times 8$ lượt rút cho cả lưới. Bằng chứng (W10): harm
của B1 ở ô headline là 0,18 dưới seed 2 và 0,86 dưới seed 3.

## 2. Cách sửa

Ở **chỗ gọi** trong trò chơi (`runner.run_once`, và hai công cụ gọi agent theo cùng lối:
`theory.py`, `tools/measure_c.py`), seed truyền cho agent là `core.agent_seed(wf_id, seed)`.
`agent.py` **không đổi**. Corpus lành tính của cổng 2 gọi agent trực tiếp với seed đã tách theo
task, nên nó và các md5 đã ghim **giữ nguyên từng byte**. Thêm `agent.py` vào `freeze.SOURCE`.
Sau khi sửa: đóng băng lại, rồi chạy lại mọi bảng mà README trích.

## 3. Dự đoán

| # | Dự đoán | Sai khi nào |
|---|---|---|
| F1 | Độ lợi theo **từng seed riêng lẻ** ở ô headline co lại: max − min < 30 điểm (trước sửa: 107 điểm, −56 … +51) | ≥ 30 điểm |
| F2 | Harm của B1 theo từng seed riêng lẻ ở ô headline nằm trong khoảng 0,15 quanh trung bình của chúng (trước sửa: 0,18 … 0,86) | vượt |
| F3 | Kết luận #13/#17 **đứng**: ở ngân sách 0,75, ít nhất một ô $\Delta = 2$ được chứng nhận có CI hoàn toàn trên 15% | không ô nào |
| F4 | Ở ngân sách 0,3205, vẫn **không** ô được chứng nhận nào có CI trên 15% ($N = 100$) | có ô |
| F5 | Cổng 2 (corpus lành tính, bảng chứng nhận) **y hệt**: 203/205, cùng hai test đỏ đã biết | lệch — khi đó sửa đã rò sang corpus, là **lỗi** |
