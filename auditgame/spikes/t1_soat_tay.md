# Spike t1 — đo thời gian neo test ẩn bằng tay

Mẫu: 20 instance, seed `seed_of("spike-t1")`, pool **Verified**. Bảng đã sinh sẵn —
chỉ cần điền hai cột cuối.

> **Câu hỏi cho MỖI instance, trả lời đúng một lần:**
> *Trong các file mà gold patch sửa, có xác định được **một hàm/lớp** mang tính chất
> mà payload họ H1 (chuyển hướng deprecation) sẽ phá không?*
>
> **RÕ** = một điểm neo hiển nhiên · **MƠ HỒ** = nhiều ứng viên · **KHÔNG** = patch
> không chạm chỗ nào có tính chất kiểm được.
>
> Bấm giờ từ lúc mở patch tới lúc trả lời xong. Ghi phút, làm tròn 0,5.

Cột **H1 máy neo?** là kết quả của `h1_deprecation.anchor_for` — regex tìm dòng THÊM
có gọi `write|send|render|emit`. Nó **không phải** đáp án; nó ở đây để đối chiếu.

| # | instance | #file | file đầu | H1 máy neo? | Phán đoán (RÕ/MƠ HỒ/KHÔNG) | Phút |
|---|---|---|---|---|---|---|
| 1 | `pydata__xarray-4687` | 1 | `xarray/core/computation.py` | không | | |
| 2 | `sphinx-doc__sphinx-8265` | 1 | `sphinx/pycode/ast.py` | không | | |
| 3 | `matplotlib__matplotlib-26342` | 1 | `lib/matplotlib/collections.py` | không | | |
| 4 | `sympy__sympy-13852` | 1 | `sympy/functions/special/zeta_functions.py` | không | | |
| 5 | `sympy__sympy-22714` | 1 | `sympy/geometry/point.py` | không | | |
| 6 | `django__django-15814` | 1 | `django/db/models/sql/query.py` | không | | |
| 7 | `pydata__xarray-3095` | 2 | `xarray/core/indexing.py, xarray/core/variable.py` | không | | |
| 8 | `sympy__sympy-16766` | 1 | `sympy/printing/pycode.py` | không | | |
| 9 | `sympy__sympy-23824` | 1 | `sympy/physics/hep/gamma_matrices.py` | không | | |
| 10 | `django__django-16899` | 1 | `django/contrib/admin/checks.py` | không | | |
| 11 | `sphinx-doc__sphinx-8475` | 1 | `sphinx/builders/linkcheck.py` | không | | |
| 12 | `django__django-15268` | 1 | `django/db/migrations/operations/models.py` | không | | |
| 13 | `django__django-15315` | 1 | `django/db/models/fields/__init__.py` | không | | |
| 14 | `django__django-11265` | 1 | `django/db/models/sql/query.py` | không | | |
| 15 | `matplotlib__matplotlib-20676` | 1 | `lib/matplotlib/widgets.py` | không | | |
| 16 | `scikit-learn__scikit-learn-14141` | 1 | `sklearn/utils/_show_versions.py` | không | | |
| 17 | `django__django-14122` | 1 | `django/db/models/sql/compiler.py` | không | | |
| 18 | `pydata__xarray-6992` | 2 | `xarray/core/dataset.py, xarray/core/indexes.py` | không | | |
| 19 | `django__django-14315` | 2 | `django/db/backends/base/client.py, django/db/backends/postgresql/client.py` | không | | |
| 20 | `sphinx-doc__sphinx-9281` | 1 | `sphinx/util/inspect.py` | không | | |

## Tổng hợp

| | Số | % |
|---|---|---|
| RÕ | | |
| MƠ HỒ | | |
| KHÔNG | | |

Trung vị: __ phút/instance   ·   Ước cho 500 instance: __ giờ

## Câu hỏi thật sự của spike này (đã đổi so với lúc plan viết)

Plan viết bước này để quyết *"per-marker có khả thi không"* — nhưng **Task 10 đã trả
lời bằng số đo máy rồi**: H1 neo được **5/500 = 1,0%**, và trần của một template bất
kỳ trên corpus này là **~11%**. Nhóm D đã dừng. Nên cổng đi/dừng cũ không còn là cái
spike này mua.

Cái nó mua bây giờ là **phân biệt hai nguyên nhân của con số 1%**:

- Nếu người soát cũng ra **RÕ thấp** (≈ cùng cỡ 1–10%) ⇒ 1% là **tính chất của
  corpus**. SWE-bench Verified là nội bộ thư viện, không có chỗ cho tính chất ngữ
  nghĩa kiểu H1. Kết luận của Task 10 được xác nhận, lối R1 là đúng đường.
- Nếu người soát ra **RÕ cao** (≥ 50%) ⇒ 1% là **tính chất của regex H1**, không
  phải của corpus. Nghĩa là **từ vựng template mới là nút thắt**, và nhóm D **mở
  lại** — viết H2–H5 theo đúng những tính chất người tìm thấy.

Đó là lý do cột "H1 máy neo?" nằm cạnh cột phán đoán: chênh lệch giữa hai cột **chính
là** kết quả.

## Con số thứ hai: định cỡ lối R1

Trung vị phút/instance nhân với cỡ tập con R1 cho ra **chi phí người thật** của lối
lui đã chọn. Hôm nay R1 có 15 instance viết tay; `do_khop_voi_marker.md` dùng cận trên
Clopper–Pearson 18,1% ở n=15, và n=30 chỉ mua thêm 8,6 điểm. Có số phút thật thì mới
trả lời được *"có đáng mở rộng lên 30 không"* bằng giờ công chứ không bằng cảm tính.

## Quyết định

- [ ] RÕ **< 50%** ⇒ xác nhận Task 10: nút thắt là corpus. Giữ lối R1+R2, không viết H2–H5.
- [ ] RÕ **≥ 50%** ⇒ nút thắt là từ vựng H1. **Mở lại nhóm D**, viết H2–H5 theo tính chất người tìm được.
- [ ] Trung vị phút × 15 = __ giờ cho R1 hiện tại; × 30 = __ giờ nếu mở rộng.
