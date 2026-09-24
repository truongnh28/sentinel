#!/usr/bin/env python3
"""plot_regime_map.py -- Figure: the budget regime map, as SVG, from the data.

Spec: docs/manuscript/Evaluation.md Figure 1.

WHY SVG BY HAND.  This repository has no plotting dependency (requirements.lock
pins nothing of the sort) and the figure has to regenerate from
spikes/budget-sweep.json rather than be redrawn whenever a number moves, so it
is emitted directly.  Vector output is also what the camera-ready wants.

The chart is a line per Delta over the budget share, with the project's 15%
gate drawn as a reference rule and the share every published table was run at
marked on the axis -- those two annotations are the whole point of the figure:
the published numbers sit just below the band where the effect is largest.

    python3 tools/plot_regime_map.py > docs/manuscript/figures/regime-map.svg
"""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "spikes" / "budget-sweep.json"

W, H = 640, 380
L, R, T, B = 68, 150, 28, 56          # margins; R leaves room for direct labels
GATE = 15.0
PUBLISHED = 0.3205

#: One hue per Delta, assigned in fixed order and never cycled.  Two series, so
#: both are also direct-labelled and the legend is the labels themselves.
COLOUR = {2: "#1f6f8b", 4: "#c2410c"}


def main() -> int:
    d = json.loads(DATA.read_text())
    series: dict = {}
    for r in d["rows"]:
        series.setdefault(r["delta"], []).append((r["share"], r["best_gain"]))
    for k in series:
        series[k].sort()

    shares = sorted({s for pts in series.values() for s, _ in pts})
    gains = [g for pts in series.values() for _, g in pts]
    ymin, ymax = min(0.0, min(gains)) - 4, max(gains) + 8

    # x is CATEGORICAL by swept share: the grid is not uniform (it is dense
    # where the regimes change), and a linear axis would hide that by design.
    def px(share):
        i = shares.index(share)
        return L + i * (W - L - R) / (len(shares) - 1)

    def py(g):
        return T + (ymax - g) * (H - T - B) / (ymax - ymin)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'font-family="Inter, Helvetica, Arial, sans-serif" font-size="12">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>']

    # horizontal grid + y labels
    step = 10
    g = int(ymin // step) * step
    while g <= ymax:
        y = py(g)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" '
                   f'stroke="#e8e8e6" stroke-width="1"/>')
        out.append(f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" '
                   f'fill="#6b6b68" font-variant-numeric="tabular-nums">{g:+d}%</text>')
        g += step

    # the 15% gate
    yg = py(GATE)
    out.append(f'<line x1="{L}" y1="{yg:.1f}" x2="{W-R}" y2="{yg:.1f}" '
               f'stroke="#8a8a86" stroke-width="1.5" stroke-dasharray="5 4"/>')
    out.append(f'<text x="{W-R+8}" y="{yg-6:.1f}" fill="#6b6b68">15% gate</text>')

    # the share every published table used
    xp = px(PUBLISHED)
    out.append(f'<line x1="{xp:.1f}" y1="{T}" x2="{xp:.1f}" y2="{H-B}" '
               f'stroke="#b8b8b4" stroke-width="1" stroke-dasharray="2 3"/>')
    out.append(f'<text x="{xp:.1f}" y="{T-10}" text-anchor="middle" '
               f'fill="#6b6b68">published tables</text>')

    # axis
    out.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" '
               f'stroke="#3a3a38" stroke-width="1"/>')
    for s in shares:
        x = px(s)
        out.append(f'<line x1="{x:.1f}" y1="{H-B}" x2="{x:.1f}" y2="{H-B+5}" '
                   f'stroke="#3a3a38" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H-B+20}" text-anchor="middle" '
                   f'fill="#3a3a38" font-variant-numeric="tabular-nums">{s:g}</text>')
    out.append(f'<text x="{(L+W-R)/2:.1f}" y="{H-14}" text-anchor="middle" '
               f'fill="#3a3a38">budget share  B / (H &#183; &#931;&#954;)</text>')
    out.append(f'<text x="18" y="{(T+H-B)/2:.1f}" fill="#3a3a38" '
               f'transform="rotate(-90 18 {(T+H-B)/2:.1f})" text-anchor="middle">'
               f'worst-case harm reduction vs B1</text>')

    # DIRECT LABELS ARE PLACED BEFORE ANYTHING IS DRAWN, because both series
    # end at +0.0% -- they converge at the floor, which is the finding -- so
    # labelling each at its own last point puts two words on top of each other.
    # Nudged apart by a minimum separation, keeping their order.
    ends = sorted(((py(series[d][-1][1]), d) for d in series))
    placed, last = {}, None
    for y, d in ends:
        if last is not None and y - last < 15:
            y = last + 15
        placed[d] = y
        last = y

    # series
    for delta in sorted(series):
        pts = series[delta]
        c = COLOUR[delta]
        path = " ".join(f"{'M' if i == 0 else 'L'}{px(s):.1f},{py(g):.1f}"
                        for i, (s, g) in enumerate(pts))
        out.append(f'<path d="{path}" fill="none" stroke="{c}" stroke-width="2" '
                   f'stroke-linejoin="round"/>')
        for s, gg in pts:
            out.append(f'<circle cx="{px(s):.1f}" cy="{py(gg):.1f}" r="4" '
                       f'fill="{c}" stroke="#ffffff" stroke-width="2"/>')
        sx, sy = pts[-1]
        ly = placed[delta]
        if abs(ly - py(sy)) > 2:                 # nudged: draw a leader line
            out.append(f'<line x1="{px(sx)+4:.1f}" y1="{py(sy):.1f}" '
                       f'x2="{px(sx)+10:.1f}" y2="{ly-4:.1f}" stroke="{c}" '
                       f'stroke-width="1"/>')
        out.append(f'<text x="{px(sx)+13:.1f}" y="{ly:.1f}" fill="{c}" '
                   f'font-weight="600">&#916; = {delta}</text>')
        # label the peak, the number the figure exists to show
        bs, bg = max(pts, key=lambda p: p[1])
        out.append(f'<text x="{px(bs):.1f}" y="{py(bg)-12:.1f}" fill="{c}" '
                   f'text-anchor="middle" font-weight="600" '
                   f'font-variant-numeric="tabular-nums">{bg:+.1f}%</text>')

    out.append("</svg>")
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
