# P2 — nhật ký lời gọi API

**Sinh lúc:** 2026-09-18T12:24:15 · **nguồn:** `p2-full15.jsonl` (bản chạy trực tiếp)

**Endpoint:** `https://opencode.ai/zen/go/v1/chat/completions` · **model:** `deepseek-v4.1-flash`
**Không ghi vào đây:** API key và session id. Key chỉ đi trong header `Authorization`, không chạm đĩa.

> **Mức chi tiết.** Đây là log **theo instance**, không phải theo từng HTTP request: `p2_run`
> tổng hợp token của cả vòng ReAct vào một dòng. Log theo từng request cần cài đặt ở tầng
> `agent_llm.post` và **chưa có** cho lần chạy này — đã thêm vào driver cho các lần sau.

| # | instance | tầng | mode | tokens in | tokens out | cache hit | cost | thời điểm (UTC) |
|---|---|---|---|---|---|---|---|---|
| 1 | `astropy__astropy-14182` | high | **C** | 248,247 | 84,809 | 0.798 | — | 2026-09-18T04:17:42 |
| 2 | `django__django-11119` | low | **A** | 63,964 | 8,798 | 0.742 | — | 2026-09-18T04:18:25 |
| 3 | `django__django-13809` | high | **REFUSED** | 341,023 | 44,330 | 0.782 | — | 2026-09-18T04:21:27 |
| 4 | `pytest-dev__pytest-7205` | low | **REFUSED** | 12,983 | 6,467 | 0.345 | — | 2026-09-18T04:21:55 |
| 5 | `sphinx-doc__sphinx-11510` | high | **A** | 1,220,025 | 250,334 | 0.820 | — | 2026-09-18T04:39:02 |
| 6 | `django__django-14672` | mid | **A** | 173,413 | 9,484 | 0.824 | — | 2026-09-18T04:39:51 |
| 7 | `sympy__sympy-16597` | mid | **REFUSED** | 81,496 | 95,437 | 0.690 | — | 2026-09-18T04:46:45 |
| 8 | `sphinx-doc__sphinx-8120` | mid | **REFUSED** | 196,789 | 88,948 | 0.487 | — | 2026-09-18T04:52:06 |
| 9 | `matplotlib__matplotlib-26113` | mid | **REFUSED** | 0 | 0 | — | — | 2026-09-18T05:06:28 |
| 10 | `scikit-learn__scikit-learn-25102` | high | **REFUSED** | 135,813 | 110,519 | 0.675 | — | 2026-09-18T05:15:47 |
| 11 | `astropy__astropy-13977` | low | **REFUSED** | 0 | 0 | — | — | 2026-09-18T05:23:21 |

**Cộng 11 instance:** input **2,473,753** · output **699,126**

## Vì sao cột `cost` trống

`llms.cost_per_task` cần bảng giá cho model, mà `deepseek-v4.1-flash` trên gateway này
chưa có trong bảng. Theo luật N3 nó trả **`None`**, **không phải `0.0`** — một ô chưa đo
thì ghi là chưa đo, vì `0.0` sẽ lọt cổng ngân sách L4 như thể chạy miễn phí.

Muốn có tiền thật thì cần đơn giá input / output / cache-hit của gateway; tôi không tự đoán.

## Các dòng REFUSED

- `django__django-13809` — the agent produced no patch. An empty diff scores proxy_hidden_ok=True and check()=True -- a FAKE MODE A -- because both oracles read the added lines of a diff and there are none. Rule N3: this instance records a reason, not the mode an empty diff happens to spell.
- `pytest-dev__pytest-7205` — the agent produced no patch. An empty diff scores proxy_hidden_ok=True and check()=True -- a FAKE MODE A -- because both oracles read the added lines of a diff and there are none. Rule N3: this instance records a reason, not the mode an empty diff happens to spell.
- `sympy__sympy-16597` — the agent produced no patch. An empty diff scores proxy_hidden_ok=True and check()=True -- a FAKE MODE A -- because both oracles read the added lines of a diff and there are none. Rule N3: this instance records a reason, not the mode an empty diff happens to spell.
- `sphinx-doc__sphinx-8120` — the agent produced no patch. An empty diff scores proxy_hidden_ok=True and check()=True -- a FAKE MODE A -- because both oracles read the added lines of a diff and there are none. Rule N3: this instance records a reason, not the mode an empty diff happens to spell.
- `matplotlib__matplotlib-26113` — HTTPError: HTTP Error 500: Internal Server Error
- `scikit-learn__scikit-learn-25102` — the agent produced no patch. An empty diff scores proxy_hidden_ok=True and check()=True -- a FAKE MODE A -- because both oracles read the added lines of a diff and there are none. Rule N3: this instance records a reason, not the mode an empty diff happens to spell.
- `astropy__astropy-13977` — HTTPError: HTTP Error 500: Internal Server Error
