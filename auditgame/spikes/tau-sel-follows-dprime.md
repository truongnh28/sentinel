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

Luật phán quyết được **chốt trước** khi chạy phép đo mới (xem báo cáo
`.superpowers/sdd/task-tausel-report.md` §0): gọi
`D = Δharm(d′=3.0) − Δharm(d′=0.0)` là **độ tụt** dọc lưới ở `Δ = 0`; đọc **(a)**
khi `D_mới < 0` và `|D_mới| ≥ 0.5·|D_cũ|`, đọc **(b)** khi `D_mới ≥ 0` hoặc
`|D_mới| < 0.5·|D_cũ|`.

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
**0.2644** (`d2.4`) → **0.2349** (`d3.0`): hàng mới **thật sự** động theo `d′`, và
không đơn điệu — đúng như `scoring.tau_sel` đã cảnh báo về chiều `n`.

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

**Ô `Δ = 2` không hề dịch.** Trên **cùng một lưới thô**, cả hai chế độ đều cho
`d′* = 2.60`; chênh lệch 2.55 ↔ 2.60 **hoàn toàn** là do chế độ mới không chạy bước
mịn hoá 0,05, không phải do ngưỡng đổi. Nghi vấn *"`d′* ≈ 2.5` là artefact của
`tau_sel` ghim"* — **bác bỏ**.

---

## 5. Chuỗi `Δ = 0`, cũ so với mới — và phán quyết

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

> ### PHÁN QUYẾT: **ĐỌC (a) — CƠ CHẾ LÀ THẬT.**
> Đảo chiều ở `Δ = 0` **sống sót nguyên vẹn** khi `tau_sel` chạy theo `d′`: không
> phải "yếu đi trong ngưỡng cho phép" mà **trùng từng chữ số** ở cả 16 điểm lưới, ở
> cả `Δharm` lẫn hai đầu CI95. Luật đã chốt đòi `|D_mới| ≥ 0.5·|D_cũ|`; thực tế
> `|D_mới| = 1.000·|D_cũ|`. Tiên nghiệm ghi trong đề bài (một hiện thực độc lập báo
> **−37%**, nghiêng về (a)) được xác nhận **theo hướng mạnh hơn**: thay đổi là **0%**.

Ba ô còn lại cũng trùng từng chữ số — xem §6 để biết vì sao, vì đó mới là kết quả
thật sự của spike này.

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
cd HCMUT/code/Sentinel/auditgame
find . -name __pycache__ -type d -exec rm -rf {} +

# §2.1  bảng tham chiếu (≈23 phút; ghi đè reference/score_table.json)
python3 reference/gen_score_table.py            # SEED=20260915, M=800000
python3 reference/gen_score_table.py --check    # phải in CHECK: MATCH

# §4, §5  cột "cũ"  — corpus seed 2026, seed chạy 1,2,3
python3 dprime_sweep.py --n 40 --json sweep_old.json

# §4, §5  cột "mới"
python3 dprime_sweep.py --n 40 --tau-follows-dprime --json sweep_new.json

# §2.2  bảng tau_sel theo hàng
python3 -c "import scoring; print([scoring.tau_sel(9, n, 1) for n in ('mid','d0.0','d2.2','d3.0')])"

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

python3 tests/run_all.py
```

Đã chạy chế độ mặc định **hai lần** — một lần trên bảng cũ, một lần trên bảng đã mở
rộng — và hai file JSON **trùng từng byte**.

**Bất biến số đóng băng.** Không sửa `oracle.py`, `runner.py`, `scoring.py`,
`metrics.py`, `detector.py`, `core.py`, `experiment.py`, `policies.py`. Ba bảng
`weak/mid/strong` byte-identical (§2.1). Đây là phép đo **cộng thêm**.
