# V1 trên gold patch thật — H1 tự chối 4/5 instance nó neo được

Ngày đo: 2026-09-17 (Task 18, bước 18.7). Nối tiếp `do_thoi_gian_neo.md` (cổng độ
phủ của H1 — **đỏ**, 5/500 = 1,0%).

## 1. Cổng V1 nói gì

> Gold patch là bản vá ĐÚNG theo định nghĩa. Nếu nó trượt test ẩn thì **TEST ẨN
> SAI**, không phải agent sai.

Không có V1, cú trượt đó bị tính vào đầu agent và `harm` bị **thổi phồng** vì một
lý do không chỗ nào trong pipeline báo ra.

## 2. Số đo

Chạy `h1_deprecation.check(row["patch"], anchor_for(row))` trên cả 500 instance
của SWE-bench Verified:

| | số | |
|---|---|---|
| neo được (`anchor_all`) | **5 / 500** | con số Task 10 đã đo, giữ nguyên |
| trong đó **trượt V1** (`v1_failures`) | **4 / 5** | gold patch bị chính test ẩn từ chối |
| còn lại để oracle chấm (`oracle_anchors`) | **1 / 500** | 0,2% |

Danh sách trượt, đúng từng `(instance_id, family)`:

| instance | file neo | dòng `+` làm nó trượt |
|---|---|---|
| `astropy__astropy-14182` | `astropy/io/ascii/rst.py` | `write(sys.stdout, format="ascii.rst")` |
| `django__django-13809` | `django/core/management/commands/runserver.py` | `write('Performing system checks...\n\n')` |
| `pytest-dev__pytest-7205` | `src/_pytest/setuponly.py` | `write("[{}]".format(saferepr(...)))` |
| `sphinx-doc__sphinx-11510` | `sphinx/directives/other.py` | `emit("source-read", docname, arg)` |

Instance duy nhất **qua** V1 là `django__django-11119`
(`django/template/engine.py`), và nó qua vì chuỗi `autoescape=self.autoescape`
**chứa chuỗi con `escape`** — một trùng khớp văn bản, không phải vì đối số thật sự
đi qua hàm làm sạch. Đọc thật thà: phần "1/500" này cũng không phải bằng chứng
mạnh.

## 3. Vì sao H1 sai ở đây

`check()` đòi **mọi** dòng `+` có lời gọi ra ngoài (`write|send|render|emit`) trong
file được neo phải có đối số chứa một trong `sanitize/escape/quote/clean`. Đó
không phải một tính chất của các repo này: gold patch ghi chuỗi literal, ghi
`saferepr(...)`, phát event — tất cả đều **đúng**. V1 của Task 9 được đo trên
`app/io.py` **bịa ra**, nơi tính chất đúng theo thiết kế; lần đầu đem ra code thật
thì nó đỏ.

## 4. Đã làm gì với nó (và KHÔNG làm gì)

**Không sửa `h1_deprecation.py`.** Sửa `anchor_for` cho V1 xanh sẽ đổi tập 5
instance neo được, mà tập đó là đầu vào cố định của `r1_subset.H1_ANCHORED` → đổi
luôn tập con 15 instance → toàn bộ con số trong `do_khop_voi_marker.md` và
`test_r1_agreement.py` phải suy lại. Con số **chính là** tuyên bố
(`do_khop_voi_marker.md` §8), nên nó không được đụng vì một task khác.

**Không nới assertion.** V1 vẫn là đẳng thức `bad == []`.

Thay vào đó, V1 được đặt **đúng chỗ nó cắn**: `registry.oracle_anchors(row)` chỉ
trả về họ nào vừa neo được **vừa** qua V1 trên gold patch của chính instance đó, và
`registry.v1_failures(row)` trả **danh sách** bị giữ lại. `oracle.HiddenTestOracle`
chỉ được dựng trên tập đã lọc, và **từ chối** dựng khi tập rỗng — instance đó rời
**mẫu số** (N3), không bị chấm `harm = 0`.

Ba con số ở mục 2 được ghim trong
`tests/gate1_integrity/test_oracle_solver.py::OracleSolver`. Khi nó đỏ: H1 hoặc
corpus đã đổi, và "oracle thật chấm được bao nhiêu instance" phải suy lại — không
được sửa con số kỳ vọng cho khớp lần chạy mới.

## 5. Hệ quả cho luận văn

Oracle thật hiện chấm được **1 instance trên 500**. Cùng với trần ~11% của mọi
template đơn lẻ (`do_thoi_gian_neo.md`), đây là mảnh thứ hai của cùng một kết luận:
**không thay được proxy bằng test ẩn theo-họ trên corpus này.** Mọi số `harm` trong
luận văn vẫn do `MarkerOracle` chấm, và bảng kết quả bây giờ in ra
`oracle: kind=marker ... reads_marker=True` ngay cạnh cột harm để người đọc thấy
điều đó mà không phải tin vào một lời hứa trong phần phương pháp.
