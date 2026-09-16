# Chốt θ cho truy xuất graded (Task 5c, Phần A)

Ngày: 2026-09-16. Nối tiếp `phan_bo_topic.md`.

> **Ghi trước khi chạy bộ lọc.** Số workflow sống sót bước 4 ở bốn giá trị θ ứng
> viên đã được đo sẵn ở task trước và **đã biết**. Chúng không xuất hiện ở bất kỳ
> đâu trong lập luận dưới đây. Tài liệu này được commit TRƯỚC khi chạy lại bộ lọc,
> để thứ tự nhân quả kiểm chứng được: θ ⇒ số sống sót, không phải ngược lại.

## Dữ liệu vào — và CHỈ dữ liệu này

`topics.distribution` trên cả hai pool, đo lại tại chỗ:

| pool | n | trung vị \|topic\| | histogram |
|---|---|---|---|
| verified | 500 | **4.0** | `{2:17, 3:217, 4:148, 5:83, 6:12, 7:8, 8:8, 9:4, 10:1, 11:1, 32:1}` |
| full | 2294 | **4.0** | `{2:88, 3:956, 4:582, 5:340, 6:108, 7:59, 8:37, 9:35, 10:20, 11:10, 12:15, 13:11, 14:5, 15:4, 17:1, 18:4, 21:3, 22:2, 23:1, 24:3, 26:1, 27:1, 28:1, 29:3, 32:2, 37:1, 46:1}` |

Hai sự kiện rút ra, và chỉ hai:

- **m ≡ trung vị |topic| = 4**, giống nhau ở cả hai pool.
- Khối lượng dồn về đuôi nhỏ: `|topic| ≤ 6` chiếm **477/500 = 95,4%** (verified) và
  **2074/2294 = 90,4%** (full); `|topic| ∈ {3,4}` chiếm 73% / 67%.

## D1 — θ chỉ phân biệt được trên LƯỚI sim đạt được

`retrieved(A,B,θ) ⇔ sim(A,B) ≥ θ`. Nếu a < b là hai giá trị sim kề nhau mà corpus
đạt được thì **mọi** θ ∈ (a, b] cho đúng một hành vi. Vậy tập θ có ý nghĩa đúng
bằng lưới sim đạt được ở kích thước topic điển hình; một θ ngoài lưới (ví dụ 0,34)
không phải lựa chọn riêng — nó là điểm lưới ngay trên nó, đội lốt.

Ở m = 4 có **hai** lưới, vì θ phục vụ hai phép so khác nhau:

| lưới | dùng ở đâu | công thức | giá trị tại m = 4 |
|---|---|---|---|
| **payload ⊆ topic của σ** | `payload_topic(σ, ε)` — mặt phẳng của ε | `sim = k/m` | 0,25 · 0,50 · 0,75 · 1,00 |
| **hai topic task đầy đủ** | `hosts_delta`, và truy xuất memory task→task | `sim = j/(2m−j)` | 0,143 · 0,333 · 0,600 · 1,00 |

## D2 — Chặn trên: loại θ = 1,0 theo định nghĩa

θ = 1,0 **chính là** `==` hiện tại. Nó là thứ task này tồn tại để tổng quát hoá, và
nó ép mọi ε < 1 thành no-op lần nữa: payload là tập con thực sự ⇒ sim < 1 ⇒ không
bao giờ được truy xuất ⇒ harm = 0 **giả**. Loại.

## D3 — Chặn dưới: loại θ = 0,25, nó giết ε với tư cách NGÂN SÁCH

`payload_topic` dùng `k = max(1, ceil(ε·m))` nên k ≥ 1 luôn, nên ở m = 4 thì
`sim ≥ 0,25` với **mọi** ε > 0. Đặt θ = 0,25 ⇒ mọi ε đều được truy xuất ⇒ ε mất
hẳn **đầu hỏng**. Một ngân sách chỉ biết tiêu thì không phải ngân sách — đúng câu
đã dùng để loại `VerbosityAttack`. Loại.

⇒ Chỉ từ yêu cầu "ε phải có cả hai đầu", θ ∈ **{0,50 · 0,75}**. Chưa nhìn số sống
sót nào.

## D4 — Giữa 0,50 và 0,75: 0,75 SỤP VỀ ĐÚNG KHỚP CHÍNH XÁC

Xét lưới thứ hai (hai topic task đầy đủ cùng cỡ m — trường hợp thống trị corpus).
`sim ≥ 0,75 ⇔ j/(2m−j) ≥ 3/4 ⇔ j ≥ 6m/7`:

| m | j tối thiểu để vượt 0,75 | nghĩa |
|---|---|---|
| 3 | ⌈18/7⌉ = 3 | **j = m ⇒ hai tập BẰNG NHAU** |
| 4 | ⌈24/7⌉ = 4 | **j = m ⇒ bằng nhau** |
| 5 | ⌈30/7⌉ = 5 | **j = m ⇒ bằng nhau** |
| 6 | ⌈36/7⌉ = 6 | **j = m ⇒ bằng nhau** |
| 7 | 6 | j < m — lần đầu có băng graded thật |

Với `|topic| ≤ 6` — **95,4%** instance Verified, 90,4% pool full — θ = 0,75 chỉ
chấp nhận hai topic **hệt nhau**. Tức trên corpus này θ = 0,75 **là** θ = 1,0 cho
phép so task↔task: nó không tổng quát hoá gì cho truy xuất memory task→task. Đúng
lý lẽ D1, áp vào lưới cặp. Loại.

θ = 0,50 trên lưới cặp: `j/(2m−j) ≥ 1/2 ⇔ j ≥ 2m/3` — m=3 ⇒ j≥2, m=4 ⇒ j≥3,
m=5 ⇒ j≥4, m=6 ⇒ j≥4. Tức **chia sẻ hai phần ba số token**: chặt hơn hẳn "đa số",
lỏng hơn hẳn "trùng khít". Là điểm lưới duy nhất còn lại có băng graded thật ở
kích thước topic điển hình của corpus.

## Chốt

$$\theta = 0{,}50$$

**Một câu:** ở trung vị |topic| = 4 đo được trên cả hai pool, 0,50 là điểm lưới
DUY NHẤT vừa cho ε có cả đầu hỏng lẫn đầu chạy (0,25 bỏ đầu hỏng, 1,0 bỏ đầu chạy),
vừa không sụp về khớp chính xác trên 95,4% instance (0,75 thì có).

## Ghi chú về mock

Topic của mock là chuỗi một token (`'orm'`), chuẩn hoá thành tập một phần tử. Với
tập một phần tử, Jaccard chỉ nhận {0, 1}, nên **mọi θ ∈ (0, 1]** tái lập đúng phép
so bằng — θ = 0,50 trên mock **là** `==`. Đây là lý do `experiment.py --n 20` phải
giống từng byte, và là phép kiểm tra chéo cho D1: mock nằm ở chỗ lưới chỉ có hai
điểm, nên không θ nào phân biệt được gì ở đó.

## Cam kết trước khi đo

Số workflow sống sót bước 4 là **hệ quả** của θ này. Dù nó là 0, 6 hay 21, nó được
báo nguyên trạng; θ không sửa sau khi thấy nó. Nếu corpus vẫn rỗng thì đó là một
**kết quả**: lời từ chối của `datasets.PENDING` được giữ, kèm lý do đo được mới.
