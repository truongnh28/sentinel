# v3-p2 — Kết quả headline (main-block), Study 2

> **CẢNH BÁO (N3, DEV-only):** Mọi số trong báo cáo này là **số DEV** từ đúng một lần chạy
> main-block đã đóng băng, **KHÔNG phải** eval held-out P5. Không có số nào được tinh chỉnh;
> tất cả tính bằng `v3/metrics.py` + `v3/scorecard.py` (không tự cài lại metric/CI/rule nào).
> Ô nào không đo được / cần block khác được ghi **TBD kèm lý do**, không bao giờ ghi 0.

## 1. Nguồn dữ liệu & cấu hình

| Mục | Giá trị |
|---|---|
| Records | `spikes/v3-run/dev-headline-main/main.jsonl` |
| `records.sha256` (main.jsonl) | `e1db94d590f3bb34a24975aa10b71acccbd13f35a6ec5b51bf98aa25accde4a4` |
| Tổng records | 218 456 (dùng Δ∈{0,4,8}: 119 560) |
| Split | **dev** |
| Hệ thống có mặt | 14 (B1, B2, B3, B4, B5, B6, cost-greedy, SW randomised, Oracle (+), Sentinel, Sentinel [dhat=oracle], −randomization, −alarm memory, −benign-drift) |
| Không có mặt | **B7** (T21 chưa cài), **Sentinel −transition uncertainty** (cần tuning nominal-only) → để TBD |
| Attacker held-out | 7 cột: branch-first-write-e0.6, memory-last-ingress-e0.3, memory-last-write-e0.6, memory-mid-write-e0.3, queue-last-ingress-e0.6, queue-mid-write-e0.6, skill-last-write-e1.0 |
| Ô headline | Δ∈{4,8} (gộp), χ=1.33, d′=2.21, K_d=2, price_only=False |
| ρ (patch exposure) | 0, 0.25, 0.5, 1.0 |
| n_workflows | 99 (Δ=4) / 56 (Δ=8, H≥9); 2 seeds |
| Bootstrap | wild cluster (Webb), cụm = repo family (17 họ), N_boot=10000, α=0.05 |
| `rules_digest()` | (xem `table2_3.json`.meta.rules_digest) |

## 2. Controls (D28) — đọc TRƯỚC mọi số Sentinel

**PASS ở mọi ρ.** (+) Oracle worst-case harm = **0.000** (≤ 0.05) tại headline; (−) tại Δ=0
không baseline sweep-only nào thắng B1. `Readout` guard được dùng cho toàn bộ số Sentinel.

## 3. Phát hiện chính (đáng lưu ý cho thầy)

**Trong lần chạy DEV này, Sentinel KHÔNG hạ worst-case harm so với B1 — H1 bị BÁC ở mọi ρ,**
và khoảng cách xấu đi mạnh khi ρ tăng. Nguyên nhân cơ học: khi ρ→1 mọi payload đi qua commit,
audit-at-commit (B1) bắt gần hết (V giảm 0.79→0.20), trong khi các chính sách phân bổ (kể cả
Sentinel) giữ nguyên ~0.75–0.82 vì cột worst-case (attacker chọn carrier/Δ) vẫn hở. Đây là
phân kỳ draft-vs-run thực chất (draft chiếu B1≈0.412, Sentinel≈0.272, gain +27.6%). **Cần thầy
xem lại** trước khi lấp vào paper (theo quy tắc: kết quả có thể đổi ⇒ hỏi).

## 4. Table 2 — headline (Δ∈{4,8}), gain vs B1 (wild-cluster CI), theo ρ

Worst-case harm V [95% CI]; gain% vs B1 [95% CI]; clean compl.%, FQ% (item-level), det.delay.
Exploitability & regret vs B7 = **TBD** (cần br block / B7).

### ρ = 0.0
| Hệ | V [CI] | gain% vs B1 [CI] | clean% | FQ% | delay |
|---|---|---|---|---|---|
| B1 | 0.787 [0.735, 0.892] | — | 90.4 | 0.0 | 5.0 |
| B2 | 0.811 [0.726, 0.900] | −3.1 | 97.3 | 59.3 | 1.3 |
| B3 | 0.858 [0.817, 0.947] | −9.0 | 100.0 | 59.0 | 0.0 |
| B4 | 0.879 [0.844, 0.953] | −11.7 | 100.0 | 41.9 | 1.1 |
| B5 | 0.792 [0.726, 0.873] | −0.6 | 97.4 | 57.6 | 1.0 |
| B6 | 0.858 [0.799, 0.942] | −9.0 | 100.0 | 34.8 | 1.9 |
| cost-greedy | 0.858 [0.784, 0.932] | −9.0 | 99.0 | 63.3 | 1.1 |
| SW randomised | 0.783 [0.707, 0.884] | +0.6 | 95.0 | 45.9 | 1.9 |
| **Sentinel** | **0.821 [0.762, 0.906]** | **−4.3 [−11.2, +4.8]** | 98.6 | 17.5 | 2.1 |

### ρ = 0.25
| Hệ | V [CI] | gain% vs B1 | clean% | FQ% | delay |
|---|---|---|---|---|---|
| B1 | 0.646 [0.614, 0.765] | — | 90.4 | 0.0 | 5.1 |
| **Sentinel** | **0.792 [0.703, 0.905]** | **−22.6 [−32.3, −3.4]** | 98.7 | 16.4 | 2.1 |

### ρ = 0.5
| Hệ | V [CI] | gain% vs B1 | clean% | FQ% | delay |
|---|---|---|---|---|---|
| B1 | 0.512 [0.450, 0.618] | — | 90.4 | 0.0 | 4.9 |
| **Sentinel** | **0.750 [0.678, 0.837]** | **−46.4 [−62.2, −25.9]** | 99.2 | 17.9 | 1.8 |

### ρ = 1.0
| Hệ | V [CI] | gain% vs B1 | clean% | FQ% | delay |
|---|---|---|---|---|---|
| B1 | 0.197 [0.138, 0.264] | — | 90.4 | 0.0 | 5.1 |
| B2 | 0.565 [0.549, 0.653] | −187.1 | 97.3 | 59.3 | 1.3 |
| SW randomised | 0.476 [0.417, 0.586] | −141.8 | 95.0 | 45.9 | 2.0 |
| **Sentinel** | **0.774 [0.692, 0.854]** | **−292.9 [−483.2, −178.9]** | 98.8 | 17.2 | 1.8 |

*(bảng đầy đủ 14 hệ × 4 ρ + 7 metric S9.3 trong `table2_3.json`.table2)*

## 5. Table 3 — Ablations (worst-case harm V [CI], headline, theo ρ)

| Biến thể | ρ=0 | ρ=0.25 | ρ=0.5 | ρ=1 | FQ% (ρ=0→1) |
|---|---|---|---|---|---|
| Full Sentinel | 0.821 | 0.792 | 0.750 | 0.774 | 17.5→17.2 |
| − randomization | 0.827 | 0.774 | 0.744 | 0.762 | 18.5→18.7 |
| − alarm memory | 0.815 | 0.810 | 0.756 | 0.774 | 13.3→15.1 |
| − benign-drift | 0.821 | 0.811 | 0.780 | 0.744 | 23.1→24.0 |
| [dhat=oracle] (arm tham chiếu) | 0.821 | 0.804 | 0.750 | 0.762 | 17.6→17.2 |
| − transition uncertainty | **TBD** | **TBD** | **TBD** | **TBD** | (không có mặt) |

Các ablation gần như không tách khỏi Full Sentinel (CI chồng lấp); −benign-drift luôn FQ cao
nhất. Toàn bộ ablation và Full Sentinel vẫn kém B1. (Delta so với Full Sentinel & CI trong JSON.)

## 6. Endpoint (H1) — reduction Sentinel vs B1, held-out, headline

| ρ | Draft | Đo được (gain% [CI]) | AbsDiff | G (H1) | P (H1) |
|---|---|---|---|---|---|
| 0    | 27.6 | −4.3 [−11.2, +4.8] | −0.034 | **bác** | **bác** |
| 0.25 | 27.6 | −22.6 [−32.3, −3.4] | −0.146 | **bác** | **bác** |
| 0.5  | 27.6 | −46.4 [−62.2, −25.9] | −0.238 | **bác** | **bác** |
| 1    | 27.6 | −292.9 [−483.2, −178.9] | −0.577 | **bác** | **bác** |

(rel_reliable=True ở mọi ρ; base_events 104/38/30/20.)

## 7. H-verdicts đã chấm (score_all, BH q=0.05, theo ρ)

| H | Rule | Kết quả (ρ=0 / .25 / .5 / 1) | Ghi chú |
|---|---|---|---|
| **H1** | G + P (gain_heldout) | **bác / bác / bác / bác** | Sentinel không hạ harm vs B1 trên dev |
| **H4** | P (gain@Δ=0) | không kết luận / bác / bác / bác | proj −1.2%; đo −4.9/−31.7/−75.4/−267.3% |
| **H6** | D (cost-greedy − uniform random) | **khớp / khớp / khớp / khớp** | cost-greedy tệ hơn uniform random (BH-reject) |
| **H10** | P (clean%, FQ%) | không kết luận (mọi ρ) | Q12 không khai báo margin cho % ⇒ chỉ báo điểm; CI side-metric = TBD |
| **H12** | P (−rand/−alarm/−drift V) | **bác** (mọi ρ) | proj 0.456/0.371/0.264, đo ~0.75–0.83 (≫) |
| H12 | P (−transition V) | chưa chạy (NOT_RUN) | hệ không có mặt |
| H12 | P (fq_pct_minus_drift) | không kết luận | không có margin (Q12) |
| H12 | D (−rand − B1) | không kết luận / khớp / khớp / khớp | ở ρ≥.25, −randomization tệ hơn B1 (BH-reject) |

## 8. H-verdicts để TBD (cần block khác — N3, không bịa)

| H | Cần gì (không có trong main-block) |
|---|---|
| H2 | cột attacker **tuning/dev** (main chỉ có held-out) |
| H3 | trục **χ** + trục Δ liên tục cho crossover + arm price-only |
| H5 | arm **heterogeneous vs uniform** (không phải một ô của main) |
| H7 | **B7** + 240 small games + covering-radius TV |
| H8 | composite **max-over-others** + framing ingress-visible world |
| H9 | **exploitability** → br block (0 record có `placement`) |
| H11 | **LLM attackers** (main chỉ có scripted) |
| H13 | trục **d′** (main chỉ 1 detector) |
| H14 | trục **η_Q** (quarantine cost) |
| H15 | CI cho **hiệu FQ%** — `gain_ci` chỉ chạy field=harm; không có code path FQ-diff |
| H16 | br carrier spread → **br block** |
| H17 | composite **nửa-benefit** (SW vs ½·Sentinel) — không có code path riêng |
| H18 | **h18 block**: cần policy `block-schedule` (vắng ở main) + các mức budget 2/1/0.5×Bmin (main chỉ b1) |
| H19 | trục **K_d** (main chỉ K_d=2) |
| H20 | cột **attacker-chooses-Δ** (không có trong records) |

**Metric để TBD vì cần br/rollout/eval:**
- **Exploitability** (cột 5 Table 2, H9): cần br block — `placement` = null trong mọi record.
- **Regret vs B7** (metric S9.3 thứ 7): B7 vắng (T21).
- **table-rollout fidelity** (T17): `line5_source` chỉ có `table`/None, **không có `rollout`** ⇒ TBD.
- Mọi số eval P5 held-out: block khác (đây là DEV).

## 9. Paper fill-map (chỉ đề xuất giá trị; KHÔNG sửa paper)

59 tham chiếu paper mà run này lấp được. Bản đầy đủ ở `table2_3.json`.fill_map_text.
Tóm tắt các vị trí:

- `results.tex:47–92` — Table 2 (tab:main) panel B–E: worst-case harm [CI] | clean% | FQ% | delay
  cho 9 hệ × 4 ρ (cột exploit = TBD br; hàng B7 = TBD).
- `results.tex:108–112` — Table 3 (tab:ablations): harm đo theo ρ (hàng −transition = TBD).
- `results.tex:256–259` — Table endpoint: gain[CI] | AbsDiff | G | P (đều **bác**).
- `results.tex:124` — controls PASS (Oracle=0.000; neg control OK mọi ρ).
- `results.tex:135` — RQ2: gain per ρ (−4.3/−22.6/−46.4/−292.9%), gate = REJECT.
- `results.tex:165` — RQ1 Δ=0: gain@Δ0 per ρ (−4.9/−31.7/−75.4/−267.3%).
- `results.tex:233–238` — RQ2 prose: B1/Sentinel V per ρ, clean~98.6–99.2 vs 90.4, FQ~16–18 vs 0, H6=MATCH.
- `results.tex:291` — RQ4/H12: ablation harm ≫ draft; −benign-drift FQ cao nhất.
- `hypotheses.tex:55 (H1), :34 (H4), :58 (H6), :61 (H10), :78 (H12)` — Measured + Verdict.
- TBD (không lấp): H2,H3,H5,H7,H8,H9,H11,H13,H14,H15,H16,H17,H18,H19,H20 (§8).

## 10. Artefact

- `spikes/v3-run/dev-headline-main/table2_3.json` — máy đọc: meta, controls, table2 (14 hệ×4 ρ×7 metric),
  table3_ablations, endpoint, hverdicts (mọi H, mọi ρ), fill_map_text.
- Chưa stage/commit gì (thầy review & commit).
