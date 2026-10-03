# Hướng dẫn chạy thí nghiệm v3

Hướng dẫn tái lập thí nghiệm mới nhất của đề tài, tức lượt 1 đánh giá giữ ngoài của v3, cùng các bước
kiểm tra và phân tích đi kèm. Mọi lệnh chạy từ trong `auditgame/`.

## Chạy nhanh

```bash
./run_quick.sh                 # 5 workflow, 1 seed, khoảng 1,5 phút trên máy 10 nhân
./run_quick.sh 20 2            # 20 workflow, 2 seed
SKIP_TESTS=1 ./run_quick.sh    # bỏ qua bộ test
```

Script làm lần lượt các bước 0–2 dưới đây: cài môi trường nếu chưa có, kiểm tra dòng `freeze-v3`, chạy
`tests/run_v3.py`, chạy khối `main` ở ô headline trên dev với đủ 15 hệ thống, rồi gọi
`tools/quick_summary.py` để in $V(L)$, $V(\text{harm})$ của từng hệ thống và mức cải thiện của Sentinel so
với B1 theo từng $\rho$. Bản ghi nằm ở `auditgame/spikes/v3-run/quick-<thời điểm>/`.

Với 5 workflow và 1 seed, khoảng tin cậy rất rộng. Lượt nhanh chỉ để kiểm tra pipeline chạy đúng, không
dùng làm kết quả.

## 0. Chuẩn bị

```bash
uv sync                      # Python >= 3.14; tạo .venv từ uv.lock
cd auditgame
```

Dữ liệu đã có sẵn trong `auditgame/data/`, không cần tải:

| File | Nội dung |
|---|---|
| `swerebench_v2_eval_pool.jsonl.gz` | 20 họ repository của tập đánh giá (SWE-rebench-V2) |
| `swerebench_v2_index.jsonl.gz`, `swerebench_v2.manifest.json` | chỉ mục và sha256 ghim bản dữ liệu |
| `swebench_*.jsonl` | SWE-bench, dùng cho tập phát triển |

Tham số đã tinh chỉnh nằm ở `reference/v3_tuned.json` và `reference/v3_kappa_measured.json`. Cấu hình
chính (`v3/config.py`): $\chi = 1{,}33$, $d' = 2{,}21$, $\Delta \in \{0, 1, 2, 4, 8\}$ (số chính lấy
$\Delta \in \{4, 8\}$), $\rho \in \{0; 0{,}25; 0{,}5; 1\}$, 10 seed.

## 1. Kiểm tra mã đang ở đúng trạng thái đóng băng

```bash
../.venv/bin/python -m v3.freeze_v3 --header
#   freeze-v3: clean sha256:9c4c0d018b18  |  freeze-d35: clean sha256:e46f8a5c2f94  |  base freeze: clean sha256:c789fa7362e0
../.venv/bin/python tests/run_v3.py                      # bộ test v3, dừng ở cổng đầu tiên bị đỏ
../.venv/bin/python tools/v3_p5_h18_heldout.py --check-freeze   # đối chiếu với V3-GATE4.json
```

Dòng `freeze-v3` phải là `clean sha256:9c4c0d018b18`, đúng giá trị `V3-GATE4.json` đã ghim. Nếu khác,
mã đã bị sửa so với bản dùng để đánh giá.

## 2. Chạy trên tập phát triển (không cần mở niêm phong)

```bash
../.venv/bin/python tools/v3_run.py --split dev --count            # số episode của từng khối
../.venv/bin/python tools/v3_run.py --split dev --seeds 1 --workflows 5 --blocks main   # chạy thử, vài phút
```

Lượt phát triển dùng cho số dev của báo cáo `docs/reports/v3-p2-headline-results.md`:

```bash
../.venv/bin/python tools/v3_run.py --split dev --blocks main --headline --seeds 2 --jobs 8 \
    --systems "B1 audit-at-commit" "B2 uniform random" "B3 audit-on-insertion" \
              "B4 audit-on-retrieval" "B5 risk-score" "B6 two-stage" "cost-greedy" \
              "SW randomised" "Oracle (+)" "Sentinel" "Sentinel [dhat=oracle]" \
              "Sentinel -randomization" "Sentinel -alarm memory" "Sentinel -benign-drift"
```

Thế giới có tín hiệu xuất xứ (A7, chỉ trên dev, `docs/reports/v3-p6-a7.md`):

```bash
../.venv/bin/python tools/v3_p6_a7.py --diagnose
../.venv/bin/python tools/v3_p6_a7.py --run --jobs 8
../.venv/bin/python tools/v3_p6_a7.py --analyse
```

Kết quả ghi vào `spikes/v3-run/dev/` (hoặc thư mục `--out`), mỗi khối một file `.jsonl` kèm sha256.

## 3. Lượt 1 đánh giá giữ ngoài

Đây là lượt cho ra kết quả chính trong README. Lượt 1 chỉ gồm các ô headline ($\chi = 1{,}33$,
$d' = 2{,}21$, mọi $\rho$ và $\Delta$), cờ `--headline`. Phạm vi này đã đăng ký trước ở
`docs/preregistration/TIEN-DANG-KY-pham-vi-eval-headline.md`.

Luôn truyền đủ 15 hệ thống, vì mặc định của một số khối rộng hơn danh sách đã khai:

```bash
SYSTEMS=("B1 audit-at-commit" "B2 uniform random" "B3 audit-on-insertion" "B4 audit-on-retrieval"
         "B5 risk-score" "B6 two-stage" "cost-greedy" "SW randomised" "Oracle (+)"
         "Sentinel" "Sentinel [dhat=oracle]" "Sentinel -randomization" "Sentinel -alarm memory"
         "Sentinel -benign-drift" "Sentinel -transition uncertainty")

# Khối main: bảng so sánh với B1 (931.500 bản ghi)
../.venv/bin/python tools/v3_run.py --split eval --headline --seeds 10 --blocks main \
    --systems "${SYSTEMS[@]}" --out spikes/v3-run/eval-pass1

# Khối h18 và kd: giả thuyết ngân sách H18 và trục carrier uỷ nhiệm H19
../.venv/bin/python tools/v3_run.py --split eval --headline --seeds 10 --blocks h18 kd \
    --systems "${SYSTEMS[@]}" --out spikes/v3-run/eval-p1-h18kd
```

Điều kiện và lưu ý:

- **Lệnh mở niêm phong.** Trước khi nạp workflow nào, `seal.unseal` kiểm `frozen/V3-GATE4.json`, manifest
  sạch, sha256 của tập đánh giá, và `git status` của `auditgame/` phải rỗng. Thiếu một điều kiện thì lệnh
  dừng với mã thoát 2.
- **Cần một repo git sạch.** Bản copy này không có `.git` riêng, nên muốn chạy eval phải `git init`,
  commit toàn bộ, rồi mới chạy. Bản gốc có lịch sử git đầy đủ.
- **Mỗi lần gọi ghi thêm một dòng** vào `frozen/v3-unseal-log.jsonl`, kể cả khi bị từ chối. Log hiện có
  bốn dòng của lượt gốc.
- **Thời gian.** Lượt eval chạy trong một tiến trình (`--jobs` bị bỏ qua), khoảng 22 giờ trên một nhân.
  Lượt gốc được chia thành nhiều tiến trình chạy song song; cách chia được khai ở
  `docs/preregistration/TIEN-DANG-KY-bo-sung-luot1-chay-song-song.md`.
- **Khác biệt với lượt gốc.** Lượt gốc của khối main chạy với khối mặc định và bị dừng giữa khối `br`
  (đáp ứng tốt nhất của attacker). Kết quả chỉ dùng `main.jsonl`, nên lệnh trên chỉ chạy `--blocks main`.
  File `br.jsonl` dở dang không được đọc.

Bản ghi của lượt gốc có sẵn trong repo: `spikes/v3-run/eval-pass1/main.jsonl` và
`spikes/v3-run/eval-p1-h18kd/{h18,kd}.jsonl`. Không cần chạy lại lượt eval để kiểm kết quả; bước 4 đọc
thẳng các file này. sha256 của chúng ghi ở `docs/reports/v3-p5-h18-heldout.md` §0.

## 4. Phân tích

H18 và H19 trên bản ghi giữ ngoài (`docs/reports/v3-p5-h18-heldout.md`). Không chạy mô phỏng, không ghi
log mở niêm phong:

```bash
../.venv/bin/python tools/v3_p5_h18_heldout.py --dev-selfcheck   # chạy cùng pipeline trên dev; phải khớp 56/56 số
../.venv/bin/python tools/v3_p5_h18_heldout.py --run             # ghi spikes/v3-run/h_verdicts_eval.json
```

Bảng chính (mức giảm $L$ và $V_{wc}$ so với B1) tính bằng `v3/metrics.py`, theo cách tổng hợp mô tả ở
`docs/reports/v3-p8-flat-charge.md` §4:

1. Lấy ô headline, các attacker giữ ngoài (`HELD_OUT`, 7 attacker) và $\Delta \in \{4, 8\}$.
2. Mỗi bản ghi tính $L = \text{harm} + \lambda_Q \cdot FQ + \lambda_T \cdot \text{clean lost}$, với
   $\lambda_Q = 0{,}54865$ và $\lambda_T = 0{,}5$ (`runner.loss_of`).
3. Cột là cặp `attack@delta` (14 cột). Lấy trung bình theo seed trong từng workflow, rồi trung bình theo
   workflow trong từng cột. Giá trị của một hệ thống là cột xấu nhất.
4. Khoảng tin cậy: `metrics.gain_ci`, wild cluster bootstrap theo họ repo, 10.000 lần rút, $\alpha = 0{,}05$.

`tools/quick_summary.py` làm đúng các bước trên bằng hàm của `v3/metrics.py` và in bảng ra màn hình,
khoảng 10 giây:

```bash
../.venv/bin/python tools/quick_summary.py spikes/v3-run/eval-pass1 --n-boot 10000
```

Ngày 02/10/2026 lệnh này cho đúng các số trong README. Cận dưới ở $\rho = 0$ chính xác là 23,9499, tức
23,9 khi làm tròn một chữ số; bản hội nghị đang ghi 24,0.

## 5. Đầu ra

| Thư mục | Nội dung |
|---|---|
| `spikes/v3-run/<lượt>/<khối>.jsonl` | bản ghi từng episode |
| `spikes/v3-run/<lượt>/records.sha256` | sha256 ghim bản ghi |
| `spikes/v3-run/<lượt>/summary.json` | tóm tắt, đọc các control trước số của Sentinel |
| `spikes/v3-run/h_verdicts_eval.json` | kết luận H18/H19 trên giữ ngoài |
