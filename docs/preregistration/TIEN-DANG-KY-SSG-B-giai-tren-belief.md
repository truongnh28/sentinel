# Tiền đăng ký — SSG-B: giải LP trên window belief

**Ngày:** 23/09/2026 · **Khai trước khi viết chính sách, commit riêng** (quy tắc R1)

---

## 1. Ô trống, và vì sao nó là ô trống

Đo trên thang USD, $\Delta = 2$, detector mid, với $\eta_Q$ **đo được**:

| Chính sách | $L$ | regret | held-out gap |
|---|---|---|---|
| SentinelW | **0,787** | 0,3219 | +0,10 |
| Sentinel | 0,865 | 0,2076 | +0,025 |
| B5 | 0,907 | 0,1433 | −0,025 |
| SSG-G | 0,988 | **0,0119** | −0,025 |
| B7 | 1,038 | 0,0254 | −0,025 |
| B1 | 1,000 | 0,0179 | 0,000 |

Xếp theo $L$ **đúng ngược** xếp theo regret, không sai bậc nào. Nguyên nhân chỉ được tên:

- `SSGRecedingGuarded` kế thừa `MinimaxLP` và **không đọc belief nào** — nó *giải*, nên vững, nhưng mù.
- `SentinelWindow` có `WindowBelief` nhưng **gán trọng số bằng tay**: `mass(c)/κ(c)` — nhạy, nhưng bị định tuyến vòng.

Không ai có cả hai.

## 2. Chính sách sẽ dựng

**SSG-B** = giải LP của SSG-G, nhưng **tiên nghiệm của attacker lấy từ posterior của `WindowBelief`** thay vì phân phối đều trên lớp tấn công đã khai. Defender vẫn cam kết một **phân phối được tính ra**, chỉ khác là tính dựa trên niềm tin hiện tại về cửa sổ tấn công — đúng khung Bayes–Stackelberg mà draft mô tả bằng lời.

Không thêm cơ chế nào khác. Không chỉnh tham số của SSG-G.

## 3. Dự đoán — khai trước, và có thể sai

| Chỉ số | Dự đoán | Điều gì bác bỏ |
|---|---|---|
| $L$ | nằm **giữa** SSG-G (0,988) và SentinelW (0,787), gần SentinelW hơn | Tệ hơn 0,988 ⇒ belief làm hỏng phép giải chứ không giúp |
| regret | ở lại **dưới 0,05**, tức cùng hạng với SSG-G/B1/B7 | Vượt 0,14 (mức B5) ⇒ dùng belief làm tiên nghiệm **tự nó** đủ để bị khai thác, và biên đánh đổi là **thật, không phá được** |
| held-out gap | không dương quá +0,025 | Vượt +0,05 ⇒ belief khớp quá mức bất kể được dùng thế nào |

**Kết quả quan trọng nhất là trường hợp bác bỏ.** Nếu SSG-B không thể vừa có $L$ thấp vừa có regret thấp, thì biên đánh đổi giữa trung bình và xấu nhất là một **tính chất của bài toán**, không phải thiếu sót của các chính sách — và đó là phát biểu mạnh hơn bất kỳ chính sách thắng cuộc nào.

## 4. Điều kiện nghiệm thu, khai trước

SSG-B chỉ được đưa vào bài như một **đóng góp** nếu đạt **cả hai** trên **held-out**, không phải trên tập phát triển. Không đạt thì nó vào phần "cái chúng tôi đã thử và không được", và biên đánh đổi là kết quả chính.

## 5. Điều này không rửa được

SSG-B được nghĩ ra **sau khi** nhìn bảng ở mục 1. Tài liệu này khai trước khi viết mã và trước khi đo, nhưng không lùi ngược được thời điểm nảy ra ý tưởng. Bài phải nói câu này.
