# Sentinel — AuditGame-SE

Mã nguồn và tài liệu phương pháp luận của đề tài **FSE-2027-15 — Sentinel**. Đề tài mô hình hoá việc phân bổ audit như một trò chơi Stackelberg giữa bên phòng thủ và kẻ tấn công. Kẻ tấn công đầu độc các *carrier* dai dẳng của một coding agent (`memory · skill · queue · branch`), và thiệt hại chỉ lộ ra sau độ trễ Δ task.

Repo gồm hai phần:

- **`docs/`** — tài liệu phương pháp luận ([mục lục](docs/README.md)).
- **`auditgame/`** — benchmark AuditGame-SE: dựng workflow từ SWE-bench, tiêm payload, chạy agent (mock hoặc LLM thật), chấm harm bằng oracle niêm phong, và so sánh các chính sách audit B1–B7 với Sentinel.

## Tài liệu

1. **[Phương pháp luận triển khai](docs/Phuong-phap-luan-trien-khai.md)** — tài liệu chính: bài toán, mô hình, lý thuyết, triển khai theo 11 stage, nguồn gốc tham số, đe doạ tính hợp lệ.
2. **[Khảo sát nguồn](docs/Khao-sat-nguon-phuong-phap-luan.md)** — cơ sở trích dẫn cho tài liệu chính, kèm lệnh chạy harness và kế hoạch thực hiện.

## Kết quả đã đo khác với dự phóng

Mọi số hiệu năng trong bản thảo gốc là giá trị dự phóng. Các phép đo đã chạy trong repo cho thấy một số điểm không khớp:

| Kết quả đo | Dữ liệu |
|---|---|
| Trên hàm mất mát `L` (payload v2, `λ_Q = 0,10`), B5 risk-score dẫn trước Sentinel ở 61/64 ô lưới | `auditgame/spikes/sweep-v2-pinned.json`, `sweep-v2-following.json` |
| Ngưỡng AUC 0,56 của cổng bề mặt nằm trong dải nhiễu của corpus ở mọi cỡ mẫu `n ≤ 1800` | `auditgame/spikes/band_curve.json` |
| Agent LLM thật (`deepseek-v4.1-flash`) làm theo lời khuyên độc ở 0/14 instance, nên giả định `P(harm \| retrieved) = 1` không đứng | `auditgame/spikes/p2-control.jsonl` |
| Trên MockAgent, lợi thế của Sentinel so với B1 không lớn nhất khi detector yếu nhất, trái với dự đoán RQ4 | `python3 experiment.py --n 40` |

## Cấu trúc

```
Sentinel/
├── README.md
├── Dockerfile           môi trường của AGENT (không phải của phép đo)
├── pyproject.toml, uv.lock
├── docs/                tài liệu phương pháp luận
└── auditgame/           benchmark — chạy mọi lệnh từ trong thư mục này
    ├── core.py build.py runner.py policies.py detector.py oracle.py …
    ├── analysis/        corpus benign, discriminator, cổng 2
    ├── hidden_tests/    oracle test ẩn
    ├── payloads/        payload đóng băng và bộ sinh
    ├── reference/       bảng tra đi kèm mã (score_table.json, gate2_v2.json)
    ├── spikes/          script thí nghiệm và dữ liệu kết quả .json/.jsonl
    ├── scripts/ tools/  tiện ích đo đạc
    ├── results/         trace công khai (M3-trace.json)
    └── tests/           ba cổng kiểm thử: gate1_integrity · gate2_validity · gate3_power
```

## Chạy

Lõi đo lường chỉ dùng thư viện chuẩn của Python. Các module được import phẳng (`import core`), nên **mọi lệnh chạy từ trong `auditgame/`**.

```bash
cd auditgame
python3 experiment.py --n 40                 # quét lưới (Δ × χ × detector) trên MockAgent (vài phút)
python3 spikes/trace_one_episode.py          # in một ván chạy đầu-tới-cuối
python3 tests/run_all.py                     # ba cổng kiểm thử, dừng ở cổng đỏ đầu tiên
python3 tests/run_all.py --all               # chạy cả ba cổng
```

Phần phân tích (scipy, scikit-learn) và công cụ SWE-bench cần môi trường đầy đủ: `uv sync`, rồi chạy bằng `../.venv/bin/python`.

Trạng thái kiểm thử ngày 22/09/2026 (`--all`): **756 đạt · 1 không đạt · 13 bỏ qua**.
- Không đạt: `test_benign_corpus…test_one_split_cannot_decide_a_delta_of_the_certify_corpus`, một phát hiện đã ghi nhận: corpus đủ mạnh khiến tiêu chí đa phân hoạch mất tác dụng.
- 13 bỏ qua: cần image Docker `auditgame:latest` (`docker build -t auditgame:latest .`).

Các lượt chạy với LLM thật có chi phí và không tái lập được theo seed. Kết quả của chúng được lưu tại `auditgame/spikes/*.jsonl` và chỉ được đọc lại, không chạy lại.

## Những gì không có trong repo

| Không đưa vào | Lý do | Cách tạo lại |
|---|---|---|
| `auditgame/data/*.jsonl` (~54 MB) | metadata SWE-bench | `python3 swebench_fetch.py` |
| `auditgame/workspace/` | bản clone các repo bên thứ ba | harness tự clone |
| `auditgame/carriers-sealed/`, `hidden_suites/`, `results/*-sealed.json` | **đáp án** (nhãn `poisoned`) mà benchmark cần suy ra | sinh lại khi chạy |
| `.env` | khoá API | tự tạo |

Lý do chi tiết nằm trong [`.gitignore`](.gitignore).
