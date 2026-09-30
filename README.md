# Sentinel — AuditGame-SE

**Đề tài:** FSE-2027-15 · **Học viên:** Nguyễn Hữu Trưởng · **GVHD:** TS. Lê Xuân Bách · **Cập nhật:** 30/09/2026

Repo này chứa mã nguồn, dữ liệu đo và tài liệu của đề tài Sentinel. Đề tài mô hình hoá việc phân bổ
một ngân sách kiểm toán có hạn như một trò chơi Stackelberg hữu hạn chân trời, quan sát được từng
phần, giữa bên phòng thủ và kẻ tấn công. Kẻ tấn công đầu độc các *carrier* dai dẳng của một coding
agent (`memory · skill · queue · branch`); payload nằm im và chỉ gây hại ở task kích hoạt $\sigma$,
sau độ trễ $\Delta$. Benchmark **AuditGame-SE** dựng quy trình từ SWE-bench, tiêm payload, chạy
agent mô phỏng, chấm tổn hại bằng oracle niêm phong, rồi so sánh các chính sách kiểm toán B1–B7
với **Sentinel**.

README cũ (báo cáo tiến độ v2, 25/09) được giữ nguyên văn ở
[docs/history/README-v2-tien-do-2509.md](docs/history/README-v2-tien-do-2509.md).


---

## Trạng thái

| | |
|---|---|
[| **Nghiên cứu hiện hành** | **v3** — thiết kế ở sentinel-v3.md](sentinel-v3.md). Tinh chỉnh chỉ trên phần chia phát triển, đóng băng bằng manifest, rồi đánh giá một lần trên phần chia giữ ngoài. |
| **Cổng 4** | **Đã ký 29/09/2026** (`auditgame/frozen/V3-GATE4.json`): ghim phần chia đánh giá, manifest v3 (`freeze-v3: clean sha256:9c4c0d018b18…`), bảng dòng-5 và quy tắc bảng điểm. |
| **Đánh giá giữ ngoài** | **Lượt 1 đã chạy**: 931.500 bản ghi, 96 quy trình từ 20 họ repository chưa từng dùng (SWE-rebench-V2), 7 attacker giữ ngoài, 10 seed, 15 hệ thống. Bốn lần mở niêm, ghi trong `auditgame/frozen/v3-unseal-log.jsonl`. **Lượt 2** (32 ô còn lại) đã đăng ký, **chưa chạy**; trục $\chi$ phải khai lại trước khi chạy. |
| **Bài báo** | Hai bản hội nghị đứng độc lập (EN 18 trang, VI 19 trang) và hai bản mở rộng (EN 88, VI 91) nằm **ngoài repo**, ở `HCMUT/paper-v3-conf`, `paper-v3-conf-vi`, `paper-v3`, `paper-v3-vi`. |
| **Chưa đo** | Độ khai thác được (khối đáp ứng tốt nhất dở dang, **không đọc**), lượt 2, attacker LLM, B7 trên lưới, thế giới giai đoạn và xuất xứ trên giữ ngoài, agent thật (thử nghiệm dẫn đường 0/7). |

## Kết quả chính (v3, giữ ngoài, cùng ngân sách, so với kiểm-toán-tại-commit B1)

| Mức lộ $\rho$ | Mức giảm hàm mất mát $L$ (95%) | Mức giảm tổn hại xấu nhất $V_{wc}$ (95%) |
|---|---|---|
| 0 | **+30,0%** [24,0; 34,7] | +4,3% [−2,8; 12,7] |
| 0,25 | **+27,7%** [18,8; 33,5] | −3,3% [−14,9; 6,1] |
| 0,5 | +8,6% [−0,1; 21,5] — không kết luận | −39,1% [−56,4; −13,1] |
| 1 | **−48,2%** [−62,7; −29,0] — B1 thắng | −354,1% [−435,7; −250,1] |

- **Chiều ngân sách (H18):** tỉ lệ bỏ sót trước kích hoạt giảm từ 0,2007 ($\Delta=4$) xuống 0,023–0,031 ($\Delta=8$), $p<10^{-4}$ ở cả bốn $\rho$: chiều giảm của Định lý 4 được xác nhận, chiều tăng bị bác.
- **Cơ chế:** B1 chặn 0,633 task sạch mỗi episode ở mức báo động sai $\varphi=0{,}12$; khoản này chiếm 74,3% của mức +30,0%. Khoản tính dòng dõi (cách ly đúng làm mất task sạch) bằng 0 trong toàn bộ 931.500 bản ghi.
- **Giới hạn:** so với B1 đọc xuất xứ (phát triển), mức giảm ở $\rho\le0{,}25$ mất ý nghĩa thống kê; kết luận phụ thuộc $\lambda_T$ (ở $\lambda_T=0$ không ô nào dương).
[- Chi tiết: v3-p2-headline-results](docs/reports/v3-p2-headline-results.md) (phát triển[), v3-p5-h18-heldout](docs/reports/v3-p5-h18-heldout.md)[, v3-p6-a7](docs/reports/v3-p6-a7.md)[, v3-p8-flat-charge](docs/reports/v3-p8-flat-charge.md)[, v3-p8-delta-star](docs/reports/v3-p8-delta-star.md).

## Các phiên bản nghiên cứu

| Bản | Ngày | Tóm tắt | Tài liệu |
|---|---|---|---|
| v1 | 18–25/09 | Dựng harness, đo tham số, bản đồ chế độ theo ngân sách; đóng băng `sha256:4ff1c8f72df4` | [README cũ](docs/history/README-v2-tien-do-2509.md) |
| v2 | 25–26/09 | Mô hình carrier §4 của draft, đánh giá một lần 57 quy trình; thêm phụ lục D35 | [v2 so với draft](docs/reports/v2-so-voi-draft.md), [tiền đăng ký v2](docs/preregistration/TIEN-DANG-KY-v2-thiet-lap-draft.md) |
[| **v3** | 27/09– | Nghiên cứu mới theo draft, phần chia giữ ngoài mới, Cổng 4 | sentinel-v3.md](sentinel-v3.md)[, kế hoạch P2](docs/plans/v3-p2-plan.md) |

Hệ thống đóng băng của v1/v2 (`freeze.header_line()` = `freeze: clean sha256:c789fa7362e0`) vẫn phải giữ sạch: v3 đọc v2 làm nền, và cổng 0 của bộ test v3 kiểm điều đó.

## Nhánh và worktree

| Nhánh | Vai trò |
|---|---|
| `master` | Nhánh chính trên GitHub. Đã trộn `v3` (PR #3, tới commit ký Cổng 4) và `int-p2` (PR #4: lượt 1 giữ ngoài, H18/H19 giữ ngoài, thế giới xuất xứ, báo cáo P8, log mở niêm). |
| `v3`, `int-p2` | Nhánh làm việc: tác giả trộn vào `v3`; agent làm trên `int-p2`. |
| `v3-lambda-t`, `v3-lambda-q` | Phép quét độ nhạy theo $\lambda_T$, $\lambda_Q$ (`auditgame/reference/v3_lambda_*.json`). Không chạm bề mặt băm; **chưa trộn**. |
| `v3-stage-world`, `v3-benign-gate`, `v3-b7-minimax`, `v3-run-resume` | Phép sửa hậu-đóng-băng và khả năng tiếp tục lượt chạy. **Làm trôi manifest**, nên **không trộn** cho tới khi Cổng 4 được ký lại. |

## Cấu trúc

```
auditgame/            mã đo lường (import phẳng, chạy từ trong thư mục này)
  v3/                 nghiên cứu v3: config, grid, runner, sentinel, baselines, metrics,
                      scorecard, seal, freeze_v3, stage_world, budget, line5 ...
  tools/              công cụ chạy: v3_run.py, v3_tune.py, v3_build_table.py, v3_p5_h18_heldout.py,
                      v3_p6_a7.py, ... (và công cụ v1/v2)
  tests/              run_all.py (v1/v2, ba cổng), run_v3.py (v3, ba cổng), tests/v3/
  frozen/             manifest đóng băng, V3-GATE4.json, v3-unseal-log.jsonl
  reference/          tham số đã tinh chỉnh, bảng điểm, kết quả quét
  spikes/v3-run/      bản ghi thô (không commit, ghim bằng sha256) và bảng tổng hợp
docs/                 tài liệu, xem docs/README.md
artifact/             smoke test đóng gói
sentinel-v3.md        thiết kế v3
```

## Chạy

Lõi đo lường chỉ dùng thư viện chuẩn; phần phân tích cần môi trường đầy đủ (`uv sync`). Mọi lệnh
chạy từ trong `auditgame/`.

```bash
cd auditgame
# v3
../.venv/bin/python tools/v3_run.py --split dev --count                 # số episode mỗi khối
../.venv/bin/python tools/v3_run.py --split dev --seeds 1 --workflows 5 --blocks main
../.venv/bin/python -m v3.freeze_v3 --header                           # dòng freeze-v3
../.venv/bin/python tests/run_v3.py                                    # ba cổng v3, dừng ở cổng đỏ đầu tiên
../.venv/bin/python tools/v3_p5_h18_heldout.py                         # H18/H19 trên bản ghi giữ ngoài đã có

# v1/v2
python3 tests/run_all.py                                               # ba cổng v1/v2
python3 freeze.py                                                      # dòng freeze v2
```

`--split eval` chỉ do tác giả chạy: nó gọi `seal.unseal`, yêu cầu tệp Cổng 4, manifest sạch và cây
`auditgame/` sạch, và **mỗi lần thử đều ghi thêm một dòng** vào log mở niêm. Luôn truyền `--systems`
tường minh: mặc định của một số khối rộng hơn 15 hệ thống đã khai.

## Quy tắc toàn vẹn

- Không sửa file trong bề mặt băm (`freeze_v3.FILES`, mọi `.py` trong `auditgame/v3/`, cây DCM) mà không ký lại Cổng 4. Công cụ mới đặt trong `tools/` thì an toàn.
- Không đọc `auditgame/spikes/v3-run/eval-pass1/br.jsonl` (khối đáp ứng tốt nhất dở dang) và `auditgame/spikes/v2-pilot/eval-touch-2509/`; không ghi vào `auditgame/spikes/v2/`.
- Không ghi `0` cho đại lượng chưa đo; ghi `null` kèm lý do. Tệp đầu ra mở ở chế độ `"x"`.
- Khoá API chỉ lấy từ biến môi trường, không ghi vào file, manifest, log hay commit.
- Git: chỉ `git add` đường dẫn tường minh; không `git add -A`; không xoá `.git/index.lock`; `.claude/` không commit.

## Việc còn mở trước khi nộp

1. **Bảng 1 giữ ngoài chưa có file đã commit.** Các dòng Bảng 1 và khoảng tin cậy từng dòng được sinh trong phiên P5 từ `spikes/v3-run/eval-pass1/main.jsonl`; `table2_3*.json` hiện có đều là bảng phát triển. Cần công cụ ghi `spikes/v3-run/eval-pass1/table2_3.json` rồi commit. Script tạm được giữ (chưa theo dõi) ở `docs/reports/session-p5-p10-scratch/` trong worktree `int-p2`.
2. **Cắt hiện vật ẩn danh từ `master`**, cộng hai nhánh $\lambda$ và ba nhánh sửa hậu-đóng-băng; điền liên kết vào bài.
3. Quyết định ký lại Cổng 4 cho các nhánh hậu-đóng-băng, và chạy B1 đọc xuất xứ trên giữ ngoài nếu cần.
4. Ba câu hỏi gửi thầy ngày 27/09 vẫn chờ trả lời.

## Tài liệu

Mục lục đầy đủ ở [docs/README.md](docs/README.md).
