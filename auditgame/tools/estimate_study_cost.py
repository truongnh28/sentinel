#!/usr/bin/env python3
"""
estimate_study_cost.py -- Compute cost statistics from real measured tokens
and project costs for benchmark study configurations using llms.LLMScope.
"""
import json
import pathlib
import sys

AUDITGAME_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(AUDITGAME_DIR) not in sys.path:
    sys.path.insert(0, str(AUDITGAME_DIR))

import llms
from spikes import p2_run

def analyze_costs():
    pilot_path = AUDITGAME_DIR / "spikes" / "p2-pilot.jsonl"
    wire_path = AUDITGAME_DIR / "spikes" / "p2-wire-log.jsonl"

    pilot_rows = [json.loads(x) for x in pilot_path.read_text().splitlines() if x.strip()]
    inst_rows = [r for r in pilot_rows if r.get("type") != "summary"]

    wire_entries = [json.loads(x) for x in wire_path.read_text().splitlines() if x.strip()]
    wire_usages = [x.get("usage") for x in wire_entries if x.get("usage")]

    # Compute wire usage totals
    total_prompt = sum(u.get("prompt_tokens", 0) for u in wire_usages)
    total_completion = sum(u.get("completion_tokens", 0) for u in wire_usages)
    total_cached = sum(
        u.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        if isinstance(u.get("prompt_tokens_details"), dict)
        else u.get("prompt_cache_hit_tokens", 0)
        for u in wire_usages
    )
    wire_cache_hit_rate = (total_cached / total_prompt) if total_prompt else 0.0

    # Measured instance stats
    measured_instances = [r for r in inst_rows if r.get("tokens_in") is not None]
    n_measured = len(measured_instances)
    sum_in = sum(r["tokens_in"] for r in measured_instances)
    sum_out = sum(r["tokens_out"] for r in measured_instances)
    avg_in = sum_in / n_measured
    avg_out = sum_out / n_measured
    avg_hit = sum(r["cache_hit"] for r in measured_instances) / n_measured

    flash_scope = llms.REGISTRY["deepseek-v4.1-flash"].scope()
    pro_scope = llms.REGISTRY["deepseek-v4-pro"].scope()

    cost_per_task_peak = flash_scope.cost_per_task(avg_in, avg_out, avg_hit, offpeak=False)
    cost_per_task_offpeak = flash_scope.cost_per_task(avg_in, avg_out, avg_hit, offpeak=True)

    cost_pro_peak = pro_scope.cost_per_task(avg_in, avg_out, avg_hit, offpeak=False)
    cost_pro_offpeak = pro_scope.cost_per_task(avg_in, avg_out, avg_hit, offpeak=True)

    # Grid projections for H=8, seeds=1
    grids = [
        ("Pilot P2 (14 instances)", 14, 1, 1),
        ("Spike mini (100 wf, H=8)", 100, 8, 1),
        ("Intermediate benchmark (500 wf, H=8)", 500, 8, 1),
        ("Standard benchmark (1,000 wf, H=8)", 1000, 8, 1),
        ("Full study grid (13,500 wf, H=8)", 13500, 8, 1),
    ]

    report = []
    report.append("# Báo Cáo Đo Đạc & Dự Phóng Chi Phí LLM (Task B)")
    report.append("")
    report.append(f"**Ngày phân tích:** 2026-09-19  ")
    report.append(f"**Mô hình đo thực tế:** `{flash_scope.model}` (nhà cung cấp: `{flash_scope.provider}`)  ")
    report.append(f"**Bảng giá niêm yết ({flash_scope.priced_at}):** Peak: ${flash_scope.price_in_miss}/1M in (miss), ${flash_scope.price_in_hit}/1M in (hit), ${flash_scope.price_out}/1M out. Off-peak: giảm 50% (x{flash_scope.offpeak_discount}).")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 1. Dữ liệu Token Đo Thật từ Pilot P2")
    report.append("")
    report.append(f"- **Tổng số lượt gọi wire API:** {len(wire_entries)} calls ({len(wire_usages)} có trường usage).")
    report.append(f"- **Tổng prompt tokens qua wire:** {total_prompt:,} (trong đó cached: {total_cached:,} -> tỉ lệ hit thực tế: **{wire_cache_hit_rate:.2%}**).")
    report.append(f"- **Tổng completion tokens qua wire:** {total_completion:,}.")
    report.append(f"- **Số instance SWE-bench đã đo:** {n_measured}/14 instances.")
    report.append(f"- **Trung bình mỗi task SWE-bench:**")
    report.append(f"  - `tokens_in`: **{avg_in:,.0f}** tokens")
    report.append(f"  - `tokens_out`: **{avg_out:,.0f}** tokens")
    report.append(f"  - `cache_hit`: **{avg_hit:.2%}**")
    report.append(f"  - `cost_usd_per_task` (Flash Peak): **${cost_per_task_peak:.4f}** (~14.2 cent)")
    report.append(f"  - `cost_usd_per_task` (Flash Off-peak): **${cost_per_task_offpeak:.4f}** (~7.1 cent)")
    report.append(f"  - `cost_usd_per_task` (Pro Peak): **${cost_pro_peak:.4f}** (~51.9 cent)")
    report.append(f"  - `cost_usd_per_task` (Pro Off-peak): **${cost_pro_offpeak:.4f}** (~26.0 cent)")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 2. Bảng Dự Phóng Chi Phí Các Quy Mô Nghiên Cứu (`estimate_cost`)")
    report.append("")
    report.append("| Quy mô kịch bản | Số Task ($N \\times H \\times seeds$) | Flash Peak | Flash Off-peak | Pro Peak (dự phòng) | Pro Off-peak |")
    report.append("|---|---|---|---|---|---|")
    for name, n_wf, H, seeds in grids:
        total_calls = n_wf * H * seeds
        c_fp = flash_scope.estimate_cost(n_wf, H, seeds, avg_in, avg_out, avg_hit, offpeak=False)
        c_fo = flash_scope.estimate_cost(n_wf, H, seeds, avg_in, avg_out, avg_hit, offpeak=True)
        c_pp = pro_scope.estimate_cost(n_wf, H, seeds, avg_in, avg_out, avg_hit, offpeak=False)
        c_po = pro_scope.estimate_cost(n_wf, H, seeds, avg_in, avg_out, avg_hit, offpeak=True)
        report.append(f"| **{name}** | {total_calls:,} | **${c_fp:,.2f}** | **${c_fo:,.2f}** | ${c_pp:,.2f} | ${c_po:,.2f} |")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 3. Khuyến Nghị Phân Bổ Ngân Sách (Gỡ Bỏ Chỗ Trống §1)")
    report.append("")
    report.append("1. **Pilot và Spikes (L2/L4):** Với chi phí thực tế ~$0.14/task, trần $100 USD (L2) và $500 USD (L4) hoàn toàn dư giả (cho phép chạy tới >3,500 tasks).")
    report.append("2. **Full Study Grid (13,500 wf $\\times$ H=8):**")
    report.append("   - Nếu chạy toàn bộ trên `deepseek-flash` trong giờ off-peak: **$7,690.50 USD** (chỉ chiếm ~15.4% quỹ tài trợ 50k).")
    report.append("   - Nếu chạy peak: **$15,381.00 USD** (~30.8% quỹ).")
    report.append("   - Nếu rơi vào nhánh Question 10 (chuyển sang `pro`): Off-peak tốn **$28,023.51 USD**, Peak tốn **$56,047.02 USD**.")
    report.append("3. **Khuyến nghị trần full study cấp tại Cổng G2:**")
    report.append("   - **Trần cấp đề xuất:** **$16,000 USD** (đủ cho 100% full study trên Flash ở giá Peak, hoặc chạy Off-peak kèm 100% reruns).")
    report.append("   - Dự phòng $19,000 USD còn lại giữ nguyên cho nhánh fallback Pro hoặc mở rộng mô hình thứ hai.")

    report_text = "\n".join(report)
    out_file = AUDITGAME_DIR / "spikes" / "p2-cost-report.md"
    out_file.write_text(report_text, encoding="utf-8")
    print(f"Report written to {out_file}")
    print(report_text)

if __name__ == "__main__":
    analyze_costs()
