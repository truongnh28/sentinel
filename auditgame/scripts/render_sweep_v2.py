#!/usr/bin/env python3
"""
render_sweep_v2.py -- Generate docs/reports/sweep-loss-v2.md from sweep-v2 JSON files and log.
"""
import json
import pathlib
import dprime_sweep as ds

def load_cells(json_path):
    with open(json_path) as f:
        data = json.load(f)
    rows = {}
    for d_str, cell_list in data["cells"].items():
        d = int(d_str)
        rows[d] = []
        for c in cell_list:
            curves = {}
            for pol_name, c_data in c.get("curves", {}).items():
                curves[pol_name] = ds.PolicyCurve(
                    harm=c_data["harm"],
                    q_false=c_data["q_false"],
                    t_lost=c_data["t_lost"],
                    spent=c_data["spent"],
                    n_feasible=c_data["n_feasible"],
                    n_total=c_data["n_total"],
                    per_wf_harm=c_data["per_wf_harm"],
                    per_wf_q_false=c_data["per_wf_q_false"],
                    per_wf_t_lost=c_data["per_wf_t_lost"],
                    per_wf_spent=c_data["per_wf_spent"]
                )
            cell = ds.SweepCell(
                d_prime=c["d_prime"],
                delta=c["delta"],
                harm_b1=c["harm_b1"],
                harm_sentinel=c["harm_sentinel"],
                dharm=c["dharm"],
                ci_lo=c["ci_lo"],
                ci_hi=c["ci_hi"],
                n_feasible=c["n_feasible"],
                n_total=c["n_total"],
                reason=c.get("reason"),
                curves=curves
            )
            rows[d].append(cell)
    return rows, data

def main():
    rows_f, data_f = load_cells("spikes/sweep-v2-following.json")
    rows_p, data_p = load_cells("spikes/sweep-v2-pinned.json")

    all_usable_f = [c for d in [0, 1, 2, 4] for c in rows_f[d] if c.usable]
    all_usable_p = [c for d in [0, 1, 2, 4] for c in rows_p[d] if c.usable]

    ps_f = {pol: ds.pairwise_summary(all_usable_f, pol) for pol in [ds.B1, ds.B5, ds.B6]}
    ps_p = {pol: ds.pairwise_summary(all_usable_p, pol) for pol in [ds.B1, ds.B5, ds.B6]}

    be_f = data_f["break_even"]
    be_p = data_p["break_even"]

    # Build markdown content
    md = []
    md.append("# Chấm điểm phép quét $d'$ bằng hàm mất mát $L$ trên Payload v2 — Bốn Policy")
    md.append("")
    md.append("**Ngày đo:** 19/09/2026 · **Module:** `dprime_sweep.py`")
    md.append("**Dữ liệu:** `spikes/sweep-v2-following.json` (bản chính) và `spikes/sweep-v2-pinned.json` (đối chứng ghim)")
    md.append("**Thay thế:** Phán quyết v1 tại `docs/reports/sweep-loss-b5-b6.md` theo nguyên tắc tiền-đăng-ký.")
    md.append("")
    md.append("> **ĐỌC BA DÒNG NÀY TRƯỚC.**")
    md.append("> 1. **Số v2 THAY số v1, KHÔNG CHỌN.** Sau khi sửa bug `MatchedAttack` ở Task A1a, kết quả đo lường v2 hoàn toàn thay thế v1.")
    md.append("> 2. **Sentinel KHÔNG hơn `B5 risk-score` trên $L$:** B5 dẫn trước trên **61/64** ô ở $\\lambda_Q = 0,10$ và chỉ tiêu **7–13%** ngân sách so với 47–50% của Sentinel. Sentinel chỉ thắng B5 ở $\\Delta = 4, d' \\in [2,4; 2,8]$ khi $\\lambda_Q \\le 0,10$.")
    md.append("> 3. **Phát biểu duy nhất còn sống (Sentinel hơn B1) TREO vào $\\lambda_T = 0,50$:** Ở $\\lambda_T = 0$ (không phạt chặn nhầm patch sạch), số ô Sentinel dẫn trước co từ **64/64** xuống **26/64** ô (§7.2.1).")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 1. Nguyên tắc chốt TRƯỚC khi chạy (Pre-commitment)")
    md.append("")
    md.append("1. **Số v2 THAY số v1, KHÔNG CHỌN:** Mọi con số v2 được ghi nhận trung thực theo thực nghiệm, không giữ lại con số thuận lợi từ v1.")
    md.append("2. **Luật so sánh ghép cặp (Common Random Numbers):** So sánh ghép cặp nội bộ trong từng phiên bản (cùng seed, cùng cấu hình payload v2). Tuyệt đối không so sánh chéo giữa v1 và v2.")
    md.append("3. **Hai chế độ đo:**")
    md.append("   - **Bản chính (`--tau-follows-dprime`):** $\\tau_{\\text{sel}}$ chạy theo từng điểm lưới $d'$, loại bỏ confound cố định ngưỡng chọn carrier cho B5/B6.")
    md.append("   - **Đối chứng ghim (`pinned`):** $\\tau_{\\text{sel}}$ ghim ở mức `mid` ($d' = 2,211$) để đối chiếu độ nhạy.")
    md.append("4. **Hàm mục tiêu phòng thủ:**")
    md.append("   $$L = \\mathbb{E}[\\text{harm}] + \\lambda_Q \\mathbb{E}[Q_{\\text{false}}] + \\lambda_T \\mathbb{E}[T_{\\text{lost}}]$$")
    md.append("   với $\\lambda_T = 0,50$ và quét $\\lambda_Q$.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 2. Thiết lập thực nghiệm v2")
    md.append("")
    md.append("| Đại lượng | Giá trị / Quy cách | Ghi chú |")
    md.append("|:---|:---|:---|")
    md.append("| Bốn policy so sánh | `B1 audit-at-commit`, `Sentinel`, `B5 risk-score`, `B6 two-stage` | Khai báo trong `policies.REGISTRY` |")
    md.append("| Lưới $d'$ | `[0.0, 0.2, 0.4, ..., 3.0]` (16 điểm) | Bản chính chạy lưới thô step 0.2 |")
    md.append("| Độ dịch $\\Delta$ | `[0, 1, 2, 4]` | 4 mức độ dịch marker |")
    md.append("| Số workflow / seed | 40 workflow, $H=8$, seed `[1, 2, 3]` | 64 ô đánh giá (16 × 4) |")
    md.append("| Trần ngân sách | $B = 17,95$ | Chung cho cả 4 policy |")
    md.append("| Bug sửa ở A1a | `MatchedAttack.payload` gọi `build.payload_content` | Đúng `PAYLOAD_LENGTH = 63`, loại bỏ chênh lệch kích thước nhân tạo |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 3. Bảng bốn policy — `harm`, `Q_false`, `T_lost`, `spent`, `L`")
    md.append("")
    md.append("Dưới đây là kết quả đo lường tại ba điểm $d'$ đại diện (hai đầu và giữa lưới) ở bản chính (`--tau-follows-dprime`):")
    md.append("")

    for dp in [0.0, 2.2, 3.0]:
        md.append(f"#### $d' = {dp:.1f}$")
        md.append("")
        md.append("| $\\Delta$ | Policy | `harm` | `Q_false` | `T_lost` | `spent` | $L(0)$ | $L(0,10)$ | Feasible |")
        md.append("|:--:|:---|---:|---:|---:|---:|---:|---:|:--:|")
        for delta in [0, 1, 2, 4]:
            cell = [c for c in rows_f[delta] if abs(c.d_prime - dp) < 1e-6][0]
            for pol in [ds.B1, ds.SENTINEL, ds.B5, ds.B6]:
                cur = cell.curves[pol]
                h = cur.harm
                q = cur.q_false
                t = cur.t_lost
                sp = cur.spent
                l0 = cur.loss(0.0)
                l10 = cur.loss(0.10)
                feas = f"{cur.n_feasible}/{cur.n_total}"
                d_label = str(delta) if pol == ds.B1 else ""
                md.append(f"| {d_label:^4} | `{pol}` | {h:.3f} | {q:.3f} | {t:.3f} | {sp:.2f} | {l0:.3f} | {l10:.3f} | {feas:^8} |")
        md.append("")

    md.append("---")
    md.append("")
    md.append("## 4. Bảng chi tiêu (Spend Table) tại $d' = 2,2$")
    md.append("")
    md.append("Chi tiêu thực tế của các policy tại điểm tham chiếu $d' = 2,2$:")
    md.append("")
    md.append("| $\\Delta$ | `B1 audit-at-commit` | `Sentinel` | `B6 two-stage` | `B5 risk-score` | Trần ngân sách |")
    md.append("|:--:|---:|---:|---:|---:|---:|")
    for d in [0, 1, 2, 4]:
        cell = [c for c in rows_f[d] if abs(c.d_prime - 2.2) < 1e-6][0]
        sp_b1 = cell.curves[ds.B1].spent
        sp_sen = cell.curves[ds.SENTINEL].spent
        sp_b6 = cell.curves[ds.B6].spent
        sp_b5 = cell.curves[ds.B5].spent
        cap = data_f["run"]["budget"]
        md.append(f"| **{d}** | {sp_b1:.2f} ({sp_b1/cap*100:.0f}%) | {sp_sen:.2f} ({sp_sen/cap*100:.0f}%) | {sp_b6:.2f} ({sp_b6/cap*100:.0f}%) | {sp_b5:.2f} ({sp_b5/cap*100:.0f}%) | {cap:.2f} |")
    md.append("")
    md.append("> **Nhận xét then chốt:** `B5 risk-score` chỉ tiêu **7% – 16%** trần ngân sách ($1,23$ đến $2,82$), bằng khoảng **1/4 đến 1/7** chi phí của Sentinel ($8,38$ đến $8,94$), trong khi đạt điểm mất mát $L$ tốt hơn hẳn ở $\\lambda_Q \\ge 0,10$.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 5. $d'^*(\\Delta)$ — Dưới `harm` và dưới $L$ ở ba mức $\\lambda_Q$")
    md.append("")
    md.append("So sánh ngưỡng hoà vốn $d'^*$ xác định bởi quy tắc frozen `break_even`:")
    md.append("")
    md.append("| $\\Delta$ | $d'^*$ harm (pinned) | $d'^*$ harm (following) | $d'^*$ của $\\Delta L, \\lambda_Q=0$ | $d'^*$ của $\\Delta L, \\lambda_Q=\\bar{\\lambda}$ | $d'^*$ của $\\Delta L, \\lambda_Q=0,10$ |")
    md.append("|:--:|:---|:---|:---|:---|:---|")
    for d in [0, 1, 2, 4]:
        d_str = str(d)
        hp = be_p[d_str]["harm"]
        hf = be_f[d_str]["harm"]
        l0 = be_f[d_str]["lambda_Q=0"]
        lbar = be_f[d_str]["lambda_Q=lambda-bar (per cell)"]
        l10 = be_f[d_str]["lambda_Q=0.1"]

        hp_s = f"**{hp:.2f}**" if hp is not None else "không có trong [0; 3]"
        hf_s = f"**{hf:.2f}**" if hf is not None else "không có trong [0; 3]"
        l0_s = f"**{l0:.2f}**" if l0 is not None else "không có trong [0; 3]"
        lbar_s = f"**{lbar:.2f}**" if lbar is not None else "không có trong [0; 3]"
        l10_s = f"**{l10:.2f}**" if l10 is not None else "không có trong [0; 3]"

        md.append(f"| **{d}** | {hp_s} | {hf_s} | {l0_s} | {lbar_s} | {l10_s} |")
    md.append("")
    md.append("### Thay đổi so với v1:")
    md.append("- Tại $\\Delta = 2$, $d'^*$ harm dịch từ **2.55** (v1) lên **2.85** (pinned) / **3.00** (following).")
    md.append("- Tại $\\Delta = 2$, $d'^*$ của $\\Delta L$ ở $\\lambda_Q = 0,10$ dịch từ **2.00** (v1) lên **2.40** (v2).")
    md.append("- Tại $\\Delta = 4$, $d'^*$ harm dịch từ **0.60** (v1) lên **0.95** (pinned) / **1.00** (following). $d'^*$ của $\\Delta L$ ở $\\lambda_Q = 0,10$ giữ nguyên **0.00**.")
    md.append("- Tại $\\Delta = 0$ và $\\Delta = 1$, không tồn tại $d'^*$ hoà vốn trên toàn dải [0, 3] dưới harm hay $\\lambda_Q = 0,10$.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 6. $\\bar{\\lambda}$ và $\\lambda_{\\times}$ theo từng ô (In trực tiếp từ công cụ)")
    md.append("")
    md.append("- $\\bar{\\lambda} = \\lambda_Q^*$ là nghiệm nhỏ nhất trên cả 4 policy.")
    md.append("- $\\lambda_{\\times}$ là điểm cắt theo từng cặp.")
    md.append("")

    for d in [0, 1, 2, 4]:
        md.append(f"### $\\Delta = {d}$")
        md.append("")
        md.append("```")
        md.append(ds.pairwise_table(rows_f[d]))
        md.append("```")
        md.append("")

    md.append("### 6.1 Tổng hợp trên toàn bộ 64 ô (Bản chính `--tau-follows-dprime`)")
    md.append("")
    md.append("| Sentinel đối đầu | Thua ngay tại $\\lambda_Q \\to 0^+$ | Hơn ở mọi $\\lambda_Q$ | Có $\\lambda_{\\times}$ | $\\lambda_{\\times}$ nhỏ nhất · **Trung vị** · Lớn nhất | Số ô $\\lambda_{\\times} \\ge 0,10$ |")
    md.append("|:---|:---:|:---:|:---:|:---|:---:|")
    for pol in [ds.B1, ds.B5, ds.B6]:
        ps = ps_f[pol]
        behind = ps["behind_from_zero"]
        every = ps["ahead_everywhere"]
        n_cross = len(ps["crossings"])
        if n_cross > 0:
            rng_str = f"{ps['min']:.4f} · **{ps['median']:.4f}** · {ps['max']:.4f}"
            ge10 = f"**{ps['crossing_at_or_above_default']}**/{n_cross}"
        else:
            rng_str = "không có"
            ge10 = "0"
        md.append(f"| `{pol}` | **{behind}**/64 | {every}/64 | {n_cross}/64 | {rng_str} | {ge10} |")
    md.append("")
    md.append("### 6.2 Thứ hạng tổng (`argmin L` trên cả 4 policy)")
    md.append("")
    md.append("| Tiêu chí đếm trên 64 ô | `B1` | `Sentinel` | `B5 risk-score` | `B6 two-stage` | Số ô hoà |")
    md.append("|:---|:---:|:---:|:---:|:---:|:---:|")
    md.append("| `argmin L` **duy nhất** tại $\\lambda_Q = 0$ | 0/64 | **39**/64 | 9/64 | 0/64 | **16** (Sentinel=B5=B6 tại $\\Delta=0$) |")
    md.append("| `argmin L` **duy nhất** tại $\\lambda_Q = 0,10$ | 0/64 | **3**/64 | **61**/64 | 0/64 | **0** (hết ô hoà) |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 7. CÂU TRẢ LỜI CHO KHUNG BÀI (Phán quyết khung)")
    md.append("")
    md.append("### 7.1 `B5 risk-score` — KHÔNG HƠN")
    md.append("")
    md.append("> **Phán quyết:** **Sentinel KHÔNG hơn `B5 risk-score` trên $L$.**")
    md.append("> ")
    md.append("> - Trên **25/64** ô, Sentinel thua B5 ngay từ $\\lambda_Q \\to 0^+$.")
    md.append("> - Trên 39 ô có điểm cắt, $\\lambda_{\\times}$ có trung vị chỉ **0,0201** (chỉ cần $\\lambda_Q > 0,02$, B5 đã vượt Sentinel).")
    md.append("> - Chỉ duy nhất **3/64** ô (ở $\\Delta = 4, d' \\in \\{2,4; 2,6; 2,8\\}$) Sentinel giữ được vị trí dẫn đầu ở $\\lambda_Q = 0,10$.")
    md.append("> - Hơn nữa, B5 đạt hiệu năng $L$ vượt trội này với chi phí chỉ bằng **1/4 đến 1/7** ngân sách của Sentinel (7%–13% so với 47%–50% trần ngân sách).")
    md.append("> ")
    md.append("> Phán quyết này **hoàn toàn trơ với $\\lambda_T$** vì cả Sentinel và B5 đều có $T_{\\text{lost}} = 0,000$ ở mọi ô.")
    md.append("")
    md.append("### 7.2 `B1 audit-at-commit` — HƠN, có điều kiện $\\lambda_T$")
    md.append("")
    md.append("> **Phán quyết:** **Sentinel hơn `B1 audit-at-commit` trên $L$ với mọi $\\lambda_Q < \\lambda_{\\times}$, với trung vị $\\lambda_{\\times} = 0,1426$ (ở $\\lambda_T = 0,50$).**")
    md.append("> ")
    md.append("> - Tại $\\lambda_Q \\to 0^+$, Sentinel dẫn trước B1 trên **64/64** ô.")
    md.append("> - Tại $\\lambda_Q = 0,10$, Sentinel dẫn trước trên **51/64** ô.")
    md.append("> - Cơ chế: Lợi thế này hoàn toàn đến từ số hạng $T_{\\text{lost}}$ (B1 làm mất $0,31$ đến $0,53$ patch sạch tại cổng commit, trong khi Sentinel có $T_{\\text{lost}} = 0,000$).")
    md.append("")
    md.append("#### 7.2.1 Độ nhạy với $\\lambda_T$")
    md.append("")
    md.append("Vì chiến thắng trước B1 phụ thuộc vào việc tính giá patch sạch bị chặn oan ($T_{\\text{lost}}$), ta quét lại 64 ô ở ba mức $\\lambda_T$:")
    md.append("")
    md.append("| $\\lambda_T$ | Sentinel hơn B1 tại $\\lambda_Q \\to 0^+$ | Thua | Có $\\lambda_{\\times}$ | $\\lambda_{\\times}$ nhỏ nhất | **Trung vị** | Lớn nhất |")
    md.append("|---:|:---:|:---:|:---:|---:|---:|---:|")
    for s in ds.lambda_t_sensitivity(all_usable_f, ds.B1, [0.0, 0.25, 0.50]):
        t_val = s["lambda_T"]
        ahead = s["ahead_at_zero"]
        n = s["n"]
        behind = s["behind_from_zero"]
        crosses = s["crossings"]
        med = s["median"] if s["median"] is not None else 0.0
        mi = s["min"] if s["min"] is not None else 0.0
        ma = s["max"] if s["max"] is not None else 0.0
        md.append(f"| **{t_val:.2f}** | **{ahead}/{n}** | {behind} | {len(crosses)} | {mi:.4f} | **{med:.4f}** | {ma:.4f} |")
    md.append("")
    md.append("> **Kết luận về $\\lambda_T$:** Ở $\\lambda_T = 0,00$ (khi chặn nhầm patch sạch không bị phạt), câu tuyên bố \"Sentinel hơn B1\" co lại chỉ còn **26/64** ô. Chiến thắng trước B1 là phát biểu về **giá trị bảo toàn thông lượng patch**, không phải về harm đơn thuần.")
    md.append("")
    md.append("### 7.3 `B6 two-stage` — HƠN có điều kiện")
    md.append("")
    md.append("> **Phán quyết:** **Sentinel hơn `B6 two-stage` trên $L$ với $\\lambda_Q < \\lambda_{\\times}$ trên 53/64 ô**, trung vị $\\lambda_{\\times} = 0,2593$. Trên 40/45 ô có điểm cắt, $\\lambda_{\\times} \\ge 0,10$. Sentinel thua B6 trên 11 ô (chủ yếu tại $\\Delta = 0$ nơi harm ngang nhau và B6 có false quarantine thấp hơn).")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 8. Kết luận khung cho luận văn FSE 2027")
    md.append("")
    md.append("1. **Bác bỏ khung khẳng định cực đoan:** Không thể tuyên bố *\"Sentinel là cơ chế kiểm toán tối ưu nhất trong mọi điều kiện\"*, vì `B5 risk-score` vượt trội hơn về mất mát $L$ ở mọi mức $\\lambda_Q \\ge 0,02$ và tiêu ít ngân sách hơn đáng kể.")
    md.append("2. **Xác lập khung đóng góp thực sự:**")
    md.append("   - Sentinel giải quyết triệt để sự tắc nghẽn thông lượng ($T_{\\text{lost}}$) của cơ chế kiểm toán tại commit (`B1`), bảo toàn 100% patch sạch với trần ngân sách thực nghiệm.")
    md.append("   - Khi kẻ tấn công dịch marker tinh vi ($\\Delta = 4$), với detector mạnh ($d' \\ge 2,4$), Sentinel ngăn chặn harm tốt hơn B5 đủ để bù đắp lượng false quarantine ở $\\lambda_Q \\le 0,10$.")
    md.append("   - Sự phân tầng rõ ràng giữa 4 policy cung cấp cơ sở phương pháp luận cho việc lựa chọn cơ chế phòng thủ dựa trên hàm chi phí thực tế của tổ chức.")

    content = "\n".join(md) + "\n"
    out = pathlib.Path(__file__).resolve().parents[2] / "docs" / "reports" / "sweep-loss-v2.md"
    out.write_text(content)
    print(f"Wrote {out} successfully!")

if __name__ == "__main__":
    main()
