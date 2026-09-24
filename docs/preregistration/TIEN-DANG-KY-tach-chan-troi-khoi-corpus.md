# Tiền đăng ký — tách chân trời khỏi corpus (issue #15)

**Ngày:** 24/09/2026 · **Khai trước khi chạy, trước mốc đóng băng 29/09**

---

## 1. Sự việc

Cùng $\Delta = 4$, detector mid, $N = 40$, `SSG-full receding` ra **+17,8%** ở
$H = 8$ nhưng **+4,0%** ở $H = 12$ (`spikes/grid-usd-H12-delta8.txt`). Phép so
này **lẫn hai thứ**: `experiment.make_corpus(n, H, seed)` dùng **một** `rng`
chung cho cả corpus và rút $H$ topic mỗi workflow, nên đổi $H$ là đổi dòng số
ngẫu nhiên ⇒ hai lưới chạy trên **hai tập workflow khác nhau**. Không tách được
chân trời với corpus.

## 2. Việc sẽ làm

Thêm `make_corpus(..., H_gen=...)` và cờ `--corpus-horizon`: sinh corpus ở
$H_{\text{gen}} = 12$ rồi **cắt** mỗi workflow xuống $H = 8$ task đầu. Hai lưới
khi đó dùng **chung workflow** (phần đầu của cùng một chuỗi task). Mặc định
`H_gen = None` giữ nguyên từng chữ số của mọi bảng cũ.

Lượt chạy: `--H 8 --corpus-horizon 12 --n 40 --seeds 3 --deltas 0 1 2 4`, thang
USD, cùng ba detector. So ô (mid, $\Delta = 4$) với hai số đã có.

## 3. Dự đoán — khai trước khi chạy

Gọi $g$ là độ lợi của `SSG-full receding` so với B1 ở ô (mid, $\Delta = 4$) trên
corpus $H = 12$ đã cắt xuống $H = 8$.

| # | Nếu | Thì đọc là |
|---|---|---|
| H1 | $g \ge 12\%$ (gần +17,8%) | Chênh lệch là **hiệu ứng chân trời thật**: cùng workflow, thêm 4 task thì lợi thế mất. Luận điểm phải phát biểu **theo $H$** |
| H2 | $g \le 8\%$ (gần +4,0%) | Chênh lệch là **hiệu ứng corpus**: +17,8% là may mắn của một tập workflow. Số $H = 8$ đã công bố **không bền theo mẫu** |
| H3 | $8\% < g < 12\%$ | **Không phân xử được** ở $N = 40$; báo cả hai nguồn và không quy cho bên nào |

Ngưỡng 8% / 12% chọn ở khoảng một phần ba và hai phần ba đoạn giữa hai số
4,0 và 17,8, **trước** khi thấy kết quả. Không sửa ngưỡng sau khi chạy.

Kiểm tra tính đúng (không phải dự đoán): với `--corpus-horizon` bỏ trống, bảng
$H = 8$ phải khớp **từng chữ số** với bảng đã công bố.
