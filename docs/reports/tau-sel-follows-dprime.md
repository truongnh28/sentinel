# `tau_sel` chạy theo `d′` — gỡ confound đã khai báo của phép quét `d′`

**Ngày đo:** 18/09/2026 · **Module:** `dprime_sweep.py`, `reference/gen_score_table.py`
**Test:** `tests/gate1_integrity/test_score_table_generator.py`,
`tests/gate2_validity/test_dprime_break_even.py`

---

## 1. Câu hỏi

Spike `dprime-sweep.md` §2 và §10.1 **tự khai** một confound: chuỗi `setting` vừa là
khoá tra bảng `tau_sel` đóng băng, và phép quét giữ `setting="mid"` ở **mọi** `d′`.
Nghĩa là ngưỡng chọn-carrier của policy đứng yên ở mức hiệu chỉnh cho `d′ = 2.211`
trong khi detector chạy theo `d′` quét. Hai hệ quả bị treo lại:

1. `d′* ≈ 2.5` ở `Δ = 2` **có thể** là artefact của ngưỡng lệch hiệu chỉnh;
2. **đảo chiều ở `Δ = 0`** — `Δharm` âm và **càng âm thêm** khi audit tốt lên —
   cần phân định giữa hai cách đọc:
   - **(a) cơ chế thật**: đảo chiều **SỐNG SÓT** khi `tau_sel` chạy theo `d′`;
   - **(b) artefact**: đảo chiều **biến mất hoặc yếu đi đáng kể**.

### 1.1 Tiền-đăng-ký — luật phán quyết, chốt TRƯỚC khi đo, chép nguyên văn vào đây

Luật dưới đây được viết và đóng dấu thời gian **trước** khi phép quét ở chế độ mới
được chạy: lúc đó phép sinh bảng tham chiếu còn đang chạy và **chưa tồn tại một
con số nào** của chế độ mới. Dự án đã một lần bị bỏng vì chọn luật tóm tắt *sau*
khi nhìn thấy dữ liệu (finding **P7**), nên luật được chép **nguyên văn vào chính
artefact được commit này** — không phải chỉ trỏ đi nơi khác — để nó không thể bị
dịch chuyển về sau và để người đọc chỉ có repository vẫn kiểm được nó.

> **TIỀN-ĐĂNG-KÝ (chốt trước phép đo).** Trên đúng mặc định đã công bố của module
> (`--n 40 --H 8 --budget 17.95 --seeds 3`, corpus seed `2026`).
>
> Gọi `D_cũ = Δharm_cũ(d′=3.0) − Δharm_cũ(d′=0.0)` và
> `D_mới = Δharm_mới(d′=3.0) − Δharm_mới(d′=0.0)` là **độ tụt** dọc lưới ở `Δ = 0`
> (âm = đảo chiều: audit tốt lên làm Sentinel **tệ đi**).
>
> * Đọc **(a) SỐNG SÓT** ⟺ ở chế độ mới: (i) `Δharm_mới(d′) < 0` trên **nửa trên**
>   của lưới, **và** (ii) `D_mới < 0`, **và** (iii) `|D_mới| ≥ 0.5·|D_cũ|`.
> * Đọc **(b) ARTEFACT / yếu đi đáng kể** ⟺ `D_mới ≥ 0` (độ tụt mất hẳn hoặc đổi
>   dấu) **hoặc** `|D_mới| < 0.5·|D_cũ|` (mất ít nhất một nửa độ lớn).
>
> Mức cắt **50%** là ranh giới giữa *"vẫn là phát hiện cũ, chỉ nhạt đi"* và *"phát
> hiện đó phần lớn là do ngưỡng bị ghim"*. Nó được phát biểu ở đây để về sau không
> ai dịch được nó.

*(Bản gốc của khối trên là §0 của nhật ký công việc `task-tausel-report.md`, nằm
dưới `.superpowers/sdd/` — thư mục đó **gitignored, không đi kèm repository**. Bản
trong tài liệu này là bản có hiệu lực cho mọi người đọc chỉ có repo.)*

> **Đọc §5 trước khi dùng luật này.** Luật trên **vô hiệu** ở đây: nó ngầm giả định
> `tau_sel` có đường đi tới cặp policy định nghĩa `Δharm`, và §6 cho thấy **không
> có**. Cái spike này phân định được là **loại bỏ một nghi can**, không phải xác
> nhận cơ chế.

---

## 2. Cái đã làm — bảng tham chiếu mọc thêm 16 hàng khoá theo `d′`

`reference/gen_score_table.py` sinh thêm **một hàng cho mỗi điểm** của
`dprime_sweep.GRID`:

| | |
|---|---|
| Tên hàng | `f"d{d_prime:.1f}"` → `d0.0`, `d0.2`, …, `d3.0` (**16 hàng**) |
| Đầu vào | **chính `d′`**, không phải cặp `(ψ, φ)` |
| `φ` | **CỐ ĐỊNH** `0.12` ⇒ `τ_det = z(1−φ) = 1.17498679206609` |
| `ψ` | `Φ(d′ − τ_det)` — **dẫn xuất**, không phải đầu vào |
| Mọi thứ khác | y nguyên: `M = 800 000`, `SEED = 20260915`, `π₀ = 0.10`, `n ≤ 30`, `K ≤ 4` |

**Vì sao `φ` phải cố định.** Đây đúng là giao kèo mà `dprime_sweep.py` phát biểu cho
đường cong — *"mọi điểm trên đường cong có cùng một tỉ lệ báo động giả"*. Một hàng
`tau_sel` có `φ` trôi theo `d′` sẽ dựng lại đúng chiều thứ hai mà phép quét sinh ra để
loại bỏ, và ngưỡng khi đó được hiệu chỉnh cho một detector **khác** với detector đang
chạy. Chú thích này nằm trong docstring của module sinh bảng và trong khối
`provenance` của chính file JSON.

`scoring.py` **không bị sửa một dòng nào**: `scoring.tau_sel(n_c, setting, k)` vốn là
một phép tra dict theo **TÊN** setting, nên tên mới là đủ.

### 2.1 Ba bảng cũ **BYTE-IDENTICAL** — chứng minh, không phải khẳng định

RNG mỗi setting là `random.Random(SEED ^ hash_name(TÊN))` (blake2b), nên **thêm**
setting không đụng vào dòng ngẫu nhiên của setting cũ. Trích riêng ba bảng, tuần tự
hoá cùng một cách (`json.dumps(indent=2, ensure_ascii=False, sort_keys=True)`) rồi so
md5:

| bảng | md5 **trước** | md5 **sau** | |
|---|---|---|:--:|
| `weak` | `b6adee03810eb4d4dd18ca9b8015144d` | `b6adee03810eb4d4dd18ca9b8015144d` | **TRÙNG** |
| `mid` | `0d8bec2e446458928fe10eb9d1b470fd` | `0d8bec2e446458928fe10eb9d1b470fd` | **TRÙNG** |
| `strong` | `6e998942f967a93be1e7f394aed35942` | `6e998942f967a93be1e7f394aed35942` | **TRÙNG** |

Bảng **"trước"** không phải là một file nằm đâu đó trên máy: nó là
`reference/score_table.json` **ở commit `65ac973`** (commit ngay trước lần mở rộng).
Lệnh tái lập đúng ba md5 trên — chạy từ `auditgame`:

```bash
git show 65ac973:auditgame/reference/score_table.json \
  > /tmp/score_table.BEFORE.json
python3 - <<'EOF'
import hashlib, json
before = json.load(open("/tmp/score_table.BEFORE.json"))
after  = json.load(open("reference/score_table.json"))
def h(doc, name):                       # ĐÚNG công thức tuần tự hoá đã dùng
    blob = json.dumps(doc["tables"][name], indent=2,
                      ensure_ascii=False, sort_keys=True).encode()
    return hashlib.md5(blob).hexdigest(), len(blob)
for name in ("weak", "mid", "strong"):
    b, a = h(before, name), h(after, name)
    print(f"{name:7} {b[0]}  {a[0]}  {b[1]}/{a[1]} byte  "
          f"{'TRÙNG' if b == a else 'LỆCH'}")
EOF
```

Số byte cũng bằng nhau (10864 / 10809 / 10831). File **thêm đúng 16** bảng, **bỏ 0**
bảng. Khối `provenance` chỉ **mọc thêm** khoá (`settings_declared`,
`settings_by_dprime`, `settings_by_dprime_note`, `sweep_phi`, `additive`); khoá duy
nhất **đổi giá trị** là `measured_at`, vốn bị `--check` loại ra theo thiết kế sẵn có.

Test gate 1 `test_each_frozen_setting_still_draws_from_its_own_name_keyed_stream`
chạy **chính `build()`** đã mở rộng với `N_MAX = 1` (giữ nguyên `M = 800 000`) và so
hàng `n = 0, 1` với **file đã commit**. Đã kiểm tra test này **có răng**: cố tình cho
mọi setting dùng chung một RNG thì cả ba bảng cũ đỏ ngay.

### 2.2 Hàng mới có đúng là hiệu chỉnh theo `d′` không — một phép thử độc lập

`d2.2` (`d′ = 2.200`) và `mid` (`d′ = 2.211`) gần như cùng một `d′` nhưng chạy trên
**hai dòng ngẫu nhiên khác hẳn nhau**. `tau_sel(K = 1)`:

| hàng | `n=1` | `n=9` | `n=20` | `n=30` |
|---|---:|---:|---:|---:|
| `mid` (`d′=2.211`) | 0.2686 | 0.2628 | 0.2424 | 0.2301 |
| `d2.2` (`d′=2.200`) | 0.2706 | 0.2632 | 0.2421 | 0.2291 |

Khớp tới ~2×10⁻³. Toàn dải thì `tau_sel(n=9, K=1)` đi **0.1000** (`d0.0`) →
**0.2644** (`d2.4`, đỉnh) → **0.2349** (`d3.0`): hàng mới **thật sự** động theo
`d′`, và **không đơn điệu theo `d′`**.

**Chiều `d′` này là một hiện tượng KHÁC với cảnh báo trong docstring của
`scoring.tau_sel`.** Docstring đó nói về **chiều `n`** (đi theo `n` thì `weak` giảm
còn `strong` tăng — một artefact **đổi dấu** giữa các setting). Còn chỗ này là
chiều `d′`, và nguyên nhân là: detector càng sắc thì **posterior của carrier SẠCH
càng bị đẩy xuống** — `E[p_c | sạch, n=9]` đi đơn điệu **0.1000** (`d0.0`) →
**0.0522** (`d3.0`). `tau_sel` là **phân vị trên** của chính phân bố đó, nên nó chịu
hai lực ngược chiều: bề rộng phân bố **nở ra** theo `d′` (từ một điểm suy biến ở
`d′ = 0`) kéo phân vị **lên**, còn cả khối phân bố **trượt xuống** kéo nó **xuống**.
Tới quanh `d′ ≈ 2.4` thì lực thứ hai thắng, và đường cong quay đầu. Không có gì
đảo dấu ở đây, và hai hiện tượng không được lẫn vào nhau.

---

## 3. Chế độ mới của phép quét

`dprime_sweep.py --tau-follows-dprime`: tại mỗi điểm quét, `setting` dùng để tra
`tau_sel` là `setting_for(d′, True) = f"d{d′:.1f}"` thay cho hằng `"mid"`.

**Mặc định KHÔNG ĐỔI.** Chạy lại `python3 dprime_sweep.py --n 40` trên bảng **đã mở
rộng** cho ra JSON **trùng từng ký tự** với lần chạy trên bảng **cũ**, và trùng bảng
đã in trong `dprime-sweep.md` §5 — `d′*` = không có / không có / **2.55** / **0.60**.

**Cờ này tắt bước mịn hoá 0,05**, và đó là **giới hạn có lý do**: bảng chỉ có hàng ở
lưới thô, và cũng **không thể** có hàng ở điểm mịn hoá — khoảng cần mịn hoá chỉ biết
được *sau* khi đo xong lưới thô. Vì vậy `d′*` ở chế độ mới đọc ở độ phân giải 0,2.

---

## 4. `d′*(Δ)` — cũ so với mới

Theo đúng định nghĩa `d′*` đã chốt trong `dprime_sweep.break_even()`.

| Δ | `d′*` cũ (`tau_sel` ghim ở `mid`) | `d′*` mới (`tau_sel` theo `d′`) | Đơn điệu cũ → mới |
|:--:|:--|:--|:--|
| **0** | không có trong `[0, 3]` | **không có trong `[0, 3]`** | KHÔNG → KHÔNG |
| **1** | không có trong `[0, 3]` | **không có trong `[0, 3]`** | KHÔNG → KHÔNG |
| **2** | **2.55** (lưới thô **2.60**, mịn hoá kéo xuống 2.55) | **2.60** (không mịn hoá được) | KHÔNG → KHÔNG |
| **4** | **0.60** | **0.60** | CÓ → CÓ |

**Ô `Δ = 2` không hề dịch — nhưng ĐỪNG đọc sự trùng khớp này như bằng chứng.**
Trên **cùng một lưới thô**, cả hai chế độ đều cho `d′* = 2.60`, và chênh lệch
2.55 ↔ 2.60 chỉ là do chế độ mới không chạy được bước mịn hoá 0,05 (§3) — một
giới hạn **độ phân giải**, không phải một hiệu ứng của ngưỡng. Nhưng hai cột trên
**BUỘC PHẢI** trùng nhau: §6 chứng minh `tau_sel` **không có đường đi nào** tới
`B1 audit-at-commit` lẫn `Sentinel` — đúng cặp policy mà `Δharm`, và do đó `d′*`,
được định nghĩa qua. **Một phép thử không thể trượt thì không phải bằng chứng**,
nên bảng đo ở trên **tự nó không chứng minh được gì** về confound.

Nghi vấn *"`d′* ≈ 2.5` ở `Δ = 2` là artefact của `tau_sel` ghim"* vẫn **bị bác
bỏ** — nhưng bác bỏ **BẰNG CẤU TRÚC** (§6: không tồn tại đường cho confound đi
qua, nên nó **không thể** đã đặt `d′*`), **không** phải bằng việc hai chế độ đo ra
cùng một số. Ranh giới chính xác của cái spike này xác lập nằm ở hộp phán quyết
§5; đọc nó trước khi trích ô này.

---

## 5. Chuỗi `Δ = 0`, cũ so với mới — và vì sao luật đã chốt không phân định được

| `d′` | `Δharm` **cũ** | CI95 cũ | `Δharm` **mới** | CI95 mới | lệch |
|---:|---:|:--:|---:|:--:|---:|
| 0.00 | −0.008 | [−0.025; +0.000] | −0.008 | [−0.025; +0.000] | 0.000 |
| 0.20 | −0.017 | [−0.042; +0.000] | −0.017 | [−0.042; +0.000] | 0.000 |
| 0.40 | −0.029 | [−0.067; +0.000] | −0.029 | [−0.067; +0.000] | 0.000 |
| 0.60 | −0.037 | [−0.079; −0.008] | −0.037 | [−0.079; −0.008] | 0.000 |
| 0.80 | −0.046 | [−0.088; −0.008] | −0.046 | [−0.088; −0.008] | 0.000 |
| 1.00 | −0.058 | [−0.108; −0.017] | −0.058 | [−0.108; −0.017] | 0.000 |
| 1.20 | −0.079 | [−0.133; −0.033] | −0.079 | [−0.133; −0.033] | 0.000 |
| 1.40 | −0.079 | [−0.133; −0.033] | −0.079 | [−0.133; −0.033] | 0.000 |
| 1.60 | −0.083 | [−0.142; −0.037] | −0.083 | [−0.142; −0.037] | 0.000 |
| 1.80 | −0.096 | [−0.158; −0.042] | −0.096 | [−0.158; −0.042] | 0.000 |
| 2.00 | −0.104 | [−0.167; −0.050] | −0.104 | [−0.167; −0.050] | 0.000 |
| 2.20 | −0.125 | [−0.192; −0.067] | −0.125 | [−0.192; −0.067] | 0.000 |
| 2.40 | −0.200 | [−0.292; −0.117] | −0.200 | [−0.292; −0.117] | 0.000 |
| 2.60 | −0.208 | [−0.300; −0.125] | −0.208 | [−0.300; −0.125] | 0.000 |
| 2.80 | −0.208 | [−0.300; −0.125] | −0.208 | [−0.300; −0.125] | 0.000 |
| 3.00 | −0.208 | [−0.300; −0.125] | −0.208 | [−0.300; −0.125] | 0.000 |

Độ tụt: `D_cũ = −0.200`, `D_mới = −0.200`, **tỉ số 1.000**.

> ### PHÁN QUYẾT: LUẬT ĐÃ CHỐT **KHÔNG PHÂN ĐỊNH ĐƯỢC** Ở ĐÂY
>
> Đọc theo mặt chữ, luật §1 trả về **(a)**: `D_mới < 0` và
> `|D_mới| = 1.000·|D_cũ| ≥ 0.5·|D_cũ|`. **Nhưng kết luận đó không được phép rút
> ra**, vì §6 chứng minh `tau_sel` **không có đường nào** đi tới `B1
> audit-at-commit` lẫn `Sentinel` — đúng cặp policy mà `Δharm` được định nghĩa qua.
> Phép can thiệp của spike này **TRƠ VỀ MẶT CẤU TRÚC** đối với đại lượng đang đo:
> hai cột "cũ" và "mới" **buộc phải** trùng nhau, dù cơ chế đằng sau đảo chiều là
> thật hay là giả. **Một phép thử không thể trượt thì không phải bằng chứng.**
> Luật §1 được chốt **trước** khi đo (đúng quy trình, và vẫn nên làm vậy), nhưng nó
> **ngầm giả định một đường đi đang sống** — đường đó không tồn tại. Vì vậy ở đây
> luật **vô hiệu**: không phải vì kết quả xấu, mà vì câu hỏi nó hỏi không chạm được
> vào dữ liệu. Cặp chữ (a)/(b) giữ lại trong tài liệu này **chỉ** như tiền-đăng-ký,
> **không** như một phán quyết đã tuyên.
>
> **Spike này THỰC SỰ xác lập — không hơn:**
>
> 1. **LOẠI BỎ, bằng cấu trúc.** Giả thuyết *"`tau_sel` bị ghim ở `mid`"* **bị loại**
>    khỏi danh sách cách giải thích đảo chiều ở `Δ = 0`. Nó **không thể** đã tạo ra
>    đảo chiều và **không thể** đã đặt `d′*` của `Δ = 2` — không phải vì đo thấy ảnh
>    hưởng nhỏ, mà vì **không có đường nào** để ảnh hưởng đi qua (§6).
> 2. **KHÔNG xác lập.** Rằng **cơ chế** đằng sau đảo chiều là **thật**. Phép quét ở
>    chế độ mới mang **ZERO thông tin** về câu hỏi đó. Đảo chiều `Δharm < 0` và càng
>    âm thêm khi audit tốt lên **vẫn chưa được giải thích**, vẫn là câu hỏi mở — chỉ
>    là **bớt đi một nghi can**.

Ba ô còn lại cũng trùng từng chữ số — xem §6 để biết vì sao, vì đó mới là kết quả
thật sự của spike này.

### 5.1 Tiên nghiệm −37% đứng ở đâu — nguồn đầy đủ, vì nó là bằng chứng dương DUY NHẤT

Con số **−37%** **không** phải một phép đo của codebase này. Vì cách đọc (a) hiện
chỉ còn dựa vào nó, nguồn được ghi đủ ngay tại đây:

| | |
|---|---|
| **Run** | `rc-20260915-032257-35131b` (AutoResearchClaw) — 23 stage, 475 file; artefact gốc ở `~/Opensource/AutoResearchClaw/artifacts/rc-20260915-032257-35131b`, **ngoài repo này** |
| **Bản đối chiếu TRONG repo** | `HCMUT/261-Master-Proposal-Analysis/Doi-chieu-voi-research-run-rc20260915.md` §1.1, bảng *"Ranh giới chế độ nằm ở Δ ≈ 2"*, dòng `research run`, cột `Δ = 0` |
| **Nó đo cái gì** | **độ lớn phần THIỆT của Sentinel tại `Δ = 0`** — một kết quả **harm**, **KHÔNG** phải phép đo độ nhạy của kết quả với ngưỡng `tau_sel` |
| **Quan hệ với codebase này** | một **hiện thực độc lập**, khác ngôn ngữ, khác tác giả, khác tham số, và **không hề có cấu trúc `tau_sel`** đang bàn ở đây |
| **Cùng ô, phiên này đo** | **−17,8%** (cùng bảng, dòng *"phiên này (4 carrier)"*) — **cùng dấu**, khác độ lớn |
| **Độ tin cậy, phải khai** | chính bản đối chiếu §0 chấm run đó **3/10** và chốt quy tắc dùng: *lưới `stage-13` dùng được để đối chiếu **ĐỊNH HƯỚNG**, mọi vô hướng toàn cục thì không*. `−37%` là một ô của lưới đó ⇒ nó là bằng chứng về **DẤU**, không phải về **độ lớn** |

**Vì vậy:** nó **không** nghịch với con số 0% ở đây (hai bên đo **hai đại lượng
khác nhau** — một bên là phần thiệt, một bên là độ nhạy với ngưỡng; đặt cạnh nhau
là so sai đơn vị), và cũng **không** phải là "được xác nhận theo hướng mạnh hơn".
Chỗ đứng đúng của nó: **bằng chứng dương DUY NHẤT** hiện có cho cách đọc (a) —
**bằng chứng về dấu, từ một hiện thực độc lập**, nên là chứng cứ hỗ trợ mà confound
của codebase này **không thể** giải thích đi được. Muốn phân định (a)/(b) thật sự
thì phải can thiệp vào một đường **đang sống** đối với cặp `(B1, Sentinel)` — việc
đó chưa có ai làm.


---

## 6. VÌ SAO trùng khít — lời giải là **CẤU TRÚC**, không phải thống kê

Hai đường cong trùng nhau ở **cả 64 ô** `(d′, Δ)` không phải chuyện nhiễu nhỏ. Lần
theo đường đi của `setting`:

```
runner.paired  →  policies.make_policy(..., setting, ...)  →  Policy.setting
Policy.setting  →  Policy.tau(sig, k)  →  scoring.tau_sel(sig.n, setting, k)
```

và `Policy.tau` **chỉ được gọi ở hai chỗ trong toàn bộ `policies.py`**:

* `RiskScore.choose` (**B5 risk-score**);
* `TwoStage.choose` (**B6 two-stage**).

`Δharm` của phép quét được định nghĩa qua cặp **`B1 audit-at-commit`** và
**`Sentinel`**. **Không policy nào trong hai policy đó đọc bảng `tau_sel`.**
`AuditAtCommit` chấm patch tại thời điểm commit; `Sentinel` chọn carrier bằng bánh xe
roulette trên `belief`, và `belief` cập nhật từ `p_c/π₀` — **posterior**, chứ không
phải một phép so với ngưỡng.

**Đo trực tiếp** (40 workflow, 3 seed, `Δ = 4`, đổi *duy nhất* hàng `tau_sel`):

| policy | `d′ = 1.0`: `mid` → `d0.0` | `d′ = 3.0`: `mid` → `d0.0` → `d3.0` | động? |
|---|---|---|:--:|
| `B1 audit-at-commit` | 0.7793 → 0.7793 | 0.7793 → 0.7793 → 0.7793 | **không** |
| `Sentinel` | 0.7207 → 0.7207 | 0.3423 → 0.3423 → 0.3423 | **không** |
| `B5 risk-score` | 0.7793 → **0.6171** | 0.3829 → **0.2027** → **0.3649** | **CÓ** |
| `B6 two-stage` | 0.7793 → **0.7207** | 0.7207 → 0.7207 → 0.7207 | **CÓ** (ở `d′=1.0`) |

Cột B5/B6 là **đối chứng**: nó chứng minh đường ống `setting → tau_sel` đang **sống**,
nên "B1 và Sentinel không nhúc nhích" là một **kết luận**, không phải một phép đo
chết. Cả hai mệnh đề được ghim bằng test gate 2
`TheDeclaredConfoundIsInertForThisDeltaHarmPair`, trong đó test đối chứng chạy
**trước** test khẳng định.

> **Kết luận về chính cái confound.** Confound `tau_sel` ghim ở `mid` là **có thật**,
> nhưng nó **TRƠ** đối với đúng đại lượng mà phép quét báo cáo. Nó **không thể** đã
> góp phần vào đảo chiều ở `Δ = 0`, và **không thể** đã đặt `d′*` của `Δ = 2` ở
> 2,5 — không phải vì đã đo thấy ảnh hưởng nhỏ, mà vì **không có đường nào** để ảnh
> hưởng đi qua. Mục §10.1 của `dprime-sweep.md` (*"điều này **có thể** góp phần vào
> chiều đi xuống ở Δ=0"*) đến đây được **giải quyết: không**.

Hệ quả cho phần còn lại của luận văn: confound vẫn **sống nguyên** với mọi kết quả
**có dính B5 hoặc B6** — tức là đúng trục mà RQ4 đo (*"B5 lái theo điểm nên SỤP,
Sentinel có sàn nhờ ngẫu nhiên hoá"*). Bảng trên cho thấy B5 ở `d′ = 3.0` đi từ
`0.3829` (`mid`) xuống `0.2027` (`d0.0`): **nguyên một phần ba** harm của B5 đến từ
việc chọn hàng ngưỡng nào. Hàng `d0.0 … d3.0` bây giờ đã có sẵn cho phép đo đó —
**việc riêng, không thuộc việc này.**

---

## 7. Giới hạn

1. **Chế độ mới không mịn hoá được** (§3). `d′*` của `Δ = 2` ở chế độ mới đọc ở độ
   phân giải 0,2 (2.60), không so trực tiếp được với 2.55 của chế độ cũ; so sánh đúng
   là **trên lưới thô**, ở đó cả hai đều là 2.60.
2. **Trơ ≠ không quan trọng.** Kết luận §6 **chỉ** áp cho cặp `(B1, Sentinel)`. Mọi
   con số có B5/B6 vẫn mang confound này.
3. **Mock agent**, oracle marker-AST, 40 workflow, 3 seed — y như
   `dprime-sweep.md` §10.3–§10.4, không đổi.
4. **Hàng `d′` chỉ có ở lưới thô** `0.0 … 3.0` bước 0,2. Muốn quét mịn hơn thì phải
   sinh thêm hàng, và mỗi hàng tốn ~70 giây.

---

## 8. Tái lập — lệnh và seed cho từng con số

```bash
cd auditgame
find . -name __pycache__ -type d -exec rm -rf {} +

# §2.1  KIỂM bảng tham chiếu — KHÔNG ghi gì, và tự nó là ĐỦ (≈23 phút)
python3 reference/gen_score_table.py --check    # phải in CHECK: MATCH

# SINH LẠI bảng: chỉ khi thật sự cần, và KHÔNG BAO GIỜ chạy trước --check.
# Lệnh này GHI ĐÈ artifact đóng băng; chạy nó trước thì --check sau đó đang so
# file với CHÍNH NÓ và sẽ in MATCH bất kể script làm gì.  Từ 18/09/2026 script
# TỪ CHỐI (exit 2) khi file đã tồn tại mà không có --force.
#   python3 reference/gen_score_table.py --force   # ≈23 phút, SEED=20260915, M=800000
# Cứu bảng lỡ bị ghi đè (bảng HIỆN HÀNH, 3 + 16 hàng):
#   git show HEAD:reference/score_table.json > reference/score_table.json
# Bảng TRƯỚC khi mở rộng (dùng cho ba md5 ở §2.1):
#   git show 65ac973:auditgame/reference/score_table.json

# §4, §5  cột "cũ"  — corpus seed 2026, seed chạy 1,2,3
python3 dprime_sweep.py --n 40 --json sweep_old.json

# §4, §5  cột "mới"
python3 dprime_sweep.py --n 40 --tau-follows-dprime --json sweep_new.json
# (file --json mang sẵn khối "run": n, H, budget, seeds, corpus_seed, grid và
#  tau_follows_dprime — nên một file lưu trữ TỰ NÓI được nó là chế độ nào.)

# §2.2  bảng tau_sel theo hàng — ĐỦ cả bốn giá trị n của bảng in ở §2.2,
#       cộng toàn dải d' cho nhận định "không đơn điệu theo d'"
python3 - <<'EOF'
import scoring, dprime_sweep as S
for row in ("mid", "d0.0", "d2.2", "d3.0"):
    print(f"{row:6}", " ".join(f"{scoring.tau_sel(n, row, 1):.4f}"
                               for n in (1, 9, 20, 30)))      # -> bảng §2.2
names = [f"d{d:.1f}" for d in S.GRID]
tables = scoring.load_table()["tables"]
print("tau_sel(9,K=1):", " ".join(f"{nm}:{scoring.tau_sel(9, nm, 1):.4f}" for nm in names))
print("E[p_c|sach,9]:", " ".join(f"{nm}:{tables[nm]['rows'][9]['mean_p']:.4f}" for nm in names))
EOF

# §6  bảng nhạy cảm của từng policy
python3 - <<'EOF'
import dprime_sweep as S, runner, agent
wfs = S.make_corpus(40, 8, seed=2026); ag = agent.MockAgent()
for dp in (1.0, 3.0):
    for pol in (S.B1, S.SENTINEL, "B5 risk-score", "B6 two-stage"):
        hs = []
        for setting in ("mid", "d0.0", "d3.0"):
            runner.reset_survivor_cache()
            hs.append(round(runner.worst_case(pol, wfs, (4,), S.CARRIERS,
                      S.make_detector(dp), ag, 17.95, (1,2,3), setting).harm, 4))
        print(dp, pol, hs)
EOF

# §5.1  tiên nghiệm −37%: KHÔNG có lệnh nào ở repo này sinh ra nó — đó là số của
#       một run NGOÀI (`rc-20260915-032257-35131b`).  Tra trong repo:
#       HCMUT/261-Master-Proposal-Analysis/Doi-chieu-voi-research-run-rc20260915.md
#       §1.1 — dòng "research run" cột Δ=0 (−37%), dòng "phiên này" (−17,8%),
#       và §0 cho quy tắc "chỉ dùng lưới stage-13 theo ĐỊNH HƯỚNG".

python3 tests/run_all.py
```

Đã chạy chế độ mặc định **hai lần** — một lần trên bảng cũ, một lần trên bảng đã mở
rộng — và hai file JSON **trùng từng byte**.

**Bất biến số đóng băng.** Không sửa `oracle.py`, `runner.py`, `scoring.py`,
`metrics.py`, `detector.py`, `core.py`, `experiment.py`, `policies.py`. Ba bảng
`weak/mid/strong` byte-identical (§2.1). Đây là phép đo **cộng thêm**.
