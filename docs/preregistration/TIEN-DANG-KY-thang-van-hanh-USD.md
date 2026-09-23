# Tiền đăng ký — đưa đường chạy chính sang thang vận hành USD

**Ngày:** 23/09/2026 · **Khai trước khi chạy lại lưới, trước mốc đóng băng 29/09**

---

## 1. Sự việc phải ghi nhận trước

README §3.2 đã chốt **USD là thang vận hành**, và ghi bảng draft
(0,4 / 0,9 / 1,6 / 4,1) là **đã rút khỏi đường chính**. Kiểm lại mã ngày 23/09:
điều đó **chưa đúng với mã**. `experiment.py` — đường sinh ra mọi bảng kết quả —
không gọi `costs.install()` ở bất kỳ đâu; nó chạy thẳng trên `policies.KAPPA`,
`policies.KAPPA_COMMIT`, `policies.ETA_Q_COST`, tức **đúng bảng placeholder đã
tuyên bố là rút**. Chỉ `spikes/ssg_sweep.py` gọi `install()`.

Đây không phải lỗi làm tròn. Trò chơi bất biến theo hệ số chung, nên chỉ bốn tỉ
số không thứ nguyên sống sót — và **ba trong bốn tỉ số đó đang sai**:

| Tỉ số | Placeholder (đang chạy) | USD (đo được) | Lệch |
|---|---:|---:|---:|
| $\chi$ | 2,114 | 1,349 | 1,57× |
| $\kappa_{\text{commit}}/\bar\kappa$ | 2,343 | 4,000 | 1,71× |
| $\eta_Q/\bar\kappa$ | 1,143 | 61,519 | **53,8×** |
| $B/(H\sum\kappa)$ | 0,3205 | 0,3205 | giữ nguyên |

Và **thứ tự carrier đảo ngược**, thứ mà $\chi$ không hề ràng buộc:

```
placeholder   memory 0,229 < skill 0,514 < queue 0,914 < branch 2,343
USD           skill  0,358 < queue 0,496 < branch 1,439 < memory 1,707
```

Trục $\chi$ hiện lấy `base = dict(P.KAPPA)` (experiment.py:329), nên `--chi 1.349`
chỉ kéo *hình dạng placeholder* về đúng độ rộng đo được mà **giữ nguyên thứ tự
sai**. Mọi chính sách biết giá đều duyệt carrier theo giá, nên đây là confound đi
thẳng vào RQ1 và RQ2.

## 2. Việc sẽ làm

1. `costs.install()` chuyển $\eta_Q$ từ tỉ số placeholder sang **giá trị đo
   được**, khai rõ phép gộp bốn carrier thành một vô hướng là **làm tròn**.
2. `experiment.py` nhận `--scale {legacy,usd}`, **mặc định `usd`**; ngân sách đi
   theo bảng bằng `costs.budget_for_table` để $B/(H\sum\kappa)$ đứng yên.
3. $\eta_Q/\bar\kappa$ vào bài bằng **M2 (quét)**, không chốt một số — vì lý do ở §3.
4. Chạy lại lưới chính trên thang đúng, với $\lambda_Q = 0{,}5486$ đã suy ra.

## 3. Vì sao $\eta_Q$ phải quét chứ không được chốt

Ở giá đo được, một lượt quarantine tốn **5,998 lần toàn bộ ngân sách episode**.
Không chính sách nào mua nổi. Chính `costs.py:229` đã cảnh báo đúng tình huống
này: *"a policy that cannot afford an action is not being compared, it is being
disabled."*

Tỉ số $\eta_Q/\bar\kappa$ có hai mốc **suy ra được, không phụ thuộc thang**, vì
$B = 0{,}3205 \cdot H \cdot 4\bar\kappa = 10{,}257\,\bar\kappa$ ở $H = 8$:

- $r = 1{,}282$ — một lượt quarantine bằng **suất ngân sách một task** $B/H$;
- $r = 10{,}257$ — một lượt quarantine bằng **cả ngân sách episode**.

Trên $r = 10{,}257$ thì quarantine chết hẳn. Giá đo được (61,5) nằm **sâu** bên
trên. Nên câu hỏi khoa học không phải "quarantine đáng giá bao nhiêu" mà **"từ
giá nào trở đi quarantine thôi là một hành động"** — và đó là câu quét trả lời
được, chốt một số thì không.

## 4. Dự đoán — khai trước khi chạy

| # | Dự đoán | Sai khi nào |
|---|---|---|
| P1 | **B1 harm tăng** trên thang USD so với placeholder | B1 mua được 4,38 → 2,56 lượt commit-audit (−41%); nếu harm không tăng thì commit-audit không phải thứ giữ B1 đứng vững |
| P2 | **Số lượt quarantine trên toàn lưới = 0** ở $\eta_Q$ đo được; NC1 thành no-op và harm của nó bằng trần không-audit | bất kỳ lượt quarantine nào được thực hiện |
| P3 | **$L$ của `Sentinel` giảm** so với lượt placeholder | lặp lại điều đã thấy ở SentinelW (1,095 → 0,855) khi quarantine được định giá đúng; sai nếu $L$ tăng |
| P4 | **Điểm lật của $\eta_Q/\bar\kappa$ nằm trong [1,3; 10,3]** | hai mốc suy ra ở §3; sai nếu thứ hạng lật ngoài dải đó, hoặc không lật ở đâu cả |
| P5 | Đảo thứ tự carrier **đổi danh tính người thắng** ở ít nhất một ô lưới | sai nếu người thắng y nguyên ở cả 12 ô |
| P6 | Trục $\chi$ trên nền USD **vẫn trơ** dưới neo `mean` | ghi chú `CHI_ANCHORS` nói winners thắng nhờ trung bình chứ không nhờ độ rộng — lập luận này độc lập hình dạng; sai nếu gain đổi quá 0,05 theo $\chi$ |

**Không sửa dự đoán sau khi thấy số.** Cái nào bị bác thì ghi là bị bác.

## 5. Điều này *không* đe doạ kết luận nào

Vùng lật của $\kappa_{\text{commit}}/\bar\kappa$ đo được là **1,43–2,0**. Cả
placeholder (2,343) lẫn USD (4,000) đều **đã nằm trên** vùng đó. Nên dấu của RQ1
được dự đoán là **không đổi** — chỉ độ lớn đổi. Nếu dấu *có* đổi, đó là kết quả
lớn hơn mọi thứ trong tài liệu này và phải được báo như vậy.
