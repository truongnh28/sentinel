# Sentinel v3 — P0: nguồn dữ liệu cho tập eval mới

27/09/2026. Đây là khảo sát để lập kế hoạch, chưa dựng tập và chưa chạy eval nào. Số liệu lấy trực tiếp từ Hugging Face (API, danh sách parquet, đọc từng cột của parquet từ xa). Số workflow là **ước tính** từ mô phỏng bộ cắt, không phải tập đã đóng băng.

## Tóm tắt

- **Có đạt được ~100 workflow / 15+ họ chưa chạm mà không dùng lại instance.** Chỉ một nguồn làm được việc này một mình: **SWE-rebench-V2** (nebius, 02/2026).
  - Có 32.079 instance trên 3.615 repo. Sau khi loại các repo của v2 còn 562 họ có ≥ 14 instance, 195 họ ≥ 28 và 46 họ ≥ 70.
  - Mọi instance đều có `created_at`, `base_commit`, `patch`, `test_patch`, `FAIL_TO_PASS` và một Docker image dựng sẵn trên Docker Hub (`docker.io/swerebenchv2/...`).
  - Ước tính: 20 họ × 5 workflow = **100 workflow, Kish 20**. Nếu chỉ dùng instance tạo từ 01/2024 trở đi: **96 workflow (91–100 theo seed) / 20 họ, Kish 19,8**.
- **Nguồn thứ hai tốt là SWE-rebench (v1, chỉ Python).**
  - Split `test` có 21.336 instance. Ước tính 100 workflow / 20 họ, Kish 20.
  - Nhưng chỉ 6.542 instance có image dựng sẵn. Nếu chỉ lấy tập có image thì còn khoảng 82 workflow / 20 họ.
- **Các nguồn còn lại không đủ nếu đứng một mình.**
  - Multi-SWE-bench: khoảng 64 workflow / 20 họ.
  - Multi-SWE-RL (bản verified): khoảng 73 workflow.
  - SWE-Gym: chỉ 11 họ.
  - SWE-bench-extra: khoảng 60 workflow, lại không có image.
  - SWE-bench-Live: khoảng 63 workflow.
  - SWE-bench Pro: 10 họ và không có `created_at`.
  - SWE-rebench-leaderboard và SWE-bench-Live/MultiLang tuy mới nhưng họ quá nhỏ (≤ 2 và 9 họ có ≥ 14 instance).
- **So với fallback C14** (26 workflow / 18 họ, Kish 10,2), phương án SWE-rebench-V2 cho số workflow gấp khoảng **4 lần** và Kish gấp khoảng **2 lần**, không phải dùng luật "H = cỡ họ", và không phải dùng lại instance.
- **Rủi ro lớn nhất là nhiễm bẩn qua huấn luyện, không phải thiếu dữ liệu.** SWE-rebench-V2 được phát hành *như tập huấn luyện RL*: hơn 100k lượt tải, có nhiều bản phái sinh và trajectory công khai. Mô hình ra đời sau 02/2026 có thể đã được huấn luyện RL trên chính các task này. Xem mục 5.

## 1. Cách đếm

- **Loại 17 repo v2** (so khớp không phân biệt hoa thường): django, sympy, sphinx, scikit-learn, matplotlib, xarray, pytest, astropy, lombok, caddy, laravel, preact, rubocop, fastlane, fluentd, phpspreadsheet, bat.
- **Khử trùng lặp** theo `instance_id`. Split `test` của leaderboard lặp lại các split theo tháng. V2-PRs có 126.300 dòng nhưng chỉ 122.910 id khác nhau.
- **"≥ 14" và "≥ 28"** là số họ có từ 14 hoặc 28 instance trở lên, tính sau khi đã loại các repo v2.
- **Workflow ước tính** được tính bằng mô phỏng bộ cắt của `corpus_v2` / `v3_p0_corpus.py`:
  - Theo từng repo, xếp theo `created_at`, cắt các cửa sổ liên tiếp với H ~ U{6..14}.
  - Chỉ **một lượt** (offset 0), nên không có instance nào được dùng lại.
  - Chạy 300 seed. Chọn F họ lớn nhất và giới hạn mỗi họ tối đa c workflow ("cap").
  - Kish = (Σw)²/Σw². Khi mọi họ đều chạm cap thì Kish = F.
- **Đọc dữ liệu.** Chỉ các cột nhỏ (repo, id, created_at, base_commit, image, language, license, số F2P) được đọc bằng column projection. Không tải patch. Script tạm nằm trong scratchpad và không được commit.

## 2. Bảng tổng hợp theo nguồn

Cột "Họ ≥14 / ≥28" tính sau khi đã loại các repo v2.

| Nguồn (HF id) | Instance | Repo | Họ ≥14 / ≥28 | Ngôn ngữ | created_at | Image / harness | License | Khoảng thời gian |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **SWE-rebench-V2** (`nebius/SWE-rebench-V2`) | 32.079 | 3.615 | **562 / 195** | 20 ngôn ngữ | có | **image cho 100%**; harness `SWE-rebench/SWE-rebench-V2` (`scripts/eval.py`) | CC-BY-4.0 + license từng repo | 11/2014 – 10/2025 (trung vị 09/2022) |
| SWE-rebench-V2-PRs (`nebius/SWE-rebench-V2-PRs`) | 122.910 | 3.221 | 1.791 / 1.116 | nhiều | có | **không có cột image**; tự build từ `install_config` | CC-BY-4.0 | 07/2013 – 07/2025 |
| SWE-rebench v1, split `test` (`nebius/SWE-rebench`) | 21.336 | 3.468 | 304 / 124 | Python | có | image cho 6.542 instance (Docker Hub `swerebench`); fork SWE-bench cho phần còn lại | CC-BY-4.0 | 04/2014 – 04/2025 |
| SWE-rebench v1, split `filtered` | 6.542 | 1.790 | 78 / 22 | Python | có | image 100% | CC-BY-4.0 | 04/2016 – 04/2025 |
| SWE-rebench-leaderboard | 860 | 413 | 2 / 1 | Python | có | image 100% | CC-BY-4.0 | 01/2025 – 05/2026 |
| Multi-SWE-bench (`ByteDance-Seed/Multi-SWE-bench`; bản parquet `PrimeIntellect/Multi-SWE-bench`) | 2.132 (1.632 không phải Python) | 51 | 23 / 12 | 7 ngôn ngữ (không kể Python) | **không có**; chỉ có số PR và `base.sha` | image `mswebench/*` + harness `multi-swe-bench` | "other" (README ghi CC0) | chưa xác định |
| Multi-SWE-RL, bản verified (`PrimeIntellect/Multi-SWE-RL-Verified`) | 2.232 | 43 | 23 / 18 | Go, TS, JS, Java, C | không có | harness `multi-swe-bench` | other / CC0 | 06/2024 – 06/2025 (theo tên thư mục) |
| SWE-Gym (`SWE-Gym/SWE-Gym`) | 2.438 | 11 | 11 / 10 | Python | có | image OpenHands (theo README) | MIT | 09/2018 – 05/2024 |
| SWE-bench-extra (`nebius/SWE-bench-extra`) | 6.376 | 1.974 | 67 / 11 | Python | có | không có image; phải tự dựng môi trường | CC-BY-4.0 | 10/2015 – 04/2024 |
| SWE-bench-Live, split `full` | 1.887 | 223 | 32 / 13 | Python | có | image `starryzhang/sweb.eval.*` | MIT | 07/2021 – 09/2025 |
| SWE-bench-Live/MultiLang | 1.077 | 431 | 9 / 1 | 8 ngôn ngữ | có | image 100% | MIT | 06/2020 – 07/2026 (trung vị 03/2026) |
| SWE-bench Pro, bản công khai (`ScaleAI/SWE-bench_Pro`) | 642 | 11 | 10 / 10 | Python, Go, JS/TS | **không có** | image `ghcr.io/scaleapi/...` | — | — |
| SWE-smith (`SWE-bench/SWE-smith`) | 59.136 | ~128 | — | Python | không có | có image | MIT | **loại**: bug tổng hợp, không phải lịch sử thật; không có `base_commit` và `created_at` |

**Về các trường dữ liệu.**
- Mọi nguồn trong bảng đều có `base_commit`, `patch` và `test_patch`, và mọi dòng đều có `FAIL_TO_PASS` không rỗng. Ngoại lệ:
  - SWE-smith không có `base_commit`.
  - Multi-SWE-bench và Multi-SWE-RL dùng `fix_patch` và `f2p_tests` (dạng dict) thay cho các tên trường trên.
- SWE-rebench-V2 còn có `meta.llm_metadata`, gồm:
  - độ khó;
  - `intent_completeness`;
  - các cờ lỗi B1 (test coupling), B2 (implicit naming), B3 (external URL), … B6.
  Có thể dùng các trường này để lọc chất lượng.

**Về image.**
- Đã kiểm tra trên Docker Hub:
  - `swerebenchv2` có 3.743 repository;
  - `swerebenchv2/getmoto-moto` có 253 tag, `pandas-dev-pandas` 218, `gleam-lang-gleam` 99, `kestra-io-kestra` 135 và `microsoft-kiota` 123. Tức là có image cho từng instance, và số tag không ít hơn cỡ họ;
  - `mswebench/cli_m_cli` có 506 tag.
- Theo bài báo V2, toàn bộ image nặng 26,36 TiB, tức khoảng **0,84 GiB mỗi instance**. Mẫu kiểm tra trên Docker Hub cho thấy khoảng 1,3 GB mỗi image (đã nén).

## 3. Chi tiết từng nguồn (top họ, sau khi loại v2)

### 3.1 SWE-rebench-V2 — ứng viên chính

**Họ ≥ 14 theo ngôn ngữ:** Python 140, Go 94, TypeScript 76, JavaScript 64, Rust 59, Java 33, PHP 23, Julia 18, Kotlin 15, Scala 9, Elixir 7, Swift 5, C 5, R 5, Dart 4, C++ 2, Clojure 2, C# 1.

**Repo v2 có mặt (đã loại):** laravel/framework 56, phpoffice/phpspreadsheet 49, projectlombok/lombok 14, sharkdp/bat 4. V2 không chứa django, sympy, pytest và các repo SWE-bench khác. Nó cũng không chứa các họ của C14 (pylint, requests, seaborn, flask), nên **có thể ghép với C14 mà không trùng họ**.

**Top 25 (toàn bộ thời gian)**

| Họ | n | Ngôn ngữ | Khoảng thời gian | n từ 2024 |
| --- | --- | --- | --- | --- |
| swc-project/swc | 410 | Rust | 07/2021–03/2025 | 68 |
| vaskoz/dailycodingproblem-go ⚠ | 355 | Go | 08/2018–10/2020 | 0 |
| serverless/serverless | 272 | JS | 10/2016–06/2023 | 0 |
| getmoto/moto | 249 | Python | 01/2023–07/2025 | 132 |
| pandas-dev/pandas | 207 | Python | 12/2022–07/2025 | 168 |
| eslint/eslint | 196 | JS | 11/2016–03/2022 | 0 |
| statamic/cms | 189 | PHP | 10/2022–05/2025 | 96 |
| fhir/sushi | 189 | TS | 01/2020–05/2025 | 21 |
| analysis-dev/diktat ⚠ | 166 | Kotlin | 10/2020–03/2023 | 0 |
| platers/obsidian-linter | 143 | TS | 09/2021–06/2025 | 30 |
| helm/helm | 139 | Go | 09/2019–05/2025 | 19 |
| pennylaneai/pennylane | 135 | Python | 02/2021–06/2025 | 49 |
| aws-cloudformation/cfn-lint | 135 | Python | 06/2021–05/2025 | 111 |
| kestra-io/kestra | 132 | Java | 09/2023–06/2025 | 117 |
| aio-libs/aiohttp | 128 | Python | 12/2020–07/2025 | 100 |
| joshuakgoldberg/create-typescript-app | 127 | TS | 10/2023–07/2025 | 126 |
| microsoft/kiota | 123 | C# | 11/2023–10/2025 | 112 |
| zeek/zeek | 121 | C++ | 06/2020–07/2025 | 32 |
| sveltejs/kit | 117 | JS | 01/2022–03/2023 | 0 |
| hypothesisworks/hypothesis | 114 | Python | 01/2020–04/2025 | 21 |
| scalameta/scalameta | 103 | Scala | 10/2021–10/2025 | 53 |
| gleam-lang/gleam | 95 | Rust | 07/2024–06/2025 | 95 |
| pybamm-team/pybamm | 95 | Python | 07/2019–06/2025 | 43 |
| rust-analyzer/rust-analyzer ⚠ | 94 | Rust | 10/2018–03/2022 | 0 |
| mgechev/revive | 93 | Go | 05/2020–06/2025 | 34 |

⚠ đánh dấu các họ cần xử lý trước khi dùng (xem mục 5).

**Chỉ tính instance tạo từ 01/2024**

| Mốc | Họ ≥14 | ≥28 | ≥42 | ≥70 |
| --- | --- | --- | --- | --- |
| từ 01/2023 | 219 | 72 | 39 | 16 |
| từ 01/2024 | 120 | 40 | 23 | 10 |
| từ 07/2024 | 72 | 26 | 14 | 7 |
| từ 01/2025 | 32 | 8 | 3 | 1 |
| từ 06/2025 | 2 | 0 | 0 | 0 |

**Top họ từ 01/2024:** pandas 168, moto 132, create-typescript-app 126, kestra 117, kiota 112, cfn-lint 111, aiohttp 100, statamic/cms 96, gleam 95, pyccel 70, swc 68, sage/carbon 64, detekt 63, veryl 54, scalameta 53, pennylane 49, rust-lang/cargo 49, openmdao 48, gradleup/shadow 47, keras 45, twig 43, pybamm 43, narwhals 43, primefaces 41, powertools-lambda-typescript 40.

Trong top 20 này có 8 họ Python, 4 Rust, 2 TS, 2 Kotlin, và mỗi thứ tiếng Java, C#, PHP, Scala có 1 họ.

**License của 105 họ ≥ 42:** Apache-2.0 34, MIT 32, `custom-check-github` 19 (cần xem tay), BSD-3 9, AGPL-3.0 1.

### 3.2 SWE-rebench-V2-PRs

- Có 122.910 task sinh từ PR, *không có issue gốc*. `problem_statement` được sinh bằng prompt `pr_description.j2`, tức là **LLM viết**.
- Có 1.791 họ ≥ 14 và 1.116 họ ≥ 28. Chỉ tính từ 2024: 489 / 271.
- Top: redis 1.084, rust-analyzer 985, wazero 793, wasmtime 764, pennylane 745, statamic 723, dd-trace-js 662, …
- Không có image dựng sẵn trong dataset. Chỉ nên dùng làm **nguồn dự phòng để nối dài** một họ của V2, vì bài toán do LLM viết lệch với phân bố issue thật mà v2 đã dùng.

### 3.3 SWE-rebench v1 (Python)

- **Split `test` (21.336):** sqlglot 452, dvc 241, dask 196, pybamm 172, conan 168, pillow 164, pydicom 133, nilearn 126, geopandas 125, sqlfluff 121, networkx 114, ignite 114, streamlink 113, narwhals 107, pennylane 105, tox 99, textual 90, faker 86, pre-commit 86, borg 84.
- **Tập có image (6.542):** sqlglot 294, pennylane 76, streamlink 73, conan 73, dvc 72, dask 72, ignite 63, tox 58, sqlfluff 51, textual 49, …
- Dữ liệu dừng ở 04/2025. Chỉ tính từ 2024 thì còn 55 họ ≥ 14 và 13 họ ≥ 28.
- Có trùng họ với V2 (pennylane, pybamm, moto, …). Nếu ghép hai nguồn thì phải khử trùng lặp theo (repo, số PR).

### 3.4 Multi-SWE-bench (ByteDance)

- **Họ không phải Python, chưa chạm:** cli/cli 397 (Go), svelte 272 (JS), material-ui 174 (TS), clap 132 (Rust), ponyc 82 (C), dayjs 56 (JS), nlohmann/json 55 (C++), vuejs/core 48 (TS), jackson-databind 42 (Java), fmt 41 (C++), logstash 38 (Java), zstd 29 (C), tokio 25, tracing 21, simdjson 20, github-readme-stats 19, jackson-core 18, jq 17, grpc-go 16, go-zero 15, nushell 14, fd 14.
- Có 23 họ ≥ 14, trải đều 7 ngôn ngữ.
- **Không có `created_at`.** Phải xếp theo số PR (tăng đơn điệu theo thời gian tạo trong cùng một repo) hoặc tra GitHub API. Đây là một sai lệch phải khai so với bộ cắt v2.
- Phần Python của bản PrimeIntellect (500 instance, django, sympy, …) trùng với v2 và đã bị loại.

### 3.5 Multi-SWE-RL (bản verified của PrimeIntellect)

- checkstyle 610 (Java), hugo 490 (Go), svelte 190, cli 108, react-router 78, lazygit 68, act 55, vuejs/core 52, material-ui 46, spotbugs 40, SDL 35, commander.js 33, zod 32, nuxt 31, syncthing 30, junit5 30, …
- Có 23 họ ≥ 14 và 18 họ ≥ 28. Họ lệch mạnh: checkstyle và hugo chiếm 50% số instance.
- **Trùng họ với Multi-SWE-bench** (svelte, cli, vuejs, mui). Nếu ghép thì phải khử trùng lặp theo số PR.
- Bản gốc `ByteDance-Seed/Multi-SWE-RL` nặng 23,9 GB jsonl và chưa được đếm. Riêng file TypeScript chiếm 17 GB.

### 3.6 Các nguồn khác

- **SWE-Gym.** Có 11 họ: pandas 737, monai 374, moto 343, mypy 257, dvc 225, dask 145, modin 107, pydantic 83, conan 75, hydra 66, bokeh 26. Chỉ 11 họ nên Kish ≤ 11, không đạt mục tiêu 15 họ.
- **SWE-bench-extra.** Là tiền thân của SWE-rebench. Top: dvc 258, pydantic 200, sqlglot 107, pyupgrade 62. Chỉ 11 họ ≥ 28 và không có image.
- **SWE-bench-Live `full`.**
  - Top: conan 164, cfn-lint 109, haystack 88, **pylint 62** (trùng C14), instructlab 52, keras 48, reflex 44.
  - Có 32 họ ≥ 14. Dữ liệu từ 2024–2025, được làm mới hằng tháng (+50 instance mỗi tháng).
- **SWE-bench-Live/MultiLang.**
  - Là nguồn mới nhất: trung vị 03/2026, tối đa 07/2026.
  - Nhưng dữ liệu rải rác: httrack 38, duckdb 26, svelte 24, … Chỉ 9 họ ≥ 14.
- **SWE-rebench-leaderboard.** Dữ liệu 01/2025–05/2026. Chỉ sqlglot 41 và litellm 16 đạt ≥ 14.
- **SWE-bench Pro.**
  - Có 10 họ, mỗi họ 38–82 instance: ansible, openlibrary, flipt, qutebrowser, teleport, vuls, protonmail, element-web, navidrome, nodebb.
  - Không có `created_at` và chỉ 10 họ.
  - Được thiết kế để chống nhiễm bẩn (repo copyleft). Chỉ đáng cân nhắc làm *phần bổ sung*.

### 3.7 Lọc chất lượng của SWE-rebench-V2 (đo trên `meta.llm_metadata`)

**Tỉ lệ instance bị gắn cờ** (các repo ngoài v2):

| Cờ | B1 | B2 | B3 | B4 | B5 | B6 |
| --- | --- | --- | --- | --- | --- | --- |
| Tỉ lệ | 3,7% | 10,0% | 1,0% | 10,6% | 3,9% | 0,7% |

**Instance "sạch"** (không có cờ nào) chiếm **72%**.

- Độ khó: easy 8.634, medium 21.722, hard 1.481.
- `intent_completeness`: complete 24.326, partial 7.352, insufficient 159.

**Số họ còn lại sau khi chỉ giữ instance sạch**

| Tập | Instance | Họ ≥14 | ≥28 | ≥42 | ≥70 | Ước tính 20 × 5 | Ước tính 25 × 4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V2, mọi thời điểm | 31.956 | 562 | 195 | 97 | 46 | 100 wf, Kish 20 | 100 |
| V2 sạch | 23.091 | 375 | 131 | 62 | 26 | 100 wf, Kish 20 | 100 |
| V2 từ 01/2024 | 9.242 | 120 | 40 | 23 | 10 | 96,1 [91; 100], Kish 19,8 | 98,0 |
| V2 sạch, từ 01/2024 | 6.680 | 78 | 26 | 14 | 6 | 86,3 [81; 92], Kish 19,2 | 88,3 |

## 4. Mô phỏng dựng tập (ước tính)

Chọn F họ lớn nhất, cap c workflow mỗi họ, cắt một lượt, 300 seed. Cột "Workflow" là trung bình [min; max].

| Nguồn / điều kiện | F × cap | Workflow | Kish | Họ nhỏ nhất được chọn |
| --- | --- | --- | --- | --- |
| **V2, mọi thời điểm** | 20 × 5 | **100** [100; 100] | **20,0** | 114 |
| V2, mọi thời điểm | 15 × 7 | 105 | 15,0 | 128 |
| V2, mọi thời điểm | 25 × 4 | 100 | 25,0 | 93 |
| V2, không Python | 20 × 5 | 100 | 20,0 | 89 |
| **V2, từ 01/2024** | 20 × 5 | **96,1** [91; 100] | **19,8** | 45 |
| V2, từ 01/2024 | 25 × 4 | 98,0 [94; 100] | 24,9 | 40 |
| V2, từ 07/2024 | 20 × 5 | 84,6 [79; 90] | 19,2 | 33 |
| V2, từ 01/2025 | 32 × 3 | 59,2 [51; 66] | 27,0 | 14 |
| V2 Filtered-Verified (PrimeIntellect, 6.272) | 25 × 4 | 70,6 | 23,1 | 24 |
| SWE-rebench v1, `test` | 20 × 5 | 100 | 20,0 | 84 |
| SWE-rebench v1, tập có image | 20 × 5 | 82,0 [75; 88] | 18,9 | 30 |
| Multi-SWE-bench, không Python | 20 × 5 | 64,1 | 15,9 | 15 |
| Multi-SWE-RL verified | 20 × 5 | 72,5 | 17,9 | 23 |
| SWE-Gym | 11 × 10 | 93,1 | 10,2 | 26 |
| SWE-bench-extra | 20 × 5 | 60,0 | 17,0 | 23 |
| SWE-bench-Live `full` | 20 × 5 | 63,2 | 17,0 | 21 |
| SWE-bench Pro | 10 × 10 | 59,6 | 9,3 | 38 |
| *Fallback C14 (v3-p0.md)* | — | *26* | *10,2* | *6* |

**Đọc bảng.**
- Với V2, mọi họ được chọn đều đủ lớn để luôn chạm cap. Vì vậy số workflow không phụ thuộc seed, và Kish bằng đúng F.
- Ở ô "từ 01/2024", một số họ chỉ có 45–54 instance nên đôi khi không đủ 5 cửa sổ.
- Khoảng 2/3 số workflow sẽ có H ≥ 9, đủ để chứa Δ = 8. Đây là suy từ H ~ U{6..14}, chưa mô phỏng lại.

**Muốn giảm nhiễm bẩn thì nên cắt từ mới về cũ.** Một cách không làm thay đổi định nghĩa workflow: cắt cửa sổ từ instance **mới nhất** ngược về, thay vì từ offset 0. Với 20 họ lớn nhất của V2 (tính mọi thời điểm), 59% trong 60 instance gần nhất của mỗi họ được tạo từ 01/2024 trở đi. Vì vậy lọc cứng theo ngày (hàng "từ 01/2024" ở bảng trên) sạch hơn so với chỉ đổi chiều cắt.

## 5. Khuyến nghị

**Kết luận: đạt được, và nên đổi sang SWE-rebench-V2.**

Phương án đề xuất là V2, chỉ lấy instance tạo từ 01/2024, 20–25 họ, cap 4–5 workflow mỗi họ, cắt một lượt.
- Ước tính **96–98 workflow / 20–25 họ, Kish 20–25**, không dùng lại instance nào.
- Mỗi instance có sẵn base commit, gold patch, F2P và Docker image.

So với fallback C14 (26 / 18 / 10,2), phương án này hơn ở mọi mặt:
- nhiều workflow hơn khoảng 4 lần;
- Kish cao hơn khoảng 2 lần;
- không cần luật "H = cỡ họ";
- không có họ nào chỉ đóng góp 1 workflow.

Nếu muốn giữ lịch sử thật Python làm lõi so sánh với v2, có thể **ghép C14-Python (pylint, requests, seaborn) với V2**, vì các họ không trùng nhau. Khi đó pool khác nhau là một biến phải khai.

**Các lưu ý cần khai hoặc xử lý**

1. **Nhiễm bẩn.**
   - Dữ liệu V2 dừng ở 10/2025. Riêng phần từ 01/2024, trung vị `created_at` là 10/2024.
   - Nặng hơn là V2 được phát hành **làm môi trường huấn luyện RL** (02/2026). Đã có hàng chục bản phái sinh và trajectory công khai: PrimeIntellect, OpenHands, các bộ trajectory GLM, Qwen, …
   - Một mô hình được huấn luyện sau 03/2026 có thể đã thấy chính các task này. Rủi ro này cao hơn so với SWE-bench full mà v2 đã dùng.
   - Nếu v3 dùng mô hình có mốc huấn luyện sau 02/2026, cần kiểm tra nhanh: đo tỉ lệ agent giải được task khi không có công cụ, hoặc so khớp gold patch.
   - Chỉ có SWE-bench-Live/MultiLang và rebench-leaderboard là thật sự mới (2026), nhưng họ quá nhỏ.
   - Nếu nhiễm bẩn là mối lo chính, có một phương án lai đáng cân nhắc: V2 từ 07/2024 (khoảng 85 workflow / 20 họ) cộng thêm các họ Live/MultiLang ≥ 14 (khoảng +10 workflow). Đây là ước tính, chưa mô phỏng tổ hợp.
2. **Định danh họ.** Phải gộp các repo đổi chủ hoặc fork trước khi đếm "một repo = một họ":
   - analysis-dev/diktat ≡ cqfn/diktat (166 + 92);
   - rust-analyzer/rust-analyzer ≡ rust-lang/rust-analyzer;
   - apple/swift-syntax ≡ swiftlang/swift-syntax;
   - friendsofphp/php-cs-fixer ≡ php-cs-fixer/php-cs-fixer;
   - yannickcr ≡ jsx-eslint/eslint-plugin-react;
   - weaveworks/eksctl, …
3. **Họ không đại diện.** Nên loại bằng quy tắc khai trước, không chọn tay sau khi đã thấy kết quả:
   - vaskoz/dailycodingproblem-go và thealgorithms/java: repo bài tập;
   - jlongster/prettier: fork có 73 instance, tất cả trong 2017.
4. **Harness khác v2.**
   - V2 dùng `scripts/eval.py` với log parser riêng cho từng ngôn ngữ, không dùng harness SWE-bench.
   - Mọi task đã được kiểm bằng chạy thật: F2P lấy từ lần chạy test trước và sau patch.
   - Bản PrimeIntellect Filtered-Verified chỉ giữ 6.272/32.079 task. Bản này có kèm danh sách flaky và danh sách "no-edit pass", nhưng chưa rõ phần bị bỏ là do lọc hay do lấy mẫu. Vì vậy **cần chạy gold patch trên từng instance được chọn** trước khi đóng băng, và loại các task flaky hoặc có cờ B1–B3. Khi đó số họ đủ lớn sẽ giảm. Ví dụ, chỉ giữ instance không có cờ nào và từ 01/2024 thì còn khoảng 86–88 workflow (mục 3.7). Nếu cần giữ đủ 100 workflow sau khi lọc thì phải nới mốc ngày về 2023 hoặc tăng cap.
5. **Chi phí đĩa.** Khoảng 1.000 instance × khoảng 0,8–1,3 GB image. Các image cùng repo có thể dùng chung layer. Ước tính **0,5–1 TB** nếu kéo hết. Nên kéo theo từng họ.
6. **Đa ngôn ngữ.**
   - Chọn theo cỡ họ thì Python chiếm 30% trong top 20 họ (mọi thời điểm) và 40% trong top 20 họ từ 01/2024.
   - Nếu v3 cần giữ tỉ lệ ngôn ngữ giống v2 (v2 chủ yếu Python cùng 9 họ Multilingual), nên phân tầng họ theo ngôn ngữ trước khi chọn F họ lớn nhất.
7. **Multi-SWE-bench và Multi-SWE-RL.** Không có `created_at`, nên nếu dùng thì phải xếp theo số PR và khai là sai lệch. Không cần dùng nếu đã chọn V2.

**Tải về**
- Parquet: `load_dataset("nebius/SWE-rebench-V2", split="train")`. File đơn `data/train-00000-of-00001.parquet` nặng 2,26 GB. Chỉ đọc cột cần thiết thì mất khoảng 5 phút qua HTTP range.
- Harness: `github.com/SWE-rebench/SWE-rebench-V2` (MIT).
- Image: `docker pull docker.io/swerebenchv2/<owner>-<repo>:<pr>-<sha7>`, theo trường `image_name`.

## Nguồn

- [SWE-rebench-V2 (HF)](https://huggingface.co/datasets/nebius/SWE-rebench-V2) · [bài báo arXiv 2602.23866](https://arxiv.org/abs/2602.23866) · [blog Nebius](https://nebius.com/blog/posts/meet-swe-rebench-v2) · [harness GitHub](https://github.com/SWE-rebench/SWE-rebench-V2)
- [SWE-rebench-V2-PRs](https://huggingface.co/datasets/nebius/SWE-rebench-V2-PRs) · [SWE-rebench](https://huggingface.co/datasets/nebius/SWE-rebench) · [SWE-rebench-leaderboard](https://huggingface.co/datasets/nebius/SWE-rebench-leaderboard) · [SWE-bench-extra](https://huggingface.co/datasets/nebius/SWE-bench-extra)
- [Multi-SWE-bench](https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench) · [bản parquet PrimeIntellect](https://huggingface.co/datasets/PrimeIntellect/Multi-SWE-bench) · [Multi-SWE-RL](https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-RL) · [Multi-SWE-RL-Verified](https://huggingface.co/datasets/PrimeIntellect/Multi-SWE-RL-Verified)
- [SWE-Gym](https://huggingface.co/datasets/SWE-Gym/SWE-Gym) · [SWE-bench-Live](https://huggingface.co/datasets/SWE-bench-Live/SWE-bench-Live) · [SWE-bench-Live/MultiLang](https://huggingface.co/datasets/SWE-bench-Live/MultiLang) · [SWE-bench Pro](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro) · [SWE-smith](https://huggingface.co/datasets/SWE-bench/SWE-smith) · [PrimeIntellect SWE-rebench-V2-Filtered-Verified](https://huggingface.co/datasets/PrimeIntellect/SWE-rebench-V2-Filtered-Verified)
