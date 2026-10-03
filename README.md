# Sentinel — AuditGame-SE

**Học viên:** Nguyễn Hữu Trưởng · **GVHD:** TS. Lê Xuân Bách · **Phiên bản:** mã nguồn cuối (v3), 02/10/2026

Đề tài mô hình hoá việc phân bổ một ngân sách kiểm toán có hạn cho coding agent như một trò chơi
Stackelberg hữu hạn chân trời, quan sát được từng phần, giữa bên phòng thủ và kẻ tấn công. Kẻ tấn công
đầu độc một trong bốn *carrier* dai dẳng của agent (`memory`, `skill`, `queue`, `branch`); payload nằm im
và chỉ gây hại ở task kích hoạt $\sigma$, sau độ trễ $\Delta$ kể từ lúc gieo.

Repo gồm hai phần:

- **Sentinel**: chính sách kiểm toán theo Algorithm 1 của draft. Mỗi task, Sentinel chọn một hành động
  kiểm toán `(carrier, độ sâu)` trong ngân sách, cập nhật belief bằng particle filter 2048 hạt (có mô hình
  drift lành tính), và cách ly carrier khi xác suất nhiễm và tổn hại kỳ vọng vượt ngưỡng.
- **AuditGame-SE**: benchmark dựng workflow từ SWE-bench / SWE-rebench-V2, tiêm payload (AgentPoison,
  MINJA, MemPoison), chạy agent mô phỏng đã hiệu chuẩn, chấm tổn hại bằng oracle niêm phong ở cuối chân
  trời, rồi so Sentinel với các baseline B1–B7 (B1 = kiểm toán tại commit).

Thiết kế đầy đủ, ánh xạ từng mục của draft sang mã và test: [sentinel-v3.md](sentinel-v3.md).

## Kết quả chính

Đánh giá giữ ngoài, chạy một lần sau khi đóng băng: 931.500 bản ghi, 96 workflow từ 20 họ repository
chưa dùng trong phát triển (SWE-rebench-V2), 7 attacker giữ ngoài, 10 seed, 15 hệ thống. So với B1 ở
cùng ngân sách; khoảng tin cậy 95% bằng wild cluster bootstrap theo họ repo. Tính lại bảng này từ bản
ghi trong khoảng 10 giây:

```bash
cd auditgame && ../.venv/bin/python tools/quick_summary.py spikes/v3-run/eval-pass1 --n-boot 10000
```

| Mức lộ payload trong patch $\rho$ | Giảm hàm mất mát $L$ | Giảm tổn hại xấu nhất $V_{wc}$ |
|---|---|---|
| 0 | **+30,0%** [23,9; 34,7] | +4,3% [−2,8; 12,7] |
| 0,25 | **+27,7%** [18,8; 33,5] | −3,3% [−14,9; 6,1] |
| 0,5 | +8,6% [−0,1; 21,5], không kết luận | −39,1% [−56,4; −13,1] |
| 1 | −48,2% [−62,7; −29,0], B1 thắng | −354,1% [−435,7; −250,1] |

- **Sentinel thắng khi patch che giấu payload** ($\rho \le 0{,}25$) và thua khi payload lộ hoàn toàn trong
  patch, vì khi đó kiểm toán tại commit bắt gần hết.
- **Nguồn của mức +30,0%:** B1 chặn trung bình 0,633 task sạch mỗi episode ở mức báo động sai
  $\varphi = 0{,}12$; khoản này chiếm 74,3% mức cải thiện. Cách ly đúng dòng dõi không làm mất task sạch nào
  trong toàn bộ 931.500 bản ghi.
- **Ngân sách (H18):** tỉ lệ bỏ sót trước kích hoạt giảm từ 0,2007 ($\Delta = 4$) xuống 0,023–0,031
  ($\Delta = 8$), $p < 10^{-4}$ ở cả bốn mức $\rho$. Dữ liệu ủng hộ chiều "trễ dài hơn thì cần ít ngân sách
  hơn" và bác chiều ngược lại của Định lý 4 bản in.
- **Giới hạn:** so với một B1 mạnh hơn có đọc xuất xứ (chỉ chạy trên phần phát triển), mức cải thiện ở
  $\rho \le 0{,}25$ không còn ý nghĩa thống kê. Kết luận phụ thuộc trọng số $\lambda_T$ của task sạch bị mất:
  ở $\lambda_T = 0$ không ô nào dương.

Báo cáo chi tiết: [docs/reports/v3-p5-h18-heldout.md](docs/reports/v3-p5-h18-heldout.md) (H18, H19 trên
giữ ngoài), [v3-p6-a7.md](docs/reports/v3-p6-a7.md), [v3-p8-flat-charge.md](docs/reports/v3-p8-flat-charge.md),
[v3-p8-delta-star.md](docs/reports/v3-p8-delta-star.md); số trên phần phát triển ở
[v3-p2-headline-results.md](docs/reports/v3-p2-headline-results.md).

## Cấu trúc

```
auditgame/                 mã đo lường; mọi lệnh chạy từ trong thư mục này
  v3/                      Sentinel và benchmark v3
    sentinel.py              Algorithm 1: chọn hành động, belief, cách ly
    belief_pf.py, belief_exact.py   particle filter và belief chính xác (game nhỏ)
    baselines.py             B1–B7 và các ablation
    attackers.py, payload.py, library.py   attacker scripted / giữ ngoài, payload, thư viện 28 chính sách
    state.py, observe.py, oracle.py, stage_world.py   trạng thái carrier, quan sát, oracle niêm phong
    grid.py, runner.py, rollout.py   lưới thí nghiệm và vòng chạy
    metrics.py, scorecard.py  L, V_wc, bootstrap, chấm giả thuyết
    seal.py, freeze_v3.py    niêm phong phần đánh giá, manifest đóng băng
    dcm/                     ma trận đối chiếu draft ↔ mã ↔ test
  tools/                   script chạy: v3_run.py, v3_tune.py, v3_build_table.py,
                           v3_p5_h18_heldout.py, v3_p6_a7.py, ...
  tests/                   run_v3.py (bộ test v3), run_all.py (nền v1/v2)
  frozen/                  manifest đóng băng, V3-GATE4.json, log mở niêm phong
  reference/               tham số đã tinh chỉnh (v3_tuned.json, v3_kappa_measured.json, ...)
  data/, payloads/, hidden_tests/   dữ liệu workflow, payload, test ẩn của oracle
  workspace/               bản checkout repo SWE-bench (tải lại được, không cần đọc)
  spikes/                  kết quả trung gian và bản ghi của các lượt chạy
    v3-run/                  bản ghi thô mọi lượt v3 (15 GB): eval-pass1/ và eval-p1-h18kd/ là
                             lượt giữ ngoài; dev-*/ là các lượt trên tập phát triển
    v3-table/                bảng hành động đã tính sẵn của Sentinel (v3_line5_table.npz; thiếu file
                             này thì Sentinel không chạy và freeze-v3 báo lệch) và checkpoint lúc dựng
    v3-tune/                 checkpoint tinh chỉnh
  *.py (cấp gốc)           nền v1/v2 mà v3 tái sử dụng (carrier, harness, agent, detector, ...)
docs/
  README.md                mục lục đầy đủ, gồm cả tài liệu v1/v2 (design/, guides/, history/, thesis/, ...)
  HUONG-DAN-CHAY.md        hướng dẫn chạy thí nghiệm
  reports/                 báo cáo kết quả (v3-*.md là của v3)
  preregistration/         tiền đăng ký của v1–v3; của v3: phạm vi đánh giá, đại lượng chính, λ_T, ...
  plans/v3-p2-plan.md      kế hoạch triển khai
  v3/                      bản text của draft và DCM; test v3 đọc thư mục này
  FSE-2027-15-paper.pdf    draft gốc; test v3 kiểm sha256 của file này
sentinel-v3.md             thiết kế nghiên cứu v3
run_quick.sh               script chạy nhanh
Dockerfile                 môi trường cho agent thật (tách khỏi môi trường đo)
```

## Cài đặt và chạy

Cách nhanh nhất, khoảng 1,5 phút:

```bash
./run_quick.sh            # cài môi trường, kiểm tra bản đóng băng, chạy test,
                          # chạy 15 hệ thống trên 5 workflow dev, in bảng so với B1
./run_quick.sh 20 2       # 20 workflow, 2 seed
```

Hướng dẫn đầy đủ, gồm cả lệnh tái lập lượt đánh giá giữ ngoài và phần phân tích:
[docs/HUONG-DAN-CHAY.md](docs/HUONG-DAN-CHAY.md). Tóm tắt:

Lõi đo lường chỉ dùng thư viện chuẩn Python. Phần phân tích cần Python ≥ 3.14 và các gói trong
`pyproject.toml`:

```bash
uv sync                      # tạo .venv từ uv.lock
cd auditgame
```

Kiểm tra mã:

```bash
../.venv/bin/python tests/run_v3.py          # bộ test v3, dừng ở cổng đầu tiên bị đỏ
../.venv/bin/python -m v3.freeze_v3 --header # in dòng "freeze-v3: clean sha256:9c4c0d018b18..."
python3 tests/run_all.py                     # test nền v1/v2
```

`run_all.py` có 2 test đỏ ở cổng 2 (`some_epsilon_makes_the_payload_indistinguishable_at_every_delta`,
`one_split_cannot_decide_a_delta_of_the_certify_corpus`). Hai test này kiểm cổng lành tính của v1, không
thuộc bề mặt v3, và đã đỏ sẵn trong repo gốc.

Chạy thử một lượt nhỏ trên phần phát triển:

```bash
../.venv/bin/python tools/v3_run.py --split dev --count                        # số episode mỗi khối
../.venv/bin/python tools/v3_run.py --split dev --seeds 1 --workflows 5 --blocks main
```

Tính lại H18/H19 từ bản ghi giữ ngoài (cần bản ghi `spikes/v3-run/`, xem dưới):

```bash
../.venv/bin/python tools/v3_p5_h18_heldout.py
```

`--split eval` mở niêm phong phần đánh giá: lệnh yêu cầu `frozen/V3-GATE4.json`, manifest sạch, và mỗi lần
gọi ghi thêm một dòng vào `frozen/v3-unseal-log.jsonl`. Không cần chạy lệnh này để kiểm tra kết quả.

## Tính toàn vẹn của kết quả

- Tham số được tinh chỉnh chỉ trên phần phát triển, rồi đóng băng bằng manifest sha256
  (`frozen/MANIFEST-V3.json`). `V3-GATE4.json` ghim manifest, phần chia đánh giá và quy tắc chấm điểm trước
  khi mở niêm phong. Sửa bất kỳ file `.py` nào trong `auditgame/v3/` sẽ làm manifest lệch và `run_v3.py`
  báo đỏ.
- Phần đánh giá được mở bốn lần, cả bốn ghi trong `frozen/v3-unseal-log.jsonl`, kể cả một lần sai phạm vi
  (giải trình ở `docs/preregistration/TIEN-DANG-KY-bo-sung-luot1-chay-song-song.md`).
- Đại lượng chưa đo được ghi `null` kèm lý do, không ghi 0.
- Bản ghi thô của mọi lượt v3 nằm ở `auditgame/spikes/v3-run/`; mỗi thư mục có `records.sha256` để kiểm
  bằng `shasum -a 256 -c records.sha256`. `eval-pass1/` không có file này vì lượt đó bị dừng giữa khối
  `br`; `br.jsonl` dở dang được giữ nguyên nhưng không đọc.

## Chưa đo

- Lượt đánh giá thứ hai (32 ô còn lại) đã đăng ký nhưng chưa chạy.
- Độ khai thác được (khối đáp ứng tốt nhất của attacker) dở dang, không dùng.
- Attacker LLM, baseline B7 trên lưới đầy đủ, thế giới giai đoạn và xuất xứ trên phần giữ ngoài.
- Agent thật: thử nghiệm dẫn đường 0/7 workflow chạy được, nên mọi số liệu dùng agent mô phỏng đã hiệu chuẩn.
