# Khai bổ sung: lượt eval 1 được chạy bằng nhiều lệnh song song trên các block rời nhau

**Viết 29/09/2026 ~08:0x, TRƯỚC khi phóng các lệnh song song.** Bổ sung cho `TIEN-DANG-KY-pham-vi-eval-headline.md` (lệch chuẩn D-v3-7). Không đổi phạm vi, không đổi policy, không đổi metric.

## 1. Vấn đề

`tools/v3_run.py` buộc lượt eval chạy **đơn tiến trình**: dòng `in_process = run_chain is not None or jobs <= 1 or token is not None`. Token của `seal.unseal` là object trong-tiến-trình và `eval_workflows` xác thực bằng *identity* trên danh sách `_ISSUED` riêng của mỗi process, nên token không băng qua ranh giới process. Vì vậy `--jobs` bị vô hiệu với eval.

Không sửa được mã: tệp Cổng 4 đã ghim `v3_manifest = 9c4c0d018b18…`; sửa `tools/v3_run.py` sẽ đổi digest đó và `seal.reasons` sẽ **từ chối** mọi lượt eval tiếp theo. Cơ chế hoạt động đúng như thiết kế.

Ở một nhân, phần còn lại của lượt 1 (≈108.120 chain trên 133.720) cần khoảng **22 giờ**.

## 2. Việc sẽ làm

Lượt 1 được chạy bằng **sáu lệnh `tools/v3_run.py` riêng, song song, trên các tập block RỜI NHAU**, mỗi lệnh vẫn đơn tiến trình, mỗi lệnh ghi vào thư mục đầu ra riêng:

| Lệnh | Block | Chain |
|---|---|---|
| 1 | `sens:reversible` | 22.400 |
| 2 | `sens:ingress-hidden` | 22.400 |
| 3 | `sens:drift-persistent` | 22.400 |
| 4 | `sens:seed-2` | 22.400 |
| 5 | `h18`, `kd`, `attacker-delta` | 17.040 |
| 6 | `br`, `h18-br`, `kd-br`, `sens-br:*`, `sens-attacker-delta:reversible` | 4.680 |

Block `main` (22.400 chain) **đã chạy xong** trước khai bổ sung này, bằng một lệnh đơn, và số của nó đã được dùng.

## 3. Điều này đổi gì, và KHÔNG đổi gì

**Đổi:** `frozen/v3-unseal-log.jsonl` sẽ có **bảy dòng** thay vì một — một dòng của lệnh `main` đã chạy (2026-09-28T18:10:14Z) và sáu dòng của các lệnh trên. Mọi dòng đều `granted`, `split=eval`, `headline=true`.

**KHÔNG đổi:**

1. **Phạm vi.** Tập hợp các block và ô đúng như D-v3-7 đã khai. Không thêm một ô, một block, một hệ thống nào.
2. **Không có phép nhìn-rồi-quyết.** Sáu lệnh được phóng **trong vòng vài phút, liên tiếp, trước khi bất kỳ kết quả nào của chúng được xem**. Việc chia block là chia theo chi phí tính toán, quyết định trước khi chạy, ghi ở mục 2.

   **Vì sao không phóng đồng thời được (một tính chất của thiết kế, ghi lại để người sau biết).** `seal.unseal` **tự ghi** một dòng vào `frozen/v3-unseal-log.jsonl` ở mỗi lần thử, và điều kiện (e) của Cổng 4 đòi `git status --porcelain` của `auditgame/` phải **rỗng**. Log chưa commit vì vậy làm bẩn cây và **chặn lần unseal kế tiếp**. Nghĩa là thiết kế buộc phải **commit bằng chứng của lần cấp trước mới xin được lần sau** — mỗi lần cấp đều bị ghim vào lịch sử git trước khi có lần tiếp theo. Thủ tục thực tế vì vậy là: commit log → phóng lệnh kế → chờ nó unseal và ghi log → commit → phóng lệnh kế… Sáu lần cấp tương ứng sáu commit liên tiếp của log, mỗi commit ghi lại đúng lần cấp trước nó. Đây là **tuân thủ** cơ chế, không phải lách nó.
3. **Policy bị digest chặn.** Cổng 4 ghim manifest, luật scorecard và bảng dòng 5; nếu bất kỳ thứ nào đổi giữa các lệnh thì `seal.reasons` từ chối. Sáu lệnh vì vậy chạy đúng một policy đã đóng băng.
4. **Kết quả không phụ thuộc cách chia.** Mọi rút ngẫu nhiên đi qua seed keyed (`core.seed_of`); post-mortem của dòng 1 chỉ mang trong cùng `(cell, system, column, seed)`; không có trạng thái chia sẻ giữa các block. Nên số thu được **giống hệt** lượt chạy một lệnh, và điều này **kiểm được**: block `main` đã chạy đơn lệnh và các block khác không đọc gì của nó.
5. **Vẫn là lượt 1.** Lượt 2 (32 ô ngoài tiêu đề) vẫn như D-v3-7 đã khai: đã tiền đăng ký, chưa chạy.

## 4. Điểm yếu phải thừa nhận

Bằng chứng "một lượt" trong log yếu hơn: người đọc không thể chỉ đếm số dòng log để kết luận không có phép nhìn-rồi-quyết, mà phải tin mục 3.2 (sáu lệnh phóng cùng lúc). Bù lại có ba thứ kiểm được độc lập: dấu thời gian của sáu dòng log nằm trong cùng một phút; `run_meta` của mỗi dòng ghi đúng tập block đã khai ở mục 2; và policy bị digest Cổng 4 chặn không cho đổi.

Nếu chọn cách trung thực nhất thì nên chạy một lệnh 22 giờ. Việc chia sáu là **đánh đổi vì thời gian**, do tác giả quyết, khai ở đây.

## 5. Không đổi kết luận đã có

Số headline (Table 2, ô tiêu đề, Δ ∈ {4,8}) đến từ block `main` **đã chạy xong bằng một lệnh đơn trước khai bổ sung này**. Sáu lệnh chỉ thêm: exploitability (`br`), H18/H19 phía eval (`h18`, `kd`), bốn thế giới độ nhạy, và cột attacker-chọn-Δ. Không lệnh nào tính lại số của `main`.

## 6. Thu hẹp lượt 1 xuống `h18` + `kd` (quyết 29/09 ~08:3x, TRƯỚC khi có kết quả của chúng)

Sáu lệnh song song ở mục 2 **không được chạy**. Thay vào đó lượt 1 chỉ chạy thêm **một lệnh: `h18` và `kd`** (13.160 chain, lần cấp thứ hai trong `frozen/v3-unseal-log.jsonl`). Quyết định này được ghi **trước khi lệnh đó cho bất kỳ số nào**.

**Lý do, theo giá trị thêm so với chi phí:**

- `h18` là món giá trị nhất còn lại: nó đưa **H18 — bác Định lý 4 bản in và xác nhận bản đã sửa** — từ bằng chứng *dev* lên *held-out*. Đó là đóng góp mạnh nhất của nghiên cứu.
- `kd` đi kèm rẻ (cùng lệnh) và cho H19.
- `br` bị bỏ: vấn đề của exploitability **không phải thiếu dữ liệu** mà là hai bộ ước lượng lệch chiều theo kiến tạo (V giữ-ngoài là một cực đại nên phồng; V_BR có cross-fit nên nén). Có thêm `br` vẫn không phát biểu được "không thể bị khai thác". Bài báo vì vậy **không báo cáo exploitability**, kèm lý do.
- Bốn thế giới độ nhạy bị bỏ: bằng chứng *dev* đã có (bản đồ chế độ sống ở 5/5 thế giới đọc được) và được dán nhãn **dev** rõ ràng trong bài.
- `attacker-delta` bị bỏ: cột đó **không có bản ghi B1 nào**, nên `V_S − V_B1` không lập được — y như trên dev.

**Hệ quả, ghi theo N3:** trên eval, **không đo** exploitability, bốn thế giới độ nhạy, và cột attacker-chọn-Δ. Không cell nào ghi 0 cho chúng, và **không suy diễn** từ dev sang eval.

**Lượt 2 (32 ô ngoài tiêu đề) cũng được quyết KHÔNG chạy**, vì lưới χ đã khai ({1,04; 1,33; 2,11}) **không tới được ở các giá audit đo thật** (đo được 2,58 / 3,10 / 3,15; `docs/reports/v3-p3-kappa.md`): trục χ thu được sẽ mang các mức không tương ứng nhãn đã khai. H3, H5, H13 vì vậy ghi là **không đo**, kèm lý do này. Nếu về sau chạy lượt 2 thì nó vẫn là lượt đã tiền đăng ký ở D-v3-7 mục 6b, nhưng quyết định hiện tại là không chạy.

## 7. Ba chỗ sai của mục 6, sửa lại theo sự thật đo được (ghi 29/09 ~09:4x, sau khi lệnh lần 3 đã phóng, TRƯỚC khi nó cho số nào)

Mục 6 được viết trước khi chạy và có ba chỗ không khớp với những gì thực sự xảy ra. Sửa ở đây, không sửa tại chỗ, để vết còn nguyên.

**(a) `br` KHÔNG bị bỏ ở mức "không phóng". Nó đã được phóng, và dở dang.**
Mục 6 viết "`br` bị bỏ". Sự thật: lần cấp thứ nhất (`frozen/v3-unseal-log.jsonl` dòng 1, 2026-09-28T18:10:14Z) ghi `blocks: null`, tức **bộ block core mặc định, trong đó có `br`**. Lệnh đó chạy xong `main` lúc 02:00 rồi chạy tiếp sang `br` và bị tác giả kill lúc ~07:56 khi tắt máy. Vì vậy trên đĩa có `spikes/v3-run/eval-pass1/br.jsonl` ≈ 7,8 GB **dở dang**, và thư mục đó **không có** `summary.json` lẫn `records.sha256` (lệnh chưa chạy tới bước chốt).

Hệ quả, ghi theo N3: tệp `br.jsonl` này **không được đọc như kết quả** và **không** đứng sau bất kỳ số nào trong bài. Bài báo vẫn **không báo cáo exploitability**, với đúng lý do đã ghi ở mục 6 (hai bộ ước lượng lệch chiều theo kiến tạo). Điều đổi là cách nói: không phải "chúng tôi không chạy `br`", mà là "`br` chạy dở trong lần cấp 1 và chúng tôi không dùng phần dở đó".

Số headline của `main` không bị ảnh hưởng: `main.jsonl` hoàn tất lúc 02:00, trước khi `br` bắt đầu, và không block nào đọc đầu ra của block khác.

**(b) Số chain của `h18`+`kd` là 16.800, không phải 13.160.**
Mục 6 ghi 13.160. Runner tự in `--headline: 16800 chains at cells chi=1.33 dprime=2.21`. Con số 13.160 là ước lượng của tác giả và sai; 16.800 là số đếm của công cụ. Phạm vi ô không đổi (χ = 1,33; d′ = 2,21; đủ 4 ρ; đủ Δ) — chỉ con số đếm bị ghi sai.

**(c) Lần cấp thứ 3 ghi `systems: null`, không phải danh sách 15 hệ thống.**
Lệnh lần 1 và 2 truyền `--systems` tường minh nên log ghi đủ 15 tên. Lệnh lần 3 (2026-09-29T02:39:40Z, `git_head` 2c282ba) bỏ cờ đó, nên `run_meta.systems` là `null` = **tập mặc định của công cụ**. Tập mặc định đúng bằng 15 tên ở dòng 1 và 2, và điều này kiểm được: chạy lại `tools/v3_run.py` không có `--systems` phải cho đúng 15 hệ thống đó. Không hệ thống nào được thêm hay bỏ. `B7` / `B1-prov` **vẫn ngoài** cả ba lần cấp.

**Vì sao có lần cấp thứ 3.** Lần cấp thứ 2 (2026-09-29T01:10:43Z) là lệnh `h18`+`kd`, bị kill lúc ~08:42 khi tắt máy, để lại `h18.jsonl` / `kd.jsonl` dở (≈ 290 / 274 MB). Hai tệp dở đó **không được đọc**; runner mở tệp đầu ra ở mode `"w"` nên lần 3 ghi đè sạch chúng. Lần 3 chạy **đúng cùng phạm vi** lần 2 — cùng block, cùng seeds, cùng cờ headline, cùng policy bị Gate 4 ghim (`freeze-v3: clean sha256:9c4c0d018b18`). Đây là **chạy lại một lệnh bị gián đoạn**, không phải một lượt mới, và không mở rộng phạm vi.

**Vì sao không có checkpoint/resume.** Tệp Cổng 4 ghim `v3_manifest`, và manifest băm `tools/v3_run.py`. Thêm resume vào tệp đó sẽ đổi digest và `seal.reasons` sẽ **từ chối** mọi lượt eval sau. Tác giả vì vậy chọn chạy lại từ đầu thay vì sửa mã và ký lại cổng — ký lại sau khi đã thấy số eval sẽ phá đúng cái bảo đảm mà cổng dựng ra. Mã resume được viết trên một nhánh **chưa merge** (`v3-run-resume`), chỉ merge sau khi mọi lượt eval dưới cổng hiện tại đã xong.
