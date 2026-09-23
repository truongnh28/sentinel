# Tiền đăng ký — khai giá trị $\lambda_T$

**Ngày:** 23/09/2026 · **Khai trước khi chạy lưới cuối, trước mốc đóng băng 29/09**

---

## 1. Vì sao đây là khai báo chứ không phải phép đo

$L = E[\text{harm}] + \lambda_Q E[Q_{\text{false}}] + \lambda_T E[T_{\text{lost}}]$.

**$\lambda_Q$ đã thôi là tham số tự do.** Một lần cách ly nhầm và một task sạch bị
mất **đều định giá được** bằng thang USD của chính dự án, nên **tỉ số** của chúng
là phép đo: $\eta_Q(k)$ chia chi phí chạy lại một task = **1,0973** (dải
0,393–1,874 theo carrier). `metrics.py` nay suy $\lambda_Q$ từ $\lambda_T$ bằng
tỉ số đó.

**$\lambda_T$ thì không đo được ở đây.** Nó là "một task sạch bị mất đáng giá mấy
lần một payload lọt lưới", và vế sau là chi phí một bản vá độc lọt vào repository
— thứ khác nhau vài bậc độ lớn giữa các dự án và benchmark này không có cách nào
định giá.

## 2. Giá trị khai: $\lambda_T = 0{,}5$

**Phát biểu tương đương, để phản biện được:** *một task sạch bị mất gây thiệt hại
bằng một nửa một payload lọt lưới.*

Đây là con số đã nằm sẵn trong `metrics.py` từ trước, và nó được **giữ**, không
phải được chọn lại sau khi nhìn bảng. Giữ nó là lựa chọn chặt hơn: nếu chọn lại
bây giờ thì mọi số trước đó phải chạy lại dưới một trọng số được chọn *sau* khi
thấy kết quả.

## 3. Điều phải nói ra: vùng thắng và vị trí của 0,5 trong đó

Quét toàn dải (`tools/anchor_lambdas.py`, thang USD, $\eta_Q$ đo được):

| $\lambda_T$ | Thắng cuộc |
|---|---|
| 0,00 – 0,25 | SentinelW window-belief |
| **0,26 – 0,57** | **SSG-G guarded** |
| 0,58 – 1,20 | B1 audit-at-commit |

SSG-G thắng trên một dải rộng **0,31**, không phải một điểm — nhưng **0,5 nằm gần
mép trên**. Khai 0,6 là B1 thắng. Bài **phải in cả bảng này**, không được chỉ in
cột tại 0,5.

## 4. Hai lập luận cho 0,5, và phản biện của từng cái

**Thuận.** Một task mất đi thì chạy lại được — đo được là 0,0868 USD. Một payload
lọt lưới thì không rút lại được: nó nằm trong lịch sử repository cho tới khi có ai
phát hiện. Một sự kiện hồi phục được đáng giá **dưới** một sự kiện không hồi phục
được, nên $\lambda_T < 1$.

**Phản.** Nó **không** nói vì sao là 0,5 chứ không phải 0,2 hay 0,8. Đúng vậy —
và đó là lý do mục 3 tồn tại: con số không được biện hộ đến mức đó, nên kết luận
phải được phát biểu **kèm điều kiện**, dạng *"khi một task mất đi đáng giá từ
0,26 đến 0,57 một payload lọt lưới, SSG-G là chính sách tốt nhất"*.

## 5. Cam kết

- Lưới cuối chạy ở $\lambda_T = 0{,}5$, và **in kèm bảng mục 3**.
- Không đổi $\lambda_T$ sau khi thấy lưới cuối. Nếu có lý do phải đổi thì ghi lý
  do vào một commit riêng **trước** khi chạy lại, và báo cả hai.
- Mọi bảng công bố trước 23/09 chạy ở $\lambda_Q = 0{,}10$ — **rẻ hơn giá đo được
  5,5 lần** — nên chúng phải được chạy lại hoặc gỡ, không được đặt cạnh bảng mới.
