# Tổ chức lại cấu trúc Sentinel — thiết kế

**Ngày:** 20/09/2026
**Phạm vi:** cấu trúc thư mục, ranh giới package, phân giải đường dẫn. **Không** đụng tới nội dung khoa học, không sửa test đỏ, không chẻ file lớn.
**Trạng thái cây mã lúc viết:** 34 module gốc trong `auditgame/`, ~13.5k LOC, 238 file tracked.

---

## 1. Vì sao làm

Năm vấn đề đo được, không phải cảm tính:

1. **`auditgame/` không phải package** (thiếu `__init__.py`) nhưng `analysis/`, `tests/`, `hidden_tests/`, `payloads/` bên trong lại là package. Mọi thứ chạy kiểu script `import core`, buộc CWD phải đúng bằng `auditgame/`. Hệ quả: 4 chỗ `sys.path.insert` vá tay trong `tools/` và `spikes/`.

2. **34 module phẳng trộn 6 nhóm trách nhiệm.** `core.py` có fan-in 20. Thêm một policy hay một attacker mới phải đọc cả thư mục mới biết đặt vào đâu.

3. **Ba vòng lặp import** đang được vá bằng lazy import trong thân hàm:
   - `core.py:14 import retrieval` (mức module) ↔ `retrieval.py:265 import core` (trong hàm)
   - `core.py:613` ↔ `sealed_trace.py:218` (cả hai đều hoãn)
   - `swebench_dataset.py:34` (mức module) ↔ `datasets.py:105` (trong hàm)

   Vòng lặp thứ nhất nghĩa là tầng nền móng đang phụ thuộc vào tầng dữ liệu.

4. **46 chỗ neo đường dẫn bằng `__file__`** (ảnh chụp 20/09 — con số này trôi theo mỗi commit), mỗi chỗ tự suy ra vị trí của mình. `scoring.py:32` → `parent/"reference"/"score_table.json"`; `swebench_dataset.py:36` → `parent/"data"`; `tests/gate1_integrity/test_environment.py:46` → `parents[3]/"requirements.lock"`. Chúng gãy **âm thầm**: sai đường dẫn không gây `ImportError` mà gây `FileNotFoundError` ở tận nơi khác, hoặc rơi vào nhánh fallback rồi cho ra số sai.

5. **Chính sách ignore nằm ngoài project.** `.gitignore` của vault có 15 luật gắn cứng tiền tố `HCMUT/code/Sentinel/...` (dòng 67–138). Dời bất kỳ thư mục nào cũng vô hiệu hoá luật tương ứng — dời `auditgame/data/` làm gãy dòng 82 và 51MB `.jsonl` bỗng commit được.

## 2. Ràng buộc

- **Clone-and-run phải giữ.** Dockerfile và README dựng trên nguyên tắc lõi đo lường chỉ dùng stdlib. Vì vậy **không dùng layout `src/`** — nó bắt buộc `pip install -e .` mới chạy được.
- **Không có baseline xanh.** Gate 1: 538/551 với 13 skip (chưa build image `auditgame:latest`) → runner tự tuyên bố UNKNOWN. Gate 2: 203/205, 2 đỏ. Gate 3: chưa từng chạy vì runner dừng ở gate đỏ đầu tiên.
- **Hai test đỏ ở gate 2 nằm ngoài phạm vi.** Chúng là phát hiện khoa học (không epsilon nào chạm trần; corpus đã đủ mạnh khiến tiêu chí multi-split thành vô dụng), không phải lỗi cấu trúc.
- **Output `.json`/`.jsonl` của spikes là dữ liệu đã trả tiền, không tái lập được** (commit `8c68096`: *"paid, unreproducible"*). Chúng chỉ đổi chỗ, giữ nguyên quy chế tracked.
- **Cây mã đang thay đổi.** Trong phiên review này, module gốc đi từ 31 → 34 (`costs.py`, `detector_llm.py` mới, cả hai fan-in = fan-out = 0, tức chưa nối vào đâu; `prose_world.py` đã được `agent` và `build` dùng).

## 3. Layout đích

```
Sentinel/
├── .gitignore              MỚI — luật tương đối, thay 15 luật trong vault
├── pyproject.toml          MỚI — chỉ để `pip install -e .` tuỳ chọn cho tools/
├── README.md               MỚI — gom từ auditgame/README.md, là cửa vào
├── Dockerfile
│
├── auditgame/              package thật (có __init__.py)
│   ├── paths.py            MỚI — nguồn chân lý duy nhất cho mọi đường dẫn
│   ├── core/               core · sealed_trace · carrier_store_fs · scoring · costs
│   ├── data/               datasets · swebench_dataset · swebench_fetch · topics · retrieval · prose_world
│   ├── agent/              agent · agents · agent_llm · llms · harness
│   ├── audit/              detector · detector_llm · oracle · policies · lp · runner
│   ├── attack/             attacks · attackers · fdetect · fdetect_g4
│   ├── study/              experiment · m3 · replay · game · metrics · theory · dprime_sweep
│   │                       + p2_run · p2_arms · p2_budget (thăng cấp từ spikes)
│   ├── analysis/           giữ nguyên
│   ├── hidden_tests/       giữ nguyên
│   ├── payloads/           giữ nguyên + gen_attacker_llm_a1a2 (thăng cấp từ spikes)
│   └── reference/          score_table.json — bảng tra kề mã, không phải output
│
├── tests/                  lên gốc, giữ nguyên 3 gate bên trong
├── spikes/                 chỉ còn .py mồ côi
├── tools/                  gộp tools/ + scripts/
├── docs/
│   ├── preregistration/    17 .md được code trích dẫn — BẤT BIẾN, chỉ append
│   ├── reports/            20 .md báo cáo nghiên cứu
│   ├── guides/             4 file HUONG-DAN-*.md
│   └── design/             gộp HAI cây superpowers (specs + plans)
├── datasets/               từ auditgame/data/ — 51MB input, gitignored
├── results/spikes/         45 file output, VẪN TRACKED
└── var/                    carriers/ · carriers-sealed/ · run_b1.json — gitignored
```

### 3.1 Quy tắc ánh xạ module → subpackage

Cây mã đang chuyển động, nên ánh xạ được định nghĩa **theo quy tắc**, và danh sách ở §3 chỉ là ảnh chụp ngày 20/09. Khi thực thi, chạy lại phép đo fan-in/fan-out rồi áp quy tắc:

| Subpackage | Quy tắc |
|---|---|
| `core/` | Kiểu dữ liệu nền và lưu trữ, fan-out nội bộ = 0 hoặc chỉ phụ thuộc `core` |
| `data/` | Chạm tới dataset SWE-bench, corpus, hoặc topic |
| `agent/` | Cài đặt giao diện `Agent`, hoặc gọi LLM thay mặt agent |
| `audit/` | Cài đặt detector, oracle, policy, hoặc vòng chạy ghép cặp |
| `attack/` | Sinh hoặc mô hình hoá hành vi attacker |
| `study/` | fan-in = 0 và có khối `__main__` — tức là lá, là nơi chạy thí nghiệm |

Module chưa nối vào đâu (fan-in = fan-out = 0, như `costs.py` và `detector_llm.py` hiện nay) xếp theo tên miền chứ không theo đồ thị, và ghi chú lại trong commit.

### 3.2 Việc phân tầng giải luôn ba vòng lặp

Đẩy `retrieval` xuống `data/` và `sealed_trace` vào `core/` làm cạnh `core → retrieval` mức module thành cạnh hướng xuống hợp lệ. Sau khi dời, ba lazy import trong thân hàm được nâng lên đầu file. **Nếu không nâng được thì việc phân tầng đã sai** — đây là phép thử tự kiểm của thiết kế, không phải việc dọn dẹp tuỳ chọn.

### 3.3 `paths.py` — lưới an toàn

Đây là phần quan trọng nhất, không phải phần phụ.

```python
# auditgame/paths.py
ROOT      = pathlib.Path(__file__).resolve().parent   # auditgame/
PROJECT   = ROOT.parent                               # Sentinel/
DATASETS  = PROJECT / "datasets"
RESULTS   = PROJECT / "results"
VAR       = PROJECT / "var"
REFERENCE = ROOT / "reference"
DOCS      = PROJECT / "docs"
LOCK      = PROJECT / "requirements.lock"
```

`paths.py` **khẳng định ngay lúc import** rằng mọi đường dẫn khai báo đều tồn tại, và báo lỗi nêu đích danh cái nào thiếu. Điều này biến cả một lớp lỗi âm thầm thành lỗi ồn ào tại dòng đầu tiên — chính là thứ khiến giai đoạn 5 an toàn.

Đúng **một** chỗ neo `__file__` cho toàn bộ package. Mọi chỗ còn lại import từ đây.

## 4. Tiêu chí đúng/sai

**Không phải "mọi thứ xanh".** Mà là:

> Tập kết quả từng test (pass / fail / skip, theo test ID) sau khi dời phải **giống hệt** trước khi dời.

Hai test đỏ ở gate 2 phải vẫn đỏ với đúng thông điệp cũ. Một test đỏ chuyển xanh cũng là dấu hiệu sai, ngang với xanh chuyển đỏ.

Baseline chụp bằng `python3 tests/run_all.py --all` để ép cả ba gate chạy, lưu ra file ngoài cây mã.

## 5. Bảy giai đoạn

Mỗi giai đoạn một commit, kiểm chứng độc lập.

| # | Việc | Rủi ro | Xác nhận |
|---|---|---|---|
| 0 | Chụp baseline `--all`; thêm `.gitignore` nội bộ cho `Sentinel/`, gỡ 15 luật khỏi vault | — | `git status` sạch y như trước |
| 1 | **`paths.py`** thay toàn bộ chỗ neo (46 lúc viết). **Không dời file nào.** | Thấp | Khớp baseline từng dòng |
| 2 | Xoá `smoke_repro.py.bak`, `hidden_suites/` rỗng, `__pycache__` | Rất thấp | Khớp baseline |
| 3 | Dời `.md` → `docs/{preregistration,reports,guides,design}`; output → `results/spikes/`; sửa 30 file trích dẫn | Thấp | `grep -rn 'spikes/.*\.md'` ra rỗng; khớp baseline |
| 4 | Thăng cấp 4 `.py` còn sống; xoá `from spikes import p2_run` | Trung bình | Khớp baseline |
| 5 | **Gói 6 subpackage**, `__init__.py`, sửa import, nâng 3 lazy import lên đầu file | **Cao** | Khớp baseline |
| 6 | `tests/`+`spikes/` lên gốc, gộp `tools/`+`scripts/`, `pyproject.toml`, `README.md` | Trung bình | Khớp baseline; sửa `top_level_dir` trong `run_all.py` |

**Giai đoạn 1 là điều kiện tiên quyết của giai đoạn 5.** Làm ngược lại thì lỗi đường dẫn và lỗi import nổ cùng lúc, không tách được nguyên nhân.

Giai đoạn 0 phải xong **trước** mọi lần dời file, vì luật ignore gắn cứng đường dẫn cũ.

## 6. Phân loại `spikes/` (92 file, ảnh chụp 20/09)

| Nhóm | Số | Đi đâu |
|---|---|---|
| `.md` được code trích dẫn | 17 | `docs/preregistration/` |
| `.md` không ai trích dẫn | 20 | `docs/reports/` |
| `.py` được test/code ngoài spikes import | 4 | `auditgame/study/` (p2_run, p2_arms, p2_budget) · `auditgame/payloads/` (gen_attacker_llm_a1a2) |
| `.py` mồ côi | 8 | ở lại `spikes/` |
| output `.json` / `.jsonl` | 45 | `results/spikes/`, giữ tracked |

**17 file tiền đăng ký:** `cong-v2.md` (10 nơi trỏ tới), `chot_theta.md` (5), `do_khop_voi_marker.md` (4), `do_thoi_gian_neo.md` (3), `ho-tan-cong-mo-rong.md`, `eps-ngan-sach-that.md`, `b5-auc.md`, `V1-failures.md`, `M3.md` (2 mỗi file), và `tau-sel-follows-dprime.md`, `sweep-loss-v2.md`, `sweep-loss-b5-b6.md`, `p2-ngan-sach-loi-khuyen.md`, `dprime-sweep.md`, `dai-theo-n.md`, `cong-v2-chot.md`, `b5-benign-enrich.md` (1 mỗi file).

Dời chúng **không làm mất tính tiền đăng ký**: git theo nội dung, nên `git log --follow` vẫn chứng minh được file được commit trước dữ liệu nó ràng buộc.

Wikilink Obsidian an toàn: chỉ 12 wikilink, đều trỏ ra ngoài vào note của vault, và Obsidian phân giải theo tên file chứ không theo đường dẫn.

## 7. Không làm

- Không chẻ `attacks.py`, `dprime_sweep.py`, `agent_llm.py` (~1.5k LOC mỗi file). Chẻ file lớn là việc riêng; trộn vào đây sẽ khiến không review được.
- Không sửa hai test đỏ ở gate 2.
- Không viết lại nội dung `.md` nào — chỉ dời và sửa đường dẫn trỏ tới chúng.
- Không dùng lớp shim để `import core` cũ vẫn chạy. Hai đường import cho cùng một thứ sẽ sống mãi trong codebase nghiên cứu.
- Không gitignore output spikes.

## 8. Rủi ro còn lại

**Gate 3 chưa bao giờ chạy trong baseline.** Chụp baseline bằng `--all` sẽ ép nó chạy, nhưng nếu gate 3 đỏ sẵn thì nó chỉ còn là "đỏ giống nhau trước và sau", không phải bằng chứng thật.

**13 skip ở gate 1 cần `docker build -t auditgame:latest .`** mới kiểm chứng được. Không build thì 13 tuyên bố đó không có hậu thuẫn nào trong cả baseline lẫn lần chạy sau.

**Cây mã đang thay đổi.** Nếu có phiên làm việc khác đang sửa `auditgame/`, giai đoạn 5 sẽ xung đột diện rộng vì nó chạm mọi dòng import. Giai đoạn 5 cần một khoảng thời gian không ai khác sửa cây mã.
