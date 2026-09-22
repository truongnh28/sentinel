# SPEC — R: truy xuất có độ phân giải

**Vấn đề một câu:** truy xuất khớp-chuỗi-chính-xác làm attacker **không có mặt phẳng nào để tối ưu**, nên AgentPoison không port được và $\varepsilon$ là tham số trang trí.

**Giải pháp một câu:** thay khớp chính xác bằng **độ tương tự Jaccard trên tập token module** — tất định, không mô hình, stdlib thuần, và khớp chính xác là **ca riêng** $\theta = 1$.

Nền: `SPEC-Phan-ra-Pipeline.md` Phần 0.

---

# 1. Đánh đổi thật, sau khi tách hai thứ bị trộn

`../eval/SPEC-AuditGame-SE.md` §4 bảo vệ khớp chính xác bằng: *"không cần mô hình ngữ nghĩa — đó là điều kiện để oracle tất định."*

Câu đó trộn hai thứ:

| | Phụ thuộc truy xuất? |
|---|---|
| **Oracle tất định** — `public ✓ ∧ hidden ✗`, hai lệnh `pytest` + so AST | ❌ **không**. Oracle chấm patch, không chấm truy xuất |
| **Replay khớp bit** — `../eval/Thiet-ke-AuditGame-SE.md` §3, đòn bẩy giảm chi phí hai bậc | ✅ **có** |

Nên thứ khớp chính xác thật sự mua là **replay**, không phải oracle. Và đánh đổi đúng là:

$$\text{truy xuất TẤT ĐỊNH} \quad\text{vs.}\quad \text{attacker có mặt phẳng TỐI ƯU}$$

**Cả hai lấy được**, vì tất định không đòi hỏi rời rạc. Một hàm liên tục vẫn tất định miễn nó không học và không bốc thăm.

---

# 2. Đặc tả

## 2.1 `topic` đổi kiểu: chuỗi → tập token

```
hiện tại:  topic: str              "orm"
sau:       topic: frozenset[str]   {"django", "db", "models", "query"}
```

Với dữ liệu thật: lấy từ **danh sách file mà gold patch của instance sửa**, tách theo `/` và bỏ đuôi. `django/db/models/query.py` → `{django, db, models, query}`. Không mô hình, không nhúng — chỉ tách chuỗi.

## 2.2 Độ tương tự

$$\operatorname{sim}(A, B) \;=\; \frac{|A \cap B|}{|A \cup B|} \qquad (\text{Jaccard})$$

$$\operatorname{retrieve}(\text{task}) \;=\; \{\, it \in \text{live} \;:\; \operatorname{sim}(it.\text{topic},\ \text{task.topic}) \ge \theta \,\}$$

$\theta$ là tham số **đóng băng**, nằm **cùng ô hash** với $\pi_0$ / phép gộp / $\tau_{\text{sel}}$ của `../eval/SPEC-Tang-Do-va-Test.md` §2.6.

## 2.3 Tương thích ngược — điều kiện bắt buộc

$\theta = 1$ và hai tập bằng nhau $\iff$ khớp chính xác. Nghĩa là **hành vi hiện tại là một điểm trong không gian mới**, không phải bị thay thế. Mọi kết quả đã đo lại được bằng $\theta = 1$.

Đây là ràng buộc thiết kế, không phải tiện ích: nếu R không tái lập được bảng cũ thì không phân biệt được "R đổi kết luận" với "R có bug".

## 2.4 $\varepsilon$ lần đầu có cơ chế

Đặt $B$ = tập token của task $\sigma$. Attacker chọn tập token cho payload:

$$A(\varepsilon) \subseteq B, \qquad |A(\varepsilon)| = \lceil \varepsilon \cdot |B| \rceil$$

Vì $A \subseteq B$ nên $\operatorname{sim}(A,B) = |A|/|B| = \varepsilon$ (làm tròn). Hai chiều đối nghịch:

| | $\varepsilon$ nhỏ | $\varepsilon$ lớn |
|---|---|---|
| payload nhắc tới | ít module | nhiều module |
| $\operatorname{sim}$ với task $\sigma$ | thấp — **có thể không vượt $\theta$** ⇒ tấn công hỏng | cao — chắc chắn được truy xuất |
| đặc trưng `size` của $F_\text{match}$ | nhỏ, lẫn vào note thường | **lớn** — note tự nhận liên quan tới nhiều module là bất thường |

$$\boxed{\;\varepsilon \;\text{đánh đổi}\; \underbrace{\text{khả năng được truy xuất}}_{\ge\,\theta} \;\;\text{lấy}\;\; \underbrace{\text{độ khó phát hiện}}_{\text{AUC trên } F_\text{match}}\;}$$

Đó **đúng nghĩa** "distinguishability budget" mà `../eval/SPEC-AuditGame-SE.md` §5.3 mô tả bằng lời nhưng chưa có mặt phẳng nào để hiện thực hoá.

## 2.5 Ràng buộc $\Delta$ tổng quát hoá, không bị thay thế

Ràng buộc cũ — *"không task nào trong $[\iota,\sigma)$ mang topic của payload"* — thành:

$$\forall j \in [0, \sigma): \quad \operatorname{sim}\big(A,\ \text{topic}(\text{task}_j)\big) < \theta$$

Hai thay đổi, cả hai đều là sửa lỗi đã biết:
- `<` thay cho `≠` — phiên bản có độ phân giải
- $[0,\sigma)$ thay cho $[\iota,\sigma)$ — vá lỗi §1.3 của `../eval/SPEC-Tang-Do-va-Test.md` (23–44% case nổ trước $\iota$)

---

# 3. Vì sao Jaccard, không phải cosine/embedding

| | tất định | không cần train | stdlib | attacker tối ưu được |
|---|---|---|---|---|
| khớp chính xác *(hiện tại)* | ✅ | ✅ | ✅ | ❌ |
| **Jaccard trên token** | ✅ | ✅ | ✅ | ✅ |
| cosine trên embedding | ⚠ phụ thuộc model+version | ❌ | ❌ | ✅ |

Embedding thêm một phụ thuộc mà **replay phải đóng băng luôn** (model + version + tokenizer), và nó phá ràng buộc *"người khác `git clone` rồi chạy được ngay bằng `python3 -m unittest`"* của `../eval/Thiet-ke-Framework-Test.md` §4. Jaccard mua được toàn bộ lợi ích tối ưu mà không trả giá nào trong số đó.

**AgentPoison port được ở mức THUẬT TOÁN, không phải mức code.** Bài toán của họ — cực đại xác suất được truy xuất với ràng buộc tàng hình — giữ nguyên hình dạng; chỉ đổi hàm tương tự. Luận văn phải khai rõ đây là **port có kiểm soát**, không phải chạy lại artifact của họ.

---

# 4. Rủi ro

| Rủi ro | Mức | Xử lý |
|---|---|---|
| $\theta$ thành tham số tự do mới | **Cao** | freeze cùng ô hash; quét độ nhạy $\theta \in \{0{,}3;\ 0{,}5;\ 0{,}7\}$, kiểm kết luận RQ không đổi dấu |
| Jaccard không phải mô hình "liên quan" đúng của SE | Trung bình | nêu là **giới hạn**; nó xấp xỉ "hai task đụng chung module", đủ cho oracle nhưng không phải ngữ nghĩa thật |
| Tập token quá nhỏ ⇒ $\operatorname{sim}$ thô | Trung bình | instance SWE-bench sửa 1–3 file ⇒ 3–10 token; đo phân bố ở P1a trước khi chốt $\theta$ |
| Đổi kiểu `topic` chạm mọi module | Thấp | `str` → `frozenset` là đổi cơ học; test cổng 1 bắt hồi quy |

---

# 5. Trạng thái

Đây là **phương án**, không phải quyết định. Câu hỏi 3 cho thầy (`SPEC-Phan-ra-Pipeline.md` Phần 3) phải được trả lời trước khi R vào nhánh chính:

> *manuscript khai attacker chọn $(k,\iota,\sigma,\varepsilon)$, nhưng với truy xuất khớp chính xác thì $\varepsilon$ không tác động được vào đâu. Vậy $\varepsilon$ trong smoke test gốc tác động lên cái gì?*

Prototype ở `code/Sentinel/auditgame/retrieval.py` chứng minh thiết kế chạy được và tương thích ngược; nó **chưa** được nối vào `core.CarrierStore`.
