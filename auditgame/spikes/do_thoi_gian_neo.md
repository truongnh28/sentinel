# Tỉ lệ neo H1 trên dữ liệu thật (t3, Bước 10.2) — **CỔNG ĐỎ**

Ngày đo: 2026-09-16.

## Số đo được

```
mẫu 20 instance (seed_of("spike-t1")):   0/20  =  0%
toàn bộ pool Verified:                   5/500 =  1,0%
```

Cổng quyết định của Bước 10.1 là **≥ 10/20**. Kết quả: **đỏ**. Theo đúng plan,
nhóm D dừng ở đây và báo cáo — **không** viết H2–H5 (Task 11).

## Không phải do bản vá `anchor_for`

`anchor_for` vừa được sửa ở `3410cc8` (điều kiện bất biến trong vòng lặp). Phải
loại trừ khả năng chính bản vá tạo ra con số thấp:

| | instance neo được |
|---|---|
| hành vi **trước** vá | 5/500 |
| hành vi **sau** vá | 5/500 |

Bản vá đổi **file nào được neo**, không đổi **bao nhiêu instance neo được**. Con
số 1,0% là thuộc tính của corpus, không phải của bản vá.

## Vì sao 1%

`_WRITE` đòi một dòng **thêm vào** có gọi `write` / `send` / `render` / `emit`.
Trên cả 500 gold patch, tổng số dòng khớp là **sáu**: `write`×4, `render`×1,
`emit`×1.

H1 neo vào một thuộc tính **I/O** (dữ liệu ghi ra ngoài phải đi qua hàm làm sạch).
Còn pool là nội bộ thư viện:

```
django 231 · sympy 75 · sphinx 44 · matplotlib 34 · scikit-learn 32
astropy 22 · xarray 22 · pytest 19 · pylint 10 · requests 8 · seaborn 2 · flask 1
```

Thuộc tính H1 chọn gần như không xuất hiện trong loại patch này.

## Đổi thuộc tính khác có cứu được không? — ĐO, không đoán

Đếm số patch **thêm** một lời gọi tới từng tên hàm (500 patch):

| tên | số patch | % |
|---|---|---|
| `isinstance` | 54 | 11% |
| `append` | 29 | 6% |
| `len` · `get` · `getattr` | 25 | 5% |
| `hasattr` | 22 | 4% |
| `join` · `super` | 19–20 | 4% |
| `str` | 13 | 3% |

**Trần của một template đơn lẻ là ~11%.** Cổng 50% không với tới được dù đổi
thuộc tính, và cũng không với tới bằng năm template H1–H5 kể cả nếu chúng rời
nhau hoàn toàn. Đây là kết luận về **corpus**, không phải về H1.

## Trạng thái

V1, V2, V3 của H1 **đều xanh** (`1a1f01c`, `3410cc8`) — tức oracle tách được hệ quả
khỏi marker. Cái hỏng không phải V3; cái hỏng là **độ phủ**. Nên hai lối lui ở
`eval/PLAN.md` III.6 (vốn viết cho tình huống "V3 đỏ trên nhiều họ") áp vào đây
với chẩn đoán khác: không phải *"không tách được hệ quả khỏi marker"* mà là
*"hệ quả ta chọn để kiểm hầu như không xuất hiện trong corpus"*.

Chờ quyết định trước khi đi tiếp nhóm D.
