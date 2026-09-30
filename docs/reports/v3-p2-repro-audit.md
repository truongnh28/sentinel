# Sentinel v3 P2 — kiểm tra tái lập các số rẻ, tất định (D19)

27/09/2026, nhánh `worktree-agent-af9ecc4898a606a70`, tách từ `int-p2` (`4be2744`). Đây là **phụ lục tái lập** cho báo cáo #8: chạy lại **chỉ các bộ sinh rẻ, tất định** và đối chiếu từng số đã ghim trong các báo cáo P2/P3 với giá trị sinh lại. Mục tiêu là bắt hồi quy âm thầm sau các lượt merge gần đây (M1 6 seed, `--jobs`, cost, wiring). **Không** chạy grid/rollout/tuning/build-table nặng, **không** chạm eval split, chỉ đọc mã (read-only trên mọi `.py`).

Lệnh dùng (đều < 1 phút, chạy từ `auditgame/` với `../.venv/bin/python`):
- `../.venv/bin/python -m v3.grid --report` (2,9 s CPU) — mô hình chi phí P0 + sau cắt.
- đọc `reference/v3_kappa_measured.json` (không chạy đo lại).
- đọc `data/swerebench_v2.manifest.json` và các hằng `EVAL_SUMMARY_PINNED` / `EVAL_SPLIT_SHA256` trong `v3/corpus.py` (chỉ hình dạng đã ghim, **không** đọc instance eval nào).
- gọi API trong bộ nhớ của `v3.grid` / `v3.budget` cho các số phụ (ô WINDOW, khối untrimmed) — cùng một bộ sinh tất định, không có lượt chạy nặng.
- đọc `v3/config.py` (`KAPPA_UNIT`, `TABLE_DIFF_SE_MAX`).

## Kết luận trước

- **Không có MISMATCH nào.** Mọi số rẻ, tất định kiểm được đều khớp từng chữ số với báo cáo tương ứng. Các merge gần đây không làm trôi số nào trong phạm vi kiểm.
- Các số **không** kiểm được đều thuộc loại SKIPPED-TOO-EXPENSIVE (N3): chúng cần build-table / m1-smoke / measure-kappa (mỗi thứ từ nhiều phút tới cả giờ) hoặc cần đọc file spike đã bị `.gitignore` và không có mặt sau `git reset --hard int-p2`. Không ghi 0 hay số đoán cho bất kỳ mục nào.

## Bảng kiểm số → kết quả

### A. `v3-p2-cost.md` — `python -m v3.grid --report`

| Số kiểm | Báo cáo | Sinh lại | Kết quả |
|---|---|---|---|
| Bảng khối split phụ (26 wf), 6 khối + tổng | mọi ô, tổng lõi 16.390.618 / 11.484.781 / 23.719.712 / 17.234.013 | trùng từng ô | MATCH |
| Bảng khối split chính (96 wf), Mô hình P0 + 3 cột cắt | tổng 62.416.541 / 43.254.077 / 91.148.829 / 65.543.095 | trùng từng ô | MATCH |
| Reproduction P0 (Mô hình P0 = P0 báo cáo, split phụ) | 6/6 khối khớp | trùng | MATCH |
| P0 rollout headline | 7.638 + 18.650 (`P0_HEADLINE`) | 7638 + 18650 | MATCH |
| CPU-giờ mô phỏng lõi split phụ | 2,5 / 5,3 / 3,8 | 2.5 / 5.3 / 3.8 | MATCH |
| CPU-giờ mô phỏng lõi split chính | 9,5 / 20,2 / 14,5 | 9.5 / 20.2 / 14.5 | MATCH |
| Rollout headline split phụ R=16/32/64 | held-out 47/94/188, BR 129/259/517 | trùng | MATCH |
| Rollout headline split chính R=16/32/64 | held-out 183/366/732, BR 614/1229/2457 | trùng | MATCH |
| Rollout headline mẫu con 30 wf, R=16 | 59 / 194 / 253 | 59 / 194 / 253 | MATCH |
| Số ô bị loại khỏi H18 | 220 | 220 (đếm dòng `dropped`) | MATCH |
| Ô WINDOW (Định lý 5.6(i)) | 33, chủ yếu Δ=1 (Δ=2 ở χ=2,11) | 33 ô riêng biệt; Δ=1: 27, Δ=2: 6 | MATCH |
| Khối untrimmed attacker-Δ (reversible), đơn vị P0 | 84.122 | 84122 | MATCH |
| Khối untrimmed attacker-Δ (reversible), split chính | 328.451 | 328451 | MATCH |
| Histogram H mẫu con 30 wf | {6:4,7:4,8:3,9:1,10:3,11:6,12:2,13:4,14:3} | trùng (`HEADLINE_ROLLOUT_H_HISTOGRAM`) | MATCH |
| sha256 thứ tự mẫu con | `11239b71e085…` | `11239b71e0857d4face8737f393e13d4cd2cb663ed12b58a94f46285eae39e01` | MATCH |

### B. `v3-p3-kappa.md` — `reference/v3_kappa_measured.json`

| Số kiểm | Báo cáo | JSON | Kết quả |
|---|---|---|---|
| κ(d=1) memory/queue/skill/commit | 0,00089 / 0,00082 / 0,0174 / 0,0752 | 0,00089 / 0,00082 / 0,01738 / 0,07516 | MATCH |
| κ(d=2) 4 mục tiêu | 0,00125 / 0,00129 / 0,0355 / 0,1701 | 0,00125 / 0,00129 / 0,03545 / 0,17006 | MATCH |
| κ(d=3) 4 mục tiêu | 0,00156 / 0,00174 / 0,0524 / 0,2504 | 0,00156 / 0,00174 / 0,05236 / 0,25042 | MATCH |
| CI 95% boot (memory/queue/skill/commit, d=1) | [0,00029;0,00203] / [0,00044;0,00154] / [0,0141;0,0213] / [0,0406;0,1281] | trùng | MATCH |
| κ(d)/(d·κ1) ở d=3 | 0,58 / 0,71 / 1,00 / 1,11 | 0,5845 / 0,7083 / 1,004 / 1,111 | MATCH |
| Tách theo họ, django d=1 | 0,00036 / 0,00045 / 0,0131 / 0,0315 | 0,00036 / 0,00045 / 0,01312 / 0,03151 | MATCH |
| Tách theo họ, sympy d=1 | 0,00174 / 0,00141 / 0,0242 / 0,1450 | 0,00174 / 0,00141 / 0,0242 / 0,145 | MATCH |
| χ đo được (range) 1.04 / 1.33 / 2.11 | 2,58 / 3,10 / 3,15 | 2,5843 / 3,0975 / 3,1550 | MATCH |
| χ đo được (2·MAD) 1.04 / 1.33 / 2.11 | 1,88 / 2,15 / 2,19 | 1,8840 / 2,1516 / 2,1898 | MATCH |
| χ (range) nhân tuyến tính κ(1)·d | 2,53 / 3,04 / 3,15 | 2,5275 / 3,0364 / 3,155 | MATCH |
| CI 95% các ô χ | trùng (xem báo cáo) | trùng | MATCH |
| Trung vị một lần reset | 0,0051 CPU-phút | 0,0050981 | MATCH |
| Loại 2 lượt delegation | django-11141, django-15280 | `looks_excluded` trùng | MATCH |
| Mẫu: 13 wf (django 8, sympy 5), audit t=3 | như báo cáo | `sample` trùng | MATCH |
| Chưa nối vào config | `wired_into_config` false; `KAPPA_UNIT` là bảng draft | false; `config.KAPPA_UNIT` = {0,4;0,9;1,6;4,1} | MATCH |

### C. `v3-p0.md` / `v3-p0-nguon-du-lieu.md` — corpus manifest & hình dạng đã ghim

| Số kiểm | Báo cáo | Nguồn ghim | Kết quả |
|---|---|---|---|
| Split chính: workflow / họ / Kish | 96 / 20 / 19,86 | `EVAL_SUMMARY_PINNED.primary` = 96 / 20 / 19,86 | MATCH |
| Split chính: instances | 941 | 941 | MATCH |
| Phần Δ=8 split chính | 56 / 20 / Kish 17,23 | `delta8` = 56 / 20 / 17,23 | MATCH |
| Split phụ (C14): wf / họ / Kish | 26 / 18 / 10,24 | `EVAL_SUMMARY_PINNED.secondary` = 26 / 18 / 10,24 | MATCH |
| Phần Δ=8 split phụ | 18 / 12 / 7,36 | 18 / 12 / 7,36 | MATCH |
| Tổng instance nguồn V2 | 32.079 | `manifest.parquet_rows` = 32079; `index rows` = 32079 | MATCH |
| Revision nguồn | 475dd5e… | `REBENCH_REVISION` = `manifest.revision` = 475dd5e8703bb5fb… | MATCH |
| License | CC-BY-4.0 | `manifest.license` | MATCH |
| `config.TABLE_DIFF_SE_MAX` (v3-p2-table.md line5-se-diff) | 0,15 | 0,15 | MATCH |

Ghi chú C: các con số hình dạng eval được đối chiếu với **hằng đã ghim** trong `v3/corpus.py` (`EVAL_SUMMARY_PINNED`) và với **metadata manifest** (`data/swerebench_v2.manifest.json`), đúng như `v3-p2-cost.md` tuyên bố (chỉ đọc hình dạng, không đọc instance). Không gọi `corpus.eval_summary()` sống trên pool vì việc đó sẽ **đọc eval split** (bị cấm). Vì vậy đây là kiểm "báo cáo có trích đúng hằng ghim không", không phải kiểm "hằng ghim có bằng lượt build sống không".

## Các số SKIPPED-TOO-EXPENSIVE (N3 — không bịa)

| Số / báo cáo | Lý do skip |
|---|---|
| Pilot digest bảng dòng 5 `sha256:1198b5e4…cb69be` (`v3-p2-table.md`) | File `spikes/v3-table/v3_line5_table_pilot.npz` bị `.gitignore`, không có mặt sau `git reset --hard int-p2`. So chuỗi cần file; dựng lại cần `v3_build_table.py --pilot` (~1 giờ thật) — nặng và do agent khác sở hữu. |
| Mọi số pilot bảng dòng 5 theo h (CPU-giây/khoá, SE, ms/rollout) và ngoại suy 223,7 / 225,1 CPU-giờ (`v3-p2-table.md`, `v3-p2-cost.md` §matched-load) | Cần `v3_build_table.py --pilot/--sources-only/--extrapolate` (nhiều phút tới hàng giờ) và các file spike vắng mặt. Vi chuẩn CPU cũng phụ thuộc tải máy (báo cáo đã khai). |
| Mọi số M1 (`v3-p2-m1.md`): bảng V / V_BR, clean completion, FQ, cổng 3a–4, lượt 6 seed | Cần `tools/v3_m1_smoke.py` (283k–869k episode scripted + BR; 230 s / 758 s). Tóm tắt `spikes/v3-m1/*.json` bị `.gitignore` và vắng mặt. |
| κ tính theo giây (insertion 0,018 s … commit 2,46 s) (`v3-p3-kappa.md`) | Là **trung vị** lấy từ số thô `spikes/v3-kappa/{django,sympy}.json` (gitignored, vắng mặt); `reference/v3_kappa_measured.json` chỉ lưu **mean**, không lưu trung vị lượt nhìn. Dựng lại cần `v3_measure_kappa.py` (chạy test django/sympy — nặng). |
| Đối chiếu `EVAL_SUMMARY_PINNED` sống với lượt build eval | Sẽ phải build/đọc eval split — bị cấm (DEV ONLY). Chỉ kiểm được tính nhất quán của hằng ghim với báo cáo. |

## Kết luận cho #8

Phụ lục này xác nhận: mọi số rẻ tất định trong `v3-p2-cost.md`, `v3-p3-kappa.md`, `v3-p0.md` và `v3-p0-nguon-du-lieu.md`, cùng hai hằng config của `v3-p2-table.md`/`v3-p2-m1.md`, **tái lập từng chữ số** từ seed đã ghim (D19) trên `int-p2` (`4be2744`). Không phát hiện hồi quy do các merge M1/`--jobs`/cost/wiring. Các số đắt (bảng dòng 5, M1, κ đo lại) chưa kiểm ở đây vì vượt ngân sách compute và/hoặc file spike không được commit; chúng cần một lượt kiểm riêng trên máy có ngân sách.
