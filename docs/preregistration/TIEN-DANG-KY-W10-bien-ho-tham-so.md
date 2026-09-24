# Tiền đăng ký — W10: biện hộ $K$, $H$, $N$ và số seed

**Ngày:** 24/09/2026 · **Khai trước khi viết công cụ và trước khi chạy. Cấu hình đóng băng `sha256:ab6179a2ed4a` không đổi.**

---

## 1. Sự việc

Bản thảo nêu $K = 4$, $H = 8$, $N$ và 3 seed nhưng không có nguồn cho các số này. W10 yêu cầu
sinh bằng chứng. Vế "$\rho$ bão hoà biện hộ 28 policy" đã khép (W7). Tài liệu này khai
ba vế còn lại. Vế ngưỡng AUC 0,56 **không** làm ở đây: cổng v2 đã đóng băng theo tiêu
chí cận trên CI, và `analysis/band_vs_n.py` đã đo dải nhiễu (0,56 nằm trong dải ở mọi
$n \le 1800$). Đổi ngưỡng sau khi đóng băng là chỉnh cổng theo kết quả.

## 2. Ablation $K = 2, 3$

**Định nghĩa.** Bỏ một carrier nghĩa là carrier đó **ra khỏi trò chơi**. Attacker không cài
vào đó được, còn defender không thấy và không audit được nó. Item lành tính vẫn nằm
trong kho vì workflow sinh chúng, nhưng không ai đọc tới. Commit-audit chấm **mọi carrier
còn lại**, nên $\kappa_{\text{commit}} = \sum_{c \in S}\kappa_c$, đúng định nghĩa đang dùng cho
$K = 4$. Ngân sách giữ **tỉ số** $B/(H\sum_{c\in S}\kappa_c)$, tức trục đã chứng minh là
bất biến thang. Cách này **không** giữ $\chi$ cố định, vì bỏ carrier là đổi $\chi$. Điều đó
khai ở đây, không giấu.

**Lưới.** Cả 4 tập $K = 3$, cả 6 cặp $K = 2$, và $K = 4$ làm đối chứng. Ngân sách
0,3205 và 0,75; $\Delta \in \{2, 4\}$; detector mid; $N = 40$, 3 seed, USD. Chính sách: B1,
B2, `SSG-full`, `SSG-up`, `SSG-G`, `SentinelW`.

| # | Dự đoán | Sai khi nào |
|---|---|---|
| K1 | Ở $K = 4$ công cụ **tái lập đúng từng chữ số** bảng quét $\pi_0$ ở $\pi_0 = 0{,}0799$ | lệch — khi đó công cụ đổi thứ gì khác ngoài $K$, là **lỗi** |
| K2 | Ở 0,75, `SSG-up` vượt B1 ≥ 15% ở **cả 4** tập $K = 3$ khi $\Delta = 4$, và ở **≥ 3/4** khi $\Delta = 2$. Nghĩa là kết quả không do riêng một carrier gánh | ít hơn thế |
| K3 | Ở 0,75, chính sách tốt nhất thuộc họ SSG (`SSG-full`/`SSG-up`/`SSG-G`) ở **mọi** tập $K = 3$ | có tập $K = 3$ mà chính sách tốt nhất ngoài họ SSG |
| K4 | Ở 0,75, $\Delta = 4$, **độ rải** của độ lợi `SSG-up` qua 6 cặp $K = 2$ **lớn hơn** độ rải qua 4 tập $K = 3$ | nhỏ hơn hoặc bằng |

## 3. $H$: phân phối $\Delta$ thật quyết định $H$ cần bao nhiêu

$\Delta$ thật đã đo trên SWE-bench Verified (`spikes/delta-swebench.json`, theo từng repo). Một
tấn công có độ trễ $\Delta$ chỉ **đặt vừa** một workflow $H$ task nếu $\Delta \le H - 1$. Công cụ
báo tỉ lệ instance có $\Delta \le H - 1$ theo từng repo, với $H \in \{4, 6, 8, 10, 12, 16\}$. Đây là
phép mô tả nên không có dự đoán; kết quả được báo như đo. $H = 8$ **được biện hộ** nếu nó
phủ **≥ 90%** $\Delta$ đo được ở mọi repo có $n \ge 10$. Nếu không, README ghi $H$ tối thiểu đạt
tiêu chí đó.

## 4. $N$ và số seed: phân tích lực

**$N$.** Từ nửa độ rộng CI ở $N = 100$ (`certified-power-*.json`), nửa độ rộng co theo
$\sqrt{100/N}$. $N$ **cần** cho một ô là $N$ nhỏ nhất sao cho độ lợi thật bằng số đo điểm vẫn
cho cận dưới > 15%.

**Seed.** Ở ô headline (0,75, $\Delta = 2$, mid, `SSG-up` so với B1, $N = 100$), tính CI với 1, 3
và 5 seed trên **cùng** 100 workflow.

| # | Dự đoán | Sai khi nào |
|---|---|---|
| S1 | Nửa độ rộng CI **gần như không đổi** giữa 3 và 5 seed (chênh < 10%): phương sai nằm ở workflow, không ở seed. Nên 3 seed là đủ và tiền nên dồn vào $N$ | chênh ≥ 10% |
| S2 | Ô headline `SSG-up` 0,75 $\Delta = 2$ mid (+35,7%) cần $N \le 40$ để cận dưới > 15% | cần $N > 40$ |
