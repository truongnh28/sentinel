# Sentinel v3 P3: đo giá audit κ (CPU-phút) của bốn kiểm tra §7

27/09/2026, nhánh `p3-kappa`, tách từ `int-p2`. Số liệu nằm ở `auditgame/reference/v3_kappa_measured.json`. Số thô theo từng lượt nhìn ở `auditgame/spikes/v3-kappa/{django,sympy}.json`. Kiểm tra được hiện thực trong `auditgame/v3/audit_checks.py`, công cụ đo là `auditgame/tools/v3_measure_kappa.py`. **Chưa nối vào `config` hay `budget`**: `config.KAPPA_UNIT` vẫn là bảng của draft (test `test_infra_p3_kappa` khoá điều này).

## Kết luận trước

- **Thứ tự của draft đứng vững, còn tỉ lệ thì không.** Kết quả ở độ sâu 1 là memory ≈ queue < skill < commit, đúng thứ tự draft. Tỉ lệ đo được là 1 : 0,92 : 19,5 : 84,5, trong khi draft ghi 1 : 2,25 : 4 : 10,25. Hai kiểm tra chạy test (delegation và commit) đắt hơn hai kiểm tra chỉ đọc repo từ một tới hai bậc độ lớn.
- **Thang tuyệt đối nhỏ hơn draft rất nhiều.** Commit tốn 0,075 CPU-phút, draft ghi 4,1. Insertion tốn 0,0009, draft ghi 0,4. Lý do: test chạy trong venv dựng sẵn, không Docker, và checkout không tính vào κ. χ không phụ thuộc thang đo, nên điều này không đổi χ. Nó chỉ đổi con số in trong Table 1.
- **χ đo được cao hơn mọi mức của lưới C16, và ba cấu hình độ sâu gần như trùng nhau.** Theo range/κ̄: (3,3,2,1) cho 2,58, (3,2,1,1) cho 3,10, (1,1,1,1) cho 3,15. Theo 2·MAD/κ̄: 1,88; 2,15; 2,19. CI của hai ô "1.33" và "2.11" chồng lên nhau gần hết. Nếu thay giá đo được vào, lưới χ {1,04; 1,33; 2,11} không còn dựng được: 81 cấu hình độ sâu chỉ phủ \[2,25; 3,70\] theo range và \[1,88; 2,72\] theo MAD.

## Bốn kiểm tra đã hiện thực (draft §7)

Mỗi task của dev (một instance SWE-bench trong corpus v2) được dựng thành bốn bản ghi. Đây là bước setup, không tính giờ, và không bản ghi nào mang nhãn.

| Mục tiêu → giai đoạn | §7 nói | Việc làm thật trên repo tại `base_commit` |
| --- | --- | --- |
| memory → insertion | content and provenance check on new memory records | Với mỗi nguồn ghi chú trích: đọc blob và băm lại, so với blob id đã trích. Parse AST để kiểm mọi hàm mà ghi chú nhắc tới có được định nghĩa trong nguồn không. Quét văn bản tìm dạng chỉ thị |
| queue → retrieval | consistency check of retrieved records against sources | Tìm lại nguyên văn các dòng pre-image mà lời gọi treo trích, trong nguồn tại base. Băm lại blob. Mọi test mà lời gọi nêu phải có trong file test (ở base hoặc do test patch thêm vào) |
| skill → delegation | contract and evidence check | Contract: áp patch của skill, so chữ ký các hàm nó sửa trước và sau khi áp. Evidence: áp test patch và **chạy** các test FAIL_TO_PASS mà skill dẫn làm bằng chứng |
| commit → commit | patch review, differential testing, provenance of contributing skills | Review: `git apply --check`, biên dịch lại file đã đổi, đếm kích thước diff. Differential testing: áp test patch, **chạy trọn các module test bị chạm** trên cây trước patch và sau patch, so kết quả từng test. Provenance: băm lại nguồn của mọi skill mà workflow đã cache trước task này |

**Độ sâu.** Theo `observe.sweep_dprime` (d′√d), độ sâu d là d lượt nhìn độc lập. Một audit độ sâu d là kiểm tra chạy trên d bản ghi gần nhất của mục tiêu, tức task t, t−1, …, t−d+1. κ(k, d) của một workflow là tổng d lượt nhìn đầu. Tuyến tính theo d (Q6) vì vậy là kết quả đo, không phải giả định. Commit cũng được đo ở d = 1–3 theo cùng định nghĩa (xét lại d commit gần nhất), nhưng mọi ô χ đều đặt commit ở độ sâu 1.

## Mẫu và cách đo (khai trước khi đo)

- **Chỉ dev.** `corpus.dev_workflows()`. Công cụ từ chối workflow nào không phải id v2 (`_dev_only`). Tập eval không được dựng.
- **Họ repo.** Chỉ đo các họ có bộ test chạy được từ venv thường, không cần phần mở rộng biên dịch hay image Docker từng instance: django (43/100 workflow dev) và sympy (15/100). Các họ không đo được liệt kê kèm lý do trong JSON (`families_not_measured`).
- **Workflow.** Lấy 8 django và 5 sympy, rút bằng `random.Random(seed_of("v3-kappa", họ))` trên danh sách id đã sắp. Audit ở task t = 3, nên mỗi workflow cho 3 lượt nhìn mỗi mục tiêu: tổng 39 lượt nhìn × 4 kiểm tra.
- **Lặp.** Mỗi lượt nhìn đo 3 lần, lấy trung vị.
- **Đồng hồ.** `process_time` cộng `RUSAGE_CHILDREN` (user+sys, gồm cả git và tiến trình test). Checkout và reset cây làm việc là setup, không tính vào κ. Trung vị một lần reset là 0,0051 CPU-phút.
- **Môi trường.** Python 3.9 (django < 5.0 và sympy; SWE-bench cũng chạy sympy trên 3.9), Python 3.11 cho django 5.0. Test chạy tại `base_commit`, `--parallel 1`.
- **CI 95%.** Tính trên workflow, bootstrap B = 10.000 có seed. Khoảng t in kèm trong JSON.
- **Loại.** 2 lượt nhìn delegation bị loại vì không test bằng chứng nào chạy (django-11141, django-15280), nên không đo được evidence. Hai workflow này mất các độ sâu có chứa lượt đó (skill d = 2 còn n = 12, d = 3 còn n = 11).

## κ đo được so với bảng draft (CPU-phút, gộp 13 workflow)

| Mục tiêu (giai đoạn) | Draft §7 | d = 1 | CI 95% | d = 2 | d = 3 | κ(d) / (d·κ(1)) ở d = 3 |
| --- | --- | --- | --- | --- | --- | --- |
| memory (insertion) | 0,4 | 0,00089 | \[0,00029; 0,00203\] | 0,00125 | 0,00156 | 0,58 |
| queue (retrieval) | 0,9 | 0,00082 | \[0,00044; 0,00154\] | 0,00129 | 0,00174 | 0,71 |
| skill (delegation) | 1,6 | 0,0174 | \[0,0141; 0,0213\] | 0,0355 | 0,0524 | 1,00 |
| commit | 4,1 | 0,0752 | \[0,0406; 0,1281\] | 0,1701 | 0,2504 | 1,11 |

Tách theo họ (d = 1, CPU-phút):

| Họ | memory | queue | skill | commit |
| --- | --- | --- | --- | --- |
| django (8) | 0,00036 | 0,00045 | 0,0131 | 0,0315 |
| sympy (5) | 0,00174 | 0,00141 | 0,0242 | 0,1450 |

Theo giây, trung vị một lượt nhìn là: insertion 0,018 s, retrieval 0,026 s, delegation 0,96 s, commit 2,46 s.

Cách đọc:
- **Hai kiểm tra đọc repo gần như miễn phí so với hai kiểm tra chạy test.** Insertion và retrieval chỉ là vài lần `git cat-file` cộng một lần parse AST. Delegation chạy vài test. Commit chạy trọn module test hai lần.
- **Trung bình của memory và queue ở d = 1 bị kéo lên bởi lượt nhìn đầu tiên đọc repo nguội.** Lượt đầu của sympy-13091 tốn 0,46 s, gấp khoảng 25 lần trung vị, vì git phải nạp chỉ mục pack lần đầu. Vì thế κ(d)/(d·κ(1)) của hai mục tiêu này dưới 1 (0,58 và 0,71): phần chi phí cố định dồn cả vào lượt đầu. Delegation và commit tuyến tính (1,00 và 1,11), nên giả định Q6 "giá tuyến tính theo độ sâu" đúng với hai kiểm tra đắt.
- **Commit có đuôi nặng.** django-16612 tốn 25,8 s, trong khi trung vị là 2,5 s: module test bị chạm to hơn hẳn. CI của commit vì vậy rộng (hệ số khoảng 3 giữa hai đầu).

## χ theo ba cấu hình độ sâu (memory, queue, skill, commit)

κ của từng mục tiêu lấy ở độ sâu của ô, đo trực tiếp chứ không nhân tuyến tính. CI là bootstrap cặp theo workflow: một lần rút lại di chuyển cả bốn mục tiêu cùng lúc.

| Ô χ (nhãn C16) | Độ sâu | χ range/κ̄: draft → đo (CI 95%) | χ 2·MAD/κ̄: draft → đo (CI 95%) |
| --- | --- | --- | --- |
| "1.04" | (3,3,2,1) | 1,036 → **2,58** \[2,17; 3,02\] | 0,607 → **1,88** \[1,78; 2,05\] |
| "1.33" (chính) | (3,2,1,1) | 1,333 → **3,10** \[2,74; 3,39\] | 0,885 → **2,15** \[1,85; 2,42\] |
| "2.11" | (1,1,1,1) | 2,114 → **3,15** \[2,81; 3,43\] | 1,343 → **2,19** \[1,89; 2,44\] |

Nếu nhân tuyến tính κ(1)·d thay vì đo trực tiếp, kết quả gần như không đổi: 2,53 / 3,04 / 3,15 theo range. Cũng với giá đo, dải χ đạt được qua cả 81 cấu hình độ sâu {1,2,3}⁴ là \[2,25; 3,70\] theo range (thấp nhất ở (3,3,3,1), cao nhất ở (1,1,1,3)) và \[1,88; 2,72\] theo MAD.

Cách đọc:
- Với giá của draft, độ sâu kéo χ đi được xa, từ 1,04 tới 2,11. Với giá đo, commit đắt gấp khoảng 4 lần skill và gấp 84–92 lần memory hay queue. Tăng độ sâu của ba mục tiêu rẻ chỉ bớt được một phần nhỏ khoảng cách đó. Vì vậy χ chỉ còn dao động giữa 2,58 và 3,15.
- Hai ô "1.33" và "2.11" chỉ còn cách nhau 0,06 theo range, CI chồng gần hết. Trục χ của lưới thực chất còn hai mức, không phải ba.
- Mức 1,34 của draft (đọc theo MAD) nằm ngoài mọi cấu hình đạt được. Mức thấp nhất đạt được là 1,88.

## Nếu nối số đo vào `config` / `budget` thì cái gì đổi (chưa làm)

1. **`config.KAPPA_UNIT`** sẽ đổi từ 0,4 / 0,9 / 1,6 / 4,1 sang 0,00089 / 0,00082 / 0,0174 / 0,0752. Tốt hơn nữa là dùng thẳng bảng κ(k, d) đo được, vì memory và queue không tuyến tính theo độ sâu.
2. **`CHI_DEPTHS` và nhãn ô.** Ba nhãn "1.04 / 1.33 / 2.11" sẽ thành khoảng 2.58 / 3.10 / 3.15. Phương án (a) của C16 ("dùng các mức đạt được") phải chọn lại. Chỉ còn hai mức phân biệt được, ví dụ (3,3,3,1) ≈ 2,25 và (1,1,1,3) ≈ 3,70. Nếu vẫn giữ commit ở độ sâu 1 cho B1, mức cao nhất là 3,15. Đây là quyết định cần thầy ký, cùng với C16.
3. **Dòng "Độ sâu commit của B1".** Câu "χ ≤ 2,11 chỉ đạt được khi commit không ở độ sâu 3" không còn cơ sở, vì không cấu hình nào xuống dưới 2,25. Lý do để commit ở độ sâu 1 phải viết lại.
4. **Ngân sách (`v3/budget.py`).** b1 = H·max κ vẫn là H·κ_commit, nhưng bằng 0,075·H CPU-phút thay vì 4,1·H. B_min của Định lý 5.6, tức ⌊(H−1)/Δ⌋·Σκ_k n_k, đổi theo tỉ lệ giữa các mục tiêu: phần của commit chiếm 79% Σκ ở cấu hình chính, thay vì 47% với giá draft. Các mức b2–b4 (bội số của B_min) đổi theo, nhưng tỉ số B/B_min thì giữ nguyên.
5. **Arm "χ chỉ đổi giá" (`price_only_kappa`).** Arm này co giá quanh κ̄ để χ_range bằng χ của ô độ sâu. Với số đo, mục tiêu cho "2.11" (3,15) chỉ cách ô chính (3,10) khoảng 2% (λ ≈ 1,02), nên arm này gần như trùng ô chính. Mục tiêu cho "1.04" cần λ ≈ 0,83.
6. **Dự phóng P0 của mô hình phủ và phân bổ theo giá của Sentinel.** Hai phần này đọc tỉ lệ κ giữa các carrier. Commit đắt tương đối hơn nhiều (84× thay vì 10× memory), nên các policy tối ưu theo giá sẽ càng tránh commit. Cần chạy lại dự phóng (`theory/checks/v3_projection.py`) trước Cổng 4 nếu nối số này.
7. **Table 1 / D7.kappa.** In số đo cạnh số draft. Ghi erratum rằng χ = 1,34 của §7 không khớp với chính công thức §4 (C3), và với giá đo, χ theo §4 là 3,15 ở độ sâu đều.

## Giới hạn

- **Chỉ hai họ Python.** django và sympy chiếm 58/100 workflow dev. Các họ cần phần mở rộng biên dịch (sklearn, matplotlib, astropy), cần ghim phiên bản theo instance (sphinx, xarray), hoặc không phải Python thì chưa đo. Commit của các họ nặng hơn (ví dụ sklearn) có thể còn đắt hơn nữa, tức χ còn cao hơn.
- **Thang tuyệt đối phụ thuộc hiện thực.** Không Docker, venv dựng sẵn, checkout không tính. Draft §10 đã nói trước điều này: "an organisation with different check implementations would have different χ". Chỉ tỉ lệ và χ mới mang sang được.
- **Tỉ lệ memory/queue là cận dưới về độ đắt.** Hai kiểm tra này không gọi detector học. Nếu insertion có chấm điểm bằng mô hình học (P3, sau khi có detector đọc nội dung), κ_memory sẽ tăng và χ sẽ giảm. Phải đo lại khi detector đó có.
- **Provenance của skill đóng góp** được đọc theo cách rộng nhất: mọi skill đã cache trước task, vì trace không ghi agent dùng skill nào. Phần này rẻ (vài lần `cat-file`) nên gần như không đổi κ_commit.

## Tái lập

```
cd auditgame
# repo sao chép và venv ở workspace/kappa/ (gitignored): django, sympy, env-dj39, env-dj311, env-sy39
../.venv/bin/python tools/v3_measure_kappa.py run --family django
../.venv/bin/python tools/v3_measure_kappa.py run --family sympy
../.venv/bin/python tools/v3_measure_kappa.py summarise
```
