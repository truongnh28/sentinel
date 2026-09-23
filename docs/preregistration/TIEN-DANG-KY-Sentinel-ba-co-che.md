# Tiền đăng ký — Sentinel lấy lại đủ ba cơ chế

**Ngày:** 23/09/2026 · **Khai trước khi sửa mã, trong một commit riêng** (quy tắc R1)
**Nối tiếp:** [TIEN-DANG-KY-Sentinel-SSG.md](TIEN-DANG-KY-Sentinel-SSG.md)

---

## 1. Hai lỗ hổng đã xác nhận

`policies.Sentinel` khai trong docstring của chính nó **ba cơ chế**:

> 1. RANDOMISATION — cam kết một phân phối, chỉ lộ phân phối
> 2. BELIEF STATE — báo động nâng posterior của carrier vừa kêu
> 3. ROTATION — bảo đảm không carrier nào bị bỏ quên lâu

Mã chỉ có **cơ chế 1 và 2**:

| Lỗ hổng | Bằng chứng |
|---|---|
| Không có kênh commit | `ACTIONS = frozenset(CARRIERS)`. Hạ $\kappa_{\text{commit}}$ xuống **rẻ hơn carrier rẻ nhất** vẫn **0/80** lần chọn commit |
| Không có rotation | `Policy._rot` khai ở `policies.py:112`, **không nơi nào trong cây mã đọc hay ghi nó** |

## 2. Vì sao điều này không phải chuyện nhỏ

Ba con số đã công bố đo trên đối tượng thiếu hai cơ chế:

- **Exploitability** regret Sentinel 0,240 so với B1 0,089 — đọc thành *"phân bổ thích nghi dễ bị khai thác hơn một chốt cố định"*. Nhưng phép so đang so một chốt cố định với **một bộ lấy mẫu chỉ biết carrier**.
- **Held-out** độ lợi đảo dấu +2,7% → −2,7%.
- **RQ4** độ lợi không lớn nhất ở detector yếu — mà rotation chính là cơ chế lẽ ra đỡ cho trường hợp đó.

## 3. Thay đổi sẽ làm

1. Thêm `"commit"` vào không gian hành động của `Sentinel`, trọng số bằng **tổng khối lượng tin tưởng** chia $\kappa_{\text{commit}}$ — đúng như `SentinelW` đã làm, để hai biến thể chỉ khác nhau ở dạng belief chứ không khác ở kênh.
2. Hiện thực rotation bằng `_rot`: một carrier không được audit trong $R$ task thì trọng số của nó được nhân lên, để không carrier nào bị bỏ quên quá lâu. $R$ **quét**, không gán.

## 4. Dự đoán — khai trước, và có thể sai

| Chỉ số | Dự đoán | Điều gì bác bỏ |
|---|---|---|
| Exploitability | regret Sentinel **giảm**, về gần SSG-G (0,012) hơn là giữ 0,231 | Giữ nguyên hoặc tăng ⇒ vấn đề nằm ở **belief heuristic**, không ở kênh thiếu |
| Held-out | khoảng cách chuyển giao **thu hẹp** từ +0,05 | Không đổi ⇒ belief vẫn khớp quá mức, rotation không cứu |
| RQ4 | độ lợi ở **detector yếu tăng** — đây là việc rotation sinh ra để làm | Vẫn tăng dần theo detector mạnh ⇒ **RQ4 ngược dấu là kết quả thật**, không phải hiện vật |
| harm tổng | có thể **xấu đi** ở detector mạnh: ngân sách chia cho commit và rotation là ngân sách lấy khỏi chỗ belief đang chỉ đúng | — |

**Cam kết:** báo cả bảng trước và sau, kể cả khi sau xấu hơn. Không chọn $R$ theo kết quả: quét và báo cả dải.

## 5. Điều này **không** rửa được

Lần chạy lại diễn ra **sau khi đã thấy dấu ngược**, nên nó là **chẩn đoán**. Tuyên bố sạch đòi tập chính sách và $R$ được khai trước rồi chạy một lần — tài liệu này là bước khai đó, nhưng nó không lùi ngược được thời điểm phát hiện. Bài phải nói câu này.
