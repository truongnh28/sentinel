# Pilots thiết kế v2 (25/09/2026), chỉ trên dev

Các bản thử dưới đây chạy **chỉ trên tập dev** (họ repo django), với các cột attacker dùng để tinh chỉnh (D18) hoặc với best response trên dev. Không có attacker held-out nào, không có repo eval nào. Chúng là bằng chứng cho quyết định thiết kế Q1/Q3 của plan `docs/design/plans/2026-09-24-Faithful-Draft-v2-Plan.md` (bản 25/09).

| Tệp | Câu hỏi | Kết quả chính |
|---|---|---|
| `pilot1.py`, `pilot1-summary.json` | Thế giới "cổng theo giai đoạn" của bản plan 24/09 có thể hiện được cơ chế của Sentinel không? | Không. B4 (retrieval@3 mọi task) có harm tệ nhất ≈ 0,019 ở mọi ρ, vì cổng retrieval thấy mọi carrier tại σ, nhưng bác nhầm ≈ 8,6 đối tượng mỗi episode. Minimax trên L chọn một policy thuần ≈ B1. Δ không có tác dụng. |
| `pilot2.py`, `pilot2.json` | Mô hình hình thức §4 của draft (audit một carrier, đọc trạng thái đang tồn tại) có thể hiện được không? | Có. B1 phẳng theo Δ; các policy quét carrier tốt lên theo Δ; điểm giao nằm quanh Δ ≈ 1–4 tuỳ ρ; lịch tất định bị khai thác khi Δ < K. |
| `pilot2b.py`, `pilot2b.json` | Như pilot 2, thêm vòng quay pha ngẫu nhiên và best response cross-fit | Vòng quay pha ngẫu nhiên trội hơn quét i.i.d.; lấy max trực tiếp làm V(B1) phình gấp đôi (0,25 so với 0,125 cross-fit; giá trị giải tích 0,1275). |

Chạy lại (từ `auditgame/`):

```bash
PYTHONPATH=spikes/v2-pilot/snapshot_2409:spikes/v2-pilot:. python3 spikes/v2-pilot/pilot1.py
PYTHONPATH=spikes/v2-pilot/snapshot_2409:spikes/v2-pilot:. python3 spikes/v2-pilot/pilot2.py
PYTHONPATH=spikes/v2-pilot/snapshot_2409:spikes/v2-pilot:. python3 spikes/v2-pilot/pilot2b.py
```

`pilot1.py` ghi `pilot1.json` thô (~15 MB); `pilot1_summarise.py` rút về `pilot1-summary.json`, và chỉ bản tóm tắt được giữ trong repo.

`snapshot_2409/` là các khối code trích nguyên văn từ bản plan 24/09 (thế giới cổng). Chúng **không** phải code v2 hiện hành; chỉ để chạy lại pilot. `pilot1.py` cần scipy cho phần tóm tắt (`../.venv/bin/python`).
